"""
Langue de My_AI : celle de l'interface et la langue par défaut des réponses
du modèle (language.default de config.yaml).

Les messages que le serveur envoie à l'interface (étapes du lancement,
notifications, erreurs, libellés des outils, agents, tâches planifiées, page
mobile du Relay…) passent par tr() : un catalogue JSON par langue
(core/locales/), clé à points → texte avec ses {paramètres}, et pour un
nombre ({count}) ses formes du pluriel (one, few, many, other…, règles CLDR).
Une clé absente d'une langue est prise en anglais, puis en français, la
langue source. Les consignes données au modèle et les journaux restent en
français.

La langue en cours est lue une fois dans config.yaml, puis changée à chaud
par set_language() (Réglages, assistant de premier lancement) : aucun
redémarrage. Au tout premier lancement de la fenêtre, la langue du système
est prise si My_AI la parle, l'anglais sinon (system_language).
"""

import ctypes
import json
import locale
import os
import re
import sys
import threading
from pathlib import Path
from typing import Any, Dict, Mapping, Optional

from utils.logger import setup_logger

logger = setup_logger(__name__)

# Langues proposées, nommées dans leur propre langue (language.supported de config.yaml)
LANGUAGE_NAMES: Dict[str, str] = {
    "fr": "Français",
    "en": "English",
    "es": "Español",
    "de": "Deutsch",
    "it": "Italiano",
    "pt": "Português",
    "nl": "Nederlands",
    "ru": "Русский",
    "zh": "中文",
    "ja": "日本語",
    "ko": "한국어",
    "ar": "العربية",
}

SUPPORTED_LANGUAGES = tuple(LANGUAGE_NAMES)

# Langue source des catalogues, et langue d'un réglage illisible
SOURCE_LANGUAGE = "fr"

# Langue d'un système dont My_AI ne parle pas la langue (premier lancement)
FALLBACK_LANGUAGE = "en"

# Écriture de droite à gauche
RTL_LANGUAGES = frozenset({"ar"})

LOCALES_DIR = Path(__file__).resolve().parent / "locales"

_PLACEHOLDER = re.compile(r"\{(\w+)\}")

_LOCK = threading.Lock()
# Langue en cours (None : pas encore lue dans config.yaml) et catalogues lus
_STATE: Dict[str, Optional[str]] = {"language": None}
_CATALOGS: Dict[str, Dict[str, Any]] = {}


def normalize(code: Any) -> Optional[str]:
    """« en-US », « pt_BR », « FR » → code pris en charge, ou None."""
    if not isinstance(code, str):
        return None
    base = code.strip().replace("_", "-").split("-")[0].lower()
    return base if base in LANGUAGE_NAMES else None


def _config_language() -> str:
    """language.default de config.yaml (le français s'il est illisible)."""
    try:
        from core.config import get_config  # pylint: disable=import-outside-toplevel
        return normalize(get_config().get("language.default", SOURCE_LANGUAGE)) or SOURCE_LANGUAGE
    except Exception:  # pylint: disable=broad-except
        return SOURCE_LANGUAGE


def current_language() -> str:
    """Langue de l'interface et des réponses par défaut du modèle."""
    language = _STATE["language"]
    if language is None:
        with _LOCK:
            language = _STATE["language"] or _config_language()
            _STATE["language"] = language
    return language


def set_language(code: str) -> str:
    """Langue en cours, changée à chaud (le réglage est écrit par l'appelant)."""
    language = normalize(code)
    if language is None:
        raise ValueError(f"Langue non prise en charge : {code}")
    with _LOCK:
        _STATE["language"] = language
    return language


def is_rtl(code: Optional[str] = None) -> bool:
    """Écriture de droite à gauche (arabe)."""
    return (code or current_language()) in RTL_LANGUAGES


def language_name(code: str) -> str:
    """Nom d'une langue dans cette langue (« English », « Español »)."""
    return LANGUAGE_NAMES.get(code, code)


def _load(code: str) -> Dict[str, Any]:
    """Catalogue d'une langue ({} s'il manque ou s'il est illisible)."""
    data = _CATALOGS.get(code)
    if data is not None:
        return data
    path = LOCALES_DIR / f"{code}.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("catalogue non objet")
    except FileNotFoundError:
        data = {}
    except (OSError, ValueError) as exc:
        logger.warning("Catalogue %s illisible : %s", path.name, exc)
        data = {}
    _CATALOGS[code] = data
    return data


def catalog(code: str) -> Dict[str, Any]:
    """Catalogue d'une langue (lecture seule)."""
    return dict(_load(code))


def _plural_ru(_n: float, i: int) -> str:
    if i % 10 == 1 and i % 100 != 11:
        return "one"
    if 2 <= i % 10 <= 4 and not 12 <= i % 100 <= 14:
        return "few"
    return "many"


def _plural_ar(n: float, i: int) -> str:
    exact = {0: "zero", 1: "one", 2: "two"}
    if n in exact:
        return exact[int(n)]
    if 3 <= i % 100 <= 10:
        return "few"
    return "many" if 11 <= i % 100 <= 99 else "other"


# Règles CLDR des nombres entiers ; chinois, japonais et coréen n'ont qu'une forme
_PLURAL_RULES = {
    "fr": lambda _n, i: "one" if i in (0, 1) else "other",
    "pt": lambda _n, i: "one" if i in (0, 1) else "other",
    "en": lambda n, _i: "one" if n == 1 else "other",
    "de": lambda n, _i: "one" if n == 1 else "other",
    "nl": lambda n, _i: "one" if n == 1 else "other",
    "it": lambda n, _i: "one" if n == 1 else "other",
    "es": lambda n, _i: "one" if n == 1 else "other",
    "ru": _plural_ru,
    "ar": _plural_ar,
}


def plural_category(code: str, count: float) -> str:
    """Forme du pluriel d'un nombre (one, few, many, other…)."""
    rule = _PLURAL_RULES.get(code)
    n = abs(count)
    return rule(n, int(n)) if rule else "other"


def _message(code: str, key: str) -> Optional[Any]:
    for language in (code, FALLBACK_LANGUAGE, SOURCE_LANGUAGE):
        value = _load(language).get(key)
        if value is not None:
            return value
    return None


def tr(key: str, /, *, _lang: Optional[str] = None, **params: Any) -> str:
    """Texte de la clé dans la langue en cours (ou `_lang`), paramètres remplacés.

    `key` est positionnel : un paramètre du message peut s'appeler « key ».
    Une clé inconnue rend la clé elle-même : visible, sans planter l'appelant.
    """
    code = normalize(_lang) or current_language()
    message = _message(code, key)
    if message is None:
        logger.debug("Clé de traduction absente : %s", key)
        return key
    if isinstance(message, Mapping):
        count = params.get("count", 0)
        try:
            number = float(count)
        except (TypeError, ValueError):
            number = 0.0
        text = message.get(plural_category(code, number)) or message.get("other") or ""
    else:
        text = str(message)
    if not params:
        return text
    return _PLACEHOLDER.sub(
        lambda match: str(params[match.group(1)]) if match.group(1) in params else match.group(0),
        text,
    )


def _windows_ui_language() -> Optional[str]:
    """Langue d'affichage de Windows (« fr_FR »), ou None."""
    try:
        langid = ctypes.windll.kernel32.GetUserDefaultUILanguage()  # type: ignore[attr-defined]
    except (AttributeError, OSError):
        return None
    return locale.windows_locale.get(langid)


def system_language() -> str:
    """Langue du système si My_AI la parle, l'anglais sinon (premier lancement)."""
    candidates = []
    if sys.platform == "win32":
        candidates.append(_windows_ui_language())
    for variable in ("LC_ALL", "LC_MESSAGES", "LANG", "LANGUAGE"):
        value = os.environ.get(variable)
        if value:
            candidates.append(value.split(":")[0].split(".")[0])
    try:
        candidates.append(locale.getlocale()[0])
    except (TypeError, ValueError):
        pass
    for candidate in candidates:
        # « C », « POSIX », « French_France » (nom Windows) : la suivante décide
        language = normalize(candidate)
        if language:
            return language
    return FALLBACK_LANGUAGE


def reset_for_tests() -> None:
    """Langue relue au prochain appel et catalogues rechargés (tests)."""
    with _LOCK:
        _STATE["language"] = None
        _CATALOGS.clear()
