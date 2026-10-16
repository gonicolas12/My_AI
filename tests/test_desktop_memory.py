"""
Tests de la Mémoire de la fenêtre (interfaces/desktop/memory.py, api_memory.py)

MemoryStore simulé : on vérifie le comportement du panneau Tk
(memory_panel.py) repris par le serveur, et que les messages de conversation
modifiés ou supprimés à la source passent par le ChatService.
"""

from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from core.chat_service import MESSAGE_GONE, ChatError
from core.memory_store import MemoryStore
from interfaces.desktop.events import EventBus
from interfaces.desktop.memory import PAGE_SIZE, MemoryPanelError, MemoryService
from interfaces.desktop.server import DesktopServer
from test_desktop_server import AUTH, BASE, PORT, FakeApp  # pylint: disable=import-error


class FakeVectors:
    """VectorMemory : entrées de conversation lues par leur identifiant."""

    def __init__(self, entries):
        self.entries = entries

    def get_entry(self, entry_id, collection_type="document"):
        del collection_type
        return self.entries.get(entry_id)


class FakeSearch:
    """ConversationSearch : réindexations comptées."""

    def __init__(self):
        self.reindexed = []

    def reindex(self, force=False):
        self.reindexed.append(force)


class FakeStore:
    """MemoryStore : 45 faits, deux messages de conversation."""

    describe_provenance = staticmethod(MemoryStore.describe_provenance)

    def __init__(self):
        self.facts = [{"kind": "fact", "id": i, "category": "general", "key": f"fait {i}",
                       "value": f"Contenu {i}", "source": "manual", "confidence": 1.0,
                       "created_at": "2026-10-13T10:00:00", "updated_at": "2026-10-13T10:00:00"}
                      for i in range(1, 46)]
        self.vector_memory = FakeVectors({
            "conv_ws1_0": {"id": "conv_ws1_0", "content": "Bonjour",
                           "metadata": {"workspace_id": "ws1", "message_index": 0,
                                        "workspace_name": "Projet", "role": "user"}},
        })
        self.conversation_search = FakeSearch()
        self.calls = []

    def list_facts(self, query="", category=None, limit=25, offset=0):
        rows = [f for f in self.facts if query.lower() in f["value"].lower()
                and (category is None or f["category"] == category)]
        return rows[offset:offset + limit], len(rows)

    def list_vectors(self, collection_type="document", query="", limit=25, offset=0):
        rows = [{"kind": "vector", "collection": collection_type, "id": key,
                 "content": entry["content"], "metadata": entry["metadata"]}
                for key, entry in self.vector_memory.entries.items()
                if query.lower() in entry["content"].lower()]
        return rows[offset:offset + limit], len(rows)

    def add_fact(self, category, key, value, source="manual"):
        self.calls.append(("add", category, key, value, source))
        return 99

    def update_fact(self, fact_id, value):
        self.calls.append(("update_fact", fact_id, value))
        return True

    def delete_fact(self, fact_id):
        self.calls.append(("delete_fact", fact_id))
        self.facts = [f for f in self.facts if f["id"] != fact_id]
        return True

    def update_vector(self, entry_id, new_text, collection_type="document", at_source=True,
                      metadata=None):
        del metadata
        self.calls.append(("update_vector", entry_id, new_text, collection_type, at_source))
        return True

    def delete_vector(self, entry_id, collection_type="document", at_source=True, metadata=None):
        del metadata
        self.calls.append(("delete_vector", entry_id, collection_type, at_source))
        return True

    def stats(self):
        return {"facts": len(self.facts), "documents": 0, "conversations": 1}


class FakeChat:
    """ChatService : changements à la source notés, ou refusés."""

    def __init__(self):
        self.changes = []
        self.refuse = False

    def change_saved_message(self, session_id, index, text, new_text):
        if self.refuse:
            raise ChatError(MESSAGE_GONE)
        self.changes.append((session_id, index, text, new_text))


@pytest.fixture(name="memory")
def memory_fixture():
    store = FakeStore()
    chat = FakeChat()
    engine = SimpleNamespace(get_memory_store=lambda: store)
    return SimpleNamespace(store=store, chat=chat,
                           service=MemoryService(lambda: engine, lambda: chat))


def test_pages_of_twenty_with_provenance_and_last_page_after_a_delete(memory):
    first = memory.service.page("facts")
    assert len(first["items"]) == PAGE_SIZE and first["total"] == 45 and first["pages"] == 3
    assert first["items"][0]["provenance"].startswith("source : manual  ·  confiance : 100%")
    assert "technical" in first["categories"] and first["stats"]["facts"] == 45

    memory.store.facts = memory.store.facts[:20]
    assert memory.service.page("facts", page=2)["page"] == 0  # au-delà : la dernière page
    assert memory.service.page("facts", query="Contenu 1")["total"] == 11

    conversation = memory.service.page("conversation")["items"][0]
    assert conversation["provenance"].startswith("💼 Projet")
    with pytest.raises(MemoryPanelError, match="Onglet inconnu"):
        memory.service.page("codebase")


def test_a_fact_added_by_hand_takes_its_first_line_as_key(memory):
    assert memory.service.add_fact("preference", "J'aime le thé vert\net le jasmin") == 99
    memory.service.add_fact("inventée", "x" * 120)
    assert memory.store.calls == [
        ("add", "preference", "J'aime le thé vert", "J'aime le thé vert\net le jasmin", "manual"),
        ("add", "general", "x" * 80, "x" * 120, "manual"),
    ]
    with pytest.raises(MemoryPanelError, match="Le contenu ne peut pas être vide"):
        memory.service.add_fact("general", "   ")


def test_conversation_entries_change_at_their_source_through_the_chat(memory):
    memory.service.update("conversation", "conv_ws1_0", "Bonjour à tous")
    memory.service.delete("conversation", "conv_ws1_0", at_source=True)
    assert memory.chat.changes == [("ws1", 0, "Bonjour", "Bonjour à tous"),
                                   ("ws1", 0, "Bonjour", None)]
    assert memory.store.conversation_search.reindexed == [False, False]

    # Index seul, sans toucher à la conversation (« sinon réapparaît au prochain réindex »)
    memory.service.delete("conversation", "conv_ws1_0", at_source=False)
    assert memory.store.calls[-1] == ("delete_vector", "conv_ws1_0", "conversation", False)

    # Message introuvable : modification refusée ; suppression : l'index au moins
    memory.chat.refuse = True
    with pytest.raises(MemoryPanelError, match="introuvable"):
        memory.service.update("conversation", "conv_ws1_0", "x")
    memory.service.delete("conversation", "conv_ws1_0", at_source=True)
    assert memory.store.calls[-1] == ("delete_vector", "conv_ws1_0", "conversation", False)


def test_facts_and_documents_change_in_place(memory):
    memory.service.update("facts", "7", "Nouveau contenu")
    memory.service.update("document", "doc_chunk_0", "Paragraphe corrigé")
    memory.service.delete("facts", "7")
    assert memory.store.calls == [
        ("update_fact", 7, "Nouveau contenu"),
        ("update_vector", "doc_chunk_0", "Paragraphe corrigé", "document", False),
        ("delete_fact", 7),
    ]


def test_memory_routes(memory):
    bus = EventBus()
    events = []
    bus.subscribe(events.append)
    app = FakeApp(None, bus)
    app.memory = memory.service
    app.notify = lambda level, message: bus.publish("notification",
                                                    {"level": level, "message": message})
    server = DesktopServer(app)
    server.port = PORT
    client = TestClient(server.fastapi, base_url=BASE)

    page = client.get("/api/memory?tab=facts&page=1", headers=AUTH).json()
    assert page["page"] == 1 and len(page["items"]) == 20
    assert client.post("/api/memory/facts", headers=AUTH,
                       json={"category": "decision", "text": "On garde React"}).json() == {"id": 99}
    assert client.put("/api/memory/facts/3", headers=AUTH, json={"text": "Révisé"}).status_code == 200
    removed = client.delete("/api/memory/conversation/conv_ws1_0?at_source=false", headers=AUTH)
    assert removed.status_code == 200
    empty = client.put("/api/memory/facts/3", headers=AUTH, json={"text": " "})
    assert empty.status_code == 409 and "vide" in empty.json()["detail"]
    messages = [e["payload"]["message"] for e in events if e["type"] == "notification"]
    assert messages == ["✅ Fait ajouté", "✅ Modifié", "🗑️ Supprimé"]

    memory.service._engine = lambda: None  # pylint: disable=protected-access
    gone = client.get("/api/memory", headers=AUTH)
    assert gone.status_code == 409 and gone.json()["detail"] == (
        "Mémoire indisponible (base non initialisée).")
