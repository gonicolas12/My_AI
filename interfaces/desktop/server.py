"""
Serveur local de l'interface desktop web

Application FastAPI réservée à la fenêtre de l'appli : elle écoute sur
127.0.0.1 uniquement, sur un port libre choisi au lancement, et exige à chaque
requête le jeton tiré au lancement (transmis à la fenêtre dans le fragment de
l'URL). Distincte du serveur Relay, exposé à Internet par les tunnels, elle
n'est jamais montée dessus.

REST pour les lectures et le CRUD, un WebSocket (/ws) pour les événements
(cf. events.py). Les en-têtes Host et Origin sont vérifiés : n'importe quel
site ouvert dans un navigateur peut tenter de joindre 127.0.0.1.
"""

import asyncio
import json
import mimetypes
import secrets
import socket
import threading
import time
import uuid
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, Optional

import uvicorn
from fastapi import FastAPI, File, HTTPException, Request, UploadFile, WebSocket
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, Response
from pydantic import BaseModel, ConfigDict, Field
from starlette.websockets import WebSocketDisconnect

from core.chat_service import ChatError
from interfaces.desktop import api_files, api_voice
from interfaces.desktop import files as local_files
from interfaces.desktop.events import parse_client_message
from interfaces.desktop.previews import PreviewStore
from interfaces.desktop.routing import ENGINE_STARTING as _ENGINE_STARTING
from interfaces.desktop.routing import call, chat_service
from utils.logger import setup_logger

if TYPE_CHECKING:  # pragma: no cover
    from interfaces.desktop.lifecycle import DesktopApp

logger = setup_logger("DesktopServer")

# Sous Windows, le registre peut associer « .js » à text/plain : le navigateur
# refuserait alors les modules JavaScript de l'interface
for _type, _ext in (("application/javascript", ".js"), ("application/javascript", ".mjs"),
                    ("text/css", ".css"), ("image/svg+xml", ".svg"),
                    ("font/woff2", ".woff2"), ("font/woff", ".woff"),
                    ("application/json", ".json"), ("application/wasm", ".wasm")):
    mimetypes.add_type(_type, _ext)

# Interface construite (frontend/dist, versionné)
DIST_DIR = Path(__file__).resolve().parents[2] / "frontend" / "dist"

# Serveur de développement Vite (launch_unified.py --dev), seulement en mode dev
DEV_ORIGINS = ("http://localhost:5173", "http://127.0.0.1:5173")

# Image collée (Ctrl+V) : taille maximale acceptée
_MAX_UPLOAD = 50 * 1024 * 1024

_PLACEHOLDER_PAGE = """<!doctype html>
<html lang="fr"><head><meta charset="utf-8"><title>My_AI</title>
<style>body{background:#0f0f0f;color:#fff;font-family:system-ui,sans-serif;
display:grid;place-items:center;height:100vh;margin:0}p{color:#9ca3af}</style>
</head><body><div><h1>My_AI</h1>
<p>Interface web en construction : le serveur local répond.</p></div></body></html>
"""


def _content_security_policy(port: int) -> str:
    """Politique de sécurité de la page de l'appli : rien hors de ce serveur."""
    return (
        "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data: blob:; font-src 'self' data:; "
        f"connect-src 'self' ws://127.0.0.1:{port} ws://localhost:{port}; "
        "frame-src 'self' blob: data:; object-src 'none'; base-uri 'none'; "
        "frame-ancestors 'none'; form-action 'none'"
    )


class SendBody(BaseModel):
    """POST /api/conversation/send (équivalent REST de chat.send)."""

    text: str = ""
    attachment_ids: Optional[list] = None
    edit_mid: Optional[str] = None
    regenerate: bool = False


class NavigateBody(BaseModel):
    """POST /api/conversation/branches/{mid} : variante à afficher."""

    version: int


class AttachmentBody(BaseModel):
    """POST /api/attachments : fichier choisi (dialogue, glisser-déposer)."""

    path: str
    type: Optional[str] = None


class RelayStartBody(BaseModel):
    """POST /api/relay/start."""

    tunnel: Optional[bool] = None  # None : réglage relay.tunnel


class UiStateBody(BaseModel):
    """PUT /api/ui : état de l'interface retenu d'un lancement à l'autre."""

    model_config = ConfigDict(extra="forbid")

    sidebar_open: Optional[bool] = None
    # Volet d'aperçu : de 320 à 1200 px, comme dans Tk
    preview_width: Optional[int] = Field(default=None, ge=320, le=1200)


class RatingBody(BaseModel):
    """POST /api/conversation/messages/{mid}/rating."""

    score: int


class DesktopServer:
    """Serveur uvicorn de l'appli, dans son propre fil."""

    def __init__(self, app: "DesktopApp", port: int = 0):
        self._app = app
        self._requested_port = port
        self.port: Optional[int] = None
        self._server: Optional[uvicorn.Server] = None
        self._thread: Optional[threading.Thread] = None
        # Liens vers les fichiers locaux et pages d'aperçu : valables pour ce lancement
        self.links = local_files.FileLinks(secrets.token_bytes(32))
        self.previews = PreviewStore()
        self.fastapi = create_app(app, self)

    # ── Contrôles d'accès ───────────────────────────────────────────────────

    def allowed_hosts(self) -> set:
        """En-têtes Host acceptés : ce serveur, et rien d'autre (DNS rebinding)."""
        return {f"127.0.0.1:{self.port}", f"localhost:{self.port}"}

    def allowed_origins(self) -> set:
        """Origines acceptées : la page de ce serveur, et Vite en mode dev."""
        origins = {f"http://127.0.0.1:{self.port}", f"http://localhost:{self.port}"}
        if self._app.dev:
            origins.update(DEV_ORIGINS)
        return origins

    def check_token(self, token: Optional[str]) -> bool:
        """Compare le jeton reçu à celui du lancement (temps constant)."""
        return bool(token) and secrets.compare_digest(str(token), self._app.token)

    # ── Démarrage, arrêt ────────────────────────────────────────────────────

    def start(self) -> int:
        """Lie le port sur 127.0.0.1 puis lance uvicorn ; renvoie le port."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind(("127.0.0.1", self._requested_port))
        self.port = sock.getsockname()[1]
        config = uvicorn.Config(
            app=self.fastapi,
            log_level="warning",
            access_log=False,
            lifespan="off",
            ws_ping_interval=20,
            ws_ping_timeout=20,
        )
        self._server = uvicorn.Server(config)
        self._thread = threading.Thread(
            target=self._server.run, kwargs={"sockets": [sock]},
            name="desktop-server", daemon=True,
        )
        self._thread.start()
        deadline = time.time() + 15
        while not self._server.started and time.time() < deadline:
            if not self._thread.is_alive():
                raise RuntimeError("Le serveur local n'a pas démarré")
            time.sleep(0.02)
        logger.info("Serveur desktop sur http://127.0.0.1:%s", self.port)
        return self.port

    def stop(self) -> None:
        """Arrête uvicorn."""
        if self._server is not None:
            self._server.should_exit = True
        if self._thread is not None and self._thread.is_alive():
            self._thread.join(timeout=5)


def create_app(app: "DesktopApp", server: DesktopServer) -> FastAPI:
    """Application FastAPI : REST, WebSocket et fichiers de l'interface."""
    api = FastAPI(title="My_AI desktop", docs_url=None, redoc_url=None, openapi_url=None)

    # ── Garde : Host, Origin, jeton ─────────────────────────────────────────

    @api.middleware("http")
    async def guard(request: Request, call_next):
        if request.headers.get("host", "") not in server.allowed_hosts():
            return JSONResponse({"detail": "Hôte refusé"}, status_code=403)
        origin = request.headers.get("origin")
        if origin is not None and origin not in server.allowed_origins():
            return JSONResponse({"detail": "Origine refusée"}, status_code=403)
        if request.url.path.startswith("/api/"):
            auth = request.headers.get("authorization", "")
            token = auth[7:] if auth.lower().startswith("bearer ") else None
            token = token or request.query_params.get("token")
            if not server.check_token(token):
                return JSONResponse({"detail": "Jeton absent ou invalide"}, status_code=401)
        response = await call_next(request)
        # Une page d'aperçu porte sa propre politique (previews.py) : l'isoler
        # de l'appli est son rôle, elle ne doit pas hériter de la sienne
        if (response.headers.get("content-type", "").startswith("text/html")
                and "content-security-policy" not in response.headers):
            response.headers["Content-Security-Policy"] = _content_security_policy(server.port)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        return response

    def chat():
        return chat_service(app)

    # ── Application ─────────────────────────────────────────────────────────

    @api.get("/api/status")
    async def status():
        # Seq lu avant l'état : la fenêtre applique ensuite les événements plus
        # récents, sans jamais revenir à un état plus ancien
        seq = app.bus.last_seq
        return {
            "status": app.status(),
            "relay": app.relay_status(),
            "dev": app.dev,
            "chat": app.chat is not None,
            "seq": seq,
        }

    @api.get("/api/ui")
    async def ui_state():
        return app.ui_state()

    @api.put("/api/ui")
    async def save_ui_state(body: UiStateBody):
        return app.set_ui_state(body.model_dump(exclude_none=True))

    @api.post("/api/shutdown")
    async def shutdown():
        threading.Thread(target=app.shutdown, name="desktop-shutdown", daemon=True).start()
        return {"ok": True}

    # ── Conversation ────────────────────────────────────────────────────────

    @api.get("/api/conversation")
    async def conversation():
        return chat().snapshot()

    @api.get("/api/conversations/{conversation_id}")
    async def conversation_by_id(conversation_id: str):
        snapshot = chat().snapshot()
        if snapshot.get("conversation_id") != conversation_id:
            raise HTTPException(status_code=404, detail="Conversation non ouverte")
        return snapshot

    @api.post("/api/conversation/send")
    async def send(body: SendBody):
        request_id = await call(
            chat().send, body.text, body.attachment_ids,
            edit_mid=body.edit_mid, regenerate=body.regenerate,
        )
        return {"request_id": request_id}

    @api.post("/api/conversation/stop")
    async def stop():
        return {"stopped": chat().stop()}

    @api.post("/api/conversation/new")
    async def new_conversation():
        await call(chat().new_conversation)
        return {"ok": True}

    @api.post("/api/conversation/clear")
    async def clear_conversation():
        await call(chat().clear)
        return {"ok": True}

    @api.post("/api/conversation/save")
    async def save_conversation():
        return {"saved": await call(chat().save_session)}

    @api.post("/api/conversation/branches/{mid}")
    async def navigate(mid: str, body: NavigateBody):
        await call(chat().navigate, mid, body.version)
        return {"ok": True}

    @api.post("/api/conversation/messages/{mid}/rating")
    async def rate(mid: str, body: RatingBody):
        return {"rating": await call(chat().rate, mid, body.score)}

    # ── Slash commands ──────────────────────────────────────────────────────

    @api.get("/api/prompts/commands")
    async def prompt_commands(prefix: str = ""):
        """Commandes « / » dont le nom commence par `prefix` (autocomplétion)."""
        library = getattr(app.engine, "prompt_library", None) if app.engine else None
        if library is None or not hasattr(library, "search"):
            return {"commands": []}
        try:
            matches = await run_in_threadpool(library.search, prefix)
        except Exception:  # pylint: disable=broad-except
            matches = []
        return {"commands": [
            {"command": item.get("command") or "", "title": item.get("title") or "",
             "description": item.get("description") or ""}
            for item in matches if item.get("command")
        ]}

    # ── Sessions ────────────────────────────────────────────────────────────

    @api.get("/api/sessions")
    async def sessions():
        return {"sessions": await call(chat().list_sessions)}

    @api.post("/api/sessions/{session_id}/load")
    async def load_session(session_id: str):
        await call(chat().load_session, session_id)
        return {"ok": True}

    @api.delete("/api/sessions/{session_id}")
    async def delete_session(session_id: str):
        return {"deleted": await call(chat().delete_session, session_id)}

    # ── Pièces jointes ──────────────────────────────────────────────────────

    @api.get("/api/attachments")
    async def attachments():
        return {"attachments": chat().attachments()}

    @api.post("/api/attachments")
    async def add_attachment(body: AttachmentBody):
        return await call(chat().add_attachment, body.path, body.type)

    @api.post("/api/attachments/upload")
    async def upload_attachment(file: UploadFile = File(...)):
        """Image collée (Ctrl+V) ou fichier sans chemin : copié dans un dossier temporaire."""
        service = chat()
        data = await file.read(_MAX_UPLOAD + 1)
        if len(data) > _MAX_UPLOAD:
            raise HTTPException(status_code=413, detail="Fichier trop volumineux")
        name = Path(file.filename or "fichier").name or "fichier"
        # Un sous-dossier par envoi : le fichier garde son nom, sans collision
        folder = local_files.UPLOAD_DIR / uuid.uuid4().hex[:12]
        folder.mkdir(parents=True, exist_ok=True)
        target = folder / name
        target.write_bytes(data)
        return await call(service.add_attachment, str(target))

    @api.delete("/api/attachments/{attachment_id}")
    async def remove_attachment(attachment_id: str):
        return {"removed": await call(chat().remove_attachment, attachment_id)}

    # ── Relay ───────────────────────────────────────────────────────────────

    @api.get("/api/relay")
    async def relay():
        return app.relay_status()

    @api.post("/api/relay/start")
    async def relay_start(body: RelayStartBody):
        if app.engine is None:
            raise HTTPException(status_code=503, detail=_ENGINE_STARTING)
        return await run_in_threadpool(app.start_relay, body.tunnel)

    @api.post("/api/relay/stop")
    async def relay_stop():
        return await run_in_threadpool(app.stop_relay)

    # ── Événements ──────────────────────────────────────────────────────────

    @api.websocket("/ws")
    async def events(websocket: WebSocket):
        host = websocket.headers.get("host", "")
        origin = websocket.headers.get("origin")
        token = websocket.query_params.get("token")
        if (host not in server.allowed_hosts()
                or (origin is not None and origin not in server.allowed_origins())
                or not server.check_token(token)):
            await websocket.close(code=4403)
            return
        await websocket.accept()
        await _serve_events(app, websocket)

    # ── Fichiers locaux et aperçus (api_files.py) ───────────────────────────

    api_files.register(api, app, server)
    api_voice.register(api, app)

    # ── Interface ───────────────────────────────────────────────────────────

    @api.get("/{path:path}")
    async def frontend(path: str):
        if path.startswith(("api/", "ws", "files/", "preview/")):
            raise HTTPException(status_code=404)
        index = DIST_DIR / "index.html"
        if not index.is_file():
            return HTMLResponse(_PLACEHOLDER_PAGE)
        candidate = (DIST_DIR / path).resolve() if path else index.resolve()
        try:
            candidate.relative_to(DIST_DIR.resolve())
        except ValueError:
            raise HTTPException(status_code=404) from None
        if candidate.is_file():
            return FileResponse(candidate)
        if "." in Path(path).name:
            return Response(status_code=404)
        return FileResponse(index)

    return api


async def _serve_events(app: "DesktopApp", websocket: WebSocket) -> None:
    """Flux d'événements d'une fenêtre ; ses messages vont au service de chat."""
    loop = asyncio.get_running_loop()
    queue: "asyncio.Queue[Dict[str, Any]]" = asyncio.Queue()

    def deliver(event: Dict[str, Any]) -> None:
        loop.call_soon_threadsafe(queue.put_nowait, event)

    since_raw = websocket.query_params.get("since")
    since = int(since_raw) if since_raw and since_raw.isdigit() else None
    unsubscribe, resumed = app.bus.subscribe(deliver, since)
    # Contrôle, hors protocole d'événements : la fenêtre sait s'il faut relire l'état
    await websocket.send_text(json.dumps({"type": "hello", "resumed": resumed}))

    async def pump() -> None:
        while True:
            event = await queue.get()
            await websocket.send_text(json.dumps(event, ensure_ascii=False, default=str))

    pump_task = asyncio.create_task(pump())
    try:
        while True:
            raw = await websocket.receive_text()
            reply = await _handle_client_message(app, raw)
            if reply is not None:
                await websocket.send_text(json.dumps(reply, ensure_ascii=False, default=str))
    except WebSocketDisconnect:
        pass
    except Exception as exc:  # pylint: disable=broad-except
        logger.info("WebSocket de la fenêtre fermé : %s", exc)
    finally:
        unsubscribe()
        pump_task.cancel()


async def _handle_client_message(app: "DesktopApp", raw: str) -> Optional[Dict[str, Any]]:
    """Exécute un message de la fenêtre ; renvoie la réponse (« reply »)."""
    ref = None
    try:
        data = json.loads(raw)
        if isinstance(data, dict):
            ref = data.get("id")
        message = parse_client_message(data)
    except (ValueError, json.JSONDecodeError) as exc:
        return {"type": "reply", "ref": ref, "ok": False, "error": str(exc)}

    if message.type == "ping":
        return {"type": "reply", "ref": ref, "ok": True, "data": {"pong": True}}
    service = app.chat
    if service is None:
        return {"type": "reply", "ref": ref, "ok": False, "error": _ENGINE_STARTING}
    try:
        if message.type == "chat.send":
            request_id = await run_in_threadpool(
                service.send, message.text, message.attachment_ids,
                edit_mid=message.edit_mid, regenerate=message.regenerate,
            )
            data_out: Dict[str, Any] = {"request_id": request_id}
        elif message.type == "chat.stop":
            data_out = {"stopped": service.stop()}
        elif message.type == "chat.cancel":
            data_out = {"cancelled": service.cancel(message.request_id)}
        elif message.type == "confirm.response":
            data_out = {"done": service.confirm(message.confirm_id, message.accepted)}
        else:  # pragma: no cover - parse_client_message filtre les types
            data_out = {}
    except ChatError as exc:
        return {"type": "reply", "ref": ref, "ok": False, "error": str(exc)}
    return {"type": "reply", "ref": ref, "ok": True, "data": data_out}
