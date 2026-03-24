"""
Gestionnaire de base de connaissances structurée pour My_AI.
Stocke des faits éditables (noms, décisions, préférences, procédures)
extraits des conversations ou ajoutés manuellement.
"""

import re
import sqlite3
import threading
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from utils.logger import setup_logger

logger = setup_logger("knowledge_base_manager")

VALID_CATEGORIES = (
    "preference",
    "decision",
    "person",
    "procedure",
    "technical",
    "general",
)

# Patrons d'extraction automatique de faits depuis du texte libre
_EXTRACT_PATTERNS: List[Dict] = [
    # Préférences explicites
    {
        "category": "preference",
        "pattern": re.compile(
            r"(?:je préfère|je prefere|j'aime mieux|j'utilise toujours|"
            r"toujours utiliser|mon choix est|je choisis)\s+(.+?)(?:\.|$)",
            re.IGNORECASE,
        ),
        "key_prefix": "préférence",
    },
    # Décisions
    {
        "category": "decision",
        "pattern": re.compile(
            r"(?:on a décidé de|nous avons décidé|la décision est de|"
            r"il a été décidé|j'ai décidé de)\s+(.+?)(?:\.|$)",
            re.IGNORECASE,
        ),
        "key_prefix": "décision",
    },
    # Personnes (noms propres avec contexte)
    {
        "category": "person",
        "pattern": re.compile(
            r"(?:(?:mon|ma|notre|le|la)\s+(?:collègue|manager|responsable|directeur|"
            r"directrice|chef|contact)\s+(?:est|s'appelle|se nomme)\s+)([A-ZÀ-Ü][a-zà-ü]+(?:\s+[A-ZÀ-Ü][a-zà-ü]+)*)",
            re.UNICODE,
        ),
        "key_prefix": "personne",
    },
    # Procédures
    {
        "category": "procedure",
        "pattern": re.compile(
            r"(?:la procédure est de|pour faire cela il faut|les étapes sont|"
            r"la marche à suivre est)\s+(.+?)(?:\.|$)",
            re.IGNORECASE,
        ),
        "key_prefix": "procédure",
    },
    # Informations techniques
    {
        "category": "technical",
        "pattern": re.compile(
            r"(?:le serveur est|l'url est|le port est|la version est|"
            r"l'adresse est|le mot de passe est|l'api key est|"
            r"on utilise|nous utilisons)\s+(.+?)(?:\.|$)",
            re.IGNORECASE,
        ),
        "key_prefix": "technique",
    },
]


class KnowledgeBaseManager:
    """
    Gestionnaire de base de connaissances structurée.
    Utilise SQLite pour le stockage persistant de faits catégorisés
    avec recherche textuelle et extraction automatique.
    """

    def __init__(self, db_path: str = "data/knowledge_base/facts.db") -> None:
        """
        Initialise le gestionnaire de base de connaissances.

        Args:
            db_path: Chemin vers le fichier de base de données SQLite.
        """
        self._db_path = Path(db_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._local = threading.local()
        self._init_db()
        logger.info("KnowledgeBaseManager initialisé avec la base : %s", self._db_path)

    # ------------------------------------------------------------------
    # Connexion thread-safe
    # ------------------------------------------------------------------

    def _get_connection(self) -> sqlite3.Connection:
        """
        Retourne une connexion SQLite propre au thread courant.

        Returns:
            Connexion SQLite avec row_factory configurée.
        """
        if not hasattr(self._local, "connection") or self._local.connection is None:
            conn = sqlite3.connect(str(self._db_path))
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA foreign_keys=ON")
            self._local.connection = conn
        return self._local.connection

    def _init_db(self) -> None:
        """Crée le schéma de la base de données si nécessaire."""
        conn = self._get_connection()
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS facts (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                category    TEXT    NOT NULL,
                key         TEXT    NOT NULL,
                value       TEXT    NOT NULL,
                source      TEXT    NOT NULL DEFAULT 'manual',
                confidence  REAL    NOT NULL DEFAULT 1.0,
                created_at  TEXT    NOT NULL,
                updated_at  TEXT    NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_facts_category ON facts(category);
            CREATE INDEX IF NOT EXISTS idx_facts_key      ON facts(key);
            """
        )
        conn.commit()

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    def add_fact(
        self,
        category: str,
        key: str,
        value: str,
        source: str = "manual",
        confidence: float = 1.0,
    ) -> int:
        """
        Ajoute un fait dans la base de connaissances.

        Args:
            category:   Catégorie du fait (preference, decision, person, ...).
            key:        Clé descriptive du fait.
            value:      Valeur du fait.
            source:     Origine du fait (manual, conversation, ...).
            confidence: Niveau de confiance entre 0.0 et 1.0.

        Returns:
            Identifiant du fait créé.

        Raises:
            ValueError: Si la catégorie est invalide ou la confiance hors bornes.
        """
        category = category.lower().strip()
        if category not in VALID_CATEGORIES:
            raise ValueError(
                f"Catégorie invalide '{category}'. "
                f"Catégories acceptées : {', '.join(VALID_CATEGORIES)}"
            )
        if not 0.0 <= confidence <= 1.0:
            raise ValueError("La confiance doit être comprise entre 0.0 et 1.0")
        if not key or not key.strip():
            raise ValueError("La clé ne peut pas être vide")
        if not value or not value.strip():
            raise ValueError("La valeur ne peut pas être vide")

        now = datetime.now().isoformat()
        conn = self._get_connection()
        cursor = conn.execute(
            """
            INSERT INTO facts (category, key, value, source, confidence, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (category, key.strip(), value.strip(), source, confidence, now, now),
        )
        conn.commit()
        fact_id = cursor.lastrowid
        logger.info("Fait ajouté [id=%d] catégorie=%s clé=%s", fact_id, category, key)
        return fact_id

    def get_fact(self, key: str) -> Optional[Dict]:
        """
        Récupère un fait par sa clé.

        Args:
            key: Clé du fait recherché.

        Returns:
            Dictionnaire du fait ou None si non trouvé.
        """
        conn = self._get_connection()
        row = conn.execute(
            "SELECT * FROM facts WHERE key = ? ORDER BY updated_at DESC LIMIT 1",
            (key,),
        ).fetchone()
        if row is None:
            return None
        return dict(row)

    def search_facts(
        self,
        query: str,
        category: str = None,
        limit: int = 10,
    ) -> List[Dict]:
        """
        Recherche des faits par texte dans la clé et la valeur.

        Args:
            query:    Terme de recherche.
            category: Filtrer par catégorie (optionnel).
            limit:    Nombre maximum de résultats.

        Returns:
            Liste de faits correspondants triés par pertinence.
        """
        conn = self._get_connection()
        search_term = f"%{query}%"

        if category:
            category = category.lower().strip()
            rows = conn.execute(
                """
                SELECT * FROM facts
                WHERE (key LIKE ? OR value LIKE ?)
                  AND category = ?
                ORDER BY
                    CASE WHEN key LIKE ? THEN 0 ELSE 1 END,
                    confidence DESC,
                    updated_at DESC
                LIMIT ?
                """,
                (search_term, search_term, category, search_term, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT * FROM facts
                WHERE key LIKE ? OR value LIKE ?
                ORDER BY
                    CASE WHEN key LIKE ? THEN 0 ELSE 1 END,
                    confidence DESC,
                    updated_at DESC
                LIMIT ?
                """,
                (search_term, search_term, search_term, limit),
            ).fetchall()

        return [dict(r) for r in rows]

    def update_fact(self, fact_id: int, value: str) -> bool:
        """
        Met à jour la valeur d'un fait existant.

        Args:
            fact_id: Identifiant du fait à modifier.
            value:   Nouvelle valeur.

        Returns:
            True si le fait a été mis à jour, False sinon.
        """
        if not value or not value.strip():
            raise ValueError("La valeur ne peut pas être vide")

        now = datetime.now().isoformat()
        conn = self._get_connection()
        cursor = conn.execute(
            "UPDATE facts SET value = ?, updated_at = ? WHERE id = ?",
            (value.strip(), now, fact_id),
        )
        conn.commit()
        updated = cursor.rowcount > 0
        if updated:
            logger.info("Fait mis à jour [id=%d]", fact_id)
        else:
            logger.warning("Fait non trouvé pour mise à jour [id=%d]", fact_id)
        return updated

    def delete_fact(self, fact_id: int) -> bool:
        """
        Supprime un fait de la base de connaissances.

        Args:
            fact_id: Identifiant du fait à supprimer.

        Returns:
            True si le fait a été supprimé, False sinon.
        """
        conn = self._get_connection()
        cursor = conn.execute("DELETE FROM facts WHERE id = ?", (fact_id,))
        conn.commit()
        deleted = cursor.rowcount > 0
        if deleted:
            logger.info("Fait supprimé [id=%d]", fact_id)
        else:
            logger.warning("Fait non trouvé pour suppression [id=%d]", fact_id)
        return deleted

    # ------------------------------------------------------------------
    # Requêtes de lecture
    # ------------------------------------------------------------------

    def get_all_facts(self, category: str = None) -> List[Dict]:
        """
        Récupère tous les faits, éventuellement filtrés par catégorie.

        Args:
            category: Filtrer par catégorie (optionnel).

        Returns:
            Liste de tous les faits correspondants.
        """
        conn = self._get_connection()
        if category:
            category = category.lower().strip()
            rows = conn.execute(
                "SELECT * FROM facts WHERE category = ? ORDER BY updated_at DESC",
                (category,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM facts ORDER BY category, updated_at DESC"
            ).fetchall()
        return [dict(r) for r in rows]

    def get_categories(self) -> List[str]:
        """
        Retourne la liste des catégories ayant au moins un fait.

        Returns:
            Liste triée des catégories utilisées.
        """
        conn = self._get_connection()
        rows = conn.execute(
            "SELECT DISTINCT category FROM facts ORDER BY category"
        ).fetchall()
        return [r["category"] for r in rows]

    # ------------------------------------------------------------------
    # Extraction automatique
    # ------------------------------------------------------------------

    def extract_facts_from_text(
        self,
        text: str,
        source: str = "conversation",
    ) -> List[Dict]:
        """
        Extrait automatiquement des faits depuis un texte libre
        en utilisant des patrons linguistiques français.

        Args:
            text:   Texte à analyser.
            source: Origine du texte (conversation, document, ...).

        Returns:
            Liste des faits extraits (dictionnaires avec id, category, key, value).
        """
        if not text or not text.strip():
            return []

        extracted: List[Dict] = []

        for spec in _EXTRACT_PATTERNS:
            for match in spec["pattern"].finditer(text):
                raw_value = match.group(1).strip()
                if not raw_value:
                    continue

                # Générer une clé lisible à partir du préfixe et d'un résumé
                key = self._build_key(spec["key_prefix"], raw_value)

                fact_id = self.add_fact(
                    category=spec["category"],
                    key=key,
                    value=raw_value,
                    source=source,
                    confidence=0.7,
                )
                extracted.append(
                    {
                        "id": fact_id,
                        "category": spec["category"],
                        "key": key,
                        "value": raw_value,
                    }
                )

        if extracted:
            logger.info(
                "%d fait(s) extrait(s) automatiquement depuis le texte", len(extracted)
            )
        return extracted

    # ------------------------------------------------------------------
    # Contexte pour le prompt
    # ------------------------------------------------------------------

    def get_context_for_prompt(self, query: str, max_facts: int = 5) -> str:
        """
        Construit une chaîne de contexte pertinente à injecter dans un prompt IA
        à partir des faits les plus pertinents pour la requête.

        Args:
            query:     Requête utilisateur courante.
            max_facts: Nombre maximum de faits à inclure.

        Returns:
            Chaîne formatée contenant les faits pertinents, ou chaîne vide
            si aucun fait pertinent n'est trouvé.
        """
        facts = self.search_facts(query, limit=max_facts)
        if not facts:
            return ""

        lines = ["[Base de connaissances]"]
        for fact in facts:
            confidence_pct = int(fact["confidence"] * 100)
            lines.append(
                f"- [{fact['category']}] {fact['key']}: {fact['value']} "
                f"(confiance: {confidence_pct}%)"
            )
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Utilitaires internes
    # ------------------------------------------------------------------

    @staticmethod
    def _build_key(prefix: str, value: str, max_length: int = 80) -> str:
        """
        Construit une clé descriptive à partir d'un préfixe et d'une valeur.

        Args:
            prefix:     Préfixe de catégorie.
            value:      Valeur brute extraite.
            max_length: Longueur maximale de la clé.

        Returns:
            Clé tronquée et nettoyée.
        """
        # Prendre les premiers mots significatifs de la valeur
        words = value.split()[:6]
        summary = " ".join(words)
        key = f"{prefix}: {summary}"
        if len(key) > max_length:
            key = key[: max_length - 3] + "..."
        return key

    def close(self) -> None:
        """Ferme la connexion SQLite du thread courant."""
        if hasattr(self._local, "connection") and self._local.connection is not None:
            self._local.connection.close()
            self._local.connection = None
            logger.info("Connexion à la base de connaissances fermée")

    def __del__(self) -> None:
        """Ferme proprement la connexion à la destruction de l'objet."""
        try:
            self.close()
        except Exception:
            pass
