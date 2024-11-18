import pickle
from bs4 import BeautifulSoup
import requests
import time
from tqdm import tqdm
import os

# Header für alle API requests
header = {
    "User-Agent": 'MTG-Deck-Tagger-V1',
    "Accept": '*/*'
}

# Globale Variable für das Rate-Limit
SCRYFALL_RATE_LIMIT = 10  # Maximal 10 Abfragen pro Sekunde
SLEEP_TIME = 1 / SCRYFALL_RATE_LIMIT  # Berechnet die Zeit, die wir zwischen den Anfragen warten müssen

with open('../ressources/card_tags_dict.pkl', "rb") as f:
    deck = pickle.load(f)

all_tags = set()
for card_key, card_data in deck.items():
    [all_tags.add(tag) for tag in card_data]

all_tags = sorted(all_tags)

for tag in tqdm(all_tags):
    if os.path.exists(f'./tag_trees/tmp/{tag}.html'):
        next
    else:
        tagger_link = f'https://tagger.scryfall.com/tags/card/{tag}/tree'
        try:
            response = requests.get(tagger_link, headers=header)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            if len(soup.find_all('div', class_='tags-list__row')) > 2:
                with open(f'./tag_trees/tmp/{tag}.html', 'w', encoding='utf-8') as file:
                    file.write(soup.find('div', 'site-body').prettify())
        except:
            next
        time.sleep(SLEEP_TIME)
