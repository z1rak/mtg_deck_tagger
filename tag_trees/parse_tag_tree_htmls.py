import os
import pickle
from bs4 import BeautifulSoup

def extract_tag_hierarchy_from_html(html):
    soup = BeautifulSoup(html, 'html.parser')
    tag_hierarchy = {}
    parent_stack = []

    for div in soup.find_all('div', class_='tags-list__row'):
        depth_class = div.get('class', [])
        depth = next((x for x in depth_class if x.startswith('depth-')), None)

        if depth:
            depth_number = int(depth.split('-')[1])
            if depth_number < 4:
                a_tag = div.find('a')
            
                # Überprüfen, ob ein <a> Tag existiert
                if a_tag:
                    tag_text = a_tag.get_text(strip=True)
                else:
                    continue  # Wenn kein <a> Tag gefunden wird, überspringe dieses Element

                # Stelle sicher, dass wir die parent_stack korrekt handhaben
                while len(parent_stack) + 1 > depth_number:
                    parent_stack.pop()  # Poppe, bis wir die richtige Tiefe haben

                if len(parent_stack) == 0:  # Falls wir bei der obersten Ebene sind
                    tag_hierarchy[tag_text] = {}
                    parent_stack.append(tag_hierarchy[tag_text])
                else:  # Wenn wir tiefer sind
                    parent_stack[-1][tag_text] = {}
                    parent_stack.append(parent_stack[-1][tag_text])

    return tag_hierarchy


def remove_duplicates_at_lowest_level(hierarchy):
    tmp_hier = hierarchy.copy()
    def traverse(node, depth, key_depths):
        # Traverse the node recursively and record depths of keys
        for key, child in node.items():
            # Append the current depth for the key
            if key not in key_depths:
                key_depths[key] = []
            key_depths[key].append(depth)
            
            if child:  # If there are nested children, recurse
                traverse(child, depth + 1, key_depths)

    def clean(node, depth, key_depths):
        # Clean duplicates at the current level
        for key in list(node.keys()):
            # Remove the key if it appears deeper in the hierarchy
            if (len(key_depths[key]) > 1) and (max(key_depths[key]) == depth):
                del node[key]
            elif node[key]:  # If the key has children, recurse
                clean(node[key], depth + 1, key_depths)

    # Step 1: Traverse the hierarchy and collect key depths
    key_depths = {}
    traverse(tmp_hier, 0, key_depths)

    # Step 2: Clean the hierarchy based on key depths
    clean(tmp_hier, 0, key_depths)

    return tmp_hier


def import_multiple_html_files_from_folder(folder_path):
    combined_hierarchy = {}

    for filename in os.listdir(folder_path):
        if filename.endswith(".html"):
            with open(os.path.join(folder_path, filename), 'r', encoding='utf-8') as file:
                html_content = file.read()
                file_hierarchy = extract_tag_hierarchy_from_html(html_content)
                combined_hierarchy.update(file_hierarchy)

    return combined_hierarchy

# Pfad zum Ordner
folder_path = './tmp'
combined_tags = import_multiple_html_files_from_folder(folder_path)
cleaned_tags = remove_duplicates_at_lowest_level(combined_tags)
cleaned_tags = {k:v for k,v in sorted(combined_tags.items())}

# Ausgabe der bereinigten kombinierten Hierarchie
print(cleaned_tags)

# Speichere die bereinigte Hierarchie in einer Datei
with open('cleaned_tag_tree.pkl', 'wb') as file:
    pickle.dump(cleaned_tags, file)