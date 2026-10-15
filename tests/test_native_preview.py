"""
Tests de l'hôte DPI (interfaces/desktop/dpi_host.py) et des visionneuses natives
(interfaces/desktop/preview_handler.py).

Régression d'un bug observé sur un écran à 125 % : une fenêtre étrangère
ré-parentée dans une fenêtre qui ne gère pas le DPI par écran perdait son
propre contexte DPI — contenu décalé, rogné, parfois une zone blanche. L'hôte,
lui, est DPI par écran : les fenêtres qu'il accueille gardent le leur.

La fenêtre de l'appli est simulée par une fenêtre Win32 ordinaire au DPI du
système, comme une fenêtre pywebview dont le processus n'a pas pu passer en
« DPI par écran » (repli de native_viewer.py). Elle s'affiche sans prendre le
premier plan, sans barre des tâches ni Alt+Tab.

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
from interfaces.desktop.dpi_host import (  # noqa: E402
    DpiAwareHost,
    client_origin,
    is_dpi_virtualized,
    screen_rect,
)
from interfaces.desktop.native_viewer import (  # noqa: E402
    PopupHost,
    close_office,
    hosted_processes,
    launched_office,
)
from interfaces.desktop.preview_handler import (  # noqa: E402
    AsyncNativePreview,
    NativePreview,
    handler_clsid,
    supports_native_preview,
)

# Début de ce module : un Word caché lancé par ses tests « l'a été par l'appli »
_MODULE_STARTED = time.time()

_PER_MONITOR = 2
_DPI_AWARENESS_CONTEXT_SYSTEM_AWARE = -2
_WS_OVERLAPPEDWINDOW = 0x00CF0000
_WS_CLIPCHILDREN = 0x02000000
_WS_EX_TOOLWINDOW = 0x00000080  # ni barre des tâches, ni Alt+Tab
_WS_EX_NOACTIVATE = 0x08000000  # jamais au premier plan
_SW_SHOWNOACTIVATE = 4
_SWP_NOSIZE = 0x0001
_SWP_NOZORDER = 0x0004
_SWP_NOACTIVATE = 0x0010
_PM_REMOVE = 0x0001


def _user32():
    user32 = ctypes.WinDLL("user32")
    user32.GetWindowDpiAwarenessContext.restype = ctypes.c_void_p
    user32.GetAwarenessFromDpiAwarenessContext.argtypes = [ctypes.c_void_p]
    user32.SetThreadDpiAwarenessContext.restype = ctypes.c_void_p
    user32.SetThreadDpiAwarenessContext.argtypes = [ctypes.c_void_p]
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
    user32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
    user32.DestroyWindow.argtypes = [wintypes.HWND]
    user32.GetParent.argtypes = [wintypes.HWND]
    user32.GetParent.restype = wintypes.HWND
    return user32


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


class _AppWindow:
    """Fenêtre de l'appli simulée, au DPI du système (FormWindow pour PopupHost).

    Fil courant (invoke appelle tout de suite) ; un déplacement est signalé à
    la main par moved(), comme le ferait l'événement Move de WinForms.
    """

    background = "#111111"

    def __init__(self):
        self._user32 = _user32()
        previous = self._user32.SetThreadDpiAwarenessContext(
            ctypes.c_void_p(_DPI_AWARENESS_CONTEXT_SYSTEM_AWARE)
        )
        try:
            self._hwnd = self._user32.CreateWindowExW(
                _WS_EX_TOOLWINDOW | _WS_EX_NOACTIVATE, "Static", "My_AI (test)",
                _WS_OVERLAPPEDWINDOW | _WS_CLIPCHILDREN, 30, 30, 800, 500,
                None, None, None, None,
            )
        finally:
            self._user32.SetThreadDpiAwarenessContext(ctypes.c_void_p(previous))
        if not self._hwnd:
            pytest.skip("pas d'affichage disponible")
        self._user32.ShowWindow(self._hwnd, _SW_SHOWNOACTIVATE)
        self.moved = None
        self.pump()

    @staticmethod
    def invoke(action):
        return action()

    def hwnd(self):
        return self._hwnd

    def on_move(self, callback):
        self.moved = callback

    def area(self):
        """Place réservée par la page dans le volet d'aperçu, en pixels de l'écran."""
        x, y = client_origin(self._hwnd)
        _left, _top, width, height = screen_rect(self._hwnd)
        return x + width * 2 // 5, y + height // 10, width // 2, height * 7 // 10

    def move_to(self, x, y):
        self._user32.SetWindowPos(self._hwnd, None, x, y, 0, 0,
                                  _SWP_NOSIZE | _SWP_NOZORDER | _SWP_NOACTIVATE)
        self.pump()

    def pump(self):
        """Messages en attente traités, comme la boucle de la fenêtre de l'appli."""
        msg = wintypes.MSG()
        while self._user32.PeekMessageW(ctypes.byref(msg), None, 0, 0, _PM_REMOVE):
            self._user32.TranslateMessage(ctypes.byref(msg))
            self._user32.DispatchMessageW(ctypes.byref(msg))

    def destroy(self):
        self._user32.DestroyWindow(self._hwnd)
        self.pump()


@pytest.fixture(name="app_window", scope="module")
def _app_window():
    window = _AppWindow()
    yield window
    window.destroy()


# ── Hôte DPI ───────────────────────────────────────────────────────────────


def test_host_is_per_monitor_aware(app_window):
    host = DpiAwareHost(app_window.hwnd())
    try:
        assert host.alive
        user32 = _user32()
        awareness = user32.GetAwarenessFromDpiAwarenessContext(
            user32.GetWindowDpiAwarenessContext(host.hwnd)
        )
        assert awareness == _PER_MONITOR, "l'hôte doit gérer le DPI par écran"
    finally:
        host.destroy()


def test_host_covers_the_place_exactly(app_window):
    host = DpiAwareHost(app_window.hwnd())
    try:
        place = app_window.area()
        host.place(place)
        assert host.visible
        assert screen_rect(host.hwnd) == place
    finally:
        host.destroy()


def test_host_can_be_sized_without_being_shown(app_window):
    """Le temps qu'une visionneuse se prépare, l'hôte est dimensionné mais masqué."""
    host = DpiAwareHost(app_window.hwnd())
    try:
        place = app_window.area()
        host.place(place, show=False)
        assert not host.visible
        assert screen_rect(host.hwnd) == place
    finally:
        host.destroy()


def test_host_hide_and_destroy(app_window):
    host = DpiAwareHost(app_window.hwnd())
    host.place(app_window.area())
    host.hide()
    assert not host.visible
    host.destroy()
    assert not host.alive
    host.destroy()  # idempotent


def test_window_without_per_monitor_dpi_is_virtualized(app_window):
    """Une fenêtre au DPI du système est mise à l'échelle en bitmap : c'est ce qui impose l'hôte."""
    assert is_dpi_virtualized(app_window.hwnd()) is True


# ── Repli de l'interface web : hôte popup posé sur un rectangle ─────────────


def test_popup_host_sits_on_the_place_and_follows_the_window(app_window):
    """Fenêtre sans DPI par écran : l'hôte popup se pose et suit."""
    host = PopupHost(app_window)
    try:
        host.place((40, 30, 300, 200), True)
        inner = host._host  # pylint: disable=protected-access
        x, y = client_origin(app_window.hwnd())
        assert inner.visible and screen_rect(inner.hwnd) == (x + 40, y + 30, 300, 200)
        assert host.handle() == inner.hwnd

        app_window.move_to(90, 110)
        app_window.moved()
        moved_x, moved_y = client_origin(app_window.hwnd())
        assert (moved_x, moved_y) != (x, y)
        assert screen_rect(inner.hwnd)[:2] == (moved_x + 40, moved_y + 30)

        host.hide()
        assert not inner.visible
    finally:
        if host._host is not None:  # pylint: disable=protected-access
            host._host.destroy()  # pylint: disable=protected-access
        app_window.move_to(30, 30)


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
def test_native_preview_renders_inside_the_host(app_window, tmp_path, fmt):
    document = _office_document(tmp_path, fmt)
    if not supports_native_preview(document):
        pytest.skip(f"visionneuse {fmt} indisponible")

    host = DpiAwareHost(app_window.hwnd())
    preview = NativePreview()
    try:
        host.place(app_window.area())
        assert preview.open(document, host.hwnd) is True
        app_window.pump()
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


def test_native_preview_rejects_a_missing_file(app_window):
    host = DpiAwareHost(app_window.hwnd())
    try:
        assert NativePreview().open("C:/nulle/part/absent.docx", host.hwnd) is False
    finally:
        host.destroy()


def test_async_preview_reports_failure_without_blocking(app_window):
    host = DpiAwareHost(app_window.hwnd())
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


def test_hidden_word_launched_for_a_preview_closes_with_the_app(app_window, tmp_path):
    """D30 : à la fermeture de l'appli, le Word caché lancé pour ses aperçus est fermé.

    Ferme aussi celui des tests de ce module : ils n'en laissent plus derrière eux.
    """
    import psutil  # pylint: disable=import-outside-toplevel

    document = _office_document(tmp_path, "docx")
    if not supports_native_preview(document):
        pytest.skip("visionneuse docx indisponible")
    host = DpiAwareHost(app_window.hwnd())
    preview = NativePreview()
    try:
        host.place(app_window.area())
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
