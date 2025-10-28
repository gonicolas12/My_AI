"""
Module d'évaluation du modèle IA local
"""
import os
import json
import csv
import importlib.util
import sys
import argparse
from typing import List, Dict, Any, Optional
from collections import Counter

def load_testset(testset_path: str) -> List[Dict[str, Any]]:
    """Charge un jeu de test au format JSONL ou CSV."""
    if not os.path.exists(testset_path):
        raise FileNotFoundError(f"Testset not found: {testset_path}")
    data = []
    if testset_path.endswith('.jsonl'):
        with open(testset_path, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    data.append(json.loads(line))
    elif testset_path.endswith('.csv'):
        with open(testset_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                data.append(row)
    else:
        raise ValueError("Testset must be .jsonl or .csv")
    return data

def load_model(model_path: str):
    """Charge un modèle IA local (stub générique, à adapter selon l'architecture)."""
    if not os.path.exists(model_path):
        raise FileNotFoundError(f"Model not found: {model_path}")
    # Exemple : chargement d'un modèle pickle, torch, ou custom
    # Ici, on suppose une interface simple avec une méthode 'predict'

    if model_path.endswith('.py'):
        spec = importlib.util.spec_from_file_location("local_model", model_path)
        module = importlib.util.module_from_spec(spec)
        sys.modules["local_model"] = module
        spec.loader.exec_module(module)
        if hasattr(module, 'LocalModel'):
            return module.LocalModel()
        elif hasattr(module, 'predict'):
            return module
        else:
            raise AttributeError("Le fichier modèle doit contenir une classe 'LocalModel' ou une fonction 'predict'.")
    else:
        raise ValueError("Format de modèle non supporté : fournir un .py avec LocalModel ou predict.")

def compute_metrics(preds: List[str], refs: List[str]) -> Dict[str, float]:
    """Calcule précision, rappel, F1, exact match."""
    assert len(preds) == len(refs)
    tp = sum(p == r for p, r in zip(preds, refs))
    total = len(preds)
    exact_match = tp / total if total else 0.0
    # Pour précision/rappel/F1 sur classification binaire ou multi-label
    # Ici, on suppose des labels string, sinon adapter
    pred_counter = Counter(preds)
    ref_counter = Counter(refs)
    common = sum((pred_counter & ref_counter).values())
    precision = common / sum(pred_counter.values()) if pred_counter else 0.0
    recall = common / sum(ref_counter.values()) if ref_counter else 0.0
    f1 = (2 * precision * recall) / (precision + recall) if (precision + recall) else 0.0
    return {
        "exact_match": exact_match,
        "precision": precision,
        "recall": recall,
        "f1": f1
    }

def evaluate_model(model_path: str, testset_path: str, input_key: str = "input", target_key: str = "target",
                   prediction_key: Optional[str] = None, verbose: bool = True) -> Dict[str, float]:
    """
    Calcule les métriques sur un jeu de test local.
    Args:
        model_path: chemin vers le modèle local (fichier .py avec LocalModel ou predict)
        testset_path: chemin vers le jeu de test (jsonl/csv)
        input_key: clé d'entrée dans le jeu de test
        target_key: clé de référence dans le jeu de test
        prediction_key: si fourni, utilise les prédictions déjà présentes dans le jeu de test
        verbose: affiche les métriques
    Returns:
        Dictionnaire de métriques
    """
    testset = load_testset(testset_path)
    if prediction_key:
        preds = [ex[prediction_key] for ex in testset]
    else:
        model = load_model(model_path)
        preds = []
        for ex in testset:
            inp = ex[input_key]
            if hasattr(model, 'predict'):
                pred = model.predict(inp)
            elif callable(model):
                pred = model(inp)
            else:
                raise AttributeError("Le modèle doit avoir une méthode 'predict' ou être appelable.")
            preds.append(str(pred))
    refs = [str(ex[target_key]) for ex in testset]
    metrics = compute_metrics(preds, refs)
    if verbose:
        print("\n===== Résultats de l'évaluation =====")
        for k, v in metrics.items():
            print(f"{k}: {v:.4f}")
    return metrics

def main():
    """Interface en ligne de commande pour l'évaluation locale du modèle IA."""
    parser = argparse.ArgumentParser(description="Évaluation locale d'un modèle IA sur un jeu de test.")
    parser.add_argument('--model', type=str, required=True, help="Chemin du modèle local (.py)")
    parser.add_argument('--testset', type=str, required=True, help="Chemin du jeu de test (.jsonl/.csv)")
    parser.add_argument('--input_key', type=str, default="input", help="Clé d'entrée dans le jeu de test")
    parser.add_argument('--target_key', type=str, default="target", help="Clé de référence dans le jeu de test")
    parser.add_argument('--prediction_key', type=str, default=None, help="Clé de prédiction si déjà présente")
    parser.add_argument('--save_metrics', type=str, default=None, help="Chemin pour sauvegarder les métriques (json)")
    args = parser.parse_args()
    metrics = evaluate_model(args.model, args.testset, args.input_key, args.target_key, args.prediction_key)
    if args.save_metrics:
        with open(args.save_metrics, 'w', encoding='utf-8') as f:
            json.dump(metrics, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    main()
