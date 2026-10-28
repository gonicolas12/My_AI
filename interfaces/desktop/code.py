"""
Page Code de la fenêtre : la conversation de l'extension VS Code

La conversation vit dans relay/code_hub.py, partagée avec l'extension VS Code
(qui exécute les outils) et la vue Code du téléphone. La fenêtre la lit en
entier (GET /api/code), puis la suit par les événements « code.* » du bus :
état de VS Code et de la réponse, message de l'utilisateur, texte en
streaming, appels d'outils et approbations, fin de réponse, effacement. Ses
messages, Stop, Effacer et réponses aux approbations passent par le même hub
que ceux du téléphone.

Les pièces jointes de la page sont celles du chat (documents, code, images,
dossier glissé) : la page garde leur liste et les envoie avec le message ; le
hub les lit, et le modèle vision décrit les images.
"""

import os
import threading
from typing import Any, Callable, Dict, List, Optional, Sequence, Set, Tuple

from core.chat_service import ChatError, file_type_for, folder_attachment_files
from core.i18n import tr
from interfaces.desktop import files as local_files
from relay.code_hub import CodeHub

# Champs du hub qui ne concernent que le Relay (lien VS Code d'où part un message)
_RELAY_ONLY = ("type", "client")


class CodeService:
    """Conversation Code vue de la fenêtre desktop."""

    def __init__(
        self,
        hub: CodeHub,
        publish: Callable[..., Dict[str, Any]],
        last_seq: Callable[[], int],
    ):
        self._hub = hub
        self._publish = publish
        self._last_seq = last_seq
        self._lock = threading.Lock()
        # Pièces jointes vérifiées : la fenêtre peut afficher leurs vignettes
        self._known: Set[str] = set()
        self._unsubscribe: Optional[Callable[[], None]] = hub.subscribe(self._deliver)

    def _deliver(self, event: Dict[str, Any]) -> None:
        """Événement du hub → événement « code.* » du bus (sous le verrou du hub)."""
        kind = event.get("type")
        if kind == "snapshot":
            return
        payload = {key: value for key, value in event.items() if key not in _RELAY_ONLY}
        self._publish(f"code.{kind}", payload, message_id=payload.get("message_id"))

    def snapshot(self) -> Dict[str, Any]:
        """État, messages et seq du dernier événement qu'ils contiennent."""
        return self._hub.snapshot(seq=self._last_seq)

    def state(self) -> Dict[str, Any]:
        """État seul (barre latérale) et seq de sa lecture."""
        snapshot = self._hub.snapshot(seq=self._last_seq)
        return {"state": snapshot["state"], "seq": snapshot["seq"]}

    def send(self, text: str, files: Sequence[Tuple[str, str]] = ()) -> str:
        """Message tapé dans la page, avec ses pièces jointes (chemin, nom).

        CodeError si VS Code est absent ou occupé.
        """
        return self._hub.send(text, "desktop", files=files)

    def inspect(self, paths: Sequence[str]) -> Dict[str, Any]:
        """Fichiers choisis, déposés ou collés dans la page, vérifiés comme dans le chat.

        Un dossier joint ses fichiers lisibles (règle du chat, D24), sans ses
        images. Chaque refus a son message.
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
            else:
                files = [path]
            for item in files:
                file_type = file_type_for(item)
                if not os.path.isfile(item):
                    refused.append(tr("chat.invalidPath", path=item))
                elif file_type is None:
                    ext = os.path.splitext(item)[1].lower() or "?"
                    refused.append(tr("chat.unsupportedFormat", ext=ext))
                else:
                    attachments.append(
                        {"path": item, "name": os.path.basename(item), "type": file_type})
        with self._lock:
            self._known.update(local_files.normalize(item["path"]) for item in attachments)
        return {"attachments": attachments, "refused": refused}

    def known_paths(self) -> Set[str]:
        """Pièces jointes de la page (vignettes des images)."""
        with self._lock:
            return set(self._known)

    def stop(self) -> bool:
        return self._hub.stop()

    def clear(self) -> None:
        self._hub.clear()

    def approve(self, call_id: str, decision: str) -> bool:
        return self._hub.approve(call_id, decision)

    def close(self) -> None:
        """Plus d'événements vers le bus (arrêt de l'appli, tests)."""
        if self._unsubscribe is not None:
            self._unsubscribe()
            self._unsubscribe = None
