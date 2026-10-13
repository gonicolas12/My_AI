"""
Cycle de vie de l'appli desktop web

Le serveur local répond tout de suite : la fenêtre affiche l'écran de
chargement et l'étape en cours. Un fil enchaîne ensuite les étapes du lanceur,
dans l'ordre de launch_unified.py :

  1. téléchargement en arrière-plan du modèle des longs documents ;
  2. redémarrage d'Ollama avec les variables du placement ;
  3. assistant de premier lancement, si nécessaire ;
  4. recréation de my_ai si le Modelfile a changé ;
  5. placement du modèle (mesuré seulement après un changement).

Viennent ensuite le moteur, le chat, le Relay (relay.auto_start) et le
scheduler. Rien n'appelle Ollama avant la fin du placement : une requête
pendant la mesure la fausserait.
"""

import json
import os
import secrets
import threading
import time
from pathlib import Path
from typing import Any, Dict, Optional

from core.chat_service import ChatError, ChatService
from interfaces.desktop.events import EventBus
from interfaces.desktop.server import DesktopServer
from utils.logger import setup_logger

logger = setup_logger("DesktopApp")

PROJECT_ROOT = Path(__file__).resolve().parents[2]
# État local de l'interface (session courante, fenêtre, barre latérale), ignoré par git
STATE_FILE = PROJECT_ROOT / "data" / ".desktop_state.json"

OLLAMA_FAILED = "Ollama n'a pas pu démarrer — lancez l'application Ollama ou « ollama serve »"

# Port du serveur local en mode --dev : celui que vise le proxy de Vite
# (frontend/vite.config.ts, MY_AI_DESKTOP_PORT), pour lancer Vite et l'appli
# dans n'importe quel ordre
DEV_BACKEND_PORT = 5180

# État de l'interface retenu d'un lancement à l'autre, avec sa valeur par défaut
# (volet d'aperçu : 560 px, comme dans Tk)
UI_DEFAULTS: Dict[str, Any] = {"sidebar_open": False, "preview_width": 560}


class DesktopState:
    """Petit fichier d'état de l'interface (data/.desktop_state.json)."""

    def __init__(self, path: Path = STATE_FILE):
        self._path = path
        self._lock = threading.Lock()

    def read(self) -> Dict[str, Any]:
        """Contenu du fichier ({} s'il manque ou s'il est illisible)."""
        try:
            with open(self._path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            return data if isinstance(data, dict) else {}
        except (OSError, ValueError):
            return {}

    def get(self, key: str, default=None):
        """Valeur d'une clé."""
        return self.read().get(key, default)

    def set(self, key: str, value) -> None:
        """Enregistre une clé (écriture atomique)."""
        with self._lock:
            data = self.read()
            data[key] = value
            try:
                self._path.parent.mkdir(parents=True, exist_ok=True)
                tmp = self._path.with_suffix(".json.tmp")
                with open(tmp, "w", encoding="utf-8") as fh:
                    json.dump(data, fh, ensure_ascii=False, indent=2)
                os.replace(tmp, self._path)
            except OSError as exc:
                logger.warning("État de l'interface non enregistré : %s", exc)


def _config_flag(key: str, default=False):
    """Réglage de config.yaml (core.config), avec repli silencieux."""
    try:
        from core.config import get_config  # pylint: disable=import-outside-toplevel
        return get_config().get(key, default)
    except Exception:  # pylint: disable=broad-except
        return default


def _save_autoread(enabled: bool) -> None:
    """Lecture automatique enregistrée dans config.yaml, commentaires gardés."""
    from interfaces.onboarding import set_config_flag  # pylint: disable=import-outside-toplevel
    set_config_flag("ui.tts_autoread", bool(enabled))


class DesktopApp:
    """Appli desktop : serveur local, étapes de lancement, moteur et services."""

    def __init__(self, launcher, *, headless: bool = False, dev: bool = False,
                 port: int = 0, state: Optional[DesktopState] = None):
        """
        Args:
            launcher: module launch_unified (redémarrage d'Ollama, placement…)
            headless: sans fenêtre (tests, client WebSocket)
            dev: interface servie par Vite (rechargement à chaud)
            port: port du serveur local (0 : port libre)
            state: état local de l'interface (data/.desktop_state.json)
        """
        self._launcher = launcher
        self.headless = headless
        self.dev = dev
        self.token = secrets.token_urlsafe(32)
        self.bus = EventBus()
        self.state = state or DesktopState()

        self.config = None
        self.engine = None
        self.chat: Optional[ChatService] = None
        self.relay = None
        self.scheduler = None
        self._agent_service = None
        self._voice = None

        self._lock = threading.Lock()
        self._status: Dict[str, Any] = {
            "state": "starting", "step": "", "label": "Démarrage…", "detail": "",
            "error": None, "ollama": True, "placement": None,
        }
        self._relay_snapshot: Optional[Dict[str, Any]] = None
        self._relay_watch: Optional[threading.Thread] = None
        self._closing = False
        self._closed = threading.Event()

        self.server = DesktopServer(self, port=port)

    # ── Démarrage ───────────────────────────────────────────────────────────

    def start(self) -> str:
        """Démarre le serveur puis les étapes de lancement ; renvoie l'URL de la fenêtre."""
        self.server.start()
        threading.Thread(target=self._launch, name="desktop-launch", daemon=True).start()
        return self.url

    @property
    def url(self) -> str:
        """Adresse de la fenêtre, jeton dans le fragment (jamais envoyé au serveur)."""
        return f"http://127.0.0.1:{self.server.port}/#token={self.token}"

    def status(self) -> Dict[str, Any]:
        """Étape de lancement, ou état du moteur."""
        with self._lock:
            return dict(self._status)

    def ui_state(self) -> Dict[str, Any]:
        """État de l'interface retenu d'un lancement à l'autre (barre latérale…)."""
        saved = self.state.get("ui")
        saved = saved if isinstance(saved, dict) else {}
        return {key: type(default)(saved.get(key, default))
                for key, default in UI_DEFAULTS.items()}

    def set_ui_state(self, values: Dict[str, Any]) -> Dict[str, Any]:
        """Retient les valeurs connues de l'état de l'interface ; renvoie l'état complet."""
        state = self.ui_state()
        state.update({key: value for key, value in values.items() if key in UI_DEFAULTS})
        self.state.set("ui", state)
        return self.ui_state()

    def _set_status(self, **fields) -> None:
        with self._lock:
            self._status.update(fields)
            status = dict(self._status)
        self.bus.publish("engine.status", status)

    def _step(self, step: str, label: str) -> None:
        logger.info("Lancement : %s", label)
        self._set_status(step=step, label=label, detail="")

    def _launch(self) -> None:
        """Étapes du lanceur, puis moteur et services (fil dédié)."""
        launcher = self._launcher
        try:
            self._step("prefetch", "Préparation du modèle des longs documents…")
            launcher.prefetch_in_background()

            self._step("ollama", "Démarrage d'Ollama…")
            launcher._ensure_ollama_parallel()  # pylint: disable=protected-access
            ollama_ok = launcher._ollama_is_running()  # pylint: disable=protected-access
            # Arrêté sans repartir (et non « pas encore prêt ») : la fenêtre l'affiche
            if not ollama_ok and launcher._port_is_free():  # pylint: disable=protected-access
                self._set_status(error=OLLAMA_FAILED, ollama=False)

            self._step("onboarding", "Vérification de la configuration…")
            self._onboarding()

            self._step("model", "Vérification du modèle my_ai…")
            launcher.sync_custom_model()

            self._step("placement", "Placement du modèle…")
            launcher.ensure_best_placement(
                launcher._restart_ollama,  # pylint: disable=protected-access
                on_progress=lambda line: self._set_status(detail=line),
            )
            self._set_status(placement=launcher.placement_label())

            self._step("engine", "Chargement du moteur…")
            self._start_engine()

            self._step("services", "Démarrage des services…")
            self._start_services()
            self._restore_session()
            self.preload_voice()
            self._set_status(state="ready", step="ready", label="Prêt", detail="")
        except Exception as exc:  # pylint: disable=broad-except
            logger.exception("Lancement en échec")
            self._set_status(state="error", error=f"Lancement en échec : {exc}")

    def _onboarding(self) -> None:
        """Assistant de premier lancement (étape 3 du lanceur).

        Son interface web arrive en phase 3 : d'ici là, l'étape est passée, sans
        marquer l'assistant comme fait.
        """
        try:
            from interfaces.onboarding import should_run  # pylint: disable=import-outside-toplevel
            if should_run():
                print("🧭 Premier lancement détecté — l'assistant de configuration "
                      "n'est pas encore disponible dans l'interface web : étape passée")
        except Exception as exc:  # pylint: disable=broad-except
            print(f"⚠️ Assistant d'onboarding ignoré : {exc}")

    def _start_engine(self) -> None:
        """Moteur et service de chat (BaseGUI.__init__ puis initialize_ai_async)."""
        # pylint: disable=import-outside-toplevel
        from core.ai_engine import AIEngine
        from core.config import Config
        from relay.relay_bridge import RelayBridge
        from utils.file_processor import FileProcessor

        self.config = Config()
        self.engine = AIEngine(self.config)
        # Vérification légère, sans génération (initialize_ai_async de Tk)
        try:
            self.engine.initialize_llm()
            ollama_ok = self.engine.is_ollama_active()
            if not ollama_ok:
                self._set_status(ollama=False)
        except Exception as exc:  # pylint: disable=broad-except
            logger.warning("Vérification du moteur : %s", exc)

        self.chat = ChatService(
            self.engine,
            self.bus.publish,
            config=self.config,
            file_processor=FileProcessor(),
            ui_connected=lambda: self.bus.subscriber_count > 0,
            on_session_change=lambda session_id: self.state.set("current_session", session_id),
        )
        self.chat.start()
        # Chat mobile : traité ici, fenêtre ouverte ou non
        self.chat.attach_bridge(RelayBridge())

    def _start_services(self) -> None:
        """Relay (relay.auto_start) puis scheduler, comme _init_relay et _init_scheduler."""
        relay_cfg = self.config.get_section("relay") or {}
        if relay_cfg.get("auto_start", False):
            self.start_relay()

        sched_cfg = self.config.get_section("scheduler") or {}
        if sched_cfg.get("enabled", True):
            try:
                from core.scheduler import get_scheduler  # pylint: disable=import-outside-toplevel
                self.scheduler = get_scheduler()
                self.scheduler.set_executor(self.agent_service)
                self.scheduler.add_listener(self._on_scheduled_result)
                self.scheduler.start()
            except Exception as exc:  # pylint: disable=broad-except
                logger.warning("Scheduler non démarré : %s", exc)

    def _restore_session(self) -> None:
        """Rouvre la session du dernier lancement (D2), historique du modèle compris."""
        session_id = self.state.get("current_session")
        if not session_id or self.chat is None:
            return
        try:
            self.chat.load_session(session_id, reason="restored")
        except ChatError as exc:
            logger.info("Session %s non rouverte : %s", session_id, exc)
            self.state.set("current_session", None)

    def preload_voice(self) -> None:
        """Modules du micro chargés en arrière-plan, à la fin du lancement."""
        threading.Thread(target=self.voice.preload_input, name="voice-preload",
                         daemon=True).start()

    @property
    def voice(self):
        """Saisie et lecture vocales de la fenêtre (créées au premier usage)."""
        with self._lock:
            if self._voice is None:
                from interfaces.desktop.voice import VoiceService  # pylint: disable=import-outside-toplevel
                self._voice = VoiceService(self.bus.publish, autoread=_config_flag("ui.tts_autoread"),
                                           save_autoread=_save_autoread)
            return self._voice

    @property
    def agent_service(self):
        """Exécuteur d'agents partagé : page Agents, Relay et scheduler."""
        with self._lock:
            if self._agent_service is None:
                from relay.agent_relay import AgentRelayService  # pylint: disable=import-outside-toplevel
                self._agent_service = AgentRelayService()
            return self._agent_service

    def files_dropped(self, paths) -> None:
        """Fichiers déposés sur la fenêtre (fil de pywebview) : la page décide."""
        self.bus.publish("files.dropped", {"paths": [str(path) for path in paths]})

    def _on_scheduled_result(self, result: Dict[str, Any]) -> None:
        """Fin d'une tâche planifiée (fil du scheduler)."""
        self.bus.publish("scheduler.result", {
            "task_id": result.get("task_id"),
            "name": result.get("name") or "",
            "status": result.get("status") or "",
            "status_text": result.get("status_text") or "",
            "summary": result.get("summary") or "",
            "output_file": result.get("output_file"),
            "finished_at": result.get("finished_at"),
            "os_toast_shown": bool(result.get("os_toast_shown")),
        })

    # ── Relay ───────────────────────────────────────────────────────────────

    def start_relay(self, tunnel: Optional[bool] = None) -> Dict[str, Any]:
        """Démarre le Relay (Ctrl+R), avec ses tunnels sauf `tunnel=False`."""
        from relay.relay_server import RelayServer  # pylint: disable=import-outside-toplevel

        if self.relay is not None and self.relay.is_running():
            return self.relay_status()
        relay_cfg = self.config.get_section("relay") or {}
        if tunnel is None:
            tunnel = relay_cfg.get("tunnel", True)
        try:
            self.relay = RelayServer(ai_engine=self.engine, config=relay_cfg,
                                     agent_service=self.agent_service)
            self.relay.start(start_tunnel=bool(tunnel))
            print(f"📡 My_AI Relay démarré sur le port {relay_cfg.get('port', 8765)}")
        except Exception as exc:  # pylint: disable=broad-except
            logger.error("Relay non démarré : %s", exc)
            self.bus.publish("notification", {
                "level": "error", "message": "Impossible de démarrer My_AI Relay."})
        self._publish_relay_status()
        if self._relay_watch is None or not self._relay_watch.is_alive():
            self._relay_watch = threading.Thread(
                target=self._watch_relay, name="relay-status", daemon=True)
            self._relay_watch.start()
        return self.relay_status()

    def stop_relay(self) -> Dict[str, Any]:
        """Arrête le Relay et ses tunnels."""
        if self.relay is not None:
            try:
                self.relay.stop()
            except Exception as exc:  # pylint: disable=broad-except
                logger.warning("Arrêt du Relay : %s", exc)
        self._publish_relay_status()
        return self.relay_status()

    def relay_status(self) -> Dict[str, Any]:
        """État du Relay (événement relay.status)."""
        relay = self.relay
        if relay is None or not relay.is_running():
            return {"running": False, "port": None, "clients": 0, "tunnels": {},
                    "url": None, "local_url": None}
        try:
            tunnels = dict(relay.tunnel_urls)
        except Exception:  # pylint: disable=broad-except
            tunnels = {}
        return {
            "running": True,
            "port": relay.port,
            "clients": relay.bridge.connected_clients,
            "tunnels": tunnels,
            "url": relay.relay_url,
            "local_url": relay.local_url,
        }

    def _publish_relay_status(self) -> None:
        status = self.relay_status()
        if status != self._relay_snapshot:
            self._relay_snapshot = status
            self.bus.publish("relay.status", status)

    def _watch_relay(self) -> None:
        """Tunnels et appareils connectés changent sans prévenir : relevés toutes les 2 s."""
        while not self._closing:
            self._publish_relay_status()
            if self.relay is None or not self.relay.is_running():
                return
            time.sleep(2)

    # ── Arrêt ───────────────────────────────────────────────────────────────

    def shutdown(self) -> None:
        """Arrêt propre : Relay et tunnels, scheduler et son verrou, chat, serveur."""
        with self._lock:
            if self._closing:
                return
            self._closing = True
        # flush : le lanceur sort par os._exit, qui ne vide pas les tampons
        print("🛑 Fermeture de l'application...", flush=True)
        # Le Relay d'abord : ses tunnels (cloudflared, ssh) resteraient orphelins
        # et garderaient la console
        if self.relay is not None:
            try:
                print("🛑 Arrêt du Relay...", flush=True)
                self.relay.stop()
            except Exception as exc:  # pylint: disable=broad-except
                print(f"⚠️ Arrêt Relay à la fermeture: {exc}", flush=True)
        if self.scheduler is not None:
            try:
                self.scheduler.stop()
            except Exception:  # pylint: disable=broad-except
                pass
        if self._voice is not None:
            try:
                self._voice.shutdown()
            except Exception:  # pylint: disable=broad-except
                pass
        if self.chat is not None:
            self.chat.close()
        self.server.stop()
        self._closed.set()

    def wait(self) -> None:
        """Attend l'arrêt de l'appli (mode sans fenêtre)."""
        while not self._closed.wait(0.5):
            pass


def run_headless(launcher, port: int = 0) -> None:
    """launch_unified.py --headless : le serveur et le moteur, sans fenêtre."""
    app = DesktopApp(launcher, headless=True, port=port)
    url = app.start()
    print(f"🖥️ Interface desktop (sans fenêtre) : {url}", flush=True)
    try:
        app.wait()
    except KeyboardInterrupt:
        pass
    finally:
        app.shutdown()


def run_desktop(launcher, *, dev: bool = False, port: int = 0) -> None:
    """launch_unified.py --ui web : la fenêtre pywebview, ou le navigateur à défaut.

    La fenêtre s'ouvre tout de suite sur l'écran de chargement ; les étapes du
    lancement tournent dans leur fil. La fermer arrête l'appli proprement.
    """
    # pylint: disable=import-outside-toplevel
    from interfaces.desktop.window import open_window

    if dev and not port:
        port = DEV_BACKEND_PORT
    app = DesktopApp(launcher, dev=dev, port=port)
    url = app.start()
    vite = None
    dev_origins: tuple = ()
    if dev:
        from interfaces.desktop.devserver import ViteServer
        vite = ViteServer(backend_port=app.server.port)
        try:
            page = vite.start()
        except RuntimeError as exc:
            print(f"⚠️ {exc} — interface construite (frontend/dist) à la place", flush=True)
            vite = None
        else:
            url = f"{page}/#token={app.token}"
            dev_origins = (page,)
    try:
        if not open_window(app, url, dev_origins=dev_origins):
            import webbrowser
            print("🌐 Fenêtre indisponible (pywebview) : interface ouverte dans le navigateur. "
                  "Fermez cette console ou faites Ctrl+C pour quitter.", flush=True)
            webbrowser.open(url)
            app.wait()
    except KeyboardInterrupt:
        pass
    finally:
        app.shutdown()
        if vite is not None:
            vite.stop()
