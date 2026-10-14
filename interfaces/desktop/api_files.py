"""
Routes des fichiers locaux et des aperçus (volet de droite)

  POST /api/files/links          liens signés des fichiers que la fenêtre affiche
  GET  /files/<sig>/<chemin>/…   le fichier (image, PDF…), par son lien signé
  POST /api/files/open           document produit par l'appli → son application
  POST /api/files/reveal         chemin existant → Explorateur, jamais exécuté
  POST /api/files/download       document produit → copie dans Téléchargements
  POST /api/previews/artifact    bloc HTML/SVG d'une réponse → page d'aperçu
  POST /api/previews/document    document → page d'aperçu HTML, ou le PDF lui-même
  POST /api/previews/<id>/browser  aperçu → navigateur du système
  GET  /preview/<id>             la page d'aperçu, avec sa propre politique

Règles, reprises de utils/path_links.py et de l'interface Tk : voir files.py.
"""

import mimetypes
import os
from typing import TYPE_CHECKING, List

from fastapi import FastAPI, HTTPException
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel, Field

from interfaces.desktop import files as local_files
from utils.logger import setup_logger

if TYPE_CHECKING:  # pragma: no cover
    from interfaces.desktop.lifecycle import DesktopApp
    from interfaces.desktop.server import DesktopServer

logger = setup_logger("DesktopFilesApi")


class PathsBody(BaseModel):
    """POST /api/files/links : fichiers à afficher."""

    paths: List[str] = Field(default_factory=list, max_length=500)


class PathBody(BaseModel):
    """Un fichier ou un dossier (ouvrir, montrer, copier, aperçu)."""

    path: str


class DocumentBody(PathBody):
    """POST /api/previews/document."""

    native: bool = False  # la fenêtre affiche les visionneuses de Windows


class ArtifactBody(BaseModel):
    """POST /api/previews/artifact : bloc HTML ou SVG d'une réponse."""

    code: str = Field(max_length=5_000_000)
    kind: str
    title: str = ""
    language: str = ""
    index: int = 0

# Fichier servi autrement qu'en PDF (lecteur de WebView2, qui ne marche pas en
# bac à sable) : s'il s'affichait comme une page (HTML, SVG…), il resterait
# isolé de l'appli, sans script
_FILE_CSP = ("sandbox; default-src 'none'; img-src 'self' data:; "
             "media-src 'self'; style-src 'unsafe-inline'")

_NOT_FOUND = "Fichier introuvable."
_NOT_GENERATED = "Seuls les documents produits par My_AI s'ouvrent ici."


def register(api: FastAPI, app: "DesktopApp", server: "DesktopServer") -> None:
    """Ajoute les routes des fichiers et des aperçus à l'application."""
    # Routes enregistrées par leurs décorateurs
    # pylint: disable=unused-variable

    def roots() -> List[str]:
        return local_files.generated_roots(getattr(app, "config", None))

    def showable(path: str) -> bool:
        """Fichier que la fenêtre peut afficher : connu de la conversation ou de
        la zone de tâche des agents, ou produit par l'appli, ou envoyé par la
        page (image collée)."""
        if not path or not os.path.isfile(path):
            return False
        normalized = local_files.normalize(path)
        chat = app.chat
        if chat is not None and normalized in chat.known_paths():
            return True
        # Pièces jointes de la zone de tâche des agents (vignettes)
        agent_attachments = getattr(app, "agent_attachments", None)
        if agent_attachments is not None and normalized in agent_attachments():
            return True
        allowed = roots() + [str(local_files.UPLOAD_DIR)]
        return any(local_files.is_inside(path, root) for root in allowed)

    def generated(path: str) -> str:
        if not local_files.is_generated(path, roots()):
            raise HTTPException(status_code=403, detail=_NOT_GENERATED)
        return path

    # ── Fichiers ────────────────────────────────────────────────────────────

    @api.post("/api/files/links")
    async def file_links(body: PathsBody):
        def build():
            return {path: (server.links.url(path) if showable(path) else None)
                    for path in dict.fromkeys(body.paths)}
        return {"links": await run_in_threadpool(build)}

    @api.get("/files/{signature}/{token}/{name}")
    async def serve_file(signature: str, token: str, name: str):
        del name  # nom lisible, pour le titre du lecteur PDF et les téléchargements
        path = server.links.resolve(signature, token)
        if path is None or not os.path.isfile(path):
            raise HTTPException(status_code=404)
        media_type = mimetypes.guess_type(path)[0] or "application/octet-stream"
        headers = {} if media_type == "application/pdf" else {"Content-Security-Policy": _FILE_CSP}
        return FileResponse(path, media_type=media_type, headers=headers,
                            filename=os.path.basename(path), content_disposition_type="inline")

    @api.post("/api/files/open")
    async def open_file(body: PathBody):
        path = generated(body.path)
        try:
            await run_in_threadpool(local_files.open_with_default_app, path)
        except OSError as exc:
            raise HTTPException(status_code=409, detail=f"Ouverture impossible : {exc}") from exc
        return {"ok": True}

    @api.post("/api/files/reveal")
    async def reveal_file(body: PathBody):
        try:
            await run_in_threadpool(local_files.reveal, body.path)
        except local_files.FileAccessError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except OSError as exc:
            raise HTTPException(status_code=409, detail=f"Ouverture impossible : {exc}") from exc
        return {"ok": True}

    @api.post("/api/files/download")
    async def download_file(body: PathBody):
        path = generated(body.path)
        try:
            target = await run_in_threadpool(local_files.copy_to_downloads, path)
        except OSError as exc:
            raise HTTPException(status_code=409,
                                detail=f"❌ Erreur de téléchargement : {exc}") from exc
        return {"path": target}

    # ── Aperçus ─────────────────────────────────────────────────────────────

    def preview_view(preview):
        if preview.kind == "pdf":
            url = server.links.url(preview.source_path)
        elif preview.kind == "native":
            url = ""  # visionneuse de la fenêtre (shell_api.native_preview_show)
        else:
            url = f"/preview/{preview.id}"
        return {"id": preview.id, "kind": preview.kind, "title": preview.title,
                "url": url, "path": preview.source_path}

    @api.post("/api/previews/artifact")
    async def artifact_preview(body: ArtifactBody):
        try:
            preview = server.previews.add_artifact(body.code, body.kind, body.title,
                                                   body.language, body.index)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        return preview_view(preview)

    @api.post("/api/previews/document")
    async def document_preview(body: DocumentBody):
        if not showable(body.path):
            raise HTTPException(status_code=404, detail=_NOT_FOUND)
        try:
            preview = await run_in_threadpool(server.previews.add_document, body.path,
                                              body.native)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        except Exception as exc:  # pylint: disable=broad-except
            logger.warning("Aperçu de %s impossible : %s", body.path, exc)
            raise HTTPException(status_code=409, detail=f"Aperçu impossible : {exc}") from exc
        return preview_view(preview)

    @api.post("/api/previews/{preview_id}/browser")
    async def preview_in_browser(preview_id: str):
        try:
            target = await run_in_threadpool(server.previews.open_in_browser, preview_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Aperçu introuvable.") from exc
        except OSError as exc:
            raise HTTPException(status_code=409,
                                detail=f"Impossible d'ouvrir le navigateur : {exc}") from exc
        return {"path": target}

    @api.get("/preview/{preview_id}")
    async def preview_page(preview_id: str):
        preview = server.previews.get(preview_id)
        if preview is None or preview.html is None:
            raise HTTPException(status_code=404)
        return HTMLResponse(preview.html, headers={"Content-Security-Policy": preview.csp,
                                                   "Cache-Control": "no-store"})
