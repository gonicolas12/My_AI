"""
Tests de l'installation au lancement des dépendances manquantes (utils/requirements_sync.py).

Après un « git pull », requirements.txt pouvait lister un paquet absent de
l'environnement (rapidocr pour l'OCR) : la fonction correspondante restait
indisponible tant que l'utilisateur ne relançait pas pip lui-même. Aucun vrai
pip n'est lancé ici : les paquets installés et pip sont simulés.
"""

import importlib.metadata

import pytest

from utils import requirements_sync as sync

REQUIREMENTS = """\
# Commentaire de section
click>=8.0.0
rapidocr>=3.9.2  # OCR des PDF scannés
PyMuPDF>=1.24.3
qrcode[pil]>=7.4.0
winotify>=1.1.0; platform_system == "Windows"
plyer>=2.1.0,<3; platform_system != "Windows"
bitsandbytes>=0.40.0; sys_platform == "plateforme-inexistante"
--extra-index-url https://example.org/simple
"""


@pytest.fixture(name="env")
def _env(monkeypatch, tmp_path):
    """Environnement simulé : paquets installés, pip qui installe tout sauf paquet-casse."""
    installed = {"click": "8.1.7", "pymupdf": "1.23.8", "qrcode": "7.4.2",
                 "winotify": "1.1.0", "plyer": "2.1.0"}
    calls = []

    def fake_pip(lines):
        calls.append(list(lines))
        if any(line.startswith("paquet-casse") for line in lines):
            return False
        for line in lines:
            name = line.split(">=")[0].lower()
            installed[name] = "99.0"
        return True

    monkeypatch.setattr(sync, "_installed_versions", lambda: dict(installed))
    monkeypatch.setattr(sync, "_pip_install", fake_pip)
    monkeypatch.setattr(sync, "_refresh_import_paths", lambda: None)
    monkeypatch.delenv(sync.SKIP_ENV, raising=False)
    requirements = tmp_path / "requirements.txt"
    requirements.write_text(REQUIREMENTS, encoding="utf-8")
    state = tmp_path / "data" / ".requirements_sync.json"
    return {"requirements": requirements, "state": state, "calls": calls, "installed": installed}


def test_lists_missing_and_too_old_packages_only(env):
    # Absent (rapidocr) et trop ancien (PyMuPDF 1.23.8) ; les marqueurs d'une
    # autre plateforme et les options pip sont ignorés
    assert sync.unsatisfied_requirements(REQUIREMENTS) == ["rapidocr>=3.9.2", "PyMuPDF>=1.24.3"]


def test_installs_missing_lines_in_one_pip_call(env):
    failed = sync.sync_requirements(env["requirements"], env["state"])
    assert failed == []
    assert env["calls"] == [["rapidocr>=3.9.2", "PyMuPDF>=1.24.3"]]
    assert sync.sync_requirements(env["requirements"], env["state"]) == []
    assert len(env["calls"]) == 1  # plus rien à installer au lancement suivant


def test_failing_line_does_not_block_others_and_is_not_retried(env, capsys):
    env["requirements"].write_text(REQUIREMENTS + "paquet-casse>=1.0\n", encoding="utf-8")
    failed = sync.sync_requirements(env["requirements"], env["state"])
    assert failed == ["paquet-casse>=1.0"]
    assert env["calls"] == [
        ["rapidocr>=3.9.2", "PyMuPDF>=1.24.3", "paquet-casse>=1.0"],
        ["rapidocr>=3.9.2"], ["PyMuPDF>=1.24.3"], ["paquet-casse>=1.0"],
    ]
    assert env["installed"]["rapidocr"] == "99.0"

    # Lancement suivant, requirements.txt inchangé : pas de nouvel essai
    assert sync.sync_requirements(env["requirements"], env["state"]) == ["paquet-casse>=1.0"]
    assert len(env["calls"]) == 4
    assert 'pip install "paquet-casse>=1.0"' in capsys.readouterr().out


def test_failed_line_is_retried_when_requirements_change(env):
    env["requirements"].write_text(REQUIREMENTS + "paquet-casse>=1.0\n", encoding="utf-8")
    sync.sync_requirements(env["requirements"], env["state"])
    env["requirements"].write_text(REQUIREMENTS + "paquet-casse>=1.1\n", encoding="utf-8")
    sync.sync_requirements(env["requirements"], env["state"])
    assert env["calls"][-1] == ["paquet-casse>=1.1"]


def test_nothing_missing_runs_no_pip(env):
    env["installed"].update({"rapidocr": "3.9.2", "pymupdf": "1.28.2"})
    assert sync.sync_requirements(env["requirements"], env["state"]) == []
    assert env["calls"] == []


def test_unchanged_requirements_are_not_checked_again(env, monkeypatch):
    env["installed"].update({"rapidocr": "3.9.2", "pymupdf": "1.28.2"})
    sync.sync_requirements(env["requirements"], env["state"])

    def no_check():
        raise AssertionError("paquets relus alors que requirements.txt n'a pas changé")

    monkeypatch.setattr(sync, "_installed_versions", no_check)
    assert sync.sync_requirements(env["requirements"], env["state"]) == []

    # Après un « git pull » qui modifie requirements.txt, la vérification reprend
    env["requirements"].write_text(REQUIREMENTS + "nouveau-paquet>=1.0\n", encoding="utf-8")
    with pytest.raises(AssertionError, match="paquets relus"):
        sync.sync_requirements(env["requirements"], env["state"])


def test_can_be_disabled(env, monkeypatch):
    monkeypatch.setenv(sync.SKIP_ENV, "1")
    assert sync.sync_requirements(env["requirements"], env["state"]) == []
    assert env["calls"] == []


def test_emptied_dist_info_is_ignored(tmp_path, monkeypatch):
    """Installation interrompue : dossier .dist-info sans METADATA à côté du bon."""
    (tmp_path / "regex-2019.12.17.dist-info").mkdir()
    good = tmp_path / "regex-2024.11.6.dist-info"
    good.mkdir()
    (good / "METADATA").write_text(
        "Metadata-Version: 2.1\nName: regex\nVersion: 2024.11.6\n", encoding="utf-8"
    )
    real = importlib.metadata.distributions
    monkeypatch.setattr(importlib.metadata, "distributions", lambda: real(path=[str(tmp_path)]))
    assert sync._installed_versions() == {"regex": "2024.11.6"}
    assert sync.unsatisfied_requirements("regex>=2023.0.0\n") == []
