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

import re
import sys
import webbrowser
from typing import Any, Callable, List, Optional, Tuple
from urllib.parse import urlsplit

from core.i18n import tr
from interfaces.desktop.native_viewer import NativeViewer, parse_rect, window_host
from utils.logger import setup_logger

logger = setup_logger("ShellApi")

# Schémas qu'un lien peut ouvrir hors de l'appli (navigateur, messagerie)
EXTERNAL_SCHEMES = ("http", "https", "mailto")

# Nom d'un filtre de dialogue : pywebview n'y admet que lettres, chiffres et espaces
_FILTER_NAME_NOISE = re.compile(r"[^\w ]+")


def _filter(key: str, patterns: str) -> str:
    """Filtre d'un dialogue de fichiers : « Fichiers PDF (*.pdf) », nom traduit.

    Un trait d'union ou une apostrophe ferait refuser tout le dialogue :
    « PDF-Dateien » y devient « PDF Dateien ».
    """
    name = " ".join(_FILTER_NAME_NOISE.sub(" ", tr(key)).split())
    return f"{name} ({patterns})"


_CODE_EXTENSIONS = (
    "*.py;*.pyw;*.js;*.mjs;*.cjs;*.ts;*.tsx;*.jsx;*.html;*.htm;*.css;*.scss;*.json;*.xml;"
    "*.yaml;*.yml;*.toml;*.ini;*.cfg;*.md;*.rst;*.txt;*.log;*.sh;*.bat;*.ps1;*.c;*.h;*.cpp;"
    "*.hpp;*.cs;*.java;*.kt;*.go;*.rs;*.rb;*.php;*.lua;*.sql;*.vue;*.svelte;*.dart;*.swift"
)

# Entrées du menu « + » (types de l'interface Tk)
ATTACH_KINDS = ("PDF", "DOCX", "Excel", "PowerPoint", "Code", "Image")


def attach_filters(kind: str) -> Tuple[Tuple[str, ...], bool]:
    """Filtres du dialogue d'une entrée du menu « + » (comme Tk), et le choix multiple.

    Le multiple est refusé pour l'image : une seule part au modèle de vision.
    """
    every = _filter("dialog.allFiles", "*.*")
    filters = {
        "PDF": ((_filter("dialog.pdf", "*.pdf"),), True),
        "DOCX": ((_filter("dialog.word", "*.docx;*.doc"),), True),
        "Excel": ((_filter("dialog.excelCsv", "*.xlsx;*.xls;*.csv"), "Excel (*.xlsx)",
                   _filter("dialog.excelOld", "*.xls"), "CSV (*.csv)", every), True),
        "PowerPoint": ((_filter("dialog.pptx", "*.pptx;*.potx"), "PowerPoint (*.pptx)",
                        _filter("dialog.potx", "*.potx")), True),
        "Code": ((_filter("dialog.code", _CODE_EXTENSIONS), _filter("dialog.python", "*.py"),
                  _filter("dialog.javascript", "*.js"), _filter("dialog.html", "*.html"),
                  every), True),
        "Image": ((_filter("dialog.images", "*.png;*.jpg;*.jpeg;*.gif;*.bmp;*.webp;*.tiff;*.tif"),
                   "PNG (*.png)", "JPEG (*.jpg;*.jpeg)", "GIF (*.gif)", "BMP (*.bmp)",
                   "WebP (*.webp)", every), False),
    }
    return filters.get(kind, ((every,), True))


def export_filters(fmt: str) -> Tuple[str, ...]:
    """Filtres du dialogue d'export, par format ; json : workflow de la page Agents."""
    first = {"markdown": "Markdown (*.md)", "html": "HTML (*.html)", "pdf": "PDF (*.pdf)",
             "json": _filter("dialog.json", "*.json")}.get(fmt)
    return (first, _filter("dialog.all", "*.*")) if first else (_filter("dialog.all", "*.*"),)


def workflow_filters() -> Tuple[str, ...]:
    """Workflow enregistré à charger sur le canvas (WorkflowCanvas.to_dict de Tk)."""
    return (_filter("dialog.json", "*.json"), _filter("dialog.allFiles", "*.*"))


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

    def __init__(self, title_bar: Optional[Callable[[str, str], bool]] = None,
                 native_source: Optional[Callable[[str], Optional[str]]] = None,
                 background: str = "#0f0f0f"):
        """
        Args:
            title_bar: pose les couleurs de la barre de titre (fond, texte « #rrggbb »)
            native_source: document d'un aperçu « native » accepté par le serveur
                (PreviewStore.native_source), None sinon
            background: fond de la visionneuse le temps du chargement
        """
        self._title_bar = title_bar
        self._window = None
        self._native_source = native_source
        self._native = NativeViewer(self._native_host)
        self._background = background

    def _native_host(self):
        form = getattr(self._window, "native", None)
        return window_host(form, self._background) if form is not None else None

    def _shutdown(self) -> None:
        """Fenêtre fermée : visionneuse déchargée (Office jamais orphelin)."""
        self._native.shutdown()

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
        file_types, multiple = attach_filters(kind)
        return self._dialog("OPEN", allow_multiple=multiple, file_types=file_types)

    def pick_folder(self) -> Optional[str]:
        """Dossier projet à attacher (codebase, documents)."""
        paths = self._dialog("FOLDER")
        return paths[0] if paths else None

    def pick_workflow(self) -> Optional[str]:
        """Workflow à charger sur le canvas de la page Agents."""
        paths = self._dialog("OPEN", allow_multiple=False, file_types=workflow_filters())
        return paths[0] if paths else None

    def save_file(self, name: str, fmt: str) -> Optional[str]:
        """Chemin d'enregistrement d'un export (Markdown, HTML, PDF) ou d'un workflow (JSON)."""
        file_types = export_filters(fmt)
        paths = self._dialog("SAVE", save_filename=str(name or "conversation"),
                             file_types=file_types)
        return paths[0] if paths else None

    def open_external(self, url: str) -> bool:
        """Ouvre un lien dans le navigateur du système."""
        return open_external(url)

    def platform(self) -> str:
        """Système : win32, darwin, linux."""
        return sys.platform

    # ── Visionneuses Office (native_viewer.py) ──────────────────────────────

    def native_preview_available(self) -> bool:
        """Visionneuses de Windows possibles dans cette fenêtre."""
        return self._native_source is not None and NativeViewer.available()

    def native_preview_show(self, preview_id: str, rect: Any) -> bool:
        """Charge un aperçu « native » à la place réservée, masqué ; True s'il est prêt."""
        source = self._native_source(str(preview_id)) if self._native_source else None
        area = parse_rect(rect)
        if not source or area is None or not NativeViewer.available():
            return False
        try:
            return self._native.show(source, area)
        except Exception as exc:  # pylint: disable=broad-except
            logger.warning("Visionneuse native indisponible : %s", exc)
            return False

    def native_preview_place(self, rect: Any, visible: bool) -> bool:
        """Recale la visionneuse ; la masque sous un dialogue, un menu, un toast."""
        area = parse_rect(rect)
        if area is None:
            return False
        try:
            return self._native.place(area, bool(visible))
        except Exception as exc:  # pylint: disable=broad-except
            logger.warning("Visionneuse native non placée : %s", exc)
            return False

    def native_preview_close(self) -> bool:
        """Masque et décharge la visionneuse (volet fermé, autre aperçu)."""
        try:
            self._native.close()
        except Exception as exc:  # pylint: disable=broad-except
            logger.warning("Visionneuse native non fermée : %s", exc)
            return False
        return True

    def set_title_bar_colors(self, background: str, text: str) -> bool:
        """Barre de titre aux couleurs de la page (jetons de tokens.css), Windows 11."""
        if self._title_bar is None:
            return False
        try:
            return bool(self._title_bar(str(background), str(text)))
        except Exception as exc:  # pylint: disable=broad-except
            logger.warning("Couleurs de la barre de titre non appliquées : %s", exc)
            return False
