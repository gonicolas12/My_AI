"""
Scheduler proactif — exécution récurrente d'agents / workflows (type cron).

Ce module transforme l'assistant **réactif** en assistant **proactif** : il permet
de planifier l'exécution d'un agent seul, d'un workflow visuel (séquentiel /
parallèle / DAG) ou d'un débat, de façon récurrente (« chaque matin 8h », « tous
les lundis », « toutes les heures »…).

Principes de conception :

  - **Ne réimplémente PAS l'exécution.** Le scheduler délègue à
    ``relay.agent_relay.AgentRelayService`` — déjà un exécuteur *headless*
    (sans GUI Tkinter) qui sait lancer ``run_workflow`` / ``run_debate`` et
    streame ses résultats via un callback ``emit(event)``. Le scheduler se
    contente de **collecter** ces events en un résultat final.

  - **100% local, pas de service système.** Une simple boucle de thread daemon
    (``threading``) qui vit tant que le GUI ou le Relay est lancé. Persistance
    des définitions de tâches en JSON (``data/scheduled_tasks.json``), cohérent
    avec ``data/custom_agents.json``.

  - **Tâches manquées.** Au démarrage, les tâches dont l'échéance est passée
    (dans une fenêtre de rattrapage) sont exécutées une fois, si l'option
    ``run_if_missed`` est active.

  - **Défer-on-busy.** Si l'exécuteur est déjà occupé (l'utilisateur lance un
    workflow depuis le GUI ou le mobile), l'exécution planifiée est différée au
    prochain tick — on évite deux charges LLM concurrentes sur Ollama.

Les notifications de fin de tâche (toast OS, entrée GUI, message WebSocket
mobile) sont dispatchées via des *listeners* enregistrés par le GUI et le Relay,
plus une tentative de toast OS native (``winotify`` / ``plyer``, optionnels).
"""

import json
import os
import threading
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from utils.logger import setup_logger

# croniter est optionnel : seules les planifications de type "cron" en ont besoin.
# Les presets (daily / weekly / interval) sont calculés à la main.
try:
    from croniter import croniter as _croniter
    _CRONITER_AVAILABLE = True
except Exception:  # pragma: no cover - dépend de l'environnement
    _croniter = None
    _CRONITER_AVAILABLE = False

logger = setup_logger("Scheduler")

# 0 = Lundi … 6 = Dimanche (datetime.weekday()).
_WEEKDAY_LABELS = ["Lun", "Mar", "Mer", "Jeu", "Ven", "Sam", "Dim"]

_VALID_KINDS = ("single", "workflow", "debate")
_VALID_SCHEDULE_TYPES = ("daily", "weekly", "interval", "cron")


# ======================================================================
# Helpers
# ======================================================================

def _load_scheduler_config() -> Dict[str, Any]:
    """Charge la section ``scheduler`` de config.yaml (avec fallback vide)."""
    try:
        from core.config import get_config
        return dict(get_config().get_section("scheduler") or {})
    except Exception:  # pragma: no cover - config indisponible
        return {}


def _parse_dt(value: Optional[str]) -> Optional[datetime]:
    """Parse une date ISO ; retourne None si absente/invalide."""
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except (ValueError, TypeError):
        return None


def _parse_hhmm(value: Any) -> tuple[int, int]:
    """Parse "HH:MM" → (heure, minute) ; tolère les valeurs invalides."""
    try:
        hh, mm = str(value).split(":", 1)
        return max(0, min(23, int(hh))), max(0, min(59, int(mm)))
    except (ValueError, AttributeError):
        return 0, 0


# ======================================================================
# Collecte des résultats d'exécution
# ======================================================================

class _ResultCollector:
    """Agrège les events ``emit`` de ``run_workflow`` / ``run_debate``.

    Reconstruit le texte final par section (thread-safe : en mode parallèle,
    ``run_workflow`` appelle ``emit`` depuis plusieurs threads).
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.sections: List[Dict[str, Any]] = []
        self._by_id: Dict[Any, Dict[str, Any]] = {}
        self.topic: Optional[str] = None
        self.status: str = "error"      # success | partial | interrupted | error
        self.status_text: str = ""
        self.error: Optional[str] = None
        self.interrupted: bool = False

    def handle(self, event: Dict[str, Any]) -> None:
        """Callback ``emit`` passé à l'exécuteur."""
        etype = event.get("type")
        with self._lock:
            if etype == "agent_section_start":
                sec = {
                    "id": event.get("section_id"),
                    "title": event.get("title", ""),
                    "text": "",
                    "success": None,
                }
                self.sections.append(sec)
                self._by_id[sec["id"]] = sec
            elif etype == "agent_section_chunk":
                sec = self._by_id.get(event.get("section_id"))
                if sec is not None:
                    # Le texte émis est cumulatif → on remplace.
                    sec["text"] = event.get("text", "")
            elif etype == "agent_section_end":
                sec = self._by_id.get(event.get("section_id"))
                if sec is not None:
                    sec["success"] = event.get("success")
            elif etype == "agent_debate_topic":
                self.topic = event.get("topic")
            elif etype == "agent_exec_end":
                self.interrupted = bool(event.get("interrupted"))
                self.status_text = event.get("status_text", "")
                if event.get("success"):
                    self.status = "success"
                elif self.interrupted:
                    self.status = "interrupted"
                else:
                    self.status = "partial"
            elif etype == "agent_exec_error":
                self.error = event.get("message")
                self.status = "error"
                self.status_text = event.get("message", "")

    def summary(self, limit: int = 280) -> str:
        """Court résumé textuel (pour le toast / la notification)."""
        with self._lock:
            parts = [s["text"].strip() for s in self.sections if s["text"].strip()]
        text = "\n".join(parts).strip()
        return text[:limit].strip()

    def to_markdown(self, name: str, started: datetime) -> str:
        """Construit le rapport markdown complet sauvegardé sur disque."""
        with self._lock:
            sections = list(self.sections)
            topic, error, status_text = self.topic, self.error, self.status_text
        lines = [f"# {name}", "", f"_Exécuté le {started:%Y-%m-%d %H:%M:%S}_"]
        if status_text:
            lines.append(f"_{status_text}_")
        lines.append("")
        if topic:
            lines += [f"**Sujet :** {topic}", ""]
        for sec in sections:
            lines += [f"## {sec['title']}", "", sec["text"].strip(), ""]
        if error:
            lines += [f"> ⚠️ {error}", ""]
        return "\n".join(lines)


# ======================================================================
# Service de planification
# ======================================================================

class SchedulerService:
    """Planificateur maison : boucle de thread + persistance JSON.

    L'exécution est entièrement déléguée à un ``executor`` de type
    ``AgentRelayService`` (méthodes ``run_workflow`` / ``run_debate`` et
    propriété ``busy``). Instancié paresseusement si non fourni.
    """

    def __init__(
        self,
        executor: Optional[Any] = None,
        config: Optional[Dict[str, Any]] = None,
    ) -> None:
        cfg = config if config is not None else _load_scheduler_config()
        self._cfg = cfg

        self.enabled = bool(cfg.get("enabled", True))
        self.check_interval = max(5, int(cfg.get("check_interval", 30)))
        self.run_missed_on_startup = bool(cfg.get("run_missed_on_startup", True))
        self.catch_up_window_hours = float(cfg.get("catch_up_window_hours", 24))
        self.max_history = max(0, int(cfg.get("max_history", 200)))
        self.notify_desktop = bool(cfg.get("notify_desktop", True))
        self.notify_mobile = bool(cfg.get("notify_mobile", True))

        # Chemins résolus relativement à la racine projet (parent de core/).
        self._base = Path(__file__).resolve().parent.parent
        self._tasks_file = self._resolve(
            cfg.get("tasks_file", "data/scheduled_tasks.json")
        )
        self._output_dir = self._resolve(
            cfg.get("output_directory", "outputs/scheduled")
        )

        self._executor = executor
        self._listeners: List[Callable[[Dict[str, Any]], None]] = []

        self._lock = threading.RLock()
        self._stop_event = threading.Event()
        # Réveille la boucle immédiatement quand une tâche est créée/modifiée
        # afin que le firing soit instantané (attente précise jusqu'à l'échéance).
        self._wake_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._started = False
        self._current_exec_id: Optional[str] = None

        # Verrou inter-processus : coordonne le scheduler in-process (GUI/Relay)
        # et le runner headless lancé par le Planificateur de tâches Windows,
        # pour qu'une même tâche ne soit JAMAIS exécutée deux fois. Le détenteur
        # rafraîchit un « heartbeat » ; un verrou plus vieux que
        # _lock_stale_seconds est considéré abandonné (process mort).
        self._lock_path = self._resolve(cfg.get("lock_file", "data/scheduler.lock"))
        self._lock_id = uuid.uuid4().hex
        self._have_lock = False
        self._lock_stale_seconds = max(self.check_interval * 3, 120)
        self._hb_thread: Optional[threading.Thread] = None
        self._hb_stop = threading.Event()

        self._data: Dict[str, Any] = {"version": "7.9.0", "tasks": [], "history": []}
        self._load()

        logger.info(
            "SchedulerService initialisé (%d tâche(s), croniter=%s)",
            len(self._data["tasks"]), _CRONITER_AVAILABLE,
        )

    # ------------------------------------------------------------------
    # Exécuteur
    # ------------------------------------------------------------------

    @property
    def executor(self) -> Any:
        """Exécuteur d'agents (lazy). Voir relay/agent_relay.py."""
        if self._executor is None:
            from relay.agent_relay import AgentRelayService
            self._executor = AgentRelayService()
        return self._executor

    def set_executor(self, executor: Any) -> None:
        """Partage un exécuteur existant (ex. celui du Relay) avec le scheduler.

        Permet aux exécutions planifiées et aux exécutions mobiles de partager
        le même gate d'exécution unique (``_busy``).
        """
        self._executor = executor

    def add_listener(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        """Enregistre un listener appelé à la fin de chaque tâche.

        Le callback reçoit un dict résultat (voir ``_notify``). Utilisé par le
        GUI (toast in-app + entrée visible) et le Relay (broadcast WebSocket).
        """
        if callback not in self._listeners:
            self._listeners.append(callback)

    # ------------------------------------------------------------------
    # Persistance JSON (écriture atomique)
    # ------------------------------------------------------------------

    def _resolve(self, path: str) -> Path:
        p = Path(path)
        return p if p.is_absolute() else self._base / p

    def _load(self) -> None:
        with self._lock:
            try:
                if self._tasks_file.is_file():
                    with open(self._tasks_file, "r", encoding="utf-8") as fh:
                        data = json.load(fh) or {}
                    self._data = {
                        "version": data.get("version", "7.9.0"),
                        "tasks": list(data.get("tasks", [])),
                        "history": list(data.get("history", [])),
                    }
            except (json.JSONDecodeError, OSError) as exc:
                logger.warning("Chargement des tâches planifiées échoué : %s", exc)

    def _save(self) -> None:
        """Écriture atomique (tmp + replace), comme core/session_manager.py."""
        with self._lock:
            self._tasks_file.parent.mkdir(parents=True, exist_ok=True)
            tmp = self._tasks_file.with_suffix(".json.tmp")
            try:
                with open(tmp, "w", encoding="utf-8") as fh:
                    json.dump(self._data, fh, indent=2, ensure_ascii=False, default=str)
                tmp.replace(self._tasks_file)
            except OSError as exc:
                logger.warning("Sauvegarde des tâches planifiées échouée : %s", exc)
                if tmp.exists():
                    try:
                        tmp.unlink()
                    except OSError:
                        pass

    # ------------------------------------------------------------------
    # CRUD des tâches
    # ------------------------------------------------------------------

    def list_tasks(self) -> List[Dict[str, Any]]:
        """Retourne une copie des tâches planifiées."""
        with self._lock:
            return [dict(t) for t in self._data["tasks"]]

    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            task = self._get_task_locked(task_id)
            return dict(task) if task else None

    def _get_task_locked(self, task_id: str) -> Optional[Dict[str, Any]]:
        for task in self._data["tasks"]:
            if task.get("id") == task_id:
                return task
        return None

    def history(self) -> List[Dict[str, Any]]:
        with self._lock:
            return list(self._data["history"])

    def _validate(self, kind: str, schedule: Dict[str, Any]) -> None:
        if kind not in _VALID_KINDS:
            raise ValueError(f"kind invalide : {kind}")
        stype = (schedule or {}).get("type")
        if stype not in _VALID_SCHEDULE_TYPES:
            raise ValueError(f"type de planning invalide : {stype}")
        if stype == "cron" and not _CRONITER_AVAILABLE:
            raise ValueError(
                "Les plannings 'cron' nécessitent le paquet croniter "
                "(pip install croniter). Utilisez daily/weekly/interval sinon."
            )
        if stype == "cron":
            try:
                _croniter(schedule.get("expr", ""), datetime.now())
            except Exception as exc:
                raise ValueError(f"Expression cron invalide : {exc}") from exc
        if stype == "weekly" and not schedule.get("days"):
            raise ValueError("Le planning hebdomadaire requiert au moins un jour.")

    def create_task(
        self,
        name: str,
        kind: str,
        task: str,
        schedule: Dict[str, Any],
        nodes: Optional[List[Dict[str, Any]]] = None,
        connections: Optional[List[Dict[str, Any]]] = None,
        debate: Optional[Dict[str, Any]] = None,
        run_if_missed: bool = True,
        enabled: bool = True,
    ) -> Dict[str, Any]:
        """Crée une tâche planifiée et calcule sa prochaine exécution."""
        name = (name or "").strip()
        task = (task or "").strip()
        if not name:
            raise ValueError("Nom requis")
        self._validate(kind, schedule)
        if kind == "debate":
            debate = debate or {}
            if not debate.get("agent_a") or not debate.get("agent_b"):
                raise ValueError("Un débat requiert deux agents.")
        elif not (nodes or []):
            raise ValueError("Au moins un agent est requis.")

        now = datetime.now()
        nxt = self._compute_next_run(schedule, now)
        entry = {
            "id": f"sched_{uuid.uuid4().hex[:8]}",
            "name": name,
            "enabled": bool(enabled),
            "kind": kind,
            "task": task,
            "nodes": list(nodes or []),
            "connections": list(connections or []),
            "debate": debate,
            "schedule": dict(schedule),
            "run_if_missed": bool(run_if_missed),
            "created_at": now.isoformat(),
            "next_run": nxt.isoformat() if nxt else None,
            "last_run": None,
            "last_status": None,
            "last_output_file": None,
        }
        with self._lock:
            self._data["tasks"].append(entry)
            self._save()
        self._wake()  # firing instantané sans attendre le prochain poll
        logger.info("Tâche planifiée créée : '%s' (%s)", name, entry["id"])
        return dict(entry)

    def update_task(self, task_id: str, **fields: Any) -> Optional[Dict[str, Any]]:
        """Met à jour une tâche. Recalcule next_run si le planning change."""
        allowed = {
            "name", "task", "nodes", "connections", "debate", "schedule",
            "run_if_missed", "enabled", "kind",
        }
        with self._lock:
            task = self._get_task_locked(task_id)
            if task is None:
                return None
            schedule_changed = "schedule" in fields and fields["schedule"] != task.get("schedule")
            for key, value in fields.items():
                if key in allowed:
                    task[key] = value
            if "schedule" in fields or "kind" in fields:
                self._validate(task.get("kind", "workflow"), task.get("schedule") or {})
            if schedule_changed or task.get("next_run") is None:
                nxt = self._compute_next_run(task.get("schedule") or {}, datetime.now())
                task["next_run"] = nxt.isoformat() if nxt else None
            self._save()
        self._wake()
        return dict(task)

    def delete_task(self, task_id: str) -> bool:
        with self._lock:
            before = len(self._data["tasks"])
            self._data["tasks"] = [
                t for t in self._data["tasks"] if t.get("id") != task_id
            ]
            changed = len(self._data["tasks"]) != before
            if changed:
                self._save()
        return changed

    def set_enabled(self, task_id: str, enabled: bool) -> Optional[Dict[str, Any]]:
        """Active/désactive une tâche. Resynchronise next_run à la réactivation."""
        with self._lock:
            task = self._get_task_locked(task_id)
            if task is None:
                return None
            task["enabled"] = bool(enabled)
            if enabled:
                nr = _parse_dt(task.get("next_run"))
                if nr is None or nr <= datetime.now():
                    nxt = self._compute_next_run(task.get("schedule") or {}, datetime.now())
                    task["next_run"] = nxt.isoformat() if nxt else None
            self._save()
            result = dict(task)
        self._wake()
        return result

    def run_now(self, task_id: str) -> Dict[str, Any]:
        """Force l'exécution immédiate d'une tâche (bouton ▶ de l'UI).

        N'affecte pas la programmation (next_run). Renvoie un statut.
        """
        task = self.get_task(task_id)
        if task is None:
            return {"success": False, "error": "Tâche introuvable"}
        try:
            if self.executor.busy:
                return {"success": False, "error": "Exécuteur occupé, réessayez."}
        except Exception:
            pass
        threading.Thread(
            target=self._fire, args=(task,), kwargs={"manual": True},
            daemon=True, name=f"SchedFire-{task_id}",
        ).start()
        return {"success": True}

    # ------------------------------------------------------------------
    # Calcul de la prochaine exécution
    # ------------------------------------------------------------------

    def _compute_next_run(
        self, schedule: Dict[str, Any], after: datetime
    ) -> Optional[datetime]:
        """Prochaine échéance strictement postérieure à ``after`` (ou None)."""
        stype = (schedule or {}).get("type")
        if stype == "interval":
            seconds = max(1, int(schedule.get("seconds", 3600)))
            return after + timedelta(seconds=seconds)
        if stype == "daily":
            hh, mm = _parse_hhmm(schedule.get("at", "08:00"))
            cand = after.replace(hour=hh, minute=mm, second=0, microsecond=0)
            if cand <= after:
                cand += timedelta(days=1)
            return cand
        if stype == "weekly":
            days = sorted({int(d) for d in schedule.get("days", [])})
            if not days:
                return None
            hh, mm = _parse_hhmm(schedule.get("at", "08:00"))
            for offset in range(0, 8):
                cand = (after + timedelta(days=offset)).replace(
                    hour=hh, minute=mm, second=0, microsecond=0
                )
                if cand > after and cand.weekday() in days:
                    return cand
            return None
        if stype == "cron":
            if not _CRONITER_AVAILABLE:
                return None
            try:
                return _croniter(schedule.get("expr", ""), after).get_next(datetime)
            except Exception as exc:  # pragma: no cover - expr invalide
                logger.warning("Expression cron invalide : %s", exc)
                return None
        return None

    @staticmethod
    def describe_schedule(schedule: Dict[str, Any]) -> str:
        """Description lisible d'un planning (UI + notifications)."""
        stype = (schedule or {}).get("type")
        if stype == "interval":
            secs = int(schedule.get("seconds", 3600))
            if secs % 3600 == 0:
                return f"toutes les {secs // 3600} h"
            if secs % 60 == 0:
                return f"toutes les {secs // 60} min"
            return f"toutes les {secs} s"
        if stype == "daily":
            return f"tous les jours à {schedule.get('at', '08:00')}"
        if stype == "weekly":
            days = sorted({int(d) for d in schedule.get("days", [])})
            labels = ", ".join(_WEEKDAY_LABELS[d] for d in days if 0 <= d <= 6)
            return f"chaque {labels} à {schedule.get('at', '08:00')}"
        if stype == "cron":
            return f"cron : {schedule.get('expr', '')}"
        return "—"

    # ------------------------------------------------------------------
    # Boucle de planification
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Démarre la boucle de planification (idempotent)."""
        if not self.enabled:
            logger.info("Scheduler désactivé (scheduler.enabled = false)")
            return
        with self._lock:
            if self._started:
                return
            self._started = True
            self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._loop, daemon=True, name="SchedulerLoop"
        )
        self._thread.start()
        logger.info("Scheduler démarré (tick = %ds)", self.check_interval)

    def stop(self) -> None:
        """Arrête la boucle et interrompt une éventuelle exécution en cours."""
        with self._lock:
            if not self._started:
                return
            self._started = False
        self._stop_event.set()
        self._wake_event.set()  # débloque l'attente précise de la boucle
        exec_id = self._current_exec_id
        if exec_id and self._executor is not None:
            try:
                self._executor.interrupt(exec_id)
            except Exception:
                pass
        if self._thread is not None:
            self._thread.join(timeout=5)
        self._release_lock()

    @property
    def is_running(self) -> bool:
        return self._started

    def _loop(self) -> None:
        # Rattrapage des tâches manquées au démarrage (peut être long : on est
        # dans le thread dédié, la programmation reprend juste après).
        if self.run_missed_on_startup:
            try:
                if self._try_acquire_lock():
                    self._handle_missed()
            except Exception:
                logger.exception("Scheduler : rattrapage des tâches manquées échoué")
        while not self._stop_event.is_set():
            try:
                # N'exécute que si on détient le verrou (sinon un runner Windows
                # ou une autre instance est actif : on lui laisse la main).
                if self._try_acquire_lock():
                    self._tick()
            except Exception:
                logger.exception("Scheduler : tick échoué")
            # Attente PRÉCISE jusqu'à la prochaine échéance → firing instantané.
            # Bornée par check_interval pour re-scanner (tâches manquées). Le
            # réveil est immédiat si une tâche est créée/modifiée (_wake_event).
            self._wake_event.wait(self._next_wait_delay())
            self._wake_event.clear()

    def _next_wait_delay(self) -> float:
        """Secondes à attendre avant le prochain tick (= prochaine échéance).

        Retourne le délai jusqu'à la tâche due la plus proche, borné par
        ``check_interval``. ~0 si une tâche est déjà due (re-tick immédiat).
        """
        now = datetime.now()
        soonest: Optional[float] = None
        for task in self.list_tasks():
            if not task.get("enabled"):
                continue
            nr = _parse_dt(task.get("next_run"))
            if nr is None:
                continue
            secs = (nr - now).total_seconds()
            if secs <= 0:
                return 0.2  # déjà due → re-tick quasi immédiat
            soonest = secs if soonest is None else min(soonest, secs)
        if soonest is None:
            return float(self.check_interval)
        return max(0.2, min(float(self.check_interval), soonest))

    def _wake(self) -> None:
        """Réveille la boucle pour recalculer l'attente (tâche créée/modifiée)."""
        self._wake_event.set()

    def _tick(self) -> None:
        now = datetime.now()
        for task in self.list_tasks():
            if self._stop_event.is_set():
                break
            if not task.get("enabled"):
                continue
            nr = _parse_dt(task.get("next_run"))
            if nr is not None and nr <= now:
                self._maybe_fire(task)

    def _handle_missed(self) -> None:
        now = datetime.now()
        window = timedelta(hours=self.catch_up_window_hours)
        for task in self.list_tasks():
            if not task.get("enabled"):
                continue
            nr = _parse_dt(task.get("next_run"))
            if nr is None:
                self._reschedule(task["id"], now)
                continue
            if nr <= now:
                missed_recent = (now - nr) <= window
                if task.get("run_if_missed", True) and missed_recent:
                    logger.info("Tâche manquée rattrapée : '%s'", task.get("name"))
                    self._maybe_fire(task, missed=True)
                else:
                    # Trop ancienne ou rattrapage désactivé → resync sans exécuter.
                    self._reschedule(task["id"], now)

    def _reschedule(self, task_id: str, after: datetime) -> None:
        """Recalcule next_run sans exécuter."""
        with self._lock:
            task = self._get_task_locked(task_id)
            if task is None:
                return
            nxt = self._compute_next_run(task.get("schedule") or {}, after)
            task["next_run"] = nxt.isoformat() if nxt else None
            self._save()

    def _maybe_fire(self, task: Dict[str, Any], missed: bool = False) -> bool:
        """Programme la prochaine échéance puis exécute — sauf si occupé.

        Défer-on-busy : si l'exécuteur est déjà occupé, on marque la tâche
        ``deferred`` sans toucher à ``next_run`` (réessai au prochain tick).
        """
        try:
            busy = self.executor.busy
        except Exception:
            busy = False
        task_id = task["id"]
        if busy:
            with self._lock:
                cur = self._get_task_locked(task_id)
                if cur is not None:
                    cur["last_status"] = "deferred"
                    self._save()
            logger.info("Tâche '%s' différée (exécuteur occupé)", task.get("name"))
            return False

        # Avance next_run AVANT d'exécuter : une exécution longue ne peut pas
        # re-déclencher la même tâche, et un crash n'enclenche pas de boucle.
        self._reschedule(task_id, datetime.now())
        self._fire(task, missed=missed)
        return True

    # ------------------------------------------------------------------
    # Exécution d'une tâche
    # ------------------------------------------------------------------

    def _fire(self, task: Dict[str, Any], missed: bool = False, manual: bool = False) -> None:
        """Exécute la tâche via l'exécuteur et collecte le résultat."""
        task_id = task.get("id")
        name = task.get("name", task_id)
        kind = task.get("kind", "workflow")
        exec_id = f"schedexec_{uuid.uuid4().hex[:12]}"
        collector = _ResultCollector()
        started = datetime.now()
        self._current_exec_id = exec_id
        logger.info(
            "Scheduler : exécution de '%s' (%s)%s", name, task_id,
            " [manqué]" if missed else (" [manuel]" if manual else ""),
        )
        try:
            if kind == "debate":
                d = task.get("debate") or {}
                rounds = int(d.get("rounds", 3) or 3)
                self.executor.run_debate(
                    exec_id, d.get("agent_a"), d.get("agent_b"),
                    task.get("task", ""), rounds, collector.handle,
                )
            else:
                self.executor.run_workflow(
                    exec_id, task.get("task", ""),
                    task.get("nodes", []) or [], task.get("connections", []) or [],
                    collector.handle,
                )
        except Exception as exc:
            logger.exception("Scheduler : échec d'exécution de '%s'", name)
            collector.error = str(exc)
            collector.status = "error"
            collector.status_text = f"Erreur : {exc}"
        finally:
            self._current_exec_id = None

        finished = datetime.now()
        markdown = collector.to_markdown(name, started)
        output_file: Optional[str] = None
        try:
            output_file = self._write_output(task_id, markdown, started)
        except Exception:
            logger.exception("Scheduler : écriture du résultat échouée")

        with self._lock:
            cur = self._get_task_locked(task_id)
            if cur is not None:
                cur["last_run"] = started.isoformat()
                cur["last_status"] = collector.status
                cur["last_output_file"] = output_file
            self._append_history_locked({
                "task_id": task_id,
                "name": name,
                "started_at": started.isoformat(),
                "finished_at": finished.isoformat(),
                "status": collector.status,
                "output_file": output_file,
            })
            self._save()

        self._notify(name, task_id, collector, output_file, started, finished)

    def _append_history_locked(self, entry: Dict[str, Any]) -> None:
        history = self._data.setdefault("history", [])
        history.append(entry)
        if self.max_history and len(history) > self.max_history:
            del history[: len(history) - self.max_history]

    def _write_output(self, task_id: str, markdown: str, started: datetime) -> str:
        self._output_dir.mkdir(parents=True, exist_ok=True)
        fname = f"{task_id}_{started:%Y%m%d_%H%M%S}.md"
        path = self._output_dir / fname
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(markdown)
        return str(path)

    # ------------------------------------------------------------------
    # Notifications
    # ------------------------------------------------------------------

    def _notify(
        self,
        name: str,
        task_id: str,
        collector: _ResultCollector,
        output_file: Optional[str],
        started: datetime,
        finished: datetime,
    ) -> None:
        status = collector.status
        status_text = collector.status_text or status
        summary = collector.summary()

        os_shown = False
        if self.notify_desktop:
            icon = "✅" if status == "success" else "⚠️"
            title = f"{icon} Tâche planifiée : {name}"
            os_shown = self._notify_desktop(title, (summary or status_text)[:220])

        result = {
            "type": "scheduled_task_result",
            "task_id": task_id,
            "name": name,
            "status": status,
            "status_text": status_text,
            "summary": summary,
            "output_file": output_file,
            "started_at": started.isoformat(),
            "finished_at": finished.isoformat(),
            "os_toast_shown": os_shown,
        }
        for callback in list(self._listeners):
            try:
                callback(result)
            except Exception:
                logger.exception("Scheduler : listener de notification échoué")

    @staticmethod
    def _notify_desktop(title: str, message: str) -> bool:
        """Tente une notification OS native. Retourne True si affichée.

        Essaie winotify (Windows) puis plyer (cross-plateforme). En cas d'échec
        ou d'absence des deux, retourne False : le fallback in-app est assuré
        par le listener GUI.
        """
        try:
            from winotify import Notification  # type: ignore
            toast = Notification(
                app_id="My_AI", title=title, msg=message or " ",
            )
            toast.show()
            return True
        except Exception:
            pass
        try:
            from plyer import notification  # type: ignore
            notification.notify(
                title=title, message=message or " ", app_name="My_AI", timeout=10,
            )
            return True
        except Exception:
            return False

    # ------------------------------------------------------------------
    # Verrou inter-processus + exécution one-shot (runner headless)
    # ------------------------------------------------------------------

    def _read_lock(self) -> Optional[Dict[str, Any]]:
        try:
            with open(self._lock_path, "r", encoding="utf-8") as fh:
                return json.load(fh)
        except (OSError, json.JSONDecodeError):
            return None

    def _write_lock(self) -> None:
        self._lock_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self._lock_path.with_suffix(".lock.tmp")
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump({"owner": self._lock_id, "pid": os.getpid(),
                       "heartbeat": datetime.now().isoformat()}, fh)
        tmp.replace(self._lock_path)

    def _lock_held_by_other(self) -> bool:
        data = self._read_lock()
        if not data or data.get("owner") == self._lock_id:
            return False
        hb = _parse_dt(data.get("heartbeat"))
        if hb is None:
            return False
        return (datetime.now() - hb).total_seconds() < self._lock_stale_seconds

    def _try_acquire_lock(self) -> bool:
        """Tente de devenir le scheduler actif. Idempotent si déjà détenteur."""
        with self._lock:
            if self._have_lock:
                return True
            if self._lock_held_by_other():
                return False
            try:
                self._write_lock()
            except OSError as exc:
                logger.warning("Écriture du verrou scheduler échouée : %s", exc)
                return False
            self._have_lock = True
            self._start_heartbeat()
            return True

    def _start_heartbeat(self) -> None:
        if self._hb_thread is not None and self._hb_thread.is_alive():
            return
        self._hb_stop.clear()
        self._hb_thread = threading.Thread(
            target=self._heartbeat_loop, daemon=True, name="SchedulerHeartbeat"
        )
        self._hb_thread.start()

    def _heartbeat_loop(self) -> None:
        interval = max(15, self.check_interval)
        while not self._hb_stop.is_set() and self._have_lock:
            try:
                self._write_lock()
            except OSError:
                pass
            self._hb_stop.wait(interval)

    def _release_lock(self) -> None:
        with self._lock:
            was_owner = self._have_lock
            self._have_lock = False
            self._hb_stop.set()
        if not was_owner:
            return
        data = self._read_lock()
        if data and data.get("owner") == self._lock_id:
            try:
                self._lock_path.unlink()
            except OSError:
                pass

    def run_once(self) -> bool:
        """Exécute UN passage de planification puis rend la main (runner headless).

        Acquiert le verrou ; si un autre scheduler (GUI/Relay ou autre runner)
        est actif, ne fait rien et retourne False. Sinon : rattrape les tâches
        manquées + exécute les tâches dues, puis libère le verrou.
        """
        if not self._try_acquire_lock():
            logger.info("Scheduler déjà actif (verrou détenu) — runner ignoré.")
            return False
        try:
            if self.run_missed_on_startup:
                self._handle_missed()
            self._tick()
            return True
        finally:
            self._release_lock()


# ======================================================================
# Singleton module
# ======================================================================

_GLOBAL_SCHEDULER: Optional[SchedulerService] = None
_GLOBAL_LOCK = threading.Lock()


def get_scheduler(
    executor: Optional[Any] = None,
    config: Optional[Dict[str, Any]] = None,
) -> SchedulerService:
    """Retourne l'instance globale du scheduler (créée à la demande).

    Si un ``executor`` est fourni et que l'instance n'en a pas encore, il est
    partagé (permet au Relay d'injecter son ``AgentRelayService``).
    """
    global _GLOBAL_SCHEDULER
    with _GLOBAL_LOCK:
        if _GLOBAL_SCHEDULER is None:
            _GLOBAL_SCHEDULER = SchedulerService(executor=executor, config=config)
        elif executor is not None and _GLOBAL_SCHEDULER._executor is None:
            _GLOBAL_SCHEDULER.set_executor(executor)
    return _GLOBAL_SCHEDULER
