"""
Fichiers locaux montrés par la fenêtre : liens signés, ouverture, Explorateur

La page ne lit jamais le disque par un chemin de son choix :
  - une image, un PDF ou un aperçu s'affiche par un lien que le serveur a
    signé (FileLinks), et il ne le signe que pour un chemin qu'il connaît
    déjà : pièce jointe, image ou document de la conversation, fichier produit
    par l'appli (dossier outputs/), image collée (dossier des envois) ;
  - un chemin cité dans une réponse est montré dans l'Explorateur, jamais
    exécuté (utils/path_links.reveal_in_file_manager) ;
  - seuls les documents produits par l'appli s'ouvrent dans leur application
    ou se copient dans Téléchargements, comme le faisait l'interface Tk.

Le lien signé sert de clé : il ne porte pas le jeton du lancement (une image
ou une iframe ne peut pas envoyer d'en-tête), et il ne vaut que pour ce
lancement et ce fichier.
"""

import base64
import binascii
import hashlib
import hmac
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Iterable, List, Optional
from urllib.parse import quote

from utils.logger import setup_logger
from utils.path_links import reveal_in_file_manager

logger = setup_logger("DesktopFiles")

PROJECT_ROOT = Path(__file__).resolve().parents[2]

# Préfixe des liens signés (servis hors de /api : pas de jeton dans l'URL)
FILES_PREFIX = "/files/"

# Fichiers envoyés par la page sans chemin (image collée, glisser-déposer hors
# de la fenêtre pywebview) : un sous-dossier par envoi garde leur nom
UPLOAD_DIR = Path(tempfile.gettempdir()) / "my_ai_desktop_uploads"


class FileAccessError(Exception):
    """Fichier inconnu ou action refusée ; le message s'affiche à l'utilisateur."""


def normalize(path: str) -> str:
    """Chemin absolu et normalisé (casse comprise sous Windows), pour comparer."""
    return os.path.normcase(os.path.abspath(os.path.normpath(path)))


def is_inside(path: str, root: str) -> bool:
    """Vrai si `path` est dans `root` (chemins réels : liens et « .. » résolus)."""
    try:
        real_path = os.path.realpath(path)
        real_root = os.path.realpath(root)
        return os.path.commonpath([os.path.normcase(real_path), os.path.normcase(real_root)]) \
            == os.path.normcase(real_root)
    except ValueError:  # autre lecteur sous Windows
        return False


class FileLinks:
    """Liens signés vers des fichiers locaux, valables pour ce lancement."""

    def __init__(self, secret: bytes):
        self._secret = secret

    def _sign(self, token: str) -> str:
        digest = hmac.new(self._secret, token.encode("ascii"), hashlib.sha256).digest()
        return base64.urlsafe_b64encode(digest[:18]).decode("ascii")

    def url(self, path: str) -> str:
        """Lien de `path` : /files/<signature>/<chemin encodé>/<nom>."""
        absolute = os.path.abspath(path)
        token = base64.urlsafe_b64encode(absolute.encode("utf-8")).decode("ascii").rstrip("=")
        name = quote(os.path.basename(absolute) or "fichier")
        return f"{FILES_PREFIX}{self._sign(token)}/{token}/{name}"

    def resolve(self, signature: str, token: str) -> Optional[str]:
        """Chemin d'un lien signé, ou None si la signature ne correspond pas."""
        if not hmac.compare_digest(self._sign(token), signature or ""):
            return None
        try:
            padded = token + "=" * (-len(token) % 4)
            return base64.urlsafe_b64decode(padded.encode("ascii")).decode("utf-8")
        except (binascii.Error, UnicodeDecodeError, ValueError):
            return None


def generated_roots(config=None) -> List[str]:
    """Dossiers où l'appli écrit ce qu'elle produit (documents, images, exports…)."""
    roots = [str(PROJECT_ROOT / "outputs")]
    configured = "outputs"
    if config is not None:
        try:
            configured = config.get("generation.output_directory", "outputs") or "outputs"
        except Exception:  # pylint: disable=broad-except
            configured = "outputs"
    # Les générateurs écrivent souvent en relatif (« outputs/… ») : depuis le
    # dossier courant, qui n'est pas forcément la racine du projet
    for candidate in (configured, "outputs"):
        absolute = os.path.abspath(candidate)
        if absolute not in roots:
            roots.append(absolute)
    return roots


def is_generated(path: str, roots: Iterable[str]) -> bool:
    """Vrai si `path` est un fichier produit par l'appli (dans l'un des `roots`)."""
    if not path or not os.path.isfile(path):
        return False
    return any(is_inside(path, root) for root in roots)


def open_with_default_app(path: str) -> None:
    """Ouvre un fichier dans son application par défaut."""
    if sys.platform == "win32":
        os.startfile(path)  # noqa: B606 - document produit par l'appli, vérifié
    elif sys.platform == "darwin":
        subprocess.Popen(["open", path])  # pylint: disable=consider-using-with
    else:
        subprocess.Popen(["xdg-open", path])  # pylint: disable=consider-using-with


def reveal(path: str) -> None:
    """Montre un fichier ou un dossier existant dans le gestionnaire de fichiers.

    Raises:
        FileAccessError: chemin introuvable
    """
    if not path or not os.path.exists(path):
        raise FileAccessError("Chemin introuvable.")
    reveal_in_file_manager(path)


def downloads_dir() -> Path:
    """Dossier Téléchargements de l'utilisateur (download_file_to_downloads de Tk)."""
    downloads = Path.home() / "Downloads"
    if not downloads.exists():
        downloads = Path.home() / "Téléchargements"
    return downloads


def copy_to_downloads(path: str) -> str:
    """Copie un fichier dans Téléchargements ; renvoie le chemin de la copie."""
    target_dir = downloads_dir()
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / os.path.basename(path)
    shutil.copy2(path, target)
    return str(target)
