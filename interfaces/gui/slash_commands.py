"""Mixin : autocomplétion des slash commands dans les zones de saisie.

Quand l'utilisateur tape « / » en tout début de saisie, un menu déroulant
apparaît avec les slash commands correspondantes (issues de la bibliothèque de
prompts). La sélection insère le contenu du template dans la zone de saisie et
positionne le curseur sur le premier placeholder `{nom}` pour le compléter.

Le menu est un `Toplevel(overrideredirect)` non focusable (mêmes fondations que
les menus « + » de layout.py / base.py) : l'utilisateur garde le focus sur la
saisie et navigue au clavier (↑/↓, Entrée/Tab, Échap) ou à la souris.

Réutilisable pour les deux zones de saisie (chat principal et écran d'accueil)
via `_attach_slash_autocomplete`.
"""

from __future__ import annotations

import re
import tkinter as tk

# Déclencheur : « / » en tout début de saisie, suivi d'un mot sans espace.
_SLASH_RE = re.compile(r"^/(\S*)$")

# Touches de navigation : elles ne doivent pas reconstruire le menu.
_NAV_KEYS = {"Up", "Down", "Tab", "Escape", "Return", "Left", "Right"}

_MAX_ROWS = 8  # nombre maximal de suggestions affichées


class SlashCommandsMixin:
    """Autocomplétion « / » + insertion de templates dans la saisie."""

    # ------------------------------------------------------------------
    # Accès à la bibliothèque de prompts
    # ------------------------------------------------------------------

    def _get_prompt_library(self):
        """Retourne la PromptLibrary (via l'AIEngine, sinon une instance locale)."""
        lib = getattr(getattr(self, "ai_engine", None), "prompt_library", None)
        if lib is not None:
            return lib
        if getattr(self, "_fallback_prompt_library", None) is None:
            try:
                from core.prompt_library import PromptLibrary
                self._fallback_prompt_library = PromptLibrary()
            except Exception:
                self._fallback_prompt_library = None
        return self._fallback_prompt_library

    # ------------------------------------------------------------------
    # Attache
    # ------------------------------------------------------------------

    def _attach_slash_autocomplete(self, textbox):
        """Active l'autocomplétion « / » sur une zone de saisie (CTkTextbox/tk.Text)."""
        if textbox is None:
            return
        # Sur CTkTextbox, le vrai widget Tk est `_textbox` : on s'y attache pour
        # garder un contrôle fin du curseur, des tags et de la propagation.
        inner = getattr(textbox, "_textbox", textbox)
        try:
            inner.bind(
                "<KeyRelease>",
                lambda e, tb=textbox: self._slash_on_keyrelease(e, tb),
                add="+",
            )
            inner.bind("<Up>", self._slash_on_up, add="+")
            inner.bind("<Down>", self._slash_on_down, add="+")
            inner.bind("<Tab>", self._slash_on_tab, add="+")
            inner.bind("<Escape>", self._slash_on_escape, add="+")
            inner.bind("<FocusOut>", self._slash_on_focusout, add="+")
        except (tk.TclError, AttributeError):
            pass

    # ------------------------------------------------------------------
    # État
    # ------------------------------------------------------------------

    def _slash_get_state(self):
        state = getattr(self, "_slash_state", None)
        if state is None:
            state = {
                "popup": None, "items": [], "index": 0,
                "textbox": None, "inner": None, "rows": [],
            }
            self._slash_state = state
        return state

    def _slash_is_open(self):
        state = getattr(self, "_slash_state", None)
        return bool(state and state.get("popup") is not None)

    # ------------------------------------------------------------------
    # Détection / mise à jour
    # ------------------------------------------------------------------

    def _slash_on_keyrelease(self, event, textbox):
        if event.keysym in _NAV_KEYS:
            return None
        lib = self._get_prompt_library()
        inner = getattr(textbox, "_textbox", textbox)
        try:
            full = inner.get("1.0", "end-1c")
        except (tk.TclError, AttributeError):
            return None
        match = _SLASH_RE.match(full)
        if not match or lib is None:
            self._slash_hide_popup()
            return None
        try:
            matches = lib.search(match.group(1))
        except Exception:
            matches = []
        if not matches:
            self._slash_hide_popup()
            return None
        self._slash_show_popup(textbox, inner, matches[:_MAX_ROWS])
        return None

    # ------------------------------------------------------------------
    # Popup
    # ------------------------------------------------------------------

    def _slash_show_popup(self, textbox, inner, items):
        state = self._slash_get_state()
        self._slash_hide_popup()  # reconstruction simple (évite la désync)

        bg = self.colors.get("bg_secondary", "#2f2f2f")
        fg = self.colors.get("text_primary", "#ffffff")
        sub = self.colors.get("text_secondary", "#9ca3af")
        border = self.colors.get("border", "#404040")

        popup = tk.Toplevel(self.root)
        popup.overrideredirect(True)
        popup.configure(bg=border)
        popup.attributes("-topmost", True)

        inner_frame = tk.Frame(popup, bg=bg)
        inner_frame.pack(fill="both", expand=True, padx=1, pady=1)

        rows = []
        for i, item in enumerate(items):
            cmd = item.get("command", "") or ""
            title = item.get("title", "") or ""
            row = tk.Label(
                inner_frame,
                text=f"  /{cmd}   ·   {title}",
                bg=bg, fg=fg, font=("Segoe UI", 11),
                anchor="w", padx=10, pady=6, cursor="hand2",
            )
            row.grid(row=i, column=0, sticky="ew")
            inner_frame.grid_columnconfigure(0, weight=1, minsize=260)
            row.bind("<Button-1>", lambda _e, it=item: self._slash_accept(it))
            row.bind("<Enter>", lambda _e, idx=i: self._slash_set_index(idx))
            rows.append(row)

        state.update({
            "popup": popup, "items": items, "index": 0,
            "textbox": textbox, "inner": inner, "rows": rows,
        })
        self._slash_highlight()

        # Positionner au-dessus de la zone de saisie (input proche du bas).
        try:
            popup.update_idletasks()
            px = inner.winfo_rootx()
            py = inner.winfo_rooty()
            ph = popup.winfo_reqheight()
            y = py - ph - 4
            if y < 0:  # pas de place au-dessus → afficher en dessous
                y = py + inner.winfo_height() + 4
            popup.geometry(f"+{px}+{y}")
        except (tk.TclError, AttributeError):
            pass

    def _slash_highlight(self):
        state = self._slash_get_state()
        rows = state.get("rows", [])
        index = state.get("index", 0)
        bg = self.colors.get("bg_secondary", "#2f2f2f")
        fg = self.colors.get("text_primary", "#ffffff")
        accent = self.colors.get("accent", "#ff6b47")
        for i, row in enumerate(rows):
            try:
                if i == index:
                    row.configure(bg=accent, fg="#ffffff")
                else:
                    row.configure(bg=bg, fg=fg)
            except tk.TclError:
                pass

    def _slash_set_index(self, index):
        state = self._slash_get_state()
        if state.get("popup") is None:
            return
        items = state.get("items", [])
        if 0 <= index < len(items):
            state["index"] = index
            self._slash_highlight()

    def _slash_move(self, delta):
        state = self._slash_get_state()
        items = state.get("items", [])
        if not items:
            return
        state["index"] = (state.get("index", 0) + delta) % len(items)
        self._slash_highlight()

    def _slash_hide_popup(self):
        state = getattr(self, "_slash_state", None)
        if not state:
            return
        popup = state.get("popup")
        if popup is not None:
            try:
                popup.destroy()
            except tk.TclError:
                pass
        state["popup"] = None
        state["items"] = []
        state["rows"] = []
        state["index"] = 0

    # ------------------------------------------------------------------
    # Navigation clavier
    # ------------------------------------------------------------------

    def _slash_on_up(self, _event):
        if self._slash_is_open():
            self._slash_move(-1)
            return "break"
        return None

    def _slash_on_down(self, _event):
        if self._slash_is_open():
            self._slash_move(1)
            return "break"
        return None

    def _slash_on_tab(self, _event):
        if self._slash_is_open():
            self._slash_accept_current()
            return "break"
        return None

    def _slash_on_escape(self, _event):
        if self._slash_is_open():
            self._slash_hide_popup()
            return "break"
        return None

    def _slash_on_focusout(self, _event):
        # Léger délai : un clic sur une ligne déclenche un FocusOut transitoire.
        try:
            self.root.after(200, self._slash_hide_popup)
        except (tk.TclError, AttributeError):
            self._slash_hide_popup()

    def _slash_popup_consume_enter(self):
        """Appelé par on_enter_key / _on_home_enter : valide la suggestion si le
        menu est ouvert (et renvoie True pour empêcher l'envoi du message)."""
        if not self._slash_is_open():
            return False
        self._slash_accept_current()
        return True

    def _slash_accept_current(self):
        state = self._slash_get_state()
        items = state.get("items", [])
        index = state.get("index", 0)
        if 0 <= index < len(items):
            self._slash_accept(items[index])
        else:
            self._slash_hide_popup()

    # ------------------------------------------------------------------
    # Insertion du template
    # ------------------------------------------------------------------

    def _slash_accept(self, item):
        """Remplace le « /cmd » tapé par le contenu du template et place le curseur."""
        state = self._slash_get_state()
        textbox = state.get("textbox")
        inner = state.get("inner")
        if inner is None:
            self._slash_hide_popup()
            return
        content = item.get("content", "") or ""
        try:
            inner.delete("1.0", "end")
            inner.insert("1.0", content)
        except (tk.TclError, AttributeError):
            self._slash_hide_popup()
            return

        # Couleur de texte normale + neutraliser l'état placeholder.
        try:
            if getattr(self, "use_ctk", False) and textbox is not None:
                textbox.configure(text_color=self.colors.get("text_primary", "#ffffff"))
            else:
                inner.configure(fg=self.colors.get("text_primary", "#ffffff"))
        except (tk.TclError, AttributeError):
            pass
        if textbox is getattr(self, "input_text", None):
            self.placeholder_active = False

        # Placer le curseur sur le premier placeholder {nom} (sélectionné).
        placed = False
        try:
            from core.prompt_library import PromptLibrary
            placeholders = PromptLibrary.extract_placeholders(content)
        except Exception:
            placeholders = []
        if placeholders:
            needle = "{" + placeholders[0] + "}"
            try:
                idx = inner.search(needle, "1.0", stopindex="end")
                if idx:
                    end = f"{idx}+{len(needle)}c"
                    inner.tag_remove("sel", "1.0", "end")
                    inner.tag_add("sel", idx, end)
                    inner.mark_set("insert", idx)
                    inner.see(idx)
                    placed = True
            except (tk.TclError, AttributeError):
                pass
        if not placed:
            try:
                inner.mark_set("insert", "end")
                inner.see("end")
            except (tk.TclError, AttributeError):
                pass

        self._slash_hide_popup()
        try:
            inner.focus_set()
        except (tk.TclError, AttributeError):
            pass
