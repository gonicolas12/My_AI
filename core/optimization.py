"""
Module d'optimisation locale pour modèles IA (quantization, pruning, etc.)
"""
import os
import importlib.util
import sys
import argparse
from typing import Any

def load_model(model_path: str):
    """Charge un modèle IA local (fichier .py avec LocalModel ou optimize)."""
    if not os.path.exists(model_path):
        raise FileNotFoundError(f"Model not found: {model_path}")

    if model_path.endswith('.py'):
        spec = importlib.util.spec_from_file_location("local_model", model_path)
        module = importlib.util.module_from_spec(spec)
        sys.modules["local_model"] = module
        spec.loader.exec_module(module)
        if hasattr(module, 'LocalModel'):
            return module.LocalModel()
        elif hasattr(module, 'optimize') and callable(module.optimize):
            return module
        else:
            raise AttributeError("Le fichier modèle doit contenir une classe 'LocalModel' ou une fonction 'optimize'.")
    else:
        raise ValueError("Format de modèle non supporté : fournir un .py avec LocalModel ou optimize.")

def optimize_model(model_path: str, method: str = "quantization", export_path: str = None, verbose: bool = True) -> Any:
    """
    Optimise le modèle localement (quantization, pruning, etc.).
    Args:
        model_path: chemin du modèle local (.py)
        method: "quantization", "pruning", "distillation", etc.
        export_path: chemin de sauvegarde du modèle optimisé
        verbose: affichage
    Returns:
        Modèle optimisé
    """
    model = load_model(model_path)
    if hasattr(model, 'optimize') and callable(model.optimize):
        optimized = model.optimize(method=method)
    elif hasattr(model, 'optimize') and callable(getattr(model, 'optimize', None)):
        optimized = model.optimize(method=method)
    elif hasattr(model, 'optimize'):
        optimized = model.optimize
    elif hasattr(model, 'quantize') and method == "quantization":
        optimized = model.quantize()
    elif hasattr(model, 'prune') and method == "pruning":
        optimized = model.prune()
    else:
        raise AttributeError("Le modèle doit avoir une méthode 'optimize', 'quantize' ou 'prune'.")
    if export_path:
        if hasattr(optimized, 'save'):
            optimized.save(export_path)
        elif hasattr(optimized, 'save_weights'):
            optimized.save_weights(export_path)
        else:
            raise AttributeError("Le modèle optimisé doit avoir une méthode 'save' ou 'save_weights'.")
        if verbose:
            print(f"Modèle optimisé sauvegardé dans {export_path}")
    else:
        if verbose:
            print("Modèle optimisé en mémoire (non sauvegardé)")
    return optimized

def main():
    """Interface en ligne de commande pour l'optimisation locale du modèle IA."""
    parser = argparse.ArgumentParser(description="Optimisation locale d'un modèle IA.")
    parser.add_argument('--model', type=str, required=True, help="Chemin du modèle local (.py)")
    parser.add_argument('--method', type=str, default="quantization", help="Méthode d'optimisation (quantization/pruning)")
    parser.add_argument('--export', type=str, default=None, help="Chemin de sauvegarde du modèle optimisé")
    args = parser.parse_args()
    optimize_model(args.model, args.method, args.export)

if __name__ == "__main__":
    main()
