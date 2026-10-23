"""
Code d'accès du Relay (relay_server.RelayServer.unlock).

Le lien du QR code (jeton et clé E2EE) suffisait pour tout faire : chat,
historique, agents, indexation de dossiers du PC. Or il peut fuiter sans que
l'écran soit vu (historique du navigateur synchronisé, presse-papiers,
appli de lecture de QR code). Le Relay tire donc un code de 6 chiffres à son
démarrage, affiché sous le QR code : sans lui, ni l'API ni le WebSocket ne
servent rien. Passé 5 codes erronés, plus aucun code n'est accepté avant un
redémarrage du Relay ; seul qui a le lien complet peut en essayer un.
"""

import json

import pytest
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from relay import relay_server
from relay.relay_server import RelayServer

testclient = pytest.importorskip("fastapi.testclient")
WebSocketDisconnect = pytest.importorskip("starlette.websockets").WebSocketDisconnect


@pytest.fixture(name="server")
def server_fixture():
    """Relay construit, sans uvicorn ni tunnel."""
    return RelayServer(config={})


@pytest.fixture(name="client")
def client_fixture(server):
    """Client HTTP et WebSocket de l'appli du Relay."""
    return testclient.TestClient(server._app)  # pylint: disable=protected-access


def unlock(client, server, code):
    """POST /api/unlock comme les clients : code chiffré, réponse chiffrée."""
    response = client.post(f"/api/unlock?token={server.auth_token}",
                           json=server.encrypt_json({"code": code}))
    assert response.status_code == 200
    return server.decrypt_json(response.json())


def wrong_code(server):
    """Un code de 6 chiffres qui n'est pas le bon."""
    return f"{(int(server.access_code) + 1) % 10 ** 6:06d}"


def test_access_code_keeps_its_leading_zeros(monkeypatch):
    monkeypatch.setattr(relay_server.secrets, "randbelow", lambda bound: 42)
    assert RelayServer(config={}).access_code == "000042"


def test_nothing_is_served_before_the_access_code(server, client):
    token = server.auth_token
    for path in ("/api/history", "/api/prompts", "/api/pending?message_id=m"):
        separator = "&" if "?" in path else "?"
        response = client.get(f"{path}{separator}token={token}")
        assert response.status_code == 403, path
        assert client.get(f"{path}{separator}token={token}&session=invente").status_code == 403
    upload = client.post(f"/api/upload?token={token}",
                         files={"file": ("enc.bin", b"x" * 64, "application/octet-stream")})
    assert upload.status_code == 403
    # WebSocket accepté puis fermé en 4003 : le client sait qu'il doit demander le code
    with client.websocket_connect(f"/ws?token={token}") as ws:
        with pytest.raises(WebSocketDisconnect) as closed:
            ws.receive_text()
    assert closed.value.code == 4003
    assert server.ws_clients == []


def test_right_code_opens_a_session(server, client):
    # Tapé comme affiché dans le panneau, avec l'espace
    code = server.access_code
    result = unlock(client, server, f"{code[:3]} {code[3:]}")
    assert result["ok"] is True
    session = result["session"]
    history = client.get(f"/api/history?token={server.auth_token}&session={session}")
    assert history.status_code == 200
    assert server.decrypt_json(history.json()) == {"history": []}
    with client.websocket_connect(f"/ws?token={server.auth_token}&session={session}") as ws:
        ws.send_text(json.dumps(server.encrypt_json({"type": "ping"})))
        assert server.decrypt_json(json.loads(ws.receive_text())) == {"type": "pong"}
    # Le jeton reste exigé : la session seule ne suffit pas
    assert client.get(f"/api/history?token=autre&session={session}").status_code == 401


def test_wrong_codes_lock_the_relay_until_it_restarts(server, client):
    opened = unlock(client, server, server.access_code)["session"]
    for remaining in (4, 3, 2, 1):
        assert unlock(client, server, wrong_code(server)) == {
            "ok": False, "error": "wrong", "remaining": remaining}
    assert unlock(client, server, wrong_code(server)) == {
        "ok": False, "error": "locked", "remaining": 0}
    assert server.access_locked and server.access_failures == 5
    # Le bon code est refusé lui aussi, sans compter de nouvel échec
    assert unlock(client, server, server.access_code)["error"] == "locked"
    assert server.access_failures == 5
    # La session ouverte avant le verrouillage reste valable
    history = client.get(f"/api/history?token={server.auth_token}&session={opened}")
    assert history.status_code == 200
    # Redémarré, le Relay tire un nouveau code et oublie les sessions
    restarted = RelayServer(config={})
    assert not restarted.access_locked and not restarted.verify_session(opened)


def test_tries_without_the_full_link_are_not_counted(server, client):
    code = server.access_code
    # Sans le jeton
    assert client.post("/api/unlock?token=autre",
                       json=server.encrypt_json({"code": code})).status_code == 401
    # Sans la clé : code en clair, ou chiffré par une autre clé
    assert client.post(f"/api/unlock?token={server.auth_token}",
                       json={"code": code}).status_code == 400
    other_key = AESGCM(AESGCM.generate_key(bit_length=256))
    nonce = b"\x00" * 12
    forged = nonce + other_key.encrypt(nonce, json.dumps({"code": code}).encode(), None)
    assert client.post(f"/api/unlock?token={server.auth_token}",
                       json={"e": server._b64u_encode(forged)}).status_code == 400  # pylint: disable=protected-access
    # Faute de frappe visible (5 chiffres) : signalée, pas comptée
    assert unlock(client, server, code[:5]) == {"ok": False, "error": "format", "remaining": 5}
    assert server.access_failures == 0


def test_without_the_link_there_is_nothing_to_type(server, client):
    # L'ancien mot de passe (relay.password, page de connexion, POST /auth) ne
    # pouvait plus ouvrir l'appli depuis le chiffrement E2EE : retiré. Sans le
    # jeton du lien, une page renvoie au QR code, sans champ à remplir.
    for path in ("/", "/?token=ancien"):
        page = client.get(path)
        assert page.status_code == 401
        assert "Scannez le QR code" in page.text and "<input" not in page.text
    assert client.post("/auth", json={"password": server.auth_token}).status_code == 404
    assert client.get(f"/?token={server.auth_token}").status_code == 200


def test_health_says_a_code_is_required_without_giving_it(server, client):
    health = client.get("/api/health")
    assert health.json()["access_code_required"] is True
    assert server.access_code not in health.text
