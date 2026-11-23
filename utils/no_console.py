"""
Lancement sans console : My_AI ouvert depuis son épingle de la barre des tâches

Lancé depuis une ligne de commande (launch.bat, « python launch_unified.py »),
My_AI garde sa console, où défilent ses messages. L'épingle de la barre des
tâches de Windows le lance par pythonw, sans console (relaunch_command,
interfaces/desktop/app_identity.py) : sys.stdout et sys.stderr valent alors
None. start() prépare ce lancement :

  - les sorties (print, journaux, traces d'erreur, et celles des commandes
    lancées) vont dans logs/console_AAAAMMJJ.log, à la suite ;
  - les commandes console (taskkill, pip, ollama, ssh…) tournent sans fenêtre :
    sans console à partager, chacune ouvrirait la sienne ;
  - une erreur qui arrête le lancement s'affiche dans une boîte de dialogue
    (show_error), avec le nom de ce fichier ;
  - un avertissement qui ne l'arrête pas passe par une notification du système
    (show_notice), sans rien bloquer.

Avec une console, rien ne change. Ce module tourne avant la vérification de
la version de Python : bibliothèque standard seulement, et une syntaxe que
les anciens Python lisent encore.
"""

import ctypes
import functools
import os
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Any, Optional

IS_WINDOWS = sys.platform.startswith("win")

APP_NAME = "My_AI"
# Un fichier par jour, comme les journaux (utils/logger.py)
LOG_PREFIX = "console_"

# Options de CreateProcess
CREATE_NO_WINDOW = 0x08000000
# CREATE_NEW_CONSOLE, DETACHED_PROCESS : la commande a choisi sa console
_OWN_CONSOLE = 0x00000010 | 0x00000008
# Rangs de stdin et de creationflags parmi les paramètres positionnels de subprocess.Popen
_STDIN_INDEX = 3
_CREATIONFLAGS_INDEX = 13

# Sorties standard et d'erreur du processus (GetStdHandle, SetStdHandle)
_STD_HANDLES = ((1, -11), (2, -12))

# Boîtes de dialogue (MessageBoxW)
_MB_ICONERROR = 0x10
_MB_ICONWARNING = 0x30
_MB_ICONINFORMATION = 0x40
_MB_SETFOREGROUND = 0x10000

_STATE: dict = {"active": False, "log": None, "stream": None}


def has_console() -> bool:
    """Faux sous pythonw : ni sortie standard ni sortie d'erreur."""
    return sys.stdout is not None and sys.stderr is not None


def active() -> bool:
    """Vrai si ce lancement se fait sans console (start() l'a préparé)."""
    return bool(_STATE["active"])


def log_path() -> Optional[Path]:
    """Fichier des sorties d'un lancement sans console (None sinon)."""
    return _STATE["log"]


def start(logs_dir: Path = Path("logs")) -> bool:
    """Prépare un lancement sans console ; ne fait rien avec une console.

    Returns:
        True si le lancement se fait sans console
    """
    if _STATE["active"]:
        return True
    if has_console():
        return False
    _STATE["log"] = redirect_output(logs_dir)
    _STATE["active"] = True
    hide_child_consoles()
    _show_crashes()
    return True


# ── Sorties ─────────────────────────────────────────────────────────────────


def redirect_output(logs_dir: Path) -> Optional[Path]:
    """Sorties standard et d'erreur vers logs/console_AAAAMMJJ.log, à la suite.

    Les commandes lancées sans redirection y écrivent aussi : le fichier devient
    la sortie standard du processus, dont elles héritent.

    Returns:
        Le fichier ; None s'il n'a pas pu s'ouvrir (sorties perdues)
    """
    path: Optional[Path] = logs_dir / f"{LOG_PREFIX}{time.strftime('%Y%m%d')}.log"
    try:
        logs_dir.mkdir(parents=True, exist_ok=True)
        # Écrit ligne à ligne : os._exit, à la fermeture de l'appli, ne vide rien
        stream = open(  # pylint: disable=consider-using-with
            path, "a", encoding="utf-8", errors="backslashreplace", buffering=1
        )
    except OSError:
        path = None
        stream = open(os.devnull, "w", encoding="utf-8")  # pylint: disable=consider-using-with
    stream.write(f"\n===== {time.strftime('%Y-%m-%d %H:%M:%S')} : lancement sans console "
                 f"({sys.executable}, pid {os.getpid()}) =====\n")
    _STATE["stream"] = stream
    _share_with_children(stream)
    if sys.stdout is None:
        sys.stdout = stream
    if sys.stderr is None:
        sys.stderr = stream
    if sys.stdin is None:
        # Une lecture rend la fin du fichier, au lieu de planter sur None
        sys.stdin = open(os.devnull, encoding="utf-8")  # pylint: disable=consider-using-with
    return path


def _share_with_children(stream) -> None:
    """Le fichier devient la sortie standard et d'erreur du processus (Windows).

    Descripteurs 1 et 2 : ce qu'écrivent les bibliothèques en C ; sorties
    standard du processus : ce dont héritent les commandes lancées.
    """
    if not IS_WINDOWS:
        return
    try:
        import msvcrt  # pylint: disable=import-outside-toplevel

        for descriptor, std_handle in _STD_HANDLES:
            os.dup2(stream.fileno(), descriptor)
            ctypes.windll.kernel32.SetStdHandle(  # type: ignore[attr-defined]
                std_handle, ctypes.c_void_p(msvcrt.get_osfhandle(descriptor))
            )
    except (AttributeError, OSError, ValueError):
        pass  # fichier de secours (os.devnull) ou système sans ces appels


# ── Commandes lancées ───────────────────────────────────────────────────────


def hide_child_consoles() -> bool:
    """Commandes console lancées sans fenêtre (CREATE_NO_WINDOW), sauf console demandée.

    Sans console à partager, une commande console (taskkill, pip, ollama,
    ssh…) ouvrirait la sienne, qui clignoterait ou resterait ouverte. Vaut
    aussi pour les bibliothèques : subprocess.Popen est changé pour tout ce
    processus. Sans effet sur une appli à fenêtres. Une commande lancée sans
    redirection écrirait dans sa console invisible : ses sorties vont dans le
    fichier des sorties.
    """
    if not IS_WINDOWS:
        return False
    original = subprocess.Popen.__init__
    if getattr(original, "_my_ai_no_window", False):
        return True

    @functools.wraps(original)
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        if len(args) <= _CREATIONFLAGS_INDEX:  # creationflags absent ou nommé
            flags = kwargs.get("creationflags") or 0
            if not flags & _OWN_CONSOLE:
                kwargs["creationflags"] = flags | CREATE_NO_WINDOW
                output = _STATE.get("stream")
                unredirected = all(kwargs.get(name) is None
                                   for name in ("stdin", "stdout", "stderr"))
                if output is not None and len(args) <= _STDIN_INDEX and unredirected:
                    kwargs.update(stdin=subprocess.DEVNULL, stdout=output, stderr=output)
        original(self, *args, **kwargs)

    __init__._my_ai_no_window = True  # type: ignore[attr-defined]
    subprocess.Popen.__init__ = __init__  # type: ignore[method-assign]
    return True


# ── Boîtes de dialogue ──────────────────────────────────────────────────────


def _tr(key: str, fallback: str, **params: Any) -> str:
    """Texte dans la langue de l'appli ; en anglais si core.i18n ne se charge pas."""
    try:
        from core.i18n import tr  # pylint: disable=import-outside-toplevel

        text = tr(key, **params)
    except Exception:  # pylint: disable=broad-except
        text = key
    return fallback.format(**params) if text == key else text


def _message_box(message: str, icon: int) -> bool:
    if not IS_WINDOWS:
        return False
    try:
        ctypes.windll.user32.MessageBoxW(  # type: ignore[attr-defined]
            None, message, APP_NAME, icon | _MB_SETFOREGROUND
        )
    except (AttributeError, OSError):
        return False
    return True


def show_error(message: str, *, warning: bool = False) -> bool:
    """Sans console, montre une erreur du lancement dans une boîte de dialogue.

    Avec une console, ne fait rien : le message y est déjà écrit. La boîte
    donne le fichier des sorties, où se trouve le détail.

    Returns:
        True si la boîte s'est affichée (et a été refermée)
    """
    if not _STATE["active"]:
        return False
    log = _STATE["log"]
    if log is not None:
        details = _tr("launch.logFile", "Details: {path}", path=Path(log).resolve())
        message = f"{message}\n\n{details}"
    return _message_box(message, _MB_ICONWARNING if warning else _MB_ICONERROR)


def show_notice(title: str, message: str) -> bool:
    """Sans console, montre un avertissement du lancement sans rien bloquer.

    Notification du système (utils/desktop_notify.py), envoyée d'un fil à part
    : le lancement n'attend ni ne dépend d'elle. Avec une console, ne fait
    rien : le message y est déjà écrit. Sans moyen de notifier (winotify pas
    encore installé…), le message reste dans le fichier des sorties.

    Returns:
        True si la notification est partie (son affichage n'est pas vérifié)
    """
    if not _STATE["active"]:
        return False

    def notify() -> None:
        try:
            from utils.desktop_notify import notify_desktop  # pylint: disable=import-outside-toplevel

            notify_desktop(title, message)
        except Exception:  # pylint: disable=broad-except
            pass

    threading.Thread(target=notify, name="launch-notice", daemon=True).start()
    return True


def wait_for_dismiss(message: str) -> bool:
    """Sans console, montre un message et attend qu'on le referme.

    Remplace la console qu'on fermerait (Ctrl+C) pour quitter l'appli, quand
    l'interface s'ouvre dans le navigateur.

    Returns:
        False avec une console (rien d'affiché)
    """
    if not _STATE["active"]:
        return False
    return _message_box(message, _MB_ICONINFORMATION)


def _show_crashes() -> None:
    """Une erreur qui arrête le lancement s'affiche, en plus de sa trace (fichier)."""
    previous = sys.excepthook

    def excepthook(kind, value, traceback):
        previous(kind, value, traceback)
        if not issubclass(kind, KeyboardInterrupt):
            show_error(_tr("launch.failed", "My_AI could not start: {error}", error=value))

    sys.excepthook = excepthook
