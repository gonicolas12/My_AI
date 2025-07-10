"""
Configuration et gestion des logs
"""

import logging
import os
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
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Handler pour fichier
    file_handler = logging.FileHandler(log_filepath, encoding='utf-8')
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

def get_log_files() -> list:
    """
    Retourne la liste des fichiers de log
    
    Returns:
        Liste des fichiers de log
    """
    logs_dir = Path("logs")
    if not logs_dir.exists():
        return []
    
    return [f for f in logs_dir.glob("*.log")]

def clean_old_logs(days: int = 30):
    """
    Supprime les logs plus anciens que le nombre de jours spécifié
    
    Args:
        days: Nombre de jours à conserver
    """
    logs_dir = Path("logs")
    if not logs_dir.exists():
        return
    
    cutoff_time = datetime.now().timestamp() - (days * 24 * 60 * 60)
    
    for log_file in logs_dir.glob("*.log"):
        if log_file.stat().st_mtime < cutoff_time:
            log_file.unlink()
            print(f"Log supprimé: {log_file}")

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

class AILogger:
    """
    Logger spécialisé pour l'IA avec métriques
    """
    
    def __init__(self, name: str):
        """
        Initialise le logger IA
        
        Args:
            name: Nom du composant
        """
        self.logger = setup_logger(f"AI.{name}")
        self.metrics = {
            "requests": 0,
            "successes": 0,
            "errors": 0,
            "total_processing_time": 0
        }
    
    def log_request(self, query: str):
        """
        Log une requête utilisateur
        
        Args:
            query: Requête de l'utilisateur
        """
        self.metrics["requests"] += 1
        self.logger.info(f"Nouvelle requête: {query[:100]}...")
    
    def log_response(self, response_type: str, success: bool, processing_time: float):
        """
        Log une réponse
        
        Args:
            response_type: Type de réponse
            success: Succès ou échec
            processing_time: Temps de traitement en secondes
        """
        if success:
            self.metrics["successes"] += 1
            self.logger.info(f"Réponse {response_type} générée en {processing_time:.2f}s")
        else:
            self.metrics["errors"] += 1
            self.logger.error(f"Échec de génération {response_type} après {processing_time:.2f}s")
        
        self.metrics["total_processing_time"] += processing_time
    
    def log_error(self, error: Exception, context: str = ""):
        """
        Log une erreur
        
        Args:
            error: Exception levée
            context: Contexte de l'erreur
        """
        self.metrics["errors"] += 1
        self.logger.error(f"Erreur {context}: {str(error)}", exc_info=True)
    
    def get_metrics(self) -> dict:
        """
        Retourne les métriques du logger
        
        Returns:
            Dictionnaire des métriques
        """
        avg_time = (
            self.metrics["total_processing_time"] / self.metrics["requests"]
            if self.metrics["requests"] > 0 else 0
        )
        
        success_rate = (
            self.metrics["successes"] / self.metrics["requests"] * 100
            if self.metrics["requests"] > 0 else 0
        )
        
        return {
            **self.metrics,
            "average_processing_time": avg_time,
            "success_rate": success_rate
        }
    
    def reset_metrics(self):
        """
        Remet à zéro les métriques
        """
        self.metrics = {
            "requests": 0,
            "successes": 0,
            "errors": 0,
            "total_processing_time": 0
        }
