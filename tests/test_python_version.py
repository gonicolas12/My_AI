"""
Tests du contrôle de la version de Python au lancement (utils/python_version.py).

Python 3.10 ne peut plus installer Pillow 13, websockets 17 ni PyMuPDF 2, et
Python 3.15 n'a pas encore de wheel onnxruntime (chromadb, faster-whisper) :
pip y échouait au milieu de l'installation, avec une erreur sans rapport visible
avec la version de Python. Les lanceurs s'arrêtent désormais avant, avec un
message qui dit quoi installer.

Le code lui-même doit se lire sous Python 3.11 : une f-string que seul Python
3.12 accepte (PEP 701) empêchait l'appli de démarrer en 3.11
(core/document_memory.py, dans la 9.2.0).
"""

import io
import json
import os
import sys
import tokenize
import warnings
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
        # Avec ou sans console (fenêtre d'attente de launch_unified.py)
        installs = [source.index(call) for call in ("sync_requirements(", "sync_dependencies(")
                    if call in source]
        assert installs and source.index("check_python_version(") < min(installs), launcher


def test_without_console_the_message_is_also_shown_elsewhere(monkeypatch, capsys):
    """Lancé depuis l'épingle (pythonw), le message va aussi à une boîte de dialogue."""
    monkeypatch.setattr(pv.sys, "version_info", (3, 15, 0, "final", 0))
    shown = []
    with pytest.raises(SystemExit) as stop:
        pv.check_python_version(report=shown.append)
    assert stop.value.code == 1
    assert len(shown) == 1 and "3.15" in shown[0]
    assert shown[0] in capsys.readouterr().out  # écrit aussi dans les sorties


# ── Le code se lit sous Python 3.11 ─────────────────────────────────────────

# Le code de l'appli et des tests ; ComfyUI s'installe dans tools/
_CODE_FOLDERS = ("core", "interfaces", "relay", "utils", "processors", "generators", "models",
                 "memory", "tools", "tests", "examples")
_NOT_CODE = {"ComfyUI_windows_portable", "node_modules", "__pycache__"}


def _python_files():
    """Fichiers Python de l'appli et de ses tests."""
    files = [ROOT / "main.py", ROOT / "launch_unified.py"]
    for folder in _CODE_FOLDERS:
        for root, dirs, names in os.walk(ROOT / folder):
            dirs[:] = [name for name in dirs if name not in _NOT_CODE]
            files += [Path(root) / name for name in names if name.endswith(".py")]
    return files


def _quote(literal):
    """Guillemets d'une chaîne (simples, doubles, ou trois de suite), préfixe ôté."""
    body = literal.lstrip("bBfFrRuUtT")
    return body[:3] if body[:3] in ('"""', "'''") else body[:1]


def _only_312_fstrings(source):
    """
    Lignes des f-strings que seul Python 3.12 lit (PEP 701), d'après tokenize
    (Python 3.12 et plus) : entre leurs accolades, Python 3.11 refuse leurs
    propres guillemets, une barre oblique inverse, un commentaire et, entre
    guillemets simples, un retour à la ligne.
    """
    lines = []
    opened = []  # guillemets des f-strings ouvertes, la plus proche en dernier
    for token in tokenize.generate_tokens(io.StringIO(source).readline):
        kind, text, line = token.type, token.string, token.start[0]
        if not opened:
            if kind == tokenize.FSTRING_START:
                opened.append(_quote(text))
            continue
        quote = opened[-1]
        if kind in (tokenize.STRING, tokenize.FSTRING_START):
            nested = _quote(text)
            if (nested[0] == quote[0]) if len(quote) == 1 else (nested == quote):
                lines.append(line)
        if ((kind == tokenize.STRING or (kind == tokenize.FSTRING_MIDDLE and len(opened) > 1))
                and "\\" in text):
            lines.append(line)
        if kind == tokenize.COMMENT or (kind == tokenize.NL and len(quote) == 1):
            lines.append(line)
        if kind == tokenize.FSTRING_START:
            opened.append(_quote(text))
        elif kind == tokenize.FSTRING_END:
            opened.pop()
    return lines


def _refused_by_python_311(source):
    """Lignes que Python 3.11 refuse (aucune s'il lit tout) : il le dit lui-même ; une
    version plus récente, qui les lit, l'apprend de _only_312_fstrings."""
    if sys.version_info < (3, 12):
        try:
            with warnings.catch_warnings():
                # Un échappement inconnu (« \d » hors d'une chaîne brute) n'est qu'un
                # avertissement : le fichier se lit
                warnings.simplefilter("ignore")
                compile(source, "<test>", "exec")
        except SyntaxError as exc:
            return [exc.lineno]
        return []
    return _only_312_fstrings(source)


@pytest.mark.parametrize("source", [
    "x = f\"folder_{digest(b'\\0')[:24]}\"",  # core/document_memory.py, 9.2.0
    "x = f\"{data[\"key\"]}\"",
    "x = f'{data['key']}'",
    "x = f'{\nvalue}'",
    "x = f\"\"\"{\"\"\"inner\"\"\"}\"\"\"",
    "x = f\"{f\"{y}\"}\"",
    "x = f\"{'\\n'.join(lines)}\"",
    "x = f\"{f'a\\tb'}\"",
    "x = f\"\"\"{value # commentaire\n}\"\"\"",
])
def test_python_311_refuses_these_fstrings(source):
    assert _refused_by_python_311(source)


@pytest.mark.parametrize("source", [
    "x = f\"{data['key']}\"",
    "x = f\"\"\"{data[\"key\"]}\"\"\"",
    "x = f'''{data['key']}'''",
    "x = f\"{'#'.join(items)}\"",
    "x = f\"{x:#x}\"",
    "x = f\"{value!r:>10}\"",
    "x = 'a' f\"{x}\"",
    "x = 'it' f\"{d['k']}\"",
    "x = f\"{value = }\"",
    "x = f\"{f'{y}'}\"",
    "x = f\"\"\"{\n  value\n}\"\"\"",
    "x = f\"é {d['k']} è {e['l']}\"",
    "x = f\"{value:{width}}\"",
    "x = f\"{value:{'>' if left else '<'}{width}}\"",
    "x = '\\n'.join(f\"{line}\" for line in lines)",
    "x = rf\"\\d{n}\"",
    "x = f\"a\\tb {c}\"",
    "x = f\"{{literal}} {c}\"",
])
def test_python_311_reads_these_fstrings(source):
    assert not _refused_by_python_311(source)


def test_the_app_reads_under_python_311():
    """Une seule f-string de Python 3.12 et l'appli ne démarre plus en 3.11 : le
    fichier ne s'importe pas (SyntaxError), ni rien de ce qui l'importe."""
    refused = {}
    for path in _python_files():
        lines = _refused_by_python_311(path.read_text(encoding="utf-8-sig"))
        if lines:
            refused[str(path.relative_to(ROOT))] = lines
    assert not refused, refused
