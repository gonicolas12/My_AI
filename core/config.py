"""
Configuration principale de l'IA personnelle
"""

import os
from typing import Any, Dict

import yaml

# Configuration principale de l'IA
AI_CONFIG = {
    "default_model": "local",  # Modèle local uniquement
    "max_tokens": 4096,
    "temperature": 0.7,
    "conversation_history_limit": 10,
    "supported_file_types": [".pdf", ".docx", ".txt", ".py", ".html", ".css", ".js"],
    "output_directory": "outputs",
    "logs_directory": "logs",
    "local_mode": True,  # Mode local uniquement
}

# Configuration locale uniquement (plus de dépendances externes)
# Configuration disponible pour développement futur si nécessaire

# Configuration des fichiers
FILE_CONFIG = {
    "max_file_size_mb": 50,
    "temp_directory": "temp",
    "backup_directory": "backups",
}

# Configuration de l'interface
UI_CONFIG = {
    "cli_prompt": "🤖 MyAI> ",
    "gui_title": "My Personal AI Assistant",
    "gui_theme": "light",
}


class Config:
    """
    Gestionnaire de configuration pour l'IA personnelle
    """

    def __init__(self, config_file: str = "config.yaml"):
        """
        Initialise la configuration

        Args:
            config_file: Chemin vers le fichier de configuration
        """
        self.config_file = config_file
        self.config_data = {}
        self._load_config()

    def _load_config(self):
        """Charge la configuration depuis le fichier YAML"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, "r", encoding="utf-8") as f:
                    self.config_data = yaml.safe_load(f) or {}
            else:
                # Utiliser la configuration par défaut
                self.config_data = {
                    "ai": AI_CONFIG,
                    "local": AI_CONFIG,
                    "files": FILE_CONFIG,
                    "ui": UI_CONFIG,
                }
                self._save_config()
        except Exception as e:
            print(f"⚠️ Erreur lors du chargement de la configuration: {e}")
            # Configuration par défaut en cas d'erreur
            self.config_data = {
                "ai": AI_CONFIG,
                "local": AI_CONFIG,
                "files": FILE_CONFIG,
                "ui": UI_CONFIG,
            }

    def _save_config(self):
        """Sauvegarde la configuration dans le fichier YAML"""
        try:
            with open(self.config_file, "w", encoding="utf-8") as f:
                yaml.dump(
                    self.config_data, f, default_flow_style=False, allow_unicode=True
                )
        except Exception as e:
            print(f"⚠️ Erreur lors de la sauvegarde de la configuration: {e}")

    def get(self, key: str, default: Any = None) -> Any:
        """
        Récupère une valeur de configuration

        Args:
            key: Clé de configuration (format: section.key)
            default: Valeur par défaut

        Returns:
            Valeur de configuration
        """
        keys = key.split(".")
        value = self.config_data

        try:
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default

    def set(self, key: str, value: Any):
        """
        Définit une valeur de configuration

        Args:
            key: Clé de configuration (format: section.key)
            value: Nouvelle valeur
        """
        keys = key.split(".")
        config = self.config_data

        # Naviguer jusqu'au parent de la clé finale
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]

        # Définir la valeur
        config[keys[-1]] = value
        self._save_config()

    def get_section(self, section: str) -> Dict[str, Any]:
        """
        Récupère une section complète de configuration

        Args:
            section: Nom de la section

        Returns:
            Dictionnaire de configuration
        """
        return self.config_data.get(section, {})

    def reload(self):
        """Recharge la configuration depuis le fichier"""
        self._load_config()

    def reset_to_defaults(self):
        """Remet la configuration aux valeurs par défaut"""
        self.config_data = {
            "ai": AI_CONFIG,
            "local": AI_CONFIG,
            "files": FILE_CONFIG,
            "ui": UI_CONFIG,
        }
        self._save_config()


# Instance globale de configuration
_GLOBAL_CONFIG = None

def get_config() -> Config:
    """Retourne l'instance globale de configuration"""
    global _GLOBAL_CONFIG
    if _GLOBAL_CONFIG is None:
        _GLOBAL_CONFIG = Config()
    return _GLOBAL_CONFIG
