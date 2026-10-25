"""
Mémoire de la fenêtre (memory_panel.py de Tk)

Faits (base de connaissances SQLite), documents et conversations (ChromaDB),
par le MemoryStore du moteur : pages de 20, recherche, catégorie, ajout d'un
fait, modification du contenu, suppression.

Un message de conversation modifié, ou supprimé « à la source », passe par le
ChatService (change_saved_message) : retrouvé par son texte, il change aussi
dans la conversation ouverte, et une sauvegarde suivante ne le fait pas
réapparaître. La recherche globale réindexe ensuite la session modifiée.

Lister et chercher ne calculent aucun embedding (recherche de texte) ; modifier
un document ou réindexer une session en recalculent, sur le modèle local de
sentence-transformers. Aucun appel à Ollama.
"""

import math
from typing import Any, Callable, Dict, Optional

from core.chat_service import ChatError
from core.i18n import tr
from utils.logger import setup_logger

logger = setup_logger("DesktopMemory")

PAGE_SIZE = 20
TABS = ("facts", "document", "conversation")
FACT_CATEGORIES = ("general", "preference", "decision", "person", "procedure", "technical")
# Clé d'un fait ajouté à la main : sa première ligne (Tk)
_KEY_MAX = 80


class MemoryPanelError(Exception):
    """Action refusée ou en échec : message affiché."""


class MemoryService:
    """Lecture et modification de la mémoire du moteur."""

    def __init__(self, engine: Callable[[], Optional[Any]], chat: Callable[[], Optional[Any]]):
        """
        Args:
            engine: moteur en cours (None pendant le lancement)
            chat: service de chat (propagation à la source des conversations)
        """
        self._engine = engine
        self._chat = chat

    def _store(self):
        engine = self._engine()
        getter = getattr(engine, "get_memory_store", None)
        store = getter() if callable(getter) else None
        if store is None:
            raise MemoryPanelError(tr("memory.unavailable"))
        return store

    def page(self, tab: str, query: str = "", category: Optional[str] = None,
             page: int = 0) -> Dict[str, Any]:
        """Une page d'un onglet : éléments, total filtré, nombre de pages, compteurs."""
        if tab not in TABS:
            raise MemoryPanelError(tr("memory.unknownTab", tab=tab))
        store = self._store()
        query = (query or "").strip()
        page = max(0, int(page))
        offset = page * PAGE_SIZE
        if tab == "facts":
            items, total = store.list_facts(query=query, category=category or None,
                                            limit=PAGE_SIZE, offset=offset)
        else:
            items, total = store.list_vectors(collection_type=tab, query=query,
                                              limit=PAGE_SIZE, offset=offset)
        pages = max(1, math.ceil(total / PAGE_SIZE))
        # Page au-delà de la fin (après une suppression) : la dernière (Tk)
        if page >= pages and total:
            return self.page(tab, query, category, pages - 1)
        return {
            "items": [self._view(store, item) for item in items],
            "total": total, "page": page, "pages": pages,
            "stats": store.stats(), "categories": list(FACT_CATEGORIES),
        }

    @staticmethod
    def _view(store, item: Dict[str, Any]) -> Dict[str, Any]:
        """Élément pour la fenêtre, avec sa provenance en clair."""
        view = dict(item)
        view["provenance"] = store.describe_provenance(item)
        if view.get("kind") == "vector":
            view["metadata"] = {key: value for key, value in (item.get("metadata") or {}).items()
                                if isinstance(value, (str, int, float, bool)) or value is None}
        return view

    def add_fact(self, category: str, text: str) -> int:
        """« Ajouter » : un fait saisi à la main (source « manual », confiance 1)."""
        text = (text or "").strip()
        if not text:
            raise MemoryPanelError(tr("memory.emptyContent"))
        if category not in FACT_CATEGORIES:
            category = "general"
        key = text.splitlines()[0].strip()[:_KEY_MAX] or "fait manuel"
        fact_id = self._store().add_fact(category, key, text, source="manual")
        if fact_id is None:
            raise MemoryPanelError(tr("memory.addFailed"))
        return fact_id

    def update(self, tab: str, entry_id: Any, text: str) -> None:
        """Nouveau contenu d'un élément ; un message de conversation change à la source."""
        text = (text or "").strip()
        if not text:
            raise MemoryPanelError(tr("memory.emptyContent"))
        store = self._store()
        if tab == "facts":
            ok = store.update_fact(int(entry_id), text)
        elif tab == "conversation":
            self._change_conversation(store, str(entry_id), text)
            ok = True
        elif tab == "document":
            ok = store.update_vector(str(entry_id), text, "document", at_source=False)
        else:
            raise MemoryPanelError(tr("memory.unknownTab", tab=tab))
        if not ok:
            raise MemoryPanelError(tr("memory.editFailed"))

    def delete(self, tab: str, entry_id: Any, at_source: bool = True) -> None:
        """Suppression ; un message de conversation peut l'être aussi à la source."""
        store = self._store()
        if tab == "facts":
            ok = store.delete_fact(int(entry_id))
        elif tab == "conversation" and at_source:
            try:
                self._change_conversation(store, str(entry_id), None)
                ok = True
            except MemoryPanelError as exc:
                # Source inaccessible : au moins l'index, comme le MemoryStore
                logger.info("Suppression à la source impossible (%s) : index seul", exc)
                ok = store.delete_vector(str(entry_id), "conversation", at_source=False)
        elif tab in ("document", "conversation"):
            ok = store.delete_vector(str(entry_id), tab, at_source=False)
        else:
            raise MemoryPanelError(tr("memory.unknownTab", tab=tab))
        if not ok:
            raise MemoryPanelError(tr("memory.deleteFailed"))

    def _change_conversation(self, store, entry_id: str, new_text: Optional[str]) -> None:
        """Message d'origine réécrit ou supprimé, puis session réindexée."""
        vector_memory = getattr(store, "vector_memory", None)
        entry = vector_memory.get_entry(entry_id, "conversation") if vector_memory else None
        meta = (entry or {}).get("metadata") or {}
        session_id = meta.get("workspace_id")
        index = meta.get("message_index")
        chat = self._chat()
        if not entry or not session_id or index is None or chat is None:
            raise MemoryPanelError(tr("memory.sourceGone"))
        try:
            chat.change_saved_message(session_id, int(index), entry.get("content") or "", new_text)
        except ChatError as exc:
            raise MemoryPanelError(str(exc)) from exc
        search = getattr(store, "conversation_search", None)
        if search is not None:
            try:
                search.reindex(force=False)
            except Exception as exc:  # pylint: disable=broad-except
                logger.warning("Réindexation des conversations échouée : %s", exc)
