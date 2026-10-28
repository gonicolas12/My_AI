"""
Routes de la page Code (code.py) : la conversation de l'extension VS Code

  GET  /api/code                     état, messages et seq du dernier événement qu'ils contiennent
  GET  /api/code/state               état seul : VS Code connecté (et son dossier), réponse en cours
  POST /api/code/send                message à l'extension VS Code, qui agit dans son workspace,
                                     avec ses pièces jointes
  POST /api/code/attachments         fichiers choisis ou déposés, vérifiés (un dossier joint
                                     ses fichiers)
  POST /api/code/attachments/upload  fichier sans chemin (image collée, navigateur)
  POST /api/code/stop                arrête la réponse en cours, d'où que vienne son message
  POST /api/code/clear               nouvelle conversation (VS Code, PC et téléphone)
  POST /api/code/approve             répond à une demande d'approbation (écriture, commande)

Un message refusé (VS Code absent, réponse en cours, message vide) répond 409
avec la raison, dans la langue de l'interface.
"""

import uuid
from pathlib import Path
from typing import TYPE_CHECKING, List

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, Field

from core.i18n import tr
from interfaces.desktop import files as local_files
from relay.code_hub import APPROVAL_DECISIONS, CodeError

if TYPE_CHECKING:  # pragma: no cover
    from interfaces.desktop.lifecycle import DesktopApp

# Taille maximale d'un fichier envoyé par la page (image collée)
_MAX_UPLOAD = 50 * 1024 * 1024


class FileRef(BaseModel):
    """Pièce jointe d'un message : chemin vérifié par /api/code/attachments."""

    path: str = Field(max_length=4096)
    name: str = Field(max_length=500)


class SendBody(BaseModel):
    """POST /api/code/send."""

    text: str = Field(default="", max_length=100_000)
    files: List[FileRef] = Field(default_factory=list, max_length=200)


class PathsBody(BaseModel):
    """POST /api/code/attachments."""

    paths: List[str] = Field(default_factory=list, max_length=200)


class ApproveBody(BaseModel):
    """POST /api/code/approve."""

    call_id: str = Field(max_length=200)
    decision: str = Field(max_length=40)


def register(api: FastAPI, app: "DesktopApp") -> None:
    """Ajoute les routes de la page Code à l'application."""
    # Routes enregistrées par leurs décorateurs
    # pylint: disable=unused-variable

    @api.get("/api/code")
    async def conversation():
        return app.code.snapshot()

    @api.get("/api/code/state")
    async def state():
        return app.code.state()

    @api.post("/api/code/send")
    async def send(body: SendBody):
        files = [(item.path, item.name) for item in body.files]
        try:
            message_id = await run_in_threadpool(app.code.send, body.text, files)
        except CodeError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        return {"message_id": message_id}

    @api.post("/api/code/attachments")
    async def add_attachments(body: PathsBody):
        return await run_in_threadpool(app.code.inspect, body.paths)

    @api.post("/api/code/attachments/upload")
    async def upload_attachment(file: UploadFile = File(...)):
        """Image collée (Ctrl+V) ou fichier sans chemin : copié dans un dossier temporaire."""
        data = await file.read(_MAX_UPLOAD + 1)
        if len(data) > _MAX_UPLOAD:
            raise HTTPException(status_code=413, detail=tr("files.tooBig"))
        name = Path(file.filename or "fichier").name or "fichier"
        # Un sous-dossier par envoi : le fichier garde son nom, sans collision
        folder = local_files.UPLOAD_DIR / uuid.uuid4().hex[:12]
        folder.mkdir(parents=True, exist_ok=True)
        target = folder / name
        target.write_bytes(data)
        return await run_in_threadpool(app.code.inspect, [str(target)])

    @api.post("/api/code/stop")
    async def stop():
        return {"stopped": await run_in_threadpool(app.code.stop)}

    @api.post("/api/code/clear")
    async def clear():
        await run_in_threadpool(app.code.clear)
        return {"ok": True}

    @api.post("/api/code/approve")
    async def approve(body: ApproveBody):
        if body.decision not in APPROVAL_DECISIONS:
            raise HTTPException(status_code=422, detail=f"Décision inconnue : {body.decision}")
        return {"ok": await run_in_threadpool(app.code.approve, body.call_id, body.decision)}
