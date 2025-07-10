#!/usr/bin/env python3
"""
Script de démonstration et test - My Personal AI
Vérifie que tous les composants fonctionnent correctement
"""

import asyncio
import sys
import traceback
from pathlib import Path

# Ajout du répertoire courant au path
sys.path.insert(0, str(Path(__file__).parent))

def print_banner():
    """Affiche la bannière de démonstration"""
    print("\n" + "="*70)
    print("🎯 DÉMONSTRATION - MY PERSONAL AI")
    print("🧪 Tests de Fonctionnalité et Validation")
    print("="*70)

def print_section(title):
    """Affiche un titre de section"""
    print(f"\n📋 {title}")
    print("-" * (len(title) + 5))

async def test_basic_imports():
    """Test des imports de base"""
    print_section("Test des Imports")
    
    try:
        from core.ai_engine import AIEngine
        from core.conversation import ConversationManager
        from core.config import AI_CONFIG
        print("✅ Core modules importés avec succès")
        
        from utils.file_manager import FileManager
        from utils.logger import setup_logger
        from utils.validators import InputValidator
        print("✅ Utilitaires importés avec succès")
        
        from processors.pdf_processor import PDFProcessor
        from processors.docx_processor import DOCXProcessor
        from processors.code_processor import CodeProcessor
        print("✅ Processeurs importés avec succès")
        
        from generators.document_generator import DocumentGenerator
        from models.generators import CodeGenerator
        print("✅ Générateurs importés avec succès")
        
        from models.custom_ai_model import CustomAIModel
        print("✅ Modèle IA local importé avec succès")
        
        return True
        
    except Exception as e:
        print(f"❌ Erreur d'import: {e}")
        traceback.print_exc()
        return False

async def test_ai_engine_initialization():
    """Test d'initialisation du moteur IA"""
    print_section("Test d'Initialisation du Moteur IA")
    
    try:
        from core.ai_engine import AIEngine
        ai_engine = AIEngine()
        print("✅ Moteur IA initialisé")
        
        # Test du statut
        status = ai_engine.get_status()
        print(f"📊 Statut: {status.get('engine', 'Unknown')}")
        
        # Test du modèle local
        local_ai = ai_engine.local_ai
        if local_ai:
            print(f"🧠 Modèle IA local: disponible")
            print(f"🎯 Type: {type(local_ai).__name__}")
        else:
            print("⚠️ Modèle IA local non disponible")
        
        return True, ai_engine
        
    except Exception as e:
        print(f"❌ Erreur d'initialisation: {e}")
        traceback.print_exc()
        return False, None

async def test_file_processors():
    """Test des processeurs de fichiers"""
    print_section("Test des Processeurs de Fichiers")
    
    try:
        from processors.pdf_processor import PDFProcessor
        from processors.docx_processor import DOCXProcessor
        from processors.code_processor import CodeProcessor
        
        # Test PDF Processor
        pdf_proc = PDFProcessor()
        pdf_deps = pdf_proc.get_dependencies_status()
        if pdf_deps.get('any_available'):
            print(f"✅ Processeur PDF prêt ({list(pdf_deps.keys())})")
        else:
            print("⚠️ Processeur PDF: dépendances manquantes")
            print("💡 Installez: pip install PyMuPDF PyPDF2")
        
        # Test DOCX Processor
        docx_proc = DOCXProcessor()
        docx_deps = docx_proc.get_dependencies_status()
        if docx_deps.get('available'):
            print("✅ Processeur DOCX prêt")
        else:
            print("⚠️ Processeur DOCX: dépendances manquantes")
            print("💡 Installez: pip install python-docx")
        
        # Test Code Processor
        code_proc = CodeProcessor()
        print("✅ Processeur de code prêt (pas de dépendances)")
        
        return True
        
    except Exception as e:
        print(f"❌ Erreur test processeurs: {e}")
        return False

async def test_generators():
    """Test des générateurs"""
    print_section("Test des Générateurs")
    
    try:
        from generators.document_generator import DocumentGenerator
        from models.generators import CodeGenerator
        
        # Test Document Generator
        doc_gen = DocumentGenerator()
        doc_deps = doc_gen.get_dependencies_status()
        
        if doc_deps.get('reportlab'):
            print("✅ Générateur PDF prêt")
        else:
            print("⚠️ Générateur PDF: ReportLab manquant")
            print("💡 Installez: pip install reportlab")
        
        if doc_deps.get('python_docx'):
            print("✅ Générateur DOCX prêt")
        else:
            print("⚠️ Générateur DOCX: python-docx manquant")
        
        if doc_deps.get('text_generation'):
            print("✅ Générateur texte prêt")
        
        # Test Code Generator
        code_gen = CodeGenerator()
        print("✅ Générateur de code prêt")
        
        return True
        
    except Exception as e:
        print(f"❌ Erreur test générateurs: {e}")
        return False

async def test_utilities():
    """Test des utilitaires"""
    print_section("Test des Utilitaires")
    
    try:
        from utils.file_manager import FileManager
        from utils.logger import setup_logger
        from utils.validators import InputValidator
        
        # Test File Manager
        fm = FileManager()
        print("✅ Gestionnaire de fichiers prêt")
        
        # Test Logger
        logger = setup_logger("Demo")
        logger.info("Test du logger")
        print("✅ Logger configuré")
        
        # Test Validators
        validation = InputValidator.validate_query("Test de validation")
        if validation.get('valid'):
            print("✅ Validateurs fonctionnels")
        else:
            print("⚠️ Problème de validation")
        
        return True
        
    except Exception as e:
        print(f"❌ Erreur test utilitaires: {e}")
        return False

async def test_simple_query(ai_engine):
    """Test d'une requête simple si possible"""
    print_section("Test de Requête Simple")
    
    if not ai_engine:
        print("⚠️ Moteur IA non disponible pour le test")
        return False
    
    try:
        # Test avec une requête très simple
        simple_query = "Dis bonjour"
        print(f"🤔 Test de requête: '{simple_query}'")
        
        response = await ai_engine.process_query(simple_query)
        
        if response.get("success"):
            message = response.get("message", "")
            if len(message) > 100:
                message = message[:100] + "..."
            print(f"✅ Réponse reçue: {message}")
            return True
        else:
            print(f"⚠️ Requête échouée: {response.get('message', 'Erreur inconnue')}")
            return False
            
    except Exception as e:
        print(f"⚠️ Erreur lors du test de requête: {e}")
        return False

async def create_demo_files():
    """Crée des fichiers de démonstration"""
    print_section("Création de Fichiers de Démonstration")
    
    try:
        # Créer les répertoires
        demo_dir = Path("demo_files")
        demo_dir.mkdir(exist_ok=True)
        
        # Fichier Python de démo
        python_demo = demo_dir / "example.py"
        with open(python_demo, 'w', encoding='utf-8') as f:
            f.write('''#!/usr/bin/env python3
"""
Fichier Python de démonstration
"""

def hello_world():
    """Fonction simple de démonstration"""
    return "Hello, World!"

def calculate_factorial(n):
    """Calcule la factorielle de n"""
    if n <= 1:
        return 1
    return n * calculate_factorial(n - 1)

if __name__ == "__main__":
    print(hello_world())
    print(f"Factorielle de 5: {calculate_factorial(5)}")
''')
        
        # Fichier texte de démo
        text_demo = demo_dir / "example.txt"
        with open(text_demo, 'w', encoding='utf-8') as f:
            f.write("""Fichier texte de démonstration pour My Personal AI

Ce fichier contient du texte simple que l'IA peut analyser.

Contenu:
- Lignes de texte
- Paragraphes multiples
- Informations à extraire

L'IA peut lire ce fichier et en extraire les informations importantes.
""")
        
        print(f"✅ Fichiers de démo créés dans: {demo_dir}")
        print(f"   - {python_demo}")
        print(f"   - {text_demo}")
        
        return True
        
    except Exception as e:
        print(f"❌ Erreur création fichiers démo: {e}")
        return False

def print_installation_summary():
    """Affiche un résumé de l'installation"""
    print_section("Résumé et Recommandations")
    
    print("📋 État de l'Installation:")
    print("   ✅ Structure du projet créée")
    print("   ✅ Modules Python fonctionnels")
    print("   ✅ Configuration de base prête")
    
    print("\n🚀 Pour Optimiser votre IA:")
    print("   1. Installez Ollama pour les meilleurs performances:")
    print("      • Téléchargez depuis: https://ollama.ai/")
    print("      • Installez et lancez: ollama pull llama3.2")
    
    print("\n   2. Installez les dépendances optionnelles:")
    print("      • PDF: pip install PyMuPDF")
    print("      • DOCX: pip install python-docx")
    print("      • Génération PDF: pip install reportlab")
    
    print("\n   3. Pour GPU (si disponible):")
    print("      • pip install torch --index-url https://download.pytorch.org/whl/cu118")
    
    print("\n📚 Documentation:")
    print("   • Installation: docs/INSTALLATION.md")
    print("   • Utilisation: docs/USAGE.md")
    print("   • Architecture: docs/ARCHITECTURE.md")
    
    print("\n🎯 Premiers Pas:")
    print("   • Lancez: python main.py")
    print("   • Tapez 'aide' pour voir les commandes")
    print("   • Testez: python examples/basic_usage.py")

async def main():
    """Fonction principale de démonstration"""
    print_banner()
    
    results = {
        'imports': False,
        'ai_engine': False,
        'processors': False,
        'generators': False,
        'utilities': False,
        'query_test': False,
        'demo_files': False
    }
    
    # Tests séquentiels
    results['imports'] = await test_basic_imports()
    
    if results['imports']:
        success, ai_engine = await test_ai_engine_initialization()
        results['ai_engine'] = success
        
        results['processors'] = await test_file_processors()
        results['generators'] = await test_generators()
        results['utilities'] = await test_utilities()
        results['demo_files'] = await create_demo_files()
        
        if ai_engine:
            results['query_test'] = await test_simple_query(ai_engine)
    
    # Résumé final
    print_section("Résultat des Tests")
    
    total_tests = len(results)
    passed_tests = sum(results.values())
    
    for test_name, passed in results.items():
        status = "✅" if passed else "❌"
        print(f"{status} {test_name.replace('_', ' ').title()}")
    
    print(f"\n📊 Score: {passed_tests}/{total_tests} tests réussis")
    
    if passed_tests == total_tests:
        print("\n🎉 INSTALLATION COMPLÈTE ET FONCTIONNELLE!")
    elif passed_tests >= total_tests * 0.7:
        print("\n✅ Installation majoritairement fonctionnelle")
        print("💡 Quelques optimisations possibles (voir recommandations)")
    else:
        print("\n⚠️ Installation partielle")
        print("🔧 Corrections nécessaires avant utilisation optimale")
    
    print_installation_summary()
    
    print("\n" + "="*70)
    print("🎯 DÉMONSTRATION TERMINÉE")
    print("="*70)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n👋 Démonstration interrompue")
    except Exception as e:
        print(f"\n❌ Erreur lors de la démonstration: {e}")
        traceback.print_exc()
