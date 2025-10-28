"""
Processeur de fichiers pour My AI
Gère l'importation et le traitement de documents PDF, DOCX, etc.
"""

import json
from pathlib import Path
from typing import Any, Dict, List

import docx
import pdfplumber
import PyPDF2


class FileProcessor:
    """Processeur de fichiers pour documents"""

    def __init__(self):
        self.supported_extensions = [".txt", ".md", ".py", ".pdf", ".docx", ".json"]

    def process_file(self, file_path: str) -> Dict[str, Any]:
        """Traite un fichier et retourne son contenu"""
        try:
            path = Path(file_path)

            if not path.exists():
                return {"error": f"Fichier non trouvé: {file_path}"}

            extension = path.suffix.lower()

            if extension == ".txt" or extension == ".md" or extension == ".py":
                return self._process_text_file(path)
            elif extension == ".json":
                return self._process_json_file(path)
            elif extension == ".pdf":
                return self._process_pdf_file(path)
            elif extension == ".docx":
                return self._process_docx_file(path)
            else:
                return {"error": f"Type de fichier non supporté: {extension}"}

        except (OSError, UnicodeDecodeError, ValueError) as e:
            return {"error": f"Erreur lors du traitement: {str(e)}"}

    def _process_text_file(self, path: Path) -> Dict[str, Any]:
        """Traite un fichier texte"""
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()

            return {
                "type": "text",
                "name": path.name,
                "content": content,
                "size": len(content),
                "lines": content.count("\n") + 1,
            }
        except UnicodeDecodeError:
            # Essayer avec d'autres encodages
            try:
                with open(path, "r", encoding="latin-1") as f:
                    content = f.read()
                return {
                    "type": "text",
                    "name": path.name,
                    "content": content,
                    "size": len(content),
                    "lines": content.count("\n") + 1,
                    "encoding": "latin-1",
                }
            except (OSError, UnicodeDecodeError) as e:
                return {"error": f"Impossible de lire le fichier: {str(e)}"}

    def _process_json_file(self, path: Path) -> Dict[str, Any]:
        """Traite un fichier JSON"""
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)

            return {
                "type": "json",
                "name": path.name,
                "content": json.dumps(data, indent=2, ensure_ascii=False),
                "data": data,
                "size": path.stat().st_size,
            }
        except json.JSONDecodeError as e:
            return {"error": f"Erreur JSON: {str(e)}"}
        except OSError as e:
            return {"error": f"Erreur d'accès au fichier JSON: {str(e)}"}

    def _process_pdf_file(self, path: Path) -> Dict[str, Any]:
        """Traite un fichier PDF (nécessite PyPDF2 ou pdfplumber)"""
        try:
            # Essayer avec PyPDF2
            try:
                return self._extract_pdf_pypdf2(path)
            except ImportError:
                pass

            # Essayer avec pdfplumber
            try:
                return self._extract_pdf_pdfplumber(path)
            except ImportError:
                pass

            return {
                "error": "Aucune bibliothèque PDF disponible (PyPDF2 ou pdfplumber requis)"
            }

        except (ImportError, OSError) as e:
            return {"error": f"Erreur PDF: {str(e)}"}

    def _process_docx_file(self, path: Path) -> Dict[str, Any]:
        """Traite un fichier DOCX (nécessite python-docx)"""
        try:
            doc = docx.Document(path)
            text_content = []

            for paragraph in doc.paragraphs:
                if paragraph.text.strip():
                    text_content.append(paragraph.text)

            content = "\n".join(text_content)

            return {
                "type": "docx",
                "name": path.name,
                "content": content,
                "paragraphs": len(text_content),
                "size": len(content),
            }

        except ImportError:
            return {"error": "python-docx requis pour les fichiers DOCX"}
        except OSError as e:
            return {"error": f"Erreur d'accès au fichier DOCX: {str(e)}"}
        except docx.opc.exceptions.PackageNotFoundError as e:
            return {"error": f"Erreur de lecture du fichier DOCX: {str(e)}"}

    def _extract_pdf_pypdf2(self, path: Path) -> Dict[str, Any]:
        """Extraction PDF avec PyPDF2"""

        with open(path, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            text_content = []

            for page in reader.pages:
                text_content.append(page.extract_text())

        content = "\n".join(text_content)

        return {
            "type": "pdf",
            "name": path.name,
            "content": content,
            "pages": len(reader.pages),
            "size": len(content),
            "extractor": "PyPDF2",
        }

    def _extract_pdf_pdfplumber(self, path: Path) -> Dict[str, Any]:
        """Extraction PDF avec pdfplumber"""

        text_content = []

        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    text_content.append(text)

        content = "\n".join(text_content)

        return {
            "type": "pdf",
            "name": path.name,
            "content": content,
            "pages": len(text_content),
            "size": len(content),
            "extractor": "pdfplumber",
        }

    def get_supported_extensions(self) -> List[str]:
        """Retourne les extensions supportées"""
        return self.supported_extensions.copy()

    def is_supported(self, file_path: str) -> bool:
        """Vérifie si un fichier est supporté"""
        extension = Path(file_path).suffix.lower()
        return extension in self.supported_extensions
