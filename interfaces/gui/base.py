"""Base GUI class and shared utilities for ModernAIGUI."""

import asyncio
import os
import platform
import random
import re
import threading
import tkinter as tk
import traceback
from datetime import datetime
from tkinter import messagebox

import customtkinter as _ctk

from core.ai_engine import AIEngine
from core.config import Config
from utils.file_processor import FileProcessor
from utils.logger import setup_logger

# Import des styles (uniquement ce qui est utilisé)
try:
    from interfaces.modern_styles import (FONT_CONFIG, FONT_SIZES,
                                          RESPONSIVE_BREAKPOINTS)
except ImportError:
    # Fallback si le fichier de styles n'est pas disponible
    FONT_CONFIG = {
        "family": "Segoe UI",
        "family_mono": "Consolas",
    }
    FONT_SIZES = {
        "title": 24,
        "subtitle": 12,
        "header": 18,
        "message": 13,
        "status": 14,
    }
    RESPONSIVE_BREAKPOINTS = {
        "small": 800,
        "medium": 1200,
        "large": 1600,
    }

try:
    from models.custom_ai_model import \
        CustomAIModel  # noqa: F401  # pylint: disable=unused-import

    ULTRA_1M_AVAILABLE = True
    print("🚀 Modèle CustomAI unifié avec système 10M tokens intégré !")
except ImportError:
    ULTRA_1M_AVAILABLE = False
    print("📝 Interface moderne en mode standard")


class BaseGUI:
    """Base class providing shared state and core logic."""

    def __init__(self):
        """Initialise l'interface moderne avec système 10M tokens"""
        self.is_interrupted = False  # Pour interruption robuste
        self.logger = setup_logger("modern_ai_gui")
        # AIEngine principal pour toute l'interface
        self.config = Config()
        self.ai_engine = AIEngine(self.config)

        # Réutilisation du CustomAIModel déjà créé par AIEngine (évite double instanciation)
        if ULTRA_1M_AVAILABLE and hasattr(self.ai_engine, "local_ai") and self.ai_engine.local_ai:
            print("🚀 Interface moderne avec modèle CustomAI unifié (instance partagée)")
            try:
                # Réutiliser l'instance déjà créée par AIEngine
                self.custom_ai = self.ai_engine.local_ai

                # Afficher les stats initiales
                stats = self.custom_ai.get_context_stats()
                print(
                    f"📊 Contexte initial: {stats.get('context_size', 0):,} / {stats.get('max_context_length', 10_485_760):,} tokens"
                )
                print(
                    f"📚 Documents: {len(self.custom_ai.conversation_memory.stored_documents)}"
                )
                print(
                    f"🧠 Mode: {'Ultra 1M' if self.custom_ai.ultra_mode else 'Classique'}"
                )
                if hasattr(self.custom_ai, "local_llm") and self.custom_ai.local_llm:
                    print(
                        f"✅ LocalLLM actif - Historique: {len(self.custom_ai.local_llm.conversation_history)} messages"
                    )
            except (tk.TclError, AttributeError) as e:
                print(f"⚠️ Erreur initialisation CustomAI: {e}")
                self.custom_ai = None
        else:
            print("📝 Interface moderne en mode standard")
            self.custom_ai = None

        # File processor unifié
        self.file_processor = FileProcessor()

        # État de l'application
        self.is_thinking = False
        self.is_searching = False
        self.conversation_history = []

        # ⚡ OPTIMISATION MÉMOIRE: Limiter le nombre de messages affichés
        self.max_displayed_messages = 100  # Maximum de messages à garder dans l'UI
        self._message_widgets = []  # Liste des widgets de messages pour nettoyage
        self._height_adjust_counter = 0  # Compteur pour optimiser update_idletasks

        # Attributs pour la génération de fichiers
        self._file_generation_active = False
        self._file_generation_filename = None
        self._file_generation_dot_count = 0
        self._file_generation_widget = None
        self._pending_file_download = None
        self._saved_input_content = ""  # Sauvegarde du contenu de l'input
        self.layout_size = "medium"  # Taille du layout (small, medium, large)
        self.placeholder_text = ""
        self.placeholder_active = False
        self.last_detected_intent = {"name": "unknown", "confidence": 0.0}
        self.current_request_id = 0
        self.current_thinking_text = ""

        # Variables d'animation
        self.thinking_dots = 0
        self.search_frame = 0

        # Variables de l'indicateur MCP inline
        self._mcp_indicator_active = False
        self._mcp_indicator_container = None
        self._mcp_indicator_text_widget = None
        self._mcp_indicator_label_text = ""
        self._mcp_dot_count = 0
        self._mcp_consumed_icon = False

        # Initialisation des variables d'animation liées à la frappe
        self.typing_index = 0
        self.typing_text = ""
        self.typing_widget = None
        self.typing_speed = 1
        self._typing_interrupted = False

        # Mapping pour pré-analyse des blocs de code
        self._code_blocks_map = {}

        # Tableau pré-analysé pour les tableaux Markdown
        self._table_blocks = []

        # Ensemble des tableaux déjà formatés
        self._formatted_tables = set()

        # Pending links list (not dict!)
        self._pending_links = []

        # Positions déjà formatées
        self._formatted_positions = set()

        # Contenus en gras déjà formatés
        self._formatted_bold_contents = set()

        # Tracker pour la coloration des blocs de code en streaming
        self._last_colored_block_end = -1

        # UI components
        self.style_config = None
        self.fonts = None
        self.clear_btn = None
        self.help_btn = None
        self.status_label = None
        self.chat_frame = None

        # Container courant du dernier message IA
        self.current_message_container = None

        # ⚡ Variables pour le streaming temps réel avec animation
        self._streaming_buffer = ""  # Buffer accumulant les tokens
        self._streaming_buffer_original = ""  # Copie intacte (jamais modifiée par l'animation)
        self._streaming_complete = False  # Flag indiquant si le streaming est terminé
        self._streaming_mode = False  # Mode streaming actif
        self._streaming_widget = None  # Widget texte du streaming
        self._streaming_container = None  # Container du message streaming
        self._streaming_bubble_created = False  # Bulle déjà créée

        # Buttons for file actions
        self.file_plus_btn = None  # Bouton "+" menu fichiers (conversation)

        # Image attachée en attente d'envoi
        self._pending_image_path = None
        self._pending_image_base64 = None

        # Initialisation des placeholders UI
        self.thinking_frame = None
        self.thinking_label = None
        self.main_container = None
        self.input_text = None
        self.send_button = None
        self.content_container = None
        self.tab_frames = {}
        self.tab_buttons = {}
        self.agents_interface = None

        # Écran d'accueil (home screen style Claude)
        self._home_screen = None
        self._home_screen_active = False
        self._home_input = None
        self._home_input_wrapper = None
        self._home_preview_frame = None
        self._pending_files = []
        self._conv_container = None
        self._chat_content_frame = None
        # Mode thinking (widget raisonnement)
        self._thinking_mode_active = False
        self._input_container = None

        # Configuration de l'interface
        self.setup_modern_gui()
        self.create_modern_layout()
        self.setup_keyboard_shortcuts()
        self.show_welcome_message()

        # Initialisation IA en arrière-plan
        self.initialize_ai_async()
        self.ensure_input_is_ready()

        # Track whether the last bubble displayed was from the user
        self._last_bubble_is_user = False

    def interrupt_ai(self):
        """Interrompt l'IA : stop écriture, recherche, réflexion, etc."""
        try:
            print(
                "🛑 [GUI] STOP cliqué - Interruption de toutes les opérations en cours"
            )
            self.is_interrupted = True
            if hasattr(self, "current_request_id"):
                self.current_request_id += 1  # Invalide toutes les requêtes en cours
            # Si une passe de raisonnement était active, la réponse finale ne sera
            # jamais créée → réinitialiser le flag pour que le prochain message
            # affiche bien l'icône 🤖.
            self._thinking_mode_active = False
            # Réinitialiser _streaming_mode immédiatement : si STOP arrive pendant
            # le thinking (avant toute bulle de streaming), _finish_streaming_animation
            # ne sera jamais appelé → sans ce reset, _streaming_mode resterait True
            # indéfiniment et bloquerait FocusIn/FocusOut/KeyPress sur l'input.
            self._streaming_mode = False
            self.hide_status_indicators()
            if hasattr(self, "stop_typing_animation"):
                self.stop_typing_animation()
            if hasattr(self, "stop_internet_search"):
                self.stop_internet_search()
            if hasattr(self, "stop_thinking"):
                self.stop_thinking()
            self.set_input_state(True)
            self.is_thinking = False
            self.is_searching = False
            print("🛑 [GUI] Interruption terminée")
        except (tk.TclError, AttributeError):
            pass

    def _safe_focus_input(self):
        """Met le focus sur l'input de manière sécurisée"""
        try:
            if hasattr(self, "input_text"):
                # CustomTkinter: accéder au widget interne pour cget('state')
                try:
                    inner = getattr(self.input_text, '_textbox', self.input_text)
                    current_state = inner.cget("state")
                except (ValueError, AttributeError, tk.TclError):
                    current_state = "normal"
                if current_state == "normal":
                    self.input_text.focus_set()
                    # Restaurer le contenu sauvegardé s'il existe
                    if (
                        hasattr(self, "_saved_input_content")
                        and self._saved_input_content
                    ):
                        current_content = self.input_text.get("1.0", "end-1c").strip()
                        if not current_content:  # Seulement si vide
                            self.input_text.insert("1.0", self._saved_input_content)
                        delattr(self, "_saved_input_content")
        except (tk.TclError, AttributeError):
            pass

    def set_input_state(self, enabled: bool):
        """Active/désactive la zone de saisie et les boutons d'action, mais le bouton Envoyer devient STOP si IA occupe."""
        # if enabled:
        #     traceback.print_stack()
        try:
            # Zone de saisie
            if hasattr(self, "input_text"):
                state = "normal" if enabled else "disabled"
                try:
                    self.input_text.configure(state=state)
                except (tk.TclError, AttributeError):
                    pass
                if enabled:
                    self.root.after(100, self._safe_focus_input)
                else:
                    # Sauvegarder le contenu réel avant de désactiver.
                    # Ne pas sauvegarder si c'est le placeholder (sinon _safe_focus_input
                    # le restaurerait comme du vrai texte avec la couleur normale).
                    if getattr(self, "placeholder_active", False):
                        self._saved_input_content = ""
                    else:
                        try:
                            self._saved_input_content = self.input_text.get("1.0", "end-1c")
                        except (tk.TclError, AttributeError):
                            self._saved_input_content = ""
            # Bouton "+" fichiers
            for btn_name in ["file_plus_btn"]:
                if hasattr(self, btn_name):
                    btn = getattr(self, btn_name)
                    try:
                        btn.configure(state="normal" if enabled else "disabled")
                    except (tk.TclError, AttributeError):
                        pass
            # Boutons Clear Chat et Aide
            for btn_name in ["clear_btn", "help_btn"]:
                if hasattr(self, btn_name):
                    btn = getattr(self, btn_name)
                    try:
                        btn.configure(state="normal" if enabled else "disabled")
                    except (tk.TclError, AttributeError):
                        pass
            # Bouton d'envoi :
            if hasattr(self, "send_button"):
                if enabled:
                    self._set_send_button_normal()
                else:
                    self._set_send_button_stop()
        except (tk.TclError, AttributeError):
            pass

    def _set_send_button_normal(self):
        """Affiche le bouton Envoyer normal et réactive l'envoi."""
        try:
            if hasattr(self, "send_button"):
                # Orange vif, texte blanc, style moderne
                if self.use_ctk:
                    self.send_button.configure(
                        text="Envoyer ↗",
                        command=self.send_message,
                        state="normal",
                        fg_color=self.colors["accent"],
                        hover_color="#ff5730",
                        text_color="#ffffff",
                        border_width=0,
                    )
                else:
                    self.send_button.configure(
                        text="Envoyer ↗",
                        command=self.send_message,
                        state="normal",
                        bg=self.colors["accent"],
                        fg="#ffffff",
                        activebackground="#ff5730",
                        relief="flat",
                        border=0,
                    )
        except (tk.TclError, AttributeError):
            pass

    def _set_send_button_stop(self):
        """Affiche le bouton STOP (carré noir dans cercle blanc, fond blanc, bord noir) pour interrompre l'IA."""
        try:
            if hasattr(self, "send_button"):
                icon = "  ■  "
                if self.use_ctk:
                    self.send_button.configure(
                        text=icon,
                        command=self.interrupt_ai,
                        state="normal",
                        fg_color="#ffffff",
                        hover_color="#f3f3f3",
                        text_color="#111111",
                        border_color="#111111",
                        border_width=2,
                    )
                else:
                    self.send_button.configure(
                        text=icon,
                        command=self.interrupt_ai,
                        state="normal",
                        bg="#ffffff",
                        fg="#111111",
                        activebackground="#f3f3f3",
                        activeforeground="#111111",
                        highlightbackground="#111111",
                        highlightcolor="#111111",
                        highlightthickness=2,
                        relief="solid",
                    )
        except (tk.TclError, AttributeError):
            pass

    def determine_layout_size(self):
        """Détermine la taille de layout selon l'écran"""
        if hasattr(self, "RESPONSIVE_BREAKPOINTS"):
            if self.screen_width < RESPONSIVE_BREAKPOINTS["small"]:
                self.layout_size = "small"
            elif self.screen_width < RESPONSIVE_BREAKPOINTS["medium"]:
                self.layout_size = "medium"
            else:
                self.layout_size = "large"
        else:
            # Fallback
            if self.screen_width < 800:
                self.layout_size = "small"
            elif self.screen_width < 1200:
                self.layout_size = "medium"
            else:
                self.layout_size = "large"

    def setup_fonts(self):
        """Configure les polices selon l'OS et la taille d'écran"""
        os_name = platform.system().lower()

        # Sélection des polices selon l'OS
        if "FONT_CONFIG" in globals() and os_name in FONT_CONFIG:
            font_family = FONT_CONFIG[os_name]["primary"]
            mono_family = FONT_CONFIG[os_name]["mono"]
        else:
            # Fallback
            if os_name == "windows":
                font_family = "Segoe UI"
                mono_family = "Consolas"
            elif os_name == "darwin":  # macOS
                font_family = "SF Pro Display"
                mono_family = "SF Mono"
            else:  # Linux
                font_family = "Ubuntu"
                mono_family = "Ubuntu Mono"

        # Tailles selon la résolution
        if "FONT_SIZES" in globals() and self.layout_size in FONT_SIZES:
            sizes = FONT_SIZES[self.layout_size]
            self.style_config = FONT_SIZES  # Stocker pour utilisation ultérieure
        else:
            # Fallback amélioré avec des tailles plus raisonnables - UNIFIÉ À 11px
            sizes = {
                "title": 20,  # Réduit de 28 à 20
                "subtitle": 12,  # Réduit de 16 à 12
                "body": 11,  # Unifié à 11 pour cohérence
                "small": 10,  # Réduit de 12 à 10
                "chat": 11,  # UNIFIÉ À 11 comme les messages
                "code": 11,  # Réduit de 13 à 11
                "message": 11,  # UNIFIÉ À 11 pour cohérence totale
                "bold": 11,  # UNIFIÉ À 11 pour cohérence
            }
            # Créer style_config même en fallback avec des tailles réduites - UNIFIÉ À 11px
            self.style_config = {
                "large_screen": {
                    "title": 22,
                    "subtitle": 14,
                    "body": 11,
                    "small": 10,
                    "chat": 11,
                    "code": 11,
                    "message": 11,
                    "bold": 11,
                },
                "medium_screen": {
                    "title": 20,
                    "subtitle": 12,
                    "body": 11,
                    "small": 10,
                    "chat": 11,
                    "code": 11,
                    "message": 11,
                    "bold": 11,
                },
                "small_screen": {
                    "title": 18,
                    "subtitle": 11,
                    "body": 11,
                    "small": 9,
                    "chat": 11,
                    "code": 10,
                    "message": 11,
                    "bold": 11,
                },
            }

            # Fallback sizes selon la taille d'écran
            if self.layout_size == "small":
                sizes = self.style_config["small_screen"]
            elif self.layout_size == "medium":
                sizes = self.style_config["medium_screen"]
            else:
                sizes = self.style_config["large_screen"]

        self.fonts = {
            "title": (font_family, sizes["title"], "bold"),
            "subtitle": (font_family, sizes["subtitle"]),
            "body": (font_family, sizes["body"]),
            "chat": (font_family, sizes["chat"]),
            "bold": (font_family, sizes["body"], "bold"),
            "code": (mono_family, sizes["code"]),
        }

    def get_current_font_size(self, font_type="message"):
        """NOUVELLE VERSION - Taille de police unifiée pour tous les messages"""
        # Cette fonction retourne la taille de police pour chaque type
        # UNIFICATION TOTALE : tous les contenus de messages utilisent la même taille
        message_types = ["message", "body", "chat", "bold", "small", "content"]
        if font_type in message_types:
            return 12

        # Seuls les éléments d'interface gardent leurs tailles spécifiques
        interface_font_sizes = {
            "timestamp": 10,  # Timestamps un peu plus petits
            "icon": 16,  # Icônes (🤖, 👤)
            "header": 39,  # Éléments d'en-tête (icône robot agrandie)
            "status": 12,  # Indicateurs de statut
            "title": 32,  # Titres principaux
            "subtitle": 18,  # Sous-titres
        }

        return interface_font_sizes.get(font_type, 12)

    def hide_status_indicators(self):
        """Cache tous les indicateurs de statut et réactive la saisie"""
        # Arrêter les animations
        self.is_thinking = False
        self.is_searching = False

        # Cacher l'indicateur MCP inline s'il est toujours visible
        self._hide_mcp_tool_indicator()

        # Ne réactive l'input que si aucune animation IA n'est en cours
        if hasattr(self, "is_animation_running") and self.is_animation_running():
            return
        self.set_input_state(True)

        if hasattr(self, "thinking_frame"):
            self.thinking_frame.grid_remove()

        # Cache aussi le texte en bas
        if hasattr(self, "status_label"):
            self.status_label.configure(text="")

    # ------------------------------------------------------------------
    # Confirmation de suppression de fichier (MCP delete_local_file)
    # ------------------------------------------------------------------

    def _show_delete_confirmation_dialog(self, file_path: str, result: dict, event):
        """
        Affiche une boîte de dialogue stylisée demandant confirmation
        avant la suppression d'un fichier via l'outil MCP delete_local_file.

        Args:
            file_path: Chemin du fichier à supprimer
            result: Dict mutable {"confirmed": bool} mis à jour par le dialog
            event: threading.Event signalé quand l'utilisateur a répondu
        """
        accent = self.colors.get("accent", "#ff6b47")
        bg = self.colors.get("bg_secondary", "#1e1e1e")
        bg_dark = self.colors.get("bg_primary", "#121212")
        fg = self.colors.get("text_primary", "#ffffff")
        fg_dim = self.colors.get("text_secondary", "#aaaaaa")
        filename = os.path.basename(file_path)

        dialog = tk.Toplevel(self.root)
        dialog.title("Confirmation de suppression")
        dialog.configure(bg=bg)
        dialog.resizable(False, False)
        dialog.attributes("-topmost", True)
        dialog.grab_set()

        # Centrer la fenêtre
        dialog.update_idletasks()
        w, h = 460, 220
        x = self.root.winfo_x() + (self.root.winfo_width() - w) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - h) // 2
        dialog.geometry(f"{w}x{h}+{x}+{y}")

        # Icône d'avertissement
        icon_label = tk.Label(
            dialog, text="⚠️", font=("Segoe UI", 32), bg=bg, fg=accent
        )
        icon_label.pack(pady=(18, 4))

        # Message
        msg_label = tk.Label(
            dialog,
            text="L'IA souhaite supprimer ce fichier :",
            font=("Segoe UI", 11),
            bg=bg,
            fg=fg,
        )
        msg_label.pack()

        # Chemin du fichier (tronqué si trop long)
        display_path = file_path if len(file_path) <= 60 else "…" + file_path[-57:]
        path_label = tk.Label(
            dialog,
            text=display_path,
            font=("Consolas", 10, "bold"),
            bg=bg_dark,
            fg=accent,
            padx=12,
            pady=6,
            relief="groove",
            bd=1,
        )
        path_label.pack(padx=20, pady=(6, 4))

        name_label = tk.Label(
            dialog,
            text=f"({filename})",
            font=("Segoe UI", 9),
            bg=bg,
            fg=fg_dim,
        )
        name_label.pack()

        # Frame boutons
        btn_frame = tk.Frame(dialog, bg=bg)
        btn_frame.pack(pady=(12, 14))

        def _on_yes():
            result["confirmed"] = True
            dialog.destroy()
            event.set()

        def _on_no():
            result["confirmed"] = False
            dialog.destroy()
            event.set()

        if self.use_ctk:
            yes_btn = _ctk.CTkButton(
                btn_frame,
                text="Oui, supprimer",
                fg_color=accent,
                hover_color="#e05535",
                text_color="#ffffff",
                font=("Segoe UI", 12, "bold"),
                corner_radius=8,
                width=140,
                height=36,
                command=_on_yes,
            )
            no_btn = _ctk.CTkButton(
                btn_frame,
                text="Non, annuler",
                fg_color="#2a2a2a",
                hover_color="#3a3a3a",
                text_color="#ffffff",
                font=("Segoe UI", 12),
                corner_radius=8,
                width=140,
                height=36,
                command=_on_no,
            )
        else:
            yes_btn = tk.Button(
                btn_frame,
                text="Oui, supprimer",
                bg=accent,
                fg="#ffffff",
                font=("Segoe UI", 12, "bold"),
                relief="flat",
                padx=16,
                pady=6,
                cursor="hand2",
                command=_on_yes,
            )
            no_btn = tk.Button(
                btn_frame,
                text="Non, annuler",
                bg="#2a2a2a",
                fg="#ffffff",
                font=("Segoe UI", 12),
                relief="flat",
                padx=16,
                pady=6,
                cursor="hand2",
                command=_on_no,
            )

        no_btn.pack(side="left", padx=(0, 10))
        yes_btn.pack(side="left")

        # Fermeture via X → annulation
        dialog.protocol("WM_DELETE_WINDOW", _on_no)
        dialog.bind("<Escape>", lambda _e: _on_no())

    # ------------------------------------------------------------------
    # Indicateur MCP inline (dans le chat, sous icône 🤖)
    # ------------------------------------------------------------------

    def _show_mcp_tool_indicator(self, label: str):
        """
        Affiche un indicateur animé directement dans le chat, à droite de
        l'icône IA, pendant qu'un outil MCP est en cours d'exécution.
        L'animation cycle sur « label. », « label.. », « label... ».
        """
        try:
            # S'il y a déjà un indicateur MCP qu'on supprime, NE PAS restaurer
            # l'icône, car l'ancien indicateur l'avait (et on veut que le nouveau
            # s'enchaîne sans la répéter).
            was_already_active = getattr(self, "_mcp_indicator_active", False)
            # Mémoriser si le premier indicateur de la chaîne avait consommé l'icône,
            # pour la propager jusqu'au dernier indicateur (qui sera masqué par la synthèse).
            _icon_already_consumed = getattr(self, "_mcp_consumed_icon", False) if was_already_active else False

            # Supprimer l'éventuel indicateur précédent
            self._hide_mcp_tool_indicator(restore_icon=not was_already_active)

            # Masquer l'animation thinking pendant l'appel MCP
            self.is_thinking = False
            if hasattr(self, "thinking_frame"):
                self.thinking_frame.grid_remove()

            # Initialiser l'état d'animation
            self._mcp_indicator_active = True
            self._mcp_indicator_label_text = label
            self._mcp_dot_count = 0

            # Placer l'indicateur à la prochaine ligne disponible
            # (sans ajouter à conversation_history pour ne pas décaler les rows)
            # Le reasoning widget ajoute désormais un placeholder dans
            # conversation_history, donc len() est déjà correct.
            row = len(self.conversation_history)

            # Container principal (identique aux bulles IA)
            msg_container = self.create_frame(
                self.chat_frame, fg_color=self.colors["bg_chat"]
            )
            msg_container.grid(
                row=row, column=0, sticky="ew", pady=(0, 0)
            )
            msg_container.grid_columnconfigure(0, weight=1)
            self._mcp_indicator_container = msg_container

            # Frame de centrage (même padding que les bulles IA)
            center_frame = self.create_frame(
                msg_container, fg_color=self.colors["bg_chat"]
            )
            center_frame.grid(
                row=0, column=0, padx=(250, 250), pady=(0, 0), sticky="ew"
            )
            center_frame.grid_columnconfigure(0, weight=0)
            center_frame.grid_columnconfigure(1, weight=1)

            # Icône IA — masquée si le dernier élément affiché est déjà un output IA
            # (ex: widget Raisonnement au-dessus). On utilise _last_bubble_is_user
            # plutôt que _thinking_mode_active car ce dernier est reset par
            # _finalize_reasoning_widget avant l'arrivée de l'indicateur MCP.
            _show_icon = getattr(self, "_last_bubble_is_user", True)
            # Propager la consommation de l'icône à travers la chaîne d'outils :
            # si un indicateur précédent avait déjà affiché l'icône, on le mémorise
            # pour que le dernier masquage (synthèse) restaure correctement _last_bubble_is_user.
            self._mcp_consumed_icon = _show_icon or _icon_already_consumed
            self._last_bubble_is_user = False  # L'indicateur MCP est un output IA
            icon_lbl = self.create_label(
                center_frame,
                text="🤖",
                font=("Segoe UI", 16),
                fg_color=self.colors["bg_chat"],
                text_color=self.colors["accent"] if _show_icon else self.colors["bg_chat"],
            )
            icon_lbl.grid(row=0, column=0, sticky="nw", padx=(0, 10), pady=(1, 0))

            # Label texte animé (gris, légèrement italique)
            text_lbl = self.create_label(
                center_frame,
                text=label + ".",
                font=("Segoe UI", 11),
                fg_color=self.colors["bg_chat"],
                text_color="#888888",
            )
            text_lbl.grid(row=0, column=1, sticky="w", padx=(4, 0), pady=(4, 4))
            self._mcp_indicator_text_widget = text_lbl

            # Démarrer l'animation des points
            self.root.after(400, self._animate_mcp_dots)
            # Scroll vers le bas pour afficher l'indicateur
            self.root.after(60, self.scroll_to_bottom)

        except Exception as exc:
            print(f"⚠️ [MCP Indicator] Erreur création: {exc}")

    def _animate_mcp_dots(self):
        """Animation des points « . » / « .. » / « ... » sur l'indicateur MCP."""
        if not getattr(self, "_mcp_indicator_active", False):
            return
        try:
            dots = (".", "..", "...")[self._mcp_dot_count % 3]
            self._mcp_dot_count += 1
            text = self._mcp_indicator_label_text + dots
            if hasattr(self, "_mcp_indicator_text_widget"):
                self._mcp_indicator_text_widget.configure(text=text)
            # Planifier la prochaine frame
            if getattr(self, "_mcp_indicator_active", False):
                self.root.after(400, self._animate_mcp_dots)
        except Exception:
            pass

    def _hide_mcp_tool_indicator(self, restore_icon=True):
        """
        Supprime l'indicateur MCP inline du chat et arrête son animation.
        Si restore_icon est True et que cet indicateur avait "consommé" l'icône,
        restaure l'affichage (via _last_bubble_is_user = True) pour que la
        bulle suivante contienne l'icône IA.
        """
        self._mcp_indicator_active = False
        try:
            if getattr(self, "_mcp_indicator_container", None):
                self._mcp_indicator_container.destroy()
                self._mcp_indicator_container = None
                if restore_icon and getattr(self, "_mcp_consumed_icon", False):
                    # Restaurer l'affichage de l'icône IA pour la prochaine bulle
                    self._last_bubble_is_user = True
                self._mcp_consumed_icon = False
        except Exception:
            pass

    def on_enter_key(self, event):
        """Gère la touche Entrée - VERSION CORRIGÉE"""
        try:
            # Permettre l'envoi même si animation interrompue
            if self.is_animation_running():
                if getattr(self, "_typing_interrupted", False):
                    self.finish_typing_animation_dynamic(interrupted=True)
                else:
                    return "break"
            # Vérifier l'état de la touche Shift
            shift_pressed = bool(event.state & 0x1)
            if shift_pressed:
                return None  # Laisser tkinter gérer l'insertion de nouvelle ligne
            else:
                try:
                    self.send_message()
                    return "break"
                except (tk.TclError, AttributeError) as e:
                    print(f"❌ Erreur lors de l'envoi du message: {e}")
                    return "break"
        except (tk.TclError, AttributeError) as e:
            print(f"❌ Erreur on_enter_key: {e}")
            return "break"

    def ensure_input_is_ready(self):
        """S'assure que l'input est prêt à recevoir du texte"""
        try:
            if hasattr(self, "input_text"):
                # S'assurer que l'input est activé au démarrage
                self.input_text.configure(state="normal")
                # Mettre le focus
                self.root.after(200, self.input_text.focus_set())
                print("✅ Input ready")
        except (tk.TclError, AttributeError) as e:
            print(f"⚠️ Erreur ensure_input_ready: {e}")

    def on_shift_enter(self, _event):
        """Gère Shift+Entrée pour nouvelle ligne - VERSION CORRIGÉE"""
        # Cette fonction peut être vide car on_enter_key gère déjà tout
        return None

    def setup_keyboard_shortcuts(self):
        """Configure les raccourcis clavier"""
        # Raccourci Ctrl+L pour effacer
        self.root.bind("<Control-l>", lambda e: self.clear_chat())
        self.root.bind("<Control-L>", lambda e: self.clear_chat())

        # Focus sur le champ de saisie au démarrage
        self.root.after(100, self.input_text.focus())

    def set_placeholder(self):
        """Définit le texte de placeholder correctement (non éditable)"""
        self.placeholder_text = "Tapez votre message ici... (Entrée pour envoyer, Shift+Entrée pour nouvelle ligne)"
        self.placeholder_active = True

        def _focus_in_handler(_event):
            """FocusIn commun CTK + standard.
            Ne pas cacher le placeholder pendant le streaming : le double-clic ou
            tout autre événement de focus pendant le streaming causerait des incohérences
            (placeholder_active=False alors que le widget est désactivé)."""
            if getattr(self, "_streaming_mode", False):
                return  # Streaming en cours → ignorer
            self._hide_placeholder()

        def _focus_out_handler(_event):
            """FocusOut commun CTK + standard.
            Ne pas afficher le placeholder pendant le streaming : cela re-activerait
            l'input (via configure(state='normal') dans _show_placeholder) et rendrait
            le texte placeholder visible comme du vrai texte."""
            if getattr(self, "_streaming_mode", False):
                return  # Streaming en cours → ignorer
            if not self.input_text.get("1.0", "end-1c").strip():
                self._show_placeholder()

        def _key_press_handler(_event):
            """KeyPress commun CTK + standard.
            Bloqué pendant le streaming : le widget disabled accepte quand même
            les KeyPress quand il a le focus (après un double-clic). Sans ce guard,
            _hide_placeholder() changerait la couleur du texte en normal sans pouvoir
            effacer le contenu (delete échoue silencieusement sur widget disabled),
            rendant le placeholder visible comme du vrai texte."""
            if getattr(self, "_streaming_mode", False):
                return
            if self.placeholder_active:
                self._hide_placeholder()

        if self.use_ctk:
            # CustomTkinter avec placeholder natif si disponible
            try:
                # Essayer d'utiliser le placeholder natif de CustomTkinter
                config_keys = self.input_text.configure() if hasattr(self.input_text, "configure") else None
                if config_keys and "placeholder_text" in config_keys:
                    self.input_text.configure(placeholder_text=self.placeholder_text)
                    self.placeholder_active = False
                    return
            except (tk.TclError, AttributeError, TypeError):
                pass

            # Fallback pour CustomTkinter
            self._show_placeholder()
            self.input_text.bind("<FocusIn>", _focus_in_handler)
            self.input_text.bind("<FocusOut>", _focus_out_handler)
            self.input_text.bind("<KeyPress>", _key_press_handler)
        else:
            # Pour tkinter standard
            self._show_placeholder()
            self.input_text.bind("<FocusIn>", _focus_in_handler)
            self.input_text.bind("<FocusOut>", _focus_out_handler)
            self.input_text.bind("<KeyPress>", _key_press_handler)

    def _show_placeholder(self):
        """Affiche le placeholder en gris clair dans la zone de saisie."""
        if not self.placeholder_active:
            self.input_text.delete("1.0", "end")
            self.input_text.insert("1.0", self.placeholder_text)

            if self.use_ctk:
                self.input_text.configure(text_color=self.colors["placeholder"])
            else:
                self.input_text.configure(fg=self.colors["placeholder"])

            # Note : on ne modifie PAS l'état (state) du widget ici.
            # Le configure(state="disabled") suivi de state="normal" qui existait
            # ici ré-activait silencieusement l'input même pendant le streaming.
            self.placeholder_active = True

    def _hide_placeholder(self):
        """Cache le placeholder et permet la saisie normale"""
        if self.placeholder_active:
            self.input_text.delete("1.0", "end")

            if self.use_ctk:
                self.input_text.configure(text_color=self.colors["text_primary"])
            else:
                self.input_text.configure(fg=self.colors["text_primary"])

            self.placeholder_active = False

    def send_message(self):
        """Envoie le message - VERSION CORRIGÉE avec gestion placeholder"""
        try:
            # Permettre l'envoi même si animation interrompue
            if self.is_animation_running():
                if getattr(self, "_typing_interrupted", False):
                    self.finish_typing_animation_dynamic(interrupted=True)
                else:
                    return

            # Vérifier si le placeholder est actif
            if getattr(self, "placeholder_active", False):
                return  # Ne pas envoyer si seul le placeholder est présent

            # Récupérer le texte AVANT de vérifier l'état
            message = ""
            try:
                message = self.input_text.get("1.0", "end-1c").strip()
            except (tk.TclError, AttributeError) as e:
                print(f"❌ Erreur lecture input: {e}")
                return

            # Vérifier que ce n'est pas le texte du placeholder
            if message == getattr(self, "placeholder_text", "") or not message:
                return

            # S'assurer que la saisie est activée pour pouvoir lire et effacer
            was_disabled = False
            try:
                # CustomTkinter: accéder au widget interne pour cget('state')
                inner = getattr(self.input_text, '_textbox', self.input_text)
                current_state = inner.cget("state")
                if current_state == "disabled":
                    was_disabled = True
                    self.input_text.configure(state="normal")
            except (tk.TclError, AttributeError, ValueError):
                pass

            # Cacher les indicateurs
            self.hide_status_indicators()

            # Transition depuis l'écran d'accueil si actif
            self._dismiss_home_screen()

            # Ajouter le message utilisateur
            self._last_bubble_is_user = True
            self.add_message_bubble(message, is_user=True)

            # Nettoyer les aperçus de fichiers attachés
            if hasattr(self, "clear_file_previews"):
                self.clear_file_previews()

            # Effacer la zone de saisie et remettre le placeholder
            try:
                self.input_text.delete("1.0", "end")
                # Remettre le placeholder après effacement
                self._show_placeholder()
            except (tk.TclError, AttributeError) as e:
                print(f"❌ Erreur effacement: {e}")

            # Remettre l'état précédent si nécessaire
            if was_disabled:
                self.input_text.configure(state="disabled")

            # Scroll vers le bas
            self.scroll_to_bottom()

            # Afficher l'animation de réflexion
            self.show_thinking_animation()

            # Incrémente l'ID de requête
            if not hasattr(self, "current_request_id"):
                self.current_request_id = 0
            self.current_request_id += 1
            request_id = self.current_request_id

            # Réinitialise l'interruption à chaque nouveau message
            self.is_interrupted = False

            # Enregistrer dans l'historique des commandes
            try:
                engine = getattr(self, "ai_engine", None)
                if engine and hasattr(engine, "command_history") and engine.command_history:
                    engine.command_history.add(query=message)
            except Exception:
                pass

            # Lancer le traitement avec l'ID
            threading.Thread(
                target=self.quel_handle_message_with_id,
                args=(message, request_id),
                daemon=True,
            ).start()

        except (tk.TclError, AttributeError):

            # En cas d'erreur, s'assurer que la saisie est réactivée
            try:
                self.set_input_state(True)
            except (tk.TclError, AttributeError):
                pass

    def quel_handle_message_with_id(self, user_text, request_id):
        """
        Traite le message utilisateur avec STREAMING pour réponse instantanée.
        Les tokens Ollama alimentent l'animation de frappe en temps réel.
        """
        # 🎯 DÉTECTION SPÉCIALE : Génération de fichier
        file_keywords = [
            "génère moi un fichier",
            "crée moi un fichier",
            "génère un fichier",
            "crée un fichier",
        ]
        is_file_generation = any(
            keyword in user_text.lower() for keyword in file_keywords
        )

        if is_file_generation:
            # Extraire le nom du fichier depuis la requête
            filename_match = re.search(
                r"fichier\s+([a-zA-Z0-9_\-]+\.\w+)", user_text, re.IGNORECASE
            )
            filename = filename_match.group(1) if filename_match else "fichier.py"

            # Variables pour l'animation
            self._file_generation_active = True
            self._file_generation_filename = filename
            self._file_generation_dot_count = 0
            self._file_generation_widget = None

            # Ajouter un placeholder à l'historique IMMÉDIATEMENT pour réserver la ligne
            self.conversation_history.append(
                {
                    "text": f"Création du fichier '{filename}' en cours...",
                    "is_user": False,
                    "timestamp": datetime.now(),
                    "type": "file_generation_placeholder",
                }
            )

            def create_file_generation_bubble():
                """Crée une bulle SIMPLE pour la génération (sans streaming)"""
                try:
                    # Container principal - utiliser l'index du placeholder qu'on vient d'ajouter
                    msg_container = self.create_frame(
                        self.chat_frame, fg_color=self.colors["bg_chat"]
                    )
                    msg_container.grid(
                        row=len(self.conversation_history) - 1,
                        column=0,
                        sticky="ew",
                        pady=(0, 12),
                    )
                    msg_container.grid_columnconfigure(0, weight=1)

                    # Frame de centrage
                    center_frame = self.create_frame(
                        msg_container, fg_color=self.colors["bg_chat"]
                    )
                    center_frame.grid(
                        row=0, column=0, padx=(250, 250), pady=(0, 0), sticky="ew"
                    )
                    center_frame.grid_columnconfigure(0, weight=0)
                    center_frame.grid_columnconfigure(1, weight=1)

                    # Icône IA — visible uniquement si le dernier élément est un message utilisateur
                    _show_icon = getattr(self, "_last_bubble_is_user", True)
                    self._last_bubble_is_user = False
                    icon_label = self.create_label(
                        center_frame,
                        text="🤖",
                        font=("Segoe UI", 16),
                        fg_color=self.colors["bg_chat"],
                        text_color=self.colors["accent"] if _show_icon else self.colors["bg_chat"],
                    )
                    icon_label.grid(
                        row=0, column=0, sticky="nw", padx=(0, 10), pady=(1, 0)
                    )

                    # Container pour le message
                    message_container = self.create_frame(
                        center_frame, fg_color=self.colors["bg_chat"]
                    )
                    message_container.grid(
                        row=0, column=1, sticky="ew", padx=0, pady=(2, 2)
                    )
                    message_container.grid_columnconfigure(0, weight=1)

                    # Widget de texte
                    text_widget = tk.Text(
                        message_container,
                        width=120,
                        height=1,
                        bg=self.colors["bg_chat"],
                        fg=self.colors["text_primary"],
                        font=("Segoe UI", 11),
                        wrap="word",
                        relief="flat",
                        state="normal",
                        cursor="arrow",
                        padx=10,
                        pady=8,
                        highlightthickness=0,
                        borderwidth=0,
                    )
                    text_widget.grid(row=0, column=0, sticky="ew", padx=0, pady=0)

                    # Texte initial
                    text_widget.insert(
                        "1.0", f"Création du fichier '{filename}' en cours."
                    )
                    text_widget.configure(state="disabled")

                    # Stocker le widget et le container pour le timestamp
                    self._file_generation_widget = text_widget
                    self.current_message_container = message_container

                    # Scroll vers le bas
                    self.root.after(100, self.scroll_to_bottom)

                except (tk.TclError, AttributeError) as e:
                    print(f"Erreur création bulle: {e}")
                    traceback.print_exc()

            def animate_loading_dots():
                """Anime les points pendant le chargement - BOUCLE CONTINUE"""
                # Vérifier l'interruption en priorité
                if self.is_interrupted:
                    self._file_generation_active = False
                    if self._file_generation_widget:
                        try:
                            self._file_generation_widget.configure(state="normal")
                            self._file_generation_widget.delete("1.0", "end")
                            self._file_generation_widget.insert(
                                "1.0", "⚠️ Création du fichier interrompue."
                            )
                            self._file_generation_widget.configure(state="disabled")
                        except (tk.TclError, AttributeError) as e:
                            print(f"Erreur affichage interruption: {e}")
                    return

                if not self._file_generation_active:
                    return

                try:
                    # Calculer le nombre de points (1, 2, 3, 1, 2, 3...)
                    dot_count = (self._file_generation_dot_count % 3) + 1
                    self._file_generation_dot_count += 1

                    dots = "." * dot_count
                    message = f"Création du fichier '{filename}' en cours{dots}"

                    # Mettre à jour le widget directement
                    if self._file_generation_widget:
                        try:
                            self._file_generation_widget.configure(state="normal")
                            self._file_generation_widget.delete("1.0", "end")
                            self._file_generation_widget.insert("1.0", message)
                            self._file_generation_widget.configure(state="disabled")
                        except (tk.TclError, AttributeError) as e:
                            print(f"Erreur animation: {e}")

                    # CONTINUER L'ANIMATION EN BOUCLE (sauf si interrompu)
                    if self._file_generation_active and not self.is_interrupted:
                        self.root.after(500, animate_loading_dots)
                except (tk.TclError, AttributeError) as e:
                    print(f"Erreur dans animate_loading_dots: {e}")

            def generate_file_async():
                """Génère le fichier en arrière-plan"""
                try:
                    # Vérifier l'interruption AVANT de commencer
                    if self.is_interrupted:
                        self._file_generation_active = False

                        def show_interrupted():
                            if self._file_generation_widget:
                                self._file_generation_widget.configure(state="normal")
                                self._file_generation_widget.delete("1.0", "end")
                                self._file_generation_widget.insert(
                                    "1.0", "⚠️ Création du fichier interrompue."
                                )
                                self._file_generation_widget.configure(state="disabled")
                                self.is_thinking = False
                                self.set_input_state(True)

                        self.root.after(0, show_interrupted)
                        return

                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)

                    # Callback avec debug
                    def check_interrupted():
                        interrupted = self.is_interrupted or self.current_request_id != request_id
                        if interrupted:
                            print(
                                f"🛑 [GUI Callback] Interruption détectée! is_interrupted={self.is_interrupted}, id_changed={self.current_request_id != request_id}"
                            )
                        return interrupted

                    result = loop.run_until_complete(
                        self.ai_engine.process_query(
                            user_text, is_interrupted_callback=check_interrupted
                        )
                    )
                    loop.close()

                    # Arrêter l'animation de points
                    self._file_generation_active = False

                    # Vérifier si le résultat indique une interruption
                    if result.get("interrupted"):
                        # L'opération a été interrompue - afficher le message d'interruption
                        def show_interrupted_after():
                            if self._file_generation_widget:
                                self._file_generation_widget.configure(state="normal")
                                self._file_generation_widget.delete("1.0", "end")
                                self._file_generation_widget.insert(
                                    "1.0", "⚠️ Création du fichier interrompue."
                                )
                                self._file_generation_widget.configure(state="disabled")
                                self.is_thinking = False
                                self.set_input_state(True)

                        self.root.after(0, show_interrupted_after)
                        return

                    # Mettre à jour avec le résultat
                    if result.get("type") == "file_generation" and result.get(
                        "success"
                    ):
                        self._pending_file_download = {
                            "filename": result.get("filename"),
                            "file_path": result.get("file_path"),
                            "code": result.get("code", ""),
                        }

                        # Messages variés pour la génération de fichiers
                        file_generation_messages = [
                            "✅ Votre fichier est prêt ! Vous pouvez le télécharger en cliquant simplement sur son nom. 👇\n\nEst-ce que vous souhaitez autre chose ? ",
                            "🎉 Fichier généré avec succès ! Cliquez sur le nom pour le télécharger. 👇\n\nBesoin d'autre chose ? ",
                            "✨ Et voilà ! Votre fichier est créé. Un simple clic sur le nom pour le récupérer. 👇\n\nQue puis-je faire d'autre pour vous ? ",
                            "🚀 Génération terminée ! Le fichier est prêt au téléchargement (cliquez sur le nom). 👇\n\nUne autre demande ? ",
                            "💾 Fichier créé ! Téléchargez-le en cliquant sur son nom ci-dessous. 👇\n\nJe peux vous aider pour autre chose ? ",
                            "✅ Mission accomplie ! Votre fichier vous attend. Cliquez pour télécharger. 👇\n\nAutre chose à générer ? ",
                            "🎯 Fichier prêt à être téléchargé ! Un clic sur le nom et c'est bon. 👇\n\nQu'est-ce qu'on fait ensuite ? ",
                            "⚡ C'est fait ! Votre fichier est disponible. Cliquez dessus pour le récupérer. 👇\n\nUne autre création ? ",
                        ]

                        # Choisir un message aléatoire
                        final_message = random.choice(file_generation_messages)

                        # REMPLACER le contenu du widget AVEC ANIMATION
                        def update_final_message():
                            try:
                                print(f"[DEBUG] Filename: {result.get('filename')}")
                                print(f"[DEBUG] File path: {result.get('file_path')}")

                                if self._file_generation_widget:
                                    filename_to_show = result.get("filename")
                                    file_path = result.get("file_path")

                                    # Message complet avec nom de fichier
                                    full_message = final_message + filename_to_show

                                    # Calculer la hauteur nécessaire (nombre de lignes + marge)
                                    num_lines = full_message.count("\n") + 1
                                    widget_height = max(num_lines, 3)

                                    print(
                                        f"[DEBUG] Nombre de lignes: {num_lines}, hauteur widget: {widget_height}"
                                    )

                                    # Ajuster la hauteur du widget
                                    self._file_generation_widget.configure(
                                        height=widget_height
                                    )

                                    # Animation de frappe caractère par caractère
                                    def animate_typing(index=0):
                                        if index < len(full_message):
                                            self._file_generation_widget.configure(
                                                state="normal"
                                            )
                                            self._file_generation_widget.delete(
                                                "1.0", "end"
                                            )
                                            self._file_generation_widget.insert(
                                                "1.0", full_message[: index + 1]
                                            )
                                            self._file_generation_widget.configure(
                                                state="disabled"
                                            )

                                            # Continuer l'animation (vitesse: 20ms par caractère)
                                            self.root.after(
                                                20, lambda: animate_typing(index + 1)
                                            )
                                        else:
                                            # Animation terminée - ajouter le tag cliquable
                                            add_clickable_tag()

                                    def add_clickable_tag():
                                        try:
                                            self._file_generation_widget.configure(
                                                state="normal"
                                            )

                                            # Trouver la position du nom de fichier
                                            text_content = (
                                                self._file_generation_widget.get(
                                                    "1.0", "end-1c"
                                                )
                                            )
                                            filename_pos = text_content.rfind(
                                                filename_to_show
                                            )

                                            if filename_pos != -1:
                                                lines_before = text_content[
                                                    :filename_pos
                                                ].count("\n")
                                                col_before = (
                                                    filename_pos
                                                    - text_content[:filename_pos].rfind(
                                                        "\n"
                                                    )
                                                    - 1
                                                    if "\n"
                                                    in text_content[:filename_pos]
                                                    else filename_pos
                                                )

                                                start_idx = (
                                                    f"{lines_before + 1}.{col_before}"
                                                )
                                                end_idx = f"{lines_before + 1}.{col_before + len(filename_to_show)}"

                                                tag_name = (
                                                    f"file_download_{filename_to_show}"
                                                )
                                                self._file_generation_widget.tag_add(
                                                    tag_name, start_idx, end_idx
                                                )
                                                self._file_generation_widget.tag_config(
                                                    tag_name,
                                                    foreground="#3b82f6",
                                                    underline=True,
                                                )

                                                # Closures pour les handlers
                                                def make_click_handler(path, name):
                                                    def on_click(_event):
                                                        self.download_file_to_downloads(
                                                            path, name
                                                        )

                                                    return on_click

                                                self._file_generation_widget.tag_bind(
                                                    tag_name,
                                                    "<Button-1>",
                                                    make_click_handler(
                                                        file_path, filename_to_show
                                                    ),
                                                )
                                                self._file_generation_widget.tag_bind(
                                                    tag_name,
                                                    "<Enter>",
                                                    lambda _e: self._file_generation_widget.configure(
                                                        cursor="hand2"
                                                    ),
                                                )
                                                self._file_generation_widget.tag_bind(
                                                    tag_name,
                                                    "<Leave>",
                                                    lambda _e: self._file_generation_widget.configure(
                                                        cursor=""
                                                    ),
                                                )

                                            self._file_generation_widget.configure(
                                                state="disabled"
                                            )

                                            # Afficher le timestamp
                                            self._show_timestamp_for_current_message()

                                            # Mettre à jour le placeholder dans conversation_history
                                            for i in range(
                                                len(self.conversation_history) - 1,
                                                -1,
                                                -1,
                                            ):
                                                if (
                                                    self.conversation_history[i].get(
                                                        "type"
                                                    )
                                                    == "file_generation_placeholder"
                                                ):
                                                    self.conversation_history[i] = {
                                                        "text": full_message,
                                                        "is_user": False,
                                                        "timestamp": datetime.now(),
                                                        "type": "file_generation",
                                                    }
                                                    break

                                            # Ajouter au contexte Ollama pour qu'il se souvienne
                                            if (
                                                hasattr(
                                                    self.ai_engine.local_ai, "local_llm"
                                                )
                                                and self.ai_engine.local_ai.local_llm
                                            ):
                                                try:
                                                    # Utiliser la VRAIE requête de l'utilisateur (pas hardcodé)
                                                    user_message = user_text  # La requête originale
                                                    # Message assistant (sans le nom du fichier à la fin pour éviter la répétition)
                                                    assistant_message = "✅ Votre fichier est prêt ! Vous pouvez le télécharger en cliquant simplement sur son nom. 👇\n\n🚀 Est-ce que vous souhaitez autre chose ?"

                                                    # Utiliser add_to_history() au lieu de manipuler directement la liste
                                                    llm = (
                                                        self.ai_engine.local_ai.local_llm
                                                    )
                                                    llm.add_to_history(
                                                        "user", user_message
                                                    )
                                                    llm.add_to_history(
                                                        "assistant", assistant_message
                                                    )

                                                    print(
                                                        "[DEBUG] Messages ajoutés à l'historique Ollama via add_to_history()"
                                                    )
                                                    print(
                                                        f"[DEBUG] Historique contient maintenant {len(llm.conversation_history)} messages"
                                                    )
                                                except (AttributeError, TypeError) as e:
                                                    print(
                                                        f"Erreur ajout historique Ollama: {e}"
                                                    )
                                                    traceback.print_exc()

                                            # NETTOYER _pending_file_download pour éviter qu'il réapparaisse
                                            self._pending_file_download = None

                                            # ARRÊTER l'animation de thinking
                                            self.is_thinking = False

                                            # Réactiver la saisie
                                            self.set_input_state(True)

                                        except (tk.TclError, AttributeError) as e:
                                            print(f"Erreur ajout tag: {e}")
                                            traceback.print_exc()

                                    # Démarrer l'animation de frappe
                                    animate_typing(0)

                            except (tk.TclError, AttributeError) as e:
                                print(f"Erreur mise à jour finale: {e}")
                                traceback.print_exc()

                        self.root.after(0, update_final_message)

                    else:
                        # Erreur
                        def show_error():
                            if self._file_generation_widget:
                                self._file_generation_widget.configure(state="normal")
                                self._file_generation_widget.delete("1.0", "end")
                                self._file_generation_widget.insert(
                                    "1.0", "❌ Erreur lors de la génération du fichier."
                                )
                                self._file_generation_widget.configure(state="disabled")
                                self.is_thinking = False
                                self.set_input_state(True)

                        self.root.after(0, show_error)

                except (OSError, ValueError) as e:
                    print(f"Erreur génération: {e}")
                    traceback.print_exc()
                    self._file_generation_active = False

                    def show_error():
                        if self._file_generation_widget:
                            self._file_generation_widget.configure(state="normal")
                            self._file_generation_widget.delete("1.0", "end")
                            self._file_generation_widget.insert(
                                "1.0", f"❌ Erreur: {str(e)}"
                            )
                            self._file_generation_widget.configure(state="disabled")
                            self.is_thinking = False
                            self.set_input_state(True)

                    self.root.after(0, show_error)

            # Bloquer la saisie pendant la génération
            self.set_input_state(False)

            # ACTIVER l'animation de "thinking"
            self.is_thinking = True

            # Créer la bulle et démarrer l'animation
            create_file_generation_bubble()
            self.root.after(500, animate_loading_dots)

            # Lancer la génération dans un thread
            threading.Thread(target=generate_file_async, daemon=True).start()

            return

        # Détection d'intention (code existant)
        intent = None
        confidence = 0.0
        try:
            if hasattr(self.ai_engine, "detect_intent"):
                intent, confidence = self.ai_engine.detect_intent(user_text)
            else:
                if (
                    "internet" in user_text.lower()
                    or "cherche sur internet" in user_text.lower()
                ):
                    intent = "internet_search"
                    confidence = 1.0
                elif (
                    "qui es-tu" in user_text.lower() or "tu es qui" in user_text.lower()
                ):
                    intent = "identity_question"
                    confidence = 1.0
                else:
                    intent = "unknown"
                    confidence = 0.0
        except (AttributeError, TypeError):
            intent = "unknown"
            confidence = 0.0

        self.last_detected_intent = {"name": intent, "confidence": confidence}

        print(
            f"[DEBUG] (ModernAIGUI) Question transmise - Mode {'CustomAI+Streaming' if self.custom_ai else 'Standard'} : {repr(user_text)}"
        )

        try:
            # ⚡ MODE MCP + STREAMING — point d'entrée unifié via AIEngine
            print("⚡ [GUI] Activation du mode STREAMING (MCP tool-calling activé)...")

            # ── WIDGET RAISONNEMENT : thinking + plan de l'orchestrateur ─────
            _image_pending = getattr(self, "_pending_image_base64", None)
            _is_complex = (
                hasattr(self, "ai_engine")
                and self.ai_engine.is_ollama_active()
                and self.ai_engine.is_complex_query(user_text)
                and not _image_pending
            )
            # Vérifier si la requête est conversationnelle (identité, salutations, etc.)
            # Pour ces requêtes, ni le thinking ni le plan ne seront utilisés.
            _is_conversational = (
                hasattr(self, "ai_engine")
                and hasattr(self.ai_engine, "is_conversational")
                and self.ai_engine.is_conversational(user_text)
            )
            # Le widget sert aussi à afficher le plan de l'orchestrateur.
            # On le crée UNIQUEMENT pour les requêtes complexes (mode Thinking)
            # où un vrai raisonnement est attendu, pour éviter d'afficher un
            # widget vide qui disparaît quand la réponse arrive.
            _show_reasoning = not _is_conversational and _is_complex
            if _show_reasoning:
                print("🧠 [GUI] Requête complexe détectée → mode Thinking activé")
                self.root.after(0, self._create_reasoning_widget)
            # ─────────────────────────────────────────────────────────────────

            # Réinitialiser le buffer de streaming
            self._streaming_buffer = ""
            self._streaming_buffer_original = ""
            self._streaming_complete = False
            self._streaming_mode = True
            self._streaming_bubble_created = False

            def on_token_received(token):
                """Callback appelé pour chaque token reçu d'Ollama."""
                if self.current_request_id != request_id or self.is_interrupted:
                    return False
                self._streaming_buffer += token
                self._streaming_buffer_original += token
                if not self._streaming_bubble_created:
                    self._streaming_bubble_created = True
                    self.root.after(0, self._create_streaming_bubble_with_animation)
                return True

            def on_thinking_token(token):
                """Callback pour chaque token de raisonnement (Thinking Mode)."""
                interrupted = self.current_request_id != request_id or self.is_interrupted
                if interrupted:
                    return False
                self.root.after(0, lambda t=token: self._stream_thinking_token(t))
                return True

            def on_thinking_complete():
                """Appelé quand la passe de raisonnement est terminée."""
                print("🧠 [ON_THINKING_COMPLETE] Appelé")
                self.root.after(0, self._finalize_reasoning_widget)

            def on_tool_call(tool_name: str, args: dict):
                """
                Feedback visuel quand Ollama appelle un outil.
                Affiche un message transitoire dans la zone de statut.
                """
                tool_labels = {
                    "web_search": f"🔍 Recherche sur internet : « {args.get('query', '')} »",
                    "search_memory": "🧠 Consultation de la mémoire vectorielle",
                    "read_local_file": f"📄 Lecture du fichier : {args.get('path', '')}",
                    "list_directory": f"📁 Exploration du répertoire : {args.get('path', '.')}",
                    "generate_code": f"💻 Génération de code {args.get('language', '')}",
                    "calculate": f"🔢 Calcul : {args.get('expression', '')}",
                    "search_local_files": f"🔎 Recherche de fichiers : « {args.get('query', '')} »",
                    "write_local_file": f"💾 Modification du fichier : {os.path.basename(args.get('path', '')) if 'path' in args else ''}",
                    "move_local_file": f"🚚 Déplacement : {os.path.basename(args.get('source', '')) if 'source' in args else ''}",
                    "delete_local_file": f"🗑️ Suppression : {os.path.basename(args.get('path', '')) if 'path' in args else ''}",
                    "create_directory": f"📂 Création du dossier : {os.path.basename(args.get('path', '')) if 'path' in args else ''}",
                    "synthesis": "🧠 Analyse du résultat et synthèse en cours",
                }
                label = tool_labels.get(
                    tool_name, f"🔧 Outil en cours : {tool_name}…"
                )
                print(f"[MCP] {label}")

                # S'il s'agit de la synthèse et que la bulle contient déjà du texte, injecter un retour à la ligne
                if tool_name == "synthesis":
                    # Pour la synthèse, on masque l'indicateur et on prépare le texte
                    def _prepare_synthesis_ui():
                        if getattr(self, "_streaming_mode", False) and getattr(self, "_streaming_buffer", ""):
                            # Assurer exactement deux retours à la ligne avec l'existant
                            old_len = len(self._streaming_buffer)
                            stripped = self._streaming_buffer.rstrip('\n')
                            stripped_orig = self._streaming_buffer_original.rstrip('\n')

                            self._streaming_buffer = stripped + "\n\n"
                            self._streaming_buffer_original = stripped_orig + "\n\n"

                            # Sécuriser l'index d'animation si le texte vient d'être raccourci d'un tas d'espaces
                            diff = len(self._streaming_buffer) - old_len
                            if hasattr(self, "typing_index") and diff < 0:
                                self.typing_index = min(self.typing_index, len(self._streaming_buffer))

                        # Masquer l'indicateur d'outil en cours.
                        # La synthèse s'écrit tout de suite, donc pas besoin du panneau temporaire inutile !
                        if hasattr(self, "_hide_mcp_tool_indicator"):
                            self._hide_mcp_tool_indicator()

                    try:
                        self.root.after(0, _prepare_synthesis_ui)
                    except Exception:
                        pass
                    return  # On ne crée pas l'indicateur MCP "Analyse et synthèse" pour éviter qu'il s'affiche sous le texte en temps réel

                # Pour tous les autres outils (Modification du fichier, Recherche...), réduire les éventuels sauts de ligne finaux
                def _strip_trailing_newlines_from_stream():
                    if getattr(self, "_streaming_mode", False) and getattr(self, "_streaming_buffer", ""):
                        old_len = len(self._streaming_buffer)
                        if old_len > 0 and self._streaming_buffer.endswith('\n'):
                            self._streaming_buffer = self._streaming_buffer.rstrip('\n')
                            self._streaming_buffer_original = self._streaming_buffer_original.rstrip('\n')
                            # Sécuriser l'index
                            if hasattr(self, "typing_index") and self.typing_index > len(self._streaming_buffer):
                                self.typing_index = len(self._streaming_buffer)

                try:
                    self.root.after(0, _strip_trailing_newlines_from_stream)
                    self.root.after(
                        0,
                        lambda l=label: self._show_mcp_tool_indicator(l),
                    )
                except Exception:
                    pass

            # Image en attente (vision)
            image_b64 = _image_pending
            if image_b64:
                self._pending_image_base64 = None
                self._pending_image_path = None

            def on_delete_confirm(file_path: str) -> bool:
                """Demande confirmation à l'utilisateur avant de supprimer un fichier.
                Bloque le thread appelant jusqu'à la réponse (Event)."""
                result = {"confirmed": False}
                event = threading.Event()

                def _show_dialog():
                    self._show_delete_confirmation_dialog(file_path, result, event)

                self.root.after(0, _show_dialog)
                event.wait()
                return result["confirmed"]

            response = self.ai_engine.process_query_stream(
                user_text,
                on_token=on_token_received,
                on_tool_call=on_tool_call,
                on_thinking_token=on_thinking_token if _show_reasoning else None,
                on_thinking_complete=on_thinking_complete if _show_reasoning else None,
                image_base64=image_b64,
                is_interrupted_callback=lambda: self.is_interrupted or self.current_request_id != request_id,
                on_delete_confirm=on_delete_confirm,
            )

            # Marquer le streaming comme terminé SEULEMENT si cette requête est
            # encore active. Un thread obsolète (request_id périmé) ne doit PAS
            # toucher _streaming_complete sous peine d'interrompre prématurément
            # l'animation d'un message suivant.
            if self.current_request_id == request_id:
                self._streaming_complete = True
                print(
                    f"📥 [STREAM] Réception terminée : {len(self._streaming_buffer)} caractères reçus (animation en cours)"
                )
                # Si la réponse n'a pas été streamée token par token (ex: FAQ,
                # fallback classique sans Ollama), l'afficher d'un bloc
                if not self._streaming_bubble_created and response:
                    on_token_received(response)
            else:
                print(
                    f"⏭ [STREAM] Requête obsolète {request_id} ignorée "
                    f"(active: {self.current_request_id})"
                )

        except (ConnectionError, TimeoutError, AttributeError) as e:
            print(f"❌ [GUI] Erreur: {e}")
            response = f"❌ Erreur IA : {e}"
            if self.current_request_id == request_id:
                self.root.after(0, lambda: self.add_ai_response(response))
        finally:
            # Garantir que les points "Raisonnement..." s'arrêtent toujours,
            # mais SEULEMENT pour la requête encore active.
            # Un thread obsolète (request_id périmé) ne doit PAS stopper les dots
            # ni masquer le bouton STOP d'un message suivant en cours.
            if self.current_request_id == request_id:
                if getattr(self, "_reasoning_dots_active", False):
                    self.root.after(0, self._stop_reasoning_dots)
                self.root.after(0, self.hide_status_indicators)

    def add_ai_response(self, response):
        """Ajoute une réponse de l'IA - VERSION CORRIGÉE pour affichage complet"""

        # EXTRACTION ROBUSTE du texte de réponse
        if isinstance(response, dict):
            # Ordre de priorité pour extraire le message
            message_keys = ["message", "text", "content", "response", "ai_response"]

            text_response = None
            for key in message_keys:
                if key in response and response[key]:
                    text_response = response[key]
                    break

            # Si aucune des clés principales n'existe, prendre la première valeur non-vide
            if text_response is None:
                for key, value in response.items():
                    if value and isinstance(value, (str, dict)):
                        text_response = value
                        break

            # Si c'est encore un dictionnaire imbriqué, extraire récursivement
            if isinstance(text_response, dict):
                if "message" in text_response:
                    text_response = text_response["message"]
                elif "text" in text_response:
                    text_response = text_response["text"]
                else:
                    text_response = str(text_response)

            # Convertir en string si nécessaire
            if text_response is None:
                text_response = str(response)
            else:
                text_response = str(text_response)

        else:
            text_response = str(response)

        # VÉRIFICATION que le texte n'est pas vide
        if not text_response or text_response.strip() == "" or text_response == "None":
            text_response = "⚠️ Réponse vide reçue"

        # Désactiver explicitement l'input pendant l'animation IA
        self.set_input_state(False)
        # Ajouter le message avec le texte complet (déclenche l'animation de frappe IA)
        self.add_message_bubble(text_response, is_user=False)

        # Scroll vers le bas avec délai pour s'assurer que le message est rendu
        self.root.after(100, self.scroll_to_bottom)
        self.root.after(300, self.scroll_to_bottom)  # Double tentative

    def clear_chat(self):
        """Efface la conversation ET les documents en mémoire pour repartir de zéro"""
        try:
            # Vider l'historique local de l'interface
            self.conversation_history.clear()

            # Vider l'interface de chat
            for widget in self.chat_frame.winfo_children():
                widget.destroy()

            # Effacer la mémoire de l'IA (conversation)
            if hasattr(self.ai_engine, "clear_conversation"):
                self.ai_engine.clear_conversation()

            # Effacer les documents du CustomAI
            if hasattr(self, "custom_ai") and self.custom_ai:
                # 🧠 IMPORTANT: Effacer l'historique du LocalLLM (mémoire Ollama)
                if hasattr(self.custom_ai, "local_llm") and self.custom_ai.local_llm:
                    if hasattr(self.custom_ai.local_llm, "clear_history"):
                        self.custom_ai.local_llm.clear_history()
                        print("🗑️ Historique LocalLLM (Ollama) effacé")

                # Effacer la mémoire de conversation (inclut les documents)
                if hasattr(self.custom_ai, "conversation_memory"):
                    self.custom_ai.conversation_memory.clear()
                    print("🗑️ Mémoire de conversation CustomAI effacée")

                # Effacer les documents du système Ultra si activé
                if hasattr(self.custom_ai, "ultra_mode") and self.custom_ai.ultra_mode:
                    if hasattr(self.custom_ai, "documents_storage"):
                        self.custom_ai.documents_storage.clear()
                        print("🗑️ Documents Ultra effacés")
                    if (
                        hasattr(self.custom_ai, "context_manager")
                        and self.custom_ai.context_manager
                    ):
                        # Réinitialiser le gestionnaire de contexte
                        if hasattr(self.custom_ai.context_manager, "clear_context"):
                            self.custom_ai.context_manager.clear_context()
                        elif hasattr(self.custom_ai.context_manager, "clear"):
                            self.custom_ai.context_manager.clear()
                        elif hasattr(self.custom_ai.context_manager, "documents"):
                            self.custom_ai.context_manager.documents.clear()
                        print("🗑️ Context Manager Ultra effacé")
                    # Réinitialiser les statistiques de contexte
                    if hasattr(self.custom_ai, "context_stats"):
                        self.custom_ai.context_stats = {
                            "documents_processed": 0,
                            "total_tokens": 0,
                            "chunks_created": 0,
                        }

                # Réinitialiser session_context
                if hasattr(self.custom_ai, "session_context"):
                    self.custom_ai.session_context = {
                        "documents_processed": [],
                        "code_files_processed": [],
                        "last_document_type": None,
                        "current_document": None,
                    }
                    print("🗑️ Session context effacé")

                # Effacer le VectorMemory si disponible
                if (
                    hasattr(self.custom_ai, "vector_memory")
                    and self.custom_ai.vector_memory
                ):
                    if hasattr(self.custom_ai.vector_memory, "clear_all"):
                        self.custom_ai.vector_memory.clear_all()
                        print("🗑️ VectorMemory effacé")

            # 🧠 Effacer aussi l'historique du LocalLLM dans l'AIEngine
            if hasattr(self.ai_engine, "local_ai") and self.ai_engine.local_ai:
                if (
                    hasattr(self.ai_engine.local_ai, "local_llm")
                    and self.ai_engine.local_ai.local_llm
                ):
                    if hasattr(self.ai_engine.local_ai.local_llm, "clear_history"):
                        self.ai_engine.local_ai.local_llm.clear_history()
                        print("🗑️ Historique LocalLLM (AIEngine) effacé")

            # Mettre à jour le compteur de tokens dans l'interface
            if hasattr(self, "update_context_stats"):
                self.update_context_stats()

            # Message de confirmation
            self.show_welcome_message()

            # RETOURNER EN HAUT de la page après clear
            self.scroll_to_top()

            self.logger.info("Conversation et documents effacés")
            print(
                "✅ Clear complet: conversation + documents + mémoire + historique Ollama"
            )

        except (tk.TclError, AttributeError) as e:
            self.logger.error("Erreur lors de l'effacement: %s", e)
            messagebox.showerror("Erreur", f"Impossible d'effacer la conversation: {e}")

    def show_welcome_message(self):
        """Affiche l'écran d'accueil style Claude (sans bulle de message)."""
        self._create_home_screen()

    def _create_home_screen(self):
        """
        Crée l'écran d'accueil centré style Claude.
        L'overlay couvre TOUT le chat_content (conv + input, rowspan=2).
        Le groupe titre + input home est centré verticalement.
        """
        # Fermer un éventuel écran d'accueil existant
        if getattr(self, "_home_screen", None) is not None:
            try:
                self._home_screen.destroy()
            except Exception:
                pass
            self._home_screen = None
        self._home_input = None

        # Masquer la zone de conversation ET l'input réel
        conv = getattr(self, "_conv_container", None)
        if conv is not None:
            try:
                conv.grid_remove()
            except Exception:
                pass

        input_c = getattr(self, "_input_container", None)
        if input_c is not None:
            try:
                input_c.grid_remove()
            except Exception:
                pass

        # Parent = chat_content frame (contient row=0:conv + row=1:input)
        parent = getattr(self, "_chat_content_frame", None)
        if parent is None:
            return

        # Overlay couvrant les 2 lignes via rowspan=2
        self._home_screen = self.create_frame(parent, fg_color=self.colors["bg_primary"])
        self._home_screen.grid(row=0, column=0, rowspan=2, sticky="nsew", padx=0, pady=0)
        self._home_screen.grid_columnconfigure(0, weight=1)
        self._home_screen.grid_rowconfigure(0, weight=2)   # spacer haut (plus petit = groupe plus haut)
        self._home_screen.grid_rowconfigure(1, weight=0)   # contenu (taille naturelle)
        self._home_screen.grid_rowconfigure(2, weight=3)   # spacer bas (plus grand = groupe plus haut)

        # ── Frame centrale (titre + zone de saisie) ─────────────────────────────
        center = self.create_frame(self._home_screen, fg_color=self.colors["bg_primary"])
        center.grid(row=1, column=0, sticky="", padx=20)
        center.grid_columnconfigure(0, weight=1)

        # Emoji 🤖 en orange
        if self.use_ctk:
            emoji_lbl = _ctk.CTkLabel(
                center, text="🤖", font=("Segoe UI", 64),
                text_color="#e07340", fg_color="transparent",
            )
        else:
            emoji_lbl = tk.Label(
                center, text="🤖", font=("Segoe UI", 64),
                fg="#e07340", bg=self.colors["bg_primary"],
            )
        emoji_lbl.grid(row=0, column=0, pady=(0, 8))

        # "My_AI" en blanc, grand et gras
        if self.use_ctk:
            title_lbl = _ctk.CTkLabel(
                center, text="My_AI", font=("Segoe UI", 44, "bold"),
                text_color=self.colors["text_primary"], fg_color="transparent",
            )
        else:
            title_lbl = tk.Label(
                center, text="My_AI", font=("Segoe UI", 44, "bold"),
                fg=self.colors["text_primary"], bg=self.colors["bg_primary"],
            )
        title_lbl.grid(row=1, column=0, pady=(0, 28))

        # ── Zone de saisie intégrée à l'écran d'accueil ────────────────────────
        # input_wrapper : bordure grise arrondie
        input_wrapper = self.create_frame(center, fg_color=self.colors["border"], corner_radius=8)
        input_wrapper.grid(row=2, column=0, sticky="ew", pady=(0, 6))
        input_wrapper.grid_columnconfigure(0, weight=1)
        self._home_input_wrapper = input_wrapper  # référence pour le drag & drop

        # content_frame (r=8, fg=input_bg) : auto-détecte bg_color=border → ses coins
        # affichent la couleur de bordure avec un arc → coins intérieurs arrondis visibles.
        # Les widgets enfants (r=0, padx=3) démarrent à (3,3) dans l'arc → pas de conflit.
        content_frame = self.create_frame(
            input_wrapper, fg_color=self.colors["input_bg"], corner_radius=8
        )
        content_frame.grid(row=0, column=0, sticky="ew", padx=3, pady=3)
        content_frame.grid_columnconfigure(0, weight=1)

        if self.use_ctk:
            self._home_input = _ctk.CTkTextbox(
                content_frame,
                height=60,
                width=600,
                fg_color=self.colors["input_bg"],
                text_color=self.colors["text_primary"],
                border_width=0,
                corner_radius=0,
                font=("Segoe UI", self.get_current_font_size("message")),
            )
        else:
            self._home_input = tk.Text(
                content_frame,
                height=3, width=60,
                bg=self.colors["input_bg"],
                fg=self.colors["text_primary"],
                font=("Segoe UI", self.get_current_font_size("message")),
                border=0, relief="flat", wrap=tk.WORD,
            )
        # Zone d'aperçu des documents attachés (en haut du rectangle)
        self._home_preview_frame = self.create_frame(
            content_frame, fg_color=self.colors["input_bg"], corner_radius=0
        )
        self._home_preview_frame.grid(row=0, column=0, sticky="ew", padx=6, pady=(6, 0))
        self._home_preview_frame.grid_remove()

        self._home_input.grid(row=1, column=0, sticky="ew", padx=3, pady=(3, 0))

        # Placeholder manuel dans home input
        _placeholder = "Tapez votre message..."
        _ph_color = self.colors.get("placeholder", "#6b7280")
        _ph_active = [True]

        def _show_ph():
            try:
                self._home_input.delete("1.0", "end")
                self._home_input.insert("1.0", _placeholder)
                if self.use_ctk:
                    self._home_input.configure(text_color=_ph_color)
                else:
                    self._home_input.configure(fg=_ph_color)
                _ph_active[0] = True
            except Exception:
                pass

        def _hide_ph(_event=None):
            if _ph_active[0]:
                try:
                    self._home_input.delete("1.0", "end")
                    if self.use_ctk:
                        self._home_input.configure(text_color=self.colors["text_primary"])
                    else:
                        self._home_input.configure(fg=self.colors["text_primary"])
                    _ph_active[0] = False
                except Exception:
                    pass

        def _on_focus_out(_event=None):
            try:
                content = self._home_input.get("1.0", "end-1c").strip()
                if not content:
                    _show_ph()
            except Exception:
                pass

        def _on_home_enter(_event=None):
            self._home_screen_send(_ph_active)
            return "break"

        _show_ph()
        self._home_input.bind("<FocusIn>", _hide_ph)
        self._home_input.bind("<FocusOut>", _on_focus_out)
        self._home_input.bind("<Return>", _on_home_enter)
        self._home_input.bind("<Shift-Return>", lambda e: None)
        self._home_input.bind("<Control-v>", self._on_paste)

        # ── Barre de boutons — row=2 (après preview row=0 et input row=1) ──
        buttons_row = self.create_frame(content_frame, fg_color=self.colors["input_bg"], corner_radius=0)
        buttons_row.grid(row=2, column=0, sticky="ew", padx=3, pady=(0, 3))
        buttons_row.grid_columnconfigure(1, weight=1)

        # ── Bouton "+" avec menu déroulant pour les fichiers ──────────────────
        _file_menu_entries = [
            ("📄  PDF",         self.load_pdf_file),
            ("📝  DOCX",        self.load_docx_file),
            ("📊  Excel / CSV", self.load_excel_file),
            ("💻  Code",        self.load_code_file),
            ("🖼  Image",        self.load_image_file),
        ]

        # Référence au popup courant pour éviter les doublons
        _popup_ref = [None]

        def _close_popup(popup):
            try:
                popup.destroy()
            except Exception:
                pass
            _popup_ref[0] = None

        def _open_file_menu():
            """Affiche un menu Toplevel sans bordure système à droite du bouton '+'."""
            # Fermer l'éventuel popup précédent
            if _popup_ref[0] is not None:
                _close_popup(_popup_ref[0])
                return

            bg = self.colors.get("bg_secondary", "#1e1e1e")
            fg = self.colors.get("text_primary", "#ffffff")
            accent = self.colors.get("accent", "#ff6b47")
            font = ("Segoe UI", 11)

            popup = tk.Toplevel(self.root)
            popup.overrideredirect(True)          # Supprime la décoration OS
            popup.configure(bg=bg)
            popup.attributes("-topmost", True)

            _popup_ref[0] = popup

            # Créer un bouton par entrée
            for i, (_lbl, _cmd) in enumerate(_file_menu_entries):
                def _make_cb(cmd, pop=popup):
                    def _cb():
                        _close_popup(pop)
                        cmd()
                    return _cb

                btn = tk.Label(
                    popup,
                    text=_lbl,
                    bg=bg,
                    fg=fg,
                    font=font,
                    anchor="w",
                    padx=14,
                    pady=7,
                    cursor="hand2",
                )
                btn.grid(row=i, column=0, sticky="ew")
                popup.grid_columnconfigure(0, weight=1)

                cb = _make_cb(_cmd)
                btn.bind("<Button-1>", lambda e, c=cb: c())
                btn.bind("<Enter>", lambda e, b=btn: b.configure(bg=accent, fg="#ffffff"))
                btn.bind("<Leave>", lambda e, b=btn: b.configure(bg=bg, fg=fg))

            # Positionner à droite du bouton "+"
            popup.update_idletasks()
            bx = _plus_btn.winfo_rootx() + _plus_btn.winfo_width() + 2
            by = _plus_btn.winfo_rooty()
            popup.geometry(f"+{bx}+{by}")

            # Fermer si on clique ailleurs
            def _on_focus_out(_):
                # Vérifier que le focus ne va pas vers le popup lui-même
                self.root.after(50, lambda: _close_popup(popup) if _popup_ref[0] is popup else None)

            popup.bind("<FocusOut>", _on_focus_out)
            popup.bind("<Escape>", lambda e: _close_popup(popup))
            self.root.bind("<Button-1>", lambda e: _close_popup(popup) if _popup_ref[0] is popup else None, add="+")
            popup.focus_set()

        if self.use_ctk:
            _plus_btn = _ctk.CTkButton(
                buttons_row,
                text="＋",
                command=_open_file_menu,
                fg_color=self.colors.get("bg_secondary", "#2a2a2a"),
                hover_color=self.colors.get("button_hover", "#3a3a3a"),
                text_color=self.colors.get("text_secondary", "#aaaaaa"),
                font=("Segoe UI", 18),
                corner_radius=6,
                width=42,
                height=32,
            )
        else:
            _plus_btn = tk.Button(
                buttons_row,
                text="＋",
                command=_open_file_menu,
                bg=self.colors.get("bg_secondary", "#2a2a2a"),
                fg=self.colors.get("text_secondary", "#aaaaaa"),
                font=("Segoe UI", 18),
                relief="flat",
                bd=0,
                padx=8,
            )
        _plus_btn.grid(row=0, column=0, sticky="w", padx=(6, 0), pady=4)

        # Bouton Envoyer à droite
        _send_btn = self.create_modern_button(
            buttons_row,
            text="Envoyer ↗",
            command=lambda: self._home_screen_send(_ph_active),
            style="primary",
        )
        if self.use_ctk:
            _send_btn.configure(width=110)
        _send_btn.grid(row=0, column=2, sticky="e", padx=(0, 6), pady=4)

        # Mettre le focus sur le home input après affichage
        self.root.after(150, self._focus_home_input)

        self._home_screen_active = True
        self._update_header_buttons_visibility()

    def _focus_home_input(self):
        """Met le focus sur le home input si disponible."""
        try:
            if self._home_input and self._home_input.winfo_exists():
                self._home_input.focus_set()
        except Exception:
            pass

    def _home_screen_send(self, _ph_active_ref=None):
        """Envoie le message tapé dans l'écran d'accueil."""
        if not getattr(self, "_home_input", None):
            return
        try:
            text = self._home_input.get("1.0", "end-1c").strip()
        except Exception:
            return
        if not text or text == "Tapez votre message...":
            return

        # 1. Fermer l'écran d'accueil et restaurer le layout
        self._dismiss_home_screen()

        # 2. Injecter le texte dans le vrai champ de saisie
        try:
            self.input_text.configure(state="normal")
            self.input_text.delete("1.0", "end")
            self.input_text.insert("1.0", text)
            self.placeholder_active = False
        except Exception:
            return

        # 3. Envoyer le message après que le mainloop ait traité les changements de layout
        self.root.after(50, self.send_message)

    def _dismiss_home_screen(self):
        """Cache l'écran d'accueil et restaure la zone de conversation."""
        if not getattr(self, "_home_screen_active", False):
            return

        # Sauvegarder les fichiers en attente (widgets seront détruits avec home)
        pending_files_backup = [
            (p, t) for p, t, _w in getattr(self, "_pending_files", [])
        ]
        self._pending_files = []

        self._home_screen_active = False
        self._home_input = None
        self._home_preview_frame = None

        # Supprimer l'overlay
        home = getattr(self, "_home_screen", None)
        if home is not None:
            try:
                home.destroy()
            except Exception:
                pass
            self._home_screen = None

        # Restaurer l'input réel
        input_c = getattr(self, "_input_container", None)
        if input_c is not None:
            try:
                input_c.grid()
            except Exception:
                pass

        # Restaurer la zone de conversation
        conv = getattr(self, "_conv_container", None)
        if conv is not None:
            try:
                conv.grid()
            except Exception:
                pass

        # Réafficher les boutons Clear Chat / Aide maintenant que l'accueil est fermé
        self._update_header_buttons_visibility()

        # Re-créer les aperçus dans la zone de saisie principale
        if pending_files_backup and hasattr(self, "add_file_preview"):
            for fpath, ftype in pending_files_backup:
                try:
                    self.add_file_preview(fpath, ftype)
                except Exception:
                    pass

    def show_help(self):
        """Affiche l'aide"""
        help_text = """**🆘 Aide - My Personal AI**

**📝 Comment utiliser :**
• Tapez votre message et appuyez sur Entrée
• Utilisez Shift+Entrée pour un saut de ligne
• Utilisez les boutons pour des actions rapides

**💬 Exemples de messages :**
• "Bonjour" - Salutation
• "Résume ce document" - Analyse de fichier
• "Génère une fonction Python" - Création de code
• "Cherche sur internet les actualités IA" - Recherche web

**🔧 Raccourcis :**
• Entrée : Envoyer le message
• Shift+Entrée : Nouvelle ligne
• Ctrl+L : Effacer la conversation"""

        self.add_message_bubble(help_text, is_user=False)

    def initialize_ai_async(self):
        """Version CORRIGÉE sans ai_status_var"""

        def init_ai():
            try:
                print("🔍 DEBUG: Initialisation de l'IA en cours...")

                if not hasattr(self, "ai_engine"):
                    print("❌ ERROR: ai_engine n'existe pas!")
                    return

                print(f"🔍 DEBUG: ai_engine type: {type(self.ai_engine)}")

                # Tester l'initialisation
                success = self.ai_engine.initialize_llm()
                print(f"🔍 DEBUG: initialize_llm résultat: {success}")

                if success:
                    print("✅ DEBUG: IA initialisée avec succès")

                    # Test de génération de réponse
                    try:
                        test_response = self.ai_engine.process_text("test")
                        print(f"🔍 DEBUG: Test réponse: {test_response[:100]}...")
                    except (ValueError, AttributeError) as e:
                        print(f"⚠️ DEBUG: Erreur test réponse: {e}")
                else:
                    print("❌ DEBUG: Échec de l'initialisation")

            except (ImportError, AttributeError) as e:
                print(f"❌ ERROR: Erreur dans init_ai: {e}")
                traceback.print_exc()

        print("🔍 DEBUG: Lancement du thread d'initialisation IA")
        threading.Thread(target=init_ai, daemon=True).start()

    def on_closing(self):
        """Gère la fermeture propre de l'application"""
        print("🛑 Fermeture de l'application...")
        try:
            # Arrêter les animations en cours
            self.is_thinking = False
            self.is_searching = False
            self._typing_interrupted = True

            # Détruire la fenêtre
            self.root.destroy()
        except tk.TclError as e:
            print(f"⚠️ Erreur lors de la fermeture: {e}")
        finally:
            # Forcer l'arrêt du programme
            os._exit(0)

    def run(self):
        """Lance l'interface"""
        try:
            self.logger.info("Démarrage de l'interface graphique moderne")
            self.root.mainloop()
        except KeyboardInterrupt:
            self.logger.info("Arrêt de l'interface par l'utilisateur")
        except Exception as e:
            self.logger.error("Erreur dans l'interface: %s", e)
            messagebox.showerror("Erreur", f"Erreur dans l'interface: {e}")
