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
  projet ») ; folders_near : ceux au nom proche d'un dossier qu'il désigne sans
  parler de la mémoire (« mon dossier onedrive »), peut-être sur le disque.
  « Dossier » et « mémoire » sont reconnus dans les 12 langues de l'application,
  et un nom collé au japonais, au chinois ou au coréen compte.
- memory_documents_block : le bloc du prompt système de la réponse, avec le
  contenu utile de chacun (sous son libellé, numéroté s'ils sont plusieurs) ;
  quand plusieurs portent le même nom, un avertissement avant eux et un rappel
  après : répondre pour chacun, sauf si la question dit lequel.
- results_block : les extraits de l'outil search_memory, groupés par document,
  sous leur libellé.
- memory_links : les documents et dossiers qu'une réponse cite, que la fenêtre
  rend cliquables (ils ouvrent l'onglet Documents sur eux) ;
  unmentioned_near_folders : ceux au nom proche de celui de la question que la
  réponse ne cite pas, que la fenêtre signale sous elle.
- documents_at : les documents qu'un chemin absent du disque désigne, lus par
  read_local_file dans la mémoire.
"""

import re
from datetime import datetime
from pathlib import PurePosixPath
from typing import Any, Callable, Dict, Iterable, List, Optional, Set, Tuple

# Documents nommés mis dans le prompt, au plus (les plus récents)
MAX_NAMED = 3
# Dossier nommé : fichiers listés et extraits, au plus
FOLDER_FILES_SHOWN = 40
FOLDER_PASSAGES = 4
# Dossier au nom proche (folders_near) : fichiers listés, au plus
NEAR_FILES_SHOWN = 10
# Extrait d'un résultat de search_memory (caractères)
RESULT_CHARS = 500
# Documents et dossiers cités rendus cliquables dans une réponse, au plus
MAX_LINKS = 40

# Tout ce qui n'est ni lettre ni chiffre : espaces, _, -, ., mais aussi la
# ponctuation collée à un nom (« dossier projet, il… », « (projet) »)
_SEPARATORS = re.compile(r"[\W_]+")


def _ranges(*pairs: Tuple[int, int]) -> str:
    """Plages d'une classe de caractères d'expression régulière, de leurs codes."""
    return "".join(f"{chr(first)}-{chr(last)}" for first, last in pairs)


# Japonais, chinois et coréen : un nom latin s'y colle sans espace (« OneDriveフォルダ »,
# « Data.xlsx를 ») ; chaque caractère y compte comme un mot
_CJK = re.compile("([" + _ranges((0x3040, 0x30FF), (0x3400, 0x4DBF), (0x4E00, 0x9FFF),
                                 (0xF900, 0xFAFF), (0xAC00, 0xD7AF)) + "])")
# Lettres et chiffres des écritures à espaces (latin, grec, cyrillique) : un nom collé à
# l'une d'elles est le bout d'un autre mot (« MyData.xlsx ») ; collé à du japonais, du
# chinois, du coréen ou de l'arabe (« Data.xlsxの中身 »), il compte
_WORD_CHARS = "0-9A-Za-z_" + _ranges((0x00C0, 0x024F), (0x0370, 0x03FF), (0x0400, 0x04FF),
                                     (0x1E00, 0x1EFF))
# « Dossier » dans les 12 langues de l'application ; japonais, chinois, coréen et arabe
# (« المجلد ») sans limite de mot, ils se collent à leurs voisins
_FOLDER_WORDS = re.compile(
    r"\b(?:dossiers?|répertoires?|folders?|director(?:y|ies)|ordner|verzeichnis(?:se)?|"
    r"carpetas?|directorios?|cartell[ae]|map|mappen|pastas?|diret[óo]rios?|папк\w*|"
    r"каталог\w*)\b|フォルダー?|ディレクトリ|文件夹|目录|資料夾|폴더|디렉터리|مجلد",
    re.IGNORECASE)
# Schéma d'une adresse (« memory:// », « file:/// ») : pas un nom de document
_SCHEME = re.compile(r"\b[a-z][a-z0-9+.\-]*://+", re.IGNORECASE)
# Le message parle de la mémoire, dans les 12 langues : « que tu as en mémoire », « in
# your memory », « in deinem Gedächtnis », « 記憶にある »…
_MEMORY_WORDS = re.compile(
    r"\b(?:m[ée]moires?|m[ée]moris\w*|memor(?:y|ies)|memori[sz]\w*|ged[äa]chtnis\w*|"
    r"memorias?|mem[óo]rias?|geheugen|памят\w*)\b|記憶|メモリ|메모리|기억|记忆|الذاكرة|ذاكرت",
    re.IGNORECASE)
# Mots lus avant et après « dossier » pour y trouver un bout de son nom : « mon dossier
# onedrive », « my onedrive folder », « OneDriveフォルダ »
_BEFORE_FOLDER_WORD = 3
_AFTER_FOLDER_WORD = 4
# Mots de 4 lettres ou plus trop courants pour désigner un dossier à eux seuls
_COMMON_WORDS = frozenset({
    # français, anglais
    "dans", "avec", "pour", "sans", "sous", "chez", "vers", "mais", "donc", "quoi", "tout",
    "tous", "toute", "toutes", "cette", "celui", "celle", "ceux", "notre", "votre",
    "fichier", "fichiers", "document", "documents", "dossier", "dossiers", "mémoire",
    "memoire", "with", "from", "that", "this", "what", "your", "inside", "which", "there",
    "file", "files", "folder", "folders", "memory",
    # allemand, néerlandais
    "meine", "meinem", "meinen", "meiner", "deine", "deinem", "deinen", "datei", "dateien",
    "dokumente", "ordner", "gedächtnis", "welche", "mijn", "jouw", "bestand", "bestanden",
    "documenten", "geheugen", "welke",
    # espagnol, italien, portugais
    "carpeta", "archivo", "archivos", "documentos", "memoria", "dentro", "cartella",
    "documenti", "della", "nella", "minha", "minhas", "pasta", "arquivo", "arquivos",
    "memória",
    # russe
    "моей", "моём", "моем", "твоей", "файл", "файлы", "папка", "папке", "памяти",
    "документы"})


def _normalized(text: str) -> str:
    """Minuscules, tout ce qui n'est ni lettre ni chiffre réduit à une espace, chaque
    caractère japonais, chinois ou coréen à part, bordé d'espaces : « Dossier projet,
    il » → « dossier projet il », « OneDriveフォルダ » → « onedrive フ ォ ル ダ »."""
    spaced = _CJK.sub(r" \1 ", str(text or "").lower())
    return f" {_SEPARATORS.sub(' ', spaced).strip()} "


def _folder_words(name: str) -> Set[str]:
    """Mots d'un nom de dossier qui suffisent à le désigner : « OneDrive_3_06-10-2026 »
    → {« onedrive »} ; ni nombres, ni mots de moins de 4 lettres, ni mots courants."""
    return {word for word in _normalized(name).split()
            if len(word) >= 4 and not word.isdigit() and word not in _COMMON_WORDS}


def _near_folder_word(query: str) -> Set[str]:
    """Mots autour de « dossier » (3 avant, 4 après) et chaque paire collée (« one
    drive » → « onedrive ») : un nom de dossier abrégé, « mon dossier onedrive », « my
    onedrive folder », « OneDriveフォルダ »."""
    found: Set[str] = set()
    for match in _FOLDER_WORDS.finditer(query):
        before = _normalized(query[:match.start()]).split()[-_BEFORE_FOLDER_WORD:]
        after = _normalized(query[match.end():]).split()[:_AFTER_FOLDER_WORD]
        for words in (before, after):
            found.update(words)
            found.update(first + second for first, second in zip(words, words[1:]))
    return found


def _names_folder(name: str, words: str, abbreviations: Set[str]) -> bool:
    """Le message désigne-t-il ce dossier ? Par son nom entier (words : le message
    normalisé), ou par un mot distinctif de son nom autour de « dossier »."""
    return _normalized(name) in words or bool(_folder_words(name) & abbreviations)


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
    # Entier (ni « MyData.xlsx », ni « Data.xlsx.bak »), mais collé au japonais, au
    # chinois ou au coréen (« Data.xlsxの中身 »)
    if base and "." in base and re.search(
            rf"(?<![{_WORD_CHARS}/.\-]){re.escape(base)}"
            rf"(?![{_WORD_CHARS}\-]|\.[{_WORD_CHARS}])", query):
        return True
    stem = _normalized(base.rsplit(".", 1)[0] if "." in base else base)
    distinctive = len(stem.split()) >= 2 or any(char.isdigit() for char in stem)
    return distinctive and len(stem.strip()) >= 5 and stem in words


def named_documents(query: str, index: Iterable[Dict[str, Any]],
                    exclude: Optional[Set[str]] = None) -> List[Dict[str, Any]]:
    """Documents de la mémoire que le message nomme, du plus récent au plus ancien.

    Quand le message nomme aussi le dossier de certains (« le rapport.pdf du
    dossier projet », ou un mot de son nom autour de « dossier » : « le Data.xlsx
    du dossier onedrive »), seuls ceux de ce dossier restent.

    Args:
        query: message de l'utilisateur
        index: MemoryStore.document_index (du plus récent au plus ancien)
        exclude: noms de fichiers déjà joints à la conversation : celui-là est
            le document dont on parle, sauf si le message nomme un dossier
    """
    query = str(query or "")
    lowered = query.lower()
    words = _normalized(query)
    exclude = {name.lower() for name in exclude or ()}
    found = [doc for doc in index if _names_file(doc, lowered, words)]
    abbreviations = _near_folder_word(query)
    in_named_folders = [doc for doc in found if doc.get("folder")
                        and _names_folder(doc["folder"], words, abbreviations)]
    if in_named_folders:
        return in_named_folders
    return [doc for doc in found if base_name(doc.get("name", "")).lower() not in exclude]


def _matching_folders(index: Iterable[Dict[str, Any]],
                      matches: Callable[[str], bool]) -> List[Dict[str, Any]]:
    """Dossiers déposés dont le nom convient, un par dossier (clé), le plus récent
    d'abord : {"key", "name", "created", "files": [libellés]}."""
    tested: Dict[str, bool] = {}
    folders: Dict[str, Dict[str, Any]] = {}
    for doc in index:
        key, name = doc.get("folder_key"), doc.get("folder")
        if not key or not name:
            continue
        if name not in tested:
            tested[name] = matches(name)
        if not tested[name]:
            continue
        folder = folders.setdefault(key, {"key": key, "name": name, "created": "",
                                          "files": []})
        folder["files"].append(doc.get("label") or base_name(doc.get("name", "")))
        folder["created"] = max(folder["created"], str(doc.get("created") or ""))
    return sorted(folders.values(), key=lambda folder: folder["created"], reverse=True)


def named_folders(query: str, index: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Dossiers déposés que le message désigne : un mot comme « dossier » (dans les 12
    langues), et le nom du dossier entier (« le dossier projet ») ou, si le message
    parle de la mémoire, un mot distinctif de ce nom autour de « dossier » (« mon
    dossier onedrive que tu as en mémoire » pour « OneDrive_3_06-10-2026 » ; sans
    « mémoire », c'est peut-être un dossier du disque, cf. folders_near). Un par
    dossier (clé), le plus récent d'abord : {"key", "name", "created", "files"}."""
    query = str(query or "")
    if not _FOLDER_WORDS.search(query):
        return []
    words = _normalized(query)
    abbreviations = _near_folder_word(query) if _MEMORY_WORDS.search(query) else set()
    return _matching_folders(index, lambda name: _names_folder(name, words, abbreviations))


def folders_near(query: str, index: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Dossiers déposés au nom proche d'un dossier que le message désigne sans parler
    de la mémoire (« il y a quoi dans mon dossier onedrive ? » pour
    « OneDrive_3_06-10-2026 ») : peut-être un dossier du disque ; le modèle signale
    celui de la mémoire au lieu de l'ignorer."""
    query = str(query or "")
    if not _FOLDER_WORDS.search(query) or _MEMORY_WORDS.search(query):
        return []
    words = _normalized(query)
    abbreviations = _near_folder_word(query)
    return _matching_folders(index, lambda name: _normalized(name) not in words
                             and bool(_folder_words(name) & abbreviations))


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
    near = folders_near(query, index)[:2]
    if near:
        blocks.append(_near_block(near))
    return "\n\n".join(blocks)


def _near_block(folders: List[Dict[str, Any]]) -> str:
    """Dossiers de la mémoire au nom proche d'un dossier que le message désigne sans
    parler de la mémoire (folders_near) : le modèle regarde le disque s'il le faut,
    mais signale ceux-ci, sans les confondre."""
    described = []
    for folder in folders:
        files = sorted(folder["files"], key=str.lower)
        shown = ", ".join(files[:NEAR_FILES_SHOWN])
        more = f" … (+{len(files) - NEAR_FILES_SHOWN})" if len(files) > NEAR_FILES_SHOWN else ""
        when = _when(folder["created"])
        described.append(f"« {folder['name']} »" + (f" (déposé le {when})" if when else "")
                         + f", {len(files)} fichier(s) : {shown}{more}")
    targets = " ou ".join(f"document=\"{folder['name']}\"" for folder in folders)
    # Pas de « termine ta réponse par… » : my_ai ne le suivait qu'une fois sur trois ; la
    # fenêtre signale elle-même ce dossier sous la réponse (unmentioned_near_folders)
    return ("À SAVOIR : la mémoire (fenêtre Mémoire, onglet Documents) contient aussi un "
            "dossier au nom proche de celui de la question : " + " ; ".join(described)
            + ". La question ne dit pas si elle parle de lui ou d'un dossier du disque : ne "
            "les confonds pas. S'il s'agit de lui, lis-le avec l'outil search_memory, "
            f"{targets} (sans citer l'outil dans ta réponse).")


def _cites(text: str, name: str) -> bool:
    """Le texte cite-t-il ce nom, entier (comme memory_links), casse ignorée ?"""
    return bool(name) and re.search(
        rf"(?<![{_WORD_CHARS}/\\.\-]){re.escape(name)}(?![{_WORD_CHARS}\-]|\.[{_WORD_CHARS}])",
        text, re.IGNORECASE) is not None


def unmentioned_near_folders(query: str, answer: str,
                             index: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Dossiers de la mémoire au nom proche de celui de la question (folders_near) dont
    la réponse ne cite ni le nom ni un fichier : elle a sans doute regardé le disque ;
    la fenêtre les signale sous elle (« Aussi dans la Mémoire »), sans compter sur le
    modèle (il ne le faisait qu'une fois sur trois). [{"name", "files"}]."""
    if not answer:
        return []
    signaled = []
    for folder in folders_near(query, index)[:2]:
        names = [folder["name"]] + [base_name(label) for label in folder["files"]]
        if not any(_cites(answer, name) for name in names):
            signaled.append({"name": folder["name"], "files": len(folder["files"])})
    return signaled


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
    """Un dossier déposé nommé : ses fichiers, où il est (la mémoire, pas le disque :
    my_ai listait sinon parfois un dossier du disque du même nom), puis les extraits
    les plus proches."""
    files = sorted(folder["files"], key=str.lower)
    shown = ", ".join(files[:FOLDER_FILES_SHOWN])
    more = f" … (+{len(files) - FOLDER_FILES_SHOWN})" if len(files) > FOLDER_FILES_SHOWN else ""
    when = _when(folder["created"])
    block = (f"DOSSIER DE LA MÉMOIRE NOMMÉ DANS LA QUESTION : « {folder['name']} »"
             + (f" (déposé le {when})" if when else "")
             + f", {len(files)} fichier(s) : {shown}{more}\n"
             + "Il est dans la mémoire (fenêtre Mémoire, onglet Documents), pas sur le disque : "
             + "réponds d'après ses fichiers et les extraits ci-dessous ; pour en lire plus : "
             + f"outil search_memory, document=\"{folder['name']}\" (sans citer l'outil dans "
             + "ta réponse).")
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


def documents_at(path: str, index: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Documents de la mémoire qu'un chemin absent du disque désigne (read_local_file) :
    leur chemin dans la mémoire (« OneDrive_3_06-10-2026/Data.xlsx »), sinon leur nom
    de fichier (« C:\\…\\Data.xlsx » inventé) ; jamais un dossier entier."""
    wanted = _SCHEME.sub("", str(path or "").strip().strip("«»\"' ")).replace("\\", "/")
    if not wanted:
        return []
    docs = list(index)
    exact = [doc for doc in docs if str(doc.get("name", "")).lower() == wanted.lower()]
    if exact:
        return exact
    base = base_name(wanted).lower()
    return [doc for doc in docs if base and base_name(doc.get("name", "")).lower() == base]


def _distinctive(name: str) -> bool:
    """Nom qu'on ne prend pas pour un mot courant : une extension, un chiffre, un
    « _ » ou un « - » (« Data.xlsx », « OneDrive_3_06-10-2026 »), ou 12 caractères
    au moins. « projet » ou « Documents » ne le sont pas."""
    return bool(re.search(r"[\d_.\-]", name)) or len(name) >= 12


def memory_links(text: str, index: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Documents et dossiers de la mémoire qu'une réponse cite : la fenêtre les rend
    cliquables, ils ouvrent l'onglet Documents sur eux.

    Chaque nom est cherché entier, casse ignorée : le chemin complet d'un fichier
    d'un dossier (« projet/docs/rapport.pdf »), son chemin dans ce dossier, que
    l'onglet affiche (« docs/rapport.pdf »), son nom (« Data.xlsx »), le nom d'un
    dossier (« OneDrive_3_06-10-2026 »). Un nom pris dans un chemin du disque
    (« C:\\Users\\…\\Data.xlsx ») ne compte pas. Un nom courant (« projet ») n'est
    cliquable que dans un lien ou du code (strict).

    Args:
        text: réponse du modèle (Markdown)
        index: MemoryStore.document_index

    Returns:
        [{"text": tel qu'écrit dans la réponse, "kind": "document" ou "folder",
          "name": ce que l'onglet cherche, "strict": bool}], les plus longs d'abord
    """
    if not text:
        return []
    names: Dict[str, Dict[str, str]] = {}
    for doc in index:
        name = str(doc.get("name") or "")
        # Chemin complet, chemin dans son dossier (ce que l'onglet affiche), nom du fichier
        for candidate in (name, str(doc.get("label") or ""), base_name(name)):
            if candidate:
                names.setdefault(candidate.lower(), {"kind": "document", "name": candidate})
        folder = str(doc.get("folder") or "")
        if folder:
            names[folder.lower()] = {"kind": "folder", "name": folder}
    # « [Data](memory://Data.xlsx) » : le nom compte, pas le schéma inventé
    scan = _SCHEME.sub(" ", text)
    lowered = scan.lower()
    links: List[Dict[str, Any]] = []
    seen: Set[str] = set()
    for key in sorted(names, key=len, reverse=True):
        if len(key) < 3 or key not in lowered:
            continue
        target = names[key]
        # Entier, mais collé au japonais, au chinois ou au coréen (« Data.xlsxには »)
        pattern = (rf"(?<![{_WORD_CHARS}/\\.\-]){re.escape(key)}"
                   rf"(?![{_WORD_CHARS}\-]|\.[{_WORD_CHARS}])")
        for match in re.finditer(pattern, scan, re.IGNORECASE):
            shown = match.group(0)
            if shown in seen:
                continue
            seen.add(shown)
            links.append({"text": shown, **target, "strict": not _distinctive(target["name"])})
            if len(links) >= MAX_LINKS:
                return links
    return links
