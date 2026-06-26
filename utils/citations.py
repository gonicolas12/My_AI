"""Utilitaires de citations numérotées pour la recherche web et le RAG.

Objectif : transformer une liste de sources (URLs, éventuellement avec titre)
en un bloc Markdown numéroté ``[n] [label](url)``, et inversement reconstruire
la table ``n → url`` depuis un texte déjà formaté. Le rendu cliquable des
marqueurs ``[n]`` est assuré côté GUI (markdown_formatting).

100 % local, aucune dépendance réseau.
"""

from __future__ import annotations

import re
from typing import Dict, List, Tuple

_URL_RE = re.compile(r"https?://[^\s)\]]+")
_MD_LINK_RE = re.compile(r"\[([^\]]+)\]\((https?://[^)]+)\)")
# Bloc « Sources » : [n] [label](url)  ou  [n] url
_CITATION_RE = re.compile(
    r"\[(\d{1,3})\]\s*(?:\[[^\]]*\]\()?(https?://[^)\s]+)"
)

DEFAULT_HEADER = "📚 **Sources**"


def _clean_url(url: str) -> str:
    return url.rstrip(".,;:) ")


def _domain(url: str) -> str:
    """Nom de domaine lisible (sans schéma ni www.) pour servir de label."""
    m = re.match(r"https?://([^/]+)", url)
    host = m.group(1) if m else url
    return host[4:] if host.startswith("www.") else host


def extract_sources(text: str) -> List[Tuple[str, str]]:
    """Extrait une liste ordonnée et dédupliquée de ``(label, url)`` d'un texte.

    Les liens Markdown ``[label](url)`` sont privilégiés (label fiable) ; les
    URLs nues restantes sont ajoutées avec le domaine comme label.
    """
    pairs: List[Tuple[str, str]] = []
    seen = set()
    for label, url in _MD_LINK_RE.findall(text or ""):
        u = _clean_url(url)
        if u not in seen:
            seen.add(u)
            pairs.append((label.strip() or _domain(u), u))
    for u in _URL_RE.findall(text or ""):
        u = _clean_url(u)
        if u not in seen:
            seen.add(u)
            pairs.append((_domain(u), u))
    return pairs


def build_numbered_sources(
    pairs: List[Tuple[str, str]], header: str = DEFAULT_HEADER, limit: int = 8
) -> str:
    """Construit un bloc Markdown de sources numérotées cliquables.

    ``pairs`` : liste de ``(label, url)``. Retourne "" si vide.
    """
    if not pairs:
        return ""
    lines = [header]
    for i, (label, url) in enumerate(pairs[:limit], 1):
        lines.append(f"[{i}] [{label}]({url})")
    return "\n".join(lines)


def parse_citation_map(text: str) -> Dict[int, str]:
    """Reconstruit la table ``{n: url}`` depuis un bloc de sources numérotées."""
    mapping: Dict[int, str] = {}
    for m in _CITATION_RE.finditer(text or ""):
        n = int(m.group(1))
        mapping.setdefault(n, _clean_url(m.group(2)))
    return mapping
