"""
Protocole d'événements entre le serveur desktop et la fenêtre

Chaque événement envoyé à la fenêtre porte :
  - type            : nom de l'événement (« assistant.token »…)
  - conversation_id : session concernée (None hors conversation)
  - message_id      : message concerné (None si sans objet)
  - seq             : numéro d'ordre, croissant sur toute la vie du serveur
  - payload         : charge utile, décrite ci-dessous par un modèle Pydantic

Le miroir TypeScript est frontend/src/lib/events.ts : les deux fichiers
évoluent ensemble.

Les événements du chat (CHAT_EVENT_TYPES) modifient l'état renvoyé par
GET /api/conversation, qui porte le seq du dernier d'entre eux. Une fenêtre
qui se reconnecte reprend le flux là où elle l'avait laissé (EventBus garde
les derniers événements), ou relit cet état complet s'il est trop ancien.

Les modèles servent de référence et aux tests : le bus ne les valide pas à la
volée, il publie un événement par jeton de réponse.
"""

import threading
from collections import deque
from typing import Any, Callable, Dict, List, Literal, Optional, Tuple, Type, Union

from pydantic import BaseModel, ConfigDict, Field


class _Payload(BaseModel):
    """Charge utile d'un événement : aucun champ inattendu."""

    model_config = ConfigDict(extra="forbid")


# ── Application ─────────────────────────────────────────────────────────────


class EngineStatus(_Payload):
    """Étapes du lancement, puis moteur prêt ou en échec."""

    state: Literal["starting", "onboarding", "ready", "error"]
    step: str = ""  # identifiant de l'étape en cours (ollama, placement…)
    label: str = ""  # libellé affiché par l'écran de chargement
    detail: str = ""  # sous-étape : lignes du calibrage du placement
    error: Optional[str] = None
    ollama: bool = True  # Ollama répond
    placement: Optional[str] = None  # où tourne le modèle, en clair


class Notification(_Payload):
    """Notification brève (équivalent de show_notification dans Tk)."""

    level: Literal["info", "success", "warning", "error"]
    message: str


class RelayStatus(_Payload):
    """État du Relay mobile."""

    running: bool
    port: Optional[int] = None
    clients: int = 0
    tunnels: Dict[str, str] = Field(default_factory=dict)
    url: Optional[str] = None  # page de routage (QR code), None sans tunnel
    local_url: Optional[str] = None  # adresse sur ce PC, clé de chiffrement comprise
    token: Optional[str] = None  # jeton d'accès, affiché dans le panneau


class SchedulerResult(_Payload):
    """Fin d'une tâche planifiée."""

    task_id: Optional[str] = None
    name: str = ""
    status: str = ""
    status_text: str = ""
    summary: str = ""
    output_file: Optional[str] = None
    finished_at: Optional[str] = None
    os_toast_shown: bool = False


class SchedulerChanged(_Payload):
    """La liste des tâches planifiées a changé : la fenêtre la relit."""


class ResourceMetrics(BaseModel):
    """Mesure du moniteur de ressources (ResourceMonitor de Tk), Ollama seul pour CPU et RAM."""

    model_config = ConfigDict(extra="allow")

    cpu_percent: float = 0.0
    ram_used_mb: float = 0.0
    ram_total_mb: float = 0.0
    ram_percent: float = 0.0
    gpu_available: bool = False
    gpu_percent: float = 0.0
    gpu_mem_used_mb: float = 0.0
    gpu_mem_total_mb: float = 0.0
    inference_ms: float = 0.0  # durée du dernier agent
    tokens_per_sec: float = 0.0  # tokens/s du dernier agent


class ResourcesSample(_Payload):
    """Mesure du moniteur (toutes les 3 s, et à la fin de chaque agent)."""

    metrics: ResourceMetrics
    inferences: int = 0  # fins d'agents relevées : un point de plus aux tokens/s


class SessionsChanged(_Payload):
    """La liste des sessions a changé : la fenêtre la relit."""


class FilesDropped(_Payload):
    """Fichiers déposés sur la fenêtre, avec leur vrai chemin (pywebview).

    La page sait où ils ont été déposés : elle décide quoi en faire.
    """

    paths: List[str]


class FoldersProgress(_Payload):
    """Indexation d'un dossier projet en cours (_index_folder_async)."""

    path: str
    name: str
    verb: str  # « Indexation », « Ré-indexation »
    done: int = 0
    total: int = 0


class FoldersChanged(_Payload):
    """Dossiers projet de la session changés (indexé, détaché, échec)."""

    path: Optional[str] = None
    ok: bool = True


class ModelsProgress(_Payload):
    """Téléchargement d'un modèle : avancée de la couche en cours (Ollama)."""

    fraction: float
    status: str = ""


class ModelsLog(_Payload):
    """Ligne du journal d'un téléchargement ou d'une création de modèle."""

    line: str


class ModelsDone(_Payload):
    """Fin d'un travail sur les modèles : pull, apply (Réglages) ou install (assistant)."""

    action: Literal["pull", "apply", "install"]
    name: str
    ok: bool
    message: str = ""


class VoiceInputState(_Payload):
    """Saisie vocale : idle, recording, transcribing, error."""

    state: Literal["idle", "recording", "transcribing", "error"]
    message: str = ""


class VoiceTranscript(_Payload):
    """Texte dicté, à insérer au curseur de la zone de saisie."""

    text: str


class VoiceOutputState(_Payload):
    """Lecture vocale : speaking, idle, error ; key désigne ce qui est lu."""

    state: Literal["speaking", "idle", "error"]
    key: Optional[str] = None
    message: str = ""


# ── Chat ────────────────────────────────────────────────────────────────────


class ConversationLoaded(_Payload):
    """Conversation remplacée d'un bloc : nouvelle, rechargée, éditée…"""

    reason: Literal["new", "cleared", "loaded", "restored", "edited", "navigated"]
    snapshot: Dict[str, Any]


class QueueItem(BaseModel):
    """Message en attente dans la file commune desktop / mobile."""

    request_id: str
    source: Literal["desktop", "mobile"]
    text: str


class QueueUpdated(_Payload):
    """Contenu de la file d'attente."""

    items: List[QueueItem]


class AttachmentRef(BaseModel):
    """Pièce jointe d'un message."""

    path: str
    name: str
    type: str


class MessageUser(_Payload):
    """Message de l'utilisateur, au moment où il est traité."""

    mid: str
    request_id: str
    text: str
    source: Literal["desktop", "mobile"]
    timestamp: str
    attachments: List[AttachmentRef] = Field(default_factory=list)
    image_path: Optional[str] = None


class AssistantStart(_Payload):
    """Début de la réponse : chat, génération de fichier ou d'image."""

    mid: str
    request_id: str
    kind: Literal["chat", "file", "image"]
    reasoning: bool = False  # bloc « Réflexion » attendu
    filename: Optional[str] = None  # génération de fichier


class AssistantToken(_Payload):
    """Fragment de texte de la réponse."""

    text: str


class AssistantSync(_Payload):
    """Texte complet de la réponse, après normalisation des sauts de ligne
    autour d'un appel d'outil (aucun texte visible n'est retiré)."""

    text: str


class AssistantThinking(_Payload):
    """Fragment de la réflexion (mode thinking)."""

    text: str


class AssistantThinkingDone(_Payload):
    """Fin d'une passe de réflexion."""

    duration_ms: int


class PathLink(BaseModel):
    """Chemin existant cité dans une réponse, rendu cliquable (Explorateur)."""

    text: str  # tel qu'il apparaît dans la réponse
    path: str  # chemin absolu normalisé


class AssistantDone(_Payload):
    """Réponse terminée."""

    mid: str
    text: str
    duration_ms: int
    tokens_per_s: Optional[float] = None
    paths: List[PathLink] = Field(default_factory=list)


class AssistantInterrupted(_Payload):
    """Réponse arrêtée (Stop, Échap, Stop du mobile)."""

    mid: Optional[str] = None
    text: str = ""
    paths: List[PathLink] = Field(default_factory=list)


class MessageRated(_Payload):
    """Réponse notée de 1 à 5 étoiles (RLHF)."""

    mid: str
    rating: int


class AssistantError(_Payload):
    """Réponse en échec."""

    mid: Optional[str] = None
    message: str


class ToolCall(_Payload):
    """Appel d'outil MCP ; « synthesis » annonce la rédaction de la réponse."""

    name: str
    label: str
    args: Dict[str, Any] = Field(default_factory=dict)
    at: int = 0  # longueur du texte de la réponse au moment de l'appel


class ToolResult(_Payload):
    """Résultat d'un appel d'outil, résumé."""

    name: str
    ok: bool
    summary: str = ""
    sources: int = 0  # recherche web : nombre de sources trouvées


class ConfirmRequest(_Payload):
    """Confirmation demandée à l'utilisateur (suppression d'un fichier)."""

    confirm_id: str
    kind: Literal["delete_file"]
    path: str
    name: str


class ConfirmClosed(_Payload):
    """Confirmation répondue (ou abandonnée)."""

    confirm_id: str
    accepted: bool


class DocumentCreated(_Payload):
    """Document produit par un outil (generate_document, edit_document)."""

    path: str
    name: str


class FileCreated(_Payload):
    """Fichier produit par la génération de fichier (« génère un fichier… »)."""

    path: str
    name: str


class ImageProgress(_Payload):
    """Progression de la génération d'image (installation comprise)."""

    message: str
    fraction: Optional[float] = None


class ImageCreated(_Payload):
    """Image générée."""

    path: str
    name: str


class AttachmentAdded(_Payload):
    """Pièce jointe ajoutée à la zone de saisie."""

    id: str
    path: str
    name: str
    type: str
    status: Literal["loading", "ready"]


class AttachmentReady(_Payload):
    """Lecture d'une pièce jointe terminée."""

    id: str


class AttachmentFailed(_Payload):
    """Lecture d'une pièce jointe en échec."""

    id: str
    message: str


class AttachmentRemoved(_Payload):
    """Pièce jointe retirée (✕ ou envoi du message)."""

    id: str


class AgentEvent(BaseModel):
    """Événement de la page Agents, repris tel quel d'AgentRelayService (type inconnu ici)."""

    model_config = ConfigDict(extra="allow")


# ── Page Agents (agents.py) ─────────────────────────────────────────────────
# Ceux d'AgentRelayService gardent son nom et sa charge utile (sans « type ») ;
# le texte cumulé d'une section devient sa suite (agent_section_delta) ou son
# texte entier (agent_section_text). section_id et node_id : identifiant du
# nœud du canvas (entier), ou « deb_N » pour un tour de débat.


class AgentsRunCreated(_Payload):
    """Nouveau fil d'exécution (vue complète, comme GET /api/agents/runs/{id})."""

    run: Dict[str, Any]


class AgentsExecStart(_Payload):
    """L'exécuteur démarre : mode du plan (single, sequential, parallel, dag, debate)."""

    exec_id: str
    mode: str


class AgentsDebateTopic(_Payload):
    """Sujet d'un débat."""

    exec_id: str
    topic: str


class AgentsSectionStart(_Payload):
    """Un agent commence : sa section dans le fil."""

    exec_id: str
    section_id: Union[int, str]
    title: str
    color: str


class AgentsSectionDelta(_Payload):
    """Suite du texte d'une section ; offset : longueur du texte avant cette suite."""

    exec_id: str
    section_id: Union[int, str]
    text: str
    offset: int


class AgentsSectionText(_Payload):
    """Texte entier d'une section, quand il ne prolonge pas le précédent."""

    exec_id: str
    section_id: Union[int, str]
    text: str


class AgentsSectionEnd(_Payload):
    """Un agent a fini : durée et tokens/s (relevé de fin de flux d'Ollama, D17)."""

    exec_id: str
    section_id: Union[int, str]
    success: bool
    inference_ms: Optional[int] = None
    tokens_per_sec: Optional[float] = None


class AgentsNodeStatus(_Payload):
    """Statut d'un nœud du canvas (couleurs de WorkflowCanvas.STATUS_META)."""

    exec_id: str
    node_id: Union[int, str]
    status: Literal["idle", "running", "done", "error"]


class AgentsExecEnd(_Payload):
    """Fin de l'exécution."""

    exec_id: str
    success: bool
    interrupted: bool
    status_text: str


class AgentsExecError(_Payload):
    """Exécution en échec (ou refusée : une autre est en cours)."""

    exec_id: str
    message: str


class AgentsRunsChanged(_Payload):
    """La liste des fils a changé : la fenêtre la relit."""


class AgentsListChanged(_Payload):
    """Les agents personnalisés ont changé : la fenêtre relit la liste."""


AGENT_EVENT_PAYLOADS: Dict[str, Type[BaseModel]] = {
    "agents.run_created": AgentsRunCreated,
    "agents.agent_exec_start": AgentsExecStart,
    "agents.agent_debate_topic": AgentsDebateTopic,
    "agents.agent_section_start": AgentsSectionStart,
    "agents.agent_section_delta": AgentsSectionDelta,
    "agents.agent_section_text": AgentsSectionText,
    "agents.agent_section_end": AgentsSectionEnd,
    "agents.agent_node_status": AgentsNodeStatus,
    "agents.agent_exec_end": AgentsExecEnd,
    "agents.agent_exec_error": AgentsExecError,
    "agents.runs_changed": AgentsRunsChanged,
    "agents.list_changed": AgentsListChanged,
}


# Type d'événement → modèle de sa charge utile
EVENT_PAYLOADS: Dict[str, Type[BaseModel]] = {
    "engine.status": EngineStatus,
    "notification": Notification,
    "relay.status": RelayStatus,
    "scheduler.result": SchedulerResult,
    "scheduler.changed": SchedulerChanged,
    "resources.sample": ResourcesSample,
    "sessions.changed": SessionsChanged,
    "files.dropped": FilesDropped,
    "folders.progress": FoldersProgress,
    "folders.changed": FoldersChanged,
    "models.progress": ModelsProgress,
    "models.log": ModelsLog,
    "models.done": ModelsDone,
    "voice.input": VoiceInputState,
    "voice.transcript": VoiceTranscript,
    "voice.output": VoiceOutputState,
    "conversation.loaded": ConversationLoaded,
    "queue.updated": QueueUpdated,
    "message.user": MessageUser,
    "message.rated": MessageRated,
    "assistant.start": AssistantStart,
    "assistant.token": AssistantToken,
    "assistant.sync": AssistantSync,
    "assistant.thinking": AssistantThinking,
    "assistant.thinking_done": AssistantThinkingDone,
    "assistant.done": AssistantDone,
    "assistant.interrupted": AssistantInterrupted,
    "assistant.error": AssistantError,
    "tool.call": ToolCall,
    "tool.result": ToolResult,
    "confirm.request": ConfirmRequest,
    "confirm.closed": ConfirmClosed,
    "document.created": DocumentCreated,
    "file.created": FileCreated,
    "image.progress": ImageProgress,
    "image.created": ImageCreated,
    "attachment.added": AttachmentAdded,
    "attachment.ready": AttachmentReady,
    "attachment.failed": AttachmentFailed,
    "attachment.removed": AttachmentRemoved,
}

# Événements de la page Agents : préfixe « agents. » + type d'AgentRelayService
AGENTS_PREFIX = "agents."

# Événements qui modifient l'état du chat (GET /api/conversation)
CHAT_EVENT_TYPES = frozenset(
    name for name in EVENT_PAYLOADS
    if name.split(".")[0] in (
        "conversation", "queue", "message", "assistant", "tool", "confirm",
        "document", "file", "image", "attachment",
    )
)


def payload_model(event_type: str) -> Optional[Type[BaseModel]]:
    """Modèle de la charge utile d'un type d'événement (None s'il est inconnu)."""
    if event_type.startswith(AGENTS_PREFIX):
        return AGENT_EVENT_PAYLOADS.get(event_type, AgentEvent)
    return EVENT_PAYLOADS.get(event_type)


def validate_event(event: Dict[str, Any]) -> None:
    """Vérifie un événement publié (tests) ; ValueError s'il est invalide."""
    for key in ("type", "conversation_id", "message_id", "seq", "payload"):
        if key not in event:
            raise ValueError(f"Champ manquant : {key}")
    model = payload_model(event["type"])
    if model is None:
        raise ValueError(f"Type d'événement inconnu : {event['type']}")
    model.model_validate(event["payload"])


# ── Messages de la fenêtre vers le serveur ──────────────────────────────────


class _ClientMessage(BaseModel):
    """Message envoyé par la fenêtre sur le WebSocket."""

    model_config = ConfigDict(extra="forbid")

    id: Optional[str] = None  # repris dans la réponse (« reply ») du serveur


class ChatSend(_ClientMessage):
    """Envoi d'un message, ou nouvelle version d'un tour existant."""

    type: Literal["chat.send"]
    text: str = ""
    attachment_ids: Optional[List[str]] = None  # None : toutes les pièces jointes en attente
    edit_mid: Optional[str] = None  # tour modifié (mid du message de l'utilisateur)
    regenerate: bool = False  # nouvelle variante du même texte


class ChatStop(_ClientMessage):
    """Arrêt de la réponse en cours (bouton Stop, Échap)."""

    type: Literal["chat.stop"]


class ChatCancel(_ClientMessage):
    """Retrait d'un message encore en file d'attente."""

    type: Literal["chat.cancel"]
    request_id: str


class ConfirmResponse(_ClientMessage):
    """Réponse à une demande de confirmation."""

    type: Literal["confirm.response"]
    confirm_id: str
    accepted: bool


class Ping(_ClientMessage):
    """Maintien de la connexion."""

    type: Literal["ping"]


CLIENT_MESSAGES: Dict[str, Type[_ClientMessage]] = {
    "chat.send": ChatSend,
    "chat.stop": ChatStop,
    "chat.cancel": ChatCancel,
    "confirm.response": ConfirmResponse,
    "ping": Ping,
}


def parse_client_message(data: Any) -> _ClientMessage:
    """Valide un message de la fenêtre ; ValueError s'il est invalide."""
    if not isinstance(data, dict):
        raise ValueError("Message attendu : un objet JSON")
    model = CLIENT_MESSAGES.get(str(data.get("type", "")))
    if model is None:
        raise ValueError(f"Type de message inconnu : {data.get('type')!r}")
    return model.model_validate(data)


# ── Bus d'événements ────────────────────────────────────────────────────────


class EventBus:
    """Diffuse les événements aux fenêtres connectées, dans l'ordre.

    publish() est appelé depuis n'importe quel fil (moteur, Relay, scheduler) :
    le numéro d'ordre et la remise aux abonnés se font sous le même verrou,
    donc chaque abonné reçoit les événements dans l'ordre de leur seq. Un
    abonné ne doit jamais bloquer : il dépose l'événement dans sa file (cf.
    server.py, call_soon_threadsafe).
    """

    def __init__(self, history: int = 5000):
        self._lock = threading.Lock()
        self._seq = 0
        self._recent: deque = deque(maxlen=history)
        self._subscribers: List[Callable[[Dict[str, Any]], None]] = []

    @property
    def last_seq(self) -> int:
        """Numéro du dernier événement publié."""
        with self._lock:
            return self._seq

    def publish(
        self,
        event_type: str,
        payload: Optional[Dict[str, Any]] = None,
        conversation_id: Optional[str] = None,
        message_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Numérote l'événement, le garde et le remet aux abonnés."""
        with self._lock:
            self._seq += 1
            event = {
                "type": event_type,
                "conversation_id": conversation_id,
                "message_id": message_id,
                "seq": self._seq,
                "payload": payload or {},
            }
            self._recent.append(event)
            for deliver in list(self._subscribers):
                try:
                    deliver(event)
                except Exception:  # pylint: disable=broad-except
                    pass  # fenêtre fermée : son désabonnement suit
        return event

    def subscribe(
        self, deliver: Callable[[Dict[str, Any]], None], since: Optional[int] = None
    ) -> Tuple[Callable[[], None], bool]:
        """Abonne une fenêtre ; rejoue d'abord ce qu'elle a manqué depuis `since`.

        Returns:
            (désabonnement, reprise) : reprise vaut False si des événements
            manqués ne sont plus gardés, la fenêtre doit alors relire l'état
            complet. Sans `since`, rien n'est rejoué et reprise vaut True.
        """
        with self._lock:
            resumed = True
            if since is not None and since < self._seq:
                oldest = self._recent[0]["seq"] if self._recent else self._seq + 1
                resumed = oldest <= since + 1
                if resumed:
                    for event in self._recent:
                        if event["seq"] > since:
                            deliver(event)
            self._subscribers.append(deliver)

        def unsubscribe() -> None:
            with self._lock:
                if deliver in self._subscribers:
                    self._subscribers.remove(deliver)

        return unsubscribe, resumed

    @property
    def subscriber_count(self) -> int:
        """Nombre de fenêtres abonnées."""
        with self._lock:
            return len(self._subscribers)
