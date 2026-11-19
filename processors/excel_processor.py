"""
Processeur de fichiers Excel et CSV
Lecture et extraction de contenu pour .xlsx, .xls, .csv
"""

import os
from pathlib import Path
from typing import Any, Dict, List

from utils.csv_table import read_table

# Texte d'un classeur donné au modèle : au plus autant de caractères, la suite
# annoncée (un long document passe ensuite par la sélection de passages,
# core/document_passages.py)
TEXT_BUDGET = 200_000
# CSV lu au plus jusque-là
CSV_MAX_ROWS = 100_000
CSV_MAX_COLUMNS = 500


def _cell_text(value: Any) -> str:
    """Cellule d'un tableau Markdown : entière, sur une ligne (retours à la ligne en
    <br>), « | » échappé."""
    text = "" if value is None else str(value).strip()
    text = text.replace("\r\n", "\n").replace("\r", "\n").replace("\n", "<br>")
    return text.replace("|", "\\|")


class ExcelProcessor:
    """Processeur pour les fichiers Excel (.xlsx, .xls) et CSV (.csv)"""

    def __init__(self):
        self.supported_extensions = [".xlsx", ".xls", ".csv"]
        self._check_dependencies()

    def _check_dependencies(self):
        try:
            import openpyxl  # noqa: F401
            self.openpyxl_available = True
        except ImportError:
            self.openpyxl_available = False
            print("⚠️ Module 'openpyxl' non installé. pip install openpyxl")

        try:
            import xlrd  # noqa: F401
            self.xlrd_available = True
        except ImportError:
            self.xlrd_available = False

    # ------------------------------------------------------------------ #
    #  Méthode principale                                                   #
    # ------------------------------------------------------------------ #

    def read_excel(self, file_path: str) -> Dict[str, Any]:
        """Lit un fichier Excel ou CSV et retourne le contenu structuré."""
        if not os.path.exists(file_path):
            return {"success": False, "error": f"Fichier non trouvé : {file_path}"}

        ext = Path(file_path).suffix.lower()

        if ext == ".csv":
            return self._read_csv(file_path)
        elif ext == ".xlsx":
            return self._read_xlsx(file_path)
        elif ext == ".xls":
            return self._read_xls(file_path)
        else:
            return {"success": False, "error": f"Format non supporté : {ext}"}

    def extract_text(self, file_path: str) -> Dict[str, Any]:
        """Interface compatible avec les autres processeurs : retourne {success, content}."""
        result = self.read_excel(file_path)
        if result.get("success"):
            return {"success": True, "content": result["content"]}
        return result

    # ------------------------------------------------------------------ #
    #  Lecteurs par format                                                  #
    # ------------------------------------------------------------------ #

    def _read_csv(self, file_path: str) -> Dict[str, Any]:
        """Lit un CSV comme un tableur (utils/csv_table.py) : encodage (UTF-8, sinon
        Windows-1252 comme les exports d'Excel en France), séparateur (« ; », « , »,
        tabulation…), cellules entre guillemets (séparateur, retours à la ligne)."""
        try:
            table = read_table(file_path, CSV_MAX_ROWS, CSV_MAX_COLUMNS)
        except Exception as exc:  # pylint: disable=broad-except
            return {"success": False, "error": f"Erreur lecture CSV : {exc}"}

        text = self._rows_to_text("Données CSV", table.rows, cut=table.truncated)
        return {
            "success": True,
            "content": text,
            "sheets": {"CSV": table.rows},
            "sheet_names": ["CSV"],
            "total_rows": len(table.rows),
            "processor": "csv-stdlib",
        }

    def _read_xlsx(self, file_path: str) -> Dict[str, Any]:
        """Lit un fichier .xlsx via openpyxl."""
        if not self.openpyxl_available:
            return {
                "success": False,
                "error": "openpyxl requis pour les fichiers .xlsx. Installez avec : pip install openpyxl",
            }
        try:
            import openpyxl

            wb = openpyxl.load_workbook(file_path, data_only=True)
            texts: List[str] = []
            sheets_data: Dict[str, List] = {}
            total_rows = 0

            for sheet_name in wb.sheetnames:
                ws = wb[sheet_name]
                rows = []
                for row in ws.iter_rows(values_only=True):
                    rows.append(
                        [str(cell) if cell is not None else "" for cell in row]
                    )
                sheets_data[sheet_name] = rows
                total_rows += len(rows)
                texts.append(self._rows_to_text(sheet_name, rows))

            return {
                "success": True,
                "content": "\n\n".join(texts),
                "sheets": sheets_data,
                "sheet_names": list(wb.sheetnames),
                "total_rows": total_rows,
                "processor": "openpyxl",
            }
        except Exception as exc:
            return {"success": False, "error": f"Erreur lecture .xlsx : {exc}"}

    def _read_xls(self, file_path: str) -> Dict[str, Any]:
        """Lit un fichier .xls (ancien format) via xlrd, sinon tente openpyxl."""
        if self.xlrd_available:
            try:
                import xlrd

                wb = xlrd.open_workbook(file_path)
                texts: List[str] = []
                sheets_data: Dict[str, List] = {}
                total_rows = 0

                for sheet_name in wb.sheet_names():
                    ws = wb.sheet_by_name(sheet_name)
                    rows = []
                    for rx in range(ws.nrows):
                        rows.append([str(ws.cell_value(rx, cx)) for cx in range(ws.ncols)])
                    sheets_data[sheet_name] = rows
                    total_rows += len(rows)
                    texts.append(self._rows_to_text(sheet_name, rows))

                return {
                    "success": True,
                    "content": "\n\n".join(texts),
                    "sheets": sheets_data,
                    "sheet_names": wb.sheet_names(),
                    "total_rows": total_rows,
                    "processor": "xlrd",
                }
            except Exception as exc:
                return {"success": False, "error": f"Erreur lecture .xls (xlrd) : {exc}"}

        # Fallback : openpyxl peut lire certains .xls
        if self.openpyxl_available:
            return self._read_xlsx(file_path)

        return {
            "success": False,
            "error": "Aucune bibliothèque disponible pour .xls. Installez xlrd ou openpyxl.",
        }

    # ------------------------------------------------------------------ #
    #  Formatage texte                                                      #
    # ------------------------------------------------------------------ #

    def _rows_to_text(self, sheet_name: str, rows: List[List[str]], cut: bool = False) -> str:
        """Tableau Markdown pour le modèle : une ligne par ligne du classeur, cellules
        entières (retours à la ligne en <br>, « | » échappé), sans les lignes vides ni
        les colonnes vides de la fin, jusqu'à TEXT_BUDGET caractères (la suite est
        annoncée).

        Args:
            cut: le fichier n'a pas été lu en entier (CSV trop long)
        """
        rows = [[_cell_text(cell) for cell in row] for row in rows]
        rows = [row for row in rows if any(row)]
        if not rows:
            return f"=== Feuille : {sheet_name} ===\n(vide)"
        ncols = max(max(index + 1 for index, cell in enumerate(row) if cell) for row in rows)

        def fmt_row(row: List[str]) -> str:
            return "| " + " | ".join((row + [""] * ncols)[:ncols]) + " |"

        lines = [f"=== Feuille : {sheet_name} ===", fmt_row(rows[0])]
        if len(rows) > 1:
            lines.append("|" + "|".join(["---"] * ncols) + "|")
        used = sum(len(line) + 1 for line in lines)
        shown = 1
        for row in rows[1:]:
            line = fmt_row(row)
            if used + len(line) + 1 > TEXT_BUDGET:
                break
            lines.append(line)
            used += len(line) + 1
            shown += 1

        if shown < len(rows):
            lines.append(f"... ({len(rows) - shown} lignes supplémentaires non affichées)")
        if cut:
            lines.append("... (fichier trop long : sa fin n'a pas été lue)")
        lines.append(f"\n📊 Total : {len(rows)} lignes × {ncols} colonnes")
        return "\n".join(lines)

    def is_supported(self, file_path: str) -> bool:
        return Path(file_path).suffix.lower() in self.supported_extensions
