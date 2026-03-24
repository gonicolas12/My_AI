"""
Detection automatique de la langue de l'utilisateur et generation
d'instructions pour que le LLM reponde dans la meme langue.
"""

from collections import OrderedDict
from typing import Dict, Optional

from utils.logger import setup_logger

logger = setup_logger(__name__)

# ── Langues supportees ───────────────────────────────────────────────
SUPPORTED_LANGUAGES: Dict[str, str] = {
    "fr": "francais",
    "en": "English",
    "es": "espanol",
    "de": "Deutsch",
    "it": "italiano",
    "pt": "portugues",
    "nl": "Nederlands",
    "ru": "русский",
    "zh": "中文",
    "ja": "日本語",
    "ko": "한국어",
    "ar": "العربية",
}

# ── Instructions systeme par langue ──────────────────────────────────
_SYSTEM_PROMPT_SUFFIXES: Dict[str, str] = {
    "fr": "Reponds toujours en francais.",
    "en": "Always respond in English.",
    "es": "Responde siempre en espanol.",
    "de": "Antworte immer auf Deutsch.",
    "it": "Rispondi sempre in italiano.",
    "pt": "Responda sempre em portugues.",
    "nl": "Antwoord altijd in het Nederlands.",
    "ru": "Всегда отвечай на русском языке.",
    "zh": "请始终用中文回答。",
    "ja": "常に日本語で回答してください。",
    "ko": "항상 한국어로 답변해 주세요.",
    "ar": "أجب دائمًا باللغة العربية.",
}

# ── Tentative d'import de langdetect ─────────────────────────────────
try:
    from langdetect import detect as _langdetect_detect
    from langdetect import DetectorFactory

    # Rend la detection deterministe (meme texte -> meme resultat)
    DetectorFactory.seed = 0
    _HAS_LANGDETECT = True
except ImportError:
    _HAS_LANGDETECT = False
    logger.warning(
        "langdetect n'est pas installe. "
        "La detection de langue utilisera le fallback (langue par defaut)."
    )


class _LRUCache(OrderedDict):
    """Cache LRU minimal pour les detections recentes."""

    def __init__(self, maxsize: int = 128):
        super().__init__()
        self._maxsize = maxsize

    def get_or_none(self, key: str) -> Optional[str]:
        """Retourne la valeur associee a la cle ou None si absente."""
        if key in self:
            self.move_to_end(key)
            return self[key]
        return None

    def put(self, key: str, value: str) -> None:
        """Insere une entree, evicte la plus ancienne si necessaire."""
        if key in self:
            self.move_to_end(key)
        self[key] = value
        if len(self) > self._maxsize:
            self.popitem(last=False)


class LanguageDetector:
    """
    Detecteur de langue pour les messages utilisateur.

    Utilise la bibliotheque langdetect si disponible, sinon
    retombe sur la langue par defaut (francais).
    Les resultats recents sont mis en cache pour assurer la
    coherence au sein d'une meme conversation.
    """

    def __init__(
        self,
        default_language: str = "fr",
        cache_size: int = 128,
        min_text_length: int = 10,
    ):
        """
        Initialise le detecteur de langue.

        Args:
            default_language: Code ISO de la langue par defaut.
            cache_size: Nombre maximal de detections en cache.
            min_text_length: Longueur minimale du texte pour
                tenter la detection (en dessous, retourne la langue
                par defaut).
        """
        self._default = default_language
        self._min_length = min_text_length
        self._cache = _LRUCache(maxsize=cache_size)
        logger.info(
            "LanguageDetector initialise (default=%s, langdetect=%s)",
            default_language,
            "disponible" if _HAS_LANGDETECT else "indisponible",
        )

    # ── API publique ─────────────────────────────────────────────────

    def detect(self, text: str) -> str:
        """
        Detecte la langue d'un texte.

        Args:
            text: Texte utilisateur a analyser.

        Returns:
            Code ISO 639-1 de la langue detectee (ex. 'fr', 'en').
            Retourne la langue par defaut si la detection echoue
            ou si le texte est trop court.
        """
        if not text or not text.strip():
            return self._default

        normalized = text.strip()

        # Verifier le cache
        cached = self._cache.get_or_none(normalized)
        if cached is not None:
            return cached

        # Texte trop court pour une detection fiable
        if len(normalized) < self._min_length:
            logger.debug(
                "Texte trop court (%d car.), langue par defaut utilisee.",
                len(normalized),
            )
            return self._default

        code = self._detect_language(normalized)
        self._cache.put(normalized, code)
        return code

    def get_language_name(self, code: str) -> str:
        """
        Retourne le nom complet de la langue dans cette meme langue.

        Args:
            code: Code ISO 639-1 (ex. 'fr', 'en').

        Returns:
            Nom de la langue (ex. 'francais', 'English').
            Retourne le code tel quel si la langue n'est pas supportee.
        """
        return SUPPORTED_LANGUAGES.get(code, code)

    def get_system_prompt_suffix(self, code: str) -> str:
        """
        Retourne une instruction pour le LLM afin qu'il reponde
        dans la langue indiquee.

        Args:
            code: Code ISO 639-1 de la langue cible.

        Returns:
            Phrase d'instruction a ajouter au prompt systeme.
        """
        return _SYSTEM_PROMPT_SUFFIXES.get(
            code, _SYSTEM_PROMPT_SUFFIXES[self._default]
        )

    @property
    def default_language(self) -> str:
        """Retourne le code de la langue par defaut."""
        return self._default

    @property
    def supported_languages(self) -> Dict[str, str]:
        """Retourne le dictionnaire des langues supportees."""
        return dict(SUPPORTED_LANGUAGES)

    # ── Logique interne ──────────────────────────────────────────────

    def _detect_language(self, text: str) -> str:
        """
        Effectue la detection via langdetect ou retourne le defaut.

        Args:
            text: Texte normalise (non vide, longueur suffisante).

        Returns:
            Code ISO de la langue detectee.
        """
        if not _HAS_LANGDETECT:
            return self._default

        try:
            raw_code = _langdetect_detect(text)
            # langdetect peut renvoyer des variantes (pt-br, zh-cn, etc.)
            code = raw_code.split("-")[0].lower()

            if code in SUPPORTED_LANGUAGES:
                logger.debug("Langue detectee : %s (%s)", code, text[:40])
                return code

            logger.debug(
                "Langue detectee '%s' non supportee, fallback sur '%s'.",
                code,
                self._default,
            )
            return self._default

        except Exception as exc:
            logger.warning(
                "Erreur lors de la detection de langue : %s. "
                "Utilisation de la langue par defaut '%s'.",
                exc,
                self._default,
            )
            return self._default
