#!/usr/bin/env python3
"""
🔍 Test de Validation des Imports - My_AI
Vérifie que tous les modules principaux peuvent être importés correctement
"""

import os
import subprocess
import sys
from pathlib import Path

# Ajout du path racine du projet
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def test_imports():
    """Teste tous les imports principaux"""

    results = {
        "success": [],
        "failed": []
    }

    tests = [
        ("core.ai_engine", "AIEngine"),
        ("models.custom_ai_model", "CustomAIModel"),
        ("models.conversation_memory", "ConversationMemory"),
        ("models.advanced_code_generator", "AdvancedCodeGenerator"),
        ("interfaces.gui_modern", "ModernAIGUI"),
        ("generators.document_generator", "DocumentGenerator"),
        ("generators.document_editor", "DocumentEditor"),
        ("generators.markdown_document", "parse_markdown"),
        ("generators.code_generator", "CodeGenerator"),
        ("processors.pdf_processor", "PDFProcessor"),
        ("processors.pptx_processor", "PPTXProcessor"),
        ("interfaces.document_preview", "build_document_preview"),
        ("utils.logger", "setup_logger"),
    ]

    print("\n🔍 TEST DE VALIDATION DES IMPORTS")
    print("=" * 60)

    for module_name, class_name in tests:
        try:
            module = __import__(module_name, fromlist=[class_name])
            getattr(module, class_name)
            results["success"].append(f"{module_name}.{class_name}")
            print(f"   ✅ {module_name}.{class_name}")
        except (ImportError, AttributeError) as e:
            results["failed"].append(f"{module_name}.{class_name}: {e}")
            print(f"   ❌ {module_name}.{class_name}: {e}")

    print("\n" + "=" * 60)
    print("📊 RÉSULTATS:")
    print(f"   ✅ Succès: {len(results['success'])}/{len(tests)}")
    print(f"   ❌ Échecs: {len(results['failed'])}/{len(tests)}")

    if results['failed']:
        print("\n⚠️ MODULES EN ÉCHEC:")
        for fail in results['failed']:
            print(f"   - {fail}")
    else:
        print("\n🎉 TOUS LES IMPORTS FONCTIONNENT !")
    # Un échec doit faire échouer pytest (un return False n'y produisait qu'un avertissement)
    assert not results['failed'], f"{len(results['failed'])} import(s) en échec"

def test_agents_package_imports_on_its_own():
    """interfaces.agents importé en premier, sans interfaces.gui : pas d'import circulaire.

    Interpréteur neuf : dans ce processus, interfaces.gui est souvent déjà
    chargé par d'autres tests, ce qui masquerait le cycle.
    """
    run = subprocess.run(
        [sys.executable, "-c", "import interfaces.agents"],
        cwd=project_root,
        capture_output=True,
        encoding="utf-8",
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
        timeout=300,
        check=False,
    )
    assert run.returncode == 0, run.stderr[-3000:]

if __name__ == "__main__":
    try:
        test_imports()
    except AssertionError:
        sys.exit(1)
