"""
Réglages de la fenêtre (settings_panel.py de Tk)

  - modèles Ollama : liste, téléchargement, modèle de base de my_ai
    (travaux de model_setup.py) ;
  - paramètres de génération : température, fenêtre de contexte et délai,
    écrits dans config.yaml et le Modelfile (commentaires gardés), puis
    appliqués tout de suite au LocalLLM du moteur, comme dans Tk ;
  - langue par défaut, Relay au lancement, relance de l'assistant de
    configuration au prochain démarrage.

La lecture automatique passe par la voix (voice.py), qui garde le bouton de
la barre latérale à jour.

Seule la liste des modèles appelle Ollama, et seulement quand le panneau
s'ouvre : la fenêtre n'affiche les panneaux qu'une fois le lancement fini,
placement du modèle compris.
"""

from typing import Any, Callable, Dict, Optional

from core import i18n
from core.i18n import tr
from interfaces.desktop.model_setup import NUM_CTX_CHOICES, TIMEOUT_RANGE, OllamaSetup
from utils.logger import setup_logger

logger = setup_logger("DesktopSettings")

# Réglages simples que le panneau écrit lui-même (la lecture automatique a sa route)
FLAGS = ("language.default", "relay.auto_start")


class SettingsError(Exception):
    """Réglage refusé : message affiché."""


class SettingsService:
    """Lecture et écriture des réglages du panneau."""

    def __init__(self, setup: OllamaSetup, engine: Callable[[], Optional[Any]]):
        """
        Args:
            setup: fonctions d'interfaces/onboarding.py et lecture de config.yaml
            engine: moteur en cours (None pendant le lancement)
        """
        self._setup = setup
        self._engine = engine

    def snapshot(self) -> Dict[str, Any]:
        """Réglages de config.yaml et modèle de base, sans appel à Ollama."""
        values = self._setup.values()
        num_ctx = int(values["num_ctx"])
        return {
            "base_model": self._setup.base_model(),
            "generation": {
                "temperature": float(values["temperature"]),
                "num_ctx": num_ctx,
                "timeout": int(values["timeout"]),
            },
            # La valeur en cours reste proposée même hors de la liste (Tk)
            "num_ctx_choices": sorted(set(NUM_CTX_CHOICES) | {num_ctx}),
            "language": values["language"],
            "languages": values["languages"],
            "relay_auto_start": values["relay_auto_start"],
        }

    def models(self) -> Dict[str, Any]:
        """Modèles d'Ollama : installés, et bases possibles de my_ai (sans my_ai)."""
        reachable = self._setup.ollama_reachable()
        installed = self._setup.installed_models() if reachable else []
        bases = [name for name in installed if not name.startswith("my_ai")] or list(installed)
        base = self._setup.base_model()
        if base and base not in bases:
            bases.insert(0, base)
        return {"ollama": reachable, "installed": installed, "bases": bases, "base_model": base}

    def save_generation(self, temperature: float, num_ctx: int, timeout: float) -> Dict[str, Any]:
        """Paramètres de génération : config.yaml, Modelfile, puis le LocalLLM en cours.

        my_ai n'est recréé qu'au prochain lancement (sync_custom_model, le
        Modelfile ayant changé), comme dans Tk.
        """
        temperature = round(min(1.0, max(0.0, float(temperature))), 2)
        num_ctx = int(num_ctx)
        if num_ctx < 512:
            raise SettingsError(tr("settings.contextTooSmall"))
        low, high = TIMEOUT_RANGE
        timeout = max(low, min(high, int(float(timeout))))
        self._setup.save_generation(temperature, num_ctx, timeout)
        llm = self._local_llm()
        if llm is not None:
            llm.gen_temperature = temperature
            llm.gen_num_ctx = num_ctx
            llm.timeout = timeout
        return {"temperature": temperature, "num_ctx": num_ctx, "timeout": timeout}

    def set_flag(self, name: str, value: Any) -> None:
        """Langue par défaut ou Relay au lancement (pris en compte au prochain démarrage)."""
        if name not in FLAGS:
            raise SettingsError(tr("settings.unknownSetting", name=name))
        if name == "language.default":
            if value not in self._setup.values()["languages"]:
                raise SettingsError(tr("settings.languageUnsupported", language=value))
        else:
            value = bool(value)
        self._setup.set_flag(name, value)

    def set_language(self, code: Any) -> str:
        """Langue de l'interface et des réponses par défaut : config.yaml, puis le moteur.

        Le détecteur de langue du moteur prend la nouvelle langue par défaut
        tout de suite (message trop court ou ambigu) : sans redémarrage.
        """
        language = i18n.normalize(code)
        if language is None or language != code:
            raise SettingsError(tr("settings.languageUnsupported", language=code))
        self.set_flag("language.default", language)
        detector = getattr(self._engine(), "language_detector", None)
        if detector is not None:
            detector.set_default_language(language)
        return language

    def restart_onboarding(self) -> None:
        """L'assistant de configuration s'affichera au prochain démarrage.

        Sauf si my_ai existe déjà à ce moment-là : should_run() remet alors le
        marqueur, comme dans Tk.
        """
        self._setup.forget_done()

    def _local_llm(self):
        engine = self._engine()
        local_ai = getattr(engine, "local_ai", None)
        return getattr(local_ai, "local_llm", None)
