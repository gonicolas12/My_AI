"""
Demandes de mémoire dans les dix langues de My_AI autres que le français et
l'anglais : retenir (« Recuerda que vivo en Madrid », « 记住我住在北京 ») et
oublier (« Vergiss, dass ich rauche », « 犬を飼っていることは忘れて »).

core/knowledge_base_manager.py lit le français et l'anglais, puis passe la main à
ce module quand il n'y trouve pas de demande. Les règles sont les mêmes, avec les
mots de chaque langue :
  - la demande ouvre sa phrase, après des mots d'introduction (« Hola, »,
    « Bitte », « 请 »). En japonais et en coréen, où le verbe vient en dernier,
    elle la ferme (« …と覚えておいて », « …기억해 줘 »), ou l'ouvre suivie de « : » ;
  - une question après le verbe (« Recuerda: ¿dónde vivo? ») demande de se
    souvenir, pas de retenir ;
  - « No olvides », « Vergiss nicht », « 别忘了 », « 忘れないで » demandent de
    retenir, pas d'oublier ; « Olvidé… », « 我忘了… », « 忘れてた » disent un oubli ;
  - un fait à oublier est introduit par le verbe (« olvida que… », « vergiss,
    dass… »), ou le message parle de la mémoire. « Olvídalo » seul peut ne
    renvoyer qu'à la conversation (« laisse tomber »).

Sans eux, ces messages passaient par la lecture sans demande, qui ne supprime
jamais rien : « Olvida que vivo en Madrid » gardait le fait, et la réponse pouvait
prétendre l'avoir oublié. Rien de ce qu'ils demandaient de retenir n'était non
plus confirmé avant la réponse.

Ce module ne dépend d'aucun autre de core : knowledge_base_manager l'importe.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Match, Optional, Pattern, Tuple

REMEMBER = "remember"
FORGET = "forget"

# Fins de phrase, toutes écritures (« ؟ » : arabe ; « 。！？ » : chinois, japonais)
_ENDS = ".!?\n。！？؟"
_SENTENCE_BODY_RE = re.compile(r"[^.!?\n。！？؟]+")
_QUESTION_MARKS = "?？؟"
# Ponctuation autour des mots d'introduction ou de politesse (« ¡Hola! », « 你好， »)
# (les voyelles arabes et les accents combinants restent : ce sont des lettres)
_PUNCTUATION_RE = re.compile(r"[^\w'’\s\u0300-\u036f\u064b-\u0652\u0670\u0640-]+")
# Signes qui ouvrent ou ferment une information citée
_QUOTES = "\"'«»“”`「」『』"
# Ce qui coupe une proposition, toutes écritures
_CLAUSE_MARKS = ",;，、；،؛"

# Chinois et japonais s'écrivent sans espaces : deux caractères y comptent pour un mot
_CJK_CHAR_RE = re.compile(r"[\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]")
# Écritures de chaque langue : un message sans elles n'a rien à y chercher
_LATIN_RE = re.compile(r"[a-zA-ZÀ-ɏ]")
_CYRILLIC_RE = re.compile(r"[\u0400-\u04ff]")
_ARABIC_RE = re.compile(r"[\u0600-\u06ff]")
_HAN_RE = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]")
_KANA_RE = re.compile(r"[\u3040-\u30ff]")
_HANGUL_RE = re.compile(r"[\uac00-\ud7a3\u1100-\u11ff\u3130-\u318f]")


def word_count(text: str) -> int:
    """
    Mots d'un texte. Le chinois et le japonais s'écrivent sans espaces : deux de
    leurs caractères y comptent pour un mot (« 我住在北京 » : trois mots). Coupé
    aux espaces, « 我住在北京 » n'avait qu'un mot, trop peu pour une information
    à retenir.
    """
    text = text or ""
    spaced = len(_CJK_CHAR_RE.sub(" ", text).split())
    joined = len(_CJK_CHAR_RE.findall(text))
    return spaced + (joined + 1) // 2


# ── Arabe : voyelles et hamza facultatives ─────────────────────────────────

# Voyelles brèves, chadda, sukun, alif suscrit, tatweel : rarement écrits, permis partout
_HARAKAT = "[\u064b-\u0652\u0670\u0640]*"
_ALEFS = "اأإآ"


def _arabic(pattern: str) -> str:
    """Un motif écrit en lettres arabes sans voyelles ni hamza (« انس ان »), qui
    les admet : « انسَ أنّ » ; un alif est n'importe lequel (ا أ إ آ), un yā' final
    aussi (ي ى), et un tā' marbūṭa peut s'écrire hā' (ة ه). Pas de classe de
    caractères arabes dans le motif : chaque lettre en devient une."""
    out = []
    for char in pattern:
        if char in _ALEFS:
            out.append("[" + _ALEFS + "]" + _HARAKAT)
        elif char in "يى":
            out.append("[يى]" + _HARAKAT)
        elif char == "ة":
            out.append("[ةه]" + _HARAKAT)
        elif "ء" <= char <= "ي":
            out.append(char + _HARAKAT)
        else:
            out.append(char)
    return "".join(out)


# ── Les mots de chaque langue ──────────────────────────────────────────────


@dataclass(frozen=True)
class _Words:
    """
    Les mots d'une langue pour ses demandes de mémoire, en motifs d'expressions
    régulières (sans casse). Verbe en tête : remember et forget en sont le verbe,
    connector ce qui introduit le fait (« que », « dass »). Verbe en dernier
    (japonais, coréen) : ils ferment la phrase, avec leur politesse (« …ください »),
    et particles relie le fait au verbe (« …ということを »).
    """

    code: str
    remember: str
    forget: str
    # Mots admis avant la demande dans sa phrase (« Hola, », « Bitte »)
    lead_in: str
    # Mots interrogatifs : « Recuerda: ¿dónde vivo? » demande de se souvenir
    question: str
    # Politesse qui peut suivre la demande sans rien demander d'autre
    polite: str
    # Ce qui ouvre une autre proposition (« y », « und », « 然后 »)
    joins: str
    # Renvoi à ce qui précède (« Recuérdalo », « Merk dir das »)
    reference: str
    # La mémoire (« borra de tu memoria… ») : un oubli qui en parle vise un fait
    memory: str
    # Ce qui introduit le fait après le verbe (« que », « dass ») ; "" en chinois,
    # où le fait suit le verbe (« 记住我住在北京 »)
    connector: str = ""
    # Entre le verbe et le fait (« Recuerda mejor que… », « Merk dir bitte, dass… »)
    adverbs: str = ""
    # Verbes qui ouvrent une autre demande dans la même phrase (« …y dame una idea ») :
    # le fait lu par les règles s'arrête avant eux
    requests: str = ""
    # Mots admis avant « retenir » seulement : « 你记住… » demande, « 你忘了… » constate
    remember_lead_in: str = ""
    # Verbe en dernier : ce qui relie le fait au verbe
    particles: str = ""
    # Verbe en dernier : comment finit une phrase qui demande (« …教えて ») ; une
    # demande suivie d'une virgule (« 犬のことは忘れて、レシピを教えて ») n'en est une
    # que dans une telle phrase (« 覚えて、テストに合格した » raconte)
    request_end: str = ""
    # Lecture sans demande (message_parts). Ce qu'il cherche (« busco… », « 我在找… ») :
    # sa demande du moment, comme « je cherche… » en français (core/chat_memory.py)
    search: str = ""
    # Verbe en dernier : comment finit une proposition qui demande (« …書いて », « …써
    # 줘 »), sans les fins d'une phrase qui dit (« …ですよ », « …운동해요 »)
    asks_end: str = ""
    # Ce qui ne vaut que pour la journée (« hoy », « сегодня », « 今天 ») : pas un fait
    # durable. Pas « maintenant » : « ahora trabajo en un banco » en est un
    momentary: str = ""
    verb_last: bool = False
    # Mots séparés par des espaces (pas le chinois ni le japonais)
    spaced: bool = True
    # Conversation Code : « pour tous mes projets », « pour ce projet »
    all_projects: str = ""
    this_project: str = ""


_SPANISH = _Words(
    code="es",
    remember=(
        r"recu[ée]rda(?:lo|la|los|las)?|recu[ée]rde(?:lo|la)?|acu[ée]rd(?:ate|ese)"
        r"|memor[íi]za(?:lo|la)?|memorice"
        r"|no\s+(?:te\s+|se\s+)?olvid(?:es|e)"
        r"|ten(?:ga)?\s+(?:muy\s+|siempre\s+)?(?:en\s+cuenta|presente|en\s+mente)"
        r"|gu[áa]rda(?:lo|la)?(?=[^.!?\n]{0,60}\bmemoria\b)"
        r"|ap[úu]nta(?:lo|la|te)?|an[óo]ta(?:lo|la|te)?|toma\s+nota"
        r"|(?:puedes|podr[íi]as|quiero\s+que|necesito\s+que|te\s+pido\s+que)\s+"
        r"(?:recordar|memorizar|recuerdes|memorices|tener\s+en\s+cuenta|tengas\s+en\s+cuenta)"
    ),
    forget=(
        r"olvida|olv[íi]da(?:lo|la|los|las)|olv[íi]d(?:ate|ese)"
        r"|(?:b[óo]rra|elimina|quita|suprime|saca)(?:lo|la)?(?=[^.!?\n]{0,80}\bmemoria\b)"
        r"|deja\s+de\s+recordar|ya\s+no\s+recuerdes|no\s+recuerdes\s+m[áa]s"
        r"|(?:puedes|podr[íi]as|quiero\s+que|necesito\s+que|te\s+pido\s+que)\s+"
        r"(?:olvidar|olvides)"
    ),
    lead_in=(
        r"hola|buenas|buenos\s+d[íi]as|buenas\s+(?:tardes|noches)|oye|oiga|mira|bueno|vale"
        r"|venga|ok(?:ay|ey)?|okey|s[íi]|no|y|e|tambi[ée]n|adem[áa]s|por\s+cierto"
        r"|por\s+favor|porfa(?:vor)?|ah|oh|eh|perfecto|genial|estupendo|gracias|entonces"
        r"|pues|ahora|importante|dato|ojo|claro|de\s+acuerdo|mejor|una\s+cosa|otra\s+cosa"
    ),
    # Sans « que » : « ¿Puedes recordar que soy vegetariano? » est une demande
    question=(
        r"qué|qui[ée]n(?:es)?|d[óo]nde|ad[óo]nde|cu[áa]ndo|por\s*qu[ée]|c[óo]mo"
        r"|cu[áa]l(?:es)?|cu[áa]nt[oa]s?"
    ),
    polite=r"gracias|muchas\s+gracias|mil\s+gracias|por\s+favor|porfa|vale|ok(?:ay|ey)?|genial|perfecto",
    joins=r"y|e|luego|despu[ée]s|entonces|tambi[ée]n|adem[áa]s|pero",
    reference=r"esto|eso|ello|aquello|lo\s+anterior|lo\s+siguiente",
    memory=r"memoria",
    connector=r"(?:de\s+)?que",
    adverbs=r"mejor|m[áa]s\s+bien|bien|tambi[ée]n|por\s+favor|en\s+cambio|en\s+su\s+lugar|siempre",
    requests=(
        r"dame|dime|d[ée]jame|escr[íi]beme|escribe|haz|hazme|busca|b[úu]scame|explica"
        r"|expl[íi]came|cu[ée]ntame|recomi[ée]ndame|recomienda|sugi[ée]reme|sugiere|prop[óo]n"
        r"|prop[óo]nme|crea|cr[ée]ame|traduce|trad[úu]ceme|ay[úu]dame|mu[ée]strame|muestra"
        r"|calcula|genera|prepara|ponme|env[íi]a|abre|lee|resume|res[úu]meme|corrige|revisa"
    ),
    search=r"busco|buscamos|(?:estoy|estamos|ando|andamos|sigo)\s+buscando|en\s+busca\s+de",
    momentary=r"(?:hoy(?!\s+en\s+d[íi]a)|ayer|anoche|esta\s+(?:noche|ma[ñn]ana|tarde))(?![\w'’])",
    all_projects=r"(?:para|en)\s+todos\s+(?:mis|los|nuestros)\s+(?:proyectos|repos(?:itorios)?)",
    this_project=r"(?:para|en)\s+(?:este|el)\s+(?:proyecto|repo(?:sitorio)?)",
)

_GERMAN = _Words(
    code="de",
    remember=(
        r"merke?\s+(?:es\s+)?dir(?!\s+(?:(?:das|es|dies|bitte)\s+)*nicht\s+mehr)"
        r"|merken\s+sie\s+(?:es\s+)?sich"
        r"|(?:behalte?|behalten\s+sie)\s+(?:(?:das|es|dies|bitte|gut)\s+)*"
        r"(?:im\s+(?:kopf|ged[äa]chtnis|hinterkopf)|in\s+erinnerung)"
        r"|vergiss\s+(?:(?:es|das|dies|bitte)\s+)*(?:nicht|nie(?:mals)?)"
        r"|vergessen\s+sie\s+(?:(?:es|das|dies|bitte)\s+)*(?:nicht|nie(?:mals)?)"
        r"|denke?\s+(?:bitte\s+)?(?:daran|dran)|denken\s+sie\s+(?:bitte\s+)?(?:daran|dran)"
        r"|erinnere?\s+dich(?:\s+(?:bitte\s+)?daran)?"
        r"|notiere?\s+(?:es\s+|das\s+)?dir"
        r"|pr[äa]ge?\s+(?:es\s+|das\s+)?dir(?:\s+(?:bitte|gut))*\s+ein"
        r"|speichere?(?=[^.!?\n]{0,60}\b(?:ged[äa]chtnis|speicher)\b)"
        r"|(?:kannst|k[öo]nntest)\s+du\s+(?:(?:dir|bitte|das|es|mal)\s+)*(?:merken|behalten)"
        r"|k[öo]nnten\s+sie\s+(?:(?:sich|bitte|das|es)\s+)*(?:merken|behalten)"
    ),
    forget=(
        r"vergiss(?!\s+(?:(?:es|das|dies|bitte)\s+)*(?:nicht|nie(?:mals)?)(?![\w'’]))"
        r"|vergessen\s+sie(?!\s+(?:(?:es|das|dies|bitte)\s+)*(?:nicht|nie(?:mals)?)(?![\w'’]))"
        r"|(?:l[öo]sche?|entferne?|streiche?)(?=[^.!?\n]{0,80}\b(?:ged[äa]chtnis|speicher)\b)"
        r"|(?:merke?\s+(?:es\s+)?dir|behalte?)\s+(?:(?:das|es|dies|bitte)\s+)*nicht\s+mehr"
        r"|(?:kannst|k[öo]nntest)\s+du\s+(?:(?:das|es|bitte|mal)\s+)*vergessen"
        r"|k[öo]nnten\s+sie\s+(?:(?:das|es|bitte)\s+)*vergessen"
    ),
    lead_in=(
        r"hallo|hi|hey|servus|moin|gr[üu](?:ß|ss)\s+(?:dich|gott)|guten\s+(?:morgen|tag|abend)"
        r"|ok(?:ay)?|gut|also|und|auch|au(?:ß|ss)erdem|[üu]brigens|bitte|ja|nein|n[öo]|nee"
        r"|ach|oh|ah|super|perfekt|toll|danke|so|nun|jetzt|wichtig|info|hinweis|kurz|na"
        r"|klar|genau|alles\s+klar|noch\s+was|noch\s+etwas|eins\s+noch"
    ),
    question=(
        r"was|wer|wo|wann|warum|wieso|weshalb|wie|welche[rsmn]?|wohin|woher|wie\s*viele?"
        r"|wessen|wem|wen"
    ),
    polite=r"danke(?:\s+sch[öo]n)?|vielen\s+dank|dankesch[öo]n|bitte(?:\s+sch[öo]n)?|ok(?:ay)?|super|perfekt",
    joins=r"und|dann|danach|au(?:ß|ss)erdem|auch|aber|sowie",
    reference=r"das|dies|es|das\s+hier|dies\s+hier|folgendes|das\s+folgende",
    memory=r"ged[äa]chtnis|speicher",
    connector=r"dass",
    adverbs=r"bitte|auch|mal|unbedingt|gut|stattdessen|lieber|eher|doch|immer",
    requests=(
        r"gib|sag|schreib(?:e)?|erkl[äa]r(?:e)?|such(?:e)?|mach(?:e)?|zeig(?:e)?|empfiehl"
        r"|hilf|erstell(?:e)?|[üu]bersetz(?:e)?|berechne|schick(?:e)?|nenn(?:e)?|schlag"
        r"|finde?|lies|fass"
    ),
    search=r"suche|suchen|auf\s+der\s+suche",
    momentary=r"(?:heute|gestern|vorhin)(?![\w'’])",
    all_projects=(
        r"(?:f[üu]r|in|bei)\s+(?:alle|allen|s[äa]mtliche[n]?)\s+(?:meine[n]?\s+|unsere[n]?\s+)?"
        r"(?:projekte[n]?|repos|repositor(?:y|ies)|codebasen)"
    ),
    this_project=r"(?:f[üu]r|in|bei)\s+(?:diese[sm]?|dem|das)\s+(?:projekt|repo(?:sitory)?)",
)

_ITALIAN = _Words(
    code="it",
    remember=(
        r"ricorda(?:ti|telo|tela|lo|la)?|ricordatevi"
        r"|tieni\s+(?:bene\s+)?(?:a\s+mente|presente|in\s+mente)|tenga\s+(?:a\s+mente|presente)"
        r"|memorizza(?:lo|la)?|memorizzi"
        r"|non\s+(?:ti\s+)?dimenticar(?:e|ti|lo|telo|la)"
        r"|prendi\s+nota|annota(?:ti|lo)?|segnati|segnatelo"
        r"|(?:salva|registra|metti)(?:lo|la)?(?=[^.!?\n]{0,60}\bmemoria\b)"
        r"|(?:puoi|potresti|voglio\s+che|vorrei\s+che)\s+"
        r"(?:ricordare|ricordarti|memorizzare|ricordi|memorizzi|tenere\s+a\s+mente)"
    ),
    forget=(
        r"dimentica(?:lo|la|li|le|ti|telo)?|scorda(?:ti|telo|lo|la)?"
        r"|(?:cancella|elimina|rimuovi|togli)(?:lo|la)?(?=[^.!?\n]{0,80}\bmemoria\b)"
        r"|non\s+ricordar(?:e|ti)\s+pi[ùu]|smetti\s+di\s+ricordare"
        r"|(?:puoi|potresti|voglio\s+che|vorrei\s+che)\s+"
        r"(?:dimenticare|dimenticarti|dimentichi|scordare|scordarti)"
    ),
    lead_in=(
        r"ciao|salve|buongiorno|buonasera|ehi|ehil[àa]|ok(?:ay)?|va\s+bene|bene|s[ìi]|no|e|ed"
        r"|anche|inoltre|comunque|a\s+proposito|per\s+favore|per\s+piacere|perfetto|ottimo"
        r"|grazie|allora|dunque|ora|adesso|importante|senti|guarda|ah|oh|beh|cio[èe]"
        r"|piuttosto|anzi|una\s+cosa"
    ),
    # Sans « che » : « Puoi ricordare che sono vegetariano? » est une demande
    question=r"cosa|che\s+cosa|chi|dove|quando|perch[ée]|come|quale|quali|quant[oaie]",
    polite=r"grazie(?:\s+mille)?|per\s+favore|per\s+piacere|ok(?:ay)?|perfetto",
    joins=r"e|ed|poi|dopo|anche|inoltre|ma|quindi",
    reference=r"questo|ci[òo]|quello|questa\s+cosa|quanto\s+segue|(?:la\s+)?seguente",
    memory=r"memoria",
    connector=r"che",
    adverbs=r"bene|invece|piuttosto|per\s+favore|anche|pure|sempre",
    requests=(
        r"dammi|dimmi|scrivi(?:mi)?|fai|fammi|cerca(?:mi)?|spiega(?:mi)?|consigliami"
        r"|consiglia|suggerisci(?:mi)?|proponi(?:mi)?|crea(?:mi)?|traduci|aiutami|mostrami"
        r"|mostra|calcola|genera|prepara(?:mi)?|manda(?:mi)?|leggi|riassumi"
    ),
    search=r"cerco|cerchiamo|(?:sto|stiamo)\s+cercando|alla\s+ricerca\s+d",
    momentary=r"(?:oggi|ieri|stasera|stamattina|stanotte)(?![\w'’])",
    all_projects=r"(?:per|in|su)\s+tutti\s+i\s+(?:miei\s+|nostri\s+)?(?:progetti|repo(?:sitory)?)",
    this_project=r"(?:per|in|su)\s+(?:questo|il)\s+(?:progetto|repo(?:sitory)?)",
)

_PORTUGUESE = _Words(
    code="pt",
    remember=(
        # Pas « lembre-me de… » (rappelle-moi de…)
        r"(?:lembr[ae](?:-(?:te|se))?|lembrem-se|recorda(?:-te)?|recorde(?:-se)?)(?!-)"
        r"|memoriz[ae](?:-[oa])?"
        r"|n[ãa]o\s+(?:te\s+|se\s+)?esque(?:[çc]as?|[çc]am|ce)"
        r"|(?:tem|tenha)\s+em\s+(?:mente|conta|aten[çc][ãa]o)"
        r"|(?:guard|grav|salv|regist|registr)[ae](?:-[oa])?(?=[^.!?\n]{0,60}\bmem[óo]ria\b)"
        r"|anot[ae](?:-[oa])?|tom[ae]\s+nota"
        r"|(?:podes|pode|poderias|poderia|voc[êe]\s+pode|quero\s+que|preciso\s+que)\s+"
        r"(?:lembrar|memorizar|recordar|lembres|lembre|memorizes|memorize)"
    ),
    # « Não esquece que… » (familier) demande de retenir
    forget=(
        r"(?<!n[ãa]o\s)(?<!n[ãa]o\ste\s)(?<!n[ãa]o\sse\s)esque(?:ce|[çc]a)(?:-(?:te|se))?"
        r"|(?:apaga|apague|remove|remova|elimina|elimine|tira|tire|exclui|exclua|deleta)"
        r"(?:-[oa])?(?=[^.!?\n]{0,80}\bmem[óo]ria\b)"
        r"|deix[ae]\s+de\s+(?:lembrar|recordar)|n[ãa]o\s+(?:te\s+|se\s+)?lembr(?:es|e)\s+mais"
        r"|par[ae]\s+de\s+lembrar"
        r"|(?:podes|pode|poderias|poderia|voc[êe]\s+pode|quero\s+que|preciso\s+que)\s+"
        r"(?:esquecer|esque[çc]as|esque[çc]a)"
    ),
    lead_in=(
        r"ol[áa]|oi|bom\s+dia|boa\s+(?:tarde|noite)|ei|ok(?:ay)?|certo|beleza|t[áa]|sim"
        r"|n[ãa]o|e|tamb[ée]m|al[ée]m\s+disso|ali[áa]s|por\s+favor|pf|perfeito|[óo]timo"
        r"|obrigad[oa]|ent[ãa]o|agora|importante|olha|ah|oh|bem|pronto|melhor|uma\s+coisa"
    ),
    # Sans « que » : « Pode lembrar que moro em Lisboa? » est une demande
    question=r"o\s+qu[eê]|quê|quem|onde|aonde|quando|por\s*qu[êe]|como|qual|quais|quant[oa]s?",
    polite=r"obrigad[oa]|muito\s+obrigad[oa]|valeu|por\s+favor|ok(?:ay)?|perfeito|beleza",
    joins=r"e|depois|ent[ãa]o|tamb[ée]m|al[ée]m\s+disso|mas",
    reference=r"isso|isto|disso|disto|aquilo|o\s+seguinte",
    memory=r"mem[óo]ria",
    connector=r"(?:de\s+)?que",
    adverbs=r"antes|melhor|em\s+vez\s+disso|por\s+favor|tamb[ée]m|bem|sempre",
    requests=(
        r"d[áa]-me|me\s+d[áa]|diz-me|me\s+diga|escreve(?:-me)?|escreva|faz(?:-me)?|fa[çc]a"
        r"|procura|explica(?:-me)?|explique|recomenda(?:-me)?|sugere|sugira|prop[õo]e|cria"
        r"|crie|traduz|traduza|ajuda-me|me\s+ajude|mostra(?:-me)?|mostre|calcula|gera|prepara"
        r"|manda|envia|l[êe]|resume"
    ),
    search=(
        r"procuro|procuramos|busco|(?:estou|estamos|ando|andamos)\s+"
        r"(?:[àa]\s+procura|procurando|buscando)|(?:[àa]|em)\s+(?:procura|busca)\s+d"
    ),
    momentary=r"(?:hoje(?!\s+em\s+dia)|ontem|esta\s+(?:noite|manh[ãa]|tarde))(?![\w'’])",
    all_projects=(
        r"(?:para|em|nos)\s+todos\s+(?:os\s+)?(?:meus\s+|nossos\s+)?"
        r"(?:projetos|projectos|reposit[óo]rios|repos)"
    ),
    this_project=(
        r"(?:para|em)\s+(?:este|esse|o)\s+(?:projeto|projecto|reposit[óo]rio|repo)"
        r"|(?:neste|nesse)\s+(?:projeto|projecto|reposit[óo]rio|repo)"
    ),
)

_DUTCH = _Words(
    code="nl",
    remember=(
        r"onthoud(?!\s+(?:(?:dat|dit|het)\s+)*niet\s+meer)|onthou"
        r"|vergeet\s+(?:(?:het|dat|dit|alsjeblieft|alstublieft|nou)\s+)*(?:niet|nooit)"
        r"|houd?\s+(?:(?:het|dat|dit|er|alsjeblieft)\s+)*"
        r"(?:in\s+(?:gedachten|je\s+achterhoofd|je\s+hoofd)|rekening\s+mee)"
        r"|(?:sla|bewaar|zet)(?=[^.!?\n]{0,60}\bgeheugen\b)|noteer"
        r"|(?:kun|kan|zou|wil)\s+(?:je|jij|u)\s+(?:(?:dit|dat|het|alsjeblieft|even|wel)\s+)*"
        r"(?:onthouden|bewaren|opslaan|noteren)"
    ),
    forget=(
        r"vergeet(?!\s+(?:(?:het|dat|dit|alsjeblieft|alstublieft|nou)\s+)*(?:niet|nooit)(?![\w'’]))"
        r"|(?:verwijder|wis|schrap|haal)(?=[^.!?\n]{0,80}\bgeheugen\b)"
        r"|onthoud\s+(?:(?:dat|dit|het)\s+)*niet\s+meer"
        r"|(?:kun|kan|zou|wil)\s+(?:je|jij|u)\s+(?:(?:dit|dat|het|alsjeblieft|even|wel)\s+)*vergeten"
    ),
    lead_in=(
        r"hoi|hallo|hey|h[ée]|goedemorgen|goedemiddag|goedenavond|ok[ée]?|okay|goed|prima"
        r"|ja|nee|en|ook|trouwens|overigens|alsjeblieft|alstublieft|aub|graag|perfect|top"
        r"|super|bedankt|dank\s+je(?:\s+wel)?|dus|nou|nu|belangrijk|even|zeg|ah|oh|o"
        r"|liever|eigenlijk"
    ),
    question=r"wat|wie|waar|wanneer|waarom|hoe|welke?|hoeveel|wiens",
    polite=r"bedankt|dank\s+je(?:\s+wel)?|dank\s+u(?:\s+wel)?|alsjeblieft|alstublieft|ok[ée]?|top|super",
    joins=r"en|dan|daarna|ook|maar|verder",
    reference=r"dit|dat|het|het\s+volgende|volgende",
    memory=r"geheugen",
    connector=r"dat",
    adverbs=r"alsjeblieft|alstublieft|ook|even|wel|liever|in\s+plaats\s+daarvan|eigenlijk|goed|altijd",
    requests=(
        r"geef|vertel|schrijf|maak|zoek|leg|raad|stel|help|toon|bereken|vertaal|stuur|noem"
        r"|lees|vat"
    ),
    search=r"zoek|zoeken|op\s+zoek",
    momentary=(r"(?:vandaag(?!\s+de\s+dag)|gisteren|vanavond|vanochtend|vanmorgen|vannacht)"
               r"(?![\w'’])"),
    all_projects=(
        r"(?:voor|in|bij)\s+(?:al\s+)?(?:mijn|onze|alle)\s+"
        r"(?:projecten|repo['’]?s|repositories)"
    ),
    this_project=r"(?:voor|in|bij)\s+(?:dit|het)\s+(?:project|repo(?:sitory)?)",
)

_RUSSIAN = _Words(
    code="ru",
    remember=(
        r"запомни(?:те)?|не\s+забу(?:дь|дьте|вай|вайте)|име(?:й|йте)\s+в\s+виду|учти(?:те)?"
        r"|(?:сохрани|занеси|положи)(?:те)?(?=[^.!?\n]{0,60}памят)"
        r"|(?:запиши|отметь)(?:те)?\s+(?:себе|в\s+памят[ьи])"
        r"|(?:(?:ты\s+)?можешь|(?:вы\s+)?можете|мог(?:ла)?\s+бы|можно|хочу,?\s+чтобы\s+ты"
        r"|прошу(?:\s+тебя)?)\s+(?:пожалуйста\s+)?(?:запомнить|запомнил(?:а)?|не\s+забывать)"
    ),
    # « Не забудь » demande de retenir
    forget=(
        r"(?<!не\s)забудь(?:те)?"
        r"|(?:удали|сотри|убери|вычеркни)(?:те)?(?=[^.!?\n]{0,80}памят)"
        r"|больше\s+не\s+(?:помни|запоминай)(?:те)?|не\s+(?:помни|запоминай)(?:те)?\s+больше"
        r"|перестань(?:те)?\s+помнить"
        r"|(?:(?:ты\s+)?можешь|(?:вы\s+)?можете|мог(?:ла)?\s+бы|можно|хочу,?\s+чтобы\s+ты"
        r"|прошу(?:\s+тебя)?)\s+(?:пожалуйста\s+)?(?:забыть|забыл(?:а)?)"
    ),
    lead_in=(
        r"привет|здравствуй(?:те)?|добрый\s+(?:день|вечер)|доброе\s+утро|слушай(?:те)?"
        r"|ок(?:ей)?|окей|ok(?:ay)?|хорошо|ладно|да|нет|и|а|ещ[её]|также|кстати|пожалуйста"
        r"|плиз|отлично|супер|спасибо|итак|так|теперь|важно|кроме\s+того|ну|эй|о|ах|лучше|вот"
    ),
    # Sans « что » : « Можешь запомнить, что я живу в Москве? » est une demande
    question=r"кто|где|когда|почему|зачем|как(?:ой|ая|ое|ие)?|сколько|куда|откуда|ч(?:ей|ья|ьё|ье|ьи)",
    polite=r"спасибо(?:\s+большое)?|пожалуйста|благодарю|ок(?:ей)?|окей|ok|отлично",
    joins=r"и|потом|затем|также|но|а\s+потом|а\s+ещ[её]",
    reference=r"это|этот\s+факт|вот\s+это|это\s+вс[её]|следующее",
    memory=r"памят",
    connector=r"что",
    adverbs=r"пожалуйста|лучше|вместо\s+этого|себе|также|ещ[её]|хорошо|навсегда",
    requests=(
        r"(?:дай|скажи|напиши|сделай|найди|объясни|посоветуй|предложи|создай|переведи|помоги"
        r"|покажи|посчитай|расскажи|подскажи|составь|пришли)(?:те)?"
    ),
    search=r"ищу|ищем|в\s+поиск(?:ах|е)",
    momentary=r"(?:сегодня|вчера|этим\s+(?:утром|вечером))(?![\w'’])",
    all_projects=(
        r"(?:для|во|в)\s+вс(?:ех|ем)\s+(?:моих\s+|наших\s+)?"
        r"(?:проект(?:ах|ов)|репозитори(?:ях|ев))"
    ),
    this_project=r"(?:для|в)\s+(?:этого|этом)\s+(?:проекта|проекте|репозитория|репозитории)",
)

_CHINESE = _Words(
    code="zh",
    remember=(
        # « 你记住了吗？ » demande si c'est fait
        r"(?:记|記)住(?!了)|(?:记|記)(?:一下|下来|下來)(?!了)|牢(?:记|記)|(?:别|別|不要)忘(?:了|记|記)"
        r"|要(?:记|記)得|(?:保存|存|记录|記錄)(?:到|在|进|進)(?:你的)?(?:记忆|記憶)"
    ),
    # « 忘记了… » sans sujet dit un oubli ; « 把…忘掉 » met le fait avant le verbe
    forget=(
        r"忘(?:掉|记|記)(?!了)|忘了(?:吧|它|这个|這個|这件事|這件事)"
        r"|(?:别|別|不要)再(?:记|記)(?:住|着|著|得)?|不用再?(?:记|記)(?:住|着|著)?了"
        r"|(?:从|從)(?:你的)?(?:记忆|記憶)(?:中|里|裡)?(?:删除|刪除|删掉|刪掉|去掉|移除|抹去|清除)"
        r"|(?:删除|刪除|删掉|刪掉|去掉|移除|清除)(?=[^。！？.!?\n]{0,40}(?:记忆|記憶))"
        r"|把[^。！？.!?\n]{1,60}?(?:忘掉|忘了吧|忘记|忘記)"
    ),
    lead_in=(
        r"你好|您好|嗨|哈喽|哈囉|喂|好的|好吧|好|嗯|哦|噢|啊|对了|對了|对|對|是的|不|不是"
        r"|另外|还有|還有|顺便说一下|順便說一下|顺便|順便|请你|請你|请|請|麻烦你|麻煩你"
        r"|麻烦|麻煩|帮我|幫我|那么|那麼|那|现在|現在|重要|注意|谢谢|謝謝|你能|您能"
        r"|你可以|您可以|能不能|可不可以|ok|okay|hi|hey|hello"
    ),
    remember_lead_in=r"你|您|你要|您要|一定要|一定|能|可以",
    question=(
        r"什么|什麼|甚麼|谁|誰|哪里|哪裡|哪儿|哪兒|哪|几|幾|多少|怎么|怎麼|为什么|為什麼"
    ),
    polite=r"谢谢|謝謝|多谢|多謝|谢啦|谢了|好的|拜托了|拜託了|麻烦了|麻煩了",
    joins=r"然后|然後|并且|並且|而且|另外|还有|還有|顺便|順便|同时|同時|接着|接著",
    reference=r"这个|這個|这些|這些|这一点|這一點|这件事|這件事|这|這|那个|那個|它|吧|了|以下",
    memory=r"记忆|記憶|内存|記錄|记录",
    requests=(
        r"告诉我|告訴我|给我|給我|帮我|幫我|推荐|推薦|建议|建議|搜索|解释|解釋|翻译|翻譯|计算|計算|生成|创建|創建|列出|说说|說說|讲讲|講講|写一|寫一"
    ),
    search=r"在找|想找|要找|寻找|尋找",
    momentary=r"今天|今晚|今早|昨天|昨晚|刚才|剛才",
    spaced=False,
    all_projects=(
        r"(?:在|对|對|为|為|于|於)?(?:我的)?所有(?:我的)?(?:的)?"
        r"(?:项目|項目|仓库|倉庫|代码库|代碼庫)(?:中|里|裡|上)?"
    ),
    this_project=r"(?:在|对|對|为|為|于|於)?(?:这个|這個|本|当前|當前)(?:项目|項目|仓库|倉庫)(?:中|里|裡|上)?",
)

# Ce qui peut suivre le verbe japonais : politesse, demande (« …てくれる？ »), insistance
_JAPANESE_SUFFIX = (
    r"(?:ください|下さい|くださいね|くれ|くれる|くれない|くれますか|ほしい(?:です)?|欲しい(?:です)?"
    r"|もらえる|もらえます(?:か)?|もらえない(?:か)?|ね|よ|な)*"
)
_JAPANESE = _Words(
    code="ja",
    remember=(
        r"(?:(?:覚え|おぼえ)(?:ておいて|といて|ていて|てて|ておけ|とけ|て)"
        r"|記憶(?:しておいて|しといて|して)|メモ(?:しておいて|しといて|して)"
        r"|忘れないで(?:おいて)?|(?:心|胸)に(?:留めて|とめて)(?:おいて)?"
        r"|頭に(?:入れて|いれて)(?:おいて)?)" + _JAPANESE_SUFFIX
    ),
    # « 忘れないで » demande de retenir ; « 忘れてた » dit un oubli
    forget=(
        r"(?:忘れて(?:しまって)?"
        r"|(?:記憶|メモリー?)(?:から|を)[^。！？]{0,40}?(?:消して|削除して|消去して|外して)"
        r"|(?:もう)?(?:覚え|おぼえ)(?:ておかなくて|なくて)(?:いい|大丈夫)(?:よ|です(?:よ)?)?)"
        + _JAPANESE_SUFFIX
    ),
    lead_in=(
        r"こんにちは|こんばんは|おはよう(?:ございます)?|ねえ|ねぇ|あのね|あの|ええと|えっと"
        r"|すみません|ちなみに|それから|あと|そうだ|あっ|そういえば|じゃあ|では|はい|いいえ"
        r"|うん|いや|違う|ちがう|お願い|ok|okay"
    ),
    question=r"何|なに|誰|だれ|どこ|いつ|なぜ|どうして|どう|どの|どれ|いくら|いくつ",
    polite=r"ありがとう(?:ございます)?|どうも|お願いします|お願い|よろしく(?:お願いします)?",
    joins=r"そして|それから|あと|また|それと|ついでに|それに",
    reference=r"これ|それ|このこと|そのこと|この事|その事|今の|さっきの|今言ったこと|以下",
    memory=r"記憶|メモリ",
    particles=(
        r"(?:(?:ということ|ってこと|という事|というの|のこと|の事)(?:を|は|も)?"
        r"|(?:こと|事)(?:を|は|も)|を|は|も|と|って)"
    ),
    request_end=r"(?:て|で|ください|下さい|くれ|ほしい|欲しい|ね|よ|な)",
    search=r"探して|探し中",
    momentary=r"今日|今晩|今夜|今朝|昨日|昨夜|さっき",
    asks_end=r"(?:て|で|ください|下さい|くれ|ちょうだい|ほしい(?:です)?|欲しい(?:です)?)(?:ね|よ|な)?",
    verb_last=True,
    spaced=False,
    all_projects=r"(?:すべて|全て|全部)の(?:私の)?(?:プロジェクト|リポジトリ)(?:で|に|に対して|について|では)?",
    this_project=r"この(?:プロジェクト|リポジトリ)(?:で|に|に対して|について|では)?",
)

_KOREAN = _Words(
    code="ko",
    remember=(
        r"기억해\s?(?:줘요|줘|주세요|주시겠어요|주실래요|둬요|둬|두세요|놔요|놔|놓아\s?줘|줄래요"
        r"|줄래|주라)|기억하세요"
        r"|잊지\s?(?:마요|마세요|마|말아\s?(?:줘요|줘|주세요)|말아요)"
        r"|명심(?:해\s?(?:줘|주세요|둬)|하세요|해)"
        r"|알아\s?(?:둬요|둬|두세요|놔)"
        r"|메모해\s?(?:줘요|줘|주세요|둬|두세요)"
        r"|(?:기억|메모리)(?:에|으로)?\s?(?:저장|기록)해\s?(?:줘요|줘|주세요|둬|두세요)"
        r"|외워\s?(?:줘요|줘|주세요|둬|두세요)"
    ),
    # « 잊지 마 » demande de retenir ; « 잊어버렸어 » dit un oubli
    forget=(
        r"잊어\s?(?:줘요|줘|주세요|주시겠어요|줄래요|줄래|버려\s?(?:줘|주세요)|버려요|버리세요"
        r"|버려)|잊으세요"
        r"|(?:기억|메모리)에서(?:는)?\s?(?:지워|삭제해|빼|없애)\s?(?:줘요|줘|주세요|버려|둬)?"
        r"|(?:(?:더\s?이상|이제)\s?)?기억하지\s?(?:마요|마세요|마|말아\s?줘|말아요)"
    ),
    lead_in=(
        r"안녕(?:하세요)?|저기(?:요)?|그리고|참|아|오|네|응|아니|좋아|그래|그럼|이제|부탁(?:해|해요|합니다)?"
        r"|ok|okay|hi|hey"
    ),
    question=r"뭐|무엇|무슨|누구|어디|언제|왜|어떻게|어느|몇|얼마",
    polite=(
        r"고마워(?:요)?|감사합니다|감사해요|부탁(?:해|해요|합니다|드려요|드립니다)|좋아요|ㅎㅎ|ㅋㅋ"
    ),
    joins=r"그리고|그다음|그\s?다음|또|그런데|그래서",
    reference=r"이거|이것|그거|그것|이걸|그걸|이것을|그것을|이\s?내용|그\s?내용|다음",
    memory=r"기억|메모리",
    particles=(
        r"(?:(?:라는|이라는|다는|는|란)\s?(?:것을|것|걸|거|사실을|사실|점을|점)|을|를|은|는|도)"
    ),
    request_end=r"(?:줘|줘요|주세요|세요|해|해요|봐|봐요|둬|자|라)",
    search=r"찾고\s?있|찾는\s?중",
    momentary=r"오늘(?!날)|어제|방금",
    asks_end=r"(?:줘|줘요|주세요|주십시오|줄래요?|주실래요|봐|봐요)",
    verb_last=True,
    all_projects=(
        r"(?:모든|전체)\s?(?:내\s?)?(?:프로젝트|저장소|레포)(?:에\s?대해서|에\s?대해|에서도|에서|에)?"
    ),
    this_project=(
        r"(?:이|현재|지금)\s?(?:프로젝트|저장소|레포)(?:에\s?대해서|에\s?대해|에서는|에서|에)?"
    ),
)

_ARABIC = _Words(
    code="ar",
    remember=_arabic(
        r"(?:و|ف)?(?:تذكر(?:ي|وا)?|احفظ(?:ي|وا)?|لا\s+تنس(?:ى|ي|وا)?"
        r"|(?:ضع|ضعي)\s+في\s+(?:اعتبارك|الاعتبار|ذهنك|بالك)|(?:خذ|خذي)\s+(?:في|بعين)\s+الاعتبار"
        r"|(?:سجل|سجلي|دون|دوني)(?=\s*(?:ان|بان|:|في\s+ذاكرت)))"
        r"|(?:هل\s+)?(?:يمكنك|تستطيع|ممكن|بامكانك)\s+(?:ان\s+)?(?:تتذكر|تحفظ)"
        r"|اريدك\s+ان\s+(?:تتذكر|تحفظ)"
    ),
    # « لا تنس » demande de retenir ; « نسيت » dit un oubli
    forget=_arabic(
        r"(?:و|ف)?(?:انس(?:ى|ي|وا)?"
        r"|(?:احذف|امسح|ازل|احذفي|امسحي|ازيلي)(?=[^.!?؟\n]{0,80}ذاكر)"
        r"|لا\s+تتذكر(?:ي)?\s+(?:بعد\s+الان|مجددا|مرة\s+اخرى)|توقف(?:ي)?\s+عن\s+تذكر)"
        r"|(?:هل\s+)?(?:يمكنك|تستطيع|ممكن|بامكانك)\s+(?:ان\s+)?تنس(?:ى|ي)?"
    ),
    lead_in=_arabic(
        r"مرحبا|اهلا|السلام\s+عليكم|حسنا|طيب|نعم|لا|ايضا|بالمناسبة|من\s+فضلك|رجاء|لو\s+سمحت"
        r"|ارجوك|شكرا|ممتاز|اذن|الان|مهم|اسمع|يا|و|ف"
    ) + r"|ok|okay",
    question=_arabic(r"ماذا|ما|من|اين|متى|لماذا|كيف|اي|كم|هل"),
    polite=_arabic(
        r"شكرا(?:\s+لك|\s+جزيلا)?|من\s+فضلك|رجاء|لو\s+سمحت|جزاك\s+الله\s+خيرا|ممتاز"
    ) + r"|ok",
    joins=_arabic(r"ثم|ايضا|لكن|كذلك|بعد\s+ذلك"),
    reference=_arabic(r"هذا|هذه|ذلك|تلك|هذا\s+الامر|ذلك\s+الامر|ما\s+يلي"),
    memory=_arabic(r"ذاكر"),
    # « أنني نباتي » : « أن » collé au pronom reste dans le fait
    connector=_arabic(r"(?:ان|بان)(?=\s)|(?=(?:ان|بان)\S)"),
    adverbs=_arabic(r"من\s+فضلك|بدلا\s+من\s+ذلك|ايضا|جيدا"),
    requests=_arabic(r"(?:و|ف)?(?:اعطني|قل\s+لي|اخبرني|اكتب|اقترح|ابحث|اشرح|ساعدني|ترجم|احسب"
                     r"|انشئ|اعرض|ارسل|لخص)"),
    search=_arabic(r"(?:ا|ن)بحث\s+عن"),
    momentary=(_arabic(r"(?:و|ف)?(?:اليوم|امس|البارحة|الليلة)") + r"(?![\w'’])"
               + "|" + _arabic(r"هذا\s+(?:الصباح|المساء)")),
    all_projects=_arabic(r"(?:ل|في)\s*(?:كل|جميع)\s+(?:مشاريعي|المشاريع|مستودعاتي|مشاريعنا)"),
    this_project=_arabic(r"(?:ل|في)\s*(?:هذا|ذلك)\s+(?:المشروع|المستودع)"),
)

_ALL_WORDS = (_SPANISH, _GERMAN, _ITALIAN, _PORTUGUESE, _DUTCH, _RUSSIAN, _CHINESE,
              _JAPANESE, _KOREAN, _ARABIC)
LANGUAGES = tuple(words.code for words in _ALL_WORDS)


# ── Motifs compilés ────────────────────────────────────────────────────────

_FLAGS = re.IGNORECASE
_BLOCK = r"\s*[:：]\s*"
# Ce qui reste d'un fait cité : « … » autour, ponctuation finale
_FACT_END_CHARS = " ?!.;,:。！？；，、：؟،؛…〜~"


@dataclass(frozen=True)
class _Language:
    """Une langue, ses motifs compilés."""

    words: _Words
    remember: Pattern[str]
    forget: Pattern[str]
    lead_in: Pattern[str]
    remember_lead_in: Pattern[str]
    question: Pattern[str]
    polite: Pattern[str]
    joins: Pattern[str]
    reference: Pattern[str]
    memory: Pattern[str]
    # Adverbes, renvois et politesse, seuls après le verbe (« Merk dir das, bitte »)
    tail: Pattern[str]
    # Une autre demande qui suit le fait dans sa phrase (« …, y dame una idea »)
    another: Optional[Pattern[str]]
    connector: Optional[Pattern[str]]
    adverbs: Optional[Pattern[str]]
    particles: Optional[Pattern[str]]
    # Verbe en dernier : le même verbe en tête, suivi de « : » (« 覚えておいて：… »)
    opening_remember: Optional[Pattern[str]]
    opening_forget: Optional[Pattern[str]]
    # Verbe en dernier : la demande suivie d'une virgule, dans une phrase qui demande
    clause_remember: Optional[Pattern[str]]
    clause_forget: Optional[Pattern[str]]
    request_end: Optional[Pattern[str]]
    # Verbe en tête : une autre demande qui ouvre le texte (« Dame una receta »)
    request_start: Optional[Pattern[str]]
    # Lecture sans demande (message_parts) : une recherche, et, verbe en dernier, la fin
    # d'une proposition qui demande ; ce qui ne vaut que pour la journée
    search: Optional[Pattern[str]]
    asks_end: Optional[Pattern[str]]
    momentary: Optional[Pattern[str]]
    script: Tuple[Pattern[str], ...]

    @property
    def code(self) -> str:
        return self.words.code


def _bounded(pattern: str, spaced: bool) -> str:
    """Le motif d'un verbe en tête, en mots entiers quand la langue a des espaces."""
    if spaced:
        return rf"(?<![\w'’-])(?:{pattern})(?![\w'’])"
    return rf"(?:{pattern})"


def _sequence(pattern: str, spaced: bool) -> str:
    """Une suite de ces mots, et rien d'autre (fullmatch)."""
    if spaced:
        return rf"(?:(?:{pattern})(?:\s+|$))+"
    return rf"(?:(?:{pattern})\s*)+"


def _compile(words: _Words) -> _Language:
    spaced = words.spaced
    lead_in = words.lead_in
    remember_lead_in = (f"{lead_in}|{words.remember_lead_in}" if words.remember_lead_in
                        else lead_in)
    if words.verb_last:
        # Le verbe ferme la phrase, avec sa politesse
        end = r"[\s〜~♪…ー]*$"
        remember = re.compile(rf"(?:{words.remember}){end}", _FLAGS)
        forget = re.compile(rf"(?:{words.forget}){end}", _FLAGS)
        opening = rf"^\s*(?:(?:{lead_in})[\s、，,!！]*)*(?P<verb>(?:{{verb}}))\s*[:：]"
        opening_remember = re.compile(opening.format(verb=words.remember), _FLAGS)
        opening_forget = re.compile(opening.format(verb=words.forget), _FLAGS)
        clause_remember = re.compile(rf"(?:{words.remember})(?=\s*[、，,])", _FLAGS)
        clause_forget = re.compile(rf"(?:{words.forget})(?=\s*[、，,])", _FLAGS)
        request_end = re.compile(rf"(?:{words.request_end}){end}", _FLAGS)
    else:
        remember = re.compile(_bounded(words.remember, spaced), _FLAGS)
        forget = re.compile(_bounded(words.forget, spaced), _FLAGS)
        opening_remember = opening_forget = clause_remember = clause_forget = None
        request_end = None
    scripts = {
        "ru": (_CYRILLIC_RE,), "ar": (_ARABIC_RE,), "zh": (_HAN_RE,), "ja": (_KANA_RE,),
        "ko": (_HANGUL_RE,),
    }.get(words.code, (_LATIN_RE,))
    return _Language(
        words=words,
        remember=remember,
        forget=forget,
        lead_in=re.compile(_sequence(lead_in, spaced), _FLAGS),
        remember_lead_in=re.compile(_sequence(remember_lead_in, spaced), _FLAGS),
        question=re.compile(rf"(?:{words.question})" + (r"(?![\w'’])" if spaced else ""), _FLAGS),
        polite=re.compile(_sequence(words.polite, spaced), _FLAGS),
        joins=re.compile(
            (rf"(?<![\w'’-])(?:{words.joins})(?![\w'’])" if spaced else rf"(?:{words.joins})"),
            _FLAGS),
        reference=re.compile(_sequence(words.reference, spaced), _FLAGS),
        memory=re.compile(rf"(?:{words.memory})", _FLAGS),
        tail=re.compile(_sequence("|".join(
            part for part in (words.adverbs, words.reference, words.polite) if part), spaced),
            _FLAGS),
        another=(re.compile(
            (rf"(?:\s*[,;，、；،]\s*(?:(?:{words.joins})\s+)?|\s+(?:{words.joins})\s+"
             # L'arabe colle « و » (et) au verbe : « …نباتي وأعطني فكرة »
             + (r"|\s+(?=[وف])" if words.code == "ar" else "") + ")"
             rf"(?:{words.requests})(?![\w'’])") if spaced
            else rf"(?:[，,；;、]|{words.joins})\s*(?:{words.requests})", _FLAGS)
            if words.requests else None),
        connector=(re.compile(rf"\s*,?\s*(?:{words.connector})"
                              + (r"(?![\w'’])" if spaced and words.code != "ar" else "")
                              + r"\s*", _FLAGS)
                   if words.connector else None),
        adverbs=(re.compile(rf"(?:\s*,?\s*(?:{words.adverbs})(?![\w'’]))+", _FLAGS)
                 if words.adverbs else None),
        particles=(re.compile(rf"(?:{words.particles})\s*$", _FLAGS)
                   if words.particles else None),
        opening_remember=opening_remember,
        opening_forget=opening_forget,
        clause_remember=clause_remember,
        clause_forget=clause_forget,
        request_end=request_end,
        request_start=(re.compile(
            rf"^(?:(?:{lead_in})(?:\s+|$))*(?:{words.requests})(?![\w'’])" if spaced
            else rf"^(?:(?:{lead_in})\s*)*(?:{words.requests})", _FLAGS)
            if words.requests else None),
        search=(re.compile((rf"(?<![\w'’-])(?:{words.search})" if spaced
                            else rf"(?:{words.search})"), _FLAGS)
                if words.search else None),
        asks_end=(re.compile(rf"(?:{words.asks_end})[\s〜~♪…ー]*$", _FLAGS)
                  if words.asks_end else None),
        momentary=(re.compile((rf"(?<![\w'’-])(?:{words.momentary})" if spaced
                               else rf"(?:{words.momentary})"), _FLAGS)
                   if words.momentary else None),
        script=scripts,
    )


_LANGUAGES = tuple(_compile(words) for words in _ALL_WORDS)


def _languages_for(message: str) -> List[_Language]:
    """Les langues dont le message a l'écriture (le japonais : des kana ; le
    chinois : des idéogrammes sans kana)."""
    kana = bool(_KANA_RE.search(message))
    found = []
    for language in _LANGUAGES:
        if language.code == "zh" and kana:
            continue
        if any(script.search(message) for script in language.script):
            found.append(language)
    return found


# ── Les demandes d'un message ──────────────────────────────────────────────


@dataclass(frozen=True)
class _Request:
    """Une demande de retenir ou d'oublier trouvée dans un message."""

    language: _Language
    kind: str
    # Le verbe (verbe en dernier : avec sa politesse)
    start: int
    end: int
    # Sa phrase, sans sa ponctuation finale
    sentence_start: int
    sentence_end: int
    # Verbe en dernier, mais en tête, suivi de « : »
    opening: bool = False

    @property
    def verb_last(self) -> bool:
        return self.language.words.verb_last and not self.opening


def _sentence_of(message: str, position: int) -> Tuple[int, int]:
    """La phrase qui contient position (sans sa ponctuation finale)."""
    start = max(message.rfind(mark, 0, position) for mark in _ENDS) + 1
    ends = [found for found in (message.find(mark, position) for mark in _ENDS) if found >= 0]
    return start, min(ends) if ends else len(message)


def _only(text: str, pattern: Pattern[str]) -> bool:
    """text, sans sa ponctuation, n'est-il fait que de ces mots (ou de rien) ?"""
    cleaned = _PUNCTUATION_RE.sub(" ", text or "").strip()
    return not cleaned or bool(pattern.fullmatch(cleaned))


def _recalls(message: str, request: _Request) -> bool:
    """
    « Recuerda: ¿dónde vivo? », « 记住，我住在哪里？ » demandent de se souvenir : la
    phrase finit par une question, et ce qui suit le verbe s'ouvre sur un mot
    interrogatif (en chinois : en contient un). « Lembra? », le verbe seul en
    question, aussi. « ¿Puedes recordar que soy vegetariano? » reste une demande.
    """
    rest = message[request.end:request.sentence_end]
    after = message[request.sentence_end:request.sentence_end + 1]
    if not after or after not in _QUESTION_MARKS:
        return False
    stripped = rest.lstrip(" \t:,-¿¡，、：「『\"'«“")
    if not stripped.strip():
        return True
    if request.language.words.spaced:
        return bool(request.language.question.match(stripped))
    return bool(request.language.question.search(stripped))


def _requests(message: str, kind: str) -> List[_Request]:
    """Les demandes de ce genre (REMEMBER, FORGET) du message, dans l'ordre."""
    if not message:
        return []
    found: List[_Request] = []
    for language in _languages_for(message):
        pattern = language.remember if kind == REMEMBER else language.forget
        lead_in = language.remember_lead_in if kind == REMEMBER else language.lead_in
        if language.words.verb_last:
            opening = language.opening_remember if kind == REMEMBER else language.opening_forget
            for body in _SENTENCE_BODY_RE.finditer(message):
                start, end = body.span()
                closing = pattern.search(body.group(0))
                if closing is not None:
                    found.append(_Request(language, kind, start + closing.start(),
                                          start + closing.end(), start, end))
                    continue
                verb_first = opening.match(body.group(0)) if opening is not None else None
                if verb_first is not None:
                    found.append(_Request(language, kind, start + verb_first.start("verb"),
                                          start + verb_first.end(), start, end, True))
                    continue
                # « 犬のことは忘れて、レシピを教えて » : la demande, puis une autre
                clause = language.clause_remember if kind == REMEMBER else language.clause_forget
                within = clause.search(body.group(0)) if clause is not None else None
                if within is not None and language.request_end.search(body.group(0)):
                    found.append(_Request(language, kind, start + within.start(),
                                          start + within.end(), start, end))
            continue
        for match in pattern.finditer(message):
            start, end = _sentence_of(message, match.start())
            if not _only(message[start:match.start()], lead_in):
                continue
            request = _Request(language, kind, match.start(), match.end(), start, end)
            if kind == REMEMBER and _recalls(message, request):
                continue
            found.append(request)
    return sorted(found, key=lambda request: request.start)


def asks_to_remember(message: str) -> bool:
    """Le message demande-t-il de retenir quelque chose, dans l'une de ces langues ?"""
    return bool(_requests(message, REMEMBER))


def asks_to_forget(message: str) -> bool:
    """Le message demande-t-il d'oublier quelque chose, dans l'une de ces langues ?"""
    return bool(_requests(message, FORGET))


def request_languages(message: str) -> List[str]:
    """Les langues des demandes de retenir ou d'oublier du message (« Olvida que… » :
    ["es"]). Un verbe peut être de deux langues (« memoriza » : es, pt)."""
    codes: List[str] = []
    for kind in (REMEMBER, FORGET):
        for request in _requests(message, kind):
            if request.language.code not in codes:
                codes.append(request.language.code)
    return codes


# ── Ce qui suit ou précède le verbe ────────────────────────────────────────


def _after_adverbs(message: str, request: _Request) -> int:
    """Position de ce qui suit le verbe et ses adverbes (« Recuerda mejor que… »)."""
    position = request.end
    adverbs = request.language.adverbs
    if adverbs is not None:
        found = adverbs.match(message, position)
        if found is not None:
            position = found.end()
    return position


def _strip_lead_in(text: str, language: _Language) -> str:
    """text sans les mots d'introduction qui l'ouvrent (« ねえ、私は… » → « 私は… »)."""
    words = language.words
    # En mots entiers quand la langue a des espaces : « 아니, … » n'est pas « 아 » + « 니 »
    boundary = r"(?![\w'’])" if words.spaced else ""
    pattern = re.compile(rf"^\s*(?:(?:{words.lead_in}){boundary}[\s、，,!！:：]*)+", _FLAGS)
    found = pattern.match(text)
    return text[found.end():] if found else text


# Coréen : « 채식주의자라는 걸 », « 서울에 산다는 걸 » → « 채식주의자다 », « 서울에 산다 »
_KOREAN_CLAUSE_RE = re.compile(r"(이)?라는\s?(?:것을|것|걸|거|사실을|사실|점을|점)$|"
                               r"다는\s?(?:것을|것|걸|거|사실을|사실|점을|점)$")


def _strip_particles(text: str, language: _Language) -> str:
    """Verbe en dernier : le fait sans ce qui le relie au verbe (« …ということを »,
    « …라는 걸 »)."""
    text = text.rstrip(" \t、，,")
    if language.code == "ko":
        found = _KOREAN_CLAUSE_RE.search(text)
        if found is not None:
            return (text[:found.start()] + (found.group(1) or "") + "다").strip()
    if language.particles is None:
        return text.strip()
    return language.particles.sub("", text).strip()


def _clean(text: str, language: _Language) -> Optional[str]:
    """Un fait lu par ces règles : sans espaces, guillemets ni politesse finale ;
    None si c'est une question ou un renvoi à ce qui précède."""
    fact = re.sub(r"\s+", " ", text or "").strip()
    if not fact or fact[-1] in _QUESTION_MARKS:
        return None
    fact = fact.rstrip(_FACT_END_CHARS).strip()
    separator = r"(?:[\s,，、]+|^)" if language.words.spaced else r"[\s,，、]*"
    polite = re.compile(rf"{separator}(?:{language.words.polite})$", _FLAGS)
    while True:
        trimmed = polite.sub("", fact).rstrip(_FACT_END_CHARS).strip()
        if trimmed == fact:
            break
        fact = trimmed
    if len(fact) > 1 and fact[0] in _QUOTES and fact[-1] in _QUOTES:
        fact = fact[1:-1].strip().rstrip(_FACT_END_CHARS).strip()
    if not fact or language.reference.fullmatch(fact):
        return None
    return fact


def _fact_span(message: str, request: _Request, block: bool) -> Optional[Tuple[int, int]]:
    """
    Où est, dans le message, le fait que la demande donne à retenir : après le
    verbe et ce qui l'introduit (« que », « dass », « : », rien en chinois), ou
    avant le verbe quand il vient en dernier. block : seulement un bloc « : », qui
    va jusqu'à la fin du message (une procédure, plusieurs phrases).
    """
    language = request.language
    if request.verb_last:
        if block:
            return None
        return request.sentence_start, request.start
    position = _after_adverbs(message, request)
    marker = re.compile(rf"(?:\s*(?:{language.words.reference}))?{_BLOCK}", _FLAGS)
    found = marker.match(message, position)
    if found is not None:
        return found.end(), len(message) if block else request.sentence_end
    if block:
        return None
    if language.connector is not None:
        found = language.connector.match(message, position)
        if found is None:
            return None
        return found.end(), request.sentence_end
    if not language.words.spaced:
        # Chinois : le fait suit le verbe (« 记住我住在北京 », « 记住，我… »)
        found = re.compile(r"[\s，,]*").match(message, position)
        return found.end(), request.sentence_end
    return None


def _fact_of(message: str, request: _Request, block: bool = False) -> Optional[str]:
    """Le fait d'une demande de retenir, ou None (voir _fact_span)."""
    span = _fact_span(message, request, block)
    if span is None:
        return None
    text = message[span[0]:span[1]]
    if request.verb_last:
        text = _strip_lead_in(_strip_particles(text, request.language), request.language)
    elif not block and request.language.another is not None:
        # « Recuerda que soy vegetariano y dame una idea de cena » : le fait s'arrête
        # avant l'autre demande
        found = request.language.another.search(text)
        if found is not None:
            text = text[:found.start()]
    if block:
        # Un bloc s'arrête à la première question ou à la politesse qui le suit
        kept = []
        # « build.bat » reste entier : un point latin ne coupe que suivi d'un espace
        for sentence in re.split(r"(?<=[.!?])\s+|(?<=[。！？؟])\s*", text.strip()):
            stripped = sentence.strip()
            if not stripped:
                continue
            if kept and (stripped[-1] in _QUESTION_MARKS
                         or _only(stripped, request.language.polite)):
                break
            kept.append(stripped)
        text = " ".join(kept)
    return _clean(text, request.language)


def extract_remember_request(message: str) -> Optional[str]:
    """Le fait que le message demande de retenir, dans l'une de ces langues (« Recuerda
    que vivo en Madrid » → « vivo en Madrid », « 我是素食者，记住… » non : le verbe ouvre
    sa phrase), ou None. À vérifier par l'appelant (is_rememberable)."""
    for request in _requests(message, REMEMBER):
        fact = _fact_of(message, request)
        if fact:
            return fact
    return None


def remember_block(message: str) -> Optional[str]:
    """Le bloc d'une demande « Recuerda esto: … », « Merk dir: … », en entier, ou None."""
    for request in _requests(message, REMEMBER):
        fact = _fact_of(message, request, block=True)
        if fact:
            return fact
    return None


def _only_polite(text: str, language: _Language) -> bool:
    """text n'est-il que de la politesse et de la ponctuation (« Gracias. ») ?"""
    for sentence in _SENTENCE_BODY_RE.findall(text or ""):
        if not _only(sentence, language.polite):
            return False
    return True


def _says_one_thing(request: _Request, message: str) -> bool:
    """
    Verbe en dernier : la phrase de la demande ne dit-elle qu'une chose, sans autre
    demande avant ni après ? « 私はベジタリアンだと覚えておいて » : oui ;
    « 犬のことは忘れて、レシピを教えて », « レシピを教えて。犬のことは忘れて » : non.
    """
    language = request.language
    if not _only(message[:request.sentence_start], language.remember_lead_in):
        return False
    said = _strip_lead_in(message[request.sentence_start:request.start], language)
    said = said.rstrip(" \t、，,")
    if len(_clauses(said, language)) > 1 or language.joins.search(said):
        return False
    return _only_polite(message[request.end:], language)


def remember_verb_last(message: str) -> bool:
    """La demande de retenir ferme-t-elle sa phrase (japonais, coréen) ? Le fait est
    alors tout ce qui précède le verbe, quels que soient les mots du modèle
    (is_only_remember_request)."""
    requests = _requests(message, REMEMBER)
    return bool(requests) and requests[0].verb_last


def is_only_remember_request(message: str, fact: str) -> bool:
    """
    Le message ne fait-il que demander de retenir fact, dans l'une de ces langues ?
    « Hola, recuerda que vivo en Madrid. ¡Gracias! » : oui ; « … y dime qué tiempo
    hace » : non. Verbe en dernier, le fait est tout ce qui précède le verbe : sa
    phrase seule décide (« 내가 채식주의자라는 걸 기억해 줘 », retenu « 내가 채식주의자다 »
    ou reformulé par le modèle, ne s'y lit pas tel quel).
    """
    if not fact:
        return False
    for request in _requests(message, REMEMBER):
        if request.verb_last:
            return _says_one_thing(request, message)
        span = _fact_span(message, request, False)
        if span is None or message.find(fact, span[0], span[1]) < 0:
            continue
        language = request.language
        start = message.find(fact, span[0], span[1])
        after = message[start + len(fact):]
        if not _only(message[:request.start], language.remember_lead_in):
            return False
        between = message[request.end:start]
        if re.search(r"[^\W\d_]", _connective_rest(between, language)):
            return False
        return _only_polite(after, language)
    return False


def _connective_rest(text: str, language: _Language) -> str:
    """Ce qui reste entre le verbe et le fait, sans adverbes, « que », « : » ni virgules."""
    rest = text
    if language.adverbs is not None:
        rest = language.adverbs.sub(" ", rest)
    if language.connector is not None:
        rest = language.connector.sub(" ", rest)
    rest = re.sub(rf"(?:{language.words.reference})?{_BLOCK}", " ", rest, flags=_FLAGS)
    return re.sub(r"[\s,，、:：]+", " ", rest).strip()


def only_asks_to_remember(message: str) -> bool:
    """
    Le message ne fait-il que demander de retenir ce qui précède, sans dire quoi ?
    « Recuérdalo », « Merk dir das, bitte », « 记住这个 », « これを覚えておいて » :
    oui ; « Recuerda que… » : non.
    """
    requests = _requests(message, REMEMBER)
    if not requests:
        return False
    request = requests[0]
    language = request.language
    if request.verb_last:
        if not _only(message[:request.sentence_start], language.remember_lead_in):
            return False
        said = _strip_lead_in(_strip_particles(message[request.sentence_start:request.start],
                                               language), language)
        said = said.strip(" 、，,")
        if said and not language.reference.fullmatch(said):
            return False
        return _only_polite(message[request.end:], language)
    if not _only(message[:request.start], language.remember_lead_in):
        return False
    return _only(message[request.end:], language.tail)


def _clauses(text: str, language: _Language) -> List[str]:
    """Les propositions de text : coupées aux virgules et aux mots qui en ouvrent
    une autre (« y », « und », « 然后 »), et en arabe au « و » collé au mot suivant."""
    words = language.words
    joins = (rf"\s+(?:{words.joins})\s+" if words.spaced else rf"(?:{words.joins})")
    parts = [rf"[{_CLAUSE_MARKS}]", joins]
    if words.code == "ar":
        parts.append(r"\s+و(?=\S)")
    return [part.strip() for part in re.split("|".join(parts), text, flags=_FLAGS)
            if part and part.strip()]


def only_asks_to_forget(message: str) -> bool:
    """
    Le message ne fait-il que demander d'oublier, dans l'une de ces langues ?
    « Olvida que tengo un perro. ¡Gracias! », « Olvida que fumo y que bebo café » :
    oui ; « …y dame una receta », une question, ou une autre demande avant : non.
    Dans le doute, non : la réponse se limite alors à confirmer l'oubli, et une
    tâche sautée est pire qu'une phrase de trop.
    """
    if not message or any(mark in message for mark in _QUESTION_MARKS):
        return False
    requests = _requests(message, FORGET)
    if not requests:
        return False
    request = requests[0]
    language = request.language
    if request.verb_last:
        return _says_one_thing(request, message)
    if not _only(message[:request.start], language.lead_in):
        return False
    if not _only_polite(message[request.sentence_end:], language):
        return False
    clauses = _clauses(message[request.end:request.sentence_end], language)
    connector = language.connector
    # « …y que bebo café » continue le fait ; « …y dame una receta » demande autre chose
    return all(connector is not None and connector.match(clause) for clause in clauses[1:])


# « 把我抽烟这件事忘掉吧 » : le fait entre « 把 » et le verbe
_BA_RE = re.compile(r"^把(?P<fact>.*?)(?:忘掉|忘了吧|忘记|忘記)$")


def forget_object(message: str) -> Optional[str]:
    """
    Ce que la demande d'oubli désigne, sa première proposition : « Olvida que tengo
    un perro y dame una receta » → « tengo un perro », « 犬を飼っていることは忘れて »
    → « 犬を飼っている » ; None sans demande d'oubli.
    """
    for request in _requests(message, FORGET):
        language = request.language
        if request.verb_last:
            said = _strip_lead_in(_strip_particles(
                message[request.sentence_start:request.start], language), language)
            return said.strip(" 、，,") or None
        ba = _BA_RE.match(message[request.start:request.end])
        if ba is not None:
            return ba.group("fact").strip() or None
        position = _after_adverbs(message, request)
        if language.connector is not None:
            found = language.connector.match(message, position)
            if found is not None:
                position = found.end()
        clauses = _clauses(message[position:request.sentence_end].strip(" ，,：:"), language)
        return clauses[0] if clauses else None
    return None


def is_request(text: str) -> bool:
    """
    Le texte demande-t-il quelque chose (une question, une autre demande) plutôt qu'il ne
    donne une information ? « Dame una receta », « 告诉我天气 », « レシピを教えて », « ¿Qué
    hora es? » : oui ; « Mi hermana se llama Lucía » : non.
    """
    text = (text or "").strip()
    if not text:
        return False
    if text.rstrip(" .!。！")[-1:] in _QUESTION_MARKS:
        return True
    cleaned = _PUNCTUATION_RE.sub(" ", text).strip()
    for language in _languages_for(text):
        if language.request_start is not None and language.request_start.match(cleaned):
            return True
        if language.words.verb_last and language.request_end is not None:
            bodies = _SENTENCE_BODY_RE.findall(text)
            if bodies and language.request_end.search(bodies[-1]):
                return True
    return False


# ── Ce qu'un message dit, et ce qu'il demande (lecture sans demande) ─────────

# Une phrase, avec sa ponctuation finale
_SENTENCE_RE = re.compile(r"[^.!?\n。！？؟]+[.!?\n。！？؟]*")
_SENTENCE_TAIL = ".!?\n。！？؟ \t"
# Ce qui sépare deux propositions : point-virgule, virgule, deux-points (pas ceux d'un
# nombre : « 3,5 », « 10:30 »)
_PART_SPLIT_RE = re.compile(r"[;，、；：،؛]|[,:](?!\d)|(?<!\d)[,:]")


@dataclass(frozen=True)
class Part:
    """Une proposition d'un message : sa place (message[start:end]), et si elle dit
    quelque chose plutôt qu'elle ne demande (says)."""

    start: int
    end: int
    text: str
    says: bool


def _asks(text: str, languages: List[_Language], question: bool, last: bool) -> bool:
    """La proposition demande-t-elle au lieu de dire (message_parts) ?"""
    if text.lstrip(" \t\"'«“(").startswith("¿"):
        return True
    cleaned = _PUNCTUATION_RE.sub(" ", text).strip()
    for language in languages:
        if language.request_start is not None and language.request_start.match(cleaned):
            return True
        if language.search is not None and language.search.search(cleaned):
            return True
        if last and language.asks_end is not None and language.asks_end.search(
                text.rstrip(_FACT_END_CHARS)):
            return True
        if question:
            rest = _strip_lead_in(cleaned, language)
            pattern = language.question
            if pattern.match(rest) if language.words.spaced else pattern.search(rest):
                return True
    return False


def message_parts(message: str) -> List[Part]:
    """
    Les propositions du message, coupées à sa ponctuation. Ne disent rien :
      - la dernière d'une phrase qui finit par une question (« Trabajo de noche,
        ¿tienes consejos? ») et, dans une question, celle qui s'ouvre sur un mot
        interrogatif ;
      - celle qui s'ouvre sur « ¿ » ou sur un verbe qui demande (« посоветуй »,
        « Schreib… », « 写一首… ») ; en japonais et en coréen, la fin d'une phrase qui
        demande (« …書いて », « …써 줘 ») ;
      - une recherche (« Я ищу роман… », « 我在找… », « Busco… ») : sa demande du
        moment, comme « je cherche… » en français (core/chat_memory.py) ;
      - ce qui ne vaut que pour la journée (« Сегодня я опоздал на работу », « Hoje
        cheguei atrasado ») : le vrai modèle en tirait « je suis souvent en retard au
        travail » ou « j'ai travaillé aujourd'hui » ;
      - celle qui n'est que salut ou politesse (« Привет », « 谢谢 »).
    """
    message = message or ""
    languages = _languages_for(message)
    parts: List[Part] = []
    for sentence in _SENTENCE_RE.finditer(message):
        question, spans = _sentence_parts(message, sentence)
        for index, (start, end) in enumerate(spans):
            text = message[start:end]
            last = index == len(spans) - 1
            asks = (question and last) or _asks(text, languages, question, last)
            parts.append(Part(start, end, text,
                              not asks and not _says_nothing_lasting(text, languages)))
    return parts


def _sentence_parts(message: str, sentence: Match[str]) -> Tuple[bool, List[Tuple[int, int]]]:
    """La phrase finit-elle par une question, et la place de ses propositions dans le
    message, sans les espaces qui les entourent (message_parts)."""
    whole = sentence.group(0)
    body = whole.rstrip(_SENTENCE_TAIL)
    question = any(mark in whole[len(body):] for mark in _QUESTION_MARKS)
    spans, begin = [], sentence.start()
    for separator in _PART_SPLIT_RE.finditer(body):
        spans.append((begin, sentence.start() + separator.start()))
        begin = sentence.start() + separator.end()
    spans.append((begin, sentence.start() + len(body)))
    trimmed = []
    for start, end in spans:
        raw = message[start:end]
        if raw.strip():
            trimmed.append((start + len(raw) - len(raw.lstrip()),
                            end - (len(raw) - len(raw.rstrip()))))
    return question, trimmed


def _says_nothing_lasting(text: str, languages: List[_Language]) -> bool:
    """La proposition n'est-elle que salut, politesse, ou ce qui ne vaut que pour la
    journée (message_parts) ?"""
    return any(_only(text, language.lead_in) or _only(text, language.polite)
               or (language.momentary is not None and bool(language.momentary.search(text)))
               for language in languages)


def forgets_a_fact(message: str) -> bool:
    """
    La demande d'oubli vise-t-elle un fait (« olvida que tengo un perro », « 忘掉我住在
    北京 », « 犬を飼っていることは忘れて ») ou la mémoire (« borra de tu memoria… ») ?
    « Olvídalo », « それは忘れて » peuvent ne renvoyer qu'à la conversation.
    """
    for request in _requests(message, FORGET):
        language = request.language
        if language.memory.search(message):
            return True
        if request.verb_last:
            said = _strip_lead_in(_strip_particles(
                message[request.sentence_start:request.start], language), language)
            said = said.strip(" 、，,")
            if said and not language.reference.fullmatch(said):
                return True
            continue
        if message[request.start] == "把":
            return True  # « 把我住在北京这件事忘掉 » : le fait est avant le verbe
        position = _after_adverbs(message, request)
        if language.connector is not None:
            if language.connector.match(message, position):
                return True
            continue
        if not language.words.spaced:
            rest = message[position:request.sentence_end].strip(" ，,：:")
            if word_count(rest) >= 2 and not language.reference.fullmatch(rest):
                return True
    return False


# ── Conversation Code : pour quels projets ─────────────────────────────────


def scope_phrases(which: str) -> Tuple[str, str]:
    """
    « Pour tous mes projets » (which = "all") ou « pour ce projet » ("this") dans ces
    langues, en deux motifs : ceux des langues à espaces, à lire en mots entiers, et
    ceux du chinois, du japonais et du coréen, collés à leurs voisins.
    """
    spaced: List[str] = []
    joined: List[str] = []
    for words in _ALL_WORDS:
        pattern = words.all_projects if which == "all" else words.this_project
        if not pattern:
            continue
        (spaced if words.spaced and not words.verb_last else joined).append(pattern)
    return "|".join(spaced), "|".join(joined)

