"""
Interface Graphique Moderne - My AI Personal Assistant
Orchestrateur léger basé sur les mixins modularisés.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Add the project root to the path (for direct execution)
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from interfaces.gui import (
    AnimationsMixin,
    BaseGUI,
    ChatAreaMixin,
    FileHandlingMixin,
    LayoutMixin,
    MarkdownFormattingMixin,
    MessageBubblesMixin,
    StreamingMixin,
    SyntaxHighlightingMixin,
    WidgetsMixin,
)


class ModernAIGUI(
    BaseGUI,
    WidgetsMixin,
    LayoutMixin,
    ChatAreaMixin,
    MessageBubblesMixin,
    AnimationsMixin,
    SyntaxHighlightingMixin,
    MarkdownFormattingMixin,
    FileHandlingMixin,
    StreamingMixin,
):
    """GUI Moderne (orchestrateur)."""


__all__ = ["ModernAIGUI"]


def main():
    """Point d'entrée principal."""
    app = ModernAIGUI()
    app.run()


if __name__ == "__main__":
    main()
