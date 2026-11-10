#!/usr/bin/env python3
"""
🚀 MY PERSONAL AI - LAUNCHER UNIFIÉ v9.1.0
Lance l'interface avec CustomAI unifié (support 10M tokens intégré)

Portable Windows / macOS / Linux : les appels propres à un OS (taskkill,
pkill, osascript…) sont isolés derrière des gardes de plateforme, pour que ce
module reste importable partout.
"""

import argparse
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

if __name__ == "__main__":
    # Python 3.11 à 3.14 (3.12 sur Mac Intel) : vérifié avant toute installation,
    # pour un message clair plutôt qu'un échec de pip (cf. utils/python_version.py)
    from utils.python_version import check_python_version

    check_python_version()

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

# Requêtes simultanées par modèle (OLLAMA_NUM_PARALLEL) : les nœuds parallèles
# des workflows d'agents avancent en même temps. Depuis Ollama 0.40.15, qwen3.5
# en profite aussi (forcé à une requête avant), et chaque requête simultanée
# réserve son propre contexte : my_ai en 32 768 tokens occupe 7,0 Gio avec 4,
# contre 3,9 Gio avec 1. Mesuré sur un Core Ultra 7 255H (Arc 140T) : 4 agents
# en parallèle 2,2 à 3,3 fois plus vite, requête seule sans écart démontré.
# Une valeur définie par l'utilisateur l'emporte (OLLAMA_NUM_PARALLEL=1 pour
# économiser la mémoire).
DEFAULT_NUM_PARALLEL = "4"


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


def _num_parallel() -> str:
    """OLLAMA_NUM_PARALLEL défini par l'utilisateur (un entier), sinon le défaut de l'appli."""
    value = os.environ.get("OLLAMA_NUM_PARALLEL", "").strip()
    return value if value.isdigit() else DEFAULT_NUM_PARALLEL


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
    """(Re)lance Ollama avec le parallélisme de l'appli et le placement retenu.

    OLLAMA_NUM_PARALLEL n'est passée qu'au serveur lancé ici. Elle n'est plus
    écrite pour tout le système (registre, launchctl) : avec Ollama 0.40.15 ou
    plus, elle ferait réserver plusieurs contextes à chaque modèle des autres
    applis qui utilisent Ollama.
    """
    # ── 1. Valeur de l'utilisateur, sinon celle de l'appli (cf. DEFAULT_NUM_PARALLEL) ──
    num_parallel = _num_parallel()
    os.environ["OLLAMA_NUM_PARALLEL"] = num_parallel

    # ── 2. (Re)lancer Ollama avec ce parallélisme et le placement du modèle
    #       retenu au dernier calibrage (GPU ou processeur) ──
    if not _port_is_free():
        print(f"🔄 Redémarrage d'Ollama avec OLLAMA_NUM_PARALLEL={num_parallel}...")
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
    parallel = ("1 requête à la fois" if num_parallel == "1"
                else f"{num_parallel} requêtes simultanées")
    print(f"✅ Ollama prêt (parallélisme: {parallel}{details})")

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

# Étapes du lancement que interfaces/desktop/lifecycle.py appelle à travers ce
# module, comme _ensure_ollama_parallel et ensure_best_placement. L'interface,
# elle, s'importe dans main() : core.shared y charge le modèle d'embeddings
from interfaces.onboarding import \
    sync_custom_model  # pylint: disable=wrong-import-position,unused-import
from core.passage_embeddings import \
    prefetch_in_background  # pylint: disable=wrong-import-position,unused-import

# Ajouter le répertoire parent au chemin
sys.path.insert(0, str(Path(__file__).parent))


def _parse_args(argv=None) -> argparse.Namespace:
    """Options du lanceur."""
    parser = argparse.ArgumentParser(description="Lanceur de My_AI")
    # Ancienne option (--ui web|tk) : « web » reste accepté pour les commandes
    # existantes ; l'interface Tk n'existe plus
    parser.add_argument("--ui", choices=("web",), default="web", help=argparse.SUPPRESS)
    parser.add_argument(
        "--dev", action="store_true",
        help="interface web servie par Vite, avec rechargement à chaud "
             "(Node et « npm install » dans frontend/)",
    )
    parser.add_argument(
        "--headless", action="store_true",
        help="serveur de l'interface web et moteur, sans fenêtre (tests, client WebSocket)",
    )
    parser.add_argument(
        "--port", type=int, default=0,
        help="port du serveur de l'interface web (défaut : un port libre, 5180 avec --dev)",
    )
    return parser.parse_args(argv)


def main():
    """Point d'entrée principal"""
    args = _parse_args()
    print("\n🚀 MY PERSONAL AI LAUNCHER UNIFIÉ v9.1.0\n")
    print("=" * 50)
    print()

    if args.headless:
        # Interface web sans fenêtre : le serveur local répond tout de suite, puis
        # interfaces/desktop/lifecycle.py enchaîne les étapes du lancement (Ollama,
        # assistant, my_ai, placement) avant le moteur
        from interfaces.desktop.lifecycle import \
            run_headless  # pylint: disable=import-outside-toplevel
        run_headless(sys.modules[__name__], port=args.port)
        # Rien ne retient le processus (fils du serveur, des tunnels…)
        os._exit(0)

    # La fenêtre s'ouvre tout de suite sur l'écran de chargement, qui nomme les
    # étapes du lancement, enchaînées par interfaces/desktop/lifecycle.py dans
    # cet ordre : modèle des longs documents en arrière-plan, redémarrage
    # d'Ollama, assistant de premier lancement, recréation de 'my_ai' si le
    # Modelfile a changé, placement du modèle, puis moteur et services
    try:
        from interfaces.desktop.lifecycle import \
            run_desktop  # pylint: disable=import-outside-toplevel
    except ImportError as e:
        print(f"❌ Erreur d'import: {e}")
        print()
        print("🔧 Solutions possibles:")
        print("   1. Installez les dépendances: pip install -r requirements.txt")
        print("   2. Vérifiez que tous les modules sont présents")
        print("   3. Utilisez: python main.py en fallback")
        sys.exit(1)
    run_desktop(sys.modules[__name__], dev=args.dev, port=args.port)
    os._exit(0)


if __name__ == "__main__":
    main()
