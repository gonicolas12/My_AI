"""
Modèles d'IA 100% locaux
Système d'intelligence artificielle autonome avec mémoire de conversation
"""

from .custom_ai_model import CustomAIModel, AdvancedLocalAI
from .base_ai import BaseAI
from .linguistic_patterns import LinguisticPatterns
from .knowledge_base import KnowledgeBase
from models.advanced_code_generator import AdvancedCodeGenerator as CodeGenerator
from .reasoning_engine import ReasoningEngine
from .conversation_memory import ConversationMemory

__all__ = [
    'CustomAIModel',
    'AdvancedLocalAI',
    'BaseAI',
    'LinguisticPatterns',
    'KnowledgeBase',
    'CodeGenerator',
    'ReasoningEngine',
    'ConversationMemory'
]