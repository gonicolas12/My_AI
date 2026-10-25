"""
Tests des demandes de génération d'image dans les autres langues de
l'interface (core/image_intent.py), et de leur branchement dans AIEngine :
« generate an image of a cat » produit une image comme « génère une image de
chat » ; une demande de code, de schéma ou d'analyse d'image jointe, non.
"""

import pytest

from core.ai_engine import AIEngine
from core.image_intent import is_image_request, strip_image_request

# (texte, sujet attendu ; None : la demande est reconnue sans sujet séparable)
_REQUESTS = [
    ("generate an image of a cat in space", "cat in space"),
    ("Can you create a realistic picture of a sunset over Paris?", "sunset over Paris"),
    ("draw me a sheep", "sheep"),
    ("make me a logo for my bakery", "my bakery"),
    ("genera una imagen de un gato astronauta", "gato astronauta"),
    ("dibújame un cordero", "cordero"),
    ("Erstelle ein Bild von einer Katze im Weltraum", "Katze im Weltraum"),
    ("Kannst du mir ein Bild von einer Katze malen?", None),
    ("Zeichne mir ein Schaf", "Schaf"),
    ("genera un'immagine di un gatto", "gatto"),
    ("disegnami una pecora", "pecora"),
    ("gere uma imagem de um gato astronauta", "gato astronauta"),
    ("genereer een afbeelding van een kat", "kat"),
    ("kun je een afbeelding van een kat maken?", None),
    ("сгенерируй изображение кота в космосе", "кота в космосе"),
    ("нарисуй кота", "кота"),
    ("生成一张猫的图片", "猫"),
    ("画一只猫", "猫"),
    ("猫の画像を生成して", "猫"),
    ("猫を描いて", "猫"),
    ("고양이 그림을 그려줘", "고양이"),
    ("고양이를 그려줘", "고양이"),
    ("고양이 이미지를 생성해 줘", "고양이"),
    ("ارسم لي قطة", "قطة"),
    ("أنشئ صورة لقطة في الفضاء", "لقطة في الفضاء"),
]

_NOT_REQUESTS = [
    "create an image resizer in python",
    "create a Docker image for my app",
    "make the image bigger",
    "describe this image",
    "draw me a diagram of the architecture",
    "create a photo gallery website",
    "what is the capital of France",
    "crea un cuadro comparativo de lenguajes",
    "crea una imagen de Docker para mi app",
    "Erstelle eine Tabelle der Planeten",
    "crie uma tabela com os planetas",
    "нарисуй график функции sin(x)",
    "画一个流程图",
    "做一个图片压缩工具",
    "グラフを描いて",
    "이 이미지를 설명해줘",
    "이 사진을 설명해줘",
    "صف هذه الصورة",
    "écris une fonction python",
]


@pytest.mark.parametrize("text, subject", _REQUESTS)
def test_image_requests_in_other_languages(text, subject):
    assert is_image_request(text)
    if subject is not None:
        assert strip_image_request(text) == subject


@pytest.mark.parametrize("text", _NOT_REQUESTS)
def test_code_diagrams_and_analysis_are_not_image_requests(text):
    assert not is_image_request(text)


def test_nothing_to_strip_without_a_request():
    assert strip_image_request("bonjour") == ""
    assert strip_image_request("") == ""


class _ImageRouter:
    """Détection d'image d'AIEngine, sans initialiser le moteur."""

    _IMAGE_GEN_RE = AIEngine._IMAGE_GEN_RE  # pylint: disable=protected-access
    _IMAGE_GEN_EXCLUDE_RE = AIEngine._IMAGE_GEN_EXCLUDE_RE  # pylint: disable=protected-access
    is_image_generation_request = AIEngine.is_image_generation_request


@pytest.fixture(name="router")
def _router(monkeypatch):
    class _Config:
        @staticmethod
        def get(_key, default=None):
            return default

    # Indépendant du config.yaml local (image_generation.enabled)
    monkeypatch.setattr("core.ai_engine.get_config", _Config)
    return _ImageRouter()


def test_engine_detects_requests_in_every_language(router):
    for text, _subject in _REQUESTS:
        assert router.is_image_generation_request(text), text
    for text in _NOT_REQUESTS:
        assert not router.is_image_generation_request(text), text
    # Le français garde ses expressions
    assert router.is_image_generation_request("génère moi une image de dauphin")
    assert not router.is_image_generation_request("génère moi un tableau excel fictif")


def test_engine_extracts_the_subject_in_every_language():
    assert AIEngine.extract_image_prompt("génère moi une image de dauphin") == "dauphin"
    assert AIEngine.extract_image_prompt("generate an image of a red fox") == "red fox"
    assert AIEngine.extract_image_prompt("猫の画像を生成して") == "猫"
    # Sujet pris dans la demande (verbe à la fin) : la phrase entière part au générateur
    text = "Kannst du mir ein Bild von einer Katze malen?"
    assert AIEngine.extract_image_prompt(text) == text
