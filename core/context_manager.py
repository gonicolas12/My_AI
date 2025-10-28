"""
Gestion efficace du contexte long pour modèles IA locaux (fenêtre glissante, résumé, mémoire locale).
"""

import os
import json
import argparse
from typing import List, Dict, Any


class ContextManager:
    """Gestionnaire de contexte pour l'IA"""

    def __init__(self, max_length: int = 2048):
        self.max_length = max_length
        self.context_history = []

    def add_context(self, text: str):
        """Ajoute du contexte"""
        self.context_history.append(text)

    def get_context(self) -> str:
        """Récupère le contexte avec fenêtre glissante"""
        return sliding_window_context(self.context_history, self.max_length)

    def clear_context(self):
        """Vide le contexte"""
        self.context_history = []


def sliding_window_context(history: List[str], max_len: int = 2048) -> str:
    """Concatène l'historique en gardant les derniers tokens jusqu'à max_len."""
    context = ""
    for msg in reversed(history):
        if len(context) + len(msg) > max_len:
            break
        context = msg + "\n" + context
    return context.strip()


def summarize_history(history: List[str], max_len: int = 512) -> str:
    """Résumé simple de l'historique (stub, à remplacer par un vrai résumé local)."""
    if not history:
        return ""
    # Ici, on prend les débuts et fins, ou on coupe brutalement
    joined = " ".join(history)
    return joined[:max_len]


def save_local_memory(memory: List[Dict[str, Any]], path: str):
    """Sauvegarde la mémoire locale au format JSONL."""
    with open(path, "w", encoding="utf-8") as f:
        for ex in memory:
            f.write(json.dumps(ex, ensure_ascii=False) + "\n")


def load_local_memory(path: str) -> List[Dict[str, Any]]:
    """Charge la mémoire locale depuis un fichier JSONL."""
    if not os.path.exists(path):
        return []
    memory = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                memory.append(json.loads(line))
    return memory


def main():
    """Interface en ligne de commande pour la gestion du contexte."""
    parser = argparse.ArgumentParser(
        description="Gestion du contexte long pour IA locale."
    )
    parser.add_argument(
        "--history", type=str, required=True, help="Fichier d'historique (jsonl)"
    )
    parser.add_argument(
        "--max_len", type=int, default=2048, help="Longueur max du contexte"
    )
    parser.add_argument(
        "--mode", type=str, default="window", help="Mode : window/summarize"
    )
    args = parser.parse_args()
    memory = load_local_memory(args.history)
    # Supporte 'text', 'input', ou 'target' comme clé
    if memory and "text" in memory[0]:
        history = [ex["text"] for ex in memory]
    elif memory and "input" in memory[0]:
        history = [ex["input"] for ex in memory]
    elif memory and "target" in memory[0]:
        history = [ex["target"] for ex in memory]
    else:
        history = []
    if args.mode == "window":
        ctx = sliding_window_context(history, args.max_len)
    else:
        ctx = summarize_history(history, args.max_len)
    print(ctx)


if __name__ == "__main__":
    main()
