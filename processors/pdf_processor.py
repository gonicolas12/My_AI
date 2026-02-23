"""
Processeur de fichiers PDF
Lecture, analyse et extraction de contenu
"""

import os
from pathlib import Path
from typing import Any, Dict

import fitz  # PyMuPDF
import PyPDF2


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
        self.pymupdf_available = False
        self.pypdf2_available = False

        try:
            self.pymupdf_available = True
        except ImportError:
            pass

        try:
            self.pypdf2_available = True
        except ImportError:
            pass

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
            doc = fitz.open(file_path)
            content = {
                "text": "",
                "pages": [],
                "metadata": doc.metadata,
                "page_count": len(doc),
            }

            for page_num, page in enumerate(doc):
                page_text = page.get_text()

                content["pages"].append(
                    {
                        "page_number": page_num + 1,
                        "text": page_text,
                        "word_count": len(page_text.split()),
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
                },
            }

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
            if result["success"]:
                return result["content"]["text"]
            raise ValueError(result.get("error", "Erreur inconnue"))
        except Exception as e:
            raise ValueError(f"Erreur lors de l'extraction de texte: {str(e)}") from e

    def extract_text_from_pdf(self, file_path: str) -> str:
        """
        Méthode alias pour compatibilité avec l'interface GUI
        """
        return self.extract_text(file_path)
