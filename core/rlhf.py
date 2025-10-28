
"""
Module RLHF (Reinforcement Learning from Human Feedback) local
"""
import os
import json
import csv
import importlib.util
import sys
import argparse
from typing import List, Dict, Any

def load_dataset(dataset_path: str) -> List[Dict[str, Any]]:
    """Charge un dataset au format JSONL ou CSV."""
    if not os.path.exists(dataset_path):
        raise FileNotFoundError(f"Dataset not found: {dataset_path}")
    data = []
    if dataset_path.endswith('.jsonl'):
        with open(dataset_path, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    data.append(json.loads(line))
    elif dataset_path.endswith('.csv'):
        with open(dataset_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                data.append(row)
    else:
        raise ValueError("Dataset must be .jsonl or .csv")
    return data

def load_model(model_path: str):
    """Charge un modèle IA local (fichier .py avec LocalModel ou train)."""
    if not os.path.exists(model_path):
        raise FileNotFoundError(f"Model not found: {model_path}")

    if model_path.endswith('.py'):
        spec = importlib.util.spec_from_file_location("local_model", model_path)
        module = importlib.util.module_from_spec(spec)
        sys.modules["local_model"] = module
        spec.loader.exec_module(module)
        if hasattr(module, 'LocalModel'):
            return module.LocalModel()
        elif hasattr(module, 'train'):
            return module
        else:
            raise AttributeError("Le fichier modèle doit contenir une classe 'LocalModel' ou une fonction 'train'.")
    else:
        raise ValueError("Format de modèle non supporté : fournir un .py avec LocalModel ou train.")

def collect_human_feedback(samples: List[Dict[str, Any]], input_key: str = "input", output_key: str = "output") -> List[int]:
    """Collecte du feedback humain (notation 0/1 ou score) pour chaque sortie du modèle."""
    feedbacks = []
    print("\n=== Feedback humain requis ===")
    for i, ex in enumerate(samples):
        print(f"\nExemple {i+1} :")
        print(f"Entrée : {ex[input_key]}")
        print(f"Sortie du modèle : {ex[output_key]}")
        fb = input("Score (1=bon, 0=mauvais, ou note 0-5) : ")
        try:
            fb = int(fb)
        except Exception:
            fb = 0
        feedbacks.append(fb)
    return feedbacks

def run_rlhf(model_path: str, dataset_path: str, input_key: str = "input", target_key: str = "target",
             output_key: str = "output", feedback_key: str = "feedback",
             max_samples: int = 20, verbose: bool = True):
    """
    Boucle RLHF locale : génère des sorties, collecte feedback humain, réentraîne le modèle.
    """
    dataset = load_dataset(dataset_path)[:max_samples]
    model = load_model(model_path)
    # Génération des sorties
    for ex in dataset:
        inp = ex[input_key]
        if hasattr(model, 'predict'):
            out = model.predict(inp)
        elif callable(model):
            out = model(inp)
        else:
            raise AttributeError("Le modèle doit avoir une méthode 'predict' ou être appelable.")
        ex[output_key] = str(out)
    # Feedback humain
    feedbacks = collect_human_feedback(dataset, input_key, output_key)
    for ex, fb in zip(dataset, feedbacks):
        ex[feedback_key] = fb
    # Réentraînement (simple, pondéré par feedback)
    inputs = [ex[input_key] for ex in dataset]
    targets = [ex[target_key] for ex in dataset]
    weights = [ex[feedback_key] for ex in dataset]
    if hasattr(model, 'train_on_batch'):
        loss = model.train_on_batch(inputs, targets, sample_weight=weights)
    elif hasattr(model, 'train'):
        loss = model.train(inputs, targets, sample_weight=weights)
    else:
        raise AttributeError("Le modèle doit avoir une méthode 'train_on_batch' ou 'train'.")
    if verbose:
        print(f"Réentraînement RLHF terminé. Loss: {loss}")
    # Sauvegarde du feedback
    feedback_path = os.path.splitext(dataset_path)[0] + "_feedback.jsonl"
    with open(feedback_path, 'w', encoding='utf-8') as f:
        for ex in dataset:
            f.write(json.dumps(ex, ensure_ascii=False) + '\n')
    if verbose:
        print(f"Feedback sauvegardé dans {feedback_path}")

def main():
    """Interface en ligne de commande pour la boucle RLHF locale."""
    parser = argparse.ArgumentParser(description="Boucle RLHF locale pour modèle IA.")
    parser.add_argument('--model', type=str, required=True, help="Chemin du modèle local (.py)")
    parser.add_argument('--dataset', type=str, required=True, help="Chemin du dataset (.jsonl/.csv)")
    parser.add_argument('--input_key', type=str, default="input", help="Clé d'entrée")
    parser.add_argument('--target_key', type=str, default="target", help="Clé de référence")
    parser.add_argument('--output_key', type=str, default="output", help="Clé de sortie générée")
    parser.add_argument('--feedback_key', type=str, default="feedback", help="Clé de feedback humain")
    parser.add_argument('--max_samples', type=int, default=20, help="Nombre max d'exemples pour feedback")
    args = parser.parse_args()
    run_rlhf(args.model, args.dataset, args.input_key, args.target_key, args.output_key, args.feedback_key, args.max_samples)

if __name__ == "__main__":
    main()
