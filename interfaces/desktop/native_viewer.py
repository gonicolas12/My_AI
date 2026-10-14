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

Word ne se ferme pas de lui-même après un aperçu : la visionneuse tourne dans
un Word caché (« WINWORD.EXE -Embedding »), qui rend l'aperçu suivant plus
rapide. Tant que l'appli tourne, il reste lancé ; à sa fermeture, l'appli ferme
le Word, l'Excel ou le PowerPoint caché qu'elle a lancé pour ses aperçus, et
lui seul (D30).
"""

import ctypes
import os
import threading
from ctypes import wintypes
from typing import Any, Callable, Dict, Iterable, List, Optional, Set, Tuple

import psutil

from interfaces.desktop.dpi_host import DpiAwareHost, client_origin, is_dpi_virtualized
from interfaces.desktop.preview_handler import (COMTYPES_AVAILABLE, IS_WINDOWS,
                                                 AsyncNativePreview)
from utils.logger import setup_logger

logger = setup_logger("NativeViewer")

# Démarrage à froid de Word, Excel ou PowerPoint : quelques secondes, rarement plus
OPEN_TIMEOUT = 45.0
# Fermeture de l'appli : ne pas laisser Office orphelin, sans bloquer trop longtemps
SHUTDOWN_WAIT = 2.0
OFFICE_EXIT_WAIT = 3.0
_MAX_SIDE = 32_000

# Programmes d'Office qui portent les visionneuses, et la classe de leur fenêtre principale
OFFICE_PROGRAMS = {"winword.exe": "OpusApp", "excel.exe": "XLMAIN",
                   "powerpnt.exe": "PPTFrameClass"}
_WM_CLOSE = 0x0010

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


# ── Office lancé pour les aperçus (D30) ─────────────────────────────────────

if IS_WINDOWS:
    _ENUM_PROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
else:  # pragma: no cover
    _ENUM_PROC = None


def _user32():
    """Instance privée de user32, signatures typées (handles 64 bits)."""
    user32 = ctypes.WinDLL("user32")
    user32.EnumChildWindows.argtypes = [wintypes.HWND, _ENUM_PROC, wintypes.LPARAM]
    user32.EnumWindows.argtypes = [_ENUM_PROC, wintypes.LPARAM]
    user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
    user32.GetWindowThreadProcessId.restype = wintypes.DWORD
    user32.IsWindowVisible.argtypes = [wintypes.HWND]
    user32.GetClassNameW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
    user32.PostMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM,
                                    wintypes.LPARAM]
    return user32


def _window_pid(user32, hwnd) -> int:
    pid = wintypes.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    return pid.value


def hosted_processes(hwnd: int) -> Set[int]:
    """Processus des fenêtres d'autres programmes posées dans l'hôte : la visionneuse."""
    if not IS_WINDOWS or not hwnd:
        return set()
    user32 = _user32()
    own = os.getpid()
    found: Set[int] = set()

    @_ENUM_PROC
    def collect(child, _param):
        pid = _window_pid(user32, child)
        if pid and pid != own:
            found.add(pid)
        return True

    user32.EnumChildWindows(hwnd, collect, 0)
    return found


def top_windows(pid: int) -> List[Tuple[int, bool, str]]:
    """Fenêtres de premier niveau d'un processus : (hwnd, visible, classe)."""
    if not IS_WINDOWS:
        return []
    user32 = _user32()
    windows: List[Tuple[int, bool, str]] = []

    @_ENUM_PROC
    def collect(hwnd, _param):
        if _window_pid(user32, hwnd) == pid:
            name = ctypes.create_unicode_buffer(64)
            user32.GetClassNameW(hwnd, name, 64)
            windows.append((hwnd, bool(user32.IsWindowVisible(hwnd)), name.value))
        return True

    user32.EnumWindows(collect, 0)
    return windows


def launched_office(pids: Iterable[int], since: float,
                    process: Callable[[int], Any] = psutil.Process,
                    windows: Callable[[int], List[Tuple[int, bool, str]]] = top_windows
                    ) -> List[Any]:
    """
    Office à fermer avec l'appli, parmi les processus des visionneuses : Word, Excel
    ou PowerPoint lancé par COM (« -Embedding »), après le lancement de l'appli
    (`since`, horodatage), sans fenêtre visible. Un Office ouvert par l'utilisateur,
    ou déjà là avant l'appli, n'en fait jamais partie.
    """
    selected = []
    for pid in sorted(set(pids)):
        try:
            proc = process(pid)
            if proc.name().lower() not in OFFICE_PROGRAMS or proc.create_time() < since:
                continue
            if not any("embedding" in part.lower() for part in proc.cmdline()):
                continue
        except psutil.Error:
            continue
        if any(visible for _hwnd, visible, _class in windows(pid)):
            continue  # un document ouvert à l'écran : celui de l'utilisateur
        selected.append(proc)
    return selected


def close_office(processes: List[Any], wait: float = OFFICE_EXIT_WAIT) -> List[int]:
    """Ferme ces Office cachés : WM_CLOSE à leur fenêtre principale, sinon arrêt. Rend leurs pid."""
    if not processes:
        return []
    user32 = _user32() if IS_WINDOWS else None
    for proc in processes:
        try:
            main = OFFICE_PROGRAMS.get(proc.name().lower())
        except psutil.Error:
            continue
        for hwnd, _visible, name in top_windows(proc.pid):
            if name == main and user32 is not None:
                user32.PostMessageW(hwnd, _WM_CLOSE, 0, 0)
    _gone, alive = psutil.wait_procs(processes, timeout=wait)
    for proc in alive:
        try:
            proc.terminate()
        except psutil.Error:
            pass
    psutil.wait_procs(alive, timeout=wait)
    logger.info("Office caché des aperçus fermé avec l'appli : %s",
                ", ".join(str(proc.pid) for proc in processes))
    return [proc.pid for proc in processes]


def _app_started() -> float:
    try:
        return psutil.Process().create_time()
    except psutil.Error:  # pragma: no cover
        return 0.0


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
        self._hwnd = 0
        # Processus qui ont porté une visionneuse, fermés avec l'appli s'il le faut (D30)
        self._hosts: Set[int] = set()
        self._since = _app_started()

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
            self._hwnd = hwnd
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
                self._hosts |= hosted_processes(hwnd)
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
            self._hosts |= hosted_processes(self._hwnd)
            if host is not None:
                try:
                    host.hide()
                except Exception as exc:  # pylint: disable=broad-except
                    logger.debug("Hôte non masqué : %s", exc)
        if preview is not None:
            preview.close(wait=wait)

    def shutdown(self) -> None:
        """
        Fermeture de l'appli (fenêtre déjà fermée) : visionneuse déchargée, attente
        bornée, puis Word, Excel ou PowerPoint caché lancé pour les aperçus fermé (D30).
        """
        with self._lock:
            self._seq += 1
            self._loaded = False
            preview = self._preview
            hosts = set(self._hosts)
        if preview is not None:
            preview.close(wait=SHUTDOWN_WAIT)
        try:
            close_office(launched_office(hosts, self._since))
        except Exception as exc:  # pylint: disable=broad-except
            logger.warning("Office caché des aperçus non fermé : %s", exc)
