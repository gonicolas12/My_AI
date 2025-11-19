"""
Tests unitaires pour core/ai_engine.py
"""

from unittest.mock import patch

import pytest
from pydantic import ValidationError

from core.ai_engine import AIEngine


class TestAIEngineInit:
    """Tests d'initialisation de AIEngine"""

    def test_engine_initializes_successfully(self):
        """Test que le moteur s'initialise correctement"""
        engine = AIEngine()
        assert engine is not None
        assert engine.conversation_memory is not None
        assert engine.local_ai is not None

    def test_session_context_initialized(self):
        """Test que le contexte de session est initialisé"""
        engine = AIEngine()
        assert "documents_processed" in engine.session_context
        assert "code_files_processed" in engine.session_context
        assert isinstance(engine.session_context["documents_processed"], list)


class TestProcessText:
    """Tests pour la méthode process_text()"""

    @pytest.fixture
    def engine(self):
        """Fixture qui crée une instance de AIEngine"""
        return AIEngine()

    def test_process_text_validates_input(self, engine):
        """Test que process_text valide l'entrée"""
        # Requête valide
        result = engine.process_text("Bonjour")
        assert result is not None
        assert isinstance(result, str)

    def test_process_text_rejects_empty_query(self, engine):
        """Test que les requêtes vides sont rejetées"""
        with pytest.raises(ValidationError):
            engine.process_text("")

    def test_process_text_rejects_dangerous_input(self, engine):
        """Test que les entrées dangereuses sont rejetées"""
        dangerous_queries = [
            '__import__("os").system("ls")',
            "exec(malicious_code)",
            'eval("bad code")',
        ]

        for query in dangerous_queries:
            with pytest.raises(ValidationError):
                engine.process_text(query)

    def test_process_text_with_context(self, engine):
        """Test que le contexte est passé correctement"""
        context = {"rag_context": "Test context", "source_file": "test.pdf"}
        result = engine.process_text("Question?", context=context)
        assert result is not None

    def test_process_text_sanitizes_input(self, engine):
        """Test que l'entrée est nettoyée"""
        # Espaces en début/fin
        result = engine.process_text("  Question  ")
        assert result is not None
        # Vérifie que la requête a été traitée (pas rejetée)


class TestFileProcessing:
    """Tests pour le traitement de fichiers"""

    @pytest.fixture
    def engine(self):
        """Teste le moteur de l'IA"""
        return AIEngine()

    def test_process_pdf_validates_path(self, engine):
        """Test validation du chemin de fichier PDF"""
        # Path traversal devrait être bloqué
        with pytest.raises(Exception):  # ValidationError ou autre
            engine.process_file("../../../etc/passwd")

    def test_process_pdf_validates_extension(self, engine):
        """Test validation de l'extension"""
        # Extension non autorisée
        with pytest.raises(Exception):
            engine.process_file("malware.exe")


class TestConversationMemory:
    """Tests pour l'intégration avec ConversationMemory"""

    def test_conversation_is_stored(self):
        """Test que les conversations sont stockées"""
        engine = AIEngine()

        # Traiter une requête
        engine.process_text("Bonjour")

        # Vérifier que la mémoire a été mise à jour
        history = engine.conversation_memory.get_recent_history(limit=1)
        assert len(history) > 0


class TestErrorHandling:
    """Tests de gestion d'erreurs"""

    def test_handles_model_error_gracefully(self):
        """Test que les erreurs du modèle sont gérées"""
        engine = AIEngine()

        # Mock le modèle pour qu'il lève une erreur
        with patch.object(
            engine.local_ai, "generate_response", side_effect=Exception("Model error")
        ):
            result = engine.process_text("Test")
            # Devrait retourner un message d'erreur, pas crasher
            assert "erreur" in result.lower() or "problème" in result.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
