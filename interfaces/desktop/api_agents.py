"""
Routes de la page Agents (agents.py)

  GET    /api/agents                     agents intégrés et personnalisés
  POST   /api/agents/custom              crée un agent personnalisé (prompt rédigé par le modèle)
  PUT    /api/agents/custom/{key}        le modifie (nouveau rôle : prompt réécrit)
  DELETE /api/agents/custom/{key}        le supprime
  GET    /api/agents/runs                fils d'exécution (résumés)
  GET    /api/agents/runs/{id}           un fil, sorties comprises
  POST   /api/agents/runs                exécute un agent seul ou un workflow
  POST   /api/agents/runs/{id}/stop      arrête le fil en cours
  DELETE /api/agents/runs/{id}           supprime un fil
  DELETE /api/agents/runs                efface l'historique (sauf le fil en cours)
  POST   /api/agents/attachments         fichiers choisis ou déposés pour la zone de tâche
  POST   /api/agents/attachments/upload  image collée, fichier sans chemin (navigateur)
  POST   /api/agents/workflow/save       enregistre le workflow (JSON de WorkflowCanvas.to_dict)
  POST   /api/agents/workflow/read       lit un workflow enregistré
  POST   /api/agents/workflow/export     exporte le workflow et ses réponses en Markdown (D11)

Rien n'appelle Ollama avant la fin du placement : ces routes répondent 503
tant que le moteur démarre.
"""

import uuid
from pathlib import Path
from typing import TYPE_CHECKING, Dict, List, Optional

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, ConfigDict, Field

from interfaces.desktop import files as local_files
from interfaces.desktop.agents import AgentsError, AgentsService, RunNotFound
from interfaces.desktop.routing import ENGINE_STARTING

if TYPE_CHECKING:  # pragma: no cover
    from interfaces.desktop.lifecycle import DesktopApp

# Image collée (Ctrl+V) : taille maximale acceptée, comme le chat
_MAX_UPLOAD = 50 * 1024 * 1024


class AgentBody(BaseModel):
    """POST /api/agents/custom, PUT /api/agents/custom/{key}."""

    name: str = Field(default="", max_length=200)
    role: str = Field(default="", max_length=5000)


class NodeBody(BaseModel):
    """Nœud du canvas (identifiants entiers, comme WorkflowCanvas de Tk)."""

    model_config = ConfigDict(extra="ignore")

    id: int
    agent_type: str = Field(max_length=200)
    name: str = Field(max_length=200)
    color: str = Field(default="#ff6b47", max_length=40)
    icon: str = Field(default="🤖", max_length=16)
    x: float = 0.0
    y: float = 0.0


class ConnectionBody(BaseModel):
    """Lien du canvas : port de sortie de `from` vers port d'entrée de `to`."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    from_: int = Field(alias="from")
    to: int


class AttachmentBody(BaseModel):
    """Pièce jointe de la zone de tâche."""

    model_config = ConfigDict(extra="ignore")

    path: str = Field(max_length=4096)
    type: Optional[str] = Field(default=None, max_length=20)


class RunBody(BaseModel):
    """POST /api/agents/runs."""

    task: str = Field(default="", max_length=500_000)
    nodes: List[NodeBody] = Field(default_factory=list, max_length=200)
    connections: List[ConnectionBody] = Field(default_factory=list, max_length=2000)
    attachments: List[AttachmentBody] = Field(default_factory=list, max_length=50)


class PathsBody(BaseModel):
    """POST /api/agents/attachments."""

    paths: List[str] = Field(default_factory=list, max_length=200)


class WorkflowNodeFile(BaseModel):
    """Nœud d'un fichier de workflow (WorkflowCanvas.to_dict), dans l'ordre de Tk."""

    model_config = ConfigDict(extra="ignore")

    agent_type: str = Field(max_length=200)
    name: str = Field(max_length=200)
    color: str = Field(default="#ff6b47", max_length=40)
    icon: str = Field(default="🤖", max_length=16)
    x: float = 0.0
    y: float = 0.0
    status: str = Field(default="idle", max_length=20)


class WorkflowFile(BaseModel):
    """Fichier de workflow : format JSON de WorkflowCanvas.to_dict (Tk)."""

    model_config = ConfigDict(extra="ignore")

    version: str = Field(default="8.1.0", max_length=20)
    nodes: Dict[str, WorkflowNodeFile] = Field(default_factory=dict, max_length=200)
    connections: List[ConnectionBody] = Field(default_factory=list, max_length=2000)
    zoom: float = 1.0
    pan_x: float = 0.0
    pan_y: float = 0.0


class WorkflowSaveBody(BaseModel):
    """POST /api/agents/workflow/save."""

    path: Optional[str] = Field(default=None, max_length=4096)  # None : outputs/workflows/
    workflow: WorkflowFile


class WorkflowReadBody(BaseModel):
    """POST /api/agents/workflow/read."""

    path: str = Field(max_length=4096)


class WorkflowExportBody(BaseModel):
    """POST /api/agents/workflow/export."""

    path: Optional[str] = Field(default=None, max_length=4096)  # None : outputs/exports/
    workflow: WorkflowFile
    run_id: Optional[str] = Field(default=None, max_length=100)


async def _run(func, *args):
    """Appel bloquant hors de la boucle ; refus → 409, fil introuvable → 404."""
    try:
        return await run_in_threadpool(func, *args)
    except RunNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except AgentsError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


def register(api: FastAPI, app: "DesktopApp") -> None:
    """Ajoute les routes de la page Agents à l'application."""
    # Routes enregistrées par leurs décorateurs
    # pylint: disable=unused-variable

    def agents() -> AgentsService:
        if getattr(app, "engine", None) is None:
            raise HTTPException(status_code=503, detail=ENGINE_STARTING)
        return app.agents

    # ── Agents ──────────────────────────────────────────────────────────────

    @api.get("/api/agents")
    async def list_agents():
        return await _run(agents().list)

    @api.post("/api/agents/custom")
    async def create_agent(body: AgentBody):
        return {"agent": await _run(agents().create, body.name, body.role)}

    @api.put("/api/agents/custom/{key}")
    async def edit_agent(key: str, body: AgentBody):
        return {"agent": await _run(agents().edit, key, body.name, body.role)}

    @api.delete("/api/agents/custom/{key}")
    async def delete_agent(key: str):
        await _run(agents().delete, key)
        return {"ok": True}

    # ── Fils d'exécution ────────────────────────────────────────────────────

    @api.get("/api/agents/runs")
    async def runs():
        return await _run(agents().runs)

    @api.get("/api/agents/runs/{run_id}")
    async def run(run_id: str):
        return await _run(agents().run, run_id)

    @api.post("/api/agents/runs")
    async def start_run(body: RunBody):
        nodes = [node.model_dump() for node in body.nodes]
        connections = [conn.model_dump(by_alias=True) for conn in body.connections]
        attachments = [item.model_dump() for item in body.attachments]
        run_id = await _run(agents().start, body.task, nodes, connections, attachments)
        return {"run_id": run_id}

    @api.post("/api/agents/runs/{run_id}/stop")
    async def stop_run(run_id: str):
        return {"stopped": await _run(agents().stop, run_id)}

    @api.delete("/api/agents/runs/{run_id}")
    async def delete_run(run_id: str):
        await _run(agents().delete_run, run_id)
        return {"ok": True}

    @api.delete("/api/agents/runs")
    async def clear_runs():
        return {"removed": await _run(agents().clear_runs)}

    # ── Pièces jointes de la zone de tâche ──────────────────────────────────

    @api.post("/api/agents/attachments")
    async def add_attachments(body: PathsBody):
        return await _run(agents().inspect, body.paths)

    @api.post("/api/agents/attachments/upload")
    async def upload_attachment(file: UploadFile = File(...)):
        """Image collée (Ctrl+V) ou fichier sans chemin : copié dans un dossier temporaire."""
        service = agents()
        data = await file.read(_MAX_UPLOAD + 1)
        if len(data) > _MAX_UPLOAD:
            raise HTTPException(status_code=413, detail="Fichier trop volumineux")
        name = Path(file.filename or "fichier").name or "fichier"
        # Un sous-dossier par envoi : le fichier garde son nom, sans collision
        folder = local_files.UPLOAD_DIR / uuid.uuid4().hex[:12]
        folder.mkdir(parents=True, exist_ok=True)
        target = folder / name
        target.write_bytes(data)
        return await _run(service.inspect, [str(target)])

    # ── Fichiers de workflow ────────────────────────────────────────────────

    @api.post("/api/agents/workflow/save")
    async def save_workflow(body: WorkflowSaveBody):
        workflow = body.workflow.model_dump(by_alias=True)
        path = await _run(agents().save_workflow, body.path, workflow)
        app.notify("success", "💾 Workflow sauvegardé")
        return {"path": path}

    @api.post("/api/agents/workflow/read")
    async def read_workflow(body: WorkflowReadBody):
        return {"workflow": await _run(agents().read_workflow, body.path)}

    @api.post("/api/agents/workflow/export")
    async def export_workflow(body: WorkflowExportBody):
        workflow = body.workflow.model_dump(by_alias=True)
        path = await _run(agents().export_workflow, body.path, workflow, body.run_id)
        app.notify("success", "📤 Workflow exporté")
        return {"path": path}
