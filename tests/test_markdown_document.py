"""
Tests du parseur Markdown → blocs de document (generators/markdown_document.py).

Le parseur est le socle commun de tous les backends de génération : une
régression ici dégrade silencieusement le DOCX, le PDF, le PPTX et le XLSX.
"""

from generators.markdown_document import (
    LINE_BREAK,
    extract_title,
    parse_inlines,
    parse_markdown,
    strip_leading_title,
)


def _types(blocks):
    """Raccourci : la suite des types de blocs, pour comparer une structure."""
    return [type(block).__name__ for block in blocks]


# ── Titres ─────────────────────────────────────────────────────────────────


def test_headings_levels():
    blocks = parse_markdown("# Un\n\n## Deux\n\n### Trois\n\n###### Six")
    assert _types(blocks) == ["Heading"] * 4
    assert [block.level for block in blocks] == [1, 2, 3, 6]
    assert [block.text for block in blocks] == ["Un", "Deux", "Trois", "Six"]


def test_heading_with_inline_styles():
    blocks = parse_markdown("## Les **baleines** bleues")
    assert blocks[0].text == "Les baleines bleues"
    assert any("bold" in styles for _text, styles, _url in blocks[0].inlines)


def test_hash_without_space_is_not_a_heading():
    blocks = parse_markdown("#pasuntitre")
    assert _types(blocks) == ["Paragraph"]


# ── Paragraphes ────────────────────────────────────────────────────────────


def test_paragraph_lines_stay_in_one_paragraph():
    """Les lignes d'un paragraphe du modèle y restent des lignes ; en CommonMark
    (texte qui ne vient pas du modèle), elles se joignent par une espace."""
    source = "Première ligne\nsuite de la phrase.\n\nAutre paragraphe."
    blocks = parse_markdown(source)
    assert _types(blocks) == ["Paragraph", "Paragraph"]
    assert blocks[0].text == "Première ligne\nsuite de la phrase."
    assert parse_markdown(source, line_breaks=False)[0].text == "Première ligne suite de la phrase."


def test_empty_input_gives_no_blocks():
    assert parse_markdown("") == []
    assert parse_markdown("   \n\n  ") == []


# ── Retours à la ligne forcés ──────────────────────────────────────────────
#
# Régression du 2026-11-18 : un poème de quatre vers rédigé par my_ai, deux
# espaces à la fin de chaque vers comme le veut CommonMark, sortait du PDF en
# un seul paragraphe, ses vers joints par des espaces.

_VERS = [
    ("Vers un,", frozenset(), None),
    LINE_BREAK,
    ("vers deux.", frozenset(), None),
]


def test_two_trailing_spaces_force_a_line_break():
    blocks = parse_markdown("Vers un,  \nvers deux.")
    assert _types(blocks) == ["Paragraph"]
    assert blocks[0].inlines == _VERS
    assert blocks[0].text == "Vers un,\nvers deux."


def test_trailing_backslash_forces_a_line_break():
    assert parse_inlines("Vers un,\\\nvers deux.") == _VERS


def test_poem_keeps_its_four_verses():
    verses = ["Les feuilles tombent,", "Le vent les emporte,",
              "La pluie les rejoint,", "Et l'hiver s'annonce."]
    blocks = parse_markdown("# Automne\n\n" + "  \n".join(verses) + "\n")
    assert _types(blocks) == ["Heading", "Paragraph"]
    assert blocks[1].text.split("\n") == verses


def test_plain_line_ending_of_the_model_breaks_the_line():
    """Contrôle du 2026-11-18 dans l'appli : my_ai a écrit ses vers avec de simples
    fins de ligne, et le PDF les a joints. Un LLM écrit chaque paragraphe d'une
    traite : une fin de ligne y est voulue, elle passe à la ligne, comme dans le chat."""
    verses = ["Les feuilles d'or dansent au vent,", "Le temps des feuilles mortes.",
              "La brise froide souffle lentement,", "Et l'automne nous fait rêver."]
    assert parse_markdown("\n".join(verses))[0].text.split("\n") == verses
    assert parse_markdown("Première ligne \nsuite.")[0].text == "Première ligne\nsuite."
    assert parse_inlines("a\t\nb") == [("a", frozenset(), None), LINE_BREAK,
                                       ("b", frozenset(), None)]


def test_commonmark_joins_a_plain_line_ending_with_a_space():
    """Texte qui ne vient pas du modèle (texte extrait d'un PDF, fichier Markdown) :
    une seule espace, une tabulation ou rien en fin de ligne, la phrase continue ;
    deux espaces ou « \\ » passent à la ligne."""
    assert parse_markdown("Première ligne \nsuite.", line_breaks=False)[0].text == (
        "Première ligne suite.")
    assert parse_inlines("a\t\nb", line_breaks=False) == [("a b", frozenset(), None)]
    assert parse_inlines("Vers un,  \nvers deux.", line_breaks=False) == _VERS
    assert parse_markdown("- Un\n  suite", line_breaks=False)[0].items[0].text == "Un suite"


def test_spaces_around_a_line_break_are_dropped():
    assert parse_inlines("Vers un,    \n    vers deux.") == _VERS
    assert parse_inlines("Vers un, \\\nvers deux.") == _VERS


def test_break_marker_at_the_end_of_a_block_does_not_break():
    """CommonMark : deux espaces en fin de bloc ne comptent pas, un « \\ » reste du texte."""
    assert parse_markdown("Fin du paragraphe.  ")[0].inlines == [
        ("Fin du paragraphe.", frozenset(), None)
    ]
    assert parse_markdown("Fin\\")[0].text == "Fin\\"


def test_two_breaks_in_a_row_leave_an_empty_line():
    assert parse_inlines("a  \n\\\nb") == [
        ("a", frozenset(), None), LINE_BREAK, LINE_BREAK, ("b", frozenset(), None),
    ]


def test_emphasis_spans_a_line_break():
    assert parse_inlines("*vers un,  \nvers deux*") == [
        ("vers un,", frozenset({"italic"}), None),
        LINE_BREAK,
        ("vers deux", frozenset({"italic"}), None),
    ]
    inlines = parse_inlines("**Gras un,  \ngras deux** fin")
    assert LINE_BREAK in inlines and "*" not in "".join(text for text, _s, _u in inlines)


def test_no_line_break_inside_inline_code():
    """Une fin de ligne dans du code en ligne vaut une espace, deux espaces compris."""
    assert parse_inlines("`a  \nb` puis c") == [
        ("a   b", frozenset({"code"}), None), (" puis c", frozenset(), None),
    ]


def test_quote_keeps_its_line_breaks():
    blocks = parse_markdown("> Vers un,  \n> vers deux.")
    assert _types(blocks) == ["Quote"]
    assert blocks[0].inlines == _VERS


def test_list_item_continuation_keeps_breaks_and_styles():
    """La ligne de continuation d'une puce s'analyse avec elle : retour forcé,
    et son gras, laissé en astérisques jusqu'ici."""
    blocks = parse_markdown("- Vers un,  \n  vers **deux**.\n- Autre")
    items = blocks[0].items
    assert [item.text for item in items] == ["Vers un,\nvers deux.", "Autre"]
    assert ("deux", frozenset({"bold"}), None) in items[0].inlines
    # Une continuation du modèle, même sans retour forcé, passe à la ligne
    assert parse_markdown("- Un\n  suite")[0].items[0].text == "Un\nsuite"


# ── Listes ─────────────────────────────────────────────────────────────────


def test_bullet_list_with_nesting():
    blocks = parse_markdown("- Un\n  - Un.a\n    - Un.a.i\n- Deux")
    assert _types(blocks) == ["ListBlock"]
    assert blocks[0].ordered is False
    assert [item.level for item in blocks[0].items] == [0, 1, 2, 0]
    assert [item.text for item in blocks[0].items] == ["Un", "Un.a", "Un.a.i", "Deux"]


def test_ordered_list_is_detected():
    blocks = parse_markdown("1. Premier\n2. Deuxième\n3) Troisième")
    assert len(blocks) == 1
    assert blocks[0].ordered is True
    assert len(blocks[0].items) == 3


def test_switching_list_type_opens_a_new_block():
    blocks = parse_markdown("- Puce\n1. Numéro")
    assert _types(blocks) == ["ListBlock", "ListBlock"]
    assert blocks[0].ordered is False
    assert blocks[1].ordered is True


def test_star_bullet_is_a_list_not_italic():
    blocks = parse_markdown("* Une puce")
    assert _types(blocks) == ["ListBlock"]
    assert blocks[0].items[0].text == "Une puce"


# ── Tableaux ───────────────────────────────────────────────────────────────


def test_table_header_and_rows():
    markdown = "| Espèce | Taille |\n|---|---|\n| Bleue | 30 m |\n| Bosse | 16 m |"
    blocks = parse_markdown(markdown)
    assert _types(blocks) == ["Table"]
    assert blocks[0].header == ["Espèce", "Taille"]
    assert blocks[0].rows == [["Bleue", "30 m"], ["Bosse", "16 m"]]


def test_short_table_rows_are_padded():
    markdown = "| A | B | C |\n|---|---|---|\n| 1 |"
    blocks = parse_markdown(markdown)
    assert blocks[0].rows == [["1", "", ""]]


def test_pipes_without_separator_stay_a_paragraph():
    blocks = parse_markdown("| ceci | n'est pas | un tableau |")
    assert _types(blocks) == ["Paragraph"]


# ── Code, citation, séparateur ─────────────────────────────────────────────


def test_code_block_keeps_content_verbatim():
    blocks = parse_markdown("```python\nif x:\n    # un # dans du code\n    pass\n```")
    assert _types(blocks) == ["CodeBlock"]
    assert blocks[0].language == "python"
    assert blocks[0].code == "if x:\n    # un # dans du code\n    pass"


def test_unclosed_code_block_consumes_the_rest():
    blocks = parse_markdown("```\nsans fermeture")
    assert _types(blocks) == ["CodeBlock"]
    assert blocks[0].code == "sans fermeture"


def test_quote_and_rule():
    blocks = parse_markdown("> Une citation\n\n---\n\nTexte")
    assert _types(blocks) == ["Quote", "Rule", "Paragraph"]
    assert blocks[0].text == "Une citation"


def test_text_right_after_a_quote_comes_after_it():
    """Régression : sans ligne vide, la ligne qui suit une citation sortait avant
    elle. Elle ouvre un paragraphe, comme après une liste (pas de continuation
    paresseuse à la CommonMark : un LLM écrit chaque paragraphe d'une traite)."""
    blocks = parse_markdown("> Une citation\n> sur deux lignes.\nTexte qui suit.")
    assert _types(blocks) == ["Quote", "Paragraph"]
    assert [block.text for block in blocks] == [
        "Une citation\nsur deux lignes.", "Texte qui suit.",
    ]
    assert _types(parse_markdown("Avant\n> Une citation\nAprès")) == [
        "Paragraph", "Quote", "Paragraph",
    ]


def test_quote_followed_by_a_list_or_heading_keeps_the_order():
    assert _types(parse_markdown("> Une citation\n- Une puce")) == ["Quote", "ListBlock"]
    assert _types(parse_markdown("> Une citation\n## Un titre")) == ["Quote", "Heading"]


# ── Fragments inline ───────────────────────────────────────────────────────


def test_inline_bold_italic_code_link():
    inlines = parse_inlines("Du **gras**, de l'*italique*, du `code` et un [lien](http://x.fr).")
    styled = {text: styles for text, styles, _url in inlines}
    assert "bold" in styled["gras"]
    assert "italic" in styled["italique"]
    assert "code" in styled["code"]
    assert any(url == "http://x.fr" for _text, _styles, url in inlines)


def test_inline_bold_containing_italic_keeps_both():
    inlines = parse_inlines("**gras et *aussi italique***")
    combined = [styles for text, styles, _url in inlines if text == "aussi italique"]
    assert combined and {"bold", "italic"} <= combined[0]
    # Aucune étoile orpheline laissée par la fermeture du gras
    assert "*" not in "".join(text for text, _styles, _url in inlines)


def test_inline_triple_marker_is_bold_italic():
    assert parse_inlines("***les deux***") == [
        ("les deux", frozenset({"bold", "italic"}), None)
    ]
    assert parse_inlines("___les deux___") == [
        ("les deux", frozenset({"bold", "italic"}), None)
    ]


def test_inline_italic_containing_bold_keeps_both():
    inlines = parse_inlines("*ital et **gras** fin*")
    styled = {text: styles for text, styles, _url in inlines}
    assert styled["gras"] == frozenset({"bold", "italic"})
    assert "italic" in styled[" fin"]


def test_intraword_underscores_are_not_emphasis():
    """snake_case et noms de fichiers ne doivent pas devenir italiques."""
    assert parse_inlines("Snake_case_ici") == [("Snake_case_ici", frozenset(), None)]
    assert parse_inlines("file_path_ok et a_b_c") == [
        ("file_path_ok et a_b_c", frozenset(), None)
    ]
    # Un vrai italique reste reconnu
    assert parse_inlines("_vrai_") == [("vrai", frozenset({"italic"}), None)]


def test_inline_code_content_is_not_reinterpreted():
    inlines = parse_inlines("`**pas du gras**`")
    assert inlines == [("**pas du gras**", frozenset({"code"}), None)]


def test_inline_plain_text_has_no_styles():
    assert parse_inlines("texte simple") == [("texte simple", frozenset(), None)]


# ── Utilitaires de titre ───────────────────────────────────────────────────


def test_extract_title_returns_first_heading():
    assert extract_title(parse_markdown("Intro\n\n# Le titre\n\n## Autre")) == "Le titre"
    assert extract_title(parse_markdown("Aucun titre ici")) == ""


def test_strip_leading_title_removes_the_duplicate():
    blocks = parse_markdown("# Les baleines\n\nTexte")
    assert _types(strip_leading_title(blocks, "Les baleines")) == ["Paragraph"]
    # Un titre différent est conservé
    assert _types(strip_leading_title(blocks, "Autre chose")) == ["Heading", "Paragraph"]


# ── Document complet ───────────────────────────────────────────────────────


def test_full_document_structure():
    markdown = (
        "# Titre\n\n"
        "Intro avec **gras**.\n\n"
        "## Section\n\n"
        "- a\n- b\n\n"
        "| X | Y |\n|---|---|\n| 1 | 2 |\n\n"
        "> Note\n\n"
        "```py\nprint(1)\n```\n"
    )
    assert _types(parse_markdown(markdown)) == [
        "Heading", "Paragraph", "Heading", "ListBlock", "Table", "Quote", "CodeBlock",
    ]
