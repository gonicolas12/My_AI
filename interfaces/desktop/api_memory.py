"""
Routes de la Mémoire (memory.py)

  GET    /api/memory?tab=&q=&category=&page=   une page : éléments, total, compteurs
  POST   /api/memory/facts                    ajoute un fait (catégorie, contenu)
  PUT    /api/memory/{tab}/{entry_id}         nouveau contenu
  DELETE /api/memory/{tab}/{entry_id}?at_source=   supprime (conversation : aussi à la source)
"""

from typing import TYPE_CHECKING, Optional

from fastapi import FastAPI, HTTPException
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, Field

from interfaces.desktop.memory import MemoryPanelError

if TYPE_CHECKING:  # pragma: no cover
    from interfaces.desktop.lifecycle import DesktopApp


class FactBody(BaseModel):
    """POST /api/memory/facts."""

    category: str = "general"
    text: str = Field(max_length=100_000)


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

    @api.post("/api/memory/facts")
    async def add_fact(body: FactBody):
        fact_id = await _run(app.memory.add_fact, body.category, body.text)
        app.notify("success", "✅ Fait ajouté")
        return {"id": fact_id}

    @api.put("/api/memory/{tab}/{entry_id}")
    async def update_entry(tab: str, entry_id: str, body: ContentBody):
        await _run(app.memory.update, tab, entry_id, body.text)
        app.notify("success", "✅ Modifié")
        return {"ok": True}

    @api.delete("/api/memory/{tab}/{entry_id}")
    async def delete_entry(tab: str, entry_id: str, at_source: bool = True):
        await _run(app.memory.delete, tab, entry_id, at_source)
        app.notify("success", "🗑️ Supprimé")
        return {"ok": True}
