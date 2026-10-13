"""
Fenêtre native de l'appli : pywebview (WebView2, le Chromium d'Edge, sous Windows)

launch_unified.py --ui web l'ouvre sur le serveur local (server.py), qui
répond tout de suite : la fenêtre affiche l'écran de chargement pendant que
les étapes du lancement tournent dans leur fil (lifecycle.py). pywebview doit
tourner sur le fil principal.

La fenêtre ne quitte jamais l'appli : une page externe chargée dedans
hériterait de l'API que pywebview expose au JavaScript (shell_api.py).
  - Une navigation hors du serveur local est annulée.
  - Un lien web (http, https, mailto) s'ouvre dans le navigateur du système ;
    tout autre schéma (file:, javascript:…) est ignoré. pywebview passerait
    sinon n'importe quelle adresse à webbrowser.open, qui sous Windows lance
    un fichier local.

D'un lancement à l'autre, la fenêtre retient sa taille, sa position et son
état agrandi (data/.desktop_state.json, clé « window »).

Sans pywebview (paquet absent, WebView2 manquant…), open_window renvoie False
et le lanceur ouvre l'interface dans le navigateur par défaut.
"""

import ctypes
import os
import re
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, Iterable, Optional, Tuple
from urllib.parse import urlsplit

from interfaces.desktop.shell_api import ShellApi, open_external
from utils.logger import setup_logger

if TYPE_CHECKING:  # pragma: no cover
    from interfaces.desktop.lifecycle import DesktopApp

logger = setup_logger("DesktopWindow")

IS_WINDOWS = sys.platform.startswith("win")

WINDOW_TITLE = "My_AI"
# Pixels logiques (à 100 %) ; pywebview les convertit selon l'échelle de l'écran
MIN_SIZE = (900, 600)
DEFAULT_SIZE = (1280, 820)
# Fond de la fenêtre avant le chargement de la page : --bg-primary de
# frontend/src/styles/tokens.css (la page envoie ensuite ses couleurs à la
# barre de titre, cf. ShellApi.set_title_bar_colors)
BACKGROUND = "#0f0f0f"
TITLE_TEXT = "#ffffff"
ICON_PATH = Path(__file__).resolve().parent / "assets" / "my_ai.ico"

# Variables d'environnement de développement (jamais réglées pour l'utilisateur)
ENV_DEBUG = "MY_AI_WEBVIEW_DEBUG"  # outils de développement sans --dev
ENV_CDP_PORT = "MY_AI_WEBVIEW_CDP_PORT"  # pilotage par Playwright (connectOverCDP)

# Attributs DWM (dwmapi.h)
_DWMWA_USE_IMMERSIVE_DARK_MODE = 20
_DWMWA_USE_IMMERSIVE_DARK_MODE_OLD = 19  # Windows 10 avant 20H1
_DWMWA_CAPTION_COLOR = 35  # Windows 11
_DWMWA_TEXT_COLOR = 36  # Windows 11

_HEX_COLOR = re.compile(r"^#[0-9a-fA-F]{6}$")


# ── Disponibilité, DPI ──────────────────────────────────────────────────────


def pywebview_available() -> bool:
    """Vrai si pywebview s'importe (sans créer de fenêtre)."""
    try:
        import webview  # noqa: F401  # pylint: disable=import-outside-toplevel,unused-import
    except Exception:  # pylint: disable=broad-except
        return False
    return True


def enable_per_monitor_dpi() -> bool:
    """Rend le processus « DPI par écran » (v2), avant que pywebview crée sa fenêtre.

    pywebview n'appelle que SetProcessDPIAware (DPI du système) : à 125 % ou en
    passant sur un écran d'une autre échelle, Windows agrandirait la fenêtre
    comme une image et le texte serait flou. Une fois le régime fixé, l'appel
    de pywebview ne change plus rien.
    """
    if not IS_WINDOWS:
        return False
    try:
        user32 = ctypes.windll.user32
        # DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2 = -4 (Windows 10 1703+)
        if user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4)):
            return True
        # Déjà fixé (relance dans le même processus) : rien à faire
        current = user32.GetThreadDpiAwarenessContext()
        return bool(user32.AreDpiAwarenessContextsEqual(current, ctypes.c_void_p(-4)))
    except (AttributeError, OSError):
        try:
            # Windows 8.1 : PROCESS_PER_MONITOR_DPI_AWARE
            return ctypes.windll.shcore.SetProcessDpiAwareness(2) == 0
        except (AttributeError, OSError):
            return False


# ── Navigation : la fenêtre ne quitte jamais l'appli ────────────────────────


def app_origins(url: str, extra: Iterable[str] = ()) -> Tuple[str, ...]:
    """Origines que la fenêtre peut charger : celle de l'interface, et les extra."""
    origins = []
    for value in (url, *extra):
        parts = urlsplit(value)
        if parts.scheme and parts.netloc:
            origins.append(f"{parts.scheme.lower()}://{parts.netloc.lower()}")
    return tuple(dict.fromkeys(origins))


def is_app_url(url: str, origins: Iterable[str]) -> bool:
    """Vrai si la fenêtre peut charger cette adresse (page de l'appli)."""
    if url == "about:blank":
        return True
    try:
        parts = urlsplit(url)
    except ValueError:
        return False
    origin = f"{parts.scheme.lower()}://{parts.netloc.lower()}"
    return origin in tuple(origins)


_allowed_origins: Tuple[str, ...] = ()


def harden_edgechromium(origins: Iterable[str]) -> bool:
    """Bloque toute navigation hors de l'appli dans WebView2 (Windows).

    Remplace deux gestionnaires de pywebview, avant que la fenêtre ne soit
    créée : NewWindowRequested (target=_blank, window.open) et
    NavigationStarting (lien ordinaire, location.href…).
    """
    global _allowed_origins  # pylint: disable=global-statement
    _allowed_origins = tuple(origins)
    try:
        from webview.platforms import edgechromium  # pylint: disable=import-outside-toplevel
    except Exception as exc:  # pylint: disable=broad-except
        logger.info("WebView2 indisponible (%s) : navigation non surveillée", exc)
        return False

    chrome = edgechromium.EdgeChrome
    if getattr(chrome, "_my_ai_hardened", False):
        return True
    original_navigation = chrome.on_navigation_start

    def on_new_window_request(_self, _sender, args):
        # Jamais de seconde fenêtre : un lien web part dans le navigateur
        args.set_Handled(True)
        open_external(str(args.get_Uri()))

    def on_navigation_start(self, sender, args):
        uri = str(args.get_Uri())
        if not is_app_url(uri, _allowed_origins):
            args.set_Cancel(True)
            logger.info("Navigation hors de l'appli annulée : %.120s", uri)
            open_external(uri)
            return
        original_navigation(self, sender, args)

    chrome.on_new_window_request = on_new_window_request
    chrome.on_navigation_start = on_navigation_start
    chrome._my_ai_hardened = True  # pylint: disable=protected-access
    return True


# ── Barre de titre sombre (Windows) ─────────────────────────────────────────


def colorref(hex_color: str) -> Optional[int]:
    """Couleur « #rrggbb » au format COLORREF de Windows (0x00bbggrr)."""
    if not isinstance(hex_color, str) or not _HEX_COLOR.match(hex_color):
        return None
    red, green, blue = (int(hex_color[i:i + 2], 16) for i in (1, 3, 5))
    return (blue << 16) | (green << 8) | red


def _dwm_set_int(hwnd: int, attribute: int, value: int) -> bool:
    data = ctypes.c_int(value)
    try:
        result = ctypes.windll.dwmapi.DwmSetWindowAttribute(
            ctypes.c_void_p(hwnd), attribute, ctypes.byref(data), ctypes.sizeof(data)
        )
    except (AttributeError, OSError):
        return False
    return result == 0


def apply_title_bar(hwnd: int, background: str = BACKGROUND, text: str = TITLE_TEXT) -> bool:
    """Barre de titre en mode sombre, de la couleur du fond de l'appli (Windows 11)."""
    if not IS_WINDOWS or not hwnd:
        return False
    dark = _dwm_set_int(hwnd, _DWMWA_USE_IMMERSIVE_DARK_MODE, 1) or _dwm_set_int(
        hwnd, _DWMWA_USE_IMMERSIVE_DARK_MODE_OLD, 1
    )
    caption, caption_text = colorref(background), colorref(text)
    if caption is not None:
        _dwm_set_int(hwnd, _DWMWA_CAPTION_COLOR, caption)
    if caption_text is not None:
        _dwm_set_int(hwnd, _DWMWA_TEXT_COLOR, caption_text)
    return dark


def _keep_title_bar_dark() -> None:
    """pywebview suit le thème de Windows (clair ou sombre) : l'appli est toujours sombre."""
    try:
        from webview.platforms import winforms  # pylint: disable=import-outside-toplevel
    except Exception:  # pylint: disable=broad-except
        return
    form = winforms.BrowserView.BrowserForm
    form.is_dark_theme = lambda _self: True


# ── Taille et position retenues ─────────────────────────────────────────────


class WindowGeometry:
    """Taille, position (pixels physiques) et état agrandi de la fenêtre."""

    def __init__(self, saved: Optional[Dict[str, Any]] = None):
        saved = saved if isinstance(saved, dict) else {}
        self.bounds: Optional[Tuple[int, int, int, int]] = None
        values = [saved.get(key) for key in ("x", "y", "width", "height")]
        if all(isinstance(v, int) for v in values) and values[2] > 0 and values[3] > 0:
            self.bounds = tuple(values)  # type: ignore[assignment]
        # Premier lancement : agrandie, comme l'interface Tk
        self.maximized = bool(saved.get("maximized", True))

    def to_dict(self) -> Dict[str, Any]:
        data: Dict[str, Any] = {"maximized": self.maximized}
        if self.bounds is not None:
            data.update(zip(("x", "y", "width", "height"), self.bounds))
        return data

    def visible(self) -> bool:
        """Vrai si les bornes retenues tombent sur un écran branché (Windows)."""
        if self.bounds is None or not IS_WINDOWS:
            return False

        class _Rect(ctypes.Structure):  # pylint: disable=too-few-public-methods
            _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long),
                        ("right", ctypes.c_long), ("bottom", ctypes.c_long)]

        x, y, width, height = self.bounds
        # Au moins la barre de titre doit être visible
        rect = _Rect(x + 40, y, x + width - 40, y + 40)
        try:
            monitor = ctypes.windll.user32.MonitorFromRect(ctypes.byref(rect), 0)
        except (AttributeError, OSError):
            return False
        return bool(monitor)

    def apply(self, form) -> None:
        """Pose les bornes retenues sur le formulaire WinForms, avant son affichage."""
        # pylint: disable=import-outside-toplevel
        import System.Windows.Forms as WinForms  # type: ignore
        from System.Drawing import Rectangle  # type: ignore

        if self.visible():
            x, y, width, height = self.bounds  # type: ignore[misc]
            form.StartPosition = WinForms.FormStartPosition.Manual
            form.Bounds = Rectangle(x, y, width, height)
        if self.maximized:
            form.WindowState = WinForms.FormWindowState.Maximized

    def capture(self, form) -> None:
        """Relève les bornes du formulaire à la fermeture (fil de l'interface)."""
        state = str(form.WindowState)
        if state == "Minimized":
            # Réduite : garder l'état d'avant (RestoreBounds donne la taille normale)
            bounds = form.RestoreBounds
        elif state == "Maximized":
            self.maximized = True
            bounds = form.RestoreBounds
        else:
            self.maximized = False
            bounds = form.Bounds
        if bounds.Width > 0 and bounds.Height > 0:
            self.bounds = (int(bounds.X), int(bounds.Y), int(bounds.Width), int(bounds.Height))


# ── Fenêtre ─────────────────────────────────────────────────────────────────


def _debug_requested(dev: bool) -> bool:
    return dev or os.environ.get(ENV_DEBUG, "") == "1"


def open_window(app: "DesktopApp", url: str, *, dev_origins: Iterable[str] = ()) -> bool:
    """Ouvre la fenêtre et bloque jusqu'à sa fermeture (fil principal).

    Returns:
        False si pywebview est indisponible : le lanceur se rabat sur le navigateur
    """
    try:
        import webview  # pylint: disable=import-outside-toplevel
    except Exception as exc:  # pylint: disable=broad-except
        logger.warning("pywebview indisponible : %s", exc)
        return False

    debug = _debug_requested(app.dev)
    enable_per_monitor_dpi()
    if IS_WINDOWS:
        harden_edgechromium(app_origins(url, dev_origins))
        _keep_title_bar_dark()

    webview.settings["OPEN_EXTERNAL_LINKS_IN_BROWSER"] = True
    webview.settings["OPEN_DEVTOOLS_IN_DEBUG"] = False
    webview.settings["ALLOW_DOWNLOADS"] = False
    webview.settings["ALLOW_FILE_URLS"] = False
    # Pilotage par Playwright (vérifications) : seulement sur demande explicite,
    # sans le mode debug, pour garder les raccourcis de l'utilisateur
    cdp_port = os.environ.get(ENV_CDP_PORT, "")
    if cdp_port.isdigit():
        logger.warning("Port de débogage WebView2 ouvert (%s) : réservé aux vérifications", cdp_port)
        webview.settings["REMOTE_DEBUGGING_PORT"] = int(cdp_port)

    geometry = WindowGeometry(app.state.get("window"))
    width, height = DEFAULT_SIZE
    handle = {"hwnd": 0}

    def title_bar(background: str, text: str) -> bool:
        return apply_title_bar(handle["hwnd"], background, text)

    main_window = webview.create_window(
        WINDOW_TITLE,
        url,
        js_api=ShellApi(title_bar=title_bar),
        width=width,
        height=height,
        min_size=MIN_SIZE,
        background_color=BACKGROUND,
        text_select=True,
        zoomable=True,
    )
    if main_window is None:
        return False

    # pywebview ne passe la fenêtre qu'à un paramètre nommé « window »
    def before_show(window):
        form = getattr(window, "native", None)
        if form is None or not IS_WINDOWS:
            return
        try:
            geometry.apply(form)
        except Exception as exc:  # pylint: disable=broad-except
            logger.warning("Taille de la fenêtre non restaurée : %s", exc)
        handle["hwnd"] = form.Handle.ToInt32()
        apply_title_bar(handle["hwnd"])

    def closing(window):
        form = getattr(window, "native", None)
        if form is not None and IS_WINDOWS:
            try:
                geometry.capture(form)
                app.state.set("window", geometry.to_dict())
            except Exception as exc:  # pylint: disable=broad-except
                logger.warning("Taille de la fenêtre non enregistrée : %s", exc)

    main_window.events.before_show += before_show
    main_window.events.closing += closing

    try:
        webview.start(
            debug=debug,
            private_mode=True,
            icon=str(ICON_PATH) if ICON_PATH.is_file() else None,
        )
    except Exception as exc:  # pylint: disable=broad-except
        # WebView2 absent, pythonnet incompatible… : repli sur le navigateur
        logger.error("Fenêtre pywebview en échec : %s", exc)
        return False
    return True
