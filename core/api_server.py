"""
Serveur API REST local pour My_AI v7.1.0

Expose les capacités de l'assistant IA via des endpoints HTTP sur localhost.
Utilise FastAPI avec uvicorn en thread daemon pour un fonctionnement
non-bloquant vis-à-vis de l'interface Tkinter principale.
"""

import asyncio
import threading
import time
from typing import Any, Dict, List, Optional

import requests as http_requests

from core.config import get_config
from memory.vector_memory import VectorMemory
from utils.logger import setup_logger

# ---------------------------------------------------------------------------
# Gestion gracieuse de l'absence de FastAPI / uvicorn
# ---------------------------------------------------------------------------

try:
    import uvicorn
    from fastapi import FastAPI, HTTPException
    from fastapi.middleware.cors import CORSMiddleware
    from pydantic import BaseModel, Field

    _FASTAPI_AVAILABLE = True
except ImportError:
    _FASTAPI_AVAILABLE = False

logger = setup_logger("APIServer")


# ===========================================================================
# Schémas Pydantic pour la validation des requêtes
# ===========================================================================

if _FASTAPI_AVAILABLE:

    class ChatRequest(BaseModel):
        """Schéma de la requête pour l'endpoint /api/chat."""

        message: str = Field(
            ...,
            min_length=1,
            max_length=50_000,
            description="Message envoyé par l'utilisateur",
        )
        system_prompt: Optional[str] = Field(
            default=None,
            max_length=10_000,
            description="Prompt système optionnel pour cadrer la réponse",
        )

    class SwitchModelRequest(BaseModel):
        """Schéma de la requête pour l'endpoint /api/models/switch."""

        model: str = Field(
            ...,
            min_length=1,
            max_length=200,
            description="Nom du modèle Ollama à activer",
        )


# ===========================================================================
# Classe principale du serveur API
# ===========================================================================


class APIServer:
    """
    Serveur API REST local exposant les fonctionnalités de My_AI.

    Le serveur tourne dans un thread daemon afin de ne pas bloquer
    l'application principale (CLI / GUI Tkinter). Il partage l'instance
    du moteur IA (ai_engine) avec le reste de l'application.
    """

    _APP_VERSION = "7.1.0"

    def __init__(
        self,
        ai_engine: Optional[Any] = None,
        config: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Initialise le serveur API.

        Args:
            ai_engine: Instance partagée du moteur IA (AIEngine).
                       Peut être None au démarrage et injectée plus tard.
            config: Configuration personnalisée pour la section ``api``.
                    Si None, la configuration est lue depuis config.yaml
                    via ``get_config()``.
        """
        # Charger la configuration depuis config.yaml si non fournie
        if config is None:
            cfg = get_config()
            config = cfg.get_section("api") or {}

        self._ai_engine = ai_engine
        self._host: str = config.get("host", "127.0.0.1")
        self._port: int = int(config.get("port", 8000))
        self._cors_origins: List[str] = config.get(
            "cors_origins",
            ["http://localhost:*"],
        )

        self._server_thread: Optional[threading.Thread] = None
        self._uvicorn_server: Optional[Any] = None
        self._running: bool = False
        self._start_time: Optional[float] = None

        if not _FASTAPI_AVAILABLE:
            logger.warning(
                "FastAPI ou uvicorn non installé. "
                "Le serveur API ne sera pas disponible. "
                "Installez-les avec : pip install fastapi uvicorn"
            )
            return

        self._app = self._create_app()

    # ------------------------------------------------------------------
    # Propriétés
    # ------------------------------------------------------------------

    @property
    def ai_engine(self) -> Optional[Any]:
        """Retourne l'instance du moteur IA."""
        return self._ai_engine

    @ai_engine.setter
    def ai_engine(self, engine: Any) -> None:
        """Permet d'injecter le moteur IA après l'initialisation."""
        self._ai_engine = engine

    # ------------------------------------------------------------------
    # Construction de l'application FastAPI
    # ------------------------------------------------------------------

    def _create_app(self) -> "FastAPI":
        """
        Construit l'application FastAPI avec tous les endpoints et middlewares.

        Returns:
            Instance FastAPI entièrement configurée.
        """
        app = FastAPI(
            title="My_AI API",
            description="API REST locale pour l'assistant IA personnel My_AI",
            version=self._APP_VERSION,
            docs_url="/docs",
            redoc_url="/redoc",
        )

        # --- Middleware CORS pour le développement local -------------------
        origins = list(self._cors_origins)
        # Ajouter des origines courantes si absentes
        for extra in [
            "http://127.0.0.1:*",
            "http://localhost:3000",
            "http://localhost:5173",
            "http://localhost:8080",
        ]:
            if extra not in origins:
                origins.append(extra)

        app.add_middleware(
            CORSMiddleware,
            allow_origins=origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        # --- Enregistrement des routes ------------------------------------
        self._register_routes(app)

        return app

    def _register_routes(self, app: "FastAPI") -> None:
        """
        Enregistre tous les endpoints sur l'application FastAPI.

        Args:
            app: Instance FastAPI cible.
        """

        # --- Utilitaire : vérifier la disponibilité du moteur IA ----------

        def _require_engine() -> Any:
            """Lève une HTTPException 503 si le moteur IA n'est pas prêt."""
            if self._ai_engine is None:
                raise HTTPException(
                    status_code=503,
                    detail="Le moteur IA n'est pas encore initialisé.",
                )
            return self._ai_engine

        # =================================================================
        # GET /api/health — Vérification de santé du serveur
        # =================================================================

        @app.get("/api/health", tags=["Système"])
        async def health_check() -> Dict[str, Any]:
            """Vérifie que le serveur est opérationnel et renvoie des infos de base."""
            uptime = round(time.time() - self._start_time, 2) if self._start_time else 0.0
            return {
                "status": "ok",
                "version": self._APP_VERSION,
                "engine_ready": self._ai_engine is not None,
                "uptime_seconds": uptime,
            }

        # =================================================================
        # POST /api/chat — Envoi d'un message à l'IA
        # =================================================================

        @app.post("/api/chat", tags=["Conversation"])
        async def chat(request: ChatRequest) -> Dict[str, Any]:
            """
            Envoie un message à l'assistant IA et retourne la réponse.

            Le moteur IA utilise le même pipeline que la CLI/GUI
            (historique, orchestration, outils MCP, etc.).
            Un prompt système optionnel peut être fourni pour cadrer
            le comportement de l'IA sur cette requête.
            """
            engine = _require_engine()

            try:
                model_name = _resolve_model_name(engine)

                # Construire le contexte avec le prompt système si fourni
                context: Dict[str, Any] = {}
                if request.system_prompt:
                    context["system_prompt"] = request.system_prompt

                response_text = engine.process_text(
                    request.message,
                    context=context if context else None,
                )

                return {
                    "response": response_text,
                    "model": model_name,
                }
            except Exception as exc:
                logger.error("Erreur lors du traitement du message : %s", exc)
                raise HTTPException(
                    status_code=500,
                    detail=f"Erreur de traitement : {exc}",
                ) from exc

        # =================================================================
        # GET /api/models — Liste des modèles Ollama disponibles
        # =================================================================

        @app.get("/api/models", tags=["Modèles"])
        async def list_models() -> Dict[str, Any]:
            """
            Interroge le serveur Ollama local pour lister les modèles installés.
            """
            engine = _require_engine()

            try:
                ollama_base = _resolve_ollama_base_url(engine)
                resp = http_requests.get(f"{ollama_base}/api/tags", timeout=5)
                resp.raise_for_status()
                data = resp.json()

                models = [
                    {
                        "name": m.get("name", ""),
                        "size": m.get("size", 0),
                        "modified_at": m.get("modified_at", ""),
                    }
                    for m in data.get("models", [])
                ]

                return {
                    "models": models,
                    "current_model": _resolve_model_name(engine),
                    "count": len(models),
                }
            except Exception as exc:
                logger.error("Erreur lors de la récupération des modèles : %s", exc)
                raise HTTPException(
                    status_code=502,
                    detail=f"Impossible de contacter Ollama : {exc}",
                ) from exc

        # =================================================================
        # POST /api/models/switch — Changement de modèle actif
        # =================================================================

        @app.post("/api/models/switch", tags=["Modèles"])
        async def switch_model(request: SwitchModelRequest) -> Dict[str, Any]:
            """
            Change le modèle Ollama actif utilisé par le moteur IA.
            Vérifie l'existence du modèle avant de basculer.
            """
            engine = _require_engine()

            try:
                llm = _resolve_local_llm(engine)
                if llm is None:
                    raise HTTPException(
                        status_code=500,
                        detail="Aucune instance LLM locale disponible.",
                    )

                # Vérifier que le modèle demandé existe dans Ollama
                check_fn = getattr(llm, "check_model_exists", None) or getattr(llm, "_check_model_exists", None)
                if check_fn and not check_fn(request.model):
                    raise HTTPException(
                        status_code=404,
                        detail=f"Modèle '{request.model}' non trouvé dans Ollama.",
                    )

                previous_model = getattr(llm, "model", "inconnu")
                llm.model = request.model

                logger.info(
                    "Modèle changé : %s -> %s", previous_model, request.model
                )
                return {
                    "success": True,
                    "previous_model": previous_model,
                    "current_model": request.model,
                }
            except HTTPException:
                raise
            except Exception as exc:
                logger.error("Erreur lors du changement de modèle : %s", exc)
                raise HTTPException(
                    status_code=500,
                    detail=f"Erreur changement de modèle : {exc}",
                ) from exc

        # =================================================================
        # GET /api/conversations — Historique de conversation
        # =================================================================

        @app.get("/api/conversations", tags=["Conversation"])
        async def get_conversations() -> Dict[str, Any]:
            """Retourne l'historique complet de la conversation en cours."""
            engine = _require_engine()

            try:
                history = engine.get_conversation_history()
                return {
                    "history": history,
                    "count": len(history),
                }
            except Exception as exc:
                logger.error(
                    "Erreur lors de la récupération de l'historique : %s", exc
                )
                raise HTTPException(
                    status_code=500,
                    detail=f"Erreur historique : {exc}",
                ) from exc

        # =================================================================
        # DELETE /api/conversations — Effacement de l'historique
        # =================================================================

        @app.delete("/api/conversations", tags=["Conversation"])
        async def clear_conversations() -> Dict[str, str]:
            """Efface l'intégralité de l'historique de conversation."""
            engine = _require_engine()

            try:
                engine.clear_conversation()
                logger.info("Historique de conversation effacé via l'API.")
                return {
                    "status": "ok",
                    "message": "Historique effacé avec succès.",
                }
            except Exception as exc:
                logger.error(
                    "Erreur lors de l'effacement de l'historique : %s", exc
                )
                raise HTTPException(
                    status_code=500,
                    detail=f"Erreur effacement : {exc}",
                ) from exc

        # =================================================================
        # GET /api/stats — Statistiques système
        # =================================================================

        @app.get("/api/stats", tags=["Système"])
        async def get_stats() -> Dict[str, Any]:
            """
            Retourne les statistiques du système : utilisation du contexte,
            informations sur le modèle actif, uptime et état de la mémoire.
            """
            engine = _require_engine()

            # Informations sur le modèle actif
            model_name = _resolve_model_name(engine)

            # Statut du moteur IA (si disponible)
            try:
                engine_status = engine.get_status()
            except Exception:
                engine_status = {"error": "Impossible de récupérer le statut du moteur."}

            # Informations sur le contexte
            context_info = _get_context_info(engine)

            # Informations sur la mémoire vectorielle
            memory_info = _get_memory_info()

            # Uptime du serveur API
            uptime = round(time.time() - self._start_time, 2) if self._start_time else 0.0

            return {
                "version": self._APP_VERSION,
                "uptime_seconds": uptime,
                "model": model_name,
                "context": context_info,
                "engine": engine_status,
                "memory": memory_info,
            }

    # ------------------------------------------------------------------
    # Gestion du cycle de vie du serveur
    # ------------------------------------------------------------------

    def start(self) -> None:
        """
        Démarre le serveur uvicorn dans un thread daemon.

        Le thread daemon est automatiquement arrêté à la fin du processus
        principal, mais la méthode ``stop()`` permet un arrêt propre et
        explicite.

        Raises:
            RuntimeError: Si FastAPI ou uvicorn n'est pas installé.
        """
        if not _FASTAPI_AVAILABLE:
            logger.error(
                "Impossible de démarrer le serveur API : "
                "FastAPI ou uvicorn non installé."
            )
            raise RuntimeError(
                "FastAPI ou uvicorn non installé. "
                "Installez-les avec : pip install fastapi uvicorn"
            )

        if self._running:
            logger.warning("Le serveur API est déjà en cours d'exécution.")
            return

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
            name="api-server",
            daemon=True,
        )
        self._server_thread.start()
        self._running = True
        self._start_time = time.time()

        logger.info(
            "Serveur API démarré sur http://%s:%s", self._host, self._port
        )

    def stop(self) -> None:
        """
        Arrête proprement le serveur uvicorn et attend la fin du thread.
        """
        if not self._running or self._uvicorn_server is None:
            logger.debug("Le serveur API n'est pas en cours d'exécution.")
            return

        logger.info("Arrêt du serveur API en cours...")
        self._uvicorn_server.should_exit = True

        if self._server_thread is not None and self._server_thread.is_alive():
            self._server_thread.join(timeout=5.0)

        self._running = False
        self._start_time = None
        logger.info("Serveur API arrêté.")

    def is_running(self) -> bool:
        """
        Indique si le serveur API est actuellement en cours d'exécution.

        Returns:
            True si le serveur tourne, False sinon.
        """
        if not self._running:
            return False

        # Vérification supplémentaire : le thread est-il encore vivant ?
        if self._server_thread is not None and not self._server_thread.is_alive():
            self._running = False
            return False

        return True

    # ------------------------------------------------------------------
    # Méthodes internes
    # ------------------------------------------------------------------

    def _run_server(self) -> None:
        """
        Point d'entrée du thread daemon qui exécute la boucle événementielle
        uvicorn. Toute exception fatale est capturée pour éviter un crash
        silencieux du thread.
        """
        try:
            asyncio.run(self._uvicorn_server.serve())
        except Exception as exc:
            logger.error("Erreur fatale du serveur API : %s", exc)
            self._running = False


# ===========================================================================
# Fonctions utilitaires (hors classe, utilisées par les routes)
# ===========================================================================


def _resolve_model_name(engine: Any) -> str:
    """
    Détermine le nom du modèle LLM actuellement actif.

    Parcourt les différentes couches de l'objet engine pour trouver
    le nom du modèle : local_ai.local_llm.model -> local_ai.model -> config.

    Args:
        engine: Instance du moteur IA.

    Returns:
        Nom du modèle actif ou ``'inconnu'``.
    """
    try:
        # Chemin principal : engine.local_ai.local_llm.model
        if hasattr(engine, "local_ai"):
            llm = getattr(engine.local_ai, "local_llm", None)
            if llm is not None and hasattr(llm, "model"):
                return str(llm.model)
            # Fallback : engine.local_ai.model
            if hasattr(engine.local_ai, "model"):
                return str(engine.local_ai.model)
    except Exception:
        pass
    return "inconnu"


def _resolve_local_llm(engine: Any) -> Optional[Any]:
    """
    Récupère l'instance LocalLLM sous-jacente depuis le moteur IA.

    Args:
        engine: Instance du moteur IA.

    Returns:
        Instance LocalLLM ou None si indisponible.
    """
    try:
        if hasattr(engine, "local_ai"):
            llm = getattr(engine.local_ai, "local_llm", None)
            if llm is not None:
                return llm
    except Exception:
        pass
    return None


def _resolve_ollama_base_url(engine: Any) -> str:
    """
    Détermine l'URL de base du serveur Ollama depuis la configuration.

    Args:
        engine: Instance du moteur IA.

    Returns:
        URL de base Ollama (sans le chemin ``/api/*``).
    """
    default_url = "http://localhost:11434"
    try:
        llm = _resolve_local_llm(engine)
        if llm is not None and hasattr(llm, "ollama_url"):
            # ollama_url est typiquement 'http://localhost:11434/api/generate'
            return llm.ollama_url.replace("/api/generate", "")
    except Exception:
        pass
    return default_url


def _get_context_info(engine: Any) -> Dict[str, Any]:
    """
    Collecte les informations sur l'utilisation du contexte par le moteur IA.

    Tente d'extraire la taille courante du contexte, la limite maximale
    et le pourcentage d'utilisation depuis les attributs du moteur.

    Args:
        engine: Instance du moteur IA.

    Returns:
        Dictionnaire avec les statistiques du contexte.
    """
    info: Dict[str, Any] = {}
    try:
        # Taille maximale du contexte depuis la configuration
        cfg = get_config()
        max_tokens = cfg.get("ai.max_tokens", 0)
        info["max_tokens"] = max_tokens

        # Historique de conversation en cours
        history = engine.get_conversation_history() if hasattr(engine, "get_conversation_history") else []
        info["conversation_turns"] = len(history)

        # Estimation grossière de l'utilisation en tokens (4 caractères ≈ 1 token)
        total_chars = sum(
            len(str(entry.get("user", ""))) + len(str(entry.get("assistant", "")))
            for entry in history
            if isinstance(entry, dict)
        )
        estimated_tokens = total_chars // 4
        info["estimated_tokens_used"] = estimated_tokens

        if max_tokens > 0:
            info["usage_percent"] = round((estimated_tokens / max_tokens) * 100, 2)
        else:
            info["usage_percent"] = 0.0

    except Exception as exc:
        info["error"] = f"Impossible de récupérer les infos de contexte : {exc}"

    return info


def _get_memory_info() -> Dict[str, Any]:
    """
    Collecte les informations sur la mémoire vectorielle.

    Returns:
        Dictionnaire avec les statistiques de la mémoire vectorielle.
    """
    try:
        vm = VectorMemory()
        stats = vm.get_stats() if hasattr(vm, "get_stats") else {}
        return {"available": True, **stats}
    except Exception:
        return {"available": False}
