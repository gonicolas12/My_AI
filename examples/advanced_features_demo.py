"""
Exemples d'utilisation des nouvelles fonctionnalités:
- RLHF Manager
- Training Manager
- Compression Monitor
"""

import sys
from pathlib import Path
import traceback

# Ajouter le projet au path AVANT les imports des modules locaux
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Imports locaux après l'ajustement du path
from core.rlhf_manager import get_rlhf_manager
from core.training_manager import get_training_manager
from core.compression_monitor import get_compression_monitor
from memory.vector_memory import VectorMemory


def example_rlhf():
    """Exemple d'utilisation du RLHF Manager"""
    print("\n" + "=" * 70)
    print("📚 EXEMPLE 1: RLHF Manager")
    print("=" * 70 + "\n")

    # Obtenir l'instance
    rlhf = get_rlhf_manager()

    # Enregistrer des interactions avec feedback
    print("📝 Enregistrement d'interactions...")

    interaction_id = rlhf.record_interaction(
        user_query="Comment installer Python ?",
        ai_response="Pour installer Python, rendez-vous sur python.org et téléchargez la dernière version...",
        feedback_type="positive",
        feedback_score=5,
        intent="technical_question",
        confidence=0.9,
        model_version="llama3.2",
    )

    print(f"✅ Interaction enregistrée (ID: {interaction_id})")

    # Ajouter plus d'interactions
    rlhf.record_interaction(
        user_query="Qu'est-ce qu'une liste en Python ?",
        ai_response="Une liste est une structure de données...",
        feedback_type="positive",
        feedback_score=4,
        intent="technical_question",
        confidence=0.85,
    )

    rlhf.record_interaction(
        user_query="Comment faire une boucle ?",
        ai_response="Utilisez for ou while...",
        feedback_type="negative",
        feedback_score=2,
        feedback_comment="Réponse trop vague",
        intent="code_help",
    )

    # Obtenir les statistiques
    print("\n📊 Statistiques RLHF:")
    stats = rlhf.get_statistics("session")

    for key, value in stats.items():
        print(f"   {key}: {value}")

    # Voir les patterns appris
    print("\n🧠 Patterns appris:")
    patterns = rlhf.get_learned_patterns(min_confidence=0.5)

    for pattern in patterns[:5]:  # Top 5
        print(
            f"   - {pattern['pattern_type']}: {pattern['user_query_pattern'][:50]}... "
            f"(confiance: {pattern['confidence']:.2f})"
        )

    # Exporter les données d'entraînement
    print("\n💾 Export des données d'entraînement...")
    count = rlhf.export_training_data("data/rlhf_training_data.jsonl", min_score=3)
    print(f"✅ {count} exemples exportés")


def example_training():
    """Exemple d'utilisation du Training Manager"""
    print("\n" + "=" * 70)
    print("🎓 EXEMPLE 2: Training Manager")
    print("=" * 70 + "\n")

    # Obtenir l'instance
    trainer = get_training_manager()

    # Données d'entraînement d'exemple
    train_data = [
        {
            "input": "Qu'est-ce que Python ?",
            "target": "Python est un langage de programmation...",
        },
        {
            "input": "Comment utiliser les listes ?",
            "target": "Les listes en Python se définissent avec []...",
        },
        {
            "input": "Qu'est-ce qu'une fonction ?",
            "target": "Une fonction est un bloc de code réutilisable...",
        },
        # ... plus de données
    ] * 10  # Simuler plus de données

    val_data = [
        {
            "input": "Qu'est-ce qu'une variable ?",
            "target": "Une variable est un conteneur...",
        },
        {
            "input": "Comment faire une boucle ?",
            "target": "En Python, utilisez for ou while...",
        },
    ] * 5

    print(
        f"📚 Données: {len(train_data)} exemples d'entraînement, {len(val_data)} validation"
    )

    # Créer un run
    run_id = trainer.create_run(
        run_name="python_basics",
        config={
            "description": "Entraînement sur les bases de Python",
            "model_type": "custom",
        },
    )

    print(f"🚀 Run créé: {run_id}")

    # Fonction callback pour suivre la progression
    def on_epoch_end(epoch, metrics):
        print(f"\n   ✨ Époque {epoch + 1} terminée!")
        print(f"      Loss: {metrics['train_loss']:.4f}")
        if "val_loss" in metrics:
            print(f"      Val Loss: {metrics['val_loss']:.4f}")

    # Entraîner le modèle
    print("\n🎯 Démarrage de l'entraînement...\n")

    results = trainer.train_model(
        train_data=train_data,
        val_data=val_data,
        epochs=3,
        batch_size=8,
        model_name="python_assistant",
        on_epoch_end=on_epoch_end,
    )

    print("\n✅ Entraînement terminé!")
    print(f"   📊 Loss finale: {results['final_loss']:.4f}")
    print(f"   📁 Résultats sauvegardés dans: {results['run_id']}")

    # Lister tous les runs
    print("\n📋 Runs d'entraînement disponibles:")
    runs = trainer.list_runs()

    for run in runs[:3]:  # Afficher les 3 derniers
        print(f"   - {run['run_id']}: {run.get('total_epochs', 0)} époques")


def example_fine_tune_ollama():
    """Exemple de fine-tuning pour Ollama"""
    print("\n" + "=" * 70)
    print("🦙 EXEMPLE 3: Fine-tuning Ollama")
    print("=" * 70 + "\n")

    trainer = get_training_manager()

    # Créer un run pour Ollama
    trainer.create_run(
        run_name="ollama_finetune",
        config={"base_model": "llama3.2", "target": "Custom AI Assistant"},
    )

    # Données de fine-tuning
    train_data = [
        {
            "input": "Qui es-tu ?",
            "target": "Je suis My AI, ton assistant IA personnel et local.",
        },
        {
            "input": "Que peux-tu faire ?",
            "target": "Je peux t'aider avec du code, des documents, des recherches...",
        },
        {
            "input": "Es-tu disponible hors ligne ?",
            "target": "Oui! Je fonctionne 100% localement sans internet.",
        },
    ] * 20

    print(f"📚 {len(train_data)} exemples pour le fine-tuning")

    # Préparer le fine-tuning
    result = trainer.fine_tune_ollama_model(
        base_model="llama3.2",
        train_data=train_data,
        new_model_name="my_ai_custom",
        epochs=5,
    )

    print("\n✅ Préparation terminée!")
    print(f"   📝 Modelfile: {result['modelfile_path']}")
    print(f"   📚 Données: {result['train_data_path']}")
    print(f"   📋 Instructions: {result['instructions_path']}")
    print(f"\n💡 Consultez {result['instructions_path']} pour créer le modèle")


def example_compression():
    """Exemple d'utilisation du Compression Monitor"""
    print("\n" + "=" * 70)
    print("📊 EXEMPLE 4: Compression Monitor")
    print("=" * 70 + "\n")

    # Obtenir l'instance
    monitor = get_compression_monitor()

    # Textes d'exemple de différents types
    text_code = (
        '''
def fibonacci(n):
    """Calcule la suite de Fibonacci"""
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)

# Test
for i in range(10):
    print(f"F({i}) = {fibonacci(i)}")
    '''
        * 20
    )  # Répéter pour avoir plus de contenu

    text_document = (
        """
Introduction à l'Intelligence Artificielle
L'intelligence artificielle (IA) est un domaine de l'informatique qui vise à créer
des systèmes capables d'effectuer des tâches nécessitant normalement l'intelligence humaine.
    """
        * 30
    )

    text_data = "data,value,category\n" + ("item,100,A\n" * 100)

    # Analyser différents types de contenu
    print("🔍 Analyse de compression...\n")

    # Simuler le chunking
    def simple_chunk(text, size=256):
        words = text.split()
        chunks = []
        for i in range(0, len(words), size):
            chunks.append(" ".join(words[i : i + size]))
        return chunks

    # Code
    code_chunks = simple_chunk(text_code)
    code_analysis = monitor.analyze_compression(
        text_code, code_chunks, "fibonacci.py", "code"
    )

    print("📄 Code Python:")
    print(f"   Ratio: {code_analysis['compression_ratio_formatted']}")
    print(f"   Efficacité: {code_analysis['efficiency']:.1f}%")
    print(f"   Qualité: {code_analysis['quality_score']:.1f}/100")

    # Document
    doc_chunks = simple_chunk(text_document)
    doc_analysis = monitor.analyze_compression(
        text_document, doc_chunks, "intro_ia.txt", "text"
    )

    print("\n📝 Document texte:")
    print(f"   Ratio: {doc_analysis['compression_ratio_formatted']}")
    print(f"   Efficacité: {doc_analysis['efficiency']:.1f}%")
    print(f"   Qualité: {doc_analysis['quality_score']:.1f}/100")

    # Données
    data_chunks = simple_chunk(text_data)
    data_analysis = monitor.analyze_compression(
        text_data, data_chunks, "data.csv", "data"
    )

    print("\n📊 Données CSV:")
    print(f"   Ratio: {data_analysis['compression_ratio_formatted']}")
    print(f"   Efficacité: {data_analysis['efficiency']:.1f}%")
    print(f"   Qualité: {data_analysis['quality_score']:.1f}/100")

    # Statistiques globales
    print("\n📈 Statistiques globales:")
    stats = monitor.get_stats()

    print(f"   Documents traités: {stats['total_documents']}")
    print(f"   Ratio moyen: {stats['average_ratio_formatted']}")
    print(f"   Meilleur ratio: {stats['best_ratio_formatted']}")
    print(f"   Espace économisé: {stats['space_saved_percent']:.1f}%")

    # Rapport détaillé
    print("\n" + "=" * 70)
    print(monitor.get_compression_report())


def example_vector_memory_with_compression():
    """Exemple d'utilisation de VectorMemory avec monitoring de compression"""
    print("\n" + "=" * 70)
    print("🧠 EXEMPLE 5: VectorMemory avec Compression Monitor")
    print("=" * 70 + "\n")

    # Créer instance avec monitoring
    memory = VectorMemory(
        max_tokens=100000, chunk_size=256, chunk_overlap=50, enable_encryption=False
    )

    # Ajouter des documents
    test_content = (
        "Python est un langage de programmation puissant et polyvalent. " * 100
    )

    print("📥 Ajout de document...")
    result = memory.add_document(
        content=test_content,
        document_name="python_intro.txt",
        metadata={"type": "text", "category": "tutorial"},
    )

    print("\n✅ Document ajouté:")
    print(f"   ID: {result['document_id']}")
    print(f"   Chunks créés: {result['chunks_created']}")
    print(f"   Tokens: {result['tokens_added']}")

    if "compression" in result:
        comp = result["compression"]
        print("\n📊 Métriques de compression:")
        print(f"   Ratio: {comp['ratio_formatted']}")
        print(f"   Efficacité: {comp['efficiency']:.1f}%")
        print(f"   Score qualité: {comp['quality_score']:.1f}/100")

    # Statistiques complètes
    print("\n📈 Statistiques VectorMemory:")
    stats = memory.get_stats()

    print(f"   Documents: {stats['documents_count']}")
    print(f"   Tokens utilisés: {stats['current_tokens']:,} / {stats['max_tokens']:,}")
    print(f"   Usage: {stats['usage_percent']:.1f}%")

    if "compression" in stats:
        print("\n   📊 Compression:")
        print(f"      Ratio moyen: {stats['compression']['average_ratio_formatted']}")
        print(f"      Meilleur ratio: {stats['compression']['best_ratio_formatted']}")

    # Rapport de compression
    print("\n" + memory.get_compression_report())


def main():
    """Exécute tous les exemples"""
    print("\n🚀 EXEMPLES D'UTILISATION - NOUVELLES FONCTIONNALITÉS")
    print("=" * 70)

    try:
        # Exemple 1: RLHF
        example_rlhf()

        # Exemple 2: Training
        example_training()

        # Exemple 3: Fine-tuning Ollama
        example_fine_tune_ollama()

        # Exemple 4: Compression
        example_compression()

        # Exemple 5: VectorMemory avec compression
        example_vector_memory_with_compression()

        print("\n" + "=" * 70)
        print("✅ TOUS LES EXEMPLES TERMINÉS!")
        print("=" * 70)

    except Exception as e:
        print(f"\n❌ Erreur: {e}")
        traceback.print_exc()


if __name__ == "__main__":
    import os

    try:
        main()
    finally:
        # Forcer le nettoyage des ressources pour éviter le blocage
        print("\n🧹 Nettoyage des ressources...")
        # Force l'exit immédiat
        os._exit(0)
