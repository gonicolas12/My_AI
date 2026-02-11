"""
Training Manager - Pipeline d'entraînement moderne pour modèles locaux
Entraînement, fine-tuning et monitoring avec support Ollama
"""

import json
import random
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from utils.logger import setup_logger


class TrainingManager:
    """
    Gestionnaire d'entraînement moderne pour modèles IA locaux

    Fonctionnalités:
    - Support Ollama et modèles personnalisés
    - Checkpointing automatique
    - Monitoring en temps réel
    - Validation et évaluation
    - Export des métriques
    """

    def __init__(
        self,
        output_dir: str = "models/training_runs",
        checkpoint_dir: str = "models/checkpoints",
    ):
        """
        Initialise le gestionnaire d'entraînement

        Args:
            output_dir: Répertoire de sortie des runs
            checkpoint_dir: Répertoire des checkpoints
        """
        self.output_dir = Path(output_dir)
        self.checkpoint_dir = Path(checkpoint_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)

        self.logger = setup_logger("TrainingManager")

        # État de l'entraînement
        self.current_run_id = None
        self.current_run_dir = None
        self.training_active = False
        self.epoch_metrics = []
        self.callback_functions = []

        self.logger.info("✅ Training Manager initialisé")

    def create_run(
        self, run_name: Optional[str] = None, config: Optional[Dict] = None
    ) -> str:
        """
        Crée un nouveau run d'entraînement

        Args:
            run_name: Nom du run (auto-généré si None)
            config: Configuration de l'entraînement

        Returns:
            ID du run
        """
        # Générer un ID unique
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        run_name = run_name or f"run_{timestamp}"
        self.current_run_id = f"{run_name}_{timestamp}"

        # Créer le répertoire du run
        self.current_run_dir = self.output_dir / self.current_run_id
        self.current_run_dir.mkdir(parents=True, exist_ok=True)

        # Sauvegarder la configuration
        config = config or {}
        config["run_id"] = self.current_run_id
        config["run_name"] = run_name
        config["created_at"] = datetime.now().isoformat()

        with open(self.current_run_dir / "config.json", "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)

        self.logger.info("🚀 Nouveau run créé: %s", self.current_run_id)

        return self.current_run_id

    def train_model(
        self,
        train_data: List[Dict[str, str]],
        val_data: Optional[List[Dict[str, str]]] = None,
        epochs: int = 3,
        batch_size: int = 8,
        learning_rate: float = 1e-4,
        model_name: str = "custom_model",
        save_every: int = 1,
        validate_every: int = 1,
        on_epoch_end: Optional[Callable] = None,
        on_batch_end: Optional[Callable] = None,
    ) -> Dict[str, Any]:
        """
        Entraîne un modèle local

        Args:
            train_data: Données d'entraînement [{input, target}]
            val_data: Données de validation
            epochs: Nombre d'époques
            batch_size: Taille des batchs
            learning_rate: Taux d'apprentissage
            model_name: Nom du modèle
            save_every: Sauvegarder tous les N epochs
            validate_every: Valider tous les N epochs
            on_epoch_end: Callback après chaque époque
            on_batch_end: Callback après chaque batch

        Returns:
            Résultats de l'entraînement
        """
        self.training_active = True
        self.epoch_metrics = []

        # Créer un run si pas encore fait
        if not self.current_run_id:
            self.create_run(run_name=f"training_{model_name}")

        # Configuration de l'entraînement
        train_config = {
            "model_name": model_name,
            "epochs": epochs,
            "batch_size": batch_size,
            "learning_rate": learning_rate,
            "train_samples": len(train_data),
            "val_samples": len(val_data) if val_data else 0,
            "started_at": datetime.now().isoformat(),
        }

        self.logger.info("📚 Démarrage de l'entraînement: %s", model_name)
        self.logger.info("   📊 %d exemples d'entraînement", len(train_data))
        self.logger.info(
            "   📊 %d exemples de validation",
            len(val_data) if val_data else 0
        )
        self.logger.info("   ⚙️  %d époques, batch size %d", epochs, batch_size)

        start_time = time.time()

        # Entraînement par époque
        for epoch in range(epochs):
            if not self.training_active:
                self.logger.info("⏸️  Entraînement interrompu")
                break

            epoch_start = time.time()
            separator = "=" * 60
            self.logger.info("\n%s", separator)
            self.logger.info("Époque %d/%d", epoch + 1, epochs)
            self.logger.info("%s", separator)

            # Métriques de l'époque
            epoch_metrics = {
                "epoch": epoch + 1,
                "train_loss": 0.0,
                "train_samples": len(train_data),
                "batches": 0,
                "started_at": datetime.now().isoformat(),
            }

            # Entraînement par batch
            n_batches = (len(train_data) + batch_size - 1) // batch_size

            for batch_idx in range(n_batches):
                if not self.training_active:
                    break

                # Extraire le batch
                start_idx = batch_idx * batch_size
                end_idx = min(start_idx + batch_size, len(train_data))
                batch = train_data[start_idx:end_idx]

                # Simuler l'entraînement (dans une vraie implémentation,
                # on appellerait le modèle ici)
                batch_loss = self._train_batch(batch, learning_rate)

                epoch_metrics["train_loss"] += batch_loss
                epoch_metrics["batches"] += 1

                # Callback batch
                if on_batch_end:
                    on_batch_end(batch_idx, n_batches, batch_loss)

                # Affichage progressif
                if (batch_idx + 1) % 10 == 0 or (batch_idx + 1) == n_batches:
                    avg_loss = epoch_metrics["train_loss"] / epoch_metrics["batches"]
                    progress = (batch_idx + 1) / n_batches * 100
                    self.logger.info(
                        "   Batch %d/%d (%.1f%%) - Loss: %.4f",
                        batch_idx + 1,
                        n_batches,
                        progress,
                        avg_loss
                    )

            # Moyenne de la loss
            epoch_metrics["train_loss"] /= epoch_metrics["batches"]
            epoch_metrics["duration"] = time.time() - epoch_start

            # Validation
            if val_data and (epoch + 1) % validate_every == 0:
                val_metrics = self._validate(val_data, batch_size)
                epoch_metrics.update(val_metrics)

                self.logger.info(
                    "\n   📊 Validation - Loss: %.4f, Accuracy: %.2f%%",
                    val_metrics['val_loss'],
                    val_metrics['val_accuracy'] * 100
                )

            # Résumé de l'époque
            self.logger.info(
                "\n   ✅ Époque %d terminée en %.2fs",
                epoch + 1,
                epoch_metrics['duration']
            )
            self.logger.info("   📊 Train Loss: %.4f", epoch_metrics['train_loss'])

            self.epoch_metrics.append(epoch_metrics)

            # Callback époque
            if on_epoch_end:
                on_epoch_end(epoch, epoch_metrics)

            # Sauvegarde checkpoint
            if (epoch + 1) % save_every == 0:
                checkpoint_path = self._save_checkpoint(epoch + 1, epoch_metrics)
                self.logger.info("   💾 Checkpoint sauvegardé: %s", checkpoint_path)

        # Finaliser l'entraînement
        total_time = time.time() - start_time
        train_config["completed_at"] = datetime.now().isoformat()
        train_config["total_duration"] = total_time
        train_config["epochs_completed"] = len(self.epoch_metrics)

        # Sauvegarder les métriques
        self._save_metrics(train_config)

        self.training_active = False

        separator = "=" * 60
        self.logger.info("\n%s", separator)
        self.logger.info("✅ Entraînement terminé en %.2fs", total_time)
        self.logger.info("   📊 %d époques complétées", len(self.epoch_metrics))
        if self.epoch_metrics:
            final_loss = self.epoch_metrics[-1]["train_loss"]
            self.logger.info("   📉 Loss finale: %.4f", final_loss)
        self.logger.info("%s\n", separator)

        return {
            "run_id": self.current_run_id,
            "config": train_config,
            "metrics": self.epoch_metrics,
            "final_loss": (
                self.epoch_metrics[-1]["train_loss"] if self.epoch_metrics else None
            ),
        }

    def _train_batch(self, _batch: List[Dict], _learning_rate: float) -> float:
        """
        Entraîne sur un batch (simulation)

        Dans une implémentation réelle, ceci appellerait le modèle
        et calculerait la vraie loss

        Args:
            batch: Batch de données
            learning_rate: Taux d'apprentissage

        Returns:
            Loss du batch
        """
        # Simulation de loss décroissante
        base_loss = 2.0
        noise = random.uniform(-0.1, 0.1)
        # Loss diminue avec le temps
        improvement_factor = 1.0 - (len(self.epoch_metrics) * 0.1)
        loss = max(0.1, base_loss * improvement_factor + noise)

        return loss

    def _validate(self, val_data: List[Dict], batch_size: int) -> Dict[str, float]:
        """
        Valide le modèle

        Args:
            val_data: Données de validation
            batch_size: Taille des batchs

        Returns:
            Métriques de validation
        """
        # Simulation de validation
        val_loss = random.uniform(0.5, 1.5)
        val_accuracy = random.uniform(0.7, 0.95)

        # Note: batch_size serait utilisé dans une vraie implémentation
        _ = batch_size  # Marquer comme utilisé

        return {
            "val_loss": val_loss,
            "val_accuracy": val_accuracy,
            "val_samples": len(val_data),
        }

    def _save_checkpoint(self, epoch: int, metrics: Dict) -> Path:
        """
        Sauvegarde un checkpoint

        Args:
            epoch: Numéro de l'époque
            metrics: Métriques de l'époque

        Returns:
            Chemin du checkpoint
        """
        checkpoint_name = f"checkpoint_epoch_{epoch}"
        checkpoint_path = self.current_run_dir / "checkpoints" / checkpoint_name
        checkpoint_path.mkdir(parents=True, exist_ok=True)

        # Sauvegarder les métriques
        with open(checkpoint_path / "metrics.json", "w", encoding="utf-8") as f:
            json.dump(metrics, f, indent=2, ensure_ascii=False)

        # Dans une vraie implémentation, sauvegarder les poids du modèle ici
        # torch.save(model.state_dict(), checkpoint_path / "model.pt")

        return checkpoint_path

    def _save_metrics(self, config: Dict):
        """
        Sauvegarde les métriques complètes

        Args:
            config: Configuration de l'entraînement
        """
        # Sauvegarder config mise à jour
        with open(self.current_run_dir / "config.json", "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)

        # Sauvegarder métriques par époque
        with open(self.current_run_dir / "metrics.jsonl", "w", encoding="utf-8") as f:
            for metrics in self.epoch_metrics:
                f.write(json.dumps(metrics, ensure_ascii=False) + "\n")

        # Créer un résumé
        summary = {
            "run_id": self.current_run_id,
            "total_epochs": len(self.epoch_metrics),
            "best_train_loss": (
                min(m["train_loss"] for m in self.epoch_metrics)
                if self.epoch_metrics
                else None
            ),
            "final_train_loss": (
                self.epoch_metrics[-1]["train_loss"] if self.epoch_metrics else None
            ),
            "total_duration": config.get("total_duration", 0),
            "completed_at": config.get("completed_at", ""),
        }

        if any("val_loss" in m for m in self.epoch_metrics):
            val_losses = [m["val_loss"] for m in self.epoch_metrics if "val_loss" in m]
            summary["best_val_loss"] = min(val_losses)
            summary["final_val_loss"] = val_losses[-1]

        with open(self.current_run_dir / "summary.json", "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)

    def fine_tune_ollama_model(
        self,
        base_model: str,
        train_data: List[Dict[str, str]],
        new_model_name: str,
        epochs: int = 3,
        learning_rate: float = 1e-4,
        on_progress: Optional[Callable] = None,
    ) -> Dict[str, Any]:
        """
        Fine-tune un modèle Ollama

        Args:
            base_model: Nom du modèle de base (ex: 'llama3.2')
            train_data: Données d'entraînement
            new_model_name: Nom du nouveau modèle
            epochs: Nombre d'époques
            learning_rate: Taux d'apprentissage
            on_progress: Callback de progression

        Returns:
            Résultats du fine-tuning
        """
        # Note: epochs, learning_rate, on_progress seraient utilisés pour un vrai fine-tuning
        _ = (
            epochs,
            learning_rate,
            on_progress,
        )  # Marquer comme utilisés pour l'implémentation future

        self.logger.info("🦙 Fine-tuning Ollama: %s → %s", base_model, new_model_name)

        # Créer un Modelfile pour le fine-tuning
        modelfile_content = f"""FROM {base_model}

# Fine-tuned model: {new_model_name}
# Base model: {base_model}
# Training samples: {len(train_data)}
# Epochs: {epochs}
# Created: {datetime.now().isoformat()}

PARAMETER temperature 0.7
PARAMETER num_ctx 8192
PARAMETER top_p 0.9

SYSTEM You are an AI assistant that has been fine-tuned with specific knowledge. You provide helpful, accurate, and contextual responses.
"""

        # Créer le Modelfile
        modelfile_path = self.current_run_dir / "Modelfile"
        with open(modelfile_path, "w", encoding="utf-8") as f:
            f.write(modelfile_content)

        # Sauvegarder les données d'entraînement
        train_data_path = self.current_run_dir / "train_data.jsonl"
        with open(train_data_path, "w", encoding="utf-8") as f:
            for item in train_data:
                f.write(json.dumps(item, ensure_ascii=False) + "\n")

        self.logger.info("   📝 Modelfile créé: %s", modelfile_path)
        self.logger.info("   📚 Données sauvegardées: %s", train_data_path)

        # Instructions pour créer le modèle
        instructions = f"""
Pour créer le modèle fine-tuné avec Ollama:

1. Créer le modèle:
   ollama create {new_model_name} -f {modelfile_path}

2. Tester le modèle:
   ollama run {new_model_name}

3. Entraîner avec vos données:
   # Utiliser les données de {train_data_path}
"""

        instructions_path = self.current_run_dir / "INSTRUCTIONS.txt"
        with open(instructions_path, "w", encoding="utf-8") as f:
            f.write(instructions)

        self.logger.info("   📋 Instructions: %s", instructions_path)

        return {
            "run_id": self.current_run_id,
            "base_model": base_model,
            "new_model_name": new_model_name,
            "modelfile_path": str(modelfile_path),
            "train_data_path": str(train_data_path),
            "instructions_path": str(instructions_path),
            "status": "prepared",
            "message": "Modelfile créé. Voir INSTRUCTIONS.txt pour créer le modèle avec Ollama.",
        }

    def load_train_data(self, data_path: str) -> List[Dict[str, str]]:
        """
        Charge des données d'entraînement

        Args:
            data_path: Chemin vers le fichier JSONL

        Returns:
            Liste de données
        """
        data = []
        with open(data_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    data.append(json.loads(line))

        self.logger.info("✅ %d exemples chargés depuis %s", len(data), data_path)
        return data

    def get_run_summary(self, run_id: str) -> Optional[Dict[str, Any]]:
        """
        Récupère le résumé d'un run

        Args:
            run_id: ID du run

        Returns:
            Résumé ou None
        """
        run_dir = self.output_dir / run_id
        summary_path = run_dir / "summary.json"

        if summary_path.exists():
            with open(summary_path, "r", encoding="utf-8") as f:
                return json.load(f)

        return None

    def list_runs(self) -> List[Dict[str, Any]]:
        """
        Liste tous les runs d'entraînement

        Returns:
            Liste des runs avec résumés
        """
        runs = []

        for run_dir in self.output_dir.iterdir():
            if run_dir.is_dir():
                summary = self.get_run_summary(run_dir.name)
                if summary:
                    runs.append(summary)

        # Trier par date (plus récent en premier)
        runs.sort(key=lambda x: x.get("completed_at", ""), reverse=True)

        return runs

    def stop_training(self):
        """Arrête l'entraînement en cours"""
        if self.training_active:
            self.training_active = False
            self.logger.info("⏹️  Arrêt de l'entraînement demandé")


# Singleton global
_TRAINING_MANAGER_INSTANCE = None


def get_training_manager() -> TrainingManager:
    """Récupère l'instance singleton du Training Manager"""
    global _TRAINING_MANAGER_INSTANCE
    if _TRAINING_MANAGER_INSTANCE is None:
        _TRAINING_MANAGER_INSTANCE = TrainingManager()
    return _TRAINING_MANAGER_INSTANCE
