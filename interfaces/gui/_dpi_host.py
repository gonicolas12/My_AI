"""Fenêtre hôte « DPI par écran » posée sur un widget Tk (Windows uniquement).

L'appli tourne sans prise en charge du DPI (sa racine est un ``TkinterDnD.Tk``,
pas un ``ctk.CTk``) : sur un écran à 125 %, Windows l'agrandit en bitmap.
Ré-parenter dans l'un de ses widgets la fenêtre d'un autre processus qui, elle,
gère le DPI par écran (Edge, visionneuses Office) ne fonctionne pas : Windows
aligne l'enfant sur le régime du parent, mais le processus propriétaire
continue de dessiner à l'échelle de l'écran. Le contenu est alors mis à
l'échelle deux fois, décalé et rogné. L'hébergement DPI « mixte » de Windows
ne s'applique pas entre processus, et Chromium ignore les options qui
pourraient forcer son régime.

Cette classe contourne le problème : elle crée une fenêtre Win32 sans bordure,
**elle-même DPI par écran**, possédée par la fenêtre principale (elle la suit
à la réduction et reste au-dessus d'elle) et posée au pixel près sur le widget
hôte. La fenêtre étrangère est ré-parentée dans CET hôte, au même régime
qu'elle : son rendu redevient exact et net. L'appelant la recale à chaque
déplacement ou redimensionnement (cf. ``place_over``).
"""

from __future__ import annotations

import ctypes
import sys
from ctypes import wintypes
from typing import Optional

IS_WINDOWS = sys.platform.startswith("win")

_WS_POPUP = 0x80000000
_WS_CLIPCHILDREN = 0x02000000
_WS_EX_TOOLWINDOW = 0x00000080  # ni barre des tâches, ni Alt+Tab
_SWP_NOZORDER = 0x0004
_SWP_NOACTIVATE = 0x0010
_SWP_SHOWWINDOW = 0x0040
_SW_HIDE = 0
_ERROR_CLASS_ALREADY_EXISTS = 1410
_DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2 = -4
_DPI_AWARENESS_PER_MONITOR = 2
_CLASS_NAME = "MyAiDpiAwareHost"

if IS_WINDOWS:
    _LRESULT = ctypes.c_ssize_t
    _WNDPROC = ctypes.WINFUNCTYPE(
        _LRESULT, wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM
    )

    class _WNDCLASSEXW(ctypes.Structure):
        _fields_ = [
            ("cbSize", wintypes.UINT),
            ("style", wintypes.UINT),
            ("lpfnWndProc", _WNDPROC),
            ("cbClsExtra", ctypes.c_int),
            ("cbWndExtra", ctypes.c_int),
            ("hInstance", wintypes.HINSTANCE),
            ("hIcon", wintypes.HICON),
            ("hCursor", wintypes.HANDLE),
            ("hbrBackground", wintypes.HBRUSH),
            ("lpszMenuName", wintypes.LPCWSTR),
            ("lpszClassName", wintypes.LPCWSTR),
            ("hIconSm", wintypes.HICON),
        ]


def _win32():
    """Charge des instances privées de user32/kernel32/gdi32, signatures typées.

    Instances privées : fixer ``argtypes`` sur ``ctypes.windll`` (partagé)
    modifierait les appels du reste de l'appli. Signatures explicites : sans
    elles, ctypes tronquerait les handles 64 bits.
    """
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    gdi32 = ctypes.WinDLL("gdi32", use_last_error=True)

    user32.DefWindowProcW.argtypes = [
        wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM
    ]
    user32.DefWindowProcW.restype = _LRESULT
    user32.RegisterClassExW.argtypes = [ctypes.POINTER(_WNDCLASSEXW)]
    user32.RegisterClassExW.restype = wintypes.ATOM
    user32.CreateWindowExW.argtypes = [
        wintypes.DWORD, wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.DWORD,
        ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
        wintypes.HWND, wintypes.HMENU, wintypes.HINSTANCE, wintypes.LPVOID,
    ]
    user32.CreateWindowExW.restype = wintypes.HWND
    user32.SetWindowPos.argtypes = [
        wintypes.HWND, wintypes.HWND, ctypes.c_int, ctypes.c_int,
        ctypes.c_int, ctypes.c_int, wintypes.UINT,
    ]
    user32.SetWindowPos.restype = wintypes.BOOL
    user32.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
    user32.GetWindowRect.restype = wintypes.BOOL
    user32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
    user32.DestroyWindow.argtypes = [wintypes.HWND]
    user32.IsWindow.argtypes = [wintypes.HWND]
    user32.IsWindowVisible.argtypes = [wintypes.HWND]
    user32.SetThreadDpiAwarenessContext.argtypes = [ctypes.c_void_p]
    user32.SetThreadDpiAwarenessContext.restype = ctypes.c_void_p
    user32.GetWindowDpiAwarenessContext.argtypes = [wintypes.HWND]
    user32.GetWindowDpiAwarenessContext.restype = ctypes.c_void_p
    user32.GetAwarenessFromDpiAwarenessContext.argtypes = [ctypes.c_void_p]
    user32.GetAwarenessFromDpiAwarenessContext.restype = ctypes.c_int
    kernel32.GetModuleHandleW.argtypes = [wintypes.LPCWSTR]
    kernel32.GetModuleHandleW.restype = wintypes.HMODULE
    gdi32.CreateSolidBrush.argtypes = [wintypes.COLORREF]
    gdi32.CreateSolidBrush.restype = wintypes.HBRUSH
    return user32, kernel32, gdi32


# La procédure de fenêtre doit survivre à l'appel : ctypes libérerait sinon
# le callback pendant que Windows l'utilise encore.
_WNDPROC_REF = None
_REGISTERED_BRUSH: Optional[int] = None


def _hex_to_colorref(color: str) -> int:
    """Convertit « #rrggbb » en COLORREF (0x00bbggrr)."""
    value = color.lstrip("#")
    try:
        red, green, blue = int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16)
    except (ValueError, IndexError):
        red = green = blue = 0x11
    return red | (green << 8) | (blue << 16)


def _ensure_class(user32, kernel32, gdi32, background: str) -> bool:
    """Enregistre (une fois) la classe de la fenêtre hôte."""
    global _WNDPROC_REF, _REGISTERED_BRUSH
    if _WNDPROC_REF is not None:
        return True

    def _proc(hwnd, msg, wparam, lparam):
        return user32.DefWindowProcW(hwnd, msg, wparam, lparam)

    wndproc = _WNDPROC(_proc)
    brush = gdi32.CreateSolidBrush(_hex_to_colorref(background))
    wndclass = _WNDCLASSEXW()
    wndclass.cbSize = ctypes.sizeof(_WNDCLASSEXW)
    wndclass.lpfnWndProc = wndproc
    wndclass.hInstance = kernel32.GetModuleHandleW(None)
    wndclass.hbrBackground = brush
    wndclass.lpszClassName = _CLASS_NAME
    if not user32.RegisterClassExW(ctypes.byref(wndclass)):
        if ctypes.get_last_error() != _ERROR_CLASS_ALREADY_EXISTS:
            return False
    _WNDPROC_REF = wndproc
    _REGISTERED_BRUSH = brush
    return True


def is_dpi_virtualized(widget) -> bool:
    """
    True si le widget vit dans une fenêtre que Windows met à l'échelle en bitmap.

    C'est le cas dès que la fenêtre n'est pas « DPI par écran » : une fenêtre
    étrangère ré-parentée dedans serait alors mal rendue sur un écran mis à
    l'échelle (cf. module).
    """
    if not IS_WINDOWS:
        return False
    try:
        user32 = _win32()[0]
        context = user32.GetWindowDpiAwarenessContext(int(widget.winfo_id()))
        return user32.GetAwarenessFromDpiAwarenessContext(context) != _DPI_AWARENESS_PER_MONITOR
    except (AttributeError, OSError):
        # Windows antérieur à 10 1607 : pas de DPI par fenêtre, rien à corriger.
        return False


class DpiAwareHost:
    """Fenêtre hôte DPI par écran, sans bordure, alignée sur un widget Tk."""

    def __init__(self, owner_widget, background: str = "#111111"):
        """
        Args:
            owner_widget: Widget de la fenêtre principale (sa racine possède
                l'hôte : l'hôte la suit à la réduction et reste au-dessus).
            background: Couleur de fond, visible le temps du chargement.
        """
        self.hwnd: Optional[int] = None
        if not IS_WINDOWS:
            return
        self._user32, kernel32, gdi32 = _win32()
        if not _ensure_class(self._user32, kernel32, gdi32, background):
            return
        try:
            owner = int(owner_widget.winfo_toplevel().wm_frame(), 16)
        except (AttributeError, ValueError):
            return

        # Création sous contexte DPI par écran : c'est ce qui rend l'hôte
        # indépendant de la mise à l'échelle bitmap de la fenêtre principale.
        previous = self._user32.SetThreadDpiAwarenessContext(
            ctypes.c_void_p(_DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2)
        )
        try:
            self.hwnd = self._user32.CreateWindowExW(
                _WS_EX_TOOLWINDOW, _CLASS_NAME, None,
                _WS_POPUP | _WS_CLIPCHILDREN,
                0, 0, 1, 1, owner, None, kernel32.GetModuleHandleW(None), None,
            ) or None
        finally:
            if previous:
                self._user32.SetThreadDpiAwarenessContext(ctypes.c_void_p(previous))

    # ── Interface « widget » attendue par EdgeEmbed.start() ────────────────

    def winfo_id(self) -> int:
        return self.hwnd or 0

    @property
    def alive(self) -> bool:
        return bool(self.hwnd) and bool(self._user32.IsWindow(self.hwnd))

    # ── Géométrie ─────────────────────────────────────────────────────────

    def place_over(self, widget, show: bool = True) -> None:
        """Aligne l'hôte, en pixels physiques, sur le rectangle écran du widget.

        Args:
            show: False pour seulement dimensionner l'hôte sans l'afficher (le
                temps qu'une visionneuse se prépare en arrière-plan).
        """
        if not self.alive:
            return
        flags = _SWP_NOZORDER | _SWP_NOACTIVATE | (_SWP_SHOWWINDOW if show else 0)
        previous = self._user32.SetThreadDpiAwarenessContext(
            ctypes.c_void_p(_DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2)
        )
        try:
            # Lu depuis un contexte DPI par écran, le rectangle d'une fenêtre
            # mise à l'échelle est converti en pixels physiques par Windows.
            rect = wintypes.RECT()
            if not self._user32.GetWindowRect(int(widget.winfo_id()), ctypes.byref(rect)):
                return
            self._user32.SetWindowPos(
                self.hwnd, None, rect.left, rect.top,
                max(rect.right - rect.left, 1), max(rect.bottom - rect.top, 1),
                flags,
            )
        finally:
            if previous:
                self._user32.SetThreadDpiAwarenessContext(ctypes.c_void_p(previous))

    @property
    def visible(self) -> bool:
        return self.alive and bool(self._user32.IsWindowVisible(self.hwnd))

    def hide(self) -> None:
        if self.alive:
            self._user32.ShowWindow(self.hwnd, _SW_HIDE)

    def destroy(self) -> None:
        """Détruit l'hôte (et donc toute fenêtre encore ré-parentée dedans)."""
        if self.alive:
            self._user32.DestroyWindow(self.hwnd)
        self.hwnd = None
