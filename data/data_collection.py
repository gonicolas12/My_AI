"""
Scripts de collecte, nettoyage et structuration des données d'entraînement locales.
"""
import os
import json
import csv
import re
import argparse
from typing import List, Dict, Any

def collect_texts_from_folder(folder: str, exts=(".txt", ".md", ".csv", ".jsonl")) -> List[str]:
    """Récupère tous les textes des fichiers d'un dossier (récursif)."""
    texts = []
    for root, _, files in os.walk(folder):
        for f in files:
            if f.endswith(exts):
                path = os.path.join(root, f)
                try:
                    with open(path, 'r', encoding='utf-8') as file:
                        texts.append(file.read())
                except Exception:
                    continue
    return texts

def clean_text(text: str) -> str:
    """Nettoie un texte brut (suppression doublons, espaces, normalisation unicode, etc.)."""
    text = re.sub(r'\s+', ' ', text)
    text = text.strip()
    return text

def remove_duplicates(texts: List[str]) -> List[str]:
    """Supprime les doublons dans une liste de textes."""
    seen = set()
    unique = []
    for t in texts:
        if t not in seen:
            unique.append(t)
            seen.add(t)
    return unique

def save_jsonl(data: List[Dict[str, Any]], path: str):
    """Sauvegarde une liste de dictionnaires au format JSONL."""
    with open(path, 'w', encoding='utf-8') as f:
        for ex in data:
            f.write(json.dumps(ex, ensure_ascii=False) + '\n')

def save_csv(data: List[Dict[str, Any]], path: str):
    """Sauvegarde une liste de dictionnaires au format CSV."""
    if not data:
        return
    with open(path, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(data[0].keys()))
        writer.writeheader()
        writer.writerows(data)

def build_dataset_from_texts(texts: List[str], output_path: str, fmt: str = "jsonl"):
    """Structure une liste de textes en dataset (jsonl/csv)."""
    data = [{"input": t, "target": t} for t in texts]
    if fmt == "jsonl":
        save_jsonl(data, output_path)
    elif fmt == "csv":
        save_csv(data, output_path)
    else:
        raise ValueError("Format non supporté")

def main():
    """Point d'entrée pour la collecte et le nettoyage des données."""
    parser = argparse.ArgumentParser(description="Collecte et nettoyage de données locales pour IA.")
    parser.add_argument('--folder', type=str, required=True, help="Dossier à explorer")
    parser.add_argument('--output', type=str, required=True, help="Fichier de sortie (.jsonl/.csv)")
    parser.add_argument('--format', type=str, default="jsonl", help="Format de sortie (jsonl/csv)")
    args = parser.parse_args()
    texts = collect_texts_from_folder(args.folder)
    texts = [clean_text(t) for t in texts]
    texts = remove_duplicates(texts)
    build_dataset_from_texts(texts, args.output, args.format)
    print(f"{len(texts)} exemples sauvegardés dans {args.output}")

if __name__ == "__main__":
    main()
