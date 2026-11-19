"""
Tests des chemins cliquables du chat (utils/path_links.py). Leur rendu dans la
fenêtre est vérifié par Vitest (features/chat/markdown/links.test.tsx).

Les chemins sont créés dans un dossier temporaire, avec des espaces comme
« OneDrive - Contoso SA » : c'est le cas réel qui rend la détection
difficile.
"""

import os
import subprocess
import sys
from pathlib import Path

import pytest

from utils import path_links
from utils.path_links import find_existing_paths, reveal_in_file_manager


@pytest.fixture(name="tree")
def _tree(tmp_path, monkeypatch):
    """Arborescence de test ; sous macOS/Linux, le dossier personnel y pointe."""
    if not path_links.IS_WINDOWS:
        # Hors Windows, seuls les chemins du dossier personnel sont sondés.
        monkeypatch.setenv("HOME", str(tmp_path))
    folder = tmp_path / "OneDrive - Contoso SA" / "My AI"
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


def test_reveal_on_linux_selects_the_file_through_the_desktop_service(tree, monkeypatch):
    """Linux : FileManager1.ShowItems (Nautilus, Dolphin, Nemo…) sélectionne le fichier,
    comme Electron et VS Code ; sans ce service ni dbus-send, xdg-open ouvre son dossier
    (il ne sait pas sélectionner). Un dossier s'ouvre toujours par xdg-open."""
    monkeypatch.setattr(path_links, "IS_WINDOWS", False)
    monkeypatch.setattr(path_links.sys, "platform", "linux")
    runs, opened = [], []
    answers = iter([0, 1])

    def run(command, **_kwargs):
        runs.append(command)
        return subprocess.CompletedProcess(command, next(answers))

    monkeypatch.setattr(path_links.subprocess, "run", run)
    monkeypatch.setattr(path_links.subprocess, "Popen", lambda cmd, *a, **k: opened.append(cmd))

    # Service présent : le fichier sélectionné, rien d'autre
    reveal_in_file_manager(tree["document"])
    assert runs[0][:2] == ["dbus-send", "--session"]
    assert "org.freedesktop.FileManager1.ShowItems" in runs[0]
    # URI encodée : l'espace de « rapport final.docx » ne coupe pas le tableau de dbus-send
    assert runs[0][-2] == "array:string:" + Path(tree["document"]).as_uri()
    assert " " not in runs[0][-2] and opened == []

    # Aucun gestionnaire ne le propose (code 1) : son dossier
    reveal_in_file_manager(tree["document"])
    assert opened == [["xdg-open", tree["folder"]]]

    def missing(*_args, **_kwargs):
        raise FileNotFoundError("dbus-send")

    monkeypatch.setattr(path_links.subprocess, "run", missing)
    # Pas de dbus-send : son dossier aussi ; un dossier : ouvert, sans le service
    reveal_in_file_manager(tree["document"])
    reveal_in_file_manager(tree["folder"])
    assert opened[1:] == [["xdg-open", tree["folder"]], ["xdg-open", tree["folder"]]]
    assert len(runs) == 2

