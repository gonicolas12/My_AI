"""
Module partagé pour éviter les imports circulaires
Contient les classes et fonctions utilisées par plusieurs modules
"""

import os
from typing import Any, Dict, List
from dataclasses import dataclass, field

try:
    from core.network import configure_network_environment, build_network_error_help
except ImportError:
    def configure_network_environment(_force: bool = False):
        """Stub de configuration réseau (si core.network est importé trop tard)"""
        return {}

    def build_network_error_help(_error: Exception) -> str:
        """Stub de génération d'aide pour les erreurs réseau"""
        return ""

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
    Charge le moteur d'embeddings de la mémoire et du RAG (core.embedding_engine) :
    1. le modèle de config.yaml (Granite par défaut), depuis le cache ;
    2. sinon MiniLM, s'il est en cache, pour cette session (le modèle choisi se
       télécharge en arrière-plan pour le lancement suivant) ;
    3. sinon (premier lancement), téléchargement du modèle choisi.

    Retourne (model, success) tuple
    """
    global _SHARED_EMBEDDING_MODEL, _EMBEDDINGS_AVAILABLE

    # Apply generic proxy/TLS setup before touching HuggingFace downloads.
    network_info = configure_network_environment()
    for warning in network_info.get("warnings", []):
        print(f"⚠️ [NETWORK] {warning}")

    # Le reste du processus ne contacte plus le Hub pour des modèles déjà en
    # cache. Les modèles sont chargés depuis leur dossier, sans aucune requête :
    # HF_HUB_OFFLINE seul ne suffit pas (huggingface_hub le fige à son import,
    # déjà fait par configure_network_environment), et même avec
    # local_files_only, sentence-transformers 5 interroge encore le Hub pour le
    # tokenizer. Un proxy TLS (Zscaler...) faisait alors échouer un cache
    # pourtant complet.
    os.environ['HF_HUB_OFFLINE'] = '1'
    os.environ['TRANSFORMERS_OFFLINE'] = '1'
    os.environ['HF_DATASETS_OFFLINE'] = '1'

    print("📦 Chargement du modèle d'embeddings... (Mode offline)")
    try:
        from core.embedding_engine import load_engine  # pylint: disable=import-outside-toplevel

        _SHARED_EMBEDDING_MODEL = load_engine()
    except Exception as error:
        print(f"⚠️ Modèle d'embeddings non disponible: {error}")
        help_msg = build_network_error_help(error)
        if help_msg:
            print(help_msg)
        _SHARED_EMBEDDING_MODEL = None
    _EMBEDDINGS_AVAILABLE = _SHARED_EMBEDDING_MODEL is not None
    return _SHARED_EMBEDDING_MODEL, _EMBEDDINGS_AVAILABLE


# Charger le modèle au démarrage
_load_embedding_model()


def get_shared_embedding_model():
    """
    Retourne le moteur d'embeddings partagé (déjà chargé au démarrage).

    Un core.embedding_engine.EmbeddingEngine : encode() comme
    sentence-transformers, plus encode_query() et encode_document().
    Usage:
        from core.shared import get_shared_embedding_model
        model = get_shared_embedding_model()
        if model:
            embeddings = model.encode_document(texts)
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
