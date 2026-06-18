"""Embarquement d'une fenêtre Microsoft Edge (mode --app) dans un widget Tk.

Windows uniquement. Lance Edge en mode application (Chromium, rendu EXACT,
aucune dépendance Python supplémentaire) sur un fichier HTML local, puis
ré-parente sa fenêtre top-level dans un widget Tkinter via l'API Win32
``SetParent`` pour donner l'illusion d'un volet embarqué.

Pour masquer la barre de titre dessinée par Edge en mode --app (qui n'est pas
un caption Win32 standard), la fenêtre est décalée vers le haut de la hauteur
de cette barre puis agrandie d'autant : seule la zone de contenu reste visible
dans le volet. Les coins arrondis Win11 sont désactivés (DWM) pour éviter les
bords blancs.

Robustesse : toute opération échoue silencieusement (False/None) ; l'appelant
retombe alors sur un autre mode de rendu. L'attachement est **non bloquant** :
on lance Edge puis on sonde l'apparition de sa fenêtre via ``poll_attach``.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Optional

IS_WINDOWS = sys.platform.startswith("win")

# Classe de fenêtre des navigateurs Chromium/Edge.
_CHROME_WND_CLASS = "Chrome_WidgetWin_1"

# Constantes Win32
_GWL_STYLE = -16
_WS_CHILD = 0x40000000
_WS_POPUP = 0x80000000
_WS_CAPTION = 0x00C00000
_WS_THICKFRAME = 0x00040000
_WS_VISIBLE = 0x10000000
_SW_SHOW = 5

# Hauteur (en px @96dpi) de la barre de titre Edge --app à masquer, et marge
# latérale/bas pour rogner les éventuels bords.
_TITLEBAR_BASE = 34
_BORDER_BASE = 1

# DWM : désactiver les coins arrondis (Win11).
_DWMWA_WINDOW_CORNER_PREFERENCE = 33
_DWMWCP_DONOTROUND = 1


def find_edge() -> Optional[str]:
    """Retourne le chemin de msedge.exe, ou None s'il est introuvable."""
    if not IS_WINDOWS:
        return None
    candidates = [
        Path(os.environ.get("PROGRAMFILES(X86)", r"C:\Program Files (x86)"))
        / "Microsoft" / "Edge" / "Application" / "msedge.exe",
        Path(os.environ.get("PROGRAMFILES", r"C:\Program Files"))
        / "Microsoft" / "Edge" / "Application" / "msedge.exe",
    ]
    for c in candidates:
        if c.exists():
            return str(c)
    return shutil.which("msedge")


def _load_win32():
    """Charge ctypes/user32 ; retourne le tuple d'helpers ou des None."""
    try:
        import ctypes
        from ctypes import wintypes

        user32 = ctypes.WinDLL("user32", use_last_error=True)
        EnumWindowsProc = ctypes.WINFUNCTYPE(
            wintypes.BOOL, wintypes.HWND, wintypes.LPARAM
        )
        return user32, EnumWindowsProc, ctypes, wintypes
    except Exception:
        return None, None, None, None


def _list_chrome_windows(user32, EnumWindowsProc, ctypes) -> set:
    """Énumère les HWND top-level visibles de classe Chromium."""
    hwnds = set()
    buf = ctypes.create_unicode_buffer(256)

    def _cb(hwnd, _lparam):
        try:
            if not user32.IsWindowVisible(hwnd):
                return True
            user32.GetClassNameW(hwnd, buf, 256)
            if buf.value == _CHROME_WND_CLASS:
                hwnds.add(hwnd)
        except Exception:
            pass
        return True

    try:
        user32.EnumWindows(EnumWindowsProc(_cb), 0)
    except Exception:
        pass
    return hwnds


class EdgeEmbed:
    """Gère le cycle de vie d'une fenêtre Edge embarquée dans un widget Tk."""

    def __init__(self):
        self._proc: Optional[subprocess.Popen] = None
        self._hwnd = None
        self._profile_dir: Optional[str] = None
        self._win32 = _load_win32()
        self._before: set = set()
        self._parent_hwnd: Optional[int] = None
        self._deadline = 0.0

    @property
    def available(self) -> bool:
        return IS_WINDOWS and find_edge() is not None and self._win32[0] is not None

    @property
    def attached(self) -> bool:
        return self._hwnd is not None

    # ── Lancement non bloquant ────────────────────────────────────────────

    def start(self, file_path: str, parent_widget, width: int, height: int) -> bool:
        """Lance Edge --app ; l'attachement se fait ensuite via poll_attach()."""
        if not self.available:
            return False
        self.close()

        user32, EnumWindowsProc, ctypes, _ = self._win32
        try:
            self._parent_hwnd = int(parent_widget.winfo_id())
        except Exception:
            return False

        self._before = _list_chrome_windows(user32, EnumWindowsProc, ctypes)
        self._profile_dir = tempfile.mkdtemp(prefix="myai_edge_")
        file_url = Path(file_path).as_uri()
        try:
            self._proc = subprocess.Popen(
                [
                    find_edge(),
                    f"--app={file_url}",
                    f"--user-data-dir={self._profile_dir}",
                    "--no-first-run",
                    "--no-default-browser-check",
                    "--disable-sync",
                    "--disable-features=Translate,EdgeCollections",
                    f"--window-size={max(width, 100)},{max(height, 100)}",
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except Exception:
            self._cleanup_profile()
            return False

        self._deadline = time.time() + 8.0
        return True

    def poll_attach(self, width: int, height: int) -> Optional[bool]:
        """Sonde l'apparition de la fenêtre Edge et la ré-parente.

        Retourne True (attaché), False (toujours en attente), None (échec/timeout).
        Non bloquant : à appeler périodiquement via ``root.after``.
        """
        if self._hwnd is not None:
            return True
        if self._proc is None:
            return None
        if time.time() > self._deadline:
            self.close()
            return None

        user32, EnumWindowsProc, ctypes, _ = self._win32
        diff = _list_chrome_windows(user32, EnumWindowsProc, ctypes) - self._before
        if not diff:
            return False

        hwnd = next(iter(diff))
        try:
            style = user32.GetWindowLongW(hwnd, _GWL_STYLE)
            style = (style & ~_WS_POPUP & ~_WS_CAPTION & ~_WS_THICKFRAME) | _WS_CHILD | _WS_VISIBLE
            user32.SetWindowLongW(hwnd, _GWL_STYLE, style)
            user32.SetParent(hwnd, self._parent_hwnd)
            self._hwnd = hwnd
            self._disable_rounded_corners(hwnd)
            self._place(width, height)
            user32.ShowWindow(hwnd, _SW_SHOW)
            return True
        except Exception:
            self.close()
            return None

    # ── Géométrie ─────────────────────────────────────────────────────────

    def _dpi_scale(self) -> float:
        try:
            dpi = self._win32[0].GetDpiForWindow(self._hwnd)
            if dpi:
                return dpi / 96.0
        except Exception:
            pass
        return 1.0

    def _place(self, width: int, height: int) -> None:
        """Positionne la fenêtre en masquant la barre de titre Edge (offset haut)."""
        if self._hwnd is None:
            return
        scale = self._dpi_scale()
        top = int(round(_TITLEBAR_BASE * scale))
        border = int(round(_BORDER_BASE * scale))
        try:
            # Décalage vers le haut de `top` (barre de titre hors zone visible)
            # + agrandissement pour que le contenu remplisse le volet, et léger
            # rognage latéral/bas pour éviter les bords blancs.
            self._win32[0].MoveWindow(
                self._hwnd,
                -border,
                -top,
                max(width, 1) + 2 * border,
                max(height, 1) + top + border,
                True,
            )
        except Exception:
            pass

    def resize(self, width: int, height: int) -> None:
        """Redimensionne la fenêtre embarquée pour épouser son parent."""
        self._place(width, height)

    def _disable_rounded_corners(self, hwnd) -> None:
        """Désactive les coins arrondis Win11 pour éviter les bords blancs."""
        try:
            import ctypes

            dwm = ctypes.WinDLL("dwmapi")
            pref = ctypes.c_int(_DWMWCP_DONOTROUND)
            dwm.DwmSetWindowAttribute(
                ctypes.c_void_p(hwnd),
                ctypes.c_int(_DWMWA_WINDOW_CORNER_PREFERENCE),
                ctypes.byref(pref),
                ctypes.sizeof(pref),
            )
        except Exception:
            pass

    # ── Cycle de vie ──────────────────────────────────────────────────────

    def close(self) -> None:
        """Ferme la fenêtre Edge et nettoie le profil temporaire."""
        self._hwnd = None
        self._before = set()
        if self._proc is not None:
            try:
                self._proc.terminate()
                try:
                    self._proc.wait(timeout=2)
                except Exception:
                    self._proc.kill()
            except Exception:
                pass
            self._proc = None
        self._cleanup_profile()

    def _cleanup_profile(self) -> None:
        if self._profile_dir:
            shutil.rmtree(self._profile_dir, ignore_errors=True)
            self._profile_dir = None
