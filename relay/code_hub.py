"""
Conversation « Code » : le chat de l'extension VS Code, partagé par trois surfaces

L'extension VS Code, la page Code de la fenêtre desktop et la vue Code du
téléphone (Relay) montrent la même conversation : un message envoyé de l'une,
la réponse en streaming, les appels d'outils et leurs approbations, l'arrêt et
l'effacement paraissent sur les trois. Chaque message lance la boucle
agentique (core/agentic_executor.py) sur la boucle asyncio du Relay ; ses
outils s'exécutent toujours dans l'extension VS Code connectée, qui demande
l'accord de l'utilisateur avant d'écrire un fichier ou de lancer une commande.

Le chat « classique » (téléphone et fenêtre desktop, RelayBridge) ne voit rien
de cette conversation, et elle ne voit rien de lui.

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
from core.agentic_executor import AgenticExecutor, RemoteToolExecutor, build_system_prompt
from core.i18n import tr
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


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _clip(text: Any, limit: int) -> str:
    text = text if isinstance(text, str) else json.dumps(text, ensure_ascii=False, default=str)
    return text if len(text) <= limit else text[:limit] + "…"


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
        self._messages, self._llm_history = self._load()

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
                    "timestamp": now, "attachments": [name for _, name in files]}
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
            self._append({"message_id": message_id, "role": "assistant", "origin": origin,
                          "timestamp": now, "parts": [], "text": "", "status": "streaming"})
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
        """Boucle agentique d'un message, outils exécutés par l'extension VS Code."""
        config = self._resolve_llm()
        if config is None:
            self._finish(run, tr("relay.engineNotReady"), "error")
            return
        loop = asyncio.get_running_loop()
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
        history = self._prepare_history(run.link, config)
        factory = self._executor_factory or AgenticExecutor
        executor = factory(
            ollama_chat_url=config["chat_url"], model=config["model"], num_ctx=config["num_ctx"],
        )

        async def send_tool_use(payload: Dict[str, Any]) -> None:
            run.link.send(payload)

        tools = RemoteToolExecutor(
            send_fn=send_tool_use,
            pending_calls=run.link.pending,
            message_id=run.message_id,
            loop=loop,
            origin=run.origin,
            keep_waiting=lambda call_id: call_id in run.approvals,
        )
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
        except Exception as exc:  # pylint: disable=broad-except
            # (Stop, Effacer : CancelledError n'est pas une Exception, _settle s'en charge)
            logger.exception("Conversation Code : boucle agentique en échec (%s)", run.message_id)
            self._finish(run, tr("relay.agenticError", error=exc), "error")
            return
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

    def _prepare_history(self, link: VSCodeLink, config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Historique du modèle : prompt système à jour, puis borné à la fenêtre de contexte.

        Le prompt système ne change que si les dossiers ouverts ou la langue
        changent : un début de prompt modifié fait relire tout l'historique à
        Ollama. Au-delà du budget, les plus anciens échanges partent.
        """
        system = build_system_prompt(link.workspace_info, language=i18n.current_language())
        with self._lock:
            history = self._llm_history
            if history and history[0].get("role") == "system":
                if history[0].get("content") != system:
                    history[0] = {"role": "system", "content": system}
            else:
                history.insert(0, {"role": "system", "content": system})
            budget = max(20_000, (int(config.get("num_ctx", 32768)) - _REPLY_TOKENS)
                         * _CHARS_PER_TOKEN)
            total = sum(len(str(item.get("content") or "")) for item in history)
            while total > budget and len(history) > 2:
                total -= len(str(history.pop(1).get("content") or ""))
            return history

    def _chunk(self, run: _Run, text: str, segment: int) -> None:
        """Texte d'une passe du modèle (fil du streaming) : en entier, à sa place."""
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
        with self._lock:
            if run.finished:
                return
            run.finished = True
            run.approvals.clear()
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

    def _load(self) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Conversation du lancement précédent ; une réponse restée en cours est arrêtée."""
        if self._store is None:
            return [], []
        try:
            with open(self._store, "r", encoding="utf-8") as fh:
                data = json.load(fh)
        except FileNotFoundError:
            return [], []
        except (OSError, ValueError) as exc:
            logger.warning("Conversation Code illisible (%s) : %s", self._store, exc)
            return [], []
        if not isinstance(data, dict):
            return [], []
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
        return messages[-MAX_MESSAGES:], llm

    def _save(self) -> None:
        """Écrit la conversation (écriture atomique) ; un échec est journalisé, jamais levé."""
        if self._store is None:
            return
        with self._lock:
            data = {"version": 1, "messages": copy.deepcopy(self._messages),
                    "llm": list(self._llm_history)}
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
    les exécute : ses propres cartes les montrent.
    """
    kind = event.get("type")
    fields = {key: value for key, value in event.items() if key not in ("type", "client")}
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
    """Événement du hub pour la vue Code du téléphone : code_snapshot, code_chunk…"""
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
