#!/usr/bin/env python3
"""
🚀 MY PERSONAL AI - LAUNCHER UNIFIÉ v6.9.0
Lance l'interface avec CustomAI unifié (support 1M tokens intégré)
"""

import os
import subprocess
import sys
import time
import winreg
import ctypes
from pathlib import Path

import requests


def _ensure_ollama_parallel():
    """Configure Ollama pour le parallélisme et le redémarre si nécessaire."""
    num_parallel = "4"

    # ── 1. Écrire la variable dans le registre Windows (permanent, sans admin) ──
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, "Environment", 0, winreg.KEY_ALL_ACCESS
        )
        try:
            current, _ = winreg.QueryValueEx(key, "OLLAMA_NUM_PARALLEL")
        except FileNotFoundError:
            current = None
        if current != num_parallel:
            winreg.SetValueEx(key, "OLLAMA_NUM_PARALLEL", 0, winreg.REG_SZ, num_parallel)
            print(f"📝 Variable OLLAMA_NUM_PARALLEL={num_parallel} enregistrée (permanent)")
            # Notifier Windows du changement
            ctypes.windll.user32.SendMessageTimeoutW(0xFFFF, 0x001A, 0, "Environment", 0, 1000, None)
        winreg.CloseKey(key)
    except Exception as e:
        print(f"⚠️ Impossible d'écrire la variable registre: {e}")

    # ── 2. Définir pour notre processus aussi ──
    os.environ["OLLAMA_NUM_PARALLEL"] = num_parallel

    # ── 3. Vérifier si Ollama tourne déjà ──
    try:
        r = requests.get("http://localhost:11434/api/tags", timeout=2)
        ollama_running = r.status_code == 200
    except Exception:
        ollama_running = False

    if ollama_running:
        # Tuer TOUS les processus Ollama (y compris l'app bureau)
        print("🔄 Redémarrage d'Ollama avec OLLAMA_NUM_PARALLEL=4...")
        subprocess.run(
            ["taskkill", "/F", "/IM", "ollama.exe", "/T"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            check=False,
        )
        # Attendre que le port soit libéré
        for _ in range(10):
            try:
                requests.get("http://localhost:11434/api/tags", timeout=0.5)
                time.sleep(0.5)
            except Exception:
                break  # Port libéré, Ollama est bien mort

    # ── 4. Lancer Ollama avec notre environnement ──
    env = os.environ.copy()
    env["OLLAMA_NUM_PARALLEL"] = num_parallel
    try:
        subprocess.Popen(
            ["ollama", "serve"],
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        # Attendre qu'Ollama soit prêt
        for _ in range(20):
            try:
                r = requests.get("http://localhost:11434/api/tags", timeout=2)
                if r.status_code == 200:
                    print(f"✅ Ollama prêt (parallélisme: {num_parallel} requêtes simultanées)")
                    return
            except Exception:
                pass
            time.sleep(0.5)
        print("⚠️ Ollama lancé mais pas encore prêt — il démarrera sous peu")
    except FileNotFoundError:
        print("⚠️ Ollama non trouvé dans le PATH — installez-le depuis ollama.com")

# =========================================================================== #
# NOTE: Le mode offline HuggingFace est géré automatiquement dans core.shared #
# avec téléchargement automatique au premier lancement si nécessaire          #
# =========================================================================== #

# Import - core.shared gère le chargement du modèle d'embeddings
from interfaces.gui_modern import \
    ModernAIGUI  # pylint: disable=wrong-import-position

# Ajouter le répertoire parent au chemin
sys.path.insert(0, str(Path(__file__).parent))

def main():
    """Point d'entrée principal"""
    print("\n🚀 MY PERSONAL AI LAUNCHER UNIFIÉ v6.9.0\n")
    print("=" * 50)
    print()

    # S'assurer qu'Ollama tourne avec le bon parallélisme
    _ensure_ollama_parallel()

    print("   🧠 CustomAI avec support 1M tokens intégré")
    print("   🔧 Processeurs PDF, DOCX, Code avancés")
    print("   🎨 Interface moderne CustomTkinter")
    print("   📊 Mémoire conversationnelle intelligente")
    print("   🌐 Recherche internet intégrée")
    print("   ⚡ Architecture 100% locale")
    print()

    try:
        print("✅ Modules chargés avec succès")
        print("🚀 Lancement de l'interface...")
        print()

        # Lancer l'interface
        app = ModernAIGUI()
        app.run()

    except ImportError as e:
        print(f"❌ Erreur d'import: {e}")
        print()
        print("🔧 Solutions possibles:")
        print("   1. Installez les dépendances: pip install -r requirements.txt")
        print("   2. Vérifiez que tous les modules sont présents")
        print("   3. Utilisez: python main.py en fallback")
        sys.exit(1)

    except (RuntimeError, OSError, AttributeError) as e:
        print(f"❌ Erreur lors du lancement: {e}")
        print()
        print("🔧 Essayez le mode debug:")
        print(
            '   python -c "from interfaces.gui_modern import ModernAIGUI; ModernAIGUI().run()"'
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
