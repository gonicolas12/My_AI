"""
Tests de la réindexation au changement de modèle d'embeddings
(memory/embedding_reindex.py et collections de memory/vector_memory.py).

Vrai ChromaDB dans un dossier temporaire, vecteurs simulés (aucun modèle) :
une collection par modèle, copie en arrière-plan depuis les textes stockés,
déchiffrés pour le calcul, ancienne collection gardée jusqu'à la fin ; rien de
ce que l'utilisateur supprime pendant la copie ne revient.
"""

import base64
import hashlib

import chromadb
import numpy as np
import pytest
from cryptography.fernet import Fernet

from core import embedding_engine as ee
from memory import embedding_reindex as er
from memory import vector_memory as vm_module
from memory.vector_memory import VectorMemory

TARGET = "documents__nouveau-0123abcd__4"


def _vector(text, dimension=4, salt=""):
    digest = hashlib.md5(f"{salt}|{text}".encode("utf-8")).digest()
    return [round(byte / 255 + 0.01, 4) for byte in digest[:dimension]]


class Embedder:
    """Calcul simulé : enregistre les textes reçus."""

    def __init__(self, dimension=4):
        self.dimension = dimension
        self.texts = []

    def __call__(self, texts):
        self.texts.extend(texts)
        return np.array([_vector(text, self.dimension) for text in texts])


@pytest.fixture(name="client")
def _client(tmp_path):
    return chromadb.PersistentClient(path=str(tmp_path / "chroma"))


def _source(client, name="documents", entries=None):
    """Ancienne collection (vecteurs d'un autre modèle)."""
    collection = client.get_or_create_collection(name, metadata={"hnsw:space": "cosine"})
    entries = entries or {
        "a": ("Premier texte", {"document_name": "doc", "chunk_index": 0}),
        "b": ("Deuxième texte", {"document_name": "doc", "chunk_index": 1}),
        "c": ("Troisième texte", {"document_name": "autre", "chunk_index": 0, "workspace_id": "w2"}),
    }
    collection.add(
        ids=list(entries),
        embeddings=[[1.0, 0.0, 0.0, 0.0]] * len(entries),
        documents=[text for text, _ in entries.values()],
        metadatas=[metadata for _, metadata in entries.values()],
    )
    return collection


def _target(client, name=TARGET):
    return client.get_or_create_collection(name, metadata={"hnsw:space": "cosine"})


def _names(client):
    return sorted(getattr(collection, "name", collection) for collection in client.list_collections())


def _run(reindexer):
    """Copie dans le thread du test (déterministe)."""
    reindexer._running = True  # pylint: disable=protected-access
    reindexer._run()  # pylint: disable=protected-access


# ── Copie ───────────────────────────────────────────────────────────────────

def test_copy_recomputes_vectors_from_stored_texts_then_drops_the_old_collection(client):
    _source(client)
    target = _target(client)
    embed = Embedder()
    reindexer = er.Reindexer(client, embed, lambda text: text)
    reindexer.add_job(TARGET, ["documents"])
    thread = reindexer.start()
    thread.join(30)

    assert not reindexer.is_running()
    assert _names(client) == [TARGET]  # ancienne collection supprimée à la fin
    copied = target.get(include=["documents", "metadatas", "embeddings"])
    rows = {entry_id: (doc, meta, list(vector))
            for entry_id, doc, meta, vector in zip(copied["ids"], copied["documents"],
                                                   copied["metadatas"], copied["embeddings"])}
    assert rows["a"][0] == "Premier texte" and rows["a"][1] == {"document_name": "doc", "chunk_index": 0}
    assert rows["c"][1]["workspace_id"] == "w2"  # métadonnées gardées : filtres et manifestes valides
    assert np.allclose(rows["b"][2], _vector("Deuxième texte"))  # vecteur du nouveau modèle
    assert sorted(embed.texts) == ["Deuxième texte", "Premier texte", "Troisième texte"]


def test_encrypted_entries_are_decrypted_for_the_model_but_stay_encrypted(client):
    cipher = Fernet(Fernet.generate_key())
    secret = base64.b64encode(cipher.encrypt("Code du coffre : 1234".encode())).decode()
    _source(client, entries={
        "s": (secret, {"encrypted": True, "document_name": "coffre"}),
        "p": ("Texte public", {"encrypted": False, "document_name": "public"}),
    })
    target = _target(client)
    embed = Embedder()

    def decrypt(stored):
        return cipher.decrypt(base64.b64decode(stored.encode())).decode()

    reindexer = er.Reindexer(client, embed, decrypt)
    reindexer.add_job(TARGET, ["documents"])
    _run(reindexer)

    assert sorted(embed.texts) == ["Code du coffre : 1234", "Texte public"]
    stored = target.get(ids=["s"], include=["documents", "embeddings"])
    assert stored["documents"] == [secret]  # jamais écrit en clair dans la base
    assert np.allclose(stored["embeddings"][0], _vector("Code du coffre : 1234"))


def test_entry_already_in_the_new_collection_wins(client):
    """Écrite après le changement de modèle, elle est plus récente que l'ancienne."""
    _source(client)
    target = _target(client)
    target.add(ids=["a"], embeddings=[_vector("Version récente")], documents=["Version récente"])
    embed = Embedder()
    reindexer = er.Reindexer(client, embed, lambda text: text)
    reindexer.add_job(TARGET, ["documents"])
    _run(reindexer)

    assert target.get(ids=["a"], include=["documents"])["documents"] == ["Version récente"]
    assert "Premier texte" not in embed.texts  # pas recalculée pour rien
    assert target.count() == 3


def test_entries_that_cannot_be_decrypted_keep_the_old_collection(client, capsys):
    """Clé perdue : rien n'est supprimé, nouvel essai au lancement suivant."""
    _source(client, entries={
        "x": ("illisible", {"encrypted": True}),
        "y": ("Texte clair", {"encrypted": False}),
    })
    target = _target(client)

    def broken(_stored):
        raise ValueError("clé de chiffrement introuvable")

    reindexer = er.Reindexer(client, Embedder(), broken)
    reindexer.add_job(TARGET, ["documents"])
    _run(reindexer)
    assert "documents" in _names(client)  # gardée intacte
    assert client.get_collection("documents").count() == 2
    assert target.get(include=[])["ids"] == ["y"]
    assert "non réindexée" in capsys.readouterr().out

    # Lancement suivant, clé retrouvée : la copie se termine
    later = er.Reindexer(client, Embedder(), lambda text: text)
    later.add_job(TARGET, ["documents"])
    _run(later)
    assert _names(client) == [TARGET] and target.count() == 2


def test_interrupted_copy_resumes_without_recomputing_what_is_done(client, monkeypatch):
    """Appli fermée au milieu : le lancement suivant ne recalcule que le reste."""
    monkeypatch.setattr(er, "BATCH_SIZE", 2)
    entries = {f"e{i}": (f"Texte {i}", {"chunk_index": i}) for i in range(5)}
    _source(client, entries=entries)
    target = _target(client)

    first = er.Reindexer(client, Embedder(), lambda text: text)
    first._copy_ids(client.get_collection("documents"), target, ["e0", "e1"])  # pylint: disable=protected-access
    assert target.count() == 2 and "documents" in _names(client)

    embed = Embedder()
    second = er.Reindexer(client, embed, lambda text: text)
    second.add_job(TARGET, ["documents"])
    _run(second)
    assert sorted(embed.texts) == ["Texte 2", "Texte 3", "Texte 4"]
    assert target.count() == 5 and _names(client) == [TARGET]


# ── Écritures de l'appli pendant la copie ───────────────────────────────────

def test_deleted_during_the_copy_never_comes_back(client):
    _source(client)
    target = _target(client)
    reindexer = er.Reindexer(client, Embedder(), lambda text: text)
    reindexer.add_job(TARGET, ["documents"])
    proxy = er.MigratingCollection(target, reindexer)

    proxy.delete(ids=["a"])  # entrée pas encore copiée
    proxy.delete(where={"workspace_id": "w2"})  # purge d'un workspace (recherche des conversations)
    _run(reindexer)
    assert target.get(include=[])["ids"] == ["b"]
    assert _names(client) == [TARGET]


def test_deleted_while_its_vector_is_computed_never_comes_back(client):
    """Suppression entre la lecture de l'entrée et l'écriture de son vecteur."""
    _source(client)
    target = _target(client)
    holder = {}

    def embed(texts):
        holder["proxy"].delete(ids=["b"])  # l'utilisateur supprime pendant le calcul
        return np.array([_vector(text) for text in texts])

    reindexer = er.Reindexer(client, embed, lambda text: text)
    reindexer.add_job(TARGET, ["documents"])
    holder["proxy"] = er.MigratingCollection(target, reindexer)
    _run(reindexer)
    assert sorted(target.get(include=[])["ids"]) == ["a", "c"]


def test_update_during_the_copy_moves_the_entry_to_the_new_collection(client):
    _source(client)
    target = _target(client)
    reindexer = er.Reindexer(client, Embedder(), lambda text: text)
    reindexer.add_job(TARGET, ["documents"])
    proxy = er.MigratingCollection(target, reindexer)

    proxy.update(ids=["a"], documents=["Texte corrigé"], embeddings=[_vector("Texte corrigé")])
    entry = target.get(ids=["a"], include=["documents", "metadatas"])
    assert entry["documents"] == ["Texte corrigé"]
    assert entry["metadatas"] == [{"document_name": "doc", "chunk_index": 0}]  # reprises de l'ancienne
    assert client.get_collection("documents").get(ids=["a"], include=[])["ids"] == []
    _run(reindexer)
    assert target.get(ids=["a"], include=["documents"])["documents"] == ["Texte corrigé"]


def test_proxy_is_a_plain_collection_once_the_copy_is_done(client):
    _source(client)
    target = _target(client)
    reindexer = er.Reindexer(client, Embedder(), lambda text: text)
    reindexer.add_job(TARGET, ["documents"])
    proxy = er.MigratingCollection(target, reindexer)
    _run(reindexer)
    proxy.update(ids=["b"], documents=["Modifié"], embeddings=[_vector("Modifié")])
    proxy.delete(ids=["c"])
    assert proxy.count() == 2 and proxy.name == TARGET and proxy.wrapped is target


def test_a_job_announced_twice_is_copied_once(client):
    """L'appli crée plusieurs VectorMemory sur le même dossier."""
    _source(client)
    _target(client)
    embed = Embedder()
    reindexer = er.Reindexer(client, embed, lambda text: text)
    reindexer.add_job(TARGET, ["documents"])
    reindexer.add_job(TARGET, ["documents"])
    _run(reindexer)
    assert len(embed.texts) == 3
    reindexer.add_job(TARGET, ["documents"])  # liste lue avant la suppression
    assert reindexer.start() is None and reindexer.source_collections(TARGET) == []


def test_forget_abandons_the_copy(client):
    _source(client)
    _target(client)
    reindexer = er.Reindexer(client, Embedder(), lambda text: text)
    reindexer.add_job(TARGET, ["documents"])
    reindexer.forget()
    assert reindexer.start() is None and reindexer.source_collections(TARGET) == []


# ── VectorMemory : une collection par modèle ────────────────────────────────

class FakeEngine:
    """Moteur simulé : vecteurs déterministes, propres à chaque modèle."""

    def __init__(self, model_id, dimension=4, fallback=False):
        self.model_id = model_id
        self.dimension = dimension
        self.revision = None
        self.fallback = fallback

    @property
    def key(self):
        return self.model_id

    def encode(self, sentences, **_kwargs):
        if isinstance(sentences, str):
            return np.array(_vector(sentences, self.dimension, self.model_id))
        return np.array([_vector(text, self.dimension, self.model_id) for text in sentences])

    encode_query = encode
    encode_document = encode


@pytest.fixture(name="memory_with")
def _memory_with(tmp_path, monkeypatch):
    """VectorMemory du dossier temporaire avec le moteur donné (sans CrossEncoder)."""
    monkeypatch.setattr(vm_module, "CROSSENCODER_AVAILABLE", False)

    def build(engine, start=True):
        monkeypatch.setattr(vm_module, "get_shared_embedding_model", lambda: engine)
        if not start:
            monkeypatch.setattr(er.Reindexer, "start", lambda self: None)
        memory = VectorMemory(max_tokens=100_000, storage_dir=str(tmp_path / "store"))
        reindexer = memory._reindexer  # pylint: disable=protected-access
        if start and reindexer is not None and reindexer._thread is not None:  # pylint: disable=protected-access
            reindexer._thread.join(30)  # pylint: disable=protected-access
        return memory

    return build


def _collections(memory):
    return _names(memory.chroma_client)


def test_each_model_writes_to_its_own_collections(memory_with):
    engine = FakeEngine("org/modele-a")
    memory = memory_with(engine)
    expected = sorted(ee.collection_name(base, "org/modele-a", 4)
                      for base in ("codebase", "conversations", "documents"))
    assert _collections(memory) == expected
    metadata = memory.document_collection.metadata
    assert metadata["embedding_model"] == "org/modele-a" and metadata["embedding_dim"] == 4
    assert memory.add_document("Le ciel est bleu.", "ciel")["status"] == "success"
    assert memory.count_entries("document") == 1


def test_changing_model_reindexes_in_the_background(memory_with):
    before = memory_with(FakeEngine("org/modele-a"))
    before.add_document("Les gants en nitrile protègent la peau.", "gants")
    before.add_document("L'entrepôt ferme à 18 h le vendredi.", "entrepot")
    ids = sorted(before.document_collection.get(include=[])["ids"])

    after = memory_with(FakeEngine("org/modele-b", dimension=6))
    assert _collections(after) == sorted(ee.collection_name(base, "org/modele-b", 6)
                                         for base in ("codebase", "conversations", "documents"))
    assert sorted(after.document_collection.get(include=[])["ids"]) == ids
    results = after.search_similar("gants", n_results=2, rerank=False)
    assert len(results) == 2  # vecteurs de 6 dimensions : interrogeables par le nouveau modèle
    assert after.get_stats()["reindexing"] is False


def test_fallback_model_leaves_the_chosen_model_index_alone(memory_with):
    """Granite pas encore téléchargé : MiniLM sert la session, l'index Granite attend."""
    granite = memory_with(FakeEngine("ibm-granite/granite-embedding-107m-multilingual"))
    granite.add_document("Texte indexé par Granite.", "granite")
    granite_name = granite.document_collection.name

    fallback = memory_with(FakeEngine(ee.FALLBACK_MODEL, fallback=True))
    assert fallback.document_collection.name == "documents"
    assert fallback._reindexer is None  # pylint: disable=protected-access
    assert fallback.chroma_client.get_collection(granite_name).count() == 1
    assert fallback.get_stats()["embedding_fallback"] is True


def test_minilm_chosen_again_reindexes_into_the_historical_collections(memory_with):
    granite = memory_with(FakeEngine("ibm-granite/granite-embedding-107m-multilingual"))
    granite.add_document("Texte indexé par Granite.", "granite")

    minilm = memory_with(FakeEngine(ee.FALLBACK_MODEL))
    assert _collections(minilm) == ["codebase", "conversations", "documents"]
    assert minilm.count_entries("document") == 1


def test_a_collection_of_another_model_is_never_mixed(memory_with, tmp_path):
    client = chromadb.PersistentClient(path=str(tmp_path / "store" / "chroma_db"))
    client.create_collection("documents", metadata={"hnsw:space": "cosine", "embedding_model": "autre/modele"})
    memory = memory_with(FakeEngine(ee.FALLBACK_MODEL))
    assert memory.document_collection is None
    assert memory.conversation_collection is not None


def test_clear_all_removes_the_collections_of_every_model(memory_with):
    old = memory_with(FakeEngine("org/modele-a"))
    old.add_document("Ancien texte.", "ancien")
    memory = memory_with(FakeEngine("org/modele-b"), start=False)  # copie pas encore faite
    memory.clear_all()
    assert _collections(memory) == sorted(ee.collection_name(base, "org/modele-b", 4)
                                          for base in ("codebase", "conversations", "documents"))
    assert memory.count_entries("document") == 0


def test_chunk_size_comes_from_config_yaml(memory_with, monkeypatch):
    class Config:
        values = {"optimization.rag.chunk_size": 128, "optimization.rag.chunk_overlap": 500}

        def get(self, key, default=None):
            return self.values.get(key, default)

    monkeypatch.setattr(vm_module, "get_config", Config)
    memory = memory_with(FakeEngine("org/modele-a"))
    assert memory.chunk_size == 128
    assert memory.chunk_overlap == 127  # jamais aussi long que le morceau (boucle infinie)
