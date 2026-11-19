"""
Documents Office montrés tels qu'ils sont, sans leur visionneuse.

La fenêtre montre Word, Excel et PowerPoint dans les visionneuses qu'Office
installe sous Windows. Sans elles (pas d'Office, macOS, Linux), et sur le
téléphone ou dans VS Code, le document passe par un PDF que Word, Excel ou
PowerPoint exportent (Windows, COM, sans fenêtre), sinon LibreOffice
(interfaces/office_pdf.py) : la fenêtre l'ouvre dans son lecteur PDF, la page
HTML en montre les pages en images. Sans l'un ni l'autre, le rendu HTML reste.

Office ouvre le fichier sans macros ni dialogue ; une instance de Word ou de
PowerPoint déjà lancée (par l'utilisateur, ou pour la visionneuse) n'est jamais
quittée, un document qu'il a ouvert jamais fermé.
"""

import os
import subprocess
import time

import pytest

from generators.document_generator import DocumentGenerator
from generators.markdown_document import parse_markdown
from interfaces import document_preview, office_pdf
from interfaces.document_preview import build_document_preview
from relay import file_preview

MARKDOWN = "## Chiffres\n\n- Ventes : +12 %\n\n| A | B |\n|---|---|\n| 1 | 2 |\n\n## Suite\n\nMerci."


@pytest.fixture(name="docs")
def docs_fixture(tmp_path):
    """Un document par application : Word, Excel, PowerPoint."""
    generator = DocumentGenerator(llm=False)
    paths = {}
    for fmt in ("docx", "xlsx", "pptx"):
        path = tmp_path / f"bilan.{fmt}"
        generator.build(parse_markdown(MARKDOWN), fmt, "Bilan", path)
        paths[fmt] = str(path)
    return paths


@pytest.fixture(name="cache")
def cache_fixture(tmp_path, monkeypatch):
    folder = tmp_path / "copies"
    monkeypatch.setattr(office_pdf, "CACHE_DIR", folder)
    monkeypatch.setattr(office_pdf, "_FAILED", set())
    return folder


def _pdf(path, pages=2, landscape=True):
    pymupdf = pytest.importorskip("pymupdf")
    document = pymupdf.open()
    for number in range(pages):
        size = (720, 405) if landscape else (595, 842)
        document.new_page(width=size[0], height=size[1]).insert_text((72, 90), f"Page {number + 1}")
    document.save(str(path))
    document.close()
    return str(path)


# ── Page HTML (téléphone, VS Code) : les pages en images, sinon le texte ───


def test_word_and_excel_show_their_printed_pages(docs, tmp_path, monkeypatch):
    pdf = _pdf(tmp_path / "pages.pdf", landscape=False)
    monkeypatch.setattr(office_pdf, "office_pdf", lambda path: pdf)
    word = build_document_preview(docs["docx"])
    assert word.count('class="office-page"') == 2
    # Excel : chaque page réduite à ce qui y est imprimé
    excel = build_document_preview(docs["xlsx"])
    assert excel.count('class="office-page cropped"') == 2
    for html in (word, excel):
        assert 'alt="Page 1 sur 2"' in html and "<table" not in html.split("</style>")[1]
        # Toucher une page l'agrandit : une case à cocher et son étiquette, sans script
        assert html.count('<input class="zoom-toggle" type="checkbox" id="zoom-office-page-') == 2
        assert '<label class="zoom" for="zoom-office-page-1"><img' in html


def test_an_excel_page_is_cut_down_to_its_table(tmp_path):
    pymupdf = pytest.importorskip("pymupdf")
    path = tmp_path / "feuille.pdf"
    document = pymupdf.open()
    page = document.new_page(width=842, height=595)  # A4 à l'italienne
    page.draw_rect(pymupdf.Rect(40, 60, 240, 140))  # le tableau, dans un coin
    page.insert_text((50, 100), "Total 4500")
    document.save(str(path))
    document.close()
    with pymupdf.open(str(path)) as opened:
        # pylint: disable-next=protected-access
        area = document_preview._content_rect(opened[0], pymupdf)
    assert (round(area.x0), round(area.y0), round(area.x1), round(area.y1)) == (32, 52, 248, 148)
    html = document_preview._pdf_page_images(  # pylint: disable=protected-access
        str(path), 12, "office-page", crop=True)
    assert 'class="office-page cropped"' in html


def test_slides_are_shown_as_images_of_their_pdf(docs, tmp_path, monkeypatch):
    pdf = _pdf(tmp_path / "diapos.pdf")
    monkeypatch.setattr(office_pdf, "office_pdf", lambda path: pdf)
    html = build_document_preview(docs["pptx"])
    assert html.count('class="slide-page"') == 2 and 'class="slide"' not in html
    assert 'alt="Diapositive 1 sur 2"' in html and "data:image/jpeg;base64," in html


def test_long_documents_show_their_first_pages(docs, tmp_path, monkeypatch):
    pdf = _pdf(tmp_path / "long.pdf", pages=3)
    monkeypatch.setattr(office_pdf, "office_pdf", lambda path: pdf)
    monkeypatch.setattr(document_preview, "_SLIDES_MAX", 2)
    monkeypatch.setattr(document_preview, "_PDF_PAGES_MAX", 2)
    assert "Les 2 premières diapositives sur 3" in build_document_preview(docs["pptx"])
    word = build_document_preview(docs["docx"])
    assert word.count('class="office-page"') == 2
    assert "Les 2 premières pages sur 3 : téléchargez le document" in word


def test_without_office_nor_libreoffice_the_html_rendering_stays(docs, monkeypatch):
    monkeypatch.setattr(office_pdf, "office_pdf", lambda path: None)
    assert "Ventes : +12 %" in build_document_preview(docs["docx"])
    assert "<table" in build_document_preview(docs["xlsx"])
    slides = build_document_preview(docs["pptx"])
    assert 'class="slide"' in slides and "Ventes : +12 %" in slides


def test_a_csv_stays_a_table(tmp_path, monkeypatch):
    asked = []
    monkeypatch.setattr(office_pdf, "office_pdf", lambda path: asked.append(path))
    table = tmp_path / "data.csv"
    table.write_bytes(b"a;b\n1;2\n")
    assert '<td class="num">1</td>' in build_document_preview(str(table)) and not asked


def test_the_phone_and_vs_code_get_the_pages(docs, tmp_path, monkeypatch):
    pdf = _pdf(tmp_path / "pages.pdf")
    monkeypatch.setattr(office_pdf, "office_pdf", lambda path: pdf)
    assert file_preview.build_preview(docs["docx"])["html"].count('class="office-page"') == 2
    assert file_preview.build_preview(docs["pptx"])["html"].count('class="slide-page"') == 2


# ── Copie PDF : une par version, Office puis LibreOffice ───────────────────


def test_the_pdf_is_made_once_per_version(docs, cache, monkeypatch):
    calls = []

    def fake_office(kind, path, target):
        calls.append(kind)
        target.write_bytes(b"%PDF-1.4 office")
        return True

    monkeypatch.setattr(office_pdf, "_with_office", fake_office)
    first = office_pdf.office_pdf(docs["docx"])
    assert first and os.path.dirname(first) == str(cache) and first.endswith(".pdf")
    assert office_pdf.office_pdf(docs["docx"]) == first and calls == ["word"]
    assert office_pdf.office_pdf(docs["xlsx"]) != first and calls == ["word", "excel"]
    # Aucun reste d'écriture
    assert sorted(entry.suffix for entry in cache.iterdir()) == [".pdf", ".pdf"]


def test_libreoffice_takes_over_when_office_fails(docs, cache, monkeypatch):
    def broken(kind, path, target):
        raise OSError("Word indisponible")

    def libreoffice(kind, path, target):
        target.write_bytes(b"%PDF-1.4 libreoffice")
        return True

    monkeypatch.setattr(office_pdf, "_with_office", broken)
    monkeypatch.setattr(office_pdf, "_with_libreoffice", libreoffice)
    made = office_pdf.office_pdf(docs["docx"])
    assert made and open(made, "rb").read() == b"%PDF-1.4 libreoffice"


def test_a_file_that_fails_is_not_exported_again(docs, cache, monkeypatch):
    calls = []

    def broken(kind, path, target):
        calls.append(path)
        raise TimeoutError("Word n'a pas répondu")

    monkeypatch.setattr(office_pdf, "_with_office", broken)
    monkeypatch.setattr(office_pdf, "_with_libreoffice", lambda kind, path, target: False)
    assert office_pdf.office_pdf(docs["docx"]) is None
    assert office_pdf.office_pdf(docs["docx"]) is None and len(calls) == 1


def test_what_is_not_exported(docs, cache, tmp_path, monkeypatch):
    monkeypatch.setattr(office_pdf, "_with_office", lambda kind, path, target: False)
    monkeypatch.setattr(office_pdf, "_with_libreoffice", lambda kind, path, target: False)
    assert office_pdf.office_pdf(docs["docx"]) is None  # ni Office ni LibreOffice
    text = tmp_path / "note.txt"
    text.write_text("x", encoding="utf-8")
    assert office_pdf.office_pdf(str(text)) is None  # pas un document Office
    assert office_pdf.office_pdf(str(tmp_path / "absent.docx")) is None
    monkeypatch.setattr(office_pdf, "MAX_SIZE", 10)
    assert office_pdf.office_pdf(docs["xlsx"]) is None  # trop gros : le rendu HTML
    assert not list(cache.iterdir())


def test_libreoffice_converts_with_a_profile_of_its_own(docs, tmp_path, monkeypatch):
    seen = []

    def fake_run(command, **kwargs):
        seen.append(command)
        folder = command[command.index("--outdir") + 1]
        with open(os.path.join(folder, "bilan.pdf"), "wb") as handle:
            handle.write(b"%PDF-1.4")
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(office_pdf, "_soffice", lambda: "soffice")
    monkeypatch.setattr(office_pdf.subprocess, "run", fake_run)
    target = tmp_path / "sortie.pdf"
    # pylint: disable-next=protected-access
    assert office_pdf._with_libreoffice("word", docs["docx"], target) is True
    assert target.read_bytes() == b"%PDF-1.4"
    command = seen[0]
    assert command[:1] == ["soffice"] and "--headless" in command
    assert command[command.index("--convert-to") + 1] == "pdf"
    assert any(part.startswith("-env:UserInstallation=file:") for part in command)


# ── Office simulé : macros coupées, rien de l'utilisateur fermé ────────────


class FakeDocument:
    """Document de Word, classeur d'Excel ou présentation de PowerPoint."""

    def __init__(self, name, log, locked=False):
        self._name, self.log, self.locked = name, log, locked

    @property
    def FullName(self):  # pylint: disable=invalid-name
        if self.locked:  # celui de la visionneuse de la fenêtre
            raise OSError("Automation rights are not granted")
        return self._name

    def ExportAsFixedFormat(self, *args):  # pylint: disable=invalid-name
        self.log.append(("export", self._name) + args[1:] if isinstance(args[0], str)
                        else ("export", self._name, args[0]))
        target = args[0] if isinstance(args[0], str) else args[1]
        with open(target, "wb") as handle:
            handle.write(b"%PDF")

    def Close(self, *args):  # pylint: disable=invalid-name
        self.log.append(("close", self._name) + args)
        self.app.opened.remove(self)


class FakeCollection:
    def __init__(self, app):
        self.app = app

    @property
    def Count(self):  # pylint: disable=invalid-name
        return len(self.app.opened)

    def Item(self, index):  # pylint: disable=invalid-name
        return self.app.opened[index - 1]

    def Open(self, *args, **kwargs):  # pylint: disable=invalid-name
        self.app.log.append(("open", args, kwargs, self.app.AutomationSecurity))
        name = kwargs.get("FileName") or args[0]
        document = FakeDocument(name, self.app.log)
        document.app = self.app
        self.app.opened.append(document)
        return document


class FakeApp:
    def __init__(self, opened=(), visible=0):
        self.log = []
        self.opened = []
        for item in opened:
            item.app = self
            self.opened.append(item)
        self.Visible = visible  # pylint: disable=invalid-name
        self.DisplayAlerts = 1  # pylint: disable=invalid-name
        self.AutomationSecurity = 1  # pylint: disable=invalid-name
        self.Documents = self.Presentations = FakeCollection(self)  # pylint: disable=invalid-name

    def Quit(self, *args):  # pylint: disable=invalid-name
        self.log.append(("quit",))


class FakeClient:
    def __init__(self, app, progid):
        self.app, self.progid = app, progid

    def CreateObject(self, name):  # pylint: disable=invalid-name
        assert name == self.progid
        return self.app


SOURCE = r"C:\docs\bilan.docx"


def _run(export, app, progid, running, monkeypatch, tmp_path, source=SOURCE):
    monkeypatch.setattr(office_pdf, "office_running", lambda kind: running)
    assert export(FakeClient(app, progid), source, str(tmp_path / "sortie.pdf")) is True
    return app.log


def test_word_exports_from_an_instance_of_its_own_then_quits_it(monkeypatch, tmp_path):
    # Word lance une instance à lui à chaque CreateObject : quittée même si un autre tourne
    for running in (False, True):
        app = FakeApp()
        # pylint: disable-next=protected-access
        log = _run(office_pdf._export_word, app, "Word.Application", running, monkeypatch,
                   tmp_path)
        opened = log[0]
        assert opened[0] == "open" and opened[2]["ReadOnly"] is True
        assert opened[2]["Visible"] is False and opened[2]["AddToRecentFiles"] is False
        assert opened[2]["PasswordDocument"]  # factice : un fichier protégé échoue
        assert opened[3] == 3 and app.DisplayAlerts == 0  # sans macros ni dialogue
        assert ("export", SOURCE, 17) in log
        assert log[-2:] == [("close", SOURCE, 0), ("quit",)]


PPT = r"C:\docs\bilan.pptx"


def test_powerpoint_is_never_quit(monkeypatch, tmp_path):
    # Lancé pour l'export, il part seul quand plus rien ne le retient
    app = FakeApp()
    # pylint: disable-next=protected-access
    log = _run(office_pdf._export_powerpoint, app, "PowerPoint.Application", False,
               monkeypatch, tmp_path, source=PPT)
    assert log[0][:2] == ("open", (PPT, -1, 0, 0)) and log[0][3] == 3
    assert app.AutomationSecurity == 1  # son réglage rendu
    assert ("export", PPT, 2, 1) in log and log[-1] == ("close", PPT)
    assert ("quit",) not in log


def test_a_running_powerpoint_keeps_the_viewers_presentation(monkeypatch, tmp_path):
    viewer = FakeDocument(PPT, [], locked=True)
    app = FakeApp(opened=[viewer])
    # pylint: disable-next=protected-access
    log = _run(office_pdf._export_powerpoint, app, "PowerPoint.Application", True,
               monkeypatch, tmp_path, source=PPT)
    assert ("close", PPT) in log and ("quit",) not in log
    assert app.opened == [viewer]


def test_the_users_open_presentation_is_exported_never_closed(monkeypatch, tmp_path):
    mine = FakeDocument(PPT, [])
    app = FakeApp(opened=[mine], visible=-1)
    mine.log = app.log
    # pylint: disable-next=protected-access
    log = _run(office_pdf._export_powerpoint, app, "PowerPoint.Application", True,
               monkeypatch, tmp_path, source=PPT)
    assert log == [("export", PPT, 2, 1)] and app.opened == [mine]


class FakeSetup:  # pylint: disable=too-few-public-methods
    """PageSetup : les réglages faits s'y lisent."""


class FakeRange:
    def __init__(self, rows, columns, address="$A$1:$D$1000"):
        self.Rows = type("Rows", (), {"Count": rows})()  # pylint: disable=invalid-name
        self.Columns = type("Columns", (), {"Count": columns})()  # pylint: disable=invalid-name
        self.Address = address  # pylint: disable=invalid-name

    def Cells(self, row, column):  # pylint: disable=invalid-name
        return (row, column)


class FakeSheet:
    def __init__(self, rows):
        self.UsedRange = FakeRange(rows, 4)  # pylint: disable=invalid-name
        self.PageSetup = FakeSetup()  # pylint: disable=invalid-name

    def Range(self, first, last):  # pylint: disable=invalid-name
        return FakeRange(0, 0, f"{first}:{last}")


class FakeWorkbook:
    def __init__(self, log, sheets):
        self.log = log
        sheets_list = list(sheets)
        self.Worksheets = type("Sheets", (), {  # pylint: disable=invalid-name
            "Count": len(sheets_list), "Item": lambda _self, index: sheets_list[index - 1]})()
        self.sheets = sheets_list

    def ExportAsFixedFormat(self, kind, target):  # pylint: disable=invalid-name
        self.log.append(("export", kind))
        with open(target, "wb") as handle:
            handle.write(b"%PDF")

    def Close(self, save):  # pylint: disable=invalid-name
        self.log.append(("close", save))


class FakeExcel:
    def __init__(self, sheets):
        self.log = []
        self.AutomationSecurity = 1  # pylint: disable=invalid-name
        self.PrintCommunication = True  # pylint: disable=invalid-name
        self.workbook = FakeWorkbook(self.log, sheets)
        excel = self

        class Workbooks:  # pylint: disable=too-few-public-methods
            @staticmethod
            def Open(*args):  # pylint: disable=invalid-name
                excel.log.append(("open", args, excel.AutomationSecurity, excel.DisplayAlerts))
                return excel.workbook

        self.Workbooks = Workbooks()  # pylint: disable=invalid-name

    def Quit(self):  # pylint: disable=invalid-name
        self.log.append(("quit",))


def test_excel_prints_each_sheet_one_page_wide_with_its_grid(monkeypatch, tmp_path):
    short, long_ = FakeSheet(rows=20), FakeSheet(rows=5000)
    app = FakeExcel([short, long_])
    # pylint: disable-next=protected-access
    log = _run(office_pdf._export_excel, app, "Excel.Application", True, monkeypatch, tmp_path,
               source=r"C:\docs\bilan.xlsx")
    opened = log[0]
    assert opened[1][:3] == (r"C:\docs\bilan.xlsx", 0, True)  # lecture seule, liens non mis à jour
    assert opened[2] == 3 and opened[3] is False  # sans macros ni dialogue
    for sheet in (short, long_):
        setup = sheet.PageSetup
        assert (setup.Orientation, setup.Zoom, setup.FitToPagesWide, setup.FitToPagesTall) == (
            2, False, 1, False)
        assert setup.PrintGridlines is True and setup.PrintHeadings is True
    # Des milliers de lignes : les premières seulement
    assert not hasattr(short.PageSetup, "PrintArea")
    assert long_.PageSetup.PrintArea == f"(1, 1):({office_pdf.EXCEL_MAX_ROWS}, 4)"
    assert app.PrintCommunication is True
    # Instance à part : toujours quittée, même si Excel tournait déjà
    assert log[-3:] == [("export", 0), ("close", False), ("quit",)]


# ── Fenêtre : le lecteur PDF quand la visionneuse manque ───────────────────


def test_the_window_opens_the_pdf_when_there_is_no_viewer(docs, tmp_path, monkeypatch):
    # pylint: disable=import-outside-toplevel
    from interfaces.desktop import preview_handler, previews

    store = previews.PreviewStore(directory=tmp_path / "artefacts")
    copy = _pdf(tmp_path / "copie.pdf")
    monkeypatch.setattr(previews, "_IS_WINDOWS", True)
    monkeypatch.setattr(office_pdf, "office_pdf", lambda path: copy)
    # Office installé : sa visionneuse d'abord
    monkeypatch.setattr(preview_handler, "supports_native_preview", lambda path: True)
    assert store.add_document(docs["docx"], native=True).kind == "native"
    # Sans elle (pas d'Office, ou elle a échoué) : le PDF exporté, dans le lecteur
    monkeypatch.setattr(preview_handler, "supports_native_preview", lambda path: False)
    for fmt in ("docx", "xlsx", "pptx"):
        preview = store.add_document(docs[fmt], native=True)
        assert (preview.kind, preview.source_path, preview.document_path) == ("pdf", copy, docs[fmt])
        assert preview.title == f"bilan.{fmt}"
    assert store.add_document(docs["docx"], native=False).kind == "pdf"
    # Sans export possible : la page HTML
    monkeypatch.setattr(office_pdf, "office_pdf", lambda path: None)
    assert store.add_document(docs["docx"], native=True).kind == "document"
    # Ailleurs que sous Windows : la page HTML, qui en montre les pages en images
    monkeypatch.setattr(office_pdf, "office_pdf", lambda path: copy)
    monkeypatch.setattr(previews, "_IS_WINDOWS", False)
    page = store.add_document(docs["docx"], native=False)
    assert page.kind == "document" and 'class="office-page"' in page.html


def test_the_exported_pdf_link_bears_the_document_name(tmp_path):
    # pylint: disable=import-outside-toplevel
    from interfaces.desktop.files import FileLinks

    links = FileLinks(b"secret")
    url = links.url(str(tmp_path / "5f2e9a.pdf"), "rapport.pdf")
    assert url.endswith("/rapport.pdf")
    signature, token = url.split("/")[2:4]
    assert links.resolve(signature, token) == str(tmp_path / "5f2e9a.pdf")
    assert links.url(str(tmp_path / "note.pdf")).endswith("/note.pdf")


# ── Vrai Office (s'il est installé) ────────────────────────────────────────


def _pids(kind):
    import psutil  # pylint: disable=import-outside-toplevel

    wanted = {"word": "winword.exe", "excel": "excel.exe", "powerpoint": "powerpnt.exe"}[kind]
    return {process.pid for process in psutil.process_iter(["name"])
            if (process.info.get("name") or "").lower() == wanted}


@pytest.mark.parametrize("fmt, kind, pages", [
    ("docx", "word", 1), ("xlsx", "excel", 1), ("pptx", "powerpoint", 3)])
def test_real_office_exports_the_document(docs, cache, fmt, kind, pages):
    pymupdf = pytest.importorskip("pymupdf")
    if not office_pdf.office_installed(kind):
        pytest.skip(f"{kind} absent")
    before = _pids(kind)
    made = office_pdf.office_pdf(docs[fmt])
    assert made, f"{kind} n'a pas exporté le document"
    with pymupdf.open(made) as document:
        assert document.page_count >= pages
    # Rien de lancé pour l'export ne reste derrière lui
    deadline = time.monotonic() + 15
    while _pids(kind) - before and time.monotonic() < deadline:
        time.sleep(0.25)
    assert not _pids(kind) - before, f"{kind} lancé pour l'export resté ouvert"


def test_real_excel_prints_only_the_first_rows_of_a_long_sheet(cache, tmp_path):
    pymupdf = pytest.importorskip("pymupdf")
    if not office_pdf.office_installed("excel"):
        pytest.skip("Excel absent")
    from openpyxl import Workbook  # pylint: disable=import-outside-toplevel

    path = tmp_path / "long.xlsx"
    book = Workbook()
    for row in range(1, 3001):
        book.active.append([row, f"ligne {row}"])
    book.save(str(path))
    made = office_pdf.office_pdf(str(path))
    assert made
    with pymupdf.open(made) as document:
        text = "".join(page.get_text() for page in document)
    assert "ligne 1000" in text and "ligne 1001" not in text
