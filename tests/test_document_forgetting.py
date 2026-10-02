"""
Tests de l'oubli d'un document (pièce jointe retirée avant l'envoi).

Un fichier joint puis retiré restait partout : mémoire de session, mémoire
vectorielle (y compris la base ChromaDB persistante, donc après redémarrage)
et analyse du document. Chaque couche sait maintenant l'oublier.
"""

import tempfile
from types import SimpleNamespace

import pytest

from memory.vector_memory import VectorMemory
from models.conversation_memory import ConversationMemory
from models.intelligent_document_analyzer import IntelligentDocumentAnalyzer
from models.mixins.context_management import ContextManagementMixin

KEPT, REMOVED = "297A1T.pdf", "RUB4026.pdf"


def test_session_memory_forgets_the_document_and_renumbers():
    memory = ConversationMemory()
    memory.store_document_content(REMOVED, "ruban adhésif mousse")
    memory.store_document_content(KEPT, "fiche de la thiourée")
    assert memory.remove_document(REMOVED) is True
    assert list(memory.stored_documents) == [KEPT] and memory.document_order == [KEPT]
    assert memory.stored_documents[KEPT]["order_index"] == 0  # « le premier document »
    assert memory.remove_document(REMOVED) is False


@pytest.fixture(name="vector_memory")
def _vector_memory():
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
        yield VectorMemory(max_tokens=100_000, storage_dir=tmpdir)


def test_vector_memory_deletes_chunks_from_chromadb(vector_memory):
    vector_memory.add_document("Fiche de sécurité de la thiourée. " * 60, document_name=KEPT)
    vector_memory.add_document("Ruban adhésif mousse double face. " * 60, document_name=REMOVED)
    tokens_before = vector_memory.current_tokens

    removed = vector_memory.remove_document(REMOVED)
    assert removed > 0
    assert [info["name"] for info in vector_memory.documents.values()] == [KEPT]
    assert vector_memory.stats["documents_added"] == 1
    assert vector_memory.current_tokens < tokens_before
    collection = vector_memory.document_collection
    if collection is not None and vector_memory.embedding_model is not None:
        assert collection.get(where={"document_name": REMOVED})["ids"] == []
        assert collection.get(where={"document_name": KEPT})["ids"]


def test_vector_memory_ignores_unknown_document(vector_memory):
    assert vector_memory.remove_document("absent.pdf") == 0


def test_analyzer_forgets_only_its_current_document():
    analyzer = IntelligentDocumentAnalyzer()
    analyzer.analyze_document("La thiourée est un solide blanc. Numéro CAS 62-56-6. " * 5, KEPT)
    assert analyzer.forget(REMOVED) is False and analyzer.sections
    assert analyzer.forget(KEPT) is True
    assert not analyzer.sections and not analyzer.facts and analyzer.analyzed_document == ""


def test_custom_ai_forgets_everywhere():
    class FakeVectorMemory:
        removed = []

        def remove_document(self, name):
            self.removed.append(name)
            return 13

    class Model(ContextManagementMixin):
        def __init__(self):
            self.conversation_memory = ConversationMemory()
            self.conversation_memory.store_document_content(REMOVED, "ruban adhésif")
            self.ultra_mode = True
            self.context_manager = FakeVectorMemory()
            self.document_analyzer = SimpleNamespace(forget=lambda name: forgotten.append(name))
            self.session_context = {"documents_processed": [REMOVED, KEPT],
                                    "code_files_processed": [], "current_document": REMOVED}

    forgotten = []
    model = Model()
    assert model.remove_document_from_context(REMOVED) == {"stored": True, "chunks_removed": 13}
    assert REMOVED not in model.conversation_memory.stored_documents
    assert model.context_manager.removed == [REMOVED] and forgotten == [REMOVED]
    assert model.session_context["documents_processed"] == [KEPT]
    assert model.session_context["current_document"] is None
