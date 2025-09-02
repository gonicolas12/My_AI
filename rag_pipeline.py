#!/usr/bin/env python3
"""
🔍 Pipeline RAG (Retrieval-Augmented Generation) - My_AI Project
Prototype complet avec chunking intelligent et index FAISS
"""

import os
import sys
import json
import time
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
from datetime import datetime
import hashlib
import pickle
from dataclasses import dataclass
from abc import ABC, abstractmethod

# Ajout du path pour imports locaux
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Imports conditionnels avec fallbacks
try:
    import faiss
    FAISS_AVAILABLE = True
except ImportError:
    FAISS_AVAILABLE = False
    print("⚠️ FAISS non installé - utilisation du mode fallback")

try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    print("⚠️ sentence-transformers non installé - utilisation embeddings simples")

from models.custom_ai_model import CustomAIModel
from models.conversation_memory import ConversationMemory
from utils.logger import setup_logger

@dataclass
class Document:
    """Représentation d'un document dans le système RAG"""
    id: str
    content: str
    metadata: Dict[str, Any]
    embedding: Optional[np.ndarray] = None
    chunks: List['DocumentChunk'] = None
    
    def __post_init__(self):
        if self.chunks is None:
            self.chunks = []

@dataclass
class DocumentChunk:
    """Chunk d'un document avec ses métadonnées"""
    id: str
    content: str
    document_id: str
    start_pos: int
    end_pos: int
    embedding: Optional[np.ndarray] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

class ChunkingStrategy(ABC):
    """Interface pour les stratégies de chunking"""
    
    @abstractmethod
    def chunk_text(self, text: str, max_chunk_size: int = 2048) -> List[str]:
        """Divise le texte en chunks"""
        pass

class SemanticChunker(ChunkingStrategy):
    """Chunking basé sur la sémantique (paragraphes, phrases)"""
    
    def chunk_text(self, text: str, max_chunk_size: int = 2048) -> List[str]:
        """Divise intelligemment par paragraphes et phrases"""
        # Séparer par paragraphes d'abord
        paragraphs = text.split('\n\n')
        chunks = []
        current_chunk = ""
        
        for paragraph in paragraphs:
            # Si le paragraphe est trop long, le diviser par phrases
            if len(paragraph) > max_chunk_size:
                sentences = self._split_sentences(paragraph)
                
                for sentence in sentences:
                    if len(current_chunk + sentence) <= max_chunk_size:
                        current_chunk += sentence + " "
                    else:
                        if current_chunk.strip():
                            chunks.append(current_chunk.strip())
                        current_chunk = sentence + " "
            else:
                # Ajouter le paragraphe au chunk actuel
                if len(current_chunk + paragraph) <= max_chunk_size:
                    current_chunk += paragraph + "\n\n"
                else:
                    if current_chunk.strip():
                        chunks.append(current_chunk.strip())
                    current_chunk = paragraph + "\n\n"
        
        # Ajouter le dernier chunk
        if current_chunk.strip():
            chunks.append(current_chunk.strip())
        
        return chunks
    
    def _split_sentences(self, text: str) -> List[str]:
        """Divise un texte en phrases de manière intelligente"""
        import re
        # Pattern pour détecter les fins de phrases
        sentence_endings = re.compile(r'[.!?]+\s+')
        sentences = sentence_endings.split(text)
        return [s.strip() for s in sentences if s.strip()]

class OverlapChunker(ChunkingStrategy):
    """Chunking avec chevauchement pour préserver le contexte"""
    
    def __init__(self, overlap_ratio: float = 0.2):
        self.overlap_ratio = overlap_ratio
    
    def chunk_text(self, text: str, max_chunk_size: int = 2048) -> List[str]:
        """Divise avec chevauchement"""
        words = text.split()
        chunks = []
        
        overlap_size = int(max_chunk_size * self.overlap_ratio)
        step_size = max_chunk_size - overlap_size
        
        for i in range(0, len(words), step_size):
            chunk_words = words[i:i + max_chunk_size]
            if chunk_words:
                chunks.append(' '.join(chunk_words))
        
        return chunks

class EmbeddingGenerator:
    """Générateur d'embeddings avec fallbacks"""
    
    def __init__(self):
        self.model = None
        self.embedding_dim = 384  # Dimension par défaut
        
        if SENTENCE_TRANSFORMERS_AVAILABLE:
            try:
                self.model = SentenceTransformer('all-MiniLM-L6-v2')
                self.embedding_dim = self.model.get_sentence_embedding_dimension()
                print(f"✅ Modèle d'embedding chargé: {self.embedding_dim}D")
            except Exception as e:
                print(f"⚠️ Erreur chargement sentence-transformers: {e}")
                self.model = None
    
    def generate_embedding(self, text: str) -> np.ndarray:
        """Génère un embedding pour le texte"""
        if self.model:
            return self.model.encode([text])[0]
        else:
            # Fallback: embedding simple basé sur les mots
            return self._simple_text_embedding(text)
    
    def generate_batch_embeddings(self, texts: List[str]) -> np.ndarray:
        """Génère des embeddings en batch pour efficacité"""
        if self.model:
            return self.model.encode(texts)
        else:
            return np.array([self._simple_text_embedding(text) for text in texts])
    
    def _simple_text_embedding(self, text: str) -> np.ndarray:
        """Embedding simple basé sur hash et statistiques du texte"""
        # Créer un vecteur basé sur les caractéristiques du texte
        features = []
        
        # Longueur du texte (normalisée)
        features.append(min(len(text) / 1000, 1.0))
        
        # Nombre de mots (normalisé)
        words = text.split()
        features.append(min(len(words) / 100, 1.0))
        
        # Hash du texte pour représentation unique
        text_hash = hashlib.md5(text.encode()).hexdigest()
        hash_features = [int(text_hash[i:i+2], 16) / 255.0 for i in range(0, min(32, len(text_hash)), 2)]
        features.extend(hash_features)
        
        # Compléter avec des zéros si nécessaire
        while len(features) < self.embedding_dim:
            features.append(0.0)
        
        return np.array(features[:self.embedding_dim], dtype=np.float32)

class VectorStore:
    """Store de vecteurs avec FAISS ou fallback"""
    
    def __init__(self, dimension: int = 384):
        self.dimension = dimension
        self.index = None
        self.documents = {}  # id -> Document
        self.chunks = {}     # chunk_id -> DocumentChunk
        
        if FAISS_AVAILABLE:
            # Index FAISS pour recherche rapide
            self.index = faiss.IndexFlatIP(dimension)  # Inner Product pour similarité cosinus
            print(f"✅ Index FAISS initialisé: {dimension}D")
        else:
            # Fallback: stockage simple en mémoire
            self.vectors = []
            self.vector_ids = []
            print(f"⚠️ Mode fallback activé (pas de FAISS)")
    
    def add_document(self, document: Document):
        """Ajoute un document avec ses chunks à l'index"""
        self.documents[document.id] = document
        
        # Ajouter les chunks à l'index
        if document.chunks:
            chunk_vectors = []
            chunk_ids = []
            
            for chunk in document.chunks:
                if chunk.embedding is not None:
                    self.chunks[chunk.id] = chunk
                    chunk_vectors.append(chunk.embedding)
                    chunk_ids.append(chunk.id)
            
            if chunk_vectors:
                vectors_array = np.array(chunk_vectors, dtype=np.float32)
                
                if FAISS_AVAILABLE and self.index:
                    # Normaliser pour la similarité cosinus
                    faiss.normalize_L2(vectors_array)
                    self.index.add(vectors_array)
                else:
                    # Mode fallback
                    self.vectors.extend(vectors_array)
                    self.vector_ids.extend(chunk_ids)
    
    def search(self, query_embedding: np.ndarray, k: int = 5) -> List[Tuple[str, float]]:
        """Recherche les k chunks les plus similaires"""
        if FAISS_AVAILABLE and self.index and self.index.ntotal > 0:
            # Recherche FAISS
            query_vector = query_embedding.reshape(1, -1).astype(np.float32)
            faiss.normalize_L2(query_vector)
            
            scores, indices = self.index.search(query_vector, min(k, self.index.ntotal))
            
            results = []
            for i, (score, idx) in enumerate(zip(scores[0], indices[0])):
                if idx >= 0:  # FAISS retourne -1 pour les résultats invalides
                    chunk_id = list(self.chunks.keys())[idx]
                    results.append((chunk_id, float(score)))
            
            return results
        else:
            # Mode fallback: similarité cosinus simple
            if not self.vectors:
                return []
            
            similarities = []
            for i, vector in enumerate(self.vectors):
                sim = np.dot(query_embedding, vector) / (
                    np.linalg.norm(query_embedding) * np.linalg.norm(vector)
                )
                similarities.append((self.vector_ids[i], float(sim)))
            
            # Trier par similarité décroissante
            similarities.sort(key=lambda x: x[1], reverse=True)
            return similarities[:k]
    
    def get_chunk(self, chunk_id: str) -> Optional[DocumentChunk]:
        """Récupère un chunk par son ID"""
        return self.chunks.get(chunk_id)
    
    def get_document(self, doc_id: str) -> Optional[Document]:
        """Récupère un document par son ID"""
        return self.documents.get(doc_id)

class RAGPipeline:
    """Pipeline RAG complet pour My_AI"""
    
    def __init__(self, 
                 chunk_size: int = 2048,
                 chunk_overlap: float = 0.2,
                 max_retrieved_chunks: int = 10,
                 chunking_strategy: str = "semantic"):
        
        self.chunk_size = chunk_size
        self.max_retrieved_chunks = max_retrieved_chunks
        self.logger = setup_logger("RAGPipeline")
        
        # Initialisation des composants
        self.embedding_generator = EmbeddingGenerator()
        self.vector_store = VectorStore(self.embedding_generator.embedding_dim)
        
        # Stratégie de chunking
        if chunking_strategy == "semantic":
            self.chunker = SemanticChunker()
        elif chunking_strategy == "overlap":
            self.chunker = OverlapChunker(chunk_overlap)
        else:
            self.chunker = SemanticChunker()  # Par défaut
        
        # Modèle IA pour génération
        self.ai_model = CustomAIModel(ConversationMemory())
        
        print(f"🚀 Pipeline RAG initialisé:")
        print(f"   • Chunk size: {chunk_size}")
        print(f"   • Strategy: {chunking_strategy}")
        print(f"   • Max retrieved: {max_retrieved_chunks}")
        print(f"   • Embedding dim: {self.embedding_generator.embedding_dim}")
    
    def add_document(self, content: str, metadata: Dict[str, Any] = None) -> str:
        """Ajoute un document au système RAG"""
        if metadata is None:
            metadata = {}
        
        # Générer un ID unique pour le document
        doc_id = hashlib.md5(content.encode()).hexdigest()[:12]
        
        print(f"📄 Ajout document {doc_id}...")
        
        # Chunking intelligent
        chunks_text = self.chunker.chunk_text(content, self.chunk_size)
        print(f"   • {len(chunks_text)} chunks générés")
        
        # Créer les chunks avec embeddings
        chunks = []
        chunk_texts_for_batch = []
        
        for i, chunk_text in enumerate(chunks_text):
            chunk_id = f"{doc_id}_chunk_{i}"
            chunk = DocumentChunk(
                id=chunk_id,
                content=chunk_text,
                document_id=doc_id,
                start_pos=content.find(chunk_text),
                end_pos=content.find(chunk_text) + len(chunk_text),
                metadata={
                    "chunk_index": i,
                    "total_chunks": len(chunks_text),
                    **metadata
                }
            )
            chunks.append(chunk)
            chunk_texts_for_batch.append(chunk_text)
        
        # Générer les embeddings en batch pour l'efficacité
        print(f"   • Génération des embeddings...")
        embeddings = self.embedding_generator.generate_batch_embeddings(chunk_texts_for_batch)
        
        # Assigner les embeddings aux chunks
        for chunk, embedding in zip(chunks, embeddings):
            chunk.embedding = embedding
        
        # Créer le document
        document = Document(
            id=doc_id,
            content=content,
            metadata=metadata,
            chunks=chunks
        )
        
        # Ajouter au vector store
        self.vector_store.add_document(document)
        
        print(f"   ✅ Document {doc_id} ajouté avec {len(chunks)} chunks")
        return doc_id
    
    def add_text(self, text: str, doc_id: str = None, metadata: Dict[str, Any] = None) -> str:
        """Alias pour add_document - compatibilité avec validation"""
        if metadata is None:
            metadata = {}
        if doc_id:
            metadata["custom_id"] = doc_id
        return self.add_document(text, metadata)
    
    def search(self, query: str, top_k: int = None) -> List[str]:
        """Recherche et retourne les textes pertinents - compatibilité avec validation"""
        if top_k is None:
            top_k = self.max_retrieved_chunks
        
        chunks = self.retrieve(query, top_k)
        return [chunk.content for chunk in chunks]
    
    def add_documents_from_directory(self, directory_path: str, 
                                   file_extensions: List[str] = ['.txt', '.md', '.py']) -> List[str]:
        """Ajoute tous les documents d'un dossier"""
        directory = Path(directory_path)
        added_docs = []
        
        print(f"📁 Traitement du dossier: {directory}")
        
        for file_path in directory.rglob('*'):
            if file_path.is_file() and file_path.suffix.lower() in file_extensions:
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    metadata = {
                        "file_path": str(file_path),
                        "file_name": file_path.name,
                        "file_type": file_path.suffix,
                        "file_size": len(content),
                        "added_at": datetime.now().isoformat()
                    }
                    
                    doc_id = self.add_document(content, metadata)
                    added_docs.append(doc_id)
                    
                except Exception as e:
                    print(f"❌ Erreur traitement {file_path}: {str(e)}")
        
        print(f"✅ {len(added_docs)} documents ajoutés depuis {directory}")
        return added_docs
    
    def retrieve(self, query: str, k: int = None) -> List[DocumentChunk]:
        """Récupère les chunks les plus pertinents pour une requête"""
        if k is None:
            k = self.max_retrieved_chunks
        
        # Générer l'embedding de la requête
        query_embedding = self.embedding_generator.generate_embedding(query)
        
        # Rechercher dans le vector store
        search_results = self.vector_store.search(query_embedding, k)
        
        # Récupérer les chunks
        retrieved_chunks = []
        for chunk_id, score in search_results:
            chunk = self.vector_store.get_chunk(chunk_id)
            if chunk:
                # Ajouter le score de similarité aux métadonnées
                chunk.metadata["similarity_score"] = score
                retrieved_chunks.append(chunk)
        
        return retrieved_chunks
    
    def generate_response(self, query: str, context: Dict[str, Any] = None) -> str:
        """Génère une réponse augmentée par la récupération"""
        if context is None:
            context = {}
        
        print(f"🤖 Génération de réponse RAG pour: {query[:50]}...")
        
        # 1. Récupération des chunks pertinents
        retrieved_chunks = self.retrieve(query)
        
        if not retrieved_chunks:
            print("   ⚠️ Aucun chunk pertinent trouvé - réponse standard")
            return self.ai_model.generate_response(query, context)
        
        # 2. Construction du contexte augmenté
        augmented_context = self._build_augmented_context(query, retrieved_chunks)
        
        # 3. Génération de la réponse avec contexte enrichi
        enhanced_prompt = self._build_enhanced_prompt(query, augmented_context)
        
        print(f"   • {len(retrieved_chunks)} chunks récupérés")
        print(f"   • Contexte augmenté: {len(augmented_context)} chars")
        
        # Ajouter les informations RAG au contexte
        rag_context = {
            **context,
            "rag_enabled": True,
            "retrieved_chunks": len(retrieved_chunks),
            "augmented_context": augmented_context[:500] + "..." if len(augmented_context) > 500 else augmented_context
        }
        
        response = self.ai_model.generate_response(enhanced_prompt, rag_context)
        
        # Ajouter métadonnées sur les sources
        if response:
            sources_info = self._build_sources_info(retrieved_chunks)
            response += f"\n\n📚 **Sources consultées:** {sources_info}"
        
        return response
    
    def _build_augmented_context(self, query: str, chunks: List[DocumentChunk]) -> str:
        """Construit le contexte augmenté à partir des chunks"""
        context_parts = []
        
        for i, chunk in enumerate(chunks):
            similarity = chunk.metadata.get("similarity_score", 0)
            doc_name = chunk.metadata.get("file_name", "Document")
            
            context_part = f"[Source {i+1} - {doc_name} (sim: {similarity:.2f})]:\n{chunk.content}\n"
            context_parts.append(context_part)
        
        return "\n---\n".join(context_parts)
    
    def _build_enhanced_prompt(self, original_query: str, augmented_context: str) -> str:
        """Construit le prompt enrichi pour le modèle"""
        prompt = f"""Contexte récupéré pertinent:
{augmented_context}

---

Question de l'utilisateur: {original_query}

Instructions: Utilise le contexte fourni ci-dessus pour enrichir ta réponse. Si le contexte contient des informations pertinentes, intègre-les naturellement. Si le contexte n'est pas pertinent, réponds normalement mais mentionne que tu n'as pas trouvé d'informations spécifiques dans la base de connaissances."""
        
        return prompt
    
    def _build_sources_info(self, chunks: List[DocumentChunk]) -> str:
        """Construit l'information sur les sources utilisées"""
        sources = set()
        for chunk in chunks:
            file_name = chunk.metadata.get("file_name", "Document")
            sources.add(file_name)
        
        return ", ".join(list(sources)[:3])  # Limiter à 3 sources
    
    def save_index(self, save_path: str):
        """Sauvegarde l'index et les métadonnées"""
        save_dir = Path(save_path)
        save_dir.mkdir(parents=True, exist_ok=True)
        
        # Sauvegarder l'index FAISS
        if FAISS_AVAILABLE and self.index:
            faiss.write_index(self.index, str(save_dir / "faiss_index.bin"))
        
        # Sauvegarder les métadonnées
        metadata = {
            "documents": {doc_id: {
                "id": doc.id,
                "metadata": doc.metadata,
                "content_length": len(doc.content),
                "chunks_count": len(doc.chunks)
            } for doc_id, doc in self.vector_store.documents.items()},
            "chunks": {chunk_id: {
                "id": chunk.id,
                "document_id": chunk.document_id,
                "metadata": chunk.metadata,
                "content_length": len(chunk.content)
            } for chunk_id, chunk in self.vector_store.chunks.items()},
            "config": {
                "chunk_size": self.chunk_size,
                "embedding_dim": self.embedding_generator.embedding_dim,
                "total_documents": len(self.vector_store.documents),
                "total_chunks": len(self.vector_store.chunks)
            }
        }
        
        with open(save_dir / "metadata.json", 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        
        print(f"💾 Index sauvegardé dans: {save_dir}")
    
    def load_index(self, load_path: str):
        """Charge un index sauvegardé"""
        load_dir = Path(load_path)
        
        # Charger l'index FAISS
        faiss_path = load_dir / "faiss_index.bin"
        if FAISS_AVAILABLE and faiss_path.exists():
            self.index = faiss.read_index(str(faiss_path))
        
        # Charger les métadonnées
        metadata_path = load_dir / "metadata.json"
        if metadata_path.exists():
            with open(metadata_path, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
            
            # Reconstruire les structures de données (sans le contenu complet)
            print(f"📚 Index chargé: {len(metadata['documents'])} docs, {len(metadata['chunks'])} chunks")
        
        print(f"✅ Index chargé depuis: {load_dir}")

class RAGOptimizer:
    """Optimiseur pour le pipeline RAG"""
    
    def __init__(self, rag_pipeline: RAGPipeline):
        self.rag = rag_pipeline
        self.optimization_results = {}
    
    def optimize_chunk_size(self, test_queries: List[str], chunk_sizes: List[int] = [256, 512, 1024, 2048]) -> Dict[str, Any]:
        """Optimise la taille des chunks"""
        print("🔧 Optimisation de la taille des chunks...")
        
        results = {}
        
        for chunk_size in chunk_sizes:
            print(f"   🧪 Test chunk size: {chunk_size}")
            
            # Créer un nouveau pipeline avec cette taille
            test_rag = RAGPipeline(chunk_size=chunk_size)
            
            # Ajouter des documents de test
            test_doc = "L'intelligence artificielle " * 200
            test_rag.add_document(test_doc, {"test": True})
            
            # Tester les performances
            total_time = 0
            total_quality = 0
            
            for query in test_queries:
                start_time = time.time()
                response = test_rag.generate_response(query)
                end_time = time.time()
                
                total_time += end_time - start_time
                total_quality += len(response.split()) if response else 0
            
            avg_time = total_time / len(test_queries) if test_queries else 0
            avg_quality = total_quality / len(test_queries) if test_queries else 0
            
            results[chunk_size] = {
                "avg_response_time": avg_time,
                "avg_response_quality": avg_quality,
                "efficiency_score": avg_quality / avg_time if avg_time > 0 else 0
            }
            
            print(f"      ⏱️ Temps moyen: {avg_time:.3f}s")
        
        # Trouver la taille optimale
        best_size = max(results.keys(), key=lambda x: results[x]["efficiency_score"])
        
        return {
            "results": results,
            "optimal_chunk_size": best_size,
            "optimization_summary": f"Taille optimale: {best_size} tokens"
        }
    
    def benchmark_retrieval_speed(self, num_queries: int = 100) -> Dict[str, Any]:
        """Benchmark de la vitesse de récupération"""
        print(f"⚡ Benchmark vitesse de récupération ({num_queries} requêtes)...")
        
        # Générer des requêtes de test
        test_queries = [f"Question de test numéro {i} sur l'intelligence artificielle" 
                       for i in range(num_queries)]
        
        retrieval_times = []
        
        for i, query in enumerate(test_queries):
            start_time = time.time()
            chunks = self.rag.retrieve(query)
            end_time = time.time()
            
            retrieval_times.append({
                "query_id": i,
                "retrieval_time": end_time - start_time,
                "chunks_found": len(chunks)
            })
            
            if (i + 1) % 20 == 0:
                print(f"   {i + 1}/{num_queries} requêtes traitées")
        
        # Statistiques
        times = [r["retrieval_time"] for r in retrieval_times]
        
        return {
            "total_queries": num_queries,
            "avg_retrieval_time": sum(times) / len(times),
            "min_retrieval_time": min(times),
            "max_retrieval_time": max(times),
            "queries_per_second": num_queries / sum(times) if sum(times) > 0 else 0,
            "detailed_times": retrieval_times
        }

def create_demo_rag_system() -> RAGPipeline:
    """Crée un système RAG de démonstration avec données d'exemple"""
    print("🎬 Création du système RAG de démonstration...")
    
    # Initialiser le pipeline
    rag = RAGPipeline(chunk_size=512, chunking_strategy="semantic")
    
    # Ajouter des documents d'exemple
    demo_documents = {
        "python_guide": """
        # Guide Python Avancé
        
        Python est un langage de programmation puissant et polyvalent. Voici les concepts clés:
        
        ## Variables et Types
        Les variables en Python sont dynamiquement typées. Vous pouvez stocker des entiers, des chaînes, des listes, et des dictionnaires.
        
        ## Fonctions
        Les fonctions permettent de réutiliser le code. Utilisez 'def' pour définir une fonction.
        
        ## Classes et Objets
        Python supporte la programmation orientée objet avec des classes et des objets.
        
        ## Modules et Packages
        Organisez votre code avec des modules et des packages pour une meilleure structure.
        """,
        
        "ai_concepts": """
        # Concepts d'Intelligence Artificielle
        
        L'IA moderne repose sur plusieurs paradigmes fondamentaux:
        
        ## Machine Learning
        L'apprentissage automatique permet aux machines d'apprendre à partir de données sans être explicitement programmées.
        
        ## Deep Learning
        Les réseaux de neurones profonds modélisent des patterns complexes dans les données.
        
        ## Natural Language Processing
        Le traitement du langage naturel permet aux machines de comprendre et générer du texte humain.
        
        ## Computer Vision
        La vision par ordinateur analyse et interprète les images et vidéos.
        """,
        
        "optimization_techniques": """
        # Techniques d'Optimisation IA
        
        ## Quantization
        La quantification réduit la précision des poids pour diminuer la taille du modèle et accélérer l'inférence.
        
        ## Pruning
        L'élagage supprime les connexions peu importantes dans les réseaux de neurones.
        
        ## Knowledge Distillation
        La distillation de connaissances transfère les connaissances d'un grand modèle vers un modèle plus petit.
        
        ## FlashAttention
        FlashAttention optimise le mécanisme d'attention pour réduire la complexité mémoire.
        """
    }
    
    # Ajouter chaque document
    for doc_name, content in demo_documents.items():
        rag.add_document(content, {"document_type": doc_name, "demo": True})
    
    return rag

def run_rag_demo():
    """Démonstration complète du système RAG"""
    print("🎯 Démonstration du Pipeline RAG")
    print("=" * 50)
    
    # Créer le système de démonstration
    rag = create_demo_rag_system()
    
    # Requêtes de test
    demo_queries = [
        "Comment définir une fonction en Python ?",
        "Qu'est-ce que le deep learning ?",
        "Explique-moi les techniques d'optimisation IA",
        "Comment organiser le code Python ?",
        "Qu'est-ce que FlashAttention ?"
    ]
    
    print("\n📋 Test avec requêtes de démonstration:")
    print("-" * 50)
    
    for i, query in enumerate(demo_queries, 1):
        print(f"\n🔍 Requête {i}: {query}")
        
        start_time = time.time()
        response = rag.generate_response(query)
        end_time = time.time()
        
        print(f"⏱️ Temps de réponse: {end_time - start_time:.3f}s")
        print(f"📝 Réponse (extrait): {response[:200]}...")
        
        # Montrer les chunks récupérés
        chunks = rag.retrieve(query, k=3)
        print(f"📚 Chunks utilisés:")
        for j, chunk in enumerate(chunks[:2]):  # Montrer les 2 premiers
            score = chunk.metadata.get("similarity_score", 0)
            source = chunk.metadata.get("document_type", "Unknown")
            print(f"   {j+1}. {source} (score: {score:.3f}) - {chunk.content[:100]}...")
    
    # Sauvegarder l'index de démo
    rag.save_index("rag_demo_index")
    
    return rag

def benchmark_rag_vs_standard():
    """Compare les performances RAG vs réponses standard"""
    print("\n⚔️ Benchmark RAG vs Standard")
    print("=" * 50)
    
    # Créer les deux systèmes
    rag_system = create_demo_rag_system()
    standard_model = CustomAIModel(ConversationMemory())
    
    test_queries = [
        "Comment optimiser un modèle IA ?",
        "Explique-moi les classes Python",
        "Qu'est-ce que la quantization ?",
        "Comment faire du machine learning ?"
    ]
    
    results = {
        "rag_performance": [],
        "standard_performance": [],
        "quality_comparison": []
    }
    
    for query in test_queries:
        print(f"\n🧪 Test: {query[:30]}...")
        
        # Test RAG
        start_time = time.time()
        rag_response = rag_system.generate_response(query)
        rag_time = time.time() - start_time
        
        # Test Standard
        start_time = time.time()
        standard_response = standard_model.generate_response(query, {})
        standard_time = time.time() - start_time
        
        results["rag_performance"].append(rag_time)
        results["standard_performance"].append(standard_time)
        
        # Comparaison qualitative simple
        quality_score = {
            "rag_length": len(rag_response.split()) if rag_response else 0,
            "standard_length": len(standard_response.split()) if standard_response else 0,
            "rag_time": rag_time,
            "standard_time": standard_time
        }
        results["quality_comparison"].append(quality_score)
        
        print(f"   RAG: {rag_time:.3f}s, {len(rag_response.split()) if rag_response else 0} mots")
        print(f"   Standard: {standard_time:.3f}s, {len(standard_response.split()) if standard_response else 0} mots")
    
    # Résumé des performances
    avg_rag_time = sum(results["rag_performance"]) / len(results["rag_performance"])
    avg_standard_time = sum(results["standard_performance"]) / len(results["standard_performance"])
    
    print(f"\n📊 RÉSUMÉ COMPARATIF:")
    print(f"   RAG moyen: {avg_rag_time:.3f}s")
    print(f"   Standard moyen: {avg_standard_time:.3f}s")
    print(f"   Différence: {((avg_rag_time - avg_standard_time) / avg_standard_time * 100):+.1f}%")
    
    return results

def main():
    """Point d'entrée principal"""
    print("🤖 My_AI - Pipeline RAG v1.0")
    print("=" * 50)
    
    # Vérifier les dépendances
    missing_deps = []
    if not FAISS_AVAILABLE:
        missing_deps.append("faiss-cpu")
    if not SENTENCE_TRANSFORMERS_AVAILABLE:
        missing_deps.append("sentence-transformers")
    
    if missing_deps:
        print(f"⚠️ Dépendances recommandées manquantes: {', '.join(missing_deps)}")
        print("💡 Installation recommandée:")
        print(f"   pip install {' '.join(missing_deps)}")
        print("\n🔄 Fonctionnement en mode fallback...")
    
    # Démonstration RAG
    rag_system = run_rag_demo()
    
    # Benchmark comparatif
    benchmark_results = benchmark_rag_vs_standard()
    
    # Optimisation des paramètres
    print("\n🔧 Optimisation des paramètres...")
    optimizer = RAGOptimizer(rag_system)
    
    optimization_results = optimizer.optimize_chunk_size([
        "Explique Python",
        "Qu'est-ce que l'IA ?",
        "Comment optimiser un modèle ?"
    ])
    
    print(f"✅ Optimisation terminée: {optimization_results['optimal_chunk_size']} tokens optimal")
    
    # Benchmark de vitesse
    speed_benchmark = optimizer.benchmark_retrieval_speed(50)
    print(f"⚡ Vitesse de récupération: {speed_benchmark['queries_per_second']:.1f} requêtes/s")
    
    print(f"\n🎉 Prototype RAG prêt à l'intégration !")
    
    return {
        "rag_system": rag_system,
        "benchmark_results": benchmark_results,
        "optimization_results": optimization_results,
        "speed_benchmark": speed_benchmark
    }

if __name__ == "__main__":
    main()
