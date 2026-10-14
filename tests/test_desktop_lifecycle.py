"""
Tests du cycle de vie de l'appli desktop web (interfaces/desktop/lifecycle.py)

Le lanceur est simulé : on vérifie l'ordre des étapes de launch_unified.py,
que rien ne touche au moteur avant la fin du placement, que l'écran de
chargement reçoit chaque étape (et le calibrage), qu'un Ollama arrêté
s'affiche au lieu de laisser la fenêtre sur l'écran de chargement, et que la
session du dernier lancement se rouvre.
"""

import time
from types import SimpleNamespace

import pytest

import interfaces.onboarding as onboarding
from core.chat_service import ChatService
from interfaces.desktop import lifecycle
from interfaces.desktop.lifecycle import OLLAMA_FAILED, DesktopApp, DesktopState
from test_chat_service import FakeEngine, FakeFileProcessor  # pylint: disable=import-error


class FakeLauncher:
    """Module launch_unified simulé : note l'ordre de ses étapes."""

    def __init__(self, ollama_running=True):
        self.calls = []
        self.ollama_running = ollama_running

    def prefetch_in_background(self):
        self.calls.append("prefetch")

    def _ensure_ollama_parallel(self):
        self.calls.append("ollama")

    def _ollama_is_running(self):
        return self.ollama_running

    def _port_is_free(self):
        return not self.ollama_running

    def sync_custom_model(self):
        self.calls.append("model")

    def ensure_best_placement(self, restart, on_progress=None):
        assert restart == self._restart_ollama
        self.calls.append("placement")
        on_progress("🔍 Recherche du meilleur emplacement pour le modèle 'my_ai'…")
        on_progress("• Processeur : lecture 70 tok/s, écriture 11,4 tok/s")
        return "gpu"

    def _restart_ollama(self, _env):
        return True

    @staticmethod
    def placement_label():
        return "modèle sur le GPU, contexte en 8 bits"


class FakeConfig:
    """core.config.Config : Relay et scheduler désactivés."""

    @staticmethod
    def get_section(name):
        return {"relay": {"auto_start": False}, "scheduler": {"enabled": False}}.get(name, {})

    @staticmethod
    def get(_key, default=None):
        return default


class TestApp(DesktopApp):
    """DesktopApp dont le moteur est simulé (AIEngine charge des modèles)."""

    __test__ = False  # pas une classe de tests pour pytest

    def __init__(self, launcher, tmp_path, **kwargs):
        super().__init__(launcher, headless=True,
                         state=DesktopState(tmp_path / ".desktop_state.json"), **kwargs)
        self._tmp_path = tmp_path

    def _start_engine(self):
        self._launcher.calls.append("engine")
        self.config = FakeConfig()
        self.engine = FakeEngine(self._tmp_path / "workspaces")
        self.chat = ChatService(
            self.engine, self.bus.publish, file_processor=FakeFileProcessor(),
            on_session_change=lambda session_id: self.state.set("current_session", session_id),
        )
        self.chat.start()

    def preload_voice(self):
        # Les vrais modules du micro (faster-whisper, torch) restent hors des tests
        self._launcher.calls.append("voice")


@pytest.fixture(autouse=True)
def _no_onboarding(monkeypatch):
    """L'assistant est déjà passé (sans appel à Ollama)."""
    monkeypatch.setattr(onboarding, "should_run", lambda: False)


def wait_ready(app, timeout=10.0):
    """Attend la fin des étapes de lancement."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        if app.status()["state"] in ("ready", "error"):
            return app.status()
        time.sleep(0.02)
    raise AssertionError(f"Lancement inachevé : {app.status()}")


@pytest.fixture(name="started")
def started_fixture(tmp_path):
    """Appli démarrée (vrai serveur local), arrêtée en fin de test."""
    apps = []

    def start(launcher=None, prepare=None):
        app = TestApp(launcher or FakeLauncher(), tmp_path)
        events = []
        app.bus.subscribe(events.append)
        if prepare is not None:
            prepare(app)
        app.start()
        apps.append(app)
        return SimpleNamespace(app=app, events=events, status=wait_ready(app))

    yield start
    for app in apps:
        app.shutdown()


def wait_state(app, state, timeout=10.0):
    """Attend un état du lancement (onboarding…)."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        if app.status()["state"] == state:
            return
        time.sleep(0.02)
    raise AssertionError(f"État {state} jamais atteint : {app.status()}")


def test_first_launch_waits_for_the_wizard(tmp_path, monkeypatch):
    monkeypatch.setattr(onboarding, "should_run", lambda: True)
    app = TestApp(FakeLauncher(), tmp_path)
    app.headless = False  # l'assistant ne s'affiche que dans la fenêtre
    app.start()
    try:
        wait_state(app, "onboarding")
        # Ni my_ai ni placement avant la fin de l'assistant (ordre du lanceur)
        assert app._launcher.calls == ["prefetch", "ollama"]
        time.sleep(0.2)
        assert app.status()["state"] == "onboarding"
        app.first_launch.finish()  # « Démarrer My_AI »
        assert wait_ready(app)["state"] == "ready"
        assert app._launcher.calls[:5] == ["prefetch", "ollama", "model", "placement", "engine"]
    finally:
        app.shutdown()


def test_wizard_is_skipped_without_a_window(started, monkeypatch):
    monkeypatch.setattr(onboarding, "should_run", lambda: True)
    assert started().status["state"] == "ready"


def test_closing_during_the_wizard_stops_the_launch(tmp_path, monkeypatch):
    monkeypatch.setattr(onboarding, "should_run", lambda: True)
    app = TestApp(FakeLauncher(), tmp_path)
    app.headless = False
    app.start()
    wait_state(app, "onboarding")
    app.shutdown()
    time.sleep(0.5)
    assert "engine" not in app._launcher.calls


def test_launch_steps_follow_the_launcher_order(started):
    run = started()

    # Une fois prête, l'appli prépare le micro (Tk l'importait en créant l'interface)
    assert run.app._launcher.calls == ["prefetch", "ollama", "model", "placement", "engine",
                                       "voice"]
    assert run.status["state"] == "ready"
    assert run.status["placement"] == "modèle sur le GPU, contexte en 8 bits"
    steps = []
    for event in run.events:
        step = event["payload"].get("step")
        if event["type"] == "engine.status" and (not steps or steps[-1] != step):
            steps.append(step)
    assert steps == ["prefetch", "ollama", "onboarding", "model", "placement", "engine",
                     "services", "ready"]
    details = [e["payload"]["detail"] for e in run.events
               if e["type"] == "engine.status" and e["payload"]["detail"]]
    assert details[0].startswith("🔍 Recherche du meilleur emplacement")


def test_window_url_carries_the_token_in_its_fragment(started):
    run = started()
    url = run.app.url
    assert url.startswith(f"http://127.0.0.1:{run.app.server.port}/#token=")
    assert url.endswith(run.app.token)


def test_stopped_ollama_is_shown_instead_of_the_loading_screen(started):
    run = started(FakeLauncher(ollama_running=False))

    assert run.status["error"] == OLLAMA_FAILED and run.status["ollama"] is False
    errors = [e for e in run.events
              if e["type"] == "engine.status" and e["payload"]["error"] == OLLAMA_FAILED]
    # Signalé dès l'étape d'Ollama, avant le moteur
    assert errors[0]["payload"]["step"] == "ollama"
    # Comme dans Tk, l'appli démarre quand même
    assert run.status["state"] == "ready"


def test_last_session_is_reopened_at_launch(started, tmp_path):
    previous = FakeEngine(tmp_path / "workspaces")
    session_id = previous.session_manager.create_workspace("Session d'hier")
    state = previous.session_manager.load_workspace(session_id)
    state["conversation_history"] = [
        {"text": "Bonjour", "is_user": True, "timestamp": "2026-10-11 18:00:00", "type": "text",
         "attachments": [], "image_path": None, "mid": "m1"},
        {"text": "Bonjour !", "is_user": False, "timestamp": "2026-10-11 18:00:05",
         "type": "text", "mid": "m2"},
    ]
    previous.session_manager.save_workspace(session_id, state)

    run = started(prepare=lambda app: app.state.set("current_session", session_id))
    snapshot = run.app.chat.snapshot()
    assert snapshot["conversation_id"] == session_id
    assert [m["text"] for m in snapshot["messages"]] == ["Bonjour", "Bonjour !"]
    assert run.app.engine.local_ai.local_llm.conversation_history[0]["content"] == "Bonjour"


def test_missing_session_is_forgotten(started):
    run = started(prepare=lambda app: app.state.set("current_session", "disparue-1234"))
    assert run.app.chat.snapshot()["conversation_id"] is None
    assert run.app.state.get("current_session") is None


def test_shutdown_stops_the_server(started):
    run = started()
    app = run.app
    app.shutdown()
    assert app._closed.is_set()  # pylint: disable=protected-access
    app.shutdown()  # sans effet la seconde fois


def test_desktop_state_survives_a_broken_file(tmp_path):
    path = tmp_path / ".desktop_state.json"
    path.write_text("{pas du json", encoding="utf-8")
    state = DesktopState(path)
    assert state.get("current_session") is None
    state.set("current_session", "abc")
    assert DesktopState(path).get("current_session") == "abc"


def test_lifecycle_module_never_imports_tkinter():
    import sys  # pylint: disable=import-outside-toplevel

    assert lifecycle.__name__ in sys.modules
    for name in ("interfaces.desktop.lifecycle", "interfaces.desktop.server",
                 "interfaces.desktop.events", "core.chat_service"):
        source = sys.modules[name].__file__
        with open(source, encoding="utf-8") as fh:
            text = fh.read()
        assert "tkinter" not in text and "customtkinter" not in text
