"""
Validation des entrées utilisateur avec Pydantic
Sécurise toutes les entrées contre injections et malformations
"""

import re
import inspect
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


class UserQueryInput(BaseModel):
    """Validation des requêtes utilisateur"""

    query: str = Field(
        ..., min_length=1, max_length=10000, description="Requête utilisateur"
    )
    context: Optional[Dict[str, Any]] = Field(
        default=None, description="Contexte additionnel (RAG, documents, etc.)"
    )

    @field_validator("query")
    @classmethod
    def sanitize_query(cls, v):
        """Nettoie la requête des caractères dangereux"""
        # Bloquer tentatives d'injection de commandes
        dangerous_patterns = [
            r"__import__",
            r"exec\s*\(",
            r"eval\s*\(",
            r"compile\s*\(",
            r"os\.system",
            r"subprocess",
            r"importlib",
        ]

        for pattern in dangerous_patterns:
            if re.search(pattern, v, re.IGNORECASE):
                raise ValueError(
                    f"Entrée potentiellement dangereuse détectée: {pattern}"
                )

        return v.strip()

    @field_validator("context")
    @classmethod
    def validate_context(cls, v):
        """Valide le contexte additionnel"""
        if v is None:
            return v

        # Limite la taille du contexte
        if isinstance(v, dict):
            # Vérifie les clés attendues
            allowed_keys = {"rag_context", "source_file", "document_type", "metadata"}
            invalid_keys = set(v.keys()) - allowed_keys
            if invalid_keys:
                raise ValueError(f"Clés de contexte non autorisées: {invalid_keys}")

            # Limite la taille du RAG context
            if "rag_context" in v and isinstance(v["rag_context"], str):
                if len(v["rag_context"]) > 500000:  # 500KB max
                    raise ValueError("RAG context trop volumineux (max 500KB)")

        return v


class FileUploadInput(BaseModel):
    """Validation des fichiers uploadés"""

    file_path: str = Field(
        ..., min_length=1, max_length=500, description="Chemin du fichier"
    )
    file_type: Optional[str] = Field(default=None, description="Type MIME du fichier")
    max_size_mb: int = Field(
        default=50, ge=1, le=500, description="Taille maximale en MB"
    )

    @field_validator("file_path")
    @classmethod
    def validate_path(cls, v):
        """Valide le chemin de fichier contre path traversal"""
        # Bloquer path traversal
        dangerous_sequences = ["..", "~", "$", "|", ";", "&", "`"]
        for seq in dangerous_sequences:
            if seq in v:
                raise ValueError(f"Séquence dangereuse dans le chemin: {seq}")

        # Vérifie l'extension
        allowed_extensions = {
            ".pdf",
            ".docx",
            ".doc",
            ".txt",
            ".py",
            ".html",
            ".css",
            ".js",
            ".json",
            ".xml",
            ".md",
            ".csv",
        }
        extension = "." + v.split(".")[-1].lower() if "." in v else ""
        if extension not in allowed_extensions:
            raise ValueError(f"Extension de fichier non autorisée: {extension}")

        return v


class CodeGenerationInput(BaseModel):
    """Validation des requêtes de génération de code"""

    description: str = Field(
        ..., min_length=5, max_length=5000, description="Description du code à générer"
    )
    language: Optional[str] = Field(
        default="python", description="Langage de programmation"
    )
    requirements: Optional[List[str]] = Field(
        default=None, description="Exigences spécifiques"
    )

    @field_validator("language")
    @classmethod
    def validate_language(cls, v):
        """Valide le langage de programmation"""
        allowed_languages = {
            "python",
            "javascript",
            "typescript",
            "java",
            "c",
            "c++",
            "c#",
            "go",
            "rust",
            "ruby",
            "php",
            "swift",
            "kotlin",
            "html",
            "css",
            "sql",
            "bash",
            "powershell",
        }
        if v and v.lower() not in allowed_languages:
            raise ValueError(f"Langage non supporté: {v}")
        return v.lower() if v else "python"


class DocumentProcessInput(BaseModel):
    """Validation des demandes de traitement de document"""

    document_path: str = Field(
        ..., min_length=1, max_length=500, description="Chemin du document"
    )
    action: str = Field(
        ..., description="Action à effectuer (summarize, analyze, extract, etc.)"
    )
    options: Optional[Dict[str, Any]] = Field(
        default=None, description="Options spécifiques au traitement"
    )

    @field_validator("action")
    @classmethod
    def validate_action(cls, v):
        """Valide l'action demandée"""
        allowed_actions = {
            "summarize",
            "analyze",
            "extract",
            "convert",
            "translate",
            "format",
            "merge",
            "split",
        }
        if v.lower() not in allowed_actions:
            raise ValueError(f"Action non supportée: {v}")
        return v.lower()


class SearchQueryInput(BaseModel):
    """Validation des requêtes de recherche (web, code, etc.)"""

    query: str = Field(
        ..., min_length=3, max_length=500, description="Requête de recherche"
    )
    search_type: str = Field(
        default="web", description="Type de recherche (web, code, documentation)"
    )
    max_results: int = Field(
        default=10, ge=1, le=50, description="Nombre maximum de résultats"
    )
    filters: Optional[Dict[str, Any]] = Field(
        default=None, description="Filtres de recherche"
    )

    @field_validator("search_type")
    @classmethod
    def validate_search_type(cls, v):
        """Valide le type de recherche"""
        allowed_types = {"web", "code", "documentation", "stackoverflow", "github"}
        if v.lower() not in allowed_types:
            raise ValueError(f"Type de recherche non supporté: {v}")
        return v.lower()


class ConfigUpdateInput(BaseModel):
    """Validation des mises à jour de configuration"""

    section: str = Field(
        ..., min_length=1, max_length=100, description="Section de configuration à modifier"
    )
    key: str = Field(
        ..., min_length=1, max_length=100, description="Clé de configuration"
    )
    value: Any = Field(..., description="Nouvelle valeur")

    @field_validator("section")
    @classmethod
    def validate_section(cls, v):
        """Valide la section de configuration"""
        allowed_sections = {
            "ai",
            "llm",
            "file_processing",
            "generation",
            "ui",
            "security",
            "logging",
            "performance",
            "optimization",
        }
        if v.lower() not in allowed_sections:
            raise ValueError(f"Section de configuration non autorisée: {v}")
        return v.lower()


# Fonction utilitaire pour valider les entrées
def validate_input(input_data: Dict[str, Any], input_type: str) -> BaseModel:
    """
    Valide une entrée selon son type

    Args:
        input_data: Données à valider
        input_type: Type d'entrée (query, file, code, document, search, config)

    Returns:
        Instance Pydantic validée

    Raises:
        ValueError: Si les données ne passent pas la validation
    """
    validators = {
        "query": UserQueryInput,
        "file": FileUploadInput,
        "code": CodeGenerationInput,
        "document": DocumentProcessInput,
        "search": SearchQueryInput,
        "config": ConfigUpdateInput,
    }

    if input_type not in validators:
        raise ValueError(f"Type d'entrée non reconnu: {input_type}")

    validator_class = validators[input_type]
    return validator_class(**input_data)


# Décorateur pour valider automatiquement les entrées
def validate_user_input(input_type: str):
    """
    Décorateur pour valider automatiquement les entrées de fonction

    Usage:
        @validate_user_input('query')
        def process_query(query: str, context: dict = None):
            # La validation est automatique
            pass
    """

    def decorator(func):
        def wrapper(*args, **kwargs):
            # Construire l'objet d'entrée à partir des arguments
            sig = inspect.signature(func)
            bound_args = sig.bind(*args, **kwargs)
            bound_args.apply_defaults()

            # Valider
            validated = validate_input(bound_args.arguments, input_type)

            # Appeler la fonction avec les données validées
            return func(**validated.dict())

        return wrapper

    return decorator
