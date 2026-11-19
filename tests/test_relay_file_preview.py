"""
Aperçu des fichiers dans la modale du téléphone et de l'extension VS Code.

Ni le téléphone ni VS Code ne lisent le disque du PC : ils demandent l'aperçu
d'un fichier au Relay (message WS « file_preview »), qui ne montre que les
fichiers de leurs conversations (pièces jointes, fichiers cités ou nommés par
une réponse, documents et images produits) et renvoie ce que la modale sait
afficher (relay/file_preview.py). Les réponses du chat portent les fichiers
qu'elles citent ou nomment, cliquables sur le téléphone.
"""

import base64
import json
import os

import pytest

from relay import file_preview
from relay.relay_bridge import RelayBridge, RelayMessage
from relay.relay_server import RelayServer

testclient = pytest.importorskip("fastapi.testclient")


@pytest.fixture(autouse=True)
def _no_office_export(monkeypatch):
    """Les documents de ces tests ne passent pas par Word ni Excel (tests/test_office_pdf.py)."""
    # pylint: disable-next=import-outside-toplevel
    from interfaces import office_pdf

    monkeypatch.setattr(office_pdf, "office_pdf", lambda path: None)


@pytest.fixture(name="bridge")
def bridge_fixture():
    """Le pont du Relay (singleton), vide avant et après chaque test."""
    bridge = RelayBridge()
    bridge.reset()
    yield bridge
    bridge.reset()


class _CodeHub:
    """Conversation Code réduite à ses pièces jointes (chemins normalisés)."""

    def __init__(self):
        self.paths = set()

    def known_paths(self):
        return set(self.paths)


@pytest.fixture(name="server")
def server_fixture(bridge, tmp_path, monkeypatch):
    """Relay construit sans uvicorn, ses envois dans un dossier du test."""
    del bridge  # vide avant et après le test
    server = RelayServer(config={}, code_hub=_CodeHub())
    uploads = tmp_path / "envois"
    uploads.mkdir()
    monkeypatch.setattr(server, "_upload_dir", uploads)
    return server


# ── Ce que la modale reçoit (relay/file_preview.py) ─────────────────────────


def test_an_image_comes_with_its_data(tmp_path):
    image = tmp_path / "photo.png"
    image.write_bytes(b"\x89PNG\r\n\x1a\nfake")
    preview = file_preview.build_preview(str(image))
    assert preview["kind"] == "image" and preview["mime"] == "image/png"
    assert base64.b64decode(preview["data"]) == image.read_bytes()
    assert preview["name"] == "photo.png" and preview["size"] == image.stat().st_size


def test_a_svg_is_an_image_with_its_source(tmp_path):
    drawing = tmp_path / "logo.svg"
    drawing.write_text('<svg xmlns="http://www.w3.org/2000/svg"><circle r="4"/></svg>',
                       encoding="utf-8")
    preview = file_preview.build_preview(str(drawing))
    assert preview["kind"] == "image" and preview["mime"] == "image/svg+xml"
    assert "<circle" in preview["text"] and preview["language"] == "xml"


def test_code_comes_as_text_with_its_language(tmp_path):
    script = tmp_path / "main.py"
    script.write_bytes("print('é')\n".encode("utf-8"))
    preview = file_preview.build_preview(str(script))
    assert preview["kind"] == "text" and preview["language"] == "python"
    assert preview["text"] == "print('é')\n" and preview["truncated"] is False


def test_a_long_text_is_cut(tmp_path, monkeypatch):
    monkeypatch.setattr(file_preview, "TEXT_MAX", 10)
    notes = tmp_path / "notes.txt"
    notes.write_text("a" * 50, encoding="utf-8")
    preview = file_preview.build_preview(str(notes))
    assert preview["text"] == "a" * 10 and preview["truncated"] is True


def test_a_web_page_comes_as_its_source(tmp_path):
    page = tmp_path / "index.html"
    page.write_text("<h1>Bonjour</h1><script>alert(1)</script>", encoding="utf-8")
    preview = file_preview.build_preview(str(page))
    assert preview["kind"] == "html" and "<script>" in preview["text"]


def test_markdown_is_rendered_with_its_source(tmp_path):
    readme = tmp_path / "README.md"
    readme.write_text('<div align="center">\n\n# Projet\n</div>\n', encoding="utf-8")
    preview = file_preview.build_preview(str(readme))
    assert preview["kind"] == "document" and "<h1>Projet</h1>" in preview["html"]
    assert "&lt;div" not in preview["html"]
    assert preview["text"].startswith('<div align="center">') and preview["language"] == "markdown"


def test_a_csv_is_a_table_with_its_source(tmp_path):
    # Export d'Excel en France : Windows-1252, séparé par « ; »
    table = tmp_path / "Phrases.csv"
    table.write_bytes("Code Phrase;Description\r\n251;NE PAS BRÛLER\r\n".encode("cp1252"))
    preview = file_preview.build_preview(str(table))
    assert preview["kind"] == "document"
    assert "<th>Code Phrase</th><th>Description</th>" in preview["html"]
    assert '<td class="num">251</td><td>NE PAS BRÛLER</td>' in preview["html"]
    assert preview["text"].startswith("Code Phrase;Description") and preview["language"] == "csv"


def test_a_csv_that_is_not_text_keeps_its_table(tmp_path):
    table = tmp_path / "export.csv"
    table.write_bytes(b"a;b\x00\n1;2\n")
    preview = file_preview.build_preview(str(table))
    assert preview["kind"] == "document" and "<table" in preview["html"]
    assert "text" not in preview and "language" not in preview


def test_a_pdf_is_rendered_by_the_document_preview(tmp_path):
    pymupdf = pytest.importorskip("pymupdf")
    pdf = tmp_path / "rapport.pdf"
    document = pymupdf.open()
    document.new_page().insert_text((72, 72), "Bonjour")
    document.save(str(pdf))
    document.close()
    preview = file_preview.build_preview(str(pdf))
    assert preview["kind"] == "document" and 'class="pdf-page"' in preview["html"]
    assert preview["label"]


def test_a_binary_file_has_no_preview_but_its_name(tmp_path):
    archive = tmp_path / "donnees.bin"
    archive.write_bytes(b"\x00\x01\x02" * 10)
    preview = file_preview.build_preview(str(archive))
    assert preview["kind"] == "none" and preview["name"] == "donnees.bin"
    assert "text" not in preview and "data" not in preview


def test_a_huge_image_keeps_only_its_download(tmp_path, monkeypatch):
    monkeypatch.setattr(file_preview, "INLINE_MAX", 4)
    image = tmp_path / "grande.jpg"
    image.write_bytes(b"\xff\xd8" * 10)
    assert file_preview.build_preview(str(image))["kind"] == "none"
    download = file_preview.build_download(str(image))
    assert download["download"] is True and download["mime"] == "image/jpeg"
    assert base64.b64decode(download["data"]) == image.read_bytes()


def test_a_missing_or_too_big_file_says_why(tmp_path, monkeypatch):
    with pytest.raises(file_preview.PreviewError):
        file_preview.build_preview(str(tmp_path / "absent.txt"))
    monkeypatch.setattr(file_preview, "DOWNLOAD_MAX", 4)
    big = tmp_path / "gros.zip"
    big.write_bytes(b"x" * 10)
    with pytest.raises(file_preview.PreviewError):
        file_preview.build_download(str(big))


def test_an_upload_shows_the_name_it_was_sent_with(tmp_path):
    uploads = tmp_path / "envois"
    uploads.mkdir()
    sent = uploads / "0123456789abcdef_budget.xlsx"
    assert file_preview.display_name(str(sent), str(uploads)) == "budget.xlsx"
    elsewhere = tmp_path / "0123456789abcdef_budget.xlsx"
    assert file_preview.display_name(str(elsewhere), str(uploads)) == elsewhere.name


# ── Réponses du chat : leurs fichiers (relay_bridge.py) ─────────────────────


def test_an_answer_keeps_its_links_and_the_files_it_produced(bridge, tmp_path):
    document = tmp_path / "rapport.docx"
    document.write_bytes(b"PK")
    bridge.arm_response("relay_1")
    bridge.submit_ai_document(str(document), message_id="relay_1")
    links = [{"text": "rapport.docx", "path": str(document), "dir": False, "name": True},
             {"text": "C:\\dossier", "path": "C:\\dossier", "dir": True}, {"text": ""}]
    bridge.submit_ai_response("Voici rapport.docx.", message_id="relay_1", links=links)

    extras = bridge.response_extras("relay_1")
    assert [link["text"] for link in extras["links"]] == ["rapport.docx", "C:\\dossier"]
    assert extras["files"] == [{"path": str(document), "name": "rapport.docx", "kind": "document"}]
    answer = bridge.history[-1]
    assert answer["links"] == extras["links"] and answer["files"] == extras["files"]
    assert bridge.response_extras("inconnu") == {"links": [], "files": []}


def test_the_conversation_knows_its_files_but_not_folders(bridge, tmp_path):
    photo, notes, made = (tmp_path / name for name in ("photo.png", "notes.txt", "image.png"))
    bridge.send_to_gui(RelayMessage(text="", is_user=True, image_path=str(photo),
                                    file_paths=[str(notes)]))
    bridge.submit_ai_image(str(made), message_id="relay_2")
    bridge.submit_ai_response("ok", message_id="relay_2", links=[
        {"text": "C:\\dossier", "path": str(tmp_path), "dir": True}])
    known = bridge.known_paths()
    for path in (photo, notes, made):
        assert str(path).lower() in {item.lower() for item in known}
    assert str(tmp_path).lower() not in {item.lower() for item in known}
    bridge.clear_history()
    assert not bridge.known_paths()


# ── Ce que le Relay montre (relay_server.py) ────────────────────────────────


def test_only_files_of_the_conversations_are_shown(server, bridge, tmp_path):
    sent = server.upload_dir / "0123456789abcdef_photo.png"
    sent.write_bytes(b"png")
    cited, code_file, other = (tmp_path / name for name in ("cite.txt", "code.py", "autre.txt"))
    for path in (cited, code_file, other):
        path.write_text("x", encoding="utf-8")
    bridge.submit_ai_response("Voir cite.txt", message_id="relay_3",
                              links=[{"text": "cite.txt", "path": str(cited)}])
    server.code_hub.paths = {os.path.normcase(os.path.abspath(str(code_file)))}

    assert server.preview_allowed(str(sent))
    assert server.preview_allowed(str(cited))
    assert server.preview_allowed(str(code_file))
    assert not server.preview_allowed(str(other))
    assert not server.preview_allowed(str(tmp_path))
    refused = server.preview_file({"path": str(other)})
    assert refused["ok"] is False and refused["error"]


def test_an_attachment_stays_previewable_after_it_was_sent(server):
    sent = server.upload_dir / "0123456789abcdef_notes.md"
    sent.write_text("# Titre\n", encoding="utf-8")
    server.register_upload("0123456789abcdef", sent, False, "notes.md")
    assert server.consume_upload_ids(["0123456789abcdef"]) == (None, [str(sent)])

    preview = server.preview_file({"file_id": "0123456789abcdef"})
    assert preview["ok"] is True and preview["name"] == "notes.md"
    # En tête de la page, le nom qu'elle avait à l'envoi, pas celui du dossier des envois
    assert preview["kind"] == "document" and ">Titre</h1>" in preview["html"]
    assert ">notes.md</h1>" in preview["html"] and "0123456789abcdef" not in preview["html"]
    by_path = server.preview_file({"path": str(sent)})
    assert by_path["ok"] is True and by_path["name"] == "notes.md"
    download = server.preview_file({"file_id": "0123456789abcdef", "download": True})
    assert base64.b64decode(download["data"]) == sent.read_bytes()
    assert server.preview_file({"file_id": "ffffffffffffffff"})["ok"] is False


def _session(client, server):
    response = client.post(f"/api/unlock?token={server.auth_token}",
                           json=server.encrypt_json({"code": server.access_code}))
    return server.decrypt_json(response.json())["session"]


def test_the_phone_asks_a_preview_over_the_websocket(server):
    sent = server.upload_dir / "0123456789abcdef_main.py"
    sent.write_bytes(b"x = 1\n")
    server.register_upload("0123456789abcdef", sent, False, "main.py")
    client = testclient.TestClient(server._app)  # pylint: disable=protected-access
    session = _session(client, server)
    with client.websocket_connect(f"/ws?token={server.auth_token}&session={session}") as ws:
        # Identifiant de demande invalide : ignoré
        ws.send_text(json.dumps(server.encrypt_json(
            {"type": "file_preview", "request_id": "x" * 100, "file_id": "0123456789abcdef"})))
        ws.send_text(json.dumps(server.encrypt_json(
            {"type": "file_preview", "request_id": "r1", "file_id": "0123456789abcdef"})))
        reply = server.decrypt_json(json.loads(ws.receive_text()))
    assert reply["type"] == "file_preview" and reply["request_id"] == "r1"
    assert reply["ok"] is True and reply["kind"] == "text" and reply["text"] == "x = 1\n"


def test_a_reconnected_phone_gets_the_links_of_its_answer(server, bridge, tmp_path):
    cited = tmp_path / "rapport.pdf"
    cited.write_bytes(b"%PDF")
    bridge.arm_response("relay_4")
    bridge.submit_ai_response("Voir rapport.pdf", message_id="relay_4",
                              links=[{"text": "rapport.pdf", "path": str(cited), "name": True}])
    client = testclient.TestClient(server._app)  # pylint: disable=protected-access
    session = _session(client, server)
    response = client.get(f"/api/pending?token={server.auth_token}&session={session}"
                          "&message_id=relay_4")
    pending = server.decrypt_json(response.json())
    assert pending["final"] is True and pending["message"] == "Voir rapport.pdf"
    assert pending["links"] == [{"text": "rapport.pdf", "path": str(cited), "dir": False,
                                 "name": True}]


def test_an_upload_keeps_its_name_in_a_folder_of_its_own(server):
    """Envoi du téléphone : un dossier par envoi, le fichier sous son nom (bulle de
    la fenêtre, réponse qui le nomme, aperçu)."""
    client = testclient.TestClient(server._app)  # pylint: disable=protected-access
    session = _session(client, server)
    name = "Budget 2026.xlsx".encode("utf-8")
    plain = b"MYAI" + len(name).to_bytes(2, "big") + name + b"PK contenu"
    response = client.post(f"/api/upload?token={server.auth_token}&session={session}",
                           files={"file": ("enc.bin", server.encrypt_bytes(plain),
                                           "application/octet-stream")})
    assert response.status_code == 200
    sent = server.decrypt_json(response.json())
    path = server.upload_dir / sent["file_id"] / "Budget_2026.xlsx"
    assert sent["filename"] == "Budget_2026.xlsx" and path.read_bytes() == b"PK contenu"
    assert server.preview_file({"path": str(path)})["name"] == "Budget_2026.xlsx"


def test_files_cited_by_an_agent_result_sent_to_the_phone_are_shown(server, tmp_path):
    """Page Agents du téléphone : la fin d'une section porte les fichiers que son
    résultat cite ou nomme ; le Relay les montre, pas les dossiers ni le reste."""
    cited, other = tmp_path / "rapport.pdf", tmp_path / "autre.pdf"
    for path in (cited, other):
        path.write_bytes(b"%PDF")
    assert not server.preview_allowed(str(cited))
    server.note_agent_links({"type": "agent_section_chunk", "links": [{"path": str(other)}]})
    server.note_agent_links({"type": "agent_section_end", "section_id": 0, "links": [
        {"text": "rapport.pdf", "path": str(cited), "name": True},
        {"text": "dossier", "path": str(tmp_path), "dir": True}, "pas un lien"]})
    assert server.preview_allowed(str(cited))
    assert not server.preview_allowed(str(other)) and not server.preview_allowed(str(tmp_path))
    assert server.preview_file({"path": str(cited)})["ok"] is True


def test_a_link_sent_again_is_forgotten_last(server, tmp_path, monkeypatch):
    """Les fichiers montrables sont bornés : un lien renvoyé au téléphone (vue Code
    relue) redevient le plus récent, les plus anciens sont oubliés d'abord."""
    # pylint: disable-next=import-outside-toplevel
    from relay import relay_server as relay_server_module

    monkeypatch.setattr(relay_server_module, "_LINKED_PATHS_MAX", 2)
    first, second, third = (tmp_path / f"{name}.txt" for name in ("a", "b", "c"))
    for path in (first, second, third):
        path.write_text("x", encoding="utf-8")
    note = server._note_linked_paths  # pylint: disable=protected-access
    note([{"path": str(first)}, {"path": str(second)}])
    note([{"path": str(first)}])
    note([{"path": str(third)}])
    assert server.preview_allowed(str(first)) and server.preview_allowed(str(third))
    assert not server.preview_allowed(str(second))
