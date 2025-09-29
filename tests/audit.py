#!/usr/bin/env python3
"""
🔍 Script d'Audit Automatique - My_AI Project
Analyse complète des performances, mémoire, et optimisations possibles
"""

import os
import sys
import time
import json
import psutil
import tracemalloc
from typing import Dict, Any, List, Optional
from pathlib import Path
from datetime import datetime
import hashlib

# Ajout du path pour imports locaux
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.ai_engine import AIEngine
from models.custom_ai_model import CustomAIModel
from models.conversation_memory import ConversationMemory
from utils.logger import setup_logger

class AIAuditor:
    """Auditeur complet pour le projet My_AI"""
    
    def __init__(self):
        self.logger = setup_logger("AIAuditor")
        self.audit_results = {}
        self.start_time = time.time()
        
    def run_full_audit(self) -> Dict[str, Any]:
        """Lance un audit complet du système"""
        print("🔍 Démarrage de l'audit automatique My_AI...")
        print("=" * 60)
        
        # 1. Audit de l'architecture
        self.audit_results["architecture"] = self._audit_architecture()
        
        # 2. Audit des performances
        self.audit_results["performance"] = self._audit_performance()
        
        # 3. Audit de la mémoire
        self.audit_results["memory"] = self._audit_memory_usage()
        
        # 4. Audit du contexte
        self.audit_results["context"] = self._audit_context_window()
        
        # 5. Audit des dépendances
        self.audit_results["dependencies"] = self._audit_dependencies()
        
        # 6. Recommandations d'optimisation
        self.audit_results["recommendations"] = self._generate_recommendations()
        
        # 7. Sauvegarde du rapport
        self._save_audit_report()
        
        return self.audit_results
    
    def _audit_architecture(self) -> Dict[str, Any]:
        """Audit de l'architecture du projet"""
        print("🏗️ Audit de l'architecture...")
        
        project_root = Path(__file__).parent
        
        # Analyser la structure des dossiers
        modules = {
            "core": list((project_root / "core").glob("*.py")) if (project_root / "core").exists() else [],
            "models": list((project_root / "models").glob("*.py")) if (project_root / "models").exists() else [],
            "processors": list((project_root / "processors").glob("*.py")) if (project_root / "processors").exists() else [],
            "interfaces": list((project_root / "interfaces").glob("*.py")) if (project_root / "interfaces").exists() else [],
            "utils": list((project_root / "utils").glob("*.py")) if (project_root / "utils").exists() else [],
            "tests": list((project_root / "tests").glob("*.py")) if (project_root / "tests").exists() else []
        }
        
        # Calculer les métriques de code
        total_lines = 0
        module_stats = {}
        
        for module_name, files in modules.items():
            module_lines = 0
            for file_path in files:
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        lines = len(f.readlines())
                        module_lines += lines
                        total_lines += lines
                except:
                    pass
            module_stats[module_name] = {
                "files": len(files),
                "lines": module_lines
            }
        
        return {
            "total_modules": len([m for m in modules.values() if m]),
            "total_files": sum(len(files) for files in modules.values()),
            "total_lines": total_lines,
            "module_breakdown": module_stats,
            "modularity_score": self._calculate_modularity_score(modules)
        }
    
    def _audit_performance(self) -> Dict[str, Any]:
        """Audit des performances du modèle"""
        print("⚡ Audit des performances...")
        
        results = {
            "response_times": [],
            "throughput": 0,
            "token_processing_speed": 0,
            "latency_stats": {}
        }
        
        try:
            # Initialiser le modèle pour les tests
            memory = ConversationMemory()
            model = CustomAIModel(conversation_memory=memory)
            
            # Tests de latence avec différents types de requêtes
            test_queries = [
                "Bonjour",  # Simple
                "Explique-moi les listes Python en détail",  # Moyen
                "Génère un code complet pour un serveur web Flask avec authentification, base de données SQLite, et API REST complète"  # Complexe
            ]
            
            for i, query in enumerate(test_queries):
                start_time = time.time()
                
                # Mesurer le temps de réponse
                try:
                    response = model.generate_response(query, {})
                    end_time = time.time()
                    
                    response_time = end_time - start_time
                    results["response_times"].append({
                        "query_type": ["simple", "medium", "complex"][i],
                        "query_length": len(query),
                        "response_length": len(response) if response else 0,
                        "response_time": response_time
                    })
                    
                    print(f"  ✓ Test {i+1}: {response_time:.3f}s")
                    
                except Exception as e:
                    print(f"  ❌ Erreur test {i+1}: {str(e)}")
            
            # Calculer la vitesse moyenne
            if results["response_times"]:
                avg_time = sum(r["response_time"] for r in results["response_times"]) / len(results["response_times"])
                avg_tokens = sum(r["response_length"] for r in results["response_times"]) / len(results["response_times"])
                results["throughput"] = avg_tokens / avg_time if avg_time > 0 else 0
                results["latency_stats"] = {
                    "avg_response_time": avg_time,
                    "min_response_time": min(r["response_time"] for r in results["response_times"]),
                    "max_response_time": max(r["response_time"] for r in results["response_times"])
                }
                
        except Exception as e:
            print(f"❌ Erreur lors de l'audit de performance: {str(e)}")
            results["error"] = str(e)
        
        return results
    
    def _audit_memory_usage(self) -> Dict[str, Any]:
        """Audit de l'utilisation mémoire"""
        print("💾 Audit de la mémoire...")
        
        # Mémoire système
        memory_info = psutil.virtual_memory()
        
        # Démarrer le monitoring de la mémoire Python
        tracemalloc.start()
        
        try:
            # Initialiser les composants et mesurer
            memory = ConversationMemory()
            model = CustomAIModel(conversation_memory=memory)
            
            # Snapshot après initialisation
            snapshot = tracemalloc.take_snapshot()
            top_stats = snapshot.statistics('lineno')
            
            # Test de consommation mémoire avec traitement de document
            test_content = "Lorem ipsum " * 1000  # ~11KB de texte
            for i in range(10):
                model.generate_response(f"Analyse ce texte: {test_content}", {})
            
            # Snapshot final
            final_snapshot = tracemalloc.take_snapshot()
            
        except Exception as e:
            print(f"❌ Erreur monitoring mémoire: {str(e)}")
            return {"error": str(e)}
        finally:
            tracemalloc.stop()
        
        return {
            "system_memory": {
                "total_gb": round(memory_info.total / (1024**3), 2),
                "available_gb": round(memory_info.available / (1024**3), 2),
                "used_percent": memory_info.percent
            },
            "python_memory": {
                "peak_mb": round(tracemalloc.get_traced_memory()[1] / (1024**2), 2),
                "current_mb": round(tracemalloc.get_traced_memory()[0] / (1024**2), 2)
            },
            "top_memory_lines": len(top_stats)
        }
    
    def _audit_context_window(self) -> Dict[str, Any]:
        """Audit de la fenêtre de contexte et gestion des tokens"""
        print("📏 Audit de la fenêtre de contexte...")
        
        try:
            # Charger la configuration
            import yaml
            config_path = Path(__file__).parent / "config.yaml"
            if config_path.exists():
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f)
                    max_tokens = config.get("ai", {}).get("max_tokens", 4096)
            else:
                max_tokens = 4096
            
            # Test avec différentes tailles de contexte
            context_tests = []
            test_sizes = [100, 500, 1000, 2000, 4000, 8000]
            
            model = CustomAIModel()
            
            for size in test_sizes:
                test_text = "Token " * size  # Approximation grossière
                start_time = time.time()
                
                try:
                    response = model.generate_response(f"Résume ce texte: {test_text}", {})
                    end_time = time.time()
                    
                    context_tests.append({
                        "input_size": size,
                        "estimated_tokens": size,
                        "processing_time": end_time - start_time,
                        "success": True,
                        "response_length": len(response) if response else 0
                    })
                    
                    print(f"  ✓ Test {size} tokens: {end_time - start_time:.3f}s")
                    
                except Exception as e:
                    context_tests.append({
                        "input_size": size,
                        "estimated_tokens": size,
                        "processing_time": -1,
                        "success": False,
                        "error": str(e)
                    })
                    print(f"  ❌ Test {size} tokens: {str(e)}")
            
            return {
                "current_max_tokens": max_tokens,
                "context_tests": context_tests,
                "effective_limit": self._find_effective_limit(context_tests),
                "optimization_potential": self._assess_context_optimization(context_tests)
            }
            
        except Exception as e:
            return {"error": str(e)}
    
    def _audit_dependencies(self) -> Dict[str, Any]:
        """Audit des dépendances et compatibilité"""
        print("📦 Audit des dépendances...")
        
        try:
            requirements_path = Path(__file__).parent / "requirements.txt"
            installed_packages = {}
            missing_packages = []
            
            if requirements_path.exists():
                with open(requirements_path, 'r', encoding='utf-8') as f:
                    requirements = f.readlines()
                
                for line in requirements:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        package = line.split('>=')[0].split('==')[0].split('[')[0]
                        try:
                            import importlib
                            mod = importlib.import_module(package.replace('-', '_'))
                            version = getattr(mod, '__version__', 'Unknown')
                            installed_packages[package] = version
                        except ImportError:
                            missing_packages.append(package)
            
            return {
                "total_requirements": len(installed_packages) + len(missing_packages),
                "installed_packages": installed_packages,
                "missing_packages": missing_packages,
                "installation_health": len(missing_packages) == 0
            }
            
        except Exception as e:
            return {"error": str(e)}
    
    def _calculate_modularity_score(self, modules: Dict[str, List]) -> float:
        """Calcule un score de modularité (0-1)"""
        total_modules = len([m for m in modules.values() if m])
        if total_modules == 0:
            return 0.0
        
        # Score basé sur la distribution équilibrée des modules
        expected_modules = ["core", "models", "processors", "interfaces", "utils", "tests"]
        present_modules = len([name for name in expected_modules if modules.get(name)])
        
        return present_modules / len(expected_modules)
    
    def _find_effective_limit(self, context_tests: List[Dict]) -> int:
        """Trouve la limite effective de tokens"""
        successful_tests = [t for t in context_tests if t["success"]]
        if not successful_tests:
            return 0
        
        return max(t["estimated_tokens"] for t in successful_tests)
    
    def _assess_context_optimization(self, context_tests: List[Dict]) -> Dict[str, Any]:
        """Évalue le potentiel d'optimisation du contexte"""
        successful_tests = [t for t in context_tests if t["success"]]
        
        if len(successful_tests) < 2:
            return {"potential": "low", "reason": "Insufficient test data"}
        
        # Analyser la dégradation des performances
        performance_degradation = []
        for i in range(1, len(successful_tests)):
            prev = successful_tests[i-1]
            curr = successful_tests[i]
            
            if prev["processing_time"] > 0:
                degradation = (curr["processing_time"] - prev["processing_time"]) / prev["processing_time"]
                performance_degradation.append(degradation)
        
        avg_degradation = sum(performance_degradation) / len(performance_degradation) if performance_degradation else 0
        
        # Déterminer le potentiel d'optimisation
        if avg_degradation > 0.5:  # 50% de dégradation
            potential = "high"
            reason = "Performance se dégrade significativement avec la taille du contexte"
        elif avg_degradation > 0.2:  # 20% de dégradation
            potential = "medium"
            reason = "Dégradation modérée, optimisations recommandées"
        else:
            potential = "low"
            reason = "Performance stable, optimisations mineures possibles"
        
        return {
            "potential": potential,
            "reason": reason,
            "avg_degradation": avg_degradation,
            "recommended_techniques": self._recommend_optimization_techniques(potential)
        }
    
    def _recommend_optimization_techniques(self, potential: str) -> List[str]:
        """Recommande des techniques d'optimisation basées sur le potentiel"""
        base_techniques = ["RAG (Retrieval-Augmented Generation)", "Context Chunking"]
        
        if potential == "high":
            return base_techniques + [
                "FlashAttention pour l'efficacité mémoire",
                "Gradient Checkpointing",
                "Model Quantization (8-bit/4-bit)",
                "Context Compression avec résumés"
            ]
        elif potential == "medium":
            return base_techniques + [
                "Attention Sliding Window",
                "Context Caching",
                "Memory Efficient Attention"
            ]
        else:
            return base_techniques
    
    def _generate_recommendations(self) -> Dict[str, List[str]]:
        """Génère des recommandations d'amélioration"""
        recommendations = {
            "immediate": [],
            "short_term": [],
            "long_term": []
        }
        
        # Recommandations immédiates
        if self.audit_results.get("dependencies", {}).get("missing_packages"):
            recommendations["immediate"].append("Installer les dépendances manquantes")
        
        # Recommandations court terme
        context_audit = self.audit_results.get("context", {})
        if context_audit.get("optimization_potential", {}).get("potential") in ["medium", "high"]:
            recommendations["short_term"].extend([
                "Implémenter RAG pour optimiser le contexte",
                "Ajouter un système de chunking intelligent",
                "Optimiser la gestion mémoire"
            ])
        
        # Recommandations long terme
        recommendations["long_term"].extend([
            "Implémenter FlashAttention pour de très longs contextes",
            "Ajouter un système de fine-tuning automatique",
            "Intégrer des métriques de qualité automatiques"
        ])
        
        return recommendations
    
    def _save_audit_report(self):
        """Sauvegarde le rapport d'audit"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = f"audit_report_{timestamp}.json"
        
        # Ajouter métadonnées
        self.audit_results["metadata"] = {
            "timestamp": timestamp,
            "audit_duration": time.time() - self.start_time,
            "system_info": {
                "platform": sys.platform,
                "python_version": sys.version,
                "cpu_count": psutil.cpu_count(),
                "total_memory_gb": round(psutil.virtual_memory().total / (1024**3), 2)
            }
        }
        
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(self.audit_results, f, indent=2, ensure_ascii=False)
        
        print(f"\n📄 Rapport d'audit sauvegardé: {report_path}")

def benchmark_context_window(max_size: int = 16384) -> Dict[str, Any]:
    """Benchmark spécifique de la fenêtre de contexte"""
    print(f"🎯 Benchmark de la fenêtre de contexte (max: {max_size} tokens)")
    
    results = {
        "max_successful_size": 0,
        "performance_curve": [],
        "memory_usage": [],
        "failure_point": None
    }
    
    try:
        model = CustomAIModel()
        
        # Tests progressifs de taille de contexte
        sizes = [512, 1024, 2048, 4096, 8192, 16384, 32768]
        sizes = [s for s in sizes if s <= max_size]
        
        for size in sizes:
            print(f"  Testing {size} tokens...")
            
            # Générer un texte de test de taille approximative
            test_text = "Le contexte long est important pour l'IA. " * (size // 8)
            
            # Monitoring mémoire
            process = psutil.Process()
            memory_before = process.memory_info().rss / (1024 * 1024)  # MB
            
            start_time = time.time()
            
            try:
                response = model.generate_response(f"Analyse ce long texte: {test_text}", {})
                end_time = time.time()
                
                memory_after = process.memory_info().rss / (1024 * 1024)  # MB
                
                processing_time = end_time - start_time
                memory_delta = memory_after - memory_before
                
                results["performance_curve"].append({
                    "context_size": size,
                    "processing_time": processing_time,
                    "tokens_per_second": size / processing_time if processing_time > 0 else 0,
                    "success": True
                })
                
                results["memory_usage"].append({
                    "context_size": size,
                    "memory_delta_mb": memory_delta,
                    "memory_after_mb": memory_after
                })
                
                results["max_successful_size"] = size
                print(f"    ✓ {processing_time:.2f}s, {memory_delta:.1f}MB delta")
                
            except Exception as e:
                results["failure_point"] = {
                    "size": size,
                    "error": str(e)
                }
                print(f"    ❌ Échec à {size} tokens: {str(e)}")
                break
                
    except Exception as e:
        results["error"] = str(e)
    
    return results

def main():
    """Point d'entrée principal"""
    print("🤖 My_AI - Audit Automatique v1.0")
    print("=" * 50)
    
    # Audit complet
    auditor = AIAuditor()
    audit_results = auditor.run_full_audit()
    
    # Benchmark spécifique du contexte
    print("\n" + "=" * 50)
    context_benchmark = benchmark_context_window(32768)
    
    # Résumé final
    print("\n" + "=" * 50)
    print("📊 RÉSUMÉ DE L'AUDIT")
    print("=" * 50)
    
    # Architecture
    arch = audit_results.get("architecture", {})
    print(f"🏗️ Architecture: {arch.get('total_files', 0)} fichiers, {arch.get('total_lines', 0)} lignes")
    print(f"   Modularité: {arch.get('modularity_score', 0):.1%}")
    
    # Performance
    perf = audit_results.get("performance", {})
    if perf.get("latency_stats"):
        avg_time = perf["latency_stats"].get("avg_response_time", 0)
        throughput = perf.get("throughput", 0)
        print(f"⚡ Performance: {avg_time:.3f}s moyenne, {throughput:.0f} tokens/s")
    
    # Mémoire
    mem = audit_results.get("memory", {})
    if mem.get("python_memory"):
        peak_mb = mem["python_memory"].get("peak_mb", 0)
        print(f"💾 Mémoire: {peak_mb:.1f}MB pic d'utilisation")
    
    # Contexte
    context_max = context_benchmark.get("max_successful_size", 0)
    print(f"📏 Contexte: Limite effective {context_max} tokens")
    
    # Recommandations prioritaires
    recs = audit_results.get("recommendations", {})
    immediate = recs.get("immediate", [])
    if immediate:
        print(f"🚨 Actions immédiates: {len(immediate)} recommandations")
        for i, rec in enumerate(immediate, 1):
            print(f"   {i}. {rec}")
    
    print(f"\n✅ Audit terminé. Rapport détaillé dans le fichier JSON généré.")
    
    return audit_results, context_benchmark

if __name__ == "__main__":
    main()
