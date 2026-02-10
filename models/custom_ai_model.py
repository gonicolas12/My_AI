"""
Modèle IA personnalisé local - Architecture modulaire
Intègre tous les modules pour une IA 100% locale avec mémoire de conversation
"""

import asyncio
import concurrent.futures
import random
import re
import time
from typing import Any, Dict, List, Optional, Tuple

from models.advanced_code_generator import AdvancedCodeGenerator as CodeGenerator
from models.ml_faq_model import MLFAQModel
from processors.code_processor import CodeProcessor
from processors.docx_processor import DOCXProcessor
from processors.pdf_processor import PDFProcessor

try:
    from models.smart_code_searcher import multi_source_searcher
except ImportError:
    multi_source_searcher = None

from .base_ai import BaseAI
from .conversation_memory import ConversationMemory
from .internet_search import InternetSearchEngine
from .knowledge_base import KnowledgeBase
from .linguistic_patterns import LinguisticPatterns
from .local_llm import LocalLLM
from .reasoning_engine import ReasoningEngine

# Import du calculateur intelligent
try:
    from utils.intelligent_calculator import intelligent_calculator

    CALCULATOR_AVAILABLE = True
except ImportError:
    CALCULATOR_AVAILABLE = False
    print("⚠️ Calculateur intelligent non disponible")

# Import du nouveau gestionnaire de mémoire vectorielle
try:
    from memory.vector_memory import VectorMemory

    VECTOR_MEMORY_AVAILABLE = True
except ImportError:
    VECTOR_MEMORY_AVAILABLE = False
    print("⚠️ Mémoire vectorielle non disponible")

# Import de l'analyseur de documents intelligent
try:
    from models.intelligent_document_analyzer import IntelligentDocumentAnalyzer

    INTELLIGENT_ANALYZER_AVAILABLE = True
except ImportError:
    INTELLIGENT_ANALYZER_AVAILABLE = False
    document_analyzer = None
    print("⚠️ Analyseur intelligent non disponible")

# Import des processeurs avancés
try:
    ADVANCED_PROCESSORS_AVAILABLE = True
except ImportError:
    ADVANCED_PROCESSORS_AVAILABLE = False
    print("⚠️ Processeurs avancés non disponibles")

from models.mixins import (
    AdvancedCodeGenMixin,
    ContextManagementMixin,
    ConversationResponseMixin,
    DocumentAnalysisMixin,
    InternetSearchMixin,
    ProgrammingHelpMixin,
)


class CustomAIModel(
    ConversationResponseMixin,
    InternetSearchMixin,
    ProgrammingHelpMixin,
    DocumentAnalysisMixin,
    ContextManagementMixin,
    AdvancedCodeGenMixin,
    BaseAI,
):
    """Modèle IA personnalisé avec architecture modulaire et mémoire persistante"""

    @staticmethod
    def _run_async(coro):
        """Exécute une coroutine depuis un contexte synchrone, de façon robuste.
        
        Gère correctement les cas :
        - Pas d'event loop existant → asyncio.run()
        - Event loop existant mais pas en cours → loop.run_until_complete()
        - Event loop en cours (GUI thread, etc.) → nouveau thread + asyncio.run()
        """
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            # Pas d'event loop en cours — le cas le plus simple
            return asyncio.run(coro)

        # Un event loop tourne déjà (ex: main.py async, tests, etc.)
        # On lance dans un thread séparé pour éviter le deadlock
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            return pool.submit(asyncio.run, coro).result(timeout=60)

    def __init__(self, conversation_memory: ConversationMemory = None):
        super().__init__()
        self.name = "Assistant IA Local"
        self.version = "6.3.0"

        # Modules spécialisés
        self.linguistic_patterns = LinguisticPatterns()
        self.knowledge_base = KnowledgeBase()
        self.code_generator = CodeGenerator()
        self.web_code_searcher = multi_source_searcher
        self.reasoning_engine = ReasoningEngine()
        self.conversation_memory = conversation_memory or ConversationMemory()
        self.internet_search = InternetSearchEngine()
        self.ml_model = MLFAQModel()  # Instance unique, données chargées au 1er predict()

        # Initialisation du LLM Local (Ollama)
        self.local_llm = LocalLLM()

        # Gestionnaire de mémoire vectorielle (remplace million_token_manager)
        if VECTOR_MEMORY_AVAILABLE:
            try:
                self.context_manager = VectorMemory(
                    max_tokens=1_000_000,
                    chunk_size=512,
                    chunk_overlap=50,
                    enable_encryption=False,  # Peut être activé via config
                )
                self.ultra_mode = True
                print("🚀 Mode Ultra avec mémoire vectorielle activé")
            except Exception as e:
                print(f"⚠️ Erreur init VectorMemory: {e}")
                self.context_manager = None
                self.ultra_mode = False
                print("📝 Mode standard activé")
        else:
            self.context_manager = None
            self.ultra_mode = False
            print("📝 Mode standard activé")

        # 🧠 Analyseur de documents intelligent (sans LLM)
        if INTELLIGENT_ANALYZER_AVAILABLE:
            self.document_analyzer = IntelligentDocumentAnalyzer()
            print("🧠 Analyseur de documents intelligent activé")
        else:
            self.document_analyzer = None
            print("⚠️ Analyseur intelligent non disponible")

        # Processeurs avancés
        if ADVANCED_PROCESSORS_AVAILABLE:
            self.pdf_processor = PDFProcessor()
            self.docx_processor = DOCXProcessor()
            self.code_processor = CodeProcessor()
            print("🔧 Processeurs avancés initialisés: PDF, DOCX, Code")
        else:
            self.pdf_processor = None
            self.docx_processor = None
            self.code_processor = None

        # Configuration
        self.confidence_threshold = 0.3
        self.max_response_length = 2000

        # État de la session
        self.session_context = {
            "documents_processed": [],
            "code_files_processed": [],
            "last_document_type": None,
            "current_document": None,
        }

        # Suivi des blagues pour éviter les répétitions
        self.used_jokes = set()  # Index des blagues déjà utilisées
        self.jokes_reset_threshold = 0.8  # Reset quand 80% des blagues sont utilisées
        self.last_joke_intro = (
            None  # Dernière intro de blague utilisée pour éviter répétitions
        )

        # Réponses personnalisées pour l'identité
        self.identity_responses = {
            "basic": [
                "Je suis votre assistant IA local ! Je suis conçu pour vous aider avec la programmation, les questions techniques, et bien plus encore.",
                "Bonjour ! Je suis un assistant IA qui fonctionne entièrement en local sur votre machine. Je peux vous aider avec le code, répondre à vos questions, et discuter avec vous.",
                "Salut ! Moi c'est Assistant IA Local. Je suis votre compagnon virtuel pour la programmation et les discussions techniques. Je tourne uniquement en local, pas besoin d'internet !",
                "Je suis votre assistant personnel ! Un modèle IA local qui peut coder, expliquer, et discuter avec vous. J'apprends de nos conversations pour mieux vous comprendre.",
            ],
            "detailed": [
                "Je suis Assistant IA Local, version 6.3.0 Je suis un modèle d'intelligence artificielle conçu pour fonctionner entièrement en local, sans dépendance externe. Je peux générer du code, expliquer des concepts, et avoir des conversations naturelles avec vous.",
                "Mon nom est Assistant IA Local. Je suis une IA modulaire avec plusieurs spécialisations : génération de code, analyse linguistique, base de connaissances, et raisonnement. Je garde en mémoire nos conversations pour mieux vous comprendre.",
                "Je suis votre assistant IA personnel ! J'ai été conçu avec une architecture modulaire incluant la génération de code, l'analyse linguistique, une base de connaissances, et un moteur de raisonnement. Tout fonctionne en local sur votre machine.",
            ],
            "casual": [
                "Salut ! Moi c'est Assistant IA Local, ton compagnon virtuel pour coder et discuter. Je suis là pour t'aider avec tout ce que tu veux !",
                "Hey ! Je suis ton assistant IA local. Je peux coder, expliquer des trucs, et juste discuter avec toi. J'apprends de nos conversations pour être plus utile.",
                "Coucou ! Je suis Assistant IA Local, ta nouvelle IA de compagnie. On peut coder ensemble, parler de tout et n'importe quoi. Je suis là pour toi !",
            ],
        }

        # Réponses sur les capacités
        self.capabilities_responses = {
            "basic": [
                "Je peux vous aider avec la programmation (Python, JavaScript, HTML/CSS...), expliquer des concepts techniques, générer du code, et avoir des conversations naturelles avec vous.",
                "Mes capacités incluent : génération de code, explication de concepts, analyse de texte, raisonnement logique, et mémorisation de nos conversations pour mieux vous comprendre.",
                "Je suis capable de coder dans plusieurs langages, d'expliquer des concepts techniques, de répondre à vos questions, et de maintenir une conversation fluide en me souvenant de nos échanges.",
            ],
            "detailed": [
                "Mes capacités principales sont :\n- Génération de code (Python, JavaScript, HTML/CSS, etc.)\n- Explication de concepts techniques\n- Analyse linguistique et détection d'intentions\n- Raisonnement logique et résolution de problèmes\n- Mémoire de conversation persistante\n- Fonctionnement 100% local sans dépendances externes",
                "Je possède plusieurs modules spécialisés :\n• CodeGenerator : pour créer du code dans différents langages\n• KnowledgeBase : pour stocker et récupérer des connaissances\n• LinguisticPatterns : pour comprendre vos messages\n• ReasoningEngine : pour le raisonnement et la logique\n• ConversationMemory : pour mémoriser nos échanges\n\nTout fonctionne en local !",
            ],
        }

        # Stock de blagues
        self.jokes = [
            "Pourquoi les plongeurs plongent-ils toujours en arrière et jamais en avant ? Parce que sinon, ils tombent dans le bateau ! 😄",
            "Que dit un escargot quand il croise une limace ? « Regarde, un nudiste ! » 🐌",
            "Pourquoi les poissons n'aiment pas jouer au tennis ? Parce qu'ils ont peur du filet ! 🐟",
            "Comment appelle-t-on un chat tombé dans un pot de peinture le jour de Noël ? Un chat-mallow ! 🎨",
            "Que dit un informaticien quand il se noie ? F1 ! F1 ! 💻",
            "Pourquoi les programmeurs préfèrent-ils le noir ? Parce que light attire les bugs ! 🐛",
            "Comment appelle-t-on un boomerang qui ne revient pas ? Un bâton ! 🪃",
            "Que dit un café qui arrive en retard au bureau ? « Désolé, j'ai eu un grain ! » ☕",
            "Pourquoi les développeurs détestent-ils la nature ? Parce qu'elle a trop de bugs ! 🌿",
            "Comment appelle-t-on un algorithme qui chante ? Un algo-rythme ! 🎵",
            "Que dit Python quand il rencontre Java ? « Salut, tu veux que je t'indente ? » 🐍",
            "Pourquoi les IA ne racontent jamais de mauvaises blagues ? Parce qu'elles ont un bon sense of humor ! 🤖",
            "Vous avez les cramptés ? QUOICOU... euuuuh nan. APANYAN. Ptit flop comme on dis sur twitt... euh X ! 😄",
            "Pourquoi les ordinateurs n’aiment-ils pas le soleil ? Parce qu’ils préfèrent rester à l’ombre du cloud ! ☁️",
            "Quel est le comble pour un développeur ? De ne pas avoir de classe ! 👨‍💻",
            "Pourquoi les robots n’ont-ils jamais froid ? Parce qu’ils ont des processeurs ! 🤖",
            "Que dit un serveur à un client fatigué ? Tu veux un cookie ? 🍪",
            "Pourquoi le wifi est jaloux du bluetooth ? Parce que le bluetooth a plus de connexions rapprochées ! 📶",
            "Comment appelle-t-on un bug qui danse ? Un buggie ! 🕺",
            "Pourquoi les informaticiens aiment les pizzas ? Parce qu’il y a toujours des parts égales ! 🍕",
            "Que fait un développeur quand il a faim ? Il mange des bytes ! 😋",
            "Pourquoi le codeur a-t-il mis ses lunettes ? Pour mieux voir les exceptions ! 🤓",
            "Comment appelle-t-on un ordinateur qui chante faux ? Un PC-cacophonie ! 🎤",
            "Pourquoi les IA aiment les maths ? Parce qu’elles trouvent ça logique ! ➗",
            "Que dit un fichier corrompu à son ami ? Je ne suis pas dans mon assiette ! 🥴",
            "Pourquoi le clavier est toujours de bonne humeur ? Parce qu’il a plein de touches ! 🎹",
            "Comment appelle-t-on un réseau qui fait du sport ? Un net-working ! 🏋️",
            "Pourquoi les développeurs aiment les ascenseurs ? Parce qu’ils ont des niveaux ! 🛗",
            "Que dit un bug à un autre bug ? On se retrouve dans le log ! 🐞",
            "Pourquoi le serveur est fatigué ? Il a trop de requêtes ! 💤",
            "Comment appelle-t-on un ordinateur qui fait du jardinage ? Un planteur de bits ! 🌱",
        ]

        self.user_preferences = {}  # Mémorisation des préférences utilisateur
        self.conversation_patterns = {}  # Analyse des patterns de conversation
        self.smart_suggestions = []  # Suggestions intelligentes
        self.context_awareness_level = "expert"  # Niveau de conscience contextuelle
        self.response_personality = "genius"  # Personnalité de génie

        # Compteurs pour l'intelligence adaptive
        self.interaction_count = 0
        self.success_predictions = 0
        self.user_satisfaction_score = 5.0

        # Base de connaissances avancée pour l'intelligence contextuelle
        self.expert_knowledge = {
            "programming_insights": [
                "Cette approche optimise généralement les performances.",
                "Je remarque un pattern d'optimisation possible ici.",
                "Cette méthode suit les best practices de l'industrie.",
                "Voici une approche plus élégante et maintenable.",
            ],
            "advanced_patterns": [
                "Basé sur le contexte, cette approche serait plus adaptée.",
                "En considérant votre historique, cette solution conviendrait mieux.",
                "Cette variante pourrait être plus puissante pour votre cas.",
            ],
        }

        print(f"✅ {self.name} v{self.version} initialisé avec succès")
        print(
            "🧠 Modules chargés : Linguistique, Base de connaissances, Génération de code, Raisonnement, Mémoire, Recherche Internet"
        )
        print("💾 Mémoire de conversation activée")
        print("🌐 Recherche internet disponible")

    def _add_to_conversation_history(
        self,
        user_message: str,
        ai_response: str,
        intent: str = "general",
        confidence: float = 1.0,
        context: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Ajoute une conversation à TOUS les systèmes de mémoire.
        Synchronise ConversationMemory ET LocalLLM pour que Ollama ait le contexte complet.

        Args:
            user_message: Le message de l'utilisateur
            ai_response: La réponse de l'IA
            intent: L'intention détectée (faq, calculation, joke, etc.)
            confidence: Le niveau de confiance de la réponse
            context: Contexte additionnel
        """
        # 1. Ajouter à ConversationMemory (pour la recherche contextuelle)
        self.conversation_memory.add_conversation(
            user_message, ai_response, intent, confidence, context
        )

        # 2. Ajouter à l'historique LocalLLM (pour le contexte Ollama)
        if self.local_llm and hasattr(self.local_llm, "add_to_history"):
            self.local_llm.add_to_history("user", user_message)
            self.local_llm.add_to_history("assistant", ai_response)
            print(f"🧠 [SYNC] Conversation ajoutée à l'historique Ollama ({intent})")

    def generate_response(
        self, user_input: str, context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Génère une réponse avec gestion améliorée des documents"""
        try:
            user_lower = user_input.lower()

            # ============================================================
            # 📚 PRIORITÉ ABSOLUE : FAQ/ML - Vérifier EN PREMIER
            # ============================================================
            # La FAQ doit être consultée AVANT tout autre système
            # pour garantir que les réponses enrichies soient utilisées
            faq_response = None
            try:
                faq_response = self.ml_model.predict(user_input)
                if faq_response is not None and str(faq_response).strip():
                    print(f"📚 [FAQ] ✅ Réponse FAQ trouvée pour: '{user_input}'")
                    # Synchroniser avec l'historique Ollama
                    self._add_to_conversation_history(user_input, faq_response, "faq")
                    return faq_response
            except (ValueError, AttributeError, TypeError) as e:
                print(f"⚠️ [FAQ] Erreur lors de la consultation FAQ: {e}")

            # ============================================================
            # 🎯 EXCEPTIONS À OLLAMA - Ces cas utilisent leurs outils dédiés
            # ============================================================

            # 1️⃣ MÉTÉO (wttr.in) - Détection des demandes météo
            weather_keywords = [
                "météo",
                "meteo",
                "temps qu'il fait",
                "quel temps",
                "température",
                "temperature",
                "fait-il chaud",
                "fait-il froid",
                "pleut",
                "pluie",
                "neige",
                "soleil",
                "nuageux",
                "orageux",
                "weather",
                "prévisions",
                "previsions",
            ]
            is_weather_request = any(kw in user_lower for kw in weather_keywords)

            # 2️⃣ RECHERCHE INTERNET - Détection explicite
            internet_keywords = [
                "cherche sur internet",
                "recherche sur internet",
                "trouve sur internet",
                "cherche sur le web",
                "recherche sur le web",
                "search on internet",
                "cherche en ligne",
                "recherche en ligne",
            ]
            is_internet_search = any(kw in user_lower for kw in internet_keywords)

            # 3️⃣ CALCUL - Utiliser intelligent_calculator
            # Les calculs sont toujours prioritaires, même avec des documents en mémoire
            is_calculation = (
                CALCULATOR_AVAILABLE
                and intelligent_calculator.is_calculation_request(user_input)
            )

            # 4️⃣ BLAGUES - Détection des demandes de blagues
            joke_keywords = [
                "dis moi une blague",
                "raconte moi une blague",
                "t'aurais une blague",
                "aurais-tu une blague",
                "une blague",
                "raconte une blague",
                "dis une blague",
                "tu connais une blague",
                "connais-tu une blague",
                "fais moi une blague",
                "une blague stp",
                "une autre blague",
            ]
            is_joke_request = any(kw in user_lower for kw in joke_keywords)

            # ========================================================= #
            # 🔀 ROUTAGE : Exceptions d'abord, puis Ollama par défaut   #
            # ========================================================= #

            # ☀️ 1. MÉTÉO → wttr.in (via internet_search ou outil dédié)
            if is_weather_request:
                print(f"☀️ [MÉTÉO] Requête météo détectée: '{user_input}'")
                # Déléguer à la recherche internet qui gère wttr.in
                response = self._handle_internet_search(user_input, context or {})
                # Synchroniser avec l'historique Ollama
                self._add_to_conversation_history(user_input, response, "weather")
                return response

            # 🌐 2. RECHERCHE INTERNET → moteur de recherche
            if is_internet_search:
                print(f"🌐 [INTERNET] Recherche internet explicite: '{user_input}'")
                response = self._handle_internet_search(user_input, context or {})
                # Synchroniser avec l'historique Ollama
                self._add_to_conversation_history(
                    user_input, response, "internet_search"
                )
                return response

            # 🧮 3. CALCUL → intelligent_calculator
            if is_calculation:
                print(f"🧮 [CALCUL] Calcul détecté: '{user_input}'")
                calc_result = intelligent_calculator.calculate(user_input)
                response = intelligent_calculator.format_response(calc_result)
                # Synchroniser avec l'historique Ollama
                self._add_to_conversation_history(user_input, response, "calculation")
                return response

            # � 4. BLAGUES → Liste self.jokes
            if is_joke_request:
                print(f"😂 [BLAGUE] Demande de blague détectée: '{user_input}'")
                joke_response = self._tell_joke()
                # Synchroniser avec l'historique Ollama
                self._add_to_conversation_history(user_input, joke_response, "joke")
                return joke_response

            # ============================================================
            # 🦙 OLLAMA PAR DÉFAUT - Pour tout le reste
            # ============================================================
            if self.local_llm and self.local_llm.is_ollama_available:
                system_prompt = None  # Utiliser le system prompt du Modelfile par défaut

                # 📄 5. QUESTIONS SUR DOCUMENTS - Injecter le contenu dans Ollama
                if self._has_documents_in_memory() and (
                    self._is_document_processing_request(user_input) or
                    self._is_document_question(user_input)
                ):
                    print("📊 [DOC-QUESTION] Question sur document détectée - envoi à Ollama")
                    doc_content = self._get_full_document_content()
                    if doc_content:
                        # Utiliser le contenu complet sans limitation
                        system_prompt = (
                            f"Tu es un assistant qui analyse des documents. "
                            f"Voici le contenu du document que l'utilisateur a chargé :\n\n"
                            f"{doc_content}\n\n"
                            f"Réponds à la question de l'utilisateur en te basant UNIQUEMENT sur ce document. "
                            f"Si l'utilisateur demande un résumé, fais un résumé structuré et détaillé du document."
                        )
                        print(f"📄 [DOC-QUESTION] Contexte document injecté: {len(doc_content)} chars")

                # Injection du contexte RAG externe si fourni
                if context and isinstance(context, dict):
                    rag_content = context.get("rag_context", "")
                    if rag_content and len(rag_content.strip()) > 50:
                        rag_summary = (
                            rag_content[:2000]
                            if len(rag_content) > 2000
                            else rag_content
                        )
                        if system_prompt:
                            system_prompt += f"\n\nCONTEXTE ADDITIONNEL:\n{rag_summary}"
                        else:
                            system_prompt = f"CONTEXTE ADDITIONNEL:\n{rag_summary}"

                print(f"🦙 [OLLAMA] Génération via Ollama pour: '{user_input}'")
                llm_response = self.local_llm.generate(
                    user_input, system_prompt=system_prompt
                )

                if llm_response:
                    # Sauvegarder dans la mémoire ET synchroniser avec Ollama
                    self._add_to_conversation_history(
                        user_input, llm_response, "ollama_llm", 1.0, {}
                    )
                    return llm_response
                else:
                    print(
                        "⚠️ [OLLAMA] Ollama n'a pas répondu, fallback vers système classique..."
                    )

            # ============================================================
            # 🔧 FALLBACK: Système classique si Ollama indisponible
            # ============================================================

            # 🔍 GESTION DU CONTEXTE RAG EXTERNE
            _rag_context_used = False
            if context and isinstance(context, dict):
                rag_content = context.get("rag_context", "")
                if rag_content and len(rag_content.strip()) > 50:
                    print(
                        f"📦 [RAG] Contexte externe détecté: {len(rag_content)} chars"
                    )

                    # Ajouter au context_manager Ultra si disponible
                    if self.ultra_mode and self.context_manager:
                        doc_name = context.get("source_file", "RAG_Context_External")
                        result = self.context_manager.add_document(
                            content=rag_content, document_name=doc_name
                        )
                        if result.get("status") == "success":
                            print(
                                f"✅ [RAG→ULTRA] Contexte ajouté au système Ultra: {result.get('chunks_created', 0)} chunks"
                            )
                            _rag_context_used = True
                        else:
                            print(f"⚠️ [RAG→ULTRA] {result.get('status', 'error')}")
                    else:
                        # Stocker en mémoire classique
                        self.conversation_memory.store_document_content(
                            "RAG_Context", rag_content
                        )
                        print("✅ [RAG→CLASSIC] Contexte ajouté à la mémoire classique")
                        _rag_context_used = True

            # Mise à jour du contexte de session
            self._update_session_context()

            # Détection d'intention avec contexte amélioré
            intent_context = {
                "code_file_processed": len(self.session_context["code_files_processed"])
                > 0,
                "document_processed": len(self.session_context["documents_processed"])
                > 0,
                "has_documents": len(self.conversation_memory.get_document_content())
                > 0,
            }

            # Détection d'intention
            intent_scores = self.linguistic_patterns.detect_intent(
                user_input, intent_context
            )
            # Sélection de l'intention primaire avec logique améliorée
            primary_intent, confidence = self._select_primary_intent(
                intent_scores, user_input
            )

            print(
                f"DEBUG: Intent détecté: {primary_intent} (confiance: {confidence:.2f})"
            )

            # NOUVELLES CAPACITÉS DE CODE GÉNÉRATION INTELLIGENTE
            if primary_intent == "code_generation":
                # Récupérer le contexte AVANT de l'utiliser
                conversation_context = (
                    self.conversation_memory.get_context_for_response(primary_intent)
                )
                response = self._run_async(
                    self._handle_advanced_code_generation(user_input)
                )
                # Synchroniser avec l'historique Ollama
                self._add_to_conversation_history(
                    user_input,
                    response,
                    "code_generation",
                    confidence,
                    conversation_context,
                )
                return response

            # Récupération du contexte conversationnel
            conversation_context = self.conversation_memory.get_context_for_response(
                primary_intent
            )

            # D'abord vérifier s'il y a des questions similaires
            similar_question = self.conversation_memory.has_similar_recent_question(
                user_input
            )

            # Puis appeler avec tous les paramètres requis
            response = self._generate_contextual_response(
                user_input,
                primary_intent,
                confidence,
                conversation_context,
                similar_question,
            )

            # Enregistrement dans la mémoire ET synchronisation avec LocalLLM
            self._add_to_conversation_history(
                user_input, response, primary_intent, confidence, conversation_context
            )

            return response

        except Exception as e:
            error_response = f"Désolé, j'ai rencontré un problème : {str(e)}"
            self._add_to_conversation_history(
                user_input, error_response, "error", 0.0, {"error": str(e)}
            )
            return error_response

    @staticmethod
    def _question_concerns_image(user_input: str) -> bool:
        """
        Détecte si la question de l'utilisateur concerne une image.
        
        Args:
            user_input: La question de l'utilisateur
            
        Returns:
            True si la question concerne l'image, False sinon
        """
        user_lower = user_input.lower().strip()

        # Mots-clés qui indiquent que la question concerne l'image
        image_keywords = [
            'image', 'photo', 'capture', 'écran', 'screenshot', 'screen',
            'picture', 'pic', 'img', 'illustration', 'figure',
            'que vois-tu', 'que voit', 'ce que tu vois', 'sur cette image',
            'sur la photo', 'dans l\'image', 'dans la photo',
            'décris', 'analyse l\'image', 'explique l\'image', 'montre',
            'cette image', 'cette photo', 'cette capture',
            'l\'image', 'la photo', 'la capture', 'sur l\'image',
            'qu\'y a-t-il', 'que représente'
        ]

        return any(keyword in user_lower for keyword in image_keywords)

    def generate_response_stream(
        self, user_input: str, on_token=None, context: Optional[Dict[str, Any]] = None,
        image_base64: Optional[str] = None
    ) -> str:
        """
        Génère une réponse en STREAMING pour affichage temps réel.

        Cette méthode utilise le streaming Ollama pour envoyer chaque token
        dès qu'il est généré, permettant un affichage instantané dans l'interface.

        Args:
            user_input: Le message de l'utilisateur
            on_token: Callback appelé pour chaque token (signature: on_token(str) -> bool)
                     Retourne False pour interrompre la génération
            context: Contexte optionnel (RAG, documents, etc.)
            image_base64: Image encodée en base64 pour analyse vision

        Returns:
            La réponse complète une fois terminée
        """
        try:
            user_lower = user_input.lower().strip()

            # ============================================================
            # 🖼️ PRIORITÉ 0 : IMAGE - Si une image est jointe ET la question concerne l'image
            # ============================================================
            if image_base64 and self.local_llm and self.local_llm.is_ollama_available and self._question_concerns_image(user_input):
                print("🖼️ [VISION] Image détectée - utilisation du modèle vision")
                system_prompt = (
                    "Tu es un assistant IA qui analyse des images. "
                    "Décris et analyse l'image de manière détaillée en français. "
                    "Si l'utilisateur pose une question spécifique, réponds-y en te basant sur l'image."
                )
                response = self.local_llm.generate_stream_with_image(
                    user_input, image_base64,
                    system_prompt=system_prompt,
                    on_token=on_token
                )
                if response:
                    self.conversation_memory.add_conversation(
                        user_input, response, "vision_stream", 1.0, {}
                    )
                    return response
                else:
                    # Erreur vision (pas de modèle vision installé)
                    error_msg = (
                        "⚠️ **Aucun modèle vision n'est installé dans Ollama.**\n\n"
                        "Pour analyser des images, installez un modèle vision :\n"
                        "```bash\nollama pull llava\n```\n\n"
                        "Modèles supportés : `llava`, `llama3.2-vision`, `bakllava`, `moondream`"
                    )
                    if on_token:
                        on_token(error_msg)
                    return error_msg

            # ============================================================
            # 📚 PRIORITÉ ABSOLUE : FAQ/ML - Vérifier EN PREMIER
            # ============================================================
            # La FAQ doit être consultée AVANT tout autre système, même en streaming
            faq_response = None
            try:
                faq_response = self.ml_model.predict(user_input)
                if faq_response is not None and str(faq_response).strip():
                    print(
                        f"📚 [FAQ STREAM] ✅ Réponse FAQ trouvée pour: '{user_input}'"
                    )
                    # IMPORTANT : Ajouter à l'historique Ollama pour le contexte
                    self._add_to_conversation_history(
                        user_input,
                        faq_response,
                        "faq",
                        1.0,
                        {"source": "enrichissement"},
                    )
                    print("🧠 [FAQ STREAM] Conversation ajoutée à l'historique Ollama")
                    if on_token:
                        on_token(faq_response)
                    return faq_response
            except (ValueError, AttributeError, TypeError) as e:
                print(f"⚠️ [FAQ STREAM] Erreur lors de la consultation FAQ: {e}")

            # ============================================================
            # 🎯 EXCEPTIONS AU STREAMING - Réponses locales immédiates
            # ============================================================

            # Ces cas n'ont pas besoin du streaming car ils sont instantanés

            # 1️⃣ RECHERCHE INTERNET - Détection explicite
            internet_keywords = [
                "cherche sur internet",
                "recherche sur internet",
                "trouve sur internet",
                "cherche sur le web",
                "recherche sur le web",
                "search on internet",
                "cherche en ligne",
                "recherche en ligne",
            ]
            if any(kw in user_lower for kw in internet_keywords):
                print(
                    f"🌐 [INTERNET STREAM] Recherche internet détectée: '{user_input}'"
                )
                # ⚡ Activer le streaming pour la recherche internet
                response = self._handle_internet_search(user_input, context, on_token)
                return response

            # 2️⃣ MÉTÉO - API externe rapide
            weather_keywords = [
                "météo",
                "meteo",
                "temps qu'il fait",
                "quel temps",
                "température",
            ]
            if any(kw in user_lower for kw in weather_keywords):
                response = self.generate_response(user_input, context)
                if on_token:
                    on_token(response)
                return response

            # 3️⃣ CALCULS - Résultat instantané
            if any(
                op in user_input for op in ["+", "-", "*", "/", "^", "sqrt", "calcule"]
            ):
                response = self.generate_response(user_input, context)
                if on_token:
                    on_token(response)
                return response

            # 4️⃣ BLAGUES - Base locale
            joke_keywords = ["blague", "rigole", "drôle", "humour", "raconte-moi une"]
            if any(kw in user_lower for kw in joke_keywords):
                response = self.generate_response(user_input, context)
                if on_token:
                    on_token(response)
                return response

            # ============================================================
            # 🦙 STREAMING OLLAMA - Pour les réponses génératives
            # ============================================================

            if self.local_llm and self.local_llm.is_ollama_available:
                system_prompt = None

                # 5️⃣ QUESTIONS SUR DOCUMENTS - Injecter le contenu du document dans Ollama
                if self._has_documents_in_memory() and (
                    self._is_document_processing_request(user_input) or
                    self._is_document_question(user_input)
                ):
                    print("📊 [STREAM-DOC] Question sur document détectée - envoi à Ollama")
                    doc_content = self._get_full_document_content()
                    if doc_content:
                        # Utiliser le contenu complet sans limitation
                        system_prompt = (
                            f"Tu es un assistant qui analyse des documents. "
                            f"Voici le contenu du document que l'utilisateur a chargé :\n\n"
                            f"{doc_content}\n\n"
                            f"Réponds à la question de l'utilisateur en te basant UNIQUEMENT sur ce document. "
                            f"Si l'utilisateur demande un résumé, fais un résumé structuré et détaillé du document."
                        )
                        print(f"📄 [STREAM-DOC] Contexte document injecté: {len(doc_content)} chars")

                # Injection RAG si fourni
                if context and isinstance(context, dict):
                    rag_content = context.get("rag_context", "")
                    if rag_content and len(rag_content.strip()) > 50:
                        rag_summary = (
                            rag_content[:2000]
                            if len(rag_content) > 2000
                            else rag_content
                        )
                        if system_prompt:
                            system_prompt += f"\n\nCONTEXTE ADDITIONNEL:\n{rag_summary}"
                        else:
                            system_prompt = f"CONTEXTE ADDITIONNEL:\n{rag_summary}"

                print(f"⚡ [STREAM] Génération streaming pour: '{user_input[:50]}...'")

                # Utiliser le streaming
                response = self.local_llm.generate_stream(
                    user_input, system_prompt=system_prompt, on_token=on_token
                )

                if response:
                    # Sauvegarder dans la mémoire (l'historique Ollama est déjà mis à jour par generate_stream)
                    self.conversation_memory.add_conversation(
                        user_input, response, "ollama_stream", 1.0, {}
                    )
                    return response
                else:
                    print("⚠️ [STREAM] Fallback vers génération classique...")

            # ============================================================
            # 🔧 FALLBACK - Mode non-streaming
            # ============================================================
            response = self.generate_response(user_input, context)
            if on_token:
                on_token(response)
            return response

        except Exception as e:
            error_msg = f"Désolé, j'ai rencontré un problème : {str(e)}"
            if on_token:
                on_token(error_msg)
            return error_msg

    def _is_document_processing_request(self, user_input: str) -> bool:
        """Détecte si c'est une demande de traitement de document système"""
        user_lower = user_input.lower()

        # Détection des demandes de résumé en français et anglais
        summary_keywords = [
            "résume", "resume", "résumé", "summarize", "summary",
            "explique", "explain", "analyse", "analyze",
            "décris", "describe"
        ]

        document_keywords = [
            "pdf", "document", "doc", "docx", "fichier", "file", "python", "code", "script"
        ]

        # Vérifier si la demande contient un mot-clé de résumé ET un mot-clé de document
        has_summary_keyword = any(kw in user_lower for kw in summary_keywords)
        has_document_keyword = any(kw in user_lower for kw in document_keywords)

        return (has_summary_keyword and has_document_keyword) or \
               user_lower.startswith("please summarize this pdf content") or \
               user_lower.startswith("please analyze this document content")

    def _get_full_document_content(self) -> str:
        """Récupère le contenu complet de tous les documents stockés en mémoire"""
        stored_docs = self.conversation_memory.get_document_content()
        if not stored_docs:
            return ""

        all_content = ""
        for doc_name, doc_data in stored_docs.items():
            if isinstance(doc_data, dict):
                content = doc_data.get("content", "") or doc_data.get("text", "") or doc_data.get("data", "")
            elif isinstance(doc_data, str):
                content = doc_data
            else:
                content = str(doc_data) if doc_data else ""

            if content:
                all_content += f"\n\n--- {doc_name} ---\n{content}"

        return all_content.strip()

    def _handle_document_processing(self, user_input: str) -> str:
        """Traite les demandes de résumé de documents avec système Ultra ou mémoire classique"""
        print("🔍 Traitement de document détecté")

        # Extraire le nom du fichier et le contenu
        filename, content = self._extract_document_info(user_input)

        if not content:
            return "Je n'ai pas pu extraire le contenu du document."

        # Stocker le document selon le mode
        if self.ultra_mode:
            print("📄 [ULTRA] Ajout au contexte 1M tokens")
            result = self.add_document_to_context(content, filename)
            if result.get("success"):
                print(f"✅ [ULTRA] Document '{filename}' ajouté avec succès")
            else:
                print(f"⚠️ [ULTRA] Erreur: {result.get('message')}")
        else:
            print("📄 [CLASSIC] Stockage en mémoire classique")
            # Stocker en mémoire classique
            self.conversation_memory.store_document_content(filename, content)

        # Vérifier que session_context existe avant mise à jour
        if not hasattr(self, "session_context"):
            self.session_context = {
                "documents_processed": [],
                "code_files_processed": [],
                "last_document_type": None,
                "current_document": None,
            }

        # Mettre à jour le contexte de session
        self.session_context["documents_processed"].append(filename)
        self.session_context["current_document"] = filename

        if "pdf" in user_input.lower():
            self.session_context["last_document_type"] = "PDF"
            doc_type = "PDF"
        else:
            self.session_context["last_document_type"] = "DOCX"
            doc_type = "document"

        print(f"✅ Document '{filename}' stocké en mémoire et ajouté au contexte")

        # Générer le résumé
        return self._create_universal_summary(content, filename, doc_type)

    def _extract_document_info(self, user_input: str) -> Tuple[str, str]:
        """Extrait le nom du fichier et le contenu du document"""
        # Recherche du nom de fichier
        filename_patterns = [
            r"from file '(.+?)':",
            r"file '(.+?)':",
            r"document '(.+?)':",
        ]

        filename = "document"
        for pattern in filename_patterns:
            match = re.search(pattern, user_input)
            if match:
                filename = match.group(1).strip()
                # Nettoyer l'extension
                filename = filename.replace(".pdf", "").replace(".docx", "")
                break

        # Extraire le contenu (après les deux points)
        content_start = user_input.find(":\n\n")
        if content_start != -1:
            content = user_input[content_start + 3 :].strip()
        else:
            content = ""

        return filename, content

    def _update_session_context(self):
        """Met à jour le contexte de session avec les documents en mémoire"""
        # Vérifier que session_context existe
        if not hasattr(self, "session_context"):
            self.session_context = {
                "documents_processed": [],
                "code_files_processed": [],
                "last_document_type": None,
                "current_document": None,
            }

        stored_docs = self.conversation_memory.get_document_content()

        # Synchroniser la liste des documents traités
        for doc_name in stored_docs.keys():
            if doc_name not in self.session_context["documents_processed"]:
                self.session_context["documents_processed"].append(doc_name)

                # Déterminer le type de document
                doc_data = stored_docs[doc_name]
                if doc_data and doc_data.get("type") == "code":
                    if doc_name not in self.session_context["code_files_processed"]:
                        self.session_context["code_files_processed"].append(doc_name)

    def _analyze_user_intelligence_level(
        self, user_input: str, _context: Dict[str, Any]
    ) -> str:
        """Analyse le niveau technique de l'utilisateur pour adapter les réponses"""
        # Analyse des mots techniques utilisés
        technical_indicators = [
            "algorithm",
            "optimization",
            "pattern",
            "architecture",
            "scalability",
            "performance",
            "async",
            "concurrency",
            "paradigm",
            "abstraction",
            "polymorphism",
            "inheritance",
            "encapsulation",
            "design pattern",
        ]

        advanced_indicators = [
            "big o",
            "complexity",
            "microservices",
            "containerization",
            "orchestration",
            "machine learning",
            "neural network",
            "deep learning",
            "devops",
            "ci/cd",
        ]

        user_lower = user_input.lower()
        technical_count = sum(1 for term in technical_indicators if term in user_lower)
        advanced_count = sum(1 for term in advanced_indicators if term in user_lower)

        if advanced_count > 0 or technical_count > 2:
            return "expert"
        elif technical_count > 0:
            return "intermediate"
        else:
            return "beginner"

    def _predict_user_needs(
        self, user_input: str, _context: Dict[str, Any]
    ) -> List[str]:
        """Prédit les besoins futurs de l'utilisateur de manière subtile"""
        predictions = []
        user_lower = user_input.lower()

        # Prédictions discrètes basées sur le contexte de programmation
        if any(word in user_lower for word in ["function", "fonction", "def "]):
            predictions.extend(
                [
                    "Pensez également à ajouter une gestion d'erreurs appropriée.",
                    "Les tests unitaires seraient un bon complément à cette fonction.",
                ]
            )

        if any(word in user_lower for word in ["class", "classe", "object"]):
            predictions.extend(
                [
                    "Vous pourriez vouloir définir des méthodes supplémentaires.",
                    "Les design patterns pourraient être utiles pour cette structure.",
                ]
            )

        if any(word in user_lower for word in ["data", "données", "file", "fichier"]):
            predictions.extend(
                [
                    "La validation des données sera probablement nécessaire.",
                    "Considérez l'optimisation et la mise en cache pour de gros volumes.",
                ]
            )

        return predictions[:1]  # Seulement une suggestion discrète

    def _add_wow_factor_to_response(
        self, response: str, user_input: str, context: Dict[str, Any]
    ) -> str:
        """Enrichit la réponse avec une intelligence contextuelle subtile"""
        self.interaction_count += 1

        # Analyse du niveau de l'utilisateur
        user_level = self._analyze_user_intelligence_level(user_input, context)

        # Prédictions intelligentes
        predictions = self._predict_user_needs(user_input, context)

        # Ajouter des insights adaptés au niveau de manière naturelle
        if user_level == "expert" and random.random() < 0.5:
            insights = random.choice(self.expert_knowledge["advanced_patterns"])
            response += f"\n\n{insights}"
        elif user_level == "intermediate" and random.random() < 0.4:
            insights = random.choice(self.expert_knowledge["programming_insights"])
            response += f"\n\n{insights}"

        # Ajouter une prédiction de manière subtile
        if predictions and random.random() < 0.3:  # Plus rare, plus subtil
            prediction = random.choice(predictions)
            response += f"\n\n{prediction}"

        return response

    def _generate_intelligent_suggestions(
        self, user_input: str, _context: Dict[str, Any]
    ) -> List[str]:
        """Génère des suggestions intelligentes basées sur l'analyse du contexte"""
        suggestions = []
        user_lower = user_input.lower()

        # Suggestions basées sur les patterns de code
        if "python" in user_lower:
            suggestions.extend(
                [
                    "💡 Voulez-vous que je montre les best practices Python ?",
                    "🔧 Souhaitez-vous optimiser ce code pour de meilleures performances ?",
                    "📚 Intéressé par les design patterns Python avancés ?",
                ]
            )

        if any(word in user_lower for word in ["problem", "problème", "bug", "error"]):
            suggestions.extend(
                [
                    "🔍 Voulez-vous que j'analyse les causes possibles ?",
                    "🛠️ Souhaitez-vous un plan de debugging structuré ?",
                    "⚡ Intéressé par des outils de diagnostic avancés ?",
                ]
            )

        return suggestions[:3]  # Limiter à 3 suggestions

    def _generate_contextual_response(
        self,
        user_input: str,
        intent: str,
        _confidence: float,
        context: Dict[str, Any],
        similar_question: Optional[Any] = None,
    ) -> str:
        """Génère une réponse contextuelle basée sur l'intention et l'historique"""

        # Détecter le style de communication de l'utilisateur
        user_style = self._detect_user_style(context)
        context["user_style"] = user_style

        # Gestion des questions similaires récentes - LOGIQUE AMÉLIORÉE
        if similar_question and intent not in [
            "greeting",
            "thank_you",
            "goodbye",
            "how_are_you",
            "identity_question",
            "capabilities_question",
        ]:
            time_ago = time.time() - similar_question.timestamp
            if time_ago < 120:  # Réduit à 2 minutes au lieu de 5
                # Éviter la duplication SEULEMENT si la requête est EXACTEMENT la même
                if (
                    user_input.lower().strip()
                    == similar_question.user_message.lower().strip()
                ):
                    # Réponse directe sans indiquer qu'il s'agit d'une question similaire
                    return similar_question.ai_response
                # Pour les questions similaires mais NON identiques, laisser une réponse normale
                # (ne plus dire "Je viens de répondre à une question similaire...")

        # Vérifier spécifiquement les questions sur documents
        if (
            intent in ["document_question", "code_question", "unknown"]
            and self._has_documents_in_memory()
        ):
            stored_docs = self.conversation_memory.get_document_content()

            # Si c'est clairement une question sur un document, traiter comme telle
            user_lower = user_input.lower()
            if any(
                word in user_lower
                for word in [
                    "résume",
                    "resume",
                    "explique",
                    "que dit",
                    "contient",
                    "analyse",
                ]
            ):
                response = self._answer_document_question(user_input, stored_docs)
                # S'assurer que la réponse est une chaîne
                if isinstance(response, dict):
                    return response.get("message", str(response))
                return response

        # Réponses spécialisées par intention
        if intent == "identity_question":
            return self._generate_identity_response(user_input)
        elif intent == "capabilities_question" or intent == "capability_question":
            return self._generate_capabilities_response(user_input, context)
        elif intent == "greeting":
            return self._generate_greeting_response(user_input, context)
        elif intent == "how_are_you":
            return self._generate_how_are_you_response(user_input, context)
        elif intent == "affirm_doing_well":
            return self._generate_affirm_doing_well_response(context)
        elif intent == "compliment":
            return self._generate_compliment_response(user_input, context)
        elif intent == "laughter":
            return self._generate_laughter_response(user_input, context)
        elif intent == "code_generation" or intent == "code_request":
            return self._generate_code_response(user_input, context)
        elif intent == "programming_question":
            return self._generate_code_response(user_input, context)
        elif intent == "url_summarization":
            return self._handle_url_summarization(user_input)
        elif intent == "internet_search":
            return self._handle_internet_search(user_input, context)
        elif intent == "general_question":
            return self._answer_general_question(user_input, context)
        elif intent == "code_question":
            # Vérifier s'il y a du code en mémoire
            stored_docs = self.conversation_memory.get_document_content()
            code_docs = {}
            for name, doc in stored_docs.items():
                if doc:
                    # Méthode 1: Vérifier le type explicite
                    if doc.get("type") == "code":
                        code_docs[name] = doc
                    # Méthode 2: Vérifier l'extension du fichier
                    elif any(
                        ext in name.lower()
                        for ext in [
                            ".py",
                            ".js",
                            ".html",
                            ".css",
                            ".java",
                            ".cpp",
                            ".c",
                            ".php",
                        ]
                    ):
                        code_docs[name] = doc
                    # Méthode 3: Vérifier la langue détectée
                    elif doc.get("language") in [
                        "python",
                        "javascript",
                        "html",
                        "css",
                        "java",
                        "cpp",
                        "c",
                        "php",
                    ]:
                        code_docs[name] = doc
            print(
                f"🔧 [CODE_QUESTION] Fichiers de code détectés: {list(code_docs.keys())}"
            )
            if code_docs:
                return self._answer_code_question(user_input, code_docs)
            else:
                # S'il n'y a pas de code en mémoire, générer du code comme pour une demande de génération
                return self._generate_code_response(user_input, context)

        # Note: La détection des blagues a été déplacée au début de generate_response()
        # pour éviter que la FAQ/ML ne cache toujours la même blague
        # Cette section a été supprimée pour éviter la duplication

        # Validation finale du type de réponse avec FALLBACK INTELLIGENT
        if intent == "document_question":
            stored_docs = self.conversation_memory.get_document_content()
            response = self._answer_document_question(user_input, stored_docs)

            # 🧠 SYSTÈME DE FALLBACK INTELLIGENT (DÉSACTIVÉ EN MODE ULTRA)
            # Vérifier si la réponse des documents est vraiment pertinente
            response_str = ""
            if isinstance(response, dict):
                response_str = response.get("message", str(response))
            else:
                response_str = str(response)

            # ⚠️ MODIFICATION : En mode Ultra, ne PAS faire de fallback vers internet
            # Le système Ultra 1M tokens est suffisamment intelligent pour trouver la bonne information
            ultra_mode_active = self.ultra_mode and self.context_manager
            print(
                f"🔍 [DEBUG] Ultra mode check: ultra_mode={self.ultra_mode}, context_manager={self.context_manager is not None}, active={ultra_mode_active}"
            )

            if not ultra_mode_active:
                # Si la réponse des documents est trop courte ou générique, essayer la recherche internet
                if self._is_response_inadequate(response_str, user_input):
                    print(
                        "🔄 Réponse document insuffisante, tentative recherche internet..."
                    )
                    internet_response = self._handle_internet_search(
                        user_input, context
                    )
                    # Retourner la meilleure réponse entre les deux
                    if len(internet_response) > len(
                        response_str
                    ) and not internet_response.startswith("❌"):
                        return internet_response
            else:
                print(
                    "🚀 [ULTRA] Mode Ultra détecté - Pas de fallback vers internet, réponse conservée"
                )

            return response_str
        elif intent == "help":
            return self._generate_help_response(user_input, context)
        elif intent == "thank_you":
            return self._generate_thank_you_response(context)
        elif intent == "goodbye":
            return self._generate_goodbye_response(context)
        elif intent == "affirmation":
            response = self._generate_affirmation_response()
        elif intent == "negation":
            response = self._generate_negation_response(context)
        else:
            response = self._generate_default_response(user_input, context)

        # Appliquer l'intelligence avancée sauf pour les réponses très courtes
        if len(response) > 50 and intent not in ["greeting", "goodbye", "joke"]:
            response = self._add_wow_factor_to_response(response, user_input, context)

        return response

    def get_conversation_summary(self) -> Dict[str, Any]:
        """Retourne un résumé de la conversation"""
        return self.conversation_memory.get_conversation_summary()

    def clear_conversation_memory(self) -> None:
        """Vide la mémoire de conversation"""
        self.conversation_memory.clear_memory()
        print("💾 Mémoire de conversation effacée")

    def export_conversation(self, filepath: str) -> None:
        """Exporte la conversation"""
        self.conversation_memory.export_conversation(filepath)
        print(f"💾 Conversation exportée vers {filepath}")

    def get_model_info(self) -> Dict[str, Any]:
        """Retourne les informations sur le modèle"""
        return {
            "name": self.name,
            "version": self.version,
            "type": "local_ai",
            "modules": [
                "LinguisticPatterns",
                "KnowledgeBase",
                "CodeGenerator",
                "ReasoningEngine",
                "ConversationMemory",
            ],
            "features": [
                "Code generation",
                "Natural language understanding",
                "Conversation memory",
                "Multi-language support",
                "100% local operation",
            ],
        }

    def _select_primary_intent(
        self, intent_scores: Dict[str, float], user_input: str
    ) -> Tuple[str, float]:
        """Sélectionne l'intention primaire avec logique contextuelle améliorée"""
        if not intent_scores:
            return "unknown", 0.0

        # Améliorer la détection des demandes de résumé
        user_lower = user_input.lower().strip()

        # PRIORITÉ 1 : Vérifier les questions d'identité AVANT tout (même avec des docs en mémoire)
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
            "présente-toi",
            "présente vous",
            "présentez-vous",
            "c'est quoi ton nom",
            "c'est quoi votre nom",
        ]

        # PRIORITÉ 1.5 : Questions "ça va" et variantes (AVANT capability_keywords)
        how_are_you_keywords = [
            "comment vas tu",
            "comment ça va",
            "ça va",
            "sa va",
            "ca va",
            "tu vas bien",
            "vous allez bien",
        ]

        capability_keywords = [
            "que peux tu",
            "que sais tu",
            "tes capacités",
            "tu peux faire",
            "que fais-tu",
            "à quoi tu sers",
            "à quoi sert tu",
            "à quoi sers tu",
            "à quoi tu sert",
            "tu sers à quoi",
            "tu sert à quoi",
            "tu sers a quoi",
            "tu sert a quoi",
        ]

        if any(keyword in user_lower for keyword in identity_keywords):
            return "identity_question", 1.0

        # Détecter "ça va" avec contexte plus précis
        if any(keyword in user_lower for keyword in how_are_you_keywords):
            # Si c'est juste "ça va" sans "et toi", c'est probablement une affirmation
            if (
                user_lower.strip() in ["ça va", "sa va", "ca va"]
                and "et toi" not in user_lower
            ):
                return "affirm_doing_well", 1.0
            else:
                return "how_are_you", 1.0

        if any(keyword in user_lower for keyword in capability_keywords):
            return "capability_question", 1.0

        # PRIORITÉ 2 : Détecter le charabia/texte aléatoire
        if len(user_lower) > 20 and not any(c.isspace() for c in user_lower[:20]):
            # Plus de 20 caractères sans espaces = probablement du charabia
            return "unknown", 0.5

        # PRIORITÉ 3 : Questions sur les documents (seulement si ce n'est pas de l'identité)
        has_docs = self._has_documents_in_memory()
        print(f"🔍 [DEBUG] Documents en mémoire: {has_docs}")

        # --- PRIORITÉ CODE/PROGRAMMING ---
        # Si le score de code_generation ou programming_question est élevé, prioriser même si documents présents
        code_intents = ["code_generation", "programming_question", "code_request"]
        best_code_intent = None
        best_code_score = 0.0
        for intent in code_intents:
            score = intent_scores.get(intent, 0.0)
            if score > best_code_score:
                best_code_intent = intent
                best_code_score = score

        # ⚠️ FIX V3: Validation stricte pour code AVANT de prioriser
        # Si une intention de code est détectée, vérifier que ce n'est pas un faux positif
        if best_code_intent and best_code_score >= 0.5:
            # TOUJOURS vérifier la présence de mots-clés d'ACTION stricts (même pour score 1.0)
            code_action_words = [
                "génère",
                "genere",
                "crée",
                "cree",
                "écris",
                "ecris",
                "développe",
                "implémente",
                "code pour",
                "fonction pour",
                "script pour",
                "programme pour",
            ]
            has_action_word = any(word in user_lower for word in code_action_words)

            if not has_action_word:
                print(
                    f"⚠️ [INTENT] {best_code_intent} (score: {best_code_score:.2f}) sans mots d'action - Pas de priorisation"
                )
                best_code_intent = None  # Annuler la priorisation
                best_code_score = 0.0
            else:
                print(
                    f"✅ [INTENT] {best_code_intent} (score: {best_code_score:.2f}) avec mots d'action confirmés"
                )

            # Prioriser seulement si validation OK ET score >= 0.7
            if best_code_intent and best_code_score >= 0.7:
                print(
                    f"🎯 [INTENT] Priorisation de l'intention code: {best_code_intent} (score: {best_code_score})"
                )
                return best_code_intent, best_code_score

        # --- LOGIQUE DOCUMENTS (inchangée) ---
        if has_docs:
            if self.ultra_mode and self.context_manager:
                stats = self.context_manager.get_stats()
                ultra_docs = stats.get("documents_added", 0)
                if ultra_docs > 0:
                    print(
                        f"🚀 [DEBUG] Mode Ultra avec {ultra_docs} docs - Priorisation forcée des documents"
                    )
                    if any(
                        q in user_lower
                        for q in [
                            "quel",
                            "quelle",
                            "qui",
                            "combien",
                            "comment",
                            "que",
                            "quoi",
                            "où",
                            "quand",
                            "pourquoi",
                        ]
                    ):
                        print(
                            "🎯 [DEBUG] Mode Ultra - Question interrogative forcée vers documents"
                        )
                        return "document_question", 0.99
                    return "document_question", 0.98
            doc_indicators = [
                "résume",
                "resume",
                "résumé",
                "explique",
                "analyse",
                "que dit",
                "contient",
                "résume le pdf",
                "résume le doc",
                "résume le document",
                "résume le fichier",
                "quel est",
                "quelle est",
                "quels sont",
                "quelles sont",
                "qui a",
                "qui est",
                "combien de",
                "comment",
                "où se",
                "pourquoi",
                "quand",
            ]
            if any(indicator in user_lower for indicator in doc_indicators):
                print(f"🎯 [DEBUG] Indicateur de document détecté: '{user_input}'")
                if any(
                    phrase in user_lower
                    for phrase in [
                        "résume le pdf",
                        "résume le doc",
                        "résume le document",
                    ]
                ):
                    print(
                        "✅ [DEBUG] Résumé de document spécifique détecté - Score: 1.0"
                    )
                    return "document_question", 1.0
                elif user_lower in ["résume", "resume", "résumé"]:
                    print("✅ [DEBUG] Résumé simple détecté - Score: 0.9")
                    return "document_question", 0.9
                elif any(
                    q in user_lower
                    for q in ["quel", "quelle", "qui", "combien", "comment"]
                ):
                    print(
                        "✅ [DEBUG] Question interrogative avec documents détectée - Score: 0.95"
                    )
                    return "document_question", 0.95
                else:
                    print(
                        "✅ [DEBUG] Autre question sur document détectée - Score: 0.8"
                    )
                    return "document_question", 0.8
            else:
                print(
                    f"🚫 [DEBUG] Aucun indicateur de document détecté dans: '{user_input}'"
                )

        # --- LOGIQUE PROGRAMMING/GENERAL (inchangée) ---
        programming_patterns = [
            "comment créer",
            "comment utiliser",
            "comment faire",
            "comment déclarer",
            "liste en python",
            "dictionnaire en python",
            "fonction en python",
            "variable en python",
            "boucle en python",
            "condition en python",
            "classe en python",
            "objet en python",
            "python",
            "programmation",
            "créer une liste",
            "créer un dictionnaire",
            "créer une fonction",
            "faire une boucle",
            "utiliser if",
            "utiliser for",
            "utiliser while",
        ]
        if any(pattern in user_lower for pattern in programming_patterns):
            if any(
                word in user_lower
                for word in [
                    "comment",
                    "créer",
                    "utiliser",
                    "faire",
                    "python",
                    "liste",
                    "dictionnaire",
                    "fonction",
                    "variable",
                    "boucle",
                    "condition",
                    "classe",
                ]
            ):
                return "programming_question", 0.9

        general_question_patterns = [
            "c'est quoi",
            "c est quoi",
            "quest ce que",
            "qu'est-ce que",
            "qu est ce que",
            "qu'est ce que",
            "quel est",
            "quelle est",
            "que signifie",
            "ça veut dire quoi",
            "ca veut dire quoi",
            "définition de",
            "explique moi",
            "peux tu expliquer",
            "dis moi ce que c'est",
        ]
        extended_question_patterns = [
            "quel",
            "quelle",
            "quels",
            "quelles",
            "qui a",
            "qui est",
            "combien",
            "comment",
        ]
        best_intent = max(intent_scores.items(), key=lambda x: x[1])
        is_general_question = any(
            pattern in user_lower for pattern in general_question_patterns
        )
        is_extended_question = False
        if self._has_documents_in_memory() and not (
            self.ultra_mode and self.context_manager
        ):
            is_extended_question = any(
                pattern in user_lower for pattern in extended_question_patterns
            )
        if is_general_question or is_extended_question:
            if self._has_documents_in_memory():
                print(
                    f"🎯 [INTENT] Question détectée avec documents disponibles: '{user_input[:50]}...'"
                )
                return "document_question", 0.95
            elif (
                best_intent[0] not in ["internet_search", "unknown"]
                and best_intent[1] >= 0.7
            ):
                return best_intent[0], best_intent[1]
            else:
                return "internet_search", 0.8
        best_intent = max(intent_scores.items(), key=lambda x: x[1])

        # ⚠️ FIX: Ne pas retourner code_generation avec un score faible
        # Si le meilleur score est < 0.5, c'est probablement une question générale
        if best_intent[1] < 0.5:
            print(
                f"⚠️ [INTENT] Score trop faible ({best_intent[1]:.2f}) pour {best_intent[0]} - Fallback vers factual_question"
            )
            return "factual_question", 0.7

        # Si c'est code_generation avec un score < 0.7, vérifier si c'est vraiment du code
        if (
            best_intent[0]
            in ["code_generation", "programming_question", "code_request"]
            and best_intent[1] < 0.7
        ):
            # Vérifier la présence de mots-clés de code STRICTS
            code_action_words = [
                "génère",
                "genere",
                "crée",
                "cree",
                "écris",
                "ecris",
                "développe",
                "implémente",
                "code pour",
                "fonction pour",
                "script pour",
            ]
            if not any(word in user_lower for word in code_action_words):
                print(
                    "⚠️ [INTENT] code_generation détecté mais sans mots-clés d'action - Fallback vers factual_question"
                )
                return "factual_question", 0.7

        return best_intent[0], best_intent[1]

    def _has_documents_in_memory(self) -> bool:
        """Vérifie si des documents sont en mémoire (Ultra ou classique)"""
        # Vérifier le système Ultra
        if self.ultra_mode and self.context_manager:
            stats = self.context_manager.get_stats()
            ultra_docs = stats.get("documents_added", 0)
            print(f"🔍 [DEBUG] Ultra mode docs: {ultra_docs}")
            if ultra_docs > 0:
                return True

        # Vérifier la mémoire classique
        classic_docs = len(self.conversation_memory.get_document_content()) > 0
        stored_docs = len(self.conversation_memory.stored_documents) > 0

        print(f"🔍 [DEBUG] Classic docs: {classic_docs}, Stored docs: {stored_docs}")

        result = classic_docs or stored_docs
        print(f"🔍 [DEBUG] Total has_documents_in_memory: {result}")

        return result

    def _is_response_inadequate(self, response: str, user_input: str) -> bool:
        """
        🧠 Évalue si une réponse est inadéquate et nécessite un fallback

        Args:
            response: La réponse à évaluer
            user_input: La question de l'utilisateur

        Returns:
            True si la réponse est inadéquate, False sinon
        """
        if not response or len(response.strip()) < 20:
            return True

        # Réponses génériques à éviter
        generic_responses = [
            "je n'ai pas trouvé",
            "aucune information",
            "pas de données",
            "document vide",
            "aucun contenu",
            "impossible de répondre",
            "pas d'information pertinente",
            "contenu non disponible",
        ]

        response_lower = response.lower()
        if any(generic in response_lower for generic in generic_responses):
            return True

        # Si la question contient des mots-clés spécifiques, vérifier qu'ils apparaissent dans la réponse
        user_lower = user_input.lower()
        key_terms = []

        # Extraire les termes importants de la question
        if "quel" in user_lower or "quelle" in user_lower:
            # Pour les questions "quel/quelle", chercher des termes techniques
            technical_terms = [
                "version",
                "algorithme",
                "langage",
                "système",
                "configuration",
                "performance",
                "temps",
                "token",
                "test",
                "turing",
            ]
            key_terms = [term for term in technical_terms if term in user_lower]

        # Si on a des termes clés et qu'aucun n'apparaît dans la réponse, c'est inadéquat
        if key_terms and not any(term in response_lower for term in key_terms):
            return True

        return False

    def _get_document_position_description(self, doc_name: str) -> str:
        """
        Génère une description de la position d'un document dans l'ordre chronologique

        Args:
            doc_name: Nom du document

        Returns:
            Description de la position (ex: "premier", "deuxième", etc.)
        """
        if not self.conversation_memory.document_order:
            return ""

        try:

            position = self.conversation_memory.document_order.index(doc_name)

            if position == 0:
                return "premier"
            elif position == 1:
                return "deuxième"
            elif position == 2:
                return "troisième"
            elif position == len(self.conversation_memory.document_order) - 1:
                return "dernier"
            else:
                return f"{position + 1}ème"
        except ValueError:
            return ""

# Alias pour compatibilité avec l'ancien nom
AdvancedLocalAI = CustomAIModel
