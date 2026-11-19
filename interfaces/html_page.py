"""
Page HTML d'un fichier du disque, pour son aperçu : ses fichiers voisins dedans

Affichée dans une iframe isolée (/preview/<id> dans la fenêtre, srcdoc sur le
téléphone et dans VS Code), une page n'a plus son adresse sur le disque : sa
feuille de style « style.css », ses scripts et ses images relatifs ne se
chargent pas (vu avec web/index.html : titre noir à empattements au lieu du
style du projet). Ceux de son dossier, et en dessous, sont mis dans la page :

  <link rel="stylesheet" href="…">   → <style>, ses url(…) d'images en data:
  <script src="…"></script>          → <script> ; defer ou async : en fin de
                                        page, là où ils se seraient exécutés
  <img src="…">, url(…) d'un <style> → data:

Un fichier hors du dossier de la page n'est jamais lu (« ../secret.css » garde
son adresse), comme les images d'un Markdown ; ni une adresse web, ni un chemin
absolu. Les polices restent dehors (la vue de VS Code refuse les data: de
police). La source reste telle quelle pour l'onglet Code : la page complétée
s'affiche à côté (« page »). Mêmes règles dans l'extension VS Code
(src/filePreview.ts), qui lit elle-même les fichiers de son workspace.
"""

import base64
import html
import os
import re
from typing import Dict, List, Optional
from urllib.parse import unquote

HTML_SUFFIXES = frozenset({".html", ".htm", ".xhtml"})

# Un fichier mis dans la page : au plus ; tous ensemble : au plus
ASSET_MAX = 3 * 1024 * 1024
ASSETS_TOTAL = 8 * 1024 * 1024

_IMAGES = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
           ".gif": "image/gif", ".webp": "image/webp", ".bmp": "image/bmp",
           ".ico": "image/x-icon", ".avif": "image/avif", ".svg": "image/svg+xml"}

# Adresse jamais lue sur le disque : avec un schéma (https:, data:, C:), absolue, ancre
_NOT_RELATIVE = re.compile(r"^(?:[a-z][a-z0-9+.-]*:|[\\/#])", re.IGNORECASE)
_LINK = re.compile(r"<link\b[^>]*>", re.IGNORECASE)
# Script externe : vide entre ses balises
_SCRIPT = re.compile(r"<script\b([^>]*)>\s*</script\s*>", re.IGNORECASE)
_IMG = re.compile(r"<img\b[^>]*>", re.IGNORECASE)
_STYLE = re.compile(r"(<style\b[^>]*>)([\s\S]*?)(</style\s*>)", re.IGNORECASE)
_CSS_URL = re.compile(r"url\(\s*(['\"]?)([^'\")]+?)\1\s*\)", re.IGNORECASE)
_LAST_BODY_END = re.compile(r"</body\s*>(?![\s\S]*</body\s*>)", re.IGNORECASE)


def _attribute(tag: str, name: str) -> Optional[str]:
    """Valeur d'un attribut d'une balise (entre guillemets ou non), ou None."""
    match = re.search(rf"\s{name}\s*=\s*(?:\"([^\"]*)\"|'([^']*)'|([^\s\"'>]+))", tag,
                      re.IGNORECASE)
    if not match:
        return None
    return next(group for group in match.groups() if group is not None)


def _without(attributes: str, *names: str) -> str:
    """Attributs d'une balise sans ceux nommés (avec ou sans valeur)."""
    for name in names:
        attributes = re.sub(
            rf"\s{name}(?:\s*=\s*(?:\"[^\"]*\"|'[^']*'|[^\s\"'>]+))?(?=[\s/>]|$)", "",
            attributes, flags=re.IGNORECASE)
    return attributes


def _inside(path: str, folder: str) -> bool:
    try:
        return path != folder and os.path.commonpath(
            [os.path.normcase(path), os.path.normcase(folder)]) == os.path.normcase(folder)
    except ValueError:  # autre lecteur sous Windows
        return False


class _Assets:
    """Fichiers du dossier de la page qu'elle désigne, dans la limite de taille."""

    def __init__(self, page_path: str):
        self.folder = os.path.dirname(os.path.abspath(page_path))
        self.budget = ASSETS_TOTAL

    def path(self, ref: Optional[str], base: str) -> Optional[str]:
        """Fichier qu'une adresse relative (à base) désigne, s'il est dans le dossier de la page."""
        ref = (ref or "").strip()
        if not ref or _NOT_RELATIVE.match(ref):
            return None
        relative = unquote(ref.split("#", 1)[0].split("?", 1)[0])
        if not relative:
            return None
        target = os.path.normpath(os.path.join(base, relative))
        return target if _inside(target, self.folder) and os.path.isfile(target) else None

    def read(self, path: str) -> Optional[bytes]:
        try:
            if os.path.getsize(path) > min(ASSET_MAX, self.budget):
                return None
            with open(path, "rb") as handle:
                data = handle.read(ASSET_MAX + 1)
        except OSError:
            return None
        if len(data) > min(ASSET_MAX, self.budget):
            return None
        self.budget -= len(data)
        return data

    def text(self, path: str) -> Optional[str]:
        data = self.read(path)
        return None if data is None else data.decode("utf-8-sig", errors="replace")

    def image(self, ref: Optional[str], base: str) -> Optional[str]:
        """Adresse data: d'une image du dossier de la page, ou None (l'adresse reste)."""
        path = self.path(ref, base)
        mime = _IMAGES.get(os.path.splitext(path)[1].lower()) if path else None
        data = self.read(path) if mime else None
        if data is None:
            return None
        return f"data:{mime};base64,{base64.b64encode(data).decode('ascii')}"

    def css(self, css: str, base: str) -> str:
        """Feuille de style, ses images relatives (à base) en data:."""
        def swap(match: re.Match) -> str:
            url = self.image(match.group(2), base)
            return f'url("{url}")' if url else match.group(0)
        return _CSS_URL.sub(swap, css)


def page_with_assets(source: str, page_path: str) -> str:
    """La page, ses feuilles de style, scripts et images de son dossier dedans.

    Rien à mettre (ou rien de lisible) : la source telle quelle.
    """
    assets = _Assets(page_path)
    folder = assets.folder
    page = _STYLE.sub(lambda match: match.group(1) + assets.css(match.group(2), folder)
                      + match.group(3), source)

    def stylesheet(match: re.Match) -> str:
        tag = match.group(0)
        href = _attribute(tag, "href")
        if "stylesheet" not in (_attribute(tag, "rel") or "").lower().split():
            return tag
        path = assets.path(href, folder)
        sheet = assets.text(path) if path else None
        if sheet is None or path is None:
            return tag
        sheet = assets.css(sheet, os.path.dirname(path)).replace("</style", "<\\/style")
        media = _attribute(tag, "media")
        shown = f' media="{html.escape(media)}"' if media else ""
        return f'<style data-href="{html.escape(href or "")}"{shown}>{sheet}</style>'

    page = _LINK.sub(stylesheet, page)
    deferred: List[str] = []

    def script(match: re.Match) -> str:
        attributes = match.group(1)
        src = _attribute(attributes, "src")
        path = assets.path(src, folder)
        code = assets.text(path) if path else None
        if code is None:
            return match.group(0)
        kept = _without(attributes, "src", "defer", "async", "integrity", "crossorigin")
        code = code.replace("</script", "<\\/script")
        tag = f'<script{kept} data-src="{html.escape(src or "")}">{code}</script>'
        module = (_attribute(attributes, "type") or "").strip().lower() == "module"
        if not module and re.search(r"\s(?:defer|async)(?=[\s=/>]|$)", attributes, re.IGNORECASE):
            deferred.append(tag)
            return ""
        return tag

    page = _SCRIPT.sub(script, page)
    if deferred:
        end = _LAST_BODY_END.search(page)
        tail = "".join(deferred)
        page = page[:end.start()] + tail + page[end.start():] if end else page + tail

    def image(match: re.Match) -> str:
        tag = match.group(0)
        url = assets.image(_attribute(tag, "src"), folder)
        if not url:
            return tag
        return re.sub(r"(\ssrc\s*=\s*)(?:\"[^\"]*\"|'[^']*'|[^\s\"'>]+)",
                      lambda found: f'{found.group(1)}"{url}"', tag, count=1, flags=re.IGNORECASE)

    return _IMG.sub(image, page)


def preview_fields(source: str, page_path: str) -> Dict[str, str]:
    """{"page": …} quand la page a des fichiers voisins à elle, sinon rien."""
    page = page_with_assets(source, page_path)
    return {"page": page} if page != source else {}
