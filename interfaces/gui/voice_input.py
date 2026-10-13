"""Bouton micro de l'interface Tk (saisie vocale).

La saisie vocale elle-même (sounddevice, faster-whisper, worker isolé) est
dans interfaces/desktop/voice_input.py, partagée avec l'interface web ; ce
module disparaît avec l'interface Tk (phase 5 de la migration web).
"""

from __future__ import annotations

import tkinter as tk
from typing import Callable, Optional

from interfaces.desktop.voice_input import VoiceInput


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
