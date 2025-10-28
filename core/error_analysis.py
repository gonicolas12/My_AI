"""
Script d'automatisation de l'analyse d'erreurs et génération de rapports d'évaluation.
"""
import json
import argparse
from typing import List, Dict, Any

def load_jsonl(path: str) -> List[Dict[str, Any]]:
    """Charge un fichier JSONL."""
    data = []
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                data.append(json.loads(line))
    return data

def analyze_errors(preds: List[str], refs: List[str]) -> List[int]:
    """Retourne les indices des erreurs (prédiction != référence)."""
    return [i for i, (p, r) in enumerate(zip(preds, refs)) if p != r]

def generate_report(metrics: Dict[str, float], errors: List[int], testset: List[Dict[str, Any]], report_path: str):
    """Génère un rapport JSON avec les métriques et exemples d'erreurs."""
    report = {
        "metrics": metrics,
        "num_errors": len(errors),
        "error_examples": [testset[i] for i in errors[:10]]
    }
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"Rapport généré dans {report_path}")

def main():
    """Interface en ligne de commande pour l'analyse d'erreurs et la génération de rapports."""
    parser = argparse.ArgumentParser(description="Analyse d'erreurs et génération de rapport d'évaluation.")
    parser.add_argument('--preds', type=str, required=True, help="Fichier de prédictions (.jsonl)")
    parser.add_argument('--refs', type=str, required=True, help="Fichier de références (.jsonl)")
    parser.add_argument('--metrics', type=str, required=True, help="Fichier de métriques (.json)")
    parser.add_argument('--report', type=str, required=True, help="Fichier de rapport de sortie (.json)")
    args = parser.parse_args()
    preds_data = load_jsonl(args.preds)
    refs_data = load_jsonl(args.refs)

    # Supporte 'prediction', 'input', ou 'target' comme clé pour les prédictions
    if preds_data and 'prediction' in preds_data[0]:
        preds = [ex['prediction'] for ex in preds_data]
    elif preds_data and 'input' in preds_data[0]:
        preds = [ex['input'] for ex in preds_data]
    elif preds_data and 'target' in preds_data[0]:
        preds = [ex['target'] for ex in preds_data]
    else:
        preds = []
    if refs_data and 'target' in refs_data[0]:
        refs = [ex['target'] for ex in refs_data]
    elif refs_data and 'input' in refs_data[0]:
        refs = [ex['input'] for ex in refs_data]
    else:
        refs = []
    with open(args.metrics, 'r', encoding='utf-8') as f:
        metrics = json.load(f)
    errors = analyze_errors(preds, refs)
    testset = load_jsonl(args.refs)
    generate_report(metrics, errors, testset, args.report)

if __name__ == "__main__":
    main()
