"""
Routes des fichiers locaux et des aperçus (volet de droite)

  POST /api/files/links          liens signés des fichiers que la fenêtre affiche
  GET  /files/<sig>/<chemin>/…   le fichier (image, PDF…), par son lien signé
  POST /api/files/open           document produit par l'appli → son application
  POST /api/files/reveal         chemin existant → Explorateur, jamais exécuté
  POST /api/files/download       document produit → copie dans Téléchargements
  POST /api/files/text           début d'un fichier texte (code, Markdown…), pour son aperçu
  POST /api/files/info           taille et date d'un fichier (en-tête de l'aperçu)
  POST /api/previews/artifact    bloc HTML/SVG d'une réponse → page d'aperçu
  POST /api/previews/document    document → page d'aperçu HTML, ou le PDF lui-même
  POST /api/previews/<id>/browser  aperçu → navigateur du système
  GET  /preview/<id>             la page d'aperçu, avec sa propre politique

Règles, reprises de utils/path_links.py et de l'interface Tk : voir files.py.
"""

import mimetypes
import os
from typing import TYPE_CHECKING, List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel, Field

from core.i18n import tr
from interfaces.desktop import files as local_files
from utils.logger import setup_logger

if TYPE_CHECKING:  # pragma: no cover
    from interfaces.desktop.lifecycle import DesktopApp
    from interfaces.desktop.server import DesktopServer

logger = setup_logger("DesktopFilesApi")


class PathsBody(BaseModel):
    """POST /api/files/links : fichiers à afficher ; base : fichier Markdown affiché,
    dont les images rangées dans son dossier s'affichent aussi (logo d'un README)."""

    paths: List[str] = Field(default_factory=list, max_length=500)
    base: Optional[str] = Field(default=None, max_length=4096)


# Images qu'un fichier Markdown affiché peut montrer, si elles sont dans son dossier
_MARKDOWN = (".md", ".markdown", ".mdx")
_IMAGES = (".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".svg", ".ico", ".avif")


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

# Refus : clés du catalogue (core/locales), traduites à l'envoi
_NOT_FOUND = "files.notFound"
_NOT_GENERATED = "files.notGenerated"


def register(api: FastAPI, app: "DesktopApp", server: "DesktopServer") -> None:
    """Ajoute les routes des fichiers et des aperçus à l'application."""
    # Routes enregistrées par leurs décorateurs
    # pylint: disable=unused-variable

    def roots() -> List[str]:
        return local_files.generated_roots(getattr(app, "config", None))

    def memory_originals() -> List[str]:
        """Copies des documents de la Mémoire (aperçu de l'onglet Documents)."""
        memory = getattr(app, "memory", None)
        root = getattr(memory, "originals_root", None)
        try:
            folder = root() if callable(root) else None
        except Exception:  # pylint: disable=broad-except
            folder = None
        return [folder] if folder else []

    def showable(path: str) -> bool:
        """Fichier que la fenêtre peut afficher : connu de la conversation, de
        la zone de tâche des agents ou de la page Code, produit par l'appli,
        envoyé par la page (image collée), copie d'un document de la Mémoire,
        ou fichier qu'une réponse cite par son chemin."""
        if not path or not os.path.isfile(path):
            return False
        normalized = local_files.normalize(path)
        chat = app.chat
        if chat is not None and normalized in chat.known_paths():
            return True
        # Pièces jointes de la zone de tâche des agents et de la page Code (vignettes)
        for name in ("agent_attachments", "code_attachments"):
            known = getattr(app, name, None)
            if known is not None and normalized in known():
                return True
        allowed = roots() + [str(local_files.UPLOAD_DIR)] + memory_originals()
        if any(local_files.is_inside(path, root) for root in allowed):
            return True
        cites = getattr(chat, "cites_path", None)
        return bool(callable(cites) and cites(path))

    def generated(path: str) -> str:
        if not local_files.is_generated(path, roots()):
            raise HTTPException(status_code=403, detail=tr(_NOT_GENERATED))
        return path

    # ── Fichiers ────────────────────────────────────────────────────────────

    @api.post("/api/files/links")
    async def file_links(body: PathsBody):
        def build():
            # Fichier Markdown affiché : seulement les images de son dossier (et dessous)
            folder = None
            if (body.base and body.base.lower().endswith(_MARKDOWN)
                    and showable(body.base)):
                folder = os.path.dirname(os.path.abspath(body.base))

            def allowed(path: str) -> bool:
                if showable(path):
                    return True
                return bool(folder and path.lower().endswith(_IMAGES)
                            and os.path.isfile(path) and local_files.is_inside(path, folder))

            return {path: (server.links.url(path) if allowed(path) else None)
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
            raise HTTPException(status_code=409, detail=tr("files.openFailed", error=exc)) from exc
        return {"ok": True}

    @api.post("/api/files/reveal")
    async def reveal_file(body: PathBody):
        try:
            await run_in_threadpool(local_files.reveal, body.path)
        except local_files.FileAccessError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except OSError as exc:
            raise HTTPException(status_code=409, detail=tr("files.openFailed", error=exc)) from exc
        return {"ok": True}

    @api.post("/api/files/download")
    async def download_file(body: PathBody):
        path = generated(body.path)
        try:
            target = await run_in_threadpool(local_files.copy_to_downloads, path)
        except OSError as exc:
            raise HTTPException(status_code=409,
                                detail=tr("files.downloadFailed", error=exc)) from exc
        return {"path": target}

    @api.post("/api/files/text")
    async def file_text(body: PathBody):
        """Début d'un fichier que la fenêtre peut afficher, s'il est du texte."""
        if not await run_in_threadpool(showable, body.path):
            raise HTTPException(status_code=404, detail=tr(_NOT_FOUND))
        try:
            text, truncated = await run_in_threadpool(local_files.read_text_preview, body.path)
        except local_files.NotTextError as exc:
            raise HTTPException(status_code=415, detail=str(exc)) from exc
        except OSError as exc:
            raise HTTPException(status_code=409, detail=tr("files.readFailed", error=exc)) from exc
        return {"text": text, "truncated": truncated}

    @api.post("/api/files/info")
    async def file_info(body: PathBody):
        """Taille et date de modification d'un fichier que la fenêtre peut afficher."""
        if not await run_in_threadpool(showable, body.path):
            raise HTTPException(status_code=404, detail=tr(_NOT_FOUND))
        try:
            return await run_in_threadpool(local_files.file_info, body.path)
        except OSError as exc:
            raise HTTPException(status_code=404, detail=tr(_NOT_FOUND)) from exc

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
        # Hors de la boucle : un fichier cité se cherche dans les réponses (disque sondé)
        if not await run_in_threadpool(showable, body.path):
            raise HTTPException(status_code=404, detail=tr(_NOT_FOUND))
        try:
            preview = await run_in_threadpool(server.previews.add_document, body.path,
                                              body.native)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        except Exception as exc:  # pylint: disable=broad-except
            logger.warning("Aperçu de %s impossible : %s", body.path, exc)
            raise HTTPException(status_code=409, detail=tr("files.previewFailed", error=exc)) from exc
        return preview_view(preview)

    @api.post("/api/previews/{preview_id}/browser")
    async def preview_in_browser(preview_id: str):
        try:
            target = await run_in_threadpool(server.previews.open_in_browser, preview_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=tr("files.previewNotFound")) from exc
        except OSError as exc:
            raise HTTPException(status_code=409,
                                detail=tr("files.browserFailed", error=exc)) from exc
        return {"path": target}

    @api.get("/preview/{preview_id}")
    async def preview_page(preview_id: str):
        preview = server.previews.get(preview_id)
        if preview is None or preview.html is None:
            raise HTTPException(status_code=404)
        return HTMLResponse(preview.html, headers={"Content-Security-Policy": preview.csp,
                                                   "Cache-Control": "no-store"})
