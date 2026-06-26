"""Notifications desktop natives, cross-plateforme et 100 % locales.

Backend par ordre de préférence :
  1. winotify  (Windows, toasts natifs Action Center)
  2. plyer     (cross-plateforme : Windows / macOS / Linux)

Si aucun backend n'est disponible, ``notify_desktop`` retourne simplement
False : l'appelant peut alors se rabattre sur une notification in-app.
Aucune dépendance réseau — conforme à la contrainte « 100 % local ».
"""

from __future__ import annotations

APP_ID = "My_AI"


def notify_desktop(title: str, message: str = "") -> bool:
    """Affiche une notification système. Retourne True si elle a été affichée.

    Ne lève jamais : toute erreur (backend absent, indisponible…) renvoie False.
    Sans danger depuis un thread worker (n'effectue aucun appel Tk).
    """
    msg = message or " "
    try:
        from winotify import Notification  # type: ignore

        Notification(app_id=APP_ID, title=title, msg=msg).show()
        return True
    except Exception:
        pass
    try:
        from plyer import notification  # type: ignore

        notification.notify(title=title, message=msg, app_name=APP_ID, timeout=10)
        return True
    except Exception:
        return False
