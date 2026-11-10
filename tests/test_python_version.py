"""
Tests du contrôle de la version de Python au lancement (utils/python_version.py).

Python 3.10 ne peut plus installer Pillow 13, websockets 17 ni PyMuPDF 2, et
Python 3.15 n'a pas encore de wheel onnxruntime (chromadb, faster-whisper) :
pip y échouait au milieu de l'installation, avec une erreur sans rapport visible
avec la version de Python. Les lanceurs s'arrêtent désormais avant, avec un
message qui dit quoi installer.
"""

import json
from pathlib import Path

import pytest

from utils import python_version as pv

ROOT = Path(__file__).resolve().parent.parent


@pytest.mark.parametrize("version, supported", [
    ((3, 10), False), ((3, 11), True), ((3, 12), True), ((3, 13), True), ((3, 14), True),
    ((3, 15), False),
])
@pytest.mark.parametrize("system, machine", [
    ("Windows", "AMD64"), ("Linux", "x86_64"), ("Darwin", "arm64"),
])
def test_supported_versions(version, supported, system, machine):
    assert (pv.unsupported_message(version, system, machine) is None) is supported


@pytest.mark.parametrize("version, supported", [((3, 11), True), ((3, 12), True), ((3, 13), False)])
def test_intel_macs_stop_at_312(version, supported):
    assert (pv.unsupported_message(version, "Darwin", "x86_64") is None) is supported


def test_message_names_the_version_and_what_to_install():
    message = pv.unsupported_message((3, 15), "Windows", "AMD64")
    assert "3.15" in message and "3.11" in message and "3.14" in message
    assert len(message.splitlines()) == 2


def test_message_on_intel_mac_recommends_312():
    assert "3.12" in pv.unsupported_message((3, 13), "Darwin", "x86_64").splitlines()[1]


@pytest.mark.parametrize("code", ["ar", "de", "en", "es", "fr", "it", "ja", "ko", "nl", "pt", "ru", "zh"])
def test_message_exists_in_the_12_languages(code):
    catalog = json.loads((ROOT / "core" / "locales" / f"{code}.json").read_text(encoding="utf-8"))
    for key, placeholders in (("launch.pythonUnsupported", ("{version}", "{minimum}", "{maximum}")),
                              ("launch.pythonInstall", ("{maximum}",))):
        assert all(p in catalog[key] for p in placeholders), (code, key)


def test_check_stops_the_launcher(monkeypatch, capsys):
    monkeypatch.setattr(pv.sys, "version_info", (3, 15, 2, "final", 0))
    monkeypatch.setattr(pv.platform, "system", lambda: "Windows")
    with pytest.raises(SystemExit) as stop:
        pv.check_python_version()
    assert stop.value.code == 1
    assert "3.15" in capsys.readouterr().out


def test_check_lets_a_supported_python_through(monkeypatch):
    monkeypatch.setattr(pv.sys, "version_info", (3, 13, 9, "final", 0))
    monkeypatch.setattr(pv.platform, "system", lambda: "Linux")
    pv.check_python_version()  # ne lève rien


def test_shell_launchers_check_the_same_range():
    expected = f"{pv.MINIMUM} <= sys.version_info[:2] <= {pv.MAXIMUM}"
    for launcher in ("launch.bat", "launch.sh"):
        assert expected in (ROOT / launcher).read_text(encoding="utf-8"), launcher


def test_python_launchers_check_before_installing_anything():
    for launcher in ("launch_unified.py", "main.py"):
        source = (ROOT / launcher).read_text(encoding="utf-8")
        assert source.index("check_python_version()") < source.index("sync_requirements()"), launcher
