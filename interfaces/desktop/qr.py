"""
QR code du Relay pour la fenêtre (_draw_qr_on_canvas de Tk)

Matrice des modules, que la fenêtre dessine en SVG. Correction L : l'adresse
mène à une page HTTPS de routage, un code moins dense se lit mieux à l'écran.
Marge de 4 modules, celle de la norme : avec moins, des lecteurs (iOS) ne
trouvent pas les repères de coin.
"""

from functools import lru_cache
from typing import Optional, Tuple

try:
    import qrcode
    from qrcode.constants import ERROR_CORRECT_L
except ImportError:  # pragma: no cover
    qrcode = None  # pylint: disable=invalid-name

QR_BORDER = 4


@lru_cache(maxsize=4)
def qr_rows(text: str) -> Optional[Tuple[str, ...]]:
    """Lignes du code, « 1 » pour un module foncé, marge comprise ; None sans qrcode."""
    if qrcode is None:
        return None
    code = qrcode.QRCode(version=None, box_size=1, border=QR_BORDER,
                         error_correction=ERROR_CORRECT_L)
    code.add_data(text)
    code.make(fit=True)
    return tuple("".join("1" if cell else "0" for cell in row) for row in code.get_matrix())
