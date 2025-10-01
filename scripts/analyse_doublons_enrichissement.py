#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script d'analyse des questions existantes dans les fichiers d'enrichissement
pour éviter les doublons lors de l'ajout de nouveau contenu.
"""

import json
from pathlib import Path
from collections import defaultdict

# Chemin vers le dossier enrichissement
ENRICHISSEMENT_DIR = Path(__file__).parent.parent / "data" / "enrichissement"

def analyser_fichiers():
    """Analyse tous les fichiers JSONL et extrait les questions."""

    questions_par_fichier = defaultdict(list)
    toutes_questions = set()
    doublons = []

    # Lister tous les fichiers JSONL
    fichiers = list(ENRICHISSEMENT_DIR.glob("*.jsonl"))

    print(f"🔍 Analyse de {len(fichiers)} fichiers d'enrichissement...\n")

    for fichier in sorted(fichiers):
        nom_fichier = fichier.name
        questions = []

        try:
            with open(fichier, 'r', encoding='utf-8') as f:
                for ligne_num, ligne in enumerate(f, 1):
                    ligne = ligne.strip()
                    if ligne:
                        try:
                            data = json.loads(ligne)
                            question = data.get("input", "").strip()
                            if question:
                                questions.append(question)

                                # Vérifier si c'est un doublon
                                if question in toutes_questions:
                                    doublons.append({
                                        "question": question,
                                        "fichier": nom_fichier,
                                        "ligne": ligne_num
                                    })
                                else:
                                    toutes_questions.add(question)
                        except json.JSONDecodeError as e:
                            print(f"⚠️  Erreur JSON dans {nom_fichier} ligne {ligne_num}: {e}")

        except Exception as e:
            print(f"❌ Erreur lors de la lecture de {nom_fichier}: {e}")
            continue

        questions_par_fichier[nom_fichier] = questions
        print(f"✅ {nom_fichier:<40} : {len(questions):>4} questions")

    print(f"\n{'='*70}")
    print(f"📊 STATISTIQUES GLOBALES")
    print(f"{'='*70}")
    print(f"Total de questions uniques : {len(toutes_questions)}")
    print(f"Total de questions (avec doublons) : {sum(len(q) for q in questions_par_fichier.values())}")
    print(f"Nombre de doublons détectés : {len(doublons)}")

    if doublons:
        print(f"\n{'='*70}")
        print(f"⚠️  DOUBLONS DÉTECTÉS")
        print(f"{'='*70}")
        for doublon in doublons:
            print(f"📄 {doublon['fichier']} (ligne {doublon['ligne']})")
            print(f"   Question: {doublon['question'][:80]}...")
            print()

    # Sauvegarder la liste des questions dans un fichier
    output_file = ENRICHISSEMENT_DIR.parent.parent / "claudedocs" / "questions_existantes.json"
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({
            "questions_par_fichier": {k: v for k, v in questions_par_fichier.items()},
            "toutes_questions": sorted(list(toutes_questions)),
            "statistiques": {
                "total_unique": len(toutes_questions),
                "total_avec_doublons": sum(len(q) for q in questions_par_fichier.values()),
                "nombre_doublons": len(doublons)
            },
            "doublons": doublons
        }, f, ensure_ascii=False, indent=2)

    print(f"\n✅ Liste des questions sauvegardée dans: {output_file}")

    return questions_par_fichier, toutes_questions, doublons


if __name__ == "__main__":
    analyser_fichiers()
