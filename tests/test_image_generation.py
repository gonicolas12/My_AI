"""
Tests du workflow ComfyUI de la génération d'image (models/image_generation.py).

Le checkpoint de l'installation automatique, sd_turbo, est distillé pour 1 à 4
étapes sans guidage. Avec les réglages SD classiques (25 étapes, CFG 7), l'image
sortait brûlée au bout de 337 s sur le CPU d'un Core Ultra 7 255H, au-delà du
délai de 300 s ; en 4 étapes à CFG 1 : ~30 s sur ce CPU, ~2 s sur son GPU
intégré. L'API HTTP de ComfyUI est simulée.
"""

import pytest
import requests

from models import image_generation as ig


class FakeResponse:
    def __init__(self, payload=None, content=b""):
        self.status_code = 200
        self.text = ""
        self.content = content
        self._payload = payload

    def json(self):
        return self._payload


class FakeComfyUI:
    """API de ComfyUI : un checkpoint, les workflows reçus, une image rendue."""

    def __init__(self, checkpoint):
        self.checkpoint = checkpoint
        self.workflows = []

    def get(self, url, **_kwargs):
        if url.endswith("/system_stats"):
            return FakeResponse({})
        if url.endswith("/object_info/CheckpointLoaderSimple"):
            ckpt_name = [[self.checkpoint]]
            return FakeResponse({"CheckpointLoaderSimple": {"input": {"required": {
                "ckpt_name": ckpt_name}}}})
        if url.endswith("/history/p1"):
            image = {"filename": "MyAI_00001_.png", "subfolder": "", "type": "output"}
            return FakeResponse({"p1": {"outputs": {"9": {"images": [image]}}}})
        if url.endswith("/view"):
            return FakeResponse(content=b"\x89PNG")
        raise AssertionError(f"URL inattendue : {url}")

    def post(self, url, json=None, **_kwargs):
        assert url.endswith("/prompt")
        self.workflows.append(json["prompt"])
        return FakeResponse({"prompt_id": "p1"})


@pytest.fixture(name="generate")
def _generate(tmp_path, monkeypatch):
    """generate(checkpoint) : workflow envoyé à ComfyUI pour « a red dragon »."""

    def run(checkpoint):
        comfy = FakeComfyUI(checkpoint)
        monkeypatch.setattr(requests, "get", comfy.get)
        monkeypatch.setattr(requests, "post", comfy.post)
        config = ig.ImageGenConfig(backend="comfyui", output_directory=str(tmp_path))
        result = ig.ImageGenerator(config).generate("a red dragon")
        assert result.success, result.message
        (workflow,) = comfy.workflows
        # Chaque lien [nœud, sortie] vise un nœud du workflow
        for node in workflow.values():
            for value in node["inputs"].values():
                if isinstance(value, list):
                    assert value[0] in workflow, f"nœud {value[0]} absent"
        return workflow

    return run


def test_turbo_checkpoint_is_sampled_in_four_steps_without_guidance(generate):
    workflow = generate("sd_turbo.safetensors")

    assert workflow["3"]["class_type"] == "SamplerCustom"
    assert workflow["3"]["inputs"]["cfg"] == 1.0
    assert workflow["10"]["inputs"]["sampler_name"] == "euler_ancestral"
    assert workflow["11"]["class_type"] == "SDTurboScheduler"
    assert workflow["11"]["inputs"]["steps"] == 4
    assert workflow["8"]["inputs"]["samples"] == ["3", 0]


def test_classic_checkpoint_keeps_the_configured_sampling(generate):
    workflow = generate("v1-5-pruned-emaonly-fp16.safetensors")

    sampler = workflow["3"]
    assert sampler["class_type"] == "KSampler"
    assert (sampler["inputs"]["steps"], sampler["inputs"]["cfg"]) == (25, 7.0)
    assert (sampler["inputs"]["sampler_name"], sampler["inputs"]["scheduler"]) == (
        "dpmpp_2m", "karras")
