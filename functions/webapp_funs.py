import os
import pickle


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
