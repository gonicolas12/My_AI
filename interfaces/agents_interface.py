"""
Interface Agents IA - Module pour l'onglet Agents dans la GUI moderne
Gère l'interface utilisateur pour le système multi-agents basé sur Ollama
"""

import threading
import tkinter as tk
from datetime import datetime
from tkinter import messagebox, scrolledtext, simpledialog

try:
    import customtkinter as ctk

    CTK_AVAILABLE = True
except ImportError:
    CTK_AVAILABLE = False
    ctk = tk

from core.agent_orchestrator import AgentOrchestrator, WorkflowTemplates


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
        self.execution_history = []

        # Référ ences UI
        self.agent_buttons = {}
        self.output_text = None
        self.task_entry = None
        self.status_label = None
        self.stats_labels = {}

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

        # Workflows pré-configurés
        self.create_workflow_shortcuts(main_scroll)

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
        """Crée une carte d'agent cliquable"""
        # Frame de la carte
        card_frame = self.create_frame(parent, fg_color=self.colors["bg_secondary"])

        if self.use_ctk:
            card_frame.configure(
                corner_radius=12, border_width=2, border_color=self.colors["border"]
            )

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
            font=("Segoe UI", 10),
            text_color=self.colors["text_secondary"],
            fg_color=self.colors["bg_secondary"],
            wraplength=200,
        )
        desc_label.pack(fill="x", pady=(10, 0))

        # Bouton de sélection
        select_btn = self.create_button(
            content_frame,
            text="Sélectionner",
            command=lambda: self.select_agent(agent_type, name),
            fg_color=color,
            hover_color=self._darken_color(color),
            text_color="#ffffff",
            font=("Segoe UI", 11, "bold"),
            height=35,
        )
        select_btn.pack(fill="x", pady=(15, 0))

        # Stocker la référence
        self.agent_buttons[agent_type] = (card_frame, select_btn, color)

        return card_frame

    def select_agent(self, agent_type, agent_name):
        """Sélectionne un agent"""
        self.current_agent = agent_type

        # Mettre à jour l'apparence des cartes
        for at, (card, _btn, original_color) in self.agent_buttons.items():
            if at == agent_type:
                # Agent sélectionné - border accent
                if self.use_ctk:
                    card.configure(border_color=original_color, border_width=3)
            else:
                # Agents non sélectionnés - border normale
                if self.use_ctk:
                    card.configure(border_color=self.colors["border"], border_width=2)

        # Mettre à jour le statut
        if self.status_label:
            self.status_label.configure(
                text=f"✅ Agent sélectionné: {agent_name}", text_color="#10b981"
            )

        # Focus sur la zone de saisie
        if self.task_entry:
            self.task_entry.focus_set()

    def create_task_input(self, parent):
        """Crée la zone de saisie de tâche"""
        section_frame = self.create_frame(parent, fg_color=self.colors["bg_primary"])
        section_frame.grid(row=3, column=0, sticky="ew", padx=30, pady=(20, 10))

        # Titre
        title = self.create_label(
            section_frame,
            text="Décrivez la Tâche",
            font=("Segoe UI", 14, "bold"),
            text_color=self.colors["text_primary"],
            fg_color=self.colors["bg_primary"],
        )
        title.pack(anchor="w", pady=(0, 10))

        # Frame pour input + bouton
        input_frame = self.create_frame(
            section_frame, fg_color=self.colors["bg_primary"]
        )
        input_frame.pack(fill="x")
        input_frame.grid_columnconfigure(0, weight=1)

        # Zone de texte (avec scrollbar si besoin)
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

        self.task_entry.grid(row=0, column=0, sticky="ew", padx=(0, 10))

        # Placeholder
        self._set_placeholder(
            "Décrivez la tâche pour l'agent sélectionné...\n\nExemple: Crée une fonction Python qui trie une liste de nombres"
        )

        # Bouton Exécuter
        execute_btn = self.create_button(
            input_frame,
            text="▶ Exécuter",
            command=self.execute_agent_task,
            fg_color=self.colors["accent"],
            hover_color="#ff5730",
            text_color="#ffffff",
            font=("Segoe UI", 13, "bold"),
            width=150,
            height=100,
        )
        execute_btn.grid(row=0, column=1)

        # Label de statut
        self.status_label = self.create_label(
            section_frame,
            text="Sélectionnez un agent ci-dessus",
            font=("Segoe UI", 10),
            text_color=self.colors["text_secondary"],
            fg_color=self.colors["bg_primary"],
        )
        self.status_label.pack(anchor="w", pady=(10, 0))

    def create_workflow_shortcuts(self, parent):
        """Crée les raccourcis vers les workflows"""
        section_frame = self.create_frame(parent, fg_color=self.colors["bg_primary"])
        section_frame.grid(row=4, column=0, sticky="ew", padx=30, pady=(20, 10))

        # Titre
        title = self.create_label(
            section_frame,
            text="⚡ Workflows Multi-Agents",
            font=("Segoe UI", 14, "bold"),
            text_color=self.colors["text_primary"],
            fg_color=self.colors["bg_primary"],
        )
        title.pack(anchor="w", pady=(0, 10))

        desc = self.create_label(
            section_frame,
            text="Workflows pré-configurés qui utilisent plusieurs agents en séquence",
            font=("Segoe UI", 10),
            text_color=self.colors["text_secondary"],
            fg_color=self.colors["bg_primary"],
        )
        desc.pack(anchor="w", pady=(0, 15))

        # Grid de workflows
        workflows_grid = self.create_frame(
            section_frame, fg_color=self.colors["bg_primary"]
        )
        workflows_grid.pack(fill="x")

        workflows = [
            {
                "name": "Développement Complet",
                "desc": "Planner → Code → Debug",
                "icon": "💻",
                "color": "#3b82f6",
                "action": self.workflow_dev,
            },
            {
                "name": "Recherche & Doc",
                "desc": "Research → Analyst → Creative",
                "icon": "📚",
                "color": "#10b981",
                "action": self.workflow_research,
            },
            {
                "name": "Debug Assisté",
                "desc": "Debug → Code",
                "icon": "🔧",
                "color": "#ef4444",
                "action": self.workflow_debug,
            },
        ]

        for idx, wf in enumerate(workflows):
            btn_frame = self.create_frame(
                workflows_grid, fg_color=self.colors["bg_secondary"]
            )
            if self.use_ctk:
                btn_frame.configure(corner_radius=10)
            btn_frame.grid(row=0, column=idx, padx=8, pady=0, sticky="ew")
            workflows_grid.grid_columnconfigure(idx, weight=1, uniform="workflow")

            # Contenu
            content = self.create_frame(btn_frame, fg_color=self.colors["bg_secondary"])
            content.pack(fill="both", expand=True, padx=15, pady=15)

            # Icône + Nom
            header = self.create_frame(content, fg_color=self.colors["bg_secondary"])
            header.pack(fill="x")

            icon_lbl = self.create_label(
                header,
                text=wf["icon"],
                font=("Segoe UI", 20),
                fg_color=self.colors["bg_secondary"],
            )
            icon_lbl.pack(side="left", padx=(0, 8))

            name_lbl = self.create_label(
                header,
                text=wf["name"],
                font=("Segoe UI", 12, "bold"),
                text_color=self.colors["text_primary"],
                fg_color=self.colors["bg_secondary"],
            )
            name_lbl.pack(side="left")

            # Description
            desc_lbl = self.create_label(
                content,
                text=wf["desc"],
                font=("Segoe UI", 9),
                text_color=self.colors["text_secondary"],
                fg_color=self.colors["bg_secondary"],
            )
            desc_lbl.pack(fill="x", pady=(5, 10))

            # Bouton
            wf_btn = self.create_button(
                content,
                text="Lancer",
                command=wf["action"],
                fg_color=wf["color"],
                hover_color=self._darken_color(wf["color"]),
                text_color="#ffffff",
                font=("Segoe UI", 10, "bold"),
                height=30,
            )
            wf_btn.pack(fill="x")

    def create_output_area(self, parent):
        """Crée la zone de sortie des résultats"""
        section_frame = self.create_frame(parent, fg_color=self.colors["bg_primary"])
        section_frame.grid(row=5, column=0, sticky="nsew", padx=30, pady=(20, 10))

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

1️⃣ Sélectionnez un agent ci-dessus
2️⃣ Décrivez votre tâche
3️⃣ Cliquez sur "Exécuter"

Les résultats apparaîtront ici en temps réel.
Vous pouvez aussi utiliser les workflows pré-configurés pour des tâches complexes.

💡 Astuce: Les agents gardent une mémoire de leurs tâches précédentes!
"""
        self.output_text.insert("1.0", welcome_msg)
        self._make_output_readonly()

    def create_stats_section(self, parent):
        """Crée la section des statistiques"""
        section_frame = self.create_frame(parent, fg_color=self.colors["bg_secondary"])
        section_frame.grid(row=6, column=0, sticky="ew", padx=30, pady=(10, 30))

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
        """Exécute une tâche avec l'agent sélectionné"""
        if self.is_processing:
            messagebox.showwarning(
                "Agent Occupé", "Un agent est déjà en train de traiter une tâche."
            )
            return

        if not self.current_agent:
            messagebox.showwarning(
                "Aucun Agent", "Veuillez sélectionner un agent avant d'exécuter."
            )
            return

        # Récupérer la tâche
        task = self._get_task_text()
        if not task or task.strip() == "":
            messagebox.showwarning(
                "Tâche Vide", "Veuillez décrire la tâche à effectuer."
            )
            return

        # Exécuter dans un thread séparé
        self.is_processing = True
        self._update_status("⏳ Traitement en cours...", "#f59e0b")
        threading.Thread(
            target=self._execute_task_thread,
            args=(self.current_agent, task),
            daemon=True,
        ).start()

    def _execute_task_thread(self, agent_type, task):
        """Exécute la tâche dans un thread séparé avec streaming"""
        try:
            # Afficher la tâche
            self._append_output(
                f"\n{'='*80}\n🤖 Agent: {agent_type.upper()}\n📋 Tâche: {task}\n{'='*80}\n\n"
            )

            # Exécuter avec streaming
            result = self.orchestrator.execute_single_task_stream(
                agent_type=agent_type,
                task=task,
                on_token=self._append_output  # Callback pour chaque token
            )

            # Afficher la fin
            if result.get("success"):
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
                    "result": result,
                    "timestamp": datetime.now().isoformat(),
                }
            )

        except Exception as e:
            self._append_output(f"❌ Exception: {str(e)}\n\n")
            self._update_status("❌ Erreur critique", "#ef4444")
        finally:
            self.is_processing = False

    def workflow_dev(self):
        """Lance le workflow de développement"""
        task = self._get_task_text()
        if not task:
            task = self._prompt_workflow_task(
                "Développement Complet",
                "Exemple: Un système de gestion de tâches avec SQLite",
            )
        if not task:
            return

        self._execute_workflow("dev", task)

    def workflow_research(self):
        """Lance le workflow de recherche"""
        task = self._get_task_text()
        if not task:
            task = self._prompt_workflow_task(
                "Recherche & Documentation",
                "Exemple: L'intelligence artificielle dans la santé",
            )
        if not task:
            return

        self._execute_workflow("research", task)

    def workflow_debug(self):
        """Lance le workflow de debug"""
        task = self._get_task_text()
        if not task:
            messagebox.showinfo(
                "Debug Workflow",
                "Pour le debug, décrivez le code et l'erreur dans la zone de saisie.\n\n"
                "Exemple: Mon code plante avec IndexError quand j'accède à ma_liste[5]",
            )
            return

        # Pour debug, on ne peut pas utiliser le template standard
        self._execute_single_debug(task)

    def _execute_workflow(self, workflow_type, description):
        """Exécute un workflow multi-agents"""
        if self.is_processing:
            messagebox.showwarning("Workflow Actif", "Un workflow est déjà en cours.")
            return

        self.is_processing = True
        self._update_status(f"⚙️ Workflow {workflow_type} en cours...", "#f59e0b")
        threading.Thread(
            target=self._workflow_thread, args=(workflow_type, description), daemon=True
        ).start()

    def _workflow_thread(self, workflow_type, description):
        """Exécute le workflow dans un thread avec streaming"""
        try:
            # Sélectionner le template
            if workflow_type == "dev":
                task_desc, workflow = WorkflowTemplates.code_development(description)
            elif workflow_type == "research":
                task_desc, workflow = WorkflowTemplates.research_and_document(
                    description
                )
            else:
                return

            # Afficher l'info
            self._append_output(f"\n{'='*80}\n⚡ WORKFLOW: {task_desc}\n{'='*80}\n\n")

            # Callbacks pour le streaming
            def on_step_start(step_idx, agent_type, task):
                """Appelé au début de chaque étape"""
                self._append_output(
                    f"\n--- Étape {step_idx}/{len(workflow)}: {agent_type.upper()} ---\n\n"
                )
                self._append_output(f"📋 Tâche: {task}\n\n")

            def on_step_complete(step_idx, result):
                """Appelé à la fin de chaque étape"""
                if not result.get("success"):
                    self._append_output(f"\n❌ Erreur: {result.get('error')}\n")
                self._append_output(f"\n\n⏱️ Étape {step_idx} terminée\n\n")

            # Exécuter avec streaming
            result = self.orchestrator.execute_multi_agent_task_stream(
                task_desc,
                workflow,
                on_step_start=on_step_start,
                on_token=self._append_output,  # Streaming des tokens
                on_step_complete=on_step_complete,
            )

            # Résumé final
            summary = result["summary"]
            self._append_output(f"\n{'='*80}\n📊 RÉSUMÉ\n{'='*80}\n")
            self._append_output(f"Tâches: {summary['total_tasks']}\n")
            self._append_output(f"Réussies: {summary['successful']}\n")
            self._append_output(f"Taux de succès: {summary['success_rate']:.1%}\n")
            self._append_output(f"Terminé: {result.get('timestamp', 'N/A')}\n\n")

            self._update_status(
                f"✅ Workflow terminé ({summary['success_rate']:.0%} succès)", "#10b981"
            )
            self._update_stats()

        except Exception as e:
            self._append_output(f"❌ Erreur workflow: {str(e)}\n\n")
            self._update_status("❌ Erreur workflow", "#ef4444")
        finally:
            self.is_processing = False

    def _execute_single_debug(self, _task):
        """Exécute une tâche de debug simple"""
        self.current_agent = "debug"
        self.execute_agent_task()

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

    def _prompt_workflow_task(self, workflow_name, example):
        """Demande la description de la tâche pour un workflow"""

        return simpledialog.askstring(
            workflow_name,
            f"Décrivez le projet pour le workflow:\n\n{example}",
            parent=self.parent,
        )

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
