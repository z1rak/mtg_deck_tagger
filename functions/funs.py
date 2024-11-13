import requests
from typing import Dict, Any
from tqdm import tqdm
import time
import pickle
import os
import re
import streamlit as st

# Header für alle API requests
header = {
    "User-Agent": 'MTG-Deck-Tagger-V1',
    "Accept": '*/*'
}

# Globale Variable für das Rate-Limit
SCRYFALL_RATE_LIMIT = 10  # Maximal 10 Abfragen pro Sekunde
SLEEP_TIME = 1 / SCRYFALL_RATE_LIMIT  # Berechnet die Zeit, die wir zwischen den Anfragen warten müssen

def get_oracle_id(scryfall_id: str) -> str:
    """
    Ruft die Oracle ID für eine Karte basierend auf der Scryfall ID ab.
    
    :param scryfall_id: Die Scryfall ID der Karte.
    :return: Die Oracle ID der Karte oder None, falls die Anfrage fehlschlägt.
    """
    scryfall_api_endpoint = 'https://api.scryfall.com/cards/'
    try:
        response = requests.get(scryfall_api_endpoint + scryfall_id, headers=header)
        response.raise_for_status()
        response_json = response.json()
        
        # Verzögere die nächste Anfrage, um das Rate-Limit zu respektieren
        time.sleep(SLEEP_TIME)
        
        return response_json["oracle_id"]
    except requests.RequestException as e:
        print(f"Fehler beim Abrufen der Oracle ID für Scryfall ID {scryfall_id}: {e}")
        return None


def get_decklist(deck_id_or_url: str) -> dict:
    """
    Holt die Deckliste von der Moxfield-API.
    
    :param deck_id_or_url: Die Deck-ID oder der volle URL-Link zum Deck.
    :return: Die Deckliste als JSON-Objekt.
    :raises: Exception falls die Anfrage fehlschlägt oder die Antwort ungültig ist.
    """
    # Überprüfen, ob der Parameter eine URL ist
    if "moxfield.com" in deck_id_or_url:
        # Wenn es eine URL ist, extrahiere die Deck-ID aus der URL
        match = re.search(r"decks/([a-zA-Z0-9]+)", deck_id_or_url)
        if match:
            deck_id = match.group(1)
        else:
            raise ValueError("Die URL enthält keine gültige Deck-ID.")
    else:
        # Wenn es bereits eine Deck-ID ist, verwenden wir sie direkt
        deck_id = deck_id_or_url

    # Moxfield API-Endpunkt
    mx_api_endpoint = 'https://api2.moxfield.com/v3/decks/all/'

    try:
        # Sende die Anfrage an die Moxfield API
        response = requests.get(mx_api_endpoint + deck_id, headers=header)
        response.raise_for_status()  # Überprüfen, ob die Anfrage erfolgreich war
        return response.json()  # Rückgabe der Deck-Daten als JSON
    except requests.RequestException as e:
        print(f"Fehler bei der Anfrage an Moxfield API: {e}")
        raise


def flatten_dict(dl: Dict[str, Any], parent_key: str = '', sep: str = '.') -> Dict[str, Any]:
    """
    Flacht ein verschachteltes Dictionary rekursiv ab.
    
    :param dl: Das verschachtelte Dictionary.
    :param parent_key: Der Präfix-Schlüssel (wird rekursiv erweitert).
    :param sep: Das Trennzeichen für verschachtelte Schlüssel.
    :return: Ein abgeflachtes Dictionary mit zusammengesetzten Schlüsseln.
    """
    items = []
    for k, v in dl.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.extend(flatten_dict(v, new_key, sep=sep).items())
        elif isinstance(v, list):
            for i, item in enumerate(v):
                items.extend(flatten_dict(item, f"{new_key}[{i}]", sep=sep).items() if isinstance(item, dict) else [(f"{new_key}[{i}]", item)])
        else:
            items.append((new_key, v))
    return dict(items)


def extract_relevant_card_data(flat_data: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """
    Filtert relevante Kartendaten aus einem abgeflachten Dictionary und gibt ein verschachteltes Dictionary zurück.
    
    :param flat_data: Das abgeflachte Dictionary mit Kartendaten.
    :return: Ein Dictionary, in dem die Kartenschlüssel als oberste Ebene dienen,
             und jede Karte ein Dictionary mit 'name', 'quantity' und 'cn' enthält.
    """
    # Zwischenspeicher für die gefilterten Kartendaten
    card_entries = {}

    # Definiere den Filter für Schlüssel, die wir extrahieren möchten
    prefixes = ["boards.mainboard.cards."]
    suffixes = [".quantity", ".card.name", ".card.set", ".card.cn", ".card.scryfall_id"]

    for key, value in flat_data.items():
        # Überprüfen, ob der Schlüssel mit einem der Prefixe beginnt und einem der Suffixe endet
        if any(key.startswith(prefix) for prefix in prefixes) and any(key.endswith(suffix) for suffix in suffixes):
            # Extrahiere den Kartenschlüssel [KEY] und das End-Attribut (z.B. name, quantity, cn)
            key_parts = key.split(".")
            card_key = key_parts[3]  # Annahme: Der 4. Teil ist der eindeutige Kartenschlüssel
            attribute = key_parts[-1]  # Der letzte Teil ist das gewünschte Attribut
            
            # Initialisiere ein Dictionary für diesen Kartenschlüssel, falls noch nicht vorhanden
            if card_key not in card_entries:
                card_entries[card_key] = {}
            
            # Mappe das Attribut zum richtigen Feldnamen
            if attribute == "quantity":
                card_entries[card_key]["quantity"] = value
            elif attribute == "name":
                card_entries[card_key]["name"] = value
            elif attribute == "cn":
                card_entries[card_key]["cn"] = value
            elif attribute == "set":
                card_entries[card_key]["set"] = value
            elif attribute == "scryfall_id":
                card_entries[card_key]["scryfall_id"] = value

    return card_entries


def add_oracle_ids(deck_dict: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """
    Fügt jedem Karteneintrag im Deck_Dict basierend auf der scryfall_id das Feld 'oracle_id' hinzu.
    
    :param deck_dict: Das Deck_Dict, das Kartendaten enthält.
    :return: Das aktualisierte Deck_Dict mit oracle_id für jede Karte.
    """
    # Fortschrittsanzeige für eine größere Anzahl von Karten
    for card_key, card_data in tqdm(deck_dict.items(), desc="Hinzufügen von Oracle IDs", unit="Karten"):
        # Prüfe, ob die scryfall_id im Dictionary existiert
        if "scryfall_id" in card_data:
            # Verwende die get_oracle_id-Funktion, um die oracle_id abzurufen
            oracle_id = get_oracle_id(card_data["scryfall_id"])
            # Füge oracle_id zum Karten-Dictionary hinzu, wenn die Abfrage erfolgreich war
            if oracle_id:
                card_data["oracle_id"] = oracle_id

    # Rückgabe des aktualisierten Dictionaries
    return deck_dict


def _load_card_tags(file_path: str) -> dict:
    """
    Lädt das card_tags_dict aus einer Pickle-Datei.
    
    :param file_path: Der Pfad zur Pickle-Datei.
    :return: Das geladene card_tags_dict.
    """
    with open(file_path, 'rb') as f:
        return pickle.load(f)


def add_tags_to_deck(deck_dict: dict) -> dict:
    """
    Fügt jedem Karteneintrag im deck_dict die zugehörigen Tags aus dem card_tags_dict hinzu.
    
    :param deck_dict: Das Deck-Dictionary mit den Karteninformationen.
    :param card_tags_dict: Das Dictionary mit Oracle_IDs als Keys und Listen von Tags als Values.
    :return: Das aktualisierte deck_dict, das die Tags für jede Karte enthält.
    """
    # Relativer Pfad zur Datei 'card_tags_dict' im Ordner 'ressources'
    card_tags_dict_path = os.path.join(os.path.dirname(__file__), '..', 'ressources', 'card_tags_dict')
    card_tags_dict = _load_card_tags(card_tags_dict_path)

    for card_key, card_data in deck_dict.items():
        # Prüfen, ob die Oracle_ID existiert
        oracle_id = card_data.get("oracle_id")
        if oracle_id:
            # Tags aus dem card_tags_dict holen, falls vorhanden
            tags = card_tags_dict.get(oracle_id, [])
            # Füge die Tags zur Karte hinzu
            card_data["tags"] = tags

    return deck_dict


def extract_unique_tags(deck_dict: dict) -> list:
    """
    Extrahiert eine Liste eindeutiger Tags aus dem Deck-Dictionary.
    
    :param deck_dict: Das Dictionary mit den Kartendaten, das die Tags enthält.
    :return: Eine Liste mit eindeutigen Tags.
    """
    unique_tags = set()  # Ein Set, um Duplikate zu vermeiden
    
    # Iteriere über alle Karten im Deck
    for card_key, card_data in deck_dict.items():
        # Überprüfe, ob die Tags für diese Karte existieren
        if "tags" in card_data:
            # Füge alle Tags der Karte dem Set hinzu
            unique_tags.update(card_data["tags"])
    
    # Rückgabe der eindeutigen Tags als Liste
    return list(unique_tags)


def add_selected_tags(deck_dict: dict, tag_auswahl: list) -> dict:
    """
    Fügt jedem Karteneintrag im Deck_Dict die Schnittmenge der Tags aus der Tag_Auswahl hinzu.
    
    :param deck_dict: Das Deck-Dictionary mit den Kartendaten.
    :param tag_auswahl: Eine Liste von ausgewählten Tags.
    :return: Das aktualisierte Deck_Dict mit dem Schlüssel 'Selected_Tags' für jede Karte.
    """
    tag_auswahl_set = set(tag_auswahl)  # Die Tag_Auswahl in ein Set umwandeln
    
    for card_key, card_data in deck_dict.items():
        # Überprüfen, ob die Karte Tags hat
        if "tags" in card_data:
            # Berechne die Schnittmenge zwischen den Tags der Karte und der Tag_Auswahl
            selected_tags = list(tag_auswahl_set.intersection(card_data["tags"]))
            # Füge die Schnittmenge als 'Selected_Tags' hinzu
            card_data["Selected_Tags"] = selected_tags
    
    return deck_dict


def build_deck_string(deck_dict: dict) -> str:
    """
    Erzeugt einen mehrzeiligen String aus dem Deck_Dict.
    Jede Zeile repräsentiert eine Karte im Format:
    [quantity] [name] ([set]) [cn] #[Selected_tags]
    
    :param deck_dict: Das Deck-Dictionary mit den Kartendaten.
    :return: Ein mehrzeiliger String, der alle Karten im Deck darstellt.
    """
    lines = []  # Eine Liste, um die einzelnen Zeilen zu speichern
    
    for card_key, card_data in deck_dict.items():
        # Extrahiere die notwendigen Felder für den String
        quantity = card_data.get("quantity", 0)
        name = card_data.get("name", "")
        set_name = card_data.get("set", "").upper()
        cn = card_data.get("cn", "")
        selected_tags = card_data.get("Selected_Tags", [])
        
        # Erstelle die Tags mit vorangestelltem Hashtag
        tag_string = " ".join([f"#{tag}" for tag in selected_tags])
        
        # Baue die Zeile im gewünschten Format
        line = f"{quantity} {name} ({set_name}) {cn} {tag_string}"
        
        # Füge die Zeile zur Liste hinzu
        lines.append(line)
    
    # Füge alle Zeilen mit einem Zeilenumbruch zusammen
    return "\n".join(lines)