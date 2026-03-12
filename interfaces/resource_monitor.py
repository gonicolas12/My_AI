"""
Monitoring des ressources système pour les agents IA
Collecte CPU, RAM, GPU et métriques d'inférence Ollama en temps réel.
"""

import platform
import subprocess
import threading
import time
from typing import Callable, Dict, List

try:
    import psutil

    PSUTIL_OK = True
except ImportError:
    PSUTIL_OK = False

# NVIDIA
try:
    import pynvml

    PYNVML_OK = True
except ImportError:
    PYNVML_OK = False

try:
    import GPUtil

    GPUTIL_OK = True
except ImportError:
    GPUTIL_OK = False

# AMD
try:
    import pyamdgpuinfo  # type: ignore

    AMDGPU_OK = True
except ImportError:
    AMDGPU_OK = False

# Windows WMI (works for any GPU vendor)
try:
    import wmi as wmi_module # type: ignore

    WMI_OK = True
except ImportError:
    WMI_OK = False


class ResourceMonitor:
    """Collecte périodique des métriques système liées à Ollama."""

    def __init__(self, interval: float = 3.0):
        self.interval = interval
        self._running = False
        self._thread = None
        self._callbacks: List[Callable[[dict], None]] = []
        self._lock = threading.Lock()
        self._metrics: Dict[str, float | bool] = {
            "cpu_percent": 0.0,
            "ram_used_mb": 0.0,
            "ram_total_mb": 0.0,
            "ram_percent": 0.0,
            "gpu_available": False,
            "gpu_percent": 0.0,
            "gpu_mem_used_mb": 0.0,
            "gpu_mem_total_mb": 0.0,
            "inference_ms": 0.0,
            "tokens_per_sec": 0.0,
        }
        # Historiques pour sparklines (60 derniers points ≈ 3 min à 3 s)
        self._history_len = 60
        self.history: Dict[str, List[float]] = {
            "cpu": [],
            "ram": [],
            "gpu": [],
            "tps": [],
        }

    # ── Contrôle ───────────────────────────────────────────────────

    def start(self):
        """Démarre la collecte dans un thread séparé."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self):
        """Arrête la collecte."""
        self._running = False

    def add_callback(self, cb: Callable[[dict], None]):
        """Ajoute une fonction de rappel qui reçoit les métriques à chaque collecte."""
        self._callbacks.append(cb)

    def get_metrics(self) -> dict:
        """Retourne une copie des métriques actuelles."""
        with self._lock:
            return dict(self._metrics)

    def update_inference(self, inference_ms: float, tokens_per_sec: float):
        """Mis à jour depuis l'extérieur quand une inférence termine."""
        with self._lock:
            self._metrics["inference_ms"] = inference_ms
            self._metrics["tokens_per_sec"] = tokens_per_sec
            self._push_history("tps", tokens_per_sec)

    # ── Boucle de collecte ─────────────────────────────────────────

    def _loop(self):
        while self._running:
            self._collect()
            with self._lock:
                snapshot = dict(self._metrics)
            for cb in self._callbacks:
                try:
                    cb(snapshot)
                except Exception:
                    pass
            time.sleep(self.interval)

    def _collect(self):
        self._collect_cpu_ram()
        self._collect_gpu()

    def _collect_cpu_ram(self):
        if not PSUTIL_OK:
            return
        try:
            ollama_cpu = 0.0
            ollama_ram = 0.0
            for proc in psutil.process_iter(["name", "cpu_percent", "memory_info"]):
                try:
                    pname = (proc.info["name"] or "").lower()
                    if "ollama" in pname:
                        ollama_cpu += proc.info["cpu_percent"] or 0.0
                        mi = proc.info["memory_info"]
                        if mi:
                            ollama_ram += mi.rss
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass

            total = psutil.virtual_memory().total
            with self._lock:
                self._metrics["cpu_percent"] = min(ollama_cpu, 100.0)
                self._metrics["ram_used_mb"] = ollama_ram / (1024 * 1024)
                self._metrics["ram_total_mb"] = total / (1024 * 1024)
                self._metrics["ram_percent"] = (
                    ollama_ram / total * 100 if total else 0.0
                )
            self._push_history("cpu", min(ollama_cpu, 100.0))
            self._push_history("ram", ollama_ram / (1024 * 1024))
        except Exception:
            pass

    def _collect_gpu(self):
        # 1) NVIDIA via pynvml
        if PYNVML_OK and self._try_nvidia_pynvml():
            return
        # 2) NVIDIA via GPUtil
        if GPUTIL_OK and self._try_nvidia_gputil():
            return
        # 3) AMD via pyamdgpuinfo
        if AMDGPU_OK and self._try_amd():
            return
        # 4) AMD via rocm-smi CLI
        if self._try_rocm_smi():
            return
        # 5) Windows WMI fallback (any vendor — basic info only)
        if WMI_OK and platform.system() == "Windows" and self._try_wmi():
            return

        with self._lock:
            self._metrics["gpu_available"] = False

    # ── NVIDIA (pynvml) ────────────────────────────────────────────

    def _try_nvidia_pynvml(self) -> bool:
        try:
            pynvml.nvmlInit()
            h = pynvml.nvmlDeviceGetHandleByIndex(0)
            util = pynvml.nvmlDeviceGetUtilizationRates(h)
            mem = pynvml.nvmlDeviceGetMemoryInfo(h)
            with self._lock:
                self._metrics["gpu_available"] = True
                self._metrics["gpu_percent"] = float(util.gpu)
                self._metrics["gpu_mem_used_mb"] = mem.used / (1024 * 1024)
                self._metrics["gpu_mem_total_mb"] = mem.total / (1024 * 1024)
            self._push_history("gpu", float(util.gpu))
            pynvml.nvmlShutdown()
            return True
        except Exception:
            return False

    # ── NVIDIA (GPUtil) ────────────────────────────────────────────

    def _try_nvidia_gputil(self) -> bool:
        try:
            gpus = GPUtil.getGPUs()
            if gpus:
                g = gpus[0]
                with self._lock:
                    self._metrics["gpu_available"] = True
                    self._metrics["gpu_percent"] = g.load * 100
                    self._metrics["gpu_mem_used_mb"] = float(g.memoryUsed)
                    self._metrics["gpu_mem_total_mb"] = float(g.memoryTotal)
                self._push_history("gpu", g.load * 100)
                return True
        except Exception:
            pass
        return False

    # ── AMD (pyamdgpuinfo) ─────────────────────────────────────────

    def _try_amd(self) -> bool:
        try:
            if pyamdgpuinfo.detect_gpus() < 1:
                return False
            gpu = pyamdgpuinfo.get_gpu(0)
            usage = gpu.query_load() * 100          # 0.0-1.0 → %
            vram_used = gpu.query_vram_usage()      # bytes
            vram_total = gpu.memory_info["vram_size"]  # bytes
            with self._lock:
                self._metrics["gpu_available"] = True
                self._metrics["gpu_percent"] = usage
                self._metrics["gpu_mem_used_mb"] = vram_used / (1024 * 1024)
                self._metrics["gpu_mem_total_mb"] = vram_total / (1024 * 1024)
            self._push_history("gpu", usage)
            return True
        except Exception:
            return False

    # ── AMD (rocm-smi CLI) ─────────────────────────────────────────

    def _try_rocm_smi(self) -> bool:
        try:
            result = subprocess.run(
                ["rocm-smi", "--showuse", "--showmemuse", "--csv"],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
            if result.returncode != 0:
                return False
            lines = result.stdout.strip().split("\n")
            if len(lines) < 2:
                return False
            # Parse CSV header + first data row
            header = [h.strip().lower() for h in lines[0].split(",")]
            values = [v.strip() for v in lines[1].split(",")]
            data = dict(zip(header, values))
            usage = float(data.get("gpu use (%)", data.get("gpu_use", "0")))
            mem_used = float(data.get("gpu memory use (%)", data.get("mem_use", "0")))
            with self._lock:
                self._metrics["gpu_available"] = True
                self._metrics["gpu_percent"] = usage
                # rocm-smi gives % for memory, not absolute — store as %
                self._metrics["gpu_mem_used_mb"] = mem_used
                self._metrics["gpu_mem_total_mb"] = 100.0
            self._push_history("gpu", usage)
            return True
        except (FileNotFoundError, subprocess.TimeoutExpired, Exception):
            return False

    # ── Windows WMI (any vendor — basic info) ──────────────────────

    def _try_wmi(self) -> bool:
        try:
            w = wmi_module.WMI()
            gpus = w.Win32_VideoController()
            if not gpus:
                return False
            gpu = gpus[0]
            # WMI can report AdapterRAM (bytes) but no real-time usage
            vram_bytes = int(gpu.AdapterRAM or 0)
            with self._lock:
                self._metrics["gpu_available"] = True
                self._metrics["gpu_percent"] = 0.0  # WMI has no usage metric
                self._metrics["gpu_mem_used_mb"] = 0.0
                self._metrics["gpu_mem_total_mb"] = vram_bytes / (1024 * 1024) if vram_bytes > 0 else 0.0
            return True
        except Exception:
            return False

    def _push_history(self, key: str, value: float):
        h = self.history[key]
        h.append(value)
        if len(h) > self._history_len:
            h.pop(0)
