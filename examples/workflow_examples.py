#!/usr/bin/env python3
"""
Exemples de workflows complets - My Personal AI

Ce script démontre des scénarios d'utilisation réalistes 
de l'IA locale avec toutes ses fonctionnalités.
"""

import sys
import os
import time

# Ajouter le répertoire parent au chemin Python
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.ai_engine import AIEngine
from core.conversation import ConversationManager

def simulate_user_input(text, delay=1):
    """Simule une entrée utilisateur avec un délai."""
    print(f"🤖 Utilisateur: {text}")
    time.sleep(delay)
    return text

def simulate_ai_response(ai_model, query):
    """Simule une réponse de l'IA."""
    response = ai_model.generate_response(query)
    print(f"🧠 IA: {response}")
    time.sleep(0.5)
    return response

def workflow_document_analysis():
    """Workflow complet d'analyse de document."""
    print("📄 WORKFLOW: Analyse de Document")
    print("=" * 50)
    
    try:
        # Initialiser l'IA
        ai_engine = AIEngine()
        ai_model = ai_engine.ai_model
        
        # 1. Salutation
        query = simulate_user_input("bonjour")
        simulate_ai_response(ai_model, query)
        
        # 2. Simulation du chargement d'un document
        print("\n📁 [Simulation: Utilisateur glisse un fichier 'rapport_2024.pdf']")
        ai_model.memory.store_document_content(
            "rapport_2024.pdf", 
            """Rapport Annuel 2024
            
            Résumé Exécutif:
            - Croissance de 15% du chiffre d'affaires
            - Expansion dans 3 nouveaux marchés
            - Investissement de 2M€ en R&D
            - Équipe passée de 50 à 75 employés
            
            Recommandations:
            1. Automatiser les processus répétitifs
            2. Développer une application mobile
            3. Renforcer la cybersécurité
            4. Former les équipes aux nouvelles technologies
            
            Technologies mentionnées:
            - Python pour l'automatisation
            - React Native pour l'app mobile
            - Solutions Cloud AWS/Azure
            """
        )
        
        # 3. Demande de résumé
        query = simulate_user_input("résume ce document")
        simulate_ai_response(ai_model, query)
        
        # 4. Question spécifique
        query = simulate_user_input("quelles sont les recommandations du rapport ?")
        simulate_ai_response(ai_model, query)
        
        # 5. Question technique liée au document
        query = simulate_user_input("comment implémenter l'automatisation en Python mentionnée dans le rapport ?")
        simulate_ai_response(ai_model, query)
        
        # 6. Au revoir
        query = simulate_user_input("merci, au revoir")
        simulate_ai_response(ai_model, query)
        
    except Exception as e:
        print(f"Erreur dans le workflow: {e}")

def workflow_coding_assistance():
    """Workflow d'assistance au développement."""
    print("\n\n💻 WORKFLOW: Assistance au Développement")
    print("=" * 50)
    
    try:
        ai_engine = AIEngine()
        ai_model = ai_engine.ai_model
        
        # 1. Salutation informelle
        query = simulate_user_input("slt")
        simulate_ai_response(ai_model, query)
        
        # 2. Question technique initiale
        query = simulate_user_input("Comment créer une classe en Python ?")
        simulate_ai_response(ai_model, query)
        
        # 3. Simulation de code fourni par l'utilisateur
        print("\n💾 [Simulation: Utilisateur partage du code]")
        code_content = """class User:
    def __init__(self, name):
        self.name = name
    
    def greet(self):
        print(f"Hello, {self.name}")
        
# Problème: comment ajouter une méthode pour l'âge ?"""
        
        ai_model.memory.store_code_content("user_class", code_content)
        
        # 4. Demande d'amélioration du code
        query = simulate_user_input("comment améliorer cette classe User ?")
        simulate_ai_response(ai_model, query)
        
        # 5. Question sur les bonnes pratiques
        query = simulate_user_input("quelles sont les bonnes pratiques pour les classes Python ?")
        simulate_ai_response(ai_model, query)
        
        # 6. Question de débogage
        query = simulate_user_input("pourquoi mon code ne fonctionne pas ?")
        simulate_ai_response(ai_model, query)
        
    except Exception as e:
        print(f"Erreur dans le workflow: {e}")

def workflow_mixed_session():
    """Workflow mixte combinant plusieurs types d'interactions."""
    print("\n\n🔄 WORKFLOW: Session Mixte Complète")
    print("=" * 50)
    
    try:
        ai_engine = AIEngine()
        ai_model = ai_engine.ai_model
        
        # 1. Salutation
        query = simulate_user_input("bjr")
        simulate_ai_response(ai_model, query)
        
        # 2. Question générale
        query = simulate_user_input("comment vas-tu ?")
        simulate_ai_response(ai_model, query)
        
        # 3. Chargement d'un document technique
        print("\n📁 [Simulation: Chargement 'guide_python.pdf']")
        ai_model.memory.store_document_content(
            "guide_python.pdf",
            """Guide Python Avancé
            
            Chapitre 1: Décorateurs
            Les décorateurs permettent de modifier le comportement des fonctions.
            
            Exemple:
            @property
            def name(self):
                return self._name
                
            Chapitre 2: Gestion des Exceptions
            try:
                # code risqué
            except ValueError as e:
                print(f"Erreur: {e}")
            """
        )
        
        # 4. Question sur le document
        query = simulate_user_input("que dit le guide sur les décorateurs ?")
        simulate_ai_response(ai_model, query)
        
        # 5. Question technique liée
        query = simulate_user_input("montre-moi un exemple de décorateur Python")
        simulate_ai_response(ai_model, query)
        
        # 6. Nouveau document
        print("\n📁 [Simulation: Chargement 'analyse_donnees.docx']")
        ai_model.memory.store_document_content(
            "analyse_donnees.docx",
            """Analyse des Données Client 2024
            
            Données collectées:
            - 10,000 clients actifs
            - Taux de satisfaction: 87%
            - Produits les plus vendus: A, B, C
            
            Recommandations analytiques:
            - Utiliser pandas pour l'analyse
            - Créer des visualisations avec matplotlib
            - Implémenter un modèle prédictif
            """
        )
        
        # 7. Question comparative entre documents
        query = simulate_user_input("comment utiliser Python pour l'analyse de données selon les deux documents ?")
        simulate_ai_response(ai_model, query)
        
        # 8. Clear et nouvelle session
        print("\n🔄 [Simulation: Clear Chat]")
        ai_model.memory.clear_all()
        ai_engine.conversation.clear_history()
        
        # 9. Nouvelle salutation après clear
        query = simulate_user_input("salut, peux-tu m'aider ?")
        simulate_ai_response(ai_model, query)
        
        # 10. Vérification que la mémoire est vide
        query = simulate_user_input("résume le guide python")
        simulate_ai_response(ai_model, query)
        
    except Exception as e:
        print(f"Erreur dans le workflow: {e}")

def workflow_error_handling():
    """Workflow de gestion d'erreurs et récupération."""
    print("\n\n⚠️ WORKFLOW: Gestion d'Erreurs")
    print("=" * 50)
    
    try:
        ai_engine = AIEngine()
        ai_model = ai_engine.ai_model
        
        # 1. Question normale
        query = simulate_user_input("bonjour")
        simulate_ai_response(ai_model, query)
        
        # 2. Question vide
        query = simulate_user_input("")
        response = ai_model.generate_response(query) if query else "Veuillez poser une question."
        print(f"🧠 IA: {response}")
        
        # 3. Question très longue
        long_query = "Peux-tu m'expliquer " + "très " * 100 + "en détail comment fonctionne Python ?"
        query = simulate_user_input(long_query[:50] + "... [question très longue]")
        simulate_ai_response(ai_model, long_query)
        
        # 4. Question avec caractères spéciaux
        query = simulate_user_input("Comment gérer les caractères spéciaux: é, à, ç, €, @, # ?")
        simulate_ai_response(ai_model, query)
        
        # 5. Récupération normale
        query = simulate_user_input("merci pour ton aide")
        simulate_ai_response(ai_model, query)
        
    except Exception as e:
        print(f"Erreur dans le workflow: {e}")

def main():
    """Fonction principale pour exécuter tous les workflows."""
    print("🎯 Démonstration des Workflows Complets")
    print("My Personal AI - 100% Local")
    print("=" * 60)
    print()
    print("Cette démonstration montre des scénarios d'utilisation réalistes")
    print("avec toutes les fonctionnalités de l'IA locale.")
    print()
    
    # Exécuter tous les workflows
    workflow_document_analysis()
    workflow_coding_assistance()
    workflow_mixed_session()
    workflow_error_handling()
    
    print("\n" + "=" * 60)
    print("✅ Tous les workflows ont été exécutés avec succès !")
    print()
    print("🔑 Points clés démontrés:")
    print("- Reconnaissance automatique des intentions")
    print("- Mémoire conversationnelle persistante")
    print("- Traitement de documents avec contexte")
    print("- Assistance au développement adaptative")
    print("- Gestion robuste des erreurs")
    print("- Fonctionnement 100% local et sécurisé")
    print()
    print("🚀 L'IA est prête pour vos propres projets !")

if __name__ == "__main__":
    main()
