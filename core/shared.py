"""
Module partagé pour éviter les imports circulaires
Contient les classes et fonctions utilisées par plusieurs modules
"""

import os
from typing import Any, Dict, List
from dataclasses import dataclass, field

# =========================================================================== #
# OPTIMISATION DÉMARRAGE : Mode offline pour HuggingFace                      #
# IMPORTANT: Ces variables DOIVENT être définies AVANT tout import de modules #
# qui utilisent HuggingFace (sentence_transformers, transformers, etc.)       #
# Évite la vérification des mises à jour à chaque lancement                   #
# Les modèles sont déjà en cache local, pas besoin de vérifier en ligne       #
# =========================================================================== #

# =============================================== #
# MODÈLE D'EMBEDDINGS PARTAGÉ                     #
# Évite de charger le modèle 3 fois au démarrage  #
# Stratégie: Offline first, téléchargement si    #
# nécessaire au premier lancement                 #
# =============================================== #

_SHARED_EMBEDDING_MODEL = None
_EMBEDDINGS_AVAILABLE = False


def _load_embedding_model():
    """
    Charge le modèle d'embeddings avec stratégie intelligente:
    1. Essaie d'abord en mode offline (rapide si modèle en cache)
    2. Si échec, passe en mode online pour télécharger le modèle
    
    Retourne (model, success) tuple
    """
    global _SHARED_EMBEDDING_MODEL, _EMBEDDINGS_AVAILABLE

    model_name = "all-MiniLM-L6-v2"

    # Étape 1: Essayer en mode OFFLINE (cache local)
    os.environ['HF_HUB_OFFLINE'] = '1'
    os.environ['TRANSFORMERS_OFFLINE'] = '1'
    os.environ['HF_DATASETS_OFFLINE'] = '1'

    try:
        print("📦 Chargement du modèle d'embeddings... (Mode offline)")
        from sentence_transformers import SentenceTransformer # pylint: disable=import-outside-toplevel
        _SHARED_EMBEDDING_MODEL = SentenceTransformer(model_name)
        _EMBEDDINGS_AVAILABLE = True
        print("✅ Modèle d'embeddings chargé depuis le cache")
        return _SHARED_EMBEDDING_MODEL, True
    except Exception as offline_error:
        # Le modèle n'est pas en cache, on doit le télécharger
        offline_msg = str(offline_error).lower()
        needs_download = any(x in offline_msg for x in [
            'offline', 'cache', 'not found', 'connection', 'network',
            'does not exist', 'no such file'
        ])

        if needs_download:
            print("📥 Premier lancement détecté - Téléchargement du modèle... (Cela peut prendre plusieurs minutes)")
            print("   (Cela ne se produira qu'une seule fois)")

            # Étape 2: Désactiver le mode offline et télécharger
            os.environ['HF_HUB_OFFLINE'] = '0'
            os.environ['TRANSFORMERS_OFFLINE'] = '0'
            os.environ['HF_DATASETS_OFFLINE'] = '0'

            try:
                # Recharger le module pour prendre en compte les nouvelles variables
                import importlib # pylint: disable=import-outside-toplevel
                import sentence_transformers # pylint: disable=import-outside-toplevel
                importlib.reload(sentence_transformers)
                from sentence_transformers import SentenceTransformer # pylint: disable=import-outside-toplevel

                _SHARED_EMBEDDING_MODEL = SentenceTransformer(model_name)
                _EMBEDDINGS_AVAILABLE = True
                print("✅ Modèle téléchargé et prêt (sera en cache pour les prochains lancements)")

                # Remettre en mode offline pour la suite de l'exécution
                os.environ['HF_HUB_OFFLINE'] = '1'
                os.environ['TRANSFORMERS_OFFLINE'] = '1'
                os.environ['HF_DATASETS_OFFLINE'] = '1'

                return _SHARED_EMBEDDING_MODEL, True
            except Exception as download_error:
                print(f"⚠️ Impossible de télécharger le modèle: {download_error}")
                print("   Vérifiez votre connexion internet et réessayez.")
                _SHARED_EMBEDDING_MODEL = None
                _EMBEDDINGS_AVAILABLE = False
                return None, False
        else:
            # Autre erreur (pas liée au mode offline)
            print(f"⚠️ Modèle d'embeddings non disponible: {offline_error}")
            _SHARED_EMBEDDING_MODEL = None
            _EMBEDDINGS_AVAILABLE = False
            return None, False


# Charger le modèle au démarrage
_load_embedding_model()


def get_shared_embedding_model():
    """
    Retourne le modèle d'embeddings partagé (déjà chargé au démarrage).
    Usage:
        from core.shared import get_SHARED_EMBEDDING_MODEL
        model = get_SHARED_EMBEDDING_MODEL()
        if model:
            embeddings = model.encode(texts)
    """
    return _SHARED_EMBEDDING_MODEL


def is_embeddings_available() -> bool:
    """Vérifie si les embeddings sont disponibles"""
    return _EMBEDDINGS_AVAILABLE


# Alias pour compatibilité
class EmbeddingModelSingleton:
    """Classe de compatibilité - le modèle est déjà chargé"""
    def get_model(self):
        """Récupère le modèle d'embeddings partagé"""
        return _SHARED_EMBEDDING_MODEL

    def is_available(self) -> bool:
        """Vérifie si le modèle est disponible"""
        return _EMBEDDINGS_AVAILABLE

    def is_loaded(self) -> bool:
        """Vérifie si le modèle est chargé"""
        return _SHARED_EMBEDDING_MODEL is not None


embedding_model_singleton = EmbeddingModelSingleton()


# ============================================================================
# CLASSES DE DONNÉES PARTAGÉES
# ============================================================================

@dataclass
class CodeSnippet:
    """
    Représente un snippet de code trouvé
    Classe partagée entre smart_code_searcher et autres modules
    """
    code: str
    language: str
    title: str
    description: str
    source_url: str
    source_name: str
    quality_score: float = 0.0
    relevance_score: float = 0.0
    final_score: float = 0.0
    tags: List[str] = field(default_factory=list)
    votes: int = 0
    views: int = 0


@dataclass
class SearchResult:
    """Résultat de recherche générique"""
    title: str
    url: str
    snippet: str
    source: str
    relevance_score: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


# Configuration partagée pour éviter duplication
DEFAULT_TIMEOUT = 10
DEFAULT_MAX_RESULTS = 8
DEFAULT_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

# Sites prioritaires pour recherche (partagés entre modules)
PRIORITY_CODE_SITES = [
    "github.com",
    "stackoverflow.com",
    "geeksforgeeks.org",
    "realpython.com",
    "pythontutor.com",
    "w3schools.com",
    "developer.mozilla.org",
    "docs.python.org"
]
