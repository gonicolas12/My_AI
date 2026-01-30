"""Layout mixin for ModernAIGUI."""

import tkinter as tk
from tkinter import ttk

try:
    import customtkinter as ctk

    CTK_AVAILABLE = True
except ImportError:
    CTK_AVAILABLE = False
    ctk = tk

try:
    from tkinterdnd2 import TkinterDnD

    DND_AVAILABLE = True
except Exception:
    DND_AVAILABLE = False
    TkinterDnD = None

# Import des styles (uniquement ce qui est utilisé)
try:
    from interfaces.modern_styles import MODERN_COLORS
except ImportError:
    MODERN_COLORS = {
        "bg_primary": "#212121",
        "bg_secondary": "#2f2f2f",
        "bg_chat": "#212121",
        "bg_user": "#3b82f6",
        "bg_ai": "#2f2f2f",
        "text_primary": "#ffffff",
        "text_secondary": "#9ca3af",
        "accent": "#3b82f6",
        "accent_hover": "#2563eb",
        "border": "#404040",
        "input_bg": "#2f2f2f",
        "button_hover": "#404040",
        "placeholder": "#6b7280",
    }

from interfaces.agents_interface import AgentsInterface


class LayoutMixin:
    """Layout and window setup methods."""

    def setup_modern_gui(self):
        """Configure l'interface principale style Claude"""
        if CTK_AVAILABLE:
            # Mode sombre moderne
            ctk.set_appearance_mode("dark")
            ctk.set_default_color_theme("blue")
            if DND_AVAILABLE:
                self.root = TkinterDnD.Tk()
            else:
                self.root = ctk.CTk()
            self.use_ctk = True
        else:
            if DND_AVAILABLE:
                self.root = TkinterDnD.Tk()
            else:
                self.root = tk.Tk()
            self.use_ctk = False
            self.setup_fallback_style()

        # Configuration de la fenêtre
        self.root.title("My Personal AI")

        # Gestionnaire de fermeture propre
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

        # Plein écran automatique et premier plan
        self.root.attributes("-topmost", True)  # Premier plan
        self.root.state("zoomed")  # Plein écran sur Windows
        self.root.after(
            1000, lambda: self.root.attributes("-topmost", False)
        )  # Retirer topmost après 1s

        # Détection de la taille d'écran pour responsive design
        self.screen_width = self.root.winfo_screenwidth()
        self.screen_height = self.root.winfo_screenheight()
        self.determine_layout_size()

        # Responsive design
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_rowconfigure(0, weight=1)

        # Couleurs modernes (utilise modern_styles.py si disponible)
        self.colors = MODERN_COLORS

        # Polices modernes adaptées à l'OS
        self.setup_fonts()

        # Configuration drag & drop
        if DND_AVAILABLE:
            self.setup_drag_drop()

    def setup_fallback_style(self):
        """Style de base pour tkinter standard"""
        self.root.configure(fg_color="#1a1a1a")

        # Style TTK pour tkinter standard
        style = ttk.Style()
        style.theme_use("clam")

        # Configuration des styles sombres
        style.configure("Dark.TFrame", background="#1a1a1a")
        style.configure("Dark.TLabel", background="#1a1a1a", foreground="#ffffff")
        style.configure("Dark.TButton", background="#2d2d2d", foreground="#ffffff")

    def create_modern_layout(self):
        """Crée le layout moderne style Claude avec onglets"""
        # Container principal
        self.main_container = self.create_frame(
            self.root, fg_color=self.colors["bg_primary"]
        )
        self.main_container.grid(row=0, column=0, sticky="nsew", padx=0, pady=0)
        self.main_container.grid_columnconfigure(0, weight=1)
        self.main_container.grid_rowconfigure(1, weight=1)

        # Header moderne
        self.create_modern_header()

        # Système d'onglets
        self.create_tabbed_interface()

        # Animations et effets (uniquement pour le chat)
        self.start_animations()

    def create_tabbed_interface(self):
        """Crée l'interface avec onglets Chat et Agents"""
        # Container pour le contenu des onglets
        self.content_container = self.create_frame(
            self.main_container, fg_color=self.colors["bg_primary"]
        )
        self.content_container.grid(row=1, column=0, sticky="nsew", padx=0, pady=0)
        self.content_container.grid_columnconfigure(0, weight=1)
        self.content_container.grid_rowconfigure(0, weight=1)
        self.main_container.grid_rowconfigure(1, weight=1)

        # Dictionnaire pour stocker les frames
        self.tab_frames = {}

        # Créer les frames pour chaque onglet
        self.create_chat_tab()
        self.create_agents_tab()

        # Afficher l'onglet Chat par défaut
        self.switch_tab("chat")

    def create_chat_tab(self):
        """Crée l'onglet Chat (interface existante)"""
        chat_frame = self.create_frame(
            self.content_container, fg_color=self.colors["bg_primary"]
        )
        chat_frame.grid(row=0, column=0, sticky="nsew")
        chat_frame.grid_columnconfigure(0, weight=1)
        chat_frame.grid_rowconfigure(0, weight=1)

        self.tab_frames["chat"] = chat_frame

        # Conteneur pour chat + input (comme avant)
        chat_content = self.create_frame(chat_frame, fg_color=self.colors["bg_primary"])
        chat_content.grid(row=0, column=0, sticky="nsew", padx=0, pady=0)
        chat_content.grid_columnconfigure(0, weight=1)
        chat_content.grid_rowconfigure(0, weight=1)

        # Zone de conversation (utilise l'ancienne méthode)
        self.create_conversation_area_in_frame(chat_content)

        # Zone de saisie
        self.create_modern_input_area_in_frame(chat_content)

    def create_agents_tab(self):
        """Crée l'onglet Agents"""
        agents_frame = self.create_frame(
            self.content_container, fg_color=self.colors["bg_primary"]
        )
        agents_frame.grid(row=0, column=0, sticky="nsew")
        agents_frame.grid_columnconfigure(0, weight=1)
        agents_frame.grid_rowconfigure(0, weight=1)

        self.tab_frames["agents"] = agents_frame

        # Créer l'interface agents
        self.agents_interface = AgentsInterface(
            parent_frame=agents_frame,
            colors=self.colors,
            create_frame=self.create_frame,
            create_label=self.create_label,
            create_button=self.create_button,
            create_text=self.create_text,
            use_ctk=self.use_ctk,
        )

    def switch_tab(self, tab_id):
        """Change d'onglet"""
        # Cacher tous les onglets
        for tid, frame in self.tab_frames.items():
            frame.grid_remove()

        # Afficher l'onglet sélectionné
        if tab_id in self.tab_frames:
            self.tab_frames[tab_id].grid()

        # Mettre à jour l'apparence des boutons (même couleur pour tous, juste l'intensité change)
        for tid, btn in self.tab_buttons.items():
            if tid == tab_id:
                # Onglet actif - couleur accent
                if self.use_ctk:
                    btn.configure(
                        fg_color=self.colors["accent"],
                        text_color="#ffffff",
                    )
                else:
                    btn.configure(bg=self.colors["accent"], fg="#ffffff")
            else:
                # Onglet inactif - couleur secondaire
                if self.use_ctk:
                    btn.configure(
                        fg_color=self.colors["bg_secondary"],
                        text_color=self.colors["text_secondary"],
                    )
                else:
                    btn.configure(
                        bg=self.colors["bg_secondary"],
                        fg=self.colors["text_secondary"],
                    )

    def create_conversation_area_in_frame(self, parent):
        """Crée la zone de conversation dans un frame spécifique"""
        # Utiliser le parent fourni au lieu de self.main_container
        original_create = self.create_conversation_area

        # Sauvegarder temporairement self.main_container
        temp_container = self.main_container

        # Remplacer temporairement par le parent fourni
        self.main_container = parent

        # Appeler la méthode originale
        original_create()

        # Restaurer self.main_container
        self.main_container = temp_container

    def create_modern_input_area_in_frame(self, parent):
        """Crée la zone de saisie dans un frame spécifique"""
        # Sauvegarder temporairement self.main_container
        temp_container = self.main_container

        # Remplacer temporairement par le parent fourni
        self.main_container = parent

        # Appeler la méthode originale
        self.create_modern_input_area()

        # Restaurer self.main_container
        self.main_container = temp_container

    def create_modern_header(self):
        """Crée l'en-tête moderne style Claude"""
        header_frame = self.create_frame(
            self.main_container, fg_color=self.colors["bg_primary"]
        )
        header_frame.grid(row=0, column=0, sticky="ew", padx=20, pady=(20, 10))
        header_frame.grid_columnconfigure(0, weight=1)  # Gauche
        header_frame.grid_columnconfigure(1, weight=0)  # Centre (boutons tabs)
        header_frame.grid_columnconfigure(2, weight=1)  # Droite

        # Container gauche (logo + titre)
        left_frame = self.create_frame(
            header_frame, fg_color=self.colors["bg_primary"]
        )
        left_frame.grid(row=0, column=0, sticky="w")

        # Logo/Icône - taille réduite
        logo_label = self.create_label(
            left_frame,
            text="🤖",
            font=("Segoe UI", self.get_current_font_size("header")),  # Dynamique
            text_color=self.colors["accent"],  # text_color au lieu de fg
            fg_color=self.colors["bg_primary"],
        )
        logo_label.grid(row=0, column=0, padx=(0, 15))

        # Titre principal
        title_frame = self.create_frame(
            left_frame, fg_color=self.colors["bg_primary"]
        )
        title_frame.grid(row=0, column=1, sticky="w", pady=(8, 0))

        title_label = self.create_label(
            title_frame,
            text="My Personal AI",
            font=self.fonts["title"],
            text_color=self.colors["text_primary"],  # text_color au lieu de fg
            fg_color=self.colors["bg_primary"],
        )
        title_label.grid(row=0, column=0, sticky="w")

        subtitle_label = self.create_label(
            title_frame,
            text="Assistant IA Local - Prêt à vous aider",
            font=self.fonts["subtitle"],
            text_color=self.colors["text_secondary"],  # text_color au lieu de fg
            fg_color=self.colors["bg_primary"],
        )
        subtitle_label.grid(row=1, column=0, sticky="w", pady=(2, 0))

        # Boutons d'onglets au centre
        self.create_tab_buttons(header_frame)

        # Boutons d'action à droite
        self.create_header_buttons(header_frame)

    def create_tab_buttons(self, parent):
        """Crée les boutons d'onglets Chat/Agents au centre du header"""
        tabs_frame = self.create_frame(parent, fg_color=self.colors["bg_primary"])
        tabs_frame.grid(row=0, column=1, padx=20)

        self.tab_buttons = {}

        tabs = [
            ("chat", "💬 Chat"),
            ("agents", "🤖 Agents"),
        ]

        for _idx, (tab_id, tab_text) in enumerate(tabs):
            if self.use_ctk:
                btn = ctk.CTkButton(
                    tabs_frame,
                    text=tab_text,
                    command=lambda tid=tab_id: self.switch_tab(tid),
                    fg_color=self.colors["bg_secondary"],
                    hover_color=self.colors["button_hover"],
                    text_color=self.colors["text_secondary"],
                    font=("Segoe UI", 12, "bold"),
                    height=40,
                    width=130,
                    corner_radius=6,
                )
            else:
                btn = tk.Button(
                    tabs_frame,
                    text=tab_text,
                    command=lambda tid=tab_id: self.switch_tab(tid),
                    bg=self.colors["bg_secondary"],
                    fg=self.colors["text_secondary"],
                    font=("Segoe UI", 12, "bold"),
                    height=2,
                    width=15,
                )
            btn.pack(side="left", padx=3)
            self.tab_buttons[tab_id] = btn

    def create_header_buttons(self, parent):
        """Crée les boutons de l'en-tête"""
        buttons_frame = self.create_frame(parent, fg_color=self.colors["bg_primary"])
        buttons_frame.grid(row=0, column=2, sticky="e", padx=(10, 0))

        # Bouton Clear Chat
        self.clear_btn = self.create_modern_button(
            buttons_frame,
            text="🗑️ Clear Chat",
            command=self.clear_chat,
            style="secondary",
        )
        self.clear_btn.grid(row=0, column=0, padx=(0, 10))

        # Bonton Help
        self.help_btn = self.create_modern_button(
            buttons_frame, text="❓ Aide", command=self.show_help, style="secondary"
        )
        self.help_btn.grid(row=0, column=1, padx=(0, 10))

        # Indicateur de statut - taille réduite
        self.status_label = self.create_label(
            buttons_frame,
            text="●",
            font=("Segoe UI", self.get_current_font_size("status")),  # Dynamique
            text_color="#00ff00",  # Vert = connecté (text_color au lieu de fg)
            fg_color=self.colors["bg_primary"],
        )
        self.status_label.grid(row=0, column=2)

    def create_modern_input_area(self):
        """Crée la zone de saisie moderne style Claude"""
        input_container = self.create_frame(
            self.main_container, fg_color=self.colors["bg_primary"]
        )
        input_container.grid(row=1, column=0, sticky="ew", padx=20, pady=(0, 20))
        input_container.grid_columnconfigure(0, weight=1)

        # Zone de saisie avec bordure moderne
        input_wrapper = self.create_frame(
            input_container, fg_color=self.colors["border"]
        )
        input_wrapper.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        input_wrapper.grid_columnconfigure(0, weight=1)

        # Champ de saisie
        if self.use_ctk:
            self.input_text = ctk.CTkTextbox(
                input_wrapper,
                height=60,
                fg_color=self.colors["input_bg"],
                text_color=self.colors["text_primary"],
                border_color=self.colors["border"],
                border_width=1,
                corner_radius=8,
                font=(
                    "Segoe UI",
                    self.get_current_font_size("message"),
                ),  # UNIFIÉ AVEC LES MESSAGES
            )
        else:
            self.input_text = tk.Text(
                input_wrapper,
                height=3,
                fg_color=self.colors["input_bg"],
                fg=self.colors["text_primary"],
                font=(
                    "Segoe UI",
                    self.get_current_font_size("message"),
                ),  # UNIFIÉ AVEC LES MESSAGES
                border=1,
                relief="solid",
                wrap=tk.WORD,
            )

        self.input_text.grid(row=0, column=0, sticky="ew", padx=2, pady=2)

        # Boutons d'action
        button_frame = self.create_frame(
            input_container, fg_color=self.colors["bg_primary"]
        )
        button_frame.grid(row=1, column=0, sticky="ew")
        button_frame.grid_columnconfigure(1, weight=1)

        # Boutons de fichiers
        file_buttons = self.create_frame(
            button_frame, fg_color=self.colors["bg_primary"]
        )
        file_buttons.grid(row=0, column=0, sticky="w")

        self.pdf_btn = self.create_modern_button(
            file_buttons, text="📄 PDF", command=self.load_pdf_file, style="file"
        )
        self.pdf_btn.grid(row=0, column=0, padx=(0, 5))

        self.docx_btn = self.create_modern_button(
            file_buttons, text="📝 DOCX", command=self.load_docx_file, style="file"
        )
        self.docx_btn.grid(row=0, column=1, padx=(0, 5))

        self.code_btn = self.create_modern_button(
            file_buttons, text="💻 Code", command=self.load_code_file, style="file"
        )
        self.code_btn.grid(row=0, column=2, padx=(0, 10))

        # Bouton d'envoi principal
        self.send_button = self.create_modern_button(
            button_frame,
            text="Envoyer ↗",
            command=self.send_message(),
            style="primary",
        )
        self.send_button.grid(row=0, column=2, sticky="e")

        # Bind des événements
        self.input_text.bind("<Return>", self.on_enter_key)
        self.input_text.bind("<Shift-Return>", self.on_shift_enter)

        # Placeholder text
        self.set_placeholder()
