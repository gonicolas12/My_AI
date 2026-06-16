"""Voice output (text-to-speech) via pyttsx3 — local & cross-platform.

Symmetric counterpart to ``voice_input.py``. Uses the OS speech engine
(SAPI5 on Windows, NSSpeechSynthesizer on macOS, espeak/espeak-ng on Linux),
so there is no model download and the voice never leaves the machine.

A single dedicated worker thread owns the engine and consumes a queue: this
avoids pyttsx3's cross-thread reentrancy issues (the engine must be created and
driven from one thread). State callbacks are marshalled back to the Tk thread
via ``root.after()`` exactly like the STT side.
"""

from __future__ import annotations

import queue
import re
import threading
from typing import Callable, Optional

try:
    import pyttsx3
    try:
        from pyttsx3.engine import Engine as _PyttsxEngine
    except Exception:
        _PyttsxEngine = None
    _TTS_OK = True
    _TTS_ERR = None
except Exception as _e:  # pragma: no cover - environment-dependent
    _TTS_OK = False
    _TTS_ERR = _e
    _PyttsxEngine = None


def _new_engine():
    """Crée un moteur pyttsx3 NEUF, en contournant le cache de pyttsx3.init().

    pyttsx3.init() met en cache le moteur par driver (WeakValueDictionary) et
    renvoie le même tant qu'une référence reste vivante. Or un moteur SAPI5
    réutilisé ne lit qu'une seule fois (les runAndWait suivants reviennent sans
    audio). On construit donc Engine directement à chaque lecture pour garantir
    qu'une nouvelle lecture fonctionne. Repli sur init() si l'import échoue.
    """
    if _PyttsxEngine is not None:
        return _PyttsxEngine(driverName=None, debug=False)
    return pyttsx3.init()


# ── Nettoyage du texte avant lecture ────────────────────────────────────
# On retire ce qui se lit mal à voix haute : blocs de code, markdown, URLs,
# emojis, pipes de tableaux. Le but est une prose naturelle.
_CODE_FENCE_RE = re.compile(r"```.*?```", re.DOTALL)
_INLINE_CODE_RE = re.compile(r"`([^`]*)`")
_IMG_RE = re.compile(r"!\[([^\]]*)\]\([^)]*\)")
_LINK_RE = re.compile(r"\[([^\]]+)\]\([^)]*\)")
_HEADING_RE = re.compile(r"^\s{0,3}#{1,6}\s*", re.MULTILINE)
_BLOCKQUOTE_RE = re.compile(r"^\s{0,3}>\s?", re.MULTILINE)
_BULLET_RE = re.compile(r"^\s{0,3}[-*+]\s+", re.MULTILINE)
_EMPHASIS_RE = re.compile(r"(\*{1,3}|_{1,3})(.+?)\1", re.DOTALL)
_URL_RE = re.compile(r"https?://\S+")
_EMOJI_RE = re.compile(
    "["
    "\U0001F000-\U0001FAFF"  # pictogrammes, emoji
    "\U00002600-\U000027BF"  # symboles divers, dingbats
    "\U0001F1E6-\U0001F1FF"  # drapeaux régionaux
    "←-⇿"          # flèches
    "⬀-⯿"          # symboles divers / flèches
    "️"                 # variation selector (emoji presentation)
    "]"
)
_MULTISPACE_RE = re.compile(r"[ \t]+")
_MULTINEWLINE_RE = re.compile(r"\n{2,}")

# Indices de correspondance langue → voix SAPI/OS (recherche par sous-chaîne
# dans l'id ou le nom de la voix, en minuscules). Permet d'éviter de lire du
# français avec une voix anglaise quand la voix OS par défaut n'est pas FR.
_LANG_VOICE_HINTS = {
    "fr": ("fr-fr", "fr_fr", "french", "hortense", "julie", "paul"),
    "en": ("en-us", "en-gb", "en_us", "english", "zira", "david", "mark", "hazel"),
    "es": ("es-es", "es-mx", "spanish", "helena", "sabina", "laura", "pablo"),
    "de": ("de-de", "german", "hedda", "katja", "stefan"),
    "it": ("it-it", "italian", "elsa", "cosimo"),
    "pt": ("pt-br", "pt-pt", "portuguese", "maria", "daniel", "helia"),
    "nl": ("nl-nl", "dutch", "frank"),
    "ru": ("ru-ru", "russian", "irina", "pavel"),
    "zh": ("zh-cn", "zh-tw", "chinese", "huihui", "yaoyao", "kangkang"),
    "ja": ("ja-jp", "japanese", "haruka", "ayumi", "ichiro"),
    "ko": ("ko-kr", "korean", "heami"),
    "ar": ("ar-sa", "ar-eg", "arabic", "naayf", "hoda"),
}


def clean_for_speech(text: str) -> str:
    """Strip markdown/code/URLs/emoji so the TTS reads natural prose."""
    if not text:
        return ""
    t = _CODE_FENCE_RE.sub(" ", text)
    t = _IMG_RE.sub(r"\1", t)
    t = _LINK_RE.sub(r"\1", t)
    t = _INLINE_CODE_RE.sub(r"\1", t)
    t = _HEADING_RE.sub("", t)
    t = _BLOCKQUOTE_RE.sub("", t)
    t = _BULLET_RE.sub("", t)
    t = _EMPHASIS_RE.sub(r"\2", t)
    t = _URL_RE.sub(" ", t)
    t = t.replace("|", " ")
    t = _EMOJI_RE.sub("", t)
    t = _MULTISPACE_RE.sub(" ", t)
    t = _MULTINEWLINE_RE.sub("\n", t)
    return t.strip()


class VoiceOutput:
    """Toggle-based text-to-speech.

    speak(text, on_state) -> enqueue text for the worker thread to read
    stop()                -> interrupt current utterance + drain the queue
    toggle(text, ...)     -> stop if speaking, otherwise speak

    on_state(state) is called from the main Tk thread when state changes,
    with state ∈ {"speaking", "idle", "error"}.
    """

    _shared: Optional["VoiceOutput"] = None

    def __init__(self, tk_root=None):
        self.tk_root = tk_root
        self._queue: "queue.Queue[tuple[int, Optional[str]]]" = queue.Queue()
        self._worker: Optional[threading.Thread] = None
        self._engine = None
        self._speaking = False
        self._on_state: Callable[[str], None] = lambda _s: None
        # Compteur de génération : un stop() l'incrémente pour invalider les
        # éléments déjà en file (ils sont ignorés par le worker).
        self._gen = 0
        # Sélection de voix par langue (construite une fois dans le worker)
        self._voice_by_lang: dict = {}
        self._default_voice = None
        self._voice_index_built = False

    # ── Singleton applicatif ────────────────────────────────────────────
    @classmethod
    def get_shared(cls, tk_root=None) -> "VoiceOutput":
        if cls._shared is None:
            cls._shared = cls(tk_root=tk_root)
        elif tk_root is not None and cls._shared.tk_root is None:
            cls._shared.tk_root = tk_root
        return cls._shared

    # ── Disponibilité ───────────────────────────────────────────────────
    @property
    def available(self) -> bool:
        """True si pyttsx3 (et un moteur TTS OS) est utilisable."""
        return _TTS_OK

    def unavailable_reason(self) -> str:
        if not _TTS_OK:
            return f"pyttsx3 indisponible : {_TTS_ERR}"
        return ""

    @property
    def is_speaking(self) -> bool:
        return self._speaking

    # ── API publique ────────────────────────────────────────────────────
    def speak(self, text: str, on_state: Optional[Callable[[str], None]] = None) -> None:
        """Lit `text` à voix haute (enfile pour le worker)."""
        if on_state is not None:
            self._on_state = on_state
        if not _TTS_OK:
            self._emit("error")
            return
        cleaned = clean_for_speech(text)
        if not cleaned:
            return
        if not self._ensure_worker():
            self._emit("error")
            return
        self._queue.put((self._gen, cleaned))

    def stop(self) -> None:
        """Stoppe la lecture en cours et vide la file d'attente."""
        # Invalide tout ce qui est en file
        self._gen += 1
        try:
            while True:
                self._queue.get_nowait()
        except queue.Empty:
            pass
        if self._engine is not None:
            try:
                self._engine.stop()
            except Exception:
                pass
        self._speaking = False
        self._emit("idle")

    def toggle(self, text: str, on_state: Optional[Callable[[str], None]] = None) -> None:
        """Stoppe si une lecture est en cours, sinon lit `text`."""
        if self._speaking:
            self.stop()
        else:
            self.speak(text, on_state)

    # ── Interne ─────────────────────────────────────────────────────────
    def _ensure_worker(self) -> bool:
        if self._worker is not None and self._worker.is_alive():
            return True
        if not _TTS_OK:
            return False
        self._worker = threading.Thread(target=self._run, daemon=True)
        self._worker.start()
        return True

    def _run(self) -> None:
        # Construire l'index de voix une seule fois (moteur jetable).
        if not self._voice_index_built:
            try:
                tmp = _new_engine()
                self._build_voice_index(tmp)
                try:
                    tmp.stop()
                except Exception:
                    pass
                del tmp
                self._voice_index_built = True
            except Exception as e:  # pragma: no cover - environment-dependent
                print(f"⚠️ [TTS] init du moteur échouée : {e}")
                self._emit("error")
                return

        while True:
            gen, text = self._queue.get()
            if text is None:  # sentinelle d'arrêt (non utilisée pour l'instant)
                break
            if gen != self._gen:
                continue  # élément obsolète (un stop() est passé)

            self._speaking = True
            self._emit("speaking")
            try:
                # Moteur NEUF à chaque lecture (cf. _new_engine) : un moteur
                # SAPI5 réutilisé ne parle qu'une fois → fix de la re-lecture.
                engine = _new_engine()
                self._engine = engine
                self._apply_voice_for(engine, text)
                engine.say(text)
                engine.runAndWait()
                try:
                    engine.stop()
                except Exception:
                    pass
            except Exception as e:
                print(f"⚠️ [TTS] lecture échouée : {e}")
                self._emit("error")
            finally:
                self._engine = None
                self._speaking = False
                # Idle seulement si plus rien à lire pour cette génération
                if self._queue.empty() or gen != self._gen:
                    self._emit("idle")

    def _build_voice_index(self, engine) -> None:
        """Construit l'index langue → id de voix à partir des voix installées."""
        try:
            voices = engine.getProperty("voices") or []
        except Exception:
            voices = []
        try:
            self._default_voice = engine.getProperty("voice")
        except Exception:
            self._default_voice = None
        for v in voices:
            hay = f"{getattr(v, 'id', '')} {getattr(v, 'name', '')}".lower()
            for lang, hints in _LANG_VOICE_HINTS.items():
                if lang in self._voice_by_lang:
                    continue
                if any(h in hay for h in hints):
                    self._voice_by_lang[lang] = v.id
        if self._voice_by_lang:
            print(f"🔊 [TTS] voix par langue : {sorted(self._voice_by_lang)}")

    def _apply_voice_for(self, engine, text: str) -> None:
        """Sélectionne, sur ce moteur, une voix correspondant à la langue du texte.

        Le moteur étant recréé à chaque lecture, il repart toujours sur la voix
        par défaut : il suffit donc d'appliquer la voix correspondante si on en
        a une pour la langue détectée.
        """
        lang = self._detect_lang(text)
        if not lang:
            return
        vid = self._voice_by_lang.get(lang)
        if vid:
            try:
                engine.setProperty("voice", vid)
            except Exception:
                pass

    @staticmethod
    def _detect_lang(text: str) -> Optional[str]:
        """Détecte la langue (code ISO court) via langdetect ; None si indispo."""
        sample = text.strip()
        if len(sample) < 8:
            return None
        try:
            from langdetect import detect
            return detect(sample[:500]).split("-")[0].lower()
        except Exception:
            return None

    def _emit(self, state: str) -> None:
        cb = self._on_state
        root = self.tk_root
        if root is not None:
            try:
                root.after(0, lambda s=state: cb(s))
                return
            except Exception:
                pass
        try:
            cb(state)
        except Exception:
            pass
