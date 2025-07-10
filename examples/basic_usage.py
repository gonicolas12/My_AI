#!/usr/bin/env python3
"""
Exemple d'utilisation basique de My Personal AI
Montre les interactions fondamentales avec l'IA
"""

import asyncio
import sys
from pathlib import Path

# Ajout du répertoire parent pour les imports
sys.path.append(str(Path(__file__).parent.parent))

from core.ai_engine import AIEngine

async def exemple_conversation_simple():
    """
    Exemple de conversation basique avec l'IA
    """
    print("🤖 Exemple: Conversation Simple")
    print("-" * 40)
    
    # Initialisation de l'IA
    ai = AIEngine()
    
    # Questions simples
    questions = [
        "Bonjour, comment ça va?",
        "Peux-tu m'expliquer ce qu'est Python?",
        "Quelles sont les bonnes pratiques en programmation?",
        "Comment optimiser les performances d'un script Python?"
    ]
    
    for question in questions:
        print(f"\n👤 Utilisateur: {question}")
        
        # Envoi de la question à l'IA
        response = await ai.process_query(question)
        
        if response.get("success"):
            print(f"🤖 IA: {response.get('message', 'Pas de réponse')}")
        else:
            print(f"❌ Erreur: {response.get('message', 'Erreur inconnue')}")
        
        print("-" * 40)

async def exemple_generation_code():
    """
    Exemple de génération de code simple
    """
    print("\n💻 Exemple: Génération de Code")
    print("-" * 40)
    
    ai = AIEngine()
    
    # Demandes de génération de code
    demandes = [
        "Crée une fonction Python qui calcule la factorielle",
        "Génère une classe Calculator avec les opérations de base",
        "Écris un script qui lit un fichier CSV et affiche les données"
    ]
    
    for demande in demandes:
        print(f"\n👤 Demande: {demande}")
        
        response = await ai.process_query(demande)
        
        if response.get("success") and response.get("type") == "code_generation":
            print("🤖 Code généré:")
            print("```python")
            print(response.get("code", "Pas de code"))
            print("```")
        else:
            print(f"❌ Erreur: {response.get('message', 'Erreur de génération')}")
        
        print("-" * 40)

async def exemple_questions_techniques():
    """
    Exemple de questions techniques variées
    """
    print("\n🔧 Exemple: Questions Techniques")
    print("-" * 40)
    
    ai = AIEngine()
    
    questions_tech = [
        "Quelle est la différence entre une liste et un tuple en Python?",
        "Comment gérer les exceptions en Python?",
        "Explique les décorateurs Python avec un exemple",
        "Quels sont les principes SOLID en programmation?"
    ]
    
    for question in questions_tech:
        print(f"\n👤 Question: {question}")
        
        response = await ai.process_query(question)
        
        if response.get("success"):
            # Limite l'affichage pour la démo
            message = response.get('message', '')
            if len(message) > 200:
                message = message[:200] + "..."
            print(f"🤖 IA: {message}")
        else:
            print(f"❌ Erreur: {response.get('message')}")
        
        print("-" * 40)

async def exemple_aide_debug():
    """
    Exemple d'aide au débogage
    """
    print("\n🐛 Exemple: Aide au Débogage")
    print("-" * 40)
    
    ai = AIEngine()
    
    # Simulation d'un code avec erreur
    code_avec_erreur = '''
def calculer_moyenne(nombres):
    total = 0
    for nombre in nombres:
        total += nombre
    return total / len(nombre)  # Erreur ici!

# Test
nums = [1, 2, 3, 4, 5]
moyenne = calculer_moyenne(nums)
print(moyenne)
'''
    
    question_debug = f"""
J'ai ce code Python qui génère une erreur, peux-tu m'aider à le corriger?

{code_avec_erreur}

Quelle est l'erreur et comment la corriger?
"""
    
    print("👤 Demande d'aide au débogage:")
    print(code_avec_erreur)
    
    response = await ai.process_query(question_debug)
    
    if response.get("success"):
        print("🤖 Analyse de l'IA:")
        print(response.get('message', 'Pas d\'analyse'))
    else:
        print(f"❌ Erreur: {response.get('message')}")

async def exemple_statut_systeme():
    """
    Exemple de vérification du statut système
    """
    print("\n📊 Exemple: Statut du Système")
    print("-" * 40)
    
    ai = AIEngine()
    
    # Récupération du statut
    statut = ai.get_status()
    
    print("Statut de l'IA:")
    print(f"  🚀 Moteur: {statut.get('engine', 'Inconnu')}")
    
    llm_status = statut.get('llm_status', {})
    print(f"  🧠 Backend actif: {llm_status.get('active_backend', 'Aucun')}")
    print(f"  🔌 Backends disponibles: {', '.join(llm_status.get('available_backends', []))}")
    print(f"  💬 Conversations: {statut.get('conversation_count', 0)}")
    
    # Informations détaillées sur les backends
    backend_info = llm_status.get('backend_info', {})
    if backend_info:
        print("\n  Détails des backends:")
        for name, info in backend_info.items():
            disponible = "✅" if info.get('available') else "❌"
            print(f"    {disponible} {name}: {info.get('model', 'N/A')}")

def afficher_menu():
    """
    Affiche le menu des exemples
    """
    print("\n" + "="*60)
    print("🎯 EXEMPLES D'UTILISATION BASIQUE")
    print("="*60)
    print("1. Conversation simple")
    print("2. Génération de code")
    print("3. Questions techniques")
    print("4. Aide au débogage")
    print("5. Statut du système")
    print("6. Tous les exemples")
    print("0. Quitter")
    print("="*60)

async def main():
    """
    Fonction principale des exemples
    """
    print("🤖 Exemples d'Utilisation - My Personal AI")
    
    while True:
        afficher_menu()
        
        try:
            choix = input("\nChoisissez un exemple (0-6): ").strip()
            
            if choix == "0":
                print("👋 Au revoir!")
                break
            elif choix == "1":
                await exemple_conversation_simple()
            elif choix == "2":
                await exemple_generation_code()
            elif choix == "3":
                await exemple_questions_techniques()
            elif choix == "4":
                await exemple_aide_debug()
            elif choix == "5":
                await exemple_statut_systeme()
            elif choix == "6":
                print("🚀 Exécution de tous les exemples...")
                await exemple_conversation_simple()
                await exemple_generation_code()
                await exemple_questions_techniques()
                await exemple_aide_debug()
                await exemple_statut_systeme()
                print("\n🎉 Tous les exemples terminés!")
            else:
                print("❌ Choix invalide. Veuillez choisir entre 0 et 6.")
            
            if choix != "0":
                input("\nAppuyez sur Entrée pour continuer...")
                
        except KeyboardInterrupt:
            print("\n👋 Interruption détectée. Au revoir!")
            break
        except Exception as e:
            print(f"❌ Erreur: {e}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Au revoir!")
    except Exception as e:
        print(f"❌ Erreur critique: {e}")
