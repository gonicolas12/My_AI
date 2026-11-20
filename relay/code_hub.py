"""
Conversation « Code » : le chat de l'extension VS Code, partagé par trois surfaces

L'extension VS Code, la page Code de la fenêtre desktop et la vue Code du
téléphone (Relay) montrent la même conversation : un message envoyé de l'une,
la réponse en streaming, les appels d'outils et leurs approbations, l'arrêt et
l'effacement paraissent sur les trois. Chaque message lance la boucle
agentique (core/agentic_executor.py) sur la boucle asyncio du Relay ; ses
outils s'exécutent dans l'extension VS Code connectée, qui demande l'accord
de l'utilisateur avant d'écrire un fichier ou de lancer une commande. Seuls
ceux de la mémoire de My_AI (MEMORY_TOOLS) s'exécutent sur le PC.

Le chat « classique » (téléphone et fenêtre desktop, RelayBridge) ne voit rien
de cette conversation, et elle ne voit rien de lui. Elle partage avec lui la
mémoire de My_AI, cloisonnée (core/code_memory.py) : les faits retenus pour le
code dans son prompt système, « retiens que… » enregistré pour le dossier
ouvert, le reste de la mémoire à la demande (search_memory).

Un seul hub par processus (get_code_hub) : il survit aux redémarrages du
Relay, et la conversation (affichage et historique du modèle) est gardée dans
data/code_conversation.json d'un lancement à l'autre.

Événements diffusés aux abonnés (une fonction appelée sous le verrou du hub,
qui ne doit jamais bloquer), dans l'ordre :
  - snapshot : état et transcription complète (à l'abonnement, si demandé)
  - state    : VS Code connecté (et son dossier), réponse en cours
  - user     : message de l'utilisateur ; client : lien VS Code d'où il part
  - chunk    : texte d'une passe du modèle (segment), en entier à chaque fois
  - tool     : appel d'outil et son état (requested, awaiting-approval avec ses
               options, running, completed, failed, denied, stopped)
  - done     : fin de la réponse (status done, stopped ou error)
  - cleared  : conversation effacée
vscode_view et mobile_view les traduisent dans le protocole du Relay.
"""

import asyncio
import copy
import json
import os
import re
import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

from core import i18n
from core.agentic_executor import (
    AGENT_TOOLS,
    MEMORY_TOOLS,
    AgenticExecutor,
    RemoteToolExecutor,
    build_system_prompt,
)
from core.i18n import tr
from core.knowledge_base_manager import SCOPE_PROJECT, fact_scope, project_name
from relay.code_links import conversation_files, reply_links, workspace_roots
from utils.logger import setup_logger

logger = setup_logger("CodeHub")

PROJECT_ROOT = Path(__file__).resolve().parents[1]
# Conversation gardée d'un lancement à l'autre, ignorée par git
STORE_FILE = PROJECT_ROOT / "data" / "code_conversation.json"

ORIGINS = ("vscode", "desktop", "mobile")
# Réponses possibles à une demande d'approbation (toolDispatcher.ts de l'extension)
APPROVAL_DECISIONS = ("allow-once", "allow-target", "allow-tool", "deny")
# États d'un appel d'outil rapportés par l'extension pendant son exécution
_EXTENSION_STATUSES = ("awaiting-approval", "running", "denied")
# Un appel encore dans l'un de ces états quand la réponse s'arrête est « stopped »
_OPEN_STATUSES = ("requested", "awaiting-approval", "running")

# Messages gardés à l'affichage (question et réponse comptent pour deux)
MAX_MESSAGES = 400
# Sortie d'un outil gardée à l'affichage ; le modèle, lui, l'a reçue en entier
MAX_TOOL_OUTPUT = 4000
# Valeur d'un argument d'outil gardée à l'affichage (contenu d'un write_file…)
MAX_TOOL_INPUT = 2000
# Texte d'une pièce jointe donné au modèle
MAX_ATTACHMENT_CHARS = 60_000
# Part de la fenêtre de contexte (hors réponse) que les pièces jointes d'un message peuvent prendre
_ATTACHMENT_SHARE = 0.5
# Part de la fenêtre de contexte laissée à la réponse (num_predict de l'exécuteur)
_REPLY_TOKENS = 8192
# Caractères par token, pour borner l'historique du modèle sans le tokeniser
_CHARS_PER_TOKEN = 3

_IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp", ".tiff", ".tif"}
_WORKSPACE_LINE = re.compile(r"^- (.+?) \(.*\)$", re.MULTILINE)

# Outils exécutés sur le PC (mémoire de My_AI), quand la mémoire est disponible
HOST_TOOLS = tuple(tool["name"] for tool in MEMORY_TOOLS)
# Passages d'un appel de search_memory
_MAX_MEMORY_RESULTS = 10
# Échanges précédents lus pour comprendre une demande de mémorisation
# (« retiens-le »), et longueur gardée de chacun
_REMEMBER_CONTEXT_MESSAGES = 4
_REMEMBER_CONTEXT_CHARS = 800
# Attente, la réponse finie, de ce que le modèle retient d'un message sans demande
# (au-delà du délai de MemoryReader)
_READ_LATER_SECONDS = 70
# Note [Mémoire] (core/code_memory.py) que le modèle recopiait parfois à la fin de
# sa réponse : elle est pour lui, pas pour l'utilisateur. Il imite aussi le repère
# devant une phrase à lui (« [Mémoire] J'ai retenu… ») : seul le repère part.
_NOTE_TAG = "[Mémoire]"
_NOTE_TAG_RE = re.compile(r"[ \t]*\[Mémoire\][ \t]*")
# Début de la note qui, recopié après le repère, en fait une copie
_NOTE_ECHO_CHARS = 60


class CodeError(Exception):
    """Message refusé (VS Code absent, réponse en cours, message vide) ; texte traduit."""


@dataclass
class VSCodeLink:
    """Extension VS Code connectée au Relay (un WebSocket).

    send : dépose un message du protocole du Relay dans la file ordonnée du
    WebSocket ; appelable depuis n'importe quel fil. pending : appels d'outils
    en attente de leur tool_result, sur la boucle du Relay.
    """

    loop: asyncio.AbstractEventLoop
    send: Callable[[Dict[str, Any]], None]
    workspace_info: str = ""
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    pending: Dict[str, "asyncio.Future[Dict[str, Any]]"] = field(default_factory=dict)
    alive: bool = True


class _Run:
    """Réponse en cours : une seule à la fois, d'où que vienne le message."""

    def __init__(self, message_id: str, origin: str, link: VSCodeLink, client: Optional[str]):
        self.message_id = message_id
        self.origin = origin
        self.link = link
        self.client = client
        self.started = time.time()
        self.future = None  # concurrent.futures.Future de la tâche sur la boucle du Relay
        self.finished = False
        # Conversation effacée pendant la réponse : sa fin n'affiche plus rien
        self.discarded = False
        # Raison d'un arrêt qui n'est pas celui de l'utilisateur (VS Code déconnecté)
        self.stop_reason: Optional[str] = None
        # Appels d'outils dont l'approbation est demandée à l'utilisateur
        self.approvals: Dict[str, List[str]] = {}
        # Outils de cette réponse exécutés sur le PC (mémoire disponible)
        self.host_tools: set = set()
        # Note [Mémoire] ajoutée au message pour le modèle : sa copie est retirée de
        # la réponse (_without_note)
        self.note = ""


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _clip(text: Any, limit: int) -> str:
    text = text if isinstance(text, str) else json.dumps(text, ensure_ascii=False, default=str)
    return text if len(text) <= limit else text[:limit] + "…"


def _without_note(text: str, note: str = "") -> str:
    """
    La réponse sans la note [Mémoire] (note : celle donnée au modèle) qu'il y
    recopie parfois, même en cours d'écriture : ce qui suit la copie part. Un
    repère qu'il met devant une phrase à lui part seul, la phrase reste (sans
    note, il l'imitait, et toute sa réponse disparaissait). Le début d'un repère
    en cours d'écriture (« [Mé ») attend la suite.
    """
    text = text or ""
    body = note[len(_NOTE_TAG):].strip() if note.startswith(_NOTE_TAG) else ""
    position = 0
    while True:
        match = _NOTE_TAG_RE.search(text, position)
        if match is None:
            break
        rest = text[match.end():]
        if body and (body.startswith(rest.rstrip()) or rest.startswith(body[:_NOTE_ECHO_CHARS])):
            return text[:match.start()].rstrip()
        before = text[:match.start()]
        text = before + (" " if before and rest and not before[-1].isspace() else "") + rest
        position = len(before)
    start = text.rfind("\n") + 1
    tail = text[start:].lstrip()
    if tail and _NOTE_TAG.startswith(tail):
        return text[:start].rstrip()
    return text


def _display_input(data: Any) -> Dict[str, Any]:
    """Arguments d'un outil à l'affichage : les longs textes coupés."""
    if not isinstance(data, dict):
        return {}
    shown: Dict[str, Any] = {}
    for key, value in data.items():
        shown[str(key)] = _clip(value, MAX_TOOL_INPUT) if isinstance(value, str) else value
    return shown


def workspace_name(workspace_info: str) -> Optional[str]:
    """Dossiers ouverts dans VS Code (« My_AI », « api, web »), d'après client_hello."""
    names = _WORKSPACE_LINE.findall(workspace_info or "")
    return ", ".join(names) if names else None


class CodeHub:
    """Conversation Code : transcription, historique du modèle, réponse en cours."""

    def __init__(self, store: Optional[Path] = STORE_FILE,
                 executor_factory: Optional[Callable[..., Any]] = None):
        """
        Args:
            store: fichier de la conversation (None : rien n'est gardé)
            executor_factory: boucle agentique (AgenticExecutor par défaut ;
                une boucle scénarisée pour la démonstration de l'interface)
        """
        self._lock = threading.RLock()
        self._save_lock = threading.Lock()
        self._store = store
        self._executor_factory = executor_factory
        self._subscribers: List[Callable[[Dict[str, Any]], None]] = []
        # Extensions connectées, la plus récemment active en dernier : c'est elle
        # qui exécute les outils d'un message du PC ou du téléphone
        self._links: List[VSCodeLink] = []
        self._active: Optional[_Run] = None
        self._llm_resolver: Optional[Callable[[], Optional[Dict[str, Any]]]] = None
        # Section « Mémoire » du prompt système en place (_memory_system) : le
        # prompt sans elle, les faits qu'elle montre, ceux que la conversation a
        # retenus depuis
        self._memory_view: Optional[Dict[str, Any]] = None
        self._messages, self._llm_history, self._memory_view = self._load()

    # ── Abonnés ─────────────────────────────────────────────────────────────

    def subscribe(
        self, deliver: Callable[[Dict[str, Any]], None], snapshot: bool = False
    ) -> Callable[[], None]:
        """Abonne une surface ; `snapshot` lui envoie d'abord l'état complet.

        L'état et l'abonnement se font sous le même verrou : aucun événement
        ne tombe entre les deux, ni n'y est compté deux fois.
        """
        with self._lock:
            if snapshot:
                self._deliver(deliver, {"type": "snapshot", **self._snapshot_locked()})
            self._subscribers.append(deliver)

        def unsubscribe() -> None:
            with self._lock:
                if deliver in self._subscribers:
                    self._subscribers.remove(deliver)

        return unsubscribe

    def push_snapshot(self, deliver: Callable[[Dict[str, Any]], None]) -> None:
        """État complet pour un abonné déjà inscrit (vue rechargée)."""
        with self._lock:
            self._deliver(deliver, {"type": "snapshot", **self._snapshot_locked()})

    def snapshot(self, seq: Optional[Callable[[], int]] = None) -> Dict[str, Any]:
        """État et transcription ; `seq` lu sous le même verrou (fenêtre desktop)."""
        with self._lock:
            data = self._snapshot_locked()
            if seq is not None:
                data["seq"] = seq()
            return data

    def state(self) -> Dict[str, Any]:
        """VS Code connecté, réponse en cours."""
        with self._lock:
            return self._state_locked()

    @staticmethod
    def _deliver(deliver: Callable[[Dict[str, Any]], None], event: Dict[str, Any]) -> None:
        try:
            deliver(event)
        except Exception as exc:  # pylint: disable=broad-except
            logger.debug("Événement Code non remis : %s", exc)

    def _emit(self, event_type: str, payload: Optional[Dict[str, Any]] = None) -> None:
        """Diffuse un événement (appelé sous le verrou)."""
        event = {"type": event_type, **(payload or {})}
        for deliver in list(self._subscribers):
            self._deliver(deliver, event)

    def _snapshot_locked(self) -> Dict[str, Any]:
        return {"state": self._state_locked(), "messages": copy.deepcopy(self._messages)}

    def _state_locked(self) -> Dict[str, Any]:
        link = self._links[-1] if self._links else None
        run = self._active
        return {
            "vscode": link is not None,
            "workspace": workspace_name(link.workspace_info) if link else None,
            "busy": run is not None,
            "message_id": run.message_id if run else None,
            "origin": run.origin if run else None,
        }

    # ── Extensions VS Code ──────────────────────────────────────────────────

    def set_llm_resolver(self, resolver: Optional[Callable[[], Optional[Dict[str, Any]]]]) -> None:
        """Modèle à appeler (chat_url, model, num_ctx), donné par le Relay démarré."""
        with self._lock:
            self._llm_resolver = resolver

    def connect_vscode(
        self, loop: asyncio.AbstractEventLoop, send: Callable[[Dict[str, Any]], None],
        workspace_info: str = "",
    ) -> VSCodeLink:
        """Extension identifiée (client_hello) : elle exécutera les outils."""
        link = VSCodeLink(loop=loop, send=send, workspace_info=workspace_info or "")
        with self._lock:
            self._links.append(link)
            self._emit("state", self._state_locked())
        return link

    def update_vscode(self, link: VSCodeLink, workspace_info: str) -> None:
        """Nouveau client_hello sur le même WebSocket : dossiers ouverts changés."""
        with self._lock:
            link.workspace_info = workspace_info or ""
            self._emit("state", self._state_locked())

    def disconnect_vscode(self, link: VSCodeLink) -> None:
        """WebSocket fermé : une réponse qui comptait sur ses outils s'arrête."""
        with self._lock:
            link.alive = False
            if link in self._links:
                self._links.remove(link)
            run = self._active
            if run is None or run.link is not link:
                self._emit("state", self._state_locked())
                return
            run.stop_reason = tr("code.vscodeLost")
        self._cancel(run)

    def relay_stopped(self) -> None:
        """Relay arrêté : plus d'extension ni de modèle joignable."""
        with self._lock:
            links = list(self._links)
            self._llm_resolver = None
        for link in links:
            self.disconnect_vscode(link)

    def _link_for(self, client: Optional[str]) -> Optional[VSCodeLink]:
        """Extension qui exécutera les outils : celle du message, sinon la plus récente."""
        for link in self._links:
            if client and link.id == client:
                self._links.remove(link)
                self._links.append(link)
                return link
        return self._links[-1] if self._links else None

    def workspace_roots(self) -> List[str]:
        """Dossiers ouverts dans la dernière extension active (le premier : ses outils)."""
        with self._lock:
            link = self._links[-1] if self._links else None
            return workspace_roots(link.workspace_info) if link else []

    def reply_links(self, message_id: str) -> List[Dict[str, Any]]:
        """Fichiers qu'une réponse cite ou nomme (relay/code_links.py) : la page Code
        de la fenêtre et la vue Code du téléphone les rendent cliquables, et en
        montrent l'aperçu."""
        with self._lock:
            message = self._assistant(message_id)
            if message is None:
                return []
            message = copy.deepcopy(message)
            files = conversation_files(self._messages)
        roots = message.get("roots") or self.workspace_roots()
        return reply_links(message, files, roots)

    def known_paths(self) -> set:
        """Pièces jointes des messages de la conversation (chemins normalisés) :
        le Relay en montre l'aperçu au téléphone et à VS Code."""
        with self._lock:
            paths = [item.get("path") for message in self._messages
                     for item in message.get("files") or [] if isinstance(item, dict)]
        return {os.path.normcase(os.path.abspath(path))
                for path in paths if isinstance(path, str) and path}

    # ── Messages ────────────────────────────────────────────────────────────

    def send(
        self, text: str, origin: str, *, client: Optional[str] = None,
        files: Sequence[Tuple[str, str]] = (),
    ) -> str:
        """Message de l'utilisateur ; renvoie son message_id (CodeError si refusé).

        files : pièces jointes, (chemin, nom affiché) : envoyées par le Relay
        (téléphone, VS Code) ou jointes dans la page Code de la fenêtre.
        """
        text = (text or "").strip()
        files = [(path, name) for path, name in files if path]
        if origin not in ORIGINS:
            raise ValueError(f"Origine inconnue : {origin!r}")
        if not text and not files:
            raise CodeError(tr("code.empty"))
        with self._lock:
            if self._active is not None:
                raise CodeError(tr("code.busy"))
            link = self._link_for(client)
            if link is None:
                raise CodeError(tr("code.vscodeOffline"))
            message_id = f"code_{uuid.uuid4().hex}"
            run = _Run(message_id, origin, link, client)
            now = _now()
            user = {"message_id": message_id, "role": "user", "text": text, "origin": origin,
                    "timestamp": now, "attachments": [name for _, name in files],
                    # Leurs chemins sur le PC : leur aperçu (file_preview du Relay)
                    "files": [{"name": name, "path": path} for path, name in files]}
            coroutine = self._run(run, text, files)
            try:
                run.future = asyncio.run_coroutine_threadsafe(coroutine, link.loop)
            except RuntimeError as exc:  # boucle du Relay fermée
                coroutine.close()
                logger.warning("Conversation Code : Relay injoignable (%s)", exc)
                raise CodeError(tr("code.vscodeOffline")) from exc
            self._active = run
            self._append(user)
            self._emit("user", {**user, "client": client})
            # Dossiers du workspace à ce moment : les chemins relatifs que la réponse
            # cite y sont cherchés (relay/code_links.py), même VS Code fermé
            self._append({"message_id": message_id, "role": "assistant", "origin": origin,
                          "timestamp": now, "parts": [], "text": "", "status": "streaming",
                          "roots": workspace_roots(link.workspace_info)})
            self._emit("state", self._state_locked())
        run.future.add_done_callback(lambda future: self._settle(run, future))
        logger.info("Conversation Code : message %s (%s, %d caractères, %d pièce(s) jointe(s))",
                    message_id, origin, len(text), len(files))
        return message_id

    def stop(self) -> bool:
        """Arrête la réponse en cours (Stop de n'importe quelle surface)."""
        with self._lock:
            run = self._active
        if run is None:
            return False
        self._cancel(run)
        return True

    def clear(self) -> None:
        """Nouvelle conversation, sur les trois surfaces ; la réponse en cours s'arrête."""
        with self._lock:
            run = self._active
            if run is not None:
                run.discarded = True
            self._messages = []
            self._llm_history = []
            self._memory_view = None
            self._emit("cleared")
            if run is None:
                self._emit("state", self._state_locked())
        if run is not None:
            self._cancel(run)
        self._save()

    def approve(self, call_id: str, decision: str) -> bool:
        """Réponse à une demande d'approbation, du PC ou du téléphone."""
        with self._lock:
            run = self._active
            options = run.approvals.get(call_id) if run is not None else None
            if not options or decision not in options:
                return False
            link = run.link
        link.send({"type": "tool_approval", "call_id": call_id, "decision": decision})
        return True

    def _cancel(self, run: _Run) -> None:
        # L'extension oublie les approbations en attente de cette réponse
        run.link.send({"type": "code_stop", "message_id": run.message_id})
        future = run.future
        if future is None or not future.cancel():
            self._finish(run, self._partial_text(run), "stopped")

    # ── Outils (fil de la boucle du Relay) ──────────────────────────────────

    @staticmethod
    def tool_result(link: VSCodeLink, call_id: str, content: str, is_error: bool) -> bool:
        """tool_result de l'extension : rend la main à l'appel qui l'attend."""
        future = link.pending.get(call_id)
        if future is None or future.done():
            return False
        future.set_result({"content": content, "is_error": bool(is_error)})
        return True

    def tool_status(self, link: VSCodeLink, call_id: str, status: str,
                    options: Optional[Sequence[str]] = None) -> None:
        """État d'un appel rapporté par l'extension : approbation demandée, en cours, refusé."""
        if status not in _EXTENSION_STATUSES:
            return
        with self._lock:
            run = self._active
            if run is None or run.link is not link:
                return
            part = self._tool_part(run.message_id, call_id)
            if part is None:
                return
            if status == "awaiting-approval":
                # Réponses possibles hors de VS Code : celles d'un message du PC ou
                # du téléphone. Aucune pour un message de VS Code (fenêtre de
                # confirmation de VS Code) : les autres surfaces montrent l'attente.
                choices = [o for o in (options or []) if o in APPROVAL_DECISIONS]
                run.approvals[call_id] = choices
                part["options"] = choices
            else:
                run.approvals.pop(call_id, None)
                part.pop("options", None)
            part["status"] = status
            self._emit("tool", {"message_id": run.message_id, **self._tool_view(part)})

    def _tool_announced(self, run: _Run, call: Dict[str, Any]) -> None:
        with self._lock:
            message = self._current_assistant(run)
            if message is None:
                return
            part = {"kind": "tool", "call_id": str(call.get("call_id", "")),
                    "name": str(call.get("name", "")), "input": _display_input(call.get("input")),
                    "status": "requested"}
            if part["name"] in run.host_tools:
                # Exécuté sur le PC : l'extension ne le voit pas passer (vscode_view)
                part["host"] = True
            message["parts"].append(part)
            self._emit("tool", {"message_id": run.message_id, **self._tool_view(part)})

    def _tool_running(self, run: _Run, call_id: str) -> None:
        """Outil de la mémoire en cours d'exécution, sur le PC."""
        with self._lock:
            if self._current_assistant(run) is None:
                return
            part = self._tool_part(run.message_id, call_id)
            if part is None or part["status"] != "requested":
                return
            part["status"] = "running"
            self._emit("tool", {"message_id": run.message_id, **self._tool_view(part)})

    def _forgotten(self, run: _Run, forgotten: Any) -> None:
        """Fait retiré de la mémoire (« oublie que… », ou remplacé) : une carte, sur les
        trois surfaces."""
        project = project_name(forgotten.project) if forgotten.scope == SCOPE_PROJECT else ""
        shown = {"fact": forgotten.fact, "scope": forgotten.scope}
        if project:
            shown["project"] = project
        with self._lock:
            if self._memory_view is not None:
                # Le modèle le lit dans la note, ou dans le message qui le remplace : le
                # prompt système n'a pas à changer
                self._memory_view.setdefault("removed", []).append(forgotten.fact_id)
            message = self._current_assistant(run)
            if message is None:
                return
            part = {"kind": "tool", "call_id": f"memory_{uuid.uuid4().hex[:12]}",
                    "name": "forget_fact", "input": _display_input(shown),
                    "status": "completed", "output": tr("code.memory.forgotten"), "host": True}
            message["parts"].append(part)
            self._emit("tool", {"message_id": run.message_id, **self._tool_view(part)})

    def _remembered(self, run: _Run, remembered: Any) -> None:
        """Information retenue : une carte dans la réponse, sur les trois surfaces
        (l'information, pour quoi elle vaut, où la retrouver)."""
        project = project_name(remembered.project) if remembered.scope == SCOPE_PROJECT else ""
        if not remembered.created:
            output = tr("code.memory.known")
        elif project:
            output = tr("code.memory.savedProject", project=project)
        else:
            output = tr("code.memory.savedAll")
        shown = {"fact": remembered.fact, "scope": remembered.scope}
        if project:
            shown["project"] = project
        with self._lock:
            if self._memory_view is not None:
                # Le modèle le lit dans l'historique : le prompt système n'a pas à changer
                self._memory_view.setdefault("added", []).append(remembered.fact_id)
            message = self._current_assistant(run)
            if message is None:
                return
            part = {"kind": "tool", "call_id": f"memory_{uuid.uuid4().hex[:12]}",
                    "name": "remember_fact", "input": _display_input(shown),
                    "status": "completed", "output": output, "host": True}
            message["parts"].append(part)
            self._emit("tool", {"message_id": run.message_id, **self._tool_view(part)})

    def _tool_done(self, run: _Run, call_id: str, result: Dict[str, Any]) -> None:
        with self._lock:
            run.approvals.pop(call_id, None)
            if self._current_assistant(run) is None:
                return
            part = self._tool_part(run.message_id, call_id)
            if part is None:
                return
            if part["status"] != "denied":
                part["status"] = "failed" if result.get("is_error") else "completed"
            part["output"] = _clip(result.get("content", ""), MAX_TOOL_OUTPUT)
            part.pop("options", None)
            self._emit("tool", {"message_id": run.message_id, **self._tool_view(part)})

    @staticmethod
    def _tool_view(part: Dict[str, Any]) -> Dict[str, Any]:
        return {key: value for key, value in part.items() if key != "kind"}

    # ── Réponse (boucle du Relay) ───────────────────────────────────────────

    async def _run(self, run: _Run, text: str, files: List[Tuple[str, str]]) -> None:
        """Boucle agentique d'un message, outils exécutés par l'extension VS Code (ceux
        de la mémoire, sur le PC)."""
        config = self._resolve_llm()
        if config is None:
            self._finish(run, tr("relay.engineNotReady"), "error")
            return
        loop = asyncio.get_running_loop()
        # Mémoire de My_AI (core/code_memory.py), si l'appli en a une
        memory = config.get("memory")
        roots = workspace_roots(run.link.workspace_info)
        note, facts, later = "", None, None
        if memory is not None:
            run.host_tools = set(HOST_TOOLS)
            if memory.asks(text):
                # « Retiens… », « oublie… » : fait avant la réponse, qui le confirme
                note = await self._update_memory(run, memory, text, roots, config)
                run.note = note
            elif text:
                # Une préférence donnée en passant : lue pendant la réponse, sans la
                # retarder, montrée à sa fin
                later = asyncio.ensure_future(
                    self._read_memory(run, memory, text, roots, config))
            try:
                facts = await loop.run_in_executor(None, memory.facts, roots)
            except Exception as exc:  # pylint: disable=broad-except
                logger.warning("Conversation Code : faits de la mémoire illisibles (%s)", exc)
        prompt = text
        if files:
            room = int((int(config.get("num_ctx", 32768)) - _REPLY_TOKENS) * _CHARS_PER_TOKEN
                       * _ATTACHMENT_SHARE)
            blocks = await loop.run_in_executor(
                None, _attachment_blocks, files, config.get("describe_image"), text,
                max(room, MAX_ATTACHMENT_CHARS // 3),
            )
            prompt = "\n\n".join(part for part in (text or "Regarde les fichiers joints.", blocks)
                                 if part)
        if note:
            prompt = f"{prompt}\n\n{note}" if prompt else note
        history = self._prepare_history(run.link, config, memory, roots, facts)
        factory = self._executor_factory or AgenticExecutor
        executor = factory(
            ollama_chat_url=config["chat_url"], model=config["model"], num_ctx=config["num_ctx"],
        )

        async def send_tool_use(payload: Dict[str, Any]) -> None:
            run.link.send(payload)

        tools = _HubTools(self, run, RemoteToolExecutor(
            send_fn=send_tool_use,
            pending_calls=run.link.pending,
            message_id=run.message_id,
            loop=loop,
            origin=run.origin,
            keep_waiting=lambda call_id: call_id in run.approvals,
        ), memory, roots)
        try:
            final_text = await executor.run(
                user_message=prompt,
                history=history,
                tool_executor=tools,
                on_chunk=lambda chunk, segment_index=0: self._chunk(run, chunk, segment_index),
                on_tool_call_announced=lambda call: self._tool_announced(run, call),
                on_tool_result=lambda call_id, result: self._tool_done(run, call_id, result),
                workspace_info=run.link.workspace_info,
            )
        except asyncio.CancelledError:
            # Stop, Effacer (_settle s'en charge) : la mémoire lue en parallèle n'est
            # pas écrite, aucune carte ne la montrerait
            if later is not None:
                later.cancel()
            raise
        except Exception as exc:  # pylint: disable=broad-except
            if later is not None:
                later.cancel()
            logger.exception("Conversation Code : boucle agentique en échec (%s)", run.message_id)
            self._finish(run, tr("relay.agenticError", error=exc), "error")
            return
        await self._show_later(run, later)
        self._finish(run, final_text, "done")

    def _resolve_llm(self) -> Optional[Dict[str, Any]]:
        with self._lock:
            resolver = self._llm_resolver
        if resolver is None:
            return None
        try:
            return resolver()
        except Exception as exc:  # pylint: disable=broad-except
            logger.warning("Modèle de la conversation Code introuvable : %s", exc)
            return None

    @staticmethod
    def _llm_of(config: Dict[str, Any]) -> Dict[str, Any]:
        """Le modèle de la conversation, pour lire ce qu'un message change dans la mémoire."""
        return {key: config.get(key) for key in ("chat_url", "model", "num_ctx")}

    async def _update_memory(self, run: _Run, memory: Any, text: str, roots: List[str],
                             config: Dict[str, Any]) -> str:
        """« Retiens que… », « retiens plutôt que… », « oublie que… » : ce que le modèle
        de la conversation lit à retenir et à oublier (core/code_memory.py), fait,
        montré (cartes) et dit au modèle par une note ("" : rien à lui dire)."""
        loop = asyncio.get_running_loop()
        context = self._recent_exchanges(run)
        llm = self._llm_of(config)
        try:
            update = await loop.run_in_executor(
                None, lambda: memory.update(text, roots, context, llm, True))
        except Exception as exc:  # pylint: disable=broad-except
            logger.warning("Conversation Code : mémoire inchangée (%s)", exc)
            return ""
        if update is None:
            return ""
        self._show_update(run, update)
        return update.prompt_note()

    async def _read_memory(self, run: _Run, memory: Any, text: str, roots: List[str],
                           config: Dict[str, Any]) -> Any:
        """Message sans demande : la préférence durable que le modèle de la conversation
        en retient (core/code_memory.py), lue pendant la réponse ; rien n'est écrit si
        elle s'est arrêtée entre-temps (aucune carte ne le montrerait)."""
        loop = asyncio.get_running_loop()
        llm = self._llm_of(config)
        return await loop.run_in_executor(
            None, lambda: memory.update(text, roots, (), llm, False,
                                        lambda: not run.finished))

    async def _show_later(self, run: _Run, later: Any) -> None:
        """Ce que le modèle a retenu d'un message sans demande : des cartes à la fin de
        la réponse."""
        if later is None:
            return
        try:
            update = await asyncio.wait_for(later, timeout=_READ_LATER_SECONDS)
        except Exception as exc:  # pylint: disable=broad-except
            logger.warning("Conversation Code : mémoire non lue (%r)", exc)
            return
        if update is not None:
            self._show_update(run, update)

    def _show_update(self, run: _Run, update: Any) -> None:
        """Les cartes de ce qu'un message a changé dans la mémoire : ce qui part, puis
        ce qui est retenu."""
        for forgotten in update.forgotten:
            logger.info("Conversation Code : 🧠 oublié : %s", forgotten.fact[:80])
            self._forgotten(run, forgotten)
        for remembered in update.remembered:
            logger.info("Conversation Code : 🧠 mémorisé pour %s%s : %s", remembered.where(),
                        "" if update.asked else " (sans demande)", remembered.fact[:80])
            self._remembered(run, remembered)
        if update.asked and not update.changed:
            logger.info("Conversation Code : demande de mémoire sans effet")

    def _recent_exchanges(self, run: _Run) -> List[Tuple[str, str]]:
        """Derniers échanges avant ce message, en texte (sans outils ni notes) : de quoi
        comprendre « retiens-le » (CodeMemory.update)."""
        with self._lock:
            earlier = [message for message in self._messages
                       if message.get("message_id") != run.message_id]
        exchanges = []
        for message in earlier[-_REMEMBER_CONTEXT_MESSAGES:]:
            text = str(message.get("text") or "").strip()
            if text:
                who = "Utilisateur" if message.get("role") == "user" else "Assistant"
                exchanges.append((who, _clip(text, _REMEMBER_CONTEXT_CHARS)))
        return exchanges

    def _prepare_history(
        self, link: VSCodeLink, config: Dict[str, Any], memory: Any = None,
        roots: Sequence[str] = (), facts: Optional[List[Dict[str, Any]]] = None,
    ) -> List[Dict[str, Any]]:
        """Historique du modèle : prompt système à jour, puis borné à la fenêtre de contexte.

        Le prompt système ne change que si les dossiers ouverts, la langue ou
        le jour changent, ou les faits retenus pour le code (_memory_system) :
        un début de prompt modifié fait relire tout l'historique à Ollama. Au-delà
        du budget, les plus anciens échanges partent.
        """
        language = i18n.current_language()
        tools = AGENT_TOOLS + MEMORY_TOOLS if memory is not None else AGENT_TOOLS
        base = build_system_prompt(link.workspace_info, tools=tools, language=language)

        def build(block: str) -> str:
            return build_system_prompt(link.workspace_info, tools=tools, language=language,
                                       memory=block)

        with self._lock:
            history = self._llm_history
            current = (history[0].get("content")
                       if history and history[0].get("role") == "system" else None)
            if memory is None:
                self._memory_view = None
                system = base
            else:
                system = self._memory_system(current, base, memory, roots, facts, build)
            if current is None:
                history.insert(0, {"role": "system", "content": system})
            elif current != system:
                history[0] = {"role": "system", "content": system}
            budget = max(20_000, (int(config.get("num_ctx", 32768)) - _REPLY_TOKENS)
                         * _CHARS_PER_TOKEN)
            total = sum(len(str(item.get("content") or "")) for item in history)
            trimmed = False
            while total > budget and len(history) > 2:
                total -= len(str(history.pop(1).get("content") or ""))
                trimmed = True
            view = self._memory_view
            if trimmed and view and (view.get("added") or view.get("removed")) \
                    and facts is not None:
                # Le début de la conversation part (Ollama relit tout de toute façon) :
                # les faits qu'elle a retenus, dont les notes [Mémoire] ont pu partir
                # avec lui, rejoignent le prompt système
                self._memory_view = None
                history[0] = {"role": "system", "content": self._memory_system(
                    None, base, memory, roots, facts, build)}
            return history

    def _memory_system(
        self, current: Optional[str], base: str, memory: Any, roots: Sequence[str],
        facts: Optional[List[Dict[str, Any]]], build: Callable[[str], str],
    ) -> str:
        """Prompt système avec sa section « Mémoire » (sous le verrou).

        Celui en place reste tant que le reste du prompt (base) ne change pas et
        que les faits qu'il montre sont ceux de la mémoire, à ceux près que la
        conversation a retenus ou oubliés depuis : le modèle l'a lu dans
        l'historique (note [Mémoire] de leur message, ou le message lui-même), et
        refaire le prompt ferait tout relire à Ollama. Un fait modifié ou supprimé
        dans la fenêtre Mémoire, ou retenu ailleurs, le refait. Faits illisibles
        (facts None) : celui en place reste.
        """
        view = self._memory_view
        if current is not None and view is not None and view.get("base") == base:
            if facts is None:
                return current
            added = set(view.get("added") or [])
            gone = added | set(view.get("removed") or [])
            if _without(_signature(facts), added) == _without(view.get("facts") or [], gone):
                return current
        facts = facts or []
        self._memory_view = {"base": base, "facts": _signature(facts), "added": [],
                             "removed": []}
        return build(memory.prompt_block(roots, facts))

    def _chunk(self, run: _Run, text: str, segment: int) -> None:
        """Texte d'une passe du modèle (fil du streaming) : en entier, à sa place."""
        text = _without_note(text, run.note)
        with self._lock:
            message = self._current_assistant(run)
            if message is None:
                return
            part = next((p for p in message["parts"]
                         if p.get("kind") == "text" and p.get("segment") == segment), None)
            if part is None:
                if not text.strip():
                    return  # pas de bulle vide (passe qui n'écrit qu'un appel d'outil)
                part = {"kind": "text", "segment": segment, "text": text}
                message["parts"].append(part)
            elif part["text"] == text:
                return
            else:
                part["text"] = text
            self._emit("chunk", {"message_id": run.message_id, "segment": segment, "text": text})

    def _settle(self, run: _Run, future) -> None:
        """Fin de la tâche, quelle qu'elle soit (rappel du futur)."""
        if run.finished:
            return
        if future.cancelled():
            if run.stop_reason:
                self._finish(run, run.stop_reason, "error")
            else:
                self._finish(run, self._partial_text(run), "stopped")
            return
        error = future.exception()
        if error is not None:
            self._finish(run, tr("relay.agenticError", error=error), "error")
        else:
            self._finish(run, self._partial_text(run), "done")

    def _finish(self, run: _Run, text: str, status: str) -> None:
        text = _without_note(text, run.note)
        with self._lock:
            if run.finished:
                return
            run.finished = True
            run.approvals.clear()
            history = self._llm_history
            if history and history[-1].get("role") == "assistant":
                # Recopiée dans l'historique, le modèle la recopierait de nouveau
                said = str(history[-1].get("content") or "")
                cleaned = _without_note(said, run.note)
                if cleaned != said:
                    history[-1] = {**history[-1], "content": cleaned}
            if self._active is run:
                self._active = None
            if run.discarded:
                self._emit("state", self._state_locked())
                return
            duration_ms = int((time.time() - run.started) * 1000)
            message = self._assistant(run.message_id)
            if message is not None:
                message["status"] = status
                message["text"] = text or ""
                message["duration_ms"] = duration_ms
                for part in message["parts"]:
                    if part.get("kind") == "tool" and part.get("status") in _OPEN_STATUSES:
                        part["status"] = "stopped"
                        part.pop("options", None)
            self._emit("done", {"message_id": run.message_id, "text": text or "",
                                "status": status, "timestamp": _now(),
                                "duration_ms": duration_ms})
            self._emit("state", self._state_locked())
        logger.info("Conversation Code : réponse %s %s (%d caractères, %.1fs)",
                    run.message_id, status, len(text or ""), duration_ms / 1000)
        self._save()

    def _partial_text(self, run: _Run) -> str:
        with self._lock:
            message = self._assistant(run.message_id)
            parts = message["parts"] if message else []
            return "\n\n".join(p["text"] for p in parts if p.get("kind") == "text" and p["text"])

    # ── Transcription ───────────────────────────────────────────────────────

    def _append(self, message: Dict[str, Any]) -> None:
        self._messages.append(message)
        if len(self._messages) > MAX_MESSAGES:
            del self._messages[: len(self._messages) - MAX_MESSAGES]

    def _assistant(self, message_id: str) -> Optional[Dict[str, Any]]:
        for message in reversed(self._messages):
            if message.get("role") == "assistant" and message.get("message_id") == message_id:
                return message
        return None

    def _current_assistant(self, run: _Run) -> Optional[Dict[str, Any]]:
        """Réponse de `run` si elle est toujours en cours (sinon : arrêtée, effacée)."""
        if self._active is not run:
            return None
        return self._assistant(run.message_id)

    def _tool_part(self, message_id: str, call_id: str) -> Optional[Dict[str, Any]]:
        message = self._assistant(message_id)
        for part in message["parts"] if message else []:
            if part.get("kind") == "tool" and part.get("call_id") == call_id:
                return part
        return None

    # ── Enregistrement ──────────────────────────────────────────────────────

    def _load(self) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]],
                             Optional[Dict[str, Any]]]:
        """Conversation du lancement précédent ; une réponse restée en cours est arrêtée.

        Returns:
            (transcription, historique du modèle, section « Mémoire » de son prompt)
        """
        if self._store is None:
            return [], [], None
        try:
            with open(self._store, "r", encoding="utf-8") as fh:
                data = json.load(fh)
        except FileNotFoundError:
            return [], [], None
        except (OSError, ValueError) as exc:
            logger.warning("Conversation Code illisible (%s) : %s", self._store, exc)
            return [], [], None
        if not isinstance(data, dict):
            return [], [], None
        messages = []
        for item in data.get("messages") or []:
            if (not isinstance(item, dict) or item.get("role") not in ("user", "assistant")
                    or not isinstance(item.get("message_id"), str)):
                continue
            if item["role"] == "assistant":
                if not isinstance(item.get("parts"), list):
                    item["parts"] = []
                if item.get("status") == "streaming":
                    item["status"] = "stopped"
                for part in item["parts"]:
                    if isinstance(part, dict) and part.get("status") in _OPEN_STATUSES:
                        part["status"] = "stopped"
                        part.pop("options", None)
            messages.append(item)
        llm = [item for item in data.get("llm") or []
               if isinstance(item, dict) and isinstance(item.get("role"), str)
               and isinstance(item.get("content"), str)]
        view = data.get("memory")
        if not (isinstance(view, dict) and isinstance(view.get("base"), str)
                and isinstance(view.get("facts"), list)):
            view = None
        return messages[-MAX_MESSAGES:], llm, view

    def _save(self) -> None:
        """Écrit la conversation (écriture atomique) ; un échec est journalisé, jamais levé."""
        if self._store is None:
            return
        with self._lock:
            data = {"version": 1, "messages": copy.deepcopy(self._messages),
                    "llm": list(self._llm_history),
                    "memory": copy.deepcopy(self._memory_view)}
        with self._save_lock:
            try:
                self._store.parent.mkdir(parents=True, exist_ok=True)
                tmp = self._store.with_suffix(".json.tmp")
                # ASCII échappé : une sortie d'outil peut porter un demi-caractère
                # UTF-16 (surrogate), que l'UTF-8 refuse d'écrire
                with open(tmp, "w", encoding="utf-8") as fh:
                    json.dump(data, fh, ensure_ascii=True)
                os.replace(tmp, self._store)
            except (OSError, ValueError, TypeError) as exc:
                logger.warning("Conversation Code non enregistrée : %s", exc)


class _HubTools:
    """Outils d'une réponse : ceux de la mémoire sur le PC (HOST_TOOLS), les autres
    dans l'extension VS Code (RemoteToolExecutor)."""

    def __init__(self, hub: CodeHub, run: _Run, remote: RemoteToolExecutor,
                 memory: Any, roots: Sequence[str]):
        self._hub = hub
        self._run = run
        self._remote = remote
        self._memory = memory
        self._roots = list(roots)

    async def call(self, call_id: str, name: str, input_data: Dict[str, Any],
                   timeout: Optional[float] = None) -> Dict[str, Any]:
        if self._memory is None or name not in HOST_TOOLS:
            return await self._remote.call(call_id=call_id, name=name, input_data=input_data,
                                           timeout=timeout)
        self._hub._tool_running(self._run, call_id)  # pylint: disable=protected-access
        data = input_data if isinstance(input_data, dict) else {}
        query = str(data.get("query") or "").strip()
        if not query:
            return {"content": "Argument « query » manquant : dis ce que tu cherches.",
                    "is_error": True}
        try:
            n_results = min(_MAX_MEMORY_RESULTS, max(1, int(data.get("n_results") or 5)))
        except (TypeError, ValueError):
            n_results = 5
        document = str(data.get("document") or "").strip()
        loop = asyncio.get_running_loop()
        try:
            content = await loop.run_in_executor(
                None, self._memory.search, query, n_results, document, self._roots)
        except Exception as exc:  # pylint: disable=broad-except
            logger.warning("Conversation Code : search_memory en échec (%s)", exc)
            return {"content": f"Erreur mémoire : {exc}", "is_error": True}
        return {"content": content, "is_error": False}


def _signature(facts: List[Dict[str, Any]]) -> List[List[Any]]:
    """Ce qui, des faits, change la section « Mémoire » : leur texte et leur portée."""
    return [[fact.get("id"), *fact_scope(fact), str(fact.get("key") or ""),
             str(fact.get("value") or "")] for fact in facts]


def _without(signature: List[List[Any]], ids: set) -> List[List[Any]]:
    return [entry for entry in signature if entry and entry[0] not in ids]


def _attachment_blocks(
    files: Sequence[Tuple[str, str]],
    describe: Optional[Callable[[str, str], Optional[str]]] = None,
    question: str = "",
    room: int = MAX_ATTACHMENT_CHARS,
) -> str:
    """Pièces jointes données au modèle avec le message, comme dans les Agents.

    Texte des documents et du code (lecteur du chat : PDF avec OCR, Word,
    Excel, PowerPoint) ; une image est décrite par le modèle vision
    (describe : LocalLLM.describe_image), la question du message en contexte.
    room : caractères pour l'ensemble, au-delà les fichiers suivants sont cités sans leur texte.
    """
    blocks = []
    for path, name in files:
        if Path(path).suffix.lower() in _IMAGE_EXTS:
            block = _image_block(path, name, describe, question)
        elif room <= 0:
            block = f"[Pièce jointe « {name} » non lue : trop de texte joint à ce message]"
        else:
            block = _text_block(path, name, min(MAX_ATTACHMENT_CHARS, room))
        room -= len(block)
        blocks.append(block)
    return "\n\n".join(blocks)


def _text_block(path: str, name: str, limit: int) -> str:
    """Document ou code joint : son texte, borné à limit caractères."""
    from processors.attachments import read_attachment_text  # pylint: disable=import-outside-toplevel

    try:
        content = read_attachment_text(path)
    except Exception as exc:  # pylint: disable=broad-except
        return f"[Pièce jointe « {name} » illisible : {exc}]"
    if not content.strip():
        return f"[Pièce jointe « {name} » vide]"
    return f"Pièce jointe « {name} » :\n```\n{_clip(content, limit)}\n```"


def _image_block(path: str, name: str, describe: Optional[Callable[[str, str], Optional[str]]],
                 question: str) -> str:
    """Image jointe, en texte : sa description par le modèle vision."""
    from core.chat_service import encode_image  # pylint: disable=import-outside-toplevel

    description = None
    if describe is not None:
        try:
            image, _width, _height = encode_image(path)
            description = describe(image, question or "Décris cette image.")
        except Exception as exc:  # pylint: disable=broad-except
            logger.warning("Image jointe non décrite (%s) : %s", name, exc)
    if not description:
        return (f"[Image jointe « {name} » : aucun modèle ne voit les images "
                "(ollama pull qwen3.5:4b).]")
    return f"Image jointe « {name} », décrite par le modèle vision :\n{description.strip()}"


# ── Protocole du Relay ──────────────────────────────────────────────────────


def vscode_view(event: Dict[str, Any], link_id: str) -> Optional[Dict[str, Any]]:
    """Événement du hub pour l'extension VS Code (None : rien à lui envoyer).

    L'extension garde son protocole : ack de ses propres messages (avec leur
    texte, pour ceux qu'elle n'a pas affichés : sélection, fichier envoyés
    par commande), chunk et response de la réponse. Les appels d'outils, elle
    les exécute : ses propres cartes les montrent. Seuls ceux exécutés sur le
    PC (mémoire de My_AI : search_memory, « retiens que… ») lui arrivent, en
    code_tool.
    """
    kind = event.get("type")
    fields = {key: value for key, value in event.items() if key not in ("type", "client")}
    if kind == "tool":
        return {"type": "code_tool", **fields} if event.get("host") else None
    if kind == "snapshot":
        return {"type": "code_snapshot", **fields}
    if kind == "state":
        return {"type": "code_state", **fields}
    if kind == "user":
        if event.get("client") == link_id:
            return {"type": "ack", **fields}
        return {"type": "code_user", **fields}
    if kind == "chunk":
        return {"type": "chunk", "message_id": event["message_id"], "text": event["text"],
                "segment_index": event["segment"], "timestamp": _now()}
    if kind == "done":
        message = tr("relay.interrupted") if event["status"] == "stopped" else event["text"]
        return {"type": "response", "message": message, "message_id": event["message_id"],
                "timestamp": event["timestamp"], "status": event["status"],
                "duration_ms": event.get("duration_ms")}
    if kind == "cleared":
        return {"type": "code_cleared"}
    return None


def mobile_view(event: Dict[str, Any]) -> Dict[str, Any]:
    """Événement du hub pour la vue Code du téléphone : code_snapshot, code_chunk…
    (le Relay y ajoute les liens des réponses, RelayServer.code_mobile_view)."""
    fields = {key: value for key, value in event.items() if key not in ("type", "client")}
    return {"type": f"code_{event.get('type')}", **fields}


_HUB: Optional[CodeHub] = None
_HUB_LOCK = threading.Lock()


def get_code_hub() -> CodeHub:
    """Hub de la conversation Code, un par processus (Relay et fenêtre desktop)."""
    global _HUB  # pylint: disable=global-statement
    with _HUB_LOCK:
        if _HUB is None:
            _HUB = CodeHub()
        return _HUB
