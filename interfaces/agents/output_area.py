"""Mixin : construction de la zone de résultats scrollable (sections dépliantes)."""

from interfaces.agents._common import ctk, tk


class OutputAreaMixin:
    """Construction du conteneur scrollable des sections de résultats."""

    def create_output_area(self, parent):
        """Crée la zone de sortie des résultats avec sections dépliantes."""
        section_frame = self.create_frame(parent, fg_color=self.colors["bg_primary"])
        section_frame.grid(row=4, column=0, sticky="nsew", padx=30, pady=(20, 10))

        # Titre
        title = self.create_label(
            section_frame,
            text="📄 Résultats",
            font=("Segoe UI", 14, "bold"),
            text_color=self.colors["text_primary"],
            fg_color=self.colors["bg_primary"],
        )
        title.pack(anchor="w", pady=(0, 10))

        # Scrollable frame pour les sections
        if self.use_ctk:
            self._output_scroll = ctk.CTkScrollableFrame(
                section_frame,
                fg_color=self.colors["bg_primary"],
                corner_radius=10,
                border_width=2,
                border_color=self.colors["border"],
                scrollbar_button_color=self.colors.get("bg_tertiary", "#2d2d2d"),
                scrollbar_button_hover_color=self.colors.get("text_secondary", "#9ca3af"),
                height=500,
            )
        else:
            self._output_scroll = tk.Frame(
                section_frame, bg=self.colors["bg_primary"]
            )
        self._output_scroll.pack(fill="both", expand=True)

        # Forcer un padding droit sur la scrollbar pour que le bord droit du CTkScrollableFrame soit visible
        try:
            if hasattr(self._output_scroll, '_scrollbar') and hasattr(self._output_scroll, '_parent_frame'):
                # pylint: disable=protected-access
                parent_frame = self._output_scroll._parent_frame
                border_sp = parent_frame.cget("corner_radius") + parent_frame.cget("border_width")
                self._output_scroll._scrollbar.grid_configure(padx=(0, border_sp))
        except Exception:
            pass

        # Empêcher le double-scroll: capturer le mousewheel dans la zone de résultats
        self._bind_scroll_isolation(self._output_scroll)

        self._output_sections = []
        self._active_section = None

        # Message de bienvenue
        self._welcome_label = self.create_label(
            self._output_scroll,
            text=(
                "Bienvenue dans le système d'agents spécialisés !\n\n"
                "1️ Décrivez votre tâche\n"
                "2️ Configurez votre workflow\n"
                "3️ Cliquez sur \"Exécuter\"\n\n"
                "Les résultats apparaîtront ici en temps réel."
            ),
            font=("Segoe UI", 11),
            text_color=self.colors["text_secondary"],
            fg_color=self.colors["bg_primary"],
        )
        if self.use_ctk:
            self._welcome_label.configure(wraplength=800, justify="left")
        self._welcome_label.pack(anchor="w", padx=16, pady=20)

        # Dummy output_text for backward compat (_make_output_readonly, etc.)
        self.output_text = None

    def _bind_scroll_isolation(self, widget):
        """Isole le scroll d'un CTkScrollableFrame pour ne pas propager au parent."""
        try:
            if not hasattr(widget, '_parent_canvas'):
                return
            canvas = widget._parent_canvas  # pylint: disable=protected-access

            def _on_mousewheel(event):
                # Multiplier par 6 pour une vitesse de scroll normale
                canvas.yview_scroll(int(-6 * (event.delta / 120)), "units")
                return "break"

            canvas.bind("<MouseWheel>", _on_mousewheel)
            # Bind aussi sur tous les enfants SAUF les Text/Scrollbar (qui gèrent leur propre scroll)
            def _bind_children(w):
                try:
                    if not isinstance(w, (tk.Text, tk.Scrollbar)):
                        w.bind("<MouseWheel>", _on_mousewheel)
                except Exception:
                    pass
                for child in w.winfo_children():
                    _bind_children(child)
            # Re-bind à chaque entrée de souris (capture les enfants créés dynamiquement)
            widget.bind("<Enter>", lambda e: _bind_children(widget))
        except Exception:
            pass
