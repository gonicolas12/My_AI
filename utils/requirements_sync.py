"""
Installation au lancement des dépendances manquantes de requirements.txt

Après un « git pull », requirements.txt peut lister de nouveaux paquets (par
exemple rapidocr, pour l'OCR des PDF scannés). Au lancement, les lignes non
satisfaites (paquet absent ou version qui ne convient plus) sont installées
avec pip, sans toucher au reste. Pour ne pas ralentir chaque lancement, la
vérification n'est refaite que si requirements.txt a changé depuis le dernier
lancement où tout était en place, et une ligne dont l'installation a échoué
n'est retentée qu'au prochain changement du fichier.

Ce module tourne avant les imports qui ont besoin de ces paquets : il n'utilise
que la bibliothèque standard, plus packaging (fourni par pip à défaut).
Désactivation : variable d'environnement MY_AI_SKIP_DEPS_SYNC=1.
"""

# Imports différés (packaging, importlib.metadata) : inutiles quand
# requirements.txt n'a pas changé, soit la plupart des lancements
# pylint: disable=import-outside-toplevel

import hashlib
import importlib
import json
import os
import re
import site
import subprocess
import sys
from pathlib import Path
from typing import Dict, List

PROJECT_ROOT = Path(__file__).resolve().parent.parent
REQUIREMENTS_FILE = PROJECT_ROOT / "requirements.txt"
# Par interpréteur Python : empreinte du requirements.txt vérifié, échecs d'installation
STATE_FILE = PROJECT_ROOT / "data" / ".requirements_sync.json"
SKIP_ENV = "MY_AI_SKIP_DEPS_SYNC"

# Commentaire de requirements.txt (même règle que pip : « # » en début de ligne
# ou précédé d'un espace, pour garder les fragments d'URL « #egg= »)
_COMMENT = re.compile(r"(^|\s+)#.*$")


def sync_requirements(
    requirements_file: Path = REQUIREMENTS_FILE, state_file: Path = STATE_FILE
) -> List[str]:
    """
    Installe les lignes de requirements.txt non satisfaites

    Args:
        requirements_file: Fichier de dépendances
        state_file: Mémoire du dernier contrôle et des échecs d'installation

    Returns:
        Lignes toujours non satisfaites (vide si tout est en place)
    """
    if os.environ.get(SKIP_ENV) or getattr(sys, "frozen", False):
        return []
    try:
        text = requirements_file.read_text(encoding="utf-8")
    except OSError:
        return []
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    state = _read_state(state_file)
    previous = state.get(sys.executable)
    if not isinstance(previous, dict) or previous.get("digest") != digest:
        previous = {}
    elif not previous.get("failed"):
        return []  # requirements.txt inchangé depuis un lancement où tout était en place

    missing = unsatisfied_requirements(text)
    failed_before = set(previous.get("failed", []))
    retry = [line for line in missing if line not in failed_before]

    failed = missing
    if retry:
        print(f"📦 Dépendances manquantes, installation : {', '.join(retry)}", flush=True)
        if not _pip_install(retry) and len(retry) > 1:
            # Une ligne qui échoue ne doit pas empêcher les autres de s'installer
            for line in retry:
                _pip_install([line])
        _refresh_import_paths()
        still_missing = set(unsatisfied_requirements(text))
        failed = [line for line in missing if line in still_missing]

    if failed:
        quoted = " ".join(f'"{line}"' for line in failed)
        print(f"⚠️ Dépendances non installées : {', '.join(failed)}")
        print(f"   Pour voir l'erreur : {sys.executable} -m pip install {quoted}")
        print(
            "   Si une installation précédente a été interrompue : "
            "python tools/clean_broken_dist_info.py"
        )
    state[sys.executable] = {"digest": digest, "failed": failed}
    _write_state(state_file, state)
    return failed


def unsatisfied_requirements(text: str) -> List[str]:
    """
    Lignes de requirements.txt que l'environnement ne satisfait pas

    Args:
        text: Contenu de requirements.txt

    Returns:
        Lignes (sans commentaire) dont le paquet est absent ou dont la version
        installée ne convient pas ; les lignes réservées à une autre
        plateforme (marqueurs) sont ignorées
    """
    requirement_class = _requirement_class()
    if requirement_class is None:
        return []
    installed = _installed_versions()
    missing = []
    for raw in text.splitlines():
        line = _COMMENT.sub("", raw).strip()
        if not line or line.startswith("-"):  # options pip (-r, --index-url...)
            continue
        try:
            requirement = requirement_class(line)
            if requirement.marker and not requirement.marker.evaluate():
                continue
            version = installed.get(_normalize(requirement.name))
            if version is None or (
                requirement.specifier
                and not requirement.specifier.contains(version, prereleases=True)
            ):
                missing.append(line)
        except ValueError:  # ligne, marqueur ou version illisible : ignorée
            continue
    return missing


def _requirement_class():
    """Classe Requirement de packaging, à défaut celle qu'embarque pip (None sans les deux)."""
    try:
        from packaging.requirements import Requirement
    except ImportError:
        try:
            from pip._vendor.packaging.requirements import Requirement
        except ImportError:
            return None
    return Requirement


def _installed_versions() -> Dict[str, str]:
    """Version de chaque distribution installée, par nom normalisé.

    Les dossiers .dist-info vidés par une installation interrompue (sans nom ni
    version) sont ignorés.
    """
    from importlib import metadata as importlib_metadata

    versions: Dict[str, str] = {}
    for distribution in importlib_metadata.distributions():
        try:
            metadata = distribution.metadata
            name = metadata.get("Name") if metadata is not None else None
            version = metadata.get("Version") if metadata is not None else None
        except (OSError, ValueError):
            continue
        if name and version:
            versions.setdefault(_normalize(name), version)
    return versions


def _normalize(name: str) -> str:
    """Nom de paquet normalisé (PEP 503) : « PyMuPDF » et « pymupdf » se rejoignent."""
    return re.sub(r"[-_.]+", "-", name).lower()


def _pip_install(lines: List[str]) -> bool:
    """Installe des lignes de requirements.txt avec le pip de l'interpréteur courant."""
    command = [sys.executable, "-m", "pip", "install", "--disable-pip-version-check", *lines]
    try:
        return subprocess.run(command, check=False).returncode == 0
    except OSError:
        return False


def _refresh_import_paths() -> None:
    """Rend importables, dès ce lancement, les paquets que pip vient d'installer.

    Sans droit d'écriture sur le Python système, pip installe dans le dossier
    utilisateur ; s'il vient d'être créé, il n'est pas encore dans sys.path.
    """
    user_site = site.getusersitepackages()
    if site.ENABLE_USER_SITE and os.path.isdir(user_site) and user_site not in sys.path:
        site.addsitedir(user_site)
    importlib.invalidate_caches()


def _read_state(state_file: Path) -> dict:
    try:
        state = json.loads(state_file.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return state if isinstance(state, dict) else {}


def _write_state(state_file: Path, state: dict) -> None:
    try:
        state_file.parent.mkdir(parents=True, exist_ok=True)
        state_file.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")
    except OSError:
        pass
