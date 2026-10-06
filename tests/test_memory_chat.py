"""
Tests de la mémoire dans le chat (core/ai_engine.py, core/chat_orchestrator.py).

Régressions observées en usage réel :
  - « retiens que… » n'enregistrait rien : le modèle répondait « c'est noté »
    (le Modelfile lui annonce une mémoire longue durée), mais aucun code
    n'écrivait dans la base de faits ;
  - dès qu'un outil était appelé (search_memory, typiquement), la synthèse
    remplaçait le prompt de la boucle et perdait les faits de la fenêtre
    Mémoire : « Cherche dans ta mémoire comment s'appelle mon chat » finissait
    sur « je n'ai rien trouvé » alors que le fait était connu ;
  - les réponses sans outils gardaient la section « ## Outils » du Modelfile.

Le vrai AIEngine.process_query_stream et le vrai ChatOrchestrator tournent
avec un faux Ollama (_resilient_post remplacé) et une base de faits temporaire.
"""

import asyncio
import json
import logging
import types

import pytest

import core.chat_orchestrator as chat_orchestrator
from core.ai_engine import AIEngine
from core.chat_orchestrator import ChatOrchestrator
from core.knowledge_base_manager import KnowledgeBaseManager
from core.modelfile import with_modelfile
from models.custom_ai_model import CustomAIModel

_IDENTITY = with_modelfile(tools=False)[:300]
_NO_RESULT = "Aucun résultat dans la mémoire (faits mémorisés et documents indexés)."


def _tool(name):
    return {"type": "function", "function": {
        "name": name, "description": name,
        "parameters": {"type": "object", "properties": {}},
    }}


_TOOLS = [_tool(name) for name in ("search_memory", "remember_fact", "web_search")]


class _OllamaStream:
    """Réponse streamée d'Ollama : texte, ou appel d'outil structuré (dict)."""

    status_code = 200

    def __init__(self, reply):
        if isinstance(reply, dict):
            message = {"content": "", "tool_calls": [{"function": reply}]}
        else:
            message = {"content": reply}
        self.lines = [
            json.dumps({"message": message, "done": False}).encode(),
            json.dumps({"message": {"content": ""}, "done": True}).encode(),
        ]

    def __enter__(self):
        return self

    def __exit__(self, *_exc):
        return False

    def iter_lines(self):
        yield from self.lines


class _Ollama:
    """Sert des réponses écrites à l'avance et garde les requêtes reçues."""

    def __init__(self):
        self.replies = []
        self.requests = []

    def post(self, _url, **kwargs):
        self.requests.append(kwargs["json"])
        return _OllamaStream(self.replies.pop(0))

    def systems(self):
        return [request["messages"][0]["content"] for request in self.requests]


@pytest.fixture(name="ollama")
def _ollama(monkeypatch):
    server = _Ollama()
    monkeypatch.setattr(chat_orchestrator, "_resilient_post", server.post)
    return server


@pytest.fixture(name="kb")
def _kb(tmp_path):
    kb = KnowledgeBaseManager(db_path=str(tmp_path / "facts.db"))
    yield kb
    kb.close()


class _LLM:
    """Ce que le moteur et l'orchestrateur lisent de LocalLLM, sans Ollama."""

    is_ollama_available = True
    model = "my_ai"
    chat_url = "http://127.0.0.1:9/api/chat"
    timeout = 1
    gen_temperature = 0.0
    gen_num_ctx = 2048

    def __init__(self):
        self.conversation_history = []
        # Prompts système et messages de generate_stream (voies sans outils)
        self.streamed_systems = []
        self.streamed_prompts = []

    def add_to_history(self, role, content):
        self.conversation_history.append({"role": role, "content": content})

    @staticmethod
    def parse_text_tool_call(_text, _names):
        return None

    def generate_stream(self, prompt, system_prompt=None, on_token=None, **_kwargs):
        self.streamed_systems.append(system_prompt)
        self.streamed_prompts.append(prompt)
        if on_token:
            on_token("Réponse.")
        return "Réponse."


def _engine(kb, tool_result=_NO_RESULT):
    """AIEngine sans __init__ : ni Ollama, ni ChromaDB, ni modèles."""
    engine = AIEngine.__new__(AIEngine)
    engine.logger = logging.getLogger(__name__)
    engine.language_detector = None
    engine.knowledge_base = kb
    engine.session_manager = None
    engine.get_folder_indexer = lambda: None
    engine._visible_documents = None
    engine._attached_documents = {}
    engine.local_ai = types.SimpleNamespace(
        local_llm=_LLM(),
        conversation_memory=types.SimpleNamespace(stored_documents={}, document_order=[]),
    )
    engine.conversation_manager = types.SimpleNamespace(get_recent_history=lambda: [])
    engine.file_manager = types.SimpleNamespace(get_timestamp=lambda: "2026-10-05")
    engine.mcp_manager = types.SimpleNamespace(
        get_ollama_tools=lambda: list(_TOOLS),
        execute_tool_sync=lambda _name, _arguments: tool_result,
    )
    engine._chat_orchestrator = ChatOrchestrator()
    return engine


def _tool_names(request):
    return [tool["function"]["name"] for tool in request.get("tools", [])]


# ── « Retiens que… » ────────────────────────────────────────────────────────


def test_remember_request_is_saved_and_confirmed(kb, ollama):
    engine, calls = _engine(kb), []

    engine.process_query_stream(
        "Retiens que mon chat s'appelle Félix",
        on_token=lambda _token: None,
        on_tool_call=lambda name, arguments: calls.append((name, arguments)),
    )

    fact = kb.get_all_facts()[0]
    assert (fact["value"], fact["source"]) == ("mon chat s'appelle Félix", "conversation")
    # Signalé au GUI comme un appel d'outil (indicateur « 🧠 Mémorisé »)
    assert calls == [("remember_fact", {"fact": "mon chat s'appelle Félix"})]
    # Rien d'autre à faire que confirmer : une génération, sans outils. Avec
    # eux, le vrai modèle rappelait remember_fact, puis une synthèse suivait.
    assert not ollama.requests
    system = engine.local_ai.local_llm.streamed_systems[0]
    assert system.startswith(_IDENTITY)
    assert "## Outils" not in system
    assert "MÉMORISATION" in system
    # « Réponds au reste de son message s'il y en a un » : le modèle cherchait
    # un reste, et ajoutait d'autres faits, voire du code
    assert "Son message ne demande rien d'autre : ta réponse se limite à cette confirmation." in system


def test_remember_request_with_a_question_keeps_the_tools(kb, ollama):
    ollama.replies.append("C'est noté ! Pour la météo, je cherche…")
    engine = _engine(kb)

    engine.process_query_stream(
        "Retiens que mon chat s'appelle Félix. Quel temps fait-il à Toulouse ?",
        on_token=lambda _token: None,
    )

    assert [fact["value"] for fact in kb.get_all_facts()] == ["mon chat s'appelle Félix"]
    request = ollama.requests[0]
    assert "MÉMORISATION" in request["messages"][0]["content"]
    assert ", puis réponds au reste de son message." in request["messages"][0]["content"]
    # Déjà enregistré : l'outil n'est pas proposé, il le doublerait
    assert _tool_names(request) == ["search_memory", "web_search"]


def test_conversational_remember_request_is_saved(kb, ollama):
    """« Merci, … » est conversationnel : aucun outil, le filet suffit."""
    engine = _engine(kb)

    engine.process_query_stream("Merci, retiens que je préfère le thé", on_token=lambda _t: None)

    assert [fact["value"] for fact in kb.get_all_facts()] == ["je préfère le thé"]
    assert not ollama.requests
    system = engine.local_ai.local_llm.streamed_systems[0]
    assert system.startswith(_IDENTITY)
    assert "## Outils" not in system
    assert "ta mémoire persistante : L'utilisateur préfère le thé." in system


def test_other_messages_save_nothing(kb, ollama):
    ollama.replies.append("Ah, mince !")
    engine, calls = _engine(kb), []

    engine.process_query_stream(
        "Je retiens que le projet est en retard",
        on_token=lambda _token: None,
        on_tool_call=lambda name, arguments: calls.append(name),
    )

    assert kb.get_all_facts() == []
    assert calls == []
    assert "remember_fact" in _tool_names(ollama.requests[0])


def test_remember_request_is_confirmed_in_the_second_person(kb):
    """« retiens que je suis nicolas gouy » était confirmé par « C'est noté :
    je suis Nicolas Gouy », et « qui je suis ? » répondu « Je suis Nicolas Gouy »."""
    engine = _engine(kb)

    engine.process_query_stream("retiens que je suis nicolas gouy", on_token=lambda _t: None)

    system = engine.local_ai.local_llm.streamed_systems[0]
    # Plus aucune phrase à la première personne à recopier
    assert "je suis nicolas gouy" not in system
    assert "- [general] L'utilisateur est nicolas gouy" in system
    assert "ta mémoire persistante : L'utilisateur est nicolas gouy." in system
    # La phrase exacte à dire, plutôt qu'un exemple à trous (« tu es X »)
    assert "(par exemple : « C'est noté : tu es nicolas gouy. »)" in system
    assert " X " not in system


def test_rules_carry_no_example_names(kb):
    """Les règles citaient « Je m'appelle Jarvis » et « Tu t'appelles Nicolas » :
    recopiés, ces exemples donnaient un nom que personne n'avait demandé."""
    kb.add_fact("general", key="je m'appelle Sophie", value="je m'appelle Sophie")
    engine = _engine(kb)

    engine.process_query_stream("Comment tu t'appelles ?", on_token=lambda _t: None)

    system = engine.local_ai.local_llm.streamed_systems[0]
    assert "L'utilisateur s'appelle Sophie" in system
    assert "Jarvis" not in system
    assert "Nicolas" not in system.split("## Auteur du projet")[0]  # hors section auteur


def test_instruction_for_the_assistant_is_confirmed_in_the_first_person(kb):
    """« Retiens que tu t'appelles Jarvis » était confirmé par « C'est noté :
    tu t'appelles Jarvis », et « comment tu t'appelles ? » répondu « My_AI »."""
    engine = _engine(kb)

    engine.process_query_stream("Retiens que tu t'appelles Jarvis", on_token=lambda _t: None)

    system = engine.local_ai.local_llm.streamed_systems[0]
    assert "Sur l'utilisateur :" not in system  # aucun fait sur lui
    assert "Consignes de l'utilisateur pour toi (prioritaires" in system
    assert "- [general] Tu t'appelles Jarvis" in system
    assert "tu viens d'enregistrer cette consigne pour toi" in system
    # La phrase exacte, pas un exemple à trous que le modèle recopiait (« je ferai X »)
    assert "(par exemple : « C'est noté : je m'appelle Jarvis. »)" in system
    assert " X " not in system


def _detecting(engine, code):
    """Détecteur de langue qui conclut toujours à `code`."""
    engine.language_detector = types.SimpleNamespace(detect=lambda _text: code)
    return engine


def test_english_instruction_is_confirmed_in_english(kb):
    """Une consigne écrite en anglais n'avait pas de phrase toute faite :
    le modèle devait seul passer de « you » à « I ». Il la traduisait ensuite :
    « Noté : je dois toujours terminer mes réponses par… »."""
    engine = _detecting(_engine(kb), "en")

    engine.process_query_stream("Remember that your name is Jarvis", on_token=lambda _t: None)

    assert [fact["value"] for fact in kb.get_all_facts()] == ["your name is Jarvis"]
    system = engine.local_ai.local_llm.streamed_systems[0]
    assert "- [general] Your name is Jarvis" in system
    assert "(par exemple : « Noted: my name is Jarvis. »)" in system
    # Langue rappelée dans le message : dans le prompt système, au milieu des
    # consignes en français, elle ne suffisait pas
    assert engine.local_ai.local_llm.streamed_prompts[0] == (
        "Remember that your name is Jarvis\n\n(Always respond in English.)"
    )


def test_language_instruction_from_memory_wins(kb):
    """« Retiens que tu dois toujours me répondre en anglais » : la consigne
    était enregistrée, mais « Réponds toujours en français. », ajouté à
    chaque message selon la langue détectée, l'emportait."""
    engine = _engine(kb)
    # Sans consigne de langue, la langue détectée reste la règle
    assert engine._language_instruction("Bonjour") == "Réponds toujours en français."

    engine.process_query_stream(
        "Retiens que tu dois toujours me répondre en anglais", on_token=lambda _t: None
    )

    system = engine.local_ai.local_llm.streamed_systems[0]
    assert "Réponds toujours en français." not in system
    # La langue demandée, explicitement : une consigne générique (« la langue
    # qu'il t'a demandée ») ne suffisait pas face à une question en français
    assert "Always respond in English." in system
    # … rappelée en fin de bloc mémoire, avec les exemples des règles en anglais…
    assert system.rstrip().endswith(
        "Réponds-lui en anglais, quelle que soit la langue de son message, sans commenter "
        "ce choix."
    )
    assert "(« Tu t'appelles… » → « My name is… »)" in system
    # Pas de phrase d'exemple en français : recopiée, elle répondait en français
    assert "C'est noté" not in system
    # … et dans le message lui-même : le vrai modèle répondait encore en
    # français à une question posée en français
    assert engine.local_ai.local_llm.streamed_prompts[0] == (
        "Retiens que tu dois toujours me répondre en anglais\n\n(Always respond in English.)"
    )


def test_english_question_is_reminded_to_be_answered_in_english(kb, ollama):
    ollama.replies.append("The capital of Italy is Rome.")
    engine = _detecting(_engine(kb), "en")

    engine.process_query_stream("What is the capital of Italy?", on_token=lambda _t: None)

    assert ollama.requests[0]["messages"][-1]["content"] == (
        "What is the capital of Italy?\n\n(Always respond in English.)"
    )


def test_english_question_gets_the_rule_examples_in_english(kb, ollama):
    """« What's your name? » recevait encore « Je m'appelle Friday. » : le
    modèle recopiait les modèles de phrase des règles, en français."""
    kb.add_fact("general", key="tu t'appelles Friday", value="tu t'appelles Friday")
    ollama.replies.append("My name is Friday.")
    engine = _detecting(_engine(kb), "en")

    engine.process_query_stream("What's your name?", on_token=lambda _t: None)

    system = ollama.systems()[0]
    assert "(« Tu t'appelles… » → « My name is… »)" in system
    # Chaque question rattachée à sa personne : un « My name is… » isolé
    # faisait répondre « Your name is Friday » à « What is my name? »
    assert "- « Who am I? », « What's my name? » portent sur l'utilisateur" in system
    assert "« Who are you? », « What's your name? » portent sur toi" in system
    assert "Je m'appelle…" not in system
    assert system.rstrip().endswith(
        "LANGUE DE RÉPONSE : l'utilisateur t'écrit en anglais. Réponds-lui en anglais, "
        "sans commenter ce choix."
    )
    # En français, les exemples restent en français, sans note de langue
    french = _detecting(_engine(kb), "fr")._knowledge_base_context("Comment tu t'appelles ?")
    assert "(« Tu t'appelles… » → « Je m'appelle… »)" in french
    assert "My name is" not in french
    assert "LANGUE DE RÉPONSE" not in french


def test_other_imposed_language_keeps_the_french_rule_examples(kb):
    kb.add_fact("general", key="tu t'appelles Friday", value="tu t'appelles Friday")
    kb.add_fact(
        "general", key="tu dois me répondre en espagnol", value="tu dois me répondre en espagnol"
    )

    block = _engine(kb)._knowledge_base_context("Comment tu t'appelles ?")

    assert "(« Tu t'appelles… » → « Je m'appelle… »)" in block
    assert block.endswith("Réponds-lui en espagnol, quelle que soit la langue de son message, "
                          "sans commenter ce choix.")


@pytest.mark.parametrize("code, message, reminded", [
    ("en", "What's your name?", "en"),
    # Passage cité ignoré : la consigne reste écrite en anglais
    ("en", "Remember that you must always end your answers with « Bonne journée »", "en"),
    # Un seul mot anglais : il faut aussi l'avis du détecteur
    ("en", "Hello there", "en"),
    ("fr", "Hello", None),
    # Sous 10 caractères, le détecteur répond « fr » : deux mots anglais suffisent
    ("fr", "Who am I?", "en"),
    # Message français pris pour de l'anglais : aucun mot anglais, ou un mot français
    ("en", "Merci beaucoup !", None),
    ("en", "c'est quoi the difference", None),
    ("en", "Traduis en français : what is your name", None),
    # Les autres langues s'en tiennent au prompt système (« Pourquoi ? » → pt)
    ("pt", "Pourquoi ?", None),
])
def test_reminded_language(kb, code, message, reminded):
    assert _detecting(_engine(kb), code)._reminded_language(message) == reminded


def test_short_english_question_gets_the_english_instruction(kb):
    """« Who am I? » recevait « Tu t'appelles Friday » : trop court pour le
    détecteur, le message passait pour du français."""
    engine = _detecting(_engine(kb), "fr")

    assert engine._language_instruction("Who am I?") == "Always respond in English."
    assert engine._language_instruction("Qui suis-je ?") == "Réponds toujours en français."


def test_short_french_message_taken_for_english_gets_no_reminder(kb):
    engine = _detecting(_engine(kb), "en")

    engine.process_query_stream("Merci, retiens que je préfère le thé", on_token=lambda _t: None)

    assert engine.local_ai.local_llm.streamed_prompts[0] == "Merci, retiens que je préfère le thé"


def test_language_reminder_is_left_out_of_the_length_thresholds():
    """Compté, le rappel faisait planifier une question anglaise de 29 caractères."""
    reminder = "\n\n(Always respond in English.)"
    question = "Which city is the capital of Italy, and which region is it in?"

    assert not ChatOrchestrator._should_plan("What is the capital of Italy?" + reminder, _TOOLS)
    assert ChatOrchestrator._validate_response("Rome, in Lazio.", question + reminder, []) == (
        True, "ok"
    )


@pytest.mark.parametrize("question", ["qui suis-je ?", "Who am I?"])
def test_who_am_i_without_user_facts_gets_no_instruction_as_answer(kb, question):
    """Avec seulement des consignes pour l'IA, « Who am I? » recevait « You are
    an AI user whose name is Friday », ou un nom inventé."""
    kb.add_fact("general", key="tu t'appelles Friday", value="tu t'appelles Friday")
    engine = _detecting(_engine(kb), "en" if question.startswith("Who") else "fr")

    block = engine._knowledge_base_context(question)

    assert "Sur l'utilisateur :\n" not in block  # aucune section sur lui
    assert (
        "portent sur l'utilisateur : tu ne sais encore rien de lui (aucun fait sur lui "
        "ci-dessus) : dis-le-lui simplement, sans lui attribuer tes consignes."
    ) in block
    assert "réponds avec ses faits" not in block


def test_instructions_are_mentioned_only_when_asked(kb):
    """Le modèle énonçait ses consignes sans qu'on les lui demande, parfois à la
    mauvaise personne (« Your name is Friday »)."""
    kb.add_fact("general", key="tu t'appelles Friday", value="tu t'appelles Friday")

    block = _engine(kb)._knowledge_base_context("Quelle est la capitale de l'Italie ?")

    assert (
        "N'en parle que si son message porte dessus, et alors à la première personne "
        "(« Tu t'appelles… » → « Je m'appelle… »)."
    ) in block


def test_user_facts_and_assistant_instructions_are_kept_apart(kb):
    kb.add_fact("general", key="je m'appelle Nicolas", value="je m'appelle Nicolas")
    kb.add_fact("general", key="tu t'appelles Jarvis", value="tu t'appelles Jarvis")
    engine = _engine(kb)

    engine.process_query_stream("Comment tu t'appelles ?", on_token=lambda _t: None)

    system = engine.local_ai.local_llm.streamed_systems[0]
    assert "Sur l'utilisateur :\n- [general] L'utilisateur s'appelle Nicolas" in system
    assert "défaut : nom, langue, ton, format) :\n- [general] Tu t'appelles Jarvis" in system


def test_who_am_i_question_gets_the_user_facts_in_the_third_person(kb, ollama):
    """« qui suis-je ? » répondu « Je m'appelle Nicolas. » : la phrase de
    l'utilisateur, même citée, était recopiée telle quelle."""
    kb.add_fact("general", key="je m'appelle Nicolas", value="je m'appelle Nicolas")
    ollama.replies.append("Tu t'appelles Nicolas. 💡")

    _engine(kb).process_query_stream("qui suis-je ?", on_token=lambda _t: None)

    system = ollama.systems()[0]
    assert "je m'appelle Nicolas" not in system
    assert "- [general] L'utilisateur s'appelle Nicolas" in system
    assert "« Qui suis-je ? »" in system  # consigne explicite pour cette question


# ── Pièces jointes ──────────────────────────────────────────────────────────


def test_remember_request_with_a_document_attached(kb, ollama):
    """Fichier joint (pdf, docx…) : son contenu part dans le prompt, sans outils.
    Le fait est enregistré, et la réponse le confirme avec les faits connus."""
    kb.add_fact("general", key="Mon chat s'appelle Félix", value="Mon chat s'appelle Félix")
    engine = _engine(kb)
    engine.local_ai.conversation_memory.stored_documents = {
        "rapport.pdf": {"content": "Chiffre d'affaires en hausse."}
    }
    engine._document_sections = lambda _query, _docs: [
        "=== rapport.pdf ===\nChiffre d'affaires en hausse."
    ]

    engine.process_query_stream("Retiens que je suis Nicolas Gouy", on_token=lambda _t: None)

    assert "je suis Nicolas Gouy" in [fact["value"] for fact in kb.get_all_facts()]
    assert not ollama.requests  # contenu dans le prompt : aucun outil
    system = engine.local_ai.local_llm.streamed_systems[0]
    assert system.startswith(_IDENTITY)
    assert "MÉMORISATION" in system
    assert "L'utilisateur : son chat s'appelle Félix" in system
    assert "=== rapport.pdf ===" in system


def _with_vision(engine):
    """Branche le vrai filtre d'image de CustomAIModel et enregistre ses appels."""
    calls = []
    engine.local_ai._question_concerns_image = CustomAIModel._question_concerns_image

    def generate_response_stream(user_input, **kwargs):
        calls.append((user_input, kwargs))
        return "Je vois un chat roux."

    engine.local_ai.generate_response_stream = generate_response_stream
    return calls


def test_image_question_receives_the_facts_and_the_memorization(kb):
    """Image jointe : la réponse vision partait sans les faits mémorisés ni la
    confirmation d'une mémorisation."""
    kb.add_fact("general", key="Mon chat s'appelle Félix", value="Mon chat s'appelle Félix")
    engine = _engine(kb)
    calls = _with_vision(engine)

    engine.process_query_stream(
        "Que vois-tu sur cette image ? Et retiens que je suis Nicolas Gouy",
        image_base64="aW1hZ2U=",
        on_token=lambda _t: None,
    )

    assert "je suis Nicolas Gouy" in [fact["value"] for fact in kb.get_all_facts()]
    ((_question, kwargs),) = calls
    assert kwargs["image_base64"] == "aW1hZ2U="
    assert "MÉMORISATION" in kwargs["answer_context"]
    assert "L'utilisateur : son chat s'appelle Félix" in kwargs["answer_context"]


def test_image_unrelated_to_the_question_takes_the_text_path(kb):
    """« Souviens-toi que… » avec une image : CustomAIModel ignorait l'image et
    son aiguillage envoyait le message (tiret compris) vers le calcul."""
    engine = _engine(kb)
    calls = _with_vision(engine)

    engine.process_query_stream(
        "Souviens-toi que je suis Nicolas Gouy", image_base64="aW1hZ2U=", on_token=lambda _t: None
    )

    assert [fact["value"] for fact in kb.get_all_facts()] == ["je suis Nicolas Gouy"]
    assert not calls
    assert "MÉMORISATION" in engine.local_ai.local_llm.streamed_systems[0]


def test_auto_extract_false_disables_chat_memory(kb, monkeypatch):
    monkeypatch.setattr(AIEngine, "_memory_auto_extract", staticmethod(lambda: False))

    assert _engine(kb)._remember_from_message("Retiens que mon chat s'appelle Félix") is None
    assert kb.get_all_facts() == []


# ── Faits envoyés au modèle ─────────────────────────────────────────────────


def test_synthesis_after_a_tool_keeps_the_facts(kb, ollama):
    """« Cherche dans ta mémoire… » : search_memory, puis la synthèse."""
    kb.add_fact("general", key="Mon chat s'appelle Félix", value="Mon chat s'appelle Félix")
    ollama.replies.extend([
        {"name": "search_memory", "arguments": {"query": "nom du chat"}},
        "Ton chat s'appelle Félix.",     # 2e tour de la boucle, remplacé par…
        "Ton chat s'appelle Félix ! 🐱",  # … la synthèse, seule affichée
    ])

    answer = _engine(kb).process_query_stream(
        "Cherche dans ta mémoire comment s'appelle mon chat", on_token=lambda _t: None
    )

    assert answer == "Ton chat s'appelle Félix ! 🐱"
    synthesis = ollama.systems()[-1]
    assert "Tu interviens en bout de processus" in synthesis
    assert synthesis.startswith(_IDENTITY)
    assert "- [general] L'utilisateur : son chat s'appelle Félix" in synthesis


@pytest.mark.parametrize("message, replies", [
    # Sans outils : mémorisation seule, conversationnel, historique
    ("retiens que j'habite à Lyon", []),
    ("Merci, retiens que je préfère le thé", []),
    ("Tu te souviens comment s'appelle mon chat ?", []),
    # Boucle d'outils, réponse directe
    ("qui suis-je ?", ["Tu t'appelles Sophie."]),
    ("Retiens que mon chien s'appelle Rex. Quelle est la capitale de l'Italie ?",
     ["C'est noté ! La capitale de l'Italie est Rome."]),
    # Outil search_memory, puis synthèse
    ("Cherche dans ta mémoire comment s'appelle mon chat", [
        {"name": "search_memory", "arguments": {"query": "nom du chat"}},
        "Ton chat s'appelle Félix.",
        "Ton chat s'appelle Félix ! 🐱",
    ]),
])
def test_every_request_of_a_memory_answer_starts_from_the_modelfile(kb, ollama, message, replies):
    """Ollama n'applique le SYSTEM du Modelfile qu'en l'absence de message
    « system » : chaque prompt système envoyé pour une réponse qui utilise la
    mémoire doit repartir de lui, puis porter les faits."""
    for value in ("je m'appelle Sophie", "tu t'appelles Friday", "mon chat s'appelle Félix"):
        kb.add_fact("general", key=value, value=value)
    ollama.replies.extend(replies)
    engine = _engine(kb)

    engine.process_query_stream(message, on_token=lambda _t: None)

    systems = engine.local_ai.local_llm.streamed_systems + ollama.systems()
    assert systems
    for system in systems:
        assert system.startswith(_IDENTITY)
        assert "MÉMOIRE PERSISTANTE" in system


def test_cli_answer_starts_from_the_modelfile_with_the_facts(kb):
    """Chemin CLI (process_query → _handle_with_mcp_tools), aussi pris par la
    génération de fichiers du GUI."""
    kb.add_fact("general", key="je m'appelle Sophie", value="je m'appelle Sophie")
    engine = _engine(kb)
    sent = []

    def generate_with_tools(prompt, tools, tool_executor, system_prompt=None):
        sent.append(system_prompt)
        return {"success": True, "response": "Tu t'appelles Sophie.", "tool_calls": []}

    engine.local_ai.local_llm.generate_with_tools = generate_with_tools

    result = asyncio.run(engine._handle_with_mcp_tools("qui suis-je ?", None))

    assert result["message"] == "Tu t'appelles Sophie."
    (system,) = sent
    assert system.startswith(_IDENTITY)
    assert "- [general] L'utilisateur s'appelle Sophie" in system


def test_memory_question_without_history_can_use_the_facts(kb):
    """« Tu te souviens… » dans une nouvelle conversation : le prompt imposait
    de répondre « nous n'avons pas encore échangé », même avec le fait connu."""
    kb.add_fact("general", key="Mon chat s'appelle Félix", value="Mon chat s'appelle Félix")
    engine = _engine(kb)

    engine.process_query_stream(
        "Tu te souviens comment s'appelle mon chat ?", on_token=lambda _t: None
    )

    system = engine.local_ai.local_llm.streamed_systems[0]
    assert system.startswith(_IDENTITY)
    assert "## Outils" not in system
    assert "L'utilisateur : son chat s'appelle Félix" in system
    assert "ce que tu sais déjà de l'utilisateur" in system


# ── Outils mémoire ──────────────────────────────────────────────────────────


def test_search_memory_returns_the_matching_facts(kb):
    kb.add_fact("general", key="Mon chat s'appelle Félix", value="Mon chat s'appelle Félix")
    engine = _engine(kb)
    engine.get_vector_memory = lambda: types.SimpleNamespace(
        search_similar=lambda _query, n_results: [{"content": "Rapport annuel 2025"}]
    )

    result = engine._search_memory("comment s'appelle mon chat", n_results="3")

    assert result.startswith(
        "Faits mémorisés :\n- [general] L'utilisateur : son chat s'appelle Félix"
    )
    assert "Documents indexés :\n[1] Rapport annuel 2025" in result


def test_search_memory_without_anything(kb):
    engine = _engine(kb)
    engine.get_vector_memory = lambda: types.SimpleNamespace(
        search_similar=lambda _query, n_results: []
    )

    # « Aucun résultat » est ce que l'orchestrateur reconnaît comme mémoire vide
    assert engine._search_memory("nom du chat") == _NO_RESULT


def test_search_memory_without_matching_words_lists_the_recent_facts(kb):
    """« Qu'est-ce que je t'ai demandé de retenir ? » : le modèle cherchait
    « fait retenu par l'utilisateur », obtenait « Aucun résultat » et
    répondait que rien n'était mémorisé."""
    kb.add_fact("general", key="tu t'appelles Jarvis", value="tu t'appelles Jarvis")
    engine = _engine(kb)
    engine.get_vector_memory = lambda: types.SimpleNamespace(
        search_similar=lambda _query, n_results: []
    )

    result = engine._search_memory("fait retenu par l'utilisateur")

    assert result == (
        "Aucun fait ne correspond exactement ; les plus récents :\n"
        "- [general] Tu t'appelles Jarvis"
    )


def test_remember_fact_tool_saves_once(kb):
    engine = _engine(kb)

    first = engine._remember_fact_tool("Le chat de l'utilisateur s'appelle Félix", "person")
    again = engine._remember_fact_tool("le chat de l'utilisateur s'appelle Félix.", "person")

    facts = kb.get_all_facts()
    assert first.startswith("Mémorisé : « Le chat de l'utilisateur s'appelle Félix »")
    assert again.startswith("Déjà en mémoire")
    assert [(f["category"], f["source"]) for f in facts] == [("person", "conversation")]
    assert engine._remember_fact_tool("  ") == "Rien à mémoriser : l'information est vide."


def _registered_tools(monkeypatch, auto_extract):
    monkeypatch.setattr(AIEngine, "_memory_auto_extract", staticmethod(lambda: auto_extract))
    registered = {}
    engine = AIEngine.__new__(AIEngine)
    engine.logger = logging.getLogger(__name__)
    engine.local_ai = types.SimpleNamespace(local_llm=None)
    engine.mcp_manager = types.SimpleNamespace(
        register_local_tool=lambda name, description, parameters, callable_fn: (
            registered.__setitem__(name, parameters)
        ),
        register_mcp_server_from_dict=lambda *_args: None,
        connect_external_servers_sync=lambda: None,
        get_ollama_tools=lambda: list(registered),
    )
    engine._setup_mcp_tools()
    return registered


def test_remember_fact_is_offered_unless_disabled(monkeypatch):
    tools = _registered_tools(monkeypatch, auto_extract=True)

    assert tools["remember_fact"]["required"] == ["fact"]
    assert "general" in tools["remember_fact"]["properties"]["category"]["enum"]
    assert "remember_fact" not in _registered_tools(monkeypatch, auto_extract=False)
