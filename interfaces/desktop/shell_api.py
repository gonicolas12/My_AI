"""
Fonctions de la fenêtre exposées au JavaScript (window.pywebview.api)

L'interface ne les appelle qu'à travers son module shell
(frontend/src/lib/shell.ts). pywebview expose toutes les méthodes publiques de
l'objet, et parcourt ses attributs publics : les références internes restent
donc privées (préfixe « _ »).

Seule la page de l'appli peut les appeler : la fenêtre ne charge jamais
d'autre page (cf. window.py), et les artefacts s'affichent dans des iframes
isolées, sans accès à ce pont.
"""

import sys
import webbrowser
from typing import Callable, List, Optional
from urllib.parse import urlsplit

from utils.logger import setup_logger

logger = setup_logger("ShellApi")

# Schémas qu'un lien peut ouvrir hors de l'appli (navigateur, messagerie)
EXTERNAL_SCHEMES = ("http", "https", "mailto")

_ALL_FILES = "Tous les fichiers (*.*)"
_CODE_EXTENSIONS = (
    "*.py;*.pyw;*.js;*.mjs;*.cjs;*.ts;*.tsx;*.jsx;*.html;*.htm;*.css;*.scss;*.json;*.xml;"
    "*.yaml;*.yml;*.toml;*.ini;*.cfg;*.md;*.rst;*.txt;*.log;*.sh;*.bat;*.ps1;*.c;*.h;*.cpp;"
    "*.hpp;*.cs;*.java;*.kt;*.go;*.rs;*.rb;*.php;*.lua;*.sql;*.vue;*.svelte;*.dart;*.swift"
)

# Filtres des dialogues de pièces jointes, par entrée du menu « + » (comme Tk) ;
# le multiple est refusé pour l'image : une seule part au modèle de vision
ATTACH_FILTERS = {
    "PDF": (("Fichiers PDF (*.pdf)",), True),
    "DOCX": (("Fichiers Word (*.docx;*.doc)",), True),
    "Excel": (("Fichiers Excel et CSV (*.xlsx;*.xls;*.csv)", "Excel (*.xlsx)",
               "Excel ancien (*.xls)", "CSV (*.csv)", _ALL_FILES), True),
    "PowerPoint": (("Présentations PowerPoint (*.pptx;*.potx)", "PowerPoint (*.pptx)",
                    "Modèle PowerPoint (*.potx)"), True),
    "Code": ((f"Fichiers de code ({_CODE_EXTENSIONS})", "Fichiers Python (*.py)",
              "Fichiers JavaScript (*.js)", "Fichiers HTML (*.html)", _ALL_FILES), True),
    "Image": (("Images (*.png;*.jpg;*.jpeg;*.gif;*.bmp;*.webp;*.tiff;*.tif)", "PNG (*.png)",
               "JPEG (*.jpg;*.jpeg)", "GIF (*.gif)", "BMP (*.bmp)", "WebP (*.webp)",
               _ALL_FILES), False),
}

# Filtres du dialogue d'export, par format
EXPORT_FILTERS = {
    "markdown": ("Markdown (*.md)", "Tous (*.*)"),
    "html": ("HTML (*.html)", "Tous (*.*)"),
    "pdf": ("PDF (*.pdf)", "Tous (*.*)"),
}


def external_url(url: str) -> Optional[str]:
    """URL d'un lien web autorisé à sortir de l'appli, ou None (file:, javascript:…)."""
    if not isinstance(url, str):
        return None
    url = url.strip()
    try:
        parts = urlsplit(url)
    except ValueError:
        return None
    if parts.scheme.lower() not in EXTERNAL_SCHEMES:
        return None
    if parts.scheme.lower() != "mailto" and not parts.netloc:
        return None
    return url


def open_external(url: str, opener: Callable[[str], bool] = webbrowser.open) -> bool:
    """Ouvre un lien web dans le navigateur du système ; tout autre schéma est refusé."""
    target = external_url(url)
    if target is None:
        logger.warning("Lien refusé (schéma non autorisé) : %.120s", url)
        return False
    try:
        return bool(opener(target))
    except Exception as exc:  # pylint: disable=broad-except
        logger.warning("Ouverture du lien impossible : %s", exc)
        return False


class ShellApi:
    """Pont entre l'interface et la fenêtre."""

    def __init__(self, title_bar: Optional[Callable[[str, str], bool]] = None):
        """
        Args:
            title_bar: pose les couleurs de la barre de titre (fond, texte « #rrggbb »)
        """
        self._title_bar = title_bar
        self._window = None

    def _attach_window(self, window) -> None:
        """Fenêtre pywebview des dialogues (privé : pas exposé au JavaScript)."""
        self._window = window

    def _dialog(self, kind: str, **options) -> List[str]:
        """Dialogue système de la fenêtre ; liste vide s'il est annulé ou impossible."""
        window = self._window
        if window is None:
            return []
        try:
            import webview  # pylint: disable=import-outside-toplevel

            dialog_type = getattr(webview.FileDialog, kind)
            result = window.create_file_dialog(dialog_type, **options)
        except Exception as exc:  # pylint: disable=broad-except
            logger.warning("Dialogue de fichiers impossible : %s", exc)
            return []
        if not result:
            return []
        if isinstance(result, str):
            return [result]
        return [str(path) for path in result]

    def pick_files(self, kind: str) -> List[str]:
        """Fichiers à joindre, par entrée du menu « + » (PDF, DOCX, Excel…)."""
        file_types, multiple = ATTACH_FILTERS.get(kind, ((_ALL_FILES,), True))
        return self._dialog("OPEN", allow_multiple=multiple, file_types=file_types)

    def pick_folder(self) -> Optional[str]:
        """Dossier projet à attacher (codebase, documents)."""
        paths = self._dialog("FOLDER")
        return paths[0] if paths else None

    def save_file(self, name: str, fmt: str) -> Optional[str]:
        """Chemin d'enregistrement d'un export (Markdown, HTML, PDF)."""
        file_types = EXPORT_FILTERS.get(fmt, (_ALL_FILES,))
        paths = self._dialog("SAVE", save_filename=str(name or "conversation"),
                             file_types=file_types)
        return paths[0] if paths else None

    def open_external(self, url: str) -> bool:
        """Ouvre un lien dans le navigateur du système."""
        return open_external(url)

    def platform(self) -> str:
        """Système : win32, darwin, linux."""
        return sys.platform

    def set_title_bar_colors(self, background: str, text: str) -> bool:
        """Barre de titre aux couleurs de la page (jetons de tokens.css), Windows 11."""
        if self._title_bar is None:
            return False
        try:
            return bool(self._title_bar(str(background), str(text)))
        except Exception as exc:  # pylint: disable=broad-except
            logger.warning("Couleurs de la barre de titre non appliquées : %s", exc)
            return False
