"""
Copies faites pour un aperçu (CSV en .xlsx, présentation en PDF)

Une copie par version du fichier (chemin, date de modification, taille, forme de
la copie), dans le dossier temporaire ; celles de plus d'une semaine sont
effacées. Chaque copie s'écrit d'abord sous un nom à elle, puis prend sa place :
une copie à moitié écrite ne sert jamais.
"""

import hashlib
import os
import tempfile
import time
import uuid
from pathlib import Path

ROOT = Path(tempfile.gettempdir()) / "my_ai_previews"
MAX_AGE = 7 * 24 * 3600


def copy_path(folder: Path, path: str, suffix: str, version: str) -> Path:
    """Place de la copie de cette version du fichier.

    Raises:
        OSError: fichier introuvable
    """
    stat = os.stat(path)
    identity = f"{version}|{os.path.abspath(path)}|{stat.st_mtime_ns}|{stat.st_size}"
    return folder / f"{hashlib.sha1(identity.encode('utf-8')).hexdigest()[:24]}{suffix}"


def partial_path(target: Path) -> Path:
    """Nom d'écriture de la copie (même extension : PowerPoint l'exige)."""
    return target.with_name(f"{target.stem}.{uuid.uuid4().hex[:8]}.part{target.suffix}")


def prune(folder: Path) -> None:
    """Copies (et restes d'écriture) de plus d'une semaine : effacées."""
    limit = time.time() - MAX_AGE
    try:
        entries = list(folder.iterdir())
    except OSError:
        return
    for old in entries:
        try:
            if old.is_file() and old.stat().st_mtime < limit:
                old.unlink()
        except OSError:
            continue
