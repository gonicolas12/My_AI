#!/usr/bin/env python3
"""
Lancement simplifié de l'assistant IA local
Mode entreprise : 100% local, aucune dépendance externe
"""

import sys
import os
from pathlib import Path

# Ajouter le dossier racine au path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def launch_gui_simple():
    """Lance l'interface graphique en mode simplifié"""
    print("🚀 Lancement de l'Assistant IA Local (Mode Entreprise)")
    print("=" * 60)
    print("✅ Mode 100% local activé")
    print("✅ Aucune donnée ne sera envoyée à l'extérieur")
    print("✅ Utilisation du modèle IA personnalisé uniquement")
    print("-" * 60)
    
    try:
        # Import direct de l'interface GUI
        from interfaces.gui_simple import SimpleAIGUI
        
        # Lancement
        app = SimpleAIGUI()
        app.run()
        
    except ImportError:
        # Fallback sur l'interface standard
        print("📱 Chargement de l'interface principale...")
        try:
            from interfaces.gui import AIAssistantGUI
            
            # Créer et lancer l'interface
            app = AIAssistantGUI()
            app.run()
            
        except Exception as e:
            print(f"❌ Erreur de lancement de l'interface : {e}")
            print("\n💡 Solutions possibles :")
            print("1. Installez tkinter : pip install tk")
            print("2. Vérifiez votre installation Python")
            print("3. Utilisez le mode console : python console_interface.py")
            
            # Lancement en mode console
            launch_console()

def launch_console():
    """Lance l'interface console"""
    print("\n🖥️  Lancement en mode console...")
    
    try:
        from core.ai_engine import AIEngine
        
        ai_engine = AIEngine()
        
        print("\n🤖 Assistant IA Local - Mode Console")
        print("Tapez 'quit' ou 'exit' pour quitter")
        print("Tapez 'help' pour l'aide")
        print("-" * 40)
        
        while True:
            try:
                user_input = input("\n👤 Vous : ").strip()
                
                if user_input.lower() in ['quit', 'exit', 'q']:
                    print("👋 Au revoir !")
                    break
                
                if not user_input:
                    continue
                
                # Traitement de la requête
                response = ai_engine.process_text(user_input)
                print(f"\n🤖 Assistant : {response}")
                
            except KeyboardInterrupt:
                print("\n\n👋 Au revoir !")
                break
            except Exception as e:
                print(f"❌ Erreur : {e}")
                
    except Exception as e:
        print(f"❌ Impossible de lancer l'assistant : {e}")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Assistant IA Local - Mode Entreprise")
    parser.add_argument('--console', action='store_true', help='Lancer en mode console')
    
    args = parser.parse_args()
    
    if args.console:
        launch_console()
    else:
        launch_gui_simple()
