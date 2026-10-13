"""
Fonctions de la fenêtre exposées au JavaScript (window.pywebview.api)

L'interface ne les appelle qu'à travers son module shell
(frontend/src/lib/shell.ts). pywebview expose toutes les méthodes publiques de
l'objet, et parcourt ses attributs publics : les références internes restent
donc privées (préfixe « _ »).

Seule la page de l'appli peut les appeler : la fenêtre ne charge jamais
d'autre page (cf. window.py), et les artefacts s'affichent dans des iframes
isolées, sans accès à ce pont.
"""

import sys
import webbrowser
from typing import Callable, Optional
from urllib.parse import urlsplit

from utils.logger import setup_logger

logger = setup_logger("ShellApi")

# Schémas qu'un lien peut ouvrir hors de l'appli (navigateur, messagerie)
EXTERNAL_SCHEMES = ("http", "https", "mailto")


def external_url(url: str) -> Optional[str]:
    """URL d'un lien web autorisé à sortir de l'appli, ou None (file:, javascript:…)."""
    if not isinstance(url, str):
        return None
    url = url.strip()
    try:
        parts = urlsplit(url)
    except ValueError:
        return None
    if parts.scheme.lower() not in EXTERNAL_SCHEMES:
        return None
    if parts.scheme.lower() != "mailto" and not parts.netloc:
        return None
    return url


def open_external(url: str, opener: Callable[[str], bool] = webbrowser.open) -> bool:
    """Ouvre un lien web dans le navigateur du système ; tout autre schéma est refusé."""
    target = external_url(url)
    if target is None:
        logger.warning("Lien refusé (schéma non autorisé) : %.120s", url)
        return False
    try:
        return bool(opener(target))
    except Exception as exc:  # pylint: disable=broad-except
        logger.warning("Ouverture du lien impossible : %s", exc)
        return False


class ShellApi:
    """Pont entre l'interface et la fenêtre."""

    def __init__(self, title_bar: Optional[Callable[[str, str], bool]] = None):
        """
        Args:
            title_bar: pose les couleurs de la barre de titre (fond, texte « #rrggbb »)
        """
        self._title_bar = title_bar

    def open_external(self, url: str) -> bool:
        """Ouvre un lien dans le navigateur du système."""
        return open_external(url)

    def platform(self) -> str:
        """Système : win32, darwin, linux."""
        return sys.platform

    def set_title_bar_colors(self, background: str, text: str) -> bool:
        """Barre de titre aux couleurs de la page (jetons de tokens.css), Windows 11."""
        if self._title_bar is None:
            return False
        try:
            return bool(self._title_bar(str(background), str(text)))
        except Exception as exc:  # pylint: disable=broad-except
            logger.warning("Couleurs de la barre de titre non appliquées : %s", exc)
            return False
