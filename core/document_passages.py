"""
Sélection des passages d'un long document selon la question

Quand un document chargé dépasse la place qui lui revient dans le prompt, le
modèle reçoit le début du document puis les passages les plus proches de la
question, au lieu des seuls premiers caractères. Score lexical BM25, insensible
aux accents, avec un bonus quand deux mots de la question se suivent dans le
passage (« section 15 », « point éclair ») : numéros, codes et noms de produits
comptent quelle que soit la langue du document. S'y ajoute, quand le modèle
multilingue est disponible (core/passage_embeddings.py), un score de sens qui
relie une question et un passage écrits dans deux langues différentes.
"""

import math
import re
import unicodedata
from collections import Counter
from typing import Callable, List, Optional, Set

# Similarité de sens de chaque passage à la question (None : indisponible)
Similarity = Callable[[str, List[str]], Optional[List[float]]]

# Taille visée d'un passage, découpé sur les fins de ligne (en caractères)
CHUNK_CHARS = 1000
# Le début du document n'est ajouté que s'il tient dans cette part du budget
HEAD_SHARE = 0.15
# Nombre de meilleurs passages complétés par leurs voisins (suite, puis début)
TOP_HITS = 3
# Longueur de la racine retenue pour comparer les mots
PREFIX_CHARS = 5

# Mots de structure équivalents (les FDS françaises disent « rubrique »)
_SYNONYMS = {"rubrique": "section", "chapitre": "section", "chapter": "section"}

_STOPWORDS = {
    # Français
    "a", "au", "aux", "avec", "ce", "ces", "cet", "cette", "dans", "de", "des",
    "dit", "dis", "donne", "du", "elle", "en", "est", "et", "il", "ils", "je",
    "la", "le", "les", "leur", "lui", "ma", "me", "mes", "moi", "mon", "ne",
    "ni", "nous", "on", "ou", "par", "parle", "pas", "pour", "qu", "que",
    "quel", "quelle", "quelles", "quels", "qui", "quoi", "sa", "se", "ses",
    "son", "sont", "sur", "ta", "te", "tes", "toi", "ton", "tu", "un", "une",
    "vos", "votre", "vous", "y", "document", "fichier",
    # Mots de question (« comment faire », « faut-il », « peut-on »...)
    "avoir", "comment", "dois", "doit", "etre", "fait", "faire", "faut", "peut",
    "peux", "veut", "veux",
    # Anglais
    "an", "and", "are", "as", "at", "be", "by", "can", "do", "does", "for",
    "from", "how", "in", "is", "it", "of", "or", "should", "the", "this", "to",
    "what", "which", "with",
}

_BM25_K1 = 1.5
_BM25_B = 0.75


def select_passages(
    text: str, query: str, limit: int, similarity: Optional[Similarity] = None
) -> str:
    """
    Extraits d'un document qui tiennent dans `limit` caractères

    Args:
        text: Texte complet du document
        query: Question de l'utilisateur
        limit: Nombre maximal de caractères d'extraits
        similarity: Similarité de sens de chaque passage à la question ; sans
            elle (ou si elle renvoie None), seuls les mots comptent

    Returns:
        Le texte entier s'il tient ; sinon une mention de sélection, puis le
        début du document et les passages les plus pertinents, dans l'ordre
        du document et séparés par « […] »
    """
    if len(text) <= limit:
        return text

    # Au moins quatre passages par budget, même quand il est petit
    size = min(CHUNK_CHARS, max(200, limit // 4))
    chunks = _split(text, size)
    scores = _scores(chunks, query)
    meaning = similarity(query, chunks) if similarity else None
    chosen: Set[int] = set()
    used = 0

    def take(index: int) -> None:
        nonlocal used
        if index < len(chunks) and index not in chosen and used + len(chunks[index]) <= limit:
            chosen.add(index)
            used += len(chunks[index])

    if len(chunks[0]) <= limit * HEAD_SHARE:
        take(0)

    # Meilleurs passages (mots et sens), puis leurs voisins (un titre précède
    # souvent la réponse), puis les autres passages contenant des mots de la
    # question ; le budget restant n'est pas rempli
    top = _ranked(_combine(scores, meaning))[:TOP_HITS]
    ranked = _ranked(scores)
    for index in top + [i + 1 for i in top] + [i - 1 for i in top if i > 0] + ranked:
        take(index)

    if not ranked:
        # Aucun mot de la question dans le document (« résume ce document ») :
        # extraits répartis jusqu'à la fin
        step = max(1, math.ceil(len(chunks) / max(1, limit // size)))
        for index in range(0, len(chunks), step):
            take(index)

    parts, previous = [], -1
    for index in sorted(chosen):
        if index != previous + 1:
            parts.append("[…]")
        parts.append(chunks[index])
        previous = index
    if previous != len(chunks) - 1:
        parts.append("[…]")

    note = (
        f"[Document long : extraits choisis selon la question ({used} caractères sur "
        f"{len(text)}). Si la réponse n'y figure pas, dis-le au lieu d'affirmer que "
        "l'information n'existe pas.]"
    )
    return "\n".join([note, *parts])


def _split(text: str, size: int) -> List[str]:
    """Passages d'environ `size` caractères, coupés sur les fins de ligne."""
    chunks, current = [], ""
    for line in text.splitlines(keepends=True):
        while len(line) > size:  # ligne très longue : coupe sur un espace
            cut = line.rfind(" ", 0, size)
            cut = cut if cut > 0 else size
            if current:
                chunks.append(current)
                current = ""
            chunks.append(line[:cut])
            line = line[cut:]
        if current and len(current) + len(line) > size:
            chunks.append(current)
            current = ""
        current += line
    if current:
        chunks.append(current)
    return chunks


def _terms(text: str) -> List[str]:
    """Mots significatifs : minuscules, sans accents, synonymes ramenés à un seul mot."""
    normalized = unicodedata.normalize("NFKD", text.lower())
    normalized = "".join(c for c in normalized if not unicodedata.combining(c))
    terms = []
    for word in re.findall(r"[a-z0-9]+", normalized):
        word = _SYNONYMS.get(word, word)
        if word not in _STOPWORDS and (len(word) > 1 or word.isdigit()):
            # Racine grossière : « charger » et « chargent » donnent « charg »
            terms.append(word[:PREFIX_CHARS] if word.isalpha() else word)
    return terms


def _scores(chunks: List[str], query: str) -> List[float]:
    """Score BM25 de chaque passage, plus un bonus par paire de mots qui se suivent."""
    asked = _terms(query)
    if not asked:
        return [0.0] * len(chunks)
    pairs = set(zip(asked, asked[1:]))

    chunk_terms = [_terms(chunk) for chunk in chunks]
    counts = [Counter(terms) for terms in chunk_terms]
    average = sum(map(len, chunk_terms)) / len(chunks) or 1.0
    idf = {}
    for term in set(asked):
        found = sum(term in count for count in counts)
        idf[term] = math.log(1 + (len(chunks) - found + 0.5) / (found + 0.5))

    return [
        _bm25(count, len(terms) / average, idf)
        + sum(idf[a] + idf[b] for a, b in pairs & set(zip(terms, terms[1:])))
        for terms, count in zip(chunk_terms, counts)
    ]


def _bm25(count: Counter, relative_length: float, idf: dict) -> float:
    """Score BM25 d'un passage, de longueur relative à la moyenne des passages."""
    norm = _BM25_K1 * (1 - _BM25_B + _BM25_B * relative_length)
    return sum(
        weight * count[term] * (_BM25_K1 + 1) / (count[term] + norm)
        for term, weight in idf.items()
        if count[term]
    )


def _ranked(scores: List[float]) -> List[int]:
    """Indices des passages de score positif, du meilleur au moins bon."""
    return sorted((i for i, s in enumerate(scores) if s > 0), key=lambda i: (-scores[i], i))


def _combine(words: List[float], meaning: Optional[List[float]]) -> List[float]:
    """Score des mots et score de sens, chacun ramené entre 0 et 1, à poids égal."""
    best = max(words, default=0.0)
    combined = [score / best for score in words] if best > 0 else [0.0] * len(words)
    if not meaning or len(meaning) != len(words):
        return combined
    low, high = min(meaning), max(meaning)
    if high <= low:
        return combined
    return [score + (sense - low) / (high - low) for score, sense in zip(combined, meaning)]
