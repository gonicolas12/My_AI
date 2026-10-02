"""
Tests du moniteur de compression (core/compression_monitor.py), qui mesure le
découpage en morceaux des documents ajoutés à VectorMemory.

Le moniteur ne garde rien sur disque ; la mémoire vectorielle est créée dans
un dossier temporaire, pas dans memory/vector_store, celle de l'utilisateur.
"""

import pytest

from core.compression_monitor import CompressionMonitor
from memory.vector_memory import VectorMemory


def test_overlapping_chunks_lower_efficiency():
    monitor = CompressionMonitor()
    text = "a" * 1000
    exact = monitor.analyze_compression(text, ["a" * 250] * 4, "exact.txt")
    overlap = monitor.analyze_compression(text, ["a" * 300] * 4, "chevauchement.txt")
    assert exact["compression_ratio"] == pytest.approx(1.0)
    assert exact["efficiency"] == pytest.approx(100)
    assert overlap["compression_ratio"] == pytest.approx(1000 / 1200)
    assert overlap["efficiency"] == pytest.approx(80)  # 200 caractères répétés
    assert overlap["quality_score"] < exact["quality_score"]


def test_stats_are_kept_per_content_type():
    monitor = CompressionMonitor()
    monitor.analyze_compression("x" * 400, ["x" * 200] * 2, "notes.txt", content_type="text")
    monitor.analyze_compression("y" * 600, ["y" * 300] * 2, "script.py", content_type="code")
    stats = monitor.get_stats()
    assert (stats["total_documents"], stats["total_chunks"]) == (2, 4)
    assert monitor.get_stats("code")["documents"] == 1


def test_vector_memory_reports_the_compression_of_added_documents(tmp_path):
    memory = VectorMemory(storage_dir=str(tmp_path), chunk_size=256, enable_encryption=False)
    result = memory.add_document(
        content="Python programming test content. " * 50,
        document_name="test_doc.txt",
        metadata={"type": "text"},
    )
    assert result["status"] == "success"
    assert result["compression"]["ratio_formatted"].endswith(":1")
    assert 0 <= result["compression"]["quality_score"] <= 100
