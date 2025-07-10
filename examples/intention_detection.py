#!/usr/bin/env python3
"""
Exemple d'utilisation de la reconnaissance d'intentions - My Personal AI

Ce script démontre comment l'IA locale reconnaît automatiquement
les différents types d'intentions et adapte ses réponses.
"""

import sys
import os

# Ajouter le répertoire parent au chemin Python
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.ai_engine import AIEngine
from models.custom_ai_model import CustomAIModel
from models.linguistic_patterns import LinguisticPatterns

def test_greeting_detection():
    """Test de la détection des salutations."""
    print("🔍 Test de détection des salutations")
    print("=" * 50)
    
    patterns = LinguisticPatterns()
    
    greetings = [
        "slt",
        "salut", 
        "bonjour",
        "bjr",
        "hello",
        "bonsoir",
        "coucou",
        "yo"
    ]
    
    for greeting in greetings:
        intention = patterns.detect_intention(greeting)
        print(f"'{greeting}' -> Intention: {intention}")
    
    print()

def test_code_questions():
    """Test de la détection des questions de code."""
    print("💻 Test de détection des questions de code")
    print("=" * 50)
    
    patterns = LinguisticPatterns()
    
    code_questions = [
        "Comment créer une fonction en Python ?",
        "Explique les décorateurs Python",
        "Comment déboguer ce code ?",
        "Quelle est la syntaxe des listes ?",
        "Comment gérer les exceptions ?",
        "Optimise cette fonction",
        "Bug dans mon script Python"
    ]
    
    for question in code_questions:
        intention = patterns.detect_intention(question)
        print(f"'{question}' -> Intention: {intention}")
    
    print()

def test_document_questions():
    """Test de la détection des questions sur documents."""
    print("📄 Test de détection des questions sur documents")
    print("=" * 50)
    
    patterns = LinguisticPatterns()
    
    doc_questions = [
        "résume ce document",
        "que dit le PDF ?",
        "analyse le rapport",
        "extrait les points clés",
        "résume le fichier DOCX",
        "que contient ce document ?",
        "points importants du rapport"
    ]
    
    for question in doc_questions:
        intention = patterns.detect_intention(question)
        print(f"'{question}' -> Intention: {intention}")
    
    print()

def test_general_questions():
    """Test de la détection des questions générales."""
    print("💬 Test de détection des questions générales")
    print("=" * 50)
    
    patterns = LinguisticPatterns()
    
    general_questions = [
        "Comment vas-tu ?",
        "Quel temps fait-il ?",
        "Raconte-moi une histoire",
        "Que penses-tu de l'IA ?",
        "Aide-moi avec un problème",
        "J'ai besoin de conseils",
        "Peux-tu m'expliquer quelque chose ?"
    ]
    
    for question in general_questions:
        intention = patterns.detect_intention(question)
        print(f"'{question}' -> Intention: {intention}")
    
    print()

def test_ai_responses():
    """Test des réponses adaptatives de l'IA."""
    print("🤖 Test des réponses adaptatives de l'IA")
    print("=" * 50)
    
    try:
        # Initialiser l'IA
        ai_engine = AIEngine()
        ai_model = ai_engine.ai_model
        
        test_cases = [
            ("slt", "Salutation"),
            ("Comment créer une liste en Python ?", "Question technique"),
            ("résume le document", "Question sur document"),
            ("Comment vas-tu ?", "Question générale")
        ]
        
        for query, description in test_cases:
            print(f"\n📝 Test: {description}")
            print(f"Question: '{query}'")
            
            # Obtenir la réponse de l'IA
            response = ai_model.generate_response(query)
            print(f"Réponse: {response[:100]}...")
            
    except Exception as e:
        print(f"Erreur lors du test de l'IA: {e}")
        print("Note: Assurez-vous que l'IA est correctement configurée.")

def demonstrate_memory_persistence():
    """Démonstration de la persistance de la mémoire."""
    print("🧠 Démonstration de la mémoire conversationnelle")
    print("=" * 50)
    
    try:
        ai_engine = AIEngine()
        ai_model = ai_engine.ai_model
        
        # Simulation d'un document traité
        print("1. Simulation du traitement d'un document...")
        ai_model.memory.store_document_content("test_document.pdf", "Contenu test du document PDF avec informations importantes.")
        
        # Vérification de la mémoire
        print("2. Vérification de la mémoire...")
        doc_content = ai_model.memory.get_document_content("test_document.pdf")
        print(f"Document en mémoire: {doc_content[:50]}...")
        
        # Question sur le document
        print("3. Question sur le document...")
        response = ai_model.generate_response("que contient test_document.pdf ?")
        print(f"Réponse: {response[:100]}...")
        
        # Simulation de stockage de code
        print("4. Simulation du stockage de code...")
        code_content = "def hello_world():\n    print('Hello, World!')"
        ai_model.memory.store_code_content("example_function", code_content)
        
        # Question sur le code
        print("5. Question sur le code...")
        response = ai_model.generate_response("explique la fonction hello_world")
        print(f"Réponse: {response[:100]}...")
        
    except Exception as e:
        print(f"Erreur lors de la démonstration: {e}")

def main():
    """Fonction principale pour tester la reconnaissance d'intentions."""
    print("🎯 Démonstration de la Reconnaissance d'Intentions")
    print("My Personal AI - 100% Local")
    print("=" * 60)
    print()
    
    # Tests des différents types d'intentions
    test_greeting_detection()
    test_code_questions()
    test_document_questions()
    test_general_questions()
    
    # Test des réponses adaptatives
    test_ai_responses()
    
    # Démonstration de la mémoire
    demonstrate_memory_persistence()
    
    print("\n✅ Démonstration terminée !")
    print("\nPoints clés:")
    print("- L'IA reconnaît automatiquement le type de votre requête")
    print("- Les réponses sont adaptées à l'intention détectée")
    print("- La mémoire conversationnelle conserve le contexte")
    print("- Tout fonctionne 100% localement, sans services externes")

if __name__ == "__main__":
    main()
