"""
Parseur Markdown → blocs de document

Module 100% local, sans dépendance externe, partagé par tous les backends de
génération de documents (DOCX, PDF, PPTX, XLSX) de ``document_generator.py``.

Le but n'est pas de couvrir CommonMark : c'est de convertir fidèlement ce
qu'un LLM produit réellement (titres ``#``, listes, tableaux, fences ```` ``` ````,
gras/italique) en une structure que python-docx, reportlab, python-pptx et
openpyxl savent chacun rendre à leur façon.

La convention de fences est la même que le reste du projet
(cf. ``interfaces/artifacts.py`` et ``interfaces/gui/syntax_highlighting.py``).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

# ── Blocs ──────────────────────────────────────────────────────────────────

# Un fragment de texte inline avec ses styles actifs.
# styles ⊆ {"bold", "italic", "code"} ; url non vide = lien.
Inline = Tuple[str, frozenset, Optional[str]]


@dataclass
class Heading:
    """Titre de niveau 1 à 6."""

    level: int
    inlines: List[Inline] = field(default_factory=list)

    @property
    def text(self) -> str:
        return "".join(part for part, _styles, _url in self.inlines)


@dataclass
class Paragraph:
    """Paragraphe de texte courant."""

    inlines: List[Inline] = field(default_factory=list)

    @property
    def text(self) -> str:
        return "".join(part for part, _styles, _url in self.inlines)


@dataclass
class ListItem:
    """Entrée de liste, avec son niveau d'indentation (0 = racine)."""

    inlines: List[Inline]
    level: int = 0

    @property
    def text(self) -> str:
        return "".join(part for part, _styles, _url in self.inlines)


@dataclass
class ListBlock:
    """Liste à puces ou numérotée, éventuellement imbriquée."""

    ordered: bool
    items: List[ListItem] = field(default_factory=list)


@dataclass
class Table:
    """Tableau Markdown (pipe table) avec sa ligne d'en-tête."""

    header: List[str] = field(default_factory=list)
    rows: List[List[str]] = field(default_factory=list)


@dataclass
class CodeBlock:
    """Bloc de code délimité par des fences."""

    language: str
    code: str


@dataclass
class Quote:
    """Citation (« > »)."""

    inlines: List[Inline] = field(default_factory=list)

    @property
    def text(self) -> str:
        return "".join(part for part, _styles, _url in self.inlines)


@dataclass
class Rule:
    """Séparateur horizontal."""


Block = object  # Union des dataclasses ci-dessus (typage volontairement souple)


# ── Motifs ─────────────────────────────────────────────────────────────────

_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$")
_BULLET_RE = re.compile(r"^(\s*)[-*+]\s+(.*)$")
_ORDERED_RE = re.compile(r"^(\s*)(\d+)[.)]\s+(.*)$")
_FENCE_OPEN_RE = re.compile(r"^\s*```([\w+#.-]*)\s*$")
_FENCE_CLOSE_RE = re.compile(r"^\s*```\s*$")
_RULE_RE = re.compile(r"^\s*([-*_])(?:\s*\1){2,}\s*$")
_QUOTE_RE = re.compile(r"^\s*>\s?(.*)$")
_TABLE_ROW_RE = re.compile(r"^\s*\|(.+)\|\s*$")
_TABLE_SEP_RE = re.compile(r"^\s*\|?[\s:|-]+\|[\s:|-]*$")

# Inline : code d'abord (son contenu ne doit pas être réinterprété), puis lien,
# puis gras+italique, puis gras, puis italique. L'ordre des alternatives fait foi.
#
# Les délimiteurs portent des gardes d'assertion pour gérer l'imbrication :
# - gras : la fermeture `**` ne doit pas être suivie d'un `*`, sinon
#   `**gras *ital***` se fermerait trop tôt et laisserait une étoile orpheline ;
# - italique : l'ouverture ne doit pas être suivie d'un `*` ni la fermeture
#   précédée d'un `*`, faute de quoi `*ital **gras** fin*` s'arrêterait sur la
#   première étoile du gras interne.
_INLINE_RE = re.compile(
    r"(?P<code>`+[^`]+`+)"
    r"|(?P<link>\[(?P<link_text>[^\]]*)\]\((?P<link_url>[^)\s]+)[^)]*\))"
    r"|(?P<bolditalic>\*\*\*(?P<bi_text>[^\n]+?)\*\*\*"
    r"|(?<!\w)___(?P<bi_text2>[^\n]+?)___(?!\w))"
    r"|(?P<bold>\*\*(?P<bold_text>[^\n]+?)\*\*(?!\*)"
    r"|(?<!\w)__(?P<bold_text2>[^\n]+?)__(?!\w))"
    r"|(?P<italic>\*(?!\*)(?P<italic_text>[^\n]+?)(?<!\*)\*(?!\*)"
    r"|(?<!\w)_(?!_)(?P<italic_text2>[^\n]+?)(?<!_)_(?!\w))",
)

# Indentation (en espaces) correspondant à un niveau de liste.
_INDENT_PER_LEVEL = 2
# Profondeur d'imbrication maximale conservée (au-delà : aplati).
_MAX_LIST_LEVEL = 4


# ── Inline ─────────────────────────────────────────────────────────────────


def parse_inlines(text: str) -> List[Inline]:
    """
    Découpe une ligne en fragments stylés.

    Args:
        text: une ligne de Markdown, sans son préfixe de bloc.

    Returns:
        La liste des ``(texte, styles, url)`` dans l'ordre d'apparition.
        ``styles`` est un frozenset parmi {"bold", "italic", "code"} et ``url``
        vaut None sauf pour un lien.
    """
    if not text:
        return []

    inlines: List[Inline] = []
    cursor = 0

    for match in _INLINE_RE.finditer(text):
        if match.start() > cursor:
            inlines.append((text[cursor:match.start()], frozenset(), None))

        if match.group("code"):
            # Retirer les backticks encadrants (1 à n, symétriques).
            raw = match.group("code")
            ticks = len(raw) - len(raw.lstrip("`"))
            inlines.append((raw[ticks:-ticks] if ticks else raw, frozenset({"code"}), None))
        elif match.group("link"):
            label = match.group("link_text") or match.group("link_url")
            inlines.append((label, frozenset(), match.group("link_url")))
        elif match.group("bolditalic"):
            content = match.group("bi_text") or match.group("bi_text2") or ""
            for part, styles, url in parse_inlines(content):
                inlines.append((part, styles | {"bold", "italic"}, url))
        elif match.group("bold"):
            content = match.group("bold_text") or match.group("bold_text2") or ""
            # Le gras peut contenir de l'italique : on ré-analyse et on fusionne.
            for part, styles, url in parse_inlines(content):
                inlines.append((part, styles | {"bold"}, url))
        elif match.group("italic"):
            content = match.group("italic_text") or match.group("italic_text2") or ""
            for part, styles, url in parse_inlines(content):
                inlines.append((part, styles | {"italic"}, url))

        cursor = match.end()

    if cursor < len(text):
        inlines.append((text[cursor:], frozenset(), None))

    # Écarter les fragments vides produits par les découpes successives.
    return [item for item in inlines if item[0]]


def inlines_to_text(inlines: List[Inline]) -> str:
    """Aplati une liste de fragments en texte brut (sans marqueurs)."""
    return "".join(part for part, _styles, _url in inlines)


# ── Blocs ──────────────────────────────────────────────────────────────────


def _split_table_row(line: str) -> List[str]:
    """Découpe une ligne « | a | b | » en cellules nettoyées."""
    match = _TABLE_ROW_RE.match(line)
    inner = match.group(1) if match else line.strip().strip("|")
    return [cell.strip() for cell in inner.split("|")]


def _list_level(indent: str) -> int:
    """Convertit l'indentation d'une puce en niveau d'imbrication."""
    width = len(indent.replace("\t", " " * _INDENT_PER_LEVEL))
    return min(width // _INDENT_PER_LEVEL, _MAX_LIST_LEVEL)


def parse_markdown(text: str) -> List[Block]:
    """
    Convertit du Markdown en liste de blocs de document.

    Args:
        text: le contenu Markdown complet.

    Returns:
        La liste des blocs (Heading, Paragraph, ListBlock, Table, CodeBlock,
        Quote, Rule) dans l'ordre du document.
    """
    if not text or not text.strip():
        return []

    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    blocks: List[Block] = []

    # Accumulateurs des blocs multi-lignes en cours de construction.
    paragraph: List[str] = []
    quote: List[str] = []
    current_list: Optional[ListBlock] = None
    table_lines: List[str] = []

    def flush_paragraph() -> None:
        if paragraph:
            joined = " ".join(part.strip() for part in paragraph).strip()
            if joined:
                blocks.append(Paragraph(parse_inlines(joined)))
            paragraph.clear()

    def flush_quote() -> None:
        if quote:
            joined = " ".join(part.strip() for part in quote).strip()
            if joined:
                blocks.append(Quote(parse_inlines(joined)))
            quote.clear()

    def flush_list() -> None:
        nonlocal current_list
        if current_list is not None and current_list.items:
            blocks.append(current_list)
        current_list = None

    def flush_table() -> None:
        if not table_lines:
            return
        header = _split_table_row(table_lines[0])
        rows = [_split_table_row(line) for line in table_lines[2:]]
        # Normaliser la largeur : un LLM produit parfois des lignes plus courtes.
        width = len(header)
        rows = [(row + [""] * width)[:width] for row in rows]
        blocks.append(Table(header=header, rows=rows))
        table_lines.clear()

    def flush_all() -> None:
        flush_paragraph()
        flush_quote()
        flush_list()
        flush_table()

    index = 0
    while index < len(lines):
        line = lines[index]

        # ── Bloc de code : tout est pris tel quel jusqu'à la fence fermante ──
        fence = _FENCE_OPEN_RE.match(line)
        if fence:
            flush_all()
            language = (fence.group(1) or "").strip().lower()
            index += 1
            code_lines: List[str] = []
            while index < len(lines) and not _FENCE_CLOSE_RE.match(lines[index]):
                code_lines.append(lines[index])
                index += 1
            index += 1  # consommer la fence fermante (ou la fin du texte)
            blocks.append(CodeBlock(language=language, code="\n".join(code_lines)))
            continue

        # ── Tableau : ligne de pipes suivie d'un séparateur ──
        if table_lines:
            if _TABLE_ROW_RE.match(line):
                table_lines.append(line)
                index += 1
                continue
            flush_table()
        elif (
            _TABLE_ROW_RE.match(line)
            and index + 1 < len(lines)
            and _TABLE_SEP_RE.match(lines[index + 1])
        ):
            flush_paragraph()
            flush_quote()
            flush_list()
            table_lines.append(line)
            table_lines.append(lines[index + 1])
            index += 2
            continue

        # ── Ligne vide : ferme les blocs en cours ──
        if not line.strip():
            flush_all()
            index += 1
            continue

        # ── Séparateur horizontal ──
        if _RULE_RE.match(line):
            flush_all()
            blocks.append(Rule())
            index += 1
            continue

        # ── Titre ──
        heading = _HEADING_RE.match(line)
        if heading:
            flush_all()
            blocks.append(
                Heading(level=len(heading.group(1)), inlines=parse_inlines(heading.group(2).strip()))
            )
            index += 1
            continue

        # ── Citation ──
        quoted = _QUOTE_RE.match(line)
        if quoted:
            flush_paragraph()
            flush_list()
            quote.append(quoted.group(1))
            index += 1
            continue

        # ── Listes ──
        bullet = _BULLET_RE.match(line)
        ordered = _ORDERED_RE.match(line)
        if bullet or ordered:
            flush_paragraph()
            flush_quote()
            is_ordered = ordered is not None
            indent = (ordered or bullet).group(1)
            content = ordered.group(3) if ordered else bullet.group(2)
            # Un changement de type (puces ↔ numéros) ouvre une nouvelle liste.
            if current_list is None or current_list.ordered != is_ordered:
                flush_list()
                current_list = ListBlock(ordered=is_ordered)
            current_list.items.append(
                ListItem(inlines=parse_inlines(content.strip()), level=_list_level(indent))
            )
            index += 1
            continue

        # ── Continuation d'une entrée de liste (ligne indentée sans puce) ──
        if current_list is not None and line.startswith((" ", "\t")):
            item = current_list.items[-1]
            item.inlines = item.inlines + [(" " + line.strip(), frozenset(), None)]
            index += 1
            continue

        # ── Texte courant ──
        flush_list()
        paragraph.append(line)
        index += 1

    flush_all()
    return blocks


def extract_title(blocks: List[Block]) -> str:
    """
    Retourne le premier titre de plus haut niveau, ou une chaîne vide.

    Sert à nommer un document quand l'appelant n'a pas fourni de titre.
    """
    for block in blocks:
        if isinstance(block, Heading):
            return block.text.strip()
    return ""


def strip_leading_title(blocks: List[Block], title: str) -> List[Block]:
    """
    Retire le premier bloc s'il répète le titre passé au générateur.

    Évite le doublon « titre du document » + « premier H1 identique » que les
    LLM produisent systématiquement.
    """
    if not blocks or not title:
        return blocks
    first = blocks[0]
    if isinstance(first, Heading) and first.text.strip().lower() == title.strip().lower():
        return blocks[1:]
    return blocks
