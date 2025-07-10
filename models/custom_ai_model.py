"""
Modèle IA personnalisé local - Architecture modulaire
Intègre tous les modules pour une IA 100% locale avec mémoire de conversation
"""

import re
import json
import time
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime

from .base_ai import BaseAI
from .linguistic_patterns import LinguisticPatterns
from .knowledge_base import KnowledgeBase
from .generators import CodeGenerator
from .reasoning_engine import ReasoningEngine
from .conversation_memory import ConversationMemory


class CustomAIModel(BaseAI):
    """Modèle IA personnalisé avec architecture modulaire et mémoire persistante"""
    
    def __init__(self, conversation_memory: ConversationMemory = None):
        super().__init__()
        self.name = "Assistant IA Local"
        self.version = "2.2.0"
        
        # Modules spécialisés
        self.linguistic_patterns = LinguisticPatterns()
        self.knowledge_base = KnowledgeBase()
        self.code_generator = CodeGenerator()
        self.reasoning_engine = ReasoningEngine()
        self.conversation_memory = conversation_memory or ConversationMemory()
        
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
        
        # Réponses personnalisées pour l'identité
        self.identity_responses = {
            "basic": [
                "Je suis votre assistant IA local ! Je m'appelle Assistant IA Local et je suis conçu pour vous aider avec la programmation, les questions techniques, et bien plus encore.",
                "Bonjour ! Je suis un assistant IA qui fonctionne entièrement en local sur votre machine. Je peux vous aider avec le code, répondre à vos questions, et discuter avec vous.",
                "Salut ! Moi c'est Assistant IA Local. Je suis votre compagnon virtuel pour la programmation et les discussions techniques. Je tourne uniquement en local, pas besoin d'internet !",
                "Je suis votre assistant personnel ! Un modèle IA local qui peut coder, expliquer, et discuter avec vous. J'apprends de nos conversations pour mieux vous comprendre."
            ],
            "detailed": [
                "Je suis Assistant IA Local, version 2.2.0. Je suis un modèle d'intelligence artificielle conçu pour fonctionner entièrement en local, sans dépendance externe. Je peux générer du code, expliquer des concepts, et avoir des conversations naturelles avec vous.",
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
        
        print(f"✅ {self.name} v{self.version} initialisé avec succès")
        print(f"🧠 Modules chargés : Linguistique, Base de connaissances, Génération de code, Raisonnement, Mémoire")
        print(f"💾 Mémoire de conversation activée")
    
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
            doc_type = "document Word"
        
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
    
    def _generate_contextual_response(self, user_input: str, intent: str, confidence: float,
                                    context: Dict[str, Any], similar_question: Optional[Any] = None) -> str:
        """Génère une réponse contextuelle basée sur l'intention et l'historique"""
        
        # Gestion des questions similaires récentes
        if similar_question and intent not in ["greeting", "thank_you", "goodbye"]:
            time_ago = time.time() - similar_question.timestamp
            if time_ago < 300:  # 5 minutes
                # Éviter la duplication si la requête est exactement la même
                if user_input.lower().strip() == similar_question.user_message.lower().strip():
                    # Réponse directe sans indiquer qu'il s'agit d'une question similaire
                    return similar_question.ai_response
                else:
                    # Réponse pour une question similaire mais non identique
                    return f"Je viens de répondre à une question similaire il y a {int(time_ago//60)} minutes. Ma réponse était : {similar_question.ai_response[:200]}..."
        
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
        elif intent == "capabilities_question":
            return self._generate_capabilities_response(user_input, context)
        elif intent == "greeting":
            return self._generate_greeting_response(user_input, context)
        elif intent == "how_are_you":
            return self._generate_how_are_you_response(context)
        elif intent == "affirm_doing_well":
            return self._generate_affirm_doing_well_response(context)
        elif intent == "compliment":
            return self._generate_compliment_response(user_input, context)
        elif intent == "code_generation" or intent == "code_request":
            return self._generate_code_response(user_input, context)
        elif intent == "code_question":
            # Vérifier s'il y a du code en mémoire
            stored_docs = self.conversation_memory.get_document_content()
            code_docs = {name: doc for name, doc in stored_docs.items() 
                        if doc and doc.get("type") == "code"}
            if code_docs:
                return self._answer_code_question(user_input, code_docs)
            else:
                return "Je n'ai pas de code en mémoire à analyser. Traitez d'abord un fichier de code."
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
            return self._generate_affirmation_response(context)
        elif intent == "negation":
            return self._generate_negation_response(context)
        else:
            return self._generate_default_response(user_input, context)
    
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
        """Réponse sur les capacités"""
        base_response = """Je peux vous aider avec plusieurs choses :

🔍 **Analyse de documents :** Je peux lire et résumer vos fichiers PDF et Word
💻 **Programmation :** Je génère du code Python, JavaScript, HTML/CSS
💬 **Conversation :** Je réponds à vos questions et discute naturellement
🧠 **Raisonnement :** J'analyse des problèmes et propose des solutions

Tout fonctionne en local sur votre machine - aucune donnée n'est envoyée à l'extérieur !"""
        
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
        if "wesh" in user_input.lower() or "yo" in user_input.lower():
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
    
    def _generate_how_are_you_response(self, context: Dict[str, Any]) -> str:
        """Génère une réponse à 'comment ça va'"""
        responses = [
            "Ça va très bien, merci ! Je suis toujours prêt à aider ! Et vous, comment allez-vous ?",
            "Tout va bien ! Je suis en pleine forme et prêt à répondre à vos questions ! 😊",
            "Ça roule ! Mon système fonctionne parfaitement et j'ai hâte de vous aider !",
            "Excellent ! J'ai tous mes modules qui fonctionnent à merveille ! Et vous ?"
        ]
        
        base_response = self._get_random_response(responses)
        
        # Ajout d'informations sur la session
        session_duration = context.get("session_duration", 0)
        if session_duration > 300:  # Plus de 5 minutes
            minutes = int(session_duration // 60)
            base_response += f"\n\nNous discutons depuis {minutes} minutes maintenant, c'est chouette !"
        
        return base_response
    
    def _generate_affirm_doing_well_response(self, context: Dict[str, Any]) -> str:
        """Génère une réponse aux affirmations 'ça va'"""
        responses = [
            "Super ! Content de savoir que ça va bien ! 😊 Comment puis-je vous aider ?",
            "Parfait ! C'est toujours bien d'aller bien ! En quoi puis-je vous assister ?",
            "Excellent ! Heureux de l'entendre ! Que puis-je faire pour vous ?",
            "Génial ! Ça fait plaisir ! Sur quoi voulez-vous que je vous aide ?",
            "Cool ! Et maintenant, que puis-je faire pour vous rendre service ?"
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
        help_text = """🤖 Aide - Assistant IA Local

💬 Pour discuter : Posez-moi vos questions naturellement
📄 Pour les documents : Utilisez les boutons pour traiter vos PDF/DOCX, puis demandez-moi de les résumer ou de répondre à des questions
💻 Pour le code : Traitez vos fichiers Python, puis demandez-moi de les expliquer ou de les améliorer
🎯 Exemples :
• "Résume le document" - après avoir traité un PDF
• "Explique ce code" - après avoir traité un fichier Python
• "Génère une fonction pour..." - pour créer du code
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
        
        # Si ça ressemble à une demande de code
        if any(word in user_lower for word in ["génère", "crée", "code", "fonction", "script"]):
            try:
                code_response = self.code_generator.generate_code(user_input)
                return f"Voici ce que j'ai généré pour vous :\n\n{code_response}"
            except:
                return "Je peux générer du code ! Soyez plus spécifique : voulez-vous une fonction, une classe, ou un script complet ?"
        
        # Si ça ressemble à une question générale
        elif any(word in user_lower for word in ["comment", "pourquoi", "qu'est-ce", "quoi"]):
            return "C'est une bonne question ! Je peux vous aider à y réfléchir. Pouvez-vous me donner plus de contexte ou être plus spécifique ?"
        
        # Réponse encourageante par défaut
        return "Je ne suis pas sûr de bien comprendre. Pouvez-vous reformuler ? Je peux vous aider avec l'analyse de documents, la génération de code, ou simplement discuter !"
    
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
        doc_type = "PDF" if is_pdf else "document Word"
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
            doc_type_display = "document Word"
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
        identity_keywords = ["qui es-tu", "qui es tu", "qui êtes vous", "comment tu t'appelles", "ton nom", "tu es qui"]
        capability_keywords = ["que peux tu", "que sais tu", "tes capacités", "tu peux faire", "que fais-tu"]
        
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
        """Répond aux questions sur les documents avec gestion améliorée"""
        if not stored_docs:
            return "Je n'ai pas de documents en mémoire pour répondre à votre question."
        
        user_lower = user_input.lower().strip()
        
        # Gestion des demandes de résumé avec sélection de document
        resume_keywords = ["résume", "resume", "résumé"]
        
        if any(keyword in user_lower for keyword in resume_keywords):
            
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
                    return self._create_universal_summary(content, doc_name, "document Word")
                else:
                    return "Je n'ai pas de document Word en mémoire."
            
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
                            doc_type = "document Word"
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
                    doc_type = "document Word"
                else:
                    doc_type = "document"
                
                return self._create_universal_summary(doc_content, doc_name, doc_type)
            else:
                # Plusieurs documents, faire un résumé pour chacun
                summaries = []
                for doc_name, doc_data in target_docs.items():
                    doc_content = doc_data["content"]
                    doc_type = "PDF" if "pdf" in doc_name.lower() else "document Word"
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
        
        # Règles spéciales pour les questions sur les documents
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
        
        # Sélection normale par score le plus élevé
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