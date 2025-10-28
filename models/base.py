"""
Classes de base pour les modèles LLM
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional


class LLMBackend(ABC):
    """Interface abstraite pour les backends LLM"""

    @abstractmethod
    async def generate_response(self, prompt: str, context: Optional[str] = None) -> str:
        """Génère une réponse à partir du prompt"""

    @abstractmethod
    def is_available(self) -> bool:
        """Vérifie si le backend est disponible"""

    @abstractmethod
    def get_model_info(self) -> Dict[str, Any]:
        """Retourne les informations du modèle"""

    @abstractmethod
    def cleanup(self):
        """Nettoie les ressources du backend"""
