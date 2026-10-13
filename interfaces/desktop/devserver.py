"""
Serveur Vite du mode développement (launch_unified.py --ui web --dev)

La fenêtre affiche alors l'interface servie par Vite, avec rechargement à
chaud : une couleur ou une marge modifiée s'affiche aussitôt, sans relancer
l'appli (relancer l'appli redémarre Ollama). Vite relaie /api et /ws vers le
serveur local (proxy de frontend/vite.config.ts, port MY_AI_DESKTOP_PORT).

Un Vite déjà lancé à la main (« npm run dev » dans frontend/) est réutilisé ;
sinon il est lancé ici, et arrêté à la fermeture de l'appli.
"""

import os
import shutil
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Optional

from utils.logger import setup_logger

logger = setup_logger("ViteServer")

FRONTEND_DIR = Path(__file__).resolve().parents[2] / "frontend"
VITE_URL = "http://127.0.0.1:5173"
# Port du serveur local que vise le proxy de Vite (cf. vite.config.ts)
PORT_ENV = "MY_AI_DESKTOP_PORT"


class ViteServer:
    """Serveur de développement de l'interface."""

    def __init__(self, backend_port: int, url: str = VITE_URL,
                 frontend_dir: Path = FRONTEND_DIR):
        self.backend_port = backend_port
        self.url = url
        self._frontend = frontend_dir
        self._process: Optional[subprocess.Popen] = None

    def running(self) -> bool:
        """Vrai si Vite répond déjà."""
        try:
            with urllib.request.urlopen(self.url, timeout=1) as response:  # nosec - adresse locale
                return response.status == 200
        except (urllib.error.URLError, OSError, ValueError):
            return False

    def start(self, timeout: float = 60.0) -> str:
        """Réutilise ou lance Vite ; renvoie son adresse.

        Raises:
            RuntimeError: Node ou les dépendances du front manquent, ou Vite ne démarre pas
        """
        if self.running():
            print(f"♻️ Serveur Vite déjà lancé ({self.url}) : réutilisé. Son proxy vise le "
                  f"port {os.environ.get(PORT_ENV, '5180')} s'il a été lancé sans {PORT_ENV}.")
            return self.url
        vite = self._frontend / "node_modules" / "vite" / "bin" / "vite.js"
        node = shutil.which("node")
        if node is None:
            raise RuntimeError("Node.js introuvable : installez Node 22 LTS pour le mode --dev")
        if not vite.is_file():
            raise RuntimeError("Dépendances de l'interface absentes : lancez « npm install » "
                               "dans frontend/")
        env = dict(os.environ)
        env[PORT_ENV] = str(self.backend_port)
        # Même console que le lanceur : les erreurs de compilation y restent visibles
        self._process = subprocess.Popen(  # pylint: disable=consider-using-with
            [node, str(vite), "--strictPort"], cwd=str(self._frontend), env=env
        )
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if self._process.poll() is not None:
                raise RuntimeError(f"Vite s'est arrêté au démarrage (code {self._process.returncode})")
            if self.running():
                logger.info("Vite prêt sur %s", self.url)
                return self.url
            time.sleep(0.25)
        self.stop()
        raise RuntimeError(f"Vite ne répond pas après {int(timeout)} s")

    def stop(self) -> None:
        """Arrête Vite s'il a été lancé ici."""
        process, self._process = self._process, None
        if process is None or process.poll() is not None:
            return
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
