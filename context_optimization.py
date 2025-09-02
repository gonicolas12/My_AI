#!/usr/bin/env python3
"""
⚡ Module d'Optimisation Avancée - My_AI Project
Techniques d'optimisation : FlashAttention, Memory Efficient Attention, Context Compression
"""

import os
import sys
import time
from datetime import datetime
import math
import numpy as np
from typing import Dict, Any, List, Optional, Tuple, Union
from dataclasses import dataclass
from abc import ABC, abstractmethod

# Ajout du path pour imports locaux
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Imports conditionnels
try:
    import torch
    import torch.nn as nn
    import torch.nn.functional as F
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    print("⚠️ PyTorch non disponible - utilisation des optimisations CPU")

try:
    from transformers import AutoTokenizer, AutoModel
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False
    print("⚠️ Transformers non disponible - utilisation tokenization simple")

from models.custom_ai_model import CustomAIModel
from utils.logger import setup_logger

@dataclass
class AttentionConfig:
    """Configuration pour les optimisations d'attention"""
    max_seq_length: int = 131072
    chunk_size: int = 4096
    overlap_size: int = 64
    attention_type: str = "efficient"  # "efficient", "sliding", "sparse"
    memory_efficient: bool = True
    use_gradient_checkpointing: bool = False

class MemoryEfficientAttention:
    """Implémentation d'attention efficace en mémoire"""
    
    def __init__(self, config: AttentionConfig):
        self.config = config
        self.logger = setup_logger("MemoryEfficientAttention")
        
    def process_long_sequence(self, sequence: str, query: str) -> str:
        """Traite une séquence longue avec attention efficace"""
        # 1. Chunking intelligent
        chunks = self._chunk_sequence_intelligently(sequence)
        
        # 2. Attention sélective sur les chunks
        relevant_chunks = self._select_relevant_chunks(chunks, query)
        
        # 3. Reconstruction du contexte optimisé
        optimized_context = self._reconstruct_optimized_context(relevant_chunks, query)
        
        return optimized_context
    
    def _chunk_sequence_intelligently(self, sequence: str) -> List[Dict[str, Any]]:
        """Découpe la séquence en chunks avec métadonnées"""
        chunks = []
        chunk_size = self.config.chunk_size
        overlap_size = self.config.overlap_size
        
        # Tokenization simple ou avancée
        if TRANSFORMERS_AVAILABLE:
            tokens = self._tokenize_with_transformers(sequence)
        else:
            tokens = sequence.split()
        
        # Création des chunks avec chevauchement
        for i in range(0, len(tokens), chunk_size - overlap_size):
            chunk_tokens = tokens[i:i + chunk_size]
            chunk_text = ' '.join(chunk_tokens) if isinstance(tokens[0], str) else ' '.join([str(t) for t in chunk_tokens])
            
            chunk_info = {
                "id": f"chunk_{i // (chunk_size - overlap_size)}",
                "content": chunk_text,
                "start_token": i,
                "end_token": min(i + chunk_size, len(tokens)),
                "token_count": len(chunk_tokens),
                "overlap_with_next": overlap_size if i + chunk_size < len(tokens) else 0
            }
            
            chunks.append(chunk_info)
        
        self.logger.info(f"Séquence divisée en {len(chunks)} chunks")
        return chunks
    
    def _select_relevant_chunks(self, chunks: List[Dict[str, Any]], query: str) -> List[Dict[str, Any]]:
        """Sélectionne les chunks les plus pertinents pour la requête"""
        # Scoring simple basé sur la correspondance de mots-clés
        query_words = set(query.lower().split())
        
        scored_chunks = []
        for chunk in chunks:
            chunk_words = set(chunk["content"].lower().split())
            
            # Score de correspondance
            intersection = query_words.intersection(chunk_words)
            relevance_score = len(intersection) / len(query_words) if query_words else 0
            
            # Score de position (premiers et derniers chunks souvent importants)
            position_score = 1.0 / (abs(chunk["start_token"] - 0) / 1000 + 1)
            
            # Score combiné
            combined_score = relevance_score * 0.8 + position_score * 0.2
            
            scored_chunks.append({
                **chunk,
                "relevance_score": combined_score
            })
        
        # Trier par pertinence et prendre les meilleurs
        scored_chunks.sort(key=lambda x: x["relevance_score"], reverse=True)
        
        # Sélectionner adaptatif : plus la requête est spécifique, moins de chunks
        num_chunks_to_select = max(3, min(8, len(chunks) // 3))
        selected = scored_chunks[:num_chunks_to_select]
        
        self.logger.info(f"{num_chunks_to_select} chunks sélectionnés sur {len(chunks)}")
        return selected
    
    def _reconstruct_optimized_context(self, chunks: List[Dict[str, Any]], query: str) -> str:
        """Reconstruit un contexte optimisé à partir des chunks sélectionnés"""
        if not chunks:
            return ""
        
        # Trier les chunks par position pour maintenir l'ordre logique
        chunks_by_position = sorted(chunks, key=lambda x: x["start_token"])
        
        # Construire le contexte avec des transitions fluides
        context_parts = []
        for i, chunk in enumerate(chunks_by_position):
            relevance = chunk["relevance_score"]
            
            # Ajouter une indication de pertinence subtile
            if relevance > 0.5:
                prefix = f"[Extrait pertinent {i+1}] "
            else:
                prefix = f"[Contexte {i+1}] "
            
            context_parts.append(prefix + chunk["content"])
        
        # Jointure avec séparateurs clairs
        optimized_context = "\n\n---\n\n".join(context_parts)
        
        # Ajouter un résumé si trop de chunks
        if len(chunks_by_position) > 5:
            summary = f"[Résumé: {len(chunks_by_position)} sections analysées pour répondre à: {query}]\n\n"
            optimized_context = summary + optimized_context
        
        return optimized_context
    
    def _tokenize_with_transformers(self, text: str) -> List[str]:
        """Tokenization avancée avec transformers"""
        try:
            tokenizer = AutoTokenizer.from_pretrained("bert-base-uncased")
            tokens = tokenizer.tokenize(text)
            return tokens
        except:
            # Fallback sur tokenization simple
            return text.split()

class ContextCompressor:
    """Compresseur de contexte pour optimiser la fenêtre"""
    
    def __init__(self, compression_ratio: float = 0.3):
        self.compression_ratio = compression_ratio
        self.logger = setup_logger("ContextCompressor")
    
    def compress_context(self, context: str, target_length: Optional[int] = None) -> str:
        """Compresse intelligemment le contexte"""
        if target_length is None:
            target_length = int(len(context) * self.compression_ratio)
        
        # Différentes stratégies de compression
        if len(context) <= target_length:
            return context
        
        # 1. Compression par extraction de phrases clés
        key_sentences = self._extract_key_sentences(context, target_length)
        
        # 2. Si encore trop long, compression par résumé
        if len(key_sentences) > target_length:
            compressed = self._summarize_content(key_sentences, target_length)
        else:
            compressed = key_sentences
        
        self.logger.info(f"Contexte compressé: {len(context)} -> {len(compressed)} chars")
        return compressed
    
    def _extract_key_sentences(self, text: str, target_length: int) -> str:
        """Extrait les phrases les plus importantes"""
        sentences = self._split_into_sentences(text)
        
        if not sentences:
            return text[:target_length]
        
        # Scorer chaque phrase
        scored_sentences = []
        for sentence in sentences:
            score = self._score_sentence_importance(sentence, text)
            scored_sentences.append((sentence, score))
        
        # Trier par importance
        scored_sentences.sort(key=lambda x: x[1], reverse=True)
        
        # Sélectionner les phrases jusqu'à atteindre la longueur cible
        selected_sentences = []
        current_length = 0
        
        for sentence, score in scored_sentences:
            if current_length + len(sentence) <= target_length:
                selected_sentences.append(sentence)
                current_length += len(sentence)
            else:
                break
        
        # Réorganiser dans l'ordre original
        original_order_sentences = []
        for sentence in sentences:
            if sentence in selected_sentences:
                original_order_sentences.append(sentence)
        
        return ' '.join(original_order_sentences)
    
    def _split_into_sentences(self, text: str) -> List[str]:
        """Divise le texte en phrases"""
        import re
        # Pattern amélioré pour détecter les fins de phrases
        sentence_pattern = r'(?<=[.!?])\s+'
        sentences = re.split(sentence_pattern, text)
        return [s.strip() for s in sentences if s.strip()]
    
    def _score_sentence_importance(self, sentence: str, full_text: str) -> float:
        """Score l'importance d'une phrase dans le contexte"""
        score = 0.0
        
        # 1. Longueur de la phrase (phrases moyennes préférées)
        length_score = 1.0 - abs(len(sentence.split()) - 15) / 30
        score += length_score * 0.2
        
        # 2. Position dans le texte (début et fin importants)
        position = full_text.find(sentence) / len(full_text)
        position_score = 1.0 - abs(position - 0.5) * 2  # Score max au milieu
        if position < 0.2 or position > 0.8:  # Bonus pour début/fin
            position_score += 0.3
        score += position_score * 0.3
        
        # 3. Richesse lexicale
        unique_words = len(set(sentence.lower().split()))
        total_words = len(sentence.split())
        lexical_diversity = unique_words / total_words if total_words > 0 else 0
        score += lexical_diversity * 0.2
        
        # 4. Présence de mots-clés techniques
        technical_keywords = ['fonction', 'classe', 'variable', 'algorithme', 'méthode', 'objet', 'données']
        tech_score = sum(1 for keyword in technical_keywords if keyword in sentence.lower())
        score += min(tech_score / len(technical_keywords), 1.0) * 0.3
        
        return min(score, 1.0)
    
    def _summarize_content(self, content: str, target_length: int) -> str:
        """Résume le contenu à la longueur cible"""
        # Résumé extractif simple
        words = content.split()
        if len(words) <= target_length // 5:  # Approximation mots -> chars
            return content
        
        # Prendre des mots distribués uniformément
        step = len(words) / (target_length // 5)
        selected_words = []
        
        for i in range(target_length // 5):
            idx = int(i * step)
            if idx < len(words):
                selected_words.append(words[idx])
        
        return ' '.join(selected_words)

class SlidingWindowAttention:
    """Attention par fenêtre glissante pour très longs contextes"""
    
    def __init__(self, window_size: int = 1024, stride: int = 512):
        self.window_size = window_size
        self.stride = stride
        self.logger = setup_logger("SlidingWindowAttention")
    
    def process_with_sliding_window(self, long_context: str, query: str, model: CustomAIModel) -> str:
        """Traite un long contexte avec fenêtre glissante"""
        # Diviser en fenêtres
        windows = self._create_sliding_windows(long_context)
        
        # Traiter chaque fenêtre
        window_responses = []
        for i, window in enumerate(windows):
            print(f"   🪟 Traitement fenêtre {i+1}/{len(windows)}")
            
            window_query = f"Basé sur ce contexte, {query}\n\nContexte:\n{window}"
            response = model.generate_response(window_query, {})
            
            if response:
                window_responses.append({
                    "window_id": i,
                    "response": response,
                    "context_start": window[:100] + "...",
                    "response_length": len(response)
                })
        
        # Synthétiser les réponses
        final_response = self._synthesize_window_responses(window_responses, query)
        
        return final_response
    
    def _create_sliding_windows(self, text: str) -> List[str]:
        """Crée des fenêtres glissantes avec chevauchement"""
        words = text.split()
        windows = []
        
        for i in range(0, len(words), self.stride):
            window_words = words[i:i + self.window_size]
            if window_words:
                window_text = ' '.join(window_words)
                windows.append(window_text)
        
        self.logger.info(f"Créé {len(windows)} fenêtres de {self.window_size} tokens")
        return windows
    
    def _synthesize_window_responses(self, responses: List[Dict], original_query: str) -> str:
        """Synthétise les réponses de multiples fenêtres"""
        if not responses:
            return "Aucune réponse générée."
        
        if len(responses) == 1:
            return responses[0]["response"]
        
        # Construire une synthèse intelligente
        synthesis = f"🔍 **Réponse basée sur l'analyse de {len(responses)} sections:**\n\n"
        
        # Extraire les points clés de chaque réponse
        key_points = []
        for resp in responses:
            response_text = resp["response"]
            # Extraire les phrases principales (simpliste)
            sentences = response_text.split('.')
            main_sentences = [s.strip() for s in sentences if len(s.strip()) > 20]
            if main_sentences:
                key_points.extend(main_sentences[:2])  # Max 2 points par fenêtre
        
        # Déduplication et organisation
        unique_points = []
        for point in key_points:
            if not any(self._texts_similar(point, existing) for existing in unique_points):
                unique_points.append(point)
        
        # Construire la réponse finale
        for i, point in enumerate(unique_points[:8], 1):  # Max 8 points
            synthesis += f"{i}. {point}.\n"
        
        synthesis += f"\n💡 *Synthèse basée sur {len(responses)} sections du document.*"
        
        return synthesis
    
    def _texts_similar(self, text1: str, text2: str, threshold: float = 0.7) -> bool:
        """Vérifie si deux textes sont similaires"""
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        if not words1 or not words2:
            return False
        
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        similarity = len(intersection) / len(union)
        return similarity >= threshold

class ContextWindowOptimizer:
    """Optimiseur principal de la fenêtre de contexte"""
    
    def __init__(self):
        self.logger = setup_logger("ContextWindowOptimizer")
        self.compressor = ContextCompressor(compression_ratio=0.4)
        self.sliding_attention = SlidingWindowAttention(window_size=1024, stride=512)
        self.memory_attention = MemoryEfficientAttention(AttentionConfig())
        
        # Statistiques d'optimisation
        self.optimization_stats = {
            "compressions_performed": 0,
            "avg_compression_ratio": 0.0,
            "total_tokens_saved": 0,
            "processing_time_saved": 0.0
        }
    
    def optimize_for_query(self, context: str, query: str, max_context_length: int = 4096) -> Tuple[str, Dict[str, Any]]:
        """Optimise le contexte pour une requête spécifique"""
        original_length = len(context)
        optimization_info = {
            "original_length": original_length,
            "target_length": max_context_length,
            "techniques_used": [],
            "optimization_ratio": 0.0,
            "processing_time": 0.0
        }
        
        start_time = time.time()
        
        # Étape 1: Si le contexte est dans la limite, pas d'optimisation
        if original_length <= max_context_length:
            optimization_info["techniques_used"].append("no_optimization_needed")
            optimization_info["processing_time"] = time.time() - start_time
            return context, optimization_info
        
        # Étape 2: Compression intelligente
        compressed_context = self.compressor.compress_context(context, max_context_length)
        optimization_info["techniques_used"].append("intelligent_compression")
        
        # Étape 3: Si encore trop long, utiliser l'attention par fenêtre glissante
        if len(compressed_context) > max_context_length:
            compressed_context = self.memory_attention.process_long_sequence(compressed_context, query)
            optimization_info["techniques_used"].append("memory_efficient_attention")
        
        # Étape 4: Dernier recours - troncature intelligente
        if len(compressed_context) > max_context_length:
            compressed_context = self._smart_truncation(compressed_context, query, max_context_length)
            optimization_info["techniques_used"].append("smart_truncation")
        
        # Calculer les métriques
        final_length = len(compressed_context)
        optimization_info["final_length"] = final_length
        optimization_info["optimization_ratio"] = (original_length - final_length) / original_length
        optimization_info["processing_time"] = time.time() - start_time
        
        # Mettre à jour les statistiques
        self._update_stats(optimization_info)
        
        self.logger.info(f"Contexte optimisé: {original_length} -> {final_length} chars "
                        f"({optimization_info['optimization_ratio']:.1%} réduction)")
        
        return compressed_context, optimization_info
    
    def _smart_truncation(self, context: str, query: str, max_length: int) -> str:
        """Troncature intelligente préservant les informations importantes"""
        if len(context) <= max_length:
            return context
        
        # Diviser en sections logiques
        sections = context.split('\n\n')
        
        # Scorer chaque section par rapport à la requête
        query_words = set(query.lower().split())
        scored_sections = []
        
        for section in sections:
            section_words = set(section.lower().split())
            relevance = len(query_words.intersection(section_words)) / len(query_words) if query_words else 0
            scored_sections.append((section, relevance))
        
        # Trier par pertinence
        scored_sections.sort(key=lambda x: x[1], reverse=True)
        
        # Sélectionner les sections les plus pertinentes
        selected_text = ""
        for section, score in scored_sections:
            if len(selected_text) + len(section) <= max_length:
                selected_text += section + "\n\n"
            else:
                # Ajouter une partie de la section si possible
                remaining_space = max_length - len(selected_text)
                if remaining_space > 100:  # Au moins 100 chars
                    selected_text += section[:remaining_space-3] + "..."
                break
        
        return selected_text.strip()
    
    def _update_stats(self, optimization_info: Dict[str, Any]):
        """Met à jour les statistiques d'optimisation"""
        self.optimization_stats["compressions_performed"] += 1
        
        # Moyenne mobile du ratio de compression
        new_ratio = optimization_info["optimization_ratio"]
        current_avg = self.optimization_stats["avg_compression_ratio"]
        count = self.optimization_stats["compressions_performed"]
        
        self.optimization_stats["avg_compression_ratio"] = (current_avg * (count - 1) + new_ratio) / count
        
        # Tokens économisés
        tokens_saved = optimization_info["original_length"] - optimization_info["final_length"]
        self.optimization_stats["total_tokens_saved"] += tokens_saved
        
        # Temps de traitement
        self.optimization_stats["processing_time_saved"] += optimization_info["processing_time"]
    
    def get_optimization_report(self) -> Dict[str, Any]:
        """Génère un rapport d'optimisation"""
        return {
            **self.optimization_stats,
            "avg_processing_time": (
                self.optimization_stats["processing_time_saved"] / 
                self.optimization_stats["compressions_performed"]
            ) if self.optimization_stats["compressions_performed"] > 0 else 0
        }

class AdaptiveContextManager:
    """Gestionnaire adaptatif du contexte basé sur l'utilisation"""
    
    def __init__(self, base_model: CustomAIModel):
        self.base_model = base_model
        self.optimizer = ContextWindowOptimizer()
        self.logger = setup_logger("AdaptiveContextManager")
        
        # Configuration adaptative
        self.context_configs = {
            "short_answer": {"max_length": 1024, "compression": 0.2},
            "detailed_analysis": {"max_length": 4096, "compression": 0.4},
            "code_generation": {"max_length": 2048, "compression": 0.3},
            "document_summary": {"max_length": 6144, "compression": 0.5}
        }
        
        # Historique d'adaptation
        self.adaptation_history = []
    
    def generate_adaptive_response(self, query: str, context: str, 
                                 query_type: Optional[str] = None) -> str:
        """Génère une réponse avec gestion adaptative du contexte"""
        # 1. Détecter le type de requête si non spécifié
        if query_type is None:
            query_type = self._detect_query_type(query)
        
        # 2. Récupérer la configuration adaptée
        config = self.context_configs.get(query_type, self.context_configs["detailed_analysis"])
        
        # 3. Optimiser le contexte selon le type de requête
        optimized_context, optimization_info = self.optimizer.optimize_for_query(
            context, query, config["max_length"]
        )
        
        # 4. Générer la réponse
        start_time = time.time()
        response = self.base_model.generate_response(query, {"optimized_context": optimized_context})
        generation_time = time.time() - start_time
        
        # 5. Enregistrer l'adaptation pour apprentissage
        adaptation_record = {
            "timestamp": datetime.now().isoformat(),
            "query_type": query_type,
            "original_context_length": len(context),
            "optimized_context_length": len(optimized_context),
            "optimization_ratio": optimization_info["optimization_ratio"],
            "generation_time": generation_time,
            "techniques_used": optimization_info["techniques_used"]
        }
        
        self.adaptation_history.append(adaptation_record)
        
        # 6. Apprentissage adaptatif (ajuster les configs)
        self._adaptive_learning(query_type, adaptation_record)
        
        self.logger.info(f"Réponse adaptative générée: {query_type}, "
                        f"contexte {len(context)}->{len(optimized_context)}")
        
        return response
    
    def _detect_query_type(self, query: str) -> str:
        """Détecte automatiquement le type de requête"""
        query_lower = query.lower()
        
        # Patterns de détection
        if any(word in query_lower for word in ["génère", "code", "fonction", "classe", "script"]):
            return "code_generation"
        elif any(word in query_lower for word in ["résume", "résumé", "synthèse", "document"]):
            return "document_summary"
        elif any(word in query_lower for word in ["analyse", "explique", "détaille", "pourquoi", "comment"]):
            return "detailed_analysis"
        else:
            return "short_answer"
    
    def _adaptive_learning(self, query_type: str, record: Dict[str, Any]):
        """Apprentissage adaptatif des configurations"""
        # Analyser les performances récentes pour ce type de requête
        recent_records = [r for r in self.adaptation_history[-20:] if r["query_type"] == query_type]
        
        if len(recent_records) >= 5:  # Assez de données pour adapter
            avg_time = sum(r["generation_time"] for r in recent_records) / len(recent_records)
            avg_ratio = sum(r["optimization_ratio"] for r in recent_records) / len(recent_records)
            
            # Ajuster la configuration si nécessaire
            current_config = self.context_configs[query_type]
            
            # Si les temps sont trop longs, réduire la longueur max
            if avg_time > 2.0:  # Plus de 2 secondes
                current_config["max_length"] = int(current_config["max_length"] * 0.9)
                current_config["compression"] = min(current_config["compression"] + 0.1, 0.8)
                self.logger.info(f"Config adaptée pour {query_type}: réduction de la fenêtre")
            
            # Si les temps sont très rapides, on peut augmenter
            elif avg_time < 0.5 and avg_ratio > 0.5:  # Très rapide et beaucoup de compression
                current_config["max_length"] = int(current_config["max_length"] * 1.1)
                current_config["compression"] = max(current_config["compression"] - 0.05, 0.1)
                self.logger.info(f"Config adaptée pour {query_type}: augmentation de la fenêtre")

class FlashAttentionSimulator:
    """Simulateur de FlashAttention pour optimisation mémoire"""
    
    def __init__(self):
        self.logger = setup_logger("FlashAttentionSimulator")
        self.block_size = 256  # Taille des blocs pour simulation
    
    def simulate_flash_attention(self, context: str, query: str) -> Dict[str, Any]:
        """Simule l'efficacité de FlashAttention"""
        # Calculer la complexité théorique
        context_length = len(context.split())
        
        # Complexité standard: O(n²)
        standard_complexity = context_length ** 2
        
        # Complexité FlashAttention: O(n)
        flash_complexity = context_length * math.log(context_length)
        
        # Estimation des gains
        memory_reduction = 1 - (flash_complexity / standard_complexity)
        speed_improvement = standard_complexity / flash_complexity
        
        # Simulation de traitement par blocs
        blocks = self._simulate_block_processing(context, query)
        
        return {
            "context_length": context_length,
            "estimated_memory_reduction": memory_reduction,
            "estimated_speed_improvement": speed_improvement,
            "blocks_processed": len(blocks),
            "theoretical_benefits": {
                "memory_usage_ratio": flash_complexity / standard_complexity,
                "speed_improvement_factor": speed_improvement,
                "optimal_for_length": context_length > 1000
            }
        }
    
    def _simulate_block_processing(self, context: str, query: str) -> List[Dict[str, Any]]:
        """Simule le traitement par blocs de FlashAttention"""
        words = context.split()
        blocks = []
        
        for i in range(0, len(words), self.block_size):
            block_words = words[i:i + self.block_size]
            
            # Simuler le calcul d'attention pour ce bloc
            attention_score = self._simulate_attention_computation(block_words, query.split())
            
            blocks.append({
                "block_id": i // self.block_size,
                "start_pos": i,
                "end_pos": min(i + self.block_size, len(words)),
                "attention_score": attention_score,
                "memory_usage": len(block_words) * 4  # Approximation en bytes
            })
        
        return blocks
    
    def _simulate_attention_computation(self, block_words: List[str], query_words: List[str]) -> float:
        """Simule le calcul d'attention pour un bloc"""
        # Score basé sur la correspondance de mots
        block_set = set(word.lower() for word in block_words)
        query_set = set(word.lower() for word in query_words)
        
        intersection = block_set.intersection(query_set)
        return len(intersection) / len(query_set) if query_set else 0.0

class AdvancedContextOptimizer:
    """Optimiseur de contexte intégrant toutes les techniques"""
    
    def __init__(self, base_model: CustomAIModel = None):
        self.base_model = base_model or CustomAIModel()
        self.adaptive_manager = AdaptiveContextManager(self.base_model)
        self.flash_simulator = FlashAttentionSimulator()
        self.logger = setup_logger("AdvancedContextOptimizer")
        
        # Métriques de performance
        self.performance_metrics = {
            "total_optimizations": 0,
            "avg_optimization_time": 0.0,
            "total_memory_saved": 0,
            "user_satisfaction_score": 0.8  # Score initial
        }
    
    def process_with_optimal_strategy(self, context: str, query: str) -> str:
        """Traite avec la stratégie optimale selon le contexte et la requête"""
        # Analyser le contexte et la requête
        analysis = self._analyze_context_and_query(context, query)
        
        # Choisir la stratégie optimale
        strategy = self._select_optimal_strategy(analysis)
        
        # Appliquer la stratégie
        optimized_response = self._apply_strategy(context, query, strategy, analysis)
        
        return optimized_response
    
    def compress_context(self, context: str, target_length: Optional[int] = None) -> str:
        """Compresse le contexte - méthode de compatibilité pour validation"""
        if target_length is None:
            target_length = int(len(context) * 0.7)  # Compression de 30%
        
        try:
            # Utiliser l'optimiseur adaptatif
            compressed, stats = self.adaptive_manager.optimizer.optimize_for_query(
                context, "", target_length
            )
            
            self.logger.info(f"Contexte compressé: {len(context)} -> {len(compressed)} chars")
            return compressed
            
        except Exception as e:
            self.logger.warning(f"Erreur compression, utilisation fallback: {e}")
            # Fallback simple
            if len(context) <= target_length:
                return context
            
            # Compression simple par troncature intelligente
            lines = context.split('\n')
            compressed_lines = []
            current_length = 0
            
            for line in lines:
                if current_length + len(line) < target_length:
                    compressed_lines.append(line)
                    current_length += len(line) + 1
                else:
                    break
            
            return '\n'.join(compressed_lines)
    
    def _analyze_context_and_query(self, context: str, query: str) -> Dict[str, Any]:
        """Analyse le contexte et la requête pour choisir la stratégie"""
        context_length = len(context)
        query_length = len(query)
        
        # Analyser le type de contenu
        content_analysis = {
            "has_code": "def " in context or "class " in context or "import " in context,
            "has_structured_data": "{" in context and "}" in context,
            "has_lists": any(marker in context for marker in ["- ", "• ", "1. ", "2. "]),
            "repetitive_content": self._detect_repetitive_content(context),
            "technical_density": self._calculate_technical_density(context)
        }
        
        # Analyser le type de requête
        query_analysis = {
            "is_summary_request": any(word in query.lower() for word in ["résume", "synthèse", "résumé"]),
            "is_specific_search": any(word in query.lower() for word in ["trouve", "cherche", "où"]),
            "is_generation_request": any(word in query.lower() for word in ["génère", "crée", "écris"]),
            "complexity_level": "high" if len(query.split()) > 10 else "medium" if len(query.split()) > 5 else "low"
        }
        
        # FlashAttention simulation
        flash_analysis = self.flash_simulator.simulate_flash_attention(context, query)
        
        return {
            "context_length": context_length,
            "query_length": query_length,
            "content_analysis": content_analysis,
            "query_analysis": query_analysis,
            "flash_analysis": flash_analysis,
            "optimization_recommended": context_length > 2048
        }
    
    def _select_optimal_strategy(self, analysis: Dict[str, Any]) -> str:
        """Sélectionne la stratégie optimale"""
        context_length = analysis["context_length"]
        content = analysis["content_analysis"]
        query = analysis["query_analysis"]
        flash = analysis["flash_analysis"]
        
        # Logique de sélection de stratégie
        if context_length < 1024:
            return "direct_processing"
        elif context_length < 4096 and not content["repetitive_content"]:
            return "light_compression"
        elif query["is_summary_request"]:
            return "summary_optimized"
        elif query["is_specific_search"]:
            return "retrieval_focused"
        elif flash["optimal_for_length"]:
            return "flash_attention_simulation"
        elif content["has_code"]:
            return "code_aware_chunking"
        else:
            return "adaptive_windowing"
    
    def _apply_strategy(self, context: str, query: str, strategy: str, analysis: Dict[str, Any]) -> str:
        """Applique la stratégie sélectionnée"""
        self.logger.info(f"Application de la stratégie: {strategy}")
        
        if strategy == "direct_processing":
            return self.base_model.generate_response(query, {"context": context})
        
        elif strategy == "light_compression":
            compressed, _ = self.adaptive_manager.optimizer.optimize_for_query(context, query, 3072)
            return self.base_model.generate_response(query, {"context": compressed})
        
        elif strategy == "summary_optimized":
            # Compression agressive pour résumés
            compressed, _ = self.adaptive_manager.optimizer.optimize_for_query(context, query, 2048)
            summary_query = f"Fais un résumé structuré de ce contenu: {query}"
            return self.base_model.generate_response(summary_query, {"context": compressed})
        
        elif strategy == "retrieval_focused":
            # Utiliser la recherche sémantique
            relevant_parts = self._extract_relevant_parts(context, query)
            return self.base_model.generate_response(query, {"context": relevant_parts})
        
        elif strategy == "flash_attention_simulation":
            # Simuler FlashAttention avec fenêtre glissante
            return self.adaptive_manager.sliding_attention.process_with_sliding_window(
                context, query, self.base_model
            )
        
        elif strategy == "code_aware_chunking":
            # Chunking spécialisé pour le code
            code_chunks = self._smart_code_chunking(context)
            optimized_context = "\n\n".join(code_chunks[:5])  # Top 5 chunks
            return self.base_model.generate_response(query, {"context": optimized_context})
        
        elif strategy == "adaptive_windowing":
            # Fenêtrage adaptatif
            return self.adaptive_manager.generate_adaptive_response(query, context)
        
        else:
            # Fallback
            return self.base_model.generate_response(query, {"context": context})
    
    def _detect_repetitive_content(self, text: str) -> bool:
        """Détecte si le contenu est répétitif"""
        sentences = text.split('.')
        if len(sentences) < 5:
            return False
        
        # Vérifier la répétition de phrases similaires
        unique_sentences = set()
        repetitive_count = 0
        
        for sentence in sentences:
            sentence_clean = ' '.join(sentence.strip().split()[:5])  # 5 premiers mots
            if sentence_clean in unique_sentences:
                repetitive_count += 1
            else:
                unique_sentences.add(sentence_clean)
        
        return repetitive_count / len(sentences) > 0.3
    
    def _calculate_technical_density(self, text: str) -> float:
        """Calcule la densité technique du texte"""
        technical_terms = [
            'function', 'class', 'variable', 'algorithm', 'method', 'object',
            'fonction', 'classe', 'variable', 'algorithme', 'méthode', 'objet',
            'model', 'training', 'neural', 'network', 'data', 'parameter'
        ]
        
        words = text.lower().split()
        technical_count = sum(1 for word in words if any(term in word for term in technical_terms))
        
        return technical_count / len(words) if words else 0
    
    def _extract_relevant_parts(self, context: str, query: str) -> str:
        """Extrait les parties les plus pertinentes du contexte"""
        query_words = set(query.lower().split())
        
        # Diviser en paragraphes
        paragraphs = context.split('\n\n')
        scored_paragraphs = []
        
        for paragraph in paragraphs:
            para_words = set(paragraph.lower().split())
            relevance = len(query_words.intersection(para_words)) / len(query_words) if query_words else 0
            scored_paragraphs.append((paragraph, relevance))
        
        # Trier et sélectionner les plus pertinents
        scored_paragraphs.sort(key=lambda x: x[1], reverse=True)
        
        # Prendre les paragraphes jusqu'à une limite raisonnable
        selected_paragraphs = []
        total_length = 0
        
        for paragraph, score in scored_paragraphs:
            if total_length + len(paragraph) <= 2048 and score > 0.1:
                selected_paragraphs.append(paragraph)
                total_length += len(paragraph)
            else:
                break
        
        return '\n\n'.join(selected_paragraphs)
    
    def _smart_code_chunking(self, code_context: str) -> List[str]:
        """Chunking intelligent spécialisé pour le code"""
        chunks = []
        
        # Diviser par fonctions/classes
        import re
        
        # Pattern pour détecter les définitions de fonctions/classes
        function_pattern = r'(def\s+\w+.*?:.*?)(?=\ndef\s|\nclass\s|\n\n|\Z)'
        class_pattern = r'(class\s+\w+.*?:.*?)(?=\nclass\s|\ndef\s|\n\n|\Z)'
        
        # Extraire fonctions et classes
        functions = re.findall(function_pattern, code_context, re.DOTALL)
        classes = re.findall(class_pattern, code_context, re.DOTALL)
        
        # Ajouter comme chunks séparés
        for func in functions:
            chunks.append(f"[FONCTION]\n{func}")
        
        for cls in classes:
            chunks.append(f"[CLASSE]\n{cls}")
        
        # Si pas de structure détectée, chunking par ligne
        if not chunks:
            lines = code_context.split('\n')
            current_chunk = ""
            
            for line in lines:
                if len(current_chunk) + len(line) <= 500:
                    current_chunk += line + '\n'
                else:
                    if current_chunk.strip():
                        chunks.append(current_chunk)
                    current_chunk = line + '\n'
            
            if current_chunk.strip():
                chunks.append(current_chunk)
        
        return chunks

def demo_optimization_techniques():
    """Démonstration des techniques d'optimisation"""
    print("🚀 Démonstration des Techniques d'Optimisation")
    print("=" * 60)
    
    # Préparer un contexte long de test
    long_context = """
    L'intelligence artificielle est un domaine en constante évolution. Les modèles de langage modernes utilisent des architectures transformer avec des mécanismes d'attention sophistiqués.
    
    FlashAttention est une technique révolutionnaire qui optimise le calcul d'attention en réduisant la complexité mémoire de O(n²) à O(n). Cette optimisation permet de traiter des séquences beaucoup plus longues.
    
    La quantification est une autre technique importante qui réduit la précision des poids du modèle, permettant une inférence plus rapide et une empreinte mémoire réduite.
    
    Le pruning supprime les connexions neuronales les moins importantes, créant des modèles plus compacts sans perte significative de performance.
    
    Les techniques de compression de contexte permettent de traiter des documents très longs en extrayant automatiquement les informations les plus pertinentes.
    """ * 10  # Répéter pour créer un long contexte
    
    # Initialiser l'optimiseur avancé
    base_model = CustomAIModel()
    advanced_optimizer = AdvancedContextOptimizer(base_model)
    
    # Test des différentes stratégies
    test_queries = [
        "Qu'est-ce que FlashAttention et comment ça marche ?",
        "Résume les techniques d'optimisation IA",
        "Génère du code pour implémenter une attention efficace",
        "Explique en détail la quantification des modèles"
    ]
    
    results = {}
    
    for query in test_queries:
        print(f"\n🧪 Test: {query[:50]}...")
        
        # Analyser et traiter
        start_time = time.time()
        response = advanced_optimizer.process_with_optimal_strategy(long_context, query)
        processing_time = time.time() - start_time
        
        # Simuler FlashAttention pour comparaison
        flash_sim = advanced_optimizer.flash_simulator.simulate_flash_attention(long_context, query)
        
        results[query] = {
            "processing_time": processing_time,
            "response_length": len(response),
            "flash_simulation": flash_sim,
            "strategy_used": "advanced_optimization"
        }
        
        print(f"  ✅ Traité en {processing_time:.3f}s")
        print(f"  📊 FlashAttention réduirait la mémoire de {flash_sim['estimated_memory_reduction']:.1%}")
        print(f"  🚀 Amélioration vitesse estimée: {flash_sim['estimated_speed_improvement']:.1f}x")
    
    # Rapport d'optimisation
    print(f"\n📈 RAPPORT D'OPTIMISATION")
    print("=" * 40)
    
    avg_time = sum(r["processing_time"] for r in results.values()) / len(results)
    avg_flash_improvement = sum(r["flash_simulation"]["estimated_speed_improvement"] for r in results.values()) / len(results)
    
    print(f"⏱️ Temps moyen actuel: {avg_time:.3f}s")
    print(f"🚀 Amélioration FlashAttention estimée: {avg_flash_improvement:.1f}x")
    print(f"💾 Réduction mémoire moyenne: {sum(r['flash_simulation']['estimated_memory_reduction'] for r in results.values()) / len(results):.1%}")
    
    return results

def main():
    """Point d'entrée principal"""
    print("⚡ My_AI - Optimisations Avancées v1.0")
    print("=" * 50)
    
    # Vérifier les dépendances optionnelles
    deps_status = {
        "torch": TORCH_AVAILABLE,
        "transformers": TRANSFORMERS_AVAILABLE
    }
    
    print("📦 Status des dépendances:")
    for dep, available in deps_status.items():
        status = "✅" if available else "❌"
        print(f"   {status} {dep}")
    
    if not any(deps_status.values()):
        print("\n💡 Pour des optimisations complètes, installez:")
        print("   pip install torch transformers")
    
    # Démonstration
    demo_results = demo_optimization_techniques()
    
    print(f"\n🎯 Optimisations prêtes à intégrer dans My_AI!")
    
    return demo_results

if __name__ == "__main__":
    main()
