"""
Visionneuses Office dans la fenêtre (volet d'aperçu)

Word, Excel et PowerPoint s'affichent avec la visionneuse de Windows
(preview_handler.py), dans une fenêtre enfant de la fenêtre pywebview posée
au-dessus de WebView2, à la place que la page réserve dans le volet. La fenêtre
de l'appli est DPI par écran (window.enable_per_monitor_dpi) : la visionneuse y
dessine à l'échelle de l'écran. Si elle ne l'est pas (Windows trop ancien),
repli sur l'hôte « popup » DPI par écran de dpi_host.py, possédé par la
fenêtre, posé à l'écran sur la place et qui suit ses déplacements, comme Tk.

La page ne peut rien dessiner par-dessus une fenêtre enfant : elle la masque
sous ses dialogues, menus et notifications (place(..., visible=False)), et la
recale quand le volet bouge. Elle ne parle qu'au pont de la fenêtre
(shell_api.py), qui ne connaît que les documents acceptés par le serveur
(aperçus « native » de previews.py).

Fils : la fenêtre hôte appartient au fil de l'interface WinForms (Invoke) ; la
visionneuse, objet COM, à son fil « appartement monothread »
(AsyncNativePreview) ; show() attend le résultat sur le fil de l'appel
(pywebview appelle le pont dans un fil à part).
"""

import threading
from typing import Any, Callable, Dict, Optional, Tuple

from interfaces.desktop.dpi_host import DpiAwareHost, client_origin, is_dpi_virtualized
from interfaces.desktop.preview_handler import (COMTYPES_AVAILABLE, IS_WINDOWS,
                                                 AsyncNativePreview)
from utils.logger import setup_logger

logger = setup_logger("NativeViewer")

# Démarrage à froid de Word, Excel ou PowerPoint : quelques secondes, rarement plus
OPEN_TIMEOUT = 45.0
# Fermeture de l'appli : ne pas laisser Office orphelin, sans bloquer trop longtemps
SHUTDOWN_WAIT = 2.0
_MAX_SIDE = 32_000

Rect = Tuple[int, int, int, int]


def parse_rect(rect: Any) -> Optional[Rect]:
    """{x, y, width, height} en pixels de l'écran → tuple borné, ou None si illisible."""
    if not isinstance(rect, dict):
        return None
    try:
        x, y, width, height = (int(rect[key]) for key in ("x", "y", "width", "height"))
    except (KeyError, TypeError, ValueError):
        return None
    if width < 1 or height < 1:
        return None
    x, y = (max(-_MAX_SIDE, min(_MAX_SIDE, value)) for value in (x, y))
    return x, y, min(width, _MAX_SIDE), min(height, _MAX_SIDE)


class FormWindow:
    """Fenêtre pywebview (formulaire WinForms) : fil de l'interface, handle, déplacements."""

    def __init__(self, form, background: str):
        """
        Args:
            form: formulaire pywebview (window.native)
            background: fond « #rrggbb » de l'hôte, visible le temps du chargement
        """
        self.form = form
        self.background = background

    def invoke(self, action: Callable[[], Any]) -> Any:
        """Exécute sur le fil de l'interface WinForms et rend le résultat."""
        # pylint: disable=import-outside-toplevel,import-error
        from System import Action  # type: ignore

        result: Dict[str, Any] = {}

        def run():
            try:
                result["value"] = action()
            except Exception as exc:  # pylint: disable=broad-except
                result["error"] = exc

        if self.form.InvokeRequired:
            self.form.Invoke(Action(run))
        else:
            run()
        if "error" in result:
            raise result["error"]
        return result.get("value")

    def hwnd(self) -> int:
        """HWND du formulaire (fil de l'interface)."""
        return int(self.form.Handle.ToInt64())

    def on_move(self, callback: Callable[[], None]) -> None:
        """callback() sur le fil de l'interface à chaque déplacement du formulaire."""
        # pylint: disable=import-outside-toplevel,import-error
        from System import EventHandler  # type: ignore

        def subscribe():
            self.form.Move += EventHandler(lambda _sender, _args: callback())

        self.invoke(subscribe)


class WinFormsHost:
    """Fenêtre hôte : un Panel WinForms au-dessus du contrôle WebView2 de la fenêtre."""

    def __init__(self, window: FormWindow):
        self._window = window
        self._panel = None

    def _ensure(self):
        """Panel créé à la première visionneuse, au-dessus de WebView2."""
        if self._panel is not None and not self._panel.IsDisposed:
            return self._panel
        # pylint: disable=import-outside-toplevel,import-error
        from System.Drawing import Color  # type: ignore
        from System.Windows.Forms import Panel  # type: ignore

        value = self._window.background.lstrip("#")
        panel = Panel()
        panel.BackColor = Color.FromArgb(int(value[0:2], 16), int(value[2:4], 16),
                                         int(value[4:6], 16))
        panel.TabStop = False
        panel.Visible = False
        self._window.form.Controls.Add(panel)
        panel.BringToFront()
        self._panel = panel
        return panel

    def handle(self) -> int:
        """HWND de l'hôte (créé au besoin)."""
        def run():
            return self._ensure().Handle.ToInt64()

        return int(self._window.invoke(run))

    def place(self, rect: Rect, visible: bool) -> None:
        """Position et taille (pixels de l'écran, dans la zone client), affiché ou non."""
        def run():
            panel = self._ensure()
            panel.SetBounds(*rect)
            panel.Visible = visible
            if visible:
                panel.BringToFront()

        self._window.invoke(run)

    def hide(self) -> None:
        """Masque l'hôte, sans le détruire."""
        def run():
            if self._panel is not None and not self._panel.IsDisposed:
                self._panel.Visible = False

        self._window.invoke(run)


class PopupHost:
    """
    Repli, fenêtre pas DPI par écran : hôte « popup » de dpi_host.py, possédé
    par la fenêtre (ni barre des tâches ni Alt+Tab), posé à l'écran sur la
    place, recalé quand la fenêtre se déplace.
    """

    def __init__(self, window):
        """
        Args:
            window: FormWindow (invoke, hwnd, on_move, background)
        """
        self._window = window
        self._host: Optional[DpiAwareHost] = None
        self._rect: Optional[Rect] = None
        self._visible = False
        window.on_move(self._follow)

    def _screen(self, rect: Rect) -> Rect:
        origin_x, origin_y = client_origin(self._window.hwnd()) or (0, 0)
        return origin_x + rect[0], origin_y + rect[1], rect[2], rect[3]

    def _ensure(self) -> DpiAwareHost:
        if self._host is None or not self._host.alive:
            self._host = DpiAwareHost(self._window.hwnd(), self._window.background)
        return self._host

    def handle(self) -> int:
        """HWND de l'hôte (créé au besoin)."""
        return int(self._window.invoke(lambda: self._ensure().hwnd or 0))

    def place(self, rect: Rect, visible: bool) -> None:
        """Place dans la zone client (pixels de l'écran) → rectangle de l'écran."""
        def run():
            self._rect, self._visible = rect, visible
            self._ensure().place(self._screen(rect), visible)

        self._window.invoke(run)

    def hide(self) -> None:
        """Masque l'hôte, sans le détruire."""
        def run():
            self._visible = False
            if self._host is not None:
                self._host.hide()

        self._window.invoke(run)

    def _follow(self) -> None:
        """Fenêtre déplacée (fil de l'interface) : l'hôte la suit."""
        if self._rect is not None and self._host is not None:
            self._host.place(self._screen(self._rect), self._visible)


def window_host(form, background: str):
    """Hôte de la visionneuse : enfant de la fenêtre si elle est DPI par écran, sinon popup."""
    window = FormWindow(form, background)
    if window.invoke(lambda: is_dpi_virtualized(window.hwnd())):
        logger.info("Fenêtre sans DPI par écran : visionneuses dans un hôte popup")
        return PopupHost(window)
    return WinFormsHost(window)


class NativeViewer:  # pylint: disable=too-many-instance-attributes
    """Une visionneuse à la fois, chargée masquée, affichée à la demande de la page."""

    def __init__(self, host_factory: Callable[[], Optional[Any]],
                 preview_factory: Callable[[], Any] = AsyncNativePreview,
                 open_timeout: float = OPEN_TIMEOUT):
        """
        Args:
            host_factory: hôte (handle, place, hide), None sans fenêtre
            preview_factory: visionneuse asynchrone (AsyncNativePreview)
        """
        self._host_factory = host_factory
        self._preview_factory = preview_factory
        self._open_timeout = open_timeout
        self._host = None
        self._preview = None
        self._lock = threading.Lock()
        self._seq = 0
        self._loaded = False
        self._rect: Optional[Rect] = None

    @staticmethod
    def available() -> bool:
        """Visionneuses possibles : Windows et comtypes."""
        return IS_WINDOWS and COMTYPES_AVAILABLE

    def _ensure(self):
        if self._host is None:
            self._host = self._host_factory()
        if self._preview is None:
            self._preview = self._preview_factory()
        return self._host

    def show(self, path: str, rect: Rect) -> bool:
        """Charge le document, hôte posé mais masqué ; True si la visionneuse est prête.

        L'hôte n'apparaît qu'au place(..., visible=True) suivant : la page sait
        seule si un dialogue le couvrirait.
        """
        with self._lock:
            self._seq += 1
            seq = self._seq
            self._loaded = False
            self._rect = rect
            host = self._ensure()
            if host is None:
                return False
            host.place(rect, False)
            hwnd = host.handle()
        done = threading.Event()
        outcome = {"ok": False}

        def on_result(ok):
            outcome["ok"] = bool(ok)
            done.set()

        self._preview.open(path, hwnd, on_result)
        if not done.wait(self._open_timeout):
            logger.warning("Visionneuse trop lente pour %s : aperçu HTML", path)
            self.close()
            return False
        with self._lock:
            if seq != self._seq:
                return False  # remplacée ou fermée entre-temps
            self._loaded = outcome["ok"]
            if self._loaded:
                # L'hôte a pu bouger pendant le chargement : la visionneuse suit
                self._preview.resize()
            return self._loaded

    def place(self, rect: Rect, visible: bool) -> bool:
        """Recale l'hôte ; visible seulement si une visionneuse est chargée."""
        with self._lock:
            if self._host is None:
                return False
            moved = rect != self._rect
            self._rect = rect
            self._host.place(rect, visible and self._loaded)
            if moved and self._loaded:
                self._preview.resize()
            return self._loaded

    def close(self, wait: float = 0.0) -> None:
        """Masque l'hôte et décharge la visionneuse."""
        with self._lock:
            self._seq += 1
            self._loaded = False
            host, preview = self._host, self._preview
            if host is not None:
                try:
                    host.hide()
                except Exception as exc:  # pylint: disable=broad-except
                    logger.debug("Hôte non masqué : %s", exc)
        if preview is not None:
            preview.close(wait=wait)

    def shutdown(self) -> None:
        """Fermeture de l'appli (fenêtre déjà fermée) : Office déchargé, attente bornée."""
        with self._lock:
            self._seq += 1
            self._loaded = False
            preview = self._preview
        if preview is not None:
            preview.close(wait=SHUTDOWN_WAIT)
