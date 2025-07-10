"""
Gestionnaire de conversations et historique
Maintient le contexte conversationnel
"""

import json
from datetime import datetime
from typing import List, Dict, Any, Optional, Union
from pathlib import Path

class ConversationManager:
    """
    Gère l'historique des conversations et le contexte
    """
    
    def __init__(self, max_history: int = 10, memory: Optional[Any] = None):
        """
        Initialise le gestionnaire de conversations
        
        Args:
            max_history: Nombre maximum d'échanges à conserver
            memory: Instance de ConversationMemory pour la persistance
        """
        self.max_history = max_history
        self.history: List[Dict[str, Any]] = []
        self.current_session = self._create_session()
        self.memory = memory
    
    def _create_session(self) -> Dict[str, Any]:
        """
        Crée une nouvelle session de conversation
        """
        return {
            "id": datetime.now().isoformat(),
            "start_time": datetime.now(),
            "exchanges": []
        }
    
    def add_exchange(self, user_input: str, ai_response: Union[str, Dict[str, Any]]) -> None:
        """
        Ajoute un échange à l'historique avec validation du format
        """
        # S'assurer que ai_response est toujours formaté correctement
        if isinstance(ai_response, dict):
            # Si c'est un dictionnaire avec message imbriqué, l'extraire
            if "message" in ai_response:
                message_content = ai_response["message"]
                if isinstance(message_content, dict) and "message" in message_content:
                    ai_response = {"text": str(message_content["message"])}
                else:
                    ai_response = {"text": str(message_content)}
            else:
                ai_response = {"text": str(ai_response)}
        elif isinstance(ai_response, str):
            ai_response = {"text": ai_response}
        else:
            ai_response = {"text": str(ai_response)}
        
        exchange = {
            "timestamp": datetime.now().isoformat(),
            "user_input": user_input,
            "ai_response": ai_response,
            "session_id": self.current_session["id"]
        }
        
        # Synchroniser avec la mémoire si disponible
        if self.memory:
            self.memory.add_conversation(
                user_input,
                ai_response.get("text", str(ai_response)),
                ai_response.get("intent", "unknown"),
                ai_response.get("confidence", 0.0),
                {"session_id": self.current_session["id"]}
            )
        
        self.history.append(exchange)
        self.current_session["exchanges"].append(exchange)
        
        # Limite l'historique
        if len(self.history) > self.max_history:
            self.history.pop(0)
    
    def add_message(self, role: str, content: str) -> None:
        """
        Ajoute un message simple à l'historique (compatibilité)
        
        Args:
            role: 'user' ou 'assistant'
            content: Contenu du message
        """
        if not hasattr(self, '_simple_history'):
            self._simple_history = []
        
        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        }
        
        self._simple_history.append(message)
        
        # Limite l'historique simple aussi
        if len(self._simple_history) > self.max_history * 2:  # 2 messages par échange
            self._simple_history.pop(0)
    
    def get_history(self) -> List[Dict[str, str]]:
        """
        Retourne l'historique simple (compatibilité)
        
        Returns:
            Liste des messages simples
        """
        if not hasattr(self, '_simple_history'):
            return []
        return self._simple_history.copy()

    def get_recent_history(self, count: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Récupère l'historique récent
        
        Args:
            count: Nombre d'échanges à récupérer (par défaut: tous)
            
        Returns:
            Liste des échanges récents
        """
        if count is None:
            return self.history.copy()
        return self.history[-count:] if self.history else []
    
    def get_context_for_llm(self) -> str:
        """
        Formate l'historique pour le LLM
        
        Returns:
            Contexte formaté pour le modèle
        """
        context_parts = []
        
        for exchange in self.get_recent_history(5):  # 5 derniers échanges
            context_parts.append(f"Utilisateur: {exchange['user_input']}")
            if exchange['ai_response'].get('message'):
                context_parts.append(f"Assistant: {exchange['ai_response']['message']}")
        
        return "\n".join(context_parts)
    
    def clear_history(self) -> None:
        """
        Efface l'historique des conversations
        """
        self.history.clear()
        if hasattr(self, '_simple_history'):
            self._simple_history.clear()
        self.current_session = self._create_session()
    
    def clear(self) -> None:
        """
        Efface l'historique des conversations et réinitialise la session
        """
        self.history.clear()
        self.current_session = self._create_session()
        if self.memory:
            self.memory.clear()
    
    def save_session(self, filepath: str) -> None:
        """
        Sauvegarde la session actuelle
        
        Args:
            filepath: Chemin du fichier de sauvegarde
        """
        session_data = {
            "session": self.current_session,
            "history": self.history
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(session_data, f, indent=2, ensure_ascii=False, default=str)
    
    def load_session(self, filepath: str) -> None:
        """
        Charge une session sauvegardée
        
        Args:
            filepath: Chemin du fichier de session
        """
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                session_data = json.load(f)
            
            self.current_session = session_data.get("session", self._create_session())
            self.history = session_data.get("history", [])
            
        except FileNotFoundError:
            print(f"Fichier de session non trouvé: {filepath}")
        except json.JSONDecodeError:
            print(f"Erreur de format dans le fichier de session: {filepath}")
    
    def get_session_summary(self) -> Dict[str, Any]:
        """
        Retourne un résumé de la session actuelle
        """
        return {
            "session_id": self.current_session["id"],
            "start_time": self.current_session["start_time"],
            "total_exchanges": len(self.history),
            "current_session_exchanges": len(self.current_session["exchanges"])
        }
