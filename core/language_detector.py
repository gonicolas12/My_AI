"""
Detection automatique de la langue de l'utilisateur et generation
d'instructions pour que le LLM reponde dans la meme langue.

La langue d'un message se lit en trois temps, du plus sur au moins sur :

1. l'ecriture : kana → ja, ideogrammes sans kana → zh, hangul → ko,
   arabe → ar, cyrillique → ru. Un nom en alphabet latin (« OneDrive »,
   « Python ») n'y change rien ;
2. en alphabet latin, les mots-outils et les lettres propres a chaque
   langue (« ¿Qué hay en mi… » → es, « Wer bin ich? » → de) ;
3. langdetect, ramene aux sept langues latines de My_AI.

Seul, langdetect se trompait sur les messages courts : « ¿Qué hay en mi
carpeta OneDrive de tu memoria? » → catalan, « 你记忆里的OneDrive文件夹里有什么？ »
→ norvegien, deux langues hors de My_AI, donc la langue par defaut.
"""

import bisect
import itertools
import re
import threading
import unicodedata
from collections import OrderedDict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

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
    "fr": "Réponds toujours en français.",
    "en": "Always respond in English.",
    "es": "Responde siempre en español.",
    "de": "Antworte immer auf Deutsch.",
    "it": "Rispondi sempre in italiano.",
    "pt": "Responda sempre em português.",
    "nl": "Antwoord altijd in het Nederlands.",
    "ru": "Всегда отвечай на русском языке.",
    "zh": "请始终用中文回答。",
    "ja": "常に日本語で回答してください。",
    "ko": "항상 한국어로 답변해 주세요.",
    "ar": "أجب دائمًا باللغة العربية.",
}

# ── Tentative d'import de langdetect ─────────────────────────────────
try:
    from langdetect import DetectorFactory
    from langdetect import detect_langs as _langdetect_detect_langs
    from langdetect.detector_factory import PROFILES_DIRECTORY as _LANGDETECT_PROFILES

    # Rend la detection deterministe (meme texte -> meme resultat)
    DetectorFactory.seed = 0
    _HAS_LANGDETECT = True
except ImportError:
    _HAS_LANGDETECT = False
    logger.warning(
        "langdetect n'est pas installe. "
        "La detection de langue se limitera a l'ecriture et aux mots-outils."
    )

# ── Ecritures ────────────────────────────────────────────────────────

# Plages Unicode (triees) des ecritures reconnues, apres NFKC ; une lettre
# hors de ces plages est d'une autre ecriture (grec, hebreu, thai…)
_SCRIPT_RANGES: Tuple[Tuple[int, int, str], ...] = (
    (0x0000, 0x024F, "latin"),  # ASCII, Latin-1, Latin etendu A et B
    (0x0400, 0x052F, "cyrillic"),
    (0x0600, 0x06FF, "arabic"),
    (0x0750, 0x077F, "arabic"),
    (0x08A0, 0x08FF, "arabic"),
    (0x1100, 0x11FF, "hangul"),
    (0x1E00, 0x1EFF, "latin"),  # Latin etendu additionnel (vietnamien)
    (0x3005, 0x3007, "han"),  # 々 〆 〇
    (0x3040, 0x30FF, "kana"),  # hiragana, katakana
    (0x3130, 0x318F, "hangul"),
    (0x31F0, 0x31FF, "kana"),
    (0x3400, 0x4DBF, "han"),
    (0x4E00, 0x9FFF, "han"),
    (0xA960, 0xA97F, "hangul"),
    (0xAC00, 0xD7FF, "hangul"),
    (0xF900, 0xFAFF, "han"),
    (0x20000, 0x3134F, "han"),
)
_SCRIPT_STARTS = [start for start, _end, _script in _SCRIPT_RANGES]

# Lettres de l'alphabet russe et de l'alphabet arabe : une autre lettre de
# la meme ecriture est celle d'une langue hors de My_AI (ukrainien « ї »,
# serbe « ђ », persan « پ », ourdou « ے »…)
_RUSSIAN_RE = re.compile(r"[а-яё]+")
_ARABIC_RE = re.compile(r"[\u0621-\u063a\u0640-\u064a\u0671]+")

# Lettres latines des sept langues latines de My_AI ; les autres (polonais
# « ł », turc « ğ », suedois « å », vietnamien « ơ »…) sont d'autres langues
_LATIN_ALPHABET = frozenset("abcdefghijklmnopqrstuvwxyzàáâãäçèéêëìíîïñòóôõöùúûüÿœßªº")

# Caracteres par mot : un ideogramme chinois vaut un peu moins d'un mot,
# le japonais ajoute ses kana (particules, terminaisons)
_CHINESE_CHARS_PER_WORD = 1.5
_JAPANESE_CHARS_PER_WORD = 2.0

_LETTERS_RE = re.compile(r"[^\W\d_]+")


def _script(char: str) -> str:
    """Ecriture d'une lettre : latin, cyrillic, arabic, han, kana, hangul ou other."""
    code = ord(char)
    index = bisect.bisect_right(_SCRIPT_STARTS, code) - 1
    if index >= 0 and code <= _SCRIPT_RANGES[index][1]:
        return _SCRIPT_RANGES[index][2]
    return "other"


@dataclass
class _Writing:
    """Lettres et mots de chaque ecriture d'un texte."""

    letters: Dict[str, int] = field(default_factory=dict)
    words: Dict[str, int] = field(default_factory=dict)
    non_russian: bool = False  # cyrillique hors de l'alphabet russe
    non_arabic: bool = False  # ecriture arabe hors de l'alphabet arabe
    non_latin_alphabet: bool = False  # lettre latine hors des langues de My_AI


def _writing(text: str) -> _Writing:
    """Lettres et mots (suites de lettres) de chaque ecriture d'un texte en minuscules."""
    writing = _Writing()
    for match in _LETTERS_RE.finditer(text):
        for script, group in itertools.groupby(match.group(), key=_script):
            run = "".join(group)
            writing.letters[script] = writing.letters.get(script, 0) + len(run)
            # Lettre isolee d'une autre ecriture : un symbole (π, α), pas un mot
            if script != "other" or len(run) > 1:
                writing.words[script] = writing.words.get(script, 0) + 1
            if script == "latin" and not _LATIN_ALPHABET.issuperset(run):
                writing.non_latin_alphabet = True
            elif script == "cyrillic" and not _RUSSIAN_RE.fullmatch(run):
                writing.non_russian = True
            elif script == "arabic" and not _ARABIC_RE.fullmatch(run):
                writing.non_arabic = True
    return writing


def _foreign_writing(writing: _Writing) -> Tuple[float, Optional[str]]:
    """
    Ecriture non latine dominante : (son poids en mots, sa langue), la
    langue valant None hors de My_AI (ukrainien, persan, grec…).
    """
    han = writing.letters.get("han", 0)
    kana = writing.letters.get("kana", 0)
    candidates: List[Tuple[float, Optional[str]]] = [
        (han / _CHINESE_CHARS_PER_WORD, "zh"),
        (writing.words.get("hangul", 0), "ko"),
        (writing.words.get("cyrillic", 0), None if writing.non_russian else "ru"),
        (writing.words.get("arabic", 0), None if writing.non_arabic else "ar"),
        (writing.words.get("other", 0), None),
    ]
    if kana:
        # Les kana n'existent qu'en japonais, avec ou sans ideogrammes
        candidates[0] = ((han + kana) / _JAPANESE_CHARS_PER_WORD, "ja")
    return max(candidates, key=lambda candidate: candidate[0])


# ── Mots-outils des langues latines ──────────────────────────────────

# Mots les plus courants de chaque langue latine (articles, pronoms,
# prepositions, auxiliaires, mots interrogatifs, formules de politesse,
# demandes usuelles) : un message court en contient presque toujours,
# quand langdetect n'a pas assez de lettres pour juger. Un mot commun a
# plusieurs langues (« de », « me ») compte pour chacune, a parts egales.
_FUNCTION_WORDS: Dict[str, str] = {
    "fr": """
        le la les l' un une des du de d' au aux ce cet cette ces c' ça ca cela ceci
        mon ma mes ton ta tes son sa ses notre votre nos vos leur leurs
        quel quelle quels quelles qui que qu' quoi dont où ou
        je j' tu il elle on nous vous ils elles me m' te t' se s' moi toi lui eux y en
        à dans sur sous avec sans pour par chez vers entre depuis pendant avant après contre
        et mais donc car ni si comme quand comment pourquoi combien
        ne n' pas plus très bien aussi encore déjà toujours jamais peu beaucoup trop
        ici là oui non voici voilà
        est es suis sont sommes êtes était étais sera serait a ai as avons avez ont avait avais
        peux peut pouvez pourrais pourrait veux veut voulez voudrais fais fait faites faire
        dois doit devez sais sait savez va vais vas allez aller dire dis dit
        bonjour bonsoir salut coucou merci svp stp plaît plait désolé
        quelque quelques chose rien tout tous toute toutes autre autres même parce
        aujourd'hui demain hier explique résume traduis écris donne montre aide cherche ouvre
        maintenant alors puis ensuite chaque ainsi cependant seulement vraiment être avoir
        personne aucun aucune
    """,
    "en": """
        the a an this that these those my your his her its our their
        i me you he him she it we us they them myself yourself
        what who whom whose which where when why how
        is are am was were be been being do does did done don't doesn't didn't
        have has had can can't cannot could couldn't would wouldn't should shouldn't
        will won't shall may might must
        not no yes of to in on at for with from by about into over under after before
        between through without and or but if so than then there here also just only
        very too again still please thanks thank hello hi hey sorry good morning evening
        night today tomorrow yesterday some any all every each more most much many other
        it's i'm i've i'll i'd you're you've we're they're that's what's there's here's
        let's who's how's where's isn't aren't wasn't
        tell show give explain write make help find open translate summarize summarise list let
        per one come now such because while until since already always never ever nothing
        something someone anything everything really maybe
    """,
    "es": """
        el la los las lo un una unos unas al del de en a con sin por para sobre entre hasta
        desde hacia contra y e o u pero porque que qué quien quién quienes cual cuál cuales
        como cómo donde dónde cuando cuándo cuanto cuánto cuánta cuántos cuántas
        mi mis tu tus su sus nuestro nuestra nuestros nuestras este esta esto estos estas
        ese esa eso esos esas aquel aquella
        yo tú él ella usted nosotros nosotras vosotros ellos ellas ustedes
        me te se nos os le les
        es son soy eres somos está están estás estoy estamos era fue ser estar
        hay ha he has han hemos había tengo tiene tienes tienen puedes puede puedo pueden
        quiero quieres quiere hace hacer haz hago
        no sí si muy más mas también tambien ya todo toda todos todas nada algo aquí aqui allí
        hola gracias buenos buenas días dias dia noches tardes favor perdón adiós bien hoy
        mañana ayer dime dame cuéntame explícame ayúdame escribe muestra abre busca traduce
        resume dos va van vamos ti solo ni ahora entonces después otro otra otros otras mismo
        misma cada mucho mucha muchos muchas poco nunca siempre ningún ninguna nadie aún
        todavía sólo luego sea así algún alguna alguien sino pues aunque mientras tan tanto
    """,
    "de": """
        der die das den dem des ein eine einen einem einer eines kein keine keinen
        mein meine meinen meinem meiner dein deine deinen deinem deiner sein seine ihr ihre
        unser unsere euer ich du er sie es wir mich dich sich mir dir ihm ihn uns euch ihnen
        was wer wen wem wie wo wann warum wieso weshalb welche welcher welches woher wohin
        ist sind bin bist seid war waren wäre habe hast hat haben habt hatte hätte
        kann kannst können könnte will willst wollen möchte muss musst müssen soll sollst
        darf wird werden würde mache machst macht machen gibt gib
        nicht nein ja auch noch schon nur sehr mehr viel viele vielen immer hier dort da dann
        und oder aber denn wenn weil dass ob als so also
        in im an am auf aus bei beim mit nach von vom vor zu zum zur über unter für ohne
        gegen durch um bis
        hallo hey danke dank bitte guten morgen tag abend tschüss entschuldigung heute gestern
        erkläre erklär zeig zeige schreib schreibe hilf öffne übersetze erzähl fasse
        etwas nichts alles alle diese dieser dieses diesen diesem
        jetzt andere anderen jeder jede jedes selbst niemand jemand wirklich vielleicht doch
        sondern obwohl während
    """,
    "it": """
        il lo la i gli le un uno una un' l' del dello della dei degli delle dell'
        al allo alla ai agli alle all' dal dallo dalla dai dagli dalle dall'
        nel nello nella nei negli nelle nell' sul sullo sulla sui sugli sulle sull'
        di a da in con su per tra fra e ed o ma che chi cosa cos' quale quali come dove dov'
        quando quanto quanta quanti quante perché perchè perche
        mio mia miei mie tuo tua tuoi tue suo sua suoi sue nostro nostra
        questo questa questi queste quest' quello quella quelli quelle
        io tu lui lei noi voi loro mi ti si ci vi ne c' d'
        è sono sei siamo siete era ero essere ho hai ha abbiamo avete hanno avere
        puoi può puo posso possiamo voglio vuoi vuole fai fa faccio fare
        non sì no molto più piu anche già ancora sempre mai tutto tutti tutta niente
        qualcosa qui qua lì solo
        ciao grazie buongiorno buonasera salve prego scusa favore bene oggi domani ieri
        dimmi spiegami mostrami aiutami scrivi raccontami elenca apri cerca traduci riassumi
        ora allora dopo altro altra altri stesso stessa ogni poco nessuno nessuna così
        qualche qualcuno però mentre tanto né
    """,
    "pt": """
        o a os as um uma uns umas do da dos das no na nos nas ao aos à às
        pelo pela pelos pelas num numa de em com sem por para sobre entre até desde contra
        e ou mas porque porquê que quê quem qual quais como onde quando quanto quanta
        quantos quantas meu minha meus minhas teu tua teus tuas seu sua seus suas
        nosso nossa este esta estes estas isto esse essa esses essas isso
        aquele aquela aquilo eu tu você voce vocês ele ela eles elas nós me te se lhe lhes
        é são sou és somos está estão estou estás estamos era foi ser estar
        há tem tenho têm temos tinha pode posso podes podem quero quer queres
        faz fazer faço não nao sim muito muita muitos muitas mais também tambem já
        tudo todo toda todos todas nada algo aqui ali dois
        olá ola oi obrigado obrigada bom boa dia dias noite tarde favor desculpe tchau bem
        hoje amanhã ontem diga conte explique ajude escreva mostre abra procure traduza resuma
        agora então depois outro outra outros outras mesmo mesma cada pouco nunca sempre
        nenhum nenhuma ninguém ainda só seja assim algum alguma alguém porém embora enquanto
        tão tanto nem
    """,
    "nl": """
        de het een deze dit die dat mijn jouw je uw zijn haar ons onze hun
        ik jij hij zij ze wij we jullie u mij me hem
        wie wat waar wanneer waarom hoe welke welk
        is ben bent was waren heb hebt heeft hebben had kan kun kunt kunnen wil wilt willen
        moet moeten mag zal zou zullen word wordt worden doe doet
        niet geen nee ja ook nog al maar alleen heel erg veel meer hier daar er
        en of want als dan omdat in op aan bij met naar van voor uit over onder door om tot
        te zonder
        hallo hoi hey dank bedankt alsjeblieft alstublieft goedemorgen goedemiddag
        goedenavond goed dag vandaag morgen gisteren wel toch iets niets alles
        leg vertel schrijf toon laat help zoek vertaal geef maak open
        nu andere elke ieder zelf altijd nooit niemand iemand echt misschien hoewel terwijl
    """,
}

# Signes propres a une langue latine de My_AI
_SIGN_HINTS: Dict[str, str] = {"¿": "es", "¡": "es", "ß": "de"}

# Lettres accentuees propres a une ou quelques langues latines de My_AI.
# Elles comptent pour moitie : on les trouve aussi dans d'autres langues
# (« ä » finnois, « à » catalan) et dans les noms propres (« Müller »).
_LETTER_HINTS: Dict[str, str] = {
    "ñ": "es",
    "ä": "de", "ö": "de", "ü": "de",
    "ã": "pt", "õ": "pt",
    "œ": "fr", "î": "fr", "û": "fr", "ÿ": "fr",
    "ì": "it", "ò": "it",
    "ë": "fr nl", "ï": "fr nl",
    "ç": "fr pt", "â": "fr pt", "ê": "fr pt", "ô": "fr pt",
    "è": "fr it", "ù": "fr it",
    "à": "fr it pt",
    "á": "es pt", "í": "es pt", "ó": "es pt", "ú": "es pt",
}
_LETTER_HINT_WEIGHT = 0.5


def _shared_weights(
    languages_of: Dict[str, List[str]], weight: float = 1.0
) -> Dict[str, Dict[str, float]]:
    """
    Poids de chaque mot ou lettre : `weight` s'il est d'une seule langue,
    partage a parts egales s'il est a plusieurs (« de » : fr, es, pt, nl).
    """
    return {
        key: {lang: weight / len(languages) for lang in languages}
        for key, languages in languages_of.items()
    }


def _languages_of_words() -> Dict[str, List[str]]:
    """Langues de chaque mot-outil (« de » : fr, es, pt, nl)."""
    languages_of: Dict[str, List[str]] = {}
    for lang, words in _FUNCTION_WORDS.items():
        for word in dict.fromkeys(words.split()):
            languages_of.setdefault(word, []).append(lang)
    return languages_of


_WORD_WEIGHTS = _shared_weights(_languages_of_words())
_LETTER_WEIGHTS = {
    **_shared_weights({sign: [lang] for sign, lang in _SIGN_HINTS.items()}),
    **_shared_weights(
        {letter: languages.split() for letter, languages in _LETTER_HINTS.items()},
        _LETTER_HINT_WEIGHT,
    ),
}

# Un mot, eventuellement elide ou contracte (« c'est », « dov'è », « don't »)
_WORD_RE = re.compile(r"[^\W\d_]+(?:'[^\W\d_]+)*'?")


def _latin_scores(text: str) -> Dict[str, float]:
    """Score de chaque langue latine : ses mots-outils et ses lettres propres."""
    scores: Dict[str, float] = {}

    def add(weights: Dict[str, float]) -> None:
        for lang, weight in weights.items():
            scores[lang] = scores.get(lang, 0.0) + weight

    for token in _WORD_RE.findall(text):
        if token in _WORD_WEIGHTS:
            add(_WORD_WEIGHTS[token])
            continue
        # Elision : « c'est » → « c' » + « est », « dov'è » → « dov' » + « è »
        *heads, tail = token.split("'")
        for piece in [head + "'" for head in heads] + [tail]:
            if piece in _WORD_WEIGHTS:
                add(_WORD_WEIGHTS[piece])
    for letter in set(text) & _LETTER_WEIGHTS.keys():
        add(_LETTER_WEIGHTS[letter])
    return scores


# ── langdetect ───────────────────────────────────────────────────────

_LATIN_LANGUAGES = ("fr", "en", "es", "de", "it", "pt", "nl")

# Lettres a partir desquelles langdetect est fiable. En dessous, il se
# trompe souvent avec assurance (« Lista mis documentos » → portugais a
# 100 %, « How are you today? » → somali) : son avis pese moins que les
# mots-outils, et une langue hors de My_AI doit etre confirmee.
_LANGDETECT_RELIABLE_LETTERS = 20

# Poids de l'avis de langdetect (probabilite de 0 a 1), face aux mots-outils
# (1 par mot propre a une langue)
_LANGDETECT_WEIGHT = 1.0

# Langue hors de My_AI (polonais, turc…) : la langue par defaut, si
# langdetect en est sur et que le texte le confirme (assez long, sans mot
# propre a une langue de My_AI, ou avec une lettre d'une autre langue :
# « ł », « ğ », « å »)
_UNSUPPORTED_MIN_PROB = 0.9
# Sauf le catalan et l'afrikaans, que langdetect voit dans des messages
# espagnols (« ¿Qué hay en mi carpeta…? »), neerlandais ou allemands
# (« Vielen Dank! »). Les compter comme l'espagnol ou le neerlandais
# trompait plus souvent qu'autrement (portugais, italien, allemand).
_RELATED_LANGUAGES = frozenset({"ca", "af"})

_LATIN_FACTORY: Dict[str, "DetectorFactory"] = {}
_LATIN_FACTORY_LOCK = threading.Lock()


def _latin_probabilities(text: str) -> Dict[str, float]:
    """Probabilites de langdetect, limite aux langues latines de My_AI."""
    with _LATIN_FACTORY_LOCK:
        factory = _LATIN_FACTORY.get("factory")
        if factory is None:
            factory = DetectorFactory()
            factory.set_seed(0)
            factory.load_json_profile([
                (Path(_LANGDETECT_PROFILES) / code).read_text(encoding="utf-8")
                for code in _LATIN_LANGUAGES
            ])
            _LATIN_FACTORY["factory"] = factory
    detector = factory.create()
    detector.append(text)
    return {result.lang: result.prob for result in detector.get_probabilities()}


def _langdetect_top(text: str) -> Tuple[str, float]:
    """Langue la plus probable selon langdetect (toutes ses langues) et sa probabilite."""
    top = _langdetect_detect_langs(text)[0]
    # langdetect peut renvoyer des variantes (zh-cn, zh-tw)
    return top.lang.split("-")[0].lower(), top.prob


# ── Texte analyse ────────────────────────────────────────────────────

_CODE_RE = re.compile(r"```.*?(?:```|$)|`[^`\n]*`", re.S)
# Liens, adresses, chemins (« C:\Users\… », « /home/… ») : ni mots ni langue.
# Une seule barre est un choix (« et/ou », « valido/i »), elle reste. Les
# motifs ne partent que d'un debut de mot (?<!\S) : partis de chaque lettre,
# ils prenaient des centaines de millisecondes sur un long texte chinois,
# sans espace.
_LINK_RE = re.compile(
    r"(?:https?://|www\.)\S+"
    r"|[A-Za-z]:[\\/]\S*"
    r"|(?<!\S)[^\s@]+@\S+"
    r"|(?<!\S)\S*[\\/]\S*[\\/]\S*"
)
# Identifiants (« my_ai », « qwen3 », « x86 ») : « my_ai » comptait comme
# le mot anglais « my » dans un message russe ou coreen
_IDENTIFIER_RE = re.compile(
    r"(?<![A-Za-z0-9_])(?:[A-Za-z0-9]+(?:_[A-Za-z0-9]+)+"
    r"|[A-Za-z]+[0-9][A-Za-z0-9]*|[0-9]+[A-Za-z][A-Za-z0-9]*)"
)
# Passage cite, souvent dans une autre langue (« Traduis "Good morning" »)
_QUOTED_RE = re.compile(r"«[^»]*»|\"[^\"]*\"|“[^”]*”|„[^“”]*[“”]|「[^」]*」|『[^』]*』")
_MAX_ANALYZED_CHARS = 10000  # comme langdetect


def _analyzed_text(text: str) -> str:
    """
    Texte a analyser (NFKC), sans code, liens, identifiants ni citations.
    La casse reste : langdetect se trompe plus souvent sur un texte en
    minuscules (allemand, anglais).
    """
    sample = unicodedata.normalize("NFKC", text[:_MAX_ANALYZED_CHARS]).replace("’", "'")
    sample = _IDENTIFIER_RE.sub(" ", _LINK_RE.sub(" ", _CODE_RE.sub(" ", sample)))
    unquoted = _QUOTED_RE.sub(" ", sample)
    # Une citation seule reste le message
    return unquoted if _LETTERS_RE.search(unquoted) else sample


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

    Lit l'ecriture, puis les mots-outils des langues latines, puis l'avis
    de langdetect s'il est installe ; un message sans indice sur sa langue
    (« ok ») ou dans une langue hors de My_AI prend la langue par defaut.
    Les resultats recents sont mis en cache pour assurer la coherence au
    sein d'une meme conversation.
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
            min_text_length: Nombre minimal de lettres latines pour
                demander l'avis de langdetect (en dessous, l'ecriture et
                les mots-outils decident seuls).
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
            Retourne la langue par defaut si le texte ne dit rien de sa
            langue (« ok ») ou s'il est dans une langue non prise en charge.
        """
        if not text or not text.strip():
            return self._default

        normalized = text.strip()

        # Verifier le cache
        cached = self._cache.get_or_none(normalized)
        if cached is not None:
            return cached

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

    def set_default_language(self, code: str) -> None:
        """
        Change la langue par defaut (Reglages), sans redemarrage.

        Le cache est vide : un texte dans une langue non prise en charge y
        gardait l'ancienne langue par defaut.
        """
        if code not in SUPPORTED_LANGUAGES or code == self._default:
            return
        self._default = code
        self._cache.clear()
        logger.info("Langue par defaut : %s", code)

    @property
    def supported_languages(self) -> Dict[str, str]:
        """Retourne le dictionnaire des langues supportees."""
        return dict(SUPPORTED_LANGUAGES)

    # ── Logique interne ──────────────────────────────────────────────

    def _detect_language(self, text: str) -> str:
        """
        Langue d'un texte : son ecriture, puis ses mots-outils et langdetect.

        Args:
            text: Texte normalise (non vide).

        Returns:
            Code ISO de la langue detectee.
        """
        try:
            sample = _analyzed_text(text)
            lowered = sample.lower()
            writing = _writing(lowered)
            scores = _latin_scores(lowered)
            latin_words = writing.words.get("latin", 0)
            units, language = _foreign_writing(writing)
            # Une autre ecriture l'emporte sur l'alphabet latin, sauf face a
            # une vraie phrase plus longue (« What does 你好 mean? ») : les
            # mots latins d'un message chinois ou russe sont des noms
            # (« OneDrive », « Docker Compose »), sans mot-outil
            if units and (units > latin_words or max(scores.values(), default=0.0) < 1):
                code = language or self._default
            elif latin_words:
                code = self._latin_language(sample, scores, writing)
            else:
                code = self._default  # ni lettre ni mot : chiffres, emojis…
            logger.debug("Langue detectee : %s (%s)", code, text[:40])
            return code
        except Exception as exc:
            logger.warning(
                "Erreur lors de la detection de langue : %s. "
                "Utilisation de la langue par defaut '%s'.",
                exc,
                self._default,
            )
            return self._default

    def _latin_language(self, text: str, scores: Dict[str, float], writing: _Writing) -> str:
        """
        Langue d'un texte en alphabet latin : ses mots-outils, puis l'avis
        de langdetect quand le texte est assez long pour qu'il en ait un.
        """
        letters = writing.letters["latin"]
        if _HAS_LANGDETECT and letters >= self._min_length:
            try:
                code, prob = _langdetect_top(text)
                probabilities = _latin_probabilities(text)
            except Exception as exc:  # pylint: disable=broad-except
                # « No features in text » : les mots-outils decident seuls
                logger.debug("langdetect sans avis : %s", exc)
            else:
                if (code not in SUPPORTED_LANGUAGES and code not in _RELATED_LANGUAGES
                        and prob >= _UNSUPPORTED_MIN_PROB
                        and (letters >= _LANGDETECT_RELIABLE_LETTERS
                             or writing.non_latin_alphabet
                             or max(scores.values(), default=0.0) < 1)):
                    logger.debug("Langue '%s' non supportee, langue par defaut.", code)
                    return self._default
                if not scores:
                    # Aucun mot-outil : l'avis de langdetect seul, comme avant
                    return code if code in _LATIN_LANGUAGES else self._default
                weight = _LANGDETECT_WEIGHT * min(1.0, letters / _LANGDETECT_RELIABLE_LETTERS)
                for lang, probability in probabilities.items():
                    scores[lang] = scores.get(lang, 0.0) + weight * probability
        if not scores:
            return self._default
        best = max(scores.values())
        winners = [lang for lang, score in scores.items() if best - score < 1e-9]
        # Egalite (« Hallo » : allemand ou neerlandais) : la langue par defaut
        return winners[0] if len(winners) == 1 else self._default


# ── Langue de reponse hors du moteur (agents) ────────────────────────

_SHARED: Dict[str, LanguageDetector] = {}
_SHARED_LOCK = threading.Lock()


def _shared_detector(default: str) -> LanguageDetector:
    """Detecteur commun aux agents, a la langue par defaut des Reglages."""
    with _SHARED_LOCK:
        detector = _SHARED.get("detector")
        if detector is None:
            detector = LanguageDetector(default_language=default)
            _SHARED["detector"] = detector
        else:
            detector.set_default_language(default)
        return detector


def reply_language(text: str, language: Optional[str] = None) -> str:
    """
    Langue de la reponse a un texte : `language` si l'appelant la connait,
    sinon celle du texte, sinon (texte sans indice ou ambigu) la langue par
    defaut choisie dans les Reglages.
    """
    if language in SUPPORTED_LANGUAGES:
        return language
    from core.i18n import current_language  # pylint: disable=import-outside-toplevel
    return _shared_detector(current_language()).detect(text or "")


def reply_instruction(text: str, language: Optional[str] = None) -> str:
    """Consigne « reponds en … » pour le modele (« Always respond in English. »)."""
    return _SYSTEM_PROMPT_SUFFIXES[reply_language(text, language)]
