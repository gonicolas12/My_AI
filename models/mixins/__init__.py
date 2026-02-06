"""
Mixins pour CustomAIModel — Découpage du God Object en modules fonctionnels.

Chaque mixin regroupe un ensemble cohérent de méthodes qui sont mixées
dans la classe CustomAIModel via l'héritage multiple.
"""

from .advanced_code_gen import AdvancedCodeGenMixin
from .context_management import ContextManagementMixin
from .conversation_responses import ConversationResponseMixin
from .document_analysis import DocumentAnalysisMixin
from .internet_search import InternetSearchMixin
from .programming_help import ProgrammingHelpMixin

__all__ = [
    "AdvancedCodeGenMixin",
    "ContextManagementMixin",
    "ConversationResponseMixin",
    "DocumentAnalysisMixin",
    "InternetSearchMixin",
    "ProgrammingHelpMixin",
]
