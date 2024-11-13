import streamlit as st
import pickle
import os
from functions.funs import get_decklist, flatten_dict, extract_relevant_card_data, add_oracle_ids, extract_unique_tags, add_tags_to_deck


# Erstelle den Cache-Ordner, falls er noch nicht existiert
cache_folder = "cache"
if not os.path.exists(cache_folder):
    os.makedirs(cache_folder)

def get_processed_deck_cache_filename(deck_id_or_url):
    """Generiert den Cache-Dateinamen basierend auf der Deck-ID und speichert es im Cache-Ordner."""
    deck_id = deck_id_or_url.split("/")[-1]  # Extrahiere die Deck-ID aus der URL (falls nötig)
    return os.path.join(cache_folder, f"processed_deck_{deck_id}.pkl")

def load_cached_processed_deck(deck_id_or_url):
    """Lädt das zwischengespeicherte, verarbeitete Deck basierend auf der Deck-ID, wenn es existiert."""
    cache_filename = get_processed_deck_cache_filename(deck_id_or_url)
    if os.path.exists(cache_filename):
        with open(cache_filename, "rb") as f:
            return pickle.load(f)
    return None

def save_processed_deck(deck_id_or_url, processed_data):
    """Speichert das verarbeitete Deck (inklusive Tags) als Pickle-Datei basierend auf der Deck-ID im Cache-Ordner."""
    cache_filename = get_processed_deck_cache_filename(deck_id_or_url)
    with open(cache_filename, "wb") as f:
        pickle.dump(processed_data, f)

def main():
    # Titel der App
    st.title("MTG Deck Tagger")

    # Eingabe der Moxfield Deck-ID oder URL
    deck_id_or_url = st.text_input("Gib die Moxfield Deck-ID oder den vollständigen Link ein:", "")

    if deck_id_or_url:
        # Versuche, das zwischengespeicherte, verarbeitete Deck zu laden
        processed_deck_data = load_cached_processed_deck(deck_id_or_url)

        if processed_deck_data is None:
            # Wenn das verarbeitete Deck nicht gefunden wurde, lade es über die API und verarbeite es
            try:
                with st.spinner("Lade und verarbeite Deck... bitte warten."):
                    # Deck von Moxfield laden
                    deck_data = get_decklist(deck_id_or_url)
                
                    # Verarbeite das Deck
                    flat_deck = flatten_dict(deck_data)
                    deck_dict = extract_relevant_card_data(flat_deck)
                    deck_dict_with_oracle_ids = add_oracle_ids(deck_dict)
                    deck_dict_with_tags = add_tags_to_deck(deck_dict_with_oracle_ids)
                
                    # Speichern des verarbeiteten Decks nach der ersten Verarbeitung
                    save_processed_deck(deck_id_or_url, deck_dict_with_tags)
                    st.toast("Deck erfolgreich geladen, verarbeitet und zwischengespeichert.")
            except Exception as e:
                st.error(f"Fehler beim Laden und Verarbeiten des Decks: {e}")
                return
        else:
            st.toast("Verarbeitete Deckdaten aus dem Cache geladen.")
            deck_dict_with_tags = processed_deck_data

        # 2. Extrahiere einzigartige Tags aus dem Deck
        all_tags = sorted(extract_unique_tags(deck_dict_with_tags))

        # --- Scrollbarer Container für die Checkboxen ---
        with st.container(height=500):
            # Nutze den gesamten verfügbaren Platz für den Container
            selected_tags = []
            with st.form("Tags aus der Liste auswählen", clear_on_submit=False):
                # Scrollbares Layout für die Tags
                for tag in all_tags:
                    if st.checkbox(tag, key=tag):
                        selected_tags.append(tag)
                sub_commit = st.form_submit_button('Deckstring generieren', type='primary')

        # 3. Button zum Generieren des Deckstrings
        if sub_commit:
            # Generiere den Deckstring
            deck_string = ""

            # Sortiere deck_dict nach Kartennamen
            sorted_deck_data = sorted(deck_dict_with_tags.items(), key=lambda item: item[1].get('name', '').lower())

            for idx, (card_key, card) in enumerate(sorted_deck_data):
                # Hole relevante Informationen
                quantity = card.get("quantity", 0)
                name = card.get("name", "")
                card_set = card.get("set", "").upper()  # Set in Großbuchstaben
                cn = card.get("cn", "")
                tags = " ".join([f"#{tag}" for tag in selected_tags if tag in card.get('tags', [])])

                # Baue den Deckstring
                deck_string += f"{quantity} {name} ({card_set}) {cn} {tags}\n"

            # Zeige den generierten Deckstring an
            with st.container(height=300):
                st.code(deck_string)
        else:
            st.warning("Keine Tags ausgewählt!")
    else:
        st.warning("Bitte gib eine Deck-ID oder URL ein!")

if __name__ == "__main__":
    main()
