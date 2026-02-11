"""
RLHF Manager - Système de Reinforcement Learning from Human Feedback intégré
Collecte automatiquement le feedback utilisateur et améliore le modèle
"""

import json
import sqlite3
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from utils.logger import setup_logger


class RLHFManager:
    """
    Gestionnaire RLHF intégré pour amélioration continue du modèle

    Fonctionnalités:
    - Collecte automatique du feedback utilisateur
    - Détection des bonnes/mauvaises réponses
    - Apprentissage progressif
    - Métriques et statistiques détaillées
    """

    def __init__(self, db_path: str = "data/rlhf_feedback.db"):
        """
        Initialise le gestionnaire RLHF

        Args:
            db_path: Chemin vers la base SQLite de feedback
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.logger = setup_logger("RLHFManager")

        # Initialiser la base de données
        self._init_database()

        # Statistiques en mémoire
        self.session_stats = {
            "positive_feedback": 0,
            "negative_feedback": 0,
            "neutral_feedback": 0,
            "total_interactions": 0,
            "session_start": time.time(),
        }

        self.logger.info("✅ RLHF Manager initialisé")

    def _init_database(self):
        """Initialise la base de données SQLite"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Table des interactions avec feedback
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                user_query TEXT NOT NULL,
                ai_response TEXT NOT NULL,
                feedback_type TEXT NOT NULL,  -- 'positive', 'negative', 'neutral'
                feedback_score INTEGER,  -- 0-5
                feedback_comment TEXT,
                intent TEXT,
                confidence REAL,
                context TEXT,
                model_version TEXT,
                response_time REAL
            )
        """
        )

        # Table des patterns appris
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS learned_patterns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pattern_type TEXT NOT NULL,  -- 'good_response', 'bad_response'
                user_query_pattern TEXT NOT NULL,
                response_pattern TEXT,
                confidence REAL DEFAULT 0.5,
                feedback_count INTEGER DEFAULT 0,
                last_updated TEXT NOT NULL,
                enabled INTEGER DEFAULT 1
            )
        """
        )

        # Table des métriques quotidiennes
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS daily_metrics (
                date TEXT PRIMARY KEY,
                total_interactions INTEGER DEFAULT 0,
                positive_feedback INTEGER DEFAULT 0,
                negative_feedback INTEGER DEFAULT 0,
                neutral_feedback INTEGER DEFAULT 0,
                average_score REAL DEFAULT 0.0,
                improvement_rate REAL DEFAULT 0.0
            )
        """
        )

        conn.commit()
        conn.close()

        self.logger.info("📊 Base de données RLHF initialisée")

    def record_interaction(
        self,
        user_query: str,
        ai_response: str,
        feedback_type: str = "neutral",
        feedback_score: Optional[int] = None,
        feedback_comment: Optional[str] = None,
        intent: str = "unknown",
        confidence: float = 0.0,
        context: Optional[Dict] = None,
        model_version: str = "unknown",
        response_time: float = 0.0,
    ) -> int:
        """
        Enregistre une interaction avec son feedback

        Args:
            user_query: Question/requête de l'utilisateur
            ai_response: Réponse de l'IA
            feedback_type: 'positive', 'negative', 'neutral'
            feedback_score: Score 0-5 (optionnel)
            feedback_comment: Commentaire libre (optionnel)
            intent: Intention détectée
            confidence: Confiance de la détection
            context: Contexte additionnel
            model_version: Version du modèle
            response_time: Temps de réponse en secondes

        Returns:
            ID de l'enregistrement
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO feedback (
                timestamp, user_query, ai_response, feedback_type,
                feedback_score, feedback_comment, intent, confidence,
                context, model_version, response_time
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                datetime.now().isoformat(),
                user_query,
                ai_response,
                feedback_type,
                feedback_score,
                feedback_comment,
                intent,
                confidence,
                json.dumps(context) if context else None,
                model_version,
                response_time,
            ),
        )

        interaction_id = cursor.lastrowid
        conn.commit()
        conn.close()

        # Mettre à jour les stats de session
        self.session_stats["total_interactions"] += 1
        if feedback_type == "positive":
            self.session_stats["positive_feedback"] += 1
        elif feedback_type == "negative":
            self.session_stats["negative_feedback"] += 1
        else:
            self.session_stats["neutral_feedback"] += 1

        # Mettre à jour les métriques quotidiennes
        self._update_daily_metrics(feedback_type, feedback_score)

        # Apprentissage automatique des patterns
        if feedback_type in ["positive", "negative"]:
            self._learn_from_feedback(
                user_query, ai_response, feedback_type, feedback_score or 3
            )

        return interaction_id

    def _learn_from_feedback(
        self, user_query: str, ai_response: str, feedback_type: str, score: int
    ):
        """
        Apprend des patterns depuis le feedback

        Args:
            user_query: Query de l'utilisateur
            ai_response: Réponse de l'IA
            feedback_type: Type de feedback
            score: Score du feedback
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        pattern_type = (
            "good_response" if feedback_type == "positive" else "bad_response"
        )

        # Extraire des patterns simples (mots-clés)
        query_pattern = self._extract_pattern(user_query)
        response_pattern = self._extract_pattern(ai_response)

        # Vérifier si le pattern existe déjà
        cursor.execute(
            """
            SELECT id, confidence, feedback_count
            FROM learned_patterns
            WHERE user_query_pattern = ? AND pattern_type = ?
        """,
            (query_pattern, pattern_type),
        )

        result = cursor.fetchone()

        if result:
            # Mettre à jour le pattern existant
            pattern_id, current_confidence, feedback_count = result

            # Ajuster la confiance basé sur le score
            score_weight = score / 5.0  # Normaliser 0-1
            new_confidence = (current_confidence * feedback_count + score_weight) / (
                feedback_count + 1
            )

            cursor.execute(
                """
                UPDATE learned_patterns
                SET confidence = ?, feedback_count = ?, last_updated = ?
                WHERE id = ?
            """,
                (
                    new_confidence,
                    feedback_count + 1,
                    datetime.now().isoformat(),
                    pattern_id,
                ),
            )
        else:
            # Créer un nouveau pattern
            initial_confidence = score / 5.0

            cursor.execute(
                """
                INSERT INTO learned_patterns (
                    pattern_type, user_query_pattern, response_pattern,
                    confidence, feedback_count, last_updated
                ) VALUES (?, ?, ?, ?, 1, ?)
            """,
                (
                    pattern_type,
                    query_pattern,
                    response_pattern,
                    initial_confidence,
                    datetime.now().isoformat(),
                ),
            )

        conn.commit()
        conn.close()

    def _extract_pattern(self, text: str, max_length: int = 100) -> str:
        """
        Extrait un pattern simple d'un texte (pour matching)

        Args:
            text: Texte source
            max_length: Longueur max du pattern

        Returns:
            Pattern extrait
        """
        # Normaliser
        text = text.lower().strip()

        # Extraire les mots-clés importants (simple heuristique)
        words = text.split()
        keywords = [w for w in words if len(w) > 3][:10]  # Top 10 mots significatifs

        pattern = " ".join(keywords)
        return pattern[:max_length]

    def _update_daily_metrics(self, feedback_type: str, score: Optional[int]):
        """Met à jour les métriques quotidiennes"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        today = datetime.now().strftime("%Y-%m-%d")

        # Récupérer ou créer l'entrée du jour
        cursor.execute(
            """
            SELECT total_interactions, positive_feedback, negative_feedback,
                   neutral_feedback, average_score
            FROM daily_metrics WHERE date = ?
        """,
            (today,),
        )

        result = cursor.fetchone()

        if result:
            total, positive, negative, neutral, avg_score = result
            total += 1

            if feedback_type == "positive":
                positive += 1
            elif feedback_type == "negative":
                negative += 1
            else:
                neutral += 1

            # Calculer la nouvelle moyenne
            if score is not None:
                avg_score = ((avg_score * (total - 1)) + score) / total

            # Calculer le taux d'amélioration (positifs / total)
            improvement_rate = positive / total if total > 0 else 0.0

            cursor.execute(
                """
                UPDATE daily_metrics
                SET total_interactions = ?, positive_feedback = ?,
                    negative_feedback = ?, neutral_feedback = ?,
                    average_score = ?, improvement_rate = ?
                WHERE date = ?
            """,
                (
                    total,
                    positive,
                    negative,
                    neutral,
                    avg_score,
                    improvement_rate,
                    today,
                ),
            )
        else:
            # Créer nouvelle entrée
            positive = 1 if feedback_type == "positive" else 0
            negative = 1 if feedback_type == "negative" else 0
            neutral = 1 if feedback_type == "neutral" else 0
            avg_score = score if score is not None else 0.0
            improvement_rate = positive / 1.0

            cursor.execute(
                """
                INSERT INTO daily_metrics (
                    date, total_interactions, positive_feedback,
                    negative_feedback, neutral_feedback, average_score,
                    improvement_rate
                ) VALUES (?, 1, ?, ?, ?, ?, ?)
            """,
                (today, positive, negative, neutral, avg_score, improvement_rate),
            )

        conn.commit()
        conn.close()

    def get_learned_patterns(
        self, pattern_type: Optional[str] = None, min_confidence: float = 0.5
    ) -> List[Dict[str, Any]]:
        """
        Récupère les patterns appris

        Args:
            pattern_type: Type de pattern ('good_response', 'bad_response', None pour tous)
            min_confidence: Confiance minimale

        Returns:
            Liste de patterns
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        if pattern_type:
            cursor.execute(
                """
                SELECT * FROM learned_patterns
                WHERE pattern_type = ? AND confidence >= ? AND enabled = 1
                ORDER BY confidence DESC, feedback_count DESC
            """,
                (pattern_type, min_confidence),
            )
        else:
            cursor.execute(
                """
                SELECT * FROM learned_patterns
                WHERE confidence >= ? AND enabled = 1
                ORDER BY confidence DESC, feedback_count DESC
            """,
                (min_confidence,),
            )

        columns = [desc[0] for desc in cursor.description]
        patterns = [dict(zip(columns, row)) for row in cursor.fetchall()]

        conn.close()
        return patterns

    def get_statistics(self, period: str = "all") -> Dict[str, Any]:
        """
        Récupère les statistiques RLHF

        Args:
            period: 'session', 'today', 'week', 'month', 'all'

        Returns:
            Dictionnaire de statistiques
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        stats = {}

        if period == "session":
            # Stats de la session en cours
            stats = {**self.session_stats}

            # Calculer des ratios
            total = stats["total_interactions"]
            if total > 0:
                stats["positive_rate"] = stats["positive_feedback"] / total
                stats["negative_rate"] = stats["negative_feedback"] / total
                stats["satisfaction_score"] = (
                    stats["positive_feedback"] - stats["negative_feedback"]
                ) / total
            else:
                stats["positive_rate"] = 0.0
                stats["negative_rate"] = 0.0
                stats["satisfaction_score"] = 0.0

        elif period == "today":
            # Stats du jour
            today = datetime.now().strftime("%Y-%m-%d")
            cursor.execute(
                """
                SELECT * FROM daily_metrics WHERE date = ?
            """,
                (today,),
            )

            result = cursor.fetchone()
            if result:
                columns = [desc[0] for desc in cursor.description]
                stats = dict(zip(columns, result))
            else:
                stats = {
                    "total_interactions": 0,
                    "positive_feedback": 0,
                    "negative_feedback": 0,
                    "average_score": 0.0,
                    "improvement_rate": 0.0,
                }

        else:
            # Stats globales
            cursor.execute(
                """
                SELECT 
                    COUNT(*) as total_interactions,
                    SUM(CASE WHEN feedback_type = 'positive' THEN 1 ELSE 0 END) as positive_feedback,
                    SUM(CASE WHEN feedback_type = 'negative' THEN 1 ELSE 0 END) as negative_feedback,
                    SUM(CASE WHEN feedback_type = 'neutral' THEN 1 ELSE 0 END) as neutral_feedback,
                    AVG(CASE WHEN feedback_score IS NOT NULL THEN feedback_score ELSE 0 END) as average_score
                FROM feedback
            """
            )

            result = cursor.fetchone()
            if result:
                total, positive, negative, neutral, avg_score = result
                stats = {
                    "total_interactions": total or 0,
                    "positive_feedback": positive or 0,
                    "negative_feedback": negative or 0,
                    "neutral_feedback": neutral or 0,
                    "average_score": avg_score or 0.0,
                    "positive_rate": (positive / total) if total > 0 else 0.0,
                    "negative_rate": (negative / total) if total > 0 else 0.0,
                    "satisfaction_score": (
                        ((positive - negative) / total) if total > 0 else 0.0
                    ),
                }
            else:
                stats = {
                    "total_interactions": 0,
                    "positive_feedback": 0,
                    "negative_feedback": 0,
                    "average_score": 0.0,
                }

        # Ajouter le nombre de patterns appris
        cursor.execute("SELECT COUNT(*) FROM learned_patterns WHERE enabled = 1")
        stats["learned_patterns_count"] = cursor.fetchone()[0]

        conn.close()
        return stats

    def get_recent_feedback(self, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Récupère les feedbacks récents

        Args:
            limit: Nombre de feedbacks à retourner

        Returns:
            Liste de feedbacks
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT * FROM feedback
            ORDER BY timestamp DESC
            LIMIT ?
        """,
            (limit,),
        )

        columns = [desc[0] for desc in cursor.description]
        feedbacks = [dict(zip(columns, row)) for row in cursor.fetchall()]

        conn.close()
        return feedbacks

    def export_training_data(self, output_path: str, min_score: int = 3):
        """
        Exporte les données pour entraînement au format JSONL

        Args:
            output_path: Chemin du fichier de sortie
            min_score: Score minimum pour inclure (filtre qualité)
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Récupérer les interactions positives
        cursor.execute(
            """
            SELECT user_query, ai_response, feedback_score
            FROM feedback
            WHERE feedback_type = 'positive'
            AND (feedback_score IS NULL OR feedback_score >= ?)
            ORDER BY timestamp DESC
        """,
            (min_score,),
        )

        training_data = []
        for row in cursor.fetchall():
            training_data.append({"input": row[0], "target": row[1], "score": row[2]})

        conn.close()

        # Sauvegarder au format JSONL
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, "w", encoding="utf-8") as f:
            for item in training_data:
                f.write(json.dumps(item, ensure_ascii=False) + "\n")

        self.logger.info(
            "✅ %d exemples exportés vers %s",
            len(training_data),
            output_path
        )

        return len(training_data)

    def reset_session_stats(self):
        """Réinitialise les statistiques de session"""
        self.session_stats = {
            "positive_feedback": 0,
            "negative_feedback": 0,
            "neutral_feedback": 0,
            "total_interactions": 0,
            "session_start": time.time(),
        }


# Singleton global
_RLHF_MANAGER_INSTANCE = None


def get_rlhf_manager() -> RLHFManager:
    """Récupère l'instance singleton du RLHF Manager"""
    global _RLHF_MANAGER_INSTANCE
    if _RLHF_MANAGER_INSTANCE is None:
        _RLHF_MANAGER_INSTANCE = RLHFManager()
    return _RLHF_MANAGER_INSTANCE
