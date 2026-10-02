"""
Tests de l'OCR des PDF scannés (processors/ocr.py).

Un PDF « converti en images puis de nouveau en PDF » n'a plus de couche
texte : le chat répondait « semble vide ou illisible » et les agents
« Aucun texte extractible ». On construit ici ce type de PDF à partir d'une
page de texte rendue en image, puis on le lit par chacun des chemins.
"""

import re
import threading

import pymupdf
import pytest

from processors import ocr
from processors.attachments import read_attachment_text
from processors.pdf_processor import PDFProcessor
from utils.file_processor import FileProcessor

SENTENCE = "Fiche de données de sécurité du produit"
EXPECTED_WORDS = {"fiche", "données", "sécurité", "produit"}


def _words(text):
    return set(re.findall(r"\w+", text.lower()))


@pytest.fixture(name="scanned_pdf")
def _scanned_pdf(tmp_path):
    """PDF d'images : une page de texte rendue en image puis remise dans un PDF."""
    source = pymupdf.open()
    source.new_page().insert_textbox(
        pymupdf.Rect(72, 72, 520, 200), SENTENCE, fontname="helv", fontsize=14
    )
    png = source[0].get_pixmap(dpi=150).tobytes("png")
    source.close()

    path = tmp_path / "scan.pdf"
    scan = pymupdf.open()
    page = scan.new_page()
    page.insert_image(page.rect, stream=png)
    scan.save(str(path))
    scan.close()
    return path


@pytest.fixture(name="require_ocr")
def _require_ocr():
    pytest.importorskip("rapidocr")


def test_pdf_processor_reads_scanned_page(scanned_pdf, require_ocr):
    result = PDFProcessor().read_pdf(str(scanned_pdf))
    assert result["file_info"]["ocr_pages"] == 1
    assert EXPECTED_WORDS <= _words(result["content"]["text"])


def test_chat_file_processor_reads_scanned_pdf(scanned_pdf, require_ocr):
    """Chemin du chat et de l'indexation RAG : plus d'échec « vide ou illisible »."""
    result = FileProcessor().process_file(str(scanned_pdf))
    assert result.get("error") is None
    assert result["ocr_pages"] == 1
    assert EXPECTED_WORDS <= _words(result["content"])


def test_agent_attachment_reads_scanned_pdf(scanned_pdf, require_ocr):
    assert EXPECTED_WORDS <= _words(read_attachment_text(str(scanned_pdf)))


def test_second_read_uses_cache(scanned_pdf, require_ocr, monkeypatch):
    """Le chat lit chaque PDF deux fois (FileProcessor puis add_file_to_context)."""
    calls = []
    real_get_engine = ocr._get_engine

    def counting_get_engine():
        engine = real_get_engine()

        def run(image):
            calls.append(image)
            return engine(image)

        return run

    monkeypatch.setattr(ocr, "_get_engine", counting_get_engine)
    first = PDFProcessor().extract_text(str(scanned_pdf))
    second = PDFProcessor().extract_text(str(scanned_pdf))
    assert first == second
    assert len(calls) == 1


def test_without_ocr_engine_explains_how_to_enable_it(scanned_pdf, monkeypatch):
    monkeypatch.setattr(ocr, "RapidOCR", None)
    assert FileProcessor().process_file(str(scanned_pdf))["error"] == ocr.MISSING_OCR_HINT
    with pytest.raises(ValueError, match="rapidocr"):
        read_attachment_text(str(scanned_pdf))


def test_interrupted_read_stops_without_fallback(scanned_pdf, monkeypatch):
    """Pièce jointe retirée : l'OCR s'arrête, sans relire le PDF par PyPDF2 ou pdfplumber."""
    monkeypatch.setattr(ocr, "RapidOCR", object)  # moteur « installé », jamais appelé
    cancel = threading.Event()
    cancel.set()
    with ocr.interruptible(cancel), pytest.raises(ocr.OcrInterrupted):
        FileProcessor().process_file(str(scanned_pdf))


def test_interruption_is_limited_to_its_block_and_thread(scanned_pdf, require_ocr):
    cancel = threading.Event()
    cancel.set()
    texts = []
    with ocr.interruptible(cancel):
        # Une autre lecture, dans un autre thread, n'est pas concernée
        worker = threading.Thread(
            target=lambda: texts.append(PDFProcessor().extract_text(str(scanned_pdf)))
        )
        worker.start()
        worker.join(120)
    assert texts and EXPECTED_WORDS <= _words(texts[0])
    # Hors du bloc, la lecture reprend normalement
    assert EXPECTED_WORDS <= _words(PDFProcessor().extract_text(str(scanned_pdf)))
