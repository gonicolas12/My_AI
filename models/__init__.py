"""
Modèles d'IA 100% locaux
Système d'intelligence artificielle autonome avec mémoire de conversation
"""

from models.advanced_code_generator import \
    AdvancedCodeGenerator as CodeGenerator

from .base_ai import BaseAI
from .conversation_memory import ConversationMemory
from .custom_ai_model import AdvancedLocalAI, CustomAIModel
from .knowledge_base import KnowledgeBase
from .linguistic_patterns import LinguisticPatterns
from .reasoning_engine import ReasoningEngine

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
