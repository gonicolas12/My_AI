"""
Tests des fichiers locaux et des aperçus de l'interface web
(interfaces/desktop/files.py, previews.py, api_files.py)

La page ne lit le disque que par des liens signés par le serveur, pour des
fichiers qu'il connaît ; seuls les documents produits par l'appli s'ouvrent
dans leur application ; un chemin cité est montré, jamais exécuté. Les pages
d'aperçu portent leur propre politique de sécurité.
"""

import os
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from core.chat_service import ChatService
from interfaces.desktop import files as local_files
from interfaces.desktop import previews as desktop_previews
from interfaces.desktop.events import EventBus
from interfaces.desktop.server import DesktopServer
from test_chat_service import FakeEngine, FakeFileProcessor, wait_for  # pylint: disable=import-error
from test_desktop_server import AUTH, BASE, PORT, FakeApp  # pylint: disable=import-error


@pytest.fixture(name="desk")
def desk_fixture(tmp_path, monkeypatch):
    """Serveur desktop avec un dossier outputs/ et des envois propres au test."""
    outputs = tmp_path / "outputs"
    (outputs / "documents").mkdir(parents=True)
    monkeypatch.setattr(local_files, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(local_files, "UPLOAD_DIR", tmp_path / "envois")
    monkeypatch.chdir(tmp_path)

    engine = FakeEngine(tmp_path / "workspaces")
    bus = EventBus()
    events = []
    bus.subscribe(events.append)
    chat = ChatService(engine, bus.publish, file_processor=FakeFileProcessor(),
                       ui_connected=lambda: True)
    chat.start()
    app = FakeApp(chat, bus, engine=engine)
    app.config = None
    server = DesktopServer(app)
    server.port = PORT
    server.previews = desktop_previews.PreviewStore(directory=tmp_path / "outputs" / "artifacts")
    client = TestClient(server.fastapi, base_url=BASE)
    yield SimpleNamespace(client=client, chat=chat, server=server, events=events,
                          tmp_path=tmp_path, outputs=outputs)
    chat.close()


def write(path, content="contenu"):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return str(path)


# ── Liens signés ────────────────────────────────────────────────────────────


def test_signed_link_round_trips_and_resists_tampering(tmp_path):
    links = local_files.FileLinks(b"secret")
    target = write(tmp_path / "Dossier é" / "rapport final.pdf")
    url = links.url(target)
    assert url.startswith("/files/") and url.endswith("/rapport%20final.pdf")
    _, _, signature, token, _name = url.split("/")
    assert links.resolve(signature, token) == os.path.abspath(target)
    # Autre chemin, ou signature d'un autre lancement : refusés
    other = local_files.FileLinks(b"autre").url(target).split("/")
    assert links.resolve(other[2], token) is None
    forged = links.url(str(tmp_path / "secret.txt")).split("/")[3]
    assert links.resolve(signature, forged) is None


def test_generated_files_are_those_inside_outputs(tmp_path):
    roots = [str(tmp_path / "outputs")]
    inside = write(tmp_path / "outputs" / "documents" / "note.docx")
    outside = write(tmp_path / "ailleurs" / "note.docx")
    sneaky = str(tmp_path / "outputs" / ".." / "ailleurs" / "note.docx")
    assert local_files.is_generated(inside, roots)
    assert not local_files.is_generated(outside, roots)
    assert not local_files.is_generated(sneaky, roots)
    assert not local_files.is_generated(str(tmp_path / "outputs" / "absent.docx"), roots)


def test_links_are_signed_only_for_files_the_conversation_knows(desk):
    attached = write(desk.tmp_path / "Documents" / "joint.txt")
    generated = write(desk.outputs / "image.png")
    unknown = write(desk.tmp_path / "Documents" / "secret.txt")
    desk.client.post("/api/attachments", json={"path": attached}, headers=AUTH)

    links = desk.client.post("/api/files/links", headers=AUTH,
                             json={"paths": [attached, generated, unknown, "C:/absent.txt"]}
                             ).json()["links"]
    assert links[attached] and links[generated]
    assert links[unknown] is None and links["C:/absent.txt"] is None
    # Sans le jeton du lancement : refusé
    assert desk.client.post("/api/files/links", json={"paths": [attached]}).status_code == 401

    served = desk.client.get(links[attached])
    assert served.status_code == 200 and served.text == "contenu"
    # Isolé s'il s'affichait comme une page ; PDF excepté (lecteur de WebView2)
    assert served.headers["content-security-policy"].startswith("sandbox")
    pdf = write(desk.outputs / "rapport.pdf", "%PDF-1.4")
    pdf_url = desk.client.post("/api/files/links", headers=AUTH,
                               json={"paths": [pdf]}).json()["links"][pdf]
    served = desk.client.get(pdf_url)
    assert served.headers["content-type"] == "application/pdf"
    assert "content-security-policy" not in served.headers
    assert served.headers["content-disposition"].startswith("inline")


def test_a_tampered_link_serves_nothing(desk):
    generated = write(desk.outputs / "image.png")
    url = desk.server.links.url(generated)
    _, _, signature, _token, name = url.split("/")
    forged = desk.server.links.url(str(desk.tmp_path / "secret.txt")).split("/")[3]
    assert desk.client.get(f"/files/{signature}/{forged}/{name}").status_code == 404
    assert desk.client.get("/files/x/y/z").status_code == 404


# ── Ouvrir, montrer, copier ─────────────────────────────────────────────────


def test_only_generated_documents_open_in_their_application(desk, monkeypatch):
    opened = []
    monkeypatch.setattr(local_files, "open_with_default_app", opened.append)
    generated = write(desk.outputs / "documents" / "rapport.docx")
    foreign = write(desk.tmp_path / "Documents" / "virus.exe")

    assert desk.client.post("/api/files/open", json={"path": generated},
                            headers=AUTH).json() == {"ok": True}
    refused = desk.client.post("/api/files/open", json={"path": foreign}, headers=AUTH)
    assert refused.status_code == 403
    assert refused.json()["detail"] == "Seuls les documents produits par My_AI s'ouvrent ici."
    assert opened == [generated]


def test_cited_paths_are_revealed_never_executed(desk, monkeypatch):
    revealed = []
    monkeypatch.setattr(local_files, "reveal_in_file_manager", revealed.append)
    existing = write(desk.tmp_path / "Documents" / "script.bat", "@echo off")
    assert desk.client.post("/api/files/reveal", json={"path": existing},
                            headers=AUTH).json() == {"ok": True}
    missing = desk.client.post("/api/files/reveal", headers=AUTH,
                               json={"path": str(desk.tmp_path / "absent.txt")})
    assert missing.status_code == 404
    assert revealed == [existing]


def test_generated_file_is_copied_to_downloads(desk, monkeypatch):
    downloads = desk.tmp_path / "Téléchargements"
    monkeypatch.setattr(local_files, "downloads_dir", lambda: downloads)
    generated = write(desk.outputs / "calcul.py", "print(1)")
    copied = desk.client.post("/api/files/download", json={"path": generated},
                              headers=AUTH).json()["path"]
    assert copied == str(downloads / "calcul.py")
    assert (downloads / "calcul.py").read_text(encoding="utf-8") == "print(1)"
    foreign = write(desk.tmp_path / "Documents" / "perso.txt")
    assert desk.client.post("/api/files/download", json={"path": foreign},
                            headers=AUTH).status_code == 403


# ── Aperçus ─────────────────────────────────────────────────────────────────


def test_artifact_page_keeps_its_scripts_but_is_isolated(desk):
    created = desk.client.post("/api/previews/artifact", headers=AUTH, json={
        "code": "<h1>Bonjour</h1><script>document.title='x'</script>", "kind": "html",
        "title": "Bonjour", "index": 0,
    }).json()
    assert created["kind"] == "html" and created["url"] == f"/preview/{created['id']}"
    page = desk.client.get(created["url"])
    assert page.status_code == 200 and "<script>document.title='x'</script>" in page.text
    policy = page.headers["content-security-policy"]
    # Sa propre politique, et non celle de l'appli (script-src 'self')
    assert policy == desktop_previews.ARTIFACT_CSP
    assert "allow-same-origin" not in policy and "allow-scripts" in policy
    assert desk.client.get("/preview/inconnu").status_code == 404
    bad = desk.client.post("/api/previews/artifact", headers=AUTH,
                           json={"code": "x", "kind": "python"})
    assert bad.status_code == 422


def test_document_preview_is_html_without_scripts(desk):
    note = write(desk.outputs / "documents" / "note.md", "# Titre\n\nTexte <script>x</script>")
    created = desk.client.post("/api/previews/document", json={"path": note},
                               headers=AUTH).json()
    assert created["kind"] == "document" and created["title"] == "note.md"
    page = desk.client.get(created["url"])
    assert "Titre" in page.text and "<script>x</script>" not in page.text
    assert page.headers["content-security-policy"] == desktop_previews.DOCUMENT_CSP


def test_pdf_preview_is_the_file_itself(desk):
    pdf = write(desk.outputs / "rapport.pdf", "%PDF-1.4")
    created = desk.client.post("/api/previews/document", json={"path": pdf},
                               headers=AUTH).json()
    assert created["kind"] == "pdf" and created["url"].startswith("/files/")
    assert desk.client.get(created["url"]).headers["content-type"] == "application/pdf"


def test_unknown_or_unsupported_documents_have_no_preview(desk):
    secret = write(desk.tmp_path / "Documents" / "secret.md")
    assert desk.client.post("/api/previews/document", json={"path": secret},
                            headers=AUTH).status_code == 404
    binary = write(desk.outputs / "programme.exe")
    assert desk.client.post("/api/previews/document", json={"path": binary},
                            headers=AUTH).status_code == 422


def test_preview_opens_in_the_system_browser(desk, monkeypatch):
    opened = []
    monkeypatch.setattr(desktop_previews.webbrowser, "open", opened.append)
    created = desk.client.post("/api/previews/artifact", headers=AUTH,
                               json={"code": "<svg></svg>", "kind": "svg"}).json()
    written = desk.client.post(f"/api/previews/{created['id']}/browser",
                               headers=AUTH).json()["path"]
    assert written.endswith(".html") and os.path.isfile(written)
    assert opened and opened[0].startswith("file:")
    assert desk.client.post("/api/previews/inconnu/browser", headers=AUTH).status_code == 404


# ── Envois de la page ───────────────────────────────────────────────────────


def test_pasted_files_keep_their_name_in_their_own_folder(desk):
    first = desk.client.post("/api/attachments/upload", headers=AUTH,
                             files={"file": ("notes.txt", b"a", "text/plain")}).json()
    second = desk.client.post("/api/attachments/upload", headers=AUTH,
                              files={"file": ("notes.txt", b"b", "text/plain")}).json()
    assert first["name"] == second["name"] == "notes.txt"
    assert first["path"] != second["path"]
    assert local_files.is_inside(first["path"], str(local_files.UPLOAD_DIR))
    wait_for(desk.events, "attachment.ready", 2)
