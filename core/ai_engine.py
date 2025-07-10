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
        
        # Mots-clés pour le traitement de fichiers
        file_keywords = ["lire", "ouvrir", "analyser", "fichier", "pdf", "docx", "document"]
        if any(keyword in query_lower for keyword in file_keywords):
            return "file_processing"
        
        # Mots-clés pour la génération de code
        code_keywords = ["code", "programme", "script", "fonction", "classe", "python", "html"]
        if any(keyword in query_lower for keyword in code_keywords):
            return "code_generation"
        
        # Mots-clés pour la génération de documents
        doc_keywords = ["créer", "générer", "rapport", "document", "résumé", "rédiger"]
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
        
        return full_context
    
    async def _handle_conversation(self, query: str, context: Dict) -> Dict[str, Any]:
        """
        Gère les conversations générales
        """
        response = self.local_ai.generate_response(query)
        
        return {
            "type": "conversation",
            "message": response,
            "success": True
        }
    
    async def _handle_file_processing(self, query: str, context: Dict) -> Dict[str, Any]:
        """
        Gère le traitement de fichiers
        """
        # Logique de traitement de fichiers
        # À implémenter selon les besoins spécifiques
        return {
            "type": "file_processing",
            "message": "Traitement de fichier en cours...",
            "success": True
        }
    
    async def _handle_code_generation(self, query: str, context: Dict) -> Dict[str, Any]:
        """
        Gère la génération de code
        """
        code = await self.code_generator.generate_code(query, context)
        
        return {
            "type": "code_generation",
            "code": code,
            "message": "Code généré avec succès",
            "success": True
        }
    
    async def _handle_document_generation(self, query: str, context: Dict) -> Dict[str, Any]:
        """
        Gère la génération de documents
        """
        document = await self.document_generator.generate_document(query, context)
        
        return {
            "type": "document_generation",
            "document": document,
            "message": "Document généré avec succès",
            "success": True
        }
    
    async def _handle_general_query(self, query: str, context: Dict) -> Dict[str, Any]:
        """
        Gère les requêtes générales
        """
        response = self.local_ai.generate_response(query)
        
        return {
            "type": "general",
            "message": response,
            "success": True
        }
    
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
