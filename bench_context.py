#!/usr/bin/env python3
"""
🎯 Benchmark de Fenêtre de Contexte - My_AI Project
Test spécialisé pour mesurer les limites et performances du contexte
"""

import os
import sys
import time
import json
import psutil
import gc
from typing import Dict, Any, List, Tuple
from pathlib import Path
from datetime import datetime
import matplotlib.pyplot as plt
import numpy as np

# Ajout du path pour imports locaux
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from models.custom_ai_model import CustomAIModel
from models.conversation_memory import ConversationMemory

class ContextBenchmark:
    """Benchmark spécialisé pour la fenêtre de contexte"""
    
    def __init__(self):
        self.results = {}
        self.model = None
        
    def run_comprehensive_benchmark(self) -> Dict[str, Any]:
        """Lance un benchmark complet de la fenêtre de contexte"""
        print("🎯 Benchmark Complet de la Fenêtre de Contexte")
        print("=" * 60)
        
        # 1. Test de montée en charge progressive
        self.results["scale_test"] = self._test_progressive_scaling()
        
        # 2. Test de types de contenu différents
        self.results["content_type_test"] = self._test_content_types()
        
        # 3. Test de performance mémoire
        self.results["memory_performance"] = self._test_memory_efficiency()
        
        # 4. Test de stabilité long-terme
        self.results["stability_test"] = self._test_long_term_stability()
        
        # 5. Générer recommandations
        self.results["recommendations"] = self._generate_context_recommendations()
        
        # 6. Sauvegarder et visualiser
        self._save_benchmark_results()
        self._generate_performance_plots()
        
        return self.results
    
    def _test_progressive_scaling(self) -> Dict[str, Any]:
        """Test de montée en charge progressive du contexte"""
        print("📈 Test de montée en charge progressive...")
        
        self.model = CustomAIModel(ConversationMemory())
        
        # Tailles de test exponentielles
        test_sizes = [128, 256, 512, 1024, 2048, 4096, 8192, 16384, 32768, 65536]
        results = []
        
        base_text = "L'intelligence artificielle évolue rapidement. "
        
        for size in test_sizes:
            print(f"  🔄 Test {size} tokens...")
            
            # Générer le texte de test
            repetitions = max(1, size // len(base_text))
            test_content = base_text * repetitions
            
            # Monitoring des ressources
            process = psutil.Process()
            cpu_before = process.cpu_percent()
            memory_before = process.memory_info().rss / (1024 * 1024)  # MB
            
            start_time = time.time()
            gc_before = len(gc.get_objects())
            
            try:
                response = self.model.generate_response(
                    f"Fais un résumé structuré de ce texte: {test_content}", 
                    {}
                )
                
                end_time = time.time()
                processing_time = end_time - start_time
                
                # Mesures post-traitement
                cpu_after = process.cpu_percent()
                memory_after = process.memory_info().rss / (1024 * 1024)  # MB
                gc_after = len(gc.get_objects())
                
                # Calculer les métriques
                tokens_per_second = size / processing_time if processing_time > 0 else 0
                memory_efficiency = size / (memory_after - memory_before) if memory_after > memory_before else float('inf')
                
                result = {
                    "context_size": size,
                    "actual_tokens": len(test_content.split()),
                    "processing_time": processing_time,
                    "tokens_per_second": tokens_per_second,
                    "memory_before_mb": memory_before,
                    "memory_after_mb": memory_after,
                    "memory_delta_mb": memory_after - memory_before,
                    "memory_efficiency": memory_efficiency,
                    "cpu_usage": cpu_after,
                    "gc_objects_delta": gc_after - gc_before,
                    "response_length": len(response) if response else 0,
                    "success": True,
                    "quality_score": self._assess_response_quality(response, test_content)
                }
                
                results.append(result)
                print(f"    ✅ {processing_time:.2f}s, {tokens_per_second:.0f} tok/s, {memory_after - memory_before:.1f}MB")
                
                # Nettoyage mémoire
                gc.collect()
                
            except Exception as e:
                result = {
                    "context_size": size,
                    "processing_time": -1,
                    "success": False,
                    "error": str(e),
                    "memory_before_mb": memory_before
                }
                results.append(result)
                print(f"    ❌ Échec: {str(e)}")
                break
        
        # Analyser les résultats
        successful_results = [r for r in results if r["success"]]
        
        analysis = {
            "max_successful_size": max([r["context_size"] for r in successful_results]) if successful_results else 0,
            "optimal_size": self._find_optimal_context_size(successful_results),
            "performance_curve": successful_results,
            "bottleneck_analysis": self._analyze_bottlenecks(successful_results)
        }
        
        return analysis
    
    def _test_content_types(self) -> Dict[str, Any]:
        """Test avec différents types de contenu"""
        print("📝 Test de types de contenu différents...")
        
        content_types = {
            "code": {
                "content": "def fibonacci(n):\n    if n <= 1:\n        return n\n    return fibonacci(n-1) + fibonacci(n-2)\n\n" * 100,
                "description": "Code Python répétitif"
            },
            "natural_text": {
                "content": "L'intelligence artificielle est une technologie révolutionnaire qui transforme notre société. Elle permet d'automatiser des tâches complexes et d'améliorer notre productivité. " * 100,
                "description": "Texte naturel"
            },
            "structured_data": {
                "content": '{"name": "Jean", "age": 30, "skills": ["Python", "JavaScript", "React"]}\n' * 200,
                "description": "Données JSON structurées"
            },
            "mixed_content": {
                "content": "# Documentation\n\nVoici du code:\n```python\nprint('hello')\n```\n\nEt du texte explicatif.\n" * 50,
                "description": "Contenu mixte (markdown, code, texte)"
            }
        }
        
        results = {}
        
        for content_type, data in content_types.items():
            print(f"  🔍 Test {content_type}...")
            
            start_time = time.time()
            memory_before = psutil.Process().memory_info().rss / (1024 * 1024)
            
            try:
                response = self.model.generate_response(
                    f"Analyse ce contenu {data['description']}: {data['content']}", 
                    {}
                )
                
                end_time = time.time()
                memory_after = psutil.Process().memory_info().rss / (1024 * 1024)
                
                results[content_type] = {
                    "content_length": len(data["content"]),
                    "estimated_tokens": len(data["content"].split()),
                    "processing_time": end_time - start_time,
                    "memory_delta_mb": memory_after - memory_before,
                    "response_length": len(response) if response else 0,
                    "success": True,
                    "efficiency": len(data["content"]) / (end_time - start_time) if end_time > start_time else 0
                }
                
                print(f"    ✅ {end_time - start_time:.2f}s, {memory_after - memory_before:.1f}MB")
                
            except Exception as e:
                results[content_type] = {
                    "success": False,
                    "error": str(e)
                }
                print(f"    ❌ Erreur: {str(e)}")
        
        return results
    
    def _test_memory_efficiency(self) -> Dict[str, Any]:
        """Test d'efficacité mémoire avec monitoring détaillé"""
        print("💾 Test d'efficacité mémoire...")
        
        # Test avec contexte croissant
        memory_timeline = []
        context_accumulation = ""
        
        for i in range(10):
            # Ajouter du contenu au contexte
            new_content = f"Partie {i+1}: L'IA doit comprendre et retenir cette information importante. " * 50
            context_accumulation += new_content
            
            # Mesurer avant traitement
            memory_before = psutil.Process().memory_info().rss / (1024 * 1024)
            
            start_time = time.time()
            
            try:
                response = self.model.generate_response(
                    f"Résume tout le contexte accumulé: {context_accumulation}", 
                    {}
                )
                
                end_time = time.time()
                memory_after = psutil.Process().memory_info().rss / (1024 * 1024)
                
                memory_timeline.append({
                    "iteration": i + 1,
                    "context_size": len(context_accumulation),
                    "estimated_tokens": len(context_accumulation.split()),
                    "memory_before_mb": memory_before,
                    "memory_after_mb": memory_after,
                    "memory_delta_mb": memory_after - memory_before,
                    "processing_time": end_time - start_time,
                    "response_length": len(response) if response else 0
                })
                
                print(f"  Iteration {i+1}: {memory_after - memory_before:.1f}MB delta")
                
                # Forcer le garbage collection
                gc.collect()
                
            except Exception as e:
                memory_timeline.append({
                    "iteration": i + 1,
                    "error": str(e),
                    "context_size": len(context_accumulation)
                })
                break
        
        # Analyser les fuites mémoire potentielles
        successful_iterations = [m for m in memory_timeline if "error" not in m]
        
        if len(successful_iterations) > 3:
            memory_growth_rate = (
                successful_iterations[-1]["memory_after_mb"] - 
                successful_iterations[0]["memory_after_mb"]
            ) / len(successful_iterations)
        else:
            memory_growth_rate = 0
        
        return {
            "memory_timeline": memory_timeline,
            "memory_growth_rate_mb": memory_growth_rate,
            "memory_leak_detected": memory_growth_rate > 10,  # Plus de 10MB par itération
            "total_iterations": len(memory_timeline),
            "max_stable_context": self._find_max_stable_context(memory_timeline)
        }
    
    def _test_long_term_stability(self) -> Dict[str, Any]:
        """Test de stabilité sur de longues sessions"""
        print("🔄 Test de stabilité long-terme...")
        
        stability_results = []
        
        # Simuler une session longue avec différents types de requêtes
        test_scenarios = [
            "Bonjour, comment ça va ?",
            "Explique-moi les algorithmes de tri",
            "Génère du code Python pour un serveur web",
            "Quelle est la différence entre liste et dictionnaire ?",
            "Raconte-moi une blague",
            "Analyse ce code: def test(): return 'hello'",
            "Recherche sur internet les nouvelles en IA",
            "Résume un document technique complexe sur l'apprentissage automatique"
        ]
        
        # Répéter le cycle plusieurs fois
        for cycle in range(5):
            print(f"  🔄 Cycle {cycle + 1}/5...")
            
            cycle_start_time = time.time()
            cycle_memory_start = psutil.Process().memory_info().rss / (1024 * 1024)
            
            for i, scenario in enumerate(test_scenarios):
                try:
                    start_time = time.time()
                    response = self.model.generate_response(scenario, {})
                    end_time = time.time()
                    
                    stability_results.append({
                        "cycle": cycle + 1,
                        "scenario": i + 1,
                        "scenario_text": scenario[:50] + "...",
                        "processing_time": end_time - start_time,
                        "response_length": len(response) if response else 0,
                        "success": True
                    })
                    
                except Exception as e:
                    stability_results.append({
                        "cycle": cycle + 1,
                        "scenario": i + 1,
                        "error": str(e),
                        "success": False
                    })
            
            cycle_end_time = time.time()
            cycle_memory_end = psutil.Process().memory_info().rss / (1024 * 1024)
            
            print(f"    Cycle {cycle + 1}: {cycle_end_time - cycle_start_time:.1f}s, "
                  f"Δmem: {cycle_memory_end - cycle_memory_start:.1f}MB")
            
            # Pause entre cycles
            time.sleep(1)
        
        # Analyser la stabilité
        successful_tests = [r for r in stability_results if r["success"]]
        
        if successful_tests:
            processing_times = [r["processing_time"] for r in successful_tests]
            avg_time = sum(processing_times) / len(processing_times)
            time_variance = np.var(processing_times) if len(processing_times) > 1 else 0
            
            stability_score = 1.0 / (1.0 + time_variance)  # Score de stabilité
        else:
            avg_time = 0
            time_variance = 0
            stability_score = 0
        
        return {
            "total_tests": len(stability_results),
            "successful_tests": len(successful_tests),
            "success_rate": len(successful_tests) / len(stability_results) if stability_results else 0,
            "avg_processing_time": avg_time,
            "time_variance": time_variance,
            "stability_score": stability_score,
            "detailed_results": stability_results
        }
    
    def _test_content_types(self) -> Dict[str, Any]:
        """Test avec différents types de contenu pour identifier les goulots d'étranglement"""
        print("📋 Test de types de contenu spécialisés...")
        
        content_templates = {
            "repetitive_code": {
                "template": "def function_{i}():\n    return {i} * 2\n\n",
                "multiplier": 100,
                "description": "Code répétitif"
            },
            "diverse_text": {
                "template": "Chapitre {i}: L'intelligence artificielle dans le domaine numéro {i} révolutionne les méthodes traditionnelles. ",
                "multiplier": 50,
                "description": "Texte diversifié"
            },
            "json_data": {
                "template": '{{"id": {i}, "data": "information_{i}", "value": {i}}},\n',
                "multiplier": 200,
                "description": "Données JSON"
            },
            "mixed_markdown": {
                "template": "## Section {i}\n\n```python\nprint('code_{i}')\n```\n\nTexte explicatif {i}.\n\n",
                "multiplier": 30,
                "description": "Markdown mixte"
            }
        }
        
        results = {}
        
        for content_type, config in content_templates.items():
            print(f"  📄 Test {content_type}...")
            
            # Générer le contenu
            content = ""
            for i in range(config["multiplier"]):
                content += config["template"].format(i=i)
            
            # Test de performance
            start_time = time.time()
            memory_before = psutil.Process().memory_info().rss / (1024 * 1024)
            
            try:
                response = self.model.generate_response(
                    f"Analyse ce {config['description']}: {content}", 
                    {}
                )
                
                end_time = time.time()
                memory_after = psutil.Process().memory_info().rss / (1024 * 1024)
                
                results[content_type] = {
                    "content_length": len(content),
                    "estimated_tokens": len(content.split()),
                    "processing_time": end_time - start_time,
                    "tokens_per_second": len(content.split()) / (end_time - start_time) if end_time > start_time else 0,
                    "memory_delta_mb": memory_after - memory_before,
                    "response_length": len(response) if response else 0,
                    "compression_ratio": len(response) / len(content) if response and content else 0,
                    "success": True
                }
                
                print(f"    ✅ {end_time - start_time:.2f}s, compression: {len(response) / len(content):.2%}")
                
            except Exception as e:
                results[content_type] = {
                    "success": False,
                    "error": str(e),
                    "content_length": len(content)
                }
                print(f"    ❌ Erreur: {str(e)}")
        
        return results
    
    def _test_memory_efficiency(self) -> Dict[str, Any]:
        """Test approfondi de l'efficacité mémoire"""
        print("🧠 Test d'efficacité mémoire avancé...")
        
        # Test de charge mémoire avec monitoring continu
        memory_snapshots = []
        context_sizes = [1024, 2048, 4096, 8192]
        
        for size in context_sizes:
            # Créer un contexte de taille spécifique
            test_text = "Information importante numéro " + " ".join([str(i) for i in range(size)])
            
            # Prendre plusieurs snapshots pendant le traitement
            snapshots = []
            
            def memory_monitor():
                for _ in range(20):  # Monitor pendant 2 secondes
                    snapshots.append({
                        "timestamp": time.time(),
                        "memory_mb": psutil.Process().memory_info().rss / (1024 * 1024)
                    })
                    time.sleep(0.1)
            
            # Démarrer monitoring en parallèle
            import threading
            monitor_thread = threading.Thread(target=memory_monitor)
            
            start_time = time.time()
            monitor_thread.start()
            
            try:
                response = self.model.generate_response(f"Traite ce contexte: {test_text}", {})
                end_time = time.time()
                success = True
            except Exception as e:
                end_time = time.time()
                success = False
                response = None
            
            monitor_thread.join()
            
            memory_snapshots.append({
                "context_size": size,
                "success": success,
                "processing_time": end_time - start_time,
                "memory_timeline": snapshots,
                "peak_memory": max([s["memory_mb"] for s in snapshots]) if snapshots else 0,
                "memory_growth": snapshots[-1]["memory_mb"] - snapshots[0]["memory_mb"] if len(snapshots) > 1 else 0
            })
            
            print(f"    Context {size}: {'✅' if success else '❌'} "
                  f"Peak: {max([s['memory_mb'] for s in snapshots]) if snapshots else 0:.1f}MB")
        
        return {
            "memory_snapshots": memory_snapshots,
            "memory_leak_detected": self._detect_memory_leaks(memory_snapshots),
            "optimal_memory_usage": self._calculate_optimal_memory_usage(memory_snapshots)
        }
    
    def _test_long_term_stability(self) -> Dict[str, Any]:
        """Test de stabilité sur une longue période"""
        print("⏰ Test de stabilité long-terme...")
        
        # Simuler 100 interactions consécutives
        interactions = []
        base_queries = [
            "Salut",
            "Comment faire une boucle en Python?",
            "Génère du code HTML",
            "Explique les classes Python"
        ]
        
        for i in range(100):
            query = base_queries[i % len(base_queries)] + f" (itération {i+1})"
            
            start_time = time.time()
            memory_before = psutil.Process().memory_info().rss / (1024 * 1024)
            
            try:
                response = self.model.generate_response(query, {})
                end_time = time.time()
                memory_after = psutil.Process().memory_info().rss / (1024 * 1024)
                
                interactions.append({
                    "iteration": i + 1,
                    "processing_time": end_time - start_time,
                    "memory_mb": memory_after,
                    "memory_delta": memory_after - memory_before,
                    "success": True
                })
                
                if (i + 1) % 20 == 0:
                    print(f"    ✅ {i + 1}/100 interactions, mémoire: {memory_after:.1f}MB")
                
            except Exception as e:
                interactions.append({
                    "iteration": i + 1,
                    "error": str(e),
                    "success": False
                })
                print(f"    ❌ Échec à l'itération {i + 1}: {str(e)}")
        
        # Analyser la stabilité
        successful_interactions = [i for i in interactions if i["success"]]
        
        if successful_interactions:
            # Tendance de performance
            early_times = [i["processing_time"] for i in successful_interactions[:20]]
            late_times = [i["processing_time"] for i in successful_interactions[-20:]]
            
            performance_degradation = (
                (sum(late_times) / len(late_times)) - (sum(early_times) / len(early_times))
            ) / (sum(early_times) / len(early_times)) if early_times else 0
            
            # Tendance mémoire
            memory_values = [i["memory_mb"] for i in successful_interactions]
            memory_trend = (memory_values[-1] - memory_values[0]) / len(memory_values) if len(memory_values) > 1 else 0
        else:
            performance_degradation = 0
            memory_trend = 0
        
        return {
            "total_interactions": len(interactions),
            "successful_interactions": len(successful_interactions),
            "success_rate": len(successful_interactions) / len(interactions) if interactions else 0,
            "performance_degradation": performance_degradation,
            "memory_trend_mb_per_interaction": memory_trend,
            "stability_rating": self._calculate_stability_rating(interactions)
        }
    
    def _assess_response_quality(self, response: str, original_content: str) -> float:
        """Évalue la qualité de la réponse (0-1)"""
        if not response:
            return 0.0
        
        # Métriques simples de qualité
        length_ratio = len(response) / len(original_content) if original_content else 0
        
        # Score basé sur la longueur relative et la présence de contenu structuré
        quality_indicators = 0
        if 0.1 <= length_ratio <= 0.8:  # Bon ratio de compression
            quality_indicators += 0.3
        if len(response.split()) > 10:  # Réponse substantielle
            quality_indicators += 0.3
        if any(marker in response for marker in ["**", "*", "\n", ":"]):  # Formatage
            quality_indicators += 0.2
        if len(response.split('.')) > 2:  # Phrases multiples
            quality_indicators += 0.2
        
        return min(1.0, quality_indicators)
    
    def _find_optimal_context_size(self, results: List[Dict]) -> int:
        """Trouve la taille de contexte optimale basée sur le ratio performance/mémoire"""
        if not results:
            return 0
        
        # Calculer un score d'efficacité pour chaque taille
        efficiency_scores = []
        
        for result in results:
            if result["success"]:
                # Score basé sur tokens/seconde et efficacité mémoire
                speed_score = result["tokens_per_second"] / 1000  # Normaliser
                memory_score = 1.0 / (result["memory_delta_mb"] + 1)  # Inverser (moins = mieux)
                
                efficiency_score = (speed_score + memory_score) / 2
                efficiency_scores.append((result["context_size"], efficiency_score))
        
        if efficiency_scores:
            # Retourner la taille avec le meilleur score d'efficacité
            optimal = max(efficiency_scores, key=lambda x: x[1])
            return optimal[0]
        
        return 0
    
    def _analyze_bottlenecks(self, results: List[Dict]) -> Dict[str, Any]:
        """Analyse les goulots d'étranglement"""
        if not results:
            return {}
        
        # Identifier où les performances se dégradent
        bottlenecks = {
            "memory_bottleneck": None,
            "speed_bottleneck": None,
            "critical_size": None
        }
        
        # Détecter la dégradation de vitesse
        for i in range(1, len(results)):
            prev = results[i-1]
            curr = results[i]
            
            if prev["tokens_per_second"] > 0 and curr["tokens_per_second"] > 0:
                speed_degradation = (prev["tokens_per_second"] - curr["tokens_per_second"]) / prev["tokens_per_second"]
                
                if speed_degradation > 0.3 and not bottlenecks["speed_bottleneck"]:  # 30% de dégradation
                    bottlenecks["speed_bottleneck"] = curr["context_size"]
            
            # Détecter l'explosion mémoire
            if curr["memory_delta_mb"] > prev["memory_delta_mb"] * 2 and not bottlenecks["memory_bottleneck"]:
                bottlenecks["memory_bottleneck"] = curr["context_size"]
        
        return bottlenecks
    
    def _find_max_stable_context(self, memory_timeline: List[Dict]) -> int:
        """Trouve la taille de contexte stable maximale"""
        stable_iterations = [m for m in memory_timeline if m.get("success") and m.get("memory_delta_mb", 0) < 50]
        
        if stable_iterations:
            return max(m["estimated_tokens"] for m in stable_iterations)
        return 0
    
    def _detect_memory_leaks(self, snapshots: List[Dict]) -> bool:
        """Détecte les fuites mémoire potentielles"""
        successful_snapshots = [s for s in snapshots if s["success"]]
        
        if len(successful_snapshots) < 3:
            return False
        
        # Vérifier si la mémoire continue de croître
        memory_growth = successful_snapshots[-1]["peak_memory"] - successful_snapshots[0]["peak_memory"]
        return memory_growth > 100  # Plus de 100MB de croissance = fuite potentielle
    
    def _calculate_optimal_memory_usage(self, snapshots: List[Dict]) -> Dict[str, float]:
        """Calcule l'utilisation mémoire optimale"""
        successful_snapshots = [s for s in snapshots if s["success"]]
        
        if not successful_snapshots:
            return {}
        
        # Efficacité mémoire = tokens traités / MB utilisé
        efficiency_ratios = []
        for snapshot in successful_snapshots:
            if snapshot["memory_growth"] > 0:
                efficiency = snapshot["context_size"] / snapshot["memory_growth"]
                efficiency_ratios.append(efficiency)
        
        return {
            "avg_efficiency": sum(efficiency_ratios) / len(efficiency_ratios) if efficiency_ratios else 0,
            "best_efficiency": max(efficiency_ratios) if efficiency_ratios else 0,
            "recommended_chunk_size": self._recommend_chunk_size(successful_snapshots)
        }
    
    def _recommend_chunk_size(self, snapshots: List[Dict]) -> int:
        """Recommande une taille de chunk optimale"""
        # Trouver le sweet spot entre performance et mémoire
        if not snapshots:
            return 2048  # Valeur par défaut
        
        # Chercher la taille où le ratio performance/mémoire est optimal
        best_ratio = 0
        best_size = 2048
        
        for snapshot in snapshots:
            if snapshot["memory_growth"] > 0 and snapshot["processing_time"] > 0:
                ratio = snapshot["context_size"] / (snapshot["memory_growth"] * snapshot["processing_time"])
                if ratio > best_ratio:
                    best_ratio = ratio
                    best_size = snapshot["context_size"]
        
        return best_size
    
    def _calculate_stability_rating(self, interactions: List[Dict]) -> str:
        """Calcule une note de stabilité"""
        if not interactions:
            return "Unknown"
        
        success_rate = len([i for i in interactions if i["success"]]) / len(interactions)
        
        if success_rate >= 0.95:
            return "Excellent"
        elif success_rate >= 0.85:
            return "Good"
        elif success_rate >= 0.70:
            return "Fair"
        else:
            return "Poor"
    
    def _generate_context_recommendations(self) -> Dict[str, Any]:
        """Génère des recommandations spécifiques au contexte"""
        recommendations = {
            "immediate_actions": [],
            "optimization_techniques": [],
            "implementation_priority": []
        }
        
        # Analyser les résultats pour générer des recommandations
        scale_test = self.results.get("scale_test", {})
        memory_test = self.results.get("memory_performance", {})
        
        # Recommandations basées sur la taille maximale
        max_size = scale_test.get("max_successful_size", 0)
        if max_size < 4096:
            recommendations["immediate_actions"].append(
                f"Contexte limité à {max_size} tokens - Implémenter RAG prioritaire"
            )
        elif max_size < 8192:
            recommendations["immediate_actions"].append(
                "Contexte modéré - Optimiser avec chunking intelligent"
            )
        
        # Recommandations basées sur la mémoire
        if memory_test.get("memory_leak_detected"):
            recommendations["immediate_actions"].append(
                "Fuite mémoire détectée - Implémenter garbage collection optimisé"
            )
        
        # Techniques d'optimisation recommandées
        recommendations["optimization_techniques"] = [
            "RAG avec FAISS pour recherche sémantique",
            "Context sliding window avec résumés",
            "Chunking adaptatif basé sur la sémantique",
            "Cache des embeddings pour réutilisation",
            "Compression de contexte avec modèles dédiés"
        ]
        
        # Priorités d'implémentation
        recommendations["implementation_priority"] = [
            {"technique": "RAG Pipeline", "priority": 1, "impact": "High", "effort": "Medium"},
            {"technique": "Context Chunking", "priority": 2, "impact": "High", "effort": "Low"},
            {"technique": "Memory Optimization", "priority": 3, "impact": "Medium", "effort": "Low"},
            {"technique": "FlashAttention", "priority": 4, "impact": "High", "effort": "High"},
            {"technique": "Model Quantization", "priority": 5, "impact": "Medium", "effort": "Medium"}
        ]
        
        return recommendations
    
    def _save_benchmark_results(self):
        """Sauvegarde les résultats détaillés"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Sauvegarde JSON détaillée
        report_path = f"context_benchmark_{timestamp}.json"
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False, default=str)
        
        print(f"📄 Benchmark sauvegardé: {report_path}")
    
    def _generate_performance_plots(self):
        """Génère des graphiques de performance"""
        try:
            scale_test = self.results.get("scale_test", {})
            performance_curve = scale_test.get("performance_curve", [])
            
            if not performance_curve:
                print("⚠️ Pas de données pour les graphiques")
                return
            
            # Créer les graphiques
            fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 10))
            
            sizes = [r["context_size"] for r in performance_curve]
            times = [r["processing_time"] for r in performance_curve]
            tokens_per_sec = [r["tokens_per_second"] for r in performance_curve]
            memory_deltas = [r.get("memory_delta_mb", 0) for r in performance_curve]
            
            # Graphique 1: Temps de traitement vs taille contexte
            ax1.plot(sizes, times, 'b-o', linewidth=2, markersize=6)
            ax1.set_xlabel('Taille du Contexte (tokens)')
            ax1.set_ylabel('Temps de Traitement (s)')
            ax1.set_title('Performance vs Taille du Contexte')
            ax1.grid(True, alpha=0.3)
            
            # Graphique 2: Throughput
            ax2.plot(sizes, tokens_per_sec, 'g-o', linewidth=2, markersize=6)
            ax2.set_xlabel('Taille du Contexte (tokens)')
            ax2.set_ylabel('Tokens/Seconde')
            ax2.set_title('Throughput du Modèle')
            ax2.grid(True, alpha=0.3)
            
            # Graphique 3: Utilisation mémoire
            ax3.plot(sizes, memory_deltas, 'r-o', linewidth=2, markersize=6)
            ax3.set_xlabel('Taille du Contexte (tokens)')
            ax3.set_ylabel('Delta Mémoire (MB)')
            ax3.set_title('Consommation Mémoire')
            ax3.grid(True, alpha=0.3)
            
            # Graphique 4: Efficacité (tokens/s par MB)
            efficiency = [t/m if m > 0 else 0 for t, m in zip(tokens_per_sec, memory_deltas)]
            ax4.plot(sizes, efficiency, 'm-o', linewidth=2, markersize=6)
            ax4.set_xlabel('Taille du Contexte (tokens)')
            ax4.set_ylabel('Efficacité (tokens/s/MB)')
            ax4.set_title('Efficacité Globale')
            ax4.grid(True, alpha=0.3)
            
            plt.tight_layout()
            
            # Sauvegarder
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            plot_path = f"context_performance_{timestamp}.png"
            plt.savefig(plot_path, dpi=300, bbox_inches='tight')
            print(f"📊 Graphiques sauvegardés: {plot_path}")
            
        except ImportError:
            print("⚠️ matplotlib non disponible - pas de graphiques générés")
        except Exception as e:
            print(f"❌ Erreur génération graphiques: {str(e)}")

def main():
    """Point d'entrée principal du benchmark"""
    benchmark = ContextBenchmark()
    results = benchmark.run_comprehensive_benchmark()
    
    # Affichage du résumé
    print("\n" + "=" * 60)
    print("📊 RÉSUMÉ DU BENCHMARK CONTEXTE")
    print("=" * 60)
    
    # Résultats de montée en charge
    scale_test = results.get("scale_test", {})
    max_size = scale_test.get("max_successful_size", 0)
    optimal_size = scale_test.get("optimal_size", 0)
    
    print(f"🎯 Taille maximale testée avec succès: {max_size:,} tokens")
    print(f"🏆 Taille optimale recommandée: {optimal_size:,} tokens")
    
    # Performance par type de contenu
    content_test = results.get("content_type_test", {})
    if content_test:
        print(f"\n📋 Performance par type de contenu:")
        for content_type, data in content_test.items():
            if data.get("success"):
                print(f"   {content_type}: {data['tokens_per_second']:.0f} tok/s")
    
    # Stabilité
    stability = results.get("stability_test", {})
    success_rate = stability.get("success_rate", 0)
    stability_rating = stability.get("stability_rating", "Unknown")
    
    print(f"\n🔄 Stabilité: {success_rate:.1%} succès, Note: {stability_rating}")
    
    # Recommandations
    recs = results.get("recommendations", {})
    immediate = recs.get("immediate_actions", [])
    if immediate:
        print(f"\n🚨 Actions Immédiates Recommandées:")
        for i, action in enumerate(immediate, 1):
            print(f"   {i}. {action}")
    
    return results

if __name__ == "__main__":
    main()
