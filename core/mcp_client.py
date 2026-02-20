"""
MCP Client - Gestionnaire d'outils Model Context Protocol
Permet à Ollama d'appeler des outils locaux et des serveurs MCP externes.

Architecture :
- LocalTool   : fonctions Python in-process (wrapping des capacités existantes)
- MCPServer   : processus externes via transport stdio (filesystem, git, sqlite, etc.)

Ollama reçoit la liste unifiée des outils et décide lui-même lequel appeler.
"""

import asyncio
import concurrent.futures
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

# MCP SDK (pip install mcp) — optionnel, dégradation gracieuse si absent
try:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    from contextlib import AsyncExitStack

    MCP_SDK_AVAILABLE = True
except ImportError:
    MCP_SDK_AVAILABLE = False


# ---------------------------------------------------------------------------
# Structures de données
# ---------------------------------------------------------------------------

@dataclass
class ToolSchema:
    """Schéma d'un outil au format JSON Schema (compatible Ollama / OpenAI)."""
    name: str
    description: str
    parameters: Dict[str, Any]  # JSON Schema object

    def to_ollama_format(self) -> Dict:
        """Convertit ce schéma au format attendu par l'API Ollama."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }


@dataclass
class LocalTool:
    """Outil in-process : appel direct à une fonction Python."""
    schema: ToolSchema
    callable: Callable[..., str]  # sync ou async


@dataclass
class MCPServerConfig:
    """Configuration d'un serveur MCP externe."""
    name: str
    command: str
    args: List[str] = field(default_factory=list)
    env: Optional[Dict[str, str]] = None
    enabled: bool = True


# ---------------------------------------------------------------------------
# Connexion à un serveur MCP externe
# ---------------------------------------------------------------------------

class _MCPServerConnection:
    """Gère la connexion à un serveur MCP via stdio."""

    def __init__(self, config: MCPServerConfig):
        self.config = config
        self.session: Optional[Any] = None  # ClientSession quand connecté
        self.tools: List[ToolSchema] = []
        self._exit_stack = None

    async def connect(self) -> bool:
        """Tente de se connecter au serveur MCP et de découvrir ses outils."""
        if not MCP_SDK_AVAILABLE:
            print(f"⚠️ [MCP] SDK non installé. Ignoré : {self.config.name}")
            return False

        try:
            self._exit_stack = AsyncExitStack()
            server_params = StdioServerParameters(
                command=self.config.command,
                args=self.config.args,
                env=self.config.env,
            )
            transport = await self._exit_stack.enter_async_context(
                stdio_client(server_params)
            )
            self.session = await self._exit_stack.enter_async_context(
                ClientSession(transport[0], transport[1])
            )
            await self.session.initialize()

            # Découverte des outils exposés par ce serveur
            response = await self.session.list_tools()
            self.tools = [
                ToolSchema(
                    name=f"{self.config.name}__{t.name}",  # namespace
                    description=t.description or "",
                    parameters=t.inputSchema or {"type": "object", "properties": {}},
                )
                for t in response.tools
            ]
            print(
                f"✅ [MCP] Serveur '{self.config.name}' connecté — "
                f"{len(self.tools)} outils"
            )
            return True

        except FileNotFoundError:
            print(
                f"⚠️ [MCP] Commande introuvable pour '{self.config.name}': "
                f"{self.config.command}. Serveur ignoré."
            )
            return False
        except Exception as exc:
            print(f"⚠️ [MCP] Connexion échouée '{self.config.name}': {exc}")
            return False

    async def call_tool(self, original_tool_name: str, arguments: Dict) -> str:
        """Appelle un outil sur ce serveur MCP avec les arguments donnés."""
        if not self.session:
            raise RuntimeError(f"Serveur MCP '{self.config.name}' non connecté")
        result = await self.session.call_tool(original_tool_name, arguments)
        if result.content:
            return "\n".join(
                c.text if hasattr(c, "text") else str(c) for c in result.content
            )
        return ""

    async def disconnect(self):
        """Ferme la connexion au serveur MCP."""
        if self._exit_stack:
            try:
                await self._exit_stack.aclose()
            except Exception:
                pass


# ---------------------------------------------------------------------------
# MCPManager — gestionnaire central
# ---------------------------------------------------------------------------

class MCPManager:
    """
    Gestionnaire central d'outils pour le projet.

    Deux couches :
    1. Outils locaux (in-process) — toujours disponibles, 0 dépendance
    2. Serveurs MCP externes (stdio) — optionnels, enrichissement progressif

    Usage dans AIEngine :
        manager = MCPManager()
        manager.register_local_tool(...)   # enregistrer les capacités existantes
        await manager.connect_external_servers()  # optionnel
        tools = manager.get_ollama_tools()  # passer à Ollama
        result = await manager.execute_tool(name, args)
    """

    def __init__(self):
        self._local_tools: Dict[str, LocalTool] = {}
        self._server_configs: Dict[str, MCPServerConfig] = {}
        self._server_connections: Dict[str, _MCPServerConnection] = {}
        self._external_tools: Dict[str, tuple] = {}  # name → (server_name, original_name)
        self._connected = False

    # ------------------------------------------------------------------
    # Enregistrement des outils locaux
    # ------------------------------------------------------------------

    def register_local_tool(
        self,
        name: str,
        description: str,
        parameters: Dict[str, Any],
        callable_fn: Callable,
    ):
        """
        Enregistre une fonction Python locale comme outil Ollama.

        Args:
            name: Nom de l'outil (snake_case, ex: "web_search")
            description: Description claire pour que le LLM sache quand l'utiliser
            parameters: JSON Schema des paramètres
            callable_fn: Fonction sync ou async à appeler
        """
        schema = ToolSchema(name=name, description=description, parameters=parameters)
        self._local_tools[name] = LocalTool(schema=schema, callable=callable_fn)
        print(f"🔧 [MCP] Outil local enregistré : {name}")

    # ------------------------------------------------------------------
    # Enregistrement des serveurs MCP externes
    # ------------------------------------------------------------------

    def register_mcp_server(self, config: MCPServerConfig):
        """Enregistre un serveur MCP externe (ne le connecte pas encore)."""
        if config.enabled:
            self._server_configs[config.name] = config
            print(f"📦 [MCP] Serveur enregistré : {config.name} ({config.command})")

    def register_mcp_server_from_dict(self, name: str, server_dict: Dict):
        """Enregistre depuis un dictionnaire de config (depuis config.yaml)."""
        config = MCPServerConfig(
            name=name,
            command=server_dict.get("command", ""),
            args=server_dict.get("args", []),
            env=server_dict.get("env"),
            enabled=server_dict.get("enabled", True),
        )
        self.register_mcp_server(config)

    # ------------------------------------------------------------------
    # Connexion aux serveurs MCP externes
    # ------------------------------------------------------------------

    async def connect_external_servers(self):
        """
        Tente de se connecter à tous les serveurs MCP enregistrés.
        Les erreurs sont gérées gracieusement : un serveur indisponible
        n'empêche pas le reste de fonctionner.
        """
        if not self._server_configs:
            return

        if not MCP_SDK_AVAILABLE:
            print(
                "⚠️ [MCP] SDK non disponible. Installez : pip install mcp\n"
                "   Les serveurs MCP externes seront ignorés.\n"
                "   Les outils locaux restent disponibles."
            )
            return

        tasks = []
        for name, config in self._server_configs.items():
            conn = _MCPServerConnection(config)
            self._server_connections[name] = conn
            tasks.append(conn.connect())

        results = await asyncio.gather(*tasks, return_exceptions=True)

        for name, result in zip(self._server_configs.keys(), results):
            if isinstance(result, Exception):
                print(f"⚠️ [MCP] Erreur connexion '{name}': {result}")
                continue
            if result:
                conn = self._server_connections[name]
                for tool in conn.tools:
                    original_name = tool.name.split("__", 1)[1]
                    self._external_tools[tool.name] = (name, original_name)

        total = len(self._local_tools) + len(self._external_tools)
        print(f"\n🎯 [MCP] Total outils disponibles : {total}")
        print(
            f"   • {len(self._local_tools)} outils locaux\n"
            f"   • {len(self._external_tools)} outils MCP externes"
        )
        self._connected = True

    def connect_external_servers_sync(self):
        """Wrapper synchrone pour connect_external_servers()."""
        try:
            asyncio.get_running_loop()
            # On est dans une boucle async — créer une tâche non bloquante
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                pool.submit(asyncio.run, self.connect_external_servers()).result(timeout=30)
        except RuntimeError:
            asyncio.run(self.connect_external_servers())

    # ------------------------------------------------------------------
    # Interface vers Ollama
    # ------------------------------------------------------------------

    def get_ollama_tools(self) -> List[Dict]:
        """
        Retourne tous les outils disponibles au format attendu par l'API
        Ollama (/api/chat avec le champ "tools").
        """
        tools = []
        for local_tool in self._local_tools.values():
            tools.append(local_tool.schema.to_ollama_format())
        for conn in self._server_connections.values():
            for tool_schema in conn.tools:
                tools.append(tool_schema.to_ollama_format())
        return tools

    def has_tools(self) -> bool:
        """Indique si au moins un outil (local ou externe) est disponible."""
        return bool(self._local_tools or self._external_tools)

    # ------------------------------------------------------------------
    # Exécution d'un outil
    # ------------------------------------------------------------------

    async def execute_tool_async(self, tool_name: str, arguments: Dict) -> str:
        """Exécute un outil (local ou externe) de manière asynchrone."""
        # 1. Outil local
        if tool_name in self._local_tools:
            fn = self._local_tools[tool_name].callable
            try:
                if asyncio.iscoroutinefunction(fn):
                    return await fn(**arguments)
                else:
                    # Exécuter la fonction sync dans un thread pour ne pas bloquer
                    loop = asyncio.get_event_loop()
                    return await loop.run_in_executor(None, lambda: fn(**arguments))
            except Exception as exc:
                return f"[Erreur outil '{tool_name}'] {exc}"

        # 2. Outil MCP externe
        if tool_name in self._external_tools:
            server_name, original_name = self._external_tools[tool_name]
            conn = self._server_connections.get(server_name)
            if conn:
                try:
                    return await conn.call_tool(original_name, arguments)
                except Exception as exc:
                    return f"[Erreur serveur MCP '{server_name}'] {exc}"

        return f"[Outil inconnu : {tool_name}]"

    def execute_tool_sync(self, tool_name: str, arguments: Dict) -> str:
        """Wrapper synchrone pour execute_tool_async()."""
        try:
            asyncio.get_running_loop()
            # Déjà dans une boucle — sous-thread
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                return pool.submit(
                    asyncio.run, self.execute_tool_async(tool_name, arguments)
                ).result(timeout=60)
        except RuntimeError:
            return asyncio.run(self.execute_tool_async(tool_name, arguments))

    # ------------------------------------------------------------------
    # Utilitaires
    # ------------------------------------------------------------------

    def get_tools_summary(self) -> str:
        """Résumé lisible de tous les outils disponibles."""
        lines = [f"🔧 Outils disponibles ({len(self.get_ollama_tools())} total) :"]
        if self._local_tools:
            lines.append("\n  📍 Outils locaux :")
            for name, tool in self._local_tools.items():
                desc = tool.schema.description[:70]
                lines.append(f"    • {name} — {desc}")
        for server_name, conn in self._server_connections.items():
            if conn.tools:
                lines.append(f"\n  📦 Serveur MCP '{server_name}' :")
                for tool in conn.tools:
                    original = tool.name.split("__", 1)[1]
                    lines.append(f"    • {original} — {tool.description[:70]}")
        return "\n".join(lines)

    async def disconnect_all(self):
        """Déconnecte tous les serveurs MCP."""
        await asyncio.gather(
            *[conn.disconnect() for conn in self._server_connections.values()],
            return_exceptions=True,
        )

    def __repr__(self):
        return (
            f"MCPManager("
            f"local={len(self._local_tools)}, "
            f"external={len(self._external_tools)}, "
            f"servers={list(self._server_connections.keys())})"
        )
