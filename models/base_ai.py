"""
Base abstraite pour les modèles d'IA locaux
Interface commune pour tous les composants d'IA
"""

from abc import ABC, abstractmethod
from typing import Dict, Optional, Any
import logging


class BaseAI(ABC):
    """Classe de base pour tous les modèles d'IA locaux"""

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)

    @abstractmethod
    def generate_response(
        self, user_input: str, context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Génère une réponse à partir du texte d'entrée"""

    def get_model_info(self) -> Dict[str, Any]:
        """Retourne les informations sur le modèle"""
        return {"name": self.__class__.__name__, "type": "base_ai", "version": "1.0.0"}

    def get_welcome_message(self) -> str:
        """Message d'accueil par défaut"""
        return "🤖 Assistant IA Local - Prêt à vous aider"

    def is_available(self) -> bool:
        """Vérifie si l'IA est disponible"""
        return True
