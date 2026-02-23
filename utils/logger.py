"""
Configuration et gestion des logs
"""

import logging
from datetime import datetime
from pathlib import Path


def setup_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """
    Configure un logger pour l'application

    Args:
        name: Nom du logger
        level: Niveau de log

    Returns:
        Logger configuré
    """
    logger = logging.getLogger(name)

    # Éviter la duplication des handlers
    if logger.handlers:
        return logger

    logger.setLevel(level)

    # Création du répertoire logs
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)

    # Nom du fichier log avec date
    log_filename = f"my_ai_{datetime.now().strftime('%Y%m%d')}.log"
    log_filepath = logs_dir / log_filename

    # Formatter
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Handler pour fichier
    file_handler = logging.FileHandler(log_filepath, encoding="utf-8")
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)

    # Handler pour console
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)

    # Ajout des handlers
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger


class Logger:
    """
    Logger principal pour l'application
    """

    @staticmethod
    def get_logger(name: str, level: int = logging.INFO) -> logging.Logger:
        """
        Retourne un logger configuré

        Args:
            name: Nom du logger
            level: Niveau de log

        Returns:
            Logger configuré
        """
        return setup_logger(name, level)
