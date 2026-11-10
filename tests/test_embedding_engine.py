"""
Tests du moteur d'embeddings de la mémoire et du RAG (core/embedding_engine.py).

MiniLM (anglais) ne retrouvait presque rien pour une question dans une autre
langue que celle du document : Granite multilingue le remplace, avec repli sur
MiniLM tant qu'il manque. Chargements et téléchargements simulés ; seul le
dernier test charge le vrai Granite, s'il est déjà dans le cache.
"""

import re
import threading
import time

import huggingface_hub
import numpy as np
import pytest

from core import embedding_engine as ee
from core import passage_embeddings as pe

GRANITE = ee.DEFAULT_MODEL


class FakeSentenceTransformer:
    """Modèle sentence-transformers simulé : enregistre les appels."""

    def __init__(self, dimension=4, with_roles=True):
        self.calls = []
        self.dimension = dimension
        if not with_roles:
            self.encode_query = None
            self.encode_document = None

    def get_embedding_dimension(self):
        return self.dimension

    def encode(self, sentences, **kwargs):
        self.calls.append(("encode", sentences, kwargs))
        return np.ones((len(sentences), self.dimension)) if isinstance(sentences, list) \
            else np.ones(self.dimension)

    def encode_query(self, sentences, **kwargs):  # pylint: disable=method-hidden
        self.calls.append(("query", sentences, kwargs))
        return np.zeros(self.dimension)

    def encode_document(self, sentences, **kwargs):  # pylint: disable=method-hidden
        self.calls.append(("document", sentences, kwargs))
        return np.zeros(self.dimension)


# ── Collections : une par modèle ─────────────────────────────────────────────

def test_minilm_keeps_the_historical_collection_names():
    """Un repli sur MiniLM retrouve l'index d'avant la mise à jour, sans recalcul."""
    for name in (ee.FALLBACK_MODEL, "all-MiniLM-L6-v2"):
        assert ee.collection_name("documents", name, 384) == "documents"


def test_each_model_and_dimension_has_its_own_collection():
    """Granite et MiniLM ont tous deux 384 dimensions : jamais la même collection."""
    granite = ee.collection_name("documents", GRANITE, 384, pe.REVISION)
    assert granite != "documents"
    assert granite.startswith("documents__granite-embedding-107m") and granite.endswith("__384")
    assert ee.collection_name("documents", GRANITE, 768, pe.REVISION) != granite
    # Autre version figée, ou même nom chez un autre éditeur : autre index
    assert ee.collection_name("documents", GRANITE, 384, "autre-version") != granite
    assert ee.collection_name("documents", "autre/granite-embedding-107m-multilingual", 384) != granite


def test_collection_names_are_valid_and_short_for_chromadb():
    for base in ("conversations", "documents", "codebase"):
        for model in (GRANITE, "intfloat/multilingual-e5-large-instruct",
                      r"C:\modèles\Mon Modèle Perso", "x" * 300):
            name = ee.collection_name(base, model, 1024)
            assert re.fullmatch(r"[a-z0-9][a-z0-9._-]*[a-z0-9]", name), name
            assert "..." not in name and len(name) <= 63, name
            assert ee.belongs_to(name, base)


def test_belongs_to_recognises_every_model_of_a_collection():
    assert ee.belongs_to("documents", "documents")
    assert ee.belongs_to("documents__granite-1234abcd__384", "documents")
    assert not ee.belongs_to("documents_old", "documents")
    assert not ee.belongs_to("conversations__granite-1234abcd__384", "documents")


# ── Moteur ──────────────────────────────────────────────────────────────────

def test_engine_distinguishes_queries_from_documents():
    model = FakeSentenceTransformer()
    engine = ee.EmbeddingEngine(model, GRANITE, pe.REVISION)
    engine.encode_query("question ?")
    engine.encode_document(["passage"])
    engine.encode(["texte"], normalize_embeddings=True)
    assert [(kind, sentences) for kind, sentences, _ in model.calls] == [
        ("query", "question ?"), ("document", ["passage"]), ("encode", ["texte"]),
    ]
    # Pas de barre de progression dans la console, sauf demande expresse
    assert all(kwargs["show_progress_bar"] is False for _, _, kwargs in model.calls)
    assert model.calls[2][2]["normalize_embeddings"] is True
    assert engine.dimension == 4 and engine.get_sentence_embedding_dimension() == 4
    assert engine.key == f"{GRANITE}@{pe.REVISION}" and engine.name == "granite-embedding-107m-multilingual"


def test_engine_falls_back_to_encode_without_query_and_document_methods():
    """sentence-transformers d'avant la 5 n'a ni encode_query ni encode_document."""
    model = FakeSentenceTransformer(with_roles=False)
    engine = ee.EmbeddingEngine(model, ee.FALLBACK_MODEL)
    engine.encode_query("question ?")
    engine.encode_document("passage")
    assert [kind for kind, _, _ in model.calls] == ["encode", "encode"]


def test_engine_serialises_calls_from_several_threads():
    """Le tokenizer rapide refuse deux appels simultanés (« Already borrowed »)."""
    state = {"inside": 0, "overlap": False}

    class SlowModel(FakeSentenceTransformer):
        def encode(self, sentences, **kwargs):
            state["inside"] += 1
            state["overlap"] |= state["inside"] > 1
            time.sleep(0.02)
            state["inside"] -= 1
            return super().encode(sentences, **kwargs)

    engine = ee.EmbeddingEngine(SlowModel(with_roles=False), GRANITE)
    threads = [threading.Thread(target=engine.encode_document, args=(["texte"],)) for _ in range(6)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(5)
    assert not state["overlap"]


def test_helpers_accept_models_that_only_have_encode():
    """Les faux modèles des tests (et les anciens appelants) n'ont qu'encode()."""

    class EncodeOnly:
        def encode(self, text):
            return [len(text)]

    assert ee.encode_documents(EncodeOnly(), "abc") == [3]
    assert ee.encode_queries(EncodeOnly(), "abcd") == [4]
    model = FakeSentenceTransformer()
    ee.encode_documents(model, "passage")
    ee.encode_queries(model, "question")
    assert [kind for kind, _, _ in model.calls] == ["document", "query"]


# ── Choix du modèle et repli ────────────────────────────────────────────────

@pytest.fixture(name="loading")
def _loading(monkeypatch):
    """Cache, téléchargements et chargements simulés."""
    state = {"cached": set(), "downloadable": set(), "downloads": [], "background": []}

    def engine_for(model_id):
        if model_id not in state["cached"]:
            return None
        return ee.EmbeddingEngine(FakeSentenceTransformer(), model_id)

    def download(model_id):
        state["downloads"].append(model_id)
        if model_id in state["downloadable"]:
            state["cached"].add(model_id)
            return True
        return False

    monkeypatch.setattr(ee, "engine_for", engine_for)
    monkeypatch.setattr(ee, "download", download)
    monkeypatch.setattr(ee, "download_in_background", state["background"].append)
    return state


def test_configured_model_is_used_when_cached(loading):
    loading["cached"] = {GRANITE, ee.FALLBACK_MODEL}
    engine = ee.load_engine(GRANITE)
    assert engine.model_id == GRANITE and not engine.fallback
    assert not loading["downloads"] and not loading["background"]


def test_minilm_replaces_a_missing_model_for_the_session(loading, capsys):
    """Mise à jour de l'appli sans Granite : MiniLM tout de suite, Granite au lancement suivant."""
    loading["cached"] = {ee.FALLBACK_MODEL}
    engine = ee.load_engine(GRANITE)
    assert engine.model_id == ee.FALLBACK_MODEL and engine.fallback
    assert loading["background"] == [GRANITE]
    assert not loading["downloads"]  # rien de bloquant au démarrage
    assert "MiniLM le remplace pour cette session" in capsys.readouterr().out


def test_first_launch_downloads_the_configured_model(loading):
    """Rien en cache : on télécharge directement Granite, pas MiniLM pour une session."""
    loading["downloadable"] = {GRANITE, ee.FALLBACK_MODEL}
    engine = ee.load_engine(GRANITE)
    assert engine.model_id == GRANITE and not engine.fallback
    assert loading["downloads"] == [GRANITE]


def test_first_launch_falls_back_to_minilm_if_the_download_fails(loading):
    loading["downloadable"] = {ee.FALLBACK_MODEL}
    engine = ee.load_engine(GRANITE)
    assert engine.model_id == ee.FALLBACK_MODEL and engine.fallback
    assert loading["downloads"] == [GRANITE, ee.FALLBACK_MODEL]


def test_no_model_at_all_means_no_embeddings(loading):
    assert ee.load_engine(GRANITE) is None


def test_minilm_chosen_on_purpose_is_not_a_fallback(loading):
    loading["cached"] = {ee.FALLBACK_MODEL}
    engine = ee.load_engine(ee.FALLBACK_MODEL)
    assert engine.model_id == ee.FALLBACK_MODEL and not engine.fallback
    assert not loading["background"]
    assert ee.is_fallback_model("all-MiniLM-L6-v2")  # nom court accepté


def test_configured_model_comes_from_config_yaml(monkeypatch):
    class Config:
        value = None

        def get(self, key, default=None):
            assert key == "optimization.rag.embedding_model"
            return self.value if self.value is not None else default

    config = Config()
    monkeypatch.setattr("core.config.get_config", lambda: config)
    assert ee.configured_model() == GRANITE  # clé absente : Granite
    config.value = "  intfloat/multilingual-e5-small "
    assert ee.configured_model() == "intfloat/multilingual-e5-small"
    config.value = ""
    assert ee.configured_model() == GRANITE


# ── Cache et téléchargement ─────────────────────────────────────────────────

def test_granite_is_loaded_from_its_pinned_revision(monkeypatch, tmp_path):
    """Le cache de Granite n'a que la version figée (pas de refs/main)."""
    asked = []
    modules = tmp_path / "snapshot" / "modules.json"

    def from_cache(repo_id, filename, revision=None):
        asked.append((repo_id, filename, revision))
        return str(modules)

    monkeypatch.setattr(pe, "is_downloaded", lambda: True)
    monkeypatch.setattr(huggingface_hub, "try_to_load_from_cache", from_cache)
    assert ee.local_path(GRANITE) == str(modules.parent)
    assert asked == [(GRANITE, "modules.json", pe.REVISION)]
    monkeypatch.setattr(pe, "is_downloaded", lambda: False)
    assert ee.local_path(GRANITE) is None


def test_granite_download_is_the_one_of_long_documents(monkeypatch):
    """Un seul téléchargement, fichier par fichier, à la version figée."""
    monkeypatch.setattr(pe, "download", lambda: True)
    monkeypatch.setattr(huggingface_hub, "snapshot_download", pytest.fail)
    assert ee.download(GRANITE) is True


def test_other_models_skip_onnx_and_openvino_weights(monkeypatch):
    calls = []
    monkeypatch.setattr(huggingface_hub, "snapshot_download",
                        lambda repo_id, **kwargs: calls.append((repo_id, kwargs)))
    assert ee.download("all-MiniLM-L6-v2") is True
    (repo_id, kwargs), = calls
    assert repo_id == ee.FALLBACK_MODEL
    assert "onnx/*" in kwargs["ignore_patterns"] and "openvino/*" in kwargs["ignore_patterns"]


def test_failed_download_is_reported(monkeypatch, capsys):
    def offline(*_args, **_kwargs):
        raise OSError("réseau injoignable")

    monkeypatch.setattr(huggingface_hub, "snapshot_download", offline)
    assert ee.download("intfloat/multilingual-e5-small") is False
    assert "réseau injoignable" in capsys.readouterr().out


def test_background_download_of_granite_reuses_the_prefetch(monkeypatch):
    marker = object()
    monkeypatch.setattr(pe, "prefetch_in_background", lambda: marker)
    assert ee.download_in_background(GRANITE) is marker


@pytest.mark.skipif(not pe.is_downloaded(), reason="Granite absent du cache")
def test_real_granite_is_loaded_once_and_finds_across_languages():
    """Une seule instance (mémoire et longs documents) ; une question française
    retrouve le passage anglais qui y répond."""
    engine = ee.engine_for(GRANITE)
    assert engine is ee.engine_for(GRANITE)
    assert engine.dimension == 384 and engine.revision == pe.REVISION
    passages = engine.encode_document([
        "Wear nitrile gloves when handling the product.",
        "The warehouse closes at 6 pm on Fridays.",
    ], normalize_embeddings=True)
    question = engine.encode_query("Faut-il porter des gants ?", normalize_embeddings=True)
    scores = passages @ question
    assert scores[0] > scores[1]
