"""
Mémoire de My_AI dans la conversation Code (relay/code_hub.py) : l'extension
VS Code, la page Code du PC et la vue Code du téléphone.

Elle est cloisonnée par portée (core/knowledge_base_manager.py, SCOPES) :
  - les faits retenus pour le code (« code » : tous les projets ; « project » :
    l'un des dossiers ouverts dans VS Code) vont d'office dans le prompt système
    (prompt_block). Ceux du chat (nom, famille, consignes de ton…) n'y vont pas :
    un modèle qui les a sous les yeux les place n'importe où, jusque dans les
    fichiers qu'il écrit (« Auteur : … Chat : … » en tête d'un script de tri,
    voir AIEngine._generation_memory) ;
  - ce qu'un message change dans cette mémoire (update) : le modèle de la
    conversation lit quoi retenir, remplacer ou oublier (MemoryReader). Quand
    l'utilisateur le demande (« retiens que… », « oublie que… », « retiens
    plutôt que… »), il doit agir, avant la réponse, qui le confirme. Sinon, il
    peut retenir de lui-même une préférence durable (« j'utilise toujours
    black »), pendant la réponse, sans la retarder, et la mettre à la place
    d'un fait qu'elle contredit ; jamais rien supprimer d'autre. Seul le message
    de l'utilisateur compte, jamais un fichier du workspace ni un résultat
    d'outil : une phrase glissée dans un README ne peut pas écrire dans sa
    mémoire, que le chat applique ensuite en priorité. Une carte montre chaque
    changement. Pour quels projets : les mots du message (le premier dossier
    ouvert, sauf « pour tous mes projets ») ;
  - l'outil search_memory, exécuté sur le PC (search) : faits du chat, du code
    et de ces dossiers, et documents de la fenêtre Mémoire.
"""

from __future__ import annotations

import json
import logging
import re
import unicodedata
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

import requests

from core.knowledge_base_manager import (
    SCOPE_CODE,
    SCOPE_PROJECT,
    asks_to_forget,
    asks_to_remember,
    content_words,
    extract_remember_request,
    fact_for_prompt,
    fact_scope,
    is_only_remember_request,
    is_rememberable,
    memorization_confirmation,
    only_asks_to_forget,
    only_asks_to_remember,
    project_name,
    remember_block,
)

logger = logging.getLogger(__name__)

# Retenu pour tous ses projets : « retiens pour tous mes projets que… »,
# « … dans tous mes repos », « remember for all my projects that… ».
# « partout » n'en est pas : « je veux des logs partout » parle du code.
_ALL_PROJECTS_RE = re.compile(
    r"(?<![\w'’])(?:"
    r"(?:pour|dans|sur)\s+(?:tous|toutes)\s+(?:mes|les|nos)\s+"
    r"(?:projets|repos|d[ée]p[ôo]ts|codes|workspaces)"
    r"|(?:for|in|across)\s+(?:all|every)\s+(?:of\s+)?(?:my\s+|the\s+|our\s+)?"
    r"(?:projects?|repos(?:itories)?|codebases?|workspaces?)"
    r")(?![\w'’])",
    re.IGNORECASE,
)
# Pour ce projet, ce qui est de toute façon le cas : la précision quitte le fait
_THIS_PROJECT_RE = re.compile(
    r"(?<![\w'’])(?:"
    r"(?:pour|dans|sur)\s+(?:ce|le)\s+(?:projet|repo|d[ée]p[ôo]t|workspace)(?:-ci|-l[àa])?"
    r"|(?:for|in)\s+this\s+(?:project|repo(?:sitory)?|codebase|workspace)"
    r")(?![\w'’])",
    re.IGNORECASE,
)
# Faits déjà retenus montrés au modèle qui lit le message (les plus récents), et
# début du message qu'il lit : un long code collé ne ralentit pas la réponse
_MAX_KNOWN_FACTS = 40
_READ_MESSAGE_CHARS = 4000
# Informations qu'il peut retenir d'un message
_MAX_READ_FACTS = 5
# Sans demande : un message de moins de trois mots (« ok », « merci ») n'est pas
# lu, et deux faits au plus sont remplacés
_MIN_SPONTANEOUS_WORDS = 3
_MAX_SPONTANEOUS_FORGET = 2
# Demande d'oubli qui parle de la mémoire, ou d'un fait (« oublie que… ») : rien
# de tel retenu, la note le dit au modèle. « Oublie ça, fais plutôt… » n'en a pas.
_FORGET_FACT_RE = re.compile(
    r"m[ée]moire|retenu|memory|remember|(?<![\w'’-])oublie[sz]?\s+(?:que|qu['’])",
    re.IGNORECASE,
)


def _plain(text: str) -> str:
    """Minuscules sans accents ni ponctuation aux bords, pour comparer deux phrases."""
    decomposed = unicodedata.normalize("NFKD", text or "")
    flat = "".join(c for c in decomposed if not unicodedata.combining(c)).casefold()
    return re.sub(r"\s+", " ", flat).strip(" ,.;:!?")


# « tu » de l'assistant ramené au « je » de l'utilisateur, pour comparer (_loose)
_FIRST_PERSON = {"tu": "je", "t": "j", "te": "me", "toi": "moi", "ton": "mon", "ta": "ma",
                 "tes": "mes", "you": "i", "your": "my", "yours": "mine"}


def _loose(text: str) -> str:
    """
    Une phrase sans casse, accents, ponctuation, pluriels ni deuxième personne :
    « Je fais mes tests. », « je fais mes test » et « tu fais tes tests » (le
    modèle reprend parfois la confirmation de l'assistant) sont la même
    information. Les petits mots restent : « je n'utilise pas pytest » n'est
    pas « j'utilise pytest ».
    """
    words = [_FIRST_PERSON.get(word, word) for word in re.findall(r"\w+", _plain(text))]
    return " ".join(word[:-1] if len(word) > 3 and word[-1] in "sx" else word for word in words)


def _without_scope(message: str) -> str:
    """Le message sans « pour tous mes projets » ni « pour ce projet »."""
    for pattern in (_ALL_PROJECTS_RE, _THIS_PROJECT_RE):
        message = pattern.sub(" ", message)
    return re.sub(r"[ \t]+", " ", message).strip()


def _trim_scope(fact: str) -> str:
    """
    Le fait lu par le modèle sans la précision de portée qui l'ouvre ou le ferme :
    « dans ce projet, les noms de variables sont en anglais », retenu pour tous
    les projets, se contredisait. Au milieu de la phrase, elle en fait partie.
    """
    for pattern in (_ALL_PROJECTS_RE, _THIS_PROJECT_RE):
        for match in pattern.finditer(fact):
            before, after = fact[:match.start()], fact[match.end():]
            if not before.strip(" ,;:") or not after.strip(" ,;:.!"):
                fact = (before.rstrip(" ,;:") + " " + after.lstrip(" ,;:")).strip()
                break
    return fact.rstrip(" ,;:")


def _clean_fact(text: str) -> str:
    """Une information lue par le modèle, nettoyée ; "" si ce n'en est pas une
    (« rien », que le vrai modèle écrivait parfois au lieu d'une liste vide)."""
    fact = re.sub(r"\s+", " ", text).strip().rstrip(" ?!.;,:")
    if len(fact) > 1 and fact[0] in "\"'«“`" and fact[-1] in "\"'»”`":
        fact = fact[1:-1].strip().rstrip(" ?!.;,:")
    fact = _trim_scope(fact)
    return fact if is_rememberable(fact) else ""


def _grounded(fact: str, sources: Sequence[str], strict: bool = True) -> bool:
    """
    Les mots qui comptent dans fact viennent de sources, ce que l'utilisateur a
    écrit (la moitié au moins, strict ; un au moins sinon) : ce que le modèle
    retient ne peut pas venir d'un fichier ni d'une réponse qu'il invente (la
    deuxième personne et les pluriels comptent comme le reste, content_words
    les ramène au même mot).
    """
    words = set(content_words(fact))
    if not words:
        return False
    shared = len(words & set(content_words(" ".join(sources))))
    return 2 * shared >= len(words) if strict else shared >= 1


# Une tâche, même écrite comme faite, n'est pas une information à retenir : le
# vrai modèle retenait « j'ai ajouté une route /health dans app.py » de « retiens
# que le port est 8000 et ajoute une route /health ». (Pas l'impératif : « ajoute
# toujours des docstrings » est une consigne durable.)
_DONE_TASK_RE = re.compile(
    r"^(?:j['’]ai|tu\s+as|on\s+a|nous\s+avons|i\s+have|i['’]ve|you\s+have|you['’]ve)\s+"
    r"(?:ajout|cr[ée][ée]|modifi|corrig|supprim|[ée]crit|impl[ée]ment|refactoris|renomm|"
    r"d[ée]plac|install|added|created|fixed|written|wrote|removed|implemented|renamed|"
    r"moved)\w*",
    re.IGNORECASE,
)


def remember_request(message: str) -> Tuple[Optional[str], str, str]:
    """
    Information que le message demande de retenir dans la conversation Code, sa
    portée et le message sans la précision de portée, lus par des règles : sans
    modèle (MemoryReader), ou quand il ne trouve rien.

    « Retiens pour tous mes projets que j'indente avec des tabulations » →
    (« j'indente avec des tabulations », « code », …). La précision (« pour tous
    mes projets », « pour ce projet ») est retirée quand elle suit le verbe ou
    ouvre ou ferme l'information ; au milieu de la phrase, elle en fait partie.

    Returns:
        (information ou None, portée SCOPE_CODE ou SCOPE_PROJECT, message lu)
    """
    raw = extract_remember_request(message)
    for pattern, scope in ((_ALL_PROJECTS_RE, SCOPE_CODE), (_THIS_PROJECT_RE, SCOPE_PROJECT)):
        match = pattern.search(message or "")
        if match is None:
            continue
        text = (message[:match.start()].rstrip(" ,") + " "
                + message[match.end():].lstrip(" ,")).strip()
        fact = extract_remember_request(text)
        phrase = _plain(match.group(0))
        if fact and (raw is None or _plain(raw).startswith(phrase) or _plain(raw).endswith(phrase)):
            return fact, scope, text
    return raw, SCOPE_PROJECT, message


def _asks_nothing_else(message: str, fact: str) -> bool:
    """
    Le message ne demande-t-il que de retenir fact ? La note dit alors au modèle
    de s'en tenir à le confirmer, sans outil. Dans le doute, non : une tâche
    sautée est pire qu'une confirmation suivie d'un mot de trop.
    """
    text = _without_scope(message)
    if fact in text:
        return is_only_remember_request(text, fact)
    written = extract_remember_request(text)
    if written and _loose(written) == _loose(fact):
        # Le modèle a repris ses mots, à la casse ou à un pluriel près
        return is_only_remember_request(text, written)
    # « Retiens-le », « retiens bien ça » : rien d'autre que le renvoi
    return only_asks_to_remember(text)


def _known_wording(fact: str, known: Sequence[Dict[str, Any]]) -> str:
    """
    fact tel qu'il est déjà retenu, s'il l'est à la casse, la ponctuation, un
    pluriel ou la personne près : la base le reconnaît alors
    (KnowledgeBaseManager.remember : rafraîchi, ou étendu à tous les projets)
    au lieu d'en faire un doublon.
    """
    wanted = _loose(fact)
    for item in known:
        if _loose(str(item.get("value") or "")) == wanted:
            return str(item["value"])
    return fact


# ── Ce que le modèle lit d'un message ───────────────────────────────────────

# Sa réponse (format JSON contraint d'Ollama). Pas la portée : le modèle disait
# « tous les projets » sans que le message le dise ; ce sont ses mots qui la
# donnent (CodeMemory.update)
_READ_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "remember": {"type": "array", "items": {"type": "string"}},
        "forget": {"type": "array", "items": {"type": "integer"}},
    },
    "required": ["remember", "forget"],
}

# Le message demande de retenir ou d'oublier : le modèle doit dire quoi
_ASKED_SYSTEM = (
    "Tu tiens la mémoire de My_AI pour la conversation Code d'un développeur. Son "
    "dernier message te demande de retenir, de remplacer ou d'oublier quelque chose : "
    "dis quoi.\n"
    "\n"
    "Réponds seulement par un objet JSON : {\"remember\": [\"…\"], \"forget\": [numéros]}.\n"
    "\n"
    "remember : les informations à retenir, une phrase chacune.\n"
    "- S'il renvoie à une information de la liste « Déjà retenu » (« retiens-le pour "
    "tous mes projets » juste après l'avoir fait retenir), recopie-la exactement comme "
    "elle y est écrite.\n"
    "- S'il renvoie à autre chose qui précède (« retiens ça », « garde ça en tête »), "
    "écris-le comme lui le dirait. Dans les messages de l'assistant, « tu » désigne "
    "l'utilisateur : écris « je ».\n"
    "- Sinon, garde ses mots et sa personne : « je… » quand il parle de lui, « tu… » "
    "pour une consigne qu'il te donne.\n"
    "- Jamais ce qu'il te demande de faire maintenant (« ajoute une route », « corrige "
    "ce bug »), même écrit comme déjà fait (« j'ai ajouté une route ») : c'est une tâche, "
    "pas une information. Ni les mots qui disent pour quels projets. Ne réponds jamais "
    "à sa place.\n"
    "\n"
    "forget : les numéros des informations de « Déjà retenu » qu'il demande d'oublier, "
    "ou que sa nouvelle information remplace (la nouvelle va alors dans remember). "
    "Aucun autre numéro.\n"
    "\n"
    "Listes vides s'il n'y a rien à retenir ni à oublier.\n"
    "\n"
    "Exemples, avec « 1. (projet notes) j'indente avec des tabulations » dans « Déjà "
    "retenu » :\n"
    "- « retiens le pour tous mes projets » → {\"remember\": [\"j'indente avec des "
    "tabulations\"], \"forget\": []}\n"
    "- « non, retiens plutôt que j'indente avec des espaces » → {\"remember\": [\"j'indente "
    "avec des espaces\"], \"forget\": [1]}\n"
    "- « oublie ce que je t'ai dit sur l'indentation » → {\"remember\": [], \"forget\": [1]}\n"
    "- « retiens que la base s'appelle notes.db et crée la table users » → {\"remember\": "
    "[\"la base s'appelle notes.db\"], \"forget\": []}"
)

# Sans demande : le modèle peut retenir une préférence durable, rien d'autre
_SPONTANEOUS_SYSTEM = (
    "Tu tiens la mémoire de My_AI pour la conversation Code d'un développeur. Lis son "
    "dernier message : dit-il, de façon durable, comment il travaille ou veut que son "
    "code soit écrit ? Une préférence, une convention, un outil, une règle de son "
    "projet : « j'utilise toujours black », « dans ce projet les noms sont en anglais », "
    "« mes commits sont en anglais », « le port de l'api est 8000 ».\n"
    "\n"
    "Réponds seulement par un objet JSON : {\"remember\": [\"…\"], \"forget\": [numéros]}.\n"
    "\n"
    "remember : ces informations durables, une phrase chacune, avec ses mots (« je… »). "
    "Rien d'autre : ni la tâche qu'il te demande (« ajoute une route », « corrige ce "
    "bug »), ni une question, ni un détail du travail en cours (un nom de fonction, une "
    "erreur), ni ce qui ne vaut que pour cette demande (« ici, utilise une boucle »). "
    "Dans le doute, rien.\n"
    "\n"
    "forget : les numéros des informations de « Déjà retenu » que son message contredit "
    "et remplace ; la nouvelle va alors dans remember. Aucun autre numéro.\n"
    "\n"
    "Exemple, avec « 1. (projet notes) j'indente avec des tabulations » dans « Déjà "
    "retenu » : « en fait, j'indente avec des espaces maintenant » → {\"remember\": "
    "[\"j'indente avec des espaces\"], \"forget\": [1]}.\n"
    "\n"
    "La plupart des messages ne contiennent rien à retenir : {\"remember\": [], "
    "\"forget\": []}."
)


def _read_prompt(message: str, context: Sequence[Tuple[str, str]],
                 known: Sequence[Tuple[str, str]], project: str) -> str:
    """Ce que le modèle lit d'un message (MemoryReader) : les faits déjà retenus,
    numérotés, les échanges précédents (pour une demande), puis le message."""
    lines = [f"Projet ouvert : {project or 'aucun'}", ""]
    if known:
        lines.append("Déjà retenu :")
        lines.extend(f"{number}. ({where}) {value}"
                     for number, (where, value) in enumerate(known, 1))
    else:
        lines.append("Déjà retenu : rien")
    if context:
        lines += ["", "Échanges précédents :"]
        lines.extend(f"{who} : {text}" for who, text in context)
    if len(message) > _READ_MESSAGE_CHARS:
        message = message[:_READ_MESSAGE_CHARS] + "…"
    lines += ["", "Dernier message de l'utilisateur :", message]
    return "\n".join(lines)


# Ce que le modèle propose de retirer, confirmé fait par fait par un second appel
# court (MemoryReader.confirm) : seul, le vrai modèle retirait des faits sans
# rapport (« oublie que j'ai un chien » retirait « je m'appelle Camille », « réponds-
# moi toujours en anglais » le prénom et le nom du chat). Le second appel a tranché
# juste dans les 17 cas essayés, en 1,4 à 3 s.
_CONFIRM_ASKED_SYSTEM = (
    "Tu tiens la mémoire de My_AI, un assistant personnel. Des informations de la "
    "mémoire de l'utilisateur, numérotées, vont être retirées à cause de son dernier "
    "message. Juge chacune à part. Réponds true seulement si son message demande de "
    "l'oublier (il la désigne : « oublie où j'habite », « oublie tout », « oublie que je "
    "veux des réponses courtes » pour « tu dois me répondre brièvement ») ou si ce qu'il "
    "demande de retenir la rend fausse (même sujet : « j'habite à Nantes » remplace "
    "« j'habite à Lyon ») ; false si elle parle d'autre chose, même d'un sujet voisin "
    "(« oublie que j'ai une voiture » ne vise pas « mon vélo est rouge »)."
)
# « Juge chacune à part » et les deux derniers exemples : avec deux faits à trancher,
# « oublie que j'ai un chien » retirait « mon chat s'appelle Félix », et « oublie que
# je veux des réponses en anglais » gardait la consigne de répondre en anglais
# (34 verdicts justes sur 38, 38 avec)
_CONFIRM_SPONTANEOUS_SYSTEM = (
    "Tu tiens la mémoire de My_AI, un assistant personnel. Des informations de la "
    "mémoire de l'utilisateur, numérotées, vont être retirées à cause de son dernier "
    "message. Pour chacune, réponds true seulement si son message la rend fausse : il dit "
    "autre chose sur le même sujet (« j'ai déménagé à Nantes » rend fausse « j'habite à "
    "Lyon » ; « je code maintenant sous VS Code » rend fausse « j'utilise PyCharm » : deux "
    "outils pour le même usage). « Maintenant », « désormais », « je suis passé à » "
    "annoncent un tel changement : ce qui valait avant pour le même usage ne vaut plus. "
    "Réponds false si elle parle d'autre chose, même s'il dit quelque chose de nouveau sur "
    "lui. Réponds false aussi quand elle reste vraie avec ce qu'il ajoute (« j'ai aussi un "
    "chien » ne rend pas fausse « j'ai un chat »)."
)
# L'exemple des outils : sans lui, le second appel gardait « j'utilise black » pour
# « maintenant je formate avec ruff », et de même jest pour vitest, ou des commits en
# anglais pour des commits en français (16 cas sur 20 tranchés juste, 19 avec).
# « Maintenant », « désormais »… et ce qui s'ajoute : sans eux, il gardait « j'utilise
# unittest » pour « en fait, maintenant j'utilise pytest pour mes tests » et « je suis
# comptable » pour « j'ai changé de métier : je suis boulanger maintenant », et retirait
# « mon chat s'appelle Félix » pour « j'ai adopté un deuxième chat, Moka » (chaque fois).
# Sonde de 27 paires, deux fois chacune : 48 verdicts justes sur 54 avant, 54 avec


def _confirm_prompt(message: str, new: Sequence[str], candidates: Sequence[str],
                    asked: bool) -> str:
    """Ce que lit le second appel (MemoryReader.confirm) : le message, ce qui en est
    retenu, puis les faits qu'il retirerait, numérotés."""
    if len(message) > _READ_MESSAGE_CHARS:
        message = message[:_READ_MESSAGE_CHARS] + "…"
    lines = ["Dernier message de l'utilisateur :", message, ""]
    if new:
        lines.append("Ce qu'il demande de retenir :" if asked else "Ce qui en est retenu :")
        lines.extend(f"- {fact}" for fact in new)
        lines.append("")
    lines.append("Informations qui vont être retirées de sa mémoire :")
    lines.extend(f"{number}. {fact}" for number, fact in enumerate(candidates, 1))
    lines += ["", "Pour chaque numéro, true (à retirer) ou false (à garder)."]
    return "\n".join(lines)


def _known_lines(known: Sequence[Dict[str, Any]]) -> List[Tuple[str, str]]:
    """Faits du code déjà retenus, (pour quoi ils valent, texte), pour _read_prompt."""
    lines = []
    for fact in known:
        scope, folder = fact_scope(fact)
        where = f"projet {project_name(folder)}" if scope == SCOPE_PROJECT else "tous ses projets"
        lines.append((where, str(fact.get("value") or "")))
    return lines


@dataclass
class Reading:
    """Ce que le modèle lit d'un message : les informations à retenir, et les numéros,
    dans la liste qu'il a reçue, des faits à oublier."""

    remember: List[str] = field(default_factory=list)
    forget: List[int] = field(default_factory=list)


class MemoryReader:
    """
    Ce qu'un message change dans la mémoire du code, lu par le modèle de la
    conversation (CodeMemory.update) : un appel court à Ollama, en JSON contraint.
    Le chat a le sien (core/chat_memory.py), avec ses consignes.
    """

    TIMEOUT_SECONDS = 60
    # Consignes : le message demande de retenir ou d'oublier, ou non
    ASKED_SYSTEM = _ASKED_SYSTEM
    SPONTANEOUS_SYSTEM = _SPONTANEOUS_SYSTEM
    CONFIRM_ASKED_SYSTEM = _CONFIRM_ASKED_SYSTEM
    CONFIRM_SPONTANEOUS_SYSTEM = _CONFIRM_SPONTANEOUS_SYSTEM
    # Sans demande : des exemples (faits connus, message, réponse), lus comme des
    # échanges avant le vrai message (le chat : core/chat_memory.py)
    SPONTANEOUS_EXAMPLES: Sequence[Tuple[Sequence[Tuple[str, str]], str, Dict[str, Any]]] = ()

    @staticmethod
    def prompt(message: str, context: Sequence[Tuple[str, str]],
               known: Sequence[Tuple[str, str]], project: str) -> str:
        """Ce que le modèle lit : faits retenus, numérotés, échanges, message."""
        return _read_prompt(message, context, known, project)

    def __init__(self, chat_url: str, model: str, num_ctx: int,
                 post: Optional[Callable[..., Any]] = None):
        self._chat_url = chat_url
        self._model = model
        self._num_ctx = int(num_ctx)
        self._post = post or requests.post

    @classmethod
    def for_llm(cls, llm: Optional[Dict[str, Any]]) -> Optional["MemoryReader"]:
        """Celui du modèle de la conversation Code (chat_url, model, num_ctx), ou None."""
        if not llm or not llm.get("chat_url") or not llm.get("model"):
            return None
        return cls(str(llm["chat_url"]), str(llm["model"]), int(llm.get("num_ctx") or 32768))

    def __call__(self, message: str, context: Sequence[Tuple[str, str]],
                 known: Sequence[Tuple[str, str]], project: str, asked: bool) -> Reading:
        """
        asked : le message demande de retenir ou d'oublier ; sinon, il n'en retient
        qu'une préférence durable, s'il en donne une.

        Raises:
            requests.RequestException, ValueError: modèle injoignable, réponse illisible.
        """
        examples = [] if asked else [
            (self.prompt(said, (), facts, ""), answer)
            for facts, said, answer in self.SPONTANEOUS_EXAMPLES
        ]
        data = self._ask(self.ASKED_SYSTEM if asked else self.SPONTANEOUS_SYSTEM,
                         self.prompt(message, context, known, project), _READ_SCHEMA, 400,
                         examples)
        remember = [fact for fact in (_clean_fact(item) for item in data.get("remember") or []
                                      if isinstance(item, str)) if fact]
        forget = []
        for item in data.get("forget") or []:
            try:
                forget.append(int(item))
            except (TypeError, ValueError):
                continue
        return Reading(remember[:_MAX_READ_FACTS], forget)

    def confirm(self, message: str, new: Sequence[str], candidates: Sequence[str],
                asked: bool) -> List[bool]:
        """
        Les faits que le modèle propose de retirer (candidates), confirmés un par
        un : True pour celui que le message désigne (« oublie que… ») ou rend faux
        (new, ce qui en est retenu, le remplace).

        Raises:
            requests.RequestException, ValueError: modèle injoignable, réponse illisible.
        """
        keys = [str(number) for number in range(1, len(candidates) + 1)]
        schema = {"type": "object", "properties": {key: {"type": "boolean"} for key in keys},
                  "required": keys}
        data = self._ask(self.CONFIRM_ASKED_SYSTEM if asked else self.CONFIRM_SPONTANEOUS_SYSTEM,
                         _confirm_prompt(message, new, candidates, asked), schema,
                         20 + 10 * len(keys))
        return [data.get(key) is True for key in keys]

    def _ask(self, system: str, prompt: str, schema: Dict[str, Any], num_predict: int,
             examples: Sequence[Tuple[str, Dict[str, Any]]] = ()) -> Dict[str, Any]:
        """Un appel court au modèle, sans réflexion, en JSON contraint par schema ;
        examples : (message, réponse) lus comme des échanges avant le vrai."""
        turns: List[Dict[str, str]] = []
        for said, answer in examples:
            turns.append({"role": "user", "content": said})
            turns.append({"role": "assistant",
                          "content": json.dumps(answer, ensure_ascii=False)})
        payload = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": system},
                *turns,
                {"role": "user", "content": prompt},
            ],
            "stream": False,
            "think": False,
            "format": schema,
            "keep_alive": "1h",
            # Même fenêtre de contexte que la conversation : une autre ferait
            # recharger le modèle par Ollama (cf. LocalLLM.gen_num_ctx)
            "options": {"temperature": 0, "num_ctx": self._num_ctx,
                        "num_predict": num_predict, "num_keep": -1},
        }
        response = self._post(self._chat_url, json=payload, timeout=self.TIMEOUT_SECONDS)
        response.raise_for_status()
        content = ((response.json() or {}).get("message") or {}).get("content") or ""
        data = json.loads(content)
        if not isinstance(data, dict):
            raise ValueError(f"Réponse inattendue : {content[:120]!r}")
        return data


@dataclass
class Remembered:
    """Information retenue depuis un message de la conversation Code."""

    fact: str
    fact_id: int
    # Nouvelle (ou désormais valable pour tous les projets), sinon déjà connue
    created: bool
    scope: str
    # Dossier d'un fait de projet ("" pour tous les projets)
    project: str

    def where(self) -> str:
        """Pour quoi elle vaut, dans le prompt du modèle."""
        if self.scope == SCOPE_PROJECT:
            return f"le projet « {project_name(self.project)} »"
        return "tous ses projets"


@dataclass
class Forgotten:
    """Fait retiré de la mémoire : demandé (« oublie que… »), ou remplacé."""

    fact: str
    fact_id: int
    scope: str
    project: str


@dataclass
class MemoryUpdate:
    """Ce qu'un message de la conversation Code a changé dans la mémoire du code."""

    # L'utilisateur l'a demandé (sinon, retenu de lui-même par le modèle)
    asked: bool
    remembered: List[Remembered] = field(default_factory=list)
    forgotten: List[Forgotten] = field(default_factory=list)
    # Le message ne demande rien d'autre
    alone: bool = False
    # Demandé de retenir, sans qu'on sache quoi (« retiens-le » sans rien avant)
    unclear: bool = False
    # Demandé d'oublier, et rien de tel n'est retenu
    missing: bool = False
    # Demandé de retenir, mais ce que le modèle a lu n'a pas pu être gardé (rien de
    # ce que l'utilisateur a écrit, ou une tâche) : rien n'a changé
    failed: bool = False

    @property
    def changed(self) -> bool:
        """La mémoire a-t-elle changé (ou une information demandée y est-elle déjà) ?"""
        return bool(self.remembered or self.forgotten)

    def prompt_note(self) -> str:
        """Note ajoutée à son message pour le modèle, quand l'utilisateur a demandé
        quelque chose : ce qui a été fait, qu'il confirme (sans elle, un petit modèle
        répondait « c'est noté » sans rien avoir enregistré, ou relançait des outils).
        Il la recopiait parfois à la fin de sa réponse : elle le lui interdit. ""
        sans demande, ou pour une demande sans effet qu'il n'a pas à commenter."""
        if not self.asked:
            return ""
        hidden = " Ne recopie pas cette note."
        then = (" Son message ne demande rien d'autre : ta réponse se limite à cela, "
                "sans outil." if self.alone
                else " Puis réponds au reste de son message.")
        if self.unclear:
            return ("[Mémoire] L'utilisateur demande de retenir quelque chose, mais on ne "
                    "sait pas quoi : My_AI n'a rien enregistré. Ne dis pas que c'est noté ; "
                    f"demande-lui en une phrase ce qu'il veut que tu retiennes.{hidden}")
        if self.missing:
            return ("[Mémoire] L'utilisateur demande d'oublier quelque chose, mais My_AI n'a "
                    "rien de tel dans sa mémoire pour son code : rien n'a été retiré. "
                    f"Dis-le-lui en une phrase.{then}{hidden}")
        if self.failed:
            return ("[Mémoire] My_AI n'a pas pu lire ce que l'utilisateur demande de "
                    "retenir : rien n'a changé dans sa mémoire. Ne dis pas que c'est noté ; "
                    f"dis-le-lui en une phrase, et propose-lui de le reformuler.{then}{hidden}")
        new = [item for item in self.remembered if item.created]
        known = [item for item in self.remembered if not item.created]
        done = []
        if self.forgotten:
            done.append("de retirer de sa mémoire : " + " ; ".join(
                f"« {item.fact} »" for item in self.forgotten))
        if new:
            done.append("d'enregistrer dans sa mémoire, " + " ; ".join(
                f"pour {item.where()} : {fact_for_prompt(item.fact)}" for item in new))
        if not done:
            if not known:
                return ""
            return ("[Mémoire] C'était déjà dans la mémoire de My_AI, " + " ; ".join(
                f"pour {item.where()} : {fact_for_prompt(item.fact)}" for item in known)
                + f". Dis-le-lui en une phrase.{then}{hidden}")
        note = "[Mémoire] À la demande de l'utilisateur, My_AI vient " + " et ".join(done) + "."
        if known:
            note += " C'était déjà dans sa mémoire : " + " ; ".join(
                fact_for_prompt(item.fact) for item in known) + "."
        single = len(new) == 1 and not self.forgotten and not known
        confirmation = memorization_confirmation(new[0].fact) if single else None
        example = f" (par exemple : « {confirmation} »)" if confirmation else ""
        return f"{note} Confirme-le-lui en une phrase{example}.{then}{hidden}"


def rereader(reader: Any, message: str, known: Sequence[Tuple[str, str]],
             project: str) -> Optional[Callable[[Sequence[Tuple[str, str]]], Reading]]:
    """La lecture d'une demande par reader (MemoryReader), à refaire sur d'autres
    échanges (apply_reading, reread) ; None sans modèle."""
    if reader is None:
        return None
    return lambda exchanges: reader(message, list(exchanges), known, project, True)


def _confirmed(confirm: Callable[..., List[bool]], message: str, kept: Sequence[str],
               forget: List[Dict[str, Any]], asked: bool, label: str) -> List[Dict[str, Any]]:
    """
    Les faits à retirer que le second appel confirme (apply_reading). Celui qui est
    retenu de nouveau (« retiens-le pour tous mes projets ») ne lui est pas montré :
    il reste de toute façon. Si l'appel échoue, seule une demande d'oubli garde ce
    que le modèle a lu ; sans demande, dans le doute, rien n'est retiré.
    """
    again = {_loose(fact) for fact in kept}
    asked_for = [fact for fact in forget if _loose(str(fact.get("value") or "")) not in again]
    if not asked_for:
        return forget
    values = [str(fact.get("value") or "") for fact in asked_for]
    try:
        verdicts = list(confirm(message, list(kept), values, asked))
    except Exception as exc:  # pylint: disable=broad-except
        logger.warning("%s : retrait non confirmé (%s)", label, exc)
        return forget if asked and asks_to_forget(message) else []
    verdicts += [False] * (len(asked_for) - len(verdicts))
    dropped = {id(fact) for fact, keep in zip(asked_for, verdicts) if not keep}
    for fact in asked_for:
        if id(fact) in dropped:
            logger.info("%s : « %s » n'est pas visé par le message, gardé", label,
                        str(fact.get("value") or "")[:80])
    return [fact for fact in forget if id(fact) not in dropped]


def apply_reading(kb: Any, message: str, reading: Reading, known: Sequence[Dict[str, Any]],
                  shown: Sequence[Dict[str, Any]], *, asked: bool, scope: str,
                  project: str = "", context: Sequence[Tuple[str, str]] = (),
                  rules: Optional[Callable[[str], Tuple[Optional[str], str]]] = None,
                  source: str = "code", wanted: Optional[Callable[[], bool]] = None,
                  label: str = "Conversation Code",
                  confirm: Optional[Callable[..., List[bool]]] = None,
                  reread: Optional[Callable[[Sequence[Tuple[str, str]]], Reading]] = None,
                  ) -> Optional[MemoryUpdate]:
    """
    Ce que le modèle a lu d'un message (reading), vérifié puis écrit dans la base :
    pour la conversation Code (CodeMemory.update) ou pour le chat
    (core/chat_memory.py).

    known : les faits que le message peut viser ; shown : ceux que le modèle a reçus,
    numérotés (reading.forget s'y rapporte). rules(message) → (information, portée) :
    ce que les règles lisent quand le modèle n'a rien lu de retenable d'une demande.
    scope, project : où va ce qui est retenu (un fait de projet sans dossier va à
    tous les projets). source : la colonne source des faits ; label : les journaux.
    confirm(message, retenus, faits, asked) → [bool] : chaque fait que le modèle
    retirerait est-il bien visé (MemoryReader.confirm) ? Sans lui, retirés tels quels.
    reread(échanges) → Reading : la même lecture, sur d'autres échanges ; un renvoi
    (« retiens ça ») dont rien n'a pu être gardé est relu sur les seuls messages de
    l'utilisateur.
    """
    facts = list(reading.remember)
    # « Retiens ceci : … » : le bloc en entier, avec ses mots (une procédure, des
    # consignes), que le modèle découpait ou reformulait ; ce qu'il remplace reste
    # lu par lui
    block = remember_block(message) if asked else None
    block = _trim_scope(block) if block else None
    if block:
        facts = [block]

    # Ce que l'utilisateur a écrit : son message ; pour une demande, aussi ce à
    # quoi il renvoie (« retiens ça », « retiens-le pour tous mes projets »).
    # Sans demande, la moitié des mots du fait doit en venir ; avec, un seul
    # suffit (il reformule parfois : « j'utilise pytest » → « je fais mes tests
    # avec pytest »)
    sources = [message]
    if asked:
        sources += [text for _who, text in context]
        sources += [str(fact.get("value") or "") for fact in known]
    # Un fait déjà retenu n'est repris que si le message ou les échanges en parlent
    # (« retiens-le pour tous mes projets », juste après l'avoir fait retenir).
    # Après une réponse qui disait l'information déjà enregistrée, le vrai modèle
    # recopiait sinon toute la liste « Déjà retenu » pour « retiens ça » : cinq
    # cartes « Mémorisé », et les faits du code copiés dans le chat
    said = [message] + [text for _who, text in context]
    retained = {_loose(str(fact.get("value") or "")) for fact in known}

    def keep(candidates: Sequence[str]) -> List[str]:
        kept: List[str] = []
        for written in candidates:
            fact = _known_wording(written, known)
            if written != block and _DONE_TASK_RE.match(fact):
                logger.info("%s : « %s » est une tâche, pas retenu", label, fact[:80])
            elif not _grounded(fact, sources, strict=not asked):
                logger.info("%s : « %s » ne vient pas de l'utilisateur, pas retenu",
                            label, fact[:80])
            elif _loose(fact) in retained and not _grounded(fact, said):
                logger.info("%s : « %s » est déjà retenu, et ni le message ni les échanges "
                            "n'en parlent : pas repris", label, fact[:80])
            elif _loose(fact) not in {_loose(other) for other in kept}:
                kept.append(fact)
        return kept

    kept = keep(facts)
    if (asked and not kept and reread is not None
            and only_asks_to_remember(_without_scope(message))):
        # « Retiens ça » dont le modèle n'a rien tiré : relu sur ce que l'utilisateur
        # a dit, sans les réponses de l'assistant, qui l'égaraient (« c'est
        # enregistré », écrit sans que rien ne le soit)
        own = [(who, text) for who, text in context if who == "Utilisateur"]
        if own and len(own) < len(context):
            try:
                reading = reread(own)
            except Exception as exc:  # pylint: disable=broad-except
                logger.warning("%s : renvoi non relu (%s)", label, exc)
            else:
                logger.info("%s : renvoi relu sans les réponses de l'assistant : retenir %s",
                            label, [fact[:60] for fact in reading.remember])
                facts = list(reading.remember)
                kept = keep(facts)
    if asked and not kept and (facts or not reading.forget):
        # Le modèle n'a rien lu de retenable là où il fallait : les règles
        fact, rule_scope = rules(message) if rules else (None, scope)
        if fact:
            kept, scope = [fact], rule_scope
    # Un remplacement dont le nouveau fait n'a pas pu être gardé : l'ancien reste
    failed = bool(facts) and not kept
    if scope == SCOPE_PROJECT and not project:
        scope = SCOPE_CODE
    where = project if scope == SCOPE_PROJECT else ""
    forget = [shown[number - 1] for number in dict.fromkeys(reading.forget)
              if 1 <= number <= len(shown)]
    if failed or (not asked and not kept):
        # Sans demande, rien n'est supprimé : au plus remplacé par ce qu'il dit
        forget = []
    elif not asked:
        forget = forget[:_MAX_SPONTANEOUS_FORGET]
    if forget and confirm is not None:
        forget = _confirmed(confirm, message, kept, forget, asked, label)
    if wanted is not None and not wanted():
        return None

    remembered = []
    for fact in kept:
        fact_id, created = kb.remember(fact, source=source, scope=scope, project=where)
        remembered.append(Remembered(fact, fact_id, created, scope, where))
    kept_ids = {item.fact_id for item in remembered}
    if not asked:
        # Une préférence redite : déjà retenue, rien à montrer
        remembered = [item for item in remembered if item.created]
    forgotten = []
    for fact in forget:
        # Retenu de nouveau (« retiens-le pour tous mes projets ») : il reste
        if fact["id"] in kept_ids or not kb.delete_fact(fact["id"]):
            continue
        fact_scope_, folder = fact_scope(fact)
        forgotten.append(Forgotten(str(fact.get("value") or ""), fact["id"],
                                   fact_scope_, folder))
    update = MemoryUpdate(asked, remembered, forgotten)
    if not asked:
        return update if update.changed else None
    if update.changed:
        if len(remembered) == 1:
            # Retenu, au besoin à la place d'un autre (« retiens plutôt que… »)
            update.alone = _asks_nothing_else(message, remembered[0].fact)
        elif not remembered:
            update.alone = only_asks_to_forget(_without_scope(message))
    elif failed:
        update.failed = True
    elif only_asks_to_remember(_without_scope(message)):
        update.unclear = update.alone = True
    elif asks_to_forget(message) and _FORGET_FACT_RE.search(message):
        update.missing = True
        update.alone = only_asks_to_forget(_without_scope(message))
    return update


class CodeMemory:
    """Faits et documents de My_AI vus de la conversation Code."""

    def __init__(
        self,
        knowledge_base: Any,
        search: Optional[Callable[..., str]] = None,
        auto_extract: Optional[Callable[[], bool]] = None,
        reader: Optional[Callable[[Optional[Dict[str, Any]]], Any]] = None,
    ):
        """
        Args:
            knowledge_base: KnowledgeBaseManager (faits SQLite).
            search: AIEngine.search_memory (faits donnés, puis documents de la
                fenêtre Mémoire) ; sans elle, les faits seulement.
            auto_extract: réglage knowledge_base.auto_extract : My_AI mémorise-t-il
                depuis les conversations ?
            reader: pour le modèle de la conversation (chat_url, model, num_ctx), ce
                qui lit ce qu'un message change (MemoryReader.for_llm) ; sans lui,
                seules les demandes « retiens que… », lues par des règles.
        """
        self._kb = knowledge_base
        self._search = search
        self._auto_extract = auto_extract or (lambda: True)
        self._reader = reader

    def facts(self, roots: Sequence[str]) -> List[Dict[str, Any]]:
        """Faits reçus d'office avec ces dossiers ouverts (prompt_block)."""
        return self._kb.code_facts(roots)

    def prompt_block(self, roots: Sequence[str],
                     facts: Optional[List[Dict[str, Any]]] = None) -> str:
        """Section « Mémoire » du prompt système : les faits du code, puis comment
        lire le reste de la mémoire et y écrire."""
        facts = self.facts(roots) if facts is None else facts
        lines: List[str] = []
        projects: Dict[str, List[Dict[str, Any]]] = {}
        everywhere = []
        for fact in facts:
            scope, folder = fact_scope(fact)
            if scope == SCOPE_PROJECT:
                projects.setdefault(project_name(folder), []).append(fact)
            elif scope == SCOPE_CODE:
                everywhere.append(fact)
        if facts:
            lines.append("Ce que l'utilisateur t'a demandé de retenir pour son code "
                         "(fenêtre 🧠 Mémoire de My_AI) :")
            for name, group in projects.items():
                lines.append(f"Pour le projet {name} :")
                lines.extend(f"- {self._kb.prompt_text(fact)}" for fact in group)
            if everywhere:
                lines.append("Pour tous ses projets :")
                lines.extend(f"- {self._kb.prompt_text(fact)}" for fact in everywhere)
            lines.append("")
            lines.append(
                "Applique ces consignes quand elles concernent ce que tu fais. Ne les recopie "
                "pas dans les fichiers, les commentaires ou les messages de commit, et n'en "
                "parle que si on te le demande.")
        lines.append(
            "Le reste de sa mémoire (ce qu'il t'a dit sur lui, documents qu'il a mis dans "
            "My_AI : cahiers des charges, notes…) se lit avec l'outil search_memory, "
            "seulement quand il en parle.")
        lines.append(
            "Tu n'écris pas toi-même dans cette mémoire : My_AI s'en charge. Quand "
            "l'utilisateur te demande de retenir, de remplacer ou d'oublier quelque chose "
            "(« retiens que… », « retiens plutôt que… », « oublie que… »), une note [Mémoire] "
            "à la fin de son message te dit ce qui a été fait ; tu ne la recopies pas. Une "
            "préférence durable qu'il donne en passant (« j'utilise toujours black »), My_AI "
            "la retient de lui-même et l'affiche par une carte : applique-la, sans dire "
            "toi-même que tu l'as notée.")
        return "\n".join(lines)

    @staticmethod
    def asks(message: str) -> bool:
        """Le message demande-t-il de retenir ou d'oublier quelque chose ? La mémoire
        change alors avant la réponse, qui le confirme (update, asked)."""
        return bool(message) and (asks_to_remember(message) or asks_to_forget(message))

    def update(self, message: str, roots: Sequence[str],
               context: Sequence[Tuple[str, str]] = (),
               llm: Optional[Dict[str, Any]] = None,
               asked: Optional[bool] = None,
               wanted: Optional[Callable[[], bool]] = None) -> Optional[MemoryUpdate]:
        """
        Ce que le message de l'utilisateur change dans la mémoire du code, fait :
        pour le premier dossier ouvert, ou pour tous ses projets si le message le
        dit (ou si VS Code n'a aucun dossier ouvert).

        asked (par défaut : asks) : le message demande de retenir ou d'oublier. Le
        modèle de la conversation (llm) lit alors quoi retenir, remplacer ou
        oublier, avec les derniers échanges (context : (« Utilisateur » ou
        « Assistant », texte)) et les faits déjà retenus ; sans lui, s'il échoue ou
        ne trouve rien, les règles de remember_request lisent les « retiens que… ».
        Sinon, il lit si le message donne une préférence durable, à retenir, au
        besoin à la place d'un fait qu'elle contredit (sans modèle : rien).

        Chaque information retenue vient de ce que l'utilisateur a écrit
        (_grounded) : son message, et pour une demande, les échanges et les faits
        auxquels il renvoie. Pour quels projets : les mots du message, pas le modèle.

        wanted : appelé avant d'écrire ; False (réponse arrêtée entre-temps) : rien
        n'est écrit, puisque aucune carte ne pourrait plus le montrer.

        Returns:
            None si le message ne change rien et ne demandait rien ; sinon ce qui a
            changé (une demande sans effet : unclear ou missing, pour la note).
        """
        if not message or not self._auto_extract():
            return None
        if asked is None:
            asked = self.asks(message)
        if not asked and len(message.split()) < _MIN_SPONTANEOUS_WORDS:
            return None
        reader = self._reader(llm) if self._reader is not None and llm else None
        if not asked and reader is None:
            return None
        project = next((root for root in roots or () if root), "")
        known = self._kb.code_facts(roots)
        shown = sorted(known, key=lambda fact: str(fact.get("updated_at") or ""))
        shown = shown[-_MAX_KNOWN_FACTS:]
        lines, name = _known_lines(shown), project_name(project) if project else ""
        reading = Reading()
        if reader is not None:
            try:
                reading = reader(message, list(context) if asked else [], lines, name, asked)
                logger.info("Conversation Code : mémoire lue par le modèle (%s) : retenir %s, "
                            "oublier %s", "demande" if asked else "sans demande",
                            [fact[:60] for fact in reading.remember], reading.forget)
            except Exception as exc:  # pylint: disable=broad-except
                logger.warning("Conversation Code : le modèle n'a pas lu la mémoire (%s)", exc)
                reading = Reading()
        if asked and _THIS_PROJECT_RE.search(message):
            # « Oublie tout ce que tu as retenu pour ce projet » : ce qui vaut pour tous
            # ses projets reste. Le vrai modèle le retirait aussi, et le second appel,
            # qui ne voit pas pour quoi vaut chaque fait, le confirmait
            reading.forget = [number for number in reading.forget
                              if 1 <= number <= len(shown)
                              and fact_scope(shown[number - 1])[0] == SCOPE_PROJECT]
        scope = SCOPE_CODE if _ALL_PROJECTS_RE.search(message) else SCOPE_PROJECT
        return apply_reading(self._kb, message, reading, known, shown, asked=asked,
                             scope=scope, project=project, context=context,
                             rules=lambda text: remember_request(text)[:2], source="code",
                             wanted=wanted, confirm=getattr(reader, "confirm", None),
                             reread=rereader(reader, message, lines, name))

    def search(self, query: str, n_results: int = 5, document: str = "",
               roots: Sequence[str] = ()) -> str:
        """Outil search_memory de la conversation Code : faits du chat, du code et de
        ces dossiers (pas ceux des autres projets), puis documents de la mémoire.

        Faute de fait correspondant, seuls ceux du code sont proposés : une
        recherche de cahier des charges ne ramène pas les faits du chat (nom,
        famille…), qui n'ont rien à faire dans le code.
        """
        code = self._kb.code_facts(roots)
        pool = self._kb.chat_facts() + code
        if self._search is not None:
            return self._search(query, n_results, document, facts=pool, recent=code)
        found = self._kb.search_text(query, n_results, facts=pool, recent=code)
        return found or "Aucun résultat dans la mémoire (faits mémorisés et documents indexés)."


def code_memory_for(engine: Any) -> Optional[CodeMemory]:
    """Mémoire de la conversation Code, de l'AIEngine de l'appli (None sans base de faits)."""
    knowledge_base = getattr(engine, "knowledge_base", None)
    if knowledge_base is None:
        return None
    return CodeMemory(
        knowledge_base,
        search=getattr(engine, "search_memory", None),
        auto_extract=getattr(engine, "_memory_auto_extract", None),
        reader=MemoryReader.for_llm,
    )
