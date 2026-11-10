"""
Vector Memory - Gestionnaire de mémoire vectorielle avec recherche sémantique
Remplace le million_token_context_manager avec de vraies capacités ML
Supporte ChromaDB et FAISS, tokenization correcte (tiktoken), chiffrement AES-256
"""

import hashlib
import os
import re
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import huggingface_hub.constants as _hf_constants
import transformers.utils.hub as _tf_hub
from huggingface_hub import snapshot_download

from core.config import get_config
from core.embedding_engine import (
    belongs_to,
    collection_name,
    encode_documents,
    encode_queries,
)
from core.reranker import choose as choose_reranker
from core.reranker import download_in_background as download_reranker_in_background
from core.reranker import filters_by_score as reranker_filters_by_score
from core.reranker import is_pinned as reranker_is_pinned
from core.reranker import local_path as reranker_local_path
from memory.embedding_reindex import MigratingCollection, reindexer_for
try:
    from core.network import configure_network_environment, build_network_error_help
except ImportError:
    def configure_network_environment(_force: bool = False):
        """Fallback no-op si le module réseau n'est pas disponible."""
        return {}

    def build_network_error_help(_error: Exception) -> str:
        """Fallback no-op pour l'aide réseau."""
        return ""

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

# CrossEncoder partagé par toutes les instances (l'appli en crée plusieurs) :
# chacune le rechargeait, en interrogeant le Hub (≈ 4 s et 30 requêtes).
_SHARED_RERANKERS: Dict[str, "_SharedReranker"] = {}
_RERANKER_LOCK = threading.Lock()

# Candidats relus au plus par le reranker : il lit chaque paire question-passage
# (≈ 0,1 s par paire de 256 tokens sur CPU avec mmarco). Au-delà de 30, l'ordre
# du modèle d'embeddings est gardé : 15 morceaux demandés n'en coûtent que 30.
RERANK_MAX_CANDIDATES = 30


class _SharedReranker:
    """CrossEncoder partagé dont predict est sérialisé : son tokenizer ne
    supporte pas deux appels simultanés depuis des threads différents."""

    def __init__(self, model):
        self._model = model
        self._lock = threading.Lock()

    def predict(self, *args, **kwargs):
        with self._lock:
            return self._model.predict(*args, **kwargs)


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
    - Embeddings sémantiques multilingues (core.embedding_engine, Granite par défaut)
    - Stockage vectoriel (ChromaDB), une collection par modèle d'embeddings
    - Chiffrement AES-256 (optionnel)
    - Recherche par similarité cosinus
    """

    def __init__(
        self,
        max_tokens: Optional[int] = None,
        chunk_size: Optional[int] = None,
        chunk_overlap: Optional[int] = None,
        storage_dir: str = "memory/vector_store",
        enable_encryption: bool = False,
        encryption_key: Optional[str] = None,
    ):
        """
        Initialise le gestionnaire de mémoire vectorielle

        Args:
            max_tokens: Limite maximale de tokens (lit config.yaml par défaut ou 1M)
            chunk_size: Taille des chunks en tokens (optimization.rag.chunk_size, 256)
            chunk_overlap: Chevauchement entre chunks (optimization.rag.chunk_overlap, 32)
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
        if chunk_size is None:
            chunk_size = self._rag_setting("chunk_size", 256)
        if chunk_overlap is None:
            chunk_overlap = self._rag_setting("chunk_overlap", 32)

        self.max_tokens = max_tokens
        self.chunk_size = max(1, int(chunk_size))
        # Un chevauchement aussi long que le morceau ferait boucler le découpage
        self.chunk_overlap = max(0, min(int(chunk_overlap), self.chunk_size - 1))
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
        self.reranker_model = None
        self.reranker_filters = True
        if CROSSENCODER_AVAILABLE:
            self._load_reranker()

        # Base vectorielle ChromaDB
        self._reindexer = None
        if CHROMADB_AVAILABLE:
            try:
                self.chroma_client = chromadb.PersistentClient(
                    path=str(self.storage_dir / "chroma_db")
                )
                existing = [
                    getattr(collection, "name", collection)
                    for collection in self.chroma_client.list_collections()
                ]

                # Collections pour différents types de données, une par modèle
                # d'embeddings (anciennes recalculées en arrière-plan)
                self.conversation_collection = self._open_collection("conversations", existing)

                self.document_collection = self._open_collection("documents", existing)

                # Collection dédiée aux dossiers attachés à un workspace
                # (codebase / dossiers de docs indexés par core.folder_indexer).
                # Séparée de "documents" pour ne pas mélanger l'index projet
                # avec les fichiers attachés ad-hoc ; filtrable par workspace_id.
                self.codebase_collection = self._open_collection("codebase", existing)

                if self._reindexer is not None:
                    self._reindexer.start()

                print("✅ ChromaDB initialisé")
            except Exception as e:
                print(f"⚠️ Erreur ChromaDB: {e}")
                self.chroma_client = None
                self.conversation_collection = None
                self.document_collection = None
                self.codebase_collection = None
        else:
            self.chroma_client = None
            self.conversation_collection = None
            self.document_collection = None
            self.codebase_collection = None

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

    @staticmethod
    def _rag_setting(name: str, default: int) -> int:
        """Réglage entier optimization.rag.<name> de config.yaml."""
        try:
            return int(get_config().get(f"optimization.rag.{name}", default))
        except Exception:
            return default

    # ------------------------------------------------------------------
    # Collections par modèle d'embeddings
    # ------------------------------------------------------------------

    def _collection_name(self, base: str) -> str:
        """Nom de la collection `base` pour le modèle d'embeddings actif."""
        model_id = getattr(self.embedding_model, "model_id", None)
        if not model_id:
            return base
        return collection_name(
            base,
            model_id,
            getattr(self.embedding_model, "dimension", 0),
            getattr(self.embedding_model, "revision", None),
        )

    def _collection_metadata(self) -> Dict[str, Any]:
        """Métadonnées d'une collection créée : distance cosinus et modèle des vecteurs."""
        metadata: Dict[str, Any] = {"hnsw:space": "cosine"}
        model_id = getattr(self.embedding_model, "model_id", None)
        if model_id:
            metadata["embedding_model"] = model_id
            metadata["embedding_dim"] = int(getattr(self.embedding_model, "dimension", 0) or 0)
        return metadata

    def _open_collection(self, base: str, existing: List[str]):
        """
        Collection `base` du modèle actif, et réindexation des autres modèles

        Une collection `base` d'un autre modèle (MiniLM avant la mise à jour,
        par exemple) est recalculée en arrière-plan vers celle-ci, puis
        supprimée. Jamais vers un modèle de repli : la collection du modèle
        choisi reste intacte en attendant son retour.

        Args:
            base: "conversations", "documents" ou "codebase"
            existing: Noms des collections présentes dans la base

        Returns:
            La collection (enveloppée pendant une réindexation), ou None si
            son nom désigne les vecteurs d'un autre modèle
        """
        name = self._collection_name(base)
        collection = self.chroma_client.get_or_create_collection(
            name=name, metadata=self._collection_metadata()
        )
        model_id = getattr(self.embedding_model, "model_id", None)
        recorded = (collection.metadata or {}).get("embedding_model")
        if model_id and recorded and recorded != model_id:
            print(f"⚠️ Collection {name} calculée avec {recorded}, pas {model_id} : ignorée")
            return None
        if not model_id or getattr(self.embedding_model, "fallback", False):
            return collection
        sources = [other for other in existing if other != name and belongs_to(other, base)]
        if not sources:
            return collection
        reindexer = self._get_reindexer()
        reindexer.add_job(name, sources)
        return MigratingCollection(collection, reindexer)

    def _get_reindexer(self):
        """Réindexeur partagé du dossier de stockage et du modèle (un seul par processus)."""
        if self._reindexer is None:
            engine = self.embedding_model
            model_key = getattr(engine, "key", None) or getattr(engine, "model_id", "")
            self._reindexer = reindexer_for(
                f"{self.storage_dir.resolve()}|{model_key}",
                self.chroma_client,
                lambda texts: encode_documents(engine, texts),
                self._decrypt_stored,
            )
        return self._reindexer

    def _decrypt_stored(self, stored: str) -> str:
        """
        Texte en clair d'une entrée chiffrée, pour la recalculer

        La clé est celle du dossier de stockage, même si cette instance ne
        chiffre pas : une entrée chiffrée d'une ancienne session reste lisible.
        """
        cipher = getattr(self, "cipher", None) if self.enable_encryption else None
        if cipher is None:
            key_file = self.storage_dir / ".encryption_key"
            if not ENCRYPTION_AVAILABLE or not key_file.exists():
                raise ValueError("clé de chiffrement introuvable")
            cipher = Fernet(key_file.read_bytes())
        return cipher.decrypt(base64.b64decode(stored.encode())).decode()

    def _embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Vecteurs de passages (un seul calcul pour tous les textes)."""
        if not texts:
            return []
        return [_as_list(vector) for vector in encode_documents(self.embedding_model, texts)]

    def _load_reranker(self):
        """
        [OPTIM] Donne à l'instance le CrossEncoder partagé, chargé au premier besoin

        Lequel : core.reranker (mmarco multilingue avec Granite, ms-marco avec
        MiniLM, ou aucun). mmarco absent du cache se télécharge en arrière-plan ;
        l'ordre du modèle d'embeddings sert en attendant.
        """
        reranker_model = choose_reranker(self.embedding_model)
        self.reranker_model = reranker_model
        # Score utilisable comme seuil de pertinence (ms-marco) ; sinon la
        # recherche des conversations filtre par distance et trie par score
        self.reranker_filters = reranker_filters_by_score(reranker_model)
        if reranker_model is None:
            return
        with _RERANKER_LOCK:
            shared = _SHARED_RERANKERS.get(reranker_model)
            if shared is None:
                if reranker_is_pinned(reranker_model):
                    self._load_pinned_reranker(reranker_model)
                else:
                    self._fetch_reranker(reranker_model)
                if self.reranker is None:
                    return  # pas de reranking ; nouvel essai à la prochaine instance
                shared = _SHARED_RERANKERS[reranker_model] = _SharedReranker(self.reranker)
            self.reranker = shared

    def _load_pinned_reranker(self, reranker_model: str):
        """Reranker à version figée (mmarco) depuis le cache, sinon téléchargé en arrière-plan."""
        path = reranker_local_path(reranker_model)
        if path is None:
            download_reranker_in_background(reranker_model)
            return
        try:
            self.reranker = CrossEncoder(path)
            print(f"✅ CrossEncoder ({reranker_model.rsplit('/', 1)[-1]}) chargé pour reranking")
        except Exception as e:
            print(f"⚠️ Reranker {reranker_model} inutilisable ({e}) : passages triés par le modèle d'embeddings")
            self.reranker = None

    def _fetch_reranker(self, reranker_model: str):
        """
        [OPTIM] Charge le CrossEncoder avec gestion offline identique à core.shared.
        1. Essaie en mode offline (cache local)
        2. Si échec, tente le téléchargement (premier lancement)
        3. Si pas de réseau → fallback sans reranking (graceful degradation)
        """
        network_info = configure_network_environment()
        for warning in network_info.get("warnings", []):
            print(f"⚠️ [NETWORK] {warning}")

        # Étape 1 : depuis le dossier du cache, sans aucune requête au Hub (même
        # avec local_files_only, sentence-transformers 5 l'interroge encore pour
        # le tokenizer) ; LocalEntryNotFoundError si le modèle n'y est pas
        try:
            self.reranker = CrossEncoder(snapshot_download(reranker_model, local_files_only=True))
            print(f"✅ CrossEncoder ({reranker_model.rsplit('/', 1)[-1]}) chargé pour reranking")
            return
        except Exception:
            pass

        # Étape 2 : tenter le téléchargement (premier lancement)
        # IMPORTANT: huggingface_hub stocke le flag offline comme constante au
        # moment de l'import. Changer os.environ ne suffit pas — il faut aussi
        # patcher cette constante, que lit is_offline_mode() (donc transformers
        # 5.x). transformers 4.x (gardé sur Mac Intel) en fige en plus sa propre
        # copie, _is_offline_mode, qui n'existe plus en 5.x.
        saved_offline = os.environ.get('HF_HUB_OFFLINE', '0')
        saved_transformers = os.environ.get('TRANSFORMERS_OFFLINE', '0')
        saved_hf_const = None
        saved_tf_const = None
        tf_offline_copy = hasattr(_tf_hub, '_is_offline_mode')
        try:
            saved_hf_const = _hf_constants.HF_HUB_OFFLINE
            _hf_constants.HF_HUB_OFFLINE = False
            if tf_offline_copy:
                saved_tf_const = _tf_hub._is_offline_mode  # pylint: disable=protected-access
                _tf_hub._is_offline_mode = False  # pylint: disable=protected-access
            os.environ['HF_HUB_OFFLINE'] = '0'
            os.environ['TRANSFORMERS_OFFLINE'] = '0'
            print("📥 Téléchargement du CrossEncoder (reranking)... (une seule fois)")
            self.reranker = CrossEncoder(reranker_model)
            print("✅ CrossEncoder téléchargé et prêt (sera en cache)")
        except Exception as e:
            print(f"⚠️ CrossEncoder non disponible (pas de réseau ?): {e}")
            help_msg = build_network_error_help(e)
            if help_msg:
                print(help_msg)
            print("   → Le RAG fonctionnera sans reranking (distance cosinus seule)")
            self.reranker = None
        finally:
            # Toujours restaurer le mode offline
            os.environ['HF_HUB_OFFLINE'] = saved_offline
            os.environ['TRANSFORMERS_OFFLINE'] = saved_transformers
            try:
                _hf_constants.HF_HUB_OFFLINE = saved_hf_const
                if tf_offline_copy:
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

            # Générer embeddings (un seul calcul pour tous les morceaux) et stocker
            chunk_ids = []
            embeddings_list = self._embed_documents(chunks) if self.embedding_model else []

            for i, chunk_text in enumerate(chunks):
                chunk_id = f"{doc_id}_chunk_{i}"
                chunk_tokens = self.count_tokens(chunk_text)

                # Chiffrer si activé
                stored_text = (
                    self._encrypt(chunk_text) if self.enable_encryption else chunk_text
                )

                # Embedding du morceau
                embedding = embeddings_list[i] if embeddings_list else None

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

                    # upsert : après un redémarrage, le même document retrouve
                    # les mêmes identifiants de morceaux, qu'add() ignorerait
                    self.document_collection.upsert(
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
        rerank: bool = True, where: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Recherche sémantique par similarité avec reranking optionnel

        Args:
            query: Requête de recherche
            n_results: Nombre de résultats finaux souhaités
            collection_type: "document", "conversation" ou "codebase"
            rerank: Si True et CrossEncoder dispo, sur-échantillonne puis reranke
            where: Filtre de métadonnées ChromaDB (ex. {"workspace_id": "..."}),
                appliqué côté base avant le reranking. None = aucun filtre.

        Returns:
            Liste de résultats avec scores
        """
        if not self.embedding_model:
            print("⚠️ Recherche sémantique non disponible (embeddings désactivés)")
            return []

        collection = self._collection_for(collection_type)

        if not collection:
            return []

        try:
            # [OPTIM] Sur-échantillonnage : récupérer 3x plus de candidats pour le reranking
            fetch_n = (max(n_results, min(n_results * 3, RERANK_MAX_CANDIDATES))
                       if (rerank and self.reranker) else n_results)

            # Générer embedding de la requête
            query_embedding = _as_list(encode_queries(self.embedding_model, query))

            # Rechercher dans ChromaDB (filtre métadonnées optionnel)
            query_kwargs = {"query_embeddings": [query_embedding], "n_results": fetch_n}
            if where:
                query_kwargs["where"] = where
            results = collection.query(**query_kwargs)

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

    # ------------------------------------------------------------------
    # CRUD par entrée (inspection / édition / suppression manuelle)
    # Utilisé par la couche unifiée MemoryStore et la fenêtre « Mémoire ».
    # ------------------------------------------------------------------

    def _collection_for(self, collection_type: str):
        """Retourne la collection ChromaDB correspondant au type demandé.

        Args:
            collection_type: "document" ou "conversation".

        Returns:
            La collection ChromaDB, ou None si indisponible.
        """
        if collection_type == "conversation":
            return self.conversation_collection
        if collection_type == "codebase":
            return self.codebase_collection
        return self.document_collection

    def count_entries(self, collection_type: str = "document") -> int:
        """Compte les entrées d'une collection.

        Args:
            collection_type: "document" ou "conversation".

        Returns:
            Nombre d'entrées (0 si la collection est indisponible).
        """
        collection = self._collection_for(collection_type)
        if not collection:
            return 0
        try:
            return collection.count()
        except Exception as e:
            print(f"⚠️ Erreur count_entries: {e}")
            return 0

    def list_entries(
        self,
        collection_type: str = "document",
        limit: Optional[int] = None,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """Liste les entrées d'une collection (déchiffrées si nécessaire).

        Interroge directement ChromaDB : self.documents n'étant pas persisté,
        c'est la seule source fiable après un redémarrage.

        Args:
            collection_type: "document" ou "conversation".
            limit: Nombre maximum d'entrées (None = toutes).
            offset: Décalage de départ (pagination).

        Returns:
            Liste de dicts {"id", "content", "metadata"}.
        """
        collection = self._collection_for(collection_type)
        if not collection:
            return []
        try:
            data = collection.get(
                include=["documents", "metadatas"],
                limit=limit,
                offset=offset,
            )
        except Exception as e:
            print(f"⚠️ Erreur list_entries: {e}")
            return []

        ids = data.get("ids") or []
        docs = data.get("documents") or []
        metas = data.get("metadatas") or []
        entries: List[Dict[str, Any]] = []
        for i, entry_id in enumerate(ids):
            content = docs[i] if i < len(docs) else ""
            metadata = metas[i] if i < len(metas) else {}
            if metadata and metadata.get("encrypted"):
                try:
                    content = self._decrypt(content)
                except Exception:
                    pass
            entries.append(
                {"id": entry_id, "content": content, "metadata": metadata or {}}
            )
        return entries

    def get_entry(
        self, entry_id: str, collection_type: str = "document"
    ) -> Optional[Dict[str, Any]]:
        """Récupère une entrée précise par son identifiant.

        Args:
            entry_id: Identifiant ChromaDB de l'entrée.
            collection_type: "document" ou "conversation".

        Returns:
            Dict {"id", "content", "metadata"} ou None si introuvable.
        """
        collection = self._collection_for(collection_type)
        if not collection:
            return None
        try:
            data = collection.get(ids=[entry_id], include=["documents", "metadatas"])
        except Exception as e:
            print(f"⚠️ Erreur get_entry: {e}")
            return None
        ids = data.get("ids") or []
        if not ids:
            return None
        content = (data.get("documents") or [""])[0]
        metadata = (data.get("metadatas") or [{}])[0] or {}
        if metadata.get("encrypted"):
            try:
                content = self._decrypt(content)
            except Exception:
                pass
        return {"id": ids[0], "content": content, "metadata": metadata}

    def update_entry(
        self, entry_id: str, new_text: str, collection_type: str = "document"
    ) -> bool:
        """Met à jour le texte d'une entrée (ré-embarque + rechiffre si besoin).

        Args:
            entry_id: Identifiant ChromaDB de l'entrée.
            new_text: Nouveau contenu textuel.
            collection_type: "document" ou "conversation".

        Returns:
            True si la mise à jour a réussi, False sinon.
        """
        collection = self._collection_for(collection_type)
        if not collection or not new_text or not new_text.strip():
            return False

        stored_text = self._encrypt(new_text) if self.enable_encryption else new_text
        try:
            if self.embedding_model:
                embedding = _as_list(encode_documents(self.embedding_model, new_text))
                collection.update(
                    ids=[entry_id],
                    documents=[stored_text],
                    embeddings=[embedding],
                )
            else:
                collection.update(ids=[entry_id], documents=[stored_text])
            return True
        except Exception as e:
            print(f"⚠️ Erreur update_entry: {e}")
            return False

    def delete_entry(self, entry_id: str, collection_type: str = "document") -> bool:
        """Supprime DÉFINITIVEMENT une entrée de ChromaDB.

        Args:
            entry_id: Identifiant ChromaDB de l'entrée.
            collection_type: "document" ou "conversation".

        Returns:
            True si la suppression a réussi, False sinon.
        """
        collection = self._collection_for(collection_type)
        if not collection:
            return False
        try:
            collection.delete(ids=[entry_id])
            return True
        except Exception as e:
            print(f"⚠️ Erreur delete_entry: {e}")
            return False

    def remove_document(self, document_name: str) -> int:
        """
        Supprime un document ajouté pendant cette session, ChromaDB compris

        Sans cela, une pièce jointe retirée avant l'envoi resterait dans la base
        persistante et pourrait ressortir dans les recherches, même après un
        redémarrage.

        Args:
            document_name: Nom du document (celui passé à add_document)

        Returns:
            Nombre de morceaux supprimés
        """
        doc_ids = [
            doc_id for doc_id, info in self.documents.items()
            if info.get("name") == document_name
        ]
        removed = 0
        for doc_id in doc_ids:
            info = self.documents.pop(doc_id)
            chunks = info.get("chunks", [])
            if self.document_collection and chunks:
                try:
                    self.document_collection.delete(ids=chunks)
                except Exception as e:
                    print(f"⚠️ Erreur suppression chunks: {e}")
            removed += len(chunks)
            self.current_tokens = max(0, self.current_tokens - info.get("total_tokens", 0))
        if doc_ids:
            self.stats["documents_added"] = max(0, self.stats["documents_added"] - len(doc_ids))
            self.stats["chunks_created"] = max(0, self.stats["chunks_created"] - removed)
            self.stats["total_tokens"] = self.current_tokens
            self.stats["last_updated"] = datetime.now().isoformat()
        return removed

    def _generate_document_id(self, content: str, name: str) -> str:
        """Identifiant stable d'un document : même nom et même contenu, même ID.

        Il contenait l'heure à la seconde près : un document ajouté deux fois
        n'était reconnu comme doublon que dans la même seconde, et chaque
        nouvel ajout recopiait ses morceaux dans ChromaDB.
        """
        content_hash = hashlib.md5(content.encode()).hexdigest()[:16]
        name_clean = re.sub(r"[^a-zA-Z0-9]", "_", name)[:20]
        return f"{name_clean}_{content_hash}"

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
            "embedding_model": getattr(self.embedding_model, "model_id", None),
            "embedding_fallback": bool(getattr(self.embedding_model, "fallback", False)),
            "reranker_model": self.reranker_model if self.reranker is not None else None,
            "reindexing": bool(self._reindexer and self._reindexer.is_running()),
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
        """Vide toute la mémoire, collections des autres modèles d'embeddings comprises"""
        if self._reindexer is not None:
            # Plus rien à recalculer : les anciennes collections partent aussi
            self._reindexer.forget()
        for base, attribute in (
            ("documents", "document_collection"),
            ("conversations", "conversation_collection"),
            ("codebase", "codebase_collection"),
        ):
            if not getattr(self, attribute):
                continue
            # ChromaDB ne permet pas de clear directement, on supprime et recrée
            try:
                for collection in self.chroma_client.list_collections():
                    name = getattr(collection, "name", collection)
                    if belongs_to(name, base):
                        self.chroma_client.delete_collection(name)
                setattr(self, attribute, self.chroma_client.create_collection(
                    name=self._collection_name(base), metadata=self._collection_metadata()
                ))
            except Exception as e:
                print(f"⚠️ Erreur clear {base}: {e}")

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
                    self.codebase_collection = None
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


def _as_list(vector) -> List[float]:
    """Vecteur numpy (ou liste) en liste de flottants pour ChromaDB."""
    return vector.tolist() if hasattr(vector, "tolist") else list(vector)


if __name__ == "__main__":
    # Tests
    print("🧪 Test VectorMemory")

    memory = VectorMemory(max_tokens=100000, enable_encryption=True)

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
