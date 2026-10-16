"""
Tests des tâches planifiées de la fenêtre (interfaces/desktop/schedule.py, api_schedule.py)

Le vrai SchedulerService (core/scheduler.py), sur des fichiers temporaires,
sans boucle ni notification du système ; la tâche du Planificateur de Windows
est simulée. Règles et messages du dialogue de Tk, routes, et une tâche
exécutée à travers l'exécuteur de la page Agents : son fil (D37) prend le nom
de la tâche, puis son rapport.
"""

import time
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from core.scheduler import _CRONITER_AVAILABLE, SchedulerService
from interfaces.desktop.agents import AgentsService
from interfaces.desktop.events import EventBus, validate_event
from interfaces.desktop.lifecycle import DesktopApp, DesktopState
from interfaces.desktop.schedule import (ScheduleError, ScheduleNotFound, ScheduleService,
                                         build_schedule)
from interfaces.desktop.server import DesktopServer
from test_desktop_agents import FakeOrchestrator, RelayService  # pylint: disable=import-error
from test_desktop_server import AUTH, BASE, PORT, FakeApp  # pylint: disable=import-error

AGENTS = {
    "builtin": [
        {"key": "web", "icon": "🔍", "name": "WebAgent", "desc": "Recherche", "color": "#10b981"},
        {"key": "code", "icon": "🐍", "name": "CodeAgent", "desc": "Code", "color": "#3b82f6"},
        {"key": "creative", "icon": "✨", "name": "CreativeAgent", "desc": "Créatif",
         "color": "#f59e0b"},
    ],
    "custom": [{"key": "custom_seo_1", "icon": "🧩", "name": "SEOAgent", "desc": "SEO",
                "color": "#16a34a", "custom": True}],
}

DAILY = {"type": "daily", "at": "08:00"}


class FakeExecutor:
    """Exécuteur du scheduler : la vérification « occupé » de run_now, et une exécution."""

    def __init__(self):
        self.busy = False
        self.calls = []

    # pylint: disable-next=too-many-arguments,too-many-positional-arguments
    def run_workflow(self, exec_id, task, nodes, connections, emit, image_path=None,
                     file_paths=None):
        del connections, image_path, file_paths
        self.calls.append((task, nodes))
        emit({"type": "agent_exec_end", "exec_id": exec_id, "success": True,
              "interrupted": False, "status_text": "✅ Workflow terminé (100% succès)"})


class FakeWindows:
    """Tâche du Planificateur de Windows simulée : jamais schtasks."""

    available = True

    def __init__(self, registered=False, ok=True):
        self._registered = registered
        self.ok = ok
        self.calls = []

    def registered(self):
        self.calls.append("query")
        return self._registered

    def register(self, interval):
        self.calls.append(("register", interval))
        if not self.ok:
            return False, "Accès refusé."
        self._registered = True
        return True, f"Exécution en arrière-plan activée (toutes les {interval} min)."

    def unregister(self):
        self.calls.append("unregister")
        self._registered = False
        return True, "Exécution en arrière-plan désactivée."


def make_scheduler(tmp_path, executor):
    """Le vrai SchedulerService, isolé dans tmp_path (comme tests/test_scheduler.py)."""
    return SchedulerService(executor=executor, config={
        "enabled": True, "check_interval": 5, "run_missed_on_startup": False,
        "catch_up_window_hours": 24, "max_history": 20,
        "tasks_file": str(tmp_path / "scheduled_tasks.json"),
        "output_directory": str(tmp_path / "out"),
        "lock_file": str(tmp_path / "scheduler.lock"),
        "notify_desktop": False, "notify_mobile": False,
    })


@pytest.fixture(name="sched")
def sched_fixture(tmp_path):
    bus = EventBus()
    events = []
    bus.subscribe(events.append)
    notes = []
    executor = FakeExecutor()
    scheduler = make_scheduler(tmp_path, executor)
    windows = FakeWindows()
    service = ScheduleService(lambda: scheduler, bus.publish, agents=lambda: AGENTS,
                              notify=lambda level, message: notes.append((level, message)),
                              windows=windows, background_interval=lambda: 1)
    return SimpleNamespace(service=service, scheduler=scheduler, executor=executor, bus=bus,
                           events=events, notes=notes, windows=windows, tmp_path=tmp_path)


def fields(**overrides):
    base = {"name": "Veille du matin", "task": "Résume l'actualité IA", "schedule": DAILY,
            "run_if_missed": True, "source": {"kind": "single", "agent": "web"}}
    base.update(overrides)
    return base


def changed(events):
    return [event for event in events if event["type"] == "scheduler.changed"]


# ── Planning ────────────────────────────────────────────────────────────────


def test_schedules_are_built_like_tk():
    assert build_schedule({"type": "daily", "at": ""}) == {"type": "daily", "at": "08:00"}
    assert build_schedule({"type": "daily", "at": "7:05"}) == {"type": "daily", "at": "07:05"}
    assert build_schedule({"type": "weekly", "at": "09:00", "days": [3, 0, 3, 9]}) == {
        "type": "weekly", "days": [0, 3], "at": "09:00"}
    assert build_schedule({"type": "interval", "every": "2", "unit": "heures"}) == {
        "type": "interval", "seconds": 7200}
    assert build_schedule({"type": "interval", "every": "1", "unit": "minutes"}) == {
        "type": "interval", "seconds": 60}
    assert build_schedule({"type": "cron", "expr": " 0 8 * * * "}) == {"type": "cron",
                                                                       "expr": "0 8 * * *"}
    refused = [
        ({"type": "daily", "at": "25:00"}, "❌ Heure invalide (HH:MM)."),
        ({"type": "weekly", "at": "09:00", "days": []}, "❌ Sélectionnez au moins un jour."),
        ({"type": "interval", "every": "0", "unit": "minutes"}, "❌ Intervalle invalide."),
        ({"type": "interval", "every": "x", "unit": "minutes"}, "❌ Intervalle invalide."),
        ({"type": "cron", "expr": "  "}, "❌ Expression cron requise."),
        ({"type": "mensuel"}, "❌ Type de planning inconnu."),
    ]
    for schedule, message in refused:
        with pytest.raises(ScheduleError) as error:
            build_schedule(schedule)
        assert str(error.value) == message


# ── Création et modification ────────────────────────────────────────────────


def test_a_single_agent_task_is_saved_like_tk(sched):
    task = sched.service.create(fields())
    # Agent seul : un workflow d'un nœud « n1 », comme Tk
    assert task["kind"] == "workflow" and task["nodes"] == [
        {"id": "n1", "agent_type": "web", "name": "WebAgent", "color": "#10b981", "icon": "🔍"}]
    assert task["next_run"] and task["enabled"] and task["run_if_missed"]
    listed = sched.service.list()
    view = listed["tasks"][0]
    assert view["description"] == "tous les jours à 08:00" and view["source"] == "Agent : WebAgent"
    assert listed["croniter"] == bool(_CRONITER_AVAILABLE)
    assert listed["background"] == {"available": True, "registered": False}
    assert sched.notes == [("success", "✅ Tâche planifiée enregistrée")]
    assert len(changed(sched.events)) == 1
    for event in sched.events:
        validate_event(event)


def test_workflow_and_debate_sources(sched):
    workflow = sched.service.create(fields(name="Audit", source={
        "kind": "workflow",
        "nodes": [{"id": 0, "agent_type": "code", "name": "CodeAgent"},
                  {"id": 1, "agent_type": "web", "name": "WebAgent", "color": "#10b981"}],
        "connections": [{"from": 0, "to": 1}]}))
    assert [n["id"] for n in workflow["nodes"]] == ["0", "1"]
    assert workflow["connections"] == [{"from": "0", "to": "1"}]
    debate = sched.service.create(fields(name="Débat", source={
        "kind": "debate", "agent_a": "code", "agent_b": "creative", "rounds": 2}))
    assert debate["kind"] == "debate" and debate["nodes"] == []
    assert debate["debate"] == {"agent_a": "code", "agent_b": "creative", "rounds": 2}
    sources = [task["source"] for task in sched.service.list()["tasks"]]
    assert sources == ["Workflow : 2 agents", "Débat : CodeAgent vs CreativeAgent"]


def test_creation_refuses_in_the_order_of_tk(sched):
    refused = [
        (fields(name="  "), "❌ Nom requis."),
        (fields(task=""), "❌ Tâche / sujet requis."),
        (fields(schedule={"type": "weekly", "at": "09:00", "days": []}),
         "❌ Sélectionnez au moins un jour."),
        (fields(source={"kind": "single"}), "❌ Choisissez un agent."),
        (fields(source={"kind": "single", "agent": "absent"}), "❌ Agent introuvable : absent"),
        (fields(source={"kind": "debate", "agent_a": "code"}), "❌ Choisissez deux agents."),
        (fields(source={"kind": "debate", "agent_a": "code", "agent_b": "code"}),
         "❌ Choisissez deux agents différents."),
        (fields(source={"kind": "workflow", "nodes": []}), "❌ Le canvas est vide."),
    ]
    for body, message in refused:
        with pytest.raises(ScheduleError) as error:
            sched.service.create(body)
        assert str(error.value) == message
    if _CRONITER_AVAILABLE:
        with pytest.raises(ScheduleError, match="❌ Expression cron invalide"):
            sched.service.create(fields(schedule={"type": "cron", "expr": "pas une expression"}))
    assert sched.service.list()["tasks"] == [] and sched.notes == []


def test_an_edit_keeps_the_source(sched):
    task = sched.service.create(fields())
    edited = sched.service.update(task["id"], fields(
        name="Veille du soir", task="Résume la journée",
        schedule={"type": "interval", "every": "2", "unit": "heures"}, run_if_missed=False,
        source={"kind": "debate", "agent_a": "code", "agent_b": "web"}))
    assert edited["name"] == "Veille du soir" and edited["task"] == "Résume la journée"
    assert edited["schedule"] == {"type": "interval", "seconds": 7200}
    assert edited["run_if_missed"] is False and edited["kind"] == "workflow"
    assert edited["nodes"][0]["agent_type"] == "web"
    with pytest.raises(ScheduleNotFound):
        sched.service.update("sched_absent", fields())


def test_delete_enable_and_run_now(sched):
    task = sched.service.create(fields())
    disabled = sched.service.set_enabled(task["id"], False)
    assert disabled["enabled"] is False
    assert sched.service.set_enabled(task["id"], True)["enabled"] is True
    sched.executor.busy = True
    with pytest.raises(ScheduleError, match="❌ Exécuteur occupé, réessayez."):
        sched.service.run_now(task["id"])
    sched.executor.busy = False
    with pytest.raises(ScheduleError, match="❌ Tâche introuvable"):
        sched.service.run_now("sched_absent")
    sched.service.run_now(task["id"])
    deadline = time.time() + 5
    while not sched.scheduler.history() and time.time() < deadline:
        time.sleep(0.02)
    assert sched.executor.calls == [("Résume l'actualité IA", task["nodes"])]
    assert sched.scheduler.get_task(task["id"])["last_status"] == "success"
    sched.service.delete(task["id"])
    with pytest.raises(ScheduleNotFound):
        sched.service.delete(task["id"])
    assert [note for note in sched.notes if note[1] != "✅ Tâche planifiée enregistrée"] == [
        ("success", "▶ Exécution lancée…"), ("error", "✕ Tâche supprimée")]


def test_the_background_task_of_windows(sched):
    assert sched.service.list()["background"]["registered"] is False
    sched.service.list()
    assert sched.windows.calls == ["query"]  # schtasks est lent : lu une fois
    assert sched.service.set_background(True)["registered"] is True
    assert sched.windows.calls[-1] == ("register", 1)
    assert sched.service.list()["background"]["registered"] is True
    assert sched.service.set_background(False)["registered"] is False
    sched.windows.ok = False
    failed = sched.service.set_background(True)
    assert failed == {"registered": False, "ok": False, "message": "Accès refusé."}
    assert sched.notes[-1] == ("error", "❌ Accès refusé.")
    sched.windows.available = False
    with pytest.raises(ScheduleError, match="Disponible uniquement sous Windows"):
        sched.service.set_background(True)
    assert sched.service.list()["background"] == {"available": False, "registered": False}


# ── Routes ──────────────────────────────────────────────────────────────────


def test_schedule_routes(sched):
    app = FakeApp(None, sched.bus)
    app.schedule = sched.service
    server = DesktopServer(app)
    server.port = PORT
    client = TestClient(server.fastapi, base_url=BASE)
    assert client.get("/api/schedule").status_code == 401
    created = client.post("/api/schedule/tasks", headers=AUTH, json=fields())
    task_id = created.json()["task"]["id"]
    listed = client.get("/api/schedule", headers=AUTH).json()
    assert listed["tasks"][0]["id"] == task_id
    refused = client.post("/api/schedule/tasks", headers=AUTH, json=fields(name=""))
    assert refused.status_code == 409 and refused.json()["detail"] == "❌ Nom requis."
    edited = client.put(f"/api/schedule/tasks/{task_id}", headers=AUTH,
                        json=fields(name="Autre nom"))
    assert edited.json()["task"]["name"] == "Autre nom"
    assert client.put("/api/schedule/tasks/absent", headers=AUTH,
                      json=fields()).status_code == 404
    switched = client.post(f"/api/schedule/tasks/{task_id}/enabled", headers=AUTH,
                           json={"enabled": False})
    assert switched.json()["task"]["enabled"] is False
    assert client.post(f"/api/schedule/tasks/{task_id}/run", headers=AUTH).json() == {"ok": True}
    background = client.post("/api/schedule/background", headers=AUTH, json={"enabled": True})
    assert background.json()["registered"] is True
    assert client.delete(f"/api/schedule/tasks/{task_id}", headers=AUTH).json() == {"ok": True}
    app.engine = None
    assert client.get("/api/schedule", headers=AUTH).status_code == 503


# ── Une tâche exécutée à travers la page Agents (D37) ───────────────────────


def test_a_scheduled_run_becomes_a_named_thread_with_its_report(tmp_path):
    app = DesktopApp(None, headless=True, state=DesktopState(tmp_path / "state.json"))
    events = []
    app.bus.subscribe(events.append)
    relay = RelayService(tmp_path / "custom_agents.json", FakeOrchestrator())
    agents = AgentsService(lambda: relay, app.bus.publish, runs_file=tmp_path / "runs.json",
                           find_scheduled=app._find_scheduled_task)  # pylint: disable=protected-access
    app._agents = agents  # pylint: disable=protected-access
    scheduler = make_scheduler(tmp_path, agents.executor_tap())
    app.scheduler = scheduler
    scheduler.add_listener(app._on_scheduled_result)  # pylint: disable=protected-access
    service = ScheduleService(lambda: scheduler, app.bus.publish,
                              agents=relay.list_agents, windows=FakeWindows())
    task = service.create(fields(name="Veille du matin", source={"kind": "single",
                                                                 "agent": "code"}))
    debate = service.create(fields(name="Débat du soir", task="Tabs ou espaces ?",
                                   source={"kind": "debate", "agent_a": "code",
                                           "agent_b": "debug", "rounds": 1}))
    def results():
        return [event for event in events if event["type"] == "scheduler.result"]

    deadline = time.time() + 10
    service.run_now(task["id"])
    while len(results()) < 1 and time.time() < deadline:
        time.sleep(0.02)
    service.run_now(debate["id"])
    while len(results()) < 2 and time.time() < deadline:
        time.sleep(0.02)

    runs = agents.runs()["runs"]
    assert [(run["title"], run["origin"], run["kind"]) for run in runs] == [
        ("Débat du soir", "scheduled", "debate"), ("Veille du matin", "scheduled", "agent")]
    first = agents.run(runs[1]["id"])["run"]
    report = scheduler.get_task(task["id"])["last_output_file"]
    assert first["schedule"] == {"task_id": task["id"], "name": "Veille du matin",
                                 "output_file": report}
    assert first["sections"][0]["text"].startswith("```python")
    assert agents.run(runs[0]["id"])["run"]["schedule"]["output_file"] == scheduler.get_task(
        debate["id"])["last_output_file"]
    assert "scheduler.changed" in [event["type"] for event in events]
