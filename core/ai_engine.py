
"""
Moteur principal de l'IA personnelle
Gère l'orchestration entre les différents modules
"""

import asyncio

import logging
from typing import Dict, Any, Optional, List
from pathlib import Path

from .config import AI_CONFIG
from .conversation import ConversationManager
from models.custom_ai_model import CustomAIModel
from models.conversation_memory import ConversationMemory
from processors.pdf_processor import PDFProcessor
from processors.docx_processor import DOCXProcessor
from processors.code_processor import CodeProcessor
from generators.document_generator import DocumentGenerator
from models.generators import CodeGenerator
from utils.logger import setup_logger
from utils.file_manager import FileManager

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
            "current_document": None
        }

        # Initialisation de la mémoire et du gestionnaire de conversations
        self.conversation_memory = ConversationMemory()
        self.conversation_manager = ConversationManager(memory=self.conversation_memory)
        
        # Modèle IA local personnalisé avec mémoire de conversation (100% autonome)
        try:
            from models.custom_ai_model import CustomAIModel
            from models.ml_faq_model import MLFAQModel
            self.local_ai = CustomAIModel(conversation_memory=self.conversation_memory)
            self.ml_ai = MLFAQModel()  # Modèle ML local (TF-IDF)
            # Debug supprimé : plus de log sur le chargement de la base FAQ/ML
            self.model = self.local_ai  # Alias pour compatibilité avec l'interface graphique
            self.logger.info("✅ Modèle IA local avec mémoire initialisé")
            self.logger.info("✅ Modèle ML (TF-IDF) initialisé")
            # Initialisation du gestionnaire de LLM
            self.llm_manager = self.local_ai  # Pour compatibilité avec les fonctions qui utilisent llm_manager
        except Exception as e:
            self.logger.error(f"❌ Erreur lors de l'initialisation du modèle IA : {e}")
            # Fallback sur l'ancien système
            self.local_ai = CustomAIModel()
            self.ml_ai = None
            self.model = self.local_ai
            self.llm_manager = self.local_ai
        
        # Processeurs
        self.pdf_processor = PDFProcessor()
        self.docx_processor = DOCXProcessor()
        self.code_processor = CodeProcessor()
        
        # Générateurs
        self.document_generator = DocumentGenerator()
        self.code_generator = CodeGenerator()
        
        self.logger.info("Moteur IA initialisé avec succès")
    
    def process_text(self, text: str) -> str:
        """
        Traite un texte en donnant la priorité à la FAQ ML (TF-IDF), puis utilise la logique avancée (process_query) pour router la demande (explication code, etc).
        """
        try:
            self.logger.info(f"[DEBUG] process_text: question utilisateur brute: {repr(text)}")
            print(f"[AIEngine] Appel FAQ pour: '{text}'")
            # 1. Tenter la FAQ ML d'abord
            response_ml = None
            if self.ml_ai is not None:
                try:
                    self.logger.info(f"[DEBUG] Passage de la question à FAQ/ML: {repr(text)}")
                    response_ml = self.ml_ai.predict(text)
                    self.logger.info(f"[DEBUG] ML model response: {repr(response_ml)}")
                except Exception as e:
                    self.logger.warning(f"Erreur modèle ML: {e}")
            else:
                print(f"[AIEngine] Modèle FAQ ML non initialisé. Passage direct au modèle custom.")

            # Priorité absolue : si la FAQ locale a une réponse, on la retourne DIRECTEMENT
            if response_ml is not None and str(response_ml).strip():
                print(f"[AIEngine] Réponse trouvée dans la FAQ locale. Priorité absolue. Pas de recherche internet ni d'appel au modèle custom.")
                try:
                    self.conversation_manager.add_exchange(text, {"message": response_ml})
                except Exception as e:
                    self.logger.warning(f"Impossible de sauvegarder la conversation: {e}")
                return response_ml

            # Sinon, router via process_query pour bénéficier de la logique avancée (explication code, etc)
            try:
                # Utilise asyncio pour appeler la méthode async
                loop = None
                try:
                    loop = asyncio.get_event_loop()
                except RuntimeError:
                    loop = None
                if loop and loop.is_running():
                    # Si déjà dans un event loop (rare hors notebook), patch avec nest_asyncio si dispo
                    try:
                        import nest_asyncio  # type: ignore
                        nest_asyncio.apply()
                    except ImportError:
                        self.logger.warning("nest_asyncio non installé : l'appel async peut échouer si déjà dans un event loop.")
                    future = self.process_query(text)
                    response = loop.run_until_complete(future)
                else:
                    response = asyncio.run(self.process_query(text))
                # On sauvegarde l'échange
                try:
                    self.conversation_manager.add_exchange(text, response)
                except Exception as e:
                    self.logger.warning(f"Impossible de sauvegarder la conversation: {e}")
                return response.get("message", "[Aucune réponse générée]")
            except Exception as e:
                self.logger.error(f"Erreur lors de l'appel à process_query: {e}")
                self.logger.warning("Utilisation du fallback response (process_query)")
                fallback_response = self._generate_fallback_response(text)
                return fallback_response
        except Exception as e:
            self.logger.error(f"Erreur dans process_text: {e}")
            self.logger.warning("Utilisation du fallback response (global)")
            fallback_response = self._generate_fallback_response(text)
            return fallback_response

    def _merge_responses(self, response_custom, response_ml):
        """
        Donne la priorité à la FAQ ML : si une réponse MLFAQ existe, elle est utilisée, sinon on utilise la réponse custom.
        """
        if response_ml is not None and str(response_ml).strip():
            return str(response_ml)
        return response_custom
    
    def _generate_simple_function(self, text: str) -> str:
        """Génère une fonction simple basée sur la demande"""
        if "factorielle" in text.lower():
            return """🔧 Fonction générée :

```python
def factorielle(n):
    \"\"\"
    Calcule la factorielle d'un nombre
    
    Args:
        n (int): Nombre dont on veut la factorielle
        
    Returns:
        int: Factorielle de n
    \"\"\"
    if n < 0:
        raise ValueError("La factorielle n'est pas définie pour les nombres négatifs")
    elif n == 0 or n == 1:
        return 1
    else:
        return n * factorielle(n - 1)

# Exemple d'utilisation
print(factorielle(5))  # Output: 120
```"""
        elif "fibonacci" in text.lower():
            return """🔧 Fonction générée :

```python
def fibonacci(n):
    \"\"\"
    Calcule le n-ième nombre de Fibonacci
    
    Args:
        n (int): Position dans la séquence
        
    Returns:
        int: n-ième nombre de Fibonacci
    \"\"\"
    if n <= 0:
        return 0
    elif n == 1:
        return 1
    else:
        return fibonacci(n-1) + fibonacci(n-2)

# Exemple d'utilisation
for i in range(10):
    print(f"F({i}) = {fibonacci(i)}")
```"""
        else:
            return f"""🔧 Fonction générée basée sur votre demande :

```python
def ma_fonction():
    \"\"\"
    Fonction générée automatiquement
    Basée sur : {text}
    \"\"\"
    # TODO: Implétez votre logique ici
    print("Fonction créée avec succès !")
    return True

# Exemple d'utilisation
ma_fonction()
```
💡 Pour une génération plus précise, décrivez exactement ce que doit faire la fonction."""
    
    def _generate_simple_class(self, text: str) -> str:
        """Génère une classe simple basée sur la demande"""
        if "personne" in text.lower() or "person" in text.lower():
            return """🏗️ Classe générée :

```python
class Personne:
    \"\"\"
    Classe représentant une personne
    \"\"\"
    
    def __init__(self, nom, age):
        \"\"\"
        Initialise une nouvelle personne
        
        Args:
            nom (str): Nom de la personne
            age (int): Âge de la personne
        \"\"\"
        self.nom = nom
        self.age = age
    
    def se_presenter(self):
        \"\"\"Présente la personne\"\"\"
        return f"Bonjour, je suis {self.nom} et j'ai {self.age} ans."
    
    def avoir_anniversaire(self):
        \"\"\"Incrémente l'âge d'un an\"\"\"
        self.age += 1
        return f"Joyeux anniversaire ! {self.nom} a maintenant {self.age} ans."

# Exemple d'utilisation
personne = Personne("Alice", 25)
print(personne.se_presenter())
print(personne.avoir_anniversaire())
```"""
        else:
            return f"""🏗️ Classe générée basée sur votre demande :

```python
class MaClasse:
    \"\"\"
    Classe générée automatiquement
    Basée sur : {text}
    \"\"\"
    
    def __init__(self):
        \"\"\"Initialise la classe\"\"\"
        self.nom = "MaClasse"
        self.active = True
    
    def action(self):
        \"\"\"Méthode d'action principale\"\"\"
        if self.active:
            return "Action exécutée avec succès !"
        return "Classe inactive"
    
    def __str__(self):
        \"\"\"Représentation string de la classe\"\"\"
        return f"{self.nom} - Active: {self.active}"

# Exemple d'utilisation
objet = MaClasse()
print(objet)
print(objet.action())
```

💡 Pour une génération plus précise, décrivez les attributs et méthodes souhaités."""
    
    def _generate_code_from_text(self, text: str) -> str:
        """Génère du code basé sur une description textuelle"""
        return f"""💻 Code généré basé sur votre demande :

```python
# Code basé sur : {text}

def solution():
    \"\"\"
    Solution générée automatiquement
    \"\"\"
    # TODO: Implétez votre solution ici
    print("Code généré avec succès !")
    
    # Exemple de logique de base
    resultat = "Mission accomplie"
    return resultat

# Exécution
if __name__ == "__main__":
    print(solution())
```

💡 Pour du code plus spécifique, donnez plus de détails sur ce que vous voulez accomplir."""
    
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
        if any(word in text_lower for word in ["salut", "bonjour", "hello", "hi", "bonsoir"]):
            return "Salut ! Comment ça va ? En quoi puis-je t'aider ?"
        
        # Questions d'aide
        if "help" in text_lower or "aide" in text_lower:
            return "Je peux t'aider avec la génération de code Python, l'analyse de documents, et répondre à tes questions techniques. Que veux-tu faire ?"
        
        # Demandes de code
        elif "génér" in text_lower or "créer" in text_lower or "fonction" in text_lower or "classe" in text_lower:
            if "fonction" in text_lower:
                return self._generate_simple_function(text)
            elif "classe" in text_lower:
                return self._generate_simple_class(text)
            else:
                return "Je peux générer du code pour toi ! Tu veux une fonction ou une classe ? Dis-moi ce que tu veux créer."
        
        # Questions sur l'IA
        elif any(phrase in text_lower for phrase in ["qui es-tu", "que fais-tu", "qu'est-ce que tu fais"]):
            return "Je suis ton assistant IA local. Je peux coder, analyser des documents et répondre à tes questions. Qu'est-ce qui t'intéresse ?"
        
        # Réponse générale naturelle
        else:
            return f"Je vois ! Et en quoi puis-je t'aider avec ça ? Tu veux que je génère du code, que je t'explique quelque chose, ou autre chose ?"

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
            "current_document": None
        }
        
        self.logger.info("Conversation cleared")

    def initialize_llm(self) -> bool:
        """Initialise les modèles LLM - Mode entreprise local uniquement"""
        try:
            # En mode entreprise, nous utilisons uniquement le modèle local
            return hasattr(self, 'local_ai') and self.local_ai is not None
        except Exception as e:
            self.logger.error(f"Erreur initialisation LLM: {e}")
            return False

    async def process_query(self, query: str, context: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Traite une requête utilisateur
        
        Args:
            query: Question/demande de l'utilisateur
            context: Contexte additionnel (fichiers, historique, etc.)
            
        Returns:
            Réponse structurée de l'IA
        """
        try:
            self.logger.info(f"Traitement de la requête: {query[:100]}...")
            print(f"[AIEngine] Appel FAQ pour: '{query}' (async)")
            # 1. Tenter la FAQ ML d'abord
            response_ml = None
            if hasattr(self, 'ml_ai') and self.ml_ai is not None:
                try:
                    response_ml = self.ml_ai.predict(query)
                    self.logger.info(f"ML model response: {str(response_ml)[:50]}...")
                except Exception as e:
                    self.logger.warning(f"Erreur modèle ML: {e}")
            if response_ml is not None and str(response_ml).strip():
                # On sauvegarde l'échange
                try:
                    self.conversation_manager.add_exchange(query, {"message": response_ml})
                except:
                    self.logger.warning("Impossible de sauvegarder la conversation (FAQ async)")
                return {"type": "faq", "message": response_ml, "success": True}

            # 2. Sinon, routage normal
            # Analyse de la requête
            query_type = self._analyze_query_type(query)
            # Préparation du contexte
            full_context = self._prepare_context(query, context)
            # Traitement selon le type
            if query_type == "conversation":
                response = await self._handle_conversation(query, full_context)
            elif query_type == "file_processing":
                response = await self._handle_file_processing(query, full_context)
            elif query_type == "code_generation":
                response = await self._handle_code_generation(query, full_context)
            elif query_type == "document_generation":
                response = await self._handle_document_generation(query, full_context)
            else:
                response = await self._handle_general_query(query, full_context)
            # Sauvegarde dans l'historique
            self.conversation_manager.add_exchange(query, response)
            return response
        except Exception as e:
            self.logger.error(f"Erreur lors du traitement: {e}")
            return {
                "type": "error",
                "message": f"Désolé, une erreur s'est produite: {str(e)}",
                "success": False
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
        identity_keywords = ["qui es-tu", "qui es tu", "qui êtes vous", "comment tu t'appelles", "ton nom", "tu es qui", "tu es quoi"]
        capability_keywords = ["que peux tu", "que sais tu", "tes capacités", "tu peux faire", "que fais-tu", "comment vas tu", "comment ça va"]
        
        if any(keyword in query_lower for keyword in identity_keywords + capability_keywords):
            return "conversation"  # Questions sur l'IA elle-même
        
        # PRIORITÉ 2 : Vérifier si c'est un texte incompréhensible/aléatoire
        if len(query_lower) > 20 and not any(c.isspace() for c in query_lower[:20]):
            # Si plus de 20 caractères sans espaces = probablement du charabia
            return "conversation"
        
        # PRIORITÉ 3 : Vérifier si on a des documents et si la question les concerne SPÉCIFIQUEMENT
        if hasattr(self.local_ai, 'conversation_memory'):
            stored_docs = self.local_ai.conversation_memory.get_document_content()
            if stored_docs:
                # Mots-clés SPÉCIFIQUES pour questions sur les documents
                doc_question_keywords = [
                    "résume", "explique", "analyse", "qu'est-ce que", "que dit", 
                    "contenu", "parle", "traite", "sujet", "doc", "document", 
                    "pdf", "docx", "fichier", "code"
                ]
                if any(keyword in query_lower for keyword in doc_question_keywords):
                    return "file_processing"
        
        # PRIORITÉ 4 : Mots-clés pour la génération de code (NOUVEAU code, pas analyse)
        # Distinguer entre questions théoriques et demandes de génération
        question_words = ["comment", "qu'est-ce que", "c'est quoi", "que signifie", "explique", "expliquer"]
        is_theoretical_question = any(qword in query_lower for qword in question_words)
        
        code_generation_keywords = ["génère", "crée", "écris", "développe", "programme", "script", "fonction", "classe"]
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
            "user_context": context or {}
        }
        
        # Ajouter les documents stockés dans la mémoire
        if hasattr(self.local_ai, 'conversation_memory'):
            stored_docs = self.local_ai.conversation_memory.stored_documents
            if stored_docs:
                full_context["stored_documents"] = stored_docs
                full_context["document_order"] = self.local_ai.conversation_memory.document_order
                self.logger.info(f"Contexte enrichi avec {len(stored_docs)} documents stockés")
        
        return full_context
    
    async def _handle_conversation(self, query: str, context: Dict) -> Dict[str, Any]:
        """
        Gère les conversations générales
        """
        try:
            # Si on a des documents, les inclure dans le contexte
            prompt = query
            if 'stored_documents' in context and context['stored_documents']:
                prompt = f"""Contexte des documents disponibles:
                
"""
                for doc_name in context['stored_documents'].keys():
                    prompt += f"- {doc_name}\n"
                
                prompt += f"\nQuestion: {query}\n\nRéponds en tenant compte du contexte si pertinent."
            
            response = self.local_ai.generate_response(prompt)
            
            return {
                "type": "conversation",
                "message": response,
                "success": True
            }
        except Exception as e:
            self.logger.error(f"Erreur conversation: {e}")
            return {
                "type": "conversation",
                "message": f"Erreur lors de la conversation: {str(e)}",
                "success": False
            }
    
    async def _handle_file_processing(self, query: str, context: Dict) -> Dict[str, Any]:
        """
        Gère le traitement de fichiers et questions sur les documents - VERSION CORRIGÉE
        """
        try:
            query_lower = query.lower()
            
            # Récupérer les documents disponibles
            all_docs = context.get('stored_documents', {})
            document_order = context.get('document_order', [])
            
            # NOUVELLE LOGIQUE : Détecter le type de document demandé VS disponible
            requested_type = self._detect_requested_document_type(query_lower)
            available_types = self._get_available_document_types(all_docs)
            
            print(f"[DEBUG] Type demandé: {requested_type}")
            print(f"[DEBUG] Types disponibles: {available_types}")
            
            # VÉRIFICATION DE COHÉRENCE
            if requested_type and requested_type not in available_types:
                return self._generate_type_mismatch_response(requested_type, available_types, all_docs)
            
            # Déterminer le document cible selon le type demandé
            target_document = None
            
            if requested_type:
                # Chercher un document du type demandé
                target_document = self._find_document_by_type(all_docs, document_order, requested_type)
            
            # Gestion des références numériques (premier, deuxième, etc.)
            is_first_requested = any(term in query_lower for term in ['premier', '1er', '1ère', 'première', 'document 1', 'le 1'])
            is_second_requested = any(term in query_lower for term in ['deuxième', '2ème', '2eme', 'seconde', 'document 2', 'le 2'])
            is_last_requested = any(term in query_lower for term in ['dernier', 'dernière', 'last'])
            
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
            if target_document and target_document.lower().endswith('.py'):
                if any(word in query_lower for word in ['explique', 'analyse', 'code']):
                    return self._handle_python_code_explanation(target_document, all_docs)
            
            # Traitement standard pour les autres documents
            if target_document and target_document in all_docs:
                doc_data = all_docs[target_document]
                doc_content = doc_data.get('content') if isinstance(doc_data, dict) else str(doc_data)
                
                if doc_content:
                    # Générer le résumé approprié selon le type de document
                    doc_type = self._determine_document_type(target_document)
                    
                    # Déléguer la création du résumé au modèle IA local
                    response = self.local_ai._create_universal_summary(doc_content, target_document, doc_type)
                    
                    return {
                        "type": "file_processing",
                        "message": response,
                        "success": True
                    }
            
            return {
                "type": "file_processing",
                "message": "Aucun document approprié trouvé pour traiter votre demande.",
                "success": False
            }
            
        except Exception as e:
            print(f"❌ Erreur traitement fichier: {e}")
            return {
                "type": "file_processing",
                "message": f"Erreur lors du traitement : {str(e)}",
                "success": False
            }

    def _detect_requested_document_type(self, query_lower: str) -> Optional[str]:
        """
        Détecte le type de document spécifiquement demandé dans la requête
        
        Returns:
            'pdf', 'docx', 'code', ou None si pas spécifique
        """
        # Détection PDF
        if any(term in query_lower for term in ['pdf', 'le pdf', 'du pdf', 'ce pdf']):
            return 'pdf'
        
        # Détection DOCX/Word
        if any(term in query_lower for term in ['docx', 'doc', 'word', 'le docx', 'du docx', 'le doc', 'du doc']):
            return 'docx'
        
        # Détection Code
        if any(term in query_lower for term in ['code', 'py', 'python', 'script', 'programme', 'le code', 'du code']):
            return 'code'
        
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
        
        if doc_name_lower.endswith('.pdf'):
            return 'pdf'
        elif doc_name_lower.endswith(('.docx', '.doc')):
            return 'docx'
        elif doc_name_lower.endswith(('.py', '.js', '.html', '.css', '.java', '.cpp', '.c')):
            return 'code'
        elif isinstance(doc_data, dict) and doc_data.get('type') == 'code':
            return 'code'
        else:
            # Par défaut, considérer comme document texte
            return 'docx'

    def _find_document_by_type(self, all_docs: Dict, document_order: List, requested_type: str) -> Optional[str]:
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

    def _generate_type_mismatch_response(self, requested_type: str, available_types: List[str], all_docs: Dict) -> Dict[str, Any]:
        """
        Génère une réponse quand le type demandé n'est pas disponible
        """
        # Mappage pour un langage plus naturel
        type_names = {
            'pdf': 'fichier PDF',
            'docx': 'document Word/DOCX', 
            'code': 'fichier de code'
        }
        
        requested_name = type_names.get(requested_type, requested_type)
        
        # Construire la liste des documents disponibles
        available_docs = []
        for doc_name in all_docs.keys():
            doc_type = self._determine_document_type(doc_name, all_docs[doc_name])
            type_name = type_names.get(doc_type, doc_type)
            available_docs.append(f"• **{doc_name}** ({type_name})")
        
        available_names = [type_names.get(t, t) for t in available_types]
        
        response = f"❌ **Document non trouvé**\n\n"
        response += f"Vous demandez l'analyse d'un **{requested_name}**, mais je n'ai pas ce type de document en mémoire.\n\n"
        
        if available_docs:
            response += f"📁 **Documents actuellement disponibles :**\n"
            response += "\n".join(available_docs)
            response += f"\n\n💡 **Suggestion :** Reformulez votre demande en utilisant le bon type :\n"
            
            if 'pdf' in available_types:
                response += f"• \"résume le PDF\" ou \"explique le PDF\"\n"
            if 'docx' in available_types:
                response += f"• \"résume le DOCX\" ou \"explique le document\"\n"
            if 'code' in available_types:
                response += f"• \"explique le code\" ou \"analyse le Python\"\n"
        else:
            response += f"Aucun document n'est actuellement en mémoire."
        
        return {
            "type": "file_processing",
            "message": response,
            "success": False
        }

    def _handle_python_code_explanation(self, target_document: str, all_docs: Dict) -> Dict[str, Any]:
        """
        Gère l'explication détaillée des fichiers Python
        """
        try:
            doc_data = all_docs.get(target_document, {})
            doc_content = doc_data.get('content') if isinstance(doc_data, dict) else str(doc_data)
            
            if not doc_content:
                return {
                    "type": "file_processing", 
                    "message": f"Le fichier {target_document} semble vide.",
                    "success": False
                }
            
            # Créer un fichier temporaire pour l'analyse
            import os, tempfile
            with tempfile.NamedTemporaryFile('w', delete=False, suffix='.py', encoding='utf-8') as tmpf:
                tmpf.write(doc_content)
                tmp_path = tmpf.name
            
            try:
                # Utiliser le code_processor pour l'explication détaillée
                explanation = self.code_processor.generate_detailed_explanation(
                    tmp_path, 
                    real_file_name=os.path.basename(target_document)
                )
                
                return {
                    "type": "file_processing",
                    "message": explanation,
                    "success": True
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
                "success": False
            }
    
    async def _handle_code_generation(self, query: str, context: Dict) -> Dict[str, Any]:
        """
        Gère la génération de code
        """
        try:
            # Générer le code sans await (methode sync)
            code = self.code_generator.generate_code(query, context)
            
            # Créer un message d'accompagnement intelligent
            language = self._detect_code_language(query)
            accompaniment = self._create_code_accompaniment(query, language)
            
            # Formater la réponse complète
            full_response = f"{accompaniment}\n\n```{language}\n{code}\n```"
            
            return {
                "type": "code_generation",
                "code": code,
                "message": full_response,
                "success": True
            }
        except Exception as e:
            self.logger.error(f"Erreur génération code: {e}")
            return {
                "type": "code_generation", 
                "message": f"❌ Erreur lors de la génération de code: {str(e)}",
                "success": False
            }
    
    async def _handle_document_generation(self, query: str, context: Dict) -> Dict[str, Any]:
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
                "success": True
            }
        except Exception as e:
            self.logger.error(f"Erreur génération document: {e}")
            return {
                "type": "document_generation",
                "message": f"Erreur lors de la génération de document: {str(e)}",
                "success": False
            }
    
    async def _handle_general_query(self, query: str, context: Dict) -> Dict[str, Any]:
        """
        Gère les requêtes générales
        """
        try:
            # Construire le prompt avec contexte si disponible
            prompt = query
            if 'stored_documents' in context and context['stored_documents']:
                prompt = f"""Contexte des documents disponibles:
                
"""
                for doc_name in context['stored_documents'].keys():
                    prompt += f"- {doc_name}\n"
                
                prompt += f"\nQuestion: {query}\n\nRéponds en tenant compte du contexte si pertinent."
            
            response = self.local_ai.generate_response(prompt)
            
            return {
                "type": "general",
                "message": response,
                "success": True
            }
        except Exception as e:
            self.logger.error(f"Erreur requête générale: {e}")
            return {
                "type": "general",
                "message": f"Erreur lors du traitement: {str(e)}",
                "success": False
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
            return f"🏗️ **Classe en {language.capitalize()}**\n\nStructure orientée objet :"
        
        elif any(word in query_lower for word in ["fonction", "function", "def"]):
            return f"⚙️ **Fonction en {language.capitalize()}**\n\nCode modulaire et réutilisable :"
        
        elif any(word in query_lower for word in ["api", "web", "serveur"]):
            return f"🌐 **Code pour API/Web en {language.capitalize()}**\n\nStructure pour service web :"
        
        else:
            return f"💻 **Code généré en {language.capitalize()}**\n\nVoici une implémentation pour votre demande :"
    
    def get_status(self) -> Dict[str, Any]:
        """
        Retourne le statut du moteur IA
        """
        return {
            "engine": "running",
            "mode": "enterprise_local",
            "llm_status": "local_custom_model_only",
            "conversation_count": len(self.conversation_manager.history) if hasattr(self.conversation_manager, 'history') else 0,
            "local_ai_stats": self.local_ai.get_stats() if hasattr(self.local_ai, 'get_stats') else {},
            "config": self.config
        }
