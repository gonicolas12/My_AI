"""
Tests des routes de la barre latérale (interfaces/desktop/api_sidebar.py, folders.py)

Recherche globale, dossiers projet, historique des requêtes et export, sur le
service de chat réel et des briques du moteur simulées : on vérifie le
comportement de l'interface Tk (sidebar.py) repris par le serveur.
"""

import threading
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from core.chat_service import ChatService
from interfaces.desktop.events import EventBus, validate_event
from interfaces.desktop.server import DesktopServer
from test_chat_service import FakeEngine, FakeFileProcessor, ask, wait_for  # pylint: disable=import-error
from test_desktop_server import AUTH, BASE, PORT, FakeApp  # pylint: disable=import-error


class FakeSearch:
    """ConversationSearch : résultats fixes, réindexation comptée."""

    def __init__(self, available=True):
        self.available = available
        self.queries = []
        self.reindexed = 0

    def is_available(self):
        return self.available

    def search(self, query, n_results=10):
        self.queries.append((query, n_results))
        return [{"workspace_id": "ws1", "workspace_name": "Projet API REST",
                 "message_index": 3, "role": "assistant", "timestamp": "2026-10-12T10:00:00",
                 "excerpt": "  Les tuples sont immuables.  ", "score": -2.0, "distance": 0.3}]

    def reindex(self, force=False):
        self.reindexed += 1
        return {"indexed": 4, "messages": 42 if force else 0, "removed": 0}


class FakeHistory:
    """CommandHistory : quelques entrées en mémoire."""

    def __init__(self):
        self.entries = [
            {"id": 1, "query": "Explique les tuples en Python", "is_favorite": 1,
             "timestamp": "2026-10-12T10:00:00"},
            {"id": 2, "query": "Écris un script de tri", "is_favorite": 0,
             "timestamp": "2026-10-12T11:00:00"},
        ]

    def get_recent(self, limit=50):
        return self.entries[:limit]

    def search(self, query, limit=20):
        return [e for e in self.entries if query.lower() in e["query"].lower()][:limit]

    def get_favorites(self):
        return [e for e in self.entries if e["is_favorite"]]

    def toggle_favorite(self, entry_id):
        for entry in self.entries:
            if entry["id"] == entry_id:
                entry["is_favorite"] = 0 if entry["is_favorite"] else 1
                return bool(entry["is_favorite"])
        return False

    def delete(self, entry_id):
        before = len(self.entries)
        self.entries = [e for e in self.entries if e["id"] != entry_id]
        return len(self.entries) != before


class FakeIndexer:
    """FolderIndexer : indexe en publiant sa progression, garde un manifeste en mémoire."""

    def __init__(self):
        self.manifest = {}
        self.gate = threading.Event()
        self.gate.set()
        self.removed = []

    def is_available(self):
        return True

    def index_folder(self, workspace_id, folder_path, force=False, progress_cb=None):
        self.gate.wait(5)
        total = 25
        for done in range(1, total + 1):
            if progress_cb:
                progress_cb(done, total, f"f{done}.py")
        self.manifest.setdefault(workspace_id, {})[folder_path] = {"files": total, "force": force}
        return {"status": "success", "folder": folder_path, "total_files": total,
                "chunks": 120, "files_indexed": total}

    def get_status(self, workspace_id):
        return {"folders": [{"path": path, "file_count": info["files"], "chunks": 120,
                             "indexed_at": "2026-10-13"}
                            for path, info in self.manifest.get(workspace_id, {}).items()]}

    def remove_folder(self, workspace_id, folder_path):
        self.removed.append(folder_path)
        return self.manifest.get(workspace_id, {}).pop(folder_path, None) is not None


@pytest.fixture(name="side")
def side_fixture(tmp_path):
    """Serveur desktop avec recherche, historique et indexeur simulés."""
    engine = FakeEngine(tmp_path / "workspaces")
    engine.search_engine = FakeSearch()
    engine.get_conversation_search = lambda: engine.search_engine
    engine.command_history = FakeHistory()
    engine.indexer = FakeIndexer()
    engine.get_folder_indexer = lambda: engine.indexer
    bus = EventBus()
    events = []
    bus.subscribe(events.append)
    chat = ChatService(engine, bus.publish, file_processor=FakeFileProcessor(),
                       ui_connected=lambda: True)
    chat.start()
    app = FakeApp(chat, bus, engine=engine)
    server = DesktopServer(app)
    server.port = PORT
    client = TestClient(server.fastapi, base_url=BASE)
    # service : nom attendu par ask() de test_chat_service
    yield SimpleNamespace(client=client, chat=chat, service=chat, engine=engine, events=events,
                          tmp_path=tmp_path)
    chat.close()


# ── Recherche globale ───────────────────────────────────────────────────────


def test_global_search_returns_fifteen_results_at_most(side):
    data = side.client.get("/api/search?q=tuples", headers=AUTH).json()
    assert data["available"] is True
    assert data["results"] == [{"workspace_id": "ws1", "workspace_name": "Projet API REST",
                                "message_index": 3, "role": "assistant",
                                "timestamp": "2026-10-12T10:00:00",
                                "excerpt": "Les tuples sont immuables."}]
    assert side.engine.search_engine.queries == [("tuples", 15)]
    assert side.client.get("/api/search?q=%20", headers=AUTH).json()["results"] == []


def test_search_tells_when_it_is_unavailable(side):
    side.engine.search_engine.available = False
    assert side.client.get("/api/search?q=x", headers=AUTH).json() == {
        "available": False, "results": []}
    assert side.client.post("/api/search/reindex", headers=AUTH).json()["available"] is False


def test_reindex_is_forced(side):
    assert side.client.post("/api/search/reindex", headers=AUTH).json() == {
        "available": True, "messages": 42}


# ── Dossiers projet ─────────────────────────────────────────────────────────


def test_folder_attaches_to_a_session_named_after_it_and_reports_progress(side):
    folder = side.tmp_path / "mon-projet"
    folder.mkdir()
    started = side.client.post("/api/folders", json={"path": str(folder)}, headers=AUTH)
    assert started.status_code == 200 and started.json()["verb"] == "Indexation"
    wait_for(side.events, "folders.changed")
    progress = [e["payload"] for e in side.events if e["type"] == "folders.progress"]
    # Comme les notifications de Tk : tous les 10 fichiers, et au dernier
    assert [(p["done"], p["total"]) for p in progress] == [(0, 0), (10, 25), (20, 25), (25, 25)]
    notes = [e["payload"]["message"] for e in side.events if e["type"] == "notification"]
    assert notes == ["⏳ Indexation de 'mon-projet'…",
                     "✅ 'mon-projet' indexé : 25 fichiers, 120 extraits"]
    status = side.client.get("/api/folders", headers=AUTH).json()
    assert status["session"] == side.chat.session_id
    assert status["folders"] == [{"path": str(folder), "name": "mon-projet", "file_count": 25,
                                  "chunks": 120, "indexed_at": "2026-10-13"}]
    assert side.chat.list_sessions()[0]["name"] == "mon-projet"
    state = side.engine.session_manager.load_workspace(side.chat.session_id)
    assert state["attached_folders"] == [str(folder)]
    for event in side.events:
        validate_event(event)


def test_folder_list_survives_the_next_conversation_save(side):
    """L'état de la session (dossiers) et la conversation partagent un fichier."""
    ask(side, "Bonjour")
    folder = side.tmp_path / "docs"
    folder.mkdir()
    side.client.post("/api/folders", json={"path": str(folder)}, headers=AUTH)
    wait_for(side.events, "folders.changed")
    ask(side, "Et ensuite ?")
    state = side.engine.session_manager.load_workspace(side.chat.session_id)
    assert state["attached_folders"] == [str(folder)]
    assert len(state["conversation_history"]) == 4


def test_folder_actions_are_refused_with_their_reason(side):
    missing = side.client.post("/api/folders", headers=AUTH,
                               json={"path": str(side.tmp_path / "absent")})
    assert missing.status_code == 409 and missing.json()["detail"] == "❌ Dossier introuvable"
    reindex = side.client.post("/api/folders/reindex", json={"path": "x"}, headers=AUTH)
    assert reindex.status_code == 409 and reindex.json()["detail"] == "❌ Aucune session active"


def test_folder_reindexes_then_detaches(side):
    folder = side.tmp_path / "code"
    folder.mkdir()
    side.client.post("/api/folders", json={"path": str(folder)}, headers=AUTH)
    wait_for(side.events, "folders.changed")
    side.engine.indexer.gate.clear()
    started = side.client.post("/api/folders/reindex", json={"path": str(folder)}, headers=AUTH)
    assert started.json()["verb"] == "Ré-indexation"
    running = side.client.get("/api/folders", headers=AUTH).json()["running"]
    assert running[0]["path"] == str(folder)
    again = side.client.post("/api/folders/reindex", json={"path": str(folder)}, headers=AUTH)
    assert again.status_code == 409 and "déjà en cours" in again.json()["detail"]
    side.engine.indexer.gate.set()
    wait_for(side.events, "folders.changed", 2)
    assert side.engine.indexer.manifest[side.chat.session_id][str(folder)]["force"] is True

    detached = side.client.post("/api/folders/detach", json={"path": str(folder)}, headers=AUTH)
    assert detached.json() == {"detached": True}
    assert side.client.get("/api/folders", headers=AUTH).json()["folders"] == []
    state = side.engine.session_manager.load_workspace(side.chat.session_id)
    assert state["attached_folders"] == []


# ── Historique ──────────────────────────────────────────────────────────────


def test_history_lists_searches_and_filters_favorites(side):
    recent = side.client.get("/api/history", headers=AUTH).json()["entries"]
    assert [e["id"] for e in recent] == [1, 2]
    assert recent[0] == {"id": 1, "query": "Explique les tuples en Python",
                         "is_favorite": True, "timestamp": "2026-10-12T10:00:00"}
    found = side.client.get("/api/history?q=tri", headers=AUTH).json()["entries"]
    assert [e["id"] for e in found] == [2]
    favorites = side.client.get("/api/history?favorites=true", headers=AUTH).json()["entries"]
    assert [e["id"] for e in favorites] == [1]


def test_history_favorite_and_delete(side):
    assert side.client.post("/api/history/2/favorite", headers=AUTH).json() == {"is_favorite": True}
    assert side.client.delete("/api/history/1", headers=AUTH).json() == {"deleted": True}
    assert [e["id"] for e in side.client.get("/api/history", headers=AUTH).json()["entries"]] == [2]


# ── Export ──────────────────────────────────────────────────────────────────


def test_export_writes_the_chosen_file(side):
    refused = side.client.post("/api/export", json={"format": "markdown"}, headers=AUTH)
    assert refused.status_code == 409
    assert refused.json()["detail"] == "⚠️ Aucune conversation à exporter"
    ask(side, "Bonjour")
    target = side.tmp_path / "exports" / "ma conversation.md"
    target.parent.mkdir()
    path = side.client.post("/api/export", headers=AUTH,
                            json={"format": "markdown", "path": str(target)}).json()["path"]
    assert Path(path) == target
    text = target.read_text(encoding="utf-8")
    assert "Bonjour" in text and "Réponse à « Bonjour »" in text
    bad = side.client.post("/api/export", json={"format": "docx"}, headers=AUTH)
    assert bad.status_code == 422


def test_export_without_a_dialog_goes_to_outputs(side, monkeypatch):
    monkeypatch.chdir(side.tmp_path)
    ask(side, "Bonjour")
    path = side.client.post("/api/export", json={"format": "html"}, headers=AUTH).json()["path"]
    assert Path(path).parent == side.tmp_path / "outputs" / "exports"
    assert Path(path).suffix == ".html" and Path(path).is_file()
