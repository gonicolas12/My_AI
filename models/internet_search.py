"""
Recherche internet de My_AI : moteurs de recherche, lecture des pages, météo.

Refonte d'octobre 2026. L'ancienne version enchaînait sept moteurs qui
échouaient presque tous (cloudscraper, Google, instances SearXNG publiques,
Brave…), retombait sur une recherche Wikipédia sans rapport avec la question
(« best car brands 2026 » → Dua Lipa, Sting) et appelait deux fois le modèle
avant même qu'il ne réponde. Principes de celle-ci :

- Un trafic ordinaire : HTTPS vérifié (magasin de certificats du système, ou
  network.ca_bundle de config.yaml), un User-Agent qui dit qui fait la
  requête, aucun contournement anti-robot, aucun métamoteur public aux
  domaines exotiques.
- Peu de requêtes : un moteur à la fois (DuckDuckGo, puis Yahoo, puis
  Wikipédia) ; un moteur qui renvoie sa page anti-robot est mis en pause au
  lieu d'être relancé à chaque recherche ; les recherches récentes restent
  en cache.
- Aucun appel au modèle : le module renvoie des sources numérotées (titre,
  lien, extrait, passages des pages). Le modèle de la conversation rédige la
  réponse et cite [n] ; le bloc « Sources » final devient cliquable
  (utils/citations.py).
"""

from __future__ import annotations

import re
import ssl
import threading
import time
import unicodedata
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Callable, Dict, List, Optional, Tuple
from urllib.parse import parse_qs, unquote, urlparse

import requests
from bs4 import BeautifulSoup, FeatureNotFound
from requests.adapters import HTTPAdapter

from utils.citations import DEFAULT_HEADER

try:  # magasin de certificats du système (certificat racine d'un proxy d'entreprise)
    import truststore
except ImportError:  # Python < 3.10 ou paquet absent : certifi, le défaut de requests
    truststore = None

# ─────────────────────────────────────────────────────────────────────────────
# Réglages
# ─────────────────────────────────────────────────────────────────────────────

_PROJECT_URL = "https://github.com/gonicolas12/My_AI"
_MAX_RESULTS = 8            # Sources renvoyées au modèle
_PER_DOMAIN = 2             # Sources d'un même site au plus
_PAGES_TO_READ = 4          # Pages ouvertes parmi les premiers résultats
_PAGE_CHARS = 1500          # Passages retenus par page
_URL_PAGE_CHARS = 6000      # Page demandée directement par son URL
_MAX_PAGE_BYTES = 2_000_000
_PAGE_SECONDS = 8.0         # Lecture d'une page, téléchargement compris
_SEARCH_TIMEOUT = (5, 10)   # (connexion, lecture) d'une page de résultats
_PAGE_TIMEOUT = (4, 7)
_BLOCKED_PAUSE = 15 * 60    # Moteur qui a renvoyé sa page anti-robot
_ERROR_PAUSE = 60           # Moteur injoignable (délai dépassé, DNS…)
_CACHE_TTL = 30 * 60
_CACHE_MAX = 64
_STALE_YEARS = 5            # Années « de recul » qu'un modèle ajoute de lui-même

# Sites dont la page ne s'affiche qu'en JavaScript ou derrière une connexion :
# l'extrait du moteur suffit, les ouvrir ne ferait qu'une requête inutile.
_UNREADABLE_DOMAINS = (
    "youtube.com", "youtu.be", "facebook.com", "instagram.com", "x.com",
    "twitter.com", "tiktok.com", "linkedin.com", "pinterest.com",
    "pinterest.fr", "reddit.com",
)
_UNREADABLE_SUFFIXES = (
    ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".zip",
    ".mp3", ".mp4", ".jpg", ".jpeg", ".png", ".gif",
)

_MONTHS_FR = (
    "janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août",
    "septembre", "octobre", "novembre", "décembre",
)
_DAYS_FR = ("lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche")

_STOPWORDS = frozenset(
    """
    le la les un une des du de et ou en au aux ce cet cette ces se sa son ses
    sur sous dans par pour avec sans qui que quoi quel quelle quels quelles est
    sont etre plus moins tres comme pas ne il elle ils elles on nous vous je tu
    mon ma mes ton ta tes leur leurs notre votre nos vos aujourd hui
    the an of to in on for with by from and or is are be at as it its this
    that these those what which who how
    """.split()
)
_ENGLISH_WORDS = frozenset(
    "the of and is are what which who how best top latest news price in for with".split()
)
_FRENCH_WORDS = frozenset(
    """
    le la les des du de et est sont pour sur dans avec quel quelle quels quelles
    comment pourquoi meilleur meilleure meilleurs meilleures prix actualite
    actualites resultat resultats aujourd hui une un
    """.split()
)

# Demande recopiée par le modèle : « Cherche sur internet… », « Trouve-moi… »,
# « Peux-tu chercher… ». « Recherche opérationnelle » ou « recherche d'emploi »
# restent entières : ce sont des sujets.
_SEARCH_PREFIX_RE = re.compile(
    r"^(?:(?:re)?cherche|trouve)r?(?:[- ]moi)?\s+(?:sur\s+(?:internet|le\s+web|google)|en\s+ligne)\s+"
    r"|^(?:cherche|trouve)[- ]moi\s+"
    r"|^(?:peux|pourrais)[- ]tu\s+(?:(?:re)?chercher|trouver)\s+(?:sur\s+(?:internet|le\s+web|google)\s+)?",
    re.IGNORECASE,
)
_URL_RE = re.compile(r"https?://[^\s<>\"'\[\]{}|\\^`]+", re.IGNORECASE)
_YEAR_RE = re.compile(r"\b(?:19|20)\d{2}\b")
_ZERO_WIDTH_RE = re.compile(r"[\u200b-\u200f\u2060\ufeff\u00ad]")
# Renvois de notes d'un wiki (« [1] », « [réf. nécessaire] ») : recopiés dans
# la réponse, ils deviendraient des citations cliquables vers nos sources
_FOOTNOTE_RE = re.compile(
    r"\s?\[(?:\d{1,3}|[a-z]|réf\. nécessaire|modifier|edit|citation needed)\]",
    re.IGNORECASE,
)

# Requête météo explicite. « temps » seul n'en est pas une : « combien de
# temps dure… », « temps de cuisson » partaient avant vers la météo.
_WEATHER_RE = re.compile(
    r"\b(?:m[ée]t[ée]o|weather|forecast)\b|\bquel\s+temps\b|\bpr[ée]visions?\s+m[ée]t[ée]o",
    re.IGNORECASE,
)
# Mots d'une requête météo qui ne sont pas le lieu
_WEATHER_NOISE = frozenset(
    """
    meteo météo weather forecast prevision prévision previsions prévisions
    quel quelle quels quelles temps fait fera va faire sera il est c ce cette
    cet ces la le les l d de du des a à au aux en pour sur dans et
    aujourd hui aujourd'hui demain apres après-demain matin midi soir nuit
    week-end weekend semaine jour jours heure heures maintenant actuel actuelle
    actuellement prochain prochaine prochains prochaines lundi mardi mercredi
    jeudi vendredi samedi dimanche today tomorrow tonight now this next week
    days day hours the in at for of what is like how s
    """.split()
)

# Codes météo de l'OMS renvoyés par Open-Meteo
_WMO_FR = {
    0: "ciel dégagé", 1: "plutôt dégagé", 2: "partiellement nuageux", 3: "couvert",
    45: "brouillard", 48: "brouillard givrant",
    51: "bruine légère", 53: "bruine", 55: "bruine dense",
    56: "bruine verglaçante légère", 57: "bruine verglaçante",
    61: "pluie faible", 63: "pluie modérée", 65: "pluie forte",
    66: "pluie verglaçante faible", 67: "pluie verglaçante forte",
    71: "neige faible", 73: "neige modérée", 75: "neige forte", 77: "grains de neige",
    80: "averses faibles", 81: "averses", 82: "averses violentes",
    85: "averses de neige faibles", 86: "averses de neige fortes",
    95: "orage", 96: "orage avec grêle", 99: "orage avec forte grêle",
}
_WIND_FR = ("nord", "nord-est", "est", "sud-est", "sud", "sud-ouest", "ouest", "nord-ouest")

# Lecture des pages : balises sans texte utile, puis blocs de texte gardés
_NOISE_TAGS = (
    "script", "style", "noscript", "template", "svg", "iframe", "form", "nav",
    "header", "footer", "aside", "button", "select", "input", "label", "menu",
    "dialog", "object", "embed", "canvas",
)
_NOISE_ROLES = frozenset(
    {"navigation", "banner", "contentinfo", "complementary", "dialog", "alert", "search"}
)
# Classe ou identifiant d'un bandeau, d'un menu ou d'une publicité (au début
# du mot, pour épargner « main-content has-sidebar »)
_NOISE_NAME_RE = re.compile(
    r"^(?:cookie|consent|gdpr|rgpd|newsletter|subscribe|abonn|banner|popup|modal|"
    r"share|sharing|social|comments?|related|recommend|breadcrumbs?|sidebar|widget|"
    r"advert|ads?|pub|promo|sponsor|paywall|outbrain|taboola|skip)(?:[-_]|$)",
    re.IGNORECASE,
)
_KEPT_CONTAINERS = frozenset({"html", "body", "main", "article"})
_NOISE_MAX_CHARS = 3000
_BLOCK_TAGS = (
    "h1", "h2", "h3", "h4", "p", "li", "tr", "dd", "dt", "blockquote", "pre",
    "figcaption",
)


class _Blocked(Exception):
    """Le moteur a renvoyé sa page anti-robot ou refusé la requête."""


@dataclass
class SearchResult:
    """Une source : ce qu'en dit le moteur, puis ce qu'on a lu sur la page."""

    title: str
    url: str
    snippet: str = ""
    engine: str = ""
    content: str = ""


@dataclass
class SearchResponse:
    """Résultat d'une recherche : le moteur qui a répondu et ses sources."""

    query: str
    engine: str = ""
    results: List[SearchResult] = field(default_factory=list)
    # Moteurs écartés et pourquoi (en pause, page anti-robot, injoignable…)
    notes: List[str] = field(default_factory=list)


# ─────────────────────────────────────────────────────────────────────────────
# État partagé : plusieurs moteurs sont instanciés (outil web_search,
# CustomAIModel, agents), la pause d'un moteur et le cache valent pour tous.
# ─────────────────────────────────────────────────────────────────────────────

_STATE_LOCK = threading.Lock()
_PAUSED_UNTIL: Dict[str, float] = {}
_CACHE: "OrderedDict[str, Tuple[float, str]]" = OrderedDict()
# Une session HTTP par thread : voir _session()
_LOCAL = threading.local()


def _paused(engine: str) -> bool:
    with _STATE_LOCK:
        return _PAUSED_UNTIL.get(engine, 0.0) > time.monotonic()


def _pause(engine: str, seconds: float) -> None:
    with _STATE_LOCK:
        _PAUSED_UNTIL[engine] = time.monotonic() + seconds


def _cache_get(key: str) -> Optional[str]:
    with _STATE_LOCK:
        entry = _CACHE.get(key)
        if entry is None:
            return None
        if time.monotonic() - entry[0] > _CACHE_TTL:
            del _CACHE[key]
            return None
        _CACHE.move_to_end(key)
        return entry[1]


def _cache_put(key: str, value: str) -> None:
    with _STATE_LOCK:
        _CACHE[key] = (time.monotonic(), value)
        _CACHE.move_to_end(key)
        while len(_CACHE) > _CACHE_MAX:
            _CACHE.popitem(last=False)


def reset_state() -> None:
    """Oublie les pauses et le cache (tests, ou après un changement de réseau)."""
    with _STATE_LOCK:
        _PAUSED_UNTIL.clear()
        _CACHE.clear()


# ─────────────────────────────────────────────────────────────────────────────
# Session HTTP
# ─────────────────────────────────────────────────────────────────────────────


class _TruststoreAdapter(HTTPAdapter):
    """Vérifie les certificats avec le magasin du système (Windows, macOS, Linux).

    Un proxy d'entreprise qui inspecte le TLS signe les pages avec son propre
    certificat racine, installé dans le magasin du système pour que les
    navigateurs l'acceptent. certifi, le défaut de requests, ne le connaît pas :
    c'est pour cela que l'ancienne version coupait toute vérification.
    """

    def init_poolmanager(self, *args, **kwargs):
        kwargs["ssl_context"] = truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        return super().init_poolmanager(*args, **kwargs)

    def proxy_manager_for(self, proxy, **proxy_kwargs):
        proxy_kwargs["ssl_context"] = truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        return super().proxy_manager_for(proxy, **proxy_kwargs)


def _user_agent() -> str:
    """User-Agent au format des robots : il dit qui fait la requête."""
    version = ""
    try:
        from core.config import get_config  # pylint: disable=import-outside-toplevel

        version = str(get_config().get("ai.version", "") or "")
    except Exception:  # noqa: BLE001 - configuration illisible : sans version
        pass
    name = f"My_AI/{version}" if version else "My_AI"
    return f"Mozilla/5.0 (compatible; {name}; +{_PROJECT_URL})"


def _build_session() -> requests.Session:
    """Session HTTP : TLS vérifié selon config.yaml, User-Agent du projet."""
    session = requests.Session()
    session.headers.update({
        "User-Agent": _user_agent(),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.7",
    })
    try:
        from core.network import tls_settings  # pylint: disable=import-outside-toplevel

        tls = tls_settings()
    except Exception:  # noqa: BLE001 - configuration illisible : réglage par défaut
        tls = {"ca_bundle": "", "use_system_truststore": True, "allow_insecure_ssl": False}

    if tls.get("ca_bundle"):
        session.verify = tls["ca_bundle"]
    elif tls.get("allow_insecure_ssl"):
        # Uniquement si l'utilisateur l'a demandé dans config.yaml
        session.verify = False
        print("⚠️ [WEB] network.allow_insecure_ssl : certificats non vérifiés")
    elif tls.get("use_system_truststore", True) and truststore is not None:
        session.mount("https://", _TruststoreAdapter(pool_connections=8, pool_maxsize=8))
    return session


def _session() -> requests.Session:
    """
    Session du thread courant.

    Jamais partagée entre threads : pendant sa poignée de main, le contexte
    TLS de truststore passe en CERT_NONE, et la connexion d'un autre thread
    qui le lisait à cet instant n'était pas vérifiée (urllib3 l'a signalé
    par InsecureRequestWarning sur les pages lues en parallèle).
    """
    session = getattr(_LOCAL, "session", None)
    if session is None:
        session = _LOCAL.session = _build_session()
    return session


# ─────────────────────────────────────────────────────────────────────────────
# Texte
# ─────────────────────────────────────────────────────────────────────────────


def _soup(markup, encoding: Optional[str] = None) -> BeautifulSoup:
    try:
        soup = BeautifulSoup(markup, "lxml", from_encoding=encoding)
    except FeatureNotFound:  # lxml absent
        soup = BeautifulSoup(markup, "html.parser", from_encoding=encoding)
    for br in soup.find_all("br"):
        br.replace_with("\n")
    return soup


def _clean(text: str) -> str:
    """Espaces normalisés, caractères invisibles retirés, ponctuation recollée."""
    text = _ZERO_WIDTH_RE.sub("", text or "")
    text = " ".join(text.split())
    text = _FOOTNOTE_RE.sub("", text)
    # get_text(" ") sépare les balises en ligne : « l' Europe » pour
    # l'<a>Europe</a>, « aujourd ' hui », « mot , ». Élisions seulement, pour
    # ne pas coller « the 'best' brands »
    text = re.sub(
        r"\b(aujourd|jusqu|lorsqu|puisqu|quoiqu|qu|[cdjlmnst])\s*(['’])\s+(?=\w)",
        r"\1\2",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(r"\s+([,.)\]%])", r"\1", text)
    text = re.sub(r"([(\[])\s+", r"\1", text)
    return text.strip()


def _text(element) -> str:
    return _clean(element.get_text(" ")) if element is not None else ""


def _fold(text: str) -> str:
    """Minuscules sans accents, pour comparer des mots."""
    decomposed = unicodedata.normalize("NFKD", text or "")
    return "".join(c for c in decomposed if not unicodedata.combining(c)).lower()


def _words(text: str) -> List[str]:
    return re.findall(r"[a-z0-9]+", _fold(text))


def _stem(word: str) -> str:
    # Préfixe commun aux formes d'un mot : « marques » et « marque »,
    # « hauteur » et « haute »
    return word[:5]


def _terms(text: str) -> List[str]:
    """Mots significatifs d'une requête, réduits à leur préfixe."""
    stems: List[str] = []
    for word in _words(text):
        if len(word) < 3 or word in _STOPWORDS or word.isdigit():
            continue
        stem = _stem(word)
        if stem not in stems:
            stems.append(stem)
    return stems


def _matches(terms: List[str], text: str) -> int:
    """Nombre de mots de la requête présents dans un texte."""
    present = {_stem(w) for w in _words(text) if len(w) >= 3}
    return sum(1 for term in terms if term in present)


def _relevant(terms: List[str], text: str) -> bool:
    """Le texte reprend au moins la moitié des mots de la requête."""
    if not terms:
        return True
    return _matches(terms, text) >= max(1, (len(terms) + 1) // 2)


def _is_french(text: str) -> bool:
    """Langue de la requête, pour la région du moteur et la Wikipédia."""
    if re.search(r"[àâçéèêëîïôûùüÿœ]", text or "", re.IGNORECASE):
        return True
    words = set(_words(text))
    if words & _FRENCH_WORDS:
        return True
    # Français par défaut : une requête sans indice (« Tour Eiffel ») vient
    # le plus souvent d'une conversation en français
    return not words & _ENGLISH_WORDS


def _french_date(day: date) -> str:
    return f"{day.day} {_MONTHS_FR[day.month - 1]} {day.year}"


def _number(value: float, decimals: int = 1) -> str:
    text = f"{value:.{decimals}f}"
    if decimals:
        text = text.rstrip("0").rstrip(".")
    return text.replace(".", ",")


def _domain(url: str) -> str:
    host = urlparse(url).netloc.lower().split("@")[-1].split(":")[0]
    return host[4:] if host.startswith("www.") else host


def _link_target(url: str) -> str:
    """URL utilisable dans un lien Markdown (les parenthèses le refermaient)."""
    return url.replace(" ", "%20").replace("(", "%28").replace(")", "%29")


def _link_label(result: SearchResult) -> str:
    label = result.title.replace("[", "(").replace("]", ")").strip() or _domain(result.url)
    return label if len(label) <= 90 else label[:87].rstrip() + "…"


# ─────────────────────────────────────────────────────────────────────────────
# Requête
# ─────────────────────────────────────────────────────────────────────────────


def clean_query(query: str, user_message: str = "") -> str:
    """
    Requête prête pour le moteur, à partir de celle qu'a choisie le modèle.

    Le modèle ne connaît pas la date du jour : il ajoute les années de son
    apprentissage (« meilleures marques de voitures 2024 2025 »), et le
    moteur remonte alors des pages périmées. Ces années récentes sont
    retirées quand l'utilisateur ne les a pas écrites lui-même ; une année
    ancienne (« construction tour Eiffel 1889 ») reste, elle est voulue.

    Args:
        query: Requête passée par le modèle à l'outil web_search.
        user_message: Message de l'utilisateur, pour les années qu'il a données
            et pour une requête vide.
    """
    text = (query or "").strip()
    if not text:
        text = (user_message or "").strip()
    # Le modèle recopie parfois toute la demande : son premier sujet suffit
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    text = lines[0] if lines else ""
    text = _SEARCH_PREFIX_RE.sub("", text)
    text = " ".join(text.split()).strip(" \"'«»“”`")
    if len(text.split()) > 14 and ". " in text:
        text = text.split(". ", 1)[0]

    current_year = date.today().year
    user_years = set(_YEAR_RE.findall(user_message or ""))

    def _drop_stale(match: "re.Match[str]") -> str:
        year = match.group(0)
        if year in user_years or not current_year - _STALE_YEARS <= int(year) < current_year:
            return year
        return ""

    without_stale = " ".join(_YEAR_RE.sub(_drop_stale, text).split())
    if without_stale:
        text = without_stale
    return text[:200].strip()


def is_weather_query(query: str) -> bool:
    """Vraie requête météo : météo, weather, forecast, « quel temps »."""
    return bool(_WEATHER_RE.search(query or ""))


def _weather_place(query: str) -> str:
    """Lieu d'une requête météo : ce qui reste une fois les autres mots retirés."""
    kept = []
    for token in re.findall(r"[\w'’-]+", query or ""):
        token = token.strip("'’-")
        lowered = token.lower().replace("’", "'")
        if not token or token.isdigit():
            continue
        if lowered in _WEATHER_NOISE:
            continue
        # « fait-il », « l'après-midi » : bruit si chaque morceau en est
        parts = [p for p in re.split(r"['-]", lowered) if p]
        if parts and all(p in _WEATHER_NOISE for p in parts):
            continue
        # « l'Isle-Jourdain » : le lieu sans l'article élidé
        kept.append(re.sub(r"^(?:l|d)['’]", "", token, flags=re.IGNORECASE))
    return " ".join(kept).strip()


def _first_url(text: str) -> str:
    match = _URL_RE.search(text or "")
    if not match:
        return ""
    url = match.group(0).rstrip(".,;:!?»")
    # « (voir https://…) » : cette parenthèse est celle de la phrase, pas
    # celle de https://fr.wikipedia.org/wiki/Python_(langage)
    while url.endswith(")") and url.count(")") > url.count("("):
        url = url[:-1].rstrip(".,;:!?»")
    return url


# ─────────────────────────────────────────────────────────────────────────────
# Moteurs
# ─────────────────────────────────────────────────────────────────────────────


def _ddg_target(href: str) -> str:
    """Adresse d'un résultat DuckDuckGo, redirection //duckduckgo.com/l/ comprise."""
    href = (href or "").strip()
    if href.startswith("//"):
        href = "https:" + href
    parsed = urlparse(href)
    if parsed.netloc.endswith("duckduckgo.com"):
        # Lien de redirection (uddg) ; sans lui, une publicité (y.js)
        href = parse_qs(parsed.query).get("uddg", [""])[0]
        parsed = urlparse(href)
    return href if parsed.scheme in ("http", "https") and parsed.netloc else ""


def _yahoo_target(href: str) -> str:
    """Adresse d'un résultat Yahoo, sortie de sa redirection r.search.yahoo.com."""
    href = (href or "").strip()
    if "/RU=" in href:
        # La cible est encodée : son premier « /R » est celui du paramètre suivant
        href = unquote(href.split("/RU=", 1)[1].split("/R", 1)[0])
    parsed = urlparse(href)
    host = parsed.netloc.lower()
    if parsed.scheme not in ("http", "https") or not host:
        return ""
    # Recherches associées et publicités ; Yahoo Finance reste une source
    if host.endswith("search.yahoo.com") or host.endswith("bing.com"):
        return ""
    return href


def _normalized(url: str) -> str:
    parsed = urlparse(url)
    return f"{_domain(url)}{parsed.path.rstrip('/')}?{parsed.query}"


def _dedupe(results: List[SearchResult]) -> List[SearchResult]:
    """Une source par adresse, deux par site au plus."""
    kept: List[SearchResult] = []
    seen = set()
    per_domain: Dict[str, int] = {}
    for result in results:
        if not result.url or not result.title:
            continue
        key = _normalized(result.url)
        domain = _domain(result.url)
        if key in seen or per_domain.get(domain, 0) >= _PER_DOMAIN:
            continue
        seen.add(key)
        per_domain[domain] = per_domain.get(domain, 0) + 1
        kept.append(result)
        if len(kept) >= _MAX_RESULTS:
            break
    return kept


def _search_duckduckgo(query: str, french: bool) -> List[SearchResult]:
    """DuckDuckGo, version HTML sans JavaScript (html.duckduckgo.com)."""
    response = _session().post(
        "https://html.duckduckgo.com/html/",
        data={"q": query, "kl": "fr-fr" if french else "wt-wt"},
        timeout=_SEARCH_TIMEOUT,
    )
    # 202 : page « anomalie » anti-robot, celle qu'obtenait cloudscraper
    if response.status_code in (202, 403, 429):
        raise _Blocked(f"HTTP {response.status_code}")
    response.raise_for_status()
    soup = _soup(response.content)
    if soup.select_one("#challenge-form, .anomaly-modal__title, .anomaly-modal"):
        raise _Blocked("page anti-robot")

    results = []
    for block in soup.select("div.result"):
        if "result--ad" in (block.get("class") or []):
            continue
        link = block.select_one("a.result__a")
        if link is None:
            continue
        results.append(SearchResult(
            title=_text(link),
            url=_ddg_target(link.get("href", "")),
            snippet=_text(block.select_one(".result__snippet")),
            engine="DuckDuckGo",
        ))
    return results


def _search_yahoo(query: str, french: bool) -> List[SearchResult]:
    """Yahoo (index de Bing), page de résultats HTML classique."""
    host = "fr.search.yahoo.com" if french else "search.yahoo.com"
    response = _session().get(
        f"https://{host}/search", params={"p": query}, timeout=_SEARCH_TIMEOUT
    )
    if response.status_code in (403, 429, 503):
        raise _Blocked(f"HTTP {response.status_code}")
    response.raise_for_status()
    if "consent." in urlparse(response.url).netloc:
        raise _Blocked("page de consentement")
    soup = _soup(response.content)

    results = []
    for block in soup.select("div.algo"):
        link = block.select_one("h3 a[href]") or block.select_one("a[href]")
        if link is None:
            continue
        # aria-label : le titre seul, sans le fil d'Ariane affiché au-dessus
        title = _clean(link.get("aria-label", "")) or _text(block.select_one("h3"))
        results.append(SearchResult(
            title=title,
            url=_yahoo_target(link.get("href", "")),
            snippet=_text(block.select_one("div.compText")),
            engine="Yahoo",
        ))
    return results


def _search_wikipedia(query: str, french: bool) -> List[SearchResult]:
    """
    Wikipédia, en dernier recours : articles pertinents seulement.

    Une requête suffit (generator=search + introductions). L'ancienne version
    lisait chaque article en entier, une requête par page, puis gardait les
    trois premiers même sans aucun rapport avec la question.
    """
    lang = "fr" if french else "en"
    response = _session().get(
        f"https://{lang}.wikipedia.org/w/api.php",
        params={
            "action": "query", "format": "json", "formatversion": "2",
            "generator": "search", "gsrsearch": query, "gsrlimit": "6",
            "gsrnamespace": "0", "prop": "extracts|info", "exintro": "1",
            "explaintext": "1", "exchars": "1200", "inprop": "url", "redirects": "1",
        },
        timeout=_SEARCH_TIMEOUT,
    )
    if response.status_code == 429:
        raise _Blocked("HTTP 429")
    response.raise_for_status()
    pages = response.json().get("query", {}).get("pages", [])
    pages.sort(key=lambda page: page.get("index", 99))

    terms = _terms(query)
    results = []
    for page in pages:
        title = page.get("title", "")
        extract = _clean(page.get("extract") or "")
        if not extract or not _relevant(terms, f"{title} {extract}"):
            continue
        results.append(SearchResult(
            title=f"{title} — Wikipédia",
            url=page.get("fullurl") or f"https://{lang}.wikipedia.org/wiki/{title.replace(' ', '_')}",
            snippet=extract[:300],
            content=extract,
            engine="Wikipédia",
        ))
    return results


# Ordre d'essai : le premier qui renvoie des résultats répond
_ENGINES: Tuple[Tuple[str, Callable[[str, bool], List[SearchResult]]], ...] = (
    ("DuckDuckGo", _search_duckduckgo),
    ("Yahoo", _search_yahoo),
    ("Wikipédia", _search_wikipedia),
)


def search_engines(query: str) -> SearchResponse:
    """Interroge les moteurs dans l'ordre, sans relancer un moteur en pause."""
    response = SearchResponse(query=query)
    french = _is_french(query)
    for name, engine in _ENGINES:
        if _paused(name):
            response.notes.append(f"{name} en pause")
            continue
        started = time.monotonic()
        try:
            results = _dedupe(engine(query, french))
        except _Blocked as exc:
            _pause(name, _BLOCKED_PAUSE)
            response.notes.append(f"{name} bloqué ({exc})")
            print(f"⏸️ [WEB] {name} en pause {_BLOCKED_PAUSE // 60} min ({exc})")
            continue
        except (requests.RequestException, ValueError) as exc:
            # ValueError : JSON illisible (page d'erreur à la place de l'API)
            _pause(name, _ERROR_PAUSE)
            response.notes.append(f"{name} injoignable")
            print(f"⚠️ [WEB] {name} injoignable : {type(exc).__name__}: {str(exc)[:120]}")
            continue
        except Exception as exc:  # noqa: BLE001 - page de résultats inattendue
            response.notes.append(f"{name} illisible")
            print(f"⚠️ [WEB] {name} illisible : {type(exc).__name__}: {str(exc)[:120]}")
            continue
        elapsed = time.monotonic() - started
        if results:
            print(f"🔍 [WEB] « {query} » → {name} : {len(results)} résultats ({elapsed:.1f} s)")
            response.engine = name
            response.results = results
            return response
        response.notes.append(f"{name} sans résultat")
    return response


# ─────────────────────────────────────────────────────────────────────────────
# Lecture des pages
# ─────────────────────────────────────────────────────────────────────────────


def _readable(url: str) -> bool:
    domain = _domain(url)
    if any(domain == d or domain.endswith("." + d) for d in _UNREADABLE_DOMAINS):
        return False
    return not urlparse(url).path.lower().endswith(_UNREADABLE_SUFFIXES)


def _fetch_html(url: str, seconds: float = _PAGE_SECONDS) -> Tuple[bytes, Optional[str]]:
    """
    Télécharge une page HTML, taille et durée bornées.

    Returns:
        (contenu, encodage annoncé par le serveur ou None)
    """
    started = time.monotonic()
    with _session().get(url, timeout=_PAGE_TIMEOUT, stream=True) as response:
        response.raise_for_status()
        content_type = response.headers.get("Content-Type", "").lower()
        if "html" not in content_type and "xml" not in content_type:
            raise ValueError(f"pas une page HTML ({content_type or 'type inconnu'})")
        encoding = None
        if "charset=" in content_type:
            encoding = content_type.split("charset=", 1)[1].split(";")[0].strip(" \"'")
        chunks: List[bytes] = []
        size = 0
        for chunk in response.iter_content(65536):
            chunks.append(chunk)
            size += len(chunk)
            if size >= _MAX_PAGE_BYTES or time.monotonic() - started > seconds:
                break
        return b"".join(chunks), encoding


def _main_container(soup: BeautifulSoup):
    """Partie principale de la page : l'article (ou main) le plus fourni."""
    candidates = soup.find_all(["article", "main"]) + soup.find_all(attrs={"role": "main"})
    best, best_size = None, 0
    for candidate in candidates:
        size = len(candidate.get_text(" ", strip=True))
        if size > best_size:
            best, best_size = candidate, size
    if best is not None and best_size >= 500:
        return best
    return soup.body or soup


def _remove_noise(soup: BeautifulSoup) -> None:
    for tag in soup(_NOISE_TAGS):
        tag.decompose()
    for tag in soup.find_all(True):
        if tag.decomposed or tag.name in _KEPT_CONTAINERS:
            continue
        attrs = tag.attrs or {}
        names = list(attrs.get("class") or [])
        if attrs.get("id"):
            names.append(str(attrs["id"]))
        if not (
            attrs.get("role") in _NOISE_ROLES
            or attrs.get("aria-hidden") == "true"
            or "hidden" in attrs
            or any(_NOISE_NAME_RE.match(name) for name in names)
        ):
            continue
        # Un bandeau ou un menu est court : au-delà, c'est la page elle-même
        # sous une classe trompeuse (« sidebar-layout », « modal-page »)
        if len(tag.get_text(" ", strip=True)) <= _NOISE_MAX_CHARS:
            tag.decompose()


def page_blocks(raw: bytes, encoding: Optional[str] = None) -> Tuple[str, List[str]]:
    """
    Texte d'une page, bloc par bloc, sans menus ni bandeaux.

    Returns:
        (titre de la page, blocs de texte dans l'ordre de lecture)
    """
    soup = _soup(raw, encoding)
    title = _text(soup.title) if soup.title else ""
    _remove_noise(soup)
    root = _main_container(soup)

    blocks: List[str] = []
    seen = set()
    for element in root.find_all(_BLOCK_TAGS):
        if element.name == "tr":
            text = " | ".join(t for t in (_text(c) for c in element.find_all(["th", "td"])) if t)
        elif element.name == "pre":
            # Code : ses lignes comptent, seuls les blancs de fin sont retirés
            text = "\n".join(
                line.rstrip() for line in element.get_text().splitlines() if line.strip()
            )
        elif element.find(_BLOCK_TAGS):
            continue  # le texte est repris par les blocs qu'il contient
        else:
            text = _text(element)
        minimum = 40 if element.name == "p" else 3
        if len(text) < minimum or text in seen:
            continue
        seen.add(text)
        blocks.append(text)

    if not blocks:  # page sans paragraphes : lignes de texte assez longues
        for line in root.get_text("\n").splitlines():
            line = _clean(line)
            if len(line) >= 40 and line not in seen:
                seen.add(line)
                blocks.append(line)
    return title, blocks


def select_passages(blocks: List[str], terms: List[str], budget: int) -> str:
    """
    Passages d'une page à transmettre au modèle, dans l'ordre de lecture.

    Le début de la page (le chapeau), puis le passage qui reprend le plus de
    mots de la requête et ce qui le suit : un titre « Classement des marques
    les plus fiables » et la liste qu'il annonce. Le reste du budget suit
    l'ordre de lecture.
    """
    if not blocks or budget <= 0:
        return ""
    picked: Dict[int, str] = {}
    used = 0

    def take(index: int) -> None:
        nonlocal used
        if index in picked or used >= budget:
            return
        text = blocks[index]
        room = budget - used
        if len(text) > room:
            # Bloc coupé : le budget est épuisé (sans cela, le reste de place
            # ajoutait des bribes d'une lettre, « R… »)
            used = budget
            if room < 80:
                return
            text = text[:room].rsplit(" ", 1)[0].rstrip(",;:") + "…"
        else:
            used += len(text) + 1
        picked[index] = text

    index = 0
    while index < len(blocks) and used < budget // 4:
        take(index)
        index += 1

    if terms:
        scores = [_matches(terms, block) for block in blocks]
        best = max(range(len(blocks)), key=lambda k: (scores[k], -k))
        if scores[best] > 0:
            for index in range(best, len(blocks)):
                if used >= budget:
                    break
                take(index)

    for index in range(len(blocks)):
        if used >= budget:
            break
        take(index)

    parts: List[str] = []
    previous = -1
    for index in sorted(picked):
        if parts and index != previous + 1:
            parts.append("[…]")
        parts.append(picked[index])
        previous = index
    return "\n".join(parts)


def _read_page(result: SearchResult, terms: List[str]) -> bool:
    """Complète une source avec les passages de sa page ; False si illisible."""
    try:
        raw, encoding = _fetch_html(result.url)
        _title, blocks = page_blocks(raw, encoding)
    except Exception as exc:  # noqa: BLE001 - une page illisible garde son extrait
        print(f"   ↳ page non lue ({type(exc).__name__}) : {result.url[:90]}")
        return False
    passages = select_passages(blocks, terms, _PAGE_CHARS)
    if len(passages) < 80:
        return False
    result.content = passages
    return True


def read_pages(results: List[SearchResult], query: str, limit: int = _PAGES_TO_READ) -> int:
    """Lit en parallèle les premières pages des résultats. Renvoie le nombre lu."""
    targets = [r for r in results if not r.content and _readable(r.url)][:limit]
    if not targets:
        return 0
    terms = _terms(query)
    started = time.monotonic()
    with ThreadPoolExecutor(max_workers=len(targets)) as pool:
        done = sum(pool.map(lambda result: _read_page(result, terms), targets))
    print(f"📄 [WEB] {done}/{len(targets)} pages lues ({time.monotonic() - started:.1f} s)")
    return done


# ─────────────────────────────────────────────────────────────────────────────
# Mise en forme pour le modèle
# ─────────────────────────────────────────────────────────────────────────────

# Consigne, puis le bloc que le modèle recopie à la fin de sa réponse : son
# en-tête est celui de utils/citations.py, et les [n] y deviennent cliquables.
SOURCES_NOTE = (
    "Pour répondre : appuie-toi uniquement sur ces sources, sans ajouter de "
    "chiffre, de note ou de rang qu'elles ne donnent pas, place le marqueur [n] "
    "après chaque information qui en vient, et termine ta réponse par ce bloc, "
    "recopié tel quel :"
)


def _sources_block(results: List[SearchResult]) -> str:
    lines = [SOURCES_NOTE, "", DEFAULT_HEADER]
    for number, result in enumerate(results, 1):
        lines.append(f"[{number}] [{_link_label(result)}]({_link_target(result.url)})")
    return "\n".join(lines)


def format_results(response: SearchResponse) -> str:
    """Sources numérotées, puis le bloc de liens que le modèle recopie."""
    lines = [
        f"Résultats de recherche web pour « {response.query} » "
        f"({response.engine}, {_french_date(date.today())}) :",
        "",
    ]
    for number, result in enumerate(response.results, 1):
        lines.append(f"[{number}] {result.title}")
        # Même écriture que dans le bloc Sources : extract_sources (utils/
        # citations.py) y verrait sinon deux adresses, la brute coupée à « ( »
        lines.append(f"Lien : {_link_target(result.url)}")
        if result.snippet:
            lines.append(f"Extrait : {result.snippet}")
        if result.content and result.content != result.snippet:
            lines.append(f"Contenu de la page :\n{result.content}")
        lines.append("")
    lines.append(_sources_block(response.results))
    return "\n".join(lines)


def _no_result_message(response: SearchResponse) -> str:
    reasons = " ; ".join(response.notes) or "aucun moteur disponible"
    return (
        f"Aucun résultat trouvé pour « {response.query} » ({reasons}). "
        "Reformule avec d'autres mots-clés, ou réponds avec ce que tu sais "
        "en précisant que la recherche n'a rien donné."
    )


# ─────────────────────────────────────────────────────────────────────────────
# Météo (Open-Meteo : sans clé, données des services météo nationaux)
# ─────────────────────────────────────────────────────────────────────────────


def _geocode(place: str, french: bool) -> Optional[Dict]:
    response = _session().get(
        "https://geocoding-api.open-meteo.com/v1/search",
        params={"name": place, "count": 1, "language": "fr" if french else "en", "format": "json"},
        timeout=_SEARCH_TIMEOUT,
    )
    response.raise_for_status()
    results = response.json().get("results") or []
    return results[0] if results else None


def _weather_report(place: Dict) -> str:
    response = _session().get(
        "https://api.open-meteo.com/v1/forecast",
        params={
            "latitude": place["latitude"],
            "longitude": place["longitude"],
            "timezone": "auto",
            "forecast_days": 7,
            "current": (
                "temperature_2m,apparent_temperature,relative_humidity_2m,"
                "precipitation,weather_code,wind_speed_10m,wind_direction_10m"
            ),
            "daily": (
                "weather_code,temperature_2m_max,temperature_2m_min,precipitation_sum,"
                "precipitation_probability_max,wind_speed_10m_max"
            ),
        },
        timeout=_SEARCH_TIMEOUT,
    )
    response.raise_for_status()
    data = response.json()
    current = data.get("current") or {}
    daily = data.get("daily") or {}

    location = ", ".join(
        part for part in (place.get("name"), place.get("admin1"), place.get("country")) if part
    )
    measured = current.get("time", "")
    # Le jour du lieu, pas celui du PC : à New York, il est encore la veille
    today = date.today()
    try:
        moment = datetime.fromisoformat(measured)
        measured = f"{_french_date(moment.date())} à {moment:%H:%M}"
        today = moment.date()
    except ValueError:
        pass

    wind_dir = current.get("wind_direction_10m")
    wind_from = f" de {_WIND_FR[round(wind_dir / 45) % 8]}" if wind_dir is not None else ""
    lines = [
        f"Météo à {location} — données Open-Meteo du {measured} (heure locale) :",
        "",
        (
            f"Maintenant : {_WMO_FR.get(current.get('weather_code'), 'temps inconnu')}, "
            f"{_number(current.get('temperature_2m', 0))} °C "
            f"(ressenti {_number(current.get('apparent_temperature', 0))} °C), "
            f"humidité {current.get('relative_humidity_2m', '?')} %, "
            f"vent {_number(current.get('wind_speed_10m', 0), 0)} km/h{wind_from}, "
            f"précipitations {_number(current.get('precipitation', 0))} mm."
        ),
        "",
        "Prévisions :",
    ]
    for i, day_text in enumerate(daily.get("time") or []):
        try:
            day = date.fromisoformat(day_text)
            label = f"{_DAYS_FR[day.weekday()]} {day.day} {_MONTHS_FR[day.month - 1]}"
            # Le modèle ignore la date du jour : sans ces repères, « demain »
            # devenait la première ligne, celle d'aujourd'hui
            if day == today:
                label = f"aujourd'hui ({label})"
            elif day == today + timedelta(days=1):
                label = f"demain ({label})"
        except ValueError:
            label = day_text

        def value(key: str, i: int = i):
            values = daily.get(key) or []
            return values[i] if i < len(values) and values[i] is not None else None

        rain = value("precipitation_sum") or 0
        chance = value("precipitation_probability_max")
        # Le code du jour est le temps le plus marqué : « pluie faible »
        # avec 0 mm au total ne mérite pas de cumul
        # « probabilité de pluie » : « risque 98 % » était relu « 98 % d'orage »
        if rain >= 0.1:
            rain_text = f", pluie {_number(rain)} mm"
            if chance is not None:
                rain_text += f" (probabilité de pluie {chance} %)"
        elif chance is not None and chance >= 20:
            rain_text = f", probabilité de pluie {chance} %"
        else:
            rain_text = ""
        lines.append(
            f"- {label} : {_WMO_FR.get(value('weather_code'), 'temps inconnu')}, "
            f"{_number(value('temperature_2m_min') or 0, 0)} à "
            f"{_number(value('temperature_2m_max') or 0, 0)} °C{rain_text}, "
            f"vent jusqu'à {_number(value('wind_speed_10m_max') or 0, 0)} km/h"
        )

    source = SearchResult(
        title=f"Open-Meteo — prévisions pour {place.get('name', '')}",
        url=(
            "https://open-meteo.com/en/docs"
            f"?latitude={place['latitude']:.4f}&longitude={place['longitude']:.4f}"
        ),
    )
    lines += ["", _sources_block([source])]
    return "\n".join(lines)


def weather(query: str) -> Optional[str]:
    """
    Météo d'un lieu nommé dans la requête, ou None pour une recherche web.

    None aussi quand le lieu est inconnu d'Open-Meteo (un quartier, une
    adresse) : les sites météo trouvés par le moteur répondront mieux qu'un
    lieu homonyme à l'autre bout du monde.
    """
    place_name = _weather_place(query)
    if not place_name:
        return None
    key = f"meteo:{_fold(place_name)}"
    cached = _cache_get(key)
    if cached:
        return cached
    try:
        place = _geocode(place_name, _is_french(query))
        if place is None:
            print(f"🌤️ [WEB] Lieu inconnu d'Open-Meteo : « {place_name} »")
            return None
        report = _weather_report(place)
    except Exception as exc:  # noqa: BLE001 - la recherche web prend le relais
        print(f"⚠️ [WEB] Open-Meteo indisponible : {type(exc).__name__}: {str(exc)[:120]}")
        return None
    print(f"🌤️ [WEB] Météo Open-Meteo : {place.get('name')} ({place.get('country', '')})")
    _cache_put(key, report)
    return report


# ─────────────────────────────────────────────────────────────────────────────
# Interface publique
# ─────────────────────────────────────────────────────────────────────────────


class EnhancedInternetSearchEngine:
    """
    Recherche internet : météo, page donnée par son URL, ou moteurs + pages.

    Sans état propre : la pause des moteurs, le cache et la session HTTP sont
    partagés par toutes les instances du module.
    """

    def __init__(self, llm=None):
        """
        Args:
            llm: Ignoré. Conservé pour les appelants qui le passent encore :
                l'ancienne version faisait analyser les pages par le modèle
                avant de lui rendre la main.
        """
        del llm

    def search(self, query: str, read: bool = True) -> SearchResponse:
        """Sources d'une requête, avec les passages des premières pages."""
        response = search_engines(query)
        if read and response.results:
            read_pages(response.results, query)
        return response

    def search_and_summarize(self, query: str) -> str:
        """
        Résultat de l'outil web_search : texte prêt pour le modèle.

        Une requête météo donne la météo, une URL donne le contenu de cette
        page, le reste passe par les moteurs. Ne lève jamais d'exception.
        """
        query = " ".join((query or "").split())
        if not query:
            return "Aucun résultat : requête de recherche vide."
        try:
            return self._answer(query)
        except Exception as exc:  # noqa: BLE001 - l'outil renvoie toujours du texte
            print(f"❌ [WEB] Recherche impossible : {type(exc).__name__}: {exc}")
            return f"Recherche impossible ({type(exc).__name__}). Aucun résultat pour « {query} »."

    def _answer(self, query: str) -> str:
        url = _first_url(query)
        if url:
            return self.summarize_url(url)
        if is_weather_query(query):
            report = weather(query)
            if report:
                return report

        key = f"search:{_fold(query)}"
        cached = _cache_get(key)
        if cached:
            print(f"💾 [WEB] « {query} » : résultat en cache")
            return cached
        response = self.search(query)
        if not response.results:
            return _no_result_message(response)
        text = format_results(response)
        _cache_put(key, text)
        return text

    # Les agents et CustomAIModel l'appellent sous ce nom
    search_best_source_context = search_and_summarize

    def summarize_url(self, url: str) -> str:
        """Contenu principal d'une page donnée par son adresse."""
        key = f"url:{url}"
        cached = _cache_get(key)
        if cached:
            return cached
        try:
            raw, encoding = _fetch_html(url, seconds=12.0)
            title, blocks = page_blocks(raw, encoding)
        except requests.HTTPError as exc:
            status = exc.response.status_code if exc.response is not None else "?"
            return f"Page illisible (erreur HTTP {status}) : {url}"
        except Exception as exc:  # noqa: BLE001 - l'outil renvoie toujours du texte
            return f"Page illisible ({type(exc).__name__}: {str(exc)[:120]}) : {url}"
        text = select_passages(blocks, [], _URL_PAGE_CHARS)
        if not text:
            return f"Aucun texte lisible sur la page {url} (contenu affiché en JavaScript ?)."
        source = SearchResult(title=title or _domain(url), url=url)
        result = "\n".join([
            f"Contenu de la page « {source.title} » ({_link_target(url)}) :",
            "",
            text,
            "",
            _sources_block([source]),
        ])
        _cache_put(key, result)
        return result


# Ancien nom, encore importé ailleurs
InternetSearchEngine = EnhancedInternetSearchEngine
