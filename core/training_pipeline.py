
"""
Pipeline d'entraînement local pour le modèle IA
"""
import os
import json
import csv
from typing import List, Dict, Any, Optional
import datetime

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
    import importlib.util
    import sys
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

def save_checkpoint(model, checkpoint_dir: str, step: int):
    """Sauvegarde un checkpoint du modèle (stub, à adapter selon l'implémentation)."""
    os.makedirs(checkpoint_dir, exist_ok=True)
    # Exemple : si le modèle a une méthode save ou save_weights
    if hasattr(model, 'save'):
        model.save(os.path.join(checkpoint_dir, f"checkpoint_{step}.bin"))
    elif hasattr(model, 'save_weights'):
        model.save_weights(os.path.join(checkpoint_dir, f"checkpoint_{step}.h5"))
    # Sinon, à adapter selon l'architecture

def train_model(model_path: str, trainset_path: str, valset_path: Optional[str] = None,
                input_key: str = "input", target_key: str = "target",
                epochs: int = 1, batch_size: int = 8, checkpoint_dir: str = "checkpoints",
                log_every: int = 100, verbose: bool = True):
    """
    Entraîne le modèle sur un jeu de données local.
    Args:
        model_path: chemin du modèle local (.py)
        trainset_path: chemin du jeu d'entraînement (jsonl/csv)
        valset_path: chemin du jeu de validation (optionnel)
        input_key: clé d'entrée
        target_key: clé de sortie
        epochs: nombre d'époques
        batch_size: taille de batch
        checkpoint_dir: dossier de sauvegarde des checkpoints
        log_every: fréquence de log
        verbose: affichage des logs
    """
    trainset = load_dataset(trainset_path)
    valset = load_dataset(valset_path) if valset_path else None
    model = load_model(model_path)
    n = len(trainset)
    for epoch in range(epochs):
        if verbose:
            print(f"\n===== Époque {epoch+1}/{epochs} =====")
        for i in range(0, n, batch_size):
            batch = trainset[i:i+batch_size]
            inputs = [ex[input_key] for ex in batch]
            targets = [ex[target_key] for ex in batch]
            # Appel à la méthode d'entraînement du modèle
            if hasattr(model, 'train_on_batch'):
                loss = model.train_on_batch(inputs, targets)
            elif hasattr(model, 'train'):
                loss = model.train(inputs, targets)
            else:
                raise AttributeError("Le modèle doit avoir une méthode 'train_on_batch' ou 'train'.")
            if verbose and (i // batch_size) % log_every == 0:
                print(f"Batch {i//batch_size}: loss={loss}")
        # Checkpoint à chaque époque
        save_checkpoint(model, checkpoint_dir, epoch+1)
        if verbose:
            print(f"Checkpoint sauvegardé dans {checkpoint_dir}")
        # Évaluation sur validation
        if valset:
            val_inputs = [ex[input_key] for ex in valset]
            val_targets = [ex[target_key] for ex in valset]
            if hasattr(model, 'evaluate'):
                val_loss = model.evaluate(val_inputs, val_targets)
                print(f"Validation loss: {val_loss}")
    if verbose:
        print("\nEntraînement terminé.")

def fine_tune_model(base_model_path: str, trainset_path: str, valset_path: Optional[str] = None,
                    input_key: str = "input", target_key: str = "target",
                    epochs: int = 1, batch_size: int = 8, checkpoint_dir: str = "checkpoints",
                    log_every: int = 100, verbose: bool = True):
    """
    Fine-tuning sur un modèle existant.
    """
    # Charge le modèle de base puis lance train_model
    return train_model(base_model_path, trainset_path, valset_path, input_key, target_key,
                      epochs, batch_size, checkpoint_dir, log_every, verbose)

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Pipeline d'entraînement local d'un modèle IA.")
    parser.add_argument('--model', type=str, required=True, help="Chemin du modèle local (.py)")
    parser.add_argument('--trainset', type=str, required=True, help="Chemin du jeu d'entraînement (.jsonl/.csv)")
    parser.add_argument('--valset', type=str, default=None, help="Chemin du jeu de validation (.jsonl/.csv)")
    parser.add_argument('--input_key', type=str, default="input", help="Clé d'entrée dans le dataset")
    parser.add_argument('--target_key', type=str, default="target", help="Clé de sortie dans le dataset")
    parser.add_argument('--epochs', type=int, default=1, help="Nombre d'époques")
    parser.add_argument('--batch_size', type=int, default=8, help="Taille de batch")
    parser.add_argument('--checkpoint_dir', type=str, default="checkpoints", help="Dossier de checkpoints")
    parser.add_argument('--log_every', type=int, default=100, help="Fréquence de log (en batchs)")
    args = parser.parse_args()
    train_model(args.model, args.trainset, args.valset, args.input_key, args.target_key,
               args.epochs, args.batch_size, args.checkpoint_dir, args.log_every)

if __name__ == "__main__":
    main()
