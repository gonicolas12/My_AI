"""
Dossiers projet de la session courante (section « Dossiers du projet »)

Repris de interfaces/gui/sidebar.py (_folder_attach, _folder_reindex,
_folder_detach, _index_folder_async) : un dossier entier (codebase,
documents) est indexé dans la mémoire vectorielle de la session, en arrière-
plan, par core/folder_indexer.py. Sans session courante, une session est créée
au nom du dossier, comme dans Tk.

La progression part en événements (folders.progress, toutes les 10 fichiers
comme Tk) ; la fin, en notification et en folders.changed.
"""

import os
import threading
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from core.i18n import tr
from utils.logger import setup_logger

if TYPE_CHECKING:  # pragma: no cover
    from interfaces.desktop.lifecycle import DesktopApp

logger = setup_logger("DesktopFolders")

# Progression publiée tous les N fichiers (et au dernier), comme les notifications de Tk
_PROGRESS_EVERY = 10


class FolderError(Exception):
    """Action refusée ; le message s'affiche tel quel."""


def folder_name(path: str) -> str:
    """Nom affiché d'un dossier."""
    return Path(path).name or path


class FolderService:
    """Attache, réindexe et détache les dossiers projet de la session courante."""

    def __init__(self, app: "DesktopApp"):
        self._app = app
        self._lock = threading.Lock()
        self._running: Dict[str, Dict[str, Any]] = {}

    # ── Accès ───────────────────────────────────────────────────────────────

    def _indexer(self):
        engine = getattr(self._app, "engine", None)
        getter = getattr(engine, "get_folder_indexer", None)
        if getter is None:
            return None
        try:
            return getter()
        except Exception:  # pylint: disable=broad-except
            return None

    def _session_id(self) -> Optional[str]:
        chat = self._app.chat
        return chat.session_id if chat is not None else None

    def _publish(self, event_type: str, payload: Dict[str, Any]) -> None:
        self._app.bus.publish(event_type, payload)

    def _notify(self, level: str, message: str) -> None:
        self._publish("notification", {"level": level, "message": message})

    # ── Lecture ─────────────────────────────────────────────────────────────

    def status(self) -> Dict[str, Any]:
        """Dossiers de la session courante, et indexations en cours."""
        indexer = self._indexer()
        session_id = self._session_id()
        with self._lock:
            running = [dict(item) for item in self._running.values()]
        if indexer is None:
            return {"available": False, "session": session_id, "folders": [],
                    "running": running}
        folders: List[Dict[str, Any]] = []
        if session_id:
            try:
                status = indexer.get_status(session_id)
            except Exception:  # pylint: disable=broad-except
                status = {"folders": []}
            for folder in status.get("folders", []):
                path = folder.get("path", "")
                folders.append({
                    "path": path,
                    "name": folder_name(path),
                    "file_count": folder.get("file_count", 0),
                    "chunks": folder.get("chunks", 0),
                    "indexed_at": folder.get("indexed_at", ""),
                })
        return {"available": True, "session": session_id, "folders": folders,
                "running": running}

    # ── Actions ─────────────────────────────────────────────────────────────

    def attach(self, folder: str) -> Dict[str, Any]:
        """Attache un dossier à la session courante (ou à une session à son nom) et l'indexe.

        Raises:
            FolderError: indexeur indisponible, dossier introuvable, pas de session
        """
        if self._indexer() is None:
            raise FolderError(tr("folders.indexerUnavailable"))
        if not folder or not os.path.isdir(folder):
            raise FolderError(tr("folders.notFound"))
        chat = self._app.chat
        session_id = chat.ensure_session(folder_name(folder)) if chat is not None else None
        if not session_id:
            raise FolderError(tr("folders.noSession"))
        return self._start(session_id, folder, reindex=False)

    def reindex(self, folder: str) -> Dict[str, Any]:
        """Réindexe un dossier de la session courante (tous ses fichiers)."""
        if self._indexer() is None:
            raise FolderError(tr("folders.indexerUnavailable"))
        session_id = self._session_id()
        if not session_id:
            raise FolderError(tr("folders.noSession"))
        return self._start(session_id, folder, reindex=True)

    def detach(self, folder: str) -> bool:
        """Détache un dossier : son index est supprimé (confirmé par la fenêtre)."""
        indexer = self._indexer()
        session_id = self._session_id()
        if indexer is None or not session_id:
            raise FolderError(tr("folders.noSession"))
        try:
            indexer.remove_folder(session_id, folder)
        except Exception as exc:  # pylint: disable=broad-except
            raise FolderError(tr("folders.error", error=exc)) from exc
        self._update_folders(session_id, remove=folder)
        self._notify("success", tr("folders.detached"))
        self._publish("folders.changed", {"path": folder, "ok": True})
        return True

    # ── Indexation en arrière-plan ──────────────────────────────────────────

    def _start(self, session_id: str, folder: str, reindex: bool) -> Dict[str, Any]:
        verb = tr("folders.verb.reindex" if reindex else "folders.verb.index")
        name = folder_name(folder)
        with self._lock:
            if folder in self._running:
                raise FolderError(tr("folders.alreadyRunning", verb=verb, name=name))
            job = {"path": folder, "name": name, "verb": verb, "done": 0, "total": 0}
            self._running[folder] = job
        self._notify("info", tr("folders.started", verb=verb, name=name))
        self._publish("folders.progress", dict(job))
        threading.Thread(target=self._run, args=(session_id, folder, reindex, job),
                         name="folder-index", daemon=True).start()
        return dict(job)

    def _run(self, session_id: str, folder: str, reindex: bool, job: Dict[str, Any]) -> None:
        name = job["name"]

        def progress(done, total, _rel):
            job["done"], job["total"] = done, total
            if done % _PROGRESS_EVERY == 0 or done == total:
                self._publish("folders.progress", dict(job))

        try:
            result = self._indexer().index_folder(session_id, folder, force=reindex,
                                                  progress_cb=progress)
        except Exception as exc:  # pylint: disable=broad-except
            logger.warning("Indexation de %s en échec : %s", folder, exc)
            result = {"status": "error", "error": tr("folders.failed", error=exc)}
        finally:
            with self._lock:
                self._running.pop(folder, None)

        if result.get("status") != "success":
            self._notify("error", f"❌ {result.get('error') or tr('folders.impossible')}")
            self._publish("folders.changed", {"path": folder, "ok": False})
            return
        self._update_folders(session_id, add=result.get("folder", folder))
        self._notify("success", tr("folders.indexed", name=name, files=result.get("total_files", 0),
                                   chunks=result.get("chunks", 0)))
        self._publish("folders.changed", {"path": folder, "ok": True})

    def _update_folders(self, session_id: str, add: Optional[str] = None,
                        remove: Optional[str] = None) -> None:
        """Liste des dossiers dans l'état de la session (attached_folders, comme Tk)."""
        chat = self._app.chat
        if chat is None:
            return

        def mutate(state):
            folders = list(state.get("attached_folders", []))
            if add and add not in folders:
                folders.append(add)
            if remove:
                resolved = str(Path(remove))
                folders = [f for f in folders if f != remove and str(Path(f)) != resolved]
            state["attached_folders"] = folders

        chat.update_session(session_id, mutate)
