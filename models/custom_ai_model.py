"""
Modèle IA personnalisé local - Architecture modulaire
Intègre tous les modules pour une IA 100% locale avec mémoire de conversation
"""

import asyncio
import random
import re
import time
import traceback
import os
import concurrent.futures
import tempfile
from typing import Any, Dict, List, Optional, Tuple

from models.advanced_code_generator import \
    AdvancedCodeGenerator as CodeGenerator
from models.smart_code_searcher import smart_code_searcher
from models.web_code_searcher import multi_source_searcher
from models.ml_faq_model import MLFAQModel
from processors.code_processor import CodeProcessor
from processors.docx_processor import DOCXProcessor
from processors.pdf_processor import PDFProcessor

from .base_ai import BaseAI
from .conversation_memory import ConversationMemory
from .internet_search import InternetSearchEngine
from .knowledge_base import KnowledgeBase
from .linguistic_patterns import LinguisticPatterns
from .reasoning_engine import ReasoningEngine

# Import du calculateur intelligent
try:
    from utils.intelligent_calculator import intelligent_calculator

    CALCULATOR_AVAILABLE = True
except ImportError:
    CALCULATOR_AVAILABLE = False
    print("⚠️ Calculateur intelligent non disponible")

# Import du gestionnaire 1M tokens
try:
    from .million_token_context_manager import MillionTokenContextManager

    MILLION_TOKEN_AVAILABLE = True
except ImportError:
    MILLION_TOKEN_AVAILABLE = False
    print("⚠️ Gestionnaire 1M tokens non disponible")

# Import des processeurs avancés
try:
    ADVANCED_PROCESSORS_AVAILABLE = True
except ImportError:
    ADVANCED_PROCESSORS_AVAILABLE = False
    print("⚠️ Processeurs avancés non disponibles")


class CustomAIModel(BaseAI):
    """Modèle IA personnalisé avec architecture modulaire et mémoire persistante"""

    def __init__(self, conversation_memory: ConversationMemory = None):
        super().__init__()
        self.name = "Assistant IA Local"
        self.version = "5.6.0"

        # Modules spécialisés
        self.linguistic_patterns = LinguisticPatterns()
        self.knowledge_base = KnowledgeBase()
        self.code_generator = CodeGenerator()
        self.web_code_searcher = multi_source_searcher
        self.reasoning_engine = ReasoningEngine()
        self.conversation_memory = conversation_memory or ConversationMemory()
        self.internet_search = InternetSearchEngine()

        # Gestionnaire 1M tokens
        if MILLION_TOKEN_AVAILABLE:
            self.context_manager = MillionTokenContextManager()
            self.ultra_mode = True
            print("🚀 Mode Ultra 1M tokens activé")
        else:
            self.context_manager = None
            self.ultra_mode = False
            print("📝 Mode standard activé")

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
        self.last_joke_intro = None  # Dernière intro de blague utilisée pour éviter répétitions

        # Réponses personnalisées pour l'identité
        self.identity_responses = {
            "basic": [
                "Je suis votre assistant IA local ! Je suis conçu pour vous aider avec la programmation, les questions techniques, et bien plus encore.",
                "Bonjour ! Je suis un assistant IA qui fonctionne entièrement en local sur votre machine. Je peux vous aider avec le code, répondre à vos questions, et discuter avec vous.",
                "Salut ! Moi c'est Assistant IA Local. Je suis votre compagnon virtuel pour la programmation et les discussions techniques. Je tourne uniquement en local, pas besoin d'internet !",
                "Je suis votre assistant personnel ! Un modèle IA local qui peut coder, expliquer, et discuter avec vous. J'apprends de nos conversations pour mieux vous comprendre.",
            ],
            "detailed": [
                "Je suis Assistant IA Local, version 5.6.0 Je suis un modèle d'intelligence artificielle conçu pour fonctionner entièrement en local, sans dépendance externe. Je peux générer du code, expliquer des concepts, et avoir des conversations naturelles avec vous.",
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

    def generate_response(
        self, user_input: str, context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Génère une réponse avec gestion améliorée des documents"""
        try:
            # 🎭 PRIORITÉ SPÉCIALE: Détection des demandes de blagues AVANT FAQ/ML
            user_lower = user_input.lower()
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

            if any(keyword in user_lower for keyword in joke_keywords):
                # Appeler directement _tell_joke() sans passer par FAQ
                joke_response = self._tell_joke()
                # Sauvegarder dans la mémoire
                self.conversation_memory.add_conversation(
                    user_input, joke_response, "joke"
                )
                return joke_response

            # 🎯 PRIORITÉ ABSOLUE: Vérification FAQ/ML d'abord (sauf pour les blagues)
            try:
                ml_model = MLFAQModel()
                faq_response = ml_model.predict(user_input)
                if faq_response is not None and str(faq_response).strip():
                    print(f"🎯 FAQ/ML: Réponse trouvée pour '{user_input}'")
                    # Sauvegarder dans la mémoire
                    self.conversation_memory.add_conversation(
                        user_input, faq_response, "faq"
                    )
                    return faq_response
            except Exception as e:
                print(f"⚠️ Erreur FAQ/ML: {e}")

            # 🧮 PRIORITÉ 2: Vérification si c'est un calcul (MAIS PAS une question sur document)
            # Note: user_lower déjà défini plus haut pour la détection des blagues

            # Éviter d'intercepter les questions sur documents qui contiennent des nombres
            is_document_question = self._has_documents_in_memory() and any(
                word in user_lower
                for word in [
                    "quel",
                    "quelle",
                    "combien",
                    "selon",
                    "configuration",
                    "système",
                    "document",
                ]
            )

            if (
                CALCULATOR_AVAILABLE
                and intelligent_calculator.is_calculation_request(user_input)
                and not is_document_question
            ):
                print(f"🧮 Calcul détecté: {user_input}")
                calc_result = intelligent_calculator.calculate(user_input)
                response = intelligent_calculator.format_response(calc_result)

                # Sauvegarder dans la mémoire de conversation
                self.conversation_memory.add_conversation(
                    user_input, response, "calculation"
                )
                return response

            # Vérification spéciale pour résumés simples
            if (
                user_lower in ["résume", "resume", "résumé"]
                and self._has_documents_in_memory()
            ):
                # Forcer l'intention document_question
                return self._answer_document_question(
                    user_input, self.conversation_memory.get_document_content()
                )

            # Traitement spécialisé pour les résumés de documents
            if self._is_document_processing_request(user_input):
                return self._handle_document_processing(user_input)

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

            # PRIORITÉ ABSOLUE pour les recherches internet explicites
            user_lower = user_input.lower()
            if any(
                phrase in user_lower
                for phrase in [
                    "cherche sur internet",
                    "recherche sur internet",
                    "trouve sur internet",
                    "cherche sur le web",
                    "recherche sur le web",
                ]
            ):
                print(
                    f"DEBUG: Recherche internet détectée explicitement dans: '{user_input}'"
                )
                primary_intent = "internet_search"
                confidence = 1.0
            else:
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
                return asyncio.run(self._handle_advanced_code_generation(user_input))

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

            # Enregistrement dans la mémoire
            self.conversation_memory.add_conversation(
                user_input, response, primary_intent, confidence, conversation_context
            )

            return response

        except Exception as e:
            error_response = f"Désolé, j'ai rencontré un problème : {str(e)}"
            self.conversation_memory.add_conversation(
                user_input, error_response, "error", 0.0, {"error": str(e)}
            )
            return error_response

    def _is_document_processing_request(self, user_input: str) -> bool:
        """Détecte si c'est une demande de traitement de document système"""
        return user_input.lower().startswith(
            "please summarize this pdf content"
        ) or user_input.lower().startswith("please analyze this document content")

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

    def _generate_identity_response(
        self, _user_input: str
    ) -> str:
        """Réponse d'identité naturelle"""
        responses = [
            "Je suis votre assistant IA local ! Je suis conçu pour vous aider avec la programmation, l'analyse de documents, et bien plus encore.",
            "Salut ! Moi c'est Assistant IA Local. Je suis votre compagnon virtuel pour coder, analyser des documents, et discuter avec vous. Tout fonctionne en local !",
            "Je suis votre assistant IA personnel qui fonctionne entièrement sur votre machine. C'est mieux pour la sécurité et la confidentialité ;)",
        ]

        return random.choice(responses)

    def _generate_capabilities_response(
        self, user_input: str, context: Dict[str, Any]
    ) -> str:
        """Réponse sur les capacités avec intelligence avancée"""

        # CORRECTION : Si c'est "ça va?" ou variantes (mais PAS des questions de capacités), rediriger vers how_are_you
        user_lower = user_input.lower().strip()
        # Vérifier que ce n'est pas une question de capacité avant de rediriger vers how_are_you
        if any(
            phrase in user_lower
            for phrase in ["ça va", "ca va", "sa va", "comment vas tu", "comment ça va"]
        ) and not any(
            phrase in user_lower
            for phrase in [
                "à quoi tu sers",
                "à quoi sert tu",
                "à quoi sers tu",
                "à quoi tu sert",
                "tu sers à quoi",
                "tu sert à quoi",
                "tu sers a quoi",
                "tu sert a quoi",
            ]
        ):
            return self._generate_how_are_you_response(user_input, context)

        # 🚀 ANALYSE INTELLIGENTE DE L'UTILISATEUR
        user_level = self._analyze_user_intelligence_level(user_input, context)

        # 🧠 RÉPONSE ADAPTÉE AU NIVEAU TECHNIQUE
        if user_level == "expert":
            base_response = """🚀 **Assistant IA Avancé - Capacités Techniques Complètes**

⚡ **Architecture modulaire :**
• `LinguisticPatterns` : NLP et détection d'intentions
• `KnowledgeBase` : Base de connaissances structurée  
• `CodeGenerator` : Génération multi-langages optimisée
• `ReasoningEngine` : Moteur d'inférence logique
• `ConversationMemory` : Mémoire contextuelle persistante
• `InternetSearch` : Requêtes web avec parsing intelligent

🔬 **Technologies intégrées :**
• Analyse sémantique avancée
• Pattern recognition pour le code
• Optimisation algorithmique automatique
• Gestion d'état conversationnel
• Processing de documents avec OCR
• API REST et WebSocket ready

💡 **Cas d'usage avancés :**
• Reverse engineering de logique métier
• Architecture de solutions complexes  
• Code review automatisé avec best practices
• Debugging assisté par IA avec stack trace analysis

🎯 **Performance :** 100% local, latence < 50ms, zero data leak"""

        elif user_level == "intermediate":
            base_response = """💻 **Assistant IA Intelligent - Tout pour les Développeurs**

🔥 **Développement accéléré :**
• Génération de code smart avec patterns détectés
• Refactoring automatique et optimisations
• Tests unitaires générés avec cas edge
• Documentation auto-générée from code
• API design avec best practices
• Database schema suggestions

📊 **Analyse avancée :**
• Code complexity analysis (Big O, maintainability)
• Security vulnerability detection
• Performance bottleneck identification  
• Architecture recommendations
• Technology stack optimization

🚀 **Productivité boostée :**
• Template project generation
• Config files auto-setup
• Dependencies management smart
• Git workflow optimization
• CI/CD pipeline suggestions

🧠 **Intelligence contextuelle :** J'apprends vos préférences de code et m'adapte !"""

        else:
            base_response = """🎯 **Votre Assistant IA Personnel - Simple et Puissant !**

🔍 **J'analyse :**
• 📄 Vos documents PDF et Word → Résumés clairs
• 💻 Vos besoins de code → Solutions sur mesure  
• 🌐 Vos questions → Recherches internet + synthèses
• 🧠 Vos problèmes → Solutions étape par étape

⚡ **Je code pour vous :**
• Sites web complets (HTML, CSS, JavaScript)
• Scripts Python pour automatiser vos tâches
• Applications simples avec interface graphique
• APIs pour connecter vos services

💬 **Je suis votre compagnon :**
• Conversations naturelles sur tous sujets
• Explications claires et pédagogiques
• Conseils personnalisés selon vos besoins
• Bonne humeur et blagues garanties ! 😄

🔒 **100% confidentiel :** Tout reste sur votre machine !"""

        # 🎯 AJOUT DE PRÉDICTIONS INTELLIGENTES
        predictions = self._predict_user_needs(user_input, context)
        if predictions:
            base_response += f"\n\n{predictions[0]}"

        # 💡 SUGGESTIONS CONTEXTUELLES
        suggestions = self._generate_intelligent_suggestions(user_input, context)
        if suggestions:
            base_response += f"\n\n**Suggestions :** {suggestions[0]}"

        return base_response

    def _generate_greeting_response(
        self, user_input: str, context: Dict[str, Any]
    ) -> str:
        """Génère une salutation personnalisée"""
        total_interactions = context.get("total_interactions", 0)

        if total_interactions == 0:
            # Première interaction
            greetings = [
                "Bonjour ! Je suis ravi de faire votre connaissance ! 😊",
                "Salut ! Content de vous rencontrer ! Comment puis-je vous aider aujourd'hui ?",
                "Hello ! Bienvenue ! Je suis votre assistant IA local, prêt à vous aider !",
                "Bonjour ! C'est un plaisir de commencer cette conversation avec vous !",
            ]
        else:
            # Retour dans la conversation
            greetings = [
                "Re-bonjour ! Content de vous revoir ! 😊",
                "Salut ! De retour pour une nouvelle question ?",
                "Hello ! Que puis-je faire pour vous cette fois ?",
                "Bonjour ! J'espère que notre dernière conversation vous a été utile !",
            ]

        # Adaptation au style de l'utilisateur
        if (
            "wesh" in user_input.lower()
            or "yo" in user_input.lower()
            or "wsh" in user_input.lower()
        ):
            greetings = [
                "Wesh ! Ça va ? 😄",
                "Yo ! Salut mec ! Quoi de neuf ?",
                "Salut ! Cool de te voir ! Tu veux qu'on fasse quoi ?",
            ]
        elif "bonsoir" in user_input.lower():
            greetings = [
                "Bonsoir ! J'espère que vous passez une bonne soirée !",
                "Bonsoir ! Comment s'est passée votre journée ?",
                "Bonsoir ! Que puis-je faire pour vous ce soir ?",
            ]
        elif "slt" in user_input.lower() or "salut" in user_input.lower():
            greetings = [
                "Salut chef ! Tu vas bien ?",
            ]
        elif (
            "sa va et toi" in user_input.lower()
            or "ça va et toi" in user_input.lower()
            or "ça va et toi ?" in user_input.lower()
            or "sa va et toi ?" in user_input.lower()
            or "ça va et toi?" in user_input.lower()
            or "sa va et toi?" in user_input.lower()
        ):
            greetings = [
                "Ça va super merci ! Hâte de pouvoir t'aider au mieux !",
            ]

        return self._get_random_response(greetings)

    def _generate_how_are_you_response(
        self, user_input: str, context: Dict[str, Any]
    ) -> str:
        """Génère une réponse adaptée selon si c'est une question réciproque ou non"""
        user_lower = user_input.lower().strip()

        # Détecter si c'est une question réciproque "ça va et toi ?"
        is_reciprocal = any(
            phrase in user_lower
            for phrase in [
                "et toi",
                "et vous",
                "ça va et toi",
                "sa va et toi",
                "ca va et toi",
            ]
        )

        # Détection du style de l'utilisateur
        user_style = context.get("user_style", "neutral")

        if is_reciprocal:
            # Réponse sans redemander (éviter la boucle)
            if user_style == "casual":
                responses = [
                    "Ça va super merci ! Hâte de pouvoir t'aider au mieux ! 😊",
                    "Tout nickel de mon côté ! En quoi je peux t'aider ?",
                    "Parfait pour moi ! Mes circuits ronronnent ! Et toi, tu as besoin de quoi ?",
                    "Excellent ! Je suis en pleine forme ! Dis-moi, qu'est-ce qui t'amène ?",
                    "Super bien merci ! Prêt à bosser sur ce que tu veux ! 🚀",
                    "Ça roule ! J'ai la pêche ! Tu as un projet en tête ?",
                ]
            else:
                responses = [
                    "Très bien, merci ! Je suis entièrement opérationnel. Comment puis-je vous aider ?",
                    "Parfaitement, merci ! Tous mes systèmes fonctionnent optimalement. Que puis-je faire pour vous ?",
                    "Excellent, merci ! Je suis prêt à vous assister. Avez-vous une question ?",
                    "Tout va pour le mieux ! Je suis à votre disposition. En quoi puis-je vous être utile ?",
                    "Très bien merci ! Je fonctionne parfaitement. Quel est votre besoin ?",
                    "Parfait ! Mes modules sont tous opérationnels. Comment puis-je vous aider aujourd'hui ?",
                ]
        else:
            # Question initiale "comment ça va ?" - on peut demander en retour
            if user_style == "casual":
                responses = [
                    "Ça va très bien, merci ! Je suis toujours prêt à aider ! Et toi, comment ça va ?",
                    "Tout va bien ! Je suis en pleine forme et prêt à répondre à tes questions ! 😊 Et toi ?",
                    "Ça roule ! Mon système fonctionne parfaitement et j'ai hâte de t'aider ! Tu vas bien ?",
                    "Excellent ! J'ai tous mes modules qui marchent à merveille ! Et de ton côté ?",
                    "Super ! Je pète la forme ! 💪 Et toi, ça se passe comment ?",
                    "Nickel ! Mes circuits sont au top ! Et toi, tu vas bien ?",
                ]
            else:
                responses = [
                    "Très bien, merci de demander ! Je suis parfaitement opérationnel. Et vous, comment allez-vous ?",
                    "Excellent, merci ! Tous mes systèmes fonctionnent optimalement. Comment allez-vous ?",
                    "Parfaitement bien, merci ! Je suis prêt à vous assister. Et vous, ça va ?",
                    "Très bien merci ! Je fonctionne sans aucun problème. Comment vous portez-vous ?",
                    "Tout va pour le mieux ! Mes modules sont tous opérationnels. Et de votre côté ?",
                    "Excellemment bien ! Je suis en pleine forme. Comment allez-vous aujourd'hui ?",
                ]

        return self._get_random_response(responses)

    def _generate_affirm_doing_well_response(self, context: Dict[str, Any]) -> str:
        """Génère une réponse aux affirmations 'ça va' PERSONNALISÉE"""
        responses = [
            "Super ! Content de savoir que ça va bien ! 😊 Comment puis-je t'aider ?",
            "Parfait ! C'est toujours bien d'aller bien ! En quoi puis-je t'assister ?",
            "Excellent ! Heureux de l'entendre ! Que puis-je faire pour toi ?",
        ]

        # 🎨 ADAPTATION au style utilisateur
        user_style = context.get("user_style", "neutral")

        if user_style == "casual":
            responses.extend([
                "Cool ! Ça fait plaisir ! 😎 Tu as besoin de quoi ?",
                "Nickel ! Content pour toi ! 🤙 Je peux t'aider avec quoi ?",
                "Top ! Allez, dis-moi ce qu'il te faut ! 😄",
            ])
        elif user_style == "formal":
            responses.extend([
                "Parfait. Je suis ravi de l'apprendre. En quoi puis-je vous être utile ?",
                "Excellent. Comment puis-je vous assister aujourd'hui ?",
            ])

        # 🎯 PERSONNALISATION selon le nombre d'interactions
        total_interactions = context.get("total_interactions", 0)

        if total_interactions > 20:
            responses.append("Super ! Content que tu ailles toujours bien ! 🤗 Qu'est-ce que je peux faire pour toi aujourd'hui ?")

        return self._get_random_response(responses)

    def _generate_compliment_response(
        self, user_input: str, _context: Dict[str, Any]
    ) -> str:
        """Génère une réponse aux compliments"""
        responses = [
            "Merci beaucoup ! Ça me fait vraiment plaisir ! 😊",
            "C'est très gentil, merci ! J'essaie toujours de faire de mon mieux !",
            "Aww, merci ! Vous êtes sympa ! C'est motivant pour moi !",
            "Merci pour ce compliment ! J'aime beaucoup vous aider !",
            "C'est gentil, merci ! J'espère continuer à vous être utile !",
        ]

        # Adaptation au style
        if "cool" in user_input.lower() or "sympa" in user_input.lower():
            responses.extend(
                [
                    "Merci, vous êtes cool aussi ! 😄",
                    "C'est sympa de dire ça ! Merci !",
                    "Cool, merci ! On fait une bonne équipe !",
                ]
            )
        elif (
            "drôle" in user_input.lower()
            or "rigolo" in user_input.lower()
            or "marrant" in user_input.lower()
        ):
            responses = [
                "Merci ! J'aime bien faire rire ! 😄",
                "Content que ça vous amuse ! J'aime l'humour !",
                "Hihi, merci ! J'essaie d'être un peu drôle parfois ! 😊",
                "Ça me fait plaisir de vous faire sourire ! 😁",
                "Merci ! L'humour rend tout plus agréable !",
            ]

        return self._get_random_response(responses)

    def _generate_laughter_response(
        self, user_input: str, _context: Dict[str, Any]
    ) -> str:
        """Génère une réponse aux rires et expressions d'amusement"""
        responses = [
            "Content que ça vous fasse rire ! 😄",
            "Hihi, j'aime bien quand on s'amuse ensemble ! 😊",
            "Ah ça fait plaisir de vous entendre rire ! 😁",
            "Super ! Rien de mieux qu'un bon moment de rigolade ! 🤣",
            "Excellent ! J'aime votre réaction ! 😄",
            "Parfait ! Un peu d'humour ça fait du bien ! 😊",
            "Génial ! Vous avez l'air de bonne humeur ! 😁",
        ]

        # Adaptation selon le type de rire
        if "mdr" in user_input.lower() or "lol" in user_input.lower():
            responses.extend(
                [
                    "MDR ! Content que ça vous plaise autant ! 😂",
                    "LOL ! C'est parti pour la rigolade ! 🤣",
                ]
            )
        elif len(user_input) > 6:  # Long rire type "hahahahaha"
            responses.extend(
                [
                    "Wow, ça vous a vraiment fait rire ! 😂",
                    "Carrément ! Vous riez aux éclats ! 🤣",
                ]
            )

        return self._get_random_response(responses)

    def _generate_code_response(self, user_input: str, _context: Dict[str, Any]) -> str:
        """Génère une réponse pour les demandes de code"""
        try:
            # Détection du langage demandé
            user_lower = user_input.lower()
            if "javascript" in user_lower or "js" in user_lower:
                language = "javascript"
            elif "html" in user_lower:
                language = "html"
            elif "css" in user_lower:
                language = "css"
            elif "java" in user_lower:
                language = "java"
            elif "c++" in user_lower or "cpp" in user_lower:
                language = "cpp"
            elif "c " in user_lower:
                language = "c"
            else:
                language = "python"

            # Appel asynchrone au générateur avancé, compatible thread
            try:
                loop = asyncio.get_running_loop()
                coro = self.code_generator.generate_code(user_input, language)
                result = loop.run_until_complete(coro)
            except RuntimeError:
                # Pas de boucle en cours (cas thread secondaire)
                loop = asyncio.new_event_loop()
                try:
                    asyncio.set_event_loop(loop)
                    result = loop.run_until_complete(
                        self.code_generator.generate_code(user_input, language)
                    )
                finally:
                    loop.close()

            code = result.get("code", "")
            explanation = result.get("explanation", "")
            source = result.get("source", "")
            rating = result.get("rating", "")
            debug = result.get("debug", "")

            intro_messages = [
                "Voici le code que j'ai généré pour vous :",
                "J'ai créé ce code selon votre demande :",
                "Voilà ce que j'ai préparé pour vous :",
                "J'espère que ce code vous aidera :",
            ]
            intro = self._get_random_response(intro_messages)
            details = f"\n\n(Source : {source} | Note : {rating}/5)"
            if explanation:
                details += f"\n\nExplication : {explanation}"
            if debug:
                details += f"\n\n[DEBUG]\n{debug}"
            return f"{intro}\n\n```{language}\n{code}\n```{details}"
        except Exception as e:
            return f"Désolé, j'ai eu un problème pour générer le code : {str(e)}"

    def _generate_help_response(self, _user_input: str, context: Dict[str, Any]) -> str:
        """Génère une réponse d'aide contextuelle PERSONNALISÉE"""
        help_text = """🤖 Aide 🤖

💬 **Pour discuter :** Posez-moi vos questions naturellement
📄 **Pour les documents :** Utilisez les boutons pour traiter vos PDF/DOCX, puis demandez-moi de les résumer
💻 **Pour le code :** Traitez vos fichiers Python, puis demandez-moi de les expliquer
🌐 **Pour la recherche internet :** Dites "Cherche sur internet [sujet]"
😄 **Pour l'humour :** Demandez-moi une blague !

🎯 **Exemples :**
• "Résume le document" - après avoir traité un PDF
• "Explique ce code" - après avoir traité un fichier Python
• "Génère une fonction pour..." - pour créer du code
• "Cherche sur internet les actualités Python"
• "Raconte-moi une blague"
• "Comment créer une liste en Python ?"
• "Qui es-tu ?" - pour connaître mes capacités"""

        # 🎯 AIDE CONTEXTUELLE selon le nombre d'interactions
        total_interactions = context.get("total_interactions", 0)

        if total_interactions <= 2:
            # Nouvel utilisateur
            help_text += "\n\n🎉 **Bienvenue !** C'est votre première fois ? N'hésitez pas à explorer mes capacités ! Je suis là pour vous guider."
        elif total_interactions > 50:
            # Utilisateur expert
            help_text += "\n\n🚀 **Mode Expert :** Je vois que vous maîtrisez déjà bien mes fonctionnalités ! N'hésitez pas pour des questions avancées."

        # 📚 DOCUMENTS en mémoire
        if self._has_documents_in_memory():
            docs_count = len(self.conversation_memory.get_document_content())
            help_text += f"\n\n📚 **Documents disponibles :** Vous avez **{docs_count}** document(s) en mémoire que je peux analyser."

        # 💻 FICHIERS CODE en mémoire
        code_files_count = len(self.session_context.get("code_files_processed", []))
        if code_files_count > 0:
            help_text += f"\n\n💻 **Code disponible :** J'ai **{code_files_count}** fichier(s) code en mémoire pour analyse."

        # 🕐 DURÉE DE SESSION
        session_duration = context.get("session_duration", 0)
        minutes = int(session_duration // 60)
        if minutes > 30:
            help_text += f"\n\n⏱️ **Session longue :** Vous êtes là depuis {minutes} minutes ! Prenez une pause si besoin ! 😊"

        # 🎨 ADAPTATION au style (remplacer vouvoiement par tutoiement si casual)
        user_style = context.get("user_style", "neutral")
        if user_style == "casual":
            help_text = help_text.replace("Posez-moi", "Pose-moi").replace("Utilisez", "Utilise").replace("Traitez", "Traite").replace("Dites", "Dis").replace("Demandez-moi", "Demande-moi")

        return help_text

    def _generate_thank_you_response(self, context: Dict[str, Any]) -> str:
        """Génère une réponse aux remerciements PERSONNALISÉE selon le contexte"""
        # Réponses de base
        responses = [
            "De rien ! C'était un plaisir de vous aider ! 😊",
            "Je vous en prie ! N'hésitez pas si vous avez d'autres questions !",
            "Avec plaisir ! C'est pour ça que je suis là !",
            "Pas de quoi ! J'espère que ça vous a été utile !",
        ]

        # 🎯 PERSONNALISATION selon le nombre d'interactions
        total_interactions = context.get("total_interactions", 0)

        if total_interactions == 1:
            # Première interaction
            responses.extend([
                "Avec grand plaisir ! 😊 N'hésitez surtout pas à me solliciter à nouveau !",
                "De rien ! Content d'avoir pu vous aider dès notre première conversation ! 🌟",
            ])
        elif 2 <= total_interactions <= 10:
            # Utilisateur récent
            responses.extend([
                "Toujours un plaisir ! J'apprécie nos échanges ! 😊",
                "Avec plaisir ! On commence à bien se connaître ! 🤝",
            ])
        elif 11 <= total_interactions <= 50:
            # Utilisateur régulier
            responses.extend([
                "De rien ! Toujours là pour nos conversations régulières ! 💬",
                "Avec plaisir ! J'apprécie vraiment nos échanges fréquents ! 🤗",
            ])
        elif total_interactions > 50:
            # Utilisateur fidèle
            responses.extend([
                f"Toujours un plaisir après {total_interactions} conversations ! 🚀",
                "De rien ! C'est un honneur de t'accompagner depuis si longtemps ! 🌟",
                "Avec un immense plaisir ! Notre collaboration est précieuse ! 💎",
            ])

        # 🕐 PERSONNALISATION selon la durée de session
        session_duration = context.get("session_duration", 0)
        minutes = int(session_duration // 60)

        if minutes > 60:
            # Session très longue (>1h)
            responses.append(f"Merci ! Content d'avoir pu t'aider pendant ces {minutes} minutes ! 🚀")
        elif minutes > 30:
            # Session longue (30min-1h)
            responses.append("De rien ! Merci pour cette belle session de travail ! 💪")

        # 🎨 ADAPTATION au style utilisateur
        user_style = context.get("user_style", "neutral")

        if user_style == "casual":
            responses.extend([
                "De rien, c'était cool ! 😎",
                "Avec plaisir, toujours dispo pour toi ! 🤙",
            ])
        elif user_style == "formal":
            responses.extend([
                "Je vous en prie, c'est toujours un plaisir de vous assister.",
                "Avec plaisir. N'hésitez pas à me solliciter de nouveau.",
            ])

        return self._get_random_response(responses)

    def _generate_goodbye_response(self, context: Dict[str, Any]) -> str:
        """Génère une réponse d'au revoir PERSONNALISÉE selon le contexte"""
        # Réponses de base
        responses = [
            "À bientôt ! Passez une excellente journée ! 👋",
            "Au revoir ! N'hésitez pas à revenir si besoin ! 😊",
            "Salut ! À la prochaine fois ! 🤗",
        ]

        # 🕐 PERSONNALISATION selon la durée de session
        session_duration = context.get("session_duration", 0)
        minutes = int(session_duration // 60)

        if minutes < 5:
            # Session très courte
            responses.extend([
                "À bientôt ! Même si c'était court, j'espère avoir pu aider ! 👋",
                "Au revoir ! N'hésite pas à revenir plus longtemps la prochaine fois ! 😊",
            ])
        elif 5 <= minutes <= 30:
            # Session normale
            responses.extend([
                "Au revoir ! Merci pour cet échange ! À très bientôt ! 😊",
                f"À plus ! Ces {minutes} minutes étaient agréables ! 👋",
            ])
        elif 30 < minutes <= 60:
            # Session longue
            responses.extend([
                f"Au revoir ! Merci pour cette belle session de {minutes} minutes ! 🚀",
                "Salut ! C'était une conversation enrichissante ! À bientôt ! 💬",
            ])
        else:
            # Session très longue (>1h)
            heures = minutes // 60
            responses.extend([
                f"Au revoir ! Merci pour ces {heures}h passées ensemble ! C'était génial ! 🌟",
                "Salut ! Quelle longue et passionnante session ! Repose-toi bien ! 😊",
            ])

        # 🎯 PERSONNALISATION selon le nombre d'interactions
        total_interactions = context.get("total_interactions", 0)

        if total_interactions == 1:
            responses.append("Au revoir ! J'espère vous revoir bientôt pour d'autres discussions ! 🌟")
        elif total_interactions > 100:
            responses.extend([
                f"À plus tard ! Nos {total_interactions} conversations sont précieuses ! 💎",
                "Au revoir mon ami ! Toujours un plaisir de te retrouver ! 🤗",
            ])

        # 🎨 ADAPTATION au style utilisateur
        user_style = context.get("user_style", "neutral")

        if user_style == "casual":
            responses.extend([
                "Salut ! À plus ! 🤙",
                "Ciao ! C'était cool ! 😎",
            ])
        elif user_style == "formal":
            responses.extend([
                "Au revoir. Ce fut un plaisir de vous assister.",
                "À bientôt. N'hésitez pas à me solliciter de nouveau.",
            ])

        return self._get_random_response(responses)

    def _generate_affirmation_response(self) -> str:
        """Génère une réponse aux affirmations"""
        responses = [
            "Parfait ! Content que vous soyez d'accord ! 😊",
            "Excellent ! On est sur la même longueur d'onde !",
            "Super ! J'aime quand on se comprend bien !",
            "Génial ! Que puis-je faire d'autre pour vous ?",
        ]

        return self._get_random_response(responses)

    def _generate_negation_response(self, _context: Dict[str, Any]) -> str:
        """Génère une réponse aux négations"""
        responses = [
            "D'accord, pas de problème ! Que préférez-vous ?",
            "Compris ! Comment puis-je mieux vous aider ?",
            "Pas de souci ! Dites-moi ce que vous voulez vraiment.",
            "OK, on peut essayer autre chose ! Qu'est-ce qui vous conviendrait mieux ?",
        ]

        return self._get_random_response(responses)

    def _generate_default_response(
        self, user_input: str, context: Dict[str, Any]
    ) -> str:
        """Génère une réponse par défaut intelligente"""
        # Analyser le type de demande
        user_lower = user_input.lower()

        # NOUVELLE VÉRIFICATION : Questions sur les capacités non détectées
        if any(
            phrase in user_lower
            for phrase in [
                "à quoi tu sers",
                "à quoi sert tu",
                "à quoi sers tu",
                "à quoi tu sert",
                "tu sers à quoi",
                "tu sert à quoi",
                "tu sers a quoi",
                "tu sert a quoi",
                "ton utilité",
                "votre utilité",
            ]
        ):
            return self._generate_capabilities_response(user_input, context)

        # Si ça ressemble à une demande de code
        if any(
            word in user_lower
            for word in ["génère", "crée", "code", "fonction", "script"]
        ):
            try:
                code_response = self.code_generator.generate_code(user_input)
                return f"Voici ce que j'ai généré pour vous :\n\n{code_response}"
            except Exception:
                return "Je peux générer du code ! Soyez plus spécifique : voulez-vous une fonction, une classe, ou un script complet ?"

        # Si ça ressemble à une question générale sur la programmation
        elif any(
            word in user_lower
            for word in [
                "comment créer",
                "comment utiliser",
                "comment faire",
                "comment déclarer",
            ]
        ):
            return self._answer_programming_question(user_input, context)

        # Si ça ressemble à une question générale autre
        elif any(
            word in user_lower for word in ["comment", "pourquoi", "qu'est-ce", "quoi"]
        ):
            return "Intéressant ! Je peux vous aider à explorer cette question. Voulez-vous que je cherche des informations sur internet ou préférez-vous en discuter ?"

        # Réponse encourageante par défaut
        return "Je ne suis pas sûr de bien comprendre. Pouvez-vous reformuler ? Je peux vous aider avec l'analyse de documents, la génération de code, ou simplement discuter !"

    def _tell_joke(self) -> str:
        """Raconte une blague aléatoire du stock en évitant les répétitions"""
        if not self.jokes:
            return "Désolé, je n'ai pas de blague en stock pour le moment ! 😅"

        # Si on a utilisé la plupart des blagues, on reset
        if len(self.used_jokes) >= len(self.jokes) * self.jokes_reset_threshold:
            self.used_jokes.clear()
            intro_reset = "Bon, j'ai épuisé mon stock, je recommence ! 😄\n\n"
        else:
            intro_reset = ""

        # Trouver les blagues non utilisées
        available_jokes = []
        for i, joke in enumerate(self.jokes):
            if i not in self.used_jokes:
                available_jokes.append((i, joke))

        # Si plus de blagues disponibles, reset complet
        if not available_jokes:
            self.used_jokes.clear()
            available_jokes = [(i, joke) for i, joke in enumerate(self.jokes)]
            intro_reset = "J'ai fait le tour de mes blagues, je recommence ! 😄\n\n"

        # Sélectionner une blague aléatoire parmi celles disponibles
        joke_index, selected_joke = random.choice(available_jokes)

        # Marquer cette blague comme utilisée
        self.used_jokes.add(joke_index)

        # Phrases d'introduction variées
        introductions = [
            "Voici une petite blague pour vous ! 😄",
            "Tiens, j'en ai une bonne ! 😆",
            "Allez, une petite blague pour détendre l'atmosphère ! 😊",
            "Haha, j'en connais une excellente ! 🤣",
            "Prêt pour une blague ? 😄",
            "Je vais vous faire sourire ! 😁",
            "En voici une qui va vous plaire ! 😉",
            "Attendez, j'en ai une drôle ! 🤭",
        ]

        # Choisir une introduction différente si possible
        if hasattr(self, "last_joke_intro"):
            available_intros = [
                intro for intro in introductions if intro != self.last_joke_intro
            ]
            if available_intros:
                intro = random.choice(available_intros)
            else:
                intro = random.choice(introductions)
        else:
            intro = random.choice(introductions)

        # Sauvegarder l'introduction pour éviter la répétition
        self.last_joke_intro = intro

        # Message de statut si on approche de la fin du stock
        status_message = ""
        remaining = len(self.jokes) - len(self.used_jokes)
        if remaining <= 2 and len(self.jokes) > 3:
            status_message = f"\n\n😅 Plus que {remaining} blague(s) dans mon stock !"

        return f"{intro_reset}{intro}\n\n{selected_joke}{status_message}"

    def _handle_internet_search(self, user_input: str, context: Dict[str, Any]) -> str:
        """
        Gère les demandes de recherche internet

        Args:
            user_input: Question de l'utilisateur
            context: Contexte de la conversation
        Returns:
            str: Résumé des résultats de recherche
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
        if not search_query:
            return """🔍 **Recherche internet**

Je n'ai pas bien compris ce que vous voulez rechercher. 

**Exemples de demandes :**
• "Cherche sur internet les actualités Python"
• "Recherche des informations sur l'intelligence artificielle"
• "Trouve-moi des news sur Tesla"
• "Peux-tu chercher comment faire du pain ?"

Reformulez votre demande en précisant ce que vous voulez rechercher."""
        # Effectuer la recherche avec le moteur de recherche internet
        try:
            print(f"🌐 Lancement de la recherche pour: '{search_query}'")
            # Note: search_and_summarize n'accepte que le query en paramètre
            result = self.internet_search.search_and_summarize(search_query)
            return result
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

    def _extract_search_query(self, user_input: str) -> str:
        """
        Extrait la requête de recherche de l'input utilisateur

        Args:
            user_input: Input de l'utilisateur

        Returns:
            str: Requête de recherche extraite
        """

        # Nettoyage du prompt pour retirer tout contexte documentaire ou artefact système
        cleaned = user_input
        # Supprimer les lignes contenant des mentions de contexte documentaire
        cleaned = re.sub(
            r"(?im)^.*(contexte des documents disponibles|contexte:|mémoire:).*$",
            "",
            cleaned,
        )
        # Supprimer tout ce qui précède 'question:' (y compris la ligne)
        cleaned = re.sub(r"(?is)^.*question\s*:\s*", "", cleaned)
        # Supprimer les artefacts de prompt système (ex: 'system:', 'assistant:', etc.)
        cleaned = re.sub(r"(?im)^\s*(system|assistant|user)\s*:\s*", "", cleaned)
        # Supprimer les lignes vides
        cleaned = "\n".join([line for line in cleaned.splitlines() if line.strip()])
        # Nettoyer les espaces
        cleaned = cleaned.strip()

        user_lower = cleaned.lower().strip()
        # Patterns pour extraire la requête
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

        # Fallback: si aucun pattern ne correspond, essayer de deviner
        for word in [
            "cherche",
            "recherche",
            "trouve",
            "sur",
            "internet",
            "web",
            "google",
            "en",
            "ligne",
            "moi",
            "des",
            "informations",
        ]:
            if user_lower.startswith(word):
                user_lower = user_lower[len(word) :].strip()

        return user_lower if len(user_lower) > 2 else ""

    def _handle_url_summarization(
        self, user_input: str
    ) -> str:
        """
        Gère les demandes de résumé d'URL directe

        Args:
            user_input: Question de l'utilisateur contenant une URL
            context: Contexte de la conversation

        Returns:
            str: Résumé du contenu de la page
        """
        # Extraire l'URL de l'input utilisateur
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

        # Utiliser la méthode summarize_url du moteur de recherche
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
        """
        Extrait une URL de l'input utilisateur

        Args:
            user_input: Input de l'utilisateur

        Returns:
            str: URL extraite ou chaîne vide si aucune URL trouvée
        """
        # Pattern pour détecter les URLs HTTP/HTTPS
        url_pattern = r"https?://[^\s<>\"{}\\|^`\[\]]+"

        # Rechercher toutes les URLs dans le texte
        urls = re.findall(url_pattern, user_input)

        if urls:
            # Retourner la première URL trouvée
            url = urls[0]
            # Nettoyer les caractères de ponctuation en fin d'URL
            url = url.rstrip(".,!?;:)")
            return url

        return ""

    def _detect_search_type(self, user_input: str) -> str:
        """
        Détecte le type de recherche demandé

        Args:
            user_input: Input de l'utilisateur

        Returns:
            str: Type de recherche
        """
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

    def _answer_programming_question(
        self, user_input: str, context: Dict[str, Any]
    ) -> str:
        """Répond aux questions de programmation avec des exemples pratiques et intelligence avancée"""
        user_lower = user_input.lower()

        # 🚀 ANALYSE INTELLIGENTE DE LA QUESTION
        complexity_level = self._analyze_user_intelligence_level(user_input, context)

        # Réponse de base adaptée au niveau
        base_response = ""

        # Détection du type de question et réponse avec exemples
        if any(word in user_lower for word in ["liste", "list"]):
            if "différence" in user_lower and (
                "dictionnaire" in user_lower or "dict" in user_lower
            ):
                base_response = self._explain_list_vs_dict_difference()
            else:
                base_response = self._explain_python_lists()
        elif any(word in user_lower for word in ["dictionnaire", "dict"]):
            base_response = self._explain_python_dictionaries()
        elif any(word in user_lower for word in ["fonction", "def"]):
            base_response = self._explain_python_functions()
        elif any(word in user_lower for word in ["variable"]):
            base_response = self._explain_python_variables()
        elif any(word in user_lower for word in ["boucle", "for", "while"]):
            base_response = self._explain_python_loops()
        elif any(word in user_lower for word in ["condition", "if", "else"]):
            base_response = self._explain_python_conditions()
        elif any(word in user_lower for word in ["classe", "class", "objet"]):
            base_response = self._explain_python_classes()
        elif any(
            word in user_lower
            for word in ["déboguer", "debug", "débogage", "debugger", "erreur"]
        ):
            base_response = self._explain_python_debugging()
        else:
            base_response = self._generate_general_programming_help()

        # 🧠 AJOUT D'INTELLIGENCE CONTEXTUELLE
        if complexity_level == "expert":
            base_response += "\n\n💡 **Conseil d'expert** : Consultez PEP 8 pour les conventions de style Python"
            base_response += "\n🔧 **Optimisation** : Considérez l'utilisation de type hints pour une meilleure maintenabilité"
        elif complexity_level == "intermediate":
            base_response += (
                "\n\n⚡ **Conseil pro** : Testez votre code avec des cas limites"
            )
            base_response += "\n📚 **Prochaine étape** : Explorez les décorateurs et les context managers"

        # 🎯 PRÉDICTIONS INTELLIGENTES
        predictions = self._predict_user_needs(user_input, context)
        if predictions:
            base_response += f"\n\n{predictions[0]}"

        return base_response

    def _answer_general_question(self, user_input: str, context: Dict[str, Any]) -> str:
        """Répond aux questions générales avec adaptation intelligente"""
        user_lower = user_input.lower().strip()

        # Extraction du sujet de la question
        subject = self._extract_question_subject(user_input)

        # Base de connaissances pour réponses rapides
        quick_answers = {
            "pomodoro": """🍅 **La technique Pomodoro**

C'est une méthode de gestion du temps créée par Francesco Cirillo :

⏰ **Le principe :**
• Travaillez 25 minutes concentré (= 1 pomodoro)  
• Prenez une pause de 5 minutes
• Répétez 4 fois
• Puis une grande pause de 15-30 minutes

🎯 **Pourquoi c'est efficace :**
• Améliore la concentration
• Évite l'épuisement mental  
• Aide à estimer le temps nécessaire
• Réduit les distractions

📱 **Comment faire :**
• Utilisez un timer (physique ou app)
• Choisissez une tâche
• Démarrez le timer 25 min
• Travaillez sans interruption
• Stop quand ça sonne !

C'est super pour la productivité ! 🚀""",
            "intelligence artificielle": """🤖 **L'Intelligence Artificielle (IA)**

L'IA, c'est la capacité des machines à simuler l'intelligence humaine.

🧠 **Types principaux :**
• **IA faible** : Spécialisée (comme moi !)
• **IA forte** : Général (pas encore créée)
• **Machine Learning** : Apprend des données
• **Deep Learning** : Réseaux de neurones

💡 **Applications courantes :**
• Assistants vocaux (Siri, Alexa)
• Recommandations (Netflix, YouTube)
• Traduction automatique
• Reconnaissance d'images
• Voitures autonomes

🎯 **Moi par exemple :** Je suis une IA locale qui peut vous aider avec vos documents, générer du code, et discuter naturellement !""",
        }

        # Recherche de réponse rapide
        for keyword, answer in quick_answers.items():
            if keyword in user_lower:
                return answer

        # Réponse générale adaptative
        style = self._detect_user_style(context)

        if style == "casual":
            return f"🤔 Excellente question sur **{subject}** !\n\nJe peux chercher des infos là-dessus si tu veux ! Dis-moi 'cherche sur internet {subject}' et je te trouve les dernières infos ! 🔍\n\nOu alors pose-moi une question plus spécifique et je ferai de mon mieux pour t'aider ! 😊"
        else:
            return f"📚 Très bonne question concernant **{subject}** !\n\nJe peux effectuer une recherche internet pour vous fournir des informations actualisées. Dites-moi 'cherche sur internet {subject}' et je vous donnerai un résumé détaillé.\n\nVous pouvez aussi me poser une question plus spécifique et je ferai de mon mieux pour vous renseigner ! 🎯"

    def _extract_question_subject(self, user_input: str) -> str:
        """Extrait le sujet principal d'une question"""
        # Supprimer les mots de question
        cleaned = user_input.lower()
        question_words = [
            "c'est quoi",
            "qu'est-ce que",
            "que signifie",
            "explique moi",
            "dis moi",
        ]

        for word in question_words:
            cleaned = cleaned.replace(word, "").strip()

        # Nettoyer la ponctuation
        cleaned = cleaned.strip("?!.,;:")

        return cleaned if cleaned else "ce sujet"

    def _detect_user_style(self, context: Dict[str, Any]) -> str:
        """Détecte le style de communication de l'utilisateur"""
        # Analyser l'historique récent pour détecter le style
        recent_messages = context.get("recent_user_messages", [])

        casual_indicators = [
            "salut",
            "sa va",
            "wesh",
            "lol",
            "mdr",
            "cool",
            "sympa",
            "ok",
            "ouais",
            "wsh",
        ]
        formal_indicators = [
            "bonjour",
            "bonsoir",
            "merci beaucoup",
            "s'il vous plaît",
            "pouvez-vous",
        ]

        if any(
            any(indicator in msg.lower() for indicator in casual_indicators)
            for msg in recent_messages
        ):
            return "casual"
        elif any(
            any(indicator in msg.lower() for indicator in formal_indicators)
            for msg in recent_messages
        ):
            return "formal"
        else:
            return "neutral"

    def _explain_python_lists(self) -> str:
        """Explique comment créer et utiliser les listes en Python"""
        return """🐍 **Comment créer une liste en Python**

Une liste est une collection ordonnée d'éléments modifiables. Voici comment s'y prendre :

📝 **Création d'une liste :**
```python
# Liste vide
ma_liste = []

# Liste avec des éléments
fruits = ["pomme", "banane", "orange"]
nombres = [1, 2, 3, 4, 5]
mixte = ["texte", 42, True, 3.14]
```

🔧 **Opérations courantes :**
```python
# Ajouter un élément
fruits.append("kiwi")          # ["pomme", "banane", "orange", "kiwi"]

# Insérer à une position
fruits.insert(1, "fraise")     # ["pomme", "fraise", "banane", "orange", "kiwi"]

# Accéder à un élément
premier_fruit = fruits[0]       # "pomme"
dernier_fruit = fruits[-1]      # "kiwi"

# Modifier un élément
fruits[0] = "poire"            # ["poire", "fraise", "banane", "orange", "kiwi"]

# Supprimer un élément
fruits.remove("fraise")        # ["poire", "banane", "orange", "kiwi"]
del fruits[0]                  # ["banane", "orange", "kiwi"]

# Longueur de la liste
taille = len(fruits)           # 3
```

💡 **Conseils pratiques :**
• Les listes sont indexées à partir de 0
• Utilisez des indices négatifs pour partir de la fin
• Les listes peuvent contenir différents types de données"""

    def _explain_python_dictionaries(self) -> str:
        """Explique comment créer et utiliser les dictionnaires en Python"""
        return """🐍 **Comment créer un dictionnaire en Python**

Un dictionnaire stocke des paires clé-valeur. Parfait pour associer des données !

📝 **Création d'un dictionnaire :**
```python
# Dictionnaire vide
mon_dict = {}

# Dictionnaire avec des données
personne = {
    "nom": "Dupont",
    "age": 30,
    "ville": "Paris"
}

# Autre méthode
coords = dict(x=10, y=20, z=5)
```

🔧 **Opérations courantes :**
```python
# Accéder à une valeur
nom = personne["nom"]           # "Dupont"
age = personne.get("age", 0)    # 30 (ou 0 si pas trouvé)

# Ajouter/modifier une valeur
personne["email"] = "dupont@example.com"
personne["age"] = 31

# Vérifier si une clé existe
if "nom" in personne:
    print("Nom trouvé !")

# Supprimer un élément
del personne["ville"]
email = personne.pop("email", "")  # Récupère et supprime

# Récupérer toutes les clés/valeurs
cles = list(personne.keys())       # ["nom", "age"]
valeurs = list(personne.values())  # ["Dupont", 31]
```

💡 **Conseils pratiques :**
• Les clés doivent être uniques et immuables
• Utilisez `get()` pour éviter les erreurs
• Parfait pour structurer des données complexes"""

    def _explain_python_functions(self) -> str:
        """Explique comment créer des fonctions en Python"""
        return """🐍 **Comment créer une fonction en Python**

Les fonctions permettent de réutiliser du code et d'organiser votre programme.

📝 **Syntaxe de base :**
```python
def nom_fonction(paramètres):
    \"\"\"Description de la fonction\"\"\"
    # Code de la fonction
    return résultat  # optionnel
```

🔧 **Exemples pratiques :**
```python
# Fonction simple
def dire_bonjour():
    print("Bonjour !")

# Fonction avec paramètres
def saluer(nom, age=25):
    return f"Salut {nom}, tu as {age} ans !"

# Fonction avec calcul
def calculer_aire_rectangle(longueur, largeur):
    \"\"\"Calcule l'aire d'un rectangle\"\"\"
    aire = longueur * largeur
    return aire

# Fonction avec plusieurs retours
def diviser(a, b):
    if b == 0:
        return None, "Division par zéro impossible"
    return a / b, "OK"

# Utilisation
dire_bonjour()                          # Affiche: Bonjour !
message = saluer("Alice")               # "Salut Alice, tu as 25 ans !"
message2 = saluer("Bob", 30)            # "Salut Bob, tu as 30 ans !"
aire = calculer_aire_rectangle(5, 3)    # 15
resultat, statut = diviser(10, 2)       # 5.0, "OK"
```

💡 **Bonnes pratiques :**
• Utilisez des noms descriptifs
• Ajoutez une docstring pour documenter
• Une fonction = une responsabilité
• Utilisez des paramètres par défaut quand c'est utile"""

    def _explain_python_variables(self) -> str:
        """Explique comment créer et utiliser les variables en Python"""
        return """🐍 **Comment créer des variables en Python**

Les variables stockent des données que vous pouvez utiliser dans votre programme.

📝 **Création de variables :**
```python
# Texte (string)
nom = "Alice"
prenom = 'Bob'
message = \"\"\"Texte
sur plusieurs
lignes\"\"\"

# Nombres
age = 25                    # Entier (int)
taille = 1.75              # Décimal (float)
complexe = 3 + 4j          # Nombre complexe

# Booléens
est_majeur = True
est_mineur = False

# Collections
fruits = ["pomme", "banane"]        # Liste
personne = {"nom": "Dupont"}        # Dictionnaire
coordonnees = (10, 20)              # Tuple (immuable)
```

🔧 **Opérations avec variables :**
```python
# Assignation multiple
x, y, z = 1, 2, 3
nom, age = "Alice", 30

# Échange de valeurs
a, b = 5, 10
a, b = b, a                # a=10, b=5

# Opérations mathématiques
somme = x + y              # 3
produit = x * z            # 3
puissance = x ** 3         # 1

# Concaténation de texte
nom_complet = prenom + " " + nom    # "Bob Alice"
presentation = f"Je suis {nom}, {age} ans"  # f-string

# Vérification du type
type(age)                  # <class 'int'>
isinstance(taille, float)  # True
```

💡 **Règles importantes :**
• Noms en minuscules avec _ pour séparer
• Pas d'espaces, pas de chiffres au début
• Évitez les mots-clés Python (if, for, class...)
• Soyez descriptifs : `age_utilisateur` plutôt que `a`"""

    def _explain_python_loops(self) -> str:
        """Explique les boucles en Python"""
        return """🐍 **Comment utiliser les boucles en Python**

Les boucles permettent de répéter du code automatiquement.

📝 **Boucle for (pour itérer) :**
```python
# Boucle sur une liste
fruits = ["pomme", "banane", "orange"]
for fruit in fruits:
    print(f"J'aime les {fruit}s")

# Boucle avec un range
for i in range(5):          # 0, 1, 2, 3, 4
    print(f"Compteur: {i}")

for i in range(2, 8, 2):    # 2, 4, 6 (début, fin, pas)
    print(f"Nombre pair: {i}")

# Boucle avec index et valeur
for index, fruit in enumerate(fruits):
    print(f"{index}: {fruit}")

# Boucle sur un dictionnaire
personne = {"nom": "Alice", "age": 30}
for cle, valeur in personne.items():
    print(f"{cle}: {valeur}")
```

🔄 **Boucle while (tant que) :**
```python
# Boucle while classique
compteur = 0
while compteur < 5:
    print(f"Compteur: {compteur}")
    compteur += 1          # Important: incrémenter !

# Boucle infinie contrôlée
while True:
    reponse = input("Continuez ? (o/n): ")
    if reponse.lower() == 'n':
        break              # Sort de la boucle
    print("On continue !")
```

🛑 **Contrôle des boucles :**
```python
# break : sort de la boucle
for i in range(10):
    if i == 5:
        break              # Sort quand i=5
    print(i)               # Affiche 0,1,2,3,4

# continue : passe à l'itération suivante
for i in range(5):
    if i == 2:
        continue           # Saute i=2
    print(i)               # Affiche 0,1,3,4
```

💡 **Conseils pratiques :**
• `for` pour un nombre connu d'itérations
• `while` pour des conditions variables
• Attention aux boucles infinies avec `while`
• Utilisez `enumerate()` si vous avez besoin de l'index"""

    def _explain_python_conditions(self) -> str:
        """Explique les conditions en Python"""
        return """🐍 **Comment utiliser les conditions en Python**

Les conditions permettent d'exécuter du code selon certains critères.

📝 **Structure if/elif/else :**
```python
age = 18

if age >= 18:
    print("Vous êtes majeur")
elif age >= 16:
    print("Vous pouvez conduire")
elif age >= 13:
    print("Vous êtes adolescent")
else:
    print("Vous êtes enfant")
```

🔍 **Opérateurs de comparaison :**
```python
# Égalité et inégalité
x == y          # Égal à
x != y          # Différent de
x > y           # Supérieur à
x >= y          # Supérieur ou égal
x < y           # Inférieur à
x <= y          # Inférieur ou égal

# Appartenance
"a" in "maison"     # True
"pomme" in fruits   # True si pomme dans la liste

# Identité
x is None           # True si x vaut None
x is not None       # True si x ne vaut pas None
```

🔗 **Opérateurs logiques :**
```python
age = 25
nom = "Alice"

# AND (et) - toutes les conditions doivent être vraies
if age >= 18 and nom == "Alice":
    print("Alice est majeure")

# OR (ou) - au moins une condition doit être vraie
if age < 18 or nom == "Bob":
    print("Mineur ou Bob")

# NOT (non) - inverse la condition
if not (age < 18):
    print("Pas mineur = majeur")
```

🎯 **Conditions avancées :**
```python
# Conditions multiples
note = 85
if 80 <= note <= 100:      # Équivalent à: note >= 80 and note <= 100
    print("Excellent !")

# Conditions avec fonctions
def est_pair(nombre):
    return nombre % 2 == 0

if est_pair(4):
    print("4 est pair")

# Opérateur ternaire (condition courte)
statut = "majeur" if age >= 18 else "mineur"
resultat = "pair" if x % 2 == 0 else "impair"

# Vérification d'existence
if fruits:                 # True si la liste n'est pas vide
    print("Il y a des fruits")

if nom:                    # True si nom n'est pas vide
    print(f"Bonjour {nom}")
```

💡 **Bonnes pratiques :**
• Utilisez des parenthèses pour clarifier les conditions complexes
• Préférez `is` et `is not` pour comparer avec `None`
• Évitez les conditions trop imbriquées
• Pensez aux cas limites (listes vides, valeurs None...)"""

    def _explain_python_classes(self) -> str:
        """Explique les classes en Python"""
        return """🐍 **Comment créer des classes en Python**

Les classes permettent de créer vos propres types d'objets avec propriétés et méthodes.

📝 **Syntaxe de base :**
```python
class Personne:
    \"\"\"Classe représentant une personne\"\"\"
    
    def __init__(self, nom, age):
        \"\"\"Constructeur : appelé à la création\"\"\"
        self.nom = nom          # Attribut
        self.age = age          # Attribut
        self.email = None       # Attribut optionnel
    
    def se_presenter(self):
        \"\"\"Méthode pour se présenter\"\"\"
        return f"Je suis {self.nom}, j'ai {self.age} ans"
    
    def avoir_anniversaire(self):
        \"\"\"Méthode pour vieillir d'un an\"\"\"
        self.age += 1
        print(f"Joyeux anniversaire ! Maintenant {self.age} ans")
```

🏗️ **Utilisation de la classe :**
```python
# Créer des objets (instances)
alice = Personne("Alice", 25)
bob = Personne("Bob", 30)

# Utiliser les méthodes
print(alice.se_presenter())     # "Je suis Alice, j'ai 25 ans"
bob.avoir_anniversaire()        # "Joyeux anniversaire ! Maintenant 31 ans"

# Accéder/modifier les attributs
alice.email = "alice@example.com"
print(f"Email: {alice.email}")

# Chaque objet est indépendant
print(f"Alice: {alice.age} ans")    # 25
print(f"Bob: {bob.age} ans")        # 31
```

🔧 **Exemple plus complet :**
```python
class CompteBancaire:
    \"\"\"Classe pour gérer un compte bancaire\"\"\"
    
    def __init__(self, proprietaire, solde_initial=0):
        self.proprietaire = proprietaire
        self.solde = solde_initial
        self.historique = []
    
    def deposer(self, montant):
        \"\"\"Déposer de l'argent\"\"\"
        if montant > 0:
            self.solde += montant
            self.historique.append(f"Dépôt: +{montant}€")
            return True
        return False
    
    def retirer(self, montant):
        \"\"\"Retirer de l'argent\"\"\"
        if 0 < montant <= self.solde:
            self.solde -= montant
            self.historique.append(f"Retrait: -{montant}€")
            return True
        return False
    
    def afficher_solde(self):
        \"\"\"Afficher le solde\"\"\"
        return f"Solde de {self.proprietaire}: {self.solde}€"

# Utilisation
compte = CompteBancaire("Alice", 1000)
compte.deposer(500)
compte.retirer(200)
print(compte.afficher_solde())      # "Solde de Alice: 1300€"
```

• `self` : référence à l'instance courante
• Attributs : variables de l'objet
• Méthodes : fonctions de l'objet
• Encapsulation : regrouper données et comportements"""

    def _explain_list_vs_dict_difference(self) -> str:
        """Explique la différence entre les listes et les dictionnaires"""
        return """📋 **Différence entre Liste et Dictionnaire en Python**

Voici les principales différences entre ces deux structures de données :

📋 **LISTES (list)**
```python
fruits = ["pomme", "banane", "orange"]
nombres = [1, 2, 3, 4, 5]
```

✅ **Caractéristiques des listes :**
• **Ordonnées** : Les éléments ont une position fixe
• **Indexées par position** : fruits[0] = "pomme"
• **Permettent les doublons** : [1, 1, 2, 2] est valide
• **Modifiables** : Ajouter, supprimer, modifier des éléments
• **Homogènes ou hétérogènes** : Même type ou types différents

🗂️ **DICTIONNAIRES (dict)**
```python
personne = {"nom": "Alice", "age": 30, "ville": "Paris"}
scores = {"Alice": 95, "Bob": 87, "Charlie": 92}
```

✅ **Caractéristiques des dictionnaires :**
• **Associatifs** : Chaque valeur a une clé unique
• **Indexés par clé** : personne["nom"] = "Alice"
• **Clés uniques** : Pas de doublons de clés
• **Modifiables** : Ajouter, supprimer, modifier des paires clé-valeur
• **Clés immuables** : String, nombre, tuple (pas de liste comme clé)

⚡ **Comparaison pratique :**
```python
# LISTE - Accès par position
fruits = ["pomme", "banane", "orange"]
print(fruits[1])        # "banane" (2ème élément)

# DICTIONNAIRE - Accès par clé
personne = {"nom": "Alice", "age": 30}
print(personne["nom"])  # "Alice" (valeur associée à "nom")
```

🎯 **Quand utiliser quoi ?**

**Utilisez une LISTE quand :**
• Vous avez une collection ordonnée d'éléments
• L'ordre importe (comme une playlist)
• Vous voulez accéder par position
• Vous pouvez avoir des doublons

**Utilisez un DICTIONNAIRE quand :**
• Vous voulez associer des clés à des valeurs
• Vous cherchez par "nom" plutôt que par position
• Vous stockez des propriétés d'un objet
• Vous voulez des accès rapides par clé

💡 **Exemple concret :**
```python
# Liste pour des courses (ordre peut importer)
courses = ["pain", "lait", "œufs", "pain"]  # pain 2 fois = OK

# Dictionnaire pour des informations personnelles
personne = {
    "nom": "Alice",
    "age": 30,
    "profession": "Développeuse"
}  # Chaque info a sa clé unique
```"""

    def _explain_python_debugging(self) -> str:
        """Explique comment déboguer du code Python"""
        return """🐍 **Comment déboguer du code Python**

Le débogage est essentiel pour identifier et corriger les erreurs dans votre code.

🔍 **1. Types d'erreurs courantes**
```python
# Erreur de syntaxe
print("Hello World"    # Manque la parenthèse fermante

# Erreur de type
age = "30"
age + 5                # Erreur: str + int

# Erreur d'index
liste = [1, 2, 3]
print(liste[5])        # Erreur: index n'existe pas

# Erreur de clé
person = {"nom": "Alice"}
print(person["age"])   # Erreur: clé n'existe pas
```

🛠️ **2. Techniques de débogage simples**
```python
# A. Print pour tracer l'exécution
def calculer_moyenne(notes):
    print(f"Notes reçues: {notes}")        # Vérifier l'entrée
    total = sum(notes)
    print(f"Total calculé: {total}")       # Vérifier le calcul
    moyenne = total / len(notes)
    print(f"Moyenne: {moyenne}")           # Vérifier le résultat
    return moyenne

# B. Print avec étiquettes claires
x = 10
y = 0
print(f"DEBUG: x={x}, y={y}")
if y != 0:
    resultat = x / y
    print(f"DEBUG: Résultat division = {resultat}")
else:
    print("DEBUG: Division par zéro évitée!")
```

🔧 **3. Utilisation du debugger Python (pdb)**
```python
import pdb

def fonction_problematique(a, b):
    pdb.set_trace()                    # Point d'arrêt
    resultat = a * b
    final = resultat + 10
    return final

# Commandes pdb utiles:
# n (next) : ligne suivante
# s (step) : entrer dans les fonctions
# l (list) : voir le code
# p variable : afficher une variable
# c (continue) : continuer l'exécution
# q (quit) : quitter
```

🚀 **4. Debugging avec VS Code**
```python
# Ajoutez des points d'arrêt en cliquant à gauche des numéros de ligne
# Utilisez F5 pour démarrer le débogage
# F10 : Ligne suivante
# F11 : Entrer dans la fonction
# Shift+F11 : Sortir de la fonction

def ma_fonction():
    a = 5
    b = 10
    c = a + b      # <- Point d'arrêt ici
    return c * 2
```

✅ **5. Bonnes pratiques de débogage**
```python
# A. Gestion d'erreurs avec try/except
def diviser_nombres(a, b):
    try:
        resultat = a / b
        return resultat
    except ZeroDivisionError:
        print("Erreur: Division par zéro!")
        return None
    except TypeError:
        print("Erreur: Types incompatibles!")
        return None

# B. Assertions pour vérifier les conditions
def calculer_racine(nombre):
    assert nombre >= 0, f"Le nombre doit être positif, reçu: {nombre}"
    return nombre ** 0.5

# C. Logging pour un suivi permanent
import logging
logging.basicConfig(level=logging.DEBUG)

def traiter_data(data):
    logging.debug(f"Traitement de {len(data)} éléments")
    for item in data:
        logging.debug(f"Traitement de l'élément: {item}")
        # ... traitement ...
```

🐛 **6. Stratégies de résolution**
```python
# A. Diviser pour régner - Isoler le problème
def fonction_complexe(data):
    # Au lieu de tout faire d'un coup:
    etape1 = nettoyer_data(data)
    print(f"Après nettoyage: {etape1}")
    
    etape2 = transformer_data(etape1)
    print(f"Après transformation: {etape2}")
    
    resultat = calculer_final(etape2)
    return resultat

# B. Créer des cas de test simples
def tester_fonction():
    # Test avec cas simple
    assert ma_fonction(1, 2) == 3
    # Test avec cas limite
    assert ma_fonction(0, 5) == 5
    # Test avec cas d'erreur
    try:
        ma_fonction("a", 2)
        assert False, "Devrait lever une erreur"
    except TypeError:
        pass  # Comportement attendu
```

💡 **7. Outils utiles**
• **print()** : Le plus simple pour débuter
• **pdb** : Debugger intégré Python
• **VS Code Debugger** : Interface graphique
• **logging** : Pour tracer en production
• **assert** : Vérifier les conditions
• **type()** : Vérifier le type d'une variable
• **dir()** : Voir les méthodes disponibles
• **help()** : Documentation intégrée

🎯 **Méthode systématique :**
1. **Reproduire** l'erreur de manière consistante
2. **Localiser** où exactement ça plante
3. **Comprendre** pourquoi ça plante
4. **Corriger** le problème
5. **Tester** que la correction fonctionne
6. **Vérifier** qu'on n'a pas cassé autre chose"""

    def _generate_general_programming_help(self) -> str:
        """Génère une aide générale sur la programmation"""
        return """🐍 **Aide générale Python**

Je peux vous aider avec de nombreux concepts Python ! Voici quelques exemples :

📚 **Sujets disponibles :**
• **Listes** : "Comment créer une liste en Python ?"
• **Dictionnaires** : "Comment utiliser un dictionnaire ?"
• **Fonctions** : "Comment créer une fonction ?"
• **Variables** : "Comment déclarer une variable ?"
• **Boucles** : "Comment faire une boucle for ?"
• **Conditions** : "Comment utiliser if/else ?"
• **Classes** : "Comment créer une classe ?"

💡 **Exemples de questions :**
• "Quelle est la différence entre une liste et un dictionnaire ?"
• "Comment faire une boucle sur un dictionnaire ?"
• "Comment créer une fonction avec des paramètres ?"

🎯 **Soyez spécifique :** Plus votre question est précise, plus ma réponse sera adaptée à vos besoins !

Que voulez-vous apprendre exactement ?"""

    def _get_random_response(self, responses: List[str]) -> str:
        """Sélectionne une réponse aléatoire"""
        return random.choice(responses)

    def _generate_document_summary(self, user_input: str) -> str:
        """
        Génère un résumé intelligent d'un document (PDF ou DOCX) - Version universelle

        Args:
            user_input: La demande de résumé contenant le texte extrait du document

        Returns:
            str: Résumé du contenu du document
        """
        print("🔍 DEBUG: user_input reçu dans _generate_document_summary:")
        print(f"Longueur: {len(user_input)}")
        print(f"Premiers 500 caractères: {user_input[:500]}")
        print("--- SÉPARATEUR ---")

        # Extraction du contenu du document depuis le prompt
        content_start = user_input.find("\n\n")
        if content_start == -1:
            return "Je n'ai pas trouvé de contenu à résumer dans votre demande."

        document_content = user_input[content_start:].strip()
        if not document_content or len(document_content) < 10:
            return "Je n'ai pas pu extraire suffisamment de texte de ce document pour en faire un résumé."

        # Sauvegarde du contenu dans la mémoire de conversation pour les futures questions
        is_pdf = "pdf content" in user_input.lower()
        doc_type = "PDF" if is_pdf else "document"
        filename = "document"

        # Extraction du nom de fichier s'il existe dans la demande
        filename_patterns = [
            r"Please summarize this PDF content from file \'(.+?)\':\n",
            r"Please analyze this document content from file \'(.+?)\':\n",
            r"Processed (?:PDF|DOCX): (.+?)(?:\n|$)",
            r"Fichier (?:PDF|DOCX): (.+?)(?:\n|$)",
            r"Document: (.+?)(?:\n|$)",
            r"PDF: (.+?)(?:\n|$)",
            r"DOCX: (.+?)(?:\n|$)",
        ]

        filename = "document"
        for pattern in filename_patterns:
            filename_match = re.search(pattern, user_input, re.IGNORECASE)
            if filename_match:
                filename = filename_match.group(1).strip()
                # Nettoyer le nom de fichier en gardant le nom de base
                filename = (
                    filename.replace(".pdf", "")
                    .replace(".docx", "")
                    .replace(".PDF", "")
                    .replace(".DOCX", "")
                )
                break

        # Si on n'a toujours pas trouvé, essayer d'extraire depuis le prompt "please summarize this"
        if filename == "document":
            # Chercher des patterns dans le prompt système
            system_patterns = [
                r"please summarize this pdf content:\s*(.+?)\.pdf",
                r"please analyze this document content:\s*(.+?)\.docx",
                r"PDF:\s*(.+?)\.pdf",
                r"DOCX:\s*(.+?)\.docx",
            ]

            for pattern in system_patterns:
                match = re.search(pattern, user_input, re.IGNORECASE)
                if match:
                    filename = match.group(1).strip()
                    break

        # Si toujours pas trouvé, chercher dans les lignes avec .pdf/.docx
        if filename == "document":
            lines = user_input.split("\n")
            for line in lines[:10]:  # Chercher dans les 10 premières lignes
                if ".pdf" in line.lower() or ".docx" in line.lower():
                    # Extraire le nom de fichier potentiel
                    words = line.split()
                    for word in words:
                        if ".pdf" in word.lower() or ".docx" in word.lower():
                            filename = (
                                word.strip(",:()[]")
                                .replace(".pdf", "")
                                .replace(".docx", "")
                                .replace(".PDF", "")
                                .replace(".DOCX", "")
                            )
                            break
                    if filename != "document":
                        break

        print(f"📄 Nom de fichier extrait: '{filename}'")

        # Stockage du contenu du document dans le contexte de conversation
        self.conversation_memory.store_document_content(filename, document_content)

        # Analyse du contenu de manière générique
        return self._create_universal_summary(document_content, filename, doc_type)

    def create_document_summary(
        self, content: str, filename: str, doc_type: str
    ) -> str:
        """
        API publique pour créer un résumé de document.

        Args:
            content: Contenu du document à résumer
            filename: Nom du fichier
            doc_type: Type du document (PDF, DOCX, etc.)

        Returns:
            str: Résumé formaté du document
        """
        return self._create_universal_summary(content, filename, doc_type)

    def _create_universal_summary(
        self, content: str, filename: str, doc_type: str
    ) -> str:
        """Génère un résumé de document style Claude avec plusieurs modèles"""

        # Choisir un style de résumé aléatoirement ou en fonction du contenu
        word_count = len(content.split())

        # Sélectionner un style en fonction de la longueur du contenu
        if word_count < 200:
            style_func = random.choice(
                [self._create_structured_summary, self._create_bullet_points_summary]
            )
        elif word_count < 800:
            style_func = random.choice(
                [self._create_executive_summary, self._create_structured_summary]
            )
        else:
            style_func = random.choice(
                [self._create_detailed_summary, self._create_executive_summary]
            )

        return style_func(content, filename, doc_type)

    def _create_structured_summary(
        self, content: str, doc_name: str, doc_type: str
    ) -> str:
        """Style de résumé structuré bien rédigé avec introduction, développement et conclusion"""

        # Analyser le contenu
        themes = self._analyze_content_themes(content)
        key_sentences = self._extract_key_sentences(content, 4)
        word_count = len(content.split())

        # **Titre en gras**
        summary = f"**RÉSUMÉ DU DOCUMENT : {doc_name.upper()}**\n\n"

        # **Introduction**
        summary += "**Introduction**\n\n"
        if doc_type.lower() == "pdf":
            summary += f"Ce document PDF de {word_count} mots présente "
        else:
            summary += f"Ce document de {word_count} mots aborde "

        if themes:
            summary += (
                f"principalement les thématiques de {', '.join(themes[:2]).lower()}. "
            )
        else:
            summary += "diverses informations importantes. "

        if key_sentences:
            summary += f"Le document s'ouvre sur l'idée que {key_sentences[0][:100].lower()}..."

        summary += "\n\n"

        # **Développement sous forme de liste rédigée**
        summary += "**Développement**\n\n"
        points = []
        if len(key_sentences) >= 2:
            points.append(
                f"- Le document met en avant l'importance de **{themes[0] if themes else 'la thématique principale'}**."
            )
            points.append(
                f"- Il précise que {key_sentences[1][:100].replace('.', '').capitalize()}."
            )
            if len(key_sentences) >= 3:
                points.append(
                    f"- Un autre point clé concerne **{themes[1] if themes and len(themes)>1 else 'un aspect complémentaire'}** : {key_sentences[2][:100].replace('.', '').capitalize()}."
                )
            if len(key_sentences) >= 4:
                points.append(
                    f"- Enfin, il est souligné que {key_sentences[3][:100].replace('.', '').capitalize()}."
                )
        else:
            points.append(
                f"- Le document présente des informations structurées autour de **{themes[0] if themes else 'son thème principal'}**."
            )
            points.append(
                "- Les éléments exposés permettent de comprendre les **enjeux** et les **modalités** présentés."
            )
        summary += "\n".join(points)
        summary += "\n\n"

        # Conclusion enrichie (toujours au moins 3 phrases, contextuelle)
        summary += "**Conclusion**\n\n"

        conclusion_patterns = [
            lambda: (
                f"En résumé, ce document offre une synthèse {'approfondie' if word_count>1000 else 'pertinente'} sur **{themes[0] if themes else 'le sujet'}**. "
                f"Les informations sont structurées de façon à faciliter la compréhension et la mise en application. "
                f"Il met en lumière les enjeux majeurs, notamment {', '.join(themes[:2]) if themes else 'les thématiques principales'}, et propose des pistes de réflexion pour approfondir le sujet."
            ),
            lambda: (
                f"Pour conclure, ce document met en exergue les points essentiels liés à **{themes[0] if themes else 'la thématique principale'}**. "
                f"La richesse des informations présentées permet d'acquérir une vision globale et nuancée du sujet. "
                f"Il constitue une base solide pour toute personne souhaitant approfondir ses connaissances ou engager une réflexion sur {themes[0] if themes else 'ce domaine'}."
            ),
            lambda: (
                f"Ce document constitue une ressource {'incontournable' if word_count>1000 else 'utile'} pour quiconque souhaite comprendre les enjeux de **{themes[0] if themes else 'ce domaine'}**. "
                f"La diversité des points abordés et la clarté de l'exposé en font un outil de référence. "
                f"Il est recommandé de s'y référer pour obtenir une compréhension approfondie et structurée du sujet traité."
            ),
            lambda: (
                f"La lecture de ce document permet d'appréhender efficacement les enjeux de **{themes[0] if themes else 'la thématique'}**. "
                f"Les éléments clés sont mis en avant de manière synthétique et argumentée. "
                f"Ce résumé invite à poursuivre l'exploration du sujet pour en saisir toutes les subtilités."
            ),
        ]
        summary += random.choice(conclusion_patterns)()
        return summary

    def _create_executive_summary(
        self, content: str, doc_name: str, doc_type: str
    ) -> str:
        """Style de résumé exécutif bien rédigé"""

        themes = self._analyze_content_themes(content)
        key_sentences = self._extract_key_sentences(content, 3)
        word_count = len(content.split())

        # **Titre en gras**
        summary = f"**SYNTHÈSE EXÉCUTIVE : {doc_name.upper()}**\n\n"

        # **Introduction**
        summary += "**Aperçu général**\n\n"
        summary += f"Le présent document {doc_type.lower()} constitue "

        if any(word in content.lower() for word in ["procédure", "guide", "manuel"]):
            summary += (
                "un guide opérationnel destiné à fournir des instructions pratiques. "
            )
        elif any(word in content.lower() for word in ["rapport", "analyse", "étude"]):
            summary += (
                "un rapport d'analyse présentant des données et des conclusions. "
            )
        elif any(
            word in content.lower() for word in ["formation", "cours", "apprentissage"]
        ):
            summary += (
                "un support de formation visant à transmettre des connaissances. "
            )
        else:
            summary += (
                "une ressource documentaire contenant des informations structurées. "
            )

        if themes:
            summary += f"Les thématiques centrales portent sur {', '.join(themes[:2]).lower()}."

        summary += "\n\n"

        # **Développement sous forme de liste rédigée**
        summary += "**Points essentiels**\n\n"
        dev_patterns = [
            lambda: "\n".join(
                [
                    f"1. **{themes[0].capitalize() if themes else 'Thème principal'}** : {key_sentences[0][:100].capitalize() if key_sentences else ''}",
                    f"2. **{themes[1].capitalize() if themes and len(themes)>1 else 'Aspect complémentaire'}** : {key_sentences[1][:100].capitalize() if len(key_sentences)>1 else ''}",
                    f"3. **Synthèse** : {key_sentences[2][:100].capitalize() if len(key_sentences)>2 else ''}",
                ]
            ),
            lambda: "\n".join(
                [
                    f"- Le document insiste sur l'importance de **{themes[0] if themes else 'la thématique principale'}**.",
                    f"- Il met en avant que {key_sentences[0][:100].replace('.', '').capitalize() if key_sentences else ''}.",
                    f"- Enfin, il propose une réflexion sur {themes[1] if themes and len(themes)>1 else 'un aspect complémentaire'}.",
                ]
            ),
            lambda: "\n".join(
                [
                    f"• **{themes[0].capitalize() if themes else 'Thème principal'}** : {key_sentences[0][:100].capitalize() if key_sentences else ''}",
                    f"• **{themes[1].capitalize() if themes and len(themes)>1 else 'Aspect complémentaire'}** : {key_sentences[1][:100].capitalize() if len(key_sentences)>1 else ''}",
                    f"• **Synthèse** : {key_sentences[2][:100].capitalize() if len(key_sentences)>2 else ''}",
                ]
            ),
        ]
        summary += random.choice(dev_patterns)()
        summary += "\n\n"

        # **Conclusion**
        summary += "**Recommandations**\n\n"

        summary += "Cette synthèse met en évidence la valeur informative du document. "

        if word_count > 1000:
            summary += f"Avec ses {word_count} mots, il offre une couverture exhaustive du sujet. "
        else:
            summary += f"Malgré sa concision ({word_count} mots), il couvre efficacement les aspects essentiels. "

        summary += "Il est recommandé de consulter ce document pour obtenir "
        if themes:
            summary += (
                f"une compréhension approfondie des enjeux liés à {themes[0].lower()}."
            )
        else:
            summary += "les informations nécessaires sur le sujet traité."

        return summary

    def _create_detailed_summary(
        self, content: str, doc_name: str, doc_type: str
    ) -> str:
        """Style de résumé détaillé bien rédigé"""

        themes = self._analyze_content_themes(content)
        key_sentences = self._extract_key_sentences(content, 5)
        sections = self._split_content_sections_claude(content)
        word_count = len(content.split())

        # **Titre en gras**
        summary = f"**ANALYSE DÉTAILLÉE : {doc_name.upper()}**\n\n"

        # **Introduction développée**
        summary += "**Introduction**\n\n"
        summary += f"Le document '{doc_name}' se présente comme un {doc_type.lower()} de {word_count} mots "
        summary += f"organisé en {len(sections)} sections principales. "

        if themes:
            summary += f"Son contenu s'articule autour de {len(themes)} thématiques majeures : "
            summary += f"{', '.join(themes).lower()}. "

        summary += (
            "Cette analyse propose une lecture structurée des éléments constitutifs "
        )
        summary += "et des enjeux soulevés dans ce document."

        summary += "\n\n"

        # **Développement multi-parties**
        summary += "**Analyse du contenu**\n\n"

        if key_sentences:
            summary += "**Premier axe d'analyse :** Le document établit d'emblée que "
            summary += (
                f"{key_sentences[0][:150].lower()}. Cette approche pose les fondements "
            )
            summary += "de l'ensemble de la démarche présentée.\n\n"

            if len(key_sentences) >= 2:
                summary += "**Deuxième axe d'analyse :** L'auteur développe ensuite l'idée selon laquelle "
                summary += (
                    f"{key_sentences[1][:150].lower()}. Cette perspective enrichit "
                )
                summary += "la compréhension globale du sujet.\n\n"

            if len(key_sentences) >= 3:
                summary += (
                    "**Troisième axe d'analyse :** Le document précise également que "
                )
                summary += f"{key_sentences[2][:150].lower()}. Cet élément apporte "
                summary += "des nuances importantes à l'analyse.\n\n"

            if len(key_sentences) >= 4:
                summary += "**Compléments d'information :** En outre, il convient de souligner que "
                summary += (
                    f"{key_sentences[3][:150].lower()}. Ces données complémentaires "
                )
                summary += "renforcent la pertinence de l'ensemble."
        else:
            summary += "Le contenu se déploie de manière progressive et méthodique. "
            summary += (
                "Chaque section apporte des éléments spécifiques qui s'articulent "
            )
            summary += "harmonieusement avec l'ensemble du propos."

        summary += "\n\n"

        # **Conclusion développée**
        summary += "**Conclusion et perspectives**\n\n"

        summary += (
            "Cette analyse révèle la richesse et la cohérence du document étudié. "
        )

        if word_count > 1500:
            summary += f"La densité informationnelle ({word_count} mots) témoigne d'un travail "
            summary += (
                "approfondi et d'une volonté de couvrir exhaustivement le sujet. "
            )
        elif word_count > 800:
            summary += (
                f"L'équilibre entre concision et exhaustivité ({word_count} mots) "
            )
            summary += "démontre une approche réfléchie et structurée. "
        else:
            summary += f"La synthèse proposée ({word_count} mots) va à l'essentiel "
            summary += "tout en préservant la richesse informationnelle. "

        if themes:
            summary += f"Les thématiques abordées ({', '.join(themes[:2]).lower()}) "
            summary += "offrent des perspectives d'approfondissement intéressantes. "

        summary += "Ce document constitue une ressource précieuse pour quiconque "
        summary += "souhaite appréhender les enjeux présentés de manière structurée et complète."

        return summary

    def _create_bullet_points_summary(
        self, content: str, doc_name: str, doc_type: str
    ) -> str:
        """Style de résumé synthétique bien rédigé (même si appelé bullet points)"""

        themes = self._analyze_content_themes(content)
        key_sentences = self._extract_key_sentences(content, 3)
        word_count = len(content.split())

        # **Titre en gras**
        summary = f"**RÉSUMÉ SYNTHÉTIQUE : {doc_name.upper()}**\n\n"

        # **Introduction**
        summary += "**Présentation**\n\n"
        summary += f"Ce document {doc_type.lower()} de {word_count} mots propose "

        if themes:
            summary += (
                f"une approche structurée des questions liées à {themes[0].lower()}. "
            )
            if len(themes) > 1:
                summary += (
                    f"Il aborde également les aspects relatifs à {themes[1].lower()}. "
                )
        else:
            summary += "un ensemble d'informations organisées et pertinentes. "

        summary += "L'objectif est de fournir une vision claire et accessible du sujet traité."

        summary += "\n\n"

        # **Développement**
        summary += "**Contenu principal**\n\n"

        if key_sentences:
            summary += "Le document développe principalement l'idée que "
            summary += f"{key_sentences[0][:120].lower()}. "

            if len(key_sentences) >= 2:
                summary += (
                    f"Il établit également que {key_sentences[1][:120].lower()}. "
                )

            if len(key_sentences) >= 3:
                summary += (
                    f"En complément, il précise que {key_sentences[2][:120].lower()}."
                )
        else:
            summary += "Le contenu présente de manière structurée les informations "
            summary += "essentielles relatives au domaine concerné."

        summary += "\n\n"

        # **Conclusion**
        summary += "**Utilité**\n\n"

        summary += "Cette ressource se révèle particulièrement utile pour "
        if themes:
            summary += f"comprendre les enjeux liés à {themes[0].lower()}. "
        else:
            summary += "appréhender les questions abordées. "

        summary += "Sa structure claire et son approche méthodique en font "
        summary += "un outil de référence approprié pour les personnes "
        summary += "cherchant à s'informer sur ce domaine."

        return summary

    def _create_short_summary(
        self, content: str, filename: str, doc_type: str, themes: List[str]
    ) -> str:
        """Résumé court pour documents de moins de 100 mots"""
        # Introduction simple
        summary = f"Ce {doc_type} '{filename}' présente un contenu concis "

        if themes:
            summary += f"centré sur {', '.join(themes[:2])}. "
        else:
            summary += "abordant quelques points essentiels. "

        # Développement condensé
        key_points = self._extract_main_points(content, max_points=2)
        if key_points:
            summary += f"Le document mentionne notamment {key_points[0].lower()}"
            if len(key_points) > 1:
                summary += f", ainsi que {key_points[1].lower()}"
            summary += ". "

        summary += "**Utilité**\n\n"
        # Conclusion enrichie (toujours au moins 3 phrases, contextuelle)
        if themes:
            summary += (
                f"Cette ressource se révèle particulièrement utile pour comprendre les enjeux liés à {themes[0].lower()}. "
                f"Elle permet d'acquérir une vision structurée et synthétique des principaux aspects abordés, notamment {', '.join(themes[:2])}. "
                f"Grâce à sa clarté et à son organisation, ce document constitue un outil de référence pour toute personne souhaitant approfondir ce domaine."
            )
        else:
            summary += (
                "Ce document permet d'appréhender les questions abordées de manière claire et concise. "
                "Sa structure méthodique facilite la compréhension des points essentiels. "
                "Il s'adresse à toute personne désireuse de s'informer efficacement sur le sujet traité."
            )
        return summary

    def _explain_code_content(self, content: str, filename: str) -> str:
        """Génère une explication détaillée du code en utilisant la fonction d'analyse existante"""

        # Détecter le langage
        language = "Python"  # Par défaut
        if filename.endswith(".js"):
            language = "JavaScript"
        elif filename.endswith(".java"):
            language = "Java"
        elif filename.endswith(".cpp") or filename.endswith(".c"):
            language = "C/C++"
        elif filename.endswith(".go"):
            language = "Go"
        elif filename.endswith(".rs"):
            language = "Rust"

        # Utiliser la fonction d'explication existante qui est plus sophistiquée
        return self._explain_code_naturally(content, filename, language)

    def _create_long_summary(
        self,
        content: str,
        filename: str,
        doc_type: str,
        themes: List[str],
        concepts: List[str],
        _sentences: List[str],
    ) -> str:
        """Résumé détaillé pour documents de plus de 500 mots"""
        # Introduction élaborée
        summary = f"Le {doc_type} '{filename}' présente une analyse "

        if themes:
            primary_theme = themes[0]
            summary += f"{primary_theme} complète et détaillée. "
            if len(themes) > 1:
                summary += (
                    f"Le document explore les dimensions {', '.join(themes[1:4])}, "
                )
                summary += "offrant une perspective multifacette sur le sujet. "
            else:
                summary += "L'approche adoptée permet une compréhension approfondie des enjeux. "
        else:
            summary += "approfondie du sujet traité, structurée de manière logique et progressive. "

        # Premier paragraphe de développement
        summary += "\n\nDans sa première partie, le document établit le contexte en présentant "
        key_points = self._extract_main_points(content, max_points=5)
        if key_points:
            summary += f"{key_points[0].lower()}. "
            if len(key_points) > 1:
                summary += (
                    f"Cette base permet ensuite d'aborder {key_points[1].lower()}, "
                )
                summary += "élément central de l'argumentation développée. "

        # Deuxième paragraphe de développement
        if len(key_points) > 2:
            summary += f"\n\nLe développement se poursuit avec l'examen de {key_points[2].lower()}. "
            if len(key_points) > 3:
                summary += f"L'auteur analyse également {key_points[3].lower()}, "
                summary += "apportant des précisions importantes sur les modalités d'application. "

            # Ajout des éléments techniques
            if concepts:
                technical_elements = [c for c in concepts if len(c) > 4][:3]
                if technical_elements:
                    summary += f"Les aspects techniques, notamment {', '.join(technical_elements)}, "
                    summary += "sont traités avec le niveau de détail nécessaire à leur mise en œuvre. "

        # Conclusion nuancée
        summary += f"\n\nEn conclusion, ce document constitue une ressource {self._get_document_value(content)} "
        summary += f"pour comprendre les enjeux {themes[0] if themes else 'abordés'}. "

        document_tone = self._get_document_tone(content)
        if document_tone in ["pratique", "opérationnelle"]:
            summary += "Son approche pratique en fait un outil utilisable directement dans le contexte professionnel. "
        elif document_tone in ["technique", "spécialisée"]:
            summary += "Son niveau technique permet aux spécialistes d'approfondir leurs connaissances. "
        else:
            summary += (
                "Sa structure claire facilite l'appropriation des concepts présentés. "
            )

        # Note de mémorisation discrète
        summary += f"\n\n💾 Le contenu de ce {doc_type} est maintenant disponible pour des questions spécifiques."

        return summary

    def _extract_main_themes_for_summary(self, content: str) -> List[str]:
        """Extrait les thèmes principaux pour le résumé rédigé"""
        content_lower = content.lower()

        theme_patterns = {
            "technique": [
                "technique",
                "technologie",
                "système",
                "méthode",
                "processus",
                "procédure",
            ],
            "gestion": [
                "gestion",
                "organisation",
                "management",
                "équipe",
                "projet",
                "planification",
            ],
            "sécurité": [
                "sécurité",
                "sécurisé",
                "protection",
                "risque",
                "prévention",
                "contrôle",
            ],
            "qualité": [
                "qualité",
                "performance",
                "excellence",
                "amélioration",
                "optimisation",
            ],
            "formation": [
                "formation",
                "apprentissage",
                "développement",
                "compétence",
                "éducation",
            ],
            "stratégique": [
                "stratégie",
                "objectif",
                "vision",
                "mission",
                "développement",
            ],
            "opérationnelle": [
                "opération",
                "production",
                "mise en œuvre",
                "application",
                "exécution",
            ],
            "analytique": [
                "analyse",
                "évaluation",
                "mesure",
                "indicateur",
                "données",
                "statistique",
            ],
        }

        detected_themes = []
        theme_scores = {}

        for theme, keywords in theme_patterns.items():
            score = sum(1 for keyword in keywords if keyword in content_lower)
            if score > 0:
                theme_scores[theme] = score

        # Trier par score et prendre les plus pertinents
        sorted_themes = sorted(theme_scores.items(), key=lambda x: x[1], reverse=True)
        detected_themes = [theme for theme, score in sorted_themes[:4] if score >= 1]

        return detected_themes

    def _extract_key_concepts(self, content: str) -> List[str]:
        """Extrait les concepts clés du document"""
        # Mots de plus de 5 caractères qui reviennent souvent
        words = re.findall(r"\b[A-Za-zÀ-ÿ]{5,}\b", content)
        word_freq = {}

        # Mots vides étendus
        stop_words = {
            "dans",
            "avec",
            "pour",
            "cette",
            "comme",
            "plus",
            "moins",
            "très",
            "bien",
            "tout",
            "tous",
            "être",
            "avoir",
            "faire",
            "aller",
            "voir",
            "dire",
            "donc",
            "mais",
            "ainsi",
            "alors",
            "après",
            "avant",
            "depuis",
            "pendant",
            "entre",
            "document",
            "texte",
            "fichier",
            "contenu",
            "information",
        }

        for word in words:
            word_lower = word.lower()
            if word_lower not in stop_words and not word_lower.isdigit():
                word_freq[word_lower] = word_freq.get(word_lower, 0) + 1

        # Garder les mots qui apparaissent plus d'une fois
        significant_concepts = [word for word, freq in word_freq.items() if freq > 1]
        return sorted(significant_concepts, key=lambda x: word_freq[x], reverse=True)[
            :8
        ]

    def _extract_main_points(self, content: str, max_points: int = 3) -> List[str]:
        """Extrait les points principaux du contenu"""
        sentences = [
            s.strip() for s in re.split(r"[.!?]+", content) if len(s.strip()) > 30
        ]

        # Mots-clés qui indiquent des points importants
        importance_indicators = [
            "important",
            "essentiel",
            "principal",
            "objectif",
            "but",
            "nécessaire",
            "recommandé",
            "obligatoire",
            "crucial",
            "fondamental",
            "primordial",
            "permet",
            "vise",
            "consiste",
            "comprend",
            "inclut",
        ]

        scored_sentences = []
        for sentence in sentences[:20]:  # Limiter pour la performance
            score = 0
            sentence_lower = sentence.lower()

            # Score basé sur les indicateurs d'importance
            for indicator in importance_indicators:
                if indicator in sentence_lower:
                    score += 2

            # Score basé sur la position (début = plus important)
            position_bonus = max(0, 3 - sentences.index(sentence) // 3)
            score += position_bonus

            # Score basé sur la longueur (ni trop court ni trop long)
            length = len(sentence.split())
            if 8 <= length <= 25:
                score += 1

            if score > 0:
                scored_sentences.append((sentence, score))

        # Trier et sélectionner les meilleurs
        scored_sentences.sort(key=lambda x: x[1], reverse=True)
        main_points = [sentence for sentence, score in scored_sentences[:max_points]]

        return main_points

    def _get_document_tone(self, content: str) -> str:
        """Détermine le ton du document"""
        content_lower = content.lower()

        if any(
            word in content_lower
            for word in [
                "procédure",
                "étape",
                "méthode",
                "application",
                "mise en œuvre",
            ]
        ):
            return "pratique"
        elif any(
            word in content_lower
            for word in [
                "technique",
                "système",
                "technologie",
                "algorithme",
                "configuration",
            ]
        ):
            return "technique"
        elif any(
            word in content_lower
            for word in [
                "stratégie",
                "objectif",
                "vision",
                "développement",
                "croissance",
            ]
        ):
            return "stratégique"
        elif any(
            word in content_lower
            for word in ["analyse", "étude", "recherche", "évaluation", "données"]
        ):
            return "analytique"
        else:
            return "générale"

    def _get_document_value(self, content: str) -> str:
        """Évalue la valeur du document"""
        word_count = len(content.split())

        if word_count > 1000:
            return "exhaustive"
        elif word_count > 500:
            return "complète"
        elif word_count > 200:
            return "utile"
        else:
            return "concise"

    def _analyze_content_themes(self, content: str) -> List[str]:
        """Analyse simple des thèmes du contenu"""
        content_lower = content.lower()

        # Mots-clés thématiques
        theme_keywords = {
            "sécurité": ["sécurité", "securite", "accident", "urgence", "secours"],
            "technique": ["système", "technique", "procédure", "méthode"],
            "entreprise": ["entreprise", "société", "organisation", "équipe"],
            "formation": ["formation", "stage", "apprentissage", "cours"],
            "contact": ["contact", "téléphone", "email", "adresse"],
        }

        detected_themes = []
        for theme, keywords in theme_keywords.items():
            if any(keyword in content_lower for keyword in keywords):
                detected_themes.append(theme)

        return detected_themes

    def _extract_key_sentences(self, content: str, max_sentences: int = 5) -> List[str]:
        """Version CORRIGÉE - Ne coupe JAMAIS les mots"""

        # Nettoyage et séparation en phrases
        content_clean = re.sub(r"\s+", " ", content.strip())

        # Séparation en phrases plus robuste
        sentences = re.split(r"[.!?]+\s+", content_clean)
        sentences = [s.strip() for s in sentences if len(s.strip()) > 15]

        key_sentences = []

        def smart_truncate_sentence(sentence, max_len=200):
            """Coupe intelligemment sans casser les mots"""
            if len(sentence) <= max_len:
                return sentence

            # Trouver le dernier espace avant max_len
            truncated = sentence[: max_len - 3]
            last_space = truncated.rfind(" ")

            # Si on trouve un espace convenable
            if last_space > max_len * 0.7:  # Au moins 70% de la longueur souhaitée
                return truncated[:last_space] + "..."
            else:
                # Chercher le premier espace après 70% de la longueur
                min_acceptable = int(max_len * 0.7)
                space_after = sentence.find(" ", min_acceptable)
                if space_after != -1 and space_after < max_len + 20:
                    return sentence[:space_after] + "..."
                else:
                    # En dernier recours, couper au dernier espace trouvé
                    return (
                        truncated[:last_space] + "..."
                        if last_space > 50
                        else sentence[: max_len - 3] + "..."
                    )

        # Première phrase (souvent importante)
        if sentences:
            first_sentence = smart_truncate_sentence(sentences[0])
            key_sentences.append(first_sentence)

        # Phrases avec mots d'importance
        importance_words = [
            "important",
            "essentiel",
            "principal",
            "objectif",
            "but",
            "conclusion",
            "résultat",
            "efficace",
            "nécessaire",
            "recommandé",
            "obligatoire",
        ]

        for sentence in sentences[1:]:
            if any(word in sentence.lower() for word in importance_words):
                if len(key_sentences) < max_sentences:
                    processed_sentence = smart_truncate_sentence(sentence)
                    key_sentences.append(processed_sentence)

        # Compléter avec d'autres phrases si nécessaire
        if len(key_sentences) < max_sentences and len(sentences) > 2:
            # Phrase du milieu
            mid_idx = len(sentences) // 2
            if mid_idx < len(sentences) and len(key_sentences) < max_sentences:
                mid_sentence = sentences[mid_idx]
                if mid_sentence not in [ks.replace("...", "") for ks in key_sentences]:
                    processed_sentence = smart_truncate_sentence(mid_sentence)
                    key_sentences.append(processed_sentence)

            # Dernière phrase
            if len(sentences) > 1 and len(key_sentences) < max_sentences:
                last_sentence = sentences[-1]
                if len(last_sentence) > 30:
                    processed_sentence = smart_truncate_sentence(last_sentence)
                    if processed_sentence not in [
                        ks.replace("...", "") for ks in key_sentences
                    ]:
                        key_sentences.append(processed_sentence)

        return key_sentences[:max_sentences]

    def smart_truncate(self, text: str, max_length: int = 200, min_length: int = 100) -> str:
        """
        Coupe intelligemment un texte sans couper les mots

        Args:
            text: Texte à couper
            max_length: Longueur maximale
            min_length: Longueur minimale garantie

        Returns:
            Texte coupé intelligemment
        """
        if len(text) <= max_length:
            return text

        # Couper à max_length - 3 pour laisser place aux "..."
        truncated = text[: max_length - 3]

        # Trouver le dernier espace pour éviter de couper un mot
        last_space = truncated.rfind(" ")

        # Si on trouve un espace et qu'il laisse suffisamment de texte
        if last_space > min_length:
            return truncated[:last_space] + "..."
        else:
            # Si pas d'espace approprié, couper quand même mais avertir
            return truncated + "..."

    def _detect_document_themes(self, content: str) -> Dict[str, List[str]]:
        """
        Détecte les thèmes principaux d'un document de manière universelle

        Args:
            content: Contenu du document

        Returns:
            Dictionnaire des thèmes et leurs mots-clés associés
        """
        text_lower = content.lower()

        # Mots vides étendus
        stop_words = {
            "le",
            "la",
            "les",
            "un",
            "une",
            "des",
            "et",
            "ou",
            "à",
            "au",
            "aux",
            "ce",
            "ces",
            "dans",
            "en",
            "par",
            "pour",
            "sur",
            "il",
            "elle",
            "ils",
            "elles",
            "je",
            "tu",
            "nous",
            "vous",
            "que",
            "qui",
            "dont",
            "où",
            "quoi",
            "comment",
            "pourquoi",
            "avec",
            "cette",
            "comme",
            "plus",
            "moins",
            "sans",
            "très",
            "tout",
            "tous",
            "toutes",
            "bien",
            "être",
            "avoir",
            "faire",
            "aller",
            "venir",
            "voir",
            "savoir",
            "pouvoir",
            "vouloir",
            "devoir",
            "falloir",
            "peut",
            "peuvent",
            "doit",
            "doivent",
            "sont",
            "était",
            "seront",
            "étaient",
            "sera",
            "donc",
            "mais",
            "car",
            "ainsi",
            "alors",
            "après",
            "avant",
            "pendant",
            "depuis",
            "jusqu",
            "lors",
            "tandis",
        }

        # Extraction de tous les mots significatifs
        words = re.findall(r"\b\w{4,}\b", text_lower)
        word_freq = {}

        for word in words:
            if word not in stop_words and not word.isdigit():
                word_freq[word] = word_freq.get(word, 0) + 1

        # Garder seulement les mots qui apparaissent plus d'une fois
        significant_words = {word: freq for word, freq in word_freq.items() if freq > 1}

        # Catégorisation thématique universelle basée sur les mots-clés
        themes = {
            "technique": [],
            "procédure": [],
            "information": [],
            "gestion": [],
            "général": [],
        }

        # Classification des mots par thème
        for word, freq in sorted(
            significant_words.items(), key=lambda x: x[1], reverse=True
        ):
            if word in [
                "technique",
                "technologie",
                "système",
                "méthode",
                "processus",
                "développement",
                "solution",
            ]:
                themes["technique"].append(f"{word} ({freq})")
            elif word in [
                "procédure",
                "étape",
                "action",
                "mesure",
                "protocole",
                "instruction",
                "consigne",
            ]:
                themes["procédure"].append(f"{word} ({freq})")
            elif word in [
                "information",
                "données",
                "résultat",
                "analyse",
                "rapport",
                "document",
                "fichier",
            ]:
                themes["information"].append(f"{word} ({freq})")
            elif word in [
                "gestion",
                "organisation",
                "responsable",
                "équipe",
                "groupe",
                "personnel",
                "service",
            ]:
                themes["gestion"].append(f"{word} ({freq})")
            else:
                # Mots les plus fréquents qui ne rentrent pas dans les catégories spécifiques
                if len(themes["général"]) < 10:  # Limiter à 10 mots généraux
                    themes["général"].append(f"{word} ({freq})")

        # Supprimer les thèmes vides
        themes = {k: v for k, v in themes.items() if v}

        return themes

    def _analyze_document_structure(self, content: str) -> Dict[str, Any]:
        """
        Analyse la structure d'un document de manière universelle

        Args:
            content: Contenu du document

        Returns:
            Informations sur la structure du document
        """
        structure = {}

        # Détection de sections/titres (lignes courtes en majuscules ou avec caractères spéciaux)
        lines = content.split("\n")
        potential_sections = []

        for line in lines:
            line_clean = line.strip()
            if line_clean:
                # Lignes courtes qui pourraient être des titres
                if len(line_clean) < 80 and (
                    line_clean.isupper()  # Tout en majuscules
                    or re.match(
                        r"^[A-Z][^.]*$", line_clean
                    )  # Commence par majuscule, pas de point final
                    or re.match(
                        r"^\d+\.?\s+[A-Z]", line_clean
                    )  # Commence par un numéro
                ):
                    potential_sections.append(line_clean)

        if potential_sections:
            structure["sections"] = potential_sections[:10]  # Max 10 sections

        # Détection de listes ou énumérations
        list_indicators = len(re.findall(r"^\s*[-•*]\s+", content, re.MULTILINE))
        numbered_lists = len(re.findall(r"^\s*\d+\.?\s+", content, re.MULTILINE))

        structure["lists"] = list_indicators + numbered_lists

        # Détection de données numériques
        numbers = re.findall(r"\b\d+(?:[.,]\d+)?\b", content)
        if len(numbers) > 5:  # Document avec beaucoup de chiffres
            structure["numbers"] = True

        return structure

    def _find_keyword_context(
        self, text: str, keyword: str, context_length: int = 30
    ) -> List[str]:
        """
        Trouve les contextes d'utilisation d'un mot-clé dans le texte

        Args:
            text: Texte complet
            keyword: Mot-clé à rechercher
            context_length: Nombre de caractères de contexte à extraire

        Returns:
            Liste des contextes trouvés (maximum 3)
        """
        contexts = []
        text_lower = text.lower()
        keyword_lower = keyword.lower()

        # Rechercher jusqu'à 3 occurrences du mot-clé
        start_pos = 0
        for _ in range(3):
            pos = text_lower.find(keyword_lower, start_pos)
            if pos == -1:
                break

            # Extraire le contexte
            context_start = max(0, pos - context_length)
            context_end = min(len(text), pos + len(keyword) + context_length)
            context = text[context_start:context_end].replace("\n", " ").strip()

            # Ajouter des ... si le contexte est tronqué
            if context_start > 0:
                context = "..." + context
            if context_end < len(text):
                context = context + "..."

            contexts.append(context)
            start_pos = pos + len(keyword)

        return contexts

    def _is_document_question(self, user_input: str) -> bool:
        """
        Détermine si une question concerne un document stocké
        """
        # Mots-clés qui indiquent une question sur l'identité ou les capacités (PAS sur un document)
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
            "ça va",
            "sa va",
            "ca va",
        ]

        # Si la question contient un mot-clé d'identité ou de capacité, ce n'est pas une question sur un document
        user_lower = user_input.lower()
        if any(
            keyword in user_lower for keyword in identity_keywords + capability_keywords
        ):
            return False

        # Mots-clés qui indiquent clairement une question sur un document
        document_keywords = [
            # Résumés et analyses spécifiques
            "résume le pdf",
            "résume le doc",
            "résume le document",
            "résume le fichier",
            "analyse le pdf",
            "analyse le doc",
            "analyse le document",
            "analyse le fichier",
            # Références explicites
            "ce pdf",
            "ce document",
            "ce fichier",
            "ce docx",
            "ce doc",
            "cette page",
            "le pdf",
            "le document",
            "le fichier",
            "le docx",
            "le doc",
            "du pdf",
            "du document",
            "du fichier",
            "du docx",
            "du doc",
            # Questions spécifiques avec contexte
            "que dit le pdf",
            "que dit le document",
            "que contient le pdf",
            "que contient le document",
            "dans le pdf",
            "dans le document",
            "dans le fichier",
            # Résumés simples avec contexte documentaire récent
            "résume",
            "resume",
            (
                "résumé"
                if any(
                    "pdf" in str(doc).lower() or "docx" in str(doc).lower()
                    for doc in self.conversation_memory.get_document_content().values()
                )
                else ""
            ),
        ]

        # Filtrer les chaînes vides
        document_keywords = [kw for kw in document_keywords if kw]

        # Si il y a des documents stockés ET la question contient des mots-clés de document spécifiques
        if self.conversation_memory.get_document_content():
            if any(keyword in user_lower for keyword in document_keywords):
                return True

        return False

    def _answer_code_question(self, user_input: str, code_docs: Dict[str, Any]) -> str:
        """Répond aux questions sur le code de manière naturelle"""
        if not code_docs:
            return "Je n'ai pas de code en mémoire pour répondre à votre question."

        # Prendre le dernier fichier de code
        if self.conversation_memory.document_order:
            last_doc = None
            for doc_name in reversed(self.conversation_memory.document_order):
                if doc_name in code_docs:
                    last_doc = doc_name
                    break

            if last_doc:
                doc_data = code_docs[last_doc]
                code_content = doc_data.get("content", "")

                user_lower = user_input.lower()

                if any(
                    word in user_lower for word in ["explique", "que fait", "comment"]
                ):
                    # Utiliser le processeur de code avancé pour les explications détaillées
                    print(f"🔧 [CODE_QUESTION] Explication demandée pour: {last_doc}")
                    return self._explain_specific_code_file(
                        last_doc, code_content, user_input
                    )
                elif any(word in user_lower for word in ["améliore", "optimise"]):
                    return self._suggest_improvements_naturally(code_content, last_doc)
                else:
                    return f"J'ai le code de '{last_doc}' en mémoire. Que voulez-vous savoir ? Je peux l'expliquer, suggérer des améliorations, ou répondre à des questions spécifiques."

        return "J'ai du code en mémoire mais je ne sais pas lequel vous intéresse. Précisez votre question !"

    def _explain_code_naturally(self, code: str, filename: str, language: str) -> str:
        """Explique le code avec un résumé rédigé dans le style Claude"""

        # Analyse du code
        analysis = self._analyze_code_structure(language)
        complexity = self._assess_code_complexity(code, analysis)
        purpose = self._infer_code_purpose(code, filename, analysis)

        # Génération du résumé selon la complexité
        if complexity == "simple":
            return self._create_simple_code_summary(
                code, filename, language, analysis, purpose
            )
        elif complexity == "medium":
            return self._create_medium_code_summary(
                code, filename, language, analysis, purpose
            )
        else:
            return self._create_complex_code_summary(
                filename, language, analysis, purpose
            )

    def _analyze_code_structure(self, code: str) -> dict:
        """Analyse la structure du code"""
        lines = code.split("\n")

        analysis = {
            "total_lines": len(lines),
            "functions": [],
            "classes": [],
            "imports": [],
            "main_patterns": [],
            "frameworks": [],
        }

        for i, line in enumerate(lines, 1):
            line_stripped = line.strip()

            # Fonctions
            if line_stripped.startswith("def "):
                func_name = line_stripped.split("(")[0].replace("def ", "")
                analysis["functions"].append({"name": func_name, "line": i})

            # Classes
            elif line_stripped.startswith("class "):
                class_name = (
                    line_stripped.split(":")[0].replace("class ", "").split("(")[0]
                )
                analysis["classes"].append({"name": class_name, "line": i})

            # Imports
            elif line_stripped.startswith(("import ", "from ")):
                analysis["imports"].append(line_stripped)

        # Détection de frameworks/bibliothèques
        code_lower = code.lower()
        if "tkinter" in code_lower or "tk." in code_lower:
            analysis["frameworks"].append("interface graphique Tkinter")
        if "flask" in code_lower:
            analysis["frameworks"].append("framework web Flask")
        if "django" in code_lower:
            analysis["frameworks"].append("framework web Django")
        if "pandas" in code_lower:
            analysis["frameworks"].append("analyse de données Pandas")
        if "matplotlib" in code_lower or "pyplot" in code_lower:
            analysis["frameworks"].append("visualisation Matplotlib")
        if "requests" in code_lower:
            analysis["frameworks"].append("requêtes HTTP")

        return analysis

    def _assess_code_complexity(self, _code: str, analysis: dict) -> str:
        """Évalue la complexité du code"""
        score = 0

        # Critères de complexité
        score += len(analysis["functions"]) * 2
        score += len(analysis["classes"]) * 3
        score += len(analysis["frameworks"]) * 2
        score += analysis["total_lines"] // 20

        if score < 8:
            return "simple"
        elif score < 20:
            return "medium"
        else:
            return "complex"

    def _infer_code_purpose(self, code: str, filename: str, analysis: dict) -> str:
        """Infère le but du code"""
        code_lower = code.lower()

        # Analyse du nom de fichier
        if "gui" in filename.lower() or "interface" in filename.lower():
            return "interface utilisateur"
        elif "test" in filename.lower():
            return "tests unitaires"
        elif "main" in filename.lower():
            return "programme principal"
        elif "config" in filename.lower():
            return "configuration"
        elif "utils" in filename.lower() or "util" in filename.lower():
            return "utilitaires"

        # Analyse du contenu
        if analysis["frameworks"]:
            if "tkinter" in code_lower:
                return "application avec interface graphique"
            elif "flask" in code_lower or "django" in code_lower:
                return "application web"
            elif "pandas" in code_lower:
                return "traitement de données"

        # Analyse des patterns
        if "class" in code and "__init__" in code:
            return "module orienté objet"
        elif len(analysis["functions"]) > 3:
            return "module fonctionnel"
        else:
            return "script"

    def _create_simple_code_summary(
        self, _code: str, filename: str, language: str, analysis: dict, purpose: str
    ) -> str:
        """Résumé pour code simple"""
        summary = f"Ce fichier {language} '{filename}' constitue un {purpose} relativement simple. "

        if analysis["functions"]:
            if len(analysis["functions"]) == 1:
                func_name = analysis["functions"][0]["name"]
                summary += f"Il définit une fonction principale '{func_name}' qui encapsule la logique métier. "
            else:
                summary += f"Il organise sa fonctionnalité autour de {len(analysis['functions'])} fonctions principales. "

        if analysis["frameworks"]:
            summary += f"Le code utilise {analysis['frameworks'][0]} pour réaliser ses objectifs. "

        summary += f"Avec ses {analysis['total_lines']} lignes, ce module reste facilement compréhensible et maintenable."

        if analysis["imports"]:
            summary += f" Il s'appuie sur {len(analysis['imports'])} dépendance(s) externe(s) pour son fonctionnement."

        return summary

    def _create_medium_code_summary(
        self, _code: str, filename: str, language: str, analysis: dict, purpose: str
    ) -> str:
        """Résumé pour code de complexité moyenne"""
        summary = (
            f"Le fichier {language} '{filename}' implémente un {purpose} structuré. "
        )

        # Introduction avec contexte
        if analysis["classes"]:
            summary += f"Il adopte une approche orientée objet avec {len(analysis['classes'])} classe(s) "
            if analysis["functions"]:
                summary += (
                    f"et {len(analysis['functions'])} fonction(s) complémentaires. "
                )
            else:
                summary += "pour organiser la logique applicative. "
        elif len(analysis["functions"]) > 3:
            summary += f"Sa structure fonctionnelle s'articule autour de {len(analysis['functions'])} fonctions spécialisées. "

        # Développement technique
        if analysis["frameworks"]:
            framework_list = ", ".join(analysis["frameworks"])
            summary += f"\n\nL'implémentation repose sur {framework_list}, "
            summary += "permettant une approche robuste et bien intégrée dans l'écosystème Python. "

        if analysis["classes"]:
            main_classes = [cls["name"] for cls in analysis["classes"][:2]]
            if len(main_classes) == 1:
                summary += f"La classe '{main_classes[0]}' centralise les fonctionnalités principales. "
            else:
                summary += f"Les classes '{main_classes[0]}' et '{main_classes[1]}' collaborent pour structurer l'application. "

        # Conclusion
        summary += f"\n\nCe module de {analysis['total_lines']} lignes présente un bon équilibre entre simplicité et fonctionnalité. "
        summary += "Son architecture facilite la maintenance et les évolutions futures."

        return summary

    def _create_complex_code_summary(
        self, filename: str, language: str, analysis: dict, purpose: str
    ) -> str:
        """Résumé pour code complexe"""
        summary = f"Le fichier {language} '{filename}' constitue un {purpose} d'envergure, développant une architecture sophistiquée. "

        # Introduction détaillée
        if analysis["classes"] and analysis["functions"]:
            summary += f"Il combine une approche orientée objet avec {len(analysis['classes'])} classe(s) "
            summary += f"et {len(analysis['functions'])} fonction(s), démontrant une conception modulaire avancée. "
        elif len(analysis["classes"]) >= 3:
            summary += f"Son design orienté objet s'appuie sur {len(analysis['classes'])} classes interconnectées, "
            summary += "révélant une architecture complexe et bien structurée. "
        elif len(analysis["functions"]) >= 10:
            summary += f"Sa structure fonctionnelle comprend {len(analysis['functions'])} fonctions spécialisées, "
            summary += "témoignant d'une décomposition minutieuse des responsabilités. "

        # Premier développement - Technologies
        if analysis["frameworks"]:
            summary += f"\n\nL'implémentation technique s'appuie sur plusieurs technologies clés : {', '.join(analysis['frameworks'])}. "
            summary += "Cette combinaison technologique permet de bénéficier d'un écosystème riche et éprouvé. "

        # Deuxième développement - Architecture
        if analysis["classes"]:
            main_classes = [cls["name"] for cls in analysis["classes"][:3]]
            summary += (
                "\n\nL'architecture s'organise principalement autour des classes "
            )
            if len(main_classes) >= 3:
                summary += (
                    f"'{main_classes[0]}', '{main_classes[1]}' et '{main_classes[2]}'. "
                )
            elif len(main_classes) == 2:
                summary += f"'{main_classes[0]}' et '{main_classes[1]}'. "
            else:
                summary += f"'{main_classes[0]}'. "

            summary += "Cette séparation claire des responsabilités facilite la compréhension et la maintenance du code. "

        # Conclusion évaluative
        summary += f"\n\nAvec ses {analysis['total_lines']} lignes, ce module représente un développement conséquent qui "

        if analysis["total_lines"] > 500:
            summary += (
                "nécessite une approche méthodique pour sa compréhension complète. "
            )
        else:
            summary += (
                "reste néanmoins accessible grâce à sa structure bien organisée. "
            )

        summary += "Il constitue un exemple de programmation Python avancée, alliant fonctionnalité et qualité architecturale."

        # Note de mémorisation
        summary += f"\n\n💾 Le code de ce fichier {language} est maintenant disponible pour des analyses détaillées."

        return summary

    def _suggest_improvements_naturally(self, code: str, filename: str) -> str:
        """Suggère des améliorations de manière naturelle"""
        suggestions = []

        # Analyse simple du code
        if '"""' not in code and "'''" not in code:
            suggestions.append(
                "📝 **Documentation :** Ajouter des docstrings aux fonctions pour expliquer leur rôle"
            )

        if "import *" in code:
            suggestions.append(
                "📦 **Imports :** Éviter `import *`, préférer des imports spécifiques"
            )

        if not any(line.strip().startswith("#") for line in code.split("\n")):
            suggestions.append(
                "💬 **Commentaires :** Ajouter des commentaires pour expliquer la logique"
            )

        if "except:" in code:
            suggestions.append(
                "⚠️ **Gestion d'erreurs :** Spécifier les types d'exceptions plutôt que `except:` générique"
            )

        response = f"🔧 **Suggestions d'amélioration pour '{filename}'**\n\n"

        if suggestions:
            for i, suggestion in enumerate(suggestions, 1):
                response += f"{i}. {suggestion}\n"
        else:
            response += "✅ **Excellent code !** Voici quelques idées générales :\n"
            response += "1. 🧪 Ajouter des tests unitaires\n"
            response += "2. 📊 Considérer l'ajout de logs pour le debug\n"
            response += "3. 🎯 Vérifier la conformité aux standards Python (PEP 8)\n"

        response += "\n💡 **Besoin d'aide ?** Demandez-moi de vous montrer comment implémenter ces améliorations !"

        return response

    def _explain_code_functionality(
        self, _user_input: str, stored_docs: Dict[str, Any]
    ) -> str:
        """Explique le fonctionnement du code"""

        # Prendre le dernier fichier de code ajouté
        if self.conversation_memory.document_order:
            last_doc = self.conversation_memory.document_order[-1]
            if last_doc in stored_docs:
                doc_data = stored_docs[last_doc]
                if doc_data.get("type") == "code":
                    code_content = doc_data["content"]
                    language = doc_data.get("language", "unknown")

                    if language == "python":
                        return self._explain_python_code(code_content, last_doc)
                    else:
                        return self._explain_generic_code(
                            code_content, last_doc, language
                        )

        return "Je n'ai pas de fichier de code récent à expliquer."

    def _explain_python_code(self, code: str, filename: str) -> str:
        """Explique spécifiquement du code Python"""

        analysis = {
            "imports": [],
            "functions": [],
            "classes": [],
            "main_logic": [],
            "key_variables": [],
        }

        lines = code.split("\n")

        for i, line in enumerate(lines, 1):
            line_stripped = line.strip()

            # Imports
            if line_stripped.startswith(("import ", "from ")):
                analysis["imports"].append(f"Ligne {i}: {line_stripped}")

            # Fonctions
            elif line_stripped.startswith("def "):
                func_name = line_stripped.split("(")[0].replace("def ", "")
                analysis["functions"].append(f"Ligne {i}: Fonction '{func_name}()'")

            # Classes
            elif line_stripped.startswith("class "):
                class_name = (
                    line_stripped.split(":")[0].replace("class ", "").split("(")[0]
                )
                analysis["classes"].append(f"Ligne {i}: Classe '{class_name}'")

            # Variables importantes (= en début de ligne)
            elif (
                line_stripped
                and not line_stripped.startswith((" ", "\t", "#"))
                and "=" in line_stripped
            ):
                var_part = line_stripped.split("=")[0].strip()
                analysis["key_variables"].append(f"Ligne {i}: Variable '{var_part}'")

        # Construire une réponse claire
        response = f"📄 **Analyse du code Python '{filename}'**\n\n"

        # Structure générale
        response += "📊 **Structure du fichier :**\n"
        response += f"• {len(lines)} lignes de code\n"
        response += f"• {len(analysis['imports'])} imports\n"
        response += f"• {len(analysis['classes'])} classes\n"
        response += f"• {len(analysis['functions'])} fonctions\n\n"

        # Imports principaux
        if analysis["imports"]:
            response += "📦 **Modules importés :**\n"
            for imp in analysis["imports"][:5]:
                module_name = imp.split(": ")[1] if ": " in imp else imp
                response += f"• {module_name}\n"
            response += "\n"

        # Classes principales
        if analysis["classes"]:
            response += "🏗️ **Classes définies :**\n"
            for cls in analysis["classes"][:3]:
                response += f"• {cls.split(': ')[1]}\n"
            response += "\n"

        # Fonctions principales
        if analysis["functions"]:
            response += "⚙️ **Fonctions principales :**\n"
            for func in analysis["functions"][:5]:
                response += f"• {func.split(': ')[1]}\n"
            response += "\n"

        # Variables clés
        if analysis["key_variables"]:
            response += "🔧 **Variables importantes :**\n"
            for var in analysis["key_variables"][:3]:
                response += f"• {var.split(': ')[1]}\n"
            response += "\n"

        # Analyse du contenu
        if "tkinter" in code.lower() or "tk." in code:
            response += "🖥️ **Type d'application :** Interface graphique (Tkinter)\n\n"
        elif "flask" in code.lower() or "django" in code.lower():
            response += "🌐 **Type d'application :** Application web\n\n"
        elif "class" in code and "def __init__" in code:
            response += "🏛️ **Paradigme :** Programmation orientée objet\n\n"

        response += "💡 **Pour aller plus loin :**\n"
        response += "• Demandez-moi d'expliquer une fonction spécifique\n"
        response += "• Posez des questions sur la logique\n"
        response += "• Demandez des suggestions d'amélioration\n"
        response += "• Demandez-moi de modifier une partie du code"

        return response

    def _suggest_code_improvements(
        self, _user_input: str, stored_docs: Dict[str, Any]
    ) -> str:
        """Suggère des améliorations pour le code"""

        last_doc = (
            self.conversation_memory.document_order[-1]
            if self.conversation_memory.document_order
            else None
        )
        if not last_doc or last_doc not in stored_docs:
            return "Je n'ai pas de code à analyser pour suggérer des améliorations."

        doc_data = stored_docs[last_doc]
        code_content = doc_data["content"]
        language = doc_data.get("language", "unknown")

        suggestions = []

        if language == "python":
            lines = code_content.split("\n")

            # Vérifier les docstrings
            has_docstrings = '"""' in code_content or "'''" in code_content
            if not has_docstrings:
                suggestions.append(
                    "📝 **Documentation :** Ajouter des docstrings aux fonctions et classes pour expliquer leur rôle"
                )

            # Vérifier les imports
            if "import *" in code_content:
                suggestions.append(
                    "📦 **Imports :** Éviter `import *`, préférer des imports spécifiques pour plus de clarté"
                )

            # Vérifier la longueur des lignes
            long_lines = [i + 1 for i, line in enumerate(lines) if len(line) > 100]
            if long_lines:
                suggestions.append(
                    f"📏 **Lisibilité :** Raccourcir les lignes trop longues (ex: lignes {long_lines[:3]})"
                )

            # Vérifier les noms de variables courtes
            short_vars = []
            for line in lines:
                if "=" in line and not line.strip().startswith("#"):
                    var_part = line.split("=")[0].strip()
                    if (
                        len(var_part) <= 2
                        and var_part.isalpha()
                        and var_part not in ["x", "y", "i", "j"]
                    ):
                        short_vars.append(var_part)

            if short_vars:
                suggestions.append(
                    f"🏷️ **Nommage :** Utiliser des noms plus descriptifs pour : {', '.join(set(short_vars[:3]))}"
                )

            # Vérifier la gestion d'erreurs
            if "try:" in code_content and "except:" in code_content:
                suggestions.append(
                    "⚠️ **Gestion d'erreurs :** Spécifier les types d'exceptions plutôt que `except:` générique"
                )

            # Vérifier les commentaires
            comment_ratio = len([l for l in lines if l.strip().startswith("#")]) / max(
                len(lines), 1
            )
            if comment_ratio < 0.1:
                suggestions.append(
                    "💬 **Commentaires :** Ajouter plus de commentaires pour expliquer la logique complexe"
                )

        if not suggestions:
            suggestions = [
                "✅ **Excellent code !** Voici quelques idées d'amélioration générale :",
                "• Ajouter des tests unitaires pour vérifier le bon fonctionnement",
                "• Considérer l'ajout de logs pour faciliter le debug",
                "• Vérifier la conformité aux standards du langage (PEP 8 pour Python)",
            ]

        response = f"🔧 **Suggestions d'amélioration pour '{last_doc}'**\n\n"
        for i, suggestion in enumerate(suggestions, 1):
            response += f"{i}. {suggestion}\n"

        response += "\n💡 **Besoin d'aide pour implémenter ces améliorations ?**\n"
        response += "Demandez-moi de vous montrer comment appliquer ces suggestions concrètement !"

        return response

    def _suggest_code_modifications(
        self, _user_input: str, _stored_docs: Dict[str, Any]
    ) -> str:
        """Suggère des modifications spécifiques du code"""
        return "🔨 **Modifications de code**\n\nDites-moi exactement ce que vous voulez modifier et je vous proposerai le code modifié !"

    def _analyze_code_issues(self, _stored_docs: Dict[str, Any]) -> str:
        """Analyse les problèmes potentiels dans le code"""
        return "🐛 **Analyse des problèmes**\n\nDécrivez-moi le problème que vous rencontrez et je vous aiderai à le résoudre !"

    def _general_code_analysis(
        self, user_input: str, stored_docs: Dict[str, Any]
    ) -> str:
        """Analyse générale du code"""
        return self._explain_code_functionality(user_input, stored_docs)

    # ===== FONCTIONS D'ASSISTANCE CLAUDE POUR LES NOUVEAUX STYLES DE RÉSUMÉ =====

    def _extract_key_points_claude(self, content: str) -> str:
        """Extrait les points clés style Claude"""
        sentences = [
            s.strip() for s in re.split(r"[.!?]+", content) if len(s.strip()) > 20
        ][:6]
        points = []
        for sentence in enumerate(sentences):
            if len(sentence) > 30:
                points.append(
                    f"• {sentence[:120]}{'...' if len(sentence) > 120 else ''}"
                )
        return (
            "\n".join(points[:4]) if points else "• Points clés à analyser en cours..."
        )

    def _extract_main_themes_claude(self, content: str) -> str:
        """Extrait les thèmes principaux style Claude"""
        themes = self._analyze_content_themes(content)
        if themes:
            return f"**Thèmes identifiés :** {', '.join(themes).title()}\n**Focus principal :** {themes[0].title()}"
        return "**Analyse thématique en cours...**"

    def _extract_important_info_claude(self, content: str) -> str:
        """Extrait les informations importantes style Claude"""
        key_sentences = self._extract_key_sentences(content, 3)
        if key_sentences:
            info = "\n".join(
                [
                    f"📌 {sentence[:100]}{'...' if len(sentence) > 100 else ''}"
                    for sentence in key_sentences
                ]
            )
            return info
        return "📌 Informations importantes en cours d'extraction..."

    def _get_document_purpose_claude(self, content: str) -> str:
        """Détermine l'objectif du document style Claude"""
        content_lower = content.lower()
        if any(word in content_lower for word in ["procédure", "guide", "manuel"]):
            return "un guide pratique avec des instructions détaillées"
        elif any(word in content_lower for word in ["rapport", "analyse", "étude"]):
            return "une analyse ou un rapport d'étude"
        elif any(
            word in content_lower for word in ["formation", "cours", "apprentissage"]
        ):
            return "du matériel de formation et d'apprentissage"
        else:
            return "des informations et données diverses"

    def _extract_essential_elements_claude(self, content: str) -> str:
        """Extrait les éléments essentiels style Claude"""
        key_points = self._extract_key_sentences(content, 4)
        elements = []
        for i, point in enumerate(key_points, 1):
            elements.append(f"**{i}.** {point[:80]}{'...' if len(point) > 80 else ''}")
        return (
            "\n".join(elements)
            if elements
            else "**Éléments en cours d'identification...**"
        )

    def _extract_actionable_items_claude(self, content: str) -> str:
        """Extrait les éléments actionnables style Claude"""
        action_words = [
            "doit",
            "devra",
            "recommandé",
            "nécessaire",
            "obligatoire",
            "conseillé",
        ]
        sentences = [
            s.strip() for s in re.split(r"[.!?]+", content) if len(s.strip()) > 15
        ]

        actionable = []
        for sentence in sentences:
            if any(word in sentence.lower() for word in action_words):
                actionable.append(
                    f"⚡ {sentence[:90]}{'...' if len(sentence) > 90 else ''}"
                )
                if len(actionable) >= 3:
                    break

        return (
            "\n".join(actionable)
            if actionable
            else "⚡ Actions recommandées à identifier..."
        )

    def _generate_conclusion_claude(self, content: str) -> str:
        """Génère une conclusion style Claude"""
        word_count = len(content.split())
        themes = self._analyze_content_themes(content)

        if word_count > 1000:
            conclusion = f"Document complet de {word_count} mots abordant {len(themes)} thématiques principales."
        elif word_count > 300:
            conclusion = (
                f"Document concis de {word_count} mots avec des informations ciblées."
            )
        else:
            conclusion = f"Document bref de {word_count} mots allant à l'essentiel."

        if themes:
            conclusion += f" Focus sur : {themes[0]}."

        return conclusion

    def _split_content_sections_claude(self, content: str) -> list:
        """Divise le contenu en sections style Claude"""
        # Diviser par paragraphes ou par sauts de ligne doubles
        sections = re.split(r"\n\s*\n", content)
        return [section.strip() for section in sections if len(section.strip()) > 50][
            :5
        ]

    def _extract_main_theme_claude(self, content: str) -> str:
        """Extrait le thème principal style Claude"""
        themes = self._analyze_content_themes(content)
        if themes:
            return f"**{themes[0].upper()} :** {content[:150]}{'...' if len(content) > 150 else ''}"
        return f"**CONTENU PRINCIPAL :** {content[:150]}{'...' if len(content) > 150 else ''}"

    def _extract_key_developments_claude(self, content: str) -> str:
        """Extrait les développements clés style Claude"""
        sentences = self._extract_key_sentences(content, 5)
        developments = []
        for i, sentence in enumerate(sentences, 1):
            developments.append(
                f"**Développement {i} :** {sentence[:100]}{'...' if len(sentence) > 100 else ''}"
            )
        return (
            "\n\n".join(developments)
            if developments
            else "**Développements en cours d'analyse...**"
        )

    def _extract_technical_details_claude(self, content: str) -> str:
        """Extrait les détails techniques style Claude"""
        technical_words = [
            "système",
            "méthode",
            "technique",
            "procédure",
            "algorithme",
            "configuration",
        ]
        sentences = [
            s.strip() for s in re.split(r"[.!?]+", content) if len(s.strip()) > 20
        ]

        technical_sentences = []
        for sentence in sentences:
            if any(word in sentence.lower() for word in technical_words):
                technical_sentences.append(
                    f"🔧 {sentence[:100]}{'...' if len(sentence) > 100 else ''}"
                )
                if len(technical_sentences) >= 3:
                    break

        return (
            "\n".join(technical_sentences)
            if technical_sentences
            else "🔧 Aspects techniques en cours d'identification..."
        )

    def _analyze_themes_claude(self, content: str) -> str:
        """Analyse thématique style Claude"""
        themes = self._analyze_content_themes(content)
        analysis = []

        for theme in themes[:3]:
            sentences = [s for s in re.split(r"[.!?]+", content) if theme in s.lower()]
            if sentences:
                analysis.append(
                    f"**{theme.upper()} :** {sentences[0][:80]}{'...' if len(sentences[0]) > 80 else ''}"
                )

        return (
            "\n".join(analysis)
            if analysis
            else "**Analyse thématique en préparation...**"
        )

    def _extract_implications_claude(self, content: str) -> str:
        """Extrait les implications style Claude"""
        implication_words = [
            "implique",
            "conséquence",
            "résultat",
            "effet",
            "impact",
            "influence",
        ]
        sentences = [
            s.strip() for s in re.split(r"[.!?]+", content) if len(s.strip()) > 20
        ]

        implications = []
        for sentence in sentences:
            if any(word in sentence.lower() for word in implication_words):
                implications.append(
                    f"📈 {sentence[:90]}{'...' if len(sentence) > 90 else ''}"
                )
                if len(implications) >= 2:
                    break

        if not implications:
            implications.append(
                "📈 Implications stratégiques à analyser selon le contexte d'utilisation"
            )

        return "\n".join(implications)

    def _create_bullet_points_claude(self, content: str) -> str:
        """Crée des points bullet style Claude"""
        key_sentences = self._extract_key_sentences(content, 5)
        bullets = []

        for sentence in key_sentences:
            # Extraire la partie la plus importante de la phrase
            words = sentence.split()
            if len(words) > 15:
                bullet_text = " ".join(words[:12]) + "..."
            else:
                bullet_text = sentence

            bullets.append(f"⚡ {bullet_text}")

        return (
            "\n".join(bullets)
            if bullets
            else "⚡ Points essentiels en cours d'extraction..."
        )

    def _extract_keywords_claude(self, content: str) -> str:
        """Extrait les mots-clés style Claude"""
        words = re.findall(r"\b[A-Za-zÀ-ÿ]{4,}\b", content.lower())
        word_freq = {}

        # Compter les mots (hors mots vides)
        stop_words = {
            "dans",
            "avec",
            "pour",
            "sans",
            "cette",
            "comme",
            "plus",
            "très",
            "tout",
            "bien",
            "être",
            "avoir",
        }
        for word in words:
            if word not in stop_words and len(word) > 4:
                word_freq[word] = word_freq.get(word, 0) + 1

        # Prendre les plus fréquents
        top_keywords = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:8]
        keywords = [word.title() for word, freq in top_keywords]

        return (
            " • ".join(keywords)
            if keywords
            else "Mots-clés en cours d'identification..."
        )

    def _extract_quick_facts_claude(self, content: str) -> str:
        """Extrait des faits rapides style Claude"""
        # Rechercher des chiffres, dates, noms propres
        numbers = re.findall(r"\b\d+(?:[.,]\d+)?\b", content)
        dates = re.findall(r"\b\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4}\b", content)

        facts = []
        if numbers:
            facts.append(f"📊 Contient {len(numbers)} valeurs numériques")
        if dates:
            facts.append(f"📅 {len(dates)} dates mentionnées")

        word_count = len(content.split())
        facts.append(f"📝 {word_count} mots au total")

        return (
            "\n".join(facts)
            if facts
            else "📊 Informations quantitatives en cours d'extraction..."
        )

    def _answer_document_question(
        self, user_input: str, stored_docs: Dict[str, Any]
    ) -> str:
        """
        🧠 Répond aux questions sur les documents avec analyse intelligente des 1M tokens
        Utilise une approche hiérarchique : Ultra -> Classic -> Recherche ciblée
        """

        print(
            f"🔍 [DEBUG] _answer_document_question appelé avec {len(stored_docs)} documents"
        )

        # 🎯 DÉTECTION PRÉALABLE : Commandes générales (résumé, analyse complète)
        user_lower = user_input.lower()
        general_document_commands = [
            "résume le pdf",
            "résume le doc",
            "résume le docx",
            "résume le document",
            "résume le fichier",
            "analyse le pdf",
            "analyse le doc",
            "analyse le docx",
            "analyse le document",
            "analyse le fichier",
            "explique le pdf",
            "explique le doc",
            "explique le docx",
            "explique le document",
            "explique le fichier",
        ]

        simple_commands = ["résume", "resume", "résumé", "analyse", "explique"]

        # 🔧 NOUVELLES COMMANDES : Détection spécifique du code
        code_commands = [
            "explique le code",
            "analyse le code",
            "décris le code",
            "code python",
            "explique le code python",
            "analyse le code python",
            "détaille le code",
        ]

        # Détecter les fichiers spécifiques mentionnés (ex: "game.py", "config.py", etc.)
        specific_file_pattern = r"\b\w+\.(py|js|html|css|java|cpp|c|php)\b"
        mentioned_files = re.findall(specific_file_pattern, user_input, re.IGNORECASE)

        is_general_command = (
            any(cmd in user_lower for cmd in general_document_commands)
            or user_lower.strip() in simple_commands
        )

        is_code_command = any(cmd in user_lower for cmd in code_commands)

        # 🎯 PRIORITÉ 1 : Fichier spécifique mentionné
        if mentioned_files:
            file_extensions = [f[1].lower() for f in mentioned_files]
            mentioned_filenames = [f"{name}.{ext}" for name, ext in mentioned_files]

            print(f"🎯 [SPECIFIC] Fichier spécifique détecté: {mentioned_filenames}")

            # Chercher le fichier dans les documents stockés
            target_file = None
            for filename in mentioned_filenames:
                if any(
                    filename.lower() in doc_name.lower()
                    for doc_name in stored_docs.keys()
                ):
                    target_file = next(
                        doc_name
                        for doc_name in stored_docs.keys()
                        if filename.lower() in doc_name.lower()
                    )
                    break

            if target_file:
                print(f"✅ [SPECIFIC] Fichier trouvé: {target_file}")
                target_content = stored_docs[target_file].get("content", "")

                # Si c'est un fichier de code ET une commande d'explication
                if (
                    any(
                        ext in ["py", "js", "html", "css", "java", "cpp", "c", "php"]
                        for ext in file_extensions
                    )
                    and is_code_command
                ):
                    print(f"🔧 [CODE] Explication de code demandée pour: {target_file}")
                    # Utiliser le processeur de code pour générer une explication détaillée
                    return self._explain_specific_code_file(
                        target_file, target_content, user_input
                    )
                else:
                    # Autres types de fichiers ou commandes générales
                    return self._create_universal_summary(
                        target_content, "document", "specific"
                    )

        # 🎯 PRIORITÉ 2 : Commandes de code générales (sans fichier spécifique)
        if is_code_command and not mentioned_files:
            print(f"🔧 [CODE] Commande de code générale détectée: '{user_input}'")

            # Chercher le dernier fichier de code ajouté
            code_extensions = [
                ".py",
                ".js",
                ".html",
                ".css",
                ".java",
                ".cpp",
                ".c",
                ".php",
            ]
            latest_code_file = None

            # Chercher dans l'ordre inverse (plus récent en premier)
            if hasattr(self.conversation_memory, "document_order"):
                for doc_name in reversed(self.conversation_memory.document_order):
                    if any(ext in doc_name.lower() for ext in code_extensions):
                        latest_code_file = doc_name
                        break

            if latest_code_file and latest_code_file in stored_docs:
                print(f"✅ [CODE] Fichier de code le plus récent: {latest_code_file}")
                target_content = stored_docs[latest_code_file].get("content", "")
                return self._explain_specific_code_file(
                    latest_code_file, target_content, user_input
                )
            else:
                print("⚠️ [CODE] Aucun fichier de code trouvé")

        # 🎯 PRIORITÉ 3 : Commandes générales sur documents
        if is_general_command:
            print(
                f"🎯 [GENERAL] Commande générale détectée: '{user_input}' - Récupération contenu complet"
            )

            # Pour les commandes générales, récupérer TOUT le contenu disponible
            if self.ultra_mode and self.context_manager:
                try:
                    # Récupérer tout le contenu en utilisant une requête générique
                    full_context = self.context_manager.get_relevant_context(
                        "document", max_chunks=50
                    )  # Plus de chunks pour avoir tout
                    if full_context and len(full_context.strip()) > 100:
                        print(
                            f"✅ [GENERAL] Contenu complet récupéré: {len(full_context)} caractères"
                        )
                        return self._create_universal_summary(
                            full_context, "document", "pdf"
                        )
                    else:
                        print(
                            "⚠️ [GENERAL] Contenu Ultra insuffisant, fallback vers mémoire classique"
                        )
                except Exception as e:
                    print(f"❌ [GENERAL] Erreur récupération Ultra: {e}")

            # Fallback vers la mémoire classique pour les commandes générales
            if stored_docs:
                all_content = ""
                for doc_name, doc_data in stored_docs.items():
                    content = doc_data.get("content", "")
                    if content:
                        all_content += f"\n\n=== {doc_name} ===\n{content}"

                if all_content:
                    print(
                        f"✅ [GENERAL] Contenu classique récupéré: {len(all_content)} caractères"
                    )
                    return self._create_universal_summary(
                        all_content, "document", "pdf"
                    )

        # 🚀 ÉTAPE 1: Tentative avec le système Ultra (1M tokens) pour questions spécifiques
        if self.ultra_mode and self.context_manager:
            try:
                print("🚀 [ULTRA] Recherche dans le contexte 1M tokens...")
                ultra_context = self.search_in_context(user_input)
                if ultra_context and ultra_context.strip() and len(ultra_context) > 50:
                    print(
                        f"✅ [ULTRA] Contexte trouvé: {len(ultra_context)} caractères"
                    )
                    intelligent_response = self._generate_intelligent_response(
                        user_input, ultra_context, "ULTRA"
                    )
                    if intelligent_response is not None:
                        return intelligent_response
                    else:
                        # 🧠 MODIFICATION : En mode Ultra, même si "non pertinent", générer une réponse basée sur le contenu trouvé
                        print(
                            "⚠️ [ULTRA] Génération d'une réponse forcée basée sur le contexte trouvé..."
                        )
                        # Générer une réponse universelle plutôt que de passer à internet
                        return (
                            self._create_universal_summary(
                                ultra_context, "document", "ultra"
                            )
                            + "\n\n*Note: Réponse basée sur le contenu Ultra 1M disponible*"
                        )
                else:
                    print("⚠️ [ULTRA] Contexte insuffisant ou vide")
            except Exception as e:
                print(f"❌ [ULTRA] Erreur: {e}")

        # 🔄 ÉTAPE 2: Utilisation des documents stockés avec recherche ciblée
        if not stored_docs and hasattr(self.conversation_memory, "stored_documents"):
            stored_docs = self.conversation_memory.stored_documents
            print(
                f"🔄 [CLASSIC] Utilisation stored_documents: {len(stored_docs)} documents"
            )

        if not stored_docs:
            return "❌ Aucun document disponible pour répondre à votre question."

        # 🎯 ÉTAPE 3: Recherche intelligente dans les documents
        print(f"🎯 [SEARCH] Recherche ciblée dans {len(stored_docs)} documents...")
        relevant_content = self._smart_document_search(user_input, stored_docs)

        if relevant_content:
            print(
                f"✅ [SEARCH] Contenu pertinent trouvé: {len(relevant_content)} caractères"
            )
            intelligent_response = self._generate_intelligent_response(
                user_input, relevant_content, "TARGETED"
            )
            if intelligent_response is not None:
                return intelligent_response
            else:
                # 🧠 MODIFICATION : Même si "non pertinent", générer une réponse basée sur le contenu trouvé
                print(
                    "⚠️ [SEARCH] Génération d'une réponse forcée basée sur le contenu trouvé..."
                )
                return (
                    self._create_universal_summary(
                        relevant_content, "document", "targeted"
                    )
                    + "\n\n*Note: Réponse basée sur le contenu disponible*"
                )
        else:
            print("⚠️ [SEARCH] Aucun contenu pertinent trouvé")
            # Fallback vers recherche internet seulement si vraiment aucun document
            return self._handle_internet_search(user_input, {})

    def _explain_specific_code_file(
        self, filename: str, content: str, _user_input: str
    ) -> str:
        """
        🔧 Explique spécifiquement un fichier de code en utilisant le processeur de code
        """
        try:
            processor = CodeProcessor()

            # Créer un fichier temporaire pour l'analyse
            # Déterminer l'extension
            if filename.endswith(".py"):
                temp_suffix = ".py"
            elif filename.endswith(".js"):
                temp_suffix = ".js"
            elif filename.endswith(".html"):
                temp_suffix = ".html"
            elif filename.endswith(".css"):
                temp_suffix = ".css"
            else:
                temp_suffix = ".py"  # Par défaut

            # Créer un fichier temporaire avec le contenu
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=temp_suffix, delete=False, encoding="utf-8"
            ) as temp_file:
                temp_file.write(content)
                temp_path = temp_file.name

            try:
                # Générer l'explication détaillée
                print(f"🔧 [CODE] Génération explication détaillée pour: {filename}")
                explanation = processor.generate_detailed_explanation(
                    temp_path, filename
                )

                # Ajouter un en-tête personnalisé
                final_explanation = explanation

                return final_explanation

            finally:
                # Nettoyer le fichier temporaire
                if os.path.exists(temp_path):
                    os.unlink(temp_path)

        except Exception as e:
            print(f"❌ [CODE] Erreur lors de l'explication: {e}")
            # Fallback vers une explication simple
            return f"""# 🔧 Analyse du fichier : `{filename}`

**Erreur lors de l'analyse avancée** : {str(e)}

## Contenu du fichier :

```python
{content}
```

💡 *Le système d'analyse avancée du code n'est pas disponible. Voici le contenu brut du fichier.*"""

    def _smart_document_search(self, user_input: str, stored_docs: dict) -> str:
        """
        🎯 Recherche intelligente dans les documents basée sur les mots-clés de la question
        """

        # Extraire les mots-clés importants de la question
        keywords = self._extract_question_keywords(user_input)
        print(f"🔑 [SEARCH] Mots-clés extraits: {keywords}")

        relevant_passages = []

        for doc_name, doc_data in stored_docs.items():
            content = doc_data.get("content", "")
            if not content:
                continue

            # Rechercher les passages contenant les mots-clés
            passages = self._find_relevant_passages(content, keywords, user_input)
            if passages:
                relevant_passages.extend([(doc_name, passage) for passage in passages])

        if relevant_passages:
            # Compiler les passages les plus pertinents
            result = []
            for doc_name, passage in relevant_passages[:3]:  # Top 3 passages
                result.append(f"📄 **{doc_name}**:\n{passage}\n")
            return "\n".join(result)

        return ""

    def _extract_question_keywords(self, user_input: str) -> list:
        """Extrait les mots-clés importants d'une question"""
        # Mots vides à ignorer
        stop_words = {
            "quel",
            "quelle",
            "quels",
            "quelles",
            "est",
            "sont",
            "le",
            "la",
            "les",
            "un",
            "une",
            "des",
            "de",
            "du",
            "dans",
            "sur",
            "avec",
            "pour",
            "par",
            "selon",
            "comment",
            "pourquoi",
            "que",
            "qui",
            "quoi",
            "où",
            "quand",
            "dont",
            "ce",
            "cette",
            "ces",
            "et",
            "ou",
            "mais",
        }

        # Mots importants techniques
        important_patterns = [
            "performance",
            "temps",
            "réponse",
            "système",
            "algorithme",
            "tri",
            "fusion",
            "version",
            "configuration",
            "json",
            "langage",
            "python",
            "recommandé",
            "débuter",
            "turing",
            "test",
            "proposé",
            "année",
            "tokens",
            "traiter",
            "million",
            "1m",
            "1000000",
            "scikit-learn",
            "pandas",
            "alan",
        ]

        keywords = []
        words = user_input.lower().split()

        for word in words:
            # Nettoyer le mot
            clean_word = word.strip('.,?!:;"()[]{}')

            # Garder si c'est un mot important ou pas dans stop_words
            if (
                clean_word not in stop_words and len(clean_word) > 2
            ) or clean_word in important_patterns:
                keywords.append(clean_word)

        return keywords

    def _find_relevant_passages(
        self, content: str, keywords: list, question: str
    ) -> list:
        """Trouve les passages pertinents dans un document"""
        passages = []

        # Diviser le contenu en paragraphes
        paragraphs = content.split("\n\n")

        for paragraph in paragraphs:
            if len(paragraph.strip()) < 20:  # Ignorer les paragraphes trop courts
                continue

            score = 0
            paragraph_lower = paragraph.lower()

            # Calculer le score de pertinence
            for keyword in keywords:
                if keyword in paragraph_lower:
                    score += 1

            # Bonus pour les questions spécifiques
            if "version" in question.lower() and any(
                v in paragraph_lower
                for v in ["version", "v.", "v", "1.", "2.", "3.", "4.", "5."]
            ):
                score += 2
            if "algorithme" in question.lower() and any(
                a in paragraph_lower
                for a in ["sort", "tri", "merge", "fusion", "insertion"]
            ):
                score += 2
            if "langage" in question.lower() and any(
                l in paragraph_lower
                for l in ["python", "java", "javascript", "c++", "programmation"]
            ):
                score += 2

            if score >= 1:  # Seuil de pertinence
                passages.append((score, paragraph.strip()[:500]))  # Limiter à 500 chars

        # Trier par score et retourner les meilleurs
        passages.sort(key=lambda x: x[0], reverse=True)
        return [passage[1] for passage in passages[:3]]

    def _generate_intelligent_response(
        self, user_input: str, content: str, source: str
    ) -> str:
        """
        🧠 Génère une réponse intelligente basée sur le contenu trouvé
        Retourne None si le contenu n'est pas pertinent pour la question
        """
        user_lower = user_input.lower()

        # 🔍 ÉTAPE 1: Détecter les commandes générales sur le document (PRIORITÉ ABSOLUE)
        general_document_commands = [
            "résume le pdf",
            "résume le doc",
            "résume le docx",
            "résume le document",
            "résume le fichier",
            "analyse le pdf",
            "analyse le doc",
            "analyse le docx",
            "analyse le document",
            "analyse le fichier",
            "explique le pdf",
            "explique le doc",
            "explique le docx",
            "explique le document",
            "explique le fichier",
        ]

        # Détecter aussi "résume" seul quand c'est clairement une commande générale
        simple_commands = [
            "résume",
            "resume",
            "résumé",
            "analyse",
            "explique",
            "décris le document",
        ]

        # Si c'est une commande générale, TOUJOURS traiter le document
        if (
            any(cmd in user_lower for cmd in general_document_commands)
            or user_lower.strip() in simple_commands
        ):
            print(
                f"✅ [RELEVANCE] Commande générale détectée: '{user_input}' - Traitement forcé"
            )
            return self._create_universal_summary(content, "document", "mixed")

        # 🔍 ÉTAPE 2: Vérifications de pertinence spécifiques AVANT l'analyse générale

        # Détecter les questions clairement hors sujet (monuments, géographie, etc.)
        irrelevant_topics = [
            "tour eiffel",
            "eiffel",
            "taille tour",
            "hauteur tour",
            "monument",
            "paris",
            "france",
            "capitale",
            "pays",
            "ville",
            "géographie",
            "président",
            "politique",
            "gouvernement",
            "histoire mondiale",
            "mathématiques",
            "physique",
            "chimie",
            "biologie",
        ]

        if any(topic in user_lower for topic in irrelevant_topics):
            print(f"⚠️ [RELEVANCE] Sujet hors contexte détecté: {user_input[:50]}...")
            return None

        # 🔍 ÉTAPE 3: Vérifier la pertinence générale par mots-clés SEULEMENT pour questions spécifiques
        question_keywords = self._extract_question_keywords(user_input)
        content_lower = content.lower()

        # Compter combien de mots-clés de la question apparaissent dans le contenu
        keyword_matches = sum(
            1 for keyword in question_keywords if keyword in content_lower
        )
        relevance_ratio = (
            keyword_matches / len(question_keywords) if question_keywords else 0
        )

        print(f"🔍 [RELEVANCE] Mots-clés question: {question_keywords}")
        print(
            f"🔍 [RELEVANCE] Correspondances: {keyword_matches}/{len(question_keywords)} = {relevance_ratio:.2f}"
        )

        # Seuil adaptatif selon le mode et le type de question
        if self.ultra_mode and self.context_manager:
            # En mode Ultra, être plus tolérant car le système trouve intelligemment le bon contenu
            base_threshold = 0.3  # Assoupli de 0.5 à 0.3 pour mode Ultra
        else:
            base_threshold = 0.4  # Assoupli de 0.5 à 0.4 pour mode classique

        if relevance_ratio < base_threshold and len(question_keywords) > 2:
            # Exceptions pour certains types de questions générales sur le document
            document_exceptions = ["document", "pdf", "docx"]
            if not any(exc in user_lower for exc in document_exceptions):
                print(
                    f"⚠️ [RELEVANCE] Contenu non pertinent (ratio: {relevance_ratio:.2f})"
                )
                return None

        # 🔍 ÉTAPE 2: Analyser le type de question pour adapter la réponse
        if "quel" in user_lower and "version" in user_lower:
            # Rechercher des numéros de version

            versions = re.findall(
                r"\b\d+\.\d+\.\d+\b|\bv?\d+\.\d+\b|\bversion\s+\d+",
                content,
                re.IGNORECASE,
            )
            if versions:
                return f"📊 **Version trouvée**: {versions[0]}\n\n📄 **Source** ({source}):\n{content[:300]}..."

        elif ("performance" in user_lower and "temps" in user_lower) or (
            "objectif" in user_lower and "performance" in user_lower
        ):
            # Rechercher des informations sur les performances et temps de réponse
            # Chercher des patterns de temps : "< 2 secondes", "3 secondes", "3000ms", etc.
            time_patterns = re.findall(
                r"[<>]?\s*\d+\s*(secondes?|ms|milliseconds?|s)\b",
                content,
                re.IGNORECASE,
            )
            perf_patterns = re.findall(
                r"(temps de (?:réponse|traitement|réponse))[:\s]*[<>]?\s*\d+\s*(secondes?|ms|milliseconds?|s)",
                content,
                re.IGNORECASE,
            )

            if time_patterns or perf_patterns:
                found_info = (
                    time_patterns[0]
                    if time_patterns
                    else f"{perf_patterns[0][0]}: {perf_patterns[0][1]}"
                )
                return f"⚡ **Performance système**: {found_info}\n\n📄 **Source** ({source}):\n{content[:400]}..."
            else:
                # Chercher des mentions générales de performance
                if any(
                    word in content.lower()
                    for word in [
                        "performance",
                        "temps de réponse",
                        "rapidité",
                        "latence",
                    ]
                ):
                    return f"📊 **Information performance trouvée**\n\n📄 **Source** ({source}):\n{content[:300]}..."
                else:
                    print(
                        "⚠️ [RELEVANCE] Aucune information de performance trouvée dans le contenu"
                    )
                    return None

        elif "algorithme" in user_lower:
            # Rechercher des algorithmes mentionnés
            algorithms = [
                "merge sort",
                "tri fusion",
                "insertion sort",
                "quick sort",
                "bubble sort",
            ]
            found_algos = [algo for algo in algorithms if algo in content.lower()]
            if found_algos:
                return f"🔧 **Algorithme identifié**: {found_algos[0]}\n\n📄 **Source** ({source}):\n{content[:400]}..."
            else:
                print("⚠️ [RELEVANCE] Aucun algorithme trouvé dans le contenu")
                return None

        elif "langage" in user_lower and "recommandé" in user_lower:
            # Rechercher des langages de programmation
            languages = ["python", "java", "javascript", "c++", "c#", "go", "rust"]
            found_langs = [lang for lang in languages if lang in content.lower()]
            if found_langs:
                return f"💻 **Langage recommandé**: {found_langs[0].capitalize()}\n\n📄 **Source** ({source}):\n{content[:400]}..."
            else:
                print(
                    "⚠️ [RELEVANCE] Aucun langage de programmation trouvé dans le contenu"
                )
                return None

        elif "turing" in user_lower:
            # Rechercher des informations sur Turing
            if (
                "alan" in content.lower()
                or "1950" in content
                or "turing" in content.lower()
            ):
                return f"🧠 **Test de Turing**: Proposé par Alan Turing en 1950\n\n📄 **Source** ({source}):\n{content[:400]}..."
            else:
                print("⚠️ [RELEVANCE] Aucune information sur Turing trouvée")
                return None

        elif any(
            word in user_lower for word in ["tour eiffel", "eiffel", "taille tour"]
        ):
            # Questions sur la tour Eiffel - clairement pas dans un document de stage (DOUBLÉ - SUPPRIMÉ)
            pass

        # 🔍 ÉTAPE 3: Questions spécifiques au document - RÉPONSE NATURELLE ET CONCISE
        if any(
            word in user_lower
            for word in [
                "date",
                "stage",
                "période",
                "rapport",
                "mission",
                "difficulté",
                "expérience",
            ]
        ):
            # Extraire une réponse courte et naturelle du contenu
            precise_answer = self._extract_precise_answer(user_input, content)
            if precise_answer:
                return precise_answer

        # 🔍 ÉTAPE 4: Vérification finale de pertinence (SEUIL ASSOUPLI POUR MODE ULTRA)
        if self.ultra_mode and self.context_manager:
            # En mode Ultra, être plus tolérant car le système trouve intelligemment le bon contenu
            final_threshold = 0.4  # Assoupli de 0.6 à 0.4 pour mode Ultra
        else:
            final_threshold = 0.5  # Assoupli de 0.6 à 0.5 pour mode classique

        if relevance_ratio >= final_threshold:
            # Même ici, extraire une réponse précise
            precise_answer = self._extract_precise_answer(user_input, content)
            if precise_answer:
                return precise_answer
            else:
                # Fallback avec filtrage de première personne
                clean_content = self._filter_first_person_content(content)
                if clean_content:
                    return f"Selon le document : {clean_content[:200]}..."
                else:
                    return "Je n'ai pas trouvé d'information pertinente dans le document pour répondre à cette question."
        else:
            print(
                f"⚠️ [RELEVANCE] Contenu non pertinent pour la question (ratio: {relevance_ratio:.2f} < {final_threshold})"
            )
            return None

    def _filter_first_person_content(self, content: str) -> str:
        """
        Filtre le contenu pour enlever les phrases de première personne
        ET trouve intelligemment la meilleure phrase pour répondre
        """
        sentences = re.split(r"[.!?]+", content)

        # D'abord chercher la phrase qui contient vraiment la réponse
        target_sentences = []
        clean_sentences = []

        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) < 10:
                continue

            sentence_lower = sentence.lower()

            # Filtre TRÈS SIMPLE et PRÉCIS pour éviter les faux positifs
            is_first_person = False

            # Recherche de mots/expressions de première personne UNIQUEMENT
            first_person_indicators = [
                "j'ai ",
                "je ",
                "j'",
                " moi ",
                "moi,",
                "moi.",
                "me ",
                "j'ai été",
                "je suis",
                "j'ai appris",
                "j'ai développé",
                "j'ai participé",
                "j'ai pu",
                "j'ai également",
                "j'étais",
                "mon stage",
                "ma mission",
                "mes tâches",
                "mon travail",
                "ma formation",
                "mon projet",
                "mes projets",
                "mon équipe",
            ]

            # Vérifier si la phrase contient vraiment de la première personne
            for indicator in first_person_indicators:
                if indicator in sentence_lower:
                    is_first_person = True
                    break

            # Garder seulement les phrases sans première personne
            if not is_first_person:
                clean_sentences.append(sentence)

                # Chercher spécifiquement les phrases avec "difficulté"
                if "difficulté" in sentence_lower:
                    target_sentences.append(sentence)

        # Retourner en priorité les phrases qui parlent de difficulté
        if target_sentences:
            # Prendre la phrase de difficulté + la suivante pour le contexte
            result = target_sentences[0]
            # Chercher la phrase suivante dans les phrases propres
            try:
                idx = clean_sentences.index(target_sentences[0])
                if idx + 1 < len(clean_sentences):
                    result += " " + clean_sentences[idx + 1]
            except ValueError:
                pass
            return result
        else:
            # Fallback sur les premières phrases propres
            return " ".join(clean_sentences[:2])

    def _extract_precise_answer(self, question: str, content: str) -> str:
        """
        🎯 Extrait une réponse précise et naturelle du contenu trouvé
        Retourne 2-3 phrases maximum, formulées naturellement
        """
        try:
            question_lower = question.lower()

            # 🎯 TRAITEMENT SPÉCIFIQUE PAR TYPE DE QUESTION

            # Questions sur les difficultés
            if any(
                word in question_lower
                for word in ["difficulté", "problème", "challenge", "obstacle"]
            ):
                return self._extract_difficulty_answer(content)

            # Questions sur les dates/périodes
            elif any(
                word in question_lower for word in ["date", "période", "quand", "durée"]
            ):
                return self._extract_date_answer(content)

            # Questions sur le lieu
            elif any(
                word in question_lower
                for word in ["lieu", "où", "endroit", "localisation"]
            ):
                return self._extract_location_answer(content)

            # Questions sur les missions/rôles
            elif any(
                word in question_lower
                for word in ["mission", "rôle", "tâche", "responsabilité", "travail"]
            ):
                return self._extract_mission_answer(content)

            # Questions sur l'expérience
            elif any(
                word in question_lower
                for word in ["expérience", "apprentissage", "bilan", "apport"]
            ):
                return self._extract_experience_answer(content)

            # Question générale - essayer d'extraire l'information la plus pertinente
            else:
                return self._extract_general_answer(content)

        except Exception as e:
            print(f"❌ [EXTRACT] Erreur: {e}")
            return None

    def _extract_difficulty_answer(self, content: str) -> str:
        """Extrait une réponse sur les difficultés"""
        # Diviser le contenu en phrases plus précisément
        sentences = re.split(r"[.!?]+", content)

        # Mots-clés génériques pour détecter les difficultés
        difficulty_keywords = [
            "difficulté",
            "problème",
            "challenge",
            "obstacle",
            "complexe",
            "compliqué",
            "difficile",
            "prise en main",
            "rencontré",
            "surmonté",
            "erreur",
            "échec",
            "blocage",
            "limitation",
            "contrainte",
            "enjeu",
            "défi",
        ]

        # D'ABORD : chercher toutes les phrases qui parlent de difficulté
        difficulty_sentences = []
        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) < 20:
                continue

            sentence_lower = sentence.lower()

            # Si la phrase contient des mots-clés de difficulté
            if any(keyword in sentence_lower for keyword in difficulty_keywords):
                difficulty_sentences.append((sentence, sentence_lower))

        print(
            f"🔍 [DEBUG] {len(difficulty_sentences)} phrases avec difficulté trouvées"
        )

        # ENSUITE : parmi ces phrases, prendre celle qui semble la plus factuelle
        for sentence, sentence_lower in difficulty_sentences:
            print(f"🔍 [DEBUG] Évaluation: {sentence[:80]}...")

            # Cette phrase parle-t-elle spécifiquement de "difficulté notable" ?
            if "difficulté" in sentence_lower and "notable" in sentence_lower:
                print("✅ [DEBUG] Phrase avec 'difficulté notable' trouvée !")

                # Nettoyer la phrase pour ne garder que la partie pertinente
                clean_sentence = self._clean_difficulty_sentence(sentence)
                return f"Selon le document, {clean_sentence.lower()}."

            # Cette phrase décrit-elle une difficulté concrète ?
            if any(
                verb in sentence_lower
                for verb in ["a été", "était", "est", "consistait"]
            ):
                print("✅ [DEBUG] Phrase descriptive trouvée !")
                clean_sentence = self._clean_difficulty_sentence(sentence)
                return f"Selon le document, {clean_sentence.lower()}."

        print(
            f"⚠️ [DEBUG] Aucune phrase appropriée trouvée parmi {len(difficulty_sentences)} candidates"
        )
        return None

    def _clean_difficulty_sentence(self, sentence: str) -> str:
        """
        Nettoie une phrase de difficulté pour ne garder que la partie pertinente
        """
        # Si la phrase contient "---" ou "•", couper là
        if "---" in sentence:
            sentence = sentence.split("---")[0].strip()

        if "•" in sentence:
            sentence = sentence.split("•")[0].strip()

        # Si la phrase est très longue, essayer de la couper à un point logique
        if len(sentence) > 200:
            # Chercher des points de coupure naturels après la description de la difficulté
            cut_points = [
                "avancées",
                "complexes",
                "techniques",
                "spécialisées",
                "précises",
                "détaillées",
                "sophistiquées",
            ]

            for cut_point in cut_points:
                if cut_point in sentence.lower():
                    # Trouver la position du mot de coupure
                    pos = sentence.lower().find(cut_point)
                    if pos > 50:  # S'assurer qu'on a assez de contenu
                        # Couper après le mot + éventuellement un peu plus
                        end_pos = pos + len(cut_point)
                        sentence = sentence[:end_pos].strip()
                        break

        # Nettoyer les caractères en fin
        sentence = sentence.rstrip(" .,;:")

        return sentence

    def _extract_date_answer(self, content: str) -> str:
        """Extrait une réponse sur les dates - VERSION GÉNÉRIQUE"""

        # Patterns génériques pour toutes sortes de dates
        date_patterns = [
            r"\b\d{1,2}\s+(janvier|février|mars|avril|mai|juin|juillet|août|septembre|octobre|novembre|décembre)\s+\d{4}\b",
            r"\b\d{1,2}\s+-\s+\d{1,2}\s+\w+\s+\d{4}\b",
            r"du\s+\d{1,2}\s+\w+\s+au\s+\d{1,2}\s+\w+\s+\d{4}",
            r"\d{1,2}/\d{1,2}/\d{4}",
            r"\d{4}-\d{1,2}-\d{1,2}",
            r"période\s*:\s*[^.]+",
            r"date\s*:\s*[^.]+",
            r"depuis\s+\d{4}",
            r"en\s+\d{4}",
        ]

        for pattern in date_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                # Extraire le contexte autour de la date
                start = max(0, match.start() - 30)
                end = min(len(content), match.end() + 30)
                context = content[start:end].strip()

                # Nettoyer et formater
                clean_context = self._clean_sentence(context)
                return f"Selon le document, {clean_context.lower()}."

        return None

    def _extract_location_answer(self, content: str) -> str:
        """Extrait une réponse sur le lieu - VERSION GÉNÉRIQUE"""
        # Mots-clés génériques pour tous types de lieux
        location_keywords = [
            "lieu",
            "endroit",
            "adresse",
            "localisation",
            "situé",
            "située",
            "emplacement",
            "ville",
            "région",
            "pays",
            "bureau",
            "siège",
            "site",
            "campus",
        ]

        sentences = content.replace("\n", " ").split(".")
        best_sentence = None
        best_score = 0

        for sentence in sentences:
            sentence_lower = sentence.lower()

            # Éviter la première personne
            if any(
                word in sentence_lower
                for word in ["j'ai", "je ", "mon ", "ma ", "mes "]
            ):
                continue

            score = sum(1 for keyword in location_keywords if keyword in sentence_lower)

            if score > best_score and len(sentence.strip()) > 20:
                best_score = score
                best_sentence = sentence.strip()

        if best_sentence:
            clean_sentence = self._clean_sentence(best_sentence)
            return f"Selon le document, {clean_sentence.lower()}."

        return None

    def _extract_mission_answer(self, content: str) -> str:
        """Extrait une réponse sur les missions - VERSION GÉNÉRIQUE"""
        # Mots-clés génériques pour toutes sortes de missions/tâches
        mission_keywords = [
            "mission",
            "rôle",
            "tâche",
            "responsabilité",
            "fonction",
            "travail",
            "activité",
            "objectif",
            "but",
            "attribution",
            "charge",
            "devoir",
            "assignment",
        ]

        sentences = content.replace("\n", " ").split(".")
        best_sentence = None
        best_score = 0

        for sentence in sentences:
            sentence = sentence.strip()
            sentence_lower = sentence.lower()

            # Éviter la première personne
            if any(
                word in sentence_lower
                for word in ["j'ai", "je ", "mon ", "ma ", "mes "]
            ):
                continue

            score = sum(1 for keyword in mission_keywords if keyword in sentence_lower)

            # Bonus pour les phrases qui décrivent concrètement des activités
            if any(
                verb in sentence_lower
                for verb in ["consiste", "comprend", "inclut", "implique"]
            ):
                score += 2

            if score > best_score and len(sentence) > 30:
                best_score = score
                best_sentence = sentence

        if best_sentence:
            clean_sentence = self._clean_sentence(best_sentence)
            return f"Selon le document, {clean_sentence.lower()}."

        return None

    def _extract_experience_answer(self, content: str) -> str:
        """Extrait une réponse sur l'expérience - VERSION GÉNÉRIQUE"""
        # Mots-clés génériques pour l'apprentissage et l'expérience
        experience_keywords = [
            "appris",
            "acquis",
            "développé",
            "expérience",
            "compétences",
            "bilan",
            "formation",
            "apprentissage",
            "connaissances",
            "expertise",
            "savoir",
            "capacité",
            "aptitude",
            "maîtrise",
            "progression",
        ]

        sentences = content.replace("\n", " ").split(".")
        best_sentence = None
        best_score = 0

        for sentence in sentences:
            sentence_lower = sentence.lower()

            # Éviter la première personne pour l'IA
            if any(
                word in sentence_lower
                for word in ["j'ai", "je ", "mon ", "ma ", "mes "]
            ):
                continue

            score = sum(
                1 for keyword in experience_keywords if keyword in sentence_lower
            )

            if score > best_score and len(sentence.strip()) > 30:
                best_score = score
                best_sentence = sentence.strip()

        if best_sentence:
            clean_sentence = self._clean_sentence(best_sentence)
            return f"D'après le document, {clean_sentence.lower()}."

        return None

    def _clean_sentence(self, sentence: str) -> str:
        """
        🧹 Nettoie une phrase pour éviter les doublons et problèmes de formatage
        """
        # Supprimer les espaces multiples
        sentence = " ".join(sentence.split())

        # Détecter et corriger les doublons de mots (comme "une Une")
        words = sentence.split()
        cleaned_words = []

        for i, word in enumerate(words):
            # Si ce n'est pas le premier mot et qu'il est identique au précédent (case insensitive)
            if i > 0 and word.lower() == words[i - 1].lower():
                continue  # Ignorer le doublon
            cleaned_words.append(word)

        sentence = " ".join(cleaned_words)

        # Supprimer les séparateurs de sections (---, ►, etc.)
        sentence = sentence.replace("---", "").replace("►", "").replace("→", "")

        # Nettoyer les caractères en début/fin
        sentence = sentence.strip(" .-•")

        return sentence

    def _extract_general_answer(self, content: str) -> str:
        """Extrait une réponse générale"""
        # Prendre la première phrase substantielle du contenu
        sentences = content.replace("\n", " ").split(".")
        for sentence in sentences:
            if len(sentence.strip()) > 50:  # Phrase avec du contenu
                return f"Selon le document, {sentence.strip()}."

        return None

    def _generate_fallback_response(self, _user_input: str, stored_docs: dict) -> str:
        """Génère une réponse de fallback quand aucun contenu spécifique n'est trouvé"""
        doc_count = len(stored_docs)

        # Essayer de donner une réponse basée sur les métadonnées
        doc_names = list(stored_docs.keys())
        doc_types = set()

        for doc_data in stored_docs.values():
            if doc_data.get("type"):
                doc_types.add(doc_data["type"])

        return f"""📋 **Information disponible**:

🗂️ J'ai {doc_count} document(s) en mémoire: {', '.join(doc_names[:3])}...
📝 Types: {', '.join(doc_types) if doc_types else 'Divers'}

❓ Je n'ai pas trouvé d'information spécifique pour répondre à votre question dans les documents analysés.

💡 **Suggestions**:
- Reformulez votre question avec d'autres termes
- Posez une question plus générale sur le contenu
- Demandez un résumé des documents disponibles"""

    def _generate_ultra_response(self, user_input: str, context: str) -> str:
        """Génère une réponse basée sur le contexte Ultra"""
        # Déterminer le type de question
        user_lower = user_input.lower()

        # Si c'est une demande d'explication de code, cibler les fichiers de code
        code_keywords = [
            "explique le code",
            "analyse le code",
            "décris le code",
            "code python",
            "fichier python",
            "script python",
        ]
        detailed_keywords = [
            "explique le code en détail",
            "explique le code de manière détaillé",
            "fais une analyse détaillé du code",
            "analyse détaillée du code",
            "explication détaillée du code",
            "analyse complète du code",
            "analyse approfondie du code",
        ]

        # Vérifier d'abord si c'est une demande d'analyse détaillée
        is_detailed_request = any(
            keyword in user_lower for keyword in detailed_keywords
        )
        is_code_request = (
            any(keyword in user_lower for keyword in code_keywords)
            or "explique" in user_lower
        )

        if is_detailed_request or (
            is_code_request
            and (
                "détail" in user_lower
                or "détaillé" in user_lower
                or "détaillée" in user_lower
            )
        ):
            print("🔍 [ULTRA] Détection d'une demande d'explication de code DÉTAILLÉE")

            # Chercher spécifiquement les fichiers de code
            if (
                hasattr(self.conversation_memory, "stored_documents")
                and self.conversation_memory.stored_documents
            ):
                docs = self.conversation_memory.stored_documents

                # Filtrer les fichiers de code (extensions .py, .js, .java, etc.)
                code_docs = {}
                for doc_name, doc_data in docs.items():
                    if (
                        doc_name.endswith(
                            (
                                ".py",
                                ".js",
                                ".java",
                                ".cpp",
                                ".c",
                                ".ts",
                                ".go",
                                ".rs",
                                ".php",
                            )
                        )
                        or doc_data.get("type") == "code"
                    ):
                        code_docs[doc_name] = doc_data

                if code_docs:
                    # Prendre le fichier de code le plus récent ou le seul disponible
                    latest_code_file = list(code_docs.keys())[-1]  # Dernier ajouté
                    doc_data = code_docs[latest_code_file]
                    content = doc_data.get("content", "")

                    print(
                        f"� [ULTRA] Analyse détaillée de code pour: {latest_code_file} ({len(content)} caractères)"
                    )

                    if content:
                        # Utiliser le processeur de code pour l'analyse détaillée
                        try:
                            code_processor = CodeProcessor()

                            # Créer un fichier temporaire pour l'analyse
                            with tempfile.NamedTemporaryFile(
                                mode="w", suffix=".py", delete=False, encoding="utf-8"
                            ) as temp_file:
                                temp_file.write(content)
                                temp_file_path = temp_file.name

                            # Générer l'explication détaillée
                            detailed_explanation = (
                                code_processor.generate_detailed_explanation(
                                    temp_file_path, latest_code_file
                                )
                            )

                            # Nettoyer le fichier temporaire
                            os.unlink(temp_file_path)

                            return detailed_explanation

                        except Exception as e:
                            print(f"⚠️ [ULTRA] Erreur analyse détaillée: {e}")
                            # Fallback vers l'analyse simple
                            return self._explain_code_content(content, latest_code_file)
                    else:
                        return f"Le fichier de code {latest_code_file} semble vide."
                else:
                    return "Je n'ai pas trouvé de fichiers de code en mémoire pour une analyse détaillée. Veuillez d'abord traiter un fichier Python, JavaScript ou autre langage de programmation."

        elif is_code_request:
            print("�🐍 [ULTRA] Détection d'une demande d'explication de code standard")

            # Chercher spécifiquement les fichiers de code
            if (
                hasattr(self.conversation_memory, "stored_documents")
                and self.conversation_memory.stored_documents
            ):
                docs = self.conversation_memory.stored_documents

                # Filtrer les fichiers de code (extensions .py, .js, .java, etc.)
                code_docs = {}
                for doc_name, doc_data in docs.items():
                    if (
                        doc_name.endswith(
                            (
                                ".py",
                                ".js",
                                ".java",
                                ".cpp",
                                ".c",
                                ".ts",
                                ".go",
                                ".rs",
                                ".php",
                            )
                        )
                        or doc_data.get("type") == "code"
                    ):
                        code_docs[doc_name] = doc_data

                if code_docs:
                    # Prendre le fichier de code le plus récent ou le seul disponible
                    latest_code_file = list(code_docs.keys())[-1]  # Dernier ajouté
                    doc_data = code_docs[latest_code_file]
                    content = doc_data.get("content", "")

                    print(
                        f"🐍 [ULTRA] Explication de code pour: {latest_code_file} ({len(content)} caractères)"
                    )

                    if content:
                        return self._explain_code_content(content, latest_code_file)
                    else:
                        return f"Le fichier de code {latest_code_file} semble vide."
                else:
                    return "Je n'ai pas trouvé de fichiers de code en mémoire. Veuillez d'abord traiter un fichier Python, JavaScript ou autre langage de programmation."

        # Si c'est une demande de résumé, utiliser create_universal_summary
        if any(
            word in user_lower for word in ["résume", "résumé", "summary", "synthèse"]
        ):
            print("🔍 [ULTRA] Recherche de documents pour résumé universel...")

            # Debug détaillé
            print(
                f"🔍 [DEBUG] conversation_memory.stored_documents: {len(self.conversation_memory.stored_documents)}"
            )
            print(
                f"🔍 [DEBUG] documents keys: {list(self.conversation_memory.stored_documents.keys())}"
            )

            # Fallback vers mémoire classique pour le résumé
            if (
                hasattr(self.conversation_memory, "stored_documents")
                and self.conversation_memory.stored_documents
            ):
                # Prendre le dernier document ajouté ou tous si pas de préférence
                docs = self.conversation_memory.stored_documents
                print(f"🔍 [DEBUG] Trouvé {len(docs)} documents dans stored_documents")

                if len(docs) == 1:
                    doc_name = list(docs.keys())[0]
                    doc_data = docs[doc_name]
                    content = doc_data.get("content", "")
                    print(
                        f"📄 [ULTRA] Résumé universel pour: {doc_name} ({len(content)} caractères)"
                    )
                    if content:
                        return self._create_universal_summary(content, doc_name, "PDF")
                    else:
                        print("⚠️ [DEBUG] Contenu vide dans doc_data")
                        return "Le document trouvé semble vide."
                else:
                    # Multiple documents - créer un résumé combiné
                    print(f"📄 [ULTRA] Résumé de {len(docs)} documents")
                    summaries = []
                    for doc_name, doc_data in docs.items():
                        content = doc_data.get("content", "")
                        if content:
                            summaries.append(
                                self._create_universal_summary(
                                    content, doc_name, "document"
                                )
                            )
                    if summaries:
                        return "\n\n" + "=" * 50 + "\n\n".join(summaries)
                    else:
                        return "Aucun document avec du contenu trouvé."
            else:
                print("⚠️ [DEBUG] Aucun document dans stored_documents")
                # Essayer aussi get_document_content()
                classic_content = self.conversation_memory.get_document_content()
                print(f"🔍 [DEBUG] get_document_content(): {len(classic_content)}")
                if classic_content:
                    # Utiliser le contenu classique
                    return self._create_universal_summary(
                        str(classic_content), "document", "unknown"
                    )

                return "Je n'ai pas de documents en mémoire pour créer un résumé."

        elif any(
            word in user_lower for word in ["analyse", "analyze", "explique", "détail"]
        ):
            if not context or context.strip() == "Aucun contexte pertinent trouvé.":
                # Fallback vers mémoire classique
                return self._generate_classic_response(
                    user_input, self.conversation_memory.stored_documents
                )

            return f"""🔍 **Analyse détaillée**

D'après le document en mémoire:

{context[:1500]}...

📊 Cette analyse exploite la capacité du système 1M tokens pour une compréhension approfondie."""

        else:
            if not context or context.strip() == "Aucun contexte pertinent trouvé.":
                # Fallback vers mémoire classique
                return self._generate_classic_response(
                    user_input, self.conversation_memory.stored_documents
                )

            return f"""📚 **Réponse basée sur le document**

{context[:1000]}...

✨ Réponse générée grâce au système 1M tokens pour une précision maximale."""

    def _generate_classic_response(self, user_input: str, stored_docs: dict) -> str:
        """Génère une réponse basée sur la mémoire classique"""
        if not stored_docs:
            return "Je n'ai pas de documents en mémoire pour répondre à votre question."

        # NOUVELLE LOGIQUE : Si le prompt contient déjà une instruction de document spécifique, la respecter
        if "🚨 RÈGLE ABSOLUE ET OBLIGATOIRE 🚨" in user_input:
            # Le prompt vient de ai_engine.py avec un document spécifique - NE PAS interférer
            lines = user_input.split("\n")
            document_content = ""
            in_content_section = False

            for line in lines:
                if "📄 CONTENU DU DOCUMENT" in line:
                    in_content_section = True
                    continue
                elif "🔒 INSTRUCTIONS STRICTES:" in line:
                    break
                elif in_content_section and line.strip():
                    document_content += line + "\n"

            if document_content.strip():
                # Extraire le nom du document
                doc_name = "document spécifié"
                for line in lines:
                    if "🎯 DOCUMENT UNIQUE À ANALYSER:" in line:
                        doc_name = line.split(":", 1)[1].strip()
                        break

                # Traiter UNIQUEMENT ce contenu
                return self._create_universal_summary(
                    document_content.strip(), doc_name, "DOCX"
                )

        # LOGIQUE AMÉLIORÉE pour la sélection de documents multiples
        user_lower = user_input.lower().strip()

        # Détection de références à des documents spécifiques
        selected_doc = self._identify_target_document(user_input, stored_docs)

        # Gestion des demandes de résumé avec sélection de document
        resume_keywords = ["résume", "resume", "résumé"]

        if any(keyword in user_lower for keyword in resume_keywords):

            if selected_doc:
                # Document spécifique identifié
                doc_data = stored_docs[selected_doc]
                content = doc_data.get("content", "")
                doc_type = doc_data.get("type", "document")

                if content:
                    return self._create_universal_summary(
                        content, selected_doc, doc_type
                    )
                else:
                    return (
                        f"Le document '{selected_doc}' semble vide ou non accessible."
                    )

            # Si seulement un document, l'utiliser directement
            elif len(stored_docs) == 1:
                doc_name = list(stored_docs.keys())[0]
                doc_data = stored_docs[doc_name]
                content = doc_data.get("content", "")

                if content:
                    return self._create_universal_summary(
                        content, doc_name, doc_data.get("type", "document")
                    )
                else:
                    return f"Le document '{doc_name}' semble vide."

            # Plusieurs documents disponibles - demander de préciser
            else:
                doc_list = list(stored_docs.keys())
                summary = "**Plusieurs documents sont disponibles**\n\n"
                summary += "Voici les documents que j'ai en mémoire :\n\n"

                for i, doc_name in enumerate(doc_list, 1):
                    doc_data = stored_docs[doc_name]
                    doc_type = doc_data.get("type", "document")
                    word_count = (
                        len(doc_data.get("content", "").split())
                        if doc_data.get("content")
                        else 0
                    )
                    summary += f"**{i}.** `{doc_name}` ({doc_type.upper()}, ~{word_count} mots)\n"

                summary += "\n**Précisez votre demande :**\n"
                summary += '• "résume le document 1" ou "résume le premier"\n'
                summary += f'• "résume {doc_list[0]}" (nom complet)\n'
                summary += '• "résume le dernier document"\n'

                return summary

        # Pour les autres questions sur documents, utiliser le dernier ou chercher le plus pertinent
        if selected_doc:
            doc_data = stored_docs[selected_doc]
            content = doc_data.get("content", "")

            # Réponse contextuelle sur le document spécifique
            return f"Concernant le document '{selected_doc}' : {content[:200]}..."

        # Fallback : utiliser le dernier document
        if stored_docs:
            last_doc = list(stored_docs.keys())[-1]
            doc_data = stored_docs[last_doc]
            content = doc_data.get("content", "")

            return f"D'après le document '{last_doc}' : {content[:200]}..."

        return "Je n'ai pas trouvé d'information pertinente dans les documents disponibles."

    def _identify_target_document(
        self, user_input: str, stored_docs: Dict[str, Any]
    ) -> str:
        """Identifie le document cible à partir de l'input utilisateur"""
        user_lower = user_input.lower().strip()
        doc_list = list(stored_docs.keys())

        # Références numériques
        if (
            "premier" in user_lower
            or "1er" in user_lower
            or ("document 1" in user_lower)
            or ("le 1" in user_lower)
        ):
            return doc_list[0] if doc_list else None

        if (
            "deuxième" in user_lower
            or "2ème" in user_lower
            or ("document 2" in user_lower)
            or ("le 2" in user_lower)
        ):
            return doc_list[1] if len(doc_list) > 1 else None

        if (
            "troisième" in user_lower
            or "3ème" in user_lower
            or ("document 3" in user_lower)
            or ("le 3" in user_lower)
        ):
            return doc_list[2] if len(doc_list) > 2 else None

        if "dernier" in user_lower or "dernière" in user_lower:
            return doc_list[-1] if doc_list else None

        # Références par nom partiel
        for doc_name in doc_list:
            # Vérifier si le nom du document (ou une partie) est mentionné
            doc_name_lower = doc_name.lower()
            doc_base_name = doc_name_lower.replace(".pdf", "").replace(".docx", "")

            if doc_name_lower in user_lower or doc_base_name in user_lower:
                return doc_name

            # Vérifier les mots individuels du nom de fichier
            doc_words = doc_base_name.replace("_", " ").replace("-", " ").split()
            if len(doc_words) > 1:
                matches = sum(
                    1 for word in doc_words if len(word) > 3 and word in user_lower
                )
                if (
                    matches >= len(doc_words) // 2
                ):  # Au moins la moitié des mots significatifs
                    return doc_name

        return None

    def _identify_target_document(
        self, user_input: str, stored_docs: Dict[str, Any]
    ) -> str:
        """Identifie le document cible à partir de l'input utilisateur"""
        user_lower = user_input.lower().strip()
        doc_list = list(stored_docs.keys())

        # Références numériques
        if (
            "premier" in user_lower
            or "1er" in user_lower
            or ("document 1" in user_lower)
            or ("le 1" in user_lower)
        ):
            return doc_list[0] if doc_list else None

        if (
            "deuxième" in user_lower
            or "2ème" in user_lower
            or ("document 2" in user_lower)
            or ("le 2" in user_lower)
        ):
            return doc_list[1] if len(doc_list) > 1 else None

        if (
            "troisième" in user_lower
            or "3ème" in user_lower
            or ("document 3" in user_lower)
            or ("le 3" in user_lower)
        ):
            return doc_list[2] if len(doc_list) > 2 else None

        if "dernier" in user_lower or "dernière" in user_lower:
            return doc_list[-1] if doc_list else None

        # Références par nom partiel
        for doc_name in doc_list:
            # Vérifier si le nom du document (ou une partie) est mentionné
            doc_name_lower = doc_name.lower()
            doc_base_name = doc_name_lower.replace(".pdf", "").replace(".docx", "")

            if doc_name_lower in user_lower or doc_base_name in user_lower:
                return doc_name

            # Vérifier les mots individuels du nom de fichier
            doc_words = doc_base_name.replace("_", " ").replace("-", " ").split()
            if len(doc_words) > 1:
                matches = sum(
                    1 for word in doc_words if len(word) > 3 and word in user_lower
                )
                if (
                    matches >= len(doc_words) // 2
                ):  # Au moins la moitié des mots significatifs
                    return doc_name

        return None

    def _process_document_question(
        self, user_input: str, target_docs: Dict[str, Any], reference_detected: bool
    ) -> str:
        """
        Traite les questions sur les documents PDF/DOCX
        """
        user_lower = user_input.lower()

        # Si c'est une demande de résumé simple
        if any(
            keyword in user_lower
            for keyword in ["résume", "resume", "résumé", "summary", "sommaire"]
        ):
            if len(target_docs) == 1:
                doc_name = list(target_docs.keys())[0]
                doc_content = target_docs[doc_name]["content"]

                # Déterminer le type de document
                if any(ext in doc_name.lower() for ext in ["pdf", "livret"]):
                    doc_type = "PDF"
                elif any(ext in doc_name.lower() for ext in ["docx", "doc", "notes"]):
                    doc_type = "document"
                else:
                    doc_type = "document"

                return self._create_universal_summary(doc_content, doc_name, doc_type)
            else:
                # Plusieurs documents, faire un résumé pour chacun
                summaries = []
                for doc_name, doc_data in target_docs.items():
                    doc_content = doc_data["content"]
                    doc_type = "PDF" if "pdf" in doc_name.lower() else "document"
                    summaries.append(
                        self._create_universal_summary(doc_content, doc_name, doc_type)
                    )
                return "\n\n".join(summaries)

        # Pour les autres questions, utiliser la logique existante de recherche
        question_keywords = self._extract_question_keywords(user_input)

        # Recherche dans les documents ciblés
        best_matches = []

        for filename, doc_data in target_docs.items():
            content = doc_data["content"]
            matches = self._find_relevant_passages(
                content, question_keywords, user_input
            )

            if matches:
                best_matches.extend(
                    [
                        {
                            "filename": filename,
                            "passage": match["passage"],
                            "context": match["context"],
                            "relevance": match["relevance"],
                        }
                        for match in matches
                    ]
                )

        if not best_matches:
            # Recherche plus large si aucune correspondance exacte
            return self._generate_general_document_response(user_input, target_docs)

        # Trier par pertinence et prendre les meilleurs résultats
        best_matches.sort(key=lambda x: x["relevance"], reverse=True)
        top_matches = best_matches[:3]

        # Construire la réponse
        response_parts = []

        if len(target_docs) == 1:
            doc_name = list(target_docs.keys())[0]
            if reference_detected:
                doc_position = self._get_document_position_description(doc_name)
                response_parts.append(
                    f'D\'après le {doc_position} document "{doc_name}" :'
                )
            else:
                response_parts.append(f'D\'après le document "{doc_name}" :')
        else:
            response_parts.append("D'après les documents que j'ai analysés :")

        for i, match in enumerate(top_matches, 1):
            passage = match["passage"]
            if len(passage) > 300:
                passage = passage[:297] + "..."

            if len(target_docs) > 1:
                response_parts.append(f"\n{i}. **Dans {match['filename']}** :")
                response_parts.append(f'   "{passage}"')
            else:
                response_parts.append(f"\n• {passage}")

            if match["context"]:
                context = match["context"]
                if len(context) > 200:
                    context = context[:197] + "..."
                response_parts.append(f"   Contexte : {context}")

        # Ajouter une phrase de conclusion
        if len(top_matches) > 1:
            response_parts.append(
                f"\nJ'ai trouvé {len(best_matches)} références pertinentes dans le(s) document(s). Voulez-vous que je détaille un point particulier ?"
            )
        else:
            response_parts.append(
                "\nC'est ce que j'ai trouvé de plus pertinent. Avez-vous besoin de plus de détails ?"
            )

        return "\n".join(response_parts)

    def _extract_question_keywords(self, question: str) -> List[str]:
        """
        Extrait les mots-clés importants d'une question avec tolérance aux fautes

        Args:
            question: Question posée

        Returns:
            Liste des mots-clés
        """
        # Mots vides à ignorer
        stop_words = {
            "le",
            "la",
            "les",
            "un",
            "une",
            "des",
            "et",
            "ou",
            "à",
            "au",
            "aux",
            "ce",
            "ces",
            "dans",
            "en",
            "par",
            "pour",
            "sur",
            "il",
            "elle",
            "ils",
            "elles",
            "je",
            "tu",
            "nous",
            "vous",
            "que",
            "qui",
            "dont",
            "où",
            "quoi",
            "comment",
            "pourquoi",
            "avec",
            "cette",
            "comme",
            "plus",
            "moins",
            "sans",
            "très",
            "tout",
            "tous",
            "toutes",
            "bien",
            "être",
            "avoir",
            "faire",
            "aller",
            "venir",
            "voir",
            "savoir",
            "pouvoir",
            "vouloir",
            "devoir",
            "peut",
            "peuvent",
            "doit",
            "doivent",
            "dit",
            "peux",
            "explique",
            "moi",
            "document",
            "pdf",
            "fichier",
        }

        # Extraire les mots de 2+ caractères (abaissé pour capturer "no", "n°")
        words = re.findall(r"\b\w{2,}\b", question.lower())
        keywords = [word for word in words if word not in stop_words]

        # Ajouter des variantes pour les fautes communes et les synonymes
        expanded_keywords = []
        for keyword in keywords:
            expanded_keywords.append(keyword)

            # Corrections communes de fautes d'orthographe et synonymes - TRÈS ÉTENDU
            corrections = {
                # Urgence et variations
                "urgence": [
                    "urgance",
                    "urgense",
                    "urgent",
                    "urgents",
                    "emergency",
                    "emergancy",
                    "emerjency",
                ],
                "urgent": ["urgence", "urgance", "urgense", "urgents", "emergency"],
                # Numéros et variations
                "numéro": [
                    "numero",
                    "numeros",
                    "numerot",
                    "n°",
                    "no",
                    "nr",
                    "num",
                    "number",
                    "tel",
                    "telephone",
                    "tél",
                ],
                "numero": [
                    "numéro",
                    "numeros",
                    "numerot",
                    "n°",
                    "no",
                    "nr",
                    "num",
                    "number",
                ],
                "number": ["numéro", "numero", "n°", "no", "nr", "num"],
                # Sécurité et variations
                "sécurité": [
                    "securite",
                    "securité",
                    "secorite",
                    "security",
                    "safety",
                    "saftey",
                ],
                "securite": ["sécurité", "securité", "secorite", "security", "safety"],
                "security": ["sécurité", "securite", "safety", "secorite"],
                # Défibrillateur et variations
                "défibrillateur": [
                    "defibrillateur",
                    "defibrillateur",
                    "défibrillateur",
                    "defibrillator",
                    "defibrulator",
                ],
                "defibrillateur": [
                    "défibrillateur",
                    "defibrillateur",
                    "défibrillateur",
                    "defibrillator",
                ],
                "defibrillator": [
                    "défibrillateur",
                    "defibrillateur",
                    "defibrillateur",
                    "défibrillateur",
                ],
                # Extincteur et variations
                "extincteur": [
                    "extincteurs",
                    "estincteur",
                    "fire",
                    "extinguisher",
                    "extinquisher",
                ],
                "extinguisher": [
                    "extincteur",
                    "extincteurs",
                    "estincteur",
                    "extinquisher",
                ],
                # Secours et variations
                "secours": [
                    "secour",
                    "secoure",
                    "secours",
                    "help",
                    "aide",
                    "assistance",
                    "emergency",
                    "urgence",
                ],
                "help": ["secours", "aide", "assistance", "secour", "secoure"],
                "aide": ["secours", "help", "assistance", "secour", "secoure"],
                # Téléphone et variations
                "téléphone": [
                    "telephone",
                    "telefone",
                    "phone",
                    "tel",
                    "appel",
                    "tél",
                    "telephon",
                ],
                "telephone": ["téléphone", "telefone", "phone", "tel", "appel", "tél"],
                "phone": ["téléphone", "telephone", "telefone", "tel", "appel"],
                "tel": ["téléphone", "telephone", "phone", "telefone", "appel", "tél"],
                # Poste et variations
                "poste": ["post", "postes", "extension", "ext", "poste"],
                "extension": ["poste", "post", "ext", "postes"],
                "ext": ["extension", "poste", "post", "postes"],
                # Travail et variations
                "travail": [
                    "travaille",
                    "travai",
                    "work",
                    "job",
                    "bureau",
                    "office",
                    "boulot",
                ],
                "work": ["travail", "travaille", "job", "bureau", "boulot"],
                "bureau": ["office", "travail", "work", "job"],
                # Contact et variations
                "contact": [
                    "contacter",
                    "appeler",
                    "joindre",
                    "call",
                    "telephoner",
                    "téléphoner",
                    "contacte",
                ],
                "contacter": ["contact", "appeler", "joindre", "call", "telephoner"],
                "appeler": ["contact", "contacter", "joindre", "call", "telephoner"],
                "call": ["contact", "contacter", "appeler", "joindre"],
                # Accident et variations
                "accident": [
                    "incidents",
                    "incident",
                    "blessure",
                    "injury",
                    "emergency",
                    "blessé",
                    "blesser",
                ],
                "incident": [
                    "accident",
                    "incidents",
                    "blessure",
                    "injury",
                    "emergency",
                ],
                "blessure": ["accident", "incident", "injury", "blessé", "blesser"],
                "injury": ["accident", "incident", "blessure", "blessé"],
                # Évacuation et variations
                "évacuation": [
                    "evacuation",
                    "sortie",
                    "exit",
                    "evacuer",
                    "évacuer",
                    "evacuate",
                ],
                "evacuation": ["évacuation", "sortie", "exit", "evacuer", "évacuer"],
                "sortie": ["évacuation", "evacuation", "exit", "evacuer"],
                "exit": ["évacuation", "evacuation", "sortie", "evacuer"],
                # Alerte et variations
                "alerte": [
                    "alarme",
                    "alert",
                    "warning",
                    "signal",
                    "sonnette",
                    "alarme",
                ],
                "alarme": ["alerte", "alert", "warning", "signal", "sonnette"],
                "alert": ["alerte", "alarme", "warning", "signal"],
                "warning": ["alerte", "alarme", "alert", "signal"],
                # Responsable et variations
                "responsable": [
                    "chef",
                    "manager",
                    "supervisor",
                    "directeur",
                    "direction",
                    "dirigeant",
                    "boss",
                ],
                "chef": ["responsable", "manager", "supervisor", "directeur", "boss"],
                "manager": ["responsable", "chef", "supervisor", "directeur", "boss"],
                "directeur": [
                    "responsable",
                    "chef",
                    "manager",
                    "supervisor",
                    "direction",
                ],
                # Procédure et variations
                "procédure": [
                    "procedure",
                    "protocol",
                    "protocole",
                    "consigne",
                    "instruction",
                    "procedur",
                ],
                "procedure": [
                    "procédure",
                    "protocol",
                    "protocole",
                    "consigne",
                    "instruction",
                ],
                "protocol": ["procédure", "procedure", "protocole", "consigne"],
                "protocole": ["procédure", "procedure", "protocol", "consigne"],
                "consigne": ["procédure", "procedure", "instruction", "protocol"],
                "instruction": ["procédure", "procedure", "consigne", "protocol"],
                # Services d'urgence
                "samu": [
                    "15",
                    "ambulance",
                    "medical",
                    "emergency",
                    "urgence",
                    "medecin",
                ],
                "pompiers": ["18", "fire", "brigade", "sapeurs", "firefighter"],
                "police": ["17", "gendarmerie", "authorities", "gendarme", "policier"],
                "ambulance": ["samu", "15", "medical", "emergency", "urgence"],
                # Mots interrogatifs avec fautes
                "où": ["ou", "where", "endroit", "lieu", "place", "location"],
                "ou": ["où", "where", "endroit", "lieu", "place"],
                "comment": ["how", "procedure", "faire", "agir", "réagir"],
                "que": ["what", "quoi", "chose", "thing"],
                "qui": ["who", "personne", "person", "gens"],
                "quand": ["when", "moment", "temps", "heure"],
                "pourquoi": ["why", "reason", "raison"],
                "combien": ["how much", "how many", "nombre", "quantité"],
                # Lieux et équipements
                "trouve": ["trouver", "located", "situé", "position"],
                "trouver": ["trouve", "located", "situé", "chercher"],
                "located": ["trouve", "trouver", "situé", "position"],
                "situé": ["trouve", "trouver", "located", "position"],
                # Actions
                "faire": ["do", "agir", "réagir", "action"],
                "agir": ["faire", "do", "réagir", "action", "react"],
                "réagir": ["faire", "agir", "do", "react", "reaction"],
            }

            # Ajouter les variantes si le mot correspond à une correction
            for correct, variants in corrections.items():
                if keyword == correct:
                    expanded_keywords.extend(variants)
                elif keyword in variants:
                    expanded_keywords.append(correct)
                    expanded_keywords.extend([v for v in variants if v != keyword])

        # Ajouter des concepts liés selon le contexte
        question_lower = question.lower()

        # Contexte d'urgence
        if any(
            word in question_lower
            for word in [
                "urgence",
                "emergency",
                "accident",
                "urgent",
                "urgance",
                "urgense",
            ]
        ):
            expanded_keywords.extend(
                [
                    "15",
                    "18",
                    "17",
                    "112",
                    "samu",
                    "pompiers",
                    "police",
                    "secours",
                    "help",
                    "aide",
                ]
            )

        # Contexte de communication
        if any(
            word in question_lower
            for word in [
                "numéro",
                "numero",
                "téléphone",
                "contact",
                "appeler",
                "phone",
                "tel",
            ]
        ):
            expanded_keywords.extend(
                ["tel", "phone", "appel", "joindre", "poste", "extension", "contact"]
            )

        # Contexte de sécurité
        if any(
            word in question_lower
            for word in ["sécurité", "securite", "safety", "security"]
        ):
            expanded_keywords.extend(
                ["responsable", "procedure", "consigne", "évacuation", "alerte"]
            )

        # Contexte d'équipement
        if any(
            word in question_lower
            for word in ["extincteur", "défibrillateur", "equipment", "matériel"]
        ):
            expanded_keywords.extend(["où", "trouve", "located", "situé", "endroit"])

        # Contexte de localisation
        if any(
            word in question_lower
            for word in ["où", "ou", "where", "trouve", "located"]
        ):
            expanded_keywords.extend(["situé", "position", "endroit", "lieu", "place"])

        return list(set(expanded_keywords))  # Supprimer les doublons

    def _find_relevant_passages(
        self, content: str, keywords: List[str], _question: str
    ) -> List[Dict[str, Any]]:
        """
        Trouve les passages pertinents dans un document

        Args:
            content: Contenu du document
            keywords: Mots-clés à rechercher
            question: Question originale

        Returns:
            Liste des passages pertinents avec leur score de pertinence
        """
        passages = []
        sentences = re.split(r"[.!?]+", content)
        sentences = [
            s.strip() for s in sentences if len(s.strip()) > 15
        ]  # Abaissé pour capturer plus de phrases

        for sentence in sentences:
            sentence_lower = sentence.lower()
            relevance_score = 0

            # Score basé sur la présence de mots-clés
            matched_keywords = []
            for keyword in keywords:
                if keyword in sentence_lower:
                    relevance_score += 2
                    matched_keywords.append(keyword)

                    # Bonus si le mot-clé apparaît plusieurs fois
                    relevance_score += sentence_lower.count(keyword) * 0.5

            # Bonus pour les combinaisons de mots-clés importantes
            important_combinations = [
                ("urgence", "numéro"),
                ("urgence", "numero"),
                ("urgence", "téléphone"),
                ("urgence", "contact"),
                ("urgence", "appel"),
                ("urgence", "poste"),
                ("sécurité", "poste"),
                ("sécurité", "responsable"),
                ("sécurité", "chef"),
                ("accident", "procédure"),
                ("accident", "secours"),
                ("accident", "alerte"),
                ("défibrillateur", "localisation"),
                ("défibrillateur", "emplacement"),
                ("extincteur", "localisation"),
                ("extincteur", "emplacement"),
                ("15", "samu"),
                ("18", "pompiers"),
                ("17", "police"),
                ("112", "urgence"),
            ]

            for combo in important_combinations:
                combo_found = True
                for word in combo:
                    # Vérifier si le mot ou ses variantes sont dans la phrase
                    word_variants = [word]
                    if word == "urgence":
                        word_variants.extend(["urgance", "urgense"])
                    elif word == "numéro":
                        word_variants.extend(["numero", "tel", "phone"])
                    elif word == "téléphone":
                        word_variants.extend(["telephone", "phone", "tel"])

                    if not any(variant in sentence_lower for variant in word_variants):
                        combo_found = False
                        break

                if combo_found:
                    relevance_score += 5

            # Bonus pour les patterns spécifiques aux urgences
            emergency_patterns = [
                r"\b(en cas d\'urgence|urgence)\b",
                r"\b(numéro|numero|n°|no)\s*(d\')?urgence\b",
                r"\b(contacter|appeler|joindre)\b",
                r"\b(\d{2,4})\s*(poste|ext|extension)?\b",  # Numéros de téléphone/poste
                r"\b(15|18|17|112)\b",  # Numéros d'urgence
                r"\b(samu|pompiers|police|secours)\b",
                r"\b(chef|responsable|manager)\s*(de)?\s*(sécurité|securite|site|équipe)\b",
            ]

            for pattern in emergency_patterns:
                if re.search(pattern, sentence_lower):
                    relevance_score += 3

            # Bonus pour les phrases qui contiennent des numéros
            if re.search(r"\b\d{2,5}\b", sentence):
                relevance_score += 1

            # Bonus pour les phrases qui commencent par des mots importants
            if any(
                sentence_lower.startswith(word)
                for word in [
                    "urgence",
                    "en cas",
                    "pour",
                    "appeler",
                    "contacter",
                    "numéro",
                ]
            ):
                relevance_score += 1

            # Malus pour les phrases très courtes (sauf si elles contiennent des numéros)
            if len(sentence) < 30 and not re.search(r"\b\d{2,5}\b", sentence):
                relevance_score *= 0.5
            # Malus pour les phrases très longues
            elif len(sentence) > 600:
                relevance_score *= 0.7

            if relevance_score > 0:
                # Trouver le contexte (phrases précédente et suivante)
                sentence_idx = sentences.index(sentence)
                context_parts = []

                if sentence_idx > 0:
                    context_parts.append(sentences[sentence_idx - 1])
                if sentence_idx < len(sentences) - 1:
                    context_parts.append(sentences[sentence_idx + 1])

                context = " [...] ".join(context_parts)

                passages.append(
                    {
                        "passage": sentence,
                        "context": context,
                        "relevance": relevance_score,
                        "matched_keywords": matched_keywords,
                    }
                )

        return passages

    def _generate_general_document_response(
        self, question: str, stored_docs: Dict[str, Any]
    ) -> str:
        """
        Génère une réponse générale quand aucune correspondance spécifique n'est trouvée

        Args:
            question: Question posée
            stored_docs: Documents stockés

        Returns:
            Réponse générale
        """
        doc_names = list(stored_docs.keys())

        # Analyse de la question pour donner des suggestions plus pertinentes
        question_lower = question.lower()

        if len(doc_names) == 1:
            doc_name = doc_names[0]
            response = f"Je n'ai pas trouvé d'information directe sur '{question}' dans le document \"{doc_name}\". "
        else:
            response = f"Je n'ai pas trouvé d'information directe sur '{question}' dans les {len(doc_names)} documents analysés. "

        # Suggestions spécifiques selon le type de question
        suggestions = []

        if any(
            word in question_lower
            for word in ["urgence", "numéro", "téléphone", "contact", "appeler"]
        ):
            suggestions.append(
                "• Cherchez des termes comme 'contact', 'téléphone', 'urgence', 'poste', 'responsable'"
            )
            suggestions.append(
                "• Recherchez des numéros (15, 18, 17, 112, ou numéros internes)"
            )
            suggestions.append(
                "• Demandez-moi 'procédure d'urgence' ou 'contacts importants'"
            )

        if any(
            word in question_lower for word in ["sécurité", "accident", "procédure"]
        ):
            suggestions.append(
                "• Recherchez 'sécurité', 'procédure', 'consignes', 'en cas d'urgence'"
            )
            suggestions.append(
                "• Demandez-moi 'mesures de sécurité' ou 'que faire en cas d'accident'"
            )

        if any(word in question_lower for word in ["responsable", "chef", "manager"]):
            suggestions.append(
                "• Cherchez 'responsable', 'chef', 'manager', 'superviseur'"
            )
            suggestions.append("• Demandez-moi 'qui contacter' ou 'organigramme'")

        if not suggestions:
            suggestions = [
                "• Reformulez votre question avec d'autres termes",
                "• Demandez-moi un résumé général du document",
                "• Posez une question plus précise sur un aspect particulier",
                "• Demandez-moi de rechercher un mot-clé spécifique",
            ]

        response += "Voici comment je peux vous aider :\n\n"
        response += "\n".join(suggestions)

        # Ajouter quelques mots-clés du document pour aider l'utilisateur
        first_doc = list(stored_docs.values())[0]
        content = first_doc["content"]

        # Extraire des mots-clés pertinents du document
        words = re.findall(r"\b\w{4,}\b", content.lower())

        # Filtrer les mots-clés pertinents
        relevant_words = []
        important_categories = [
            "urgence",
            "sécurité",
            "accident",
            "procédure",
            "responsable",
            "chef",
            "téléphone",
            "contact",
            "poste",
            "numéro",
            "appeler",
            "joindre",
            "défibrillateur",
            "extincteur",
            "secours",
            "évacuation",
            "alerte",
            "travail",
            "bureau",
            "site",
            "équipe",
            "service",
            "département",
        ]

        word_freq = {}
        for word in words:
            if word in important_categories or any(
                cat in word for cat in important_categories
            ):
                word_freq[word] = word_freq.get(word, 0) + 1

        if word_freq:
            sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
            relevant_words = [word for word, freq in sorted_words[:8] if freq > 1]

        if relevant_words:
            response += f"\n\n📋 Mots-clés présents dans le document : {', '.join(relevant_words[:6])}"

        # Encourager l'utilisateur à essayer différentes formulations
        response += "\n\n💡 Astuce : Essayez des questions comme 'Quel est le numéro d'urgence ?' ou 'Comment contacter la sécurité ?'"

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

    # =============== MÉTHODES ULTRA 1M TOKENS ===============

    def add_document_to_context(
        self, document_content: str, document_name: str = ""
    ) -> Dict[str, Any]:
        """
        Ajoute un document au contexte 1M tokens
        """
        if not self.ultra_mode:
            # Mode standard - utiliser la mémoire classique
            return self._add_document_to_classic_memory(document_content, document_name)

        try:
            # Mode Ultra - utiliser le gestionnaire 1M tokens
            result = self.context_manager.add_document(
                content=document_content, document_name=document_name
            )

            # Stocker aussi dans la mémoire classique pour compatibilité
            self._add_document_to_classic_memory(document_content, document_name)

            return {
                "success": True,
                "message": f"Document '{document_name}' ajouté au contexte Ultra",
                "chunks_created": result.get("chunks_created", 0),
                "context_size": self.context_manager.current_tokens,
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Erreur lors de l'ajout du document: {str(e)}",
            }

    def _add_document_to_classic_memory(
        self, content: str, doc_name: str
    ) -> Dict[str, Any]:
        """Ajoute un document à la mémoire classique"""
        try:
            word_count = len(content.split())

            # Stocker le document avec métadonnées
            self.conversation_memory.stored_documents[doc_name] = {
                "content": content,
                "timestamp": time.time(),
                "word_count": word_count,
                "order_index": len(self.conversation_memory.document_order),
            }

            # Mettre à jour l'ordre chronologique
            if doc_name not in self.conversation_memory.document_order:
                self.conversation_memory.document_order.append(doc_name)

            return {
                "success": True,
                "message": f"Document '{doc_name}' stocké en mémoire classique",
                "word_count": word_count,
            }
        except Exception as e:
            return {"success": False, "message": f"Erreur mémoire classique: {str(e)}"}

    def add_file_to_context(self, file_path: str) -> Dict[str, Any]:
        """Ajoute un fichier au contexte en utilisant les processeurs avancés"""
        try:
            file_name = os.path.basename(file_path)
            file_ext = os.path.splitext(file_path)[1].lower()

            # Traitement selon le type de fichier
            content = ""
            processor_used = "basic"

            if file_ext == ".pdf" and self.pdf_processor:
                try:
                    result = self.pdf_processor.read_pdf(file_path)
                    if result.get("error"):
                        print(f"⚠️ Erreur PDF: {result['error']}")
                        content = ""
                    elif result.get("success"):
                        # Structure: result["content"]["text"]
                        content_data = result.get("content", {})
                        content = content_data.get("text", "")
                        pages = content_data.get("page_count", 0)
                        processor_used = "PDF"
                        print(
                            f"📄 [PDF] Traitement PDF: {pages} pages, {len(content)} caractères"
                        )
                    else:
                        # Structure: result["text"] (fallback)
                        content = result.get("text", "")
                        pages = result.get("page_count", 0)
                        processor_used = "PDF"
                        print(
                            f"📄 [PDF] Traitement PDF: {pages} pages, {len(content)} caractères"
                        )
                except Exception as e:
                    print(f"⚠️ Erreur processeur PDF: {e}")
                    # Fallback vers lecture basique
                    try:
                        with open(file_path, "rb") as f:
                            content = f.read().decode("utf-8", errors="ignore")
                    except Exception:
                        content = ""

            elif file_ext in [".docx", ".doc"] and self.docx_processor:
                try:
                    result = self.docx_processor.read_docx(file_path)
                    content = result.get("text", "")
                    processor_used = "DOCX"
                    print(
                        f"📄 [DOCX] Traitement DOCX: {result.get('paragraphs', 0)} paragraphes"
                    )
                except Exception as e:
                    print(f"⚠️ Erreur processeur DOCX: {e}")
                    # Fallback vers lecture basique
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.read()

            elif (
                file_ext in [".py", ".js", ".html", ".css", ".cpp", ".java"]
                and self.code_processor
            ):
                try:
                    result = self.code_processor.analyze_code(file_path)
                    content = result.get("content", "")
                    processor_used = "Code"
                    print(
                        f"📄 [CODE] Traitement code: {result.get('language', 'unknown')}"
                    )
                except Exception as e:
                    print(f"⚠️ Erreur processeur Code: {e}")
                    # Fallback vers lecture basique
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.read()
            else:
                # Lecture basique
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.read()
                    processor_used = "basic"
                except UnicodeDecodeError:
                    with open(file_path, "r", encoding="latin-1") as f:
                        content = f.read()
                    processor_used = "basic-latin1"

            if not content:
                return {"success": False, "message": "Contenu vide après traitement"}

            # Ajouter au contexte
            result = self.add_document_to_context(content, file_name)
            result.update(
                {
                    "processor_used": processor_used,
                    "analysis_info": f"Pages: N/A, Caractères: {len(content)}",
                }
            )

            return result

        except Exception as e:
            return {
                "success": False,
                "message": f"Erreur lors du traitement du fichier: {str(e)}",
            }

    def search_in_context(self, query: str) -> str:
        """
        🔍 Recherche intelligente dans le contexte 1M tokens
        Améliore la recherche pour trouver les passages les plus pertinents
        """
        if not self.ultra_mode:
            return self._search_in_classic_memory(query)

        try:
            print(f"🔍 [ULTRA] Recherche intelligente pour: '{query[:60]}...'")

            # 🎯 ÉTAPE 1: Extraire les mots-clés de la question
            keywords = self._extract_question_keywords(query)
            print(f"🔑 [ULTRA] Mots-clés extraits: {keywords}")

            # 🎯 ÉTAPE 2: Recherche avec mots-clés spécifiques
            enhanced_query = " ".join(keywords)  # Requête améliorée avec les mots-clés

            # Recherche dans le contexte Ultra avec plus de chunks pour avoir plus de choix
            context = self.context_manager.get_relevant_context(
                enhanced_query, max_chunks=10
            )

            if not context or len(context.strip()) < 100:
                print(
                    "⚠️ [ULTRA] Contexte insuffisant, recherche avec requête originale..."
                )
                # Fallback avec la requête originale
                context = self.context_manager.get_relevant_context(query, max_chunks=8)

            if context and len(context.strip()) > 50:
                print(f"✅ [ULTRA] Contexte trouvé: {len(context)} caractères")

                # 🎯 ÉTAPE 3: Post-traitement pour extraire les passages les plus pertinents
                refined_context = self._refine_ultra_context(context, query, keywords)

                # ✅ NOUVELLE LOGIQUE : Utiliser le contenu raffiné s'il est pertinent, même s'il est court
                if (
                    refined_context and len(refined_context.strip()) > 100
                ):  # Au moins 100 caractères de contenu
                    print(
                        f"🎯 [ULTRA] Contexte raffiné utilisé: {len(refined_context)} caractères"
                    )
                    return refined_context
                elif refined_context and len(refined_context.strip()) > 50:
                    print(
                        f"🎯 [ULTRA] Contexte raffiné court mais utilisé: {len(refined_context)} caractères"
                    )
                    return refined_context
                else:
                    print(
                        f"🔄 [ULTRA] Raffinement insuffisant ({len(refined_context) if refined_context else 0} chars), utilisation contexte complet"
                    )
                    return context
            else:
                print("⚠️ [ULTRA] Contexte vide ou insuffisant")

            # Fallback vers mémoire classique
            return self._search_in_classic_memory(query)

        except Exception as e:
            print(f"❌ [ULTRA] Erreur recherche: {e}")
            return self._search_in_classic_memory(query)

    def _refine_ultra_context(self, context: str, query: str, keywords: list) -> str:
        """
        🎯 Raffine le contexte Ultra pour extraire les passages les plus pertinents
        """
        try:
            print(f"🔍 [REFINE] Début du raffinement: {len(context)} caractères")

            # 🎯 ÉTAPE 1: Diviser le contenu de manière plus agressive
            # Essayer plusieurs méthodes de division
            sections = []

            # Méthode 1: Double saut de ligne
            if "\n\n" in context:
                sections = context.split("\n\n")
                print(f"📄 [REFINE] Division par double saut: {len(sections)} sections")

            # Méthode 2: Saut de ligne simple si peu de sections
            if len(sections) < 5:
                sections = context.split("\n")
                sections = [s.strip() for s in sections if len(s.strip()) > 20]
                print(f"📄 [REFINE] Division par saut simple: {len(sections)} sections")

            # Méthode 3: Division par phrases longues si toujours peu de sections
            if len(sections) < 5:

                # Diviser par points, mais garder les phrases longues ensemble
                sentences = re.split(r"[.!?]+", context)
                sections = []
                current_section = ""

                for sentence in sentences:
                    sentence = sentence.strip()
                    if len(sentence) < 10:  # Ignorer les phrases trop courtes
                        continue

                    if (
                        len(current_section) + len(sentence) > 300
                    ):  # ~300 caractères par section
                        if current_section:
                            sections.append(current_section.strip())
                        current_section = sentence
                    else:
                        current_section += (
                            ". " + sentence if current_section else sentence
                        )

                if current_section:
                    sections.append(current_section.strip())

                print(f"📄 [REFINE] Division par phrases: {len(sections)} sections")

            # 🎯 ÉTAPE 2: Scorer chaque section
            scored_sections = []
            query_lower = query.lower()

            for i, section in enumerate(sections):
                if len(section.strip()) < 30:  # Ignorer les sections trop courtes
                    continue

                section_lower = section.lower()
                score = 0

                # Score basé sur les mots-clés de la question
                for keyword in keywords:
                    if keyword in section_lower:
                        score += 3  # Score plus élevé pour les mots-clés directs
                        # Bonus si le mot-clé apparaît plusieurs fois
                        score += section_lower.count(keyword) * 1.5

                # Score basé sur des mots-clés spécifiques selon le type de question
                if "difficulté" in query_lower or "problème" in query_lower:
                    difficulty_words = [
                        "difficulté",
                        "problème",
                        "challenge",
                        "obstacle",
                        "compliqué",
                        "difficile",
                        "complexe",
                    ]
                    for word in difficulty_words:
                        if word in section_lower:
                            score += 5  # Score très élevé pour les questions sur les difficultés

                elif "date" in query_lower or "période" in query_lower:
                    date_words = [
                        "date",
                        "période",
                        "juin",
                        "juillet",
                        "août",
                        "2025",
                        "début",
                        "fin",
                        "durée",
                    ]
                    for word in date_words:
                        if word in section_lower:
                            score += 5

                elif "lieu" in query_lower or "endroit" in query_lower:
                    location_words = [
                        "lieu",
                        "endroit",
                        "pierre fabre",
                        "lavaur",
                        "cauquillous",
                        "adresse",
                        "localisation",
                    ]
                    for word in location_words:
                        if word in section_lower:
                            score += 5

                elif "mission" in query_lower or "tâche" in query_lower:
                    mission_words = [
                        "mission",
                        "tâche",
                        "responsabilité",
                        "rôle",
                        "travail",
                        "fonction",
                        "activité",
                    ]
                    for word in mission_words:
                        if word in section_lower:
                            score += 5

                # Bonus pour les éléments de structure (listes, titres, etc.)
                if any(
                    char in section
                    for char in [":", "-", "•", "►", "→", "1.", "2.", "3."]
                ):
                    score += 2

                # Malus pour les sections qui semblent être de la table des matières
                if "table des matières" in section_lower or section.count(".....") > 2:
                    score -= 10

                print(f"📊 [REFINE] Section {i}: {score} points - {section[:60]}...")

                if score > 0:
                    scored_sections.append((score, section.strip()))

            # 🎯 ÉTAPE 3: Sélectionner les meilleures sections
            if scored_sections:
                # Trier par score décroissant
                scored_sections.sort(key=lambda x: x[0], reverse=True)

                print(f"🏆 [REFINE] Top scores: {[s[0] for s in scored_sections[:5]]}")

                # Prendre les sections avec un score significatif
                good_sections = [
                    section[1] for section in scored_sections if section[0] >= 3
                ]

                if good_sections:
                    # Limiter à 3 sections maximum pour éviter trop de texte
                    selected_sections = good_sections[:3]
                    refined_content = "\n\n---\n\n".join(selected_sections)

                    print(
                        f"✅ [REFINE] {len(selected_sections)} sections sélectionnées, {len(refined_content)} caractères"
                    )
                    return refined_content
                else:
                    print("⚠️ [REFINE] Aucune section avec score suffisant")

            # 🔄 FALLBACK: Si aucune section pertinente, retourner un échantillon intelligent
            print("🔄 [REFINE] Fallback - recherche par mots-clés simples")
            return self._simple_keyword_search(context, keywords)

        except Exception as e:
            print(f"❌ [REFINE] Erreur: {e}")
            return self._simple_keyword_search(context, keywords)

    def _simple_keyword_search(self, content: str, keywords: list) -> str:
        """Recherche simple par mots-clés si le raffinement avancé échoue"""
        try:
            lines = content.split("\n")
            relevant_lines = []

            for line in lines:
                line_lower = line.lower()
                if (
                    any(keyword in line_lower for keyword in keywords)
                    and len(line.strip()) > 20
                ):
                    relevant_lines.append(line.strip())

            if relevant_lines:
                # Prendre les 5 premières lignes pertinentes
                result = "\n".join(relevant_lines[:5])
                print(f"🔍 [SIMPLE] {len(relevant_lines)} lignes pertinentes trouvées")
                return result
            else:
                # Ultime fallback: premiers 800 caractères
                print("🔄 [SIMPLE] Aucune ligne pertinente, retour début document")
                return content[:800]

        except Exception as e:
            print(f"❌ [SIMPLE] Erreur: {e}")
            return content[:800]

    def _search_in_classic_memory(self, query: str) -> str:
        """Recherche dans la mémoire classique"""
        try:
            query_lower = query.lower()
            found_docs = []

            for doc_data in self.conversation_memory.stored_documents.items():
                content = doc_data.get("content", "")
                if any(word in content.lower() for word in query_lower.split()):
                    found_docs.append(content)

            return "\n\n".join(found_docs) if found_docs else ""

        except Exception as e:
            print(f"⚠️ Erreur recherche classique: {e}")
            return ""

    def get_context_stats(self) -> Dict[str, Any]:
        """Obtient les statistiques du contexte"""
        if self.ultra_mode and self.context_manager:
            stats = self.context_manager.get_stats()
            # Ajouter les informations manquantes pour compatibilité
            stats.update(
                {
                    "context_size": self.context_manager.current_tokens,
                    "max_context_length": self.context_manager.max_tokens,
                    "utilization_percent": round(
                        (
                            self.context_manager.current_tokens
                            / self.context_manager.max_tokens
                        )
                        * 100,
                        2,
                    ),
                }
            )
            return stats
        else:
            # Stats de la mémoire classique
            doc_count = len(self.conversation_memory.stored_documents)
            total_words = sum(
                doc.get("word_count", 0)
                for doc in self.conversation_memory.stored_documents.values()
            )

            return {
                "mode": "classic",
                "documents": doc_count,
                "total_words": total_words,
                "context_size": total_words * 1.3,  # Estimation approximative en tokens
                "max_context_length": 100000,  # Limite approximative mode classique
                "utilization_percent": min(100, (total_words * 1.3 / 100000) * 100),
            }

    async def _handle_advanced_code_generation(self, user_input: str) -> str:
        """
        🚀 NOUVELLE VERSION - Génération de code avancée avec SmartCodeSearcher
        Rivalise avec ChatGPT/Claude grâce à:
        - Recherche web intelligente (DuckDuckGo)
        - Analyse sémantique avec embeddings
        - Ranking intelligent des solutions
        - Cache avec similarité
        """
        try:
            # 1. Analyse de la demande
            language = self._detect_programming_language(user_input)
            complexity = self._analyze_complexity(user_input)
            requirements = self._extract_requirements(user_input)

            print(f"🚀 Génération de code SMART: {language}, complexité: {complexity}")

            # 2. 🆕 Utiliser SmartCodeSearcher (nouveau système intelligent)
            try:
                print("🔍 Recherche avec SmartCodeSearcher...")
                smart_snippets = await smart_code_searcher.search_code(
                    user_input, language
                )

                if smart_snippets and len(smart_snippets) > 0:
                    # Prendre la meilleure solution
                    best_snippet = smart_snippets[0]

                    print(
                        f"✅ Meilleure solution trouvée: Score={best_snippet.final_score:.2f}, Source={best_snippet.source_name}"
                    )

                    # Utiliser le code brut directement, sans modification
                    code = best_snippet.code.strip()

                    # Réponse naturelle avec le code complet
                    response = f"""Voici le code complet :

```{language}
{code}
```

_(Source: {best_snippet.source_name})_"""

                    # Enregistrer dans la mémoire
                    self.conversation_memory.add_conversation(
                        user_input,
                        response,
                        "code_generation",
                        1.0,
                        {
                            "language": language,
                            "complexity": complexity,
                            "source": best_snippet.source_name,
                            "score": best_snippet.final_score,
                        },
                    )

                    return response
                else:
                    print("⚠️ SmartCodeSearcher n'a pas trouvé de solutions")

            except Exception as e:
                print(f"⚠️ Erreur SmartCodeSearcher: {e}")

                traceback.print_exc()

            # 3. Fallback sur l'ancien système
            print("📦 Fallback sur l'ancien système de recherche...")
            web_solutions = []
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        future = executor.submit(
                            asyncio.run,
                            self._search_web_solutions(user_input, language),
                        )
                        web_solutions = future.result(timeout=10)
                else:
                    web_solutions = loop.run_until_complete(
                        self._search_web_solutions(user_input, language)
                    )
            except RuntimeError:
                web_solutions = asyncio.run(
                    self._search_web_solutions(user_input, language)
                )
            except Exception as e:
                print(f"⚠️ Recherche web (fallback) échouée: {e}")

            # 4. Génération hybride ou locale
            if web_solutions:
                best_solution = web_solutions[0]
                enhanced_code = self._create_enhanced_solution(
                    best_solution, user_input, language, requirements
                )
                response = f"💻 Code généré avec recherche web:\n```{language}\n{enhanced_code}\n```\n"
            else:
                # Dernière option: génération locale
                local_code = await self._generate_local_advanced_code(
                    user_input, language, requirements
                )
                response = (
                    f"📝 Code généré localement:\n```{language}\n{local_code}\n```\n"
                )

            # Enregistrer dans la mémoire
            self.conversation_memory.add_conversation(
                user_input,
                response,
                "code_generation",
                0.8,
                {"language": language, "complexity": complexity, "method": "fallback"},
            )

            return response

        except Exception as e:
            error_msg = f"❌ Erreur lors de la génération de code: {str(e)}"
            print(error_msg)

            traceback.print_exc()
            return error_msg

    def _enhance_smart_snippet(self, snippet, query: str, requirements: list) -> str:
        """Améliore un snippet du SmartCodeSearcher avec commentaires et adaptations"""
        code = snippet.code.strip()

        # En-tête descriptif
        header = f'''"""
{snippet.title}

Solution pour: {query}
Source: {snippet.source_name}
Qualité: {snippet.quality_score:.1f}/10 | Pertinence: {snippet.relevance_score:.1f}/10
"""

'''

        enhanced_code = header + code

        # Ajouter des commentaires selon les requirements
        if "error_handling" in requirements and snippet.language == "python":
            enhanced_code += (
                "\n\n# 💡 Conseil: Ajoutez une gestion d'erreurs avec try/except"
            )

        if "examples" in requirements:
            enhanced_code += "\n\n# 💡 Exemple d'utilisation ci-dessus"

        if "documentation" in requirements:
            enhanced_code += (
                "\n\n# 📝 Ajoutez des docstrings pour documenter vos fonctions"
            )

        return enhanced_code

    async def _search_web_solutions(self, query: str, language: str):
        """Recherche asynchrone de solutions web"""
        return await self.web_code_searcher.search_all_sources(
            query, language, max_results=3
        )

    def _detect_programming_language(self, user_input: str) -> str:
        """Détecte le langage de programmation demandé"""
        user_lower = user_input.lower()

        language_keywords = {
            "python": ["python", "py", "django", "flask", "pandas", "numpy"],
            "javascript": ["javascript", "js", "node", "react", "vue", "angular"],
            "html": ["html", "page web", "site web", "webpage"],
            "css": ["css", "style", "stylesheet", "bootstrap"],
            "java": ["java", "spring", "maven"],
            "cpp": ["c++", "cpp", "c plus plus"],
            "c": ["langage c", "programmation c"],
            "sql": ["sql", "mysql", "database", "base de données"],
            "php": ["php", "laravel", "wordpress"],
            "go": ["golang", "go lang"],
            "rust": ["rust", "cargo"],
            "swift": ["swift", "ios"],
            "kotlin": ["kotlin", "android"],
        }

        for lang, keywords in language_keywords.items():
            if any(keyword in user_lower for keyword in keywords):
                return lang

        return "python"  # Défaut

    def _analyze_complexity(self, user_input: str) -> str:
        """Analyse la complexité de la demande"""
        user_lower = user_input.lower()

        complex_keywords = [
            "api",
            "base de données",
            "algorithme",
            "optimisé",
            "performant",
            "architecture",
            "design pattern",
            "async",
            "threading",
        ]
        intermediate_keywords = [
            "classe",
            "fonction",
            "boucle",
            "condition",
            "fichier",
            "json",
            "csv",
        ]

        if any(keyword in user_lower for keyword in complex_keywords):
            return "avancé"
        elif any(keyword in user_lower for keyword in intermediate_keywords):
            return "intermédiaire"
        else:
            return "débutant"

    def _extract_requirements(self, user_input: str) -> list:
        """Extrait les exigences spécifiques de la demande"""
        requirements = []
        user_lower = user_input.lower()

        # Exigences communes
        if "gestion erreur" in user_lower or "try except" in user_lower:
            requirements.append("error_handling")
        if "commentaire" in user_lower or "documentation" in user_lower:
            requirements.append("documentation")
        if "test" in user_lower or "exemple" in user_lower:
            requirements.append("examples")
        if "optimisé" in user_lower or "performance" in user_lower:
            requirements.append("optimization")
        if "sécurisé" in user_lower or "sécurité" in user_lower:
            requirements.append("security")

        return requirements

    def _create_enhanced_solution(
        self, web_solution, query: str, language: str, requirements: list
    ) -> str:
        """Crée une solution améliorée basée sur une solution web"""
        base_code = web_solution.code

        # Améliorations basées sur les exigences
        enhanced_code = f'"""\n{web_solution.title}\nSolution adaptée pour: {query}\nSource: {web_solution.source_name}\n"""\n\n{base_code}'

        # Ajout de gestion d'erreurs
        if "error_handling" in requirements and language == "python":
            enhanced_code += '\n\n# Gestion d\'erreurs recommandée:\n# try:\n#     result = votre_fonction()\n# except Exception as e:\n#     print(f"Erreur: {e}")'

        # Ajout d'exemples
        if "examples" in requirements:
            enhanced_code += '\n\n# Exemple d\'utilisation:\nif __name__ == "__main__":\n    # Testez votre code ici\n    pass'

        return enhanced_code

    async def _generate_local_advanced_code(
        self, query: str, language: str, requirements: list
    ) -> str:
        """Génère du code avancé localement avec notre AdvancedCodeGenerator"""
        try:
            # Utiliser notre générateur corrigé avec la bonne signature
            result = await self.code_generator.generate_code(
                query, language=language, requirements=requirements
            )

            if result.get("success"):
                return result.get("code", "# Aucun code généré")
            else:
                # Fallback en cas d'échec
                return f"# Erreur lors de la génération: {result.get('error', 'Erreur inconnue')}"

        except Exception as e:
            return f"# Erreur lors de la génération: {str(e)}"


# Alias pour compatibilité avec l'ancien nom
AdvancedLocalAI = CustomAIModel
