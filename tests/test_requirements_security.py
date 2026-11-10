"""
Bornes de sécurité de requirements.txt (veille du 09/11/2026).

Relever une borne minimale suffit à mettre à niveau les installations
existantes : au lancement, utils/requirements_sync.py réinstalle les lignes que
la version installée ne satisfait plus. Ces tests empêchent qu'une édition de
requirements.txt redescende sous un correctif, et vérifient sur les quatre
plateformes que les lignes à marqueurs restent exclusives (une seule ligne par
paquet).
"""

import pytest
from packaging.markers import default_environment
from packaging.requirements import Requirement

from utils import requirements_sync as sync

TEXT = sync.REQUIREMENTS_FILE.read_text(encoding="utf-8")

PLATFORMS = {
    "Windows": {"platform_system": "Windows", "platform_machine": "AMD64", "sys_platform": "win32"},
    "Linux": {"platform_system": "Linux", "platform_machine": "x86_64", "sys_platform": "linux"},
    "Mac Apple Silicon": {"platform_system": "Darwin", "platform_machine": "arm64",
                          "sys_platform": "darwin"},
    "Mac Intel": {"platform_system": "Darwin", "platform_machine": "x86_64", "sys_platform": "darwin"},
}

# (paquet, première version corrigée, dernière version vulnérable)
SECURITY_FLOORS = [
    ("pillow", "13.0.0", "12.3.0"),  # une quarantaine d'avis (PYSEC-2026-4327…), rien en 12.x
    ("aiohttp", "3.14.4", "3.14.3"),  # GHSA-2g87-pp6c-29x5 et 7 autres
    ("websockets", "17.4", "17.3"),  # recv() : plus de 4096 fragments
    ("sentence-transformers", "5.6.0", "5.5.1"),  # GHSA-jhr6-gm9c-rqjv
]


def _active(platform_name, python="3.12"):
    """Lignes de requirements.txt retenues sur cette plateforme."""
    env = default_environment()
    env.update(PLATFORMS[platform_name])
    env.update({"python_version": python, "python_full_version": f"{python}.0"})
    requirements = []
    for raw in TEXT.splitlines():
        line = sync._COMMENT.sub("", raw).strip()  # pylint: disable=protected-access
        if not line or line.startswith("-"):
            continue
        requirement = Requirement(line)
        if requirement.marker is None or requirement.marker.evaluate(env):
            requirements.append(requirement)
    return requirements


def _line(platform_name, name):
    (requirement,) = [r for r in _active(platform_name) if r.name.lower() == name]
    return requirement


@pytest.mark.parametrize("platform_name", PLATFORMS)
def test_one_line_per_package_on_each_platform(platform_name):
    names = [r.name.lower() for r in _active(platform_name)]
    assert sorted({n for n in names if names.count(n) > 1}) == []


@pytest.mark.parametrize("platform_name", PLATFORMS)
@pytest.mark.parametrize("name, fixed, vulnerable", SECURITY_FLOORS)
def test_security_floors(platform_name, name, fixed, vulnerable):
    specifier = _line(platform_name, name).specifier
    assert specifier.contains(fixed, prereleases=True)
    assert not specifier.contains(vulnerable, prereleases=True)


def test_pymupdf_stays_1x_on_intel_macs_only():
    # PyMuPDF 2.x n'a pas de wheel macOS x86_64 : pip compilerait ses sources
    assert _line("Mac Intel", "pymupdf").specifier.contains("1.28.2")
    assert not _line("Mac Intel", "pymupdf").specifier.contains("2.1")
    for platform_name in ("Windows", "Linux", "Mac Apple Silicon"):
        assert _line(platform_name, "pymupdf").specifier.contains("2.1")


def test_intel_macs_keep_their_pinned_ml_stack():
    assert not _line("Mac Intel", "torch").specifier.contains("2.3.0")
    assert not _line("Mac Intel", "numpy").specifier.contains("2.0.0")
    assert not _line("Mac Intel", "transformers").specifier.contains("5.0.0")


@pytest.mark.parametrize("platform_name", ["Windows", "Linux", "Mac Apple Silicon"])
def test_transformers_5_everywhere_else(platform_name):
    # 5.10.0 : GHSA-xrqw-3rrv-vx5w, dernier des six avis que la 4.57.6 garde
    transformers = _line(platform_name, "transformers").specifier
    assert transformers.contains("5.10.0") and transformers.contains("5.22.2")
    assert not transformers.contains("5.9.0") and not transformers.contains("4.57.6")
    # transformers 5.x désactive torch en dessous de 2.6 sans le mettre à jour
    torch = _line(platform_name, "torch").specifier
    assert torch.contains("2.6.0") and torch.contains("2.15.0")
    assert not torch.contains("2.5.1")


def test_too_old_installed_versions_are_reinstalled_at_launch(monkeypatch):
    # Ce PC le 09/11/2026 : les lignes concernées repartent dans pip au lancement
    installed = {"pillow": "12.3.0", "aiohttp": "3.14.3", "websockets": "16.1.1"}
    monkeypatch.setattr(sync, "_installed_versions", lambda: dict(installed))
    missing = sync.unsatisfied_requirements(TEXT)
    assert {"pillow>=13.0.0", "aiohttp>=3.14.4", "websockets>=17.4"} <= set(missing)

    installed.update({"pillow": "13.0.0", "aiohttp": "3.14.5", "websockets": "17.4"})
    missing = sync.unsatisfied_requirements(TEXT)
    assert not {"pillow>=13.0.0", "aiohttp>=3.14.4", "websockets>=17.4"} & set(missing)
