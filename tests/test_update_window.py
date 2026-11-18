"""
Tests de la fenêtre d'attente des mises à jour d'avant l'appli (utils/update_window.py)

Lancé sans console (épingle de la barre des tâches), My_AI installe les
dépendances ajoutées à requirements.txt sous cette fenêtre. Ni pip ni vraie
fenêtre ici : Tk tourne, sa fenêtre masquée, et pip est simulé.
"""

# pylint: disable=protected-access

import os
import subprocess
import sys
import threading
from pathlib import Path

import pytest
import yaml

from core import i18n
from utils import no_console, update_window

PROJECT_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(autouse=True)
def _french(monkeypatch):
    i18n.reset_for_tests()
    i18n.set_language("fr")
    # Le régime DPI ne se fixe qu'une fois par processus : pas celui de pytest
    monkeypatch.setattr(update_window, "_per_monitor_dpi", lambda: None)
    yield
    i18n.reset_for_tests()


# ── Langue de l'appli, sans PyYAML ──────────────────────────────────────────


@pytest.mark.parametrize("text, expected", [
    ('language:\n  auto_detect: true\n  default: "es"\n  supported: ["fr", "es"]\n', "es"),
    ("language:\r\n  default: 'de'\r\n", "de"),  # fins de ligne Windows
    ("language:\n\n  # commentaire\n  default: ja\nvoice:\n  default: fr\n", "ja"),
    ("llm:\n  local:\n    default_model: qwen3.5:4b\nlanguage:\n  default: \"ko\"", "ko"),
    ("voice:\n  default: fr\n", None),  # pas de bloc language
    ("language:\n  auto_detect: true\nvoice:\n  default: fr\n", None),  # pas de default
])
def test_app_language_is_read_without_pyyaml(text, expected):
    assert update_window.config_language(text) == expected


def test_real_config_gives_the_language_pyyaml_reads():
    text = (PROJECT_ROOT / "config.yaml").read_text(encoding="utf-8")
    assert update_window.config_language(text) == yaml.safe_load(text)["language"]["default"]


def test_texts_of_the_window_load_no_pyyaml():
    """PyYAML chargé, pip ne pourrait plus remplacer son module compilé (Windows)."""
    code = (
        "import sys\n"
        "from utils import update_window\n"
        "update_window._use_app_language()\n"
        "from core.i18n import tr\n"
        "print(tr('launch.dependencies'))\n"
        "print('yaml' in sys.modules)\n"
    )
    run = subprocess.run([sys.executable, "-c", code], cwd=PROJECT_ROOT, capture_output=True,
                         encoding="utf-8", env={**os.environ, "PYTHONIOENCODING": "utf-8"},
                         timeout=120, check=False)
    assert run.returncode == 0, run.stderr[-3000:]
    title, yaml_loaded = run.stdout.splitlines()
    assert title == i18n.tr("launch.dependencies", _lang=update_window.config_language(
        (PROJECT_ROOT / "config.yaml").read_text(encoding="utf-8")))
    assert yaml_loaded == "False"


def test_pip_lines_are_trimmed():
    assert update_window.last_line("  Downloading   rapidocr-3.9.2.whl (12 MB)\n") == \
        "Downloading rapidocr-3.9.2.whl (12 MB)"
    assert len(update_window.last_line("x" * 300)) == update_window.LINE_LIMIT
    assert update_window.last_line("x" * 300).endswith("…")


# ── Fenêtre (vrai Tk, masqué) ───────────────────────────────────────────────


class Shown:
    """Texte du détail de la fenêtre (StringVar de Tk), valeurs successives."""

    def __init__(self):
        self.values = []

    def set(self, value):
        self.values.append(value)


@pytest.fixture(name="hidden_tk")
def hidden_tk_fixture(monkeypatch):
    """Vrai Tk (boucle, after, quit, destroy), fenêtre masquée : rien ne s'affiche."""
    tkinter = pytest.importorskip("tkinter")
    try:
        tkinter.Tk().destroy()
    except tkinter.TclError as exc:
        pytest.skip(f"Tk sans écran : {exc}")
    shown = Shown()
    built = []

    def build(root, _tkinter, _ttk, title, detail):
        root.withdraw()
        built.append((title, detail))
        return shown

    monkeypatch.setattr(update_window, "_build", build)
    return shown, built


def test_work_runs_in_a_thread_under_the_window(hidden_tk):
    shown, built = hidden_tk
    release = threading.Event()

    def work(report):
        report("Collecting rapidocr>=3.9.2")
        report("  Downloading rapidocr-3.9.2-py3-none-any.whl (12 MB)")
        release.wait(5)
        return threading.current_thread().name

    threading.Timer(0.4, release.set).start()
    result = update_window.run_in_window(work, "Mise à jour des dépendances…",
                                         "Installation : rapidocr>=3.9.2")
    assert result == "update-window"  # pas le fil de Tk
    assert built == [("Mise à jour des dépendances…", "Installation : rapidocr>=3.9.2")]
    # Le détail garde les paquets et montre la dernière ligne de pip
    assert shown.values[-1] == ("Installation : rapidocr>=3.9.2\n"
                                "Downloading rapidocr-3.9.2-py3-none-any.whl (12 MB)")


def test_an_error_of_the_work_reaches_the_caller(hidden_tk):
    def work(_report):
        raise RuntimeError("pip introuvable")

    with pytest.raises(RuntimeError, match="pip introuvable"):
        update_window.run_in_window(work, "titre")


def test_without_tk_the_work_runs_without_window(monkeypatch):
    tkinter = pytest.importorskip("tkinter")

    def no_display():
        raise tkinter.TclError("no display name and no $DISPLAY environment variable")

    monkeypatch.setattr(tkinter, "Tk", no_display)
    lines = []
    assert update_window.run_in_window(lambda report: lines.append(report("x")) or 7, "t") == 7
    assert lines == [None]  # report existe, sans rien afficher


def test_a_window_that_cannot_be_built_does_not_stop_the_work(monkeypatch):
    tkinter = pytest.importorskip("tkinter")
    try:
        tkinter.Tk().destroy()
    except tkinter.TclError as exc:
        pytest.skip(f"Tk sans écran : {exc}")

    def broken(*_args):
        raise tkinter.TclError('bad window path name ".!label"')

    monkeypatch.setattr(update_window, "_build", broken)
    assert update_window.run_in_window(lambda _report: "installé", "t") == "installé"


# ── Dépendances ─────────────────────────────────────────────────────────────


@pytest.fixture(name="deps")
def deps_fixture(monkeypatch):
    """sync_requirements simulé, fenêtre et boîte de dialogue enregistrées."""
    env = {"windows": [], "errors": [], "pip": [], "failed": [], "attempt": True}

    def fake_sync(progress=None):
        if env["attempt"]:
            progress(lambda report: env["pip"].append(report("Collecting rapidocr")),
                     ["rapidocr>=3.9.2", "PyMuPDF>=1.24.3"])
        return list(env["failed"])

    def fake_window(work, title, detail):
        env["windows"].append((title, detail))
        return work(lambda line: line)

    monkeypatch.setattr(update_window, "sync_requirements", fake_sync)
    monkeypatch.setattr(update_window, "run_in_window", fake_window)
    monkeypatch.setattr(update_window, "_use_app_language", lambda: None)
    from interfaces.desktop import app_identity  # pylint: disable=import-outside-toplevel
    monkeypatch.setattr(app_identity, "set_windows_app_id", lambda: True)
    monkeypatch.setattr(no_console, "show_error",
                        lambda message, warning=False: env["errors"].append((message, warning)))
    return env


def test_dependencies_install_under_the_window(deps):
    assert update_window.sync_dependencies() == []
    assert deps["windows"] == [("Mise à jour des dépendances…",
                                "Installation : rapidocr>=3.9.2, PyMuPDF>=1.24.3")]
    assert deps["pip"] == ["Collecting rapidocr"]
    assert deps["errors"] == []


def test_a_failed_installation_is_shown_in_a_dialog(deps):
    deps["failed"] = ["rapidocr>=3.9.2"]
    assert update_window.sync_dependencies() == ["rapidocr>=3.9.2"]
    assert deps["errors"] == [(
        "Dépendances non installées : rapidocr>=3.9.2. My_AI démarre sans elles : "
        "les fonctions qui en ont besoin resteront indisponibles.", True)]


def test_no_dialog_for_a_line_that_already_failed(deps):
    """Échec d'un lancement précédent, pas de nouvel essai : rien ne s'est passé ici."""
    deps["failed"], deps["attempt"] = ["rapidocr>=3.9.2"], False
    assert update_window.sync_dependencies() == ["rapidocr>=3.9.2"]
    assert deps["windows"] == [] and deps["errors"] == []
