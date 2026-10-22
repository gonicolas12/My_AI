"""Utilitaires de citations numérotées pour la recherche web et le RAG.

Objectif : transformer une liste de sources (URLs, éventuellement avec titre)
en un bloc Markdown numéroté ``[n] [label](url)``, et inversement reconstruire
la table ``n → url`` depuis un texte déjà formaté, ou réduire ce bloc aux
sources qu'une réponse cite. Le rendu cliquable des marqueurs ``[n]`` est
assuré côté GUI (markdown_formatting).

100 % local, aucune dépendance réseau.
"""

from __future__ import annotations

import re
from typing import Dict, List, Set, Tuple

_URL_RE = re.compile(r"https?://[^\s)\]]+")
_MD_LINK_RE = re.compile(r"\[([^\]]+)\]\((https?://[^)]+)\)")
# Bloc « Sources » : [n] [label](url)  ou  [n] url
_CITATION_RE = re.compile(
    r"\[(\d{1,3})\]\s*(?:\[[^\]]*\]\()?(https?://[^)\s]+)"
)
# Marqueur d'une réponse : [n], ou [1, 3] pour plusieurs sources
_MARKER_RE = re.compile(r"\[(\d{1,3}(?:\s*,\s*\d{1,3})*)\]")
# Numéro en tête d'une ligne du bloc « Sources »
_SOURCE_LINE_RE = re.compile(r"\s*\[(\d{1,3})\]")

DEFAULT_HEADER = "📚 **Sources**"

# Consigne qui précède ce bloc dans un résultat de recherche web
# (models/internet_search.py) : le modèle le recopie à la fin de sa réponse.
SOURCES_NOTE = (
    "Pour répondre : appuie-toi uniquement sur ces sources, sans ajouter de "
    "chiffre, de note ou de rang qu'elles ne donnent pas, place le marqueur [n] "
    "après chaque information qui en vient, et termine ta réponse par ce bloc, "
    "recopié tel quel, sans autre liste de sources :"
)

# Début de ce bloc quand le modèle le recopie : séquences d'arrêt, après
# lesquelles l'appelant l'écrit lui-même, réduit aux sources citées
# (sources_tail). Seulement l'en-tête exact : un « 📚 » décoratif en tête de
# ligne ne doit pas couper la réponse.
SOURCES_STOP = ["\n📚 **Sources", "\n📚 Sources"]


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


def cited_numbers(text: str) -> Set[int]:
    """Numéros des sources que citent les marqueurs ``[n]`` d'un texte."""
    numbers: Set[int] = set()
    for m in _MARKER_RE.finditer(text or ""):
        numbers.update(int(n) for n in m.group(1).split(","))
    return numbers


def keep_cited_sources(block: str, text: str) -> str:
    """Bloc de sources réduit à celles que ``text`` cite, numéros gardés.

    Le bloc entier si le texte n'en cite aucune : ses liens restent utiles.
    """
    cited = cited_numbers(text)
    lines = (block or "").strip().splitlines()
    numbers = [int(m.group(1)) if m else None for m in map(_SOURCE_LINE_RE.match, lines)]
    if not cited.intersection(numbers):
        return "\n".join(lines)
    return "\n".join(
        line for line, n in zip(lines, numbers) if n is None or n in cited
    )


def sources_block(text: str) -> str:
    """Bloc 📚 Sources d'un résultat de recherche web (après SOURCES_NOTE), ou "".

    Une ancienne réponse et son propre bloc (résultat de la mémoire, par
    exemple) n'en ont pas : elle n'est pas à compléter.
    """
    return (text or "").partition(SOURCES_NOTE)[2].strip()


def sources_tail(answer: str, block: str) -> str:
    """Fin d'une réponse arrêtée au début du bloc de sources (SOURCES_STOP).

    Ce bloc, réduit aux sources qu'elle cite (numéros gardés), après une
    ligne vide ; rien sans réponse ou sans bloc.
    """
    if not answer or not block:
        return ""
    newlines = len(answer) - len(answer.rstrip("\n"))
    return "\n" * max(0, 2 - newlines) + keep_cited_sources(block, answer)
