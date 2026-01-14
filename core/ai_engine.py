"""
Moteur principal de l'IA personnelle
Gère l'orchestration entre les différents modules
"""

import asyncio
import concurrent.futures
import os
import tempfile
from typing import Any, Dict, List, Optional

from generators.document_generator import DocumentGenerator
from generators.code_generator import CodeGenerator as OllamaCodeGenerator
from models.advanced_code_generator import AdvancedCodeGenerator as WebCodeGenerator
from models.conversation_memory import ConversationMemory
from models.custom_ai_model import CustomAIModel
from models.internet_search import InternetSearchEngine
from models.ml_faq_model import MLFAQModel
from models.smart_web_searcher import search_smart_code
from models.smart_code_searcher import multi_source_searcher
from processors.code_processor import CodeProcessor
from processors.docx_processor import DOCXProcessor
from processors.pdf_processor import PDFProcessor
from utils.file_manager import FileManager
from utils.logger import setup_logger

from .config import AI_CONFIG
from .conversation import ConversationManager
from .validation import validate_input


class AIEngine:
    """
    Moteur principal de l'IA personnelle
    """

    def __init__(self, config: Optional[Dict] = None):
        """
        Initialise le moteur IA

        Args:
            config: Configuration personnalisée (optionnel)
        """
        self.config = config or AI_CONFIG
        self.logger = setup_logger("AIEngine")

        # Initialisation des composants
        self.file_manager = FileManager()

        self.current_request_id = 0

        # Initialiser session_context AVANT tout le reste
        self.session_context = {
            "documents_processed": [],
            "code_files_processed": [],
            "last_document_type": None,
            "current_document": None,
        }

        # Initialisation de la mémoire et du gestionnaire de conversations
        self.conversation_memory = ConversationMemory()
        self.conversation_manager = ConversationManager(memory=self.conversation_memory)

        # Modèle IA local personnalisé avec mémoire de conversation (100% autonome)
        try:
            self.local_ai = CustomAIModel(conversation_memory=self.conversation_memory)
            self.ml_ai = MLFAQModel()  # Modèle ML local (TF-IDF)
            # Debug supprimé : plus de log sur le chargement de la base FAQ/ML
            self.model = (
                self.local_ai
            )  # Alias pour compatibilité avec l'interface graphique
            self.logger.info("✅ Modèle IA local avec mémoire initialisé")
            self.logger.info("✅ Modèle ML (TF-IDF) initialisé")
            # Initialisation du gestionnaire de LLM
            self.llm_manager = (
                self.local_ai
            )  # Pour compatibilité avec les fonctions qui utilisent llm_manager
        except Exception as e:
            self.logger.error("❌ Erreur lors de l'initialisation du modèle IA : %s", e)
            # Fallback sur l'ancien système
            self.local_ai = CustomAIModel()
            self.ml_ai = None
            self.model = self.local_ai
            self.llm_manager = self.local_ai

        # Processeurs
        self.pdf_processor = PDFProcessor()
        self.docx_processor = DOCXProcessor()
        self.code_processor = CodeProcessor()

        # Générateurs avec support Ollama
        llm_instance = (
            self.local_ai.local_llm if hasattr(self.local_ai, "local_llm") else None
        )
        self.document_generator = DocumentGenerator(llm=llm_instance)
        self.ollama_code_generator = OllamaCodeGenerator(
            llm=llm_instance
        )  # Générateur avec Ollama
        self.code_generator = WebCodeGenerator()  # Générateur avec recherche web
        self.web_code_searcher = multi_source_searcher

        self.logger.info(
            "Moteur IA initialisé avec succès (Générateurs Ollama + Web activés)"
        )

    def process_text(self, text: str, context: Optional[Dict[str, Any]] = None) -> str:
        """
        Interface synchrone avec validation des entrées

        Args:
            text: Texte de la requête utilisateur
            context: Contexte additionnel (optionnel)

        Returns:
            Réponse générée

        Raises:
            ValueError: Si l'entrée ne passe pas la validation
        """
        try:
            # Validation de l'entrée avec Pydantic
            validated_input = validate_input(
                {"query": text, "context": context}, "query"
            )

            # Utiliser les données validées et nettoyées
            text = validated_input.query
            context = validated_input.context

            self.logger.info("[VALIDÉ] process_text: %s", repr(text[:100]))

            # Analyser rapidement le type de requête
            text_lower = text.lower()

            # 1. Questions factuelles → Recherche web directe
            if any(
                word in text_lower
                for word in [
                    "combien",
                    "population",
                    "habitants",
                    "nombre",
                    "statistiques",
                ]
            ):
                return "🔍 **Recherche web en cours...**\n\nJe recherche cette information sur internet pour vous donner une réponse à jour.\n\n*(Note: Le système de recherche web est en cours d'implémentation)*"

            # 2. Demandes de code → Nouveau générateur web
            code_keywords = [
                "génère",
                "crée",
                "écris",
                "développe",
                "fonction",
                "script",
                "code",
            ]
            if any(keyword in text_lower for keyword in code_keywords):
                try:
                    # Détecter le langage
                    language = "python"  # Défaut
                    if "javascript" in text_lower or "js" in text_lower:
                        language = "javascript"
                    elif "java" in text_lower and "javascript" not in text_lower:
                        language = "java"

                    # Lancer la recherche web via AdvancedCodeGenerator
                    async def run_web_search():
                        return await self.code_generator.generate_code_from_web(
                            text, language
                        )

                    # Exécuter la recherche
                    try:
                        loop = asyncio.get_event_loop()
                        if loop.is_running():
                            # Dans un event loop existant
                            with concurrent.futures.ThreadPoolExecutor() as executor:
                                future = executor.submit(asyncio.run, run_web_search())
                                result = future.result(timeout=30)
                        else:
                            result = loop.run_until_complete(run_web_search())
                    except RuntimeError:
                        # Pas d'event loop
                        result = asyncio.run(run_web_search())

                    if result.get("success"):
                        code = result.get("code", "")
                        source = result.get("source", "Web")
                        explanation = result.get("explanation", "")

                        return f"🌐 **Code trouvé sur {source}:**\n\n```{language}\n{code}\n```\n\n💬 **Explication:** {explanation}"
                    else:
                        # Fallback minimal seulement si recherche web échoue
                        if "tri" in text_lower or "sort" in text_lower:
                            return f"🛠️ **Code généré localement (recherche web échouée):**\n\n```{language}\ndef sort_list(items):\n    \"\"\"Trie une liste par ordre alphabétique\"\"\"\n    return sorted(items)\n\n# Exemple\nwords = ['pomme', 'banane', 'cerise']\nsorted_words = sort_list(words)\nprint(sorted_words)  # ['banane', 'cerise', 'pomme']\n```"
                        else:
                            return f'❌ **Impossible de trouver du code pour:** "{text}"\n\n🔍 **Recherches effectuées:**\n• GitHub, Stack Overflow, GeeksforGeeks\n\n💡 **Suggestions:**\n• Soyez plus spécifique (ex: "fonction Python qui trie une liste")\n• Précisez le langage souhaité'

                except ImportError:
                    return "❌ **Erreur:** Module de recherche web non disponible.\n\nVeuillez vérifier que tous les modules sont installés correctement."
                except Exception as e:
                    return f"❌ **Erreur lors de la recherche web:** {str(e)}\n\nLe système de recherche web rencontre des difficultés."

            # 3. Questions conversationnelles
            if any(
                phrase in text_lower
                for phrase in [
                    "comment ça va",
                    "comment vas tu",
                    "ça va",
                    "salut",
                    "bonjour",
                ]
            ):
                # Éviter le bug "Très bien, merci de demander"
                if "comment ça va" in text_lower and not any(
                    tech in text_lower for tech in ["python", "code", "fonction"]
                ):
                    return "Salut ! Je vais bien, merci ! 😊 Je suis votre assistant IA et je suis prêt à vous aider. Que puis-je faire pour vous ?"
                else:
                    return "Bonjour ! Comment puis-je vous aider aujourd'hui ? Je peux générer du code, répondre à vos questions techniques, ou rechercher des informations sur internet."

            # 4. Questions sur l'IA
            if any(
                phrase in text_lower
                for phrase in ["qui es-tu", "que fais-tu", "tes capacités"]
            ):
                return """Je suis votre assistant IA personnel ! 🤖

🌐 **Mes capacités principales :**
• **Génération de code** (Python, JavaScript, etc.) avec recherche web
• **Recherche d'informations** sur internet en temps réel
• **Analyse de documents** et de fichiers
• **Assistance technique** et programmation

💡 **Nouveautés :**
• Je cherche maintenant du code sur GitHub, Stack Overflow, etc.
• Plus de templates pré-codés - uniquement du vrai code trouvé sur le web !

Que voulez-vous que je fasse pour vous ?"""

            # 5. Fallback général
            return "Je vois ! Et comment puis-je vous aider avec ça ?\n\n💡 **Je peux :**\n• Générer du code (avec recherche web)\n• Rechercher des informations sur internet\n• Répondre à vos questions techniques\n\nQue souhaitez-vous faire ?"

        except Exception as e:
            self.logger.error("Erreur dans le nouveau process_text: %s", e)
            return f"❌ **Erreur système:** {str(e)}\n\nLe nouveau système de recherche web rencontre des difficultés. Veuillez réessayer."

    def _merge_responses(self, response_custom, response_ml):
        """
        Donne la priorité à la FAQ ML : si une réponse MLFAQ existe, elle est utilisée, sinon on utilise la réponse custom.
        """
        if response_ml is not None and str(response_ml).strip():
            return str(response_ml)
        return response_custom

    def _get_help_text(self) -> str:
        """Retourne le texte d'aide"""
        return """🤖 Aide - My AI Personal Assistant

📝 **Génération de code :**
• "génère une fonction pour calculer la factorielle"
• "crée une classe Personne avec nom et âge"
• "génère du code pour lire un fichier CSV"

📊 **Traitement de documents :**
• Utilisez les boutons pour traiter des PDF/DOCX
• Glissez-déposez vos fichiers

💻 **Analyse de code :**
• Utilisez le bouton "Process Code" pour analyser vos fichiers

❓ **Questions générales :**
• Posez vos questions en langage naturel
• Je peux vous aider avec la programmation Python

💡 **Conseils :**
• Soyez spécifique dans vos demandes
• N'hésitez pas à demander des exemples
• Utilisez "aide" pour revoir cette aide"""

    def _generate_fallback_response(self, text: str) -> str:
        """
        Génère une réponse de fallback en cas d'erreur du modèle principal

        Args:
            text: Texte de l'utilisateur

        Returns:
            Réponse de fallback naturelle
        """
        text_lower = text.lower()

        # Salutations
        if any(
            word in text_lower
            for word in ["salut", "bonjour", "hello", "hi", "bonsoir"]
        ):
            return "Salut ! Comment ça va ? En quoi puis-je t'aider ?"

        # Questions d'aide
        if "help" in text_lower or "aide" in text_lower:
            return "Je peux t'aider avec la génération de code Python, l'analyse de documents, et répondre à tes questions techniques. Que veux-tu faire ?"

        # Demandes de code
        elif (
            "génér" in text_lower
            or "créer" in text_lower
            or "fonction" in text_lower
            or "classe" in text_lower
        ):
            if "fonction" in text_lower:
                return self.code_generator.generate_simple_function(text)
            elif "classe" in text_lower:
                return self.code_generator.generate_simple_class(text)
            else:
                return "Je peux générer du code pour toi ! Tu veux une fonction ou une classe ? Dis-moi ce que tu veux créer."

        # Questions sur l'IA
        elif any(
            phrase in text_lower
            for phrase in ["qui es-tu", "que fais-tu", "qu'est-ce que tu fais"]
        ):
            return "Je suis ton assistant IA local. Je peux coder, analyser des documents et répondre à tes questions. Qu'est-ce qui t'intéresse ?"

        # Réponse générale naturelle
        else:
            return "Je vois ! Et en quoi puis-je t'aider avec ça ? Tu veux que je génère du code, que je t'explique quelque chose, ou autre chose ?"

    async def process_message(self, message: str) -> str:
        """
        Traite un message de manière asynchrone

        Args:
            message: Message de l'utilisateur

        Returns:
            Réponse de l'IA
        """
        return self.process_text(message)

    def get_conversation_history(self) -> List[Dict[str, str]]:
        """
        Récupère l'historique de conversation

        Returns:
            Liste des messages
        """
        return self.conversation_manager.get_history()

    def clear_conversation(self):
        """
        Clear the conversation history and memory
        """
        self.conversation_manager.clear()
        self.conversation_memory.clear()

        # Réinitialiser aussi le session_context
        self.session_context = {
            "documents_processed": [],
            "code_files_processed": [],
            "last_document_type": None,
            "current_document": None,
        }

        self.logger.info("Conversation cleared")

    def initialize_llm(self) -> bool:
        """Initialise les modèles LLM - Mode entreprise local uniquement"""
        try:
            # En mode entreprise, nous utilisons uniquement le modèle local
            return hasattr(self, "local_ai") and self.local_ai is not None
        except Exception as e:
            self.logger.error("Erreur initialisation LLM: %s", e)
            return False

    async def process_query(
        self, query: str, context: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Traite une requête utilisateur

        Args:
            query: Question/demande de l'utilisateur
            context: Contexte additionnel (fichiers, historique, etc.)

        Returns:
            Réponse structurée de l'IA
        """
        try:
            self.logger.info("Traitement de la requête: %s...", query[:100])
            print(f"[AIEngine] Appel FAQ pour: '{query}' (async)")
            # 1. Tenter la FAQ ML d'abord
            response_ml = None
            if hasattr(self, "ml_ai") and self.ml_ai is not None:
                try:
                    response_ml = self.ml_ai.predict(query)
                    self.logger.info("ML model response: %s...", str(response_ml)[:50])
                except Exception as e:
                    self.logger.warning("Erreur modèle ML: %s", e)
            if response_ml is not None and str(response_ml).strip():
                # On sauvegarde l'échange
                try:
                    self.conversation_manager.add_exchange(
                        query, {"message": response_ml}
                    )
                except Exception:
                    self.logger.warning(
                        "Impossible de sauvegarder la conversation (FAQ async)"
                    )
                return {"type": "faq", "message": response_ml, "success": True}

            # 2. Sinon, routage normal
            # Analyse de la requête
            query_type = self._analyze_query_type(query)
            # Préparation du contexte
            full_context = self._prepare_context(query, context)
            # Traitement selon le type
            if query_type == "web_search":
                response = await self._handle_web_search(query)
            elif query_type == "conversation":
                response = await self._handle_conversation(query, full_context)
            elif query_type == "file_processing":
                response = await self._handle_file_processing(query, full_context)
            elif query_type == "code_generation":
                response = await self._handle_code_generation(query)
            elif query_type == "document_generation":
                response = await self._handle_document_generation(query, full_context)
            else:
                response = await self._handle_general_query(query, full_context)
            # Sauvegarde dans l'historique
            self.conversation_manager.add_exchange(query, response)
            return response
        except Exception as e:
            self.logger.error("Erreur lors du traitement: %s", e)
            return {
                "type": "error",
                "message": f"Désolé, une erreur s'est produite: {str(e)}",
                "success": False,
            }

    def _analyze_query_type(self, query: str) -> str:
        """
        Analyse le type de requête

        Args:
            query: Requête utilisateur

        Returns:
            Type de requête identifié
        """
        query_lower = query.lower()

        # PRIORITÉ 1 : Vérifier d'abord les questions d'identité/capacités (AVANT documents)
        identity_keywords = [
            "qui es-tu",
            "qui es tu",
            "qui êtes vous",
            "comment tu t'appelles",
            "ton nom",
            "tu es qui",
            "tu es quoi",
            "présente toi",
            "presente toi",
            "présentez vous",
            "présentez-vous",
            "vous êtes qui",
            "vous êtes quoi",
            "ton identité",
            "votre identité",
            "c'est quoi ton nom",
            "c'est quoi votre nom",
        ]
        capability_keywords = [
            "que peux tu",
            "que sais tu",
            "tes capacités",
            "tu peux faire",
            "que fais-tu",
            "comment vas tu",
            "comment ça va",
        ]

        if any(
            keyword in query_lower
            for keyword in identity_keywords + capability_keywords
        ):
            return "conversation"  # Questions sur l'IA elle-même

        # PRIORITÉ 2 : Vérifier si c'est un texte incompréhensible/aléatoire
        if len(query_lower) > 20 and not any(c.isspace() for c in query_lower[:20]):
            # Si plus de 20 caractères sans espaces = probablement du charabia
            return "conversation"

        # PRIORITÉ 2.5 : Questions factuelles ou de recherche web
        web_keywords = [
            "combien",
            "population",
            "habitants",
            "nombre",
            "statistiques",
            "chiffre",
            "prix",
            "coût",
            "taille",
            "poids",
            "année",
            "date",
        ]
        if any(keyword in query_lower for keyword in web_keywords):
            return "web_search"

        # PRIORITÉ 3 : Vérifier si on a des documents et si la question les concerne SPÉCIFIQUEMENT
        if hasattr(self.local_ai, "conversation_memory"):
            stored_docs = self.local_ai.conversation_memory.get_document_content()
            if stored_docs:
                # Mots-clés SPÉCIFIQUES pour questions sur les documents
                doc_question_keywords = [
                    "résume",
                    "explique",
                    "analyse",
                    "qu'est-ce que",
                    "que dit",
                    "contenu",
                    "parle",
                    "traite",
                    "sujet",
                    "doc",
                    "document",
                    "pdf",
                    "docx",
                    "fichier",
                    "code",
                ]
                if any(keyword in query_lower for keyword in doc_question_keywords):
                    return "file_processing"

        # PRIORITÉ 4 : Mots-clés pour la génération de code (NOUVEAU code, pas analyse)
        # Distinguer entre questions théoriques et demandes de génération
        question_words = [
            "comment",
            "qu'est-ce que",
            "c'est quoi",
            "que signifie",
            "explique",
            "expliquer",
        ]
        is_theoretical_question = any(qword in query_lower for qword in question_words)

        code_generation_keywords = [
            "génère",
            "crée",
            "écris",
            "développe",
            "programme",
            "script",
            "fonction",
            "classe",
        ]

        if any(keyword in query_lower for keyword in code_generation_keywords):
            # Si c'est une question théorique (ex: "comment créer une liste ?"), laisser le CustomAIModel s'en occuper
            if is_theoretical_question:
                return "general"  # Laisser le CustomAIModel traiter
            else:
                return "code_generation"  # Vraie demande de génération

        # PRIORITÉ 5 : Mots-clés pour la génération de documents
        doc_keywords = ["créer", "générer", "rapport", "rédiger", "documenter"]
        if any(keyword in query_lower for keyword in doc_keywords):
            return "document_generation"

        return "conversation"

    def _prepare_context(self, query: str, context: Optional[Dict]) -> Dict[str, Any]:
        """
        Prépare le contexte complet pour la requête
        """
        full_context = {
            "query": query,
            "conversation_history": self.conversation_manager.get_recent_history(),
            "timestamp": self.file_manager.get_timestamp(),
            "user_context": context or {},
        }

        # Ajouter les documents stockés dans la mémoire
        if hasattr(self.local_ai, "conversation_memory"):
            stored_docs = self.local_ai.conversation_memory.stored_documents
            if stored_docs:
                full_context["stored_documents"] = stored_docs
                full_context["document_order"] = (
                    self.local_ai.conversation_memory.document_order
                )
                self.logger.info(
                    "Contexte enrichi avec %d documents stockés", len(stored_docs)
                )

        return full_context

    async def _handle_conversation(self, query: str, context: Dict) -> Dict[str, Any]:
        """
        Gère les conversations générales
        """
        try:
            # Si on a des documents, les inclure dans le contexte
            prompt = query
            if "stored_documents" in context and context["stored_documents"]:
                prompt = """Contexte des documents disponibles:
                
"""
                for doc_name in context["stored_documents"].keys():
                    prompt += f"- {doc_name}\n"

                prompt += f"\nQuestion: {query}\n\nRéponds en tenant compte du contexte si pertinent."

            response = self.local_ai.generate_response(prompt)

            return {"type": "conversation", "message": response, "success": True}
        except Exception as e:
            self.logger.error("Erreur conversation: %s", e)
            return {
                "type": "conversation",
                "message": f"Erreur lors de la conversation: {str(e)}",
                "success": False,
            }

    async def _handle_file_processing(
        self, query: str, context: Dict
    ) -> Dict[str, Any]:
        """
        Gère le traitement de fichiers et questions sur les documents - VERSION CORRIGÉE
        """
        try:
            query_lower = query.lower()

            # Récupérer les documents disponibles
            all_docs = context.get("stored_documents", {})
            document_order = context.get("document_order", [])

            # NOUVELLE LOGIQUE : Détecter le type de document demandé VS disponible
            requested_type = self._detect_requested_document_type(query_lower)
            available_types = self._get_available_document_types(all_docs)

            print(f"[DEBUG] Type demandé: {requested_type}")
            print(f"[DEBUG] Types disponibles: {available_types}")

            # VÉRIFICATION DE COHÉRENCE
            if requested_type and requested_type not in available_types:
                return self._generate_type_mismatch_response(
                    requested_type, available_types, all_docs
                )

            # Déterminer le document cible selon le type demandé
            target_document = None

            if requested_type:
                # Chercher un document du type demandé
                target_document = self._find_document_by_type(
                    all_docs, document_order, requested_type
                )

            # Gestion des références numériques (premier, deuxième, etc.)
            is_first_requested = any(
                term in query_lower
                for term in ["premier", "1er", "1ère", "première", "document 1", "le 1"]
            )
            is_second_requested = any(
                term in query_lower
                for term in [
                    "deuxième",
                    "2ème",
                    "2eme",
                    "seconde",
                    "document 2",
                    "le 2",
                ]
            )
            is_last_requested = any(
                term in query_lower for term in ["dernier", "dernière", "last"]
            )

            if is_first_requested and len(document_order) >= 1:
                target_document = document_order[0]
            elif is_second_requested and len(document_order) >= 2:
                target_document = document_order[1]
            elif is_last_requested and document_order:
                target_document = document_order[-1]

            # Si aucun document spécifique trouvé, prendre le plus récent
            if not target_document and document_order:
                target_document = document_order[-1]

            # Traitement spécial pour les fichiers Python (explication détaillée)
            if target_document and target_document.lower().endswith(".py"):
                if any(word in query_lower for word in ["explique", "analyse", "code"]):
                    return self._handle_python_code_explanation(
                        target_document, all_docs
                    )

            # Traitement standard pour les autres documents
            if target_document and target_document in all_docs:
                doc_data = all_docs[target_document]
                doc_content = (
                    doc_data.get("content")
                    if isinstance(doc_data, dict)
                    else str(doc_data)
                )

                if doc_content:
                    # Générer le résumé approprié selon le type de document
                    doc_type = self._determine_document_type(target_document)

                    # Déléguer la création du résumé au modèle IA local
                    response = self.local_ai.create_document_summary(
                        doc_content, target_document, doc_type
                    )

                    return {
                        "type": "file_processing",
                        "message": response,
                        "success": True,
                    }

            return {
                "type": "file_processing",
                "message": "Aucun document approprié trouvé pour traiter votre demande.",
                "success": False,
            }

        except Exception as e:
            print(f"❌ Erreur traitement fichier: {e}")
            return {
                "type": "file_processing",
                "message": f"Erreur lors du traitement : {str(e)}",
                "success": False,
            }

    def _detect_requested_document_type(self, query_lower: str) -> Optional[str]:
        """
        Détecte le type de document spécifiquement demandé dans la requête

        Returns:
            'pdf', 'docx', 'code', ou None si pas spécifique
        """
        # Détection PDF
        if any(term in query_lower for term in ["pdf", "le pdf", "du pdf", "ce pdf"]):
            return "pdf"

        # Détection DOCX/Word
        if any(
            term in query_lower
            for term in [
                "docx",
                "doc",
                "word",
                "le docx",
                "du docx",
                "le doc",
                "du doc",
            ]
        ):
            return "docx"

        # Détection Code
        if any(
            term in query_lower
            for term in [
                "code",
                "py",
                "python",
                "script",
                "programme",
                "le code",
                "du code",
            ]
        ):
            return "code"

        return None

    def _get_available_document_types(self, all_docs: Dict) -> List[str]:
        """
        Détermine les types de documents disponibles

        Returns:
            Liste des types disponibles: ['pdf', 'docx', 'code']
        """
        available_types = []

        for doc_name, doc_data in all_docs.items():
            doc_type = self._determine_document_type(doc_name, doc_data)
            if doc_type not in available_types:
                available_types.append(doc_type)

        return available_types

    def _determine_document_type(self, doc_name: str, doc_data: Any = None) -> str:
        """
        Détermine le type d'un document

        Returns:
            'pdf', 'docx', ou 'code'
        """
        doc_name_lower = doc_name.lower()

        if doc_name_lower.endswith(".pdf"):
            return "pdf"
        elif doc_name_lower.endswith((".docx", ".doc")):
            return "docx"
        elif doc_name_lower.endswith(
            (".py", ".js", ".html", ".css", ".java", ".cpp", ".c")
        ):
            return "code"
        elif isinstance(doc_data, dict) and doc_data.get("type") == "code":
            return "code"
        else:
            # Par défaut, considérer comme document texte
            return "docx"

    def _find_document_by_type(
        self, all_docs: Dict, document_order: List, requested_type: str
    ) -> Optional[str]:
        """
        Trouve un document du type demandé

        Returns:
            Nom du document trouvé ou None
        """
        # Chercher dans l'ordre inverse (le plus récent en premier)
        for doc_name in reversed(document_order):
            if doc_name in all_docs:
                doc_type = self._determine_document_type(doc_name, all_docs[doc_name])
                if doc_type == requested_type:
                    return doc_name

        return None

    def _generate_type_mismatch_response(
        self, requested_type: str, available_types: List[str], all_docs: Dict
    ) -> Dict[str, Any]:
        """
        Génère une réponse quand le type demandé n'est pas disponible
        """
        # Mappage pour un langage plus naturel
        type_names = {
            "pdf": "fichier PDF",
            "docx": "document Word/DOCX",
            "code": "fichier de code",
        }

        requested_name = type_names.get(requested_type, requested_type)

        # Construire la liste des documents disponibles
        available_docs = []
        for doc_name in all_docs.keys():
            doc_type = self._determine_document_type(doc_name, all_docs[doc_name])
            type_name = type_names.get(doc_type, doc_type)
            available_docs.append(f"• **{doc_name}** ({type_name})")

        response = "❌ **Document non trouvé**\n\n"
        response += f"Vous demandez l'analyse d'un **{requested_name}**, mais je n'ai pas ce type de document en mémoire.\n\n"

        if available_docs:
            response += "📁 **Documents actuellement disponibles :**\n"
            response += "\n".join(available_docs)
            response += "\n\n💡 **Suggestion :** Reformulez votre demande en utilisant le bon type :\n"

            if "pdf" in available_types:
                response += '• "résume le PDF" ou "explique le PDF"\n'
            if "docx" in available_types:
                response += '• "résume le DOCX" ou "explique le document"\n'
            if "code" in available_types:
                response += '• "explique le code" ou "analyse le Python"\n'
        else:
            response += "Aucun document n'est actuellement en mémoire."

        return {"type": "file_processing", "message": response, "success": False}

    def _handle_python_code_explanation(
        self, target_document: str, all_docs: Dict
    ) -> Dict[str, Any]:
        """
        Gère l'explication détaillée des fichiers Python
        """
        try:
            doc_data = all_docs.get(target_document, {})
            doc_content = (
                doc_data.get("content") if isinstance(doc_data, dict) else str(doc_data)
            )

            if not doc_content:
                return {
                    "type": "file_processing",
                    "message": f"Le fichier {target_document} semble vide.",
                    "success": False,
                }

            # Créer un fichier temporaire pour l'analyse
            with tempfile.NamedTemporaryFile(
                "w", delete=False, suffix=".py", encoding="utf-8"
            ) as tmpf:
                tmpf.write(doc_content)
                tmp_path = tmpf.name

            try:
                # Utiliser le code_processor pour l'explication détaillée
                explanation = self.code_processor.generate_detailed_explanation(
                    tmp_path, real_file_name=os.path.basename(target_document)
                )

                return {
                    "type": "file_processing",
                    "message": explanation,
                    "success": True,
                }

            finally:
                # Nettoyer le fichier temporaire
                try:
                    os.remove(tmp_path)
                except Exception:
                    pass

        except Exception as e:
            return {
                "type": "file_processing",
                "message": f"Erreur lors de l'explication du code : {str(e)}",
                "success": False,
            }

    async def _handle_web_search(self, query: str) -> Dict[str, Any]:
        """
        Gère les requêtes de recherche web factuelle
        """
        try:
            search_engine = InternetSearchEngine()
            summary = search_engine.search_and_summarize(query)
            return {"type": "web_search", "message": summary, "success": True}
        except Exception as e:
            self.logger.error("Erreur recherche web: %s", e)
            return {
                "type": "web_search",
                "message": f"Erreur lors de la recherche web: {str(e)}",
                "success": False,
            }

    async def _handle_code_generation(self, query: str) -> Dict[str, Any]:
        """
        Gère la génération de code avec Ollama ou recherche web
        """
        try:
            query_lower = query.lower()
            language = self._detect_code_language(query)

            # 🆕 PRIORITÉ 0: Détection "génère moi un fichier..." -> Utiliser CodeGenerator avec Ollama
            file_keywords = [
                "génère moi un fichier",
                "crée moi un fichier",
                "génère un fichier",
                "crée un fichier",
            ]
            if any(keyword in query_lower for keyword in file_keywords):
                try:
                    self.logger.info("🔧 Détection génération de fichier avec Ollama")

                    # Utiliser le générateur Ollama déjà initialisé
                    result = await self.ollama_code_generator.generate_file(query)

                    if result.get("success"):
                        code = result.get("code", "")
                        filename = result.get("filename", "generated_file")
                        file_path = result.get("file_path", "")

                        return {
                            "type": "file_generation",  # Type spécial pour GUI
                            "code": code,
                            "message": f"Voici votre fichier : {filename}",
                            "filename": filename,
                            "file_path": file_path,
                            "source": "Ollama (Génération locale)",
                            "success": True,
                            "is_file_download": True,  # Flag pour l'interface
                        }
                    else:
                        error_msg = result.get("error", "Erreur inconnue")
                        self.logger.warning("Échec génération fichier: %s", error_msg)
                        # Continuer vers le fallback

                except Exception as e:
                    self.logger.warning("Erreur génération fichier avec Ollama: %s", e)
                    # Continuer vers le fallback

            # 🌐 PRIORITÉ 1: Recherche web PURE sans templates pré-codés
            try:
                web_result = await self.code_generator.generate_code_from_web(
                    query, language
                )

                if web_result.get("success"):
                    code = web_result.get("code", "")
                    explanation = web_result.get("explanation", "")
                    source = web_result.get("source", "Recherche Web")
                    url = web_result.get("url", "")

                    # Formater la réponse avec source
                    source_info = f" ([Source]({url}))" if url else ""

                    self.logger.info("✅ Code trouvé sur le web: %s", source)
                    return {
                        "type": "code_generation",
                        "code": code,
                        "message": f"🌐 **Code trouvé sur {source}**{source_info}\n\n```{language}\n{code}\n```\n\n💬 **Explication:** {explanation}",
                        "source": source,
                        "url": url,
                        "rating": web_result.get("rating", 4.0),
                        "success": True,
                    }
                else:
                    self.logger.warning(
                        "Recherche web échouée: %s",
                        web_result.get("error", "Erreur inconnue"),
                    )

            except Exception as e:
                self.logger.warning("Générateur web pur indisponible: %s", e)

            # 🔄 FALLBACK 1: Système de recherche web intelligent (avec cache)
            try:
                web_results = await search_smart_code(query, language, max_results=3)

                if web_results and len(web_results) > 0:
                    best_result = web_results[0]

                    # Vérifier la pertinence
                    if best_result.relevance_score > 0.4:  # Seuil plus permissif
                        sources_info = "\n".join(
                            [
                                f"• {result.title} ({result.source_name})"
                                for result in web_results[:2]
                            ]
                        )

                        return {
                            "type": "code_generation",
                            "code": best_result.code,
                            "message": f"🌐 **Code trouvé sur le web:**\n{sources_info}\n\n```{language}\n{best_result.code}\n```\n\n💬 **Source:** {best_result.description}",
                            "sources": [
                                {
                                    "title": r.title,
                                    "url": r.source_url,
                                    "source": r.source_name,
                                }
                                for r in web_results
                            ],
                            "rating": best_result.rating,
                            "success": True,
                        }

            except Exception as e:
                self.logger.warning("Recherche web intelligente échouée: %s", e)

            # 🔧 FALLBACK 2: Générateur local spécialisé MINIMAL (sans templates complexes)
            local_code = self._generate_minimal_code(query, language)

            if local_code and len(local_code.strip()) > 30:
                return {
                    "type": "code_generation",
                    "code": local_code,
                    "message": f"🛠️ **Code généré localement (recherche web échouée):**\n\n```{language}\n{local_code}\n```\n\n💬 **Note:** Solution basique créée car aucune solution trouvée sur le web.",
                    "source": "Générateur local minimal",
                    "rating": 2.5,
                    "success": True,
                }

            # 🚨 ÉCHEC TOTAL
            return {
                "type": "code_generation",
                "message": f'❌ **Impossible de trouver du code pour:** "{query}"\n\n🔍 **Recherches effectuées:**\n• GitHub, Stack Overflow, GeeksforGeeks\n• Recherche Google générale\n\n💡 **Suggestions:**\n• Reformulez votre demande (ex: "fonction Python qui trie une liste")\n• Précisez le langage (Python, JavaScript, etc.)\n• Décrivez ce que la fonction doit faire exactement',
                "success": False,
            }

        except Exception as e:
            self.logger.error("Erreur génération code: %s", e)
            return {
                "type": "code_generation",
                "message": f"❌ Erreur lors de la recherche de code: {str(e)}",
                "success": False,
            }

    async def _handle_document_generation(
        self, query: str, context: Dict
    ) -> Dict[str, Any]:
        """
        Gère la génération de documents
        """
        try:
            # Générer le document sans await (methode sync)
            document = self.document_generator.generate_document(query, context)

            return {
                "type": "document_generation",
                "document": document,
                "message": "Document généré avec succès",
                "success": True,
            }
        except Exception as e:
            self.logger.error("Erreur génération document: %s", e)
            return {
                "type": "document_generation",
                "message": f"Erreur lors de la génération de document: {str(e)}",
                "success": False,
            }

    async def _handle_general_query(self, query: str, context: Dict) -> Dict[str, Any]:
        """
        Gère les requêtes générales
        """
        try:
            # Construire le prompt avec contexte si disponible
            prompt = query
            if "stored_documents" in context and context["stored_documents"]:
                prompt = """Contexte des documents disponibles:
                
"""
                for doc_name in context["stored_documents"].keys():
                    prompt += f"- {doc_name}\n"

                prompt += f"\nQuestion: {query}\n\nRéponds en tenant compte du contexte si pertinent."

            response = self.local_ai.generate_response(prompt)

            return {"type": "general", "message": response, "success": True}
        except Exception as e:
            self.logger.error("Erreur requête générale: %s", e)
            return {
                "type": "general",
                "message": f"Erreur lors du traitement: {str(e)}",
                "success": False,
            }

    def _detect_code_language(self, query: str) -> str:
        """Détecte le langage de programmation demandé"""
        query_lower = query.lower()

        if any(word in query_lower for word in ["python", "py"]):
            return "python"
        elif any(word in query_lower for word in ["javascript", "js", "node"]):
            return "javascript"
        elif any(word in query_lower for word in ["html", "page web", "site"]):
            return "html"
        elif any(word in query_lower for word in ["css", "style"]):
            return "css"
        else:
            return "python"  # Par défaut

    def _create_code_accompaniment(self, query: str, language: str) -> str:
        """Crée un message d'accompagnement intelligent pour le code"""
        query_lower = query.lower()

        # Messages spécifiques selon le type de code demandé
        if any(word in query_lower for word in ["factorielle", "factorial"]):
            return f"🔢 **Code pour calculer une factorielle en {language.capitalize()}**\n\nVoici une implémentation efficace avec gestion des cas d'erreur :"

        elif any(word in query_lower for word in ["hello", "world", "bonjour"]):
            return f"👋 **Programme Hello World en {language.capitalize()}**\n\nLe classique pour débuter :"

        elif any(word in query_lower for word in ["fibonacci", "fibo"]):
            return f"🌀 **Séquence de Fibonacci en {language.capitalize()}**\n\nCode optimisé pour générer la suite :"

        elif any(word in query_lower for word in ["tri", "sort", "trier"]):
            return f"📊 **Algorithme de tri en {language.capitalize()}**\n\nImplémentation d'un tri efficace :"

        elif any(word in query_lower for word in ["classe", "class", "objet"]):
            return (
                f"🏗️ **Classe en {language.capitalize()}**\n\nStructure orientée objet :"
            )

        elif any(word in query_lower for word in ["fonction", "function", "def"]):
            return f"⚙️ **Fonction en {language.capitalize()}**\n\nCode modulaire et réutilisable :"

        elif any(word in query_lower for word in ["api", "web", "serveur"]):
            return f"🌐 **Code pour API/Web en {language.capitalize()}**\n\nStructure pour service web :"

        else:
            return f"💻 **Code généré en {language.capitalize()}**\n\nVoici une implémentation pour votre demande :"

    def _enhance_web_solution(self, web_solution, query: str, language: str) -> str:
        """
        Améliore une solution trouvée sur le web en l'adaptant à la demande précise
        """
        base_code = web_solution.code
        query_lower = query.lower()

        # Ajouts intelligents basés sur la demande
        enhanced_code = base_code

        # Ajouter des commentaires explicatifs si manquants
        if not any(
            line.strip().startswith("#")
            or line.strip().startswith("//")
            or line.strip().startswith("/*")
            for line in base_code.split("\n")
        ):
            if language.lower() == "python":
                enhanced_code = f'"""\n{web_solution.title}\nSolution adaptée pour: {query}\n"""\n\n{base_code}'
            elif language.lower() in ["javascript", "js"]:
                enhanced_code = f"/**\n * {web_solution.title}\n * Solution adaptée pour: {query}\n */\n\n{base_code}"

        # Ajout de gestion d'erreurs si nécessaire
        if (
            "error" not in base_code.lower()
            and "try" not in base_code.lower()
            and "except" not in base_code.lower()
        ):
            if language.lower() == "python" and len(base_code.split("\n")) > 5:
                if "def " in base_code:
                    # Wrapper avec try/except pour les fonctions
                    enhanced_code = (
                        enhanced_code.replace("def ", "def ")
                        + '\n\n# Exemple d\'usage sécurisé:\n# try:\n#     result = votre_fonction()\n# except Exception as e:\n#     print(f"Erreur: {e}")'
                    )

        # Ajout d'exemples d'usage si manquants
        if "example" not in base_code.lower() and "test" not in base_code.lower():
            if language.lower() == "python":
                enhanced_code += '\n\n# Exemple d\'utilisation:\nif __name__ == "__main__":\n    # Testez votre code ici\n    pass'

        # Optimisations spécifiques par type de demande
        if any(word in query_lower for word in ["api", "web", "http"]):
            if language.lower() == "python" and "requests" not in base_code:
                enhanced_code = "import requests\n" + enhanced_code

        if any(word in query_lower for word in ["file", "fichier", "csv", "json"]):
            if language.lower() == "python" and "with open" not in base_code:
                enhanced_code += (
                    "\n\n# Gestion sécurisée des fichiers avec context manager"
                )

        return enhanced_code

    def _validate_solution_relevance(self, solution, query: str, language: str) -> bool:
        """
        Valide strictement la pertinence d'une solution web par rapport à la demande
        """
        code_lower = solution.code.lower()
        query_lower = query.lower()

        # 1. Vérifier que le code contient les concepts clés de la requête
        key_concepts = self._extract_query_concepts(query_lower)

        if not key_concepts:
            return False

        # 2. Score de pertinence basé sur les concepts présents dans le code
        concept_matches = 0
        for concept in key_concepts:
            if concept in code_lower:
                concept_matches += 1

        relevance_score = concept_matches / len(key_concepts)

        # 3. Vérifications spécifiques selon le type de demande
        specific_checks = self._perform_specific_validation(
            code_lower, query_lower, language
        )

        # 4. Score final : au moins 70% de pertinence + validations spécifiques
        is_relevant = relevance_score >= 0.7 and specific_checks

        print(
            f"[VALIDATION] Query: '{query[:30]}...' | Score: {relevance_score:.2f} | Spécific: {specific_checks} | Result: {is_relevant}"
        )

        return is_relevant

    def _extract_query_concepts(self, query_lower: str) -> list:
        """Extrait les concepts clés de la requête"""
        concept_mapping = {
            "concat": [
                "concat",
                "concatén",
                "join",
                "joindre",
                "combiner",
                "fusionner",
            ],
            "string": ["string", "chaîne", "chaine", "caractère", "str", "texte"],
            "function": ["fonction", "function", "def"],
            "sort": ["tri", "trier", "sort", "order", "ordonner"],
            "file": ["fichier", "file", "lire", "read", "écrire", "write"],
            "api": ["api", "rest", "endpoint", "requête", "request"],
            "class": ["classe", "class", "objet", "object"],
            "array": ["liste", "array", "list", "tableau"],
            "loop": ["boucle", "loop", "for", "while", "itération"],
        }

        concepts = []
        for main_concept, variations in concept_mapping.items():
            if any(var in query_lower for var in variations):
                concepts.append(main_concept)

        return concepts

    def _perform_specific_validation(
        self, code_lower: str, query_lower: str, language: str
    ) -> bool:
        """Effectue des validations spécifiques selon le type de demande"""

        # Validation pour les fonctions de concaténation
        if "concat" in query_lower or "concatén" in query_lower:
            concat_indicators = [
                "+",
                "join()",
                ".join",
                "concat",
                "format",
                'f"',
                "f'",
                "%s",
            ]
            return any(indicator in code_lower for indicator in concat_indicators)

        # Validation pour les fonctions de tri
        if "tri" in query_lower or "sort" in query_lower:
            sort_indicators = ["sort", "sorted", "key=", "reverse=", "lambda", "order"]
            return any(indicator in code_lower for indicator in sort_indicators)

        # Validation pour la lecture de fichiers
        if "fichier" in query_lower or "file" in query_lower:
            file_indicators = ["open(", "with open", "read()", "write()", "close()"]
            return any(indicator in code_lower for indicator in file_indicators)

        # Validation pour les API
        if "api" in query_lower:
            api_indicators = [
                "request",
                "response",
                "json",
                "get(",
                "post(",
                "flask",
                "fastapi",
            ]
            return any(indicator in code_lower for indicator in api_indicators)

        # Validation pour les classes
        if "classe" in query_lower or "class" in query_lower:
            class_indicators = ["class ", "__init__", "self.", "def "]
            return any(indicator in code_lower for indicator in class_indicators)

        # Validation générale : au moins une structure de code Python valide
        if language.lower() == "python":
            python_indicators = [
                "def ",
                "class ",
                "import ",
                "for ",
                "if ",
                "return",
                "print(",
            ]
            return any(indicator in code_lower for indicator in python_indicators)

        return True  # Pas de validation spécifique, accepter

    def _generate_smart_local_code(self, query: str, language: str) -> str:
        """
        Génère du code local intelligent basé sur des patterns reconnus
        """
        query_lower = query.lower()

        # Template pour concaténation de chaînes
        if (
            "concat" in query_lower
            and "string" in query_lower
            or "chaîne" in query_lower
        ):
            return self._generate_string_concat_code(language)

        # Template pour fonction de tri
        elif "tri" in query_lower or "sort" in query_lower:
            return self._generate_sort_code(language)

        # Template pour lecture de fichier
        elif "fichier" in query_lower or "file" in query_lower:
            return self._generate_file_code(language)

        # Template pour classe basique
        elif "classe" in query_lower or "class" in query_lower:
            return self._generate_class_code(language)

        # Template pour API simple
        elif "api" in query_lower:
            return self._generate_api_code(language)

        return ""  # Aucun template trouvé

    def _generate_string_concat_code(self, language: str) -> str:
        """Génère du code de concaténation de chaînes"""
        if language.lower() == "python":
            return '''def concat_strings(*strings):
    """
    Concatène plusieurs chaînes de caractères

    Args:
        *strings: Chaînes à concaténer

    Returns:
        str: Chaîne concaténée
    """
    return ''.join(str(s) for s in strings)

def concat_with_separator(separator, *strings):
    """
    Concatène des chaînes avec un séparateur

    Args:
        separator (str): Séparateur à utiliser
        *strings: Chaînes à concaténer

    Returns:
        str: Chaîne concaténée avec séparateur
    """
    return separator.join(str(s) for s in strings)

# Exemples d'utilisation
if __name__ == "__main__":
    # Concaténation simple
    result1 = concat_strings("Hello", " ", "World", "!")
    print(f"Résultat 1: {result1}")  # Hello World!

    # Concaténation avec séparateur
    result2 = concat_with_separator(" - ", "Pierre", "Paul", "Jacques")
    print(f"Résultat 2: {result2}")  # Pierre - Paul - Jacques

    # Méthodes alternatives Python
    str1, str2, str3 = "Hello", "World", "!"

    # Méthode 1: Opérateur +
    concat1 = str1 + " " + str2 + str3

    # Méthode 2: f-string (recommandé)
    concat2 = f"{str1} {str2}{str3}"

    # Méthode 3: join()
    concat3 = " ".join([str1, str2]) + str3

    print(f"Méthode +: {concat1}")
    print(f"Méthode f-string: {concat2}")
    print(f"Méthode join: {concat3}")'''

        elif language.lower() == "javascript":
            return """function concatStrings(...strings) {
    /**
     * Concatène plusieurs chaînes de caractères
     * @param {...string} strings - Chaînes à concaténer
     * @returns {string} Chaîne concaténée
     */
    return strings.join('');
}

function concatWithSeparator(separator, ...strings) {
    /**
     * Concatène des chaînes avec un séparateur
     * @param {string} separator - Séparateur à utiliser
     * @param {...string} strings - Chaînes à concaténer
     * @returns {string} Chaîne concaténée avec séparateur
     */
    return strings.join(separator);
}

// Exemples d'utilisation
const result1 = concatStrings("Hello", " ", "World", "!");
console.log("Résultat 1:", result1); // Hello World!

const result2 = concatWithSeparator(" - ", "Pierre", "Paul", "Jacques");
console.log("Résultat 2:", result2); // Pierre - Paul - Jacques

// Méthodes alternatives JavaScript
const str1 = "Hello", str2 = "World", str3 = "!";

// Méthode 1: Opérateur +
const concat1 = str1 + " " + str2 + str3;

// Méthode 2: Template literals (recommandé)
const concat2 = `${str1} ${str2}${str3}`;

// Méthode 3: concat()
const concat3 = str1.concat(" ", str2, str3);

console.log("Méthode +:", concat1);
console.log("Template literals:", concat2);
console.log("Méthode concat():", concat3);"""

        return ""

    def _generate_sort_code(self, language: str) -> str:
        """Génère du code de tri"""
        if language.lower() == "python":
            return '''def sort_list(items, reverse=False):
    """
    Trie une liste d'éléments

    Args:
        items (list): Liste à trier
        reverse (bool): Tri décroissant si True

    Returns:
        list: Liste triée
    """
    return sorted(items, reverse=reverse)

def sort_by_key(items, key_func, reverse=False):
    """
    Trie une liste selon une fonction clé

    Args:
        items (list): Liste à trier
        key_func (function): Fonction pour extraire la clé
        reverse (bool): Tri décroissant si True

    Returns:
        list: Liste triée
    """
    return sorted(items, key=key_func, reverse=reverse)

# Exemples d'utilisation
if __name__ == "__main__":
    # Tri simple
    numbers = [3, 1, 4, 1, 5, 9, 2, 6]
    sorted_numbers = sort_list(numbers)
    print(f"Nombres triés: {sorted_numbers}")

    # Tri décroissant
    sorted_desc = sort_list(numbers, reverse=True)
    print(f"Tri décroissant: {sorted_desc}")

    # Tri de chaînes
    names = ["Pierre", "Paul", "Alice", "Bob"]
    sorted_names = sort_list(names)
    print(f"Noms triés: {sorted_names}")

    # Tri par longueur
    sorted_by_length = sort_by_key(names, len)
    print(f"Tri par longueur: {sorted_by_length}")

    # Tri d'objets complexes
    people = [
        {"name": "Alice", "age": 30},
        {"name": "Bob", "age": 25},
        {"name": "Charlie", "age": 35}
    ]
    sorted_by_age = sort_by_key(people, lambda x: x["age"])
    print(f"Tri par âge: {sorted_by_age}")'''

        return ""

    def _generate_file_code(self, language: str) -> str:
        """Génère du code de gestion de fichiers"""
        if language.lower() == "python":
            return '''def read_file(file_path, encoding='utf-8'):
    """
    Lit le contenu d'un fichier

    Args:
        file_path (str): Chemin vers le fichier
        encoding (str): Encodage du fichier

    Returns:
        str: Contenu du fichier
    """
    try:
        with open(file_path, 'r', encoding=encoding) as file:
            return file.read()
    except FileNotFoundError:
        print(f"Erreur: Fichier '{file_path}' non trouvé")
        return ""
    except Exception as e:
        print(f"Erreur lors de la lecture: {e}")
        return ""

def write_file(file_path, content, encoding='utf-8'):
    """
    Écrit du contenu dans un fichier

    Args:
        file_path (str): Chemin vers le fichier
        content (str): Contenu à écrire
        encoding (str): Encodage du fichier

    Returns:
        bool: True si succès
    """
    try:
        with open(file_path, 'w', encoding=encoding) as file:
            file.write(content)
        return True
    except Exception as e:
        print(f"Erreur lors de l'écriture: {e}")
        return False

# Exemple d'utilisation
if __name__ == "__main__":
    # Écriture d'un fichier test
    test_content = "Hello World!\\nCeci est un test."

    if write_file("test.txt", test_content):
        print("Fichier écrit avec succès")

        # Lecture du fichier
        content = read_file("test.txt")
        print(f"Contenu lu: {content}")
    else:
        print("Erreur lors de l'écriture")'''

        return ""

    def _generate_class_code(self, language: str) -> str:
        """Génère une classe exemple"""
        if language.lower() == "python":
            return '''class User:
    """
    Classe pour représenter un utilisateur
    """

    def __init__(self, name, email, age=None):
        """
        Initialise un nouvel utilisateur

        Args:
            name (str): Nom de l'utilisateur
            email (str): Email de l'utilisateur
            age (int, optional): Âge de l'utilisateur
        """
        self.name = name
        self.email = email
        self.age = age
        self.is_active = True

    def get_info(self):
        """
        Retourne les informations de l'utilisateur

        Returns:
            dict: Informations utilisateur
        """
        return {
            "name": self.name,
            "email": self.email,
            "age": self.age,
            "is_active": self.is_active
        }

    def update_email(self, new_email):
        """
        Met à jour l'email de l'utilisateur

        Args:
            new_email (str): Nouvel email
        """
        self.email = new_email

    def deactivate(self):
        """Désactive l'utilisateur"""
        self.is_active = False

    def __str__(self):
        """Représentation string de l'utilisateur"""
        return f"User(name='{self.name}', email='{self.email}')"

    def __repr__(self):
        """Représentation technique de l'utilisateur"""
        return f"User(name='{self.name}', email='{self.email}', age={self.age})"

# Exemple d'utilisation
if __name__ == "__main__":
    # Créer un utilisateur
    user = User("Alice Dupont", "alice@example.com", 30)

    # Afficher les informations
    print(user)
    print(f"Infos: {user.get_info()}")

    # Modifier l'email
    user.update_email("alice.dupont@newdomain.com")
    print(f"Nouvel email: {user.email}")

    # Désactiver l'utilisateur
    user.deactivate()
    print(f"Utilisateur actif: {user.is_active}")'''

        return ""

    def _generate_api_code(self, language: str) -> str:
        """Génère du code API basique"""
        if language.lower() == "python":
            return '''from flask import Flask, jsonify, request

app = Flask(__name__)

# Base de données simulée
users = [
    {"id": 1, "name": "Alice", "email": "alice@example.com"},
    {"id": 2, "name": "Bob", "email": "bob@example.com"}
]

@app.route('/api/users', methods=['GET'])
def get_users():
    """
    Récupère la liste des utilisateurs

    Returns:
        JSON: Liste des utilisateurs
    """
    return jsonify({"users": users, "count": len(users)})

@app.route('/api/users/<int:user_id>', methods=['GET'])
def get_user(user_id):
    """
    Récupère un utilisateur spécifique

    Args:
        user_id (int): ID de l'utilisateur

    Returns:
        JSON: Utilisateur ou erreur
    """
    user = next((u for u in users if u["id"] == user_id), None)
    if user:
        return jsonify(user)
    return jsonify({"error": "Utilisateur non trouvé"}), 404

@app.route('/api/users', methods=['POST'])
def create_user():
    """
    Crée un nouvel utilisateur

    Returns:
        JSON: Utilisateur créé
    """
    data = request.get_json()

    if not data or 'name' not in data or 'email' not in data:
        return jsonify({"error": "Nom et email requis"}), 400

    new_id = max(u["id"] for u in users) + 1 if users else 1
    new_user = {
        "id": new_id,
        "name": data["name"],
        "email": data["email"]
    }

    users.append(new_user)
    return jsonify(new_user), 201

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)'''

        return ""

    def _generate_minimal_code(self, query: str, language: str) -> str:
        """
        Générateur minimal uniquement si la recherche web échoue complètement
        """
        query_lower = query.lower()

        if language.lower() == "python":
            # Tri alphabétique minimal
            if any(
                word in query_lower for word in ["tri", "sort", "ordre", "alphabétique"]
            ):
                return '''def sort_list(items):
    """Trie une liste par ordre alphabétique"""
    return sorted(items)

# Exemple
words = ["pomme", "banane", "cerise"]
sorted_words = sort_list(words)
print(sorted_words)  # ['banane', 'cerise', 'pomme']'''

            # Conversion majuscules
            elif any(
                word in query_lower for word in ["majuscule", "uppercase", "upper"]
            ):
                return '''def to_uppercase(text):
    """Convertit le texte en majuscules"""
    return text.upper()

# Exemple
result = to_uppercase("hello world")
print(result)  # HELLO WORLD'''

            # Fonction basique
            elif any(word in query_lower for word in ["fonction", "function", "def"]):
                return '''def my_function(parameter):
    """Description de votre fonction"""
    # Votre code ici
    result = parameter
    return result

# Exemple d'utilisation
output = my_function("test")
print(output)'''

        elif language.lower() == "javascript":
            # Tri alphabétique
            if any(
                word in query_lower for word in ["tri", "sort", "ordre", "alphabétique"]
            ):
                return """function sortArray(items) {
    // Trie un tableau par ordre alphabétique
    return items.sort();
}

// Exemple
const words = ["pomme", "banane", "cerise"];
const sortedWords = sortArray([...words]);
console.log(sortedWords); // ["banane", "cerise", "pomme"]"""

            # Fonction basique
            elif any(word in query_lower for word in ["fonction", "function"]):
                return """function myFunction(parameter) {
    // Description de votre fonction
    // Votre code ici
    return parameter;
}

// Exemple d'utilisation
const result = myFunction("test");
console.log(result);"""

        return ""  # Aucun template minimal trouvé

    def get_status(self) -> Dict[str, Any]:
        """
        Retourne le statut du moteur IA
        """
        return {
            "engine": "running",
            "mode": "enterprise_local",
            "llm_status": "local_custom_model_only",
            "conversation_count": (
                len(self.conversation_manager.history)
                if hasattr(self.conversation_manager, "history")
                else 0
            ),
            "local_ai_stats": (
                self.local_ai.get_stats() if hasattr(self.local_ai, "get_stats") else {}
            ),
            "config": self.config,
        }
