"""
Interface Agents IA - Module pour l'onglet Agents dans la GUI moderne
Gère l'interface utilisateur pour le système multi-agents basé sur Ollama
"""

import json
import os
import random
import re
import threading
import time
import tkinter as tk
from datetime import datetime
from tkinter import filedialog, messagebox, scrolledtext
from processors.pdf_processor import PDFProcessor
from processors.docx_processor import DOCXProcessor

try:
    import customtkinter as ctk

    CTK_AVAILABLE = True
except ImportError:
    CTK_AVAILABLE = False
    ctk = tk

from core.agent_orchestrator import AgentOrchestrator
from core.config import get_default_model as _get_default_model
from interfaces.resource_monitor import ResourceMonitor

try:
    from interfaces.gui.syntax_highlighting import \
        SyntaxHighlightingMixin as _SyntaxMixin

    class SyntaxColorHelper(_SyntaxMixin):
        """Wrapper exposing GUI syntax-highlighting helpers to the agents pane."""

        def __init__(self, colors):
            self.colors = colors

        def configure_tags(self, tw):
            """Configure all language colour tags on *tw*."""
            self._configure_formatting_tags(tw)  # pylint: disable=protected-access

        def highlight_line(self, tw, line, lang):
            """Tokenise *line* for *lang* and insert coloured spans into *tw*."""
            code_map = {}
            try:
                dispatch = {
                    "python":     self._analyze_python_tokens,
                    "javascript": self._analyze_javascript_tokens,
                    "js":         self._analyze_javascript_tokens,
                    "typescript": self._analyze_javascript_tokens,
                    "ts":         self._analyze_javascript_tokens,
                    "css":        self._analyze_css_tokens,
                    "html":       self._analyze_html_tokens,
                    "xml":        self._analyze_html_tokens,
                    "bash":       self._analyze_bash_tokens,
                    "shell":      self._analyze_bash_tokens,
                    "sh":         self._analyze_bash_tokens,
                    "sql":        self._analyze_sql_tokens,
                    "mysql":      self._analyze_sql_tokens,
                    "postgresql": self._analyze_sql_tokens,
                    "sqlite":     self._analyze_sql_tokens,
                    "java":       self._analyze_java_tokens,
                    "go":         self._analyze_go_tokens,
                    "golang":     self._analyze_go_tokens,
                    "ruby":       self._analyze_ruby_tokens,
                    "rb":         self._analyze_ruby_tokens,
                    "swift":      self._analyze_swift_tokens,
                    "php":        self._analyze_php_tokens,
                    "perl":       self._analyze_perl_tokens,
                    "pl":         self._analyze_perl_tokens,
                    "rust":       self._analyze_rust_tokens,
                    "rs":         self._analyze_rust_tokens,
                }  # pylint: disable=protected-access
                if lang in ("c", "cpp", "c++", "cxx"):
                    self._analyze_cpp_tokens(line, 0, code_map, lang)  # pylint: disable=protected-access
                elif lang in ("csharp", "cs", "c#"):
                    self._analyze_csharp_tokens(line, 0, code_map)  # pylint: disable=protected-access
                elif lang in dispatch:
                    dispatch[lang](line, 0, code_map)
                else:
                    tw.insert("end", line, "code_block")
                    return
            except Exception:
                tw.insert("end", line, "code_block")
                return

            n = len(line)
            i = 0
            while i < n:
                if i in code_map:
                    tag = code_map[i][1]
                    j = i + 1
                    while j < n and j in code_map and code_map[j][1] == tag:
                        j += 1
                    tw.insert("end", line[i:j], tag)
                    i = j
                else:
                    j = i + 1
                    while j < n and j not in code_map:
                        j += 1
                    tw.insert("end", line[i:j], "code_block")
                    i = j

    # Singleton used only for token analysis (no colors needed)
    _SYNTAX_ANALYZER = SyntaxColorHelper({})
    _SYNTAX_AVAILABLE = True
except Exception:
    SyntaxColorHelper = None # pylint: disable=invalid-name
    _SYNTAX_ANALYZER = None
    _SYNTAX_AVAILABLE = False
from interfaces.workflow_canvas import WorkflowCanvas
from models.ai_agents import AVAILABLE_AGENTS, AIAgent
from models.local_llm import LocalLLM


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
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
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

        # Highlight canvas outer frame border when dragging over it
        if self.workflow_canvas and self.workflow_canvas.is_over(event.x_root, event.y_root):
            try:
                if self.use_ctk and hasattr(self, 'canvas_outer'):
                    self.canvas_outer.configure(
                        border_color=self.colors["accent"], border_width=3
                    )
            except Exception:
                pass
        else:
            try:
                if self.use_ctk and hasattr(self, 'canvas_outer'):
                    self.canvas_outer.configure(
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

        # Reset canvas outer border
        if self.use_ctk and hasattr(self, 'canvas_outer'):
            try:
                self.canvas_outer.configure(
                    border_color=self.colors["border"], border_width=2
                )
            except Exception:
                pass

        if not agent_data:
            self._drag_data = {"agent": None, "toplevel": None}
            return

        agent_type, name, color = agent_data

        # Trouver l'icône de l'agent
        icon = self._get_agent_icon(agent_type)

        # Drop uniquement sur le canvas de workflow visuel
        if self.workflow_canvas and self.workflow_canvas.is_over(event.x_root, event.y_root):
            self.workflow_canvas.drop_agent(
                agent_type, name, color, event.x_root, event.y_root, icon=icon
            )

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

    # ── Icônes des agents ──────────────────────────────────────────

    _AGENT_ICONS = {
        "code": "🐍", "web": "🌐", "analyst": "📊", "creative": "✨",
        "debug": "🐛", "planner": "📋", "security": "🛡",
        "optimizer": "⚡", "datascience": "🧬",
    }

    def _get_agent_icon(self, agent_type: str) -> str:
        """Retourne l'emoji d'un type d'agent."""
        return self._AGENT_ICONS.get(agent_type, "🤖")

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
        # Vider aussi le canvas visuel
        if self.workflow_canvas:
            self.workflow_canvas.clear()
        self._update_status(
            "Glissez-déposez des agents pour créer votre workflow",
            self.colors["text_secondary"],
        )

    # ── Gestion des fichiers attachés dans l'interface agents ──

    def _agent_load_file(self, file_type: str):
        """Charge un fichier depuis le sélecteur et l'ajoute en aperçu dans la zone agents."""

        filetypes_map = {
            "PDF": [("Fichiers PDF", "*.pdf")],
            "DOCX": [("Fichiers Word", "*.docx")],
            "Excel": [("Excel & CSV", "*.xlsx *.xls *.csv")],
            "Code": [("Code", "*.py *.js *.html *.css *.json *.xml *.md *.txt"), ("Tous", "*.*")],
            "Image": [("Images", "*.png *.jpg *.jpeg *.gif *.bmp *.webp"), ("Tous", "*.*")],
        }
        ft = filetypes_map.get(file_type, [("Tous", "*.*")])
        file_path = filedialog.askopenfilename(title=f"Sélectionner un fichier {file_type}", filetypes=ft)
        if file_path:
            self._agent_add_preview(file_path, file_type)

    def _agent_add_preview(self, file_path: str, file_type: str):
        """Ajoute un aperçu miniature dans la zone de tâche agents."""
        filename = os.path.basename(file_path)
        type_icons = {"PDF": "📄", "DOCX": "📝", "Excel": "📊", "Code": "💻", "Image": "🖼"}
        icon = type_icons.get(file_type, "📎")

        bg = self.colors.get("bg_secondary", "#2a2a2a")
        accent = self.colors.get("accent", "#ff6b47")

        if self.use_ctk:
            thumb = ctk.CTkFrame(
                self._agent_preview_frame, fg_color=bg, corner_radius=6,
                border_width=1, border_color=self.colors.get("border", "#404040"),
            )
        else:
            thumb = tk.Frame(self._agent_preview_frame, bg=bg, relief="solid", bd=1)
        thumb.pack(side="left", padx=(0, 8), pady=4)

        display_name = filename if len(filename) <= 20 else filename[:17] + "..."
        if self.use_ctk:
            lbl = ctk.CTkLabel(
                thumb, text=f"{icon} {display_name}", font=("Segoe UI", 11),
                text_color=self.colors.get("text_primary", "#ffffff"), fg_color="transparent",
            )
        else:
            lbl = tk.Label(
                thumb, text=f"{icon} {display_name}", bg=bg,
                fg=self.colors.get("text_primary", "#ffffff"), font=("Segoe UI", 11),
            )
        lbl.pack(side="left", padx=(8, 4), pady=4)

        def _remove():
            self._agent_pending_files = [
                (p, t, w) for p, t, w in self._agent_pending_files if w is not thumb
            ]
            thumb.destroy()
            if not self._agent_pending_files:
                self._agent_preview_frame.grid_remove()

        if self.use_ctk:
            close_btn = ctk.CTkButton(
                thumb, text="✕", width=24, height=24,
                fg_color="transparent", hover_color=accent,
                text_color=self.colors.get("text_secondary", "#aaaaaa"),
                font=("Segoe UI", 12, "bold"), corner_radius=4, command=_remove,
            )
        else:
            close_btn = tk.Button(
                thumb, text="✕", bg=bg, fg=self.colors.get("text_secondary", "#aaaaaa"),
                font=("Segoe UI", 10, "bold"), relief="flat", bd=0, command=_remove, cursor="hand2",
            )
        close_btn.pack(side="left", padx=(0, 6), pady=4)

        self._agent_pending_files.append((file_path, file_type, thumb))
        self._agent_preview_frame.grid()

        print(f"📎 [AGENTS] Fichier attaché: {filename} ({file_type})")

    def _agent_get_pending_files(self) -> list:
        """Retourne la liste des fichiers attachés aux agents [(path, type), ...]."""
        return [(p, t) for p, t, _ in self._agent_pending_files]

    def _agent_clear_previews(self):
        """Retire tous les aperçus de fichiers de l'interface agents."""
        for _, _, widget in self._agent_pending_files:
            try:
                widget.destroy()
            except Exception:
                pass
        self._agent_pending_files = []
        self._agent_preview_frame.grid_remove()

    @staticmethod
    def _read_attached_file(file_path: str, file_type: str) -> str:
        """Lit le contenu d'un fichier attaché et retourne le texte brut."""
        ext = os.path.splitext(file_path)[1].lower()

        if file_type == "PDF" or ext == ".pdf":
            try:
                proc = PDFProcessor()
                result = proc.process_file(file_path)
                return result.get("content", "")
            except ImportError:
                pass

        if file_type == "DOCX" or ext in (".docx", ".doc"):
            try:
                proc = DOCXProcessor()
                result = proc.process_file(file_path)
                return result.get("content", "")
            except ImportError:
                pass

        # Fichiers texte / code / CSV / markdown — lecture directe
        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                return f.read(200_000)  # limiter à 200k chars
        except Exception:
            # Fallback binaire
            with open(file_path, "rb") as f:
                return f.read(100_000).decode("utf-8", errors="replace")

    # ── Sauvegarde / Chargement / Export de workflow ──

    def _save_workflow(self):
        """Sauvegarde le workflow actuel dans un fichier JSON."""
        if not self.workflow_canvas:
            return
        filepath = filedialog.asksaveasfilename(
            title="Sauvegarder le workflow",
            defaultextension=".json",
            filetypes=[("Fichiers JSON", "*.json"), ("Tous", "*.*")],
            initialfile="workflow.json",
        )
        if filepath:
            self.workflow_canvas.save_to_file(filepath)
            if hasattr(self, "show_notification"):
                self.show_notification("💾 Workflow sauvegardé", "success", 1500)
            print(f"💾 [WORKFLOW] Sauvegardé: {filepath}")

    def _load_workflow(self):
        """Charge un workflow depuis un fichier JSON."""
        if not self.workflow_canvas:
            return
        filepath = filedialog.askopenfilename(
            title="Charger un workflow",
            filetypes=[("Fichiers JSON", "*.json"), ("Tous", "*.*")],
        )
        if filepath:
            success = self.workflow_canvas.load_from_file(filepath)
            if success:
                self._on_canvas_changed()
                if hasattr(self, "show_notification"):
                    self.show_notification("📂 Workflow chargé", "success", 1500)
                print(f"📂 [WORKFLOW] Chargé: {filepath}")
            else:
                if hasattr(self, "show_notification"):
                    self.show_notification("❌ Erreur chargement workflow", "error", 2000)

    def _export_workflow(self):
        """Exporte le workflow et ses résultats en fichier texte."""
        if not self.workflow_canvas:
            return
        filepath = filedialog.asksaveasfilename(
            title="Exporter le workflow",
            defaultextension=".md",
            filetypes=[("Markdown", "*.md"), ("Texte", "*.txt"), ("Tous", "*.*")],
            initialfile="workflow_export.md",
        )
        if filepath:
            try:
                data = self.workflow_canvas.to_dict()
                lines = ["# Workflow Export\n", f"**Version**: {data.get('version', '7.0.0')}\n"]
                lines.append(f"**Nodes**: {len(data.get('nodes', {}))}\n")
                lines.append(f"**Connections**: {len(data.get('connections', []))}\n\n")
                for nid, node in data.get("nodes", {}).items():
                    lines.append(f"## {node.get('icon', '🤖')} {node.get('name', nid)}\n")
                    lines.append(f"- Type: {node.get('agent_type', 'unknown')}\n")
                    lines.append(f"- Status: {node.get('status', 'idle')}\n\n")
                with open(filepath, "w", encoding="utf-8") as f:
                    f.writelines(lines)
                if hasattr(self, "show_notification"):
                    self.show_notification("📤 Workflow exporté", "success", 1500)
                print(f"📤 [WORKFLOW] Exporté: {filepath}")
            except Exception as e:
                print(f"❌ [WORKFLOW] Erreur export: {e}")

    def _on_canvas_changed(self):
        """Callback quand le canvas de workflow est modifié."""
        if not self.workflow_canvas:
            return
        # Synchroniser custom_workflow avec le canvas
        self.custom_workflow = list(self.workflow_canvas.get_ordered_agents())
        self.current_agent = (
            self.custom_workflow[-1][0] if self.custom_workflow else None
        )
        self.update_pipeline_display()

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

        # Frame pour input + boutons
        input_frame = self.create_frame(
            section_frame, fg_color=self.colors["bg_primary"]
        )
        input_frame.pack(fill="x")
        input_frame.grid_columnconfigure(0, weight=1)

        # Wrapper pour la zone de texte (contient preview + textbox + bouton +)
        task_wrapper = self.create_frame(
            input_frame, fg_color=self.colors["input_bg"], corner_radius=8
        )
        if self.use_ctk:
            task_wrapper.configure(border_width=2, border_color=self.colors["border"])
        task_wrapper.grid(row=0, column=0, rowspan=3, sticky="nsew", padx=(0, 10))
        task_wrapper.grid_columnconfigure(0, weight=1)
        # Row 1 (text area) prend tout l'espace restant à l'intérieur du wrapper
        task_wrapper.grid_rowconfigure(1, weight=1)
        task_wrapper.grid_propagate(False)
        # Hauteur fixe du wrapper : identique à l'originale
        if self.use_ctk:
            task_wrapper.configure(height=160)
        else:
            task_wrapper.configure(height=160)

        # ── Zone d'aperçu des documents attachés (agents) ──
        self._agent_preview_frame = self.create_frame(
            task_wrapper, fg_color=self.colors["input_bg"], corner_radius=0
        )
        self._agent_preview_frame.grid(row=0, column=0, sticky="ew", padx=6, pady=(6, 0))
        self._agent_preview_frame.grid_remove()
        self._agent_pending_files = []

        # Zone de texte
        if self.use_ctk:
            self.task_entry = ctk.CTkTextbox(
                task_wrapper,
                height=100,
                font=("Segoe UI", 12),
                fg_color=self.colors["input_bg"],
                text_color=self.colors["text_primary"],
                border_width=0,
                corner_radius=0,
            )
        else:
            self.task_entry = scrolledtext.ScrolledText(
                task_wrapper,
                height=5,
                font=("Segoe UI", 12),
                bg=self.colors["input_bg"],
                fg=self.colors["text_primary"],
                insertbackground=self.colors["text_primary"],
                relief="flat",
                borderwidth=0,
            )

        self.task_entry.grid(row=1, column=0, sticky="nsew", padx=4, pady=2)

        # ── Barre d'outils sous le textbox (bouton + pour fichiers) ──
        task_toolbar = self.create_frame(
            task_wrapper, fg_color=self.colors["input_bg"], corner_radius=0
        )
        task_toolbar.grid(row=2, column=0, sticky="ew", padx=4, pady=(0, 4))

        _agent_file_entries = [
            ("📄  PDF",         lambda: self._agent_load_file("PDF")),
            ("📝  DOCX",        lambda: self._agent_load_file("DOCX")),
            ("📊  Excel / CSV", lambda: self._agent_load_file("Excel")),
            ("💻  Code",        lambda: self._agent_load_file("Code")),
            ("🖼  Image",       lambda: self._agent_load_file("Image")),
        ]
        _agent_popup_ref = [None]

        def _close_agent_popup(popup):
            try:
                popup.destroy()
            except Exception:
                pass
            _agent_popup_ref[0] = None

        def _open_agent_file_menu():
            if _agent_popup_ref[0] is not None:
                _close_agent_popup(_agent_popup_ref[0])
                return
            bg     = self.colors.get("bg_secondary", "#1e1e1e")
            fg     = self.colors.get("text_primary",  "#ffffff")
            accent = self.colors.get("accent",        "#ff6b47")
            font   = ("Segoe UI", 11)
            popup = tk.Toplevel(self.parent.winfo_toplevel())
            popup.overrideredirect(True)
            popup.configure(bg=bg)
            popup.attributes("-topmost", True)
            _agent_popup_ref[0] = popup
            for i, (_lbl, _cmd) in enumerate(_agent_file_entries):
                def _make_cb(cmd, pop=popup):
                    def _cb():
                        _close_agent_popup(pop)
                        cmd()
                    return _cb
                btn = tk.Label(
                    popup, text=_lbl, bg=bg, fg=fg, font=font,
                    anchor="w", padx=14, pady=7, cursor="hand2",
                )
                btn.grid(row=i, column=0, sticky="ew")
                popup.grid_columnconfigure(0, weight=1)
                cb = _make_cb(_cmd)
                btn.bind("<Button-1>", lambda _e, c=cb: c())
                btn.bind("<Enter>", lambda _e, b=btn: b.configure(bg=accent, fg="#ffffff"))
                btn.bind("<Leave>", lambda _e, b=btn: b.configure(bg=bg, fg=fg))
            popup.update_idletasks()
            ph = popup.winfo_reqheight()
            bx = self._agent_file_btn.winfo_rootx()
            by = self._agent_file_btn.winfo_rooty() - ph
            popup.geometry(f"+{bx}+{by}")
            def _on_focus_out(_e):
                self.parent.winfo_toplevel().after(50, lambda: _close_agent_popup(popup) if _agent_popup_ref[0] is popup else None)
            popup.bind("<FocusOut>", _on_focus_out)
            popup.bind("<Escape>", lambda _e: _close_agent_popup(popup))
            self.parent.winfo_toplevel().bind("<Button-1>",
                           lambda _e: _close_agent_popup(popup) if _agent_popup_ref[0] is popup else None,
                           add="+")
            popup.focus_set()

        if self.use_ctk:
            self._agent_file_btn = ctk.CTkButton(
                task_toolbar, text="＋", command=_open_agent_file_menu,
                fg_color=self.colors.get("bg_secondary", "#2a2a2a"),
                hover_color=self.colors.get("button_hover", "#3a3a3a"),
                text_color=self.colors.get("text_secondary", "#aaaaaa"),
                font=("Segoe UI", 16), corner_radius=6, width=36, height=28,
            )
        else:
            self._agent_file_btn = tk.Button(
                task_toolbar, text="＋", command=_open_agent_file_menu,
                bg=self.colors.get("bg_secondary", "#2a2a2a"),
                fg=self.colors.get("text_secondary", "#aaaaaa"),
                font=("Segoe UI", 16), relief="flat", bd=0, padx=6,
            )
        self._agent_file_btn.pack(side="left", padx=(2, 0))

        # Placeholder
        self._set_placeholder(
            "Décrivez la tâche à confier aux agents sélectionnés...\n"
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

        # Bouton Clear Workflow (rouge)
        if self.use_ctk:
            clear_btn = ctk.CTkButton(
                buttons_frame,
                text="❌ Clear Workflow",
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
                text="❌ Clear Workflow",
                command=self.clear_workflow,
                bg="#dc2626",
                fg="#ffffff",
                font=("Segoe UI", 13, "bold"),
                border=0,
                relief="flat",
            )
        clear_btn.pack(fill="both", expand=True, pady=(4, 0))

        # drop_zone_frame / pipeline_frame conservés comme attributs vides
        # pour compatibilité — le canvas visuel remplace l'ancienne zone de drop
        self.drop_zone_frame = None
        self.pipeline_frame = None

        # ── Canvas de workflow visuel (style n8n) ──────────────────
        self.canvas_outer = self.create_frame(
            section_frame, fg_color=self.colors["bg_secondary"]
        )
        canvas_outer = self.canvas_outer
        if self.use_ctk:
            canvas_outer.configure(
                corner_radius=10, border_width=2,
                border_color=self.colors["border"],
            )
        canvas_outer.pack(fill="both", expand=True, pady=(10, 0))

        # ── Barre de titre + boutons workflow ──
        canvas_header = self.create_frame(
            canvas_outer, fg_color=self.colors["bg_secondary"]
        )
        canvas_header.pack(fill="x", padx=12, pady=(8, 0))

        canvas_title = self.create_label(
            canvas_header,
            text="🔗 Workflow Visuel — glissez des agents, connectez les ports",
            font=("Segoe UI", 10),
            text_color=self.colors["text_secondary"],
            fg_color=self.colors["bg_secondary"],
        )
        canvas_title.pack(side="left")

        # Boutons Save / Load / Export
        wf_btn_style = {
            "font": ("Segoe UI", 10),
            "corner_radius": 4,
            "width": 70,
            "height": 24,
        } if self.use_ctk else {}

        def _make_wf_btn(parent, text, cmd):
            if self.use_ctk:
                return ctk.CTkButton(
                    parent, text=text, command=cmd,
                    fg_color=self.colors.get("bg_primary", "#1a1a1a"),
                    hover_color=self.colors.get("button_hover", "#3a3a3a"),
                    text_color=self.colors.get("text_secondary", "#aaaaaa"),
                    **wf_btn_style,
                )
            else:
                return tk.Button(
                    parent, text=text, command=cmd,
                    bg=self.colors.get("bg_primary", "#1a1a1a"),
                    fg=self.colors.get("text_secondary", "#aaaaaa"),
                    font=("Segoe UI", 10), relief="flat", bd=0,
                )

        export_btn = _make_wf_btn(canvas_header, "📤 Export", self._export_workflow)
        export_btn.pack(side="right", padx=(4, 0))
        load_btn = _make_wf_btn(canvas_header, "📂 Load", self._load_workflow)
        load_btn.pack(side="right", padx=(4, 0))
        save_btn = _make_wf_btn(canvas_header, "💾 Save", self._save_workflow)
        save_btn.pack(side="right", padx=(4, 0))

        self.workflow_canvas = WorkflowCanvas(
            canvas_outer,
            self.colors,
            width=800,
            height=380,
            on_workflow_changed=self._on_canvas_changed,
            snap_to_grid=True,
        )
        self.workflow_canvas.pack(fill="both", expand=True, padx=4, pady=4)

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

        # ── Section Consommation de ressources ─────────────────────
        separator = self.create_frame(content, fg_color=self.colors["border"])
        separator.pack(fill="x", pady=(15, 10))
        if self.use_ctk:
            separator.configure(height=1)
        else:
            separator.config(height=1)

        res_title = self.create_label(
            content,
            text="⚡ Consommation de ressources (Ollama)",
            font=("Segoe UI", 12, "bold"),
            text_color=self.colors["text_primary"],
            fg_color=self.colors["bg_secondary"],
        )
        res_title.pack(anchor="w", pady=(0, 10))

        # Métriques à afficher
        resource_defs = [
            ("cpu",   "CPU",             "%"),
            ("ram",   "RAM",             ""),
            ("gpu",   "GPU",             "%"),
            ("vram",  "VRAM",            ""),
            ("infer", "Temps inférence", ""),
            ("tps",   "Tokens/sec",      ""),
        ]

        res_grid = self.create_frame(content, fg_color=self.colors["bg_secondary"])
        res_grid.pack(fill="x")
        res_grid.grid_columnconfigure(1, weight=1)

        for row_idx, (key, label, _unit) in enumerate(resource_defs):
            # Label
            lbl = self.create_label(
                res_grid, text=label,
                font=("Segoe UI", 10),
                text_color=self.colors["text_secondary"],
                fg_color=self.colors["bg_secondary"],
                anchor="w", width=120,
            )
            lbl.grid(row=row_idx, column=0, sticky="w", padx=(0, 8), pady=3)

            # Progress bar (canvas-based for color control)
            bar_canvas = tk.Canvas(
                res_grid, height=16, bg=self.colors["bg_primary"],
                highlightthickness=0, bd=0,
            )
            bar_canvas.grid(row=row_idx, column=1, sticky="ew", padx=(0, 8), pady=3)
            self._resource_bars[key] = bar_canvas

            # Value label
            val_lbl = self.create_label(
                res_grid, text="—",
                font=("Segoe UI", 10, "bold"),
                text_color=self.colors["text_primary"],
                fg_color=self.colors["bg_secondary"],
                anchor="e", width=100,
            )
            val_lbl.grid(row=row_idx, column=2, sticky="e", padx=(0, 8), pady=3)
            self._resource_labels[key] = val_lbl

            # Sparkline mini-graph
            spark = tk.Canvas(
                res_grid, width=80, height=16,
                bg=self.colors["bg_primary"], highlightthickness=0, bd=0,
            )
            spark.grid(row=row_idx, column=3, sticky="e", pady=3)
            self._sparkline_canvases[key] = spark

        # Démarrer le monitoring
        self.resource_monitor.add_callback(self._on_resource_update)
        self.resource_monitor.start()

    def execute_agent_task(self):
        """Exécute une tâche avec l'agent ou le workflow personnalisé"""
        if self.is_processing:
            messagebox.showwarning(
                "Agent Occupé", "Un agent est déjà en train de traiter une tâche."
            )
            return

        # Vérifier s'il y a des nœuds sur le canvas OU dans le workflow classique
        has_canvas_nodes = (
            self.workflow_canvas and len(self.workflow_canvas.nodes) > 0
        )
        if not self.custom_workflow and not has_canvas_nodes:
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

        # Inclure le contenu des fichiers attachés dans le prompt
        attached = self._agent_get_pending_files()
        if attached:
            file_sections = []
            for fpath, ftype in attached:
                try:
                    content = self._read_attached_file(fpath, ftype)
                    if content:
                        fname = os.path.basename(fpath)
                        file_sections.append(
                            f"--- Fichier joint : {fname} ({ftype}) ---\n{content}"
                        )
                except Exception as exc:
                    file_sections.append(
                        f"--- Fichier joint : {os.path.basename(fpath)} ---\n"
                        f"[Erreur de lecture : {exc}]"
                    )
            if file_sections:
                task = task + "\n\n" + "\n\n".join(file_sections)
            self._agent_clear_previews()

        self.is_interrupted = False
        self._set_execute_button_stop()

        # Utiliser le plan d'exécution du canvas si des nœuds y sont présents
        if has_canvas_nodes:
            plan = self.workflow_canvas.get_execution_plan()
            self.is_processing = True
            if plan["mode"] in ("sequential", "dag"):
                self._update_status("⏳ Workflow visuel en cours...", "#f59e0b")
                threading.Thread(
                    target=self._execute_canvas_workflow_thread,
                    args=(task, plan),
                    daemon=True,
                ).start()
            elif plan["mode"] == "single":
                nid = plan["steps"][0]["nodes"][0]
                nd = plan["node_map"][nid]
                agent_type = nd["agent_type"]
                self._update_status("⏳ Traitement en cours...", "#f59e0b")
                threading.Thread(
                    target=self._execute_task_thread,
                    args=(agent_type, task, nd["name"], nd.get("color"), nid),
                    daemon=True,
                ).start()
            else:
                # parallel (tous isolés)
                self._update_status("⏳ Exécution parallèle...", "#f59e0b")
                threading.Thread(
                    target=self._execute_canvas_workflow_thread,
                    args=(task, plan),
                    daemon=True,
                ).start()
        elif len(self.custom_workflow) == 1:
            # Mode agent unique (workflow classique)
            agent_type, wf_name, wf_color = self.custom_workflow[0]
            self.is_processing = True
            self._update_status("⏳ Traitement en cours...", "#f59e0b")
            threading.Thread(
                target=self._execute_task_thread,
                args=(agent_type, task, wf_name, wf_color),
                daemon=True,
            ).start()
        else:
            # Mode workflow personnalisé multi-agents (classique)
            self.is_processing = True
            self._update_status("⏳ Workflow personnalisé en cours...", "#f59e0b")
            threading.Thread(
                target=self._execute_custom_workflow_thread,
                args=(task,),
                daemon=True,
            ).start()

    def _execute_task_thread(self, agent_type, task, explicit_name=None, explicit_color=None, canvas_node_id=None):
        """Exécute la tâche dans un thread séparé avec streaming"""
        try:
            # Préparer la zone de sortie
            self._clear_output_sections_sync()

            # Mettre à jour le statut du nœud canvas si applicable
            if canvas_node_id is not None:
                self._set_canvas_node_status(canvas_node_id, "running")

            # Trouver le nom et la couleur de l'agent
            agent_colors = {
                "code": "#3b82f6", "web": "#10b981", "analyst": "#8b5cf6",
                "creative": "#f59e0b", "debug": "#ef4444", "planner": "#06b6d4",
                "security": "#ec4899", "optimizer": "#14b8a6", "datascience": "#f97316",
            }
            agent_names = {
                "code": "CodeAgent", "web": "WebAgent", "analyst": "AnalystAgent",
                "creative": "CreativeAgent", "debug": "DebugAgent",
                "planner": "PlannerAgent", "security": "SecurityAgent",
                "optimizer": "OptimizerAgent", "datascience": "DataScienceAgent",
            }
            if explicit_color:
                color = explicit_color
            else:
                color = agent_colors.get(agent_type)
                if not color:
                    ca = self.custom_agents.get(agent_type, {})
                    color = ca.get("color", "#ff6b47")
            if explicit_name:
                name = explicit_name
            else:
                name = agent_names.get(agent_type)
                if not name:
                    ca = self.custom_agents.get(agent_type, {})
                    name = ca.get("name", agent_type.capitalize())

            section = self._create_step_section_sync(name, color)
            self._active_section = section

            # Exécuter avec streaming
            t_start = time.time()
            result = self.orchestrator.execute_single_task_stream(
                agent_type=agent_type,
                task=task,
                on_token=self._on_token_received
            )
            elapsed_ms = (time.time() - t_start) * 1000
            self.resource_monitor.update_inference(elapsed_ms, 0)

            if self.is_interrupted:
                self._finish_section(section, success=False)
                self._update_status("⛔ Génération interrompue", "#ef4444")
                if canvas_node_id is not None:
                    self._set_canvas_node_status(canvas_node_id, "error")
            elif result.get("success"):
                self._finish_section(section, success=True)
                self._update_status(
                    f"✅ Tâche terminée avec {result['agent']}", "#10b981"
                )
                if canvas_node_id is not None:
                    self._set_canvas_node_status(canvas_node_id, "done")
            else:
                self._finish_section(section, success=False)
                self._update_status("❌ Erreur lors de l'exécution", "#ef4444")
                if canvas_node_id is not None:
                    self._set_canvas_node_status(canvas_node_id, "error")

            self._active_section = None
            self._update_stats()

            self.execution_history.append(
                {
                    "agent": agent_type,
                    "task": task,
                    "result": result if not self.is_interrupted else {"success": False, "error": "interrupted"},
                    "timestamp": datetime.now().isoformat(),
                }
            )

        except Exception:
            self._finish_section(self._active_section, success=False)
            self._active_section = None
            self._update_status("❌ Erreur critique", "#ef4444")
            if canvas_node_id is not None:
                self._set_canvas_node_status(canvas_node_id, "error")
        finally:
            self.is_processing = False
            self.is_interrupted = False
            self._set_execute_button_normal()

    def _execute_custom_workflow_thread(self, task):
        """Exécute un workflow personnalisé multi-agents"""
        try:
            self._clear_output_sections_sync()

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

            step_sections = {}

            def on_step_start(step_idx, agent_type, _step_task):
                if self.is_interrupted:
                    return
                name = next(
                    (n for at, n, _ in self.custom_workflow if at == agent_type),
                    agent_type,
                )
                color = next(
                    (c for at, _n, c in self.custom_workflow if at == agent_type),
                    "#ff6b47",
                )
                sec = self._create_step_section_sync(
                    f"Étape {step_idx}/{len(workflow)}: {name}", color
                )
                step_sections[step_idx] = sec
                self._active_section = sec

            def on_step_complete(step_idx, result):
                if self.is_interrupted:
                    return
                sec = step_sections.get(step_idx)
                self._finish_section(sec, success=result.get("success", False))
                self._active_section = None

            result = self.orchestrator.execute_multi_agent_task_stream(
                task,
                workflow,
                on_step_start=on_step_start,
                on_token=self._on_token_received,
                on_step_complete=on_step_complete,
                on_should_stop=lambda: self.is_interrupted,
            )

            if self.is_interrupted:
                self._update_status("⛔ Génération interrompue", "#ef4444")
            else:
                summary = result["summary"]
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

    def _execute_canvas_workflow_thread(self, task, plan):
        """Exécute un workflow basé sur le plan d'exécution du canvas (DAG)."""
        try:
            self._clear_output_sections_sync()

            node_map = plan["node_map"]
            steps = plan["steps"]
            isolated = plan["isolated"]
            total_steps = len(steps)
            results_by_node = {}
            success_count = 0
            total_count = 0

            for nid in node_map:
                self._set_canvas_node_status(nid, "idle")

            for step_idx, step in enumerate(steps):
                if self.is_interrupted:
                    break

                nids = step["nodes"]
                is_parallel = step["parallel"]

                if is_parallel:
                    # Label d'en-tête
                    par_names = ", ".join(node_map[n]["name"] for n in nids)
                    self._create_output_header_sync(
                        f"⚡ Étape {step_idx+1}/{total_steps} — parallèle: {par_names}"
                    )

                    # Créer les sections dépliantes (repliées pendant l'exécution)
                    par_sections = {}
                    for nid in nids:
                        nd = node_map[nid]
                        sec = self._create_step_section_sync(
                            nd["name"], nd.get("color", "#ff6b47"), expanded=True
                        )
                        par_sections[nid] = sec

                    # Exécuter en parallèle — chaque agent stream en temps réel
                    threads = []
                    local_results = {}
                    par_lock = threading.Lock()

                    def _make_runner(shared_results, shared_lock, sections_map):
                        def run_agent(nid):
                            if self.is_interrupted:
                                return
                            nd = node_map[nid]
                            self._set_canvas_node_status(nid, "running")
                            agent_task = task
                            parents = [
                                c["from"]
                                for c in (self.workflow_canvas.connections if self.workflow_canvas else [])
                                if c["to"] == nid
                            ]
                            if parents:
                                context_parts = [
                                    f"[{node_map[pid]['name']}]:\n{results_by_node[pid]}"
                                    for pid in parents
                                    if pid in results_by_node
                                ]
                                if context_parts:
                                    _sep = "\n---\n"
                                    agent_task = (
                                        f"Contexte précédent:\n{_sep.join(context_parts)}\n\n"
                                        f"Tâche: {task}"
                                    )

                            sec = sections_map[nid]  # pylint: disable=cell-var-from-loop

                            def stream_token(token, _sec=sec):
                                self._append_to_section(_sec, token)
                                return not self.is_interrupted

                            t_start = time.time()
                            result = self.orchestrator.execute_single_task_stream(
                                agent_type=nd["agent_type"],
                                task=agent_task,
                                on_token=stream_token,
                            )
                            elapsed = (time.time() - t_start) * 1000
                            self.resource_monitor.update_inference(elapsed, 0)

                            with shared_lock:
                                shared_results[nid] = result
                            if result.get("success"):
                                self._set_canvas_node_status(nid, "done")
                                with shared_lock:
                                    shared_results[nid] = result.get("result", "")
                            else:
                                self._set_canvas_node_status(nid, "error")
                        return run_agent

                    agent_runner = _make_runner(local_results, par_lock, par_sections)
                    for nid in nids:
                        t = threading.Thread(target=agent_runner, args=(nid,), daemon=True)
                        threads.append(t)
                        t.start()
                    for t in threads:
                        t.join()

                    # Finaliser les sections
                    for nid in nids:
                        sec = par_sections.get(nid)
                        if sec is None:
                            continue
                        ok = isinstance(local_results.get(nid), str) or (
                            isinstance(local_results.get(nid), dict) and local_results[nid].get("success")
                        )
                        self._finish_section(sec, success=ok)

                    # Collecter les résultats
                    for nid, res in local_results.items():
                        total_count += 1
                        if isinstance(res, str):
                            results_by_node[nid] = res
                            success_count += 1
                        elif isinstance(res, dict) and res.get("success"):
                            results_by_node[nid] = res.get("result", "")
                            success_count += 1
                else:
                    # Séquentiel
                    nid = nids[0]
                    nd = node_map[nid]

                    sec = self._create_step_section_sync(
                        f"Étape {step_idx+1}/{total_steps}: {nd['name']}",
                        nd.get("color", "#ff6b47"),
                    )
                    self._active_section = sec
                    self._set_canvas_node_status(nid, "running")

                    agent_task = task
                    if self.workflow_canvas:
                        parents = [c["from"] for c in self.workflow_canvas.connections
                                   if c["to"] == nid]
                        if parents:
                            context_parts = [
                                f"[{node_map[p]['name']}]:\n{results_by_node[p]}"
                                for p in parents
                                if p in results_by_node
                            ]
                            if context_parts:
                                _sep = "\n---\n"
                                agent_task = (
                                    f"Contexte précédent:\n{_sep.join(context_parts)}\n\n"
                                    f"Tâche: {task}"
                                )

                    t_start = time.time()
                    result = self.orchestrator.execute_single_task_stream(
                        agent_type=nd["agent_type"],
                        task=agent_task,
                        on_token=self._on_token_received,
                    )
                    elapsed = (time.time() - t_start) * 1000
                    self.resource_monitor.update_inference(elapsed, 0)

                    total_count += 1
                    if result.get("success"):
                        results_by_node[nid] = result.get("result", "")
                        success_count += 1
                        self._set_canvas_node_status(nid, "done")
                        self._finish_section(sec, success=True)
                    else:
                        self._set_canvas_node_status(nid, "error")
                        self._finish_section(sec, success=False)
                    self._active_section = None

            # Exécuter les nœuds isolés
            for nid in isolated:
                if self.is_interrupted:
                    break
                if nid not in node_map:
                    continue
                nd = node_map[nid]
                sec = self._create_step_section_sync(
                    f"Agent isolé: {nd['name']}", nd.get("color", "#ff6b47")
                )
                self._active_section = sec
                self._set_canvas_node_status(nid, "running")
                t_start = time.time()
                result = self.orchestrator.execute_single_task_stream(
                    agent_type=nd["agent_type"],
                    task=task,
                    on_token=self._on_token_received,
                )
                elapsed = (time.time() - t_start) * 1000
                self.resource_monitor.update_inference(elapsed, 0)
                total_count += 1
                ok = result.get("success", False)
                if ok:
                    success_count += 1
                    self._set_canvas_node_status(nid, "done")
                else:
                    self._set_canvas_node_status(nid, "error")
                self._finish_section(sec, success=ok)
                self._active_section = None

            # Résumé
            if self.is_interrupted:
                self._update_status("⛔ Génération interrompue", "#ef4444")
            else:
                rate = success_count / max(total_count, 1)
                self._update_status(
                    f"✅ Workflow visuel terminé ({rate:.0%} succès)", "#10b981"
                )

            self._update_stats()
            self.execution_history.append({
                "agent": "workflow_canvas",
                "task": task,
                "result": {"success": success_count == total_count,
                           "total": total_count, "successful": success_count},
                "timestamp": datetime.now().isoformat(),
            })

        except Exception as e:
            self._update_status(f"❌ Erreur workflow: {str(e)}", "#ef4444")
        finally:
            self._active_section = None
            self.is_processing = False
            self.is_interrupted = False
            self._set_execute_button_normal()

    def _set_canvas_node_status(self, nid: int, status: str):
        """Met à jour le statut visuel d'un nœud du canvas."""
        if self.workflow_canvas:
            def _update():
                self.workflow_canvas.set_node_status(nid, status)
            if self.parent.winfo_exists():
                self.parent.after(0, _update)

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

    # ── Section-based output management ────────────────────────────

    def _clear_output_sections(self):
        """Supprime toutes les sections de sortie."""
        for sec in self._output_sections:
            try:
                sec["container"].destroy()
            except Exception:
                pass
        self._output_sections.clear()
        self._active_section = None
        if self._welcome_label:
            try:
                self._welcome_label.destroy()
            except Exception:
                pass
            self._welcome_label = None

    def _create_step_section(self, name, color="#ff6b47", expanded=True):
        """Crée une section dépliante dans la zone de résultats (main thread)."""
        section = {"name": name, "color": color, "expanded": expanded}

        bg1 = self.colors.get("bg_primary", "#0f0f0f")
        bg2 = self.colors.get("bg_secondary", "#1a1a1a")
        bg3 = self.colors.get("bg_tertiary", "#2d2d2d")
        txt2 = self.colors.get("text_secondary", "#9ca3af")

        container = tk.Frame(self._output_scroll, bg=bg1)
        container.pack(fill="x", pady=(0, 6), padx=4)
        section["container"] = container

        # Header (clickable)
        header = tk.Frame(container, bg=bg2, cursor="hand2")
        header.pack(fill="x")

        # Color indicator strip
        indicator = tk.Frame(header, bg=color, width=4)
        indicator.pack(side="left", fill="y")

        # Arrow
        arrow_var = tk.StringVar(value="▾" if expanded else "▸")
        arrow = tk.Label(
            header, textvariable=arrow_var, font=("Segoe UI", 18),
            fg=txt2, bg=bg2, cursor="hand2",
        )
        arrow.pack(side="left", padx=(10, 4), pady=6)
        section["arrow_var"] = arrow_var

        # Name
        name_lbl = tk.Label(
            header, text=name, font=("Segoe UI", 12, "bold"),
            fg="#ffffff", bg=bg2, cursor="hand2",
        )
        name_lbl.pack(side="left", pady=8)

        # Status (right)
        status_var = tk.StringVar(value="⏳ En cours...")
        status_lbl = tk.Label(
            header, textvariable=status_var, font=("Segoe UI", 9),
            fg=txt2, bg=bg2,
        )
        status_lbl.pack(side="right", padx=12, pady=8)
        section["status_var"] = status_var

        # Content frame with agent-colored left border
        border_wrap = tk.Frame(container, bg=color)
        section["border_wrap"] = border_wrap
        if expanded:
            border_wrap.pack(fill="x", padx=(16, 4), pady=(2, 4))

        content = tk.Frame(border_wrap, bg=bg1)
        section["content"] = content
        content.pack(fill="x", padx=(2, 0))

        # Scrollable text area — hauteur max fixe avec scrollbar custom
        text_container = tk.Frame(content, bg=bg1)
        text_container.pack(fill="x")

        tw = tk.Text(
            text_container, wrap="word", font=("Segoe UI", 11),
            bg=bg1, fg=self.colors.get("text_primary", "#ffffff"),
            relief="flat", borderwidth=0, padx=12, pady=10,
            height=3, state="disabled",
            insertbackground=self.colors.get("text_primary", "#ffffff"),
        )
        tw.pack(side="left", fill="both", expand=True)

        # Custom dark scrollbar (canvas-based, matching CTk style)
        sb_width = 6
        sb_canvas = tk.Canvas(
            text_container, width=sb_width + 4, bg=bg1,
            highlightthickness=0, borderwidth=0,
        )
        sb_canvas.pack(side="right", fill="y", padx=(0, 2))
        sb_thumb = sb_canvas.create_rectangle(0, 0, 0, 0, fill=bg3, outline="", width=0)
        section["_sb_canvas"] = sb_canvas
        section["_sb_thumb"] = sb_thumb

        def _update_scrollbar(*args):
            try:
                first, last = float(args[0]), float(args[1])
                if last - first >= 1.0:
                    sb_canvas.coords(sb_thumb, 0, 0, 0, 0)
                    return
                h = sb_canvas.winfo_height()
                y1 = int(first * h)
                y2 = int(last * h)
                x_pad = (sb_width + 4 - sb_width) // 2
                sb_canvas.coords(sb_thumb, x_pad, y1, x_pad + sb_width, y2)
                sb_canvas.itemconfig(sb_thumb, fill=bg3)
            except Exception:
                pass

        tw.configure(yscrollcommand=_update_scrollbar)

        def _sb_drag(event):
            h = sb_canvas.winfo_height()
            if h > 0:
                tw.yview_moveto(event.y / h)

        sb_canvas.bind("<B1-Motion>", _sb_drag)
        sb_canvas.bind("<Button-1>", _sb_drag)

        def _sb_enter(_event):
            sb_canvas.itemconfig(sb_thumb, fill=txt2)
        def _sb_leave(_event):
            sb_canvas.itemconfig(sb_thumb, fill=bg3)
        sb_canvas.bind("<Enter>", _sb_enter)
        sb_canvas.bind("<Leave>", _sb_leave)

        self._setup_markdown_tags(tw)
        section["text_widget"] = tw

        # Mousewheel scrolle le contenu du Text (pas le parent)
        def _text_scroll(event):
            tw.yview_scroll(int(-3 * (event.delta / 120)), "units")
            return "break"
        tw.bind("<MouseWheel>", _text_scroll)
        sb_canvas.bind("<MouseWheel>", _text_scroll)

        # Toggle on click
        def toggle(_event=None):
            self._toggle_section(section)

        for w in (header, arrow, name_lbl):
            w.bind("<Button-1>", toggle)

        self._output_sections.append(section)
        return section

    def _create_step_section_sync(self, name, color="#ff6b47", expanded=True):
        """Thread-safe: crée une section sur le thread principal et attend."""
        result = [None]
        event = threading.Event()

        def create():
            result[0] = self._create_step_section(name, color, expanded)
            event.set()

        if self.parent.winfo_exists():
            self.parent.after(0, create)
            event.wait(timeout=5.0)
        return result[0]

    def _clear_output_sections_sync(self):
        """Thread-safe: efface toutes les sections sur le thread principal."""
        event = threading.Event()

        def clear():
            self._clear_output_sections()
            event.set()

        if self.parent.winfo_exists():
            self.parent.after(0, clear)
            event.wait(timeout=2.0)

    def _create_output_header_sync(self, text):
        """Thread-safe: crée un label d'en-tête dans la zone de résultats."""
        event = threading.Event()

        def create():
            lbl = tk.Label(
                self._output_scroll, text=text, font=("Segoe UI", 10),
                fg=self.colors.get("text_secondary", "#9ca3af"),
                bg=self.colors.get("bg_primary", "#0f0f0f"),
                anchor="w",
            )
            lbl.pack(fill="x", padx=16, pady=(8, 2))
            event.set()

        if self.parent.winfo_exists():
            self.parent.after(0, create)
            event.wait(timeout=2.0)

    def _toggle_section(self, section):
        """Déplie/replie une section."""
        toggle_target = section.get("border_wrap", section["content"])
        if section["expanded"]:
            toggle_target.pack_forget()
            section["arrow_var"].set("▸")
            section["expanded"] = False
        else:
            toggle_target.pack(fill="x", padx=(16, 4), pady=(2, 4))
            section["arrow_var"].set("▾")
            section["expanded"] = True

    def _append_to_section(self, section, text):
        """Ajoute du texte à une section avec formatage Markdown progressif (thread-safe)."""
        if section is None:
            return

        # Initialiser le buffer de ligne si nécessaire
        if "_line_buf" not in section:
            section["_line_buf"] = ""
            section["_in_code_block"] = False
            section["_code_lang"] = ""
            section["_first_line"] = True
            section["_table_buf"] = []  # buffer pour accumuler les lignes de tableau

        section["_line_buf"] += text

        # Extraire et formater les lignes complètes
        while "\n" in section["_line_buf"]:
            line, section["_line_buf"] = section["_line_buf"].split("\n", 1)
            self._format_and_insert_line(section, line, newline=True)

    def _format_and_insert_line(self, section, line, newline=True):  # pylint: disable=unused-argument,W0613
        """Formate et insère une ligne complète avec le bon style Markdown."""
        stripped = line.strip()
        table_buf = section.get("_table_buf", [])

        # Détection de ligne de tableau
        is_table_line = ("|" in stripped and stripped.startswith("|") and stripped.endswith("|"))
        is_table_sep = bool(re.match(r'^\s*\|?[\s:]*-{2,}[\s:]*\|', stripped))

        if is_table_line or is_table_sep:
            table_buf.append(line)
            section["_table_buf"] = table_buf
            return  # accumulate, don't render yet

        # Si on avait des lignes de tableau en buffer et qu'on reçoit une non-table line
        if table_buf:
            self._flush_table_buffer(section)

        self._insert_single_line(section, line)

    def _flush_table_buffer(self, section):
        """Rend le tableau accumulé avec box-drawing characters."""
        table_buf = section.get("_table_buf", [])
        if not table_buf:
            return
        section["_table_buf"] = []

        def update():
            tw = section["text_widget"]
            tw.configure(state="normal")

            # Parser toutes les lignes du tableau
            separator_pattern = r'^\s*\|?[\s:]*-{2,}[\s:]*\|'
            data_rows = []
            for tl in table_buf:
                s = tl.strip()
                if re.match(separator_pattern, s):
                    continue  # skip separator
                cells = [c.strip() for c in s.strip("|").split("|")]
                data_rows.append(cells)

            if not data_rows:
                tw.configure(state="disabled")
                return

            # Calculer largeurs de colonnes
            max_cols = max(len(r) for r in data_rows)
            widths = []
            max_col_w = max(10, 100 // max(max_cols, 1) - 3)
            for col in range(max_cols):
                w = 3
                for row in data_rows:
                    if col < len(row):
                        cell_text = re.sub(r'\*\*([^*]+)\*\*', r'\1', row[col])
                        cell_text = re.sub(r'`([^`]+)`', r'\1', cell_text)
                        w = max(w, len(cell_text))
                widths.append(min(w, max_col_w))

            # Newline before table
            if not section.get("_first_line"):
                tw.insert("end", "\n")
            section["_first_line"] = False

            # Top border
            tw.insert("end", "\u250c" + "\u252c".join("\u2500" * (w + 2) for w in widths) + "\u2510", "table_border")

            for row_idx, cells in enumerate(data_rows):
                tw.insert("end", "\n")
                is_header = row_idx == 0

                # Separator after header
                if row_idx == 1:
                    tw.insert("end", "\u251c" + "\u253c".join("\u2500" * (w + 2) for w in widths) + "\u2524", "table_border")
                    tw.insert("end", "\n")

                tw.insert("end", "\u2502", "table_border")
                for col_idx, width in enumerate(widths):
                    cell = cells[col_idx] if col_idx < len(cells) else ""
                    # Display length without markdown markers
                    disp = re.sub(r'\*\*([^*]+)\*\*', r'\1', cell)
                    disp = re.sub(r'`([^`]+)`', r'\1', disp)
                    disp_len = len(disp)
                    if disp_len > width:
                        cell = disp[:width - 1] + "\u2026"
                        disp_len = width
                    padding = max(0, width - disp_len)
                    lpad = padding // 2
                    rpad = padding - lpad
                    tw.insert("end", " " + " " * lpad, "table_border")
                    # Insert cell content with inline formatting
                    tag = "table_header" if is_header else "table_cell"
                    self._insert_table_cell(tw, cell, tag)
                    tw.insert("end", " " * rpad + " ", "table_border")
                    tw.insert("end", "\u2502", "table_border")

            # Bottom border
            tw.insert("end", "\n")
            tw.insert("end", "\u2514" + "\u2534".join("\u2500" * (w + 2) for w in widths) + "\u2518", "table_border")

            tw.configure(state="disabled")
            self._resize_section_text(tw)
            tw.see("end")
            if section.get("expanded", False):
                self._auto_scroll_output()

        if self.parent.winfo_exists():
            self.parent.after(0, update)

    def _insert_table_cell(self, tw, cell_content, base_tag):
        """Insère le contenu d'une cellule de tableau avec gras/code inline."""
        pattern = r'(\*\*[^*]+\*\*|`[^`]+`)'
        parts = re.split(pattern, cell_content)
        for part in parts:
            if not part:
                continue
            if part.startswith("**") and part.endswith("**"):
                tw.insert("end", part[2:-2], "table_cell_bold")
            elif part.startswith("`") and part.endswith("`"):
                tw.insert("end", part[1:-1], "code_inline")
            else:
                tw.insert("end", part, base_tag)

    def _insert_single_line(self, section, line):
        """Insère une seule ligne formatée (non-table)."""
        def update():
            tw = section["text_widget"]
            tw.configure(state="normal")

            stripped = line.strip()

            # Ajouter un saut de ligne sauf pour la première ligne
            if not section.get("_first_line"):
                tw.insert("end", "\n")
            section["_first_line"] = False

            # Code block markers
            if stripped.startswith("```"):
                if section["_in_code_block"]:
                    section["_in_code_block"] = False
                    section["_code_lang"] = ""
                else:
                    section["_in_code_block"] = True
                    section["_code_lang"] = stripped[3:].strip().lower()
                    # Language label intentionally hidden — used only for highlighting logic
                tw.configure(state="disabled")
                self._resize_section_text(tw)
                return

            if section["_in_code_block"]:
                self._highlight_code_line(tw, line, section.get("_code_lang", ""))
                tw.configure(state="disabled")
                self._resize_section_text(tw)
                return

            # Headers
            if stripped.startswith("#### "):
                tw.insert("end", stripped[5:], "h4")
            elif stripped.startswith("### "):
                tw.insert("end", stripped[4:], "h3")
            elif stripped.startswith("## "):
                tw.insert("end", stripped[3:], "h2")
            elif stripped.startswith("# "):
                tw.insert("end", stripped[2:], "h1")
            # Separators
            elif re.match(r'^[=\-]{3,}$', stripped):
                tw.insert("end", "\u2500" * 60, "separator")
            # Bullet points
            elif re.match(r'^(\s*)[-*]\s+(.*)', line):
                m = re.match(r'^(\s*)[-*]\s+(.*)', line)
                self._insert_inline_md(tw, m.group(1) + "\u2022 " + m.group(2), "bullet")
            # Numbered lists
            elif re.match(r'^\s*\d+\.\s+', line):
                self._insert_inline_md(tw, line, "bullet")
            # Normal line
            else:
                self._insert_inline_md(tw, line, "normal")

            tw.configure(state="disabled")
            self._resize_section_text(tw)
            tw.see("end")
            if section.get("expanded", False):
                self._auto_scroll_output()

        if self.parent.winfo_exists():
            self.parent.after(0, update)

    def _auto_scroll_output(self):
        """Scroll la zone de résultats vers le bas pour suivre la génération (délai pour rendu)."""
        def _do_scroll():
            try:
                if self._output_scroll and hasattr(self._output_scroll, '_parent_canvas'):
                    self._output_scroll._parent_canvas.yview_moveto(1.0)  # pylint: disable=protected-access
            except Exception:
                pass
        if self.parent.winfo_exists():
            self.parent.after(30, _do_scroll)

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

    def _resize_section_text(self, tw):
        """Redimensionne le texte : grandit jusqu'à 20 lignes, puis la scrollbar prend le relais."""
        try:
            tw.update_idletasks()
            info = tw.count("1.0", "end", "displaylines")
            lines = info[0] if info else int(tw.index("end-1c").split(".")[0])
        except Exception:
            lines = int(tw.index("end-1c").split(".")[0])
        tw.configure(height=max(3, min(lines + 1, 20)))

    def _finish_section(self, section, success=True):
        """Finalise une section: flush le buffer restant et met à jour le statut."""
        if section is None:
            return

        # Flush table buffer if any
        table_buf = section.get("_table_buf", [])
        if table_buf:
            self._flush_table_buffer(section)

        # Flush remaining line buffer through the full formatting pipeline
        remaining = section.get("_line_buf", "")
        if remaining.strip():
            self._format_and_insert_line(section, remaining, newline=True)
        section["_line_buf"] = ""

        # Flush table buffer again in case the last line was a table line
        table_buf2 = section.get("_table_buf", [])
        if table_buf2:
            self._flush_table_buffer(section)

        def update():
            section["status_var"].set("\u2705 Terminé" if success else "\u274c Erreur")

        if self.parent.winfo_exists():
            self.parent.after(0, update)

    def _setup_markdown_tags(self, tw):
        """Configure les tags de formatage Markdown sur un widget texte."""
        base = "Segoe UI"
        mono = "Consolas"

        # 1. Appliquer tous les tags de coloration syntaxique par langage depuis le mixin GUI
        if _SYNTAX_AVAILABLE:
            try:
                SyntaxColorHelper(self.colors).configure_tags(tw)
            except Exception:
                pass

        # 2. Tags spécifiques à la zone résultats (priorité sur le mixin)
        tw.tag_configure("h1", font=(base, 16, "bold"), foreground="#ffffff",
                         spacing1=10, spacing3=6)
        tw.tag_configure("h2", font=(base, 14, "bold"), foreground="#e0e0ff",
                         spacing1=8, spacing3=4)
        tw.tag_configure("h3", font=(base, 12, "bold"), foreground="#c0c0e0",
                         spacing1=6, spacing3=3)
        tw.tag_configure("h4", font=(base, 11, "bold"), foreground="#a0b0d0",
                         spacing1=4, spacing3=2)
        tw.tag_configure("bold", font=(base, 11, "bold"), foreground="#ffffff")
        tw.tag_configure("italic", font=(base, 11, "italic"), foreground="#d0d0e0")
        tw.tag_configure("code_inline", font=(mono, 10), foreground="#ff9f43")
        # code_block = fallback pour les langages non reconnus ou whitespace non tokenisé
        tw.tag_configure("code_block", font=(mono, 10), foreground="#d4d4d4",
                         spacing1=4, spacing3=4,
                         lmargin1=16, lmargin2=16)
        tw.tag_configure("code_lang", font=(mono, 9, "bold"), foreground="#6090c0",
                         spacing1=6)
        tw.tag_configure("bullet", foreground="#d0d0e0", lmargin1=20,
                         lmargin2=32, font=(base, 11))
        tw.tag_configure("normal", font=(base, 11),
                         foreground=self.colors.get("text_primary", "#ffffff"))
        tw.tag_configure("separator", foreground="#3a3a5c", font=(base, 6))
        # Table tags (matching chat page style)
        tw.tag_configure("table_header", font=(mono, 10, "bold"),
                         foreground="#58a6ff", background="#1a1a2e")
        tw.tag_configure("table_cell", font=(mono, 10),
                         foreground="#e6e6e6", background="#16213e")
        tw.tag_configure("table_border", font=(mono, 10),
                         foreground="#444466")
        tw.tag_configure("table_cell_bold", font=(mono, 10, "bold"),
                         foreground="#ffd700", background="#16213e")

    def _insert_with_markdown(self, tw, full_text):
        """Parse du texte Markdown et insertion formatée dans un widget texte."""
        lines = full_text.split("\n")
        in_code_block = False
        current_lang = ""
        i = 0

        while i < len(lines):
            line = lines[i]
            if i > 0:
                tw.insert("end", "\n")

            stripped = line.strip()

            # Code block markers
            if stripped.startswith("```"):
                if in_code_block:
                    in_code_block = False
                    current_lang = ""
                    i += 1
                    continue
                else:
                    in_code_block = True
                    current_lang = stripped[3:].strip().lower()
                    # Language label intentionally hidden — used only for highlighting logic
                    i += 1
                    continue

            if in_code_block:
                self._highlight_code_line(tw, line, current_lang)
                i += 1
                continue

            # Headers
            if stripped.startswith("#### "):
                tw.insert("end", stripped[5:], "h4")
                i += 1
                continue
            if stripped.startswith("### "):
                tw.insert("end", stripped[4:], "h3")
                i += 1
                continue
            if stripped.startswith("## "):
                tw.insert("end", stripped[3:], "h2")
                i += 1
                continue
            if stripped.startswith("# "):
                tw.insert("end", stripped[2:], "h1")
                i += 1
                continue

            # Table separator (|---|---|)
            if re.match(r'^\s*\|?[\s:]*-{2,}[\s:]*\|', stripped):
                i += 1
                continue

            # Table rows (| col | col |)
            if stripped.startswith("|") and stripped.endswith("|"):
                cells = [c.strip() for c in stripped.strip("|").split("|")]
                for ci, cell in enumerate(cells):
                    if ci > 0:
                        tw.insert("end", "  │  ", "separator")
                    self._insert_inline_md(tw, cell, "normal")
                i += 1
                continue

            # Separators
            if re.match(r'^[=\-]{3,}$', stripped):
                tw.insert("end", "─" * 60, "separator")
                i += 1
                continue

            # Bullet points
            m = re.match(r'^(\s*)[-*]\s+(.*)', line)
            if m:
                self._insert_inline_md(tw, m.group(1) + "• " + m.group(2), "bullet")
                i += 1
                continue

            # Numbered lists
            if re.match(r'^\s*\d+\.\s+', line):
                self._insert_inline_md(tw, line, "bullet")
                i += 1
                continue

            # Normal line
            self._insert_inline_md(tw, line, "normal")
            i += 1

    def _highlight_code_line(self, tw, line, lang):
        """Insère une ligne de code avec coloration syntaxique par langage."""
        if not _SYNTAX_AVAILABLE or not lang:
            tw.insert("end", line, "code_block")
            return
        _SYNTAX_ANALYZER.highlight_line(tw, line, lang)

    def _insert_inline_md(self, tw, text, base_tag):
        """Insère du texte avec formatage inline Markdown (gras, italique, code)."""
        pattern = r'(\*\*[^*]+\*\*|\*[^*]+\*|`[^`]+`)'
        parts = re.split(pattern, text)
        for part in parts:
            if not part:
                continue
            if part.startswith("**") and part.endswith("**"):
                tw.insert("end", part[2:-2], "bold")
            elif part.startswith("*") and part.endswith("*") and len(part) > 2:
                tw.insert("end", part[1:-1], "italic")
            elif part.startswith("`") and part.endswith("`"):
                tw.insert("end", part[1:-1], "code_inline")
            else:
                tw.insert("end", part, base_tag)

    def _append_output(self, text):
        """Ajoute du texte à la section active."""
        if self._active_section is not None:
            self._append_to_section(self._active_section, text)

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
        """No-op: les sections gèrent leur propre état."""

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

    # === Resource Monitoring UI =======================================

    def _on_resource_update(self, metrics: dict):
        """Callback du ResourceMonitor — met à jour les barres."""
        if not self.parent.winfo_exists():
            return
        self.parent.after(0, lambda m=dict(metrics): self._apply_resource_metrics(m))

    def _apply_resource_metrics(self, m: dict):
        """Applique les métriques à l'UI (thread principal)."""
        gpu_ok = m.get("gpu_available", False)

        rows = {
            "cpu":   (m.get("cpu_percent", 0), f"{m['cpu_percent']:.1f} %"),
            "ram":   (
                min(m.get("ram_percent", 0), 100),
                f"{m['ram_used_mb']:.0f} Mo / {m['ram_total_mb']:.0f} Mo  ({m['ram_percent']:.1f} %)",
            ),
            "gpu":   (
                m.get("gpu_percent", 0) if gpu_ok else 0,
                f"{m['gpu_percent']:.1f} %" if gpu_ok else "N/A",
            ),
            "vram":  (
                (m["gpu_mem_used_mb"] / max(m["gpu_mem_total_mb"], 1) * 100) if gpu_ok else 0,
                (f"{m['gpu_mem_used_mb']:.0f} / {m['gpu_mem_total_mb']:.0f} Mo"
                 if gpu_ok else "N/A"),
            ),
            "infer": (
                min(m.get("inference_ms", 0) / 50, 100),  # 5 s = 100%
                f"{m['inference_ms']:.0f} ms" if m.get("inference_ms") else "—",
            ),
            "tps":   (
                min(m.get("tokens_per_sec", 0) / 1, 100),  # cap visuel
                f"{m['tokens_per_sec']:.1f} tok/s" if m.get("tokens_per_sec") else "—",
            ),
        }

        for key, (pct, text) in rows.items():
            self._draw_bar(key, pct)
            lbl = self._resource_labels.get(key)
            if lbl and lbl.winfo_exists():
                lbl.configure(text=text)

        # Sparklines
        hist = self.resource_monitor.history
        spark_map = {"cpu": "cpu", "ram": "ram", "gpu": "gpu", "tps": "tps"}
        for ui_key, h_key in spark_map.items():
            data = hist.get(h_key, [])
            self._draw_sparkline(ui_key, data)

    def _draw_bar(self, key: str, pct: float):
        """Dessine une barre de progression colorée."""
        c = self._resource_bars.get(key)
        if not c or not c.winfo_exists():
            return
        c.delete("all")
        w = c.winfo_width() or 200
        h = c.winfo_height() or 16
        # Background
        c.create_rectangle(0, 0, w, h, fill=self.colors["bg_primary"], outline="")
        # Filled portion
        pct = max(0, min(pct, 100))
        fill_w = w * pct / 100
        color = "#10b981" if pct < 50 else "#f59e0b" if pct < 80 else "#ef4444"
        if fill_w > 0:
            c.create_rectangle(0, 0, fill_w, h, fill=color, outline="")

    def _draw_sparkline(self, key: str, data: list):
        """Dessine un mini graphe sparkline."""
        c = self._sparkline_canvases.get(key)
        if not c or not c.winfo_exists() or len(data) < 2:
            return
        c.delete("all")
        w = c.winfo_width() or 80
        h = c.winfo_height() or 16
        max_v = max(data) or 1
        step = w / max(len(data) - 1, 1)
        pts = []
        for i, v in enumerate(data):
            x = i * step
            y = h - (v / max_v) * (h - 2) - 1
            pts.extend([x, y])
        if len(pts) >= 4:
            c.create_line(*pts, fill=self.colors["accent"], width=1.5, smooth=True)

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
        def factory(model=None):
            return AIAgent(
                name=agent_data["name"],
                expertise=agent_data["desc"],
                system_prompt=agent_data["system_prompt"],
                model=model or _get_default_model(),
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
