"""
Tests des visionneuses Office de la fenêtre (interfaces/desktop/native_viewer.py)
et de leur pont (shell_api.py)

Hôte et visionneuse simulés : chargement masqué, affichage à la demande de la
page, aperçu remplacé ou fermé pendant un chargement, délai dépassé, documents
acceptés par le serveur seulement. Le vrai rendu de Word, Excel et PowerPoint
est vérifié par tests/test_native_preview.py et dans la vraie fenêtre.
"""

import threading

import pytest

from interfaces.desktop import native_viewer
from interfaces.desktop.native_viewer import NativeViewer, parse_rect
from interfaces.desktop.shell_api import ShellApi

RECT = {"x": 900, "y": 60, "width": 700, "height": 800}


@pytest.fixture(autouse=True, name="office")
def office_fixture(monkeypatch):
    """Aucun vrai processus : la visionneuse simulée « tourne » dans le processus 9001."""
    closed = []
    monkeypatch.setattr(native_viewer, "hosted_processes", lambda hwnd: {9001} if hwnd else set())
    monkeypatch.setattr(native_viewer, "launched_office",
                        lambda pids, since: [("office", pid) for pid in sorted(pids)])
    monkeypatch.setattr(native_viewer, "close_office", closed.append)
    return closed


class FakeHost:
    """Hôte WinForms : positions et visibilité notées."""

    def __init__(self):
        self.calls = []

    @staticmethod
    def handle():
        return 4242

    def place(self, rect, visible):
        self.calls.append(("place", rect, visible))

    def hide(self):
        self.calls.append(("hide",))

    @property
    def visible(self):
        shown = [call for call in self.calls if call[0] in ("place", "hide")]
        return bool(shown) and shown[-1][0] == "place" and shown[-1][2]


class FakePreview:
    """AsyncNativePreview : résultat rendu tout de suite, ou à la demande."""

    def __init__(self, ok=True, manual=False):
        self.ok = ok
        self.manual = manual
        self.pending = []
        self.calls = []

    def open(self, path, hwnd, on_result):
        self.calls.append(("open", path, hwnd))
        if self.manual:
            self.pending.append(on_result)
        else:
            on_result(self.ok)

    def resize(self):
        self.calls.append(("resize",))

    def close(self, wait=0.0):
        self.calls.append(("close", wait))


def make(preview=None, timeout=5.0):
    host = FakeHost()
    preview = preview or FakePreview()
    return host, preview, NativeViewer(lambda: host, lambda: preview, open_timeout=timeout)


def test_rects_are_checked():
    assert parse_rect(RECT) == (900, 60, 700, 800)
    assert parse_rect({"x": "12", "y": 3.7, "width": 10, "height": 10}) == (12, 3, 10, 10)
    assert parse_rect({"x": 0, "y": 0, "width": 0, "height": 10}) is None
    assert parse_rect({"x": 0, "y": 0}) is None and parse_rect("0,0,10,10") is None
    assert parse_rect({"x": 10**9, "y": 0, "width": 10**9, "height": 5}) == (32000, 0, 32000, 5)


def test_loaded_hidden_then_shown_by_the_page():
    host, preview, viewer = make()
    rect = parse_rect(RECT)
    assert viewer.place(rect, True) is False  # rien de chargé : pas d'hôte
    assert viewer.show("C:/docs/rapport.docx", rect) is True
    assert preview.calls[0] == ("open", "C:/docs/rapport.docx", 4242)
    assert host.calls[0] == ("place", rect, False) and not host.visible

    assert viewer.place(rect, True) is True and host.visible
    # Un dialogue s'ouvre : masquée, toujours chargée
    assert viewer.place(rect, False) is True and not host.visible
    moved = (880, 60, 720, 800)
    viewer.place(moved, True)
    assert host.calls[-1] == ("place", moved, True) and preview.calls[-1] == ("resize",)

    viewer.close()
    assert not host.visible and preview.calls[-1] == ("close", 0.0)
    viewer.place(rect, True)
    assert not host.visible  # plus rien de chargé


def test_a_failed_viewer_never_shows():
    host, _preview, viewer = make(FakePreview(ok=False))
    assert viewer.show("C:/docs/abime.xlsx", parse_rect(RECT)) is False
    viewer.place(parse_rect(RECT), True)
    assert not host.visible


def test_a_viewer_replaced_while_loading_is_not_shown():
    preview = FakePreview(manual=True)
    host, _preview, viewer = make(preview)
    results = []
    worker = threading.Thread(
        target=lambda: results.append(viewer.show("C:/docs/a.pptx", parse_rect(RECT))))
    worker.start()
    while not preview.pending:
        threading.Event().wait(0.01)
    viewer.close()  # volet fermé pendant le démarrage de PowerPoint
    preview.pending.pop()(True)
    worker.join(2)
    assert results == [False]
    viewer.place(parse_rect(RECT), True)
    assert not host.visible


def test_a_slow_viewer_falls_back(monkeypatch):
    monkeypatch.setattr(native_viewer.logger, "warning", lambda *args: None)
    _host, preview, viewer = make(FakePreview(manual=True), timeout=0.05)
    assert viewer.show("C:/docs/lent.docx", parse_rect(RECT)) is False
    assert ("close", 0.0) in preview.calls


def test_shutdown_waits_for_office_then_closes_the_one_it_launched(office):
    _host, preview, viewer = make()
    viewer.show("C:/docs/rapport.docx", parse_rect(RECT))
    viewer.close()  # aperçu fermé : Word caché laissé lancé, l'appli tourne encore
    assert office == []
    viewer.shutdown()
    assert preview.calls[-1] == ("close", native_viewer.SHUTDOWN_WAIT)
    assert office == [[("office", 9001)]]


class FakeProcess:
    """psutil.Process simulé."""

    def __init__(self, pid, name, started, cmdline):
        self.pid = pid
        self._name, self._started, self._cmdline = name, started, cmdline

    def name(self):
        return self._name

    def create_time(self):
        return self._started

    def cmdline(self):
        return self._cmdline


def test_only_hidden_office_launched_for_previews_is_closed(monkeypatch):
    monkeypatch.undo()  # la vraie sélection, sur des processus simulés
    processes = {
        1: FakeProcess(1, "WINWORD.EXE", 200, ["WINWORD.EXE", "-Embedding"]),
        2: FakeProcess(2, "WINWORD.EXE", 50, ["WINWORD.EXE", "-Embedding"]),   # avant l'appli
        3: FakeProcess(3, "WINWORD.EXE", 300, ["WINWORD.EXE", "/n", "C:/a.docx"]),  # ouvert par toi
        4: FakeProcess(4, "WINWORD.EXE", 300, ["WINWORD.EXE", "/Embedding"]),  # document visible
        5: FakeProcess(5, "EXCEL.EXE", 250, ["EXCEL.EXE", "/automation", "-Embedding"]),
        6: FakeProcess(6, "chrome.exe", 300, ["chrome.exe", "--embedding"]),
    }

    def process(pid):
        if pid not in processes:
            raise native_viewer.psutil.NoSuchProcess(pid)
        return processes[pid]

    def windows(pid):
        return [(40, pid == 4, "OpusApp")]

    selected = native_viewer.launched_office([1, 2, 3, 4, 5, 6, 7], since=100,
                                             process=process, windows=windows)
    assert [proc.pid for proc in selected] == [1, 5]


def test_the_bridge_opens_only_what_the_server_accepted(monkeypatch):
    monkeypatch.setattr(NativeViewer, "available", staticmethod(lambda: True))
    sources = {"apercu-1": "C:/docs/rapport.docx"}
    shell = ShellApi(native_source=sources.get)
    host, preview, viewer = make()
    shell._native = viewer  # pylint: disable=protected-access

    assert shell.native_preview_available() is True
    assert shell.native_preview_show("inconnu", RECT) is False
    assert shell.native_preview_show("apercu-1", {"x": 1}) is False
    assert preview.calls == []
    assert shell.native_preview_show("apercu-1", RECT) is True
    assert shell.native_preview_place(RECT, True) is True and host.visible
    assert shell.native_preview_place("ailleurs", True) is False
    assert shell.native_preview_close() is True and not host.visible

    # Hors de la fenêtre (navigateur) : aucune visionneuse
    assert ShellApi().native_preview_available() is False


def test_without_window_there_is_no_host():
    shell = ShellApi(native_source=lambda _id: "C:/docs/rapport.docx")
    viewer = shell._native  # pylint: disable=protected-access
    if not NativeViewer.available():
        pytest.skip("visionneuses Windows indisponibles")
    assert viewer.show("C:/docs/rapport.docx", parse_rect(RECT)) is False
