"""
Tests du texte des PDF (utils/pdf_text.py) et de l'export des conversations
(core/conversation_exporter.py) : Helvetica pour l'alphabet latin, comme
avant ; une police qui écrit le chinois, le japonais, le coréen, le cyrillique
ou l'arabe quand le texte (libellés traduits compris) en contient, faute de
quoi le PDF n'en montrait que des carrés ; l'arabe et l'hébreu aux lettres
liées et de droite à gauche, quand ReportLab les écrivait à l'envers, en
lettres isolées.
"""

import re
from pathlib import Path

import pytest
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase.pdfmetrics import stringWidth

from core import i18n
from core.conversation_exporter import ConversationExporter
from utils.pdf_text import (
    _measure,
    aligned,
    code_font,
    has_rtl,
    paragraph_markup,
    pdf_fonts,
    rtl_paragraph,
    runs_markup,
    shaping_available,
    system_font,
    visual,
    wrap,
)

HELVETICA = ("Helvetica", "Helvetica-Bold")
# Lettres arabes de base : une fois façonnées, il n'en reste plus (formes liées)
ARABIC_LETTERS = re.compile(r"[ء-ي]")
needs_shaping = pytest.mark.skipif(not shaping_available(),
                                   reason="arabic-reshaper ou python-bidi absent")


@pytest.fixture(autouse=True)
def _french():
    i18n.reset_for_tests()
    i18n.set_language("fr")
    yield
    i18n.reset_for_tests()


def _masked(text: str) -> str:
    """Mots arabes remplacés par « a » : l'ordre de gauche à droite se lit sans algorithme bidi."""
    return re.sub(r"[؀-ۿﭐ-﷿ﹰ-﻿]+", "a", text)


def _style(font: str = "Helvetica", **kwargs) -> ParagraphStyle:
    return ParagraphStyle("test", fontName=font, fontSize=10, **kwargs)


# ── Polices ──────────────────────────────────────────────────────────────────


def test_latin_text_keeps_helvetica():
    assert pdf_fonts("Bonjour, ça va ? Œuvre — « déjà » ✅") == HELVETICA
    assert pdf_fonts("Grüße aus Köln, ¿qué tal?") == HELVETICA


def test_chinese_and_japanese_use_adobe_fonts():
    assert pdf_fonts("你好，世界")[0] == "STSong-Light"
    assert pdf_fonts("こんにちは世界")[0] == "HeiseiKakuGo-W5"
    # Idéogrammes seuls : japonais si l'interface l'est
    i18n.set_language("ja")
    assert pdf_fonts("世界")[0] == "HeiseiKakuGo-W5"


def test_korean_uses_a_font_pdfium_can_show():
    expected = ("MyAI-ko", "MyAI-ko-Bold") if system_font("ko") else ("HYGothic-Medium",) * 2
    assert pdf_fonts("안녕하세요") == expected


def test_cyrillic_arabic_and_hebrew_use_a_system_font_when_there_is_one():
    expected = ("MyAI-sans", "MyAI-sans-Bold") if system_font("sans") else HELVETICA
    assert pdf_fonts("Привет, мир") == expected
    assert pdf_fonts("مرحبا بالعالم") == expected
    assert pdf_fonts("שלום עולם") == expected


def test_code_stays_in_courier_when_it_is_latin():
    assert code_font('print("ok")', "MyAI-sans") == "Courier"
    assert code_font('print("Привет")', "MyAI-sans") == "MyAI-sans"


# ── Sens d'écriture ──────────────────────────────────────────────────────────


def test_direction_of_a_paragraph():
    assert has_rtl("Le mot سلام") and has_rtl("שלום") and not has_rtl("Привет, 你好")
    # Le premier caractère fort décide : arabe, puis latin
    assert rtl_paragraph("« مرحبا » Paris")
    assert not rtl_paragraph("Paris مرحبا")
    assert not rtl_paragraph("2026 !")


@needs_shaping
def test_arabic_letters_are_joined_and_put_in_display_order():
    # sîn initiale, lam-alif finale, mîm isolée ; de gauche à droite, la mîm d'abord
    assert visual("سلام") == "ﻡﻼﺳ"
    assert visual("Bonjour") == "Bonjour"


@needs_shaping
def test_brackets_numbers_and_latin_words_inside_arabic():
    assert _masked(visual("باريس (Paris).")) == ".(Paris) a"
    # Les crochets retournés : celui qui ouvre est à droite, tourné vers le texte
    assert _masked(visual("في [إيل دو فرانس] 2024")) == "2024 [a a a] a"


@needs_shaping
def test_code_stays_left_to_right():
    markup = paragraph_markup('print("مرحبا")', _style(), 400, rtl=False)
    assert _masked(markup) == 'print("a")'


def test_latin_markup_is_left_to_reportlab():
    """Sans arabe ni hébreu, ReportLab coupe les lignes, comme avant."""
    assert paragraph_markup("a < b & c\nd", _style(), 100) == "a &lt; b &amp; c<br/>d"
    runs = [("gras", "<b>", "</b>"), (" et <code>", "", "")]
    assert runs_markup(runs, _style(), 100) == "<b>gras</b> et &lt;code&gt;"


@needs_shaping
def test_arabic_lines_are_cut_in_reading_order():
    font = pdf_fonts("مرحبا")[0]
    text = " ".join(["المدينة", "عاصمة", "فرنسا", "هي", "باريس", "وأكثر", "من", "مليون"] * 6)
    lines = wrap(text, font, 10, 120)
    assert len(lines) > 3
    assert " ".join(lines) == text  # aucun mot perdu ni déplacé
    measure = _measure(font, 10)  # largeur des lettres liées
    assert all(measure(line) <= 120 for line in lines)
    # Chaque ligne coupée ici, mise dans l'ordre d'affichage : ReportLab ne la recoupe pas
    markup = paragraph_markup(text, _style(font), 120 + 1)
    assert markup.count("<br/>") == len(lines) - 1


def test_overlong_word_is_cut_where_it_overflows():
    url = "https://example.com/" + "a" * 120
    lines = wrap(url, "Helvetica", 10, 100)
    assert "".join(lines) == url and len(lines) > 1
    assert all(stringWidth(line, "Helvetica", 10) <= 100 for line in lines)


@needs_shaping
def test_bold_follows_its_word_in_arabic():
    runs = [("مرحبا ", "", ""), ("بالعالم", "<b>", "</b>"), (" (Paris)", "", "")]
    markup = runs_markup(runs, _style(pdf_fonts("مرحبا")[0]), 400)
    # De gauche à droite : (Paris), le mot en gras, puis le premier mot
    assert _masked(markup) == "(Paris) <b>a</b> a"


def test_rtl_paragraphs_are_aligned_right():
    left = _style(leftIndent=14)
    rtl = aligned(left, "مرحبا")
    # pylint: disable-next=no-member
    assert (rtl.alignment, rtl.leftIndent, rtl.rightIndent) == (TA_RIGHT, 0, 14)
    assert aligned(left, "Hello مرحبا") is left
    centered = _style(alignment=TA_CENTER)
    assert aligned(centered, "مرحبا") is centered


# ── Export des conversations ─────────────────────────────────────────────────


def _export(tmp_path, content, output_format="pdf"):
    exporter = ConversationExporter(output_dir=str(tmp_path))
    path = exporter.export([{"role": "user", "content": content, "timestamp": None},
                            {"role": "assistant", "content": "OK", "timestamp": None}],
                           output_format=output_format, filename="conversation")
    return Path(path).read_bytes()


def test_pdf_written_in_the_language_of_the_interface(tmp_path):
    """Libellés traduits seuls (contenu latin) : la police suit la langue de l'interface."""
    i18n.set_language("zh")
    assert b"STSong-Light" in _export(tmp_path, "Hello")
    i18n.set_language("fr")
    data = _export(tmp_path, "Bonjour")
    assert b"STSong-Light" not in data and b"Helvetica" in data


def test_pdf_with_russian_content_embeds_a_unicode_font(tmp_path):
    if not system_font("sans"):
        pytest.skip("aucune police TrueType Unicode sur ce système")
    data = _export(tmp_path, "Привет, мир")
    assert b"+Arial" in data or b"+DejaVuSans" in data


@needs_shaping
def test_arabic_pdf_has_joined_letters(tmp_path):
    fitz = pytest.importorskip("fitz")
    if not system_font("sans"):
        pytest.skip("aucune police TrueType Unicode sur ce système")
    i18n.set_language("ar")
    data = _export(tmp_path, 'مرحبا! ما هي عاصمة فرنسا؟\n```python\nprint("سلام")\n```')
    with fitz.open(stream=data, filetype="pdf") as document:
        text = document[0].get_text()
    assert re.search(r"[ﹰ-ﻼ]", text)  # formes liées
    assert not ARABIC_LETTERS.search(text)  # plus une lettre isolée


def test_html_export_reads_right_to_left_in_arabic(tmp_path):
    i18n.set_language("ar")
    page = _export(tmp_path, "مرحبا", output_format="html").decode("utf-8")
    assert '<html lang="ar" dir="rtl">' in page
    assert '<div class="message-content" dir="auto">' in page
    i18n.set_language("fr")
    page = _export(tmp_path, "Bonjour", output_format="html").decode("utf-8")
    assert '<html lang="fr" dir="ltr">' in page
