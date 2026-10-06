"""
Mémoire dans les contenus générés : fichiers de code et documents.

Régression : « génère un fichier python qui affiche mon prénom » ignorait le
prénom mémorisé. Les générateurs rédigent avec leur propre prompt (le contenu
d'un fichier n'a pas à suivre le format du chat), et rien ne leur passait les
faits de la fenêtre Mémoire.
"""

import asyncio
import logging
import types

import pytest

from core.ai_engine import AIEngine
from core.knowledge_base_manager import KnowledgeBaseManager
from generators.code_generator import CodeGenerator
from generators.document_generator import DocumentGenerator

_SOPHIE = "- [general] L'utilisateur s'appelle Sophie"


class _LLM:
    """Garde les prompts reçus et répond un contenu fixe."""

    is_ollama_available = True

    def __init__(self, reply):
        self.reply = reply
        self.prompts = []

    def generate(self, prompt, system_prompt=None, **_kwargs):  # pylint: disable=unused-argument
        self.prompts.append(prompt)
        return self.reply


@pytest.fixture(name="kb")
def _kb(tmp_path):
    kb = KnowledgeBaseManager(db_path=str(tmp_path / "facts.db"))
    kb.add_fact("general", key="je m'appelle Sophie", value="je m'appelle Sophie")
    yield kb
    kb.close()


def _engine(kb):
    """AIEngine sans __init__ : ni Ollama, ni ChromaDB, ni modèles."""
    engine = AIEngine.__new__(AIEngine)
    engine.logger = logging.getLogger(__name__)
    engine.knowledge_base = kb
    return engine


# ── Faits transmis aux générateurs ──────────────────────────────────────────


def test_generation_memory_has_the_user_facts_only(kb):
    """Une consigne pour le chat n'a pas sa place à la fin d'un script."""
    consigne = "tu dois toujours terminer tes réponses par « Have a nice day »"
    kb.add_fact("general", key=consigne, value=consigne)

    memory = _engine(kb)._generation_memory("génère un fichier qui affiche mon prénom")

    assert memory == _SOPHIE


@pytest.mark.parametrize("request_text, personal", [
    ("génère un fichier python qui affiche mon prénom", True),
    ("une carte de visite avec mon nom et mon entreprise", True),
    ("génère mon CV en Word", True),
    ("rédige une lettre de motivation pour un poste de technicien", True),
    ("écris un poème sur mon chat", True),
    ("prépare le planning de mon équipe", True),
    # Avec les faits, le modèle mettait « Auteur : Sophie Martin… Chat :
    # Félix » en tête d'un script de tri
    ("génère un fichier python qui trie une liste de nombres", False),
    # « mon fichier », « ma liste » : des possessifs qui ne parlent pas de lui
    ("génère un fichier python qui trie ma liste de nombres", False),
    ("crée un script qui lit mon fichier CSV", False),
    ("un rapport sur les baleines", False),
])
def test_generation_memory_only_for_requests_about_the_user(kb, request_text, personal):
    assert _engine(kb)._generation_memory(request_text) == (_SOPHIE if personal else "")


def test_generation_memory_is_empty_without_facts(tmp_path):
    kb = KnowledgeBaseManager(db_path=str(tmp_path / "empty.db"))
    try:
        assert _engine(kb)._generation_memory("génère mon CV") == ""
    finally:
        kb.close()


# ── Prompts des générateurs ─────────────────────────────────────────────────


def test_code_generator_gives_the_memory_to_the_model():
    llm = _LLM("print('Bonjour Sophie')")

    code = asyncio.run(CodeGenerator(llm=llm)._generate_with_ollama(
        "génère un fichier python qui affiche mon prénom", "python", {}, memory=_SOPHIE,
    ))

    assert code == "print('Bonjour Sophie')"
    (prompt,) = llm.prompts
    assert "Ce que tu sais de l'utilisateur (sa mémoire)" in prompt
    assert f"{_SOPHIE}\n\nGénère le code maintenant :" in prompt


def test_code_generator_prompt_is_unchanged_without_memory():
    llm = _LLM("print('ok')")

    asyncio.run(CodeGenerator(llm=llm)._generate_with_ollama("un script", "python", {}))

    assert llm.prompts[0].endswith(
        "- Structure claire et organisée\n\nGénère le code maintenant :"
    )


def test_document_writer_gets_the_memory():
    llm = _LLM("# CV\n\nSophie")

    content = asyncio.run(
        DocumentGenerator(llm=llm)._write_content("un CV", "", "docx", memory=_SOPHIE)
    )

    assert content == "# CV\n\nSophie"
    assert "CE QUE TU SAIS DE L'UTILISATEUR (sa mémoire)" in llm.prompts[0]
    assert _SOPHIE in llm.prompts[0]


def test_document_writer_prompt_is_unchanged_without_memory():
    llm = _LLM("# Les baleines")

    asyncio.run(DocumentGenerator(llm=llm)._write_content("un rapport", "", "docx"))

    assert "CE QUE TU SAIS DE L'UTILISATEUR" not in llm.prompts[0]


# ── Branchement dans AIEngine ───────────────────────────────────────────────


def test_file_generation_request_passes_the_memory(kb):
    """« génère un fichier… » : GUI et CLI, via _handle_code_generation."""
    engine = _engine(kb)
    received = {}

    async def generate_file(query, is_interrupted_callback=None, memory=""):  # pylint: disable=unused-argument
        received["memory"] = memory
        return {"success": True, "code": "print('Bonjour Sophie')", "filename": "prenom.py"}

    engine.ollama_code_generator = types.SimpleNamespace(generate_file=generate_file)

    result = asyncio.run(engine._handle_code_generation(
        "génère un fichier python qui affiche mon prénom"
    ))

    assert result["type"] == "file_generation"
    assert received["memory"] == _SOPHIE


def _registered_tools(engine, monkeypatch):
    """Outils MCP enregistrés par _setup_mcp_tools, par nom."""
    monkeypatch.setattr(AIEngine, "_memory_auto_extract", staticmethod(lambda: True))
    registered = {}
    engine.local_ai = types.SimpleNamespace(local_llm=None)
    engine.mcp_manager = types.SimpleNamespace(
        register_local_tool=lambda name, description, parameters, callable_fn: (
            registered.__setitem__(name, callable_fn)
        ),
        register_mcp_server_from_dict=lambda *_args: None,
        connect_external_servers_sync=lambda: None,
        get_ollama_tools=lambda: list(registered),
    )
    engine._setup_mcp_tools()
    return registered


@pytest.mark.parametrize("route", ["outil generate_document", "routage par mots-clés"])
def test_document_generation_passes_the_memory(kb, monkeypatch, route):
    engine = _engine(kb)
    engine._turn_research = []
    received = {}

    async def generate_document(brief, **kwargs):
        received.update(kwargs, brief=brief)
        return {"success": False, "error": "rendu non testé ici"}

    engine.document_generator = types.SimpleNamespace(generate_document=generate_document)

    if route == "outil generate_document":
        tool = _registered_tools(engine, monkeypatch)["generate_document"]
        asyncio.run(tool(brief="mon CV", format="docx"))
    else:
        asyncio.run(engine._handle_document_generation("génère mon CV en Word", {}))

    assert received["memory"] == _SOPHIE


def test_document_tool_reads_the_original_request(kb, monkeypatch):
    """Le modèle réécrit « mon parcours » à la troisième personne dans brief."""
    engine = _engine(kb)
    engine._turn_research = []
    engine._turn_request = "fais une présentation de mon parcours en PowerPoint"
    received = {}

    async def generate_document(brief, **kwargs):
        received.update(kwargs, brief=brief)
        return {"success": False, "error": "rendu non testé ici"}

    engine.document_generator = types.SimpleNamespace(generate_document=generate_document)
    tool = _registered_tools(engine, monkeypatch)["generate_document"]

    asyncio.run(tool(brief="Présentation du parcours de l'utilisateur", format="pptx"))

    assert received["memory"] == _SOPHIE
