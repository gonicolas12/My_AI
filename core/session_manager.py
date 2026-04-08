"""
Gestionnaire de workspaces et sessions pour My_AI v7.1.0
Regroupe conversation, documents, agents et parametres dans une unite nommee et sauvegardable.
"""

import json
import re
import shutil
import threading
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from utils.logger import setup_logger

logger = setup_logger("session_manager")


def _slugify(text: str) -> str:
    """
    Transforme un texte en slug URL-safe pour les noms de dossiers.

    Args:
        text: Texte a transformer

    Returns:
        Chaine slugifiee en minuscules, sans caracteres speciaux
    """
    text = text.lower().strip()
    text = re.sub(r"[àáâãäå]", "a", text)
    text = re.sub(r"[èéêë]", "e", text)
    text = re.sub(r"[ìíîï]", "i", text)
    text = re.sub(r"[òóôõö]", "o", text)
    text = re.sub(r"[ùúûü]", "u", text)
    text = re.sub(r"[ç]", "c", text)
    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = text.strip("-")
    return text


class SessionManager:
    """
    Gestionnaire de workspaces pour l'assistant IA local.

    Chaque workspace regroupe une conversation, des documents attaches,
    les agents actifs, les parametres et les metadonnees dans une unite
    nommee et persistee sur disque au format JSON.
    """

    def __init__(self, workspaces_dir: str = "data/workspaces") -> None:
        """
        Initialise le gestionnaire de sessions.

        Args:
            workspaces_dir: Chemin du repertoire racine des workspaces
        """
        self._workspaces_dir = Path(workspaces_dir)
        self._workspaces_dir.mkdir(parents=True, exist_ok=True)
        self._current_workspace_id: Optional[str] = None
        self._lock = threading.Lock()
        logger.info(
            "SessionManager initialise avec repertoire: %s",
            self._workspaces_dir.resolve(),
        )

    def create_workspace(self, name: str, description: str = "") -> str:
        """
        Cree un nouveau workspace avec un identifiant unique.

        Args:
            name: Nom lisible du workspace
            description: Description optionnelle du workspace

        Returns:
            Identifiant unique du workspace (slug + uuid court)

        Raises:
            ValueError: Si le nom est vide ou invalide
        """
        if not name or not name.strip():
            raise ValueError("Le nom du workspace ne peut pas etre vide")

        slug = _slugify(name)
        if not slug:
            raise ValueError(
                f"Le nom '{name}' ne produit pas de slug valide"
            )

        short_id = uuid.uuid4().hex[:8]
        workspace_id = f"{slug}-{short_id}"

        workspace_path = self._workspaces_dir / workspace_id
        with self._lock:
            workspace_path.mkdir(parents=True, exist_ok=True)

            now = datetime.now().isoformat()
            metadata = {
                "id": workspace_id,
                "name": name.strip(),
                "description": description.strip(),
                "created_at": now,
                "last_modified": now,
                "message_count": 0,
            }

            initial_state = {
                "conversation_history": [],
                "attached_documents": [],
                "active_agents": [],
                "settings": {},
                "metadata": metadata,
            }

            self._write_json(workspace_path / "metadata.json", metadata)
            self._write_json(workspace_path / "state.json", initial_state)

        logger.info("Workspace cree: '%s' (id=%s)", name, workspace_id)
        return workspace_id

    def save_workspace(self, workspace_id: str, state: dict) -> bool:
        """
        Sauvegarde l'etat complet d'un workspace.

        L'etat attendu contient les cles: conversation_history,
        attached_documents, active_agents, settings, metadata.

        Args:
            workspace_id: Identifiant du workspace
            state: Dictionnaire representant l'etat complet

        Returns:
            True si la sauvegarde a reussi, False sinon
        """
        workspace_path = self._workspaces_dir / workspace_id
        if not workspace_path.is_dir():
            logger.error(
                "Sauvegarde impossible: workspace '%s' introuvable",
                workspace_id,
            )
            return False

        try:
            with self._lock:
                metadata = self._read_json(workspace_path / "metadata.json")
                if metadata is None:
                    logger.error(
                        "Metadonnees corrompues pour le workspace '%s'",
                        workspace_id,
                    )
                    return False

                metadata["last_modified"] = datetime.now().isoformat()
                metadata["message_count"] = len(
                    state.get("conversation_history", [])
                )

                if "metadata" in state:
                    user_meta = state["metadata"]
                    for key in ("name", "description"):
                        if key in user_meta:
                            metadata[key] = user_meta[key]

                state_to_save = {
                    "conversation_history": state.get("conversation_history", []),
                    "attached_documents": state.get("attached_documents", []),
                    "active_agents": state.get("active_agents", []),
                    "settings": state.get("settings", {}),
                    "metadata": metadata,
                }

                self._write_json(workspace_path / "state.json", state_to_save)
                self._write_json(workspace_path / "metadata.json", metadata)

            logger.info("Workspace '%s' sauvegarde avec succes", workspace_id)
            return True

        except Exception as exc:
            logger.error(
                "Erreur lors de la sauvegarde du workspace '%s': %s",
                workspace_id,
                exc,
            )
            return False

    def load_workspace(self, workspace_id: str) -> Optional[dict]:
        """
        Charge l'etat complet d'un workspace depuis le disque.

        Args:
            workspace_id: Identifiant du workspace a charger

        Returns:
            Dictionnaire de l'etat du workspace, ou None si introuvable/corrompu
        """
        workspace_path = self._workspaces_dir / workspace_id
        if not workspace_path.is_dir():
            logger.warning(
                "Chargement impossible: workspace '%s' introuvable",
                workspace_id,
            )
            return None

        with self._lock:
            state = self._read_json(workspace_path / "state.json")

        if state is None:
            logger.error(
                "Etat corrompu pour le workspace '%s'", workspace_id
            )
            return None

        logger.info("Workspace '%s' charge avec succes", workspace_id)
        return state

    def list_workspaces(self) -> List[dict]:
        """
        Liste tous les workspaces disponibles avec leurs informations resumees.

        Returns:
            Liste de dictionnaires contenant id, name, description,
            last_modified et message_count pour chaque workspace
        """
        workspaces: List[dict] = []

        if not self._workspaces_dir.exists():
            return workspaces

        with self._lock:
            for entry in sorted(self._workspaces_dir.iterdir()):
                if not entry.is_dir():
                    continue

                metadata_path = entry / "metadata.json"
                metadata = self._read_json(metadata_path)
                if metadata is None:
                    logger.warning(
                        "Metadonnees manquantes ou corrompues pour '%s', ignore",
                        entry.name,
                    )
                    continue

                workspaces.append(
                    {
                        "id": metadata.get("id", entry.name),
                        "name": metadata.get("name", entry.name),
                        "description": metadata.get("description", ""),
                        "last_modified": metadata.get("last_modified", ""),
                        "message_count": metadata.get("message_count", 0),
                    }
                )

        workspaces.sort(key=lambda w: w["last_modified"], reverse=True)
        return workspaces

    def delete_workspace(self, workspace_id: str) -> bool:
        """
        Supprime un workspace et tout son contenu du disque.

        Args:
            workspace_id: Identifiant du workspace a supprimer

        Returns:
            True si la suppression a reussi, False sinon
        """
        workspace_path = self._workspaces_dir / workspace_id
        if not workspace_path.is_dir():
            logger.warning(
                "Suppression impossible: workspace '%s' introuvable",
                workspace_id,
            )
            return False

        try:
            with self._lock:
                shutil.rmtree(workspace_path)

                if self._current_workspace_id == workspace_id:
                    self._current_workspace_id = None

            logger.info("Workspace '%s' supprime", workspace_id)
            return True

        except Exception as exc:
            logger.error(
                "Erreur lors de la suppression du workspace '%s': %s",
                workspace_id,
                exc,
            )
            return False

    def rename_workspace(self, workspace_id: str, new_name: str) -> bool:
        """
        Renomme un workspace existant sans changer son identifiant.

        Args:
            workspace_id: Identifiant du workspace a renommer
            new_name: Nouveau nom lisible

        Returns:
            True si le renommage a reussi, False sinon

        Raises:
            ValueError: Si le nouveau nom est vide
        """
        if not new_name or not new_name.strip():
            raise ValueError("Le nouveau nom ne peut pas etre vide")

        workspace_path = self._workspaces_dir / workspace_id
        if not workspace_path.is_dir():
            logger.warning(
                "Renommage impossible: workspace '%s' introuvable",
                workspace_id,
            )
            return False

        try:
            with self._lock:
                metadata = self._read_json(workspace_path / "metadata.json")
                if metadata is None:
                    return False

                old_name = metadata.get("name", "")
                metadata["name"] = new_name.strip()
                metadata["last_modified"] = datetime.now().isoformat()
                self._write_json(workspace_path / "metadata.json", metadata)

                state = self._read_json(workspace_path / "state.json")
                if state and "metadata" in state:
                    state["metadata"]["name"] = new_name.strip()
                    state["metadata"]["last_modified"] = metadata["last_modified"]
                    self._write_json(workspace_path / "state.json", state)

            logger.info(
                "Workspace '%s' renomme: '%s' -> '%s'",
                workspace_id,
                old_name,
                new_name.strip(),
            )
            return True

        except Exception as exc:
            logger.error(
                "Erreur lors du renommage du workspace '%s': %s",
                workspace_id,
                exc,
            )
            return False

    def get_current_workspace(self) -> Optional[str]:
        """
        Retourne l'identifiant du workspace actuellement actif.

        Returns:
            Identifiant du workspace courant, ou None si aucun n'est actif
        """
        return self._current_workspace_id

    def set_current_workspace(self, workspace_id: str) -> None:
        """
        Definit le workspace actif pour la session en cours.

        Args:
            workspace_id: Identifiant du workspace a activer

        Raises:
            ValueError: Si le workspace n'existe pas
        """
        workspace_path = self._workspaces_dir / workspace_id
        if not workspace_path.is_dir():
            raise ValueError(
                f"Le workspace '{workspace_id}' n'existe pas"
            )

        self._current_workspace_id = workspace_id
        logger.info("Workspace actif defini: '%s'", workspace_id)

    def auto_save(self, workspace_id: str, state: dict) -> bool:
        """
        Sauvegarde automatique periodique d'un workspace.

        Identique a save_workspace mais avec journalisation distincte
        pour differencier les sauvegardes manuelles des automatiques.

        Args:
            workspace_id: Identifiant du workspace
            state: Dictionnaire representant l'etat complet

        Returns:
            True si la sauvegarde automatique a reussi, False sinon
        """
        logger.debug("Auto-save declenche pour le workspace '%s'", workspace_id)
        success = self.save_workspace(workspace_id, state)
        if success:
            logger.debug(
                "Auto-save termine avec succes pour '%s'", workspace_id
            )
        else:
            logger.warning(
                "Echec de l'auto-save pour le workspace '%s'", workspace_id
            )
        return success

    # ------------------------------------------------------------------
    # Methodes internes
    # ------------------------------------------------------------------

    @staticmethod
    def _write_json(path: Path, data: Dict[str, Any]) -> None:
        """
        Ecrit un dictionnaire en JSON sur disque de maniere atomique.

        Utilise un fichier temporaire puis un renommage pour eviter
        la corruption en cas d'interruption.

        Args:
            path: Chemin du fichier JSON cible
            data: Donnees a serialiser
        """
        tmp_path = path.with_suffix(".json.tmp")
        try:
            with open(tmp_path, "w", encoding="utf-8") as fh:
                json.dump(data, fh, indent=2, ensure_ascii=False, default=str)
            tmp_path.replace(path)
        except Exception:
            if tmp_path.exists():
                tmp_path.unlink()
            raise

    @staticmethod
    def _read_json(path: Path) -> Optional[Dict[str, Any]]:
        """
        Lit et deserialise un fichier JSON depuis le disque.

        Args:
            path: Chemin du fichier JSON a lire

        Returns:
            Dictionnaire deserialise, ou None si le fichier est absent ou invalide
        """
        if not path.is_file():
            return None
        try:
            with open(path, "r", encoding="utf-8") as fh:
                return json.load(fh)
        except (json.JSONDecodeError, OSError) as exc:
            logger.error("Lecture JSON echouee pour '%s': %s", path, exc)
            return None
