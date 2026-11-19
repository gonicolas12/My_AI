"""
Page web d'un fichier du disque, pour son aperçu (interfaces/html_page.py)

Vu avec le vrai modèle dans VS Code : web/index.html s'affichait sans son
style.css (le cadre de l'aperçu n'a pas son adresse sur le disque ; la vue de
VS Code répondait 403), et de même dans la fenêtre et sur le téléphone. Les
feuilles de style, scripts et images du dossier de la page sont mis dedans ;
rien d'autre n'est lu.
"""

import base64

from interfaces import html_page
from interfaces.html_page import page_with_assets, preview_fields

PNG = b"\x89PNG\r\n\x1a\n" + b"x" * 20
DATA_PNG = "data:image/png;base64," + base64.b64encode(PNG).decode("ascii")


def site(tmp_path):
    """projet/web avec css/ et img/logo.png"""
    web = tmp_path / "projet" / "web"
    (web / "css").mkdir(parents=True)
    (web / "img").mkdir()
    (web / "img" / "logo.png").write_bytes(PNG)
    return web


def test_a_relative_style_sheet_is_put_in_the_page_with_its_images(tmp_path):
    web = site(tmp_path)
    (web / "css" / "style.css").write_text(
        "h1{color:#2b5797}\nheader{background:url('../img/logo.png')}", encoding="utf-8")
    source = ('<head><link href="css/style.css" rel="stylesheet" media="screen"></head>'
              "<h1>Catalogue</h1>")
    page = page_with_assets(source, str(web / "index.html"))
    assert "<link" not in page
    assert '<style data-href="css/style.css" media="screen">h1{color:#2b5797}' in page
    # url(…) relative à la feuille de style (../img), pas à la page
    assert f'url("{DATA_PNG}")' in page
    assert page.endswith("<h1>Catalogue</h1>")
    assert preview_fields(source, str(web / "index.html")) == {"page": page}


def test_scripts_and_images_of_the_folder_too_deferred_ones_at_the_end(tmp_path):
    web = site(tmp_path)
    (web / "app.js").write_text("document.title = 'prêt'; const fin = '</script>';",
                                encoding="utf-8")
    (web / "outil.js").write_text("var outil = 1;", encoding="utf-8")
    source = ('<html><head><script src="app.js" defer></script><script src=outil.js></script>'
              '</head><body><img alt="logo" src="img/logo.png"><h1>T</h1></body></html>')
    page = page_with_assets(source, str(web / "index.html"))
    # Un script ordinaire à sa place ; un script defer avant </body>, où il se serait exécuté
    assert page.startswith('<html><head><script data-src="outil.js">var outil = 1;</script></head>')
    assert page.endswith('<h1>T</h1><script data-src="app.js">document.title = \'prêt\'; '
                         "const fin = '<\\/script>';</script></body></html>")
    assert f'<img alt="logo" src="{DATA_PNG}">' in page


def test_a_module_script_stays_where_it_is(tmp_path):
    web = site(tmp_path)
    (web / "main.js").write_text("console.log(1)", encoding="utf-8")
    page = page_with_assets('<script type="module" src="main.js"></script><p>x</p>',
                            str(web / "index.html"))
    assert page == '<script type="module" data-src="main.js">console.log(1)</script><p>x</p>'


def test_images_of_the_page_own_style_blocks_too(tmp_path):
    web = site(tmp_path)
    page = page_with_assets("<style>body{background:url(img/logo.png)}</style>",
                            str(web / "index.html"))
    assert page == f'<style>body{{background:url("{DATA_PNG}")}}</style>'


def test_nothing_outside_the_page_folder_nor_remote_nor_absolute_is_read(tmp_path):
    web = site(tmp_path)
    secret = tmp_path / "projet" / "secret.css"
    secret.write_text("h1{color:red}", encoding="utf-8")
    source = ('<link rel="stylesheet" href="../secret.css">'
              '<link rel="stylesheet" href="%2e%2e/secret.css">'
              f'<link rel="stylesheet" href="{secret}">'
              f'<link rel="stylesheet" href="file:///{secret}">'
              '<link rel="stylesheet" href="https://example.com/a.css">'
              '<link rel="stylesheet" href="absent.css">'
              '<link rel="icon" href="img/logo.png">'
              '<script src="https://example.com/a.js"></script>'
              '<img src="//example.com/logo.png"><img src="#ancre"><img src="css">')
    assert page_with_assets(source, str(web / "index.html")) == source
    assert preview_fields(source, str(web / "index.html")) == {}


def test_too_big_files_keep_their_address(tmp_path, monkeypatch):
    web = site(tmp_path)
    (web / "a.css").write_text("h1{color:#111}", encoding="utf-8")
    (web / "b.css").write_text("h2{color:#222}", encoding="utf-8")
    source = '<link rel="stylesheet" href="a.css"><link rel="stylesheet" href="b.css">'
    # Un fichier au-delà de la limite reste dehors…
    monkeypatch.setattr(html_page, "ASSET_MAX", 10)
    assert page_with_assets(source, str(web / "index.html")) == source
    # … et l'ensemble aussi : la première feuille entre, la seconde garde son adresse
    monkeypatch.setattr(html_page, "ASSET_MAX", 100)
    monkeypatch.setattr(html_page, "ASSETS_TOTAL", 20)
    assert page_with_assets(source, str(web / "index.html")) == (
        '<style data-href="a.css">h1{color:#111}</style><link rel="stylesheet" href="b.css">')
