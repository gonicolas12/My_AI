"""
Tests pour core/folder_indexer.py (indexation incrementale d'un dossier).

Utilise un faux VectorMemory deterministe (sans modele ML, sans ChromaDB) pour
valider : respect des exclusions (.gitignore + dossiers par defaut), indexation
incrementale (skip si inchange, reindex si modifie, purge si supprime),
detachement de dossier, filtrage par workspace et statut. Aucun embedding reel.
"""

import tempfile
from pathlib import Path

import pytest

from core.folder_indexer import FolderIndexer


# ---------------------------------------------------------------------------
# Faux VectorMemory : mime l'interface utilisee par FolderIndexer
# ---------------------------------------------------------------------------

class _FakeEmbedding(list):
    def tolist(self):
        return list(self)


class _FakeModel:
    def encode(self, text):
        return _FakeEmbedding([float(len(text))])


def _where_match(meta, where):
    """Evalue un filtre ChromaDB ({"$and":[...]} ou {k:v}) contre une metadata."""
    if not where:
        return True
    if "$and" in where:
        return all(_where_match(meta, cond) for cond in where["$and"])
    return all(meta.get(k) == v for k, v in where.items())


class _FakeCollection:
    def __init__(self):
        self.store = {}  # id -> {"document", "metadata"}

    def add(self, ids, embeddings, documents, metadatas):
        for i, _id in enumerate(ids):
            self.store[_id] = {"document": documents[i], "metadata": metadatas[i]}

    def delete(self, ids=None, where=None):
        if ids:
            for _id in ids:
                self.store.pop(_id, None)
            return
        to_del = [k for k, v in self.store.items()
                  if _where_match(v["metadata"], where)]
        for k in to_del:
            del self.store[k]

    def query(self, query_embeddings=None, n_results=5, where=None):
        items = [(k, v) for k, v in self.store.items()
                 if _where_match(v["metadata"], where)]
        items = items[:n_results]
        return {
            "ids": [[k for k, _ in items]],
            "documents": [[v["document"] for _, v in items]],
            "metadatas": [[v["metadata"] for _, v in items]],
            "distances": [[0.1 for _ in items]],
        }

    def count(self):
        return len(self.store)


class _FakeVectorMemory:
    def __init__(self):
        self.embedding_model = _FakeModel()
        self.codebase_collection = _FakeCollection()
        self.reranker = None

    def _collection_for(self, collection_type):
        return self.codebase_collection

    def split_into_chunks(self, text):
        # Decoupage simple par double saut de ligne (1 chunk minimum).
        parts = [p.strip() for p in text.split("\n\n") if p.strip()]
        return parts or ([text.strip()] if text.strip() else [])

    def search_similar(self, query, n_results=5, collection_type="codebase",
                       rerank=True, where=None):
        res = self.codebase_collection.query(n_results=n_results, where=where)
        out = []
        ids = res["ids"][0]
        for i, _id in enumerate(ids):
            out.append({
                "chunk_id": _id,
                "content": res["documents"][0][i],
                "metadata": res["metadatas"][0][i],
                "distance": res["distances"][0][i],
            })
        return out


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def env():
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        vm = _FakeVectorMemory()
        indexer = FolderIndexer(
            vector_memory=vm,
            workspaces_dir=str(tmp / "workspaces"),
        )
        yield tmp, vm, indexer


def _make_project(root: Path):
    """Cree un mini projet avec du bruit a exclure."""
    root.mkdir(parents=True, exist_ok=True)
    (root / "main.py").write_text("print('hello world')\n", encoding="utf-8")
    (root / "utils.py").write_text("def add(a, b):\n    return a + b\n", encoding="utf-8")
    (root / "README.md").write_text("# Projet\n\nDoc du projet.\n", encoding="utf-8")
    # Bruit a exclure par defaut
    (root / "node_modules").mkdir()
    (root / "node_modules" / "lib.js").write_text("export const x = 1;", encoding="utf-8")
    (root / "__pycache__").mkdir()
    (root / "__pycache__" / "main.cpython.pyc").write_text("binarystuff", encoding="utf-8")
    (root / ".git").mkdir()
    (root / ".git" / "config").write_text("[core]", encoding="utf-8")
    return root


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_is_available(env):
    _, _, indexer = env
    assert indexer.is_available() is True


def test_index_excludes_noise(env):
    tmp, vm, indexer = env
    root = _make_project(tmp / "proj")
    res = indexer.index_folder("ws1", str(root))

    assert res["status"] == "success"
    # 3 fichiers utiles (main.py, utils.py, README.md), le reste exclu
    assert res["files_indexed"] == 3
    indexed_files = {m["metadata"]["file_path"]
                     for m in vm.codebase_collection.store.values()}
    assert indexed_files == {"main.py", "utils.py", "README.md"}
    assert not any("node_modules" in f for f in indexed_files)


def test_gitignore_respected(env):
    tmp, vm, indexer = env
    root = _make_project(tmp / "proj")
    (root / ".gitignore").write_text("utils.py\n*.md\n", encoding="utf-8")

    indexer.index_folder("ws1", str(root))
    indexed = {m["metadata"]["file_path"]
               for m in vm.codebase_collection.store.values()}
    assert "utils.py" not in indexed
    assert "README.md" not in indexed
    assert "main.py" in indexed


def test_incremental_skip_unchanged(env):
    tmp, _, indexer = env
    root = _make_project(tmp / "proj")
    indexer.index_folder("ws1", str(root))

    res2 = indexer.index_folder("ws1", str(root))
    assert res2["files_indexed"] == 0
    assert res2["files_skipped"] == 3


def test_incremental_reindex_modified(env):
    tmp, _, indexer = env
    root = _make_project(tmp / "proj")
    indexer.index_folder("ws1", str(root))

    # Modifier le contenu (mtime + taille changent)
    (root / "main.py").write_text(
        "print('changed')\n\nprint('second paragraph')\n", encoding="utf-8")
    res = indexer.index_folder("ws1", str(root))
    assert res["files_indexed"] == 1
    assert res["files_skipped"] == 2


def test_incremental_remove_deleted_file(env):
    tmp, vm, indexer = env
    root = _make_project(tmp / "proj")
    indexer.index_folder("ws1", str(root))

    (root / "utils.py").unlink()
    res = indexer.index_folder("ws1", str(root))
    assert res["files_removed"] == 1
    remaining = {m["metadata"]["file_path"]
                 for m in vm.codebase_collection.store.values()}
    assert "utils.py" not in remaining


def test_search_filters_by_workspace(env):
    tmp, _, indexer = env
    root_a = _make_project(tmp / "projA")
    root_b = tmp / "projB"
    root_b.mkdir()
    (root_b / "other.py").write_text("print('hello world')\n", encoding="utf-8")

    indexer.index_folder("wsA", str(root_a))
    indexer.index_folder("wsB", str(root_b))

    res_a = indexer.search("wsA", "hello world")
    assert res_a
    assert all(r["metadata"]["workspace_id"] == "wsA" for r in res_a)


def test_remove_folder_purges(env):
    tmp, vm, indexer = env
    root = _make_project(tmp / "proj")
    indexer.index_folder("ws1", str(root))
    assert vm.codebase_collection.count() > 0

    removed = indexer.remove_folder("ws1", str(root))
    assert removed is True
    assert vm.codebase_collection.count() == 0
    assert indexer.list_folders("ws1") == []


def test_get_status(env):
    tmp, _, indexer = env
    root = _make_project(tmp / "proj")
    indexer.index_folder("ws1", str(root))

    status = indexer.get_status("ws1")
    assert status["total_files"] == 3
    assert len(status["folders"]) == 1
    assert status["folders"][0]["file_count"] == 3
    # Les noms de fichiers sont exposés (pour l'UI et l'injection de contexte)
    assert set(status["folders"][0]["files"]) == {"main.py", "utils.py", "README.md"}


def test_progress_callback(env):
    tmp, _, indexer = env
    root = _make_project(tmp / "proj")
    seen = []
    indexer.index_folder("ws1", str(root),
                         progress_cb=lambda d, t, p: seen.append((d, t, p)))
    assert seen
    assert seen[-1][0] == seen[-1][1]  # done == total a la fin
