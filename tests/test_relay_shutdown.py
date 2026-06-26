"""
Tests d'arrêt propre du Relay (évite le terminal figé à la fermeture du GUI).

Quand l'app se ferme, les sous-processus de tunnel (cloudflared/ssh) doivent
être terminés, sinon ils restent orphelins et gardent la console → terminal figé.
On valide ici la logique de _stop_tunnel sans démarrer de vrai serveur.
"""

import subprocess
import threading

from relay.relay_server import RelayServer


class _FakeProc:
    """Mime subprocess.Popen pour _stop_tunnel (terminate/wait/kill)."""

    def __init__(self, hang: bool = False):
        self.hang = hang          # si True, wait() expire une fois -> kill attendu
        self.terminated = False
        self.killed = False
        self._waited = False

    def terminate(self):
        self.terminated = True

    def wait(self, timeout=None):
        if self.hang and not self._waited:
            self._waited = True
            raise subprocess.TimeoutExpired(cmd="tunnel", timeout=timeout)
        return 0

    def kill(self):
        self.killed = True


def _make_server_with_procs(procs):
    """Instancie un RelayServer minimal (sans __init__) pour tester _stop_tunnel."""
    server = RelayServer.__new__(RelayServer)
    server._tunnel_processes = dict(procs)
    server._tunnel_urls = {name: f"https://{name}.example" for name in procs}
    server._tunnel_urls_lock = threading.Lock()
    return server


def test_stop_tunnel_terminates_all_and_clears():
    procs = {"cloudflared": _FakeProc(), "serveo": _FakeProc(),
             "localhost.run": _FakeProc()}
    server = _make_server_with_procs(procs)

    server._stop_tunnel()

    assert all(p.terminated for p in procs.values())
    assert server._tunnel_processes == {}
    assert server._tunnel_urls == {}


def test_stop_tunnel_kills_straggler_on_timeout():
    hung = _FakeProc(hang=True)
    procs = {"cloudflared": _FakeProc(), "serveo": hung}
    server = _make_server_with_procs(procs)

    server._stop_tunnel()

    # Le process qui n'a pas répondu au terminate est tué (kill) en repli.
    assert hung.terminated is True
    assert hung.killed is True
    assert server._tunnel_processes == {}


def test_spawn_tunnel_redirects_stdin(monkeypatch):
    """_spawn_tunnel doit lancer le sous-processus avec stdin=DEVNULL pour ne
    pas hériter du stdin de la console (cause du terminal figé)."""
    server = RelayServer.__new__(RelayServer)
    server._tunnel_processes = {}
    server._tunnel_urls = {}
    server._tunnel_urls_lock = threading.Lock()

    captured = {}

    class _DummyPopen:
        def __init__(self, cmd, **kwargs):
            captured.update(kwargs)
            self.stdout = []  # itérable vide -> le thread lecteur sort aussitôt

    monkeypatch.setattr(subprocess, "Popen", _DummyPopen)

    server._spawn_tunnel(
        provider="cloudflared",
        cmd=["cloudflared", "tunnel"],
        url_pattern=r"https://x",
    )

    assert captured.get("stdin") == subprocess.DEVNULL
    assert "cloudflared" in server._tunnel_processes
