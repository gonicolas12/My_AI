#!/usr/bin/env python3
"""
🚀 MY PERSONAL AI - LAUNCHER UNIFIÉ v8.0.0
Lance l'interface avec CustomAI unifié (support 10M tokens intégré)

Portable Windows / macOS / Linux : les appels propres à un OS (registre,
taskkill, launchctl…) sont isolés derrière des gardes de plateforme et
importés paresseusement, pour que ce module reste importable partout.
"""

import os
import subprocess
import sys
import time
from pathlib import Path

import requests

IS_WINDOWS = sys.platform.startswith("win")
IS_MACOS = sys.platform == "darwin"

# CREATE_NO_WINDOW n'existe que sous Windows (évite une console qui flashe)
_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)

OLLAMA_TAGS_URL = "http://localhost:11434/api/tags"


def _ollama_is_running(timeout: float = 2.0) -> bool:
    """Vrai si un serveur Ollama répond déjà sur le port local."""
    try:
        return requests.get(OLLAMA_TAGS_URL, timeout=timeout).status_code == 200
    except Exception:
        return False


def _persist_env_var(name: str, value: str) -> None:
    """Enregistre la variable pour les prochains lancements, selon l'OS.

    Windows : registre utilisateur (permanent, sans admin).
    macOS   : ``launchctl setenv`` — vu par l'app Ollama lancée ensuite depuis
              le Finder, mais remis à zéro à la fin de la session.
    Linux   : pas de mécanisme utilisateur standard ; on se contente de
              l'environnement de nos processus enfants.
    """
    if IS_WINDOWS:
        try:
            import ctypes  # pylint: disable=import-outside-toplevel
            import winreg  # pylint: disable=import-outside-toplevel

            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER, "Environment", 0, winreg.KEY_ALL_ACCESS
            )
            try:
                current, _ = winreg.QueryValueEx(key, name)
            except FileNotFoundError:
                current = None
            if current != value:
                winreg.SetValueEx(key, name, 0, winreg.REG_SZ, value)
                print(f"📝 Variable {name}={value} enregistrée (permanent)")
                # Notifier Windows du changement
                ctypes.windll.user32.SendMessageTimeoutW(
                    0xFFFF, 0x001A, 0, "Environment", 0, 1000, None
                )
            winreg.CloseKey(key)
        except Exception as e:
            print(f"⚠️ Impossible d'écrire la variable registre: {e}")
        return

    if IS_MACOS:
        try:
            subprocess.run(
                ["launchctl", "setenv", name, value],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                check=False,
            )
            print(f"📝 Variable {name}={value} posée via launchctl (session courante)")
        except FileNotFoundError:
            print("⚠️ launchctl introuvable — variable posée pour ce processus seulement")
        return

    print(
        f"💡 Pour rendre {name}={value} permanent sous Linux, passez par "
        "'systemctl edit ollama.service' ou votre profil shell"
    )


def _kill_ollama() -> None:
    """Arrête tous les processus Ollama, y compris l'application bureau."""
    if IS_WINDOWS:
        subprocess.run(
            ["taskkill", "/F", "/IM", "ollama.exe", "/T"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            check=False,
        )
        return

    # macOS / Linux : le serveur tourne sous le nom exact « ollama ».
    try:
        subprocess.run(
            ["pkill", "-x", "ollama"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            check=False,
        )
    except FileNotFoundError:
        print("⚠️ pkill introuvable — arrêtez Ollama manuellement si besoin")

    if IS_MACOS:
        # Sans ça, l'app bureau relance le serveur avec l'ancien environnement.
        subprocess.run(
            ["osascript", "-e", 'tell application "Ollama" to quit'],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            check=False,
        )


def _ensure_ollama_parallel():
    """Configure Ollama pour le parallélisme et le redémarre si nécessaire."""
    num_parallel = "4"

    # ── 1. Rendre la variable persistante autant que l'OS le permet ──
    _persist_env_var("OLLAMA_NUM_PARALLEL", num_parallel)

    # ── 2. Définir pour notre processus aussi ──
    os.environ["OLLAMA_NUM_PARALLEL"] = num_parallel

    # ── 3. Si Ollama tourne déjà, le redémarrer avec le bon environnement ──
    if _ollama_is_running():
        # Tuer TOUS les processus Ollama (y compris l'app bureau)
        print("🔄 Redémarrage d'Ollama avec OLLAMA_NUM_PARALLEL=4...")
        _kill_ollama()
        # Attendre que le port soit libéré
        for _ in range(10):
            if not _ollama_is_running(timeout=0.5):
                break  # Port libéré, Ollama est bien mort
            time.sleep(0.5)

    # ── 4. Lancer Ollama avec notre environnement ──
    env = os.environ.copy()
    env["OLLAMA_NUM_PARALLEL"] = num_parallel
    popen_kwargs = {
        "env": env,
        "stdout": subprocess.DEVNULL,
        "stderr": subprocess.DEVNULL,
    }
    if IS_WINDOWS:
        popen_kwargs["creationflags"] = _NO_WINDOW
    else:
        # Détacher le serveur : il survit à la fermeture du lanceur.
        popen_kwargs["start_new_session"] = True
    try:
        subprocess.Popen(["ollama", "serve"], **popen_kwargs)
        # Attendre qu'Ollama soit prêt
        for _ in range(20):
            if _ollama_is_running():
                print(f"✅ Ollama prêt (parallélisme: {num_parallel} requêtes simultanées)")
                return
            time.sleep(0.5)
        print("⚠️ Ollama lancé mais pas encore prêt — il démarrera sous peu")
    except FileNotFoundError:
        print("⚠️ Ollama non trouvé dans le PATH — installez-le depuis ollama.com")

# =========================================================================== #
# NOTE: Le mode offline HuggingFace est géré automatiquement dans core.shared #
# avec téléchargement automatique au premier lancement si nécessaire          #
# =========================================================================== #

# Initialiser le stack reseau/proxy avant les imports applicatifs.
try:
    from core.network import configure_network_environment

    configure_network_environment()
except Exception:
    pass

# Import - core.shared gère le chargement du modèle d'embeddings
from interfaces.gui_modern import \
    ModernAIGUI  # pylint: disable=wrong-import-position

# Ajouter le répertoire parent au chemin
sys.path.insert(0, str(Path(__file__).parent))

def main():
    """Point d'entrée principal"""
    print("\n🚀 MY PERSONAL AI LAUNCHER UNIFIÉ v8.0.0\n")
    print("=" * 50)
    print()

    # S'assurer qu'Ollama tourne avec le bon parallélisme
    _ensure_ollama_parallel()

    # Assistant de premier lancement (détection RAM → pull modèle → modèle custom).
    # Ne s'affiche qu'une fois (marqueur data/.onboarding_done) et jamais si le
    # modèle 'my_ai' existe déjà. Échec non bloquant : l'app démarre quand même.
    try:
        from interfaces.onboarding import OnboardingWizard, should_run
        if should_run():
            print("🧭 Premier lancement détecté — assistant de configuration…")
            OnboardingWizard().run()
    except Exception as exc:
        print(f"⚠️ Assistant d'onboarding ignoré : {exc}")

    print("   🧠 CustomAI avec support 10M tokens intégré")
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
