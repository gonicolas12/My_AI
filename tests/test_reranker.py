"""
Tests du reranker de la mémoire (core/reranker.py) et de son chargement par
memory/vector_memory.py.

Le CrossEncoder anglais défaisait le gain de Granite : sur 35 questions en 10
langues posées à la doc de My_AI, les 3 passages retenus contenaient la réponse
60 % du temps après lui, 77 % avec Granite seul, 86 % après mmarco-mMiniLMv2
(multilingue). Téléchargements, modèles et réglages simulés.
"""

import hashlib
import threading
from types import SimpleNamespace

import huggingface_hub
import numpy as np
import pytest

from core import embedding_engine as ee
from core import reranker as rr
from memory import vector_memory as vm_module
from memory.vector_memory import VectorMemory

GRANITE = ee.DEFAULT_MODEL
PINNED = rr._PINNED[rr.MULTILINGUAL]  # pylint: disable=protected-access


def _setting(monkeypatch, value):
    """optimization.rag.reranker_model de config.yaml (absent si value est ...)."""

    class Config:
        def get(self, key, default=None):
            if key == "optimization.rag.reranker_model":
                return default if value is ... else value
            return default

    monkeypatch.setattr("core.config.get_config", Config)


# ── Choix ───────────────────────────────────────────────────────────────────

def test_auto_picks_mmarco_for_granite_and_ms_marco_for_minilm(monkeypatch):
    _setting(monkeypatch, ...)
    assert rr.choose(SimpleNamespace(model_id=GRANITE)) == rr.MULTILINGUAL
    assert rr.choose(SimpleNamespace(model_id=ee.FALLBACK_MODEL)) == rr.ENGLISH
    assert rr.choose(SimpleNamespace(model_id="all-MiniLM-L6-v2")) == rr.ENGLISH
    assert rr.choose(None) == rr.ENGLISH
    _setting(monkeypatch, "auto")
    assert rr.choose(SimpleNamespace(model_id="intfloat/multilingual-e5-small")) == rr.MULTILINGUAL


def test_reranker_can_be_turned_off_or_named(monkeypatch):
    for value in ("none", "  NONE ", False, None, ""):
        _setting(monkeypatch, value)
        assert rr.choose(SimpleNamespace(model_id=GRANITE)) is None, value
    _setting(monkeypatch, "BAAI/bge-reranker-v2-m3")
    assert rr.choose(SimpleNamespace(model_id=GRANITE)) == "BAAI/bge-reranker-v2-m3"


def test_only_the_english_reranker_score_is_a_relevance_threshold():
    """Le score de mmarco change d'échelle d'une question à l'autre : il trie seulement."""
    assert rr.filters_by_score(rr.ENGLISH)
    assert not rr.filters_by_score(rr.MULTILINGUAL)
    assert not rr.filters_by_score(None)


# ── Cache et téléchargement ─────────────────────────────────────────────────

def test_mmarco_is_read_from_its_pinned_revision(monkeypatch, tmp_path):
    asked = []

    def from_cache(repo_id, filename, revision=None):
        asked.append((repo_id, filename, revision))
        return str(tmp_path / filename)

    monkeypatch.setattr(huggingface_hub, "try_to_load_from_cache", from_cache)
    assert rr.local_path(rr.MULTILINGUAL) == str(tmp_path)
    assert asked == [(rr.MULTILINGUAL, name, PINNED["revision"]) for name in PINNED["files"]]
    # Téléchargement interrompu : pas de modèle à moitié chargé
    monkeypatch.setattr(huggingface_hub, "try_to_load_from_cache",
                        lambda repo_id, filename, revision=None:
                        None if filename == "model.safetensors" else str(tmp_path / filename))
    assert rr.local_path(rr.MULTILINGUAL) is None
    assert rr.local_path(rr.ENGLISH) is None  # pas figé : chemin historique de vector_memory


def test_download_announces_its_size_and_fetches_one_file_at_a_time(monkeypatch, capsys):
    """Dans le thread appelant, sans le pool de snapshot_download (WinError 1314
    sous Windows sans droit de lien symbolique), à la version figée."""
    calls = []
    monkeypatch.setattr(huggingface_hub, "hf_hub_download", lambda repo_id, filename, revision=None: calls.append(
        (repo_id, filename, revision, threading.current_thread())))
    monkeypatch.setattr(huggingface_hub, "snapshot_download", pytest.fail)
    assert rr.download(rr.MULTILINGUAL) is True
    assert [name for _, name, _, _ in calls] == list(PINNED["files"])
    assert all(repo == rr.MULTILINGUAL and revision == PINNED["revision"] and thread is threading.current_thread()
               for repo, _, revision, thread in calls)
    assert "470 Mo" in capsys.readouterr().out


def test_failed_download_keeps_the_embedding_order(monkeypatch, capsys):
    def offline(*_args, **_kwargs):
        raise OSError("réseau injoignable")

    monkeypatch.setattr(huggingface_hub, "hf_hub_download", offline)
    assert rr.download(rr.MULTILINGUAL) is False
    output = capsys.readouterr().out
    assert "réseau injoignable" in output and "nouvel essai au prochain lancement" in output
    assert rr.download(rr.ENGLISH) is False  # pas figé : rien à télécharger ici


def test_background_download_runs_once_per_process(monkeypatch):
    """Chaque VectorMemory de l'appli le demande : un seul téléchargement."""
    release, started = threading.Event(), []
    monkeypatch.setattr(rr, "download", lambda model: (started.append(model), release.wait(5)))
    monkeypatch.setattr(rr, "_downloads", {})
    first = rr.download_in_background(rr.MULTILINGUAL)
    try:
        assert rr.download_in_background(rr.MULTILINGUAL) is first and first.daemon
    finally:
        release.set()
        first.join(5)
    assert started == [rr.MULTILINGUAL]
    assert rr.download_in_background(rr.ENGLISH) is None


# ── VectorMemory ────────────────────────────────────────────────────────────

def _vector(text, salt):
    digest = hashlib.md5(f"{salt}|{text}".encode("utf-8")).digest()
    return [byte / 255 + 0.01 for byte in digest[:4]]


class FakeEngine:
    """Moteur d'embeddings simulé (vecteurs déterministes de 4 dimensions)."""

    def __init__(self, model_id):
        self.model_id = model_id
        self.key = model_id
        self.dimension = 4
        self.revision = None
        self.fallback = False

    def encode(self, sentences, **_kwargs):
        if isinstance(sentences, str):
            return np.array(_vector(sentences, self.model_id))
        return np.array([_vector(text, self.model_id) for text in sentences])

    encode_query = encode
    encode_document = encode


class FakeCrossEncoder:
    """CrossEncoder simulé : compte les paires relues."""

    def __init__(self, path):
        self.path = path
        self.pairs = []

    def predict(self, pairs, **_kwargs):
        self.pairs.append(len(pairs))
        return np.array([float(len(passage)) for _, passage in pairs])


@pytest.fixture(name="memory_with")
def _memory_with(tmp_path, monkeypatch):
    """VectorMemory du dossier temporaire avec ce modèle d'embeddings et ce reranker en cache."""
    monkeypatch.setattr(vm_module, "_SHARED_RERANKERS", {})
    monkeypatch.setattr(vm_module, "CrossEncoder", FakeCrossEncoder)
    state = {"background": [], "fetched": []}
    monkeypatch.setattr(vm_module, "download_reranker_in_background", state["background"].append)

    def fetch(self, model):
        state["fetched"].append(model)
        self.reranker = FakeCrossEncoder(model)

    monkeypatch.setattr(VectorMemory, "_fetch_reranker", fetch)

    def build(model_id, cached=True, setting=...):
        _setting(monkeypatch, setting)
        monkeypatch.setattr(vm_module, "get_shared_embedding_model", lambda: FakeEngine(model_id))
        monkeypatch.setattr(vm_module, "reranker_local_path",
                            lambda model: str(tmp_path / "mmarco") if cached else None)
        return VectorMemory(max_tokens=100_000, storage_dir=str(tmp_path / "store"))

    return build, state


def test_granite_memory_loads_mmarco_from_the_cache(memory_with):
    build, state = memory_with
    memory = build(GRANITE)
    assert memory.reranker_model == rr.MULTILINGUAL and memory.reranker is not None
    assert memory.reranker._model.path.endswith("mmarco")  # pylint: disable=protected-access
    assert memory.reranker_filters is False
    assert not state["background"] and not state["fetched"]
    assert memory.get_stats()["reranker_model"] == rr.MULTILINGUAL


def test_missing_mmarco_downloads_in_background_and_keeps_granite_order(memory_with):
    build, state = memory_with
    memory = build(GRANITE, cached=False)
    assert memory.reranker is None
    assert state["background"] == [rr.MULTILINGUAL]
    assert memory.get_stats()["reranker_model"] is None
    memory.add_document("Les gants en nitrile protègent la peau.", "gants")
    assert memory.search_similar("gants", n_results=1)  # ordre de Granite, sans reranker


def test_minilm_memory_keeps_its_english_reranker(memory_with):
    build, state = memory_with
    memory = build(ee.FALLBACK_MODEL)
    assert state["fetched"] == [rr.ENGLISH] and not state["background"]
    assert memory.reranker_model == rr.ENGLISH and memory.reranker_filters is True


def test_reranking_can_be_turned_off(memory_with):
    build, state = memory_with
    memory = build(GRANITE, setting="none")
    assert memory.reranker is None and memory.reranker_model is None
    assert not state["background"] and not state["fetched"]


def test_reranker_reads_at_most_30_candidates(memory_with):
    """≈ 0,1 s par paire avec mmarco sur CPU : 15 morceaux demandés n'en relisent que 30."""
    build, _ = memory_with
    memory = build(GRANITE)
    for i in range(40):
        memory.add_document(f"Document numéro {i}. " * (i % 7 + 1), f"doc{i}")
    model = memory.reranker._model  # pylint: disable=protected-access
    assert len(memory.search_similar("document", n_results=3)) == 3
    assert len(memory.search_similar("document", n_results=15)) == 15
    assert model.pairs == [9, 30]
    # Autant de candidats que de résultats demandés : rien à départager
    assert len(memory.search_similar("document", n_results=40)) == 40
    assert model.pairs == [9, 30]
