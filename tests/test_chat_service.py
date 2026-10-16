"""
Tests du service de chat sans interface (core/chat_service.py)

Le moteur est simulé : il note chaque appel reçu et rejoue un scénario
(jetons, réflexion, appels d'outils, confirmation…). Le premier test fixe
l'ordre exact des appels au moteur, repris de l'interface Tk : la reprise du
prompt par Ollama en dépend (docs/OPTIMIZATION.md, section 8), et seule la
lenteur la trahirait sur le vrai modèle.
"""

import json
import os
import threading
import time
from datetime import datetime
from types import SimpleNamespace

import pytest

import core.chat_service as chat_service_module
from core.chat_service import (FILE_GENERATION_HISTORY, ChatError, ChatService,
                               session_name_for)
from core.session_manager import SessionManager
from interfaces.desktop.events import EventBus, validate_event
from relay.relay_bridge import RelayBridge, RelayMessage


# ── Moteur simulé ───────────────────────────────────────────────────────────


class FakeLLM:
    """LocalLLM : historique de conversation du modèle."""

    def __init__(self):
        self.conversation_history = []
        self.calls = []
        self.last_stream_stats = None  # relevé de fin de flux (D17)

    def add_to_history(self, role, content):
        self.conversation_history.append({"role": role, "content": content})
        self.calls.append(("add", role, content))

    def clear_history(self):
        self.conversation_history.clear()
        self.calls.append(("clear",))


class FakeMemory:
    """Mémoire de conversation : documents joints."""

    def __init__(self):
        self.stored_documents = {}

    def store_document_content(self, name, content):
        self.stored_documents[name] = content

    def clear(self):
        self.stored_documents.clear()


class FakeLocalAI:
    """CustomAIModel."""

    def __init__(self):
        self.local_llm = FakeLLM()
        self.conversation_memory = FakeMemory()
        self.ultra_mode = False
        self.session_context = {}
        self.added = []
        self.removed = []

    def add_file_to_context(self, path):
        self.added.append(path)
        return {"success": True}

    def remove_document_from_context(self, name):
        self.removed.append(name)
        self.conversation_memory.stored_documents.pop(name, None)
        return {"stored": True, "chunks_removed": 1}


class FakeCommandHistory:
    """Historique des commandes."""

    def __init__(self):
        self.queries = []

    def add(self, query, **_kwargs):
        self.queries.append(query)
        return len(self.queries)


class FakePromptLibrary:
    """Bibliothèque de prompts : une seule commande, /code."""

    @staticmethod
    def expand(text):
        if text.startswith("/code "):
            return "Écris un programme complet pour : " + text[len("/code "):]
        return None

    @staticmethod
    def search(prefix):
        prefix = (prefix or "").lstrip("/").lower()
        commands = [{"command": "code", "title": "Génération de code",
                     "description": "Génère un programme complet et commenté"}]
        return [dict(item) for item in commands if item["command"].startswith(prefix)]


class FakeRLHF:
    """Gestionnaire des notes (core.rlhf_manager) : garde ce qu'il reçoit."""

    def __init__(self):
        self.records = []

    def record_interaction(self, **kwargs):
        self.records.append(kwargs)
        return len(self.records)


class FakeEngine:
    """AIEngine simulé : note ses appels, rejoue `script` dans process_query_stream."""

    def __init__(self, workspaces_dir):
        self.calls = []
        self.local_ai = FakeLocalAI()
        self.session_manager = SessionManager(str(workspaces_dir))
        self.command_history = FakeCommandHistory()
        self.prompt_library = FakePromptLibrary()
        self.conversation_manager = SimpleNamespace(
            clear=lambda: self.calls.append("conversation_manager.clear")
        )
        self.complex = False
        self.conversational = False
        self.image_request = False
        self.script = None  # None : une réponse qui cite la question
        self.stream_kwargs = None
        self.delete_answers = []
        self.file_result = {}
        self.generator = None
        # Relevé de fin de flux de l'orchestrateur (D15), écrit par l'étape « stats »
        self._chat_orchestrator = SimpleNamespace(last_stream_stats=None)

    @property
    def image_generator(self):
        return self.generator

    def set_visible_documents(self, names):
        self.calls.append(("set_visible_documents", sorted(names)))

    def set_attached_documents(self, paths):
        self.calls.append(("set_attached_documents", list(paths)))

    def is_image_generation_request(self, _text):
        self.calls.append("is_image_generation_request")
        return self.image_request

    def is_ollama_active(self):
        self.calls.append("is_ollama_active")
        return True

    def is_complex_query(self, _text):
        self.calls.append("is_complex_query")
        return self.complex

    def is_conversational(self, _text):
        self.calls.append("is_conversational")
        return self.conversational

    def clear_conversation(self):
        self.calls.append("clear_conversation")

    def extract_image_prompt(self, _text):
        return "un phare"

    async def process_query(self, query, context=None, is_interrupted_callback=None):
        del context, is_interrupted_callback
        self.calls.append(("process_query", query))
        return self.file_result

    def process_query_stream(self, user_input, **kwargs):
        self.calls.append(("process_query_stream", user_input))
        self.stream_kwargs = kwargs
        script = self.script if self.script is not None else [
            ("token", "Réponse à "), ("token", f"« {user_input} »"),
        ]
        streamed = ""
        for step in script:
            kind = step[0]
            if kind == "token":
                if kwargs["on_token"](step[1]) is False:
                    break
                streamed += step[1]
            elif kind == "thinking":
                kwargs["on_thinking_token"](step[1])
            elif kind == "thinking_done":
                kwargs["on_thinking_complete"]()
            elif kind == "tool":
                kwargs["on_tool_call"](step[1], step[2])
            elif kind == "tool_result":
                kwargs["on_tool_result"](step[1], step[2], step[3])
            elif kind == "document":
                kwargs["on_document"](step[1])
            elif kind == "delete":
                self.delete_answers.append(kwargs["on_delete_confirm"](step[1]))
            elif kind == "wait":
                while not step[1].wait(0.01):
                    if kwargs["is_interrupted_callback"]():
                        break
                if kwargs["is_interrupted_callback"]():
                    break
            elif kind == "raise":
                raise step[1]
            elif kind == "stats":
                self._chat_orchestrator.last_stream_stats = {
                    "eval_count": step[1], "eval_duration": step[2], "at": time.perf_counter(),
                }
            elif kind == "llm_stats":  # réponse sans outils (LocalLLM.generate_stream)
                self.local_ai.local_llm.last_stream_stats = {
                    "eval_count": step[1], "eval_duration": step[2], "at": time.perf_counter(),
                }
        return streamed


class FakeFileProcessor:
    """utils.file_processor.FileProcessor : lecture bloquée tant que `gate` est fermé."""

    def __init__(self):
        self.gate = None
        self.gates = []  # une barrière par lecture, prises dans l'ordre des lectures
        self.error = None  # erreur d'un fichier illisible

    def process_file(self, path):
        gate = self.gates.pop(0) if self.gates else self.gate
        if gate is not None:
            gate.wait(5)
        if self.error:
            return {"error": self.error}
        return {"content": f"Contenu de {path}"}


class FakeBridge:
    """RelayBridge réduit à ce que le service utilise."""

    def __init__(self):
        self.active = True
        self.callbacks = []
        self.chunks = []
        self.responses = []
        self.documents = []
        self.interrupt = False

    def on_gui_message(self, callback):
        self.callbacks.append(callback)

    def remove_gui_callback(self, callback):
        if callback in self.callbacks:
            self.callbacks.remove(callback)

    @staticmethod
    def poll_gui_messages():
        return []

    def consume_interrupt_request(self):
        requested, self.interrupt = self.interrupt, False
        return requested

    def submit_ai_chunk(self, text, message_id=None):
        self.chunks.append((message_id, text))

    def submit_ai_response(self, text, message_id=None):
        self.responses.append((message_id, text))

    def submit_ai_document(self, path, message_id=None):
        self.documents.append((message_id, path))

    def deliver(self, message):
        """Message du mobile, comme RelayBridge.send_to_gui."""
        for callback in list(self.callbacks):
            callback(message)


# ── Outils ──────────────────────────────────────────────────────────────────


def wait_for(events, event_type, count=1, timeout=5.0):
    """Attend `count` événements du type donné ; les renvoie."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        found = [event for event in events if event["type"] == event_type]
        if len(found) >= count:
            return found
        time.sleep(0.01)
    seen = [event["type"] for event in events]
    raise AssertionError(f"{event_type} ×{count} non reçu ; reçus : {seen}")


def chat_types(events):
    """Types des événements du fil de conversation (sans file ni sessions)."""
    return [event["type"] for event in events
            if event["type"] not in ("queue.updated", "sessions.changed", "notification")]


def texts(snapshot):
    """Textes des messages d'un état de conversation."""
    return [message["text"] for message in snapshot["messages"]]


@pytest.fixture(name="chat")
def chat_fixture(tmp_path):
    """Service de chat branché sur un moteur simulé et un vrai bus d'événements."""
    engine = FakeEngine(tmp_path / "workspaces")
    bus = EventBus()
    events = []
    bus.subscribe(events.append)
    processor = FakeFileProcessor()
    ui = {"connected": True}
    sessions = []
    service = ChatService(
        engine, bus.publish, file_processor=processor,
        ui_connected=lambda: ui["connected"], on_session_change=sessions.append,
    )
    service.start()
    yield SimpleNamespace(service=service, engine=engine, events=events, bus=bus,
                          processor=processor, ui=ui, tmp_path=tmp_path,
                          sessions=sessions)
    service.close()


def ask(chat, text, done_count=None, **kwargs):
    """Envoie un message et attend la fin de sa réponse."""
    already = len([e for e in chat.events if e["type"] == "assistant.done"])
    chat.service.send(text, **kwargs)
    return wait_for(chat.events, "assistant.done", (done_count or already + 1))[-1]["payload"]


# ── Pipeline : les appels de l'interface Tk ─────────────────────────────────


def test_message_makes_the_tk_engine_calls_in_the_same_order(chat):
    done = ask(chat, "Bonjour")

    assert chat.engine.calls == [
        ("set_visible_documents", []),
        ("set_attached_documents", []),
        "is_image_generation_request",
        "is_ollama_active",
        "is_complex_query",
        "is_conversational",
        ("process_query_stream", "Bonjour"),
    ]
    kwargs = chat.engine.stream_kwargs
    assert set(kwargs) == {
        "on_token", "on_tool_call", "on_thinking_token", "on_thinking_complete",
        "image_base64", "is_interrupted_callback", "on_delete_confirm", "on_document",
        "on_tool_result",
    }
    # Pas de réflexion pour une requête simple, comme dans Tk
    assert kwargs["on_thinking_token"] is None and kwargs["on_thinking_complete"] is None
    assert kwargs["image_base64"] is None
    assert chat.engine.command_history.queries == ["Bonjour"]
    # Aucune réécriture de l'historique du modèle pour un message ordinaire
    assert chat.engine.local_ai.local_llm.calls == []
    assert done["text"] == "Réponse à « Bonjour »"
    assert chat_types(chat.events)[:3] == ["message.user", "assistant.start", "assistant.token"]


def test_complex_query_streams_its_reasoning(chat):
    chat.engine.complex = True
    chat.engine.script = [
        ("thinking", "🧠 Analyse :\n"), ("thinking", "Je compare."), ("thinking_done",),
        ("token", "Réponse détaillée"),
    ]
    ask(chat, "Compare deux algorithmes de tri")

    assert chat.engine.stream_kwargs["on_thinking_token"] is not None
    start = wait_for(chat.events, "assistant.start")[0]["payload"]
    assert start["reasoning"] is True
    thinking = "".join(e["payload"]["text"] for e in chat.events
                       if e["type"] == "assistant.thinking")
    assert thinking == "🧠 Analyse :\nJe compare."
    wait_for(chat.events, "assistant.thinking_done")
    answer = chat.service.snapshot()["messages"][-1]
    assert answer["thinking"] == thinking


def test_slash_command_is_expanded_but_the_message_keeps_it(chat):
    ask(chat, "/code un morpion")

    assert ("process_query_stream", "Écris un programme complet pour : un morpion") in chat.engine.calls
    assert texts(chat.service.snapshot())[0] == "/code un morpion"


def test_stop_keeps_the_partial_answer(chat):
    gate = threading.Event()
    chat.engine.script = [("token", "Début"), ("wait", gate), ("token", " et fin")]
    chat.service.send("Raconte une histoire")
    wait_for(chat.events, "assistant.token")

    assert chat.service.stop() is True
    interrupted = wait_for(chat.events, "assistant.interrupted")[0]["payload"]
    assert interrupted["text"] == "Début"
    answer = chat.service.snapshot()["messages"][-1]
    assert answer["text"] == "Début" and answer["interrupted"] is True
    assert chat.engine.stream_kwargs["is_interrupted_callback"]() is True


def test_messages_wait_their_turn_in_the_queue(chat):
    gate = threading.Event()
    chat.engine.script = [("token", "Première réponse"), ("wait", gate)]
    chat.service.send("Premier")
    wait_for(chat.events, "assistant.token")
    second = chat.service.send("Second")

    queue = [e for e in chat.events if e["type"] == "queue.updated"][-1]["payload"]["items"]
    assert [item["request_id"] for item in queue] == [second]
    assert chat.service.snapshot()["queue"][0]["text"] == "Second"

    chat.engine.script = None
    gate.set()
    wait_for(chat.events, "assistant.done", 2)
    users = [e["payload"]["text"] for e in chat.events if e["type"] == "message.user"]
    assert users == ["Premier", "Second"]
    assert texts(chat.service.snapshot()) == [
        "Premier", "Première réponse", "Second", "Réponse à « Second »",
    ]


def test_queued_message_can_be_withdrawn(chat):
    gate = threading.Event()
    chat.engine.script = [("token", "En cours"), ("wait", gate)]
    chat.service.send("Premier")
    wait_for(chat.events, "assistant.token")
    second = chat.service.send("Second")

    assert chat.service.cancel(second) is True
    gate.set()
    wait_for(chat.events, "assistant.done")
    time.sleep(0.1)
    assert [e["payload"]["text"] for e in chat.events if e["type"] == "message.user"] == ["Premier"]


# ── Outils et confirmations ─────────────────────────────────────────────────


def test_tool_calls_keep_the_tk_line_breaks_and_their_results(chat):
    chat.engine.script = [
        ("token", "Je cherche.\n"),
        ("tool", "web_search", {"query": "python"}),
        ("tool_result", "web_search", {"query": "python"},
         "[1] https://a.example/page\n[2] https://b.example/doc"),
        ("tool", "synthesis", {}),
        ("token", "Voici la réponse."),
    ]
    done = ask(chat, "Cherche sur internet Python")

    syncs = [e["payload"]["text"] for e in chat.events if e["type"] == "assistant.sync"]
    assert syncs == ["Je cherche.", "Je cherche.\n\n"]
    assert done["text"] == "Je cherche.\n\nVoici la réponse."
    calls = [e["payload"] for e in chat.events if e["type"] == "tool.call"]
    assert calls[0]["label"] == "🔍 Recherche sur internet : « python »"
    # Position de chaque appel dans le texte, une fois les sauts de ligne normalisés
    assert [(c["name"], c["at"]) for c in calls] == [("web_search", 11), ("synthesis", 13)]
    result = wait_for(chat.events, "tool.result")[0]["payload"]
    assert result == {"name": "web_search", "ok": True, "summary": "[1] https://a.example/page",
                      "sources": 2}
    answer = chat.service.snapshot()["messages"][-1]
    assert answer["tool_calls"] == [{
        "name": "web_search", "label": "🔍 Recherche sur internet : « python »", "at": 11,
        "ok": True, "summary": "[1] https://a.example/page", "sources": 2,
    }]


def test_tokens_per_second_come_from_ollama_stream_stats(chat):
    # D15 : eval_count / eval_duration du dernier flux, relevés par l'orchestrateur
    chat.engine.script = [("token", "Une réponse"), ("token", " assez longue."),
                          ("stats", 146, 2_000_000_000)]
    done = ask(chat, "Explique")

    assert done["tokens_per_s"] == 73.0
    assert chat.service.snapshot()["messages"][-1]["tokens_per_s"] == 73.0


def test_tokens_per_second_of_an_answer_without_tools_come_from_local_llm(chat):
    # D17 : LocalLLM.generate_stream garde le même relevé que l'orchestrateur
    chat.engine.script = [("token", "Bonjour !"), ("llm_stats", 30, 400_000_000)]
    done = ask(chat, "Salut")

    assert done["tokens_per_s"] == 75.0


def test_the_most_recent_stream_stats_win(chat):
    # Orchestrateur sans réponse, puis relance sans outils par LocalLLM
    chat.engine.script = [("stats", 20, 1_000_000_000), ("token", "Réponse"),
                          ("llm_stats", 150, 2_000_000_000)]
    done = ask(chat, "Question")

    assert done["tokens_per_s"] == 75.0


def test_stale_stream_stats_are_ignored(chat):
    # Relevé d'une réponse précédente (flux coupé, autre chemin) : repli sur
    # l'estimation, absente pour une réponse si brève
    chat.engine._chat_orchestrator.last_stream_stats = {  # pylint: disable=protected-access
        "eval_count": 999, "eval_duration": 1_000_000_000, "at": time.perf_counter() - 60,
    }
    done = ask(chat, "Bonjour")

    assert done["tokens_per_s"] is None


def test_file_deletion_waits_for_the_window(chat):
    chat.engine.script = [("delete", "C:/dossier/a.txt"), ("token", "Supprimé.")]
    chat.service.send("Supprime a.txt")
    request = wait_for(chat.events, "confirm.request")[0]["payload"]
    assert request["name"] == "a.txt"
    assert chat.service.snapshot()["confirm"]["confirm_id"] == request["confirm_id"]

    assert chat.service.confirm(request["confirm_id"], True) is True
    wait_for(chat.events, "assistant.done")
    assert chat.engine.delete_answers == [True]
    assert wait_for(chat.events, "confirm.closed")[0]["payload"]["accepted"] is True


def test_file_deletion_is_refused_without_a_window(chat):
    chat.ui["connected"] = False
    chat.engine.script = [("delete", "C:/dossier/a.txt"), ("token", "Refusé.")]
    ask(chat, "Supprime a.txt")

    assert chat.engine.delete_answers == [False]


def test_stop_refuses_a_pending_deletion(chat):
    chat.engine.script = [("delete", "C:/dossier/a.txt")]
    chat.service.send("Supprime a.txt")
    wait_for(chat.events, "confirm.request")

    chat.service.stop()
    wait_for(chat.events, "assistant.interrupted")
    assert chat.engine.delete_answers == [False]


def test_documents_produced_by_a_tool_are_announced(chat):
    chat.engine.script = [("document", "C:/out/rapport.docx"), ("document", "C:/out/rapport.docx"),
                          ("token", "Le document est prêt.")]
    ask(chat, "Crée un rapport Word")

    created = wait_for(chat.events, "document.created")
    assert len(created) == 1 and created[0]["payload"]["name"] == "rapport.docx"
    assert chat.service.snapshot()["messages"][-1]["documents"] == ["C:/out/rapport.docx"]


def test_engine_failure_becomes_an_error_answer(chat):
    chat.engine.script = [("raise", ConnectionError("Ollama injoignable"))]
    chat.service.send("Bonjour")

    error = wait_for(chat.events, "assistant.error")[0]["payload"]
    assert error["message"] == "❌ Erreur IA : Ollama injoignable"
    answer = chat.service.snapshot()["messages"][-1]
    assert answer["error"] is True and answer["text"] == "❌ Erreur IA : Ollama injoignable"


# ── Générations de fichier et d'image ───────────────────────────────────────


def test_file_generation_takes_the_tk_path(chat):
    chat.engine.file_result = {"type": "file_generation", "success": True,
                               "filename": "calc.py", "file_path": "C:/out/calc.py"}
    done = ask(chat, "Génère moi un fichier calc.py")

    assert ("process_query", "Génère moi un fichier calc.py") in chat.engine.calls
    assert not any(call[0] == "process_query_stream" for call in chat.engine.calls
                   if isinstance(call, tuple))
    assert done["text"].endswith("calc.py")
    assert wait_for(chat.events, "file.created")[0]["payload"]["path"] == "C:/out/calc.py"
    assert chat.engine.local_ai.local_llm.calls == [
        ("add", "user", "Génère moi un fichier calc.py"),
        ("add", "assistant", FILE_GENERATION_HISTORY),
    ]
    answer = chat.service.snapshot()["messages"][-1]
    assert answer["type"] == "file_generation" and answer["file_path"] == "C:/out/calc.py"


def test_image_generation_reports_progress_and_is_remembered(chat):
    progress_seen = []

    class FakeGenerator:
        @staticmethod
        def is_available():
            return True

        @staticmethod
        def generate(prompt, on_progress, is_interrupted):
            progress_seen.append((prompt, is_interrupted()))
            on_progress(0.5, "Diffusion 50 %")
            return SimpleNamespace(interrupted=False, success=True,
                                   image_path="C:/outputs/phare.png", message="🎨 Image générée")

    chat.engine.image_request = True
    chat.engine.generator = FakeGenerator()
    done = ask(chat, "Génère une image d'un phare")

    assert done["text"] == "🎨 Image générée"
    assert progress_seen == [("un phare", False)]
    assert wait_for(chat.events, "image.progress")[0]["payload"]["message"] == "Diffusion 50 %"
    assert wait_for(chat.events, "image.created")[0]["payload"]["name"] == "phare.png"
    llm_calls = chat.engine.local_ai.local_llm.calls
    assert llm_calls[0] == ("add", "user", "Génère une image d'un phare")
    assert llm_calls[1][1] == "assistant" and "« un phare »" in llm_calls[1][2]
    answer = chat.service.snapshot()["messages"][-1]
    assert answer["type"] == "image_generation" and answer["image_path"] == "C:/outputs/phare.png"


# ── Pièces jointes ──────────────────────────────────────────────────────────


def test_send_waits_until_an_attachment_is_read(chat):
    document = chat.tmp_path / "rapport.pdf"
    document.write_bytes(b"%PDF-1.4")
    chat.processor.gate = threading.Event()
    attachment = chat.service.add_attachment(str(document))
    assert attachment["status"] == "loading"

    with pytest.raises(ChatError, match="en cours de chargement"):
        chat.service.send("Résume ce document")

    chat.processor.gate.set()
    wait_for(chat.events, "attachment.ready")
    ask(chat, "Résume ce document")

    user = chat.service.snapshot()["messages"][0]
    assert user["text"] == "Résume ce document\n📎 rapport.pdf"
    assert user["attachments"] == [{"path": str(document), "name": "rapport.pdf", "type": "PDF"}]
    assert ("set_visible_documents", ["rapport.pdf"]) in chat.engine.calls
    assert "rapport.pdf" in chat.engine.local_ai.conversation_memory.stored_documents
    assert chat.service.attachments() == []


def test_image_attachment_goes_to_the_vision_model(chat):
    from PIL import Image  # pylint: disable=import-outside-toplevel

    image = chat.tmp_path / "schema.png"
    Image.new("RGBA", (64, 32), (255, 107, 71, 255)).save(image)
    chat.service.add_attachment(str(image))
    ask(chat, "Que vois-tu ?")

    kwargs = chat.engine.stream_kwargs
    assert kwargs["image_base64"]
    # Image en attente : pas de réflexion, comme dans Tk
    assert kwargs["on_thinking_token"] is None
    user = chat.service.snapshot()["messages"][0]
    assert user["text"] == "Que vois-tu ?\n🖼️ schema.png" and user["image_path"] == str(image)


def test_a_new_image_replaces_the_pending_one(chat):
    from PIL import Image  # pylint: disable=import-outside-toplevel

    first, second = chat.tmp_path / "schema.png", chat.tmp_path / "photo.png"
    Image.new("RGB", (64, 32), (255, 107, 71)).save(first)
    Image.new("RGB", (32, 64), (37, 99, 235)).save(second)
    old = chat.service.add_attachment(str(first))
    document = chat.tmp_path / "notes.txt"
    document.write_text("notes", encoding="utf-8")
    chat.service.add_attachment(str(document))
    chat.service.add_attachment(str(second))

    # Le modèle ne reçoit qu'une image : la puce de la première disparaît
    names = [att["name"] for att in chat.service.attachments()]
    assert names == ["notes.txt", "photo.png"]
    assert {"id": old["id"]} in [event["payload"] for event in chat.events
                                 if event["type"] == "attachment.removed"]
    messages = [event["payload"]["message"] for event in chat.events if event["type"] == "notification"]
    assert "✅ photo.png prête (32x64), à la place de schema.png (une image par message)" in messages


def test_a_dropped_folder_attaches_its_files(chat):
    from PIL import Image  # pylint: disable=import-outside-toplevel

    folder = chat.tmp_path / "projet"
    for sub in ("src", "node_modules/lib", ".git"):
        (folder / sub).mkdir(parents=True)
    (folder / "README.md").write_text("# Projet", encoding="utf-8")
    (folder / "src" / "main.py").write_text("print(1)", encoding="utf-8")
    (folder / "node_modules" / "lib" / "index.js").write_text("x", encoding="utf-8")
    (folder / ".git" / "config").write_text("x", encoding="utf-8")
    (folder / ".env").write_text("SECRET=1", encoding="utf-8")
    (folder / "donnees.bin").write_bytes(bytes(4))
    Image.new("RGB", (8, 8)).save(folder / "logo.png")

    result = chat.service.add_attachment(str(folder))

    # Comme sur claude.ai : chaque fichier lisible devient une pièce jointe
    assert [att["name"] for att in chat.service.attachments()] == ["README.md", "main.py"]
    assert [att["name"] for att in result["attachments"]] == ["README.md", "main.py"]
    assert result["images_skipped"] == 1
    messages = [event["payload"]["message"] for event in chat.events
                if event["type"] == "notification"]
    assert ("📁 2 fichiers de « projet » joints, 1 image laissée de côté "
            "(une seule par message)") in messages


def test_a_big_or_empty_folder_is_not_attached(chat, monkeypatch):
    monkeypatch.setattr(chat_service_module, "FOLDER_ATTACHMENT_LIMIT", 3)
    folder = chat.tmp_path / "gros"
    folder.mkdir()
    for index in range(5):
        (folder / f"f{index}.py").write_text("x", encoding="utf-8")
    with pytest.raises(ChatError, match="Attachez-le plutôt dans « Dossiers du projet »"):
        chat.service.add_attachment(str(folder))
    assert not chat.service.attachments()

    empty = chat.tmp_path / "vide"
    empty.mkdir()
    with pytest.raises(ChatError, match="Aucun fichier lisible dans « vide »"):
        chat.service.add_attachment(str(empty))


def test_removed_attachment_is_forgotten_unless_still_used(chat):
    document = chat.tmp_path / "notes.txt"
    document.write_text("notes", encoding="utf-8")
    attachment = chat.service.add_attachment(str(document))
    wait_for(chat.events, "attachment.ready")

    assert chat.service.remove_attachment(attachment["id"]) is True
    assert chat.engine.local_ai.removed == ["notes.txt"]

    # Joint à un message envoyé : le retirer d'un nouvel envoi ne l'oublie pas
    chat.service.add_attachment(str(document))
    wait_for(chat.events, "attachment.ready", 2)
    ask(chat, "Lis mes notes")
    again = chat.service.add_attachment(str(document))
    chat.service.remove_attachment(again["id"])
    assert chat.engine.local_ai.removed == ["notes.txt"]


def test_removing_an_attachment_being_read_frees_sending_and_forgets_it(chat):
    document = chat.tmp_path / "fiche.pdf"
    document.write_bytes(b"%PDF-1.4")
    chat.processor.gate = threading.Event()
    attachment = chat.service.add_attachment(str(document))
    chat.service.remove_attachment(attachment["id"])

    ask(chat, "Question sans pièce jointe")  # plus rien n'attend la lecture
    chat.processor.gate.set()
    deadline = time.time() + 5
    while not chat.engine.local_ai.removed and time.time() < deadline:
        time.sleep(0.01)
    # Lecture interrompue : rien de gardé, aucune erreur signalée
    assert chat.engine.local_ai.removed == ["fiche.pdf"]
    assert "fiche.pdf" not in chat.engine.local_ai.conversation_memory.stored_documents
    assert not [e for e in chat.events if e["type"] in ("attachment.ready", "attachment.failed")]
    assert not [e for e in chat.events
                if e["type"] == "notification" and e["payload"]["level"] == "error"]


def test_the_same_file_attached_twice_waits_for_both_reads(chat):
    document = chat.tmp_path / "rapport.pdf"
    document.write_bytes(b"%PDF-1.4")
    first, second = threading.Event(), threading.Event()
    chat.processor.gates = [first, second]
    chat.service.add_attachment(str(document))
    chat.service.add_attachment(str(document))

    first.set()
    wait_for(chat.events, "attachment.ready")
    with pytest.raises(ChatError, match="en cours de chargement"):
        chat.service.send("Résume ce document")
    second.set()
    wait_for(chat.events, "attachment.ready", 2)
    ask(chat, "Résume ce document")


def test_an_unreadable_file_does_not_block_sending(chat):
    document = chat.tmp_path / "scan.pdf"
    document.write_bytes(b"%PDF-1.4")
    chat.processor.error = "PDF illisible"
    chat.service.add_attachment(str(document))

    assert wait_for(chat.events, "attachment.failed")[0]["payload"]["message"] == "PDF illisible"
    assert "❌ Erreur : scan.pdf" in [e["payload"]["message"] for e in chat.events
                                     if e["type"] == "notification"]
    ask(chat, "Que dit ce document ?")
    # Toujours cité dans le message, comme dans Tk
    assert chat.service.snapshot()["messages"][0]["text"] == "Que dit ce document ?\n📎 scan.pdf"


def test_a_document_already_in_memory_is_kept(chat):
    """Déjà lu plus tôt dans la session : retirer la pièce jointe ne l'oublie pas."""
    chat.engine.local_ai.conversation_memory.stored_documents["notes.txt"] = "notes"
    document = chat.tmp_path / "notes.txt"
    document.write_text("notes", encoding="utf-8")
    attachment = chat.service.add_attachment(str(document))
    wait_for(chat.events, "attachment.ready")

    chat.service.remove_attachment(attachment["id"])
    assert chat.engine.local_ai.removed == []


def test_a_document_still_used_elsewhere_is_kept(chat):
    """Encore joint à une autre pièce en attente, ou à une variante d'un tour modifié."""
    document = chat.tmp_path / "notes.txt"
    document.write_text("notes", encoding="utf-8")
    first = chat.service.add_attachment(str(document))
    second = chat.service.add_attachment(str(document))
    wait_for(chat.events, "attachment.ready", 2)
    chat.service.remove_attachment(first["id"])
    assert chat.engine.local_ai.removed == []

    # Variante d'avant d'un tour modifié, avec ce fichier ; la version affichée, sans
    chat.service._branches["m1"] = {"current": 1, "versions": [  # pylint: disable=protected-access
        {"user": "version d'avant", "attachments": [[str(document), "Code"]], "tail": []},
        {"user": "version affichée", "attachments": [], "tail": []},
    ]}
    chat.service.remove_attachment(second["id"])
    assert chat.engine.local_ai.removed == []


def test_removal_during_ocr_skips_the_remaining_pages(chat, monkeypatch):
    """Bout en bout : PDF de 3 pages scannées, pièce jointe retirée pendant la première."""
    pymupdf = pytest.importorskip("pymupdf")
    from processors import ocr  # pylint: disable=import-outside-toplevel
    from utils.file_processor import FileProcessor  # pylint: disable=import-outside-toplevel

    pages = []
    attached = threading.Event()
    attachment = {}

    def engine(_image):
        pages.append(1)
        attached.wait(5)
        chat.service.remove_attachment(attachment["id"])  # ✕ pendant l'OCR
        return SimpleNamespace(txts=("texte reconnu",))

    monkeypatch.setattr(ocr, "_get_engine", lambda: engine)
    monkeypatch.setattr(ocr, "RapidOCR", object)
    path = chat.tmp_path / "scan.pdf"
    pdf = pymupdf.open()
    for _ in range(3):
        pdf.new_page()  # pages sans couche texte : OCR
    pdf.save(str(path))
    pdf.close()
    chat.service._file_processor = FileProcessor()  # pylint: disable=protected-access

    attachment.update(chat.service.add_attachment(str(path)))
    attached.set()
    deadline = time.time() + 10
    while not chat.engine.local_ai.removed and time.time() < deadline:
        time.sleep(0.02)
    assert pages == [1]  # pages 2 et 3 jamais reconnues
    assert chat.engine.local_ai.removed == ["scan.pdf"]
    assert "scan.pdf" not in chat.engine.local_ai.conversation_memory.stored_documents
    assert not [e for e in chat.events
                if e["type"] == "notification" and e["payload"]["level"] == "error"]


def test_unknown_formats_are_refused(chat):
    unknown = chat.tmp_path / "archive.xyz"
    unknown.write_bytes(b"?")
    with pytest.raises(ChatError, match="Format non supporté"):
        chat.service.add_attachment(str(unknown))


# ── Variantes d'édition ─────────────────────────────────────────────────────


def test_edit_creates_a_variant_and_navigation_restores_what_followed(chat):
    ask(chat, "Question A")
    ask(chat, "Question B")
    first = chat.service.snapshot()["messages"][0]["mid"]
    llm = chat.engine.local_ai.local_llm
    llm.calls.clear()

    chat.service.send("Question A modifiée", edit_mid=first)
    wait_for(chat.events, "assistant.done", 3)

    snapshot = chat.service.snapshot()
    assert texts(snapshot) == ["Question A modifiée", "Réponse à « Question A modifiée »"]
    assert snapshot["branches"] == {first: {"count": 2, "current": 1}}
    assert snapshot["messages"][0]["mid"] == first
    # Historique du modèle réaligné sur ce qui précède le tour édité (rien)
    assert llm.calls[0] == ("clear",)
    # Une variante ne compte pas dans l'historique des commandes
    assert chat.engine.command_history.queries == ["Question A", "Question B"]
    reason = [e["payload"]["reason"] for e in chat.events if e["type"] == "conversation.loaded"]
    assert reason == ["edited"]

    chat.service.navigate(first, 0)
    assert texts(chat.service.snapshot()) == [
        "Question A", "Réponse à « Question A »", "Question B", "Réponse à « Question B »",
    ]
    assert llm.calls[-5:] == [
        ("clear",),
        ("add", "user", "Question A"), ("add", "assistant", "Réponse à « Question A »"),
        ("add", "user", "Question B"), ("add", "assistant", "Réponse à « Question B »"),
    ]

    chat.service.navigate(first, 1)
    assert texts(chat.service.snapshot()) == [
        "Question A modifiée", "Réponse à « Question A modifiée »",
    ]


def test_regenerate_adds_a_variant_of_the_same_message(chat):
    ask(chat, "Raconte une blague")
    first = chat.service.snapshot()["messages"][0]["mid"]

    chat.service.send("", edit_mid=first, regenerate=True)
    wait_for(chat.events, "assistant.done", 2)

    snapshot = chat.service.snapshot()
    assert texts(snapshot)[0] == "Raconte une blague"
    assert snapshot["branches"][first] == {"count": 2, "current": 1}


def test_unchanged_edit_and_edit_during_an_answer_are_refused(chat):
    ask(chat, "Question")
    first = chat.service.snapshot()["messages"][0]["mid"]
    with pytest.raises(ChatError, match="pas changé"):
        chat.service.send("Question", edit_mid=first)

    gate = threading.Event()
    chat.engine.script = [("token", "…"), ("wait", gate)]
    chat.service.send("Autre question")
    wait_for(chat.events, "assistant.token", 3)
    with pytest.raises(ChatError, match="Attendez"):
        chat.service.send("Question modifiée", edit_mid=first)
    gate.set()


# ── Sessions ────────────────────────────────────────────────────────────────


def test_first_message_creates_a_session_saved_in_the_tk_format(chat):
    ask(chat, "Comment trier une liste en Python ?")

    session_id = chat.service.session_id
    assert session_id and chat.sessions[-1] == session_id
    assert chat.service.list_sessions()[0]["name"] == "Comment trier une liste en Python ?"
    state = json.loads(
        (chat.tmp_path / "workspaces" / session_id / "state.json").read_text(encoding="utf-8")
    )
    user, answer = state["conversation_history"]
    assert user["is_user"] is True and user["type"] == "text" and user["mid"]
    assert answer["is_user"] is False and answer["text"] == "Réponse à « Comment trier une liste en Python ? »"
    # Horodatage relu par Tk (message_editing._format_stamp)
    datetime.fromisoformat(user["timestamp"])
    assert state["turn_branches"] == {}


def test_session_names_come_from_the_first_message():
    assert session_name_for("Bonjour") == "Bonjour"
    long_name = session_name_for(
        "Peux-tu m'expliquer en détail comment fonctionne la pagination par curseur ?"
    )
    assert long_name.endswith("…") and len(long_name) <= 49
    assert session_name_for("\n📎 rapport.pdf") == "Conversation"


def test_new_conversation_resets_the_engine_and_loading_rebuilds_its_history(chat):
    ask(chat, "Question A")
    session_id = chat.service.session_id

    chat.service.new_conversation()
    assert chat.service.session_id is None and texts(chat.service.snapshot()) == []
    assert "clear_conversation" in chat.engine.calls
    assert ("clear",) in chat.engine.local_ai.local_llm.calls

    chat.service.load_session(session_id)
    assert texts(chat.service.snapshot()) == ["Question A", "Réponse à « Question A »"]
    assert "conversation_manager.clear" in chat.engine.calls
    # D3 : le modèle retrouve la conversation rechargée
    assert chat.engine.local_ai.local_llm.conversation_history == [
        {"role": "user", "content": "Question A"},
        {"role": "assistant", "content": "Réponse à « Question A »"},
    ]
    assert chat.service.session_id == session_id


def test_opening_another_session_keeps_an_unchanged_one_in_place(chat):
    """Rouvrir une conversation sans y toucher ne la réenregistre pas : elle
    garde sa date, donc sa place dans la liste (D2 l'a déjà enregistrée)."""
    ask(chat, "Question A")
    first = chat.service.session_id
    chat.service.new_conversation()
    ask(chat, "Question B")
    second = chat.service.session_id
    sessions = chat.engine.session_manager

    def modified(session_id):
        return next(w["last_modified"] for w in sessions.list_workspaces()
                    if w["id"] == session_id)

    before = modified(second)
    time.sleep(0.05)
    chat.service.load_session(first)
    chat.service.load_session(second)
    chat.service.load_session(first)
    assert modified(second) == before
    assert chat.service.save_session() is True  # Ctrl+S : déjà à jour

    first_before = modified(first)
    time.sleep(0.05)
    ask(chat, "Question A2")
    assert modified(first) > first_before
    assert texts(chat.service.snapshot())[-1] == "Réponse à « Question A2 »"


def test_a_session_saved_by_tk_opens_unchanged(chat):
    sessions = chat.engine.session_manager
    session_id = sessions.create_workspace("Session Tk")
    mid = "a" * 32
    state = sessions.load_workspace(session_id)
    state["conversation_history"] = [
        {"text": "Analyse ce PDF\n📎 rapport.pdf", "is_user": True,
         "timestamp": "2026-10-06 09:12:40.123456", "type": "text",
         "attachments": [["C:/docs/rapport.pdf", "PDF"]], "image_path": None, "mid": mid},
        {"text": "", "is_user": False, "timestamp": "2026-10-06 09:12:42", "type": "reasoning_widget"},
        {"text": "Le rapport décrit l'API.", "is_user": False,
         "timestamp": "2026-10-06 09:13:07", "type": "streaming"},
    ]
    state["turn_branches"] = {mid: {"versions": [
        {"user": "Lis ce PDF\n📎 rapport.pdf", "attachments": [["C:/docs/rapport.pdf", "PDF"]],
         "image_path": None, "ai": "Ancienne réponse", "ai_mid": None, "tail": []},
        {"user": "Analyse ce PDF\n📎 rapport.pdf", "attachments": [["C:/docs/rapport.pdf", "PDF"]],
         "image_path": None, "ai": None, "tail": []},
    ], "current": 1}}
    sessions.save_workspace(session_id, state)

    chat.service.load_session(session_id)
    snapshot = chat.service.snapshot()
    assert texts(snapshot) == ["Analyse ce PDF\n📎 rapport.pdf", "Le rapport décrit l'API."]
    assert all(message["mid"] for message in snapshot["messages"])
    assert snapshot["messages"][0]["attachments"][0]["type"] == "PDF"
    assert snapshot["messages"][0]["timestamp"] == "2026-10-06T09:12:40.123456"
    assert snapshot["branches"] == {mid: {"count": 2, "current": 1}}

    chat.service.navigate(mid, 0)
    assert texts(chat.service.snapshot()) == ["Lis ce PDF\n📎 rapport.pdf", "Ancienne réponse"]


# ── Chat mobile ─────────────────────────────────────────────────────────────


def test_mobile_message_is_answered_without_a_window(chat):
    bridge = FakeBridge()
    chat.service.attach_bridge(bridge)
    bridge.deliver(RelayMessage(text="Salut du téléphone", is_user=True, message_id="relay_1"))

    done = wait_for(chat.events, "assistant.done")[0]["payload"]
    user = wait_for(chat.events, "message.user")[0]["payload"]
    assert user["source"] == "mobile" and user["text"] == "Salut du téléphone"
    assert bridge.responses == [("relay_1", done["text"])]
    assert bridge.chunks and all(mid == "relay_1" for mid, _text in bridge.chunks)
    assert chat.service.snapshot()["messages"][0]["source"] == "mobile"
    assert chat.engine.command_history.queries == ["Salut du téléphone"]


def test_mobile_file_without_text_gets_the_default_request(chat):
    document = chat.tmp_path / "budget.xlsx"
    document.write_bytes(b"PK")
    bridge = FakeBridge()
    chat.service.attach_bridge(bridge)
    bridge.deliver(RelayMessage(text="", is_user=True, message_id="relay_2",
                                file_paths=[str(document)]))

    wait_for(chat.events, "assistant.done")
    assert ("process_query_stream", "Analyse ce fichier et résume-le.") in chat.engine.calls
    assert chat.engine.local_ai.added == [str(document)]
    assert texts(chat.service.snapshot())[0] == "📎 budget.xlsx"
    # Lu pour le téléphone : jamais oublié ensuite (aucune pièce jointe à retirer)
    assert "budget.xlsx" in chat.engine.local_ai.conversation_memory.stored_documents
    assert chat.engine.local_ai.removed == []


def test_desktop_answers_are_not_sent_to_the_mobile(chat):
    bridge = FakeBridge()
    chat.service.attach_bridge(bridge)
    ask(chat, "Question du PC")

    assert bridge.responses == [] and bridge.chunks == []


def test_mobile_stop_interrupts_its_own_answer(chat):
    gate = threading.Event()
    chat.engine.script = [("token", "Réponse partielle"), ("wait", gate)]
    bridge = FakeBridge()
    chat.service.attach_bridge(bridge)
    bridge.deliver(RelayMessage(text="Question", is_user=True, message_id="relay_3"))
    wait_for(chat.events, "assistant.token")

    bridge.interrupt = True
    wait_for(chat.events, "assistant.interrupted")
    assert bridge.responses == [("relay_3", "Réponse partielle\n\n⚠️ *Réponse interrompue.*")]


def test_mobile_stop_withdraws_its_queued_message_first(chat):
    gate = threading.Event()
    chat.engine.script = [("token", "Réponse du PC"), ("wait", gate)]
    bridge = FakeBridge()
    chat.service.attach_bridge(bridge)
    chat.service.send("Question du PC")
    wait_for(chat.events, "assistant.token")
    bridge.deliver(RelayMessage(text="Question mobile", is_user=True, message_id="relay_4"))

    bridge.interrupt = True
    deadline = time.time() + 5
    while not bridge.responses and time.time() < deadline:
        time.sleep(0.02)
    assert bridge.responses == [("relay_4", "⚠️ Réponse interrompue.")]
    assert chat.service.busy  # la réponse du PC continue
    gate.set()
    wait_for(chat.events, "assistant.done")


def test_real_relay_bridge_delivers_the_answer_to_its_message():
    bridge = RelayBridge()
    bridge.reset()
    try:
        engine_dir = __import__("tempfile").mkdtemp()
        engine = FakeEngine(engine_dir)
        bus = EventBus()
        events = []
        bus.subscribe(events.append)
        service = ChatService(engine, bus.publish, file_processor=FakeFileProcessor())
        service.start()
        service.attach_bridge(bridge)
        bridge.active = True
        message = RelayMessage(text="Bonjour", is_user=True)
        bridge.arm_response(message.message_id)
        bridge.send_to_gui(message)

        wait_for(events, "assistant.done")
        deadline = time.time() + 2
        pending = None
        while pending is None and time.time() < deadline:
            pending = bridge.peek_pending_response(message.message_id)
            time.sleep(0.01)
        assert pending == "Réponse à « Bonjour »"
        assert bridge.poll_gui_messages() == []
        service.close()
    finally:
        bridge.reset()


# ── Protocole ───────────────────────────────────────────────────────────────


def test_published_events_follow_the_protocol(chat):
    chat.engine.complex = True
    chat.engine.script = [
        ("thinking", "Réflexion"), ("thinking_done",),
        ("token", "Je cherche.\n"),
        ("tool", "web_search", {"query": "x" * 1000}),
        ("tool_result", "web_search", {"query": "x"}, "[1] https://a.example"),
        ("tool", "synthesis", {}),
        ("document", "C:/out/doc.docx"),
        ("token", "Fin."),
    ]
    document = chat.tmp_path / "notes.md"
    document.write_text("# notes", encoding="utf-8")
    chat.service.add_attachment(str(document))
    wait_for(chat.events, "attachment.ready")
    ask(chat, "Compare et cherche")
    chat.service.new_conversation()

    for event in chat.events:
        validate_event(event)
    seqs = [event["seq"] for event in chat.events]
    assert seqs == sorted(seqs) and len(set(seqs)) == len(seqs)
    # Arguments d'outil allégés pour la fenêtre
    call = wait_for(chat.events, "tool.call")[0]["payload"]
    assert len(call["args"]["query"]) < 1000


# ── Notes, fichiers, dossiers, export (phase 3) ─────────────────────────────


def test_rating_is_recorded_with_its_question_then_frozen(chat):
    rlhf = FakeRLHF()
    chat.service._rlhf_manager = rlhf  # pylint: disable=protected-access
    done = ask(chat, "Explique les tuples")
    assert chat.service.rate(done["mid"], 4) == 4
    assert rlhf.records == [{
        "user_query": "Explique les tuples", "ai_response": "Réponse à « Explique les tuples »",
        "feedback_type": "positive", "feedback_score": 4, "intent": "conversation",
        "confidence": 1.0, "model_version": "ollama",
    }]
    rated = wait_for(chat.events, "message.rated")[0]
    assert rated["payload"] == {"mid": done["mid"], "rating": 4}
    # Gardée dans la session (clé optionnelle, D7), et figée comme dans Tk
    assert chat.service.snapshot()["messages"][1]["rating"] == 4
    state = chat.engine.session_manager.load_workspace(chat.service.session_id)
    assert state["conversation_history"][1]["rating"] == 4
    with pytest.raises(ChatError, match="déjà notée"):
        chat.service.rate(done["mid"], 2)
    with pytest.raises(ChatError, match="de 1 à 5"):
        chat.service.rate(done["mid"], 6)
    user_mid = chat.service.snapshot()["messages"][0]["mid"]
    with pytest.raises(ChatError, match="introuvable"):
        chat.service.rate(user_mid, 3)


def test_rating_types_follow_tk(chat):
    rlhf = FakeRLHF()
    chat.service._rlhf_manager = rlhf  # pylint: disable=protected-access
    mids = [ask(chat, f"Question {n}")["mid"] for n in range(3)]
    for mid, score in zip(mids, (1, 3, 5)):
        chat.service.rate(mid, score)
    assert [r["feedback_type"] for r in rlhf.records] == ["negative", "neutral", "positive"]


def test_existing_paths_in_an_answer_become_links(chat):
    target = chat.tmp_path / "rapport final.docx"
    target.write_text("x", encoding="utf-8")
    chat.engine.script = [("token", f"Le fichier est dans {target}. Voir aussi C:/absent/x.txt.")]
    done = ask(chat, "Où est le rapport ?")
    assert done["paths"] == [{"text": str(target), "path": os.path.normpath(str(target))}]
    view = chat.service.snapshot()["messages"][1]
    assert view["paths"] == done["paths"]
    # Les messages de l'utilisateur ne sont pas concernés
    assert "paths" not in chat.service.snapshot()["messages"][0]


def test_known_paths_cover_attachments_and_produced_files(chat):
    joined = chat.tmp_path / "joint.md"
    joined.write_text("# joint", encoding="utf-8")
    chat.service.add_attachment(str(joined))
    wait_for(chat.events, "attachment.ready")
    pending = os.path.normcase(os.path.abspath(str(joined)))
    assert pending in chat.service.known_paths()
    chat.engine.script = [("document", str(chat.tmp_path / "outputs" / "doc.docx")),
                          ("token", "Voici.")]
    ask(chat, "Rédige un document")
    known = chat.service.known_paths()
    assert pending in known
    assert os.path.normcase(os.path.abspath(str(chat.tmp_path / "outputs" / "doc.docx"))) in known


def test_memory_changes_the_open_conversation_at_its_source(chat):
    ask(chat, "Question A")
    ask(chat, "Question B")
    session = chat.service.session_id
    texts = [m["text"] for m in chat.service.snapshot()["messages"]]
    answer_a = texts[1]

    # Index noté par la recherche, puis vieilli : le texte fait foi
    chat.service.change_saved_message(session, 0, "Question A", None)
    chat.service.change_saved_message(session, 2, "Question B", "Question B, précisée")

    shown = [m["text"] for m in chat.service.snapshot()["messages"]]
    assert shown == [answer_a, "Question B, précisée", texts[3]]
    saved = chat.engine.session_manager.load_workspace(session)["conversation_history"]
    assert [m["text"] for m in saved] == shown
    assert wait_for(chat.events, "conversation.loaded")[-1]["payload"]["reason"] == "edited"

    with pytest.raises(ChatError, match="introuvable"):
        chat.service.change_saved_message(session, 0, "Jamais dit", None)


def test_memory_changes_another_conversation_without_touching_the_open_one(chat):
    ask(chat, "Ancienne question")
    old = chat.service.session_id
    chat.service.new_conversation()
    ask(chat, "Nouvelle question")

    chat.service.change_saved_message(old, 0, "Ancienne question", "Question reformulée")
    saved = chat.engine.session_manager.load_workspace(old)["conversation_history"]
    assert saved[0]["text"] == "Question reformulée"
    assert chat.service.snapshot()["messages"][0]["text"] == "Nouvelle question"
    with pytest.raises(ChatError, match="introuvable"):
        chat.service.change_saved_message("session-inconnue", 0, "x", None)


def test_project_folder_attaches_to_the_current_session_or_a_new_one(chat):
    session_id = chat.service.ensure_session("mon-projet")
    assert session_id and chat.service.session_id == session_id
    sessions = chat.service.list_sessions()
    assert sessions[0]["name"] == "mon-projet" and sessions[0]["current"]
    # Une session existe déjà : elle sert, et le premier message y reste
    assert chat.service.ensure_session("autre") == session_id
    ask(chat, "Bonjour")
    assert chat.service.session_id == session_id


def test_export_messages_use_the_exporter_format(chat):
    ask(chat, "Bonjour")
    assert chat.service.export_messages() == [
        {"role": "user", "content": "Bonjour"},
        {"role": "assistant", "content": "Réponse à « Bonjour »"},
    ]


def test_a_variant_keeps_its_whole_answer(chat):
    """Revenir à une variante rend sa réponse entière : outils, documents, note (D7)."""
    chat.service._rlhf_manager = FakeRLHF()  # pylint: disable=protected-access
    chat.engine.script = [("tool", "web_search", {"query": "café"}),
                          ("tool_result", "web_search", {}, "[1] https://a.example"),
                          ("document", "C:/out/cafe.docx"), ("token", "Le café…")]
    first = ask(chat, "Parle du café")
    chat.service.rate(first["mid"], 5)
    user_mid = chat.service.snapshot()["messages"][0]["mid"]
    chat.engine.script = [("token", "Autre version")]
    chat.service.send("", edit_mid=user_mid, regenerate=True)
    wait_for(chat.events, "assistant.done", 2)
    chat.service.navigate(user_mid, 0)
    answer = chat.service.snapshot()["messages"][1]
    assert answer["text"] == "Le café…" and answer["rating"] == 5
    assert answer["documents"] == ["C:/out/cafe.docx"]
    assert answer["tool_calls"][0]["name"] == "web_search"
    # Variante enregistrée par Tk (sans « ai_extra ») : la réponse reste lisible
    branch = chat.service._branches[user_mid]  # pylint: disable=protected-access
    branch["versions"][1].pop("ai_extra")
    chat.service.navigate(user_mid, 1)
    assert chat.service.snapshot()["messages"][1]["text"] == "Autre version"
