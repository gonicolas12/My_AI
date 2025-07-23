"""
Moteur principal de l'IA personnelle
Gère l'orchestration entre les différents modules
"""

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
            self.local_ai = CustomAIModel(conversation_memory=self.conversation_memory)
            self.model = self.local_ai  # Alias pour compatibilité avec l'interface graphique
            self.logger.info("✅ Modèle IA local avec mémoire initialisé")
            # Initialisation du gestionnaire de LLM
            self.llm_manager = self.local_ai  # Pour compatibilité avec les fonctions qui utilisent llm_manager
        except Exception as e:
            self.logger.error(f"❌ Erreur lors de l'initialisation du modèle IA : {e}")
            # Fallback sur l'ancien système
            self.local_ai = CustomAIModel()
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
        Traite un texte en utilisant le modèle IA local personnalisé
        
        Args:
            text: Texte à traiter
            
        Returns:
            Réponse de l'IA sous forme de texte
        """
        try:
            self.logger.info(f"Processing text: {text[:50]}...")
            
            # Utilisation du modèle IA local 100% autonome
            response = self.local_ai.generate_response(text)
            
            self.logger.info(f"AI model response: {response[:50]}...")
            
            # On sauvegarde l'échange sans utiliser add_message qui cause des erreurs
            try:
                # Tente d'utiliser add_exchange qui est une autre méthode disponible
                self.conversation_manager.add_exchange(text, {"message": response})
            except:
                # Si ça échoue aussi, on ne fait rien - l'important est de ne pas planter
                self.logger.warning("Impossible de sauvegarder la conversation")
            
            return response
        
        except Exception as e:
            self.logger.error(f"Erreur dans process_text: {e}")
            self.logger.warning("Utilisation du fallback response")
            fallback_response = self._generate_fallback_response(text)
            return fallback_response
    
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
        Gère le traitement de fichiers et questions sur les documents
        """
        try:
            query_lower = query.lower()
            
            # Déterminer quel document spécifique est demandé
            target_document = None
            all_docs = context.get('stored_documents', {})
            document_order = context.get('document_order', [])
            
            # Log pour debug
            self.logger.info(f"Query: '{query}' | Documents disponibles: {list(all_docs.keys())}")
            
            # Recherche de mots-clés spécifiques au type de document - LOGIQUE RENFORCÉE

            # Définir les flags de référence numérique AVANT leur utilisation
            is_first_requested = any(term in query_lower for term in ['premier', '1er', '1ère', 'première', 'document 1', 'le 1'])
            is_second_requested = any(term in query_lower for term in ['deuxième', '2ème', '2eme', 'seconde', 'document 2', 'le 2'])
            is_last_requested = any(term in query_lower for term in ['dernier', 'dernière', 'last'])
            
            # 1. RECHERCHE EXPLICITE par mention du nom exact du fichier
            for doc_name in all_docs.keys():
                doc_name_clean = doc_name.lower().replace('.pdf', '').replace('.docx', '').replace('.doc', '').replace('.py', '')
                # Construire le prompt avec le document ciblé - PROTECTION RENFORCÉE
                if target_document and target_document in all_docs:
                    doc_data = all_docs[target_document]
                    if isinstance(doc_data, dict) and 'content' in doc_data:
                        doc_content = doc_data['content']
                    else:
                        doc_content = str(doc_data)

                    # Provide more content for more detailed summaries
                    max_len = 8000
                    self.logger.info(f"📄 DOCUMENT SÉLECTIONNÉ POUR TRAITEMENT: {target_document}")
                    self.logger.info(f"📊 Taille contenu: {len(doc_content)} caractères")

                    prompt = f"""🚨 RÈGLE ABSOLUE ET OBLIGATOIRE 🚨
 JE TE DONNE ACCÈS À UN SEUL DOCUMENT. TU NE DOIS ANALYSER QUE CE DOCUMENT.
 IGNORE COMPLÈTEMENT TOUTE RÉFÉRENCE À D'AUTRES DOCUMENTS.

 🎯 DOCUMENT UNIQUE À ANALYSER: {target_document}
 � QUESTION: {query}

 📄 CONTENU DU DOCUMENT \"{target_document}\":
 {doc_content[:max_len]}"""
                    if len(doc_content) > max_len:
                        prompt += "\n[... contenu tronqué pour économiser l'espace ...]"

                    prompt += f"""

 🔒 INSTRUCTIONS STRICTES:
 1. Réponds UNIQUEMENT sur le contenu ci-dessus du fichier \"{target_document}\"
 2. Commence ta réponse par \"📄 DOCX analysé : {target_document}\"
 3. NE MENTIONNE AUCUN AUTRE DOCUMENT
 4. Base-toi EXCLUSIVEMENT sur le contenu fourni ci-dessus
 5. Si tu vois une référence à un autre document, IGNORE-LA COMPLÈTEMENT
 6. Fais un résumé TRÈS DÉTAILLÉ, structuré, avec une introduction, un développement en plusieurs points, et une conclusion riche. Utilise des listes, des titres en gras, et mets en valeur les mots importants.
 """
                    # Log pour debug final
                    self.logger.info(f"🔍 PROMPT généré pour {target_document} (début): {prompt[:300]}...")

                    # PROTECTION FINALE : créer un contexte isolé avec SEULEMENT le document ciblé
                    isolated_context = {
                        'stored_documents': {target_document: all_docs[target_document]},
                        'document_order': [target_document],
                        'conversation_history': context.get('conversation_history', [])
                    }

                    # Générer la réponse avec le contexte isolé
                    response = self.local_ai.generate_response(prompt)
                    # "doc" isolé sans contexte PDF
                    query_words = query_lower.split()
                    if 'doc' in query_words or 'du doc' in query_lower or 'le doc' in query_lower:
                        docx_docs = [doc for doc in document_order if doc.lower().endswith(('.docx', '.doc'))]
                        
                        if docx_docs:
                            if is_first_requested and len(docx_docs) >= 1:
                                target_document = docx_docs[0]
                                self.logger.info(f"PREMIER DOC sélectionné: {target_document}")
                            else:
                                target_document = docx_docs[-1]
                                self.logger.info(f"DOCX sélectionné par 'doc' isolé: {target_document}")
                
                # Détection CODE
                elif any(term in query_lower for term in ['code', 'py', 'python', 'script']):
                    code_docs = [doc for doc in document_order if doc.lower().endswith(('.py', '.js', '.ts', '.java', '.cpp', '.c', '.html', '.css', '.json'))]
                    
                    if code_docs:
                        if is_first_requested and len(code_docs) >= 1:
                            target_document = code_docs[0]
                            self.logger.info(f"PREMIER CODE sélectionné: {target_document}")
                        else:
                            target_document = code_docs[-1]
                            self.logger.info(f"Code sélectionné par type: {target_document}")
                
                # GESTION GÉNÉRALE DES RÉFÉRENCES NUMÉRIQUES (tous types confondus)
                elif is_first_requested or is_second_requested or is_last_requested:
                    if is_first_requested and len(document_order) >= 1:
                        target_document = document_order[0]
                        self.logger.info(f"PREMIER DOCUMENT (tous types) sélectionné: {target_document}")
                    elif is_second_requested and len(document_order) >= 2:
                        target_document = document_order[1]
                        self.logger.info(f"DEUXIÈME DOCUMENT (tous types) sélectionné: {target_document}")
                    elif is_last_requested and document_order:
                        target_document = document_order[-1]
                        self.logger.info(f"DERNIER DOCUMENT (tous types) sélectionné: {target_document}")
            
            # 3. Si pas de type spécifique mais demande d'action (résumé, analyse, etc.)
            if not target_document:
                action_keywords = ['résume', 'résumé', 'analyse', 'contenu', 'explique', 'décris', 'que dit', 'que contient']
                if any(keyword in query_lower for keyword in action_keywords):
                    if document_order:
                        target_document = document_order[-1]
                        self.logger.info(f"Dernier document sélectionné pour action: {target_document}")
            
            # NOUVEAU : Log détaillé pour debug - VÉRIFIE LA SÉLECTION
            self.logger.info(f"=== DEBUG SÉLECTION DOCUMENT ===")
            self.logger.info(f"Query originale: '{query}'")
            self.logger.info(f"Query lowercase: '{query_lower}'")
            self.logger.info(f"Documents disponibles: {list(all_docs.keys())}")
            self.logger.info(f"Ordre documents: {document_order}")
            self.logger.info(f"Document ciblé FINAL: {target_document}")
            self.logger.info(f"=== FIN DEBUG ===")
            
            if not target_document:
                self.logger.warning(f"Aucun document spécifique détecté dans: '{query_lower}'")
            
            # Si aucun document spécifique n'est mentionné, prendre le plus récent
            if not target_document and document_order:
                target_document = document_order[-1]
                self.logger.info(f"Document le plus récent sélectionné: {target_document}")
            
            # Construire le prompt avec le document ciblé - PROTECTION RENFORCÉE
            if target_document and target_document in all_docs:
                doc_data = all_docs[target_document]
                if isinstance(doc_data, dict) and 'content' in doc_data:
                    doc_content = doc_data['content']
                else:
                    doc_content = str(doc_data)
                
                # PROTECTION SUPPLÉMENTAIRE : vérifier que c'est bien le bon document
                self.logger.info(f"📄 DOCUMENT SÉLECTIONNÉ POUR TRAITEMENT: {target_document}")
                self.logger.info(f"📊 Taille contenu: {len(doc_content)} caractères")
                
                # PROMPT ULTRA-SPÉCIFIQUE avec BLOCAGE des autres documents
                prompt = f"""🚨 RÈGLE ABSOLUE ET OBLIGATOIRE 🚨
JE TE DONNE ACCÈS À UN SEUL DOCUMENT. TU NE DOIS ANALYSER QUE CE DOCUMENT.
IGNORE COMPLÈTEMENT TOUTE RÉFÉRENCE À D'AUTRES DOCUMENTS.

🎯 DOCUMENT UNIQUE À ANALYSER: {target_document}
� QUESTION: {query}

📄 CONTENU DU DOCUMENT "{target_document}":
{doc_content[:3000]}"""
                
                if len(doc_content) > 3000:
                    prompt += "\n[... contenu tronqué pour économiser l'espace ...]"
                    
                prompt += f"""

🔒 INSTRUCTIONS STRICTES:
1. Réponds UNIQUEMENT sur le contenu ci-dessus du fichier "{target_document}"
2. Commence ta réponse par "📄 DOCX analysé : {target_document}"
3. NE MENTIONNE AUCUN AUTRE DOCUMENT
4. Base-toi EXCLUSIVEMENT sur le contenu fourni ci-dessus
5. Si tu vois une référence à un autre document, IGNORE-LA COMPLÈTEMENT
"""
                
                # Log pour debug final
                self.logger.info(f"🔍 PROMPT généré pour {target_document} (début): {prompt[:300]}...")
                
                # PROTECTION FINALE : créer un contexte isolé avec SEULEMENT le document ciblé
                isolated_context = {
                    'stored_documents': {target_document: all_docs[target_document]},
                    'document_order': [target_document],
                    'conversation_history': context.get('conversation_history', [])
                }
                
                # Générer la réponse avec le contexte isolé
                response = self.local_ai.generate_response(prompt)
                
            else:
                # Fallback: utiliser tous les documents disponibles
                self.logger.warning("Aucun document ciblé trouvé, utilisation de tous les documents")
                prompt = f"""Question: {query}

Contexte des documents disponibles:"""
                
                if 'stored_documents' in context:
                    for doc_name, doc_data in context['stored_documents'].items():
                        if isinstance(doc_data, dict) and 'content' in doc_data:
                            doc_content = doc_data['content']
                        else:
                            doc_content = str(doc_data)
                        
                        prompt += f"\n\n--- Document: {doc_name} ---\n{doc_content[:2000]}"
                        if len(doc_content) > 2000:
                            prompt += "\n[... contenu tronqué ...]"
                
                prompt += f"\n\nRéponds à la question en te basant sur le contenu des documents ci-dessus."
                
                # Générer la réponse
                response = self.local_ai.generate_response(prompt)
            
            # NE PLUS ajouter de préfixe ici car custom_ai_model s'en charge déjà
            return {
                "type": "file_processing",
                "message": response,
                "success": True
            }
        except Exception as e:
            self.logger.error(f"Erreur traitement fichier: {e}")
            return {
                "type": "file_processing",
                "message": "Traitement de fichier en cours...",
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
