"""
Tests pour core/conversation_search.py (recherche globale cross-conversations).

Utilise un faux VectorMemory deterministe (sans modele ML) pour valider la
logique d'indexation incrementale, de purge et de filtrage. Aucun embedding
reel n'est requis.
"""

import tempfile
from pathlib import Path

import pytest

from core.conversation_search import ConversationSearch
from core.session_manager import SessionManager


# ---------------------------------------------------------------------------
# Faux VectorMemory : mime l'interface utilisee par ConversationSearch
# ---------------------------------------------------------------------------

class _FakeEmbedding(list):
    def tolist(self):
        return list(self)


class _FakeModel:
    def encode(self, text):
        # Vecteur factice deterministe (longueur du texte) - non utilise pour le
        # scoring, juste pour respecter l'API encode().tolist().
        return _FakeEmbedding([float(len(text))])


class _FakeCollection:
    def __init__(self):
        # id -> {"document": str, "metadata": dict}
        self.store = {}

    def add(self, ids, embeddings, documents, metadatas):
        for i, _id in enumerate(ids):
            self.store[_id] = {"document": documents[i], "metadata": metadatas[i]}

    def delete(self, where=None):
        if not where:
            self.store.clear()
            return
        ws = where.get("workspace_id")
        to_del = [k for k, v in self.store.items()
                  if v["metadata"].get("workspace_id") == ws]
        for k in to_del:
            del self.store[k]


class _FakeVectorMemory:
    def __init__(self, storage_dir):
        self.storage_dir = Path(storage_dir)
        self.embedding_model = _FakeModel()
        self.conversation_collection = _FakeCollection()

    def search_similar(self, query, n_results=5, collection_type="conversation",
                       rerank=True):
        # Scoring deterministe par recouvrement de mots-cles.
        q_words = set(query.lower().split())
        scored = []
        for entry in self.conversation_collection.store.values():
            content = entry["document"]
            overlap = len(q_words & set(content.lower().split()))
            if overlap > 0:
                scored.append((overlap, content, entry["metadata"]))
        scored.sort(key=lambda t: t[0], reverse=True)
        results = []
        for overlap, content, meta in scored[:n_results]:
            results.append({
                "content": content,
                "metadata": meta,
                "distance": 1.0 / (1 + overlap),
                "rerank_score": float(overlap),
            })
        return results


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def env():
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        sm = SessionManager(workspaces_dir=str(tmp / "workspaces"))
        vm = _FakeVectorMemory(tmp / "vector_store")
        (tmp / "vector_store").mkdir(parents=True, exist_ok=True)
        cs = ConversationSearch(session_manager=sm, vector_memory=vm)
        yield sm, vm, cs


def _make_ws(sm, name, messages):
    ws_id = sm.create_workspace(name)
    sm.save_workspace(ws_id, {"conversation_history": messages})
    return ws_id


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_available(env):
    _, _, cs = env
    assert cs.is_available() is True


def test_index_and_search_finds_right_workspace(env):
    sm, _, cs = env
    _make_ws(sm, "Python", [
        {"text": "Comment installer une bibliotheque python avec pip", "is_user": True},
        {"text": "Tu peux utiliser pip install nom_du_paquet", "is_user": False},
    ])
    ws_cuisine = _make_ws(sm, "Cuisine", [
        {"text": "Quelle est la meilleure recette de tarte aux pommes", "is_user": True},
        {"text": "Il faut des pommes du beurre et de la pate feuilletee", "is_user": False},
    ])

    stats = cs.reindex(force=True)
    assert stats["indexed"] == 2
    assert stats["messages"] == 4

    results = cs.search("recette tarte pommes", n_results=5, auto_reindex=False)
    assert results
    assert results[0]["workspace_id"] == ws_cuisine
    assert "pomme" in results[0]["excerpt"].lower()


def test_incremental_reindex_skips_unchanged(env):
    sm, _, cs = env
    _make_ws(sm, "Notes", [
        {"text": "Une note suffisamment longue pour etre indexee ici", "is_user": True},
    ])
    first = cs.reindex(force=False)
    assert first["indexed"] == 1
    # Rien n'a change -> aucun reindex
    second = cs.reindex(force=False)
    assert second["indexed"] == 0
    assert second["messages"] == 0


def test_reindex_picks_up_modifications(env):
    sm, vm, cs = env
    ws_id = _make_ws(sm, "Journal", [
        {"text": "Premier message assez long pour passer le filtre", "is_user": True},
    ])
    cs.reindex(force=False)
    count_before = len(vm.conversation_collection.store)

    # Ajout d'un message -> last_modified change
    sm.save_workspace(ws_id, {"conversation_history": [
        {"text": "Premier message assez long pour passer le filtre", "is_user": True},
        {"text": "Deuxieme message ajoute plus tard dans la conversation", "is_user": False},
    ]})
    stats = cs.reindex(force=False)
    assert stats["indexed"] == 1
    assert len(vm.conversation_collection.store) > count_before


def test_deleted_workspace_is_purged(env):
    sm, vm, cs = env
    ws_id = _make_ws(sm, "Temporaire", [
        {"text": "Contenu temporaire qui sera supprime du systeme bientot", "is_user": True},
    ])
    cs.reindex(force=False)
    assert any(m["metadata"]["workspace_id"] == ws_id
               for m in vm.conversation_collection.store.values())

    sm.delete_workspace(ws_id)
    stats = cs.reindex(force=False)
    assert stats["removed"] == 1
    assert not any(m["metadata"]["workspace_id"] == ws_id
                   for m in vm.conversation_collection.store.values())


def test_short_messages_skipped(env):
    sm, vm, cs = env
    _make_ws(sm, "Court", [
        {"text": "ok", "is_user": True},
        {"text": "oui", "is_user": False},
        {"text": "Ceci est un message assez long pour etre indexe correctement", "is_user": True},
    ])
    cs.reindex(force=True)
    assert len(vm.conversation_collection.store) == 1


def test_role_and_keyword_filters(env):
    sm, _, cs = env
    _make_ws(sm, "Mix", [
        {"text": "question sur le deploiement docker en production", "is_user": True},
        {"text": "reponse sur le deploiement docker avec compose", "is_user": False},
    ])
    cs.reindex(force=True)

    only_user = cs.search("deploiement docker", role="user", auto_reindex=False)
    assert only_user
    assert all(r["role"] == "user" for r in only_user)

    kw = cs.search("deploiement docker", keyword="compose", auto_reindex=False)
    assert kw
    assert all("compose" in r["excerpt"].lower() for r in kw)
