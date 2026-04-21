"""Mixin de base : initialisation et structure générale de l'interface Agents."""

import os

from interfaces.agents._common import ctk, tk
from interfaces.resource_monitor import ResourceMonitor
from interfaces.workflow_canvas import WorkflowCanvas  # noqa: F401  (réexport utile)
from core.agent_orchestrator import AgentOrchestrator
from core.config import get_default_model as _get_default_model
from models.local_llm import LocalLLM


class BaseMixin:
    """Construction + layout racine de l'interface Agents."""

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
        self._builtin_agents_info: dict = {}

        # Section-based output
        self._output_scroll = None
        self._output_sections = []
        self._active_section = None
        self._welcome_label = None
        self.stats_labels = {}

        # Custom workflow (drag & drop)
        self.custom_workflow = []  # List of (agent_type, name, color) tuples
        self._drag_data = {"agent": None, "toplevel": None}
        self.pipeline_frame = None
        self.drop_zone_frame = None
        self.task_section_frame = None

        # File attachment (agents page)
        self._agent_preview_frame = None
        self._agent_pending_files = []
        self._agent_file_btn = None

        # Workflow canvas (n8n-style)
        self.workflow_canvas: WorkflowCanvas | None = None
        self.canvas_outer = None

        # Resource monitor
        self.resource_monitor = ResourceMonitor(interval=3.0)
        self._resource_bars: dict = {}
        self._sparkline_canvases: dict = {}
        self._resource_labels: dict = {}

        # Custom agents created by user
        self.custom_agents = {}  # key -> {name, desc, color, system_prompt, temperature}
        self.custom_agents_file = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            "data", "custom_agents.json"
        )
        self.agents_grid = None  # Reference to agents grid for adding custom agents
        self._load_custom_agents()

        # LLM for generating system prompts
        self.llm = LocalLLM(model=_get_default_model())

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
