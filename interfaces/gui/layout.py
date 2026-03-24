"""Layout mixin for ModernAIGUI."""

import os
import tkinter as tk
import threading
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
    TKINTER_DND = TkinterDnD
except Exception:
    DND_AVAILABLE = False
    TKINTER_DND = None

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
                self.root = TKINTER_DND.Tk()
            else:
                self.root = ctk.CTk()
            self.use_ctk = True
        else:
            if DND_AVAILABLE:
                self.root = TKINTER_DND.Tk()
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

        # Référence pour l'écran d'accueil
        self._chat_content_frame = chat_content

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

    def _update_header_buttons_visibility(self):
        """Affiche ou masque les boutons Clear Chat / Aide selon le contexte.
        Visible uniquement sur l'onglet Chat ET hors écran d'accueil."""
        show = (
            getattr(self, "_current_tab", "chat") == "chat"
            and not getattr(self, "_home_screen_active", False)
        )
        for btn in (
            getattr(self, "clear_btn", None),
            getattr(self, "help_btn", None),
        ):
            if btn is None:
                continue
            try:
                if show:
                    btn.grid()
                else:
                    btn.grid_remove()
            except Exception:
                pass

    def switch_tab(self, tab_id):
        """Change d'onglet"""
        self._current_tab = tab_id

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

        # Afficher/masquer les boutons Clear Chat / Aide selon l'onglet actif
        self._update_header_buttons_visibility()

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
        # Restaurer la hauteur de la barre d'en-tête (identique à l'original)
        self.main_container.grid_rowconfigure(0, minsize=80)

        header_frame = self.create_frame(
            self.main_container, fg_color=self.colors["bg_primary"]
        )
        header_frame.grid(row=0, column=0, sticky="nsew", padx=20, pady=0)
        # Seule la colonne des boutons a un poids (boutons collés à droite)
        header_frame.grid_columnconfigure(2, weight=1)

        # Boutons d'onglets centrés (place pour centrage absolu)
        self.create_tab_buttons(header_frame)

        # Boutons d'action à droite
        self.create_header_buttons(header_frame)

    def create_tab_buttons(self, parent):
        """Crée les boutons d'onglets Chat/Agents au centre du header"""
        tabs_frame = self.create_frame(parent, fg_color=self.colors["bg_primary"])
        # Centrage absolu horizontal et vertical dans le header
        tabs_frame.place(relx=0.5, rely=0.5, anchor="center")

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
        buttons_frame.grid(row=0, column=2, sticky="e", padx=(10, 0), pady=35)

        # ── Sélecteur de modèle (hot-reload) ──
        self._model_selector_var = tk.StringVar(value="")
        if self.use_ctk:
            self.model_selector = ctk.CTkOptionMenu(
                buttons_frame,
                variable=self._model_selector_var,
                values=["Chargement..."],
                command=self._on_model_selected,
                fg_color=self.colors.get("bg_secondary", "#2a2a2a"),
                button_color=self.colors.get("accent", "#ff6b47"),
                button_hover_color=self.colors.get("button_hover", "#3a3a3a"),
                text_color=self.colors.get("text_primary", "#ffffff"),
                dropdown_fg_color=self.colors.get("bg_secondary", "#2a2a2a"),
                dropdown_text_color=self.colors.get("text_primary", "#ffffff"),
                dropdown_hover_color=self.colors.get("accent", "#ff6b47"),
                font=("Segoe UI", 11),
                width=160,
                height=32,
                corner_radius=6,
            )
        else:
            self.model_selector = tk.OptionMenu(
                buttons_frame, self._model_selector_var, "Chargement...",
            )
            self.model_selector.configure(
                bg=self.colors.get("bg_secondary", "#2a2a2a"),
                fg=self.colors.get("text_primary", "#ffffff"),
                font=("Segoe UI", 11), relief="flat",
            )
        self.model_selector.grid(row=0, column=0, padx=(0, 10))
        # Charger les modèles en arrière-plan
        self.root.after(500, self._populate_model_selector)

        # Bouton Clear Chat
        self.clear_btn = self.create_modern_button(
            buttons_frame,
            text="🗑️ Clear Chat",
            command=self.clear_chat,
            style="secondary",
        )
        self.clear_btn.grid(row=0, column=1, padx=(0, 10))

        # Bonton Help
        self.help_btn = self.create_modern_button(
            buttons_frame, text="❓ Aide", command=self.show_help, style="secondary"
        )
        self.help_btn.grid(row=0, column=2, padx=(0, 10))

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

        # Référence pour l'écran d'accueil (ajustement padding)
        self._input_container = input_container

        # Bordure extérieure arrondie
        input_wrapper = self.create_frame(
            input_container, fg_color=self.colors["border"], corner_radius=8
        )
        input_wrapper.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        input_wrapper.grid_columnconfigure(0, weight=1)
        self.input_wrapper = input_wrapper  # référence pour le drag & drop

        # Frame intérieur (r=8) : auto-détecte bg_color=border → ses coins montrent la couleur
        # de bordure, créant des coins intérieurs arrondis. Les enfants (padx=3) démarrent
        # à l'intérieur de l'arc, donc ne cachent pas ces pixels de coin.
        content_frame = self.create_frame(
            input_wrapper, fg_color=self.colors["input_bg"], corner_radius=8
        )
        content_frame.grid(row=0, column=0, sticky="ew", padx=3, pady=3)
        content_frame.grid_columnconfigure(0, weight=1)

        # ── Zone d'aperçu des documents attachés (initialement masquée) ────
        self._preview_frame = self.create_frame(
            content_frame, fg_color=self.colors["input_bg"], corner_radius=0
        )
        # row=0 réservé pour les aperçus — masqué tant qu'aucun fichier n'est attaché
        self._preview_frame.grid(row=0, column=0, sticky="ew", padx=6, pady=(6, 0))
        self._preview_frame.grid_remove()  # Masquer par défaut
        self._pending_files = []  # Liste des fichiers en attente [(path, type, widget), ...]

        # Champ de saisie — dans content_frame, padx=3 laisse les coins arrondis visibles
        if self.use_ctk:
            self.input_text = ctk.CTkTextbox(
                content_frame,
                height=60,
                fg_color=self.colors["input_bg"],
                text_color=self.colors["text_primary"],
                border_width=0,
                corner_radius=0,
                font=(
                    "Segoe UI",
                    self.get_current_font_size("message"),
                ),  # UNIFIÉ AVEC LES MESSAGES
            )
        else:
            self.input_text = tk.Text(
                content_frame,
                height=3,
                fg=self.colors["text_primary"],
                bg=self.colors["input_bg"],
                font=(
                    "Segoe UI",
                    self.get_current_font_size("message"),
                ),  # UNIFIÉ AVEC LES MESSAGES
                border=0,
                relief="flat",
                wrap=tk.WORD,
            )

        self.input_text.grid(row=1, column=0, sticky="ew", padx=3, pady=(3, 0))

        # Boutons d'action — dans content_frame, r=0 évite les artifacts à la jonction
        button_frame = self.create_frame(
            content_frame, fg_color=self.colors["input_bg"], corner_radius=0
        )
        button_frame.grid(row=2, column=0, sticky="ew", padx=3, pady=(0, 3))
        button_frame.grid_columnconfigure(1, weight=1)

        # ── Bouton "+" avec menu déroulant vers le haut ──────────────────────
        _chat_file_entries = [
            ("📄  PDF",         self.load_pdf_file),
            ("📝  DOCX",        self.load_docx_file),
            ("📊  Excel / CSV", self.load_excel_file),
            ("💻  Code",        self.load_code_file),
            ("🖼  Image",        self.load_image_file),
        ]
        _chat_popup_ref = [None]

        def _close_chat_popup(popup):
            try:
                popup.destroy()
            except Exception:
                pass
            _chat_popup_ref[0] = None

        def _open_chat_file_menu():
            """Menu déroulant vers le haut, aligné sur le bouton '+'."""
            if _chat_popup_ref[0] is not None:
                _close_chat_popup(_chat_popup_ref[0])
                return

            bg     = self.colors.get("bg_secondary", "#1e1e1e")
            fg     = self.colors.get("text_primary",  "#ffffff")
            accent = self.colors.get("accent",        "#ff6b47")
            font   = ("Segoe UI", 11)

            popup = tk.Toplevel(self.root)
            popup.overrideredirect(True)
            popup.configure(bg=bg)
            popup.attributes("-topmost", True)
            _chat_popup_ref[0] = popup

            for i, (_lbl, _cmd) in enumerate(_chat_file_entries):
                def _make_cb(cmd, pop=popup):
                    def _cb():
                        _close_chat_popup(pop)
                        cmd()
                    return _cb
                btn = tk.Label(
                    popup, text=_lbl, bg=bg, fg=fg, font=font,
                    anchor="w", padx=14, pady=7, cursor="hand2",
                )
                btn.grid(row=i, column=0, sticky="ew")
                popup.grid_columnconfigure(0, weight=1)
                cb = _make_cb(_cmd)
                btn.bind("<Button-1>", lambda e, c=cb: c())
                btn.bind("<Enter>",    lambda e, b=btn: b.configure(bg=accent, fg="#ffffff"))
                btn.bind("<Leave>",    lambda e, b=btn: b.configure(bg=bg,     fg=fg))

            # Positionner au-dessus du bouton
            popup.update_idletasks()
            ph = popup.winfo_reqheight()
            bx = self.file_plus_btn.winfo_rootx()
            by = self.file_plus_btn.winfo_rooty() - ph
            popup.geometry(f"+{bx}+{by}")

            def _on_focus_out(_e):
                self.root.after(50, lambda: _close_chat_popup(popup) if _chat_popup_ref[0] is popup else None)

            popup.bind("<FocusOut>", _on_focus_out)
            popup.bind("<Escape>",   lambda _e: _close_chat_popup(popup))
            self.root.bind("<Button-1>",
                           lambda _e: _close_chat_popup(popup) if _chat_popup_ref[0] is popup else None,
                           add="+")
            popup.focus_set()

        if self.use_ctk:
            self.file_plus_btn = ctk.CTkButton(
                button_frame,
                text="＋",
                command=_open_chat_file_menu,
                fg_color=self.colors.get("bg_secondary", "#2a2a2a"),
                hover_color=self.colors.get("button_hover", "#3a3a3a"),
                text_color=self.colors.get("text_secondary", "#aaaaaa"),
                font=("Segoe UI", 18),
                corner_radius=6,
                width=42,
                height=32,
            )
        else:
            self.file_plus_btn = tk.Button(
                button_frame,
                text="＋",
                command=_open_chat_file_menu,
                bg=self.colors.get("bg_secondary", "#2a2a2a"),
                fg=self.colors.get("text_secondary", "#aaaaaa"),
                font=("Segoe UI", 18),
                relief="flat", bd=0, padx=8,
            )
        self.file_plus_btn.grid(row=0, column=0, sticky="w", padx=(6, 0), pady=4)

        # Bouton d'envoi principal
        self.send_button = self.create_modern_button(
            button_frame,
            text="Envoyer ↗",
            command=self.send_message(),
            style="primary",
        )
        self.send_button.grid(row=0, column=2, sticky="e", padx=(0, 6), pady=4)

        # Bind des événements
        self.input_text.bind("<Return>", self.on_enter_key)
        self.input_text.bind("<Shift-Return>", self.on_shift_enter)
        self.input_text.bind("<Control-v>", self._on_paste)

        # Placeholder text
        self.set_placeholder()

    # ── Gestion des aperçus de documents dans la zone de saisie ────────────

    def _get_active_preview_frame(self):
        """Retourne la preview frame active selon l'écran courant (home ou chat)."""
        if getattr(self, "_home_screen_active", False):
            return getattr(self, "_home_preview_frame", None) or self._preview_frame
        return self._preview_frame

    def add_file_preview(self, file_path: str, file_type: str):
        """
        Ajoute un aperçu miniature d'un fichier attaché dans la zone de saisie.
        Affiche une vignette avec le nom du fichier et un bouton ✕ pour retirer.
        """
        filename = os.path.basename(file_path)
        preview_frame = self._get_active_preview_frame()

        # Icônes par type de fichier
        type_icons = {
            "PDF": "📄", "DOCX": "📝", "Excel": "📊",
            "Code": "💻", "Image": "🖼",
        }
        icon = type_icons.get(file_type, "📎")

        # Conteneur de la vignette
        bg = self.colors.get("bg_secondary", "#2a2a2a")
        accent = self.colors.get("accent", "#ff6b47")

        if self.use_ctk:
            thumb = ctk.CTkFrame(
                preview_frame, fg_color=bg, corner_radius=6,
                border_width=1, border_color=self.colors.get("border", "#404040"),
            )
        else:
            thumb = tk.Frame(preview_frame, bg=bg, relief="solid", bd=1)

        thumb.pack(side="left", padx=(0, 8), pady=4)

        # Icône + nom du fichier (tronqué si trop long)
        display_name = filename if len(filename) <= 20 else filename[:17] + "..."
        label_text = f"{icon} {display_name}"

        if self.use_ctk:
            lbl = ctk.CTkLabel(
                thumb, text=label_text,
                font=("Segoe UI", 11),
                text_color=self.colors.get("text_primary", "#ffffff"),
                fg_color="transparent",
            )
        else:
            lbl = tk.Label(
                thumb, text=label_text, bg=bg,
                fg=self.colors.get("text_primary", "#ffffff"),
                font=("Segoe UI", 11),
            )
        lbl.pack(side="left", padx=(8, 4), pady=4)

        # Bouton ✕ pour retirer le fichier
        _pf = preview_frame  # capturer la bonne frame dans la closure

        def _remove_file():
            self._pending_files = [
                (p, t, w) for p, t, w in self._pending_files if w is not thumb
            ]
            thumb.destroy()
            if not self._pending_files:
                _pf.grid_remove()

        if self.use_ctk:
            close_btn = ctk.CTkButton(
                thumb, text="✕", width=24, height=24,
                fg_color="transparent", hover_color=accent,
                text_color=self.colors.get("text_secondary", "#aaaaaa"),
                font=("Segoe UI", 12, "bold"),
                corner_radius=4, command=_remove_file,
            )
        else:
            close_btn = tk.Button(
                thumb, text="✕", bg=bg, fg=self.colors.get("text_secondary", "#aaaaaa"),
                font=("Segoe UI", 10, "bold"), relief="flat", bd=0,
                command=_remove_file, cursor="hand2",
            )
        close_btn.pack(side="left", padx=(0, 6), pady=4)

        # Enregistrer le fichier en attente
        self._pending_files.append((file_path, file_type, thumb))

        # Afficher la zone d'aperçu
        preview_frame.grid()

    def clear_file_previews(self):
        """Retire tous les aperçus de fichiers de la zone de saisie."""
        for _, _, widget in self._pending_files:
            try:
                widget.destroy()
            except Exception:
                pass
        self._pending_files = []
        self._preview_frame.grid_remove()
        # Masquer aussi la preview home si elle existe
        home_pf = getattr(self, "_home_preview_frame", None)
        if home_pf is not None:
            try:
                home_pf.grid_remove()
            except Exception:
                pass

    def get_pending_files(self) -> list:
        """Retourne la liste des fichiers en attente [(path, type), ...]."""
        return [(p, t) for p, t, _ in self._pending_files]

    # ── Sélecteur de modèle (hot-reload) ──────────────────────────────────

    def _populate_model_selector(self):
        """Charge la liste des modèles Ollama disponibles dans le sélecteur."""

        def _load():
            models = []
            current = ""
            try:
                llm = None
                if hasattr(self, "custom_ai") and self.custom_ai and hasattr(self.custom_ai, "local_llm"):
                    llm = self.custom_ai.local_llm
                elif hasattr(self, "ai_engine") and hasattr(self.ai_engine, "local_ai"):
                    ai = self.ai_engine.local_ai
                    if hasattr(ai, "local_llm"):
                        llm = ai.local_llm
                if llm:
                    models = llm.list_available_models()
                    current = llm.get_current_model()
            except Exception as e:
                print(f"⚠️ [MODEL_SELECTOR] Erreur chargement modèles: {e}")

            if models:
                self.root.after(0, lambda: self._update_model_selector(models, current))

        threading.Thread(target=_load, daemon=True).start()

    def _update_model_selector(self, models: list, current: str):
        """Met à jour le sélecteur avec la liste des modèles."""
        if not models:
            return
        if self.use_ctk and hasattr(self.model_selector, "configure"):
            self.model_selector.configure(values=models)
        if current and current in models:
            self._model_selector_var.set(current)
        elif models:
            self._model_selector_var.set(models[0])

    def _on_model_selected(self, selected_model: str):
        """Callback quand l'utilisateur sélectionne un nouveau modèle."""

        def _switch():
            try:
                llm = None
                if hasattr(self, "custom_ai") and self.custom_ai and hasattr(self.custom_ai, "local_llm"):
                    llm = self.custom_ai.local_llm
                elif hasattr(self, "ai_engine") and hasattr(self.ai_engine, "local_ai"):
                    ai = self.ai_engine.local_ai
                    if hasattr(ai, "local_llm"):
                        llm = ai.local_llm
                if llm:
                    success = llm.switch_model(selected_model)
                    if success:
                        self.root.after(
                            0,
                            lambda: self.show_notification(
                                f"🔄 Modèle changé → {selected_model}", "success", 2000
                            ),
                        )
                    else:
                        self.root.after(
                            0,
                            lambda: self.show_notification(
                                f"❌ Modèle {selected_model} indisponible", "error", 2000
                            ),
                        )
            except Exception as e:
                print(f"⚠️ [MODEL_SELECTOR] Erreur changement: {e}")

        threading.Thread(target=_switch, daemon=True).start()
