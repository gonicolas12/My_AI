"""
Bornes de sécurité de requirements.txt (veilles du 09/11 et du 16/11/2026).

Relever une borne minimale suffit à mettre à niveau les installations
existantes : au lancement, utils/requirements_sync.py réinstalle les lignes que
la version installée ne satisfait plus. Ces tests empêchent qu'une édition de
requirements.txt redescende sous un correctif, et vérifient sur les quatre
plateformes que les lignes à marqueurs restent exclusives (une seule ligne par
paquet). Ils vérifient aussi qu'un pip ancien lit le fichier en UTF-8.
"""

import re

import pytest
from packaging import markers
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


def _python_markers(python):
    """Marqueurs python_version et python_full_version d'un Python « x.y.z »."""
    return {"python_version": python.rsplit(".", 1)[0], "python_full_version": python}


def _active(platform_name, python="3.12.0"):
    """Lignes de requirements.txt retenues sur cette plateforme et ce Python (x.y.z)."""
    env = default_environment()
    env.update(PLATFORMS[platform_name])
    env.update(_python_markers(python))
    requirements = []
    for raw in TEXT.splitlines():
        line = sync._COMMENT.sub("", raw).strip()  # pylint: disable=protected-access
        if not line or line.startswith("-"):
            continue
        requirement = Requirement(line)
        if requirement.marker is None or requirement.marker.evaluate(env):
            requirements.append(requirement)
    return requirements


def _line(platform_name, name, python="3.12.0"):
    (requirement,) = [r for r in _active(platform_name, python) if r.name.lower() == name]
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


def test_cryptography_stays_48_on_intel_macs_only():
    # cryptography 49+ n'a plus de wheel macOS x86_64 : pip compilerait le sdist.
    # 48.0.1, dernière wheel universal2, corrige GHSA-537c-gmf6-5ccf.
    intel = _line("Mac Intel", "cryptography").specifier
    assert intel.contains("48.0.1")
    assert not intel.contains("48.0.0") and not intel.contains("49.0.0")
    for platform_name in ("Windows", "Linux", "Mac Apple Silicon"):
        # 49.0.0 : GHSA-jwv3-5hgf-82ww et GHSA-m2h6-j472-rp4c ; 50.0.0 : GHSA-g6cj-pr64-35w5
        specifier = _line(platform_name, "cryptography").specifier
        assert specifier.contains("50.0.0") and specifier.contains("50.0.2")
        assert not specifier.contains("49.0.0") and not specifier.contains("48.0.1")


@pytest.mark.parametrize("platform_name", PLATFORMS)
def test_soupsieve_4_from_python_3_11_5(platform_name):
    # GHSA-mmhr-3c5m-f64f corrigé en 4.0 ; les versions 3.0.2 et suivantes
    # exigent Python 3.11.5
    for python in ("3.11.5", "3.12.0", "3.14.7"):
        specifier = _line(platform_name, "soupsieve", python).specifier
        assert specifier.contains("4.0") and specifier.contains("4.1.1")
        assert not specifier.contains("3.0.2") and not specifier.contains("2.10")
    # Sous 3.11.0 à 3.11.4, aucune version corrigée ne s'installe : ligne ignorée
    for python in ("3.11.0", "3.11.4"):
        assert "soupsieve" not in [r.name.lower() for r in _active(platform_name, python)]


@pytest.mark.parametrize("python, upgraded", [("3.11.4", False), ("3.11.5", True),
                                              ("3.14.7", True)])
def test_soupsieve_is_upgraded_at_launch_from_python_3_11_5(monkeypatch, python, upgraded):
    # Installation existante : beautifulsoup4 avait tiré la 2.10. Le lancement
    # évalue python_full_version et réinstalle la ligne à partir de 3.11.5.
    environment = default_environment()
    environment.update(_python_markers(python))
    monkeypatch.setattr(markers, "default_environment", lambda: dict(environment))
    monkeypatch.setattr(sync, "_installed_versions", lambda: {"soupsieve": "2.10"})
    missing = [line for line in sync.unsatisfied_requirements(TEXT) if line.startswith("soupsieve")]
    assert missing == (['soupsieve>=4.0; python_full_version >= "3.11.5"'] if upgraded else [])


def test_old_pip_reads_requirements_as_utf8():
    # pip avant la 25.0 (24.0 est fourni avec Python 3.11.9) lit requirements.txt
    # dans l'encodage local, cp1252 sous Windows, sauf déclaration PEP 263 dans
    # les deux premières lignes : sans elle, « pip install -r » s'arrêtait sur
    # l'octet 0x8F de « ⚠️ » (UnicodeDecodeError). Même expression que pip.
    first_lines = sync.REQUIREMENTS_FILE.read_bytes().splitlines()[:2]
    declared = [re.search(rb"coding[:=]\s*([-\w.]+)", line)
                for line in first_lines if line.startswith(b"#")]
    assert [found.group(1) for found in declared if found] == [b"utf-8"]


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
