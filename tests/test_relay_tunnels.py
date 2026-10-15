"""
Vérification des tunnels du Relay depuis ce PC (relay_server._watch_tunnels).

Une adresse de tunnel annoncée peut ne mener nulle part : le 2026-10-15,
localhost.run répondait « 502 no tunnel » dès son annonce, et le premier QR
code (localhost.run seul) menait le téléphone à un échec. Un tunnel n'entre
plus dans la page de routage qu'une fois joignable (GET /api/health, le test
de la page de routage). Un tunnel neuf reste « à vérifier » 30 s (cloudflared
met une dizaine de secondes à répondre), puis passe muet ; si aucun n'a
jamais répondu au PC, ils entrent tous dans la page de routage au bout de 30 s.
"""

import base64
import http.server
import json
import os
import socket
import sys
import tempfile
import threading
import time
from pathlib import Path
from types import SimpleNamespace

import pytest

from relay import relay_server
from relay.relay_server import RelayServer

# La vérification est interne au Relay : les tests passent par ses méthodes privées
# pylint: disable=protected-access

CF = "https://essai.trycloudflare.com"
LHR = "https://essai.lhr.life"


@pytest.fixture(name="server")
def server_fixture():
    """Relay construit (sans démarrer uvicorn ni de vrai tunnel, sans réseau)."""
    server = RelayServer(config={"tunnel_providers": ["cloudflared", "localhost.run"]})
    server._tunnel_probe = lambda url: False
    yield server
    server._stop_tunnel()


def routed(server):
    """Adresses de tunnels de la page de routage (fragment du QR code), None sans QR code."""
    url = server.relay_url
    if url is None:
        return None
    data = url.split("#d=")[1]
    payload = json.loads(base64.urlsafe_b64decode(data + "=" * (-len(data) % 4)))
    return payload["urls"]


def run_checks(server, now, results):
    """Une passe de vérification à `now`, sans fil ni réseau : {fournisseur: joignable}."""
    due = dict(server._due_tunnel_checks(now))
    assert set(due) == set(results)
    for provider, ok in results.items():
        server._record_tunnel_check(provider, due[provider], ok, now)


def test_tunnel_enters_qr_code_only_once_reachable(server):
    server._set_tunnel_url("localhost.run", LHR)
    assert server.tunnel_states == {"localhost.run": "checking"}
    assert server.relay_url is None  # pas de QR code avant la vérification

    # Pas de réponse : toujours à vérifier (un tunnel neuf peut tarder à répondre)
    since = server._tunnel_health["localhost.run"]["since"]
    run_checks(server, since, {"localhost.run": False})
    assert server.tunnel_states == {"localhost.run": "checking"}
    assert server.relay_url is None

    server._set_tunnel_url("cloudflared", CF)
    run_checks(server, since + 1, {"cloudflared": True})
    assert server.tunnel_states == {"localhost.run": "checking", "cloudflared": "ok"}
    assert routed(server) == [CF]

    # 30 s sans réponse : muet
    run_checks(server, since + relay_server._TUNNEL_VERIFY_GRACE, {"localhost.run": False})
    assert server.tunnel_states == {"localhost.run": "dead", "cloudflared": "ok"}
    assert routed(server) == [CF]
    # Les tunnels annoncés restent listés (Tk, /api/tunnels), vérifiés ou non
    assert server.tunnel_urls == {"localhost.run": LHR, "cloudflared": CF}


def test_checks_are_close_after_the_announce_then_spaced(server):
    server._set_tunnel_url("localhost.run", LHR)
    since = server._tunnel_health["localhost.run"]["since"]

    run_checks(server, since, {"localhost.run": False})
    assert server._due_tunnel_checks(since + 2.9) == []
    run_checks(server, since + 3.0, {"localhost.run": False})

    # Muet depuis plus d'une minute : un essai toutes les 30 s
    run_checks(server, since + 61, {"localhost.run": False})
    assert server.tunnel_states == {"localhost.run": "dead"}
    assert server._tunnel_health["localhost.run"]["next"] == pytest.approx(since + 91)

    # Joignable : contrôlé toutes les 30 s
    run_checks(server, since + 91, {"localhost.run": True})
    assert server._tunnel_health["localhost.run"]["next"] == pytest.approx(since + 121)
    assert routed(server) == [LHR]


def test_reachable_tunnel_leaves_after_two_failures_without_fallback(server):
    server._set_tunnel_url("cloudflared", CF)
    server._set_tunnel_url("localhost.run", LHR)
    now = time.monotonic()
    run_checks(server, now, {"cloudflared": True, "localhost.run": False})
    assert routed(server) == [CF]

    # Une coupure passagère ne change pas le QR code ; nouvel essai dans 3 s
    run_checks(server, now + 30, {"cloudflared": False, "localhost.run": False})
    assert server.tunnel_states == {"cloudflared": "ok", "localhost.run": "dead"}
    assert server._tunnel_health["cloudflared"]["next"] == pytest.approx(now + 33)

    run_checks(server, now + 33, {"cloudflared": False, "localhost.run": False})
    assert server.tunnel_states == {"cloudflared": "dead", "localhost.run": "dead"}
    # Un tunnel a déjà répondu à ce PC : les muets ne reviennent pas dans le QR code
    server._tunnel_first_seen -= 60
    assert server.relay_url is None


def test_all_tunnels_return_when_none_ever_answered_this_pc(server):
    server._set_tunnel_url("localhost.run", LHR)
    since = server._tunnel_health["localhost.run"]["since"]
    run_checks(server, since, {"localhost.run": False})
    run_checks(server, since + relay_server._TUNNEL_VERIFY_GRACE, {"localhost.run": False})
    assert server.tunnel_states == {"localhost.run": "dead"}
    assert server.relay_url is None  # le délai court depuis la première annonce

    # 30 s sans réponse : le PC est peut-être sur un réseau filtré, pas le téléphone
    server._tunnel_first_seen -= relay_server._TUNNEL_VERIFY_GRACE
    assert routed(server) == [LHR]


def test_ended_tunnel_process_is_dead_without_check(server):
    # Processus de tunnel terminé (code de sortie 255, comme ssh refusé)
    server._tunnel_processes["localhost.run"] = SimpleNamespace(poll=lambda: 255)
    server._set_tunnel_url("localhost.run", LHR)
    assert server._due_tunnel_checks(time.monotonic()) == []
    assert server.tunnel_states == {"localhost.run": "dead"}
    assert server._due_tunnel_checks(time.monotonic() + 3600) == []


def test_result_for_a_stopped_or_replaced_tunnel_is_ignored(server):
    server._set_tunnel_url("localhost.run", LHR)
    (_, url), = server._due_tunnel_checks(time.monotonic())

    # Adresse remplacée pendant le test : le résultat de l'ancienne ne compte pas
    server._set_tunnel_url("localhost.run", "https://autre.lhr.life")
    server._record_tunnel_check("localhost.run", url, True, time.monotonic())
    assert server.tunnel_states == {"localhost.run": "checking"}

    # Tunnels arrêtés pendant le test
    server._stop_tunnel()
    server._record_tunnel_check("localhost.run", "https://autre.lhr.life", True, time.monotonic())
    assert server.tunnel_states == {} and server.relay_url is None


def test_stop_resets_the_verification(server):
    server._start_tunnel_watch()
    stop = server._tunnel_watch_stop
    server._set_tunnel_url("cloudflared", CF)
    run_checks(server, time.monotonic(), {"cloudflared": True})

    server._stop_tunnel()
    assert stop.is_set() and server._tunnel_watch_stop is None
    assert server._tunnel_health == {} and server._tunnel_first_seen is None
    assert server._tunnel_ever_ok is False


def test_watch_thread_checks_each_announced_tunnel(server):
    checked = []

    def probe(url):
        checked.append(url)
        return url == CF

    server._tunnel_probe = probe
    server._start_tunnel_watch()
    server._set_tunnel_url("cloudflared", CF)
    server._set_tunnel_url("localhost.run", LHR)

    deadline = time.monotonic() + 5
    while time.monotonic() < deadline and not (
            set(checked) == {CF, LHR} and server.tunnel_states.get("cloudflared") == "ok"):
        time.sleep(0.05)
    # localhost.run, sans réponse depuis moins de 30 s : toujours à vérifier
    assert server.tunnel_states == {"cloudflared": "ok", "localhost.run": "checking"}
    assert set(checked) == {CF, LHR}
    assert routed(server) == [CF]

    server._stop_tunnel()
    deadline = time.monotonic() + 3
    while time.monotonic() < deadline and any(
            thread.name == "tunnel-watch" for thread in threading.enumerate()):
        time.sleep(0.05)
    assert not any(thread.name == "tunnel-watch" for thread in threading.enumerate())


def test_ssh_tunnels_write_no_nul_file(server, monkeypatch):
    # Sous Windows, OpenSSH écrivait « UserKnownHostsFile=nul » dans un vrai fichier « nul »,
    # à la racine du dépôt quand l'appli y est lancée
    commands = {}
    monkeypatch.setattr(relay_server.shutil, "which", lambda name: name)
    monkeypatch.setattr(server, "_spawn_tunnel",
                        lambda provider, cmd, **kwargs: commands.__setitem__(provider, cmd))
    known = Path(tempfile.gettempdir()) / "my_ai_relay_serveo_known_hosts"
    if sys.platform == "win32":
        known.write_text("serveo.net ssh-ed25519 ancienne-clé\n", encoding="utf-8")

    server._start_serveo()
    server._start_localhost_run()

    assert set(commands) == {"serveo", "localhost.run"}
    for provider, cmd in commands.items():
        target = next(arg for arg in cmd if arg.startswith("UserKnownHostsFile=")).split("=", 1)[1]
        if sys.platform == "win32":
            assert Path(target).parent == Path(tempfile.gettempdir()) and provider in target
        else:
            assert target == os.devnull
    # Vidé à chaque démarrage : aucune clé gardée d'une fois à l'autre, comme avec /dev/null
    assert not known.exists()


class _Health(http.server.BaseHTTPRequestHandler):
    """Réponses possibles d'une adresse de tunnel."""

    ANSWERS = {
        "/ok/api/health": (200, b'{"status": "ok", "relay": "My_AI Relay"}'),
        "/html/api/health": (200, b"<html>no tunnel</html>"),
        "/liste/api/health": (200, b"[1, 2]"),
        "/autre/api/health": (200, b'{"status": "starting"}'),
        "/502/api/health": (502, b"no tunnel"),
    }

    def do_GET(self):  # pylint: disable=invalid-name
        """Réponse fixée par le chemin."""
        status, body = self.ANSWERS.get(self.path, (404, b""))
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):  # pylint: disable=arguments-differ
        """Silencieux."""


def test_probe_is_the_router_page_test(monkeypatch):
    for name in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy"):
        monkeypatch.delenv(name, raising=False)
    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), _Health)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{httpd.server_address[1]}"
    try:
        probe = RelayServer._probe_tunnel_url
        assert probe(f"{base}/ok") is True
        for path in ("/html", "/liste", "/autre", "/502", "/absent"):
            assert probe(f"{base}{path}") is False, path
    finally:
        httpd.shutdown()
        httpd.server_close()

    # Port fermé : refus de connexion, sans exception
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        closed = sock.getsockname()[1]
    assert RelayServer._probe_tunnel_url(f"http://127.0.0.1:{closed}") is False
