import streamlit as st
from streamlit_tree_select import tree_select
import pickle
import os
from functions.general_funs import *
from functions.webapp_funs import *




# Lade Tag Tree
with open('./tag_trees/cleaned_tag_tree.pkl', "rb") as f:
    tag_tree = pickle.load(f)


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
                    deck_dict = extract_card_data(flat_deck)
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
        deck_tag_tree = filter_tag_tree(tag_tree, all_tags)

        # --- Scrollbarer Container für die Checkboxen ---
        with st.container(height=500):
            # Nutze den gesamten verfügbaren Platz für den Container
            selected_tags = []
            with st.form('Select Tags'):
                sub_commit = st.form_submit_button('Deckstring generieren')
                nodes = convert_to_tree_select_format(deck_tag_tree)
                selected_tags = tree_select(nodes, no_cascade=True)["checked"]
                
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
                tags = " ".join([f"#{tag}" for tag in get_matching_tags(selected_tags, tag_tree, card.get('tags', []))])

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
