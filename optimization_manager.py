#!/usr/bin/env python3
"""
🎯 Gestionnaire Central des Optimisations - My_AI
Coordonne toutes les optimisations : RAG, Context, Fine-tuning
"""

import os
import sys
import yaml
import time
from typing import Dict, Any, Optional
import logging

# Imports conditionnels
try:
    from rag_pipeline import RAGPipeline
    RAG_AVAILABLE = True
except ImportError:
    RAG_AVAILABLE = False

try:
    from context_optimization import AdvancedContextOptimizer
    CONTEXT_OPT_AVAILABLE = True
except ImportError:
    CONTEXT_OPT_AVAILABLE = False

class OptimizationManager:
    """Gestionnaire central des optimisations"""
    
    def __init__(self, config_path: str = "config.yaml"):
        self.config_path = config_path
        self.config = self._load_config()
        self.logger = self._setup_logger()
        
        # Composants d'optimisation
        self.rag_pipeline = None
        self.context_optimizer = None
        
        self._initialize_components()
    
    def _load_config(self) -> Dict[str, Any]:
        """Charge la configuration"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except:
            return {}
    
    def _setup_logger(self):
        """Configure le logger"""
        logging.basicConfig(level=logging.INFO)
        return logging.getLogger("OptimizationManager")
    
    def _initialize_components(self):
        """Initialise les composants d'optimisation"""
        opt_config = self.config.get("optimization", {})
        
        # RAG Pipeline
        if RAG_AVAILABLE and opt_config.get("rag", {}).get("enabled", False):
            try:
                self.rag_pipeline = RAGPipeline()
                self.logger.info("✅ RAG Pipeline initialisé")
            except Exception as e:
                self.logger.warning(f"Erreur init RAG: {e}")
        
        # Context Optimizer
        if CONTEXT_OPT_AVAILABLE and opt_config.get("context_optimization", {}).get("enabled", False):
            try:
                self.context_optimizer = AdvancedContextOptimizer()
                self.logger.info("✅ Optimiseur de contexte initialisé")
            except Exception as e:
                self.logger.warning(f"Erreur init context optimizer: {e}")
    
    def optimize_query(self, query: str, context: Dict[str, Any], model) -> str:
        """Applique toutes les optimisations à une requête"""
        
        # 1. Optimisation du contexte si nécessaire
        if self.context_optimizer and len(query) > 2000:
            query = self.context_optimizer.compress_context(query)
            self.logger.debug("Contexte compressé")
        
        # 2. Recherche RAG si disponible
        if self.rag_pipeline:
            try:
                rag_response = self.rag_pipeline.query(query, model)
                if rag_response and len(rag_response) > 10:
                    return rag_response
            except Exception as e:
                self.logger.warning(f"Erreur RAG: {e}")
        
        # 3. Fallback sur le modèle standard
        return model.generate_response(query, context)
    
    def get_optimization_status(self) -> Dict[str, Any]:
        """Retourne le statut des optimisations"""
        return {
            "rag_available": RAG_AVAILABLE,
            "rag_enabled": self.rag_pipeline is not None,
            "context_optimization_available": CONTEXT_OPT_AVAILABLE,
            "context_optimization_enabled": self.context_optimizer is not None,
            "config_loaded": bool(self.config),
            "components_active": sum([
                self.rag_pipeline is not None,
                self.context_optimizer is not None
            ])
        }

# Singleton global
_optimization_manager = None

def get_optimization_manager() -> OptimizationManager:
    """Obtient l'instance globale du gestionnaire d'optimisations"""
    global _optimization_manager
    if _optimization_manager is None:
        _optimization_manager = OptimizationManager()
    return _optimization_manager
