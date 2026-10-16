"""
Pilotage Win32 de la vraie fenêtre My_AI, pour les vérifications
(frontend/scripts/window_*.mjs).

  python tools/interface_web/win.py rect             bornes de la fenêtre, [x, y, largeur, hauteur]
  python tools/interface_web/win.py origin           coin haut gauche de la page, [x, y] à l'écran
  python tools/interface_web/win.py state            normale, agrandie ou réduite
  python tools/interface_web/win.py screen           bornes du bureau (tous les écrans), [x, y, largeur, hauteur]
  python tools/interface_web/win.py move X Y W H [HWND]
                                                     déplace et redimensionne My_AI (restaurée), ou HWND
  python tools/interface_web/win.py close [HWND]     WM_CLOSE (comme la croix) à My_AI, ou à la fenêtre HWND
  python tools/interface_web/win.py windows [CLASSE] fenêtres visibles : [hwnd, classe, processus, titre]
  python tools/interface_web/win.py children         fenêtres enfants directes de My_AI : hwnd, classe,
                                                     visible, bornes à l'écran, et programmes des fenêtres
                                                     d'autres processus qu'elles contiennent (WebView2 :
                                                     msedgewebview2.exe ; visionneuse Office : un autre)
  python tools/interface_web/win.py front            met My_AI au premier plan
  python tools/interface_web/win.py shot FICHIER     premier plan, puis capture (barre de titre comprise)
  python tools/interface_web/win.py capture FICHIER  capture sans premier plan ni saisie (PrintWindow),
                                                     lecteur PDF compris (absent des captures CDP)
  python tools/interface_web/win.py keys TOUCHE...   premier plan, puis touches (ex. f5 ctrl+r ctrl+b esc)
  python tools/interface_web/win.py cursor X Y       déplace le vrai curseur
  python tools/interface_web/win.py dialog [CHEMIN | --annuler]
                                                     dialogue de fichiers ou de dossier ouvert par
                                                     My_AI : titre et types ; avec CHEMIN, l'écrit
                                                     dans le nom et valide (messages adressés au
                                                     dialogue, ni focus ni saisie du système)
  python tools/interface_web/win.py drag X1 Y1 X2 Y2 glisser-déposer à la vraie souris (écran)
  python tools/interface_web/win.py element TITRE NOM
                                                     centre à l'écran de l'élément NOM (UI Automation)
                                                     dans la fenêtre dont le titre contient TITRE ;
                                                     NOM sans extension aussi (Explorateur)

Les touches et le curseur du système vont à la fenêtre au premier plan, pas à
celle qu'on vise. front, shot, keys, cursor et drag attendent donc que le clavier
et la souris n'aient pas servi depuis IDLE_S secondes (WAIT_S secondes au plus,
sinon refus, code de sortie 2), et keys n'envoie chaque touche que si My_AI est
au premier plan. rect, origin, state, screen, capture, close, windows, children,
dialog et element ne touchent ni au focus ni aux saisies ; move restaure la fenêtre, ce qui peut
l'activer.
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


GW_OWNER = 4
WM_SETTEXT = 0x000C
WM_GETTEXT = 0x000D
WM_COMMAND = 0x0111
WM_CHAR, EM_SETSEL = 0x0102, 0x00B1
IDOK, IDCANCEL = 1, 2
MOUSEEVENTF_MOVE, MOUSEEVENTF_LEFTDOWN, MOUSEEVENTF_LEFTUP = 0x0001, 0x0002, 0x0004
MOUSEEVENTF_VIRTUALDESK, MOUSEEVENTF_ABSOLUTE = 0x4000, 0x8000
ENUM_PROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)


def class_name(hwnd):
    """Classe Win32 d'une fenêtre."""
    name = ctypes.create_unicode_buffer(64)
    user32.GetClassNameW(hwnd, name, 64)
    return name.value


def window_text(hwnd):
    """Texte d'une fenêtre, même d'un autre processus (WM_GETTEXT, recopié par Windows)."""
    text = ctypes.create_unicode_buffer(512)
    user32.SendMessageW(hwnd, WM_GETTEXT, 512, text)
    return text.value


def file_dialog(owner, timeout=10.0):
    """Dialogue de fichiers ou de dossier (#32770) ouvert par My_AI, ou None."""
    deadline = time.monotonic() + timeout
    while True:
        found = []

        @ENUM_PROC
        def collect(hwnd, _param):
            if class_name(hwnd) == "#32770" and user32.IsWindowVisible(hwnd) \
                    and user32.GetWindow(hwnd, GW_OWNER) == owner:
                found.append(hwnd)
            return True

        user32.EnumWindows(collect, 0)
        if found or time.monotonic() >= deadline:
            return found[0] if found else None
        time.sleep(0.2)


def dialog_controls(dialog):
    """Contrôles visibles du dialogue : [(hwnd, classe, identifiant)], tous niveaux."""
    found = []

    @ENUM_PROC
    def collect(hwnd, _param):
        if user32.IsWindowVisible(hwnd):
            found.append((hwnd, class_name(hwnd), user32.GetDlgCtrlID(hwnd)))
        return True

    user32.EnumChildWindows(dialog, collect, 0)
    return found


def dialog_name_box(dialog):
    """Zone « Nom du fichier » (ou « Dossier ») du dialogue.

    Ouvrir : saisie de la ComboBoxEx32 n° 1148 ; Enregistrer : de la ComboBox
    n° 1001 ; choix d'un dossier : saisie n° 1152 (Enregistrer en a une aussi,
    qui n'est pas la bonne : elle vient après) ; sinon la première saisie
    visible d'une liste déroulante.
    """
    controls = dialog_controls(dialog)
    edits = [hwnd for hwnd, name, _ident in controls if name == "Edit"]
    for wanted in (1148, 1001):
        for hwnd in edits:
            parent = user32.GetParent(hwnd)
            if any(user32.GetDlgCtrlID(a) == wanted for a in (parent, user32.GetParent(parent))):
                return hwnd
    for hwnd in edits:
        if user32.GetDlgCtrlID(hwnd) == 1152:
            return hwnd
    for hwnd in edits:
        if class_name(user32.GetParent(hwnd)) == "ComboBox":
            return hwnd
    return None


def type_into(box, text):
    """Remplace le texte d'une zone de saisie, caractère par caractère (WM_CHAR).

    Message adressé à la zone seule, pas une saisie du système. WM_SETTEXT ne
    suffit pas : « Enregistrer sous » garde alors son nom proposé.
    """
    user32.SendMessageW(box, EM_SETSEL, 0, -1)
    for char in text:
        user32.SendMessageW(box, WM_CHAR, ord(char), 0)


def dialog_address(dialog):
    """Dossier affiché par le dialogue : texte de sa barre d'adresse (« Adresse : … »)."""
    for hwnd, name, ident in dialog_controls(dialog):
        if name == "ToolbarWindow32" and ident == 1001:
            return window_text(hwnd)
    return ""


def dialog_info(dialog):
    """Titre du dialogue et types de fichiers proposés (liste déroulante des filtres)."""
    filters = [window_text(hwnd) for hwnd, name, _ident in dialog_controls(dialog)
               if name == "ComboBox" and "(" in window_text(hwnd)]
    title = ctypes.create_unicode_buffer(256)
    user32.GetWindowTextW(dialog, title, 256)
    return {"titre": title.value, "types": filters}


def mouse_to(x, y):
    """Déplace le vrai curseur par un événement de souris (bureau virtuel entier)."""
    left, top, width, height = (user32.GetSystemMetrics(index) for index in (76, 77, 78, 79))
    dx = round((x - left) * 65535 / max(width - 1, 1))
    dy = round((y - top) * 65535 / max(height - 1, 1))
    user32.mouse_event(MOUSEEVENTF_MOVE | MOUSEEVENTF_ABSOLUTE | MOUSEEVENTF_VIRTUALDESK,
                       dx, dy, 0, 0)


def drag(start, end, steps=30):
    """Glisser-déposer à la vraie souris, de `start` à `end` (coordonnées d'écran)."""
    mouse_to(*start)
    time.sleep(0.3)
    user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
    time.sleep(0.3)
    for step in range(1, steps + 1):
        mouse_to(round(start[0] + (end[0] - start[0]) * step / steps),
                 round(start[1] + (end[1] - start[1]) * step / steps))
        time.sleep(0.03)
    # Survol de la cible avant le dépôt : la page reçoit dragover
    time.sleep(0.6)
    user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
    note_own_input()


def program(pid):
    """Nom du programme d'un processus (« msedgewebview2.exe »), ou son numéro."""
    process = kernel32.OpenProcess(0x1000, False, pid)  # PROCESS_QUERY_LIMITED_INFORMATION
    if not process:
        return str(pid)
    try:
        size = wintypes.DWORD(1024)
        buffer = ctypes.create_unicode_buffer(size.value)
        if kernel32.QueryFullProcessImageNameW(process, 0, buffer, ctypes.byref(size)):
            return Path(buffer.value).name
        return str(pid)
    finally:
        kernel32.CloseHandle(process)


def children(parent):
    """Enfants directs : {hwnd, classe, visible, bornes, programmes des descendants}."""
    own = wintypes.DWORD()
    user32.GetWindowThreadProcessId(parent, ctypes.byref(own))
    found = []

    @ENUM_PROC
    def collect(hwnd, _param):
        if user32.GetParent(hwnd) == parent:
            processes = set()

            @ENUM_PROC
            def inner(child, _param):
                process = wintypes.DWORD()
                user32.GetWindowThreadProcessId(child, ctypes.byref(process))
                processes.add(process.value)
                return True

            user32.EnumChildWindows(hwnd, inner, 0)
            found.append({"hwnd": hwnd, "class": class_name(hwnd),
                          "visible": bool(user32.IsWindowVisible(hwnd)), "rect": rect(hwnd),
                          "foreign": sorted({program(pid) for pid in processes - {own.value}})})
        return True

    user32.EnumChildWindows(parent, collect, 0)
    return found


def visible_windows(wanted_class=None):
    """Fenêtres visibles et titrées : [hwnd, classe, processus, titre]."""
    found = []

    @ENUM_PROC
    def collect(hwnd, _param):
        title = ctypes.create_unicode_buffer(512)
        user32.GetWindowTextW(hwnd, title, 512)
        name = class_name(hwnd)
        if user32.IsWindowVisible(hwnd) and title.value and wanted_class in (None, name):
            process = wintypes.DWORD()
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(process))
            found.append([hwnd, name, process.value, title.value])
        return True

    user32.EnumWindows(collect, 0)
    return found


def element_center(title_part, name):
    """Centre à l'écran de l'élément `name` (UI Automation) d'une fenêtre, ou None.

    La fenêtre est la première visible dont le titre contient `title_part`.
    L'Explorateur masque souvent les extensions : le nom sans extension est
    essayé ensuite.
    """
    import comtypes.client  # pylint: disable=import-outside-toplevel
    comtypes.client.GetModule("UIAutomationCore.dll")
    from comtypes.gen import UIAutomationClient as uia  # pylint: disable=import-outside-toplevel,import-error,no-name-in-module
    windows = []

    @ENUM_PROC
    def collect(hwnd, _param):
        title = ctypes.create_unicode_buffer(512)
        user32.GetWindowTextW(hwnd, title, 512)
        if user32.IsWindowVisible(hwnd) and title_part in title.value:
            windows.append(hwnd)
        return True

    user32.EnumWindows(collect, 0)
    if not windows:
        return None
    automation = comtypes.client.CreateObject(uia.CUIAutomation, interface=uia.IUIAutomation)
    root = automation.ElementFromHandle(windows[0])
    for candidate in dict.fromkeys((name, Path(name).stem)):
        condition = automation.CreatePropertyCondition(uia.UIA_NamePropertyId, candidate)
        element = root.FindFirst(uia.TreeScope_Descendants, condition)
        if element:
            box = element.CurrentBoundingRectangle
            return [(box.left + box.right) // 2, (box.top + box.bottom) // 2]
    return None


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


def main():  # pylint: disable=too-many-branches,too-many-statements,too-many-locals
    """Action demandée sur la ligne de commande."""
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    action = sys.argv[1]
    # Ces trois actions se passent de la fenêtre My_AI
    hwnd = None if action in ("screen", "windows", "element") else find()
    if action == "rect":
        print(json.dumps(rect(hwnd)))
    elif action == "origin":
        # WebView2 remplit la zone client (la visionneuse Office se pose par-dessus)
        point = wintypes.POINT(0, 0)
        user32.ClientToScreen(hwnd, ctypes.byref(point))
        print(json.dumps([point.x, point.y]))
    elif action == "state":
        print("agrandie" if user32.IsZoomed(hwnd) else "réduite" if user32.IsIconic(hwnd) else "normale")
    elif action == "screen":
        # SM_XVIRTUALSCREEN, SM_YVIRTUALSCREEN, SM_CXVIRTUALSCREEN, SM_CYVIRTUALSCREEN
        print(json.dumps([user32.GetSystemMetrics(index) for index in (76, 77, 78, 79)]))
    elif action == "move":
        x, y, w, h = map(int, sys.argv[2:6])
        target = int(sys.argv[6]) if len(sys.argv) > 6 else hwnd
        user32.ShowWindow(target, 9)  # SW_RESTORE
        user32.MoveWindow(target, x, y, w, h, True)
        time.sleep(0.5)
        print(json.dumps(rect(target)))
    elif action == "close":
        target = int(sys.argv[2]) if len(sys.argv) > 2 else hwnd
        user32.PostMessageW(target, 0x0010, 0, 0)  # WM_CLOSE
        print("WM_CLOSE envoyé")
    elif action == "windows":
        print(json.dumps(visible_windows(sys.argv[2] if len(sys.argv) > 2 else None),
                         ensure_ascii=False))
    elif action == "children":
        print(json.dumps(children(hwnd), ensure_ascii=False))
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
    elif action == "dialog":
        dialog = file_dialog(hwnd)
        if not dialog:
            sys.exit("aucun dialogue de fichiers ouvert par My_AI")
        print(json.dumps(dialog_info(dialog), ensure_ascii=False))
        if len(sys.argv) > 2 and sys.argv[2] == "--annuler":
            user32.PostMessageW(dialog, WM_COMMAND, IDCANCEL, 0)
            print("annulé")
        elif len(sys.argv) > 2:
            box = dialog_name_box(dialog)
            if not box:
                sys.exit("zone du nom introuvable")
            type_into(box, sys.argv[2])
            time.sleep(0.2)
            user32.PostMessageW(dialog, WM_COMMAND, IDOK, user32.GetDlgItem(dialog, IDOK))
            # Choix d'un dossier : un chemin complet ne fait qu'y mener. Une fois
            # la barre d'adresse arrivée, la zone vidée et un second clic
            # choisissent le dossier affiché
            target = sys.argv[2].rstrip("\\").lower()
            deadline = time.monotonic() + 8
            while user32.IsWindow(dialog) and user32.IsWindowVisible(dialog)                     and time.monotonic() < deadline:
                if dialog_address(dialog).rstrip("\\").lower().endswith(target):
                    user32.SendMessageW(box, WM_SETTEXT, 0, ctypes.c_wchar_p(""))
                    time.sleep(0.2)
                    user32.PostMessageW(dialog, WM_COMMAND, IDOK, user32.GetDlgItem(dialog, IDOK))
                    break
                time.sleep(0.2)
            print("validé", sys.argv[2])
    elif action == "drag":
        x1, y1, x2, y2 = map(int, sys.argv[2:6])
        require_idle()
        drag((x1, y1), (x2, y2))
        print("déposé", [x1, y1], "→", [x2, y2])
    elif action == "element":
        print(json.dumps(element_center(sys.argv[2], sys.argv[3])))
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()
