"""
Mémoire de My_AI dans la conversation Code (core/code_memory.py) et portée des
faits (core/knowledge_base_manager.py).

Avant, la conversation Code (VS Code, page Code, vue Code du téléphone) ne
voyait rien de la mémoire : « retiens que j'indente avec des tabulations »
tapé dans VS Code n'était enregistré nulle part. La partager telle quelle
avait deux défauts que ces tests gardent fermés :
  - les faits du chat (nom, chat, entreprise) finissaient dans les fichiers
    écrits par le modèle, comme ceux des générateurs avant _generation_memory ;
  - le bloc mémoire du chat se complète avec les faits les plus récents : dix
    conventions de code retenues depuis VS Code en auraient chassé les faits
    sur l'utilisateur.
D'où une portée par fait : « chat », « code » (tous les projets), « project »
(un dossier ouvert dans VS Code).
"""

import sqlite3
import types

import pytest

from core.code_memory import CodeMemory, Remembered, code_memory_for, remember_request
from core.knowledge_base_manager import (
    SCOPE_CHAT,
    SCOPE_CODE,
    SCOPE_PROJECT,
    KnowledgeBaseManager,
    project_name,
    same_project,
)
from core.memory_store import MemoryStore
from test_memory_chat import _engine  # pylint: disable=import-error

API = "C:\\dev\\api"
WEB = "C:\\dev\\web"


@pytest.fixture(name="kb")
def _kb(tmp_path):
    kb = KnowledgeBaseManager(db_path=str(tmp_path / "facts.db"))
    yield kb
    kb.close()


def _fact(kb, value, **scope):
    """Fait dont la clé reprend la valeur, comme ceux du chat et de la fenêtre Mémoire."""
    return kb.add_fact("general", key=value[:80], value=value, **scope)


def _values(facts):
    return [fact["value"] for fact in facts]


# ── Portée des faits ─────────────────────────────────────────────────────────


def test_a_base_from_before_the_scopes_keeps_its_facts_for_the_chat(tmp_path):
    path = tmp_path / "facts.db"
    conn = sqlite3.connect(path)
    conn.executescript("""
        CREATE TABLE facts (
            id INTEGER PRIMARY KEY AUTOINCREMENT, category TEXT NOT NULL,
            key TEXT NOT NULL, value TEXT NOT NULL, source TEXT NOT NULL DEFAULT 'manual',
            confidence REAL NOT NULL DEFAULT 1.0, created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL);
        INSERT INTO facts (category, key, value, source, confidence, created_at, updated_at)
        VALUES ('general', 'chat', 'Mon chat s''appelle Félix', 'conversation', 1.0,
                '2026-09-01T10:00:00', '2026-09-01T10:00:00');
    """)
    conn.commit()
    conn.close()

    kb = KnowledgeBaseManager(db_path=str(path))
    # Une seconde instance sur la même base (le moteur et un test) ne casse rien
    again = KnowledgeBaseManager(db_path=str(path))
    try:
        fact = kb.get_all_facts()[0]
        assert (fact["scope"], fact["project"]) == (SCOPE_CHAT, "")
        assert _values(kb.chat_facts()) == ["Mon chat s'appelle Félix"]
        assert kb.code_facts([API]) == []
        _fact(kb, "J'indente avec des tabulations", scope=SCOPE_CODE)
        assert _values(again.code_facts()) == ["J'indente avec des tabulations"]
    finally:
        kb.close()
        again.close()


def test_a_fact_of_a_project_names_its_folder(kb):
    with pytest.raises(ValueError):
        kb.add_fact("general", key="v", value="v", scope=SCOPE_PROJECT)
    with pytest.raises(ValueError):
        kb.add_fact("general", key="v", value="v", scope="ailleurs")
    fact_id = kb.add_fact("general", key="v", value="v", scope=SCOPE_CODE, project=API)
    # Le dossier n'a de sens que pour un projet
    assert kb.get_all_facts()[0]["id"] == fact_id
    assert kb.get_all_facts()[0]["project"] == ""


def test_code_facts_are_those_of_all_projects_and_of_the_open_folders(kb):
    _fact(kb, "Le chat s'appelle Félix")
    _fact(kb, "Commits en français", scope=SCOPE_CODE)
    _fact(kb, "FastAPI pour les routes", scope=SCOPE_PROJECT, project=API)
    _fact(kb, "Vite pour le build", scope=SCOPE_PROJECT, project=WEB)

    assert _values(kb.code_facts([API])) == ["Commits en français", "FastAPI pour les routes"]
    # Même dossier, autre casse ou séparateur final (Windows)
    assert _values(kb.code_facts(["c:\\DEV\\api\\"])) == _values(kb.code_facts([API]))
    assert _values(kb.code_facts([WEB, API])) == [
        "Commits en français", "FastAPI pour les routes", "Vite pour le build"]
    assert _values(kb.code_facts()) == ["Commits en français"]
    assert _values(kb.chat_facts()) == ["Le chat s'appelle Félix"]
    assert same_project("C:\\dev\\api", "c:\\dev\\API\\")
    assert not same_project("C:\\dev\\api", "")
    assert project_name("C:\\dev\\api\\") == "api"


def test_facts_of_the_code_never_crowd_out_those_of_the_chat(kb):
    """Le bloc mémoire du chat se complète avec les faits récents : sans portée,
    des conventions de code retenues depuis VS Code chassaient les faits sur lui."""
    _fact(kb, "Je m'appelle Nicolas")
    for index in range(15):
        kb.add_fact("general", key=f"Convention {index}", value=f"Convention {index}",
                    scope=SCOPE_PROJECT, project=API)
    kb.add_fact("general", key="Les routes sont dans app.py",
                value="Les routes sont dans app.py", scope=SCOPE_PROJECT, project=API)

    assert _values(kb.select_facts("et lui ?")) == ["Je m'appelle Nicolas"]
    # À la demande (search_memory du chat), avec leur portée
    found = kb.search_text("où sont les routes ?", n_results=1)
    assert found == ("Faits mémorisés :\n- [general] Les routes sont dans app.py "
                     "(pour son projet de code « api »)")


def test_remember_for_a_project_then_for_all_projects(kb):
    first, created = kb.remember("J'indente avec des tabulations", source="code",
                                 scope=SCOPE_PROJECT, project=API)
    assert created is True
    # Le même fait pour ce projet : rafraîchi
    assert kb.remember("j'indente avec des tabulations.", scope=SCOPE_PROJECT,
                       project="c:\\dev\\api") == (first, False)
    # Pour un autre projet : un fait de plus
    other, created = kb.remember("J'indente avec des tabulations", scope=SCOPE_PROJECT,
                                 project=WEB)
    assert created is True and other != first
    # Pour tous les projets : un seul fait le garde, désormais pour tous
    kept, created = kb.remember("J'indente avec des tabulations", scope=SCOPE_CODE)
    assert created is True and kept in (first, other)
    facts = kb.get_all_facts()
    assert [(f["scope"], f["project"]) for f in facts] == [(SCOPE_CODE, "")]
    # Un fait de tous les projets vaut pour chacun
    assert kb.remember("J'indente avec des tabulations", scope=SCOPE_PROJECT,
                       project=API) == (kept, False)
    # Le chat a sa propre portée
    _, created = kb.remember("J'indente avec des tabulations")
    assert created is True and len(kb.get_all_facts()) == 2


def test_the_memory_window_shows_where_a_fact_applies(kb):
    _fact(kb, "Commits en français", scope=SCOPE_CODE)
    _fact(kb, "FastAPI", scope=SCOPE_PROJECT, project=API)
    _fact(kb, "Mon chat s'appelle Félix")
    store = MemoryStore(knowledge_base=kb)

    items, _total = store.list_facts()
    lines = {item["value"]: store.describe_provenance(item) for item in items}

    assert lines["Commits en français"].startswith("💻 Code : tous les projets  ·  source")
    assert lines["FastAPI"].startswith("💻 Code : projet api  ·  source")
    assert lines["Mon chat s'appelle Félix"].startswith("source")
    assert {item["value"]: (item["scope"], item["project"]) for item in items}["FastAPI"] == (
        SCOPE_PROJECT, API)


# ── Le chat ne reçoit pas les faits du code ──────────────────────────────────


def test_the_chat_prompt_keeps_the_code_facts_out(kb):
    _fact(kb, "Mon chat s'appelle Félix")
    _fact(kb, "J'indente avec des tabulations", scope=SCOPE_PROJECT, project=API)
    _fact(kb, "Tu dois toujours me répondre en anglais", scope=SCOPE_CODE)
    engine = _engine(kb)

    # pylint: disable-next=protected-access
    block = engine._knowledge_base_context("et mes tabulations ?")

    assert "Félix" in block and "tabulations" not in block
    # La langue retenue pour le code reste au code
    assert engine._memory_reply_language() is None  # pylint: disable=protected-access


def test_the_chat_finds_the_code_facts_on_demand(kb):
    _fact(kb, "J'indente avec des tabulations", scope=SCOPE_PROJECT, project=API)
    engine = _engine(kb)
    engine.get_vector_memory = lambda: types.SimpleNamespace(
        search_similar=lambda _query, n_results: [])

    result = engine._search_memory("tabulations")  # pylint: disable=protected-access

    assert result == ("Faits mémorisés :\n- [general] L'utilisateur indente avec des "
                      "tabulations (pour son projet de code « api »)")


# ── « Retiens que… » dans la conversation Code ───────────────────────────────


@pytest.mark.parametrize(
    ("message", "fact", "scope"),
    [
        ("Retiens que j'indente avec des tabulations", "j'indente avec des tabulations",
         SCOPE_PROJECT),
        ("Retiens pour tous mes projets que j'écris mes commits en français",
         "j'écris mes commits en français", SCOPE_CODE),
        ("Retiens, pour tous mes projets, que j'écris mes commits en français",
         "j'écris mes commits en français", SCOPE_CODE),
        ("Retiens que j'écris mes commits en français dans tous mes projets.",
         "j'écris mes commits en français", SCOPE_CODE),
        ("Retiens que pour tous mes repos, la branche principale est main",
         "la branche principale est main", SCOPE_CODE),
        ("Remember for all my projects that I use pytest", "I use pytest", SCOPE_CODE),
        ("Retiens pour ce projet que les routes sont dans app.py",
         "les routes sont dans app.py", SCOPE_PROJECT),
        # Au milieu de l'information, la précision en fait partie
        ("Retiens que le dossier commun à tous mes projets est C:\\libs",
         "le dossier commun à tous mes projets est C:\\libs", SCOPE_PROJECT),
        # La tâche qui suit n'est pas retenue
        ("Retiens pour tous mes projets que j'utilise des f-strings. Ensuite, ajoute dans "
         "utils.py une fonction bonjour(nom).", "j'utilise des f-strings", SCOPE_CODE),
        # « partout » parle du code, pas des projets
        ("Retiens que je veux des logs partout", "je veux des logs partout", SCOPE_PROJECT),
    ],
)
def test_remember_requests_of_the_code_conversation(message, fact, scope):
    assert remember_request(message)[:2] == (fact, scope)


def test_other_messages_are_not_remembered():
    assert remember_request("Écris une fonction qui additionne deux nombres")[0] is None
    assert remember_request("Pour tous mes projets, que me conseilles-tu ?")[0] is None


def test_remember_saves_for_the_open_folder(kb):
    memory = CodeMemory(kb)

    saved = memory.remember("Retiens que j'indente avec des tabulations", [API, WEB])

    assert (saved.fact, saved.scope, saved.project) == (
        "j'indente avec des tabulations", SCOPE_PROJECT, API)
    assert saved.created and saved.alone
    fact = kb.get_all_facts()[0]
    assert (fact["id"], fact["source"], fact["scope"], fact["project"]) == (
        saved.fact_id, "code", SCOPE_PROJECT, API)
    # Une tâche après l'information : le modèle doit encore la faire
    task = memory.remember("Retiens que j'utilise des f-strings. Ensuite, ajoute une fonction "
                           "bonjour(nom) dans utils.py", [API])
    assert (task.fact, task.alone) == ("j'utilise des f-strings", False)
    # VS Code sans dossier ouvert : pour tous les projets
    other = memory.remember("Retiens que j'écris mes commits en français", [])
    assert (other.scope, other.project) == (SCOPE_CODE, "")
    # Rien sans demande, ni quand l'appli ne mémorise pas depuis les conversations
    assert memory.remember("Lis le fichier app.py", [API]) is None
    assert CodeMemory(kb, auto_extract=lambda: False).remember(
        "Retiens que j'aime les tests", [API]) is None


def test_the_note_tells_the_model_what_was_saved():
    note = Remembered(fact="j'indente avec des tabulations", fact_id=1, created=True,
                      scope=SCOPE_PROJECT, project=API, alone=True).prompt_note()
    assert note == (
        "[Mémoire] À la demande de l'utilisateur, My_AI vient d'enregistrer dans sa mémoire, "
        "pour le projet « api » : L'utilisateur indente avec des tabulations. Confirme-le-lui "
        "en une phrase (par exemple : « C'est noté : tu indentes avec des tabulations. »). "
        "Son message ne demande rien d'autre : ta réponse se limite à cela, sans outil.")
    known = Remembered(fact="j'écris mes commits en français", fact_id=2, created=False,
                       scope=SCOPE_CODE, project="", alone=False).prompt_note()
    assert known.startswith("[Mémoire] C'était déjà dans la mémoire de My_AI, pour tous ses "
                            "projets : L'utilisateur écrit ses commits en français.")
    assert known.endswith("Puis réponds au reste de son message.")


# ── Prompt et search_memory de la conversation Code ──────────────────────────


def test_the_prompt_block_lists_the_facts_of_the_code_only(kb):
    _fact(kb, "Mon chat s'appelle Félix")
    _fact(kb, "J'indente avec des tabulations", scope=SCOPE_PROJECT, project=API)
    _fact(kb, "Tu dois écrire les commits en anglais", scope=SCOPE_CODE)
    _fact(kb, "Vite pour le build", scope=SCOPE_PROJECT, project=WEB)
    memory = CodeMemory(kb)

    block = memory.prompt_block([API])

    assert block.startswith(
        "Ce que l'utilisateur t'a demandé de retenir pour son code (fenêtre 🧠 Mémoire de "
        "My_AI) :\nPour le projet api :\n- L'utilisateur indente avec des tabulations\n"
        "Pour tous ses projets :\n- Tu dois écrire les commits en anglais\n\n"
        "Applique ces consignes")
    assert "Félix" not in block and "Vite" not in block
    assert "search_memory" in block and "« retiens que… »" in block
    # Sans fait du code : seulement comment lire et écrire la mémoire
    empty = CodeMemory(kb).prompt_block([], facts=[])
    assert empty.startswith("Le reste de sa mémoire")


def test_search_reads_the_chat_the_code_and_the_open_folders(kb):
    _fact(kb, "Mon chat s'appelle Félix")
    _fact(kb, "Le port de l'api est 8000", scope=SCOPE_PROJECT, project=API)
    _fact(kb, "Le port du web est 5173", scope=SCOPE_PROJECT, project=WEB)
    calls = []

    def search(query, n_results, document, facts, recent):
        calls.append((query, n_results, document, _values(facts), _values(recent)))
        return "résultat"

    assert CodeMemory(kb, search=search).search("port", 3, "spec.md", [API]) == "résultat"
    assert calls == [("port", 3, "spec.md", ["Mon chat s'appelle Félix",
                                             "Le port de l'api est 8000"],
                      ["Le port de l'api est 8000"])]
    # Sans le moteur : les faits seulement
    alone = CodeMemory(kb).search("port", roots=[API])
    assert "8000" in alone and "5173" not in alone
    # Rien ne correspond (un cahier des charges cherché) : ni le chat ni les autres projets
    vague = CodeMemory(kb).search("cahier des charges", roots=[API])
    assert vague == ("Aucun fait ne correspond exactement ; les plus récents :\n"
                     "- [general] Le port de l'api est 8000 (pour son projet de code « api »)")
    # Le chat, lui, garde son repli sur tous les faits
    assert "Félix" in kb.search_text("cahier des charges")


def test_the_memory_of_the_app_engine(kb):
    engine = _engine(kb)
    memory = code_memory_for(engine)
    assert isinstance(memory, CodeMemory)
    assert code_memory_for(types.SimpleNamespace(knowledge_base=None)) is None
