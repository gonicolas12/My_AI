"""Aperçu natif des documents Office via les visionneuses de Windows.

Windows fournit, pour chaque type de document, une « visionneuse » COM
(``IPreviewHandler``) : c'est elle qu'utilise le volet d'aperçu de
l'Explorateur. Office en enregistre pour Word, PowerPoint et Excel. Les
héberger dans le volet d'aperçu affiche un .docx comme Word l'affiche, un
.pptx avec ses diapositives et un .xlsx avec sa grille et ses onglets — au
lieu d'une reconstitution HTML.

La visionneuse dessine dans une fenêtre qu'elle crée comme enfant de la
fenêtre qu'on lui confie. Comme pour Edge, cette fenêtre hôte doit être
« DPI par écran » (cf. interfaces/gui/_dpi_host.py), sans quoi le rendu serait
faussé sur un écran mis à l'échelle.

Windows uniquement, et dépend de comtypes (installé avec pyttsx3). Toute
erreur est silencieuse : l'appelant retombe alors sur l'aperçu HTML.
"""

from __future__ import annotations

import ctypes
import os
import sys
from ctypes import wintypes
from pathlib import Path
from typing import Optional

IS_WINDOWS = sys.platform.startswith("win")

# Identifiant de l'extension shell « visionneuse » dans le registre.
_PREVIEW_HANDLER_SHELLEX = "{8895b1c6-b41f-4c1c-a562-0d564250836f}"
# Formats confiés à une visionneuse native (le PDF reste au lecteur d'Edge).
NATIVE_EXTENSIONS = frozenset({".docx", ".doc", ".pptx", ".ppt", ".xlsx", ".xlsm", ".xls"})

_STGM_READ = 0x00000000
_STGM_SHARE_DENY_NONE = 0x00000040
_CLSCTX_INPROC_SERVER = 0x1
_CLSCTX_LOCAL_SERVER = 0x4
_DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2 = -4

try:
    if not IS_WINDOWS:
        raise ImportError("Windows uniquement")
    import comtypes
    from comtypes import COMMETHOD, GUID, HRESULT, IUnknown

    class IPreviewHandler(IUnknown):
        _iid_ = GUID(_PREVIEW_HANDLER_SHELLEX)
        _methods_ = [
            COMMETHOD([], HRESULT, "SetWindow",
                      (["in"], wintypes.HWND, "hwnd"),
                      (["in"], ctypes.POINTER(wintypes.RECT), "prc")),
            COMMETHOD([], HRESULT, "SetRect",
                      (["in"], ctypes.POINTER(wintypes.RECT), "prc")),
            COMMETHOD([], HRESULT, "DoPreview"),
            COMMETHOD([], HRESULT, "Unload"),
            COMMETHOD([], HRESULT, "SetFocus"),
            COMMETHOD([], HRESULT, "QueryFocus",
                      (["out"], ctypes.POINTER(wintypes.HWND), "phwnd")),
            COMMETHOD([], HRESULT, "TranslateAccelerator",
                      (["in"], ctypes.POINTER(wintypes.MSG), "pmsg")),
        ]

    class IInitializeWithFile(IUnknown):
        _iid_ = GUID("{b7d14566-0509-4cce-a71f-0a554233bd9b}")
        _methods_ = [
            COMMETHOD([], HRESULT, "Initialize",
                      (["in"], wintypes.LPCWSTR, "pszFilePath"),
                      (["in"], wintypes.DWORD, "grfMode")),
        ]

    class IInitializeWithStream(IUnknown):
        _iid_ = GUID("{b824b49d-22ac-4161-ac8a-9916e8fa3f7f}")
        _methods_ = [
            COMMETHOD([], HRESULT, "Initialize",
                      (["in"], ctypes.c_void_p, "pstream"),
                      (["in"], wintypes.DWORD, "grfMode")),
        ]

    COMTYPES_AVAILABLE = True
except Exception:  # noqa: BLE001 - comtypes absent ou plateforme non Windows
    COMTYPES_AVAILABLE = False


def handler_clsid(path: str) -> Optional[str]:
    """CLSID de la visionneuse enregistrée pour ce type de fichier, ou None."""
    if not IS_WINDOWS:
        return None
    import winreg

    extension = Path(path).suffix.lower()
    keys = [rf"{extension}\ShellEx\{_PREVIEW_HANDLER_SHELLEX}"]
    # La visionneuse peut aussi être déclarée sous le ProgID de l'extension.
    try:
        with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, extension) as key:
            prog_id = winreg.QueryValue(key, None)
        if prog_id:
            keys.append(rf"{prog_id}\ShellEx\{_PREVIEW_HANDLER_SHELLEX}")
    except OSError:
        pass
    for subkey in keys:
        try:
            with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, subkey) as key:
                value = winreg.QueryValue(key, None)
            if value:
                return value
        except OSError:
            continue
    return None


def supports_native_preview(path: str) -> bool:
    """True si le fichier peut être affiché par une visionneuse native."""
    return (
        COMTYPES_AVAILABLE
        and Path(path).suffix.lower() in NATIVE_EXTENSIONS
        and handler_clsid(path) is not None
    )


class NativePreview:
    """Héberge une visionneuse Windows dans une fenêtre donnée."""

    def __init__(self):
        self._handler = None
        self._stream = None  # flux ouvert si la visionneuse l'exige (à libérer)
        self._hwnd: Optional[int] = None

    @property
    def active(self) -> bool:
        return self._handler is not None

    def open(self, path: str, hwnd: int) -> bool:
        """
        Affiche le document dans la fenêtre ``hwnd`` (hôte DPI par écran).

        Returns:
            True si la visionneuse affiche le document ; False sinon (l'appelant
            retombe sur l'aperçu HTML).
        """
        self.close()
        clsid = handler_clsid(path) if COMTYPES_AVAILABLE else None
        if clsid is None or not hwnd or not os.path.exists(path):
            return False

        try:
            # Le thread Tk doit être un appartement COM monothread : les
            # visionneuses sont des objets STA et Tk fournit la pompe à messages.
            comtypes.CoInitialize()
            handler = self._create(clsid)
            if handler is None:
                return False
            if not self._initialize(handler, path):
                return False
            self._hwnd = hwnd
            rect = self._client_rect()
            handler.SetWindow(hwnd, ctypes.byref(rect))
            handler.DoPreview()
            self._handler = handler
            return True
        except Exception as exc:  # noqa: BLE001 - toute erreur COM → repli HTML
            print(f"⚠️ [APERÇU NATIF] Visionneuse indisponible pour {Path(path).name} : {exc}")
            self.close()
            return False

    def resize(self) -> None:
        """Adapte la visionneuse à la taille courante de la fenêtre hôte."""
        if self._handler is None:
            return
        try:
            rect = self._client_rect()
            self._handler.SetRect(ctypes.byref(rect))
        except Exception:  # noqa: BLE001
            pass

    def close(self) -> None:
        """Décharge la visionneuse et libère le document."""
        handler, self._handler = self._handler, None
        if handler is not None:
            try:
                handler.Unload()
            except Exception:  # noqa: BLE001
                pass
            del handler
        if self._stream is not None:
            _release(self._stream)
            self._stream = None
        self._hwnd = None

    # ── Détails COM ───────────────────────────────────────────────────────

    @staticmethod
    def _create(clsid: str):
        """Instancie la visionneuse, hors processus d'abord (comme l'Explorateur)."""
        for context in (_CLSCTX_LOCAL_SERVER, _CLSCTX_INPROC_SERVER):
            try:
                return comtypes.CoCreateInstance(
                    GUID(clsid), interface=IPreviewHandler, clsctx=context
                )
            except Exception:  # noqa: BLE001 - essayer le contexte suivant
                continue
        return None

    def _initialize(self, handler, path: str) -> bool:
        """Transmet le document à la visionneuse (chemin, sinon flux)."""
        try:
            handler.QueryInterface(IInitializeWithFile).Initialize(str(path), _STGM_READ)
            return True
        except Exception:  # noqa: BLE001 - visionneuse sans IInitializeWithFile
            pass
        try:
            stream = _open_stream(path)
            if not stream:
                return False
            handler.QueryInterface(IInitializeWithStream).Initialize(stream, _STGM_READ)
            self._stream = stream
            return True
        except Exception:  # noqa: BLE001
            return False

    def _client_rect(self):
        """Zone client de l'hôte, en pixels physiques (hôte DPI par écran)."""
        user32 = ctypes.WinDLL("user32")
        user32.SetThreadDpiAwarenessContext.argtypes = [ctypes.c_void_p]
        user32.SetThreadDpiAwarenessContext.restype = ctypes.c_void_p
        user32.GetClientRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
        rect = wintypes.RECT()
        previous = user32.SetThreadDpiAwarenessContext(
            ctypes.c_void_p(_DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2)
        )
        try:
            user32.GetClientRect(self._hwnd, ctypes.byref(rect))
        finally:
            if previous:
                user32.SetThreadDpiAwarenessContext(ctypes.c_void_p(previous))
        return rect


class AsyncNativePreview:
    """
    Pilote une visionneuse depuis un thread COM dédié, sans figer l'interface.

    Démarrer Word, Excel ou PowerPoint à froid prend plusieurs secondes : fait
    sur le thread Tk, ce démarrage gèlerait tout le chat au moment précis où
    l'aperçu s'ouvre. Toutes les commandes sont donc exécutées, dans l'ordre,
    par un thread « appartement monothread » propriétaire de la visionneuse.
    """

    def __init__(self):
        import queue

        self._queue: "queue.Queue" = queue.Queue()
        self._thread = None

    def open(self, path: str, hwnd: int, on_result) -> None:
        """
        Demande l'ouverture du document dans ``hwnd``.

        Args:
            on_result: Appelé avec True/False quand la visionneuse est prête ou
                a échoué — DEPUIS LE THREAD COM : l'appelant doit repasser sur
                le thread Tk (root.after) avant de toucher à l'interface.
        """
        self._submit("open", (path, hwnd, on_result))

    def resize(self) -> None:
        """Adapte la visionneuse à la taille courante de sa fenêtre hôte."""
        self._submit("resize", None)

    def close(self, wait: float = 0.0) -> None:
        """
        Décharge la visionneuse.

        Args:
            wait: Secondes d'attente maximale de la fermeture effective (à la
                sortie de l'appli, pour ne pas laisser Office orphelin).
        """
        if self._thread is None:
            return
        import threading

        done = threading.Event()
        self._submit("close", done)
        if wait:
            done.wait(wait)

    def _submit(self, command: str, payload) -> None:
        if self._thread is None:
            import threading

            self._thread = threading.Thread(
                target=self._run, name="apercu-natif", daemon=True
            )
            self._thread.start()
        self._queue.put((command, payload))

    def _run(self) -> None:
        comtypes.CoInitialize()
        preview = NativePreview()
        while True:
            command, payload = self._queue.get()
            try:
                if command == "open":
                    path, hwnd, on_result = payload
                    on_result(preview.open(path, hwnd))
                elif command == "resize":
                    preview.resize()
                elif command == "close":
                    preview.close()
                    payload.set()
            except Exception as exc:  # noqa: BLE001 - le thread ne doit jamais mourir
                print(f"⚠️ [APERÇU NATIF] {command} : {exc}")
                if command == "close":
                    payload.set()


def _open_stream(path: str) -> Optional[int]:
    """Ouvre un IStream en lecture seule (partagé) sur le fichier."""
    shlwapi = ctypes.WinDLL("shlwapi")
    shlwapi.SHCreateStreamOnFileEx.argtypes = [
        wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, wintypes.BOOL,
        ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p),
    ]
    stream = ctypes.c_void_p()
    result = shlwapi.SHCreateStreamOnFileEx(
        str(path), _STGM_READ | _STGM_SHARE_DENY_NONE, 0, False, None, ctypes.byref(stream)
    )
    return stream.value if result == 0 else None


def _release(pointer: int) -> None:
    """Libère un pointeur COM brut (IUnknown::Release, 3e entrée de la vtable)."""
    try:
        vtable = ctypes.cast(pointer, ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p))).contents
        release = ctypes.WINFUNCTYPE(ctypes.c_ulong, ctypes.c_void_p)(vtable[2])
        release(pointer)
    except Exception:  # noqa: BLE001
        pass
