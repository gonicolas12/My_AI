"""
Routes de la barre latérale (interfaces/gui/sidebar.py dans Tk)

  GET    /api/search?q=…          recherche dans toutes les conversations (15 résultats)
  POST   /api/search/reindex      réindexation complète
  GET    /api/folders             dossiers projet de la session courante
  POST   /api/folders             attacher un dossier (indexation en arrière-plan)
  POST   /api/folders/reindex     réindexer un dossier
  POST   /api/folders/detach      détacher un dossier (son index est supprimé)
  GET    /api/history             historique des requêtes (20, recherche, favoris)
  POST   /api/history/{id}/favorite   favori ou non
  DELETE /api/history/{id}        supprimer une entrée
  POST   /api/export              exporter la conversation (Markdown, HTML, PDF)
"""

import os
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel

from interfaces.desktop.folders import FolderError, FolderService
from interfaces.desktop.routing import chat_service, engine_of
from utils.logger import setup_logger

if TYPE_CHECKING:  # pragma: no cover
    from interfaces.desktop.lifecycle import DesktopApp

logger = setup_logger("DesktopSidebarApi")

# Résultats de la recherche globale et entrées de l'historique (Tk)
SEARCH_RESULTS = 15
HISTORY_ENTRIES = 20

EXPORT_FORMATS = ("markdown", "html", "pdf")


class FolderBody(BaseModel):
    """Dossier projet (attacher, réindexer, détacher)."""

    path: str


class ExportBody(BaseModel):
    """POST /api/export : format, et chemin choisi dans le dialogue du système."""

    format: str
    path: Optional[str] = None  # None : outputs/exports/, nom daté


def _search_view(result: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "workspace_id": result.get("workspace_id", ""),
        "workspace_name": result.get("workspace_name") or "(sans nom)",
        "message_index": result.get("message_index", 0),
        "role": result.get("role", ""),
        "timestamp": result.get("timestamp", ""),
        "excerpt": (result.get("excerpt") or "").strip(),
    }


def _history_view(entry: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": entry.get("id"),
        "query": entry.get("query", ""),
        "is_favorite": bool(entry.get("is_favorite", False)),
        "timestamp": entry.get("timestamp"),
    }


def register(api: FastAPI, app: "DesktopApp") -> None:
    """Ajoute les routes de la barre latérale à l'application."""
    # pylint: disable=unused-variable  (routes enregistrées par leurs décorateurs)
    folders = FolderService(app)

    def conversation_search():
        getter = getattr(engine_of(app), "get_conversation_search", None)
        if getter is None:
            return None
        try:
            search = getter()
        except Exception:  # pylint: disable=broad-except
            return None
        return search if search is not None and search.is_available() else None

    def command_history():
        history = getattr(engine_of(app), "command_history", None)
        if history is None:
            raise HTTPException(status_code=503, detail="Historique indisponible")
        return history

    # ── Recherche globale ───────────────────────────────────────────────────

    @api.get("/api/search")
    async def search(q: str = ""):
        query = q.strip()

        def run():
            engine = conversation_search()
            if engine is None:
                return {"available": False, "results": []}
            if not query:
                return {"available": True, "results": []}
            try:
                results = engine.search(query, n_results=SEARCH_RESULTS)
            except Exception as exc:  # pylint: disable=broad-except
                logger.warning("Recherche globale en échec : %s", exc)
                results = []
            return {"available": True, "results": [_search_view(r) for r in results]}

        return await run_in_threadpool(run)

    @api.post("/api/search/reindex")
    async def search_reindex():
        def run():
            engine = conversation_search()
            if engine is None:
                return {"available": False, "messages": 0}
            stats = engine.reindex(force=True)
            return {"available": True, "messages": stats.get("messages", 0)}

        try:
            return await run_in_threadpool(run)
        except Exception as exc:  # pylint: disable=broad-except
            raise HTTPException(status_code=409, detail=f"Erreur : {exc}") from exc

    # ── Dossiers projet ─────────────────────────────────────────────────────

    async def folder_call(func, *args):
        try:
            return await run_in_threadpool(func, *args)
        except FolderError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    @api.get("/api/folders")
    async def folders_status():
        chat_service(app)
        return await run_in_threadpool(folders.status)

    @api.post("/api/folders")
    async def folders_attach(body: FolderBody):
        chat_service(app)
        return await folder_call(folders.attach, body.path)

    @api.post("/api/folders/reindex")
    async def folders_reindex(body: FolderBody):
        chat_service(app)
        return await folder_call(folders.reindex, body.path)

    @api.post("/api/folders/detach")
    async def folders_detach(body: FolderBody):
        chat_service(app)
        return {"detached": await folder_call(folders.detach, body.path)}

    # ── Historique des requêtes ─────────────────────────────────────────────

    @api.get("/api/history")
    async def history(q: str = "", favorites: bool = False):
        store = command_history()

        def run() -> List[Dict[str, Any]]:
            if favorites:
                entries = store.get_favorites()
            elif q.strip():
                entries = store.search(q.strip(), limit=HISTORY_ENTRIES)
            else:
                entries = store.get_recent(limit=HISTORY_ENTRIES)
            return [_history_view(entry) for entry in entries]

        return {"entries": await run_in_threadpool(run)}

    @api.post("/api/history/{entry_id}/favorite")
    async def history_favorite(entry_id: int):
        store = command_history()
        return {"is_favorite": bool(await run_in_threadpool(store.toggle_favorite, entry_id))}

    @api.delete("/api/history/{entry_id}")
    async def history_delete(entry_id: int):
        store = command_history()
        return {"deleted": bool(await run_in_threadpool(store.delete, entry_id))}

    # ── Export ──────────────────────────────────────────────────────────────

    @api.post("/api/export")
    async def export(body: ExportBody):
        if body.format not in EXPORT_FORMATS:
            raise HTTPException(status_code=422, detail=f"Format inconnu : {body.format}")
        messages = chat_service(app).export_messages()
        if not messages:
            raise HTTPException(status_code=409, detail="⚠️ Aucune conversation à exporter")

        def run() -> str:
            # pylint: disable=import-outside-toplevel
            from core.conversation_exporter import ConversationExporter

            if body.path:
                target = Path(body.path)
                exporter = ConversationExporter(output_dir=str(target.parent))
                return exporter.export(messages=messages, output_format=body.format,
                                       filename=target.stem)
            exporter = ConversationExporter()
            return exporter.export(messages=messages, output_format=body.format)

        try:
            path = await run_in_threadpool(run)
        except Exception as exc:  # pylint: disable=broad-except
            logger.warning("Export en échec : %s", exc)
            raise HTTPException(status_code=409, detail=f"❌ Erreur export : {exc}") from exc
        return {"path": os.path.abspath(str(path))}
