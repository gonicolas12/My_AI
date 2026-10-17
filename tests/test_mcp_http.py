"""HTTP MCP : vrai SDK, requêtes HTTP observées et réponses Ollama scriptées."""

import asyncio
import copy
import json
from contextlib import asynccontextmanager
from pathlib import Path

import httpx
import pytest
import yaml

from core import mcp_client
from core.config import Config
from core.mcp_client import HTTP_USER_AGENT, MCPManager, MCPServerConfig

ENDPOINT = "https://search.parallel.ai/mcp"
PAGE = "https://docs.python.org/3/library/asyncio.html"


@pytest.fixture
def wire(monkeypatch):
    """Intercepte le réseau du SDK, pas le dispatcher ni ClientSession."""
    from mcp.client.streamable_http import streamablehttp_client

    class Wire:
        requests = None
        mode = "normal"
        method = "tools/call"
        closed = 0
        started = None
        paginated = False

        def __init__(self):
            self.requests = []

        async def handle(self, request):
            payload = json.loads(request.content)
            self.requests.append((str(request.url), dict(request.headers), payload))
            method = payload["method"]
            if method == self.method:
                if self.started:
                    self.started.set()
                if self.mode == "slow":
                    await asyncio.sleep(60)
                if self.mode == "http_error":
                    return httpx.Response(503, text="Service unavailable")
                if self.mode == "unauthorized":
                    return httpx.Response(401, text="Unauthorized")
            if "id" not in payload:
                return httpx.Response(202)
            if method == "initialize":
                result = {"protocolVersion": payload["params"]["protocolVersion"],
                          "capabilities": {"tools": {}},
                          "serverInfo": {"name": "fixture", "version": "1"}}
            elif method == "tools/list":
                names = ["web_search", "web_fetch"]
                if self.paginated:
                    names = ["web_fetch"] if payload.get("params", {}).get("cursor") else ["web_search"]
                result = {"tools": [{"name": n, "description": n,
                                      "inputSchema": {"type": "object", "properties": {}}}
                                     for n in names]}
                if self.paginated and names == ["web_search"]:
                    result["nextCursor"] = "page-2"
            elif method == "tools/call":
                if self.mode == "tool_error":
                    result = {"isError": True, "content": [{"type": "text", "text": "Quota exceeded"}]}
                elif self.mode == "structured":
                    result = {"content": [], "structuredContent": {"url": PAGE}}
                else:
                    text = (f"asyncio documentation: {PAGE}" if payload["params"]["name"] == "web_search"
                            else f"{PAGE}\nasyncio provides async/await concurrency.")
                    result = {"content": [{"type": "text", "text": text}]}
            else:
                raise AssertionError(method)
            return httpx.Response(200, json={"jsonrpc": "2.0", "id": payload["id"], "result": result})

    observed = Wire()

    @asynccontextmanager
    async def transport(url, **kwargs):
        def factory(headers=None, timeout=None, auth=None):
            return httpx.AsyncClient(transport=httpx.MockTransport(observed.handle),
                                     headers=headers, timeout=timeout, auth=auth)
        try:
            async with streamablehttp_client(url, httpx_client_factory=factory, **kwargs) as streams:
                yield streams
        finally:
            observed.closed += 1

    monkeypatch.setattr(mcp_client, "streamablehttp_client", transport)
    # Des identifiants ambiants ne doivent pas modifier le préréglage anonyme.
    monkeypatch.setenv("PARALLEL_API_KEY", "must-not-be-sent")
    return observed


def manager(**overrides):
    obj = MCPManager()
    obj.register_mcp_server_from_dict("parallel_search", {
        "enabled": True, "transport": "streamable-http", "url": ENDPOINT,
        **overrides,
    })
    return obj


def test_config_defaults_and_saved_choices(tmp_path, wire):
    config = Config(str(Path(__file__).resolve().parents[1] / "config.yaml"))
    servers = config.get_section("mcp")["servers"]
    assert servers["parallel_search"]["enabled"] is False
    obj = MCPManager()
    for name, settings in servers.items():
        obj.register_mcp_server_from_dict(name, settings)
    obj.connect_external_servers_sync()
    assert obj.get_ollama_tools() == []
    assert wire.requests == []
    saved = tmp_path / "saved.yaml"
    choices = {"mcp": {"servers": {"custom": {"command": "my-server", "enabled": True}}}}
    saved.write_text(yaml.safe_dump(choices), encoding="utf-8")
    assert Config(str(saved)).get_section("mcp") == choices["mcp"]
    assert saved.read_text(encoding="utf-8") == yaml.safe_dump(choices)


def test_dispatch_and_results_survive_startup_loop(wire):
    obj = manager()
    # Le même chemin sync que le démarrage et les appels depuis AIEngine.
    obj.connect_external_servers_sync()
    names = [t["function"]["name"] for t in obj.get_ollama_tools()]
    assert names == ["parallel_search__web_search", "parallel_search__web_fetch"]
    search = obj.execute_tool_sync(names[0], {"objective": "Python asyncio documentation"})
    fetch = obj.execute_tool_sync(names[1], {"urls": [PAGE]})
    assert PAGE in search and "async/await" in fetch
    assert wire.closed == 3
    assert {url for url, _, _ in wire.requests} == {ENDPOINT}
    assert all(headers["user-agent"] == HTTP_USER_AGENT for _, headers, _ in wire.requests)
    assert all("authorization" not in headers for _, headers, _ in wire.requests)
    calls = [p["params"] for _, _, p in wire.requests if p["method"] == "tools/call"]
    assert calls[1] == {"name": "web_fetch", "arguments": {"urls": [PAGE]}}


def test_scripted_ollama_consumes_search_and_fetch(wire, monkeypatch):
    """LocalLLM réel, réponses du modèle scriptées ; aucun modèle réel revendiqué."""
    import models.local_llm as local_llm
    obj = manager()
    obj.connect_external_servers_sync()
    llm = local_llm.LocalLLM.__new__(local_llm.LocalLLM)
    llm.is_ollama_available = True
    llm.model = "scripted-test-model"
    llm.chat_url = "http://127.0.0.1:9/api/chat"
    llm.timeout = 1
    llm.gen_temperature = 0
    llm.gen_num_ctx = 2048
    llm.conversation_history = []
    llm.max_history_length = 20
    sent = []

    def reply(url, **kwargs):
        assert url == llm.chat_url
        sent.append(copy.deepcopy(kwargs["json"]))
        if len(sent) < 3:
            name, args = (("web_search", {"objective": "Python asyncio documentation"})
                          if len(sent) == 1 else ("web_fetch", {"urls": [PAGE]}))
            message = {"role": "assistant", "tool_calls": [{"function": {
                "name": "parallel_search__" + name, "arguments": args}}]}
        else:
            tool_results = [m["content"] for m in sent[-1]["messages"] if m["role"] == "tool"]
            assert len(tool_results) == 2 and all(PAGE in result for result in tool_results)
            assert "async/await" in tool_results[1]
            message = {"role": "assistant", "content": f"asyncio supports async/await: {PAGE}"}
        return type("Response", (), {"status_code": 200, "json": lambda self: {"message": message}})()

    monkeypatch.setattr(local_llm, "_resilient_post", reply)
    result = llm.generate_with_tools("Research asyncio", obj.get_ollama_tools(), obj.execute_tool_sync)
    assert result["success"] and PAGE in result["response"]
    assert len(result["tool_calls"]) == 2
    assert len(sent) == 3


def test_explicit_url_headers_timeout_and_stdio_preserved(wire):
    url = "https://custom.example/mcp?mode=fast"
    obj = manager(url=url, headers={"Authorization": "Bearer explicit"}, timeout=2)
    obj.register_mcp_server_from_dict("old", {"command": "python", "args": ["server.py"], "env": {"KEY": "saved"}})
    assert obj._server_configs["old"].transport == "stdio"
    assert obj._server_configs["old"].args == ["server.py"]
    assert obj._server_configs["old"].env == {"KEY": "saved"}
    # Ne pas lancer le serveur stdio de cette fixture.
    obj._server_configs.pop("old")
    obj.connect_external_servers_sync()
    assert PAGE in obj.execute_tool_sync("parallel_search__web_search", {})
    assert all(u == url and h["authorization"] == "Bearer explicit" for u, h, _ in wire.requests)
    assert obj._server_configs["parallel_search"].timeout == 2


def test_explicit_user_agent_has_no_duplicate_header(wire):
    obj = manager(headers={"User-Agent": "My_AI custom deployment"})
    obj.connect_external_servers_sync()
    assert all(h["user-agent"] == "My_AI custom deployment" for _, h, _ in wire.requests)


@pytest.mark.parametrize("mode", ["http_error", "unauthorized", "tool_error", "structured"])
def test_response_contract_and_no_fallback(wire, mode):
    obj = manager()
    obj.register_local_tool("web_search", "Existing search", {}, lambda: pytest.fail("Unexpected fallback"))
    obj.connect_external_servers_sync()
    wire.mode = mode
    result = obj.execute_tool_sync("parallel_search__web_search", {})
    assert (PAGE in result) if mode == "structured" else ("Erreur" in result)
    if mode == "tool_error":
        assert "Quota exceeded" in result
    assert len([p for _, _, p in wire.requests if p["method"] == "tools/call"]) == 1


def test_paginated_discovery_and_unavailable_server(wire):
    wire.paginated = True
    obj = manager()
    obj.connect_external_servers_sync()
    assert len(obj.get_ollama_tools()) == 2
    wire.method = "initialize"
    wire.mode = "unauthorized"
    bad = manager()
    bad.register_local_tool("local", "Local tool", {}, lambda: "still works")
    bad.connect_external_servers_sync()
    assert [t["function"]["name"] for t in bad.get_ollama_tools()] == ["local"]
    assert bad.execute_tool_sync("local", {}) == "still works"


def test_call_and_discovery_timeout_close_transport(wire):
    obj = manager(timeout=0.05)
    obj.connect_external_servers_sync()
    wire.mode = "slow"
    result = obj.execute_tool_sync("parallel_search__web_search", {})
    assert "Délai MCP dépassé" in result and wire.closed == 2
    wire.method = "initialize"
    bad = manager(timeout=0.05)
    bad.connect_external_servers_sync()
    assert bad.get_ollama_tools() == [] and wire.closed == 3


@pytest.mark.asyncio
async def test_cancellation_closes_session_and_propagates(wire):
    obj = manager()
    await obj.connect_external_servers()
    wire.mode = "slow"
    wire.started = asyncio.Event()
    task = asyncio.create_task(obj.execute_tool_async("parallel_search__web_fetch", {"urls": [PAGE]}))
    await asyncio.wait_for(wire.started.wait(), 1)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert wire.closed == 2
    # Un appel ultérieur peut repartir avec une nouvelle session.
    wire.mode = "normal"
    assert PAGE in await obj.execute_tool_async("parallel_search__web_fetch", {"urls": [PAGE]})
    await obj.disconnect_all()
    assert obj.get_ollama_tools() == []


@pytest.mark.parametrize("settings", [
    {"url": "file:///etc/passwd"}, {"url": "https://user:secret@example.com/mcp"},
    {"url": "https://example.com/mcp#fragment"}, {"timeout": 0},
    {"timeout": float("inf")}, {"timeout": True}, {"headers": {"Key": 12}},
    {"transport": "sse"},
])
def test_invalid_http_settings(settings):
    with pytest.raises(ValueError):
        MCPServerConfig(name="bad", **{"transport": "streamable-http", "url": ENDPOINT, **settings})


def test_missing_http_sdk_keeps_local_and_stdio_support(wire, monkeypatch):
    monkeypatch.setattr(mcp_client, "streamablehttp_client", None)
    obj = manager()
    obj.register_local_tool("local", "Local tool", {}, lambda: "works")
    obj.connect_external_servers_sync()
    assert [t["function"]["name"] for t in obj.get_ollama_tools()] == ["local"]
    assert obj.execute_tool_sync("local", {}) == "works"
    assert wire.requests == []
