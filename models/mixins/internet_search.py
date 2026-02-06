"""
InternetSearchMixin — Méthodes de recherche internet pour CustomAIModel.

Regroupe : _handle_internet_search, _get_search_query_from_context,
_clean_search_query, _generate_ollama_search_response, _extract_search_query,
_optimize_search_query_with_ollama, _handle_url_summarization, _extract_url,
_detect_search_type.
"""

import re
from typing import Any, Dict


class InternetSearchMixin:
    """Mixin regroupant toutes les méthodes de recherche internet."""

    def _handle_internet_search(
        self, user_input: str, context: Dict[str, Any], on_token=None
    ) -> str:
        """
        Gère les demandes de recherche internet avec intégration Ollama.
        Utilise le contexte de conversation pour comprendre les requêtes implicites.

        Args:
            user_input: Question de l'utilisateur
            context: Contexte de la conversation
            on_token: Callback pour le streaming (optionnel)
        Returns:
            str: Réponse générée par Ollama basée sur les résultats de recherche
        """
        # Si la question ne mentionne pas explicitement un document, on ignore le contexte documentaire
        if not any(
            word in user_input.lower()
            for word in ["document", "pdf", "docx", "fichier", "rapport", "contenu"]
        ):
            context = context.copy() if context else {}
            # Supprimer toutes les clés contenant 'document', 'pdf' ou 'docx' (nettoyage renforcé)
            for k in list(context.keys()):
                if any(x in k.lower() for x in ["document", "pdf", "docx"]):
                    context.pop(k)

        # Extraire la requête de recherche de l'input utilisateur
        search_query = self._extract_search_query(user_input)

        # 🧠 NOUVEAU: Si pas de requête explicite OU requête trop générique, utiliser le contexte
        generic_terms = ["internet", "web", "google", "en ligne", "ligne", ""]
        if not search_query or search_query.lower().strip() in generic_terms:
            context_query = self._get_search_query_from_context(user_input)
            if context_query:
                print(f"🧠 [CONTEXTE] Requête déduite du contexte: '{context_query}'")
                search_query = context_query

        if not search_query:
            return """🔍 **Recherche internet**

Je n'ai pas bien compris ce que vous voulez rechercher. 

**Exemples de demandes :**
• "Cherche sur internet les actualités Python"
• "Recherche des informations sur l'intelligence artificielle"
• "Trouve-moi des news sur Tesla"
• "Peux-tu chercher comment faire du pain ?"

Reformulez votre demande en précisant ce que vous voulez rechercher."""

        # 🧠 OPTIMISATION: Si la requête est longue (>20 caractères), utiliser Ollama pour extraire les mots-clés
        if (
            len(search_query) > 20
            and self.local_llm
            and self.local_llm.is_ollama_available
        ):
            optimized_query = self._optimize_search_query_with_ollama(search_query)
            if optimized_query and len(optimized_query) < len(search_query):
                print(
                    f"🧠 [OLLAMA] Requête optimisée: '{search_query}' → '{optimized_query}'"
                )
                search_query = optimized_query

        # Effectuer la recherche avec le moteur de recherche internet
        try:
            print(f"🌐 Lancement de la recherche pour: '{search_query}'")
            # Obtenir les résultats bruts de la recherche
            raw_results = self.internet_search.search_and_summarize(search_query)

            # 🦙 NOUVEAU: Utiliser Ollama pour générer une réponse intelligente
            if self.local_llm and self.local_llm.is_ollama_available:
                ollama_response = self._generate_ollama_search_response(
                    search_query, raw_results, user_input, on_token
                )
                if ollama_response:
                    return ollama_response

            # Fallback: retourner les résultats bruts si Ollama n'est pas disponible
            return raw_results

        except Exception as e:
            print(f"❌ Erreur lors de la recherche internet: {str(e)}")
            return f"""❌ **Erreur de recherche**

Désolé, je n'ai pas pu effectuer la recherche pour '{search_query}'.

**Causes possibles :**
• Pas de connexion internet
• Problème temporaire avec les moteurs de recherche
• Requête trop complexe

**Solutions :**
• Vérifiez votre connexion internet
• Reformulez votre demande
• Réessayez dans quelques instants

Erreur technique : {str(e)}"""

    def _get_search_query_from_context(self, user_input: str) -> str:
        """
        Déduit la requête de recherche à partir du contexte de conversation.
        Utilisé quand l'utilisateur dit juste "cherche sur internet" sans préciser quoi.
        """
        # Vérifier si c'est une demande implicite (sans sujet précis)
        implicit_patterns = [
            r"^cherche\s+(sur\s+)?internet\s*$",
            r"^recherche\s+(sur\s+)?internet\s*$",
            r"^cherche\s+(sur\s+)?(le\s+)?web\s*$",
            r"^recherche\s+en\s+ligne\s*$",
            r"^trouve\s+(ça|cela)?\s*(sur\s+)?internet\s*$",
            r"^va\s+chercher\s+(sur\s+)?internet\s*$",
        ]

        user_lower = user_input.lower().strip()
        is_implicit = any(
            re.match(pattern, user_lower) for pattern in implicit_patterns
        )

        if not is_implicit:
            generic_only = user_lower in [
                "cherche sur internet",
                "recherche sur internet",
                "cherche internet",
                "internet",
            ]
            if not generic_only:
                return ""

        print("🧠 [CONTEXTE] Requête implicite détectée, analyse du contexte...")

        ignore_keywords = [
            "cherche",
            "recherche",
            "internet",
            "web",
            "trouve",
            "google",
            "en ligne",
        ]

        original_question = ""

        # PRIORITÉ 1: Utiliser la ConversationMemory (plus fiable)
        if self.conversation_memory:
            recent = self.conversation_memory.get_recent_conversations(10)
            print(f"🧠 [CONTEXTE] {len(recent)} conversations récentes en mémoire")

            for conv in reversed(recent):
                content = conv.user_message.lower().strip()
                if len(content) > 5 and not any(
                    kw in content for kw in ignore_keywords
                ):
                    print(
                        f"🧠 [CONTEXTE] Question précédente trouvée (ConversationMemory): '{conv.user_message[:100]}'"
                    )
                    original_question = conv.user_message
                    break

        # PRIORITÉ 2: Utiliser l'historique LocalLLM comme fallback
        if (
            not original_question
            and self.local_llm
            and hasattr(self.local_llm, "conversation_history")
        ):
            history = self.local_llm.conversation_history
            print(f"🧠 [CONTEXTE] {len(history)} messages dans l'historique LocalLLM")

            for msg in reversed(history):
                if msg["role"] == "user":
                    content = msg["content"].lower().strip()
                    if len(content) > 5 and not any(
                        kw in content for kw in ignore_keywords
                    ):
                        print(
                            f"🧠 [CONTEXTE] Dernière question trouvée (LocalLLM): '{msg['content'][:100]}'"
                        )
                        original_question = msg["content"]
                        break

        if not original_question:
            print("⚠️ [CONTEXTE] Aucune question pertinente trouvée dans le contexte")
            return ""

        cleaned_query = self._clean_search_query(original_question)
        print(
            f"🔧 [CONTEXTE] Requête nettoyée: '{original_question}' → '{cleaned_query}'"
        )

        return cleaned_query

    def _clean_search_query(self, query: str) -> str:
        """
        Nettoie une question pour en faire une requête de recherche optimale.
        Supprime les mots inutiles et garde uniquement les mots-clés essentiels.
        """
        stop_words = {
            "le", "la", "les", "un", "une", "des", "du", "de", "d", "l",
            "je", "tu", "il", "elle", "on", "nous", "vous", "ils", "elles",
            "me", "te", "se", "moi", "toi", "lui", "eux",
            "à", "au", "aux", "en", "dans", "sur", "sous", "par", "pour", "avec", "sans",
            "et", "ou", "mais", "donc", "car", "ni", "que", "qui", "quoi",
            "est", "sont", "suis", "es", "sommes", "êtes", "était", "être",
            "ai", "as", "a", "avons", "avez", "ont", "avoir",
            "fais", "fait", "faire", "peux", "peut", "peuvent", "pouvoir",
            "dis", "donne", "montre", "explique", "raconte", "décris",
            "stp", "svp", "please", "merci",
            "comment", "pourquoi", "quand", "combien", "quel", "quelle", "quels", "quelles",
            "ça", "cela", "ce", "cette", "ces", "mon", "ma", "mes",
            "ton", "ta", "tes", "son", "sa", "ses", "notre", "votre",
            "leur", "leurs", "très", "plus", "moins", "bien", "bon", "bonne",
            "tout", "tous", "toute", "toutes",
        }

        query_lower = query.lower()
        query_clean = re.sub(r"['\"\-.,;:!?()\\[\\]{}]", " ", query_lower)
        query_clean = re.sub(r"\s+", " ", query_clean).strip()

        words = query_clean.split()
        keywords = [word for word in words if len(word) > 2 and word not in stop_words]

        cleaned = " ".join(keywords)
        if len(cleaned) < 3:
            return query_clean

        return cleaned

    def _generate_ollama_search_response(
        self, search_query: str, raw_results: str, original_question: str, on_token=None
    ) -> str:
        """
        Utilise Ollama pour générer une réponse basée sur les résultats de recherche.
        """
        try:
            sources_section = ""
            if "🔗 **Sources**" in raw_results or "**Sources**" in raw_results:
                source_patterns = [
                    r"(🔗\s*\*\*Sources\*\*.*?)$",
                    r"(\*\*Sources\*\*.*?)$",
                    r"(📚\s*Sources.*?)$",
                ]
                for pattern in source_patterns:
                    match = re.search(pattern, raw_results, re.DOTALL | re.IGNORECASE)
                    if match:
                        sources_section = match.group(1).strip()
                        break

            system_prompt = """Tu es un assistant IA expert qui synthétise des informations de recherche internet.
Ton rôle est de fournir une réponse claire, structurée et informative basée sur les résultats de recherche.

Instructions:
- Réponds de manière naturelle et conversationnelle en français
- Utilise le formatage Markdown (gras, listes, titres) pour structurer ta réponse
- Sois précis et cite les informations importantes
- Ne mentionne pas que tu analyses des "résultats de recherche", réponds directement
- Si les résultats contiennent des informations contradictoires, mentionne-le
- Garde un ton amical et accessible"""

            user_prompt = f"""Question de l'utilisateur: {original_question}

Informations trouvées sur internet concernant "{search_query}":
{raw_results[:4000]}

Génère une réponse complète et bien structurée basée sur ces informations."""

            print("🦙 [OLLAMA] Génération de la réponse basée sur la recherche...")

            saved_history = self.local_llm.conversation_history.copy()
            self.local_llm.conversation_history = []

            try:
                sources_text = ""
                if sources_section:
                    sources_text = f"\n\n{sources_section}"
                elif "http" in raw_results:
                    urls = re.findall(r"https?://[^\s\)]+", raw_results)
                    if urls:
                        unique_urls = list(dict.fromkeys(urls))[:5]
                        sources_text = "\n\n🔗 **Sources**\n"
                        for url in unique_urls:
                            clean_url = url.rstrip(".,;:)")
                            sources_text += f"• [{clean_url[:50]}...]({clean_url})\n"

                ollama_response = self.local_llm.generate_stream(
                    user_prompt,
                    system_prompt=system_prompt,
                    on_token=on_token,
                )

                if ollama_response:
                    final_response = ollama_response.strip()

                    if sources_text and on_token:
                        on_token(sources_text)

                    final_response += sources_text

                    self.local_llm.conversation_history = saved_history

                    self._add_to_conversation_history(
                        original_question,
                        final_response,
                        "internet_search",
                        1.0,
                        {},
                    )

                    print("✅ [OLLAMA] Réponse générée avec succès")
                    return final_response

            finally:
                self.local_llm.conversation_history = saved_history

            print("⚠️ [OLLAMA] Échec de la génération, utilisation des résultats bruts")
            return None

        except Exception as e:
            print(f"⚠️ [OLLAMA] Erreur lors de la génération: {e}")
            return None

    def _extract_search_query(self, user_input: str) -> str:
        """Extrait la requête de recherche de l'input utilisateur"""
        cleaned = user_input
        cleaned = re.sub(
            r"(?im)^.*(contexte des documents disponibles|contexte:|mémoire:).*$",
            "",
            cleaned,
        )
        cleaned = re.sub(r"(?is)^.*question\s*:\s*", "", cleaned)
        cleaned = re.sub(r"(?im)^\s*(system|assistant|user)\s*:\s*", "", cleaned)
        cleaned = "\n".join([line for line in cleaned.splitlines() if line.strip()])
        cleaned = cleaned.strip()

        user_lower = cleaned.lower().strip()
        patterns = [
            r"(?:cherche|recherche|trouve)\s+(?:sur\s+)?(?:internet|web|google|en ligne)\s+(.+)",
            r"(?:cherche|recherche)\s+(?:moi\s+)?(?:des\s+)?(?:informations?\s+)?(?:sur|à propos de)\s+(.+)",
            r"cherche[-\s]moi\s+(.+)",
            r"peux[-\s]tu\s+(?:chercher|rechercher|trouver)\s+(.+)",
            r"(?:informations?|info|données|news|actualités?)\s+(?:sur|à propos de|concernant)\s+(.+)",
            r"(?:dernières?\s+)?(?:actualités?|news|nouvelles?)\s+(?:sur|de|à propos de)\s+(.+)",
            r"qu[\'\"]?est[-\s]ce\s+qu[\'\"]?on\s+dit\s+(?:sur|de)\s+(.+)",
            r"(?:web|internet|google)\s+search\s+(.+)",
        ]
        for pattern in patterns:
            match = re.search(pattern, user_lower)
            if match:
                query = match.group(1).strip()
                query = re.sub(r"\s+", " ", query)
                query = query.strip(".,!?;")
                return query

        for word in [
            "cherche", "recherche", "trouve", "sur", "internet", "web",
            "google", "en", "ligne", "moi", "des", "informations",
        ]:
            if user_lower.startswith(word):
                user_lower = user_lower[len(word):].strip()

        return user_lower if len(user_lower) > 2 else ""

    def _optimize_search_query_with_ollama(self, long_query: str) -> str:
        """Utilise Ollama pour transformer une requête longue en mots-clés courts."""
        try:
            prompt = f"""Tu es un expert en optimisation de requêtes de recherche internet.

Transforme cette requête de recherche longue en une liste de 2-5 mots-clés courts et pertinents pour un moteur de recherche (Google, DuckDuckGo).

Requête originale: "{long_query}"

Règles:
- Maximum 5 mots-clés
- Utilise des mots simples et directs
- Retire les mots comme "des", "sur", "pourquoi", "comment" si possible
- Garde les termes essentiels
- Pas de ponctuation
- Pas de phrase, juste des mots-clés séparés par des espaces

Réponds UNIQUEMENT avec les mots-clés, rien d'autre.

Mots-clés optimisés:"""

            response = self.local_llm.generate(
                prompt=prompt,
                system_prompt="Tu es un assistant qui extrait des mots-clés pour la recherche internet.",
            )

            if response:
                optimized = response.strip().strip("\"'")
                if len(optimized) <= 150 and len(optimized) >= 3:
                    return optimized

        except Exception as e:
            print(f"⚠️ Erreur lors de l'optimisation de la requête avec Ollama: {e}")

        return long_query

    def _handle_url_summarization(self, user_input: str) -> str:
        """Gère les demandes de résumé d'URL directe"""
        url = self._extract_url(user_input)

        if not url:
            return """🔗 **Résumé d'URL**

Je n'ai pas trouvé d'URL valide dans votre message.

**Exemples de demandes :**
• "Résume cette page : https://example.com"
• "Résume ce lien : https://example.com/article"
• "Que contient cette page : https://example.com/blog"
• "Résume ceci : https://example.com"

Assurez-vous d'inclure une URL complète commençant par http:// ou https://"""

        try:
            print(f"🌐 Récupération et résumé de l'URL: {url}")
            result = self.internet_search.summarize_url(url)
            return result
        except Exception as e:
            print(f"❌ Erreur lors du résumé de l'URL: {str(e)}")
            return f"""❌ **Erreur de résumé**

Désolé, je n'ai pas pu résumer la page '{url}'.

**Causes possibles :**
• La page n'est pas accessible ou est protégée
• Problème de connexion internet
• Le format de la page n'est pas supporté
• La page nécessite une authentification

**Solutions :**
• Vérifiez que l'URL est correcte et accessible
• Vérifiez votre connexion internet
• Essayez avec une autre page
• Réessayez dans quelques instants

Erreur technique : {str(e)}"""

    def _extract_url(self, user_input: str) -> str:
        """Extrait une URL de l'input utilisateur"""
        url_pattern = r"https?://[^\s<>\"{}\\|^`\[\]]+"
        urls = re.findall(url_pattern, user_input)

        if urls:
            url = urls[0]
            url = url.rstrip(".,!?;:)")
            return url

        return ""

    def _detect_search_type(self, user_input: str) -> str:
        """Détecte le type de recherche demandé"""
        user_lower = user_input.lower()

        if any(
            word in user_lower
            for word in ["actualité", "news", "dernières nouvelles", "récent"]
        ):
            return "news"
        elif any(
            word in user_lower
            for word in ["comment", "how to", "tutorial", "guide", "étapes"]
        ):
            return "tutorial"
        elif any(
            word in user_lower
            for word in ["qu'est-ce que", "définition", "c'est quoi", "define"]
        ):
            return "definition"
        elif any(word in user_lower for word in ["prix", "coût", "combien", "price"]):
            return "price"
        elif any(
            word in user_lower for word in ["avis", "opinion", "review", "critique"]
        ):
            return "review"
        else:
            return "general"
