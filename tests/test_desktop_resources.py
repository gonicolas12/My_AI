"""
Tests du moniteur de ressources de la fenêtre (interfaces/desktop/resources.py)

Le moniteur de Tk (interfaces/resource_monitor.py) est simulé, sauf pour
vérifier qu'il ne mesure rien sans fenêtre connectée : démarrage à la
première lecture, mesures publiées seulement vers une fenêtre, fin d'un agent
publiée tout de suite, avec ses tokens/s.
"""

import threading
from types import SimpleNamespace

from interfaces.desktop import resources as resources_module
from interfaces.desktop.events import EventBus, validate_event
from interfaces.desktop.resources import ResourcesService


class FakeMonitor:
    """ResourceMonitor de Tk réduit à son interface."""

    interval = 3.0

    def __init__(self):
        self.callbacks = []
        self.started = False
        self._lock = threading.Lock()
        self.metrics = {"cpu_percent": 4.0, "ram_used_mb": 2900.0, "ram_total_mb": 16000.0,
                        "ram_percent": 18.1, "gpu_available": True, "gpu_percent": 35.0,
                        "gpu_mem_used_mb": 3700.0, "gpu_mem_total_mb": 6144.0,
                        "inference_ms": 0.0, "tokens_per_sec": 0.0}
        self.history = {"cpu": [3.0, 4.0], "ram": [2900.0, 2900.0], "gpu": [30.0, 35.0],
                        "tps": []}

    def add_callback(self, callback):
        self.callbacks.append(callback)

    def start(self):
        self.started = True

    def stop(self):
        self.started = False

    def get_metrics(self):
        return dict(self.metrics)

    def update_inference(self, inference_ms, tokens_per_sec):
        self.metrics.update(inference_ms=inference_ms, tokens_per_sec=tokens_per_sec)
        self.history["tps"].append(tokens_per_sec)


def service_with(connected=True):
    bus = EventBus()
    events = []
    bus.subscribe(events.append)
    state = {"connected": connected}
    monitor = FakeMonitor()
    service = ResourcesService(bus.publish, lambda: state["connected"], monitor=monitor)
    return SimpleNamespace(service=service, monitor=monitor, events=events, state=state)


def samples(events):
    return [event for event in events if event["type"] == "resources.sample"]


def test_the_first_read_starts_the_monitor_once():
    env = service_with()
    snapshot = env.service.snapshot()
    assert env.monitor.started and len(env.monitor.callbacks) == 1
    assert snapshot == {"metrics": env.monitor.metrics, "history": env.monitor.history,
                        "inferences": 0, "interval": 3.0}
    env.service.snapshot()
    assert len(env.monitor.callbacks) == 1
    env.service.stop()
    assert not env.monitor.started


def test_samples_reach_a_connected_window_only():
    env = service_with()
    env.service.snapshot()
    sample = env.monitor.callbacks[0]
    sample(env.monitor.get_metrics())
    published = samples(env.events)
    assert len(published) == 1 and published[0]["payload"]["metrics"]["gpu_percent"] == 35.0
    validate_event(published[0])
    env.state["connected"] = False
    sample(env.monitor.get_metrics())
    assert len(samples(env.events)) == 1


def test_the_end_of_an_agent_is_published_at_once():
    env = service_with()
    env.service.update_inference(1840.0, 41.5)
    published = samples(env.events)[-1]["payload"]
    assert published["metrics"]["tokens_per_sec"] == 41.5
    assert published["metrics"]["inference_ms"] == 1840.0 and published["inferences"] == 1
    assert env.service.snapshot()["history"]["tps"] == [41.5]


def test_the_monitor_counts_the_model_process_of_ollama(monkeypatch):
    """Depuis Ollama 0.40, le modèle tourne dans « llama-server », lancé par Ollama."""
    from interfaces import resource_monitor  # pylint: disable=import-outside-toplevel

    def proc(pid, ppid, name, cpu, rss_mb):
        return SimpleNamespace(info={"pid": pid, "ppid": ppid, "name": name, "cpu_percent": cpu,
                                     "memory_info": SimpleNamespace(rss=rss_mb * 1024 * 1024)})

    processes = [proc(10, 1, "ollama.exe", 2.0, 58), proc(11, 10, "llama-server.exe", 30.0, 1700),
                 proc(12, 1, "llama-server.exe", 50.0, 900), proc(13, 1, "code.exe", 40.0, 800)]
    monkeypatch.setattr(resource_monitor.psutil, "process_iter", lambda _attrs: processes)
    monitor = resource_monitor.ResourceMonitor()
    monitor._collect_cpu_ram()  # pylint: disable=protected-access
    metrics = monitor.get_metrics()
    # Ollama et son runner ; ni un autre llama-server ni le reste du système
    assert metrics["cpu_percent"] == 32.0 and round(metrics["ram_used_mb"]) == 1758


def test_the_real_monitor_measures_only_with_a_window(monkeypatch):
    monitor_class = resources_module._monitor_class()  # pylint: disable=protected-access
    measured = []
    monkeypatch.setattr(monitor_class.__mro__[1], "_collect", lambda self: measured.append(1))
    monitor_class(lambda: False)._collect()  # pylint: disable=protected-access
    assert not measured
    monitor_class(lambda: True)._collect()  # pylint: disable=protected-access
    assert measured == [1]
