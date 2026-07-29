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

        # Le modèle est simulé : ce test vérifie le passage du contexte,
        # pas la qualité de la génération (et garde le test déterministe).
        with patch.object(
            engine.local_ai, "generate_response", return_value="Réponse simulée"
        ) as mock_generate:
            result = engine.process_text("Question?", context=context)

        assert result == "Réponse simulée"
        # Le contexte validé doit effectivement parvenir au modèle
        transmitted_context = mock_generate.call_args[0][1]
        assert transmitted_context["rag_context"] == "Test context"
        assert transmitted_context["source_file"] == "test.pdf"

    def test_process_text_sanitizes_input(self, engine):
        """Test que l'entrée est nettoyée"""
        with patch.object(
            engine.local_ai, "generate_response", return_value="Réponse simulée"
        ) as mock_generate:
            # Espaces en début/fin
            result = engine.process_text("  Question  ")

        assert result is not None
        # La requête transmise au modèle est débarrassée des espaces superflus
        assert mock_generate.call_args[0][0] == "Question"


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

    def test_model_exchange_is_stored_exactly_once(self):
        """Le modèle mémorise lui-même : process_text ne doit pas dupliquer"""
        engine = AIEngine()
        question = "Explique-moi ce principe en détail"

        # Simule fidèlement CustomAIModel.generate_response, qui enregistre
        # l'échange via _add_to_conversation_history avant de retourner.
        def fake_generate(user_input, context=None):
            engine.conversation_memory.add_conversation(user_input, "Réponse simulée")
            return "Réponse simulée"

        with patch.object(
            engine.local_ai, "generate_response", side_effect=fake_generate
        ):
            engine.process_text(question)

        history = engine.conversation_memory.get_recent_history(limit=10)
        stored = [
            entry
            for entry in history
            if getattr(entry, "user_message", None) == question
        ]
        assert len(stored) == 1


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
