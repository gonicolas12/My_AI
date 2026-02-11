"""
Test rapide des nouvelles fonctionnalités
Vérifie que tout fonctionne correctement
"""

import sys
from pathlib import Path
import traceback

# Ajouter le projet au path AVANT les imports des modules locaux
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Imports locaux après l'ajustement du path
from core.rlhf_manager import get_rlhf_manager  # noqa: E402
from core.training_manager import get_training_manager  # noqa: E402
from core.compression_monitor import get_compression_monitor  # noqa: E402
from memory.vector_memory import VectorMemory  # noqa: E402


def test_rlhf_manager():
    """Test du RLHF Manager"""
    print("\n" + "=" * 60)
    print("🧪 TEST 1: RLHF Manager")
    print("=" * 60)

    try:
        rlhf = get_rlhf_manager()
        print("✅ Import réussi")

        # Test enregistrement
        interaction_id = rlhf.record_interaction(
            user_query="Test question",
            ai_response="Test response",
            feedback_type="positive",
            feedback_score=5,
        )
        print(f"✅ Interaction enregistrée (ID: {interaction_id})")

        # Test statistiques
        stats = rlhf.get_statistics("session")
        assert stats["total_interactions"] > 0
        print(
            f"✅ Statistiques récupérées ({stats['total_interactions']} interactions)"
        )

        # Test patterns
        patterns = rlhf.get_learned_patterns()
        print(f"✅ Patterns appris récupérés ({len(patterns)} patterns)")

        print("\n✅ RLHF Manager: TOUS LES TESTS PASSÉS")
        return True

    except Exception as e:
        print(f"\n❌ RLHF Manager: ÉCHEC - {e}")
        traceback.print_exc()
        return False


def test_training_manager():
    """Test du Training Manager"""
    print("\n" + "=" * 60)
    print("🧪 TEST 2: Training Manager")
    print("=" * 60)

    try:
        trainer = get_training_manager()
        print("✅ Import réussi")

        # Test création de run
        run_id = trainer.create_run(run_name="test_run", config={"test": True})
        assert run_id is not None
        print(f"✅ Run créé: {run_id}")

        # Test données d'entraînement
        train_data = [
            {"input": "test1", "target": "output1"},
            {"input": "test2", "target": "output2"},
        ] * 5

        # Test entraînement court
        results = trainer.train_model(
            train_data=train_data, epochs=1, batch_size=2, model_name="test_model"
        )
        assert results["final_loss"] is not None
        print(f"✅ Entraînement complété (Loss: {results['final_loss']:.4f})")

        # Test listage des runs
        runs = trainer.list_runs()
        assert len(runs) > 0
        print(f"✅ Runs listés ({len(runs)} runs)")

        print("\n✅ Training Manager: TOUS LES TESTS PASSÉS")
        return True

    except Exception as e:
        print(f"\n❌ Training Manager: ÉCHEC - {e}")
        traceback.print_exc()
        return False


def test_compression_monitor():
    """Test du Compression Monitor"""
    print("\n" + "=" * 60)
    print("🧪 TEST 3: Compression Monitor")
    print("=" * 60)

    try:
        monitor = get_compression_monitor()
        print("✅ Import réussi")

        # Test analyse
        text = "Test text " * 100
        chunks = ["Test text " * 25 for _ in range(4)]

        analysis = monitor.analyze_compression(
            original_text=text,
            chunks=chunks,
            document_name="test.txt",
            content_type="text",
        )

        assert "compression_ratio" in analysis
        assert "efficiency" in analysis
        assert "quality_score" in analysis
        print(
            f"✅ Analyse complétée (Ratio: {analysis['compression_ratio_formatted']})"
        )

        # Test statistiques
        stats = monitor.get_stats()
        assert stats["total_documents"] > 0
        print(f"✅ Statistiques récupérées ({stats['total_documents']} documents)")

        # Test rapport
        report = monitor.get_compression_report()
        assert len(report) > 0
        print(f"✅ Rapport généré ({len(report)} caractères)")

        print("\n✅ Compression Monitor: TOUS LES TESTS PASSÉS")
        return True

    except Exception as e:
        print(f"\n❌ Compression Monitor: ÉCHEC - {e}")
        traceback.print_exc()
        return False


def test_vector_memory_integration():
    """Test de l'intégration VectorMemory"""
    print("\n" + "=" * 60)
    print("🧪 TEST 4: VectorMemory + Compression")
    print("=" * 60)

    try:
        memory = VectorMemory(max_tokens=50000, chunk_size=256, enable_encryption=False)
        print("✅ VectorMemory créé")

        # Test ajout document
        test_content = "Python programming test content. " * 50
        result = memory.add_document(
            content=test_content,
            document_name="test_doc.txt",
            metadata={"type": "text"},
        )

        assert result["status"] == "success"
        print(f"✅ Document ajouté ({result['chunks_created']} chunks)")

        # Vérifier métriques de compression
        if "compression" in result:
            comp = result["compression"]
            assert "ratio_formatted" in comp
            print(f"✅ Compression intégrée (Ratio: {comp['ratio_formatted']})")
        else:
            print("⚠️  Compression Monitor non disponible (optionnel)")

        # Test stats
        stats = memory.get_stats()
        assert "current_tokens" in stats
        print(f"✅ Stats récupérées ({stats['current_tokens']} tokens)")

        # Test rapport
        try:
            report = memory.get_compression_report()
            if report and "RAPPORT" in report:
                print("✅ Rapport de compression disponible")
        except Exception:
            print("⚠️  Rapport de compression non disponible (optionnel)")

        print("\n✅ VectorMemory Integration: TOUS LES TESTS PASSÉS")
        return True

    except Exception as e:
        print(f"\n❌ VectorMemory Integration: ÉCHEC - {e}")
        traceback.print_exc()
        return False


def test_all():
    """Exécute tous les tests"""
    print("\n" + "=" * 60)
    print("🚀 SUITE DE TESTS - FONCTIONNALITÉS AVANCÉES")
    print("=" * 60)

    results = {
        "RLHF Manager": test_rlhf_manager(),
        "Training Manager": test_training_manager(),
        "Compression Monitor": test_compression_monitor(),
        "VectorMemory Integration": test_vector_memory_integration(),
    }

    print("\n" + "=" * 60)
    print("📊 RÉSUMÉ DES TESTS")
    print("=" * 60)

    passed = 0
    failed = 0

    for test_name, result in results.items():
        status = "✅ PASSÉ" if result else "❌ ÉCHOUÉ"
        print(f"{test_name}: {status}")
        if result:
            passed += 1
        else:
            failed += 1

    print("\n" + "=" * 60)
    print(f"Total: {passed} passé(s), {failed} échoué(s)")

    if failed == 0:
        print("\n🎉 TOUS LES TESTS SONT PASSÉS!")
        print("✅ Les nouvelles fonctionnalités sont opérationnelles")
    else:
        print(f"\n⚠️  {failed} test(s) ont échoué")
        print("Vérifiez les erreurs ci-dessus")

    print("=" * 60 + "\n")

    return failed == 0


if __name__ == "__main__":
    import argparse
    import os

    parser = argparse.ArgumentParser(description="Tests des fonctionnalités avancées")
    parser.add_argument(
        "--test",
        choices=["all", "rlhf", "training", "compression", "vector"],
        default="all",
        help="Test spécifique à lancer"
    )

    args = parser.parse_args()

    TEST_SUCCESS = False
    try:
        if args.test == "all":
            TEST_SUCCESS = test_all()
        elif args.test == "rlhf":
            TEST_SUCCESS = test_rlhf_manager()
        elif args.test == "training":
            TEST_SUCCESS = test_training_manager()
        elif args.test == "compression":
            TEST_SUCCESS = test_compression_monitor()
        elif args.test == "vector":
            TEST_SUCCESS = test_vector_memory_integration()
    finally:
        # Forcer le nettoyage des ressources pour éviter le blocage
        print("\n🧹 Nettoyage des ressources...")

        # Force l'exit immédiat
        os._exit(0 if TEST_SUCCESS else 1)
