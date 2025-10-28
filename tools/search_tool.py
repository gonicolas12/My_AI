"""
Outil de recherche locale dans les fichiers/dossiers
"""
import os

def search_files(keyword: str, directory: str) -> list:
    """
    Recherche les fichiers contenant un mot-clé dans leur nom dans un répertoire donné.

    Args:
        keyword: Mot-clé à rechercher dans les noms de fichiers
        directory: Répertoire de recherche

    Returns:
        Liste des chemins de fichiers correspondants
    """
    results = []
    for root, _, files in os.walk(directory):
        for file in files:
            if keyword.lower() in file.lower():
                results.append(os.path.join(root, file))
    return results
