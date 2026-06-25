"""
Garde-fou anti-boucle de l'AgenticExecutor (mode VS Code).

Les modèles locaux faibles réécrivent parfois le même fichier en boucle sans
jamais conclure. Ces tests vérifient que la boucle est coupée bien avant
MAX_ITERATIONS, sans pénaliser un enchaînement légitime d'actions distinctes.

L'appel LLM est simulé (pas d'Ollama requis) en remplaçant
``_call_llm_streaming``.
"""

import asyncio

import pytest

from core.agentic_executor import AgenticExecutor, _tool_signature


class StubToolExecutor:
    """Exécuteur d'outils factice : renvoie toujours un succès."""

    async def call(self, call_id, name, input_data):
        return {"content": "ok", "is_error": False}


def _make_executor():
    return AgenticExecutor(ollama_chat_url="http://localhost:0/api/chat", model="test")


def _run(ex):
    return asyncio.run(ex.run(
        user_message="go",
        history=[],
        tool_executor=StubToolExecutor(),
        on_chunk=lambda *a, **k: None,
        on_tool_call_announced=lambda c: None,
        on_tool_result=lambda *a, **k: None,
        workspace_info="",
    ))


WRITE_SAME = (
    '<tool_use>{"name": "write_file", '
    '"input": {"path": "a.html", "content": "x"}}</tool_use>'
)


class TestLoopGuard:

    def test_repeated_write_breaks_before_max_iterations(self):
        ex = _make_executor()
        n_calls = {"n": 0}

        async def fake_llm(messages, segment_index, on_chunk):
            n_calls["n"] += 1
            return WRITE_SAME  # toujours la même réécriture du même fichier

        ex._call_llm_streaming = fake_llm  # type: ignore[assignment]
        result = _run(ex)

        assert "boucle" in result.lower()                 # coupé par le garde-fou
        assert n_calls["n"] == ex.LOOP_HARD_LIMIT          # stoppe à la limite dure
        assert n_calls["n"] < ex.MAX_ITERATIONS            # bien avant max_iter

    def test_distinct_actions_then_done_completes_normally(self):
        ex = _make_executor()
        seq = [
            '<tool_use>{"name": "write_file", "input": {"path": "a.html", "content": "x"}}</tool_use>',
            '<tool_use>{"name": "write_file", "input": {"path": "b.css", "content": "y"}}</tool_use>',
            "Terminé : les fichiers sont créés.",  # plus de tool_use → fin propre
        ]
        idx = {"i": 0}

        async def fake_llm(messages, segment_index, on_chunk):
            out = seq[idx["i"]]
            idx["i"] += 1
            return out

        ex._call_llm_streaming = fake_llm  # type: ignore[assignment]
        result = _run(ex)

        assert "Terminé" in result
        assert "boucle" not in result.lower()


class TestToolSignature:

    def test_groups_by_path_ignoring_content(self):
        a = {"name": "write_file", "input": {"path": "x.html", "content": "aaa"}}
        b = {"name": "write_file", "input": {"path": "x.html", "content": "bbb"}}
        c = {"name": "write_file", "input": {"path": "y.html", "content": "aaa"}}
        assert _tool_signature(a) == _tool_signature(b)   # même chemin → même signature
        assert _tool_signature(a) != _tool_signature(c)   # chemin différent

    def test_falls_back_to_full_input_without_path(self):
        a = {"name": "list_dir", "input": {"path": "."}}
        b = {"name": "glob", "input": {"pattern": "**/x"}}
        assert _tool_signature(a) != _tool_signature(b)
        # Sans path ni pattern : signature sur l'entrée complète.
        c = {"name": "run_command", "input": {"command": "ls"}}
        assert "run_command" in _tool_signature(c)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
