"""
Demandes de fichier (« génère un fichier… », « crée moi un fichier… ») : code
ou document.

Ces demandes partent dans la génération de fichier de code
(generators/code_generator.py), qui n'écrit que du code, en Python par défaut :
« Crée un fichier PDF nommé essai avec un poème » donnait essai.py, un script,
et aucun PDF. Un fichier dans un format de document (PDF, Word, Excel,
PowerPoint, Markdown, CSV, texte) est un document : il suit la voie des
documents (outil generate_document, generators/document_generator.py), qui
l'écrit dans ce format.

Le format se lit sur le fichier demandé :
- l'extension de son nom : « un fichier rapport.pdf », « un fichier nommé notes.md » ;
- le mot qui suit « fichier » : « un fichier PDF », « un fichier Word »,
  « un fichier au format Excel », « un fichier en PDF », « un fichier texte » ;
- plus loin, après « en » ou « format » : « un fichier nommé poème en PDF »,
  « un fichier avec un poème au format Markdown ». Pas pour un programme :
  « un fichier qui convertit un PDF en Word », « un fichier avec une fonction
  Python qui exporte en CSV » restent du code.
Un nom de fichier de code (« calcul.py », « index.html ») ou un langage (« un
fichier python ») reste du code, comme une demande qui ne nomme aucun format de
document.
"""

import re
from dataclasses import dataclass
from typing import Optional, Tuple

# Demandes de génération de fichier (core/chat_service.py, core/ai_engine.py)
FILE_GENERATION_KEYWORDS = (
    "génère moi un fichier",
    "crée moi un fichier",
    "génère un fichier",
    "crée un fichier",
)
_KEYWORD_RE = re.compile(
    "|".join(re.escape(keyword) for keyword in FILE_GENERATION_KEYWORDS), re.IGNORECASE
)

# Extension d'un nom de fichier → format du générateur de documents
_DOCUMENT_EXTENSIONS = {
    "pdf": "pdf",
    "docx": "docx", "doc": "docx",
    "xlsx": "xlsx", "xls": "xlsx",
    "pptx": "pptx", "ppt": "pptx",
    "md": "md", "markdown": "md",
    "csv": "csv",
    "txt": "txt",
}
# Nom d'un format → format du générateur de documents
_FORMAT_NAMES = {
    "pdf": "pdf",
    "word": "docx", "docx": "docx", "doc": "docx",
    "excel": "xlsx", "xlsx": "xlsx", "xls": "xlsx", "tableur": "xlsx",
    "powerpoint": "pptx", "pptx": "pptx", "ppt": "pptx", "diaporama": "pptx",
    "markdown": "md", "md": "md",
    "csv": "csv",
    "texte": "txt", "text": "txt", "txt": "txt",
}
# Ceux-là seulement juste après « fichier » : ailleurs, « une fonction qui
# affiche un texte » ou « la doc de l'API » ne disent rien du fichier
_HEAD_ONLY_NAMES = {"texte", "text", "doc"}

# Langages : le fichier est un programme (« un fichier python », « un fichier
# en JavaScript », « … avec une fonction Python qui exporte en CSV »)
_LANGUAGES = {
    "python", "javascript", "typescript", "java", "html", "css", "php", "ruby", "rust",
    "kotlin", "swift", "golang", "bash", "powershell", "sql", "json", "yaml", "xml",
    "c++", "cpp", "c#", "csharp",
}
# Le fichier décrit par ce qu'il fait : un programme (« un fichier qui convertit
# un PDF en Word », « un fichier permettant de… »)
_BEHAVIOUR_WORDS = {"qui", "permettant", "capable"}

_WORD = r"[\w+#]+"
_EXTENSION = r"[A-Za-z][A-Za-z0-9]{0,9}"
# Ce qui peut séparer « fichier » de son format : « au format », « de type »…
_FORMAT_INTRO = (
    r"(?:(?:au|en|sous)\s+(?:le\s+)?format\s+|format\s+|(?:de|du)\s+type\s+|type\s+|en\s+)?"
)
_NAMED = r"(?:nomm|appel|intitul|baptis)[ée]e?s?\s+"
_OPEN_QUOTE = r"[«\"“]"
# Nom entre guillemets appariés : l'apostrophe (« d’automne ») n'en ferme aucun
_QUOTED = (
    r"«\s*(?P<french>[^»\n]{1,100}?)\s*»"
    r"|\"\s*(?P<straight>[^\"\n]{1,100}?)\s*\""
    r"|“\s*(?P<curly>[^”\n]{1,100}?)\s*”"
    r"|'(?P<single>[^'\n]{1,100}?)'"
)

# Nom à extension juste après « fichier » : « un fichier rapport.pdf »,
# « un fichier nommé « calcul.py » »
_HEAD_FILENAME_RE = re.compile(
    rf"^\s*(?:{_NAMED})?(?:{_OPEN_QUOTE}\s*)?(?P<stem>[\w\-]+)\.(?P<ext>{_EXTENSION})\b",
    re.IGNORECASE,
)
# Premier mot après « fichier » et ses mots d'introduction
_HEAD_WORD_RE = re.compile(rf"^\s*{_FORMAT_INTRO}\.?(?P<word>{_WORD})", re.IGNORECASE)
# Nom donné au fichier : « nommé essai », « appelé « Mon rapport » », « intitulé notes.md »
_NAMED_RE = re.compile(
    rf"\b{_NAMED}(?:{_QUOTED}|(?P<bare>[\w\-]+(?:['’.][\w\-]+)*))",
    re.IGNORECASE,
)
# Format nommé plus loin : « en PDF », « au format Word », « de type Excel ».
# Le mot est lu en avance : « en format PDF » donne « format PDF » au tour suivant
_LATER_FORMAT_RE = re.compile(
    rf"\b(?:en|format|type|extension)\s+(?=\.?(?P<word>{_WORD}))", re.IGNORECASE
)
# Nom de fichier à extension, n'importe où dans la demande
_ANY_FILENAME_RE = re.compile(rf"(?<![\w.])[\w\-]+\.(?P<ext>{_EXTENSION})\b")
# Mot isolé (langages : « c++ » et « c# » compris)
_ANY_WORD_RE = re.compile(_WORD)
# Extension à la fin d'un nom
_NAME_EXTENSION_RE = re.compile(rf"^(.+)\.({_EXTENSION})$")


@dataclass(frozen=True)
class DocumentFile:
    """Fichier demandé dans un format de document : `fmt`, format du générateur
    de documents (pdf, docx, xlsx, pptx, md, csv ou txt), et `name`, nom donné
    au fichier sans extension (vide si la demande n'en donne pas)."""

    fmt: str
    name: str = ""


def is_file_request(text: str) -> bool:
    """True pour une demande de génération de fichier (« génère un fichier… »)."""
    lowered = (text or "").lower()
    return any(keyword in lowered for keyword in FILE_GENERATION_KEYWORDS)


def is_code_file_request(text: str) -> bool:
    """True pour une demande de fichier de code : un fichier demandé, sans
    format de document (cf. requested_document)."""
    return is_file_request(text) and requested_document(text) is None


def requested_document(text: str) -> Optional[DocumentFile]:
    """
    Le document demandé par « génère un fichier… » / « crée un fichier… »,
    quand le fichier est dans un format de document ; None pour un fichier de
    code ou une demande qui n'est pas une génération de fichier.
    """
    match = _KEYWORD_RE.search(text or "")
    if not match:
        return None
    rest = text[match.end():]

    # 1. Nom à extension juste après « fichier » : son extension décide
    head = _HEAD_FILENAME_RE.match(rest)
    if head:
        fmt = _DOCUMENT_EXTENSIONS.get(head.group("ext").lower())
        return DocumentFile(fmt, _clean_name(head.group("stem"))) if fmt else None

    # 2. Mot qui suit « fichier » : un format, un langage, ou ce que fait le fichier
    word = _HEAD_WORD_RE.match(rest)
    if word:
        head_word = word.group("word").lower()
        if head_word in _FORMAT_NAMES:
            return DocumentFile(_FORMAT_NAMES[head_word], _given_name(rest))
        if head_word in _LANGUAGES or head_word in _BEHAVIOUR_WORDS:
            return None

    # 3. Nom donné plus loin, à extension : « un fichier avec un poème nommé poeme.pdf »
    stem, ext = _split_extension(_named(rest))
    if ext:
        fmt = _DOCUMENT_EXTENSIONS.get(ext.lower())
        return DocumentFile(fmt, _clean_name(stem)) if fmt else None

    # 4. Format nommé plus loin (« en PDF », « au format Word »), sauf si la
    # demande parle de code : un langage, un nom de fichier de code
    if _mentions_code(rest):
        return None
    for later in _LATER_FORMAT_RE.finditer(rest):
        later_word = later.group("word").lower()
        if later_word in _FORMAT_NAMES and later_word not in _HEAD_ONLY_NAMES:
            return DocumentFile(_FORMAT_NAMES[later_word], _given_name(rest))
    return None


def _mentions_code(text: str) -> bool:
    """True si ``text`` nomme un langage ou un fichier de code (« calcul.py »)."""
    if any(word.lower() in _LANGUAGES for word in _ANY_WORD_RE.findall(text)):
        return True
    return any(
        name.group("ext").lower() not in _DOCUMENT_EXTENSIONS
        for name in _ANY_FILENAME_RE.finditer(text)
    )


def _named(text: str) -> str:
    """Nom donné au fichier (« nommé essai », « appelé « Mon rapport » »), tel
    qu'écrit ; chaîne vide sans nom."""
    named = _NAMED_RE.search(text)
    if not named:
        return ""
    return next((value for value in named.group("french", "straight", "curly", "single", "bare")
                 if value), "")


def _split_extension(name: str) -> Tuple[str, str]:
    """(nom, extension) : (« poeme », « pdf ») pour « poeme.pdf », (« v1.2 », « »)
    pour « v1.2 »."""
    match = _NAME_EXTENSION_RE.match(name)
    return (match.group(1), match.group(2)) if match else (name, "")


def _given_name(text: str) -> str:
    """Nom donné au fichier, sans extension de document ; chaîne vide sans nom."""
    name = _named(text)
    stem, ext = _split_extension(name)
    if ext.lower() in _DOCUMENT_EXTENSIONS:
        name = stem
    return _clean_name(name)


def _clean_name(name: str) -> str:
    """Nom utilisable pour un fichier : sans caractère interdit par Windows."""
    return re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", name or "").strip(" .")[:100]
