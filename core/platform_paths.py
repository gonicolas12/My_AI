"""Exemples de chemins absolus adaptés à l'OS courant.

Les descriptions d'outils et les prompts système citaient « C:\\Users\\... » en
dur : sur macOS et Linux, le modèle proposait donc des chemins Windows à ses
propres outils fichier, qui échouaient.

Module volontairement sans dépendance interne : il est importé aussi bien par
``core.ai_engine`` que par ``core.chat_orchestrator``, que le premier importe.
"""

from __future__ import annotations

import sys
from typing import Dict

__all__ = ["PATH_EXAMPLES", "path_examples"]


def path_examples() -> Dict[str, str]:
    """Retourne les exemples de chemins correspondant à la plateforme courante.

    Clés : ``os``, ``home``, ``named_dir``, ``file``, ``roots``, ``sep``.
    """
    if sys.platform == "win32":
        return {
            "os": "Windows",
            "home": "C:\\Users\\...",
            "named_dir": "C:\\Users\\Nom",
            "file": "C:\\Users\\...\\fichier.txt",
            "roots": "C:\\, D:\\, répertoires systèmes",
            "sep": "\\",
        }
    if sys.platform == "darwin":
        return {
            "os": "macOS",
            "home": "/Users/...",
            "named_dir": "/Users/nom",
            "file": "/Users/.../fichier.txt",
            "roots": "/, /Users, /Applications, /Volumes",
            "sep": "/",
        }
    return {
        "os": "Linux",
        "home": "/home/...",
        "named_dir": "/home/nom",
        "file": "/home/.../fichier.txt",
        "roots": "/, /home, /mnt, /media",
        "sep": "/",
    }


PATH_EXAMPLES: Dict[str, str] = path_examples()
