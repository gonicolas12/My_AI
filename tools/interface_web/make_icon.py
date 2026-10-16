"""
Icône de la fenêtre : le robot de vscode_extension/media/icon-activitybar.svg,
dans la couleur --accent de frontend/src/styles/tokens.css.

Usage, depuis la racine du dépôt :
  python tools/interface_web/make_icon.py interfaces/desktop/assets/my_ai.ico [APERCU.png]
"""

import sys

from PIL import Image, ImageDraw

ACCENT = (0xFF, 0x6B, 0x47, 255)
CLEAR = (0, 0, 0, 0)
SIZE = 1024
SCALE = SIZE / 24.0  # le SVG est dessiné sur 24 × 24
SIZES = [(16, 16), (20, 20), (24, 24), (32, 32), (40, 40), (48, 48), (64, 64), (128, 128), (256, 256)]


def box(x0, y0, x1, y1):
    """Rectangle du SVG (24 × 24) en pixels de l'image."""
    return [round(x0 * SCALE), round(y0 * SCALE), round(x1 * SCALE), round(y1 * SCALE)]


def robot() -> Image.Image:
    """Robot de 256 px, dessiné en 1024 px puis réduit (bords lissés)."""
    img = Image.new("RGBA", (SIZE, SIZE), CLEAR)
    draw = ImageDraw.Draw(img)
    # Antennes : boule + tige
    for cx in (7, 17):
        draw.ellipse(box(cx - 1, 0.5, cx + 1, 2.5), fill=ACCENT)
        draw.rounded_rectangle(box(cx - 0.4, 2.4, cx + 0.4, 5.2), radius=round(0.4 * SCALE), fill=ACCENT)
    # Tête
    draw.rounded_rectangle(box(1, 4.5, 23, 22), radius=round(4 * SCALE), fill=ACCENT)
    # Yeux et bouche : des trous
    draw.rounded_rectangle(box(5, 9.25, 10, 13.25), radius=round(1.25 * SCALE), fill=CLEAR)
    draw.rounded_rectangle(box(14, 9.25, 19, 13.25), radius=round(1.25 * SCALE), fill=CLEAR)
    draw.rounded_rectangle(box(9, 15.75, 15, 17.75), radius=round(1 * SCALE), fill=CLEAR)
    return img.resize((256, 256), Image.Resampling.LANCZOS)


def main():
    """Écrit l'icône, et l'aperçu PNG s'il est demandé."""
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    image = robot()
    image.save(sys.argv[1], format="ICO", sizes=SIZES)
    if len(sys.argv) > 2:
        image.save(sys.argv[2])
    print("icône écrite :", sys.argv[1])


if __name__ == "__main__":
    main()
