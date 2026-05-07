"""
Boucle agentique pour le mode "VS Code" du Relay.

Ce module est utilisé EXCLUSIVEMENT quand un client Relay s'identifie comme
``client_kind == "vscode"``. Il n'a aucun impact sur le flux mobile/GUI :

- Le mode mobile continue d'utiliser ``RelayBridge.send_to_gui`` puis le
  pipeline complet de ``AIEngine.process_text`` (avec tous ses MCP locaux
  qui voient l'intégralité du PC hôte).
- Le mode "vscode" passe par cet exécuteur, qui appelle directement Ollama
  avec un set d'outils dont l'EXÉCUTION est délégué à l'extension VS Code
  (lecture/écriture de fichiers, recherche, exécution de commandes, ...).
  Le LLM reste sur l'hôte, mais ne voit rien d'autre que le workspace VS
  Code de l'utilisateur — sauf approbation explicite côté extension.

Le format d'invocation des outils est volontairement basé sur des balises
texte (``<tool_use>{"name": "...", "input": {...}}</tool_use>``) plutôt que
sur le tool-calling natif d'Ollama : ça marche avec n'importe quel modèle
(qwen3.5:2b/4b, llama, mistral, ...) sans dépendre du support de l'API
``tools`` côté serveur Ollama.
"""

from __future__ import annotations

import asyncio
import json
import re
import time
import uuid
from typing import Any, Awaitable, Callable, Dict, List, Optional

import requests

from utils.logger import setup_logger

logger = setup_logger("AgenticExecutor")


# ===========================================================================
# Schéma des outils exposés à l'agent
# ===========================================================================
#
# Le set est fixe et identique pour toutes les sessions VS Code. L'EXÉCUTION
# vit côté extension : ici on ne fait que décrire les outils au LLM via le
# prompt système, puis transmettre les appels à l'extension via le Relay.
# ---------------------------------------------------------------------------

AGENT_TOOLS: List[Dict[str, Any]] = [
    {
        "name": "read_file",
        "description": (
            "Lit un fichier du workspace VS Code. Le chemin doit être relatif "
            "au workspace (ex: 'src/index.ts'). Utiliser offset/limit pour "
            "paginer les gros fichiers (lignes 1-indexées)."
        ),
        "input_schema": {
            "path": "string (relatif au workspace)",
            "offset": "int optionnel (1er ligne à lire, défaut 1)",
            "limit": "int optionnel (nombre max de lignes, défaut 2000)",
        },
    },
    {
        "name": "write_file",
        "description": (
            "Crée ou remplace un fichier dans le workspace. L'utilisateur "
            "DOIT approuver l'opération côté VS Code avant exécution."
        ),
        "input_schema": {
            "path": "string (relatif au workspace)",
            "content": "string (contenu complet du fichier)",
        },
    },
    {
        "name": "edit_file",
        "description": (
            "Remplace une chaîne exacte par une autre dans un fichier "
            "existant. old_string DOIT être unique dans le fichier (ou "
            "passer replace_all=true). L'utilisateur DOIT approuver."
        ),
        "input_schema": {
            "path": "string (relatif au workspace)",
            "old_string": "string (à remplacer, exact match)",
            "new_string": "string (remplacement)",
            "replace_all": "bool optionnel (défaut false)",
        },
    },
    {
        "name": "list_dir",
        "description": (
            "Liste le contenu d'un dossier du workspace (fichiers + sous-"
            "dossiers, non récursif)."
        ),
        "input_schema": {
            "path": "string (relatif au workspace, défaut '.')",
        },
    },
    {
        "name": "glob",
        "description": (
            "Cherche des fichiers du workspace par pattern glob "
            "(ex: '**/*.ts', 'src/**/index.*')."
        ),
        "input_schema": {
            "pattern": "string (pattern glob)",
        },
    },
    {
        "name": "grep",
        "description": (
            "Recherche une regex dans le contenu des fichiers du workspace "
            "(ripgrep). Retourne les fichiers qui matchent (output_mode="
            "'files') ou les lignes (output_mode='content')."
        ),
        "input_schema": {
            "pattern": "string (regex)",
            "path": "string optionnel (sous-dossier, défaut workspace)",
            "glob": "string optionnel (filtre glob: '*.py', '**/*.ts')",
            "output_mode": "'files' | 'content' (défaut 'files')",
            "case_insensitive": "bool optionnel (défaut false)",
        },
    },
    {
        "name": "run_command",
        "description": (
            "Exécute une commande shell dans le workspace (terminal VS Code). "
            "L'utilisateur DOIT approuver. Retourne stdout/stderr/exit_code."
        ),
        "input_schema": {
            "command": "string (commande shell)",
            "cwd": "string optionnel (sous-dossier, défaut workspace root)",
            "timeout_seconds": "int optionnel (défaut 60)",
        },
    },
    {
        "name": "get_active_editor",
        "description": (
            "Retourne le fichier actuellement ouvert dans VS Code, le contenu "
            "et la sélection de l'utilisateur si applicable."
        ),
        "input_schema": {},
    },
    {
        "name": "open_file",
        "description": (
            "Ouvre un fichier du workspace dans l'éditeur VS Code (utile "
            "pour montrer le résultat à l'utilisateur)."
        ),
        "input_schema": {
            "path": "string (relatif au workspace)",
            "line": "int optionnel (ligne à révéler)",
        },
    },
]


# ===========================================================================
# Prompt système
# ===========================================================================


def _format_tools_for_prompt(tools: List[Dict[str, Any]]) -> str:
    lines: List[str] = []
    for tool in tools:
        lines.append(f"### {tool['name']}")
        lines.append(tool["description"])
        schema = tool.get("input_schema", {})
        if schema:
            lines.append("Input:")
            for key, kind in schema.items():
                lines.append(f"  - {key}: {kind}")
        else:
            lines.append("Input: (aucun)")
        lines.append("")
    return "\n".join(lines).strip()


_SYSTEM_PROMPT_TEMPLATE = """\
Tu es My_AI, un assistant de développement intégré à VS Code via une extension.
Tu fonctionnes exactement comme Claude Code : tu peux lire, modifier, créer \
des fichiers, lancer des commandes shell et chercher du contenu dans le \
workspace de l'utilisateur. Tu N'AS PAS accès aux fichiers en dehors du \
workspace VS Code, sauf si l'utilisateur l'autorise explicitement.

# Workspace
{workspace_info}

# Outils disponibles

{tools_doc}

# Comment utiliser un outil

Quand tu veux utiliser un outil, écris EXACTEMENT ce format dans ta réponse :

<tool_use>
{{"name": "<nom_outil>", "input": {{<arguments JSON>}}}}
</tool_use>

Tu peux invoquer plusieurs outils en parallèle dans une même réponse en \
mettant plusieurs blocs <tool_use>...</tool_use> à la suite.

Une fois que tu as émis un ou plusieurs blocs <tool_use>, ARRÊTE-TOI \
immédiatement. Le système exécutera les outils et te renverra les \
résultats (sous forme <tool_result call_id="...">...</tool_result>) dans \
un message suivant. Tu pourras alors continuer ton raisonnement et \
émettre d'autres tool_use ou donner la réponse finale.

# Règles

1. Avant de modifier un fichier que tu n'as pas lu, LIS-LE d'abord avec \
read_file pour ne rien casser.
2. Pour chercher du code, préfère grep (recherche dans le contenu) à glob \
(recherche par nom de fichier).
3. Quand tu écris/modifies du code : pas de TODO, pas de placeholders, \
pas de fonctions stub. Le code doit être complet et fonctionnel.
4. N'ajoute pas de commentaires inutiles. Ne raconte pas ce que fait le \
code dans des commentaires si les noms de variables/fonctions le disent \
déjà.
5. Pour lancer une commande shell, utilise run_command. L'utilisateur \
sera prévenu et devra confirmer.
6. Quand tu réponds en finale (sans tool_use), sois concis. L'utilisateur \
voit déjà tout ce que tu as fait via les outils — pas besoin de tout \
résumer.
7. Réponds dans la langue de l'utilisateur (français par défaut).
"""


def build_system_prompt(workspace_info: str, tools: Optional[List[Dict[str, Any]]] = None) -> str:
    """Construit le prompt système complet à partir des infos de workspace et du set d'outils."""
    if tools is None:
        tools = AGENT_TOOLS
    return _SYSTEM_PROMPT_TEMPLATE.format(
        workspace_info=workspace_info or "(workspace inconnu)",
        tools_doc=_format_tools_for_prompt(tools),
    )


# ===========================================================================
# Parsing des appels d'outils
# ===========================================================================

_TOOL_USE_RE = re.compile(
    r"<tool_use>\s*(?P<body>.+?)\s*</tool_use>",
    re.DOTALL | re.IGNORECASE,
)


def parse_tool_calls(assistant_text: str) -> List[Dict[str, Any]]:
    """Extrait les blocs <tool_use>...</tool_use> du texte du modèle.

    Tolère le JSON malformé : on logge et on ignore le bloc invalide. Le
    LLM verra son tool_use rester sans réponse → il pourra réessayer.
    """
    calls: List[Dict[str, Any]] = []
    for match in _TOOL_USE_RE.finditer(assistant_text):
        body = match.group("body").strip()
        body = _strip_code_fence(body)
        try:
            data = json.loads(body)
        except json.JSONDecodeError as exc:
            logger.warning(
                "Bloc <tool_use> ignoré (JSON invalide: %s) : %r", exc, body[:120]
            )
            continue
        if not isinstance(data, dict):
            continue
        name = data.get("name")
        if not isinstance(name, str) or not name:
            continue
        input_data = data.get("input", {})
        if not isinstance(input_data, dict):
            input_data = {}
        calls.append({
            "call_id": uuid.uuid4().hex,
            "name": name,
            "input": input_data,
        })
    return calls


def _strip_code_fence(text: str) -> str:
    """Retire un éventuel fence ```json ... ``` autour du JSON."""
    stripped = text.strip()
    if stripped.startswith("```"):
        # Couper la première ligne (```json ou ```)
        first_nl = stripped.find("\n")
        if first_nl >= 0:
            stripped = stripped[first_nl + 1 :]
        if stripped.endswith("```"):
            stripped = stripped[:-3]
    return stripped.strip()


# ===========================================================================
# Pont d'exécution distant (Relay → Extension VS Code)
# ===========================================================================


class RemoteToolExecutor:
    """Envoie un appel d'outil à l'extension via le Relay et attend la réponse.

    L'instance est créée par le serveur Relay pour la durée d'UNE requête
    utilisateur. Elle utilise un dict partagé ``pending_calls`` pour
    associer chaque ``call_id`` à une ``asyncio.Future`` ; le handler WS
    ``tool_result`` résout la future quand l'extension répond.
    """

    def __init__(
        self,
        send_fn: Callable[[Dict[str, Any]], Awaitable[None]],
        pending_calls: Dict[str, "asyncio.Future[Any]"],
        message_id: str,
        loop: asyncio.AbstractEventLoop,
        default_timeout: float = 120.0,
    ) -> None:
        self._send = send_fn
        self._pending = pending_calls
        self._message_id = message_id
        self._loop = loop
        self._default_timeout = default_timeout

    async def call(
        self,
        call_id: str,
        name: str,
        input_data: Dict[str, Any],
        timeout: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Envoie ``tool_use`` et attend ``tool_result`` correspondant.

        Retourne ``{"content": str, "is_error": bool, ...}``.
        Lève ``asyncio.TimeoutError`` si l'extension ne répond pas à temps,
        ou propage l'exception côté extension via ``is_error=True``.
        """
        fut: "asyncio.Future[Dict[str, Any]]" = self._loop.create_future()
        self._pending[call_id] = fut
        try:
            await self._send({
                "type": "tool_use",
                "call_id": call_id,
                "name": name,
                "input": input_data,
                "message_id": self._message_id,
            })
            return await asyncio.wait_for(fut, timeout=timeout or self._default_timeout)
        finally:
            self._pending.pop(call_id, None)


# ===========================================================================
# Boucle agentique
# ===========================================================================


class AgenticExecutor:
    """Boucle "LLM ↔ outils" pour le mode VS Code.

    L'exécuteur appelle directement l'API Ollama ``/api/chat`` avec le
    système de messages complet, sans passer par ``LocalLLM`` ni
    ``AIEngine.process_text`` (qui ont des side-effects sur l'historique
    de conversation utilisé par le GUI).
    """

    MAX_ITERATIONS = 25
    # Durée max d'une réponse LLM individuelle (avant timeout HTTP)
    LLM_TIMEOUT_SECONDS = 600

    def __init__(
        self,
        ollama_chat_url: str,
        model: str,
        num_ctx: int = 32768,
        num_predict: int = 8192,
        temperature: float = 0.4,
    ) -> None:
        self._chat_url = ollama_chat_url
        self._model = model
        self._num_ctx = num_ctx
        self._num_predict = num_predict
        self._temperature = temperature

    async def run(
        self,
        user_message: str,
        history: List[Dict[str, str]],
        tool_executor: RemoteToolExecutor,
        on_chunk: Callable[[str], None],
        on_tool_call_announced: Callable[[Dict[str, Any]], None],
        on_tool_result: Callable[[str, Dict[str, Any]], None],
        workspace_info: str,
        max_iterations: Optional[int] = None,
    ) -> str:
        """Exécute la boucle agentique et retourne la réponse finale au format texte.

        - ``history`` est mutée en place (append-only) : la session VS Code
          réutilise la même liste pour conserver le contexte d'un message
          au suivant. La 1re entrée system_prompt est insérée si absente.
        - ``on_chunk(text_partial_cumulatif)`` : appelé pendant le streaming
          du LLM (pour broadcast au webview chat). Le texte est cumulatif.
        - ``on_tool_call_announced(call)`` : appelé juste avant qu'un appel
          d'outil parte au client (pour afficher la carte "tool_use" dans
          l'UI).
        - ``on_tool_result(call_id, result)`` : appelé à la réception du
          résultat d'un outil.
        """
        max_iters = max_iterations or self.MAX_ITERATIONS

        if not history or history[0].get("role") != "system":
            history.insert(0, {
                "role": "system",
                "content": build_system_prompt(workspace_info),
            })
        history.append({"role": "user", "content": user_message})
        messages = history

        # Texte cumulatif visible par l'utilisateur (concaténation des
        # passes successives du LLM, mais SANS les blocs <tool_use> qui
        # sont déjà rendus comme cartes UI).
        visible_so_far = ""

        for iteration in range(max_iters):
            assistant_text = await self._call_llm_streaming(
                messages,
                visible_so_far,
                on_chunk,
            )
            messages.append({"role": "assistant", "content": assistant_text})

            tool_calls = parse_tool_calls(assistant_text)

            # Mettre à jour le texte visible : on retire les blocs tool_use
            # de l'affichage (ils seront rendus comme cartes), mais on
            # garde le reste du texte (raisonnement libre du modèle).
            visible_chunk = _TOOL_USE_RE.sub("", assistant_text).strip()
            if visible_chunk:
                if visible_so_far:
                    visible_so_far = visible_so_far + "\n\n" + visible_chunk
                else:
                    visible_so_far = visible_chunk
                # Pousser une mise à jour finale du chunk visible
                on_chunk(visible_so_far)

            if not tool_calls:
                # Le modèle a fini : pas de tool_use, on retourne la
                # réponse visible cumulée.
                return visible_so_far or assistant_text.strip()

            # Exécuter les tool_calls (en parallèle pour aller vite).
            results = await self._dispatch_tool_calls(
                tool_calls,
                tool_executor,
                on_tool_call_announced,
                on_tool_result,
            )

            # Réinjecter les résultats au modèle dans un nouveau message
            # utilisateur (style "tool" non standard — on utilise role:user
            # pour rester compatible avec tous les modèles, même ceux qui
            # n'ont pas le rôle "tool").
            results_block = self._format_tool_results(tool_calls, results)
            messages.append({"role": "user", "content": results_block})

        return (
            visible_so_far
            + "\n\n[⚠️ Boucle agentique interrompue — limite d'itérations atteinte.]"
        ).strip()

    # ------------------------------------------------------------------
    # Appel LLM en streaming (Ollama /api/chat)
    # ------------------------------------------------------------------

    async def _call_llm_streaming(
        self,
        messages: List[Dict[str, str]],
        visible_prefix: str,
        on_chunk: Callable[[str], None],
    ) -> str:
        """Appelle Ollama /api/chat en streaming, retourne le texte complet."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            self._sync_call_llm_streaming,
            messages,
            visible_prefix,
            on_chunk,
        )

    def _sync_call_llm_streaming(
        self,
        messages: List[Dict[str, str]],
        visible_prefix: str,
        on_chunk: Callable[[str], None],
    ) -> str:
        data = {
            "model": self._model,
            "messages": messages,
            "stream": True,
            "keep_alive": "1h",
            "options": {
                "temperature": self._temperature,
                "num_ctx": self._num_ctx,
                "num_predict": self._num_predict,
                "num_keep": -1,
            },
        }

        full_response = ""
        last_chunk_pushed_at = 0.0

        try:
            with requests.post(
                self._chat_url,
                json=data,
                timeout=self.LLM_TIMEOUT_SECONDS,
                stream=True,
            ) as resp:
                if resp.status_code != 200:
                    err = f"[Erreur LLM HTTP {resp.status_code}]"
                    logger.error("Ollama HTTP %d: %s", resp.status_code, resp.text[:200])
                    return err
                for raw_line in resp.iter_lines():
                    if not raw_line:
                        continue
                    try:
                        chunk = json.loads(raw_line)
                    except json.JSONDecodeError:
                        continue
                    msg = chunk.get("message", {})
                    token = msg.get("content", "")
                    if not token:
                        continue
                    full_response += token

                    # Throttle des chunks vers l'UI : 50ms.
                    now = time.time()
                    if now - last_chunk_pushed_at >= 0.05:
                        last_chunk_pushed_at = now
                        # Le texte visible est : préfixe + (nouvelle réponse
                        # avec les tool_use retirés). On retire à la volée
                        # pour éviter d'afficher du JSON brut pendant que le
                        # modèle écrit le bloc.
                        visible = _TOOL_USE_RE.sub("", full_response).strip()
                        if visible_prefix and visible:
                            visible = visible_prefix + "\n\n" + visible
                        elif visible_prefix:
                            visible = visible_prefix
                        try:
                            on_chunk(visible)
                        except Exception as exc:
                            logger.debug("on_chunk a levé: %s", exc)
        except requests.RequestException as exc:
            logger.error("Erreur appel Ollama : %s", exc)
            return f"[Erreur LLM : {exc}]"
        return full_response

    # ------------------------------------------------------------------
    # Dispatch des tool calls vers l'extension
    # ------------------------------------------------------------------

    async def _dispatch_tool_calls(
        self,
        calls: List[Dict[str, Any]],
        executor: RemoteToolExecutor,
        on_announced: Callable[[Dict[str, Any]], None],
        on_result: Callable[[str, Dict[str, Any]], None],
    ) -> List[Dict[str, Any]]:
        async def _one(call: Dict[str, Any]) -> Dict[str, Any]:
            try:
                on_announced(call)
            except Exception as exc:
                logger.debug("on_announced a levé: %s", exc)
            try:
                result = await executor.call(
                    call_id=call["call_id"],
                    name=call["name"],
                    input_data=call["input"],
                )
            except asyncio.TimeoutError:
                result = {
                    "content": "[Timeout : aucune réponse de l'extension VS Code "
                    "dans le délai imparti.]",
                    "is_error": True,
                }
            except Exception as exc:
                logger.exception("Erreur lors de l'exécution distante de %s", call.get("name"))
                result = {"content": f"[Erreur exécution : {exc}]", "is_error": True}
            try:
                on_result(call["call_id"], result)
            except Exception as exc:
                logger.debug("on_result a levé: %s", exc)
            return result

        return await asyncio.gather(*(_one(c) for c in calls))

    # ------------------------------------------------------------------
    # Formattage des résultats à réinjecter dans le contexte du LLM
    # ------------------------------------------------------------------

    @staticmethod
    def _format_tool_results(
        calls: List[Dict[str, Any]],
        results: List[Dict[str, Any]],
    ) -> str:
        chunks: List[str] = []
        for call, result in zip(calls, results):
            content = result.get("content", "")
            if not isinstance(content, str):
                try:
                    content = json.dumps(content, ensure_ascii=False)
                except Exception:
                    content = str(content)
            tag = "tool_error" if result.get("is_error") else "tool_result"
            chunks.append(
                f'<{tag} call_id="{call["call_id"]}" name="{call["name"]}">\n'
                f"{content}\n"
                f"</{tag}>"
            )
        return "\n\n".join(chunks)


__all__ = [
    "AGENT_TOOLS",
    "AgenticExecutor",
    "RemoteToolExecutor",
    "build_system_prompt",
    "parse_tool_calls",
]
