"""
Tests du lancement sans console (utils/no_console.py) : My_AI ouvert depuis son épingle

L'épingle de la barre des tâches lance My_AI par pythonw, sans console :
sys.stdout et sys.stderr valent None. Les sorties doivent alors aller dans
logs/, les commandes console ne doivent pas ouvrir leur propre fenêtre, et une
erreur du lancement doit se voir. Les vrais lancements sans console tournent
dans un pythonw neuf ; aucune boîte de dialogue ne s'y affiche (simulée).
"""

# pylint: disable=protected-access

import os
import subprocess
import sys
import threading
import time
from pathlib import Path

import pytest

from utils import desktop_notify, no_console

PROJECT_ROOT = Path(__file__).resolve().parent.parent
IS_WINDOWS = sys.platform.startswith("win")
CREATE_NEW_CONSOLE = 0x10
CREATE_NEW_PROCESS_GROUP = 0x200


@pytest.fixture(autouse=True)
def _fresh_state(monkeypatch):
    """Chaque test part d'un lancement avec console, boîtes de dialogue simulées."""
    monkeypatch.setattr(no_console, "_STATE", {"active": False, "log": None, "stream": None})
    boxes = []
    monkeypatch.setattr(no_console, "_message_box",
                        lambda message, icon: boxes.append((message, icon)) or True)
    return boxes


def pythonw():
    path = Path(sys.executable).with_name("pythonw.exe")
    if not IS_WINDOWS or not path.is_file():
        pytest.skip("pythonw : Windows seulement")
    return path


def launch_block(log, pid):
    """Sorties d'un lancement sans console, de son en-tête (pid) au lancement suivant."""
    text = log.read_text(encoding="utf-8")
    start = text.index(f"pid {pid})")
    following = text.find("\n===== ", start)
    return text[start:] if following == -1 else text[start:following]


# ── Avec une console : rien ne change ───────────────────────────────────────


def test_with_a_console_nothing_changes(_fresh_state, tmp_path):
    assert no_console.has_console()
    assert no_console.start(tmp_path / "logs") is False
    assert not no_console.active() and no_console.log_path() is None
    assert not (tmp_path / "logs").exists()
    # Les messages sont déjà dans la console : pas de boîte de dialogue
    assert no_console.show_error("Python 3.15 n'est pas pris en charge") is False
    assert no_console.wait_for_dismiss("Interface ouverte dans le navigateur") is False
    assert _fresh_state == []


def test_a_launch_warning_is_a_notification_that_blocks_nothing(_fresh_state, monkeypatch):
    shown = []
    done = threading.Event()

    def notify_desktop(title, message):
        shown.append((title, message, threading.current_thread() is threading.main_thread()))
        done.set()
        return True

    monkeypatch.setattr(desktop_notify, "notify_desktop", notify_desktop)
    # Avec une console : rien, l'avertissement y est déjà écrit
    assert no_console.show_notice("Mise à jour de Python conseillée", "Installez…") is False
    assert shown == []
    # Sans console : une notification, envoyée d'un fil à part ; jamais de boîte
    # de dialogue, qui attendrait qu'on la referme
    monkeypatch.setitem(no_console._STATE, "active", True)
    assert no_console.show_notice("Mise à jour de Python conseillée", "Installez…") is True
    assert done.wait(5)
    assert shown == [("Mise à jour de Python conseillée", "Installez…", False)]
    assert _fresh_state == []


# ── Sans console ────────────────────────────────────────────────────────────


@pytest.fixture(name="windowless")
def windowless_fixture(monkeypatch):
    """Ce processus vu comme un pythonw, sans toucher à ce que pytest garde pour lui.

    pytest remet ses propres sys.stdout et sys.stderr à chaque phase du test :
    as_pythonw() les met à None dans le corps du test. Ni les descripteurs 1
    et 2 ni subprocess.Popen du processus de pytest ne changent.
    """
    monkeypatch.setattr(sys, "excepthook", sys.excepthook)
    monkeypatch.setattr(no_console, "_share_with_children", lambda _stream: None)
    hidden = []
    monkeypatch.setattr(no_console, "hide_child_consoles", lambda: hidden.append(True))
    streams = []

    def tracked_open(*args, **kwargs):
        stream = open(*args, **kwargs)  # pylint: disable=consider-using-with,unspecified-encoding
        streams.append(stream)
        return stream

    monkeypatch.setattr(no_console, "open", tracked_open, raising=False)

    def as_pythonw():
        for name in ("stdout", "stderr", "stdin"):
            monkeypatch.setattr(sys, name, None)

    yield as_pythonw, hidden
    for stream in streams:
        stream.close()


def test_without_console_outputs_go_to_a_dated_log(windowless, tmp_path):
    as_pythonw, hidden = windowless
    as_pythonw()
    logs = tmp_path / "logs"
    assert no_console.start(logs) is True
    log = logs / f"console_{time.strftime('%Y%m%d')}.log"
    assert no_console.active() and no_console.log_path() == log
    assert hidden == [True]  # commandes console sans fenêtre
    print("🚀 MY PERSONAL AI LAUNCHER UNIFIÉ")
    print("erreur", file=sys.stderr)
    assert sys.stdin.read() == ""  # une lecture rend la fin du fichier
    text = log.read_text(encoding="utf-8")
    assert "lancement sans console" in text and f"pid {os.getpid()}" in text
    assert text.endswith("🚀 MY PERSONAL AI LAUNCHER UNIFIÉ\nerreur\n")
    # Un second appel ne rouvre rien
    assert no_console.start(logs) is True and hidden == [True]


def test_log_appends_one_launch_after_the_other(windowless, tmp_path):
    windowless[0]()
    logs = tmp_path / "logs"
    logs.mkdir()
    log = logs / f"console_{time.strftime('%Y%m%d')}.log"
    log.write_text("lancement précédent\n", encoding="utf-8")
    no_console.start(logs)
    print("ce lancement")
    text = log.read_text(encoding="utf-8")
    assert text.startswith("lancement précédent\n") and text.endswith("ce lancement\n")


def test_an_unwritable_logs_folder_does_not_stop_the_launch(windowless, tmp_path):
    windowless[0]()
    blocked = tmp_path / "logs"
    blocked.write_text("un fichier, pas un dossier", encoding="utf-8")
    assert no_console.start(blocked) is True
    assert no_console.log_path() is None
    print("perdu, sans planter")  # sys.stdout n'est plus None


def test_errors_show_in_a_dialog_with_the_log_file(_fresh_state, windowless, tmp_path):
    windowless[0]()
    no_console.start(tmp_path / "logs")
    assert no_console.show_error("Python 3.15 n'est pas pris en charge") is True
    assert no_console.show_error("Dépendances non installées", warning=True) is True
    assert no_console.wait_for_dismiss("Fermez ce message pour quitter My_AI.") is True
    (error, error_icon), (warning, warning_icon), (info, info_icon) = _fresh_state
    log = (tmp_path / "logs" / f"console_{time.strftime('%Y%m%d')}.log").resolve()
    assert error.startswith("Python 3.15 n'est pas pris en charge\n\n") and str(log) in error
    assert str(log) in warning and info == "Fermez ce message pour quitter My_AI."
    assert (error_icon, warning_icon, info_icon) == (0x10, 0x30, 0x40)


def test_a_crash_shows_a_dialog_after_its_trace(_fresh_state, windowless, tmp_path):
    windowless[0]()
    traces = []
    sys.excepthook = lambda kind, value, _tb: traces.append((kind, str(value)))
    no_console.start(tmp_path / "logs")
    sys.excepthook(RuntimeError, RuntimeError("port 5180 pris"), None)
    assert traces == [(RuntimeError, "port 5180 pris")]  # trace dans le fichier, d'abord
    assert len(_fresh_state) == 1 and "port 5180 pris" in _fresh_state[0][0]
    # Ctrl+C n'est pas une panne
    sys.excepthook(KeyboardInterrupt, KeyboardInterrupt(), None)
    assert len(_fresh_state) == 1


# ── Commandes lancées ───────────────────────────────────────────────────────


@pytest.fixture(name="popen")
def popen_fixture(monkeypatch):
    """subprocess.Popen qui ne lance rien : options reçues, une fois enveloppé."""
    calls = []

    def recorded_init(self, *args, **kwargs):
        self._child_created = False  # pour Popen.__del__
        flags = kwargs.get("creationflags", args[13] if len(args) > 13 else 0)
        calls.append((flags, {name: kwargs.get(name) for name in ("stdin", "stdout", "stderr")}))

    monkeypatch.setattr(subprocess.Popen, "__init__", recorded_init)
    assert no_console.hide_child_consoles() is True
    assert no_console.hide_child_consoles() is True  # pas enveloppé deux fois
    return calls


@pytest.mark.skipif(not IS_WINDOWS, reason="CREATE_NO_WINDOW : Windows seulement")
def test_child_commands_get_no_console_window_unless_they_ask(popen):
    subprocess.Popen(["taskkill", "/F", "/IM", "ollama.exe"], stdout=subprocess.DEVNULL)
    subprocess.Popen(["ssh", "-R", "80:localhost:5180"], creationflags=CREATE_NEW_PROCESS_GROUP)
    subprocess.Popen(["cmd"], creationflags=CREATE_NEW_CONSOLE)  # console voulue
    subprocess.Popen(["x"], *[None] * 12, CREATE_NEW_CONSOLE)  # creationflags positionnel
    assert [flags for flags, _std in popen] == [
        no_console.CREATE_NO_WINDOW,
        CREATE_NEW_PROCESS_GROUP | no_console.CREATE_NO_WINDOW,
        CREATE_NEW_CONSOLE, CREATE_NEW_CONSOLE,
    ]


@pytest.mark.skipif(not IS_WINDOWS, reason="CREATE_NO_WINDOW : Windows seulement")
def test_unredirected_commands_write_to_the_log(popen):
    log = object()  # fichier des sorties d'un lancement sans console
    no_console._STATE["stream"] = log
    subprocess.Popen(["ollama", "list"])
    subprocess.Popen(["ollama", "list"], stdout=subprocess.PIPE)  # redirigée : intacte
    subprocess.Popen(["cmd"], creationflags=CREATE_NEW_CONSOLE)  # sa propre console
    assert [std for _flags, std in popen] == [
        {"stdin": subprocess.DEVNULL, "stdout": log, "stderr": log},
        {"stdin": None, "stdout": subprocess.PIPE, "stderr": None},
        {"stdin": None, "stdout": None, "stderr": None},
    ]


def test_no_change_to_commands_elsewhere(monkeypatch):
    monkeypatch.setattr(no_console, "IS_WINDOWS", False)
    original = subprocess.Popen.__init__
    assert no_console.hide_child_consoles() is False
    assert subprocess.Popen.__init__ is original


# ── Vrai lancement sans console (pythonw) ───────────────────────────────────


CHILD = (
    "import os, subprocess, sys\n"
    "from pathlib import Path\n"
    "from utils import no_console\n"
    # Jamais de vraie boîte de dialogue dans les tests
    "no_console._message_box = lambda message, icon: print('BOÎTE', message) or True\n"
    "active = no_console.start(Path(sys.argv[1]))\n"
    "print('actif', active, no_console.log_path().name)\n"
    "print('é ✓ 🤖', flush=True)\n"
    # Ce qu'écrit une bibliothèque en C, sur le descripteur 2
    "os.write(2, 'écrit en C\\n'.encode('utf-8'))\n"
    # Commande console : sans fenêtre, et ses sorties dans le même fichier
    "python = Path(sys.executable).with_name('python.exe')\n"
    "subprocess.run([str(python), '-c', 'import ctypes, sys; "
    "print(\"fenêtre de la console :\", ctypes.windll.kernel32.GetConsoleWindow()); "
    "print(\"erreur de la commande\", file=sys.stderr)'], check=True)\n"
    # Sortie standard redirigée seule : la sortie d'erreur reste celle du processus
    "subprocess.run([str(python), '-c', 'import sys; print(\"jetée\"); "
    "print(\"erreur gardée\", file=sys.stderr)'], stdout=subprocess.DEVNULL, check=True)\n"
    "print('fin')\n"
)


def test_a_real_windowless_launch_logs_everything_and_opens_no_console(tmp_path):
    executable = pythonw()
    logs = tmp_path / "logs"
    process = subprocess.Popen([str(executable), "-c", CHILD, str(logs)], cwd=PROJECT_ROOT)
    assert process.wait(timeout=120) == 0
    block = launch_block(logs / f"console_{time.strftime('%Y%m%d')}.log", process.pid)
    assert f"actif True console_{time.strftime('%Y%m%d')}.log\né ✓ 🤖\n" in block
    assert "écrit en C\n" in block
    # CREATE_NO_WINDOW : la commande a une console, mais sans fenêtre
    assert "fenêtre de la console : 0\n" in block
    assert "erreur de la commande\n" in block
    assert "erreur gardée\n" in block and "jetée" not in block
    assert block.endswith("fin\n") and "BOÎTE" not in block
