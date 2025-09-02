#!/usr/bin/env python3
'''🎊 My_AI Ultra - Lanceur Final Simple'''

import subprocess
import sys
import os

def main():
    print("🎊 MY_AI ULTRA v6.0")
    print("🎯 1 Million de tokens disponibles")
    print("=" * 40)
    
    print("\nChoisissez votre interface:")
    print("1. 🚀 Interface Ultra (1M tokens)")
    print("2. 🎮 Menu de démarrage")
    print("3. 🧪 Test complet")
    
    try:
        choice = input("\nChoix (1-3) ou Entrée pour Ultra: ").strip()
        
        if choice == "" or choice == "1":
            print("🚀 Lancement interface ultra...")
            subprocess.run([sys.executable, "launch_ultra.py"])
        elif choice == "2":
            print("🎮 Lancement menu...")
            subprocess.run([sys.executable, "start_ultra.py"])
        elif choice == "3":
            print("🧪 Test complet...")
            subprocess.run([sys.executable, "test_final_ultra.py"])
        else:
            print("🚀 Lancement par défaut...")
            subprocess.run([sys.executable, "launch_ultra.py"])
            
    except KeyboardInterrupt:
        print("\n👋 Au revoir !")
    except Exception as e:
        print(f"❌ Erreur: {e}")

if __name__ == "__main__":
    main()
