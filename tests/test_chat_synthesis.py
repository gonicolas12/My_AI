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
    _NOT_MEMORIZED_NOTE,
    _SYNTHESIS_RETRY_NOTE,
    ChatOrchestrator,
    _claims_memory,
)
from core.modelfile import with_modelfile
from models import internet_search as ws
from utils.citations import sources_block

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
            # (réflexion, réponse) : la réflexion native arrive d'abord
            thinking, text = text if isinstance(text, tuple) else ("", text)
            self.lines = [
                json.dumps({"message": {field: value[i:i + chunk]}, "done": False}).encode()
                for field, value in (("thinking", thinking), ("content", text))
                for i in range(0, len(value), chunk)
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
    synthèse, alors qu'il figure déjà dans la conversation. La question, qui
    suit le XML, y reste."""
    ollama.replies.append(_ANSWER)
    request = (
        "Voici le xml de la mission :\n"
        + "<item><title>LOGM-80 : bases articles</title></item>\n" * 200
        + "Résume-moi la mission et ce qu'il faut faire."
    )
    messages = [dict(message) for message in _LOOP_MESSAGES]
    messages[1] = {"role": "user", "content": request}
    ChatOrchestrator()._stream_synthesis(
        messages=messages, user_input=request, llm=_LLM(), on_token=None,
        is_interrupted_callback=None, tool_calls_log=[{"tool": "list_directory"}], loop_start=2,
    )

    instructions = ollama.requests[0]["messages"][-1]["content"]
    assert instructions.endswith(
        "Résume-moi la mission et ce qu'il faut faire. (demande complète plus haut)"
    )
    assert "Voici le xml de la mission" in instructions
    assert len(instructions) < len(request)


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


_POPULATION = "cherche sur internet le nombre d'habitants sur terre"


def _search_result(*urls):
    """Résultat de web_search : sources numérotées, puis le bloc à recopier."""
    return ws.format_results(ws.SearchResponse(
        query="population mondiale", engine="DuckDuckGo",
        results=[ws.SearchResult(title=f"Source {n}", url=url, snippet="Extrait.")
                 for n, url in enumerate(urls, 1)],
    ))


def _web_search_loop(*results):
    """Boucle au moment de la synthèse : une recherche web par résultat."""
    messages = [{"role": "system", "content": "système"}, {"role": "user", "content": _POPULATION}]
    for result in results:
        messages += [
            {"role": "assistant", "content": "", "tool_calls": [
                {"function": {"name": "web_search", "arguments": {"query": "population"}}}
            ]},
            {"role": "tool", "content": result},
        ]
    return messages


def _synthesize_search(ollama, results, *replies, **options):
    """Synthèse après une ou plusieurs recherches web."""
    ollama.replies.extend(replies)
    llm, shown = _LLM(), []
    response = ChatOrchestrator()._stream_synthesis(
        messages=_web_search_loop(*results),
        user_input=_POPULATION,
        llm=llm,
        on_token=shown.append,
        is_interrupted_callback=None,
        tool_calls_log=[{"tool": "web_search"} for _ in results],
        loop_start=2,
        **options,
    )
    return response, shown, llm


def test_web_search_lists_only_the_cited_sources(ollama):
    """Comme le WebAgent : le flux est coupé au début du bloc 📚 Sources que le
    modèle recopiait, sources non citées comprises, et le bloc suit sa
    réponse, réduit aux sources qu'elle cite, numéros gardés. Avant, seul le
    modèle en décidait : prié de recopier le bloc « tel quel », il n'en
    retirait les sources non citées que s'il le voulait bien."""
    result = _search_result(*(f"https://example.org/{n}" for n in range(1, 5)))
    answer = "La population mondiale atteint 8,3 milliards [1], et croît de 0,8 % [3]."
    ollama.replies.append(f"{answer}\n\n{sources_block(result)}")
    turns = [{"name": "web_search", "arguments": {"query": "population mondiale"}}]

    def fake_turn(**_kwargs):
        return {"content": "", "tool_calls": [{"function": turns.pop(0)}], "streamed": False}

    orchestrator = ChatOrchestrator()
    orchestrator._call_ollama_smart_stream = fake_turn
    llm, shown = _LLM(), []
    response = orchestrator.run(
        user_input=_POPULATION,
        tools=[{"type": "function", "function": {"name": "web_search"}}],
        tool_executor=lambda _name, _arguments: result,
        llm=llm,
        system_prompt="système",
        on_token=shown.append,
    )

    expected = (
        f"{answer}\n\n📚 **Sources**\n"
        "[1] [Source 1](https://example.org/1)\n"
        "[3] [Source 3](https://example.org/3)"
    )
    # Rien du bloc recopié n'a paru, pas même son début, en morceaux de 12 caractères
    assert "".join(shown) == expected
    assert response == expected
    assert llm.replies() == [expected]
    # Flux coupé : le modèle n'a pas fini de recopier les adresses
    assert ollama.streams[0].lines_read < len(ollama.streams[0].lines)


def test_sources_drafted_in_the_thinking_do_not_stop_the_synthesis(ollama):
    """Essai réel sur my_ai : l'option « stop » d'Ollama vaut aussi pour la
    réflexion native, et un brouillon du bloc 📚 Sources l'y arrêtait, réponse
    vide, puis synthèse à part, bien plus lente. L'arrêt ne porte que sur la
    réponse, et la réflexion arrive entière."""
    result = _search_result("https://example.org/1", "https://example.org/2")
    block = sources_block(result)
    thinking = f"Je cite [1], puis je termine par le bloc :\n{block}\nC'est bon."
    answer = "La population mondiale atteint 8,3 milliards [1]."
    thoughts = []
    response, shown, _llm = _synthesize_search(
        ollama, [result], (thinking, f"{answer}\n\n{block}"),
        on_thinking_token=thoughts.append,
    )

    expected = f"{answer}\n\n📚 **Sources**\n[1] [Source 1](https://example.org/1)"
    assert response == expected and "".join(shown) == expected
    assert thinking in "".join(thoughts)
    assert len(ollama.requests) == 1  # pas de synthèse à part
    assert "stop" not in ollama.requests[0]["options"]


def test_answer_kept_whole_when_it_merely_ends_with_a_newline(ollama):
    """Une fin de ligne peut commencer le bloc : retenue, elle est rendue à la
    fin du flux quand rien ne l'a suivie (aucun bloc recopié)."""
    result = _search_result("https://example.org/1", "https://example.org/2")
    answer = (
        "La population mondiale atteint environ 8,3 milliards d'habitants en 2026 [2], "
        "avec une croissance annuelle qui ralentit nettement depuis plusieurs décennies "
        "selon les sources.\n"
    )
    assert len(answer) > SYNTHESIS_HEAD_CHARS  # affichée au fil du flux
    response, shown, _llm = _synthesize_search(ollama, [result], answer)

    expected = f"{answer}\n📚 **Sources**\n[2] [Source 2](https://example.org/2)"
    assert response == expected and "".join(shown) == expected


def _run_with_turns(turns, tool_executor):
    """run() complet, tours du modèle joués d'avance ; garde les appels reçus."""
    model_turns = []

    def fake_turn(**kwargs):
        model_turns.append(kwargs)
        return turns.pop(0)

    orchestrator = ChatOrchestrator()
    orchestrator._call_ollama_smart_stream = fake_turn
    response = orchestrator.run(
        user_input=_POPULATION,
        tools=[{"type": "function", "function": {"name": "web_search"}}],
        tool_executor=tool_executor,
        llm=_LLM(),
        system_prompt="système",
        on_token=lambda _token: None,
    )
    return response, model_turns


_EMPTY_TURN = {"content": "", "tool_calls": [], "streamed": False}


def test_empty_first_turn_is_tried_once_more(ollama):
    """Tour vide : le modèle avait écrit un appel d'outil qu'Ollama n'a pas su
    lire, et l'a jeté (my_ai, 22 octobre 2026). Rien n'a été affiché : l'appel
    est refait, et la recherche a lieu, au lieu d'un repli sans outils où le
    modèle répondait de mémoire, avec des « Sources » inventées."""
    result = _search_result(*(f"https://example.org/{n}" for n in range(1, 5)))
    answer = "La population mondiale atteint 8,3 milliards [1]."
    ollama.replies.append(answer)
    search = {"name": "web_search", "arguments": {"query": "population mondiale"}}
    searches = []

    def tool_executor(name, arguments):
        searches.append((name, arguments))
        return result

    response, model_turns = _run_with_turns(
        [dict(_EMPTY_TURN), {"content": "", "tool_calls": [{"function": search}],
                             "streamed": False}],
        tool_executor,
    )

    assert len(model_turns) == 2 and model_turns[1] == model_turns[0]  # le même appel
    assert searches == [("web_search", {"query": "population mondiale"})]
    assert response.startswith(answer)
    assert response.endswith("[1] [Source 1](https://example.org/1)")


def test_a_second_empty_turn_hands_back_to_the_engine(ollama):
    """Un seul nouvel essai : vide encore, la boucle rend la main au moteur."""
    response, model_turns = _run_with_turns(
        [dict(_EMPTY_TURN), dict(_EMPTY_TURN)], lambda _name, _arguments: ""
    )
    assert response is None and len(model_turns) == 2
    assert not ollama.requests  # ni synthèse ni autre appel


def test_several_web_searches_keep_the_model_list(ollama):
    """Deux recherches numérotent chacune leurs sources à partir de [1] : un
    [n] ne dit plus laquelle il cite, et le modèle garde la main sur sa liste."""
    first, second = _search_result("https://example.org/a"), _search_result("https://example.org/b")
    reply = f"Réponse tirée des deux recherches [1].\n\n{sources_block(first)}"
    response, shown, _llm = _synthesize_search(ollama, [first, second], reply)

    assert response == reply and "".join(shown) == reply
    assert ollama.streams[0].lines_read == len(ollama.streams[0].lines)


# ── Une information donnée en passant, après une recherche dans la mémoire ───

_LOCKER = "Le code de mon casier à la salle de sport est le 4815."
_FACTS = "Faits mémorisés :\n- [general] L'utilisateur vit à Lyon"
_NOTED = "C'est noté ! J'ai bien enregistré que ton code de casier est le **4815**. ✅"
_HONEST = ("Ton code de casier est le 4815. Si tu veux que je m'en souvienne, dis-moi "
           "simplement « retiens ça ».")


def _after_memory_search(ollama, *replies, user_input=_LOCKER, used=("search_memory",),
                         kept=False):
    """Synthèse après search_memory ; kept : ce que la mémoire a retenu du message
    (None : il demandait de retenir ou d'oublier). Rend aussi les appels à
    memory_kept."""
    ollama.replies.extend(replies)
    messages = [
        {"role": "system", "content": "système"},
        {"role": "user", "content": user_input},
        {"role": "assistant", "content": "", "tool_calls": [
            {"function": {"name": "search_memory", "arguments": {"query": "code casier"}}}
        ]},
        {"role": "tool", "content": _FACTS},
        {"role": "user", "content": _NUDGE},
    ]
    shown, asked = [], []

    def memory_kept():
        asked.append(True)
        return kept

    result = ChatOrchestrator()._stream_synthesis(
        messages=messages, user_input=user_input, llm=_LLM(), on_token=shown.append,
        is_interrupted_callback=None, tool_calls_log=[{"tool": name} for name in used],
        loop_start=2, memory_kept=None if kept is None else memory_kept,
    )
    return result, "".join(shown), asked


def test_information_given_in_passing_is_not_said_to_be_saved(ollama):
    """« Le code de mon casier… est le 4815. », sans « retiens » : rien n'est retenu
    (un code), mais après search_memory la synthèse répondait « C'est noté ! J'ai bien
    enregistré… » (my_ai : 9 fois sur 15). Ce début n'est pas affiché : la synthèse à
    part le refait, en sachant que rien n'a été enregistré."""
    result, shown, asked = _after_memory_search(ollama, _NOTED, _HONEST)

    # Rien de la première réponse n'a été affiché
    assert result == shown == _HONEST
    assert asked == [True]
    assert len(ollama.requests) == 2
    retry = ollama.requests[1]["messages"]
    assert {"role": "tool", "content": _FACTS} in retry
    assert retry[-1]["content"].endswith(_SYNTHESIS_RETRY_NOTE + _NOT_MEMORIZED_NOTE)
    assert "« retiens ça »" in _NOT_MEMORIZED_NOTE


def test_a_claim_after_a_preamble_is_caught_too(ollama):
    """Un tiers de ces affirmations venaient après « J'ai vérifié ma mémoire… » : le
    début retenu est plus long qu'à l'ordinaire."""
    late = ("J'ai vérifié ta mémoire : je n'y avais rien sur ton casier, mais je me souviens "
            "que tu vis à Lyon, que ton chat s'appelle Félix et que tu aimes le café noir. "
            "C'est une nouvelle information que j'enregistre pour toi. ✅")
    assert late.index("j'enregistre") > SYNTHESIS_HEAD_CHARS

    result, shown, _asked = _after_memory_search(ollama, late, _HONEST)

    assert result == shown == _HONEST
    assert len(ollama.requests) == 2


def test_the_claim_stays_when_the_memory_kept_something(ollama):
    """« Je suis végétarien depuis dix ans. » : lu pendant la réponse, il est retenu ;
    « C'est noté » est alors vrai, et la carte « Mémorisé » le montre."""
    result, shown, asked = _after_memory_search(
        ollama, _NOTED, user_input="Je suis végétarien depuis dix ans.", kept=True)

    assert result == shown == _NOTED
    assert asked == [True] and len(ollama.requests) == 1


@pytest.mark.parametrize("user_input, used, kept", [
    # Une question : la réponse n'est pas qu'une reprise de ce qu'il a dit
    ("Mon code de casier est le 4815, tu peux me le rappeler demain ?", ("search_memory",),
     False),
    # Une demande, sans « ? »
    ("Cherche dans ta mémoire le code de mon casier", ("search_memory",), False),
    # D'autres outils que la recherche dans la mémoire
    (_LOCKER, ("search_memory", "web_search"), False),
    # « Retiens que… » : le bloc MÉMORISATION dit déjà ce qui a été fait
    (_LOCKER, ("search_memory",), None),
])
def test_other_syntheses_keep_their_answer(ollama, user_input, used, kept):
    result, shown, asked = _after_memory_search(
        ollama, _NOTED, user_input=user_input, used=used, kept=kept)

    assert result == shown == _NOTED
    assert len(ollama.requests) == 1
    # La lecture du message n'est attendue que pour une information donnée en passant
    assert not asked


@pytest.mark.parametrize("reply", [
    "J'ai noté que ton digicode est **7B42**. 🏢",
    # Plus long que le tampon du premier tour : jugé dès ses 120 premiers caractères
    "C'est noté Camille ! 🚆 Ton train pour Bordeaux part demain à **8h12**. Veux-tu que "
    "je te prépare une petite checklist pour le voyage, ou que je vérifie la météo ?",
])
def test_a_rejected_first_turn_is_held(ollama, reply):
    """Premier tour sans outil : un début que screen refuse n'est pas affiché, et la
    réponse est seulement accumulée, à refaire par l'appelant."""
    ollama.replies.append(reply)
    shown = []

    result = ChatOrchestrator()._call_ollama_smart_stream(
        _LLM(), [{"role": "user", "content": "Le digicode est 7B42."}], [],
        on_token=shown.append, screen=lambda text: not _claims_memory(text))

    assert result["held"] and result["content"] == reply
    assert not shown and not result["streamed"]


def test_an_accepted_first_turn_is_streamed(ollama):
    ollama.replies.append(_ANSWER)
    shown = []

    result = ChatOrchestrator()._call_ollama_smart_stream(
        _LLM(), [{"role": "user", "content": _QUESTION}], [], on_token=shown.append,
        screen=lambda text: not _claims_memory(text))

    assert "".join(shown) == _ANSWER
    assert result["streamed"] and not result["held"]


@pytest.mark.parametrize("text, claims", [
    ("C'est noté ! Ton code de casier est le 4815.", True),
    ("J'ai bien noté ton code de casier : 4815.", True),
    ("Ton code de salle de sport a été enregistré ! ✅", True),
    ("Je le retiens : 4815.", True),
    ("Je vais le garder précieusement dans ma mémoire.", True),
    # my_ai, après la correction : « je peux » n'y fait pas une offre
    ("Je peux directement confirmer que j'ai mémorisé l'information : ton code est le 4815.",
     True),
    ("Je peux l'enregistrer si tu le souhaites.", False),
    ("Le code **4815** est donc maintenant bien retenu pour l'avenir.", True),
    # Réponses directes (premier tour sans outil) de my_ai
    ("Noté ! Ton vélo **Brompton vert** est un beau choix.", True),
    ("Noté : ton rendez-vous dentaire est **jeudi à 14h**. 🦷", True),
    ("Je m'apprends que ton mot de passe est Soleil2024. J'en garde cette information.",
     True),
    ("J'ai mis à jour ma mémoire avec ce fait personnel.", True),
    ("Il n'est pas encore retenu pour l'avenir.", False),
    ("Je n'ai pas enregistré ce numéro dans ta mémoire.", False),
    ("Rien n'a été enregistré pour l'instant.", False),
    ("Je ne l'ai pas noté.", False),
    ("Si tu veux que je le garde, dis-moi « retiens ça ».", False),
    ("Voici ce que j'ai noté pour tes projets : tu fais tes tests avec pytest.", False),
    ("Ton casier porte le numéro 4815 : pense à le noter quelque part !", False),
])
def test_claims_memory(text, claims):
    assert _claims_memory(text) is claims
