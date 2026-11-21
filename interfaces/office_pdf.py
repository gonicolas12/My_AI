"""
Document Office en PDF, pour le montrer tel qu'il est sans sa visionneuse

La fenêtre montre Word, Excel et PowerPoint dans leurs visionneuses, qu'Office
installe sous Windows. Sans elles (pas d'Office, macOS, Linux), et sur le
téléphone ou dans VS Code, le document passe par un PDF : Word, Excel ou
PowerPoint l'exportent (Windows, par COM, sans fenêtre), sinon LibreOffice s'il
est installé (toutes plateformes). La fenêtre ouvre ce PDF dans son lecteur ;
la page HTML (interfaces/document_preview.py) en montre les pages en images.
Une copie par version du fichier (utils/preview_cache.py). Sans Office ni
LibreOffice, None : l'aperçu garde son rendu HTML (texte, tableaux).

Office ouvre le fichier comme l'utilisateur le ferait, avec ses précautions :
  - aucune macro ne s'exécute (AutomationSecurity : désactivées, puis rendu tel
    quel) ; un mot de passe factice fait échouer un fichier protégé au lieu
    d'attendre sa saisie dans une fenêtre invisible ;
  - Word et Excel lancent une instance à eux pour l'export (« /Automation ») :
    une copie en lecture seule y est ouverte sans fenêtre, puis l'instance est
    quittée (Word ne part pas seul : sans Quit, il restait en mémoire). Dans
    Excel, chaque feuille tient en largeur sur une page à l'italienne, grille et
    en-têtes de lignes et de colonnes imprimés (la copie n'est jamais enregistrée) ;
  - Excel met en page pour « Microsoft Print to PDF », locale et toujours là, et
    non pour l'imprimante de Windows, qui peut être une imprimante réseau éteinte
    (Windows garde la sienne). Bloqué malgré tout, il est fermé passé le délai :
    l'instance de l'export, repérée par sa fenêtre, jamais un Excel de l'utilisateur ;
  - PowerPoint n'a qu'une instance, que la visionneuse de la fenêtre occupe
    peut-être déjà (« -Embedding », ses présentations refusent
    l'automatisation) et où l'utilisateur peut avoir ouvert le fichier : celui-là
    est exporté (ExportAsFixedFormat : ni fermé ni déplacé), sinon une copie en
    lecture seule, sans fenêtre, refermée ensuite. Il n'est jamais quitté :
    lancé pour l'export, il part seul quand plus rien ne le retient (Quit
    laissait la référence pointer sur un processus déjà parti).
"""

import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
from pathlib import Path
from typing import Callable, Optional

from utils import preview_cache
from utils.logger import setup_logger

logger = setup_logger("OfficePdf")

CACHE_DIR = preview_cache.ROOT / "office"
# Forme des copies : à changer avec elle, les anciennes ne resservent plus
_FORMAT = "1"
# Au-delà, l'export est abandonné (fichier protégé, dialogue d'Office…)
EXPORT_TIMEOUT = 90.0
# Instance d'Excel fermée faute de réponse : son appel en cours échoue aussitôt
_AFTER_CLOSE = 5.0
# Au-delà de cette taille, l'aperçu garde son rendu HTML (export trop long)
MAX_SIZE = 25 * 1024 * 1024
# Feuille d'Excel : ses premières lignes seulement (des milliers de pages sinon)
EXCEL_MAX_ROWS = 1000
_IS_WINDOWS = sys.platform.startswith("win")
# Application d'Office de chaque format
APPS = {
    ".docx": "word", ".doc": "word",
    ".xlsx": "excel", ".xlsm": "excel", ".xls": "excel",
    ".pptx": "powerpoint", ".potx": "powerpoint",
}
_PROGIDS = {"word": "Word.Application", "excel": "Excel.Application",
            "powerpoint": "PowerPoint.Application"}
_PROCESSES = {"word": "winword.exe", "excel": "excel.exe", "powerpoint": "powerpnt.exe"}
# Constantes d'Office (MsoTriState, MsoAutomationSecurity, formats d'export…)
_MSO_TRUE, _MSO_FALSE = -1, 0
_MACROS_OFF = 3  # msoAutomationSecurityForceDisable
_WORD_PDF, _WORD_NO_SAVE = 17, 0  # wdExportFormatPDF, wdDoNotSaveChanges
_EXCEL_PDF, _EXCEL_LANDSCAPE = 0, 2  # xlTypePDF, xlLandscape
_PPT_PDF, _PPT_SCREEN = 2, 1  # ppFixedFormatTypePDF, ppFixedFormatIntentScreen
# Mot de passe factice : un fichier protégé échoue au lieu d'attendre sa saisie
_NO_PASSWORD = "my_ai-apercu"
# Imprimante de la mise en page d'Excel : locale, installée avec Windows
_PDF_PRINTER = "Microsoft Print to PDF"
_PRINTERS_KEY = r"Software\Microsoft\Windows NT\CurrentVersion\Devices"
_SOFFICE_PATHS = (
    r"C:\Program Files\LibreOffice\program\soffice.exe",
    r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
    "/Applications/LibreOffice.app/Contents/MacOS/soffice",
)
# Un export à la fois : deux aperçus du même fichier attendent la même copie
_LOCK = threading.Lock()
# Versions de fichiers qui n'ont pas pu être exportées (protégées, illisibles) : pas
# de nouvel essai pendant ce lancement, la page HTML les montre tout de suite
_FAILED: set = set()


def office_kind(path: str) -> Optional[str]:
    """« word », « excel » ou « powerpoint » selon le format ; None sinon."""
    return APPS.get(Path(path).suffix.lower())


def office_pdf(path: str) -> Optional[str]:
    """PDF du document tel qu'Office (ou LibreOffice) l'imprime, ou None."""
    kind = office_kind(path)
    if kind is None:
        return None
    try:
        if os.path.getsize(path) > MAX_SIZE:
            return None
        target = preview_cache.copy_path(CACHE_DIR, path, ".pdf", _FORMAT)
    except OSError:
        return None
    with _LOCK:
        if target.is_file():
            return str(target)
        if target.name in _FAILED:
            return None
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        preview_cache.prune(CACHE_DIR)
        tried = False
        for export in (_with_office, _with_libreoffice):
            partial = preview_cache.partial_path(target)
            try:
                if export(kind, path, partial) and partial.is_file() and partial.stat().st_size:
                    os.replace(partial, target)
                    return str(target)
            except Exception as exc:  # pylint: disable=broad-except
                tried = True
                logger.warning("Export PDF de %s impossible (%s) : %s",
                               path, export.__name__, exc)
            finally:
                partial.unlink(missing_ok=True)
        if tried:
            _FAILED.add(target.name)
    return None


# ── Office (Windows) ───────────────────────────────────────────────────────


def office_installed(kind: str) -> bool:
    """L'application d'Office de ce genre est-elle installée (son automatisation) ?"""
    if not _IS_WINDOWS:
        return False
    import winreg  # pylint: disable=import-outside-toplevel

    try:
        winreg.CloseKey(winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, _PROGIDS[kind]))
        return True
    except OSError:
        return False


def office_running(kind: str) -> bool:
    """L'application tourne déjà (lancée par l'utilisateur, ou pour la visionneuse)."""
    import psutil  # pylint: disable=import-outside-toplevel

    wanted = _PROCESSES[kind]
    return any((process.info.get("name") or "").lower() == wanted
               for process in psutil.process_iter(["name"]))


def _opened(collection, source: str):
    """Document de l'utilisateur ouvert sur ce fichier, ou None (ceux de la
    visionneuse refusent l'automatisation : passés)."""
    wanted = os.path.normcase(source)
    for index in range(collection.Count, 0, -1):
        try:
            item = collection.Item(index)
            if os.path.normcase(item.FullName) == wanted:
                return item
        except Exception:  # pylint: disable=broad-except
            continue
    return None


def _macros_off(app) -> Optional[int]:
    """Macros désactivées pour ce que l'export ouvre ; renvoie le réglage d'avant."""
    try:
        previous = app.AutomationSecurity
        app.AutomationSecurity = _MACROS_OFF
        return previous
    except Exception:  # pylint: disable=broad-except
        return None


def _restore_macros(app, previous: Optional[int]) -> None:
    if previous is not None:
        try:
            app.AutomationSecurity = previous
        except Exception:  # pylint: disable=broad-except
            pass


def _quit(app, name: str) -> None:
    """Quitte l'instance lancée pour l'export (Word et Excel en ont une à eux)."""
    try:
        app.Quit()
    except Exception as exc:  # pylint: disable=broad-except
        logger.debug("%s laissé ouvert : %s", name, exc)


def _export_word(client, source: str, target: str) -> bool:
    # Word lance une instance à lui à chaque CreateObject : jamais celle de l'utilisateur
    app = client.CreateObject("Word.Application")
    try:
        app.DisplayAlerts = 0  # wdAlertsNone : aucun dialogue
        _macros_off(app)
        document = app.Documents.Open(
            FileName=source, ConfirmConversions=False, ReadOnly=True,
            AddToRecentFiles=False, PasswordDocument=_NO_PASSWORD, Visible=False)
        try:
            document.ExportAsFixedFormat(target, _WORD_PDF)
        finally:
            document.Close(_WORD_NO_SAVE)
        return True
    finally:
        _quit(app, "Word")


def _printer_port(name: str) -> Optional[str]:
    """Port d'une imprimante tel qu'Office le nomme (« Ne00: »), None si elle manque."""
    if not _IS_WINDOWS:
        return None
    import winreg  # pylint: disable=import-outside-toplevel

    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _PRINTERS_KEY) as key:
            value = winreg.QueryValueEx(key, name)[0]  # « winspool,Ne00: »
    except OSError:
        return None
    found = re.search(r"\bNe\d+:", str(value))
    return found.group(0) if found else None


def _print_to_pdf(app) -> None:
    """Excel met en page pour « Microsoft Print to PDF », et non pour l'imprimante de Windows.

    Réseau et éteinte, celle-ci faisait attendre chaque réglage de la mise en page
    (20 s), puis l'export ouvrait « Choix de l'imprimante », où personne ne répond.
    Seule cette instance d'Excel en change : Windows garde la sienne. Excel refuse
    tant qu'aucun classeur n'est ouvert, et ne prend que le nom complet
    (« … sur Ne00: », le mot dans la langue d'Office, le port du registre).
    """
    port = _printer_port(_PDF_PRINTER)
    if port is None:
        return
    try:
        # « HP… sur Ne01: » : le mot entre le nom et le port est celui d'Office
        found = re.search(r" (\S+) Ne\d+:$", app.ActivePrinter or "")
        word = found.group(1) if found else "on"
        app.ActivePrinter = f"{_PDF_PRINTER} {word} {port}"
    except Exception as exc:  # pylint: disable=broad-except
        logger.debug("Excel garde l'imprimante de Windows : %s", exc)


def _fit_sheets(app, workbook) -> None:
    """Chaque feuille en largeur sur une page à l'italienne, grille et en-têtes compris."""
    try:
        app.PrintCommunication = False  # réglages groupés : sinon une seconde chacun
    except Exception:  # pylint: disable=broad-except
        pass
    try:
        for index in range(1, workbook.Worksheets.Count + 1):
            sheet = workbook.Worksheets.Item(index)
            try:
                used = sheet.UsedRange
                if used.Rows.Count > EXCEL_MAX_ROWS:
                    last = used.Cells(EXCEL_MAX_ROWS, used.Columns.Count)
                    # Propriété à paramètres : comtypes la rend à appeler (« $A$1:$D$1000 »)
                    address = sheet.Range(used.Cells(1, 1), last).Address
                    sheet.PageSetup.PrintArea = address() if callable(address) else address
            except Exception as exc:  # pylint: disable=broad-except
                logger.debug("Feuille %d imprimée en entier : %s", index, exc)
            try:
                setup = sheet.PageSetup
                setup.Orientation = _EXCEL_LANDSCAPE
                setup.Zoom = False
                setup.FitToPagesWide = 1
                setup.FitToPagesTall = False
                setup.PrintGridlines = True
                setup.PrintHeadings = True
            except Exception as exc:  # pylint: disable=broad-except
                logger.debug("Mise en page de la feuille %d laissée : %s", index, exc)
    finally:
        try:
            app.PrintCommunication = True
        except Exception:  # pylint: disable=broad-except
            pass


def _export_excel(client, source: str, target: str) -> bool:
    # Excel a plusieurs instances : celle-ci n'est qu'à l'export
    app = client.CreateObject("Excel.Application")
    try:
        app.Visible = False
        app.DisplayAlerts = False
        app.ScreenUpdating = False
        app.EnableEvents = False
        _macros_off(app)
        workbook = app.Workbooks.Open(source, 0, True, None, _NO_PASSWORD)
        try:
            _print_to_pdf(app)
            _fit_sheets(app, workbook)
            workbook.ExportAsFixedFormat(_EXCEL_PDF, target)
        finally:
            workbook.Close(False)
        return True
    finally:
        _quit(app, "Excel")


def _export_powerpoint(client, source: str, target: str) -> bool:
    # Une seule instance, peut-être celle de l'utilisateur ou de la visionneuse : jamais
    # quittée ; lancée pour l'export, elle part seule quand plus rien ne la retient
    app = client.CreateObject("PowerPoint.Application")
    mine = _opened(app.Presentations, source)
    if mine is not None:
        mine.ExportAsFixedFormat(target, _PPT_PDF, _PPT_SCREEN)
        return True
    previous = _macros_off(app)
    try:
        presentation = app.Presentations.Open(source, _MSO_TRUE, _MSO_FALSE, _MSO_FALSE)
    finally:
        _restore_macros(app, previous)
    try:
        presentation.ExportAsFixedFormat(target, _PPT_PDF, _PPT_SCREEN)
    finally:
        presentation.Close()
    return True


_EXPORTERS: dict = {"word": _export_word, "excel": _export_excel,
                    "powerpoint": _export_powerpoint}


def _excel_process(app):
    """Processus d'une instance d'Excel, par sa fenêtre (cachée) ; None s'il échappe."""
    try:
        import ctypes  # pylint: disable=import-outside-toplevel
        from ctypes import wintypes  # pylint: disable=import-outside-toplevel

        import psutil  # pylint: disable=import-outside-toplevel

        pid = wintypes.DWORD()
        ctypes.windll.user32.GetWindowThreadProcessId(wintypes.HWND(app.Hwnd), ctypes.byref(pid))
        process = psutil.Process(pid.value)
        if process.name().lower() == _PROCESSES["excel"]:
            return process
    except Exception as exc:  # pylint: disable=broad-except
        logger.debug("Instance d'Excel de l'export non repérée : %s", exc)
    return None


class _ExportClient:  # pylint: disable=too-few-public-methods
    """Client COM de l'export : note le processus de l'instance d'Excel qu'il lance.

    Bloquée, elle ne rend jamais la main : passé le délai, elle est fermée, elle seule
    (ni un Excel de l'utilisateur, ni PowerPoint, dont l'instance est peut-être la sienne).
    """

    def __init__(self, client):
        self._client = client
        self.process = None

    def CreateObject(self, progid: str):  # pylint: disable=invalid-name
        """L'application d'Office ; d'Excel, le processus de son instance est noté."""
        app = self._client.CreateObject(progid)
        if progid == _PROGIDS["excel"]:
            self.process = _excel_process(app)
        return app


def _close(process) -> bool:
    """Ferme l'instance lancée pour l'export ; vrai si elle est partie."""
    if process is None:
        return False
    try:
        # psutil vérifie d'abord que son numéro n'a pas été repris par un autre processus
        process.kill()
        process.wait(_AFTER_CLOSE)
    except Exception as exc:  # pylint: disable=broad-except
        logger.debug("Instance de l'export non fermée : %s", exc)
        return False
    return True


def _with_office(kind: str, path: str, target: Path) -> bool:
    if not office_installed(kind):
        return False
    try:
        import comtypes  # pylint: disable=import-outside-toplevel
        import comtypes.client  # pylint: disable=import-outside-toplevel
    except ImportError:
        return False
    export: Callable = _EXPORTERS[kind]
    # Office n'accepte que les chemins Windows complets (« \ »)
    source = os.path.normpath(os.path.abspath(path))
    client = _ExportClient(comtypes.client)
    outcome = {}

    def run():
        comtypes.CoInitialize()
        try:
            outcome["ok"] = export(client, source, os.path.normpath(str(target)))
        except Exception as exc:  # pylint: disable=broad-except
            outcome["error"] = exc
        finally:
            comtypes.CoUninitialize()

    worker = threading.Thread(target=run, name=f"export-{kind}", daemon=True)
    worker.start()
    worker.join(EXPORT_TIMEOUT)
    if worker.is_alive():
        message = f"{kind} n'a pas exporté {path} en {EXPORT_TIMEOUT:.0f} s"
        # Bloquée (un dialogue que personne ne voit…), l'instance de l'export restait
        # ouverte : fermée, son appel en cours échoue et le fil s'achève
        if _close(client.process):
            worker.join(_AFTER_CLOSE)
            message += " : son instance a été fermée"
        # Noté en échec : pas un nouvel essai aussi long à chaque aperçu
        raise TimeoutError(message)
    if "error" in outcome:
        raise outcome["error"]
    return bool(outcome.get("ok"))


# ── LibreOffice ────────────────────────────────────────────────────────────


def _soffice() -> Optional[str]:
    found = shutil.which("soffice") or shutil.which("libreoffice")
    if found:
        return found
    return next((path for path in _SOFFICE_PATHS if os.path.isfile(path)), None)


def _with_libreoffice(kind: str, path: str, target: Path) -> bool:
    del kind  # LibreOffice lit les trois formats
    soffice = _soffice()
    if not soffice:
        return False
    with tempfile.TemporaryDirectory(prefix="my_ai_soffice_") as folder:
        # Profil à part : un LibreOffice déjà ouvert ne prend pas la conversion pour lui
        profile = Path(folder) / "profil"
        subprocess.run(
            [soffice, f"-env:UserInstallation={profile.as_uri()}", "--headless", "--norestore",
             "--convert-to", "pdf", "--outdir", folder, os.path.abspath(path)],
            capture_output=True, timeout=EXPORT_TIMEOUT, check=False,
        )
        produced = Path(folder) / f"{Path(path).stem}.pdf"
        if not produced.is_file():
            return False
        shutil.move(str(produced), str(target))
    return True
