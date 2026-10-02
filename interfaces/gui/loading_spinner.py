"""
Cercle de chargement : anneau transparent dont un arc orange tourne

Affiché dans l'aperçu d'une pièce jointe tant qu'elle est en cours de lecture.
Les images sont dessinées avec Pillow à 4 fois la taille affichée puis réduites :
le bord reste lisse (le Canvas Tk ne lisse pas les courbes). Avec
CustomTkinter, ce sont des CTkImage : CTk les redimensionne selon la mise à
l'échelle de l'écran (100 %, 125 %, 150 %...), y compris quand elle change
pendant que l'app tourne, exactement comme le texte voisin.
"""

import tkinter as tk
from typing import Dict, List

try:
    from PIL import Image, ImageDraw, ImageTk

    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

try:
    import customtkinter as ctk

    CTK_AVAILABLE = True
except ImportError:
    CTK_AVAILABLE = False

# Diamètre et épaisseur du trait à 100 % d'échelle (en pixels)
SIZE = 14
STROKE = 2
# Images par tour et durée de chacune : un tour en ≈ 1 s
FRAMES = 24
PERIOD_MS = 40
# Longueur de l'arc plein ; le reste du cercle est un bord pâle
ARC_DEGREES = 110
TRACK_ALPHA = 70
# Facteur de suréchantillonnage du dessin (bord lissé jusqu'à 400 % d'échelle)
_SUPERSAMPLE = 4

_frames_cache: Dict[str, list] = {}


def create_loading_spinner(parent, color: str, background: str, use_ctk: bool):
    """
    Crée le cercle de chargement (à placer avec pack ou grid)

    Args:
        parent: Conteneur du cercle
        color: Couleur du bord (accent de l'app)
        background: Couleur du conteneur, visible au centre du cercle
        use_ctk: Interface CustomTkinter (mise à l'échelle gérée par CTk)

    Returns:
        Le widget ; il tourne jusqu'à sa destruction
    """
    if not PIL_AVAILABLE:
        return tk.Label(parent, text="⏳", bg=background, fg=color, bd=0)
    frames = _frames(color)
    if use_ctk and CTK_AVAILABLE:
        images = [ctk.CTkImage(light_image=f, dark_image=f, size=(SIZE, SIZE)) for f in frames]
        widget = ctk.CTkLabel(
            parent, text="", image=images[0], width=SIZE, height=SIZE, fg_color="transparent"
        )
    else:
        # Sans CTk, l'app ne gère pas la mise à l'échelle : Windows agrandit la fenêtre
        images = [
            ImageTk.PhotoImage(f.resize((SIZE, SIZE), Image.Resampling.LANCZOS), master=parent)
            for f in frames
        ]
        widget = tk.Label(parent, image=images[0], bg=background, bd=0, highlightthickness=0)
    _Rotation(widget, images)
    return widget


def _frames(color: str) -> list:
    """Images RGBA d'un tour, dans le sens des aiguilles d'une montre."""
    if color not in _frames_cache:
        rgb = tuple(int(color.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4))
        side, stroke = SIZE * _SUPERSAMPLE, STROKE * _SUPERSAMPLE
        box = (stroke // 2, stroke // 2, side - 1 - stroke // 2, side - 1 - stroke // 2)
        frames = []
        for step in range(FRAMES):
            # Fond transparent de la même teinte : pas de liseré sombre à la réduction
            image = Image.new("RGBA", (side, side), rgb + (0,))
            draw = ImageDraw.Draw(image)
            draw.ellipse(box, outline=rgb + (TRACK_ALPHA,), width=stroke)
            start = step * 360 / FRAMES
            draw.arc(box, start=start, end=start + ARC_DEGREES, fill=rgb + (255,), width=stroke)
            frames.append(image)
        _frames_cache[color] = frames
    return _frames_cache[color]


class _Rotation:
    """Fait défiler les images d'un widget toutes les PERIOD_MS ms, jusqu'à sa destruction."""

    def __init__(self, widget, images: List):
        self._widget = widget
        self._images = images  # gardées en mémoire tant que l'animation tourne
        self._step = 0
        # Minuterie portée par la fenêtre et non par le widget : détruire le
        # widget supprimerait la commande planifiée (« invalid command name »)
        self._window = widget.winfo_toplevel()
        self._window.after(PERIOD_MS, self._next_frame)

    def _next_frame(self):
        try:
            if not self._widget.winfo_exists():
                return
            self._step = (self._step + 1) % len(self._images)
            self._widget.configure(image=self._images[self._step])
            self._window.after(PERIOD_MS, self._next_frame)
        except tk.TclError:  # fenêtre fermée entre deux images
            pass
