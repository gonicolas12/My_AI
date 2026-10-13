"""
Tests du serveur local de l'interface web (interfaces/desktop/server.py)

D'abord l'accès : jeton du lancement exigé, Host et Origin vérifiés, car
n'importe quel site ouvert dans un navigateur peut tenter de joindre
127.0.0.1. Puis le REST et le WebSocket, branchés sur le service de chat avec
le moteur simulé de test_chat_service.
"""

import time
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from core.chat_service import ChatService
from interfaces.desktop import server as desktop_server
from interfaces.desktop.events import EventBus, validate_event
from interfaces.desktop.server import DesktopServer
from test_chat_service import FakeEngine, FakeFileProcessor, wait_for  # pylint: disable=import-error

TOKEN = "jeton-de-test"
PORT = 8123
BASE = f"http://127.0.0.1:{PORT}"
AUTH = {"Authorization": f"Bearer {TOKEN}"}


def ws_connect(client, url, headers=None):
    """WebSocket du client de test, avec l'hôte du serveur (« testserver » sinon)."""
    return client.websocket_connect(url, headers={"Host": f"127.0.0.1:{PORT}", **(headers or {})})


class FakeApp:
    """DesktopApp réduite à ce que le serveur utilise."""

    def __init__(self, chat, bus, dev=False):
        self.token = TOKEN
        self.dev = dev
        self.bus = bus
        self.chat = chat
        self.engine = object()
        self.shutdowns = 0
        self.relay_calls = []
        self.ui = {"sidebar_open": False}

    @staticmethod
    def status():
        return {"state": "ready", "step": "ready", "label": "Prêt", "detail": "",
                "error": None, "ollama": True, "placement": "modèle sur le GPU"}

    @staticmethod
    def relay_status():
        return {"running": False, "port": None, "clients": 0, "tunnels": {},
                "url": None, "local_url": None}

    def start_relay(self, tunnel):
        self.relay_calls.append(("start", tunnel))
        return self.relay_status()

    def stop_relay(self):
        self.relay_calls.append(("stop",))
        return self.relay_status()

    def shutdown(self):
        self.shutdowns += 1

    def ui_state(self):
        return dict(self.ui)

    def set_ui_state(self, values):
        self.ui.update(values)
        return dict(self.ui)


@pytest.fixture(name="desktop")
def desktop_fixture(tmp_path):
    """Serveur desktop branché sur un vrai service de chat et un moteur simulé."""
    engine = FakeEngine(tmp_path / "workspaces")
    bus = EventBus()
    events = []
    bus.subscribe(events.append)
    chat = ChatService(engine, bus.publish, file_processor=FakeFileProcessor(),
                       ui_connected=lambda: True)
    chat.start()
    app = FakeApp(chat, bus)
    server = DesktopServer(app)
    server.port = PORT
    client = TestClient(server.fastapi, base_url=BASE)
    yield SimpleNamespace(app=app, server=server, client=client, chat=chat,
                          engine=engine, bus=bus, events=events, tmp_path=tmp_path)
    chat.close()


# ── Accès ───────────────────────────────────────────────────────────────────


def test_api_requires_the_launch_token(desktop):
    assert desktop.client.get("/api/status").status_code == 401
    assert desktop.client.get("/api/status",
                              headers={"Authorization": "Bearer autre"}).status_code == 401
    assert desktop.client.get("/api/status", headers=AUTH).status_code == 200
    assert desktop.client.get(f"/api/status?token={TOKEN}").status_code == 200


def test_foreign_host_is_refused_even_with_the_token(desktop):
    """DNS rebinding : un site qui ferait pointer son domaine vers 127.0.0.1."""
    response = desktop.client.get("/api/status",
                                  headers={**AUTH, "Host": f"attaquant.example:{PORT}"})
    assert response.status_code == 403
    assert desktop.client.get("/", headers={"Host": "attaquant.example"}).status_code == 403


def test_foreign_origin_is_refused(desktop):
    refused = desktop.client.get("/api/status",
                                 headers={**AUTH, "Origin": "https://site.example"})
    assert refused.status_code == 403
    allowed = desktop.client.get("/api/status", headers={**AUTH, "Origin": BASE})
    assert allowed.status_code == 200


def test_vite_origin_is_accepted_only_in_dev_mode(desktop):
    headers = {**AUTH, "Origin": "http://localhost:5173"}
    assert desktop.client.get("/api/status", headers=headers).status_code == 403
    desktop.app.dev = True
    assert desktop.client.get("/api/status", headers=headers).status_code == 200


def test_websocket_requires_token_and_a_known_origin(desktop):
    for url, headers in (
        ("/ws", {}),
        ("/ws?token=autre", {}),
        (f"/ws?token={TOKEN}", {"Origin": "https://site.example"}),
        (f"/ws?token={TOKEN}", {"Host": "attaquant.example"}),
    ):
        with pytest.raises(WebSocketDisconnect):
            with ws_connect(desktop.client, url, headers) as ws:
                ws.receive_json()
    with ws_connect(desktop.client, f"/ws?token={TOKEN}", {"Origin": BASE}) as ws:
        assert ws.receive_json() == {"type": "hello", "resumed": True}


# ── Chat ────────────────────────────────────────────────────────────────────


def test_chat_over_the_websocket_streams_its_events(desktop):
    with ws_connect(desktop.client, f"/ws?token={TOKEN}") as ws:
        assert ws.receive_json()["type"] == "hello"
        ws.send_json({"type": "chat.send", "id": "envoi-1", "text": "Bonjour"})
        received = []
        reply = None
        while True:
            message = ws.receive_json()
            if message["type"] == "reply":
                reply = message
                continue
            received.append(message)
            if message["type"] == "assistant.done":
                break
    assert reply["ref"] == "envoi-1" and reply["ok"] is True and reply["data"]["request_id"]
    for event in received:
        validate_event(event)
    types = [event["type"] for event in received]
    assert "message.user" in types and "assistant.token" in types
    tokens = "".join(e["payload"]["text"] for e in received if e["type"] == "assistant.token")
    assert tokens == "Réponse à « Bonjour »"

    snapshot = desktop.client.get("/api/conversation", headers=AUTH).json()
    assert [m["text"] for m in snapshot["messages"]] == ["Bonjour", "Réponse à « Bonjour »"]
    assert snapshot["seq"] >= received[-1]["seq"]


def test_invalid_message_gets_an_error_reply(desktop):
    with ws_connect(desktop.client, f"/ws?token={TOKEN}") as ws:
        ws.receive_json()
        ws.send_json({"type": "inconnu", "id": "x"})
        reply = ws.receive_json()
        assert reply["ok"] is False and "inconnu" in reply["error"]
        ws.send_json({"type": "chat.send", "id": "y", "text": "   "})
        reply = ws.receive_json()
        while reply["type"] != "reply":
            reply = ws.receive_json()
        assert reply == {"type": "reply", "ref": "y", "ok": False, "error": "Message vide."}


def test_reconnection_replays_missed_events(desktop):
    desktop.client.post("/api/conversation/send", json={"text": "Bonjour"}, headers=AUTH)
    wait_for(desktop.events, "assistant.done")
    first = desktop.events[0]["seq"]

    with ws_connect(desktop.client, f"/ws?token={TOKEN}&since={first}") as ws:
        assert ws.receive_json() == {"type": "hello", "resumed": True}
        replayed = ws.receive_json()
        assert replayed["seq"] == first + 1


def test_event_bus_reports_when_missed_events_are_gone():
    bus = EventBus(history=3)
    for _ in range(10):
        bus.publish("notification", {"level": "info", "message": "…"})
    received = []
    _unsubscribe, resumed = bus.subscribe(received.append, since=2)
    assert resumed is False and received == []
    _unsubscribe, resumed = bus.subscribe(received.append, since=8)
    assert resumed is True and [event["seq"] for event in received] == [9, 10]


def test_chat_errors_and_a_starting_engine_have_their_own_status(desktop):
    response = desktop.client.post("/api/conversation/send", json={"text": " "}, headers=AUTH)
    assert response.status_code == 409 and response.json()["detail"] == "Message vide."

    desktop.app.chat = None
    response = desktop.client.get("/api/conversation", headers=AUTH)
    assert response.status_code == 503 and response.json()["detail"] == "Le moteur démarre…"


def test_sessions_over_rest(desktop):
    desktop.client.post("/api/conversation/send", json={"text": "Question A"}, headers=AUTH)
    wait_for(desktop.events, "assistant.done")
    sessions = desktop.client.get("/api/sessions", headers=AUTH).json()["sessions"]
    assert sessions[0]["name"] == "Question A" and sessions[0]["current"] is True

    assert desktop.client.post("/api/conversation/new", headers=AUTH).json() == {"ok": True}
    assert desktop.client.get("/api/conversation", headers=AUTH).json()["messages"] == []

    session_id = sessions[0]["id"]
    assert desktop.client.post(f"/api/sessions/{session_id}/load", headers=AUTH).status_code == 200
    snapshot = desktop.client.get("/api/conversation", headers=AUTH).json()
    assert [m["text"] for m in snapshot["messages"]] == ["Question A", "Réponse à « Question A »"]
    assert desktop.client.get(f"/api/conversations/{session_id}", headers=AUTH).status_code == 200
    assert desktop.client.get("/api/conversations/autre", headers=AUTH).status_code == 404


def test_pasted_image_is_uploaded_as_an_attachment(desktop):
    from io import BytesIO  # pylint: disable=import-outside-toplevel
    from PIL import Image  # pylint: disable=import-outside-toplevel

    buffer = BytesIO()
    Image.new("RGB", (20, 10), (255, 0, 0)).save(buffer, format="PNG")
    response = desktop.client.post(
        "/api/attachments/upload", headers=AUTH,
        files={"file": ("presse-papier.png", buffer.getvalue(), "image/png")},
    )
    assert response.status_code == 200
    attachment = response.json()
    assert attachment["type"] == "Image" and attachment["status"] == "ready"
    assert attachment["name"].endswith("presse-papier.png")
    removed = desktop.client.delete(f"/api/attachments/{attachment['id']}", headers=AUTH)
    assert removed.json() == {"removed": True}


def test_relay_and_shutdown_routes(desktop):
    assert desktop.client.post("/api/relay/start", json={"tunnel": False},
                               headers=AUTH).json()["running"] is False
    desktop.client.post("/api/relay/stop", headers=AUTH)
    assert desktop.app.relay_calls == [("start", False), ("stop",)]

    assert desktop.client.post("/api/shutdown", headers=AUTH).json() == {"ok": True}
    deadline = time.time() + 2
    while not desktop.app.shutdowns and time.time() < deadline:
        time.sleep(0.01)
    assert desktop.app.shutdowns == 1


# ── Interface ───────────────────────────────────────────────────────────────


def test_page_has_a_strict_content_security_policy(desktop, tmp_path, monkeypatch):
    monkeypatch.setattr(desktop_server, "DIST_DIR", tmp_path / "absent")
    page = desktop.client.get("/")
    assert page.status_code == 200 and "My_AI" in page.text
    policy = page.headers["content-security-policy"]
    assert "default-src 'self'" in policy and "script-src 'self'" in policy
    assert f"connect-src 'self' ws://127.0.0.1:{PORT}" in policy


def test_built_interface_is_served_without_escaping_its_folder(desktop, tmp_path, monkeypatch):
    dist = tmp_path / "dist"
    (dist / "assets").mkdir(parents=True)
    (dist / "index.html").write_text("<!doctype html><title>My_AI</title>", encoding="utf-8")
    (dist / "assets" / "app.js").write_text("console.log('ok')", encoding="utf-8")
    (tmp_path / "secret.txt").write_text("secret", encoding="utf-8")
    monkeypatch.setattr(desktop_server, "DIST_DIR", dist)

    script = desktop.client.get("/assets/app.js")
    assert script.status_code == 200
    assert script.headers["content-type"].startswith("application/javascript")
    assert desktop.client.get("/").text.startswith("<!doctype html>")
    assert desktop.client.get("/assets/absent.js").status_code == 404
    assert desktop.client.get("/%2e%2e/secret.txt").status_code == 404


# ── État de l'appli et de l'interface ───────────────────────────────────────


def test_status_tells_the_window_where_to_resume(desktop):
    desktop.bus.publish("notification", {"level": "info", "message": "x"})
    data = desktop.client.get("/api/status", headers=AUTH).json()
    assert data["chat"] is True
    # Seq du dernier événement publié : la fenêtre applique ensuite les plus récents
    assert data["seq"] == desktop.bus.last_seq
    assert data["status"]["state"] == "ready"


def test_ui_state_is_read_and_saved(desktop):
    assert desktop.client.get("/api/ui", headers=AUTH).json() == {"sidebar_open": False}
    saved = desktop.client.put("/api/ui", headers=AUTH, json={"sidebar_open": True})
    assert saved.json() == {"sidebar_open": True}
    assert desktop.app.ui == {"sidebar_open": True}
    # Clé inconnue : refusée par le schéma
    assert desktop.client.put("/api/ui", headers=AUTH, json={"autre": 1}).status_code == 422
    # Sans jeton : refusé
    assert desktop.client.put("/api/ui", json={"sidebar_open": False}).status_code == 401
