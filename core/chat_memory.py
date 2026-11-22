"""
Mémoire de My_AI dans le chat (fenêtre et téléphone : AIEngine.process_query_stream),
comme dans la conversation Code (core/code_memory.py) : le modèle du chat lit ce
qu'un message change dans la mémoire, retenir, remplacer ou oublier.

  - Demande (« retiens que… », « oublie que… », « retiens plutôt que… ») : faite
    avant la réponse, qui la confirme (bloc MÉMORISATION du prompt, AIEngine).
  - Sans demande : ce qu'il dit de durable sur lui ou sur la façon dont il veut
    qu'on lui réponde (« j'habite à Lyon », « réponds-moi plus court ») est retenu,
    lu pendant la réponse, sans la retarder. Un fait qu'il contredit est remplacé ;
    rien d'autre n'est supprimé.
  - Seul son message compte, jamais une page web, un fichier lu ni un résultat
    d'outil : le modèle n'a plus d'outil pour écrire dans la mémoire.

Ce qui est retenu va au chat (portée « chat »). Une demande d'oubli vise aussi les
faits du code, que la fenêtre Mémoire montre de même.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

from core.code_memory import MemoryReader, MemoryUpdate, Reading, apply_reading, rereader
from core.knowledge_base_manager import (
    SCOPE_CHAT,
    SCOPE_PROJECT,
    asks_to_forget,
    asks_to_remember,
    content_words,
    extract_remember_request,
    fact_scope,
    is_assistant_fact,
    project_name,
)
from core.memory_languages import word_count

logger = logging.getLogger(__name__)

# Faits montrés au modèle qui lit le message (les plus récents)
_MAX_KNOWN_FACTS = 40
# Sans demande : un message de moins de trois mots (« ok merci ») n'est pas lu, ni
# un long texte collé, qui parle rarement de lui (et un article qui dit « j'habite
# à Paris » n'est pas lui)
_MIN_SPONTANEOUS_WORDS = 3
_MAX_SPONTANEOUS_CHARS = 1500
# Sans demande, une consigne pour l'IA (« tu dois… ») tirée d'une question qui ne la
# dit pas durable est sa demande du moment : « Je travaille de nuit, tu as des
# conseils pour dormir ? » donnait « tu dois me donner des conseils pour dormir »
_LASTING_RE = re.compile(
    r"(?<![\w'’])(?:toujours|jamais|d[ée]sormais|dor[ée]navant|[àa]\s+partir\s+de\s+"
    r"maintenant|[àa]\s+l['’]avenir|chaque\s+fois|always|never|from\s+now\s+on)(?![\w'’])",
    re.IGNORECASE,
)
# Sans demande, ni code ni mot de passe (« le code de mon casier est le 4815 ») : il
# dira « retiens ça » s'il veut qu'on les garde. Le lecteur retenait ceux d'un message
# sans autre fait connu (un casier, un digicode, le mot de passe du wifi) ; le lui
# interdire dans sa consigne déplaçait ses autres réponses (« tu dois me donner des
# conseils pour dormir », de « je travaille de nuit, tu as des conseils pour
# dormir ? »). « Je code en Python », « j'écris du code propre » et un code postal
# restent
_SECRET_RE = re.compile(
    r"(?<![\w'’])(?:mots?\s+de\s+passe|digicodes?|passwords?|passcodes?|pin"
    r"|(?:le|la|les|mon|ma|mes|ton|ta|tes|son|sa|ses|un|ce|cet|l['’])\s*codes?"
    r"(?!\s+postal)"
    # Les mots de passe des dix autres langues (core/memory_languages.py)
    r"|contrase[ñn]as?|passw[öo]rter|passwort|kennw[öo]rter|kennwort|senhas?"
    r"|wachtwoord(?:en)?|парол(?:ь|и|я|ем)|كلمة\s+(?:المرور|السر)|كلمات\s+المرور"
    r")(?![\w'’])"
    r"|密码|密碼|口令|パスワード|暗証番号|비밀번호|패스워드",
    re.IGNORECASE,
)
# Ce qu'il dit de lui, le modèle l'écrivait parfois à la deuxième personne, en
# reprenant le « tu » de sa question : « tu travailles de nuit » de « Je travaille de
# nuit, tu as des conseils pour dormir ? », « tu parles couramment espagnol » de « Je
# parle couramment espagnol. Tu me conseilles un roman en espagnol ? ». Le fait
# passait pour une consigne pour l'IA, écartée d'une question : il est repris de son
# message (_in_own_words). Sujet du fait, et ce qui lui répond dans le message
_PERSONS = (
    (re.compile(r"(?:tu\b|t['’])", re.IGNORECASE),
     re.compile(r"(?<![\w'’])(?:je\b|j['’])", re.IGNORECASE)),
    (re.compile(r"(?:ton|ta|tes)\b", re.IGNORECASE),
     re.compile(r"(?<![\w'’])(?:mon|ma|mes)\b", re.IGNORECASE)),
)
_SECOND_PERSON_WORD_RE = re.compile(r"(?<![\w'’])(?:(?:tu|te|toi|ton|ta|tes)\b|t['’])",
                                    re.IGNORECASE)
_CLAUSE_END_RE = re.compile(r"[.!?;:,()\[\]«»\"“”\n]+")
# Sans demande, ce qu'il cherche est sa demande du moment, même sans « ? » : de « Je
# cherche un roman en espagnol pour ma sœur. », le modèle retenait « je cherche un
# roman en espagnol pour ma sœur », ou en tirait « ma sœur aime les romans en
# espagnol ». Rien de ce qui vient de cette partie du message n'est retenu ; ce qu'il
# dit à côté (« …pour ma sœur, qui vit à Madrid ») reste (_from_a_search). « Je cherche
# à… » (j'essaie de) n'est pas une recherche
_SEARCH_RE = re.compile(
    r"(?<![\w'’])(?:(?:je|on)\s+(?:re)?cherche|nous\s+(?:re)?cherchons)\b(?!\s+[àa]\s)"
    r"|(?<![\w'’])[àa]\s+la\s+recherche\s+d",
    re.IGNORECASE,
)
# Les parties d'un message : ses propositions, et ce que relient « et », « mais »,
# « qui »…
_PART_RE = re.compile(r"[.!?;:,()\[\]«»\"“”\n]+|\s(?:et|mais|car|donc|qui|parce\s+que|puisque)\s",
                      re.IGNORECASE)

_CHAT_ASKED_SYSTEM = (
    "Tu tiens la mémoire de My_AI, un assistant personnel. Le dernier message de "
    "l'utilisateur te demande de retenir, de remplacer ou d'oublier quelque chose : "
    "dis quoi.\n"
    "\n"
    "Réponds seulement par un objet JSON : {\"remember\": [\"…\"], \"forget\": [numéros]}.\n"
    "\n"
    "remember : les informations à retenir, une phrase chacune.\n"
    "- S'il renvoie à une information de la liste « Déjà retenu », recopie-la exactement "
    "comme elle y est écrite.\n"
    "- S'il renvoie à autre chose qui précède (« retiens ça », « garde ça en tête »), "
    "écris-le comme lui le dirait. Dans les messages de l'assistant, « tu » désigne "
    "l'utilisateur : écris « je ».\n"
    "- Sinon, garde ses mots et sa personne : « je… » quand il parle de lui, « tu… » pour "
    "une consigne qu'il te donne (« tu dois me répondre en anglais »).\n"
    "- Jamais ce qu'il te demande de faire maintenant (« cherche la météo », « écris un "
    "poème »), même écrit comme déjà fait. Ne réponds jamais à sa place.\n"
    "\n"
    "forget : les numéros des informations de « Déjà retenu » qu'il demande d'oublier, ou "
    "que sa nouvelle information remplace (la nouvelle va alors dans remember). Aucun "
    "autre numéro.\n"
    "\n"
    "Listes vides s'il n'y a rien à retenir ni à oublier.\n"
    "\n"
    "Exemples, avec « 1. (chat) j'habite à Lyon » dans « Déjà retenu » :\n"
    "- « non, retiens plutôt que j'habite à Nantes » → {\"remember\": [\"j'habite à "
    "Nantes\"], \"forget\": [1]}\n"
    "- « oublie où j'habite » → {\"remember\": [], \"forget\": [1]}\n"
    "- « retiens que mon frère s'appelle Paul et écris-lui un poème » → {\"remember\": "
    "[\"mon frère s'appelle Paul\"], \"forget\": []}"
)

_CHAT_SPONTANEOUS_SYSTEM = (
    "Tu tiens la mémoire de My_AI, un assistant personnel. Lis le dernier message de "
    "l'utilisateur : dit-il quelque chose de durable sur lui (son nom, ses proches, son "
    "métier, où il vit, ses goûts, ses habitudes) ou sur la façon dont il veut que tu lui "
    "répondes (langue, ton, longueur, ton nom) ? « je m'appelle Camille », « mon chat "
    "s'appelle Félix », « je suis végétarien », « réponds-moi toujours en anglais ».\n"
    "\n"
    "Réponds seulement par un objet JSON : {\"remember\": [\"…\"], \"forget\": [numéros]}.\n"
    "\n"
    "remember : ces informations durables, une phrase chacune, écrite comme lui la dirait : "
    "« je… », « mon… » quand il parle de lui ; « tu dois… » pour une consigne qu'il te "
    "donne. Rien d'autre : ni ce qu'il te demande "
    "de faire (« cherche… », « écris… »), ni une question, ni ce qui ne vaut que pour "
    "l'instant (« je suis fatigué ce soir »), ni ce que dit un texte qu'il colle ou une "
    "page qu'il cite, ni une information générale sur le monde. Dans le doute, rien.\n"
    "\n"
    "forget : les numéros des informations de « Déjà retenu » que son message contredit "
    "et remplace ; la nouvelle va alors dans remember. Aucun autre numéro.\n"
    "\n"
    "La plupart des messages ne contiennent rien à retenir : {\"remember\": [], "
    "\"forget\": []}."
)
# Ses exemples, lus comme des échanges (faits connus, message, réponse) avant le vrai
# message (MemoryReader.SPONTANEOUS_EXAMPLES). Écrits dans la consigne, sous « avec
# « 1. (chat) j'habite à Lyon » dans « Déjà retenu » », ils se confondaient avec la
# vraie liste : dès qu'un fait était connu, le modèle ne retenait presque plus rien
# (« je travaille de nuit », pourtant son premier exemple, avec « j'habite à
# Toulouse » retenu). Sonde de 72 cas tenus à l'écart des exemples, deux fois
# chacun, jugés après les filtres d'update et d'apply_reading : informations
# durables retenues 24 fois sur 96 avant, 74 avec, sans rien retenir des messages
# qui n'en donnent pas (38 sur 40 avant, 40 avec)
_CHAT_SPONTANEOUS_EXAMPLES = (
    ((("chat", "j'aime le jazz"),), "je suis kiné, tu connais des étirements pour le dos ?",
     {"remember": ["je suis kiné"], "forget": []}),
    # Une langue qu'il parle. Sans lui, dès qu'un fait était connu, le modèle n'en
    # retenait presque aucune (« je parle couramment espagnol » : 4 fois sur 16), ou
    # recopiait la consigne de l'exemple « réponds-moi en anglais ». Une adresse parmi les
    # faits connus : avec un seul fait (« j'ai deux enfants »), il proposait de retirer
    # « j'habite à Toulouse » chaque fois qu'il retenait autre chose
    ((("chat", "j'habite à Lille"), ("chat", "j'ai deux enfants")),
     "je parle couramment le russe, tu me conseilles un film russe ?",
     {"remember": ["je parle couramment le russe"], "forget": []}),
    ((("chat", "j'habite à Lyon"),), "j'ai déménagé à Nantes le mois dernier",
     {"remember": ["j'habite à Nantes"], "forget": [1]}),
    # Même sujet, rien de contredit : sans lui, le modèle proposait de retirer un fait
    # sans rapport pour 21 informations retenues sur 96, 13 avec
    ((("chat", "j'ai un chat qui s'appelle Moka"),), "j'ai aussi un chien, il s'appelle Rex",
     {"remember": ["j'ai un chien qui s'appelle Rex"], "forget": []}),
    ((), "à partir de maintenant, réponds-moi en anglais",
     {"remember": ["tu dois toujours me répondre en anglais"], "forget": []}),
    ((("chat", "j'habite à Lyon"),), "quel temps fera-t-il à Nantes demain ?",
     {"remember": [], "forget": []}),
)


def _chat_prompt(message: str, context: Sequence[Tuple[str, str]],
                 known: Sequence[Tuple[str, str]], _project: str = "") -> str:
    """Ce que le modèle lit : les faits retenus, numérotés, les échanges précédents
    (pour une demande), puis le message."""
    lines = ["Déjà retenu :" if known else "Déjà retenu : rien"]
    lines.extend(f"{number}. ({where}) {value}"
                 for number, (where, value) in enumerate(known, 1))
    if context:
        lines += ["", "Échanges précédents :"]
        lines.extend(f"{who} : {text}" for who, text in context)
    if len(message) > 4000:
        message = message[:4000] + "…"
    lines += ["", "Dernier message de l'utilisateur :", message]
    return "\n".join(lines)


class ChatMemoryReader(MemoryReader):
    """Ce qu'un message du chat change dans la mémoire, lu par le modèle du chat."""

    ASKED_SYSTEM = _CHAT_ASKED_SYSTEM
    SPONTANEOUS_SYSTEM = _CHAT_SPONTANEOUS_SYSTEM
    SPONTANEOUS_EXAMPLES = _CHAT_SPONTANEOUS_EXAMPLES

    @staticmethod
    def prompt(message: str, context: Sequence[Tuple[str, str]],
               known: Sequence[Tuple[str, str]], project: str) -> str:
        return _chat_prompt(message, context, known, project)


def _known_lines(known: Sequence[Dict[str, Any]]) -> List[Tuple[str, str]]:
    """Faits montrés au modèle, (d'où ils viennent, texte)."""
    lines = []
    for fact in known:
        scope, folder = fact_scope(fact)
        if scope == SCOPE_CHAT:
            where = "chat"
        elif scope == SCOPE_PROJECT:
            where = f"code, projet {project_name(folder)}"
        else:
            where = "code, tous ses projets"
        lines.append((where, str(fact.get("value") or "")))
    return lines


def _in_own_words(fact: str, message: str) -> str:
    """
    fact, écrit à la deuxième personne (« tu travailles de nuit », « ton fils s'appelle
    Hugo »), tel que son message le dit à la première (« Je travaille de nuit, tu as des
    conseils pour dormir ? » → « je travaille de nuit ») : du sujet (« je », « mon »…)
    jusqu'au dernier des mots du fait qu'il y emploie, dans la même proposition et
    avant tout « tu » (« je veux que tu me répondes en anglais » reste une consigne).
    Il doit y employer les deux tiers au moins des mots qui comptent du fait. Sinon,
    fact tel quel.
    """
    for you_re, me_re in _PERSONS:
        if you_re.match(fact):
            break
    else:
        return fact
    # « tu es », « tu as » : des mots trop courts pour compter ; « tu vas », « je vais »
    wanted = {"vai" if word == "vas" else word for word in content_words(fact)}
    if not wanted:
        return fact
    for clause in _CLAUSE_END_RE.split(message):
        for subject in me_re.finditer(clause):
            said = clause[subject.start():]
            you = _SECOND_PERSON_WORD_RE.search(said)
            if you is not None:
                said = said[:you.start()]
            # Les deux tiers de ses mots au moins : il reformule parfois (« tu
            # travailles en télétravail » de « je suis en télétravail »)
            found = wanted & set(content_words(said))
            if 3 * len(found) < 2 * len(wanted):
                continue
            for word in re.finditer(r"\S+", said):
                words = said[:word.end()]
                if found <= set(content_words(words)):
                    return words[:1].lower() + words[1:]
    return fact


def _said_of_himself(message: str) -> str:
    """Ce que son message dit de lui, sans sa question : ses propositions qui commencent
    par « je » ou « mon, ma, mes », sans « tu » (« Je travaille de nuit, tu as des
    conseils pour dormir ? » → « Je travaille de nuit. »)."""
    said = [clause.strip() for clause in _CLAUSE_END_RE.split(message)]
    said = [clause for clause in said
            if any(me_re.match(clause) for _you_re, me_re in _PERSONS)
            and not _SECOND_PERSON_WORD_RE.search(clause) and not _SEARCH_RE.search(clause)]
    return " ".join(clause + "." for clause in said)


def _from_a_search(fact: str, message: str) -> bool:
    """
    Le fait vient-il de ce qu'il cherche (« je cherche un roman en espagnol pour ma
    sœur ») ? Oui si les parties du message qui ont le plus de ses mots le cherchent
    toutes : « ma sœur vit à Madrid », de « Je cherche un roman pour ma sœur, qui vit à
    Madrid », vient de « qui vit à Madrid ».
    """
    if not _SEARCH_RE.search(message):
        return False
    wanted = set(content_words(fact))
    shares = [(len(wanted & set(content_words(part))), part)
              for part in _PART_RE.split(message) if part.strip()]
    best = max((shared for shared, _part in shares), default=0)
    return best > 0 and all(_SEARCH_RE.search(part) for shared, part in shares
                            if shared == best)


def _read(reader: Any, text: str, message: str, context: Sequence[Tuple[str, str]],
          lines: Sequence[Tuple[str, str]], asked: bool, how: str) -> Reading:
    """Ce que le modèle lit de text (le message, ou ce qu'il dit de lui), ce qu'il dit de
    lui repris des mots de message (_in_own_words) ; rien sans modèle, ou s'il échoue."""
    if reader is None:
        return Reading()
    try:
        reading = reader(text, list(context), lines, "", asked)
    except Exception as exc:  # pylint: disable=broad-except
        logger.warning("Chat : le modèle n'a pas lu la mémoire (%s)", exc)
        return Reading()
    logger.info("Chat : mémoire lue par le modèle (%s) : retenir %s, oublier %s", how,
                [fact[:60] for fact in reading.remember], reading.forget)
    for index, fact in enumerate(reading.remember):
        own = _in_own_words(fact, message)
        if own != fact:
            logger.info("Chat : « %s » repris de son message : « %s »", fact[:80], own[:80])
            reading.remember[index] = own
    return reading


def _drop_unwanted(reading: Reading, message: str) -> List[str]:
    """
    Sans demande, retire de reading ce qui ne se retient pas : une consigne tirée d'une
    question qui ne la dit pas durable (sa demande du moment), ce qui vient de ce qu'il
    cherche, un code ou un mot de passe. Renvoie les consignes tirées d'une question.
    """
    question = "?" in message and not _LASTING_RE.search(message)
    momentary = []
    for fact in list(reading.remember):
        if question and is_assistant_fact(fact):
            logger.info("Chat : « %s » est sa demande du moment, pas une consigne : "
                        "pas retenu", fact[:80])
            reading.remember.remove(fact)
            momentary.append(fact)
        elif _from_a_search(fact, message):
            logger.info("Chat : « %s » vient de ce qu'il cherche, sa demande du moment : "
                        "pas retenu", fact[:80])
            reading.remember.remove(fact)
        elif _SECRET_RE.search(fact):
            logger.info("Chat : « %s » est un code, retenu seulement sur demande", fact[:80])
            reading.remember.remove(fact)
    return momentary


class ChatMemory:
    """Ce qu'un message du chat change dans la mémoire de My_AI."""

    def __init__(self, knowledge_base: Any,
                 auto_extract: Optional[Callable[[], bool]] = None,
                 reader: Optional[Callable[[Optional[Dict[str, Any]]], Any]] = None):
        """
        Args:
            knowledge_base: KnowledgeBaseManager (faits SQLite).
            auto_extract: réglage knowledge_base.auto_extract : My_AI mémorise-t-il
                depuis les conversations ?
            reader: pour le modèle du chat (chat_url, model, num_ctx), ce qui lit ce
                qu'un message change (ChatMemoryReader.for_llm) ; sans lui, seules
                les demandes « retiens que… », lues par des règles.
        """
        self._kb = knowledge_base
        self._auto_extract = auto_extract or (lambda: True)
        self._reader = reader

    @staticmethod
    def asks(message: str) -> bool:
        """Le message demande-t-il de retenir ou d'oublier quelque chose ? La mémoire
        change alors avant la réponse, qui le confirme."""
        return bool(message) and (asks_to_remember(message) or asks_to_forget(message))

    def update(self, message: str, context: Sequence[Tuple[str, str]] = (),
               llm: Optional[Dict[str, Any]] = None, asked: Optional[bool] = None,
               wanted: Optional[Callable[[], bool]] = None) -> Optional[MemoryUpdate]:
        """
        Ce que le message change dans la mémoire, fait (voir CodeMemory.update) : ce
        qui est retenu va au chat ; une demande d'oubli vise aussi les faits du code.

        Returns:
            None si le message ne change rien et ne demandait rien ; sinon ce qui a
            changé (une demande sans effet : unclear, missing ou failed).
        """
        if not message or not self._auto_extract():
            return None
        if asked is None:
            asked = self.asks(message)
        if not asked and (word_count(message) < _MIN_SPONTANEOUS_WORDS
                          or len(message) > _MAX_SPONTANEOUS_CHARS):
            return None
        reader = self._reader(llm) if self._reader is not None and llm else None
        if not asked and reader is None:
            return None
        facts = self._kb.get_all_facts()
        known = (facts if asked
                 else [fact for fact in facts if fact_scope(fact)[0] == SCOPE_CHAT])
        shown = sorted(known, key=lambda fact: str(fact.get("updated_at") or ""))
        shown = shown[-_MAX_KNOWN_FACTS:]
        lines = _known_lines(shown)
        reading = _read(reader, message, message, list(context) if asked else [], lines, asked,
                        "demande" if asked else "sans demande")
        if not asked:
            momentary = _drop_unwanted(reading, message)
            said = _said_of_himself(message) if momentary and not reading.remember else ""
            if len(said.split()) >= _MIN_SPONTANEOUS_WORDS:
                # « Je travaille de nuit, tu as des conseils pour dormir ? » : le modèle
                # n'en tirait parfois que sa demande du moment (« tu dois me donner des
                # conseils pour dormir »), écartée. Relu sans sa question, il ne reste
                # que ce qu'il dit de lui (« Je travaille de nuit. »)
                again = _read(reader, said, message, [], lines, False, "relu sans sa question")
                _drop_unwanted(again, message)
                if again.remember:
                    reading = again
        return apply_reading(
            self._kb, message, reading, known, shown, asked=asked, scope=SCOPE_CHAT,
            context=context, rules=lambda text: (extract_remember_request(text), SCOPE_CHAT),
            source="conversation", wanted=wanted, label="Chat",
            confirm=getattr(reader, "confirm", None), reread=rereader(reader, message, lines, ""))


def chat_memory_for(engine: Any) -> Optional[ChatMemory]:
    """Mémoire du chat, de l'AIEngine de l'appli (None sans base de faits)."""
    knowledge_base = getattr(engine, "knowledge_base", None)
    if knowledge_base is None:
        return None
    return ChatMemory(knowledge_base,
                      auto_extract=getattr(engine, "_memory_auto_extract", None),
                      reader=ChatMemoryReader.for_llm)
