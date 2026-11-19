"""
SYSTEM du Modelfile : identité, format et règles de My_AI.

Ollama n'applique le SYSTEM intégré au modèle my_ai que si la requête ne
contient aucun message « system ». Tout appel qui envoie son propre prompt
système doit donc repartir de ce texte et y AJOUTER ses consignes : les
mettre à la place effaçait l'identité de My_AI. Après un outil, la réponse
se présentait ainsi comme « une IA capable de gérer des fichiers », sans
emoji ni mise en forme.

La date du jour s'y ajoute (today_note) : le modèle ne la connaît pas.
"""

from __future__ import annotations

import logging
import re
from datetime import date
from functools import lru_cache
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

MODELFILE_PATH = Path(__file__).resolve().parent.parent / "Modelfile"

# Identité minimale quand le Modelfile est illisible
FALLBACK_IDENTITY = "Tu es My_AI, un assistant personnel local, confidentiel et puissant."

# Section « ## Outils » : de son titre jusqu'à la section suivante de même niveau
_TOOLS_SECTION_RE = re.compile(r"^## Outils[ \t]*$.*?(?=^## |\Z)", re.MULTILINE | re.DOTALL)

_DAYS = ("lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche")
_MONTHS = ("janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août",
           "septembre", "octobre", "novembre", "décembre")


def today_note(day: Optional[date] = None) -> str:
    """
    Date du jour pour le modèle, qui ne la connaît pas : sans elle, un document
    daté du mois dernier lui paraissait « futur » (ses connaissances s'arrêtent
    avant). Au jour près : le prompt système, que relit Ollama quand son début
    change, ne change ainsi qu'une fois par jour.
    """
    day = day or date.today()
    number = "1er" if day.day == 1 else str(day.day)
    return (
        "## Date du jour\n"
        f"Nous sommes le {_DAYS[day.weekday()]} {number} {_MONTHS[day.month - 1]} "
        f"{day.year} ({day:%d/%m/%Y}). Toute date antérieure à aujourd'hui est passée, "
        "même si elle est postérieure à tes données d'entraînement."
    )


def with_today(prompt: str) -> str:
    """Prompt système d'un agent ou de la page Code, suivi de la date du jour."""
    note = today_note()
    return f"{prompt}\n\n{note}" if prompt else note


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


def drop_tools_section(prompt: str) -> str:
    """
    Retire la section « ## Outils » d'un prompt système déjà construit, pour
    un appel qui n'offre aucun outil : elle pousse le modèle à appeler des
    outils qu'il n'a pas.
    """
    return _TOOLS_SECTION_RE.sub("", prompt).strip()


def with_modelfile(instructions: str = "", tools: bool = True) -> str:
    """
    Prompt système d'une réponse destinée à l'utilisateur : le SYSTEM du
    Modelfile, la date du jour, puis les consignes propres à l'appel.

    Args:
        instructions: consignes et contexte de l'appel, placés après
                      l'identité.
        tools:        False quand l'appel n'offre aucun outil. La section
                      « ## Outils » est alors retirée (drop_tools_section).
    """
    base = modelfile_system()
    if base and not tools:
        base = drop_tools_section(base)
    base = f"{base or FALLBACK_IDENTITY}\n\n{today_note()}"
    return f"{base}\n\n{instructions}" if instructions else base
