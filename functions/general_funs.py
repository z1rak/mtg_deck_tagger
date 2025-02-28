import requests
from typing import Dict, Any
from tqdm import tqdm
import time
import pickle
import os
import re
from collections import defaultdict


# Header für alle API requests
header = {
    "User-Agent": 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:133.0) Gecko/20100101 Firefox/133.0',
    "Accept": 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
}


# Globale Variable für das Rate-Limit
SCRYFALL_RATE_LIMIT = 10  # Maximal 10 Abfragen pro Sekunde
SLEEP_TIME = 1 / SCRYFALL_RATE_LIMIT  # Berechnet die Zeit, die wir zwischen den Anfragen warten müssen


def get_card_tags_dict():
    url = "https://api.scryfall.com/private/tags/oracle?pretty=true"
    output_path = "../ressources/card_tags_dict.pkl"
    response = requests.get(url)
    data = response.json()

    flipped_mapping = defaultdict(list)

    for entry in data["data"]:
        label = entry["label"]
        for oracle_id in entry["oracle_ids"]:
            flipped_mapping[oracle_id].append(label)

    flipped_mapping = dict(flipped_mapping)

    with open(output_path, "wb") as f:
        pickle.dump(flipped_mapping, f)



def fetch_oracle_id(scryfall_id: str) -> str:
    """
    Retrieves the Oracle ID for a card based on its Scryfall ID.
    
    :param scryfall_id: The Scryfall ID of the card.
    :return: The Oracle ID of the card or None if the request fails.
    """
    scryfall_api_endpoint = 'https://api.scryfall.com/cards/'
    try:
        response = requests.get(scryfall_api_endpoint + scryfall_id, headers=header)
        response.raise_for_status()
        response_json = response.json()
        
        # Delay the next request to respect rate limit
        time.sleep(SLEEP_TIME)
        
        return response_json["oracle_id"]
    except requests.RequestException as e:
        print(f"Error fetching Oracle ID for Scryfall ID {scryfall_id}: {e}")
        return None


def get_decklist(deck_id_or_url: str) -> dict:
    """
    Fetches the decklist from the Moxfield API.
    
    :param deck_id_or_url: The deck ID or full URL of the deck.
    :return: The decklist as a JSON object.
    :raises: Exception if the request fails or the response is invalid.
    """
    if "moxfield.com" in deck_id_or_url:
        match = re.search(r"decks/([a-zA-Z0-9_-]+)", deck_id_or_url)
        if match:
            deck_id = match.group(1)
        else:
            raise ValueError("The URL does not contain a valid deck ID.")
    else:
        deck_id = deck_id_or_url

    mx_api_endpoint = 'https://api2.moxfield.com/v3/decks/all/'

    try:
        response = requests.get(mx_api_endpoint + deck_id, headers=header)
        response.raise_for_status()  # Check if request was successful
        return response.json()  # Return deck data as JSON
    except requests.RequestException as e:
        print(f"Error with Moxfield API request: {e}")
        raise


def flatten_dict(data: Dict[str, Any], parent_key: str = '', sep: str = '.') -> Dict[str, Any]:
    """
    Flattens a nested dictionary recursively.
    
    :param data: The nested dictionary.
    :param parent_key: The prefix for the key (used recursively).
    :param sep: The separator for nested keys.
    :return: A flattened dictionary with combined keys.
    """
    items = []
    for k, v in data.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.extend(flatten_dict(v, new_key, sep=sep).items())
        elif isinstance(v, list):
            for i, item in enumerate(v):
                items.extend(flatten_dict(item, f"{new_key}[{i}]", sep=sep).items() if isinstance(item, dict) else [(f"{new_key}[{i}]", item)])
        else:
            items.append((new_key, v))
    return dict(items)


def extract_card_data(flat_data: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """
    Filters relevant card data from a flattened dictionary and returns a nested dictionary.
    
    :param flat_data: The flattened dictionary containing card data.
    :return: A dictionary where card keys are at the top level, each containing 'name', 'quantity', and 'cn'.
    """
    card_entries = {}
    prefixes = ["boards.mainboard.cards."]
    suffixes = [".quantity", ".card.name", ".card.set", ".card.cn", ".card.scryfall_id"]

    for key, value in flat_data.items():
        if any(key.startswith(prefix) for prefix in prefixes) and any(key.endswith(suffix) for suffix in suffixes):
            key_parts = key.split(".")
            card_key = key_parts[3]
            attribute = key_parts[-1]
            
            if card_key not in card_entries:
                card_entries[card_key] = {}
            
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


def add_oracle_ids(deck_data: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """
    Adds Oracle IDs to each card entry in the deck data based on their Scryfall ID.
    
    :param deck_data: The deck dictionary containing card data.
    :return: The updated deck dictionary with Oracle ID added for each card.
    """
    for card_key, card_data in tqdm(deck_data.items(), desc="Adding Oracle IDs", unit="card"):
        if "scryfall_id" in card_data:
            oracle_id = fetch_oracle_id(card_data["scryfall_id"])
            if oracle_id:
                card_data["oracle_id"] = oracle_id

    return deck_data


def _load_card_tags(file_path: str) -> dict:
    """
    Loads the card tags from a pickle file.
    
    :param file_path: The path to the pickle file.
    :return: The loaded card tags dictionary.
    """
    with open(file_path, 'rb') as f:
        return pickle.load(f)


def add_tags_to_deck(deck_data: dict) -> dict:
    """
    Adds tags to each card in the deck from the card tags dictionary.
    
    :param deck_data: The deck dictionary with card data.
    :return: The updated deck dictionary with tags for each card.
    """
    card_tags_dict_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'ressources', 'card_tags_dict.pkl')
    card_tags_dict = _load_card_tags(card_tags_dict_path)

    for card_key, card_data in deck_data.items():
        oracle_id = card_data.get("oracle_id")
        if oracle_id:
            tags = card_tags_dict.get(oracle_id, [])
            card_data["tags"] = tags

    return deck_data


def extract_unique_tags(deck_data: dict) -> list:
    """
    Extracts a list of unique tags from the deck data.
    
    :param deck_data: The deck dictionary containing the card tags.
    :return: A list of unique tags.
    """
    unique_tags = set()
    
    for card_key, card_data in deck_data.items():
        if "tags" in card_data:
            unique_tags.update(card_data["tags"])
    
    return list(unique_tags)


def add_selected_tags(deck_data: dict, selected_tags: list) -> dict:
    """
    Adds the intersection of selected tags to each card in the deck.
    
    :param deck_data: The deck dictionary with card data.
    :param selected_tags: A list of selected tags.
    :return: The updated deck dictionary with 'Selected_Tags' for each card.
    """
    selected_tags_set = set(selected_tags)
    
    for card_key, card_data in deck_data.items():
        if "tags" in card_data:
            selected_tags_in_card = list(selected_tags_set.intersection(card_data["tags"]))
            card_data["Selected_Tags"] = selected_tags_in_card
    
    return deck_data



def build_deck_string(deck_data: dict) -> str:
    """
    Builds a multiline string representing the deck from the deck data.
    
    :param deck_data: The deck dictionary with card data.
    :return: A multiline string representing the deck.
    """
    lines = []
    
    for card_key, card_data in deck_data.items():
        quantity = card_data.get("quantity", 0)
        name = card_data.get("name", "")
        set_name = card_data.get("set", "").upper()
        cn = card_data.get("cn", "")
        selected_tags = card_data.get("Selected_Tags", [])
        
        tag_string = " ".join([f"#{tag}" for tag in selected_tags])
        
        line = f"{quantity} {name} ({set_name}) {cn} {tag_string}"
        lines.append(line)
    
    return "\n".join(lines)


def convert_to_tree_select_format(tag_tree):
    """
    Converts the tag hierarchy into a format suitable for a tree select component.
    
    :param tag_tree: The nested tag tree.
    :return: A list of nodes formatted for tree select.
    """
    nodes = []
    for tag, sub_tags in tag_tree.items():
        node = {"label": tag, "value": tag}
        if sub_tags:
            node["children"] = convert_to_tree_select_format(sub_tags)
        nodes.append(node)
    return nodes



def get_matching_tags(selected_tags, tag_tree, card_tags):
    def get_all_descendants(tag, tree):
        """Recursively get all descendants of a tag in the hierarchy."""
        descendants = set()
        if tag in tree:
            for child in tree[tag]:
                descendants.add(child)
                descendants.update(get_all_descendants(child, tree))
        return descendants

    matching_tags = set()

    for tag in selected_tags:
        # Collect all descendants of the tag
        all_related_tags = {tag}  # Include the tag itself
        all_related_tags.update(get_all_descendants(tag, tag_tree))

        # Check if any related tag is in card_tags
        if any(related_tag in card_tags for related_tag in all_related_tags):
            matching_tags.add(tag)

    return list(matching_tags)


def filter_tag_tree(tag_tree, all_tags):
    def filter_hierarchy(tag):
        """Recursively filter the hierarchy to include only tags in all_tags."""
        if tag not in tag_tree:
            return {}
        
        # Get filtered children that are in all_tags
        filtered_children = {
            child: filter_hierarchy(child)
            for child in tag_tree[tag]
            if child in all_tags or any(desc in all_tags for desc in get_all_descendants(child, tag_tree))
        }
        
        # Only return this tag if it has filtered children or is itself in all_tags
        if tag in all_tags or filtered_children:
            return filtered_children
        return {}

    def get_all_descendants(tag, tree):
        """Recursively get all descendants of a tag in the hierarchy."""
        descendants = set()
        if tag in tree:
            for child in tree[tag]:
                descendants.add(child)
                descendants.update(get_all_descendants(child, tree))
        return descendants
    
    def get_all_keys(nested_dict):
        """Recursively extract all keys from a nested dictionary."""
        keys = set()
        for key, value in nested_dict.items():
            keys.add(key)
            if isinstance(value, dict):  # Check if the value is a nested dictionary
                keys.update(get_all_keys(value))
        return keys

    # Step 1: Filter the existing hierarchy
    filtered_tree = {
        tag: filter_hierarchy(tag)
        for tag in tag_tree
        if tag in all_tags or any(desc in all_tags for desc in get_all_descendants(tag, tag_tree))
    }

    return filtered_tree