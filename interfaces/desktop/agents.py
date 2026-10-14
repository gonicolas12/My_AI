"""
Page Agents de la fenêtre (interfaces/agents/ de Tk)

Expose l'exécuteur d'agents partagé, AgentRelayService (relay/agent_relay.py),
sans le réécrire : liste des agents, agents personnalisés, exécution d'un
agent seul ou d'un workflow (séquentiel, parallèle, DAG) et arrêt. Une seule
exécution à la fois, partout : la page Agents, le mobile et le scheduler
partagent le même exécuteur (cf. lifecycle.py, agent_service).

Chaque exécution devient un fil (D32) : sa tâche, son workflow, la sortie de
chaque agent et son statut, gardés pour être rouverts, y compris après un
redémarrage (D33 : les 50 derniers, dans data/agent_runs.json).

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
from typing import Any, Callable, Dict, List, Optional, Set

from core.chat_service import ChatError, file_type_for, folder_attachment_files
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

# Messages de Tk (execution.py), repris par la fenêtre
NO_AGENT = "Glissez-déposez un ou plusieurs agents pour commencer."
EMPTY_TASK = "Veuillez décrire la tâche à effectuer."
BUSY = "Un agent est déjà en train de traiter une tâche."
INTERRUPTED = "⛔ Génération interrompue"

# Statuts d'un nœud du canvas (WorkflowCanvas.STATUS_META de Tk)
NODE_STATUSES = ("idle", "running", "done", "error")

# Libellés des statuts de nœud, pour l'export Markdown
_STATUS_LABELS = {"idle": "En attente", "running": "En cours", "done": "Terminé", "error": "Erreur"}

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
        # État du fil vivant, jamais enregistré
        self.stop_requested = False
        self.forwarded = False  # au moins un événement reçu de l'exécuteur
        self.started_clock = time.perf_counter()

    def view(self) -> Dict[str, Any]:
        """Fil complet, pour la fenêtre et le fichier des fils."""
        return {
            "id": self.id, "kind": self.kind, "title": self.title, "task": self.task,
            "attachments": self.attachments, "sources": self.sources,
            "nodes": self.nodes, "connections": self.connections, "plan": self.plan,
            "mode": self.mode, "status": self.status, "status_text": self.status_text,
            "error": self.error, "started_at": self.started_at,
            "finished_at": self.finished_at, "duration_ms": self.duration_ms,
            "sections": self.sections, "node_status": self.node_status,
        }

    def summary(self) -> Dict[str, Any]:
        """Ligne de la liste des fils."""
        first = self.nodes[0] if self.nodes else {}
        return {
            "id": self.id, "kind": self.kind, "title": self.title,
            "task": _excerpt(self.task), "status": self.status,
            "status_text": self.status_text, "started_at": self.started_at,
            "finished_at": self.finished_at, "duration_ms": self.duration_ms,
            "agent_type": first.get("agent_type"), "color": first.get("color"),
            "agents": len(self.nodes),
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


class AgentsService:
    """Agents de la fenêtre : liste, agents personnalisés, fils d'exécution, workflows."""

    # pylint: disable=too-many-instance-attributes,too-many-public-methods

    def __init__(self, executor: Callable[[], Any], publish: Callable[..., Any], *,
                 runs_file: Path = RUNS_FILE,
                 notify: Optional[Callable[[str, str], None]] = None,
                 last_seq: Optional[Callable[[], int]] = None):
        """
        Args:
            executor: exécuteur d'agents partagé (AgentRelayService), créé au premier usage
            publish: publication d'un événement sur le bus de la fenêtre
            runs_file: fichier des fils (data/agent_runs.json)
            notify: notification brève de la fenêtre (niveau, message)
            last_seq: numéro du dernier événement publié (lectures de l'état)
        """
        self._executor = executor
        self._publish = publish
        self._notify = notify or (lambda _level, _message: None)
        self._last_seq = last_seq or (lambda: 0)
        self._runs_file = Path(runs_file)
        # Verrou réentrant : un événement de l'exécuteur peut suivre un arrêt
        # demandé dans le même fil
        self._lock = threading.RLock()
        self._save_lock = threading.Lock()
        self._runs: List[Run] = self._load()
        self._active: Optional[Run] = None
        # Pièces jointes de la zone de tâche : la fenêtre peut en montrer la vignette
        self._known: Set[str] = set()

    # ── Agents ──────────────────────────────────────────────────────────────

    def list(self) -> Dict[str, Any]:
        """Agents intégrés et personnalisés (relit data/custom_agents.json)."""
        return self._executor().list_agents()

    def create(self, name: str, role: str) -> Dict[str, Any]:
        """Crée un agent personnalisé : son prompt système est rédigé par le modèle."""
        result = self._executor().create_agent(name, role)
        return self._agent_changed(result, "✅ Agent créé !")

    def edit(self, key: str, name: str, role: str) -> Dict[str, Any]:
        """Modifie un agent personnalisé ; un nouveau rôle fait réécrire son prompt."""
        result = self._executor().edit_agent(key, name, role)
        return self._agent_changed(result, "✅ Agent modifié !")

    def delete(self, key: str) -> None:
        """Supprime un agent personnalisé."""
        result = self._executor().delete_agent(key)
        if not result.get("success"):
            raise AgentsError(f"❌ {result.get('error') or 'Suppression impossible'}")
        self._publish("agents.list_changed", {})
        # Message et couleur de Tk (_delete_custom_agent)
        self._notify("error", "❌ Agent supprimé")

    def _agent_changed(self, result: Dict[str, Any], message: str) -> Dict[str, Any]:
        if not result.get("success"):
            raise AgentsError(f"❌ Erreur : {result.get('error') or 'opération impossible'}")
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
                "seq": seq,
            }

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

    def _find(self, run_id: str) -> Run:
        run = next((r for r in self._runs if r.id == run_id), None)
        if run is None:
            raise RunNotFound("Exécution introuvable.")
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
            raise AgentsError(NO_AGENT)
        if not task:
            raise AgentsError(EMPTY_TASK)
        files = [self._attachment(item.get("path", ""), item.get("type")) for item in attachments or []]
        executor = self._executor()
        plan = executor.compute_execution_plan(nodes, connections)
        single = len(nodes) == 1
        run = Run({
            "id": f"exec_{uuid.uuid4().hex}",
            "kind": "agent" if single else "workflow",
            "title": nodes[0].get("name", "Agent") if single else f"Workflow · {len(nodes)} agents",
            "task": task,
            "attachments": files,
            "sources": self._code_sources(files),
            "nodes": nodes,
            # Liens valides seulement (deux extrémités connues), comme le plan
            "connections": plan.get("connections", []),
            "plan": _plan_view(plan),
            "node_status": {str(node["id"]): "idle" for node in nodes},
        })
        with self._lock:
            if self._active is not None or self._busy():
                raise AgentsError(BUSY)
            self._active = run
            self._runs.insert(0, run)
            self._trim()
            self._publish("agents.run_created", {"run": run.view()})
        self._save()
        threading.Thread(target=self._execute, args=(run,), name="agents-run", daemon=True).start()
        return run.id

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
                raise AgentsError("Exécution en cours : arrêtez-la d'abord.")
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
                run.finish("interrupted", INTERRUPTED)
        if run is not None:
            try:
                self._executor().interrupt(run.id)
            except Exception:  # pylint: disable=broad-except
                pass
        self._save()

    # ── Exécution ───────────────────────────────────────────────────────────

    def _execute(self, run: Run) -> None:
        """Fil d'exécution : images décrites, puis run_workflow d'AgentRelayService."""
        executor = self._executor()
        try:
            task = self._with_images(executor, run)
            if run.stop_requested:
                # Arrêté pendant la lecture des pièces jointes : l'exécuteur n'a rien lancé
                self._on_event(run, {"type": "agent_exec_end", "exec_id": run.id, "success": False,
                                     "interrupted": True, "status_text": INTERRUPTED})
                return
            documents = [item["path"] for item in run.attachments if item["type"] != "Image"]
            executor.run_workflow(run.id, task, run.nodes, run.connections,
                                  lambda event: self._on_event(run, event),
                                  None, documents or None)
        except Exception as exc:  # pylint: disable=broad-except
            logger.exception("Exécution d'agents en échec (%s)", run.id)
            self._on_event(run, {"type": "agent_exec_error", "exec_id": run.id,
                                 "message": f"Erreur workflow : {exc}"})
        finally:
            with self._lock:
                if run.status == "running":
                    if run.stop_requested:
                        run.finish("interrupted", INTERRUPTED)
                    else:
                        run.finish("error", "❌ Exécution terminée sans résultat")
                if self._active is run:
                    self._active = None
                self._publish("agents.runs_changed", {})
            self._save()

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
        section = {
            "id": section_id, "title": title or node.get("name", ""),
            "color": color or node.get("color", ""), "agent_type": node.get("agent_type"),
            "text": "", "status": "running", "started_at": _now(), "finished_at": None,
        }
        run.sections.append(section)
        return section

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
                text = (f"✅ Tâche terminée avec {name}" if status == "done"
                        else "❌ Erreur lors de l'exécution")
            run.finish(status, text)
        elif kind == "agent_exec_error":
            message = str(payload.get("message") or "Erreur")
            run.finish("error", f"❌ {message}", error=message)

    # ── Pièces jointes de la zone de tâche ──────────────────────────────────

    def _attachment(self, path: str, file_type: Optional[str] = None) -> Dict[str, str]:
        """Pièce jointe vérifiée : fichier existant, d'un type que les agents savent lire."""
        path = os.path.abspath(path or "")
        if not os.path.isfile(path):
            raise AgentsError(f"❌ Fichier introuvable : {os.path.basename(path) or path}")
        if file_type not in ATTACH_TYPES:
            file_type = file_type_for(path)
        if file_type is None:
            ext = os.path.splitext(path)[1].lower() or "?"
            raise AgentsError(f"❌ Format non supporté : {ext}")
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
                run.status_text = INTERRUPTED
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
            raise AgentsError(f"❌ Workflow non enregistré : {exc}") from exc
        return str(target.resolve())

    @staticmethod
    def read_workflow(path: str) -> Dict[str, Any]:
        """Workflow enregistré (Tk ou fenêtre) : la fenêtre en vérifie le contenu."""
        try:
            if os.path.getsize(path) > 5_000_000:
                raise AgentsError("❌ Erreur chargement workflow : fichier trop gros")
            with open(path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
        except (OSError, ValueError) as exc:
            raise AgentsError(f"❌ Erreur chargement workflow : {exc}") from exc
        if not isinstance(data, dict):
            raise AgentsError("❌ Erreur chargement workflow : format inconnu")
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
             f"**Version**: {workflow.get('version', '8.1.0')}",
             f"**Nodes**: {len(nodes)}",
             f"**Connections**: {len(connections)}", ""]
    lines += ["## Tâche", "", (run or {}).get("task") or "_Aucune exécution._", ""]
    lines += ["## Agents", ""]
    for node in nodes.values():
        status = _STATUS_LABELS.get(node.get("status", "idle"), node.get("status", ""))
        lines.append(f"- {node.get('icon', '🤖')} **{node.get('name', '')}** — "
                     f"type : `{node.get('agent_type', '')}` — statut : {status}")
    lines.append("")
    if run is None:
        return "\n".join(lines)
    started = (run.get("started_at") or "").replace("T", " ")[:16]
    lines += [f"## Réponses de la dernière exécution ({started})", ""]
    sections = {_node_key(s.get("id")): s for s in run.get("sections") or []}
    run_nodes = {_node_key(n.get("id")): n for n in run.get("nodes") or []}
    for key, node in nodes.items():
        lines += [f"### {node.get('icon', '🤖')} {node.get('name', '')}", ""]
        section = sections.get(_node_key(key))
        same_agent = run_nodes.get(_node_key(key), {}).get("agent_type") == node.get("agent_type")
        if section is None or not same_agent:
            lines += ["_Pas de réponse à la dernière exécution._", ""]
            continue
        lines += [section.get("text") or "_Réponse vide._", ""]
    if run.get("status_text"):
        lines += ["---", "", run["status_text"], ""]
    return "\n".join(lines)
