"""
Tâches planifiées de la page Agents (scheduler_ui.py de Tk)

Façade du SchedulerService (core/scheduler.py), sans le réécrire : liste,
création, modification, suppression, activation, exécution immédiate, et
« Exécuter même l'appli fermée » (tâche du Planificateur de tâches de
Windows, core/scheduler_runner.py). Les règles et les messages du dialogue de
Tk (_save_scheduled_task, _build_schedule, _resolve_source) sont repris ici :
la fenêtre et Tk enregistrent les mêmes tâches, dans le même fichier.

Événement publié : scheduler.changed (la liste a changé : la fenêtre la relit),
après chaque modification et à la fin de chaque tâche.
"""

import os
import re
import threading
from typing import Any, Callable, Dict, List, Optional, Tuple

from utils.logger import setup_logger

logger = setup_logger("DesktopSchedule")

# Jours de la semaine (0 = lundi), comme core/scheduler.py
DAY_LABELS = ["Lun", "Mar", "Mer", "Jeu", "Ven", "Sam", "Dim"]

_TIME_RE = re.compile(r"^(\d{1,2}):(\d{2})$")


class ScheduleError(Exception):
    """Action refusée ou en échec : message affiché."""


class ScheduleNotFound(ScheduleError):
    """Tâche introuvable."""


class WindowsTask:
    """Tâche du Planificateur de tâches de Windows (core/scheduler_runner.py)."""

    available = os.name == "nt"

    @staticmethod
    def registered() -> bool:
        """La tâche existe (schtasks /Query)."""
        from core import scheduler_runner  # pylint: disable=import-outside-toplevel
        return scheduler_runner.is_windows_task_registered()

    @staticmethod
    def register(interval_minutes: int) -> Tuple[bool, str]:
        """Crée la tâche (par utilisateur, sans droits d'administrateur)."""
        from core import scheduler_runner  # pylint: disable=import-outside-toplevel
        return scheduler_runner.register_windows_task(interval_minutes)

    @staticmethod
    def unregister() -> Tuple[bool, str]:
        """Supprime la tâche."""
        from core import scheduler_runner  # pylint: disable=import-outside-toplevel
        return scheduler_runner.unregister_windows_task()


def build_schedule(schedule: Dict[str, Any]) -> Dict[str, Any]:
    """Planning enregistré à partir des champs du dialogue (_build_schedule de Tk).

    Args:
        schedule: {type, at, days, every, unit, expr} ; type parmi daily,
            weekly, interval, cron ; unit : « minutes » ou « heures »

    Raises:
        ScheduleError: champ manquant ou invalide (messages de Tk)
    """
    stype = schedule.get("type")
    if stype in ("daily", "weekly"):
        at = str(schedule.get("at") or "").strip() or "08:00"
        match = _TIME_RE.match(at)
        if not match or int(match.group(1)) > 23 or int(match.group(2)) > 59:
            raise ScheduleError("❌ Heure invalide (HH:MM).")
        at = f"{int(match.group(1)):02d}:{match.group(2)}"
        if stype == "daily":
            return {"type": "daily", "at": at}
        days = sorted({int(day) for day in schedule.get("days") or [] if str(day).isdigit()
                       and 0 <= int(day) <= 6})
        if not days:
            raise ScheduleError("❌ Sélectionnez au moins un jour.")
        return {"type": "weekly", "days": days, "at": at}
    if stype == "interval":
        try:
            every = int(str(schedule.get("every", "")).strip())
        except ValueError:
            every = 0
        if every < 1:
            raise ScheduleError("❌ Intervalle invalide.")
        seconds = every * 3600 if schedule.get("unit") == "heures" else every * 60
        return {"type": "interval", "seconds": max(60, seconds)}
    if stype == "cron":
        expr = str(schedule.get("expr") or "").strip()
        if not expr:
            raise ScheduleError("❌ Expression cron requise.")
        return {"type": "cron", "expr": expr}
    raise ScheduleError("❌ Type de planning inconnu.")


class ScheduleService:
    """Tâches planifiées de la fenêtre, sur le scheduler de l'appli."""

    # pylint: disable=too-many-instance-attributes

    # pylint: disable-next=too-many-arguments
    def __init__(self, scheduler: Callable[[], Any], publish: Callable[..., Any], *,
                 agents: Callable[[], Dict[str, Any]],
                 notify: Optional[Callable[[str, str], None]] = None,
                 windows: Any = WindowsTask,
                 background_interval: Callable[[], int] = lambda: 1):
        """
        Args:
            scheduler: SchedulerService de l'appli (get_scheduler)
            publish: publication d'un événement sur le bus de la fenêtre
            agents: agents intégrés et personnalisés (AgentRelayService.list_agents)
            notify: notification brève de la fenêtre (niveau, message)
            windows: tâche du Planificateur de Windows (simulée en démonstration)
            background_interval: minutes entre deux passages du runner
                (scheduler.background_interval_minutes)
        """
        self._scheduler = scheduler
        self._publish = publish
        self._agents = agents
        self._notify = notify or (lambda _level, _message: None)
        self._windows = windows
        self._background_interval = background_interval
        self._lock = threading.Lock()
        self._registered: Optional[bool] = None

    # ── Lecture ─────────────────────────────────────────────────────────────

    def list(self) -> Dict[str, Any]:
        """Tâches, avec leur planning et leur source en clair, et l'exécution appli fermée."""
        # pylint: disable-next=import-outside-toplevel
        from core.scheduler import _CRONITER_AVAILABLE, SchedulerService
        names = self._agent_names()
        tasks = []
        for task in self._scheduler().list_tasks():
            view = dict(task)
            view["description"] = SchedulerService.describe_schedule(task.get("schedule") or {})
            view["source"] = self._describe_source(task, names)
            tasks.append(view)
        return {
            "tasks": tasks,
            "croniter": bool(_CRONITER_AVAILABLE),
            "background": {"available": bool(self._windows.available),
                           "registered": self._background_registered()},
        }

    def _background_registered(self) -> bool:
        """Tâche du Planificateur de Windows enregistrée (lue une fois : schtasks est lent)."""
        if not self._windows.available:
            return False
        with self._lock:
            if self._registered is None:
                try:
                    self._registered = bool(self._windows.registered())
                except Exception:  # pylint: disable=broad-except
                    self._registered = False
            return self._registered

    def _agent_names(self) -> Dict[str, Dict[str, Any]]:
        try:
            listing = self._agents()
        except Exception:  # pylint: disable=broad-except
            return {}
        return {agent["key"]: agent
                for agent in listing.get("builtin", []) + listing.get("custom", [])}

    @staticmethod
    def _describe_source(task: Dict[str, Any], names: Dict[str, Dict[str, Any]]) -> str:
        """Source en clair (_describe_source de Tk)."""
        if task.get("kind") == "debate":
            debate = task.get("debate") or {}
            first = names.get(debate.get("agent_a"), {}).get("name", debate.get("agent_a"))
            second = names.get(debate.get("agent_b"), {}).get("name", debate.get("agent_b"))
            return f"Débat : {first} vs {second}"
        nodes = task.get("nodes") or []
        if len(nodes) == 1:
            return f"Agent : {nodes[0].get('name', nodes[0].get('agent_type'))}"
        return f"Workflow : {len(nodes)} agents"

    # ── Création et modification ────────────────────────────────────────────

    def create(self, fields: Dict[str, Any]) -> Dict[str, Any]:
        """
        Crée une tâche (dialogue « Nouvelle tâche planifiée »).

        Args:
            fields: {name, task, schedule, run_if_missed, source} ; source :
                {kind: single | workflow | debate, agent, agent_a, agent_b,
                rounds, nodes, connections}

        Raises:
            ScheduleError: champ manquant ou invalide (messages de Tk)
        """
        name, text, schedule = self._common(fields)
        kind, nodes, connections, debate = self._resolve_source(fields.get("source") or {})
        try:
            task = self._scheduler().create_task(
                name=name, kind=kind, task=text, schedule=schedule, nodes=nodes,
                connections=connections, debate=debate,
                run_if_missed=bool(fields.get("run_if_missed", True)))
        except ValueError as exc:
            raise ScheduleError(f"❌ {exc}") from exc
        self._changed("✅ Tâche planifiée enregistrée")
        return task

    def update(self, task_id: str, fields: Dict[str, Any]) -> Dict[str, Any]:
        """Modifie une tâche : nom, tâche, planning, rattrapage ; la source reste figée (Tk)."""
        name, text, schedule = self._common(fields)
        try:
            task = self._scheduler().update_task(
                task_id, name=name, task=text, schedule=schedule,
                run_if_missed=bool(fields.get("run_if_missed", True)))
        except ValueError as exc:
            raise ScheduleError(f"❌ {exc}") from exc
        if task is None:
            raise ScheduleNotFound("❌ Tâche introuvable")
        self._changed("✅ Tâche planifiée enregistrée")
        return task

    @staticmethod
    def _common(fields: Dict[str, Any]) -> Tuple[str, str, Dict[str, Any]]:
        """Nom, tâche et planning, vérifiés dans l'ordre du dialogue de Tk."""
        name = str(fields.get("name") or "").strip()
        if not name:
            raise ScheduleError("❌ Nom requis.")
        text = str(fields.get("task") or "").strip()
        if not text:
            raise ScheduleError("❌ Tâche / sujet requis.")
        return name, text, build_schedule(fields.get("schedule") or {})

    def _resolve_source(self, source: Dict[str, Any]
                        ) -> Tuple[str, List[Dict[str, Any]], List[Dict[str, Any]],
                                   Optional[Dict[str, Any]]]:
        """(kind, nœuds, liens, débat) de la source choisie (_resolve_source de Tk)."""
        kind = source.get("kind")
        if kind == "debate":
            first, second = source.get("agent_a"), source.get("agent_b")
            if not first or not second:
                raise ScheduleError("❌ Choisissez deux agents.")
            if first == second:
                raise ScheduleError("❌ Choisissez deux agents différents.")
            try:
                rounds = max(1, min(10, int(source.get("rounds") or 3)))
            except (TypeError, ValueError):
                rounds = 3
            return "debate", [], [], {"agent_a": first, "agent_b": second, "rounds": rounds}
        if kind == "workflow":
            nodes = [self._node(item) for item in source.get("nodes") or []]
            if not nodes:
                raise ScheduleError("❌ Le canvas est vide.")
            connections = [{"from": str(item.get("from")), "to": str(item.get("to"))}
                           for item in source.get("connections") or []]
            return "workflow", nodes, connections, None
        key = source.get("agent")
        if not key:
            raise ScheduleError("❌ Choisissez un agent.")
        agent = self._agent_names().get(key)
        if agent is None:
            raise ScheduleError(f"❌ Agent introuvable : {key}")
        # Agent seul : un workflow d'un nœud, comme Tk
        return "workflow", [{"id": "n1", "agent_type": key, "name": agent.get("name", key),
                             "color": agent.get("color", "#3b82f6"),
                             "icon": agent.get("icon", "🤖")}], [], None

    @staticmethod
    def _node(item: Dict[str, Any]) -> Dict[str, Any]:
        """Nœud du canvas figé dans la tâche (identifiants en texte, comme Tk)."""
        return {"id": str(item.get("id")), "agent_type": str(item.get("agent_type", "")),
                "name": str(item.get("name", "")), "color": str(item.get("color") or "#3b82f6"),
                "icon": str(item.get("icon") or "🤖")}

    # ── Actions de la liste ─────────────────────────────────────────────────

    def delete(self, task_id: str) -> None:
        """Supprime une tâche (après confirmation dans la fenêtre)."""
        if not self._scheduler().delete_task(task_id):
            raise ScheduleNotFound("❌ Tâche introuvable")
        self._changed("✕ Tâche supprimée", level="error")

    def set_enabled(self, task_id: str, enabled: bool) -> Dict[str, Any]:
        """Active ou désactive une tâche (prochaine échéance recalculée à l'activation)."""
        task = self._scheduler().set_enabled(task_id, bool(enabled))
        if task is None:
            raise ScheduleNotFound("❌ Tâche introuvable")
        self._changed()
        return task

    def run_now(self, task_id: str) -> None:
        """Exécute une tâche tout de suite (▶), sans toucher à sa programmation."""
        result = self._scheduler().run_now(task_id)
        if not result.get("success"):
            raise ScheduleError(f"❌ {result.get('error') or 'Échec'}")
        self._notify("success", "▶ Exécution lancée…")

    def set_background(self, enabled: bool) -> Dict[str, Any]:
        """« Exécuter même l'appli fermée » : tâche du Planificateur de Windows créée ou ôtée."""
        if not self._windows.available:
            raise ScheduleError("❌ Disponible uniquement sous Windows.")
        try:
            if enabled:
                ok, message = self._windows.register(max(1, int(self._background_interval())))
            else:
                ok, message = self._windows.unregister()
        except Exception as exc:  # pylint: disable=broad-except
            ok, message = False, str(exc)
        with self._lock:
            if ok:
                self._registered = bool(enabled)
            registered = bool(self._registered)
        self._notify("success" if ok else "error", f"{'✅' if ok else '❌'} {message}")
        self._publish("scheduler.changed", {})
        return {"registered": registered, "ok": ok, "message": message}

    def task_finished(self, _result: Dict[str, Any]) -> None:
        """Fin d'une tâche (listener du scheduler) : dernier résultat, prochaine échéance."""
        self._publish("scheduler.changed", {})

    def _changed(self, message: str = "", level: str = "success") -> None:
        self._publish("scheduler.changed", {})
        if message:
            self._notify(level, message)
