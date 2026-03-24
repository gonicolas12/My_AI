"""
Historique des commandes et requêtes utilisateur.

Permet le suivi, la recherche et le rejeu de toutes les interactions
avec l'assistant My_AI. Stockage persistant via SQLite thread-safe.
"""

import json
import sqlite3
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from utils.logger import setup_logger

logger = setup_logger("command_history")

_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS command_history (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp       TEXT    NOT NULL,
    query           TEXT    NOT NULL,
    response_preview TEXT   NOT NULL DEFAULT '',
    agent_type      TEXT,
    is_favorite     INTEGER NOT NULL DEFAULT 0,
    metadata_json   TEXT
);

CREATE INDEX IF NOT EXISTS idx_ch_timestamp ON command_history(timestamp);
CREATE INDEX IF NOT EXISTS idx_ch_favorite  ON command_history(is_favorite);
CREATE INDEX IF NOT EXISTS idx_ch_query     ON command_history(query);
"""


class CommandHistory:
    """Gestionnaire d'historique des commandes et requêtes utilisateur."""

    def __init__(
        self,
        db_path: str = "data/command_history.db",
        max_entries: int = 5000,
    ) -> None:
        """
        Initialise l'historique des commandes.

        Args:
            db_path: Chemin vers la base de données SQLite.
            max_entries: Nombre maximal d'entrées conservées.
                         Les plus anciennes (hors favoris) sont purgées
                         automatiquement lors de l'ajout.
        """
        self._db_path = Path(db_path)
        self._max_entries = max_entries
        self._lock = threading.Lock()

        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
        logger.info("CommandHistory initialisé (db=%s, max=%d)", db_path, max_entries)

    # ------------------------------------------------------------------
    # Initialisation
    # ------------------------------------------------------------------

    def _init_db(self) -> None:
        """Crée le schéma si nécessaire."""
        with self._connect() as conn:
            conn.executescript(_SCHEMA_SQL)

    def _connect(self) -> sqlite3.Connection:
        """
        Ouvre une connexion SQLite configurée pour un usage thread-safe.

        Returns:
            Connexion SQLite avec row_factory activée.
        """
        conn = sqlite3.connect(str(self._db_path), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    # ------------------------------------------------------------------
    # Opérations CRUD
    # ------------------------------------------------------------------

    def add(
        self,
        query: str,
        response_preview: str = "",
        agent_type: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> int:
        """
        Enregistre une nouvelle requête dans l'historique.

        Args:
            query: Texte de la requête utilisateur.
            response_preview: Aperçu de la réponse (tronqué à 200 caractères).
            agent_type: Type d'agent ayant traité la requête.
            metadata: Métadonnées additionnelles (sérialisées en JSON).

        Returns:
            Identifiant unique de l'entrée créée.
        """
        preview = (response_preview or "")[:200]
        meta_json = json.dumps(metadata, ensure_ascii=False) if metadata else None
        now = datetime.now().isoformat()

        with self._lock:
            with self._connect() as conn:
                cursor = conn.execute(
                    """
                    INSERT INTO command_history
                        (timestamp, query, response_preview, agent_type, metadata_json)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (now, query, preview, agent_type, meta_json),
                )
                entry_id: int = cursor.lastrowid  # type: ignore[assignment]
                conn.commit()

            self._enforce_max_entries()

        logger.debug("Entrée ajoutée id=%d query='%s'", entry_id, query[:80])
        return entry_id

    def search(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Recherche dans l'historique par correspondance partielle.

        La recherche porte sur le texte de la requête et l'aperçu de la
        réponse (insensible à la casse).

        Args:
            query: Terme de recherche.
            limit: Nombre maximal de résultats.

        Returns:
            Liste de dictionnaires représentant les entrées correspondantes,
            triées par date décroissante.
        """
        pattern = f"%{query}%"
        with self._lock:
            with self._connect() as conn:
                rows = conn.execute(
                    """
                    SELECT * FROM command_history
                    WHERE query LIKE ? COLLATE NOCASE
                       OR response_preview LIKE ? COLLATE NOCASE
                    ORDER BY timestamp DESC
                    LIMIT ?
                    """,
                    (pattern, pattern, limit),
                ).fetchall()
        return [self._row_to_dict(r) for r in rows]

    def get_recent(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Récupère les entrées les plus récentes.

        Args:
            limit: Nombre maximal d'entrées retournées.

        Returns:
            Liste de dictionnaires triés par date décroissante.
        """
        with self._lock:
            with self._connect() as conn:
                rows = conn.execute(
                    """
                    SELECT * FROM command_history
                    ORDER BY timestamp DESC
                    LIMIT ?
                    """,
                    (limit,),
                ).fetchall()
        return [self._row_to_dict(r) for r in rows]

    def get_favorites(self) -> List[Dict[str, Any]]:
        """
        Récupère toutes les entrées marquées comme favorites.

        Returns:
            Liste de dictionnaires triés par date décroissante.
        """
        with self._lock:
            with self._connect() as conn:
                rows = conn.execute(
                    """
                    SELECT * FROM command_history
                    WHERE is_favorite = 1
                    ORDER BY timestamp DESC
                    """,
                ).fetchall()
        return [self._row_to_dict(r) for r in rows]

    def toggle_favorite(self, entry_id: int) -> bool:
        """
        Bascule l'état favori d'une entrée.

        Args:
            entry_id: Identifiant de l'entrée.

        Returns:
            ``True`` si l'entrée est désormais favorite,
            ``False`` si elle ne l'est plus.

        Raises:
            ValueError: Si l'identifiant n'existe pas.
        """
        with self._lock:
            with self._connect() as conn:
                row = conn.execute(
                    "SELECT is_favorite FROM command_history WHERE id = ?",
                    (entry_id,),
                ).fetchone()
                if row is None:
                    raise ValueError(f"Entrée introuvable : id={entry_id}")

                new_state = 0 if row["is_favorite"] else 1
                conn.execute(
                    "UPDATE command_history SET is_favorite = ? WHERE id = ?",
                    (new_state, entry_id),
                )
                conn.commit()

        is_fav = bool(new_state)
        logger.debug("Favori basculé id=%d -> %s", entry_id, is_fav)
        return is_fav

    def delete(self, entry_id: int) -> bool:
        """
        Supprime une entrée de l'historique.

        Args:
            entry_id: Identifiant de l'entrée à supprimer.

        Returns:
            ``True`` si l'entrée existait et a été supprimée,
            ``False`` sinon.
        """
        with self._lock:
            with self._connect() as conn:
                cursor = conn.execute(
                    "DELETE FROM command_history WHERE id = ?",
                    (entry_id,),
                )
                conn.commit()
                deleted = cursor.rowcount > 0

        if deleted:
            logger.debug("Entrée supprimée id=%d", entry_id)
        return deleted

    # ------------------------------------------------------------------
    # Statistiques et maintenance
    # ------------------------------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        """
        Calcule les statistiques de l'historique.

        Returns:
            Dictionnaire contenant :
            - ``total_entries`` : nombre total d'entrées
            - ``favorites_count`` : nombre de favoris
            - ``date_range`` : dict avec ``oldest`` et ``newest`` (ISO)
            - ``agent_types`` : dict {type: count}
        """
        with self._lock:
            with self._connect() as conn:
                total = conn.execute(
                    "SELECT COUNT(*) AS c FROM command_history"
                ).fetchone()["c"]

                favorites = conn.execute(
                    "SELECT COUNT(*) AS c FROM command_history WHERE is_favorite = 1"
                ).fetchone()["c"]

                dates = conn.execute(
                    """
                    SELECT MIN(timestamp) AS oldest, MAX(timestamp) AS newest
                    FROM command_history
                    """
                ).fetchone()

                agent_rows = conn.execute(
                    """
                    SELECT agent_type, COUNT(*) AS c
                    FROM command_history
                    GROUP BY agent_type
                    """
                ).fetchall()

        agent_types: Dict[str, int] = {
            (row["agent_type"] or "unknown"): row["c"] for row in agent_rows
        }

        return {
            "total_entries": total,
            "favorites_count": favorites,
            "date_range": {
                "oldest": dates["oldest"],
                "newest": dates["newest"],
            },
            "agent_types": agent_types,
        }

    def clear_old(self, days: int = 90) -> int:
        """
        Supprime les entrées non favorites plus anciennes qu'un nombre de jours.

        Args:
            days: Seuil d'ancienneté en jours.

        Returns:
            Nombre d'entrées supprimées.
        """
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        with self._lock:
            with self._connect() as conn:
                cursor = conn.execute(
                    """
                    DELETE FROM command_history
                    WHERE timestamp < ? AND is_favorite = 0
                    """,
                    (cutoff,),
                )
                conn.commit()
                deleted = cursor.rowcount

        if deleted:
            logger.info(
                "%d entrée(s) antérieure(s) à %d jours supprimée(s)", deleted, days
            )
        return deleted

    # ------------------------------------------------------------------
    # Utilitaires internes
    # ------------------------------------------------------------------

    def _enforce_max_entries(self) -> None:
        """Purge les entrées excédentaires (hors favoris), les plus anciennes d'abord."""
        with self._connect() as conn:
            total = conn.execute(
                "SELECT COUNT(*) AS c FROM command_history"
            ).fetchone()["c"]

            if total <= self._max_entries:
                return

            overflow = total - self._max_entries
            conn.execute(
                """
                DELETE FROM command_history
                WHERE id IN (
                    SELECT id FROM command_history
                    WHERE is_favorite = 0
                    ORDER BY timestamp ASC
                    LIMIT ?
                )
                """,
                (overflow,),
            )
            conn.commit()
            logger.debug("Purge automatique : %d entrée(s) supprimée(s)", overflow)

    @staticmethod
    def _row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
        """
        Convertit une ligne SQLite en dictionnaire exploitable.

        Les métadonnées JSON sont désérialisées automatiquement.
        """
        d: Dict[str, Any] = dict(row)
        raw_meta = d.get("metadata_json")
        if raw_meta:
            try:
                d["metadata"] = json.loads(raw_meta)
            except (json.JSONDecodeError, TypeError):
                d["metadata"] = None
        else:
            d["metadata"] = None
        return d
