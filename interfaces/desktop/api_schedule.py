"""
Routes des tâches planifiées de la page Agents (schedule.py)

  GET    /api/schedule                      tâches, planning et source en clair,
                                            exécution appli fermée
  POST   /api/schedule/tasks                crée une tâche
  PUT    /api/schedule/tasks/{id}           la modifie (source figée, comme Tk)
  DELETE /api/schedule/tasks/{id}           la supprime
  POST   /api/schedule/tasks/{id}/enabled   l'active ou la désactive
  POST   /api/schedule/tasks/{id}/run       l'exécute tout de suite
  POST   /api/schedule/background           « Exécuter même l'appli fermée »

Comme les routes des agents, elles répondent 503 tant que le moteur démarre.
"""

from typing import TYPE_CHECKING, List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, ConfigDict, Field

from interfaces.desktop.routing import ENGINE_STARTING
from interfaces.desktop.schedule import ScheduleError, ScheduleNotFound, ScheduleService

if TYPE_CHECKING:  # pragma: no cover
    from interfaces.desktop.lifecycle import DesktopApp


class ScheduleBody(BaseModel):
    """Planning saisi : quotidien, hebdomadaire, intervalle ou cron (_build_schedule de Tk)."""

    model_config = ConfigDict(extra="ignore")

    type: str = Field(default="daily", max_length=20)
    at: str = Field(default="08:00", max_length=10)
    days: List[int] = Field(default_factory=list, max_length=7)
    every: str = Field(default="", max_length=10)
    unit: str = Field(default="minutes", max_length=10)
    expr: str = Field(default="", max_length=200)


class SourceNode(BaseModel):
    """Nœud du canvas courant, figé dans la tâche."""

    model_config = ConfigDict(extra="ignore")

    id: str = Field(max_length=80)
    agent_type: str = Field(max_length=200)
    name: str = Field(default="", max_length=200)
    color: str = Field(default="#3b82f6", max_length=40)
    icon: str = Field(default="🤖", max_length=16)


class SourceConnection(BaseModel):
    """Lien du canvas courant."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    from_: str = Field(alias="from", max_length=80)
    to: str = Field(max_length=80)


class SourceBody(BaseModel):
    """Source d'une tâche : agent seul, workflow du canvas ou débat (création seulement)."""

    model_config = ConfigDict(extra="ignore")

    kind: str = Field(default="single", max_length=20)
    agent: Optional[str] = Field(default=None, max_length=200)
    agent_a: Optional[str] = Field(default=None, max_length=200)
    agent_b: Optional[str] = Field(default=None, max_length=200)
    rounds: int = Field(default=3, ge=1, le=10)
    nodes: List[SourceNode] = Field(default_factory=list, max_length=200)
    connections: List[SourceConnection] = Field(default_factory=list, max_length=2000)


class TaskBody(BaseModel):
    """POST /api/schedule/tasks, PUT /api/schedule/tasks/{id}."""

    name: str = Field(default="", max_length=200)
    task: str = Field(default="", max_length=100_000)
    schedule: ScheduleBody = Field(default_factory=ScheduleBody)
    run_if_missed: bool = True
    source: Optional[SourceBody] = None  # ignorée à la modification


class EnabledBody(BaseModel):
    """POST /api/schedule/tasks/{id}/enabled, POST /api/schedule/background."""

    enabled: bool


def _fields(body: TaskBody) -> dict:
    """Champs du dialogue, liens du canvas avec leur clé « from »."""
    return body.model_dump(by_alias=True)


async def _run(func, *args):
    """Appel bloquant hors de la boucle ; tâche introuvable → 404, refus → 409."""
    try:
        return await run_in_threadpool(func, *args)
    except ScheduleNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ScheduleError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


def register(api: FastAPI, app: "DesktopApp") -> None:
    """Ajoute les routes des tâches planifiées à l'application."""
    # Routes enregistrées par leurs décorateurs
    # pylint: disable=unused-variable

    def schedule() -> ScheduleService:
        if getattr(app, "engine", None) is None:
            raise HTTPException(status_code=503, detail=ENGINE_STARTING)
        return app.schedule

    @api.get("/api/schedule")
    async def list_tasks():
        return await _run(schedule().list)

    @api.post("/api/schedule/tasks")
    async def create_task(body: TaskBody):
        return {"task": await _run(schedule().create, _fields(body))}

    @api.put("/api/schedule/tasks/{task_id}")
    async def update_task(task_id: str, body: TaskBody):
        return {"task": await _run(schedule().update, task_id, _fields(body))}

    @api.delete("/api/schedule/tasks/{task_id}")
    async def delete_task(task_id: str):
        await _run(schedule().delete, task_id)
        return {"ok": True}

    @api.post("/api/schedule/tasks/{task_id}/enabled")
    async def set_enabled(task_id: str, body: EnabledBody):
        return {"task": await _run(schedule().set_enabled, task_id, body.enabled)}

    @api.post("/api/schedule/tasks/{task_id}/run")
    async def run_now(task_id: str):
        await _run(schedule().run_now, task_id)
        return {"ok": True}

    @api.post("/api/schedule/background")
    async def set_background(body: EnabledBody):
        return await _run(schedule().set_background, body.enabled)
