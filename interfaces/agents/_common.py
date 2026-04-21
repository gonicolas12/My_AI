"""Imports partagés pour les mixins de l'interface Agents."""

import tkinter as tk  # noqa: F401  pylint: disable=unused-import

try:
    import customtkinter as ctk  # noqa: F401  pylint: disable=unused-import

    CTK_AVAILABLE = True
except ImportError:  # pragma: no cover - fallback
    CTK_AVAILABLE = False
    ctk = tk  # type: ignore

__all__ = ["tk", "ctk", "CTK_AVAILABLE"]
