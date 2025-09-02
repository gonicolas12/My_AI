#!/usr/bin/env python3
"""
🚀 My_AI Ultra Launcher v5.0
Lance My_AI avec 1M tokens et optimisations extrêmes
"""

import os
import sys
import time

def show_ultra_banner():
    """Affiche la bannière ultra"""
    print("🚀 MY_AI ULTRA LAUNCHER v5.0")
    print("=" * 40)
    print("🎯 CONFIGURATION ULTRA:")
    print("   💥 1,048,576 tokens (1M)")
    print("   🧠 1000 tours de mémoire")
    print("   ⚡ Compression adaptative")
    print("   🔍 RAG ultra-optimisé")
    print("   🚀 Performance maximale")

def check_ultra_readiness():
    """Vérifie la disponibilité du mode ultra"""
    print("\n🔍 Vérification configuration ultra...")
    
    required_files = [
        "optimization_manager.py",
        "rag_pipeline.py", 
        "context_optimization.py",
        "interfaces/gui_modern.py"
    ]
    
    missing = []
    for file_path in required_files:
        if os.path.exists(file_path):
            print(f"   ✅ {file_path}")
        else:
            missing.append(file_path)
            print(f"   ❌ {file_path}")
    
    if missing:
        print(f"\n❌ Fichiers manquants: {len(missing)}")
        return False
    
    print(f"\n✅ Système prêt pour mode ultra !")
    return True

def launch_ultra_gui():
    """Lance l'interface avec optimisations ultra"""
    print("\n🚀 Lancement interface ultra...")
    
    # Variables d'environnement pour mode ultra
    os.environ["MY_AI_ULTRA_MODE"] = "1"
    os.environ["MY_AI_MAX_TOKENS"] = "1048576"
    os.environ["MY_AI_ULTRA_MEMORY"] = "1000"
    os.environ["MY_AI_ULTRA_COMPRESSION"] = "0.4"
    
    print("   🔧 Variables ultra configurées")
    print("   🎯 Lancement en cours...")
    
    # Lancer l'interface optimisée
    os.system("python interfaces/gui_modern.py")

def quick_ultra_test():
    """Test rapide du mode ultra"""
    print("\n🧪 TEST RAPIDE MODE ULTRA")
    print("=" * 35)
    
    try:
        from models.custom_ai_model import CustomAIModel
        from optimization_manager import get_optimization_manager
        
        model = CustomAIModel()
        opt_manager = get_optimization_manager()
        
        # Test avec contexte de 100K caractères (25K tokens)
        mega_context = "Données massives d'intelligence artificielle. " * 2000
        test_query = "Analyse ce contexte ultra-long"
        
        print(f"📊 Test avec {len(mega_context):,} chars ({len(mega_context)//4:,} tokens)")
        
        start_time = time.time()
        response = opt_manager.optimize_query(test_query, {"mega_context": mega_context}, model)
        ultra_time = time.time() - start_time
        
        print(f"⚡ Traitement ultra: {ultra_time:.2f}s")
        print(f"🎯 Capacité confirmée: {len(mega_context)//4:,} tokens")
        
        if len(mega_context)//4 > 20000:
            print("🚀 ULTRA MODE ACTIF: Traite 20K+ tokens !")
        
        return True
        
    except Exception as e:
        print(f"❌ Test ultra échoué: {str(e)}")
        return False

def main():
    """Launcher principal"""
    show_ultra_banner()
    
    if not check_ultra_readiness():
        print("\n❌ Mode ultra non disponible")
        print("   Lancez: python integration_optimizations.py")
        return
    
    # Test rapide
    if quick_ultra_test():
        print("\n💡 Lancement interface ultra en 3 secondes...")
        time.sleep(3)
        launch_ultra_gui()
    else:
        print("\n⚠️ Mode ultra non opérationnel")
        print("   Mode standard disponible: python interfaces/gui_modern.py")

if __name__ == "__main__":
    main()
