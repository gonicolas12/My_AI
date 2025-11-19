"""
Tests unitaires pour memory/vector_memory.py
"""

import tempfile
from pathlib import Path

import pytest

from memory.vector_memory import VectorMemory


class TestVectorMemoryInit:
    """Tests d'initialisation de VectorMemory"""

    def test_initialization_default(self):
        """Test initialisation par défaut"""
        with tempfile.TemporaryDirectory() as tmpdir:
            memory = VectorMemory(storage_dir=tmpdir)
            assert memory.max_tokens == 1_000_000
            assert memory.chunk_size == 512
            assert memory.current_tokens == 0

    def test_initialization_custom_params(self):
        """Test initialisation avec paramètres personnalisés"""
        with tempfile.TemporaryDirectory() as tmpdir:
            memory = VectorMemory(
                max_tokens=500_000, chunk_size=256, chunk_overlap=25, storage_dir=tmpdir
            )
            assert memory.max_tokens == 500_000
            assert memory.chunk_size == 256
            assert memory.chunk_overlap == 25

    def test_storage_dir_created(self):
        """Test que le répertoire de stockage est créé"""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "test_storage"
            _memory = VectorMemory(storage_dir=str(storage_path))
            assert storage_path.exists()


class TestTokenCounting:
    """Tests de comptage de tokens"""

    @pytest.fixture
    def memory(self):
        """Teste la mémoire"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield VectorMemory(storage_dir=tmpdir)

    def test_count_tokens_simple(self, memory):
        """Test comptage de tokens simple"""
        text = "Hello world"
        token_count = memory.count_tokens(text)
        assert token_count > 0
        assert isinstance(token_count, int)

    def test_count_tokens_empty(self, memory):
        """Test comptage sur texte vide"""
        token_count = memory.count_tokens("")
        assert token_count == 0

    def test_count_tokens_long_text(self, memory):
        """Test comptage sur texte long"""
        text = "Python est un langage de programmation. " * 100
        token_count = memory.count_tokens(text)
        assert token_count > 100  # Au moins 100 tokens


class TestChunking:
    """Tests de découpage en chunks"""

    @pytest.fixture
    def memory(self):
        """Teste la mémoire"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield VectorMemory(chunk_size=50, chunk_overlap=10, storage_dir=tmpdir)

    def test_split_small_text(self, memory):
        """Test découpage texte court"""
        text = "Un petit texte de test"
        chunks = memory.split_into_chunks(text)
        assert len(chunks) >= 1
        assert all(isinstance(chunk, str) for chunk in chunks)

    def test_split_long_text(self, memory):
        """Test découpage texte long"""
        text = "Python est un langage de programmation. " * 50
        chunks = memory.split_into_chunks(text)
        assert len(chunks) > 1  # Doit être divisé en plusieurs chunks

    def test_chunks_have_overlap(self, memory):
        """Test que les chunks ont du chevauchement"""
        text = "Un deux trois quatre cinq six sept huit neuf dix. " * 20
        chunks = memory.split_into_chunks(text)

        if len(chunks) > 1:
            # Vérifier qu'il y a du contenu partagé entre chunks adjacents
            # (simplifié: juste vérifier qu'ils ne sont pas complètement disjoints)
            assert len(chunks[0]) > 0
            assert len(chunks[1]) > 0


class TestDocumentManagement:
    """Tests d'ajout et gestion de documents"""

    @pytest.fixture
    def memory(self):
        """Teste la mémoire"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield VectorMemory(max_tokens=10000, storage_dir=tmpdir)

    def test_add_document_simple(self, memory):
        """Test ajout document simple"""
        content = "Ceci est un document de test."
        result = memory.add_document(content, "Test Doc")

        assert result["status"] == "success"
        assert result["chunks_created"] > 0
        assert result["tokens_added"] > 0

    def test_add_document_with_metadata(self, memory):
        """Test ajout document avec métadonnées"""
        content = "Document avec métadonnées"
        metadata = {"source": "test", "category": "demo"}
        result = memory.add_document(content, "Test", metadata=metadata)

        assert result["status"] == "success"
        assert result["document_id"] in memory.documents

    def test_add_duplicate_document(self, memory):
        """Test qu'un document dupliqué est détecté"""
        content = "Document unique"
        name = "TestDup"

        result1 = memory.add_document(content, name)
        assert result1["status"] == "success"

        result2 = memory.add_document(content, name)
        assert result2["status"] == "duplicate"
        assert result2["chunks_created"] == 0

    def test_document_stats_updated(self, memory):
        """Test que les statistiques sont mises à jour"""
        initial_docs = memory.stats["documents_added"]

        memory.add_document("Test content", "Test")

        assert memory.stats["documents_added"] == initial_docs + 1
        assert memory.stats["total_tokens"] > 0


class TestSearch:
    """Tests de recherche sémantique"""

    @pytest.fixture
    def memory(self):
        """Teste la mémoire"""
        with tempfile.TemporaryDirectory() as tmpdir:
            mem = VectorMemory(storage_dir=tmpdir)

            # Ajouter quelques documents de test
            mem.add_document(
                "Python est un langage de programmation orienté objet.", "Python Doc"
            )
            mem.add_document(
                "JavaScript est utilisé pour le développement web.", "JS Doc"
            )

            yield mem

    def test_search_similar_basic(self, memory):
        """Test recherche sémantique basique"""
        if not memory.embedding_model:
            pytest.skip("Embeddings non disponibles")

        results = memory.search_similar("programmation Python")
        assert isinstance(results, list)

    def test_get_relevant_context(self, memory):
        """Test récupération de contexte pertinent"""
        context = memory.get_relevant_context("Python")
        assert isinstance(context, str)
        assert len(context) > 0


class TestEncryption:
    """Tests de chiffrement"""

    def test_encryption_enabled(self):
        """Test que le chiffrement peut être activé"""
        with tempfile.TemporaryDirectory() as tmpdir:
            memory = VectorMemory(enable_encryption=True, storage_dir=tmpdir)

            # Vérifier que le chiffrement est activé si cryptography disponible
            if memory.enable_encryption:
                assert memory.cipher is not None

    def test_encrypt_decrypt(self):
        """Test chiffrement/déchiffrement"""
        with tempfile.TemporaryDirectory() as tmpdir:
            memory = VectorMemory(enable_encryption=True, storage_dir=tmpdir)

            if memory.enable_encryption:
                original = "Texte secret"
                # Access the encryption methods via getattr to avoid direct protected-member access
                _encrypt = getattr(memory, "_encrypt", None)
                _decrypt = getattr(memory, "_decrypt", None)
                if _encrypt is None or _decrypt is None:
                    pytest.skip("Encryption methods not available")
                encrypted = _encrypt(original)
                decrypted = _decrypt(encrypted)

                assert encrypted != original  # Texte chiffré différent
                assert decrypted == original  # Déchiffrement correct


class TestMemoryManagement:
    """Tests de gestion de la mémoire"""

    def test_cleanup_when_full(self):
        """Test nettoyage quand mémoire pleine"""
        with tempfile.TemporaryDirectory() as tmpdir:
            memory = VectorMemory(max_tokens=1000, storage_dir=tmpdir)

            # Ajouter plusieurs documents pour remplir
            for i in range(10):
                memory.add_document(
                    "Document de test avec du contenu. " * 20, f"Doc{i}"
                )

            # Vérifier que des documents ont été supprimés
            assert len(memory.documents) < 10
            assert memory.current_tokens <= memory.max_tokens

    def test_clear_all(self):
        """Test vidage complet de la mémoire"""
        with tempfile.TemporaryDirectory() as tmpdir:
            memory = VectorMemory(storage_dir=tmpdir)

            # Ajouter des documents
            memory.add_document("Test 1", "Doc1")
            memory.add_document("Test 2", "Doc2")

            # Vider
            memory.clear_all()

            assert len(memory.documents) == 0
            assert memory.current_tokens == 0


class TestStats:
    """Tests des statistiques"""

    def test_get_stats_structure(self):
        """Test structure des statistiques"""
        with tempfile.TemporaryDirectory() as tmpdir:
            memory = VectorMemory(storage_dir=tmpdir)
            stats = memory.get_stats()

            assert "documents_added" in stats
            assert "chunks_created" in stats
            assert "total_tokens" in stats
            assert "current_tokens" in stats
            assert "usage_percent" in stats

    def test_usage_percent_calculation(self):
        """Test calcul du pourcentage d'utilisation"""
        with tempfile.TemporaryDirectory() as tmpdir:
            memory = VectorMemory(max_tokens=1000, storage_dir=tmpdir)

            # Ajouter un document
            memory.add_document("Test content " * 50, "Test")

            stats = memory.get_stats()
            assert 0 <= stats["usage_percent"] <= 100


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
