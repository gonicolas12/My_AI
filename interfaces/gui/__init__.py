"""GUI modules package for ModernAIGUI."""

from .base import BaseGUI
from .widgets import WidgetsMixin
from .layout import LayoutMixin
from .chat_area import ChatAreaMixin
from .message_bubbles import MessageBubblesMixin
from .animations import AnimationsMixin
from .syntax_highlighting import SyntaxHighlightingMixin
from .markdown_formatting import MarkdownFormattingMixin
from .file_handling import FileHandlingMixin
from .streaming import StreamingMixin

__all__ = [
    "BaseGUI",
    "WidgetsMixin",
    "LayoutMixin",
    "ChatAreaMixin",
    "MessageBubblesMixin",
    "AnimationsMixin",
    "SyntaxHighlightingMixin",
    "MarkdownFormattingMixin",
    "FileHandlingMixin",
    "StreamingMixin",
]
