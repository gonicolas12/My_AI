"""
Tests de la fenêtre de contexte unique de my_ai (llm.local.num_ctx).

Chaque étape demandait sa propre fenêtre à Ollama : 4 096 pour la
planification, 8 192 pour la synthèse, 16 384 pour la réponse, 32 768 pour le
résumé glissant et le mode VS Code, celle du Modelfile pour le préchauffage.
Ollama rechargeait alors le modèle à chaque changement (≈ 3,5 s sur un GPU
intégré) et perdait la conversation déjà lue. Aucun vrai Ollama n'est appelé
ici : les requêtes sont interceptées.
"""

import json
from types import SimpleNamespace

import pytest

import core.chat_orchestrator as chat_orchestrator
import models.local_llm as local_llm
from core.chat_orchestrator import COMPACT_THRESHOLD, ChatOrchestrator
from models.local_llm import LocalLLM
from relay.relay_server import _resolve_ollama_for_agentic

WINDOW = 32768


class _Response:
    """Réponse d'Ollama, streamée ou non, qui convient à chaque étape."""

    status_code = 200

    def __enter__(self):
        return self

    def __exit__(self, *_exc):
        return False

    @staticmethod
    def json():
        return {"message": {"content": "Résumé des échanges."}, "done": True}

    @staticmethod
    def iter_lines():
        yield json.dumps({"message": {"content": "1. Chercher la météo"}, "done": False}).encode()
        yield json.dumps({"message": {"content": ""}, "done": True}).encode()


@pytest.fixture(name="windows")
def _windows(monkeypatch):
    """Fenêtres de contexte demandées à Ollama, requête par requête."""
    sent = []

    def fake_post(_url, **kwargs):
        sent.append(kwargs["json"]["options"].get("num_ctx"))
        return _Response()

    monkeypatch.setattr(chat_orchestrator, "_resilient_post", fake_post)
    monkeypatch.setattr(local_llm, "_resilient_post", fake_post)
    monkeypatch.setattr(local_llm.requests, "post", fake_post)  # préchauffage
    return sent


def _llm():
    """LocalLLM sans __init__ (aucun appel à Ollama), fenêtre réglée à 32k."""
    llm = LocalLLM.__new__(LocalLLM)
    llm.is_ollama_available = True
    llm.model = "my_ai"
    llm.ollama_url = "http://127.0.0.1:9/api/generate"
    llm.chat_url = "http://127.0.0.1:9/api/chat"
    llm.timeout = 1
    llm.gen_temperature = 0.7
    llm.gen_num_ctx = WINDOW
    llm.conversation_history = []
    llm.max_history_length = 200
    llm._keep_recent_messages = 20  # pylint: disable=protected-access
    llm._conversation_summary = ""  # pylint: disable=protected-access
    return llm


def _messages(count, chars=100):
    return [
        {"role": "user" if n % 2 == 0 else "assistant", "content": f"{n} " + "x" * chars}
        for n in range(count)
    ]


# pylint: disable=protected-access
def test_every_step_asks_ollama_for_the_same_window(windows):
    llm, orchestrator = _llm(), ChatOrchestrator()
    llm._warmup_model()
    llm.generate("Bonjour", save_history=False)
    orchestrator._generate_plan_stream("Cherche la météo de Paris", llm)
    orchestrator._compact_context_if_needed(
        [{"role": "system", "content": "Système"}, *_messages(COMPACT_THRESHOLD + 1),
         {"role": "user", "content": "Et donc ?"}],
        llm,
    )
    orchestrator._synthesis_pass(
        llm, [{"role": "user", "content": "Quel temps fait-il ?"}], "Quel temps fait-il ?",
        [], None, None, None, None, False,
    )
    llm.conversation_history = _messages(30)
    llm._compress_old_history()

    # Préchauffage, réponse, planification, compaction, synthèse, résumé glissant
    assert windows == [WINDOW] * 6


def test_vscode_mode_uses_the_window_of_the_app():
    """Le mode agentique de l'extension demandait 32 768 quelle que soit la
    fenêtre réglée dans ⚙️ Réglages."""
    llm = SimpleNamespace(
        chat_url="http://127.0.0.1:11434/api/chat", model="my_ai", gen_num_ctx=65536
    )
    server = SimpleNamespace(ai_engine=SimpleNamespace(local_ai=SimpleNamespace(local_llm=llm)))
    assert _resolve_ollama_for_agentic(server) == {
        "chat_url": "http://127.0.0.1:11434/api/chat", "model": "my_ai", "num_ctx": 65536,
    }


def test_rolling_summary_starts_at_half_the_window(windows):
    """Le seuil était de 24 000 tokens, quelle que soit la fenêtre, et aucun
    résumé n'avait lieu sous 100 messages : au-delà de la fenêtre, Ollama
    coupait lui-même le début de la conversation."""
    llm = _llm()
    assert llm._summary_threshold_tokens == WINDOW // 2

    llm.conversation_history = _messages(27, chars=2400)  # 16 220 tokens estimés
    llm.add_to_history("user", "Et ensuite ?")
    assert windows == []

    llm.add_to_history("assistant", "y" * 2400)  # 16 823 : seuil de 16 384 dépassé
    assert windows == [WINDOW]
    assert llm.conversation_history[0]["content"].startswith(
        "[Résumé de la conversation précédente]"
    )
    assert llm._estimate_tokens(llm.conversation_history) < llm._summary_threshold_tokens


def test_threshold_follows_the_window_set_in_settings():
    llm = _llm()
    llm.gen_num_ctx = 65536  # ⚙️ Réglages l'applique en direct à LocalLLM
    assert llm._summary_threshold_tokens == 32768


def test_long_answers_do_not_trigger_a_summary_at_every_message(windows):
    """Les 20 derniers messages étaient gardés quelle que soit leur taille :
    avec de longues réponses (du code…), ils dépassaient à eux seuls le seuil,
    et chaque nouveau message relançait un résumé, donc un appel au modèle."""
    llm = _llm()
    for _ in range(30):
        llm.add_to_history("user", "Montre-moi la suite du code.")
        llm.add_to_history("assistant", "c" * 8000)  # ≈ 2 000 tokens

    # Un résumé toutes les 4 à 5 réponses, pas un par message
    assert 1 <= len(windows) <= 8
    assert llm._estimate_tokens(llm.conversation_history) <= llm._summary_threshold_tokens
