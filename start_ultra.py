#!/usr/bin/env python3
'''🚀 My_AI Ultra - Démarrage Simple'''

import subprocess
import sys

def main():
    print("🎊 My_AI Ultra - Démarrage")
    print("🎯 Capacité: 1M tokens")
    
    choice = input("\nChoisissez:\n1. Interface Ultra\n2. Test Complet\n3. Audit\nChoix (1-3): ")
    
    if choice == "1":
        subprocess.run([sys.executable, "launch_ultra.py"])
    elif choice == "2":
        subprocess.run([sys.executable, "test_final_ultra.py"])
    elif choice == "3":
        subprocess.run([sys.executable, "audit.py"])
    else:
        print("Lancement interface par défaut...")
        subprocess.run([sys.executable, "launch_ultra.py"])

if __name__ == "__main__":
    main()
