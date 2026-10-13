"""
Voix de l'interface web : saisie (Whisper) et lecture (pyttsx3)

La capture du micro, la transcription et la synthèse restent côté Python,
comme dans l'interface Tk (voice_input.py, voice_output.py) ; la fenêtre ne
fait que démarrer, arrêter et afficher l'état, reçu en événements :
  - voice.input      : idle, recording, transcribing, error
  - voice.transcript : texte dicté, inséré au curseur de la zone de saisie
  - voice.output     : speaking, idle, error, avec la clé de ce qui est lu

Les modules de la voix ne sont importés qu'au premier usage : faster-whisper
(ctranslate2) alourdirait le lancement.
"""

import importlib.util
import threading
from typing import Any, Callable, Dict, Optional

from utils.logger import setup_logger

logger = setup_logger("DesktopVoice")

# Messages de l'interface Tk quand une dépendance manque
INPUT_UNAVAILABLE = "Saisie vocale indisponible : installe 'faster-whisper' et 'sounddevice'."
OUTPUT_UNAVAILABLE = "Lecture vocale indisponible : installe 'pyttsx3'."


def _installed(module: str) -> bool:
    """Vrai si le paquet est installé (sans l'importer)."""
    try:
        return importlib.util.find_spec(module) is not None
    except (ImportError, ValueError):
        return False


class VoiceService:
    """Saisie et lecture vocales de la fenêtre, état publié en événements."""

    def __init__(self, publish: Callable[..., Any], autoread: bool = False,
                 save_autoread: Optional[Callable[[bool], None]] = None):
        """
        Args:
            publish: collecteur d'événements (EventBus.publish)
            autoread: lecture automatique des réponses (réglage ui.tts_autoread)
            save_autoread: enregistre ce réglage (config.yaml, commentaires gardés)
        """
        self._publish = publish
        self._autoread = bool(autoread)
        self._save_autoread = save_autoread
        self._lock = threading.Lock()
        self._input = None
        self._output = None
        self._input_state = "idle"
        self._output_state = "idle"
        self._speaking_key: Optional[str] = None

    # ── État ────────────────────────────────────────────────────────────────

    def status(self) -> Dict[str, Any]:
        """Disponibilité et état courant (GET /api/voice)."""
        with self._lock:
            return {
                "input_available": _installed("faster_whisper") and _installed("sounddevice"),
                "output_available": _installed("pyttsx3"),
                "input_state": self._input_state,
                "output_state": self._output_state,
                "speaking_key": self._speaking_key,
                "autoread": self._autoread,
            }

    @property
    def autoread(self) -> bool:
        """Lecture automatique des réponses."""
        return self._autoread

    def set_autoread(self, enabled: bool) -> bool:
        """Active ou coupe la lecture automatique ; la couper arrête la lecture en cours."""
        self._autoread = bool(enabled)
        if self._save_autoread is not None:
            try:
                self._save_autoread(self._autoread)
            except Exception as exc:  # pylint: disable=broad-except
                logger.warning("Lecture automatique non enregistrée : %s", exc)
        if not self._autoread:
            self.stop_speaking()
        return self._autoread

    # ── Saisie ──────────────────────────────────────────────────────────────

    def _voice_input(self):
        with self._lock:
            if self._input is None:
                from interfaces.desktop.voice_input import VoiceInput  # pylint: disable=import-outside-toplevel
                self._input = VoiceInput(on_result=self._on_transcript,
                                         on_state=self._on_input_state)
            return self._input

    def toggle_input(self) -> str:
        """Démarre l'enregistrement, ou l'arrête (transcription) ; renvoie l'état."""
        voice = self._voice_input()
        if not voice.available:
            logger.info("[VOICE] %s", voice.unavailable_reason())
            self._on_input_state("error", INPUT_UNAVAILABLE)
            return "error"
        voice.toggle()
        return voice.state

    def stop_input(self) -> None:
        """Arrête l'enregistrement en cours (sa transcription suit)."""
        voice = self._input
        if voice is not None and voice.recording:
            voice.stop()

    def _on_input_state(self, state: str, message: str = "") -> None:
        with self._lock:
            self._input_state = state
        self._publish("voice.input", {"state": state, "message": message})
        if state == "error":
            # Comme le bouton Tk : l'erreur se signale, puis le micro redevient disponible
            threading.Timer(1.5, self._reset_input_error).start()

    def _reset_input_error(self) -> None:
        with self._lock:
            if self._input_state != "error":
                return
            self._input_state = "idle"
        self._publish("voice.input", {"state": "idle", "message": ""})

    def _on_transcript(self, text: str) -> None:
        if text:
            self._publish("voice.transcript", {"text": text})

    # ── Lecture ─────────────────────────────────────────────────────────────

    def _voice_output(self):
        with self._lock:
            if self._output is None:
                from interfaces.desktop.voice_output import VoiceOutput  # pylint: disable=import-outside-toplevel
                self._output = VoiceOutput()
            return self._output

    def speak(self, text: str, key: Optional[str] = None) -> str:
        """Lit un texte à voix haute (Markdown, code et liens retirés) ; renvoie l'état."""
        voice = self._voice_output()
        if not voice.available:
            self._on_output_state("error", key, OUTPUT_UNAVAILABLE)
            return "error"
        if voice.is_speaking:
            voice.stop()
        with self._lock:
            self._speaking_key = key
        voice.speak(text, on_state=lambda state: self._on_output_state(state, key))
        return "speaking"

    def toggle_speak(self, text: str, key: Optional[str] = None) -> str:
        """Bouton de lecture d'une réponse : arrête sa lecture, ou la lance."""
        with self._lock:
            reading_this = self._output_state == "speaking" and self._speaking_key == key
        if reading_this:
            self.stop_speaking()
            return "idle"
        return self.speak(text, key)

    def stop_speaking(self) -> None:
        """Coupe la lecture en cours."""
        voice = self._output
        if voice is not None:
            voice.stop()

    def _on_output_state(self, state: str, key: Optional[str], message: str = "") -> None:
        with self._lock:
            # Fin d'une lecture remplacée par une autre : son état ne compte plus
            if key != self._speaking_key and state != "error":
                return
            self._output_state = state
            if state != "speaking":
                self._speaking_key = None
        if state == "error" and not message:
            message = OUTPUT_UNAVAILABLE  # comme le bouton 🔇 de Tk
        self._publish("voice.output", {"state": state, "key": key, "message": message})

    # ── Arrêt ───────────────────────────────────────────────────────────────

    def shutdown(self) -> None:
        """Arrête micro, lecture et worker Whisper (fermeture de l'appli)."""
        self.stop_input()
        self.stop_speaking()
        if self._input is not None:
            try:
                from interfaces.desktop.voice_input import _WhisperWorker  # pylint: disable=import-outside-toplevel
                _WhisperWorker.get().stop()
            except Exception:  # pylint: disable=broad-except
                pass
