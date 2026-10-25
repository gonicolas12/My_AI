"""
Tests des langues de My_AI (core/i18n.py) : catalogues du serveur
(core/locales/) et de la page mobile du Relay (relay/static/locales/), tr(),
formes du pluriel, langue du système, changement de langue à chaud (Réglages,
détecteur de langue, rappel de langue du moteur, page mobile) et commandes des
prompts par défaut dans chaque langue.
"""

import json
import re
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

from core import i18n
from core.i18n import tr
from core.language_detector import LanguageDetector, reply_instruction, reply_language
from core.prompt_library import _DEFAULT_TEMPLATES, PromptLibrary
from interfaces.desktop.settings import SettingsError, SettingsService
from relay.relay_server import _get_link_required_page, page_catalog, page_catalog_json

ROOT = Path(__file__).resolve().parents[1]
CATALOG_DIRS = {
    "serveur": ROOT / "core" / "locales",
    "page mobile": ROOT / "relay" / "static" / "locales",
}
CASES = [(surface, code) for surface in CATALOG_DIRS for code in i18n.SUPPORTED_LANGUAGES]
PLACEHOLDER = re.compile(r"\{(\w+)\}")


@pytest.fixture(autouse=True)
def _french():
    """Chaque test part du français et rend la main avec la langue du réglage."""
    i18n.reset_for_tests()
    i18n.set_language("fr")
    yield
    i18n.reset_for_tests()


def _catalog(surface, code):
    return json.loads((CATALOG_DIRS[surface] / f"{code}.json").read_text(encoding="utf-8"))


def _variants(message):
    return list(message.values()) if isinstance(message, dict) else [message]


def _placeholders(message):
    return {name for text in _variants(message) for name in PLACEHOLDER.findall(text)}


# ── Catalogues ───────────────────────────────────────────────────────────────


def test_languages_are_those_of_the_settings():
    """La liste des Réglages (config.yaml) et celle de My_AI ne font qu'une."""
    config = yaml.safe_load((ROOT / "config.yaml").read_text(encoding="utf-8"))
    assert tuple(config["language"]["supported"]) == i18n.SUPPORTED_LANGUAGES
    assert config["language"]["default"] in i18n.SUPPORTED_LANGUAGES
    for folder in CATALOG_DIRS.values():
        stems = sorted(path.stem for path in folder.glob("*.json"))
        assert stems == sorted(i18n.SUPPORTED_LANGUAGES)


@pytest.mark.parametrize("surface, code", CASES)
def test_catalog_has_the_french_keys_and_placeholders(surface, code):
    source = _catalog(surface, "fr")
    catalog = _catalog(surface, code)
    assert list(catalog) == list(source)
    for key, message in catalog.items():
        assert _placeholders(message) == _placeholders(source[key]), key
        for text in _variants(message):
            assert isinstance(text, str) and text.strip(), key


@pytest.mark.parametrize("surface, code", CASES)
def test_catalog_has_a_plural_form_for_every_integer(surface, code):
    """0 à 1000 : chaque nombre trouve sa forme (few et many du russe, zero et two de l'arabe)."""
    catalog = _catalog(surface, code)
    for key, source in _catalog(surface, "fr").items():
        if not isinstance(source, dict):
            continue
        assert isinstance(catalog[key], dict), key
        for count in range(1001):
            assert i18n.plural_category(code, count) in catalog[key], (key, count)


def test_workflow_rate_stays_readable_by_the_window():
    """La page Agents lit le taux de « ✅ … (50% … » quelle que soit la langue (agentMeta.ts)."""
    for code in i18n.SUPPORTED_LANGUAGES:
        text = tr("agents.workflowDone", _lang=code, rate="50%")
        assert text.startswith("✅") and re.search(r"[(（]\s*50\s*%", text), code


def _literal_keys(paths, pattern):
    keys = set()
    for path in paths:
        keys.update(pattern.findall(path.read_text(encoding="utf-8")))
    return keys


def test_server_messages_exist_in_the_catalog():
    """Une clé écrite en dur dans le code (tr("…")) existe dans le catalogue."""
    sources = [path for folder in ("core", "interfaces", "relay", "models", "utils")
               for path in (ROOT / folder).rglob("*.py")]
    keys = _literal_keys(sources, re.compile(r"\b(?:tr|translate)\(\s*[\"']([a-z][\w.]+)[\"']"))
    assert len(keys) > 300
    missing = sorted(keys - set(_catalog("serveur", "fr")))
    assert not missing


def test_mobile_page_texts_exist_in_the_catalog():
    """Clés de la page mobile : T('…') des scripts, data-i18n… du HTML."""
    static = ROOT / "relay" / "static"
    keys = _literal_keys([static / "app.js", static / "agents.js"],
                         re.compile(r"\bT\(\s*'([\w.]+)'"))
    keys |= _literal_keys([static / "index.html"], re.compile(r'data-i18n[\w-]*="([\w.]+)"'))
    assert len(keys) > 80
    missing = sorted(keys - set(_catalog("page mobile", "fr")))
    assert not missing


# ── tr() et langue en cours ──────────────────────────────────────────────────


def test_tr_fills_parameters_and_plurals():
    assert tr("agents.debateDone", count=1) == "✅ Débat terminé (1 tour)"
    assert tr("agents.debateDone", count=3) == "✅ Débat terminé (3 tours)"
    assert tr("agents.debateDone", _lang="ru", count=3) == "✅ Дебаты завершены (3 раунда)"
    assert tr("agents.debateDone", _lang="ru", count=5) == "✅ Дебаты завершены (5 раундов)"
    assert tr("agents.debateDone", _lang="ar", count=2) == "✅ انتهت المناظرة (جولتان)"
    # « key » est un paramètre comme un autre : la clé du message est positionnelle
    text = tr("schedule.agentNotFound", _lang="en", key="web")  # pylint: disable=kwarg-superseded-by-positional-arg
    assert text == "❌ Agent not found: web"


def test_tr_follows_the_current_language():
    assert tr("launch.ready") == "Prêt"
    i18n.set_language("de")
    assert i18n.current_language() == "de"
    assert tr("launch.ready") == "Bereit"
    i18n.set_language("ja")
    assert tr("launch.ready") == "準備完了"


def test_missing_key_falls_back_to_english_then_french(monkeypatch):
    monkeypatch.setitem(i18n._CATALOGS, "de", {"only.de": "nur Deutsch"})  # pylint: disable=protected-access
    monkeypatch.setitem(i18n._CATALOGS, "en", {"only.en": "English only"})  # pylint: disable=protected-access
    assert tr("only.de", _lang="de") == "nur Deutsch"
    assert tr("only.en", _lang="de") == "English only"
    assert tr("launch.ready", _lang="de") == "Prêt"
    # Clé inconnue partout : rendue telle quelle, l'appelant ne plante pas
    assert tr("does.not.exist", _lang="de") == "does.not.exist"


def test_language_codes_are_normalized():
    assert i18n.normalize("pt-BR") == "pt"
    assert i18n.normalize("zh_CN") == "zh"
    assert i18n.normalize("EN") == "en"
    assert i18n.normalize("tr-TR") is None
    assert i18n.normalize(None) is None
    with pytest.raises(ValueError):
        i18n.set_language("xx")
    assert i18n.is_rtl("ar") and not i18n.is_rtl("fr")
    assert i18n.language_name("ko") == "한국어"


def _no_environment_language(monkeypatch):
    for variable in ("LC_ALL", "LC_MESSAGES", "LANG", "LANGUAGE"):
        monkeypatch.delenv(variable, raising=False)
    monkeypatch.setattr(i18n.locale, "getlocale", lambda: (None, None))


@pytest.mark.parametrize("windows, expected", [
    ("ja_JP", "ja"), ("pt_BR", "pt"), ("de_AT", "de"), ("tr_TR", "en"), (None, "en"),
])
def test_system_language_or_english(monkeypatch, windows, expected):
    """Premier lancement : la langue de Windows si My_AI la parle, l'anglais sinon."""
    _no_environment_language(monkeypatch)
    monkeypatch.setattr(i18n.sys, "platform", "win32")
    monkeypatch.setattr(i18n, "_windows_ui_language", lambda: windows)
    assert i18n.system_language() == expected


def test_system_language_from_the_environment(monkeypatch):
    _no_environment_language(monkeypatch)
    monkeypatch.setattr(i18n.sys, "platform", "linux")
    monkeypatch.setenv("LANG", "es_ES.UTF-8")
    assert i18n.system_language() == "es"


# ── Changement de langue à chaud ─────────────────────────────────────────────


class _LanguageSetup:
    """Réglages réduits à la langue (config.yaml en mémoire)."""

    def __init__(self):
        self.flags = {}

    @staticmethod
    def values():
        return {"languages": list(i18n.SUPPORTED_LANGUAGES)}

    def set_flag(self, name, value):
        self.flags[name] = value


def test_settings_change_the_model_default_language_at_once():
    detector = LanguageDetector(default_language="fr")
    setup = _LanguageSetup()
    settings = SettingsService(setup, lambda: SimpleNamespace(language_detector=detector))
    assert settings.set_language("ko") == "ko"
    assert setup.flags == {"language.default": "ko"}
    assert detector.default_language == "ko"
    # Code inconnu, ou à normaliser (« en-US ») : refusé, rien n'est écrit
    for code in ("xx", "en-US", None):
        with pytest.raises(SettingsError):
            settings.set_language(code)
    assert setup.flags == {"language.default": "ko"}


def test_settings_without_engine_still_save_the_language():
    setup = _LanguageSetup()
    assert SettingsService(setup, lambda: None).set_language("it") == "it"
    assert setup.flags == {"language.default": "it"}


def test_short_messages_are_answered_in_the_default_language():
    """Message trop court pour juger (« ok ») : la langue des Réglages, pour les agents aussi."""
    i18n.set_language("es")
    assert reply_language("ok") == "es"
    assert reply_instruction("ok") == "Responde siempre en español."
    assert reply_language("ok", "ja") == "ja"
    i18n.set_language("de")
    assert reply_language("ok") == "de"


class _Detector:
    def __init__(self, default, detected):
        self.default_language = default
        self.detected = detected

    def detect(self, _text):
        return self.detected


def _reminded(default, detected, text="ok"):
    from core.ai_engine import AIEngine  # pylint: disable=import-outside-toplevel
    engine = SimpleNamespace(
        language_detector=_Detector(default, detected),
        _memory_reply_language=lambda: None,
        _message_in_english=lambda _text: detected == "en",
        _LANG_SUFFIXES=AIEngine._LANG_SUFFIXES,  # pylint: disable=protected-access
    )
    engine._default_language = lambda: AIEngine._default_language(engine)  # pylint: disable=protected-access
    return AIEngine._reminded_language(engine, text)  # pylint: disable=protected-access


def test_engine_reminds_the_default_language_at_the_end_of_the_message():
    # Français par défaut : rien à rappeler, comme avant
    assert _reminded("fr", "fr") is None
    # Langue des Réglages autre que le français : rappelée…
    assert _reminded("ja", "ja") == "ja"
    # … sauf pour un message clairement dans une autre langue, qui garde la sienne
    assert _reminded("ja", "de") is None
    assert _reminded("fr", "en") == "en"


# ── Page mobile du Relay ─────────────────────────────────────────────────────


def test_mobile_page_catalog_is_completed_by_english_then_french(monkeypatch, tmp_path):
    from relay import relay_server  # pylint: disable=import-outside-toplevel
    (tmp_path / "fr.json").write_text(json.dumps({"a": "fr-a", "b": "fr-b", "c": "fr-c"}), "utf-8")
    (tmp_path / "en.json").write_text(json.dumps({"b": "en-b", "c": "en-c"}), "utf-8")
    (tmp_path / "ko.json").write_text(json.dumps({"c": "ko-c"}), "utf-8")
    monkeypatch.setattr(relay_server, "_LOCALES_DIR", tmp_path)
    assert page_catalog("ko") == {"a": "fr-a", "b": "en-b", "c": "ko-c"}


def test_mobile_page_catalog_cannot_close_its_script_tag():
    text = page_catalog_json("ar")
    assert "</" not in text
    assert json.loads(text)["unlock.button"] == "فتح القفل"


def test_link_required_page_speaks_the_language_of_my_ai():
    i18n.set_language("ar")
    page = _get_link_required_page()
    assert '<html lang="ar" dir="rtl">' in page
    assert tr("relay.linkRequired") in page
    i18n.set_language("en")
    assert '<html lang="en" dir="ltr">' in _get_link_required_page()


def test_router_page_speaks_every_language():
    """Page de routage du QR code (docs/router.html, servie par GitHub Pages) : ses
    textes dans les 12 langues, mêmes clés, toutes lues par la page."""
    page = (ROOT / "docs" / "router.html").read_text(encoding="utf-8")
    block = re.search(r'<script type="application/json" id="messages">(.*?)</script>', page, re.S)
    messages = json.loads(block.group(1))
    assert sorted(messages) == sorted(i18n.SUPPORTED_LANGUAGES)
    keys = list(messages["fr"])
    for code, texts in messages.items():
        assert list(texts) == keys, code
        assert all(isinstance(text, str) and text.strip() for text in texts.values()), code
    assert set(re.findall(r"\bT\.(\w+)", page)) == set(keys)


# ── Prompts par défaut ───────────────────────────────────────────────────────

_BUILTIN_IDS = [template["id"] for template in _DEFAULT_TEMPLATES]
_FIELDS = ("command", "title", "description", "content")


def test_french_builtin_prompts_are_those_of_the_code():
    for template in _DEFAULT_TEMPLATES:
        for field in _FIELDS:
            assert tr(f"prompts.builtin.{template['id']}.{field}") == template[field]


@pytest.mark.parametrize("code", i18n.SUPPORTED_LANGUAGES)
def test_builtin_commands_are_single_and_distinct_words(code):
    owners = {}
    for template_id in _BUILTIN_IDS:
        content = tr(f"prompts.builtin.{template_id}.content", _lang=code)
        assert "{arguments}" in content, template_id
        french = tr(f"prompts.builtin.{template_id}.command", _lang="fr")
        local = tr(f"prompts.builtin.{template_id}.command", _lang=code)
        for command in (french, local):
            assert command and " " not in command
            owner = owners.setdefault(PromptLibrary._normalize(command), template_id)  # pylint: disable=protected-access
            assert owner == template_id, (code, command)


@pytest.fixture(name="library")
def _library(tmp_path):
    return PromptLibrary(path=str(tmp_path / "prompts.json"))


def test_builtin_prompts_follow_the_language(library):
    i18n.set_language("en")
    summary = library.get("resume")
    assert summary["command"] == "summarize" and summary["title"] == "Summary"
    assert library.find_by_command("summarize")["id"] == "resume"
    # La commande française reste comprise
    assert library.find_by_command("résume")["id"] == "resume"
    assert library.find_by_command("resume")["id"] == "resume"
    expanded = library.expand("/translate Bonjour tout le monde")
    assert "translate into English" in expanded and "Bonjour tout le monde" in expanded
    i18n.set_language("ja")
    assert library.find_by_command("要約")["id"] == "resume"
    assert [view["command"] for view in library.search("翻")] == ["翻訳"]


def test_custom_command_wins_over_a_translated_builtin_one(library):
    """Un prompt « /summarize » créé en français reste le sien une fois l'interface en anglais."""
    custom = library.add(title="Mon résumé", command="summarize",
                         content="Résume en 3 mots : {arguments}")
    i18n.set_language("en")
    assert library.find_by_command("summarize")["id"] == custom["id"]
    assert library.find_by_command("résume")["id"] == "resume"
