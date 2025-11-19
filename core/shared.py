"""
Module partagé pour éviter les imports circulaires
Contient les classes et fonctions utilisées par plusieurs modules
"""

from typing import Any, Dict, List
from dataclasses import dataclass, field


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
