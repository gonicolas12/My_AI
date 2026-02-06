"""
Modèles d'IA 100% locaux
Système d'intelligence artificielle autonome avec mémoire de conversation

Les imports sont lazy : les modules lourds ne sont chargés qu'à la première
utilisation via __getattr__, ce qui accélère le démarrage de l'application.
"""

from __future__ import annotations

import importlib

from typing import TYPE_CHECKING

# Imports visibles uniquement par Pylance/mypy, jamais exécutés à runtime
if TYPE_CHECKING:
    from .advanced_code_generator import AdvancedCodeGenerator as CodeGenerator
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

# Mapping nom public -> (module, nom réel dans le module)
_LAZY_IMPORTS = {
    'CustomAIModel': ('.custom_ai_model', 'CustomAIModel'),
    'AdvancedLocalAI': ('.custom_ai_model', 'AdvancedLocalAI'),
    'BaseAI': ('.base_ai', 'BaseAI'),
    'ConversationMemory': ('.conversation_memory', 'ConversationMemory'),
    'KnowledgeBase': ('.knowledge_base', 'KnowledgeBase'),
    'LinguisticPatterns': ('.linguistic_patterns', 'LinguisticPatterns'),
    'ReasoningEngine': ('.reasoning_engine', 'ReasoningEngine'),
    'CodeGenerator': ('.advanced_code_generator', 'AdvancedCodeGenerator'),
}


def __getattr__(name: str):
    if name in _LAZY_IMPORTS:
        module_path, attr_name = _LAZY_IMPORTS[name]
        module = importlib.import_module(module_path, package=__name__)
        value = getattr(module, attr_name)
        # Cache dans le namespace du package pour les accès suivants
        globals()[name] = value
        return value
    raise AttributeError(f"module 'models' has no attribute {name!r}")
