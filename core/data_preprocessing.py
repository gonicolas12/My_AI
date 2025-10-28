"""
Module de prétraitement des données pour l'entraînement local
"""
import json
import re
import csv
import logging
from typing import List, Dict

def clean_text(text: str) -> str:
    """Nettoie une chaîne de texte (ponctuation, espaces, casse, etc.)"""
    text = text.strip()
    text = re.sub(r"\s+", " ", text)  # espaces multiples
    text = text.replace('\u200b', '')  # caractères invisibles
    text = text.replace('\ufeff', '')  # BOM
    text = text.replace('\r', '')
    text = text.replace('\t', ' ')
    text = text.replace('“', '"').replace('”', '"')
    text = text.replace('’', "'")
    text = text.replace('–', '-')
    return text

def load_dataset(path: str) -> List[Dict]:
    """Charge un dataset local (JSONL ou CSV)"""
    data = []
    if path.endswith('.jsonl'):
        with open(path, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    data.append(json.loads(line))
    elif path.endswith('.csv'):
        with open(path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                data.append(dict(row))
    else:
        raise ValueError("Format de fichier non supporté (utilise .jsonl ou .csv)")
    return data

def save_cleaned_dataset(data: List[Dict], path: str):
    """Sauvegarde le dataset nettoyé au format JSONL ou CSV"""
    if path.endswith('.jsonl'):
        with open(path, 'w', encoding='utf-8') as f:
            for item in data:
                f.write(json.dumps(item, ensure_ascii=False) + '\n')
    elif path.endswith('.csv'):
        if not data:
            return
        with open(path, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=list(data[0].keys()))
            writer.writeheader()
            for item in data:
                writer.writerow(item)
    else:
        raise ValueError("Format de fichier non supporté (utilise .jsonl ou .csv)")

def preprocess_dataset(input_path: str, output_path: str, text_fields: list = None):
    """Pipeline complet : charge, nettoie, sauvegarde"""
    data = load_dataset(input_path)
    cleaned = []
    for item in data:
        item_clean = item.copy()
        if text_fields is None:
            # Nettoie tous les champs str
            for k, v in item.items():
                if isinstance(v, str):
                    item_clean[k] = clean_text(v)
        else:
            for k in text_fields:
                if k in item_clean and isinstance(item_clean[k], str):
                    item_clean[k] = clean_text(item_clean[k])
        cleaned.append(item_clean)
    save_cleaned_dataset(cleaned, output_path)
    logging.info("Prétraitement terminé : %s exemples sauvegardés dans %s", len(cleaned), output_path)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Prétraitement de dataset IA local")
    parser.add_argument("--input", required=True, help="Chemin du dataset brut (.jsonl ou .csv)")
    parser.add_argument("--output", required=True, help="Chemin du dataset nettoyé (.jsonl ou .csv)")
    parser.add_argument("--fields", nargs="*", help="Champs texte à nettoyer (par défaut : tous)")
    args = parser.parse_args()
    preprocess_dataset(args.input, args.output, args.fields)
