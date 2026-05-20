"""Voice input (speech-to-text) via faster-whisper + sounddevice.

Lazy-loads the Whisper model on first use so app startup stays fast.
Recording happens in a background thread; transcription too.
The main thread is only touched via a Tk-safe callback (`on_result`).
"""

from __future__ import annotations

import threading
import time
import tkinter as tk
from typing import Callable, Optional

try:
    import numpy as np
    import sounddevice as sd
    _AUDIO_OK = True
    _AUDIO_ERR = None
except Exception as _e:  # pragma: no cover - environment-dependent
    _AUDIO_OK = False
    _AUDIO_ERR = _e

try:
    from faster_whisper import WhisperModel
    _WHISPER_OK = True
    _WHISPER_ERR = None
except Exception as _e:  # pragma: no cover - environment-dependent
    _WHISPER_OK = False
    _WHISPER_ERR = _e


SAMPLE_RATE = 16000
CHANNELS = 1
MODEL_SIZE = "small"  # ~150 MB, bon compromis qualité/poids


class VoiceInput:
    """Toggle-based voice input. Call `toggle()` to start/stop.

    on_result(text)  -> called from the main Tk thread with the transcribed text
    on_state(state)  -> called from the main Tk thread when state changes
                        state ∈ {"idle", "recording", "transcribing", "error"}
    tk_root          -> any Tk widget, used to marshal callbacks via .after()
    """

    _model: Optional["WhisperModel"] = None
    _model_lock = threading.Lock()
    _shared_instance: Optional["VoiceInput"] = None

    def __init__(
        self,
        tk_root,
        on_result: Callable[[str], None],
        on_state: Callable[[str], None] = lambda _s: None,
    ):
        self.tk_root = tk_root
        self.on_result = on_result
        self.on_state = on_state
        self._recording = False
        self._frames: list = []
        self._stream: Optional["sd.InputStream"] = None
        self._state = "idle"

    @property
    def state(self) -> str:
        """Current state: "idle", "recording", "transcribing", or "error"."""
        return self._state

    @property
    def available(self) -> bool:
        """True if the required dependencies are available and the microphone can be accessed."""
        return _AUDIO_OK and _WHISPER_OK

    def unavailable_reason(self) -> str:
        """Returns a user-friendly string explaining why voice input is unavailable, if it is."""
        if not _AUDIO_OK:
            return f"sounddevice indisponible : {_AUDIO_ERR}"
        if not _WHISPER_OK:
            return f"faster-whisper indisponible : {_WHISPER_ERR}"
        return ""

    # ── State transitions (marshalled to Tk thread) ─────────────────────
    def _set_state(self, state: str) -> None:
        self._state = state
        try:
            self.tk_root.after(0, lambda s=state: self.on_state(s))
        except Exception:
            pass

    def _deliver(self, text: str) -> None:
        try:
            self.tk_root.after(0, lambda t=text: self.on_result(t))
        except Exception:
            pass

    # ── Public API ──────────────────────────────────────────────────────
    def toggle(self) -> None:
        """Toggle recording on/off. If starting, will stop any ongoing recording first."""
        if not self.available:
            self._set_state("error")
            return
        if self._recording:
            self.stop()
        else:
            self.start()

    def start(self) -> None:
        """Start recording. No-op if already recording."""
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
        except Exception as e:
            print(f"⚠️ [VOICE] Erreur ouverture micro : {e}")
            self._set_state("error")

    def stop(self) -> None:
        """Stop recording. No-op if not currently recording."""
        if not self._recording:
            return
        self._recording = False
        try:
            if self._stream is not None:
                self._stream.stop()
                self._stream.close()
        except Exception as e:
            print(f"⚠️ [VOICE] Erreur arrêt micro : {e}")
        finally:
            self._stream = None

        self._set_state("transcribing")
        threading.Thread(target=self._transcribe_async, daemon=True).start()

    # ── Internal ────────────────────────────────────────────────────────
    def _on_audio(self, indata, _frames, _time_info, status) -> None:
        if status:
            # underrun/overrun ; on continue
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

            model = self._get_model()
            t0 = time.time()
            segments, info = model.transcribe(
                audio,
                language=None,  # auto-détection
                vad_filter=True,
                beam_size=1,
            )
            text = " ".join(seg.text.strip() for seg in segments).strip()
            dt = time.time() - t0
            print(f"🎙️  [VOICE] {info.language} ({info.language_probability:.0%}) "
                  f"en {dt:.1f}s : {text!r}")
            if text:
                self._deliver(text)
        except Exception as e:
            print(f"⚠️ [VOICE] Erreur transcription : {e}")
            self._set_state("error")
            return
        finally:
            if self._state == "transcribing":
                self._set_state("idle")

    @classmethod
    def get_shared(cls, tk_root) -> "VoiceInput":
        """Retourne (et crée si besoin) l'instance partagée de l'application.

        Singleton : l'app n'a qu'un Tk root, et un seul enregistrement actif
        à la fois — une instance suffit.
        """
        if cls._shared_instance is None:
            cls._shared_instance = cls(tk_root=tk_root, on_result=lambda _t: None)
        return cls._shared_instance

    @classmethod
    def _get_model(cls) -> "WhisperModel":
        if cls._model is not None:
            return cls._model
        with cls._model_lock:
            if cls._model is None:
                print(f"🎙️  [VOICE] Chargement Whisper '{MODEL_SIZE}' (premier appel)...")
                cls._model = WhisperModel(
                    MODEL_SIZE,
                    device="cpu",
                    compute_type="int8",
                )
                print("🎙️  [VOICE] Whisper prêt.")
        return cls._model


def attach_mic_button(
    parent,
    tk_root,
    target_getter: Callable[[], object],
    colors: dict,
    show_notification: Optional[Callable[[str, str, int], None]] = None,
):
    """Crée un bouton micro (overlay haut-droite) sur `parent`.

    parent             : frame Tk où placer le bouton (en overlay via .place())
    tk_root            : root window (pour .after() et instance VoiceInput partagée)
    target_getter      : callable retournant le widget Text/CTkTextbox cible
                         (résolu au moment du clic, pour gérer le hot-swap d'écran)
    colors             : dict de couleurs (placeholder, input_bg, accent)
    show_notification  : callable(msg, level, duration_ms) si dispo, sinon print

    Retourne le widget label créé.
    """
    ph_color = colors.get("placeholder", "#6b7280")
    input_bg = colors.get("input_bg", "#2f2f2f")
    rec_color = "#e74c3c"
    rec_dim = "#7a2a23"
    busy_color = colors.get("accent", "#ff6b47")

    mic_label = tk.Label(
        parent,
        text="\U0001F399",
        font=("Segoe UI Emoji", 13),
        fg=ph_color,
        bg=input_bg,
        cursor="hand2",
        padx=6,
        pady=2,
    )

    def _place(_event=None):
        mic_label.place(relx=1.0, rely=0.0, anchor="ne", x=-8, y=4)
        mic_label.lift()

    parent.after_idle(_place)
    parent.bind("<Configure>", _place, add="+")

    pulse_state = {"on": False, "bright": True}

    def _pulse():
        if not pulse_state["on"]:
            return
        try:
            mic_label.configure(fg=rec_color if pulse_state["bright"] else rec_dim)
        except tk.TclError:
            return
        pulse_state["bright"] = not pulse_state["bright"]
        tk_root.after(500, _pulse)

    placeholder_color = colors.get("placeholder", "#6b7280")
    text_primary = colors.get("text_primary", "#ffffff")

    def _has_placeholder_color(widget) -> bool:
        """Detecte si le widget affiche actuellement le placeholder (par couleur)."""
        for attr in ("text_color", "fg"):
            try:
                color = widget.cget(attr)
            except (tk.TclError, AttributeError, ValueError):
                continue
            # CTk renvoie parfois un tuple (light, dark) ; on prend la couleur dark
            if isinstance(color, (list, tuple)):
                color = color[-1] if color else ""
            if str(color).lower() == placeholder_color.lower():
                return True
        return False

    def _clear_placeholder(widget) -> None:
        try:
            widget.delete("1.0", "end")
        except tk.TclError:
            pass
        for attr in ("text_color", "fg"):
            try:
                widget.configure(**{attr: text_primary})
                break
            except (tk.TclError, ValueError):
                continue

    def _do_insert(widget, text: str) -> None:
        try:
            pos = widget.index("insert")
            needs_space = False
            try:
                prev = widget.get(f"{pos} -1 chars", pos)
                if prev and not prev.isspace():
                    needs_space = True
            except tk.TclError:
                pass
            widget.insert("insert", (" " if needs_space else "") + text)
        except tk.TclError as e:
            print(f"[VOICE] insertion impossible : {e}")

    def _insert_at_cursor(text: str):
        widget = target_getter()
        if widget is None:
            return
        # On focus tout de suite (declenche <FocusIn> natif en background)
        try:
            widget.focus_set()
        except tk.TclError:
            pass
        # Si le placeholder est visible (couleur grise), on le nettoie nous-meme.
        # Cela couvre les deux types de placeholders (chat home + agents) sans
        # dependre des bindings internes qui ne sont pas synchrones.
        if _has_placeholder_color(widget):
            _clear_placeholder(widget)
        # Differer l'insert de quelques ms pour laisser le binding <FocusIn>
        # natif s'executer (sinon il pourrait wipe notre texte juste apres) :
        # - cas chat home : _hide_ph deletes everything si _ph_active flag est True
        # - cas agents : on_focus_in no-op si contenu != placeholder, donc OK
        # 50 ms est imperceptible pour l'utilisateur.
        tk_root.after(50, lambda: _do_insert(widget, text))

    def _on_state(state: str):
        if state == "recording":
            mic_label.configure(text="●", fg=rec_color)
            pulse_state["on"] = True
            pulse_state["bright"] = True
            tk_root.after(500, _pulse)
        elif state == "transcribing":
            pulse_state["on"] = False
            mic_label.configure(text="⏳", fg=busy_color)
        elif state == "error":
            pulse_state["on"] = False
            mic_label.configure(text="\U0001F399", fg=rec_color)
            tk_root.after(1500, lambda: mic_label.configure(fg=ph_color))
        else:  # idle
            pulse_state["on"] = False
            mic_label.configure(text="\U0001F399", fg=ph_color)

    vi = VoiceInput.get_shared(tk_root)

    # État activé/désactivé du bouton (désactivé pendant que le LLM écrit).
    enabled_state = {"on": True}
    disabled_color = "#3a3a3a"

    def _on_click(_event=None):
        if not enabled_state["on"]:
            return
        if not vi.available:
            reason = vi.unavailable_reason()
            print(f"[VOICE] {reason}")
            msg = "Saisie vocale indisponible : installe 'faster-whisper' et 'sounddevice'."
            if callable(show_notification):
                try:
                    show_notification(msg, "error", 3000)
                except Exception:
                    pass
            return
        # Réassigner les handlers (l'écran/onglet actif peut avoir changé)
        vi.on_result = _insert_at_cursor
        vi.on_state = _on_state
        vi.toggle()

    def set_enabled(enabled: bool) -> None:
        """Active/désactive le bouton micro (clic + apparence visuelle)."""
        enabled_state["on"] = bool(enabled)
        try:
            if enabled:
                mic_label.configure(cursor="hand2")
                # Restaure l'apparence idle si on n'est pas en cours d'enregistrement
                if vi.state == "idle":
                    mic_label.configure(text="\U0001F399", fg=ph_color)
            else:
                # Si un enregistrement est en cours, l'arrêter proprement.
                if vi._recording:
                    vi.stop()
                pulse_state["on"] = False
                mic_label.configure(
                    text="\U0001F399", fg=disabled_color, cursor="arrow"
                )
        except tk.TclError:
            pass

    mic_label.set_enabled = set_enabled  # type: ignore[attr-defined]
    mic_label.bind("<Button-1>", _on_click)
    return mic_label
