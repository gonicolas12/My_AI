"""
Tests des documents de la mémoire pour le modèle (core/memory_documents.py, et
leur usage par core/ai_engine.py : contexte de la réponse, outil search_memory)

Deux documents peuvent porter le même nom : « rapport.pdf » ajouté à la main,
un autre joint au chat, « projet/docs/rapport.pdf » venu d'un dossier déposé.
Le modèle doit savoir lequel lire selon la demande, et ne pas les confondre.
"""
# pylint: disable=protected-access

import logging
import types

from core import ai_engine
from core.ai_engine import AIEngine
from core.memory_documents import (MAX_NAMED, document_label, memory_documents_block,
                                   named_documents, named_folders, resolve_documents,
                                   results_block)

INDEX = [
    {"id": "a", "name": "rapport.pdf", "label": "rapport.pdf", "folder": None,
     "folder_key": None, "created": "2026-11-17T11:19:00", "source": "manual"},
    {"id": "b", "name": "projet/docs/rapport.pdf", "label": "docs/rapport.pdf",
     "folder": "projet", "folder_key": "f1", "created": "2026-11-16T09:05:00",
     "source": "manual"},
    {"id": "c", "name": "rapport.pdf", "label": "rapport.pdf", "folder": None,
     "folder_key": None, "created": "2026-11-12T09:02:00", "source": None},
    {"id": "d", "name": "rapport_trimestriel.pdf", "label": "rapport_trimestriel.pdf",
     "folder": None, "folder_key": None, "created": "2026-10-08T14:30:00", "source": None},
    {"id": "e", "name": "notes.txt", "label": "notes.txt", "folder": None,
     "folder_key": None, "created": "2026-10-08T14:30:00", "source": "manual"},
    {"id": "g", "name": "projet/src/app.py", "label": "src/app.py", "folder": "projet",
     "folder_key": "f1", "created": "2026-11-16T09:05:00", "source": "manual"},
]

TEXTS = {
    "a": "Rapport ajouté à la main : budget de 12 000 euros.",
    "b": "Rapport du dossier projet : livraison le 28 novembre.",
    "c": "Rapport joint au chat : réunion annulée.",
    "d": "Rapport trimestriel : chiffre d'affaires en hausse de 12 %.",
    "e": "Notes du lundi.",
    "g": "def main(): pass",
}


def _ids(docs):
    return [doc["id"] for doc in docs]


def test_each_document_has_a_label_with_its_origin_and_date():
    assert document_label(INDEX[0]) == "« rapport.pdf » — ajouté à la main le 17/11/2026 à 11:19"
    assert document_label(INDEX[1]) == (
        "« projet/docs/rapport.pdf » — fichier du dossier « projet », déposé le 16/11/2026 "
        "à 09:05")
    assert document_label(INDEX[2]) == "« rapport.pdf » — joint au chat le 12/11/2026 à 09:02"
    # Métadonnées d'un morceau (outil search_memory), date illisible
    assert document_label({"document_name": "x.md", "created": "?"}) == "« x.md » — joint au chat"


def test_the_documents_a_message_names():
    # Un nom porté par plusieurs : tous, du plus récent au plus ancien
    assert _ids(named_documents("Résume rapport.pdf", INDEX)) == ["a", "b", "c"]
    # Le dossier nommé aussi : seulement le sien
    assert _ids(named_documents("que dit le rapport.pdf du dossier projet ?", INDEX)) == ["b"]
    assert _ids(named_documents("ouvre projet/docs/rapport.pdf", INDEX)) == ["b"]
    # Sans extension : un nom distinctif (deux mots, ou un chiffre) suffit
    assert _ids(named_documents("et le rapport trimestriel ?", INDEX)) == ["d"]
    assert _ids(named_documents("lis notes.txt", INDEX)) == ["e"]
    # Un mot courant n'est pas un nom de document ; ni une partie d'un autre nom
    for message in ("lis mes notes", "un rapport sur les baleines", "rapport.pdfx",
                    "le fichier xrapport.pdf", ""):
        assert not named_documents(message, INDEX), message


def test_a_file_attached_to_the_conversation_wins():
    """« rapport.pdf » joint à la conversation : c'est de lui qu'on parle ; ceux
    de la mémoire ne s'y mêlent pas, sauf si le message nomme leur dossier."""
    assert not named_documents("Résume rapport.pdf", INDEX, {"rapport.pdf"})
    assert _ids(named_documents("compare rapport.pdf avec celui du dossier projet", INDEX,
                                {"rapport.pdf"})) == ["b"]


def test_punctuation_next_to_a_name():
    """Vu avec le vrai modèle : « du dossier projet, il parle de quoi ? » ; la
    virgule collée au nom du dossier le cachait."""
    message = "Et le rapport.pdf du dossier projet, il parle de quoi ?"
    assert _ids(named_documents(message, INDEX, {"rapport.pdf"})) == ["b"]
    assert [folder["key"] for folder in named_folders(message, INDEX)] == ["f1"]
    assert _ids(named_documents("(dossier «projet») : rapport.pdf", INDEX)) == ["b"]
    assert _ids(named_documents("Le rapport trimestriel, tu l'as ?", INDEX)) == ["d"]


def test_the_folders_a_message_names():
    folders = named_folders("Que contient le dossier projet ?", INDEX)
    assert [(folder["key"], sorted(folder["files"])) for folder in folders] == [
        ("f1", ["docs/rapport.pdf", "src/app.py"])]
    assert not named_folders("parle-moi du projet", INDEX)  # sans « dossier »


def test_a_document_designated_by_the_search_tool():
    assert _ids(resolve_documents("rapport.pdf", INDEX)) == ["a", "c"]
    assert _ids(resolve_documents("« projet/docs/rapport.pdf »", INDEX)) == ["b"]
    assert _ids(resolve_documents("projet", INDEX)) == ["b", "g"]
    assert _ids(resolve_documents("Rapport Trimestriel", INDEX)) == ["d"]
    assert not resolve_documents("inconnu.pdf", INDEX) and not resolve_documents(" ", INDEX)


def test_search_results_are_grouped_by_document_with_a_warning():
    results = [
        {"content": "budget de 12 000 euros", "metadata": {
            "document_id": "a", "document_name": "rapport.pdf", "source": "manual",
            "created": "2026-11-17T11:19:00"}},
        {"content": "livraison le 28 novembre", "metadata": {
            "document_id": "b", "document_name": "projet/docs/rapport.pdf", "folder": "projet",
            "created": "2026-11-16T09:05:00"}},
        {"content": "dépenses détaillées", "metadata": {
            "document_id": "a", "document_name": "rapport.pdf", "source": "manual",
            "created": "2026-11-17T11:19:00"}},
    ]
    block = results_block(results)
    assert block.startswith("⚠️ Plusieurs documents DIFFÉRENTS portent le même nom "
                            "(« rapport.pdf »)")
    assert ("[1] « rapport.pdf » — ajouté à la main le 17/11/2026 à 11:19\n"
            "budget de 12 000 euros\n[…]\ndépenses détaillées") in block
    assert block.endswith("[2] « projet/docs/rapport.pdf » — fichier du dossier « projet », "
                          "déposé le 16/11/2026 à 09:05\nlivraison le 28 novembre")
    assert "⚠️" not in results_block(results[:1])


class _Store:
    """MemoryStore : l'index ci-dessus et le texte de chaque document."""

    def __init__(self, index=None):
        self.index = INDEX if index is None else index
        self.read = []

    def document_index(self):
        return self.index

    def document_text(self, document_id):
        self.read.append(document_id)
        return TEXTS.get(document_id, f"Texte de {document_id}.")


def _block(query, store=None, exclude=None, search=None):
    return memory_documents_block(query, store or _Store(), 3000,
                                  lambda text, _question, limit: text[:limit],
                                  exclude=exclude, search=search)


def test_the_named_documents_go_into_the_prompt_under_their_label():
    block = _block("Résume rapport.pdf")
    assert block.startswith("DOCUMENTS DE LA MÉMOIRE NOMMÉS DANS LA QUESTION")
    assert ("⚠️ 3 documents DIFFÉRENTS s'appellent « rapport.pdf » (n° 1, n° 2 et n° 3 "
            "ci-dessous) : ne les confonds pas, ne mélange pas leurs contenus.") in block
    for doc_id in ("a", "b", "c"):
        assert TEXTS[doc_id] in block
    assert block.index("=== Document n° 1 : « rapport.pdf » — ajouté à la main") < block.index(
        "=== Document n° 2 : « projet/docs/rapport.pdf »") < block.index(
        "=== Document n° 3 : « rapport.pdf » — joint au chat")
    # Après leur contenu, le rappel : les 3, sauf si la question dit lequel
    assert block.endswith(
        f"{TEXTS['c']}\n\nRAPPEL : si la question ne précise pas lequel des 3 « rapport.pdf » "
        "(son dossier, « ajouté à la main », « joint au chat » ou sa date), réponds pour les "
        "3, l'un après l'autre, chacun sous un titre qui dit lequel c'est. Si elle le précise, "
        "réponds seulement d'après celui-là.")
    # Le dossier nommé : un seul document, sans numéro, avertissement ni rappel
    narrowed = _block("que dit le rapport.pdf du dossier projet ?")
    assert TEXTS["b"] in narrowed and TEXTS["a"] not in narrowed
    assert "=== « projet/docs/rapport.pdf »" in narrowed
    assert not any(word in narrowed for word in ("⚠️", "n° 1", "RAPPEL"))
    # Deux documents de noms différents : numérotés, sans avertissement
    both = _block("compare rapport_trimestriel.pdf et notes.txt")
    assert "=== Document n° 2 : « notes.txt »" in both and "RAPPEL" not in both
    # Rien de nommé, ou le fichier joint à la conversation : rien
    assert _block("Bonjour, ça va ?") == ""
    assert _block("Résume rapport.pdf", exclude={"rapport.pdf"}) == ""


def test_at_most_a_few_documents_of_the_same_name():
    index = [{**INDEX[0], "id": f"r{n}", "created": f"2026-11-{17 - n:02d}T10:00:00"}
             for n in range(MAX_NAMED + 2)]
    store = _Store(index)
    block = _block("rapport.pdf", store)
    assert store.read == [f"r{n}" for n in range(MAX_NAMED)]  # les plus récents
    assert "(+2 autre(s) document(s) plus ancien(s) de ce nom, non montré(s).)" in block


def test_a_named_folder_lists_its_files_and_closest_passages():
    calls = []

    def search(query, n_results, where):
        calls.append((query, n_results, where))
        return [{"content": "def main(): pass", "metadata": {
            "document_id": "g", "document_name": "projet/src/app.py", "folder": "projet",
            "created": "2026-11-16T09:05:00"}}]

    block = _block("Que contient le dossier projet ?", search=search)
    assert block.startswith("DOSSIER DE LA MÉMOIRE NOMMÉ DANS LA QUESTION : « projet » "
                            "(déposé le 16/11/2026 à 09:05), 2 fichier(s) : docs/rapport.pdf, "
                            "src/app.py")
    assert calls == [("Que contient le dossier projet ?", 4, {"folder_id": "f1"})]
    assert "[1] « projet/src/app.py »" in block


def _engine(store, results=None):
    """AIEngine sans __init__ : le MemoryStore et la recherche de la mémoire simulés."""
    engine = AIEngine.__new__(AIEngine)
    engine.logger = logging.getLogger(__name__)
    engine.knowledge_base = None
    engine._visible_documents = None
    engine.local_ai = types.SimpleNamespace(
        local_llm=types.SimpleNamespace(gen_num_ctx=8192),
        conversation_memory=types.SimpleNamespace(stored_documents={}))
    searches = []

    def search_similar(query, n_results=5, **options):
        searches.append((query, n_results, options))
        return results or []

    engine.get_memory_store = lambda: store
    engine.get_vector_memory = lambda: types.SimpleNamespace(search_similar=search_similar)
    engine.searches = searches
    return engine


def test_the_engine_puts_the_named_documents_in_the_answer_context(monkeypatch):
    monkeypatch.setattr(ai_engine, "passage_similarities", lambda _query, _passages: None)
    engine = _engine(_Store())
    context = engine._memory_documents_context("Que dit le rapport trimestriel ?")
    assert "=== « rapport_trimestriel.pdf » — joint au chat le 08/10/2026 à 14:30 ===" in context
    assert TEXTS["d"] in context
    # Le fichier joint à la conversation affichée passe avant celui de la mémoire
    engine.local_ai.conversation_memory.stored_documents = {"rapport.pdf": {"content": "x"}}
    assert engine._memory_documents_context("Résume rapport.pdf") == ""
    # Mémoire indisponible : rien, sans erreur
    broken = _engine(None)
    assert broken._memory_documents_context("Résume rapport.pdf") == ""


def test_search_memory_can_be_restricted_to_a_document():
    engine = _engine(_Store(), results=[{"content": "livraison le 28 novembre", "metadata": {
        "document_id": "b", "document_name": "projet/docs/rapport.pdf", "folder": "projet",
        "created": "2026-11-16T09:05:00"}}])
    result = engine._search_memory("date de livraison", document="projet/docs/rapport.pdf")
    assert engine.searches[-1] == ("date de livraison", 5, {"where": {"document_id": "b"}})
    assert "[1] « projet/docs/rapport.pdf » — fichier du dossier « projet »" in result
    # Un nom porté par deux documents : les deux ; un nom inconnu : toute la mémoire
    engine._search_memory("budget", document="rapport.pdf")
    assert engine.searches[-1][2] == {"where": {"document_id": {"$in": ["a", "c"]}}}
    result = engine._search_memory("budget", document="facture.pdf")
    assert engine.searches[-1][2] == {}
    assert result.startswith("Aucun document nommé « facture.pdf » dans la mémoire : "
                             "recherche dans toute la mémoire.")
