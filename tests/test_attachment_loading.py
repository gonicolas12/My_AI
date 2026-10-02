"""
Tests du cycle de vie des pièces jointes du chat (interfaces/gui).

Deux défauts observés en usage réel :
- une question envoyée pendant la lecture d'un PDF (40 s d'OCR) partait sans
  son contenu : le modèle répondait qu'il ne voyait aucun document. L'envoi est
  désormais refusé tant qu'une pièce jointe du message est en lecture, et son
  aperçu affiche un cercle de chargement ;
- un fichier joint puis retiré (bouton ✕) restait en mémoire, et sa lecture
  continuait si elle était en cours. Retirer l'aperçu arrête la lecture et
  oublie le document, sauf s'il sert encore ailleurs.
"""

import logging
import time
from types import SimpleNamespace

import pytest

from interfaces.gui import loading_spinner
from interfaces.gui.base import BaseGUI
from interfaces.gui.file_handling import FileHandlingMixin
from interfaces.gui.layout import LayoutMixin
from interfaces.modern_styles import MODERN_COLORS
from models.conversation_memory import ConversationMemory

PDF = r"C:\docs\fiche de sécurité.pdf"
NAME = "fiche de sécurité.pdf"


@pytest.fixture(name="tk_root", scope="module")
def _tk_root():
    """Une seule racine Tk pour le module : en enchaîner plusieurs dans un même
    processus échoue par intermittence sous Windows."""
    tk = pytest.importorskip("tkinter")
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("pas d'affichage disponible")
    root.withdraw()
    yield root
    root.destroy()


class _LocalAI:
    """Moteur réduit : mémoire de session réelle, oublis enregistrés."""

    def __init__(self):
        self.conversation_memory = ConversationMemory()
        self.forgotten = []

    def remove_document_from_context(self, name):
        self.forgotten.append(name)
        return {"stored": self.conversation_memory.remove_document(name), "chunks_removed": 3}


class _Gui(LayoutMixin, FileHandlingMixin):
    """Zone de saisie réduite : aperçus des pièces jointes et suivi de leur lecture."""

    def __init__(self, root, use_ctk):
        import tkinter as tk  # pylint: disable=import-outside-toplevel

        self.root = root
        self.use_ctk = use_ctk
        self.colors = dict(MODERN_COLORS)
        self.logger = logging.getLogger("test_attachment_loading")
        self._pending_files = []
        self._attachments_loading = {}
        self._attachments_introduced = set()
        self._preview_frame = tk.Frame(root)
        self.input_text = tk.Text(root)
        self.ai_engine = SimpleNamespace(local_ai=_LocalAI())
        self.conversation_history = []
        self.notifications = []
        self.calls = []

    def show_notification(self, message, type_notif="info", duration=2000):
        self.notifications.append((message, type_notif, duration))

    def is_animation_running(self):
        return False

    def hide_status_indicators(self):
        """Première étape de l'envoi après les contrôles : on s'arrête là."""
        self.calls.append("envoi")
        raise AttributeError("fin du test")

    def set_input_state(self, enabled):
        self.calls.append(("saisie", enabled))

    def _dismiss_home_screen(self):
        self.calls.append("accueil fermé")


@pytest.fixture(name="gui", params=[True, False], ids=["customtkinter", "tkinter"])
def _gui(request, tk_root):
    if request.param:
        pytest.importorskip("customtkinter")
    gui = _Gui(tk_root, use_ctk=request.param)
    yield gui
    gui.clear_file_previews()
    gui.input_text.destroy()
    gui._preview_frame.destroy()


def _attach(gui, path=PDF):
    """Ce que fait process_file avant de lancer la lecture en arrière-plan.

    Returns:
        (aperçu, événement d'arrêt de la lecture)
    """
    cancel = gui._attachment_loading_started(path)
    gui.add_file_preview(path, "PDF")
    return gui._pending_files[-1][2], cancel


def _store(gui, name=NAME):
    """Ce que la lecture range en mémoire de session."""
    gui.ai_engine.local_ai.conversation_memory.store_document_content(name, "contenu " * 50)


def _memory(gui):
    return gui.ai_engine.local_ai.conversation_memory.stored_documents


def _click_remove(thumb):
    """Bouton ✕ de l'aperçu."""
    (button,) = [w for w in thumb.winfo_children() if str(w.cget("text")) == "✕"]
    button.invoke()


# ── Envoi pendant la lecture ──────────────────────────────────────────────


def test_send_is_refused_while_attachment_loads(gui):
    _attach(gui)
    gui.input_text.insert("1.0", "que dit ce pdf ?")
    BaseGUI.send_message(gui)
    assert gui.calls == []  # rien n'est parti
    assert gui.input_text.get("1.0", "end-1c") == "que dit ce pdf ?"
    (message, kind, _), = gui.notifications
    assert kind == "warning" and "en cours de chargement" in message


def test_send_goes_through_once_loaded(gui):
    _thumb, cancel = _attach(gui)
    gui.input_text.insert("1.0", "que dit ce pdf ?")
    gui._attachment_loading_finished(PDF, cancel)
    BaseGUI.send_message(gui)
    assert gui.calls[0] == "envoi" and gui.notifications == []


def test_removing_the_loading_attachment_allows_sending(gui):
    thumb, _cancel = _attach(gui)
    _click_remove(thumb)
    gui.input_text.insert("1.0", "question sans pièce jointe")
    BaseGUI.send_message(gui)
    assert gui.calls[0] == "envoi"


def test_home_screen_keeps_its_text_while_loading(gui, tk_root):
    import tkinter as tk  # pylint: disable=import-outside-toplevel

    _attach(gui)
    gui._home_input = tk.Text(tk_root)
    gui._home_input.insert("1.0", "résume ce document")
    BaseGUI._home_screen_send(gui)
    assert "accueil fermé" not in gui.calls
    assert gui._home_input.get("1.0", "end-1c") == "résume ce document"
    assert gui.notifications
    gui._home_input.destroy()


def test_spinner_shows_while_loading_and_disappears_after(gui, tk_root):
    thumb, cancel = _attach(gui)
    spinner = thumb.loading_spinner
    tk_root.update()
    assert spinner is not None and spinner.winfo_exists()
    assert spinner.winfo_manager() == "pack"

    gui._attachment_loading_finished(PDF, cancel)
    tk_root.update()
    assert thumb.loading_spinner is None and not spinner.winfo_exists()
    assert thumb.name_label.pack_info()["padx"] == (8, 4)


def test_loaded_attachment_has_no_spinner(gui):
    gui.add_file_preview(PDF, "PDF")
    assert gui._pending_files[-1][2].loading_spinner is None


def test_same_file_attached_twice_waits_for_both_reads(gui):
    _thumb, first = _attach(gui)
    _thumb, second = _attach(gui)
    gui._attachment_loading_finished(PDF, first)
    assert gui._refuse_send_while_loading()
    gui._attachment_loading_finished(PDF, second)
    gui.notifications.clear()
    assert not gui._refuse_send_while_loading()


def test_failed_read_unblocks_sending(gui, tk_root):
    """Fichier illisible : la lecture échoue mais l'envoi ne reste pas bloqué."""

    class Unreadable:
        @staticmethod
        def process_file(_path):
            return {"error": "PDF illisible"}

    gui.file_processor = Unreadable()
    _thumb, cancel = _attach(gui)
    gui.process_file_background(PDF, "PDF", NAME, cancel)
    tk_root.update()
    assert not gui._is_attachment_loading(PDF)
    assert any(kind == "error" for _, kind, _ in gui.notifications)


# ── Pièce jointe retirée (bouton ✕) ───────────────────────────────────────


def test_removed_attachment_is_forgotten(gui):
    thumb, cancel = _attach(gui)
    _store(gui)
    gui._attachment_loading_finished(PDF, cancel)
    _click_remove(thumb)
    assert NAME not in _memory(gui)
    assert gui.ai_engine.local_ai.forgotten == [NAME]


def test_removal_during_reading_stops_it_then_forgets(gui):
    thumb, cancel = _attach(gui)
    _click_remove(thumb)
    assert cancel.is_set()  # la lecture s'arrête avant la page suivante
    assert gui.ai_engine.local_ai.forgotten == []  # pas encore : elle tourne
    _store(gui)  # ce que la lecture avait déjà rangé
    gui._attachment_loading_finished(PDF, cancel)
    assert NAME not in _memory(gui)


def test_interrupted_read_stores_nothing_and_reports_no_error(gui, tk_root):
    class SlowReader:
        @staticmethod
        def process_file(_path):
            cancel.set()  # retirée pendant la lecture
            return {"content": "texte de la première page"}

    gui.file_processor = SlowReader()
    gui.custom_ai = None
    _thumb, cancel = _attach(gui)
    gui.process_file_background(PDF, "PDF", NAME, cancel)
    tk_root.update()
    assert NAME not in _memory(gui)
    assert not any(kind == "error" for _, kind, _ in gui.notifications)


def test_document_already_in_memory_is_kept(gui):
    """Déjà joint et envoyé dans une autre conversation de la session."""
    _store(gui)
    thumb, cancel = _attach(gui)
    gui._attachment_loading_finished(PDF, cancel)
    _click_remove(thumb)
    assert NAME in _memory(gui)


def test_document_attached_to_a_message_is_kept(gui):
    thumb, cancel = _attach(gui)
    _store(gui)
    gui._attachment_loading_finished(PDF, cancel)
    gui.conversation_history.append({"is_user": True, "attachments": [(PDF, "PDF")]})
    _click_remove(thumb)
    assert NAME in _memory(gui)


def test_document_attached_to_another_edit_variant_is_kept(gui):
    thumb, cancel = _attach(gui)
    _store(gui)
    gui._attachment_loading_finished(PDF, cancel)
    gui._turn_branches = {"m1": {"current": 1, "versions": [
        {"user": "version d'avant", "attachments": [[PDF, "PDF"]], "tail": []},
        {"user": "version affichée", "attachments": [], "tail": []},
    ]}}
    _click_remove(thumb)
    assert NAME in _memory(gui)


def test_same_file_still_attached_to_another_preview_is_kept(gui):
    first, cancel_1 = _attach(gui)
    _second, cancel_2 = _attach(gui)
    _store(gui)
    gui._attachment_loading_finished(PDF, cancel_1)
    gui._attachment_loading_finished(PDF, cancel_2)
    _click_remove(first)
    assert NAME in _memory(gui)


def test_sent_attachment_is_not_forgotten_by_a_later_preview(gui):
    thumb, cancel = _attach(gui)
    _store(gui)
    gui._attachment_loading_finished(PDF, cancel)
    gui.clear_file_previews()  # envoi du message
    thumb, cancel = _attach(gui)  # même fichier, joint à nouveau
    gui._attachment_loading_finished(PDF, cancel)
    _click_remove(thumb)
    assert NAME in _memory(gui)


def test_mobile_read_is_never_forgotten(gui, tk_root):
    """Relay mobile : lecture sans aperçu (cancel=None), rien à oublier ensuite."""

    class Reader:
        @staticmethod
        def process_file(_path):
            return {"content": "contenu de la fiche"}

    gui.file_processor = Reader()
    gui.custom_ai = None
    gui.process_file_background(PDF, "PDF", NAME)
    tk_root.update()
    assert NAME in _memory(gui)
    assert gui.ai_engine.local_ai.forgotten == []


def test_removal_during_ocr_skips_the_remaining_pages(gui, tk_root, tmp_path, monkeypatch):
    """Bout en bout : PDF de 3 pages scannées, aperçu retiré pendant la première."""
    pymupdf = pytest.importorskip("pymupdf")
    from processors import ocr  # pylint: disable=import-outside-toplevel
    from utils.file_processor import FileProcessor  # pylint: disable=import-outside-toplevel

    pages = []

    def engine(_image):
        pages.append(1)
        _click_remove(thumb)  # l'utilisateur clique sur ✕ pendant l'OCR
        return SimpleNamespace(txts=("texte reconnu",))

    monkeypatch.setattr(ocr, "_get_engine", lambda: engine)
    monkeypatch.setattr(ocr, "RapidOCR", object)
    path = str(tmp_path / "scan.pdf")
    pdf = pymupdf.open()
    for _ in range(3):
        pdf.new_page()  # pages sans couche texte : OCR
    pdf.save(path)
    pdf.close()

    gui.file_processor = FileProcessor()
    gui.custom_ai = None
    thumb, cancel = _attach(gui, path)
    gui.process_file_background(path, "PDF", "scan.pdf", cancel)
    tk_root.update()
    assert pages == [1]  # pages 2 et 3 jamais reconnues
    assert "scan.pdf" not in _memory(gui)
    assert not gui._is_attachment_loading(path)
    assert not any(kind == "error" for _, kind, _ in gui.notifications)


# ── Cercle de chargement ──────────────────────────────────────────────────


def test_spinner_turns_until_destroyed(tk_root, capfd):
    spinner = loading_spinner.create_loading_spinner(tk_root, "#ff6b47", "#2a2a2a", use_ctk=False)
    spinner.pack()
    shown = set()
    deadline = time.time() + 0.5
    while time.time() < deadline:
        tk_root.update()
        shown.add(str(spinner.cget("image")))
        time.sleep(0.01)
    assert len(shown) > 3  # plusieurs images en une demi-seconde : il tourne

    spinner.destroy()
    deadline = time.time() + 0.2
    while time.time() < deadline:  # minuterie en cours après la destruction
        tk_root.update()
        time.sleep(0.01)
    assert "invalid command name" not in capfd.readouterr().err


def test_spinner_follows_screen_scaling(tk_root):
    """Avec CustomTkinter, des CTkImage : CTk les met à l'échelle de l'écran
    (125 %, 150 %...) comme le texte voisin, y compris si elle change."""
    ctk = pytest.importorskip("customtkinter")
    spinner = loading_spinner.create_loading_spinner(tk_root, "#ff6b47", "#2a2a2a", use_ctk=True)
    image = spinner.cget("image")
    assert isinstance(image, ctk.CTkImage)
    assert image.cget("size") == (loading_spinner.SIZE, loading_spinner.SIZE)
    spinner.destroy()


@pytest.mark.parametrize("scaling", [1.0, 1.25, 1.5, 1.75, 2.0])
def test_spinner_edge_is_smooth_and_center_transparent(scaling):
    """Image réduite comme CTk le fait à cette échelle (17 px à 125 %)."""
    side = int(loading_spinner.SIZE * scaling)
    frame = loading_spinner._frames("#ff6b47")[0].resize((side, side))
    assert frame.getpixel((side // 2, side // 2))[3] == 0  # centre transparent
    alphas = {frame.getpixel((x, y))[3] for x in range(side) for y in range(side)}
    assert len(alphas) > 8  # dégradé sur le bord : lissé, pas crénelé
