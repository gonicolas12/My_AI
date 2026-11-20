"""
Conversation Code (relay/code_hub.py) : le chat de l'extension VS Code, partagé
avec la page Code du PC et la vue Code du téléphone.

Avant, l'extension VS Code recevait les réponses du chat du téléphone (le
Relay les diffusait à tous ses WebSockets) et son historique était celui du
téléphone ; ses propres échanges n'allaient nulle part ailleurs. Désormais
le chat du téléphone et du PC d'un côté, la conversation Code de l'autre :
un message envoyé de VS Code, du PC ou du téléphone y paraît sur les trois
surfaces, réponse en streaming, appels d'outils et approbations compris.

La boucle agentique est simulée (pas d'Ollama) ; la boucle asyncio du Relay
tourne dans un fil, comme dans l'appli.
"""

import asyncio
import json
import threading
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from core.agentic_executor import RemoteToolExecutor, build_system_prompt
from core.code_memory import CodeMemory
from core.i18n import tr
from core.knowledge_base_manager import KnowledgeBaseManager
from interfaces.desktop import files as local_files
from interfaces.desktop.code import CodeService
from interfaces.desktop.events import EventBus, validate_event
from interfaces.desktop.server import DesktopServer
from relay import code_hub as hub_module
from relay.code_hub import CodeError, CodeHub, mobile_view, vscode_view
from test_desktop_server import AUTH, BASE, PORT, FakeApp  # pylint: disable=import-error

LLM = {"chat_url": "http://ollama.invalid/api/chat", "model": "my_ai", "num_ctx": 32768}


def wait_until(predicate, timeout=3.0):
    """Attend qu'une condition devienne vraie (événements livrés par un autre fil)."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        if predicate():
            return
        time.sleep(0.01)
    raise AssertionError("condition jamais remplie")


class FakeExecutor:
    """AgenticExecutor simulé : `script` reçoit les arguments de run()."""

    script = None
    created = []

    def __init__(self, **kwargs):
        self.kwargs = kwargs
        FakeExecutor.created.append(self)

    async def run(self, **kwargs):
        return await FakeExecutor.script(kwargs)


async def say_hello(run):
    run["on_chunk"]("Bon", 0)
    run["on_chunk"]("Bonjour !", 0)
    return "Bonjour !"


async def write_a_file(run):
    run["on_chunk"]("J'écris le fichier.", 0)
    call = {"call_id": "c1", "name": "write_file",
            "input": {"path": "a.txt", "content": "x" * 5000}}
    run["on_tool_call_announced"](call)
    result = await run["tool_executor"].call(call_id="c1", name="write_file",
                                             input_data=call["input"])
    run["on_tool_result"]("c1", result)
    run["on_chunk"]("C'est fait.", 1)
    return "J'écris le fichier.\n\nC'est fait."


async def write_forever(run):
    text = ""
    while True:
        text += "mot "
        run["on_chunk"](text, 0)
        await asyncio.sleep(0.02)


@pytest.fixture(name="loop")
def loop_fixture():
    """Boucle asyncio du Relay, dans son fil."""
    loop = asyncio.new_event_loop()
    thread = threading.Thread(target=loop.run_forever, daemon=True)
    thread.start()
    yield loop
    loop.call_soon_threadsafe(loop.stop)
    thread.join(timeout=2)
    loop.close()


@pytest.fixture(name="hub")
def hub_fixture(tmp_path, monkeypatch):
    monkeypatch.setattr(hub_module, "AgenticExecutor", FakeExecutor)
    FakeExecutor.script = say_hello
    FakeExecutor.created = []
    hub = CodeHub(store=tmp_path / "code_conversation.json")
    hub.set_llm_resolver(lambda: dict(LLM))
    return hub


class Surface:
    """Une surface abonnée : messages reçus dans le protocole du Relay."""

    def __init__(self):
        self.messages = []
        self._lock = threading.Lock()

    def put(self, message):
        if message is not None:
            with self._lock:
                self.messages.append(message)

    def types(self):
        with self._lock:
            return [m["type"] for m in self.messages]

    def of(self, kind):
        with self._lock:
            return [m for m in self.messages if m["type"] == kind]


def connect_vscode(hub, loop, workspace="My_AI"):
    """Extension VS Code : son lien (tool_use…) et sa vue de la conversation."""
    surface = Surface()
    info = f"Workspace folders:\n- {workspace} (C:\\dev\\{workspace})\nPlatform: win32"
    link = hub.connect_vscode(loop, surface.put, info)
    hub.subscribe(lambda event: surface.put(vscode_view(event, link.id)), snapshot=True)
    return link, surface


def subscribe_phone(hub):
    phone = Surface()
    hub.subscribe(lambda event: phone.put(mobile_view(event)), snapshot=True)
    return phone


def test_phone_message_streams_to_vscode_and_back(hub, loop):
    link, vscode = connect_vscode(hub, loop)
    phone = subscribe_phone(hub)
    assert phone.of("code_snapshot")[0]["state"]["workspace"] == "My_AI"

    message_id = hub.send("Salut", "mobile")
    wait_until(lambda: phone.of("code_done"))

    # L'extension voit le message du téléphone, puis la réponse en streaming
    user = vscode.of("code_user")[0]
    assert (user["message_id"], user["text"], user["origin"]) == (message_id, "Salut", "mobile")
    assert [c["text"] for c in vscode.of("chunk")] == ["Bon", "Bonjour !"]
    assert vscode.of("chunk")[-1]["segment_index"] == 0
    response = vscode.of("response")[0]
    assert (response["message_id"], response["message"], response["status"]) == (
        message_id, "Bonjour !", "done")
    # Sa durée, sous la bulle comme sur le téléphone
    assert response["duration_ms"] == phone.of("code_done")[0]["duration_ms"] >= 0
    # Le téléphone aussi, dans son protocole
    assert phone.types()[1:] == ["code_user", "code_state", "code_chunk", "code_chunk",
                                 "code_done", "code_state"]
    assert phone.of("code_state")[0]["busy"] is True
    assert phone.of("code_state")[-1]["busy"] is False
    # Transcription : la question, puis la réponse et son texte, à sa place
    messages = hub.snapshot()["messages"]
    assert [m["role"] for m in messages] == ["user", "assistant"]
    assert messages[1]["parts"] == [{"kind": "text", "segment": 0, "text": "Bonjour !"}]
    assert messages[1]["status"] == "done"
    assert link.pending == {}


def test_vscode_message_is_acknowledged_to_its_own_extension(hub, loop):
    link, vscode = connect_vscode(hub, loop)
    other_link, other = connect_vscode(hub, loop, workspace="api")
    message_id = hub.send("Explique ce fichier", "vscode", client=link.id)
    wait_until(lambda: vscode.of("response"))
    # Son texte avec : « Envoyer la sélection » ne passe pas par la zone de saisie
    ack = vscode.of("ack")[0]
    assert (ack["message_id"], ack["text"], ack["origin"]) == (
        message_id, "Explique ce fichier", "vscode")
    assert not vscode.of("code_user")
    # L'autre fenêtre VS Code le voit comme un message venu d'ailleurs
    assert other.of("code_user")[0]["origin"] == "vscode"
    # Les outils de ce message sont pour l'extension d'où il part
    assert FakeExecutor.created[0].kwargs["model"] == "my_ai"
    assert other_link is not link


def test_tool_call_runs_in_vscode_and_is_approved_from_the_phone(hub, loop):
    FakeExecutor.script = write_a_file
    link, vscode = connect_vscode(hub, loop)
    phone = subscribe_phone(hub)
    message_id = hub.send("Écris a.txt", "mobile")

    # L'extension reçoit l'appel, avec l'origine du message
    wait_until(lambda: vscode.of("tool_use"))
    tool_use = vscode.of("tool_use")[0]
    assert (tool_use["call_id"], tool_use["name"], tool_use["origin"]) == (
        "c1", "write_file", "mobile")
    assert tool_use["message_id"] == message_id
    # Le téléphone voit l'appel, ses longs arguments coupés
    requested = phone.of("code_tool")[0]
    assert requested["status"] == "requested"
    assert len(requested["input"]["content"]) < 2100

    # Approbation demandée dans l'extension : montrée au téléphone, répondue de là
    loop.call_soon_threadsafe(hub.tool_status, link, "c1", "awaiting-approval",
                              ["allow-once", "allow-target", "allow-tool", "deny"])
    wait_until(lambda: any(t["status"] == "awaiting-approval" for t in phone.of("code_tool")))
    assert hub.approve("c1", "launch-missiles") is False
    assert hub.approve("c1", "allow-once") is True
    assert vscode.of("tool_approval") == [
        {"type": "tool_approval", "call_id": "c1", "decision": "allow-once"}]

    loop.call_soon_threadsafe(hub.tool_status, link, "c1", "running", None)
    loop.call_soon_threadsafe(hub.tool_result, link, "c1", "Fichier écrit.", False)
    wait_until(lambda: phone.of("code_done"))

    statuses = [t["status"] for t in phone.of("code_tool")]
    assert statuses == ["requested", "awaiting-approval", "running", "completed"]
    assert phone.of("code_tool")[-1]["output"] == "Fichier écrit."
    parts = hub.snapshot()["messages"][1]["parts"]
    assert [p["kind"] for p in parts] == ["text", "tool", "text"]
    assert parts[1]["status"] == "completed" and "options" not in parts[1]


def test_approval_of_a_vscode_message_stays_in_vscode(hub, loop):
    """Message tapé dans VS Code : la fenêtre de confirmation de VS Code décide seule."""
    FakeExecutor.script = write_a_file
    link, vscode = connect_vscode(hub, loop)
    phone = subscribe_phone(hub)
    hub.send("Écris a.txt", "vscode", client=link.id)
    wait_until(lambda: vscode.of("tool_use"))
    assert vscode.of("tool_use")[0]["origin"] == "vscode"
    loop.call_soon_threadsafe(hub.tool_status, link, "c1", "awaiting-approval", None)
    wait_until(lambda: any(t["status"] == "awaiting-approval" for t in phone.of("code_tool")))
    assert phone.of("code_tool")[-1]["options"] == []
    assert hub.approve("c1", "allow-once") is False
    loop.call_soon_threadsafe(hub.tool_status, link, "c1", "denied", None)
    loop.call_soon_threadsafe(hub.tool_result, link, "c1", "Refusé.", True)
    wait_until(lambda: phone.of("code_done"))
    assert phone.of("code_tool")[-1]["status"] == "denied"


def test_waiting_for_an_approval_does_not_time_out():
    """Approbation en attente : pas de délai ; il repart de zéro une fois répondue."""
    async def scenario():
        loop = asyncio.get_running_loop()
        sent, pending, waiting = [], {}, {"c1"}

        async def send(payload):
            sent.append(payload)

        executor = RemoteToolExecutor(send, pending, "m1", loop, default_timeout=0.2,
                                      origin="desktop", keep_waiting=lambda cid: cid in waiting)
        task = asyncio.ensure_future(executor.call("c1", "run_command", {"command": "ls"}))
        await asyncio.sleep(0.5)               # bien plus que le délai : toujours en attente
        assert not task.done()
        waiting.clear()                         # l'utilisateur a répondu
        await asyncio.sleep(0.1)
        assert not task.done()                  # le délai repart de zéro
        pending["c1"].set_result({"content": "ok", "is_error": False})
        assert (await task)["content"] == "ok"
        assert sent[0]["origin"] == "desktop"

        timed_out = RemoteToolExecutor(send, {}, "m2", loop, default_timeout=0.1)
        with pytest.raises(asyncio.TimeoutError):
            await timed_out.call("c2", "read_file", {"path": "a"})

    asyncio.run(scenario())


def test_stop_from_any_surface_ends_the_reply(hub, loop):
    FakeExecutor.script = write_forever
    link, vscode = connect_vscode(hub, loop)
    phone = subscribe_phone(hub)
    message_id = hub.send("Écris longtemps", "desktop")
    wait_until(lambda: len(phone.of("code_chunk")) >= 3)

    assert hub.stop() is True
    wait_until(lambda: phone.of("code_done"))
    done = phone.of("code_done")[0]
    assert done["status"] == "stopped" and done["text"].startswith("mot mot mot")
    # L'extension oublie ses approbations en attente, puis voit la fin « interrompue »
    assert {"type": "code_stop", "message_id": message_id} in vscode.messages
    assert vscode.of("response")[0]["status"] == "stopped"
    assert hub.state()["busy"] is False
    count = len(phone.of("code_chunk"))
    time.sleep(0.15)
    assert len(phone.of("code_chunk")) == count  # plus rien ne s'écrit
    assert hub.stop() is False
    assert link.pending == {}


def test_clear_starts_a_new_conversation_everywhere(hub, loop, tmp_path):
    _link, vscode = connect_vscode(hub, loop)
    hub.send("Salut", "vscode")
    wait_until(lambda: vscode.of("response"))
    assert hub._llm_history  # pylint: disable=protected-access

    hub.clear()
    assert vscode.of("code_cleared") == [{"type": "code_cleared"}]
    assert hub.snapshot()["messages"] == []
    assert hub._llm_history == []  # pylint: disable=protected-access
    saved = json.loads((tmp_path / "code_conversation.json").read_text(encoding="utf-8"))
    assert saved["messages"] == [] and saved["llm"] == []


def test_clear_during_a_reply_stops_it_without_writing_it(hub, loop):
    FakeExecutor.script = write_forever
    _link, vscode = connect_vscode(hub, loop)
    phone = subscribe_phone(hub)
    hub.send("Écris longtemps", "mobile")
    wait_until(lambda: phone.of("code_chunk"))
    hub.clear()
    wait_until(lambda: not hub.state()["busy"])
    time.sleep(0.1)
    assert not phone.of("code_done")
    assert hub.snapshot()["messages"] == []
    assert vscode.of("code_state")[-1]["busy"] is False


def test_messages_are_refused_without_vscode_or_during_a_reply(hub, loop):
    with pytest.raises(CodeError):
        hub.send("Salut", "desktop")  # aucune extension connectée
    FakeExecutor.script = write_forever
    connect_vscode(hub, loop)
    with pytest.raises(CodeError):
        hub.send("   ", "desktop")
    hub.send("Écris longtemps", "desktop")
    with pytest.raises(CodeError):
        hub.send("Encore", "mobile")
    hub.stop()


def test_vscode_disconnect_stops_its_reply(hub, loop):
    FakeExecutor.script = write_a_file
    link, vscode = connect_vscode(hub, loop)
    phone = subscribe_phone(hub)
    hub.send("Écris a.txt", "mobile")
    wait_until(lambda: vscode.of("tool_use"))
    hub.disconnect_vscode(link)
    wait_until(lambda: phone.of("code_done"))
    assert phone.of("code_done")[0]["status"] == "error"
    assert phone.of("code_state")[-1] == {"type": "code_state", "vscode": False,
                                          "workspace": None, "busy": False,
                                          "message_id": None, "origin": None}
    assert hub.snapshot()["messages"][1]["parts"][1]["status"] == "stopped"


def test_conversation_and_model_history_survive_a_restart(hub, loop, tmp_path):
    _link, vscode = connect_vscode(hub, loop)
    hub.send("Salut", "vscode")
    store = tmp_path / "code_conversation.json"
    wait_until(lambda: vscode.of("response") and store.exists())  # écrit après la fin
    saved = json.loads(store.read_text(encoding="utf-8"))
    # Appli tuée pendant une réponse : elle redevient « arrêtée »
    saved["messages"][1]["status"] = "streaming"
    store.write_text(json.dumps(saved), encoding="utf-8")

    restarted = CodeHub(store=store)
    messages = restarted.snapshot()["messages"]
    assert [m["text"] for m in messages if m["role"] == "user"] == ["Salut"]
    assert messages[1]["status"] == "stopped"
    assert restarted._llm_history[0]["role"] == "system"  # pylint: disable=protected-access


def test_system_prompt_follows_the_workspace_and_the_language(hub, loop):
    _link, vscode = connect_vscode(hub, loop, workspace="api")
    hub.send("Salut", "vscode")
    wait_until(lambda: vscode.of("response"))
    system = FakeExecutor.created[0].kwargs  # constructeur : modèle et fenêtre
    assert system["num_ctx"] == 32768
    prompt = hub._llm_history[0]["content"]  # pylint: disable=protected-access
    assert "- api (C:\\dev\\api)" in prompt
    assert "(français par défaut)" in prompt
    assert "(anglais par défaut)" in build_system_prompt("", language="en")


def relay_message(ws, server, timeout=10.0):
    """Message suivant du Relay, déchiffré.

    receive_text() du TestClient attend sans fin : un message perdu bloquait
    toute la suite. Ici, il fait échouer le test.
    """
    received = {}

    def receive():
        try:
            received["text"] = ws.receive_text()
        except BaseException as exc:  # pylint: disable=broad-exception-caught
            received["error"] = exc

    reader = threading.Thread(target=receive, daemon=True)
    reader.start()
    reader.join(timeout)
    if reader.is_alive():
        raise AssertionError(f"aucun message du Relay en {timeout:g} s")
    if "error" in received:
        raise received["error"]
    return server.decrypt_json(json.loads(received["text"]))


def relay_send(ws, server, payload):
    ws.send_text(json.dumps(server.encrypt_json(payload)))


def test_relay_keeps_the_phone_chat_away_from_vscode(hub):
    """Captures du 2026-10-27 : « Tout va bien… », réponse au téléphone, paraissait dans VS Code."""
    testclient = pytest.importorskip("fastapi.testclient")
    from relay.relay_server import RelayServer  # pylint: disable=import-outside-toplevel

    server = RelayServer(config={}, code_hub=hub)
    # `with` : une seule boucle asyncio pour toutes les connexions, comme uvicorn
    # dans l'appli. Sans lui, chaque WebSocket du TestClient avait sa boucle, dans
    # son fil : _broadcast_chunk écrivait au téléphone depuis la boucle de VS Code,
    # dans un flux mémoire anyio qui n'est pas thread-safe, et le réveil du lecteur
    # se perdait (le test bloquait 7 fois sur 40).
    with testclient.TestClient(server._app) as client:  # pylint: disable=protected-access
        unlocked = server.decrypt_json(client.post(
            f"/api/unlock?token={server.auth_token}",
            json=server.encrypt_json({"code": server.access_code})).json())
        url = f"/ws?token={server.auth_token}&session={unlocked['session']}"
        with client.websocket_connect(url) as vscode_ws, client.websocket_connect(url) as phone_ws:
            relay_send(vscode_ws, server, {
                "type": "client_hello", "client_kind": "vscode",
                "workspace_info": "Workspace folders:\n- My_AI (C:\\dev\\My_AI)"})
            hello = relay_message(vscode_ws, server)
            assert hello["type"] == "hello_ack" and hello["code"] is True
            assert hello["language"] == "fr"
            assert relay_message(vscode_ws, server)["type"] == "code_snapshot"

            # Réponse du chat du téléphone (bridge) : au téléphone seulement.
            # Boucle du Relay : celle du TestClient, où tournent les deux WebSockets
            loop = client.portal.call(asyncio.get_running_loop)
            assert hub._links[-1].loop is loop  # pylint: disable=protected-access
            server._loop = loop  # pylint: disable=protected-access
            server._broadcast_chunk("relay_1", "Tout va bien")  # pylint: disable=protected-access
            assert relay_message(phone_ws, server)["text"] == "Tout va bien"
            relay_send(vscode_ws, server, {"type": "ping"})
            assert relay_message(vscode_ws, server)["type"] == "pong"

            # Vue Code du téléphone : message à l'extension, réponse aux deux
            relay_send(phone_ws, server, {"type": "code_subscribe"})
            snapshot = relay_message(phone_ws, server)
            assert snapshot["type"] == "code_snapshot"
            assert snapshot["state"]["workspace"] == "My_AI"
            relay_send(phone_ws, server, {"type": "code_chat", "message": "Salut"})
            phone_types = []
            while "code_done" not in phone_types:
                phone_types.append(relay_message(phone_ws, server)["type"])
            assert phone_types[:2] == ["code_user", "code_state"]
            vscode_messages = []
            while not any(m["type"] == "response" for m in vscode_messages):
                vscode_messages.append(relay_message(vscode_ws, server))
            assert vscode_messages[0]["type"] == "code_user"
            assert vscode_messages[0]["origin"] == "mobile"
            assert vscode_messages[-1]["message"] == "Bonjour !"

            # L'historique du téléphone reste le sien
            history = server.decrypt_json(client.get(
                f"/api/history?token={server.auth_token}&session={unlocked['session']}").json())
            assert all("Salut" != item["text"] for item in history["history"])


def test_desktop_page_follows_the_conversation_through_the_bus(hub, loop):
    bus = EventBus()
    seen = []
    bus.subscribe(seen.append)
    service = CodeService(hub, bus.publish, lambda: bus.last_seq)
    connect_vscode(hub, loop)
    message_id = service.send("Salut")
    wait_until(lambda: any(e["type"] == "code.done" for e in seen))
    for event in seen:
        validate_event(event)
    assert [e["type"] for e in seen] == ["code.state", "code.user", "code.state", "code.chunk",
                                         "code.chunk", "code.done", "code.state"]
    user = next(e for e in seen if e["type"] == "code.user")
    assert user["message_id"] == message_id and user["payload"]["origin"] == "desktop"
    snapshot = service.snapshot()
    assert snapshot["seq"] == bus.last_seq and len(snapshot["messages"]) == 2
    service.close()


def test_desktop_attachments_reach_the_model(hub, loop, tmp_path):
    """La page Code joint les fichiers du chat : le modèle lit le code et les
    documents, le modèle vision décrit les images (comme dans les Agents) ;
    VS Code et le téléphone voient leurs noms. Avant, la page n'avait pas de
    pièces jointes, et une image venue du Relay n'était pas lue."""
    code = tmp_path / "app.py"
    code.write_text("print('bonjour')", encoding="utf-8")
    image = tmp_path / "maquette.png"
    Image.new("RGB", (40, 20), "white").save(image)
    folder = tmp_path / "docs"
    folder.mkdir()
    (folder / "notes.md").write_text("# Notes de version", encoding="utf-8")
    (tmp_path / "data.bin").write_bytes(b"\x00\x01")

    questions = []

    def describe(image_b64, question):
        assert image_b64
        questions.append(question)
        return "Un formulaire de connexion."

    hub.set_llm_resolver(lambda: {**LLM, "describe_image": describe})
    prompts = []

    async def read_the_prompt(run):
        prompts.append(run["user_message"])
        return "Vu."

    FakeExecutor.script = read_the_prompt
    bus = EventBus()
    service = CodeService(hub, bus.publish, lambda: bus.last_seq)
    _link, vscode = connect_vscode(hub, loop)
    phone = subscribe_phone(hub)

    # Fichiers choisis ou déposés : vérifiés comme dans le chat, un dossier joint ses fichiers
    checked = service.inspect([str(code), str(image), str(folder), str(tmp_path / "data.bin"),
                               str(tmp_path / "absent.py")])
    assert [(item["name"], item["type"]) for item in checked["attachments"]] == [
        ("app.py", "Code"), ("maquette.png", "Image"), ("notes.md", "Code")]
    assert len(checked["refused"]) == 2
    # La fenêtre peut afficher leurs vignettes
    assert local_files.normalize(str(image)) in service.known_paths()

    service.send("Fais cette page", [(item["path"], item["name"])
                                     for item in checked["attachments"]])
    wait_until(lambda: vscode.of("response"))
    prompt = prompts[0]
    assert prompt.startswith("Fais cette page\n\n")
    assert "Pièce jointe « app.py » :\n```\nprint('bonjour')\n```" in prompt
    assert ("Image jointe « maquette.png », décrite par le modèle vision :\n"
            "Un formulaire de connexion.") in prompt
    assert "# Notes de version" in prompt
    assert questions == ["Fais cette page"]
    names = ["app.py", "maquette.png", "notes.md"]
    assert vscode.of("code_user")[0]["attachments"] == names
    assert phone.of("code_user")[0]["attachments"] == names
    service.close()


def test_attachments_stay_within_the_context_window(tmp_path):
    """Les pièces jointes d'un message prennent au plus leur part de la fenêtre
    de contexte : au-delà, les suivantes sont citées sans leur texte. Sans
    modèle qui voit les images, le modèle sait qu'une image n'a pas été lue."""
    big = tmp_path / "big.txt"
    big.write_text("a" * 50_000, encoding="utf-8")
    small = tmp_path / "small.txt"
    small.write_text("b" * 10, encoding="utf-8")
    image = tmp_path / "capture.png"
    Image.new("RGB", (10, 10), "black").save(image)
    files = [(str(big), "big.txt"), (str(small), "small.txt"), (str(image), "capture.png")]

    text = hub_module._attachment_blocks(files, None, "", room=20_000)
    assert "a" * 20_000 + "…" in text and "a" * 20_001 not in text
    assert "[Pièce jointe « small.txt » non lue : trop de texte joint à ce message]" in text
    assert "[Image jointe « capture.png » : aucun modèle ne voit les images" in text


def test_code_page_routes_attach_and_send_files(hub, loop, tmp_path):
    """Routes de la page Code : fichiers vérifiés (vignettes comprises), image
    collée, message parti avec ses seules pièces jointes."""
    bus = EventBus()
    app = FakeApp(None, bus)
    app.code = CodeService(hub, bus.publish, lambda: bus.last_seq)
    app.code_attachments = app.code.known_paths
    server = DesktopServer(app)
    server.port = PORT
    client = TestClient(server.fastapi, base_url=BASE)

    image = tmp_path / "capture.png"
    Image.new("RGB", (8, 8), "white").save(image)
    picked = client.post("/api/code/attachments", headers=AUTH,
                         json={"paths": [str(image)]}).json()
    assert picked["attachments"][0]["type"] == "Image" and picked["refused"] == []
    links = client.post("/api/files/links", headers=AUTH,
                        json={"paths": [str(image)]}).json()["links"]
    assert links[str(image)]  # vignette de la page Code
    uploaded = client.post("/api/code/attachments/upload", headers=AUTH,
                           files={"file": ("clipboard_image.png", image.read_bytes(),
                                           "image/png")}).json()
    item = uploaded["attachments"][0]
    assert item["name"] == "clipboard_image.png" and Path(item["path"]).is_file()

    prompts = []

    async def read_the_prompt(run):
        prompts.append(run["user_message"])
        return "Vu."

    FakeExecutor.script = read_the_prompt
    _link, vscode = connect_vscode(hub, loop)
    sent = client.post("/api/code/send", headers=AUTH,
                       json={"text": "", "files": [{"path": str(image), "name": "capture.png"}]})
    assert sent.status_code == 200
    wait_until(lambda: vscode.of("response"))
    assert prompts[0].startswith("Regarde les fichiers joints.\n\n[Image jointe « capture.png »")
    app.code.close()


def test_desktop_page_links_the_files_a_reply_cites(hub, loop, tmp_path):
    """Page Code de la fenêtre : comme le chat, les pièces jointes d'un message
    ont leur type (vignette d'une image) et une réponse terminée les fichiers
    qu'elle cite ou nomme, chemins relatifs au workspace de VS Code compris ;
    la fenêtre peut en montrer l'aperçu. Après un redémarrage, VS Code fermé,
    les liens restent (dossiers gardés avec la réponse). Avant, la page n'avait
    ni volet d'aperçu ni liens."""
    workspace = tmp_path / "ws"
    (workspace / "src" / "lib").mkdir(parents=True)
    for relative in ("README.md", "src/app.ts", "src/lib/shell.ts"):
        (workspace / relative).write_text("x", encoding="utf-8")
    notes = tmp_path / "notes.txt"
    notes.write_text("Notes", encoding="utf-8")

    async def edit_and_cite(run):
        run["on_tool_call_announced"]({"call_id": "c1", "name": "edit_file",
                                       "input": {"path": "src/lib/shell.ts"}})
        run["on_tool_result"]("c1", {"content": "ok", "is_error": False})
        text = "J'ai lu src/app.ts et notes.txt, modifié shell.ts ; voir README.md."
        run["on_chunk"](text, 0)
        return text

    FakeExecutor.script = edit_and_cite
    bus = EventBus()
    seen = []
    bus.subscribe(seen.append)
    service = CodeService(hub, bus.publish, lambda: bus.last_seq)
    surface = Surface()
    hub.connect_vscode(loop, surface.put,
                       f"Workspace folders:\n- ws ({workspace})\nPlatform: win32")
    service.send("Regarde", [(str(notes), "notes.txt")])
    # La conversation est écrite après la fin : le redémarrage plus bas la relit
    store = tmp_path / "code_conversation.json"
    wait_until(lambda: any(e["type"] == "code.done" for e in seen) and store.exists())
    for event in seen:
        validate_event(event)
    user = next(e for e in seen if e["type"] == "code.user")["payload"]
    assert user["files"] == [{"name": "notes.txt", "path": str(notes), "type": "Code"}]
    done = next(e for e in seen if e["type"] == "code.done")["payload"]
    expected = {
        "src/app.ts": str(workspace / "src" / "app.ts"),
        "notes.txt": str(notes),
        "shell.ts": str(workspace / "src" / "lib" / "shell.ts"),
        "README.md": str(workspace / "README.md"),
    }
    assert {link["text"]: link["path"] for link in done["paths"]} == expected
    # La fenêtre peut montrer leur aperçu
    known = service.known_paths()
    assert all(local_files.normalize(path) in known for path in expected.values())

    # Lecture de la page : mêmes liens, sans les dossiers du workspace
    snapshot = service.snapshot()
    reply = snapshot["messages"][1]
    assert {link["text"] for link in reply["paths"]} == set(expected)
    assert "roots" not in reply
    assert snapshot["messages"][0]["files"][0]["type"] == "Code"
    service.close()

    # Redémarrage, VS Code fermé : les chemins relatifs restent des liens
    again = CodeHub(store=store)
    restarted = CodeService(again, EventBus().publish, lambda: 0)
    reply = restarted.snapshot()["messages"][1]
    assert {link["text"] for link in reply["paths"]} == set(expected)

    # Route de la fenêtre : le fichier cité a son lien signé (aperçu, vignette)
    app = FakeApp(None, EventBus())
    app.code = restarted
    app.code_attachments = restarted.known_paths
    server = DesktopServer(app)
    server.port = PORT
    client = TestClient(server.fastapi, base_url=BASE)
    cited = str(workspace / "src" / "app.ts")
    links = client.post("/api/files/links", headers=AUTH, json={"paths": [cited]}).json()["links"]
    assert links[cited]
    restarted.close()


def test_phone_code_view_links_the_files_a_reply_cites(hub, loop, tmp_path):
    """Vue Code du téléphone : comme la page Code de la fenêtre, une réponse
    terminée porte les fichiers qu'elle cite ou nomme (« links »), à sa fin et à
    chaque lecture de la conversation, et le Relay en montre l'aperçu ; ses
    pièces jointes ont leurs chemins sur le PC. Avant, la vue n'avait aucun
    aperçu : pièces jointes en texte, fichiers cités sans lien."""
    from relay.relay_server import RelayServer  # pylint: disable=import-outside-toplevel

    workspace = tmp_path / "ws"
    (workspace / "src" / "lib").mkdir(parents=True)
    for relative in ("README.md", "src/app.ts"):
        (workspace / relative).write_text("x", encoding="utf-8")
    notes = tmp_path / "notes.txt"
    notes.write_text("Notes", encoding="utf-8")
    other = tmp_path / "autre.txt"
    other.write_text("x", encoding="utf-8")
    app_ts = str(workspace / "src" / "app.ts")

    async def cite(run):
        text = "J'ai lu src/app.ts et notes.txt ; voir README.md et le dossier src/lib."
        run["on_chunk"](text, 0)
        return text

    FakeExecutor.script = cite
    server = RelayServer(config={}, code_hub=hub)
    hub.connect_vscode(loop, Surface().put,
                       f"Workspace folders:\n- ws ({workspace})\nPlatform: win32")
    phone = Surface()
    hub.subscribe(lambda event: phone.put(server.code_mobile_view(event)), snapshot=True)
    assert not server.preview_allowed(app_ts)

    hub.send("Regarde", "mobile", files=[(str(notes), "notes.txt")])
    wait_until(lambda: phone.of("code_done"))
    assert phone.of("code_user")[0]["files"] == [{"name": "notes.txt", "path": str(notes)}]
    expected = {"src/app.ts": app_ts, "notes.txt": str(notes),
                "README.md": str(workspace / "README.md"), "src/lib": str(workspace / "src" / "lib")}
    links = phone.of("code_done")[0]["links"]
    assert {link["text"]: link["path"] for link in links} == expected
    assert [link["text"] for link in links if link["dir"]] == ["src/lib"]
    # Le Relay montre ces fichiers au téléphone : ni un dossier, ni un autre fichier
    for text in ("src/app.ts", "notes.txt", "README.md"):
        assert server.preview_allowed(expected[text])
    assert not server.preview_allowed(expected["src/lib"])
    assert not server.preview_allowed(str(other))
    assert server.preview_file({"path": app_ts})["ok"] is True

    # Vue rechargée : mêmes liens, sans les dossiers du workspace gardés avec la réponse
    reloaded = Surface()
    hub.subscribe(lambda event: reloaded.put(server.code_mobile_view(event)), snapshot=True)
    reply = reloaded.of("code_snapshot")[0]["messages"][1]
    assert {link["text"] for link in reply["links"]} == set(expected)
    assert "roots" not in reply
    # Relay redémarré : il apprend ces fichiers à la lecture de la conversation
    fresh = RelayServer(config={}, code_hub=hub)
    assert not fresh.preview_allowed(app_ts)
    hub.push_snapshot(fresh.code_mobile_view)
    assert fresh.preview_allowed(app_ts)

    # Réponse en erreur : aucun lien
    async def fail(_run):
        raise RuntimeError("Ollama absent")

    FakeExecutor.script = fail
    hub.send("Encore", "mobile")
    wait_until(lambda: len(phone.of("code_done")) == 2)
    failed = phone.of("code_done")[1]
    assert failed["status"] == "error" and "links" not in failed


# ── Mémoire de My_AI dans la conversation Code ───────────────────────────────


def _memory_hub(hub, tmp_path):
    """Le hub avec la mémoire de l'appli : base de faits temporaire, documents absents."""
    kb = KnowledgeBaseManager(db_path=str(tmp_path / "facts.db"))
    memory = CodeMemory(kb)
    hub.set_llm_resolver(lambda: {**LLM, "memory": memory})
    return kb


async def answer_briefly(run):
    run["on_chunk"]("C'est noté.", 0)
    return "C'est noté."


def test_remember_in_the_code_conversation_saves_for_the_open_folder(hub, loop, tmp_path):
    """« Retiens que… » tapé dans la conversation Code n'était enregistré nulle part."""
    kb = _memory_hub(hub, tmp_path)
    FakeExecutor.script = answer_briefly
    _link, vscode = connect_vscode(hub, loop)
    phone = subscribe_phone(hub)
    seen = []
    FakeExecutor.script = lambda run: (seen.append(run["user_message"]), answer_briefly(run))[1]

    message_id = hub.send("Retiens que j'indente avec des tabulations", "desktop")
    wait_until(lambda: phone.of("code_done"))

    fact = kb.get_all_facts()[0]
    assert (fact["value"], fact["source"], fact["scope"], fact["project"]) == (
        "j'indente avec des tabulations", "code", "project", "C:\dev\My_AI")
    # Une carte au début de la réponse, sur les trois surfaces (VS Code ne l'a pas exécutée)
    card = phone.of("code_tool")[0]
    assert (card["message_id"], card["name"], card["status"], card["host"]) == (
        message_id, "remember_fact", "completed", True)
    assert card["input"] == {"fact": "j'indente avec des tabulations", "scope": "project",
                             "project": "My_AI"}
    assert card["output"] == tr("code.memory.savedProject", project="My_AI")
    assert vscode.of("code_tool")[0]["call_id"] == card["call_id"]
    parts = hub.snapshot()["messages"][1]["parts"]
    assert [p["kind"] for p in parts] == ["tool", "text"]
    # Le modèle le sait : la note suit son message
    assert seen[0].startswith("Retiens que j'indente avec des tabulations\n\n[Mémoire] ")
    assert "pour le projet « My_AI »" in seen[0]


async def search_the_memory(run):
    call = {"call_id": "m1", "name": "search_memory", "input": {"query": "port"}}
    run["on_tool_call_announced"](call)
    result = await run["tool_executor"].call(call_id="m1", name="search_memory",
                                             input_data=call["input"])
    run["on_tool_result"]("m1", result)
    run["on_chunk"](result["content"], 1)
    return result["content"]


def test_search_memory_runs_on_the_pc(hub, loop, tmp_path):
    kb = _memory_hub(hub, tmp_path)
    kb.add_fact("general", key="Le port de l'api est 8000", value="Le port de l'api est 8000",
                scope="project", project="C:\dev\My_AI")
    kb.add_fact("general", key="Le port du web est 5173", value="Le port du web est 5173",
                scope="project", project="C:\dev\web")
    FakeExecutor.script = search_the_memory
    _link, vscode = connect_vscode(hub, loop)
    phone = subscribe_phone(hub)

    hub.send("Quel port j'ai mis en mémoire ?", "mobile")
    wait_until(lambda: phone.of("code_done"))

    # Jamais envoyé à l'extension, mais montré partout
    assert not vscode.of("tool_use")
    assert [t["status"] for t in phone.of("code_tool")] == ["requested", "running", "completed"]
    assert [t["status"] for t in vscode.of("code_tool")] == ["requested", "running", "completed"]
    output = phone.of("code_tool")[-1]["output"]
    assert "8000" in output and "5173" not in output  # pas les faits d'un autre projet
    assert phone.of("code_done")[0]["status"] == "done"


def test_the_system_prompt_lists_the_code_facts_and_stays_put(hub, loop, tmp_path):
    """Un « retiens que… » ne refait pas le prompt système (Ollama relirait toute la
    conversation) ; un fait modifié dans la fenêtre Mémoire, si."""
    kb = _memory_hub(hub, tmp_path)
    tabs = kb.add_fact("general", key="J'indente avec des tabulations",
                       value="J'indente avec des tabulations", scope="code")
    kb.add_fact("general", key="Mon chat s'appelle Félix", value="Mon chat s'appelle Félix")
    _link, vscode = connect_vscode(hub, loop)

    def ask(text, count):
        hub.send(text, "vscode")
        wait_until(lambda: len(vscode.of("response")) == count)
        return hub._llm_history[0]["content"]  # pylint: disable=protected-access

    first = ask("Salut", 1)
    assert "# Mémoire" in first and "- L'utilisateur indente avec des tabulations" in first
    assert "Félix" not in first
    assert "### search_memory" in first
    assert ask("Retiens que j'écris mes commits en français", 2) == first
    assert ask("Et maintenant ?", 3) == first
    # Après un redémarrage aussi
    store = tmp_path / "code_conversation.json"
    wait_until(lambda: json.loads(store.read_text(encoding="utf-8")).get("memory"))
    restarted = CodeHub(store=store)
    assert restarted._memory_view == hub._memory_view  # pylint: disable=protected-access

    kb.update_fact(tabs, "J'indente avec quatre espaces")
    rebuilt = ask("Encore ?", 4)
    assert rebuilt != first
    assert "quatre espaces" in rebuilt and "indente avec des tabulations\n" not in rebuilt
    assert "- L'utilisateur écrit ses commits en français" in rebuilt


def test_facts_remembered_long_ago_come_back_when_the_start_goes(hub, loop, tmp_path):
    """Au-delà du budget, les premiers échanges partent, notes [Mémoire] comprises (Ollama
    relit alors tout de toute façon) : les faits retenus rejoignent le prompt système."""
    kb = KnowledgeBaseManager(db_path=str(tmp_path / "facts.db"))
    memory = CodeMemory(kb)
    hub.set_llm_resolver(lambda: {**LLM, "num_ctx": 8192, "memory": memory})

    async def long_reply(run):
        run["history"].append({"role": "user", "content": run["user_message"]})
        run["history"].append({"role": "assistant", "content": "x" * 9000})
        run["on_chunk"]("ok", 0)
        return "ok"

    FakeExecutor.script = long_reply
    _link, vscode = connect_vscode(hub, loop)

    def ask(text, count):
        hub.send(text, "vscode")
        wait_until(lambda: len(vscode.of("response")) == count)
        return hub._llm_history[0]["content"]  # pylint: disable=protected-access

    first = ask("Salut", 1)
    assert ask("Retiens que j'indente avec des tabulations", 2) == first
    assert "tabulations" not in first
    rebuilt = ask("Et ensuite ?", 3)
    assert "- L'utilisateur indente avec des tabulations" in rebuilt
    assert hub._llm_history[1]["content"].startswith("Retiens que")  # pylint: disable=protected-access


def test_without_memory_the_prompt_is_the_same_as_before(hub, loop):
    _link, vscode = connect_vscode(hub, loop)
    hub.send("Salut", "vscode")
    wait_until(lambda: vscode.of("response"))
    prompt = hub._llm_history[0]["content"]  # pylint: disable=protected-access
    assert "# Mémoire" not in prompt and "search_memory" not in prompt
    assert prompt == build_system_prompt(
        "Workspace folders:\n- My_AI (C:\dev\My_AI)\nPlatform: win32", language="fr")
    assert hub._memory_view is None  # pylint: disable=protected-access


def test_vscode_sees_only_the_tools_run_on_the_pc():
    tool = {"type": "tool", "message_id": "code_1", "call_id": "c1", "name": "read_file",
            "input": {}, "status": "running"}
    assert vscode_view(tool, "link") is None
    shown = vscode_view({**tool, "name": "search_memory", "host": True}, "link")
    assert shown["type"] == "code_tool" and shown["name"] == "search_memory"
    # La fenêtre desktop reçoit le même champ (événement « code.tool »)
    payload = {key: value for key, value in tool.items() if key != "type"} | {"host": True}
    validate_event({"type": "code.tool", "conversation_id": None, "message_id": "code_1",
                    "seq": 1, "payload": payload})
