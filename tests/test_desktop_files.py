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
from test_chat_service import (  # pylint: disable=import-error
    FakeEngine, FakeFileProcessor, ask, wait_for)
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


def test_scheduled_reports_count_as_generated(tmp_path):
    config = {"scheduler.output_directory": str(tmp_path / "rapports")}
    roots = local_files.generated_roots(SimpleNamespace(get=lambda key, default=None: config.get(key, default)))
    assert str(tmp_path / "rapports") in roots
    assert str(local_files.PROJECT_ROOT / "outputs" / "scheduled") in local_files.generated_roots()


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


def test_download_never_overwrites_a_file_of_the_same_name(desk, monkeypatch):
    downloads = desk.tmp_path / "Téléchargements"
    monkeypatch.setattr(local_files, "downloads_dir", lambda: downloads)
    write(downloads / "calcul.py", "ancien")
    write(downloads / "calcul (1).py", "ancien aussi")
    generated = write(desk.outputs / "calcul.py", "print(2)")
    copied = desk.client.post("/api/files/download", json={"path": generated},
                              headers=AUTH).json()["path"]
    assert copied == str(downloads / "calcul (2).py")
    assert (downloads / "calcul (2).py").read_text(encoding="utf-8") == "print(2)"
    assert (downloads / "calcul.py").read_text(encoding="utf-8") == "ancien"
    assert (downloads / "calcul (1).py").read_text(encoding="utf-8") == "ancien aussi"


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


def test_artifact_page_gets_a_storage_before_its_own_scripts():
    shim = desktop_previews.STORAGE_SHIM
    full = "<!DOCTYPE html><html><head><title>t</title></head><body><script>x()</script></body></html>"
    page = desktop_previews.with_storage(full)
    assert page.startswith("<!DOCTYPE html><html><head>" + shim + "<title>")
    # Sans <head> : après <html>, ou après le doctype (jamais devant : mode quirks)
    assert desktop_previews.with_storage("<html><p>a</p></html>") == f"<html>{shim}<p>a</p></html>"
    assert desktop_previews.with_storage("<!doctype html><p>a</p>") == f"<!doctype html>{shim}<p>a</p>"
    assert desktop_previews.with_storage("<p>a</p>") == f"{shim}<p>a</p>"


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


def test_office_documents_go_to_the_window_viewer_on_request(desk, monkeypatch):
    # pylint: disable-next=import-outside-toplevel
    from interfaces import document_preview
    from interfaces.desktop import preview_handler  # pylint: disable=import-outside-toplevel

    monkeypatch.setattr(preview_handler, "supports_native_preview",
                        lambda path: path.endswith(".docx"))
    built = []
    monkeypatch.setattr(document_preview, "build_document_preview",
                        lambda path: built.append(path) or "<p>Rapport</p>")
    report = write(desk.outputs / "documents" / "rapport.docx", "docx")
    native = desk.client.post("/api/previews/document", headers=AUTH,
                              json={"path": report, "native": True}).json()
    # Visionneuse de la fenêtre : aucune page HTML produite d'avance
    assert native["kind"] == "native" and native["url"] == "" and built == []
    assert desk.server.previews.native_source(native["id"]) == report

    # Repli de la page (visionneuse en échec) : la page HTML, comme Tk
    html = desk.client.post("/api/previews/document", headers=AUTH,
                            json={"path": report}).json()
    assert html["kind"] == "document" and built == [report]
    assert desk.server.previews.native_source(html["id"]) is None
    assert desk.server.previews.native_source("inconnu") is None

    # Le navigateur du système reçoit la page HTML, sous la politique des documents
    monkeypatch.setattr(desktop_previews.webbrowser, "open", lambda _uri: True)
    written = desk.client.post(f"/api/previews/{native['id']}/browser", headers=AUTH).json()
    assert "Rapport" in open(written["path"], encoding="utf-8").read()
    preview = desk.server.previews.get(native["id"])
    assert preview.csp == desktop_previews.DOCUMENT_CSP

    # Format sans visionneuse : la page HTML même sur demande de la fenêtre
    note = write(desk.outputs / "documents" / "note.md", "# Note")
    assert desk.client.post("/api/previews/document", headers=AUTH,
                            json={"path": note, "native": True}).json()["kind"] == "document"


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


# ── Aperçu d'un fichier : texte, taille et date ────────────────────────────


def test_text_preview_reads_the_beginning_of_known_text_files(desk, monkeypatch):
    code = write(desk.outputs / "calcul.py", "print('é')")
    text = desk.client.post("/api/files/text", json={"path": code}, headers=AUTH).json()
    assert text == {"text": "print('é')", "truncated": False}
    # Fichier long : son début seulement, sans caractère coupé en deux
    monkeypatch.setattr(local_files, "TEXT_PREVIEW_MAX", 5)
    long = write(desk.outputs / "long.txt", "abcdé" * 10)
    assert local_files.read_text_preview(long, limit=5) == ("abcd", True)
    # UTF-16 (BOM) et Windows-1252 se lisent aussi
    utf16 = desk.outputs / "utf16.txt"
    utf16.write_bytes("é".encode("utf-16"))
    assert local_files.read_text_preview(str(utf16)) == ("é", False)
    latin = desk.outputs / "latin.txt"
    latin.write_bytes("été".encode("cp1252"))
    assert local_files.read_text_preview(str(latin)) == ("été", False)

    binary = desk.outputs / "image.bin"
    binary.write_bytes(b"\x89PNG\x00\x00data")
    refused = desk.client.post("/api/files/text", json={"path": str(binary)}, headers=AUTH)
    assert refused.status_code == 415
    assert refused.json()["detail"] == "Pas d'aperçu : ce fichier n'est pas du texte."
    # Fichier que la conversation ne connaît pas : rien n'en est lu
    secret = write(desk.tmp_path / "Documents" / "secret.txt", "mot de passe")
    assert desk.client.post("/api/files/text", json={"path": secret},
                            headers=AUTH).status_code == 404
    assert desk.client.post("/api/files/text", json={"path": secret}).status_code == 401


def test_file_info_gives_size_and_date_of_known_files_only(desk):
    report = write(desk.outputs / "rapport.md", "x" * 1234)
    info = desk.client.post("/api/files/info", json={"path": report}, headers=AUTH).json()
    assert info["size"] == 1234 and info["modified"].startswith("20")
    secret = write(desk.tmp_path / "Documents" / "secret.txt")
    assert desk.client.post("/api/files/info", json={"path": secret},
                            headers=AUTH).status_code == 404


def test_files_cited_in_an_answer_can_be_previewed(desk):
    """Un fichier cité par son chemin dans une réponse s'affiche dans le volet ; pas un autre."""
    cited = write(desk.tmp_path / "Documents" / "budget.csv", "a;b")
    other = write(desk.tmp_path / "Documents" / "autre.csv", "c;d")
    desk.chat.send("Où est le budget ?")
    wait_for(desk.events, "assistant.done", 1)
    assert desk.client.post("/api/files/text", json={"path": cited},
                            headers=AUTH).status_code == 404

    desk.chat._engine.script = [("token", f"Le budget est dans {cited}.")]  # pylint: disable=protected-access
    desk.chat.send("Et maintenant ?")
    done = wait_for(desk.events, "assistant.done", 2)[-1]["payload"]
    assert done["paths"] == [{"text": cited, "path": os.path.normpath(cited), "dir": False}]
    assert desk.client.post("/api/files/text", json={"path": cited},
                            headers=AUTH).json()["text"] == "a;b"
    links = desk.client.post("/api/files/links", headers=AUTH,
                             json={"paths": [cited, other]}).json()["links"]
    assert links[cited] and links[other] is None


def test_a_shown_markdown_file_shows_the_images_of_its_folder_only(desk):
    """README cité : son logo (une image de son dossier) s'affiche ; ni un autre
    fichier de ce dossier, ni une image hors de lui, ni pour un Markdown inconnu."""
    readme = write(desk.tmp_path / "Projet" / "README.md", "# Projet")
    logo = write(desk.tmp_path / "Projet" / "docs" / "logo.png", "png")
    secret = write(desk.tmp_path / "Projet" / "secret.txt", "mot de passe")
    outside = write(desk.tmp_path / "Ailleurs" / "photo.png", "png")
    desk.chat._engine.script = [("token", f"Le README est {readme}.")]  # pylint: disable=protected-access
    desk.chat.send("Où est le README ?")
    wait_for(desk.events, "assistant.done", 1)

    def links(paths, base):
        return desk.client.post("/api/files/links", headers=AUTH,
                                json={"paths": paths, "base": base}).json()["links"]

    found = links([logo, secret, outside], readme)
    assert found[logo] and found[secret] is None and found[outside] is None
    assert desk.client.get(found[logo]).text == "png"
    # Sans le Markdown affiché comme base, ou avec un Markdown que la page ne connaît pas
    assert links([logo], None)[logo] is None
    unknown = write(desk.tmp_path / "Autre" / "notes.md", "# Notes")
    write(desk.tmp_path / "Autre" / "image.png", "png")
    assert links([str(desk.tmp_path / "Autre" / "image.png")], unknown)[
        str(desk.tmp_path / "Autre" / "image.png")] is None
    # Une image ne sert pas de base : seulement un fichier Markdown
    assert links([logo], logo)[logo] is None


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
