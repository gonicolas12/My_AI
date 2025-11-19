"""
Tests unitaires pour le module de validation (core/validation.py)
"""

import pytest
from pydantic import ValidationError

from core.validation import (
    UserQueryInput,
    FileUploadInput,
    CodeGenerationInput,
    SearchQueryInput,
    ConfigUpdateInput,
    validate_input,
)


class TestUserQueryInput:
    """Tests pour UserQueryInput"""

    def test_valid_query(self):
        """Test d'une requête valide"""
        data = {"query": "Quelle est la capitale de la France?"}
        validated = UserQueryInput(**data)
        assert validated.query == "Quelle est la capitale de la France?"
        assert validated.context is None

    def test_query_with_context(self):
        """Test avec contexte RAG"""
        data = {
            "query": "Résume ce document",
            "context": {
                "rag_context": "Ceci est un document test",
                "source_file": "test.pdf",
            },
        }
        validated = UserQueryInput(**data)
        assert validated.query == "Résume ce document"
        assert validated.context["rag_context"] == "Ceci est un document test"

    def test_empty_query_raises_error(self):
        """Test qu'une requête vide lève une erreur"""
        with pytest.raises(ValidationError):
            UserQueryInput(query="")

    def test_query_too_long_raises_error(self):
        """Test qu'une requête trop longue lève une erreur"""
        long_query = "a" * 10001
        with pytest.raises(ValidationError):
            UserQueryInput(query=long_query)

    def test_dangerous_query_raises_error(self):
        """Test détection d'injections dangereuses"""
        dangerous_queries = [
            '__import__("os").system("rm -rf /")',
            "exec(malicious_code)",
            'eval("print(1)")',
            'os.system("ls")',
        ]

        for query in dangerous_queries:
            with pytest.raises(ValidationError):
                UserQueryInput(query=query)

    def test_query_sanitization(self):
        """Test que les espaces sont nettoyés"""
        data = {"query": "  Question avec espaces  "}
        validated = UserQueryInput(**data)
        assert validated.query == "Question avec espaces"

    def test_context_too_large_raises_error(self):
        """Test qu'un contexte trop volumineux est rejeté"""
        large_context = "a" * 500001
        data = {"query": "test", "context": {"rag_context": large_context}}
        with pytest.raises(ValidationError):
            UserQueryInput(**data)

    def test_invalid_context_keys_raises_error(self):
        """Test que des clés non autorisées sont rejetées"""
        data = {"query": "test", "context": {"malicious_key": "value"}}
        with pytest.raises(ValidationError):
            UserQueryInput(**data)


class TestFileUploadInput:
    """Tests pour FileUploadInput"""

    def test_valid_file_path(self):
        """Test d'un chemin de fichier valide"""
        data = {"file_path": "document.pdf"}
        validated = FileUploadInput(**data)
        assert validated.file_path == "document.pdf"

    def test_path_traversal_raises_error(self):
        """Test détection de path traversal"""
        dangerous_paths = [
            "../../../etc/passwd",
            "~/.ssh/id_rsa",
            "file|cat /etc/passwd",
            "file;rm -rf /",
        ]

        for path in dangerous_paths:
            with pytest.raises(ValidationError):
                FileUploadInput(file_path=path)

    def test_invalid_extension_raises_error(self):
        """Test qu'une extension non autorisée lève une erreur"""
        with pytest.raises(ValidationError):
            FileUploadInput(file_path="malware.exe")

    def test_valid_extensions(self):
        """Test des extensions valides"""
        valid_files = [
            "document.pdf",
            "report.docx",
            "data.csv",
            "code.py",
            "config.json",
        ]

        for file in valid_files:
            validated = FileUploadInput(file_path=file)
            assert validated.file_path == file


class TestCodeGenerationInput:
    """Tests pour CodeGenerationInput"""

    def test_valid_code_request(self):
        """Test d'une requête de code valide"""
        data = {"description": "Fonction pour trier une liste", "language": "python"}
        validated = CodeGenerationInput(**data)
        assert validated.description == "Fonction pour trier une liste"
        assert validated.language == "python"

    def test_default_language_is_python(self):
        """Test que le langage par défaut est Python"""
        data = {"description": "Créer une fonction"}
        validated = CodeGenerationInput(**data)
        assert validated.language == "python"

    def test_invalid_language_raises_error(self):
        """Test qu'un langage invalide lève une erreur"""
        with pytest.raises(ValidationError):
            CodeGenerationInput(description="Test", language="langage_inexistant")

    def test_language_case_insensitive(self):
        """Test que le langage est case-insensitive"""
        data = {"description": "Créer une fonction de test", "language": "JavaScript"}
        validated = CodeGenerationInput(**data)
        assert validated.language == "javascript"


class TestSearchQueryInput:
    """Tests pour SearchQueryInput"""

    def test_valid_search_query(self):
        """Test d'une recherche valide"""
        data = {"query": "Python tutorial", "search_type": "web"}
        validated = SearchQueryInput(**data)
        assert validated.query == "Python tutorial"
        assert validated.search_type == "web"

    def test_max_results_bounds(self):
        """Test les limites de max_results"""
        # Trop petit
        with pytest.raises(ValidationError):
            SearchQueryInput(query="test", max_results=0)

        # Trop grand
        with pytest.raises(ValidationError):
            SearchQueryInput(query="test", max_results=100)

        # Valide
        validated = SearchQueryInput(query="test", max_results=25)
        assert validated.max_results == 25

    def test_invalid_search_type_raises_error(self):
        """Test qu'un type de recherche invalide lève une erreur"""
        with pytest.raises(ValidationError):
            SearchQueryInput(query="test", search_type="invalid_type")


class TestConfigUpdateInput:
    """Tests pour ConfigUpdateInput"""

    def test_valid_config_update(self):
        """Test d'une mise à jour de config valide"""
        data = {"section": "ai", "key": "max_tokens", "value": 8192}
        validated = ConfigUpdateInput(**data)
        assert validated.section == "ai"
        assert validated.key == "max_tokens"
        assert validated.value == 8192

    def test_invalid_section_raises_error(self):
        """Test qu'une section invalide lève une erreur"""
        with pytest.raises(ValidationError):
            ConfigUpdateInput(section="invalid_section", key="some_key", value="value")


class TestValidateInputFunction:
    """Tests pour la fonction validate_input()"""

    def test_validate_query_type(self):
        """Test validation d'une requête"""
        data = {"query": "Test question"}
        validated = validate_input(data, "query")
        assert isinstance(validated, UserQueryInput)
        assert validated.query == "Test question"

    def test_validate_file_type(self):
        """Test validation d'un fichier"""
        data = {"file_path": "test.pdf"}
        validated = validate_input(data, "file")
        assert isinstance(validated, FileUploadInput)

    def test_invalid_input_type_raises_error(self):
        """Test qu'un type invalide lève une erreur"""
        with pytest.raises(ValueError, match="Type d'entrée non reconnu"):
            validate_input({}, "invalid_type")

    def test_validation_error_propagated(self):
        """Test que les erreurs de validation sont propagées"""
        with pytest.raises(ValidationError):
            validate_input({"query": ""}, "query")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
