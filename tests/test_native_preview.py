"""
Tests de l'hôte DPI (interfaces/desktop/dpi_host.py, par son relais Tk) et des visionneuses natives
(interfaces/desktop/preview_handler.py).

Régression d'un bug observé sur un écran à 125 % : l'appli ne gère pas le DPI
(racine TkinterDnD), et une fenêtre étrangère ré-parentée dans l'un de ses
widgets perdait son propre contexte DPI — contenu décalé, rogné, parfois une
zone blanche. L'hôte, lui, est DPI par écran : les fenêtres qu'il accueille
gardent le leur.

Windows uniquement ; les tests de visionneuse lancent un vrai Word ou Excel et
sont ignorés si Office n'est pas installé.
"""

import ctypes
import sys
import threading
import time
from ctypes import wintypes

import pytest

pytestmark = pytest.mark.skipif(not sys.platform.startswith("win"), reason="Windows uniquement")

from interfaces.desktop import preview_handler as _preview_handler  # noqa: E402
from interfaces.desktop.preview_handler import (  # noqa: E402
    AsyncNativePreview,
    NativePreview,
    handler_clsid,
    supports_native_preview,
)
from interfaces.gui._dpi_host import DpiAwareHost, is_dpi_virtualized  # noqa: E402
from interfaces.desktop.dpi_host import client_origin, screen_rect  # noqa: E402
from interfaces.desktop.native_viewer import (  # noqa: E402
    PopupHost,
    close_office,
    hosted_processes,
    launched_office,
)

# Début de ce module : un Word caché lancé par ses tests « l'a été par l'appli »
_MODULE_STARTED = time.time()

_PER_MONITOR = 2


def _user32():
    user32 = ctypes.WinDLL("user32")
    user32.GetWindowDpiAwarenessContext.restype = ctypes.c_void_p
    user32.GetAwarenessFromDpiAwarenessContext.argtypes = [ctypes.c_void_p]
    user32.SetThreadDpiAwarenessContext.restype = ctypes.c_void_p
    user32.SetThreadDpiAwarenessContext.argtypes = [ctypes.c_void_p]
    return user32


def _physical_rect(hwnd):
    user32 = _user32()
    previous = user32.SetThreadDpiAwarenessContext(ctypes.c_void_p(-4))
    try:
        rect = wintypes.RECT()
        user32.GetWindowRect(hwnd, ctypes.byref(rect))
        return rect.left, rect.top, rect.right, rect.bottom
    finally:
        user32.SetThreadDpiAwarenessContext(ctypes.c_void_p(previous))


def _children(hwnd):
    user32 = _user32()
    found = []
    callback = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

    def _collect(child, _lparam):
        if user32.GetParent(child) == hwnd:
            found.append(child)
        return True

    user32.EnumChildWindows(hwnd, callback(_collect), 0)
    return found


@pytest.fixture(name="tk_root", scope="module")
def _tk_root():
    tk = pytest.importorskip("tkinter")
    try:
        root = tk.Tk()  # comme l'appli : racine Tk simple, sans prise en charge du DPI
    except tk.TclError:
        pytest.skip("pas d'affichage disponible")
    root.geometry("800x500+30+30")
    yield root
    root.destroy()


@pytest.fixture(name="frame")
def _frame(tk_root):
    import tkinter as tk

    frame = tk.Frame(tk_root, bg="#111111")
    frame.place(relx=0.4, rely=0.1, relwidth=0.5, relheight=0.8)
    tk_root.update()
    yield frame
    frame.destroy()


# ── Hôte DPI ───────────────────────────────────────────────────────────────


def test_host_is_per_monitor_aware(frame):
    host = DpiAwareHost(frame)
    try:
        assert host.alive
        user32 = _user32()
        awareness = user32.GetAwarenessFromDpiAwarenessContext(
            user32.GetWindowDpiAwarenessContext(host.hwnd)
        )
        assert awareness == _PER_MONITOR, "l'hôte doit gérer le DPI par écran"
    finally:
        host.destroy()


def test_host_covers_the_widget_exactly(frame):
    host = DpiAwareHost(frame)
    try:
        host.place_over(frame)
        assert host.visible
        assert _physical_rect(host.hwnd) == _physical_rect(int(frame.winfo_id()))
    finally:
        host.destroy()


def test_host_can_be_sized_without_being_shown(frame):
    """Le temps qu'une visionneuse se prépare, l'hôte est dimensionné mais masqué."""
    host = DpiAwareHost(frame)
    try:
        host.place_over(frame, show=False)
        assert not host.visible
        assert _physical_rect(host.hwnd) == _physical_rect(int(frame.winfo_id()))
    finally:
        host.destroy()


def test_host_hide_and_destroy(frame):
    host = DpiAwareHost(frame)
    host.place_over(frame)
    host.hide()
    assert not host.visible
    host.destroy()
    assert not host.alive
    host.destroy()  # idempotent


def test_plain_tk_window_is_dpi_virtualized(frame):
    """La racine de l'appli ne gère pas le DPI : c'est ce qui impose l'hôte."""
    assert is_dpi_virtualized(frame) is True


# ── Repli de l'interface web : hôte popup posé sur un rectangle ─────────────


class _TkWindow:
    """FormWindow simulée sur la racine Tk : fil courant, déplacement signalé à la main."""

    background = "#111111"

    def __init__(self, root):
        self.root = root
        self.moved = None

    @staticmethod
    def invoke(action):
        return action()

    def hwnd(self):
        return int(self.root.wm_frame(), 16)

    def on_move(self, callback):
        self.moved = callback


def test_popup_host_sits_on_the_place_and_follows_the_window(tk_root):
    """Fenêtre sans DPI par écran (racine Tk) : l'hôte popup se pose et suit."""
    window = _TkWindow(tk_root)
    host = PopupHost(window)
    try:
        host.place((40, 30, 300, 200), True)
        inner = host._host  # pylint: disable=protected-access
        x, y = client_origin(window.hwnd())
        assert inner.visible and screen_rect(inner.hwnd) == (x + 40, y + 30, 300, 200)
        assert host.handle() == inner.hwnd

        tk_root.geometry("+90+110")
        tk_root.update()
        window.moved()
        moved_x, moved_y = client_origin(window.hwnd())
        assert (moved_x, moved_y) != (x, y)
        assert screen_rect(inner.hwnd)[:2] == (moved_x + 40, moved_y + 30)

        host.hide()
        assert not inner.visible
    finally:
        if host._host is not None:  # pylint: disable=protected-access
            host._host.destroy()  # pylint: disable=protected-access
        tk_root.geometry("800x500+30+30")
        tk_root.update()


# ── Visionneuses : sélection ───────────────────────────────────────────────


@pytest.mark.parametrize("name", ["a.pdf", "a.md", "a.html", "a.csv", "a.txt"])
def test_non_office_formats_are_not_native(name, tmp_path):
    path = tmp_path / name
    path.write_text("x", encoding="utf-8")
    assert supports_native_preview(str(path)) is False


def test_office_handlers_are_found_when_installed():
    clsid = handler_clsid("x.docx")
    if clsid is None:
        pytest.skip("visionneuse Word non enregistrée")
    assert clsid.startswith("{") and clsid.endswith("}")


# ── Visionneuses : intégration (vrai Office) ───────────────────────────────


def _office_document(tmp_path, fmt):
    from generators.document_generator import DocumentGenerator
    from generators.markdown_document import parse_markdown

    path = tmp_path / f"apercu.{fmt}"
    DocumentGenerator(llm=False).build(
        parse_markdown("## Titre\n\nTexte.\n\n| A | B |\n|---|---|\n| 1 | 2 |"), fmt, "Test", path
    )
    return str(path)


@pytest.mark.parametrize("fmt", ["docx", "xlsx"])
def test_native_preview_renders_inside_the_host(frame, tmp_path, fmt):
    document = _office_document(tmp_path, fmt)
    if not supports_native_preview(document):
        pytest.skip(f"visionneuse {fmt} indisponible")

    host = DpiAwareHost(frame)
    preview = NativePreview()
    try:
        host.place_over(frame)
        assert preview.open(document, host.hwnd) is True
        children = _children(host.hwnd)
        assert children, "la visionneuse doit dessiner DANS l'hôte"
        user32 = _user32()
        for child in children:
            awareness = user32.GetAwarenessFromDpiAwarenessContext(
                user32.GetWindowDpiAwarenessContext(child)
            )
            assert awareness == _PER_MONITOR, "la visionneuse doit garder son DPI"
    finally:
        preview.close()
        host.destroy()


def test_native_preview_rejects_a_missing_file(frame):
    host = DpiAwareHost(frame)
    try:
        assert NativePreview().open("C:/nulle/part/absent.docx", host.hwnd) is False
    finally:
        host.destroy()


def test_async_preview_reports_failure_without_blocking(frame, tk_root):
    host = DpiAwareHost(frame)
    preview = AsyncNativePreview()
    results = []
    done = threading.Event()
    try:
        started = time.time()
        preview.open("C:/nulle/part/absent.xlsx", host.hwnd,
                      lambda ok: (results.append(ok), done.set()))
        assert time.time() - started < 0.5, "open() ne doit jamais bloquer l'appelant"
        assert done.wait(10), "le résultat doit être rapporté"
        assert results == [False]
    finally:
        preview.close(wait=5)
        host.destroy()


def test_async_close_without_open_is_harmless():
    AsyncNativePreview().close(wait=1)


def test_comtypes_absence_disables_native_preview(monkeypatch, tmp_path):
    monkeypatch.setattr(_preview_handler, "COMTYPES_AVAILABLE", False)
    path = tmp_path / "x.docx"
    path.write_bytes(b"x")
    assert supports_native_preview(str(path)) is False
    assert NativePreview().open(str(path), 1) is False


def test_hidden_word_launched_for_a_preview_closes_with_the_app(frame, tmp_path):
    """D30 : à la fermeture de l'appli, le Word caché lancé pour ses aperçus est fermé.

    Ferme aussi celui des tests de ce module : ils n'en laissent plus derrière eux.
    """
    import psutil  # pylint: disable=import-outside-toplevel

    document = _office_document(tmp_path, "docx")
    if not supports_native_preview(document):
        pytest.skip("visionneuse docx indisponible")
    host = DpiAwareHost(frame)
    preview = NativePreview()
    try:
        host.place_over(frame)
        assert preview.open(document, host.hwnd) is True
        hosts = hosted_processes(host.hwnd)
    finally:
        preview.close()
        host.destroy()
    word = launched_office(hosts, _MODULE_STARTED)
    if not word:
        pytest.skip("Word déjà lancé avant ces tests : laissé tel quel")
    closed = close_office(word)
    assert closed and not any(psutil.pid_exists(pid) for pid in closed)
