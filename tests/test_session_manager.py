"""
Tests du gestionnaire de sessions (core/session_manager.py) : un identifiant
de session ne mène jamais hors du dossier des workspaces

Les routes /api/sessions/{id} (chargement, renommage, suppression)
transmettent le segment d'URL tel quel, et DELETE /api/sessions/.. effaçait le
dossier parent de data/workspaces, soit tout data/ dans l'appli. Le TestClient de FastAPI réduit « .. » avant l'envoi,
mais pas %2E%2E ni %5C, que le serveur décode : les routes se testent avec
ceux-là, et à la main avec curl --path-as-is contre
tools/interface_web/demo_server.py, jamais contre la vraie appli.

Les workspaces sont rangés sous tmp_path/appli/data/workspaces, avec des
leurres à chaque niveau : même sans la garde, aucun identifiant testé ne
pourrait toucher à un fichier hors de tmp_path.
"""

import json
import os
import re
import shutil
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from core.chat_service import ChatError, ChatService
from core.i18n import tr
from core.session_manager import SessionManager, workspace_dir
from interfaces.desktop.events import EventBus
from interfaces.desktop.server import DesktopServer
from test_chat_service import FakeEngine, FakeFileProcessor  # pylint: disable=import-error
from test_desktop_server import AUTH, BASE, PORT, FakeApp  # pylint: disable=import-error

# Identifiants qui mèneraient ailleurs que dans un dossier de workspace : le
# parent, le dossier des workspaces lui-même, un sous-dossier, un chemin absolu
# (« {ailleurs} », un leurre hors de appli/), un lecteur seul (« {lecteur} »,
# celui de tmp_path : collé au dossier des workspaces, il désigne ce dossier),
# un caractère de contrôle. Sous Windows, « ... » et « .. » suivi d'une espace
# désignent aussi le dossier des workspaces (points et espaces finaux retirés).
BAD_IDS = ["..", ".", "", "a/b", "a\\b", "{ailleurs}", "../..", "..\\..", "{lecteur}",
           "x\ny", "...", ".. "]
WINDOWS_ONLY = ("...", ".. ")

LURE = {"id": "leurre", "name": "Leurre", "last_modified": "2026-01-01T00:00:00",
        "message_count": 1}


def _lure(folder: Path) -> None:
    """Ce qu'une méthode lirait, réécrirait ou effacerait si l'identifiant la menait ici."""
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "metadata.json").write_text(json.dumps(LURE), encoding="utf-8")
    (folder / "state.json").write_text(
        json.dumps({"conversation_history": [{"text": "leurre"}], "metadata": LURE}),
        encoding="utf-8")
    (folder / "temoin.txt").write_text("doit survivre", encoding="utf-8")


def _snapshot(root: Path) -> dict:
    """Tous les dossiers et fichiers sous root, avec le contenu des fichiers."""
    return {path.relative_to(root).as_posix(): path.read_bytes() if path.is_file() else None
            for path in sorted(root.rglob("*"))}


def _expand(raw_id: str, tree) -> str:
    """Identifiant concret : « {ailleurs} » et « {lecteur} » dépendent de tmp_path."""
    return raw_id.format(ailleurs=tree.elsewhere, lecteur=tree.tmp_path.drive or "C:")


def _link(link: Path, target: Path) -> None:
    """Lien vers un dossier : symbolique, sinon jonction (Windows, sans droit
    particulier), sinon le test est sauté."""
    try:
        os.symlink(target, link, target_is_directory=True)
        return
    except OSError:
        pass
    try:
        import _winapi  # pylint: disable=import-outside-toplevel
        _winapi.CreateJunction(str(target), str(link))
    except (ImportError, AttributeError, OSError):
        pytest.skip("ni lien symbolique ni jonction possible ici")


@pytest.fixture(name="tree")
def tree_fixture(tmp_path):
    """appli/data/workspaces avec un vrai workspace, et des leurres autour."""
    workspaces = tmp_path / "appli" / "data" / "workspaces"
    manager = SessionManager(str(workspaces))
    workspace_id = manager.create_workspace("Projet gardé")
    assert manager.save_workspace(workspace_id, {"conversation_history": [{"text": "Bonjour"}]})
    elsewhere = tmp_path / "ailleurs"
    for folder in (workspaces.parent.parent, workspaces.parent, workspaces,
                   workspaces / "a" / "b", elsewhere):
        _lure(folder)
    return SimpleNamespace(tmp_path=tmp_path, workspaces=workspaces, manager=manager,
                           workspace_id=workspace_id, elsewhere=elsewhere)


# ── SessionManager ──────────────────────────────────────────────────────────


def test_delete_dotdot_deletes_nothing(tree):
    """Le cas constaté : delete_workspace("..") effaçait data/ en entier."""
    assert tree.manager.delete_workspace("..") is False
    assert (tree.workspaces.parent / "temoin.txt").read_text(encoding="utf-8") == "doit survivre"
    state = tree.manager.load_workspace(tree.workspace_id)
    assert state["conversation_history"] == [{"text": "Bonjour"}]


@pytest.mark.parametrize("raw_id", BAD_IDS)
def test_refused_id_reads_and_writes_nothing(tree, raw_id):
    """Chaque méthode répond comme pour un workspace introuvable, sans toucher au disque."""
    workspace_id = _expand(raw_id, tree)
    manager = tree.manager
    before = _snapshot(tree.tmp_path)

    assert manager.load_workspace(workspace_id) is None
    assert manager.save_workspace(workspace_id, {"conversation_history": [{"text": "écrasé"}]}) is False
    assert manager.auto_save(workspace_id, {"conversation_history": []}) is False
    assert manager.rename_workspace(workspace_id, "Renommé") is False
    with pytest.raises(ValueError):
        manager.set_current_workspace(workspace_id)
    assert manager.get_current_workspace() is None
    assert manager.delete_workspace(workspace_id) is False

    assert _snapshot(tree.tmp_path) == before
    assert [workspace["id"] for workspace in manager.list_workspaces()] == [tree.workspace_id]


@pytest.mark.parametrize("raw_id", [raw for raw in BAD_IDS if raw not in WINDOWS_ONLY])
def test_workspace_dir_refuses_anything_but_a_plain_folder_name(tree, raw_id):
    assert workspace_dir(tree.workspaces, _expand(raw_id, tree)) is None


@pytest.mark.skipif(os.name != "nt", reason="seul Windows retire points et espaces finaux")
@pytest.mark.parametrize("raw_id", ["...", "....", ".. ", " ..", ". ."])
def test_windows_dots_and_spaces_naming_the_workspaces_folder_are_refused(tree, raw_id):
    assert workspace_dir(tree.workspaces, raw_id) is None


def test_link_to_another_folder_is_refused(tree):
    """Un lien sous le dossier des workspaces qui mène ailleurs est écarté :
    save et rename écriraient à travers lui."""
    _link(tree.workspaces / "lien", tree.elsewhere)
    manager = tree.manager
    before = _snapshot(tree.tmp_path)

    assert workspace_dir(tree.workspaces, "lien") is None
    assert manager.load_workspace("lien") is None
    assert manager.save_workspace("lien", {"conversation_history": []}) is False
    assert manager.rename_workspace("lien", "Renommé") is False
    assert manager.delete_workspace("lien") is False

    assert _snapshot(tree.tmp_path) == before


def test_legitimate_ids_are_accepted(tree):
    """Aucun identifiant légitime n'est refusé : ceux de create_workspace, quel
    que soit le nom, et les noms de dossier simples d'un workspace copié à la main."""
    manager = tree.manager
    created = [manager.create_workspace(name) for name in
               ("Projet API REST", "Éléphant & café !", "123", "a.b_c", "x" * 48)]
    copied = ["Mon projet", "ws1", "Copie_de_projet-1a2b3c4d", "projet.v2", "été"]
    for folder in copied:
        shutil.copytree(tree.workspaces / tree.workspace_id, tree.workspaces / folder)

    for workspace_id in created + copied:
        assert workspace_dir(tree.workspaces, workspace_id) == tree.workspaces / workspace_id
        assert manager.save_workspace(workspace_id, {"conversation_history": [{"text": "salut"}]})
        assert manager.load_workspace(workspace_id)["conversation_history"] == [{"text": "salut"}]
        assert manager.rename_workspace(workspace_id, "Renommé")
        manager.set_current_workspace(workspace_id)
        assert manager.get_current_workspace() == workspace_id
        assert manager.delete_workspace(workspace_id)
        assert not (tree.workspaces / workspace_id).exists()
    assert manager.get_current_workspace() is None


# ── Service de chat et routes du serveur local ──────────────────────────────


@pytest.fixture(name="server")
def server_fixture(tree):
    """Serveur local sur un vrai service de chat, avec les workspaces de `tree`."""
    engine = FakeEngine(tree.workspaces)
    bus = EventBus()
    events = []
    bus.subscribe(events.append)
    chat = ChatService(engine, bus.publish, file_processor=FakeFileProcessor(),
                       ui_connected=lambda: True)
    chat.start()
    desktop = DesktopServer(FakeApp(chat, bus, engine=engine))
    desktop.port = PORT
    yield SimpleNamespace(client=TestClient(desktop.fastapi, base_url=BASE), chat=chat,
                          events=events, tree=tree)
    chat.close()


@pytest.mark.parametrize("raw_id", BAD_IDS)
def test_chat_service_answers_as_for_an_unknown_session(server, raw_id):
    """rename_session (PUT .../name), load_session et delete_session : la réponse
    d'une session inconnue, sans événement de session ni écriture."""
    workspace_id = _expand(raw_id, server.tree)
    chat = server.chat
    before = _snapshot(server.tree.tmp_path)
    server.events.clear()

    with pytest.raises(ChatError, match=re.escape(tr("chat.sessionNotFound"))):
        chat.rename_session(workspace_id, "Nom")
    with pytest.raises(ChatError, match="Session introuvable"):
        chat.load_session(workspace_id)
    assert chat.delete_session(workspace_id) is False

    session_events = ("sessions.changed", "conversation.renamed", "conversation.loaded")
    assert not [event for event in server.events if event["type"] in session_events]
    assert _snapshot(server.tree.tmp_path) == before


# Segments que le TestClient envoie tels quels (il ne réduit que « .. » et « . »
# littéraux), décodés par le serveur en .., ., ..\.., a\b et lecteur seul
ENCODED_IDS = ["%2E%2E", "%2e%2e", "%2E", "..%5C..", "a%5Cb", "{lecteur}%3A"]


@pytest.mark.parametrize("segment", ENCODED_IDS)
def test_routes_answer_as_for_an_unknown_session(server, segment):
    """409 au chargement et au renommage, {"deleted": false} à la suppression,
    et rien ne bouge."""
    client = server.client
    segment = segment.format(lecteur=(server.tree.tmp_path.drive or "C:").rstrip(":"))
    before = _snapshot(server.tree.tmp_path)
    unknown = "/api/sessions/inconnue-1a2b3c4d"
    unknown_load = client.post(f"{unknown}/load", headers=AUTH)
    unknown_rename = client.put(f"{unknown}/name", json={"name": "Nom"}, headers=AUTH)
    unknown_delete = client.delete(unknown, headers=AUTH)

    load = client.post(f"/api/sessions/{segment}/load", headers=AUTH)
    rename = client.put(f"/api/sessions/{segment}/name", json={"name": "Nom"}, headers=AUTH)
    delete = client.delete(f"/api/sessions/{segment}", headers=AUTH)

    assert load.status_code == unknown_load.status_code == 409
    assert load.json() == unknown_load.json()
    assert rename.status_code == unknown_rename.status_code == 409
    assert rename.json() == unknown_rename.json()
    assert delete.status_code == unknown_delete.status_code == 200
    assert delete.json() == unknown_delete.json() == {"deleted": False}
    assert _snapshot(server.tree.tmp_path) == before


def test_a_real_session_is_still_renamed_and_deleted_over_rest(server):
    workspace_id = server.tree.workspace_id
    url = f"/api/sessions/{workspace_id}"
    rename = server.client.put(f"{url}/name", json={"name": "Nouveau nom"}, headers=AUTH)
    assert rename.status_code == 200 and rename.json() == {"name": "Nouveau nom"}
    assert server.tree.manager.load_workspace(workspace_id)["metadata"]["name"] == "Nouveau nom"
    assert server.client.delete(url, headers=AUTH).json() == {"deleted": True}
    assert not (server.tree.workspaces / workspace_id).exists()
