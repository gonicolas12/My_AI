"""
Modèle IA personnalisé local - Architecture modulaire
Intègre tous les modules pour une IA 100% locale avec mémoire de conversation
"""

import re
import json
import time
import random
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime

from .base_ai import BaseAI
from .linguistic_patterns import LinguisticPatterns
from .knowledge_base import KnowledgeBase
from .generators import CodeGenerator
from .reasoning_engine import ReasoningEngine
from .conversation_memory import ConversationMemory
from .internet_search import InternetSearchEngine


class CustomAIModel(BaseAI):
    """Modèle IA personnalisé avec architecture modulaire et mémoire persistante"""
    
    def __init__(self, conversation_memory: ConversationMemory = None):
        super().__init__()
        self.name = "Assistant IA Local"
        self.version = "3.1.0"
        
        # Modules spécialisés
        self.linguistic_patterns = LinguisticPatterns()
        self.knowledge_base = KnowledgeBase()
        self.code_generator = CodeGenerator()
        self.reasoning_engine = ReasoningEngine()
        self.conversation_memory = conversation_memory or ConversationMemory()
        self.internet_search = InternetSearchEngine()
        
        # Configuration
        self.confidence_threshold = 0.3
        self.max_response_length = 2000

        # État de la session
        self.session_context = {
            "documents_processed": [],
            "code_files_processed": [],
            "last_document_type": None,
            "current_document": None
        }
        
        # Suivi des blagues pour éviter les répétitions
        self.used_jokes = set()  # Index des blagues déjà utilisées
        self.jokes_reset_threshold = 0.8  # Reset quand 80% des blagues sont utilisées
        
        # Réponses personnalisées pour l'identité
        self.identity_responses = {
            "basic": [
                "Je suis votre assistant IA local ! Je m'appelle Assistant IA Local et je suis conçu pour vous aider avec la programmation, les questions techniques, et bien plus encore.",
                "Bonjour ! Je suis un assistant IA qui fonctionne entièrement en local sur votre machine. Je peux vous aider avec le code, répondre à vos questions, et discuter avec vous.",
                "Salut ! Moi c'est Assistant IA Local. Je suis votre compagnon virtuel pour la programmation et les discussions techniques. Je tourne uniquement en local, pas besoin d'internet !",
                "Je suis votre assistant personnel ! Un modèle IA local qui peut coder, expliquer, et discuter avec vous. J'apprends de nos conversations pour mieux vous comprendre."
            ],
            "detailed": [
                "Je suis Assistant IA Local, version 3.1.0 Je suis un modèle d'intelligence artificielle conçu pour fonctionner entièrement en local, sans dépendance externe. Je peux générer du code, expliquer des concepts, et avoir des conversations naturelles avec vous.",
                "Mon nom est Assistant IA Local. Je suis une IA modulaire avec plusieurs spécialisations : génération de code, analyse linguistique, base de connaissances, et raisonnement. Je garde en mémoire nos conversations pour mieux vous comprendre.",
                "Je suis votre assistant IA personnel ! J'ai été conçu avec une architecture modulaire incluant la génération de code, l'analyse linguistique, une base de connaissances, et un moteur de raisonnement. Tout fonctionne en local sur votre machine."
            ],
            "casual": [
                "Salut ! Moi c'est Assistant IA Local, ton compagnon virtuel pour coder et discuter. Je suis là pour t'aider avec tout ce que tu veux !",
                "Hey ! Je suis ton assistant IA local. Je peux coder, expliquer des trucs, et juste discuter avec toi. J'apprends de nos conversations pour être plus utile.",
                "Coucou ! Je suis Assistant IA Local, ta nouvelle IA de compagnie. On peut coder ensemble, parler de tout et n'importe quoi. Je suis là pour toi !"
            ]
        }
        
        # Réponses sur les capacités
        self.capabilities_responses = {
            "basic": [
                "Je peux vous aider avec la programmation (Python, JavaScript, HTML/CSS...), expliquer des concepts techniques, générer du code, et avoir des conversations naturelles avec vous.",
                "Mes capacités incluent : génération de code, explication de concepts, analyse de texte, raisonnement logique, et mémorisation de nos conversations pour mieux vous comprendre.",
                "Je suis capable de coder dans plusieurs langages, d'expliquer des concepts techniques, de répondre à vos questions, et de maintenir une conversation fluide en me souvenant de nos échanges."
            ],
            "detailed": [
                "Mes capacités principales sont :\n- Génération de code (Python, JavaScript, HTML/CSS, etc.)\n- Explication de concepts techniques\n- Analyse linguistique et détection d'intentions\n- Raisonnement logique et résolution de problèmes\n- Mémoire de conversation persistante\n- Fonctionnement 100% local sans dépendances externes",
                "Je possède plusieurs modules spécialisés :\n• CodeGenerator : pour créer du code dans différents langages\n• KnowledgeBase : pour stocker et récupérer des connaissances\n• LinguisticPatterns : pour comprendre vos messages\n• ReasoningEngine : pour le raisonnement et la logique\n• ConversationMemory : pour mémoriser nos échanges\n\nTout fonctionne en local !"
            ]
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
        
        # 🚀 NOUVELLES FONCTIONNALITÉS "WOW FACTOR" - INTELLIGENCE AVANCÉE
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
                "Voici une approche plus élégante et maintenable."
            ],
            "advanced_patterns": [
                "Basé sur le contexte, cette approche serait plus adaptée.",
                "En considérant votre historique, cette solution conviendrait mieux.",
                "Cette variante pourrait être plus puissante pour votre cas."
            ]
        }
        
        print(f"✅ {self.name} v{self.version} initialisé avec succès")
        print(f"🧠 Modules chargés : Linguistique, Base de connaissances, Génération de code, Raisonnement, Mémoire, Recherche Internet")
        print(f"💾 Mémoire de conversation activée")
        print(f"🌐 Recherche internet disponible")
    
    def generate_response(self, user_input: str, context: Optional[Dict[str, Any]] = None) -> str:
        """Génère une réponse avec gestion améliorée des documents"""
        try:
            # Vérification spéciale pour résumés simples
            user_lower = user_input.lower().strip()
            if user_lower in ["résume", "resume", "résumé"] and self._has_documents_in_memory():
                # Forcer l'intention document_question
                return self._answer_document_question(user_input, self.conversation_memory.get_document_content())
            
            # Traitement spécialisé pour les résumés de documents
            if self._is_document_processing_request(user_input):
                return self._handle_document_processing(user_input)
            
            # Mise à jour du contexte de session
            self._update_session_context()
            
            # Détection d'intention avec contexte amélioré
            intent_context = {
                "code_file_processed": len(self.session_context["code_files_processed"]) > 0,
                "document_processed": len(self.session_context["documents_processed"]) > 0,
                "has_documents": len(self.conversation_memory.get_document_content()) > 0
            }
            
            intent_scores = self.linguistic_patterns.detect_intent(user_input, intent_context)
            
            # Sélection de l'intention primaire avec logique améliorée
            primary_intent, confidence = self._select_primary_intent(intent_scores, user_input)
            
            print(f"DEBUG: Intent détecté: {primary_intent} (confiance: {confidence:.2f})")
            
            # Récupération du contexte conversationnel
            conversation_context = self.conversation_memory.get_context_for_response(primary_intent)
            
            # D'abord vérifier s'il y a des questions similaires
            similar_question = self.conversation_memory.has_similar_recent_question(user_input)
            
            # Puis appeler avec tous les paramètres requis
            response = self._generate_contextual_response(
                user_input, primary_intent, confidence, conversation_context, similar_question
            )
            
            # Enregistrement dans la mémoire
            self.conversation_memory.add_conversation(
                user_input, response, primary_intent, confidence, conversation_context
            )
            
            return response
            
        except Exception as e:
            error_response = f"Désolé, j'ai rencontré un problème : {str(e)}"
            self.conversation_memory.add_conversation(user_input, error_response, "error", 0.0, {"error": str(e)})
            return error_response
        
    def _is_document_processing_request(self, user_input: str) -> bool:
        """Détecte si c'est une demande de traitement de document système"""
        return (user_input.lower().startswith("please summarize this pdf content") or 
                user_input.lower().startswith("please analyze this document content"))
    
    def _handle_document_processing(self, user_input: str) -> str:
        """Traite les demandes de résumé de documents avec mémorisation immédiate"""
        print(f"🔍 Traitement de document détecté")
        
        # Extraire le nom du fichier et le contenu
        filename, content = self._extract_document_info(user_input)
        
        if not content:
            return "Je n'ai pas pu extraire le contenu du document."
        
        # **IMMÉDIATEMENT** stocker dans la mémoire
        self.conversation_memory.store_document_content(filename, content)
        
        # Vérifier que session_context existe avant mise à jour
        if not hasattr(self, 'session_context'):
            self.session_context = {
                "documents_processed": [],
                "code_files_processed": [],
                "last_document_type": None,
                "current_document": None
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
                filename = filename.replace('.pdf', '').replace('.docx', '')
                break
        
        # Extraire le contenu (après les deux points)
        content_start = user_input.find(":\n\n")
        if content_start != -1:
            content = user_input[content_start + 3:].strip()
        else:
            content = ""
        
        return filename, content
    
    def _update_session_context(self):
        """Met à jour le contexte de session avec les documents en mémoire"""
        # Vérifier que session_context existe
        if not hasattr(self, 'session_context'):
            self.session_context = {
                "documents_processed": [],
                "code_files_processed": [],
                "last_document_type": None,
                "current_document": None
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
    
    # 🚀 NOUVELLES MÉTHODES "WOW FACTOR" - INTELLIGENCE AVANCÉE
    
    def _analyze_user_intelligence_level(self, user_input: str, context: Dict[str, Any]) -> str:
        """Analyse le niveau technique de l'utilisateur pour adapter les réponses"""
        # Analyse des mots techniques utilisés
        technical_indicators = [
            "algorithm", "optimization", "pattern", "architecture", "scalability",
            "performance", "async", "concurrency", "paradigm", "abstraction",
            "polymorphism", "inheritance", "encapsulation", "design pattern"
        ]
        
        advanced_indicators = [
            "big o", "complexity", "microservices", "containerization", "orchestration",
            "machine learning", "neural network", "deep learning", "devops", "ci/cd"
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
    
    def _predict_user_needs(self, user_input: str, context: Dict[str, Any]) -> List[str]:
        """Prédit les besoins futurs de l'utilisateur de manière subtile"""
        predictions = []
        user_lower = user_input.lower()
        
        # Prédictions discrètes basées sur le contexte de programmation
        if any(word in user_lower for word in ["function", "fonction", "def "]):
            predictions.extend([
                "Pensez également à ajouter une gestion d'erreurs appropriée.",
                "Les tests unitaires seraient un bon complément à cette fonction."
            ])
        
        if any(word in user_lower for word in ["class", "classe", "object"]):
            predictions.extend([
                "Vous pourriez vouloir définir des méthodes supplémentaires.",
                "Les design patterns pourraient être utiles pour cette structure."
            ])
        
        if any(word in user_lower for word in ["data", "données", "file", "fichier"]):
            predictions.extend([
                "La validation des données sera probablement nécessaire.",
                "Considérez l'optimisation et la mise en cache pour de gros volumes."
            ])
        
        return predictions[:1]  # Seulement une suggestion discrète
    
    def _add_wow_factor_to_response(self, response: str, user_input: str, context: Dict[str, Any]) -> str:
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
    
    def _generate_intelligent_suggestions(self, user_input: str, context: Dict[str, Any]) -> List[str]:
        """Génère des suggestions intelligentes basées sur l'analyse du contexte"""
        suggestions = []
        user_lower = user_input.lower()
        
        # Suggestions basées sur les patterns de code
        if "python" in user_lower:
            suggestions.extend([
                "💡 Voulez-vous que je montre les best practices Python ?",
                "🔧 Souhaitez-vous optimiser ce code pour de meilleures performances ?",
                "📚 Intéressé par les design patterns Python avancés ?"
            ])
        
        if any(word in user_lower for word in ["problem", "problème", "bug", "error"]):
            suggestions.extend([
                "🔍 Voulez-vous que j'analyse les causes possibles ?",
                "🛠️ Souhaitez-vous un plan de debugging structuré ?",
                "⚡ Intéressé par des outils de diagnostic avancés ?"
            ])
        
        return suggestions[:3]  # Limiter à 3 suggestions
    
    def _generate_contextual_response(self, user_input: str, intent: str, confidence: float,
                                    context: Dict[str, Any], similar_question: Optional[Any] = None) -> str:
        """Génère une réponse contextuelle basée sur l'intention et l'historique"""
        
        # Détecter le style de communication de l'utilisateur
        user_style = self._detect_user_style(context)
        context["user_style"] = user_style
        
        # Gestion des questions similaires récentes - LOGIQUE AMÉLIORÉE
        if similar_question and intent not in ["greeting", "thank_you", "goodbye", "how_are_you", "identity_question", "capabilities_question"]:
            time_ago = time.time() - similar_question.timestamp
            if time_ago < 120:  # Réduit à 2 minutes au lieu de 5
                # Éviter la duplication SEULEMENT si la requête est EXACTEMENT la même
                if user_input.lower().strip() == similar_question.user_message.lower().strip():
                    # Réponse directe sans indiquer qu'il s'agit d'une question similaire
                    return similar_question.ai_response
                # Pour les questions similaires mais NON identiques, laisser une réponse normale
                # (ne plus dire "Je viens de répondre à une question similaire...")
        
        
        # Vérifier spécifiquement les questions sur documents
        if intent in ["document_question", "code_question", "unknown"] and self._has_documents_in_memory():
            stored_docs = self.conversation_memory.get_document_content()
        
            # Si c'est clairement une question sur un document, traiter comme telle
            user_lower = user_input.lower()
            if any(word in user_lower for word in ["résume", "resume", "explique", "que dit", "contient", "analyse"]):
                response = self._answer_document_question(user_input, stored_docs)
                # S'assurer que la réponse est une chaîne
                if isinstance(response, dict):
                    return response.get("message", str(response))
                return response

        # Réponses spécialisées par intention
        if intent == "identity_question":
            return self._generate_identity_response(user_input, context)
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
            return self._answer_programming_question(user_input, context)
        elif intent == "internet_search":
            return self._handle_internet_search(user_input, context)
        elif intent == "general_question":
            return self._answer_general_question(user_input, context)
        elif intent == "code_question":
            # Vérifier s'il y a du code en mémoire
            stored_docs = self.conversation_memory.get_document_content()
            code_docs = {name: doc for name, doc in stored_docs.items() 
                        if doc and doc.get("type") == "code"}
            if code_docs:
                return self._answer_code_question(user_input, code_docs)
            else:
                return "Je n'ai pas de code en mémoire à analyser. Traitez d'abord un fichier de code."
        
        # Vérification spéciale pour les demandes de blagues
        user_lower = user_input.lower()
        joke_keywords = [
            "dis moi une blague", "raconte moi une blague", "t'aurais une blague",
            "aurais-tu une blague", "une blague", "raconte une blague",
            "dis une blague", "tu connais une blague", "connais-tu une blague", "fais moi une blague", 
            "une blague stp", "une autre blague"
        ]
        
        if any(keyword in user_lower for keyword in joke_keywords):
            return self._tell_joke()
            
        # Validation finale du type de réponse
        if intent == "document_question":
            stored_docs = self.conversation_memory.get_document_content()
            response = self._answer_document_question(user_input, stored_docs)
            
            # CORRECTION CRITIQUE: Toujours retourner une chaîne
            if isinstance(response, dict):
                if "message" in response:
                    return response["message"]
                else:
                    return str(response)
            return response
        elif intent == "help":
            return self._generate_help_response(user_input, context)
        elif intent == "thank_you":
            return self._generate_thank_you_response(context)
        elif intent == "goodbye":
            return self._generate_goodbye_response(context)
        elif intent == "affirmation":
            response = self._generate_affirmation_response(context)
        elif intent == "negation":
            response = self._generate_negation_response(context)
        else:
            response = self._generate_default_response(user_input, context)
        
        # 🚀 AJOUT DU "WOW FACTOR" À TOUTES LES RÉPONSES
        # Appliquer l'intelligence avancée sauf pour les réponses très courtes
        if len(response) > 50 and intent not in ["greeting", "goodbye", "joke"]:
            response = self._add_wow_factor_to_response(response, user_input, context)
        
        return response
    
    def _generate_identity_response(self, user_input: str, context: Dict[str, Any]) -> str:
        """Réponse d'identité naturelle"""
        responses = [
            "Je suis votre assistant IA local ! Je m'appelle Assistant IA Local et je suis conçu pour vous aider avec la programmation, l'analyse de documents, et bien plus encore.",
            "Salut ! Moi c'est Assistant IA Local. Je suis votre compagnon virtuel pour coder, analyser des documents, et discuter avec vous. Tout fonctionne en local !",
            "Je suis Assistant IA Local, votre assistant personnel qui fonctionne entièrement sur votre machine. Je peux analyser des documents, générer du code, et avoir des conversations naturelles avec vous."
        ]
        
        import random
        return random.choice(responses)
    
    def _generate_capabilities_response(self, user_input: str, context: Dict[str, Any]) -> str:
        """Réponse sur les capacités avec intelligence avancée et factor WOW"""
        
        # CORRECTION : Si c'est "ça va?" ou variantes (mais PAS des questions de capacités), rediriger vers how_are_you
        user_lower = user_input.lower().strip()
        # Vérifier que ce n'est pas une question de capacité avant de rediriger vers how_are_you
        if (any(phrase in user_lower for phrase in ["ça va", "ca va", "sa va", "comment vas tu", "comment ça va"]) and
            not any(phrase in user_lower for phrase in ["à quoi tu sers", "à quoi sert tu", "à quoi sers tu", "à quoi tu sert", 
                                                         "tu sers à quoi", "tu sert à quoi", "tu sers a quoi", "tu sert a quoi"])):
            return self._generate_how_are_you_response(user_input, context)
        
        # 🚀 ANALYSE INTELLIGENTE DE L'UTILISATEUR
        user_level = self._analyze_user_intelligence_level(user_input, context)
        user_style = context.get("user_style", "neutral")
        
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

🔍 **J'analyse tout :**
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
        
        # Variations selon la formulation de la question
        if "à quoi tu sers" in user_lower or "à quoi sert tu" in user_lower:
            base_responses = [
                """🎯 **Mon rôle principal ?** Je suis votre assistant IA polyvalent !

🔍 **J'analyse vos documents** (PDF, Word) pour en extraire l'essentiel
💻 **Je code pour vous** en Python, JavaScript, HTML/CSS... 
🌐 **Je cherche sur internet** et synthétise les informations
💬 **Je discute naturellement** et réponds à vos questions
🧠 **Je résous des problèmes** avec logique et créativité
😄 **Je détends l'atmosphère** avec un peu d'humour quand il faut !

En gros, je suis là pour vous faciliter la vie ! 🚀""",

                """🤖 **À quoi je sers ?** Excellente question !

Je suis votre couteau suisse numérique :
• 📄 **Résumés intelligents** de vos docs
• ⚡ **Code sur mesure** dans plusieurs langages  
• 🔍 **Recherche internet** avec synthèse
• 🗣️ **Conversation naturelle** sur tous sujets
• 🎯 **Résolution de problèmes** étape par étape
• 🎭 **Bonne humeur** garantie !

Tout ça en local, rapide et confidentiel ! 💪""",

                """🎪 **Mon utilité ?** Je suis un assistant tout-terrain !

🎯 **Mes spécialités :**
- Décrypter vos documents complexes
- Pondre du code propre et efficace
- Dénicher des infos sur le web
- Tenir des conversations enrichissantes
- Démêler les problèmes épineux
- Égayer votre journée avec des blagues !

Pensez à moi comme votre collègue virtuel ultra-compétent ! 😎"""
            ]
        elif "que peux tu" in user_lower or "tes capacités" in user_lower:
            base_responses = [
                """💪 **Mes capacités principales :**

🔍 **Analyse documentaire :** PDF, Word, textes - je lis tout !
💻 **Génération de code :** Python, JS, HTML/CSS, API...
🌐 **Recherche web :** Infos actualisées + synthèses
💬 **Intelligence conversationnelle :** Questions, discussions, conseils
🧠 **Raisonnement logique :** Problèmes complexes, déductions
😄 **Compagnon sympa :** Blagues et bonne humeur !

Le tout fonctionnant en local pour votre confidentialité ! 🔒""",

                """🚀 **Voici ce que je sais faire :**

📚 **Documents :** Je lis, résume et analyse vos fichiers
⚙️ **Programmation :** Code sur mesure, toutes demandes
🔎 **Internet :** Recherche + synthèse d'informations
🗨️ **Discussion :** Réponses naturelles, aide personnalisée
🎯 **Logique :** Résolution méthodique de problèmes
🎉 **Détente :** Humour et conversation décontractée

Assistant local, rapide, et toujours disponible ! ⚡"""
            ]
        else:
            # Réponse générale par défaut
            base_responses = [
                """Je peux vous aider avec plusieurs choses :

🔍 **Analyse de documents :** Je peux lire et résumer vos fichiers PDF et Word
💻 **Programmation :** Je génère du code Python, JavaScript, HTML/CSS
🌐 **Recherche internet :** Je peux chercher des informations en ligne et faire des résumés
💬 **Conversation :** Je réponds à vos questions et discute naturellement
🧠 **Raisonnement :** J'analyse des problèmes et propose des solutions
😄 **Humour :** Je peux raconter des blagues pour vous détendre

Tout fonctionne en local sur votre machine - seule la recherche internet nécessite une connexion."""]
        
        # Sélectionner une réponse au hasard pour la variété
        import random
        base_response = random.choice(base_responses)
        
        # Ajouter des informations contextuelles
        if self._has_documents_in_memory():
            docs = list(self.conversation_memory.get_document_content().keys())
            base_response += f"\n\n📚 **Actuellement en mémoire :** {', '.join(docs[:3])}"
            if len(docs) > 3:
                base_response += f" et {len(docs)-3} autre(s)"
        
        return base_response
    
    def _generate_greeting_response(self, user_input: str, context: Dict[str, Any]) -> str:
        """Génère une salutation personnalisée"""
        total_interactions = context.get("total_interactions", 0)
        
        if total_interactions == 0:
            # Première interaction
            greetings = [
                "Bonjour ! Je suis ravi de faire votre connaissance ! 😊",
                "Salut ! Content de vous rencontrer ! Comment puis-je vous aider aujourd'hui ?",
                "Hello ! Bienvenue ! Je suis votre assistant IA local, prêt à vous aider !",
                "Bonjour ! C'est un plaisir de commencer cette conversation avec vous !"
            ]
        else:
            # Retour dans la conversation
            greetings = [
                "Re-bonjour ! Content de vous revoir ! 😊",
                "Salut ! De retour pour une nouvelle question ?",
                "Hello ! Que puis-je faire pour vous cette fois ?",
                "Bonjour ! J'espère que notre dernière conversation vous a été utile !"
            ]
        
        # Adaptation au style de l'utilisateur
        if "wesh" in user_input.lower() or "yo" in user_input.lower() or "wsh" in user_input.lower():
            greetings = [
                "Wesh ! Ça va ? 😄",
                "Yo ! Salut mec ! Quoi de neuf ?",
                "Salut ! Cool de te voir ! Tu veux qu'on fasse quoi ?"
            ]
        elif "bonsoir" in user_input.lower():
            greetings = [
                "Bonsoir ! J'espère que vous passez une bonne soirée !",
                "Bonsoir ! Comment s'est passée votre journée ?",
                "Bonsoir ! Que puis-je faire pour vous ce soir ?"
            ]
        elif "slt" in user_input.lower() or "salut" in user_input.lower():
            greetings = [
                "Salut chef ! Tu vas bien ?",
            ]
        elif "sa va et toi" in user_input.lower() or "ça va et toi" in user_input.lower() or "ça va et toi ?" in user_input.lower() or "sa va et toi ?" in user_input.lower() or "ça va et toi?" in user_input.lower() or "sa va et toi?" in user_input.lower():
            greetings = [
                "Ça va super merci ! Hâte de pouvoir t'aider au mieux !",
            ]
        
        return self._get_random_response(greetings)
    
    def _generate_how_are_you_response(self, user_input: str, context: Dict[str, Any]) -> str:
        """Génère une réponse adaptée selon si c'est une question réciproque ou non"""
        user_lower = user_input.lower().strip()
        
        # Détecter si c'est une question réciproque "ça va et toi ?"
        is_reciprocal = any(phrase in user_lower for phrase in [
            "et toi", "et vous", "ça va et toi", "sa va et toi", "ca va et toi"
        ])
        
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
                    "Ça roule ! J'ai la pêche ! Tu as un projet en tête ?"
                ]
            else:
                responses = [
                    "Très bien, merci ! Je suis entièrement opérationnel. Comment puis-je vous aider ?",
                    "Parfaitement, merci ! Tous mes systèmes fonctionnent optimalement. Que puis-je faire pour vous ?",
                    "Excellent, merci ! Je suis prêt à vous assister. Avez-vous une question ?",
                    "Tout va pour le mieux ! Je suis à votre disposition. En quoi puis-je vous être utile ?",
                    "Très bien merci ! Je fonctionne parfaitement. Quel est votre besoin ?",
                    "Parfait ! Mes modules sont tous opérationnels. Comment puis-je vous aider aujourd'hui ?"
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
                    "Nickel ! Mes circuits sont au top ! Et toi, tu vas bien ?"
                ]
            else:
                responses = [
                    "Très bien, merci de demander ! Je suis parfaitement opérationnel. Et vous, comment allez-vous ?",
                    "Excellent, merci ! Tous mes systèmes fonctionnent optimalement. Comment allez-vous ?",
                    "Parfaitement bien, merci ! Je suis prêt à vous assister. Et vous, ça va ?",
                    "Très bien merci ! Je fonctionne sans aucun problème. Comment vous portez-vous ?",
                    "Tout va pour le mieux ! Mes modules sont tous opérationnels. Et de votre côté ?",
                    "Excellemment bien ! Je suis en pleine forme. Comment allez-vous aujourd'hui ?"
                ]
        
        return self._get_random_response(responses)
        
        base_response = self._get_random_response(responses)
        
        # Ajout d'informations sur la session pour les longues conversations
        session_duration = context.get("session_duration", 0)
   
        return base_response
    
    def _generate_affirm_doing_well_response(self, context: Dict[str, Any]) -> str:
        """Génère une réponse aux affirmations 'ça va' (simple, sans question)"""
        responses = [
            "Super ! Content de savoir que ça va bien ! 😊 Comment puis-je t'aider ?",
            "Parfait ! C'est toujours bien d'aller bien ! En quoi puis-je t'assister ?",
            "Excellent ! Heureux de l'entendre ! Que puis-je faire pour toi ?",
            "Génial ! Ça fait plaisir ! Sur quoi veux-tu que je t'aide ?",
            "Cool ! Et maintenant, que puis-je faire pour toi ?",
            "Nickel ! Tu as une question ou un projet en tête ?",
            "Top ! Dis-moi ce dont tu as besoin !",
            "Parfait ! Je suis là si tu veux discuter de quelque chose !"
        ]
        
        return self._get_random_response(responses)
    
    def _generate_compliment_response(self, user_input: str, context: Dict[str, Any]) -> str:
        """Génère une réponse aux compliments"""
        responses = [
            "Merci beaucoup ! Ça me fait vraiment plaisir ! 😊",
            "C'est très gentil, merci ! J'essaie toujours de faire de mon mieux !",
            "Aww, merci ! Vous êtes sympa ! C'est motivant pour moi !",
            "Merci pour ce compliment ! J'aime beaucoup vous aider !",
            "C'est gentil, merci ! J'espère continuer à vous être utile !"
        ]
        
        # Adaptation au style
        if "cool" in user_input.lower() or "sympa" in user_input.lower():
            responses.extend([
                "Merci, vous êtes cool aussi ! 😄",
                "C'est sympa de dire ça ! Merci !",
                "Cool, merci ! On fait une bonne équipe !"
            ])
        elif "drôle" in user_input.lower() or "rigolo" in user_input.lower() or "marrant" in user_input.lower():
            responses = [
                "Merci ! J'aime bien faire rire ! 😄",
                "Content que ça vous amuse ! J'aime l'humour !",
                "Hihi, merci ! J'essaie d'être un peu drôle parfois ! 😊",
                "Ça me fait plaisir de vous faire sourire ! 😁",
                "Merci ! L'humour rend tout plus agréable !"
            ]
        
        return self._get_random_response(responses)
    
    def _generate_laughter_response(self, user_input: str, context: Dict[str, Any]) -> str:
        """Génère une réponse aux rires et expressions d'amusement"""
        responses = [
            "Content que ça vous fasse rire ! 😄",
            "Hihi, j'aime bien quand on s'amuse ensemble ! 😊",
            "Ah ça fait plaisir de vous entendre rire ! 😁",
            "Super ! Rien de mieux qu'un bon moment de rigolade ! 🤣",
            "Excellent ! J'aime votre réaction ! 😄",
            "Parfait ! Un peu d'humour ça fait du bien ! 😊",
            "Génial ! Vous avez l'air de bonne humeur ! 😁"
        ]
        
        # Adaptation selon le type de rire
        if "mdr" in user_input.lower() or "lol" in user_input.lower():
            responses.extend([
                "MDR ! Content que ça vous plaise autant ! 😂",
                "LOL ! C'est parti pour la rigolade ! 🤣"
            ])
        elif len(user_input) > 6:  # Long rire type "hahahahaha"
            responses.extend([
                "Wow, ça vous a vraiment fait rire ! 😂",
                "Carrément ! Vous riez aux éclats ! 🤣"
            ])
        
        return self._get_random_response(responses)
    
    def _generate_code_response(self, user_input: str, context: Dict[str, Any]) -> str:
        """Génère une réponse pour les demandes de code"""
        try:
            # Utilisation du générateur de code
            code_response = self.code_generator.generate_code(user_input)
            
            # Ajout d'un message personnalisé
            intro_messages = [
                "Voici le code que j'ai généré pour vous :",
                "J'ai créé ce code selon votre demande :",
                "Voilà ce que j'ai préparé pour vous :",
                "J'espère que ce code vous aidera :"
            ]
            
            intro = self._get_random_response(intro_messages)
            return f"{intro}\n\n{code_response}"
            
        except Exception as e:
            return f"Désolé, j'ai eu un problème pour générer le code : {str(e)}"
    
    def _generate_help_response(self, user_input: str, context: Dict[str, Any]) -> str:
        """Génère une réponse d'aide contextuelle"""
        help_text = """🤖 Aide 🤖

💬 **Pour discuter :** Posez-moi vos questions naturellement
📄 **Pour les documents :** Utilisez les boutons pour traiter vos PDF/DOCX, puis demandez-moi de les résumer ou de répondre à des questions
💻 **Pour le code :** Traitez vos fichiers Python, puis demandez-moi de les expliquer ou de les améliorer
� **Pour la recherche internet :** Dites "Cherche sur internet [sujet]"
😄 **Pour l'humour :** Demandez-moi une blague !

�🎯 **Exemples :**
• "Résume le document" - après avoir traité un PDF
• "Explique ce code" - après avoir traité un fichier Python
• "Génère une fonction pour..." - pour créer du code
• "Cherche sur internet les actualités Python"
• "Raconte-moi une blague"
• "Comment créer une liste en Python ?"
• "Qui es-tu ?" - pour connaître mes capacités"""
        
        if self._has_documents_in_memory():
            help_text += f"\n\n📚 **Documents disponibles :** Vous avez {len(self.conversation_memory.get_document_content())} document(s) en mémoire"
        
        return help_text
    
    def _generate_thank_you_response(self, context: Dict[str, Any]) -> str:
        """Génère une réponse aux remerciements"""
        responses = [
            "De rien ! C'était un plaisir de vous aider ! 😊",
            "Je vous en prie ! N'hésitez pas si vous avez d'autres questions !",
            "Avec plaisir ! C'est pour ça que je suis là !",
            "Pas de quoi ! J'espère que ça vous a été utile !",
            "De rien du tout ! J'aime beaucoup aider !"
        ]
        
        return self._get_random_response(responses)
    
    def _generate_goodbye_response(self, context: Dict[str, Any]) -> str:
        """Génère une réponse d'au revoir"""
        total_interactions = context.get("total_interactions", 0)
        
        goodbyes = [
            "Au revoir ! J'ai été ravi de discuter avec vous ! 😊",
            "À bientôt ! N'hésitez pas à revenir quand vous voulez !",
            "Salut ! J'espère vous revoir bientôt !",
            "Au revoir ! Passez une excellente journée !"
        ]
        
        base_response = self._get_random_response(goodbyes)
        
        # Ajout d'un résumé de la session
        if total_interactions > 3:
            minutes = int(context.get("session_duration", 0) // 60)
            base_response += f"\n\nMerci pour cette conversation de {total_interactions} messages ! "
            if minutes > 0:
                base_response += f"Nous avons discuté {minutes} minutes, c'était super !"
        
        return base_response
    
    def _generate_affirmation_response(self, context: Dict[str, Any]) -> str:
        """Génère une réponse aux affirmations"""
        responses = [
            "Parfait ! Content que vous soyez d'accord ! 😊",
            "Excellent ! On est sur la même longueur d'onde !",
            "Super ! J'aime quand on se comprend bien !",
            "Génial ! Que puis-je faire d'autre pour vous ?"
        ]
        
        return self._get_random_response(responses)
    
    def _generate_negation_response(self, context: Dict[str, Any]) -> str:
        """Génère une réponse aux négations"""
        responses = [
            "D'accord, pas de problème ! Que préférez-vous ?",
            "Compris ! Comment puis-je mieux vous aider ?",
            "Pas de souci ! Dites-moi ce que vous voulez vraiment.",
            "OK, on peut essayer autre chose ! Qu'est-ce qui vous conviendrait mieux ?"
        ]
        
        return self._get_random_response(responses)
    
    def _generate_default_response(self, user_input: str, context: Dict[str, Any]) -> str:
        """Génère une réponse par défaut intelligente"""
        # Analyser le type de demande
        user_lower = user_input.lower()
        
        # NOUVELLE VÉRIFICATION : Questions sur les capacités non détectées
        if any(phrase in user_lower for phrase in ["à quoi tu sers", "à quoi sert tu", "à quoi sers tu", "à quoi tu sert", 
                                                    "tu sers à quoi", "tu sert à quoi", "tu sers a quoi", "tu sert a quoi", 
                                                    "ton utilité", "votre utilité"]):
            return self._generate_capabilities_response(user_input, context)
        
        # Si ça ressemble à une demande de code
        if any(word in user_lower for word in ["génère", "crée", "code", "fonction", "script"]):
            try:
                code_response = self.code_generator.generate_code(user_input)
                return f"Voici ce que j'ai généré pour vous :\n\n{code_response}"
            except:
                return "Je peux générer du code ! Soyez plus spécifique : voulez-vous une fonction, une classe, ou un script complet ?"
        
        # Si ça ressemble à une question générale sur la programmation
        elif any(word in user_lower for word in ["comment créer", "comment utiliser", "comment faire", "comment déclarer"]):
            return self._answer_programming_question(user_input, context)
        
        # Si ça ressemble à une question générale autre
        elif any(word in user_lower for word in ["comment", "pourquoi", "qu'est-ce", "quoi"]):
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
            "Attendez, j'en ai une drôle ! 🤭"
        ]
        
        # Choisir une introduction différente si possible
        if hasattr(self, 'last_joke_intro'):
            available_intros = [intro for intro in introductions if intro != self.last_joke_intro]
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
            search_context = {
                "conversation_context": context,
                "user_language": "français",
                "search_type": self._detect_search_type(user_input)
            }
            
            result = self.internet_search.search_and_summarize(search_query, search_context)
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
        user_lower = user_input.lower().strip()
        
        # Patterns pour extraire la requête
        patterns = [
            r"(?:cherche|recherche|trouve)\s+(?:sur\s+)?(?:internet|web|google|en ligne)\s+(.+)",
            r"(?:cherche|recherche)\s+(?:moi\s+)?(?:des\s+)?(?:informations?\s+)?(?:sur|à propos de)\s+(.+)",
            r"cherche[-\s]moi\s+(.+)",
            r"peux[-\s]tu\s+(?:chercher|rechercher|trouver)\s+(.+)",
            r"(?:informations?|info|données|news|actualités?)\s+(?:sur|à propos de|concernant)\s+(.+)",
            r"(?:dernières?\s+)?(?:actualités?|news|nouvelles?)\s+(?:sur|de|à propos de)\s+(.+)",
            r"qu[\'']?est[-\s]ce\s+qu[\'']?on\s+dit\s+(?:sur|de)\s+(.+)",
            r"(?:web|internet|google)\s+search\s+(.+)"
        ]
        
        for pattern in patterns:
            match = re.search(pattern, user_lower)
            if match:
                query = match.group(1).strip()
                # Nettoyer la requête
                query = re.sub(r'\s+', ' ', query)  # Normaliser les espaces
                query = query.strip('.,!?;')  # Supprimer la ponctuation finale
                return query
        
        # Fallback: si aucun pattern ne correspond, essayer de deviner
        # Supprimer les mots de commande du début
        for word in ["cherche", "recherche", "trouve", "sur", "internet", "web", "google", "en", "ligne", "moi", "des", "informations"]:
            if user_lower.startswith(word):
                user_lower = user_lower[len(word):].strip()
        
        return user_lower if len(user_lower) > 2 else ""
    
    def _detect_search_type(self, user_input: str) -> str:
        """
        Détecte le type de recherche demandé
        
        Args:
            user_input: Input de l'utilisateur
            
        Returns:
            str: Type de recherche
        """
        user_lower = user_input.lower()
        
        if any(word in user_lower for word in ["actualité", "news", "dernières nouvelles", "récent"]):
            return "news"
        elif any(word in user_lower for word in ["comment", "how to", "tutorial", "guide", "étapes"]):
            return "tutorial"
        elif any(word in user_lower for word in ["qu'est-ce que", "définition", "c'est quoi", "define"]):
            return "definition"
        elif any(word in user_lower for word in ["prix", "coût", "combien", "price"]):
            return "price"
        elif any(word in user_lower for word in ["avis", "opinion", "review", "critique"]):
            return "review"
        else:
            return "general"
    
    def _answer_programming_question(self, user_input: str, context: Dict[str, Any]) -> str:
        """Répond aux questions de programmation avec des exemples pratiques et intelligence avancée"""
        user_lower = user_input.lower()
        
        # 🚀 ANALYSE INTELLIGENTE DE LA QUESTION
        complexity_level = self._analyze_user_intelligence_level(user_input, context)
        
        # Réponse de base adaptée au niveau
        base_response = ""
        
        # Détection du type de question et réponse avec exemples
        if any(word in user_lower for word in ["liste", "list"]):
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
        else:
            base_response = self._generate_general_programming_help(user_input)
        
        # 🧠 AJOUT D'INTELLIGENCE CONTEXTUELLE
        if complexity_level == "expert":
            base_response += "\n\n💡 **Conseil d'expert** : Consultez PEP 8 pour les conventions de style Python"
            base_response += "\n🔧 **Optimisation** : Considérez l'utilisation de type hints pour une meilleure maintenabilité"
        elif complexity_level == "intermediate":
            base_response += "\n\n⚡ **Conseil pro** : Testez votre code avec des cas limites"
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

🎯 **Moi par exemple :** Je suis une IA locale qui peut vous aider avec vos documents, générer du code, et discuter naturellement !"""
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
        question_words = ["c'est quoi", "qu'est-ce que", "que signifie", "explique moi", "dis moi"]
        
        for word in question_words:
            cleaned = cleaned.replace(word, "").strip()
        
        # Nettoyer la ponctuation
        cleaned = cleaned.strip("?!.,;:")
        
        return cleaned if cleaned else "ce sujet"
    
    def _detect_user_style(self, context: Dict[str, Any]) -> str:
        """Détecte le style de communication de l'utilisateur"""
        # Analyser l'historique récent pour détecter le style
        recent_messages = context.get("recent_user_messages", [])
        
        casual_indicators = ["salut", "sa va", "wesh", "lol", "mdr", "cool", "sympa", "ok", "ouais", "wsh"]
        formal_indicators = ["bonjour", "bonsoir", "merci beaucoup", "s'il vous plaît", "pouvez-vous"]
        
        if any(any(indicator in msg.lower() for indicator in casual_indicators) for msg in recent_messages):
            return "casual"
        elif any(any(indicator in msg.lower() for indicator in formal_indicators) for msg in recent_messages):
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

💡 **Concepts clés :**
• `__init__` : constructeur appelé à la création
• `self` : référence à l'instance courante
• Attributs : variables de l'objet
• Méthodes : fonctions de l'objet
• Encapsulation : regrouper données et comportements"""

    def _generate_general_programming_help(self, user_input: str) -> str:
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
• "Comment créer une liste en Python ?"
• "Quelle est la différence entre une liste et un dictionnaire ?"
• "Comment faire une boucle sur un dictionnaire ?"
• "Comment créer une fonction avec des paramètres ?"

🎯 **Soyez spécifique :** Plus votre question est précise, plus ma réponse sera adaptée à vos besoins !

Que voulez-vous apprendre exactement ?"""
    
    def _get_random_response(self, responses: List[str]) -> str:
        """Sélectionne une réponse aléatoire"""
        import random
        return random.choice(responses)
        
    def _generate_document_summary(self, user_input: str) -> str:
        """
        Génère un résumé intelligent d'un document (PDF ou DOCX) - Version universelle
        
        Args:
            user_input: La demande de résumé contenant le texte extrait du document
            
        Returns:
            str: Résumé du contenu du document
        """
        print(f"🔍 DEBUG: user_input reçu dans _generate_document_summary:")
        print(f"Longueur: {len(user_input)}")
        print(f"Premiers 500 caractères: {user_input[:500]}")
        print(f"--- SÉPARATEUR ---")
        
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
            r'Please summarize this PDF content from file \'(.+?)\':\n',
            r'Please analyze this document content from file \'(.+?)\':\n',
            r'Processed (?:PDF|DOCX): (.+?)(?:\n|$)',
            r'Fichier (?:PDF|DOCX): (.+?)(?:\n|$)',
            r'Document: (.+?)(?:\n|$)',
            r'PDF: (.+?)(?:\n|$)',
            r'DOCX: (.+?)(?:\n|$)'
        ]
        
        filename = "document"
        for pattern in filename_patterns:
            filename_match = re.search(pattern, user_input, re.IGNORECASE)
            if filename_match:
                filename = filename_match.group(1).strip()
                # Nettoyer le nom de fichier en gardant le nom de base
                filename = filename.replace('.pdf', '').replace('.docx', '').replace('.PDF', '').replace('.DOCX', '')
                break
        
        # Si on n'a toujours pas trouvé, essayer d'extraire depuis le prompt "please summarize this"
        if filename == "document":
            # Chercher des patterns dans le prompt système
            system_patterns = [
                r'please summarize this pdf content:\s*(.+?)\.pdf',
                r'please analyze this document content:\s*(.+?)\.docx',
                r'PDF:\s*(.+?)\.pdf',
                r'DOCX:\s*(.+?)\.docx'
            ]
            
            for pattern in system_patterns:
                match = re.search(pattern, user_input, re.IGNORECASE)
                if match:
                    filename = match.group(1).strip()
                    break
        
        # Si toujours pas trouvé, chercher dans les lignes avec .pdf/.docx
        if filename == "document":
            lines = user_input.split('\n')
            for line in lines[:10]:  # Chercher dans les 10 premières lignes
                if '.pdf' in line.lower() or '.docx' in line.lower():
                    # Extraire le nom de fichier potentiel
                    words = line.split()
                    for word in words:
                        if '.pdf' in word.lower() or '.docx' in word.lower():
                            filename = word.strip(',:()[]').replace('.pdf', '').replace('.docx', '').replace('.PDF', '').replace('.DOCX', '')
                            break
                    if filename != "document":
                        break
        
        print(f"📄 Nom de fichier extrait: '{filename}'")
        
        # Stockage du contenu du document dans le contexte de conversation
        self.conversation_memory.store_document_content(filename, document_content)
        
        # Analyse du contenu de manière générique
        return self._create_universal_summary(document_content, filename, doc_type)
    
    def _create_universal_summary(self, content: str, filename: str, doc_type: str) -> str:
        """Crée un résumé universel et naturel"""
        # Statistiques de base
        word_count = len(content.split())
        char_count = len(content)
        paragraph_count = len([p for p in content.split('\n\n') if p.strip()])
        
        # Extraction des phrases clés
        sentences = [s.strip() for s in re.split(r'[.!?]+', content) if len(s.strip()) > 20]
        
        if "docx" in filename.lower() or doc_type.lower() == "docx":
            doc_type_display = "document"
        elif "pdf" in filename.lower() or doc_type.lower() == "pdf":
            doc_type_display = "PDF"
        else:
            doc_type_display = doc_type
        
        # Début du résumé
        summary = f"📄 **Résumé du {doc_type_display} '{filename}'**\n\n"
        
        if word_count < 50:
            summary += "⚠️ Ce document contient très peu de texte.\n\n"
        
        summary += f"📊 **Contenu analysé :** {word_count} mots, {paragraph_count} paragraphes\n\n"
        
        # Contenu principal
        if sentences:
            summary += "📝 **Contenu principal :**\n"
            if len(sentences) >= 1:
                summary += f"Le document commence par : \"{sentences[0][:150]}{'...' if len(sentences[0]) > 150 else ''}\"\n\n"
            
            if len(sentences) > 1:
                summary += "🔍 **Points clés :**\n"
                key_sentences = sentences[1:4]  # 2-4ème phrases
                for i, sentence in enumerate(key_sentences, 1):
                    if len(sentence) > 200:
                        sentence = sentence[:197] + "..."
                    summary += f"• {sentence}\n"
                summary += "\n"
        
        # Analyse thématique simple
        themes = self._analyze_content_themes(content)
        if themes:
            summary += "🏷️ **Thèmes identifiés :** " + ", ".join(themes[:5]) + "\n\n"
        
        # Message de mémorisation
        summary += "💾 **Document mémorisé :** Vous pouvez maintenant me poser des questions spécifiques sur ce contenu."
        
        return summary

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
        """
        Extrait les phrases clés d'un document de manière universelle
        
        Args:
            content: Contenu du document
            max_sentences: Nombre maximum de phrases à extraire
            
        Returns:
            Liste des phrases clés
        """
        # Nettoyage et séparation en phrases
        content_clean = re.sub(r'\s+', ' ', content.strip())
        
        # Séparation en phrases (approximative)
        sentences = re.split(r'[.!?]+\s+', content_clean)
        sentences = [s.strip() for s in sentences if len(s.strip()) > 20]  # Phrases significatives
        
        key_sentences = []
        
        # Première phrase (souvent importante)
        if sentences:
            key_sentences.append(sentences[0][:200] + "..." if len(sentences[0]) > 200 else sentences[0])
        
        # Phrases avec des mots d'importance (mots de transition, etc.)
        importance_words = ['important', 'essentiel', 'principal', 'objectif', 'but', 'conclusion', 
                          'résultat', 'efficace', 'nécessaire', 'recommandé', 'obligatoire']
        
        for sentence in sentences[1:]:
            if any(word in sentence.lower() for word in importance_words):
                if len(key_sentences) < max_sentences:
                    key_sentences.append(sentence[:200] + "..." if len(sentence) > 200 else sentence)
        
        # Si pas assez de phrases "importantes", prendre des phrases du milieu et de la fin
        if len(key_sentences) < max_sentences and len(sentences) > 2:
            # Phrase du milieu
            mid_idx = len(sentences) // 2
            if mid_idx < len(sentences) and len(key_sentences) < max_sentences:
                mid_sentence = sentences[mid_idx]
                if mid_sentence not in key_sentences:
                    key_sentences.append(mid_sentence[:200] + "..." if len(mid_sentence) > 200 else mid_sentence)
            
            # Dernière phrase si elle est substantielle
            if len(sentences) > 1 and len(key_sentences) < max_sentences:
                last_sentence = sentences[-1]
                if len(last_sentence) > 30 and last_sentence not in key_sentences:
                    key_sentences.append(last_sentence[:200] + "..." if len(last_sentence) > 200 else last_sentence)
        
        return key_sentences[:max_sentences]
    
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
            "le", "la", "les", "un", "une", "des", "et", "ou", "à", "au", "aux", "ce", "ces", 
            "dans", "en", "par", "pour", "sur", "il", "elle", "ils", "elles", "je", "tu", 
            "nous", "vous", "que", "qui", "dont", "où", "quoi", "comment", "pourquoi", "avec", 
            "cette", "comme", "plus", "moins", "sans", "très", "tout", "tous", "toutes", "bien", 
            "être", "avoir", "faire", "aller", "venir", "voir", "savoir", "pouvoir", "vouloir", 
            "devoir", "falloir", "peut", "peuvent", "doit", "doivent", "sont", "était", "sera", 
            "seront", "était", "étaient", "sera", "seront", "donc", "mais", "car", "ainsi", 
            "alors", "après", "avant", "pendant", "depuis", "jusqu", "lors", "tandis"
        }
        
        # Extraction de tous les mots significatifs
        words = re.findall(r'\b\w{4,}\b', text_lower)
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
            "général": []
        }
        
        # Classification des mots par thème
        for word, freq in sorted(significant_words.items(), key=lambda x: x[1], reverse=True):
            if word in ['technique', 'technologie', 'système', 'méthode', 'processus', 'développement', 'solution']:
                themes["technique"].append(f"{word} ({freq})")
            elif word in ['procédure', 'étape', 'action', 'mesure', 'protocole', 'instruction', 'consigne']:
                themes["procédure"].append(f"{word} ({freq})")
            elif word in ['information', 'données', 'résultat', 'analyse', 'rapport', 'document', 'fichier']:
                themes["information"].append(f"{word} ({freq})")
            elif word in ['gestion', 'organisation', 'responsable', 'équipe', 'groupe', 'personnel', 'service']:
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
        lines = content.split('\n')
        potential_sections = []
        
        for line in lines:
            line_clean = line.strip()
            if line_clean:
                # Lignes courtes qui pourraient être des titres
                if len(line_clean) < 80 and (
                    line_clean.isupper() or  # Tout en majuscules
                    re.match(r'^[A-Z][^.]*$', line_clean) or  # Commence par majuscule, pas de point final
                    re.match(r'^\d+\.?\s+[A-Z]', line_clean)  # Commence par un numéro
                ):
                    potential_sections.append(line_clean)
        
        if potential_sections:
            structure['sections'] = potential_sections[:10]  # Max 10 sections
        
        # Détection de listes ou énumérations
        list_indicators = len(re.findall(r'^\s*[-•*]\s+', content, re.MULTILINE))
        numbered_lists = len(re.findall(r'^\s*\d+\.?\s+', content, re.MULTILINE))
        
        structure['lists'] = list_indicators + numbered_lists
        
        # Détection de données numériques
        numbers = re.findall(r'\b\d+(?:[.,]\d+)?\b', content)
        if len(numbers) > 5:  # Document avec beaucoup de chiffres
            structure['numbers'] = True
        
        return structure
        
    def _find_keyword_context(self, text: str, keyword: str, context_length: int = 30) -> List[str]:
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
            context = text[context_start:context_end].replace('\n', ' ').strip()
            
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
        identity_keywords = ["qui es-tu", "qui es tu", "qui êtes vous", "comment tu t'appelles", "ton nom", "tu es qui", "tu es quoi"]
        capability_keywords = ["que peux tu", "que sais tu", "tes capacités", "tu peux faire", "que fais-tu", 
                              "comment vas tu", "comment ça va", "ça va", "sa va", "ca va"]
        
        # Si la question contient un mot-clé d'identité ou de capacité, ce n'est pas une question sur un document
        user_lower = user_input.lower()
        if any(keyword in user_lower for keyword in identity_keywords + capability_keywords):
            return False
            
        # Mots-clés qui indiquent clairement une question sur un document
        document_keywords = [
            # Résumés et analyses spécifiques
            "résume le pdf", "résume le doc", "résume le document", "résume le fichier",
            "analyse le pdf", "analyse le doc", "analyse le document", "analyse le fichier",
            
            # Références explicites
            "ce pdf", "ce document", "ce fichier", "ce docx", "ce doc", "cette page",
            "le pdf", "le document", "le fichier", "le docx", "le doc",
            "du pdf", "du document", "du fichier", "du docx", "du doc",
            
            # Questions spécifiques avec contexte
            "que dit le pdf", "que dit le document", "que contient le pdf", "que contient le document",
            "dans le pdf", "dans le document", "dans le fichier",
            
            # Résumés simples avec contexte documentaire récent
            "résume", "resume", "résumé" if any("pdf" in str(doc).lower() or "docx" in str(doc).lower() 
                                                 for doc in self.conversation_memory.get_document_content().values()) else ""
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
                language = doc_data.get("language", "Python")
                
                user_lower = user_input.lower()
                
                if any(word in user_lower for word in ["explique", "que fait", "comment"]):
                    return self._explain_code_naturally(code_content, last_doc, language)
                elif any(word in user_lower for word in ["améliore", "optimise"]):
                    return self._suggest_improvements_naturally(code_content, last_doc)
                else:
                    return f"J'ai le code de '{last_doc}' en mémoire. Que voulez-vous savoir ? Je peux l'expliquer, suggérer des améliorations, ou répondre à des questions spécifiques."
        
        return "J'ai du code en mémoire mais je ne sais pas lequel vous intéresse. Précisez votre question !"
    
    def _explain_code_naturally(self, code: str, filename: str, language: str) -> str:
        """Explique le code de manière naturelle et accessible"""
        lines = code.split('\n')
        
        # Analyse basique
        functions = []
        classes = []
        imports = []
        
        for i, line in enumerate(lines, 1):
            line_stripped = line.strip()
            if line_stripped.startswith('def '):
                func_name = line_stripped.split('(')[0].replace('def ', '')
                functions.append(f"'{func_name}()' (ligne {i})")
            elif line_stripped.startswith('class '):
                class_name = line_stripped.split(':')[0].replace('class ', '').split('(')[0]
                classes.append(f"'{class_name}' (ligne {i})")
            elif line_stripped.startswith(('import ', 'from ')):
                imports.append(line_stripped)
        
        response = f"📄 **Explication du code '{filename}'**\n\n"
        
        # Structure générale
        response += f"Ce fichier {language} fait {len(lines)} lignes. Voici ce qu'il contient :\n\n"
        
        if imports:
            response += f"📦 **Modules utilisés :** {len(imports)} imports\n"
            for imp in imports[:3]:  # Montrer les 3 premiers
                response += f"• {imp}\n"
            if len(imports) > 3:
                response += f"• ... et {len(imports)-3} autres\n"
            response += "\n"
        
        if classes:
            response += f"🏗️ **Classes définies :** {len(classes)}\n"
            for cls in classes:
                response += f"• Classe {cls}\n"
            response += "\n"
        
        if functions:
            response += f"⚙️ **Fonctions principales :** {len(functions)}\n"
            for func in functions[:5]:  # Montrer les 5 premières
                response += f"• Fonction {func}\n"
            if len(functions) > 5:
                response += f"• ... et {len(functions)-5} autres\n"
            response += "\n"
        
        # Analyse du contenu
        if "tkinter" in code.lower():
            response += "🖥️ **Type :** Interface graphique (Tkinter)\n"
        elif "flask" in code.lower() or "django" in code.lower():
            response += "🌐 **Type :** Application web\n"
        elif "class" in code and "def __init__" in code:
            response += "🏛️ **Style :** Programmation orientée objet\n"
        
        response += "\n💬 **Questions :** N'hésitez pas à me demander des détails sur une fonction spécifique ou la logique générale !"
        
        return response

    def _suggest_improvements_naturally(self, code: str, filename: str) -> str:
        """Suggère des améliorations de manière naturelle"""
        suggestions = []
        
        # Analyse simple du code
        if '"""' not in code and "'''" not in code:
            suggestions.append("📝 **Documentation :** Ajouter des docstrings aux fonctions pour expliquer leur rôle")
        
        if 'import *' in code:
            suggestions.append("📦 **Imports :** Éviter `import *`, préférer des imports spécifiques")
        
        if not any(line.strip().startswith('#') for line in code.split('\n')):
            suggestions.append("💬 **Commentaires :** Ajouter des commentaires pour expliquer la logique")
        
        if 'except:' in code:
            suggestions.append("⚠️ **Gestion d'erreurs :** Spécifier les types d'exceptions plutôt que `except:` générique")
        
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
        
    def _explain_code_functionality(self, user_input: str, stored_docs: Dict[str, Any]) -> str:
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
                        return self._explain_generic_code(code_content, last_doc, language)
        
        return "Je n'ai pas de fichier de code récent à expliquer."

    def _explain_python_code(self, code: str, filename: str) -> str:
        """Explique spécifiquement du code Python"""
        
        analysis = {
            "imports": [],
            "functions": [],
            "classes": [],
            "main_logic": [],
            "key_variables": []
        }
        
        lines = code.split('\n')
        
        for i, line in enumerate(lines, 1):
            line_stripped = line.strip()
            
            # Imports
            if line_stripped.startswith(('import ', 'from ')):
                analysis["imports"].append(f"Ligne {i}: {line_stripped}")
            
            # Fonctions
            elif line_stripped.startswith('def '):
                func_name = line_stripped.split('(')[0].replace('def ', '')
                analysis["functions"].append(f"Ligne {i}: Fonction '{func_name}()'")
            
            # Classes
            elif line_stripped.startswith('class '):
                class_name = line_stripped.split(':')[0].replace('class ', '').split('(')[0]
                analysis["classes"].append(f"Ligne {i}: Classe '{class_name}'")
            
            # Variables importantes (= en début de ligne)
            elif line_stripped and not line_stripped.startswith((' ', '\t', '#')) and '=' in line_stripped:
                var_part = line_stripped.split('=')[0].strip()
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
                module_name = imp.split(': ')[1] if ': ' in imp else imp
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
    
    def _suggest_code_improvements(self, user_input: str, stored_docs: Dict[str, Any]) -> str:
        """Suggère des améliorations pour le code"""
        
        last_doc = self.conversation_memory.document_order[-1] if self.conversation_memory.document_order else None
        if not last_doc or last_doc not in stored_docs:
            return "Je n'ai pas de code à analyser pour suggérer des améliorations."
        
        doc_data = stored_docs[last_doc]
        code_content = doc_data["content"]
        language = doc_data.get("language", "unknown")
        
        suggestions = []
        
        if language == "python":
            lines = code_content.split('\n')
            
            # Vérifier les docstrings
            has_docstrings = '"""' in code_content or "'''" in code_content
            if not has_docstrings:
                suggestions.append("📝 **Documentation :** Ajouter des docstrings aux fonctions et classes pour expliquer leur rôle")
            
            # Vérifier les imports
            if 'import *' in code_content:
                suggestions.append("📦 **Imports :** Éviter `import *`, préférer des imports spécifiques pour plus de clarté")
            
            # Vérifier la longueur des lignes
            long_lines = [i+1 for i, line in enumerate(lines) if len(line) > 100]
            if long_lines:
                suggestions.append(f"📏 **Lisibilité :** Raccourcir les lignes trop longues (ex: lignes {long_lines[:3]})")
            
            # Vérifier les noms de variables courtes
            short_vars = []
            for line in lines:
                if '=' in line and not line.strip().startswith('#'):
                    var_part = line.split('=')[0].strip()
                    if len(var_part) <= 2 and var_part.isalpha() and var_part not in ['x', 'y', 'i', 'j']:
                        short_vars.append(var_part)
            
            if short_vars:
                suggestions.append(f"🏷️ **Nommage :** Utiliser des noms plus descriptifs pour : {', '.join(set(short_vars[:3]))}")
            
            # Vérifier la gestion d'erreurs
            if 'try:' in code_content and 'except:' in code_content:
                suggestions.append("⚠️ **Gestion d'erreurs :** Spécifier les types d'exceptions plutôt que `except:` générique")
            
            # Vérifier les commentaires
            comment_ratio = len([l for l in lines if l.strip().startswith('#')]) / max(len(lines), 1)
            if comment_ratio < 0.1:
                suggestions.append("💬 **Commentaires :** Ajouter plus de commentaires pour expliquer la logique complexe")
        
        if not suggestions:
            suggestions = [
                "✅ **Excellent code !** Voici quelques idées d'amélioration générale :",
                "• Ajouter des tests unitaires pour vérifier le bon fonctionnement",
                "• Considérer l'ajout de logs pour faciliter le debug",
                "• Vérifier la conformité aux standards du langage (PEP 8 pour Python)"
            ]
        
        response = f"🔧 **Suggestions d'amélioration pour '{last_doc}'**\n\n"
        for i, suggestion in enumerate(suggestions, 1):
            response += f"{i}. {suggestion}\n"
        
        response += "\n💡 **Besoin d'aide pour implémenter ces améliorations ?**\n"
        response += "Demandez-moi de vous montrer comment appliquer ces suggestions concrètement !"
        
        return response
    
    def _suggest_code_modifications(self, user_input: str, stored_docs: Dict[str, Any]) -> str:
        """Suggère des modifications spécifiques du code"""
        return "🔨 **Modifications de code**\n\nDites-moi exactement ce que vous voulez modifier et je vous proposerai le code modifié !"

    def _analyze_code_issues(self, user_input: str, stored_docs: Dict[str, Any]) -> str:
        """Analyse les problèmes potentiels dans le code"""
        return "🐛 **Analyse des problèmes**\n\nDécrivez-moi le problème que vous rencontrez et je vous aiderai à le résoudre !"

    def _general_code_analysis(self, user_input: str, stored_docs: Dict[str, Any]) -> str:
        """Analyse générale du code"""
        return self._explain_code_functionality(user_input, stored_docs)

    def _answer_document_question(self, user_input: str, stored_docs: Dict[str, Any]) -> str:
        """Répond aux questions sur les documents - VERSION SIMPLIFIÉE qui respecte la sélection AI_ENGINE"""
        if not stored_docs:
            return "Je n'ai pas de documents en mémoire pour répondre à votre question."
        
        # NOUVELLE LOGIQUE : Si le prompt contient déjà une instruction de document spécifique, la respecter
        if "🚨 RÈGLE ABSOLUE ET OBLIGATOIRE 🚨" in user_input:
            # Le prompt vient de ai_engine.py avec un document spécifique - NE PAS interférer
            lines = user_input.split('\n')
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
                return self._create_universal_summary(document_content.strip(), doc_name, "DOCX")
        
        # ANCIENNE LOGIQUE pour les autres cas (garde pour compatibilité)
        user_lower = user_input.lower().strip()
        
        # Gestion des demandes de résumé avec sélection de document
        resume_keywords = ["résume", "resume", "résumé"]
        
        if any(keyword in user_lower for keyword in resume_keywords):
            
            # Si seulement un document, l'utiliser directement
            if len(stored_docs) == 1:
                doc_name = list(stored_docs.keys())[0]
                doc_data = stored_docs[doc_name]
                content = doc_data.get("content", "")
                
                # Déterminer le type de document
                if any(ext in doc_name.lower() for ext in ["pdf", "livret"]):
                    doc_type = "PDF"
                elif any(ext in doc_name.lower() for ext in ["docx", "doc", "notes"]):
                    doc_type = "document"
                else:
                    doc_type = "document"
                    
                return self._create_universal_summary(content, doc_name, doc_type)
            
            # LOGIQUE MULTI-DOCUMENTS (ancienne logique conservée)
            # Gestion spécifique selon le type de document demandé
            if "pdf" in user_lower:
                # L'utilisateur demande spécifiquement le PDF
                pdf_docs = {name: doc for name, doc in stored_docs.items() 
                        if any(word in name.lower() for word in ["pdf", "livret", "cauquillous"])}
                
                if pdf_docs:
                    doc_name = list(pdf_docs.keys())[0]
                    doc_data = pdf_docs[doc_name]
                    content = doc_data.get("content", "")
                    return self._create_universal_summary(content, doc_name, "PDF")
                else:
                    return "Je n'ai pas de document PDF en mémoire."
            
            elif any(word in user_lower for word in ["doc", "docx", "word"]):
                # L'utilisateur demande spécifiquement le document Word
                docx_docs = {name: doc for name, doc in stored_docs.items() 
                            if any(word in name.lower() for word in ["notes", "stage", "docx"])}
                
                if docx_docs:
                    doc_name = list(docx_docs.keys())[0]
                    doc_data = docx_docs[doc_name]
                    content = doc_data.get("content", "")
                    return self._create_universal_summary(content, doc_name, "document")
                else:
                    return "Je n'ai pas de document en mémoire."
            
            else:
                # Résumé générique - prendre le dernier document ajouté
                if self.conversation_memory.document_order:
                    last_doc = self.conversation_memory.document_order[-1]
                    if last_doc in stored_docs:
                        doc_data = stored_docs[last_doc]
                        content = doc_data.get("content", "")
                        
                        # Déterminer le type correct
                        if any(word in last_doc.lower() for word in ["pdf", "livret"]):
                            doc_type = "PDF"
                        elif any(word in last_doc.lower() for word in ["notes", "stage", "docx"]):
                            doc_type = "document"
                        else:
                            doc_type = "document"
                        
                        return self._create_universal_summary(content, last_doc, doc_type)
        
        # Autres questions spécifiques
        return f"J'ai {len(stored_docs)} document(s) en mémoire : {', '.join(stored_docs.keys())}. Que voulez-vous savoir précisément ?"

    def _process_document_question(self, user_input: str, target_docs: Dict[str, Any], reference_detected: bool) -> str:
        """
        Traite les questions sur les documents PDF/DOCX
        """
        user_lower = user_input.lower()
        
        # Si c'est une demande de résumé simple
        if any(keyword in user_lower for keyword in ["résume", "resume", "résumé", "summary", "sommaire"]):
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
                    summaries.append(self._create_universal_summary(doc_content, doc_name, doc_type))
                return "\n\n".join(summaries)
        
        # Pour les autres questions, utiliser la logique existante de recherche
        question_keywords = self._extract_question_keywords(user_input)
        
        # Recherche dans les documents ciblés
        best_matches = []
        
        for filename, doc_data in target_docs.items():
            content = doc_data["content"]
            matches = self._find_relevant_passages(content, question_keywords, user_input)
            
            if matches:
                best_matches.extend([{
                    "filename": filename,
                    "passage": match["passage"],
                    "context": match["context"],
                    "relevance": match["relevance"]
                } for match in matches])
        
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
                response_parts.append(f"D'après le {doc_position} document \"{doc_name}\" :")
            else:
                response_parts.append(f"D'après le document \"{doc_name}\" :")
        else:
            response_parts.append("D'après les documents que j'ai analysés :")
        
        for i, match in enumerate(top_matches, 1):
            passage = match["passage"]
            if len(passage) > 300:
                passage = passage[:297] + "..."
            
            if len(target_docs) > 1:
                response_parts.append(f"\n{i}. **Dans {match['filename']}** :")
                response_parts.append(f"   \"{passage}\"")
            else:
                response_parts.append(f"\n• {passage}")
            
            if match["context"]:
                context = match["context"]
                if len(context) > 200:
                    context = context[:197] + "..."
                response_parts.append(f"   Contexte : {context}")
        
        # Ajouter une phrase de conclusion
        if len(top_matches) > 1:
            response_parts.append(f"\nJ'ai trouvé {len(best_matches)} références pertinentes dans le(s) document(s). Voulez-vous que je détaille un point particulier ?")
        else:
            response_parts.append(f"\nC'est ce que j'ai trouvé de plus pertinent. Avez-vous besoin de plus de détails ?")
        
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
            "le", "la", "les", "un", "une", "des", "et", "ou", "à", "au", "aux", 
            "ce", "ces", "dans", "en", "par", "pour", "sur", "il", "elle", "ils", 
            "elles", "je", "tu", "nous", "vous", "que", "qui", "dont", "où", 
            "quoi", "comment", "pourquoi", "avec", "cette", "comme", "plus", 
            "moins", "sans", "très", "tout", "tous", "toutes", "bien", "être", 
            "avoir", "faire", "aller", "venir", "voir", "savoir", "pouvoir", 
            "vouloir", "devoir", "peut", "peuvent", "doit", "doivent", "que", 
            "dit", "peux", "explique", "moi", "document", "pdf", "fichier"
        }
        
        # Extraire les mots de 2+ caractères (abaissé pour capturer "no", "n°")
        words = re.findall(r'\b\w{2,}\b', question.lower())
        keywords = [word for word in words if word not in stop_words]
        
        # Ajouter des variantes pour les fautes communes et les synonymes
        expanded_keywords = []
        for keyword in keywords:
            expanded_keywords.append(keyword)
            
            # Corrections communes de fautes d'orthographe et synonymes - TRÈS ÉTENDU
            corrections = {
                # Urgence et variations
                "urgence": ["urgance", "urgense", "urgent", "urgents", "emergency", "emergancy", "emerjency"],
                "urgent": ["urgence", "urgance", "urgense", "urgents", "emergency"],
                
                # Numéros et variations
                "numéro": ["numero", "numeros", "numerot", "n°", "no", "nr", "num", "number", "tel", "telephone", "tél"],
                "numero": ["numéro", "numeros", "numerot", "n°", "no", "nr", "num", "number"],
                "number": ["numéro", "numero", "n°", "no", "nr", "num"],
                
                # Sécurité et variations
                "sécurité": ["securite", "securité", "secorite", "security", "safety", "saftey"],
                "securite": ["sécurité", "securité", "secorite", "security", "safety"],
                "security": ["sécurité", "securite", "safety", "secorite"],
                
                # Défibrillateur et variations
                "défibrillateur": ["defibrillateur", "defibrillateur", "défibrillateur", "defibrillator", "defibrulator"],
                "defibrillateur": ["défibrillateur", "defibrillateur", "défibrillateur", "defibrillator"],
                "defibrillator": ["défibrillateur", "defibrillateur", "defibrillateur", "défibrillateur"],
                
                # Extincteur et variations
                "extincteur": ["extincteurs", "estincteur", "fire", "extinguisher", "extinquisher"],
                "extinguisher": ["extincteur", "extincteurs", "estincteur", "extinquisher"],
                
                # Secours et variations
                "secours": ["secour", "secoure", "secours", "help", "aide", "assistance", "emergency", "urgence"],
                "help": ["secours", "aide", "assistance", "secour", "secoure"],
                "aide": ["secours", "help", "assistance", "secour", "secoure"],
                
                # Téléphone et variations
                "téléphone": ["telephone", "telefone", "phone", "tel", "appel", "tél", "telephon"],
                "telephone": ["téléphone", "telefone", "phone", "tel", "appel", "tél"],
                "phone": ["téléphone", "telephone", "telefone", "tel", "appel"],
                "tel": ["téléphone", "telephone", "phone", "telefone", "appel", "tél"],
                
                # Poste et variations
                "poste": ["post", "postes", "extension", "ext", "poste"],
                "extension": ["poste", "post", "ext", "postes"],
                "ext": ["extension", "poste", "post", "postes"],
                
                # Travail et variations
                "travail": ["travaille", "travai", "work", "job", "bureau", "office", "boulot"],
                "work": ["travail", "travaille", "job", "bureau", "boulot"],
                "bureau": ["office", "travail", "work", "job"],
                
                # Contact et variations
                "contact": ["contacter", "appeler", "joindre", "call", "telephoner", "téléphoner", "contacte"],
                "contacter": ["contact", "appeler", "joindre", "call", "telephoner"],
                "appeler": ["contact", "contacter", "joindre", "call", "telephoner"],
                "call": ["contact", "contacter", "appeler", "joindre"],
                
                # Accident et variations
                "accident": ["incidents", "incident", "blessure", "injury", "emergency", "blessé", "blesser"],
                "incident": ["accident", "incidents", "blessure", "injury", "emergency"],
                "blessure": ["accident", "incident", "injury", "blessé", "blesser"],
                "injury": ["accident", "incident", "blessure", "blessé"],
                
                # Évacuation et variations
                "évacuation": ["evacuation", "sortie", "exit", "evacuer", "évacuer", "evacuate"],
                "evacuation": ["évacuation", "sortie", "exit", "evacuer", "évacuer"],
                "sortie": ["évacuation", "evacuation", "exit", "evacuer"],
                "exit": ["évacuation", "evacuation", "sortie", "evacuer"],
                
                # Alerte et variations
                "alerte": ["alarme", "alert", "warning", "signal", "sonnette", "alarme"],
                "alarme": ["alerte", "alert", "warning", "signal", "sonnette"],
                "alert": ["alerte", "alarme", "warning", "signal"],
                "warning": ["alerte", "alarme", "alert", "signal"],
                
                # Responsable et variations
                "responsable": ["chef", "manager", "supervisor", "directeur", "direction", "dirigeant", "boss"],
                "chef": ["responsable", "manager", "supervisor", "directeur", "boss"],
                "manager": ["responsable", "chef", "supervisor", "directeur", "boss"],
                "directeur": ["responsable", "chef", "manager", "supervisor", "direction"],
                
                # Procédure et variations
                "procédure": ["procedure", "protocol", "protocole", "consigne", "instruction", "procedur"],
                "procedure": ["procédure", "protocol", "protocole", "consigne", "instruction"],
                "protocol": ["procédure", "procedure", "protocole", "consigne"],
                "protocole": ["procédure", "procedure", "protocol", "consigne"],
                "consigne": ["procédure", "procedure", "instruction", "protocol"],
                "instruction": ["procédure", "procedure", "consigne", "protocol"],
                
                # Services d'urgence
                "samu": ["15", "ambulance", "medical", "emergency", "urgence", "medecin"],
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
                "réagir": ["faire", "agir", "do", "react", "reaction"]
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
        if any(word in question_lower for word in ["urgence", "emergency", "accident", "urgent", "urgance", "urgense"]):
            expanded_keywords.extend(["15", "18", "17", "112", "samu", "pompiers", "police", "secours", "help", "aide"])
        
        # Contexte de communication
        if any(word in question_lower for word in ["numéro", "numero", "téléphone", "contact", "appeler", "phone", "tel"]):
            expanded_keywords.extend(["tel", "phone", "appel", "joindre", "poste", "extension", "contact"])
        
        # Contexte de sécurité
        if any(word in question_lower for word in ["sécurité", "securite", "safety", "security"]):
            expanded_keywords.extend(["responsable", "procedure", "consigne", "évacuation", "alerte"])
        
        # Contexte d'équipement
        if any(word in question_lower for word in ["extincteur", "défibrillateur", "equipment", "matériel"]):
            expanded_keywords.extend(["où", "trouve", "located", "situé", "endroit"])
        
        # Contexte de localisation
        if any(word in question_lower for word in ["où", "ou", "where", "trouve", "located"]):
            expanded_keywords.extend(["situé", "position", "endroit", "lieu", "place"])
        
        return list(set(expanded_keywords))  # Supprimer les doublons
    
    def _find_relevant_passages(self, content: str, keywords: List[str], question: str) -> List[Dict[str, Any]]:
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
        sentences = re.split(r'[.!?]+', content)
        sentences = [s.strip() for s in sentences if len(s.strip()) > 15]  # Abaissé pour capturer plus de phrases
        
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
                ("urgence", "numéro"), ("urgence", "numero"), ("urgence", "téléphone"),
                ("urgence", "contact"), ("urgence", "appel"), ("urgence", "poste"),
                ("sécurité", "poste"), ("sécurité", "responsable"), ("sécurité", "chef"),
                ("accident", "procédure"), ("accident", "secours"), ("accident", "alerte"),
                ("défibrillateur", "localisation"), ("défibrillateur", "emplacement"),
                ("extincteur", "localisation"), ("extincteur", "emplacement"),
                ("15", "samu"), ("18", "pompiers"), ("17", "police"), ("112", "urgence")
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
                r'\b(en cas d\'urgence|urgence)\b',
                r'\b(numéro|numero|n°|no)\s*(d\')?urgence\b',
                r'\b(contacter|appeler|joindre)\b',
                r'\b(\d{2,4})\s*(poste|ext|extension)?\b',  # Numéros de téléphone/poste
                r'\b(15|18|17|112)\b',  # Numéros d'urgence
                r'\b(samu|pompiers|police|secours)\b',
                r'\b(chef|responsable|manager)\s*(de)?\s*(sécurité|securite|site|équipe)\b'
            ]
            
            for pattern in emergency_patterns:
                if re.search(pattern, sentence_lower):
                    relevance_score += 3
            
            # Bonus pour les phrases qui contiennent des numéros
            if re.search(r'\b\d{2,5}\b', sentence):
                relevance_score += 1
            
            # Bonus pour les phrases qui commencent par des mots importants
            if any(sentence_lower.startswith(word) for word in ["urgence", "en cas", "pour", "appeler", "contacter", "numéro"]):
                relevance_score += 1
            
            # Malus pour les phrases très courtes (sauf si elles contiennent des numéros)
            if len(sentence) < 30 and not re.search(r'\b\d{2,5}\b', sentence):
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
                
                passages.append({
                    "passage": sentence,
                    "context": context,
                    "relevance": relevance_score,
                    "matched_keywords": matched_keywords
                })
        
        return passages
    
    def _generate_general_document_response(self, question: str, stored_docs: Dict[str, Any]) -> str:
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
        
        if any(word in question_lower for word in ["urgence", "numéro", "téléphone", "contact", "appeler"]):
            suggestions.append("• Cherchez des termes comme 'contact', 'téléphone', 'urgence', 'poste', 'responsable'")
            suggestions.append("• Recherchez des numéros (15, 18, 17, 112, ou numéros internes)")
            suggestions.append("• Demandez-moi 'procédure d'urgence' ou 'contacts importants'")
        
        if any(word in question_lower for word in ["sécurité", "accident", "procédure"]):
            suggestions.append("• Recherchez 'sécurité', 'procédure', 'consignes', 'en cas d'urgence'")
            suggestions.append("• Demandez-moi 'mesures de sécurité' ou 'que faire en cas d'accident'")
        
        if any(word in question_lower for word in ["responsable", "chef", "manager"]):
            suggestions.append("• Cherchez 'responsable', 'chef', 'manager', 'superviseur'")
            suggestions.append("• Demandez-moi 'qui contacter' ou 'organigramme'")
        
        if not suggestions:
            suggestions = [
                "• Reformulez votre question avec d'autres termes",
                "• Demandez-moi un résumé général du document",
                "• Posez une question plus précise sur un aspect particulier",
                "• Demandez-moi de rechercher un mot-clé spécifique"
            ]
        
        response += "Voici comment je peux vous aider :\n\n"
        response += "\n".join(suggestions)
        
        # Ajouter quelques mots-clés du document pour aider l'utilisateur
        first_doc = list(stored_docs.values())[0]
        content = first_doc["content"]
        
        # Extraire des mots-clés pertinents du document
        words = re.findall(r'\b\w{4,}\b', content.lower())
        
        # Filtrer les mots-clés pertinents
        relevant_words = []
        important_categories = [
            "urgence", "sécurité", "accident", "procédure", "responsable", "chef",
            "téléphone", "contact", "poste", "numéro", "appeler", "joindre",
            "défibrillateur", "extincteur", "secours", "évacuation", "alerte",
            "travail", "bureau", "site", "équipe", "service", "département"
        ]
        
        word_freq = {}
        for word in words:
            if word in important_categories or any(cat in word for cat in important_categories):
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
                "ConversationMemory"
            ],
            "features": [
                "Code generation",
                "Natural language understanding",
                "Conversation memory",
                "Multi-language support",
                "100% local operation"
            ]
        }
    
    def _select_primary_intent(self, intent_scores: Dict[str, float], user_input: str) -> Tuple[str, float]:
        """Sélectionne l'intention primaire avec logique contextuelle améliorée"""
        if not intent_scores:
            return "unknown", 0.0
        
        # Améliorer la détection des demandes de résumé
        user_lower = user_input.lower().strip()
        
        # PRIORITÉ 1 : Vérifier les questions d'identité AVANT tout (même avec des docs en mémoire)
        identity_keywords = ["qui es-tu", "qui es tu", "qui êtes vous", "comment tu t'appelles", "ton nom", "tu es qui", "tu es quoi"]
        
        # PRIORITÉ 1.5 : Questions "ça va" et variantes (AVANT capability_keywords)
        how_are_you_keywords = ["comment vas tu", "comment ça va", "ça va", "sa va", "ca va", "tu vas bien", "vous allez bien"]
        
        capability_keywords = ["que peux tu", "que sais tu", "tes capacités", "tu peux faire", "que fais-tu", 
                              "à quoi tu sers", "à quoi sert tu", "à quoi sers tu", "à quoi tu sert", 
                              "tu sers à quoi", "tu sert à quoi", "tu sers a quoi", "tu sert a quoi"]
        
        if any(keyword in user_lower for keyword in identity_keywords):
            return "identity_question", 1.0
            
        # Détecter "ça va" avec contexte plus précis
        if any(keyword in user_lower for keyword in how_are_you_keywords):
            # Si c'est juste "ça va" sans "et toi", c'est probablement une affirmation
            if user_lower.strip() in ["ça va", "sa va", "ca va"] and "et toi" not in user_lower:
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
        if self._has_documents_in_memory():
            # Mots-clés qui indiquent clairement une question sur un document
            doc_indicators = [
                "résume", "resume", "résumé", "explique", "analyse", 
                "que dit", "contient", "résume le pdf", "résume le doc",
                "résume le document", "résume le fichier"
            ]
            
            # Détecter "résume le pdf" même si seul
            if any(indicator in user_lower for indicator in doc_indicators):
                # Si c'est spécifiquement "résume le pdf" ou "résume le doc"
                if any(phrase in user_lower for phrase in ["résume le pdf", "résume le doc", "résume le document"]):
                    return "document_question", 1.0  # Force high confidence
                
                # Ou si c'est juste "résume" et qu'on a des documents
                elif user_lower in ["résume", "resume", "résumé"]:
                    return "document_question", 0.9
                
                # Autres questions sur documents
                else:
                    return "document_question", 0.8
        
        # PRIORITÉ 3.5 : Questions de programmation avec détection spécifique
        programming_patterns = [
            "comment créer", "comment utiliser", "comment faire", "comment déclarer",
            "liste en python", "dictionnaire en python", "fonction en python", 
            "variable en python", "boucle en python", "condition en python",
            "classe en python", "objet en python", "python", "programmation",
            "créer une liste", "créer un dictionnaire", "créer une fonction",
            "faire une boucle", "utiliser if", "utiliser for", "utiliser while"
        ]
        
        if any(pattern in user_lower for pattern in programming_patterns):
            # Vérifier si c'est vraiment une question de programmation
            if any(word in user_lower for word in ["comment", "créer", "utiliser", "faire", "python", "liste", "dictionnaire", "fonction", "variable", "boucle", "condition", "classe"]):
                return "programming_question", 0.9
        
        # PRIORITÉ 3.6 : Questions générales avec structure "c'est quoi", "qu'est-ce que"
        general_question_patterns = [
            "c'est quoi", "c est quoi", "quest ce que", "qu'est-ce que", "qu est ce que",
            "que signifie", "ça veut dire quoi", "ca veut dire quoi", "définition de",
            "explique moi", "peux tu expliquer", "dis moi ce que c'est"
        ]
        
        if any(pattern in user_lower for pattern in general_question_patterns):
            return "general_question", 0.9
        
        # PRIORITÉ 4 : Sélection normale par score le plus élevé
        best_intent = max(intent_scores.items(), key=lambda x: x[1])
        return best_intent[0], best_intent[1]
    
    def _has_documents_in_memory(self) -> bool:
        """Vérifie si des documents sont en mémoire"""
        return len(self.conversation_memory.get_document_content()) > 0
    
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