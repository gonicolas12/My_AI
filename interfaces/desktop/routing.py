"""
Aides communes aux routes du serveur local (server.py et api_*.py)
"""

from typing import TYPE_CHECKING

from fastapi import HTTPException
from fastapi.concurrency import run_in_threadpool

from core.chat_service import ChatError
from core.i18n import tr

if TYPE_CHECKING:  # pragma: no cover
    from core.chat_service import ChatService
    from interfaces.desktop.lifecycle import DesktopApp

# Clé du catalogue (core/locales), traduite à l'envoi
ENGINE_STARTING = "launch.engineStarting"


def chat_service(app: "DesktopApp") -> "ChatService":
    """Service de chat, ou 503 tant que le moteur démarre."""
    service = app.chat
    if service is None:
        raise HTTPException(status_code=503, detail=tr(ENGINE_STARTING))
    return service


def engine_of(app: "DesktopApp"):
    """Moteur, ou 503 tant qu'il démarre."""
    engine = getattr(app, "engine", None)
    if engine is None:
        raise HTTPException(status_code=503, detail=tr(ENGINE_STARTING))
    return engine


async def call(func, *args, **kwargs):
    """Appel bloquant, hors de la boucle ; ChatError → 409 avec son message."""
    try:
        return await run_in_threadpool(func, *args, **kwargs)
    except ChatError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
