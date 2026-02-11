"""
Compression Monitor - Analyse et expose les métriques de compression
Calcul des ratios de compression, stats et monitoring
"""

import json
import time
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from utils.logger import setup_logger


class CompressionMonitor:
    """
    Moniteur de compression pour analyser l'efficacité du chunking et de la compression

    Fonctionnalités:
    - Calcul des ratios de compression en temps réel
    - Statistiques détaillées par type de contenu
    - Historique des compressions
    - Rapports et visualisations
    """

    def __init__(self):
        """Initialise le moniteur de compression"""
        self.logger = setup_logger("CompressionMonitor")

        # Historique des compressions
        self.compression_history: List[Dict[str, Any]] = []

        # Stats globales
        self.stats = {
            "total_documents": 0,
            "total_original_size": 0,
            "total_compressed_size": 0,
            "total_chunks": 0,
            "average_ratio": 0.0,
            "best_ratio": 0.0,
            "worst_ratio": 0.0,
            "by_content_type": {},
        }

        self.logger.info("✅ Compression Monitor initialisé")

    def analyze_compression(
        self,
        original_text: str,
        chunks: List[str],
        document_name: str = "",
        content_type: str = "text",
        metadata: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """
        Analyse la compression d'un document

        Args:
            original_text: Texte original
            chunks: Liste des chunks créés
            document_name: Nom du document
            content_type: Type de contenu (text, code, pdf, docx, etc.)
            metadata: Métadonnées additionnelles

        Returns:
            Analyse de compression complète
        """
        # Calculs de base
        original_size = len(original_text)
        original_tokens = len(original_text.split())  # Approximation

        # Taille des chunks
        chunk_sizes = [len(chunk) for chunk in chunks]
        total_chunk_size = sum(chunk_sizes)

        # Calcul du ratio de compression
        # Ratio = taille originale / taille compressée (chunks)
        # Un ratio élevé = bonne compression
        if total_chunk_size > 0:
            compression_ratio = original_size / total_chunk_size
        else:
            compression_ratio = 1.0

        # Overhead (redondance due au chevauchement)
        overhead = total_chunk_size - original_size
        overhead_percent = (overhead / original_size * 100) if original_size > 0 else 0

        # Efficacité (inverse de l'overhead)
        efficiency = 100 - overhead_percent

        # Analyse détaillée
        analysis = {
            "document_name": document_name,
            "content_type": content_type,
            "timestamp": datetime.now().isoformat(),
            # Tailles
            "original_size": original_size,
            "original_tokens": original_tokens,
            "chunk_count": len(chunks),
            "total_chunk_size": total_chunk_size,
            "average_chunk_size": total_chunk_size / len(chunks) if chunks else 0,
            # Ratios
            "compression_ratio": compression_ratio,
            "compression_ratio_formatted": f"{compression_ratio:.1f}:1",
            "space_saved_bytes": original_size - total_chunk_size,
            "space_saved_percent": (
                ((original_size - total_chunk_size) / original_size * 100)
                if original_size > 0
                else 0
            ),
            # Overhead
            "overhead_bytes": overhead,
            "overhead_percent": overhead_percent,
            "efficiency": efficiency,
            # Distribution des chunks
            "min_chunk_size": min(chunk_sizes) if chunk_sizes else 0,
            "max_chunk_size": max(chunk_sizes) if chunk_sizes else 0,
            "avg_chunk_size": sum(chunk_sizes) / len(chunk_sizes) if chunk_sizes else 0,
            # Qualité
            "quality_score": self._calculate_quality_score(
                compression_ratio, efficiency, len(chunks)
            ),
            # Métadonnées
            "metadata": metadata or {},
        }

        # Ajouter à l'historique
        self.compression_history.append(analysis)

        # Mettre à jour les stats globales
        self._update_stats(analysis)

        # Log
        self.logger.info(
            "📊 Compression: %s | Ratio: %s | Chunks: %d | Efficacité: %.1f%%",
            document_name,
            analysis['compression_ratio_formatted'],
            len(chunks),
            efficiency
        )

        return analysis

    def _calculate_quality_score(
        self, compression_ratio: float, efficiency: float, chunk_count: int
    ) -> float:
        """
        Calcule un score de qualité global (0-100)

        Args:
            compression_ratio: Ratio de compression
            efficiency: Efficacité (%)
            chunk_count: Nombre de chunks

        Returns:
            Score de qualité
        """
        # Normaliser le ratio (bon si > 2.0, excellent si > 10.0)
        ratio_score = min(100, (compression_ratio / 10.0) * 100)

        # Score d'efficacité (directement en %)
        efficiency_score = efficiency

        # Pénalité pour trop de chunks (fragmentation)
        chunk_penalty = min(20, max(0, (chunk_count - 10) * 2))

        # Score final (pondéré)
        quality = (ratio_score * 0.4 + efficiency_score * 0.5) - chunk_penalty

        return max(0, min(100, quality))

    def _update_stats(self, analysis: Dict[str, Any]):
        """
        Met à jour les statistiques globales

        Args:
            analysis: Analyse de compression
        """
        content_type = analysis["content_type"]

        # Stats globales
        self.stats["total_documents"] += 1
        self.stats["total_original_size"] += analysis["original_size"]
        self.stats["total_compressed_size"] += analysis["total_chunk_size"]
        self.stats["total_chunks"] += analysis["chunk_count"]

        # Ratio moyen
        if self.stats["total_original_size"] > 0:
            self.stats["average_ratio"] = (
                self.stats["total_original_size"] / self.stats["total_compressed_size"]
            )

        # Meilleur et pire ratios
        ratio = analysis["compression_ratio"]
        if self.stats["best_ratio"] == 0 or ratio > self.stats["best_ratio"]:
            self.stats["best_ratio"] = ratio
        if self.stats["worst_ratio"] == 0 or ratio < self.stats["worst_ratio"]:
            self.stats["worst_ratio"] = ratio

        # Stats par type de contenu
        if content_type not in self.stats["by_content_type"]:
            self.stats["by_content_type"][content_type] = {
                "count": 0,
                "total_original": 0,
                "total_compressed": 0,
                "average_ratio": 0.0,
            }

        type_stats = self.stats["by_content_type"][content_type]
        type_stats["count"] += 1
        type_stats["total_original"] += analysis["original_size"]
        type_stats["total_compressed"] += analysis["total_chunk_size"]

        if type_stats["total_compressed"] > 0:
            type_stats["average_ratio"] = (
                type_stats["total_original"] / type_stats["total_compressed"]
            )

    def get_stats(self, content_type: Optional[str] = None) -> Dict[str, Any]:
        """
        Récupère les statistiques

        Args:
            content_type: Type de contenu spécifique (None pour tous)

        Returns:
            Statistiques
        """
        if content_type and content_type in self.stats["by_content_type"]:
            # Stats pour un type spécifique
            type_stats = self.stats["by_content_type"][content_type]

            return {
                "content_type": content_type,
                "documents": type_stats["count"],
                "original_size": type_stats["total_original"],
                "compressed_size": type_stats["total_compressed"],
                "average_ratio": type_stats["average_ratio"],
                "average_ratio_formatted": f"{type_stats['average_ratio']:.1f}:1",
                "space_saved": type_stats["total_original"]
                - type_stats["total_compressed"],
                "space_saved_percent": (
                    (
                        (type_stats["total_original"] - type_stats["total_compressed"])
                        / type_stats["total_original"]
                        * 100
                    )
                    if type_stats["total_original"] > 0
                    else 0
                ),
            }
        else:
            # Stats globales avec formatage
            return {
                "total_documents": self.stats["total_documents"],
                "total_original_size": self.stats["total_original_size"],
                "total_compressed_size": self.stats["total_compressed_size"],
                "total_chunks": self.stats["total_chunks"],
                "average_ratio": self.stats["average_ratio"],
                "average_ratio_formatted": f"{self.stats['average_ratio']:.1f}:1",
                "best_ratio": self.stats["best_ratio"],
                "best_ratio_formatted": f"{self.stats['best_ratio']:.1f}:1",
                "worst_ratio": self.stats["worst_ratio"],
                "worst_ratio_formatted": f"{self.stats['worst_ratio']:.1f}:1",
                "space_saved": self.stats["total_original_size"]
                - self.stats["total_compressed_size"],
                "space_saved_percent": (
                    (
                        (
                            self.stats["total_original_size"]
                            - self.stats["total_compressed_size"]
                        )
                        / self.stats["total_original_size"]
                        * 100
                    )
                    if self.stats["total_original_size"] > 0
                    else 0
                ),
                "by_content_type": self.stats["by_content_type"],
            }

    def get_recent_compressions(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Récupère les compressions récentes

        Args:
            limit: Nombre de résultats

        Returns:
            Liste des compressions récentes
        """
        return self.compression_history[-limit:]

    def get_compression_report(self) -> str:
        """
        Génère un rapport de compression détaillé

        Returns:
            Rapport formaté en texte
        """
        stats = self.get_stats()

        report_lines = [
            "=" * 70,
            "📊 RAPPORT DE COMPRESSION INTELLIGENTE",
            "=" * 70,
            "",
            "📈 STATISTIQUES GLOBALES",
            "-" * 70,
            f"Total de documents traités: {stats['total_documents']}",
            f"Total de chunks créés: {stats['total_chunks']}",
            f"Taille originale totale: {self._format_size(stats['total_original_size'])}",
            f"Taille compressée totale: {self._format_size(stats['total_compressed_size'])}",
            f"Espace économisé: {self._format_size(stats['space_saved'])} ({stats['space_saved_percent']:.1f}%)",
            "",
            "📏 RATIOS DE COMPRESSION",
            "-" * 70,
            f"Ratio moyen: {stats['average_ratio_formatted']}",
            f"Meilleur ratio: {stats['best_ratio_formatted']}",
            f"Pire ratio: {stats['worst_ratio_formatted']}",
            "",
        ]

        # Stats par type de contenu
        if stats["by_content_type"]:
            report_lines.extend(["📂 PAR TYPE DE CONTENU", "-" * 70])

            for content_type, type_stats in stats["by_content_type"].items():
                type_ratio = f"{type_stats['average_ratio']:.1f}:1"
                report_lines.append(
                    f"  {content_type.upper()}: {type_stats['count']} docs | "
                    f"Ratio: {type_ratio}"
                )
            report_lines.append("")

        # Compressions récentes
        recent = self.get_recent_compressions(5)
        if recent:
            report_lines.extend(["🕒 COMPRESSIONS RÉCENTES (5 dernières)", "-" * 70])

            for comp in recent:
                report_lines.append(
                    f"  {comp['document_name'][:40]:<40} | "
                    f"{comp['compression_ratio_formatted']:>8} | "
                    f"Efficacité: {comp['efficiency']:>5.1f}%"
                )
            report_lines.append("")

        report_lines.append("=" * 70)

        return "\n".join(report_lines)

    def _format_size(self, size_bytes: int) -> str:
        """
        Formate une taille en bytes de manière lisible

        Args:
            size_bytes: Taille en bytes

        Returns:
            Taille formatée
        """
        for unit in ["B", "KB", "MB", "GB"]:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} TB"

    def benchmark_compression(
        self, text_samples: List[Tuple[str, str, str]]
    ) -> Dict[str, Any]:
        """
        Benchmark de différents textes pour comparer la compression

        Args:
            text_samples: Liste de (texte, nom, type)

        Returns:
            Résultats du benchmark
        """
        self.logger.info("🏁 Démarrage du benchmark de compression")

        results = []
        start_time = time.time()

        for text, name, content_type in text_samples:
            # Simuler le chunking (simple split par mots)
            words = text.split()
            chunk_size = 256  # mots par chunk
            chunks = []

            for i in range(0, len(words), chunk_size):
                chunk = " ".join(words[i : i + chunk_size])
                chunks.append(chunk)

            # Analyser
            analysis = self.analyze_compression(text, chunks, name, content_type)
            results.append(analysis)

        duration = time.time() - start_time

        # Résumé du benchmark
        summary = {
            "samples_tested": len(text_samples),
            "duration": duration,
            "average_ratio": sum(r["compression_ratio"] for r in results)
            / len(results),
            "average_efficiency": sum(r["efficiency"] for r in results) / len(results),
            "best_compression": max(results, key=lambda x: x["compression_ratio"]),
            "worst_compression": min(results, key=lambda x: x["compression_ratio"]),
            "results": results,
        }

        self.logger.info(
            "✅ Benchmark terminé en %.2fs | Ratio moyen: %.1f:1",
            duration,
            summary['average_ratio']
        )

        return summary

    def export_stats(self, output_path: str):
        """
        Exporte les statistiques au format JSON

        Args:
            output_path: Chemin du fichier de sortie
        """
        stats = self.get_stats()
        stats["history"] = self.compression_history
        stats["exported_at"] = datetime.now().isoformat()

        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(stats, f, indent=2, ensure_ascii=False)

        self.logger.info("📊 Statistiques exportées vers %s", output_path)

    def reset_stats(self):
        """Réinitialise toutes les statistiques"""
        self.compression_history = []
        self.stats = {
            "total_documents": 0,
            "total_original_size": 0,
            "total_compressed_size": 0,
            "total_chunks": 0,
            "average_ratio": 0.0,
            "best_ratio": 0.0,
            "worst_ratio": 0.0,
            "by_content_type": {},
        }
        self.logger.info("🔄 Statistiques réinitialisées")


# Singleton global
_COMPRESSION_MONITOR_INSTANCE = None


def get_compression_monitor() -> CompressionMonitor:
    """Récupère l'instance singleton du Compression Monitor"""
    global _COMPRESSION_MONITOR_INSTANCE
    if _COMPRESSION_MONITOR_INSTANCE is None:
        _COMPRESSION_MONITOR_INSTANCE = CompressionMonitor()
    return _COMPRESSION_MONITOR_INSTANCE
