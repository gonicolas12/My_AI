"""
Routes des Réglages et de l'assistant de premier lancement

  GET  /api/settings                     réglages de config.yaml, modèle de base
  GET  /api/settings/models              modèles d'Ollama (installés, bases possibles)
  GET  /api/settings/models/job          téléchargement ou création en cours (ou dernier)
  POST /api/settings/models/pull         télécharge un modèle
  POST /api/settings/models/apply        régénère my_ai à partir d'un modèle de base
  PUT  /api/settings/generation          température, fenêtre de contexte, délai
  PUT  /api/settings/flags               langue par défaut, Relay au lancement
  GET  /api/i18n                         langue de l'interface, langues proposées
  PUT  /api/i18n                         langue de l'interface et du modèle, à chaud
  POST /api/settings/onboarding/restart  l'assistant reviendra au prochain démarrage

  GET  /api/onboarding                   assistant : Ollama, matériel, recommandation
  POST /api/onboarding/install           « Installer » : modèle téléchargé, my_ai créé
  POST /api/onboarding/skip              « Passer » : marqué comme fait, lancement repris
  POST /api/onboarding/finish            « Démarrer My_AI » : lancement repris
"""

from typing import TYPE_CHECKING, Any

from fastapi import FastAPI, HTTPException
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, Field

from core.i18n import tr
from interfaces.desktop.model_setup import ModelJobError
from interfaces.desktop.settings import SettingsError

if TYPE_CHECKING:  # pragma: no cover
    from interfaces.desktop.lifecycle import DesktopApp


class ModelBody(BaseModel):
    """Nom d'un modèle Ollama."""

    name: str = Field(max_length=200)


class GenerationBody(BaseModel):
    """PUT /api/settings/generation."""

    temperature: float
    num_ctx: int
    timeout: float


class FlagBody(BaseModel):
    """PUT /api/settings/flags."""

    name: str
    value: Any


class LanguageBody(BaseModel):
    """PUT /api/i18n."""

    language: str = Field(max_length=16)


async def _run(func, *args):
    """Appel bloquant hors de la boucle ; refus → 409 avec son message."""
    try:
        return await run_in_threadpool(func, *args)
    except (ModelJobError, SettingsError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


def register(api: FastAPI, app: "DesktopApp") -> None:
    """Ajoute les routes des Réglages et de l'assistant à l'application."""
    # Routes enregistrées par leurs décorateurs
    # pylint: disable=unused-variable

    @api.get("/api/settings")
    async def settings():
        return await _run(app.settings.snapshot)

    @api.get("/api/settings/models")
    async def models():
        return await _run(app.settings.models)

    @api.get("/api/settings/models/job")
    async def model_job():
        return {"job": app.model_jobs.status()}

    @api.post("/api/settings/models/pull")
    async def pull(body: ModelBody):
        await _run(app.model_jobs.pull, body.name)
        return {"job": app.model_jobs.status()}

    @api.post("/api/settings/models/apply")
    async def apply(body: ModelBody):
        await _run(app.model_jobs.apply, body.name)
        return {"job": app.model_jobs.status()}

    @api.put("/api/settings/generation")
    async def generation(body: GenerationBody):
        saved = await _run(app.settings.save_generation, body.temperature, body.num_ctx,
                           body.timeout)
        app.notify("success", tr("settings.saved"))
        return saved

    @api.put("/api/settings/flags")
    async def flags(body: FlagBody):
        # La langue s'applique à chaud partout (fenêtre, moteur, Relay)
        if body.name == "language.default":
            await _run(app.set_language, body.value)
        else:
            await _run(app.settings.set_flag, body.name, body.value)
        return await _run(app.settings.snapshot)

    @api.get("/api/i18n")
    async def language():
        return app.language_view()

    @api.put("/api/i18n")
    async def set_language(body: LanguageBody):
        return await _run(app.set_language, body.language)

    @api.post("/api/settings/onboarding/restart")
    async def restart_onboarding():
        await _run(app.settings.restart_onboarding)
        app.notify("success", tr("settings.wizardRestart"))
        return {"ok": True}

    @api.get("/api/onboarding")
    async def onboarding():
        return await _run(app.first_launch.info)

    @api.post("/api/onboarding/install")
    async def onboarding_install(body: ModelBody):
        await _run(app.first_launch.install, body.name)
        return {"job": app.model_jobs.status()}

    @api.post("/api/onboarding/skip")
    async def onboarding_skip():
        await _run(app.first_launch.skip)
        return {"ok": True}

    @api.post("/api/onboarding/finish")
    async def onboarding_finish():
        app.first_launch.finish()
        return {"ok": True}
