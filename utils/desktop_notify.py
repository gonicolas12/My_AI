"""Notifications desktop natives, cross-plateforme et 100 % locales.

Backend par ordre de préférence :
  1. winotify  (Windows, toasts natifs Action Center)
  2. osascript (macOS, natif — aucune dépendance Python)
  3. plyer     (cross-plateforme : Windows / macOS / Linux)

Si aucun backend n'est disponible, ``notify_desktop`` retourne simplement
False : l'appelant peut alors se rabattre sur une notification in-app.
Aucune dépendance réseau — conforme à la contrainte « 100 % local ».

Une notification n'affiche que du texte brut : le Markdown d'un résumé
(« # Analyse : … », gras, liens…) est réduit à son texte par ``plain_text``.
"""

from __future__ import annotations

import re
import subprocess
import sys
from typing import Optional

APP_ID = "My_AI"

# Texte d'une notification : 220 caractères au plus, comme celle d'une tâche
# planifiée depuis toujours (Windows n'en montre de toute façon que 3 lignes)
MESSAGE_LIMIT = 220

# Lignes de balisage seules : clôtures de bloc de code, règles, séparateurs de tableau
_FENCE_RE = re.compile(r"^[ \t]*(```|~~~).*$", re.MULTILINE)
_RULE_RE = re.compile(r"^[ \t]*([-*_])([ \t]*\1){2,}[ \t]*$", re.MULTILINE)
_TABLE_SEP_RE = re.compile(
    r"^[ \t]*\|?[ \t]*:?-{3,}:?[ \t]*(\|[ \t]*:?-{3,}:?[ \t]*)*\|?[ \t]*$", re.MULTILINE
)
# Début de ligne : titre, citation, puce
_HEADING_RE = re.compile(r"^[ \t]{0,3}#{1,6}[ \t]+", re.MULTILINE)
_QUOTE_RE = re.compile(r"^[ \t]{0,3}>[ \t]?", re.MULTILINE)
_BULLET_RE = re.compile(r"^[ \t]*[-*+][ \t]+", re.MULTILINE)
# Image et lien réduits à leur texte, même coupés en route (« [titre](https://exa »)
_IMAGE_RE = re.compile(r"!\[([^\]\n]*)\]\([^)\s]*\)?")
_LINK_RE = re.compile(r"\[([^\]\n]+)\]\([^)\s]*\)?")
_CODE_RE = re.compile(r"`([^`\n]+)`")
# Gras et italique : jamais au milieu d'un mot (« 3*4*5 », « nom_de_variable »)
_STRONG_RE = re.compile(r"(?<![\w*])(\*\*|__)(?=\S)(.+?)(?<=\S)\1(?![\w*])")
_EMPHASIS_RE = re.compile(r"(?<![\w*])(\*|_)(?=\S)(.+?)(?<=\S)\1(?![\w*])")
# Marques restées seules, quand le résumé a été coupé au milieu d'un gras
_STRAY_RE = re.compile(
    r"(?:(?<=\s)|^)(\*{1,3}|_{2,3})(?=[^\s*_])|(?<=[^\s*_])(\*{1,3}|_{2,3})(?=\s|$)",
    re.MULTILINE,
)
_SPACES_RE = re.compile(r"[ \t]+")


def _table_row(line: str) -> str:
    """« | a | b | » devient « a · b » ; toute autre ligne reste telle quelle."""
    stripped = line.strip()
    if len(stripped) > 1 and stripped.startswith("|") and stripped.endswith("|"):
        cells = [cell.strip() for cell in stripped[1:-1].split("|")]
        return " · ".join(cell for cell in cells if cell)
    return line


def _shorten(text: str, limit: int) -> str:
    """Coupe le texte à ``limit`` caractères, sur un mot, suivi de « … »."""
    if len(text) <= limit:
        return text
    cut = text[: limit - 1]
    space = max(cut.rfind(" "), cut.rfind("\n"))
    if space >= limit // 2:
        cut = cut[:space]
    return cut.rstrip(" \n,;:.-–—(") + "…"


def plain_text(text: str, limit: Optional[int] = None) -> str:
    """Texte brut d'un résumé en Markdown, pour une notification.

    Titres, gras, italique, code, liens, citations et tableaux sont réduits à
    leur texte, les puces deviennent « • » et les lignes vides disparaissent ;
    les émojis restent. Au-delà de ``limit`` caractères, le texte est coupé
    sur un mot, suivi de « … ».
    """
    if not text:
        return ""
    t = text.replace("\r\n", "\n")
    t = _FENCE_RE.sub("", t)
    t = _RULE_RE.sub("", t)
    t = _TABLE_SEP_RE.sub("", t)
    t = _HEADING_RE.sub("", t)
    t = _QUOTE_RE.sub("", t)
    t = _BULLET_RE.sub("• ", t)
    t = _IMAGE_RE.sub(r"\1", t)
    t = _LINK_RE.sub(r"\1", t)
    t = _CODE_RE.sub(r"\1", t).replace("`", "")
    t = _STRONG_RE.sub(r"\2", t)
    t = _EMPHASIS_RE.sub(r"\2", t)
    t = _STRAY_RE.sub("", t)
    lines = (_SPACES_RE.sub(" ", _table_row(line)).strip() for line in t.split("\n"))
    t = "\n".join(line for line in lines if line)
    return _shorten(t, limit) if limit else t


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

    Le message passe en texte brut, 220 caractères au plus (``plain_text``).
    Ne lève jamais : toute erreur (backend absent, indisponible…) renvoie False.
    Sans danger depuis n'importe quel fil.
    """
    msg = plain_text(message, MESSAGE_LIMIT) or " "
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
