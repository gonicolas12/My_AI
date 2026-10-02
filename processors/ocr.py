"""
OCR des pages PDF sans couche texte (documents scannés)
Moteur : RapidOCR, modèles ONNX fournis avec le paquet (fonctionne hors ligne)
"""

import os
import threading
from collections import OrderedDict
from contextlib import contextmanager

try:
    from rapidocr import RapidOCR
except ImportError:  # OCR indisponible : les pages scannées restent sans texte
    RapidOCR = None

# Résolution du rendu des pages avant OCR
OCR_DPI = 200

# Message quand un PDF sans texte ne peut pas être lu faute d'OCR
MISSING_OCR_HINT = (
    "Aucun texte dans ce PDF (scan ?) : installez rapidocr pour activer l'OCR "
    "(pip install rapidocr)"
)

# Pages déjà reconnues : un même PDF est lu plusieurs fois par le chat
_CACHE_SIZE = 512
_cache: "OrderedDict[tuple, str]" = OrderedDict()

_engine = None
_lock = threading.Lock()

# Lecture en cours dans ce thread : événement levé si elle doit s'arrêter
_reading = threading.local()


class OcrInterrupted(Exception):
    """Lecture abandonnée avant la page suivante (pièce jointe retirée pendant l'OCR)."""


@contextmanager
def interruptible(cancel):
    """
    Pendant ce bloc, dans ce thread, l'OCR s'arrête dès que `cancel` est levé

    Chaque page coûte ≈ 4 s de calcul : sans ce point d'arrêt, un PDF scanné
    retiré du message continuerait d'occuper le processeur pendant que le
    modèle répond.

    Args:
        cancel: threading.Event, ou None (lecture non interruptible)

    Raises:
        OcrInterrupted: Depuis ocr_page, à la première page après la levée
    """
    previous = getattr(_reading, "cancel", None)
    _reading.cancel = cancel
    try:
        yield
    finally:
        _reading.cancel = previous


def ocr_available() -> bool:
    """
    Indique si le moteur OCR est installé
    """
    return RapidOCR is not None


def ocr_page(page) -> str:
    """
    Reconnaît le texte d'une page PyMuPDF rendue en image

    Args:
        page: Page PyMuPDF (pymupdf.Page)

    Returns:
        Texte reconnu, une ligne par bloc de texte détecté

    Raises:
        OcrInterrupted: Lecture interrompue (cf. interruptible)
    """
    _stop_if_interrupted()
    key = _cache_key(page)
    # Un seul OCR à la fois : PyMuPDF n'est pas sûr entre threads et le moteur est partagé
    with _lock:
        _stop_if_interrupted()  # interrompue pendant l'attente d'une autre lecture
        if key in _cache:
            _cache.move_to_end(key)
            return _cache[key]

        image = page.get_pixmap(dpi=OCR_DPI).tobytes("png")
        text = "\n".join(_get_engine()(image).txts or ())
        if key is not None:
            _cache[key] = text
            if len(_cache) > _CACHE_SIZE:
                _cache.popitem(last=False)
        return text


def _stop_if_interrupted():
    cancel = getattr(_reading, "cancel", None)
    if cancel is not None and cancel.is_set():
        raise OcrInterrupted("lecture interrompue")


def _get_engine():
    """Moteur créé au premier usage (≈ 0,5 s), appelé sous _lock."""
    global _engine  # pylint: disable=global-statement
    if _engine is None:
        # Niveau passé au moteur : il réapplique le sien (info) à la création
        _engine = RapidOCR(params={"Global.log_level": "error"})
    return _engine


def _cache_key(page):
    """Fichier + date de modification + n° de page ; None pour un PDF ouvert en mémoire."""
    path = page.parent.name
    try:
        stat = os.stat(path)
    except (OSError, TypeError, ValueError):
        return None
    return (os.path.abspath(path), stat.st_mtime_ns, stat.st_size, page.number)
