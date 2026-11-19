"""
Tableau d'un fichier CSV, lu comme l'ouvrirait un tableur

Un CSV n'a ni encodage ni séparateur déclarés. Ceux d'Excel en France sont en
Windows-1252, séparés par « ; » (la virgule y est le séparateur décimal), et
une cellule entre guillemets peut contenir le séparateur, des guillemets
doublés ou des retours à la ligne. Lu ici :

  - encodage : BOM UTF-8 ou UTF-16, sinon UTF-8, sinon Windows-1252 ;
  - séparateur : « ; », « , », tabulation ou « | », celui qui donne à la plupart
    des lignes le même nombre de colonnes (au moins deux) ;
  - cellules : module csv de Python (guillemets, retours à la ligne).

Aperçus : page HTML (interfaces/document_preview.py : téléphone, VS Code,
fenêtre en repli) et copie .xlsx pour la visionneuse d'Excel de la fenêtre
(interfaces/desktop/csv_workbook.py), Windows n'en ayant pas pour le CSV.
"""

import csv
import io
from typing import List, NamedTuple

SEPARATORS = (";", ",", "\t", "|")
# Début du fichier lu pour deviner le séparateur
_SNIFF_CHARS = 64 * 1024
# Lignes regardées pour le deviner
_SNIFF_ROWS = 50


class CsvTable(NamedTuple):
    """Lignes d'un CSV, toutes de la même largeur."""

    rows: List[List[str]]
    # Le fichier a plus de lignes, de colonnes ou d'octets que ce qui est lu
    truncated: bool
    separator: str


def decode(data: bytes, cut: bool = False) -> str:
    """Texte d'un CSV : BOM UTF-8 ou UTF-16, UTF-8, sinon Windows-1252 (Excel en France).

    cut : data n'est que le début du fichier, son dernier caractère peut être coupé
    """
    if data.startswith(b"\xef\xbb\xbf"):
        return data[3:].decode("utf-8", errors="replace")
    if data.startswith((b"\xff\xfe", b"\xfe\xff")):
        return data.decode("utf-16", errors="replace")
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError as exc:
        # Coupé au milieu de son dernier caractère (fichier lu en partie) : sans lui
        if cut and exc.reason == "unexpected end of data":
            return data[:exc.start].decode("utf-8")
        return data.decode("cp1252", errors="replace")


def guess_separator(text: str) -> str:
    """Séparateur des premières lignes : celui qui donne au plus de lignes le même
    nombre de colonnes (au moins deux), puis le plus de colonnes ; « , » à défaut."""
    sample = text[:_SNIFF_CHARS]
    if len(text) > _SNIFF_CHARS and "\n" in sample:
        sample = sample[:sample.rindex("\n")]  # sans la ligne coupée
    best, best_score = ",", (0, 0)
    for separator in SEPARATORS:
        try:
            rows = []
            for row in csv.reader(io.StringIO(sample), delimiter=separator):
                if any(cell.strip() for cell in row):
                    rows.append(len(row))
                if len(rows) >= _SNIFF_ROWS:
                    break
        except csv.Error:
            continue
        widths = [width for width in rows if width >= 2]
        if not widths:
            continue
        common = max(set(widths), key=widths.count)
        score = (widths.count(common), common)
        if score > best_score:
            best, best_score = separator, score
    return best


def _cell(text: str) -> str:
    """Cellule sans les espaces qui l'entourent, ses retours à la ligne en « \n »."""
    return text.strip().replace("\r\n", "\n").replace("\r", "\n")


def read_table(path: str, max_rows: int, max_columns: int,
               max_bytes: int = 16 * 1024 * 1024) -> CsvTable:
    """Lignes d'un CSV (au plus max_rows, max_columns colonnes), sans les lignes vides.

    Raises:
        OSError: lecture impossible
    """
    with open(path, "rb") as handle:
        data = handle.read(max_bytes + 1)
    truncated = len(data) > max_bytes
    data = data[:max_bytes]
    if truncated and b"\n" in data:
        data = data[:data.rindex(b"\n")]  # sans la ligne coupée
    text = decode(data, cut=truncated)
    separator = guess_separator(text)
    rows: List[List[str]] = []
    try:
        for row in csv.reader(io.StringIO(text, newline=""), delimiter=separator):
            if not any(cell.strip() for cell in row):
                continue
            if len(rows) >= max_rows:
                truncated = True
                break
            if len(row) > max_columns:
                truncated = True
                row = row[:max_columns]
            rows.append([_cell(cell) for cell in row])
    except csv.Error:
        # Fichier mal formé (octet nul…) : une ligne par ligne de texte
        lines = [line for line in text.splitlines() if line.strip()]
        truncated = truncated or len(lines) > max_rows
        rows = [[line] for line in lines[:max_rows]]
    width = max((len(row) for row in rows), default=0)
    return CsvTable([row + [""] * (width - len(row)) for row in rows], truncated, separator)
