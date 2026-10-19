"""
Arrêt du streaming de l'AgenticExecutor (mode VS Code) quand la tâche est annulée.

Le bouton STOP de l'extension annule la tâche asyncio de la boucle agentique,
mais l'appel à Ollama tourne dans un thread que l'annulation n'arrête pas : il
continuait de lire le flux et de pousser des chunks au client (qui les
affichait après un Clear), et Ollama de générer jusqu'au bout. Ce test vérifie
que le thread arrête de lire et ferme la connexion dès l'annulation.

Ollama est simulé (pas de serveur requis) en remplaçant ``requests.post``.
"""

import asyncio
import json
import threading
import time
from unittest import mock

import pytest

from core.agentic_executor import AgenticExecutor


class FakeStreamResponse:
    """Réponse Ollama en streaming : un token toutes les 10 ms pendant 3 s."""

    status_code = 200

    def __init__(self):
        self.closed = threading.Event()
        self.lines_read = 0

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.closed.set()
        return False

    def iter_lines(self):
        for _ in range(300):
            time.sleep(0.01)
            self.lines_read += 1
            yield json.dumps({"message": {"content": "mot "}}).encode()


def test_cancel_stops_stream_thread():
    ex = AgenticExecutor(ollama_chat_url="http://localhost:0/api/chat", model="test")
    resp = FakeStreamResponse()
    chunks = []
    state = {}

    async def scenario():
        with mock.patch("core.agentic_executor.requests.post", return_value=resp):
            task = asyncio.ensure_future(ex._call_llm_streaming(
                [{"role": "user", "content": "go"}], 0,
                lambda text, segment_index: chunks.append(text),
            ))
            await asyncio.sleep(0.3)          # génération en cours
            assert chunks, "le flux devait avoir commencé"
            task.cancel()                     # bouton STOP
            with pytest.raises(asyncio.CancelledError):
                await task
            await asyncio.sleep(0.1)          # le thread lit au plus une ligne de plus
            state["closed"] = resp.closed.is_set()
            state["lines"] = resp.lines_read
            state["chunks"] = len(chunks)
            await asyncio.sleep(0.3)
            state["lines_after"] = resp.lines_read
            state["chunks_after"] = len(chunks)

    asyncio.run(scenario())

    assert state["closed"]                                # connexion fermée → Ollama s'arrête
    assert state["lines_after"] == state["lines"]         # plus rien n'est lu
    assert state["chunks_after"] == state["chunks"]       # plus aucun chunk vers le client
    assert state["lines"] < 100                           # coupé bien avant la fin du flux


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
