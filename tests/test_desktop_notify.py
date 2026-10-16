"""
Texte des notifications du système (utils/desktop_notify.py, D47)

Le résumé d'une tâche planifiée est le début de la sortie de l'agent, en
Markdown : la notification de Windows le montrait tel quel (« # Analyse : … »,
essai du 2026-10-15). Elle ne montre plus que du texte brut, coupé sur un mot.
"""

import sys
import types

import pytest

from utils.desktop_notify import MESSAGE_LIMIT, notify_desktop, plain_text

# Début du rapport de l'essai du 2026-10-15 (AnalystAgent), tel que le scheduler le résume
REPORT = (
    "# Analyse : Le Meilleur Langage de Code en 2024\n\n"
    "En tant qu'AnalystAgent, j'ai examiné les données actuelles concernant "
    "l'écosystème des langages de programmation (statistiques GitHub, rapports "
    "TIOBE, sondages Stack Overflow, tendances d'embauche et adoption industrielle) "
    "pour déterminer le \"meilleur\" langage.\n\n"
    "La conclusion est claire : **Il n'existe pas un seul \"meilleur\" langage universel**"
)[:280]


def test_the_report_of_the_essay_becomes_plain_text_cut_on_a_word():
    text = plain_text(REPORT, MESSAGE_LIMIT)
    assert text.startswith(
        "Analyse : Le Meilleur Langage de Code en 2024\nEn tant qu'AnalystAgent, j'ai examiné"
    )
    assert "#" not in text and "**" not in text
    assert len(text) <= MESSAGE_LIMIT and text.endswith("…")
    # Coupé entre deux mots du texte brut
    whole = plain_text(REPORT)
    body = text[:-1]
    assert whole.startswith(body) and whole[len(body)] in " \n"


@pytest.mark.parametrize("markdown, expected", [
    ("## Titre\n\nTexte", "Titre\nTexte"),
    ("**gras**, *italique*, __gras__ et _italique_", "gras, italique, gras et italique"),
    ("***les deux***", "les deux"),
    ("Voir [la doc](https://example.org/a) et ![schéma](img.png)", "Voir la doc et schéma"),
    ("- un\n* deux\n+ trois\n1. quatre", "• un\n• deux\n• trois\n1. quatre"),
    ("> citation", "citation"),
    ("avant\n\n---\n\naprès", "avant\naprès"),
    ("```python\nprint(1)\n```", "print(1)"),
    ("le code `x = 1` ici", "le code x = 1 ici"),
    ("| Langage | Usage |\n|---|---|\n| Python | IA |", "Langage · Usage\nPython · IA"),
    ("✅ Fini   🎉\r\n\r\nSuite", "✅ Fini 🎉\nSuite"),
])
def test_markdown_is_reduced_to_its_text(markdown, expected):
    assert plain_text(markdown) == expected


@pytest.mark.parametrize("text", ["3*4*5 = 60", "nom_de_variable et autre_nom", "2**10", "a * b"])
def test_stars_and_underscores_inside_words_are_kept(text):
    assert plain_text(text) == text


def test_markdown_cut_in_the_middle_leaves_no_markup():
    # Résumé coupé au milieu d'un gras ou d'un lien
    assert plain_text("Conclusion : **Il n'existe pas") == "Conclusion : Il n'existe pas"
    assert plain_text("Source : [OCU](https://www.autosblog.fr/cla") == "Source : OCU"


def test_short_text_is_left_whole():
    assert plain_text("Trois articles retenus.", MESSAGE_LIMIT) == "Trois articles retenus."
    assert plain_text("", MESSAGE_LIMIT) == ""


def test_the_system_notification_receives_plain_text(monkeypatch):
    shown = []

    class Notification:  # winotify simulé : aucune vraie notification
        def __init__(self, app_id, title, msg):
            shown.append((app_id, title, msg))

        def show(self):
            pass

    monkeypatch.setitem(sys.modules, "winotify", types.SimpleNamespace(Notification=Notification))
    assert notify_desktop("✅ Tâche planifiée : Veille", REPORT) is True
    (app_id, title, msg), = shown
    assert (app_id, title) == ("My_AI", "✅ Tâche planifiée : Veille")
    assert msg == plain_text(REPORT, MESSAGE_LIMIT)
