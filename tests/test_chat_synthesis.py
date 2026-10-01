"""
Tests de la synthèse de l'orchestrateur Chat (core/chat_orchestrator.py).

Régression d'un bug observé en usage réel : sur « tu vois quoi dans mon
dossier téléchargements ? », la synthèse commençait par « Je n'ai pas accès à
mon scratchpad interne… ». Elle n'était validée qu'une fois affichée : la
relance se streamait alors sous la première réponse, et deux réponses
s'enchaînaient dans la même bulle.

Le flux HTTP d'Ollama est simulé en remplaçant ``_resilient_post``.
"""

import json

import pytest

import core.chat_orchestrator as chat_orchestrator
from core.chat_orchestrator import (
    SYNTHESIS_HEAD_CHARS,
    _SYNTHESIS_RETRY_NOTE,
    ChatOrchestrator,
)
from core.modelfile import with_modelfile

_QUESTION = "tu vois quoi dans mon dossier téléchargements ?"
_LISTING = (
    "C:\\Users\\me\\Downloads\\CDE FREYSSINET.pdf\n"
    "C:\\Users\\me\\Downloads\\OllamaSetup.exe"
)
_NUDGE = "Vérifie ton <scratchpad>. S'il te reste de VRAIES actions techniques…"

# Début de la synthèse fautive, tel qu'affiché à l'utilisateur
_OFF_TRACK = (
    "Je n'ai pas accès à mon scratchpad interne ni aux éléments de réflexion "
    "qui m'ont précédé, car ils sont conçus pour rester invisibles et ne font "
    "pas partie de mes réponses directes. Cependant, j'ai bien listé ton dossier."
)
_ANSWER = (
    "J'ai listé ton dossier Téléchargements. Voici ce qu'il contient :\n\n"
    "- 📄 **CDE FREYSSINET.pdf** : un document PDF ;\n"
    "- ⚙️ **OllamaSetup.exe** : l'installeur d'Ollama.\n\n"
    "Veux-tu que j'ouvre le PDF pour t'en faire un résumé ?"
)


class _OllamaStream:
    """Réponse streamée d'Ollama : une ligne JSON par morceau de texte."""

    status_code = 200

    def __init__(self, text, chunk=12):
        pieces = [text[i:i + chunk] for i in range(0, len(text), chunk)]
        self.lines = [
            json.dumps({"message": {"content": piece}, "done": False}).encode()
            for piece in pieces
        ] + [json.dumps({"message": {"content": ""}, "done": True}).encode()]
        self.lines_read = 0

    def __enter__(self):
        return self

    def __exit__(self, *_exc):
        return False

    def iter_lines(self):
        for line in self.lines:
            self.lines_read += 1
            yield line


class _Ollama:
    """Sert des réponses écrites à l'avance et garde les requêtes reçues."""

    def __init__(self):
        self.replies = []
        self.requests = []
        self.streams = []

    def post(self, _url, **kwargs):
        self.requests.append(kwargs["json"])
        stream = _OllamaStream(self.replies.pop(0))
        self.streams.append(stream)
        return stream


@pytest.fixture(name="ollama")
def _ollama(monkeypatch):
    server = _Ollama()
    monkeypatch.setattr(chat_orchestrator, "_resilient_post", server.post)
    return server


class _LLM:
    """Ce que l'orchestrateur lit de LocalLLM, sans Ollama."""

    is_ollama_available = True
    model = "fake"
    chat_url = "http://127.0.0.1:9/api/chat"
    timeout = 1
    gen_temperature = 0.0
    gen_num_ctx = 2048

    def __init__(self):
        self.conversation_history = []

    def add_to_history(self, role, content):
        self.conversation_history.append({"role": role, "content": content})

    @staticmethod
    def parse_text_tool_call(_text, _names):
        return None

    @staticmethod
    def generate_stream(on_token=None, **_kwargs):
        # Relance générique sans outils : ne doit plus suivre une synthèse
        if on_token:
            on_token("[relance sans outils]")
        return "[relance sans outils]"

    def replies(self):
        return [m["content"] for m in self.conversation_history if m["role"] == "assistant"]


def _synthesize(ollama, *replies, **options):
    """Synthèse après un list_directory, suivie de la relance de la boucle."""
    ollama.replies.extend(replies)
    llm, shown = _LLM(), []
    messages = [
        {"role": "system", "content": "système"},
        {"role": "user", "content": _QUESTION},
        {"role": "assistant", "content": "", "tool_calls": [
            {"function": {"name": "list_directory", "arguments": {}}}
        ]},
        {"role": "tool", "content": _LISTING},
        {"role": "user", "content": _NUDGE},
    ]
    result = ChatOrchestrator()._stream_synthesis(
        messages=messages,
        user_input=_QUESTION,
        llm=llm,
        on_token=shown.append,
        is_interrupted_callback=None,
        tool_calls_log=[{"tool": "list_directory"}],
        loop_start=2,
        **options,
    )
    return result, shown, llm


def test_downloads_question_gets_a_single_answer(ollama):
    """Scénario réel : outil, synthèse fautive, puis une seule réponse à l'écran."""
    ollama.replies.extend([_OFF_TRACK, _ANSWER])
    turns = [
        {"name": "list_directory", "arguments": {"path": "C:\\Users\\me\\Downloads"}},
        "Ton dossier contient deux fichiers.",  # tour 2 : texte → synthèse
    ]

    def fake_turn(**_kwargs):
        turn = turns.pop(0)
        if isinstance(turn, dict):
            return {"content": "", "tool_calls": [{"function": turn}], "streamed": False}
        return {"content": turn, "tool_calls": [], "streamed": True}

    orchestrator = ChatOrchestrator()
    orchestrator._call_ollama_smart_stream = fake_turn
    llm, shown = _LLM(), []
    result = orchestrator.run(
        user_input=_QUESTION,
        tools=[{"type": "function", "function": {"name": "list_directory"}}],
        tool_executor=lambda _name, _arguments: _LISTING,
        llm=llm,
        system_prompt="système",
        on_token=shown.append,
    )

    assert result == _ANSWER
    assert "".join(shown) == _ANSWER
    assert llm.replies() == [_ANSWER]
    # La synthèse fautive a été coupée avant la fin de sa génération
    assert ollama.streams[0].lines_read < len(ollama.streams[0].lines)
    # La seconde synthèse garde les résultats de l'outil
    retry = ollama.requests[1]["messages"]
    assert {"role": "tool", "content": _LISTING} in retry
    assert retry[-1]["content"].endswith(_SYNTHESIS_RETRY_NOTE)


def test_synthesis_context_drops_the_loop_instructions(ollama):
    """Le scratchpad et ses relances n'existent plus pour la synthèse."""
    _synthesize(ollama, _ANSWER)

    messages = ollama.requests[0]["messages"]
    assert [m["role"] for m in messages] == ["system", "user", "assistant", "tool", "user"]
    assert all("scratchpad" not in m["content"].lower() for m in messages)
    assert messages[-1]["content"].endswith(_QUESTION)


def test_synthesis_keeps_the_modelfile_identity(ollama):
    """Sans le Modelfile, My_AI se présentait comme « une IA qui synthétise »."""
    _synthesize(ollama, _ANSWER)

    system = ollama.requests[0]["messages"][0]["content"]
    assert system.startswith(with_modelfile(tools=False))
    assert "Tu interviens en bout de processus" in system
    assert "## Outils" not in system


def test_valid_synthesis_is_shown_once(ollama):
    result, shown, llm = _synthesize(ollama, _ANSWER)

    assert result == _ANSWER
    assert "".join(shown) == _ANSWER
    assert len(ollama.requests) == 1
    # Le début n'est transmis qu'une fois validé, d'un seul bloc
    assert len(shown[0]) >= SYNTHESIS_HEAD_CHARS
    assert llm.replies() == [_ANSWER]


def test_short_synthesis_is_validated_whole(ollama):
    short = "Ton dossier contient deux fichiers."
    result, shown, _llm = _synthesize(ollama, short)

    assert result == short
    assert shown == [short]


def test_caveat_after_the_head_does_not_restart_the_answer(ollama):
    """Une fois affichée, la synthèse n'est jamais suivie d'une seconde."""
    with_caveat = _ANSWER + "\n\nNB : je n'ai pas accès au contenu du PDF sans l'ouvrir."
    result, shown, _llm = _synthesize(ollama, with_caveat)

    assert result == with_caveat
    assert "".join(shown) == with_caveat
    assert len(ollama.requests) == 1


def test_empty_synthesis_is_redone_without_thinking(ollama):
    """La réflexion avait consommé tout le budget : aucun texte, et le moteur
    retombait sur une génération privée des résultats de l'outil."""
    result, shown, llm = _synthesize(
        ollama, "", _ANSWER, on_thinking_token=lambda _token: None
    )

    assert result == _ANSWER
    assert "".join(shown) == _ANSWER
    assert [request["think"] for request in ollama.requests] == [True, False]
    assert {"role": "tool", "content": _LISTING} in ollama.requests[1]["messages"]
    assert llm.replies() == [_ANSWER]


def test_second_synthesis_is_shown_as_is(ollama):
    """Au plus une relance : son texte s'affiche même s'il reste imparfait."""
    result, shown, llm = _synthesize(ollama, _OFF_TRACK, _OFF_TRACK)

    assert result == _OFF_TRACK
    assert "".join(shown) == _OFF_TRACK
    assert len(ollama.requests) == 2
    assert llm.replies() == [_OFF_TRACK]
