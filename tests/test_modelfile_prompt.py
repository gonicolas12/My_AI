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
from core.modelfile import FALLBACK_IDENTITY, modelfile_system, with_modelfile
from models.custom_ai_model import CustomAIModel
from models.local_llm import LocalLLM

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
