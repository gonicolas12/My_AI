"""
Tests de la couche d'accès CRUD unifiée core/memory_store.py.

Opérations RÉELLES (pas de mock) : SQLite temporaire pour les faits, ChromaDB
temporaire pour les vecteurs. Les tests vectoriels sont ignorés (skip) si les
embeddings / ChromaDB ne sont pas disponibles sur la machine.
"""

import copy
import gc
import os
import shutil
import tempfile
from datetime import datetime

import pytest

from core.knowledge_base_manager import KnowledgeBaseManager
from core.memory_store import MemoryStore


# ----------------------------------------------------------------------
# Faux SessionManager en mémoire (pour la propagation « à la source »)
# ----------------------------------------------------------------------

class FakeSessionManager:
    """Implémentation minimale en mémoire compatible avec ConversationSearch."""

    def __init__(self):
        self._states = {}
        self._meta = {}

    def add_workspace(self, ws_id, name, history):
        self._states[ws_id] = {
            "conversation_history": history,
            "metadata": {"name": name},
        }
        self._meta[ws_id] = {
            "id": ws_id, "name": name,
            "last_modified": datetime.now().isoformat(),
        }

    def list_workspaces(self):
        return [dict(m) for m in self._meta.values()]

    def load_workspace(self, ws_id):
        state = self._states.get(ws_id)
        return copy.deepcopy(state) if state is not None else None

    def save_workspace(self, ws_id, state):
        self._states[ws_id] = copy.deepcopy(state)
        if ws_id in self._meta:
            self._meta[ws_id]["last_modified"] = datetime.now().isoformat()
        return True


# ----------------------------------------------------------------------
# Faits structurés (SQLite) — pas besoin d'embeddings
# ----------------------------------------------------------------------

class TestFactsCRUD:

    @pytest.fixture
    def store(self):
        tmp = tempfile.mkdtemp()
        kb = KnowledgeBaseManager(db_path=os.path.join(tmp, "facts.db"))
        try:
            yield MemoryStore(knowledge_base=kb)
        finally:
            try:
                kb.close()
            except Exception:
                pass
            gc.collect()
            shutil.rmtree(tmp, ignore_errors=True)

    def test_add_and_list(self, store):
        for i in range(5):
            assert store.add_fact("preference", f"cle {i}", f"valeur {i}") is not None
        items, total = store.list_facts()
        assert total == 5 and len(items) == 5
        assert all(it["kind"] == "fact" for it in items)

    def test_pagination(self, store):
        for i in range(7):
            store.add_fact("general", f"k{i}", f"v{i}")
        page1, total = store.list_facts(limit=5, offset=0)
        page2, total2 = store.list_facts(limit=5, offset=5)
        assert total == total2 == 7
        assert len(page1) == 5 and len(page2) == 2

    def test_filter_by_category(self, store):
        store.add_fact("preference", "p1", "café")
        store.add_fact("technical", "t1", "python")
        items, total = store.list_facts(category="technical")
        assert total == 1 and items[0]["value"] == "python"

    def test_search(self, store):
        store.add_fact("general", "langage", "j'utilise python au travail")
        store.add_fact("general", "boisson", "je bois du thé")
        items, total = store.list_facts(query="python")
        assert total == 1 and "python" in items[0]["value"]

    def test_update(self, store):
        fid = store.add_fact("general", "k", "ancienne valeur")
        assert store.update_fact(fid, "nouvelle valeur")
        items, _ = store.list_facts()
        assert any(it["id"] == fid and it["value"] == "nouvelle valeur" for it in items)

    def test_delete(self, store):
        fid = store.add_fact("general", "k", "à supprimer")
        assert store.delete_fact(fid)
        items, total = store.list_facts()
        assert total == 0 and not items

    def test_categories_and_stats(self, store):
        store.add_fact("preference", "a", "x")
        store.add_fact("technical", "b", "y")
        cats = store.fact_categories()
        assert "preference" in cats and "technical" in cats
        assert store.stats()["facts"] == 2


# ----------------------------------------------------------------------
# Entrées vectorielles « documents » (ChromaDB)
# ----------------------------------------------------------------------

class TestVectorDocuments:

    @pytest.fixture
    def store(self):
        from memory.vector_memory import VectorMemory
        tmp = tempfile.mkdtemp()
        vm = VectorMemory(max_tokens=100000, storage_dir=os.path.join(tmp, "vec"))
        if not vm.embedding_model or not vm.document_collection:
            vm.cleanup()
            shutil.rmtree(tmp, ignore_errors=True)
            pytest.skip("Embeddings/ChromaDB non disponibles")
        vm.add_document("Le ciel est bleu et lumineux. " * 40, "doc_test")
        try:
            yield MemoryStore(vector_memory=vm)
        finally:
            try:
                vm.cleanup()
            except Exception:
                pass
            gc.collect()
            shutil.rmtree(tmp, ignore_errors=True)

    def test_list_and_count(self, store):
        items, total = store.list_vectors("document")
        assert total >= 1 and len(items) == total
        assert all(it["kind"] == "vector" and it["collection"] == "document"
                   for it in items)

    def test_pagination(self, store):
        _, total = store.list_vectors("document")
        if total < 2:
            pytest.skip("Pas assez de chunks")
        p1, _ = store.list_vectors("document", limit=1, offset=0)
        p2, _ = store.list_vectors("document", limit=1, offset=1)
        assert p1[0]["id"] != p2[0]["id"]

    def test_search_substring(self, store):
        items, total = store.list_vectors("document", query="ciel")
        assert total >= 1
        assert all("ciel" in it["content"].lower() for it in items)
        none, n = store.list_vectors("document", query="zzzzz_introuvable")
        assert n == 0 and not none

    def test_update_vector(self, store):
        entry_id = store.list_vectors("document")[0][0]["id"]
        assert store.update_vector(entry_id, "Contenu réécrit", "document")
        items, _ = store.list_vectors("document")
        assert any(it["id"] == entry_id and it["content"] == "Contenu réécrit"
                   for it in items)

    def test_delete_vector_is_real(self, store):
        items, before = store.list_vectors("document")
        entry_id = items[0]["id"]
        assert store.delete_vector(entry_id, "document")
        _, after = store.list_vectors("document")
        assert after == before - 1


# ----------------------------------------------------------------------
# Entrées de conversation — propagation « à la source »
# ----------------------------------------------------------------------

class TestConversationsAtSource:

    @pytest.fixture
    def setup(self):
        from memory.vector_memory import VectorMemory
        try:
            from core.conversation_search import ConversationSearch
        except Exception:
            pytest.skip("ConversationSearch indisponible")

        tmp = tempfile.mkdtemp()
        vm = VectorMemory(max_tokens=100000, storage_dir=os.path.join(tmp, "vec"))
        if not vm.embedding_model or not vm.conversation_collection:
            vm.cleanup()
            shutil.rmtree(tmp, ignore_errors=True)
            pytest.skip("Embeddings/ChromaDB non disponibles")

        sm = FakeSessionManager()
        sm.add_workspace("ws1", "Projet", [
            {"is_user": True, "text": "J'adore le chocolat noir corsé."},
            {"is_user": False, "text": "Très bien, c'est bien noté."},
        ])
        cs = ConversationSearch(session_manager=sm, vector_memory=vm)
        if not cs.is_available():
            vm.cleanup()
            shutil.rmtree(tmp, ignore_errors=True)
            pytest.skip("Recherche conversations indisponible")
        cs.reindex(force=True)

        try:
            yield (
                MemoryStore(
                    vector_memory=vm, session_manager=sm, conversation_search=cs,
                ),
                vm, sm, cs,
            )
        finally:
            try:
                vm.cleanup()
            except Exception:
                pass
            gc.collect()
            shutil.rmtree(tmp, ignore_errors=True)

    def _find_user_entry(self, store):
        items, _ = store.list_vectors("conversation")
        for it in items:
            if "chocolat" in it["content"].lower() and \
                    it["metadata"].get("role") == "user":
                return it
        return None

    def test_indexed(self, setup):
        store, _vm, _sm, _cs = setup
        _, total = store.list_vectors("conversation")
        assert total == 2

    def test_transient_delete_reappears_on_force_reindex(self, setup):
        store, vm, _sm, cs = setup
        entry = self._find_user_entry(store)
        assert entry is not None
        # Suppression directe (transitoire), sans toucher à la source
        assert store.delete_vector(entry["id"], "conversation", at_source=False)
        assert vm.count_entries("conversation") == 1
        # Un réindex forcé reconstruit depuis le workspace → l'entrée revient
        cs.reindex(force=True)
        assert vm.count_entries("conversation") == 2

    def test_delete_at_source_is_durable(self, setup):
        store, vm, sm, cs = setup
        entry = self._find_user_entry(store)
        assert entry is not None

        assert store.delete_vector(
            entry["id"], "conversation", at_source=True, metadata=entry["metadata"],
        )
        # Le message d'origine a disparu du workspace
        history = sm.load_workspace("ws1")["conversation_history"]
        assert len(history) == 1
        assert all("chocolat" not in (m.get("text", "")).lower() for m in history)
        # Et il ne réapparaît pas, même après un réindex forcé
        assert vm.count_entries("conversation") == 1
        cs.reindex(force=True)
        assert vm.count_entries("conversation") == 1

    def test_edit_at_source(self, setup):
        store, _vm, sm, _cs = setup
        entry = self._find_user_entry(store)
        assert entry is not None
        assert store.update_vector(
            entry["id"], "Finalement je préfère le thé vert.",
            "conversation", at_source=True, metadata=entry["metadata"],
        )
        history = sm.load_workspace("ws1")["conversation_history"]
        assert history[0]["text"] == "Finalement je préfère le thé vert."


# ----------------------------------------------------------------------
# Provenance & dégradation gracieuse
# ----------------------------------------------------------------------

class TestProvenanceAndGraceful:

    def test_describe_provenance_fact(self):
        item = {
            "kind": "fact", "key": "boisson", "source": "manual",
            "confidence": 0.7, "updated_at": "2026-06-24T09:00:00",
        }
        line = MemoryStore.describe_provenance(item)
        assert "boisson" not in line  # la clé est gérée par la fenêtre, pas ici
        assert "manual" in line and "70%" in line

    def test_describe_provenance_conversation(self):
        item = {
            "kind": "vector", "collection": "conversation",
            "metadata": {"workspace_name": "Projet", "role": "user",
                         "timestamp": "2026-06-24T10:30:00"},
        }
        line = MemoryStore.describe_provenance(item)
        assert "Projet" in line and "vous" in line

    def test_describe_provenance_document(self):
        item = {
            "kind": "vector", "collection": "document",
            "metadata": {"document_name": "rapport.pdf", "chunk_index": 3},
        }
        line = MemoryStore.describe_provenance(item)
        assert "rapport.pdf" in line and "chunk 3" in line

    def test_empty_store_is_graceful(self):
        store = MemoryStore()  # aucun backend
        assert store.list_facts() == ([], 0)
        assert store.list_vectors("document") == ([], 0)
        assert store.update_fact(1, "x") is False
        assert store.delete_fact(1) is False
        assert store.stats() == {"facts": 0, "documents": 0, "conversations": 0}
        assert store.fact_categories() == []


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
