"""
Lecture des pièces jointes des agents
Partagée par la page Agents du GUI et le Relay mobile
"""

import os

from processors.docx_processor import DOCXProcessor
from processors.excel_processor import ExcelProcessor
from processors.ocr import MISSING_OCR_HINT, ocr_available
from processors.pdf_processor import PDFProcessor
from processors.pptx_processor import PPTXProcessor

# Taille maximale lue pour un fichier texte ou de code (en caractères)
MAX_TEXT_CHARS = 200_000


def read_attachment_text(file_path: str, file_type: str = "") -> str:
    """
    Extrait le texte d'une pièce jointe

    Les documents (PDF, Word, Excel/CSV, PowerPoint) passent par leur
    processeur ; les autres fichiers (code, texte, markdown...) sont lus
    tels quels.

    Args:
        file_path: Chemin vers le fichier
        file_type: Type choisi dans le GUI ("PDF", "DOCX", "Excel",
            "PowerPoint"...) ; à défaut, l'extension décide

    Returns:
        Texte de la pièce jointe

    Raises:
        ValueError: Si le texte d'un document n'a pas pu être extrait. On ne
            retombe jamais sur une lecture brute : les octets du fichier
            finiraient tels quels dans le prompt de l'agent.
        OSError: Si un fichier texte ne peut pas être ouvert
    """
    ext = os.path.splitext(file_path)[1].lower()

    if file_type == "PDF" or ext == ".pdf":
        # Les pages scannées passent par l'OCR de PDFProcessor
        text = PDFProcessor().extract_text(file_path)
        if not text.strip():
            raise ValueError(
                "Aucun texte reconnu dans ce PDF" if ocr_available() else MISSING_OCR_HINT
            )
        return text

    if file_type == "DOCX" or ext in (".docx", ".doc"):
        result = DOCXProcessor().extract_text(file_path)
    elif file_type == "Excel" or ext in (".xlsx", ".xls", ".csv"):
        result = ExcelProcessor().extract_text(file_path)
    elif file_type == "PowerPoint" or ext in (".pptx", ".potx"):
        result = PPTXProcessor().extract_text(file_path)
    else:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            return f.read(MAX_TEXT_CHARS)

    if not result.get("success"):
        raise ValueError(result.get("error", "Erreur inconnue"))
    return result["content"]
