"""
Page Agents de la fenêtre (interfaces/agents/ de Tk)

Expose l'exécuteur d'agents partagé, AgentRelayService (relay/agent_relay.py),
sans le réécrire : liste des agents, agents personnalisés, exécution d'un
agent seul, d'un workflow (séquentiel, parallèle, DAG) ou d'un débat, et
arrêt. Une seule exécution à la fois, partout : la page Agents, le mobile et
le scheduler partagent le même exécuteur (cf. lifecycle.py, agent_service).

Chaque exécution devient un fil (D32) : sa tâche, son workflow, la sortie de
chaque agent et son statut, gardés pour être rouverts, y compris après un
redémarrage (D33 : les 50 derniers, dans data/agent_runs.json). Les
exécutions lancées par le téléphone (Relay) et par les tâches planifiées
deviennent aussi des fils (D37) : le Relay et le scheduler reçoivent
l'exécuteur à travers SharedExecutor, qui les relaie et en garde une copie.

Autour des fils : statistiques (tâches, agents, taux de succès, sur les fils
gardés), temps d'inférence et tokens/s de chaque agent (relevé de fin de flux
d'Ollama gardé par LocalLLM, D17 : aucune requête en plus), et notification du
système à la fin d'un fil long de la page, fenêtre sans focus (comme Tk).

Événements publiés (préfixe « agents. ») : ceux d'AgentRelayService, repris
tels quels (agent_exec_start, agent_section_start, agent_section_end,
agent_node_status, agent_exec_end, agent_exec_error…), sauf le texte des
sections. AgentRelayService renvoie à chaque fragment le texte cumulé de la
section ; la fenêtre en reçoit seulement la suite (agent_section_delta), ou le
texte entier s'il a changé autrement (agent_section_text) : le bus garde les
derniers événements pour la reprise après une reconnexion, et des textes
cumulés y pèseraient des dizaines de Mo. S'y ajoutent run_created (nouveau
fil), runs_changed (liste des fils modifiée) et list_changed (agents
personnalisés modifiés).
"""

import json
import os
import re
import threading
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from core.chat_service import ChatError, file_type_for, folder_attachment_files
from core.i18n import tr
from interfaces.desktop import files as local_files
from utils.logger import setup_logger

logger = setup_logger("DesktopAgents")

PROJECT_ROOT = Path(__file__).resolve().parents[2]
# Fils d'exécution gardés d'un lancement à l'autre (D33), ignoré par git
RUNS_FILE = PROJECT_ROOT / "data" / "agent_runs.json"
MAX_RUNS = 50

# Code fourni à un agent (pièce jointe « Code ») : gardé dans le fil pour
# montrer en diff le code qu'il modifie (§8 du prompt), dans cette limite
MAX_CODE_SOURCE = 200_000

# Messages de Tk (execution.py, debate.py), repris par la fenêtre : clés du
# catalogue (core/locales), traduites à l'envoi
NO_AGENT = "agents.workflow.noAgent"
EMPTY_TASK = "agents.workflow.emptyTask"
BUSY = "agents.workflow.busy"
INTERRUPTED = "agents.interrupted"
DEBATE_BUSY = "agents.debate.busy"
DEBATE_SAME_AGENT = "agents.debate.sameAgent"
DEBATE_NO_TOPIC = "agents.debate.noTopic"
DEBATE_INTERRUPTED = "agents.debateInterrupted"

# Refus d'AgentRelayService quand une exécution est en cours (run_workflow, run_debate)
EXECUTOR_BUSY = "agents.busy"

# Origine d'un fil : la page, le téléphone (Relay) ou une tâche planifiée (D37)
ORIGINS = ("desktop", "mobile", "scheduled")
# Identifiant des exécutions du scheduler (core/scheduler.py, _fire)
SCHEDULED_PREFIX = "schedexec_"

# Notification du système : fil de plus de 8 s, fenêtre sans focus (Tk, execution.py)
NOTIFY_MIN_SECONDS = 8

# Statuts d'un nœud du canvas (WorkflowCanvas.STATUS_META de Tk)
NODE_STATUSES = ("idle", "running", "done", "error")

# Libellés des statuts de nœud, pour l'export Markdown (clés du catalogue)
_STATUS_LABELS = {status: f"agents.status.{status}" for status in NODE_STATUSES}

# Types de pièces jointes du menu « + » (types de l'interface Tk)
ATTACH_TYPES = ("PDF", "DOCX", "Excel", "PowerPoint", "Code", "Image")

_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,80}$")


class AgentsError(Exception):
    """Action refusée ou en échec : message affiché."""


class RunNotFound(AgentsError):
    """Fil introuvable."""


def _now() -> str:
    # À la milliseconde : la durée d'un agent rapide ne tombe pas à zéro
    return datetime.now().isoformat(timespec="milliseconds")


def _excerpt(text: str, size: int = 160) -> str:
    """Début d'un texte, sur une ligne."""
    line = " ".join((text or "").split())
    return line if len(line) <= size else line[: size - 1].rstrip() + "…"


def _plan_view(plan: Dict[str, Any]) -> Dict[str, Any]:
    """Plan d'exécution (compute_execution_plan) sans la table des nœuds."""
    return {
        "mode": plan.get("mode", "empty"),
        "steps": [list(step.get("nodes", [])) for step in plan.get("steps", [])],
        "isolated": list(plan.get("isolated", [])),
    }


def _debate_node(node_id: str, agent: Dict[str, Any]) -> Dict[str, Any]:
    """Agent d'un débat, rangé comme un nœud du fil (type, nom, couleur)."""
    return {"id": node_id, "agent_type": agent["key"], "name": agent.get("name") or agent["key"],
            "color": agent.get("color") or "#8b5cf6", "icon": agent.get("icon") or "🤖"}


def _clamp_rounds(rounds: Any) -> int:
    """Nombre de tours d'un débat : de 1 à 10, 3 par défaut (debate.py de Tk)."""
    try:
        return max(1, min(10, int(rounds or 3)))
    except (TypeError, ValueError):
        return 3


class Run:
    """Un fil : une exécution de la page Agents, avec la sortie de chaque agent."""

    # pylint: disable=too-many-instance-attributes

    def __init__(self, data: Dict[str, Any]):
        self.id: str = data["id"]
        self.kind: str = data.get("kind", "workflow")
        self.title: str = data.get("title", "")
        self.task: str = data.get("task", "")
        self.attachments: List[Dict[str, str]] = list(data.get("attachments") or [])
        self.sources: List[Dict[str, str]] = list(data.get("sources") or [])
        self.nodes: List[Dict[str, Any]] = list(data.get("nodes") or [])
        self.connections: List[Dict[str, Any]] = list(data.get("connections") or [])
        self.plan: Dict[str, Any] = dict(data.get("plan") or {})
        self.mode: Optional[str] = data.get("mode")
        self.status: str = data.get("status", "running")
        self.status_text: str = data.get("status_text", "")
        self.error: Optional[str] = data.get("error")
        self.started_at: str = data.get("started_at") or _now()
        self.finished_at: Optional[str] = data.get("finished_at")
        self.duration_ms: Optional[int] = data.get("duration_ms")
        self.sections: List[Dict[str, Any]] = [dict(s) for s in data.get("sections") or []]
        self.node_status: Dict[str, str] = dict(data.get("node_status") or {})
        origin = data.get("origin")
        self.origin: str = origin if origin in ORIGINS else "desktop"
        # Débat : {agent_a, agent_b, rounds}
        self.debate: Optional[Dict[str, Any]] = data.get("debate")
        # Tâche planifiée : {task_id, name, output_file}
        self.schedule: Optional[Dict[str, Any]] = data.get("schedule")
        # État du fil vivant, jamais enregistré
        self.stop_requested = False
        self.forwarded = False  # au moins un événement reçu de l'exécuteur
        self.started_clock = time.perf_counter()
        self.section_clocks: Dict[str, float] = {}

    def view(self) -> Dict[str, Any]:
        """Fil complet, pour la fenêtre et le fichier des fils."""
        return {
            "id": self.id, "kind": self.kind, "origin": self.origin, "title": self.title,
            "task": self.task, "attachments": self.attachments, "sources": self.sources,
            "nodes": self.nodes, "connections": self.connections, "plan": self.plan,
            "debate": self.debate, "schedule": self.schedule,
            "mode": self.mode, "status": self.status, "status_text": self.status_text,
            "error": self.error, "started_at": self.started_at,
            "finished_at": self.finished_at, "duration_ms": self.duration_ms,
            "sections": self.sections, "node_status": self.node_status,
        }

    def summary(self) -> Dict[str, Any]:
        """Ligne de la liste des fils."""
        first = self.nodes[0] if self.nodes else {}
        return {
            "id": self.id, "kind": self.kind, "origin": self.origin, "title": self.title,
            "task": _excerpt(self.task), "status": self.status,
            "status_text": self.status_text, "started_at": self.started_at,
            "finished_at": self.finished_at, "duration_ms": self.duration_ms,
            "agent_type": first.get("agent_type"), "color": first.get("color"),
            "agents": len(self.nodes),
            "schedule_task_id": (self.schedule or {}).get("task_id"),
        }

    def section(self, section_id: Any) -> Optional[Dict[str, Any]]:
        """Section d'un agent (identifiant du nœud, ou « deb_N » pour un débat)."""
        return next((s for s in self.sections if s["id"] == section_id), None)

    def node(self, node_id: Any) -> Dict[str, Any]:
        """Nœud du workflow de ce fil ({} s'il est inconnu)."""
        return next((n for n in self.nodes if n.get("id") == node_id), {})

    def finish(self, status: str, status_text: str = "", error: Optional[str] = None) -> None:
        """Fin du fil : statut, durée ; les sections restées ouvertes sont closes."""
        self.status = status
        self.status_text = status_text or self.status_text
        self.error = error
        self.finished_at = _now()
        self.duration_ms = int((time.perf_counter() - self.started_clock) * 1000)
        for section in self.sections:
            if section.get("status") == "running":
                section["status"] = "error"
        for key, value in list(self.node_status.items()):
            if value == "running":
                self.node_status[key] = "error"


def _interrupted_text(run: Run) -> str:
    """Texte d'un fil arrêté : celui d'AgentRelayService pour un débat, celui de Tk sinon."""
    return tr(DEBATE_INTERRUPTED if run.kind == "debate" else INTERRUPTED)


def notification_text(run: Run) -> Tuple[str, str]:
    """Titre et message de la notification de fin d'un fil (_notify_task_complete de Tk).

    Tk ne notifiait pas la fin d'un débat ; la fenêtre le fait, avec son texte
    de fin (« ✅ Débat terminé (3 tours) ») et le sujet.
    """
    if run.kind == "agent":
        name = run.nodes[0].get("name", "") if run.nodes else ""
        icon = "✅" if run.status == "done" else "❌"
        return tr("agents.notify.agentDone", icon=icon, name=name), run.task[:120]
    if run.kind == "debate":
        return run.status_text or tr("agents.notify.debateDone"), run.task[:120]
    answered = [s for s in run.sections if s.get("status") in ("done", "error")]
    rate = sum(s.get("status") == "done" for s in answered) / max(len(answered), 1)
    return tr("agents.notify.workflowDone"), tr("agents.notify.workflowRate",
                                                 rate=f"{rate:.0%}", task=run.task[:90])


class AgentsService:
    """Agents de la fenêtre : liste, agents personnalisés, fils d'exécution, workflows."""

    # pylint: disable=too-many-instance-attributes,too-many-public-methods

    # pylint: disable-next=too-many-arguments
    def __init__(self, executor: Callable[[], Any], publish: Callable[..., Any], *,
                 runs_file: Path = RUNS_FILE,
                 notify: Optional[Callable[[str, str], None]] = None,
                 last_seq: Optional[Callable[[], int]] = None,
                 window_focused: Optional[Callable[[], bool]] = None,
                 os_notify: Optional[Callable[[str, str], Any]] = None,
                 on_inference: Optional[Callable[[float, float], None]] = None,
                 find_scheduled: Optional[Callable[..., Optional[Dict[str, Any]]]] = None):
        """
        Args:
            executor: exécuteur d'agents partagé (AgentRelayService), créé au premier usage
            publish: publication d'un événement sur le bus de la fenêtre
            runs_file: fichier des fils (data/agent_runs.json)
            notify: notification brève de la fenêtre (niveau, message)
            last_seq: numéro du dernier événement publié (lectures de l'état)
            window_focused: la fenêtre a le focus (signalé par la page)
            os_notify: notification du système (titre, message) ; None : aucune
            on_inference: fin d'un agent (durée en ms, tokens/s), pour le moniteur
            find_scheduled: tâche planifiée d'une exécution du scheduler
                (texte, nœuds, débat), pour titrer son fil
        """
        self._executor = executor
        self._publish = publish
        self._notify = notify or (lambda _level, _message: None)
        self._last_seq = last_seq or (lambda: 0)
        self._window_focused = window_focused or (lambda: True)
        self._os_notify = os_notify
        self._on_inference = on_inference
        self._find_scheduled = find_scheduled or (lambda *_args: None)
        self._runs_file = Path(runs_file)
        # Verrou réentrant : un événement de l'exécuteur peut suivre un arrêt
        # demandé dans le même fil
        self._lock = threading.RLock()
        self._save_lock = threading.Lock()
        self._runs: List[Run] = self._load()
        self._active: Optional[Run] = None
        # Pièces jointes de la zone de tâche : la fenêtre peut en montrer la vignette
        self._known: Set[str] = set()
        # Exécuteur vu du Relay et du scheduler (D37)
        self._tap: Optional["SharedExecutor"] = None

    # ── Agents ──────────────────────────────────────────────────────────────

    def list(self) -> Dict[str, Any]:
        """Agents intégrés et personnalisés (relit data/custom_agents.json)."""
        return self._executor().list_agents()

    def create(self, name: str, role: str) -> Dict[str, Any]:
        """Crée un agent personnalisé : son prompt système est rédigé par le modèle."""
        result = self._executor().create_agent(name, role)
        return self._agent_changed(result, tr("agents.created"))

    def edit(self, key: str, name: str, role: str) -> Dict[str, Any]:
        """Modifie un agent personnalisé ; un nouveau rôle fait réécrire son prompt."""
        result = self._executor().edit_agent(key, name, role)
        return self._agent_changed(result, tr("agents.edited"))

    def delete(self, key: str) -> None:
        """Supprime un agent personnalisé."""
        result = self._executor().delete_agent(key)
        if not result.get("success"):
            raise AgentsError(f"❌ {result.get('error') or tr('agents.deleteFailed')}")
        self._publish("agents.list_changed", {})
        # Message et couleur de Tk (_delete_custom_agent)
        self._notify("error", tr("agents.deleted"))

    def _agent_changed(self, result: Dict[str, Any], message: str) -> Dict[str, Any]:
        if not result.get("success"):
            raise AgentsError(tr("agents.operationFailed",
                                 error=result.get("error") or tr("agents.operationImpossible")))
        self._publish("agents.list_changed", {})
        self._notify("success", message)
        return result.get("agent") or {}

    # ── Fils d'exécution ────────────────────────────────────────────────────

    def runs(self) -> Dict[str, Any]:
        """Liste des fils, du plus récent au plus ancien, et le seq de cette lecture."""
        with self._lock:
            seq = self._last_seq()
            return {
                "runs": [run.summary() for run in self._runs],
                "active": self._active.id if self._active else None,
                "busy": self._busy(),
                "stats": self._stats(),
                "seq": seq,
            }

    def _stats(self) -> Dict[str, Any]:
        """Statistiques de Tk (stats_section.py), calculées sur les fils gardés (D33).

        Tâches exécutées : agents qui ont répondu (une section close) ; agents
        actifs : types d'agents différents employés ; taux de succès : part des
        fils terminés qui ont réussi (None tant qu'aucun n'est terminé).
        """
        tasks = 0
        kinds: Set[str] = set()
        for run in self._runs:
            for section in run.sections:
                if section.get("status") in ("done", "error"):
                    tasks += 1
                if section.get("agent_type"):
                    kinds.add(str(section["agent_type"]))
        ended = [run for run in self._runs if run.status != "running"]
        rate = (round(100 * sum(run.status == "done" for run in ended) / len(ended))
                if ended else None)
        return {"tasks": tasks, "agents": len(kinds), "success_rate": rate}

    def run(self, run_id: str) -> Dict[str, Any]:
        """Fil complet (sorties comprises), et le seq de cette lecture."""
        with self._lock:
            seq = self._last_seq()
            return {"run": self._find(run_id).view(), "seq": seq}

    def known_paths(self) -> Set[str]:
        """Pièces jointes de la zone de tâche (vignettes des images)."""
        with self._lock:
            return set(self._known)

    def _busy(self) -> bool:
        try:
            return bool(self._executor().busy)
        except Exception:  # pylint: disable=broad-except
            return False

    def busy(self) -> bool:
        """Une exécution est en cours ou se prépare (lecture des pièces jointes comprise)."""
        with self._lock:
            return self._active is not None or self._busy()

    def _find(self, run_id: str) -> Run:
        run = next((r for r in self._runs if r.id == run_id), None)
        if run is None:
            raise RunNotFound(tr("agents.runNotFound"))
        return run

    def start(self, task: str, nodes: List[Dict[str, Any]],
              connections: List[Dict[str, Any]],
              attachments: Optional[List[Dict[str, Any]]] = None) -> str:
        """
        Lance un agent seul ou un workflow, dans un fil d'exécution dédié.

        Args:
            task: tâche saisie (sans le contenu des pièces jointes)
            nodes: nœuds du canvas [{id, agent_type, name, color, icon, x, y}]
            connections: liens du canvas [{from, to}]
            attachments: pièces jointes [{path, type}]

        Returns:
            Identifiant du fil (exec_id d'AgentRelayService)

        Raises:
            AgentsError: aucun agent, tâche vide, exécution déjà en cours,
                pièce jointe introuvable
        """
        task = (task or "").strip()
        if not nodes:
            raise AgentsError(tr(NO_AGENT))
        if not task:
            raise AgentsError(tr(EMPTY_TASK))
        files = [self._attachment(item.get("path", ""), item.get("type"))
                 for item in attachments or []]
        executor = self._executor()
        plan = executor.compute_execution_plan(nodes, connections)
        single = len(nodes) == 1
        run = Run({
            "id": f"exec_{uuid.uuid4().hex}",
            "kind": "agent" if single else "workflow",
            "title": (nodes[0].get("name", "Agent") if single
                      else tr("agents.title.workflow", count=len(nodes))),
            "task": task,
            "attachments": files,
            "sources": self._code_sources(files),
            "nodes": nodes,
            # Liens valides seulement (deux extrémités connues), comme le plan
            "connections": plan.get("connections", []),
            "plan": _plan_view(plan),
            "node_status": {str(node["id"]): "idle" for node in nodes},
        })
        self._begin(run, tr(BUSY))
        threading.Thread(target=self._execute, args=(run,), name="agents-run", daemon=True).start()
        return run.id

    def start_debate(self, agent_a: str, agent_b: str, topic: str, rounds: int = 3) -> str:
        """
        Lance un débat entre deux agents (debate.py de Tk), dans un fil dédié.

        Args:
            agent_a: agent proposant (clé d'un agent intégré ou personnalisé)
            agent_b: agent opposant
            topic: sujet du débat
            rounds: nombre de tours, de 1 à 10

        Returns:
            Identifiant du fil

        Raises:
            AgentsError: agents identiques ou inconnus, sujet vide, exécution en cours
        """
        topic = (topic or "").strip()
        if not agent_a or not agent_b or agent_a == agent_b:
            raise AgentsError(tr(DEBATE_SAME_AGENT))
        if not topic:
            raise AgentsError(tr(DEBATE_NO_TOPIC))
        rounds = _clamp_rounds(rounds)
        known = self._agents_by_key()
        first, second = known.get(agent_a), known.get(agent_b)
        if first is None or second is None:
            raise AgentsError(tr("agents.agentNotFound",
                                 key=agent_a if first is None else agent_b))
        run = Run({
            "id": f"exec_{uuid.uuid4().hex}",
            "kind": "debate",
            "title": tr("agents.title.debate", a=first["name"], b=second["name"]),
            "task": topic,
            "nodes": [_debate_node("a", first), _debate_node("b", second)],
            "debate": {"agent_a": agent_a, "agent_b": agent_b, "rounds": rounds},
            "plan": {"mode": "debate", "steps": [], "isolated": []},
        })
        self._begin(run, tr(DEBATE_BUSY))
        threading.Thread(target=self._execute, args=(run,), name="agents-debate",
                         daemon=True).start()
        return run.id

    def _agents_by_key(self) -> Dict[str, Dict[str, Any]]:
        """Agents intégrés et personnalisés, par clé."""
        listing = self._executor().list_agents()
        return {agent["key"]: agent
                for agent in listing.get("builtin", []) + listing.get("custom", [])}

    def _begin(self, run: Run, busy_message: str) -> None:
        """Fil en cours : refusé si une exécution est déjà en cours, sinon publié et enregistré."""
        with self._lock:
            if self._active is not None or self._busy():
                raise AgentsError(busy_message)
            self._active = run
            self._runs.insert(0, run)
            self._trim()
            self._publish("agents.run_created", {"run": run.view()})
        self._save()

    def stop(self, run_id: Optional[str] = None) -> bool:
        """Arrête le fil en cours (Arrêter, Échap) ; faux s'il n'y en a pas."""
        with self._lock:
            run = self._active
            if run is None or (run_id and run.id != run_id) or run.status != "running":
                return False
            run.stop_requested = True
            forwarded = run.forwarded
        if forwarded:
            self._executor().interrupt(run.id)
        return True

    def delete_run(self, run_id: str) -> None:
        """Supprime un fil terminé."""
        with self._lock:
            run = self._find(run_id)
            if run is self._active:
                raise AgentsError(tr("agents.stopFirst"))
            self._runs.remove(run)
            self._publish("agents.runs_changed", {})
        self._save()

    def clear_runs(self) -> int:
        """Efface l'historique des fils, sauf celui en cours ; renvoie le nombre effacé."""
        with self._lock:
            kept = [run for run in self._runs if run is self._active]
            removed = len(self._runs) - len(kept)
            self._runs = kept
            self._publish("agents.runs_changed", {})
        self._save()
        return removed

    def shutdown(self) -> None:
        """Fermeture de l'appli : le fil en cours est arrêté et enregistré comme interrompu."""
        with self._lock:
            run = self._active
            if run is not None and run.status == "running":
                run.stop_requested = True
                run.finish("interrupted", _interrupted_text(run))
        if run is not None:
            try:
                self._executor().interrupt(run.id)
            except Exception:  # pylint: disable=broad-except
                pass
        self._save()

    # ── Exécution ───────────────────────────────────────────────────────────

    def _execute(self, run: Run) -> None:
        """Fil de la page : images décrites, puis run_workflow ou run_debate de l'exécuteur."""
        executor = self._executor()
        try:
            if run.kind == "debate":
                debate = run.debate or {}
                executor.run_debate(run.id, debate.get("agent_a"), debate.get("agent_b"),
                                    run.task, debate.get("rounds", 3),
                                    lambda event: self._on_event(run, event))
                return
            task = self._with_images(executor, run)
            if run.stop_requested:
                # Arrêté pendant la lecture des pièces jointes : l'exécuteur n'a rien lancé
                self._on_event(run, {"type": "agent_exec_end", "exec_id": run.id, "success": False,
                                     "interrupted": True, "status_text": tr(INTERRUPTED)})
                return
            documents = [item["path"] for item in run.attachments if item["type"] != "Image"]
            executor.run_workflow(run.id, task, run.nodes, run.connections,
                                  lambda event: self._on_event(run, event),
                                  None, documents or None)
        except Exception as exc:  # pylint: disable=broad-except
            logger.exception("Exécution d'agents en échec (%s)", run.id)
            key = "agents.debateError" if run.kind == "debate" else "agents.workflowError"
            self._on_event(run, {"type": "agent_exec_error", "exec_id": run.id,
                                 "message": tr(key, error=exc)})
        finally:
            self._finish_run(run)

    def _finish_run(self, run: Run) -> None:
        """Fin du fil (fil de l'exécuteur) : statut s'il en manque, enregistrement, notification."""
        with self._lock:
            if run.status == "running":
                if run.stop_requested:
                    run.finish("interrupted", _interrupted_text(run))
                else:
                    run.finish("error", tr("agents.noResult"))
            if self._active is run:
                self._active = None
            self._publish("agents.runs_changed", {})
        self._save()
        self._maybe_notify(run)

    def _maybe_notify(self, run: Run) -> None:
        """Notification du système à la fin d'un fil long de la page, fenêtre sans focus.

        Comme _notify_task_complete de Tk : plus de 8 s, ni interrompu ni en
        échec avant de commencer. Le téléphone et le scheduler (qui notifie
        lui-même) n'en déclenchent pas.
        """
        if self._os_notify is None or run.origin != "desktop":
            return
        if run.status == "interrupted" or run.error:
            return
        if (run.duration_ms or 0) < NOTIFY_MIN_SECONDS * 1000:
            return
        try:
            if self._window_focused():
                return
        except Exception:  # pylint: disable=broad-except
            pass
        title, message = notification_text(run)
        threading.Thread(target=self._os_notify, args=(title, message),
                         name="agents-notify", daemon=True).start()

    def _with_images(self, executor: Any, run: Run) -> str:
        """Tâche complétée par la description de chaque image jointe (modèle de vision).

        run_workflow ne prend qu'une image ; la page Agents de Tk en décrivait
        autant que l'utilisateur en joignait (_analyze_image_for_agent) : chaque
        image passe donc par la description d'AgentRelayService, une à une, avec
        les mêmes sections que lui.
        """
        sections = []
        for item in run.attachments:
            if item["type"] != "Image" or run.stop_requested:
                continue
            name = os.path.basename(item["path"])
            # Même pipeline que le GUI (minicpm-v), partagé avec le mobile
            description = executor._describe_image(item["path"])  # pylint: disable=protected-access
            if description:
                sections.append(f"--- Image jointe : {name} ---\nDescription de l'image :\n"
                                f"{description}")
            else:
                sections.append(f"--- Image jointe : {name} ---\n[Aucun modèle vision disponible. "
                                "Installez-en un : ollama pull minicpm-v]")
        return run.task + "\n\n" + "\n\n".join(sections) if sections else run.task

    def _on_event(self, run: Run, event: Dict[str, Any]) -> None:
        """Événement d'AgentRelayService (fils de l'exécuteur) : fil mis à jour, puis publié."""
        kind = str(event.get("type", ""))
        payload = {key: value for key, value in event.items() if key != "type"}
        interrupt = False
        with self._lock:
            if run.status != "running" and kind not in ("agent_exec_end", "agent_exec_error"):
                return  # fil déjà clos (fermeture de l'appli)
            if not run.forwarded:
                run.forwarded = True
                # Arrêt demandé avant que l'exécuteur ne démarre : il remet son
                # drapeau à zéro en démarrant, il faut le lui redemander
                interrupt = run.stop_requested
            if kind == "agent_section_chunk":
                self._section_text(run, payload)
            else:
                self._apply(run, kind, payload)
                if kind == "agent_exec_end":
                    # Texte final du fil (celui de Tk pour un agent seul)
                    payload["status_text"] = run.status_text
                elif kind == "agent_section_end":
                    section = run.section(payload.get("section_id")) or {}
                    payload["inference_ms"] = section.get("inference_ms")
                    payload["tokens_per_sec"] = section.get("tokens_per_sec")
                self._publish(f"agents.{kind}", payload)
        if interrupt:
            self._executor().interrupt(run.id)
        if kind in ("agent_exec_end", "agent_exec_error"):
            self._save()

    def _section_text(self, run: Run, payload: Dict[str, Any]) -> None:
        """Texte cumulé d'une section : seule la suite part vers la fenêtre."""
        section_id = payload.get("section_id")
        text = str(payload.get("text") or "")
        section = run.section(section_id)
        if section is None:
            section = self._new_section(run, section_id, "", "")
        previous = section.get("text", "")
        if text == previous:
            return
        section["text"] = text
        if text.startswith(previous):
            self._publish("agents.agent_section_delta", {
                "exec_id": run.id, "section_id": section_id,
                "text": text[len(previous):], "offset": len(previous)})
        else:
            self._publish("agents.agent_section_text", {
                "exec_id": run.id, "section_id": section_id, "text": text})

    @staticmethod
    def _new_section(run: Run, section_id: Any, title: str, color: str) -> Dict[str, Any]:
        node = run.node(section_id)
        if not node and run.kind == "debate" and run.nodes:
            # Tours d'un débat (« deb_N ») : le proposant, puis l'opposant, à chaque tour
            node = run.nodes[len(run.sections) % len(run.nodes)]
        section = {
            "id": section_id, "title": title or node.get("name", ""),
            "color": color or node.get("color", ""), "agent_type": node.get("agent_type"),
            "text": "", "status": "running", "started_at": _now(), "finished_at": None,
        }
        run.sections.append(section)
        run.section_clocks[str(section_id)] = time.perf_counter()
        return section

    def _measure(self, run: Run, section: Dict[str, Any]) -> None:
        """Temps d'inférence et tokens/s de l'agent qui vient de finir.

        Tokens/s : eval_count et eval_duration de la fin du flux, gardés par
        le LocalLLM de l'agent (D17), sans requête en plus ; le temps
        d'inférence est celui de l'agent, comme le mesurait Tk.
        """
        started = run.section_clocks.pop(str(section["id"]), None)
        if started is None:
            return
        elapsed_ms = (time.perf_counter() - started) * 1000
        stats = self._last_stream_stats(started) or {}
        count, duration = stats.get("eval_count"), stats.get("eval_duration")
        tps = count / (duration / 1e9) if count and duration else 0.0
        section["inference_ms"] = round(elapsed_ms)
        section["tokens_per_sec"] = round(tps, 1) if tps else None
        if tps and self._on_inference is not None:
            try:
                self._on_inference(elapsed_ms, tps)
            except Exception:  # pylint: disable=broad-except
                logger.debug("Moniteur non mis à jour", exc_info=True)

    def _last_stream_stats(self, since: float) -> Optional[Dict[str, Any]]:
        """Relevé de fin de flux le plus récent des agents de l'exécuteur, pris depuis `since`."""
        try:
            agents = dict(self._executor()._orchestrator.agents)  # pylint: disable=protected-access
        except Exception:  # pylint: disable=broad-except
            return None
        best: Optional[Dict[str, Any]] = None
        best_at = since
        for agent in agents.values():
            stats = getattr(getattr(agent, "llm", None), "last_stream_stats", None)
            at = (stats.get("at") or 0) if isinstance(stats, dict) else 0
            if at >= best_at:
                best, best_at = stats, at
        return best

    def _apply(self, run: Run, kind: str, payload: Dict[str, Any]) -> None:
        """État du fil après un événement de l'exécuteur."""
        if kind == "agent_exec_start":
            run.mode = payload.get("mode")
        elif kind == "agent_section_start":
            section = run.section(payload.get("section_id"))
            if section is None:
                self._new_section(run, payload.get("section_id"), payload.get("title", ""),
                                  payload.get("color", ""))
            else:
                section.update(title=payload.get("title", section["title"]), status="running")
        elif kind == "agent_section_end":
            section = run.section(payload.get("section_id"))
            if section is not None:
                section["status"] = "done" if payload.get("success") else "error"
                section["finished_at"] = _now()
                self._measure(run, section)
        elif kind == "agent_node_status":
            status = payload.get("status")
            if status in NODE_STATUSES:
                run.node_status[str(payload.get("node_id"))] = status
        elif kind == "agent_exec_end":
            if payload.get("interrupted"):
                status = "interrupted"
            else:
                status = "done" if payload.get("success") else "error"
            text = str(payload.get("status_text") or "")
            if run.kind == "agent" and status != "interrupted":
                # Agent seul : messages de Tk (_execute_task_thread), et non
                # « Workflow terminé (0% succès) » d'AgentRelayService
                name = run.nodes[0].get("name", "") if run.nodes else ""
                text = (tr("agents.agentTaskDone", name=name) if status == "done"
                        else tr("agents.agentTaskError"))
            run.finish(status, text)
        elif kind == "agent_exec_error":
            message = str(payload.get("message") or tr("agents.errorDefault"))
            run.finish("error", f"❌ {message}", error=message)

    # ── Exécutions du téléphone et des tâches planifiées (D37) ──────────────

    def executor(self) -> Any:
        """Exécuteur d'agents partagé (AgentRelayService)."""
        return self._executor()

    def executor_tap(self) -> "SharedExecutor":
        """L'exécuteur à donner au Relay et au scheduler : leurs exécutions deviennent des fils."""
        with self._lock:
            if self._tap is None:
                self._tap = SharedExecutor(self)
            return self._tap

    def run_external(self, exec_id: str, emit: Callable[[Dict[str, Any]], None],
                     request: Dict[str, Any]) -> None:
        """
        Exécution demandée par le téléphone ou par le scheduler (bloquant).

        Elle devient un fil, puis passe à l'exécuteur ; chaque événement va
        d'abord à l'appelant, tel quel, puis au fil. Si la page a une
        exécution en cours ou en préparation, l'appelant reçoit le refus de
        l'exécuteur (« Une exécution est déjà en cours. »).

        Args:
            exec_id: identifiant de l'exécution (celui de l'appelant)
            emit: événements de l'exécuteur, pour l'appelant
            request: {task, nodes, connections, image_path, file_paths} pour un
                workflow, {task, debate: {agent_a, agent_b, rounds}} pour un débat
        """
        executor = self._executor()
        run = self._adopt(executor, exec_id, request)
        if run is None:
            emit({"type": "agent_exec_error", "exec_id": exec_id, "message": tr(EXECUTOR_BUSY)})
            return

        def relay(event: Dict[str, Any]) -> None:
            try:
                emit(event)
            except Exception:  # pylint: disable=broad-except
                logger.debug("Événement non relayé (%s)", exec_id, exc_info=True)
            try:
                self._on_event(run, event)
            except Exception:  # pylint: disable=broad-except
                logger.exception("Fil %s non mis à jour", exec_id)

        debate = request.get("debate")
        try:
            if debate is not None:
                executor.run_debate(exec_id, debate.get("agent_a"), debate.get("agent_b"),
                                    request.get("task", ""), debate.get("rounds", 3), relay)
            else:
                executor.run_workflow(exec_id, request.get("task", ""), run.nodes,
                                      list(request.get("connections") or []), relay,
                                      request.get("image_path"), request.get("file_paths"))
        finally:
            self._finish_run(run)

    @staticmethod
    def _external_files(request: Dict[str, Any]) -> List[Dict[str, str]]:
        """Pièces jointes d'une exécution du téléphone (déjà enregistrées par le Relay)."""
        files: List[Dict[str, str]] = []
        image = request.get("image_path")
        if image:
            files.append({"path": image, "name": os.path.basename(image), "type": "Image"})
        for path in request.get("file_paths") or []:
            files.append({"path": path, "name": os.path.basename(path),
                          "type": file_type_for(path) or "Fichier"})
        return files

    def _external_plan(self, executor: Any, request: Dict[str, Any]) -> Dict[str, Any]:
        """Genre, titre, nœuds et plan du fil d'une exécution venue d'ailleurs."""
        debate = request.get("debate")
        if debate is not None:
            known = self._agents_by_key()
            nodes = [_debate_node(node_id, known.get(key) or {"key": key or "?"})
                     for node_id, key in (("a", debate.get("agent_a")),
                                          ("b", debate.get("agent_b")))]
            return {"kind": "debate",
                    "title": tr("agents.title.debate", a=nodes[0]["name"], b=nodes[1]["name"]),
                    "nodes": nodes, "plan": {"mode": "debate", "steps": [], "isolated": []},
                    "debate": {"agent_a": debate.get("agent_a"), "agent_b": debate.get("agent_b"),
                               "rounds": _clamp_rounds(debate.get("rounds"))}}
        nodes = list(request.get("nodes") or [])
        plan = executor.compute_execution_plan(nodes, list(request.get("connections") or []))
        single = len(nodes) == 1
        title = (nodes[0].get("name", "Agent") if single
                 else tr("agents.title.workflow", count=len(nodes)))
        return {"kind": "agent" if single else "workflow", "title": title,
                "nodes": nodes, "connections": plan.get("connections", []),
                "plan": _plan_view(plan),
                "node_status": {str(node.get("id")): "idle" for node in nodes}}

    def _scheduled_task(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Tâche planifiée qu'exécute le scheduler : son nom titre le fil, son rapport suivra."""
        scheduled = None
        try:
            scheduled = self._find_scheduled(request.get("task", ""),
                                             list(request.get("nodes") or []),
                                             request.get("debate"))
        except Exception:  # pylint: disable=broad-except
            logger.debug("Tâche planifiée introuvable", exc_info=True)
        scheduled = scheduled or {}
        return {"task_id": scheduled.get("id"), "name": scheduled.get("name"),
                "output_file": None}

    def _adopt(self, executor: Any, exec_id: str, request: Dict[str, Any]) -> Optional[Run]:
        """Fil d'une exécution venue d'ailleurs ; None si une exécution est déjà en cours."""
        origin = "scheduled" if str(exec_id).startswith(SCHEDULED_PREFIX) else "mobile"
        files = self._external_files(request)
        data: Dict[str, Any] = {
            "id": str(exec_id), "origin": origin, "task": request.get("task") or "",
            "attachments": files, "sources": self._code_sources(files),
            **self._external_plan(executor, request),
        }
        if origin == "scheduled":
            data["schedule"] = self._scheduled_task(request)
            data["title"] = data["schedule"]["name"] or data["title"]
        run = Run(data)
        with self._lock:
            if self._active is not None or self._busy():
                return None
            self._active = run
            self._runs.insert(0, run)
            self._trim()
            self._publish("agents.run_created", {"run": run.view()})
        self._save()
        return run

    def scheduled_result(self, result: Dict[str, Any]) -> None:
        """Fin d'une tâche planifiée (listener du scheduler) : son rapport rattaché à son fil."""
        task_id = result.get("task_id")
        with self._lock:
            run = next((r for r in self._runs
                        if r.origin == "scheduled" and r.status != "running"
                        and not (r.schedule or {}).get("output_file")
                        and (r.schedule or {}).get("task_id") in (task_id, None)), None)
            if run is None:
                return
            run.schedule = {"task_id": task_id,
                            "name": result.get("name") or (run.schedule or {}).get("name"),
                            "output_file": result.get("output_file")}
            self._publish("agents.runs_changed", {})
        self._save()

    # ── Pièces jointes de la zone de tâche ──────────────────────────────────

    def _attachment(self, path: str, file_type: Optional[str] = None) -> Dict[str, str]:
        """Pièce jointe vérifiée : fichier existant, d'un type que les agents savent lire."""
        path = os.path.abspath(path or "")
        if not os.path.isfile(path):
            raise AgentsError(tr("agents.fileNotFound", name=os.path.basename(path) or path))
        if file_type not in ATTACH_TYPES:
            file_type = file_type_for(path)
        if file_type is None:
            ext = os.path.splitext(path)[1].lower() or "?"
            raise AgentsError(tr("agents.unsupportedFormat", ext=ext))
        with self._lock:
            self._known.add(local_files.normalize(path))
        return {"path": path, "name": os.path.basename(path), "type": file_type}

    def inspect(self, paths: List[str]) -> Dict[str, Any]:
        """Fichiers choisis ou déposés pour la zone de tâche.

        Un dossier joint ses fichiers lisibles, avec la règle du chat (D24) ;
        ses images restent de côté. Chaque refus a son message.
        """
        attachments: List[Dict[str, str]] = []
        refused: List[str] = []
        for raw in paths:
            path = os.path.abspath(raw or "")
            if os.path.isdir(path):
                try:
                    files, _images = folder_attachment_files(path)
                except ChatError as exc:
                    refused.append(str(exc))
                    continue
                attachments.extend(self._attachment(item) for item in files)
                continue
            try:
                attachments.append(self._attachment(path))
            except AgentsError as exc:
                refused.append(str(exc))
        return {"attachments": attachments, "refused": refused}

    @staticmethod
    def _code_sources(files: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """Code joint à la tâche, gardé pour le diff des sorties qui le modifient."""
        sources = []
        for item in files:
            if item["type"] != "Code":
                continue
            try:
                with open(item["path"], "r", encoding="utf-8", errors="replace") as fh:
                    text = fh.read(MAX_CODE_SOURCE + 1)
            except OSError:
                continue
            if len(text) <= MAX_CODE_SOURCE:
                sources.append({"name": item["name"], "text": text})
        return sources

    # ── Fichier des fils (D33) ──────────────────────────────────────────────

    def _trim(self) -> None:
        """Garde les MAX_RUNS fils les plus récents (jamais celui en cours)."""
        while len(self._runs) > MAX_RUNS:
            oldest = next((r for r in reversed(self._runs) if r is not self._active), None)
            if oldest is None:
                return
            self._runs.remove(oldest)

    def _load(self) -> List[Run]:
        """Fils enregistrés ; un fil resté « en cours » (appli tuée) est interrompu."""
        try:
            with open(self._runs_file, "r", encoding="utf-8") as fh:
                data = json.load(fh)
        except FileNotFoundError:
            return []
        except (OSError, ValueError) as exc:
            logger.warning("Fils d'exécution illisibles (%s) : %s", self._runs_file, exc)
            return []
        runs = []
        for item in data.get("runs", []) if isinstance(data, dict) else []:
            if not isinstance(item, dict) or not _ID_RE.match(str(item.get("id", ""))):
                continue
            run = Run(item)
            if run.status == "running":
                run.status = "interrupted"
                run.status_text = _interrupted_text(run)
                for section in run.sections:
                    if section.get("status") == "running":
                        section["status"] = "error"
            runs.append(run)
        return runs[:MAX_RUNS]

    def _save(self) -> None:
        """Écrit les fils (écriture atomique) ; un échec est journalisé, jamais levé."""
        with self._lock:
            data = {"version": 1, "runs": [run.view() for run in self._runs]}
        with self._save_lock:
            try:
                self._runs_file.parent.mkdir(parents=True, exist_ok=True)
                tmp = self._runs_file.with_suffix(".json.tmp")
                with open(tmp, "w", encoding="utf-8") as fh:
                    json.dump(data, fh, ensure_ascii=False, indent=1)
                os.replace(tmp, self._runs_file)
            except OSError as exc:
                logger.warning("Fils d'exécution non enregistrés : %s", exc)

    # ── Fichiers de workflow (Enregistrer, Charger, Exporter) ───────────────

    @staticmethod
    def default_path(folder: str, stem: str, suffix: str) -> Path:
        """Fichier daté sous outputs/ (pas de dialogue : navigateur, --dev)."""
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return Path("outputs") / folder / f"{stem}_{stamp}{suffix}"

    def save_workflow(self, path: Optional[str], workflow: Dict[str, Any]) -> str:
        """Enregistre le workflow au format JSON de WorkflowCanvas.to_dict (Tk)."""
        target = Path(path) if path else self.default_path("workflows", "workflow", ".json")
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            with open(target, "w", encoding="utf-8") as fh:
                json.dump(workflow, fh, ensure_ascii=False, indent=2)
        except OSError as exc:
            raise AgentsError(tr("agents.workflowNotSaved", error=exc)) from exc
        return str(target.resolve())

    @staticmethod
    def read_workflow(path: str) -> Dict[str, Any]:
        """Workflow enregistré (Tk ou fenêtre) : la fenêtre en vérifie le contenu."""
        try:
            if os.path.getsize(path) > 5_000_000:
                raise AgentsError(tr("agents.workflowTooBig"))
            with open(path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
        except (OSError, ValueError) as exc:
            raise AgentsError(tr("agents.workflowReadError", error=exc)) from exc
        if not isinstance(data, dict):
            raise AgentsError(tr("agents.workflowUnknownFormat"))
        return data

    def export_workflow(self, path: Optional[str], workflow: Dict[str, Any],
                        run_id: Optional[str] = None) -> str:
        """Exporte le workflow en Markdown (D11) : la tâche, les agents, puis la
        réponse de chacun à la dernière exécution."""
        with self._lock:
            run = next((r for r in self._runs if r.id == run_id), None) if run_id else None
            run_view = run.view() if run is not None else None
        text = workflow_markdown(workflow, run_view)
        target = Path(path) if path else self.default_path("exports", "workflow_export", ".md")
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(text, encoding="utf-8")
        except OSError as exc:
            raise AgentsError(f"❌ Erreur export : {exc}") from exc
        return str(target.resolve())


class SharedExecutor:
    """L'exécuteur partagé, vu du Relay et du scheduler (D37).

    Même interface qu'AgentRelayService, à qui tout le reste est délégué :
    run_workflow et run_debate passent par la page Agents, qui en fait des
    fils marqués de leur origine, puis rendent chaque événement tel quel à
    l'appelant (téléphone, collecteur du scheduler). busy compte aussi une
    exécution de la page qui se prépare (lecture des pièces jointes) : le
    scheduler la diffère, comme quand l'exécuteur est occupé.
    """

    def __init__(self, service: AgentsService):
        self._service = service

    def __getattr__(self, name: str) -> Any:
        if name.startswith("__"):
            raise AttributeError(name)
        return getattr(self._service.executor(), name)

    @property
    def busy(self) -> bool:
        """Une exécution est en cours ou se prépare, d'où qu'elle vienne."""
        return self._service.busy()

    # pylint: disable-next=too-many-arguments,too-many-positional-arguments
    def run_workflow(self, exec_id: str, task: str, nodes: List[Dict[str, Any]],
                     connections: List[Dict[str, Any]], emit: Callable[[Dict[str, Any]], None],
                     image_path: Optional[str] = None,
                     file_paths: Optional[List[str]] = None) -> None:
        """AgentRelayService.run_workflow, avec son fil."""
        self._service.run_external(exec_id, emit, {
            "task": task, "nodes": nodes, "connections": connections,
            "image_path": image_path, "file_paths": file_paths})

    # pylint: disable-next=too-many-arguments,too-many-positional-arguments
    def run_debate(self, exec_id: str, agent_a: str, agent_b: str, topic: str, rounds: int,
                   emit: Callable[[Dict[str, Any]], None]) -> None:
        """AgentRelayService.run_debate, avec son fil."""
        self._service.run_external(exec_id, emit, {
            "task": topic, "debate": {"agent_a": agent_a, "agent_b": agent_b, "rounds": rounds}})


def _node_key(node_id: Any) -> str:
    return str(node_id)


def workflow_markdown(workflow: Dict[str, Any], run: Optional[Dict[str, Any]] = None) -> str:
    """Markdown de l'export d'un workflow (D11).

    Les en-têtes de Tk (_export_workflow) sont gardés ; s'y ajoutent la tâche
    et la réponse de chaque agent à la dernière exécution. Un nœud n'a de
    réponse que s'il figurait, avec le même agent, dans cette exécution.
    """
    nodes = workflow.get("nodes") or {}
    connections = workflow.get("connections") or []
    lines = ["# Workflow Export", "",
             f"**Version**: {workflow.get('version', '9.0.0')}",
             f"**Nodes**: {len(nodes)}",
             f"**Connections**: {len(connections)}", ""]
    lines += [f"## {tr('export.workflow.task')}", "",
              (run or {}).get("task") or tr("export.workflow.noRun"), ""]
    lines += [f"## {tr('export.workflow.agents')}", ""]
    for node in nodes.values():
        raw = node.get("status", "idle")
        status = tr(_STATUS_LABELS[raw]) if raw in _STATUS_LABELS else raw
        line = tr("export.workflow.agentLine", type=node.get("agent_type", ""), status=status)
        lines.append(f"- {node.get('icon', '🤖')} **{node.get('name', '')}** — {line}")
    lines.append("")
    if run is None:
        return "\n".join(lines)
    started = (run.get("started_at") or "").replace("T", " ")[:16]
    lines += [f"## {tr('export.workflow.answers', started=started)}", ""]
    sections = {_node_key(s.get("id")): s for s in run.get("sections") or []}
    run_nodes = {_node_key(n.get("id")): n for n in run.get("nodes") or []}
    for key, node in nodes.items():
        lines += [f"### {node.get('icon', '🤖')} {node.get('name', '')}", ""]
        section = sections.get(_node_key(key))
        same_agent = run_nodes.get(_node_key(key), {}).get("agent_type") == node.get("agent_type")
        if section is None or not same_agent:
            lines += [tr("export.workflow.noAnswer"), ""]
            continue
        lines += [section.get("text") or tr("export.workflow.emptyAnswer"), ""]
    if run.get("status_text"):
        lines += ["---", "", run["status_text"], ""]
    return "\n".join(lines)
