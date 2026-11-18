"""
Demandes de fichier : code ou document (core/file_intent.py), et leur routage
dans AIEngine.

Régression observée avec le vrai modèle : « Crée un fichier PDF nommé
essai_apercu_poeme avec un court poème… » partait dans la génération de
fichier de code, qui écrivait outputs/essai_apercu_poeme.py (un script Python,
langage par défaut) et aucun PDF. « génère un fichier calcul.py » doit rester
une génération de code.
"""

import asyncio
import logging
from types import SimpleNamespace

import pytest

from core.ai_engine import AIEngine
from core.file_intent import is_code_file_request, is_file_request, requested_document
from generators.document_generator import FORMAT_EXTENSIONS

_POEM = ("Crée un fichier PDF nommé essai_apercu_poeme avec un court poème de quatre "
         "vers sur l’automne.")

# (demande, format attendu, nom attendu)
_DOCUMENTS = [
    (_POEM, "pdf", "essai_apercu_poeme"),
    ("génère un fichier Word sur les baleines", "docx", ""),
    ("crée moi un fichier excel avec les ventes du trimestre", "xlsx", ""),
    ("génère moi un fichier PowerPoint de 5 diapositives sur le climat", "pptx", ""),
    ("crée un fichier markdown avec ma liste de courses", "md", ""),
    ("génère un fichier CSV des planètes", "csv", ""),
    ("crée un fichier texte avec un poème", "txt", ""),
    # Extension du nom
    ("crée un fichier rapport.pdf sur les dauphins", "pdf", "rapport"),
    ("crée un fichier nommé bilan.docx avec le bilan de l'année", "docx", "bilan"),
    ("crée un fichier notes.txt avec un poème", "txt", "notes"),
    ("Crée un fichier « Poème.pdf »", "pdf", "Poème"),
    # Format introduit, ou nommé plus loin
    ("génère un fichier au format PDF avec un poème", "pdf", ""),
    ("crée un fichier .pdf avec un poème", "pdf", ""),
    ("crée un fichier nommé poeme en PDF", "pdf", "poeme"),
    ("crée un fichier nommé « Mon rapport » au format Word", "docx", "Mon rapport"),
    ("crée un fichier avec un poème en format PDF", "pdf", ""),
    ("crée un fichier avec un poème nommé poeme.pdf", "pdf", "poeme"),
    ("crée un fichier avec un poème appelé « Poème d’automne.md »", "md", "Poème d’automne"),
    # « qui » décrit le document, pas un programme : le format vient d'abord
    ("crée un fichier PDF qui présente les planètes", "pdf", ""),
    ("CRÉE UN FICHIER EXCEL NOMMÉ ventes_2026", "xlsx", "ventes_2026"),
]

_CODE_FILES = [
    "génère un fichier calcul.py",
    "génère moi un fichier main.py qui me permet de jouer au morpion",
    "génère un fichier python qui affiche mon prénom",
    "génère un fichier en python qui trie une liste",
    "génère un fichier server.js pour un serveur Express simple",
    "crée moi un fichier index.html pour une page web moderne",
    "génère un fichier HTML avec un formulaire",
    # Un format dans le nom d'un fichier de code
    "crée un fichier test-pdf.py",
    "génère un fichier markdown_parser.py",
    # Un format cité par un programme
    "génère un fichier calcul.py qui exporte les résultats en PDF",
    "génère un fichier python qui lit un PDF et en extrait le texte",
    "génère un fichier avec une fonction python qui exporte en CSV",
    "crée un fichier qui convertit les PDF en Word",
    "génère un fichier qui affiche bonjour",
    "génère un fichier qui lit le fichier nommé data.csv",
    # Aucun format de document : du code, comme avant
    "crée un fichier avec un poème",
]


# ── Détection ───────────────────────────────────────────────────────────────


@pytest.mark.parametrize("request_text, fmt, name", _DOCUMENTS)
def test_a_document_format_makes_a_document(request_text, fmt, name):
    document = requested_document(request_text)

    assert document is not None
    assert (document.fmt, document.name) == (fmt, name)
    assert is_file_request(request_text) and not is_code_file_request(request_text)


@pytest.mark.parametrize("request_text", _CODE_FILES)
def test_code_files_stay_code(request_text):
    assert requested_document(request_text) is None
    assert is_code_file_request(request_text)


@pytest.mark.parametrize("request_text", [
    "Rédige un document PDF de trois lignes sur l’automne",
    "crée un PDF sur les dauphins",
    "génère une image de chat",
])
def test_other_requests_are_not_file_requests(request_text):
    """Sans « génère/crée un fichier », la réponse normale s'en occupe déjà."""
    assert requested_document(request_text) is None
    assert not is_code_file_request(request_text)


def test_every_format_is_one_the_document_generator_writes():
    formats = {fmt for _text, fmt, _name in _DOCUMENTS}
    assert formats == {"pdf", "docx", "xlsx", "pptx", "md", "csv", "txt"}
    assert formats <= set(FORMAT_EXTENSIONS)


def test_the_given_name_is_a_valid_file_name():
    document = requested_document("crée un fichier PDF nommé « essai: v1/2 »")
    assert document.name == "essai_ v1_2"


# ── Routage dans AIEngine ───────────────────────────────────────────────────


def _engine(mcp=False):
    """AIEngine sans __init__ : générateurs simulés, ni Ollama ni modèles.

    `calls` note les générateurs appelés et ce qu'ils reçoivent ; avec `mcp`,
    la boucle d'outils est disponible et note la demande reçue.
    """
    engine = AIEngine.__new__(AIEngine)
    engine.logger = logging.getLogger(__name__)
    engine.calls = []
    engine.knowledge_base = None
    engine._last_documents = []
    engine._remember_from_message = lambda _query: None
    engine._language_instruction = lambda _query: ""
    engine.is_image_generation_request = lambda _query: False
    engine.conversation_manager = SimpleNamespace(
        add_exchange=lambda _query, _response: None, get_recent_history=lambda: [],
    )
    engine.file_manager = SimpleNamespace(get_timestamp=lambda: "")
    engine.local_ai = SimpleNamespace(
        local_llm=SimpleNamespace(is_ollama_available=True) if mcp else None
    )
    engine.mcp_manager = SimpleNamespace(has_tools=lambda: mcp)

    async def with_tools(query, _context, _is_interrupted_callback=None):
        engine.calls.append(("mcp", query))
        return {"type": "mcp", "message": "Le PDF est prêt.", "success": True}

    async def generate_file(query, is_interrupted_callback=None, memory=""):
        del is_interrupted_callback, memory
        engine.calls.append(("code", query))
        return {"success": True, "code": "print(1)", "filename": "calcul.py",
                "file_path": "outputs/calcul.py"}

    async def generate_document(brief, **kwargs):
        engine.calls.append(("document", kwargs["fmt"], kwargs["filename"]))
        name = f"{kwargs['filename'] or 'document'}.{kwargs['fmt']}"
        return {"success": True, "file_path": f"outputs/documents/{name}",
                "file_name": name, "format": kwargs["fmt"]}

    engine._handle_with_mcp_tools = with_tools
    engine.ollama_code_generator = SimpleNamespace(generate_file=generate_file)
    engine.document_generator = SimpleNamespace(generate_document=generate_document)
    return engine


def test_a_pdf_file_request_is_written_as_a_pdf():
    """Sans boucle d'outils (pas d'Ollama), le routage par mots-clés écrit le
    document dans le format et sous le nom demandés."""
    engine = _engine()

    response = asyncio.run(engine.process_query(_POEM))

    assert engine.calls == [("document", "pdf", "essai_apercu_poeme")]
    assert response["type"] == "document_generation"
    assert response["filename"] == "essai_apercu_poeme.pdf"
    assert engine._last_documents == ["outputs/documents/essai_apercu_poeme.pdf"]


def test_a_document_file_request_reaches_the_tool_loop():
    """Avec Ollama, le court-circuit vers le code ne la prend plus : la boucle
    d'outils (generate_document) répond, comme à « rédige un document PDF »."""
    engine = _engine(mcp=True)

    response = asyncio.run(engine.process_query(_POEM))

    assert engine.calls == [("mcp", _POEM)]
    assert response["message"] == "Le PDF est prêt."


@pytest.mark.parametrize("mcp", [False, True])
def test_a_code_file_request_still_skips_the_tool_loop(mcp):
    engine = _engine(mcp=mcp)

    response = asyncio.run(engine.process_query("génère un fichier calcul.py"))

    assert engine.calls == [("code", "génère un fichier calcul.py")]
    assert response["type"] == "file_generation"
    assert response["filename"] == "calcul.py"


@pytest.mark.parametrize("stored", [{}, {"rapport.pdf": "contenu"}])
def test_the_keyword_router_classifies_document_files_first(stored):
    """« crée » menait au code ; avec un document en mémoire, « pdf » et
    « fichier » menaient à son analyse."""
    engine = _engine()
    engine.local_ai = SimpleNamespace(conversation_memory=SimpleNamespace(
        get_document_content=lambda: stored,
    ))

    assert engine._analyze_query_type(_POEM) == "document_generation"
