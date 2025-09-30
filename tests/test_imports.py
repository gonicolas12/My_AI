#!/usr/bin/env python3
"""
🔍 Test de Validation des Imports - My_AI
Vérifie que tous les modules principaux peuvent être importés correctement
"""

import sys
import os
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
        ("models.ultra_custom_ai", "UltraCustomAIModel"),
        ("models.advanced_code_generator", "AdvancedCodeGenerator"),
        ("interfaces.gui_modern", "ModernAIGUI"),
        ("generators.document_generator", "DocumentGenerator"),
        ("generators.code_generator", "CodeGenerator"),
        ("processors.pdf_processor", "PDFProcessor"),
        ("utils.logger", "setup_logger"),
    ]

    print("🔍 TEST DE VALIDATION DES IMPORTS")
    print("=" * 60)

    for module_name, class_name in tests:
        try:
            module = __import__(module_name, fromlist=[class_name])
            getattr(module, class_name)
            results["success"].append(f"{module_name}.{class_name}")
            print(f"   ✅ {module_name}.{class_name}")
        except Exception as e:
            results["failed"].append(f"{module_name}.{class_name}: {e}")
            print(f"   ❌ {module_name}.{class_name}: {e}")

    print("\n" + "=" * 60)
    print(f"📊 RÉSULTATS:")
    print(f"   ✅ Succès: {len(results['success'])}/{len(tests)}")
    print(f"   ❌ Échecs: {len(results['failed'])}/{len(tests)}")

    if results['failed']:
        print("\n⚠️ MODULES EN ÉCHEC:")
        for fail in results['failed']:
            print(f"   - {fail}")
        return False
    else:
        print("\n🎉 TOUS LES IMPORTS FONCTIONNENT !")
        return True

if __name__ == "__main__":
    success = test_imports()
    sys.exit(0 if success else 1)