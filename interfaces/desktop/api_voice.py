"""
Routes de la voix (voice.py)

  GET  /api/voice              disponibilité, états, lecture automatique
  POST /api/voice/input        micro : démarre l'enregistrement, ou l'arrête
  POST /api/voice/input/stop   arrête l'enregistrement en cours
  POST /api/voice/speak        lecture d'une réponse (bascule : la relancer l'arrête)
  POST /api/voice/stop         coupe la lecture
  PUT  /api/voice/autoread     lecture automatique des réponses (ui.tts_autoread)
"""

from typing import TYPE_CHECKING, Optional

from fastapi import FastAPI
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, Field

if TYPE_CHECKING:  # pragma: no cover
    from interfaces.desktop.lifecycle import DesktopApp


class SpeakBody(BaseModel):
    """POST /api/voice/speak."""

    text: str = Field(max_length=500_000)
    key: Optional[str] = None  # ce qui est lu (identifiant de la réponse)


class AutoreadBody(BaseModel):
    """PUT /api/voice/autoread."""

    enabled: bool


def register(api: FastAPI, app: "DesktopApp") -> None:
    """Ajoute les routes de la voix à l'application."""
    # Routes enregistrées par leurs décorateurs
    # pylint: disable=unused-variable

    @api.get("/api/voice")
    async def voice_status():
        return app.voice.status()

    @api.post("/api/voice/input")
    async def voice_input():
        return {"state": await run_in_threadpool(app.voice.toggle_input)}

    @api.post("/api/voice/input/stop")
    async def voice_input_stop():
        await run_in_threadpool(app.voice.stop_input)
        return {"ok": True}

    @api.post("/api/voice/speak")
    async def voice_speak(body: SpeakBody):
        return {"state": await run_in_threadpool(app.voice.toggle_speak, body.text, body.key)}

    @api.post("/api/voice/stop")
    async def voice_stop():
        await run_in_threadpool(app.voice.stop_speaking)
        return {"ok": True}

    @api.put("/api/voice/autoread")
    async def voice_autoread(body: AutoreadBody):
        return {"autoread": await run_in_threadpool(app.voice.set_autoread, body.enabled)}
