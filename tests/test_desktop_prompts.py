"""
Tests des Prompts de la fenêtre (interfaces/desktop/prompts.py, api_prompts.py)

Vraie PromptLibrary, sur un fichier JSON temporaire : contrôles du formulaire
Tk (prompts_panel.py), commande déjà prise, routes et notifications.
"""

from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from core.prompt_library import PromptLibrary
from interfaces.desktop.events import EventBus
from interfaces.desktop.prompts import PromptsError, PromptsService
from interfaces.desktop.server import DesktopServer
from test_desktop_server import AUTH, BASE, PORT, FakeApp  # pylint: disable=import-error


@pytest.fixture(name="prompts")
def prompts_fixture(tmp_path):
    engine = SimpleNamespace(prompt_library=PromptLibrary(path=str(tmp_path / "prompts.json")))
    return SimpleNamespace(library=engine.prompt_library,
                           service=PromptsService(lambda: engine))


def test_defaults_are_listed_with_their_commands(prompts):
    listed = prompts.service.list()
    assert {"code", "résume", "traduis"} <= {item["command"] for item in listed}
    assert all(item["builtin"] for item in listed)


def test_the_form_checks_of_tk(prompts):
    with pytest.raises(PromptsError, match="au moins un nom ou une commande"):
        prompts.service.save(None, {"title": " ", "command": "", "content": "x"})
    with pytest.raises(PromptsError, match="Le contenu ne peut pas être vide"):
        prompts.service.save(None, {"title": "Relecture", "content": "  \n "})
    with pytest.raises(PromptsError, match="La commande /code existe déjà"):
        prompts.service.save(None, {"command": "/code", "content": "Autre"})


def test_create_edit_and_delete(prompts):
    created = prompts.service.save(None, {"command": "relis", "description": "Relecture",
                                          "content": "Relis : {arguments}\n"})
    # Sans nom : la commande sert de nom, comme dans Tk
    assert created["title"] == "relis" and created["content"] == "Relis : {arguments}"
    assert prompts.library.find_by_command("relis")["id"] == created["id"]

    edited = prompts.service.save(created["id"], {"title": "Relecture", "command": "relecture",
                                                  "content": "Relis avec soin : {arguments}"})
    assert edited["command"] == "relecture" and prompts.library.find_by_command("relis") is None

    builtin = prompts.service.save("code", {"title": "Code", "command": "code",
                                            "content": "Écris le code : {arguments}"})
    assert builtin["builtin"] is False  # édité : il devient personnel (PromptLibrary)

    prompts.service.delete(created["id"])
    with pytest.raises(PromptsError, match="introuvable"):
        prompts.service.delete(created["id"])
    with pytest.raises(PromptsError, match="introuvable"):
        prompts.service.save("absent", {"title": "x", "content": "y"})


def test_prompt_routes(prompts):
    bus = EventBus()
    events = []
    bus.subscribe(events.append)
    app = FakeApp(None, bus)
    app.prompts = prompts.service
    app.notify = lambda level, message: bus.publish("notification",
                                                    {"level": level, "message": message})
    server = DesktopServer(app)
    server.port = PORT
    client = TestClient(server.fastapi, base_url=BASE)

    created = client.post("/api/prompts", headers=AUTH,
                          json={"title": "Plan", "command": "plan", "content": "Plan : {arguments}"})
    assert created.status_code == 200 and created.json()["command"] == "plan"
    prompt_id = created.json()["id"]
    assert any(item["id"] == prompt_id
               for item in client.get("/api/prompts", headers=AUTH).json()["prompts"])
    assert client.put(f"/api/prompts/{prompt_id}", headers=AUTH,
                      json={"title": "Plan détaillé", "command": "plan",
                            "content": "Plan détaillé : {arguments}"}).status_code == 200
    clash = client.put(f"/api/prompts/{prompt_id}", headers=AUTH,
                       json={"title": "Plan", "command": "code", "content": "x"})
    assert clash.status_code == 409 and clash.json()["detail"] == "La commande /code existe déjà."
    assert client.delete(f"/api/prompts/{prompt_id}", headers=AUTH).status_code == 200
    # La commande supprimée ne s'affiche plus dans l'autocomplétion
    app.engine = SimpleNamespace(prompt_library=prompts.library)
    commands = client.get("/api/prompts/commands?prefix=pl", headers=AUTH).json()["commands"]
    assert commands == []
    messages = [e["payload"]["message"] for e in events if e["type"] == "notification"]
    assert messages == ["✅ Prompt créé", "✅ Prompt enregistré", "🗑️ Prompt supprimé"]

    prompts.service._engine = lambda: None  # pylint: disable=protected-access
    gone = client.get("/api/prompts", headers=AUTH)
    assert gone.status_code == 409 and gone.json()["detail"] == (
        "Bibliothèque de prompts indisponible.")
