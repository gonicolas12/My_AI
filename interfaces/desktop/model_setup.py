"""
Modèles Ollama de la fenêtre : téléchargement, création de « my_ai »,
assistant de premier lancement

Les fenêtres Tk (settings_panel.py, OnboardingWizard d'interfaces/onboarding.py)
appelaient les fonctions d'interfaces/onboarding.py dans un fil et affichaient
leur progression et leur journal. Ici, un seul travail à la fois (ModelJobs) :
sa progression et son journal partent à la fenêtre en événements
(models.progress, models.log, models.done), et son état se relit (panneau
rouvert, fenêtre rechargée).

OllamaSetup regroupe ces fonctions et la lecture de config.yaml : la
démonstration et les tests le remplacent, et n'écrivent ainsi jamais dans le
vrai config.yaml ni dans le Modelfile.
"""

import threading
from typing import Any, Callable, Dict, List, Optional

from utils.logger import setup_logger

logger = setup_logger("DesktopModels")

# Lignes du journal gardées pour une fenêtre qui se rouvre
_LOG_KEEP = 200

# Fenêtres de contexte proposées (Réglages de Tk)
NUM_CTX_CHOICES = [2048, 4096, 8192, 16384, 32768, 65536]
# Délai d'une requête au modèle (s), borné comme dans Tk
TIMEOUT_RANGE = (30, 7200)


class ModelJobError(Exception):
    """Travail refusé (déjà en cours, nom vide, Ollama absent) : message affiché."""


class OllamaSetup:
    """Fonctions d'interfaces/onboarding.py et réglages de config.yaml."""

    @staticmethod
    def _module():
        from interfaces import onboarding  # pylint: disable=import-outside-toplevel
        return onboarding

    def values(self) -> Dict[str, Any]:
        """Réglages lus dans config.yaml, à la racine du projet (là où les écrit onboarding.py)."""
        from core.config import Config  # pylint: disable=import-outside-toplevel
        config = Config(str(self._module().PROJECT_ROOT / "config.yaml"))
        supported = config.get("language.supported") or ["fr", "en"]
        return {
            "temperature": config.get("llm.local.temperature", 0.7),
            "num_ctx": config.get("llm.local.num_ctx", 32768),
            "timeout": config.get("llm.local.timeout", 1200),
            "language": config.get("language.default", "fr"),
            "languages": [str(code) for code in supported],
            "relay_auto_start": bool(config.get("relay.auto_start", False)),
        }

    def model_choices(self) -> List[str]:
        """Modèles proposés par l'assistant de premier lancement."""
        return list(self._module().MODEL_CHOICES)

    def ollama_reachable(self) -> bool:
        """Ollama répond (GET /api/tags, 2 s)."""
        return self._module().ollama_reachable()

    def installed_models(self) -> List[str]:
        """Modèles installés, my_ai compris (liste vide si Ollama ne répond pas)."""
        return self._module().list_installed_models()

    def base_model(self) -> str:
        """Modèle de base de my_ai (ligne FROM du Modelfile)."""
        return self._module().current_base_model()

    def pull(self, name: str, on_progress: Callable[[float, str], None],
             on_log: Callable[[str], None]) -> None:
        """Télécharge un modèle (bloquant, sans annulation possible)."""
        self._module().pull_model(name, on_progress, on_log)

    def apply_base(self, base: str) -> None:
        """Ligne FROM du Modelfile et default_model de config.yaml."""
        self._module().apply_model_choice(base)

    def create_custom_model(self, on_log: Callable[[str], None]) -> None:
        """Recrée my_ai depuis le Modelfile (ollama create)."""
        self._module().create_custom_model(on_log)

    def save_generation(self, temperature: float, num_ctx: int, timeout: int) -> None:
        """Paramètres de génération dans config.yaml et le Modelfile (commentaires gardés)."""
        self._module().apply_generation_params(temperature=temperature, num_ctx=num_ctx,
                                               timeout=timeout)

    def set_flag(self, name: str, value) -> None:
        """Réglage simple de config.yaml (language.default, ui.tts_autoread, relay.auto_start)."""
        self._module().set_config_flag(name, value)

    def mark_done(self) -> None:
        """L'assistant de premier lancement ne s'affichera plus."""
        self._module().mark_done()

    def forget_done(self) -> None:
        """L'assistant s'affichera au prochain démarrage (marqueur supprimé)."""
        marker = self._module().marker_path()
        if marker.exists():
            marker.unlink()

    def hardware(self) -> Dict[str, Any]:
        """RAM, mémoire du GPU, cœurs et modèle recommandé (nvidia-smi : jusqu'à 4 s)."""
        module = self._module()
        ram = module.detect_ram_gb()
        vram = module.detect_vram_gb()
        cores = module.detect_cpu_cores()
        return {"ram_gb": ram, "vram_gb": vram, "cpu_cores": cores,
                "recommended": module.recommend_model(ram, vram, cores)}


class ModelJobs:
    """Téléchargement et création de modèles, un seul à la fois."""

    def __init__(self, setup: OllamaSetup, publish: Callable[[str, Dict[str, Any]], None]):
        self._setup = setup
        self._publish = publish
        self._lock = threading.Lock()
        self._job: Optional[Dict[str, Any]] = None

    def status(self) -> Optional[Dict[str, Any]]:
        """Travail en cours ou dernier terminé : action, modèle, progression, journal."""
        with self._lock:
            if self._job is None:
                return None
            return dict(self._job, log=list(self._job["log"]))

    def pull(self, name: str) -> None:
        """Télécharge un modèle (bouton « Pull » des Réglages)."""
        name = (name or "").strip()
        if not name:
            raise ModelJobError("Entrez un nom de modèle (ex : qwen3.5:4b).")
        self._start("pull", name, self._run_pull)

    def apply(self, base: str) -> None:
        """Régénère my_ai à partir d'un modèle de base (bouton « Appliquer »)."""
        base = (base or "").strip()
        if not base:
            raise ModelJobError("Choisissez un modèle de base.")
        self._start("apply", base, self._run_apply)

    def install(self, model: str) -> None:
        """Assistant : télécharge le modèle, crée my_ai, marque l'assistant comme fait."""
        self._start("install", model, self._run_install)

    def _start(self, action: str, name: str, target: Callable[[str], str]) -> None:
        with self._lock:
            if self._job is not None and self._job["running"]:
                raise ModelJobError("Un téléchargement ou une création de modèle est déjà en cours.")
        if not self._setup.ollama_reachable():
            raise ModelJobError("Ollama n'est pas joignable.")
        with self._lock:
            if self._job is not None and self._job["running"]:
                raise ModelJobError("Un téléchargement ou une création de modèle est déjà en cours.")
            self._job = {"action": action, "name": name, "running": True, "ok": None,
                         "fraction": 0.0, "status": "", "message": "", "log": []}
        threading.Thread(target=self._run, args=(action, name, target), name=f"models-{action}",
                         daemon=True).start()

    def _run(self, action: str, name: str, target: Callable[[str], str]) -> None:
        try:
            message = target(name)
            ok = True
        except Exception as exc:  # pylint: disable=broad-except
            logger.warning("Modèle %s (%s) en échec : %s", name, action, exc)
            self.log(f"❌ Erreur pull : {exc}" if action == "pull" else f"❌ Erreur : {exc}")
            ok, message = False, str(exc)
        with self._lock:
            if self._job is not None:
                self._job.update(running=False, ok=ok, message=message)
        self._publish("models.done", {"action": action, "name": name, "ok": ok,
                                      "message": message})
        # Toasts des Réglages (l'assistant affiche lui-même son état)
        if action == "pull":
            self._publish("notification", {
                "level": "success" if ok else "error",
                "message": f"✅ {name} téléchargé" if ok else "❌ Échec du téléchargement"})
        elif action == "apply":
            self._publish("notification", {
                "level": "success" if ok else "error",
                "message": "✅ Modèle 'my_ai' régénéré" if ok else "❌ Échec de la régénération"})

    def progress(self, fraction: float, status: str) -> None:
        """Avancée du téléchargement (par couche, comme Ollama la donne)."""
        fraction = max(0.0, min(1.0, float(fraction)))
        with self._lock:
            if self._job is not None:
                self._job.update(fraction=fraction, status=status or "")
        self._publish("models.progress", {"fraction": fraction, "status": status or ""})

    def log(self, line: str) -> None:
        """Ligne du journal (sorties d'Ollama, étapes)."""
        line = (line or "").rstrip()
        if not line:
            return
        with self._lock:
            if self._job is not None:
                self._job["log"] = (self._job["log"] + [line])[-_LOG_KEEP:]
        self._publish("models.log", {"line": line})

    def _run_pull(self, name: str) -> str:
        self.log(f"📥 Téléchargement de {name}…")
        self._setup.pull(name, self.progress, self.log)
        self.log(f"✅ {name} téléchargé.")
        return f"✅ {name} téléchargé"

    def _run_apply(self, base: str) -> str:
        self.log(f"🔧 Modelfile FROM → {base}")
        self._setup.apply_base(base)
        self.log("🏗️  Création du modèle 'my_ai'…")
        self._setup.create_custom_model(self.log)
        self.log("✅ Modèle 'my_ai' régénéré.")
        return "✅ Modèle 'my_ai' régénéré"

    def _run_install(self, model: str) -> str:
        self.log(f"📥 Téléchargement de {model}…")
        self._setup.pull(model, self.progress, self.log)
        self.log(f"✅ {model} téléchargé.")
        self.log("🔧 Mise à jour de Modelfile et config.yaml…")
        self._setup.apply_base(model)
        self.log("🏗️  Création du modèle personnalisé 'my_ai'…")
        self._setup.create_custom_model(self.log)
        self.log("✅ Modèle 'my_ai' créé.")
        self._setup.mark_done()
        self.progress(1.0, "Terminé")
        self.log("🎉 Configuration terminée ! Vous pouvez lancer My_AI.")
        return "🎉 Configuration terminée"


class FirstLaunch:
    """Assistant de premier lancement, dans la fenêtre (OnboardingWizard de Tk).

    Le lancement s'arrête à son étape, avant la synchronisation de my_ai et le
    placement du modèle, jusqu'à « Démarrer My_AI » (après l'installation) ou
    « Passer » (l'assistant est alors marqué comme fait, comme dans Tk).
    """

    def __init__(self, setup: OllamaSetup, jobs: ModelJobs):
        self._setup = setup
        self._jobs = jobs
        self._released = threading.Event()
        self._lock = threading.Lock()
        self._hardware: Optional[Dict[str, Any]] = None

    def info(self) -> Dict[str, Any]:
        """Ollama, matériel et recommandation, modèles proposés, travail en cours."""
        with self._lock:
            if self._hardware is None:
                self._hardware = self._setup.hardware()
            hardware = dict(self._hardware)
        return dict(hardware, ollama=self._setup.ollama_reachable(),
                    choices=self._setup.model_choices(), job=self._jobs.status())

    def install(self, model: str) -> None:
        """« Installer » : télécharge le modèle choisi et crée my_ai."""
        if model not in self._setup.model_choices():
            raise ModelJobError(f"Modèle inconnu : {model}")
        self._jobs.install(model)

    def skip(self) -> None:
        """« Passer » ou « Continuer quand même » : marqué comme fait, lancement repris."""
        self._setup.mark_done()
        self._released.set()

    def finish(self) -> None:
        """« Démarrer My_AI », après l'installation : le lancement reprend."""
        self._released.set()

    @property
    def released(self) -> bool:
        """Le lancement a repris."""
        return self._released.is_set()

    def wait(self, closing: Callable[[], bool], poll: float = 0.2) -> bool:
        """Attend la fin de l'assistant ; False si l'appli se ferme entre-temps."""
        while not self._released.wait(poll):
            if closing():
                return False
        return True
