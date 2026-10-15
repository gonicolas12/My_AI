"""
Moniteur de ressources de la page Agents (stats_section.py de Tk)

Reprend interfaces/resource_monitor.py : CPU et RAM des processus d'Ollama
(et, depuis la phase 4b, du « llama-server » qu'il lance pour le modèle), GPU
et VRAM (NVML, GPUtil, AMD, WMI), une mesure toutes les 3 s, les 60 dernières
gardées pour les mini-graphiques. S'y ajoutent le temps d'inférence et les
tokens/s du dernier agent, que la page Agents lui donne (agents.py, D17) :
dans Tk, les tokens/s restaient à 0.

Le moniteur démarre à la première ouverture de la page Agents, et ne mesure
que tant qu'une fenêtre est connectée. Chaque mesure part en événement
« resources.sample » ; GET /api/resources rend la dernière et l'historique.
"""

import threading
from typing import Any, Callable, Dict, Optional

from utils.logger import setup_logger

logger = setup_logger("DesktopResources")

# Intervalle des mesures (ResourceMonitor de Tk)
INTERVAL = 3.0


def _monitor_class():
    """ResourceMonitor de Tk, dont la mesure attend qu'une fenêtre soit connectée."""
    # pylint: disable=import-outside-toplevel
    from interfaces.resource_monitor import ResourceMonitor

    class WindowResourceMonitor(ResourceMonitor):
        """Ne mesure rien tant qu'aucune fenêtre n'est connectée."""

        def __init__(self, connected: Callable[[], bool], interval: float = INTERVAL):
            super().__init__(interval=interval)
            self._connected = connected

        def _collect(self):
            if self._connected():
                super()._collect()

    return WindowResourceMonitor


class ResourcesService:
    """Mesures de la page Agents, publiées sur le bus de la fenêtre."""

    def __init__(self, publish: Callable[..., Any], connected: Callable[[], bool],
                 monitor: Optional[Any] = None):
        """
        Args:
            publish: publication d'un événement sur le bus de la fenêtre
            connected: au moins une fenêtre est connectée
            monitor: moniteur (ResourceMonitor de Tk par défaut ; simulé en démonstration)
        """
        self._publish = publish
        self._connected = connected
        self._lock = threading.Lock()
        self._monitor = monitor
        self._started = False
        # Fins d'agents relevées : la page ajoute un point aux tokens/s à chaque nouvelle
        self._inferences = 0

    @property
    def monitor(self) -> Any:
        """Moniteur, créé au premier usage (import de psutil, NVML…)."""
        with self._lock:
            if self._monitor is None:
                self._monitor = _monitor_class()(self._connected)
            return self._monitor

    def start(self) -> None:
        """Démarre les mesures (première ouverture de la page Agents)."""
        monitor = self.monitor
        with self._lock:
            if self._started:
                return
            self._started = True
        monitor.add_callback(self._on_sample)
        monitor.start()
        logger.info("Moniteur de ressources démarré (une mesure toutes les %.0f s)",
                    monitor.interval)

    def stop(self) -> None:
        """Arrête les mesures (fermeture de l'appli)."""
        with self._lock:
            monitor = self._monitor if self._started else None
            self._started = False
        if monitor is not None:
            monitor.stop()

    def snapshot(self) -> Dict[str, Any]:
        """Dernière mesure et historique (60 points) ; démarre le moniteur."""
        self.start()
        monitor = self.monitor
        metrics = monitor.get_metrics()
        with monitor._lock:  # pylint: disable=protected-access
            history = {key: list(values) for key, values in monitor.history.items()}
        return {"metrics": metrics, "history": history, "inferences": self._inferences,
                "interval": monitor.interval}

    def update_inference(self, inference_ms: float, tokens_per_sec: float) -> None:
        """Fin d'un agent : durée et tokens/s (page Agents), publiés tout de suite."""
        monitor = self.monitor
        monitor.update_inference(inference_ms, tokens_per_sec)
        with self._lock:
            self._inferences += 1
        self._on_sample(monitor.get_metrics())

    def _on_sample(self, metrics: Dict[str, Any]) -> None:
        """Mesure du moniteur (son fil) : publiée si une fenêtre la verra."""
        if not self._connected():
            return
        self._publish("resources.sample", {"metrics": dict(metrics),
                                           "inferences": self._inferences})
