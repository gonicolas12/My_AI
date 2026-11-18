"""
Tests du logo de My_AI dans la barre des tâches et le Dock (interfaces/desktop/app_identity.py)

Aucune fenêtre n'est affichée ici. L'AppUserModelID de Windows vaut pour tout
le processus : il se vérifie dans un interpréteur neuf, comme les propriétés
de relance (nom du bouton, épingle), posées sur une vraie fenêtre jamais
affichée. macOS et Linux se vérifient avec des modules GTK et Qt simulés, et
sur le code de pywebview installé, qui pose l'icône qu'on lui passe.
"""

# pylint: disable=protected-access

import configparser
import importlib.util
import os
import re
import subprocess
import sys
import types
from pathlib import Path
from types import SimpleNamespace

import pytest

from interfaces.desktop import app_identity
from interfaces.desktop.app_identity import (LINUX_APP_ID, applications_dir, desktop_entry,
                                             icon_path, install_desktop_entry)

PROJECT_ROOT = Path(__file__).resolve().parent.parent


# ── Icônes ──────────────────────────────────────────────────────────────────


@pytest.mark.parametrize("platform, name", [
    ("win32", "my_ai.ico"),
    ("darwin", "my_ai.png"),
    ("linux", "my_ai.png"),
])
def test_each_system_gets_its_icon_format(platform, name):
    path = icon_path(platform)
    assert path is not None and path.name == name and path.is_file()


def test_a_missing_icon_is_not_passed_to_pywebview(monkeypatch, tmp_path):
    monkeypatch.setattr(app_identity, "PNG_PATH", tmp_path / "absente.png")
    assert icon_path("linux") is None


def test_the_png_is_the_windows_icon_drawing():
    """Même robot partout : le PNG est la plus grande taille de l'icône Windows."""
    image = pytest.importorskip("PIL.Image")
    png = image.open(app_identity.PNG_PATH)
    # 256 px : GTK 3 ignore sous X11 une icône de 512 px
    assert (png.format, png.size, png.mode) == ("PNG", (256, 256), "RGBA")
    ico = image.open(app_identity.ICO_PATH)
    ico.size = (256, 256)
    assert ico.convert("RGBA").tobytes() == png.tobytes()


PYWEBVIEW_ICON_CODE = {
    # Barre de titre ; la barre des tâches aussi, une fois l'AppUserModelID posé
    "winforms": ("self.Icon = Icon(_state['icon'])",),
    # Dock
    "cocoa": ("initByReferencingFile_(_state['icon'])", "setApplicationIconImage_(ns_image)"),
    # Fenêtre (X11)
    "gtk": ("set_icon_from_file(_state['icon'])",),
    # Fenêtre, puis before_show avant l'affichage : l'app_id posé là sert encore
    "qt": ("QIcon(_state['icon'])", "events.before_show.set()", "browser.show()"),
}


@pytest.mark.parametrize("platform", sorted(PYWEBVIEW_ICON_CODE))
def test_installed_pywebview_shows_the_icon_it_is_given(platform):
    """L'icône passée à webview.start sert sous chaque système, Dock compris.

    Lu dans le code installé : celui de macOS et de Linux ne s'importe pas ici.
    """
    spec = importlib.util.find_spec("webview")
    if spec is None or spec.origin is None:
        pytest.skip("pywebview absent")
    source = (Path(spec.origin).parent / "platforms" / f"{platform}.py").read_text(encoding="utf-8")
    positions = [source.find(code) for code in PYWEBVIEW_ICON_CODE[platform]]
    assert -1 not in positions, dict(zip(PYWEBVIEW_ICON_CODE[platform], positions))
    assert positions == sorted(positions)


# ── Windows : AppUserModelID ────────────────────────────────────────────────


def test_windows_app_id_is_set_for_the_process():
    """Le vrai appel de Windows, relu par GetCurrentProcessExplicitAppUserModelID."""
    if not sys.platform.startswith("win"):
        pytest.skip("AppUserModelID : Windows seulement")
    code = (
        "import ctypes\n"
        "from interfaces.desktop import app_identity\n"
        "shell32 = ctypes.windll.shell32\n"
        "value = ctypes.c_wchar_p()\n"
        "print(shell32.GetCurrentProcessExplicitAppUserModelID(ctypes.byref(value)) != 0)\n"
        "print(app_identity.set_windows_app_id())\n"
        "print(shell32.GetCurrentProcessExplicitAppUserModelID(ctypes.byref(value)) == 0,"
        " value.value)\n"
        "ctypes.windll.ole32.CoTaskMemFree(value)\n"
    )
    run = subprocess.run(
        [sys.executable, "-c", code],
        cwd=PROJECT_ROOT,
        capture_output=True,
        encoding="utf-8",
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
        timeout=120,
        check=False,
    )
    assert run.returncode == 0, run.stderr[-3000:]
    # Aucun identifiant avant l'appel (celui de python.exe), « My_AI » après
    assert run.stdout.splitlines() == ["True", "True", "True My_AI"]


class FakeShell32:
    """shell32 réduit à SetCurrentProcessExplicitAppUserModelID."""

    def __init__(self, result=0):
        self.result = result
        self.calls = []

    def SetCurrentProcessExplicitAppUserModelID(self, app_id):  # pylint: disable=invalid-name
        self.calls.append(app_id.value)
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


def test_windows_app_id_is_my_ai_like_the_notifications(monkeypatch):
    from utils.desktop_notify import APP_ID  # pylint: disable=import-outside-toplevel

    shell32 = FakeShell32()
    monkeypatch.setattr(app_identity, "IS_WINDOWS", True)
    monkeypatch.setattr(app_identity, "_shell32", lambda: shell32)
    assert app_identity.set_windows_app_id() is True
    assert shell32.calls == ["My_AI"] == [APP_ID]


@pytest.mark.parametrize("result", [-2147024809, OSError("shell32")])  # E_INVALIDARG
def test_a_refused_windows_app_id_does_not_stop_the_launch(monkeypatch, result):
    monkeypatch.setattr(app_identity, "IS_WINDOWS", True)
    monkeypatch.setattr(app_identity, "_shell32", lambda: FakeShell32(result))
    assert app_identity.set_windows_app_id() is False


def test_no_windows_app_id_elsewhere(monkeypatch):
    shell32 = FakeShell32()
    monkeypatch.setattr(app_identity, "IS_WINDOWS", False)
    monkeypatch.setattr(app_identity, "_shell32", lambda: shell32)
    assert app_identity.set_windows_app_id() is False
    assert shell32.calls == []


# ── Windows : nom du bouton et épingle (propriétés de la fenêtre) ───────────


def command_line(command):
    """Arguments d'une ligne de commande, lus comme Windows (CommandLineToArgvW)."""
    import ctypes  # pylint: disable=import-outside-toplevel
    from ctypes import wintypes  # pylint: disable=import-outside-toplevel

    parse = ctypes.windll.shell32.CommandLineToArgvW
    parse.restype = ctypes.POINTER(wintypes.LPWSTR)
    parse.argtypes = [wintypes.LPCWSTR, ctypes.POINTER(ctypes.c_int)]
    count = ctypes.c_int()
    argv = parse(command, ctypes.byref(count))
    try:
        return [argv[i] for i in range(count.value)]
    finally:
        ctypes.windll.kernel32.LocalFree(argv)


def test_a_pinned_my_ai_runs_the_launcher_with_pythonw(tmp_path):
    """Sans console : pythonw.exe, à côté de python.exe (installation comme venv)."""
    scripts = tmp_path / "Mes projets" / "venv" / "Scripts"
    scripts.mkdir(parents=True)
    python = scripts / "python.exe"
    python.write_bytes(b"")
    launcher = tmp_path / "Mes projets" / "My_AI" / "launch_unified.py"
    # Sans pythonw.exe, python.exe (avec sa console) plutôt que rien
    assert app_identity.relaunch_command(str(python), launcher) == f'"{python}" "{launcher}"'
    (scripts / "pythonw.exe").write_bytes(b"")
    command = app_identity.relaunch_command(str(python), launcher)
    assert command == f'"{scripts / "pythonw.exe"}" "{launcher}"'
    if sys.platform.startswith("win"):
        # Lue comme le shell la lira : les espaces ne coupent pas les chemins
        assert command_line(command) == [str(scripts / "pythonw.exe"), str(launcher)]
    assert app_identity.relaunch_command("", launcher) is None


def test_by_default_the_pin_relaunches_this_launcher():
    command = app_identity.relaunch_command()
    assert command.endswith(f' "{PROJECT_ROOT / "launch_unified.py"}"')
    windowed = Path(sys.executable).with_name("pythonw.exe")
    expected = windowed if windowed.is_file() else Path(sys.executable)
    assert command.startswith(f'"{expected}" ')


def test_relaunch_properties_come_before_the_window_app_id():
    """Ordre demandé par Windows : poser l'AppUserModelID fait relire la fenêtre."""
    properties = app_identity.window_properties('"pythonw.exe" "launch_unified.py"')
    assert properties == [
        (app_identity.PID_RELAUNCH_COMMAND, '"pythonw.exe" "launch_unified.py"'),
        (app_identity.PID_RELAUNCH_NAME, "My_AI"),  # nom du bouton et de l'épingle
        (app_identity.PID_RELAUNCH_ICON, f"{app_identity.ICO_PATH},0"),
        (app_identity.PID_APP_ID, "My_AI"),  # celui du processus et des notifications
    ]
    assert [pid for pid, _value in properties] == [2, 4, 3, 5]  # propkey.h


class FakeStore:
    """IPropertyStore d'une fenêtre, simulé : propriétés posées, dans l'ordre."""

    created = []

    def __init__(self, hwnd, fail=None):
        self.hwnd = hwnd
        self.fail = fail
        self.calls = []
        self.closed = False
        FakeStore.created.append(self)

    def set(self, pid, value):
        if self.fail == "set":
            raise OSError("IPropertyStore::SetValue : HRESULT 0x80070005")
        self.calls.append((pid, value))

    def close(self):
        self.closed = True


@pytest.fixture(name="stores")
def stores_fixture(monkeypatch):
    """Fenêtres de Windows simulées : les IPropertyStore ouverts."""
    monkeypatch.setattr(app_identity, "IS_WINDOWS", True)
    monkeypatch.setattr(FakeStore, "created", [])
    monkeypatch.setattr(app_identity, "WindowPropertyStore", FakeStore)
    return FakeStore.created


def test_window_gets_its_name_then_loses_it_before_closing(stores):
    assert app_identity.set_window_identity(4242, command='"pythonw.exe" "l.py"') is True
    assert app_identity.clear_window_identity(4242) is True
    posed, cleared = stores
    assert posed.hwnd == cleared.hwnd == 4242
    assert posed.calls == app_identity.window_properties('"pythonw.exe" "l.py"')
    # Retirées (VT_EMPTY) avant la fermeture, comme le demande Windows
    assert cleared.calls == [(2, None), (4, None), (3, None), (5, None)]
    assert posed.closed and cleared.closed


def test_window_relaunch_command_defaults_to_the_launcher(stores):
    assert app_identity.set_window_identity(4242) is True
    assert stores[0].calls[0] == (2, app_identity.relaunch_command())


@pytest.mark.parametrize("fail", ["store", "set"])
def test_a_refused_window_property_does_not_stop_the_launch(monkeypatch, stores, fail):
    def store(hwnd):
        if fail == "store":
            raise OSError("SHGetPropertyStoreForWindow : HRESULT 0x80070057")
        return FakeStore(hwnd, fail)

    monkeypatch.setattr(app_identity, "WindowPropertyStore", store)
    assert app_identity.set_window_identity(4242, command="c") is False
    assert app_identity.clear_window_identity(4242) is False
    assert all(created.closed for created in stores)  # jamais d'IPropertyStore oublié


def test_no_window_properties_elsewhere_or_without_window(monkeypatch, stores):
    assert app_identity.set_window_identity(0, command="c") is False
    assert app_identity.set_window_identity(4242, command="") is False
    monkeypatch.setattr(app_identity, "IS_WINDOWS", False)
    assert app_identity.set_window_identity(4242, command="c") is False
    assert app_identity.clear_window_identity(4242) is False
    assert stores == []


def test_window_properties_are_set_on_a_real_window():
    """Le vrai appel de Windows, sur une fenêtre jamais affichée, relu par IPropertyStore."""
    if not sys.platform.startswith("win"):
        pytest.skip("propriétés de fenêtre : Windows seulement")
    code = (
        "import ctypes\n"
        "from ctypes import wintypes\n"
        "from interfaces.desktop import app_identity as ai\n"
        "user32 = ctypes.windll.user32\n"
        "user32.CreateWindowExW.restype = wintypes.HWND\n"
        "user32.CreateWindowExW.argtypes = [wintypes.DWORD, wintypes.LPCWSTR, wintypes.LPCWSTR,"
        " wintypes.DWORD] + [ctypes.c_int] * 4 + [wintypes.HWND, wintypes.HMENU,"
        " wintypes.HINSTANCE, wintypes.LPVOID]\n"
        # WS_OVERLAPPEDWINDOW, sans WS_VISIBLE : aucun bouton dans la barre des tâches
        "hwnd = user32.CreateWindowExW(0, 'STATIC', 'My_AI', 0x00CF0000, 0, 0, 200, 100,"
        " None, None, None, None)\n"
        "print(ai.set_window_identity(hwnd))\n"
        "store = ai.WindowPropertyStore(hwnd)\n"
        "print(store.count())\n"
        "for pid in (2, 4, 3, 5):\n"
        "    print(store.get(pid))\n"
        "store.close()\n"
        "print(ai.clear_window_identity(hwnd))\n"
        "store = ai.WindowPropertyStore(hwnd)\n"
        "print(store.count(), store.get(5))\n"
        "store.close()\n"
        "print(bool(user32.DestroyWindow(hwnd)))\n"
    )
    run = subprocess.run(
        [sys.executable, "-c", code],
        cwd=PROJECT_ROOT,
        capture_output=True,
        encoding="utf-8",
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
        timeout=120,
        check=False,
    )
    assert run.returncode == 0, run.stderr[-3000:]
    assert run.stdout.splitlines() == [
        "True", "4",
        app_identity.relaunch_command(sys.executable),
        "My_AI",
        f"{app_identity.ICO_PATH},0",
        "My_AI",
        "True", "0 None",  # plus rien sur la fenêtre une fois retirées
        "True",
    ]


# ── Linux : app_id de la fenêtre (GTK, Qt) ──────────────────────────────────


def fake_module(monkeypatch, name, **attributes):
    """Module simulé dans sys.modules, rattaché à son paquet parent."""
    module = types.ModuleType(name)
    for key, value in attributes.items():
        setattr(module, key, value)
    monkeypatch.setitem(sys.modules, name, module)
    parent, _, child = name.rpartition(".")
    if parent:
        setattr(sys.modules[parent], child, module)
    return module


def test_gtk_takes_my_ai_as_program_name(monkeypatch):
    names = []
    fake_module(monkeypatch, "gi")
    fake_module(monkeypatch, "gi.repository", GLib=SimpleNamespace(set_prgname=names.append))
    assert app_identity.set_linux_app_id() is True
    assert names == [LINUX_APP_ID] == ["my_ai"]


def test_without_gtk_the_program_name_is_left_to_qt(monkeypatch):
    monkeypatch.setitem(sys.modules, "gi", None)  # PyGObject absent
    assert app_identity.set_linux_app_id() is False


def pywebview_window(platform):
    """Fenêtre native de pywebview : une instance de la classe de son module."""
    return type("BrowserView", (), {"__module__": f"webview.platforms.{platform}"})()


def test_qt_window_takes_my_ai_as_app_id(monkeypatch):
    names = []
    fake_module(monkeypatch, "qtpy")
    fake_module(monkeypatch, "qtpy.QtGui",
                QGuiApplication=SimpleNamespace(setDesktopFileName=names.append))
    assert app_identity.set_qt_app_id(pywebview_window("qt")) is True
    assert names == ["my_ai"]
    # Les autres fenêtres de pywebview n'importent pas Qt
    for native in (pywebview_window("gtk"), pywebview_window("winforms"), None):
        assert app_identity.set_qt_app_id(native) is False
    assert names == ["my_ai"]


def test_a_failing_qt_does_not_stop_the_launch(monkeypatch):
    def refuse(_name):
        raise RuntimeError("Qt trop ancien")

    fake_module(monkeypatch, "qtpy")
    fake_module(monkeypatch, "qtpy.QtGui",
                QGuiApplication=SimpleNamespace(setDesktopFileName=refuse))
    assert app_identity.set_qt_app_id(pywebview_window("qt")) is False


# ── Linux : fichier .desktop ────────────────────────────────────────────────


_STRING_ESCAPES = {"s": " ", "n": "\n", "t": "\t", "r": "\r", "\\": "\\"}


def desktop_value(raw):
    """Valeur de type chaîne, lue comme le fait le bureau."""
    return re.sub(r"\\(.)", lambda m: _STRING_ESCAPES.get(m.group(1), m.group(0)), raw)


def exec_arguments(raw):
    """Arguments de la clé Exec, lus selon la spécification Desktop Entry."""
    text = desktop_value(raw).replace("%%", "%")
    arguments, current, quoted, escaped, started = [], [], False, False, False
    for char in text:
        if escaped:
            current.append(char)
            escaped = False
        elif quoted and char == "\\":
            escaped = True
        elif char == '"':
            quoted, started = not quoted, True
        elif char == " " and not quoted:
            if started:
                arguments.append("".join(current))
            current, started = [], False
        else:
            current.append(char)
            started = True
    assert not quoted and not escaped
    if started:
        arguments.append("".join(current))
    return arguments


def read_entry(content):
    """Clés brutes du groupe [Desktop Entry]."""
    parser = configparser.ConfigParser(interpolation=None, delimiters=("=",))
    parser.optionxform = str  # les clés gardent leur casse
    parser.read_string(content)
    return dict(parser["Desktop Entry"])


ROOT = "/home/moi/My_AI"
ENTRY_ARGS = ("/usr/bin/python3", f"{ROOT}/launch_unified.py",
              f"{ROOT}/interfaces/desktop/assets/my_ai.png", ROOT)


def test_desktop_entry_gives_the_window_its_icon():
    entry = read_entry(desktop_entry(*ENTRY_ARGS))
    assert entry["Type"] == "Application" and entry["Name"] == "My_AI"
    assert entry["Icon"] == f"{ROOT}/interfaces/desktop/assets/my_ai.png"
    # Même nom que l'app_id de la fenêtre (Wayland) et que sa classe (X11)
    assert entry["StartupWMClass"] == LINUX_APP_ID
    assert entry["NoDisplay"] == "true"  # hors des menus
    assert entry["Exec"] == f'"/usr/bin/python3" "{ROOT}/launch_unified.py"'
    assert entry["Path"] == ROOT and entry["Terminal"] == "false"


@pytest.mark.parametrize("python, launcher", [
    ("/home/moi/Mes projets/venv/bin/python", "/home/moi/Mes projets/My_AI/launch_unified.py"),
    ('/opt/"guillemets"/python3', "/opt/$HOME/`date`/100%/a\\b/launch_unified.py"),
])
def test_exec_keeps_unusual_paths_intact(python, launcher):
    entry = read_entry(desktop_entry(python, launcher, "/opt/a b/my_ai.png", "/opt/a b"))
    assert exec_arguments(entry["Exec"]) == [python, launcher]
    assert desktop_value(entry["Icon"]) == "/opt/a b/my_ai.png"


def test_paths_with_control_characters_give_no_desktop_entry():
    assert desktop_entry("/usr/bin/python3", "/opt/a\nb/launch_unified.py", "/i.png", "/") is None


def test_desktop_entries_go_to_the_xdg_data_home():
    assert applications_dir({"XDG_DATA_HOME": str(PROJECT_ROOT)}) == PROJECT_ROOT / "applications"
    default = Path.home() / ".local" / "share" / "applications"
    assert applications_dir({}) == default
    # Relatif : ignoré (spécification XDG Base Directory)
    assert applications_dir({"XDG_DATA_HOME": "relatif/share"}) == default


def test_desktop_file_is_written_then_kept_while_unchanged(tmp_path):
    content = desktop_entry(*ENTRY_ARGS)
    folder = tmp_path / "share" / "applications"
    path = install_desktop_entry(content, folder)
    assert path == folder / "my_ai.desktop"
    assert path.read_bytes() == content.encode("utf-8")  # fins de ligne LF
    assert sorted(p.name for p in folder.iterdir()) == ["my_ai.desktop"]

    os.utime(path, ns=(0, 0))
    assert install_desktop_entry(content, folder) == path
    assert path.stat().st_mtime_ns == 0  # pas réécrit

    # Dépôt déplacé, autre Python : réécrit
    moved = desktop_entry("/opt/venv/bin/python", "/srv/My_AI/launch_unified.py",
                          "/srv/My_AI/interfaces/desktop/assets/my_ai.png", "/srv/My_AI")
    assert install_desktop_entry(moved, folder) == path
    assert path.read_text(encoding="utf-8") == moved


def test_the_users_own_desktop_file_is_left_alone(tmp_path):
    own = "[Desktop Entry]\nType=Application\nName=Mon My_AI\nExec=my_ai\nIcon=robot\n"
    (tmp_path / "my_ai.desktop").write_text(own, encoding="utf-8")
    assert install_desktop_entry(desktop_entry(*ENTRY_ARGS), tmp_path) is None
    assert (tmp_path / "my_ai.desktop").read_text(encoding="utf-8") == own


def test_an_unwritable_folder_does_not_stop_the_launch(tmp_path):
    blocked = tmp_path / "applications"
    blocked.write_text("un fichier, pas un dossier", encoding="utf-8")
    assert install_desktop_entry(desktop_entry(*ENTRY_ARGS), blocked) is None


# ── Avant la première fenêtre ───────────────────────────────────────────────


@pytest.fixture(name="steps")
def steps_fixture(monkeypatch):
    """Étapes de prepare() appelées, sans rien poser pour de vrai."""
    calls = []
    monkeypatch.setattr(app_identity, "set_windows_app_id", lambda: calls.append("windows"))
    monkeypatch.setattr(app_identity, "set_linux_app_id", lambda: calls.append("gtk"))
    return calls


def test_windows_launch_only_sets_the_app_id(monkeypatch, steps, tmp_path):
    monkeypatch.setattr(app_identity, "IS_WINDOWS", True)
    monkeypatch.setattr(app_identity, "IS_MACOS", False)
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    app_identity.prepare()
    assert steps == ["windows"]
    assert not (tmp_path / "applications").exists()


def test_macos_launch_leaves_the_dock_to_pywebview(monkeypatch, steps, tmp_path):
    monkeypatch.setattr(app_identity, "IS_WINDOWS", False)
    monkeypatch.setattr(app_identity, "IS_MACOS", True)
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    app_identity.prepare()
    assert steps == []
    assert not (tmp_path / "applications").exists()


def test_linux_launch_names_the_window_and_writes_its_desktop_file(monkeypatch, steps, tmp_path):
    monkeypatch.setattr(app_identity, "IS_WINDOWS", False)
    monkeypatch.setattr(app_identity, "IS_MACOS", False)
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    app_identity.prepare()
    assert steps == ["gtk"]
    entry = read_entry((tmp_path / "applications" / "my_ai.desktop").read_text(encoding="utf-8"))
    assert desktop_value(entry["Icon"]) == str(app_identity.PNG_PATH)
    launcher = str(PROJECT_ROOT / "launch_unified.py")
    assert exec_arguments(entry["Exec"]) == [sys.executable, launcher]
    assert desktop_value(entry["Path"]) == str(PROJECT_ROOT)
