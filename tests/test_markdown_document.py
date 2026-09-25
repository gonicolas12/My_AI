"""
Tests du parseur Markdown → blocs de document (generators/markdown_document.py).

Le parseur est le socle commun de tous les backends de génération : une
régression ici dégrade silencieusement le DOCX, le PDF, le PPTX et le XLSX.
"""

from generators.markdown_document import (
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


def test_paragraph_lines_are_joined():
    blocks = parse_markdown("Première ligne\nsuite de la phrase.\n\nAutre paragraphe.")
    assert _types(blocks) == ["Paragraph", "Paragraph"]
    assert blocks[0].text == "Première ligne suite de la phrase."


def test_empty_input_gives_no_blocks():
    assert parse_markdown("") == []
    assert parse_markdown("   \n\n  ") == []


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
