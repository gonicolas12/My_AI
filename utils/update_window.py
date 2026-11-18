"""
Fenêtre d'attente des mises à jour faites avant l'appli, lancée sans console

Après un « git pull », launch_unified.py installe les dépendances ajoutées à
requirements.txt (utils/requirements_sync.py) avant les imports qui en ont
besoin, donc avant la fenêtre de l'appli. Avec une console, pip y écrit sa
progression. Lancé depuis son épingle de la barre des tâches (pythonw, cf.
utils/no_console.py), My_AI n'en a pas : cette petite fenêtre, aux couleurs de
l'écran de chargement, dit ce qui s'installe, avec la dernière ligne de pip,
jusqu'à la fin de l'installation.

Elle ne charge rien que pip pourrait avoir à remplacer : Tk (bibliothèque
standard), et la langue de l'appli lue dans config.yaml sans PyYAML. Sans
Tk, l'installation se fait sans fenêtre (sorties dans logs/).
"""

import ctypes
import queue
import re
import sys
import threading
from pathlib import Path
from typing import Any, Callable, List, Optional, TypeVar

from utils import no_console
from utils.requirements_sync import sync_requirements

T = TypeVar("T")
Report = Callable[[str], None]

IS_WINDOWS = sys.platform.startswith("win")
PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_FILE = PROJECT_ROOT / "config.yaml"
ICON = PROJECT_ROOT / "interfaces" / "desktop" / "assets" / "my_ai.ico"

# Couleurs de l'écran de chargement (frontend/src/styles/tokens.css)
BACKGROUND = "#0f0f0f"
TRACK = "#2d2d2d"
TEXT = "#ffffff"
TEXT_SECONDARY = "#9ca3af"
TEXT_MUTED = "#6b7280"
ACCENT = "#ff6b47"
FONT = "Segoe UI"

# Dernière ligne de pip affichée : assez pour un nom de paquet et sa taille
LINE_LIMIT = 90
POLL_MS = 100

# Barre de titre sombre (dwmapi.h), comme la fenêtre de l'appli (window.apply_title_bar)
_DWM_TITLE_BAR = ((20, 1), (35, 0x000F0F0F), (36, 0x00FFFFFF))  # mode sombre, fond, texte

# language.default de config.yaml (bloc « language: », clé « default: »)
_LANGUAGE_BLOCK = re.compile(r"^language:[ \t]*\r?\n((?:[ \t]+.*(?:\r?\n|$)|[ \t]*\r?\n)*)", re.M)
_DEFAULT_KEY = re.compile(r"^[ \t]+default:[ \t]*[\"']?([A-Za-z_-]+)", re.M)


def config_language(text: str) -> Optional[str]:
    """language.default d'un config.yaml, lu sans PyYAML (None s'il manque)."""
    block = _LANGUAGE_BLOCK.search(text)
    key = _DEFAULT_KEY.search(block.group(1)) if block else None
    return key.group(1) if key else None


def _use_app_language() -> None:
    """Langue de l'appli pour core.i18n, sans qu'il charge PyYAML.

    tr() lirait sinon config.yaml avec PyYAML, dont pip ne pourrait plus
    remplacer le module compilé, chargé (fichier verrouillé sous Windows).
    """
    from core import i18n  # pylint: disable=import-outside-toplevel

    try:
        code = i18n.normalize(config_language(CONFIG_FILE.read_text(encoding="utf-8")))
    except OSError:
        code = None
    i18n.set_language(code or i18n.SOURCE_LANGUAGE)


def last_line(text: str, limit: int = LINE_LIMIT) -> str:
    """Ligne de pip à afficher : sans blancs autour, coupée à limit caractères."""
    line = " ".join(text.split())
    return line if len(line) <= limit else line[:limit - 1] + "…"


def run_in_window(work: Callable[[Report], T], title: str, detail: str = "") -> T:
    """Fait tourner work(report) dans un fil, en montrant la fenêtre d'attente.

    Args:
        work: le travail (pip) ; report(ligne) affiche sa progression
        title: ce qui se fait (« Mise à jour des dépendances… »)
        detail: sous le titre (les paquets installés)

    Returns:
        Ce que renvoie work ; une exception de work est relancée ici
    """
    try:
        import tkinter  # pylint: disable=import-outside-toplevel
        from tkinter import ttk  # pylint: disable=import-outside-toplevel

        _per_monitor_dpi()
        root = tkinter.Tk()
    except Exception:  # pylint: disable=broad-except
        return work(lambda _line: None)  # pas de Tk, ou pas d'écran : sans fenêtre

    updates: "queue.Queue[str]" = queue.Queue()
    outcome: dict = {}

    def target() -> None:
        try:
            outcome["value"] = work(updates.put)
        except BaseException as exc:  # pylint: disable=broad-except
            outcome["error"] = exc  # relancée par le fil principal

    try:
        shown = _build(root, tkinter, ttk, title, detail)
    except Exception:  # pylint: disable=broad-except
        _destroy(root)
        return work(lambda _line: None)  # fenêtre impossible à construire : sans elle

    thread = threading.Thread(target=target, name="update-window", daemon=True)

    def poll() -> None:
        line = None
        while True:
            try:
                line = updates.get_nowait()
            except queue.Empty:
                break
        if line is not None:
            shown.set(f"{detail}\n{last_line(line)}" if detail else last_line(line))
        if thread.is_alive():
            root.after(POLL_MS, poll)
        else:
            root.quit()

    thread.start()
    root.after(POLL_MS, poll)
    try:
        root.mainloop()
    finally:
        _destroy(root)
        thread.join()  # même si Tk s'arrête : pip va jusqu'au bout
    if "error" in outcome:
        raise outcome["error"]
    return outcome["value"]


def _destroy(root: Any) -> None:
    try:
        root.destroy()
    except Exception:  # pylint: disable=broad-except
        pass


def _per_monitor_dpi() -> None:
    """DPI par écran, comme la fenêtre de l'appli ensuite : texte net, pas étiré.

    Le même régime que window.enable_per_monitor_dpi, qui le trouvera déjà fixé.
    """
    if IS_WINDOWS:
        try:
            # DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2
            ctypes.windll.user32.SetProcessDpiAwarenessContext(  # type: ignore[attr-defined]
                ctypes.c_void_p(-4)
            )
        except (AttributeError, OSError):
            pass


def _dark_title_bar(root: Any) -> None:
    if not IS_WINDOWS:
        return
    try:
        hwnd = ctypes.c_void_p(int(root.wm_frame(), 16))
        for attribute, value in _DWM_TITLE_BAR:
            data = ctypes.c_int(value)
            ctypes.windll.dwmapi.DwmSetWindowAttribute(  # type: ignore[attr-defined]
                hwnd, attribute, ctypes.byref(data), ctypes.sizeof(data)
            )
    except (AttributeError, OSError, ValueError):
        pass


def _build(root: Any, tkinter: Any, ttk: Any, title: str, detail: str) -> Any:
    """Fenêtre d'attente : My_AI, ce qui se fait, le détail, une barre qui défile."""
    root.withdraw()
    root.title(no_console.APP_NAME)
    root.configure(bg=BACKGROUND)
    root.resizable(False, False)
    # pip ne s'interrompt pas en route : la fenêtre se ferme à la fin
    root.protocol("WM_DELETE_WINDOW", lambda: None)
    if ICON.is_file():
        try:
            root.iconbitmap(default=str(ICON))
        except tkinter.TclError:
            pass
    # Les polices suivent l'échelle de l'écran (points) ; les marges, en pixels, aussi
    scale = float(root.tk.call("tk", "scaling")) * 72 / 96

    def px(value: int) -> int:
        return int(round(value * scale))

    tkinter.Label(root, text=no_console.APP_NAME, bg=BACKGROUND, fg=TEXT,
                  font=(FONT, 15, "bold")).pack(padx=px(32), pady=(px(24), px(2)))
    tkinter.Label(root, text=title, bg=BACKGROUND, fg=TEXT_SECONDARY,
                  font=(FONT, 10)).pack(padx=px(32))
    shown = tkinter.StringVar(root, value=detail)
    tkinter.Label(root, textvariable=shown, bg=BACKGROUND, fg=TEXT_MUTED, font=(FONT, 9),
                  width=60, height=2, justify="center").pack(padx=px(32), pady=(px(8), 0))

    style = ttk.Style(root)
    style.theme_use("clam")
    style.configure("MyAI.Horizontal.TProgressbar", background=ACCENT, troughcolor=TRACK,
                    bordercolor=TRACK, lightcolor=ACCENT, darkcolor=ACCENT,
                    thickness=px(6))
    bar = ttk.Progressbar(root, mode="indeterminate", length=px(380),
                          style="MyAI.Horizontal.TProgressbar")
    bar.pack(padx=px(32), pady=(px(14), px(26)))
    bar.start(12)

    root.update_idletasks()
    _dark_title_bar(root)
    width, height = root.winfo_reqwidth(), root.winfo_reqheight()
    left = max(0, (root.winfo_screenwidth() - width) // 2)
    top = max(0, (root.winfo_screenheight() - height) // 3)
    root.geometry(f"+{left}+{top}")
    root.deiconify()
    root.lift()
    return shown


def sync_dependencies() -> List[str]:
    """Dépendances de requirements.txt (sync_requirements), installées sous cette fenêtre.

    Une installation qui échoue s'affiche dans une boîte de dialogue : sans
    console, ses messages ne se verraient pas.

    Returns:
        Lignes toujours non satisfaites
    """
    attempted: List[str] = []

    def progress(install: Callable[[Report], T], lines: List[str]) -> T:
        from core.i18n import tr  # pylint: disable=import-outside-toplevel
        from interfaces.desktop import app_identity  # pylint: disable=import-outside-toplevel

        attempted.extend(lines)
        _use_app_language()
        # Fenêtre rangée avec l'épingle de My_AI, et non sous Python
        app_identity.set_windows_app_id()
        return run_in_window(install, tr("launch.dependencies"),
                             tr("launch.installing", packages=", ".join(lines)))

    failed = sync_requirements(progress=progress)
    if failed and attempted:
        from core.i18n import tr  # pylint: disable=import-outside-toplevel

        no_console.show_error(tr("launch.dependenciesFailed", packages=", ".join(failed)),
                              warning=True)
    return failed
