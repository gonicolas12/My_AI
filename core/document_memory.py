"""
Lecture d'un fichier pour la mémoire des documents (bouton « Ajouter » de
l'onglet Documents)

Un document : le texte que range une pièce jointe du chat, lu par les mêmes
processeurs (CustomAIModel.read_file_for_context, sinon utils.file_processor).
Un fichier ajouté puis joint au chat garde ainsi le même identifiant dans
ChromaDB, et n'y est jamais rangé deux fois.

Une image : sa description par le modèle de vision (le modèle de chat s'il voit
les images, comme dans le chat), puis le texte que l'OCR y lit. L'une ou
l'autre suffit : une photo sans texte reste retrouvable par sa description, une
capture lue par l'OCR reste utile sans Ollama. Sa description changeant d'une
fois à l'autre, une image est rangée sous l'empreinte de son fichier
(image_document_id) : la même image n'est ni décrite ni rangée deux fois.
"""

import hashlib
import os
from typing import Any, Callable, Optional, Tuple

from core.chat_service import encode_image, file_type_for
from core.i18n import tr
from utils.logger import setup_logger

logger = setup_logger("DocumentMemory")

# Étapes de la lecture d'un fichier, affichées dans l'onglet Documents
STAGE_READING = "reading"
STAGE_DESCRIBING = "describing"


class DocumentReadError(Exception):
    """Fichier illisible, ou rien à retenir ; le message s'affiche tel quel."""


def read_document(
    path: str,
    local_ai: Any = None,
    file_processor: Any = None,
    on_stage: Optional[Callable[[str], None]] = None,
) -> Tuple[str, str]:
    """
    Texte à mettre en mémoire pour un fichier, et son type

    Args:
        path: Fichier à lire
        local_ai: CustomAIModel du moteur (processeurs de fichiers, modèle de vision)
        file_processor: utils.file_processor.FileProcessor (repli)
        on_stage: Appelé avec STAGE_DESCRIBING avant la description d'une image

    Returns:
        (texte, type de pièce jointe : PDF, DOCX, Excel, PowerPoint, Code ou Image)

    Raises:
        DocumentReadError: format non pris en charge, fichier vide ou illisible
    """
    kind = file_type_for(path)
    if kind is None:
        ext = os.path.splitext(path)[1].lower() or "?"
        raise DocumentReadError(tr("chat.unsupportedFormat", ext=ext))
    if kind == "Image":
        return read_image(path, local_ai, on_stage), kind
    return _read_text(path, local_ai, file_processor), kind


def _read_text(path: str, local_ai: Any, file_processor: Any) -> str:
    """Texte d'un document : celui d'une pièce jointe du chat."""
    name = os.path.basename(path)
    content = ""
    reader = getattr(local_ai, "read_file_for_context", None)
    if callable(reader):
        try:
            content = (reader(path) or {}).get("content") or ""
        except Exception as exc:  # pylint: disable=broad-except
            logger.warning("Lecture de %s par les processeurs du modèle impossible : %s",
                           name, exc)
    if not content.strip():
        # Repli, et message d'erreur précis (PDF scanné sans OCR, format…)
        if file_processor is None:
            # pylint: disable-next=import-outside-toplevel
            from utils.file_processor import FileProcessor
            file_processor = FileProcessor()
        result = file_processor.process_file(path) or {}
        if result.get("error"):
            raise DocumentReadError(str(result["error"]))
        content = result.get("content") or ""
    if not content.strip():
        raise DocumentReadError(tr("chat.fileEmpty", name=name))
    return content


def read_image(path: str, local_ai: Any = None,
               on_stage: Optional[Callable[[str], None]] = None) -> str:
    """
    Texte d'une image : sa description, puis le texte lu par l'OCR

    Raises:
        DocumentReadError: ni description (pas de modèle de vision) ni texte lisible
    """
    name = os.path.basename(path)
    text = ""
    try:
        from processors.ocr import ocr_image  # pylint: disable=import-outside-toplevel
        text = ocr_image(path).strip()
    except Exception as exc:  # pylint: disable=broad-except
        logger.warning("OCR de %s impossible : %s", name, exc)
    if on_stage is not None:
        on_stage(STAGE_DESCRIBING)
    description = describe_image(path, local_ai)
    if not description and not text:
        raise DocumentReadError(tr("memory.documents.imageEmpty"))
    return image_text(description, text)


# Description d'une image pour la mémoire : un paragraphe (≈ 100 à 200 tokens)
_DESCRIPTION_MAX_TOKENS = 400


def describe_image(path: str, local_ai: Any) -> str:
    """Description de l'image par le modèle de vision, "" sans modèle de vision ni Ollama.

    Consigne de la mémoire (memory.documents.visionPrompt), dans la langue de
    l'interface : un paragraphe sobre, le texte visible recopié. La description
    détaillée du chat, avec titres, listes et emojis, en faisait 4 morceaux.
    """
    llm = getattr(local_ai, "local_llm", None)
    describe = getattr(llm, "describe_image", None)
    if not callable(describe):
        return ""
    try:
        image_b64, _width, _height = encode_image(path)
        return (describe(image_b64, instructions=tr("memory.documents.visionPrompt"),
                         max_tokens=_DESCRIPTION_MAX_TOKENS) or "").strip()
    except Exception as exc:  # pylint: disable=broad-except
        logger.warning("Description de %s impossible : %s", os.path.basename(path), exc)
        return ""


def _file_digest(path: str, prefix: bytes = b"") -> str:
    """Empreinte SHA-1 du contenu d'un fichier, précédé de prefix."""
    digest = hashlib.sha1(prefix)
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def image_document_id(path: str) -> str:
    """Identifiant d'une image dans la mémoire : l'empreinte de son contenu.

    Ni son nom (deux captures « clipboard_image.png ») ni sa description (qui
    change d'une fois à l'autre) : la même image n'est rangée qu'une fois.

    Raises:
        OSError: fichier illisible
    """
    return f"image_{_file_digest(path)[:16]}"


def folder_document_id(path: str, name: str) -> str:
    """Identifiant d'un fichier d'un dossier déposé : son nom dans la mémoire
    (« dossier/chemin ») et l'empreinte de son contenu.

    Déposer de nouveau le dossier ne relit pas un fichier inchangé (une image
    n'est pas redécrite) ; un fichier modifié change d'identifiant, et sa
    nouvelle version remplace l'ancienne (MemoryStore.add_document, replace).
    Deux fichiers identiques du dossier, sous deux chemins, y restent deux
    documents.

    Raises:
        OSError: fichier illisible
    """
    return f"folder_{_file_digest(path, name.encode('utf-8') + b'\0')[:24]}"


def image_text(description: str, text: str) -> str:
    """Contenu rangé pour une image : description, puis texte lu, chacun sous son titre."""
    parts = []
    if description:
        parts.append(f"{tr('memory.documents.imageDescription')}\n{description}")
    if text:
        parts.append(f"{tr('memory.documents.imageText')}\n{text}")
    return "\n\n".join(parts)
