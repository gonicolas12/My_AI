"""
Tests du RLHF Manager (core/rlhf_manager.py) : les notes en étoiles du chat.

Base SQLite dans un dossier temporaire : rien n'est écrit dans
data/rlhf_feedback.db, celle de l'utilisateur.
"""

import pytest

from core.rlhf_manager import RLHFManager


@pytest.fixture(name="rlhf")
def _rlhf(tmp_path):
    return RLHFManager(db_path=str(tmp_path / "rlhf.db"))


def _rate(rlhf, score, response="Environ 13 °C."):
    """Comme le chat : 4-5 étoiles = positive, 1-2 = negative, 3 = neutral."""
    feedback_type = "positive" if score >= 4 else "negative" if score <= 2 else "neutral"
    return rlhf.record_interaction(
        user_query="Quel est le point d'éclair de l'éthanol ?",
        ai_response=response,
        feedback_type=feedback_type,
        feedback_score=score,
        intent="conversation",
        confidence=1.0,
        model_version="ollama",
    )


def test_ratings_are_saved_and_counted(rlhf):
    _rate(rlhf, 5)
    _rate(rlhf, 1, response="Je ne sais pas.")
    _rate(rlhf, 3)
    stats = rlhf.get_statistics("all")
    assert stats["total_interactions"] == 3
    assert (stats["positive_feedback"], stats["negative_feedback"],
            stats["neutral_feedback"]) == (1, 1, 1)
    assert stats["average_score"] == pytest.approx(3.0)
    assert rlhf.get_statistics("session")["total_interactions"] == 3


def test_same_answer_rated_twice_reinforces_one_pattern(rlhf):
    _rate(rlhf, 5)
    _rate(rlhf, 4)
    (pattern,) = rlhf.get_learned_patterns("good_response")
    assert pattern["feedback_count"] == 2
    assert pattern["confidence"] == pytest.approx((5 / 5 + 4 / 5) / 2)


def test_bad_rating_is_learned_as_a_bad_response(rlhf):
    _rate(rlhf, 1, response="Je ne sais pas.")
    assert rlhf.get_learned_patterns("good_response", min_confidence=0.0) == []
    assert len(rlhf.get_learned_patterns("bad_response", min_confidence=0.0)) == 1
