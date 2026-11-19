"""
Fichiers qu'une réponse de la conversation Code cite ou nomme (relay/code_links.py)

La page Code de la fenêtre n'avait ni volet d'aperçu ni liens : un fichier
cité par le modèle (« src/app.ts », « shell.ts ») restait du texte. Elle les
rend cliquables comme le chat, chemins relatifs au workspace de VS Code
compris, puisque l'extension et le modèle n'emploient presque qu'eux. La vue
Code du téléphone reçoit les mêmes liens.
"""

import os

import pytest

from relay import code_links
from relay.code_links import conversation_files, link_transcript, reply_links, workspace_roots


@pytest.fixture(name="workspace")
def workspace_fixture(tmp_path):
    """Workspace de VS Code : src/app.ts, src/lib/shell.ts, README.md, package.json."""
    root = tmp_path / "ws"
    (root / "src" / "lib").mkdir(parents=True)
    for relative in ("README.md", "package.json", "src/app.ts", "src/lib/shell.ts"):
        (root / relative).write_text("x", encoding="utf-8")
    return root


def reply(*texts, tools=()):
    """Réponse de la transcription : ses passes de texte et ses appels d'outils."""
    parts = [{"kind": "text", "segment": i, "text": text} for i, text in enumerate(texts)]
    parts += [{"kind": "tool", "call_id": f"c{i}", "name": name, "input": {"path": path},
               "status": "completed"} for i, (name, path) in enumerate(tools)]
    return {"role": "assistant", "parts": parts, "text": "", "status": "done"}


def by_text(links):
    return {link["text"]: link for link in links}


def test_workspace_roots_reads_every_folder_in_order():
    info = "\n".join([
        "Workspace folders:",
        r"- My_AI (C:\Users\moi\My_AI)",
        r"- outils (old) (D:\outils)",
        r"- app (C:\Program Files (x86)\app)",
        "Active editor: src/app.ts (typescript)",
        "Platform: win32 (Windows path style)",
    ])
    roots = workspace_roots(info)
    if os.name == "nt":
        assert roots == [r"C:\Users\moi\My_AI", r"D:\outils", r"C:\Program Files (x86)\app"]
    assert workspace_roots("No workspace folder is open in VS Code.") == []
    assert workspace_roots("") == []


def test_relative_paths_bare_names_and_folders_become_links(workspace):
    text = ("J'ai lu `src/app.ts` et src\\lib\\shell.ts ; voir README.md, ./package.json "
            "et le dossier src/lib.")
    links = by_text(reply_links(reply(text), {}, [str(workspace)]))
    assert links["src/app.ts"]["path"] == str(workspace / "src" / "app.ts")
    assert links["src/app.ts"]["name"] is True and links["src/app.ts"]["dir"] is False
    assert links["src\\lib\\shell.ts"]["path"] == str(workspace / "src" / "lib" / "shell.ts")
    assert links["README.md"]["path"] == str(workspace / "README.md")
    assert links["./package.json"]["path"] == str(workspace / "package.json")
    assert links["src/lib"]["dir"] is True


def test_absolute_paths_tool_files_and_attachments_by_name(workspace, tmp_path):
    notes = tmp_path / "notes.txt"
    notes.write_text("x", encoding="utf-8")
    message = reply(f"Fait dans shell.ts, d'après notes.txt et {workspace / 'README.md'}.",
                    tools=[("edit_file", "src/lib/shell.ts"), ("list_dir", "src")])
    files = conversation_files([{"role": "user", "files": [
        {"name": "notes.txt", "path": str(notes)}]}])
    links = by_text(reply_links(message, files, [str(workspace)]))
    # Fichier d'un outil, nommé sans son chemin
    assert links["shell.ts"]["path"] == str(workspace / "src" / "lib" / "shell.ts")
    # Pièce jointe nommée
    assert links["notes.txt"]["path"] == str(notes)
    # Chemin absolu, comme dans le chat
    assert links[str(workspace / "README.md")]["path"] == str(workspace / "README.md")


def test_a_name_two_read_files_bear_stays_text(workspace):
    """Les outils ont lu deux fichiers du même nom (« utils.py » de tests/ et de src/) :
    leur nom seul n'en désigne aucun (vu avec le vrai modèle, il menait à l'un des
    deux), leurs chemins restent des liens. Un même fichier lu deux fois, par son
    chemin relatif puis absolu, reste un seul fichier."""
    (workspace / "tests").mkdir()
    (workspace / "tests" / "utils.py").write_text("x", encoding="utf-8")
    (workspace / "src" / "utils.py").write_text("x", encoding="utf-8")
    both = reply("Voici chaque fichier `utils.py` : **tests/utils.py** et **src/utils.py**.",
                 tools=[("read_file", "tests/utils.py"), ("read_file", "src/utils.py")])
    links = by_text(reply_links(both, {}, [str(workspace)]))
    assert "utils.py" not in links
    assert links["tests/utils.py"]["path"] == str(workspace / "tests" / "utils.py")
    assert links["src/utils.py"]["path"] == str(workspace / "src" / "utils.py")

    once = reply("Le formatage est dans `utils.py`.",
                 tools=[("read_file", "src/utils.py"), ("read_file", str(workspace / "src" / "utils.py"))])
    assert by_text(reply_links(once, {}, [str(workspace)]))["utils.py"]["path"] \
        == str(workspace / "src" / "utils.py")


def test_nothing_from_code_blocks_urls_other_paths_or_outside_the_workspace(workspace, tmp_path):
    (tmp_path / "secret.txt").write_text("x", encoding="utf-8")
    text = "\n".join([
        "Le site https://example.com/src/app.ts, le chemin web/src/app.ts,",
        "le module core.chat_service, la version 1.2.3, et ../secret.txt.",
        "```ts",
        "import { x } from 'src/app.ts';",
        "```",
    ])
    assert reply_links(reply(text), {}, [str(workspace)]) == []
    # Un fichier qui n'existe pas n'est jamais un lien
    assert reply_links(reply("Voir src/absent.ts."), {}, [str(workspace)]) == []


def test_without_workspace_only_absolute_paths_and_names(workspace):
    message = reply(f"Voir src/app.ts et {workspace / 'README.md'}.")
    links = reply_links(message, {}, [])
    assert [link["text"] for link in links] == [str(workspace / "README.md")]


def test_network_workspace_is_never_probed(workspace, monkeypatch):
    """Un dossier sur un partage réseau déconnecté bloquerait : jamais sondé."""
    monkeypatch.setattr(code_links, "safe_to_probe", lambda _path: False)
    assert reply_links(reply("Voir src/app.ts."), {}, [str(workspace)]) == []


def test_links_are_capped(workspace):
    for i in range(code_links.MAX_LINKS + 5):
        (workspace / "src" / f"f{i}.ts").write_text("x", encoding="utf-8")
    text = " ".join(f"src/f{i}.ts" for i in range(code_links.MAX_LINKS + 5))
    assert len(reply_links(reply(text), {}, [str(workspace)])) == code_links.MAX_LINKS


def test_a_read_transcript_links_its_finished_replies(workspace, tmp_path):
    """Lecture de la conversation (fenêtre, téléphone) : les réponses terminées ou
    arrêtées reçoivent leurs liens, cherchés dans les dossiers gardés avec elles
    (sinon ceux de VS Code ouvert) ; ni une réponse en cours ni une erreur. Les
    dossiers gardés ne quittent pas le serveur."""
    other = tmp_path / "autre"
    other.mkdir()
    (other / "main.py").write_text("x", encoding="utf-8")
    error = reply("Voir README.md.")
    error["status"] = "error"
    streaming = reply("Voir README.md.")
    streaming["status"] = "streaming"
    stopped = reply("Voir main.py.")
    stopped["status"] = "stopped"
    messages = [{"role": "user", "text": "Regarde", "files": []},
                {**reply("Voir src/app.ts."), "roots": [str(workspace)]},
                {**error, "roots": [str(workspace)]}, streaming, stopped]

    found = link_transcript(messages, [str(other)], "links")

    assert [link["path"] for link in found] == [str(workspace / "src" / "app.ts"),
                                                str(other / "main.py")]
    assert [link["text"] for link in messages[1]["links"]] == ["src/app.ts"]
    assert [link["text"] for link in messages[4]["links"]] == ["main.py"]
    assert "links" not in messages[2] and "links" not in messages[3]
    assert all("roots" not in message for message in messages)
