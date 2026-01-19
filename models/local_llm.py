"""
Module de gestion des LLM locaux avec priorité à Ollama.
Support de l'historique de conversation pour un contexte persistant.
"""

from typing import Dict, List

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
        timeout=500,
    ):
        # On essaie d'abord le modèle personnalisé 'my_ai', sinon fallback sur 'llama3'
        self.model = model
        self.ollama_url = ollama_url
        self.chat_url = ollama_url.replace("/api/generate", "/api/chat")
        self.timeout = timeout  # Timeout configurable
        self.is_ollama_available = self._check_ollama_availability()

        # 🧠 Historique de conversation pour le contexte
        self.conversation_history: List[Dict[str, str]] = []
        self.max_history_length = 100  # Garder les 100 derniers échanges

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

    def generate(self, prompt, system_prompt=None):
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
        messages.extend(self.conversation_history)

        # Ajouter le message actuel de l'utilisateur
        messages.append({"role": "user", "content": prompt})

        data = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": 0.7,
                "num_ctx": 8192,  # Contexte plus grand pour l'historique
                "num_predict": 1024,  # Réponses plus complètes
            },
        }

        try:
            print(
                f"⏳ [LocalLLM] Génération avec contexte ({len(self.conversation_history)} messages précédents)..."
            )
            response = requests.post(self.chat_url, json=data, timeout=self.timeout)
            if response.status_code == 200:
                result = response.json()
                assistant_response = result.get("message", {}).get("content", "")

                if assistant_response:
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
                "   💡 Conseil: Essayez un modèle plus léger (llama3.2) ou augmentez le timeout."
            )
            return None
        except Exception as e:
            print(f"⚠️ [LocalLLM] Exception durant la génération: {e}")
            return None

    def add_to_history(self, role: str, content: str):
        """Ajoute un message à l'historique de conversation"""
        self.conversation_history.append({"role": role, "content": content})

        # Limiter la taille de l'historique
        if len(self.conversation_history) > self.max_history_length * 2:
            # Garder les premiers messages (contexte initial) et les derniers
            self.conversation_history = self.conversation_history[
                -self.max_history_length * 2 :
            ]
            print(
                f"🔄 [LocalLLM] Historique tronqué à {len(self.conversation_history)} messages"
            )

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

    def generate_stream(self, prompt, system_prompt=None, on_token=None):
        """
        Génère une réponse en STREAMING pour une latence minimale.
        Chaque token est envoyé via le callback on_token(token_text) dès qu'il est reçu.

        Args:
            prompt: Le message de l'utilisateur
            system_prompt: Prompt système optionnel
            on_token: Callback appelé pour chaque token reçu (signature: on_token(str) -> bool)
                     Retourne False pour interrompre la génération

        Returns:
            La réponse complète une fois terminée, ou None si erreur
        """
        if not self.is_ollama_available:
            return None

        # Construire les messages avec historique
        messages = []

        # Ajouter le system prompt s'il existe
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        # Ajouter l'historique de conversation
        messages.extend(self.conversation_history)

        # Ajouter le message actuel de l'utilisateur
        messages.append({"role": "user", "content": prompt})

        data = {
            "model": self.model,
            "messages": messages,
            "stream": True,  # ⚡ STREAMING ACTIVÉ
            "options": {
                "temperature": 0.7,
                "num_ctx": 8192,
                "num_predict": 1024,
            },
        }

        try:
            print(
                f"⚡ [LocalLLM] Génération STREAMING ({len(self.conversation_history)} messages contexte)..."
            )

            full_response = ""

            # Requête en streaming
            with requests.post(
                self.chat_url, json=data, timeout=self.timeout, stream=True
            ) as response:
                if response.status_code != 200:
                    print(f"⚠️ [LocalLLM] Erreur API Ollama: {response.status_code}")
                    return None

                # Lire les chunks JSON ligne par ligne
                for line in response.iter_lines():
                    if line:
                        try:
                            chunk = line.decode("utf-8")
                            json_chunk = __import__("json").loads(chunk)

                            # Extraire le contenu du token
                            token = json_chunk.get("message", {}).get("content", "")

                            if token:
                                full_response += token

                                # Appeler le callback si fourni
                                if on_token:
                                    should_continue = on_token(token)
                                    if should_continue is False:
                                        print(
                                            "🛑 [LocalLLM] Génération interrompue par callback"
                                        )
                                        break

                            # Vérifier si c'est le dernier message
                            if json_chunk.get("done", False):
                                break

                        except Exception as e:
                            print(f"⚠️ [LocalLLM] Erreur parsing chunk: {e}")
                            continue

            if full_response:
                # Sauvegarder dans l'historique
                self.add_to_history("user", prompt)
                self.add_to_history("assistant", full_response)
                print(
                    "✅ [LocalLLM] Réponse streaming complète et ajoutée à l'historique"
                )

            return full_response

        except requests.exceptions.Timeout:
            print(f"⚠️ [LocalLLM] Timeout après {self.timeout}s")
            return None
        except Exception as e:
            print(f"⚠️ [LocalLLM] Exception streaming: {e}")
            return None
