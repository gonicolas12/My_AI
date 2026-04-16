"""
Relay Bridge - Pont de communication entre le serveur Relay et le GUI desktop.

Fournit un système d'événements thread-safe pour synchroniser les messages
entre l'interface mobile (via WebSocket) et l'interface Tkinter locale.
"""

import asyncio
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Tuple

from utils.logger import setup_logger

logger = setup_logger("RelayBridge")

# Durée de conservation d'une réponse IA en attente côté bridge, avant GC.
# 10 minutes laissent largement le temps à un mobile mis en veille de revenir
# récupérer sa réponse sans perdre le contenu.
_PENDING_RESPONSE_TTL = 600.0
# Nombre max de réponses conservées en cache (protection mémoire).
_PENDING_RESPONSE_MAX = 50


@dataclass
class RelayMessage:
    """Un message transitant par le Relay."""

    text: str
    is_user: bool
    timestamp: datetime = field(default_factory=datetime.now)
    source: str = "relay"  # "relay" (mobile) ou "local" (desktop)
    message_id: str = ""
    # Pièces jointes envoyées depuis le mobile :
    # - image_path : chemin local vers l'image (traitée via le modèle vision)
    # - file_paths : chemins locaux vers les fichiers (pdf, docx, xlsx, code, ...)
    image_path: Optional[str] = None
    file_paths: List[str] = field(default_factory=list)

    def __post_init__(self):
        if not self.message_id:
            self.message_id = f"{self.source}_{int(self.timestamp.timestamp() * 1000)}"

    def to_dict(self) -> Dict[str, Any]:
        """Convertit le message en dict pour sérialisation JSON."""
        return {
            "text": self.text,
            "is_user": self.is_user,
            "timestamp": self.timestamp.isoformat(),
            "source": self.source,
            "message_id": self.message_id,
            "image_path": self.image_path,
            "file_paths": list(self.file_paths),
        }


class RelayBridge:
    """
    Pont bidirectionnel entre le serveur Relay (mobile) et le GUI (desktop).

    Le bridge maintient une file de messages et des callbacks pour notifier
    les deux côtés (GUI et WebSocket) quand de nouveaux messages arrivent.
    """

    _instance: Optional["RelayBridge"] = None
    _lock = threading.Lock()

    def __new__(cls):
        """Singleton thread-safe."""
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self):
        if getattr(self, '_initialized', False):
            return
        self._initialized = True

        # Files de messages pour chaque direction
        self._gui_queue: deque[RelayMessage] = deque(maxlen=500)
        self._ws_queue: deque[RelayMessage] = deque(maxlen=500)

        # Historique complet de la session relay
        self._history: List[RelayMessage] = []

        # Callbacks enregistrés
        self._gui_callbacks: List[Callable[[RelayMessage], None]] = []
        self._ws_callbacks: List[Callable[[RelayMessage], None]] = []

        # État
        self._active = False
        self._connected_clients = 0

        # Mécanisme de réponse : le GUI traite le message en streaming
        # et soumet la réponse finale via submit_ai_response().
        # Le WebSocket attend via wait_for_ai_response().
        self._response_event = threading.Event()
        self._latest_response = ""
        self._latest_message_id: str = ""

        # Réponses IA prêtes mais pas encore consommées par un WS vivant.
        # Clé : message_id de la question utilisateur.
        # Valeur : (texte_réponse, timestamp). Permet à un mobile déconnecté
        # de récupérer sa réponse après reconnexion.
        self._pending_responses: Dict[str, Tuple[str, float]] = {}
        self._pending_lock = threading.Lock()

        # Callbacks déclenchés dès qu'une réponse est soumise (broadcast WS).
        self._response_callbacks: List[Callable[[str, str], None]] = []

        logger.info("RelayBridge initialisé (singleton)")

    # ------------------------------------------------------------------
    # Propriétés
    # ------------------------------------------------------------------

    @property
    def active(self) -> bool:
        """Indique si le Relay est actif (au moins un client connecté)."""
        return self._active

    @active.setter
    def active(self, value: bool):
        self._active = value

    @property
    def connected_clients(self) -> int:
        """Nombre de clients mobiles actuellement connectés."""
        return self._connected_clients

    @connected_clients.setter
    def connected_clients(self, value: int):
        self._connected_clients = max(0, value)

    @property
    def history(self) -> List[Dict[str, Any]]:
        """Retourne l'historique complet de la session relay sous forme de liste de dicts."""
        return [msg.to_dict() for msg in self._history]

    # ------------------------------------------------------------------
    # Enregistrement de callbacks
    # ------------------------------------------------------------------

    def on_gui_message(self, callback: Callable[[RelayMessage], None]):
        """Enregistre un callback appelé quand un message doit s'afficher dans le GUI."""
        self._gui_callbacks.append(callback)

    def on_ws_message(self, callback: Callable[[RelayMessage], None]):
        """Enregistre un callback appelé quand un message doit être envoyé au WebSocket."""
        self._ws_callbacks.append(callback)

    def remove_gui_callback(self, callback: Callable):
        """Supprime un callback GUI enregistré."""
        self._gui_callbacks = [cb for cb in self._gui_callbacks if cb != callback]

    def remove_ws_callback(self, callback: Callable):
        """Supprime un callback WebSocket enregistré."""
        self._ws_callbacks = [cb for cb in self._ws_callbacks if cb != callback]

    # ------------------------------------------------------------------
    # Envoi de messages
    # ------------------------------------------------------------------

    def send_to_gui(self, message: RelayMessage):
        """Envoie un message au GUI desktop (depuis le mobile)."""
        self._history.append(message)
        self._gui_queue.append(message)
        for cb in self._gui_callbacks:
            try:
                cb(message)
            except Exception as e:
                logger.error("Erreur callback GUI: %s", e)

    def send_to_ws(self, message: RelayMessage):
        """Envoie un message au WebSocket mobile (depuis le desktop)."""
        self._history.append(message)
        self._ws_queue.append(message)
        for cb in self._ws_callbacks:
            try:
                cb(message)
            except Exception as e:
                logger.error("Erreur callback WS: %s", e)

    # ------------------------------------------------------------------
    # Lecture des files (polling par le GUI)
    # ------------------------------------------------------------------

    def poll_gui_messages(self) -> List[RelayMessage]:
        """Récupère et vide les messages en attente pour le GUI."""
        messages = list(self._gui_queue)
        self._gui_queue.clear()
        return messages

    def poll_ws_messages(self) -> List[RelayMessage]:
        """Récupère et vide les messages en attente pour le WebSocket."""
        messages = list(self._ws_queue)
        self._ws_queue.clear()
        return messages

    # ------------------------------------------------------------------
    # Gestion de session
    # ------------------------------------------------------------------

    def clear_history(self):
        """Efface l'historique de la session relay."""
        self._history.clear()
        self._gui_queue.clear()
        self._ws_queue.clear()

    def reset(self):
        """Réinitialise complètement le bridge."""
        self.clear_history()
        self._gui_callbacks.clear()
        self._ws_callbacks.clear()
        self._response_callbacks.clear()
        self._active = False
        self._connected_clients = 0
        self._response_event.clear()
        self._latest_response = ""
        self._latest_message_id = ""
        with self._pending_lock:
            self._pending_responses.clear()
        logger.info("RelayBridge réinitialisé")

    # ------------------------------------------------------------------
    # Réponse IA (GUI → mobile via WebSocket)
    # ------------------------------------------------------------------

    def arm_response(self, message_id: str) -> None:
        """Prépare le bridge pour attendre une réponse à un message donné.

        À appeler AVANT `send_to_gui` pour associer l'attente à l'id du
        message utilisateur. Ainsi, si le WS d'origine meurt pendant la
        génération, un WS reconnecté peut récupérer la réponse via
        `consume_pending_response(message_id)`.
        """
        self._response_event.clear()
        self._latest_response = ""
        self._latest_message_id = message_id

    async def wait_for_ai_response(self, timeout: float = 500) -> Tuple[str, str]:
        """
        Attend que le GUI produise la réponse IA (après streaming).
        Appelé depuis le handler WebSocket (async). Utilise run_in_executor
        pour ne pas bloquer la boucle asyncio.

        Retourne (texte_réponse, message_id) — message_id peut être vide
        si arm_response n'a pas été appelé.
        """
        loop = asyncio.get_event_loop()
        got = await loop.run_in_executor(
            None, self._response_event.wait, timeout
        )
        if not got:
            return ("⏱️ Délai d'attente dépassé pour la réponse.", self._latest_message_id)
        return (self._latest_response, self._latest_message_id)

    def submit_ai_response(self, text: str, message_id: Optional[str] = None) -> None:
        """
        Soumet la réponse IA au bridge. Appelé depuis le thread GUI
        (Tkinter) quand le streaming est terminé.

        La réponse est également mise en cache par message_id pour permettre
        à un mobile reconnecté de la récupérer si son WebSocket d'origine
        est mort pendant la génération.
        """
        self._latest_response = text
        # Si le caller n'a pas fourni d'id, on utilise celui enregistré via
        # arm_response(). Backward-compat pour les anciens appels.
        effective_id = message_id or self._latest_message_id

        # Enregistrer dans l'historique
        ai_msg = RelayMessage(text=text, is_user=False, source="relay")
        self._history.append(ai_msg)

        # Cacher la réponse pour récupération ultérieure (mobile déconnecté)
        if effective_id:
            self._store_pending_response(effective_id, text)

        # Signaler au WebSocket d'origine que la réponse est prête
        self._response_event.set()

        # Broadcaster à tous les WS connectés (y compris ceux qui ont rejoint
        # pendant la génération après reconnexion).
        for cb in list(self._response_callbacks):
            try:
                cb(effective_id, text)
            except Exception as e:
                logger.error("Erreur callback response broadcast: %s", e)

        logger.info(
            "Réponse IA soumise au bridge (%d chars, id=%s)",
            len(text),
            effective_id or "—",
        )

    # ------------------------------------------------------------------
    # Cache de réponses en attente (récupération après reconnexion)
    # ------------------------------------------------------------------

    def _gc_pending_responses(self) -> None:
        """Supprime les réponses expirées et borne la taille du cache."""
        now = time.time()
        expired = [
            mid for mid, (_, ts) in self._pending_responses.items()
            if now - ts > _PENDING_RESPONSE_TTL
        ]
        for mid in expired:
            self._pending_responses.pop(mid, None)
        # Si encore trop de réponses en cache, supprimer les plus anciennes
        while len(self._pending_responses) > _PENDING_RESPONSE_MAX:
            oldest = min(
                self._pending_responses.items(),
                key=lambda kv: kv[1][1],
            )[0]
            self._pending_responses.pop(oldest, None)

    def _store_pending_response(self, message_id: str, text: str) -> None:
        with self._pending_lock:
            self._pending_responses[message_id] = (text, time.time())
            self._gc_pending_responses()

    def consume_pending_response(self, message_id: str) -> Optional[str]:
        """Récupère et retire la réponse mise en cache pour un message_id.

        Appelé par le serveur Relay quand un mobile reconnecté demande
        « as-tu une réponse pour ma question X ? ».
        """
        if not message_id:
            return None
        with self._pending_lock:
            self._gc_pending_responses()
            entry = self._pending_responses.pop(message_id, None)
        return entry[0] if entry else None

    def peek_pending_response(self, message_id: str) -> Optional[str]:
        """Comme consume_pending_response mais sans retirer du cache."""
        if not message_id:
            return None
        with self._pending_lock:
            self._gc_pending_responses()
            entry = self._pending_responses.get(message_id)
        return entry[0] if entry else None

    def on_response(self, callback: Callable[[str, str], None]) -> None:
        """Enregistre un callback (message_id, text) appelé à chaque
        nouvelle réponse IA soumise. Utilisé par le serveur pour broadcaster
        vers tous les WS connectés."""
        self._response_callbacks.append(callback)

    def remove_response_callback(self, callback: Callable[[str, str], None]) -> None:
        """Supprime un callback de réponse enregistré."""
        self._response_callbacks = [
            cb for cb in self._response_callbacks if cb != callback
        ]
