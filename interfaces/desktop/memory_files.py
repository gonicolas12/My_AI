"""
Fichiers d'origine des documents de la Mémoire (aperçu de l'onglet Documents)

La Mémoire range le texte d'un document (ses morceaux, dans ChromaDB), pas le
fichier : sans lui, l'aperçu d'un PDF, d'une image ou d'un classeur ne
montrerait que ce texte. Une copie du fichier lu est donc gardée à côté de la
base, un dossier par document (nommé d'après l'empreinte de son identifiant :
celui-ci peut contenir des caractères interdits dans un nom de fichier), et
supprimée avec lui.

Un document rangé avant cette copie, trop gros, ou une mémoire chiffrée (une
copie en clair contournerait le chiffrement) n'en a pas : l'aperçu montre
alors le texte gardé en mémoire.

Les copies ne quittent jamais la machine : la fenêtre les affiche par un lien
signé (files.py), comme une pièce jointe.
"""

import hashlib
import os
import re
import shutil
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Callable, Iterable, Optional

from utils.logger import setup_logger

logger = setup_logger("DesktopMemoryFiles")

# Dossier des copies, dans celui de la base vectorielle
ORIGINALS_DIRNAME = "originals"
# Au-delà, le fichier n'est pas copié (l'aperçu montre son texte)
ORIGINAL_MAX = 64 * 1024 * 1024
# Copie en cours d'écriture (renommée une fois complète)
_PARTIAL = ".partial"

# Caractères interdits dans un nom de fichier sous Windows, et de contrôle
_UNSAFE = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def safe_file_name(name: str, fallback: str = "document") -> str:
    """Nom de fichier sûr sur tous les systèmes : dernier élément d'un chemin,
    sans caractère interdit, ni point ou espace final (refusés par Windows)."""
    last = PureWindowsPath(PurePosixPath(str(name or "")).name).name
    cleaned = _UNSAFE.sub("_", last).strip().rstrip(". ")
    return cleaned[:180] or fallback


class OriginalFiles:
    """Copies des fichiers d'origine, un dossier par document."""

    def __init__(self, root: Path):
        self.root = Path(root)

    @staticmethod
    def folder_name(document_id: str) -> str:
        """Dossier d'un document : l'empreinte de son identifiant."""
        return hashlib.sha256(str(document_id).encode("utf-8")).hexdigest()[:32]

    def _folder(self, document_id: str) -> Path:
        return self.root / self.folder_name(document_id)

    def find(self, document_id: str) -> Optional[str]:
        """Copie du fichier d'origine d'un document, ou None s'il n'en a pas."""
        if not document_id:
            return None
        folder = self._folder(document_id)
        try:
            files = sorted(entry for entry in folder.iterdir()
                           if entry.is_file() and not entry.name.endswith(_PARTIAL))
        except OSError:
            return None
        return str(files[0]) if files else None

    def keep(self, document_id: str, source: str, name: str,
             replace: bool = True) -> Optional[str]:
        """Copie le fichier lu pour un document ; la copie, ou None (trop gros, illisible).

        Args:
            name: nom du document (« dossier/chemin » pour un fichier d'un dossier) :
                la copie prend son dernier élément, avec l'extension du fichier lu
                s'il n'en a pas
            replace: remplacer une copie déjà là (False : la garder)
        """
        if not document_id or not source:
            return None
        if not replace:
            existing = self.find(document_id)
            if existing:
                return existing
        try:
            if not os.path.isfile(source) or os.path.getsize(source) > ORIGINAL_MAX:
                return None
            shown = safe_file_name(name, fallback=safe_file_name(os.path.basename(source)))
            if not os.path.splitext(shown)[1]:
                shown += os.path.splitext(source)[1]
            folder = self._folder(document_id)
            folder.mkdir(parents=True, exist_ok=True)
            target = folder / shown
            partial = folder / (shown + _PARTIAL)
            shutil.copyfile(source, partial)
            # Une seule copie par document : l'ancienne (autre nom) s'en va
            for entry in folder.iterdir():
                if entry.is_file() and entry != partial and entry.name != shown:
                    entry.unlink(missing_ok=True)
            os.replace(partial, target)
            return str(target)
        except OSError as exc:
            logger.warning("Copie du document %s non gardée : %s", name, exc)
            return None

    def forget(self, document_ids: Iterable[str]) -> int:
        """Supprime les copies de documents retirés de la mémoire ; combien."""
        removed = 0
        for document_id in document_ids:
            folder = self._folder(document_id)
            if folder.is_dir():
                shutil.rmtree(folder, ignore_errors=True)
                removed += 1
        return removed

    def prune(self, document_ids: Callable[[], Iterable[str]]) -> int:
        """Supprime les copies des documents qui ne sont plus en mémoire (retirés
        ailleurs : pièce jointe oubliée, version remplacée, fichier d'un dossier
        mis à jour) ; combien.

        Args:
            document_ids: documents en mémoire, lus une fois les copies listées :
                un document rangé entre-temps (sa copie suit son rangement) n'est
                jamais pris pour un document retiré
        """
        try:
            folders = [entry for entry in self.root.iterdir() if entry.is_dir()]
        except OSError:
            return 0
        if not folders:
            return 0
        ids = list(document_ids())
        if not ids:
            # Index illisible ou mémoire vidée : rien n'est supprimé à l'aveugle
            return 0
        keep = {self.folder_name(document_id) for document_id in ids}
        removed = 0
        for folder in folders:
            if folder.name not in keep:
                shutil.rmtree(folder, ignore_errors=True)
                removed += 1
        if removed:
            logger.info("%d copie(s) de documents retirés de la mémoire supprimée(s)", removed)
        return removed
