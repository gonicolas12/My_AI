"""
📊 BENCHMARK PROFESSIONNEL SYSTÈME 1M TOKENS
My Personal AI Ultra v5.0.0 - Analyse de Performance Complète

Mesures précises des performances pour validation industrielle
"""

import sys
import time
import json
import statistics
from pathlib import Path
from datetime import datetime
import gc

# Configuration du chemin
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

# Imports du système Ultra
try:
    from models.ultra_custom_ai import UltraCustomAIModel
    from models.intelligent_context_manager import UltraIntelligentContextManager
    from core.ai_engine import AIEngine
    ULTRA_AVAILABLE = True
except ImportError as e:
    ULTRA_AVAILABLE = False
    print(f"❌ Système Ultra non disponible: {e}")

class Benchmark1M:
    """Benchmark professionnel du système 1M tokens"""
    
    def __init__(self):
        self.results = {
            "benchmark_date": datetime.now().isoformat(),
            "system_version": "My Personal AI Ultra v5.0.0",
            "test_environment": "Production Ready",
            "performance_metrics": {},
            "scalability_analysis": {},
            "memory_efficiency": {},
            "professional_grade": "PENDING"
        }
    
    def generate_benchmark_content(self, size_tokens: int) -> str:
        """Génère du contenu optimisé pour benchmark"""
        # Contenu technique réaliste
        base_content = """
        Analyse de performance système IA ultra-avancé avec capacité étendue de traitement.
        Implémentation d'algorithmes de compression et d'indexation sémantique optimisés.
        Architecture modulaire permettant scalabilité horizontale et verticale.
        Gestionnaire de contexte intelligent avec éviction automatique des données anciennes.
        Système de chunks adaptatifs avec déduplication et compression en temps réel.
        Indexation vectorielle pour recherche sémantique ultra-rapide dans corpus massifs.
        Pipeline de traitement distribué avec gestion d'erreurs et récupération automatique.
        Interface API RESTful pour intégration enterprise avec authentification et monitoring.
        Base de données vectorielle optimisée pour requêtes de similarité à grande échelle.
        Machine learning intégré pour amélioration continue des performances système.
        """
        
        # Calculer le nombre de répétitions nécessaires
        base_tokens = len(base_content.split())
        repetitions = max(1, size_tokens // base_tokens)
        
        return (base_content + " ") * repetitions
    
    def benchmark_storage_performance(self) -> dict:
        """Benchmark des performances de stockage"""
        print("📊 BENCHMARK STOCKAGE")
        print("-" * 30)
        
        storage_results = {}
        test_sizes = [1000, 5000, 10000, 25000, 50000, 100000, 250000]
        
        context_mgr = UltraIntelligentContextManager()
        
        for size in test_sizes:
            print(f"  📦 Test {size:,} tokens...")
            
            # Générer contenu
            content = self.generate_benchmark_content(size)
            
            # Mesures multiples pour précision
            times = []
            for i in range(3):
                gc.collect()  # Nettoyage mémoire pour mesures précises
                
                start = time.perf_counter()
                chunk_ids = context_mgr.add_ultra_content(
                    content, 
                    content_type=f"benchmark_{size}_{i}",
                    importance_level="medium"
                )
                elapsed = time.perf_counter() - start
                times.append(elapsed)
            
            # Statistiques
            avg_time = statistics.mean(times)
            std_dev = statistics.stdev(times) if len(times) > 1 else 0
            tokens_per_sec = size / avg_time
            
            storage_results[size] = {
                "avg_time_seconds": round(avg_time, 4),
                "std_deviation": round(std_dev, 4),
                "tokens_per_second": round(tokens_per_sec, 0),
                "chunks_created": len(chunk_ids),
                "efficiency_score": round(tokens_per_sec / 1000, 2)  # Score sur 1000 tokens/sec
            }
            
            print(f"    ⏱️  {avg_time:.3f}s ± {std_dev:.3f}s")
            print(f"    ⚡ {tokens_per_sec:,.0f} tokens/sec")
        
        return storage_results
    
    def benchmark_search_performance(self) -> dict:
        """Benchmark des performances de recherche"""
        print("\n🔍 BENCHMARK RECHERCHE")
        print("-" * 30)
        
        search_results = {}
        context_mgr = UltraIntelligentContextManager()
        
        # Préparer corpus de test
        corpus_sizes = [10000, 50000, 100000, 500000]
        search_queries = [
            "analyse performance système",
            "algorithme compression",
            "architecture modulaire",
            "indexation sémantique",
            "machine learning"
        ]
        
        for corpus_size in corpus_sizes:
            print(f"  📚 Corpus {corpus_size:,} tokens...")
            
            # Charger corpus
            content = self.generate_benchmark_content(corpus_size)
            context_mgr.add_ultra_content(content, content_type=f"corpus_{corpus_size}")
            
            # Tester recherches
            search_times = []
            result_counts = []
            
            for query in search_queries:
                times_for_query = []
                
                for _ in range(5):  # 5 mesures par requête
                    start = time.perf_counter()
                    results = context_mgr.search_relevant_chunks(query, max_chunks=10)
                    elapsed = time.perf_counter() - start
                    times_for_query.append(elapsed)
                    result_counts.append(len(results))
                
                search_times.extend(times_for_query)
            
            # Statistiques de recherche
            avg_search_time = statistics.mean(search_times)
            avg_results = statistics.mean(result_counts)
            searches_per_sec = 1 / avg_search_time if avg_search_time > 0 else float('inf')
            
            search_results[corpus_size] = {
                "avg_search_time_ms": round(avg_search_time * 1000, 2),
                "searches_per_second": round(searches_per_sec, 1),
                "avg_results_found": round(avg_results, 1),
                "search_efficiency": round(searches_per_sec * avg_results, 1)
            }
            
            print(f"    🔍 {avg_search_time*1000:.2f}ms par recherche")
            print(f"    📈 {searches_per_sec:.1f} recherches/sec")
    
        return search_results
    
    def benchmark_memory_efficiency(self) -> dict:
        """Benchmark de l'efficacité mémoire"""
        print("\n💾 BENCHMARK MÉMOIRE")
        print("-" * 30)
        
        memory_results = {}
        
        try:
            import psutil
            import os
            
            process = psutil.Process(os.getpid())
            
            # Mesure mémoire initiale
            initial_memory = process.memory_info().rss / 1024 / 1024  # MB
            print(f"  📊 Mémoire initiale: {initial_memory:.1f} MB")
            
            context_mgr = UltraIntelligentContextManager()
            
            # Test progression mémoire
            test_loads = [50000, 100000, 200000, 500000]
            memory_progression = []
            
            for load in test_loads:
                # Charger données
                content = self.generate_benchmark_content(load)
                context_mgr.add_ultra_content(content, content_type=f"memory_test_{load}")
                
                # Mesurer mémoire
                current_memory = process.memory_info().rss / 1024 / 1024
                memory_used = current_memory - initial_memory
                stats = context_mgr.get_stats()
                tokens_loaded = stats.get('total_tokens', 0)
                
                # Calculs d'efficacité
                mb_per_1k_tokens = (memory_used / tokens_loaded * 1000) if tokens_loaded > 0 else 0
                
                memory_progression.append({
                    "tokens_loaded": tokens_loaded,
                    "memory_used_mb": round(memory_used, 1),
                    "mb_per_1k_tokens": round(mb_per_1k_tokens, 3),
                    "efficiency_rating": "Excellent" if mb_per_1k_tokens < 0.5 else 
                                       "Good" if mb_per_1k_tokens < 1.0 else
                                       "Moderate" if mb_per_1k_tokens < 2.0 else "Poor"
                })
                
                print(f"  📈 {tokens_loaded:,} tokens: {memory_used:.1f} MB ({mb_per_1k_tokens:.3f} MB/1k tokens)")
            
            # Analyse finale mémoire
            final_memory = process.memory_info().rss / 1024 / 1024
            total_memory_used = final_memory - initial_memory
            final_stats = context_mgr.get_stats()
            final_tokens = final_stats.get('total_tokens', 0)
            
            memory_results = {
                "initial_memory_mb": round(initial_memory, 1),
                "final_memory_mb": round(final_memory, 1), 
                "total_memory_used_mb": round(total_memory_used, 1),
                "final_tokens_loaded": final_tokens,
                "overall_efficiency_mb_per_1k": round((total_memory_used / final_tokens * 1000), 3) if final_tokens > 0 else 0,
                "memory_progression": memory_progression,
                "efficiency_grade": "A+" if total_memory_used < 100 else
                                   "A" if total_memory_used < 200 else
                                   "B" if total_memory_used < 500 else "C"
            }
            
        except ImportError:
            print("  ⚠️ psutil non disponible - benchmark mémoire limité")
            memory_results = {"status": "unavailable", "reason": "psutil not installed"}
        
        return memory_results
    
    def benchmark_scalability(self) -> dict:
        """Benchmark de scalabilité"""
        print("\n📈 BENCHMARK SCALABILITÉ")
        print("-" * 30)
        
        scalability_results = {}
        context_mgr = UltraIntelligentContextManager()
        
        # Test montée en charge progressive
        load_stages = [
            (10000, "Charge légère"),
            (50000, "Charge modérée"), 
            (100000, "Charge élevée"),
            (250000, "Charge intensive"),
            (500000, "Charge maximale"),
            (750000, "Stress test"),
            (1000000, "Limite absolue")
        ]
        
        cumulative_tokens = 0
        performance_degradation = []
        
        for tokens, description in load_stages:
            print(f"  🎯 {description}: +{tokens:,} tokens...")
            
            content = self.generate_benchmark_content(tokens)
            
            # Mesurer performance
            start = time.perf_counter()
            chunk_ids = context_mgr.add_ultra_content(content, content_type=f"scalability_{tokens}")
            add_time = time.perf_counter() - start
            
            # Mesurer recherche sous charge
            search_start = time.perf_counter()
            results = context_mgr.search_relevant_chunks("performance test", max_chunks=5)
            search_time = time.perf_counter() - search_start
            
            # Statistiques
            stats = context_mgr.get_stats()
            cumulative_tokens = stats.get('total_tokens', 0)
            tokens_per_sec = tokens / add_time if add_time > 0 else float('inf')
            
            stage_result = {
                "stage": description,
                "tokens_added": tokens,
                "cumulative_tokens": cumulative_tokens,
                "add_time_seconds": round(add_time, 3),
                "search_time_ms": round(search_time * 1000, 2),
                "tokens_per_second": round(tokens_per_sec, 0),
                "chunks_total": stats.get('total_chunks', 0),
                "utilization": stats.get('utilization', '0%')
            }
            
            performance_degradation.append(stage_result)
            
            print(f"    ⏱️  Ajout: {add_time:.3f}s ({tokens_per_sec:,.0f} tokens/sec)")
            print(f"    🔍 Recherche: {search_time*1000:.2f}ms")
            print(f"    📊 Total: {cumulative_tokens:,} tokens ({stats.get('utilization', '0%')})")
            
            # Arrêter si on atteint la limite ou performance dégradée
            if cumulative_tokens >= 1000000 or add_time > 1.0:
                if cumulative_tokens >= 1000000:
                    print(f"    🏆 LIMITE 1M TOKENS ATTEINTE!")
                break
        
        # Analyse de la scalabilité
        if len(performance_degradation) > 1:
            first_stage = performance_degradation[0]
            last_stage = performance_degradation[-1]
            
            performance_ratio = last_stage['tokens_per_second'] / first_stage['tokens_per_second']
            scalability_grade = (
                "Excellent" if performance_ratio > 0.8 else
                "Good" if performance_ratio > 0.6 else
                "Moderate" if performance_ratio > 0.4 else
                "Poor"
            )
        else:
            performance_ratio = 1.0
            scalability_grade = "Unknown"
        
        scalability_results = {
            "max_tokens_achieved": cumulative_tokens,
            "stages_completed": len(performance_degradation),
            "performance_ratio": round(performance_ratio, 2),
            "scalability_grade": scalability_grade,
            "stage_details": performance_degradation,
            "linear_scalability": performance_ratio > 0.8
        }
        
        return scalability_results
    
    def calculate_professional_grade(self) -> str:
        """Calcule le grade professionnel du système"""
        metrics = self.results["performance_metrics"]
        
        # Critères d'évaluation
        scores = []
        
        # Performance stockage (tokens/sec pour 100k tokens)
        storage = metrics.get("storage_performance", {})
        if 100000 in storage:
            tps = storage[100000].get("tokens_per_second", 0)
            scores.append(min(100, tps / 1000))  # 100k+ tokens/sec = 100 points
        
        # Performance recherche (recherches/sec)
        search = metrics.get("search_performance", {})
        if search:
            avg_searches_per_sec = statistics.mean([
                data.get("searches_per_second", 0) for data in search.values()
            ])
            scores.append(min(100, avg_searches_per_sec * 10))  # 10+ recherches/sec = 100 points
        
        # Scalabilité
        scalability = metrics.get("scalability_analysis", {})
        max_tokens = scalability.get("max_tokens_achieved", 0)
        scores.append(min(100, max_tokens / 10000))  # 1M tokens = 100 points
        
        # Efficacité mémoire
        memory = metrics.get("memory_efficiency", {})
        if "overall_efficiency_mb_per_1k" in memory:
            efficiency = memory["overall_efficiency_mb_per_1k"]
            # Moins de mémoire = meilleur score (inversé)
            scores.append(max(0, 100 - efficiency * 20))  # < 0.5 MB/1k = score parfait
        
        # Calcul du grade final
        if scores:
            avg_score = statistics.mean(scores)
            if avg_score >= 90:
                return "A+ (Excellence Industrielle)"
            elif avg_score >= 80:
                return "A (Production Haute Performance)"
            elif avg_score >= 70:
                return "B+ (Production Standard)"
            elif avg_score >= 60:
                return "B (Prêt Production)"
            else:
                return "C (Développement/Test)"
        
        return "Non Évalué"
    
    def run_complete_benchmark(self) -> dict:
        """Lance le benchmark complet"""
        print("📊 BENCHMARK PROFESSIONNEL SYSTÈME 1M TOKENS")
        print("=" * 60)
        
        if not ULTRA_AVAILABLE:
            print("❌ Système Ultra non disponible")
            return self.results
        
        start_time = time.perf_counter()
        
        # Exécution des benchmarks
        print("🚀 Lancement des tests de performance...")
        
        self.results["performance_metrics"]["storage_performance"] = self.benchmark_storage_performance()
        self.results["performance_metrics"]["search_performance"] = self.benchmark_search_performance()
        self.results["performance_metrics"]["memory_efficiency"] = self.benchmark_memory_efficiency()
        self.results["performance_metrics"]["scalability_analysis"] = self.benchmark_scalability()
        
        total_time = time.perf_counter() - start_time
        
        # Calcul du grade professionnel
        professional_grade = self.calculate_professional_grade()
        self.results["professional_grade"] = professional_grade
        self.results["total_benchmark_time"] = round(total_time, 2)
        
        # Affichage du résumé
        self.display_benchmark_summary()
        
        return self.results
    
    def display_benchmark_summary(self):
        """Affiche le résumé du benchmark"""
        print("\n" + "=" * 60)
        print("📊 RÉSUMÉ BENCHMARK PROFESSIONNEL")
        print("=" * 60)
        
        metrics = self.results["performance_metrics"]
        
        # Performance stockage
        storage = metrics.get("storage_performance", {})
        if storage:
            max_tps = max(data.get("tokens_per_second", 0) for data in storage.values())
            print(f"📦 Stockage Max: {max_tps:,.0f} tokens/sec")
        
        # Performance recherche
        search = metrics.get("search_performance", {})
        if search:
            avg_search = statistics.mean([
                data.get("searches_per_second", 0) for data in search.values()
            ])
            print(f"🔍 Recherche Moy: {avg_search:.1f} recherches/sec")
        
        # Scalabilité
        scalability = metrics.get("scalability_analysis", {})
        max_tokens = scalability.get("max_tokens_achieved", 0)
        scalability_grade = scalability.get("scalability_grade", "Unknown")
        print(f"📈 Capacité Max: {max_tokens:,} tokens ({scalability_grade})")
        
        # Mémoire
        memory = metrics.get("memory_efficiency", {})
        if "efficiency_grade" in memory:
            print(f"💾 Efficacité Mémoire: Grade {memory['efficiency_grade']}")
        
        # Grade final
        grade = self.results["professional_grade"]
        print(f"\n🏆 GRADE PROFESSIONNEL: {grade}")
        
        # Temps total
        total_time = self.results.get("total_benchmark_time", 0)
        print(f"⏱️ Temps Total: {total_time:.2f} secondes")
        
        # Recommandation
        if "A+" in grade or "A" in grade:
            print(f"\n✅ RECOMMANDATION: DÉPLOIEMENT PRODUCTION IMMÉDIAT")
            print(f"💡 Système de niveau industriel confirmé")
        elif "B" in grade:
            print(f"\n⚡ RECOMMANDATION: SYSTÈME PRÊT PRODUCTION")
            print(f"💡 Performance solide pour environnement professionnel")
        else:
            print(f"\n⚠️ RECOMMANDATION: OPTIMISATIONS SUGGÉRÉES")
            print(f"💡 Système fonctionnel nécessitant améliorations")

def main():
    """Benchmark principal"""
    print("📊 BENCHMARK PROFESSIONNEL SYSTÈME 1M TOKENS")
    print("My Personal AI Ultra v5.0.0")
    print("=" * 60)
    
    print("Ce benchmark va mesurer précisément les performances")
    print("de votre système pour validation industrielle.")
    print()
    
    choice = input("Lancer le benchmark complet? (o/n): ").lower().strip()
    
    if choice in ['o', 'oui', 'y', 'yes']:
        benchmark = Benchmark1M()
        results = benchmark.run_complete_benchmark()
        
        # Sauvegarde des résultats
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"benchmark_1m_results_{timestamp}.json"
        
        with open(filename, "w") as f:
            json.dump(results, f, indent=2)
        
        print(f"\n💾 Résultats sauvés dans '{filename}'")
        print("🎉 Benchmark professionnel terminé!")
        
    else:
        print("Benchmark annulé.")

if __name__ == "__main__":
    main()
