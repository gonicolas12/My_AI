"""
Tests du client MCP (core/mcp_client.py) face aux deux versions du SDK.

Depuis la 2.0.0 (juillet 2026), « pip install mcp » installe le SDK 2.x, dont
les outils n'ont plus que ``input_schema`` : lire ``t.inputSchema`` levait
AttributeError, que connect() avalait (« Connexion échouée ») pour chaque
serveur MCP activé.

Dans l'appli, la connexion passait par asyncio.run : la boucle se fermait dès
la connexion faite, le serveur était arrêté et chaque appel d'outil échouait.
La session simulée ici se comporte comme la vraie (anyio) : elle ne sert que
dans sa boucle et se referme dans la tâche qui l'a ouverte. Aucun serveur réel
n'est lancé : le transport stdio et la session sont simulés.
"""

import asyncio
import contextlib
import threading
from pathlib import Path
from types import SimpleNamespace

import pytest
from packaging.requirements import Requirement

from core import mcp_client

SCHEMA = {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}
EMPTY = {"type": "object", "properties": {}}
READ_FILE = SimpleNamespace(name="read_file", description="Lit un fichier", input_schema=SCHEMA)


class _FakeTransport:
    """stdio_client simulé : « lance » le serveur et l'arrête en sortant."""

    def __init__(self, events):
        self.events = events
        self.task = None

    async def __aenter__(self):
        self.task = asyncio.current_task()
        self.events.append("serveur lancé")
        return ("lecture", "écriture")

    async def __aexit__(self, *exc):
        assert asyncio.current_task() is self.task, "transport refermé dans une autre tâche"
        self.events.append("serveur arrêté")
        return False


class _FakeSession:
    """ClientSession simulée, liée comme la vraie à sa boucle et à sa tâche."""

    def __init__(self, tools, events):
        self._tools = tools
        self.events = events
        self.loop = None
        self.task = None

    async def __aenter__(self):
        self.loop = asyncio.get_running_loop()
        self.task = asyncio.current_task()
        self.events.append("session ouverte")
        return self

    async def __aexit__(self, *exc):
        assert asyncio.current_task() is self.task, "session refermée dans une autre tâche"
        self.events.append("session fermée")
        return False

    async def initialize(self):
        return None

    async def list_tools(self):
        return SimpleNamespace(tools=self._tools)

    async def call_tool(self, name, arguments):
        if asyncio.get_running_loop() is not self.loop:
            raise RuntimeError("session utilisée hors de sa boucle")
        return SimpleNamespace(content=[SimpleNamespace(text=f"{name} {arguments['path']}")])


def _fake_sdk(monkeypatch, tools, session_class=_FakeSession):
    """Remplace le SDK MCP par le transport et la session simulés ; renvoie le journal."""
    events = []
    # raising=False : ces noms n'existent pas dans le module si le SDK est absent
    monkeypatch.setattr(mcp_client, "MCP_SDK_AVAILABLE", True)
    monkeypatch.setattr(mcp_client, "AsyncExitStack", contextlib.AsyncExitStack, raising=False)
    monkeypatch.setattr(mcp_client, "StdioServerParameters", lambda **kw: SimpleNamespace(**kw),
                        raising=False)
    monkeypatch.setattr(mcp_client, "stdio_client", lambda _params: _FakeTransport(events),
                        raising=False)
    monkeypatch.setattr(mcp_client, "ClientSession",
                        lambda _read, _write: session_class(tools, events), raising=False)
    return events


def _connect(monkeypatch, tools):
    """Connecte puis déconnecte un serveur « filesystem » simulé qui expose ces outils."""
    _fake_sdk(monkeypatch, tools)
    conn = mcp_client._MCPServerConnection(  # pylint: disable=protected-access
        mcp_client.MCPServerConfig(name="filesystem", command="npx")
    )

    async def scenario():
        connected = await conn.connect()
        await conn.disconnect()
        return connected

    assert asyncio.run(scenario()) is True
    return conn


def test_sdk_2x_tool_with_input_schema_only(monkeypatch):
    conn = _connect(monkeypatch, [READ_FILE])
    assert [(t.name, t.description, t.parameters) for t in conn.tools] == [
        ("filesystem__read_file", "Lit un fichier", SCHEMA)
    ]


def test_sdk_1x_tool_with_camel_case_input_schema(monkeypatch):
    tool = SimpleNamespace(name="read_file", description="Lit un fichier", inputSchema=SCHEMA)
    conn = _connect(monkeypatch, [tool])
    assert conn.tools[0].parameters == SCHEMA


def test_tool_without_schema_or_description(monkeypatch):
    conn = _connect(monkeypatch, [SimpleNamespace(name="ping", description=None, input_schema=None)])
    assert (conn.tools[0].description, conn.tools[0].parameters) == ("", EMPTY)


def test_installed_sdk_tool_parsed_from_server_json():
    # Le serveur envoie toujours « inputSchema » (JSON-RPC) ; le SDK installé,
    # 1.x ou 2.x, en fait l'objet que lit connect()
    types = pytest.importorskip("mcp.types")
    tool = types.Tool.model_validate({"name": "read_file", "inputSchema": SCHEMA})
    assert mcp_client._input_schema(tool) == SCHEMA  # pylint: disable=protected-access


def test_app_path_keeps_the_server_alive_between_calls(monkeypatch):
    events = _fake_sdk(monkeypatch, [READ_FILE])
    manager = mcp_client.MCPManager()
    manager.register_mcp_server_from_dict(
        "filesystem", {"command": "npx", "args": ["serveur"], "enabled": True}
    )
    # Comme core/ai_engine.py : connexion depuis un fil, appels depuis un autre
    thread = threading.Thread(target=manager.connect_external_servers_sync)
    thread.start()
    thread.join(10)
    assert manager.execute_tool_sync("filesystem__read_file", {"path": "a.txt"}) == "read_file a.txt"
    assert manager.execute_tool_sync("filesystem__read_file", {"path": "b.txt"}) == "read_file b.txt"
    assert events == ["serveur lancé", "session ouverte"]

    manager.disconnect_all_sync()
    assert events == ["serveur lancé", "session ouverte", "session fermée", "serveur arrêté"]


def test_failed_connection_stops_the_server(monkeypatch, capsys):
    class _IncompatibleSession(_FakeSession):
        async def initialize(self):
            raise RuntimeError("protocole incompatible")

    events = _fake_sdk(monkeypatch, [READ_FILE], session_class=_IncompatibleSession)
    conn = mcp_client._MCPServerConnection(  # pylint: disable=protected-access
        mcp_client.MCPServerConfig(name="filesystem", command="npx")
    )
    assert asyncio.run(conn.connect()) is False
    # Le processus du serveur ne reste pas en vie derrière un échec
    assert events == ["serveur lancé", "session ouverte", "session fermée", "serveur arrêté"]
    assert "Connexion échouée 'filesystem': protocole incompatible" in capsys.readouterr().out


def test_requirements_keep_sdk_1x_with_security_fixes():
    text = (Path(__file__).resolve().parent.parent / "requirements.txt").read_text(encoding="utf-8")
    lines = [line.split("#")[0].strip() for line in text.splitlines()]
    (mcp_line,) = [line for line in lines if line and Requirement(line).name == "mcp"]
    specifier = Requirement(mcp_line).specifier
    # 1.30.0 corrige GHSA-rwrf-2pqf-9j8j ; la 2.x attend la migration du client
    assert specifier.contains("1.30.0")
    assert not specifier.contains("1.29.1")
    assert not specifier.contains("2.0.0")
