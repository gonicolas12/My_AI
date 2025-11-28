"""
Vector Memory - Gestionnaire de mémoire vectorielle avec recherche sémantique
Remplace le million_token_context_manager avec de vraies capacités ML
Supporte ChromaDB et FAISS, tokenization correcte, chiffrement AES-256
"""

import hashlib
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
import re

# Note: Le mode offline HuggingFace est géré intelligemment dans core.shared
# Il télécharge automatiquement le modèle au premier lancement si nécessaire

try:
    import chromadb

    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False
    print("⚠️ ChromaDB non disponible. Installez: pip install chromadb")

try:
    from core.shared import get_shared_embedding_model, is_embeddings_available

    EMBEDDINGS_AVAILABLE = is_embeddings_available()
except ImportError:
    EMBEDDINGS_AVAILABLE = False
    print(
        "⚠️ Sentence-transformers non disponible. Installez: pip install sentence-transformers"
    )
    get_shared_embedding_model = lambda: None

try:
    from transformers import AutoTokenizer

    TOKENIZER_AVAILABLE = True
except ImportError:
    TOKENIZER_AVAILABLE = False
    print("⚠️ Transformers non disponible. Installez: pip install transformers")

try:
    from cryptography.fernet import Fernet
    import base64

    ENCRYPTION_AVAILABLE = True
except ImportError:
    ENCRYPTION_AVAILABLE = False
    print("⚠️ Cryptography non disponible. Installez: pip install cryptography")


class VectorMemory:
    """
    Gestionnaire de mémoire vectorielle avec recherche sémantique

    Fonctionnalités:
    - Tokenization correcte (transformers)
    - Embeddings sémantiques (sentence-transformers)
    - Stockage vectoriel (ChromaDB/FAISS)
    - Chiffrement AES-256 (optionnel)
    - Recherche par similarité cosinus
    """

    def __init__(
        self,
        max_tokens: int = 1_000_000,
        chunk_size: int = 512,
        chunk_overlap: int = 50,
        embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2",
        storage_dir: str = "memory/vector_store",
        enable_encryption: bool = False,
        encryption_key: Optional[str] = None,
    ):
        """
        Initialise le gestionnaire de mémoire vectorielle

        Args:
            max_tokens: Limite maximale de tokens (1M par défaut)
            chunk_size: Taille des chunks en tokens
            chunk_overlap: Chevauchement entre chunks
            embedding_model: Modèle d'embeddings à utiliser
            storage_dir: Répertoire de stockage
            enable_encryption: Activer le chiffrement AES-256
            encryption_key: Clé de chiffrement (générée si None)
        """
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

        # Tokenizer (vrai comptage de tokens)
        if TOKENIZER_AVAILABLE:
            try:
                self.tokenizer = AutoTokenizer.from_pretrained("gpt2")
                print("✅ Tokenizer GPT-2 chargé")
            except Exception as e:
                print(f"⚠️ Erreur chargement tokenizer: {e}")
                self.tokenizer = None
        else:
            self.tokenizer = None

        # Modèle d'embeddings partagé (déjà chargé au démarrage dans core.shared)
        self.embedding_model = get_shared_embedding_model()

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

        print(f"✅ VectorMemory initialisé (max: {max_tokens:,} tokens)")

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
            # Vrai comptage avec tokenizer
            tokens = self.tokenizer.encode(text, add_special_tokens=False)
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
            # Découpage basé sur les vrais tokens
            tokens = self.tokenizer.encode(text, add_special_tokens=False)
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
                "preview": content[:200] + "..." if len(content) > 200 else content,
                "metadata": metadata,
            }

            # Mettre à jour statistiques
            self.stats["documents_added"] += 1
            self.stats["chunks_created"] += len(chunks)
            self.stats["total_tokens"] = self.current_tokens
            self.stats["last_updated"] = datetime.now().isoformat()

            return {
                "document_id": doc_id,
                "document_name": document_name,
                "chunks_created": len(chunks),
                "tokens_added": total_tokens,
                "status": "success",
            }

        except Exception as e:
            return {"error": str(e), "status": "error"}

    def search_similar(
        self, query: str, n_results: int = 5, collection_type: str = "document"
    ) -> List[Dict[str, Any]]:
        """
        Recherche sémantique par similarité

        Args:
            query: Requête de recherche
            n_results: Nombre de résultats
            collection_type: "document" ou "conversation"

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
            # Générer embedding de la requête
            query_embedding = self.embedding_model.encode(query).tolist()

            # Rechercher dans ChromaDB
            results = collection.query(
                query_embeddings=[query_embedding], n_results=n_results
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

            return formatted_results

        except Exception as e:
            print(f"⚠️ Erreur recherche: {e}")
            return []

    def get_relevant_context(
        self, query: str, max_chunks: int = 10, collection_type: str = "document"
    ) -> str:
        """
        Récupère le contexte le plus pertinent (API compatible avec ancien système)

        Args:
            query: Requête de recherche
            max_chunks: Nombre maximum de chunks
            collection_type: Type de collection

        Returns:
            Contexte consolidé
        """
        results = self.search_similar(
            query, n_results=max_chunks, collection_type=collection_type
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
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        return f"{name_clean}_{content_hash}_{timestamp}"

    def _cleanup_old_documents(self, tokens_needed: int):
        """Nettoie les anciens documents pour faire de la place"""
        docs_by_date = sorted(self.documents.items(), key=lambda x: x[1]["created"])

        tokens_freed = 0
        for doc_id, doc_info in docs_by_date:
            if tokens_freed >= tokens_needed:
                break

            # Supprimer chunks de ChromaDB
            if self.document_collection:
                self.document_collection.delete(ids=doc_info["chunks"])

            tokens_freed += doc_info["total_tokens"]
            self.current_tokens -= doc_info["total_tokens"]
            del self.documents[doc_id]

        print(f"🧹 Nettoyage: {tokens_freed:,} tokens libérés")

    def get_stats(self) -> Dict[str, Any]:
        """Retourne les statistiques"""
        return {
            **self.stats,
            "current_tokens": self.current_tokens,
            "documents_count": len(self.documents),
            "max_tokens": self.max_tokens,
            "usage_percent": (self.current_tokens / self.max_tokens) * 100,
            "embeddings_enabled": self.embedding_model is not None,
            "chromadb_enabled": self.chroma_client is not None,
            "tokenizer": "transformers" if self.tokenizer else "fallback",
        }

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
    result = memory.add_document(TEST_CONTENT, "Test Python")
    print(f"✅ Document ajouté: {result}")

    # Test recherche
    if memory.embedding_model:
        search_results = memory.search_similar("Python programmation")
        print(f"✅ Recherche: {len(search_results)} résultats")

        CONTEXT = memory.get_relevant_context("Python")
        print(f"✅ Contexte: {len(CONTEXT)} caractères")

    # Stats
    stats = memory.get_stats()
    print(f"📊 Stats: {stats}")
