"""
Tests de la recherche internet (models/internet_search.py).

L'ancienne version enchaînait des moteurs qui échouaient (cloudscraper,
Google, SearXNG publics, Brave), puis retombait sur une Wikipédia sans rapport
avec la question : « best car brands 2026 » rendait Dua Lipa et Sting. La
requête du modèle était en plus remplacée par une autre, tirée du message
entier. Aucun réseau ici : les moteurs et les pages sont simulés.
"""

from datetime import date

import pytest

from models import internet_search as ws
from utils.citations import extract_sources, parse_citation_map

YEAR = date.today().year


@pytest.fixture(autouse=True)
def _clean_state():
    ws.reset_state()
    yield
    ws.reset_state()


class _Response:
    """Ce que le module lit d'une réponse requests."""

    def __init__(self, status=200, body=b"", url="https://example.org/",
                 content_type="text/html; charset=utf-8", payload=None):
        self.status_code = status
        self.content = body if isinstance(body, bytes) else body.encode("utf-8")
        self.url = url
        self.headers = {"Content-Type": content_type}
        self._payload = payload

    def json(self):
        if self._payload is None:
            raise ValueError("pas de JSON")
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            import requests  # pylint: disable=import-outside-toplevel
            raise requests.HTTPError(f"HTTP {self.status_code}", response=self)

    def iter_content(self, _size):
        yield self.content

    def __enter__(self):
        return self

    def __exit__(self, *_exc):
        return False


class _Session:
    """Session simulée : une fonction par hôte, et le journal des appels."""

    def __init__(self, routes):
        self.routes = routes
        self.calls = []

    def _answer(self, method, url, **kwargs):
        self.calls.append((method, url))
        for host, handler in self.routes.items():
            if host in url:
                return handler(url, **kwargs)
        return _Response(status=404, url=url)

    def get(self, url, **kwargs):
        return self._answer("GET", url, **kwargs)

    def post(self, url, **kwargs):
        return self._answer("POST", url, **kwargs)

    def hosts(self):
        return [url.split("/")[2] for _method, url in self.calls]


def _use(monkeypatch, routes):
    session = _Session(routes)
    monkeypatch.setattr(ws, "_session", lambda: session)
    return session


DDG_PAGE = """
<html><body>
<div class="result results_links result--ad"><a class="result__a"
   href="https://duckduckgo.com/y.js?ad_domain=pub.example">Publicité</a></div>
<div class="result results_links">
  <a class="result__a" href="//duckduckgo.com/l/?uddg=https%3A%2F%2Fwww.autos.example%2Fclassement%2F&rut=x">
    Classement des <b>marques</b> les plus fiables</a>
  <a class="result__snippet">Toyota, Lexus et Mazda dominent le <b>classement</b> 2026.</a>
</div>
<div class="result results_links">
  <a class="result__a" href="https://fr.wikipedia.org/wiki/Constructeur_(automobile)">Constructeur automobile</a>
  <a class="result__snippet">Un constructeur automobile est une entreprise…</a>
</div>
</body></html>
"""

YAHOO_PAGE = """
<html><body>
<div class="dd algo algo-sr"><div class="compTitle"><h3 class="title">
  <a aria-label="Les marques auto préférées des Français"
     href="https://r.search.yahoo.com/_ylt=A/RV=2/RE=1/RO=10/RU=https%3a%2f%2fwww.journal.example%2fauto%2fmarques%2f/RK=2/RS=abc-">
    <span>www.journal.example › auto</span>Les marques auto préférées des Français</a></h3></div>
  <div class="compText"><p><span>2 mars 2026 ·</span><span>Renault et Peugeot en tête.</span></p></div>
</div>
</body></html>
"""

ARTICLE = """
<html><head><title>Les marques les plus fiables</title></head><body>
<div class="cookie-banner"><p>Nous utilisons des cookies pour améliorer votre expérience de navigation.</p></div>
<nav><ul><li>Accueil</li><li>Essais</li><li>Occasion</li></ul></nav>
<header><h1>Mon site auto</h1></header>
<article>
  <h1>Les marques de voitures les plus fiables</h1>
  <p>La fiabilité est devenue le premier critère d'achat des automobilistes français cette année.</p>
  <p>Ce dossier compare les études européennes et les retours des ateliers indépendants.</p>
  <h2>Le classement des marques les plus fiables</h2>
  <ul><li>Toyota : moteurs hybrides robustes</li><li>Lexus : finition haut de gamme</li>
      <li>Mazda : mécanique simple</li></ul>
  <table><tr><th>Marque</th><th>Note</th></tr><tr><td>Toyota</td><td>92</td></tr></table>
  <aside><p>À lire aussi : nos essais de la semaine, les meilleures citadines du moment.</p></aside>
</article>
<footer><p>Mentions légales, conditions générales et plan du site de Mon site auto.</p></footer>
</body></html>
"""


# ── Requête ──────────────────────────────────────────────────────────────


def test_clean_query_retire_les_annees_ajoutees_par_le_modele():
    # Le cas du journal : le modèle ajoute « 2024 2025 », l'utilisateur rien
    query = ws.clean_query(
        f"meilleures marques de voitures {YEAR - 2} {YEAR - 1} classement",
        "Cherche sur internet les meilleures marques de voiture.\nFais la liste dans un tableau.",
    )
    assert query == "meilleures marques de voitures classement"


def test_clean_query_garde_les_annees_de_l_utilisateur_et_les_anciennes():
    assert ws.clean_query(f"ligue des champions {YEAR - 1}", f"qui a gagné en {YEAR - 1} ?") == (
        f"ligue des champions {YEAR - 1}"
    )
    assert ws.clean_query("construction tour Eiffel 1889", "quand a-t-elle été construite ?") == (
        "construction tour Eiffel 1889"
    )
    assert ws.clean_query(f"salon de l'auto {YEAR}", "") == f"salon de l'auto {YEAR}"


def test_clean_query_premiere_ligne_et_verbe_de_recherche():
    assert ws.clean_query("Cherche sur internet les prix du cuivre\nFais un tableau", "") == (
        "les prix du cuivre"
    )
    assert ws.clean_query("", "Trouve-moi les horaires du musée d'Orsay") == (
        "les horaires du musée d'Orsay"
    )
    assert ws.clean_query("peux-tu chercher la recette du far breton", "") == (
        "la recette du far breton"
    )
    # Des sujets, pas des demandes : rien n'est retiré
    assert ws.clean_query("recherche opérationnelle définition", "") == (
        "recherche opérationnelle définition"
    )
    assert ws.clean_query("recherche d'emploi conseils", "") == "recherche d'emploi conseils"


def test_url_de_la_requete():
    # pylint: disable=protected-access
    assert ws._first_url("résume https://fr.wikipedia.org/wiki/Python_(langage) stp") == (
        "https://fr.wikipedia.org/wiki/Python_(langage)"
    )
    assert ws._first_url("lis cette page (https://example.org/a).") == "https://example.org/a"
    assert ws._first_url("aucune adresse ici") == ""


def test_ponctuation_recollee_sans_coller_les_guillemets():
    # pylint: disable=protected-access
    assert ws._clean("l' Europe et aujourd ' hui , le prix") == "l'Europe et aujourd'hui, le prix"
    assert ws._clean("the 'best' brands") == "the 'best' brands"
    assert ws._clean("Paris est la capitale [1] de la France [réf. nécessaire].") == (
        "Paris est la capitale de la France."
    )


# ── Météo ────────────────────────────────────────────────────────────────


@pytest.mark.parametrize("query,place", [
    ("météo Toulouse", "Toulouse"),
    ("Quel temps fait-il à Saint-Étienne ce week-end ?", "Saint-Étienne"),
    ("weather in New York tomorrow", "New York"),
    ("prévisions météo Bordeaux 7 jours", "Bordeaux"),
])
def test_requete_meteo_et_lieu(query, place):
    assert ws.is_weather_query(query)
    assert ws._weather_place(query) == place  # pylint: disable=protected-access


@pytest.mark.parametrize("query", [
    "combien de temps dure un vol Paris Tokyo",
    "temps de cuisson des pâtes",
    "changement climatique effets",
])
def test_temps_ou_climat_ne_sont_pas_la_meteo(query):
    assert not ws.is_weather_query(query)


def _open_meteo_routes(found=True):
    place = {"name": "Toulouse", "admin1": "Occitanie", "country": "France",
             "latitude": 43.60426, "longitude": 1.44367}
    forecast = {
        "current": {"time": "2026-10-08T09:15", "temperature_2m": 14.3, "apparent_temperature": 12.2,
                    "relative_humidity_2m": 82, "precipitation": 0.0, "weather_code": 3,
                    "wind_speed_10m": 16.9, "wind_direction_10m": 308},
        "daily": {"time": ["2026-10-08", "2026-10-09"], "weather_code": [63, 61],
                  "temperature_2m_max": [17.3, 17.4], "temperature_2m_min": [12.0, 9.5],
                  "precipitation_sum": [7.4, 0.0], "precipitation_probability_max": [98, 5],
                  "wind_speed_10m_max": [21.2, 14.7]},
    }
    return {
        "geocoding-api.open-meteo.com": lambda url, **kw: _Response(
            payload={"results": [place]} if found else {}, content_type="application/json"),
        "api.open-meteo.com": lambda url, **kw: _Response(payload=forecast, content_type="application/json"),
        "html.duckduckgo.com": lambda url, **kw: _Response(body=DDG_PAGE),
    }


def test_meteo_open_meteo(monkeypatch):
    session = _use(monkeypatch, _open_meteo_routes())
    text = ws.EnhancedInternetSearchEngine().search_and_summarize("météo Toulouse")
    assert "Météo à Toulouse, Occitanie, France" in text
    assert "Maintenant : couvert, 14,3 °C (ressenti 12,2 °C)" in text
    assert "vent 17 km/h de nord-ouest" in text
    # Jours repérés par rapport à la date du lieu : sans cela, l'agent web
    # donnait pour « demain » la ligne d'aujourd'hui
    assert (
        "- aujourd'hui (jeudi 8 octobre) : pluie modérée, 12 à 17 °C, "
        "pluie 7,4 mm (probabilité de pluie 98 %)"
    ) in text
    # 0 mm et 5 % : ni cumul ni probabilité, plus de « pluie faible… pas de pluie prévue »
    assert "- demain (vendredi 9 octobre) : pluie faible, 10 à 17 °C, vent jusqu'à 15 km/h" in text
    assert parse_citation_map(text)[1].startswith("https://open-meteo.com/")
    assert "html.duckduckgo.com" not in session.hosts()


def test_meteo_incomplete_passe_par_la_recherche_web(monkeypatch):
    # Valeur nulle d'Open-Meteo : plus d'exception qui sortait de l'outil
    routes = _open_meteo_routes()
    routes["api.open-meteo.com"] = lambda url, **kw: _Response(
        payload={"current": {"temperature_2m": None}, "daily": {}}, content_type="application/json")
    _use(monkeypatch, routes)
    text = ws.EnhancedInternetSearchEngine().search_and_summarize("météo Toulouse")
    assert text.startswith("Résultats de recherche web")


def test_lieu_inconnu_passe_par_la_recherche_web(monkeypatch):
    session = _use(monkeypatch, _open_meteo_routes(found=False))
    text = ws.EnhancedInternetSearchEngine().search_and_summarize("météo Compans Caffarelli")
    assert text.startswith("Résultats de recherche web")
    assert "html.duckduckgo.com" in session.hosts()


# ── Moteurs ──────────────────────────────────────────────────────────────


def test_liens_des_moteurs():
    # pylint: disable=protected-access
    assert ws._ddg_target("//duckduckgo.com/l/?uddg=https%3A%2F%2Fa.example%2Fp&rut=1") == "https://a.example/p"
    assert ws._ddg_target("https://duckduckgo.com/y.js?ad_domain=x") == ""
    assert ws._ddg_target("https://b.example/page") == "https://b.example/page"
    assert ws._yahoo_target(
        "https://r.search.yahoo.com/_ylt=A/RV=2/RU=https%3a%2f%2fc.example%2fx%2f/RK=2/RS=z-"
    ) == "https://c.example/x/"
    assert ws._yahoo_target("https://fr.search.yahoo.com/search?p=autre") == ""
    assert ws._yahoo_target(
        "https://r.search.yahoo.com/RU=https%3a%2f%2fwww.bing.com%2faclick%3fld%3d1/RK=2/RS=z-"
    ) == ""
    # Un article de Yahoo Finance est une source comme une autre
    assert ws._yahoo_target(
        "https://r.search.yahoo.com/RU=https%3a%2f%2ffr.finance.yahoo.com%2fquote%2fAAPL%2f/RK=2/RS=z-"
    ) == "https://fr.finance.yahoo.com/quote/AAPL/"


def test_duckduckgo_sans_publicite(monkeypatch):
    _use(monkeypatch, {"html.duckduckgo.com": lambda url, **kw: _Response(body=DDG_PAGE)})
    response = ws.search_engines("marques de voitures fiables")
    assert response.engine == "DuckDuckGo"
    assert [r.url for r in response.results] == [
        "https://www.autos.example/classement/",
        "https://fr.wikipedia.org/wiki/Constructeur_(automobile)",
    ]
    assert response.results[0].title == "Classement des marques les plus fiables"
    assert response.results[0].snippet == "Toyota, Lexus et Mazda dominent le classement 2026."


def test_moteur_bloque_mis_en_pause(monkeypatch):
    session = _use(monkeypatch, {
        "html.duckduckgo.com": lambda url, **kw: _Response(status=202, body="anomaly"),
        "fr.search.yahoo.com": lambda url, **kw: _Response(body=YAHOO_PAGE, url=url),
    })
    first = ws.search_engines("marques auto préférées")
    assert first.engine == "Yahoo"
    assert first.results[0].title == "Les marques auto préférées des Français"
    assert first.results[0].url == "https://www.journal.example/auto/marques/"
    assert any("DuckDuckGo bloqué" in note for note in first.notes)

    # Deuxième recherche : DuckDuckGo n'est pas relancé pendant sa pause
    second = ws.search_engines("autre recherche")
    assert second.engine == "Yahoo"
    assert session.hosts().count("html.duckduckgo.com") == 1


def test_wikipedia_ne_garde_que_les_articles_pertinents(monkeypatch):
    payload = {"query": {"pages": [
        {"index": 1, "title": "Dua Lipa", "fullurl": "https://en.wikipedia.org/wiki/Dua_Lipa",
         "extract": "Dua Lipa is an English and Albanian singer and songwriter."},
        {"index": 2, "title": "Car brand", "fullurl": "https://en.wikipedia.org/wiki/Car_brand",
         "extract": "Rankings of the best car brands by reliability and sales."},
    ]}}
    _use(monkeypatch, {
        "html.duckduckgo.com": lambda url, **kw: _Response(body="<html></html>"),
        "search.yahoo.com": lambda url, **kw: _Response(body="<html></html>", url=url),
        "wikipedia.org": lambda url, **kw: _Response(payload=payload, content_type="application/json"),
    })
    response = ws.search_engines("best car brands ranking")
    assert response.engine == "Wikipédia"
    assert [r.title for r in response.results] == ["Car brand — Wikipédia"]


def test_aucun_moteur_message_explicite(monkeypatch):
    _use(monkeypatch, {
        "html.duckduckgo.com": lambda url, **kw: _Response(status=429),
        "search.yahoo.com": lambda url, **kw: _Response(status=503, url=url),
        "wikipedia.org": lambda url, **kw: _Response(payload={}, content_type="application/json"),
    })
    text = ws.EnhancedInternetSearchEngine().search_and_summarize("sujet introuvable")
    # « Aucun résultat » : l'orchestrateur invite alors le modèle à reformuler
    assert text.startswith("Aucun résultat trouvé pour « sujet introuvable »")
    assert "DuckDuckGo bloqué" in text and "Yahoo bloqué" in text


# ── Pages ────────────────────────────────────────────────────────────────


def test_texte_de_page_sans_menus_ni_bandeaux():
    title, blocks = ws.page_blocks(ARTICLE.encode("utf-8"))
    assert title == "Les marques les plus fiables"
    joined = "\n".join(blocks)
    for noise in ("cookies", "Accueil", "Mon site auto", "À lire aussi", "Mentions légales"):
        assert noise not in joined
    assert "Toyota : moteurs hybrides robustes" in blocks
    assert "Marque | Note" in blocks and "Toyota | 92" in blocks


def test_page_sous_une_classe_de_bandeau_gardee():
    # Le contenu entier dans <div class="sidebar-layout"> : ce n'est pas un bandeau
    paragraph = "<p>" + "Texte principal de la page sur la fiabilité des marques. " * 8 + "</p>"
    html = f'<html><body><div class="sidebar-layout">{paragraph * 8}</div></body></html>'
    _title, blocks = ws.page_blocks(html.encode("utf-8"))
    assert len(blocks) == 1 and blocks[0].startswith("Texte principal")


def test_code_garde_ses_lignes():
    html = "<html><body><pre>def f(x):\n    return x * 2\n\nprint(f(3))</pre></body></html>"
    _title, blocks = ws.page_blocks(html.encode("utf-8"))
    assert blocks == ["def f(x):\n    return x * 2\nprint(f(3))"]


def test_passages_chapeau_puis_passage_pertinent():
    blocks = [f"Paragraphe d'introduction numéro {i} sans rapport." for i in range(40)]
    blocks[30] = "Le classement des marques les plus fiables"
    blocks[31] = "Toyota : première place"
    text = ws.select_passages(blocks, ws._terms("classement marques fiables"), 400)  # pylint: disable=protected-access
    lines = text.splitlines()
    assert lines[0] == blocks[0]
    assert "[…]" in lines
    assert "Le classement des marques les plus fiables" in lines
    assert "Toyota : première place" in lines
    assert len(text) <= 400 + 10


def test_passages_coupes_sans_bribes():
    text = ws.select_passages(["mot " * 100, "R" * 300], [], 250)
    assert text.endswith("…")
    assert "\nR" not in text


# ── Mise en forme et outil ───────────────────────────────────────────────


def _engine_with_pages(monkeypatch):
    routes = {
        "html.duckduckgo.com": lambda url, **kw: _Response(body=DDG_PAGE),
        "www.autos.example": lambda url, **kw: _Response(body=ARTICLE, url=url),
        "fr.wikipedia.org": lambda url, **kw: _Response(status=403, url=url),
    }
    return _use(monkeypatch, routes), ws.EnhancedInternetSearchEngine()


def test_resultat_de_l_outil_et_citations(monkeypatch):
    _session, engine = _engine_with_pages(monkeypatch)
    text = engine.search_and_summarize("marques de voitures fiables")
    assert text.startswith("Résultats de recherche web pour « marques de voitures fiables » (DuckDuckGo")
    assert "Contenu de la page :" in text and "Toyota : moteurs hybrides robustes" in text
    # Page refusée (403) : l'extrait du moteur reste
    assert "Un constructeur automobile est une entreprise" in text

    citations = parse_citation_map(text)
    assert citations == {
        1: "https://www.autos.example/classement/",
        2: "https://fr.wikipedia.org/wiki/Constructeur_%28automobile%29",
    }
    # Une source par adresse : la ligne « Lien : » ne crée pas de doublon
    assert len(extract_sources(text)) == 2


def test_cache_evite_une_seconde_requete(monkeypatch):
    session, engine = _engine_with_pages(monkeypatch)
    first = engine.search_and_summarize("marques de voitures fiables")
    calls = len(session.calls)
    assert engine.search_and_summarize("Marques de voitures  fiables") == first
    assert len(session.calls) == calls


def test_url_dans_la_requete_lit_la_page(monkeypatch):
    session, engine = _engine_with_pages(monkeypatch)
    text = engine.search_and_summarize("résume https://www.autos.example/classement/")
    assert text.startswith("Contenu de la page « Les marques les plus fiables »")
    assert "Toyota : moteurs hybrides robustes" in text
    assert "html.duckduckgo.com" not in session.hosts()


def test_chemin_custom_ai_ajoute_les_sources_numerotees():
    """CustomAIModel : sa liste de sources suit la réponse, sans consigne contraire."""
    from models.mixins.internet_search import InternetSearchMixin  # pylint: disable=import-outside-toplevel

    class _LocalLLM:
        is_ollama_available = True

        def __init__(self):
            self.conversation_history = []
            self.prompts = []

        def generate_stream(self, prompt, system_prompt=None, on_token=None):
            del system_prompt, on_token
            self.prompts.append(prompt)
            return "Toyota arrive en tête [1]."

    class _Host(InternetSearchMixin):
        def __init__(self):
            self.local_llm = _LocalLLM()

        def _add_to_conversation_history(self, *_args):
            pass

    response = ws.SearchResponse(query="marques fiables", engine="DuckDuckGo", results=[
        ws.SearchResult(title="Classement des marques", url="https://www.autos.example/classement/",
                        snippet="Toyota en tête."),
        ws.SearchResult(title="Python (langage)", url="https://fr.wikipedia.org/wiki/Python_(langage)"),
    ])
    host = _Host()
    answer = host._generate_ollama_search_response(  # pylint: disable=protected-access
        "marques fiables", ws.format_results(response), "quelles marques sont fiables ?"
    )
    assert ws.SOURCES_NOTE not in host.local_llm.prompts[0]
    assert answer.startswith("Toyota arrive en tête [1].")
    assert parse_citation_map(answer) == {
        1: "https://www.autos.example/classement/",
        2: "https://fr.wikipedia.org/wiki/Python_%28langage%29",
    }


def test_moteur_compatible_avec_les_anciens_appelants():
    engine = ws.InternetSearchEngine(llm=object())
    assert engine.search_best_source_context == engine.search_and_summarize


# ── TLS ──────────────────────────────────────────────────────────────────


def _session_with(monkeypatch, tls):
    import core.network  # pylint: disable=import-outside-toplevel
    monkeypatch.setattr(core.network, "tls_settings", lambda: tls)
    return ws._build_session()  # pylint: disable=protected-access


def test_tls_verifie_par_defaut(monkeypatch, tmp_path):
    session = _session_with(monkeypatch, {"ca_bundle": "", "use_system_truststore": True,
                                          "allow_insecure_ssl": False})
    assert session.verify is True
    if ws.truststore is not None:
        assert isinstance(session.get_adapter("https://example.org"), ws._TruststoreAdapter)  # pylint: disable=protected-access
    assert "My_AI" in session.headers["User-Agent"]

    bundle = tmp_path / "racine.pem"
    bundle.write_text("certificat", encoding="utf-8")
    session = _session_with(monkeypatch, {"ca_bundle": str(bundle), "use_system_truststore": True,
                                          "allow_insecure_ssl": False})
    assert session.verify == str(bundle)


def test_tls_desactive_seulement_sur_demande(monkeypatch):
    session = _session_with(monkeypatch, {"ca_bundle": "", "use_system_truststore": True,
                                          "allow_insecure_ssl": True})
    assert session.verify is False


def test_meteo_json_open_meteo_illisible(monkeypatch):
    # Une page d'erreur à la place du JSON : pas de météo, la recherche web prend le relais
    _use(monkeypatch, {
        "geocoding-api.open-meteo.com": lambda url, **kw: _Response(body="<html>erreur</html>"),
        "html.duckduckgo.com": lambda url, **kw: _Response(body=DDG_PAGE),
    })
    assert ws.weather("météo Lyon") is None
