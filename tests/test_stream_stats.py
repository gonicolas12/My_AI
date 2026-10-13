"""
Tests du relevé de fin de flux d'Ollama (tokens/s, décisions D15 et D17)

L'orchestrateur (réponses avec outils) et LocalLLM (réponses sans outils)
gardent, en lecture seule, eval_count et eval_duration du dernier fragment
d'un flux : le service de chat en tire ses tokens/s. Les requêtes à Ollama
n'en dépendent pas. Aucun vrai Ollama n'est appelé ici.
"""

# Les flux testés sont des méthodes privées
# pylint: disable=protected-access

import json

import pytest

from core import chat_orchestrator
from core.chat_orchestrator import ChatOrchestrator
from models import local_llm
from models.local_llm import LocalLLM

STATS = {"eval_count": 146, "eval_duration": 2_000_000_000}


class _Stream:
    """Réponse streamée d'Ollama : texte en morceaux, puis le fragment de fin."""

    status_code = 200

    def __init__(self, text, done=True):
        self.lines = [json.dumps({"message": {"content": text[i:i + 8]}, "done": False}).encode()
                      for i in range(0, len(text), 8)]
        if done:
            self.lines.append(json.dumps({"message": {"content": ""}, "done": True,
                                          **STATS}).encode())

    def __enter__(self):
        return self

    def __exit__(self, *_exc):
        return False

    def iter_lines(self):
        yield from self.lines


@pytest.fixture(name="ollama")
def _ollama(monkeypatch):
    """Flux servis à l'orchestrateur et à LocalLLM ; requêtes gardées."""
    state = {"done": True, "requests": []}

    def post(_url, **kwargs):
        state["requests"].append(kwargs["json"])
        return _Stream("Une réponse assez longue pour plusieurs morceaux.", done=state["done"])

    monkeypatch.setattr(chat_orchestrator, "_resilient_post", post)
    monkeypatch.setattr(local_llm, "_resilient_post", post)
    return state


def _llm():
    """LocalLLM sans __init__ (aucun appel à Ollama)."""
    llm = LocalLLM.__new__(LocalLLM)
    llm.is_ollama_available = True
    llm.model = "my_ai"
    llm.ollama_url = "http://127.0.0.1:9/api/generate"
    llm.chat_url = "http://127.0.0.1:9/api/chat"
    llm.timeout = 1
    llm.gen_temperature = 0.7
    llm.gen_num_ctx = 32768
    llm.conversation_history = []
    llm.max_history_length = 200
    llm._keep_recent_messages = 20
    llm._conversation_summary = ""
    return llm


def test_local_llm_keeps_the_last_stream_stats(ollama):
    llm = _llm()
    assert llm.last_stream_stats is None
    answer = llm.generate_stream("Bonjour", on_token=lambda _token: True)

    assert answer.startswith("Une réponse")
    stats = llm.last_stream_stats
    assert (stats["eval_count"], stats["eval_duration"]) == (146, 2_000_000_000)
    assert stats["at"] > 0
    # Lecture seule : la requête envoyée à Ollama ne change pas
    assert "eval_count" not in json.dumps(ollama["requests"][0])


def test_an_interrupted_stream_leaves_no_stats(ollama):
    ollama["done"] = False  # flux coupé avant son fragment de fin
    llm = _llm()
    llm.generate_stream("Bonjour", on_token=lambda _token: True)
    assert llm.last_stream_stats is None


def test_orchestrator_keeps_the_stats_of_its_streams(ollama):
    llm, orchestrator = _llm(), ChatOrchestrator()
    result = orchestrator._call_ollama_smart_stream(
        llm, [{"role": "user", "content": "Bonjour"}], [], on_token=lambda _token: True)
    assert result and result["content"].startswith("Une réponse")
    assert orchestrator.last_stream_stats["eval_count"] == 146

    orchestrator.last_stream_stats = None
    orchestrator._synthesis_pass(
        llm, [{"role": "user", "content": "Bonjour"}], "Bonjour", [],
        lambda _token: True, None, None, None, False,
    )
    assert orchestrator.last_stream_stats["eval_duration"] == 2_000_000_000
    assert len(ollama["requests"]) == 2
