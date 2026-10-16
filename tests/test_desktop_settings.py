"""
Tests des Réglages et de l'assistant de premier lancement
(interfaces/desktop/model_setup.py, settings.py, api_settings.py)

Les fonctions d'interfaces/onboarding.py sont remplacées par FakeSetup : on
vérifie le comportement des fenêtres Tk (settings_panel.py, OnboardingWizard)
repris par le serveur, sans Ollama ni écriture dans config.yaml.
"""

import threading
import time
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from interfaces.desktop.events import EventBus, validate_event
from interfaces.desktop.model_setup import FirstLaunch, ModelJobError, ModelJobs, OllamaSetup
from interfaces.desktop.server import DesktopServer
from interfaces.desktop.settings import SettingsError, SettingsService
from test_desktop_server import AUTH, BASE, PORT, FakeApp  # pylint: disable=import-error


class FakeSetup(OllamaSetup):
    """Ollama, Modelfile et config.yaml simulés, en mémoire."""

    def __init__(self):
        self.reachable = True
        self.installed = ["qwen3.5:4b", "my_ai:latest", "llava:latest"]
        self.base = "qwen3.5:4b"
        self.config = {"temperature": 0.7, "num_ctx": 32768, "timeout": 1200, "language": "fr",
                       "languages": ["fr", "en", "es"], "relay_auto_start": False}
        self.flags = {}
        self.done = False
        self.forgotten = False
        self.calls = []
        self.fail = None  # étape en échec : « pull », « create »
        self.gate = None  # threading.Event qui retient le téléchargement

    def values(self):
        return dict(self.config)

    def model_choices(self):
        return ["qwen3.5:2b", "qwen3.5:4b", "qwen3.5:9b"]

    def ollama_reachable(self):
        return self.reachable

    def installed_models(self):
        return list(self.installed)

    def base_model(self):
        return self.base

    def pull(self, name, on_progress, on_log):
        self.calls.append(("pull", name))
        if self.gate is not None:
            self.gate.wait(5)
        on_log("pulling manifest")
        on_progress(0.5, "pulling 2f5d…")
        if self.fail == "pull":
            raise RuntimeError("manifest introuvable")
        on_progress(1.0, "pulling 2f5d…")

    def apply_base(self, base):
        self.calls.append(("apply", base))
        self.base = base

    def create_custom_model(self, on_log):
        self.calls.append(("create",))
        if self.fail == "create":
            raise RuntimeError("ollama create a échoué.")
        on_log("success")

    def save_generation(self, temperature, num_ctx, timeout):
        self.config.update(temperature=temperature, num_ctx=num_ctx, timeout=timeout)

    def set_flag(self, name, value):
        self.flags[name] = value

    def mark_done(self):
        self.done = True

    def forget_done(self):
        self.forgotten = True

    def hardware(self):
        self.calls.append(("hardware",))
        return {"ram_gb": 15.7, "vram_gb": 6.0, "cpu_cores": 14, "recommended": "qwen3.5:4b"}


def wait_until(predicate, timeout=5.0):
    """Attend qu'une condition devienne vraie (fils de travail)."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        if predicate():
            return
        time.sleep(0.01)
    raise AssertionError("condition jamais remplie")


def of_type(events, event_type):
    return [event["payload"] for event in events if event["type"] == event_type]


@pytest.fixture(name="models")
def models_fixture():
    """Travaux sur les modèles, sur Ollama simulé ; événements validés."""
    bus = EventBus()
    events = []
    bus.subscribe(events.append)
    setup = FakeSetup()
    jobs = ModelJobs(setup, bus.publish)
    yield SimpleNamespace(setup=setup, jobs=jobs, events=events, bus=bus)
    for event in events:
        validate_event(event)


def done(models, count=1):
    wait_until(lambda: len(of_type(models.events, "models.done")) >= count)
    return of_type(models.events, "models.done")[-1]


# ── Travaux sur les modèles ─────────────────────────────────────────────────


def test_pull_reports_progress_log_and_end(models):
    models.jobs.pull("  llava:7b ")

    assert done(models) == {"action": "pull", "name": "llava:7b", "ok": True,
                            "message": "✅ llava:7b téléchargé"}
    lines = [payload["line"] for payload in of_type(models.events, "models.log")]
    assert lines == ["📥 Téléchargement de llava:7b…", "pulling manifest",
                     "✅ llava:7b téléchargé."]
    assert of_type(models.events, "models.progress")[0] == {"fraction": 0.5,
                                                             "status": "pulling 2f5d…"}
    assert {"level": "success", "message": "✅ llava:7b téléchargé"} in of_type(
        models.events, "notification")
    # Panneau rouvert : le journal se relit
    status = models.jobs.status()
    assert status["running"] is False and status["ok"] is True and status["log"] == lines


def test_one_job_at_a_time_and_clear_refusals(models):
    models.setup.gate = threading.Event()
    models.jobs.pull("qwen3.5:9b")
    with pytest.raises(ModelJobError, match="déjà en cours"):
        models.jobs.apply("qwen3.5:9b")
    models.setup.gate.set()
    done(models)

    with pytest.raises(ModelJobError, match="Entrez un nom de modèle"):
        models.jobs.pull("  ")
    models.setup.reachable = False
    with pytest.raises(ModelJobError, match="Ollama n'est pas joignable."):
        models.jobs.pull("qwen3.5:2b")


def test_apply_regenerates_my_ai_or_says_why_not(models):
    models.jobs.apply("llava:latest")
    assert done(models)["ok"] is True
    assert models.setup.calls == [("apply", "llava:latest"), ("create",)]
    lines = [payload["line"] for payload in of_type(models.events, "models.log")]
    assert lines == ["🔧 Modelfile FROM → llava:latest", "🏗️  Création du modèle 'my_ai'…",
                     "success", "✅ Modèle 'my_ai' régénéré."]

    models.setup.fail = "create"
    models.jobs.apply("qwen3.5:4b")
    failed = done(models, 2)
    assert failed["ok"] is False and failed["message"] == "ollama create a échoué."
    assert of_type(models.events, "models.log")[-1]["line"] == "❌ Erreur : ollama create a échoué."
    assert of_type(models.events, "notification")[-1] == {
        "level": "error", "message": "❌ Échec de la régénération"}


# ── Assistant de premier lancement ──────────────────────────────────────────


def test_wizard_installs_then_waits_for_start(models):
    wizard = FirstLaunch(models.setup, models.jobs)
    info = wizard.info()
    assert info["recommended"] == "qwen3.5:4b" and info["ollama"] is True
    assert info["choices"] == ["qwen3.5:2b", "qwen3.5:4b", "qwen3.5:9b"]
    wizard.info()
    assert models.setup.calls.count(("hardware",)) == 1  # nvidia-smi : une seule fois

    with pytest.raises(ModelJobError, match="Modèle inconnu"):
        wizard.install("llama:70b")
    wizard.install("qwen3.5:9b")
    assert done(models)["action"] == "install"
    assert models.setup.done is True and models.setup.base == "qwen3.5:9b"
    assert of_type(models.events, "models.log")[-1]["line"] == (
        "🎉 Configuration terminée ! Vous pouvez lancer My_AI.")
    # Pas de toast : l'assistant affiche lui-même son état
    assert not of_type(models.events, "notification")

    assert wizard.released is False  # « Démarrer My_AI » reste à cliquer
    wizard.finish()
    assert wizard.wait(lambda: False) is True


def test_wizard_skip_marks_it_done_and_closing_stops_the_wait(models):
    wizard = FirstLaunch(models.setup, models.jobs)
    wizard.skip()
    assert models.setup.done is True and wizard.released is True

    other = FirstLaunch(models.setup, models.jobs)
    started = time.time()
    assert other.wait(lambda: True, poll=0.01) is False
    assert time.time() - started < 1


# ── Réglages ────────────────────────────────────────────────────────────────


def test_settings_read_models_without_my_ai():
    setup = FakeSetup()
    settings = SettingsService(setup, lambda: None)
    snapshot = settings.snapshot()
    assert snapshot["generation"] == {"temperature": 0.7, "num_ctx": 32768, "timeout": 1200}
    assert snapshot["num_ctx_choices"] == [2048, 4096, 8192, 16384, 32768, 65536]
    assert snapshot["languages"] == ["fr", "en", "es"] and snapshot["base_model"] == "qwen3.5:4b"
    setup.config["num_ctx"] = 12000
    assert 12000 in settings.snapshot()["num_ctx_choices"]

    models = settings.models()
    assert models["bases"] == ["qwen3.5:4b", "llava:latest"]
    assert "my_ai:latest" in models["installed"]
    setup.reachable = False
    assert settings.models() == {"ollama": False, "installed": [], "bases": ["qwen3.5:4b"],
                                 "base_model": "qwen3.5:4b"}


def test_generation_params_are_bounded_and_applied_to_the_running_model():
    setup = FakeSetup()
    llm = SimpleNamespace(gen_temperature=0.7, gen_num_ctx=32768, timeout=1200)
    engine = SimpleNamespace(local_ai=SimpleNamespace(local_llm=llm))
    settings = SettingsService(setup, lambda: engine)

    saved = settings.save_generation(1.734, 8192, 5)
    assert saved == {"temperature": 1.0, "num_ctx": 8192, "timeout": 30}
    assert (llm.gen_temperature, llm.gen_num_ctx, llm.timeout) == (1.0, 8192, 30)
    assert setup.config["timeout"] == 30
    assert settings.save_generation(0.456, 4096, 99999)["timeout"] == 7200
    with pytest.raises(SettingsError):
        settings.save_generation(0.5, 100, 600)


def test_flags_and_wizard_restart():
    setup = FakeSetup()
    settings = SettingsService(setup, lambda: None)
    settings.set_flag("language.default", "en")
    settings.set_flag("relay.auto_start", 1)
    assert setup.flags == {"language.default": "en", "relay.auto_start": True}
    with pytest.raises(SettingsError, match="Langue non prise en charge"):
        settings.set_flag("language.default", "xx")
    # La lecture automatique a sa propre route (voice.py)
    with pytest.raises(SettingsError, match="Réglage inconnu"):
        settings.set_flag("ui.tts_autoread", True)
    settings.restart_onboarding()
    assert setup.forgotten is True


# ── Routes ──────────────────────────────────────────────────────────────────


class SettingsApp(FakeApp):
    """FakeApp avec les services des Réglages et de l'assistant."""

    def __init__(self, bus, setup):
        super().__init__(None, bus)
        self.model_jobs = ModelJobs(setup, bus.publish)
        self.first_launch = FirstLaunch(setup, self.model_jobs)
        self.settings = SettingsService(setup, lambda: None)

    def notify(self, level, message):
        self.bus.publish("notification", {"level": level, "message": message})


@pytest.fixture(name="routes")
def routes_fixture():
    bus = EventBus()
    events = []
    bus.subscribe(events.append)
    setup = FakeSetup()
    server = DesktopServer(SettingsApp(bus, setup))
    server.port = PORT
    client = TestClient(server.fastapi, base_url=BASE)
    return SimpleNamespace(client=client, setup=setup, events=events)


def test_settings_routes(routes):
    client = routes.client
    assert client.get("/api/settings").status_code == 401
    assert client.get("/api/settings", headers=AUTH).json()["language"] == "fr"
    assert client.get("/api/settings/models", headers=AUTH).json()["bases"] == [
        "qwen3.5:4b", "llava:latest"]

    routes.setup.gate = threading.Event()
    started = client.post("/api/settings/models/pull", json={"name": "llava:7b"}, headers=AUTH)
    assert started.status_code == 200 and started.json()["job"]["running"] is True
    busy = client.post("/api/settings/models/apply", json={"name": "llava:7b"}, headers=AUTH)
    assert busy.status_code == 409 and "déjà en cours" in busy.json()["detail"]
    routes.setup.gate.set()
    wait_until(lambda: not client.get("/api/settings/models/job",
                                      headers=AUTH).json()["job"]["running"])

    saved = client.put("/api/settings/generation", headers=AUTH,
                       json={"temperature": 0.35, "num_ctx": 16384, "timeout": 900})
    assert saved.json() == {"temperature": 0.35, "num_ctx": 16384, "timeout": 900}
    assert {"level": "success", "message": "💾 Paramètres enregistrés"} in of_type(
        routes.events, "notification")
    flags = client.put("/api/settings/flags", headers=AUTH,
                       json={"name": "relay.auto_start", "value": True})
    assert flags.status_code == 200 and routes.setup.flags == {"relay.auto_start": True}
    bad = client.put("/api/settings/flags", headers=AUTH, json={"name": "x", "value": 1})
    assert bad.status_code == 409
    assert client.post("/api/settings/onboarding/restart", headers=AUTH).json() == {"ok": True}
    assert routes.setup.forgotten is True


def test_onboarding_routes(routes):
    client = routes.client
    info = client.get("/api/onboarding", headers=AUTH).json()
    assert info["recommended"] == "qwen3.5:4b" and info["job"] is None
    assert client.post("/api/onboarding/install", json={"name": "qwen3.5:2b"},
                       headers=AUTH).status_code == 200
    wait_until(lambda: routes.setup.done)
    assert client.post("/api/onboarding/finish", headers=AUTH).json() == {"ok": True}
    unknown = client.post("/api/onboarding/install", json={"name": "x"}, headers=AUTH)
    assert unknown.status_code == 409
