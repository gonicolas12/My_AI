"""
Tests du modèle multilingue de la sélection des passages (core/passage_embeddings.py).

Une question en français ne trouvait pas le passage d'un document anglais qui
y répond (« gants » ne trouve pas « gloves ») : la sélection ne comparait que
les mots. Le téléchargement est simulé ; seul le dernier test utilise le vrai
modèle, s'il est déjà dans le cache (aucun téléchargement pendant les tests).
"""

import threading

import huggingface_hub
import numpy as np
import pytest

from core import passage_embeddings as pe


@pytest.fixture(name="missing_model")
def _missing_model(monkeypatch):
    """Modèle activé mais absent du cache."""
    monkeypatch.setattr(pe, "enabled", lambda: True)
    monkeypatch.setattr(pe, "is_downloaded", lambda: False)


def test_download_fetches_only_model_files_one_at_a_time(missing_model, monkeypatch):
    """Un fichier après l'autre, dans le thread appelant, à la version figée.

    snapshot_download passerait par un pool de threads non-démon : fermer l'app
    pendant le téléchargement figerait le terminal jusqu'à sa fin.
    """
    calls = []
    monkeypatch.setattr(
        huggingface_hub,
        "hf_hub_download",
        lambda *args, **kwargs: calls.append((args, kwargs, threading.current_thread())),
    )
    assert pe.ensure_downloaded() is True
    assert [args for args, _, _ in calls] == [(pe.MODEL_ID, name) for name in pe.MODEL_FILES]
    assert all(kwargs == {"revision": pe.REVISION} for _, kwargs, _ in calls)
    assert all(thread is threading.current_thread() for _, _, thread in calls)


def test_failed_download_keeps_keyword_selection(missing_model, monkeypatch, capsys):
    def offline(*_args, **_kwargs):
        raise OSError("réseau injoignable")

    monkeypatch.setattr(huggingface_hub, "hf_hub_download", offline)
    assert pe.ensure_downloaded() is False
    output = capsys.readouterr().out
    assert "réseau injoignable" in output and "nouvel essai au prochain lancement" in output


def test_disabled_model_is_never_downloaded(monkeypatch):
    monkeypatch.setattr(pe, "enabled", lambda: False)
    monkeypatch.setattr(huggingface_hub, "hf_hub_download", pytest.fail)
    assert pe.ensure_downloaded() is False
    assert pe.prefetch_in_background() is None


def test_prefetch_downloads_in_a_background_thread(missing_model, monkeypatch):
    threads = []
    monkeypatch.setattr(pe, "ensure_downloaded", lambda: threads.append(threading.current_thread()))
    thread = pe.prefetch_in_background()
    thread.join(5)
    assert threads == [thread] and thread.daemon and thread is not threading.main_thread()


def test_prefetch_does_nothing_once_downloaded(monkeypatch):
    monkeypatch.setattr(pe, "enabled", lambda: True)
    monkeypatch.setattr(pe, "is_downloaded", lambda: True)
    assert pe.prefetch_in_background() is None


def test_no_model_means_no_similarity(monkeypatch):
    monkeypatch.setattr(pe, "_loaded_model", lambda: None)
    assert pe.similarities("question", ["passage"]) is None


def test_passages_are_encoded_once_across_questions(monkeypatch):
    encoded = []

    class FakeModel:
        def encode(self, texts, **_kwargs):
            encoded.append(list(texts))
            return np.array([[1.0, 0.0] if "gloves" in t else [0.0, 1.0] for t in texts])

    monkeypatch.setattr(pe, "_loaded_model", FakeModel)
    monkeypatch.setattr(pe, "_vectors", type(pe._vectors)())
    passages = ["wear gloves", "storage", "wear gloves"]
    assert pe.similarities("gloves ?", passages) == [1.0, 0.0, 1.0]
    assert pe.similarities("stockage ?", passages) == [0.0, 1.0, 0.0]
    assert encoded == [["wear gloves", "storage"], ["gloves ?"], ["stockage ?"]]


@pytest.mark.skipif(not pe.is_downloaded(), reason="modèle multilingue absent du cache")
def test_french_question_finds_english_passage():
    """Aucun mot commun entre la question et le passage attendu.

    Une question ambiguë pour le sens seul (« comment éliminer le produit ? »,
    proche de « extinguishers ») est départagée par les mots dans
    document_passages, d'où son absence ici.
    """
    passages = [
        "Skin Protection: Avoid prolonged or repeated skin contact. Gloves not normally required.",
        "Waste Disposal Method: Reclaim if feasible, or dispose of in a sanitary landfill.",
        "Extinguishing media: use fire extinguishers with class B agents (dry chemical, CO2).",
        "Transport information: not regulated per U.S. DOT, IATA or IMO.",
    ]
    for question, expected in (
        ("faut-il porter des gants ?", 0),
        ("où jeter les déchets ?", 1),
        ("avec quoi éteindre un feu ?", 2),
        ("peut-on l'expédier par avion ?", 3),
    ):
        scores = pe.similarities(question, passages)
        assert scores.index(max(scores)) == expected, question
