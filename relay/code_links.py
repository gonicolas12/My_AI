"""
Fichiers qu'une réponse de la conversation Code cite ou nomme, rendus cliquables

La page Code de la fenêtre en montre l'aperçu dans son volet de droite, la vue
Code du téléphone dans sa fenêtre d'aperçu, comme le chat
(core/chat_service.answer_paths, named_file_links) :
  - chemins absolus existants (« C:\\…\\rapport.docx ») ;
  - chemins relatifs au workspace de VS Code (« src/app.ts », « README.md »),
    ceux qu'emploient l'extension et le modèle ; un dossier s'ouvre dans
    l'Explorateur ;
  - noms seuls (« shell.ts ») des fichiers que les outils de la réponse ont
    lus, écrits ou ouverts, et des pièces jointes de la conversation.

Le workspace est celui de VS Code au moment du message (« roots » de la
réponse, tirés de son client_hello) : seul un fichier qui existe sur ce PC,
dans l'un de ses dossiers, devient un lien. Un VS Code sur une autre machine
a des chemins qui n'existent pas ici : rien n'y est cliquable.
"""

import os
import re
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from utils.path_links import safe_to_probe

# Réponses dont les fichiers cités deviennent des liens : ni en cours, ni en erreur
LINKED_STATUSES = ("done", "stopped")
# Liens d'une réponse : au plus, comme ceux d'une section d'agent (relay/agent_relay.py)
MAX_LINKS = 60
# Chemins relatifs essayés par réponse : au plus (chacun sonde le disque)
MAX_CANDIDATES = 120

# Outils de l'extension dont l'argument « path » est un fichier (core/agentic_executor.py)
_FILE_TOOLS = frozenset({"read_file", "write_file", "edit_file", "open_file"})

# Ligne d'un dossier dans le client_hello de VS Code : « - My_AI (C:\…\My_AI) »
_FOLDER_LINE = re.compile(r"^- (.+)\)\s*$", re.MULTILINE)

# Bloc de code clôturé : la fenêtre n'y rend rien cliquable, inutile d'y chercher
_FENCE = re.compile(r"```[\s\S]*?(?:```|\Z)")
# Élément d'un chemin relatif : ni « . » ni « .. » en tête (jamais hors du workspace)
_PART = r"[\w@$%+-][\w.@$%+~-]*"
# Chemin relatif (« src/app.ts », « .\docs\a.md », « README.md ») : pas au milieu d'un
# autre chemin, d'une adresse web ou d'un mot (rien de tout cela juste avant lui)
_RELATIVE = re.compile(rf"(?<![\w.\\/:@$%+~-])(?:\.[\\/])?(?:{_PART}[\\/])*{_PART}")

Resolved = Optional[Tuple[str, bool]]


def workspace_roots(workspace_info: str) -> List[str]:
    """Dossiers ouverts dans VS Code, dans l'ordre (le premier : celui de ses outils).

    Un nom de dossier ou un chemin peut contenir des parenthèses
    (« C:\\Program Files (x86)\\app ») : le chemin est la fin de la ligne qui
    commence à la première « ( » suivie d'un chemin absolu.
    """
    roots: List[str] = []
    for body in _FOLDER_LINE.findall(workspace_info or ""):
        start = body.find(" (")
        while start >= 0:
            root = body[start + 2:]
            if os.path.isabs(root):
                roots.append(root)
                break
            start = body.find(" (", start + 1)
    return roots


def usable_roots(roots: Iterable[Any]) -> List[str]:
    """Dossiers du workspace qu'on peut sonder : absolus, jamais un partage réseau."""
    usable = []
    for root in roots or []:
        if isinstance(root, str) and os.path.isabs(root) and safe_to_probe(root):
            usable.append(os.path.normpath(root))
    return usable


def conversation_files(messages: Iterable[Dict[str, Any]]) -> Dict[str, str]:
    """Pièces jointes de la conversation : nom en minuscules → chemin (le plus récent)."""
    files: Dict[str, str] = {}
    for message in messages or []:
        if message.get("role") != "user":
            continue
        for item in message.get("files") or []:
            if not isinstance(item, dict):
                continue
            path = item.get("path")
            name = item.get("name") or os.path.basename(path or "")
            if isinstance(path, str) and path and isinstance(name, str) and name:
                files[name.lower()] = path
    return files


def reply_text(message: Dict[str, Any]) -> str:
    """Texte affiché d'une réponse : celui de ses passes, sinon son texte final."""
    texts = [part.get("text") or "" for part in message.get("parts") or []
             if isinstance(part, dict) and part.get("kind") == "text"]
    joined = "\n\n".join(text for text in texts if text)
    return joined or (message.get("text") or "")


def _inside(path: str, root: str) -> bool:
    try:
        return os.path.commonpath([os.path.normcase(path), os.path.normcase(root)]) \
            == os.path.normcase(root)
    except ValueError:  # autre lecteur sous Windows
        return False


def _resolve(relative: str, roots: Sequence[str], cache: Dict[Tuple[str, str], Resolved],
             files_only: bool = False) -> Resolved:
    """Chemin relatif → (chemin absolu, dossier ?) dans le premier dossier qui le contient."""
    if relative[:2] in ("./", ".\\"):
        relative = relative[2:]
    for root in roots:
        key = (root, relative)
        if key not in cache:
            full = os.path.normpath(os.path.join(root, relative))
            cache[key] = ((full, os.path.isdir(full))
                          if _inside(full, root) and os.path.exists(full) else None)
        found = cache[key]
        if found and not (files_only and found[1]):
            return found
    return None


def _candidates(text: str) -> List[str]:
    """Chemins relatifs plausibles d'un texte, hors blocs de code, dans l'ordre."""
    seen: List[str] = []
    for match in _RELATIVE.finditer(_FENCE.sub(" ", text)):
        candidate = match.group(0).rstrip(".")
        last = re.split(r"[\\/]", candidate)[-1]
        # Un mot seul n'est pas un fichier : il faut un dossier ou une extension
        if candidate in seen or not ("/" in candidate or "\\" in candidate or "." in last):
            continue
        seen.append(candidate)
        if len(seen) >= MAX_CANDIDATES:
            break
    return seen


def _tool_files(parts: Iterable[Any], roots: Sequence[str],
                cache: Dict[Tuple[str, str], Resolved]) -> Dict[str, str]:
    """Fichiers que les outils de la réponse ont lus, écrits ou ouverts : nom → chemin."""
    named: Dict[str, str] = {}
    for part in parts or []:
        if (not isinstance(part, dict) or part.get("kind") != "tool"
                or part.get("name") not in _FILE_TOOLS):
            continue
        raw = (part.get("input") or {}).get("path")
        if not isinstance(raw, str) or not raw.strip():
            continue
        raw = raw.strip()
        if os.path.isabs(raw):
            found = (os.path.normpath(raw), False) if (
                safe_to_probe(raw) and os.path.isfile(raw)) else None
        else:
            found = _resolve(raw, roots, cache, files_only=True)
        if found is None:
            continue
        name = os.path.basename(found[0])
        stem, extension = os.path.splitext(name)
        if stem and len(extension) > 1:
            named[name.lower()] = found[0]
    return named


def reply_links(
    message: Dict[str, Any],
    files: Dict[str, str],
    roots: Sequence[str],
    cache: Optional[Dict[Tuple[str, str], Resolved]] = None,
) -> List[Dict[str, Any]]:
    """Fichiers et dossiers qu'une réponse cite ou nomme : {"text", "path", "dir", "name"}.

    Args:
        message: réponse de la transcription (parts, text)
        files: pièces jointes de la conversation (conversation_files)
        roots: dossiers du workspace de VS Code au moment du message
        cache: sondages du disque partagés entre les réponses d'une même lecture
    """
    # pylint: disable=import-outside-toplevel
    from core.chat_service import answer_paths, named_file_links

    text = reply_text(message)
    if not text:
        return []
    cache = {} if cache is None else cache
    roots = usable_roots(roots)
    links = answer_paths(text)
    seen = {link["text"] for link in links}
    # Chemins relatifs : entiers, comme un nom (ni « src/a.ts » dans « web/src/a.ts »)
    for candidate in _candidates(text) if roots else []:
        if candidate in seen:
            continue
        found = _resolve(candidate, roots, cache)
        if found is not None:
            links.append({"text": candidate, "path": found[0], "dir": found[1], "name": True})
            seen.add(candidate)
    named = dict(files or {})
    named.update(_tool_files(message.get("parts"), roots, cache))
    for link in named_file_links(text, named):
        if link["text"] not in seen:
            links.append(link)
            seen.add(link["text"])
    return links[:MAX_LINKS]


def link_transcript(messages: List[Dict[str, Any]], current_roots: Sequence[str],
                    field: str) -> List[Dict[str, Any]]:
    """Liens des réponses terminées d'une transcription, cherchés sur le disque.

    Modifie `messages` (une copie de celle du hub) : chaque réponse terminée
    reçoit ses liens sous `field` (« paths » pour la fenêtre, « links » pour le
    téléphone) et perd ses dossiers du workspace (« roots »), qui ne servent
    qu'ici ; une réponse sans dossiers gardés prend ceux de VS Code ouvert.

    Returns:
        Tous les liens trouvés : la surface en montre l'aperçu.
    """
    files = conversation_files(messages)
    cache: Dict[Tuple[str, str], Resolved] = {}
    found: List[Dict[str, Any]] = []
    for message in messages:
        if message.get("role") == "user":
            continue
        roots = message.pop("roots", None) or current_roots
        if message.get("status") in LINKED_STATUSES:
            links = reply_links(message, files, roots, cache)
            if links:
                message[field] = links
                found.extend(links)
    return found
