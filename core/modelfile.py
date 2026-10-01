"""
SYSTEM du Modelfile : identité, format et règles de My_AI.

Ollama n'applique le SYSTEM intégré au modèle my_ai que si la requête ne
contient aucun message « system ». Tout appel qui envoie son propre prompt
système doit donc repartir de ce texte et y AJOUTER ses consignes : les
mettre à la place effaçait l'identité de My_AI. Après un outil, la réponse
se présentait ainsi comme « une IA capable de gérer des fichiers », sans
emoji ni mise en forme.
"""

from __future__ import annotations

import logging
import re
from functools import lru_cache
from pathlib import Path

logger = logging.getLogger(__name__)

MODELFILE_PATH = Path(__file__).resolve().parent.parent / "Modelfile"

# Identité minimale quand le Modelfile est illisible
FALLBACK_IDENTITY = "Tu es My_AI, un assistant personnel local, confidentiel et puissant."

# Section « ## Outils » : de son titre jusqu'à la section suivante de même niveau
_TOOLS_SECTION_RE = re.compile(r"^## Outils[ \t]*$.*?(?=^## |\Z)", re.MULTILINE | re.DOTALL)


@lru_cache(maxsize=1)
def modelfile_system() -> str:
    """Bloc SYSTEM du Modelfile, ou chaîne vide s'il est illisible."""
    try:
        content = MODELFILE_PATH.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        logger.warning("Impossible de lire le Modelfile : %s", exc)
        return ""
    match = re.search(r'SYSTEM\s+"""(.*?)"""', content, re.DOTALL)
    if not match:
        logger.warning("Aucun bloc SYSTEM dans %s", MODELFILE_PATH)
        return ""
    return match.group(1).strip()


def with_modelfile(instructions: str = "", tools: bool = True) -> str:
    """
    Prompt système d'une réponse destinée à l'utilisateur : le SYSTEM du
    Modelfile, puis les consignes propres à l'appel.

    Args:
        instructions: consignes et contexte de l'appel, placés après
                      l'identité.
        tools:        False quand l'appel n'offre aucun outil. La section
                      « ## Outils » est alors retirée : elle pousse le modèle
                      à appeler des outils qu'il n'a pas.
    """
    base = modelfile_system()
    if base and not tools:
        base = _TOOLS_SECTION_RE.sub("", base).strip()
    base = base or FALLBACK_IDENTITY
    return f"{base}\n\n{instructions}" if instructions else base
