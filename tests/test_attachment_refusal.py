"""
Tests du garde-fou des réponses sur pièces jointes (core/ai_engine.py).

Avec un PDF joint, le modèle (qwen3.5:4b) répondait parfois « j'ai besoin
d'accéder au fichier, veuillez l'envoyer » alors que son contenu était dans le
prompt : environ une réponse sur trente, toujours dès la première phrase. Cette
phrase est retenue avant affichage ; si c'est un tel refus, la génération est
coupée et la réponse redemandée une fois par un message de rappel.
"""

import json
import logging

import pytest

from core import ai_engine
from core.ai_engine import AIEngine
from models import local_llm

# Refus réellement produits par le modèle, puis formulations voisines
REFUSALS = [
    "Pour mieux répondre à votre demande et analyser précisément le contenu du PDF que vous "
    "mentionnez (cybersécurité 1er semestre 2025Corrigé_fr.pdf), j'ai besoin d'accéder "
    "directement au fichier.\n\nVeuillez envoyer le fichier ou copier-coller son contenu",
    "Pour répondre précisément à votre question, j'ai besoin d'accéder au contenu du fichier "
    "`cybersécurité 1er semestre 2025Corrigé_fr.pdf` qui semble être",
    "Je ne peux pas ouvrir ce PDF. Pourriez-vous me transmettre le contenu du document ?",
    "Je n'ai pas accès au fichier mentionné.",
]
# Réponses correctes (dont des débuts réels) qui ne doivent pas être écartées
ANSWERS = [
    "Dans le document **cybersécurité 1er semestre 2025Corrigé_fr.pdf**, je vois un "
    "**questionnaire corrigé** couvrant les bases fondamentales de la cybersécurité.",
    "Dans le document « X » que tu viens de fournir, je vois un formulaire corrigé.",
    "Veuillez noter qu'il ne faut jamais partager son mot de passe avec un collègue.",
    "Merci de verrouiller votre poste (Windows + L) dès que vous vous absentez.",
    "Je vais analyser le contenu du PDF que vous avez mentionné. Pour être précis, "
    "je vais extraire et structurer les informations.",
]


@pytest.mark.parametrize("text", REFUSALS)
def test_refusals_are_detected(text):
    assert ai_engine._ASKS_FOR_ATTACHMENT.search(text)


@pytest.mark.parametrize("text", ANSWERS)
def test_correct_answers_are_not_flagged(text):
    assert not ai_engine._ASKS_FOR_ATTACHMENT.search(text)


def _tokens(text, size=7):
    return [text[i:i + size] for i in range(0, len(text), size)]


@pytest.mark.parametrize("text", REFUSALS)
def test_refusals_open_like_a_refusal(text):
    """Ils sont donc retenus jusqu'à la fin de leur première phrase."""
    assert ai_engine._RISKY_OPENING.match(text)


def test_ordinary_answer_shows_after_a_few_characters():
    """« Dans le document… » : affichée sans attendre la fin de la phrase."""
    shown = []
    guard = ai_engine._FirstSentenceGuard(shown.append)
    for token in _tokens(ANSWERS[0]):
        guard(token)
        if shown:
            break
    assert guard.released and len("".join(shown)) < 40


def test_refusal_shaped_opening_waits_for_the_sentence_end():
    shown = []
    guard = ai_engine._FirstSentenceGuard(shown.append)
    answer = "Pour résumer, le document est un questionnaire corrigé. Il aborde le phishing."
    for token in _tokens(answer):
        assert guard(token) is not False
        if not guard.released:
            assert shown == []  # première phrase pas encore finie
    assert "".join(shown) == answer and not guard.rejected


def test_refusal_is_cut_as_soon_as_detected_and_never_shown():
    shown, received = [], ""
    guard = ai_engine._FirstSentenceGuard(shown.append)
    for token in _tokens(REFUSALS[0]):
        received += token
        if guard(token) is False:
            break
    assert guard.rejected and shown == []
    assert "Veuillez envoyer" not in received  # coupé dès « …accéder directement au fichier »


def test_guard_releases_a_short_answer_at_the_end():
    shown = []
    guard = ai_engine._FirstSentenceGuard(shown.append)
    guard("Oui.")
    assert shown == []
    guard.release()
    assert shown == ["Oui."]


class _FakeLLM:
    """generate_stream scripté : une réponse par appel, historique comme LocalLLM."""

    def __init__(self, *replies):
        self.replies = list(replies)
        self.conversation_history = []
        self.calls = []

    def generate_stream(self, prompt, system_prompt=None, on_token=None, **kwargs):
        self.calls.append({"prompt": prompt, **kwargs})
        reply, full = self.replies.pop(0), ""
        for token in _tokens(reply):
            full += token
            if on_token and on_token(token) is False:
                break
        self.conversation_history += [{"role": "user", "content": prompt},
                                      {"role": "assistant", "content": full}]
        return full


@pytest.fixture(name="engine")
def _engine():
    engine = AIEngine.__new__(AIEngine)
    engine.logger = logging.getLogger("test_attachment_refusal")
    return engine


def test_refusal_is_cut_and_the_answer_asked_again(engine):
    llm = _FakeLLM(REFUSALS[0], ANSWERS[0])
    shown = []
    response = engine._stream_document_answer(
        llm, "que vois tu dans ce pdf ?", "système", on_token=shown.append,
        on_thinking_token=print, on_thinking_complete=print,
    )
    assert response == ANSWERS[0] and "".join(shown) == ANSWERS[0]
    first, retry = llm.calls
    assert first["prompt"] == "que vois tu dans ce pdf ?"
    assert retry["prompt"] == ai_engine._ATTACHMENT_REMINDER
    assert "on_thinking_token" not in retry and "on_thinking_complete" not in retry
    assert "on_thinking_token" in first
    # Le rappel suit le refus coupé, qui reste dans l'historique du modèle
    question, refusal, reminder, answer = llm.conversation_history
    assert question["content"] == "que vois tu dans ce pdf ?"
    assert "besoin d'accéder" in refusal["content"] and "Veuillez" not in refusal["content"]
    assert reminder["content"] == ai_engine._ATTACHMENT_REMINDER
    assert answer["content"] == ANSWERS[0]


def test_correct_answer_is_generated_once(engine):
    llm = _FakeLLM(ANSWERS[0])
    shown = []
    response = engine._stream_document_answer(
        llm, "que vois tu ?", "système", on_token=shown.append
    )
    assert response == ANSWERS[0] and "".join(shown) == ANSWERS[0] and len(llm.calls) == 1


def test_no_new_attempt_after_a_stop_request(engine):
    llm = _FakeLLM(REFUSALS[0], ANSWERS[0])
    shown = []
    response = engine._stream_document_answer(
        llm, "que vois tu ?", "système", on_token=shown.append,
        is_interrupted_callback=lambda: True,
    )
    assert response == "" and shown == [] and len(llm.calls) == 1


class _OllamaStream:
    """Réponse HTTP en streaming d'Ollama (/api/chat) pour une réponse scriptée."""

    status_code = 200

    def __init__(self, reply):
        self.lines = [json.dumps({"message": {"content": t}}).encode() for t in _tokens(reply)]
        self.lines.append(json.dumps({"message": {"content": ""}, "done": True}).encode())

    def __enter__(self):
        return self

    def __exit__(self, *_exc):
        return False

    def iter_lines(self):
        yield from self.lines


def test_process_query_stream_asks_again_after_a_refusal(monkeypatch):
    """Vrai moteur et vrai LocalLLM, Ollama simulé : le refus n'est jamais affiché,
    et le nouvel essai prolonge les messages du premier (Ollama en reprend le calcul)."""
    engine = AIEngine()
    llm = engine.local_ai.local_llm
    monkeypatch.setattr(llm, "is_ollama_available", True)
    name = "fiche de sécurité.pdf"
    engine.local_ai.conversation_memory.store_document_content(
        name, "La thiourée est un solide blanc. " * 20
    )
    engine.set_visible_documents({name})  # joint au message, comme dans le GUI
    replies, sent = [REFUSALS[0], ANSWERS[0]], []

    def fake_post(_url, **kwargs):
        sent.append(kwargs["json"]["messages"])
        return _OllamaStream(replies.pop(0))

    monkeypatch.setattr(local_llm, "_resilient_post", fake_post)
    shown = []
    response = engine.process_query_stream("que vois tu dans ce pdf ?", on_token=shown.append)
    assert response == ANSWERS[0] and "".join(shown) == ANSWERS[0]
    first, retry = sent
    assert "La thiourée est un solide blanc." in first[0]["content"]
    assert retry[:len(first)] == first
    assert retry[-1] == {"role": "user", "content": ai_engine._ATTACHMENT_REMINDER}


def test_conversation_recap_shows_only_what_the_user_saw(monkeypatch):
    """« De quoi on a parlé ? » : le refus coupé et le rappel restent dans l'historique
    du modèle, mais le récapitulatif ne montre que la question et la réponse affichée."""
    engine = AIEngine()
    llm = engine.local_ai.local_llm
    monkeypatch.setattr(llm, "is_ollama_available", True)
    llm.conversation_history[:] = [
        {"role": "user", "content": "que vois tu dans ce pdf ?"},
        {"role": "assistant", "content": REFUSALS[1]},
        {"role": "user", "content": ai_engine._ATTACHMENT_REMINDER},
        {"role": "assistant", "content": ANSWERS[0]},
    ]
    system_prompts = []

    def scripted(prompt, system_prompt=None, on_token=None, **_kwargs):
        system_prompts.append(system_prompt)
        return "Nous avons parlé de ton PDF sur la cybersécurité."

    monkeypatch.setattr(llm, "generate_stream", scripted)
    engine.process_query_stream("de quoi on a parlé ?", on_token=lambda _token: None)
    recap = system_prompts[0].split("Voici l'historique complet de cette conversation :")[1]
    assert "- Utilisateur : que vois tu dans ce pdf ?" in recap
    assert "questionnaire corrigé" in recap
    assert "besoin d'accéder" not in recap and ai_engine._ATTACHMENT_REMINDER not in recap
