"""
Tests du texte des documents chargés injecté dans le prompt (core/ai_engine.py).

Chaque document était coupé à 8 000 caractères sans que le modèle le sache :
sur une FDS de 10 961 caractères, la section 15 (caractère 8 217) manquait et
le modèle affirmait que « le document se termine à la section 14 ».
"""

import logging
from types import SimpleNamespace

import pytest

from core import ai_engine
from core.ai_engine import AIEngine

# FDS simulée : 16 sections d'environ 700 caractères, section 15 vers 9 800
FDS = "\n".join(f"SECTION {n}: TITRE {n}\n" + "contenu " * 85 for n in range(1, 17))
# Grande FDS : 60 sections (≈ 42 000 caractères), au-delà du budget du prompt
BIG_FDS = "\n".join(f"SECTION {n}: TITRE {n}\n" + "contenu " * 85 for n in range(1, 61))


@pytest.fixture(autouse=True)
def _keywords_only(monkeypatch):
    """Sélection par mots seuls, que le modèle multilingue soit en cache ou non."""
    monkeypatch.setattr(ai_engine, "passage_similarities", lambda _query, _passages: None)


@pytest.fixture(name="engine")
def _engine():
    """AIEngine minimal : seule la fenêtre de contexte du LLM sert au budget."""
    engine = AIEngine.__new__(AIEngine)
    engine.local_ai = SimpleNamespace(local_llm=SimpleNamespace(gen_num_ctx=32768))
    engine._visible_documents = None
    engine.logger = logging.getLogger("test_document_context")
    return engine


def test_log_counts_the_documents_really_sent(engine, caplog):
    """Le log comptait les documents en mémoire, pas ceux envoyés au modèle."""
    engine._visible_documents = {"297A1T.pdf"}  # seul fichier joint à un message
    stored = {"RUB4026.pdf": {"content": "ruban " * 50}, "297A1T.pdf": {"content": "fiche " * 50}}
    with caplog.at_level(logging.INFO, logger="test_document_context"):
        sections = engine._document_sections("que dit ce pdf ?", stored)
    assert len(sections) == 1
    assert (
        "Documents envoyés au modèle : 1 sur 2 en mémoire (non envoyés : RUB4026.pdf)"
        in caplog.text
    )


def test_document_beyond_8000_chars_is_sent_whole(engine):
    assert FDS.index("SECTION 15") > 8000
    sections = engine._document_sections(
        "de quoi parle la section 15 du document ?", {"fds.pdf": {"content": FDS}}
    )
    assert len(sections) == 1
    assert "SECTION 15: TITRE 15" in sections[0]
    assert "SECTION 16: TITRE 16" in sections[0]
    assert "tronqué" not in sections[0]


def test_document_beyond_budget_keeps_passages_about_the_question(engine):
    budget = engine._document_char_budget()
    assert budget == 32768 // 4 * 3  # un quart de la fenêtre, ≈ 8 000 tokens
    assert BIG_FDS.index("SECTION 47") > budget
    section = engine._document_sections(
        "de quoi parle la section 47 ?", {"fds.pdf": {"content": BIG_FDS}}
    )[0]
    assert "Document long : extraits choisis selon la question" in section
    assert "SECTION 47: TITRE 47" in section
    assert len(section) < budget + 1_000


def test_budget_shared_between_documents(engine):
    short, long_ = engine._document_sections(
        "section 47",
        {"court.txt": {"content": "c" * 1_000}, "fds.pdf": {"content": BIG_FDS}},
    )
    assert short == "=== court.txt ===\n" + "c" * 1_000
    assert "SECTION 47: TITRE 47" in long_
    assert len(long_) < engine._document_char_budget()


def test_long_document_passages_also_follow_meaning(engine, monkeypatch):
    """Question française sur une FDS anglaise : le sens désigne le passage."""
    doc = BIG_FDS.replace(
        "SECTION 33: TITRE 33\n", "SECTION 33: TITRE 33\nGloves not normally required. "
    )
    monkeypatch.setattr(
        ai_engine,
        "passage_similarities",
        lambda _query, passages: [1.0 if "Gloves" in p else 0.0 for p in passages],
    )
    section = engine._document_sections(
        "faut-il porter des gants ?", {"fds.pdf": {"content": doc}}
    )[0]
    assert "Gloves not normally required" in section


def test_read_local_file_clip_is_announced():
    clipped = AIEngine._clip_document("#" * 100, 40)
    assert clipped.startswith("#" * 40 + "\n[… Document tronqué : 60 caractères sur 100")


def test_budget_follows_context_window(engine):
    engine.local_ai.local_llm.gen_num_ctx = 65536  # option 64k de ⚙️ Réglages
    section = engine._document_sections("q", {"doc.txt": {"content": "#" * 30_000}})[0]
    assert section.count("#") == 30_000
    assert "tronqué" not in section
