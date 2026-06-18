"""
Détection et préparation des « artifacts » (HTML / SVG rendables).

Module 100% local, sans dépendance réseau, partagé par :
- le GUI desktop (volet de preview + bouton « Aperçu »),
- le serveur Relay (génération du fichier servi à l'iframe mobile).

La détection réutilise la même convention de blocs de code Markdown que le
reste du projet (cf. ``interfaces/gui/syntax_highlighting.py``) : des fences
``` avec un langage optionnel.
"""

from __future__ import annotations

import os
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

# Racine projet (…/My_AI). Ce fichier est dans …/My_AI/interfaces/artifacts.py
PROJECT_ROOT = Path(__file__).resolve().parent.parent
ARTIFACTS_DIR = PROJECT_ROOT / "outputs" / "artifacts"

# Même motif de fence que _preanalyze_code_blocks : ```langage\n…```
_FENCE_RE = re.compile(r"```([\w+#.-]+)?[ \t]*\n?(.*?)```", re.DOTALL)

# Langages considérés comme « rendables » dans un navigateur / webview.
_HTML_LANGS = {"html", "htm", "xhtml"}
_SVG_LANGS = {"svg"}
# xml n'est rendable que s'il contient réellement du SVG/HTML (voir _classify).

# Heuristiques de détection « c'est du HTML » sur le contenu brut.
_HTML_HINT_RE = re.compile(
    r"<!doctype html|<html[\s>]|<body[\s>]|<head[\s>]|<div[\s>]|<table[\s>]",
    re.IGNORECASE,
)
_SVG_HINT_RE = re.compile(r"<svg[\s>]", re.IGNORECASE)


@dataclass
class Artifact:
    """Un fragment rendable extrait d'une réponse de l'IA."""

    kind: str  # "html" | "svg"
    code: str  # le code source brut du fragment
    title: str = "Artifact"
    language: str = ""  # langage de la fence d'origine ("html", "svg", "xml"…)
    index: int = 0  # position du bloc dans la réponse (0-based)

    @property
    def is_full_document(self) -> bool:
        """True si le code est déjà un document HTML complet (<html>/<!doctype>)."""
        head = self.code.lstrip()[:200].lower()
        return head.startswith("<!doctype") or head.startswith("<html") or "<html" in head[:50]


def _classify(language: str, code: str) -> Optional[str]:
    """Retourne 'html', 'svg' ou None selon le langage de fence + le contenu."""
    lang = (language or "").lower()
    code_stripped = code.strip()
    if not code_stripped:
        return None

    if lang in _SVG_LANGS or _SVG_HINT_RE.search(code_stripped[:300]):
        # Un <svg> seul est rendable tel quel.
        if _SVG_HINT_RE.search(code_stripped):
            return "svg"

    if lang in _HTML_LANGS:
        return "html"

    if lang in {"xml", ""} or lang not in _HTML_LANGS:
        # Sans langage explicite ou xml : on rend uniquement si ça « ressemble »
        # à du HTML (évite de proposer un aperçu pour du JSON, du Python, etc.).
        if _HTML_HINT_RE.search(code_stripped):
            return "html"

    return None


def _derive_title(code: str, kind: str, index: int) -> str:
    """Déduit un titre lisible : <title>, premier <h1>, ou défaut."""
    m = re.search(r"<title[^>]*>(.*?)</title>", code, re.IGNORECASE | re.DOTALL)
    if m and m.group(1).strip():
        return m.group(1).strip()[:80]
    m = re.search(r"<h1[^>]*>(.*?)</h1>", code, re.IGNORECASE | re.DOTALL)
    if m:
        text = re.sub(r"<[^>]+>", "", m.group(1)).strip()
        if text:
            return text[:80]
    label = "SVG" if kind == "svg" else "Page HTML"
    return f"{label} #{index + 1}"


def detect_artifacts(text: str) -> List[Artifact]:
    """
    Extrait tous les artifacts rendables (HTML/SVG) d'une réponse Markdown.

    Args:
        text: le texte brut de la réponse (avec ses fences ```).

    Returns:
        La liste des Artifact détectés, dans l'ordre d'apparition.
    """
    if not text or "```" not in text:
        return []

    artifacts: List[Artifact] = []
    for idx, match in enumerate(_FENCE_RE.finditer(text)):
        language = (match.group(1) or "").strip()
        code = (match.group(2) or "").strip()
        kind = _classify(language, code)
        if kind is None:
            continue
        artifacts.append(
            Artifact(
                kind=kind,
                code=code,
                title=_derive_title(code, kind, len(artifacts)),
                language=language.lower(),
                index=idx,
            )
        )
    return artifacts


def has_artifact(text: str) -> bool:
    """Raccourci : True si la réponse contient au moins un artifact rendable."""
    return bool(detect_artifacts(text))


# ── Préparation du document HTML rendable ──────────────────────────────────

# Thème sombre cohérent avec le GUI (cf. interfaces/modern_styles.py).
_PREVIEW_WRAPPER = """<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<style>
  html, body {{ margin: 0; padding: 0; }}
  body {{
    background: #212121;
    color: #ffffff;
    font-family: "Segoe UI", system-ui, sans-serif;
    padding: 16px;
    box-sizing: border-box;
  }}
</style>
</head>
<body>
{body}
</body>
</html>
"""


def build_preview_document(artifact: Artifact) -> str:
    """
    Construit un document HTML complet et autonome pour le rendu.

    - Si l'artifact est déjà un document complet, on le renvoie tel quel.
    - Pour un fragment HTML ou un <svg>, on l'enveloppe dans une page sombre
      cohérente avec le thème du GUI.
    """
    if artifact.kind == "html" and artifact.is_full_document:
        return artifact.code

    body = artifact.code
    if artifact.kind == "svg":
        # Centrer le SVG dans la page.
        body = f'<div style="display:flex;justify-content:center">{body}</div>'

    return _PREVIEW_WRAPPER.format(
        title=_html_escape(artifact.title), body=body
    )


def _html_escape(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def write_artifact_html(artifact: Artifact, directory: Optional[Path] = None) -> Path:
    """
    Écrit le document de preview dans outputs/artifacts/ et retourne son chemin.

    Utilisé par le fallback « Ouvrir dans le navigateur » (desktop) et par la
    route de service de l'iframe (mobile).
    """
    target_dir = Path(directory) if directory else ARTIFACTS_DIR
    target_dir.mkdir(parents=True, exist_ok=True)

    suffix = "svg" if artifact.kind == "svg" else "html"
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    filename = f"artifact_{timestamp}_{artifact.index}.html"
    filepath = target_dir / filename

    document = build_preview_document(artifact)
    filepath.write_text(document, encoding="utf-8")
    return filepath


def detect_html_files(directory: Optional[Path] = None) -> List[Path]:
    """
    Liste les fichiers .html générés dans outputs/ (hors dossier artifacts/),
    pour proposer un aperçu de documents HTML produits par les générateurs.
    """
    base = Path(directory) if directory else (PROJECT_ROOT / "outputs")
    if not base.exists():
        return []
    files = []
    for entry in base.glob("*.html"):
        files.append(entry)
    return sorted(files, key=lambda p: p.stat().st_mtime, reverse=True)
