"""
Configuration principale de l'IA personnelle

Source de vérité : config.yaml (racine du projet).
Les dicts _DEFAULT_* ci-dessous ne servent que de fallback si le YAML
est absent ou incomplet.  Tout le code doit passer par get_config().
"""

import os
from typing import Any, Dict

import yaml

# ── Defaults (fallback uniquement) ──────────────────────────────────
_DEFAULT_AI_CONFIG: Dict[str, Any] = {
    "default_model": "local",
    "max_tokens": 4096,
    "temperature": 0.7,
    "conversation_history_limit": 10,
    "supported_file_types": [".pdf", ".docx", ".txt", ".py", ".html", ".css", ".js"],
    "output_directory": "outputs",
    "logs_directory": "logs",
    "local_mode": True,
}

_DEFAULT_FILE_CONFIG: Dict[str, Any] = {
    "max_file_size_mb": 50,
    "temp_directory": "temp",
    "backup_directory": "backups",
}

_DEFAULT_UI_CONFIG: Dict[str, Any] = {
    "cli_prompt": "\U0001f916 MyAI> ",
    "gui_title": "My Personal AI Assistant",
    "gui_theme": "light",
}

# Rétrocompatibilité : anciens noms publics (à supprimer quand tous les imports seront migrés)
AI_CONFIG = _DEFAULT_AI_CONFIG
FILE_CONFIG = _DEFAULT_FILE_CONFIG
UI_CONFIG = _DEFAULT_UI_CONFIG


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

    @staticmethod
    def _defaults() -> Dict[str, Any]:
        """Retourne la configuration par défaut (fallback)"""
        return {
            "ai": dict(_DEFAULT_AI_CONFIG),
            "files": dict(_DEFAULT_FILE_CONFIG),
            "ui": dict(_DEFAULT_UI_CONFIG),
        }

    @staticmethod
    def _deep_merge(base: Dict, override: Dict) -> Dict:
        """Fusionne *override* dans *base* récursivement (override gagne)."""
        merged = dict(base)
        for key, value in override.items():
            if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
                merged[key] = Config._deep_merge(merged[key], value)
            else:
                merged[key] = value
        return merged

    def _load_config(self):
        """Charge la configuration : defaults + YAML (le YAML écrase)."""
        defaults = self._defaults()
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, "r", encoding="utf-8") as f:
                    yaml_data = yaml.safe_load(f) or {}
                self.config_data = self._deep_merge(defaults, yaml_data)
            else:
                self.config_data = defaults
                self._save_config()
        except (yaml.YAMLError, OSError) as e:
            print(f"Erreur chargement configuration: {e}")
            self.config_data = defaults

    def _save_config(self):
        """Sauvegarde la configuration dans le fichier YAML"""
        try:
            with open(self.config_file, "w", encoding="utf-8") as f:
                yaml.dump(
                    self.config_data, f, default_flow_style=False, allow_unicode=True
                )
        except (yaml.YAMLError, OSError) as e:
            print(f"⚠️ Erreur lors de la sauvegarde de la configuration: {e}")

    def get(self, key: str, default=None):
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
        self.config_data = self._defaults()
        self._save_config()


# Instance globale de configuration
_GLOBAL_CONFIG = None

def get_config() -> Config:
    """Retourne l'instance globale de configuration"""
    global _GLOBAL_CONFIG
    if _GLOBAL_CONFIG is None:
        _GLOBAL_CONFIG = Config()
    return _GLOBAL_CONFIG
