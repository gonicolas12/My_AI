"""
Rendu des réponses commun au téléphone (Relay) et à l'extension VS Code.

markdown.js (Markdown des réponses), turn.js (une réponse de la conversation
Code : une bulle, ses appels d'outils dedans, dans l'ordre) et thread.css sont
copiés tels quels dans relay/static/ et vscode_extension/media/ : les deux
surfaces ont le même rendu tant que les copies restent identiques. Ce test le
vérifie, ainsi que le chargement de ces fichiers par les deux pages et leurs
textes dans les deux catalogues. Le rendu Markdown lui-même passe par Node
(sauté sans lui).
"""

import json
import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from relay import relay_server
from relay.relay_server import RelayServer

ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / "relay" / "static"
MEDIA = ROOT / "vscode_extension" / "media"
PROVIDER = ROOT / "vscode_extension" / "src" / "chatViewProvider.ts"
SHARED = ("markdown.js", "turn.js", "thread.css")


@pytest.mark.parametrize("name", SHARED)
def test_shared_files_are_the_same_in_both_places(name):
    assert (STATIC / name).read_bytes() == (MEDIA / name).read_bytes(), (
        f"relay/static/{name} et vscode_extension/media/{name} diffèrent : "
        "recopier le fichier modifié de l'autre côté")


def test_both_pages_load_the_shared_files():
    index = (STATIC / "index.html").read_text(encoding="utf-8")
    chat = (MEDIA / "chat.html").read_text(encoding="utf-8")
    provider = PROVIDER.read_text(encoding="utf-8")
    for name in SHARED:
        assert f"/static/{name}?v=%%ASSET_VERSION%%" in index
        assert "%" + name.replace(".", "_").upper() + "_URI%" in chat
        assert f"uri('{name}')" in provider
    # Le rendu avant les scripts qui s'en servent, sa feuille avant celle de la page
    order = [index.index(f"/static/{name}") for name in
             ("markdown.js", "turn.js", "app.js", "agents.js", "code.js")]
    assert order == sorted(order)
    assert index.index("/static/thread.css") < index.index("/static/style.css")
    order = [chat.index(f"%{name}_URI%") for name in ("MARKDOWN_JS", "TURN_JS", "CHAT_JS")]
    assert order == sorted(order)
    assert chat.index("%THREAD_CSS_URI%") < chat.index("%CHAT_CSS_URI%")
    # Scripts de la vue VS Code : seuls ceux qui portent le nonce s'exécutent
    assert len(re.findall(r'<script nonce="%NONCE%" src=', chat)) == 3


def test_a_shared_file_changes_the_asset_version(monkeypatch, tmp_path):
    """Le téléphone recharge markdown.js, turn.js et thread.css quand ils changent."""
    for name in ("index.html", "app.js", "style.css") + SHARED:
        path = tmp_path / name
        path.write_text("x", encoding="utf-8")
        os.utime(path, (1000, 1000))
    for name, stamp in (("thread.css", 3000), ("turn.js", 5000), ("markdown.js", 4000)):
        os.utime(tmp_path / name, (stamp, stamp))
    monkeypatch.setattr(relay_server, "_STATIC_DIR", tmp_path)
    monkeypatch.setattr(relay_server, "_LOCALES_DIR", tmp_path / "locales")
    assert RelayServer(config={}).get_static_assets_version() == "5000"


def _turn_keys():
    return set(re.findall(r"'(code\.[\w.]+)'", (STATIC / "turn.js").read_text(encoding="utf-8")))


def test_reply_texts_exist_on_the_phone():
    keys = _turn_keys()
    assert len(keys) > 20
    catalog = json.loads((STATIC / "locales" / "fr.json").read_text(encoding="utf-8"))
    assert not sorted(keys - set(catalog))


def test_reply_texts_exist_in_vscode():
    """Les textes des réponses, donnés à la vue par l'extension sous les clés du téléphone."""
    provider = PROVIDER.read_text(encoding="utf-8")
    strings = set(re.findall(r"^\s*'([\w.-]+)':", provider[provider.index("function getWebviewStrings"):],
                             re.M))
    # Message tapé dans VS Code : sa fenêtre de confirmation demande l'accord, pas la bulle
    assert not sorted(_turn_keys() - strings - {"code.approval.inVscode"})


# ── Markdown (markdown.js, par Node) ─────────────────────────────────────────

CASES = {
    "heading": ("## Résumé\nVoici les **points clés** :", {}),
    "nested": ("1. Un\n2. Deux :\n   - a\n   - b\n3. Trois", {}),
    "nested_two_spaces": ("1. Étape\n  - détail\n2. Suite", {}),
    "numbering": ("1. Installer\n```bash\nnpm i\n```\n2. Lancer", {}),
    "html": ('<img src=x onerror="alert(1)"> & <b>gras</b>', {}),
    "unsafe_link": ("[clic](javascript:alert(1)) [doc](https://example.com/a_(b))", {}),
    "code": ('```py\na = "**x**" < 3\n```', {"codeActions": [{"action": "copy", "label": "Copier"}]}),
    "table": ("| a | b |\n|:--|--:|\n| `x|y` | *2* |", {}),
    "citations": ("Paris [1].\n\n📚 **Sources**\n[1] [Wiki](https://fr.wikipedia.org/wiki/Paris)", {}),
    "underscores": ("livre_id, src/*.py et *.js restent tels quels", {}),
    "tasks": ("- [x] fait\n- [ ] à faire", {}),
    "quote": ("> **Note :** relancer\n> le serveur\n\n---\n\nAprès", {}),
    "breaks": ("Ligne 1\nLigne 2\n\nParagraphe 2", {}),
    "cursor_text": ("Bonjour **toi**", {"cursor": True}),
    "cursor_list": ("- a\n- b", {"cursor": True}),
    "cursor_open_fence": ("Voici :\n```js\nconst a", {"cursor": True}),
}

_RENDER_ALL = (
    "const md = require(process.argv[1]);"
    "const cases = JSON.parse(process.argv[2]);"
    "process.stdout.write(JSON.stringify(cases.map(([text, options]) => md.render(text, options))));"
)


@pytest.fixture(name="html", scope="module")
def html_fixture():
    node = shutil.which("node")
    if not node:
        pytest.skip("Node.js absent : rendu Markdown non vérifié")
    result = subprocess.run(
        [node, "-e", _RENDER_ALL, str(STATIC / "markdown.js"), json.dumps(list(CASES.values()))],
        capture_output=True, text=True, encoding="utf-8", check=True, timeout=60,
    )
    return dict(zip(CASES, json.loads(result.stdout)))


def test_heading_is_followed_by_its_text_without_blank_line(html):
    assert html["heading"] == "<h2>Résumé</h2><p>Voici les <strong>points clés</strong> :</p>"


def test_nested_lists_keep_their_numbering(html):
    assert html["nested"] == ("<ol><li>Un</li><li>Deux :<ul><li>a</li><li>b</li></ul></li>"
                              "<li>Trois</li></ol>")
    assert html["nested_two_spaces"] == "<ol><li>Étape<ul><li>détail</li></ul></li><li>Suite</li></ol>"
    # Un bloc de code entre deux éléments : la liste reprend à 2
    assert html["numbering"].endswith('<ol start="2"><li>Lancer</li></ol>')


def test_text_of_the_model_is_never_html(html):
    assert "<img" not in html["html"] and "<b>" not in html["html"]
    assert html["html"] == "<p>&lt;img src=x onerror=&quot;alert(1)&quot;&gt; &amp; &lt;b&gt;gras&lt;/b&gt;</p>"
    # Seuls les liens http(s) et mailto deviennent des liens
    assert "javascript" not in html["unsafe_link"]
    assert html["unsafe_link"].startswith("<p>clic ")
    assert '<a href="https://example.com/a_(b)" target="_blank" rel="noopener noreferrer">doc</a>' in (
        html["unsafe_link"])


def test_code_block_has_its_language_and_buttons(html):
    code = html["code"]
    assert '<span class="md-code-lang">py</span>' in code
    assert '<button type="button" class="md-code-btn" data-action="copy">Copier</button>' in code
    assert "<code>a = &quot;**x**&quot; &lt; 3</code>" in code
    assert "<strong>" not in code


def test_table_cells_are_aligned_and_formatted(html):
    table = html["table"]
    assert '<th style="text-align:left">a</th><th style="text-align:right">b</th>' in table
    # Le | d'un code en ligne ne coupe pas la cellule
    assert '<td style="text-align:left"><code>x|y</code></td>' in table
    assert '<td style="text-align:right"><em>2</em></td>' in table


def test_citations_link_to_their_source(html):
    link = '<a href="https://fr.wikipedia.org/wiki/Paris" class="md-cite" target="_blank"'
    assert html["citations"].startswith("<p>Paris " + link)
    assert '<p class="md-sources">📚 <strong>Sources</strong><br>' in html["citations"]


def test_underscores_and_stars_of_code_are_not_emphasis(html):
    assert html["underscores"] == "<p>livre_id, src/*.py et *.js restent tels quels</p>"


def test_tasks_quotes_rules_and_line_breaks(html):
    assert html["tasks"] == ('<ul><li class="md-task"><input type="checkbox" disabled checked> fait</li>'
                             '<li class="md-task"><input type="checkbox" disabled> à faire</li></ul>')
    assert html["quote"] == ("<blockquote><p><strong>Note :</strong> relancer<br>le serveur</p></blockquote>"
                             "<hr><p>Après</p>")
    assert html["breaks"] == "<p>Ligne 1<br>Ligne 2</p><p>Paragraphe 2</p>"


def test_streaming_cursor_follows_the_last_character(html):
    cursor = '<span class="md-cursor"></span>'
    assert html["cursor_text"] == f"<p>Bonjour <strong>toi</strong>{cursor}</p>"
    assert html["cursor_list"] == f"<ul><li>a</li><li>b{cursor}</li></ul>"
    # Bloc de code pas encore fermé : du code jusqu'à la fin, le curseur dedans
    assert html["cursor_open_fence"].endswith(f"<code>const a{cursor}</code></pre></div>")
