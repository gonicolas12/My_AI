"""
Liens cliquables dans les résultats de la page Agents
(interfaces/agents/output_rendering.py).

Les sources du WebAgent (« [1] [Titre](https://…) ») s'affichaient en texte
brut : le rendu ne connaissait que le gras, l'italique et le code, alors que
le chat rend ces liens cliquables.
"""

import pytest

from interfaces.agents import output_rendering
from interfaces.agents.output_rendering import OutputRenderingMixin, _display_text


class _TextWidget:
    """Ce que le rendu utilise d'un tk.Text : segments insérés et liaisons."""

    def __init__(self):
        self.segments = []
        self.bindings = {}
        self.cursor = "xterm"

    def insert(self, _index, text, tags=()):
        self.segments.append((text, tags if isinstance(tags, tuple) else (tags,)))

    def tag_bind(self, tag, sequence, func):
        self.bindings[(tag, sequence)] = func

    def cget(self, _option):
        return self.cursor

    def configure(self, cursor=None, **_kwargs):
        if cursor is not None:
            self.cursor = cursor

    def text(self):
        return "".join(text for text, _tags in self.segments)

    def links(self):
        return [(text, tags) for text, tags in self.segments if "link" in tags]


@pytest.fixture(name="opened")
def _opened(monkeypatch):
    urls = []
    monkeypatch.setattr(output_rendering.webbrowser, "open", urls.append)
    return urls


def _click(widget, tags):
    tag = next(t for t in tags if t.startswith("link_"))
    return widget.bindings[(tag, "<Button-1>")](None)


def test_liens_markdown_et_adresses_nues_cliquables(opened):
    widget = _TextWidget()
    OutputRenderingMixin()._insert_inline_md(  # pylint: disable=protected-access
        widget,
        "Voir [Classement OCU](https://www.autosblog.fr/classement/) et https://example.org/b.",
        "normal",
    )
    assert widget.text() == (
        "Voir Classement OCU et https://example.org/b."
    )
    links = widget.links()
    assert [text for text, _tags in links] == ["Classement OCU", "https://example.org/b"]
    assert all("normal" in tags for _text, tags in links)

    assert _click(widget, links[0][1]) == "break"
    _click(widget, links[1][1])
    assert opened == ["https://www.autosblog.fr/classement/", "https://example.org/b"]


def test_curseur_main_sur_un_lien():
    widget = _TextWidget()
    OutputRenderingMixin._insert_link(widget, "Doc", "https://example.org", "bullet")  # pylint: disable=protected-access
    tag = next(t for t in widget.segments[0][1] if t.startswith("link_"))
    widget.bindings[(tag, "<Enter>")](None)
    assert widget.cursor == "hand2"
    widget.bindings[(tag, "<Leave>")](None)
    assert widget.cursor == "xterm"


def test_bloc_sources_du_webagent(opened):
    widget = _TextWidget()
    renderer = OutputRenderingMixin()
    for line in (
        "[1] [Marques fiables 2026](https://www.autosblog.fr/marques/)",
        "[2] [Fiabilité OCU](https://automedias.fr/voiture-fiable/)",
    ):
        renderer._insert_inline_md(widget, line, "normal")  # pylint: disable=protected-access
    assert widget.text() == "[1] Marques fiables 2026[2] Fiabilité OCU"
    for _text, tags in widget.links():
        _click(widget, tags)
    assert opened == ["https://www.autosblog.fr/marques/", "https://automedias.fr/voiture-fiable/"]


def test_gras_italique_et_code_inchanges():
    widget = _TextWidget()
    OutputRenderingMixin()._insert_inline_md(widget, "**Toyota** *fiable* `code`", "normal")  # pylint: disable=protected-access
    assert widget.segments == [
        ("Toyota", ("bold",)), (" ", ("normal",)), ("fiable", ("italic",)),
        (" ", ("normal",)), ("code", ("code_inline",)),
    ]


def test_lien_dans_une_cellule_de_tableau(opened):
    widget = _TextWidget()
    OutputRenderingMixin()._insert_table_cell(  # pylint: disable=protected-access
        widget, "voir [OCU](https://www.autosblog.fr/ocu/)", "table_cell"
    )
    assert widget.text() == "voir OCU"
    (_text, tags), = widget.links()
    assert "table_cell" in tags
    _click(widget, tags)
    assert opened == ["https://www.autosblog.fr/ocu/"]


def test_largeur_de_colonne_sans_balisage_de_lien():
    # La largeur des colonnes se calcule sur le texte affiché : avec l'URL
    # comptée, les colonnes du tableau se décalaient
    assert _display_text("[Classement OCU](https://www.autosblog.fr/x/)") == "Classement OCU"
    assert _display_text("**Toyota** `98/100`") == "Toyota 98/100"

