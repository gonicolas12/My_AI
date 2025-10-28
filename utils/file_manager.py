"""
Gestionnaire de fichiers et utilitaires
"""

import os
import shutil
import mimetypes
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List


class FileManager:
    """
    Gestionnaire de fichiers pour l'IA
    """

    def __init__(self, base_dir: str = ""):
        """
        Initialise le gestionnaire de fichiers

        Args:
            base_dir: Répertoire de base
        """
        self.base_dir = Path(base_dir) if base_dir else Path.cwd()
        self.supported_types = {
            ".pdf": "PDF Document",
            ".docx": "Word Document",
            ".doc": "Word Document (Legacy)",
            ".txt": "Text File",
            ".py": "Python Script",
            ".html": "HTML File",
            ".css": "CSS Stylesheet",
            ".js": "JavaScript File",
            ".json": "JSON File",
            ".xml": "XML File",
            ".md": "Markdown File",
        }

        # Création des répertoires nécessaires
        self._create_directories()

    def _create_directories(self):
        """
        Crée les répertoires nécessaires
        """
        directories = ["outputs", "logs", "temp", "backups"]
        for directory in directories:
            (self.base_dir / directory).mkdir(exist_ok=True)

    def get_file_info(self, file_path: str) -> Dict[str, Any]:
        """
        Obtient les informations détaillées d'un fichier

        Args:
            file_path: Chemin vers le fichier

        Returns:
            Informations sur le fichier
        """
        path = Path(file_path)

        if not path.exists():
            return {"error": "Fichier non trouvé", "exists": False}

        stat = path.stat()

        info = {
            "exists": True,
            "path": str(path.absolute()),
            "name": path.name,
            "stem": path.stem,
            "suffix": path.suffix,
            "size": stat.st_size,
            "size_human": self._human_readable_size(stat.st_size),
            "created": datetime.fromtimestamp(stat.st_ctime),
            "modified": datetime.fromtimestamp(stat.st_mtime),
            "accessed": datetime.fromtimestamp(stat.st_atime),
            "is_file": path.is_file(),
            "is_directory": path.is_dir(),
            "mime_type": mimetypes.guess_type(str(path))[0],
            "file_type": self.supported_types.get(path.suffix.lower(), "Unknown"),
        }

        # Permissions (Unix/Linux)
        if hasattr(stat, "st_mode"):
            info["permissions"] = oct(stat.st_mode)[-3:]

        return info

    def _human_readable_size(self, size: int) -> str:
        """
        Convertit une taille en bytes en format lisible

        Args:
            size: Taille en bytes

        Returns:
            Taille formatée
        """
        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} PB"

    def is_supported(self, file_path: str) -> bool:
        """
        Vérifie si le type de fichier est supporté

        Args:
            file_path: Chemin vers le fichier

        Returns:
            True si supporté
        """
        return Path(file_path).suffix.lower() in self.supported_types

    def list_files(
        self, directory: str = "", pattern: str = "*", recursive: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Liste les fichiers d'un répertoire

        Args:
            directory: Répertoire à explorer
            pattern: Pattern de fichiers
            recursive: Recherche récursive

        Returns:
            Liste des fichiers avec informations
        """
        dir_path = Path(directory) if directory else self.base_dir

        if not dir_path.exists():
            return []

        files = []

        if recursive:
            file_paths = dir_path.rglob(pattern)
        else:
            file_paths = dir_path.glob(pattern)

        for file_path in file_paths:
            if file_path.is_file():
                files.append(self.get_file_info(str(file_path)))

        return files

    def copy_file(
        self, source: str, destination: str, overwrite: bool = False
    ) -> Dict[str, Any]:
        """
        Copie un fichier

        Args:
            source: Fichier source
            destination: Destination
            overwrite: Écraser si existe

        Returns:
            Résultat de la copie
        """
        try:
            source_path = Path(source)
            dest_path = Path(destination)

            if not source_path.exists():
                return {"success": False, "error": "Fichier source non trouvé"}

            if dest_path.exists() and not overwrite:
                return {"success": False, "error": "Fichier de destination existe déjà"}

            # Création du répertoire parent si nécessaire
            dest_path.parent.mkdir(parents=True, exist_ok=True)

            shutil.copy2(source, destination)

            return {
                "success": True,
                "source": str(source_path.absolute()),
                "destination": str(dest_path.absolute()),
                "size": dest_path.stat().st_size,
            }

        except (OSError, shutil.Error) as e:
            return {"success": False, "error": str(e)}

    def move_file(
        self, source: str, destination: str, overwrite: bool = False
    ) -> Dict[str, Any]:
        """
        Déplace un fichier

        Args:
            source: Fichier source
            destination: Destination
            overwrite: Écraser si existe

        Returns:
            Résultat du déplacement
        """
        try:
            source_path = Path(source)
            dest_path = Path(destination)

            if not source_path.exists():
                return {"success": False, "error": "Fichier source non trouvé"}

            if dest_path.exists() and not overwrite:
                return {"success": False, "error": "Fichier de destination existe déjà"}

            # Création du répertoire parent si nécessaire
            dest_path.parent.mkdir(parents=True, exist_ok=True)

            shutil.move(source, destination)

            return {
                "success": True,
                "old_path": str(source_path),
                "new_path": str(dest_path.absolute()),
            }

        except (OSError, shutil.Error) as e:
            return {"success": False, "error": str(e)}

    def delete_file(self, file_path: str, backup: bool = True) -> Dict[str, Any]:
        """
        Supprime un fichier

        Args:
            file_path: Chemin du fichier
            backup: Créer une sauvegarde

        Returns:
            Résultat de la suppression
        """
        try:
            path = Path(file_path)

            if not path.exists():
                return {"success": False, "error": "Fichier non trouvé"}

            backup_path = None
            if backup:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_name = f"{path.stem}_{timestamp}{path.suffix}"
                backup_path = self.base_dir / "backups" / backup_name
                shutil.copy2(file_path, backup_path)

            path.unlink()

            result = {"success": True, "deleted_file": str(path.absolute())}

            if backup_path:
                result["backup_path"] = str(backup_path.absolute())

            return result

        except (OSError, shutil.Error) as e:
            return {"success": False, "error": str(e)}

    def create_backup(self, file_path: str) -> Dict[str, Any]:
        """
        Crée une sauvegarde d'un fichier

        Args:
            file_path: Fichier à sauvegarder

        Returns:
            Résultat de la sauvegarde
        """
        try:
            source_path = Path(file_path)

            if not source_path.exists():
                return {"success": False, "error": "Fichier non trouvé"}

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"{source_path.stem}_{timestamp}{source_path.suffix}"
            backup_path = self.base_dir / "backups" / backup_name

            shutil.copy2(file_path, backup_path)

            return {
                "success": True,
                "original": str(source_path.absolute()),
                "backup": str(backup_path.absolute()),
                "size": backup_path.stat().st_size,
            }

        except (OSError, shutil.Error) as e:
            return {"success": False, "error": str(e)}

    def clean_temp_files(self, max_age_hours: int = 24) -> Dict[str, Any]:
        """
        Nettoie les fichiers temporaires

        Args:
            max_age_hours: Âge maximum en heures

        Returns:
            Résultat du nettoyage
        """
        try:
            temp_dir = self.base_dir / "temp"
            deleted_files = []
            total_size = 0

            if not temp_dir.exists():
                return {"success": True, "deleted_files": [], "total_size": 0}

            cutoff_time = datetime.now().timestamp() - (max_age_hours * 3600)

            for file_path in temp_dir.rglob("*"):
                if file_path.is_file() and file_path.stat().st_mtime < cutoff_time:
                    size = file_path.stat().st_size
                    file_path.unlink()
                    deleted_files.append(str(file_path))
                    total_size += size

            return {
                "success": True,
                "deleted_files": deleted_files,
                "total_size": total_size,
                "total_size_human": self._human_readable_size(total_size),
            }

        except (OSError, shutil.Error) as e:
            return {"success": False, "error": str(e)}

    def get_disk_usage(self, path: str = "") -> Dict[str, Any]:
        """
        Obtient l'utilisation du disque

        Args:
            path: Chemin à analyser

        Returns:
            Informations sur l'utilisation
        """
        try:
            check_path = Path(path) if path else self.base_dir

            if not check_path.exists():
                return {"error": "Chemin non trouvé"}

            total, used, free = shutil.disk_usage(check_path)

            return {
                "path": str(check_path.absolute()),
                "total": total,
                "used": used,
                "free": free,
                "total_human": self._human_readable_size(total),
                "used_human": self._human_readable_size(used),
                "free_human": self._human_readable_size(free),
                "usage_percent": (used / total) * 100,
            }

        except (OSError, shutil.Error) as e:
            return {"error": str(e)}

    def get_timestamp(self) -> str:
        """
        Retourne un timestamp formaté

        Returns:
            Timestamp actuel
        """
        return datetime.now().isoformat()

    def sanitize_filename(self, filename: str) -> str:
        """
        Nettoie un nom de fichier

        Args:
            filename: Nom de fichier à nettoyer

        Returns:
            Nom de fichier nettoyé
        """
        # Caractères interdits
        invalid_chars = '<>:"/\\|?*'

        # Remplacement des caractères invalides
        sanitized = filename
        for char in invalid_chars:
            sanitized = sanitized.replace(char, "_")

        # Limitation de la longueur
        if len(sanitized) > 255:
            name, ext = os.path.splitext(sanitized)
            sanitized = name[: 255 - len(ext)] + ext

        return sanitized
