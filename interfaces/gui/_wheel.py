"""Normalisation des événements de molette entre plateformes.

Tkinter ne livre pas ``event.delta`` de la même façon selon l'OS :

- **Windows** : multiples de 120 (un cran = 120).
- **macOS**   : petits entiers, un cran valant typiquement ±1. Tk n'applique
  *pas* le facteur 120.
- **Linux/X11** : pas de ``delta`` du tout, mais les boutons 4 (haut) et 5 (bas).

Le code historique divisait directement par 120 (ou par 6), ce qui donne 0 sur
macOS pour un cran standard : la molette ne faisait donc rien, alors que la
barre de défilement fonctionnait.

``wheel_notches`` ramène tout à une unité commune — le **cran**, positif vers le
haut — pour que chaque appelant applique ensuite son propre facteur.
"""

from __future__ import annotations

import sys

__all__ = ["wheel_notches"]

_IS_MACOS = sys.platform == "darwin"

# Sous Windows, un cran de molette vaut 120.
_WINDOWS_DELTA_PER_NOTCH = 120


def wheel_notches(event) -> float:
    """Convertit un événement de molette en nombre de crans.

    Positif = vers le haut. Retourne 0.0 si l'événement ne porte aucune
    information de défilement exploitable.
    """
    # Linux/X11 : boutons 4 et 5, sans delta.
    num = getattr(event, "num", None)
    if num == 4:
        return 1.0
    if num == 5:
        return -1.0

    delta = getattr(event, "delta", 0) or 0
    if not delta:
        return 0.0

    if _IS_MACOS:
        # Déjà exprimé en crans ; on garde le signe et l'amplitude.
        return float(delta)

    return delta / _WINDOWS_DELTA_PER_NOTCH
