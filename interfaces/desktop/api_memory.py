"""
Routes de la Mémoire (memory.py)

  GET    /api/memory?tab=&q=&category=&page=   une page : éléments, total, compteurs,
                                              documents ajoutés en cours de lecture
                                              (Documents : un élément par document ou dossier)
  POST   /api/memory/facts                    ajoute un fait (catégorie, contenu)
  POST   /api/memory/documents/existing       fichiers (noms) et dossiers déjà là, avec
                                              leur date : la fenêtre demande s'il faut les
                                              mettre à jour ou garder les deux
  POST   /api/memory/documents                ajoute des fichiers, par leur chemin
                                              (dialogue du système) ; targets : ceux qu'ils
                                              mettent à jour
  POST   /api/memory/documents/upload         ajoute un fichier sans chemin (dépôt,
                                              navigateur) ; replace : celui qu'il met à jour
  POST   /api/memory/documents/folder         ajoute un dossier déposé : ses fichiers et
                                              leur chemin dedans, rangés sous son nom ;
                                              target : le dossier qu'il met à jour
  DELETE /api/memory/documents?document=      supprime un document (tous ses morceaux)
  DELETE /api/memory/folders?folder=          supprime un dossier déposé et ses documents
  PUT    /api/memory/{tab}/{entry_id}         nouveau contenu
  DELETE /api/memory/{tab}/{entry_id}?at_source=   supprime (conversation : aussi à la source)
"""

import shutil
import uuid
from pathlib import Path
from typing import TYPE_CHECKING, Dict, List, Optional

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, Field

from core.i18n import tr
from interfaces.desktop import files as local_files
from interfaces.desktop.memory import FOLDER_FILES_MAX, MemoryPanelError, clean_folder_name

if TYPE_CHECKING:  # pragma: no cover
    from interfaces.desktop.lifecycle import DesktopApp

# Fichier envoyé sans chemin (navigateur) : même limite que les pièces jointes
_MAX_UPLOAD = 50 * 1024 * 1024


async def _save_upload(file: UploadFile) -> Path:
    """Copie d'un fichier envoyé, dans son propre dossier (il garde son nom, sans collision).

    Raises:
        HTTPException: 413 au-delà de _MAX_UPLOAD
    """
    data = await file.read(_MAX_UPLOAD + 1)
    if len(data) > _MAX_UPLOAD:
        raise HTTPException(status_code=413, detail="Fichier trop volumineux")
    name = Path(file.filename or "fichier").name or "fichier"
    folder = local_files.UPLOAD_DIR / uuid.uuid4().hex[:12]
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / name
    target.write_bytes(data)
    return target


class FactBody(BaseModel):
    """POST /api/memory/facts."""

    category: str = "general"
    text: str = Field(max_length=100_000)


class DocumentsBody(BaseModel):
    """POST /api/memory/documents ; targets : nom → document qu'il met à jour."""

    paths: List[str] = Field(max_length=200)
    targets: Dict[str, str] = Field(default_factory=dict, max_length=200)


class ExistingBody(BaseModel):
    """POST /api/memory/documents/existing."""

    names: List[str] = Field(default_factory=list, max_length=500)
    folders: List[str] = Field(default_factory=list, max_length=100)


class ContentBody(BaseModel):
    """PUT /api/memory/{tab}/{entry_id}."""

    text: str = Field(max_length=1_000_000)


async def _run(func, *args):
    """Appel bloquant hors de la boucle (ChromaDB, SQLite) ; refus → 409 avec son message."""
    try:
        return await run_in_threadpool(func, *args)
    except MemoryPanelError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


def register(api: FastAPI, app: "DesktopApp") -> None:
    """Ajoute les routes de la Mémoire à l'application."""
    # Routes enregistrées par leurs décorateurs
    # pylint: disable=unused-variable

    @api.get("/api/memory")
    async def memory_page(tab: str = "facts", q: str = "", category: Optional[str] = None,
                          page: int = 0):
        return await _run(app.memory.page, tab, q, category, page)

    @api.post("/api/memory/documents/existing")
    async def existing_documents(body: ExistingBody):
        """Fichiers et dossiers déjà dans l'onglet Documents, avant de les envoyer."""
        return await _run(app.memory.existing, body.names, body.folders)

    @api.delete("/api/memory/documents")
    async def delete_document(document: str):
        await _run(app.memory.delete_document, document)
        app.notify("success", tr("memory.deleted"))
        return {"ok": True}

    @api.delete("/api/memory/folders")
    async def delete_folder(folder: str):
        """Un dossier déposé, par sa clé (un autre dossier du même nom reste)."""
        await _run(app.memory.delete_folder, folder)
        app.notify("success", tr("memory.deleted"))
        return {"ok": True}

    @api.post("/api/memory/facts")
    async def add_fact(body: FactBody):
        fact_id = await _run(app.memory.add_fact, body.category, body.text)
        app.notify("success", tr("memory.factAdded"))
        return {"id": fact_id}

    @api.post("/api/memory/documents")
    async def add_documents(body: DocumentsBody):
        """Fichiers à mettre en mémoire, lus en arrière-plan (événements memory.jobs)."""
        return await _run(app.memory.add_documents, body.paths, False, body.targets)

    @api.post("/api/memory/documents/upload")
    async def upload_document(file: UploadFile = File(...),
                              replace: Optional[str] = Form(None, max_length=200)):
        """Fichier sans chemin (navigateur, dépôt) : copié à part, effacé une fois lu ;
        replace : document qu'il met à jour (« Mettre à jour »)."""
        target = await _save_upload(file)
        result = None
        try:
            result = await _run(app.memory.add_documents, [str(target)], True,
                                {target.name: replace} if replace else None)
            return result
        finally:
            if not (result or {}).get("jobs"):
                # Refusé, ou mémoire indisponible : rien ne lira la copie
                shutil.rmtree(target.parent, ignore_errors=True)

    @api.post("/api/memory/documents/folder")
    async def upload_folder(folder: str = Form(..., max_length=500),
                            paths: List[str] = Form(...),
                            files: List[UploadFile] = File(...),
                            target: Optional[str] = Form(None, max_length=200)):
        """Dossier déposé : ses fichiers (contenu) et leur chemin dedans, dans le même
        ordre ; target : dossier déjà en mémoire qu'il met à jour (« Mettre à jour »)."""
        if len(files) != len(paths):
            raise HTTPException(status_code=422, detail="paths et files ne correspondent pas")
        if len(files) > FOLDER_FILES_MAX:
            raise HTTPException(status_code=413, detail=tr(
                "memory.documents.folderTooBig", name=clean_folder_name(folder),
                max=FOLDER_FILES_MAX))
        saved: List[Path] = []
        result = None
        try:
            for upload in files:
                saved.append(await _save_upload(upload))
            result = await _run(app.memory.add_folder, folder,
                                [(str(copy), relative) for copy, relative in zip(saved, paths)],
                                True, target)
            return result
        finally:
            if not (result or {}).get("jobs"):
                # Refusé, ou mémoire indisponible : rien ne lira les copies
                for target in saved:
                    shutil.rmtree(target.parent, ignore_errors=True)

    @api.put("/api/memory/{tab}/{entry_id}")
    async def update_entry(tab: str, entry_id: str, body: ContentBody):
        await _run(app.memory.update, tab, entry_id, body.text)
        app.notify("success", tr("memory.edited"))
        return {"ok": True}

    @api.delete("/api/memory/{tab}/{entry_id}")
    async def delete_entry(tab: str, entry_id: str, at_source: bool = True):
        await _run(app.memory.delete, tab, entry_id, at_source)
        app.notify("success", tr("memory.deleted"))
        return {"ok": True}
