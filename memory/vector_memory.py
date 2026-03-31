"""
Vector Memory - Gestionnaire de mémoire vectorielle avec recherche sémantique
Remplace le million_token_context_manager avec de vraies capacités ML
Supporte ChromaDB et FAISS, tokenization correcte (tiktoken), chiffrement AES-256
"""

import hashlib
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import huggingface_hub.constants as _hf_constants
import transformers.utils.hub as _tf_hub

from core.config import get_config

# Import du moniteur de compression et modèles partagés
try:
    from core.compression_monitor import get_compression_monitor
    from core.shared import get_shared_embedding_model, is_embeddings_available

    COMPRESSION_MONITOR_AVAILABLE = True
    EMBEDDINGS_AVAILABLE = is_embeddings_available()
except ImportError:
    COMPRESSION_MONITOR_AVAILABLE = False
    EMBEDDINGS_AVAILABLE = False
    print("⚠️ Compression Monitor ou Embeddings non disponible")

    def get_shared_embedding_model():
        """Fallback si imports échouent"""
        return None

# Note: Le mode offline HuggingFace est géré intelligemment dans core.shared
# Il télécharge automatiquement le modèle au premier lancement si nécessaire

try:
    import chromadb

    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False
    print("⚠️ ChromaDB non disponible. Installez: pip install chromadb")

# [OPTIM] Cross-Encoder pour reranking sémantique fin
# Note: Le chargement effectif est fait dans VectorMemory.__init__
# avec gestion intelligente du mode offline (même stratégie que core.shared)
try:
    from sentence_transformers import CrossEncoder

    CROSSENCODER_AVAILABLE = True
except ImportError:
    CROSSENCODER_AVAILABLE = False
    print("⚠️ CrossEncoder non disponible (sentence-transformers requis)")

try:
    import tiktoken

    TOKENIZER_AVAILABLE = True
except ImportError:
    TOKENIZER_AVAILABLE = False
    print("⚠️ tiktoken non disponible. Installez: pip install tiktoken")

try:
    import base64

    from cryptography.fernet import Fernet

    ENCRYPTION_AVAILABLE = True
except ImportError:
    ENCRYPTION_AVAILABLE = False
    print("⚠️ Cryptography non disponible. Installez: pip install cryptography")


class VectorMemory:
    """
    Gestionnaire de mémoire vectorielle avec recherche sémantique

    Fonctionnalités:
    - Tokenization correcte (tiktoken cl100k_base, compatible Llama 3)
    - Embeddings sémantiques (sentence-transformers)
    - Stockage vectoriel (ChromaDB/FAISS)
    - Chiffrement AES-256 (optionnel)
    - Recherche par similarité cosinus
    """

    def __init__(
        self,
        max_tokens: Optional[int] = None,
        chunk_size: int = 512,
        chunk_overlap: int = 50,
        storage_dir: str = "memory/vector_store",
        enable_encryption: bool = False,
        encryption_key: Optional[str] = None,
    ):
        """
        Initialise le gestionnaire de mémoire vectorielle

        Args:
            max_tokens: Limite maximale de tokens (lit config.yaml par défaut ou 1M)
            chunk_size: Taille des chunks en tokens
            chunk_overlap: Chevauchement entre chunks
            storage_dir: Répertoire de stockage
            enable_encryption: Activer le chiffrement AES-256
            encryption_key: Clé de chiffrement (générée si None)
        """
        if max_tokens is None:
            try:
                # On récupère depuis le config.yaml, 1M par défaut
                max_tokens = get_config().get("ai.max_tokens", 1000000)
            except Exception:
                max_tokens = 1000000

        self.max_tokens = max_tokens
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.current_tokens = 0

        # Configuration du stockage
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        # Chiffrement
        self.enable_encryption = enable_encryption and ENCRYPTION_AVAILABLE
        if self.enable_encryption:
            self._init_encryption(encryption_key)

        # Tokenizer (vrai comptage de tokens via tiktoken - cl100k_base, compatible Llama 3)
        if TOKENIZER_AVAILABLE:
            try:
                self.tokenizer = tiktoken.get_encoding("cl100k_base")
                print("✅ Tokenizer tiktoken (cl100k_base) chargé")
            except Exception as e:
                print(f"⚠️ Erreur chargement tokenizer tiktoken: {e}")
                self.tokenizer = None
        else:
            self.tokenizer = None

        # Modèle d'embeddings partagé (déjà chargé au démarrage dans core.shared)
        self.embedding_model = get_shared_embedding_model()

        # [OPTIM] Cross-Encoder pour reranking sémantique fin (RAG avancé)
        # Stratégie identique à core.shared : offline first, download si nécessaire
        self.reranker = None
        if CROSSENCODER_AVAILABLE:
            self._load_reranker()

        # Base vectorielle ChromaDB
        if CHROMADB_AVAILABLE:
            try:
                self.chroma_client = chromadb.PersistentClient(
                    path=str(self.storage_dir / "chroma_db")
                )

                # Collections pour différents types de données
                self.conversation_collection = (
                    self.chroma_client.get_or_create_collection(
                        name="conversations", metadata={"hnsw:space": "cosine"}
                    )
                )

                self.document_collection = self.chroma_client.get_or_create_collection(
                    name="documents", metadata={"hnsw:space": "cosine"}
                )

                print("✅ ChromaDB initialisé")
            except Exception as e:
                print(f"⚠️ Erreur ChromaDB: {e}")
                self.chroma_client = None
                self.conversation_collection = None
                self.document_collection = None
        else:
            self.chroma_client = None
            self.conversation_collection = None
            self.document_collection = None

        # Métadonnées et statistiques
        self.documents = {}
        self.stats = {
            "documents_added": 0,
            "chunks_created": 0,
            "total_tokens": 0,
            "last_updated": None,
            "encryption_enabled": self.enable_encryption,
        }

        # Moniteur de compression
        if COMPRESSION_MONITOR_AVAILABLE:
            self.compression_monitor = get_compression_monitor()
        else:
            self.compression_monitor = None

        print(f"✅ VectorMemory initialisé (max: {max_tokens:,} tokens)")

    def _load_reranker(self):
        """
        [OPTIM] Charge le CrossEncoder avec gestion offline identique à core.shared.
        1. Essaie en mode offline (cache local)
        2. Si échec, tente le téléchargement (premier lancement)
        3. Si pas de réseau → fallback sans reranking (graceful degradation)
        """
        reranker_model = "cross-encoder/ms-marco-MiniLM-L-6-v2"

        # Étape 1 : essayer depuis le cache (mode offline déjà activé par core.shared)
        try:
            self.reranker = CrossEncoder(reranker_model)
            print("✅ CrossEncoder (ms-marco-MiniLM-L-6-v2) chargé pour reranking")
            return
        except Exception:
            pass

        # Étape 2 : tenter le téléchargement (premier lancement)
        # IMPORTANT: huggingface_hub et transformers stockent le flag offline
        # comme constante au moment de l'import. Changer os.environ ne suffit
        # pas — il faut aussi patcher les constantes internes des modules.
        saved_offline = os.environ.get('HF_HUB_OFFLINE', '0')
        saved_transformers = os.environ.get('TRANSFORMERS_OFFLINE', '0')
        saved_hf_const = None
        saved_tf_const = None
        try:
            saved_hf_const = _hf_constants.HF_HUB_OFFLINE
            saved_tf_const = _tf_hub._is_offline_mode  # pylint: disable=protected-access
            _hf_constants.HF_HUB_OFFLINE = False
            _tf_hub._is_offline_mode = False  # pylint: disable=protected-access
            os.environ['HF_HUB_OFFLINE'] = '0'
            os.environ['TRANSFORMERS_OFFLINE'] = '0'
            print("📥 Téléchargement du CrossEncoder (reranking)... (une seule fois)")
            self.reranker = CrossEncoder(reranker_model)
            print("✅ CrossEncoder téléchargé et prêt (sera en cache)")
        except Exception as e:
            print(f"⚠️ CrossEncoder non disponible (pas de réseau ?): {e}")
            print("   → Le RAG fonctionnera sans reranking (distance cosinus seule)")
            self.reranker = None
        finally:
            # Toujours restaurer le mode offline
            os.environ['HF_HUB_OFFLINE'] = saved_offline
            os.environ['TRANSFORMERS_OFFLINE'] = saved_transformers
            try:
                _hf_constants.HF_HUB_OFFLINE = saved_hf_const
                _tf_hub._is_offline_mode = saved_tf_const  # pylint: disable=protected-access
            except Exception:
                pass

    def _init_encryption(self, encryption_key: Optional[str] = None):
        """Initialise le système de chiffrement AES-256"""
        if not ENCRYPTION_AVAILABLE:
            print("⚠️ Chiffrement désactivé: cryptography non disponible")
            self.enable_encryption = False
            return

        key_file = self.storage_dir / ".encryption_key"

        if encryption_key:
            # Utiliser la clé fournie
            key_bytes = encryption_key.encode()
        elif key_file.exists():
            # Charger la clé existante
            with open(key_file, "rb") as f:
                key_bytes = f.read()
        else:
            # Générer une nouvelle clé
            key_bytes = Fernet.generate_key()
            with open(key_file, "wb") as f:
                f.write(key_bytes)
            print("🔐 Nouvelle clé de chiffrement générée")

        self.cipher = Fernet(key_bytes)
        print("✅ Chiffrement AES-256 activé")

    def _encrypt(self, text: str) -> str:
        """Chiffre un texte"""
        if not self.enable_encryption:
            return text
        encrypted = self.cipher.encrypt(text.encode())
        return base64.b64encode(encrypted).decode()

    def _decrypt(self, encrypted_text: str) -> str:
        """Déchiffre un texte"""
        if not self.enable_encryption:
            return encrypted_text
        encrypted = base64.b64decode(encrypted_text.encode())
        return self.cipher.decrypt(encrypted).decode()

    def count_tokens(self, text: str) -> int:
        """
        Compte le nombre réel de tokens (pas de mots)

        Args:
            text: Texte à analyser

        Returns:
            Nombre de tokens
        """
        if self.tokenizer:
            # Vrai comptage avec tiktoken
            tokens = self.tokenizer.encode(text)
            return len(tokens)
        else:
            # Fallback: approximation (1 mot ≈ 0.75 tokens)
            words = text.split()
            return int(len(words) * 0.75)

    def split_into_chunks(self, text: str) -> List[str]:
        """
        Divise le texte en chunks avec chevauchement

        Args:
            text: Texte à diviser

        Returns:
            Liste de chunks
        """
        if self.tokenizer:
            # Découpage basé sur les vrais tokens (tiktoken)
            tokens = self.tokenizer.encode(text)
            chunks = []

            start = 0
            while start < len(tokens):
                end = min(start + self.chunk_size, len(tokens))
                chunk_tokens = tokens[start:end]
                chunk_text = self.tokenizer.decode(chunk_tokens)
                chunks.append(chunk_text)

                # Avancer avec chevauchement
                start += self.chunk_size - self.chunk_overlap

            return chunks
        else:
            # Fallback: découpage par mots
            words = text.split()
            chunks = []
            word_chunk_size = int(self.chunk_size / 0.75)  # Approximation
            word_overlap = int(self.chunk_overlap / 0.75)

            start = 0
            while start < len(words):
                end = min(start + word_chunk_size, len(words))
                chunk_words = words[start:end]
                chunks.append(" ".join(chunk_words))
                start += word_chunk_size - word_overlap

            return chunks

    def add_document(
        self,
        content: str,
        document_name: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Ajoute un document à la mémoire vectorielle

        Args:
            content: Contenu du document
            document_name: Nom du document
            metadata: Métadonnées additionnelles

        Returns:
            Informations sur l'ajout
        """
        try:
            # Générer ID unique
            doc_id = self._generate_document_id(content, document_name)

            # Vérifier doublon
            if doc_id in self.documents:
                return {
                    "document_id": doc_id,
                    "status": "duplicate",
                    "chunks_created": 0,
                    "tokens_added": 0,
                }

            # Compter tokens
            total_tokens = self.count_tokens(content)

            # Vérifier capacité
            if self.current_tokens + total_tokens > self.max_tokens:
                self._cleanup_old_documents(total_tokens)

            # Diviser en chunks
            chunks = self.split_into_chunks(content)

            # Analyser la compression avec le moniteur (après création des chunks)
            compression_analysis = None
            if self.compression_monitor:
                compression_analysis = self.compression_monitor.analyze_compression(
                    original_text=content,
                    chunks=chunks,
                    document_name=document_name,
                    content_type=metadata.get("type", "text") if metadata else "text",
                    metadata=metadata
                )

            # Générer embeddings et stocker
            chunk_ids = []
            embeddings_list = []

            for i, chunk_text in enumerate(chunks):
                chunk_id = f"{doc_id}_chunk_{i}"
                chunk_tokens = self.count_tokens(chunk_text)

                # Chiffrer si activé
                stored_text = (
                    self._encrypt(chunk_text) if self.enable_encryption else chunk_text
                )

                # Générer embedding
                if self.embedding_model:
                    embedding = self.embedding_model.encode(chunk_text).tolist()
                    embeddings_list.append(embedding)
                else:
                    embedding = None

                # Stocker dans ChromaDB
                if self.document_collection and embedding:
                    chunk_metadata = {
                        "document_id": doc_id,
                        "document_name": document_name,
                        "chunk_index": i,
                        "tokens": chunk_tokens,
                        "created": datetime.now().isoformat(),
                        "encrypted": self.enable_encryption,
                        **(metadata or {}),
                    }

                    self.document_collection.add(
                        ids=[chunk_id],
                        embeddings=[embedding],
                        documents=[stored_text],
                        metadatas=[chunk_metadata],
                    )

                chunk_ids.append(chunk_id)
                self.current_tokens += chunk_tokens

            # Enregistrer métadonnées document
            self.documents[doc_id] = {
                "name": document_name or f"Document_{len(self.documents)}",
                "chunks": chunk_ids,
                "total_tokens": total_tokens,
                "created": datetime.now().isoformat(),
            }

            # Mettre à jour statistiques
            self.stats["documents_added"] += 1
            self.stats["chunks_created"] += len(chunks)
            self.stats["total_tokens"] = self.current_tokens
            self.stats["last_updated"] = datetime.now().isoformat()

            # Préparer le résultat
            result = {
                "document_id": doc_id,
                "document_name": document_name,
                "chunks_created": len(chunks),
                "tokens_added": total_tokens,
                "status": "success",
            }

            # Ajouter les métriques de compression si disponibles
            if compression_analysis:
                result["compression"] = {
                    "ratio": compression_analysis["compression_ratio"],
                    "ratio_formatted": compression_analysis["compression_ratio_formatted"],
                    "efficiency": compression_analysis["efficiency"],
                    "quality_score": compression_analysis["quality_score"]
                }

            return result

        except Exception as e:
            return {"error": str(e), "status": "error"}

    def search_similar(
        self, query: str, n_results: int = 5, collection_type: str = "document",
        rerank: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        Recherche sémantique par similarité avec reranking optionnel

        Args:
            query: Requête de recherche
            n_results: Nombre de résultats finaux souhaités
            collection_type: "document" ou "conversation"
            rerank: Si True et CrossEncoder dispo, sur-échantillonne puis reranke

        Returns:
            Liste de résultats avec scores
        """
        if not self.embedding_model:
            print("⚠️ Recherche sémantique non disponible (embeddings désactivés)")
            return []

        collection = (
            self.document_collection
            if collection_type == "document"
            else self.conversation_collection
        )

        if not collection:
            return []

        try:
            # [OPTIM] Sur-échantillonnage : récupérer 3x plus de candidats pour le reranking
            fetch_n = n_results * 3 if (rerank and self.reranker) else n_results

            # Générer embedding de la requête
            query_embedding = self.embedding_model.encode(query).tolist()

            # Rechercher dans ChromaDB
            results = collection.query(
                query_embeddings=[query_embedding], n_results=fetch_n
            )

            # Formater les résultats
            formatted_results = []
            if results and results["ids"] and len(results["ids"][0]) > 0:
                for i, chunk_id in enumerate(results["ids"][0]):
                    # Déchiffrer si nécessaire
                    content = results["documents"][0][i]
                    if results["metadatas"][0][i].get("encrypted", False):
                        content = self._decrypt(content)

                    formatted_results.append(
                        {
                            "chunk_id": chunk_id,
                            "content": content,
                            "metadata": results["metadatas"][0][i],
                            "distance": (
                                results["distances"][0][i]
                                if "distances" in results
                                else None
                            ),
                        }
                    )

            # [OPTIM] Reranking via CrossEncoder pour précision sémantique fine
            if rerank and self.reranker and len(formatted_results) > n_results:
                pairs = [[query, r["content"]] for r in formatted_results]
                scores = self.reranker.predict(pairs)
                for idx, result in enumerate(formatted_results):
                    result["rerank_score"] = float(scores[idx])
                formatted_results.sort(key=lambda r: r["rerank_score"], reverse=True)
                formatted_results = formatted_results[:n_results]
                print(f"🔀 [OPTIM] Reranking: {fetch_n} candidats → top {n_results}")

            return formatted_results

        except Exception as e:
            print(f"⚠️ Erreur recherche: {e}")
            return []

    def get_relevant_context(
        self, query: str, max_chunks: int = 5, collection_type: str = "document"
    ) -> str:
        """
        Récupère le contexte le plus pertinent (API compatible avec ancien système)
        [OPTIM] Utilise le reranking CrossEncoder pour une meilleure précision

        Args:
            query: Requête de recherche
            max_chunks: Nombre maximum de chunks finaux (après reranking)
            collection_type: Type de collection

        Returns:
            Contexte consolidé
        """
        results = self.search_similar(
            query, n_results=max_chunks, collection_type=collection_type,
            rerank=True,
        )

        if not results:
            return "Aucun contexte pertinent trouvé."

        context_parts = []
        for res in results:
            metadata = res["metadata"]
            doc_name = metadata.get("document_name", "Document")
            chunk_idx = metadata.get("chunk_index", 0)

            context_parts.append(
                f"--- {doc_name} (Chunk {chunk_idx}) ---\n" f"{res['content']}\n"
            )

        return "\n".join(context_parts)

    def _generate_document_id(self, content: str, name: str) -> str:
        """Génère un ID unique pour un document"""
        content_hash = hashlib.md5(content.encode()).hexdigest()[:8]
        name_clean = re.sub(r"[^a-zA-Z0-9]", "_", name)[:20]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"{name_clean}_{content_hash}_{timestamp}"

    def _cleanup_old_documents(self, tokens_needed: int):
        """
        Nettoie les vieux documents pour libérer de l'espace
        
        Args:
            tokens_needed: Nombre de tokens à libérer
        """
        if not self.documents:
            return

        # Trier par date (plus anciens en premier)
        sorted_docs = sorted(
            self.documents.items(),
            key=lambda x: x[1].get("created", "")
        )

        tokens_freed = 0
        docs_to_remove = []

        for doc_id, doc_info in sorted_docs:
            if self.current_tokens - tokens_freed + tokens_needed <= self.max_tokens:
                break

            # Supprimer chunks de ChromaDB
            if self.document_collection:
                try:
                    self.document_collection.delete(ids=doc_info["chunks"])
                except Exception as e:
                    print(f"⚠️ Erreur suppression chunks: {e}")

            tokens_freed += doc_info["total_tokens"]
            self.current_tokens -= doc_info["total_tokens"]
            docs_to_remove.append(doc_id)

        # Supprimer des métadonnées
        for doc_id in docs_to_remove:
            del self.documents[doc_id]

        if tokens_freed > 0:
            print(f"🧹 Nettoyage: {tokens_freed:,} tokens libérés ({len(docs_to_remove)} documents)")

    def get_stats(self) -> Dict[str, Any]:
        """Retourne les statistiques avec métriques de compression"""
        stats = {
            **self.stats,
            "current_tokens": self.current_tokens,
            "documents_count": len(self.documents),
            "max_tokens": self.max_tokens,
            "usage_percent": (self.current_tokens / self.max_tokens) * 100,
            "embeddings_enabled": self.embedding_model is not None,
            "chromadb_enabled": self.chroma_client is not None,
            "tokenizer": "tiktoken" if self.tokenizer else "fallback",
        }

        # Ajouter les stats de compression si disponibles
        if self.compression_monitor:
            compression_stats = self.compression_monitor.get_stats()
            stats["compression"] = compression_stats

        return stats

    def get_compression_report(self) -> str:
        """Génère un rapport de compression détaillé"""
        if self.compression_monitor:
            return self.compression_monitor.get_compression_report()
        else:
            return "Compression Monitor non disponible"

    def clear_all(self):
        """Vide toute la mémoire"""
        if self.document_collection:
            # ChromaDB ne permet pas de clear directement, on supprime et recrée
            try:
                self.chroma_client.delete_collection("documents")
                self.document_collection = self.chroma_client.create_collection(
                    name="documents", metadata={"hnsw:space": "cosine"}
                )
            except Exception as e:
                print(f"⚠️ Erreur clear documents: {e}")

        if self.conversation_collection:
            try:
                self.chroma_client.delete_collection("conversations")
                self.conversation_collection = self.chroma_client.create_collection(
                    name="conversations", metadata={"hnsw:space": "cosine"}
                )
            except Exception as e:
                print(f"⚠️ Erreur clear conversations: {e}")

        self.documents = {}
        self.current_tokens = 0
        self.stats = {
            "documents_added": 0,
            "chunks_created": 0,
            "total_tokens": 0,
            "last_updated": datetime.now().isoformat(),
            "encryption_enabled": self.enable_encryption,
        }

        print("🧹 Mémoire vidée")

    def cleanup(self):
        """
        Nettoie proprement les ressources (ChromaDB, threads, etc.)
        Doit être appelé avant de terminer le programme pour éviter le blocage
        """
        try:
            print("🧹 Nettoyage des ressources VectorMemory...")

            # Fermer ChromaDB proprement
            if self.chroma_client:
                try:
                    # ChromaDB PersistentClient n'a pas de méthode close() explicite
                    # mais on peut forcer la libération des ressources
                    self.chroma_client = None
                    self.document_collection = None
                    self.conversation_collection = None
                except Exception as e:
                    print(f"⚠️ Erreur fermeture ChromaDB: {e}")

            # Libérer le modèle d'embeddings
            if self.embedding_model:
                self.embedding_model = None

            # [OPTIM] Libérer le CrossEncoder
            if self.reranker:
                self.reranker = None

            # Libérer le tokenizer
            if self.tokenizer:
                self.tokenizer = None

            print("✅ Ressources VectorMemory libérées")

        except Exception as e:
            print(f"⚠️ Erreur cleanup VectorMemory: {e}")

if __name__ == "__main__":
    # Tests
    print("🧪 Test VectorMemory")

    memory = VectorMemory(max_tokens=100000, chunk_size=256, enable_encryption=True)

    # Test ajout document
    TEST_CONTENT = (
        "Python est un langage de programmation puissant et facile à apprendre. " * 50
    )
    ADD_RESULT = memory.add_document(TEST_CONTENT, "Test Python")
    print(f"✅ Document ajouté: {ADD_RESULT}")

    # Test recherche
    if memory.embedding_model:
        SEARCH_RESULTS = memory.search_similar("Python programmation")
        print(f"✅ Recherche: {len(SEARCH_RESULTS)} résultats")

        CONTEXT = memory.get_relevant_context("Python")
        print(f"✅ Contexte: {len(CONTEXT)} caractères")

    # Stats
    MEMORY_STATS = memory.get_stats()
    print(f"📊 Stats: {MEMORY_STATS}")
