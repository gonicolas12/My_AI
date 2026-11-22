"""
Gestionnaire de base de connaissances structurée pour My_AI.
Stocke des faits éditables (noms, décisions, préférences, procédures)
extraits des conversations ou ajoutés manuellement.

Chaque fait a une portée : la conversation qui le reçoit d'office dans son
prompt. Les autres le trouvent à la demande (outil search_memory).
"""

import os
import re
import sqlite3
import threading
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

from utils.logger import setup_logger
from utils.text_fold import fold

logger = setup_logger("knowledge_base_manager")

VALID_CATEGORIES = (
    "preference",
    "decision",
    "person",
    "procedure",
    "technical",
    "general",
)

# Portées d'un fait. « chat » : le chat (fenêtre, téléphone), comme tous les
# faits d'avant les portées. « code » : la conversation Code (VS Code, page Code,
# vue Code du téléphone), quel que soit le dossier ouvert. « project » : la
# conversation Code quand ce dossier (colonne project, son chemin) est ouvert
# dans VS Code. Dix conventions de code retenues depuis VS Code chassaient sinon
# du prompt du chat les faits sur l'utilisateur, et ses faits personnels
# finissaient dans les fichiers écrits par le modèle.
SCOPE_CHAT = "chat"
SCOPE_CODE = "code"
SCOPE_PROJECT = "project"
SCOPES = (SCOPE_CHAT, SCOPE_CODE, SCOPE_PROJECT)


def same_project(first: str, second: str) -> bool:
    """Deux chemins désignent-ils le même dossier (casse de Windows, séparateur final) ?"""
    if not first or not second:
        return False
    return (os.path.normcase(os.path.normpath(first))
            == os.path.normcase(os.path.normpath(second)))


def project_name(project: str) -> str:
    """Nom affiché d'un projet : celui de son dossier."""
    path = os.path.normpath(project) if project else ""
    return os.path.basename(path) or path


def _checked_scope(scope: Optional[str], project: Optional[str]) -> Tuple[str, str]:
    """(portée, dossier) d'un fait ; le dossier n'a de sens que pour un projet.

    Raises:
        ValueError: Portée inconnue, ou fait de projet sans son dossier.
    """
    scope = (scope or SCOPE_CHAT).lower().strip()
    if scope not in SCOPES:
        raise ValueError(f"Portée invalide '{scope}'. Portées acceptées : {', '.join(SCOPES)}")
    if scope != SCOPE_PROJECT:
        return scope, ""
    project = str(project or "").strip()
    if not project:
        raise ValueError("Un fait de projet doit nommer son dossier")
    return scope, os.path.normpath(project)


def fact_scope(fact: Dict) -> Tuple[str, str]:
    """(portée, dossier) d'un fait lu en base ; un fait d'avant les portées est du chat."""
    scope = str(fact.get("scope") or SCOPE_CHAT)
    return scope, str(fact.get("project") or "") if scope == SCOPE_PROJECT else ""


def scope_note(fact: Dict) -> str:
    """Portée d'un fait pour le modèle, entre parenthèses après lui ("" pour le chat)."""
    scope, project = fact_scope(fact)
    if scope == SCOPE_CODE:
        return "pour tous ses projets de code"
    if scope == SCOPE_PROJECT:
        return f"pour son projet de code « {project_name(project)} »"
    return ""

_QUERY_STOPWORDS = {
    "qui", "que", "quoi", "quand", "ou", "où", "comment", "pourquoi",
    "est", "es", "suis", "sont", "etre", "être", "a", "au", "aux",
    "le", "la", "les", "un", "une", "des", "de", "du", "d", "et",
    "donc", "or", "ni", "car", "je", "tu", "il", "elle", "on",
    "nous", "vous", "ils", "elles", "mon", "ma", "mes", "ton", "ta",
    "tes", "son", "sa", "ses", "notre", "nos", "votre", "vos", "leur",
    "leurs", "l", "j", "c", "ce", "cet", "cette", "ces",
    "quel", "quelle", "quels", "quelles", "dans", "pour", "avec", "sur",
    "par", "pas", "moi", "toi", "the", "and", "what", "who", "how",
    "you", "your", "are", "was", "this", "that",
}

# Taille maximale d'un fait dans le prompt (le reste est tronqué)
_FACT_DISPLAY_CHARS = 600

# Fait écrit à la première personne, avec les mots de l'utilisateur
# (« je suis Nicolas », « mon chat… », « my car… »)
_FIRST_PERSON_RE = re.compile(
    r"(?<![\w'’])(?:(?:je|me|moi|mon|ma|mes|mien(?:ne)?s?|i|my|mine|myself)\b|[jm]['’])",
    re.IGNORECASE,
)

# ------------------------------------------------------------------
# Fait à la première personne → troisième personne, pour le prompt
# ------------------------------------------------------------------

# « je » / « j' », négation, pronoms compléments, puis le verbe conjugué
_JE_CLAUSE_RE = re.compile(
    r"(?<![\w'’])(?:je\s+|j['’])"
    r"(?P<neg>ne\s+|n['’])?"
    r"(?P<clitics>(?:(?:me|te|se|les|le|la|lui|leur|y|en)\s+|[mtsl]['’])*)"
    r"(?P<verb>[^\W\d_]+)",
    re.IGNORECASE,
)
_CLITIC_RE = re.compile(r"[mtsl]['’]|me|te|se|les|le|la|lui|leur|y|en", re.IGNORECASE)
_ELIDED_CLITICS = {"m": "me", "t": "te", "s": "se", "l": "le"}
_THIRD_PERSON_IRREGULAR = {"suis": "est", "ai": "a", "vais": "va"}
_POSSESSIVE_RE = re.compile(r"(?<![\w'’])(?:mon|ma|mes|mien|mienne|miens|miennes)\b", re.IGNORECASE)
_EMPHATIC_MOI_RE = re.compile(r"(?<![\w'’])moi\s*,\s*(?=j)", re.IGNORECASE)  # « Moi, je… »
_MOI_RE = re.compile(r"(?<![\w'’])moi\b", re.IGNORECASE)
_VOWELS = "aeiouyàâäéèêëîïôöùûüÿh"
_FRENCH_MARKER_RE = re.compile(r"(?<![\w'’])(?:(?:je|mon|ma|mes|moi)\b|j['’])", re.IGNORECASE)
_ENGLISH_MARKER_RE = re.compile(r"(?<![\w'’])(?:I|my|My|mine|myself)(?![\w])|\bI['’]")
# Formes anglaises sûres ; « I like… » reste cité (le verbe n'est pas reconnu)
_ENGLISH_THIRD_PERSON = (
    (re.compile(r"\bI(?:['’]m| am)\b"), "the user is"),
    (re.compile(r"\bI was\b"), "the user was"),
    (re.compile(r"\bI(?:['’]ve| have)\b"), "the user has"),
    (re.compile(r"\bI had\b"), "the user had"),
    (re.compile(r"\bI(?:['’]ll| will)\b"), "the user will"),
    (re.compile(r"\bI (can|could|would|should|must|might|may)\b"), r"the user \1"),
    (re.compile(r"\bI (?:do not|don['’]t)\b"), "the user does not"),
    (re.compile(r"\b[Mm]y\b"), "the user's"),
    (re.compile(r"\bmine\b"), "the user's"),
    (re.compile(r"\bme\b"), "the user"),
)


def _third_person_verb(verb: str) -> Optional[str]:
    """Le verbe conjugué avec « je », au même temps avec « il » (None si inconnu)."""
    lower = verb.lower()
    if lower in _THIRD_PERSON_IRREGULAR:
        return _THIRD_PERSON_IRREGULAR[lower]
    if lower.endswith("ai"):  # futur : serai → sera
        return verb[:-1]
    if lower.endswith(("ds", "ts", "cs")):  # prends → prend, mets → met
        return verb[:-1]
    if lower.endswith(("s", "x")):  # fais → fait, peux → peut, étais → était
        return verb[:-1] + "t"
    if lower.endswith("e"):  # travaille, (m')appelle
        return verb
    return None


def _je_clause_in_third_person(match: re.Match) -> Optional[str]:
    """« je ne m'appelle » → « l'utilisateur ne s'appelle » (None si verbe inconnu)."""
    verb = _third_person_verb(match.group("verb"))
    if verb is None:
        return None
    words = ["ne"] if match.group("neg") else []
    for clitic in _CLITIC_RE.findall(match.group("clitics")):
        word = clitic.lower()
        if word[-1] in "'’":
            word = _ELIDED_CLITICS[word[0]]
        words.append("se" if word == "me" else word)
    words.append(verb)
    clause = ""
    for word, following in zip(words, words[1:] + [""]):
        if following and word in ("ne", "se", "te", "le", "la") and following[0].lower() in _VOWELS:
            clause += word[0] + "'"  # se + est → s'est, ne + est → n'est
        else:
            clause += word + (" " if following else "")
    return "l'utilisateur " + clause


def _french_in_third_person(text: str) -> Optional[str]:
    failed = False

    def convert(match: re.Match) -> str:
        nonlocal failed
        clause = _je_clause_in_third_person(match)
        if clause is None:
            failed = True
            return match.group(0)
        return clause

    text = _JE_CLAUSE_RE.sub(convert, _EMPHATIC_MOI_RE.sub("", text))
    if failed:
        return None
    # mon → son, Ma → Sa, mien → sien…
    text = _POSSESSIVE_RE.sub(
        lambda m: ("S" if m.group(0)[0] == "M" else "s") + m.group(0)[1:], text
    )
    return _MOI_RE.sub("l'utilisateur", text)


def user_fact_for_prompt(text: str) -> str:
    """
    Un fait tel que le modèle doit le lire, à la troisième personne s'il est
    écrit à la première : « je m'appelle Nicolas » → « L'utilisateur s'appelle
    Nicolas », « mon chat… » → « L'utilisateur : son chat… ». Si une forme
    n'est pas reconnue, le fait est cité comme les mots de l'utilisateur.

    Même cité, un fait laissé à la première personne était parfois recopié
    tel quel : « qui suis-je ? » → « Je m'appelle Nicolas ».
    """
    if not _FIRST_PERSON_RE.search(text):
        return text
    english = bool(_ENGLISH_MARKER_RE.search(text)) and not _FRENCH_MARKER_RE.search(text)
    if english:
        converted = text
        for pattern, replacement in _ENGLISH_THIRD_PERSON:
            converted = pattern.sub(replacement, converted)
    else:
        converted = _french_in_third_person(text)
    if converted is None or _FIRST_PERSON_RE.search(converted):
        return f"L'utilisateur t'a dit : « {text} »"
    subject = "the user" if english else "l'utilisateur"
    if subject not in converted.lower():
        if re.match(r"S(?:on|a|es|ien(?:ne)?s?)\b", converted):  # « Mon chat » devenu « Son chat »
            converted = "s" + converted[1:]
        converted = ("The user: " if english else "L'utilisateur : ") + converted
    return converted[:1].upper() + converted[1:]


# Sujet de la phrase : « tu » (l'IA) ou « je » (l'utilisateur), qui vient en premier
_YOU_SUBJECT_RE = re.compile(r"(?<![\w'’])(?:tu|you)\b", re.IGNORECASE)
_I_SUBJECT_RE = re.compile(r"(?i:(?<![\w'’])(?:je\b|j['’]))|(?<![\w'’])I\b")
# Sans sujet : « ton nom est Jarvis », « your name is Jarvis »
_YOUR_RE = re.compile(r"(?<![\w'’])(?:ton|ta|tes|toi|tien(?:ne)?s?|your|yours)\b", re.IGNORECASE)


def is_assistant_fact(text: str) -> bool:
    """
    Le fait parle-t-il de l'IA plutôt que de l'utilisateur ? « tu t'appelles
    Jarvis », « tu dois toujours me répondre en anglais », « ton nom est
    Jarvis » : des consignes pour elle, à appliquer, dont elle parle à la
    première personne (« Je m'appelle Jarvis »).
    """
    you = _YOU_SUBJECT_RE.search(text)
    me = _I_SUBJECT_RE.search(text)
    if you:
        return me is None or you.start() < me.start()
    return me is None and bool(_YOUR_RE.search(text)) and not _FIRST_PERSON_RE.search(text)


# Consigne de langue de réponse (« réponds-moi en anglais », « answer in English »)
_LANGUAGE_CODES = {
    "anglais": "en", "english": "en", "francais": "fr", "french": "fr",
    "espagnol": "es", "spanish": "es", "allemand": "de", "german": "de",
    "italien": "it", "italian": "it", "portugais": "pt", "portuguese": "pt",
    "neerlandais": "nl", "dutch": "nl", "russe": "ru", "russian": "ru",
    "chinois": "zh", "chinese": "zh", "japonais": "ja", "japanese": "ja",
    "coreen": "ko", "korean": "ko", "arabe": "ar", "arabic": "ar",
}
_REPLY_LANGUAGE_RE = re.compile(
    r"\b(?:r[ée]pond\w*|parl\w*|[ée]cri\w*|answer\w*|repl\w*|speak\w*|talk\w*|writ\w*)"
    r"[^.!?\n]{0,40}?\b(?:en|in)\s+(?P<language>[^\W\d_]+)",
    re.IGNORECASE,
)
# La consigne s'adresse à l'IA : « je parle en anglais au travail » n'en est pas une
_ADDRESSEE_RE = re.compile(
    r"(?<![\w'’])(?:tu|vous|you)\b|(?<!\w)on\b|\w-moi\b",  # « qu'on parle… »
    re.IGNORECASE,
)


def reply_language(text: str) -> Optional[str]:
    """
    Code de la langue de réponse que le fait impose à l'IA (« tu dois me
    répondre en anglais » → "en"), ou None.
    """
    if not _ADDRESSEE_RE.search(text or ""):
        return None
    for match in _REPLY_LANGUAGE_RE.finditer(text):
        code = _LANGUAGE_CODES.get(_normalize(match.group("language")))
        if code:
            return code
    return None


# « je » ou « tu » + négation + pronoms + verbe : la proposition change de personne
_PERSON_CLAUSE_RE = re.compile(
    r"(?<![\w'’])(?P<subject>je\s+|j['’]|tu\s+)"
    r"(?P<neg>ne\s+|n['’])?"
    r"(?P<clitics>(?:(?:me|te|se|les|le|la|lui|leur|y|en)\s+|[mtsl]['’])*)"
    r"(?P<verb>[^\W\d_]+)",
    re.IGNORECASE,
)
_PERSON_SUBJECT_RE = re.compile(r"(?<![\w'’])(?:(?:je|tu)\b|j['’])", re.IGNORECASE)
# Hors de ces propositions : « me » ↔ « te », « mon » ↔ « ton »…
_PERSON_SWAP = {
    "me": "te", "te": "me", "moi": "toi", "toi": "moi",
    "mon": "ton", "ton": "mon", "ma": "ta", "ta": "ma", "mes": "tes", "tes": "mes",
}
_PERSON_SWAP_RE = re.compile(
    r"(?<![\w'’])(?:(?:moi|toi|mon|ton|mes|tes|me|te|ma|ta)\b|[mt]['’])", re.IGNORECASE
)
_QUOTED_RE = re.compile(r"(«[^»]*»|\"[^\"]*\"|“[^”]*”)")
# Fait écrit en français ou en anglais, qui parle de l'un ou de l'autre
_FRENCH_PERSON_RE = re.compile(
    r"(?<![\w'’])(?:(?:je|tu|me|te|moi|toi|mon|ton|ma|ta|mes|tes)\b|[jmt]['’])", re.IGNORECASE
)
_ENGLISH_YOU_RE = re.compile(r"(?<![\w'’])(?:you|your|yours|yourself)\b", re.IGNORECASE)
# Sans « me », qui existe dans les deux langues (« call me Nico »)
_FRENCH_ONLY_PERSON_RE = re.compile(
    r"(?<![\w'’])(?:(?:je|tu|te|moi|toi|mon|ton|ma|ta|mes|tes)\b|[jmt]['’])", re.IGNORECASE
)


def _written_in_english(text: str) -> bool:
    """Le fait parle-t-il de l'un ou de l'autre en anglais (« you », « my », « I »…) ?"""
    english = _ENGLISH_YOU_RE.search(text) or _ENGLISH_MARKER_RE.search(text)
    return bool(english) and not _FRENCH_ONLY_PERSON_RE.search(text)


def _first_person_verb(verb: str) -> str:
    """Le verbe conjugué avec « tu », au même temps avec « je »."""
    lower = verb.lower()
    if lower == "es":
        return "suis"
    if lower == "vas":
        return "vais"
    if lower.endswith("as"):  # as → ai, seras → serai
        return verb[:-1] + "i"
    if lower.endswith("es"):  # appelles → appelle, tutoies → tutoie
        return verb[:-1]
    return verb  # dois, peux, fais, réponds : même forme


def _second_person_verb(verb: str) -> str:
    """Le verbe conjugué avec « je », au même temps avec « tu »."""
    lower = verb.lower()
    if lower == "suis":
        return "es"
    if lower == "vais":
        return "vas"
    if lower.endswith("ai"):  # ai → as, serai → seras
        return verb[:-1] + "s"
    if lower.endswith("e"):  # appelle → appelles, préfère → préfères
        return verb + "s"
    return verb  # dois, peux, fais, prends : même forme


def _swap_person(word: str) -> str:
    """« me » ↔ « te », « mon » ↔ « ton »… en gardant la majuscule."""
    lower = word.lower().replace("’", "'")
    swapped = {"m'": "t'", "t'": "m'"}.get(lower) or _PERSON_SWAP[lower]
    return swapped.capitalize() if word[0].isupper() else swapped


def _elide(words: List[str]) -> str:
    """Assemble « je ai » → « j'ai », « ne est » → « n'est », « me appelle » → « m'appelle »."""
    text = ""
    for word, following in zip(words, words[1:] + [""]):
        if following and word.lower() in ("je", "ne", "me", "te", "se", "le", "la") \
                and following[0].lower() in _VOWELS:
            text += word[:-1] + "'"
        else:
            text += word + (" " if following else "")
    return text


def _french_spoken_to_user(text: str) -> Optional[str]:
    """« je m'appelle Sophie » → « tu t'appelles Sophie », et inversement."""

    def clause(match: re.Match) -> str:
        from_user = match.group("subject").lower().startswith("j")  # « je » → « tu »
        words = ["tu" if from_user else "je"]
        if match.group("neg"):
            words.append("ne")
        for clitic in _CLITIC_RE.findall(match.group("clitics")):
            word = clitic.lower()
            if word[-1] in "'’":
                word = _ELIDED_CLITICS[word[0]]
            words.append({"me": "te", "te": "me"}.get(word, word))
        verb = match.group("verb")
        words.append(_second_person_verb(verb) if from_user else _first_person_verb(verb))
        spoken = _elide(words)
        return spoken.capitalize() if match.group(0)[0].isupper() else spoken

    def swap(segment: str) -> str:
        return _PERSON_SWAP_RE.sub(lambda m: _swap_person(m.group(0)), segment)

    clauses = list(_PERSON_CLAUSE_RE.finditer(text))
    if len(clauses) != len(_PERSON_SUBJECT_RE.findall(text)):
        return None  # un « je » ou un « tu » sans verbe reconnu
    pieces = []
    last = 0
    for match in clauses:
        pieces += [swap(text[last:match.start()]), clause(match)]
        last = match.end()
    pieces.append(swap(text[last:]))
    return "".join(pieces)


# Anglais : « you » devient « I », « I » et « me » deviennent « you ».
# Les verbes ne changent pas de forme, sauf « be » (are ↔ am, were ↔ was).
_ENGLISH_SWAP = {
    "you are": "I am", "you are not": "I am not", "you aren't": "I'm not",
    "you were": "I was", "you weren't": "I wasn't",
    "you're": "I'm", "you've": "I've", "you'll": "I'll", "you'd": "I'd",
    "your": "my", "yours": "mine", "yourself": "myself",
    "i am": "you are", "i'm": "you're", "i was": "you were", "i wasn't": "you weren't",
    "i've": "you've", "i'll": "you'll", "i'd": "you'd", "i": "you",
    "my": "your", "mine": "yours", "myself": "yourself", "me": "you",
}
_ENGLISH_SWAP_RE = re.compile(
    r"(?<![\w'’])(?:you\s+(?:are(?:\s+not)?|aren['’]t|were|weren['’]t)|you['’](?:re|ve|ll|d)"
    r"|i\s+(?:am|was|wasn['’]t)|i['’](?:m|ve|ll|d)"
    r"|yourself|yours|your|myself|mine|my|me|you|i)\b",
    re.IGNORECASE,
)
# « you » sujet (→ « I ») en début de proposition, complément (→ « me ») sinon
_ENGLISH_CLAUSE_START_RE = re.compile(
    r"(?:^|[,;:.!?(]|\b(?:that|and|but|or|if|when|so|because|while|unless|then|where|"
    r"whenever|though|although|since))\s*$",
    re.IGNORECASE,
)


def _english_spoken_to_user(text: str) -> str:
    """« you must always call me Nico » → « I must always call you Nico »."""

    def swap(match: re.Match) -> str:
        before = text[:match.start()]
        key = re.sub(r"\s+", " ", match.group(0).lower().replace("’", "'"))
        if key == "you":
            if before.rstrip().lower().endswith("thank"):
                return match.group(0)  # « thank you » reste tel quel
            spoken = "I" if _ENGLISH_CLAUSE_START_RE.search(before) else "me"
        else:
            spoken = _ENGLISH_SWAP[key]
        # Majuscule en début de phrase, ou en tête si l'original en avait une
        # (« I » en a toujours une : elle ne compte pas)
        sentence_start = bool(before.strip()) and before.rstrip()[-1] in ".!?"
        first_capital = (
            not before.strip() and match.group(0)[0].isupper() and not key.startswith("i")
        )
        if spoken[0].islower() and (sentence_start or first_capital):
            spoken = spoken[0].upper() + spoken[1:]
        return spoken

    return _ENGLISH_SWAP_RE.sub(swap, text)


def spoken_to_user(text: str) -> Optional[str]:
    """
    Le fait tel que l'IA le dirait à l'utilisateur, personnes inversées :
    « je m'appelle Sophie » → « tu t'appelles Sophie », « tu dois toujours
    me répondre en anglais » → « je dois toujours te répondre en anglais »,
    « your name is Friday » → « my name is Friday ». Les citations restent
    telles quelles. None si le fait ne parle ni de l'un ni de l'autre, ou si
    une forme n'est pas reconnue.
    """
    if _written_in_english(text):
        convert = _english_spoken_to_user
    elif _FRENCH_PERSON_RE.search(text):
        convert = _french_spoken_to_user
    else:
        return None
    pieces = []
    for part in _QUOTED_RE.split(text):
        spoken = part if _QUOTED_RE.fullmatch(part) else convert(part)
        if spoken is None:
            return None
        pieces.append(spoken)
    return "".join(pieces)


def memorization_confirmation(text: str, language: Optional[str] = None) -> Optional[str]:
    """
    La confirmation exacte d'une mémorisation, dans la langue du fait :
    « C'est noté : tu t'appelles Sophie. », « Noted: my name is Friday. »
    (None si elle ne peut pas être calculée sûrement, ou si `language`, la
    langue de la réponse, n'est pas celle du fait).

    Avec des exemples à trous (« Tu dois faire X » → « je ferai X »), le
    modèle recopiait parfois l'exemple tel quel : « je ferai X ». Recopiée
    de même, une phrase en français répondait en français à « retiens que
    tu dois toujours me répondre en anglais ».
    """
    english = _written_in_english(text)
    if language and language != ("en" if english else "fr"):
        return None
    spoken = spoken_to_user(text)
    if not spoken:
        return None
    if re.match(r"(?:Je|J['’]|Tu|Mon|Ton|Ma|Ta|Mes|Tes|You|My|Your)\b", spoken):
        spoken = spoken[0].lower() + spoken[1:]
    if english:
        return f"Noted: {spoken}."
    return f"C'est noté : {spoken}."


def fact_for_prompt(text: str) -> str:
    """
    Un fait tel que le modèle doit le lire.

    Fait sur l'utilisateur : à la troisième personne (user_fact_for_prompt).
    Consigne pour l'IA : à la deuxième personne, comme le reste du prompt
    système qui s'adresse à elle (« Tu t'appelles Jarvis ») ; citée comme
    une demande de l'utilisateur si elle parle aussi de lui (« me », « mon »).
    """
    if not is_assistant_fact(text):
        return user_fact_for_prompt(text)
    if _FIRST_PERSON_RE.search(text):
        return f"L'utilisateur t'a demandé : « {text} »"
    return text[:1].upper() + text[1:]


def _normalize(text: str) -> str:
    """Minuscules sans accents ni ligatures : « Félix » et « felix », « sœur » et
    « soeur » se retrouvent (utils/text_fold.py)."""
    return fold(text)


_NORMALIZED_STOPWORDS = {_normalize(word) for word in _QUERY_STOPWORDS}

# ------------------------------------------------------------------
# Demandes explicites de mémorisation (« retiens que… »)
# ------------------------------------------------------------------

_REMEMBER_VERBS = (
    r"retiens|m[ée]morise|memori[sz]e|souviens[- ]toi|rappelle[- ]toi|"
    r"n['’ ]?oublies?\s+pas|"
    r"garde(?:\s+(?:bien|[çc]a|ceci|cela))*\s+en\s+(?:t[êe]te|m[ée]moire)|"
    r"prends?\s+(?:bien\s+|bonne\s+)?note|"
    r"note\s+(?:bien\s+)?(?:dans\s+ta|en)\s+m[ée]moire|"
    r"(?:enregistre|ajoute|mets)\s+(?:[çc]a\s+|ceci\s+|cela\s+)?(?:dans|[àa])\s+ta\s+m[ée]moire|"
    # Infinitifs, seulement dans une demande (« tu peux retenir que… »)
    r"(?:(?:peux|pourrais|veux|voudrais)[- ]tu|tu\s+(?:peux|pourrais|veux|voudrais)|"
    r"merci\s+de|pense\s+[àa]|essaie\s+de)\s+(?:bien\s+)?"
    r"(?:retenir|m[ée]moriser|te\s+souvenir|garder\s+en\s+(?:t[êe]te|m[ée]moire)|prendre\s+note)|"
    r"remember|keep\s+in\s+mind|(?:don['’]?t|do\s+not)\s+forget"
)
# Le verbe, puis ce qui l'introduit : « que », ou un bloc « ceci : », « : »…
# (« retiens plutôt que… » : un fait qui en remplace un autre)
_REMEMBER_RE = re.compile(
    rf"(?<![\w'’-])(?:{_REMEMBER_VERBS})(?:\s+(?:bien|plut[ôo]t|instead))?"
    r"(?:\s+(?:que|that)\s+|\s+qu['’]\s*|"
    r"(?P<block>\s+(?:de\s+)?(?:ceci|[çc]a|cela|this)\s*(?:[:,]\s*|\s+)|\s*:\s*))"
    r"(?P<fact>.+)",
    re.IGNORECASE | re.DOTALL,
)
# Le même verbe en fin de texte : ce qui précède l'information
_REMEMBER_TAIL_RE = re.compile(
    rf"(?:{_REMEMBER_VERBS})(?:\s+(?:bien|plut[ôo]t|instead))?"
    r"(?:\s+(?:que|that)|\s+qu['’]|\s+(?:de\s+)?(?:ceci|[çc]a|cela|this)\s*[:,]?|\s*:)?\s*$",
    re.IGNORECASE,
)
# « Retiens mon prénom : Nicolas » : l'information suit directement le verbe.
# Retenue seulement si elle contient « : », sinon « mémorise le fichier
# joint » deviendrait un fait.
_REMEMBER_DIRECT_RE = re.compile(
    r"(?<![\w'’-])(?:retiens|m[ée]morise|memori[sz]e)(?:\s+bien)?\s+(?P<fact>[^\s-].*)",
    re.IGNORECASE | re.DOTALL,
)
# Seuls mots admis avant la demande dans sa phrase (« Au fait, retiens que… »,
# « Non, retiens plutôt que… »). « Je retiens que… », « tu te souviens que… ? »
# ou une consigne glissée dans une tâche (« écris la fonction et n'oublie pas
# que… ») ne sont pas des demandes de mémorisation.
_REMEMBER_LEAD_IN_RE = re.compile(
    r"^(?:(?:au\s+fait|ok(?:ay)?|bon|alors|et|aussi|enfin|maintenant|d['’]ailleurs|"
    r"sinon|merci|stp|svp|s['’]il\s+te\s+pla[iî]t|s['’]il\s+vous\s+pla[iî]t|please|"
    r"salut|bonjour|bonsoir|coucou|hello|hi|"
    r"hey|h[ée]|dis(?:[- ]moi)?|tiens|pour\s+info(?:rmation)?|info|important|rappel|"
    r"petite\s+info|ah|oh|super|parfait|cool|top|nickel|d['’]accord|ouais|oui|non|"
    r"est[- ]ce\s+que|yes|no|so|also|and|btw|by\s+the\s+way)[\s,!:-]*)*$",
    re.IGNORECASE,
)
_POLITENESS = (
    r"merci(?:\s+beaucoup)?|stp|svp|s['’]il\s+te\s+pla[iî]t|"
    r"s['’]il\s+vous\s+pla[iî]t|please|thanks?(?:\s+you)?"
)
# Phrase de politesse qui suit l'information (« … Félix. Merci ! »)
_POLITENESS_SENTENCE_RE = re.compile(
    rf"^(?:{_POLITENESS}|ok(?:ay)?|d['’]accord)[\s.!,?]*$", re.IGNORECASE
)
# Autre demande après l'information (« Retiens que je débute. Explique-moi… »).
# Coupe une information introduite par « que », pas un bloc « ceci : … »,
# qui peut décrire une procédure (« lance build.bat. Vérifie les logs »).
# Les verbes du code en sont (« Retiens que j'utilise des f-strings. Ensuite,
# ajoute une fonction… ») : sans eux, la tâche entière était retenue, et le
# modèle, à qui l'on disait que le message ne demandait rien d'autre, ne la
# faisait pas, ou prétendait l'avoir faite.
_REQUEST_START_RE = re.compile(
    r"^(?:(?:et|maintenant|puis|ensuite|alors|then|now|next|and|also)[\s,]+)?"
    r"(?:(?:peux|pourrais|veux|voudrais)[- ]tu|(?:can|could|would|will)\s+you|"
    r"(?:explique|dis|donne|[ée]cris|fais|montre|cr[ée]e|g[ée]n[èe]re|aide|trouve|"
    r"cherche|liste|r[ée]sume|traduis|calcule|propose|r[ée]dige|corrige|"
    r"ajoute|modifie|impl[ée]mente|supprime|enl[èe]ve|retire|renomme|remplace|d[ée]place|"
    r"lance|ex[ée]cute|teste|v[ée]rifie|analyse|regarde|lis|ouvre|installe|refactorise|"
    r"optimise|documente|commente|mets|"
    r"explain|tell|give|write|make|show|create|generate|help|find|search|list|"
    r"summari[sz]e|translate|fix|add|implement|update|change|remove|delete|rename|"
    r"replace|move|run|test|check|read|open|install|refactor)"
    r"(?:[- ](?:moi|nous|le|la|les|me))?)\b",
    re.IGNORECASE,
)
# Politesse en fin d'information (« … Félix, stp »). « ok » seulement après
# une virgule : « le build est ok » est une information.
_TRAILING_POLITENESS_RE = re.compile(
    rf"(?:[\s,]+(?:{_POLITENESS})|\s*,\s*(?:ok(?:ay)?|d['’]accord))\s*$",
    re.IGNORECASE,
)
# « Retiens ce que je t'ai dit » : renvoi à autre chose, pas une information
_REFERENCE_RE = re.compile(r"^(?:ce\s+qu|ce\s+dont|tout\s+(?:ce|[çc]a|cela)\b)", re.IGNORECASE)
# Au-delà, ce n'est plus un fait à retenir (texte collé, document…)
MAX_REMEMBERED_CHARS = 1000
# Début d'une question : « Rappelle-toi : où j'habite ? » demande de se
# souvenir, pas de retenir. « où j'habite » était enregistré comme un fait.
_QUESTION_START_RE = re.compile(
    r"(?:comment|quel(?:le)?s?|qui|où|quand|pourquoi|combien|est-ce|qu['’]est-ce|lequel|"
    r"laquelle|lesquel(?:le)?s|what|who|where|when|why|how|which)\b",
    re.IGNORECASE,
)


def _is_question(message: str, fact: str) -> bool:
    """fact est-il une question (mot interrogatif, puis « ? » juste après) ?"""
    if not _QUESTION_START_RE.match(fact) or fact not in message:
        return False
    return message.split(fact, 1)[1].lstrip().startswith("?")


def _opens_sentence(message: str, position: int) -> bool:
    """La demande ouvre-t-elle sa phrase, aux mots d'introduction près ?"""
    before = re.split(r"[.!?\n]", message[:position])[-1]
    before = re.sub(r"[^\w'’\s,!:-]", " ", before).strip()
    return bool(_REMEMBER_LEAD_IN_RE.match(before))


def _clean_remembered(text: str, block: bool) -> Optional[str]:
    """
    Information retenue, sans la question, la politesse ni (hors bloc
    « ceci : … ») l'autre demande qui la suivent.
    """
    kept: List[str] = []
    for sentence in re.split(r"(?<=[.!?])\s+", text.strip()):
        stripped = sentence.strip()
        is_question = stripped.endswith("?")
        if kept and (
            is_question
            or _POLITENESS_SENTENCE_RE.match(stripped)
            or (not block and _REQUEST_START_RE.match(stripped))
        ):
            break
        kept.append(sentence)
        if is_question:  # Information formulée en question (« Tu peux retenir que… ? »)
            break
    fact = " ".join(kept).strip().rstrip(" ?!.;,:")
    fact = _TRAILING_POLITENESS_RE.sub("", fact).strip().rstrip(" ?!.;,:").strip()
    # Guillemets autour de toute l'information seulement : ceux d'une
    # citation finale (« … par « Bonne journée ! » ») restent
    if len(fact) > 1 and fact[0] in "\"'«“`" and fact[-1] in "\"'»”`":
        fact = fact[1:-1].strip().rstrip(" ?!.;,:").strip()
    if len(fact) > MAX_REMEMBERED_CHARS or len(fact.split()) < 2:
        return None
    if _REFERENCE_RE.match(fact):
        return None
    return fact


def extract_remember_request(message: str) -> Optional[str]:
    """
    Information que le message demande explicitement de retenir, ou None.

    Reconnaît « retiens que… », « souviens-toi que… », « n'oublie pas que… »,
    « mémorise ceci : … », « tu peux retenir que… », « remember that… », etc.
    La demande doit ouvrir sa phrase (voir _REMEMBER_LEAD_IN_RE), et une
    question qui suit l'information en est retirée : « Retiens que mon chat
    s'appelle Félix. Quel temps fait-il ? » → « mon chat s'appelle Félix ».
    """
    if not message:
        return None
    for pattern in (_REMEMBER_RE, _REMEMBER_DIRECT_RE):
        position = 0
        while True:
            match = pattern.search(message, position)
            if match is None:
                break
            position = match.start() + 1
            if not _opens_sentence(message, match.start()):
                continue
            direct = pattern is _REMEMBER_DIRECT_RE
            block = direct or match.group("block") is not None
            fact = _clean_remembered(match.group("fact"), block)
            if fact and _is_question(message, fact):
                # Sans fait à retenir : la forme directe reprenait sinon la
                # question (« Retiens ceci : quel est… ? » → « ceci : quel est… »)
                return None
            if fact and (not direct or ":" in fact):
                return fact
    return None


def remember_block(message: str) -> Optional[str]:
    """
    Le bloc d'une demande « retiens ceci : … » (« mémorise : … », « remember
    this: … »), en entier, consignes comprises (une procédure), ou None : une
    demande « retiens que… », ou un bloc qui n'est qu'une question.

    Le modèle qui lit les demandes (core/code_memory.py, apply_reading) découpait
    ou reformulait un tel bloc : ce sont les mots de l'utilisateur qui sont retenus.
    """
    if not message:
        return None
    position = 0
    while True:
        match = _REMEMBER_RE.search(message, position)
        if match is None:
            return None
        position = match.start() + 1
        if not _opens_sentence(message, match.start()):
            continue
        marker = match.group("block")
        if marker is None or ":" not in marker:
            return None
        fact = _clean_remembered(match.group("fact"), True)
        return None if not fact or _is_question(message, fact) else fact


def is_only_remember_request(message: str, fact: str) -> bool:
    """
    Le message ne fait-il que demander de retenir fact (extract_remember_request) ?

    Vrai pour « Salut ! Retiens que mon chat s'appelle Félix » ou « Tu peux
    retenir que… ? » ; faux s'il reste une question ou une autre demande
    (« … Quel temps fait-il ? »). Une telle demande se confirme sans outils.
    """
    if not fact or fact not in message:
        return False
    before, after = message.split(fact, 1)
    # Ponctuation de la demande elle-même, puis politesse éventuelle
    after = after.lstrip(" ?!.,;:\"'«»“”`").strip()
    if after and not _POLITENESS_SENTENCE_RE.match(after):
        return False
    prefix = _REMEMBER_TAIL_RE.sub("", before)
    if "?" in prefix:
        return False
    prefix = re.sub(r"[^\w'’\s,!:-]", " ", prefix).strip()
    return bool(_REMEMBER_LEAD_IN_RE.match(prefix))


# Demande de mémorisation, quoi qu'elle dise ensuite : « retiens que… », mais
# aussi « retiens-le pour tous mes projets », « retiens ça », « garde-le en
# tête », que extract_remember_request ne lit pas (rien à recopier)
_REMEMBER_ASK = (
    rf"(?:{_REMEMBER_VERBS}|garde[- ](?:le|la|les)\s+en\s+(?:t[êe]te|m[ée]moire)|"
    r"(?:save|add|put|store)\s+(?:this|that|it)\s+(?:to|in|into)\s+(?:your\s+)?memory)"
)
_REMEMBER_ASK_RE = re.compile(rf"(?<![\w'’-]){_REMEMBER_ASK}(?![\w'’])", re.IGNORECASE)
# Ce qui renvoie à l'information après la demande : « retiens-le », « retiens bien ça »
_REMEMBER_REFERENCE_RE = re.compile(
    r"(?:[\s-]+(?:le|la|les|[çc]a|ceci|cela|bien|this|that|it))*", re.IGNORECASE
)
_POLITENESS_WORD_RE = re.compile(
    rf"(?<![\w'’])(?:{_POLITENESS}|ok(?:ay)?|d['’]accord)(?![\w'’])", re.IGNORECASE
)


def _recalls(message: str, match: "re.Match[str]") -> bool:
    """« Rappelle-toi : quel framework j'utilise ? » demande de se souvenir, pas de
    retenir : un mot interrogatif suit le verbe, et sa phrase finit par « ? »."""
    sentence = re.match(r"[^.!?\n]*[.!?]?", message[match.end():]).group(0)
    question = sentence.lstrip(" \t:,-")
    return sentence.rstrip().endswith("?") and bool(_QUESTION_START_RE.match(question))


def is_rememberable(text: str) -> bool:
    """
    Une information à retenir ? Deux mots au moins (« rien », un mot seul, n'en
    est pas une), pas plus de MAX_REMEMBERED_CHARS, et pas un renvoi à autre
    chose (« ce que je t'ai dit »).
    """
    text = (text or "").strip()
    return (len(text.split()) >= 2 and len(text) <= MAX_REMEMBERED_CHARS
            and not _REFERENCE_RE.match(text))


def asks_to_remember(message: str) -> bool:
    """
    Le message demande-t-il de retenir quelque chose ?

    Le verbe doit ouvrir sa phrase, comme pour extract_remember_request
    (« Je retiens que… », « écris la fonction et n'oublie pas que… » n'en
    sont pas), mais ce qui le suit importe peu : « retiens-le pour tous mes
    projets » renvoie à ce qui précède, et c'est au modèle de lire quoi
    retenir (core/code_memory.py). Sauf une question : le modèle y répondait,
    et sa réponse était retenue (« Je n'ai pas d'information sur… »).
    """
    for match in _REMEMBER_ASK_RE.finditer(message or ""):
        if _opens_sentence(message, match.start()) and not _recalls(message, match):
            return True
    return False


# Demande d'oubli : « oublie que… », « oublie-le », « ne retiens plus… », « retire de
# ta mémoire… », « forget… ». « N'oublie pas » n'en est pas une (_REMEMBER_VERBS),
# « oublie pas » (familier) non plus.
_FORGET_ASK_RE = re.compile(
    r"(?<![\w'’-])(?:"
    r"oublie[sz]?(?!\s+pas\b)"
    r"|(?:(?:peux|pourrais|veux|voudrais)[- ]tu|tu\s+(?:peux|pourrais|veux|voudrais)|"
    r"merci\s+d['’])\s*oublier"
    r"|ne\s+(?:retiens|garde|m[ée]morise|te\s+souviens)\s+plus"
    r"|(?:efface|supprime|retire|enl[èe]ve)\b(?=[^.!?\n]{0,80}\bm[ée]moire\b)"
    r"|forget"
    r"|(?:remove|delete|erase)\b(?=[^.!?\n]{0,80}\bmemory\b)"
    r"|(?:do\s+not|don['’]?t)\s+remember"
    r")(?![\w'’])",
    re.IGNORECASE,
)


def asks_to_forget(message: str) -> bool:
    """
    Le message demande-t-il d'oublier quelque chose (« oublie que j'utilise
    unittest », « oublie tout ce que tu as retenu pour ce projet ») ? Le verbe
    ouvre sa phrase, comme pour asks_to_remember ; « supprime » ou « retire »
    seulement s'ils parlent de la mémoire (« supprime la fonction » est du code).
    """
    for match in _FORGET_ASK_RE.finditer(message or ""):
        if _opens_sentence(message, match.start()):
            return True
    return False


# Les propositions d'une demande d'oubli (« oublie que je suis végétarien, et
# propose-moi une recette » : la seconde demande autre chose)
_CLAUSE_SPLIT_RE = re.compile(r"\s*(?:[,;]|\b(?:et|puis|ensuite|then|and)\b)\s*", re.IGNORECASE)


def only_asks_to_forget(message: str) -> bool:
    """
    Le message ne fait-il que demander d'oublier (« oublie que j'habite à Lyon »,
    « salut, oublie tout ce que tu sais sur moi. Merci ! ») ? Une question ou une
    autre demande (« …, et propose-moi une recette ») : non. Sa réponse se limite
    alors à le confirmer, sans outils (le modèle « vérifiait » sinon la mémoire).
    """
    if not message or "?" in message:
        return False
    for match in _FORGET_ASK_RE.finditer(message):
        prefix = re.sub(r"[^\w'’\s,!:-]", " ", message[:match.start()]).strip()
        if not _REMEMBER_LEAD_IN_RE.match(prefix):
            return False
        sentences = [part.strip() for part in re.split(r"(?<=[.!])\s+|\n+",
                                                         message[match.end():])
                     if part.strip()]
        if any(not _POLITENESS_SENTENCE_RE.match(sentence) for sentence in sentences[1:]):
            return False
        clauses = _CLAUSE_SPLIT_RE.split(sentences[0]) if sentences else []
        return not any(_REQUEST_START_RE.match(clause) for clause in clauses if clause)
    return False


def content_words(text: str) -> List[str]:
    """Mots significatifs d'un texte, sans casse, accents, pluriel ni petits mots
    (« quel », « pour »…) : ceux qui comptent pour comparer deux phrases."""
    tokens = []
    for token in re.findall(r"[a-z0-9_]+", _normalize(text)):
        if len(token) < 3 or token in _NORMALIZED_STOPWORDS:
            continue
        if len(token) > 3 and token[-1] in "sx":
            token = token[:-1]  # « chats » et « chat » se retrouvent
        tokens.append(token)
    return tokens


def only_asks_to_remember(message: str) -> bool:
    """
    Le message ne fait-il que demander de retenir ce qui précède, sans dire quoi
    ni rien demander d'autre ? « Retiens-le », « ok, retiens bien ça, merci » :
    oui ; « retiens ça et ajoute une route » : non. La précision « pour tous
    mes projets » est à retirer avant (core/code_memory.py).
    """
    for match in _REMEMBER_ASK_RE.finditer(message or ""):
        prefix = re.sub(r"[^\w'’\s,!:-]", " ", message[:match.start()]).strip()
        if not _REMEMBER_LEAD_IN_RE.match(prefix):
            return False
        rest = message[match.end():]
        rest = rest[_REMEMBER_REFERENCE_RE.match(rest).end():]
        return not re.search(r"\w", _POLITENESS_WORD_RE.sub(" ", rest))
    return False


# Patrons d'extraction automatique de faits depuis du texte libre
_EXTRACT_PATTERNS: List[Dict] = [
    # Préférences explicites
    {
        "category": "preference",
        "pattern": re.compile(
            r"(?:je préfère|je prefere|j'aime mieux|j'utilise toujours|"
            r"toujours utiliser|mon choix est|je choisis)\s+(.+?)(?:\.|$)",
            re.IGNORECASE,
        ),
        "key_prefix": "préférence",
    },
    # Décisions
    {
        "category": "decision",
        "pattern": re.compile(
            r"(?:on a décidé de|nous avons décidé|la décision est de|"
            r"il a été décidé|j'ai décidé de)\s+(.+?)(?:\.|$)",
            re.IGNORECASE,
        ),
        "key_prefix": "décision",
    },
    # Personnes (noms propres avec contexte)
    {
        "category": "person",
        "pattern": re.compile(
            r"(?:(?:mon|ma|notre|le|la)\s+(?:collègue|manager|responsable|directeur|"
            r"directrice|chef|contact)\s+(?:est|s'appelle|se nomme)\s+)([A-ZÀ-Ü][a-zà-ü]+(?:\s+[A-ZÀ-Ü][a-zà-ü]+)*)",
            re.UNICODE,
        ),
        "key_prefix": "personne",
    },
    # Procédures
    {
        "category": "procedure",
        "pattern": re.compile(
            r"(?:la procédure est de|pour faire cela il faut|les étapes sont|"
            r"la marche à suivre est)\s+(.+?)(?:\.|$)",
            re.IGNORECASE,
        ),
        "key_prefix": "procédure",
    },
    # Informations techniques
    {
        "category": "technical",
        "pattern": re.compile(
            r"(?:le serveur est|l'url est|le port est|la version est|"
            r"l'adresse est|le mot de passe est|l'api key est|"
            r"on utilise|nous utilisons)\s+(.+?)(?:\.|$)",
            re.IGNORECASE,
        ),
        "key_prefix": "technique",
    },
]


class KnowledgeBaseManager:
    """
    Gestionnaire de base de connaissances structurée.
    Utilise SQLite pour le stockage persistant de faits catégorisés
    avec recherche textuelle et extraction automatique.
    """

    def __init__(self, db_path: str = "data/knowledge_base/facts.db") -> None:
        """
        Initialise le gestionnaire de base de connaissances.

        Args:
            db_path: Chemin vers le fichier de base de données SQLite.
        """
        self._db_path = Path(db_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._local = threading.local()
        self._init_db()
        logger.info("KnowledgeBaseManager initialisé avec la base : %s", self._db_path)

    # ------------------------------------------------------------------
    # Connexion thread-safe
    # ------------------------------------------------------------------

    def _get_connection(self) -> sqlite3.Connection:
        """
        Retourne une connexion SQLite propre au thread courant.

        Returns:
            Connexion SQLite avec row_factory configurée.
        """
        if not hasattr(self._local, "connection") or self._local.connection is None:
            conn = sqlite3.connect(str(self._db_path))
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA foreign_keys=ON")
            self._local.connection = conn
        return self._local.connection

    def _init_db(self) -> None:
        """Crée le schéma de la base de données si nécessaire.

        Une base d'avant les portées reçoit leurs colonnes : ses faits sont
        ceux du chat, qui les recevait tous.
        """
        conn = self._get_connection()
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS facts (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                category    TEXT    NOT NULL,
                key         TEXT    NOT NULL,
                value       TEXT    NOT NULL,
                source      TEXT    NOT NULL DEFAULT 'manual',
                confidence  REAL    NOT NULL DEFAULT 1.0,
                created_at  TEXT    NOT NULL,
                updated_at  TEXT    NOT NULL,
                scope       TEXT    NOT NULL DEFAULT 'chat',
                project     TEXT    NOT NULL DEFAULT ''
            );

            CREATE INDEX IF NOT EXISTS idx_facts_category ON facts(category);
            CREATE INDEX IF NOT EXISTS idx_facts_key      ON facts(key);
            """
        )
        columns = {row["name"] for row in conn.execute("PRAGMA table_info(facts)")}
        for name in ("scope", "project"):
            if name in columns:
                continue
            default = SCOPE_CHAT if name == "scope" else ""
            try:
                conn.execute(f"ALTER TABLE facts ADD COLUMN {name} TEXT NOT NULL DEFAULT '{default}'")
            except sqlite3.OperationalError as exc:
                # Ajoutée entre-temps par une autre instance (même base, même processus)
                if "duplicate column" not in str(exc).lower():
                    raise
        conn.execute("CREATE INDEX IF NOT EXISTS idx_facts_scope ON facts(scope)")
        conn.commit()

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    def add_fact(
        self,
        category: str,
        key: Optional[str] = None,
        value: Optional[str] = None,
        source: str = "manual",
        confidence: float = 1.0,
        content: Optional[str] = None,
        scope: str = SCOPE_CHAT,
        project: str = "",
    ) -> int:
        """
        Ajoute un fait dans la base de connaissances.

        Args:
            category:   Catégorie du fait (preference, decision, person, ...).
            key:        Clé descriptive du fait.
            value:      Valeur du fait.
            source:     Origine du fait (manual, conversation, ...).
            confidence: Niveau de confiance entre 0.0 et 1.0.
            content:    Alias rétrocompatible de value (ancienne API).
            scope:      Portée (SCOPES) : conversation qui le reçoit d'office.
            project:    Dossier d'un fait de projet (scope « project »).

        Returns:
            Identifiant du fait créé.

        Raises:
            ValueError: Si la catégorie ou la portée est invalide, ou la confiance hors bornes.
        """
        category = category.lower().strip()
        if category not in VALID_CATEGORIES:
            raise ValueError(
                f"Catégorie invalide '{category}'. "
                f"Catégories acceptées : {', '.join(VALID_CATEGORIES)}"
            )
        if not 0.0 <= confidence <= 1.0:
            raise ValueError("La confiance doit être comprise entre 0.0 et 1.0")
        scope, project = _checked_scope(scope, project)

        # Rétrocompatibilité: ancienne API add_fact(category=..., content=...)
        if content is not None:
            normalized_content = content.strip()
            if not value:
                value = normalized_content
            if not key:
                key = self._build_key("fait", normalized_content)

        if not key or not key.strip():
            raise ValueError("La clé ne peut pas être vide")
        if not value or not value.strip():
            raise ValueError("La valeur ne peut pas être vide")

        now = datetime.now().isoformat()
        conn = self._get_connection()
        cursor = conn.execute(
            """
            INSERT INTO facts (category, key, value, source, confidence, created_at, updated_at,
                               scope, project)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (category, key.strip(), value.strip(), source, confidence, now, now, scope, project),
        )
        conn.commit()
        fact_id = cursor.lastrowid
        logger.info("Fait ajouté [id=%d] catégorie=%s portée=%s clé=%s", fact_id, category, scope, key)
        return fact_id

    def get_fact(self, key: str) -> Optional[Dict]:
        """
        Récupère un fait par sa clé.

        Args:
            key: Clé du fait recherché.

        Returns:
            Dictionnaire du fait ou None si non trouvé.
        """
        conn = self._get_connection()
        row = conn.execute(
            "SELECT * FROM facts WHERE key = ? ORDER BY updated_at DESC LIMIT 1",
            (key,),
        ).fetchone()
        if row is None:
            return None
        return dict(row)

    def search_facts(
        self,
        query: str,
        category: str = None,
        limit: int = 10,
    ) -> List[Dict]:
        """
        Recherche des faits par texte dans la clé et la valeur.

        Args:
            query:    Terme de recherche.
            category: Filtrer par catégorie (optionnel).
            limit:    Nombre maximum de résultats.

        Returns:
            Liste de faits correspondants triés par pertinence.
        """
        conn = self._get_connection()
        search_term = f"%{query}%"

        if category:
            category = category.lower().strip()
            rows = conn.execute(
                """
                SELECT * FROM facts
                WHERE (key LIKE ? OR value LIKE ?)
                  AND category = ?
                ORDER BY
                    CASE WHEN key LIKE ? THEN 0 ELSE 1 END,
                    confidence DESC,
                    updated_at DESC
                LIMIT ?
                """,
                (search_term, search_term, category, search_term, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT * FROM facts
                WHERE key LIKE ? OR value LIKE ?
                ORDER BY
                    CASE WHEN key LIKE ? THEN 0 ELSE 1 END,
                    confidence DESC,
                    updated_at DESC
                LIMIT ?
                """,
                (search_term, search_term, search_term, limit),
            ).fetchall()

        return [dict(r) for r in rows]

    def update_fact(self, fact_id: int, value: str) -> bool:
        """
        Met à jour la valeur d'un fait existant.

        Args:
            fact_id: Identifiant du fait à modifier.
            value:   Nouvelle valeur.

        Returns:
            True si le fait a été mis à jour, False sinon.
        """
        if not value or not value.strip():
            raise ValueError("La valeur ne peut pas être vide")

        now = datetime.now().isoformat()
        conn = self._get_connection()
        cursor = conn.execute(
            "UPDATE facts SET value = ?, updated_at = ? WHERE id = ?",
            (value.strip(), now, fact_id),
        )
        conn.commit()
        updated = cursor.rowcount > 0
        if updated:
            logger.info("Fait mis à jour [id=%d]", fact_id)
        else:
            logger.warning("Fait non trouvé pour mise à jour [id=%d]", fact_id)
        return updated

    def delete_fact(self, fact_id: int) -> bool:
        """
        Supprime un fait de la base de connaissances.

        Args:
            fact_id: Identifiant du fait à supprimer.

        Returns:
            True si le fait a été supprimé, False sinon.
        """
        conn = self._get_connection()
        cursor = conn.execute("DELETE FROM facts WHERE id = ?", (fact_id,))
        conn.commit()
        deleted = cursor.rowcount > 0
        if deleted:
            logger.info("Fait supprimé [id=%d]", fact_id)
        else:
            logger.warning("Fait non trouvé pour suppression [id=%d]", fact_id)
        return deleted

    def remember(
        self,
        value: str,
        category: str = "general",
        source: str = "conversation",
        scope: str = SCOPE_CHAT,
        project: str = "",
    ) -> Tuple[int, bool]:
        """
        Enregistre une information que l'utilisateur demande de retenir.

        Sans doublon : si la même information existe déjà pour cette portée,
        ou pour tous les projets quand elle est retenue pour l'un d'eux (casse,
        accents et ponctuation finale ignorés), elle est rafraîchie au lieu
        d'être recopiée. Retenue pour tous les projets alors qu'elle l'était
        pour certains, elle vaut désormais pour tous : un seul fait la garde.
        Une catégorie inconnue devient « general ».

        Args:
            value:    L'information à retenir.
            category: Catégorie du fait.
            source:   Origine (« conversation » pour le chat, « code » pour la
                      conversation Code).
            scope:    Portée du fait (SCOPES).
            project:  Dossier d'un fait de projet.

        Returns:
            (identifiant du fait, True s'il vient d'être créé ou vaut
            désormais pour tous les projets)

        Raises:
            ValueError: Si la valeur est vide, ou la portée invalide.
        """
        value = (value or "").strip()
        if not value:
            raise ValueError("La valeur ne peut pas être vide")
        category = (category or "general").lower().strip()
        if category not in VALID_CATEGORIES:
            category = "general"
        scope, project = _checked_scope(scope, project)

        wanted = _normalize(value).rstrip(" .!")
        same = [fact for fact in self.get_all_facts()
                if _normalize(fact["value"]).rstrip(" .!") == wanted]
        now = datetime.now().isoformat()
        conn = self._get_connection()
        for fact in same:
            if self._covers(fact, scope, project):
                conn.execute("UPDATE facts SET updated_at = ? WHERE id = ?", (now, fact["id"]))
                conn.commit()
                logger.info("Fait déjà connu, rafraîchi [id=%d]", fact["id"])
                return fact["id"], False

        if scope == SCOPE_CODE:
            narrower = [fact for fact in same if fact_scope(fact)[0] == SCOPE_PROJECT]
            if narrower:
                kept = max(narrower, key=lambda fact: fact["updated_at"])
                conn.execute(
                    "UPDATE facts SET scope = ?, project = '', updated_at = ? WHERE id = ?",
                    (SCOPE_CODE, now, kept["id"]),
                )
                for fact in narrower:
                    if fact["id"] != kept["id"]:
                        conn.execute("DELETE FROM facts WHERE id = ?", (fact["id"],))
                conn.commit()
                logger.info("Fait d'un projet étendu à tous [id=%d]", kept["id"])
                return kept["id"], True

        # Même clé que les faits ajoutés depuis la fenêtre Mémoire
        key = value.split("\n", 1)[0].strip()[:80]
        return self.add_fact(category, key=key, value=value, source=source,
                             scope=scope, project=project), True

    @staticmethod
    def _covers(fact: Dict, scope: str, project: str) -> bool:
        """Le fait vaut-il déjà pour cette portée ? Un fait de tous les projets
        vaut pour chacun d'eux."""
        current, folder = fact_scope(fact)
        if current == scope:
            return scope != SCOPE_PROJECT or same_project(folder, project)
        return current == SCOPE_CODE and scope == SCOPE_PROJECT

    # ------------------------------------------------------------------
    # Requêtes de lecture
    # ------------------------------------------------------------------

    def get_all_facts(self, category: str = None) -> List[Dict]:
        """
        Récupère tous les faits, éventuellement filtrés par catégorie.

        Args:
            category: Filtrer par catégorie (optionnel).

        Returns:
            Liste de tous les faits correspondants.
        """
        conn = self._get_connection()
        if category:
            category = category.lower().strip()
            rows = conn.execute(
                "SELECT * FROM facts WHERE category = ? ORDER BY updated_at DESC",
                (category,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM facts ORDER BY category, updated_at DESC"
            ).fetchall()
        return [dict(r) for r in rows]

    def chat_facts(self) -> List[Dict]:
        """Faits que le chat (fenêtre, téléphone) reçoit d'office : ceux de sa portée."""
        return [fact for fact in self.get_all_facts() if fact_scope(fact)[0] == SCOPE_CHAT]

    def code_facts(self, projects: Iterable[str] = ()) -> List[Dict]:
        """Faits que la conversation Code reçoit d'office dans ces dossiers : ceux de
        tous les projets, et ceux de l'un de ces dossiers, dans l'ordre où ils ont été
        retenus."""
        folders = [folder for folder in projects or () if folder]
        facts = []
        for fact in self.get_all_facts():
            scope, project = fact_scope(fact)
            if scope == SCOPE_CODE or (
                    scope == SCOPE_PROJECT and any(same_project(project, f) for f in folders)):
                facts.append(fact)
        return sorted(facts, key=lambda fact: (fact["created_at"], fact["id"]))

    def get_categories(self) -> List[str]:
        """
        Retourne la liste des catégories ayant au moins un fait.

        Returns:
            Liste triée des catégories utilisées.
        """
        conn = self._get_connection()
        rows = conn.execute(
            "SELECT DISTINCT category FROM facts ORDER BY category"
        ).fetchall()
        return [r["category"] for r in rows]

    # ------------------------------------------------------------------
    # Extraction automatique
    # ------------------------------------------------------------------

    def extract_facts_from_text(
        self,
        text: str,
        source: str = "conversation",
    ) -> List[Dict]:
        """
        Extrait automatiquement des faits depuis un texte libre
        en utilisant des patrons linguistiques français.

        Args:
            text:   Texte à analyser.
            source: Origine du texte (conversation, document, ...).

        Returns:
            Liste des faits extraits (dictionnaires avec id, category, key, value).
        """
        if not text or not text.strip():
            return []

        extracted: List[Dict] = []

        for spec in _EXTRACT_PATTERNS:
            for match in spec["pattern"].finditer(text):
                raw_value = match.group(1).strip()
                if not raw_value:
                    continue

                # Générer une clé lisible à partir du préfixe et d'un résumé
                key = self._build_key(spec["key_prefix"], raw_value)

                fact_id = self.add_fact(
                    category=spec["category"],
                    key=key,
                    value=raw_value,
                    source=source,
                    confidence=0.7,
                )
                extracted.append(
                    {
                        "id": fact_id,
                        "category": spec["category"],
                        "key": key,
                        "value": raw_value,
                    }
                )

        if extracted:
            logger.info(
                "%d fait(s) extrait(s) automatiquement depuis le texte", len(extracted)
            )
        return extracted

    # ------------------------------------------------------------------
    # Contexte pour le prompt
    # ------------------------------------------------------------------

    def select_facts(
        self,
        query: str,
        max_facts: int = 12,
        max_chars: int = 2500,
        include_recent: bool = True,
        facts: Optional[Iterable[Dict]] = None,
    ) -> List[Dict]:
        """
        Choisit les faits à donner au modèle pour une requête.

        D'abord ceux qui partagent des mots avec la requête (casse, accents et
        pluriels ignorés ; le plus de mots en commun d'abord ; pour un fait du
        code, « code » et le nom de son projet en sont, voir _match_text), puis,
        avec include_recent, les plus récemment ajoutés ou modifiés : une relance
        courte (« et lui ? ») garde ainsi l'essentiel de la mémoire.

        Args:
            query:          Requête utilisateur courante.
            max_facts:      Nombre maximum de faits retenus.
            max_chars:      Taille maximale des lignes affichées (format_facts).
            include_recent: Compléter avec les faits récents sans mot commun.
            facts:          Faits parmi lesquels choisir ; par défaut ceux du chat
                            (chat_facts).

        Returns:
            Les faits retenus, du plus utile au moins utile.
        """
        facts = self.chat_facts() if facts is None else list(facts)
        wanted = set(self._match_tokens(query))

        relevant = []
        if wanted:
            for fact in facts:
                shared = wanted & set(self._match_tokens(self._match_text(fact)))
                if shared:
                    relevant.append((len(shared), fact["updated_at"], fact))
            relevant.sort(key=lambda scored: scored[:2], reverse=True)

        candidates = [fact for _, _, fact in relevant]
        if include_recent:
            candidates += sorted(facts, key=lambda f: f["updated_at"], reverse=True)

        selected: List[Dict] = []
        seen = set()
        used = 0
        for fact in candidates:
            if len(selected) >= max_facts:
                break
            if fact["id"] in seen:
                continue
            size = len(self._fact_line(fact))
            if selected and used + size > max_chars:
                continue  # Un fait plus court tient peut-être encore
            seen.add(fact["id"])
            selected.append(fact)
            used += size
        return selected

    @staticmethod
    def _match_text(fact: Dict) -> str:
        """
        Texte d'un fait pour la recherche par mots (select_facts) : sa clé et sa
        valeur, et pour un fait du code, le mot « code » et le nom de son projet.

        Sans eux, « quelles règles de code j'ai données pour My_AI ? », posée
        dans le chat, ne retrouvait pas « je fais mes tests avec pytest »,
        retenu pour ce projet : aucun mot commun. L'outil search_memory donnait
        alors les faits les plus récents, ou le seul fait du chat qui disait
        « code » (« je code en Python »).
        """
        text = f"{fact['key']} {fact['value']}"
        scope, project = fact_scope(fact)
        if scope == SCOPE_PROJECT:
            return f"{text} code {project_name(project)}"
        if scope == SCOPE_CODE:
            return f"{text} code"
        return text

    @classmethod
    def format_facts(cls, facts: List[Dict], with_scope: bool = False) -> List[str]:
        """Une ligne par fait, prête à placer dans un prompt ; with_scope : la
        portée d'un fait qui n'est pas du chat suit le fait (scope_note)."""
        return [cls._fact_line(fact, with_scope) for fact in facts]

    def search_text(self, query: str, n_results: int = 5,
                    facts: Optional[Iterable[Dict]] = None,
                    recent: Optional[Iterable[Dict]] = None) -> str:
        """
        Faits d'un appel de l'outil search_memory, chacun avec sa portée : ceux
        qui partagent des mots avec la requête, sinon les plus récents (« fait
        retenu par l'utilisateur » ne partage aucun mot avec eux : « Aucun
        résultat » faisait croire la mémoire vide). "" sans aucun fait.

        Args:
            facts: Faits parmi lesquels chercher ; par défaut tous (le chat
                trouve à la demande ceux du code).
            recent: Faits proposés quand aucun ne correspond ; par défaut les
                mêmes. La conversation Code n'y met pas ceux du chat : une
                recherche de document y aurait ramené la vie de l'utilisateur.
        """
        pool = self.get_all_facts() if facts is None else list(facts)
        found = self.select_facts(query, max_facts=n_results, include_recent=False, facts=pool)
        header = "Faits mémorisés :"
        if not found:
            fallback = pool if recent is None else list(recent)
            found = self.select_facts(query, max_facts=n_results, facts=fallback)
            header = "Aucun fait ne correspond exactement ; les plus récents :"
        if not found:
            return ""
        return header + "\n" + "\n".join(self.format_facts(found, with_scope=True))

    def get_context_for_prompt(self, query: str, max_facts: int = 5) -> str:
        """
        Construit une chaîne de contexte pertinente à injecter dans un prompt IA
        à partir des faits les plus pertinents pour la requête.

        Args:
            query:     Requête utilisateur courante.
            max_facts: Nombre maximum de faits à inclure.

        Returns:
            Chaîne formatée contenant les faits pertinents, ou chaîne vide
            si aucun fait ne partage de mot avec la requête.
        """
        facts = self.select_facts(query, max_facts=max_facts, include_recent=False)
        if not facts:
            return ""
        return "\n".join(["[Base de connaissances]"] + self.format_facts(facts))

    @staticmethod
    def _match_tokens(text: str) -> List[str]:
        """Mots significatifs d'un texte, sans casse, accents ni pluriel (content_words)."""
        return content_words(text)

    @classmethod
    def is_about_assistant(cls, fact: Dict) -> bool:
        """Le fait est-il une consigne pour l'IA (voir is_assistant_fact) ?"""
        return is_assistant_fact(cls._fact_text(fact))

    @classmethod
    def prompt_text(cls, fact: Dict) -> str:
        """Le fait tel que le modèle doit le lire, sans catégorie ni portée (fact_for_prompt)."""
        return fact_for_prompt(cls._fact_text(fact))

    @classmethod
    def _fact_text(cls, fact: Dict) -> str:
        """Le fait, tronqué au-delà de _FACT_DISPLAY_CHARS, avec sa clé si elle informe."""
        value = str(fact.get("value", "")).strip()
        if len(value) > _FACT_DISPLAY_CHARS:
            value = value[:_FACT_DISPLAY_CHARS].rstrip() + "…"
        key = str(fact.get("key", "")).strip()
        return f"{key}: {value}" if cls._key_adds_info(key, value) else value

    @classmethod
    def _fact_line(cls, fact: Dict, with_scope: bool = False) -> str:
        """
        « - [catégorie] fait », tel que le modèle doit le lire (fact_for_prompt) ;
        with_scope : suivi de sa portée s'il n'est pas du chat.

        Un fait à la première personne passe à la troisième : nu dans le prompt
        système (« je suis Nicolas Gouy »), le modèle le prenait pour lui et
        répondait « Je suis Nicolas Gouy » à « qui je suis ? ».
        """
        line = f"- [{fact.get('category', 'general')}] {fact_for_prompt(cls._fact_text(fact))}"
        note = scope_note(fact) if with_scope else ""
        if note:
            line += f" ({note})"
        try:
            confidence = float(fact.get("confidence", 1.0))
        except (TypeError, ValueError):
            confidence = 1.0
        if confidence < 1.0:
            line += f" (confiance: {int(confidence * 100)}%)"
        return line

    @staticmethod
    def _key_adds_info(key: str, value: str) -> bool:
        """
        La clé dit-elle autre chose que la valeur ? Une clé tirée du début de
        la valeur (ajout depuis la fenêtre Mémoire ou le chat, extraction
        automatique « préfixe: début ») ne ferait que la répéter.
        """
        normalized_key = _normalize(key).rstrip(".… ")
        if not normalized_key:
            return False
        if ": " in normalized_key:
            normalized_key = normalized_key.split(": ", 1)[1]
        normalized_value = _normalize(value)
        return not (
            normalized_value.startswith(normalized_key)
            or normalized_key in normalized_value
        )

    # ------------------------------------------------------------------
    # Utilitaires internes
    # ------------------------------------------------------------------

    @staticmethod
    def _build_key(prefix: str, value: str, max_length: int = 80) -> str:
        """
        Construit une clé descriptive à partir d'un préfixe et d'une valeur.

        Args:
            prefix:     Préfixe de catégorie.
            value:      Valeur brute extraite.
            max_length: Longueur maximale de la clé.

        Returns:
            Clé tronquée et nettoyée.
        """
        # Prendre les premiers mots significatifs de la valeur
        words = value.split()[:6]
        summary = " ".join(words)
        key = f"{prefix}: {summary}"
        if len(key) > max_length:
            key = key[: max_length - 3] + "..."
        return key

    def close(self) -> None:
        """Ferme la connexion SQLite du thread courant."""
        if hasattr(self._local, "connection") and self._local.connection is not None:
            self._local.connection.close()
            self._local.connection = None
            logger.info("Connexion à la base de connaissances fermée")

    def __del__(self) -> None:
        """Ferme proprement la connexion à la destruction de l'objet."""
        try:
            self.close()
        except Exception:
            pass
