"""
Tests de l'embarquement Edge du volet d'aperçu (interfaces/gui/_edge_embed.py).

Régressions de trois défauts observés en usage réel, tous liés au fait que le
``msedge.exe`` lancé n'est qu'un **lanceur** qui démarre le vrai navigateur
puis se termine aussitôt :

1. ``close()`` visait le lanceur, déjà mort : l'instance Edge (≈15 processus)
   survivait, les fenêtres s'empilaient dans le volet à chaque réouverture ;
2. la capture prenait « n'importe quelle nouvelle fenêtre Chromium » : une
   fenêtre de VS Code, Teams ou du navigateur pouvait être embarquée à la
   place de la nôtre, qui restait flottante avec sa barre de titre ;
3. le profil temporaire était supprimé sous un Edge encore vivant.

Les tests d'intégration lancent un VRAI Edge : ils ne tournent que sous
Windows, avec Edge et psutil disponibles.
"""

import os
import subprocess
import tempfile
import time

import pytest

from interfaces.gui import _edge_embed
from interfaces.gui._edge_embed import (
    EdgeEmbed,
    _list_chrome_windows,
    _profile_processes,
    _sweep_stale_profiles,
    find_edge,
)

_EDGE_READY = (
    _edge_embed.IS_WINDOWS
    and find_edge() is not None
    and _edge_embed.psutil is not None
)
requires_edge = pytest.mark.skipif(
    not _EDGE_READY, reason="Windows + Microsoft Edge + psutil requis"
)


class _FakeParent:
    """Widget minimal : start() ne lit que l'identifiant de fenêtre du parent."""

    def winfo_id(self):
        return 0


def _wait_for(predicate, timeout=10.0, step=0.2):
    """Attend qu'un prédicat devienne vrai ; retourne sa dernière valeur."""
    deadline = time.time() + timeout
    value = predicate()
    while not value and time.time() < deadline:
        time.sleep(step)
        value = predicate()
    return value


@pytest.fixture(name="page")
def _page(tmp_path):
    path = tmp_path / "apercu.html"
    path.write_text("<html><body><h1>Aperçu</h1></body></html>", encoding="utf-8")
    return path


def _new_windows_of(embed):
    user32, enum_proc, ctypes, _ = embed._win32
    return [
        hwnd
        for hwnd in _list_chrome_windows(user32, enum_proc, ctypes) - embed._before
        if embed._is_ours(hwnd)
    ]


# ── 1. close() termine réellement l'instance ──────────────────────────────


@requires_edge
def test_close_terminates_the_real_browser_not_just_the_launcher(page):
    embed = EdgeEmbed()
    assert embed.start(str(page), _FakeParent(), 400, 300)
    profile = embed._profile_dir
    try:
        assert _wait_for(lambda: _profile_processes(profile)), "Edge n'a pas démarré"
        # Le processus lancé est un lanceur : il meurt, le navigateur vit.
        _wait_for(lambda: embed._proc.poll() is not None, timeout=5)
        assert _profile_processes(profile), "le navigateur réel doit tourner"
    finally:
        embed.close()

    assert not _profile_processes(profile), "des processus Edge ont survécu à close()"
    assert not os.path.exists(profile), "le profil temporaire n'a pas été supprimé"


@requires_edge
def test_close_after_attach_identification_kills_the_whole_tree(page):
    embed = EdgeEmbed()
    assert embed.start(str(page), _FakeParent(), 400, 300)
    profile = embed._profile_dir
    try:
        windows = _wait_for(lambda: _new_windows_of(embed))
        assert windows, "aucune fenêtre Edge de notre instance"
        # _is_ours a mémorisé le PID du navigateur : close() emprunte le
        # chemin rapide (arbre du navigateur) plutôt que le balayage.
        assert embed._browser_pid is not None
    finally:
        embed.close()
    assert not _profile_processes(profile)


# ── 2. Seules nos fenêtres sont éligibles ─────────────────────────────────


@requires_edge
def test_foreign_chromium_window_is_never_ours(page, tmp_path):
    foreign_profile = tempfile.mkdtemp(prefix="pytest_foreign_")
    foreign = subprocess.Popen(
        [
            find_edge(),
            f"--app={page.resolve().as_uri()}",
            f"--user-data-dir={foreign_profile}",
            "--no-first-run",
            "--window-size=300,200",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    embed = EdgeEmbed()
    try:
        assert embed.start(str(page), _FakeParent(), 400, 300)
        user32, enum_proc, ctypes, _ = embed._win32

        def foreign_windows():
            return [
                hwnd
                for hwnd in _list_chrome_windows(user32, enum_proc, ctypes)
                if _edge_embed._window_pid(user32, ctypes, hwnd)
                in {p.pid for p in _profile_processes(foreign_profile)}
            ]

        assert _wait_for(foreign_windows), "la fenêtre étrangère n'est pas apparue"
        assert _wait_for(lambda: _new_windows_of(embed)), "notre fenêtre n'est pas apparue"

        for hwnd in foreign_windows():
            assert embed._is_ours(hwnd) is False, "fenêtre étrangère prise pour la nôtre"
        for hwnd in _new_windows_of(embed):
            assert embed._is_ours(hwnd) is True
    finally:
        embed.close()
        for proc in _profile_processes(foreign_profile):
            proc.kill()
        foreign.wait(timeout=5)
        time.sleep(0.5)
        import shutil

        shutil.rmtree(foreign_profile, ignore_errors=True)


@requires_edge
def test_window_of_unknown_process_is_not_ours(page):
    """Le bureau (PID du shell) n'appartient à aucune instance d'aperçu."""
    embed = EdgeEmbed()
    assert embed.start(str(page), _FakeParent(), 400, 300)
    try:
        user32 = embed._win32[0]
        assert embed._is_ours(user32.GetShellWindow()) is False
    finally:
        embed.close()


# ── 3. Nettoyage des profils abandonnés ───────────────────────────────────


def test_sweep_removes_only_stale_profiles(tmp_path, monkeypatch):
    monkeypatch.setattr(_edge_embed.tempfile, "gettempdir", lambda: str(tmp_path))

    stale = tmp_path / "myai_edge_ancien"
    fresh = tmp_path / "myai_edge_recent"
    unrelated = tmp_path / "autre_dossier"
    for folder in (stale, fresh, unrelated):
        folder.mkdir()
        (folder / "fichier.txt").write_text("x", encoding="utf-8")

    old = time.time() - _edge_embed._STALE_PROFILE_AGE_S - 60
    os.utime(stale, (old, old))
    os.utime(unrelated, (old, old))

    _sweep_stale_profiles()

    assert not stale.exists(), "un profil abandonné aurait dû être supprimé"
    assert fresh.exists(), "un profil récent (aperçu en cours ?) a été supprimé"
    assert unrelated.exists(), "un dossier étranger au préfixe a été supprimé"


def test_close_without_start_is_harmless():
    embed = EdgeEmbed()
    embed.close()
    embed.close()
    assert embed.attached is False
