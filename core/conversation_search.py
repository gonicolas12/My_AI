"""
Recherche globale cross-conversations / cross-workspaces.

Interroge TOUTES les conversations sauvegardees (workspaces) a la fois, en
semantique, en REUTILISANT l'index ChromaDB existant (collection "conversations"
de memory.vector_memory) et l'embedding partage (core.shared). Aucun second
pipeline d'embedding n'est cree.

Principe :
  - L'indexation est incrementale : un manifeste (conversation_index.json) garde
    le `last_modified` de chaque workspace deja indexe. Au reindex, seuls les
    workspaces nouveaux/modifies sont re-traites, et les workspaces supprimes
    sont retires de l'index.
  - La recherche est hybride : similarite semantique (+ reranking CrossEncoder
    si dispo, herite de VectorMemory.search_similar) puis post-filtres optionnels
    mot-cle / role / date.
"""

from __future__ import annotations

import json
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from utils.logger import setup_logger
    logger = setup_logger("conversation_search")
except Exception:  # pragma: no cover - logger optionnel
    import logging
    logger = logging.getLogger("conversation_search")


# Messages trop courts ou techniques a ne pas indexer (bruit)
_MIN_MESSAGE_LEN = 15
_SKIP_TYPES = {"file_generation_placeholder", "image"}


class ConversationSearch:
    """Recherche semantique globale sur l'ensemble des workspaces."""

    def __init__(self, session_manager: Any, vector_memory: Any) -> None:
        """
        Args:
            session_manager: instance de core.session_manager.SessionManager
            vector_memory: instance de memory.vector_memory.VectorMemory (partagee)
        """
        self.session_manager = session_manager
        self.vector_memory = vector_memory
        self._lock = threading.Lock()

        # Manifeste d'indexation, range a cote de l'index ChromaDB
        try:
            storage_dir = Path(getattr(vector_memory, "storage_dir", "memory/vector_store"))
        except Exception:
            storage_dir = Path("memory/vector_store")
        self._manifest_path = storage_dir / "conversation_index.json"

    # ------------------------------------------------------------------
    # Disponibilite
    # ------------------------------------------------------------------

    def is_available(self) -> bool:
        """La recherche n'est exploitable que si embedding + collection presents."""
        vm = self.vector_memory
        return bool(
            vm is not None
            and getattr(vm, "embedding_model", None) is not None
            and getattr(vm, "conversation_collection", None) is not None
            and self.session_manager is not None
        )

    @property
    def _collection(self):
        return getattr(self.vector_memory, "conversation_collection", None)

    # ------------------------------------------------------------------
    # Manifeste
    # ------------------------------------------------------------------

    def _load_manifest(self) -> Dict[str, str]:
        if not self._manifest_path.is_file():
            return {}
        try:
            with open(self._manifest_path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            return data if isinstance(data, dict) else {}
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Manifeste de recherche illisible: %s", exc)
            return {}

    def _save_manifest(self, manifest: Dict[str, str]) -> None:
        try:
            self._manifest_path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self._manifest_path.with_suffix(".json.tmp")
            with open(tmp, "w", encoding="utf-8") as fh:
                json.dump(manifest, fh, indent=2, ensure_ascii=False)
            tmp.replace(self._manifest_path)
        except OSError as exc:
            logger.warning("Sauvegarde du manifeste echouee: %s", exc)

    # ------------------------------------------------------------------
    # Indexation
    # ------------------------------------------------------------------

    @staticmethod
    def _iter_indexable_messages(history: List[dict]):
        """Genere (index, role, text, timestamp) pour les messages indexables."""
        for idx, msg in enumerate(history):
            if not isinstance(msg, dict):
                continue
            if msg.get("type") in _SKIP_TYPES:
                continue
            text = (msg.get("text") or msg.get("content") or "").strip()
            if len(text) < _MIN_MESSAGE_LEN:
                continue
            is_user = msg.get("is_user", msg.get("role", "user") == "user")
            role = "user" if is_user else "assistant"
            timestamp = str(msg.get("timestamp", ""))
            yield idx, role, text, timestamp

    def _delete_workspace_entries(self, workspace_id: str) -> None:
        """Supprime de l'index toutes les entrees d'un workspace."""
        col = self._collection
        if col is None:
            return
        try:
            col.delete(where={"workspace_id": workspace_id})
        except Exception as exc:
            logger.warning("Suppression index workspace '%s' echouee: %s", workspace_id, exc)

    def _index_workspace(self, workspace_id: str, workspace_name: str) -> int:
        """(Re)indexe un workspace. Retourne le nombre de messages indexes."""
        col = self._collection
        model = getattr(self.vector_memory, "embedding_model", None)
        if col is None or model is None:
            return 0

        state = self.session_manager.load_workspace(workspace_id)
        if not state:
            return 0
        history = state.get("conversation_history", state.get("history", []))
        if not isinstance(history, list):
            return 0

        # Repartir de zero pour ce workspace (gere les editions/suppressions)
        self._delete_workspace_entries(workspace_id)

        ids: List[str] = []
        embeddings: List[list] = []
        documents: List[str] = []
        metadatas: List[dict] = []

        for idx, role, text, timestamp in self._iter_indexable_messages(history):
            ids.append(f"conv_{workspace_id}_{idx}")
            embeddings.append(model.encode(text).tolist())
            documents.append(text)
            metadatas.append(
                {
                    "workspace_id": workspace_id,
                    "workspace_name": workspace_name,
                    "message_index": idx,
                    "role": role,
                    "timestamp": timestamp,
                }
            )

        if ids:
            try:
                col.add(
                    ids=ids,
                    embeddings=embeddings,
                    documents=documents,
                    metadatas=metadatas,
                )
            except Exception as exc:
                logger.error("Indexation workspace '%s' echouee: %s", workspace_id, exc)
                return 0

        return len(ids)

    def reindex(self, force: bool = False) -> Dict[str, int]:
        """
        Synchronise l'index avec les workspaces sur disque (incremental).

        Args:
            force: si True, reindexe tous les workspaces sans tenir compte du
                   manifeste.

        Returns:
            {"indexed": n_workspaces, "messages": n_messages, "removed": n_supprimes}
        """
        if not self.is_available():
            return {"indexed": 0, "messages": 0, "removed": 0}

        with self._lock:
            manifest = {} if force else self._load_manifest()
            try:
                workspaces = self.session_manager.list_workspaces()
            except Exception as exc:
                logger.warning("Liste des workspaces indisponible: %s", exc)
                return {"indexed": 0, "messages": 0, "removed": 0}

            current_ids = {ws.get("id") for ws in workspaces if ws.get("id")}

            # Workspaces disparus -> purge de l'index + du manifeste
            removed = 0
            for old_id in list(manifest.keys()):
                if old_id not in current_ids:
                    self._delete_workspace_entries(old_id)
                    manifest.pop(old_id, None)
                    removed += 1

            indexed = 0
            messages = 0
            for ws in workspaces:
                ws_id = ws.get("id")
                if not ws_id:
                    continue
                last_modified = str(ws.get("last_modified", ""))
                if not force and manifest.get(ws_id) == last_modified:
                    continue  # inchange depuis le dernier index
                ws_name = ws.get("name", ws_id)
                n = self._index_workspace(ws_id, ws_name)
                manifest[ws_id] = last_modified
                indexed += 1
                messages += n

            self._save_manifest(manifest)
            if indexed or removed:
                logger.info(
                    "Reindex termine: %d workspace(s), %d message(s), %d supprime(s)",
                    indexed, messages, removed,
                )
            return {"indexed": indexed, "messages": messages, "removed": removed}

    # ------------------------------------------------------------------
    # Recherche
    # ------------------------------------------------------------------

    def search(
        self,
        query: str,
        n_results: int = 10,
        role: Optional[str] = None,
        keyword: Optional[str] = None,
        since: Optional[str] = None,
        auto_reindex: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        Recherche semantique globale sur toutes les conversations.

        Args:
            query: requete en langage naturel
            n_results: nombre de resultats finaux
            role: filtre "user" | "assistant" (None = tous)
            keyword: sous-chaine devant apparaitre dans l'extrait (filtre exact)
            since: date ISO minimale (timestamp >= since)
            auto_reindex: rafraichit l'index avant de chercher (incremental)

        Returns:
            Liste de resultats tries par pertinence :
            {workspace_id, workspace_name, message_index, role, timestamp,
             excerpt, score, distance}
        """
        if not self.is_available() or not query or not query.strip():
            return []

        if auto_reindex:
            try:
                self.reindex(force=False)
            except Exception as exc:
                logger.warning("Reindex avant recherche ignore: %s", exc)

        # Sur-echantillonner pour absorber les post-filtres
        fetch_n = max(n_results * 4, n_results)
        try:
            raw = self.vector_memory.search_similar(
                query, n_results=fetch_n, collection_type="conversation", rerank=True,
            )
        except Exception as exc:
            logger.warning("Recherche conversations echouee: %s", exc)
            return []

        keyword_lc = keyword.lower() if keyword else None
        results: List[Dict[str, Any]] = []
        for r in raw:
            meta = r.get("metadata", {}) or {}
            content = r.get("content", "")

            if role and meta.get("role") != role:
                continue
            if keyword_lc and keyword_lc not in content.lower():
                continue
            ts = str(meta.get("timestamp", ""))
            if since and ts and ts < since:
                continue

            results.append(
                {
                    "workspace_id": meta.get("workspace_id", ""),
                    "workspace_name": meta.get("workspace_name", ""),
                    "message_index": meta.get("message_index", 0),
                    "role": meta.get("role", ""),
                    "timestamp": ts,
                    "excerpt": content,
                    "score": r.get("rerank_score"),
                    "distance": r.get("distance"),
                }
            )
            if len(results) >= n_results:
                break

        return results
