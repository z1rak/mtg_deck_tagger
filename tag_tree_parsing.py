import streamlit as st
import pickle
from streamlit_tree_select import tree_select

# Beispiel für tag_tree (hierarchische Daten)
with open('./tag_trees/tag_tree', "rb") as f:
    tag_tree = pickle.load(f)


# Funktion, die den Baum in das für `tree_select` benötigte Format umwandelt
def convert_to_tree_select_format(tag_tree):
    nodes = []
    for tag, sub_tags in tag_tree.items():
        node = {"label": tag, "value": tag}
        if sub_tags:
            node["children"] = convert_to_tree_select_format(sub_tags)
        nodes.append(node)
    return nodes

def main():
    # Titel der App
    st.title("MTG Deck Tagger")

    # Umwandlung der tag_tree in das Format für `tree_select`
    nodes = convert_to_tree_select_format(tag_tree)

    # Zeige die Tree Select-Komponente
    selected_tags = tree_select(nodes, no_cascade=True)

    # Wenn Tags ausgewählt wurden, zeige sie
    if selected_tags:
        st.write("Ausgewählte Tags:", selected_tags["checked"])
    else:
        st.write("Keine Tags ausgewählt.")

if __name__ == "__main__":
    main()
