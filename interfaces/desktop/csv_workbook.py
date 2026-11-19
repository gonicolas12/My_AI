"""
CSV dans la visionneuse d'Excel de la fenêtre

Windows n'a pas de visionneuse pour le CSV (la fenêtre en a une pour le
.xlsx : celle d'Excel). Un CSV y est donc montré par une copie .xlsx : ses
cellules lues comme un tableur (utils/csv_table.py), son en-tête en gras et
figé, ses colonnes à la largeur de leur texte, ses nombres en nombres. Une
copie par version du fichier (utils/preview_cache.py).
"""

import os
import re
import threading
from pathlib import Path
from typing import Any, List, Optional

from core.i18n import tr
from utils import preview_cache
from utils.csv_table import read_table
from utils.logger import setup_logger

logger = setup_logger("CsvWorkbook")

CACHE_DIR = preview_cache.ROOT / "csv"
# Forme des copies : à changer avec elle, les anciennes ne resservent plus
_FORMAT = "1"
# Une copie montre au plus ces lignes et colonnes
MAX_ROWS = 20000
MAX_COLUMNS = 200
# Largeur d'une colonne : celle de son texte (premières lignes), bornée ; au-delà,
# le texte d'une cellule va à la ligne
_WIDTH_ROWS = 200
_WIDTH_MIN, _WIDTH_MAX = 8, 60
# Nombre écrit comme Excel le lirait : entier sans zéro en tête (un code « 007 »
# reste du texte), décimal à point, ou à virgule quand elle ne sépare pas les cellules
_INTEGER = re.compile(r"^-?(?:0|[1-9]\d{0,14})$")
_DECIMAL_POINT = re.compile(r"^-?(?:0|[1-9]\d{0,14})\.\d{1,10}$")
_DECIMAL_COMMA = re.compile(r"^-?(?:0|[1-9]\d{0,14}),\d{1,10}$")
_SHEET_FORBIDDEN = re.compile(r"[\[\]:*?/\\]")
# Une conversion à la fois : deux aperçus du même fichier attendent la même copie
_LOCK = threading.Lock()


def _value(text: str, decimal_comma: bool) -> Any:
    """Cellule : un nombre quand le texte en est un, sinon le texte."""
    if _INTEGER.match(text):
        return int(text)
    if _DECIMAL_POINT.match(text):
        return float(text)
    if decimal_comma and _DECIMAL_COMMA.match(text):
        return float(text.replace(",", "."))
    return text


def _sheet_title(name: str) -> str:
    """Nom de feuille accepté par Excel : 31 caractères, sans [ ] : * ? / \\."""
    return _SHEET_FORBIDDEN.sub("_", name).strip("'")[:31] or "CSV"


def _widths(rows: List[List[str]]) -> List[int]:
    widths: List[int] = []
    for row in rows[:_WIDTH_ROWS]:
        for index, cell in enumerate(row):
            longest = max((len(line) for line in cell.split("\n")), default=0)
            if index >= len(widths):
                widths.append(0)
            widths[index] = max(widths[index], longest)
    return [min(_WIDTH_MAX, max(_WIDTH_MIN, width + 2)) for width in widths]


def _write(path: str, target: Path) -> None:
    # pylint: disable=import-outside-toplevel
    from openpyxl import Workbook
    from openpyxl.cell import WriteOnlyCell
    from openpyxl.styles import Alignment, Font
    from openpyxl.utils import get_column_letter

    table = read_table(path, MAX_ROWS, MAX_COLUMNS)
    book = Workbook(write_only=True)
    sheet = book.create_sheet(_sheet_title(Path(path).stem))
    sheet.freeze_panes = "A2"
    widths = _widths(table.rows)
    for index, width in enumerate(widths, start=1):
        sheet.column_dimensions[get_column_letter(index)].width = width
    bold = Font(bold=True)
    # En haut de leur ligne : un code reste en face du début de son texte
    top = Alignment(vertical="top")
    wrap = Alignment(wrap_text=True, vertical="top")
    decimal_comma = table.separator != ","
    for number, row in enumerate(table.rows):
        cells = []
        for column, text in enumerate(row):
            cell = WriteOnlyCell(sheet, value=text if number == 0 else _value(text, decimal_comma))
            if number == 0:
                cell.font = bold
            # Plus long que sa colonne, ou sur plusieurs lignes : à la ligne
            cell.alignment = wrap if "\n" in text or len(text) > widths[column] else top
            cells.append(cell)
        sheet.append(cells)
    if table.truncated:
        note = WriteOnlyCell(sheet, value=tr("docpreview.truncated"))
        note.font = Font(italic=True)
        sheet.append([note])
    partial = preview_cache.partial_path(target)
    try:
        book.save(str(partial))
        os.replace(partial, target)
    finally:
        partial.unlink(missing_ok=True)


def csv_workbook(path: str) -> Optional[str]:
    """Copie .xlsx d'un CSV pour la visionneuse d'Excel ; None si elle n'a pas pu être faite."""
    try:
        target = preview_cache.copy_path(CACHE_DIR, path, ".xlsx", _FORMAT)
        with _LOCK:
            if not target.is_file():
                CACHE_DIR.mkdir(parents=True, exist_ok=True)
                preview_cache.prune(CACHE_DIR)
                _write(path, target)
        return str(target)
    except Exception as exc:  # pylint: disable=broad-except
        logger.warning("Copie .xlsx du CSV impossible (%s) : %s", path, exc)
        return None
