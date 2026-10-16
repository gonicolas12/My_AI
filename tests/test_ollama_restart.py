"""
Tests du redémarrage d'Ollama au lancement (launch_unified._restart_ollama).

Le lanceur arrête Ollama, application bureau comprise, pour le relancer avec
ses propres variables. Or taskkill rend la main avant la fin de l'arrêt : le
serveur tué gardait encore un instant le port 11434 sans plus répondre, le
lanceur le croyait arrêté, et « ollama serve », relancé aussitôt, s'arrêtait
faute de port. L'application bureau étant arrêtée elle aussi, plus rien ne
relançait Ollama. Aucun vrai Ollama n'est lancé ici : le port, les serveurs et
l'horloge sont simulés.
"""

# Les fonctions du lanceur testées ici sont privées
# pylint: disable=protected-access

import importlib.util
import socket
import sys
import types
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent

# Imports lourds du lanceur (modèles d'embeddings, Ollama) : inutiles ici
_STUBS = {
    "interfaces.onboarding": {"sync_custom_model": None},
    "core.passage_embeddings": {"prefetch_in_background": None},
    "core.network": {"configure_network_environment": lambda: None},
}


class FakeServer:
    """Processus « ollama serve » simulé."""

    def __init__(self, returncode=None):
        self.returncode = returncode

    def poll(self):
        """Code de sortie, None tant que le serveur tourne."""
        return self.returncode


class FakeOllama:
    """Port d'Ollama, serveurs et horloge simulés, comme observés sous Windows.

    Un serveur tué ne répond plus mais garde son port encore un instant ; au
    démarrage, un serveur tient le port mais ne répond qu'une fois les GPU
    détectés ; « ollama serve » lancé sur un port pris s'arrête aussitôt.
    """

    def __init__(self):
        self.now = 0.0
        self.holder = None  # ce qui tient le port : None, "ollama" ou "autre"
        self.answers = False  # le serveur en place répond aux requêtes
        self.release_delay = 0.0  # temps pendant lequel un serveur tué garde le port
        self.released_at = None  # fin de l'arrêt du serveur tué
        self.startup_requests = 2  # requêtes sans réponse au démarrage (détection des GPU)
        self.pending = 0  # requêtes auxquelles le serveur en place ne répondra pas encore
        self.crash = False  # « ollama serve » s'arrête au démarrage, même port libre
        self.kills = 0
        self.requests = 0
        self.launches = []  # port libre ou non au lancement de chaque « ollama serve »

    def monotonic(self):
        """time.monotonic du lanceur."""
        return self.now

    def sleep(self, seconds):
        """time.sleep du lanceur : avance l'horloge, sans attendre."""
        self.now += seconds

    def port_is_free(self):
        """launch_unified._port_is_free"""
        if self.released_at is not None and self.now >= self.released_at:
            self.holder, self.released_at = None, None
        return self.holder is None

    def is_running(self, timeout=2.0):
        """launch_unified._ollama_is_running"""
        del timeout
        self.requests += 1
        if self.holder == "ollama" and not self.answers and self.released_at is None:
            if self.pending:
                self.pending -= 1
            else:
                self.answers = True
        return self.answers

    def kill(self):
        """launch_unified._kill_ollama : n'arrête qu'Ollama."""
        self.kills += 1
        if self.holder == "ollama":
            self.answers = False
            self.released_at = self.now + self.release_delay

    def popen(self, command, **_kwargs):
        """subprocess.Popen, pour « ollama serve »."""
        assert command == ["ollama", "serve"]
        free = self.port_is_free()
        self.launches.append(free)
        if self.crash or not free:
            # « bind: Only one usage of each socket address » quand le port est pris
            return FakeServer(returncode=1)
        self.holder, self.answers, self.pending = "ollama", False, self.startup_requests
        return FakeServer()


@pytest.fixture(name="launcher")
def _launcher(monkeypatch):
    """launch_unified chargé sans ses imports lourds."""
    for name, attributes in _STUBS.items():
        module = types.ModuleType(name)
        vars(module).update(attributes)
        monkeypatch.setitem(sys.modules, name, module)
    monkeypatch.setattr(sys, "path", list(sys.path))  # le lanceur y ajoute sa racine
    spec = importlib.util.spec_from_file_location("launch_unified", ROOT / "launch_unified.py")
    launcher = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(launcher)
    return launcher


@pytest.fixture(name="ollama")
def _ollama(launcher, monkeypatch):
    """Ollama simulé, branché sur le lanceur."""
    ollama = FakeOllama()
    monkeypatch.setattr(launcher, "_port_is_free", ollama.port_is_free)
    monkeypatch.setattr(launcher, "_ollama_is_running", ollama.is_running)
    monkeypatch.setattr(launcher, "_kill_ollama", ollama.kill)
    monkeypatch.setattr(launcher.subprocess, "Popen", ollama.popen)
    clock = types.SimpleNamespace(monotonic=ollama.monotonic, sleep=ollama.sleep)
    monkeypatch.setattr(launcher, "time", clock)
    return ollama


@pytest.fixture(name="ensure")
def _ensure(launcher, ollama, monkeypatch):
    """_ensure_ollama_parallel, sans écrire dans le registre ni lire le dernier calibrage."""
    del ollama  # branché sur le lanceur
    monkeypatch.setattr(launcher, "_persist_env_var", lambda _name, _value: None)
    monkeypatch.setattr(launcher, "saved_env", dict)
    monkeypatch.setattr(launcher, "placement_label", lambda: None)
    monkeypatch.setenv("OLLAMA_NUM_PARALLEL", "4")  # rétablie après le test
    return launcher._ensure_ollama_parallel


def test_waits_for_killed_server_to_release_port(launcher, ollama):
    """Cas observé : le serveur tué ne répond plus mais garde le port un instant."""
    ollama.holder, ollama.answers = "ollama", True  # application bureau en marche
    ollama.release_delay = 0.8

    assert launcher._restart_ollama({}) is True
    assert ollama.kills == 1
    assert ollama.launches == [True]  # lancé une fois, port rendu


def test_replaces_server_still_detecting_gpus(launcher, ollama):
    """Application bureau tout juste lancée : son serveur tient le port sans répondre encore."""
    ollama.holder, ollama.pending = "ollama", 5

    assert launcher._restart_ollama({}) is True
    assert ollama.kills == 1
    assert ollama.launches == [True]  # le nôtre, avec nos variables, remplace le sien


def test_starts_server_when_none_runs(launcher, ollama):
    assert launcher._restart_ollama({}) is True
    assert ollama.kills == 0
    assert ollama.launches == [True]


def test_server_stopped_at_startup_is_not_waited_for(launcher, ollama):
    ollama.crash = True

    assert launcher._restart_ollama({}) is False
    assert ollama.requests == 1  # et non 20 requêtes, ≈ 50 s sous Windows


def test_server_that_cannot_be_stopped_is_kept(launcher, ollama):
    """Ollama d'un service système ou de Docker : hors de portée de _kill_ollama."""
    ollama.holder, ollama.answers = "autre", True

    assert launcher._restart_ollama({}) is True
    assert ollama.launches == [False]
    assert ollama.now == pytest.approx(launcher._PORT_RELEASE_TIMEOUT, abs=0.2)


def test_restart_is_announced(ensure, ollama, capsys):
    ollama.holder, ollama.answers = "ollama", True

    ensure()
    out = capsys.readouterr().out
    assert "Redémarrage d'Ollama" in out
    assert "✅ Ollama prêt" in out


def test_server_that_did_not_start_is_reported(ensure, ollama, capsys):
    ollama.crash = True

    ensure()
    out = capsys.readouterr().out
    assert "Ollama n'a pas pu démarrer" in out
    assert "il démarrera sous peu" not in out


def test_server_still_starting_is_reported(ensure, ollama, capsys):
    ollama.startup_requests = 100  # détection des GPU plus longue que l'attente

    ensure()
    assert "il démarrera sous peu" in capsys.readouterr().out


def test_port_is_free_sees_a_listening_server(launcher, monkeypatch):
    """Vrai socket, sur un port libre quelconque plutôt que celui d'Ollama."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
        server.bind(("127.0.0.1", 0))
        monkeypatch.setattr(launcher, "_OLLAMA_PORT", server.getsockname()[1])
        server.listen()
        assert launcher._port_is_free() is False
    assert launcher._port_is_free() is True


# ── Options du lanceur ──────────────────────────────────────────────────────


def test_web_interface_is_the_default(launcher):
    args = launcher._parse_args([])
    assert (args.ui, args.dev, args.headless, args.port) == ("web", False, False, 0)


def test_old_ui_option_accepts_only_the_web_interface(launcher):
    # « --ui web » des commandes existantes ; l'interface Tk n'existe plus
    assert launcher._parse_args(["--ui", "web", "--dev"]).dev is True
    assert launcher._parse_args(["--dev", "--port", "5190"]).port == 5190
    for retired in ("tk", "qt"):
        with pytest.raises(SystemExit):
            launcher._parse_args(["--ui", retired])


def test_the_launcher_opens_the_web_window(launcher, monkeypatch):
    """main() : la fenêtre web, avec ce module comme lanceur (étapes de lifecycle.py)."""
    opened = []
    lifecycle = types.ModuleType("interfaces.desktop.lifecycle")
    lifecycle.run_desktop = lambda module, dev, port: opened.append((module, dev, port))
    monkeypatch.setitem(sys.modules, "interfaces.desktop.lifecycle", lifecycle)
    monkeypatch.setitem(sys.modules, "launch_unified", launcher)
    monkeypatch.setattr(sys, "argv", ["launch_unified.py", "--dev"])
    monkeypatch.setattr(launcher.os, "_exit", lambda code: (_ for _ in ()).throw(SystemExit(code)))

    with pytest.raises(SystemExit) as stopped:
        launcher.main()
    assert stopped.value.code == 0
    assert opened == [(launcher, True, 0)]
