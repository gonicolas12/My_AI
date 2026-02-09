"""
Interface Agents IA - Module pour l'onglet Agents dans la GUI moderne
Gère l'interface utilisateur pour le système multi-agents basé sur Ollama
"""

import threading
import tkinter as tk
from datetime import datetime
from tkinter import messagebox, scrolledtext

try:
    import customtkinter as ctk

    CTK_AVAILABLE = True
except ImportError:
    CTK_AVAILABLE = False
    ctk = tk

from core.agent_orchestrator import AgentOrchestrator


class AgentsInterface:
    """
    Interface pour le système d'agents IA
    S'intègre avec l'interface ModernAIGUI existante
    """

    def __init__(
        self,
        parent_frame,
        colors,
        create_frame,
        create_label,
        create_button,
        create_text,
        use_ctk=True,
    ):
        """
        Initialise l'interface agents

        Args:
            parent_frame: Frame parent où insérer l'interface
            colors: Dictionnaire de couleurs de l'interface principale
            create_frame: Fonction pour créer des frames (depuis ModernAIGUI)
            create_label: Fonction pour créer des labels
            create_button: Fonction pour créer des boutons
            create_text: Fonction pour créer des widgets Text
            use_ctk: Utilise CustomTkinter si True
        """
        self.parent = parent_frame
        self.colors = colors
        self.create_frame = create_frame
        self.create_label = create_label
        self.create_button = create_button
        self.create_text = create_text
        self.use_ctk = use_ctk

        # Orchestrateur d'agents
        self.orchestrator = AgentOrchestrator()

        # État de l'interface
        self.current_agent = None
        self.is_processing = False
        self.is_interrupted = False
        self.execution_history = []
        self.execute_btn = None

        # Référ ences UI
        self.agent_buttons = {}
        self.output_text = None
        self.task_entry = None
        self.status_label = None
        self.stats_labels = {}

        # Custom workflow (drag & drop)
        self.custom_workflow = []  # List of (agent_type, name, color) tuples
        self._drag_data = {"agent": None, "toplevel": None}
        self.pipeline_frame = None
        self.drop_zone_frame = None
        self.task_section_frame = None

        # Créer l'interface
        self.create_agents_interface()

    def create_agents_interface(self):
        """Crée l'interface complète des agents"""
        # Container principal avec scroll
        if self.use_ctk:
            main_scroll = ctk.CTkScrollableFrame(
                self.parent, fg_color=self.colors["bg_primary"], corner_radius=0
            )
        else:
            main_scroll = tk.Frame(self.parent, bg=self.colors["bg_primary"])

        main_scroll.pack(fill="both", expand=True, padx=0, pady=0)
        main_scroll.grid_columnconfigure(0, weight=1)

        # Header de la page
        self.create_header(main_scroll)

        # Section de sélection d'agents
        self.create_agent_selection(main_scroll)

        # Section de saisie de tâche
        self.create_task_input(main_scroll)

        # Zone de sortie/résultats
        self.create_output_area(main_scroll)

        # Statistiques en bas
        self.create_stats_section(main_scroll)

    def create_header(self, parent):
        """Crée l'en-tête de la page agents"""
        header_frame = self.create_frame(parent, fg_color=self.colors["bg_primary"])
        header_frame.grid(row=0, column=0, sticky="ew", padx=30, pady=(20, 10))

        # Titre
        title = self.create_label(
            header_frame,
            text="🤖 Agents IA Spécialisés",
            font=("Segoe UI", 24, "bold"),
            text_color=self.colors["text_primary"],
            fg_color=self.colors["bg_primary"],
        )
        title.pack()

        # Description
        desc_frame = self.create_frame(parent, fg_color=self.colors["bg_secondary"])
        desc_frame.grid(row=1, column=0, sticky="ew", padx=30, pady=(0, 20))

        desc_text = (
            "Les agents IA sont des assistants spécialisés basés sur Ollama. "
            "Choisissez un agent selon la tâche, ou utilisez un workflow pour des tâches complexes."
        )

        desc_label = self.create_label(
            desc_frame,
            text=desc_text,
            font=("Segoe UI", 11),
            text_color=self.colors["text_secondary"],
            fg_color=self.colors["bg_secondary"],
            wraplength=900,
        )
        desc_label.pack(padx=20, pady=15)

    def create_agent_selection(self, parent):
        """Crée la section de sélection d'agents"""
        section_frame = self.create_frame(parent, fg_color=self.colors["bg_primary"])
        section_frame.grid(row=2, column=0, sticky="ew", padx=30, pady=(0, 10))

        # Titre de section
        section_title = self.create_label(
            section_frame,
            text="Sélectionnez un Agent",
            font=("Segoe UI", 14, "bold"),
            text_color=self.colors["text_primary"],
            fg_color=self.colors["bg_primary"],
        )
        section_title.pack(anchor="w", pady=(0, 15))

        # Agents disponibles
        agents_info = {
            "code": {
                "icon": "🐍",
                "name": "CodeAgent",
                "desc": "Génération et debug de code",
                "color": "#3b82f6",
            },
            "research": {
                "icon": "📚",
                "name": "ResearchAgent",
                "desc": "Recherche et documentation",
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
                "icon": "🛡️",
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

        # Grille d'agents (3 par ligne)
        agents_grid = self.create_frame(
            section_frame, fg_color=self.colors["bg_primary"]
        )
        agents_grid.pack(fill="x")

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
        for widget in [card_frame, content_frame, header_frame,
                       icon_label, name_label, desc_label]:
            self._make_draggable(widget, agent_type, name, color)

        # Hover effect
        def on_enter(_e):
            if self.use_ctk:
                card_frame.configure(border_color=color, border_width=2)

        def on_leave(_e):
            if self.use_ctk:
                card_frame.configure(
                    border_color=self.colors["border"], border_width=2
                )

        card_frame.bind("<Enter>", on_enter)
        card_frame.bind("<Leave>", on_leave)

        # Stocker la référence
        self.agent_buttons[agent_type] = (card_frame, None, color)

        return card_frame

    def select_agent(self, agent_type, agent_name):
        """Sélectionne un agent (compatibilité - ajoute au workflow)"""
        # Chercher la couleur de l'agent
        color = "#ffffff"
        if agent_type in self.agent_buttons:
            _, _, color = self.agent_buttons[agent_type]
        self.add_agent_to_workflow(agent_type, agent_name, color)

    # === Drag & Drop System ===

    def _make_draggable(self, widget, agent_type, name, color):
        """Rend un widget draggable pour le drag & drop d'agents"""
        widget.bind(
            "<ButtonPress-1>",
            lambda e: self._on_drag_start(e, agent_type, name, color),
        )
        widget.bind("<B1-Motion>", self._on_drag_motion)
        widget.bind("<ButtonRelease-1>", self._on_drag_end)

    def _on_drag_start(self, event, agent_type, name, color):
        """Début du drag - crée un indicateur flottant"""
        self._drag_data["agent"] = (agent_type, name, color)

        # Créer un toplevel flottant comme indicateur visuel
        top = tk.Toplevel()
        top.overrideredirect(True)
        top.attributes("-topmost", True)
        try:
            top.attributes("-alpha", 0.85)
        except Exception:
            pass

        # Contenu du toplevel
        frame = tk.Frame(top, bg=color, padx=12, pady=8, relief="solid", bd=1)
        frame.pack()

        label = tk.Label(
            frame,
            text=f"🤖 {name}",
            font=("Segoe UI", 12, "bold"),
            fg="white",
            bg=color,
        )
        label.pack()

        # Positionner
        top.geometry(f"+{event.x_root + 10}+{event.y_root + 10}")
        self._drag_data["toplevel"] = top

    def _on_drag_motion(self, event):
        """Mouvement pendant le drag"""
        top = self._drag_data.get("toplevel")
        if top and top.winfo_exists():
            top.geometry(f"+{event.x_root + 10}+{event.y_root + 10}")

        # Highlight drop zone quand on survole
        if self._is_over_drop_zone(event.x_root, event.y_root):
            if self.drop_zone_frame and self.use_ctk:
                try:
                    agent_data = self._drag_data.get("agent")
                    c = agent_data[2] if agent_data else "#10b981"
                    self.drop_zone_frame.configure(border_color=c, border_width=3)
                except Exception:
                    pass
        else:
            if self.drop_zone_frame and self.use_ctk:
                try:
                    self.drop_zone_frame.configure(
                        border_color=self.colors["border"], border_width=2
                    )
                except Exception:
                    pass

    def _on_drag_end(self, event):
        """Fin du drag - vérifie si on est sur la zone de drop"""
        agent_data = self._drag_data.get("agent")
        top = self._drag_data.get("toplevel")

        # Détruire l'indicateur flottant
        if top and top.winfo_exists():
            top.destroy()

        # Reset la border de la drop zone
        if self.drop_zone_frame and self.use_ctk:
            try:
                self.drop_zone_frame.configure(
                    border_color=self.colors["border"], border_width=2
                )
            except Exception:
                pass

        if not agent_data:
            self._drag_data = {"agent": None, "toplevel": None}
            return

        # Vérifier si on est sur la zone de drop
        if self._is_over_drop_zone(event.x_root, event.y_root):
            agent_type, name, color = agent_data
            self.add_agent_to_workflow(agent_type, name, color)

        self._drag_data = {"agent": None, "toplevel": None}

    def _is_over_drop_zone(self, x_root, y_root):
        """Vérifie si les coordonnées sont sur la zone de drop"""
        # Vérifier la zone de drop principale
        if self.drop_zone_frame and self.drop_zone_frame.winfo_exists():
            try:
                dz_x = self.drop_zone_frame.winfo_rootx()
                dz_y = self.drop_zone_frame.winfo_rooty()
                dz_w = self.drop_zone_frame.winfo_width()
                dz_h = self.drop_zone_frame.winfo_height()
                if (dz_x <= x_root <= dz_x + dz_w) and (
                    dz_y <= y_root <= dz_y + dz_h
                ):
                    return True
            except Exception:
                pass

        # Vérifier aussi la zone de texte de la tâche
        if self.task_section_frame and self.task_section_frame.winfo_exists():
            try:
                ts_x = self.task_section_frame.winfo_rootx()
                ts_y = self.task_section_frame.winfo_rooty()
                ts_w = self.task_section_frame.winfo_width()
                ts_h = self.task_section_frame.winfo_height()
                if (ts_x <= x_root <= ts_x + ts_w) and (
                    ts_y <= y_root <= ts_y + ts_h
                ):
                    return True
            except Exception:
                pass

        return False

    # === Workflow Management ===

    def add_agent_to_workflow(self, agent_type, name, color):
        """Ajoute un agent au workflow personnalisé"""
        self.custom_workflow.append((agent_type, name, color))
        self.current_agent = agent_type
        self.update_pipeline_display()

        # Mettre à jour le statut
        if len(self.custom_workflow) == 1:
            self._update_status(f"✅ Agent ajouté: {name}", "#10b981")
        else:
            agent_names = " → ".join(n for _, n, _ in self.custom_workflow)
            self._update_status(f"✅ Workflow: {agent_names}", "#10b981")

    def clear_workflow(self):
        """Efface le workflow personnalisé"""
        self.custom_workflow.clear()
        self.current_agent = None
        self.update_pipeline_display()
        self._update_status(
            "Glissez-déposez des agents pour créer votre workflow",
            self.colors["text_secondary"],
        )

    def update_pipeline_display(self):
        """Met à jour l'affichage du pipeline de workflow"""
        if not self.pipeline_frame:
            return

        # Nettoyer le contenu existant
        for widget in self.pipeline_frame.winfo_children():
            widget.destroy()

        if not self.custom_workflow:
            # Placeholder
            placeholder = self.create_label(
                self.pipeline_frame,
                text="⇩ Glissez-déposez des agents ici pour créer votre workflow",
                font=("Segoe UI", 10),
                text_color=self.colors["text_secondary"],
                fg_color=self.colors["bg_secondary"],
            )
            placeholder.pack(pady=10)
            return

        # Afficher le pipeline
        pipeline_container = self.create_frame(
            self.pipeline_frame, fg_color=self.colors["bg_secondary"]
        )
        pipeline_container.pack(pady=10, padx=10)

        for idx, (agent_type, name, color) in enumerate(self.custom_workflow):
            if idx > 0:
                # Flèche entre agents
                arrow = self.create_label(
                    pipeline_container,
                    text="  →  ",
                    font=("Segoe UI", 16, "bold"),
                    text_color=self.colors["text_secondary"],
                    fg_color=self.colors["bg_secondary"],
                )
                arrow.pack(side="left")

            # Badge de l'agent avec sa couleur
            agent_badge = self.create_label(
                pipeline_container,
                text=f" {name} ",
                font=("Segoe UI", 12, "bold"),
                text_color=color,
                fg_color=self.colors["bg_secondary"],
            )
            agent_badge.pack(side="left")

    def create_task_input(self, parent):
        """Crée la zone de saisie de tâche avec zone de drop"""
        section_frame = self.create_frame(parent, fg_color=self.colors["bg_primary"])
        section_frame.grid(row=3, column=0, sticky="ew", padx=30, pady=(20, 10))
        self.task_section_frame = section_frame

        # Titre
        title = self.create_label(
            section_frame,
            text="Décrivez la Tâche",
            font=("Segoe UI", 14, "bold"),
            text_color=self.colors["text_primary"],
            fg_color=self.colors["bg_primary"],
        )
        title.pack(anchor="w", pady=(0, 10))

        # Frame pour input + boutons
        input_frame = self.create_frame(
            section_frame, fg_color=self.colors["bg_primary"]
        )
        input_frame.pack(fill="x")
        input_frame.grid_columnconfigure(0, weight=1)

        # Zone de texte
        if self.use_ctk:
            self.task_entry = ctk.CTkTextbox(
                input_frame,
                height=100,
                font=("Segoe UI", 12),
                fg_color=self.colors["input_bg"],
                text_color=self.colors["text_primary"],
                border_width=2,
                border_color=self.colors["border"],
                corner_radius=8,
            )
        else:
            self.task_entry = scrolledtext.ScrolledText(
                input_frame,
                height=5,
                font=("Segoe UI", 12),
                bg=self.colors["input_bg"],
                fg=self.colors["text_primary"],
                insertbackground=self.colors["text_primary"],
                relief="solid",
                borderwidth=2,
            )

        self.task_entry.grid(row=0, column=0, rowspan=2, sticky="nsew", padx=(0, 10))

        # Placeholder
        self._set_placeholder(
            "Décrivez la tâche pour l'agent sélectionné...\n\nExemple: Crée une fonction Python qui trie une liste de nombres"
        )

        # Frame pour les boutons (à droite, étiré pour s'aligner avec la zone de texte)
        buttons_frame = self.create_frame(
            input_frame, fg_color=self.colors["bg_primary"]
        )
        buttons_frame.grid(row=0, column=1, rowspan=2, sticky="nsew")

        # Bouton Exécuter (prend tout l'espace restant au-dessus de Clear)
        if self.use_ctk:
            self.execute_btn = ctk.CTkButton(
                buttons_frame,
                text="▶ Exécuter",
                command=self.execute_agent_task,
                fg_color=self.colors["accent"],
                hover_color="#ff5730",
                text_color="#ffffff",
                font=("Segoe UI", 13, "bold"),
                corner_radius=8,
                width=160,
                border_width=0,
            )
        else:
            self.execute_btn = tk.Button(
                buttons_frame,
                text="▶ Exécuter",
                command=self.execute_agent_task,
                bg=self.colors["accent"],
                fg="#ffffff",
                font=("Segoe UI", 13, "bold"),
                border=0,
                relief="flat",
            )
        self.execute_btn.pack(fill="both", expand=True, pady=(0, 8))

        # Bouton Clear Selection (rouge, hauteur fixe en bas)
        if self.use_ctk:
            clear_btn = ctk.CTkButton(
                buttons_frame,
                text="✕ Clear Selection",
                command=self.clear_workflow,
                fg_color="#dc2626",
                hover_color="#b91c1c",
                text_color="#ffffff",
                font=("Segoe UI", 11, "bold"),
                corner_radius=8,
                width=160,
                height=36,
            )
        else:
            clear_btn = tk.Button(
                buttons_frame,
                text="✕ Clear Selection",
                command=self.clear_workflow,
                bg="#dc2626",
                fg="#ffffff",
                font=("Segoe UI", 11, "bold"),
                border=0,
                relief="flat",
            )
        clear_btn.pack(anchor="n")

        # Zone de drop / Pipeline display
        self.drop_zone_frame = self.create_frame(
            section_frame, fg_color=self.colors["bg_secondary"]
        )
        if self.use_ctk:
            self.drop_zone_frame.configure(
                corner_radius=10, border_width=2, border_color=self.colors["border"]
            )
        self.drop_zone_frame.pack(fill="x", pady=(10, 0))

        self.pipeline_frame = self.create_frame(
            self.drop_zone_frame, fg_color=self.colors["bg_secondary"]
        )
        self.pipeline_frame.pack(fill="x")

        # Placeholder initial dans le pipeline
        self.update_pipeline_display()

        # Label de statut
        self.status_label = self.create_label(
            section_frame,
            text="Glissez-déposez des agents pour créer votre workflow",
            font=("Segoe UI", 10),
            text_color=self.colors["text_secondary"],
            fg_color=self.colors["bg_primary"],
        )
        self.status_label.pack(anchor="w", pady=(10, 0))

    def create_output_area(self, parent):
        """Crée la zone de sortie des résultats"""
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

        # Zone de texte avec scroll
        if self.use_ctk:
            self.output_text = ctk.CTkTextbox(
                section_frame,
                height=400,
                font=("Consolas", 11),
                fg_color=self.colors["bg_secondary"],
                text_color=self.colors["text_primary"],
                corner_radius=10,
                border_width=1,
                border_color=self.colors["border"],
            )
        else:
            self.output_text = scrolledtext.ScrolledText(
                section_frame,
                height=20,
                font=("Consolas", 11),
                bg=self.colors["bg_secondary"],
                fg=self.colors["text_primary"],
                insertbackground=self.colors["text_primary"],
                relief="solid",
                borderwidth=1,
            )

        self.output_text.pack(fill="both", expand=True)

        # Message initial
        welcome_msg = """🤖 Zone de Résultats des Agents IA

Bienvenue dans le système d'agents spécialisés !

1️ Sélectionnez un ou plusieurs agents
2️ Décrivez votre tâche
3️ Cliquez sur "Exécuter"

Les résultats apparaîtront ici en temps réel.

💡 Astuce: Glissez-déposez plusieurs agents pour créer votre propre workflow !
"""
        self.output_text.insert("1.0", welcome_msg)
        self._make_output_readonly()

    def create_stats_section(self, parent):
        """Crée la section des statistiques"""
        section_frame = self.create_frame(parent, fg_color=self.colors["bg_secondary"])
        section_frame.grid(row=5, column=0, sticky="ew", padx=30, pady=(10, 30))

        if self.use_ctk:
            section_frame.configure(corner_radius=10)

        content = self.create_frame(section_frame, fg_color=self.colors["bg_secondary"])
        content.pack(fill="x", padx=20, pady=15)

        # Titre
        title = self.create_label(
            content,
            text="📊 Statistiques",
            font=("Segoe UI", 12, "bold"),
            text_color=self.colors["text_primary"],
            fg_color=self.colors["bg_secondary"],
        )
        title.pack(anchor="w", pady=(0, 10))

        # Grid de stats
        stats_grid = self.create_frame(content, fg_color=self.colors["bg_secondary"])
        stats_grid.pack(fill="x")

        stats_names = [
            ("tasks", "Tâches Exécutées", "0"),
            ("agents", "Agents Actifs", "0"),
            ("success", "Taux de Succès", "100%"),
        ]

        for idx, (key, label, default) in enumerate(stats_names):
            stat_frame = self.create_frame(
                stats_grid, fg_color=self.colors["bg_secondary"]
            )
            stat_frame.grid(row=0, column=idx, padx=10, sticky="w")

            lbl = self.create_label(
                stat_frame,
                text=label,
                font=("Segoe UI", 9),
                text_color=self.colors["text_secondary"],
                fg_color=self.colors["bg_secondary"],
            )
            lbl.pack(anchor="w")

            val = self.create_label(
                stat_frame,
                text=default,
                font=("Segoe UI", 16, "bold"),
                text_color=self.colors["accent"],
                fg_color=self.colors["bg_secondary"],
            )
            val.pack(anchor="w")

            self.stats_labels[key] = val

    def execute_agent_task(self):
        """Exécute une tâche avec l'agent ou le workflow personnalisé"""
        if self.is_processing:
            messagebox.showwarning(
                "Agent Occupé", "Un agent est déjà en train de traiter une tâche."
            )
            return

        if not self.custom_workflow:
            messagebox.showwarning(
                "Aucun Agent",
                "Glissez-déposez un ou plusieurs agents pour commencer.",
            )
            return

        # Récupérer la tâche
        task = self._get_task_text()
        if not task or task.strip() == "":
            messagebox.showwarning(
                "Tâche Vide", "Veuillez décrire la tâche à effectuer."
            )
            return

        self.is_interrupted = False
        self._set_execute_button_stop()

        if len(self.custom_workflow) == 1:
            # Mode agent unique
            agent_type = self.custom_workflow[0][0]
            self.is_processing = True
            self._update_status("⏳ Traitement en cours...", "#f59e0b")
            threading.Thread(
                target=self._execute_task_thread,
                args=(agent_type, task),
                daemon=True,
            ).start()
        else:
            # Mode workflow personnalisé multi-agents
            self.is_processing = True
            self._update_status("⏳ Workflow personnalisé en cours...", "#f59e0b")
            threading.Thread(
                target=self._execute_custom_workflow_thread,
                args=(task,),
                daemon=True,
            ).start()

    def _execute_task_thread(self, agent_type, task):
        """Exécute la tâche dans un thread séparé avec streaming"""
        try:
            # Afficher la tâche
            self._append_output(
                f"\n{'='*80}\n🤖 Agent: {agent_type.upper()}\n📋 Tâche: {task}\n{'='*80}\n\n"
            )

            # Exécuter avec streaming (on_token retourne False si interrompu)
            result = self.orchestrator.execute_single_task_stream(
                agent_type=agent_type,
                task=task,
                on_token=self._on_token_received
            )

            if self.is_interrupted:
                self._append_output("\n\n⛔ Génération interrompue\n")
                self._update_status("⛔ Génération interrompue", "#ef4444")
            elif result.get("success"):
                self._append_output(f"\n\n⏱️  Terminé: {result.get('timestamp', 'N/A')}\n")
                self._update_status(
                    f"✅ Tâche terminée avec {result['agent']}", "#10b981"
                )
            else:
                self._append_output(f"\n\n❌ Erreur: {result.get('error')}\n\n")
                self._update_status("❌ Erreur lors de l'exécution", "#ef4444")

            # Mettre à jour les stats
            self._update_stats()

            # Enregistrer dans l'historique
            self.execution_history.append(
                {
                    "agent": agent_type,
                    "task": task,
                    "result": result if not self.is_interrupted else {"success": False, "error": "interrupted"},
                    "timestamp": datetime.now().isoformat(),
                }
            )

        except Exception as e:
            self._append_output(f"❌ Exception: {str(e)}\n\n")
            self._update_status("❌ Erreur critique", "#ef4444")
        finally:
            self.is_processing = False
            self.is_interrupted = False
            self._set_execute_button_normal()

    def _execute_custom_workflow_thread(self, task):
        """Exécute un workflow personnalisé multi-agents"""
        try:
            # Construire le workflow
            workflow = []
            for idx, (agent_type, name, color) in enumerate(self.custom_workflow):
                workflow.append(
                    {
                        "agent": agent_type,
                        "task": (
                            task
                            if idx == 0
                            else f"Continue en te basant sur le résultat précédent pour: {task}"
                        ),
                        "pass_result": idx > 0,
                    }
                )

            agent_names = " → ".join(n for _, n, _ in self.custom_workflow)
            self._append_output(
                f"\n{'='*80}\n⚡ WORKFLOW PERSONNALISÉ: {agent_names}\n"
                f"📋 Tâche: {task}\n{'='*80}\n\n"
            )

            # Callbacks pour le streaming
            def on_step_start(step_idx, agent_type, step_task):
                if self.is_interrupted:
                    return
                name = next(
                    (n for at, n, _ in self.custom_workflow if at == agent_type),
                    agent_type,
                )
                self._append_output(
                    f"\n--- Étape {step_idx}/{len(workflow)}: {name.upper()} ---\n\n"
                )

            def on_step_complete(step_idx, result):
                if self.is_interrupted:
                    return
                if not result.get("success"):
                    self._append_output(f"\n❌ Erreur: {result.get('error')}\n")
                self._append_output(f"\n\n⏱️ Étape {step_idx} terminée\n\n")

            # Exécuter avec streaming
            result = self.orchestrator.execute_multi_agent_task_stream(
                task,
                workflow,
                on_step_start=on_step_start,
                on_token=self._on_token_received,
                on_step_complete=on_step_complete,
                on_should_stop=lambda: self.is_interrupted,
            )

            if self.is_interrupted:
                self._append_output("\n\n⛔ Génération interrompue\n")
                self._update_status("⛔ Génération interrompue", "#ef4444")
            else:
                # Résumé final
                summary = result["summary"]
                self._append_output(f"\n{'='*80}\n📊 RÉSUMÉ\n{'='*80}\n")
                self._append_output(f"Tâches: {summary['total_tasks']}\n")
                self._append_output(f"Réussies: {summary['successful']}\n")
                self._append_output(
                    f"Taux de succès: {summary['success_rate']:.1%}\n\n"
                )
                self._update_status(
                    f"✅ Workflow terminé ({summary['success_rate']:.0%} succès)",
                    "#10b981",
                )
            self._update_stats()

            self.execution_history.append(
                {
                    "agent": "workflow_custom",
                    "task": task,
                    "result": result if not self.is_interrupted else {"success": False, "error": "interrupted"},
                    "timestamp": datetime.now().isoformat(),
                }
            )

        except Exception as e:
            self._append_output(f"❌ Erreur workflow: {str(e)}\n\n")
            self._update_status("❌ Erreur workflow", "#ef4444")
        finally:
            self.is_processing = False
            self.is_interrupted = False
            self._set_execute_button_normal()



    # === Méthodes utilitaires ===

    def _set_placeholder(self, text):
        """Définit le placeholder de la zone de saisie"""
        if self.use_ctk:
            self.task_entry.insert("0.0", text)
            self.task_entry.configure(text_color=self.colors["placeholder"])

            def on_focus_in(_event):
                if self.task_entry.get("0.0", "end-1c") == text:
                    self.task_entry.delete("0.0", "end")
                    self.task_entry.configure(text_color=self.colors["text_primary"])

            def on_focus_out(_event):
                if not self.task_entry.get("0.0", "end-1c").strip():
                    self.task_entry.insert("0.0", text)
                    self.task_entry.configure(text_color=self.colors["placeholder"])

            self.task_entry.bind("<FocusIn>", on_focus_in)
            self.task_entry.bind("<FocusOut>", on_focus_out)

    def _get_task_text(self):
        """Récupère le texte de la tâche"""
        if self.use_ctk:
            text = self.task_entry.get("0.0", "end-1c").strip()
        else:
            text = self.task_entry.get("1.0", "end-1c").strip()

        # Vérifier si c'est le placeholder
        if "Décrivez la tâche" in text:
            return ""

        return text

    def _append_output(self, text):
        """Ajoute du texte à la zone de sortie"""

        def update():
            self.output_text.configure(state="normal" if not self.use_ctk else "normal")
            self.output_text.insert("end", text)
            self.output_text.see("end")
            self._make_output_readonly()

        # S'assurer que c'est dans le thread UI
        if self.parent.winfo_exists():
            self.parent.after(0, update)

    def _on_token_received(self, token):
        """Callback pour chaque token reçu pendant le streaming.
        Retourne False pour interrompre la génération."""
        if self.is_interrupted:
            return False
        self._append_output(token)
        return True

    def interrupt_agents(self):
        """Interrompt la génération en cours"""
        if self.is_processing:
            self.is_interrupted = True
            self._update_status("⛔ Interruption en cours...", "#ef4444")

    def _set_execute_button_stop(self):
        """Transforme le bouton Exécuter en bouton STOP (carré noir sur fond blanc)"""
        def update():
            if self.execute_btn and self.execute_btn.winfo_exists():
                if self.use_ctk:
                    self.execute_btn.configure(
                        text="  ■  ",
                        command=self.interrupt_agents,
                        state="normal",
                        fg_color="#ffffff",
                        hover_color="#f3f3f3",
                        text_color="#111111",
                        border_color="#111111",
                        border_width=2,
                        font=("Segoe UI", 16, "bold"),
                    )
                else:
                    self.execute_btn.configure(
                        text="  ■  ",
                        command=self.interrupt_agents,
                        bg="#ffffff",
                        fg="#111111",
                        activebackground="#f3f3f3",
                        font=("Segoe UI", 16, "bold"),
                    )
        if self.parent.winfo_exists():
            self.parent.after(0, update)

    def _set_execute_button_normal(self):
        """Restaure le bouton Exécuter en mode normal (identique à la création)"""
        def update():
            if self.execute_btn and self.execute_btn.winfo_exists():
                if self.use_ctk:
                    self.execute_btn.configure(
                        text="▶ Exécuter",
                        command=self.execute_agent_task,
                        state="normal",
                        fg_color=self.colors["accent"],
                        hover_color="#ff5730",
                        text_color="#ffffff",
                        font=("Segoe UI", 13, "bold"),
                        corner_radius=8,
                        border_width=0,
                        border_color=self.colors["accent"],
                    )
                else:
                    self.execute_btn.configure(
                        text="▶ Exécuter",
                        command=self.execute_agent_task,
                        bg=self.colors["accent"],
                        fg="#ffffff",
                        font=("Segoe UI", 12, "bold"),
                        border=0,
                        relief="flat",
                    )
        if self.parent.winfo_exists():
            self.parent.after(0, update)

    def _make_output_readonly(self):
        """Rend la zone de sortie en lecture seule"""
        try:
            if self.use_ctk:
                # Pour CTkTextbox, on désactive les événements clavier
                self.output_text.configure(state="disabled")
            else:
                self.output_text.configure(state="disabled")
        except Exception:
            pass

    def _update_status(self, text, color):
        """Met à jour le label de statut"""

        def update():
            if self.status_label and self.status_label.winfo_exists():
                self.status_label.configure(text=text, text_color=color)

        if self.parent.winfo_exists():
            self.parent.after(0, update)

    def _update_stats(self):
        """Met à jour les statistiques"""

        def update():
            stats = self.orchestrator.get_orchestrator_stats()

            if "tasks" in self.stats_labels:
                self.stats_labels["tasks"].configure(text=str(stats["total_tasks"]))

            if "agents" in self.stats_labels:
                self.stats_labels["agents"].configure(text=str(stats["active_agents"]))

            # Calculer le taux de succès basé sur l'historique
            if self.execution_history:
                success_count = sum(
                    1 for h in self.execution_history if h["result"].get("success")
                )
                success_rate = (success_count / len(self.execution_history)) * 100
                if "success" in self.stats_labels:
                    self.stats_labels["success"].configure(text=f"{success_rate:.0f}%")

        if self.parent.winfo_exists():
            self.parent.after(0, update)

    def _darken_color(self, hex_color):
        """Assombrit une couleur hexadécimale"""
        # Convertir hex en RGB
        hex_color = hex_color.lstrip("#")
        r, g, b = tuple(int(hex_color[i : i + 2], 16) for i in (0, 2, 4))

        # Assombrir de 20%
        r = int(r * 0.8)
        g = int(g * 0.8)
        b = int(b * 0.8)

        # Reconvertir en hex
        return f"#{r:02x}{g:02x}{b:02x}"
