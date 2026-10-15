"""
Tests de la page Agents de la fenêtre (interfaces/desktop/agents.py, api_agents.py)

Le vrai AgentRelayService (relay/agent_relay.py), avec un orchestrateur et un
modèle simulés : mêmes événements que pour le mobile, repris sur le bus de la
fenêtre (texte des sections en suites), fils d'exécution gardés dans un
fichier (D33), arrêt avant et pendant l'exécution, images décrites une à une,
fichiers de workflow au format de Tk et export Markdown (D11), débats,
exécutions du téléphone et des tâches planifiées devenues des fils (D37),
statistiques, tokens/s de chaque agent, notification de fin, routes.
"""

import json
import threading
import time
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from interfaces.desktop import agents as agents_module
from interfaces.desktop.agents import (BUSY, DEBATE_BUSY, DEBATE_INTERRUPTED, DEBATE_NO_TOPIC,
                                       DEBATE_SAME_AGENT, EMPTY_TASK, EXECUTOR_BUSY, INTERRUPTED,
                                       NO_AGENT, AgentsError, AgentsService, RunNotFound,
                                       workflow_markdown)
from interfaces.desktop.events import EventBus, validate_event
from interfaces.desktop.server import DesktopServer
from relay.agent_relay import AgentRelayService
from test_chat_service import wait_for  # pylint: disable=import-error
from test_desktop_server import AUTH, BASE, PORT, FakeApp  # pylint: disable=import-error

OUTPUTS = {
    "planner": "## Plan\n1. Modèles\n2. Routes\n",
    "code": "```python\ndef somme(a, b):\n    return a + b\n```\n",
    "security": "Rien à signaler.",
    "debug": "Aucun bogue.",
}

GENERATED = """Tu es TranslatorAgent, un expert en traduction.

EXPERTISE: langues
TEMPERATURE: 0.3
SUMMARY: traduction multilingue"""


class FakeOrchestrator:
    """Orchestrateur simulé : chaque agent écrit sa réponse en petits morceaux.

    Comme LocalLLM (D17), le modèle de chaque agent garde le relevé de fin de
    flux (eval_count, eval_duration) quand la réponse va jusqu'au bout.
    """

    def __init__(self, delay=0.0, fail=()):
        self.agents = {}
        self.calls = []
        self.delay = delay
        self.fail = set(fail)
        self.started = threading.Event()

    def execute_single_task_stream(self, agent_type, task, context=None, on_token=None):
        del context
        self.calls.append((agent_type, task))
        self.started.set()
        text = OUTPUTS.get(agent_type, f"Réponse de {agent_type}")
        for start in range(0, len(text), 3):
            if on_token(text[start:start + 3]) is False:
                return {"success": False, "error": "interrompu", "result": ""}
            if self.delay:
                time.sleep(self.delay)
        # 50 jetons en 2 s : 25 tokens/s
        llm = SimpleNamespace(last_stream_stats={"eval_count": 50, "eval_duration": 2_000_000_000,
                                                 "at": time.perf_counter()})
        self.agents[agent_type] = SimpleNamespace(llm=llm)
        if agent_type in self.fail:
            return {"success": False, "error": "échec simulé", "result": ""}
        return {"success": True, "result": text, "agent": agent_type}

    # pylint: disable-next=too-many-arguments,too-many-positional-arguments
    def execute_debate(self, agent_type_a, agent_type_b, topic, rounds=3, on_token=None,
                       on_round_start=None, on_should_stop=None):
        """Comme AgentOrchestrator.execute_debate : le proposant, puis l'opposant, à chaque tour."""
        turns = 0
        for round_num in range(1, rounds + 1):
            if on_should_stop():
                break
            on_round_start(round_num, agent_type_a)
            self.execute_single_task_stream(agent_type_a, f"Proposant, tour {round_num} : {topic}",
                                            None, on_token)
            turns += 1
            if on_should_stop():
                break
            on_round_start(round_num, agent_type_b)
            self.execute_single_task_stream(agent_type_b, f"Opposant, tour {round_num} : {topic}",
                                            None, on_token)
            turns += 1
        return {"success": True, "rounds_completed": turns // 2}


class FakeLLM:
    """Modèle simulé : prompts d'agents personnalisés, description d'images."""

    def __init__(self):
        self.prompts = []
        self.images = 0

    def generate(self, prompt, system_prompt=None):
        del system_prompt
        self.prompts.append(prompt)
        return GENERATED

    def describe_image(self, _b64):
        self.images += 1
        return f"Une image de test n°{self.images}."


class RelayService(AgentRelayService):
    """Le vrai service, avec son fichier d'agents personnalisés dans tmp_path."""

    def __init__(self, agents_file, orchestrator):
        self._test_agents_file = str(agents_file)
        super().__init__()
        self._orchestrator = orchestrator
        self._llm = FakeLLM()

    def _load_and_register_custom(self):
        self._custom_agents_file = self._test_agents_file
        super()._load_and_register_custom()


def node(node_id, agent_type, name=None):
    return {"id": node_id, "agent_type": agent_type, "name": name or f"{agent_type.title()}Agent",
            "color": "#3b82f6", "icon": "🐍", "x": 100.0 * node_id, "y": 50.0}


@pytest.fixture(name="agents")
def agents_fixture(tmp_path):
    """Service de la fenêtre sur le vrai AgentRelayService, bus réel."""
    bus = EventBus()
    events = []
    bus.subscribe(events.append)
    notes = []
    orchestrator = FakeOrchestrator()
    relay = RelayService(tmp_path / "custom_agents.json", orchestrator)
    service = AgentsService(lambda: relay, bus.publish, runs_file=tmp_path / "agent_runs.json",
                            notify=lambda level, message: notes.append((level, message)),
                            last_seq=lambda: bus.last_seq)
    return SimpleNamespace(service=service, relay=relay, orchestrator=orchestrator, bus=bus,
                           events=events, notes=notes, tmp_path=tmp_path)


def wait_run_end(agents, run_id, timeout=10.0):
    """Attend la fin d'un fil (runs_changed publié après son enregistrement)."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        run = agents.service.run(run_id)["run"]
        if run["status"] != "running" and agents.service.runs()["active"] is None:
            return run
        time.sleep(0.02)
    raise AssertionError("fil toujours en cours")


def agent_events(events):
    return [event for event in events if event["type"].startswith("agents.")]


# ── Agents personnalisés ────────────────────────────────────────────────────


def test_custom_agents_are_created_edited_and_deleted(agents):
    created = agents.service.create("TranslatorAgent", "Traduction multilingue")
    assert created["name"] == "TranslatorAgent" and created["custom"] is True
    assert created["desc"] == "Traduction multilingue"  # résumé rédigé par le modèle
    listed = agents.service.list()
    assert [a["key"] for a in listed["custom"]] == [created["key"]]
    assert len(listed["builtin"]) == 9

    # Nom seul : modification immédiate, sans appel au modèle (Tk)
    calls = len(agents.relay._llm.prompts)  # pylint: disable=protected-access
    renamed = agents.service.edit(created["key"], "Traducteur", "Traduction multilingue")
    assert renamed["name"] == "Traducteur"
    assert len(agents.relay._llm.prompts) == calls  # pylint: disable=protected-access
    agents.service.edit(created["key"], "Traducteur", "Traduction juridique")
    assert len(agents.relay._llm.prompts) == calls + 1  # pylint: disable=protected-access

    agents.service.delete(created["key"])
    assert agents.service.list()["custom"] == []
    assert agents.notes == [("success", "✅ Agent créé !"), ("success", "✅ Agent modifié !"),
                            ("success", "✅ Agent modifié !"), ("error", "❌ Agent supprimé")]
    assert [e["type"] for e in agent_events(agents.events)] == ["agents.list_changed"] * 4
    saved = json.loads((agents.tmp_path / "custom_agents.json").read_text(encoding="utf-8"))
    assert saved == {}


def test_custom_agent_errors_keep_the_service_message(agents):
    with pytest.raises(AgentsError, match="Nom requis"):
        agents.service.create("  ", "Rôle")
    with pytest.raises(AgentsError, match="Agent introuvable"):
        agents.service.edit("absent", "Nom", "Rôle")
    with pytest.raises(AgentsError, match="Agent introuvable"):
        agents.service.delete("absent")
    assert not agent_events(agents.events)


# ── Exécution ───────────────────────────────────────────────────────────────


def test_a_single_agent_run_streams_into_its_thread(agents):
    run_id = agents.service.start("Écris une fonction somme", [node(0, "code")], [])
    run = wait_run_end(agents, run_id)
    assert run["status"] == "done" and run["kind"] == "agent" and run["title"] == "CodeAgent"
    assert run["mode"] == "single" and run["plan"] == {"mode": "single", "steps": [[0]],
                                                       "isolated": []}
    assert run["sections"][0]["text"] == OUTPUTS["code"]
    assert run["sections"][0]["status"] == "done" and run["sections"][0]["agent_type"] == "code"
    assert run["node_status"] == {"0": "done"} and run["duration_ms"] >= 0
    # Agent seul : message de fin de Tk, dans le fil comme dans l'événement
    assert run["status_text"] == "✅ Tâche terminée avec CodeAgent"
    end = [e for e in agents.events if e["type"] == "agents.agent_exec_end"][-1]
    assert end["payload"]["status_text"] == "✅ Tâche terminée avec CodeAgent"

    types = [e["type"] for e in agent_events(agents.events)]
    assert types[0] == "agents.run_created"
    assert types[1:4] == ["agents.agent_exec_start", "agents.agent_node_status",
                          "agents.agent_section_start"]
    assert types[-3:] == ["agents.agent_node_status", "agents.agent_exec_end",
                          "agents.runs_changed"]
    assert "agents.agent_section_chunk" not in types
    # Les suites recomposent la réponse, sans trou ni recouvrement
    text = ""
    for event in agent_events(agents.events):
        if event["type"] == "agents.agent_section_delta":
            assert event["payload"]["offset"] == len(text)
            text += event["payload"]["text"]
    assert text == OUTPUTS["code"]
    for event in agents.events:
        validate_event(event)


def test_a_dag_runs_its_steps_and_passes_the_context(agents):
    nodes = [node(0, "planner"), node(1, "code"), node(2, "security"), node(3, "debug")]
    connections = [{"from": 0, "to": 1}, {"from": 0, "to": 2}, {"from": 1, "to": 3},
                   {"from": 5, "to": 1}]  # lien vers un nœud inconnu : ignoré
    run_id = agents.service.start("Une API REST", nodes, connections)
    run = wait_run_end(agents, run_id)
    assert run["kind"] == "workflow" and run["title"] == "Workflow · 4 agents"
    assert run["plan"] == {"mode": "dag", "steps": [[0], [1, 2], [3]], "isolated": []}
    assert run["connections"] == connections[:3]
    assert run["status"] == "done" and run["status_text"] == "✅ Workflow terminé (100% succès)"
    assert [s["id"] for s in run["sections"]][0] == 0 and len(run["sections"]) == 4
    tasks = dict(agents.orchestrator.calls)
    assert tasks["planner"] == "Une API REST"
    assert tasks["code"].startswith("Contexte précédent:\n[PlannerAgent]:\n## Plan")
    assert tasks["debug"].startswith("Contexte précédent:\n[CodeAgent]:")


def test_a_failed_agent_marks_its_node_and_the_run(agents):
    agents.orchestrator.fail = {"debug"}
    run_id = agents.service.start("Tâche", [node(0, "code"), node(1, "debug")],
                                  [{"from": 0, "to": 1}])
    run = wait_run_end(agents, run_id)
    assert run["status"] == "error" and run["node_status"] == {"0": "done", "1": "error"}
    assert run["sections"][1]["status"] == "error"
    assert run["status_text"] == "✅ Workflow terminé (50% succès)"  # texte du service


def test_start_refuses_like_tk(agents, tmp_path):
    with pytest.raises(AgentsError, match=NO_AGENT):
        agents.service.start("Tâche", [], [])
    with pytest.raises(AgentsError, match=EMPTY_TASK):
        agents.service.start("   ", [node(0, "code")], [])
    with pytest.raises(AgentsError, match="Fichier introuvable"):
        agents.service.start("Tâche", [node(0, "code")], [],
                             [{"path": str(tmp_path / "absent.pdf")}])
    agents.relay._busy = True  # pylint: disable=protected-access
    with pytest.raises(AgentsError, match=BUSY):
        agents.service.start("Tâche", [node(0, "code")], [])
    agents.relay._busy = False  # pylint: disable=protected-access
    assert agents.service.runs()["runs"] == []


def test_one_run_at_a_time(agents):
    agents.orchestrator.delay = 0.05
    run_id = agents.service.start("Tâche", [node(0, "code")], [])
    with pytest.raises(AgentsError, match=BUSY):
        agents.service.start("Autre", [node(0, "debug")], [])
    assert agents.service.stop(run_id)
    wait_run_end(agents, run_id)


def test_stop_interrupts_the_run(agents):
    agents.orchestrator.delay = 0.05
    run_id = agents.service.start("Tâche", [node(0, "code"), node(1, "debug")],
                                  [{"from": 0, "to": 1}])
    assert agents.orchestrator.started.wait(5)
    assert agents.service.stop(run_id)
    run = wait_run_end(agents, run_id)
    assert run["status"] == "interrupted" and run["status_text"] == INTERRUPTED
    assert [call[0] for call in agents.orchestrator.calls] == ["code"]  # étape suivante annulée
    assert run["node_status"]["1"] == "idle"
    assert not agents.service.stop(run_id)  # déjà fini


def test_stop_during_the_images_ends_without_running(agents, tmp_path):
    image = tmp_path / "photo.png"
    image.write_bytes(b"png")
    entered, release = threading.Event(), threading.Event()

    def slow_describe(_path):
        entered.set()
        release.wait(5)
        return "une photo"

    agents.relay._describe_image = slow_describe  # pylint: disable=protected-access
    run_id = agents.service.start("Décris", [node(0, "code")], [],
                                  [{"path": str(image), "type": "Image"}])
    assert entered.wait(5)
    assert agents.service.stop(run_id)
    release.set()
    run = wait_run_end(agents, run_id)
    assert run["status"] == "interrupted" and agents.orchestrator.calls == []
    assert run["sections"] == []


def test_a_stop_before_the_executor_starts_is_sent_again(agents):
    """L'exécuteur remet son drapeau d'arrêt à zéro en démarrant : l'arrêt
    demandé juste avant lui est redemandé à son premier événement."""
    entered, release = threading.Event(), threading.Event()
    real_run = agents.relay.run_workflow

    def late_run(*args, **kwargs):
        entered.set()
        release.wait(5)
        return real_run(*args, **kwargs)

    agents.relay.run_workflow = late_run
    agents.orchestrator.delay = 0.05
    run_id = agents.service.start("Tâche", [node(0, "code"), node(1, "debug")],
                                  [{"from": 0, "to": 1}])
    assert entered.wait(5)
    assert agents.service.stop(run_id)
    release.set()
    run = wait_run_end(agents, run_id)
    assert run["status"] == "interrupted"
    assert len(agents.orchestrator.calls) <= 1


def test_every_image_is_described_in_order(agents, tmp_path):
    first, second = tmp_path / "a.png", tmp_path / "b.jpg"
    doc = tmp_path / "notes.txt"
    for path in (first, second):
        path.write_bytes(b"img")
    doc.write_text("contenu du document", encoding="utf-8")
    described = []
    agents.relay._describe_image = lambda path: described.append(Path(path).name) or "vue"  # pylint: disable=protected-access
    received = {}
    real_run = agents.relay.run_workflow

    def spy(exec_id, task, nodes, connections, emit, image_path=None, file_paths=None):
        received.update(task=task, image_path=image_path, file_paths=file_paths)
        return real_run(exec_id, task, nodes, connections, emit, image_path, file_paths)

    agents.relay.run_workflow = spy
    run_id = agents.service.start("Compare", [node(0, "code")], [], [
        {"path": str(first), "type": "Image"}, {"path": str(doc)},
        {"path": str(second), "type": "Image"}])
    wait_run_end(agents, run_id)
    assert described == ["a.png", "b.jpg"]
    assert received["image_path"] is None and received["file_paths"] == [str(doc)]
    task = received["task"]
    assert task.index("--- Image jointe : a.png ---") < task.index("--- Image jointe : b.jpg ---")
    # Le document est lu par le service, comme pour le mobile
    assert "--- Fichier joint : notes.txt ---\ncontenu du document" in agents.orchestrator.calls[0][1]


def test_code_attachments_are_kept_for_the_diff(agents, tmp_path):
    code = tmp_path / "utils.py"
    code.write_text("def f():\n    return 1\n", encoding="utf-8")
    run_id = agents.service.start("Optimise", [node(0, "optimizer")], [], [{"path": str(code)}])
    run = wait_run_end(agents, run_id)
    assert run["sources"] == [{"name": "utils.py", "text": "def f():\n    return 1\n"}]
    assert run["attachments"] == [{"path": str(code), "name": "utils.py", "type": "Code"}]


def test_a_replaced_section_text_is_sent_whole(agents):
    run_id = agents.service.start("Tâche", [node(0, "code")], [])
    wait_run_end(agents, run_id)
    run = agents.service._runs[0]  # pylint: disable=protected-access
    agents.service._on_event(run, {"type": "agent_exec_end", "exec_id": run_id,  # pylint: disable=protected-access
                                   "success": True, "interrupted": False, "status_text": "fin"})
    run.status = "running"
    agents.service._on_event(run, {"type": "agent_section_chunk", "exec_id": run_id,  # pylint: disable=protected-access
                                   "section_id": 0, "text": "Autre texte"})
    last = agent_events(agents.events)[-1]
    assert last["type"] == "agents.agent_section_text"
    assert last["payload"] == {"exec_id": run_id, "section_id": 0, "text": "Autre texte"}


# ── Fils gardés (D33) ───────────────────────────────────────────────────────


def test_runs_are_saved_and_reloaded(agents):
    run_id = agents.service.start("Tâche", [node(0, "code")], [])
    wait_run_end(agents, run_id)
    again = AgentsService(lambda: agents.relay, agents.bus.publish,
                          runs_file=agents.tmp_path / "agent_runs.json")
    listed = again.runs()["runs"]
    assert [item["id"] for item in listed] == [run_id]
    assert listed[0]["status"] == "done" and listed[0]["agent_type"] == "code"
    assert again.run(run_id)["run"]["sections"][0]["text"] == OUTPUTS["code"]


def test_a_run_left_running_is_reloaded_as_interrupted(tmp_path):
    runs_file = tmp_path / "agent_runs.json"
    runs = [{"id": f"exec_{n}", "task": f"t{n}", "status": "done"} for n in range(60)]
    runs[0] = {"id": "exec_0", "task": "t0", "status": "running",
               "sections": [{"id": 0, "title": "A", "text": "début", "status": "running"}]}
    runs.append({"id": "../evil", "status": "done"})
    runs_file.write_text(json.dumps({"version": 1, "runs": runs}), encoding="utf-8")
    service = AgentsService(lambda: None, lambda *a, **k: None, runs_file=runs_file)
    listed = service.runs()["runs"]
    assert len(listed) == agents_module.MAX_RUNS
    assert listed[0]["status"] == "interrupted" and listed[0]["status_text"] == INTERRUPTED
    assert service.run("exec_0")["run"]["sections"][0]["status"] == "error"
    with pytest.raises(RunNotFound):
        service.run("../evil")


def test_an_unreadable_runs_file_starts_empty(tmp_path):
    runs_file = tmp_path / "agent_runs.json"
    runs_file.write_text("{pas du json", encoding="utf-8")
    service = AgentsService(lambda: None, lambda *a, **k: None, runs_file=runs_file)
    assert service.runs()["runs"] == []


def test_only_the_last_fifty_runs_are_kept(agents, monkeypatch):
    monkeypatch.setattr(agents_module, "MAX_RUNS", 3)
    ids = []
    for index in range(5):
        run_id = agents.service.start(f"Tâche {index}", [node(0, "code")], [])
        wait_run_end(agents, run_id)
        ids.append(run_id)
    listed = [item["id"] for item in agents.service.runs()["runs"]]
    assert listed == ids[::-1][:3]


def test_runs_are_deleted_and_cleared(agents):
    first = agents.service.start("Un", [node(0, "code")], [])
    wait_run_end(agents, first)
    agents.orchestrator.delay = 0.05
    second = agents.service.start("Deux", [node(0, "code")], [])
    with pytest.raises(AgentsError, match="arrêtez-la d'abord"):
        agents.service.delete_run(second)
    assert agents.service.clear_runs() == 1  # le fil en cours reste
    assert [item["id"] for item in agents.service.runs()["runs"]] == [second]
    agents.service.stop(second)
    wait_run_end(agents, second)
    agents.service.delete_run(second)
    assert agents.service.runs()["runs"] == []
    with pytest.raises(RunNotFound):
        agents.service.delete_run(second)
    saved = json.loads((agents.tmp_path / "agent_runs.json").read_text(encoding="utf-8"))
    assert saved["runs"] == []


def test_shutdown_saves_the_run_as_interrupted(agents):
    agents.orchestrator.delay = 0.05
    run_id = agents.service.start("Tâche", [node(0, "code")], [])
    assert agents.orchestrator.started.wait(5)
    agents.service.shutdown()
    saved = json.loads((agents.tmp_path / "agent_runs.json").read_text(encoding="utf-8"))
    assert saved["runs"][0]["id"] == run_id and saved["runs"][0]["status"] == "interrupted"
    wait_run_end(agents, run_id)


def test_reads_carry_the_seq_of_their_state(agents):
    run_id = agents.service.start("Tâche", [node(0, "code")], [])
    wait_run_end(agents, run_id)
    assert agents.service.runs()["seq"] == agents.bus.last_seq
    assert agents.service.run(run_id)["seq"] == agents.bus.last_seq


# ── Pièces jointes de la zone de tâche ──────────────────────────────────────


def test_inspect_classifies_files_and_folders(agents, tmp_path):
    folder = tmp_path / "projet"
    (folder / "src").mkdir(parents=True)
    (folder / "src" / "main.py").write_text("print(1)", encoding="utf-8")
    (folder / "logo.png").write_bytes(b"png")
    (folder / "node_modules").mkdir()
    (folder / "node_modules" / "x.js").write_text("x", encoding="utf-8")
    report = tmp_path / "rapport.pdf"
    report.write_bytes(b"%PDF")
    binary = tmp_path / "outil.exe"
    binary.write_bytes(b"MZ")
    result = agents.service.inspect([str(report), str(folder), str(binary),
                                     str(tmp_path / "absent.docx")])
    assert [(a["name"], a["type"]) for a in result["attachments"]] == [
        ("rapport.pdf", "PDF"), ("main.py", "Code")]
    assert result["refused"] == ["❌ Format non supporté : .exe",
                                 "❌ Fichier introuvable : absent.docx"]
    assert str(report.resolve()).lower() in {p.lower() for p in agents.service.known_paths()}


# ── Fichiers de workflow ────────────────────────────────────────────────────

TK_WORKFLOW = {
    "version": "8.1.0",
    "nodes": {
        "0": {"agent_type": "planner", "name": "PlannerAgent", "color": "#06b6d4", "icon": "📋",
              "x": 75, "y": 50, "status": "done"},
        "1": {"agent_type": "code", "name": "CodeAgent", "color": "#3b82f6", "icon": "🐍",
              "x": 375, "y": 50, "status": "done"},
    },
    "connections": [{"from": 0, "to": 1}],
    "zoom": 1.0, "pan_x": 0.0, "pan_y": 0.0,
}


def test_workflow_markdown_follows_d11():
    run = {"task": "Une API", "started_at": "2026-10-14T14:02:00", "status_text": "✅ fini",
           "nodes": [{"id": 0, "agent_type": "planner"}, {"id": 1, "agent_type": "debug"}],
           "sections": [{"id": 0, "text": "## Plan"}, {"id": 1, "text": "autre agent"}]}
    text = workflow_markdown(TK_WORKFLOW, run)
    assert text.startswith("# Workflow Export\n\n**Version**: 8.1.0\n**Nodes**: 2\n"
                           "**Connections**: 1\n\n## Tâche\n\nUne API\n\n## Agents\n\n")
    assert "- 📋 **PlannerAgent** — type : `planner` — statut : Terminé" in text
    assert "## Réponses de la dernière exécution (2026-10-14 14:02)" in text
    assert "### 📋 PlannerAgent\n\n## Plan\n" in text
    # Nœud 1 : un autre agent à la dernière exécution (canvas changé depuis)
    assert "### 🐍 CodeAgent\n\n_Pas de réponse à la dernière exécution._" in text
    assert text.rstrip().endswith("✅ fini")
    assert "## Réponses" not in workflow_markdown(TK_WORKFLOW, None)


# ── Routes ──────────────────────────────────────────────────────────────────


@pytest.fixture(name="client")
def client_fixture(agents):
    bus = agents.bus
    app = FakeApp(None, bus)
    app.agents = agents.service
    app.agent_attachments = agents.service.known_paths
    app.notify = lambda level, message: bus.publish("notification",
                                                    {"level": level, "message": message})
    server = DesktopServer(app)
    server.port = PORT
    return SimpleNamespace(client=TestClient(server.fastapi, base_url=BASE), app=app,
                           server=server)


def test_routes_require_the_token_and_a_ready_engine(client):
    assert client.client.get("/api/agents").status_code == 401
    client.app.engine = None
    answer = client.client.get("/api/agents", headers=AUTH)
    assert answer.status_code == 503 and answer.json()["detail"] == "Le moteur démarre…"


def test_run_routes(client, agents):
    listed = client.client.get("/api/agents", headers=AUTH).json()
    assert [a["key"] for a in listed["builtin"]][:3] == ["code", "web", "analyst"]
    bad = client.client.post("/api/agents/runs", headers=AUTH,
                             json={"task": "x", "nodes": [{"id": "a", "agent_type": "code"}]})
    assert bad.status_code == 422
    empty = client.client.post("/api/agents/runs", headers=AUTH, json={"task": "x", "nodes": []})
    assert empty.status_code == 409 and empty.json()["detail"] == NO_AGENT
    started = client.client.post("/api/agents/runs", headers=AUTH, json={
        "task": "Somme", "nodes": [node(0, "code"), node(1, "debug")],
        "connections": [{"from": 0, "to": 1}]})
    run_id = started.json()["run_id"]
    wait_run_end(agents, run_id)
    runs = client.client.get("/api/agents/runs", headers=AUTH).json()
    assert runs["runs"][0]["id"] == run_id and runs["active"] is None and "seq" in runs
    detail = client.client.get(f"/api/agents/runs/{run_id}", headers=AUTH).json()["run"]
    assert detail["connections"] == [{"from": 0, "to": 1}]
    assert client.client.get("/api/agents/runs/absent", headers=AUTH).status_code == 404
    assert client.client.post(f"/api/agents/runs/{run_id}/stop",
                              headers=AUTH).json() == {"stopped": False}
    assert client.client.delete(f"/api/agents/runs/{run_id}", headers=AUTH).status_code == 200
    assert client.client.delete("/api/agents/runs", headers=AUTH).json() == {"removed": 0}


def test_custom_agent_routes(client, agents):
    created = client.client.post("/api/agents/custom", headers=AUTH,
                                 json={"name": "SEOAgent", "role": "Référencement"})
    key = created.json()["agent"]["key"]
    edited = client.client.put(f"/api/agents/custom/{key}", headers=AUTH,
                               json={"name": "SEO", "role": "Référencement"})
    assert edited.json()["agent"]["name"] == "SEO"
    refused = client.client.post("/api/agents/custom", headers=AUTH, json={"name": "", "role": "x"})
    assert refused.status_code == 409 and refused.json()["detail"] == "❌ Erreur : Nom requis"
    assert client.client.delete(f"/api/agents/custom/{key}", headers=AUTH).status_code == 200
    assert [message for _level, message in agents.notes] == [
        "✅ Agent créé !", "✅ Agent modifié !", "❌ Agent supprimé"]


def test_attachment_routes_and_thumbnails(client, tmp_path):
    image = tmp_path / "capture.png"
    image.write_bytes(b"\x89PNG")
    picked = client.client.post("/api/agents/attachments", headers=AUTH,
                                json={"paths": [str(image)]}).json()
    assert picked["attachments"][0]["type"] == "Image"
    links = client.client.post("/api/files/links", headers=AUTH,
                               json={"paths": [str(image)]}).json()["links"]
    assert links[str(image)]  # vignette de la zone de tâche
    uploaded = client.client.post("/api/agents/attachments/upload", headers=AUTH,
                                  files={"file": ("clipboard_image.png", b"\x89PNG", "image/png")})
    item = uploaded.json()["attachments"][0]
    assert item["name"] == "clipboard_image.png" and Path(item["path"]).is_file()


def test_workflow_file_routes(client, agents, tmp_path, monkeypatch):
    target = tmp_path / "flux" / "workflow.json"
    saved = client.client.post("/api/agents/workflow/save", headers=AUTH,
                               json={"path": str(target), "workflow": TK_WORKFLOW})
    assert saved.status_code == 200
    written = json.loads(target.read_text(encoding="utf-8"))
    assert written == TK_WORKFLOW
    # Même ordre des clés que WorkflowCanvas.to_dict de Tk
    assert list(written) == ["version", "nodes", "connections", "zoom", "pan_x", "pan_y"]
    assert list(written["nodes"]["0"]) == ["agent_type", "name", "color", "icon", "x", "y",
                                           "status"]
    read = client.client.post("/api/agents/workflow/read", headers=AUTH,
                              json={"path": str(target)}).json()["workflow"]
    assert read == TK_WORKFLOW
    broken = tmp_path / "casse.json"
    broken.write_text("[1, 2]", encoding="utf-8")
    refused = client.client.post("/api/agents/workflow/read", headers=AUTH,
                                 json={"path": str(broken)})
    assert refused.status_code == 409 and "format inconnu" in refused.json()["detail"]

    run_id = agents.service.start("Une API", [node(0, "planner"), node(1, "code")],
                                  [{"from": 0, "to": 1}])
    wait_run_end(agents, run_id)
    export = tmp_path / "export.md"
    client.client.post("/api/agents/workflow/export", headers=AUTH,
                       json={"path": str(export), "workflow": TK_WORKFLOW, "run_id": run_id})
    text = export.read_text(encoding="utf-8")
    assert "## Tâche\n\nUne API" in text and OUTPUTS["code"].strip() in text

    # Sans dialogue (navigateur) : fichiers datés sous outputs/
    monkeypatch.chdir(tmp_path)
    fallback = client.client.post("/api/agents/workflow/save", headers=AUTH,
                                  json={"workflow": TK_WORKFLOW}).json()["path"]
    assert Path(fallback).parent == (tmp_path / "outputs" / "workflows").resolve()
    messages = [e["payload"]["message"] for e in agents.events if e["type"] == "notification"]
    assert messages == ["💾 Workflow sauvegardé", "📤 Workflow exporté", "💾 Workflow sauvegardé"]


def test_debate_resources_and_focus_routes(client, agents):
    started = client.client.post("/api/agents/debates", headers=AUTH, json={
        "agent_a": "code", "agent_b": "debug", "topic": "Tabs ou espaces ?", "rounds": 1})
    run = wait_run_end(agents, started.json()["run_id"])
    assert run["kind"] == "debate" and len(run["sections"]) == 2
    same = client.client.post("/api/agents/debates", headers=AUTH,
                              json={"agent_a": "code", "agent_b": "code", "topic": "Sujet"})
    assert same.status_code == 409 and same.json()["detail"] == DEBATE_SAME_AGENT
    too_long = client.client.post("/api/agents/debates", headers=AUTH, json={
        "agent_a": "code", "agent_b": "debug", "topic": "Sujet", "rounds": 11})
    assert too_long.status_code == 422

    client.app.window_focused = True
    focus = client.client.post("/api/window/focus", headers=AUTH, json={"focused": False})
    assert focus.json() == {"ok": True} and client.app.window_focused is False

    snapshot = {"metrics": {"cpu_percent": 12.5}, "history": {"cpu": [12.5]}, "inferences": 0,
                "interval": 3.0}
    client.app.resources = SimpleNamespace(snapshot=lambda: snapshot)
    assert client.client.get("/api/resources", headers=AUTH).json() == snapshot


# ── Débat ───────────────────────────────────────────────────────────────────


def until(predicate, timeout=5.0):
    """Attend qu'une condition soit vraie (fil de l'exécuteur, notification)."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        if predicate():
            return
        time.sleep(0.01)
    raise AssertionError("condition jamais remplie")


def test_a_debate_alternates_its_two_agents(agents):
    run_id = agents.service.start_debate("code", "debug", "Tabs ou espaces ?", 2)
    run = wait_run_end(agents, run_id)
    assert run["kind"] == "debate" and run["origin"] == "desktop" and run["mode"] == "debate"
    assert run["title"] == "Débat · CodeAgent vs DebugAgent" and run["task"] == "Tabs ou espaces ?"
    assert run["debate"] == {"agent_a": "code", "agent_b": "debug", "rounds": 2}
    # Un tour par section : le proposant, puis l'opposant (titres d'AgentRelayService)
    assert [s["id"] for s in run["sections"]] == ["deb_1", "deb_2", "deb_3", "deb_4"]
    assert [s["title"] for s in run["sections"]] == [
        "Tour 1 — CodeAgent (Proposant)", "Tour 1 — DebugAgent (Opposant)",
        "Tour 2 — CodeAgent (Proposant)", "Tour 2 — DebugAgent (Opposant)"]
    assert [s["agent_type"] for s in run["sections"]] == ["code", "debug", "code", "debug"]
    assert run["sections"][1]["text"] == OUTPUTS["debug"]
    assert run["status"] == "done" and run["status_text"] == "✅ Débat terminé (2 tours)"
    assert [call[1] for call in agents.orchestrator.calls][:2] == [
        "Proposant, tour 1 : Tabs ou espaces ?", "Opposant, tour 1 : Tabs ou espaces ?"]
    for event in agents.events:
        validate_event(event)


def test_a_debate_refuses_like_tk(agents):
    with pytest.raises(AgentsError, match=DEBATE_SAME_AGENT):
        agents.service.start_debate("code", "code", "Sujet", 3)
    with pytest.raises(AgentsError, match=DEBATE_NO_TOPIC):
        agents.service.start_debate("code", "debug", "   ", 3)
    with pytest.raises(AgentsError, match="Agent introuvable : absent"):
        agents.service.start_debate("code", "absent", "Sujet", 3)
    agents.relay._busy = True  # pylint: disable=protected-access
    with pytest.raises(AgentsError, match=DEBATE_BUSY):
        agents.service.start_debate("code", "debug", "Sujet", 3)
    agents.relay._busy = False  # pylint: disable=protected-access
    assert agents.service.runs()["runs"] == []
    # Nombre de tours ramené entre 1 et 10, comme le dialogue de Tk
    run = wait_run_end(agents, agents.service.start_debate("code", "debug", "Sujet", 0))
    assert run["debate"]["rounds"] == 3


def test_a_stopped_debate_says_so(agents):
    agents.orchestrator.delay = 0.05
    run_id = agents.service.start_debate("code", "debug", "Sujet", 10)
    assert agents.orchestrator.started.wait(5)
    assert agents.service.stop(run_id)
    run = wait_run_end(agents, run_id)
    assert run["status"] == "interrupted" and run["status_text"] == DEBATE_INTERRUPTED
    assert len(run["sections"]) == 1 and run["sections"][0]["status"] == "error"


# ── Exécutions du téléphone et des tâches planifiées (D37) ──────────────────


PHONE_NODE = {"id": "n1", "agent_type": "code", "name": "CodeAgent", "color": "#3b82f6",
              "icon": "🐍"}


def test_a_phone_run_becomes_a_thread_and_reaches_the_phone_unchanged(agents):
    tap = agents.service.executor_tap()
    assert tap is agents.service.executor_tap()
    phone = []
    tap.run_workflow("exec_1760000000000_42", "Une API", [PHONE_NODE], [], phone.append, None, [])
    run = agents.service.run("exec_1760000000000_42")["run"]
    assert run["origin"] == "mobile" and run["kind"] == "agent" and run["title"] == "CodeAgent"
    assert run["status"] == "done" and run["sections"][0]["text"] == OUTPUTS["code"]
    assert run["node_status"] == {"n1": "done"}
    # Le téléphone reçoit les événements de l'exécuteur tels quels (texte cumulé)
    assert phone[0]["type"] == "agent_exec_start" and phone[-1]["type"] == "agent_exec_end"
    chunks = [e["text"] for e in phone if e["type"] == "agent_section_chunk"]
    assert chunks[-1] == OUTPUTS["code"]
    end = next(e for e in phone if e["type"] == "agent_section_end")
    assert set(end) == {"type", "exec_id", "section_id", "success"}
    assert agents.service.runs()["runs"][0]["origin"] == "mobile"
    # Le reste de l'exécuteur est délégué
    assert tap.list_agents()["builtin"][0]["key"] == "code" and tap.busy is False


def test_a_phone_run_is_refused_while_the_page_prepares_one(agents, tmp_path):
    image = tmp_path / "photo.png"
    image.write_bytes(b"png")
    entered, release = threading.Event(), threading.Event()

    def slow_describe(_path):
        entered.set()
        release.wait(5)
        return "une photo"

    agents.relay._describe_image = slow_describe  # pylint: disable=protected-access
    run_id = agents.service.start("Décris", [node(0, "code")], [],
                                  [{"path": str(image), "type": "Image"}])
    assert entered.wait(5)
    tap = agents.service.executor_tap()
    assert tap.busy  # le scheduler la diffère
    phone = []
    tap.run_workflow("exec_phone", "Autre", [PHONE_NODE], [], phone.append)
    assert phone == [{"type": "agent_exec_error", "exec_id": "exec_phone",
                      "message": EXECUTOR_BUSY}]
    release.set()
    wait_run_end(agents, run_id)
    assert [run["id"] for run in agents.service.runs()["runs"]] == [run_id]


def test_a_phone_debate_can_be_stopped_from_the_window(agents):
    agents.orchestrator.delay = 0.05
    tap = agents.service.executor_tap()
    phone = []
    worker = threading.Thread(target=tap.run_debate,
                              args=("deb_1760000000000_7", "code", "creative", "Sujet", 3,
                                    phone.append))
    worker.start()
    assert agents.orchestrator.started.wait(5)
    assert agents.service.runs()["active"] == "deb_1760000000000_7"
    assert agents.service.stop("deb_1760000000000_7")
    worker.join(10)
    run = agents.service.run("deb_1760000000000_7")["run"]
    assert run["origin"] == "mobile" and run["kind"] == "debate"
    assert run["title"] == "Débat · CodeAgent vs CreativeAgent"
    assert run["status"] == "interrupted"
    assert phone[-1]["type"] == "agent_exec_end" and phone[-1]["interrupted"] is True


def test_a_scheduled_run_is_titled_and_gets_its_report(agents):
    asked = []

    def find_scheduled(task, nodes, debate):
        asked.append((task, nodes, debate))
        return {"id": "sched_1", "name": "Veille du matin"}

    agents.service._find_scheduled = find_scheduled  # pylint: disable=protected-access
    collected = []
    agents.service.executor_tap().run_workflow("schedexec_0123456789ab", "Résume l'actualité",
                                               [PHONE_NODE], [], collected.append)
    assert asked == [("Résume l'actualité", [PHONE_NODE], None)]
    run = agents.service.run("schedexec_0123456789ab")["run"]
    assert run["origin"] == "scheduled" and run["title"] == "Veille du matin"
    assert run["schedule"] == {"task_id": "sched_1", "name": "Veille du matin",
                               "output_file": None}
    assert collected[-1]["type"] == "agent_exec_end"  # le collecteur du scheduler a tout reçu
    agents.service.scheduled_result({"task_id": "sched_1", "name": "Veille du matin",
                                     "output_file": "outputs/scheduled/sched_1.md"})
    run = agents.service.run("schedexec_0123456789ab")["run"]
    assert run["schedule"]["output_file"] == "outputs/scheduled/sched_1.md"
    assert agents.service.runs()["runs"][0]["schedule_task_id"] == "sched_1"


# ── Statistiques, temps d'inférence, notification ───────────────────────────


def test_stats_are_computed_on_the_kept_threads(agents):
    assert agents.service.runs()["stats"] == {"tasks": 0, "agents": 0, "success_rate": None}
    agents.orchestrator.fail = {"debug"}
    wait_run_end(agents, agents.service.start("Somme", [node(0, "code")], []))
    wait_run_end(agents, agents.service.start("Tâche", [node(0, "planner"), node(1, "debug")],
                                              [{"from": 0, "to": 1}]))
    assert agents.service.runs()["stats"] == {"tasks": 3, "agents": 3, "success_rate": 50}


def test_each_agent_reports_its_inference_time_and_tokens_per_second(agents):
    seen = []
    agents.service._on_inference = lambda ms, tps: seen.append((ms, tps))  # pylint: disable=protected-access
    run = wait_run_end(agents, agents.service.start("Somme", [node(0, "code")], []))
    section = run["sections"][0]
    assert section["tokens_per_sec"] == 25.0 and section["inference_ms"] >= 0
    assert len(seen) == 1 and seen[0][1] == 25.0
    end = next(e for e in agents.events if e["type"] == "agents.agent_section_end")
    assert end["payload"]["tokens_per_sec"] == 25.0
    validate_event(end)


def test_an_interrupted_agent_has_no_tokens_per_second(agents):
    seen = []
    agents.service._on_inference = lambda ms, tps: seen.append((ms, tps))  # pylint: disable=protected-access
    agents.orchestrator.delay = 0.05
    run_id = agents.service.start("Somme", [node(0, "code")], [])
    assert agents.orchestrator.started.wait(5)
    agents.service.stop(run_id)
    run = wait_run_end(agents, run_id)
    assert run["sections"][0]["tokens_per_sec"] is None and seen == []


def test_a_long_run_is_notified_when_the_window_has_no_focus(agents, monkeypatch):
    monkeypatch.setattr(agents_module, "NOTIFY_MIN_SECONDS", 0)
    notified = []
    focused = {"value": False}
    agents.service._os_notify = lambda title, message: notified.append((title, message))  # pylint: disable=protected-access
    agents.service._window_focused = lambda: focused["value"]  # pylint: disable=protected-access

    wait_run_end(agents, agents.service.start("Écris une fonction somme", [node(0, "code")], []))
    until(lambda: len(notified) == 1)
    assert notified[0] == ("✅ CodeAgent — tâche terminée", "Écris une fonction somme")

    wait_run_end(agents, agents.service.start("Une API", [node(0, "planner"), node(1, "code")],
                                              [{"from": 0, "to": 1}]))
    until(lambda: len(notified) == 2)
    assert notified[1] == ("✅ Workflow visuel terminé", "100% de succès — Une API")

    wait_run_end(agents, agents.service.start_debate("code", "debug", "Tabs ?", 1))
    until(lambda: len(notified) == 3)
    assert notified[2] == ("✅ Débat terminé (1 tour)", "Tabs ?")

    # Ni fenêtre au premier plan, ni exécution du téléphone, ni fil arrêté
    focused["value"] = True
    wait_run_end(agents, agents.service.start("Somme", [node(0, "code")], []))
    focused["value"] = False
    agents.service.executor_tap().run_workflow("exec_phone_2", "Somme", [PHONE_NODE], [],
                                               lambda _event: None)
    agents.orchestrator.delay = 0.05
    stopped = agents.service.start("Somme", [node(0, "code")], [])
    assert agents.orchestrator.started.wait(5)
    agents.service.stop(stopped)
    wait_run_end(agents, stopped)
    time.sleep(0.2)
    assert len(notified) == 3


def test_a_short_run_is_not_notified(agents):
    notified = []
    agents.service._os_notify = lambda title, message: notified.append((title, message))  # pylint: disable=protected-access
    agents.service._window_focused = lambda: False  # pylint: disable=protected-access
    wait_run_end(agents, agents.service.start("Somme", [node(0, "code")], []))
    time.sleep(0.2)
    assert notified == []  # moins de 8 s
