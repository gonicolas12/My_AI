"""
Outil de recherche locale dans les fichiers/dossiers
"""
import os

def search_files(keyword: str, directory: str) -> list:
    results = []
    for root, _, files in os.walk(directory):
        for file in files:
            if keyword.lower() in file.lower():
                results.append(os.path.join(root, file))
    return results
