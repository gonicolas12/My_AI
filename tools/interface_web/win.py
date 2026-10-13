"""
Pilotage Win32 de la vraie fenêtre My_AI, pour les vérifications
(frontend/scripts/window_*.mjs).

  python tools/interface_web/win.py rect             bornes de la fenêtre, [x, y, largeur, hauteur]
  python tools/interface_web/win.py origin           coin haut gauche de la page, [x, y] à l'écran
  python tools/interface_web/win.py state            normale, agrandie ou réduite
  python tools/interface_web/win.py screen           bornes du bureau (tous les écrans), [x, y, largeur, hauteur]
  python tools/interface_web/win.py move X Y W H     déplace et redimensionne (restaurée)
  python tools/interface_web/win.py close            WM_CLOSE (comme la croix)
  python tools/interface_web/win.py front            met My_AI au premier plan
  python tools/interface_web/win.py shot FICHIER     premier plan, puis capture (barre de titre comprise)
  python tools/interface_web/win.py capture FICHIER  capture sans premier plan ni saisie (PrintWindow),
                                                     lecteur PDF compris (absent des captures CDP)
  python tools/interface_web/win.py keys TOUCHE...   premier plan, puis touches (ex. f5 ctrl+r ctrl+b esc)
  python tools/interface_web/win.py cursor X Y       déplace le vrai curseur

Les touches et le curseur du système vont à la fenêtre au premier plan, pas à
celle qu'on vise. front, shot, keys et cursor attendent donc que le clavier et
la souris n'aient pas servi depuis IDLE_S secondes (WAIT_S secondes au plus,
sinon refus, code de sortie 2), et keys n'envoie chaque touche que si My_AI est
au premier plan. rect, origin, state, screen, capture et close ne touchent ni
au focus ni aux saisies ; move restaure la fenêtre, ce qui peut l'activer.
"""

import ctypes
import json
import sys
import tempfile
import time
from ctypes import wintypes
from pathlib import Path

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32
kernel32.GetTickCount.restype = wintypes.DWORD
user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))

TITLE = "My_AI"
IDLE_S = 20
WAIT_S = 60
# Heure (GetTickCount) de la dernière saisie envoyée par cet outil
OWN_INPUT = Path(tempfile.gettempdir()) / "my_ai_win_last_input.txt"
VK = {
    "ctrl": 0x11, "shift": 0x10, "alt": 0x12, "esc": 0x1B, "enter": 0x0D,
    "f1": 0x70, "f3": 0x72, "f5": 0x74, "f7": 0x76, "f12": 0x7B,
    "left": 0x25, "right": 0x27, ",": 0xBC,
}


class LASTINPUTINFO(ctypes.Structure):  # pylint: disable=too-few-public-methods
    """Structure de GetLastInputInfo."""
    _fields_ = [("cbSize", wintypes.UINT), ("dwTime", wintypes.DWORD)]


class BITMAPINFOHEADER(ctypes.Structure):  # pylint: disable=too-few-public-methods
    """En-tête de GetDIBits (pixels de 32 bits, lignes de haut en bas)."""
    _fields_ = [("biSize", wintypes.DWORD), ("biWidth", wintypes.LONG),
                ("biHeight", wintypes.LONG), ("biPlanes", wintypes.WORD),
                ("biBitCount", wintypes.WORD), ("biCompression", wintypes.DWORD),
                ("biSizeImage", wintypes.DWORD), ("biXPelsPerMeter", wintypes.LONG),
                ("biYPelsPerMeter", wintypes.LONG), ("biClrUsed", wintypes.DWORD),
                ("biClrImportant", wintypes.DWORD)]


def find():
    """Fenêtre My_AI (quitte si elle est introuvable)."""
    hwnd = user32.FindWindowW(None, TITLE)
    if not hwnd:
        sys.exit("fenêtre introuvable")
    return hwnd


def rect(hwnd):
    """Bornes de la fenêtre à l'écran : [x, y, largeur, hauteur]."""
    r = wintypes.RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(r))
    return [r.left, r.top, r.right - r.left, r.bottom - r.top]


def own_input(last_tick):
    """Vrai si la dernière saisie du système est celle que cet outil a envoyée."""
    try:
        own = int(OWN_INPUT.read_text(encoding="ascii"))
    except (OSError, ValueError):
        return False
    # Compteurs de 32 bits en millisecondes : différences modulo 2**32
    return (own - last_tick) & 0xFFFFFFFF <= 1000


def require_idle():
    """Attend que le clavier et la souris n'aient pas servi depuis IDLE_S secondes.

    WAIT_S secondes au plus, puis refuse (code de sortie 2). Les saisies
    envoyées par cet outil ne comptent pas : si la dernière saisie du système
    est la sienne, personne n'a rien fait depuis.
    """
    deadline = time.monotonic() + WAIT_S
    told = False
    while True:
        info = LASTINPUTINFO(ctypes.sizeof(LASTINPUTINFO), 0)
        user32.GetLastInputInfo(ctypes.byref(info))
        if own_input(info.dwTime):
            return
        idle = ((kernel32.GetTickCount() - info.dwTime) & 0xFFFFFFFF) / 1000
        if idle >= IDLE_S:
            return
        if time.monotonic() >= deadline:
            print(f"refusé : clavier ou souris utilisés il y a {idle:.0f} s, rien n'est envoyé",
                  file=sys.stderr)
            sys.exit(2)
        if not told:
            print(f"en attente : ne plus toucher au clavier ni à la souris pendant {IDLE_S} s…",
                  file=sys.stderr, flush=True)
            told = True
        time.sleep(0.5)


def note_own_input():
    """Note l'heure de la saisie que cet outil vient d'envoyer."""
    OWN_INPUT.write_text(str(kernel32.GetTickCount()), encoding="ascii")


def foreground(hwnd):
    """Met la fenêtre au premier plan ; vrai si Windows l'a accepté."""
    # Une touche envoyée par ce processus autorise SetForegroundWindow. Maj et
    # non Alt : Alt seul ouvrirait le mode menu, qui avale la touche suivante
    if user32.GetForegroundWindow() != hwnd:
        user32.keybd_event(VK["shift"], 0, 0, 0)
        user32.keybd_event(VK["shift"], 0, 2, 0)
        note_own_input()
        user32.SetForegroundWindow(hwnd)
        time.sleep(0.4)
    return user32.GetForegroundWindow() == hwnd


def print_window(hwnd, path):
    """Capture de la fenêtre, même cachée par une autre, sans la mettre au premier plan.

    PrintWindow avec PW_RENDERFULLCONTENT : rendu composé de WebView2, lecteur
    PDF compris, que les captures par CDP laissent gris.
    """
    from PIL import Image  # pylint: disable=import-outside-toplevel
    gdi32 = ctypes.windll.gdi32
    _x, _y, width, height = rect(hwnd)
    window_dc = user32.GetWindowDC(hwnd)
    memory_dc = gdi32.CreateCompatibleDC(window_dc)
    bitmap = gdi32.CreateCompatibleBitmap(window_dc, width, height)
    try:
        gdi32.SelectObject(memory_dc, bitmap)
        if not user32.PrintWindow(hwnd, memory_dc, 2):  # PW_RENDERFULLCONTENT
            sys.exit("PrintWindow a échoué")
        header = BITMAPINFOHEADER(ctypes.sizeof(BITMAPINFOHEADER), width, -height, 1, 32,
                                  0, 0, 0, 0, 0, 0)
        pixels = ctypes.create_string_buffer(width * height * 4)
        gdi32.GetDIBits(memory_dc, bitmap, 0, height, pixels, ctypes.byref(header), 0)
        Image.frombuffer("RGB", (width, height), pixels, "raw", "BGRX", 0, 1).save(path)
    finally:
        gdi32.DeleteObject(bitmap)
        gdi32.DeleteDC(memory_dc)
        user32.ReleaseDC(hwnd, window_dc)
    return [width, height]


def press(hwnd, combo):
    """Envoie une combinaison (ex. ctrl+b), si My_AI est toujours au premier plan."""
    keys = combo.lower().split("+")
    codes = [VK.get(k, ord(k.upper()) if len(k) == 1 else None) for k in keys]
    if None in codes:
        sys.exit(f"touche inconnue : {combo}")
    if user32.GetForegroundWindow() != hwnd:
        print(f"refusé : My_AI n'est plus au premier plan, {combo} non envoyée", file=sys.stderr)
        sys.exit(2)
    for code in codes:
        user32.keybd_event(code, 0, 0, 0)
    for code in reversed(codes):
        user32.keybd_event(code, 0, 2, 0)
    note_own_input()
    time.sleep(0.4)


def main():  # pylint: disable=too-many-branches,too-many-statements
    """Action demandée sur la ligne de commande."""
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    action = sys.argv[1]
    hwnd = find()
    if action == "rect":
        print(json.dumps(rect(hwnd)))
    elif action == "origin":
        # La page est la première fenêtre enfant (WebView2)
        point = wintypes.POINT(0, 0)
        child = user32.FindWindowExW(hwnd, None, None, None)
        user32.ClientToScreen(child or hwnd, ctypes.byref(point))
        print(json.dumps([point.x, point.y]))
    elif action == "state":
        print("agrandie" if user32.IsZoomed(hwnd) else "réduite" if user32.IsIconic(hwnd) else "normale")
    elif action == "screen":
        # SM_XVIRTUALSCREEN, SM_YVIRTUALSCREEN, SM_CXVIRTUALSCREEN, SM_CYVIRTUALSCREEN
        print(json.dumps([user32.GetSystemMetrics(index) for index in (76, 77, 78, 79)]))
    elif action == "move":
        x, y, w, h = map(int, sys.argv[2:6])
        user32.ShowWindow(hwnd, 9)  # SW_RESTORE
        user32.MoveWindow(hwnd, x, y, w, h, True)
        time.sleep(0.5)
        print(json.dumps(rect(hwnd)))
    elif action == "close":
        user32.PostMessageW(hwnd, 0x0010, 0, 0)  # WM_CLOSE
        print("WM_CLOSE envoyé")
    elif action == "front":
        require_idle()
        if not foreground(hwnd):
            print("refusé : Windows n'a pas mis My_AI au premier plan", file=sys.stderr)
            sys.exit(2)
        print("premier plan")
    elif action == "shot":
        from PIL import ImageGrab  # pylint: disable=import-outside-toplevel
        require_idle()
        foreground(hwnd)
        x, y, w, h = rect(hwnd)
        ImageGrab.grab(bbox=(x, y, x + w, y + h), all_screens=True).save(sys.argv[2])
        print("capture", sys.argv[2], [x, y, w, h])
    elif action == "capture":
        print("capture", sys.argv[2], print_window(hwnd, sys.argv[2]))
    elif action == "keys":
        require_idle()
        if not foreground(hwnd):
            print("refusé : Windows n'a pas mis My_AI au premier plan, aucune touche envoyée",
                  file=sys.stderr)
            sys.exit(2)
        for combo in sys.argv[2:]:
            press(hwnd, combo)
            print("touche", combo)
    elif action == "cursor":
        require_idle()
        user32.SetCursorPos(int(sys.argv[2]), int(sys.argv[3]))
        note_own_input()
        print("curseur", sys.argv[2], sys.argv[3])
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()
