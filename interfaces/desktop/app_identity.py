"""
Logo de My_AI dans la barre des tâches (Windows, Linux) et le Dock (macOS)

Lancée par « python launch_unified.py », l'appli est un processus Python : sans
rien de plus, le système la range sous Python et lui en donne le logo.

  - Windows : la barre des tâches regroupe les fenêtres par AppUserModelID et
    montre l'icône de l'appli qu'il désigne, par défaut python.exe. Un
    identifiant propre au processus, posé avant la première fenêtre, lui fait
    prendre celle de la fenêtre (my_ai.ico, que pywebview lui donne).
  - macOS : pywebview passe l'icône à NSApplication (setApplicationIconImage_),
    qui la montre dans le Dock (my_ai.png).
  - Linux : pywebview pose l'icône sur la fenêtre GTK ou Qt (my_ai.png), que
    les barres des tâches X11 montrent. Sous Wayland, GNOME et KDE prennent
    celle du fichier .desktop qui porte l'app_id de la fenêtre : l'app_id
    devient « my_ai », et ~/.local/share/applications/my_ai.desktop, caché des
    menus, donne l'icône.

Rien ici n'arrête le lancement : au pire, le logo de Python revient.
"""

import ctypes
import os
import re
import sys
from pathlib import Path
from typing import Any, Mapping, Optional

from utils.desktop_notify import APP_ID
from utils.logger import setup_logger

logger = setup_logger("DesktopIdentity")

IS_WINDOWS = sys.platform.startswith("win")
IS_MACOS = sys.platform == "darwin"

APP_NAME = "My_AI"
ASSETS = Path(__file__).resolve().parent / "assets"
# Windows : toutes les tailles de la barre des tâches et de la barre de titre
ICO_PATH = ASSETS / "my_ai.ico"
# macOS et Linux : 256 px, la plus grande taille de l'icône Windows (GTK 3
# ignore sans rien dire, sous X11, une icône de 512 px)
PNG_PATH = ASSETS / "my_ai.png"
PROJECT_ROOT = Path(__file__).resolve().parents[2]
LAUNCHER = PROJECT_ROOT / "launch_unified.py"

# Windows : le même identifiant que les notifications (utils/desktop_notify.py)
WINDOWS_APP_ID = APP_ID
# Linux : nom du programme pour GTK, app_id de la fenêtre sous Wayland, nom du
# fichier .desktop et sa clé StartupWMClass (X11)
LINUX_APP_ID = "my_ai"
# Marque du fichier .desktop écrit par l'appli : un my_ai.desktop sans elle est
# celui de l'utilisateur, jamais réécrit
_GENERATED_KEY = "X-MyAI-Generated"
_CONTROL_CHARS = re.compile(r"[\x00-\x1f\x7f]")


def icon_path(platform: str = sys.platform) -> Optional[Path]:
    """Icône à passer à pywebview : .ico sous Windows, .png ailleurs (None si absente)."""
    path = ICO_PATH if platform.startswith("win") else PNG_PATH
    return path if path.is_file() else None


# ── Windows : AppUserModelID ────────────────────────────────────────────────


def _shell32() -> Any:
    return ctypes.windll.shell32  # type: ignore[attr-defined]


def set_windows_app_id(app_id: str = WINDOWS_APP_ID) -> bool:
    """AppUserModelID du processus : la barre des tâches montre l'icône de la fenêtre.

    À poser avant la première fenêtre du processus (documentation de Windows).
    """
    if not IS_WINDOWS:
        return False
    try:
        result = _shell32().SetCurrentProcessExplicitAppUserModelID(ctypes.c_wchar_p(app_id))
    except (AttributeError, OSError) as exc:
        logger.info("AppUserModelID non posé : %s", exc)
        return False
    return result == 0


# ── Linux : app_id de la fenêtre ────────────────────────────────────────────


def set_linux_app_id(app_id: str = LINUX_APP_ID) -> bool:
    """Nom du programme pour GTK : app_id de la fenêtre (Wayland), WM_CLASS (X11).

    À poser avant que pywebview n'importe Gtk, qui en tire aussi la classe de
    la fenêtre (« My_ai ») ; sinon GTK prend le nom du script lancé.
    """
    try:
        from gi.repository import GLib  # pylint: disable=import-outside-toplevel
    except Exception:  # pylint: disable=broad-except
        return False  # pas de PyGObject : pywebview prendra Qt
    try:
        GLib.set_prgname(app_id)
    except Exception as exc:  # pylint: disable=broad-except
        logger.info("Nom du programme GTK non posé : %s", exc)
        return False
    return True


def set_qt_app_id(native: Any, app_id: str = LINUX_APP_ID) -> bool:
    """app_id d'une fenêtre Qt, construite mais pas encore affichée (before_show).

    Qt le lit à l'affichage, dans QGuiApplication.desktopFileName ; sans lui,
    il prend le nom de l'exécutable (python3).
    """
    if type(native).__module__ != "webview.platforms.qt":
        return False
    try:
        from qtpy.QtGui import QGuiApplication  # pylint: disable=import-outside-toplevel

        QGuiApplication.setDesktopFileName(app_id)
    except Exception as exc:  # pylint: disable=broad-except
        logger.info("app_id de la fenêtre Qt non posé : %s", exc)
        return False
    return True


# ── Linux : fichier .desktop ────────────────────────────────────────────────


def _desktop_string(value: str) -> str:
    """Valeur de type chaîne d'un fichier .desktop : barre oblique inverse doublée."""
    return value.replace("\\", "\\\\")


def _exec_argument(value: str) -> str:
    """Argument de la clé Exec, entre guillemets (spécification Desktop Entry).

    Entre les guillemets, « " », « ` », « $ » et la barre oblique inverse en
    prennent une devant eux ; puis la valeur passe par l'échappement des
    chaînes (barre oblique inverse doublée), et « % » s'écrit « %% ».
    """
    quoted = '"' + re.sub(r'(["`$\\])', r"\\\1", value) + '"'
    return _desktop_string(quoted).replace("%", "%%")


def desktop_entry(python: str, launcher: str, icon: str, workdir: str) -> Optional[str]:
    """Contenu de my_ai.desktop ; None si un chemin contient un caractère de contrôle."""
    if any(_CONTROL_CHARS.search(value) for value in (python, launcher, icon, workdir)):
        return None
    return "\n".join((
        "[Desktop Entry]",
        "Type=Application",
        f"Name={APP_NAME}",
        f"Exec={_exec_argument(python)} {_exec_argument(launcher)}",
        f"Path={_desktop_string(workdir)}",
        f"Icon={_desktop_string(icon)}",
        "Terminal=false",
        # Hors des menus : il ne sert qu'à donner son icône à la fenêtre
        "NoDisplay=true",
        f"StartupWMClass={LINUX_APP_ID}",
        f"{_GENERATED_KEY}=true",
    )) + "\n"


def applications_dir(environ: Mapping[str, str] = os.environ) -> Path:
    """Dossier des fichiers .desktop de l'utilisateur : $XDG_DATA_HOME/applications."""
    data_home = environ.get("XDG_DATA_HOME", "")
    # Un chemin relatif ne compte pas (spécification XDG Base Directory)
    base = Path(data_home) if os.path.isabs(data_home) else Path.home() / ".local" / "share"
    return base / "applications"


def install_desktop_entry(content: str, folder: Path) -> Optional[Path]:
    """Écrit my_ai.desktop dans folder s'il a changé (dépôt déplacé, autre Python…).

    Returns:
        Le fichier à jour ; None s'il n'a pas pu s'écrire, ou s'il est celui
        de l'utilisateur (laissé tel quel)
    """
    path = folder / f"{LINUX_APP_ID}.desktop"
    try:
        if path.is_file():
            current = path.read_text(encoding="utf-8", errors="replace")
            if current == content:
                return path
            if f"\n{_GENERATED_KEY}=true" not in current:
                logger.info("%s n'a pas été écrit par My_AI : laissé tel quel", path)
                return None
        folder.mkdir(parents=True, exist_ok=True)
        # Écrit à côté puis renommé : le bureau relit le dossier dès qu'il change
        temporary = folder / f".{path.name}.tmp"
        temporary.write_text(content, encoding="utf-8", newline="\n")
        os.replace(temporary, path)
    except OSError as exc:
        logger.info("%s non écrit : %s", path, exc)
        return None
    return path


# ── Avant la première fenêtre ───────────────────────────────────────────────


def prepare() -> None:
    """Identité de l'appli auprès du système, avant que pywebview ne crée la fenêtre.

    macOS n'a rien à préparer : pywebview donne au Dock l'icône qu'on lui passe.
    """
    if IS_WINDOWS:
        set_windows_app_id()
    elif not IS_MACOS:  # Linux et autres bureaux freedesktop
        set_linux_app_id()
        content = desktop_entry(sys.executable, str(LAUNCHER), str(PNG_PATH), str(PROJECT_ROOT))
        if content is not None:
            install_desktop_entry(content, applications_dir())
