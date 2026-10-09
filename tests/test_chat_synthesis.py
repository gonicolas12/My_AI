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
        if isinstance(text, dict):  # appel d'outil structuré, sans texte
            self.lines = [json.dumps({
                "message": {"content": "", "tool_calls": [{"function": text}]}, "done": False,
            }).encode()]
        else:
            pieces = [text[i:i + chunk] for i in range(0, len(text), chunk)]
            self.lines = [
                json.dumps({"message": {"content": piece}, "done": False}).encode()
                for piece in pieces
            ]
        self.lines.append(json.dumps({"message": {"content": ""}, "done": True}).encode())
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


# Boucle d'outils au moment de la synthèse : un list_directory, puis la relance
_LOOP_MESSAGES = [
    {"role": "system", "content": "système"},
    {"role": "user", "content": _QUESTION},
    {"role": "assistant", "content": "", "tool_calls": [
        {"function": {"name": "list_directory", "arguments": {}}}
    ]},
    {"role": "tool", "content": _LISTING},
    {"role": "user", "content": _NUDGE},
]


def _synthesize(ollama, *replies, **options):
    """Synthèse après un list_directory, suivie de la relance de la boucle."""
    ollama.replies.extend(replies)
    llm, shown = _LLM(), []
    result = ChatOrchestrator()._stream_synthesis(
        messages=[dict(message) for message in _LOOP_MESSAGES],
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


def test_synthesis_continues_the_loop_prompt(ollama):
    """Le prompt du dernier tour est repris tel quel, outils compris, et les
    consignes de synthèse viennent en dernier : Ollama reprend la lecture là
    où la boucle l'a laissée, au lieu de relire toute la conversation (130 s
    sur une requête à deux outils, qwen3.5:4b sur GPU intégré)."""
    tools = [{"type": "function", "function": {"name": "list_directory"}}]
    _synthesize(ollama, _ANSWER, tools=tools)

    assert len(ollama.requests) == 1
    request = ollama.requests[0]
    assert request["messages"][:-1] == _LOOP_MESSAGES
    assert request["tools"] == tools
    instructions = request["messages"][-1]
    assert instructions["role"] == "user"
    assert "Tu interviens en bout de processus" in instructions["content"]
    assert instructions["content"].endswith(_QUESTION)


def test_long_request_is_only_recalled_in_the_synthesis(ollama):
    """Le XML d'un ticket aurait été recopié en entier dans la demande de
    synthèse, alors qu'il figure déjà dans la conversation."""
    ollama.replies.append(_ANSWER)
    xml = "<item><title>LOGM-80 : bases articles</title></item>\n" * 200
    messages = [dict(message) for message in _LOOP_MESSAGES]
    messages[1] = {"role": "user", "content": xml}
    ChatOrchestrator()._stream_synthesis(
        messages=messages, user_input=xml, llm=_LLM(), on_token=None,
        is_interrupted_callback=None, tool_calls_log=[{"tool": "list_directory"}], loop_start=2,
    )

    instructions = ollama.requests[0]["messages"][-1]["content"]
    assert instructions.endswith("… (demande complète plus haut)")
    assert len(instructions) < len(xml)


def test_synthesis_citing_the_loop_falls_back(ollama):
    """Dans la foulée de la boucle, le modèle en voit encore les consignes :
    une réponse qui parle de son scratchpad n'est pas affichée, la synthèse à
    part la remplace."""
    citing = (
        "D'après mon scratchpad, j'ai bien listé ton dossier Téléchargements : il "
        "contient un PDF et l'installeur d'Ollama. Veux-tu que j'ouvre le PDF pour toi ?"
    )
    result, shown, llm = _synthesize(ollama, citing, _ANSWER)

    assert result == _ANSWER
    assert "".join(shown) == _ANSWER
    assert len(ollama.requests) == 2
    assert llm.replies() == [_ANSWER]


def test_tool_call_instead_of_the_synthesis_falls_back(ollama):
    """Les outils restent dans la requête, pour garder le même début de
    prompt : un appel d'outil sans texte mène à la synthèse à part, qui n'en
    propose aucun."""
    tools = [{"type": "function", "function": {"name": "list_directory"}}]
    result, shown, _llm = _synthesize(
        ollama, {"name": "list_directory", "arguments": {}}, _ANSWER, tools=tools
    )

    assert result == _ANSWER
    assert "".join(shown) == _ANSWER
    assert "tools" not in ollama.requests[1]


def test_fallback_synthesis_drops_the_loop_instructions(ollama):
    """La synthèse à part n'a ni scratchpad ni relances de la boucle."""
    _synthesize(ollama, _OFF_TRACK, _ANSWER)

    messages = ollama.requests[1]["messages"]
    assert [m["role"] for m in messages] == ["system", "user", "assistant", "tool", "user"]
    assert all("scratchpad" not in m["content"].lower() for m in messages)
    assert _QUESTION in messages[-1]["content"]


def test_synthesis_keeps_the_modelfile_identity(ollama):
    """Sans le Modelfile, My_AI se présentait comme « une IA qui synthétise »."""
    _synthesize(ollama, _OFF_TRACK, _ANSWER)

    # Dans la foulée de la boucle : son message système, qui porte le Modelfile
    assert ollama.requests[0]["messages"][0] == _LOOP_MESSAGES[0]
    # Synthèse à part : le Modelfile, sans « ## Outils »
    system = ollama.requests[1]["messages"][0]["content"]
    assert system.startswith(with_modelfile(tools=False))
    assert "Tu interviens en bout de processus" in system
    assert "## Outils" not in system


def test_fallback_synthesis_keeps_the_answer_context(ollama):
    """Les faits de la fenêtre Mémoire n'étaient que dans le prompt de la
    boucle : la synthèse à part, qui le remplace, répondait sans eux. Dans la
    foulée de la boucle, ils restent dans son message système
    (test_memory_chat)."""
    facts = "\n\nFAITS UTILISATEUR :\n[Base de connaissances]\n- [general] Mon chat s'appelle Félix"
    _synthesize(ollama, _OFF_TRACK, _ANSWER, answer_context=facts)

    system = ollama.requests[1]["messages"][0]["content"]
    assert system.startswith(with_modelfile(tools=False))
    assert system.endswith(facts)


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


def test_enough_search_results_go_straight_to_the_synthesis(ollama):
    """Recherche web suffisante : la synthèse suit l'outil, sans tour de plus.

    Ce tour sans outils rédigeait une réponse complète, jamais affichée, que
    la synthèse refaisait : sur « cherche les meilleures marques de voiture »,
    165 s de génération perdues sur 375 (qwen3.5:4b sur iGPU).
    """
    ollama.replies.append(_ANSWER)
    turns = [{"name": "web_search", "arguments": {"query": "marques de voitures fiables"}}]
    model_turns = []

    def fake_turn(**kwargs):
        model_turns.append(kwargs)
        return {"content": "", "tool_calls": [{"function": turns.pop(0)}], "streamed": False}

    orchestrator = ChatOrchestrator()
    orchestrator._call_ollama_smart_stream = fake_turn
    llm, shown = _LLM(), []
    result = orchestrator.run(
        user_input="cherche les marques de voitures les plus fiables",
        tools=[{"type": "function", "function": {"name": "web_search"}}],
        tool_executor=lambda _name, _arguments: "Résultats de recherche web " + "x" * 2000,
        llm=llm,
        system_prompt="système",
        on_token=shown.append,
    )

    assert result == _ANSWER
    assert "".join(shown) == _ANSWER
    assert len(model_turns) == 1  # le tour qui a appelé la recherche
    assert len(ollama.requests) == 1  # puis la synthèse, une fois
    synthesis = ollama.requests[0]["messages"]
    assert {"role": "tool", "content": "Résultats de recherche web " + "x" * 2000} in synthesis
    assert not any("STOP" in str(m.get("content", "")) for m in synthesis)
