"""
Outil d'extraction d'informations structurées depuis un texte
"""

import re

def extract_emails(text: str) -> list:
    """
    Extrait toutes les adresses e-mail d'un texte donné.

    Args:
        text: Texte à analyser

    Returns:
        Liste des adresses e-mail extraites
    """
    return re.findall(r"[\w\.-]+@[\w\.-]+", text)

def extract_dates(text: str) -> list:
    """
    Extrait toutes les dates au format JJ/MM/AAAA ou variantes d'un texte donné.

    Args:
        text: Texte à analyser

    Returns:
        Liste des dates extraites
    """
    return re.findall(r"\b\d{1,2}/\d{1,2}/\d{2,4}\b", text)
