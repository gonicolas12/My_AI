"""
Relay Server - Serveur FastAPI avec WebSocket pour l'accès mobile.

Expose une interface web mobile-friendly et un endpoint WebSocket
pour la communication en temps réel avec My_AI depuis un téléphone.
Gère l'authentification par token et plusieurs tunnels en parallèle
(cloudflared + serveo + localhost.run) avec failover client-side via
une page de routage statique hébergée sur GitHub Pages.
"""

import asyncio
import base64
import hashlib
import json
import os
import re
import secrets
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests

from core.config import get_config
from utils.logger import setup_logger

from .relay_bridge import RelayBridge, RelayMessage

# Page de routage statique (GitHub Pages) qui ping les tunnels côté client
# et redirige vers le premier vivant. Évite que le téléphone soit bloqué
# si l'un des providers est filtré par l'opérateur mobile.
_ROUTER_PAGE_URL = "https://gonicolas12.github.io/My_AI/router.html"

# Extensions acceptées pour l'upload mobile (doivent correspondre
# aux processeurs supportés côté GUI dans file_handling.py)
_IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp", ".tiff", ".tif"}
_DOC_EXTS = {
    ".pdf", ".docx", ".doc", ".xlsx", ".xls", ".csv",
    ".py", ".js", ".html", ".css", ".json", ".xml", ".md", ".txt",
}
_MAX_UPLOAD_SIZE = 25 * 1024 * 1024  # 25 Mo

# ---------------------------------------------------------------------------
# Imports optionnels
# ---------------------------------------------------------------------------

try:
    import uvicorn
    from fastapi import (FastAPI, File, HTTPException, Query, UploadFile,
                         WebSocket, WebSocketDisconnect)
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import HTMLResponse
    from fastapi.staticfiles import StaticFiles

    _FASTAPI_AVAILABLE = True
except ImportError:
    _FASTAPI_AVAILABLE = False

try:
    import qrcode
    import qrcode.image.svg

    _QR_AVAILABLE = True
except ImportError:
    _QR_AVAILABLE = False

logger = setup_logger("RelayServer")

# ---------------------------------------------------------------------------
# Chemin vers les fichiers statiques
# ---------------------------------------------------------------------------

_STATIC_DIR = Path(__file__).parent / "static"


class RelayServer:
    """
    Serveur Relay pour l'accès mobile à My_AI.

    Fonctionnalités :
    - Interface web mobile-friendly (PWA)
    - WebSocket temps réel pour le chat
    - Authentification par token
    - Tunnel cloudflared pour l'accès externe
    """

    def __init__(
        self,
        ai_engine: Optional[Any] = None,
        config: Optional[Dict[str, Any]] = None,
    ) -> None:
        # Configuration
        if config is None:
            cfg = get_config()
            config = cfg.get_section("relay") or {}

        self._ai_engine = ai_engine
        self._host: str = config.get("host", "0.0.0.0")
        self._port: int = int(config.get("port", 8765))
        self._password: str = config.get("password", "")
        raw_response_timeout = config.get("response_timeout", 500)
        try:
            self._response_timeout: float = float(raw_response_timeout)
        except (TypeError, ValueError):
            self._response_timeout = 500.0
        if self._response_timeout <= 0:
            self._response_timeout = 500.0

        # Générer un token d'authentification
        self._auth_token: str = ""
        self._generate_auth_token()

        # Bridge pour la synchronisation GUI
        self._bridge = RelayBridge()

        # État du serveur
        self._server_thread: Optional[threading.Thread] = None
        self._uvicorn_server: Optional[Any] = None
        self._running: bool = False
        self._start_time: Optional[float] = None

        # Tunnels actifs : un sous-processus + une URL publique par provider.
        # Plusieurs providers tournent en parallèle pour qu'au moins un soit
        # joignable même si l'opérateur mobile en filtre certains (ex.
        # *.trycloudflare.com bloqué par certains MVNO 5G).
        self._tunnel_processes: Dict[str, subprocess.Popen] = {}
        self._tunnel_urls: Dict[str, str] = {}
        self._tunnel_urls_lock = threading.Lock()
        # Liste des providers à activer. Personnalisable via config.yaml :
        #   relay.tunnel_providers: ["cloudflared", "serveo", "localhost.run"]
        raw_providers = config.get(
            "tunnel_providers",
            ["cloudflared", "serveo", "localhost.run"],
        )
        if isinstance(raw_providers, str):
            raw_providers = [raw_providers]
        self._tunnel_provider_names: List[str] = [
            p.strip().lower() for p in raw_providers if p and p.strip()
        ] or ["cloudflared"]

        # WebSocket clients connectés
        self._ws_clients: List[WebSocket] = []

        # Boucle asyncio du serveur (initialisée à l'accept de la première
        # connexion WS) pour broadcaster depuis un thread GUI.
        self._loop: Optional[asyncio.AbstractEventLoop] = None

        # Uploads mobiles en attente : file_id -> {"path", "is_image", "filename"}
        self._uploads: Dict[str, Dict[str, Any]] = {}
        self._uploads_lock = threading.Lock()
        self._upload_dir = Path(tempfile.gettempdir()) / "my_ai_relay_uploads"
        self._upload_dir.mkdir(exist_ok=True)

        if not _FASTAPI_AVAILABLE:
            logger.warning(
                "FastAPI/uvicorn non installé. Le serveur Relay ne sera pas disponible."
            )
            return

        self._app = self._create_app()

    # ------------------------------------------------------------------
    # Propriétés
    # ------------------------------------------------------------------

    @property
    def ai_engine(self) -> Optional[Any]:
        """Retourne le moteur IA actuellement utilisé par le Relay."""
        return self._ai_engine

    @ai_engine.setter
    def ai_engine(self, engine: Any):
        self._ai_engine = engine

    @property
    def bridge(self) -> RelayBridge:
        """Retourne le RelayBridge pour synchroniser les messages entre les deux côtés."""
        return self._bridge

    @property
    def tunnel_url(self) -> Optional[str]:
        """Retourne la première URL de tunnel publique disponible (compat).

        Pour la liste complète des tunnels actifs (un par provider), utiliser
        `tunnel_urls`. Cette propriété est conservée pour la rétrocompat
        avec l'ancienne popup GUI et le code externe.
        """
        with self._tunnel_urls_lock:
            for name in self._tunnel_provider_names:
                url = self._tunnel_urls.get(name)
                if url:
                    return url
            # Fallback : n'importe quelle URL connue (ordre indéterminé)
            for url in self._tunnel_urls.values():
                if url:
                    return url
        return None

    @property
    def tunnel_urls(self) -> Dict[str, str]:
        """Retourne un snapshot des URLs publiques actives par provider."""
        with self._tunnel_urls_lock:
            return dict(self._tunnel_urls)

    @property
    def auth_token(self) -> str:
        """Retourne le token d'authentification actuel pour accéder au Relay."""
        return self._auth_token

    @property
    def relay_url(self) -> Optional[str]:
        """URL complète pour accéder au Relay (page de routage + tunnels + token).

        Renvoie l'URL de la page de routage GitHub Pages, qui pinge tous
        les tunnels publiés et redirige vers le premier joignable. Cette
        URL est ce qui est encodé dans le QR code : un seul scan, failover
        automatique côté client.
        """
        with self._tunnel_urls_lock:
            urls = [u for u in self._tunnel_urls.values() if u]
        if not urls:
            return None
        payload = json.dumps({"urls": urls, "token": self._auth_token})
        encoded = base64.urlsafe_b64encode(payload.encode("utf-8")).decode("ascii").rstrip("=")
        return f"{_ROUTER_PAGE_URL}#d={encoded}"

    @property
    def port(self) -> int:
        """Port sur lequel le serveur écoute."""
        return self._port

    @property
    def response_timeout(self) -> float:
        """Délai max d'attente de la réponse IA côté WebSocket (secondes)."""
        return self._response_timeout

    @property
    def upload_dir(self) -> Path:
        """Dossier local temporaire des fichiers uploadés depuis le mobile."""
        return self._upload_dir

    @property
    def start_time(self) -> Optional[float]:
        """Timestamp de démarrage du serveur, ou None si non démarré."""
        return self._start_time

    @property
    def ws_clients(self) -> List["WebSocket"]:
        """Liste des clients WebSocket actuellement connectés."""
        return self._ws_clients

    # ------------------------------------------------------------------
    # Authentification
    # ------------------------------------------------------------------

    def _generate_auth_token(self):
        """Génère un token d'authentification unique."""
        if self._password:
            # Token dérivé du mot de passe (reproductible)
            self._auth_token = hashlib.sha256(
                self._password.encode()
            ).hexdigest()[:16]
        else:
            # Token aléatoire (change à chaque démarrage)
            self._auth_token = secrets.token_urlsafe(12)

    def verify_token(self, token: str) -> bool:
        """Vérifie si le token fourni est valide."""
        return token == self._auth_token

    def get_static_assets_version(self) -> str:
        """Version de cache-busting des assets statiques du Relay.

        Basée sur le dernier mtime connu de index.html, app.js et style.css.
        """
        asset_paths = [
            _STATIC_DIR / "index.html",
            _STATIC_DIR / "app.js",
            _STATIC_DIR / "style.css",
        ]
        mtimes: List[int] = []
        for path in asset_paths:
            if not path.exists():
                continue
            try:
                mtimes.append(int(path.stat().st_mtime))
            except OSError:
                continue
        if not mtimes:
            return str(int(time.time()))
        return str(max(mtimes))

    def register_upload(
        self,
        file_id: str,
        path: Path,
        is_image: bool,
        filename: str,
    ) -> None:
        """Enregistre un upload mobile en attente de consommation par le WS."""
        with self._uploads_lock:
            self._uploads[file_id] = {
                "path": str(path),
                "is_image": is_image,
                "filename": filename,
                "ts": time.time(),
            }

    def consume_upload_ids(self, file_ids: List[str]) -> tuple[Optional[str], List[str]]:
        """Consomme les file_ids et retourne (image_path, file_paths)."""
        image_path: Optional[str] = None
        file_paths: List[str] = []
        with self._uploads_lock:
            for fid in file_ids:
                info = self._uploads.pop(fid, None)
                if not info:
                    continue
                if info.get("is_image") and image_path is None:
                    image_path = info["path"]
                else:
                    file_paths.append(info["path"])
        return image_path, file_paths

    # ------------------------------------------------------------------
    # Construction de l'application FastAPI
    # ------------------------------------------------------------------

    def _create_app(self) -> "FastAPI":
        app = FastAPI(
            title="My_AI Relay",
            description="Accès mobile à My_AI",
            version="1.0.0",
            docs_url=None,  # Pas de docs Swagger en production
            redoc_url=None,
        )

        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        self._register_routes(app)

        # Servir les fichiers statiques (CSS, JS)
        if _STATIC_DIR.exists():
            app.mount("/static", StaticFiles(directory=str(_STATIC_DIR)), name="static")

        return app

    def _register_routes(self, app: "FastAPI") -> None:
        server = self  # Capture pour les closures

        # =================================================================
        # GET / — Page d'authentification + interface mobile
        # =================================================================

        @app.get("/", response_class=HTMLResponse)
        async def serve_app(token: Optional[str] = Query(default=None)):
            """Sert l'interface mobile (vérifie le token via query param)."""
            index_file = _STATIC_DIR / "index.html"
            if not index_file.exists():
                return HTMLResponse(
                    "<h1>My_AI Relay</h1><p>Interface mobile non trouvée.</p>",
                    status_code=500,
                )

            if token and server.verify_token(token):
                html = index_file.read_text(encoding="utf-8")
                # Injecter le token dans le HTML pour le WebSocket
                html = html.replace("%%RELAY_TOKEN%%", token)
                html = html.replace("%%ASSET_VERSION%%", server.get_static_assets_version())
                return HTMLResponse(html)
            else:
                # Page de login
                return HTMLResponse(_get_login_page())

        # =================================================================
        # POST /auth — Authentification par mot de passe
        # =================================================================

        @app.post("/auth")
        async def authenticate(data: dict):
            """Authentifie avec un mot de passe et retourne le token."""
            password = data.get("password", "")
            if not password:
                raise HTTPException(status_code=400, detail="Mot de passe requis")

            # Vérifier le mot de passe
            expected_token = hashlib.sha256(
                password.encode()
            ).hexdigest()[:16]

            if expected_token == server.auth_token:
                return {"token": server.auth_token}

            # Si pas de mot de passe configuré, vérifier directement le token
            if server.verify_token(password):
                return {"token": server.auth_token}

            raise HTTPException(status_code=401, detail="Mot de passe incorrect")

        # =================================================================
        # GET /api/health — Santé du serveur
        # =================================================================

        @app.get("/api/health")
        async def health():
            uptime = round(time.time() - server.start_time, 2) if server.start_time else 0
            return {
                "status": "ok",
                "relay": "My_AI Relay",
                "version": "1.0.0",
                "uptime_seconds": uptime,
                "engine_ready": server.ai_engine is not None,
                "connected_clients": len(server.ws_clients),
            }

        # =================================================================
        # GET /api/tunnels — Liste des tunnels publics actuellement actifs
        # (utilisé par la page de routage GitHub Pages pour faire le ping
        # côté client et choisir un endpoint vivant). Pas authentifié : la
        # liste contient juste des URLs déjà publiques.
        # =================================================================

        @app.get("/api/tunnels")
        async def tunnels():
            return {"tunnels": server.tunnel_urls}

        # =================================================================
        # GET /api/history — Historique de la conversation
        # =================================================================

        @app.get("/api/history")
        async def get_history(token: str = Query(...)):
            if not server.verify_token(token):
                raise HTTPException(status_code=401, detail="Non autorisé")
            return {"history": server.bridge.history}

        # =================================================================
        # GET /api/pending — Récupérer une réponse IA en attente (après
        # reconnexion d'un mobile dont le WebSocket est mort pendant la
        # génération). Le client fournit le dernier message_id connu.
        # =================================================================

        @app.get("/api/pending")
        async def get_pending(
            token: str = Query(...),
            message_id: str = Query(...),
        ):
            if not server.verify_token(token):
                raise HTTPException(status_code=401, detail="Non autorisé")
            # Priorité 1 : réponse terminée en cache
            pending = server.bridge.consume_pending_response(message_id)
            if pending is not None:
                return {
                    "pending": True,
                    "final": True,
                    "message_id": message_id,
                    "message": pending,
                    "timestamp": datetime.now().isoformat(),
                }
            # Priorité 2 : génération encore en cours, retourner l'état courant
            partial = server.bridge.get_active_stream(message_id)
            if partial is not None:
                return {
                    "pending": True,
                    "final": False,
                    "message_id": message_id,
                    "message": partial,
                    "timestamp": datetime.now().isoformat(),
                }
            return {"pending": False, "message_id": message_id}

        # =================================================================
        # POST /api/upload — Upload de fichier/image depuis le mobile
        # =================================================================

        @app.post("/api/upload")
        async def upload_file(
            token: str = Query(...),
            file: UploadFile = File(...),
        ):
            """Reçoit un fichier depuis le mobile, le stocke localement,
            et renvoie un file_id à réutiliser dans le prochain message."""
            if not server.verify_token(token):
                raise HTTPException(status_code=401, detail="Non autorisé")

            original_name = file.filename or "upload"
            safe_name = re.sub(r"[^\w\.\-]", "_", original_name)[:120] or "upload"
            ext = Path(safe_name).suffix.lower()

            if ext in _IMAGE_EXTS:
                is_image = True
            elif ext in _DOC_EXTS:
                is_image = False
            else:
                raise HTTPException(
                    status_code=415,
                    detail=f"Format non supporté : {ext or 'inconnu'}",
                )

            # Écrire le fichier par morceaux pour contrôler la taille
            file_id = uuid.uuid4().hex[:16]
            dest = server.upload_dir / f"{file_id}_{safe_name}"
            size = 0
            try:
                with dest.open("wb") as f:
                    while True:
                        chunk = await file.read(65536)
                        if not chunk:
                            break
                        size += len(chunk)
                        if size > _MAX_UPLOAD_SIZE:
                            f.close()
                            dest.unlink(missing_ok=True)
                            raise HTTPException(
                                status_code=413,
                                detail=(
                                    f"Fichier trop volumineux "
                                    f"(> {_MAX_UPLOAD_SIZE // (1024 * 1024)} Mo)"
                                ),
                            )
                        f.write(chunk)
            except HTTPException:
                raise
            except Exception as e:
                logger.error("Erreur upload Relay : %s", e)
                try:
                    dest.unlink(missing_ok=True)
                except Exception:
                    pass
                raise HTTPException(status_code=500, detail="Erreur écriture fichier") from e

            server.register_upload(
                file_id=file_id,
                path=dest,
                is_image=is_image,
                filename=safe_name,
            )

            logger.info(
                "Upload Relay reçu : %s (%d octets, image=%s, id=%s)",
                safe_name, size, is_image, file_id,
            )
            return {
                "file_id": file_id,
                "filename": safe_name,
                "is_image": is_image,
                "size": size,
            }

        # =================================================================
        # WebSocket /ws — Chat temps réel
        # =================================================================

        @app.websocket("/ws")
        async def websocket_endpoint(websocket: WebSocket):
            # Extraire le token manuellement depuis les query params
            # (Query(...) de FastAPI peut rejeter silencieusement le WS
            # handshake avant accept(), surtout à travers un tunnel)
            token = websocket.query_params.get("token", "")
            logger.info("Tentative de connexion WebSocket (token=%s...)", token[:6] if token else "vide")

            if not token or not server.verify_token(token):
                logger.warning("WebSocket rejeté : token invalide")
                await websocket.close(code=4001, reason="Non autorisé")
                return

            await websocket.accept()
            server.ws_clients.append(websocket)
            server.bridge.connected_clients = len(server.ws_clients)
            logger.info(
                "Client Relay connecté (%d actifs)", len(server.ws_clients)
            )

            try:
                while True:
                    data = await websocket.receive_text()
                    msg_data = json.loads(data)

                    if msg_data.get("type") == "chat":
                        user_text = msg_data.get("message", "").strip()
                        raw_ids = msg_data.get("file_ids", []) or []
                        if not isinstance(raw_ids, list):
                            raw_ids = []

                        # Résoudre les file_ids en chemins et séparer image/docs
                        image_path, file_paths = server.consume_upload_ids(raw_ids)

                        if not user_text and not image_path and not file_paths:
                            continue

                        # Créer le message utilisateur (avec pièces jointes éventuelles)
                        user_msg = RelayMessage(
                            text=user_text,
                            is_user=True,
                            source="relay",
                            image_path=image_path,
                            file_paths=file_paths,
                        )

                        # Armer le bridge AVANT d'envoyer au GUI : la réponse
                        # sera associée à ce message_id et mise en cache si
                        # le WS d'origine meurt pendant la génération.
                        server.bridge.arm_response(user_msg.message_id)

                        # Notifier le GUI qu'un message arrive du mobile.
                        # Le GUI va traiter le message en streaming (comme un
                        # message local) et soumettre la réponse via le bridge.
                        server.bridge.send_to_gui(user_msg)

                        # Envoyer un accusé de réception
                        await websocket.send_text(json.dumps({
                            "type": "ack",
                            "message_id": user_msg.message_id,
                        }))

                        # Attendre que le GUI produise la réponse (streaming).
                        # Retourne (texte, message_id). On ignore l'id car il
                        # correspond forcément à user_msg.message_id ici.
                        response_text, _ = await server.bridge.wait_for_ai_response(
                            timeout=server.response_timeout
                        )

                        # Envoyer la réponse au mobile d'origine (si encore
                        # connecté). En parallèle, le broadcast_response
                        # enregistré via on_response() aura déjà poussé la
                        # réponse à tous les autres WS actifs.
                        try:
                            await websocket.send_text(json.dumps({
                                "type": "response",
                                "message": response_text,
                                "message_id": user_msg.message_id,
                                "timestamp": datetime.now().isoformat(),
                            }))
                        except Exception as send_err:
                            # WS d'origine mort : la réponse reste en cache
                            # côté bridge, le mobile la récupérera via
                            # /api/pending ou au prochain handshake "resume".
                            # Sortir de la boucle proprement pour éviter que
                            # le receive_text() suivant ne relance une
                            # exception bruyante sur un WS déjà fermé.
                            logger.info(
                                "WS d'origine indisponible (%s), réponse en cache id=%s",
                                send_err, user_msg.message_id,
                            )
                            break

                    elif msg_data.get("type") == "resume":
                        # Mobile reconnecté : il demande si une réponse est
                        # disponible pour son dernier message_id envoyé.
                        # Deux cas possibles :
                        #   - la réponse est déjà complète → type "response"
                        #   - la génération est encore en cours → type "chunk"
                        #     (état courant du stream) ; les chunks suivants
                        #     arriveront ensuite via le broadcast.
                        last_id = msg_data.get("last_message_id", "") or ""
                        pending = server.bridge.consume_pending_response(last_id)
                        if pending is not None:
                            await websocket.send_text(json.dumps({
                                "type": "response",
                                "message": pending,
                                "message_id": last_id,
                                "timestamp": datetime.now().isoformat(),
                                "resumed": True,
                            }))
                        else:
                            partial = server.bridge.get_active_stream(last_id)
                            if partial is not None:
                                await websocket.send_text(json.dumps({
                                    "type": "chunk",
                                    "message_id": last_id,
                                    "text": partial,
                                    "timestamp": datetime.now().isoformat(),
                                    "resumed": True,
                                }))
                            else:
                                await websocket.send_text(json.dumps({
                                    "type": "resume_empty",
                                    "message_id": last_id,
                                }))

                    elif msg_data.get("type") == "ping":
                        await websocket.send_text(json.dumps({"type": "pong"}))

            except WebSocketDisconnect:
                logger.info("Client Relay déconnecté")
            except Exception as e:
                # Quand iOS/Safari ferme brutalement le WS (ex. onglet mis
                # en arrière-plan puis tué), les appels suivants sur le
                # websocket lèvent une RuntimeError « not connected »/« not
                # accepted » au lieu d'un WebSocketDisconnect propre.
                # Rétrograder en INFO pour éviter de polluer les logs.
                msg = str(e)
                if (
                    "not connected" in msg
                    or "close message has been sent" in msg
                    or "accept" in msg.lower()
                ):
                    logger.info("Client Relay déconnecté (brutal): %s", msg)
                else:
                    logger.error("Erreur WebSocket Relay: %s", e)
            finally:
                if websocket in server.ws_clients:
                    server.ws_clients.remove(websocket)
                server.bridge.connected_clients = len(server.ws_clients)

    # ------------------------------------------------------------------
    # Cycle de vie du serveur
    # ------------------------------------------------------------------

    def _broadcast_chunk(self, message_id: str, text: str) -> None:
        """Callback déclenché par le bridge à chaque chunk de streaming.

        Broadcaste l'état courant de la génération à tous les WebSockets
        connectés, pour que le mobile voie la réponse se construire en
        direct comme sur le GUI desktop. Le texte est cumulatif.
        """
        if not self._loop or not self._ws_clients:
            return
        payload = json.dumps({
            "type": "chunk",
            "message_id": message_id,
            "text": text,
            "timestamp": datetime.now().isoformat(),
        })

        async def _push():
            dead: List[WebSocket] = []
            for ws in list(self._ws_clients):
                try:
                    await ws.send_text(payload)
                except Exception:
                    dead.append(ws)
            for ws in dead:
                if ws in self._ws_clients:
                    self._ws_clients.remove(ws)
            if dead:
                self._bridge.connected_clients = len(self._ws_clients)

        try:
            asyncio.run_coroutine_threadsafe(_push(), self._loop)
        except Exception as e:
            logger.debug("Broadcast chunk WS impossible : %s", e)

    def _broadcast_response(self, message_id: str, text: str) -> None:
        """Callback déclenché par le bridge à chaque réponse IA soumise.

        Broadcaste la réponse à tous les WebSockets actuellement connectés,
        ce qui permet à un mobile reconnecté pendant la génération de
        recevoir la réponse même si son WS d'origine est mort.
        """
        if not self._loop or not self._ws_clients:
            return
        payload = json.dumps({
            "type": "response",
            "message": text,
            "message_id": message_id,
            "timestamp": datetime.now().isoformat(),
            "broadcast": True,
        })

        async def _push():
            dead: List[WebSocket] = []
            for ws in list(self._ws_clients):
                try:
                    await ws.send_text(payload)
                except Exception:
                    # WS mort (iOS a fermé brutalement) : marquer pour
                    # retrait immédiat afin que le compteur de clients
                    # connectés redevienne cohérent sans attendre que le
                    # handler receive_text() échoue à son tour.
                    dead.append(ws)
            for ws in dead:
                if ws in self._ws_clients:
                    self._ws_clients.remove(ws)
            if dead:
                self._bridge.connected_clients = len(self._ws_clients)

        try:
            asyncio.run_coroutine_threadsafe(_push(), self._loop)
        except Exception as e:
            logger.debug("Broadcast WS impossible : %s", e)

    def start(self, start_tunnel: bool = True) -> None:
        """Démarre le serveur Relay et optionnellement le tunnel."""
        if not _FASTAPI_AVAILABLE:
            raise RuntimeError("FastAPI/uvicorn non installé.")

        if self._running:
            logger.warning("Relay déjà en cours d'exécution.")
            return

        self._bridge.active = True
        # Enregistrer les callbacks de broadcast (une seule fois par start).
        self._bridge.remove_response_callback(self._broadcast_response)
        self._bridge.on_response(self._broadcast_response)
        self._bridge.remove_chunk_callback(self._broadcast_chunk)
        self._bridge.on_chunk(self._broadcast_chunk)

        # Démarrer le serveur uvicorn
        config = uvicorn.Config(
            app=self._app,
            host=self._host,
            port=self._port,
            log_level="warning",
            access_log=False,
        )
        self._uvicorn_server = uvicorn.Server(config)

        self._server_thread = threading.Thread(
            target=self._run_server,
            name="relay-server",
            daemon=True,
        )
        self._server_thread.start()
        self._running = True
        self._start_time = time.time()

        logger.info("Relay démarré sur http://%s:%s", self._host, self._port)

        # Démarrer le tunnel cloudflared
        if start_tunnel:
            self._start_tunnel()

    def stop(self) -> None:
        """Arrête le serveur Relay et le tunnel."""
        if not self._running:
            return

        logger.info("Arrêt du Relay...")
        self._bridge.active = False

        # Arrêter le tunnel
        self._stop_tunnel()

        # Arrêter uvicorn
        if self._uvicorn_server:
            self._uvicorn_server.should_exit = True

        if self._server_thread and self._server_thread.is_alive():
            self._server_thread.join(timeout=5.0)

        # Fermer les WebSocket clients
        self._ws_clients.clear()

        self._running = False
        self._start_time = None
        logger.info("Relay arrêté.")

    def is_running(self) -> bool:
        """Indique si le serveur Relay est actuellement en cours d'exécution."""
        if not self._running:
            return False
        if self._server_thread and not self._server_thread.is_alive():
            self._running = False
            return False
        return True

    def _run_server(self) -> None:
        try:
            # Créer explicitement la boucle pour pouvoir la capturer avant
            # que uvicorn ne la bloque. Équivalent à asyncio.run() mais
            # nous laisse accéder à la référence (utilisée pour broadcaster
            # des messages WS depuis le thread GUI).
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            self._loop = loop
            try:
                loop.run_until_complete(self._uvicorn_server.serve())
            finally:
                self._loop = None
                loop.close()
        except Exception as e:
            logger.error("Erreur fatale Relay: %s", e)
            self._running = False

    # ------------------------------------------------------------------
    # Tunnels publics (multi-provider, en parallèle)
    # ------------------------------------------------------------------

    def _start_tunnel(self) -> None:
        """Démarre tous les providers de tunnel configurés en parallèle.

        Chaque provider tourne dans son propre sous-processus et publie
        son URL via _set_tunnel_url(). Les providers indisponibles sont
        ignorés silencieusement (log warning) — au moins un autre devrait
        fonctionner.
        """
        starters = {
            "cloudflared": self._start_cloudflared,
            "serveo": self._start_serveo,
            "localhost.run": self._start_localhost_run,
        }
        for name in self._tunnel_provider_names:
            starter = starters.get(name)
            if not starter:
                logger.warning("Provider de tunnel inconnu : %s", name)
                continue
            try:
                starter()
            except Exception as e:
                logger.error("Démarrage tunnel %s impossible : %s", name, e)

    def _set_tunnel_url(self, provider: str, url: str) -> None:
        """Enregistre l'URL publique d'un provider et la log."""
        with self._tunnel_urls_lock:
            self._tunnel_urls[provider] = url
        logger.info("Tunnel %s actif : %s", provider, url)

    def _spawn_tunnel(
        self,
        provider: str,
        cmd: List[str],
        url_pattern: str,
        env: Optional[Dict[str, str]] = None,
    ) -> None:
        """Lance un sous-processus de tunnel et parse son URL en arrière-plan.

        Le sous-processus est arrêté automatiquement par _stop_tunnel().
        L'URL est extraite de stdout+stderr via la regex `url_pattern`.
        """
        try:
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                env=env,
                creationflags=(
                    subprocess.CREATE_NO_WINDOW
                    if sys.platform == "win32"
                    else 0
                ),
            )
        except Exception as e:
            logger.error("Spawn tunnel %s échoué : %s", provider, e)
            return

        self._tunnel_processes[provider] = proc

        def _reader():
            compiled = re.compile(url_pattern)
            try:
                if proc.stdout is None:
                    return
                for line in proc.stdout:
                    match = compiled.search(line)
                    if match:
                        self._set_tunnel_url(provider, match.group(0))
                        # Continuer à drainer pour éviter de bloquer le pipe
            except Exception as e:
                logger.debug("Lecture sortie tunnel %s : %s", provider, e)

        threading.Thread(
            target=_reader,
            name=f"tunnel-reader-{provider}",
            daemon=True,
        ).start()

    def _start_cloudflared(self) -> None:
        """Démarre un tunnel cloudflared (trycloudflare.com)."""
        cf_path = shutil.which("cloudflared")
        if not cf_path:
            tools_path = Path(__file__).parent.parent / "tools" / "cloudflared.exe"
            if tools_path.exists():
                cf_path = str(tools_path)
        if not cf_path:
            cf_path = self._download_cloudflared()
        if not cf_path:
            logger.warning(
                "cloudflared introuvable. Tunnel cloudflared désactivé."
            )
            return

        self._spawn_tunnel(
            provider="cloudflared",
            cmd=[cf_path, "tunnel", "--url", f"http://localhost:{self._port}"],
            url_pattern=r"https://[a-z0-9-]+\.trycloudflare\.com",
        )
        logger.info("Tunnel cloudflared en cours de démarrage...")

    def _start_serveo(self) -> None:
        """Démarre un tunnel serveo.net via SSH (port forwarding distant).

        Nécessite uniquement le client SSH (intégré sur Win10+/macOS/Linux).
        Le tunnel reste anonyme — pas de compte requis.
        """
        ssh = shutil.which("ssh")
        if not ssh:
            logger.warning("ssh introuvable. Tunnel serveo désactivé.")
            return

        # -o options pour : pas de prompt host key, garder la connexion vive,
        # pas de tty (on ne lit que la bannière). Serveo annonce l'URL HTTPS
        # juste après l'auth.
        cmd = [
            ssh,
            "-o", "StrictHostKeyChecking=no",
            "-o", f"UserKnownHostsFile={os.devnull}",
            "-o", "ServerAliveInterval=30",
            "-o", "ExitOnForwardFailure=yes",
            "-T",  # pas de tty
            "-R", f"80:localhost:{self._port}",
            "serveo.net",
        ]
        self._spawn_tunnel(
            provider="serveo",
            cmd=cmd,
            url_pattern=r"https://[a-z0-9-]+\.serveo\.net",
        )
        logger.info("Tunnel serveo en cours de démarrage...")

    def _start_localhost_run(self) -> None:
        """Démarre un tunnel localhost.run via SSH (anonyme, *.lhr.life)."""
        ssh = shutil.which("ssh")
        if not ssh:
            logger.warning("ssh introuvable. Tunnel localhost.run désactivé.")
            return

        cmd = [
            ssh,
            "-o", "StrictHostKeyChecking=no",
            "-o", f"UserKnownHostsFile={os.devnull}",
            "-o", "ServerAliveInterval=30",
            "-o", "ExitOnForwardFailure=yes",
            "-T",
            "-R", f"80:localhost:{self._port}",
            "nokey@localhost.run",
        ]
        self._spawn_tunnel(
            provider="localhost.run",
            cmd=cmd,
            # localhost.run attribue généralement *.lhr.life (legacy: *.localhost.run)
            url_pattern=r"https://[a-z0-9-]+\.(?:lhr\.life|localhost\.run)",
        )
        logger.info("Tunnel localhost.run en cours de démarrage...")

    def _stop_tunnel(self) -> None:
        """Arrête tous les tunnels actifs."""
        for provider, proc in list(self._tunnel_processes.items()):
            try:
                proc.terminate()
                proc.wait(timeout=5)
            except Exception:
                try:
                    proc.kill()
                except Exception:
                    pass
        self._tunnel_processes.clear()
        with self._tunnel_urls_lock:
            self._tunnel_urls.clear()

    # ------------------------------------------------------------------
    # Téléchargement automatique de cloudflared
    # ------------------------------------------------------------------

    def _download_cloudflared(self) -> Optional[str]:
        """
        Télécharge cloudflared automatiquement dans tools/.

        Returns:
            Chemin vers l'exécutable ou None en cas d'échec.
        """
        tools_dir = Path(__file__).parent.parent / "tools"
        tools_dir.mkdir(exist_ok=True)

        if sys.platform == "win32":
            filename = "cloudflared.exe"
            url = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe"
        elif sys.platform == "darwin":
            filename = "cloudflared"
            url = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-darwin-amd64.tgz"
        else:
            filename = "cloudflared"
            url = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64"

        dest = tools_dir / filename

        try:
            logger.info("Téléchargement de cloudflared depuis GitHub...")
            print("📥 Téléchargement de cloudflared (première utilisation)...")

            resp = requests.get(url, stream=True, timeout=60)
            resp.raise_for_status()

            with open(dest, "wb") as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    f.write(chunk)

            # Rendre exécutable sur Unix
            if sys.platform != "win32":
                os.chmod(dest, 0o755)

            logger.info("cloudflared téléchargé avec succès dans %s", dest)
            print(f"✅ cloudflared installé dans {dest}")
            return str(dest)

        except Exception as e:
            logger.error("Échec du téléchargement de cloudflared: %s", e)
            print(f"⚠️ Impossible de télécharger cloudflared: {e}")
            # Nettoyer le fichier partiel
            if dest.exists():
                dest.unlink()
            return None

    # ------------------------------------------------------------------
    # QR Code
    # ------------------------------------------------------------------

    def generate_qr_code(self) -> Optional[str]:
        """
        Génère un QR code SVG de l'URL Relay (avec token).

        Returns:
            Chaîne SVG du QR code ou None si non disponible.
        """
        url = self.relay_url
        if not url or not _QR_AVAILABLE:
            return None

        try:
            qr = qrcode.QRCode(version=1, box_size=10, border=2)
            qr.add_data(url)
            qr.make(fit=True)
            img = qr.make_image(
                image_factory=qrcode.image.svg.SvgPathImage,
                fill_color="#ff6b47",
                back_color="#0f0f0f",
            )
            return img.to_string(encoding="unicode")
        except Exception as e:
            logger.error("Erreur génération QR: %s", e)
            return None


# ===========================================================================
# Fonctions utilitaires
# ===========================================================================


def _get_login_page() -> str:
    """Retourne la page HTML de login."""
    return """<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
<title>My_AI Relay</title>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    background: #0f0f0f; color: #fff;
    display: flex; align-items: center; justify-content: center;
    min-height: 100dvh;
  }
  .login-card {
    background: #1a1a1a; border-radius: 20px;
    padding: 40px 32px; width: 90%; max-width: 380px;
    text-align: center; border: 1px solid #2d2d2d;
  }
  .logo { font-size: 48px; margin-bottom: 8px; }
  h1 { font-size: 22px; font-weight: 600; margin-bottom: 4px; }
  .subtitle { color: #9ca3af; font-size: 14px; margin-bottom: 32px; }
  input {
    width: 100%; padding: 14px 16px; background: #0f0f0f;
    border: 1px solid #374151; border-radius: 12px; color: #fff;
    font-size: 16px; outline: none; margin-bottom: 16px;
    -webkit-appearance: none;
  }
  input:focus { border-color: #ff6b47; }
  button {
    width: 100%; padding: 14px; background: #ff6b47;
    border: none; border-radius: 12px; color: #fff;
    font-size: 16px; font-weight: 600; cursor: pointer;
  }
  button:active { background: #ff5730; }
  .error { color: #ef4444; font-size: 13px; margin-bottom: 12px; display: none; }
</style>
</head>
<body>
<div class="login-card">
  <div class="logo">&#x1F916;</div>
  <h1>My_AI Relay</h1>
  <p class="subtitle">Entrez le mot de passe pour accéder à votre IA</p>
  <div class="error" id="error">Mot de passe incorrect</div>
  <input type="password" id="pwd" placeholder="Mot de passe ou token" autocomplete="off" autofocus>
  <button onclick="login()">Se connecter</button>
</div>
<script>
document.getElementById('pwd').addEventListener('keydown', e => {
  if (e.key === 'Enter') login();
});
async function login() {
  const pwd = document.getElementById('pwd').value.trim();
  if (!pwd) return;
  try {
    const r = await fetch('/auth', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({password: pwd})
    });
    if (r.ok) {
      const d = await r.json();
      window.location.href = '/?token=' + d.token;
    } else {
      document.getElementById('error').style.display = 'block';
    }
  } catch(e) {
    document.getElementById('error').textContent = 'Erreur de connexion';
    document.getElementById('error').style.display = 'block';
  }
}
</script>
</body>
</html>"""
