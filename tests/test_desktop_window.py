"""
Tests de la fenêtre de l'interface web (interfaces/desktop/window.py, shell_api.py)

Aucune fenêtre n'est ouverte ici. On vérifie ce qui protège l'appli : la
fenêtre ne charge que ses propres pages, et seuls les liens web sortent vers
le navigateur du système (un « file:// » lancerait un programme). Puis ce qui
se retient d'un lancement à l'autre : taille, position, barre latérale.
"""

# Les gestionnaires de pywebview remplacés sont privés
# pylint: disable=protected-access

import sys
from types import SimpleNamespace

import pytest

from interfaces.desktop import window as desktop_window
from interfaces.desktop.devserver import ViteServer
from interfaces.desktop.lifecycle import UI_DEFAULTS, DesktopApp, DesktopState
from interfaces.desktop.shell_api import (ATTACH_FILTERS, EXPORT_FILTERS, WORKFLOW_FILTERS,
                                          ShellApi, external_url, open_external)
from interfaces.desktop.window import (WindowGeometry, app_origins, colorref,
                                       dropped_paths, is_app_url, watch_drops)

APP = "http://127.0.0.1:53211"


# ── Liens qui sortent de l'appli ────────────────────────────────────────────


@pytest.mark.parametrize("url", [
    "https://example.com/page?q=1#ancre",
    "http://example.com",
    "mailto:contact@example.com",
    "HTTPS://EXAMPLE.COM",
])
def test_web_links_may_leave_the_app(url):
    assert external_url(url) == url


@pytest.mark.parametrize("url", [
    "file:///C:/Windows/System32/calc.exe",
    "javascript:alert(1)",
    "data:text/html,<script>alert(1)</script>",
    "C:/Users/moi/document.pdf",
    "ms-settings:privacy",
    "https://",
    "",
    None,
])
def test_other_schemes_never_leave_the_app(url):
    assert external_url(url) is None


def test_open_external_only_opens_web_links():
    opened = []
    assert open_external("https://example.com", opener=lambda u: opened.append(u) or True)
    assert not open_external("file:///C:/x.exe", opener=lambda u: opened.append(u) or True)
    assert opened == ["https://example.com"]


def test_open_external_survives_a_failing_browser():
    def broken(_url):
        raise OSError("aucun navigateur")

    assert open_external("https://example.com", opener=broken) is False


# ── Pages que la fenêtre peut charger ───────────────────────────────────────


def test_app_origins_come_from_the_window_url():
    url = f"{APP}/#token=secret"
    assert app_origins(url) == (APP,)
    assert app_origins(url, ["http://127.0.0.1:5173"]) == (APP, "http://127.0.0.1:5173")


def test_only_the_app_pages_may_load_in_the_window():
    origins = app_origins(APP)
    assert is_app_url(f"{APP}/#token=secret", origins)
    assert is_app_url(f"{APP}/assets/index.js", origins)
    assert is_app_url("about:blank", origins)
    assert not is_app_url("http://127.0.0.1:9999/", origins)  # autre port
    assert not is_app_url("https://example.com/", origins)
    assert not is_app_url("file:///C:/Windows/notepad.exe", origins)


class FakeNavigation:
    """Arguments des événements WebView2 NavigationStarting / NewWindowRequested."""

    def __init__(self, uri):
        self.uri = uri
        self.cancel = False
        self.handled = False

    def get_Uri(self):  # pylint: disable=invalid-name
        return self.uri

    def set_Cancel(self, value):  # pylint: disable=invalid-name
        self.cancel = value

    def set_Handled(self, value):  # pylint: disable=invalid-name
        self.handled = value


@pytest.fixture(name="chrome")
def chrome_fixture(monkeypatch):
    """Gestionnaires de pywebview (WebView2) remplacés par harden_edgechromium."""
    if not sys.platform.startswith("win"):
        pytest.skip("WebView2 : Windows seulement")
    edgechromium = pytest.importorskip("webview.platforms.edgechromium")
    opened = []
    monkeypatch.setattr(desktop_window, "open_external", opened.append)
    assert desktop_window.harden_edgechromium(app_origins(APP)) is True
    return SimpleNamespace(cls=edgechromium.EdgeChrome, opened=opened)


def test_navigation_outside_the_app_is_cancelled(chrome):
    args = FakeNavigation("https://example.com/")
    chrome.cls.on_navigation_start(SimpleNamespace(pywebview_window=None), None, args)
    assert args.cancel is True
    assert chrome.opened == ["https://example.com/"]


def test_navigation_inside_the_app_goes_on(chrome):
    args = FakeNavigation(f"{APP}/#token=secret")
    page = SimpleNamespace(pywebview_window=SimpleNamespace(transparent=False))
    chrome.cls.on_navigation_start(page, None, args)
    assert args.cancel is False
    assert chrome.opened == []


def test_new_window_never_opens_in_the_app(chrome):
    args = FakeNavigation("file:///C:/Windows/System32/calc.exe")
    chrome.cls.on_new_window_request(None, None, args)
    assert args.handled is True
    # open_external refuse lui-même les schémas non web
    assert chrome.opened == ["file:///C:/Windows/System32/calc.exe"]
    assert external_url(chrome.opened[0]) is None


# ── Barre de titre ──────────────────────────────────────────────────────────


def test_colorref_is_windows_byte_order():
    assert colorref("#0f0f0f") == 0x0F0F0F
    assert colorref("#ff6b47") == 0x476BFF
    assert colorref("#FFFFFF") == 0xFFFFFF
    assert colorref("rgb(1, 2, 3)") is None
    assert colorref("#fff") is None


def test_shell_api_exposes_only_its_functions():
    # pywebview parcourt aussi les attributs publics : rien d'autre ne doit l'être
    public = [name for name in dir(ShellApi()) if not name.startswith("_")]
    assert public == ["native_preview_available", "native_preview_close", "native_preview_place",
                      "native_preview_show", "open_external", "pick_files", "pick_folder",
                      "pick_workflow", "platform", "save_file", "set_title_bar_colors"]


def test_title_bar_colors_go_to_the_window():
    calls = []
    api = ShellApi(title_bar=lambda bg, fg: calls.append((bg, fg)) or True)
    assert api.set_title_bar_colors("#0f0f0f", "#ffffff") is True
    assert calls == [("#0f0f0f", "#ffffff")]
    assert ShellApi().set_title_bar_colors("#0f0f0f", "#ffffff") is False


# ── Dialogues de fichiers et glisser-déposer ────────────────────────────────


def test_dialog_filters_follow_the_pywebview_format():
    """pywebview refuse tout le dialogue si un seul filtre est mal formé."""
    util = pytest.importorskip("webview.util")
    filters = [f for types, _multiple in ATTACH_FILTERS.values() for f in types]
    filters += [f for types in EXPORT_FILTERS.values() for f in types]
    filters += list(WORKFLOW_FILTERS)
    for file_type in filters:
        util.parse_file_type(file_type)
    assert set(ATTACH_FILTERS) == {"PDF", "DOCX", "Excel", "PowerPoint", "Code", "Image"}


class FakeDialogWindow:
    """Fenêtre pywebview réduite à son dialogue de fichiers."""

    def __init__(self, result):
        self.result = result
        self.calls = []

    def create_file_dialog(self, dialog_type, **options):
        self.calls.append((dialog_type, options))
        return self.result


def test_file_dialogs_go_through_the_window(monkeypatch):
    webview = SimpleNamespace(FileDialog=SimpleNamespace(OPEN=10, FOLDER=20, SAVE=30))
    monkeypatch.setitem(sys.modules, "webview", webview)
    api = ShellApi()
    assert api.pick_files("PDF") == []  # pas encore de fenêtre
    window = FakeDialogWindow(("C:/a.pdf", "C:/b.pdf"))
    api._attach_window(window)
    assert api.pick_files("PDF") == ["C:/a.pdf", "C:/b.pdf"]
    assert window.calls[-1] == (10, {"allow_multiple": True,
                                     "file_types": ATTACH_FILTERS["PDF"][0]})
    api.pick_files("Image")
    assert window.calls[-1][1]["allow_multiple"] is False  # une seule image, comme Tk
    window.result = "C:/Projet"
    assert api.pick_folder() == "C:/Projet" and window.calls[-1][0] == 20
    window.result = None
    assert api.save_file("conversation", "pdf") is None
    assert window.calls[-1] == (30, {"save_filename": "conversation",
                                     "file_types": EXPORT_FILTERS["pdf"]})
    # Page Agents : un workflow à charger, un seul fichier JSON
    window.result = ("C:/flux/workflow.json",)
    assert api.pick_workflow() == "C:/flux/workflow.json"
    assert window.calls[-1] == (10, {"allow_multiple": False, "file_types": WORKFLOW_FILTERS})
    window.result = None
    assert api.pick_workflow() is None


def test_dropped_paths_come_from_pywebview():
    event = {"dataTransfer": {"files": [
        {"name": "a.pdf", "pywebviewFullPath": "C:/Docs/a.pdf"},
        {"name": "b.txt"},  # chemin inconnu de pywebview
    ]}}
    assert dropped_paths(event) == ["C:/Docs/a.pdf"]
    assert dropped_paths(None) == [] and dropped_paths({"dataTransfer": None}) == []


def test_drops_are_watched_on_the_document(monkeypatch):
    registered, received = [], []

    class Handler:  # pylint: disable=too-few-public-methods
        def __init__(self, callback, prevent_default=False):
            self.callback = callback
            self.prevent_default = prevent_default

    monkeypatch.setitem(sys.modules, "webview.dom", SimpleNamespace(DOMEventHandler=Handler))
    document = SimpleNamespace(on=lambda event, handler: registered.append((event, handler)))
    window = SimpleNamespace(dom=SimpleNamespace(document=document))
    assert watch_drops(window, received.append) is True
    event, handler = registered[0]
    # La page garde la main sur le dépôt (elle seule sait où il a eu lieu)
    assert event == "drop" and handler.prevent_default is False
    handler.callback({"dataTransfer": {"files": [{"pywebviewFullPath": "C:/x.png"}]}})
    handler.callback({"dataTransfer": {"files": []}})
    assert received == [["C:/x.png"]]


def test_dropped_files_reach_the_page_as_an_event(app):
    events = []
    app.bus.subscribe(events.append)
    app.files_dropped(["C:/a.pdf"])
    assert events[-1]["type"] == "files.dropped"
    assert events[-1]["payload"] == {"paths": ["C:/a.pdf"]}


# ── Taille et position retenues ─────────────────────────────────────────────


def test_first_launch_is_maximized_like_tk():
    geometry = WindowGeometry(None)
    assert geometry.maximized is True
    assert geometry.bounds is None
    assert geometry.to_dict() == {"maximized": True}


def test_saved_geometry_round_trips():
    saved = {"x": 10, "y": 20, "width": 1200, "height": 800, "maximized": False}
    assert WindowGeometry(saved).to_dict() == saved


def test_invalid_saved_geometry_is_ignored():
    geometry = WindowGeometry({"x": "a", "y": 2, "width": 0, "height": 5, "maximized": False})
    assert geometry.bounds is None
    assert geometry.maximized is False


def bounds(x, y, width, height):
    return SimpleNamespace(X=x, Y=y, Width=width, Height=height)


@pytest.mark.parametrize("state, maximized, expected", [
    ("Normal", False, (100, 50, 1300, 850)),
    ("Maximized", True, (40, 30, 1200, 800)),
    ("Minimized", True, (40, 30, 1200, 800)),  # garde l'état d'avant la réduction
])
def test_geometry_is_captured_from_the_form(state, maximized, expected):
    form = SimpleNamespace(WindowState=state, Bounds=bounds(100, 50, 1300, 850),
                           RestoreBounds=bounds(40, 30, 1200, 800))
    geometry = WindowGeometry({"maximized": True})
    geometry.capture(form)
    assert geometry.maximized is maximized
    assert geometry.bounds == expected


def test_geometry_off_every_screen_is_not_restored():
    geometry = WindowGeometry({"x": -100_000, "y": -100_000, "width": 800, "height": 600})
    assert geometry.visible() is False


# ── État de l'interface (barre latérale) ────────────────────────────────────


@pytest.fixture(name="app")
def app_fixture(tmp_path):
    """DesktopApp sans lancement : seul son état local sert ici."""
    return DesktopApp(None, state=DesktopState(tmp_path / ".desktop_state.json"))


def test_ui_state_has_defaults(app):
    assert app.ui_state() == UI_DEFAULTS == {"sidebar_open": False, "preview_width": 560}


def test_ui_state_keeps_only_known_keys(app, tmp_path):
    saved = app.set_ui_state({"sidebar_open": True, "preview_width": 700, "inconnu": 1})
    assert saved == {"sidebar_open": True, "preview_width": 700}
    reloaded = DesktopApp(None, state=DesktopState(tmp_path / ".desktop_state.json"))
    assert reloaded.ui_state() == {"sidebar_open": True, "preview_width": 700}
    assert "inconnu" not in reloaded.state.get("ui")


# ── Serveur Vite du mode --dev ──────────────────────────────────────────────


def test_vite_is_not_running_on_a_closed_port():
    assert ViteServer(5180, url="http://127.0.0.1:9").running() is False


def test_vite_needs_the_front_dependencies(tmp_path):
    vite = ViteServer(5180, url="http://127.0.0.1:9", frontend_dir=tmp_path)
    with pytest.raises(RuntimeError, match="npm install|Node"):
        vite.start(timeout=1)


# ── Ouverture de la fenêtre (pywebview simulé) ──────────────────────────────


class FakeEvent:
    """Événement de pywebview : la fenêtre n'est passée qu'à un paramètre « window »."""

    def __init__(self, window):
        self.window = window
        self.handlers = []

    def __iadd__(self, handler):
        self.handlers.append(handler)
        return self

    def set(self):
        import inspect  # pylint: disable=import-outside-toplevel
        for handler in self.handlers:
            if "window" in inspect.signature(handler).parameters:
                handler(self.window)
            else:
                handler()


class FakeWebview:
    """Module webview réduit à ce qu'utilise open_window."""

    def __init__(self):
        self.settings = {}
        self.window = None
        self.created = None
        self.started = None

    def create_window(self, title, url, **kwargs):
        self.created = (title, url, kwargs)
        self.window = SimpleNamespace(native=None)
        self.window.events = SimpleNamespace(before_show=FakeEvent(self.window),
                                             loaded=FakeEvent(self.window),
                                             closing=FakeEvent(self.window))
        return self.window

    def start(self, **kwargs):
        self.started = kwargs
        self.window.events.before_show.set()
        self.window.events.loaded.set()
        self.window.events.closing.set()


def test_open_window_wires_the_handlers_as_pywebview_calls_them(app, monkeypatch):
    fake = FakeWebview()
    monkeypatch.setitem(sys.modules, "webview", fake)
    for name in ("enable_per_monitor_dpi", "_keep_title_bar_dark"):
        monkeypatch.setattr(desktop_window, name, lambda *_a, **_k: None)
    monkeypatch.setattr(desktop_window, "harden_edgechromium", lambda origins: origins)
    monkeypatch.delenv(desktop_window.ENV_CDP_PORT, raising=False)

    watched = []
    monkeypatch.setattr(desktop_window, "watch_drops",
                        lambda window, on_paths: watched.append((window, on_paths)))
    assert desktop_window.open_window(app, f"{APP}/#token=x") is True
    # Dépôts de fichiers écoutés à chaque chargement de la page
    assert watched == [(fake.window, app.files_dropped)]
    title, url, kwargs = fake.created
    assert (title, url) == ("My_AI", f"{APP}/#token=x")
    assert kwargs["min_size"] == desktop_window.MIN_SIZE and kwargs["text_select"] is True
    assert isinstance(kwargs["js_api"], ShellApi)
    assert fake.settings["ALLOW_DOWNLOADS"] is False and fake.settings["ALLOW_FILE_URLS"] is False
    assert "REMOTE_DEBUGGING_PORT" not in fake.settings  # jamais sans demande explicite
    assert fake.started["private_mode"] is True and fake.started["debug"] is False


def test_without_pywebview_the_interface_opens_in_the_browser(monkeypatch, tmp_path):
    """Repli du §3 : sans fenêtre pywebview, l'URL (jeton compris) part au navigateur."""
    from interfaces.desktop import lifecycle  # pylint: disable=import-outside-toplevel

    opened, waited = [], []
    monkeypatch.setattr(desktop_window, "open_window", lambda _app, _url, **_kw: False)
    monkeypatch.setattr("webbrowser.open", lambda url: opened.append(url) or True)
    monkeypatch.setattr(lifecycle.DesktopApp, "wait", lambda _self: waited.append(True))
    monkeypatch.setattr(lifecycle, "DesktopState",
                        lambda: DesktopState(tmp_path / ".desktop_state.json"))
    # Lanceur vide : les étapes du lancement échouent sans rien lancer
    lifecycle.run_desktop(SimpleNamespace(), port=0)

    assert len(opened) == 1 and opened[0].startswith("http://127.0.0.1:")
    assert "#token=" in opened[0]
    assert waited == [True]
