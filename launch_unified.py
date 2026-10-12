#!/usr/bin/env python3
"""
🚀 MY PERSONAL AI - LAUNCHER UNIFIÉ v8.1.0
Lance l'interface avec CustomAI unifié (support 10M tokens intégré)

Portable Windows / macOS / Linux : les appels propres à un OS (registre,
taskkill, launchctl…) sont isolés derrière des gardes de plateforme et
importés paresseusement, pour que ce module reste importable partout.
"""

import argparse
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

if __name__ == "__main__":
    # Paquets ajoutés à requirements.txt depuis le dernier lancement (git pull) :
    # installés avant les imports qui en ont besoin
    from utils.requirements_sync import sync_requirements

    sync_requirements()

import requests  # pylint: disable=wrong-import-position

from utils.ollama_placement import (  # pylint: disable=wrong-import-position,ungrouped-imports
    ensure_best_placement,
    placement_label,
    saved_env,
    server_env,
)

IS_WINDOWS = sys.platform.startswith("win")
IS_MACOS = sys.platform == "darwin"

# CREATE_NO_WINDOW n'existe que sous Windows (évite une console qui flashe)
_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)

# 127.0.0.1 et non localhost : sous Windows, localhost essaie d'abord l'IPv6,
# où Ollama n'écoute pas, et perd ≈ 2 s à chaque requête
_OLLAMA_IP, _OLLAMA_PORT = "127.0.0.1", 11434
OLLAMA_TAGS_URL = f"http://{_OLLAMA_IP}:{_OLLAMA_PORT}/api/tags"

# Attente maximale, après l'arrêt d'Ollama, que son port soit rendu
_PORT_RELEASE_TIMEOUT = 10.0


def _ollama_is_running(timeout: float = 2.0) -> bool:
    """Vrai si un serveur Ollama répond déjà sur le port local."""
    try:
        return requests.get(OLLAMA_TAGS_URL, timeout=timeout).status_code == 200
    except Exception:
        return False


def _port_is_free() -> bool:
    """Vrai si « ollama serve » pourrait prendre son port.

    Contrairement à _ollama_is_running, voit aussi un serveur qui ne répond pas
    encore (détection des GPU au démarrage) ou qui finit de s'arrêter.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        if not IS_WINDOWS:
            # Comme Ollama (Go) : sans cette option, les connexions de l'ancien
            # serveur restées en TIME_WAIT bloqueraient le port jusqu'à une minute
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind((_OLLAMA_IP, _OLLAMA_PORT))
        except OSError:
            return False
    return True


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
        # L'application bureau d'abord : sinon elle relance aussitôt son propre
        # serveur, avec son environnement à elle (sans nos variables)
        for image in ("ollama app.exe", "ollama.exe"):
            subprocess.run(
                ["taskkill", "/F", "/IM", image, "/T"],
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


def _restart_ollama(placement_env: dict) -> bool:
    """(Re)lance le serveur Ollama avec notre environnement et ce placement du modèle.

    Returns:
        True si le serveur répond

    Raises:
        FileNotFoundError: commande « ollama » introuvable
    """
    # ── 1. Si Ollama tourne déjà, l'arrêter : il garderait son environnement.
    #       Port testé plutôt qu'une requête : un serveur qui démarre ne répond
    #       pas encore, mais garde le port ──
    if not _port_is_free():
        # Tuer TOUS les processus Ollama (y compris l'app bureau)
        _kill_ollama()
        # Attendre que le port soit rendu : taskkill rend la main avant la fin
        # de l'arrêt, et un serveur lancé trop tôt s'arrêterait faute de port.
        # Pas de requête ici : le serveur mourant ne répond plus mais garde le port
        deadline = time.monotonic() + _PORT_RELEASE_TIMEOUT
        while not _port_is_free() and time.monotonic() < deadline:
            time.sleep(0.1)

    # ── 2. Le lancer avec notre environnement (OLLAMA_NUM_PARALLEL compris)
    #       et les variables du placement (cf. utils/ollama_placement.py) ──
    popen_kwargs = {
        "env": server_env(os.environ, placement_env),
        "stdout": subprocess.DEVNULL,
        "stderr": subprocess.DEVNULL,
    }
    if IS_WINDOWS:
        popen_kwargs["creationflags"] = _NO_WINDOW
    else:
        # Détacher le serveur : il survit à la fermeture du lanceur.
        popen_kwargs["start_new_session"] = True
    server = subprocess.Popen(["ollama", "serve"], **popen_kwargs)
    # Attendre qu'Ollama soit prêt
    for _ in range(20):
        stopped = server.poll() is not None
        if _ollama_is_running():
            return True  # le nôtre, ou un serveur que _kill_ollama ne peut arrêter
        if stopped:
            return False  # arrêté au démarrage : inutile d'attendre
        time.sleep(0.5)
    return False


def _ensure_ollama_parallel():
    """Configure Ollama pour le parallélisme et le redémarre si nécessaire."""
    num_parallel = "4"

    # ── 1. Rendre la variable persistante autant que l'OS le permet ──
    _persist_env_var("OLLAMA_NUM_PARALLEL", num_parallel)

    # ── 2. Définir pour notre processus aussi ──
    os.environ["OLLAMA_NUM_PARALLEL"] = num_parallel

    # ── 3. (Re)lancer Ollama avec ce parallélisme et le placement du modèle
    #       retenu au dernier calibrage (GPU ou processeur) ──
    if not _port_is_free():
        print("🔄 Redémarrage d'Ollama avec OLLAMA_NUM_PARALLEL=4...")
    try:
        ready = _restart_ollama(saved_env())
    except FileNotFoundError:
        print("⚠️ Ollama non trouvé dans le PATH — installez-le depuis ollama.com")
        return
    if not ready:
        if _port_is_free():  # serveur arrêté : il ne démarrera pas tout seul
            print(
                "⚠️ Ollama n'a pas pu démarrer — lancez l'application Ollama "
                "ou « ollama serve »"
            )
        else:
            print("⚠️ Ollama lancé mais pas encore prêt — il démarrera sous peu")
        return
    label = placement_label()
    details = f", {label}" if label else ""
    print(f"✅ Ollama prêt (parallélisme: {num_parallel} requêtes simultanées{details})")

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

# L'interface (Tk ou web) s'importe dans main() : core.shared y charge le
# modèle d'embeddings
from interfaces.onboarding import \
    sync_custom_model  # pylint: disable=wrong-import-position
from core.passage_embeddings import \
    prefetch_in_background  # pylint: disable=wrong-import-position

# Ajouter le répertoire parent au chemin
sys.path.insert(0, str(Path(__file__).parent))


def _parse_args(argv=None) -> argparse.Namespace:
    """Options du lanceur."""
    parser = argparse.ArgumentParser(description="Lanceur de My_AI")
    parser.add_argument(
        "--headless", action="store_true",
        help="serveur de l'interface web et moteur, sans fenêtre (tests, client WebSocket)",
    )
    parser.add_argument(
        "--port", type=int, default=0,
        help="port du serveur de l'interface web (défaut : un port libre)",
    )
    return parser.parse_args(argv)


def main():
    """Point d'entrée principal"""
    args = _parse_args()
    print("\n🚀 MY PERSONAL AI LAUNCHER UNIFIÉ v8.1.0\n")
    print("=" * 50)
    print()

    if args.headless:
        # Interface web sans fenêtre : le serveur local répond tout de suite, puis
        # interfaces/desktop/lifecycle.py enchaîne les étapes ci-dessous (Ollama,
        # assistant, my_ai, placement) avant le moteur
        from interfaces.desktop.lifecycle import \
            run_headless  # pylint: disable=import-outside-toplevel
        run_headless(sys.modules[__name__], port=args.port)
        # Comme à la fermeture de l'interface Tk : rien ne retient le processus
        os._exit(0)

    # Modèle multilingue des longs documents : téléchargé en arrière-plan s'il
    # manque (premier lancement, ou mise à jour qui l'introduit)
    prefetch_in_background()

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

    # Modèle 'my_ai' recréé si le Modelfile a changé depuis sa création
    # (modifié à la main, par un git pull ou par ⚙️ Réglages)
    sync_custom_model()

    # Modèle placé sur le matériel le plus rapide (carte graphique, GPU intégré
    # ou processeur) : mesuré au premier lancement, puis après une mise à jour
    # d'Ollama ou un changement de modèle ou de matériel
    ensure_best_placement(_restart_ollama)

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
        from interfaces.gui_modern import \
            ModernAIGUI  # pylint: disable=import-outside-toplevel
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
