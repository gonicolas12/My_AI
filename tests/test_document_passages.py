"""
Tests de la sélection de passages des longs documents (core/document_passages.py).

Un document plus long que sa place dans le prompt n'était envoyé qu'en partie
(son début) : une question sur la fin du document restait sans réponse. On
vérifie ici que les passages liés à la question sont retenus.
"""

from core.document_passages import select_passages


def _doc(sections, label="SECTION"):
    """Document de `sections` sections numérotées d'environ 1 000 caractères."""
    return "\n".join(
        f"{label} {n}: TITRE {n}\n" + f"texte{n} " * 120 for n in range(1, sections + 1)
    )


def test_text_that_fits_is_returned_unchanged():
    assert select_passages("court", "question", 100) == "court"


def test_numbered_section_is_selected():
    doc = _doc(50)
    result = select_passages(doc, "que dit la section 37 ?", 8000)
    assert "SECTION 37: TITRE 37" in result
    assert result.startswith("[Document long : extraits choisis selon la question")
    assert len(result) < 8000 + 500


def test_rubrique_and_section_are_the_same_word():
    result = select_passages(_doc(50, label="RUBRIQUE"), "de quoi parle la section 12 ?", 8000)
    assert "RUBRIQUE 12: TITRE 12" in result


def test_accents_and_word_forms_are_ignored():
    filler = [f"Paragraphe {n} : remplissage neutre. " * 25 for n in range(40)]
    filler[30] = "Les fichiers ne se chargent pas : vérifiez la sécurité du disque."
    result = select_passages("\n".join(filler), "mon fichier ne se charge pas, securite ?", 4000)
    assert "Les fichiers ne se chargent pas" in result


def test_passages_follow_document_order_after_its_beginning():
    result = select_passages(_doc(50), "sections 40 et 5", 8000)
    beginning = result.index("SECTION 1: TITRE 1")
    assert beginning < result.index("SECTION 5: TITRE 5") < result.index("SECTION 40: TITRE 40")
    assert "[…]" in result


def test_without_matching_words_extracts_cover_whole_document():
    result = select_passages(_doc(50), "résume ce document", 8000)
    assert "SECTION 1: TITRE 1" in result
    assert any(f"texte{n} " in result for n in range(45, 51))


# ── Sens (modèle multilingue, simulé ici) ─────────────────────────────────


def test_meaning_finds_passage_without_shared_words():
    """Question française, document anglais : aucun mot en commun."""
    sections = [f"SECTION {n}: HEADING {n}\n" + f"filler{n} " * 120 for n in range(1, 41)]
    sections[26] = (
        "SECTION 27: PERSONAL PROTECTION\nGloves not normally required. " + "filler " * 110
    )
    doc = "\n".join(sections)
    question = "faut-il porter des gants ?"

    def meaning(_query, passages):
        return [1.0 if "Gloves" in passage else 0.0 for passage in passages]

    assert "Gloves" not in select_passages(doc, question, 4000)  # mots seuls : passage manqué
    assert "Gloves not normally required" in select_passages(doc, question, 4000, meaning)


def test_unavailable_meaning_keeps_keyword_selection():
    doc = _doc(50)
    assert select_passages(doc, "section 37", 8000, lambda _q, _p: None) == select_passages(
        doc, "section 37", 8000
    )


def test_words_and_meaning_both_count():
    def meaning(_query, passages):  # le sens désigne la section 5, les mots la 37
        return [1.0 if "SECTION 5:" in passage else 0.0 for passage in passages]

    result = select_passages(_doc(50), "que dit la section 37 ?", 8000, meaning)
    assert "SECTION 37: TITRE 37" in result and "SECTION 5: TITRE 5" in result
