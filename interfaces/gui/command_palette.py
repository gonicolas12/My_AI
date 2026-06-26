"""Command palette mixin (Ctrl+K) + raccourcis clavier globaux pour ModernAIGUI.

Fournit une palette type « Ctrl+K » listant les actions principales (nouveau
chat, export, Relay, réglages, navigation d'onglets…) avec recherche filtrante
au clavier, plus un jeu de raccourcis globaux bindés sur la fenêtre racine.

Le mixin est autonome : il ne référence les actions existantes que via getattr,
de sorte qu'une action absente est simplement masquée plutôt que de provoquer
une erreur.
"""

import tkinter as tk

try:
    import customtkinter as ctk

    CTK_AVAILABLE = True
except ImportError:
    CTK_AVAILABLE = False
    ctk = tk


class CommandPaletteMixin:
    """Palette de commandes (Ctrl+K) et raccourcis clavier globaux."""

    # ── Construction de la liste des commandes ─────────────────────────────

    def _build_command_list(self):
        """Construit la liste des commandes disponibles selon le contexte.

        Chaque entrée est un dict ``{"label", "hint", "run"}``. Les actions
        absentes (méthode introuvable) sont ignorées silencieusement.
        """
        cmds = []

        def add(label, hint, attr, *args):
            fn = getattr(self, attr, None)
            if not callable(fn):
                return
            run = (lambda f=fn, a=args: f(*a)) if args else fn
            cmds.append({"label": label, "hint": hint, "run": run})

        add("Nouveau chat", "Ctrl+N", "_session_new")
        add("Effacer le chat", "Ctrl+L", "clear_chat")
        add("Sauvegarder la session", "Ctrl+S", "_session_save_current")
        add("Afficher / masquer la barre latérale", "Ctrl+B", "toggle_sidebar")
        add("Aller à l'onglet Chat", "", "switch_tab", "chat")
        add("Aller à l'onglet Agents", "", "switch_tab", "agents")
        add("Relay (accès mobile)", "Ctrl+R", "_toggle_relay")
        add("Réglages", "Ctrl+,", "open_settings_window")
        add("Mémoire", "", "open_memory_window")
        add("Bibliothèque de prompts", "", "open_prompts_window")
        add("Exporter la conversation (Markdown)", "", "_export_conversation", "markdown")
        add("Exporter la conversation (HTML)", "", "_export_conversation", "html")
        add("Exporter la conversation (PDF)", "", "_export_conversation", "pdf")
        add("Aide", "F1", "show_help")
        return cmds

    # ── Raccourcis clavier globaux ─────────────────────────────────────────

    def setup_command_palette_shortcuts(self):
        """Binde les raccourcis globaux. À appeler après setup_keyboard_shortcuts."""
        root = getattr(self, "root", None)
        if root is None:
            return

        def _bind(seq, attr, *args):
            fn = getattr(self, attr, None)
            if not callable(fn):
                return

            def handler(_e, f=fn, a=args):
                try:
                    f(*a)
                except Exception as exc:  # noqa: BLE001
                    print(f"⚠️ [Palette] Raccourci {seq} échoué : {exc}")
                return "break"

            root.bind(seq, handler)

        # Palette
        root.bind("<Control-k>", lambda e: (self.toggle_command_palette(), "break")[1])
        root.bind("<Control-K>", lambda e: (self.toggle_command_palette(), "break")[1])

        # Actions directes (Ctrl+L est déjà géré dans setup_keyboard_shortcuts)
        _bind("<Control-n>", "_session_new")
        _bind("<Control-N>", "_session_new")
        _bind("<Control-s>", "_session_save_current")
        _bind("<Control-S>", "_session_save_current")
        _bind("<Control-b>", "toggle_sidebar")
        _bind("<Control-B>", "toggle_sidebar")
        _bind("<Control-r>", "_toggle_relay")
        _bind("<Control-R>", "_toggle_relay")
        _bind("<Control-comma>", "open_settings_window")
        _bind("<F1>", "show_help")

    # ── Ouverture / fermeture ──────────────────────────────────────────────

    def toggle_command_palette(self):
        """Ouvre la palette, ou la referme si elle est déjà ouverte."""
        if getattr(self, "_cmd_palette_win", None) is not None:
            self._close_command_palette()
        else:
            self.open_command_palette()

    def _close_command_palette(self):
        win = getattr(self, "_cmd_palette_win", None)
        self._cmd_palette_win = None
        if win is not None:
            try:
                win.destroy()
            except Exception:
                pass

    def open_command_palette(self):
        """Affiche la palette de commandes (overlay centré en haut de la fenêtre)."""
        if getattr(self, "_cmd_palette_win", None) is not None:
            return

        colors = getattr(self, "colors", {})
        bg = colors.get("bg_secondary", "#2f2f2f")
        bg_input = colors.get("input_bg", "#262626")
        fg = colors.get("text_primary", "#ffffff")
        fg_dim = colors.get("text_secondary", "#9ca3af")
        accent = colors.get("accent", "#3b82f6")
        border = colors.get("border", "#404040")

        all_cmds = self._build_command_list()

        win = tk.Toplevel(self.root)
        win.overrideredirect(True)
        win.configure(bg=border)
        win.attributes("-topmost", True)
        self._cmd_palette_win = win

        # État de navigation
        state = {
            "filtered": list(all_cmds), "selected": 0,
            "rows": [], "meta": [], "last_query": None,
        }

        outer = tk.Frame(win, bg=border)
        outer.pack(fill="both", expand=True, padx=1, pady=1)

        # ── Champ de recherche ──
        entry = tk.Entry(
            outer,
            bg=bg_input,
            fg=fg,
            insertbackground=fg,
            relief="flat",
            font=("Segoe UI", 14),
            highlightthickness=0,
            bd=10,
        )
        entry.pack(fill="x", padx=0, pady=0)

        # ── Liste des résultats ──
        list_frame = tk.Frame(outer, bg=bg)
        list_frame.pack(fill="both", expand=True)

        def _execute(index):
            if not state["filtered"]:
                return
            index = max(0, min(index, len(state["filtered"]) - 1))
            cmd = state["filtered"][index]
            self._close_command_palette()
            try:
                cmd["run"]()
            except Exception as exc:  # noqa: BLE001
                print(f"⚠️ [Palette] '{cmd['label']}' a échoué : {exc}")

        def _highlight():
            """Met à jour uniquement les couleurs selon la sélection (pas de rebuild)."""
            for i, (row, lbl, hint_lbl) in enumerate(state["meta"]):
                sel = i == state["selected"]
                row_bg = accent if sel else bg
                try:
                    row.configure(bg=row_bg)
                    lbl.configure(bg=row_bg, fg="#ffffff" if sel else fg)
                    if hint_lbl is not None:
                        hint_lbl.configure(
                            bg=row_bg, fg="#ffffff" if sel else fg_dim
                        )
                except tk.TclError:
                    pass

        def _select(idx):
            state["selected"] = idx
            _highlight()

        def _build_rows():
            """Construit les lignes UNE fois ; le survol ne fait que recolorer."""
            for w in state["rows"]:
                w.destroy()
            state["rows"] = []
            state["meta"] = []
            for i, cmd in enumerate(state["filtered"]):
                row = tk.Frame(list_frame, bg=bg, cursor="hand2")
                row.pack(fill="x")
                lbl = tk.Label(
                    row, text=cmd["label"], bg=bg, fg=fg,
                    font=("Segoe UI", 12), anchor="w", padx=14, pady=7,
                )
                lbl.pack(side="left", fill="x", expand=True)
                hint_lbl = None
                if cmd["hint"]:
                    hint_lbl = tk.Label(
                        row, text=cmd["hint"], bg=bg, fg=fg_dim,
                        font=("Segoe UI", 10), anchor="e", padx=14,
                    )
                    hint_lbl.pack(side="right")

                widgets = [row, lbl] + ([hint_lbl] if hint_lbl else [])
                for w in widgets:
                    w.bind("<Button-1>", lambda _e, idx=i: _execute(idx))
                    w.bind("<Enter>", lambda _e, idx=i: _select(idx))
                state["rows"].append(row)
                state["meta"].append((row, lbl, hint_lbl))
            _highlight()

        def _filter(_e=None):
            query = entry.get().strip().lower()
            # Les touches de navigation (flèches, Entrée…) déclenchent aussi
            # <KeyRelease> sans modifier le texte : ne rien reconstruire alors,
            # sinon la sélection serait réinitialisée à chaque flèche.
            if query == state["last_query"]:
                return
            state["last_query"] = query
            if not query:
                state["filtered"] = list(all_cmds)
            else:
                state["filtered"] = [
                    c for c in all_cmds
                    if query in (c["label"] + " " + c["hint"]).lower()
                ]
            state["selected"] = 0
            _build_rows()

        def _move(delta):
            if not state["filtered"]:
                return "break"
            state["selected"] = (state["selected"] + delta) % len(state["filtered"])
            _highlight()
            return "break"

        entry.bind("<KeyRelease>", _filter)
        entry.bind("<Down>", lambda e: _move(1))
        entry.bind("<Up>", lambda e: _move(-1))
        entry.bind("<Return>", lambda e: (_execute(state["selected"]), "break")[1])
        entry.bind("<Escape>", lambda e: (self._close_command_palette(), "break")[1])
        win.bind("<FocusOut>", lambda e: self.root.after(120, self._close_if_unfocused))

        _build_rows()

        # ── Positionnement : centré horizontalement, ~14% du haut ──
        self.root.update_idletasks()
        win.update_idletasks()
        rw = self.root.winfo_width()
        rh = self.root.winfo_height()
        width = max(480, min(640, rw - 80))
        # Hauteur ajustée au contenu (entrée + lignes), bornée à 80% de l'écran
        content_h = win.winfo_reqheight() + 4
        height = min(content_h, int(self.root.winfo_screenheight() * 0.8))
        rx = self.root.winfo_rootx()
        ry = self.root.winfo_rooty()
        x = rx + (rw - width) // 2
        y = ry + max(60, int(rh * 0.14))
        win.geometry(f"{width}x{height}+{x}+{y}")

        entry.focus_set()

    def _close_if_unfocused(self):
        """Ferme la palette si plus aucun de ses widgets n'a le focus."""
        win = getattr(self, "_cmd_palette_win", None)
        if win is None:
            return
        try:
            focused = win.focus_get()
        except Exception:
            focused = None
        if focused is None:
            self._close_command_palette()
