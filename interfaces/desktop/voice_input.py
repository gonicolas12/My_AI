"""
Saisie vocale (parole → texte) : faster-whisper et sounddevice, 100 % locale

Le modèle Whisper n'est chargé qu'au premier usage : le lancement de l'appli
reste rapide. L'enregistrement et la transcription tournent dans des fils de
travail ; les rappels (texte dicté, état) partent de ces fils, ou passent par
l'interface Tk quand elle est donnée (`ui`, sa méthode .after).

Déplacé de interfaces/gui/voice_input.py, qui n'y garde que le bouton micro de
l'interface Tk (supprimée en phase 5 de la migration web).
"""

from __future__ import annotations

import atexit
import json
import os
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Callable, Optional

try:
    import numpy as np
    import sounddevice as sd
    _AUDIO_OK = True
    _AUDIO_ERR = None
except Exception as _e:  # pragma: no cover - selon l'environnement
    _AUDIO_OK = False
    _AUDIO_ERR = _e

try:
    from faster_whisper import WhisperModel
    _WHISPER_OK = True
    _WHISPER_ERR = None
except Exception as _e:  # pragma: no cover - selon l'environnement
    _WHISPER_OK = False
    _WHISPER_ERR = _e


SAMPLE_RATE = 16000
CHANNELS = 1
MODEL_SIZE = "small"  # ~150 Mo, bon compromis qualité/poids
COMPUTE_TYPE = "int8"

_WORKER_PATH = Path(__file__).with_name("_whisper_worker.py")

# Forçage manuel du mode, utile pour tester le worker hors macOS :
#   MY_AI_WHISPER_WORKER=1  -> toujours le process isolé
#   MY_AI_WHISPER_WORKER=0  -> toujours en process
_WORKER_ENV = "MY_AI_WHISPER_WORKER"


def _openmp_runtimes() -> list:
    """Runtimes OpenMP chargés dans ce process (macOS uniquement).

    ctranslate2, torch et scikit-learn embarquent chacun le leur dans leurs
    ``.dylibs``. Au-delà d'un seul, le pool de threads de ctranslate2 segfaulte
    (``EXC_BAD_ACCESS`` dans ``__kmp_fork_barrier``) sans le message
    ``OMP: Error #15`` habituel : sklearn et threadpoolctl posent
    ``KMP_DUPLICATE_LIB_OK=True`` à l'import, ce qui remplace l'abort explicite
    par un crash muet.

    Voir ``_whisper_worker.py`` pour le détail : torch est inévitable, puisque
    ctranslate2 l'importe lui-même ; c'est ``libomp`` (LLVM), apporté par
    scikit-learn, qui fait la différence.
    """
    if sys.platform != "darwin":
        return []
    try:
        import ctypes  # pylint: disable=import-outside-toplevel

        libc = ctypes.CDLL(None)
        libc._dyld_image_count.restype = ctypes.c_uint32  # pylint: disable=protected-access
        libc._dyld_get_image_name.restype = ctypes.c_char_p  # pylint: disable=protected-access
        libc._dyld_get_image_name.argtypes = [ctypes.c_uint32]  # pylint: disable=protected-access

        found = []
        for i in range(libc._dyld_image_count()):  # pylint: disable=protected-access
            raw = libc._dyld_get_image_name(i)  # pylint: disable=protected-access
            if not raw:
                continue
            base = os.path.basename(raw.decode("utf-8", "replace"))
            if base.startswith(("libiomp5", "libomp", "libgomp")):
                found.append(base)
        return found
    except Exception:  # pylint: disable=broad-except
        return []


def _needs_isolation() -> bool:
    """True si Whisper doit tourner dans un process séparé."""
    forced = os.environ.get(_WORKER_ENV)
    if forced is not None:
        return forced.strip() not in ("", "0", "false", "False")
    return len(_openmp_runtimes()) > 1


class _WhisperWorker:
    """Client du process de transcription isolé (voir ``_whisper_worker.py``).

    Le process est persistant : le modèle n'est chargé qu'une fois, et les
    transcriptions suivantes ne paient que le transfert de l'audio.
    """

    _instance: Optional["_WhisperWorker"] = None
    _singleton_lock = threading.Lock()

    def __init__(self):
        self._proc: Optional[subprocess.Popen] = None
        self._io_lock = threading.Lock()

    @classmethod
    def get(cls) -> "_WhisperWorker":
        """Instance partagée."""
        with cls._singleton_lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    def _ensure_process(self) -> subprocess.Popen:
        if self._proc is not None and self._proc.poll() is None:
            return self._proc
        if not _WORKER_PATH.exists():
            raise RuntimeError(f"worker introuvable : {_WORKER_PATH}")

        kwargs = {
            "stdin": subprocess.PIPE,
            "stdout": subprocess.PIPE,
            # stderr hérité : les journaux du worker arrivent dans la console.
        }
        if sys.platform == "win32":
            kwargs["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        else:
            kwargs["start_new_session"] = True

        # Lancé PAR CHEMIN : comme module d'un paquet, il exécuterait ses
        # __init__.py (cf. la docstring du worker)
        self._proc = subprocess.Popen(  # pylint: disable=consider-using-with
            [sys.executable, str(_WORKER_PATH), MODEL_SIZE, COMPUTE_TYPE], **kwargs
        )
        # Sans ça, un parent qui meurt sans fermer le tube laisse le worker
        # bloqué indéfiniment sur readline().
        atexit.register(self.stop)
        return self._proc

    def transcribe(self, audio) -> dict:
        """Envoie l'audio au worker et retourne sa réponse décodée."""
        with self._io_lock:
            proc = self._ensure_process()
            payload = audio.astype(np.float32).tobytes()
            try:
                proc.stdin.write(
                    (json.dumps({"n": int(audio.shape[0])}) + "\n").encode("utf-8")
                )
                proc.stdin.write(payload)
                proc.stdin.flush()
                line = proc.stdout.readline()
            except (BrokenPipeError, OSError) as exc:
                self.stop()
                raise RuntimeError(f"tube rompu : {exc}") from exc

            if not line:
                code = proc.poll()
                self.stop()
                raise RuntimeError(f"worker terminé sans réponse (code {code})")
            return json.loads(line.decode("utf-8"))

    def stop(self) -> None:
        """Ferme le process de transcription."""
        proc, self._proc = self._proc, None
        if proc is None or proc.poll() is not None:
            return
        try:
            if proc.stdin:
                proc.stdin.close()
            proc.wait(timeout=2)
        except Exception:  # pylint: disable=broad-except
            try:
                proc.kill()
            except Exception:  # pylint: disable=broad-except
                pass


class VoiceInput:
    """Saisie vocale à bascule : `toggle()` démarre puis arrête l'enregistrement.

    on_result(texte) -> texte dicté
    on_state(état)   -> changement d'état : idle, recording, transcribing, error
    ui               -> interface Tk (rappels passés par ui.after(0, …)) ;
                        None : rappels appelés depuis le fil de travail
    """

    _model: Optional["WhisperModel"] = None
    _model_single: Optional["WhisperModel"] = None  # repli cpu_threads=1
    _model_lock = threading.Lock()
    _shared_instance: Optional["VoiceInput"] = None

    def __init__(
        self,
        ui=None,
        on_result: Optional[Callable[[str], None]] = None,
        on_state: Optional[Callable[[str], None]] = None,
    ):
        self.ui = ui
        self.on_result = on_result or (lambda _t: None)
        self.on_state = on_state or (lambda _s: None)
        self._recording = False
        self._frames: list = []
        self._stream: Optional["sd.InputStream"] = None
        self._state = "idle"

    @property
    def state(self) -> str:
        """État courant : idle, recording, transcribing ou error."""
        return self._state

    @property
    def recording(self) -> bool:
        """Vrai pendant l'enregistrement."""
        return self._recording

    @property
    def available(self) -> bool:
        """Vrai si le micro (sounddevice) et Whisper (faster-whisper) sont utilisables."""
        return _AUDIO_OK and _WHISPER_OK

    def unavailable_reason(self) -> str:
        """Raison lisible de l'indisponibilité, s'il y a lieu."""
        if not _AUDIO_OK:
            return f"sounddevice indisponible : {_AUDIO_ERR}"
        if not _WHISPER_OK:
            return f"faster-whisper indisponible : {_WHISPER_ERR}"
        return ""

    # ── Rappels (dans le fil de l'interface s'il y en a une) ─────────────
    def _call(self, callback: Callable[[], None]) -> None:
        if self.ui is None:
            try:
                callback()
            except Exception:  # pylint: disable=broad-except
                pass
            return
        try:
            self.ui.after(0, callback)
        except Exception:  # pylint: disable=broad-except
            pass

    def _set_state(self, state: str) -> None:
        self._state = state
        self._call(lambda s=state: self.on_state(s))

    def _deliver(self, text: str) -> None:
        self._call(lambda t=text: self.on_result(t))

    # ── API publique ────────────────────────────────────────────────────
    def toggle(self) -> None:
        """Démarre l'enregistrement, ou l'arrête s'il est en cours."""
        if not self.available:
            self._set_state("error")
            return
        if self._recording:
            self.stop()
        else:
            self.start()

    def start(self) -> None:
        """Démarre l'enregistrement (sans effet s'il est déjà en cours)."""
        if self._recording or not self.available:
            return
        self._frames = []
        try:
            self._stream = sd.InputStream(
                samplerate=SAMPLE_RATE,
                channels=CHANNELS,
                dtype="float32",
                callback=self._on_audio,
            )
            self._stream.start()
            self._recording = True
            self._set_state("recording")
        except Exception as e:  # pylint: disable=broad-except
            print(f"⚠️ [VOICE] Erreur ouverture micro : {e}")
            self._set_state("error")

    def stop(self) -> None:
        """Arrête l'enregistrement et lance la transcription."""
        if not self._recording:
            return
        self._recording = False
        try:
            if self._stream is not None:
                self._stream.stop()
                self._stream.close()
        except Exception as e:  # pylint: disable=broad-except
            print(f"⚠️ [VOICE] Erreur arrêt micro : {e}")
        finally:
            self._stream = None

        self._set_state("transcribing")
        threading.Thread(target=self._transcribe_async, daemon=True).start()

    # ── Interne ─────────────────────────────────────────────────────────
    def _on_audio(self, indata, _frames, _time_info, status) -> None:
        if status:
            # débordement du tampon audio : on continue
            pass
        self._frames.append(indata.copy())

    def _transcribe_async(self) -> None:
        try:
            if not self._frames:
                self._set_state("idle")
                return

            audio = np.concatenate(self._frames, axis=0).flatten().astype(np.float32)
            # Trop court (< 0.3 s) : on ignore
            if audio.shape[0] < int(SAMPLE_RATE * 0.3):
                self._set_state("idle")
                return

            t0 = time.time()
            if _needs_isolation():
                try:
                    reply = _WhisperWorker.get().transcribe(audio)
                    if reply.get("error"):
                        raise RuntimeError(reply["error"])
                    text = reply["text"]
                    lang = reply["language"]
                    prob = reply["language_probability"]
                except Exception as exc:  # pylint: disable=broad-except
                    # Dernier recours : en process mais mono-thread. Plus lent
                    # (~1.8x), seule configuration qui ne segfault pas quand
                    # plusieurs runtimes OpenMP cohabitent.
                    print(f"⚠️ [VOICE] Process isolé indisponible ({exc}) "
                          f"— repli mono-thread")
                    text, lang, prob = self._transcribe_here(audio, single_thread=True)
            else:
                text, lang, prob = self._transcribe_here(audio, single_thread=False)
            dt = time.time() - t0
            print(f"🎙️  [VOICE] {lang} ({prob:.0%}) en {dt:.1f}s : {text!r}")
            if text:
                self._deliver(text)
        except Exception as e:  # pylint: disable=broad-except
            print(f"⚠️ [VOICE] Erreur transcription : {e}")
            self._set_state("error")
            return
        finally:
            if self._state == "transcribing":
                self._set_state("idle")

    @classmethod
    def get_shared(cls, ui=None) -> "VoiceInput":
        """Instance partagée de l'appli : un seul enregistrement à la fois."""
        if cls._shared_instance is None:
            cls._shared_instance = cls(ui=ui)
        return cls._shared_instance

    def _transcribe_here(self, audio, single_thread: bool = False) -> tuple:
        """Transcrit dans ce process. Retourne (texte, langue, probabilité)."""
        model = self._get_model(single_thread=single_thread)
        segments, info = model.transcribe(
            audio,
            language=None,  # auto-détection
            vad_filter=True,
            beam_size=1,
        )
        text = " ".join(seg.text.strip() for seg in segments).strip()
        return text, info.language, info.language_probability

    @classmethod
    def _get_model(cls, single_thread: bool = False) -> "WhisperModel":
        cached = cls._model_single if single_thread else cls._model
        if cached is not None:
            return cached
        with cls._model_lock:
            if single_thread:
                if cls._model_single is None:
                    print(f"🎙️  [VOICE] Chargement Whisper '{MODEL_SIZE}' "
                          f"(mono-thread, contournement OpenMP)...")
                    cls._model_single = WhisperModel(
                        MODEL_SIZE,
                        device="cpu",
                        compute_type=COMPUTE_TYPE,
                        cpu_threads=1,
                    )
                    print("🎙️  [VOICE] Whisper prêt (mono-thread).")
                return cls._model_single
            if cls._model is None:
                print(f"🎙️  [VOICE] Chargement Whisper '{MODEL_SIZE}' (premier appel)...")
                cls._model = WhisperModel(
                    MODEL_SIZE,
                    device="cpu",
                    compute_type=COMPUTE_TYPE,
                )
                print("🎙️  [VOICE] Whisper prêt.")
        return cls._model
