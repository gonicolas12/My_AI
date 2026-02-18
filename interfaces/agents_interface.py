"""
Interface Agents IA - Module pour l'onglet Agents dans la GUI moderne
Gère l'interface utilisateur pour le système multi-agents basé sur Ollama
"""

import json
import os
import random
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
from models.local_llm import LocalLLM
from models.ai_agents import AIAgent, AVAILABLE_AGENTS


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

        # Custom agents created by user
        self.custom_agents = {}  # key -> {name, desc, color, system_prompt, temperature}
        self.custom_agents_file = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "data", "custom_agents.json"
        )
        self.agents_grid = None  # Reference to agents grid for adding custom agents
        self._load_custom_agents()

        # LLM for generating system prompts
        self.llm = LocalLLM(model="llama3.2")

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
            "web": {
                "icon": "🌐",
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

        # Highlight zone de texte de la tâche avec la couleur orange
        if self._is_over_task_entry(event.x_root, event.y_root):
            if self.task_entry and self.use_ctk:
                try:
                    self.task_entry.configure(
                        border_color=self.colors["accent"], border_width=3
                    )
                except Exception:
                    pass
        else:
            if self.task_entry and self.use_ctk:
                try:
                    self.task_entry.configure(
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

        # Reset la border de la zone de texte de la tâche
        if self.task_entry and self.use_ctk:
            try:
                self.task_entry.configure(
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

    def _is_over_task_entry(self, x_root, y_root):
        """Vérifie si les coordonnées sont sur la zone de texte de la tâche"""
        if self.task_entry and self.task_entry.winfo_exists():
            try:
                te_x = self.task_entry.winfo_rootx()
                te_y = self.task_entry.winfo_rooty()
                te_w = self.task_entry.winfo_width()
                te_h = self.task_entry.winfo_height()
                if (te_x <= x_root <= te_x + te_w) and (
                    te_y <= y_root <= te_y + te_h
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

        for idx, (_agent_type, name, color) in enumerate(self.custom_workflow):
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
                height=130,
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
                height=7,
                font=("Segoe UI", 12),
                bg=self.colors["input_bg"],
                fg=self.colors["text_primary"],
                insertbackground=self.colors["text_primary"],
                relief="solid",
                borderwidth=2,
            )

        self.task_entry.grid(row=0, column=0, rowspan=3, sticky="nsew", padx=(0, 10))

        # Placeholder
        self._set_placeholder(
            "Décrivez la tâche pour l'agent sélectionné...\n\nExemple: Crée une fonction Python qui trie une liste de nombres"
        )

        # Frame pour les boutons (à droite, étiré pour s'aligner avec la zone de texte)
        buttons_frame = self.create_frame(
            input_frame, fg_color=self.colors["bg_primary"]
        )
        buttons_frame.grid(row=0, column=1, rowspan=3, sticky="nsew")

        # Bouton Exécuter
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
        self.execute_btn.pack(fill="both", expand=True, pady=(0, 4))

        # Bouton Créer Agent (bleu, entre les deux)
        if self.use_ctk:
            create_agent_btn = ctk.CTkButton(
                buttons_frame,
                text="➕ Créer Agent",
                command=self._open_create_agent_dialog,
                fg_color="#3b82f6",
                hover_color="#2563eb",
                text_color="#ffffff",
                font=("Segoe UI", 13, "bold"),
                corner_radius=8,
                width=160,
            )
        else:
            create_agent_btn = tk.Button(
                buttons_frame,
                text="➕ Créer Agent",
                command=self._open_create_agent_dialog,
                bg="#3b82f6",
                fg="#ffffff",
                font=("Segoe UI", 13, "bold"),
                border=0,
                relief="flat",
            )
        create_agent_btn.pack(fill="both", expand=True, pady=4)

        # Bouton Clear Selection (rouge)
        if self.use_ctk:
            clear_btn = ctk.CTkButton(
                buttons_frame,
                text="❌ Clear Selection",
                command=self.clear_workflow,
                fg_color="#dc2626",
                hover_color="#b91c1c",
                text_color="#ffffff",
                font=("Segoe UI", 13, "bold"),
                corner_radius=8,
                width=160,
            )
        else:
            clear_btn = tk.Button(
                buttons_frame,
                text="❌ Clear Selection",
                command=self.clear_workflow,
                bg="#dc2626",
                fg="#ffffff",
                font=("Segoe UI", 13, "bold"),
                border=0,
                relief="flat",
            )
        clear_btn.pack(fill="both", expand=True, pady=(4, 0))

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
        welcome_msg = """Bienvenue dans le système d'agents spécialisés !

1️ Sélectionnez un ou plusieurs agents
2️ Décrivez votre tâche
3️ Cliquez sur "Exécuter"

Les résultats apparaîtront ici en temps réel.
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
                f"\n{'='*80}\n\n"
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
            for idx, (agent_type, _name, _color) in enumerate(self.custom_workflow):
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

            # Callbacks pour le streaming
            def on_step_start(step_idx, agent_type, _step_task):
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

    # === Custom Agent Management ===

    def _get_random_color(self):
        """Returns a random vibrant color for custom agents"""
        palette = [
            "#e11d48", "#7c3aed", "#0891b2", "#059669", "#d97706",
            "#dc2626", "#9333ea", "#0284c7", "#16a34a", "#ca8a04",
            "#be185d", "#6d28d9", "#0e7490", "#047857", "#b45309",
            "#c026d3", "#4f46e5", "#0369a1", "#15803d", "#a16207",
        ]
        return random.choice(palette)

    def _load_custom_agents(self):
        """Load custom agents from JSON file"""
        try:
            if os.path.exists(self.custom_agents_file):
                with open(self.custom_agents_file, "r", encoding="utf-8") as f:
                    self.custom_agents = json.load(f)
                print(f"✅ {len(self.custom_agents)} agents personnalisés chargés")
        except Exception as e:
            print(f"⚠️ Erreur chargement agents personnalisés: {e}")
            self.custom_agents = {}

    def _save_custom_agents(self):
        """Save custom agents to JSON file"""
        try:
            os.makedirs(os.path.dirname(self.custom_agents_file), exist_ok=True)
            with open(self.custom_agents_file, "w", encoding="utf-8") as f:
                json.dump(self.custom_agents, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"⚠️ Erreur sauvegarde agents personnalisés: {e}")

    def _register_custom_agent_in_orchestrator(self, agent_key, agent_data):
        """Register a custom agent so it can be used by the orchestrator"""
        def factory(model="llama3.2"):
            return AIAgent(
                name=agent_data["name"],
                expertise=agent_data["desc"],
                system_prompt=agent_data["system_prompt"],
                model=model,
                temperature=agent_data.get("temperature", 0.5),
            )
        # Add to available agents
        AVAILABLE_AGENTS[agent_key] = factory

    def _render_custom_agents_in_grid(self, start_idx=9):
        """Render all custom agents in the agents grid"""
        if not self.agents_grid:
            return
        for idx, (agent_key, agent_data) in enumerate(self.custom_agents.items()):
            total_idx = start_idx + idx
            row = total_idx // 3
            col = total_idx % 3

            card = self._create_custom_agent_card(
                self.agents_grid,
                agent_key,
                agent_data["name"],
                agent_data["desc"],
                agent_data["color"],
            )
            card.grid(row=row, column=col, padx=8, pady=8, sticky="nsew")
            self.agents_grid.grid_columnconfigure(col, weight=1, uniform="agent")

            # Register in orchestrator
            self._register_custom_agent_in_orchestrator(agent_key, agent_data)

    def _create_custom_agent_card(self, parent, agent_key, name, desc, color):
        """Create a custom agent card with edit/delete buttons"""
        card_frame = self.create_frame(parent, fg_color=self.colors["bg_secondary"])

        if self.use_ctk:
            card_frame.configure(
                corner_radius=12, border_width=2, border_color=self.colors["border"]
            )

        try:
            card_frame.configure(cursor="hand2")
        except Exception:
            pass

        content_frame = self.create_frame(
            card_frame, fg_color=self.colors["bg_secondary"]
        )
        content_frame.pack(fill="both", expand=True, padx=20, pady=20)

        # Top bar with edit/delete buttons
        top_bar = self.create_frame(content_frame, fg_color=self.colors["bg_secondary"])
        top_bar.pack(fill="x")

        # Icon + Name (left side)
        header_frame = self.create_frame(
            top_bar, fg_color=self.colors["bg_secondary"]
        )
        header_frame.pack(side="left", fill="x", expand=True)

        icon_label = self.create_label(
            header_frame,
            text="🤖",
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

        # Action buttons (right side, top)
        actions_frame = self.create_frame(
            top_bar, fg_color=self.colors["bg_secondary"]
        )
        actions_frame.pack(side="right")

        # Edit button (pencil)
        if self.use_ctk:
            edit_btn = ctk.CTkButton(
                actions_frame,
                text="📝",
                width=30, height=30,
                fg_color="transparent",
                hover_color=self.colors["bg_primary"],
                font=("Segoe UI", 14),
                corner_radius=6,
                command=lambda k=agent_key: self._open_edit_agent_dialog(k),
            )
        else:
            edit_btn = tk.Button(
                actions_frame,
                text="📝",
                bg=self.colors["bg_secondary"],
                font=("Segoe UI", 12),
                border=0, relief="flat",
                command=lambda k=agent_key: self._open_edit_agent_dialog(k),
            )
        edit_btn.pack(side="left", padx=(0, 4))

        # Delete button (cross)
        if self.use_ctk:
            delete_btn = ctk.CTkButton(
                actions_frame,
                text="✕",
                width=30, height=30,
                fg_color="transparent",
                hover_color=self.colors["bg_primary"],
                text_color="#ef4444",
                font=("Segoe UI", 14, "bold"),
                corner_radius=6,
                command=lambda k=agent_key: self._delete_custom_agent(k),
            )
        else:
            delete_btn = tk.Button(
                actions_frame,
                text="✕",
                bg=self.colors["bg_secondary"],
                fg="#ef4444",
                font=("Segoe UI", 12, "bold"),
                border=0, relief="flat",
                command=lambda k=agent_key: self._delete_custom_agent(k),
            )
        delete_btn.pack(side="left")

        # Short description (use short_desc if available, else desc)
        agent_data = self.custom_agents.get(agent_key, {})
        display_desc = agent_data.get("short_desc", desc)
        desc_label = self.create_label(
            content_frame,
            text=display_desc,
            font=("Segoe UI", 12, "bold"),
            text_color=self.colors["text_primary"],
            fg_color=self.colors["bg_secondary"],
            wraplength=250,
        )
        desc_label.pack(fill="x", pady=(15, 5))

        # Make draggable (exclude edit/delete buttons)
        all_widgets = [card_frame, content_frame, top_bar, header_frame,
                       icon_label, name_label, desc_label]

        for widget in all_widgets:
            self._make_draggable(widget, agent_key, name, color)

        # Hover effect
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

        self.agent_buttons[agent_key] = (card_frame, None, color)
        return card_frame

    def _show_notification(self, message, color="#10b981", duration=2500):
        """Show a notification in the top-right corner of the agents page"""
        try:
            if self.use_ctk:
                notif = ctk.CTkFrame(
                    self.parent, fg_color=color, corner_radius=8
                )
                lbl = ctk.CTkLabel(
                    notif, text=message, text_color="#ffffff",
                    font=("Segoe UI", 12, "bold"), fg_color="transparent",
                )
            else:
                notif = tk.Frame(self.parent, bg=color)
                lbl = tk.Label(
                    notif, text=message, fg="#ffffff", bg=color,
                    font=("Segoe UI", 12, "bold"),
                )

            notif.place(relx=0.98, rely=0.02, anchor="ne")
            lbl.pack(padx=15, pady=8)
            notif.lift()
            self.parent.after(duration, notif.destroy)
        except Exception:
            pass

    # === Create Agent Dialog ===

    def _open_create_agent_dialog(self):
        """Open a dialog to create a custom agent"""
        dialog = tk.Toplevel()
        dialog.title("Créer un Agent Personnalisé")
        dialog.geometry("500x380")
        dialog.resizable(False, False)
        dialog.configure(bg=self.colors["bg_primary"])
        dialog.transient(self.parent.winfo_toplevel())
        dialog.grab_set()

        # Center the dialog
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - 250
        y = (dialog.winfo_screenheight() // 2) - 190
        dialog.geometry(f"500x380+{x}+{y}")

        # Title
        title_lbl = self.create_label(
            dialog,
            text="🤖 Créer un Agent Personnalisé",
            font=("Segoe UI", 16, "bold"),
            text_color=self.colors["text_primary"],
            fg_color=self.colors["bg_primary"],
        )
        title_lbl.pack(padx=20, pady=(20, 15))

        # Name field
        name_lbl = self.create_label(
            dialog, text="Nom de l'agent",
            font=("Segoe UI", 11, "bold"),
            text_color=self.colors["text_primary"],
            fg_color=self.colors["bg_primary"],
        )
        name_lbl.pack(anchor="w", padx=30)

        if self.use_ctk:
            name_entry = ctk.CTkEntry(
                dialog, font=("Segoe UI", 12), height=36,
                fg_color=self.colors["input_bg"],
                text_color=self.colors["text_primary"],
                border_color=self.colors["border"],
                corner_radius=6, placeholder_text="Ex: MyCustomAgent",
            )
        else:
            name_entry = tk.Entry(
                dialog, font=("Segoe UI", 12),
                bg=self.colors["input_bg"], fg=self.colors["text_primary"],
            )
        name_entry.pack(fill="x", padx=30, pady=(4, 12))

        # Role/description field
        role_lbl = self.create_label(
            dialog, text="Rôle / Description",
            font=("Segoe UI", 11, "bold"),
            text_color=self.colors["text_primary"],
            fg_color=self.colors["bg_primary"],
        )
        role_lbl.pack(anchor="w", padx=30)

        if self.use_ctk:
            role_entry = ctk.CTkTextbox(
                dialog, height=100, font=("Segoe UI", 12),
                fg_color=self.colors["input_bg"],
                text_color=self.colors["text_primary"],
                border_width=1, border_color=self.colors["border"],
                corner_radius=6,
            )
        else:
            role_entry = tk.Text(
                dialog, height=5, font=("Segoe UI", 12),
                bg=self.colors["input_bg"], fg=self.colors["text_primary"],
            )
        role_entry.pack(fill="x", padx=30, pady=(4, 15))

        # Loading indicator (hidden initially)
        loading_frame = self.create_frame(dialog, fg_color=self.colors["bg_primary"])
        loading_frame.pack(fill="x", padx=30)

        loading_label = self.create_label(
            loading_frame, text="",
            font=("Segoe UI", 11),
            text_color="#f59e0b",
            fg_color=self.colors["bg_primary"],
        )
        loading_label.pack()

        # Buttons frame
        btn_frame = self.create_frame(dialog, fg_color=self.colors["bg_primary"])
        btn_frame.pack(fill="x", padx=30, pady=(10, 20))

        # Cancel button
        if self.use_ctk:
            cancel_btn = ctk.CTkButton(
                btn_frame, text="Annuler", width=120,
                fg_color=self.colors["bg_secondary"],
                hover_color=self.colors["border"],
                text_color=self.colors["text_primary"],
                font=("Segoe UI", 11, "bold"),
                corner_radius=8,
                command=dialog.destroy,
            )
        else:
            cancel_btn = tk.Button(
                btn_frame, text="Annuler",
                bg=self.colors["bg_secondary"],
                fg=self.colors["text_primary"],
                font=("Segoe UI", 11, "bold"),
                command=dialog.destroy,
            )
        cancel_btn.pack(side="right", padx=(10, 0))

        # Create button
        if self.use_ctk:
            create_btn = ctk.CTkButton(
                btn_frame, text="Créer", width=120,
                fg_color="#3b82f6", hover_color="#2563eb",
                text_color="#ffffff",
                font=("Segoe UI", 11, "bold"),
                corner_radius=8,
                command=lambda: self._do_create_agent(
                    dialog, name_entry, role_entry,
                    loading_label, create_btn, cancel_btn
                ),
            )
        else:
            create_btn = tk.Button(
                btn_frame, text="Créer",
                bg="#3b82f6", fg="#ffffff",
                font=("Segoe UI", 11, "bold"),
                command=lambda: self._do_create_agent(
                    dialog, name_entry, role_entry,
                    loading_label, create_btn, cancel_btn
                ),
            )
        create_btn.pack(side="right")

    def _do_create_agent(self, dialog, name_entry, role_entry,
                         loading_label, create_btn, cancel_btn):
        """Start the agent creation process"""
        # Get values
        if self.use_ctk:
            name = name_entry.get().strip()
            role = role_entry.get("0.0", "end-1c").strip()
        else:
            name = name_entry.get().strip()
            role = role_entry.get("1.0", "end-1c").strip()

        if not name:
            messagebox.showwarning("Nom requis", "Veuillez entrer un nom pour l'agent.")
            return
        if not role:
            messagebox.showwarning("Rôle requis", "Veuillez décrire le rôle de l'agent.")
            return

        # Disable buttons and show loading
        if self.use_ctk:
            create_btn.configure(state="disabled")
            cancel_btn.configure(state="disabled")
        else:
            create_btn.configure(state="disabled")
            cancel_btn.configure(state="disabled")

        # Loading animation
        self._animate_loading(loading_label, dialog, 0)

        # Generate system prompt in background thread
        threading.Thread(
            target=self._generate_agent_in_background,
            args=(dialog, name, role, loading_label),
            daemon=True,
        ).start()

    def _animate_loading(self, label, dialog, step):
        """Animate a loading indicator"""
        if not dialog.winfo_exists():
            return
        spinner = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
        icon = spinner[step % len(spinner)]
        label.configure(text=f"{icon} Génération du system prompt en cours...")
        dialog.after(200, lambda: self._animate_loading(label, dialog, step + 1))

    def _generate_agent_in_background(self, dialog, name, role, loading_label):
        """Generate system prompt via Ollama in background thread"""
        prompt = f"""Tu dois créer un system prompt pour un agent IA spécialisé.

Voici le nom de l'agent: {name}
Voici la description de son rôle: {role}

Génère un system prompt complet en suivant EXACTEMENT ce format:

Tu es {name}, un expert en [domaine basé sur la description].

EXPERTISE: [liste des domaines d'expertise basée sur la description]

COMPORTEMENT:
- [comportement 1]
- [comportement 2]
- [comportement 3]
- [comportement 4]
- [comportement 5]

FORMAT DE RÉPONSE:
- [format 1]
- [format 2]
- [format 3]
- [format 4]

Réponds UNIQUEMENT avec le system prompt, rien d'autre. Pas d'explication, pas de commentaire.
Génère aussi à la fin, sur une ligne séparée commençant par "TEMPERATURE:", une valeur de température entre 0.1 et 0.9 adaptée au rôle (précis = bas, créatif = haut).
Ensuite, sur une dernière ligne séparée commençant par "SUMMARY:", génère un résumé de 3-4 mots maximum du rôle de l'agent, avec la première lettre en majuscule (ex: "Recherche web avancée" ou "Analyse de données")."""

        try:
            response = self.llm.generate(
                prompt=prompt,
                system_prompt="Tu es un assistant qui génère des system prompts pour des agents IA. Réponds uniquement avec le contenu demandé, sans explications."
            )

            if response:
                # Parse temperature and summary from response
                temperature = 0.5
                short_desc = role[:30]
                system_prompt = response.strip()

                if "SUMMARY:" in system_prompt:
                    parts = system_prompt.rsplit("SUMMARY:", 1)
                    system_prompt = parts[0].strip()
                    short_desc = parts[1].strip().split("\n")[0].strip()
                    if short_desc:
                        short_desc = short_desc[0].upper() + short_desc[1:]

                if "TEMPERATURE:" in system_prompt:
                    parts = system_prompt.rsplit("TEMPERATURE:", 1)
                    system_prompt = parts[0].strip()
                    try:
                        temp_str = parts[1].strip().split()[0]
                        temperature = float(temp_str)
                        temperature = max(0.1, min(0.9, temperature))
                    except (ValueError, IndexError):
                        temperature = 0.5

                color = self._get_random_color()
                agent_key = f"custom_{name.lower().replace(' ', '_')}_{int(datetime.now().timestamp())}"

                agent_data = {
                    "name": name,
                    "desc": role,
                    "short_desc": short_desc,
                    "color": color,
                    "system_prompt": system_prompt,
                    "temperature": temperature,
                }

                self.custom_agents[agent_key] = agent_data
                self._save_custom_agents()
                self._register_custom_agent_in_orchestrator(agent_key, agent_data)

                # Update UI on main thread
                def on_success():
                    if dialog.winfo_exists():
                        dialog.destroy()
                    self._add_custom_agent_card_to_grid(agent_key, agent_data)
                    self._show_notification("✅ Agent créé !", "#10b981")

                self.parent.after(0, on_success)
            else:
                def on_error():
                    if dialog.winfo_exists():
                        loading_label.configure(
                            text="❌ Erreur: Ollama n'a pas répondu. Vérifiez qu'Ollama est lancé.",
                            text_color="#ef4444"
                        )
                self.parent.after(0, on_error)

        except Exception as e:
            def on_error():
                if dialog.winfo_exists():
                    loading_label.configure(
                        text=f"❌ Erreur: {str(e)[:60]}",
                        text_color="#ef4444"
                    )
            self.parent.after(0, on_error)

    def _add_custom_agent_card_to_grid(self, agent_key, agent_data):
        """Add a single custom agent card to the existing grid"""
        if not self.agents_grid:
            return
        # Count existing cards
        total = 9 + len(self.custom_agents) - 1  # 9 built-in + already added custom - current
        row = total // 3
        col = total % 3

        card = self._create_custom_agent_card(
            self.agents_grid,
            agent_key,
            agent_data["name"],
            agent_data["desc"],
            agent_data["color"],
        )
        card.grid(row=row, column=col, padx=8, pady=8, sticky="nsew")
        self.agents_grid.grid_columnconfigure(col, weight=1, uniform="agent")

    # === Edit Agent Dialog ===

    def _open_edit_agent_dialog(self, agent_key):
        """Open dialog to edit a custom agent"""
        if agent_key not in self.custom_agents:
            return

        agent_data = self.custom_agents[agent_key]

        dialog = tk.Toplevel()
        dialog.title(f"Modifier {agent_data['name']}")
        dialog.geometry("500x380")
        dialog.resizable(False, False)
        dialog.configure(bg=self.colors["bg_primary"])
        dialog.transient(self.parent.winfo_toplevel())
        dialog.grab_set()

        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - 250
        y = (dialog.winfo_screenheight() // 2) - 190
        dialog.geometry(f"500x380+{x}+{y}")

        # Title
        title_lbl = self.create_label(
            dialog,
            text=f"📝 Modifier {agent_data['name']}",
            font=("Segoe UI", 16, "bold"),
            text_color=self.colors["text_primary"],
            fg_color=self.colors["bg_primary"],
        )
        title_lbl.pack(padx=20, pady=(20, 15))

        # Name field
        name_lbl = self.create_label(
            dialog, text="Nom de l'agent",
            font=("Segoe UI", 11, "bold"),
            text_color=self.colors["text_primary"],
            fg_color=self.colors["bg_primary"],
        )
        name_lbl.pack(anchor="w", padx=30)

        if self.use_ctk:
            name_entry = ctk.CTkEntry(
                dialog, font=("Segoe UI", 12), height=36,
                fg_color=self.colors["input_bg"],
                text_color=self.colors["text_primary"],
                border_color=self.colors["border"],
                corner_radius=6,
            )
            name_entry.insert(0, agent_data["name"])
        else:
            name_entry = tk.Entry(
                dialog, font=("Segoe UI", 12),
                bg=self.colors["input_bg"], fg=self.colors["text_primary"],
            )
            name_entry.insert(0, agent_data["name"])
        name_entry.pack(fill="x", padx=30, pady=(4, 12))

        # Role/description field
        role_lbl = self.create_label(
            dialog, text="Rôle / Description",
            font=("Segoe UI", 11, "bold"),
            text_color=self.colors["text_primary"],
            fg_color=self.colors["bg_primary"],
        )
        role_lbl.pack(anchor="w", padx=30)

        if self.use_ctk:
            role_entry = ctk.CTkTextbox(
                dialog, height=100, font=("Segoe UI", 12),
                fg_color=self.colors["input_bg"],
                text_color=self.colors["text_primary"],
                border_width=1, border_color=self.colors["border"],
                corner_radius=6,
            )
            role_entry.insert("0.0", agent_data["desc"])
        else:
            role_entry = tk.Text(
                dialog, height=5, font=("Segoe UI", 12),
                bg=self.colors["input_bg"], fg=self.colors["text_primary"],
            )
            role_entry.insert("1.0", agent_data["desc"])
        role_entry.pack(fill="x", padx=30, pady=(4, 15))

        # Loading indicator
        loading_frame = self.create_frame(dialog, fg_color=self.colors["bg_primary"])
        loading_frame.pack(fill="x", padx=30)

        loading_label = self.create_label(
            loading_frame, text="",
            font=("Segoe UI", 11),
            text_color="#f59e0b",
            fg_color=self.colors["bg_primary"],
        )
        loading_label.pack()

        # Buttons
        btn_frame = self.create_frame(dialog, fg_color=self.colors["bg_primary"])
        btn_frame.pack(fill="x", padx=30, pady=(10, 20))

        if self.use_ctk:
            cancel_btn = ctk.CTkButton(
                btn_frame, text="Annuler", width=120,
                fg_color=self.colors["bg_secondary"],
                hover_color=self.colors["border"],
                text_color=self.colors["text_primary"],
                font=("Segoe UI", 11, "bold"),
                corner_radius=8,
                command=dialog.destroy,
            )
        else:
            cancel_btn = tk.Button(
                btn_frame, text="Annuler",
                bg=self.colors["bg_secondary"],
                fg=self.colors["text_primary"],
                font=("Segoe UI", 11, "bold"),
                command=dialog.destroy,
            )
        cancel_btn.pack(side="right", padx=(10, 0))

        if self.use_ctk:
            save_btn = ctk.CTkButton(
                btn_frame, text="Sauvegarder", width=140,
                fg_color="#3b82f6", hover_color="#2563eb",
                text_color="#ffffff",
                font=("Segoe UI", 11, "bold"),
                corner_radius=8,
                command=lambda: self._do_edit_agent(
                    dialog, agent_key, name_entry, role_entry,
                    loading_label, save_btn, cancel_btn
                ),
            )
        else:
            save_btn = tk.Button(
                btn_frame, text="Sauvegarder",
                bg="#3b82f6", fg="#ffffff",
                font=("Segoe UI", 11, "bold"),
                command=lambda: self._do_edit_agent(
                    dialog, agent_key, name_entry, role_entry,
                    loading_label, save_btn, cancel_btn
                ),
            )
        save_btn.pack(side="right")

    def _do_edit_agent(self, dialog, agent_key, name_entry, role_entry,
                       loading_label, save_btn, cancel_btn):
        """Process agent edit"""
        if self.use_ctk:
            new_name = name_entry.get().strip()
            new_role = role_entry.get("0.0", "end-1c").strip()
        else:
            new_name = name_entry.get().strip()
            new_role = role_entry.get("1.0", "end-1c").strip()

        if not new_name:
            messagebox.showwarning("Nom requis", "Veuillez entrer un nom pour l'agent.")
            return
        if not new_role:
            messagebox.showwarning("Rôle requis", "Veuillez décrire le rôle de l'agent.")
            return

        old_data = self.custom_agents[agent_key]
        name_changed = new_name != old_data["name"]
        desc_changed = new_role != old_data["desc"]

        if not name_changed and not desc_changed:
            dialog.destroy()
            return

        if desc_changed:
            # Description changed -> regenerate system prompt via Ollama
            if self.use_ctk:
                save_btn.configure(state="disabled")
                cancel_btn.configure(state="disabled")
            else:
                save_btn.configure(state="disabled")
                cancel_btn.configure(state="disabled")

            self._animate_loading(loading_label, dialog, 0)

            threading.Thread(
                target=self._regenerate_agent_prompt,
                args=(dialog, agent_key, new_name, new_role, loading_label),
                daemon=True,
            ).start()
        else:
            # Only name changed -> just update name
            self.custom_agents[agent_key]["name"] = new_name
            self._save_custom_agents()
            self._register_custom_agent_in_orchestrator(agent_key, self.custom_agents[agent_key])
            dialog.destroy()
            self._refresh_agents_grid()
            self._show_notification("✅ Agent modifié !", "#10b981")

    def _regenerate_agent_prompt(self, dialog, agent_key, new_name, new_role, loading_label):
        """Regenerate an agent's system prompt after description change"""
        prompt = f"""Tu dois créer un system prompt pour un agent IA spécialisé.

Voici le nom de l'agent: {new_name}
Voici la description de son rôle: {new_role}

Génère un system prompt complet en suivant EXACTEMENT ce format:

Tu es {new_name}, un expert en [domaine basé sur la description].

EXPERTISE: [liste des domaines d'expertise basée sur la description]

COMPORTEMENT:
- [comportement 1]
- [comportement 2]
- [comportement 3]
- [comportement 4]
- [comportement 5]

FORMAT DE RÉPONSE:
- [format 1]
- [format 2]
- [format 3]
- [format 4]

Réponds UNIQUEMENT avec le system prompt, rien d'autre. Pas d'explication, pas de commentaire.
Génère aussi à la fin, sur une ligne séparée commençant par "TEMPERATURE:", une valeur de température entre 0.1 et 0.9 adaptée au rôle (précis = bas, créatif = haut).
Ensuite, sur une dernière ligne séparée commençant par "SUMMARY:", génère un résumé de 3-4 mots maximum du rôle de l'agent, avec la première lettre en majuscule (ex: "Recherche web avancée" ou "Analyse de données")."""

        try:
            response = self.llm.generate(
                prompt=prompt,
                system_prompt="Tu es un assistant qui génère des system prompts pour des agents IA. Réponds uniquement avec le contenu demandé, sans explications."
            )

            if response:
                temperature = 0.5
                short_desc = new_role[:30]
                system_prompt = response.strip()

                if "SUMMARY:" in system_prompt:
                    parts = system_prompt.rsplit("SUMMARY:", 1)
                    system_prompt = parts[0].strip()
                    short_desc = parts[1].strip().split("\n")[0].strip()
                    if short_desc:
                        short_desc = short_desc[0].upper() + short_desc[1:]

                if "TEMPERATURE:" in system_prompt:
                    parts = system_prompt.rsplit("TEMPERATURE:", 1)
                    system_prompt = parts[0].strip()
                    try:
                        temp_str = parts[1].strip().split()[0]
                        temperature = float(temp_str)
                        temperature = max(0.1, min(0.9, temperature))
                    except (ValueError, IndexError):
                        temperature = 0.5

                self.custom_agents[agent_key]["name"] = new_name
                self.custom_agents[agent_key]["desc"] = new_role
                self.custom_agents[agent_key]["short_desc"] = short_desc
                self.custom_agents[agent_key]["system_prompt"] = system_prompt
                self.custom_agents[agent_key]["temperature"] = temperature
                self._save_custom_agents()
                self._register_custom_agent_in_orchestrator(agent_key, self.custom_agents[agent_key])

                # Remove cached agent from orchestrator so it gets recreated
                if agent_key in self.orchestrator.agents:
                    del self.orchestrator.agents[agent_key]

                def on_success():
                    if dialog.winfo_exists():
                        dialog.destroy()
                    self._refresh_agents_grid()
                    self._show_notification("✅ Agent modifié !", "#10b981")

                self.parent.after(0, on_success)
            else:
                def on_error():
                    if dialog.winfo_exists():
                        loading_label.configure(
                            text="❌ Erreur: Ollama n'a pas répondu.",
                            text_color="#ef4444"
                        )
                self.parent.after(0, on_error)

        except Exception as e:
            def on_error():
                if dialog.winfo_exists():
                    loading_label.configure(
                        text=f"❌ Erreur: {str(e)[:60]}",
                        text_color="#ef4444"
                    )
            self.parent.after(0, on_error)

    # === Delete Agent ===

    def _delete_custom_agent(self, agent_key):
        """Delete a custom agent"""
        if agent_key not in self.custom_agents:
            return

        agent_name = self.custom_agents[agent_key]["name"]
        confirm = messagebox.askyesno(
            "Supprimer l'agent",
            f"Voulez-vous vraiment supprimer l'agent '{agent_name}' ?"
        )

        if confirm:
            # Remove from data
            del self.custom_agents[agent_key]
            self._save_custom_agents()

            # Remove from orchestrator
            if agent_key in self.orchestrator.agents:
                del self.orchestrator.agents[agent_key]
            if agent_key in AVAILABLE_AGENTS:
                del AVAILABLE_AGENTS[agent_key]
            if agent_key in self.agent_buttons:
                del self.agent_buttons[agent_key]

            # Remove from workflow if present
            self.custom_workflow = [
                (at, n, c) for at, n, c in self.custom_workflow if at != agent_key
            ]
            self.update_pipeline_display()

            # Refresh grid
            self._refresh_agents_grid()
            self._show_notification("❌ Agent supprimé", "#ef4444")

    def _refresh_agents_grid(self):
        """Refresh the entire agents grid (rebuild custom agents)"""
        if not self.agents_grid:
            return

        # Remove custom agent cards (children after the 9 built-in cards)
        children = self.agents_grid.winfo_children()
        # Built-in agents have 9 cards (indices 0-8), remove the rest
        for child in children[9:]:
            child.destroy()

        # Re-render custom agents
        self._render_custom_agents_in_grid(9)
