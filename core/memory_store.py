"""
Couche d'accès CRUD unifiée à la mémoire de My_AI.

Façade au-dessus des DEUX stores locaux où l'IA conserve ce qu'elle « sait » de
l'utilisateur :

  - les faits structurés  → core.knowledge_base_manager.KnowledgeBaseManager (SQLite)
  - la mémoire vectorielle → memory.vector_memory.VectorMemory (ChromaDB), avec ses
    deux collections « documents » (chunks de documents) et « conversations »
    (index de recherche cross-conversations).

Objectif : offrir à la fenêtre « Mémoire » une API homogène (lister, paginer,
filtrer, éditer, supprimer) sans qu'elle ait à connaître les détails de chaque
backend. 100 % local, opérations réelles (pas de mock).

Cas particulier des « conversations » : cette collection est reconstruite depuis
les workspaces par core.conversation_search. Une suppression/édition directe dans
ChromaDB réapparaîtrait au prochain réindex ; pour rester durable (at_source=True),
on modifie le message d'origine dans le workspace puis on relance un réindex
incrémental.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

try:
    from utils.logger import setup_logger
    logger = setup_logger("memory_store")
except Exception:  # pragma: no cover - logger optionnel
    import logging
    logger = logging.getLogger("memory_store")


class MemoryStore:
    """Accès CRUD unifié aux faits (SQLite) et aux entrées vectorielles (ChromaDB)."""

    def __init__(
        self,
        knowledge_base: Any = None,
        vector_memory: Any = None,
        session_manager: Any = None,
        conversation_search: Any = None,
    ) -> None:
        """
        Args:
            knowledge_base: instance de KnowledgeBaseManager (faits SQLite).
            vector_memory: instance de VectorMemory (collections ChromaDB).
            session_manager: SessionManager, requis pour la suppression/édition
                « à la source » des entrées de conversation.
            conversation_search: ConversationSearch, pour réindexer après une
                modification à la source.
        """
        self.knowledge_base = knowledge_base
        self.vector_memory = vector_memory
        self.session_manager = session_manager
        self.conversation_search = conversation_search

    # ------------------------------------------------------------------
    # Faits structurés (SQLite)
    # ------------------------------------------------------------------

    def list_facts(
        self,
        query: str = "",
        category: Optional[str] = None,
        limit: int = 25,
        offset: int = 0,
    ) -> Tuple[List[Dict[str, Any]], int]:
        """Liste paginée des faits, filtrée par recherche et/ou catégorie.

        Returns:
            (items, total) où items est la page demandée et total le nombre de
            faits correspondant au filtre (avant pagination).
        """
        kb = self.knowledge_base
        if kb is None:
            return [], 0
        category = (category or "").strip() or None
        try:
            if query and query.strip():
                facts = kb.search_facts(query.strip(), category=category, limit=10000)
            else:
                facts = kb.get_all_facts(category=category)
        except Exception as exc:
            logger.warning("Lecture des faits échouée: %s", exc)
            return [], 0

        total = len(facts)
        page = facts[offset:offset + limit] if limit else facts[offset:]
        return [self._fact_item(f) for f in page], total

    def add_fact(
        self,
        category: str,
        key: str,
        value: str,
        source: str = "manual",
    ) -> Optional[int]:
        """Ajoute un fait. Retourne son id, ou None en cas d'échec."""
        kb = self.knowledge_base
        if kb is None:
            return None
        try:
            return kb.add_fact(category=category, key=key, value=value, source=source)
        except Exception as exc:
            logger.warning("Ajout de fait échoué: %s", exc)
            return None

    def update_fact(self, fact_id: int, value: str) -> bool:
        """Met à jour la valeur d'un fait."""
        kb = self.knowledge_base
        if kb is None:
            return False
        try:
            return bool(kb.update_fact(fact_id, value))
        except Exception as exc:
            logger.warning("Mise à jour de fait échouée: %s", exc)
            return False

    def delete_fact(self, fact_id: int) -> bool:
        """Supprime un fait."""
        kb = self.knowledge_base
        if kb is None:
            return False
        try:
            return bool(kb.delete_fact(fact_id))
        except Exception as exc:
            logger.warning("Suppression de fait échouée: %s", exc)
            return False

    def fact_categories(self) -> List[str]:
        """Catégories ayant au moins un fait."""
        kb = self.knowledge_base
        if kb is None:
            return []
        try:
            return list(kb.get_categories())
        except Exception:
            return []

    # ------------------------------------------------------------------
    # Entrées vectorielles (ChromaDB)
    # ------------------------------------------------------------------

    def list_vectors(
        self,
        collection_type: str = "document",
        query: str = "",
        limit: int = 25,
        offset: int = 0,
    ) -> Tuple[List[Dict[str, Any]], int]:
        """Liste paginée des entrées d'une collection vectorielle.

        Sans recherche : pagination native ChromaDB (count + get limit/offset).
        Avec recherche : balayage du corpus + filtre sous-chaîne insensible à la
        casse, puis pagination en mémoire (prévisible, toutes langues).
        """
        vm = self.vector_memory
        if vm is None:
            return [], 0
        try:
            if query and query.strip():
                q = query.strip().lower()
                everything = vm.list_entries(collection_type, limit=None, offset=0)
                filtered = [
                    e for e in everything
                    if q in (e.get("content", "") or "").lower()
                ]
                total = len(filtered)
                page = filtered[offset:offset + limit] if limit else filtered[offset:]
            else:
                total = vm.count_entries(collection_type)
                page = vm.list_entries(collection_type, limit=limit, offset=offset)
        except Exception as exc:
            logger.warning("Lecture des entrées vectorielles échouée: %s", exc)
            return [], 0

        items = [
            {"kind": "vector", "collection": collection_type, **entry}
            for entry in page
        ]
        return items, total

    def update_vector(
        self,
        entry_id: str,
        new_text: str,
        collection_type: str = "document",
        at_source: bool = True,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Met à jour le texte d'une entrée vectorielle.

        Pour les conversations avec at_source=True, modifie le message d'origine
        dans le workspace puis réindexe (durable). Sinon, met à jour directement
        l'entrée ChromaDB.
        """
        vm = self.vector_memory
        if vm is None:
            return False

        if collection_type == "conversation" and at_source and self.session_manager:
            meta = metadata if metadata is not None else self._entry_meta(
                entry_id, collection_type
            )
            if self._edit_conversation_source(meta, new_text):
                self._reindex_conversations()
                return True
            return False

        return bool(vm.update_entry(entry_id, new_text, collection_type))

    def delete_vector(
        self,
        entry_id: str,
        collection_type: str = "document",
        at_source: bool = True,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Supprime une entrée vectorielle.

        Pour les conversations avec at_source=True, supprime le message d'origine
        dans le workspace puis réindexe (la suppression ne réapparaît pas). Sinon,
        suppression directe dans ChromaDB (transitoire pour les conversations).
        """
        vm = self.vector_memory
        if vm is None:
            return False

        if collection_type == "conversation" and at_source and self.session_manager:
            meta = metadata if metadata is not None else self._entry_meta(
                entry_id, collection_type
            )
            if self._delete_conversation_source(meta):
                self._reindex_conversations()
                return True
            # Repli : si la source est inaccessible, au moins retirer l'index.
            return bool(vm.delete_entry(entry_id, collection_type))

        return bool(vm.delete_entry(entry_id, collection_type))

    # ------------------------------------------------------------------
    # Propagation « à la source » pour les conversations
    # ------------------------------------------------------------------

    def _entry_meta(self, entry_id: str, collection_type: str) -> Dict[str, Any]:
        """Récupère les métadonnées d'une entrée (workspace_id, message_index…)."""
        try:
            entry = self.vector_memory.get_entry(entry_id, collection_type)
        except Exception:
            entry = None
        return (entry or {}).get("metadata", {}) or {}

    def _load_history(self, workspace_id: str):
        """Charge l'état d'un workspace et localise sa liste d'historique.

        Returns:
            (state, key, history) ou (None, None, None) si introuvable.
        """
        state = self.session_manager.load_workspace(workspace_id)
        if not state:
            return None, None, None
        key = "conversation_history" if "conversation_history" in state else (
            "history" if "history" in state else "conversation_history"
        )
        history = state.get(key) or []
        if not isinstance(history, list):
            return None, None, None
        return state, key, history

    def _delete_conversation_source(self, meta: Dict[str, Any]) -> bool:
        """Supprime le message d'origine d'une entrée de conversation."""
        if not meta:
            return False
        ws_id = meta.get("workspace_id")
        idx = meta.get("message_index")
        if not ws_id or idx is None:
            return False
        try:
            idx = int(idx)
        except (TypeError, ValueError):
            return False

        state, key, history = self._load_history(ws_id)
        if state is None or not (0 <= idx < len(history)):
            return False
        del history[idx]
        state[key] = history
        try:
            return bool(self.session_manager.save_workspace(ws_id, state))
        except Exception as exc:
            logger.warning("Sauvegarde workspace après suppression échouée: %s", exc)
            return False

    def _edit_conversation_source(self, meta: Dict[str, Any], new_text: str) -> bool:
        """Réécrit le message d'origine d'une entrée de conversation."""
        if not meta or not new_text or not new_text.strip():
            return False
        ws_id = meta.get("workspace_id")
        idx = meta.get("message_index")
        if not ws_id or idx is None:
            return False
        try:
            idx = int(idx)
        except (TypeError, ValueError):
            return False

        state, key, history = self._load_history(ws_id)
        if state is None or not (0 <= idx < len(history)):
            return False
        msg = history[idx]
        if not isinstance(msg, dict):
            return False
        # Conserver le champ texte utilisé par le message d'origine.
        if "content" in msg and "text" not in msg:
            msg["content"] = new_text
        else:
            msg["text"] = new_text
        state[key] = history
        try:
            return bool(self.session_manager.save_workspace(ws_id, state))
        except Exception as exc:
            logger.warning("Sauvegarde workspace après édition échouée: %s", exc)
            return False

    def _reindex_conversations(self) -> None:
        """Relance un réindex incrémental (reconstruit le workspace modifié)."""
        cs = self.conversation_search
        if cs is None:
            return
        try:
            cs.reindex(force=False)
        except Exception as exc:
            logger.warning("Réindexation des conversations échouée: %s", exc)

    # ------------------------------------------------------------------
    # Vue d'ensemble / provenance
    # ------------------------------------------------------------------

    def stats(self) -> Dict[str, int]:
        """Compteurs par source (faits, documents, conversations)."""
        facts = 0
        if self.knowledge_base is not None:
            try:
                facts = len(self.knowledge_base.get_all_facts())
            except Exception:
                facts = 0
        documents = conversations = 0
        if self.vector_memory is not None:
            documents = self.vector_memory.count_entries("document")
            conversations = self.vector_memory.count_entries("conversation")
        return {
            "facts": facts,
            "documents": documents,
            "conversations": conversations,
        }

    @staticmethod
    def describe_provenance(item: Dict[str, Any]) -> str:
        """Construit une ligne de provenance lisible pour un item de mémoire."""
        if item.get("kind") == "fact":
            src = item.get("source") or "manuel"
            try:
                conf_pct = int(float(item.get("confidence", 1.0)) * 100)
            except (TypeError, ValueError):
                conf_pct = 100
            parts = [f"source : {src}", f"confiance : {conf_pct}%"]
            updated = str(item.get("updated_at", ""))
            if updated:
                parts.append(f"maj : {updated[:19].replace('T', ' ')}")
            return "  ·  ".join(parts)

        meta = item.get("metadata", {}) or {}
        if item.get("collection") == "conversation":
            name = meta.get("workspace_name") or meta.get("workspace_id") or "conversation"
            parts = [f"💼 {name}"]
            role = meta.get("role", "")
            if role:
                parts.append("🧑 vous" if role == "user" else "🤖 assistant")
            ts = str(meta.get("timestamp", ""))
            if ts:
                parts.append(ts[:19].replace("T", " "))
            return "  ·  ".join(parts)

        # Collection « documents »
        name = meta.get("document_name") or "document"
        parts = [f"📄 {name}"]
        chunk = meta.get("chunk_index")
        if chunk is not None:
            parts.append(f"chunk {chunk}")
        created = str(meta.get("created", ""))
        if created:
            parts.append(created[:19].replace("T", " "))
        return "  ·  ".join(parts)

    @staticmethod
    def _fact_item(fact: Dict[str, Any]) -> Dict[str, Any]:
        """Normalise un fait SQLite en item de mémoire homogène."""
        return {
            "kind": "fact",
            "id": fact.get("id"),
            "category": fact.get("category", "general"),
            "key": fact.get("key", ""),
            "value": fact.get("value", fact.get("content", "")),
            "source": fact.get("source", ""),
            "confidence": fact.get("confidence", 1.0),
            "created_at": fact.get("created_at", ""),
            "updated_at": fact.get("updated_at", ""),
        }
