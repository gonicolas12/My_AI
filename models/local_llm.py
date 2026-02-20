"""
Module de gestion des LLM locaux avec priorité à Ollama.
Support de l'historique de conversation pour un contexte persistant.
"""

import json
import re
from typing import Callable, Dict, List, Optional

import requests


class LocalLLM:
    """
    Gestionnaire intelligent de LLM Local avec mémoire de conversation.
    Tente d'utiliser Ollama en priorité, sinon gère le fallback.
    """

    def __init__(
        self,
        model="my_ai",
        ollama_url="http://localhost:11434/api/generate",
        timeout=600,
    ):
        # On essaie d'abord le modèle personnalisé 'my_ai', sinon fallback sur 'llama3'
        self.model = model
        self.ollama_url = ollama_url
        self.chat_url = ollama_url.replace("/api/generate", "/api/chat")
        self.timeout = timeout  # Timeout configurable
        self.is_ollama_available = self._check_ollama_availability()

        # 🧠 Historique de conversation pour le contexte
        self.conversation_history: List[Dict[str, str]] = []
        self.max_history_length = 200  # Garder les 200 derniers échanges
        self._streamed_already = False  # Flag pour tracking du streaming vision

        # 📝 Résumé glissant : résumé compressé des anciens messages
        self._conversation_summary: str = ""
        # Seuil en tokens estimés avant déclenchement du résumé (laisser ~8k pour réponse+prompt)
        self._summary_threshold_tokens: int = 24000
        # Taille cible après résumé (en nombre de messages à conserver "vivants")
        self._keep_recent_messages: int = 20

        if self.is_ollama_available:
            # Vérifier si le modèle personnalisé existe, sinon utiliser llama3
            if not self._check_model_exists(model):
                print(
                    f"⚠️ [LocalLLM] Modèle '{model}' non trouvé. Fallback sur 'llama3'."
                )
                self.model = "llama3"

            print(
                f"✅ [LocalLLM] Ollama détecté et actif sur {self.ollama_url} (Modèle: {self.model})"
            )
            print(
                f"   ℹ️  Timeout configuré: {self.timeout}s (la première requête peut être lente)"
            )
            print(
                f"   🧠 Mémoire de conversation activée (max {self.max_history_length} échanges)"
            )
        else:
            print(
                "⚠️ [LocalLLM] Ollama non détecté. Le mode génératif avancé sera désactivé."
            )

    def _check_model_exists(self, model_name):
        """Vérifie si le modèle existe dans Ollama"""
        try:
            response = requests.get(
                self.ollama_url.replace("/api/generate", "/api/tags"), timeout=2
            )
            if response.status_code == 200:
                models = [m["name"] for m in response.json().get("models", [])]
                # Vérifie si le modèle est dans la liste (avec ou sans tag :latest)
                return any(model_name in m for m in models)
            return False
        except Exception:
            return False

    def _check_ollama_availability(self):
        """Vérifie si le serveur Ollama répond"""
        try:
            # On tente juste un ping rapide (GET sur la racine ou une API légère)
            response = requests.get(
                self.ollama_url.replace("/api/generate", ""), timeout=2
            )
            return response.status_code == 200
        except Exception:
            return False

    def generate(self, prompt, system_prompt=None, save_history=True, use_history=True):
        """
        Génère une réponse avec contexte de conversation.
        Utilise l'API /api/chat pour maintenir l'historique.
        Retourne None si Ollama n'est pas disponible (pour déclencher le fallback).
        """
        if not self.is_ollama_available:
            return None

        # Construire les messages avec historique
        messages = []

        # Ajouter le system prompt s'il existe
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        # Ajouter l'historique de conversation
        if use_history:
            messages.extend(self.conversation_history)

        # Ajouter le message actuel de l'utilisateur
        messages.append({"role": "user", "content": prompt})

        data = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": 0.7,
                "num_ctx": 32768,
                "num_predict": 2048,
            },
        }

        try:
            print(
                f"⏳ [LocalLLM] Génération avec contexte ({len(self.conversation_history) if use_history else 0} messages précédents)..."
            )
            response = requests.post(self.chat_url, json=data, timeout=self.timeout)
            if response.status_code == 200:
                result = response.json()
                assistant_response = result.get("message", {}).get("content", "")

                if assistant_response and save_history:
                    # Sauvegarder dans l'historique
                    self.add_to_history("user", prompt)
                    self.add_to_history("assistant", assistant_response)
                    print("✅ [LocalLLM] Réponse générée et ajoutée à l'historique")

                return assistant_response
            else:
                print(f"⚠️ [LocalLLM] Erreur API Ollama: {response.status_code}")
                return None
        except requests.exceptions.Timeout:
            print(
                f"⚠️ [LocalLLM] Timeout après {self.timeout}s - Le modèle est trop lent."
            )
            print(
                "   💡 Conseil: Essayez un modèle plus léger ou augmentez le timeout."
            )
            return None
        except Exception as e:
            print(f"⚠️ [LocalLLM] Exception durant la génération: {e}")
            return None

    def generate_stream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        on_token: Optional[Callable] = None,
        is_interrupted_callback: Optional[Callable] = None,
    ) -> str:
        """
        Génère une réponse en streaming réel depuis Ollama.
        Appelle on_token(chunk) pour chaque morceau reçu.
        Retourne la réponse complète.
        """
        if not self.is_ollama_available:
            return ""

        messages: List[Dict] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.extend(self.conversation_history)
        messages.append({"role": "user", "content": prompt})

        data = {
            "model": self.model,
            "messages": messages,
            "stream": True,
            "options": {"temperature": 0.7, "num_ctx": 32768, "num_predict": 4096},
        }

        full_response = ""
        try:
            with requests.post(
                self.chat_url, json=data, timeout=self.timeout, stream=True
            ) as resp:
                if resp.status_code != 200:
                    print(f"⚠️ [LocalLLM] generate_stream HTTP {resp.status_code}")
                    return ""
                for raw_line in resp.iter_lines():
                    if is_interrupted_callback and is_interrupted_callback():
                        break
                    if not raw_line:
                        continue
                    try:
                        chunk = json.loads(raw_line)
                    except json.JSONDecodeError:
                        continue
                    token = chunk.get("message", {}).get("content", "")
                    if token:
                        full_response += token
                        if on_token:
                            result = on_token(token)
                            if result is False:
                                break
                    if chunk.get("done"):
                        break
        except Exception as exc:
            print(f"⚠️ [LocalLLM] generate_stream exception: {exc}")

        if full_response:
            self.add_to_history("user", prompt)
            self.add_to_history("assistant", full_response)
        return full_response

    def generate_with_tools(
        self,
        prompt: str,
        tools: List[Dict],
        tool_executor: Callable,
        system_prompt: Optional[str] = None,
        on_token: Optional[Callable] = None,
        max_tool_iterations: int = 10,
    ) -> Dict:
        """
        Boucle agentique : Ollama choisit et appelle des outils, puis génère
        la réponse finale après avoir reçu tous les résultats.

        Flux :
          1. Envoi message + liste d'outils → Ollama
          2. Si Ollama retourne des tool_calls → exécution via tool_executor
          3. Résultats ajoutés en messages "tool" → retour étape 1
          4. Quand Ollama retourne une réponse texte → fin

        Args:
            prompt:             Message utilisateur
            tools:              Liste d'outils au format Ollama
            tool_executor:      Callable(tool_name: str, arguments: dict) → str
                                (peut être MCPManager.execute_tool_sync)
            system_prompt:      Prompt système optionnel
            on_token:           Callback de streaming pour la réponse finale
            max_tool_iterations: Garde-fou contre les boucles infinies

        Returns:
            Dict {
                "response":    str  — réponse finale de l'IA
                "tool_calls":  list — journal des appels effectués
                "success":     bool
            }
        """
        if not self.is_ollama_available:
            return {"response": None, "tool_calls": [], "success": False}

        # Construction du contexte initial
        messages: List[Dict] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.extend(self.conversation_history)
        messages.append({"role": "user", "content": prompt})

        tool_calls_log: List[Dict] = []

        for _ in range(max_tool_iterations):
            # ----------------------------------------------------------------
            # Appel Ollama avec la liste d'outils
            # ----------------------------------------------------------------
            data = {
                "model": self.model,
                "messages": messages,
                "tools": tools,
                "stream": False,
                "options": {
                    "temperature": 0.7,
                    "num_ctx": 32768,
                    "num_predict": 4096,
                },
            }

            try:
                response = requests.post(
                    self.chat_url, json=data, timeout=self.timeout
                )
                if response.status_code != 200:
                    print(
                        f"⚠️ [LocalLLM] Erreur tool-calling: {response.status_code}"
                    )
                    break

                result = response.json()
                message = result.get("message", {})

            except Exception as exc:
                print(f"⚠️ [LocalLLM] Exception tool-calling: {exc}")
                break

            # ----------------------------------------------------------------
            # Pas de tool calls → réponse finale
            # ----------------------------------------------------------------
            if not message.get("tool_calls"):
                final_text = message.get("content", "")
                if final_text:
                    # Streaming simulé si callback fourni
                    if on_token:
                        on_token(final_text)
                    self.add_to_history("user", prompt)
                    self.add_to_history("assistant", final_text)
                    print(
                        f"✅ [LocalLLM] Réponse agentique ({len(tool_calls_log)} "
                        f"appels d'outils effectués)"
                    )
                return {
                    "response": final_text,
                    "tool_calls": tool_calls_log,
                    "success": bool(final_text),
                }

            # ----------------------------------------------------------------
            # Tool calls → exécution + réinjection dans le contexte
            # ----------------------------------------------------------------
            # Ajouter la réponse partielle de l'assistant au contexte
            messages.append(message)

            for tool_call in message.get("tool_calls", []):
                func = tool_call.get("function", {})
                tool_name = func.get("name", "")
                arguments = func.get("arguments", {})

                # Nettoyage des arguments si le modèle a halluciné le schéma
                cleaned_args = {}
                for k, v in arguments.items():
                    if isinstance(v, dict) and "type" in v and "description" in v:
                        if "description" in v and v["description"] != "La requête de recherche":
                            cleaned_args[k] = v["description"]
                        else:
                            continue
                    else:
                        cleaned_args[k] = v
                arguments = cleaned_args

                print(
                    f"🔧 [LocalLLM] Tool call: {tool_name}({json.dumps(arguments)[:80]})"
                )

                # Exécution de l'outil
                try:
                    tool_result = tool_executor(tool_name, arguments)
                except Exception as exc:
                    tool_result = f"[Erreur lors de l'exécution de {tool_name}]: {exc}"

                tool_calls_log.append({
                    "tool": tool_name,
                    "arguments": arguments,
                    "result_preview": str(tool_result)[:200],
                })

                print(f"   ↳ Résultat : {str(tool_result)[:100]}...")

                # Réinjecter le résultat dans le contexte
                messages.append({
                    "role": "tool",
                    "content": str(tool_result),
                })

        # Garde-fou : max iterations atteint
        print(
            f"⚠️ [LocalLLM] max_tool_iterations ({max_tool_iterations}) atteint"
        )
        return {"response": None, "tool_calls": tool_calls_log, "success": False}

    # ------------------------------------------------------------------
    # Détection des "text tool calls" (llama3.2 bug workaround)
    # ------------------------------------------------------------------

    @staticmethod
    def parse_text_tool_call(
        text: str, known_tool_names: List[str]
    ) -> Optional[Dict]:
        """
        Certains modèles (llama3.2, mistral) écrivent le tool call sous forme de
        texte JSON au lieu d'utiliser le champ `tool_calls` de l'API.

        Exemples détectés :
          {"name": "web_search", "parameters": {"query": "..."}}
          {"name": "web_search", "arguments": {"query": "..."}}
          [{"name": "web_search", "parameters": {"query": "..."}}]

        Retourne {"name": str, "arguments": dict} ou None.
        """
        text = text.strip()
        if not text.startswith(("{", "[")):
            return None
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            # Essayer d'extraire un bloc JSON embarqué
            m = re.search(r'\{[^{}]*"name"\s*:[^{}]*\}', text, re.DOTALL)
            if not m:
                return None
            try:
                data = json.loads(m.group(0))
            except json.JSONDecodeError:
                return None

        # Supporter la forme liste [{"name": ...}]
        if isinstance(data, list) and data:
            data = data[0]

        if not isinstance(data, dict):
            return None

        name = data.get("name") or data.get("tool") or data.get("function")
        if not name or name not in known_tool_names:
            return None

        # "parameters" ou "arguments"
        args = data.get("arguments") or data.get("parameters") or data.get("input") or {}
        if not isinstance(args, dict):
            args = {}

        # Parfois le modèle imbrique les arguments dans un sous-dictionnaire
        # ex: {"query": {"type": "string", "description": "..."}} au lieu de {"query": "..."}
        # On essaie de nettoyer ça si on détecte un schéma JSON au lieu d'une valeur
        cleaned_args = {}
        for k, v in args.items():
            if isinstance(v, dict) and "type" in v and "description" in v:
                # Le modèle a recopié le schéma au lieu de donner une valeur !
                # On essaie de récupérer la valeur si elle est dans la description
                # (souvent le modèle met la valeur dans la description par erreur)
                if "description" in v and v["description"] != "La requête de recherche":
                    cleaned_args[k] = v["description"]
                else:
                    continue
            else:
                cleaned_args[k] = v

        return {"name": name, "arguments": cleaned_args}

    def generate_with_tools_stream(
        self,
        prompt: str,
        tools: List[Dict],
        tool_executor: Callable,
        system_prompt: Optional[str] = None,
        on_token: Optional[Callable] = None,
        on_tool_call: Optional[Callable] = None,
        is_interrupted_callback: Optional[Callable] = None,
        max_tool_iterations: int = 10,
    ) -> Dict:
        """
        Version streaming de generate_with_tools.
        - Les appels d'outils sont non-streamés (nécessaire pour l'API Ollama)
        - La réponse finale est streamée token par token via on_token
        - Gère le fallback "text tool call" (llama3.2 écrit le JSON au lieu de
          remplir le champ tool_calls)

        Args:
            on_tool_call: Callback(tool_name, args) appelé avant chaque exécution
                          (pour afficher "Je recherche..." dans l'UI)
        """
        if not self.is_ollama_available:
            return {"response": None, "tool_calls": [], "success": False}

        # Noms des outils disponibles (pour détecter les text tool calls)
        known_tool_names: List[str] = [
            t.get("function", {}).get("name", "")
            for t in tools
            if isinstance(t, dict)
        ]

        messages: List[Dict] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.extend(self.conversation_history)
        messages.append({"role": "user", "content": prompt})

        tool_calls_log: List[Dict] = []

        for iteration in range(max_tool_iterations):
            if is_interrupted_callback and is_interrupted_callback():
                break

            # Après au moins un appel d'outil, ne plus passer les outils à Ollama
            # pour l'étape de synthèse. Sans outils disponibles, le modèle est
            # forcé de synthétiser depuis les résultats déjà injectés.
            tools_for_this_call = [] if tool_calls_log else tools

            # Lors de la synthèse, remplacer le message système pour éviter que
            # le modèle réponde « je n'ai pas accès aux données en temps réel »
            # malgré les résultats déjà injectés.
            if tool_calls_log and messages and messages[0].get("role") == "system":
                messages[0] = {
                    "role": "system",
                    "content": (
                        "Les informations demandées ont été récupérées en temps réel "
                        "via des outils externes. Tu DOIS utiliser UNIQUEMENT ces données "
                        "pour répondre à la question. "
                        "Ne dis JAMAIS que tu n'as pas accès aux données en temps réel "
                        "car tu viens de les recevoir. "
                        "Réponds de façon précise, factuelle et concise en te basant "
                        "sur les résultats fournis par les outils."
                    ),
                }

            data_no_stream = {
                "model": self.model,
                "messages": messages,
                "tools": tools_for_this_call,
                "stream": False,
                "options": {"temperature": 0.7, "num_ctx": 32768, "num_predict": 4096},
            }

            try:
                response = requests.post(
                    self.chat_url, json=data_no_stream, timeout=self.timeout
                )
                if response.status_code != 200:
                    print(f"⚠️ [LocalLLM] HTTP {response.status_code} à iter {iteration}")
                    break
                result = response.json()
                message = result.get("message", {})
            except Exception as exc:
                print(f"⚠️ [LocalLLM] Exception tool-stream: {exc}")
                break

            # ----------------------------------------------------------------
            # Cas 1 : tool_calls natif (API Ollama)
            # ----------------------------------------------------------------
            if message.get("tool_calls"):
                messages.append(message)
                for tool_call in message["tool_calls"]:
                    func = tool_call.get("function", {})
                    tool_name = func.get("name", "")
                    arguments = func.get("arguments", {})

                    # Nettoyage des arguments si le modèle a halluciné le schéma
                    cleaned_args = {}
                    for k, v in arguments.items():
                        if isinstance(v, dict) and "type" in v and "description" in v:
                            if "description" in v and v["description"] != "La requête de recherche":
                                cleaned_args[k] = v["description"]
                            else:
                                continue
                        else:
                            cleaned_args[k] = v
                    arguments = cleaned_args

                    # NE PAS appeler on_tool_call ici : tool_executor (ai_engine.py)
                    # le fait après optimisation de la requête, évitant le double affichage.
                    print(f"🔧 [LocalLLM] Stream tool call: {tool_name}")
                    try:
                        tool_result = tool_executor(tool_name, arguments)
                    except Exception as exc:
                        tool_result = f"[Erreur {tool_name}]: {exc}"

                    tool_calls_log.append({
                        "tool": tool_name,
                        "arguments": arguments,
                        "result_preview": str(tool_result)[:200],
                    })
                    messages.append({"role": "tool", "content": str(tool_result)})
                # Message de relance explicite pour forcer la synthèse
                messages.append({
                    "role": "user",
                    "content": (
                        f"En utilisant UNIQUEMENT les informations ci-dessus retournées par l'outil, "
                        f"réponds directement et précisément à ma question : {prompt}"
                    ),
                })
                continue  # rejouer la boucle pour obtenir la réponse finale

            # ----------------------------------------------------------------
            # Cas 2 : le modèle a écrit le tool call comme texte JSON
            #          (bug connu llama3.2 / mistral)
            # ----------------------------------------------------------------
            final_text = message.get("content", "")
            text_tc = self.parse_text_tool_call(final_text, known_tool_names)

            if text_tc and iteration < max_tool_iterations - 1:
                tool_name = text_tc["name"]
                arguments = text_tc["arguments"]

                if on_tool_call:
                    on_tool_call(tool_name, arguments)

                print(f"🔧 [LocalLLM] Text tool call détecté: {tool_name}({json.dumps(arguments)[:80]})")
                try:
                    tool_result = tool_executor(tool_name, arguments)
                except Exception as exc:
                    tool_result = f"[Erreur {tool_name}]: {exc}"

                tool_calls_log.append({
                    "tool": tool_name,
                    "arguments": arguments,
                    "result_preview": str(tool_result)[:200],
                })
                print(f"   ↳ Résultat : {str(tool_result)[:120]}...")

                # Remplacer le message texte JSON par un vrai échange
                # assistant + tool pour que le modèle comprende le contexte
                messages.append({"role": "assistant", "content": final_text})
                messages.append({"role": "tool", "content": str(tool_result)})
                messages.append({
                    "role": "user",
                    "content": (
                        f"En utilisant UNIQUEMENT les informations ci-dessus retournées par l'outil, "
                        f"réponds directement et précisément à ma question : {prompt}"
                    ),
                })
                continue  # rejouer la boucle

            # ----------------------------------------------------------------
            # Cas 3 : réponse finale en texte → streaming
            # ----------------------------------------------------------------
            if final_text:
                # Garde-fou (approche regex indépendante de _parse_text_tool_call) :
                # si le modèle a retourné du JSON de tool call en texte brut,
                # on l'intercepte AVANT de le streamer.
                if final_text.strip().startswith("{") and iteration < max_tool_iterations - 1:
                    _pattern = (
                        r'"name"\s*:\s*"('
                        + "|".join(re.escape(n) for n in known_tool_names if n)
                        + r')"'
                    )
                    _m = re.search(_pattern, final_text)
                    if _m:
                        t_name = _m.group(1)
                        # Extraire la valeur depuis "description" (hallucination de schéma)
                        t_args: Dict = {}
                        _d = re.search(r'"description"\s*:\s*"([^"]+)"', final_text)
                        if _d:
                            if t_name == "web_search":
                                t_args = {"query": _d.group(1)}
                            elif t_name in ("read_local_file", "list_directory"):
                                t_args = {"path": _d.group(1)}
                            elif t_name == "calculate":
                                t_args = {"expression": _d.group(1)}
                            elif t_name == "generate_code":
                                t_args = {"description": _d.group(1), "language": "python"}
                        # Fallback ultime : dériver depuis le prompt utilisateur
                        if not t_args:
                            if t_name == "web_search":
                                t_args = {"query": prompt}
                            elif t_name in ("read_local_file", "list_directory"):
                                _pm = re.search(r"[\w./\\]+", prompt)
                                t_args = {"path": _pm.group(0) if _pm else "."}
                            elif t_name == "calculate":
                                t_args = {"expression": prompt}
                            elif t_name == "generate_code":
                                t_args = {"description": prompt, "language": "python"}
                        # NE PAS appeler on_tool_call ici : tool_executor (ai_engine.py)
                        # s'en charge après optimisation de la requête.
                        print(f"🔧 [LocalLLM] Cas3 regex tool call: {t_name}({json.dumps(t_args)[:80]})")
                        try:
                            t_result = tool_executor(t_name, t_args)
                        except Exception as exc:
                            t_result = f"[Erreur {t_name}]: {exc}"
                        tool_calls_log.append({"tool": t_name, "arguments": t_args, "result_preview": str(t_result)[:200]})
                        print(f"   ↳ Résultat : {str(t_result)[:120]}...")
                        messages.append({"role": "assistant", "content": final_text})
                        messages.append({"role": "tool", "content": str(t_result)})
                        messages.append({
                            "role": "user",
                            "content": (
                                f"En utilisant UNIQUEMENT les informations ci-dessus retournées par l'outil, "
                                f"réponds directement et précisément à ma question : {prompt}"
                            ),
                        })
                        continue  # relancer la boucle pour la synthèse finale

                if on_token:
                    words = final_text.split(" ")
                    for i, word in enumerate(words):
                        if is_interrupted_callback and is_interrupted_callback():
                            break
                        chunk = word + (" " if i < len(words) - 1 else "")
                        should_continue = on_token(chunk)
                        if should_continue is False:
                            break
                self.add_to_history("user", prompt)
                self.add_to_history("assistant", final_text)
            return {
                "response": final_text,
                "tool_calls": tool_calls_log,
                "success": bool(final_text),
            }

        return {"response": None, "tool_calls": tool_calls_log, "success": False}

    # ------------------------------------------------------------------
    # Gestion de l'historique avec résumé glissant
    # ------------------------------------------------------------------

    @staticmethod
    def _estimate_tokens(messages: List[Dict[str, str]]) -> int:
        """Estime le nombre de tokens d'une liste de messages (≈4 chars/token)."""
        total_chars = sum(len(m.get("content", "")) for m in messages)
        return total_chars // 4

    def _build_summary_prompt(self, messages_to_summarize: List[Dict[str, str]]) -> str:
        """Construit le prompt de résumé pour les messages anciens."""
        conversation_text = ""
        for m in messages_to_summarize:
            role_label = "Utilisateur" if m["role"] == "user" else "Assistant"
            conversation_text += f"{role_label}: {m['content']}\n"
        return (
            "Fais un résumé factuel et concis de cette conversation en 3-5 phrases. "
            "Conserve les faits importants, décisions prises et contexte clé. "
            "Réponds uniquement avec le résumé, sans introduction.\n\n"
            f"{conversation_text}"
        )

    def _compress_old_history(self):
        """
        Résume les messages les plus anciens de l'historique via Ollama
        et remplace les messages résumés par un unique message système.
        """
        if len(self.conversation_history) < self.max_history_length // 2:
            return  # Pas assez de messages pour résumer

        # Séparer : anciens messages à résumer / récents à conserver
        split_point = len(self.conversation_history) - self._keep_recent_messages
        if split_point <= 0:
            return

        old_messages = self.conversation_history[:split_point]
        recent_messages = self.conversation_history[split_point:]

        print(f"📝 [LocalLLM] Résumé glissant : compression de {len(old_messages)} anciens messages...")

        # Appel Ollama pour résumer l'ancienne partie
        summary_text = None
        try:
            summary_prompt = self._build_summary_prompt(old_messages)
            data = {
                "model": self.model,
                "messages": [{"role": "user", "content": summary_prompt}],
                "stream": False,
                "options": {"temperature": 0.3, "num_ctx": 8192, "num_predict": 512},
            }
            response = requests.post(self.chat_url, json=data, timeout=60)
            if response.status_code == 200:
                summary_text = response.json().get("message", {}).get("content", "").strip()
        except Exception as e:
            print(f"⚠️ [LocalLLM] Résumé impossible: {e}")

        # Construire le nouvel historique : résumé précédent + nouveau résumé + messages récents
        if summary_text:
            # Combiner avec l'éventuel résumé précédent
            if self._conversation_summary:
                combined = f"{self._conversation_summary}\n{summary_text}"
                # Résumer les deux résumés si combiné trop long
                if len(combined) > 2000:
                    self._conversation_summary = summary_text
                else:
                    self._conversation_summary = combined
            else:
                self._conversation_summary = summary_text

            summary_message = {
                "role": "system",
                "content": f"[Résumé de la conversation précédente] {self._conversation_summary}",
            }
            self.conversation_history = [summary_message] + recent_messages
            print(f"✅ [LocalLLM] Historique compressé → 1 résumé + {len(recent_messages)} messages récents")
        else:
            # Fallback simple : tronquer sans résumé
            self.conversation_history = recent_messages
            print(f"🔄 [LocalLLM] Historique tronqué à {len(recent_messages)} messages (résumé indisponible)")

    def add_to_history(self, role: str, content: str):
        """Ajoute un message à l'historique et déclenche le résumé glissant si nécessaire."""
        self.conversation_history.append({"role": role, "content": content})

        # Déclencher la compression si le contexte estimé dépasse le seuil
        estimated_tokens = self._estimate_tokens(self.conversation_history)
        if estimated_tokens > self._summary_threshold_tokens:
            print(
                f"⚡ [LocalLLM] Contexte estimé {estimated_tokens:,} tokens > seuil "
                f"{self._summary_threshold_tokens:,} → résumé glissant..."
            )
            self._compress_old_history()
        elif len(self.conversation_history) > self.max_history_length * 2:
            # Garde-fou sur le nombre brut de messages
            self.conversation_history = self.conversation_history[
                -self.max_history_length * 2 :
            ]
            print(
                f"🔄 [LocalLLM] Historique tronqué à {len(self.conversation_history)} messages"
            )

    @staticmethod
    def _sanitize_vision_response(response_text: str) -> str:
        """Nettoie les amorces contradictoires de refus dans les réponses vision."""
        if not response_text:
            return response_text

        response_lower = response_text.lower()
        refusal_markers = [
            "je ne peux pas",
            "je ne suis pas capable",
            "désolé, mais je ne peux pas",
            "malheureusement, je ne peux pas",
            "i cannot",
            "i can't",
            "i'm not able",
            "i am not able",
        ]
        visual_markers = [
            "je vois", "on voit", "sur l'image", "au centre",
            "à gauche", "à droite", "il y a", "capture d'écran",
            "interface", "texte", "bouton", "couleur", "page",
            "écran", "fenêtre", "menu", "i see", "i can see",
            "the image shows", "in the image",
        ]

        has_refusal = any(marker in response_lower for marker in refusal_markers)
        has_visual_content = any(marker in response_lower for marker in visual_markers)
        if not (has_refusal and has_visual_content):
            return response_text

        text = response_text.lstrip()
        lower_text = text.lower()

        # Retirer l'amorce contradictoire si elle est au début de la réponse
        starters = (
            "je ne peux pas", "je ne suis pas capable",
            "désolé", "malheureusement", "i cannot", "i can't",
            "i'm not able", "i am not able",
        )
        if lower_text.startswith(starters):
            # 1) Couper sur connecteurs de transition
            for transition in [
                "cependant", "néanmoins", "mais", "toutefois",
                "however", "but", "nevertheless",
            ]:
                idx = lower_text.find(transition)
                if 0 <= idx <= 300:
                    remainder = text[idx + len(transition):].lstrip(" ,:-")
                    if remainder:
                        return remainder[0].upper() + remainder[1:]

            # 2) Chercher le début de la description visuelle
            for marker in visual_markers:
                idx = lower_text.find(marker)
                if 0 < idx <= 400:
                    remainder = text[idx:].lstrip()
                    if remainder:
                        return remainder[0].upper() + remainder[1:]

            # 3) Fallback : couper après la première phrase
            period_idx = text.find(".")
            if 0 <= period_idx <= 300 and period_idx + 1 < len(text):
                remainder = text[period_idx + 1:].lstrip(" \n")
                if remainder:
                    return remainder[0].upper() + remainder[1:]

        return response_text

    @staticmethod
    def _is_vision_refusal(response_text: str) -> bool:
        """Détecte si la réponse est un refus de traiter l'image (sans contenu visuel utile)."""
        if not response_text:
            return True
        if len(response_text.strip()) < 50:
            return True

        response_lower = response_text.lower()
        refusal_phrases = [
            "je ne peux pas voir",
            "je ne peux pas analyser",
            "je ne peux pas vous aider à identifier",
            "je ne suis pas capable d'interagir",
            "je ne peux pas interagir",
            "l'image n'a pas été transmise",
            "l'image n'a pas été jointe",
            "vous devez me la partager",
            "donnez un résumé",
            "i cannot see",
            "i can't see",
            "i'm unable to view",
        ]
        visual_markers = [
            "je vois", "on voit", "au centre", "à gauche", "à droite",
            "il y a", "capture d'écran", "interface", "texte visible",
            "bouton", "page web", "écran", "fenêtre",
            "couleurs", "en haut", "en bas",
            "i see", "i can see", "the image shows",
        ]

        has_refusal = any(phrase in response_lower for phrase in refusal_phrases)
        has_visual = any(marker in response_lower for marker in visual_markers)

        # C'est un refus si ça contient des phrases de refus SANS contenu visuel utile
        return has_refusal and not has_visual

    def generate_with_image(self, prompt, image_base64, _system_prompt=None):
        """
        Génère une réponse à partir d'une image en utilisant un modèle vision.
        Utilise /api/generate (plus fiable pour les modèles vision que /api/chat).

        Args:
            prompt: Le message/question de l'utilisateur sur l'image
            image_base64: L'image encodée en base64
            system_prompt: Prompt système optionnel (ignoré, intégré au prompt)

        Returns:
            La réponse du modèle ou None si erreur
        """
        if not self.is_ollama_available:
            return None

        vision_model = self._get_vision_model()
        if not vision_model:
            return None

        # Construire un prompt direct sans system role (plus fiable pour llava)
        full_prompt = (
            f"Describe this image in detail in French. "
            f"User question: {prompt}"
        )

        data = {
            "model": vision_model,
            "prompt": full_prompt,
            "images": [image_base64],
            "stream": False,
            "options": {
                "temperature": 0.0,
                "top_p": 0.95,
                "repeat_penalty": 1.1,
                "num_ctx": 2048,
                "num_predict": 400,
            },
        }

        try:
            print(f"🖼️ [LocalLLM] Génération vision via '{vision_model}' (generate API)...")
            response = requests.post(self.ollama_url, json=data, timeout=self.timeout)
            if response.status_code == 200:
                result = response.json()
                assistant_response = result.get("response", "")
                if assistant_response:
                    assistant_response = self._sanitize_vision_response(assistant_response)
                    self.add_to_history("user", f"[Image jointe] {prompt}")
                    self.add_to_history("assistant", assistant_response)
                    print("✅ [LocalLLM] Réponse vision générée")
                return assistant_response
            else:
                print(f"⚠️ [LocalLLM] Erreur API vision: {response.status_code}")
                return None
        except requests.exceptions.Timeout:
            print(f"⚠️ [LocalLLM] Timeout vision après {self.timeout}s")
            return None
        except Exception as e:
            print(f"⚠️ [LocalLLM] Exception vision: {e}")
            return None

    def generate_stream_with_image(self, prompt, image_base64, _system_prompt=None, on_token=None):
        """
        Génère une réponse avec image en STREAMING.
        Utilise /api/generate (plus fiable pour vision) avec retry sur refus.

        Args:
            prompt: Le message de l'utilisateur
            image_base64: L'image encodée en base64
            system_prompt: Prompt système optionnel (ignoré, intégré au prompt)
            on_token: Callback pour chaque token

        Returns:
            La réponse complète ou None
        """
        if not self.is_ollama_available:
            return None

        vision_model = self._get_vision_model()
        if not vision_model:
            return None

        # Prompts de tentatives successives - anglais (langue native de llava)
        # Prompt ultra-strict pour éviter les hallucinations
        prompts_to_try = [
            (
                f"You are viewing an image. Describe ONLY what you can ACTUALLY SEE in the image. "
                f"Do not guess, do not infer, do not make assumptions. "
                f"If you cannot see something clearly, say so. "
                f"Answer in French.\n\n"
                f"User question: {prompt}"
            ),
            (
                f"IMPORTANT: An image is provided above. You MUST describe what you SEE in the image. "
                f"Be factual and literal. Do not invent content.\n\n"
                f"Question: {prompt}\n\n"
                f"Answer in French."
            ),
        ]

        for attempt, full_prompt in enumerate(prompts_to_try):
            # Le 1er essai utilise le streaming normal ; le retry est non-streaming
            # pour ne pas afficher un refus à l'utilisateur
            if attempt == 0:
                result = self._stream_vision_attempt(
                    vision_model, full_prompt, image_base64, on_token, attempt
                )
            else:
                print(f"🔄 [LocalLLM] Retry vision (tentative {attempt + 1})...")
                result = self._non_stream_vision_attempt(
                    vision_model, full_prompt, image_base64, attempt
                )

            if result and not self._is_vision_refusal(result):
                result = self._sanitize_vision_response(result)
                self.add_to_history("user", f"[Image jointe] {prompt}")
                self.add_to_history("assistant", result)
                print(f"✅ [LocalLLM] Réponse vision OK (tentative {attempt + 1})")

                # Si c'était un retry, envoyer la réponse au callback d'un coup
                if attempt > 0 and on_token:
                    on_token(result)

                return result

            if result:
                print(f"⚠️ [LocalLLM] Tentative {attempt + 1}: refus détecté ({len(result)} chars)")

        # Toutes les tentatives ont échoué, retourner la dernière réponse (même si c'est un refus)
        if result:
            result = self._sanitize_vision_response(result)
            self.add_to_history("user", f"[Image jointe] {prompt}")
            self.add_to_history("assistant", result)
            if on_token and not self._streamed_already:
                on_token(result)
            return result

        return None

    def _stream_vision_attempt(self, vision_model, full_prompt, image_base64, on_token, _attempt):
        """Tentative de vision en streaming via /api/generate."""
        self._streamed_already = False

        data = {
            "model": vision_model,
            "prompt": full_prompt,
            "images": [image_base64],
            "stream": True,
            "options": {
                "temperature": 0.0,
                "top_p": 0.95,
                "repeat_penalty": 1.1,
                "num_ctx": 2048,
                "num_predict": 400,
            },
        }

        try:
            print(f"⚡🖼️ [LocalLLM] Streaming vision via '{vision_model}' (generate API)...")
            full_response = ""

            with requests.post(
                self.ollama_url, json=data, timeout=self.timeout, stream=True
            ) as response:
                if response.status_code != 200:
                    print(f"⚠️ [LocalLLM] Erreur API vision: {response.status_code}")
                    return None

                for line in response.iter_lines():
                    if line:
                        try:
                            chunk = line.decode("utf-8")
                            json_chunk = __import__("json").loads(chunk)
                            token = json_chunk.get("response", "")

                            if token:
                                full_response += token
                                if on_token:
                                    should_continue = on_token(token)
                                    if should_continue is False:
                                        print("🛑 [LocalLLM] Vision interrompue")
                                        break

                            if json_chunk.get("done", False):
                                break
                        except Exception as e:
                            print(f"⚠️ [LocalLLM] Erreur parsing vision chunk: {e}")
                            continue

            self._streamed_already = bool(full_response)
            return full_response

        except requests.exceptions.Timeout:
            print(f"⚠️ [LocalLLM] Timeout vision streaming après {self.timeout}s")
            return None
        except Exception as e:
            print(f"⚠️ [LocalLLM] Exception vision streaming: {e}")
            return None

    def _non_stream_vision_attempt(self, vision_model, full_prompt, image_base64, _attempt):
        """Tentative de vision non-streaming via /api/generate (pour retry silencieux)."""
        data = {
            "model": vision_model,
            "prompt": full_prompt,
            "images": [image_base64],
            "stream": False,
            "options": {
                "temperature": 0.0,
                "top_p": 0.95,
                "repeat_penalty": 1.1,
                "num_ctx": 2048,
                "num_predict": 400,
            },
        }

        try:
            response = requests.post(self.ollama_url, json=data, timeout=self.timeout)
            if response.status_code == 200:
                return response.json().get("response", "")
            return None
        except Exception as e:
            print(f"⚠️ [LocalLLM] Exception retry vision: {e}")
            return None

    def _get_vision_model(self):
        """Détecte et retourne un modèle vision disponible dans Ollama"""
        vision_models = ["llama3.2-vision", "llava", "llava:13b", "llava:7b", "bakllava", "moondream"]

        try:
            response = requests.get(
                self.ollama_url.replace("/api/generate", "/api/tags"), timeout=5
            )
            if response.status_code == 200:
                models = response.json().get("models", [])
                available_names = [m.get("name", "").split(":", maxsplit=1)[0] for m in models]

                for vm in vision_models:
                    base_name = vm.split(":", maxsplit=1)[0]
                    if base_name in available_names:
                        # Retourner le nom exact du modèle trouvé
                        for m in models:
                            if m.get("name", "").startswith(base_name):
                                print(f"🖼️ [LocalLLM] Modèle vision trouvé: {m['name']}")
                                return m["name"]

                print("⚠️ [LocalLLM] Aucun modèle vision trouvé.")
                print("   💡 Installez-en un avec: ollama pull llava")
                print(f"   📋 Modèles supportés: {', '.join(vision_models)}")
                return None
        except Exception as e:
            print(f"⚠️ [LocalLLM] Erreur détection modèle vision: {e}")
            return None

    def clear_history(self):
        """Efface l'historique de conversation"""
        self.conversation_history.clear()
        print("🗑️ [LocalLLM] Historique de conversation effacé")

    def get_last_user_message(self) -> str:
        """Récupère le dernier message de l'utilisateur pour le contexte"""
        for msg in reversed(self.conversation_history):
            if msg["role"] == "user":
                return msg["content"]
        return ""

    def get_conversation_context(self, n_messages: int = 5) -> str:
        """Récupère les n derniers échanges sous forme de texte pour le contexte"""
        recent = (
            self.conversation_history[-n_messages * 2 :]
            if self.conversation_history
            else []
        )
        context_parts = []
        for msg in recent:
            role = "Utilisateur" if msg["role"] == "user" else "Assistant"
            context_parts.append(f"{role}: {msg['content']}")
        return "\n".join(context_parts)
