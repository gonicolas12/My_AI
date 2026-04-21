"""Mixin : grille de cartes d'agents (built-in) + icônes."""


class AgentSelectionMixin:
    """Construction des cartes d'agents et dispatch d'icônes."""

    # ── Icônes des agents ──────────────────────────────────────────
    _AGENT_ICONS = {
        "code": "🐍", "web": "🔍", "analyst": "📊", "creative": "✨",
        "debug": "🐛", "planner": "📋", "security": "🛡",
        "optimizer": "⚡", "datascience": "🧬",
    }

    def create_agent_selection(self, parent):
        """Crée la section de sélection d'agents"""
        section_frame = self.create_frame(parent, fg_color=self.colors["bg_primary"])
        section_frame.grid(row=2, column=0, sticky="ew", padx=30, pady=(0, 10))

        # Agents disponibles
        agents_info = {
            "code": {
                "icon": "🐍",
                "name": "CodeAgent",
                "desc": "Génération et debug de code",
                "color": "#3b82f6",
            },
            "web": {
                "icon": "🔍",
                "name": "WebAgent",
                "desc": "Recherche Internet & Fact-Checking",
                "color": "#10b981",
            },
            "analyst": {
                "icon": "📊",
                "name": "AnalystAgent",
                "desc": "Analyse de données",
                "color": "#8b5cf6",
            },
            "creative": {
                "icon": "✨",
                "name": "CreativeAgent",
                "desc": "Contenu créatif",
                "color": "#f59e0b",
            },
            "debug": {
                "icon": "🐛",
                "name": "DebugAgent",
                "desc": "Debug et correction",
                "color": "#ef4444",
            },
            "planner": {
                "icon": "📋",
                "name": "PlannerAgent",
                "desc": "Planification de projets",
                "color": "#06b6d4",
            },
            "security": {
                "icon": "🛡",
                "name": "SecurityAgent",
                "desc": "Audit de sécurité & vulnérabilités",
                "color": "#ec4899",
            },
            "optimizer": {
                "icon": "⚡",
                "name": "OptimizerAgent",
                "desc": "Optimisation & Performance",
                "color": "#14b8a6",
            },
            "datascience": {
                "icon": "🧬",
                "name": "DataScienceAgent",
                "desc": "Data Science & Machine Learning",
                "color": "#f97316",
            },
        }

        # Mémorise les agents built-in pour le popup Mode Débat
        self._builtin_agents_info = agents_info

        # Grille d'agents (3 par ligne)
        agents_grid = self.create_frame(
            section_frame, fg_color=self.colors["bg_primary"]
        )
        agents_grid.pack(fill="x")
        self.agents_grid = agents_grid

        for idx, (agent_type, info) in enumerate(agents_info.items()):
            row = idx // 3
            col = idx % 3

            agent_card = self.create_agent_card(
                agents_grid,
                agent_type,
                info["icon"],
                info["name"],
                info["desc"],
                info["color"],
            )
            agent_card.grid(row=row, column=col, padx=8, pady=8, sticky="nsew")
            agents_grid.grid_columnconfigure(col, weight=1, uniform="agent")

        # Render custom agents after built-in ones
        self._render_custom_agents_in_grid(len(agents_info))

    def create_agent_card(self, parent, agent_type, icon, name, desc, color):
        """Crée une carte d'agent draggable"""
        # Frame de la carte
        card_frame = self.create_frame(parent, fg_color=self.colors["bg_secondary"])

        if self.use_ctk:
            card_frame.configure(
                corner_radius=12, border_width=2, border_color=self.colors["border"]
            )

        # Curseur de drag
        try:
            card_frame.configure(cursor="hand2")
        except Exception:
            pass

        # Contenu de la carte
        content_frame = self.create_frame(
            card_frame, fg_color=self.colors["bg_secondary"]
        )
        content_frame.pack(fill="both", expand=True, padx=20, pady=20)

        # Icône + Nom
        header_frame = self.create_frame(
            content_frame, fg_color=self.colors["bg_secondary"]
        )
        header_frame.pack(fill="x")

        icon_label = self.create_label(
            header_frame,
            text=icon,
            font=("Segoe UI", 28),
            fg_color=self.colors["bg_secondary"],
        )
        icon_label.pack(side="left", padx=(0, 10))

        name_label = self.create_label(
            header_frame,
            text=name,
            font=("Segoe UI", 14, "bold"),
            text_color=color,
            fg_color=self.colors["bg_secondary"],
        )
        name_label.pack(side="left", anchor="w")

        # Description
        desc_label = self.create_label(
            content_frame,
            text=desc,
            font=("Segoe UI", 12, "bold"),
            text_color=self.colors["text_primary"],
            fg_color=self.colors["bg_secondary"],
            wraplength=250,
        )
        desc_label.pack(fill="x", pady=(15, 5))

        # Rendre tous les widgets de la carte draggables
        all_widgets = [card_frame, content_frame, header_frame,
                       icon_label, name_label, desc_label]

        for widget in all_widgets:
            self._make_draggable(widget, agent_type, name, color)

        # Hover effect sur tous les widgets
        def on_enter(_e):
            if self.use_ctk:
                card_frame.configure(border_color=color, border_width=2)

        def on_leave(_e):
            if self.use_ctk:
                card_frame.configure(
                    border_color=self.colors["border"], border_width=2
                )

        for widget in all_widgets:
            widget.bind("<Enter>", on_enter)
            widget.bind("<Leave>", on_leave)

        # Stocker la référence
        self.agent_buttons[agent_type] = (card_frame, None, color)

        return card_frame

    def _get_agent_icon(self, agent_type: str) -> str:
        """Retourne l'emoji d'un type d'agent."""
        return self._AGENT_ICONS.get(agent_type, "🤖")
