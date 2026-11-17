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
from core.memory_documents import (MAX_NAMED, document_label, documents_at, folders_near,
                                   memory_documents_block, memory_links, named_documents,
                                   named_folders, resolve_documents, results_block,
                                   unmentioned_near_folders)

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


ONEDRIVE = {"id": "x", "name": "OneDrive_3_06-10-2026/Data.xlsx", "label": "Data.xlsx",
            "folder": "OneDrive_3_06-10-2026", "folder_key": "f2",
            "created": "2026-11-17T12:00:00", "source": "manual"}


def test_a_folder_named_by_part_of_its_name():
    """Vu avec my_ai : « mon dossier onedrive que tu as en mémoire » ne désignait pas
    « OneDrive_3_06-10-2026 » ; il listait alors parfois un dossier du disque."""
    index = INDEX + [ONEDRIVE]
    for message in ("il y a quoi dans mon dossier onedrive que tu as en mémoire ?",
                    "Dans ma mémoire, le dossier One Drive contient quoi ?"):
        assert [folder["key"] for folder in named_folders(message, index)] == ["f2"], message
    # Sans parler de la mémoire : peut-être un dossier du disque ; un nombre ne suffit pas
    assert not named_folders("liste mon dossier onedrive", index)
    assert not named_folders("le dossier 2026 en mémoire", index)
    # Un fichier nommé avec un bout du nom de son dossier : seulement celui de ce dossier
    alone = {**ONEDRIVE, "id": "y", "name": "Data.xlsx", "label": "Data.xlsx", "folder": None,
             "folder_key": None}
    assert _ids(named_documents("le Data.xlsx du dossier onedrive", index + [alone])) == ["x"]


# La question sur le dossier « OneDrive_3_06-10-2026 » de la mémoire, dans chaque langue
WITH_MEMORY = {
    "fr": "il y a quoi dans mon dossier onedrive que tu as en mémoire ?",
    "en": "What's in my OneDrive folder in your memory?",
    "de": "Was ist in meinem OneDrive-Ordner in deinem Gedächtnis?",
    "es": "¿Qué hay en mi carpeta OneDrive de tu memoria?",
    "it": "Cosa c'è nella cartella OneDrive nella tua memoria?",
    "nl": "Wat zit er in mijn OneDrive-map in je geheugen?",
    "pt": "O que há na minha pasta OneDrive na sua memória?",
    "ru": "Что лежит в моей папке OneDrive в твоей памяти?",
    "ar": "ماذا يوجد في مجلد OneDrive في ذاكرتك؟",
    "ja": "記憶にあるOneDriveフォルダには何がありますか？",
    "ko": "기억에 있는 OneDrive 폴더에는 뭐가 있어?",
    "zh": "你记忆里的OneDrive文件夹里有什么？",
}


def test_folder_and_memory_words_in_the_12_languages():
    index = INDEX + [ONEDRIVE]
    for lang, message in WITH_MEMORY.items():
        assert [folder["key"] for folder in named_folders(message, index)] == ["f2"], lang
        assert not folders_near(message, index), lang


def test_a_folder_with_a_close_name_is_pointed_out():
    """« mon dossier onedrive » sans parler de la mémoire : peut-être le vrai OneDrive ;
    le modèle signale celui de la mémoire, sans le confondre avec le disque."""
    index = INDEX + [ONEDRIVE]
    for message in ("il y a quoi dans mon dossier onedrive ?", "What's in my OneDrive folder?",
                    "OneDriveフォルダには何がありますか？"):
        assert not named_folders(message, index), message
        assert [folder["key"] for folder in folders_near(message, index)] == ["f2"], message
    assert _block("il y a quoi dans mon dossier onedrive ?", _Store(index)) == (
        "À SAVOIR : la mémoire (fenêtre Mémoire, onglet Documents) contient aussi un dossier "
        "au nom proche de celui de la question : « OneDrive_3_06-10-2026 » (déposé le "
        "17/11/2026 à 12:00), 1 fichier(s) : Data.xlsx. La question ne dit pas si elle parle de "
        "lui ou d'un dossier du disque : ne les confonds pas. S'il s'agit de lui, lis-le avec "
        "l'outil search_memory, document=\"OneDrive_3_06-10-2026\" (sans citer l'outil dans ta "
        "réponse).")
    # Son nom entier (il est alors nommé), ou un dossier sans rapport : pas de signal
    assert not folders_near("le dossier OneDrive_3_06-10-2026", index)
    assert not folders_near("range ça dans le dossier photos", index)


def test_a_close_folder_the_answer_does_not_cite_is_signaled_under_it():
    """my_ai ne signalait qu'une fois sur trois le dossier de la mémoire après avoir
    regardé le disque : la fenêtre le fait, sauf si la réponse le cite déjà."""
    index = INDEX + [ONEDRIVE]
    question = "il y a quoi dans mon dossier onedrive ?"
    assert unmentioned_near_folders(question, "Ton OneDrive contient desktop.ini.", index) == [
        {"name": "OneDrive_3_06-10-2026", "files": 1}]
    assert not unmentioned_near_folders(
        question, "Le dossier onedrive_3_06-10-2026 contient des commandes.", index)
    # Un de ses fichiers cité : la réponse parle déjà de ce dossier de la mémoire
    assert not unmentioned_near_folders(question, "Ton dossier contient `Data.xlsx`.", index)
    assert unmentioned_near_folders(question, "Ton dossier contient MyData.xlsx.", index)
    # La question parle de la mémoire (le dossier est alors nommé), ou pas de réponse
    assert not unmentioned_near_folders(question + " en mémoire", "desktop.ini", index)
    assert not unmentioned_near_folders(question, "", index)


def test_names_next_to_japanese_chinese_korean():
    index = [ONEDRIVE]
    for message in ("Data.xlsxの中身は？", "Data.xlsx를 보여줘", "Data.xlsx里有什么？"):
        assert _ids(named_documents(message, index)) == ["x"], message
        assert [link["text"] for link in memory_links(message, index)] == ["Data.xlsx"], message
    # Collé à un autre mot latin, ou une autre extension : pas ce fichier
    for message in ("MyData.xlsx", "Data.xlsx.bak", "Data.xlsxs"):
        assert not named_documents(message, index) and not memory_links(message, index), message


def test_documents_and_folders_cited_in_an_answer():
    """Vu dans l'appli : « [Dossier OneDrive_3_06-10-2026](memory://one drive) » et
    `Data.xlsx` ; la fenêtre rend cliquables les documents et dossiers cités."""
    answer = ("📁 **[Dossier OneDrive_3_06-10-2026](memory://one drive)**\n"
              "- `Data.xlsx` et le rapport.pdf du dossier projet ; projet/docs/rapport.pdf aussi.")
    assert memory_links(answer, INDEX + [ONEDRIVE]) == [
        {"text": "projet/docs/rapport.pdf", "kind": "document",
         "name": "projet/docs/rapport.pdf", "strict": False},
        {"text": "OneDrive_3_06-10-2026", "kind": "folder", "name": "OneDrive_3_06-10-2026",
         "strict": False},
        {"text": "rapport.pdf", "kind": "document", "name": "rapport.pdf", "strict": False},
        {"text": "Data.xlsx", "kind": "document", "name": "Data.xlsx", "strict": False},
        # Un nom courant : cliquable seulement dans un lien ou du code (la fenêtre)
        {"text": "projet", "kind": "folder", "name": "projet", "strict": True},
    ]


def test_a_cited_name_is_whole_and_outside_disk_paths():
    index = [ONEDRIVE]
    assert not memory_links(r"Voir C:\Users\moi\Data.xlsx, MyData.xlsx ou Data.xlsx.bak", index)
    # Casse ignorée, le texte tel qu'écrit ; le schéma d'un lien inventé ne compte pas
    assert memory_links("le fichier DATA.XLSX", index)[0]["text"] == "DATA.XLSX"
    assert memory_links("[données](memory://Data.xlsx)", index)[0]["name"] == "Data.xlsx"
    assert memory_links("", index) == [] and memory_links("Data.xlsx", []) == []
    # Le chemin d'un fichier dans son dossier, comme l'onglet l'affiche
    assert [link["text"] for link in memory_links("le fichier `docs/rapport.pdf`", INDEX)] == [
        "docs/rapport.pdf"]


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
                            "src/app.py\nIl est dans la mémoire (fenêtre Mémoire, onglet "
                            "Documents), pas sur le disque : réponds d'après ses fichiers et les "
                            "extraits ci-dessous ; pour en lire plus : outil search_memory, "
                            'document="projet" (sans citer l\'outil dans ta réponse).')
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


def test_a_memory_file_read_from_a_path_that_is_not_on_disk():
    """my_ai a essayé read_local_file("OneDrive_3_06-10-2026/Data.xlsx") : ce fichier est
    dans la mémoire, pas sur le disque ; l'outil le lit là, sous son libellé."""
    index = INDEX + [ONEDRIVE]
    assert _ids(documents_at("OneDrive_3_06-10-2026/Data.xlsx", index)) == ["x"]
    # Chemin inventé : son nom de fichier ; jamais un dossier entier
    assert _ids(documents_at(r"C:\Users\moi\inventé\data.xlsx", index)) == ["x"]
    assert _ids(documents_at("file:///C:/x/rapport.pdf", index)) == ["a", "b", "c"]
    assert not documents_at("projet", index) and not documents_at("", index)
    engine = _engine(_Store(index))
    text = engine._memory_file_text("OneDrive_3_06-10-2026/Data.xlsx")
    assert text.startswith(
        "Ce fichier n'est pas sur le disque, mais dans la mémoire (fenêtre Mémoire, onglet "
        "Documents) :\n\n=== « OneDrive_3_06-10-2026/Data.xlsx » — fichier du dossier "
        "« OneDrive_3_06-10-2026 », déposé le 17/11/2026 à 12:00 ===\nTexte de x.")
    assert engine._memory_file_text("absent.txt") == ""


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
