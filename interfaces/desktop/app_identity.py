"""
Logo de My_AI dans la barre des tâches (Windows, Linux) et le Dock (macOS)

Lancée par « python launch_unified.py », l'appli est un processus Python : sans
rien de plus, le système la range sous Python et lui en donne le logo.

  - Windows : la barre des tâches regroupe les fenêtres par AppUserModelID et
    montre l'icône de l'appli qu'il désigne, par défaut python.exe. Un
    identifiant propre au processus, posé avant la première fenêtre, lui fait
    prendre celle de la fenêtre (my_ai.ico, que pywebview lui donne). Le nom
    du bouton et ce que lance un My_AI épinglé viennent des propriétés de
    relance de la fenêtre, posées avant son affichage : « My_AI », et
    launch_unified.py lancé par pythonw, sans console.
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
import uuid
from pathlib import Path
from typing import Any, List, Mapping, Optional, Tuple

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


# ── Windows : nom du bouton et épingle (propriétés de la fenêtre) ───────────
#
# Faute de raccourci qui porte l'AppUserModelID « My_AI », la barre des tâches
# tire le nom du bouton de python.exe (« Python »), et épinglerait python.exe
# sans arguments. Les propriétés de relance de la fenêtre lui donnent son nom,
# son icône et la commande d'un My_AI épinglé ; Windows ne les lit que sur une
# fenêtre qui a son propre AppUserModelID, posé après elles.

# Propriétés System.AppUserModel.* (propkey.h) : même GUID, numéro propre à chacune
_APP_USER_MODEL = "{9F4C2855-9F79-4B39-A8D0-E1D42DE1D5F3}"
PID_RELAUNCH_COMMAND = 2
PID_RELAUNCH_ICON = 3
PID_RELAUNCH_NAME = 4
PID_APP_ID = 5
_IID_PROPERTY_STORE = "{886D8EEB-8CF2-4446-8D02-CDBA1DBDCF99}"
_VT_EMPTY = 0
_VT_LPWSTR = 31
_HRESULT = ctypes.c_long


def relaunch_command(python: str = sys.executable, launcher: Path = LAUNCHER) -> Optional[str]:
    """Commande d'un My_AI épinglé : launch_unified.py lancé par pythonw, sans console.

    pythonw.exe est à côté de python.exe (installation comme venv) ; à défaut,
    python.exe, avec sa console. launch_unified.py se place lui-même dans son
    dossier : celui d'un raccourci épinglé n'est pas garanti.
    """
    if not python:
        return None
    executable = Path(python)
    windowed = executable.with_name("pythonw.exe")
    if windowed.is_file():
        executable = windowed
    # Guillemets toujours : un chemin Windows ne peut pas en contenir
    return f'"{executable}" "{launcher}"'


def window_properties(command: str, icon: Path = ICO_PATH) -> List[Tuple[int, str]]:
    """Propriétés de la fenêtre, dans l'ordre où les poser.

    Les propriétés de relance d'abord, l'AppUserModelID ensuite (documentation
    de Windows) : le poser fait relire la fenêtre à la barre des tâches.
    """
    return [
        (PID_RELAUNCH_COMMAND, command),
        (PID_RELAUNCH_NAME, APP_NAME),
        (PID_RELAUNCH_ICON, f"{icon},0"),  # .ico : numéro de l'image, sans « - »
        (PID_APP_ID, WINDOWS_APP_ID),
    ]


class _Guid(ctypes.Structure):  # pylint: disable=too-few-public-methods
    _fields_ = [("data1", ctypes.c_uint32), ("data2", ctypes.c_uint16),
                ("data3", ctypes.c_uint16), ("data4", ctypes.c_ubyte * 8)]


def _guid(text: str) -> _Guid:
    return _Guid.from_buffer_copy(uuid.UUID(text).bytes_le)


class _PropertyKey(ctypes.Structure):  # pylint: disable=too-few-public-methods
    _fields_ = [("fmtid", _Guid), ("pid", ctypes.c_uint32)]


class _PropVariantValue(ctypes.Union):  # pylint: disable=too-few-public-methods
    # Le plus grand membre de l'union de PROPVARIANT : un compte et un pointeur
    _fields_ = [("pwszVal", ctypes.c_void_p), ("_size", ctypes.c_void_p * 2)]


class _PropVariant(ctypes.Structure):  # pylint: disable=too-few-public-methods
    """PROPVARIANT, lu ou écrit ici comme chaîne (VT_LPWSTR) ou vide (VT_EMPTY)."""

    _fields_ = [("vt", ctypes.c_uint16), ("reserved", ctypes.c_uint16 * 3),
                ("value", _PropVariantValue)]


class WindowPropertyStore:
    """IPropertyStore d'une fenêtre (SHGetPropertyStoreForWindow), appelé par sa vtable.

    Une valeur posée est aussitôt rangée sur la fenêtre : pas de Commit.
    """

    # Rangs des méthodes dans la vtable (IUnknown, puis IPropertyStore)
    _RELEASE, _GET_COUNT, _GET_VALUE, _SET_VALUE = 2, 3, 5, 6

    def __init__(self, hwnd: int):
        prototype = ctypes.WINFUNCTYPE(_HRESULT, ctypes.c_void_p, ctypes.POINTER(_Guid),
                                       ctypes.POINTER(ctypes.c_void_p))
        get_store = prototype(("SHGetPropertyStoreForWindow", _shell32()))
        self._pointer = ctypes.c_void_p()
        self._check(get_store(hwnd, ctypes.byref(_guid(_IID_PROPERTY_STORE)),
                              ctypes.byref(self._pointer)), "SHGetPropertyStoreForWindow")
        if not self._pointer:
            raise OSError("SHGetPropertyStoreForWindow : aucun IPropertyStore")

    @staticmethod
    def _check(result: int, name: str) -> None:
        if result < 0:
            raise OSError(f"{name} : HRESULT 0x{result & 0xFFFFFFFF:08X}")

    def _method(self, index: int, restype: Any, *argtypes: Any) -> Any:
        vtable = ctypes.cast(self._pointer, ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p)))
        return ctypes.WINFUNCTYPE(restype, ctypes.c_void_p, *argtypes)(vtable.contents[index])

    @staticmethod
    def _key(pid: int) -> _PropertyKey:
        return _PropertyKey(_guid(_APP_USER_MODEL), pid)

    def set(self, pid: int, value: Optional[str]) -> None:
        """Pose une propriété System.AppUserModel ; None la retire (VT_EMPTY)."""
        variant = _PropVariant()
        text = None
        if value is not None:
            text = ctypes.create_unicode_buffer(value)
            variant.vt = _VT_LPWSTR
            variant.value.pwszVal = ctypes.cast(text, ctypes.c_void_p).value
        set_value = self._method(self._SET_VALUE, _HRESULT, ctypes.POINTER(_PropertyKey),
                                 ctypes.POINTER(_PropVariant))
        # La fenêtre garde sa copie de la chaîne : text peut disparaître ensuite
        self._check(set_value(self._pointer, ctypes.byref(self._key(pid)),
                              ctypes.byref(variant)), "IPropertyStore::SetValue")

    def get(self, pid: int) -> Optional[str]:
        """Valeur d'une propriété System.AppUserModel (None si absente)."""
        variant = _PropVariant()
        get_value = self._method(self._GET_VALUE, _HRESULT, ctypes.POINTER(_PropertyKey),
                                 ctypes.POINTER(_PropVariant))
        self._check(get_value(self._pointer, ctypes.byref(self._key(pid)),
                              ctypes.byref(variant)), "IPropertyStore::GetValue")
        try:
            if variant.vt == _VT_LPWSTR and variant.value.pwszVal:
                return ctypes.wstring_at(variant.value.pwszVal)
            return None
        finally:
            ole32 = ctypes.windll.ole32  # type: ignore[attr-defined]
            ole32.PropVariantClear(ctypes.byref(variant))

    def count(self) -> int:
        """Nombre de propriétés posées sur la fenêtre."""
        number = ctypes.c_uint32()
        get_count = self._method(self._GET_COUNT, _HRESULT, ctypes.POINTER(ctypes.c_uint32))
        self._check(get_count(self._pointer, ctypes.byref(number)), "IPropertyStore::GetCount")
        return number.value

    def close(self) -> None:
        if self._pointer:
            self._method(self._RELEASE, ctypes.c_ulong)(self._pointer)
            self._pointer = ctypes.c_void_p()


def _apply_window_properties(hwnd: int, values: List[Tuple[int, Optional[str]]],
                             action: str) -> bool:
    if not IS_WINDOWS or not hwnd:
        return False
    try:
        store = WindowPropertyStore(hwnd)
    except (AttributeError, OSError) as exc:
        logger.info("Propriétés de la fenêtre non %s : %s", action, exc)
        return False
    try:
        for pid, value in values:
            store.set(pid, value)
    except OSError as exc:
        logger.info("Propriétés de la fenêtre non %s : %s", action, exc)
        return False
    finally:
        store.close()
    return True


def set_window_identity(hwnd: int, command: Optional[str] = None) -> bool:
    """Bouton « My_AI » de la fenêtre dans la barre des tâches, et ce que lance son épingle.

    À poser avant l'affichage de la fenêtre, et à retirer avant sa fermeture
    (clear_window_identity).

    Args:
        hwnd: fenêtre (formulaire WinForms de pywebview)
        command: commande de relance (relaunch_command() par défaut)
    """
    command = relaunch_command() if command is None else command
    if not command:
        return False
    return _apply_window_properties(hwnd, list(window_properties(command)), "posées")


def clear_window_identity(hwnd: int) -> bool:
    """Retire les propriétés de set_window_identity, avant la fermeture de la fenêtre.

    La documentation de SHGetPropertyStoreForWindow le demande : sinon, les
    ressources de ces propriétés ne sont pas rendues au système.
    """
    pids = [pid for pid, _value in window_properties("")]
    return _apply_window_properties(hwnd, [(pid, None) for pid in pids], "retirées")


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
