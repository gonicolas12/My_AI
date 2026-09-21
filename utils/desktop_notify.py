"""Notifications desktop natives, cross-plateforme et 100 % locales.

Backend par ordre de préférence :
  1. winotify  (Windows, toasts natifs Action Center)
  2. osascript (macOS, natif — aucune dépendance Python)
  3. plyer     (cross-plateforme : Windows / macOS / Linux)

Si aucun backend n'est disponible, ``notify_desktop`` retourne simplement
False : l'appelant peut alors se rabattre sur une notification in-app.
Aucune dépendance réseau — conforme à la contrainte « 100 % local ».
"""

from __future__ import annotations

import subprocess
import sys

APP_ID = "My_AI"


def _osascript_escape(text: str) -> str:
    """Échappe une chaîne pour une littérale AppleScript entre guillemets."""
    return text.replace("\\", "\\\\").replace('"', '\\"')


def _notify_macos(title: str, msg: str) -> bool:
    """Notification macOS via osascript. Aucune dépendance Python requise."""
    script = (
        f'display notification "{_osascript_escape(msg)}" '
        f'with title "{_osascript_escape(title)}"'
    )
    try:
        result = subprocess.run(
            ["osascript", "-e", script],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            timeout=5, check=False,
        )
        return result.returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


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
    # macOS : osascript est présent par défaut, contrairement à plyer.
    if sys.platform == "darwin" and _notify_macos(title, msg):
        return True
    try:
        from plyer import notification  # type: ignore

        notification.notify(title=title, message=msg, app_name=APP_ID, timeout=10)
        return True
    except Exception:
        return False
