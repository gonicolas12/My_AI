"""
Documents de la mémoire (onglet Documents) pour le modèle : lequel lire selon
la demande, sans les confondre

Deux documents peuvent porter le même nom : « rapport.pdf » ajouté à la main,
un autre « rapport.pdf » joint au chat, « projet/rapport.pdf » venu d'un
dossier déposé. Le modèle les distingue par leur libellé (document_label) :
nom ou chemin dans son dossier, origine et date d'ajout.

- named_documents : les documents qu'un message nomme (nom de fichier avec son
  extension, chemin dans un dossier, ou nom distinctif sans extension : « le
  rapport trimestriel ») ; un dossier nommé lui aussi ne garde que les siens.
- named_folders : les dossiers déposés qu'un message désigne (« le dossier
  projet »).
- memory_documents_block : le bloc du prompt système de la réponse, avec le
  contenu utile de chacun (sous son libellé, numéroté s'ils sont plusieurs) ;
  quand plusieurs portent le même nom, un avertissement avant eux et un rappel
  après : répondre pour chacun, sauf si la question dit lequel.
- results_block : les extraits de l'outil search_memory, groupés par document,
  sous leur libellé.
"""

import re
from datetime import datetime
from pathlib import PurePosixPath
from typing import Any, Callable, Dict, Iterable, List, Optional, Set

# Documents nommés mis dans le prompt, au plus (les plus récents)
MAX_NAMED = 3
# Dossier nommé : fichiers listés et extraits, au plus
FOLDER_FILES_SHOWN = 40
FOLDER_PASSAGES = 4
# Extrait d'un résultat de search_memory (caractères)
RESULT_CHARS = 500

# Tout ce qui n'est ni lettre ni chiffre : espaces, _, -, ., mais aussi la
# ponctuation collée à un nom (« dossier projet, il… », « (projet) »)
_SEPARATORS = re.compile(r"[\W_]+")
_FOLDER_WORDS = re.compile(r"\b(?:dossier|dossiers|répertoire|folder|directory)\b",
                           re.IGNORECASE)


def _normalized(text: str) -> str:
    """Minuscules, tout ce qui n'est ni lettre ni chiffre réduit à une espace,
    bordé d'espaces : « Dossier projet, il » → « dossier projet il »."""
    return f" {_SEPARATORS.sub(' ', str(text or '').lower()).strip()} "


def base_name(name: str) -> str:
    """Nom du fichier d'un document : « projet/docs/rapport.pdf » → « rapport.pdf »."""
    return PurePosixPath(str(name or "").replace("\\", "/")).name or str(name or "")


def _when(created: str) -> str:
    """« 17/11/2026 à 11:19 » d'une date ISO ; "" si elle est illisible."""
    try:
        return datetime.fromisoformat(str(created)).strftime("%d/%m/%Y à %H:%M")
    except (TypeError, ValueError):
        return ""


def document_label(doc: Dict[str, Any]) -> str:
    """« « rapport.pdf » — ajouté à la main le 17/11/2026 à 11:19 », ou
    « « projet/rapport.pdf » — fichier du dossier « projet », déposé le … »,
    ou « … — joint au chat le … ».

    Args:
        doc: document de MemoryStore.document_index, ou métadonnées d'un morceau
            (document_name, folder, source, created)
    """
    name = str(doc.get("name") or doc.get("document_name") or "document")
    folder = doc.get("folder")
    when = _when(doc.get("created", ""))
    if folder:
        origin = f"fichier du dossier « {folder} », déposé"
    elif doc.get("source") == "manual":
        origin = "ajouté à la main"
    else:
        origin = "joint au chat"
    return f"« {name} » — {origin}" + (f" le {when}" if when else "")


def _names_file(doc: Dict[str, Any], query: str, words: str) -> bool:
    """Le message nomme-t-il ce document ? Par son chemin, son nom de fichier
    (avec extension), ou un nom distinctif sans extension (deux mots, ou un
    chiffre : « rapport trimestriel », « facture2024 »)."""
    name = str(doc.get("name") or "")
    base = base_name(name).lower()
    if "/" in name and name.lower() in query:
        return True
    if base and "." in base and re.search(
            rf"(?<![\w/.\-]){re.escape(base)}(?![\w\-])", query):
        return True
    stem = _normalized(base.rsplit(".", 1)[0] if "." in base else base)
    distinctive = len(stem.split()) >= 2 or any(char.isdigit() for char in stem)
    return distinctive and len(stem.strip()) >= 5 and stem in words


def named_documents(query: str, index: Iterable[Dict[str, Any]],
                    exclude: Optional[Set[str]] = None) -> List[Dict[str, Any]]:
    """Documents de la mémoire que le message nomme, du plus récent au plus ancien.

    Quand le message nomme aussi le dossier de certains (« le rapport.pdf du
    dossier projet »), seuls ceux de ce dossier restent.

    Args:
        query: message de l'utilisateur
        index: MemoryStore.document_index (du plus récent au plus ancien)
        exclude: noms de fichiers déjà joints à la conversation : celui-là est
            le document dont on parle, sauf si le message nomme un dossier
    """
    lowered = str(query or "").lower()
    words = _normalized(query)
    exclude = {name.lower() for name in exclude or ()}
    found = [doc for doc in index if _names_file(doc, lowered, words)]
    in_named_folders = [doc for doc in found
                        if doc.get("folder") and _normalized(doc["folder"]) in words]
    if in_named_folders:
        return in_named_folders
    return [doc for doc in found if base_name(doc.get("name", "")).lower() not in exclude]


def named_folders(query: str, index: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Dossiers déposés que le message désigne (« le dossier projet ») : leur nom,
    entier, et un mot comme « dossier ». Un par dossier (clé), le plus récent
    d'abord : {"key", "name", "created", "files": [libellés]}."""
    if not _FOLDER_WORDS.search(str(query or "")):
        return []
    words = _normalized(query)
    folders: Dict[str, Dict[str, Any]] = {}
    for doc in index:
        key, name = doc.get("folder_key"), doc.get("folder")
        if not key or not name or _normalized(name) not in words:
            continue
        folder = folders.setdefault(key, {"key": key, "name": name, "created": "",
                                          "files": []})
        folder["files"].append(doc.get("label") or base_name(doc.get("name", "")))
        folder["created"] = max(folder["created"], str(doc.get("created") or ""))
    return sorted(folders.values(), key=lambda folder: folder["created"], reverse=True)


def _shared_names(docs: List[Dict[str, Any]]) -> Dict[str, List[int]]:
    """Noms de fichier portés par plusieurs de ces documents → leurs numéros (dès 1)."""
    numbers: Dict[str, List[int]] = {}
    for number, doc in enumerate(docs, 1):
        name = base_name(doc.get("name") or doc.get("document_name") or "")
        numbers.setdefault(name, []).append(number)
    return {name: found for name, found in numbers.items() if len(found) > 1}


def _numbers(numbers: List[int]) -> str:
    """« n° 1 et n° 2 », « n° 1, n° 2 et n° 3 »."""
    parts = [f"n° {number}" for number in numbers]
    return parts[0] if len(parts) == 1 else ", ".join(parts[:-1]) + " et " + parts[-1]


def _same_names_warning(docs: List[Dict[str, Any]]) -> str:
    """Avertissement quand plusieurs documents différents portent le même nom."""
    shared = sorted(_shared_names(docs))
    if not shared:
        return ""
    names = ", ".join(f"« {name} »" for name in shared)
    return (f"⚠️ Plusieurs documents DIFFÉRENTS portent le même nom ({names}) : ne les "
            "confonds pas. Si la question ne dit pas lequel (dossier, date), réponds pour "
            "chacun en le désignant par son dossier ou sa date, ou demande lequel.")


Passages = Callable[[str, str, int], str]


def memory_documents_block(query: str, store: Any, budget: int, passages: Passages,
                           exclude: Optional[Set[str]] = None,
                           search: Optional[Callable[..., List[Dict[str, Any]]]] = None) -> str:
    """Bloc du prompt système : documents et dossiers de la mémoire que le message
    nomme, chacun sous son libellé ; "" s'il n'en nomme aucun.

    Args:
        query: message de l'utilisateur
        store: MemoryStore (document_index, document_text)
        budget: caractères de contenu, au plus, pour tous les documents
        passages: (texte, question, limite) → extraits utiles (document_passages)
        exclude: noms des fichiers joints à la conversation (déjà dans le prompt)
        search: recherche par le sens (VectorMemory.search_similar), pour les
            extraits d'un dossier nommé
    """
    try:
        index = store.document_index()
    except Exception:  # pylint: disable=broad-except
        return ""
    if not index:
        return ""
    docs = named_documents(query, index, exclude)
    included = []
    for doc in docs[:MAX_NAMED]:
        text = store.document_text(doc["id"])
        if text:
            included.append((doc, text))
    blocks = []
    if included:
        others = len(docs) - min(len(docs), MAX_NAMED)
        blocks.append(_documents_block(included, others, query, budget, passages))
    for folder in named_folders(query, index)[:2]:
        blocks.append(_folder_block(folder, query, search))
    return "\n\n".join(blocks)


def _documents_block(included: List[Any], others: int, query: str, budget: int,
                     passages: Passages) -> str:
    """Les documents nommés et leur contenu utile, numérotés quand ils sont plusieurs.

    Quand plusieurs portent le même nom, un avertissement les annonce et un
    rappel, après leur contenu, dit lequel lire : un petit modèle, sinon,
    répond d'après le premier sans parler des autres.

    Args:
        included: (document, texte) de chacun, du plus récent au plus ancien
        others: documents plus anciens du même nom, non montrés
    """
    share = max(800, budget // len(included))
    numbered = len(included) > 1
    sections = []
    for number, (doc, text) in enumerate(included, 1):
        title = (f"Document n° {number} : " if numbered else "") + document_label(doc)
        sections.append(f"=== {title} ===\n{passages(text, query, share)}")
    lines = ["DOCUMENTS DE LA MÉMOIRE NOMMÉS DANS LA QUESTION (fenêtre Mémoire, onglet "
             "Documents) : leur contenu utile est ci-dessous, chacun sous son nom, son "
             "dossier éventuel et sa date d'ajout. Réponds d'après eux."]
    shared = _shared_names([doc for doc, _text in included])
    for name, numbers in shared.items():
        lines.append(f"⚠️ {len(numbers)} documents DIFFÉRENTS s'appellent « {name} » "
                     f"({_numbers(numbers)} ci-dessous) : ne les confonds pas, ne mélange "
                     "pas leurs contenus.")
    if others > 0:
        lines.append(f"(+{others} autre(s) document(s) plus ancien(s) de ce nom, non montré(s).)")
    block = "\n".join(lines) + "\n\n" + "\n\n".join(sections)
    for name, numbers in shared.items():
        block += (f"\n\nRAPPEL : si la question ne précise pas lequel des {len(numbers)} "
                  f"« {name} » (son dossier, « ajouté à la main », « joint au chat » ou sa "
                  f"date), réponds pour les {len(numbers)}, l'un après l'autre, chacun sous "
                  "un titre qui dit lequel c'est. Si elle le précise, réponds seulement "
                  "d'après celui-là.")
    return block


def _folder_block(folder: Dict[str, Any], query: str,
                  search: Optional[Callable[..., List[Dict[str, Any]]]]) -> str:
    """Un dossier déposé nommé : ses fichiers, puis les extraits les plus proches."""
    files = sorted(folder["files"], key=str.lower)
    shown = ", ".join(files[:FOLDER_FILES_SHOWN])
    more = f" … (+{len(files) - FOLDER_FILES_SHOWN})" if len(files) > FOLDER_FILES_SHOWN else ""
    when = _when(folder["created"])
    block = (f"DOSSIER DE LA MÉMOIRE NOMMÉ DANS LA QUESTION : « {folder['name']} »"
             + (f" (déposé le {when})" if when else "")
             + f", {len(files)} fichier(s) : {shown}{more}")
    results = []
    if search is not None:
        try:
            results = search(query, n_results=FOLDER_PASSAGES,
                             where={"folder_id": folder["key"]})
        except Exception:  # pylint: disable=broad-except
            results = []
    if results:
        block += "\nExtraits les plus proches de la question :\n" + results_block(results)
    return block


def results_block(results: List[Dict[str, Any]], chars: int = RESULT_CHARS) -> str:
    """Extraits de search_memory groupés par document, sous leur libellé, dans
    l'ordre de pertinence du premier extrait de chacun."""
    groups: Dict[str, Dict[str, Any]] = {}
    for result in results:
        meta = result.get("metadata") or {}
        key = str(meta.get("document_id") or meta.get("document_name") or len(groups))
        group = groups.setdefault(key, {"meta": meta, "texts": []})
        text = str(result.get("content", result.get("text", "")) or "").strip()
        if text:
            group["texts"].append(text[:chars])
    lines = []
    for number, group in enumerate(groups.values(), 1):
        lines.append(f"[{number}] {document_label(group['meta'])}\n"
                     + "\n[…]\n".join(group["texts"]))
    warning = _same_names_warning([group["meta"] for group in groups.values()])
    return "\n\n".join(([warning] if warning else []) + lines)


def resolve_documents(reference: str, index: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Documents désignés par l'argument « document » de search_memory : un chemin
    (« projet/rapport.pdf »), un nom (« rapport.pdf », tous ceux qui le portent),
    un nom sans extension, ou un dossier déposé (tous ses fichiers)."""
    wanted = str(reference or "").strip().strip("«»\"' ").replace("\\", "/").lower()
    if not wanted:
        return []
    docs = list(index)
    exact = [doc for doc in docs if str(doc.get("name", "")).lower() == wanted]
    if exact:
        return exact
    named = [doc for doc in docs if base_name(doc.get("name", "")).lower() == wanted]
    if named:
        return named
    in_folder = [doc for doc in docs if str(doc.get("folder") or "").lower() == wanted]
    if in_folder:
        return in_folder
    stem = _normalized(wanted.rsplit(".", 1)[0] if "." in wanted else wanted)
    return [doc for doc in docs
            if _normalized(base_name(doc.get("name", "")).rsplit(".", 1)[0]) == stem]
