"""
Vérification des tunnels du Relay depuis ce PC (relay_server._watch_tunnels).

Une adresse de tunnel annoncée peut ne mener nulle part : le 2026-10-15,
localhost.run répondait « 502 no tunnel » dès son annonce, et le premier QR
code (localhost.run seul) menait le téléphone à un échec (cause trouvée le
2026-10-19 : le tunnel renvoyait vers « localhost », soit ::1 où le Relay
n'écoute pas, voir test_tunnels_forward_to_127_0_0_1). Un tunnel n'entre
plus dans la page de routage qu'une fois joignable (GET /api/health, le test
de la page de routage). Un tunnel neuf reste « à vérifier » 30 s, puis passe
muet ; si aucun n'a jamais répondu au PC, ils entrent tous dans la page de
routage au bout de 30 s.

Le nom d'un tunnel cloudflared n'existe que 1 à 12 s après son annonce. Le
2026-10-16, le PC le demandait aussitôt à son DNS : la réponse « ce nom
n'existe pas », gardée 60 s par la box et par Windows, a rendu le tunnel
injoignable depuis le PC 92 s. Le Relay ne demande plus ce nom au DNS du PC :
il prend l'adresse du tunnel aux serveurs faisant autorité (sans cache) et y
envoie le test, au nom du tunnel (TLS, en-tête Host).
"""

import base64
import http.server
import json
import os
import socket
import ssl
import struct
import sys
import tempfile
import threading
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509.oid import NameOID

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
    # Noms publiés, sans réseau : le test direct d'un tunnel cloudflared passe par la même
    # doublure que les autres (_tunnel_probe, que chaque test peut remplacer)
    server._tunnel_dns = lambda host: ["104.16.0.1"]
    server._tunnel_probe_at = lambda url, address: server._tunnel_probe(url)
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
    # Les tunnels annoncés restent listés (panneau Relay), vérifiés ou non
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


def test_cloudflared_name_never_goes_to_the_pc_dns(server):
    addresses = iter([[], [], ["104.16.0.1", "104.16.0.2"]])
    asked, direct, by_pc_dns = [], [], []
    server._tunnel_dns = lambda host: asked.append(host) or next(addresses)
    server._tunnel_probe_at = lambda url, address: direct.append((url, address)) or True
    server._tunnel_probe = lambda url: by_pc_dns.append(url) or True
    server._set_tunnel_url("cloudflared", CF)

    # Nom pas encore publié : pas de test
    server._check_tunnel("cloudflared", CF)
    server._check_tunnel("cloudflared", CF)
    assert not direct and server.tunnel_states == {"cloudflared": "checking"}
    assert server.relay_url is None

    # Publié : test envoyé à l'adresse donnée par les serveurs faisant autorité
    server._check_tunnel("cloudflared", CF)
    assert direct == [(CF, "104.16.0.1")] and routed(server) == [CF]
    assert asked == ["essai.trycloudflare.com"] * 3
    # Jamais par le DNS du PC : rien de faux dans les caches de la box ni de Windows
    assert not by_pc_dns


def test_silent_dns_authorities_fall_back_to_the_pc_dns(server):
    # Réseau qui filtre le DNS direct : test par le DNS du PC, le nom presque sûrement publié
    by_pc_dns = []
    server._tunnel_dns = lambda host: None
    server._tunnel_probe = lambda url: by_pc_dns.append(url) or True
    server._set_tunnel_url("cloudflared", CF)

    server._check_tunnel("cloudflared", CF)
    assert not by_pc_dns and server.tunnel_states == {"cloudflared": "checking"}

    server._tunnel_health["cloudflared"]["since"] -= relay_server._TUNNEL_DNS_FALLBACK
    server._check_tunnel("cloudflared", CF)
    assert by_pc_dns == [CF] and server.tunnel_states == {"cloudflared": "ok"}


def test_wildcard_tunnel_names_go_to_the_pc_dns_at_once(server):
    # lhr.life et serveo.net répondent pour tout nom : rien à demander aux serveurs faisant autorité
    serveo = "https://essai.serveo.net"
    asked, by_pc_dns = [], []
    server._tunnel_dns = asked.append
    server._tunnel_probe = lambda url: by_pc_dns.append(url) or False
    for provider, url in (("localhost.run", LHR), ("serveo", serveo)):
        server._set_tunnel_url(provider, url)
        server._check_tunnel(provider, url)
    assert not asked and by_pc_dns == [LHR, serveo]


class _FakeAuthority:  # pylint: disable=too-few-public-methods
    """Serveur DNS faisant autorité, en UDP local : réponse choisie par le premier label du nom."""

    QR, AA = 0x8000, 0x0400

    def __init__(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(("127.0.0.1", 0))
        self.address = self.sock.getsockname()
        self.flags_seen = []
        threading.Thread(target=self._serve, daemon=True).start()

    def _serve(self):
        while True:
            try:
                query, client = self.sock.recvfrom(512)
            except OSError:
                return  # fermé
            query_id, flags = struct.unpack(">2H", query[:4])
            self.flags_seen.append(flags)
            label = query[13:13 + query[12]].decode("ascii")

            def record(rtype, data):
                """Enregistrement de réponse : nom (renvoi vers la question), type, classe, TTL."""
                return b"\xc0\x0c" + struct.pack(">2HIH", rtype, 1, 300, len(data)) + data

            first, second = record(1, bytes([104, 16, 0, 1])), record(1, bytes([104, 16, 0, 2]))
            alias = record(5, b"\x05cible\x0bcfargotunnel\x03com\x00")  # CNAME seul
            answers = {
                "publie": (query_id, self.QR | self.AA, 1, first),
                "deux": (query_id, self.QR | self.AA, 2, first + second),
                "alias": (query_id, self.QR | self.AA, 1, alias),
                "tronque": (query_id, self.QR | self.AA, 1, first[:-2]),
                "absent": (query_id, self.QR | self.AA | 3, 0, b""),
                "relaye": (query_id, self.QR | 3, 0, b""),  # NXDOMAIN sans autorité
                "refus": (query_id, self.QR | 5, 0, b""),
                "vide": (query_id, self.QR | self.AA, 0, b""),
                "autre": (query_id ^ 1, self.QR | self.AA, 1, first),
            }
            if label not in answers:
                continue  # muet
            reply_id, reply_flags, count, body = answers[label]
            self.sock.sendto(struct.pack(">6H", reply_id, reply_flags, 1, count, 0, 0)
                             + query[12:] + body, client)

    def close(self):
        """Arrête le serveur."""
        self.sock.close()


def test_dns_question_goes_straight_to_the_authority():
    authority = _FakeAuthority()
    ask = RelayServer._ask_dns_authority
    try:
        assert ask("publie.trycloudflare.com", [authority.address]) == ["104.16.0.1"]
        assert ask("deux.trycloudflare.com", [authority.address]) == ["104.16.0.1", "104.16.0.2"]
        assert ask("absent.trycloudflare.com", [authority.address]) == []
        # Réponse sans adresse, illisible, sans autorité, refus, autre question, muet
        for name in ("alias", "tronque", "relaye", "refus", "vide", "autre", "muet"):
            assert ask(f"{name}.trycloudflare.com", [authority.address], timeout=0.3) is None, name
        # Sans récursion : aucun résolveur sur le chemin, donc aucun cache
        assert authority.flags_seen and not any(flags & 0x0100 for flags in authority.flags_seen)

        # Premier serveur fermé : le suivant tranche ; aucun serveur : on ne sait pas
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.bind(("127.0.0.1", 0))
            closed = sock.getsockname()
        assert ask("absent.trycloudflare.com", [closed, authority.address], timeout=0.3) == []
        assert ask("publie.trycloudflare.com", [], timeout=0.3) is None
    finally:
        authority.close()


def test_dns_authorities_of_the_zone_are_asked(monkeypatch):
    authority = _FakeAuthority()
    monkeypatch.setitem(relay_server._DNS_AUTHORITIES, "essai.test",
                        ("ns1.essai.test", "ns2.essai.test"))
    resolved = []

    def getaddrinfo(name, port, family, kind):
        resolved.append((name, port))
        if name == "ns1.essai.test":
            raise socket.gaierror("serveur introuvable")
        return [(family, kind, 17, "", authority.address)]

    monkeypatch.setattr(relay_server.socket, "getaddrinfo", getaddrinfo)
    try:
        assert RelayServer._dns_addresses("publie.essai.test") == ["104.16.0.1"]
        assert resolved == [("ns1.essai.test", 53), ("ns2.essai.test", 53)]
        # Zone sans serveurs connus : on ne sait pas
        assert RelayServer._dns_addresses("publie.ailleurs.test") is None
    finally:
        authority.close()


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


def test_tunnels_forward_to_127_0_0_1(server, monkeypatch):
    # « localhost » donne d'abord ::1, où le Relay n'écoute pas : l'OpenSSH de Windows
    # perdait la connexion sans essayer 127.0.0.1, et serveo comme localhost.run
    # répondaient « 502 » à tout (2026-10-19)
    commands = {}
    monkeypatch.setattr(relay_server.shutil, "which", lambda name: name)
    monkeypatch.setattr(server, "_spawn_tunnel",
                        lambda provider, cmd, **kwargs: commands.__setitem__(provider, cmd))

    server._start_cloudflared()
    server._start_serveo()
    server._start_localhost_run()

    target = f"127.0.0.1:{server.port}"
    assert commands["cloudflared"][-1] == f"http://{target}"
    for provider in ("serveo", "localhost.run"):
        cmd = commands[provider]
        assert cmd[cmd.index("-R") + 1] == f"80:{target}"


def test_serveo_address_is_read_on_its_new_domain(server, monkeypatch):
    # serveo annonce maintenant *.serveousercontent.com : l'ancien motif (*.serveo.net)
    # ne le voyait pas, et serveo n'entrait jamais dans le QR code (2026-10-19)
    reading = {}
    monkeypatch.setattr(relay_server.shutil, "which", lambda name: name)
    monkeypatch.setattr(server, "_spawn_tunnel",
                        lambda provider, cmd, **kwargs: reading.update(kwargs))
    server._start_serveo()

    url = "https://2806d784fd3ec9bb-203-0-113-7.serveousercontent.com"
    output = [
        # Bannière : une adresse serveo qui n'est pas celle du tunnel
        "Tip (5): Add your SSH key to reserve names: https://console.serveo.net/settings?n=5",
        chr(27) + "[32mForwarding HTTP traffic from " + url,
    ]
    echo = [sys.executable, "-c", "import sys; [print(line) for line in sys.argv[1:]]"]
    RelayServer._spawn_tunnel(server, "serveo", echo + output, **reading)

    deadline = time.monotonic() + 10
    while "serveo" not in server.tunnel_urls and time.monotonic() < deadline:
        time.sleep(0.05)
    assert server.tunnel_urls.get("serveo") == url


def test_serveo_is_off_by_default():
    # Le nom d'un tunnel serveo contient l'adresse IP publique du réseau du PC
    # lancé seulement si on le demande
    assert RelayServer(config={})._tunnel_provider_names == ["cloudflared", "localhost.run"]
    asked = RelayServer(config={"tunnel_providers": ["cloudflared", "serveo"]})
    assert asked._tunnel_provider_names == ["cloudflared", "serveo"]


def test_tunnel_addresses_are_not_listed_without_token(server):
    # Qui connaît une adresse de tunnel ne doit pas obtenir les autres (dont celle
    # de serveo, IP publique comprise) : GET /api/tunnels, sans jeton, n'existe plus
    testclient = pytest.importorskip("fastapi.testclient")
    server._set_tunnel_url("localhost.run", LHR)
    client = testclient.TestClient(server._app)
    assert client.get("/api/tunnels").status_code == 404
    health = client.get("/api/health")
    assert health.status_code == 200 and LHR not in health.text


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


def _tls_files(folder, name):
    """Autorité de test, et certificat qu'elle signe pour `name` : (autorité, certificat, clé)."""
    now = datetime.now(timezone.utc)

    def certificate(subject, public_key, signing_key, extensions):
        builder = (x509.CertificateBuilder()
                   .subject_name(subject).issuer_name(authority_name)
                   .public_key(public_key).serial_number(x509.random_serial_number())
                   .not_valid_before(now - timedelta(minutes=5))
                   .not_valid_after(now + timedelta(days=1)))
        for extension, critical in extensions:
            builder = builder.add_extension(extension, critical=critical)
        return builder.sign(signing_key, hashes.SHA256())

    authority_key = ec.generate_private_key(ec.SECP256R1())
    authority_name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "Autorité de test")])
    authority = certificate(authority_name, authority_key.public_key(), authority_key, [
        (x509.BasicConstraints(ca=True, path_length=None), True),
        (x509.KeyUsage(digital_signature=True, content_commitment=False,
                       key_encipherment=False, data_encipherment=False, key_agreement=False,
                       key_cert_sign=True, crl_sign=True, encipher_only=False,
                       decipher_only=False), True),
        (x509.SubjectKeyIdentifier.from_public_key(authority_key.public_key()), False),
    ])
    key = ec.generate_private_key(ec.SECP256R1())
    server = certificate(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, name)]),
                         key.public_key(), authority_key, [
        (x509.SubjectAlternativeName([x509.DNSName(name)]), False),
        (x509.BasicConstraints(ca=False, path_length=None), True),
        (x509.AuthorityKeyIdentifier.from_issuer_public_key(authority_key.public_key()), False),
    ])
    paths = (folder / "autorite.pem", folder / "certificat.pem", folder / "cle.pem")
    paths[0].write_bytes(authority.public_bytes(serialization.Encoding.PEM))
    paths[1].write_bytes(server.public_bytes(serialization.Encoding.PEM))
    paths[2].write_bytes(key.private_bytes(serialization.Encoding.PEM,
                                           serialization.PrivateFormat.PKCS8,
                                           serialization.NoEncryption()))
    return tuple(str(path) for path in paths)


class _HealthWithHost(_Health):
    """_Health, en notant l'en-tête Host de chaque requête."""

    hosts = []

    def do_GET(self):  # pylint: disable=invalid-name
        """Réponse fixée par le chemin."""
        self.hosts.append(self.headers.get("Host"))
        super().do_GET()


def test_direct_probe_goes_to_the_address_under_the_tunnel_name(tmp_path, monkeypatch):
    # Tunnel cloudflared : test envoyé à l'adresse donnée par les serveurs faisant autorité,
    # au nom du tunnel (SNI, certificat, Host), sans que le DNS du PC voie passer ce nom
    name = "essai.trycloudflare.com"
    authority, certificate, key = _tls_files(tmp_path, name)
    monkeypatch.setattr(relay_server.requests.certs, "where", lambda: authority)
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(certificate, key)
    server_names = []
    context.sni_callback = lambda sock, server_name, ctx: server_names.append(server_name)
    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), _HealthWithHost)
    httpd.socket = context.wrap_socket(httpd.socket, server_side=True)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    port = httpd.server_address[1]
    _HealthWithHost.hosts = []
    probe = RelayServer._probe_tunnel_at
    try:
        # Ce nom n'existe dans aucun DNS : seul l'envoi à l'adresse donnée le joint
        assert probe(f"https://{name}:{port}/ok", "127.0.0.1") is True
        assert server_names == [name] and _HealthWithHost.hosts == [f"{name}:{port}"]
        for path in ("/html", "/liste", "/autre", "/502", "/absent"):
            assert probe(f"https://{name}:{port}{path}", "127.0.0.1") is False, path
        # Certificat d'un autre nom : refusé, la vérification TLS porte sur le nom du tunnel
        assert probe(f"https://autre.trycloudflare.com:{port}/ok", "127.0.0.1") is False
    finally:
        httpd.shutdown()
        httpd.server_close()

    # Port fermé : refus de connexion, sans exception
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        closed = sock.getsockname()[1]
    assert probe(f"https://{name}:{closed}/ok", "127.0.0.1") is False
