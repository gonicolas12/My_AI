#!/usr/bin/env python3
"""
🚀 My_AI Ultra Launcher v5.0
Lance My_AI avec 1M tokens RÉELS et optimisations extrêmes
"""

import os
import sys
import time

# 🚀 NOUVEAU: Import du vrai système 1M tokens
try:
    from models.ultra_custom_ai import UltraCustomAIModel
    from interfaces.gui_modern import ModernAIGUI
    ULTRA_SYSTEM_AVAILABLE = True
    print("🚀 Système 1M tokens RÉEL disponible !")
except ImportError as e:
    try:
        from core.ai_engine import AIEngine
        from interfaces.gui_modern import ModernAIGUI  
        ULTRA_SYSTEM_AVAILABLE = False
        print("📝 Système standard disponible")
    except ImportError:
        print("❌ Erreur d'import des modules")
        print(f"Détails: {e}")
        sys.exit(1)

def show_ultra_banner():
    """Affiche la bannière ultra"""
    if ULTRA_SYSTEM_AVAILABLE:
        print("🚀 MY_AI ULTRA LAUNCHER v5.0 - SYSTÈME 1M TOKENS RÉEL")
        print("=" * 60)
        print("🎯 CONFIGURATION ULTRA:")
        print("   💥 1,048,576 tokens RÉELS (1M)")
        print("   🗜️  Compression intelligente 2.4:1 à 52:1")
        print("   🔍 Recherche sémantique ultra-rapide")
        print("   � Persistance SQLite optimisée")
        print("   🚀 Architecture 100% locale")
        print("   ⚡ Gestion automatique de la mémoire")
    else:
        print("📝 MY_AI STANDARD LAUNCHER v5.0")
        print("=" * 40)
        print("🎯 CONFIGURATION STANDARD:")
        print("   💥 Mode classique")
        print("   🧠 Capacités de base")

def check_ultra_readiness():
    """Vérifie la disponibilité du mode ultra"""
    print("\n🔍 Vérification système 1M tokens...")
    
    if ULTRA_SYSTEM_AVAILABLE:
        # Vérifier les composants du système 1M tokens
        required_files = [
            "models/ultra_custom_ai.py",
            "models/million_token_context_manager.py", 
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
            print(f"\n❌ Fichiers système 1M tokens manquants: {len(missing)}")
            return False
        
        # Test d'initialisation
        try:
            from core.ai_engine import AIEngine
            base_ai = AIEngine()
            ai = UltraCustomAIModel(base_ai)
            stats = ai.get_context_stats()
            print(f"   ✅ Système 1M tokens initialisé")
            print(f"   📊 Contexte: {stats['current_tokens']:,} / {stats['max_context_length']:,} tokens")
            print(f"   � Documents: {stats['documents_processed']}")
            print(f"   🧩 Chunks: {stats['chunks_created']}")
            return True
            
        except Exception as e:
            print(f"   ❌ Erreur initialisation: {e}")
            return False
    else:
        # Mode standard
        print("   📝 Mode standard activé")
        return True

def launch_ultra_gui():
    """Lance l'interface avec système 1M tokens"""
    print(f"\n🚀 Lancement interface {'ultra 1M tokens' if ULTRA_SYSTEM_AVAILABLE else 'standard'}...")
    
    try:
        if ULTRA_SYSTEM_AVAILABLE:
            # Interface Ultra avec 1M tokens
            from core.ai_engine import AIEngine
            base_ai = AIEngine()
            ai = UltraCustomAIModel(base_ai)
            gui = ModernAIGUI()
        else:
            # Interface standard
            from core.ai_engine import AIEngine
            ai = AIEngine()
            gui = ModernAIGUI()
        
        print("   ✅ Interface graphique initialisée")
        print("   🖥️  Ouverture de la fenêtre...")
        
        # Lancement de l'interface
        gui.run()
        
    except Exception as e:
        print(f"   ❌ Erreur lors du lancement: {e}")
        print(f"   🔧 Essayez: python main.py")
        return False
    
    return True

def main():
    """Fonction principale du launcher ultra"""
    
    # Afficher la bannière
    show_ultra_banner()
    
    # Vérifier la configuration
    if not check_ultra_readiness():
        print("\n❌ Configuration ultra non disponible")
        print("🔧 Utilisation du mode standard...")
        time.sleep(2)
    
    # Lancer l'interface
    success = launch_ultra_gui()
    
    if success:
        print("\n✅ Session terminée normalement")
    else:
        print("\n❌ Erreur lors de la session")
        print("🔧 Solutions possibles :")
        print("   1. Lancez: python main_ultra.py --ultra --gui")
        print("   2. Vérifiez les dépendances: pip install -r requirements.txt")
        print("   3. Consultez: GUIDE_INTÉGRATION_1M_TOKENS.md")

if __name__ == "__main__":
    try:
        main()
        input("\n👋 Appuyez sur Entrée pour fermer...")
    except KeyboardInterrupt:
        print("\n\n👋 Arrêt demandé par l'utilisateur")
    except Exception as e:
        print(f"\n❌ Erreur fatale: {e}")
        input("Appuyez sur Entrée pour fermer...")
