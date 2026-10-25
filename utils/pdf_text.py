"""
Texte des PDF écrits par ReportLab, dans toutes les langues de My_AI : export
des conversations (core/conversation_exporter.py) et documents rédigés par
l'IA (generators/document_generator.py).

Police : Helvetica, police standard du PDF, n'écrit que l'alphabet latin
(cp1252). Le chinois et le japonais passent par une police CID d'Adobe, connue
des lecteurs de PDF (aucun fichier à fournir) ; le coréen, le cyrillique, le
grec, l'arabe et l'hébreu par une police TrueType du système, intégrée au PDF.

Sens d'écriture : ReportLab écrit les caractères dans l'ordre logique, de
gauche à droite, sous leur forme isolée, et l'arabe sortait à l'envers, en
lettres détachées. Un paragraphe qui contient de l'arabe ou de l'hébreu est
donc coupé en lignes ici, dans l'ordre logique, puis chaque ligne est façonnée
(arabic-reshaper : formes initiale, médiane et finale, lam-alif) et mise dans
l'ordre d'affichage (python-bidi, parenthèses retournées comprises), le gras,
l'italique, les liens et le code gardant leurs balises. Sans ces deux
bibliothèques, le texte reste tel quel.
"""

import os
import re
import unicodedata
from functools import lru_cache
from itertools import groupby
from pathlib import Path
from typing import Any, Callable, Dict, Iterator, List, Optional, Sequence, Tuple

from core.i18n import current_language
from utils.logger import setup_logger

logger = setup_logger("pdf_text")

HELVETICA = ("Helvetica", "Helvetica-Bold")
# Fragment d'un paragraphe et les balises ReportLab qui l'entourent : ("mot", "<b>", "</b>")
Run = Tuple[str, str, str]

_CJK_FONTS = {"zh": "STSong-Light", "ja": "HeiseiKakuGo-W5", "ko": "HYGothic-Medium"}
# Fichiers (normal, gras) par écriture : Windows, puis Linux et matplotlib
_SYSTEM_FONT_FILES = {
    "sans": (("arial.ttf", "arialbd.ttf"), ("DejaVuSans.ttf", "DejaVuSans-Bold.ttf")),
    # PDFium (Edge, la fenêtre) n'affiche rien avec la police CID coréenne
    "ko": (("malgun.ttf", "malgunbd.ttf"), ("NanumGothic.ttf", "NanumGothicBold.ttf")),
}
_SYSTEM_FONTS: Dict[str, Optional[Tuple[str, str]]] = {}

# Hébreu, arabe (syriaque, thâna…) et leurs formes de présentation
_RTL_CHARS = re.compile(r"[\u0590-\u08FF\uFB1D-\uFDFF\uFE70-\uFEFF]")


# ── Polices ──────────────────────────────────────────────────────────────────


def _cjk_language(text: str) -> Optional[str]:
    """Chinois, japonais ou coréen dans le texte (hangul, puis kana, puis idéogrammes)."""
    hangul = kana = han = False
    for char in text:
        code = ord(char)
        if 0xAC00 <= code <= 0xD7AF or 0x1100 <= code <= 0x11FF or 0x3130 <= code <= 0x318F:
            hangul = True
        elif 0x3040 <= code <= 0x30FF or 0x31F0 <= code <= 0x31FF:
            kana = True
        elif 0x4E00 <= code <= 0x9FFF or 0x3400 <= code <= 0x4DBF:
            han = True
    if hangul:
        return "ko"
    if kana:
        return "ja"
    if han:
        # Idéogrammes seuls : kanji d'un texte japonais si l'interface l'est
        return "ja" if current_language() == "ja" else "zh"
    return None


def _outside_latin(char: str) -> bool:
    """Lettre que Helvetica n'écrit pas (hors cp1252 : cyrillique, grec, arabe, ł, ő…)."""
    if not char.isalpha():
        return False
    try:
        char.encode("cp1252")
        return False
    except UnicodeEncodeError:
        return True


def _font_dirs() -> Iterator[Path]:
    yield Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts"
    yield Path("/usr/share/fonts/truetype/dejavu")
    yield Path("/usr/share/fonts/truetype/nanum")
    yield Path("/Library/Fonts")
    try:
        import matplotlib  # pylint: disable=import-outside-toplevel
        yield Path(matplotlib.get_data_path()) / "fonts" / "ttf"
    except Exception:  # pylint: disable=broad-except
        pass  # sans matplotlib : les polices du système seulement


def _register_family(regular: str, bold: str) -> None:
    """Famille de la police : <b> et <i> du balisage ReportLab la retrouvent."""
    from reportlab.lib.fonts import addMapping  # pylint: disable=import-outside-toplevel
    for is_bold, is_italic in ((0, 0), (0, 1), (1, 0), (1, 1)):
        addMapping(regular, is_bold, is_italic, bold if is_bold else regular)


def system_font(kind: str) -> Optional[Tuple[str, str]]:
    """Police TrueType du système pour une écriture (_SYSTEM_FONT_FILES), enregistrée une fois."""
    if kind not in _SYSTEM_FONTS:
        _SYSTEM_FONTS[kind] = None
        names = (f"MyAI-{kind}", f"MyAI-{kind}-Bold")
        try:
            # pylint: disable=import-outside-toplevel
            from reportlab.pdfbase import pdfmetrics
            from reportlab.pdfbase.ttfonts import TTFont
            for folder in _font_dirs():
                regular, bold = next(((folder / r, folder / b) for r, b in _SYSTEM_FONT_FILES[kind]
                                      if (folder / r).is_file()), (None, None))
                if regular is None:
                    continue
                pdfmetrics.registerFont(TTFont(names[0], str(regular)))
                pdfmetrics.registerFont(TTFont(names[1], str(bold if bold.is_file() else regular)))
                _register_family(*names)
                _SYSTEM_FONTS[kind] = names
                break
        except Exception as exc:  # pylint: disable=broad-except
            logger.warning("Police %s du PDF indisponible : %s", kind, exc)
    return _SYSTEM_FONTS[kind]


def pdf_fonts(text: str) -> Tuple[str, str]:
    """(police, police grasse) qui écrivent le texte du PDF ; Helvetica pour le latin."""
    language = _cjk_language(text)
    korean = system_font("ko") if language == "ko" else None
    if korean:
        return korean
    if language:
        name = _CJK_FONTS[language]
        try:
            # pylint: disable=import-outside-toplevel
            from reportlab.pdfbase import pdfmetrics
            from reportlab.pdfbase.cidfonts import UnicodeCIDFont
            if name not in pdfmetrics.getRegisteredFontNames():
                pdfmetrics.registerFont(UnicodeCIDFont(name))
                _register_family(name, name)
            return name, name
        except Exception as exc:  # pylint: disable=broad-except
            logger.warning("Police %s indisponible : %s", name, exc)
    if any(_outside_latin(char) for char in text) or has_rtl(text):
        return system_font("sans") or HELVETICA
    return HELVETICA


def code_font(text: str, font: str) -> str:
    """Police du code : Courier s'il est en alphabet latin, sinon ``font``, celle du document."""
    return "Courier" if pdf_fonts(text) == HELVETICA else font


def word_wrap(font: str) -> Optional[str]:
    """Coupure des lignes par ReportLab (``wordWrap`` d'un style) : n'importe où en
    chinois et en japonais, écrits sans espaces, sinon aux espaces (None). ReportLab ne
    coupait qu'aux espaces : une phrase chinoise partait entière à la ligne suivante."""
    return "CJK" if font in (_CJK_FONTS["zh"], _CJK_FONTS["ja"]) else None


# ── Écriture de droite à gauche ──────────────────────────────────────────────


def has_rtl(text: str) -> bool:
    """Le texte contient de l'arabe ou de l'hébreu."""
    return bool(_RTL_CHARS.search(text or ""))


def rtl_paragraph(text: str) -> bool:
    """Paragraphe de droite à gauche : son premier caractère fort est arabe ou hébreu."""
    for char in text or "":
        kind = unicodedata.bidirectional(char)
        if kind in ("R", "AL"):
            return True
        if kind == "L":
            return False
    return False


@lru_cache(maxsize=1)
def _shaping() -> Optional[Tuple[Callable[[str], str], Callable[..., str]]]:
    """(reshape, get_display) d'arabic-reshaper et de python-bidi, ou None sans eux."""
    try:
        # pylint: disable=import-outside-toplevel
        from arabic_reshaper import reshape
        # Version Python de l'algorithme : celle en Rust ne retourne pas les parenthèses
        from bidi.algorithm import get_display
    except ImportError:
        logger.warning("arabic-reshaper ou python-bidi absent : arabe non façonné dans les PDF")
        return None
    return reshape, get_display


def shaping_available() -> bool:
    """L'arabe et l'hébreu des PDF peuvent être façonnés et remis dans l'ordre."""
    return _shaping() is not None


def visual(text: str, rtl: Optional[bool] = None) -> str:
    """Une ligne dans l'ordre d'affichage, lettres arabes liées ; sans arabe ni
    hébreu, telle quelle."""
    shaping = _shaping()
    if not text or shaping is None or not has_rtl(text):
        return text
    reshape, get_display = shaping
    rtl = rtl_paragraph(text) if rtl is None else rtl
    return get_display(reshape(text), base_dir="R" if rtl else "L")


def _display_order(text: str, rtl: bool) -> Optional[List[Tuple[str, int]]]:
    """(caractère affiché, rang dans ``text``) de gauche à droite, parenthèses retournées.

    get_display ne rend que le texte : les étapes de son algorithme, appelées
    une à une, disent d'où vient chaque caractère, pour que les balises du
    gras ou d'un lien le suivent. None si python-bidi les a changées.
    """
    try:
        from bidi import algorithm  # pylint: disable=import-outside-toplevel
        storage = algorithm.get_empty_storage()
        storage["base_level"] = 1 if rtl else 0
        storage["base_dir"] = "R" if rtl else "L"
        algorithm.get_embedding_levels(text, storage)
        for index, char in enumerate(storage["chars"]):
            char["index"] = index
        algorithm.explicit_embed_and_overrides(storage)
        algorithm.resolve_weak_types(storage)
        algorithm.resolve_neutral_types(storage, False)
        algorithm.resolve_implicit_levels(storage, False)
        algorithm.reorder_resolved_levels(storage, False)
        algorithm.apply_mirroring(storage, False)
        return [(char["ch"], char["index"]) for char in storage["chars"]]
    except Exception as exc:  # pylint: disable=broad-except
        logger.warning("Ordre d'affichage de python-bidi indisponible, texte sans styles : %s", exc)
        return None


def _measure(font: str, size: float) -> Callable[[str], float]:
    """Largeur d'un texte une fois façonné (les formes liées n'ont pas la largeur des isolées)."""
    from reportlab.pdfbase.pdfmetrics import stringWidth  # pylint: disable=import-outside-toplevel
    shaping = _shaping()
    reshape = shaping[0] if shaping else (lambda text: text)
    return lambda text: stringWidth(reshape(text), font, size)


def _spans(text: str, measure: Callable[[str], float], width: float) -> List[Tuple[int, int]]:
    """Lignes d'un paragraphe sans saut de ligne, (début, fin) dans ``text`` : coupées aux
    espaces, et un mot plus large que la ligne (lien, nombre) là où il déborde."""
    spans: List[Tuple[int, int]] = []
    start = end = -1
    for word in re.finditer(r"\S+", text):
        if start >= 0 and measure(text[start:word.end()]) <= width:
            end = word.end()
            continue
        if start >= 0:
            spans.append((start, end))
        start, end = word.span()
        if measure(text[start:end]) > width:
            for position in range(start + 2, end + 1):
                if measure(text[start:position]) > width:
                    spans.append((start, position - 1))
                    start = position - 1
    if start >= 0:
        spans.append((start, end))
    return spans


def wrap(text: str, font: str, size: float, width: float) -> List[str]:
    """Lignes d'un texte dans l'ordre logique, aux sauts de ligne et à la largeur donnée."""
    measure = _measure(font, size)
    lines: List[str] = []
    for paragraph in (text or "").split("\n"):
        spans = _spans(paragraph, measure, width) or [(0, 0)]
        lines.extend(paragraph[start:end] for start, end in spans)
    return lines


def escape(text: str) -> str:
    """Texte brut échappé pour le balisage d'un Paragraph ReportLab (&, <, >)."""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _usable_width(style: Any, width: float) -> float:
    # Un point de marge : une ligne trop large, recoupée par ReportLab, le serait dans le désordre
    return width - style.leftIndent - style.rightIndent - 1


def paragraph_markup(text: str, style: Any, width: float, rtl: Optional[bool] = None) -> str:
    """Balisage d'un Paragraph ReportLab pour un texte brut.

    Sans arabe ni hébreu : le texte échappé, sauts de ligne en <br/>, et
    ReportLab coupe les lignes. Sinon : les lignes coupées ici, pour la police
    et la taille du style dans la largeur donnée, puis mises dans l'ordre
    d'affichage. Le style doit alors être aligné avec ``aligned``. ``rtl``
    impose le sens du paragraphe (False pour du code), sinon son premier
    caractère fort le donne.
    """
    if not has_rtl(text) or not shaping_available():
        return escape(text).replace("\n", "<br/>")
    rtl = rtl_paragraph(text) if rtl is None else rtl
    lines = wrap(text, style.fontName, style.fontSize, _usable_width(style, width))
    return "<br/>".join(escape(visual(line, rtl)) for line in lines)


def _styled_line(chars: Sequence[Tuple[str, int]], runs: Sequence[Run], rtl: bool) -> str:
    """Une ligne de (caractère, rang de son fragment dans ``runs``), façonnée et mise
    dans l'ordre d'affichage, chaque fragment dans ses balises."""
    reshape = _shaping()[0]
    shaped: List[Tuple[str, int]] = []
    for owner, piece in groupby(chars, key=lambda item: item[1]):
        # Un fragment façonné à part : une lettre en gras au milieu d'un mot ne s'y lie pas
        shaped.extend((char, owner) for char in reshape("".join(char for char, _owner in piece)))
    order = _display_order("".join(char for char, _owner in shaped), rtl)
    if order is None:
        return escape(visual("".join(char for char, _owner in chars), rtl))
    markup = []
    for owner, piece in groupby(order, key=lambda item: shaped[item[1]][1]):
        _part, opening, closing = runs[owner]
        markup.append(f"{opening}{escape(''.join(char for char, _index in piece))}{closing}")
    return "".join(markup)


def runs_markup(runs: Sequence[Run], style: Any, width: float,
                rtl: Optional[bool] = None, font: Optional[str] = None) -> str:
    """Balisage d'un Paragraph ReportLab fait de fragments stylés (gras, italique, lien, code).

    Sans arabe ni hébreu : chaque fragment échappé dans ses balises, et
    ReportLab coupe les lignes. Sinon, comme ``paragraph_markup`` : les lignes
    coupées ici, mesurées avec ``font`` (la police grasse, la plus large, à
    défaut celle du style), puis chaque fragment façonné et mis à sa place
    d'affichage avec ses balises. Les sauts de ligne comptent pour des espaces,
    comme ReportLab les compte.
    """
    text = "".join(part for part, _opening, _closing in runs)
    if not has_rtl(text) or not shaping_available():
        return "".join(f"{opening}{escape(part)}{closing}" for part, opening, closing in runs)
    rtl = rtl_paragraph(text) if rtl is None else rtl
    text = text.replace("\n", " ")
    chars = [(char, index) for index, (part, _opening, _closing) in enumerate(runs)
             for char in part.replace("\n", " ")]
    measure = _measure(font or style.fontName, style.fontSize)
    spans = _spans(text, measure, _usable_width(style, width)) or [(0, 0)]
    return "<br/>".join(_styled_line(chars[start:end], runs, rtl) for start, end in spans)


def rtl_style(style: Any) -> Any:
    """Le style d'un paragraphe de droite à gauche : aligné à droite, retraits inversés."""
    # pylint: disable=import-outside-toplevel
    from reportlab.lib.enums import TA_RIGHT
    from reportlab.lib.styles import ParagraphStyle
    return ParagraphStyle(f"{style.name}-rtl", parent=style, alignment=TA_RIGHT,
                          leftIndent=style.rightIndent, rightIndent=style.leftIndent)


def aligned(style: Any, text: str) -> Any:
    """Le style du paragraphe, mis de droite à gauche (``rtl_style``) si son texte l'est.

    Un paragraphe justifié l'est aussi : ses lignes, coupées par ``paragraph_markup``,
    finissent toutes par un saut de ligne, que ReportLab ne justifie pas. Un paragraphe
    centré le reste.
    """
    from reportlab.lib.enums import TA_JUSTIFY, TA_LEFT  # pylint: disable=import-outside-toplevel
    if style.alignment not in (TA_LEFT, TA_JUSTIFY) or not rtl_paragraph(text):
        return style
    return rtl_style(style)
