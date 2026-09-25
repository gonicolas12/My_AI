"""
Chemins de fichiers et de dossiers cités dans un texte

Sert à rendre cliquables, dans les réponses du chat, les chemins que le modèle
affiche (« Le fichier a été créé dans C:\\Users\\…\\rapport.docx »).

La difficulté est de savoir où un chemin s'arrête : ceux de Windows contiennent
des espaces (« OneDrive - Pierre Fabre SA ») et se fondent dans la phrase. La
règle retenue est de garder, depuis chaque début de chemin plausible, **le plus
long préfixe qui existe réellement sur le disque**. Un chemin inventé par le
modèle n'est donc jamais rendu cliquable.

Tester l'existence d'un chemin sur un lecteur réseau déconnecté peut bloquer
plusieurs secondes : seuls les disques locaux sont sondés sous Windows, et
seul le dossier personnel sous macOS/Linux.
"""

import os
import re
import subprocess
import sys
from dataclasses import dataclass
from typing import Dict, List, Optional

IS_WINDOWS = sys.platform.startswith("win")

# Début de chemin Windows : lecteur + « :\ » ou « :/ », non précédé d'un
# caractère de mot, d'une barre ou d'un « : » (exclut « file:///C:/… »).
_WINDOWS_START_RE = re.compile(r"(?<![\w\\/:])[A-Za-z]:[\\/]")
# Début de chemin POSIX : « ~/ » ou « / » suivi d'une lettre, en début de ligne
# ou après une espace, une ouverture ou un guillemet (exclut « https://… »).
_POSIX_START_RE = re.compile(r"(?:^|(?<=[\s(\[«\"'`]))(?:~/|/(?=[A-Za-z]))", re.MULTILINE)

# Caractères devant lesquels un chemin peut s'arrêter.
_BOUNDARY_CHARS = frozenset(" \t\"'`)]}>«»,;|")
# Ponctuation retirée en fin de candidat (fin de phrase, guillemets…).
_TRAILING = " \t.,;:!?)]}>\"'`»"
# Borne la longueur examinée après un début de chemin.
_MAX_PATH_LEN = 400

# Types de lecteurs Windows sûrs à sonder (GetDriveTypeW) : amovible, fixe,
# disque virtuel. Réseau (4) et lecteur optique (5) sont exclus.
_SAFE_DRIVE_TYPES = frozenset({2, 3, 6})


@dataclass(frozen=True)
class PathMatch:
    """Chemin existant repéré dans un texte."""

    start: int  # position du premier caractère dans le texte
    end: int  # position suivant le dernier caractère
    text: str  # texte tel qu'il apparaît
    path: str  # chemin absolu normalisé, prêt à ouvrir


def find_existing_paths(text: str) -> List[PathMatch]:
    """
    Repère les chemins de fichiers ou de dossiers existants dans un texte.

    Args:
        text: Texte affiché (sans marqueurs Markdown)

    Returns:
        Les chemins trouvés, dans l'ordre, sans chevauchement.
    """
    if not text:
        return []

    starts = sorted(
        {m.start() for m in _WINDOWS_START_RE.finditer(text)}
        | ({m.start() for m in _POSIX_START_RE.finditer(text)} if not IS_WINDOWS else set())
    )
    drive_cache: Dict[str, bool] = {}
    matches: List[PathMatch] = []
    covered_until = -1

    for start in starts:
        if start < covered_until:
            continue
        line_end = text.find("\n", start)
        rest = text[start:line_end if line_end != -1 else len(text)][:_MAX_PATH_LEN]
        found = _longest_existing_prefix(rest, drive_cache)
        if found is None:
            continue
        shown, resolved = found
        matches.append(PathMatch(start, start + len(shown), shown, resolved))
        covered_until = start + len(shown)

    return matches


def _longest_existing_prefix(rest: str, drive_cache: Dict[str, bool]) -> Optional[tuple]:
    """Plus long préfixe de `rest` qui existe sur le disque : (texte, chemin)."""
    ends = {len(rest)} | {i for i, char in enumerate(rest) if char in _BOUNDARY_CHARS}
    for end in sorted(ends, reverse=True):
        shown = rest[:end].rstrip(_TRAILING)
        if len(shown) <= 3:  # « C:\ » seul n'a pas d'intérêt
            continue
        resolved = _resolve(shown)
        if resolved is None or not _safe_to_probe(resolved, drive_cache):
            continue
        if os.path.exists(resolved):
            return shown, resolved
    return None


def _resolve(shown: str) -> Optional[str]:
    """Normalise un chemin affiché ; None s'il sort du périmètre autorisé."""
    if IS_WINDOWS:
        return os.path.normpath(shown)
    expanded = os.path.normpath(os.path.expanduser(shown))
    home = os.path.normpath(os.path.expanduser("~"))
    # Hors du dossier personnel, un chemin POSIX peut viser un montage réseau.
    if expanded != home and not expanded.startswith(home + os.sep):
        return None
    return expanded


def _safe_to_probe(path: str, drive_cache: Dict[str, bool]) -> bool:
    """True si tester l'existence du chemin ne risque pas de bloquer."""
    if not IS_WINDOWS:
        return True
    drive = os.path.splitdrive(path)[0]
    if not drive or drive.startswith("\\\\"):
        return False  # chemin UNC : partage réseau
    if drive not in drive_cache:
        try:
            import ctypes

            drive_type = ctypes.windll.kernel32.GetDriveTypeW(f"{drive}\\")
        except (AttributeError, OSError):
            drive_type = 0
        drive_cache[drive] = drive_type in _SAFE_DRIVE_TYPES
    return drive_cache[drive]


def reveal_in_file_manager(path: str) -> None:
    """
    Ouvre l'emplacement d'un chemin dans le gestionnaire de fichiers.

    Dossier : il est ouvert. Fichier : son dossier est ouvert avec le fichier
    sélectionné — on mène l'utilisateur à l'emplacement, sans ouvrir le
    document lui-même (le bouton 📂 du volet d'aperçu s'en charge).
    """
    path = os.path.normpath(path)
    is_dir = os.path.isdir(path)
    if IS_WINDOWS:
        if is_dir:
            os.startfile(path)  # noqa: B606 - chemin vérifié sur le disque
        else:
            # Chaîne de commande et non liste : explorer n'accepte le chemin
            # que sous la forme /select,"…" (un chemin Windows ne peut pas
            # contenir de guillemet).
            subprocess.Popen(f'explorer /select,"{path}"')
    elif sys.platform == "darwin":
        subprocess.Popen(["open", path] if is_dir else ["open", "-R", path])
    else:
        subprocess.Popen(["xdg-open", path if is_dir else os.path.dirname(path)])
