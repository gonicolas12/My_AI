"""
Tests de la Mémoire de la fenêtre (interfaces/desktop/memory.py, api_memory.py)

MemoryStore simulé : on vérifie le comportement du panneau Tk
(memory_panel.py) repris par le serveur, et que les messages de conversation
modifiés ou supprimés à la source passent par le ChatService.
"""

import os
import time
from datetime import datetime
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from core.chat_service import MESSAGE_GONE, ChatError
from core.document_memory import DocumentReadError, folder_document_id, image_document_id
from core.i18n import tr
from core.memory_store import MemoryStore
from interfaces.desktop import files as local_files
from interfaces.desktop.events import EventBus, payload_model
from interfaces.desktop.memory import (FOLDER_FILES_MAX, PAGE_SIZE, MemoryPanelError,
                                       MemoryService, clean_folder_name, clean_relative_path)
from interfaces.desktop.memory_files import OriginalFiles, safe_file_name
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
        self.docs = {}  # identifiant → document rangé (nom, contenu, dossier, date)
        self.clock = 0
        self.options = []  # (document_id, keep) de chaque add_document
        self.deleted = []  # documents supprimés (cible d'une mise à jour, suppression)
        self.pruned = []  # (dossier, fichiers retirés) de chaque prune_folder

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

    def add_document(self, content, name, metadata=None, document_id=None, keep=True):
        """Comme MemoryStore : même nom et même contenu (ou même identifiant imposé) :
        doublon ; deux fichiers du même nom restent ; échec pour « panne »."""
        self.calls.append(("add_document", name, content, metadata))
        self.options.append((document_id, keep))
        if "panne" in name:
            return {"status": "error", "document_id": "", "chunks": 0,
                    "error": "ChromaDB indisponible"}
        doc_id = document_id or f"doc:{name}:{content}"
        if doc_id in self.docs:
            return {"status": "duplicate", "document_id": doc_id, "chunks": 3, "error": ""}
        meta = metadata or {}
        self.clock += 1
        self.docs[doc_id] = {
            "id": doc_id, "name": name, "label": name.split("/", 1)[-1] if meta.get("folder")
            else name, "content": content, "folder": meta.get("folder"),
            "folder_key": meta.get("folder_id"), "created": f"2026-11-17T10:{self.clock:02d}:00",
            "source": meta.get("source"), "type": meta.get("type")}
        return {"status": "added", "document_id": doc_id, "chunks": 3, "error": ""}

    def named(self, name):
        """Documents rangés sous ce nom (tests)."""
        return [doc for doc in self.docs.values() if doc["name"] == name]

    def has_document(self, document_id):
        return document_id in self.docs

    def keep_document(self, document_id):
        self.calls.append(("keep_document", document_id))
        return 3

    def delete_document(self, document_id):
        self.deleted.append(document_id)
        return 3 if self.docs.pop(document_id, None) else 0

    def remove_other_versions(self, name, document_id, folder_id=None):
        stale = [key for key, doc in self.docs.items()
                 if doc["name"] == name and key != document_id
                 and (folder_id is None or doc["folder_key"] == folder_id)]
        for key in stale:
            del self.docs[key]
        return 3 * len(stale)

    def document_index(self):
        return sorted(self.docs.values(), key=lambda doc: doc["created"], reverse=True)

    def prune_folder(self, folder_id, keep):
        stale = sorted(doc["name"] for doc in self.docs.values()
                       if doc["folder_key"] == folder_id and doc["name"] not in set(keep))
        self.docs = {key: doc for key, doc in self.docs.items()
                     if not (doc["folder_key"] == folder_id and doc["name"] in stale)}
        self.pruned.append((folder_id, stale))
        return len(stale)

    def stats(self):
        return {"facts": len(self.facts), "documents": 0, "conversations": 1}


GROUP = {"kind": "document", "id": "rapport_1", "name": "rapport.pdf", "label": "rapport.pdf",
         "folder": None, "chunks": 120, "created": "2026-11-17T14:32:00", "type": "PDF",
         "source": "manual"}


class GroupedStore(FakeStore):
    """MemoryStore avec l'onglet Documents groupé : un document de 120 morceaux."""

    def list_document_groups(self, query="", limit=25, offset=0):
        self.calls.append(("groups", query, limit, offset))
        return [dict(GROUP)], 1

    def delete_document(self, document_id):
        self.calls.append(("delete_document", document_id))
        return 0 if document_id == "absent" else 120

    def delete_folder(self, name):
        self.calls.append(("delete_folder", name))
        return 0 if name == "absent" else 5


class FakeChat:
    """ChatService : changements à la source notés, ou refusés."""

    def __init__(self):
        self.changes = []
        self.refuse = False

    def change_saved_message(self, session_id, index, text, new_text):
        if self.refuse:
            raise ChatError(tr(MESSAGE_GONE))
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


@pytest.fixture(name="grouped")
def grouped_fixture():
    store = GroupedStore()
    engine = SimpleNamespace(get_memory_store=lambda: store)
    return SimpleNamespace(store=store, service=MemoryService(lambda: engine, lambda: None))


def test_documents_tab_lists_documents_and_deletes_them_whole(grouped):
    """Onglet Documents : un élément par document (ses morceaux restent internes)."""
    view = grouped.service.page("document", query=" rapport ")
    assert view["items"] == [GROUP] and view["total"] == 1 and view["pages"] == 1
    assert grouped.store.calls[-1] == ("groups", "rapport", PAGE_SIZE, 0)
    assert not hasattr(grouped.service, "document_chunks")

    assert grouped.service.delete_document("rapport_1") == 120
    assert grouped.service.delete_folder("site") == 5
    with pytest.raises(MemoryPanelError, match="Échec de la suppression"):
        grouped.service.delete_document("absent")
    with pytest.raises(MemoryPanelError, match="Échec de la suppression"):
        grouped.service.delete_folder("absent")


def test_document_group_routes(grouped):
    bus = EventBus()
    events = []
    bus.subscribe(events.append)
    app = FakeApp(None, bus)
    app.memory = grouped.service
    app.notify = lambda level, message: bus.publish("notification",
                                                    {"level": level, "message": message})
    server = DesktopServer(app)
    server.port = PORT
    client = TestClient(server.fastapi, base_url=BASE)

    # Les morceaux (chunks) restent internes : aucune route ne les liste
    assert client.get("/api/memory/chunks?document=rapport_1", headers=AUTH).status_code == 404
    # Déjà en mémoire ? (la fenêtre le demande avant d'envoyer), avec la date
    rapport = grouped.store.add_document("v1", "rapport.pdf", {"source": "manual"})
    grouped.store.add_document("a", "site/a.md", {"folder": "site", "folder_id": "s1"})
    existing = client.post("/api/memory/documents/existing", headers=AUTH,
                           json={"names": ["C:\\docs\\rapport.pdf", "neuf.md"],
                                 "folders": ["site", "autre"]}).json()
    assert existing == {
        "files": [{"name": "C:\\docs\\rapport.pdf", "target": rapport["document_id"],
                   "created": "2026-11-17T10:01:00", "count": 1}],
        "folders": [{"name": "site", "target": "s1", "created": "2026-11-17T10:02:00",
                     "count": 1}]}
    assert client.delete("/api/memory/documents?document=rapport_1",
                         headers=AUTH).status_code == 200
    # Un dossier se supprime par sa clé : un autre du même nom resterait
    assert client.delete("/api/memory/folders?folder=site", headers=AUTH).status_code == 200
    absent = client.delete("/api/memory/folders?folder=absent", headers=AUTH)
    assert absent.status_code == 409 and "suppression" in absent.json()["detail"]
    assert ("delete_document", "rapport_1") in grouped.store.calls
    assert ("delete_folder", "site") in grouped.store.calls
    messages = [e["payload"]["message"] for e in events if e["type"] == "notification"]
    assert messages == ["🗑️ Supprimé", "🗑️ Supprimé"]


# ── Documents ajoutés à la main (bouton Ajouter de l'onglet Documents) ──────


def _idle(service, timeout=10.0):
    """Attend la fin de la file des documents ajoutés."""
    deadline = time.monotonic() + timeout
    while service.jobs() or service._worker is not None:  # pylint: disable=protected-access
        assert time.monotonic() < deadline, "documents toujours en cours"
        time.sleep(0.02)


def _notifications(events):
    return [payload["message"] for kind, payload in events if kind == "notification"]


@pytest.fixture(name="documents")
def documents_fixture(tmp_path):
    store = FakeStore()
    events = []
    reads = []

    def read_file_for_context(path):
        """Processeurs du modèle : le texte d'une pièce jointe du chat."""
        reads.append(os.path.basename(path))
        return {"content": f"Contenu de {os.path.basename(path)}", "processor_used": "Code"}

    engine = SimpleNamespace(get_memory_store=lambda: store,
                             local_ai=SimpleNamespace(read_file_for_context=read_file_for_context))
    service = MemoryService(lambda: engine, lambda: None,
                            publish=lambda kind, payload: events.append((kind, payload)))

    def write(name, text="x"):
        path = tmp_path / name
        path.write_text(text, encoding="utf-8")
        return str(path)

    return SimpleNamespace(store=store, events=events, reads=reads, service=service,
                           write=write, tmp=tmp_path)


def test_documents_added_by_hand_are_read_and_stored_in_order(documents):
    note, plan = documents.write("note.txt"), documents.write("plan.py", "print(1)")
    archive = documents.write("sauvegarde.zip")
    result = documents.service.add_documents(
        [note, plan, note, archive, str(documents.tmp / "absent.pdf")])
    assert [job["name"] for job in result["jobs"]] == ["note.txt", "plan.py"]  # une seule fois
    assert result["refused"] == [
        {"name": "sauvegarde.zip", "message": "❌ Format non supporté : .zip"},
        {"name": "absent.pdf", "message": "❌ Fichier introuvable : absent.pdf"}]
    _idle(documents.service)

    assert documents.reads == ["note.txt", "plan.py"]  # un à la fois, dans l'ordre
    assert [call for call in documents.store.calls if call[0] == "add_document"] == [
        ("add_document", "note.txt", "Contenu de note.txt", {"source": "manual", "type": "Code"}),
        ("add_document", "plan.py", "Contenu de plan.py", {"source": "manual", "type": "Code"})]
    assert _notifications(documents.events) == [
        "📄 « note.txt » mis en mémoire", "📄 « plan.py » mis en mémoire"]
    files = [[(job["name"], job["state"]) for job in payload["jobs"]]
             for kind, payload in documents.events if kind == "memory.jobs"]
    assert files[0] == [("note.txt", "queued"), ("plan.py", "queued")]
    assert [("note.txt", "reading"), ("plan.py", "queued")] in files and files[-1] == []
    assert [payload for kind, payload in documents.events
            if kind == "memory.changed"] == [{"tab": "document"}] * 2
    for kind, payload in documents.events:  # protocole de la fenêtre (events.py)
        payload_model(kind).model_validate(payload)
    assert documents.service.page("document")["jobs"] == []


def test_every_outcome_of_a_document_is_notified(documents, monkeypatch):
    """Déjà à jour, illisible, échec du rangement : chacun son message."""
    # Sans moteur prêt, le lecteur du chat (utils.file_processor) lit les fichiers
    engine = documents.service._engine()  # pylint: disable=protected-access
    monkeypatch.setattr(engine, "local_ai", None)
    note = documents.write("note.txt")
    documents.service.add_documents([note])
    _idle(documents.service)
    documents.service.add_documents([note, documents.write("panne.md"),
                                     documents.write("vide.txt", " ")])
    _idle(documents.service)
    assert _notifications(documents.events)[1:] == [
        "ℹ️ « note.txt » est déjà en mémoire, à l'identique",
        "❌ « panne.md » non mis en mémoire : ChromaDB indisponible",
        "❌ « vide.txt » non mis en mémoire : Le fichier vide.txt semble vide ou illisible"]


def test_an_image_shows_its_description_step(documents, monkeypatch):
    image = documents.tmp / "tableau.png"
    image.write_bytes(b"png")
    stages = []

    def describe(path, local_ai=None, file_processor=None, on_stage=None):
        del local_ai, file_processor
        stages.append([job["state"] for job in documents.service.jobs()])
        on_stage("describing")
        stages.append([job["state"] for job in documents.service.jobs()])
        return f"Description de {os.path.basename(path)}", "Image"

    monkeypatch.setattr("interfaces.desktop.memory.read_document", describe)
    documents.service.add_documents([str(image)])
    _idle(documents.service)
    assert stages == [["reading"], ["describing"]]
    assert documents.store.calls[-1] == ("add_document", "tableau.png",
                                         "Description de tableau.png",
                                         {"source": "manual", "type": "Image"})


def _png(path, color=(200, 120, 40)):
    Image.new("RGB", (16, 16), color).save(path)
    return str(path)


def test_an_image_added_twice_by_hand_is_described_once(documents, monkeypatch):
    """Rangée sous l'empreinte de son fichier : la même image, sous un autre
    nom, est « déjà en mémoire » sans nouvelle description."""
    described = []

    def describe(path, local_ai=None, file_processor=None, on_stage=None):
        del local_ai, file_processor, on_stage
        described.append(os.path.basename(path))
        return "Description de l'image :\nUn graphique en barres", "Image"

    monkeypatch.setattr("interfaces.desktop.memory.read_document", describe)
    image = _png(documents.tmp / "graphique.png")
    documents.service.add_documents([image])
    _idle(documents.service)
    copy = documents.tmp / "graphique (2).png"
    copy.write_bytes((documents.tmp / "graphique.png").read_bytes())
    documents.service.add_documents([str(copy)])
    _idle(documents.service)

    assert described == ["graphique.png"]
    assert documents.store.options == [(image_document_id(image), True)]
    assert documents.store.calls[-1] == ("keep_document", image_document_id(image))
    assert _notifications(documents.events) == [
        "📄 « graphique.png » mis en mémoire",
        "ℹ️ « graphique (2).png » est déjà en mémoire, à l'identique"]


def test_images_sent_in_the_chat_are_stored_once_the_answer_is_over(documents, monkeypatch):
    """Images envoyées dans le chat : « en attente » pendant la réponse, puis
    décrites et rangées, sans notification (comme les documents joints)."""
    chat = SimpleNamespace(busy=True)
    documents.service._chat = lambda: chat  # pylint: disable=protected-access
    monkeypatch.setattr(MemoryService, "CHAT_POLL", 0.01)
    described = []

    def describe(path, local_ai=None, file_processor=None, on_stage=None):
        del local_ai, file_processor
        described.append((os.path.basename(path), chat.busy))
        on_stage("describing")
        return "Description de l'image :\nUn tableau blanc", "Image"

    monkeypatch.setattr("interfaces.desktop.memory.read_document", describe)
    image = _png(documents.tmp / "a1b2c3d4e5f60718_tableau.png")  # envoi du mobile
    documents.service.remember_chat_images([image, str(documents.tmp / "absente.png"),
                                            documents.write("note.txt")])
    time.sleep(0.2)
    assert [(job["name"], job["state"]) for job in documents.service.jobs()] == [
        ("tableau.png", "queued")]
    assert not described  # pas pendant la réponse
    chat.busy = False
    _idle(documents.service)

    assert described == [("a1b2c3d4e5f60718_tableau.png", False)]
    assert documents.store.calls[-1] == ("add_document", "tableau.png",
                                         "Description de l'image :\nUn tableau blanc",
                                         {"type": "Image"})
    assert documents.store.options == [(image_document_id(image), False)]
    assert _notifications(documents.events) == []
    assert [payload for kind, payload in documents.events
            if kind == "memory.changed"] == [{"tab": "document"}]

    # La même image renvoyée sous un autre nom (capture collée) : ni décrite ni rangée
    copy = documents.tmp / "clipboard_image.png"
    copy.write_bytes((documents.tmp / "a1b2c3d4e5f60718_tableau.png").read_bytes())
    documents.service.remember_chat_images([str(copy)])
    _idle(documents.service)
    assert len(described) == 1 and len(documents.store.options) == 1
    assert _notifications(documents.events) == []


def test_a_chat_image_with_nothing_to_keep_is_dropped_quietly(documents, monkeypatch):
    def nothing(path, local_ai=None, file_processor=None, on_stage=None):
        del path, local_ai, file_processor, on_stage
        raise DocumentReadError("rien à retenir")

    def broken(path, local_ai=None, file_processor=None, on_stage=None):
        del path, local_ai, file_processor, on_stage
        raise RuntimeError("Ollama a planté")

    monkeypatch.setattr("interfaces.desktop.memory.read_document", nothing)
    documents.service.remember_chat_images([_png(documents.tmp / "flou.png")])
    _idle(documents.service)
    monkeypatch.setattr("interfaces.desktop.memory.read_document", broken)
    documents.service.remember_chat_images([_png(documents.tmp / "autre.png", (1, 2, 3))])
    _idle(documents.service)
    assert _notifications(documents.events) == []
    assert not documents.store.options
    documents.service._engine = lambda: None  # pylint: disable=protected-access
    documents.service.remember_chat_images([_png(documents.tmp / "sans_moteur.png")])
    assert documents.service.jobs() == []  # mémoire indisponible : rien en file


def test_memory_unavailable_refuses_documents(documents):
    documents.service._engine = lambda: None  # pylint: disable=protected-access
    with pytest.raises(MemoryPanelError, match="Mémoire indisponible"):
        documents.service.add_documents([documents.write("note.txt")])
    assert documents.service.jobs() == []


# ── Dossier déposé sur l'onglet Documents ───────────────────────────────────


def test_a_dropped_folder_is_stored_under_its_name_with_one_summary(documents):
    """Chaque fichier devient « dossier/chemin » (métadonnées folder et folder_id) ;
    la file n'en montre qu'une ligne ; un seul bilan à la fin."""
    files = [(documents.write("readme.md", "# Site"), "README.md"),
             (documents.write("app.py", "print(1)"), "src\\app.py"),
             (documents.write("panne.py"), "src/panne.py"),  # échec du rangement
             (documents.write("logo.zip"), "logo.zip")]  # format non pris en charge : ignoré
    result = documents.service.add_folder("site", files, temporary=False)
    assert result["refused"] == []
    assert [(job["name"], job["folder"], job["files"], job["current"])
            for job in result["jobs"]] == [("site", "site", 3, None)]
    _idle(documents.service)

    added = [call for call in documents.store.calls if call[0] == "add_document"]
    assert [call[1] for call in added] == ["site/README.md", "site/src/app.py",
                                           "site/src/panne.py"]
    folder_id = added[0][3]["folder_id"]
    assert added[0][3] == {"source": "manual", "type": "Code", "folder": "site",
                           "folder_id": folder_id}
    # Identité d'un fichier du dossier : ce dossier-là, son chemin, son contenu
    assert documents.store.options[0] == (
        folder_document_id(files[0][0], f"{folder_id}/README.md"), True)
    assert _notifications(documents.events) == [
        "📁 « site » : 2 fichiers ajoutés, 1 fichier en échec (src/panne.py)."]
    levels = [payload["level"] for kind, payload in documents.events if kind == "notification"]
    assert levels == ["warning"]

    lines = [payload["jobs"] for kind, payload in documents.events if kind == "memory.jobs"]
    assert lines[0] == [{"id": result["jobs"][0]["id"], "name": "site", "state": "queued",
                         "folder": "site", "files": 3, "current": None}]
    assert [{**line[0], "id": ""} for line in lines if line and line[0]["current"]][0] == {
        "id": "", "name": "site", "state": "reading", "folder": "site", "files": 3,
        "current": "README.md"}
    # Commencé, le dossier reste « en lecture » entre deux fichiers (pas de clignotement)
    assert "queued" not in [line[0]["state"] for line in lines[1:] if line]
    assert [line[0]["files"] for line in lines if line][-1] == 1
    assert lines[-1] == []
    for kind, payload in documents.events:  # protocole de la fenêtre (events.py)
        payload_model(kind).model_validate(payload)

    # Redéposé, mis à jour (sa cible) : les fichiers inchangés ne sont pas relus
    reads = len(documents.reads)
    documents.service.add_folder("site", files[:2], temporary=False, target=folder_id)
    _idle(documents.service)
    assert len(documents.reads) == reads
    assert _notifications(documents.events)[-1] == "📁 « site » : 2 fichiers déjà à jour."

    # Redéposé, « garder les deux » (sans cible) : un second dossier « site »
    documents.service.add_folder("site", files[:2], temporary=False)
    _idle(documents.service)
    assert _notifications(documents.events)[-1] == "📁 « site » : 2 fichiers ajoutés."
    keys = {doc["folder_key"] for doc in documents.store.docs.values()}
    assert len(keys) == 2 and folder_id in keys
    assert len(documents.store.named("site/README.md")) == 2
    # Une cible inconnue (dossier supprimé depuis) : un nouveau dossier
    documents.service.add_folder("site", files[:1], temporary=False, target="disparu")
    _idle(documents.service)
    assert len({doc["folder_key"] for doc in documents.store.docs.values()}) == 3


def test_a_dropped_folder_is_refused_when_empty_or_too_big(documents):
    with pytest.raises(MemoryPanelError, match="Aucun fichier à mettre en mémoire dans « vide »"):
        documents.service.add_folder("vide", [(documents.write("a.zip"), "a.zip")], False)
    many = [(documents.write("note.md"), f"note_{index}.md")
            for index in range(FOLDER_FILES_MAX + 1)]
    with pytest.raises(MemoryPanelError, match=f"plus de {FOLDER_FILES_MAX} fichiers"):
        documents.service.add_folder("enorme", many, False)
    assert documents.service.jobs() == []
    assert clean_folder_name(" a/b\\c\n") == "a b c" and clean_folder_name("\t") == "folder"
    assert clean_relative_path("../x/./y\\z.py") == "x/y/z.py"
    assert clean_relative_path("..") == ""


# ── Fichier ou dossier remis sous un nom déjà pris ─────────────────────────


def test_existing_files_and_folders_are_found_by_name(documents):
    """La fenêtre demande lesquels portent un nom déjà pris, avant d'envoyer : un
    chemin vaut son nom, un dossier son nom nettoyé, chacun une fois, tel
    qu'envoyé, avec le plus récent du même nom (sa cible, sa date) et leur
    nombre. Un fichier d'un dossier déposé ne compte pas comme fichier seul."""
    store = documents.store
    store.add_document("v1", "rapport.pdf", {"source": "manual"})
    newest = store.add_document("v2", "rapport.pdf", {})["document_id"]  # joint au chat
    store.add_document("a", "site/a.md", {"folder": "site", "folder_id": "s1"})
    store.add_document("a2", "site/a.md", {"folder": "site", "folder_id": "s2"})
    store.add_document("b", "si te/b.md", {"folder": "si te", "folder_id": "t1"})
    found = documents.service.existing(
        ["C:\\docs\\rapport.pdf", "/home/moi/rapport.pdf", "neuf.md", "rapport.pdf",
         "rapport.pdf", "a.md"],
        ["site", "si/te", "autre", "site"])
    rapport = {"target": newest, "created": "2026-11-17T10:02:00", "count": 2}
    assert found["files"] == [{"name": "C:\\docs\\rapport.pdf", **rapport},
                              {"name": "/home/moi/rapport.pdf", **rapport},
                              {"name": "rapport.pdf", **rapport}]
    assert found["folders"] == [
        {"name": "site", "target": "s2", "created": "2026-11-17T10:04:00", "count": 2},
        {"name": "si/te", "target": "t1", "created": "2026-11-17T10:05:00", "count": 1}]


@pytest.fixture(name="texts")
def texts_fixture(monkeypatch):
    """Lecteur simulé : le texte de chaque lecture, dans l'ordre."""
    queue = []

    def read(path, local_ai=None, file_processor=None, on_stage=None):
        del path, local_ai, file_processor, on_stage
        return queue.pop(0), "Code"

    monkeypatch.setattr("interfaces.desktop.memory.read_document", read)
    return queue


def test_two_files_with_the_same_name_both_stay(documents, texts):
    """Sans « Mettre à jour », un fichier du même nom s'ajoute à côté : c'est à
    l'utilisateur de s'organiser, leur date les distingue. Même contenu : pas
    de seconde copie."""
    texts.extend(["Rapport de l'atelier A", "Rapport de l'atelier B", "Rapport de l'atelier B"])
    note = documents.write("rapport.md")
    for _ in range(3):
        documents.service.add_documents([note])
        _idle(documents.service)
    assert [doc["content"] for doc in documents.store.named("rapport.md")] == [
        "Rapport de l'atelier A", "Rapport de l'atelier B"]
    assert not documents.store.deleted
    assert _notifications(documents.events) == [
        "📄 « rapport.md » mis en mémoire", "📄 « rapport.md » mis en mémoire",
        "ℹ️ « rapport.md » est déjà en mémoire, à l'identique"]


def test_update_replaces_the_chosen_document_only(documents, texts):
    """« Mettre à jour » : la nouvelle version remplace la cible choisie (le plus
    récent du même nom), et elle seule ; l'autre du même nom reste."""
    texts.extend(["Version 1", "Autre fichier", "Version 2", "Version 2"])
    note = documents.write("rapport.md")
    documents.service.add_documents([note])
    _idle(documents.service)
    documents.service.add_documents([note])  # gardé à côté
    _idle(documents.service)
    first, other = (doc["id"] for doc in documents.store.named("rapport.md"))
    documents.service.add_documents([note], targets={"rapport.md": first})
    _idle(documents.service)
    assert documents.store.deleted == [first]
    assert sorted(doc["content"] for doc in documents.store.named("rapport.md")) == [
        "Autre fichier", "Version 2"]
    assert _notifications(documents.events)[-1] == "🔄 « rapport.md » mis à jour dans la mémoire"
    levels = [payload["level"] for kind, payload in documents.events if kind == "notification"]
    assert levels[-1] == "success"

    # Même contenu que sa cible : rien à remplacer
    current = next(doc["id"] for doc in documents.store.named("rapport.md")
                   if doc["content"] == "Version 2")
    documents.service.add_documents([note], targets={"rapport.md": current})
    _idle(documents.service)
    assert documents.store.deleted == [first] and other in documents.store.docs
    assert _notifications(documents.events)[-1] == (
        "ℹ️ « rapport.md » est déjà en mémoire, à l'identique")


def test_a_folder_dropped_again_is_updated(documents):
    """Dossier redéposé, mis à jour (sa cible) : fichiers inchangés gardés (pas
    relus), modifiés remplacés, nouveaux ajoutés, et ceux qu'il ne contient
    plus retirés ; un autre dossier du même nom n'est pas touché."""
    readme = documents.write("readme.md", "# Site")
    app = documents.write("app.py", "print(1)")
    notes = documents.write("notes.txt", "Réunion")
    documents.service.add_folder("site", [(readme, "README.md"), (app, "src/app.py"),
                                          (notes, "notes.txt")], temporary=False)
    _idle(documents.service)
    assert _notifications(documents.events)[-1] == "📁 « site » : 3 fichiers ajoutés."
    folder_id = next(iter(documents.store.docs.values()))["folder_key"]
    # Un autre dossier « site », gardé à côté
    documents.store.add_document("autre", "site/notes.txt", {"folder": "site",
                                                             "folder_id": "autre_site"})
    reads = len(documents.reads)

    documents.write("app.py", "print(2)")  # modifié
    plan = documents.write("plan.md", "# Plan")  # nouveau
    documents.service.add_folder("site", [(readme, "README.md"), (app, "src/app.py"),
                                          (plan, "plan.md")], temporary=False,
                                 target=folder_id)
    _idle(documents.service)
    assert documents.reads[reads:] == ["app.py", "plan.md"]  # README inchangé : pas relu
    assert documents.store.pruned[-1] == (folder_id, ["site/notes.txt"])
    mine = sorted(doc["name"] for doc in documents.store.docs.values()
                  if doc["folder_key"] == folder_id)
    assert mine == ["site/README.md", "site/plan.md", "site/src/app.py"]
    assert [doc["folder_key"] for doc in documents.store.named("site/notes.txt")] == [
        "autre_site"]
    assert _notifications(documents.events)[-1] == (
        "📁 « site » : 1 fichier ajouté, 1 fichier mis à jour, 1 fichier déjà à jour, "
        "1 fichier retiré.")
    levels = [payload["level"] for kind, payload in documents.events if kind == "notification"]
    assert levels[-1] == "success"


def test_document_routes(documents, monkeypatch, tmp_path):
    monkeypatch.setattr(local_files, "UPLOAD_DIR", tmp_path / "envois")
    app = FakeApp(None, EventBus())
    app.memory = documents.service
    server = DesktopServer(app)
    server.port = PORT
    client = TestClient(server.fastapi, base_url=BASE)

    added = client.post("/api/memory/documents", headers=AUTH,
                        json={"paths": [documents.write("note.txt"), "C:/absent.pdf"]})
    assert added.status_code == 200
    assert [job["name"] for job in added.json()["jobs"]] == ["note.txt"]
    assert [item["name"] for item in added.json()["refused"]] == ["absent.pdf"]
    _idle(documents.service)

    # Navigateur : copie à part, lue puis effacée ; un format refusé n'est pas gardé
    sent = client.post("/api/memory/documents/upload", headers=AUTH,
                       files={"file": ("compte-rendu.md", b"# Point du lundi", "text/markdown")})
    assert [job["name"] for job in sent.json()["jobs"]] == ["compte-rendu.md"]
    _idle(documents.service)
    assert documents.reads[-1] == "compte-rendu.md"
    refused = client.post("/api/memory/documents/upload", headers=AUTH,
                          files={"file": ("archive.zip", b"PK", "application/zip")})
    assert refused.status_code == 200 and refused.json()["jobs"] == []
    assert not list((tmp_path / "envois").rglob("*.*"))
    # « Mettre à jour » : le document remplacé part avec le fichier (replace)
    old = documents.store.add_document("ancien", "planning.md", {"source": "manual"})
    client.post("/api/memory/documents/upload", headers=AUTH,
                data={"replace": old["document_id"]},
                files={"file": ("planning.md", b"# Planning", "text/markdown")})
    _idle(documents.service)
    assert documents.store.deleted[-1] == old["document_id"]
    assert [doc["content"] for doc in documents.store.named("planning.md")] == [
        "Contenu de planning.md"]

    # Dossier déposé : chaque fichier et son chemin dedans, lus puis effacés
    folder = client.post(
        "/api/memory/documents/folder", headers=AUTH,
        data={"folder": "notes", "paths": ["a.md", "sous/b.md"]},
        files=[("files", ("a.md", b"# A", "text/markdown")),
               ("files", ("b.md", b"# B", "text/markdown"))])
    assert folder.status_code == 200
    assert [(job["name"], job["files"]) for job in folder.json()["jobs"]] == [("notes", 2)]
    _idle(documents.service)
    assert documents.reads[-2:] == ["a.md", "b.md"]
    assert [call[1] for call in documents.store.calls if call[0] == "add_document"][-2:] == [
        "notes/a.md", "notes/sous/b.md"]
    assert not list((tmp_path / "envois").rglob("*.*"))
    # Redéposé, « Mettre à jour » : ce dossier-là (target), sous-dossier retiré
    notes_id = documents.store.named("notes/a.md")[0]["folder_key"]
    client.post("/api/memory/documents/folder", headers=AUTH,
                data={"folder": "notes", "paths": ["a.md"], "target": notes_id},
                files=[("files", ("a.md", b"# A", "text/markdown"))])
    _idle(documents.service)
    assert documents.store.pruned[-1] == (notes_id, ["notes/sous/b.md"])
    assert not list((tmp_path / "envois").rglob("*.*"))
    mismatch = client.post("/api/memory/documents/folder", headers=AUTH,
                           data={"folder": "notes", "paths": ["a.md"]},
                           files=[("files", ("a.md", b"# A", "text/markdown")),
                                  ("files", ("b.md", b"# B", "text/markdown"))])
    assert mismatch.status_code == 422
    monkeypatch.setattr("interfaces.desktop.api_memory.FOLDER_FILES_MAX", 1)
    too_big = client.post("/api/memory/documents/folder", headers=AUTH,
                          data={"folder": "notes", "paths": ["a.md", "b.md"]},
                          files=[("files", ("a.md", b"# A", "text/markdown")),
                                 ("files", ("b.md", b"# B", "text/markdown"))])
    assert too_big.status_code == 413 and "plus de 1 fichiers" in too_big.json()["detail"]
    nothing = client.post("/api/memory/documents/folder", headers=AUTH,
                          data={"folder": "zip", "paths": ["a.zip"]},
                          files=[("files", ("a.zip", b"PK", "application/zip"))])
    assert nothing.status_code == 409 and not list((tmp_path / "envois").rglob("*.*"))

    documents.service._engine = lambda: None  # pylint: disable=protected-access
    gone = client.post("/api/memory/documents", headers=AUTH, json={"paths": []})
    assert gone.status_code == 409
    upload_gone = client.post("/api/memory/documents/upload", headers=AUTH,
                              files={"file": ("note.md", b"x", "text/markdown")})
    assert upload_gone.status_code == 409 and not list((tmp_path / "envois").rglob("*.*"))


# ── Aperçu d'un document : copie de son fichier, sinon son texte ───────────


class CopyingStore(FakeStore):
    """MemoryStore avec une base vectorielle dans un dossier : les fichiers lus y
    sont gardés (memory_files.py)."""

    def __init__(self, folder, encrypted=False):
        super().__init__()
        self.vector_memory.storage_dir = folder
        self.vector_memory.enable_encryption = encrypted

    def document_text(self, document_id):
        doc = self.docs.get(document_id)
        return doc["content"] if doc else ""

    def delete_folder(self, key):
        gone = [doc_id for doc_id, doc in self.docs.items() if doc["folder_key"] == key]
        for doc_id in gone:
            del self.docs[doc_id]
        return 3 * len(gone)


@pytest.fixture(name="copies")
def copies_fixture(tmp_path):
    store = CopyingStore(tmp_path / "vector_store")
    engine = SimpleNamespace(get_memory_store=lambda: store, local_ai=SimpleNamespace(
        read_file_for_context=lambda path: {"content": f"Contenu de {os.path.basename(path)}",
                                            "processor_used": "Code"}))
    service = MemoryService(lambda: engine, lambda: None, publish=lambda kind, payload: None)

    def write(name, text="x"):
        path = tmp_path / "source" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return str(path)

    return SimpleNamespace(store=store, service=service, write=write, tmp=tmp_path,
                           root=tmp_path / "vector_store" / "originals")


def test_a_document_keeps_a_copy_of_its_file_for_its_preview(copies):
    note = copies.write("note.md", "# Note")
    copies.service.add_documents([note])
    _idle(copies.service)
    [doc] = copies.store.named("note.md")
    preview = copies.service.preview(doc["id"])
    assert preview["text"] is None and preview["size"] == 6
    assert os.path.basename(preview["path"]) == "note.md"
    assert open(preview["path"], encoding="utf-8").read() == "# Note"
    assert copies.service.originals_root() == str(copies.root)
    # Le fichier d'origine peut disparaître : la copie reste
    os.remove(note)
    assert os.path.isfile(copies.service.preview(doc["id"])["path"])
    # Supprimé de la mémoire : sa copie aussi
    copies.service.delete_document(doc["id"])
    assert not os.listdir(copies.root)
    with pytest.raises(MemoryPanelError, match="n'est plus dans la mémoire"):
        copies.service.preview(doc["id"])


def test_files_sent_by_the_window_and_folders_keep_their_copy(copies):
    upload = copies.write("envoi/compte-rendu.md", "# Lundi")
    copies.service.add_documents([upload], temporary=True)
    _idle(copies.service)
    assert not os.path.exists(upload)  # l'envoi temporaire est effacé, la copie reste
    [doc] = copies.store.named("compte-rendu.md")
    assert open(copies.service.preview(doc["id"])["path"], encoding="utf-8").read() == "# Lundi"

    plan = copies.write("site/sous/plan.py", "print(1)")
    copies.service.add_folder("site", [(plan, "sous/plan.py")], temporary=False)
    _idle(copies.service)
    [inside] = copies.store.named("site/sous/plan.py")
    assert os.path.basename(copies.service.preview(inside["id"])["path"]) == "plan.py"
    copies.service.delete_folder(inside["folder_key"])
    assert sorted(os.listdir(copies.root)) == [
        OriginalFiles.folder_name(doc["id"])]  # celle du compte rendu seulement


def test_a_document_without_copy_shows_its_stored_text(copies, monkeypatch):
    stored = copies.store.add_document("Texte gardé " * 3, "ancien.pdf", {"type": "PDF"})
    preview = copies.service.preview(stored["document_id"])
    assert preview["path"] is None and preview["text"] == "Texte gardé " * 3
    assert preview["truncated"] is False and preview["type"] == "PDF"
    monkeypatch.setattr("interfaces.desktop.memory.PREVIEW_TEXT_MAX", 5)
    assert copies.service.preview(stored["document_id"])["text"] == "Texte"
    assert copies.service.preview(stored["document_id"])["truncated"] is True


def test_copies_of_documents_removed_elsewhere_are_pruned(copies):
    for name in ("a.md", "b.md"):
        copies.service.add_documents([copies.write(name)])
    _idle(copies.service)
    assert len(os.listdir(copies.root)) == 2
    # Retiré ailleurs que par l'onglet (pièce jointe du chat oubliée)
    [gone] = copies.store.named("a.md")
    del copies.store.docs[gone["id"]]
    copies.service._prune_originals()  # pylint: disable=protected-access
    [kept] = copies.store.named("b.md")
    assert os.listdir(copies.root) == [OriginalFiles.folder_name(kept["id"])]
    # Mémoire vide (ou illisible) : rien n'est supprimé à l'aveugle
    copies.store.docs.clear()
    copies.service._prune_originals()  # pylint: disable=protected-access
    assert len(os.listdir(copies.root)) == 1


def test_a_chat_attachment_stored_just_now_keeps_its_copy(copies, monkeypatch):
    """Rangé à l'instant par le chat : sa copie ; un doublon d'un ancien document
    du même nom, ou un fichier d'un dossier, n'en reçoit pas."""
    attached = copies.write("joint/rapport.pdf", "%PDF récent")
    stored = copies.store.add_document("Texte du rapport", "rapport.pdf", {"type": "PDF"})
    fresh = datetime.now().isoformat(timespec="seconds")
    copies.store.docs[stored["document_id"]]["created"] = fresh
    copies.service.keep_chat_document(attached, "rapport.pdf")
    preview = copies.service.preview(stored["document_id"])
    assert preview["path"] and open(preview["path"], encoding="utf-8").read() == "%PDF récent"

    # Ancien document du même nom (pièce jointe déjà rangée il y a longtemps) : rien
    old = copies.store.add_document("Ancien texte", "ancien.pdf", {"type": "PDF"})
    copies.store.docs[old["document_id"]]["created"] = "2026-01-02T10:00:00"
    copies.service.keep_chat_document(copies.write("joint/ancien.pdf"), "ancien.pdf")
    assert copies.service.preview(old["document_id"])["path"] is None
    # Fichier d'un dossier du même nom : pas une pièce jointe du chat
    inside = copies.store.add_document("Plan", "site/plan.pdf",
                                       {"folder": "site", "folder_id": "s1"})
    copies.store.docs[inside["document_id"]].update(created=fresh, name="plan.pdf")
    copies.service.keep_chat_document(copies.write("joint/plan.pdf"), "plan.pdf")
    assert copies.service.preview(inside["document_id"])["path"] is None
    # Fichier disparu entre-temps, ou mémoire sans copies : rien, sans erreur
    copies.service.keep_chat_document(str(copies.tmp / "absent.pdf"), "rapport.pdf")
    monkeypatch.setattr(copies.service, "_originals", lambda: None)
    copies.service.keep_chat_document(attached, "rapport.pdf")


def test_an_encrypted_memory_keeps_no_copy(tmp_path):
    store = CopyingStore(tmp_path / "vector_store", encrypted=True)
    engine = SimpleNamespace(get_memory_store=lambda: store, local_ai=SimpleNamespace(
        read_file_for_context=lambda path: {"content": "secret", "processor_used": "Code"}))
    service = MemoryService(lambda: engine, lambda: None)
    note = tmp_path / "note.md"
    note.write_text("secret", encoding="utf-8")
    service.add_documents([str(note)])
    _idle(service)
    assert service.originals_root() is None
    assert not (tmp_path / "vector_store" / "originals").exists()
    [doc] = store.named("note.md")
    assert service.preview(doc["id"])["text"] == "secret"


def test_copy_names_are_safe_everywhere(tmp_path):
    assert safe_file_name("dossier/sous/rap:port?.pdf. ") == "rap_port_.pdf"
    assert safe_file_name("C:\\x\\note.md") == "note.md"
    assert safe_file_name("") == "document"
    files = OriginalFiles(tmp_path / "originals")
    source = tmp_path / "plan"
    source.write_text("v1", encoding="utf-8")
    # Ni le nom ni le fichier lu n'ont d'extension : la copie non plus
    first = files.keep("doc:1", str(source), "plan")
    assert os.path.basename(first) == "plan"
    other = tmp_path / "plan.py"
    other.write_text("v2", encoding="utf-8")
    second = files.keep("doc:1", str(other), "projet/plan")
    assert os.path.basename(second) == "plan.py"
    # Une seule copie par document ; replace=False garde celle qui est là
    assert os.listdir(os.path.dirname(second)) == ["plan.py"]
    assert files.keep("doc:1", str(source), "plan.txt", replace=False) == second
    assert files.find("doc:inconnu") is None
    assert files.keep("doc:2", str(tmp_path / "absent.md"), "absent.md") is None


def test_document_preview_route(copies):
    app = FakeApp(None, EventBus())
    app.memory = copies.service
    server = DesktopServer(app)
    server.port = PORT
    client = TestClient(server.fastapi, base_url=BASE)
    copies.service.add_documents([copies.write("note.md", "# Note")])
    _idle(copies.service)
    [doc] = copies.store.named("note.md")
    preview = client.post("/api/memory/documents/preview", headers=AUTH,
                          json={"document": doc["id"]}).json()
    assert preview["name"] == "note.md" and preview["text"] is None
    # La copie s'affiche comme une pièce jointe : lien signé, texte lisible
    links = client.post("/api/files/links", headers=AUTH,
                        json={"paths": [preview["path"]]}).json()["links"]
    assert links[preview["path"]]
    assert client.post("/api/files/text", headers=AUTH,
                       json={"path": preview["path"]}).json()["text"] == "# Note"
    gone = client.post("/api/memory/documents/preview", headers=AUTH,
                       json={"document": "absent"})
    assert gone.status_code == 409
