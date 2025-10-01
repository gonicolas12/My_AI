#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de nettoyage des doublons dans les fichiers d'enrichissement.
Garde la première occurrence de chaque question et supprime les suivantes.
"""

import json
from pathlib import Path

# Chemin vers le dossier enrichissement
ENRICHISSEMENT_DIR = Path(__file__).parent.parent / "data" / "enrichissement"

def nettoyer_doublons():
    """Nettoie les doublons dans tous les fichiers JSONL."""

    fichiers = sorted(ENRICHISSEMENT_DIR.glob("*.jsonl"))
    questions_globales = set()
    stats = {}

    print("=" * 70)
    print("NETTOYAGE DES DOUBLONS")
    print("=" * 70)
    print()

    for fichier in fichiers:
        nom_fichier = fichier.name
        print(f"Traitement de {nom_fichier}...")

        lignes_uniques = []
        questions_locales = set()
        doublons_supprimes = 0
        total_lignes = 0

        # Lire le fichier
        with open(fichier, 'r', encoding='utf-8') as f:
            for ligne in f:
                ligne = ligne.strip()
                if ligne:
                    total_lignes += 1
                    try:
                        data = json.loads(ligne)
                        question = data.get("input", "").strip()

                        # Vérifier si la question est unique (globalement ET localement)
                        if question and question not in questions_globales and question not in questions_locales:
                            lignes_uniques.append(ligne)
                            questions_globales.add(question)
                            questions_locales.add(question)
                        else:
                            doublons_supprimes += 1

                    except json.JSONDecodeError:
                        # Garder les lignes avec erreur JSON pour inspection manuelle
                        lignes_uniques.append(ligne)

        # Réécrire le fichier sans doublons
        with open(fichier, 'w', encoding='utf-8') as f:
            for ligne in lignes_uniques:
                f.write(ligne + '\n')

        stats[nom_fichier] = {
            'avant': total_lignes,
            'apres': len(lignes_uniques),
            'supprimes': doublons_supprimes
        }

        print(f"  Avant: {total_lignes} questions")
        print(f"  Apres: {len(lignes_uniques)} questions")
        print(f"  Doublons supprimes: {doublons_supprimes}")
        print()

    # Résumé global
    print("=" * 70)
    print("RESUME GLOBAL")
    print("=" * 70)

    total_avant = sum(s['avant'] for s in stats.values())
    total_apres = sum(s['apres'] for s in stats.values())
    total_supprimes = sum(s['supprimes'] for s in stats.values())

    print(f"Total questions avant nettoyage: {total_avant}")
    print(f"Total questions apres nettoyage: {total_apres}")
    print(f"Total doublons supprimes: {total_supprimes}")
    print()

    # Détail par fichier
    print("DETAIL PAR FICHIER:")
    print("-" * 70)
    for nom, s in stats.items():
        print(f"{nom:<40} : {s['avant']:>3} -> {s['apres']:>3} (-{s['supprimes']:>2})")

    print()
    print("=" * 70)
    print("Nettoyage termine avec succes!")
    print("=" * 70)

if __name__ == "__main__":
    nettoyer_doublons()
