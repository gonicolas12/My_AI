"""
Classe de base pour les générateurs de code
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional

class BaseCodeGenerator(ABC):
    """Classe de base pour les générateurs de code spécifiques à un langage"""
    
    def __init__(self, language: str):
        self.language = language
        self.templates = self._load_templates()
        self.patterns = self._load_patterns()
    
    @abstractmethod
    def _load_templates(self) -> Dict[str, str]:
        """Charge les templates spécifiques au langage"""
        pass
    
    @abstractmethod
    def _load_patterns(self) -> Dict[str, str]:
        """Charge les patterns de code prédéfinis"""
        pass
    
    @abstractmethod
    def generate_function(self, name: str, params: List[str] = None, description: str = "") -> str:
        """Génère une fonction basique"""
        pass
    
    @abstractmethod
    def generate_class(self, name: str, description: str = "") -> str:
        """Génère une classe basique"""
        pass
    
    @abstractmethod
    def generate_hello_world(self) -> str:
        """Génère un programme Hello World"""
        pass
    
    @abstractmethod
    def generate_factorial(self) -> str:
        """Génère une fonction factorielle"""
        pass
