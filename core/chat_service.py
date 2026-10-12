"""
Service de chat, sans interface : du message de l'utilisateur à la réponse

Extrait de l'interface Tk (interfaces/gui/base.py, file_handling.py,
message_editing.py, sidebar.py) pour servir la fenêtre web, le chat mobile du
Relay et les tests, fenêtre ouverte ou non.

Les appels au moteur sont ceux de l'interface Tk, avec les mêmes arguments et
dans le même ordre (quel_handle_message_with_id) : tant que le prompt ne fait
que s'allonger, Ollama n'en relit que la fin (docs/OPTIMIZATION.md, section 8).
Le service ne réécrit ni l'historique du modèle ni son message système, sauf là
où Tk le faisait déjà : édition d'un message, changement de variante,
chargement d'une session.

Les messages du desktop et du mobile passent par une file commune et sont
traités un à la fois : Ollama ne sert qu'une requête à la fois pour my_ai.

L'état de la conversation (conversation_history, turn_branches) garde le format
de l'interface Tk, pour que les sessions s'ouvrent dans les deux. Les réponses
y gagnent des clés optionnelles (réflexion, appels d'outils, documents, durée),
que Tk ignore.
"""

import asyncio
import base64
import io
import os
import random
import re
import threading
import time
import traceback
from collections import deque
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Tuple
from uuid import uuid4

from utils.logger import setup_logger

logger = setup_logger("ChatService")

# Signature du collecteur d'événements : (type, charge, conversation, message)
# → événement publié (dict portant son seq), cf. interfaces/desktop/events.py
EmitFn = Callable[..., Optional[Dict[str, Any]]]

BUSY_MESSAGE = "⏳ Attendez la fin de la réponse en cours."

# Génération de fichier : mêmes mots-clés que l'interface Tk et AIEngine
FILE_GENERATION_KEYWORDS = (
    "génère moi un fichier",
    "crée moi un fichier",
    "génère un fichier",
    "crée un fichier",
)
_FILENAME_RE = re.compile(r"fichier\s+([a-zA-Z0-9_\-]+\.\w+)", re.IGNORECASE)

# Messages variés de fin de génération de fichier (interface Tk)
FILE_GENERATION_MESSAGES = [
    "✅ Votre fichier est prêt ! Vous pouvez le télécharger en cliquant simplement sur son nom. 👇\n\nEst-ce que vous souhaitez autre chose ? ",
    "🎉 Fichier généré avec succès ! Cliquez sur le nom pour le télécharger. 👇\n\nBesoin d'autre chose ? ",
    "✨ Et voilà ! Votre fichier est créé. Un simple clic sur le nom pour le récupérer. 👇\n\nQue puis-je faire d'autre pour vous ? ",
    "🚀 Génération terminée ! Le fichier est prêt au téléchargement (cliquez sur le nom). 👇\n\nUne autre demande ? ",
    "💾 Fichier créé ! Téléchargez-le en cliquant sur son nom ci-dessous. 👇\n\nJe peux vous aider pour autre chose ? ",
    "✅ Mission accomplie ! Votre fichier vous attend. Cliquez pour télécharger. 👇\n\nAutre chose à générer ? ",
    "🎯 Fichier prêt à être téléchargé ! Un clic sur le nom et c'est bon. 👇\n\nQu'est-ce qu'on fait ensuite ? ",
    "⚡ C'est fait ! Votre fichier est disponible. Cliquez dessus pour le récupérer. 👇\n\nUne autre création ? ",
]
# Réponse retenue dans l'historique du modèle, sans le nom du fichier
FILE_GENERATION_HISTORY = (
    "✅ Votre fichier est prêt ! Vous pouvez le télécharger en cliquant simplement "
    "sur son nom. 👇\n\n🚀 Est-ce que vous souhaitez autre chose ?"
)

# Réponse interrompue, renvoyée au mobile
INTERRUPTED_SUFFIX = "\n\n⚠️ *Réponse interrompue.*"
INTERRUPTED_EMPTY = "⚠️ Réponse interrompue."

# Ligne de pièce jointe ajoutée au texte d'un message (cf. _bubble_text)
ATTACH_LINE_RE = re.compile(r"^(?:📎|🖼️|🖼)\s+\S")
# Préfixe des pièces jointes envoyées par le mobile (cf. relay/relay_server.py)
_RELAY_UPLOAD_PREFIX_RE = re.compile(r"^[0-9a-f]{16}_")

_CODE_EXTENSIONS = {
    ".py", ".pyw", ".js", ".mjs", ".cjs", ".ts", ".tsx", ".jsx",
    ".html", ".htm", ".css", ".scss", ".sass", ".less",
    ".json", ".xml", ".yaml", ".yml", ".toml", ".ini", ".cfg", ".conf",
    ".md", ".rst", ".txt", ".log",
    ".sh", ".bash", ".bat", ".cmd", ".ps1",
    ".c", ".h", ".cpp", ".hpp", ".cs", ".java", ".kt",
    ".go", ".rs", ".rb", ".php", ".lua", ".sql",
    ".vue", ".svelte", ".dart", ".swift",
}
_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp", ".tiff", ".tif"}

# Nom d'une session : début de son premier message
_SESSION_NAME_MAX = 48

# Résultat d'outil en échec (début du texte renvoyé par l'outil)
_FAILED_TOOL_STARTS = ("❌", "⚠️", "Erreur", "[Erreur", "[Suppression annulée", "[Interrompu")
_URL_RE = re.compile(r"https?://[^\s)\]]+")


class ChatError(Exception):
    """Action refusée ; le message s'affiche tel quel à l'utilisateur."""


def file_type_for(path: str) -> Optional[str]:
    """Type de pièce jointe d'après l'extension (types de l'interface Tk)."""
    ext = os.path.splitext(path)[1].lower()
    if ext == ".pdf":
        return "PDF"
    if ext in (".docx", ".doc"):
        return "DOCX"
    if ext in (".xlsx", ".xls", ".csv"):
        return "Excel"
    if ext in (".pptx", ".potx"):
        return "PowerPoint"
    if ext in _CODE_EXTENSIONS:
        return "Code"
    if ext in _IMAGE_EXTENSIONS:
        return "Image"
    return None


def display_name(path: str) -> str:
    """Nom de fichier affiché, sans le préfixe des envois du mobile."""
    return _RELAY_UPLOAD_PREFIX_RE.sub("", os.path.basename(path or ""))


def bubble_text(message: str, attachments: List[Tuple[str, str]]) -> str:
    """Texte d'un message suivi de ses pièces jointes (_build_attachment_lines)."""
    lines = []
    for path, file_type in attachments:
        emoji = "🖼️" if file_type == "Image" else "📎"
        lines.append(f"{emoji} {display_name(path)}")
    if not lines:
        return message
    return (message.rstrip() + "\n" + "\n".join(lines)).strip()


def split_attachments(text: str) -> Tuple[str, List[str]]:
    """Sépare le corps d'un message de ses lignes de pièces jointes finales."""
    lines = (text or "").split("\n")
    attach = []
    while lines and ATTACH_LINE_RE.match(lines[-1]):
        attach.insert(0, lines.pop())
    return "\n".join(lines).rstrip(), attach


def session_name_for(text: str) -> str:
    """Nom d'une nouvelle session : début de son premier message."""
    body, _lines = split_attachments(text or "")
    body = " ".join(body.split())
    if len(body) > _SESSION_NAME_MAX:
        cut = body[:_SESSION_NAME_MAX].rsplit(" ", 1)[0] or body[:_SESSION_NAME_MAX]
        body = cut.rstrip(" ,;:.!?") + "…"
    return body or "Conversation"


def tool_label(tool_name: str, args: Dict[str, Any]) -> str:
    """Libellé d'un appel d'outil, repris de l'interface Tk (on_tool_call)."""
    def base(key):
        return os.path.basename(args.get(key, "")) if key in args else ""

    labels = {
        "web_search": f"🔍 Recherche sur internet : « {args.get('query', '')} »",
        "search_memory": "🧠 Consultation de la mémoire",
        "remember_fact": f"🧠 Mémorisé : « {args.get('fact', '')} »",
        "read_local_file": f"📄 Lecture du fichier : {args.get('path', '')}",
        "list_directory": f"📁 Exploration du répertoire : {args.get('path', '.')}",
        "generate_code": f"💻 Génération de code {args.get('language', '')}",
        "generate_document": f"📄 Rédaction du document {args.get('format', '')}",
        "edit_document": f"✏️ Modification de : {base('path')}",
        "calculate": f"🔢 Calcul : {args.get('expression', '')}",
        "search_local_files": f"🔎 Recherche de fichiers : « {args.get('query', '')} »",
        "write_local_file": f"💾 Modification du fichier : {base('path')}",
        "move_local_file": f"🚚 Déplacement : {base('source')}",
        "delete_local_file": f"🗑️ Suppression : {base('path')}",
        "create_directory": f"📂 Création du dossier : {base('path')}",
        "synthesis": "🧠 Analyse du résultat et synthèse en cours",
    }
    return labels.get(tool_name, f"🔧 Outil en cours : {tool_name}…")


def _short_args(args: Dict[str, Any], limit: int = 400) -> Dict[str, Any]:
    """Arguments d'outil allégés pour l'affichage (contenu d'un fichier écrit…)."""
    short = {}
    for key, value in (args or {}).items():
        if isinstance(value, str) and len(value) > limit:
            value = value[:limit] + "…"
        elif not isinstance(value, (str, int, float, bool, type(None))):
            value = str(value)[:limit]
        short[key] = value
    return short


def _tool_summary(tool_name: str, result: Any) -> Dict[str, Any]:
    """Résumé d'un résultat d'outil : réussite, première ligne, sources."""
    text = result if isinstance(result, str) else str(result or "")
    stripped = text.strip()
    first = next((line.strip() for line in stripped.splitlines() if line.strip()), "")
    if len(first) > 160:
        first = first[:157] + "…"
    sources = len(set(_URL_RE.findall(text))) if tool_name == "web_search" else 0
    return {
        "ok": bool(stripped) and not stripped.startswith(_FAILED_TOOL_STARTS),
        "summary": first,
        "sources": sources,
    }


def _iso(stamp: Any) -> Optional[str]:
    """Horodatage en ISO 8601, qu'il soit datetime ou chaîne (après JSON)."""
    if isinstance(stamp, datetime):
        return stamp.isoformat()
    if isinstance(stamp, str) and stamp:
        try:
            return datetime.fromisoformat(stamp).isoformat()
        except ValueError:
            return stamp
    return None


def encode_image(path: str) -> Tuple[str, int, int]:
    """Encode une image pour le modèle vision (_process_image_file de Tk).

    Returns:
        (base64 JPEG, largeur, hauteur)
    """
    from PIL import Image  # pylint: disable=import-outside-toplevel

    img = Image.open(path)
    # Normaliser pour la vision : alpha et palette, puis RGB
    if img.mode in ("RGBA", "LA"):
        alpha = img.getchannel("A")
        _alpha_min, alpha_max = alpha.getextrema()
        if alpha_max <= 5:
            # Presse-papier Windows : alpha quasi vide mais RGB utile
            img = img.convert("RGB")
        else:
            background = Image.new("RGB", img.size, (255, 255, 255))
            background.paste(img.convert("RGB"), mask=alpha)
            img = background
    elif img.mode != "RGB":
        img = img.convert("RGB")
    # 1024 px de côté au plus pour Ollama
    max_size = 1024
    if img.width > max_size or img.height > max_size:
        img.thumbnail((max_size, max_size), Image.LANCZOS)
    buffer = io.BytesIO()
    img.save(buffer, format="JPEG", quality=92, optimize=True)
    return base64.b64encode(buffer.getvalue()).decode("utf-8"), img.width, img.height


@dataclass
class _Attachment:
    """Pièce jointe dans la zone de saisie, pas encore envoyée."""

    id: str
    path: str
    name: str
    type: str
    status: str = "ready"  # loading, ready, error
    cancel: Optional[threading.Event] = None
    image_b64: Optional[str] = None

    def view(self) -> Dict[str, Any]:
        """Vue publique (API, événements)."""
        return {"id": self.id, "path": self.path, "name": self.name,
                "type": self.type, "status": self.status}


@dataclass
class _Request:
    """Message en file d'attente, du desktop ou du mobile."""

    id: str
    source: str  # desktop, mobile
    text: str  # texte transmis au moteur (avant expansion des slash commands)
    bubble: str  # texte affiché et gardé dans l'historique
    attachments: List[Tuple[str, str]] = field(default_factory=list)
    image_path: Optional[str] = None
    image_b64: Optional[str] = None
    mid: Optional[str] = None  # repris d'un tour édité
    edit: bool = False  # nouvelle variante d'un tour (pas d'historique des commandes)
    history_query: Optional[str] = None  # entrée de l'historique des commandes
    relay_message_id: Optional[str] = None
    relay_files: List[str] = field(default_factory=list)


@dataclass
class _Turn:
    """Réponse en cours."""

    mid: str
    request: _Request
    kind: str  # chat, file, image
    reasoning: bool = False
    started: float = field(default_factory=time.time)
    text: str = ""
    tokens: int = 0
    first_token_at: Optional[float] = None
    thinking: str = ""
    thinking_started: Optional[float] = None
    thinking_ms: int = 0
    thinking_done_sent: bool = False
    tools: List[Dict[str, Any]] = field(default_factory=list)
    documents: List[str] = field(default_factory=list)
    status: str = ""  # génération de fichier ou d'image : étape affichée
    filename: Optional[str] = None
    file_path: Optional[str] = None
    image_path: Optional[str] = None


class ChatService:
    """Conversation du chat : file d'attente, pipeline du moteur, pièces jointes,
    variantes d'édition et sessions."""

    def __init__(
        self,
        engine,
        emit: EmitFn,
        *,
        config=None,
        file_processor=None,
        ui_connected: Optional[Callable[[], bool]] = None,
        on_session_change: Optional[Callable[[Optional[str]], None]] = None,
    ):
        """
        Args:
            engine: AIEngine (ou un moteur factice dans les tests)
            emit: collecteur d'événements (EventBus.publish)
            config: core.config.Config de l'appli (génération d'image)
            file_processor: utils.file_processor.FileProcessor (pièces jointes)
            ui_connected: vrai si une fenêtre peut répondre à une confirmation
            on_session_change: appelé avec la session courante (persistance)
        """
        self._engine = engine
        self._emit_fn = emit
        self._config = config
        self._file_processor = file_processor
        self._ui_connected = ui_connected or (lambda: False)
        self._on_session_change = on_session_change

        # État et émission sous le même verrou : l'état renvoyé par snapshot()
        # contient exactement les événements de seq inférieur ou égal au sien
        self._lock = threading.RLock()
        self._cond = threading.Condition(self._lock)
        # Une seule opération lourde à la fois : réponse, chargement de session…
        self._op_lock = threading.Lock()
        self._last_seq = 0

        self._history: List[Dict[str, Any]] = []
        self._branches: Dict[str, Dict[str, Any]] = {}
        self._session_id: Optional[str] = None
        self._session_name: Optional[str] = None

        self._attachments: List[_Attachment] = []
        # Documents chargés en mémoire par une pièce jointe pas encore envoyée :
        # la retirer les oublie (cf. _forget_if_unused)
        self._introduced: set = set()

        self._queue: deque = deque()
        self._pending: Optional[_Request] = None  # sorti de la file, pas encore commencé
        self._active: Optional[_Request] = None
        self._answering = False  # réponse en cours (puis sauvegarde de la session)
        self._turn: Optional[_Turn] = None
        self._interrupted = False
        self._confirm: Optional[Dict[str, Any]] = None

        self._closed = False
        self._worker: Optional[threading.Thread] = None
        self._bridge = None
        self._bridge_watch: Optional[threading.Thread] = None
        self._fallback_prompt_library = None

    # ── Cycle de vie ────────────────────────────────────────────────────────

    def start(self) -> None:
        """Démarre le fil qui traite la file d'attente."""
        if self._worker is not None:
            return
        self._worker = threading.Thread(target=self._worker_loop, name="chat-worker", daemon=True)
        self._worker.start()

    def close(self) -> None:
        """Arrête la réponse en cours et le fil de la file d'attente."""
        with self._cond:
            self._closed = True
            self._interrupted = True
            self._resolve_confirm(False)
            self._cond.notify_all()
        self.detach_bridge()

    # ── Émission ────────────────────────────────────────────────────────────

    def _emit(self, event_type: str, payload: Optional[Dict[str, Any]] = None,
              message_id: Optional[str] = None) -> None:
        """Publie un événement de la conversation courante (verrou d'état tenu)."""
        with self._lock:
            try:
                event = self._emit_fn(
                    event_type, payload or {},
                    conversation_id=self._session_id, message_id=message_id,
                )
            except Exception as exc:  # pylint: disable=broad-except
                logger.warning("Émission de %s impossible : %s", event_type, exc)
                return
            if isinstance(event, dict) and isinstance(event.get("seq"), int):
                self._last_seq = event["seq"]

    def _notify(self, level: str, message: str) -> None:
        self._emit("notification", {"level": level, "message": message})

    # ── Accès au moteur ─────────────────────────────────────────────────────

    def _local_ai(self):
        return getattr(self._engine, "local_ai", None)

    def _llm(self):
        """LocalLLM du moteur (historique de conversation du modèle)."""
        local_ai = self._local_ai()
        return getattr(local_ai, "local_llm", None) if local_ai is not None else None

    def _sessions(self):
        return getattr(self._engine, "session_manager", None)

    def _prompt_library(self):
        """Bibliothèque de prompts du moteur, sinon une instance locale (Tk)."""
        lib = getattr(self._engine, "prompt_library", None)
        if lib is not None:
            return lib
        if self._fallback_prompt_library is None:
            try:
                from core.prompt_library import PromptLibrary  # pylint: disable=import-outside-toplevel
                self._fallback_prompt_library = PromptLibrary()
            except Exception:  # pylint: disable=broad-except
                self._fallback_prompt_library = None
        return self._fallback_prompt_library

    # ── État ────────────────────────────────────────────────────────────────

    def _busy(self) -> bool:
        return bool(self._answering or self._pending or self._queue)

    @contextmanager
    def _exclusive(self):
        """Opération sur la conversation (édition, session…), refusée pendant une réponse.

        Après une réponse, le fil de la file garde la main le temps d'enregistrer
        la session : l'opération l'attend, quelques millisecondes.
        """
        with self._lock:
            if self._busy():
                raise ChatError(BUSY_MESSAGE)
        if not self._op_lock.acquire(timeout=5):
            raise ChatError(BUSY_MESSAGE)
        try:
            with self._lock:
                if self._busy():
                    raise ChatError(BUSY_MESSAGE)
                yield
        finally:
            self._op_lock.release()

    @property
    def busy(self) -> bool:
        """Vrai pendant une réponse ou s'il reste des messages en file."""
        with self._lock:
            return self._busy()

    @property
    def session_id(self) -> Optional[str]:
        """Session courante (None avant le premier message)."""
        with self._lock:
            return self._session_id

    def snapshot(self) -> Dict[str, Any]:
        """État complet de la conversation, pour la fenêtre (GET /api/conversation)."""
        with self._lock:
            messages = [self._view_entry(entry) for entry in self._history]
            return {
                "conversation_id": self._session_id,
                "name": self._session_name,
                "seq": self._last_seq,
                "messages": messages,
                "branches": {
                    mid: {"count": len(branch.get("versions", [])),
                          "current": branch.get("current", 0)}
                    for mid, branch in self._branches.items()
                    if len(branch.get("versions", [])) > 1
                },
                "active": self._view_turn(),
                "queue": self._queue_view(),
                "attachments": [att.view() for att in self._attachments],
                "confirm": self._confirm_view(),
                "busy": self._busy(),
            }

    @staticmethod
    def _view_entry(entry: Dict[str, Any]) -> Dict[str, Any]:
        """Message de l'historique vu par la fenêtre."""
        attachments = []
        for item in entry.get("attachments") or []:
            if isinstance(item, (list, tuple)) and item and isinstance(item[0], str):
                file_type = item[1] if len(item) > 1 else (file_type_for(item[0]) or "Code")
                attachments.append({"path": item[0], "name": display_name(item[0]),
                                    "type": file_type})
        view = {
            "mid": entry.get("mid"),
            "role": "user" if entry.get("is_user") else "assistant",
            "text": entry.get("text", ""),
            "timestamp": _iso(entry.get("timestamp")),
            "type": entry.get("type", "text"),
            "attachments": attachments,
            "image_path": entry.get("image_path"),
        }
        for key in ("source", "thinking", "thinking_ms", "tool_calls", "documents",
                    "file_path", "interrupted", "error", "duration_ms", "tokens_per_s"):
            if entry.get(key) not in (None, "", [], False):
                view[key] = entry[key]
        return view

    def _view_turn(self) -> Optional[Dict[str, Any]]:
        turn = self._turn
        if turn is None:
            return None
        return {
            "request_id": turn.request.id,
            "mid": turn.mid,
            "kind": turn.kind,
            "source": turn.request.source,
            "reasoning": turn.reasoning,
            "text": turn.text,
            "thinking": turn.thinking,
            "tools": [dict(tool) for tool in turn.tools],
            "documents": list(turn.documents),
            "status": turn.status,
            "filename": turn.filename,
            "started_at": datetime.fromtimestamp(turn.started).isoformat(),
        }

    def _queue_view(self) -> List[Dict[str, Any]]:
        return [
            {"request_id": req.id, "source": req.source, "text": req.bubble}
            for req in self._queue
        ]

    def _confirm_view(self) -> Optional[Dict[str, Any]]:
        if not self._confirm:
            return None
        path = self._confirm["path"]
        return {"confirm_id": self._confirm["id"], "kind": "delete_file", "path": path,
                "name": os.path.basename(path)}

    # ── Envoi et file d'attente ─────────────────────────────────────────────

    def send(
        self,
        text: str,
        attachment_ids: Optional[List[str]] = None,
        *,
        edit_mid: Optional[str] = None,
        regenerate: bool = False,
    ) -> str:
        """Envoie un message du desktop (ou une nouvelle version d'un tour).

        Args:
            text: message saisi
            attachment_ids: pièces jointes à envoyer (None : toutes celles en attente)
            edit_mid: tour modifié (mid du message de l'utilisateur)
            regenerate: nouvelle variante du même texte

        Returns:
            Identifiant de la requête

        Raises:
            ChatError: message vide, pièce jointe en lecture, tour introuvable…
        """
        if edit_mid:
            return self._edit(edit_mid, text, regenerate)
        message = (text or "").strip()
        if not message:
            raise ChatError("Message vide.")
        with self._cond:
            if self._closed:
                raise ChatError("Le chat est arrêté.")
            selected = self._select_attachments(attachment_ids)
            loading = [att for att in selected if att.status == "loading"]
            if loading:
                # Sinon la question part sans le contenu du fichier
                raise ChatError(
                    "⏳ Pièce jointe en cours de chargement : envoi possible dès qu'elle est prête"
                    if len(loading) == 1 else
                    "⏳ Pièces jointes en cours de chargement : envoi possible dès qu'elles sont prêtes"
                )
            # Une pièce jointe illisible reste citée dans le message, comme dans Tk
            files = [(att.path, att.type) for att in selected]
            images = [att for att in selected if att.type == "Image" and att.image_b64]
            image = images[-1] if images else None
            request = _Request(
                id=uuid4().hex,
                source="desktop",
                text=message,
                bubble=bubble_text(message, files),
                attachments=files,
                image_path=image.path if image else None,
                image_b64=image.image_b64 if image else None,
                history_query=message,
            )
            self._consume_attachments(selected)
            self._enqueue(request)
        return request.id

    def _enqueue(self, request: _Request) -> None:
        """Ajoute une requête à la file (verrou tenu)."""
        self._queue.append(request)
        self._emit("queue.updated", {"items": self._queue_view()})
        self._cond.notify_all()

    def cancel(self, request_id: str) -> bool:
        """Retire un message encore en file d'attente."""
        with self._cond:
            for request in list(self._queue):
                if request.id == request_id:
                    self._queue.remove(request)
                    self._emit("queue.updated", {"items": self._queue_view()})
                    self._relay_submit_response(request, INTERRUPTED_EMPTY)
                    return True
        return False

    def stop(self) -> bool:
        """Arrête la réponse en cours (bouton Stop, Échap). Vrai s'il y en avait une."""
        with self._lock:
            if self._active is None:
                return False
            self._interrupted = True
            self._resolve_confirm(False)
            return True

    def _is_stale(self, request: _Request) -> bool:
        """Vrai si la réponse à `request` doit s'arrêter (Stop, autre requête)."""
        return self._interrupted or self._active is not request

    def _worker_loop(self) -> None:
        while True:
            with self._cond:
                while not self._queue and not self._closed:
                    self._cond.wait()
                if self._closed:
                    return
                request = self._queue.popleft()
                self._pending = request
                self._emit("queue.updated", {"items": self._queue_view()})
            with self._op_lock:
                try:
                    self._process(request)
                except Exception:  # pylint: disable=broad-except
                    logger.error("Requête %s en échec :\n%s", request.id, traceback.format_exc())
                finally:
                    with self._lock:
                        self._active = None
                        self._pending = None
                        self._turn = None

    # ── Traitement d'une requête ────────────────────────────────────────────

    def _process(self, request: _Request) -> None:
        with self._lock:
            self._pending = None
            self._active = request
            self._answering = True
            self._interrupted = False
            self._add_user_entry(request)

        try:
            if not request.edit:
                history = getattr(self._engine, "command_history", None)
                if history is not None:
                    try:
                        history.add(query=request.history_query or "")
                    except Exception:  # pylint: disable=broad-except
                        pass

            if request.source == "mobile":
                self._prepare_relay_attachments(request)

            self._answer(request)
        finally:
            with self._lock:
                self._answering = False
        self._save_current()

    def _add_user_entry(self, request: _Request) -> None:
        """Message de l'utilisateur dans l'historique (verrou tenu)."""
        if self._session_id is None:
            self._create_session(request.bubble)
        mid = request.mid or uuid4().hex
        request.mid = mid
        entry = {
            "text": request.bubble,
            "is_user": True,
            "timestamp": datetime.now(),
            "type": "text",
            "attachments": [list(item) for item in request.attachments],
            "image_path": request.image_path,
            "mid": mid,
        }
        if request.source == "mobile":
            entry["source"] = "mobile"
        self._history.append(entry)
        self._emit("message.user", {
            "mid": mid,
            "request_id": request.id,
            "text": request.bubble,
            "source": request.source,
            "timestamp": _iso(entry["timestamp"]),
            "attachments": self._view_entry(entry)["attachments"],
            "image_path": request.image_path,
        }, message_id=mid)

    def _answer(self, request: _Request) -> None:
        """Pipeline de quel_handle_message_with_id : mêmes appels, même ordre."""
        # Slash commands : « /commande arguments » → prompt détaillé ; le
        # message affiché garde la commande courte
        user_text = self._expand_slash_command(request.text)

        # Documents injectés : ceux joints à la conversation affichée
        self._sync_visible_documents()

        if any(keyword in user_text.lower() for keyword in FILE_GENERATION_KEYWORDS):
            self._generate_file(request, user_text)
            return

        try:
            is_image_request = self._engine.is_image_generation_request(user_text)
        except Exception:  # pylint: disable=broad-except
            is_image_request = False
        if is_image_request:
            self._generate_image(request, user_text)
            return

        self._stream_answer(request, user_text)

    def _expand_slash_command(self, text: str) -> str:
        """Étend « /commande arguments » via la bibliothèque de prompts."""
        if not text or not text.lstrip().startswith("/"):
            return text
        lib = self._prompt_library()
        if lib is None:
            return text
        try:
            expanded = lib.expand(text)
        except Exception:  # pylint: disable=broad-except
            return text
        return expanded if expanded else text

    def _sync_visible_documents(self) -> None:
        """Déclare au moteur les pièces jointes de la conversation affichée.

        Un fichier joint dans une variante d'édition abandonnée ne doit plus
        être injecté (cf. AIEngine.set_visible_documents).
        """
        engine = self._engine
        if not hasattr(engine, "set_visible_documents"):
            return
        names = set()
        paths = []
        with self._lock:
            messages = list(self._history)
        for msg in messages:
            for item in msg.get("attachments") or []:
                # (path, type) en mémoire, [path, type] après un aller-retour JSON
                if not isinstance(item, (list, tuple)) or not item:
                    continue
                path = item[0]
                if isinstance(path, str) and path:
                    names.add(os.path.basename(path))
                    paths.append(path)
        engine.set_visible_documents(names)
        # edit_document ouvre le vrai fichier : il lui faut le chemin
        if hasattr(engine, "set_attached_documents"):
            engine.set_attached_documents(paths)

    # ── Réponse en streaming ────────────────────────────────────────────────

    def _begin_turn(self, request: _Request, kind: str, reasoning: bool = False,
                    filename: Optional[str] = None, status: str = "") -> _Turn:
        with self._lock:
            turn = _Turn(mid=uuid4().hex, request=request, kind=kind, reasoning=reasoning,
                         filename=filename, status=status)
            self._turn = turn
            self._emit("assistant.start", {
                "mid": turn.mid, "request_id": request.id, "kind": kind,
                "reasoning": reasoning, "filename": filename,
            }, message_id=turn.mid)
            return turn

    def _stream_answer(self, request: _Request, user_text: str) -> None:
        engine = self._engine
        turn: Optional[_Turn] = None
        error: Optional[str] = None
        try:
            image_b64 = request.image_b64
            # Même évaluation que Tk : Ollama joignable, requête complexe, puis
            # requête conversationnelle (bloc « Réflexion » ou non)
            is_complex = (
                engine.is_ollama_active()
                and engine.is_complex_query(user_text)
                and not image_b64
            )
            is_conversational = (
                hasattr(engine, "is_conversational")
                and engine.is_conversational(user_text)
            )
            show_reasoning = not is_conversational and is_complex
            turn = self._begin_turn(request, "chat", reasoning=bool(show_reasoning))

            response = engine.process_query_stream(
                user_text,
                on_token=lambda token: self._on_token(turn, token),
                on_tool_call=lambda name, args: self._on_tool_call(turn, name, args),
                on_thinking_token=(
                    (lambda token: self._on_thinking_token(turn, token))
                    if show_reasoning else None
                ),
                on_thinking_complete=(
                    (lambda: self._on_thinking_complete(turn)) if show_reasoning else None
                ),
                image_base64=image_b64,
                is_interrupted_callback=lambda: self._is_stale(request),
                on_delete_confirm=lambda path: self._confirm_delete(request, path),
                on_document=lambda path: self._on_document(turn, path),
                on_tool_result=lambda name, args, result: self._on_tool_result(
                    turn, name, args, result),
            )
            # Réponse non streamée (repli sans Ollama) : affichée d'un bloc
            if not self._is_stale(request) and not turn.text and response:
                self._on_token(turn, response)
        except Exception as exc:  # pylint: disable=broad-except
            logger.error("Réponse en échec :\n%s", traceback.format_exc())
            error = f"❌ Erreur IA : {exc}"
            if turn is None:
                turn = self._begin_turn(request, "chat")
        self._finish_turn(turn, error=error)

    def _on_token(self, turn: _Turn, token: str) -> bool:
        request = turn.request
        with self._lock:
            if self._is_stale(request):
                return False
            if turn.first_token_at is None:
                turn.first_token_at = time.time()
            turn.text += token
            turn.tokens += 1
            self._emit("assistant.token", {"text": token}, message_id=turn.mid)
            text = turn.text
        # Le bridge limite lui-même la cadence des envois au mobile
        if request.source == "mobile" and self._bridge_active():
            try:
                self._bridge.submit_ai_chunk(text, message_id=request.relay_message_id)
            except Exception:  # pylint: disable=broad-except
                pass
        return True

    def _on_tool_call(self, turn: _Turn, tool_name: str, args: Dict[str, Any]) -> None:
        label = tool_label(tool_name, args or {})
        logger.info("[MCP] %s", label)
        with self._lock:
            if self._is_stale(turn.request):
                return
            before = turn.text
            if tool_name == "synthesis":
                # La synthèse commence un nouveau paragraphe
                if turn.text:
                    turn.text = turn.text.rstrip("\n") + "\n\n"
            elif turn.text.endswith("\n"):
                # L'indicateur d'outil suit directement le texte
                turn.text = turn.text.rstrip("\n")
            if turn.text != before:
                self._emit("assistant.sync", {"text": turn.text}, message_id=turn.mid)
            turn.tools.append({"name": tool_name, "label": label})
            self._emit("tool.call", {"name": tool_name, "label": label,
                                     "args": _short_args(args)}, message_id=turn.mid)

    def _on_tool_result(self, turn: _Turn, tool_name: str, _args: Dict[str, Any],
                        result: Any) -> None:
        summary = _tool_summary(tool_name, result)
        with self._lock:
            if self._is_stale(turn.request):
                return
            for tool in reversed(turn.tools):
                if tool["name"] == tool_name and "ok" not in tool:
                    tool.update(summary)
                    break
            self._emit("tool.result", {"name": tool_name, **summary}, message_id=turn.mid)

    def _on_thinking_token(self, turn: _Turn, token: str) -> bool:
        with self._lock:
            if self._is_stale(turn.request):
                return False
            if turn.thinking_started is None:
                turn.thinking_started = time.time()
            turn.thinking += token
            self._emit("assistant.thinking", {"text": token}, message_id=turn.mid)
            return True

    def _on_thinking_complete(self, turn: _Turn) -> None:
        with self._lock:
            # Appelé à la fin de chaque passe (« Analyse », « Synthèse ») et
            # encore à la fin du traitement : une seule fin par passe
            if turn.thinking_started is None and turn.thinking_done_sent:
                return
            if turn.thinking_started is not None:
                turn.thinking_ms += int((time.time() - turn.thinking_started) * 1000)
                turn.thinking_started = None
            turn.thinking_done_sent = True
            self._emit("assistant.thinking_done", {"duration_ms": turn.thinking_ms},
                       message_id=turn.mid)

    def _on_document(self, turn: _Turn, path: str) -> None:
        request = turn.request
        with self._lock:
            if self._active is not request or not path or path in turn.documents:
                return
            turn.documents.append(path)
            self._emit("document.created", {"path": path, "name": os.path.basename(path)},
                       message_id=turn.mid)
        # Mobile : aperçu et fichier envoyés chiffrés, comme une image générée
        if request.source == "mobile" and self._bridge_active():
            try:
                self._bridge.submit_ai_document(path, message_id=request.relay_message_id)
            except Exception as exc:  # pylint: disable=broad-except
                logger.warning("Envoi du document au mobile échoué : %s", exc)

    def _confirm_delete(self, request: _Request, path: str) -> bool:
        """Demande à la fenêtre de confirmer une suppression (fil du moteur bloqué)."""
        confirm_id = uuid4().hex
        done = threading.Event()
        with self._lock:
            self._confirm = {"id": confirm_id, "path": path, "event": done, "accepted": False}
            self._emit("confirm.request", self._confirm_view())
        # Sans fenêtre pour répondre, la suppression est refusée
        while not done.wait(0.2):
            if self._is_stale(request) or not self._ui_connected():
                with self._lock:
                    self._resolve_confirm(False)
                break
        with self._lock:
            accepted = bool(self._confirm and self._confirm["id"] == confirm_id
                            and self._confirm["accepted"])
            if self._confirm and self._confirm["id"] == confirm_id:
                self._confirm = None
            self._emit("confirm.closed", {"confirm_id": confirm_id, "accepted": accepted})
        return accepted

    def confirm(self, confirm_id: str, accepted: bool) -> bool:
        """Réponse de la fenêtre à une demande de confirmation."""
        with self._lock:
            if not self._confirm or self._confirm["id"] != confirm_id:
                return False
            self._confirm["accepted"] = bool(accepted)
            self._confirm["event"].set()
            return True

    def _resolve_confirm(self, accepted: bool) -> None:
        """Répond d'office à la confirmation en attente (verrou tenu)."""
        if self._confirm:
            self._confirm["accepted"] = accepted
            self._confirm["event"].set()

    def _finish_turn(self, turn: _Turn, error: Optional[str] = None,
                     entry_type: str = "text") -> None:
        """Range la réponse dans l'historique et l'annonce (fin, arrêt ou échec)."""
        request = turn.request
        with self._lock:
            interrupted = self._interrupted and not error
            text = turn.text or (error or "")
            now = time.time()
            duration_ms = int((now - turn.started) * 1000)
            tokens_per_s = None
            if turn.first_token_at and turn.tokens > 1:
                span = now - turn.first_token_at
                if span > 0.2:
                    # Un fragment streamé par Ollama correspond à un jeton
                    tokens_per_s = round(turn.tokens / span, 1)
            if turn.thinking_started is not None:
                turn.thinking_ms += int((now - turn.thinking_started) * 1000)
                turn.thinking_started = None
            if text:
                entry = {
                    "text": text,
                    "is_user": False,
                    "timestamp": datetime.now(),
                    "type": entry_type,
                    "attachments": [],
                    "image_path": turn.image_path,
                    "mid": turn.mid,
                    "duration_ms": duration_ms,
                }
                if turn.thinking:
                    entry["thinking"] = turn.thinking
                    entry["thinking_ms"] = turn.thinking_ms
                if turn.tools:
                    entry["tool_calls"] = [dict(tool) for tool in turn.tools
                                           if tool["name"] != "synthesis"]
                if turn.documents:
                    entry["documents"] = list(turn.documents)
                if turn.file_path:
                    entry["file_path"] = turn.file_path
                if tokens_per_s:
                    entry["tokens_per_s"] = tokens_per_s
                if interrupted:
                    entry["interrupted"] = True
                if error:
                    entry["error"] = True
                self._history.append(entry)
            # Réponse rangée : édition et sessions redeviennent possibles
            self._answering = False
            if error:
                self._emit("assistant.error", {"mid": turn.mid, "message": error},
                           message_id=turn.mid)
            elif interrupted:
                self._emit("assistant.interrupted", {"mid": turn.mid, "text": text},
                           message_id=turn.mid)
            else:
                self._emit("assistant.done", {
                    "mid": turn.mid, "text": text, "duration_ms": duration_ms,
                    "tokens_per_s": tokens_per_s,
                }, message_id=turn.mid)
            self._turn = None

        if request.source == "mobile":
            if interrupted and turn.kind == "chat":
                self._relay_submit_response(
                    request, (text + INTERRUPTED_SUFFIX) if text else INTERRUPTED_EMPTY
                )
            else:
                self._relay_submit_response(request, text or INTERRUPTED_EMPTY)

    # ── Génération de fichier ───────────────────────────────────────────────

    def _generate_file(self, request: _Request, user_text: str) -> None:
        """Branche « génération de fichier » de quel_handle_message_with_id."""
        match = _FILENAME_RE.search(user_text)
        filename = match.group(1) if match else "fichier.py"
        turn = self._begin_turn(request, "file", filename=filename,
                                status=f"Création du fichier '{filename}' en cours...")

        def check_interrupted():
            return self._is_stale(request)

        if check_interrupted():
            turn.text = "⚠️ Création du fichier interrompue."
            self._finish_turn(turn, entry_type="file_generation")
            return
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result = loop.run_until_complete(
                    self._engine.process_query(
                        user_text, is_interrupted_callback=check_interrupted
                    )
                )
            finally:
                loop.close()
        except (OSError, ValueError) as exc:
            turn.text = f"❌ Erreur: {exc}"
            self._finish_turn(turn, entry_type="file_generation")
            return

        if result.get("interrupted"):
            turn.text = "⚠️ Création du fichier interrompue."
        elif result.get("type") == "file_generation" and result.get("success"):
            shown = result.get("filename") or filename
            turn.text = random.choice(FILE_GENERATION_MESSAGES) + shown
            turn.file_path = result.get("file_path")
            with self._lock:
                self._emit("file.created", {"path": turn.file_path or "", "name": shown},
                           message_id=turn.mid)
            # Le modèle se souvient du fichier créé
            llm = self._llm()
            if llm is not None and hasattr(llm, "add_to_history"):
                try:
                    llm.add_to_history("user", user_text)
                    llm.add_to_history("assistant", FILE_GENERATION_HISTORY)
                except (AttributeError, TypeError) as exc:
                    logger.warning("Ajout à l'historique du modèle échoué : %s", exc)
        else:
            turn.text = "❌ Erreur lors de la génération du fichier."
        self._finish_turn(turn, entry_type="file_generation")

    # ── Génération d'image ──────────────────────────────────────────────────

    def _generate_image(self, request: _Request, user_text: str) -> None:
        """_handle_image_generation_ui sans interface : progression, arrêt, image."""
        turn = self._begin_turn(request, "image", status="Génération de l'image en cours")
        interrupted_text = "⏹️ Génération de l'image interrompue."

        def is_interrupted():
            return self._is_stale(request)

        def on_progress(fraction, message):
            if not message:
                return
            with self._lock:
                turn.status = message
                self._emit("image.progress", {
                    "message": message,
                    "fraction": float(fraction) if isinstance(fraction, (int, float)) else None,
                }, message_id=turn.mid)

        try:
            gen = getattr(self._engine, "image_generator", None)
            # Aucun backend : installation automatique de ComfyUI (1ʳᵉ fois)
            if gen is not None and not gen.is_available():
                if not self._auto_setup_image_backend(gen, on_progress, is_interrupted):
                    if is_interrupted():
                        turn.text = interrupted_text
                        self._finish_turn(turn, entry_type="image_generation")
                        return
            if gen is None or not gen.is_available():
                turn.text = (
                    gen.unavailable_message() if gen is not None
                    else "🎨 Génération d'image indisponible."
                )
                self._finish_turn(turn, entry_type="image_generation")
                return

            prompt = self._engine.extract_image_prompt(user_text)
            result = gen.generate(prompt, on_progress=on_progress, is_interrupted=is_interrupted)
            if result.interrupted or is_interrupted():
                turn.text = interrupted_text
            elif result.success and result.image_path:
                # Le modèle sait qu'une image a été générée (« de quoi on a parlé ? »)
                self._remember_image_generation(user_text, prompt, result.image_path)
                turn.text = result.message
                turn.image_path = result.image_path
                with self._lock:
                    self._emit("image.created", {
                        "path": result.image_path, "name": os.path.basename(result.image_path),
                    }, message_id=turn.mid)
                if request.source == "mobile" and self._bridge_active():
                    try:
                        self._bridge.submit_ai_image(result.image_path,
                                                     message_id=request.relay_message_id)
                    except Exception as exc:  # pylint: disable=broad-except
                        logger.warning("Envoi de l'image au mobile échoué : %s", exc)
            else:
                turn.text = result.message
        except Exception as exc:  # pylint: disable=broad-except
            logger.error("Génération d'image en échec :\n%s", traceback.format_exc())
            turn.text = f"⚠️ Erreur génération d'image : {exc}"
        self._finish_turn(turn, entry_type="image_generation")

    def _auto_setup_image_backend(self, gen, on_progress, is_interrupted) -> bool:
        """Installe et lance ComfyUI portable au premier usage, si activé."""
        try:
            auto = bool(self._config.get("image_generation.auto_setup", True)) \
                if self._config is not None else True
        except Exception:  # pylint: disable=broad-except
            auto = True
        if not auto:
            return False
        try:
            from models.comfyui_manager import (  # pylint: disable=import-outside-toplevel
                ComfyUISetupError, get_comfyui_manager)
        except Exception as exc:  # pylint: disable=broad-except
            logger.warning("comfyui_manager indisponible : %s", exc)
            return False
        manager = get_comfyui_manager()
        if not manager.is_supported():
            return False
        on_progress(None, "Installation de la génération d'image (1ʳᵉ fois)…")
        try:
            ok = manager.ensure_running(on_progress=on_progress, is_interrupted=is_interrupted)
        except ComfyUISetupError as exc:
            if str(exc) == "__interrupted__" or is_interrupted():
                return False
            logger.warning("Auto-setup ComfyUI échoué : %s", exc)
            on_progress(None, f"Échec installation ComfyUI : {exc}")
            return False
        except Exception as exc:  # pylint: disable=broad-except
            logger.warning("Auto-setup ComfyUI exception : %s", exc)
            return False
        if ok:
            # Le générateur passe sur l'instance ComfyUI gérée pour cette session
            try:
                gen.config.backend = "comfyui"
                gen.resolve_backend(force=True)
            except Exception:  # pylint: disable=broad-except
                pass
        return ok and gen.is_available()

    def _remember_image_generation(self, user_text: str, prompt: str, image_path: str) -> None:
        """Inscrit la génération d'image dans l'historique du modèle (Tk)."""
        llm = self._llm()
        if llm is None or not hasattr(llm, "add_to_history"):
            return
        try:
            filename = os.path.basename(image_path)
            llm.add_to_history("user", user_text)
            llm.add_to_history(
                "assistant",
                f"🎨 J'ai généré une image à partir de la description « {prompt} » "
                f"et je l'ai affichée dans le chat (fichier : {filename}).",
            )
        except Exception as exc:  # pylint: disable=broad-except
            logger.warning("Ajout de l'image au contexte du modèle échoué : %s", exc)

    # ── Pièces jointes ──────────────────────────────────────────────────────

    def add_attachment(self, path: str, file_type: Optional[str] = None) -> Dict[str, Any]:
        """Joint un fichier au prochain message ; un document est lu en arrière-plan.

        Raises:
            ChatError: chemin invalide, dossier, format non supporté, image illisible
        """
        path = os.path.abspath(path or "")
        if os.path.isdir(path):
            raise ChatError("📁 Pour un dossier, utilisez « Dossiers du projet ».")
        if not os.path.isfile(path):
            raise ChatError(f"❌ Chemin invalide : {path}")
        file_type = file_type or file_type_for(path)
        if file_type is None:
            ext = os.path.splitext(path)[1].lower() or "?"
            raise ChatError(f"❌ Format non supporté : {ext}")
        name = os.path.basename(path)
        attachment = _Attachment(id=uuid4().hex, path=path, name=name, type=file_type)

        if file_type == "Image":
            try:
                attachment.image_b64, width, height = encode_image(path)
            except Exception as exc:
                raise ChatError(f"❌ Erreur lors du traitement de l'image : {exc}") from exc
            with self._lock:
                self._attachments.append(attachment)
                self._emit("attachment.added", attachment.view())
                self._notify("success", f"✅ {name} prête ({width}x{height})")
            return attachment.view()

        attachment.status = "loading"
        attachment.cancel = threading.Event()
        with self._lock:
            if not self._document_in_memory(name):
                # Cette pièce jointe charge le document : la retirer l'oubliera
                self._introduced.add(name)
            self._attachments.append(attachment)
            self._emit("attachment.added", attachment.view())
        threading.Thread(
            target=self._read_attachment, args=(attachment,), name="attachment", daemon=True
        ).start()
        return attachment.view()

    def remove_attachment(self, attachment_id: str) -> bool:
        """Retire une pièce jointe avant l'envoi : arrête sa lecture, oublie son document."""
        with self._lock:
            attachment = next((att for att in self._attachments if att.id == attachment_id), None)
            if attachment is None:
                return False
            self._attachments.remove(attachment)
            self._emit("attachment.removed", {"id": attachment_id})
            if attachment.status == "loading" and attachment.cancel is not None:
                # La lecture s'arrête avant la page suivante ; ce qu'elle a déjà
                # rangé en mémoire est oublié à sa fin (_read_attachment)
                attachment.cancel.set()
                return True
        if attachment.type != "Image":
            self._forget_if_unused(attachment.path)
        return True

    def attachments(self) -> List[Dict[str, Any]]:
        """Pièces jointes en attente."""
        with self._lock:
            return [att.view() for att in self._attachments]

    def _select_attachments(self, attachment_ids: Optional[List[str]]) -> List[_Attachment]:
        if attachment_ids is None:
            return list(self._attachments)
        by_id = {att.id: att for att in self._attachments}
        return [by_id[att_id] for att_id in attachment_ids if att_id in by_id]

    def _consume_attachments(self, selected: List[_Attachment]) -> None:
        """Pièces jointes envoyées : elles appartiennent désormais au message."""
        for attachment in selected:
            if attachment in self._attachments:
                self._attachments.remove(attachment)
                self._introduced.discard(attachment.name)
                self._emit("attachment.removed", {"id": attachment.id})

    def _read_attachment(self, attachment: _Attachment) -> None:
        """Lecture d'un document joint (process_file_background de Tk)."""
        ok, error = self._load_document(attachment.path, attachment.name, attachment.cancel)
        cancelled = attachment.cancel is not None and attachment.cancel.is_set()
        with self._lock:
            if cancelled:
                attachment.status = "error"
            elif ok:
                attachment.status = "ready"
                if attachment in self._attachments:
                    self._emit("attachment.ready", {"id": attachment.id})
                self._notify("success", f"✅ {attachment.name} prêt")
            else:
                attachment.status = "error"
                if attachment in self._attachments:
                    self._emit("attachment.failed", {"id": attachment.id, "message": error})
                self._notify("error", f"❌ Erreur : {attachment.name}")
        if cancelled:
            # Retirée pendant sa lecture : ce qui est déjà en mémoire est oublié
            self._forget_if_unused(attachment.path)

    def _load_document(self, path: str, filename: str,
                       cancel: Optional[threading.Event] = None) -> Tuple[bool, str]:
        """Extrait le contenu d'un document et le range dans la mémoire du moteur.

        Returns:
            (succès, message d'erreur)
        """
        from processors.ocr import interruptible  # pylint: disable=import-outside-toplevel

        try:
            if self._file_processor is None:
                raise ValueError("Lecture des fichiers indisponible")
            # L'OCR s'arrête avant la page suivante si la pièce jointe est retirée
            with interruptible(cancel):
                result = self._file_processor.process_file(path)
            if cancel is not None and cancel.is_set():
                return False, ""
            if result.get("error"):
                raise ValueError(result["error"])
            content = result.get("content", "")
            if not content or not content.strip():
                raise ValueError(f"Le fichier {filename} semble vide ou illisible")

            custom_ai = self._local_ai()
            if custom_ai is not None:
                try:
                    if hasattr(custom_ai, "add_file_to_context"):
                        # Processeurs spécialisés (PDF, DOCX, code…)
                        with interruptible(cancel):
                            custom_ai.add_file_to_context(path)
                    elif hasattr(custom_ai, "add_document_to_context"):
                        custom_ai.add_document_to_context(content, filename)
                except Exception as exc:  # pylint: disable=broad-except
                    logger.warning("Ajout au contexte de %s échoué : %s", filename, exc)
            if cancel is not None and cancel.is_set():
                return False, ""
            # Mémoire classique, pour compatibilité
            memory = getattr(custom_ai, "conversation_memory", None)
            if memory is not None and hasattr(memory, "store_document_content"):
                memory.store_document_content(filename, content)
            return True, ""
        except Exception as exc:  # pylint: disable=broad-except
            if cancel is not None and cancel.is_set():
                return False, ""  # lecture interrompue : pas d'erreur à signaler
            logger.error("Erreur lors du traitement de %s : %s", filename, exc)
            return False, str(exc)

    def _document_in_memory(self, name: str) -> bool:
        memory = getattr(self._local_ai(), "conversation_memory", None)
        return name in getattr(memory, "stored_documents", {})

    def _names_attached_to_messages(self) -> set:
        """Noms des fichiers joints aux messages, variantes d'édition comprises."""
        messages = list(self._history)
        for branch in list(self._branches.values()):
            for version in branch.get("versions", []):
                messages.append(version)
                messages.extend(version.get("tail") or [])
        names = set()
        for message in messages:
            for item in message.get("attachments") or []:
                if isinstance(item, (list, tuple)) and item and isinstance(item[0], str):
                    names.add(os.path.basename(item[0]))
        return names

    def _forget_if_unused(self, path: str) -> None:
        """Oublie le document d'une pièce jointe retirée, s'il ne sert plus.

        Il sert encore s'il était en mémoire avant elle, s'il est joint à une
        autre pièce en attente, ou à un message de la conversation ou de l'une
        de ses variantes.
        """
        name = os.path.basename(path)
        with self._lock:
            if name not in self._introduced:
                return
            if any(att.name == name for att in self._attachments):
                return
            if name in self._names_attached_to_messages():
                return
            self._introduced.discard(name)
        forget = getattr(self._local_ai(), "remove_document_from_context", None)
        if forget is None:
            return
        try:
            result = forget(name) or {}
        except Exception as exc:  # pylint: disable=broad-except
            logger.warning("Document %s non oublié : %s", name, exc)
            return
        if result.get("stored") or result.get("chunks_removed"):
            logger.info("🗑️ Pièce jointe retirée, document oublié : %s", name)

    # ── Variantes d'édition (message_editing.py) ────────────────────────────

    def _turn_start_index(self, turn_key: Optional[str]) -> Optional[int]:
        if not turn_key:
            return None
        for index, message in enumerate(self._history):
            if message.get("is_user") and message.get("mid") == turn_key:
                return index
        return None

    def _turn_end_index(self, start: int) -> int:
        """Index du premier message après le tour qui commence à `start`."""
        history = self._history
        has_ai = start + 1 < len(history) and not history[start + 1].get("is_user")
        return start + 2 if has_ai else start + 1

    def _persist_version(self, branch: Dict[str, Any], start: int) -> None:
        """Recopie le tour affiché, suite comprise, dans sa variante courante."""
        history = self._history
        version = branch["versions"][branch["current"]]
        if start < len(history):
            entry = history[start]
            version["user"] = entry.get("text", "")
            version["attachments"] = list(entry.get("attachments") or [])
            version["image_path"] = entry.get("image_path")
            version["timestamp"] = entry.get("timestamp")
        end = self._turn_end_index(start)
        has_ai = end == start + 2
        version["ai"] = history[start + 1].get("text", "") if has_ai else None
        version["ai_mid"] = history[start + 1].get("mid") if has_ai else None
        version["tail"] = [dict(message) for message in history[end:]]

    def _edit(self, turn_key: str, new_text: str, regenerate: bool) -> str:
        """Nouvelle variante d'un tour : archive l'actuelle, tronque, régénère."""
        with self._exclusive():
            start = self._turn_start_index(turn_key)
            if start is None:
                raise ChatError("Message introuvable.")
            if start + 1 >= len(self._history):
                raise ChatError("Ce message n'a pas encore de réponse à regénérer.")
            old_entry = self._history[start]
            original, attach_lines = split_attachments(old_entry.get("text", ""))
            body = original if regenerate else (new_text or "").strip()
            if not body:
                raise ChatError("Message vide.")
            if not regenerate and body == original.strip():
                raise ChatError("Le message n'a pas changé.")
            attachments = [tuple(item) for item in old_entry.get("attachments") or []
                           if isinstance(item, (list, tuple)) and item]
            image_path = old_entry.get("image_path")

            # La bulle éditée garde les mêmes lignes de pièces jointes
            bubble = body
            if attach_lines:
                bubble = (body.rstrip() + "\n" + "\n".join(attach_lines)).strip()

            branch = self._branches.get(turn_key)
            if branch is None:
                branch = {"versions": [{}], "current": 0}
                self._branches[turn_key] = branch
            # Archiver le tour affiché (réponse et suite comprises)
            self._persist_version(branch, start)
            branch["versions"].append({
                "attachments": [list(item) for item in attachments],
                "image_path": image_path, "user": bubble, "ai": None, "tail": [],
            })
            branch["current"] = len(branch["versions"]) - 1

            # Tronquer à partir du tour édité, réaligner l'historique du modèle
            self._history = self._history[:start]
            self._rewind_engine_history()

            # L'image de vision, consommée au premier envoi, est ré-encodée
            image_b64 = None
            if image_path and os.path.isfile(image_path):
                try:
                    image_b64 = encode_image(image_path)[0]
                except Exception as exc:  # pylint: disable=broad-except
                    logger.warning("Ré-encodage de l'image échoué : %s", exc)

            self._emit("conversation.loaded", {
                "reason": "edited", "snapshot": self.snapshot(),
            })
            request = _Request(
                id=uuid4().hex, source="desktop", text=body, bubble=bubble,
                attachments=list(attachments), image_path=image_path,
                image_b64=image_b64, mid=turn_key, edit=True,
            )
            self._enqueue(request)
        return request.id

    def navigate(self, turn_key: str, target_version: int) -> None:
        """Affiche une autre variante d'un tour (‹ k/n ›).

        Raises:
            ChatError: réponse en cours, tour ou variante introuvable
        """
        with self._exclusive():
            branch = self._branches.get(turn_key)
            versions = branch["versions"] if branch else []
            if not 0 <= target_version < len(versions):
                raise ChatError("Variante introuvable.")
            start = self._turn_start_index(turn_key)
            if start is None:
                raise ChatError("Message introuvable.")
            # Garder la variante affichée, suite comprise, avant de basculer
            self._persist_version(branch, start)
            version = branch["versions"][target_version]
            branch["current"] = target_version
            history = self._history[:start]
            history.append({
                "text": version.get("user", ""), "is_user": True,
                "timestamp": version.get("timestamp") or datetime.now(), "type": "text",
                "attachments": list(version.get("attachments") or []),
                "image_path": version.get("image_path"),
                "mid": turn_key,
            })
            if version.get("ai") is not None:
                history.append({
                    "text": version["ai"], "is_user": False,
                    "timestamp": datetime.now(), "type": "text",
                    "mid": version.get("ai_mid") or uuid4().hex,
                })
            history.extend(dict(message) for message in version.get("tail") or [])
            self._history = history
            self._rewind_engine_history()
            self._emit("conversation.loaded", {
                "reason": "navigated", "snapshot": self.snapshot(),
            })
            self._save_current()

    def _rewind_engine_history(self) -> None:
        """Réaligne l'historique du modèle sur la conversation affichée (Tk)."""
        llm = self._llm()
        if llm is None:
            return
        try:
            if hasattr(llm, "clear_history"):
                llm.clear_history()
            if hasattr(llm, "add_to_history"):
                for message in self._history:
                    text = message.get("text", "")
                    # Comme le rendu de Tk avant ce réalignement : sans les
                    # entrées vides ni les générations de fichier inachevées
                    if not text or message.get("type") == "file_generation_placeholder":
                        continue
                    role = "user" if message.get("is_user") else "assistant"
                    llm.add_to_history(role, text)
        except Exception as exc:  # pylint: disable=broad-except
            logger.warning("Réalignement de l'historique du modèle échoué : %s", exc)

    # ── Remise à zéro et sessions ───────────────────────────────────────────

    def _reset_engine_memory(self) -> None:
        """Vide la mémoire du moteur comme clear_chat (Ctrl+L) dans Tk."""
        engine = self._engine
        if hasattr(engine, "clear_conversation"):
            engine.clear_conversation()
        custom_ai = self._local_ai()
        if custom_ai is not None:
            local_llm = getattr(custom_ai, "local_llm", None)
            if local_llm is not None and hasattr(local_llm, "clear_history"):
                local_llm.clear_history()
            memory = getattr(custom_ai, "conversation_memory", None)
            if memory is not None and hasattr(memory, "clear"):
                memory.clear()
            if getattr(custom_ai, "ultra_mode", False):
                storage = getattr(custom_ai, "documents_storage", None)
                if storage is not None and hasattr(storage, "clear"):
                    storage.clear()
                manager = getattr(custom_ai, "context_manager", None)
                if manager is not None:
                    if hasattr(manager, "clear_context"):
                        manager.clear_context()
                    elif hasattr(manager, "clear"):
                        manager.clear()
                    elif hasattr(manager, "documents"):
                        manager.documents.clear()
                if hasattr(custom_ai, "context_stats"):
                    custom_ai.context_stats = {
                        "documents_processed": 0,
                        "total_tokens": 0,
                        "chunks_created": 0,
                    }
            if hasattr(custom_ai, "session_context"):
                custom_ai.session_context = {
                    "documents_processed": [],
                    "code_files_processed": [],
                    "last_document_type": None,
                    "current_document": None,
                }
            vector_memory = getattr(custom_ai, "vector_memory", None)
            if vector_memory is not None and hasattr(vector_memory, "clear_all"):
                vector_memory.clear_all()

    def _clear_state(self) -> None:
        """Conversation vide, sans pièce jointe (verrou tenu)."""
        self._history = []
        self._branches = {}
        for attachment in self._attachments:
            if attachment.cancel is not None:
                attachment.cancel.set()
        self._attachments = []
        self._introduced = set()

    def new_conversation(self, reason: str = "new") -> None:
        """Nouvelle conversation (Ctrl+N, Ctrl+L) ; la session courante reste enregistrée.

        Raises:
            ChatError: réponse en cours
        """
        with self._exclusive():
            self._save_current()
            self._reset_engine_memory()
            self._clear_state()
            self._set_session(None, None)
            self._emit("conversation.loaded", {"reason": reason, "snapshot": self.snapshot()})

    def clear(self) -> None:
        """Ctrl+L : mémoire du moteur vidée, nouvelle conversation."""
        self.new_conversation(reason="cleared")

    def _set_session(self, session_id: Optional[str], name: Optional[str]) -> None:
        """Change de session courante (verrou tenu)."""
        self._session_id = session_id
        self._session_name = name
        sessions = self._sessions()
        if sessions is not None:
            try:
                if session_id:
                    sessions.set_current_workspace(session_id)
                elif hasattr(sessions, "clear_current_workspace"):
                    sessions.clear_current_workspace()
            except Exception as exc:  # pylint: disable=broad-except
                logger.warning("Session courante non changée : %s", exc)
        if self._on_session_change is not None:
            try:
                self._on_session_change(session_id)
            except Exception:  # pylint: disable=broad-except
                pass

    def _create_session(self, first_message: str) -> None:
        """Crée la session d'une nouvelle conversation, nommée d'après son début."""
        sessions = self._sessions()
        if sessions is None:
            return
        name = session_name_for(first_message)
        try:
            session_id = sessions.create_workspace(name)
        except ValueError:
            name = "Conversation"
            session_id = sessions.create_workspace(name)
        except Exception as exc:  # pylint: disable=broad-except
            logger.warning("Session non créée : %s", exc)
            return
        self._set_session(session_id, name)
        self._emit("sessions.changed")

    def _save_current(self) -> bool:
        """Enregistre la conversation dans sa session (sauvegarde automatique)."""
        with self._lock:
            session_id = self._session_id
            sessions = self._sessions()
            if not session_id or sessions is None:
                return False
            history = [dict(message) for message in self._history]
            branches = self._branches
            try:
                # Garder les clés déjà stockées (dossiers projet, réglages…) :
                # save_workspace réécrit l'état complet
                state = sessions.load_workspace(session_id) or {}
                state["conversation_history"] = history
                state["turn_branches"] = branches
                saved = sessions.save_workspace(session_id, state)
            except Exception as exc:  # pylint: disable=broad-except
                logger.warning("Session %s non enregistrée : %s", session_id, exc)
                return False
            if saved:
                self._emit("sessions.changed")
            return bool(saved)

    def save_session(self) -> bool:
        """Ctrl+S : enregistre la session courante."""
        saved = self._save_current()
        if saved:
            self._notify("success", "💾 Session sauvegardée")
        return saved

    def list_sessions(self) -> List[Dict[str, Any]]:
        """Sessions enregistrées, la plus récente d'abord."""
        sessions = self._sessions()
        if sessions is None:
            return []
        current = self.session_id
        items = []
        for workspace in sessions.list_workspaces():
            items.append({
                "id": workspace.get("id"),
                "name": workspace.get("name") or workspace.get("id"),
                "last_modified": workspace.get("last_modified"),
                "message_count": workspace.get("message_count", 0),
                "current": workspace.get("id") == current,
            })
        items.sort(key=lambda item: item.get("last_modified") or "", reverse=True)
        return items

    def load_session(self, session_id: str, reason: str = "loaded") -> None:
        """Ouvre une session : la conversation actuelle reste enregistrée.

        L'historique du modèle est reconstruit depuis la session (D3) : Tk ne le
        faisait que s'il y avait des variantes d'édition.

        Raises:
            ChatError: réponse en cours, session introuvable
        """
        sessions = self._sessions()
        if sessions is None:
            raise ChatError("Sessions indisponibles.")
        with self._exclusive():
            state = sessions.load_workspace(session_id)
            if state is None:
                raise ChatError("❌ Session introuvable")
            self._save_current()
            manager = getattr(self._engine, "conversation_manager", None)
            if manager is not None and hasattr(manager, "clear"):
                manager.clear()
            self._reset_engine_memory()
            self._clear_state()

            raw_history = state.get("conversation_history", state.get("history", [])) or []
            history = []
            for message in raw_history:
                if not isinstance(message, dict):
                    continue
                content = message.get("text", message.get("content", ""))
                if not content:
                    continue  # comme Tk au chargement : sans les entrées vides
                entry = dict(message)
                entry["text"] = content
                entry["is_user"] = message.get("is_user", message.get("role", "user") == "user")
                # Identifiant stable : les variantes d'édition y sont rattachées
                entry["mid"] = message.get("mid") or uuid4().hex
                entry.setdefault("timestamp", datetime.now())
                history.append(entry)
            self._history = history
            self._branches = state.get("turn_branches") or {}
            name = (state.get("metadata") or {}).get("name", session_id)
            self._set_session(session_id, name)
            self._rewind_engine_history()
            self._emit("conversation.loaded", {"reason": reason, "snapshot": self.snapshot()})

    def delete_session(self, session_id: str) -> bool:
        """Supprime une session ; la session courante laisse place à une conversation vide."""
        sessions = self._sessions()
        if sessions is None:
            return False
        if session_id == self.session_id:
            self.new_conversation()
        deleted = sessions.delete_workspace(session_id)
        if deleted:
            self._emit("sessions.changed")
        return bool(deleted)

    # ── Chat mobile (RelayBridge) ───────────────────────────────────────────

    def attach_bridge(self, bridge) -> None:
        """Traite les messages du mobile, fenêtre ouverte ou non.

        Le Relay dépose chaque message dans le bridge (send_to_gui) : il est mis
        en file comme un message du desktop. La réponse repart par le bridge,
        avec l'identifiant du message mobile (submit_ai_chunk / response).
        """
        if self._bridge is bridge:
            return
        self.detach_bridge()
        self._bridge = bridge
        bridge.on_gui_message(self._on_relay_message)
        self._bridge_watch = threading.Thread(
            target=self._watch_relay_interrupts, name="relay-interrupts", daemon=True
        )
        self._bridge_watch.start()

    def detach_bridge(self) -> None:
        """Ne traite plus les messages du mobile."""
        bridge, self._bridge = self._bridge, None
        if bridge is not None:
            try:
                bridge.remove_gui_callback(self._on_relay_message)
            except Exception:  # pylint: disable=broad-except
                pass

    def _bridge_active(self) -> bool:
        bridge = self._bridge
        return bridge is not None and bool(getattr(bridge, "active", False))

    def _on_relay_message(self, relay_msg) -> None:
        """Message du mobile (fil du Relay) : mis en file, rien de bloquant ici."""
        bridge = self._bridge
        if bridge is not None:
            try:
                bridge.poll_gui_messages()  # file de l'ancienne interface, jamais lue
            except Exception:  # pylint: disable=broad-except
                pass
        if not getattr(relay_msg, "is_user", False):
            return
        text = relay_msg.text or ""
        image_path = getattr(relay_msg, "image_path", None)
        file_paths = [fp for fp in (getattr(relay_msg, "file_paths", None) or []) if fp]
        attachments: List[Tuple[str, str]] = []
        if image_path:
            attachments.append((image_path, "Image"))
        for path in file_paths:
            attachments.append((path, file_type_for(path) or "Code"))
        # Un fichier sans texte : une demande par défaut pour l'IA
        ai_text = text
        if not ai_text.strip():
            if image_path:
                ai_text = "Décris cette image en détail."
            elif file_paths:
                ai_text = "Analyse ce fichier et résume-le."
        request = _Request(
            id=uuid4().hex,
            source="mobile",
            text=ai_text,
            bubble=bubble_text(text, attachments),
            attachments=attachments,
            image_path=image_path,
            history_query=text,
            relay_message_id=getattr(relay_msg, "message_id", None),
            relay_files=file_paths,
        )
        with self._cond:
            if self._closed:
                return
            self._enqueue(request)

    def _prepare_relay_attachments(self, request: _Request) -> None:
        """Pièces jointes du mobile lues avant la réponse (_process_relay_attachments_then_ai)."""
        for path in request.relay_files:
            if not os.path.isfile(path):
                continue
            ok, error = self._load_document(path, os.path.basename(path))
            if not ok:
                logger.warning("Pièce jointe du mobile illisible (%s) : %s", path, error)
        if request.image_path and os.path.isfile(request.image_path):
            try:
                request.image_b64 = encode_image(request.image_path)[0]
            except Exception as exc:  # pylint: disable=broad-except
                logger.warning("Image du mobile illisible (%s) : %s", request.image_path, exc)

    def _relay_submit_response(self, request: _Request, text: str) -> None:
        if request.source != "mobile" or not self._bridge_active():
            return
        try:
            self._bridge.submit_ai_response(text, message_id=request.relay_message_id)
        except Exception as exc:  # pylint: disable=broad-except
            logger.warning("Envoi de la réponse au mobile échoué : %s", exc)

    def _watch_relay_interrupts(self) -> None:
        """Bouton Stop du chat mobile : sondé comme le faisait la boucle Tk."""
        while not self._closed:
            bridge = self._bridge
            if bridge is None:
                return
            try:
                if bridge.consume_interrupt_request():
                    self._stop_from_mobile()
            except Exception:  # pylint: disable=broad-except
                pass
            time.sleep(0.15)

    def _stop_from_mobile(self) -> None:
        """Stop du mobile : sa réponse en cours, sinon ses messages en attente.

        Le Relay ne dit pas quel message arrêter : le message mobile en cours
        s'arrête ; à défaut, les messages mobiles en file sont retirés ; à
        défaut encore, la réponse en cours s'arrête (comme dans Tk).
        """
        with self._cond:
            active = self._active
            if active is not None and active.source == "mobile":
                self._interrupted = True
                self._resolve_confirm(False)
                return
            queued = [request for request in self._queue if request.source == "mobile"]
        if queued:
            for request in queued:
                self.cancel(request.id)
            return
        self.stop()
