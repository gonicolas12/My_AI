"""
MillionTokenContextManager - Gestionnaire de contexte 1M tokens
Gestion intelligente d'un contexte étendu jusqu'à 1 million de tokens
"""

import json
import hashlib
from typing import Dict, Any, List, Tuple
from pathlib import Path
import re
from datetime import datetime


class MillionTokenContextManager:
    """
    Gestionnaire de contexte intelligent pour 1 million de tokens
    Utilise un système de chunks, indexation et recherche sémantique basique
    """

    def __init__(self, max_tokens: int = 1000000, chunk_size: int = 2048):
        """
        Initialise le gestionnaire de contexte

        Args:
            max_tokens: Limite maximale de tokens (défaut: 1M)
            chunk_size: Taille des chunks en tokens (défaut: 2048)
        """
        self.max_tokens = max_tokens
        self.chunk_size = chunk_size
        self.current_tokens = 0

        # Storage pour les documents et chunks
        self.documents = {}  # document_id -> document_info
        self.chunks = {}  # chunk_id -> chunk_content
        self.chunk_index = {}  # mot -> [chunk_ids]

        # Statistiques
        self.stats = {
            "documents_added": 0,
            "chunks_created": 0,
            "total_tokens": 0,
            "last_updated": None,
        }

        # Répertoire de sauvegarde
        self.storage_dir = Path("context_storage")
        self.storage_dir.mkdir(exist_ok=True)

    def add_document(self, content: str, document_name: str = "") -> Dict[str, Any]:
        """
        Ajoute un document au contexte

        Args:
            content: Contenu du document
            document_name: Nom du document

        Returns:
            Informations sur l'ajout
        """
        try:
            # Générer un ID unique pour le document
            doc_id = self._generate_document_id(content, document_name)

            # Éviter les doublons
            if doc_id in self.documents:
                return {
                    "document_id": doc_id,
                    "chunks_created": 0,
                    "tokens_added": 0,
                    "status": "duplicate",
                }

            # Diviser en chunks
            chunks = self._split_into_chunks(content)
            chunk_ids = []
            tokens_added = 0

            for i, chunk_content in enumerate(chunks):
                chunk_id = f"{doc_id}_chunk_{i}"
                chunk_tokens = len(chunk_content.split())

                # Vérifier la limite de tokens
                if self.current_tokens + chunk_tokens > self.max_tokens:
                    # Nettoyer les anciens chunks si nécessaire
                    self._cleanup_old_chunks(chunk_tokens)

                # Ajouter le chunk
                self.chunks[chunk_id] = {
                    "content": chunk_content,
                    "document_id": doc_id,
                    "chunk_index": i,
                    "tokens": chunk_tokens,
                    "created": datetime.now().isoformat(),
                }

                # Indexer les mots du chunk
                self._index_chunk(chunk_id, chunk_content)

                chunk_ids.append(chunk_id)
                tokens_added += chunk_tokens
                self.current_tokens += chunk_tokens

            # Enregistrer les informations du document
            self.documents[doc_id] = {
                "name": document_name or f"Document_{len(self.documents)}",
                "chunks": chunk_ids,
                "total_tokens": tokens_added,
                "created": datetime.now().isoformat(),
                "preview": content[:200] + "..." if len(content) > 200 else content,
            }

            # Mettre à jour les statistiques
            self.stats["documents_added"] += 1
            self.stats["chunks_created"] += len(chunks)
            self.stats["total_tokens"] = self.current_tokens
            self.stats["last_updated"] = datetime.now().isoformat()

            return {
                "document_id": doc_id,
                "document_name": document_name,
                "chunks_created": len(chunks),
                "tokens_added": tokens_added,
                "status": "success",
            }

        except Exception as e:
            return {
                "error": f"Erreur lors de l'ajout du document: {str(e)}",
                "status": "error",
            }

    def get_relevant_context(self, query: str, max_chunks: int = 10) -> str:
        """
        Récupère le contexte le plus pertinent pour une requête

        Args:
            query: Requête de recherche
            max_chunks: Nombre maximum de chunks à retourner

        Returns:
            Contexte consolidé
        """
        try:
            # Rechercher les chunks pertinents
            relevant_chunks = self._search_chunks(query, max_chunks)

            if not relevant_chunks:
                return "Aucun contexte pertinent trouvé."

            # Construire le contexte
            context_parts = []
            for chunk_id in relevant_chunks:
                chunk = self.chunks[chunk_id]
                doc_name = self.documents[chunk["document_id"]]["name"]

                context_parts.append(
                    f"--- {doc_name} (Chunk {chunk['chunk_index']}) ---\n"
                    f"{chunk['content']}\n"
                )

            return "\n".join(context_parts)

        except Exception as e:
            return f"Erreur lors de la récupération du contexte: {str(e)}"

    def _split_into_chunks(self, content: str) -> List[str]:
        """
        Divise le contenu en chunks de taille appropriée
        """
        words = content.split()
        chunks = []
        current_chunk = []
        current_size = 0

        for word in words:
            if current_size + 1 > self.chunk_size and current_chunk:
                # Sauvegarder le chunk actuel
                chunks.append(" ".join(current_chunk))
                current_chunk = [word]
                current_size = 1
            else:
                current_chunk.append(word)
                current_size += 1

        # Ajouter le dernier chunk
        if current_chunk:
            chunks.append(" ".join(current_chunk))

        return chunks

    def _generate_document_id(self, content: str, name: str) -> str:
        """Génère un ID unique pour un document"""
        content_hash = hashlib.md5(content.encode()).hexdigest()[:8]
        name_clean = re.sub(r"[^a-zA-Z0-9]", "_", name)[:20]
        return f"{name_clean}_{content_hash}"

    def _index_chunk(self, chunk_id: str, content: str):
        """
        Indexe les mots d'un chunk pour la recherche
        """
        # Nettoyer et extraire les mots
        words = re.findall(r"\b\w+\b", content.lower())

        for word in set(words):  # Éviter les doublons
            if word not in self.chunk_index:
                self.chunk_index[word] = []

            if chunk_id not in self.chunk_index[word]:
                self.chunk_index[word].append(chunk_id)

    def _search_chunks(self, query: str, max_results: int) -> List[Tuple[str, float]]:
        """
        Recherche les chunks les plus pertinents

        Returns:
            Liste de (chunk_id, score) triée par pertinence
        """
        query_words = set(re.findall(r"\b\w+\b", query.lower()))
        chunk_scores = {}

        # Calculer le score pour chaque chunk
        for word in query_words:
            if word in self.chunk_index:
                for chunk_id in self.chunk_index[word]:
                    if chunk_id not in chunk_scores:
                        chunk_scores[chunk_id] = 0
                    chunk_scores[chunk_id] += 1

        # Trier par score et retourner les meilleurs
        sorted_chunks = sorted(chunk_scores.items(), key=lambda x: x[1], reverse=True)

        return sorted_chunks[:max_results]

    def _cleanup_old_chunks(self, tokens_needed: int):
        """
        Nettoie les anciens chunks pour faire de la place
        """
        # Stratégie simple: supprimer les plus anciens documents
        docs_by_date = sorted(self.documents.items(), key=lambda x: x[1]["created"])

        tokens_freed = 0
        for doc_id, doc_info in docs_by_date:
            if tokens_freed >= tokens_needed:
                break

            # Supprimer tous les chunks du document
            for chunk_id in doc_info["chunks"]:
                if chunk_id in self.chunks:
                    chunk = self.chunks[chunk_id]
                    tokens_freed += chunk["tokens"]
                    self.current_tokens -= chunk["tokens"]

                    # Supprimer de l'index
                    self._remove_chunk_from_index(chunk_id, chunk["content"])
                    del self.chunks[chunk_id]

            # Supprimer le document
            del self.documents[doc_id]

    def _remove_chunk_from_index(self, chunk_id: str, content: str):
        """Supprime un chunk de l'index de recherche"""
        words = set(re.findall(r"\b\w+\b", content.lower()))

        for word in words:
            if word in self.chunk_index and chunk_id in self.chunk_index[word]:
                self.chunk_index[word].remove(chunk_id)

                # Supprimer le mot s'il n'a plus de chunks
                if not self.chunk_index[word]:
                    del self.chunk_index[word]

    def get_stats(self) -> Dict[str, Any]:
        """Retourne les statistiques du gestionnaire"""
        return {
            **self.stats,
            "current_tokens": self.current_tokens,
            "documents_count": len(self.documents),
            "chunks_count": len(self.chunks),
            "max_tokens": self.max_tokens,
            "usage_percent": (self.current_tokens / self.max_tokens) * 100,
        }

    def clear_context(self):
        """Vide tout le contexte"""
        self.documents = {}
        self.chunks = {}
        self.chunk_index = {}
        self.current_tokens = 0

        self.stats = {
            "documents_added": 0,
            "chunks_created": 0,
            "total_tokens": 0,
            "last_updated": datetime.now().isoformat(),
        }

    def save_context(self, filename: str = None):
        """Sauvegarde le contexte sur disque"""
        if not filename:
            filename = f"context_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

        filepath = self.storage_dir / filename

        context_data = {
            "documents": self.documents,
            "chunks": self.chunks,
            "chunk_index": self.chunk_index,
            "stats": self.stats,
            "current_tokens": self.current_tokens,
            "max_tokens": self.max_tokens,
            "chunk_size": self.chunk_size,
        }

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(context_data, f, indent=2, ensure_ascii=False)

        return str(filepath)

    def load_context(self, filename: str):
        """Charge le contexte depuis le disque"""
        filepath = self.storage_dir / filename

        if not filepath.exists():
            raise FileNotFoundError(f"Fichier de contexte non trouvé: {filepath}")

        with open(filepath, "r", encoding="utf-8") as f:
            context_data = json.load(f)

        self.documents = context_data.get("documents", {})
        self.chunks = context_data.get("chunks", {})
        self.chunk_index = context_data.get("chunk_index", {})
        self.stats = context_data.get("stats", {})
        self.current_tokens = context_data.get("current_tokens", 0)
        self.max_tokens = context_data.get("max_tokens", 1000000)
        self.chunk_size = context_data.get("chunk_size", 2048)


if __name__ == "__main__":
    # Test du gestionnaire
    print("🧠 Test du gestionnaire de contexte 1M tokens")

    manager = MillionTokenContextManager()

    # Test d'ajout de document
    TEST_CONTENT = "Ceci est un document de test. " * 100
    result = manager.add_document(TEST_CONTENT, "Document Test")
    print(f"Ajout: {result}")

    # Test de recherche
    CONTEXT = manager.get_relevant_context("document test")
    print(f"Contexte trouvé: {len(CONTEXT)} caractères")

    # Statistiques
    stats = manager.get_stats()
    print(f"Stats: {stats}")
