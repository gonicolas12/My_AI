"""
Routes de la bibliothèque de prompts (prompts.py)

  GET    /api/prompts         tous les prompts
  POST   /api/prompts         crée un prompt (nom, commande, description, contenu)
  PUT    /api/prompts/{id}    modifie un prompt
  DELETE /api/prompts/{id}    supprime un prompt

L'autocomplétion des commandes « / » reste GET /api/prompts/commands (server.py).
"""

from typing import TYPE_CHECKING

from fastapi import FastAPI, HTTPException
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, Field

from interfaces.desktop.prompts import PromptsError

if TYPE_CHECKING:  # pragma: no cover
    from interfaces.desktop.lifecycle import DesktopApp


class PromptBody(BaseModel):
    """POST /api/prompts, PUT /api/prompts/{id}."""

    title: str = Field(default="", max_length=500)
    command: str = Field(default="", max_length=200)
    description: str = Field(default="", max_length=2000)
    content: str = Field(default="", max_length=200_000)


async def _run(func, *args):
    """Écriture du fichier JSON hors de la boucle ; refus → 409 avec son message."""
    try:
        return await run_in_threadpool(func, *args)
    except PromptsError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


def register(api: FastAPI, app: "DesktopApp") -> None:
    """Ajoute les routes des prompts à l'application."""
    # Routes enregistrées par leurs décorateurs
    # pylint: disable=unused-variable

    @api.get("/api/prompts")
    async def prompts():
        return {"prompts": await _run(app.prompts.list)}

    @api.post("/api/prompts")
    async def create_prompt(body: PromptBody):
        prompt = await _run(app.prompts.save, None, body.model_dump())
        app.notify("success", "✅ Prompt créé")
        return prompt

    @api.put("/api/prompts/{template_id}")
    async def update_prompt(template_id: str, body: PromptBody):
        prompt = await _run(app.prompts.save, template_id, body.model_dump())
        app.notify("success", "✅ Prompt enregistré")
        return prompt

    @api.delete("/api/prompts/{template_id}")
    async def delete_prompt(template_id: str):
        await _run(app.prompts.delete, template_id)
        app.notify("success", "🗑️ Prompt supprimé")
        return {"ok": True}
