"""
Tests du SYSTEM du Modelfile dans les prompts système (core/modelfile.py).

Régression observée en usage réel : à « il y a quoi dans mon dossier
téléchargements ? et toi qui es tu ? », My_AI se présentait comme « une IA
capable de gérer des fichiers », sans emoji ni mise en forme. Ollama
n'applique le SYSTEM de my_ai qu'en l'absence de message « system » : les
réponses qui envoyaient leur propre prompt effaçaient l'identité au lieu de
la compléter.
"""

import logging
import types

import pytest

import core.modelfile as modelfile
import models.local_llm as local_llm
from core.ai_engine import AIEngine
from core.chat_orchestrator import ChatOrchestrator
from core.modelfile import (
    FALLBACK_IDENTITY,
    drop_tools_section,
    modelfile_system,
    with_modelfile,
)
from models.custom_ai_model import CustomAIModel
from models.local_llm import LocalLLM
from models.mixins.conversation_responses import ConversationResponseMixin
from models.mixins.document_analysis import DocumentAnalysisMixin

_IDENTITY = "Tu es My_AI"


# ── core.modelfile ──────────────────────────────────────────────────────────


def test_modelfile_system_is_the_system_block():
    system = modelfile_system()

    assert system.startswith(_IDENTITY)
    assert "## Outils" in system
    assert "## Format" in system


def test_instructions_come_after_the_identity():
    assert with_modelfile("CONSIGNE") == modelfile_system() + "\n\nCONSIGNE"


def test_without_tools_only_the_tools_section_is_dropped():
    prompt = with_modelfile("CONSIGNE", tools=False)

    assert prompt.startswith(_IDENTITY)
    assert "## Outils" not in prompt
    assert "`web_search`" not in prompt
    for heading in (
        "## Capacités", "## Contexte documentaire", "## Raisonnement",
        "## Format", "## Règles", "## Auteur du projet", "### Liens à utiliser",
    ):
        assert heading in prompt
    assert prompt.endswith("\n\nCONSIGNE")


def test_tools_section_dropped_from_a_built_prompt():
    """Les voies sans outils retirent la section d'un prompt déjà complété."""
    prompt = with_modelfile("CONSIGNE") + "\n\nFAITS UTILISATEUR"

    expected = with_modelfile("CONSIGNE", tools=False) + "\n\nFAITS UTILISATEUR"
    assert drop_tools_section(prompt) == expected


@pytest.fixture(name="missing_modelfile")
def _missing_modelfile(monkeypatch, tmp_path):
    monkeypatch.setattr(modelfile, "MODELFILE_PATH", tmp_path / "Modelfile")
    modelfile_system.cache_clear()
    yield
    modelfile_system.cache_clear()


def test_missing_modelfile_falls_back_to_a_short_identity(missing_modelfile):
    assert modelfile_system() == ""
    assert with_modelfile("CONSIGNE", tools=False) == FALLBACK_IDENTITY + "\n\nCONSIGNE"


# ── LocalLLM : le résumé glissant ne passe pas devant le Modelfile ──────────


class _Response:
    status_code = 200

    @staticmethod
    def json():
        return {"message": {"content": "Je suis My_AI."}}


def test_summarized_history_keeps_the_modelfile_first(monkeypatch):
    """_compress_old_history place un message « system » en tête d'historique."""
    sent = []

    def fake_post(_url, **kwargs):
        sent.append(kwargs["json"])
        return _Response()

    monkeypatch.setattr(local_llm, "_resilient_post", fake_post)
    summary = {"role": "system", "content": "[Résumé de la conversation précédente] …"}
    llm = LocalLLM.__new__(LocalLLM)  # sans __init__ : aucun appel à Ollama
    llm.is_ollama_available = True
    llm.model = "my_ai"
    llm.chat_url = "http://127.0.0.1:9/api/chat"
    llm.timeout = 1
    llm.gen_temperature = 0.0
    llm.gen_num_ctx = 2048
    llm.conversation_history = [
        summary,
        {"role": "user", "content": "Salut"},
        {"role": "assistant", "content": "Bonjour !"},
    ]

    llm.generate("Et toi, qui es-tu ?", save_history=False)

    messages = sent[0]["messages"]
    assert messages[0] == {"role": "system", "content": modelfile_system()}
    assert messages[1] == summary
    assert messages[-1] == {"role": "user", "content": "Et toi, qui es-tu ?"}


def test_caller_system_prompt_is_sent_as_is():
    assert LocalLLM._system_messages("CONSIGNE") == [
        {"role": "system", "content": "CONSIGNE"}
    ]


# ── CustomAIModel : document chargé, contexte RAG ───────────────────────────


def _custom_model(document=""):
    """Ce que _ollama_system_prompt lit de CustomAIModel."""
    return types.SimpleNamespace(
        _has_documents_in_memory=lambda: bool(document),
        _is_document_processing_request=lambda _query: False,
        _is_document_question=lambda _query: True,
        _get_full_document_content=lambda: document,
    )


def test_document_answer_keeps_the_identity():
    model = _custom_model("Rapport annuel : chiffre d'affaires en hausse.")

    system = CustomAIModel._ollama_system_prompt(model, "résume le document", None, "TEST")

    assert system.startswith(with_modelfile(tools=False))
    assert "chiffre d'affaires en hausse" in system
    assert "## Outils" not in system


def test_rag_context_alone_keeps_the_identity():
    context = {"rag_context": "Extrait pertinent de la base de connaissances. " * 3}

    system = CustomAIModel._ollama_system_prompt(_custom_model(), "question", context, "TEST")

    assert system.startswith(with_modelfile(tools=False))
    assert "CONTEXTE ADDITIONNEL:\nExtrait pertinent" in system


def test_without_context_local_llm_sends_the_modelfile():
    assert CustomAIModel._ollama_system_prompt(_custom_model(), "salut", None, "TEST") is None


# ── AIEngine : question sur le dossier projet attaché ───────────────────────


class _Indexer:
    @staticmethod
    def list_folders(_workspace):
        return ["C:/projet"]

    @staticmethod
    def get_status(_workspace):
        return {"folders": [{"path": "C:/projet", "files": ["main.py"], "file_count": 1}]}

    @staticmethod
    def get_relevant_context(_workspace, _query):
        return "def main(): ..."


def test_project_answer_keeps_the_identity():
    captured = {}

    class _LLM:
        @staticmethod
        def generate_stream(prompt, system_prompt=None, **_kwargs):
            captured["system"] = system_prompt
            return "Le projet contient main.py."

    engine = types.SimpleNamespace(  # ce que la méthode lit d'AIEngine
        _CODEBASE_SIGNALS=AIEngine._CODEBASE_SIGNALS,
        _LANG_SUFFIXES=AIEngine._LANG_SUFFIXES,
        _current_lang_instruction="Réponds toujours en français.",
        get_folder_indexer=lambda: _Indexer(),
        session_manager=types.SimpleNamespace(get_current_workspace=lambda: "ws"),
        logger=logging.getLogger(__name__),
    )

    answer = AIEngine._try_codebase_direct_answer(engine, "résume le projet", _LLM())

    assert answer == "Le projet contient main.py."
    assert captured["system"].startswith(with_modelfile(tools=False))
    assert "C:/projet" in captured["system"]
    assert "## Outils" not in captured["system"]


# ── Réponses sans outils : relance de l'orchestrateur, repli CustomAIModel ──


class _CapturingLLM:
    """Garde le prompt système reçu ; ce que lisent les appelants testés."""

    is_ollama_available = True

    def __init__(self):
        self.system = None

    def _answer(self, system_prompt):
        self.system = system_prompt
        return "Je suis My_AI."

    def generate(self, _prompt, system_prompt=None, **_kwargs):
        return self._answer(system_prompt)

    def generate_stream(self, prompt=None, system_prompt=None, **_kwargs):  # pylint: disable=unused-argument
        return self._answer(system_prompt)


def test_orchestrator_retry_without_tools_drops_the_tools_section():
    llm = _CapturingLLM()

    ChatOrchestrator()._retry_without_tools(
        user_input="qui es-tu ?",
        llm=llm,
        system_prompt=with_modelfile("CONSIGNE"),
        on_token=None,
        is_interrupted_callback=None,
    )

    assert llm.system == with_modelfile("CONSIGNE", tools=False)


def test_custom_model_default_answer_keeps_the_identity():
    """Ce repli de CustomAIModel se présentait comme « un assistant expert en
    programmation », sans l'identité ni le format de My_AI."""
    llm = _CapturingLLM()
    model = types.SimpleNamespace(local_llm=llm, name="My_AI")

    ConversationResponseMixin._generate_default_response(model, "salut", {})
    assert llm.system == with_modelfile(tools=False)

    context = {"rag_context": "Extrait pertinent."}
    ConversationResponseMixin._generate_default_response(model, "question", context)
    assert llm.system.startswith(with_modelfile(tools=False))
    assert "CONTEXTE DOCUMENTAIRE:\nExtrait pertinent." in llm.system


@pytest.mark.parametrize("question", ["qui suis-je ?", "Souviens-toi : comment s'appelle mon chat ?"])
def test_fallback_question_with_a_hyphen_keeps_the_identity_and_the_facts(question):
    """Dernier recours d'AIEngine : tout message contenant un « - » partait vers
    le calcul, puis generate_response, sans les faits mémorisés. « qui
    suis-je ? » recevait « je n'ai pas accès à vos informations personnelles »."""
    llm = _CapturingLLM()
    model = types.SimpleNamespace(
        local_llm=llm,
        _ollama_system_prompt=lambda *_args: None,  # aucun document
        generate_response=lambda *_args: "branche calcul",
        conversation_memory=types.SimpleNamespace(add_conversation=lambda *_a: None),
    )

    answer = CustomAIModel.generate_response_stream(
        model, question, answer_context="\n\nMÉMOIRE PERSISTANTE : …"
    )

    assert answer == "Je suis My_AI."
    assert llm.system == with_modelfile(tools=False) + "\n\nMÉMOIRE PERSISTANTE : …"


def test_fallback_calculation_still_goes_to_the_calculator():
    model = types.SimpleNamespace(
        local_llm=_CapturingLLM(), generate_response=lambda *_args: "4",
    )

    assert CustomAIModel.generate_response_stream(model, "combien font 2+2") == "4"


def test_document_passages_answer_keeps_the_identity():
    """Ancien routage par intentions : ce prompt seul effaçait l'identité."""
    llm = _CapturingLLM()
    model = types.SimpleNamespace(local_llm=llm)

    DocumentAnalysisMixin._generate_response_from_passages(
        model, "Quand a lieu la réunion ?",
        [{"passage": "La réunion d'équipe a lieu le mardi à 10h."}],
    )

    assert llm.system.startswith(with_modelfile(tools=False))
    assert llm.system.endswith(
        "Réponds de manière concise et précise aux questions sur des documents."
    )


# ── Image jointe : rédaction de la réponse vision ───────────────────────────


def test_vision_answer_gets_the_identity_and_the_answer_context():
    """La rédaction vision partait sans prompt de l'appelant : ni les faits
    mémorisés, ni la confirmation d'une mémorisation."""
    captured = {}

    class _VisionLLM:
        is_ollama_available = True

        @staticmethod
        def generate_stream_with_image(_prompt, _image, system_prompt=None, **_kwargs):
            captured["system"] = system_prompt
            return "Je vois un chat roux."

    model = types.SimpleNamespace(
        local_llm=_VisionLLM(),
        _question_concerns_image=CustomAIModel._question_concerns_image,
        conversation_memory=types.SimpleNamespace(add_conversation=lambda *_a: None),
    )

    answer = CustomAIModel.generate_response_stream(
        model, "Que vois-tu sur cette image ?", image_base64="aW1hZ2U=",
        answer_context="\n\nFAITS UTILISATEUR : …",
    )

    assert answer == "Je vois un chat roux."
    assert captured["system"] == with_modelfile("FAITS UTILISATEUR : …", tools=False)


def test_vision_pipeline_writes_with_the_given_system_prompt():
    written = {}
    llm = LocalLLM.__new__(LocalLLM)  # sans __init__ : aucun appel à Ollama
    llm.is_ollama_available = True
    llm.conversation_history = []
    llm.max_history_length = 50
    llm._summary_threshold_tokens = 10**9
    llm._get_vision_model = lambda: "minicpm-v"
    llm._get_vision_description = lambda _model, _prompt, _image: "Un chat roux sur un canapé."

    def generate_stream(prompt, system_prompt=None, **_kwargs):
        written.update(prompt=prompt, system=system_prompt)
        return "Je vois un chat roux."

    llm.generate_stream = generate_stream

    answer = llm.generate_stream_with_image("Que vois-tu ?", "aW1hZ2U=", system_prompt="CONSIGNE")

    assert answer == "Je vois un chat roux."
    assert written["system"] == "CONSIGNE"
    assert "Un chat roux sur un canapé." in written["prompt"]
