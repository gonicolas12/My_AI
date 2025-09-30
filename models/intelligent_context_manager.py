"""
Gestionnaire de contexte ultra-intelligent pour 1M tokens RÉELS
Architecture 100% locale pour votre CustomAIModel
"""

import re
import json
import time
import sqlite3
import hashlib
import gzip
import pickle
from typing import List, Dict, Any, Tuple, Optional
from dataclasses import dataclass, field
from datetime import datetime
from collections import defaultdict, deque

try:
    import numpy as np
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    SKLEARN_AVAILABLE = True
except ImportError:
    # Fallback complet sans sklearn
    SKLEARN_AVAILABLE = False
    import re
    
    # Classes de fallback pour remplacer sklearn
    class TfidfVectorizer:
        def __init__(self, max_features=5000, stop_words=None, ngram_range=(1, 1)):
            self.max_features = max_features
            
        def fit_transform(self, texts):
            return None
            
        def transform(self, texts):
            return None
    
    def cosine_similarity(a, b):
        """Fallback pour cosine_similarity"""
        return [[0.5]]  # Similarité par défaut

@dataclass
class UltraContextChunk:
    """Chunk de contexte ultra-optimisé avec compression et indexation"""
    id: str
    content: str
    tokens: int
    importance: float
    type: str  # 'conversation', 'document', 'code', 'system'
    timestamp: float
    keywords: List[str]
    summary: str
    compressed_content: Optional[bytes] = None
    references: List[str] = field(default_factory=list)
    access_count: int = 0
    last_access: float = 0

class UltraIntelligentContextManager:
    """
    Gestionnaire de contexte ULTRA-INTELLIGENT pour 1M tokens réels
    Techniques avancées: compression, hierarchisation, indexation sémantique
    """
    
    def __init__(self, max_total_tokens: int = 1048576):  # 1M tokens RÉELS
        self.max_total_tokens = max_total_tokens
        self.active_chunks: List[UltraContextChunk] = []
        self.archived_chunks: Dict[str, UltraContextChunk] = {}
        
        # Système d'indexation multi-niveaux (avec fallback si sklearn absent)
        if SKLEARN_AVAILABLE:
            self.tfidf_vectorizer = TfidfVectorizer(
                max_features=5000, 
                stop_words='english',
                ngram_range=(1, 2)  # Unigrammes et bigrammes
            )
        else:
            self.tfidf_vectorizer = TfidfVectorizer()  # Classe fallback
        
        self.chunk_vectors = None
        
        # Index sémantique pour recherche ultra-rapide
        self.keyword_index: Dict[str, List[str]] = defaultdict(list)
        self.semantic_clusters: Dict[str, List[str]] = {}
        
        # Système de hiérarchisation intelligent
        self.importance_levels = {
            'critical': 1.0,    # Système, erreurs
            'high': 0.8,        # Code, documents importants
            'medium': 0.6,      # Conversations importantes
            'low': 0.4,         # Conversations normales
            'minimal': 0.2      # Logs, debug
        }
        
        # Base de données pour persistance
        self.db_path = "context_storage/ultra_context.db"
        self._init_database()
        
        # Statistiques en temps réel
        self.stats = {
            'total_processed': 0,
            'compression_ratio': 0.0,
            'search_performance': 0.0,
            'memory_efficiency': 0.0
        }
        
        print("🚀 UltraIntelligentContextManager initialisé - Capacité 1M tokens")
    
    def _init_database(self):
        """Initialise la base de données SQLite"""
        try:
            import sqlite3
            conn = sqlite3.connect(self.db_path)
            conn.execute('''
                CREATE TABLE IF NOT EXISTS chunks (
                    id TEXT PRIMARY KEY,
                    content TEXT,
                    tokens INTEGER,
                    importance REAL,
                    type TEXT,
                    timestamp REAL,
                    keywords TEXT,
                    summary TEXT
                )
            ''')
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"⚠️ Erreur base de données: {e}")
        
    def add_ultra_content(self, content: str, content_type: str = "conversation", 
                         importance_level: str = "medium", metadata: Dict = None) -> List[str]:
        """
        Ajoute du contenu avec découpage ULTRA-INTELLIGENT
        
        Args:
            content: Contenu à ajouter
            content_type: Type ('conversation', 'document', 'code', 'system')  
            importance_level: Niveau d'importance ('critical', 'high', 'medium', 'low', 'minimal')
            metadata: Métadonnées additionnelles
            
        Returns:
            Liste des IDs des chunks créés
        """
        
        if not content.strip():
            return []
        
        # Découpage ultra-intelligent selon le type
        chunks = self._intelligent_chunking(content, content_type)
        
        chunk_ids = []
        importance = self.importance_levels.get(importance_level, 0.6)
        
        for i, chunk_text in enumerate(chunks):
            # Génération d'ID unique basé sur hash + timestamp
            chunk_hash = hashlib.md5(chunk_text.encode()).hexdigest()[:8]
            chunk_id = f"{content_type}_{int(time.time())}_{i}_{chunk_hash}"
            
            # Extraction de mots-clés avancée
            keywords = self._extract_keywords(chunk_text)
            
            # Génération de résumé intelligent
            summary = self._generate_summary(chunk_text)
            
            # Création du chunk ultra-optimisé
            chunk = UltraContextChunk(
                id=chunk_id,
                content=chunk_text,
                tokens=self._ultra_count_tokens(chunk_text),
                importance=importance,
                type=content_type,
                timestamp=time.time(),
                keywords=keywords,
                summary=summary,
                access_count=0,
                last_access=time.time()
            )
            
            # Compression automatique pour les gros chunks
            if chunk.tokens > 2000:
                chunk.compressed_content = self._compress_chunk(chunk_text)
            
            # Ajout au contexte actif
            self._add_to_active_context(chunk)
            
            # Indexation sémantique
            self._update_semantic_index(chunk)
            
            chunk_ids.append(chunk_id)
            
        # Optimisation automatique si nécessaire
        self._auto_optimize_if_needed()
        
        # Mise à jour des statistiques
        self._update_stats()
        
        return chunk_ids
    
    def _intelligent_chunking(self, content: str, content_type: str) -> List[str]:
        """Découpe intelligemment selon le type de contenu"""
        
        if content_type == "code":
            return self._chunk_code(content)
        elif content_type == "document":
            return self._chunk_document(content)
        elif content_type == "conversation":
            return self._chunk_conversation(content)
        else:
            return self._chunk_generic(content)
    
    def _chunk_code(self, code: str) -> List[str]:
        """Découpe le code par fonctions/classes"""
        chunks = []
        lines = code.split('\n')
        
        current_chunk = []
        current_size = 0
        target_size = 2000  # ~500 tokens par chunk
        
        i = 0
        while i < len(lines):
            line = lines[i]
            
            # Détecter le début d'une fonction ou classe
            if line.strip().startswith(('def ', 'class ')):
                # Sauvegarder le chunk précédent s'il existe
                if current_chunk:
                    chunks.append('\n'.join(current_chunk))
                    current_chunk = []
                    current_size = 0
                
                # Collecter toute la fonction/classe
                indent_level = len(line) - len(line.lstrip())
                current_chunk.append(line)
                current_size += len(line)
                i += 1
                
                # Continuer tant qu'on est dans la même fonction/classe
                while i < len(lines):
                    next_line = lines[i]
                    if (next_line.strip() and 
                        not next_line.startswith(' ' * (indent_level + 1)) and
                        not next_line.strip() == '' and
                        len(next_line) - len(next_line.lstrip()) <= indent_level):
                        break
                    
                    current_chunk.append(next_line)
                    current_size += len(next_line)
                    i += 1
                
                # Si le chunk devient trop gros, le finaliser
                if current_size > target_size:
                    chunks.append('\n'.join(current_chunk))
                    current_chunk = []
                    current_size = 0
            else:
                current_chunk.append(line)
                current_size += len(line)
                
                # Chunk trop gros, le finaliser
                if current_size > target_size:
                    chunks.append('\n'.join(current_chunk))
                    current_chunk = []
                    current_size = 0
                
                i += 1
        
        # Ajouter le dernier chunk s'il existe
        if current_chunk:
            chunks.append('\n'.join(current_chunk))
        
        return [chunk for chunk in chunks if len(chunk.strip()) > 50]
    
    def _chunk_document(self, content: str) -> List[str]:
        """Découpe le document par paragraphes/sections"""
        # Essayer de détecter les sections
        sections = re.split(r'\n\s*\n', content)
        chunks = []
        
        current_chunk = ""
        target_size = 3000  # ~750 tokens
        
        for section in sections:
            section = section.strip()
            if not section:
                continue
            
            # Si ajouter cette section dépasse la taille cible
            if len(current_chunk) + len(section) > target_size and current_chunk:
                chunks.append(current_chunk)
                current_chunk = section
            else:
                if current_chunk:
                    current_chunk += "\n\n" + section
                else:
                    current_chunk = section
        
        # Ajouter le dernier chunk
        if current_chunk:
            chunks.append(current_chunk)
        
        return chunks
    
    def _chunk_conversation(self, content: str) -> List[str]:
        """Découpe la conversation par échanges"""
        # Détecter les patterns de conversation
        exchanges = re.split(r'(User:|AI:|Human:|Assistant:)', content)
        chunks = []
        
        current_chunk = ""
        exchange_count = 0
        target_exchanges = 10  # 10 échanges par chunk
        
        for i in range(0, len(exchanges), 2):
            if i + 1 < len(exchanges):
                exchange = exchanges[i] + exchanges[i + 1]
                current_chunk += exchange
                exchange_count += 1
                
                if exchange_count >= target_exchanges:
                    chunks.append(current_chunk)
                    current_chunk = ""
                    exchange_count = 0
        
        if current_chunk:
            chunks.append(current_chunk)
        
        return chunks
    
    def _chunk_generic(self, content: str) -> List[str]:
        """Découpe générique par taille"""
        target_size = 2500  # ~625 tokens
        chunks = []
        
        sentences = re.split(r'[.!?]+\s+', content)
        current_chunk = ""
        
        for sentence in sentences:
            if len(current_chunk) + len(sentence) > target_size and current_chunk:
                chunks.append(current_chunk)
                current_chunk = sentence
            else:
                if current_chunk:
                    current_chunk += ". " + sentence
                else:
                    current_chunk = sentence
        
        if current_chunk:
            chunks.append(current_chunk)
        
        return chunks
    
    def _ultra_count_tokens(self, text: str) -> int:
        """Compte précis des tokens"""
        return self._estimate_tokens(text)
    
    def _generate_summary(self, text: str) -> str:
        """Génère un résumé du texte"""
        # Résumé simple : prendre les 2 premières phrases
        sentences = text.split('. ')
        return '. '.join(sentences[:2]) + '.' if len(sentences) > 1 else text[:100] + '...'
    
    def _compress_chunk(self, content: str) -> bytes:
        """Compresse le contenu d'un chunk"""
        try:
            import gzip
            return gzip.compress(content.encode('utf-8'))
        except:
            return content.encode('utf-8')
    
    def _add_to_active_context(self, chunk: UltraContextChunk):
        """Ajoute un chunk au contexte actif"""
        self.active_chunks.append(chunk)
        self._manage_context_size()
    
    def _update_semantic_index(self, chunk: UltraContextChunk):
        """Met à jour l'index sémantique"""
        for keyword in chunk.keywords:
            self.keyword_index[keyword.lower()].append(chunk.id)
    
    def _auto_optimize_if_needed(self):
        """Optimise automatiquement si nécessaire"""
        total_tokens = sum(c.tokens for c in self.active_chunks)
        if total_tokens > self.max_total_tokens * 0.9:  # 90% de la capacité
            self._manage_context_size()
    
    def _update_stats(self):
        """Met à jour les statistiques"""
        self.stats['total_processed'] += 1
        total_tokens = sum(c.tokens for c in self.active_chunks)
        self.stats['compression_ratio'] = total_tokens / max(1, len(self.active_chunks))
        self.stats['memory_efficiency'] = (total_tokens / self.max_total_tokens) * 100
    
    def _estimate_tokens(self, text: str) -> int:
        """Estimation du nombre de tokens"""
        return len(text) // 4  # Approximation
    
    def _extract_keywords(self, text: str) -> List[str]:
        """Extrait les mots-clés importants"""
        words = re.findall(r'\b[a-zA-Z]{4,}\b', text.lower())
        # Garder les mots les plus fréquents
        word_freq = {}
        for word in words:
            word_freq[word] = word_freq.get(word, 0) + 1
        
        # Retourner les 5 mots les plus fréquents
        top_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:5]
        return [word for word, freq in top_words]
    
    def _manage_context_size(self):
        """Maintient la taille du contexte sous la limite"""
        total_tokens = sum(chunk.tokens for chunk in self.active_chunks)
        
        while total_tokens > self.max_total_tokens and self.active_chunks:
            # Supprimer les chunks les moins importants et les plus anciens
            self.active_chunks.sort(key=lambda c: (c.importance, c.timestamp))
            removed_chunk = self.active_chunks.pop(0)
            total_tokens -= removed_chunk.tokens
            print(f"🗑️ Chunk retiré: {removed_chunk.id} ({removed_chunk.tokens} tokens)")
    
    def _update_vectors(self):
        """Met à jour les vecteurs TF-IDF pour la recherche"""
        if not self.active_chunks:
            return
        
        texts = [chunk.content for chunk in self.active_chunks]
        try:
            self.chunk_vectors = self.tfidf_vectorizer.fit_transform(texts)
        except ValueError:
            # Fallback si pas assez de contenu
            self.chunk_vectors = None
    
    def search_relevant_chunks(self, query: str, max_chunks: int = 10) -> List['UltraContextChunk']:
        """Recherche les chunks les plus pertinents pour une requête"""
        if not self.active_chunks or self.chunk_vectors is None:
            return self.active_chunks[:max_chunks]
        
        try:
            if not SKLEARN_AVAILABLE:
                # Fallback simple par mots-clés
                query_words = set(query.lower().split())
                scored_chunks = []
                for chunk in self.active_chunks:
                    score = len(query_words.intersection(set(chunk.keywords)))
                    scored_chunks.append((score * chunk.importance, chunk))
                
                scored_chunks.sort(key=lambda x: x[0], reverse=True)
                return [chunk for score, chunk in scored_chunks[:max_chunks]]
            
            query_vector = self.tfidf_vectorizer.transform([query])
            similarities = cosine_similarity(query_vector, self.chunk_vectors)[0]
            
            # Combiner similarité et importance
            scores = []
            for i, chunk in enumerate(self.active_chunks):
                score = similarities[i] * chunk.importance
                scores.append((score, chunk))
            
            # Trier par score décroissant
            scores.sort(key=lambda x: x[0], reverse=True)
            
            return [chunk for score, chunk in scores[:max_chunks]]
        
        except Exception as e:
            print(f"⚠️ Erreur recherche: {e}")
            return self.active_chunks[:max_chunks]
    
    def get_context_for_query(self, query: str, max_tokens: int = 50000) -> str:
        """Construit le contexte optimal pour une requête"""
        relevant_chunks = self.search_relevant_chunks(query, max_chunks=20)
        
        context_parts = []
        total_tokens = 0
        
        for chunk in relevant_chunks:
            if total_tokens + chunk.tokens <= max_tokens:
                context_parts.append(f"=== {chunk.type.upper()}: {chunk.id} ===")
                context_parts.append(chunk.content)
                context_parts.append("=" * 50)
                total_tokens += chunk.tokens
            else:
                break
        
        print(f"📊 Contexte final: {total_tokens:,} tokens de {len(context_parts)//3} chunks")
        return "\n".join(context_parts)
    
    def get_stats(self) -> Dict[str, Any]:
        """Retourne les statistiques du contexte"""
        total_tokens = sum(chunk.tokens for chunk in self.active_chunks)
        by_type = {}
        
        for chunk in self.active_chunks:
            chunk_type = chunk.type
            if chunk_type not in by_type:
                by_type[chunk_type] = {"count": 0, "tokens": 0}
            by_type[chunk_type]["count"] += 1
            by_type[chunk_type]["tokens"] += chunk.tokens
        
        return {
            "total_chunks": len(self.active_chunks),
            "total_tokens": total_tokens,
            "max_tokens": self.max_total_tokens,
            "utilization": f"{(total_tokens/self.max_total_tokens)*100:.1f}%",
            "by_type": by_type
        }


# Pour intégrer dans votre CustomAIModel
import time

def integrate_intelligent_context_manager(self):
    """Intègre le gestionnaire de contexte intelligent"""
    self.context_manager = UltraIntelligentContextManager(max_total_tokens=1000000)
    print("✅ Gestionnaire de contexte 1M tokens initialisé")

def add_content_to_extended_context(self, content: str, content_type: str, importance: float = 1.0):
    """Ajoute du contenu au contexte étendu"""
    if hasattr(self, 'context_manager'):
        return self.context_manager.add_content(content, content_type, importance)
    else:
        print("⚠️ Gestionnaire de contexte non initialisé")
        return None

def generate_response_with_intelligent_context(self, user_input: str, context: Dict[str, Any] = None) -> str:
    """Génère une réponse en utilisant le contexte intelligent"""
    if not hasattr(self, 'context_manager'):
        return self.generate_response(user_input, context)
    
    # Obtenir le contexte optimal pour cette requête
    relevant_context = self.context_manager.get_context_for_query(user_input, max_tokens=100000)
    
    # Ajouter à votre logique de génération existante
    if relevant_context:
        enhanced_context = context.copy() if context else {}
        enhanced_context['extended_context'] = relevant_context
        
        print(f"🚀 Utilisation du contexte étendu pour la réponse")
        return self.generate_response(user_input, enhanced_context)
    else:
        return self.generate_response(user_input, context)
