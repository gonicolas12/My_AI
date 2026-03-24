"""
Cache HTTP pour les résultats de recherche web.
Stockage persistant sur disque avec TTL et nettoyage automatique.
"""

import hashlib
import threading
from typing import Dict, Optional

import diskcache

from utils.logger import setup_logger


class WebCache:
    """
    Cache persistant pour les réponses HTTP des recherches web.

    Utilise diskcache pour le stockage sur disque avec support
    natif du TTL et de la concurrence thread-safe.
    """

    def __init__(
        self,
        cache_dir: str = "data/web_cache",
        ttl_seconds: int = 3600,
        max_entries: int = 1000,
    ):
        """
        Initialise le cache web.

        Args:
            cache_dir: Répertoire de stockage du cache
            ttl_seconds: Durée de vie des entrées en secondes
            max_entries: Nombre maximum d'entrées en cache
        """
        self.logger = setup_logger("WebCache")
        self.ttl_seconds = ttl_seconds
        self.max_entries = max_entries

        self._cache = diskcache.Cache(
            directory=cache_dir,
            size_limit=max_entries * 512 * 1024,  # ~500 Ko par entrée estimé
        )

        self._lock = threading.Lock()
        self._hits = 0
        self._misses = 0

        self._cleanup_expired()
        self.logger.info(
            "Cache web initialisé (dir=%s, ttl=%ds, max=%d)",
            cache_dir,
            ttl_seconds,
            max_entries,
        )

    def _make_key(self, url: str) -> str:
        """Génère une clé de cache stable à partir de l'URL."""
        return hashlib.sha256(url.encode("utf-8")).hexdigest()

    def get(self, url: str) -> Optional[str]:
        """
        Récupère le contenu en cache pour une URL.

        Args:
            url: URL de la ressource

        Returns:
            Contenu en cache ou None si absent/expiré
        """
        key = self._make_key(url)
        value = self._cache.get(key, default=None)

        with self._lock:
            if value is not None:
                self._hits += 1
                self.logger.debug("Cache HIT pour %s", url)
                return value

            self._misses += 1
            self.logger.debug("Cache MISS pour %s", url)
            return None

    def put(self, url: str, content: str) -> None:
        """
        Stocke le contenu en cache avec TTL.

        Args:
            url: URL de la ressource
            content: Contenu de la réponse à stocker
        """
        key = self._make_key(url)
        self._cache.set(key, content, expire=self.ttl_seconds)
        self.logger.debug("Contenu mis en cache pour %s", url)

        if len(self._cache) > self.max_entries:
            self._evict_oldest()

    def invalidate(self, url: str) -> None:
        """
        Supprime une entrée spécifique du cache.

        Args:
            url: URL de la ressource à invalider
        """
        key = self._make_key(url)
        deleted = self._cache.delete(key)
        if deleted:
            self.logger.debug("Entrée invalidée pour %s", url)

    def clear(self) -> None:
        """Vide entièrement le cache."""
        self._cache.clear()
        with self._lock:
            self._hits = 0
            self._misses = 0
        self.logger.info("Cache vidé")

    def stats(self) -> Dict[str, int]:
        """
        Retourne les statistiques du cache.

        Returns:
            Dictionnaire avec hits, misses, taille actuelle
        """
        with self._lock:
            return {
                "hits": self._hits,
                "misses": self._misses,
                "size": len(self._cache),
                "volume_bytes": self._cache.volume(),
            }

    def _cleanup_expired(self) -> None:
        """Purge les entrées expirées du cache."""
        try:
            self._cache.expire()
            self.logger.debug("Nettoyage des entrées expirées effectué")
        except Exception as exc:
            self.logger.warning("Erreur lors du nettoyage du cache: %s", exc)

    def _evict_oldest(self) -> None:
        """Évince les entrées les plus anciennes si le cache dépasse max_entries."""
        try:
            while len(self._cache) > self.max_entries:
                self._cache.cull()
        except Exception as exc:
            self.logger.warning("Erreur lors de l'éviction du cache: %s", exc)

    def close(self) -> None:
        """Ferme proprement le cache disque."""
        self._cache.close()
        self.logger.info("Cache fermé")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False
