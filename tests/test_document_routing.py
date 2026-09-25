"""
Tests du routage « recherche puis document » (core/chat_orchestrator.py,
core/ai_engine.py).

Régressions de bugs observés en usage réel :
- sur « génère moi un docx sur les baleines », le modèle appelait d'abord
  `web_search`, puis l'orchestrateur forçait la synthèse — `generate_document`
  n'était jamais atteint et l'utilisateur recevait un résumé à la place du
  fichier ;
- sur « génère un pdf sur les dauphins », le modèle annonçait le document sans
  appeler l'outil, et la réponse s'arrêtait là ;
- « génère moi un tableau excel » partait en génération d'image.

Les helpers sont testés sans instancier AIEngine (dont l'initialisation charge
les modèles) : `_remember_research` et `_research_context` ne dépendent que de
l'attribut `_turn_research`.
"""

import pytest

from core.ai_engine import (
    _OUTLINE_MAX_SECTIONS,
    _RESEARCH_CONTEXT_MAX,
    _RESEARCH_TOOLS,
    AIEngine,
    _document_success_message,
)
from core.chat_orchestrator import (
    _DOCUMENT_NUDGE,
    _DOCUMENT_TOOLS,
    ChatOrchestrator,
    _announces_without_acting,
    _document_confirmation,
    _wants_document,
)

# Messages de succès réels renvoyés par les outils (cf. AIEngine._setup_local_tools).
_GENERATE_OK = _document_success_message({
    "format": "docx",
    "title": "Les baleines",
    "file_path": r"C:\Users\x\My_AI\outputs\documents\rapport.docx",
    "size": 40591,
    "outline": ["Introduction", "Espèces", "Conservation"],
})
_EDIT_OK = (
    r"Succès : 2 modification(s) appliquée(s). Copie modifiée écrite à "
    r"C:\out\rapport_modifie.docx. Le fichier d'origine (C:\src\rapport.docx) "
    "n'a pas été touché."
)


class _ResearchHolder:
    """Porteur minimal de l'état de recherche d'un tour."""

    def __init__(self):
        self._turn_research = []

    remember = AIEngine._remember_research
    context = AIEngine._research_context


# ── Détection d'une demande de document ────────────────────────────────────


@pytest.mark.parametrize(
    "query",
    [
        "génère moi un docx sur les baleines",
        "genere un document sur la conservation",
        "fais-moi un PDF de synthèse",
        "crée une présentation sur le climat",
        "génère un tableur excel des ventes",
        "rédige un rapport sur la conservation marine",
        "prépare un compte rendu de la réunion",
        "écris une note de synthèse en pdf",
    ],
)
def test_document_requests_are_detected(query):
    assert _wants_document(query) is True


@pytest.mark.parametrize(
    "query",
    [
        "résume ce document",
        "de quoi parle ce pdf ?",
        "cherche des infos sur les baleines",
        "quelle est la population des baleines",
        "supprime ce fichier",
        "explique-moi le format docx",
        "combien pèse une baleine bleue",
    ],
)
def test_non_production_requests_are_not_detected(query):
    """Lire ou parler d'un document n'est pas en produire un."""
    assert _wants_document(query) is False


def test_detection_requires_both_a_verb_and_a_document_word():
    # Verbe sans document → non
    assert _wants_document("génère une fonction python") is False
    # Document sans verbe de production → non
    assert _wants_document("ce rapport est intéressant") is False


def test_document_tools_are_the_producing_ones():
    assert _DOCUMENT_TOOLS == {"generate_document", "edit_document"}


# ── Confirmation de secours quand la synthèse n'aboutit pas ────────────────
#
# La synthèse du modèle présente normalement le document. Si elle ne produit
# rien (délai dépassé, Ollama tombé), l'utilisateur ne doit pas rester devant
# un chat vide alors que son fichier existe : un message construit à partir du
# résultat de l'outil prend le relais.


def test_generated_document_fallback_confirmation():
    message = _document_confirmation(
        [{"tool": "generate_document"}], {"generate_document": _GENERATE_OK}
    )
    assert message is not None
    assert "rapport.docx" in message
    assert "prêt" in message
    # Le chemin extrait s'arrête avant la taille et le plan
    assert "octets" not in message and "Plan du document" not in message


def test_success_message_carries_the_plan_for_the_synthesis():
    """Sans plan, la synthèse devrait inventer le contenu du document."""
    assert "Plan du document : Introduction ; Espèces ; Conservation." in _GENERATE_OK
    assert "« Les baleines »" in _GENERATE_OK


def test_success_message_caps_the_plan():
    sections = [f"Section {i}" for i in range(40)]
    message = _document_success_message({
        "format": "pdf", "title": "T", "file_path": "C:/x.pdf",
        "size": 1, "outline": sections,
    })
    assert f"Section {_OUTLINE_MAX_SECTIONS - 1}" in message
    assert f"Section {_OUTLINE_MAX_SECTIONS}" not in message


def test_success_message_without_sections():
    message = _document_success_message({
        "format": "md", "title": "T", "file_path": "C:/x.md", "size": 1, "outline": [],
    })
    assert "(pas de sections)" in message


def test_edited_document_confirmation_reassures_about_the_source():
    message = _document_confirmation(
        [{"tool": "edit_document"}], {"edit_document": _EDIT_OK}
    )
    assert message is not None
    assert "rapport_modifie.docx" in message
    assert "origine n'a pas été touché" in message


def test_no_fallback_when_the_last_tool_is_not_a_document():
    """Après une recherche, la synthèse normale doit reprendre la main."""
    assert (
        _document_confirmation(
            [{"tool": "generate_document"}, {"tool": "web_search"}],
            {"generate_document": _GENERATE_OK, "web_search": "des résultats"},
        )
        is None
    )


def test_no_fallback_on_tool_failure():
    """Un échec doit être expliqué par le modèle, pas masqué par un ✅."""
    assert (
        _document_confirmation(
            [{"tool": "generate_document"}],
            {"generate_document": "Génération impossible : Ollama arrêté"},
        )
        is None
    )


def test_no_fallback_without_tools():
    assert _document_confirmation([], {}) is None


def test_no_fallback_when_the_path_is_unreadable():
    """Sans chemin exploitable, mieux vaut laisser le modèle formuler."""
    assert (
        _document_confirmation(
            [{"tool": "generate_document"}], {"generate_document": "Succès."}
        )
        is None
    )


# ── Mémoire de recherche du tour ───────────────────────────────────────────


def test_search_results_are_remembered():
    holder = _ResearchHolder()
    holder.remember("web_search", "A" * 500)
    assert "web_search" in holder.context()
    assert "A" * 500 in holder.context()


def test_producing_tools_are_not_research():
    """Le chemin d'un document produit n'a rien à faire dans la documentation."""
    holder = _ResearchHolder()
    holder.remember("generate_document", "Succès : document créé à " + "x" * 300)
    holder.remember("write_local_file", "Succès : fichier écrit " + "y" * 300)
    assert holder.context() == ""


def test_short_or_empty_results_are_ignored():
    """Une erreur ou un « aucun résultat » n'aide pas le rédacteur."""
    holder = _ResearchHolder()
    holder.remember("web_search", "Aucun résultat trouvé.")
    holder.remember("search_memory", "")
    holder.remember("read_local_file", None)
    assert holder.context() == ""


def test_context_is_capped():
    holder = _ResearchHolder()
    for _ in range(10):
        holder.remember("web_search", "B" * 5000)
    context = holder.context()
    assert len(context) <= _RESEARCH_CONTEXT_MAX + 10
    assert context.endswith("[…]")


def test_several_tools_are_concatenated():
    holder = _ResearchHolder()
    holder.remember("web_search", "Résultat web " + "a" * 300)
    holder.remember("read_local_file", "Contenu fichier " + "b" * 300)
    context = holder.context()
    assert "[web_search]" in context and "[read_local_file]" in context


def test_research_tools_cover_the_collecting_ones():
    assert "web_search" in _RESEARCH_TOOLS
    assert "search_memory" in _RESEARCH_TOOLS
    assert "generate_document" not in _RESEARCH_TOOLS


# ── Le contexte atteint bien le rédacteur ──────────────────────────────────


def test_research_is_injected_into_the_writing_prompt(monkeypatch):
    """Sans cette injection, la recherche préalable serait jetée."""
    import asyncio

    from generators.document_generator import DocumentGenerator

    captured = {}

    class _FakeLLM:
        is_ollama_available = True

        def generate(self, prompt, system_prompt=None, **_kwargs):
            captured["prompt"] = prompt
            captured["system"] = system_prompt
            return "## Section\n\nContenu."

    generator = DocumentGenerator(llm=_FakeLLM())
    result = asyncio.run(
        generator.generate_document(
            "un rapport sur les baleines",
            fmt="md",
            research="Les baleines bleues mesurent jusqu'à 30 mètres.",
            filename="pytest_research",
        )
    )
    assert result["success"] is True
    assert "INFORMATIONS COLLECTÉES" in captured["prompt"]
    assert "30 mètres" in captured["prompt"]

    from pathlib import Path

    Path(result["file_path"]).unlink(missing_ok=True)


def test_no_research_leaves_the_prompt_clean():
    import asyncio

    from generators.document_generator import DocumentGenerator

    captured = {}

    class _FakeLLM:
        is_ollama_available = True

        def generate(self, prompt, system_prompt=None, **_kwargs):
            captured["prompt"] = prompt
            return "## Section\n\nContenu."

    generator = DocumentGenerator(llm=_FakeLLM())
    result = asyncio.run(
        generator.generate_document(
            "un rapport", fmt="md", filename="pytest_no_research"
        )
    )
    assert "INFORMATIONS COLLECTÉES" not in captured["prompt"]

    from pathlib import Path

    Path(result["file_path"]).unlink(missing_ok=True)


# ── Document annoncé sans appel d'outil ────────────────────────────────────
#
# Le modèle a répondu par cette annonce, sans appeler l'outil : la réponse
# s'arrêtait là et aucun fichier n'existait.

_ANNOUNCE = (
    "Je vais créer un document PDF sur les dauphins. Commençons par préparer "
    "le contenu informatif et puis générer le document."
)
_TOOLS = [
    {"type": "function", "function": {"name": "generate_document"}},
    {"type": "function", "function": {"name": "web_search"}},
]
_SYNTHESIS = "J'ai créé le PDF « Les dauphins » : il présente leurs espèces et leur habitat."
_GENERATE_CALL = {
    "name": "generate_document",
    "arguments": {"format": "pdf", "title": "Les dauphins", "brief": "les dauphins"},
}


@pytest.mark.parametrize(
    "answer",
    [
        _ANNOUNCE,
        "D'accord, je m’en occupe tout de suite.",
        "Je ne peux pas créer de fichier PDF.",
        "Sure, let me create that PDF for you.",
    ],
)
def test_announcements_are_detected(answer):
    assert _announces_without_acting(answer) is True


@pytest.mark.parametrize(
    "answer",
    [
        "Sur quel aspect des dauphins voulez-vous que le document porte ?",
        "Je vais créer le document. Quel format préférez-vous ?",
        "Les dauphins sont des mammifères marins très sociables.",
        "",
        "Je vais détailler chaque espèce. " + "Texte du document. " * 40,
    ],
)
def test_answers_and_questions_are_not_announcements(answer):
    """Une question ou une vraie réponse ne justifie pas de relancer le modèle."""
    assert _announces_without_acting(answer) is False


class _ScriptedLLM:
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


def _run_scripted(user_input, turns, tools=None):
    """
    Déroule l'orchestrateur sur des réponses de modèle écrites à l'avance.

    Chaque élément de ``turns`` est un tour du modèle : un texte, un appel
    d'outil (dict) ou None (Ollama injoignable).
    """
    orchestrator = ChatOrchestrator()
    script = list(turns)
    calls, shown, executed = [], [], []

    def fake_stream(**kwargs):
        # Copie : l'orchestrateur continue de remplir la même liste
        calls.append({**kwargs, "messages": list(kwargs["messages"])})
        turn = script.pop(0)
        if turn is None:
            return None
        if isinstance(turn, dict):
            return {"content": "", "tool_calls": [{"function": turn}], "streamed": False}
        if kwargs["on_token"]:
            kwargs["on_token"](turn)
        return {"content": turn, "tool_calls": [], "streamed": True}

    def fake_synthesis(**kwargs):
        kwargs["on_token"](_SYNTHESIS)
        return _SYNTHESIS

    def executor(name, _arguments):
        executed.append(name)
        return _GENERATE_OK

    orchestrator._call_ollama_smart_stream = fake_stream
    orchestrator._stream_synthesis = fake_synthesis
    llm = _ScriptedLLM()
    result = orchestrator.run(
        user_input=user_input,
        tools=_TOOLS if tools is None else tools,
        tool_executor=executor,
        llm=llm,
        system_prompt="système",
        on_token=shown.append,
    )
    return result, calls, shown, executed, llm


def test_announced_document_is_nudged_then_created():
    result, calls, shown, executed, _llm = _run_scripted(
        "génère un pdf sur les dauphins", [_ANNOUNCE, _GENERATE_CALL, ""]
    )
    assert executed == ["generate_document"]
    assert result == _SYNTHESIS
    # L'annonce reste en préambule, la synthèse s'y enchaîne
    assert shown == [_ANNOUNCE, _SYNTHESIS]
    # La relance dit au modèle qu'aucun fichier n'existe…
    assert calls[1]["messages"][-1]["content"] == _DOCUMENT_NUDGE
    # … et son tour n'est pas affiché : l'annonce est déjà à l'écran
    assert calls[1]["on_token"] is None


def test_a_single_nudge_then_the_first_answer_stands():
    """Si la relance reste sans effet, rien ne s'empile sous l'annonce."""
    result, calls, shown, executed, llm = _run_scripted(
        "génère un pdf sur les dauphins", [_ANNOUNCE, "Je vais m'en occuper."]
    )
    assert executed == []
    assert len(calls) == 2
    assert result == _ANNOUNCE
    assert shown == [_ANNOUNCE]
    replies = [m["content"] for m in llm.conversation_history if m["role"] == "assistant"]
    assert replies == [_ANNOUNCE]


def test_unreachable_model_during_the_nudge_keeps_the_first_answer():
    """Un None ferait relancer une génération sans outils qui doublerait l'annonce."""
    result, _calls, shown, _executed, _llm = _run_scripted(
        "génère un pdf sur les dauphins", [_ANNOUNCE, None]
    )
    assert result == _ANNOUNCE
    assert shown == [_ANNOUNCE]


@pytest.mark.parametrize(
    "user_input, answer",
    [
        ("génère un pdf", "Sur quel sujet voulez-vous ce PDF ?"),
        ("comment vas-tu ?", "Je vais bien, merci !"),
    ],
)
def test_no_nudge_for_questions_or_other_requests(user_input, answer):
    result, calls, shown, _executed, _llm = _run_scripted(user_input, [answer])
    assert len(calls) == 1
    assert result == answer and shown == [answer]


def test_no_nudge_when_the_document_tool_is_unavailable():
    web_only = [{"type": "function", "function": {"name": "web_search"}}]
    result, calls, _shown, _executed, _llm = _run_scripted(
        "génère un pdf sur les dauphins", [_ANNOUNCE], tools=web_only
    )
    assert len(calls) == 1
    assert result == _ANNOUNCE


# ── « Tableau » : données ou peinture ─────────────────────────────────────
#
# « génère moi un tableau excel fictif » partait en génération d'image :
# « tableau » y était lu comme une peinture.


class _ImageRouter:
    """Détection d'image d'AIEngine, sans initialiser le moteur."""

    _IMAGE_GEN_RE = AIEngine._IMAGE_GEN_RE
    _IMAGE_GEN_EXCLUDE_RE = AIEngine._IMAGE_GEN_EXCLUDE_RE
    is_image_generation_request = AIEngine.is_image_generation_request


@pytest.fixture(name="image_router")
def _image_router(monkeypatch):
    class _Config:
        @staticmethod
        def get(_key, default=None):
            return default

    # Indépendant du config.yaml local (image_generation.enabled)
    monkeypatch.setattr("core.ai_engine.get_config", _Config)
    return _ImageRouter()


_DATA_TABLES = [
    "génère moi un tableau excel fictif avec les données que tu veux",
    "génère un tableau comparatif des langages de programmation",
    "fais-moi un tableau des planètes du système solaire",
    "crée un tableau récapitulatif des ventes",
]
_PICTURES = [
    "génère un tableau impressionniste d'un port au coucher du soleil",
    "fais un tableau à l’huile représentant une forêt",
    "peins-moi un tableau de la mer",
    "génère moi une image de dauphin",
]


@pytest.mark.parametrize("query", _DATA_TABLES)
def test_data_tables_are_not_image_requests(image_router, query):
    assert image_router.is_image_generation_request(query) is False


@pytest.mark.parametrize("query", _PICTURES)
def test_paintings_and_images_still_are(image_router, query):
    assert image_router.is_image_generation_request(query) is True


def test_fallback_classifier_applies_the_same_rule():
    """Le classifieur de repli (sans Ollama) ne doit pas contredire le moteur."""
    from models.linguistic_patterns import LinguisticPatterns

    patterns = LinguisticPatterns()
    for query in _DATA_TABLES:
        assert "image_generation" not in patterns.detect_intent(query), query
    for query in _PICTURES:
        assert "image_generation" in patterns.detect_intent(query), query
