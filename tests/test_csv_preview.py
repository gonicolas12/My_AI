"""
Aperçu des fichiers CSV : lus comme un tableur, montrés en tableau.

Un CSV d'Excel en France est en Windows-1252 et séparé par « ; » ; ses cellules
entre guillemets peuvent contenir le séparateur, des guillemets doublés ou des
retours à la ligne. Lu autrement (séparé par « , », en UTF-8), il s'affichait
en une seule colonne aux cellules coupées. Ici :

  - utils/csv_table.py : encodage, séparateur et cellules ;
  - interfaces/document_preview.py : la page HTML (téléphone, VS Code, repli
    de la fenêtre), et les .xls lus par xlrd ;
  - interfaces/desktop/csv_workbook.py : la copie .xlsx qui ouvre un CSV dans
    la visionneuse d'Excel de la fenêtre (Windows n'en a pas pour le CSV) ;
  - processors/excel_processor.py : le texte que reçoit le modèle, un tableau
    Markdown aux cellules entières (il les coupait à 30 caractères, et lisait
    un CSV « ; » en Windows-1252 en une colonne aux accents perdus).
"""

import os
import time

import pytest
from openpyxl import load_workbook

from core.i18n import tr
from interfaces import document_preview, office_pdf
from interfaces.desktop import csv_workbook
from interfaces.document_preview import build_document_preview
from processors import excel_processor
from processors.excel_processor import ExcelProcessor
from utils.csv_table import decode, guess_separator, read_table


@pytest.fixture(autouse=True)
def _html_rendering(monkeypatch):
    """Ni Office ni LibreOffice : les tableaux HTML (un .xls y passerait par Excel,
    tests/test_office_pdf.py)."""
    monkeypatch.setattr(office_pdf, "office_pdf", lambda path: None)

# CSV exporté par Excel en France : Windows-1252, « ; », guillemets, retour à la ligne
EXCEL_FR = (
    'Code Phrase;"(GC) Description"\r\n'
    '251;"NE PAS PERFORER, NI BRÛLER, MÊME APRÈS USAGE."\r\n'
    '101;"Dit ""non""; puis part"\r\n'
    '7;"ligne 1\r\nligne 2"\r\n'
    '\r\n'
    '3,5;Éthanol\r\n'
).encode("cp1252")


def _csv(tmp_path, data, name="Phrases.csv"):
    path = tmp_path / name
    path.write_bytes(data)
    return str(path)


# ── Lecture : encodage, séparateur, cellules ───────────────────────────────


def test_an_excel_csv_in_french_is_read_like_excel(tmp_path):
    table = read_table(_csv(tmp_path, EXCEL_FR), 100, 10)
    assert table.separator == ";" and table.truncated is False
    assert table.rows == [
        ["Code Phrase", "(GC) Description"],
        ["251", "NE PAS PERFORER, NI BRÛLER, MÊME APRÈS USAGE."],
        ["101", 'Dit "non"; puis part'],
        ["7", "ligne 1\nligne 2"],
        ["3,5", "Éthanol"],
    ]


@pytest.mark.parametrize("data, cut, text", [
    (b"\xef\xbb\xbfa;\xc3\xa9", False, "a;é"),
    ("a;é".encode("utf-16"), False, "a;é"),
    ("a;é".encode("utf-8"), False, "a;é"),
    # Windows-1252, même quand le dernier octet ressemble à un début de caractère UTF-8
    ("a;é".encode("cp1252"), False, "a;é"),
    ("a;Arrêté".encode("cp1252"), True, "a;Arrêté"),
    # Lu en partie, coupé au milieu d'un caractère : sans lui, toujours en UTF-8
    ("a;é".encode("utf-8")[:-1], True, "a;"),
])
def test_the_encoding_is_found_without_being_declared(data, cut, text):
    assert decode(data, cut) == text


@pytest.mark.parametrize("text, separator", [
    ('nom,ville\n"Durand; Paul",Paris\nMartin,Lyon\n', ","),
    ("nom;montant\nA;1,5\nB;2,25\n", ";"),
    ("nom\tville\nA\tParis\n", "\t"),
    ("nom|ville\nA|Paris\n", "|"),
    # Une seule colonne : « , » par défaut
    ("nom\nA\nB\n", ","),
])
def test_the_separator_is_the_one_that_makes_columns(text, separator):
    assert guess_separator(text) == separator


def test_rows_are_padded_and_blank_lines_skipped(tmp_path):
    table = read_table(_csv(tmp_path, b"a;b;c\n\n1;2\n ; \n4;5;6\n"), 100, 10)
    assert table.rows == [["a", "b", "c"], ["1", "2", ""], ["4", "5", "6"]]


def test_a_big_csv_is_cut_and_says_so(tmp_path):
    lines = "".join(f"{n};{n * 2};{n * 3}\n" for n in range(50)).encode()
    assert read_table(_csv(tmp_path, lines), 10, 10).rows[-1] == ["9", "18", "27"]
    assert read_table(_csv(tmp_path, lines), 10, 10).truncated is True
    narrow = read_table(_csv(tmp_path, lines), 100, 2)
    assert narrow.truncated is True and narrow.rows[0] == ["0", "0"]
    # Octets : la ligne coupée n'est pas montrée
    cut = read_table(_csv(tmp_path, lines), 100, 10, max_bytes=20)
    assert cut.truncated is True and cut.rows == [["0", "0", "0"], ["1", "2", "3"], ["2", "4", "6"]]


def test_an_unclosed_quote_shows_the_lines_as_they_are(tmp_path):
    # Le guillemet jamais fermé avale le fichier : cellule trop grande pour le module csv
    data = ('a;b\n"x;' + "y" * 140_000 + "\n1;2\n").encode()
    table = read_table(_csv(tmp_path, data), 100, 10)
    assert table.rows[0] == ["a;b"] and table.rows[-1] == ["1;2"]


# ── Page HTML : téléphone, VS Code, repli de la fenêtre ────────────────────


def test_a_french_csv_preview_shows_its_columns(tmp_path):
    html = build_document_preview(_csv(tmp_path, EXCEL_FR))
    assert "<th>Code Phrase</th><th>(GC) Description</th>" in html
    assert '<td class="num">251</td><td>NE PAS PERFORER, NI BRÛLER, MÊME APRÈS USAGE.</td>' in html
    assert "Dit &quot;non&quot;; puis part" in html
    assert '<td class="num">3,5</td>' in html
    # Ni titre de feuille ni ligne « === Feuille » (l'ancien texte d'ExcelProcessor)
    assert "sheet-title" not in html.split("</style>")[1] and "===" not in html
    assert "…" not in html


def test_a_csv_table_fits_a_phone_screen(tmp_path):
    html = build_document_preview(_csv(tmp_path, b"code;texte\n260;GAZ/VAPEURS/AEROSOLS\n"))
    # Une liste sans espace va à la ligne après ses « / »
    assert "<td>GAZ/<wbr>VAPEURS/<wbr>AEROSOLS</td>" in html
    # Tableur plus large que l'écran : la feuille s'élargit avec lui, il n'en déborde pas
    assert '<div class="tabular">' in html and ".sheet:has(> .tabular)" in html


def test_a_long_csv_preview_says_it_is_cut(tmp_path, monkeypatch):
    monkeypatch.setattr(document_preview, "_CSV_MAX_ROWS", 3)
    lines = "".join(f"{n};x\n" for n in range(10)).encode()
    html = build_document_preview(_csv(tmp_path, lines))
    assert html.count("<tr>") == 3 and tr("docpreview.truncated") in html


def test_xls_values_are_written_like_xlsx_ones():
    xlrd = pytest.importorskip("xlrd")
    cell = xlrd.sheet.Cell
    date = xlrd.xldate.xldate_from_date_tuple((2024, 1, 2), 0)
    values = [
        cell(xlrd.XL_CELL_NUMBER, 251.0), cell(xlrd.XL_CELL_NUMBER, 3.5),
        cell(xlrd.XL_CELL_DATE, date), cell(xlrd.XL_CELL_BOOLEAN, 1),
        cell(xlrd.XL_CELL_ERROR, 7), cell(xlrd.XL_CELL_EMPTY, ""),
        cell(xlrd.XL_CELL_BLANK, ""), cell(xlrd.XL_CELL_TEXT, "Éthanol"),
    ]
    # pylint: disable-next=protected-access
    shown = [document_preview._xls_value(value, 0) for value in values]
    assert shown == ["251", "3.5", "2024-01-02 00:00:00", "True", "#DIV/0!", "", "", "Éthanol"]


def test_xls_sheets_are_read_by_xlrd(tmp_path, monkeypatch):
    xlrd = pytest.importorskip("xlrd")
    cell = xlrd.sheet.Cell

    class Sheet:  # pylint: disable=too-few-public-methods
        name = "Données"
        rows = [[cell(xlrd.XL_CELL_TEXT, "Code"), cell(xlrd.XL_CELL_TEXT, "Libellé")],
                [cell(xlrd.XL_CELL_NUMBER, 251.0), cell(xlrd.XL_CELL_TEXT, "Éthanol")]]
        nrows, ncols = len(rows), 2

        def row(self, index):
            return self.rows[index]

    released = []

    class Book:
        datemode = 0

        def sheets(self):
            return [Sheet()]

        def release_resources(self):
            released.append(True)

    monkeypatch.setattr(xlrd, "open_workbook", lambda path, on_demand: Book())
    path = tmp_path / "ancien.xls"
    path.write_bytes(b"xls")
    html = build_document_preview(str(path))
    assert '<div class="sheet-title" dir="auto">Données</div>' in html
    assert "<th>Code</th><th>Libellé</th>" in html and '<td class="num">251</td>' in html
    assert released == [True]


# ── Copie .xlsx pour la visionneuse d'Excel de la fenêtre ──────────────────


@pytest.fixture(name="cache")
def cache_fixture(tmp_path, monkeypatch):
    folder = tmp_path / "copies"
    monkeypatch.setattr(csv_workbook, "CACHE_DIR", folder)
    return folder


def test_a_csv_becomes_a_workbook_for_excels_viewer(tmp_path, cache):
    copy = csv_workbook.csv_workbook(_csv(tmp_path, EXCEL_FR))
    assert copy and os.path.dirname(copy) == str(cache) and copy.endswith(".xlsx")
    sheet = load_workbook(copy).active
    assert sheet.title == "Phrases" and sheet.freeze_panes == "A2"
    header = [(c.value, c.font.b) for c in sheet[1]]
    assert header == [("Code Phrase", True), ("(GC) Description", True)]
    values = [[c.value for c in row] for row in sheet.iter_rows(min_row=2)]
    assert values == [
        [251, "NE PAS PERFORER, NI BRÛLER, MÊME APRÈS USAGE."],
        [101, 'Dit "non"; puis part'],
        [7, "ligne 1\nligne 2"],
        [3.5, "Éthanol"],
    ]
    # Cellule sur plusieurs lignes : à la ligne ; colonnes à la largeur de leur texte
    assert sheet["B4"].alignment.wrap_text is True and not sheet["B2"].alignment.wrap_text
    # Le code reste en face du début de son texte
    assert sheet["A4"].alignment.vertical == "top"
    assert sheet.column_dimensions["A"].width == 13
    longest = len("NE PAS PERFORER, NI BRÛLER, MÊME APRÈS USAGE.")
    assert sheet.column_dimensions["B"].width == longest + 2


def test_numbers_are_numbers_only_when_excel_would_read_them(tmp_path, cache):
    data = b'code,montant,taux\n007,"1,5",2.25\n12345678901234567,-4,0\n'
    sheet = load_workbook(csv_workbook.csv_workbook(_csv(tmp_path, data, "a.csv"))).active
    # Zéro en tête, plus de 15 chiffres : du texte ; « 1,5 » dans un CSV à virgules : du texte
    assert [c.value for c in sheet[2]] == ["007", "1,5", 2.25]
    assert [c.value for c in sheet[3]] == ["12345678901234567", -4, 0]


def test_a_long_csv_copy_says_it_is_cut(tmp_path, cache, monkeypatch):
    monkeypatch.setattr(csv_workbook, "MAX_ROWS", 3)
    lines = "".join(f"{n};x\n" for n in range(10)).encode()
    sheet = load_workbook(csv_workbook.csv_workbook(_csv(tmp_path, lines))).active
    assert sheet.max_row == 4
    assert sheet["A4"].value == tr("docpreview.truncated") and sheet["A4"].font.i


def test_the_copy_is_made_once_per_version_of_the_file(tmp_path, cache):
    path = _csv(tmp_path, b"a;b\n1;2\n")
    first = csv_workbook.csv_workbook(path)
    written = os.stat(first).st_mtime_ns
    assert csv_workbook.csv_workbook(path) == first and os.stat(first).st_mtime_ns == written
    # Le fichier a changé : une nouvelle copie, avec son contenu
    _csv(tmp_path, b"a;b\n3;4\n")
    later = time.time() + 5
    os.utime(path, (later, later))
    second = csv_workbook.csv_workbook(path)
    assert second != first and load_workbook(second).active["A2"].value == 3
    assert [p.suffix for p in cache.iterdir()] == [".xlsx", ".xlsx"]


def test_old_copies_are_removed(tmp_path, cache):
    cache.mkdir()
    old, recent = cache / "ancienne.xlsx", cache / "recente.xlsx"
    stale = cache / "reste.tmp"
    for path in (old, recent, stale):
        path.write_bytes(b"x")
    week_ago = time.time() - 8 * 24 * 3600
    os.utime(old, (week_ago, week_ago))
    os.utime(stale, (week_ago, week_ago))
    csv_workbook.csv_workbook(_csv(tmp_path, b"a;b\n1;2\n"))
    assert not old.exists() and not stale.exists() and recent.exists()


def test_an_unreadable_csv_has_no_copy(tmp_path, cache):
    assert csv_workbook.csv_workbook(str(tmp_path / "absent.csv")) is None
    assert not cache.exists() or not list(cache.iterdir())


# ── Texte donné au modèle (processors/excel_processor.py) ──────────────────


def test_the_model_reads_a_french_csv_whole(tmp_path):
    result = ExcelProcessor().extract_text(_csv(tmp_path, EXCEL_FR))
    text = result["content"]
    assert result["success"] is True
    assert "| Code Phrase | (GC) Description |\n|---|---|\n" in text
    assert "| 251 | NE PAS PERFORER, NI BRÛLER, MÊME APRÈS USAGE. |" in text
    assert '| 101 | Dit "non"; puis part |' in text and "| 7 | ligne 1<br>ligne 2 |" in text
    # Ni accent perdu (caractère de remplacement), ni cellule coupée, ni colonne née d'une virgule du texte
    assert chr(0xFFFD) not in text and "..." not in text
    assert text.endswith("Total : 5 lignes × 2 colonnes")


def test_the_model_text_of_a_big_table_is_bounded(tmp_path, monkeypatch):
    monkeypatch.setattr(excel_processor, "TEXT_BUDGET", 200)
    lines = "".join(f"{n};phrase numéro {n}\n" for n in range(100)).encode("utf-8")
    text = ExcelProcessor().extract_text(_csv(tmp_path, lines))["content"]
    assert len(text) < 400 and "| 0 | phrase numéro 0 |" in text
    assert "lignes supplémentaires non affichées" in text


def test_xlsx_cells_are_whole_for_the_model(tmp_path):
    from openpyxl import Workbook  # pylint: disable=import-outside-toplevel

    path = tmp_path / "phrases.xlsx"
    book = Workbook()
    sheet = book.active
    sheet.title = "Phrases"
    sheet.append(["Code", "Description", None])
    sheet.append([231, "MANIPULER ET STOCKER LE PRODUIT SOUS GAZ INERTE.", None])
    sheet.append([300, "Choix A | choix B", None])
    sheet["E10"].value = None  # cellule vide plus loin : ni ligne ni colonne en plus
    sheet.append([None, None, None])
    book.save(str(path))
    text = ExcelProcessor().extract_text(str(path))["content"]
    assert "| 231 | MANIPULER ET STOCKER LE PRODUIT SOUS GAZ INERTE. |" in text
    assert "| 300 | Choix A \\| choix B |" in text
    assert text.startswith("=== Feuille : Phrases ===") and text.endswith("3 lignes × 2 colonnes")
