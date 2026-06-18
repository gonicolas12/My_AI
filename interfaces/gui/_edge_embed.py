"""Embarquement d'une fenêtre Microsoft Edge (mode --app) dans un widget Tk.

Windows uniquement. Lance Edge en mode application (Chromium, rendu EXACT,
aucune dépendance Python supplémentaire) sur un fichier HTML local, puis
ré-parente sa fenêtre top-level dans un widget Tkinter via l'API Win32
``SetParent`` pour donner l'illusion d'un volet embarqué.

Robustesse : toute opération échoue silencieusement (retourne False / None) ;
l'appelant retombe alors sur un autre mode de rendu.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import List, Optional

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
    found = shutil.which("msedge")
    return found


def _load_win32():
    """Charge ctypes/user32 ; retourne (user32, EnumWindowsProc) ou (None, None)."""
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


def _list_chrome_windows(user32, EnumWindowsProc, ctypes, wintypes) -> set:
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

    @property
    def available(self) -> bool:
        return IS_WINDOWS and find_edge() is not None and self._win32[0] is not None

    def embed(self, file_path: str, parent_widget, width: int, height: int) -> bool:
        """Lance Edge sur file_path et ré-parente sa fenêtre dans parent_widget.

        Retourne True si l'embarquement a réussi.
        """
        if not self.available:
            return False
        self.close()  # nettoyer une éventuelle instance précédente

        edge = find_edge()
        user32, EnumWindowsProc, ctypes, wintypes = self._win32

        try:
            parent_hwnd = int(parent_widget.winfo_id())
        except Exception:
            return False

        before = _list_chrome_windows(user32, EnumWindowsProc, ctypes, wintypes)

        # Profil dédié → garantit une NOUVELLE fenêtre identifiable.
        self._profile_dir = tempfile.mkdtemp(prefix="myai_edge_")
        file_url = Path(file_path).as_uri()
        try:
            self._proc = subprocess.Popen(
                [
                    edge,
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

        # Attendre l'apparition d'une NOUVELLE fenêtre Chromium (max ~8s).
        new_hwnd = None
        deadline = time.time() + 8.0
        while time.time() < deadline:
            after = _list_chrome_windows(user32, EnumWindowsProc, ctypes, wintypes)
            diff = after - before
            if diff:
                new_hwnd = next(iter(diff))
                break
            time.sleep(0.12)

        if new_hwnd is None:
            self.close()
            return False

        # Ré-parentage : transformer la fenêtre top-level en enfant sans bordure.
        try:
            style = user32.GetWindowLongW(new_hwnd, _GWL_STYLE)
            style = (style & ~_WS_POPUP & ~_WS_CAPTION & ~_WS_THICKFRAME) | _WS_CHILD | _WS_VISIBLE
            user32.SetWindowLongW(new_hwnd, _GWL_STYLE, style)
            user32.SetParent(new_hwnd, parent_hwnd)
            user32.MoveWindow(new_hwnd, 0, 0, max(width, 1), max(height, 1), True)
            user32.ShowWindow(new_hwnd, _SW_SHOW)
            self._hwnd = new_hwnd
            return True
        except Exception:
            self.close()
            return False

    def resize(self, width: int, height: int) -> None:
        """Redimensionne la fenêtre embarquée pour épouser son parent."""
        if self._hwnd is None or self._win32[0] is None:
            return
        try:
            self._win32[0].MoveWindow(
                self._hwnd, 0, 0, max(width, 1), max(height, 1), True
            )
        except Exception:
            pass

    def close(self) -> None:
        """Ferme la fenêtre Edge et nettoie le profil temporaire."""
        self._hwnd = None
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
