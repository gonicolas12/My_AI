"""
Tests de la lecture d'un fichier pour la mémoire des documents
(core/document_memory.py, bouton « Ajouter » de l'onglet Documents)

Un document est lu comme une pièce jointe du chat (même texte, donc même
identifiant dans ChromaDB) ; une image est décrite par le modèle de vision et
lue par l'OCR, l'une ou l'autre suffit.
"""

from types import SimpleNamespace

import pytest
from PIL import Image

from core import document_memory
from core.document_memory import STAGE_DESCRIBING, DocumentReadError, read_document
from core.i18n import tr
from models.mixins.context_management import ContextManagementMixin


class FakeLLM:
    """LocalLLM : description d'image fixe, ou aucune (pas de modèle de vision)."""

    def __init__(self, description):
        self.description = description
        self.images = []
        self.options = []

    def describe_image(self, image_base64, **options):
        self.images.append(image_base64)
        self.options.append(options)
        return self.description


def _image(tmp_path, name="photo.png"):
    path = tmp_path / name
    Image.new("RGB", (64, 48), (200, 120, 40)).save(path)
    return path


def test_document_is_read_like_a_chat_attachment(tmp_path):
    """Texte des processeurs du modèle (celui d'une pièce jointe) : même identifiant."""
    path = tmp_path / "rapport.pdf"
    path.write_bytes(b"%PDF-1.4")
    read = []
    local_ai = SimpleNamespace(
        read_file_for_context=lambda p: read.append(p) or {
            "content": "Texte du rapport", "processor_used": "PDF"})
    assert read_document(str(path), local_ai=local_ai) == ("Texte du rapport", "PDF")
    assert read == [str(path)]


def test_model_reads_a_file_without_adding_it_to_the_conversation(tmp_path):
    """read_file_for_context : le texte d'une pièce jointe, sans rien ajouter au contexte."""
    added = []

    class Model(ContextManagementMixin):
        """CustomAIModel sans processeurs avancés : lecture de base."""

        pdf_processor = docx_processor = code_processor = None

        def add_document_to_context(self, document_content, document_name=""):
            added.append((document_name, document_content))
            return {"success": True}

    path = tmp_path / "notes.txt"
    path.write_text("Point du lundi", encoding="utf-8")
    model = Model()
    assert model.read_file_for_context(str(path)) == {
        "content": "Point du lundi", "processor_used": "basic"}
    assert not added
    assert model.add_file_to_context(str(path))["processor_used"] == "basic"
    assert added == [("notes.txt", "Point du lundi")]


def test_without_engine_the_file_processor_reads_it(tmp_path):
    path = tmp_path / "notes.md"
    path.write_text("# Réunion\nLundi 9 h, salle B", encoding="utf-8")
    assert read_document(str(path)) == ("# Réunion\nLundi 9 h, salle B", "Code")
    # Processeurs du modèle en échec ou muets : le lecteur du chat prend le relais
    broken = SimpleNamespace(read_file_for_context=lambda _p: 1 / 0)
    assert read_document(str(path), local_ai=broken)[0].startswith("# Réunion")
    silent = SimpleNamespace(read_file_for_context=lambda _p: {"content": ""})
    assert read_document(str(path), local_ai=silent)[0].startswith("# Réunion")


def test_refused_files(tmp_path):
    archive = tmp_path / "sauvegarde.zip"
    archive.write_bytes(b"PK")
    with pytest.raises(DocumentReadError, match=r"\.zip"):
        read_document(str(archive))
    empty = tmp_path / "vide.txt"
    empty.write_text("  \n", encoding="utf-8")
    with pytest.raises(DocumentReadError, match="vide ou illisible"):
        read_document(str(empty))
    failing = SimpleNamespace(process_file=lambda _p: {"error": "Erreur JSON: ligne 1"})
    with pytest.raises(DocumentReadError, match="Erreur JSON"):
        read_document(str(tmp_path / "config.json"), file_processor=failing)


def test_image_is_described_then_read(tmp_path, monkeypatch):
    monkeypatch.setattr("processors.ocr.ocr_image", lambda _path: "Réunion lundi 9h\nSalle B")
    llm = FakeLLM("Un tableau blanc couvert de notes.")
    stages = []
    content, kind = read_document(str(_image(tmp_path)), local_ai=SimpleNamespace(local_llm=llm),
                                  on_stage=stages.append)
    assert kind == "Image" and stages == [STAGE_DESCRIBING]
    assert content == (
        f"{tr('memory.documents.imageDescription')}\nUn tableau blanc couvert de notes.\n\n"
        f"{tr('memory.documents.imageText')}\nRéunion lundi 9h\nSalle B")
    assert len(llm.images) == 1 and llm.images[0]  # JPEG en base64 (encode_image)
    # Consigne de la mémoire : un paragraphe sobre, pas la description détaillée du chat
    assert llm.options == [{"instructions": tr("memory.documents.visionPrompt"),
                            "max_tokens": 400}]


def test_image_needs_a_description_or_text(tmp_path, monkeypatch):
    path = _image(tmp_path)
    monkeypatch.setattr("processors.ocr.ocr_image", lambda _path: "")
    # Photo sans texte : la description suffit
    described = read_document(str(path),
                              local_ai=SimpleNamespace(local_llm=FakeLLM("Un chat roux")))
    assert described[0] == f"{tr('memory.documents.imageDescription')}\nUn chat roux"
    # Ni modèle de vision (None), ni Ollama (pas de local_ai), ni texte : refusée
    with pytest.raises(DocumentReadError, match="ni texte lisible"):
        read_document(str(path), local_ai=SimpleNamespace(local_llm=FakeLLM(None)))
    with pytest.raises(DocumentReadError, match="ni texte lisible"):
        read_document(str(path))


def test_capture_without_vision_keeps_its_text(tmp_path, monkeypatch):
    monkeypatch.setattr("processors.ocr.ocr_image", lambda _path: "Code coffre : 4512")
    assert document_memory.read_image(str(_image(tmp_path, "capture.jpg"))) == (
        f"{tr('memory.documents.imageText')}\nCode coffre : 4512")


def test_an_image_is_known_by_its_content(tmp_path):
    """Ni son nom (captures collées, toutes « clipboard_image.png »), ni sa description."""
    photo = _image(tmp_path, "photo.png")
    copy = tmp_path / "clipboard_image.png"
    copy.write_bytes(photo.read_bytes())
    other = tmp_path / "autre.png"
    Image.new("RGB", (64, 48), (0, 0, 0)).save(other)
    identifier = document_memory.image_document_id(str(photo))
    assert identifier.startswith("image_") and len(identifier) == len("image_") + 16
    assert document_memory.image_document_id(str(copy)) == identifier
    assert document_memory.image_document_id(str(other)) != identifier
    with pytest.raises(OSError):
        document_memory.image_document_id(str(tmp_path / "absente.png"))


def test_a_folder_file_is_known_by_its_path_and_content(tmp_path):
    """Fichier d'un dossier déposé : inchangé, même identifiant (pas relu) ;
    modifié, ou le même contenu sous un autre chemin, un autre."""
    first, second = tmp_path / "a.py", tmp_path / "b.py"
    first.write_text("print(1)", encoding="utf-8")
    second.write_text("print(1)", encoding="utf-8")
    identifier = document_memory.folder_document_id(str(first), "site/src/a.py")
    assert identifier.startswith("folder_") and len(identifier) == len("folder_") + 24
    assert document_memory.folder_document_id(str(second), "site/src/a.py") == identifier
    assert document_memory.folder_document_id(str(second), "site/lib/a.py") != identifier
    second.write_text("print(2)", encoding="utf-8")
    assert document_memory.folder_document_id(str(second), "site/src/a.py") != identifier


def test_unreadable_image_is_neither_described_nor_read(tmp_path, monkeypatch):
    broken = tmp_path / "abimee.png"
    broken.write_bytes(b"pas une image")

    def ocr_fails(_path):
        raise RuntimeError("image illisible")

    monkeypatch.setattr("processors.ocr.ocr_image", ocr_fails)
    llm = FakeLLM("jamais appelé")
    with pytest.raises(DocumentReadError):
        read_document(str(broken), local_ai=SimpleNamespace(local_llm=llm))
    assert not llm.images  # encode_image a échoué avant la description
