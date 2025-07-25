"""
Script d'automatisation de l'intégration du feedback RLHF dans le pipeline d'entraînement local.
"""
import os
import json
from typing import List, Dict, Any

def merge_feedback_into_dataset(dataset_path: str, feedback_path: str, output_path: str):
    """Ajoute les feedbacks RLHF au dataset d'entraînement."""
    data = []
    with open(dataset_path, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                data.append(json.loads(line))
    feedbacks = []
    with open(feedback_path, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                feedbacks.append(json.loads(line))
    # Fusion par input (suppose que input est unique)
    fb_map = {ex['input']: ex for ex in feedbacks}
    for ex in data:
        if ex['input'] in fb_map:
            ex['feedback'] = fb_map[ex['input']].get('feedback', None)
    with open(output_path, 'w', encoding='utf-8') as f:
        for ex in data:
            f.write(json.dumps(ex, ensure_ascii=False) + '\n')
    print(f"Feedback intégré dans {output_path}")

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Intégration automatique du feedback RLHF dans le dataset.")
    parser.add_argument('--dataset', type=str, required=True, help="Dataset d'entraînement (.jsonl)")
    parser.add_argument('--feedback', type=str, required=True, help="Fichier de feedback RLHF (.jsonl)")
    parser.add_argument('--output', type=str, required=True, help="Fichier de sortie (.jsonl)")
    args = parser.parse_args()
    merge_feedback_into_dataset(args.dataset, args.feedback, args.output)

if __name__ == "__main__":
    main()
