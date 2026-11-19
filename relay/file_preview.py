"""
Aperçu d'un fichier du PC dans la modale du téléphone et de l'extension VS Code

Ni le téléphone ni VS Code ne lisent le disque du PC : ils demandent l'aperçu
d'un fichier (message WS « file_preview », relay_server.py) et le Relay le leur
renvoie dans l'enveloppe chiffrée, sous la forme qu'ils savent afficher. Les
genres suivent ceux de la fenêtre (frontend/src/lib/fileKinds.ts) :

  image     l'image en base64 ; un SVG aussi (affiché en <img>, sans script),
            avec sa source pour l'onglet Code
  document  page HTML d'interfaces/document_preview : PDF en images de ses
            pages, Word, Excel, PowerPoint, CSV en tableau ; Markdown rendu avec
            son HTML ; le Markdown et le CSV ont leur source en plus
  html      la source d'une page, rendue par la modale dans une iframe isolée
  text      le début d'un fichier de code ou de texte, et son langage
  audio, video  le fichier en base64, lu par la page
  none      rien d'affichable : nom et taille, le téléchargement reste

Le téléchargement (download) renvoie le fichier lui-même, quel qu'il soit.
Seuls les fichiers que la conversation montre s'ouvrent ainsi : c'est le
Relay qui en décide (RelayServer.preview_allowed), pas ce module.
"""

import base64
import mimetypes
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from core.i18n import tr

# Image, son ou vidéo mis dans la réponse ; au-delà, seul le téléchargement reste
INLINE_MAX = 12 * 1024 * 1024
# Fichier envoyé tel quel (Télécharger) : la taille des envois du téléphone
DOWNLOAD_MAX = 25 * 1024 * 1024
# Début d'un fichier texte montré (la fenêtre lit autant, files.TEXT_PREVIEW_MAX)
TEXT_MAX = 512 * 1024
# Au-delà, un document n'est pas rendu (PDF de centaines de pages, gros classeur)
DOCUMENT_MAX = 60 * 1024 * 1024

_IMAGES = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
           ".gif": "image/gif", ".webp": "image/webp", ".bmp": "image/bmp",
           ".ico": "image/x-icon", ".avif": "image/avif", ".svg": "image/svg+xml"}
_AUDIO = {".mp3": "audio/mpeg", ".wav": "audio/wav", ".ogg": "audio/ogg",
          ".oga": "audio/ogg", ".m4a": "audio/mp4", ".aac": "audio/aac",
          ".flac": "audio/flac", ".opus": "audio/ogg"}
_VIDEO = {".mp4": "video/mp4", ".webm": "video/webm", ".mov": "video/quicktime",
          ".m4v": "video/mp4", ".ogv": "video/ogg"}
# Rendus en HTML par interfaces/document_preview (.doc, .ppt : pas lisibles ici)
_DOCUMENTS = frozenset({".pdf", ".docx", ".xlsx", ".xlsm", ".xls", ".csv", ".pptx", ".potx",
                        ".md", ".markdown"})
# Documents rendus dont la source se lit aussi (onglet Code) : son langage
_SOURCES = {".md": "markdown", ".markdown": "markdown", ".csv": "csv"}
_HTML = frozenset({".html", ".htm", ".xhtml"})
# Extension → langage affiché en tête du bloc de code (comme lib/fileKinds.ts)
_LANGUAGES = {
    ".py": "python", ".pyw": "python", ".pyi": "python", ".ipynb": "json",
    ".js": "javascript", ".mjs": "javascript", ".cjs": "javascript", ".jsx": "jsx",
    ".ts": "typescript", ".mts": "typescript", ".cts": "typescript", ".tsx": "tsx",
    ".json": "json", ".jsonc": "jsonc", ".json5": "jsonc", ".yaml": "yaml", ".yml": "yaml",
    ".toml": "toml", ".ini": "ini", ".cfg": "ini", ".conf": "ini", ".properties": "ini",
    ".env": "ini", ".xml": "xml", ".xsd": "xml", ".xsl": "xml", ".csproj": "xml",
    ".css": "css", ".scss": "scss", ".sass": "scss", ".less": "css", ".sql": "sql",
    ".sh": "bash", ".bash": "bash", ".zsh": "bash", ".ps1": "powershell",
    ".psm1": "powershell", ".bat": "bat", ".cmd": "bat", ".c": "c", ".h": "c",
    ".cpp": "cpp", ".cc": "cpp", ".cxx": "cpp", ".hpp": "cpp", ".hh": "cpp", ".cs": "csharp",
    ".java": "java", ".kt": "kotlin", ".kts": "kotlin", ".go": "go", ".rs": "rust",
    ".rb": "ruby", ".php": "php", ".pl": "perl", ".pm": "perl", ".lua": "lua", ".r": "r",
    ".swift": "swift", ".scala": "scala", ".dart": "dart", ".hs": "haskell",
    ".m": "matlab", ".tex": "latex", ".graphql": "graphql", ".gql": "graphql",
    ".diff": "diff", ".patch": "diff", ".vue": "html", ".svelte": "html",
    ".gradle": "kotlin", ".dockerfile": "dockerfile", ".mk": "makefile",
}
_NAMED = {"dockerfile": "dockerfile", "makefile": "makefile", ".gitignore": "ini",
          ".gitattributes": "ini", ".editorconfig": "ini", ".env": "ini"}
# Envoi du téléphone ou de VS Code, rangé par le Relay sous « <file_id>_<nom> »
_UPLOAD_PREFIX = re.compile(r"^[0-9a-f]{16}_(?=.)")


class PreviewError(Exception):
    """Aperçu impossible : message déjà traduit, montré dans la modale."""


def display_name(path: str, upload_dir: Optional[str] = None) -> str:
    """Nom du fichier tel que l'utilisateur l'a envoyé (sans l'identifiant du Relay)."""
    name = os.path.basename(path)
    if upload_dir and os.path.normcase(os.path.dirname(os.path.abspath(path))) == \
            os.path.normcase(os.path.abspath(upload_dir)):
        return _UPLOAD_PREFIX.sub("", name)
    return name


def _encoded(path: str) -> str:
    with open(path, "rb") as handle:
        return base64.b64encode(handle.read()).decode("ascii")


def _text(path: str) -> Dict[str, Any]:
    """Début d'un fichier texte, décodé comme dans la fenêtre (BOM, UTF-16, cp1252)."""
    # pylint: disable=import-outside-toplevel
    from interfaces.desktop.files import NotTextError, read_text_preview

    try:
        text, truncated = read_text_preview(path, TEXT_MAX)
    except NotTextError as exc:
        raise PreviewError(str(exc)) from exc
    return {"text": text, "truncated": truncated}


def _language(path: str) -> str:
    name = os.path.basename(path).lower()
    return _LANGUAGES.get(os.path.splitext(name)[1], _NAMED.get(name, ""))


def build_preview(path: str, name: Optional[str] = None) -> Dict[str, Any]:
    """Aperçu d'un fichier pour la modale : genre, nom, taille et contenu affichable.

    Raises:
        PreviewError: fichier introuvable ou illisible (message traduit)
    """
    try:
        stat = os.stat(path)
    except OSError as exc:
        raise PreviewError(tr("files.notFound")) from exc
    if not os.path.isfile(path):
        raise PreviewError(tr("files.notFound"))
    suffix = Path(path).suffix.lower()
    preview: Dict[str, Any] = {
        "name": name or os.path.basename(path),
        "size": stat.st_size,
        "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(timespec="seconds"),
        "kind": "none",
    }
    try:
        if suffix in _IMAGES:
            if stat.st_size <= INLINE_MAX:
                preview.update(kind="image", mime=_IMAGES[suffix], data=_encoded(path))
                if suffix == ".svg":
                    preview.update(_text(path), language="xml")
        elif suffix in _AUDIO or suffix in _VIDEO:
            if stat.st_size <= INLINE_MAX:
                kind = "audio" if suffix in _AUDIO else "video"
                preview.update(kind=kind, mime=(_AUDIO.get(suffix) or _VIDEO[suffix]),
                               data=_encoded(path))
        elif suffix in _DOCUMENTS:
            if stat.st_size <= DOCUMENT_MAX:
                # pylint: disable=import-outside-toplevel
                from interfaces.document_preview import build_document_preview, document_summary

                preview.update(kind="document",
                               html=build_document_preview(path, preview["name"]),
                               label=document_summary(path)["label"])
                if suffix in _SOURCES:
                    try:
                        preview.update(_text(path), language=_SOURCES[suffix])
                    except PreviewError:
                        pass  # pas du texte (octet nul) : la page seule
        elif suffix in _HTML:
            preview.update(_text(path), kind="html", language="html")
        else:
            # Code, texte, ou tout fichier qui se lit comme du texte
            preview.update(_text(path), kind="text", language=_language(path))
    except PreviewError:
        # Pas du texte : rien d'affichable, le téléchargement reste
        preview["kind"] = "none"
        for key in ("text", "truncated", "language"):
            preview.pop(key, None)
    except OSError as exc:
        raise PreviewError(tr("files.readFailed", error=exc.strerror or exc)) from exc
    return preview


def build_download(path: str, name: Optional[str] = None) -> Dict[str, Any]:
    """Le fichier lui-même (base64), pour l'enregistrer sur le téléphone.

    Raises:
        PreviewError: introuvable, trop gros ou illisible (message traduit)
    """
    try:
        size = os.path.getsize(path)
    except OSError as exc:
        raise PreviewError(tr("files.notFound")) from exc
    if size > DOWNLOAD_MAX:
        raise PreviewError(tr("relay.fileTooBig", mb=DOWNLOAD_MAX // (1024 * 1024)))
    shown = name or os.path.basename(path)
    try:
        data = _encoded(path)
    except OSError as exc:
        raise PreviewError(tr("files.readFailed", error=exc.strerror or exc)) from exc
    return {"name": shown, "size": size, "download": True, "data": data,
            "mime": mimetypes.guess_type(shown)[0] or "application/octet-stream"}
