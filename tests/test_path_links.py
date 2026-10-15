"""
Tests des chemins cliquables du chat (utils/path_links.py). Leur rendu dans la
fenêtre est vérifié par Vitest (features/chat/markdown/links.test.tsx).

Les chemins sont créés dans un dossier temporaire, avec des espaces comme
« OneDrive - Pierre Fabre SA » : c'est le cas réel qui rend la détection
difficile.
"""

import os
import sys

import pytest

from utils import path_links
from utils.path_links import find_existing_paths, reveal_in_file_manager


@pytest.fixture(name="tree")
def _tree(tmp_path, monkeypatch):
    """Arborescence de test ; sous macOS/Linux, le dossier personnel y pointe."""
    if not path_links.IS_WINDOWS:
        # Hors Windows, seuls les chemins du dossier personnel sont sondés.
        monkeypatch.setenv("HOME", str(tmp_path))
    folder = tmp_path / "OneDrive - Pierre Fabre SA" / "My AI"
    folder.mkdir(parents=True)
    document = folder / "rapport final.docx"
    document.write_bytes(b"x")
    return {"folder": str(folder), "document": str(document)}


# ── Détection ──────────────────────────────────────────────────────────────


def test_path_with_spaces_is_found_whole(tree):
    text = f"Le fichier a été créé dans le dossier complet suivant : {tree['document']}"
    matches = find_existing_paths(text)
    assert [m.text for m in matches] == [tree["document"]]
    assert matches[0].start == text.index(tree["document"])


@pytest.mark.parametrize("wrapper", ["{}.", "`{}`", "({})", "« {} »", "{}, puis la suite"])
def test_surrounding_punctuation_is_excluded(tree, wrapper):
    matches = find_existing_paths("Voir " + wrapper.format(tree["document"]))
    assert [m.text for m in matches] == [tree["document"]]


def test_sentence_after_the_path_is_excluded(tree):
    matches = find_existing_paths(f"{tree['document']} est prêt à être ouvert.")
    assert [m.text for m in matches] == [tree["document"]]


def test_folder_is_found(tree):
    assert [m.text for m in find_existing_paths(f"Dossier : {tree['folder']}")] == [tree["folder"]]


def test_several_paths_in_one_sentence(tree):
    text = f"Voir {tree['document']} et {tree['folder']}."
    assert [m.text for m in find_existing_paths(text)] == [tree["document"], tree["folder"]]


def test_invented_path_is_not_linked(tree):
    fake = os.path.join(tree["folder"], "fantome.docx")
    assert find_existing_paths(f"Le fichier {fake} est prêt.") == []


def test_urls_are_not_paths():
    assert find_existing_paths("Voir https://example.com/docs/page et file:///C:/x") == []


def test_path_does_not_cross_lines(tree):
    text = f"{tree['folder']}\nsuite sur une autre ligne"
    assert [m.text for m in find_existing_paths(text)] == [tree["folder"]]


def test_empty_text():
    assert find_existing_paths("") == []
    assert find_existing_paths("Aucun chemin ici.") == []


@pytest.mark.skipif(not path_links.IS_WINDOWS, reason="lecteurs Windows")
def test_network_drives_are_never_probed(monkeypatch):
    """Un lecteur réseau déconnecté pourrait figer l'interface plusieurs secondes."""
    probed = []
    monkeypatch.setattr(path_links.os.path, "exists", lambda p: probed.append(p) or True)
    # UNC : jamais sondé
    assert find_existing_paths(r"Voir \\serveur\partage\rapport.docx") == []
    assert probed == []


# ── Ouverture de l'emplacement ─────────────────────────────────────────────


def test_reveal_selects_a_file_and_opens_a_folder(tree, monkeypatch):
    calls = []
    monkeypatch.setattr(path_links.subprocess, "Popen", lambda cmd, *a, **k: calls.append(cmd))
    if path_links.IS_WINDOWS:
        monkeypatch.setattr(path_links.os, "startfile", lambda p: calls.append(("startfile", p)))

    reveal_in_file_manager(tree["document"])
    reveal_in_file_manager(tree["folder"])

    if path_links.IS_WINDOWS:
        assert calls[0] == f'explorer /select,"{tree["document"]}"'
        assert calls[1] == ("startfile", tree["folder"])
    elif sys.platform == "darwin":
        assert calls[0] == ["open", "-R", tree["document"]]
        assert calls[1] == ["open", tree["folder"]]

