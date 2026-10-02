"""
Processeur de fichiers PDF
Lecture, analyse et extraction de contenu
"""

import os
from pathlib import Path
from typing import Any, Dict

# Bibliothèques optionnelles : read_pdf utilise la première disponible
try:
    import pymupdf
except ImportError:  # absent, ou PyMuPDF < 1.24.3 (module encore nommé fitz)
    pymupdf = None

try:
    import PyPDF2
except ImportError:
    PyPDF2 = None

from processors.ocr import OcrInterrupted, ocr_available, ocr_page


class PDFProcessor:
    """
    Processeur pour les fichiers PDF
    """

    def __init__(self):
        """
        Initialise le processeur PDF
        """
        self.supported_extensions = [".pdf"]
        self._check_dependencies()

    def _check_dependencies(self):
        """
        Vérifie la disponibilité des bibliothèques PDF
        """
        self.pymupdf_available = pymupdf is not None
        self.pypdf2_available = PyPDF2 is not None

    def read_pdf(self, file_path: str) -> Dict[str, Any]:
        """
        Lit un fichier PDF et extrait le contenu

        Args:
            file_path: Chemin vers le fichier PDF

        Returns:
            Dictionnaire avec le contenu extrait
        """
        if not os.path.exists(file_path):
            return {"error": "Fichier non trouvé", "content": ""}

        # Essayer PyMuPDF en premier (meilleur)
        if self.pymupdf_available:
            return self._read_with_pymupdf(file_path)
        if self.pypdf2_available:
            return self._read_with_pypdf2(file_path)
        return {
            "error": "Aucune bibliothèque PDF disponible. Installez PyMuPDF ou PyPDF2",
            "content": "",
        }

    def _read_with_pymupdf(self, file_path: str) -> Dict[str, Any]:
        """
        Lit un PDF avec PyMuPDF (recommandé)
        """
        try:
            doc = pymupdf.open(file_path)
            content = {
                "text": "",
                "pages": [],
                "metadata": doc.metadata,  # pylint: disable=no-member  # attribut dynamique
                "page_count": len(doc),
            }

            ocr_pages = 0
            for page_num, page in enumerate(doc):
                page_text = page.get_text()

                # Page sans couche texte (scan, PDF d'images) : OCR
                is_ocr = not page_text.strip() and ocr_available()
                if is_ocr:
                    page_text = ocr_page(page)
                    ocr_pages += 1

                content["pages"].append(
                    {
                        "page_number": page_num + 1,
                        "text": page_text,
                        "word_count": len(page_text.split()),
                        "ocr": is_ocr,
                    }
                )
                content["text"] += page_text + "\n"

            doc.close()

            return {
                "success": True,
                "content": content,
                "file_info": {
                    "path": file_path,
                    "size": os.path.getsize(file_path),
                    "processor": "PyMuPDF",
                    "ocr_pages": ocr_pages,
                },
            }

        except OcrInterrupted:
            # Pièce jointe retirée : remonter tel quel, sans repli sur PyPDF2
            raise
        except Exception as e:
            return {"error": f"Erreur PyMuPDF: {str(e)}", "content": ""}

    def _read_with_pypdf2(self, file_path: str) -> Dict[str, Any]:
        """
        Lit un PDF avec PyPDF2 (fallback)
        """
        try:
            with open(file_path, "rb") as file:
                reader = PyPDF2.PdfReader(file)

                content = {
                    "text": "",
                    "pages": [],
                    "metadata": reader.metadata if reader.metadata else {},
                    "page_count": len(reader.pages),
                }

                for page_num, page in enumerate(reader.pages):
                    page_text = page.extract_text()

                    content["pages"].append(
                        {
                            "page_number": page_num + 1,
                            "text": page_text,
                            "word_count": len(page_text.split()),
                        }
                    )
                    content["text"] += page_text + "\n"

                return {
                    "success": True,
                    "content": content,
                    "file_info": {
                        "path": file_path,
                        "size": os.path.getsize(file_path),
                        "processor": "PyPDF2",
                    },
                }

        except Exception as e:
            return {"error": f"Erreur PyPDF2: {str(e)}", "content": ""}

    def is_supported(self, file_path: str) -> bool:
        """
        Vérifie si le fichier est supporté

        Args:
            file_path: Chemin vers le fichier

        Returns:
            True si le fichier est supporté
        """
        return Path(file_path).suffix.lower() in self.supported_extensions

    def extract_text(self, file_path: str) -> str:
        """
        Extrait le texte d'un fichier PDF

        Args:
            file_path: Chemin vers le fichier PDF

        Returns:
            Texte extrait du PDF
        """
        try:
            result = self.read_pdf(file_path)
            if result.get("success"):
                return result["content"]["text"]
            raise ValueError(result.get("error", "Erreur inconnue"))
        except Exception as e:
            raise ValueError(f"Erreur lors de l'extraction de texte: {str(e)}") from e

    def extract_text_from_pdf(self, file_path: str) -> str:
        """
        Méthode alias pour compatibilité avec l'interface GUI
        """
        return self.extract_text(file_path)
