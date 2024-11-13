import functions.funs as fn
import pickle

deck_id = '0IDl8PGifEmggQsiVlzQuw'

decklist = fn.get_decklist(deck_id)
flatten_decklist = fn.flatten_dict(decklist)
deck_dict = fn.extract_relevant_card_data(flatten_decklist)
deck_dict = fn.add_oracle_ids(deck_dict)
deck_dict = fn.add_tags_to_deck(deck_dict)

unique_tags = fn.extract_unique_tags(deck_dict)

selected_tags = fn.tag_selection_app(unique_tags)

with open('deck_tags_unique', 'wb') as file:
    pickle.dump(unique_tags, file)

#### JUMP TO TKINTER

with open('tags_selection', 'rb') as file:
    wants = pickle.load(file)

deck_dict = fn.add_selected_tags(deck_dict, wants)

deck_string = fn.build_deck_string(deck_dict)

print(deck_string)