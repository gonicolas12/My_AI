"""
Tests de la couche d'accès CRUD unifiée core/memory_store.py.

Opérations RÉELLES (pas de mock) : SQLite temporaire pour les faits, ChromaDB
temporaire pour les vecteurs. Les tests vectoriels sont ignorés (skip) si les
embeddings / ChromaDB ne sont pas disponibles sur la machine.
"""

import copy
import gc
import os
import shutil
import tempfile
from datetime import datetime

import pytest

from core.knowledge_base_manager import KnowledgeBaseManager
from core.memory_store import MemoryStore, document_key, group_documents, join_chunks


# ----------------------------------------------------------------------
# Faux SessionManager en mémoire (pour la propagation « à la source »)
# ----------------------------------------------------------------------

class FakeSessionManager:
    """Implémentation minimale en mémoire compatible avec ConversationSearch."""

    def __init__(self):
        self._states = {}
        self._meta = {}

    def add_workspace(self, ws_id, name, history):
        self._states[ws_id] = {
            "conversation_history": history,
            "metadata": {"name": name},
        }
        self._meta[ws_id] = {
            "id": ws_id, "name": name,
            "last_modified": datetime.now().isoformat(),
        }

    def list_workspaces(self):
        return [dict(m) for m in self._meta.values()]

    def load_workspace(self, ws_id):
        state = self._states.get(ws_id)
        return copy.deepcopy(state) if state is not None else None

    def save_workspace(self, ws_id, state):
        self._states[ws_id] = copy.deepcopy(state)
        if ws_id in self._meta:
            self._meta[ws_id]["last_modified"] = datetime.now().isoformat()
        return True


# ----------------------------------------------------------------------
# Faits structurés (SQLite) — pas besoin d'embeddings
# ----------------------------------------------------------------------

class TestFactsCRUD:

    @pytest.fixture
    def store(self):
        tmp = tempfile.mkdtemp()
        kb = KnowledgeBaseManager(db_path=os.path.join(tmp, "facts.db"))
        try:
            yield MemoryStore(knowledge_base=kb)
        finally:
            try:
                kb.close()
            except Exception:
                pass
            gc.collect()
            shutil.rmtree(tmp, ignore_errors=True)

    def test_add_and_list(self, store):
        for i in range(5):
            assert store.add_fact("preference", f"cle {i}", f"valeur {i}") is not None
        items, total = store.list_facts()
        assert total == 5 and len(items) == 5
        assert all(it["kind"] == "fact" for it in items)

    def test_pagination(self, store):
        for i in range(7):
            store.add_fact("general", f"k{i}", f"v{i}")
        page1, total = store.list_facts(limit=5, offset=0)
        page2, total2 = store.list_facts(limit=5, offset=5)
        assert total == total2 == 7
        assert len(page1) == 5 and len(page2) == 2

    def test_filter_by_category(self, store):
        store.add_fact("preference", "p1", "café")
        store.add_fact("technical", "t1", "python")
        items, total = store.list_facts(category="technical")
        assert total == 1 and items[0]["value"] == "python"

    def test_search(self, store):
        store.add_fact("general", "langage", "j'utilise python au travail")
        store.add_fact("general", "boisson", "je bois du thé")
        items, total = store.list_facts(query="python")
        assert total == 1 and "python" in items[0]["value"]

    def test_update(self, store):
        fid = store.add_fact("general", "k", "ancienne valeur")
        assert store.update_fact(fid, "nouvelle valeur")
        items, _ = store.list_facts()
        assert any(it["id"] == fid and it["value"] == "nouvelle valeur" for it in items)

    def test_delete(self, store):
        fid = store.add_fact("general", "k", "à supprimer")
        assert store.delete_fact(fid)
        items, total = store.list_facts()
        assert total == 0 and not items

    def test_categories_and_stats(self, store):
        store.add_fact("preference", "a", "x")
        store.add_fact("technical", "b", "y")
        cats = store.fact_categories()
        assert "preference" in cats and "technical" in cats
        assert store.stats()["facts"] == 2


# ----------------------------------------------------------------------
# Entrées vectorielles « documents » (ChromaDB)
# ----------------------------------------------------------------------

class TestVectorDocuments:

    @pytest.fixture
    def store(self):
        from memory.vector_memory import VectorMemory
        tmp = tempfile.mkdtemp()
        vm = VectorMemory(max_tokens=100000, storage_dir=os.path.join(tmp, "vec"))
        if not vm.embedding_model or not vm.document_collection:
            vm.cleanup()
            shutil.rmtree(tmp, ignore_errors=True)
            pytest.skip("Embeddings/ChromaDB non disponibles")
        vm.add_document("Le ciel est bleu et lumineux. " * 40, "doc_test")
        try:
            yield MemoryStore(vector_memory=vm)
        finally:
            try:
                vm.cleanup()
            except Exception:
                pass
            gc.collect()
            shutil.rmtree(tmp, ignore_errors=True)

    def test_list_and_count(self, store):
        items, total = store.list_vectors("document")
        assert total >= 1 and len(items) == total
        assert all(it["kind"] == "vector" and it["collection"] == "document"
                   for it in items)

    def test_pagination(self, store):
        _, total = store.list_vectors("document")
        if total < 2:
            pytest.skip("Pas assez de chunks")
        p1, _ = store.list_vectors("document", limit=1, offset=0)
        p2, _ = store.list_vectors("document", limit=1, offset=1)
        assert p1[0]["id"] != p2[0]["id"]

    def test_search_substring(self, store):
        items, total = store.list_vectors("document", query="ciel")
        assert total >= 1
        assert all("ciel" in it["content"].lower() for it in items)
        none, n = store.list_vectors("document", query="zzzzz_introuvable")
        assert n == 0 and not none

    def test_update_vector(self, store):
        entry_id = store.list_vectors("document")[0][0]["id"]
        assert store.update_vector(entry_id, "Contenu réécrit", "document")
        items, _ = store.list_vectors("document")
        assert any(it["id"] == entry_id and it["content"] == "Contenu réécrit"
                   for it in items)

    def test_delete_vector_is_real(self, store):
        items, before = store.list_vectors("document")
        entry_id = items[0]["id"]
        assert store.delete_vector(entry_id, "document")
        _, after = store.list_vectors("document")
        assert after == before - 1

    def test_add_document_by_hand(self, store):
        """Bouton Ajouter de la Mémoire : rangé avec sa provenance, jamais recopié."""
        _, before = store.list_vectors("document")
        content = "Consignes d'accueil des visiteurs du site. " * 40
        added = store.add_document(content, "accueil.md", {"source": "manual", "type": "Code"})
        assert added["status"] == "added" and added["chunks"] > 1
        items, total = store.list_vectors("document", query="visiteurs")
        assert total == added["chunks"] and len(items) == total
        line = MemoryStore.describe_provenance(items[0])
        assert line.startswith("📄 accueil.md") and line.endswith("ajouté à la main")

        assert store.add_document(content, "accueil.md") == {
            "status": "duplicate", "document_id": added["document_id"],
            "chunks": added["chunks"], "error": ""}
        assert store.list_vectors("document")[1] == before + added["chunks"]

    def test_newest_document_first_and_its_chunks_in_order(self, store):
        """Un document ajouté s'affiche en tête de la première page (et non à la
        fin de la liste), du premier morceau au dernier."""
        store.add_document("Inventaire du magasin, rayon par rayon. " * 80, "inventaire.txt")
        items, total = store.list_vectors("document", limit=100)
        names = [it["metadata"]["document_name"] for it in items]
        added = names.count("inventaire.txt")
        assert added > 2 and len(items) == total
        assert names == ["inventaire.txt"] * added + ["doc_test"] * (total - added)
        assert [it["metadata"]["chunk_index"] for it in items[:added]] == list(range(added))
        first, _ = store.list_vectors("document", limit=2)
        second, _ = store.list_vectors("document", limit=2, offset=2)
        assert [it["id"] for it in first + second] == [it["id"] for it in items[:4]]
        assert first[0]["content"] == items[0]["content"]  # texte lu pour la page
        found, matches = store.list_vectors("document", query="rayon")
        assert matches == added
        assert [it["metadata"]["chunk_index"] for it in found] == list(range(added))

    def test_chat_image_is_not_kept_by_hand(self, store):
        """Image du chat : rangée sous son empreinte, ni recopiée ni « ajoutée à la main »."""
        image_id = "image_aaaaaaaaaaaaaaaa"
        assert not store.has_document(image_id)
        first = store.add_document("Description de l'image : un pont.", "pont.png",
                                   {"type": "Image"}, document_id=image_id, keep=False)
        assert first["status"] == "added" and store.has_document(image_id)
        again = store.add_document("Description de l'image : un pont la nuit.", "pont.png",
                                   {"type": "Image"}, document_id=image_id, keep=False)
        assert again == {"status": "duplicate", "document_id": image_id, "chunks": 0,
                         "error": ""}
        items, total = store.list_vectors("document", query="pont")
        assert total == 1 and "source" not in items[0]["metadata"]
        assert MemoryStore.describe_provenance(items[0]).startswith("🖼️ pont.png")
        assert store.keep_document(image_id) == 1  # puis ajoutée à la main

    def test_documents_and_dropped_folders_are_grouped(self, store):
        """Onglet Documents : un élément par document, un par dossier déposé (ses
        fichiers rangés par chemin), le plus récent en tête ; chacun se supprime
        en entier. Leurs morceaux (chunks) restent internes."""
        report = store.add_document("Partie du rapport annuel. " * 300 + "Conclusion unique.",
                                    "rapport.txt", {"source": "manual", "type": "Code"})
        assert report["status"] == "added" and report["chunks"] > 2 and report["document_id"]
        folder_meta = {"source": "manual", "type": "Code", "folder": "site", "folder_id": "s1"}
        for relative, text in (("src/app.py", "print('bonjour')\n" * 3),
                               ("README.md", "Site vitrine de l'association. " * 5)):
            store.add_document(text, f"site/{relative}", folder_meta,
                               document_id=f"folder_{relative.replace('/', '_')}")

        groups, total = store.list_document_groups()
        assert total == 3 and [group["kind"] for group in groups] == [
            "folder", "document", "document"]
        site, rapport, fixture = groups
        assert (site["name"], site["key"], site["files"]) == ("site", "s1", 2)
        assert [doc["label"] for doc in site["documents"]] == ["README.md", "src/app.py"]
        assert site["documents"][1]["name"] == "site/src/app.py"
        assert (rapport["name"], rapport["source"]) == ("rapport.txt", "manual")
        assert fixture["name"] == "doc_test" and fixture["source"] is None
        assert store.list_document_groups(limit=1, offset=1)[0] == [rapport]
        # Recherche : dans le texte ou dans le nom
        assert store.list_document_groups(query="conclusion unique")[0] == [rapport]
        assert store.list_document_groups(query="bonjour")[0][0]["files"] == 1
        assert store.list_document_groups(query="rapport.txt")[1] == 1

        assert store.delete_document(rapport["id"]) == report["chunks"]
        assert store.delete_folder("site") == 0  # par sa clé, pas par son nom
        assert store.delete_folder("s1") == 2
        groups, total = store.list_document_groups()
        assert total == 1 and groups[0]["name"] == "doc_test"

    def test_two_folders_with_the_same_name_stay_apart(self, store):
        """Deux dossiers déposés du même nom : deux dossiers, chacun ses fichiers ;
        en supprimer un laisse l'autre."""
        for key, text in (("s1", "Première version du site. " * 3),
                          ("s2", "Seconde version du site. " * 3)):
            store.add_document(text, "site/index.html", {
                "source": "manual", "folder": "site", "folder_id": key},
                document_id=f"folder_{key}_index")
        folders = [group for group in store.list_document_groups()[0]
                   if group["kind"] == "folder"]
        assert [(group["name"], group["key"]) for group in folders] == [
            ("site", "s2"), ("site", "s1")]
        assert store.delete_folder("s2") == 1
        folders = [group for group in store.list_document_groups()[0]
                   if group["kind"] == "folder"]
        assert [group["key"] for group in folders] == ["s1"]

    def test_a_folder_file_dropped_again_replaces_its_old_version(self, store):
        """Même chemin dans le même dossier, contenu modifié : la nouvelle version
        remplace l'ancienne, une fois rangée ; celle d'un autre dossier du même
        nom reste."""
        meta = {"source": "manual", "type": "Code", "folder": "site", "folder_id": "s1"}
        first = store.add_document("Version 1 du script. " * 3, "site/app.py", meta,
                                   document_id="folder_v1")
        store.add_document("Version 0 du script. " * 3, "site/app.py",
                           {**meta, "folder_id": "s2"}, document_id="folder_autre")
        second = store.add_document("Version 2 du script. " * 3, "site/app.py", meta,
                                    document_id="folder_v2")
        assert first["status"] == second["status"] == "added"
        assert store.remove_other_versions("site/app.py", "folder_v2", folder_id="s1") == 1
        assert store.has_document("folder_v2") and not store.has_document("folder_v1")
        assert store.has_document("folder_autre")

    def test_two_files_with_the_same_name_both_stay(self, store):
        """Deux fichiers du même nom, de contenus différents, restent deux documents
        (l'utilisateur les distingue par leur date) ; même contenu : pas de copie.
        « Mettre à jour » supprime sa cible, une fois la nouvelle version rangée."""
        manual = {"source": "manual", "type": "Code"}
        first = store.add_document("Horaires : lundi 9 h. " * 5, "horaires.md", manual)
        second = store.add_document("Horaires : mardi 10 h. " * 5, "horaires.md", manual)
        same = store.add_document("Horaires : mardi 10 h. " * 5, "horaires.md", manual)
        assert [first["status"], second["status"], same["status"]] == [
            "added", "added", "duplicate"]
        assert same["document_id"] == second["document_id"]
        named = [doc for doc in store.document_index() if doc["name"] == "horaires.md"]
        assert len(named) == 2 and named[0]["id"] == second["document_id"]  # le plus récent
        # Mise à jour du plus ancien : la nouvelle version, puis la cible supprimée
        third = store.add_document("Horaires : jeudi 14 h. " * 5, "horaires.md", manual)
        assert store.delete_document(first["document_id"]) == 1
        names = sorted(doc["id"] for doc in store.document_index()
                       if doc["name"] == "horaires.md")
        assert names == sorted([second["document_id"], third["document_id"]])

    def test_document_index_texts_and_folder_update(self, store):
        """Index des documents (sans leurs morceaux), texte recomposé d'un document,
        et un dossier mis à jour qui perd les fichiers qu'il ne contient plus."""
        meta = {"source": "manual", "type": "Code", "folder": "site", "folder_id": "s1"}
        for relative in ("a.md", "b.md", "c.md"):
            store.add_document(f"Contenu de {relative}. " * 3, f"site/{relative}", meta,
                               document_id=f"folder_{relative}")
        store.add_document("Notes du lundi. " * 3, "notes.md", {"source": "manual"})
        index = store.document_index()
        assert [doc["name"] for doc in index][:1] == ["notes.md"]  # le plus récent
        assert {doc["name"]: doc["folder_key"] for doc in index if doc["folder"]} == {
            "site/a.md": "s1", "site/b.md": "s1", "site/c.md": "s1"}
        assert store.stats()["documents"] == 5  # 5 documents, bien plus de morceaux
        assert store.vector_memory.count_entries("document") > 5

        assert store.prune_folder("s1", ["site/a.md", "site/c.md"]) == 1
        assert sorted(doc["name"] for doc in store.document_index() if doc["folder"]) == [
            "site/a.md", "site/c.md"]
        assert store.prune_folder("s1", ["site/a.md", "site/c.md"]) == 0
        assert store.stats()["documents"] == 4

        long_text = " ".join(f"Phrase numéro {n} du compte rendu annuel." for n in range(600))
        long_doc = store.add_document(long_text, "compte_rendu.txt", {"source": "manual"})
        assert long_doc["chunks"] > 3
        # Les morceaux se chevauchent : le texte recomposé n'en garde qu'un exemplaire
        assert store.document_text(long_doc["document_id"]).split() == long_text.split()

    def test_document_of_an_attachment_is_kept_when_added_by_hand(self, store):
        """Déjà rangé par une pièce jointe : « Ajouter » le garde comme ajouté à la main."""
        attachment = store.vector_memory.add_document("Le ciel est bleu et lumineux. " * 40,
                                                      "doc_test")
        assert attachment["status"] == "duplicate"  # rangé par la fixture
        kept = store.add_document("Le ciel est bleu et lumineux. " * 40, "doc_test",
                                  {"source": "manual", "type": "Code"})
        assert kept["status"] == "duplicate" and kept["chunks"] > 0
        assert store.vector_memory.remove_document("doc_test") == 0  # pièce jointe retirée
        assert store.list_vectors("document", query="ciel")[1] == kept["chunks"]


# ----------------------------------------------------------------------
# Entrées de conversation — propagation « à la source »
# ----------------------------------------------------------------------

class TestConversationsAtSource:

    @pytest.fixture
    def setup(self):
        from memory.vector_memory import VectorMemory
        try:
            from core.conversation_search import ConversationSearch
        except Exception:
            pytest.skip("ConversationSearch indisponible")

        tmp = tempfile.mkdtemp()
        vm = VectorMemory(max_tokens=100000, storage_dir=os.path.join(tmp, "vec"))
        if not vm.embedding_model or not vm.conversation_collection:
            vm.cleanup()
            shutil.rmtree(tmp, ignore_errors=True)
            pytest.skip("Embeddings/ChromaDB non disponibles")

        sm = FakeSessionManager()
        sm.add_workspace("ws1", "Projet", [
            {"is_user": True, "text": "J'adore le chocolat noir corsé."},
            {"is_user": False, "text": "Très bien, c'est bien noté."},
        ])
        cs = ConversationSearch(session_manager=sm, vector_memory=vm)
        if not cs.is_available():
            vm.cleanup()
            shutil.rmtree(tmp, ignore_errors=True)
            pytest.skip("Recherche conversations indisponible")
        cs.reindex(force=True)

        try:
            yield (
                MemoryStore(
                    vector_memory=vm, session_manager=sm, conversation_search=cs,
                ),
                vm, sm, cs,
            )
        finally:
            try:
                vm.cleanup()
            except Exception:
                pass
            gc.collect()
            shutil.rmtree(tmp, ignore_errors=True)

    def _find_user_entry(self, store):
        items, _ = store.list_vectors("conversation")
        for it in items:
            if "chocolat" in it["content"].lower() and \
                    it["metadata"].get("role") == "user":
                return it
        return None

    def test_indexed(self, setup):
        store, _vm, _sm, _cs = setup
        _, total = store.list_vectors("conversation")
        assert total == 2

    def test_transient_delete_reappears_on_force_reindex(self, setup):
        store, vm, _sm, cs = setup
        entry = self._find_user_entry(store)
        assert entry is not None
        # Suppression directe (transitoire), sans toucher à la source
        assert store.delete_vector(entry["id"], "conversation", at_source=False)
        assert vm.count_entries("conversation") == 1
        # Un réindex forcé reconstruit depuis le workspace → l'entrée revient
        cs.reindex(force=True)
        assert vm.count_entries("conversation") == 2

    def test_delete_at_source_is_durable(self, setup):
        store, vm, sm, cs = setup
        entry = self._find_user_entry(store)
        assert entry is not None

        assert store.delete_vector(
            entry["id"], "conversation", at_source=True, metadata=entry["metadata"],
        )
        # Le message d'origine a disparu du workspace
        history = sm.load_workspace("ws1")["conversation_history"]
        assert len(history) == 1
        assert all("chocolat" not in (m.get("text", "")).lower() for m in history)
        # Et il ne réapparaît pas, même après un réindex forcé
        assert vm.count_entries("conversation") == 1
        cs.reindex(force=True)
        assert vm.count_entries("conversation") == 1

    def test_edit_at_source(self, setup):
        store, _vm, sm, _cs = setup
        entry = self._find_user_entry(store)
        assert entry is not None
        assert store.update_vector(
            entry["id"], "Finalement je préfère le thé vert.",
            "conversation", at_source=True, metadata=entry["metadata"],
        )
        history = sm.load_workspace("ws1")["conversation_history"]
        assert history[0]["text"] == "Finalement je préfère le thé vert."


# ----------------------------------------------------------------------
# Provenance & dégradation gracieuse
# ----------------------------------------------------------------------

class TestProvenanceAndGraceful:

    def test_group_documents_without_chromadb(self):
        """Clé d'un document : son identifiant, sinon son nom (ancienne entrée),
        sinon l'entrée seule ; un dossier prend la date de son fichier le plus récent."""
        entries = [
            {"id": "a0", "metadata": {"document_name": "ancien.pdf", "chunk_index": 0,
                                      "created": "2026-01-01T10:00:00"}},
            {"id": "s0", "metadata": {"document_id": "f1", "document_name": "site/b.md",
                                      "folder": "site", "source": "manual",
                                      "created": "2026-01-02T10:00:00"}},
            {"id": "a1", "metadata": {"document_name": "ancien.pdf", "chunk_index": 1,
                                      "created": "2026-01-01T10:00:00"}},
            {"id": "s1", "metadata": {"document_id": "f2", "document_name": "site/a/c.py",
                                      "folder": "site", "source": "manual",
                                      "created": "2026-01-03T10:00:00"}},
            {"id": "orphelin", "metadata": {}},
        ]
        groups = group_documents(entries)
        assert [(group["kind"], group["id"]) for group in groups] == [
            ("document", "entry:orphelin"), ("folder", "folder:site"),
            ("document", "name:ancien.pdf")]
        site = groups[1]
        assert (site["files"], site["chunks"], site["created"], site["source"]) == (
            2, 2, "2026-01-03T10:00:00", "manual")
        assert [doc["label"] for doc in site["documents"]] == ["a/c.py", "b.md"]
        assert groups[2]["chunks"] == 2 and groups[2]["source"] is None
        assert document_key(entries[0]) == "name:ancien.pdf"
        assert document_key(entries[1]) == "f1"

        # Un second dossier « site » (autre identifiant) : un autre groupe, plus récent
        entries.append({"id": "t0", "metadata": {
            "document_id": "f3", "document_name": "site/b.md", "folder": "site",
            "folder_id": "s9", "created": "2026-01-04T10:00:00"}})
        groups = group_documents(entries)
        folders = [(group["name"], group["key"]) for group in groups
                   if group["kind"] == "folder"]
        assert folders == [("site", "s9"), ("site", "site")]

    def test_join_chunks_keeps_each_overlap_once(self):
        """Morceaux voisins qui se chevauchent : le passage commun n'est gardé
        qu'une fois ; sans passage commun, ils sont mis bout à bout."""
        text = " ".join(f"mot{n}" for n in range(300))
        words = text.split()
        chunks = [" ".join(words[0:120]), " ".join(words[100:220]), " ".join(words[200:300])]
        assert join_chunks(chunks).split() == words
        assert join_chunks(["Premier morceau.", "Second, sans rapport."]) == (
            "Premier morceau.\nSecond, sans rapport.")
        assert join_chunks([]) == "" and join_chunks(["", "seul"]) == "seul"

    def test_describe_provenance_fact(self):
        item = {
            "kind": "fact", "key": "boisson", "source": "manual",
            "confidence": 0.7, "updated_at": "2026-06-24T09:00:00",
        }
        line = MemoryStore.describe_provenance(item)
        assert "boisson" not in line  # la clé est gérée par la fenêtre, pas ici
        assert "manual" in line and "70%" in line

    def test_describe_provenance_conversation(self):
        item = {
            "kind": "vector", "collection": "conversation",
            "metadata": {"workspace_name": "Projet", "role": "user",
                         "timestamp": "2026-06-24T10:30:00"},
        }
        line = MemoryStore.describe_provenance(item)
        assert "Projet" in line and "vous" in line

    def test_describe_provenance_document(self):
        item = {
            "kind": "vector", "collection": "document",
            "metadata": {"document_name": "rapport.pdf", "chunk_index": 3},
        }
        line = MemoryStore.describe_provenance(item)
        assert "rapport.pdf" in line and "chunk 3" in line
        assert "à la main" not in line  # pièce jointe du chat

    def test_describe_provenance_image_added_by_hand(self):
        item = {
            "kind": "vector", "collection": "document",
            "metadata": {"document_name": "tableau.png", "chunk_index": 0,
                         "type": "Image", "source": "manual"},
        }
        assert MemoryStore.describe_provenance(item) == (
            "🖼️ tableau.png  ·  chunk 0  ·  ajouté à la main")

    def test_empty_store_is_graceful(self):
        store = MemoryStore()  # aucun backend
        assert store.list_facts() == ([], 0)
        assert store.list_vectors("document") == ([], 0)
        assert store.update_fact(1, "x") is False
        assert store.delete_fact(1) is False
        assert store.stats() == {"facts": 0, "documents": 0, "conversations": 0}
        assert store.fact_categories() == []
        refused = store.add_document("texte", "doc.txt")
        assert refused["status"] == "error" and refused["chunks"] == 0
        assert store.has_document("image_0") is False and store.keep_document("image_0") == 0

    def test_document_split_but_not_stored_is_an_error(self):
        """Sans modèle d'embeddings, add_document découpe le texte mais ne range
        rien dans ChromaDB : ce n'est pas « mis en mémoire »."""

        class SplitOnly:  # pylint: disable=too-few-public-methods
            """VectorMemory sans modèle d'embeddings."""

            @staticmethod
            def add_document(content, document_name="", metadata=None, document_id=None):
                del content, document_name, metadata, document_id
                return {"status": "success", "document_id": "doc_txt_1",
                        "chunks_created": 3, "chunks_stored": 0}

        assert MemoryStore(vector_memory=SplitOnly()).add_document("texte", "doc.txt") == {
            "status": "error", "document_id": "", "chunks": 0,
            "error": "Mémoire indisponible (base non initialisée)."}


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
