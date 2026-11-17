"""
Tests de la langue des messages (core/language_detector.py) : l'écriture
d'abord (kana → japonais, idéogrammes → chinois, hangul → coréen, arabe,
cyrillique), puis les mots-outils et langdetect pour l'alphabet latin.

Seul, langdetect se trompait sur les messages courts : « ¿Qué hay en mi
carpeta OneDrive de tu memoria? » → catalan, « 你记忆里的OneDrive文件夹里有什么？ »
→ norvégien, deux langues hors de My_AI, et my_ai répondait en français.
"""

import logging

import pytest

from core import i18n, language_detector
from core.ai_engine import AIEngine
from core.language_detector import LanguageDetector, reply_instruction, reply_language

# Les deux messages du constat (onglet Documents du panneau Mémoire)
SPANISH_QUESTION = "¿Qué hay en mi carpeta OneDrive de tu memoria?"
CHINESE_QUESTION = "你记忆里的OneDrive文件夹里有什么？"

# La même question sur la mémoire des documents, dans les 12 langues
MEMORY_QUESTIONS = {
    "fr": "Qu'y a-t-il dans mon dossier OneDrive de ta mémoire ?",
    "en": "What's in my OneDrive folder from your memory?",
    "es": SPANISH_QUESTION,
    "de": "Was ist in meinem OneDrive-Ordner in deinem Gedächtnis?",
    "it": "Cosa c'è nella mia cartella OneDrive nella tua memoria?",
    "pt": "O que há na minha pasta OneDrive da tua memória?",
    "nl": "Wat zit er in mijn OneDrive-map in je geheugen?",
    "ru": "Что в моей папке OneDrive в твоей памяти?",
    "zh": CHINESE_QUESTION,
    "ja": "あなたの記憶にあるOneDriveフォルダには何がありますか？",
    "ko": "네 기억 속 OneDrive 폴더에 뭐가 있어?",
    "ar": "ماذا يوجد في مجلد OneDrive في ذاكرتك؟",
}

# Messages courts que l'ancien détecteur manquait : langue voisine hors de
# My_AI (« Vielen Dank! » → afrikaans, « Привет, как дела? » → macédonien)
# ou moins de 10 caractères (la langue par défaut, quelle qu'elle soit)
SHORT_MESSAGES = {
    "fr": ["Merci beaucoup !", "Pourquoi ?"],
    "en": ["How are you today?", "I don't understand", "Who am I?"],
    "es": ["Lista mis documentos", "¿Por qué?", "Hola"],
    "de": ["Vielen Dank!", "Wie viel ist 12 mal 7?"],
    "it": ["Mostrami i miei file", "Puoi riassumere questo documento?"],
    "pt": ["Quem sou eu?", "Explique as listas em Python"],
    "nl": ["Dank je wel!", "Welke dag is het vandaag?"],
    "ru": ["Привет, как дела?", "Кто я?"],
    "zh": ["你好吗？", "给我解释一下Python的列表"],
    "ja": ["ありがとう", "私は誰？"],
    "ko": ["안녕하세요?", "나는 누구야?"],
    "ar": ["من أنا؟", "مرحبا"],
}


@pytest.fixture(autouse=True)
def _french():
    """Chaque test part du français et rend la main avec la langue du réglage."""
    i18n.reset_for_tests()
    i18n.set_language("fr")
    yield
    i18n.reset_for_tests()


def _detector(expected):
    """Détecteur dont la langue par défaut n'est pas celle attendue : un repli se voit."""
    return LanguageDetector(default_language="en" if expected == "fr" else "fr")


def _engine():
    """AIEngine sans __init__, avec le vrai détecteur et sans mémoire."""
    engine = AIEngine.__new__(AIEngine)
    engine.logger = logging.getLogger(__name__)
    engine.knowledge_base = None
    engine.language_detector = LanguageDetector(default_language="fr")
    return engine


# ── Les 12 langues ───────────────────────────────────────────────────────────


@pytest.mark.parametrize("code", list(MEMORY_QUESTIONS))
def test_memory_question_is_read_in_every_language(code):
    assert _detector(code).detect(MEMORY_QUESTIONS[code]) == code


@pytest.mark.parametrize(
    "code, message",
    [(code, message) for code, messages in SHORT_MESSAGES.items() for message in messages],
)
def test_short_message_is_read_in_every_language(code, message):
    assert _detector(code).detect(message) == code


def test_reported_messages_get_their_language_instruction():
    """« Réponds toujours en français. » faisait répondre my_ai en français."""
    engine = _engine()
    # pylint: disable=protected-access
    assert engine._language_instruction(SPANISH_QUESTION) == "Responde siempre en español."
    assert engine._language_instruction(CHINESE_QUESTION) == "请始终用中文回答。"
    # Le français et l'anglais court restent ce qu'ils étaient
    assert engine._language_instruction(MEMORY_QUESTIONS["fr"]) == "Réponds toujours en français."
    assert engine._language_instruction("Who am I?") == "Always respond in English."
    assert engine._language_instruction("ok") == "Réponds toujours en français."


def test_agents_read_the_language_of_a_short_message():
    """Les agents passent par reply_language() : même détecteur, langue des Réglages en repli."""
    assert reply_language("你好吗？") == "zh"
    assert reply_instruction(SPANISH_QUESTION) == "Responde siempre en español."
    assert reply_language("ok") == "fr"
    i18n.set_language("de")
    assert reply_language("ok") == "de"


# ── Écritures mêlées, citations ──────────────────────────────────────────────


@pytest.mark.parametrize("message, code", [
    # Des noms en alphabet latin n'enlèvent rien à l'autre écriture
    ("Что такое Docker Compose?", "ru"),
    ("PythonでHello Worldを表示する方法は？", "ja"),
    ("Python 리스트를 설명해 줘", "ko"),
    ("اشرح لي القوائم في Python", "ar"),
    # Un identifiant n'est pas le mot anglais « my »
    ("Проверка модели my_ai…", "ru"),
    # Une phrase en alphabet latin qui cite un mot d'une autre écriture garde sa langue
    ("What does ありがとう mean?", "en"),
    ("Que veut dire 谢谢 ?", "fr"),
    ("How do you say Спасибо?", "en"),
    # Un passage cité ne compte pas : la langue est celle de la demande
    ("Traduis « Where is the station? » en espagnol", "fr"),
    ("这句话是什么意思：“How are you doing today”", "zh"),
    # Liens et code non plus
    ("Résume https://en.wikipedia.org/wiki/Language_model pour moi", "fr"),
    ("Explica este código: `for item in items: print(item)`", "es"),
])
def test_mixed_message_keeps_the_language_of_its_author(message, code):
    assert _detector(code).detect(message) == code


# ── Repli sur la langue par défaut ───────────────────────────────────────────


@pytest.mark.parametrize("message", [
    # Rien qui dise une langue
    "ok", "👍", "12345", "Python", "https://example.com/page",
    # Langues hors de My_AI, sans être prises pour une voisine
    "Dzień dobry, jak się masz?",  # polonais
    "Bu kodla bana yardım edebilir misin?",  # turc
    "Terima kasih banyak",  # indonésien
    "Привіт, як справи?",  # ukrainien : pas du russe
    "سلام، حالت چطوره؟",  # persan : pas de l'arabe
    "Γεια σου, τι κάνεις;",  # grec
])
def test_message_without_a_supported_language_gets_the_default(message):
    for default in ("fr", "ja"):
        assert LanguageDetector(default_language=default).detect(message) == default


def test_ambiguous_word_gets_the_default():
    """« Hallo » est allemand ou néerlandais : la langue par défaut tranche."""
    assert LanguageDetector(default_language="ko").detect("Hallo") == "ko"
    assert LanguageDetector(default_language="ko").detect("Hallo, wie geht es dir?") == "de"


def test_without_langdetect_the_script_and_function_words_still_decide(monkeypatch):
    monkeypatch.setattr(language_detector, "_HAS_LANGDETECT", False)
    for code, message in [
        ("es", SPANISH_QUESTION),
        ("zh", CHINESE_QUESTION),
        ("fr", "Merci beaucoup !"),
        ("de", "Wer bin ich?"),
        ("ar", "من أنا؟"),
    ]:
        assert _detector(code).detect(message) == code
    # Sans indice, toujours la langue par défaut
    assert LanguageDetector(default_language="it").detect("Python") == "it"
