"""
Tests unitaires pour core/scheduler.py

L'exécution est simulée par un FakeExecutor qui émet les mêmes events que
``AgentRelayService.run_workflow`` / ``run_debate`` — aucun LLM réel n'est
sollicité.
"""

import os
from datetime import datetime, timedelta

import pytest

from core.scheduler import SchedulerService, _CRONITER_AVAILABLE


# ----------------------------------------------------------------------
# Exécuteur factice
# ----------------------------------------------------------------------

class FakeExecutor:
    """Imite AgentRelayService : run_workflow / run_debate + propriété busy."""

    def __init__(self, busy=False, fail=False):
        self.busy = busy
        self.fail = fail
        self.calls = []
        self.interrupted = []

    def run_workflow(self, exec_id, task, nodes, connections, emit,
                     image_path=None, file_paths=None):
        self.calls.append(("workflow", task))
        emit({"type": "agent_exec_start", "exec_id": exec_id, "mode": "single"})
        emit({"type": "agent_section_start", "exec_id": exec_id,
              "section_id": "n1", "title": "WebAgent", "color": "#10b981"})
        emit({"type": "agent_section_chunk", "exec_id": exec_id,
              "section_id": "n1", "text": "Résultat de la tâche planifiée."})
        emit({"type": "agent_section_end", "exec_id": exec_id,
              "section_id": "n1", "success": not self.fail})
        emit({"type": "agent_exec_end", "exec_id": exec_id,
              "success": not self.fail, "interrupted": False,
              "status_text": "✅ Workflow terminé" if not self.fail else "❌ Échec"})

    def run_debate(self, exec_id, agent_a, agent_b, topic, rounds, emit):
        self.calls.append(("debate", topic))
        emit({"type": "agent_exec_start", "exec_id": exec_id, "mode": "debate"})
        emit({"type": "agent_debate_topic", "exec_id": exec_id, "topic": topic})
        emit({"type": "agent_section_start", "exec_id": exec_id,
              "section_id": "d1", "title": "Tour 1 — A", "color": "#fff"})
        emit({"type": "agent_section_chunk", "exec_id": exec_id,
              "section_id": "d1", "text": "Argument du proposant."})
        emit({"type": "agent_section_end", "exec_id": exec_id,
              "section_id": "d1", "success": True})
        emit({"type": "agent_exec_end", "exec_id": exec_id, "success": True,
              "interrupted": False, "status_text": "✅ Débat terminé"})

    def interrupt(self, exec_id):
        self.interrupted.append(exec_id)


def _make_service(tmp_path, executor=None, **overrides):
    """Construit un SchedulerService isolé dans tmp_path (pas de thread)."""
    cfg = {
        "enabled": True,
        "check_interval": 5,
        "run_missed_on_startup": False,
        "catch_up_window_hours": 24,
        "max_history": 5,
        "tasks_file": str(tmp_path / "scheduled_tasks.json"),
        "output_directory": str(tmp_path / "out"),
        "notify_desktop": False,   # pas d'appel OS pendant les tests
        "notify_mobile": False,
    }
    cfg.update(overrides)
    return SchedulerService(executor=executor or FakeExecutor(), config=cfg)


_WF_NODE = [{"id": "n1", "agent_type": "web", "name": "WebAgent",
             "color": "#10b981", "icon": "🔍"}]


# ----------------------------------------------------------------------
# Calcul de la prochaine exécution
# ----------------------------------------------------------------------

class TestComputeNextRun:

    def test_interval(self, tmp_path):
        svc = _make_service(tmp_path)
        after = datetime(2026, 6, 18, 10, 0, 0)
        nxt = svc._compute_next_run({"type": "interval", "seconds": 3600}, after)
        assert nxt == after + timedelta(seconds=3600)

    def test_daily_later_today(self, tmp_path):
        svc = _make_service(tmp_path)
        after = datetime(2026, 6, 18, 6, 0, 0)
        nxt = svc._compute_next_run({"type": "daily", "at": "08:00"}, after)
        assert nxt == datetime(2026, 6, 18, 8, 0, 0)

    def test_daily_rolls_to_tomorrow(self, tmp_path):
        svc = _make_service(tmp_path)
        after = datetime(2026, 6, 18, 9, 0, 0)
        nxt = svc._compute_next_run({"type": "daily", "at": "08:00"}, after)
        assert nxt == datetime(2026, 6, 19, 8, 0, 0)

    def test_weekly_picks_next_matching_day(self, tmp_path):
        svc = _make_service(tmp_path)
        # 2026-06-18 est un jeudi (weekday 3). Prochain lundi (0) = 2026-06-22.
        after = datetime(2026, 6, 18, 12, 0, 0)
        nxt = svc._compute_next_run({"type": "weekly", "days": [0], "at": "09:00"}, after)
        assert nxt == datetime(2026, 6, 22, 9, 0, 0)
        assert nxt.weekday() == 0

    def test_weekly_without_days_is_none(self, tmp_path):
        svc = _make_service(tmp_path)
        assert svc._compute_next_run({"type": "weekly", "days": []}, datetime.now()) is None

    @pytest.mark.skipif(not _CRONITER_AVAILABLE, reason="croniter non installé")
    def test_cron(self, tmp_path):
        svc = _make_service(tmp_path)
        after = datetime(2026, 6, 18, 6, 0, 0)
        nxt = svc._compute_next_run({"type": "cron", "expr": "0 8 * * *"}, after)
        assert nxt == datetime(2026, 6, 18, 8, 0, 0)


# ----------------------------------------------------------------------
# CRUD + persistance
# ----------------------------------------------------------------------

class TestPersistence:

    def test_create_computes_next_run(self, tmp_path):
        svc = _make_service(tmp_path)
        task = svc.create_task(
            name="Veille IA", kind="workflow", task="Résume l'actu",
            schedule={"type": "interval", "seconds": 3600}, nodes=_WF_NODE,
        )
        assert task["id"].startswith("sched_")
        assert task["next_run"] is not None
        assert _CRONITER_AVAILABLE or True  # smoke

    def test_roundtrip_reload(self, tmp_path):
        svc = _make_service(tmp_path)
        task = svc.create_task(
            name="T1", kind="workflow", task="x",
            schedule={"type": "daily", "at": "08:00"}, nodes=_WF_NODE,
        )
        # Nouvelle instance pointant sur le même fichier
        svc2 = _make_service(tmp_path)
        loaded = svc2.get_task(task["id"])
        assert loaded is not None
        assert loaded["name"] == "T1"

    def test_update_and_delete(self, tmp_path):
        svc = _make_service(tmp_path)
        task = svc.create_task(
            name="T1", kind="workflow", task="x",
            schedule={"type": "daily", "at": "08:00"}, nodes=_WF_NODE,
        )
        svc.update_task(task["id"], name="T1-renommée")
        assert svc.get_task(task["id"])["name"] == "T1-renommée"
        assert svc.delete_task(task["id"]) is True
        assert svc.get_task(task["id"]) is None

    def test_create_workflow_without_nodes_raises(self, tmp_path):
        svc = _make_service(tmp_path)
        with pytest.raises(ValueError):
            svc.create_task(name="X", kind="workflow", task="x",
                            schedule={"type": "daily", "at": "08:00"}, nodes=[])

    def test_set_enabled_resyncs_past_next_run(self, tmp_path):
        svc = _make_service(tmp_path)
        task = svc.create_task(
            name="T1", kind="workflow", task="x", enabled=False,
            schedule={"type": "interval", "seconds": 60}, nodes=_WF_NODE,
        )
        # Forcer une échéance passée
        svc._data["tasks"][0]["next_run"] = (datetime.now() - timedelta(hours=1)).isoformat()
        updated = svc.set_enabled(task["id"], True)
        assert updated["enabled"] is True
        assert _parse_future(updated["next_run"])


def _parse_future(iso):
    return datetime.fromisoformat(iso) > datetime.now()


# ----------------------------------------------------------------------
# Exécution
# ----------------------------------------------------------------------

class TestFire:

    def test_fire_collects_and_writes_output(self, tmp_path):
        executor = FakeExecutor()
        svc = _make_service(tmp_path, executor=executor)
        results = []
        svc.add_listener(results.append)
        task = svc.create_task(
            name="Veille", kind="workflow", task="Résume",
            schedule={"type": "interval", "seconds": 3600}, nodes=_WF_NODE,
        )
        svc._fire(svc.get_task(task["id"]))

        # Exécuteur appelé
        assert executor.calls == [("workflow", "Résume")]
        # Statut + fichier de sortie
        updated = svc.get_task(task["id"])
        assert updated["last_status"] == "success"
        assert updated["last_output_file"] and os.path.isfile(updated["last_output_file"])
        with open(updated["last_output_file"], encoding="utf-8") as fh:
            content = fh.read()
        assert "Résultat de la tâche planifiée." in content
        # Listener notifié
        assert results and results[0]["status"] == "success"
        assert results[0]["task_id"] == task["id"]
        # Historique
        assert len(svc.history()) == 1

    def test_fire_debate(self, tmp_path):
        executor = FakeExecutor()
        svc = _make_service(tmp_path, executor=executor)
        task = svc.create_task(
            name="Débat", kind="debate", task="L'IA va-t-elle remplacer les devs ?",
            schedule={"type": "interval", "seconds": 3600},
            debate={"agent_a": "code", "agent_b": "creative", "rounds": 1},
        )
        svc._fire(svc.get_task(task["id"]))
        assert executor.calls[0][0] == "debate"
        assert svc.get_task(task["id"])["last_status"] == "success"

    def test_fire_failure_status(self, tmp_path):
        svc = _make_service(tmp_path, executor=FakeExecutor(fail=True))
        task = svc.create_task(
            name="X", kind="workflow", task="x",
            schedule={"type": "interval", "seconds": 3600}, nodes=_WF_NODE,
        )
        svc._fire(svc.get_task(task["id"]))
        assert svc.get_task(task["id"])["last_status"] == "partial"

    def test_defer_on_busy(self, tmp_path):
        executor = FakeExecutor(busy=True)
        svc = _make_service(tmp_path, executor=executor)
        task = svc.create_task(
            name="X", kind="workflow", task="x",
            schedule={"type": "interval", "seconds": 60}, nodes=_WF_NODE,
        )
        before = svc.get_task(task["id"])["next_run"]
        fired = svc._maybe_fire(svc.get_task(task["id"]))
        assert fired is False
        assert executor.calls == []                      # rien exécuté
        after = svc.get_task(task["id"])
        assert after["last_status"] == "deferred"
        assert after["next_run"] == before               # next_run inchangé

    def test_maybe_fire_advances_next_run(self, tmp_path):
        svc = _make_service(tmp_path, executor=FakeExecutor())
        task = svc.create_task(
            name="X", kind="workflow", task="x",
            schedule={"type": "interval", "seconds": 60}, nodes=_WF_NODE,
        )
        # Forcer l'échéance dans le passé
        svc._data["tasks"][0]["next_run"] = (datetime.now() - timedelta(seconds=1)).isoformat()
        assert svc._maybe_fire(svc.get_task(task["id"])) is True
        assert _parse_future(svc.get_task(task["id"])["next_run"])


# ----------------------------------------------------------------------
# Rattrapage des tâches manquées
# ----------------------------------------------------------------------

class TestMissed:

    def test_recent_missed_is_fired(self, tmp_path):
        executor = FakeExecutor()
        svc = _make_service(tmp_path, executor=executor)
        task = svc.create_task(
            name="X", kind="workflow", task="x", run_if_missed=True,
            schedule={"type": "daily", "at": "08:00"}, nodes=_WF_NODE,
        )
        svc._data["tasks"][0]["next_run"] = (datetime.now() - timedelta(hours=2)).isoformat()
        svc._handle_missed()
        assert executor.calls == [("workflow", "x")]
        assert _parse_future(svc.get_task(task["id"])["next_run"])

    def test_old_missed_is_resynced_not_fired(self, tmp_path):
        executor = FakeExecutor()
        svc = _make_service(tmp_path, executor=executor, catch_up_window_hours=1)
        task = svc.create_task(
            name="X", kind="workflow", task="x", run_if_missed=True,
            schedule={"type": "daily", "at": "08:00"}, nodes=_WF_NODE,
        )
        svc._data["tasks"][0]["next_run"] = (datetime.now() - timedelta(hours=48)).isoformat()
        svc._handle_missed()
        assert executor.calls == []                       # pas exécuté
        assert _parse_future(svc.get_task(task["id"])["next_run"])  # resynchronisé

    def test_run_if_missed_false_skips(self, tmp_path):
        executor = FakeExecutor()
        svc = _make_service(tmp_path, executor=executor)
        task = svc.create_task(
            name="X", kind="workflow", task="x", run_if_missed=False,
            schedule={"type": "daily", "at": "08:00"}, nodes=_WF_NODE,
        )
        svc._data["tasks"][0]["next_run"] = (datetime.now() - timedelta(hours=2)).isoformat()
        svc._handle_missed()
        assert executor.calls == []
        assert _parse_future(svc.get_task(task["id"])["next_run"])


class TestHistoryCap:

    def test_history_capped(self, tmp_path):
        svc = _make_service(tmp_path, executor=FakeExecutor(), max_history=3)
        task = svc.create_task(
            name="X", kind="workflow", task="x",
            schedule={"type": "interval", "seconds": 3600}, nodes=_WF_NODE,
        )
        for _ in range(5):
            svc._fire(svc.get_task(task["id"]))
        assert len(svc.history()) == 3
