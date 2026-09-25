"""
Processeur de fichiers PPTX
Lecture, analyse et extraction de contenu PowerPoint
"""

import io
import os
import zipfile
from pathlib import Path
from typing import Any, Dict, List

from pptx import Presentation

from processors.path_resolution import resolve_onedrive_path

# Un modèle .potx a la structure d'un .pptx : seul le type de contenu de sa
# partie principale diffère, et python-pptx refuse de l'ouvrir tel quel.
_TEMPLATE_CONTENT_TYPE = (
    b"application/vnd.openxmlformats-officedocument.presentationml.template.main+xml"
)
_PRESENTATION_CONTENT_TYPE = (
    b"application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml"
)


def _open_presentation(path: str):
    """Ouvre un .pptx, ou un modèle .potx présenté en mémoire comme un .pptx."""
    if Path(path).suffix.lower() != ".potx":
        return Presentation(path)
    buffer = io.BytesIO()
    with zipfile.ZipFile(path) as source, zipfile.ZipFile(
        buffer, "w", zipfile.ZIP_DEFLATED
    ) as target:
        for item in source.infolist():
            data = source.read(item.filename)
            if item.filename == "[Content_Types].xml":
                data = data.replace(_TEMPLATE_CONTENT_TYPE, _PRESENTATION_CONTENT_TYPE)
            target.writestr(item, data)
    buffer.seek(0)
    return Presentation(buffer)


class PPTXProcessor:
    """
    Processeur pour les fichiers PPTX (PowerPoint)
    """

    def __init__(self):
        """
        Initialise le processeur PPTX
        """
        # .ppt (format binaire pré-2007) n'est pas lisible par python-pptx.
        self.supported_extensions = [".pptx", ".potx"]
        self._check_dependencies()

    def _check_dependencies(self):
        """
        Vérifie la disponibilité des bibliothèques PPTX
        """
        self.python_pptx_available = False

        try:
            # Test d'import complet
            self.python_pptx_available = True
            print("✅ Module python-pptx disponible")
        except ImportError as e:
            print(f"❌ Module 'python-pptx' non installé: {e}")
            print("💡 Installez avec: pip install python-pptx")
        except Exception as e:
            print(f"❌ Erreur lors de l'import python-pptx: {e}")

    def read_pptx(self, file_path: str) -> Dict[str, Any]:
        """
        Lit un fichier PPTX et extrait le contenu - Version avec support OneDrive
        """
        resolved_path = self._resolve_onedrive_path(file_path)

        if not os.path.exists(resolved_path):
            return {
                "success": False,
                "error": f"Fichier non trouvé: {file_path}",
                "error_type": "FILE_NOT_FOUND",
                "resolution": "Vérifiez que le fichier existe ou qu'il est synchronisé depuis OneDrive",
            }

        if not self.python_pptx_available:
            return {
                "success": False,
                "error": "python-pptx non disponible. Installez avec: pip install python-pptx",
                "error_type": "MISSING_PACKAGE",
                "resolution": "Installez le package avec : pip install python-pptx",
            }

        try:
            print(f"📂 Lecture du fichier: {resolved_path}")
            presentation = _open_presentation(resolved_path)

            content = {
                "text": "",
                "slides": [],
                "properties": {},
            }
            text_parts: List[str] = []

            for index, slide in enumerate(presentation.slides, start=1):
                slide_data = self._extract_slide(slide, index)
                content["slides"].append(slide_data)

                # Représentation textuelle destinée au contexte du modèle
                text_parts.append(f"--- Diapositive {index} ---")
                if slide_data["title"]:
                    text_parts.append(slide_data["title"])
                text_parts.extend(slide_data["bullets"])
                for table in slide_data["tables"]:
                    for row in table["rows"]:
                        text_parts.append(" | ".join(row))
                if slide_data["notes"]:
                    text_parts.append(f"[Notes] {slide_data['notes']}")
                text_parts.append("")

            content["text"] = "\n".join(text_parts)

            props = presentation.core_properties
            content["properties"] = {
                "title": props.title,
                "author": props.author,
                "subject": props.subject,
                "created": str(props.created) if props.created else None,
                "modified": str(props.modified) if props.modified else None,
                "slide_count": len(content["slides"]),
            }

            return {
                "success": True,
                "content": content,
                "file_info": {
                    "original_path": file_path,
                    "resolved_path": resolved_path,
                    "size": os.path.getsize(resolved_path),
                    "processor": "python-pptx",
                },
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"Erreur lors de la lecture PPTX: {str(e)}",
                "error_type": "PROCESSING_ERROR",
                "resolution": "Vérifiez que le fichier n'est pas corrompu et qu'il est accessible",
            }

    def _extract_slide(self, slide, number: int) -> Dict[str, Any]:
        """
        Extrait le contenu d'une diapositive.

        Args:
            slide: Objet Slide de python-pptx
            number: Numéro de la diapositive (1-based)

        Returns:
            {slide_number, title, bullets, tables, notes}
        """
        title = ""
        if slide.shapes.title is not None:
            title = (slide.shapes.title.text or "").strip()

        bullets: List[str] = []
        tables: List[Dict[str, Any]] = []

        for shape in slide.shapes:
            if shape.has_table:
                tables.append({
                    "rows": [
                        [cell.text.strip() for cell in row.cells]
                        for row in shape.table.rows
                    ]
                })
                continue

            if not shape.has_text_frame:
                continue
            # Le titre est déjà capturé : ne pas le répéter dans les puces.
            if slide.shapes.title is not None and shape == slide.shapes.title:
                continue

            for paragraph in shape.text_frame.paragraphs:
                text = "".join(run.text for run in paragraph.runs).strip()
                if text:
                    bullets.append("    " * paragraph.level + text)

        notes = ""
        if slide.has_notes_slide:
            notes = (slide.notes_slide.notes_text_frame.text or "").strip()

        return {
            "slide_number": number,
            "title": title,
            "bullets": bullets,
            "tables": tables,
            "notes": notes,
        }

    def _resolve_onedrive_path(self, file_path: str) -> str:
        """
        Résout les chemins OneDrive pour les rendre accessibles

        Args:
            file_path: Chemin du fichier (peut être OneDrive)

        Returns:
            Chemin résolu et accessible
        """
        return resolve_onedrive_path(file_path)

    def is_supported(self, file_path: str) -> bool:
        """
        Vérifie si le fichier est supporté

        Args:
            file_path: Chemin vers le fichier

        Returns:
            True si le fichier est supporté
        """
        return Path(file_path).suffix.lower() in self.supported_extensions

    def extract_text(self, file_path: str) -> Dict[str, Any]:
        """
        Extrait le texte d'un fichier PPTX avec gestion des erreurs

        Args:
            file_path: Chemin vers le fichier PPTX

        Returns:
            Dict avec le texte extrait et les métadonnées ou l'erreur
        """
        if not self.python_pptx_available:
            return {
                "success": False,
                "error": "Le module python-pptx n'est pas installé",
                "error_type": "MISSING_PACKAGE",
                "resolution": "Installez le package avec : pip install python-pptx",
            }

        result = self.read_pptx(file_path)
        if not result.get("success"):
            return result

        content = result["content"]
        if not content.get("text", "").strip():
            return {
                "success": False,
                "error": "Présentation vide ou non lisible",
                "error_type": "EMPTY_CONTENT",
            }

        return {
            "success": True,
            "content": content["text"],
            "metadata": {
                "slides": len(content["slides"]),
                "properties": content["properties"],
            },
        }

    def extract_text_from_pptx(self, file_path: str) -> str:
        """
        Méthode pour extraire du texte d'un fichier PPTX (compatible avec l'interface GUI)

        Args:
            file_path: Chemin vers le fichier PPTX

        Returns:
            Texte extrait du fichier PPTX
        """
        try:
            result = self.extract_text(file_path)
            if result.get("success", False):
                return result.get("content", "")
            raise Exception(result.get("error", "Erreur inconnue"))
        except Exception as e:
            raise Exception(f"Erreur lors de l'extraction PPTX: {str(e)}") from e
