"""
Tests du processeur PDF (processors/pdf_processor.py).

PyMuPDF est la bibliothèque principale et PyPDF2 le repli. Les deux étaient
importées sans condition : sans PyMuPDF (ou avec une version antérieure à
1.24.3), My_AI ne démarrait plus au lieu de passer à PyPDF2.
"""

import os
import subprocess
import sys
from pathlib import Path

import pymupdf
import pytest

from processors import pdf_processor
from processors.pdf_processor import PDFProcessor

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TEXT = "Rapport annuel 2026"


@pytest.fixture(name="pdf_path")
def _pdf_path(tmp_path):
    path = tmp_path / "rapport.pdf"
    doc = pymupdf.open()
    doc.new_page().insert_text((72, 72), TEXT)
    doc.save(str(path))
    doc.close()
    return path


def test_reads_with_pymupdf_when_available(pdf_path):
    result = PDFProcessor().read_pdf(str(pdf_path))
    assert result["file_info"]["processor"] == "PyMuPDF"
    assert TEXT in result["content"]["text"]


def test_falls_back_to_pypdf2_without_pymupdf(pdf_path):
    """Interpréteur neuf où `import pymupdf` échoue, comme sur un poste sans PyMuPDF."""
    code = (
        "import sys\n"
        "sys.modules['pymupdf'] = None\n"
        "from processors.pdf_processor import PDFProcessor\n"
        f"result = PDFProcessor().read_pdf({str(pdf_path)!r})\n"
        "print(result['file_info']['processor'])\n"
        "print(result['content']['text'])\n"
    )
    run = subprocess.run(
        [sys.executable, "-c", code],
        cwd=PROJECT_ROOT,
        capture_output=True,
        encoding="utf-8",
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
        timeout=120,
        check=False,
    )
    assert run.returncode == 0, run.stderr
    assert run.stdout.splitlines()[0] == "PyPDF2"
    assert TEXT in run.stdout


def test_reports_when_no_pdf_library(pdf_path, monkeypatch):
    monkeypatch.setattr(pdf_processor, "pymupdf", None)
    monkeypatch.setattr(pdf_processor, "PyPDF2", None)
    result = PDFProcessor().read_pdf(str(pdf_path))
    assert "Aucune bibliothèque PDF disponible" in result["error"]


def test_extract_text_reports_the_pymupdf_error(tmp_path):
    path = tmp_path / "casse.pdf"
    path.write_bytes(b"pas un pdf")
    with pytest.raises(ValueError, match="Erreur PyMuPDF"):
        PDFProcessor().extract_text(str(path))
