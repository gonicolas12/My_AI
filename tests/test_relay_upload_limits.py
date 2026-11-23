"""
Limites des corps de requête du Relay (FastAPI 0.165 : max_body_size, form_limits).

Le tunnel public mène au Relay sans jeton, et FastAPI lit le formulaire de
POST /api/upload avant d'appeler la fonction, donc avant toute vérification
(GHSA-f56c-v883-vx8r touchait justement cette extraction). Le corps est
désormais borné avant d'être lu : 25 Mo de fichier, chiffré dans son
enveloppe multipart, un seul fichier et aucun autre champ ; les autres
requêtes (POST /api/unlock) 64 Kio. Le téléphone garde le message
« Fichier trop volumineux » qu'il affichait déjà.
"""

# pylint: disable=protected-access

import pytest

from core.i18n import tr
from relay import relay_server
from relay.relay_server import RelayServer

testclient = pytest.importorskip("fastapi.testclient")

MB = 1024 * 1024


@pytest.fixture(name="server")
def server_fixture(tmp_path):
    """Relay construit, sans uvicorn ni tunnel ; envois dans un dossier jetable."""
    server = RelayServer(config={})
    server._upload_dir = tmp_path / "envois"
    return server


@pytest.fixture(name="client")
def client_fixture(server):
    return testclient.TestClient(server._app)


@pytest.fixture(name="session")
def session_fixture(server, client):
    """Session ouverte par le code d'accès, comme le téléphone."""
    response = client.post(f"/api/unlock?token={server.auth_token}",
                           json=server.encrypt_json({"code": server.access_code}))
    return server.decrypt_json(response.json())["session"]


def wire(server, name, content):
    """Corps chiffré d'un envoi, comme relay/static/app.js (uploadEncryptedFile)."""
    raw = name.encode("utf-8")
    return server.encrypt_bytes(b"MYAI" + len(raw).to_bytes(2, "big") + raw + content)


def upload_url(server, session):
    return f"/api/upload?token={server.auth_token}&session={session}"


def too_big_message():
    return tr("relay.fileTooBig", mb=relay_server._MAX_UPLOAD_SIZE // MB)


def test_a_25_mb_file_with_the_longest_name_still_goes_through(server, client, session):
    # 256 octets en UTF-8, le plus long nom accepté (88 caractères : le nom gardé
    # en compte 120 au plus, extension comprise)
    name = "文" * 84 + ".pdf"
    assert len(name.encode("utf-8")) == 256
    body = wire(server, name, b"%" * relay_server._MAX_UPLOAD_SIZE)
    response = client.post(upload_url(server, session),
                           files={"file": ("enc.bin", body, "application/octet-stream")})
    assert response.status_code == 200, response.text
    assert server.decrypt_json(response.json())["size"] == relay_server._MAX_UPLOAD_SIZE
    # Chiffré et enveloppe multipart compris, le corps reste sous la limite
    sent = len(response.request.content)
    assert sent < relay_server._UPLOAD_BODY_MAX
    assert relay_server._UPLOAD_BODY_MAX - sent > 4096


@pytest.mark.parametrize("chunked", [False, True])
def test_a_body_over_the_limit_is_refused_before_the_function(server, client, monkeypatch,
                                                              chunked):
    called = []
    monkeypatch.setattr(server, "decrypt_bytes", lambda blob: called.append(len(blob)))
    boundary = "----essai"
    head = (f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; "
            f"filename=\"enc.bin\"\r\nContent-Type: application/octet-stream\r\n\r\n").encode()
    body = head + b"\0" * relay_server._UPLOAD_BODY_MAX + f"\r\n--{boundary}--\r\n".encode()
    headers = {"Content-Type": f"multipart/form-data; boundary={boundary}"}
    # Sans jeton ni session : la limite passe avant toute vérification
    if chunked:  # sans Content-Length : compté au fil de la lecture
        response = client.post("/api/upload", content=iter([body[:MB], body[MB:]]),
                               headers=headers)
    else:
        response = client.post("/api/upload", content=body, headers=headers)
    assert response.status_code == 413
    # Le message que le téléphone affichait déjà (refus de la fonction d'envoi)
    assert response.json() == {"detail": too_big_message()}
    assert called == []


def test_the_function_still_refuses_a_too_big_file(server, client, session):
    # Juste sous la limite de FastAPI, mais un clair de plus de 25 Mo : refus de la fonction
    body = wire(server, "photo.png", b"\x89" * (relay_server._MAX_UPLOAD_SIZE + 1))
    response = client.post(upload_url(server, session),
                           files={"file": ("enc.bin", body, "application/octet-stream")})
    assert response.status_code == 413
    assert response.json() == {"detail": too_big_message()}


def test_one_file_and_nothing_else(server, client, session):
    first = wire(server, "a.txt", b"un")
    second = wire(server, "b.txt", b"deux")
    two_files = client.post(upload_url(server, session), files=[
        ("file", ("enc.bin", first, "application/octet-stream")),
        ("file", ("enc.bin", second, "application/octet-stream")),
    ])
    assert two_files.status_code == 400
    extra_field = client.post(upload_url(server, session), data={"nom": "a.txt"},
                              files={"file": ("enc.bin", first, "application/octet-stream")})
    assert extra_field.status_code == 400
    assert not server.upload_dir.exists() or not any(server.upload_dir.iterdir())
    # Le même envoi, seul, passe
    alone = client.post(upload_url(server, session),
                        files={"file": ("enc.bin", first, "application/octet-stream")})
    assert alone.status_code == 200


def test_other_requests_are_limited_to_64_kib(server, client):
    # POST /api/unlock : un code chiffré de quelques centaines d'octets
    padding = "x" * relay_server._BODY_MAX
    response = client.post(f"/api/unlock?token={server.auth_token}",
                           json={"e": padding})
    assert response.status_code == 413
    assert too_big_message() not in response.text  # message propre aux envois
    # Un vrai code passe toujours
    ok = client.post(f"/api/unlock?token={server.auth_token}",
                     json=server.encrypt_json({"code": server.access_code}))
    assert ok.status_code == 200 and server.decrypt_json(ok.json())["ok"] is True


def test_an_older_fastapi_still_starts_the_relay(caplog):
    # requirements.txt demande la 0.165, installée au lancement ; hors ligne, pip
    # peut échouer : le Relay démarre alors sans ces limites, avec un avertissement
    def old_post(path, response_model=None):  # pylint: disable=unused-argument
        return None

    options = relay_server._fastapi_options(old_post, max_body_size=1, form_limits={},
                                            response_model=None)
    assert options == {"response_model": None}
    assert "max_body_size" in caplog.text and "form_limits" in caplog.text


def test_this_fastapi_knows_the_limits():
    # Sinon les tests ci-dessus passeraient sans limite (version trop ancienne)
    fastapi = pytest.importorskip("fastapi")
    assert relay_server._fastapi_options(fastapi.FastAPI.post, max_body_size=1,
                                         form_limits={}) == {"max_body_size": 1,
                                                             "form_limits": {}}
