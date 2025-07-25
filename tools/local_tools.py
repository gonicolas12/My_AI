"""
Outils locaux spécialisés pour raisonnement, calcul, recherche, extraction d'infos, etc.
"""
import os
import math
import glob
import re
from typing import List, Any

def local_math(expr: str) -> Any:
    """Évalue une expression mathématique locale."""
    try:
        return eval(expr, {"__builtins__": None, "math": math})
    except Exception as e:
        return f"Erreur: {e}"

def local_search(pattern: str, folder: str = ".") -> List[str]:
    """Recherche de fichiers locaux par motif."""
    return glob.glob(os.path.join(folder, pattern), recursive=True)

def extract_emails(text: str) -> List[str]:
    """Extraction d'adresses email d'un texte."""
    return re.findall(r"[\w\.-]+@[\w\.-]+", text)

def extract_dates(text: str) -> List[str]:
    """Extraction de dates simples (format JJ/MM/AAAA ou AAAA-MM-JJ)."""
    return re.findall(r"\b\d{2}/\d{2}/\d{4}\b|\b\d{4}-\d{2}-\d{2}\b", text)

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Outils locaux pour IA (calcul, recherche, extraction)")
    parser.add_argument('--tool', type=str, required=True, help="math/search/emails/dates")
    parser.add_argument('--input', type=str, required=True, help="Entrée pour l'outil")
    parser.add_argument('--folder', type=str, default=".", help="Dossier pour la recherche locale")
    args = parser.parse_args()
    if args.tool == "math":
        print(local_math(args.input))
    elif args.tool == "search":
        print(local_search(args.input, args.folder))
    elif args.tool == "emails":
        print(extract_emails(args.input))
    elif args.tool == "dates":
        print(extract_dates(args.input))
    else:
        print("Outil non reconnu")

if __name__ == "__main__":
    main()
