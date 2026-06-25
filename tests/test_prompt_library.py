"""
Tests de la bibliothèque de prompts / slash commands (core/prompt_library.py).

Opérations RÉELLES (pas de mock) : persistance JSON sur un fichier temporaire,
relue pour vérifier la durabilité.
"""

import json
import os
import shutil
import tempfile

import pytest

from core.prompt_library import PromptLibrary


class TestSeedAndPersistence:

    @pytest.fixture
    def tmp_path_json(self):
        tmp = tempfile.mkdtemp()
        try:
            yield os.path.join(tmp, "prompt_templates.json")
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_defaults_seeded_on_first_run(self, tmp_path_json):
        lib = PromptLibrary(path=tmp_path_json)
        assert os.path.exists(tmp_path_json)
        commands = {t["command"] for t in lib.list()}
        assert {"résume", "traduis", "explique"} <= commands
        assert all(t["builtin"] for t in lib.list())

    def test_persisted_json_is_valid_list(self, tmp_path_json):
        PromptLibrary(path=tmp_path_json)
        with open(tmp_path_json, encoding="utf-8") as fh:
            data = json.load(fh)
        assert isinstance(data, list) and len(data) >= 6
        assert all({"id", "command", "title", "content"} <= set(t) for t in data)

    def test_empty_list_is_respected_no_reseed(self, tmp_path_json):
        # Un fichier contenant une liste vide = l'utilisateur a tout supprimé.
        with open(tmp_path_json, "w", encoding="utf-8") as fh:
            json.dump([], fh)
        lib = PromptLibrary(path=tmp_path_json)
        assert lib.list() == []

    def test_unreadable_file_falls_back_to_defaults(self, tmp_path_json):
        with open(tmp_path_json, "w", encoding="utf-8") as fh:
            fh.write("{ ceci n'est pas du JSON")
        lib = PromptLibrary(path=tmp_path_json)
        assert len(lib.list()) >= 6


class TestCRUD:

    @pytest.fixture
    def lib(self):
        tmp = tempfile.mkdtemp()
        try:
            yield PromptLibrary(path=os.path.join(tmp, "p.json"))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_add_and_reload(self, lib):
        created = lib.add(
            title="Mail pro", content="Rédige un email à {destinataire}.",
            command="mail", description="Email professionnel",
        )
        assert created["command"] == "mail"
        reloaded = PromptLibrary(path=lib._path)
        assert any(t["command"] == "mail" for t in reloaded.list())

    def test_add_duplicate_command_raises(self, lib):
        lib.add(title="A", content="x", command="dup")
        with pytest.raises(ValueError):
            lib.add(title="B", content="y", command="/dup")  # même cmd, avec slash

    def test_update_fields(self, lib):
        created = lib.add(title="T", content="ancien", command="c")
        updated = lib.update(created["id"], content="nouveau", title="T2")
        assert updated["content"] == "nouveau" and updated["title"] == "T2"
        assert lib.get(created["id"])["content"] == "nouveau"

    def test_update_to_clashing_command_raises(self, lib):
        a = lib.add(title="A", content="x", command="alpha")
        lib.add(title="B", content="y", command="beta")
        with pytest.raises(ValueError):
            lib.update(a["id"], command="beta")

    def test_update_missing_returns_none(self, lib):
        assert lib.update("inexistant", title="x") is None

    def test_delete(self, lib):
        created = lib.add(title="X", content="z", command="todel")
        assert lib.delete(created["id"]) is True
        assert lib.get(created["id"]) is None
        assert lib.delete(created["id"]) is False
        # La suppression est durable.
        reloaded = PromptLibrary(path=lib._path)
        assert all(t["command"] != "todel" for t in reloaded.list())


class TestMatchingAndPlaceholders:

    @pytest.fixture
    def lib(self):
        tmp = tempfile.mkdtemp()
        try:
            yield PromptLibrary(path=os.path.join(tmp, "p.json"))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_find_by_command_accent_insensitive(self, lib):
        assert lib.find_by_command("resume") is not None      # sans accent
        assert lib.find_by_command("/résume") is not None      # avec slash + accent
        assert lib.find_by_command("RESUME") is not None       # casse différente

    def test_search_prefix(self, lib):
        results = lib.search("re")  # « résume », « reformule »
        cmds = {t["command"] for t in results}
        assert "résume" in cmds and "reformule" in cmds
        assert "traduis" not in cmds

    def test_search_empty_prefix_returns_all_commands(self, lib):
        results = lib.search("/")
        assert len(results) == len([t for t in lib.list() if t["command"]])

    def test_extract_placeholders_ordered_unique(self):
        ph = PromptLibrary.extract_placeholders(
            "Traduis {texte} en {langue} puis re-traduis {texte}."
        )
        assert ph == ["texte", "langue"]

    def test_extract_placeholders_none(self):
        assert PromptLibrary.extract_placeholders("Aucun placeholder ici.") == []


class TestExpansion:

    @pytest.fixture
    def lib(self):
        tmp = tempfile.mkdtemp()
        try:
            yield PromptLibrary(path=os.path.join(tmp, "p.json"))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_expand_injects_arguments(self, lib):
        out = lib.expand("/code un jeu de morpion")
        assert out is not None
        assert "un jeu de morpion" in out          # texte saisi injecté
        assert "{arguments}" not in out            # placeholder remplacé
        assert out != "/code un jeu de morpion"    # prompt réellement étendu
        assert len(out) > len("/code un jeu de morpion")

    def test_expand_accent_insensitive_command(self, lib):
        assert lib.expand("/resume ce paragraphe") is not None  # /résume

    def test_expand_unknown_command_returns_none(self, lib):
        assert lib.expand("/inconnu blabla") is None

    def test_expand_non_slash_returns_none(self, lib):
        assert lib.expand("bonjour le monde") is None
        assert lib.expand("") is None

    def test_render_appends_when_no_arguments_placeholder(self, lib):
        created = lib.add(title="Sans ph", content="Fais ceci.", command="x")
        out = lib.expand("/x mon contenu")
        assert out == "Fais ceci.\n\nmon contenu"
        # Et sans arguments, on renvoie le contenu tel quel.
        assert lib.render(lib.get(created["id"]), "") == "Fais ceci."

    def test_expand_command_without_args(self, lib):
        out = lib.expand("/résume")
        assert out is not None and "{arguments}" not in out


class TestBuiltinMigration:

    def test_old_builtin_content_is_migrated(self):
        tmp = tempfile.mkdtemp()
        try:
            path = os.path.join(tmp, "p.json")
            # Ancien format persisté (avant le passage à {arguments}).
            old = [{
                "id": "code", "command": "code", "title": "Ancien",
                "description": "old", "content": "Écris du code en {langage}.",
                "builtin": True,
                "created_at": "2020-01-01T00:00:00", "updated_at": "2020-01-01T00:00:00",
            }]
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(old, fh)
            lib = PromptLibrary(path=path)
            code = lib.find_by_command("code")
            assert "{arguments}" in code["content"]   # migré vers le nouveau format
            assert "{langage}" not in code["content"]
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_user_edited_builtin_is_not_overwritten(self):
        tmp = tempfile.mkdtemp()
        try:
            path = os.path.join(tmp, "p.json")
            edited = [{
                "id": "code", "command": "code", "title": "Mon code",
                "description": "perso", "content": "MON CONTENU PERSO",
                "builtin": False,  # édité → personnel
                "created_at": "2020-01-01T00:00:00", "updated_at": "2020-01-01T00:00:00",
            }]
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(edited, fh)
            lib = PromptLibrary(path=path)
            assert lib.find_by_command("code")["content"] == "MON CONTENU PERSO"
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
