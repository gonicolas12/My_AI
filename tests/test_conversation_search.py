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

    def get(self, include=None):
        ids = list(self.store.keys())
        return {
            "ids": ids,
            "documents": [self.store[i]["document"] for i in ids],
            "metadatas": [self.store[i]["metadata"] for i in ids],
        }


def _overlap(query, content):
    return len(set(query.lower().split()) & set(content.lower().split()))


class _FakeReranker:
    """Mime le CrossEncoder : score bas (~ -11) sans recouvrement, eleve sinon."""

    def predict(self, pairs):
        return [float(_overlap(q, d) * 8 - 11) for q, d in pairs]


class _FakeVectorMemory:
    def __init__(self, storage_dir, with_reranker=True, semantic_blind=False):
        self.storage_dir = Path(storage_dir)
        self.embedding_model = _FakeModel()
        self.conversation_collection = _FakeCollection()
        self.reranker = _FakeReranker() if with_reranker else None
        # semantic_blind : simule un corpus ou le bon message est HORS des plus
        # proches voisins (search_similar ne le remonte pas).
        self.semantic_blind = semantic_blind

    def search_similar(self, query, n_results=5, collection_type="conversation",
                       rerank=True):
        if self.semantic_blind:
            return []
        # Comme ChromaDB : renvoie les n plus proches voisins SANS notion de
        # seuil (proxy de distance = inverse du recouvrement de mots).
        scored = []
        for entry in self.conversation_collection.store.values():
            content = entry["document"]
            ov = _overlap(query, content)
            scored.append((ov, content, entry["metadata"]))
        # Tri par proximite decroissante, tronque a n_results
        scored.sort(key=lambda t: t[0], reverse=True)
        results = []
        for ov, content, meta in scored[:n_results]:
            results.append({
                "content": content,
                "metadata": meta,
                "distance": 1.0 / (1 + ov),
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


def test_all_nonempty_messages_indexed_no_length_limit(env):
    """Aucune limite de longueur : tout message non vide est indexe, vides ignores."""
    sm, vm, cs = env
    _make_ws(sm, "Court", [
        {"text": "ok", "is_user": True},      # tres court -> garde quand meme
        {"text": "Ok !", "is_user": False},   # tres court -> garde quand meme
        {"text": "   ", "is_user": True},     # vide apres strip -> ignore
        {"text": "", "is_user": False},        # vide -> ignore
    ])
    cs.reindex(force=True)
    assert len(vm.conversation_collection.store) == 2


def test_user_messages_are_searchable(env):
    """Coeur de la demande : retrouver SES propres messages, meme courts."""
    sm, _, cs = env
    ws_id = _make_ws(sm, "Mes questions", [
        {"text": "comment configurer un reverse proxy nginx", "is_user": True},
        {"text": "Voici comment faire avec un bloc server et proxy_pass", "is_user": False},
    ])
    cs.reindex(force=True)
    res = cs.search("reverse proxy nginx", role="user", auto_reindex=False)
    assert res
    assert res[0]["workspace_id"] == ws_id
    assert res[0]["role"] == "user"


def test_irrelevant_query_returns_nothing(env):
    """Le bug d'origine : une requete hors-sujet ne doit PAS tout remonter."""
    sm, _, cs = env
    _make_ws(sm, "Python", [
        {"text": "Comment installer une bibliotheque avec pip et venv", "is_user": True},
        {"text": "Utilise pip install puis active environnement virtuel", "is_user": False},
    ])
    cs.reindex(force=True)
    # Aucun recouvrement lexical ni semantique -> score reranker tres bas -> filtre
    results = cs.search("aujourd hui meteo", auto_reindex=False)
    assert results == []


def test_lexical_match_survives_low_rerank(env):
    """Un mot-cle present litteralement passe meme si le reranker le note bas."""
    sm, vm, cs = env

    # Reranker qui note TOUT tres bas (simule la faiblesse sur le francais)
    class _Harsh:
        def predict(self, pairs):
            return [-50.0 for _ in pairs]
    vm.reranker = _Harsh()

    _make_ws(sm, "Docker", [
        {"text": "Procedure de deploiement docker en production avec compose", "is_user": True},
    ])
    cs.reindex(force=True)
    results = cs.search("docker", auto_reindex=False)
    assert results, "le filet lexical doit conserver une correspondance exacte"
    assert "docker" in results[0]["excerpt"].lower()


def test_no_reranker_distance_fallback():
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        sm = SessionManager(workspaces_dir=str(tmp / "workspaces"))
        vm = _FakeVectorMemory(tmp / "vs", with_reranker=False)
        (tmp / "vs").mkdir(parents=True, exist_ok=True)
        cs = ConversationSearch(session_manager=sm, vector_memory=vm)
        _make_ws(sm, "Notes", [
            {"text": "Une note sur les algorithmes de tri rapide quicksort", "is_user": True},
        ])
        cs.reindex(force=True)
        # Mot present -> filet lexical (distance proxy faible aussi)
        assert cs.search("quicksort", auto_reindex=False)


def test_exact_word_never_missed_even_outside_semantic_topn():
    """Un mot exact doit etre trouve meme si la recherche semantique ne le
    remonte PAS (corpus volumineux / autre langue)."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        sm = SessionManager(workspaces_dir=str(tmp / "workspaces"))
        vm = _FakeVectorMemory(tmp / "vs", with_reranker=True, semantic_blind=True)
        (tmp / "vs").mkdir(parents=True, exist_ok=True)
        cs = ConversationSearch(session_manager=sm, vector_memory=vm)
        ws_id = _make_ws(sm, "Ops", [
            {"text": "On a deploye le cluster kubernetes hier soir", "is_user": True},
            {"text": "Parfait, tout tourne correctement", "is_user": False},
        ])
        cs.reindex(force=True)
        # search_similar renvoie [] (semantic_blind) -> seul le balayage exact agit
        res = cs.search("kubernetes", auto_reindex=False)
        assert res, "le mot exact doit ressortir via le balayage full-text"
        assert res[0]["workspace_id"] == ws_id
        assert "kubernetes" in res[0]["excerpt"].lower()


def test_exact_word_other_language_case_insensitive():
    """Mot exact dans une autre langue + casse differente."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        sm = SessionManager(workspaces_dir=str(tmp / "workspaces"))
        vm = _FakeVectorMemory(tmp / "vs", with_reranker=False, semantic_blind=True)
        (tmp / "vs").mkdir(parents=True, exist_ok=True)
        cs = ConversationSearch(session_manager=sm, vector_memory=vm)
        _make_ws(sm, "ES", [
            {"text": "Necesito ayuda con la Configuración del servidor", "is_user": True},
        ])
        cs.reindex(force=True)
        res = cs.search("configuración", auto_reindex=False)  # minuscule
        assert res
        assert "configuración" in res[0]["excerpt"].lower()


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
