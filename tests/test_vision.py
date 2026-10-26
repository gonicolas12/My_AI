"""
Tests de l'analyse d'images de LocalLLM : le modèle de chat qui voit.

qwen3.5, et my_ai qui en part, voient les images. Une image jointe partait
pourtant vers un second modèle (minicpm-v) qui la décrivait, puis my_ai
rédigeait à partir de la description : deux modèles en mémoire, une étape de
plus, et les erreurs de la description passaient dans la réponse. Aucun vrai
Ollama n'est appelé ici.
"""

# Les étapes testées sont des méthodes privées
# pylint: disable=protected-access

import json

import pytest

from models import local_llm
from models.local_llm import LocalLLM

IMAGE = "aW1hZ2U="
WINDOW = 32768
DESCRIPTION = "Un chat roux est assis sur un canapé bleu, à gauche de l'image."


def _tag(name, *capabilities):
    """Modèle de /api/tags ; sans capacité, celui d'un Ollama qui n'en publie pas."""
    model = {"name": name}
    if capabilities:
        model["capabilities"] = list(capabilities)
    return model


class _Tags:
    status_code = 200

    def __init__(self, models):
        self.models = models

    def json(self):
        return {"models": self.models}


class _Stream:
    """Réponse streamée d'Ollama (/api/chat)."""

    status_code = 200

    def __enter__(self):
        return self

    def __exit__(self, *_exc):
        return False

    @staticmethod
    def iter_lines():
        for token in ("Un chat ", "roux."):
            yield json.dumps({"message": {"content": token}, "done": False}).encode()
        yield json.dumps({"message": {"content": ""}, "done": True}).encode()


class _Description:
    """Réponse non streamée d'Ollama (/api/generate)."""

    status_code = 200

    @staticmethod
    def json():
        return {"response": DESCRIPTION}


@pytest.fixture(name="ollama")
def _ollama(monkeypatch):
    """Faux Ollama : modèles installés (à remplir) et requêtes reçues."""
    state = {"tags": [], "requests": []}

    def get(_url, **_kwargs):
        return _Tags(state["tags"])

    def post(url, **kwargs):
        state["requests"].append((url, kwargs["json"]))
        return _Stream() if kwargs.get("stream") else _Description()

    monkeypatch.setattr(local_llm.requests, "get", get)
    monkeypatch.setattr(local_llm, "_resilient_post", post)
    return state


def _llm():
    """LocalLLM sans __init__ (aucun appel à Ollama), modèle de chat my_ai."""
    llm = LocalLLM.__new__(LocalLLM)
    llm.is_ollama_available = True
    llm.model = "my_ai"
    llm.ollama_url = "http://127.0.0.1:9/api/generate"
    llm.chat_url = "http://127.0.0.1:9/api/chat"
    llm.timeout = 1
    llm.gen_temperature = 0.7
    llm.gen_num_ctx = WINDOW
    llm.conversation_history = []
    llm.max_history_length = 200
    llm._keep_recent_messages = 20
    llm._conversation_summary = ""
    return llm


# ── Choix du modèle ─────────────────────────────────────────────────────────


def test_the_chat_model_sees_the_images(ollama):
    ollama["tags"] = [_tag("minicpm-v:latest", "completion", "vision"),
                      _tag("my_ai:latest", "completion", "vision", "tools", "thinking")]

    assert _llm()._get_vision_model() == "my_ai"


def test_a_chat_model_without_vision_hands_over_to_qwen35(ollama):
    """my_ai sur une base sans vision (mistral…) : qwen3.5:4b avant minicpm-v."""
    ollama["tags"] = [_tag("my_ai:latest", "completion", "tools"),
                      _tag("minicpm-v:latest", "completion", "vision"),
                      _tag("qwen3.5:2b", "completion", "vision"),
                      _tag("qwen3.5:4b", "completion", "vision")]

    assert _llm()._get_vision_model() == "qwen3.5:4b"


def test_any_model_that_sees_is_the_last_resort(ollama):
    ollama["tags"] = [_tag("my_ai:latest", "completion", "tools"),
                      _tag("mistral:latest", "completion", "tools"),
                      _tag("gemma4:e4b", "completion", "vision")]

    assert _llm()._get_vision_model() == "gemma4:e4b"


def test_no_model_sees_the_images(ollama):
    ollama["tags"] = [_tag("my_ai:latest", "completion", "tools")]

    assert _llm()._get_vision_model() is None


def test_an_ollama_without_capabilities_goes_by_the_names(ollama):
    ollama["tags"] = [_tag("my_ai:latest"), _tag("mistral:latest"), _tag("llava:7b")]

    assert _llm()._get_vision_model() == "llava:7b"


# ── Question sur une image ──────────────────────────────────────────────────


def test_the_image_goes_with_the_question_to_the_chat_model(ollama):
    ollama["tags"] = [_tag("my_ai:latest", "completion", "vision", "tools", "thinking"),
                      _tag("minicpm-v:latest", "completion", "vision")]
    llm, tokens = _llm(), []

    answer = llm.generate_stream_with_image(
        "Que vois-tu ?", IMAGE, system_prompt="CONSIGNE", on_token=tokens.append
    )

    assert answer == "Un chat roux." and "".join(tokens) == answer
    ((url, request),) = ollama["requests"]  # pas de description à part
    assert url == llm.chat_url and request["model"] == "my_ai"
    assert request["messages"][0] == {"role": "system", "content": "CONSIGNE"}
    assert request["messages"][-1] == {
        "role": "user", "content": "Que vois-tu ?", "images": [IMAGE],
    }
    assert request["options"]["num_ctx"] == WINDOW
    assert request["think"] is False  # sans bloc « Réflexion »
    # L'historique garde la question, pas l'image
    assert llm.conversation_history == [
        {"role": "user", "content": "[Image jointe] Que vois-tu ?"},
        {"role": "assistant", "content": "Un chat roux."},
    ]


def test_a_dedicated_vision_model_describes_then_the_chat_model_writes(ollama):
    ollama["tags"] = [_tag("my_ai:latest", "completion", "tools"),
                      _tag("minicpm-v:latest", "completion", "vision")]
    llm = _llm()

    answer = llm.generate_stream_with_image("Que vois-tu ?", IMAGE)

    assert answer == "Un chat roux."
    (_, describe), (_, write) = ollama["requests"]
    assert describe["model"] == "minicpm-v:latest" and describe["images"] == [IMAGE]
    assert describe["options"]["num_ctx"] == 4096  # le modèle de chat garde la sienne
    assert write["model"] == "my_ai" and "images" not in write["messages"][-1]
    assert DESCRIPTION in write["messages"][-1]["content"]
    assert llm.conversation_history[0] == {
        "role": "user", "content": "[Image jointe] Que vois-tu ?",
    }


# ── Description seule (agents, Relay) ───────────────────────────────────────


def test_the_chat_model_describes_in_its_own_window_without_thinking(ollama):
    """Une autre fenêtre ferait recharger my_ai par Ollama (et perdre la
    conversation déjà lue), la réflexion de qwen3.5 retarderait la description."""
    ollama["tags"] = [_tag("my_ai:latest", "completion", "vision", "tools", "thinking")]

    assert _llm().describe_image(IMAGE) == DESCRIPTION
    ((url, request),) = ollama["requests"]
    assert url.endswith("/api/generate") and request["model"] == "my_ai"
    assert request["options"]["num_ctx"] == WINDOW
    assert request["think"] is False
