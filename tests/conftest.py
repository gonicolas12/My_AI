"""Réglages communs aux tests."""

import pytest

import core.chat_memory as chat_memory


@pytest.fixture(autouse=True)
def _no_chat_memory_reader(monkeypatch):
    """Le chat ne lit pas ce qu'un message change dans sa mémoire avec un vrai
    modèle pendant les tests (core/chat_memory.py) : son lecteur appellerait
    Ollama, ou attendrait 2 s qu'un faux serveur refuse la connexion, à chaque
    réponse. Un test qui en veut un le remplace par le sien."""
    monkeypatch.setattr(chat_memory.ChatMemoryReader, "for_llm",
                        classmethod(lambda cls, llm: None))
