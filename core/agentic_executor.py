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
            "au workspace (ex: 'src/index.ts'). Le résultat affiche en tête "
            "'(lignes A-B sur N)' quand le fichier est plus grand que la "
            "fenêtre lue, et un pied de message indique l'offset à utiliser "
            "pour lire la suite. Quand l'utilisateur demande l'intégralité "
            "d'un fichier, RAPPELLE read_file en boucle avec offset croissant "
            "jusqu'à ne plus voir de pied 'Fichier tronqué'."
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
8. ANTI-BOUCLE : NE rappelle JAMAIS un outil avec exactement les mêmes \
arguments dans la même conversation. Si tu vois <tool_result> ou \
<tool_error> pour un appel donné, ce résultat reste valide pour TOUTE la \
conversation : utilise-le directement plutôt que de relancer l'outil.
9. Si <tool_error> indique qu'un fichier n'existe pas, NE retente PAS \
read_file ou glob avec le même nom : utilise list_dir pour découvrir le \
vrai nom du fichier ou demande à l'utilisateur.
10. Quand tous les outils nécessaires ont été appelés, ARRÊTE d'émettre \
des <tool_use> et donne ta réponse finale en texte normal.
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

# Repère une balise ouvrante `<tool_use>` non fermée (apparait pendant le
# streaming, avant que le LLM ait fini d'écrire le bloc). Sert à masquer
# les balises inachevées dans l'UI.
_PARTIAL_TOOL_USE_OPEN_RE = re.compile(r"<tool_use\b", re.IGNORECASE)


def strip_tool_use_for_display(text: str) -> str:
    """Retire les blocs `<tool_use>...</tool_use>` ET tout bloc ouvert sans
    fermeture (typiquement en cours d'écriture pendant le streaming).

    Sans ça, l'utilisateur voit du JSON brut s'afficher au moment où le
    modèle écrit ses appels d'outils, puis ce contenu disparaît : très
    confus côté UX.
    """
    cleaned = _TOOL_USE_RE.sub("", text)
    # Couper tout `<tool_use` non fermé encore présent après le sub().
    open_match = _PARTIAL_TOOL_USE_OPEN_RE.search(cleaned)
    if open_match is not None:
        cleaned = cleaned[: open_match.start()]
    return cleaned.strip()


def _safe_on_chunk(
    callback: Callable[..., None],
    text: str,
    segment_index: int,
) -> None:
    """Appelle ``callback(text, segment_index)`` ou retombe sur ``callback(text)``.

    Permet aux anciens callers (qui ne connaissent pas la notion de segment)
    de continuer à fonctionner sans modification, tout en passant l'info
    aux nouveaux callers qui rendent les segments séparément.
    """
    try:
        callback(text, segment_index)
        return
    except TypeError:
        # callback à 1 argument (ancien protocole)
        pass
    except Exception as exc:
        logger.debug("on_chunk a levé: %s", exc)
        return
    try:
        callback(text)
    except Exception as exc:
        logger.debug("on_chunk(legacy) a levé: %s", exc)


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


def _tool_signature(call: Dict[str, Any]) -> str:
    """Signature stable d'un appel d'outil, pour détecter les répétitions.

    Pour les outils qui ciblent un fichier/chemin, on regroupe par chemin : le
    *contenu* peut varier légèrement à chaque réécriture, mais réécrire 5 fois
    le même fichier reste une boucle. Sinon on prend l'entrée canonique complète.
    """
    name = call.get("name", "")
    inp = call.get("input", {}) or {}
    key = inp.get("path") or inp.get("pattern")
    if not key:
        try:
            key = json.dumps(inp, sort_keys=True, ensure_ascii=False)
        except (TypeError, ValueError):
            key = str(inp)
    return f"{name}:{key}"


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
    # Garde-fou anti-boucle : si le modèle répète la MÊME action (même outil
    # sur le même fichier/chemin), on le recadre à partir de LOOP_SOFT_LIMIT
    # répétitions, puis on coupe à LOOP_HARD_LIMIT (les modèles locaux faibles
    # réécrivent parfois le même fichier en boucle sans jamais conclure).
    LOOP_SOFT_LIMIT = 3
    LOOP_HARD_LIMIT = 5

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
        on_chunk: Callable[..., None],
        on_tool_call_announced: Callable[[Dict[str, Any]], None],
        on_tool_result: Callable[[str, Dict[str, Any]], None],
        workspace_info: str,
        max_iterations: Optional[int] = None,
    ) -> str:
        """Exécute la boucle agentique et retourne la réponse finale au format texte.

        - ``history`` est mutée en place (append-only) : la session VS Code
          réutilise la même liste pour conserver le contexte d'un message
          au suivant. La 1re entrée system_prompt est insérée si absente.
        - ``on_chunk(text, segment_index)`` : appelé pendant le streaming
          du LLM. Le texte est CELUI DE L'ITÉRATION COURANTE uniquement
          (pas cumulatif). Chaque itération a son propre ``segment_index``
          (0, 1, 2, ...), ce qui permet au client de rendre une bulle
          séparée par itération avec les cartes d'outils intercalées dans
          le bon ordre. La signature accepte ``segment_index`` en kwarg
          pour rester compatible avec les anciens callers à 1 arg.
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

        logger.info(
            "Boucle agentique : démarrage (model=%s, max_iter=%d, history=%d msgs)",
            self._model, max_iters, len(messages),
        )

        # Texte par segment : un segment = une passe LLM (entre deux
        # exécutions d'outils). Conservé pour reconstruire la réponse
        # finale envoyée via ``response`` à la fin.
        segments: List[str] = []

        # Compteur de signatures d'appels d'outils (garde-fou anti-boucle).
        signature_counts: Dict[str, int] = {}

        for iteration_index in range(max_iters):
            segment_index = iteration_index
            logger.info(
                "Boucle agentique : itération %d/%d (segment=%d)",
                iteration_index + 1, max_iters, segment_index,
            )
            assistant_text = await self._call_llm_streaming(
                messages,
                segment_index,
                on_chunk,
            )
            messages.append({"role": "assistant", "content": assistant_text})

            tool_calls = parse_tool_calls(assistant_text)
            visible_chunk = strip_tool_use_for_display(assistant_text)
            if visible_chunk:
                segments.append(visible_chunk)
                # Push final pour être sûr que le client a reçu la
                # version complète du segment avant les cartes d'outils.
                _safe_on_chunk(on_chunk, visible_chunk, segment_index)

            if not tool_calls:
                final_text = "\n\n".join(segments) if segments else assistant_text.strip()
                logger.info(
                    "Boucle agentique : fin (itération %d, %d segment(s), %d chars)",
                    iteration_index + 1, len(segments), len(final_text),
                )
                return final_text

            tool_names = ", ".join(c["name"] for c in tool_calls)
            logger.info(
                "Boucle agentique : itération %d → %d tool call(s) [%s]",
                iteration_index + 1, len(tool_calls), tool_names,
            )

            # Garde-fou anti-boucle : compter les signatures de cette itération.
            iteration_sigs = [_tool_signature(c) for c in tool_calls]
            for sig in iteration_sigs:
                signature_counts[sig] = signature_counts.get(sig, 0) + 1
            worst_sig = max(iteration_sigs, key=lambda s: signature_counts[s])
            worst_count = signature_counts[worst_sig]

            # Coupe nette : on stoppe AVANT de redispatcher l'action répétée
            # (évite une N-ième réécriture du même fichier).
            if worst_count >= self.LOOP_HARD_LIMIT:
                logger.warning(
                    "Boucle agentique : action répétée %d fois (%s) → arrêt anti-boucle",
                    worst_count, worst_sig,
                )
                final_text = "\n\n".join(segments) if segments else assistant_text.strip()
                return (
                    final_text
                    + "\n\n[⚠️ Arrêt automatique : la même action a été répétée "
                    f"{worst_count} fois (boucle détectée). La tâche est probablement "
                    "déjà faite — relance avec une consigne plus précise si besoin.]"
                ).strip()

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
            # Recadrage progressif : on prévient le modèle qu'il se répète,
            # pour l'inciter à conclure sans nouvel appel d'outil.
            if worst_count >= self.LOOP_SOFT_LIMIT:
                results_block += (
                    "\n\n[Système] Tu viens de répéter la même action plusieurs fois. "
                    "Si le fichier est déjà créé et la tâche terminée, réponds MAINTENANT "
                    "sans appel d'outil pour conclure. N'effectue pas à nouveau la même action."
                )
            messages.append({"role": "user", "content": results_block})

        logger.warning(
            "Boucle agentique : limite d'itérations atteinte (%d), arrêt forcé",
            max_iters,
        )
        truncated = "\n\n".join(segments) if segments else ""
        return (
            truncated
            + "\n\n[⚠️ Boucle agentique interrompue — limite d'itérations atteinte.]"
        ).strip()

    # ------------------------------------------------------------------
    # Appel LLM en streaming (Ollama /api/chat)
    # ------------------------------------------------------------------

    async def _call_llm_streaming(
        self,
        messages: List[Dict[str, str]],
        segment_index: int,
        on_chunk: Callable[..., None],
    ) -> str:
        """Appelle Ollama /api/chat en streaming, retourne le texte complet."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            self._sync_call_llm_streaming,
            messages,
            segment_index,
            on_chunk,
        )

    def _sync_call_llm_streaming(
        self,
        messages: List[Dict[str, str]],
        segment_index: int,
        on_chunk: Callable[..., None],
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
                        # On retire à la volée les blocs <tool_use> (et tout
                        # bloc ouvert sans fermeture) pour éviter d'afficher
                        # du JSON brut pendant que le modèle écrit le bloc.
                        visible = strip_tool_use_for_display(full_response)
                        _safe_on_chunk(on_chunk, visible, segment_index)
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
            call_name = call.get("name", "?")
            try:
                input_repr = json.dumps(call.get("input", {}), ensure_ascii=False)
            except (TypeError, ValueError):
                input_repr = str(call.get("input", {}))
            logger.info(
                "→ Tool call: %s(%s) [call_id=%s]",
                call_name,
                input_repr if len(input_repr) < 200 else input_repr[:200] + "…",
                call.get("call_id", "?"),
            )
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
                logger.exception("Erreur lors de l'exécution distante de %s", call_name)
                result = {"content": f"[Erreur exécution : {exc}]", "is_error": True}
            content_len = len(result.get("content", "")) if isinstance(result, dict) else 0
            logger.info(
                "← Tool result: %s [call_id=%s, is_error=%s, %d chars]",
                call_name,
                call.get("call_id", "?"),
                result.get("is_error", False) if isinstance(result, dict) else "?",
                content_len,
            )
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
    "strip_tool_use_for_display",
]
