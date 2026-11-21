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
    extract_remember_request,
    fact_scope,
    is_assistant_fact,
    project_name,
)

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
    r"(?!\s+postal))(?![\w'’])",
    re.IGNORECASE,
)

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
        if not asked and (len(message.split()) < _MIN_SPONTANEOUS_WORDS
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
        reading = Reading()
        if reader is not None:
            try:
                reading = reader(message, list(context) if asked else [], lines, "", asked)
                logger.info("Chat : mémoire lue par le modèle (%s) : retenir %s, oublier %s",
                            "demande" if asked else "sans demande",
                            [fact[:60] for fact in reading.remember], reading.forget)
            except Exception as exc:  # pylint: disable=broad-except
                logger.warning("Chat : le modèle n'a pas lu la mémoire (%s)", exc)
                reading = Reading()
        if not asked:
            question = "?" in message and not _LASTING_RE.search(message)
            for fact in list(reading.remember):
                if question and is_assistant_fact(fact):
                    logger.info("Chat : « %s » est sa demande du moment, pas une consigne : "
                                "pas retenu", fact[:80])
                    reading.remember.remove(fact)
                elif _SECRET_RE.search(fact):
                    logger.info("Chat : « %s » est un code, retenu seulement sur demande",
                                fact[:80])
                    reading.remember.remove(fact)
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
