"""
Interface Graphique Moderne - My AI Personal Assistant
Inspirée de l'interface Claude avec animations et design moderne
"""

import asyncio
import json
import keyword
import os
import platform
import random
import re
import sys
import threading
import tkinter as tk
import traceback
import webbrowser
import shutil
from pathlib import Path
from datetime import datetime
from tkinter import filedialog, messagebox, ttk

from tkinterdnd2 import DND_FILES, TkinterDnD

try:
    from pygments import lex
    from pygments.lexers.python import PythonLexer

    PYGMENTS_AVAILABLE = True
except ImportError:
    PYGMENTS_AVAILABLE = False
    PythonLexer = None

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import du modèle CustomAI unifié avec support 1M tokens
try:
    from models.custom_ai_model import CustomAIModel

    ULTRA_1M_AVAILABLE = True
    print("🚀 Modèle CustomAI unifié avec système 1M tokens intégré !")
except ImportError:
    ULTRA_1M_AVAILABLE = False
    print("📝 Interface moderne en mode standard")

# Import CustomTkinter ou fallback vers tkinter
try:
    import customtkinter as ctk

    CTK_AVAILABLE = True
except ImportError:
    CTK_AVAILABLE = False
    # CustomTkinter non disponible, utilisation de tkinter standard
    ctk = tk  # Fallback vers tkinter standard (déjà importé ligne 17)

# TkinterDnD2 déjà importé ligne 24
DND_AVAILABLE = True

# Import des styles (uniquement ce qui est utilisé)
try:
    from interfaces.modern_styles import (
        FONT_CONFIG,
        FONT_SIZES,
        MODERN_COLORS,
        RESPONSIVE_BREAKPOINTS,
    )
except ImportError:
    # Fallback colors si le fichier de styles n'est pas disponible
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

# Import core et utils avec fallback path si nécessaire
try:
    from core.ai_engine import AIEngine
    from core.config import Config
    from interfaces.agents_interface import AgentsInterface
    from utils.file_processor import FileProcessor
    from utils.logger import setup_logger
except ImportError:
    # Fallback for direct execution - add parent to path then reimport
    parent_dir = Path(__file__).parent.parent
    sys.path.insert(0, str(parent_dir))

    from core.ai_engine import AIEngine
    from core.config import Config
    from utils.file_processor import FileProcessor
    from utils.logger import setup_logger
    from interfaces.agents_interface import AgentsInterface


class ModernAIGUI:
    """GUI Moderne"""

    def adjust_text_widget_height(self, text_widget):
        """⚡ OPTIMISÉ : Hauteur illimitée avec moins d'update_idletasks"""
        try:
            # ⚡ OPTIMISATION: Un seul update_idletasks au lieu de 2
            current_state = text_widget.cget("state")
            text_widget.configure(state="normal")

            # ⚡ CORRECTION MAJEURE : Compter les lignes VISUELLES (avec wrapping), pas juste les \n
            display_lines = text_widget.count("1.0", "end", "displaylines")

            if display_lines and len(display_lines) > 0:
                line_count = display_lines[0]  # count() retourne un tuple
            else:
                # Fallback si displaylines échoue
                line_count = int(text_widget.index("end-1c").split(".")[0])

            # ⚡ HAUTEUR GÉNÉREUSE : Toujours assez pour tout afficher
            generous_height = max(line_count + 3, 10)  # Au moins 10 lignes, +3 de marge

            text_widget.configure(height=generous_height, state=current_state)
            # ⚡ OPTIMISATION: update_idletasks() uniquement tous les 5 ajustements
            self._height_adjust_counter += 1
            if self._height_adjust_counter % 5 == 0:
                text_widget.update_idletasks()

        except Exception:
            # Fallback sécurisé : laisser la hauteur par défaut
            try:
                self._disable_text_scroll(text_widget)
            except Exception:
                pass

    def _get_parent_canvas(self):
        """
        Récupère le canvas parent pour CustomTkinter ScrollableFrame.
        Accès à un attribut protégé nécessaire pour le scrolling.
        """
        # pylint: disable=protected-access
        if (
            self.use_ctk
            and hasattr(self, "chat_frame")
            and hasattr(self.chat_frame, "_parent_canvas")
        ):
            return self.chat_frame._parent_canvas
        return None

    def _disable_text_scroll(self, text_widget):
        """Désactive complètement le scroll interne du widget Text"""

        def block_scroll(_event):
            return "break"

        # Désactiver tous les événements de scroll
        scroll_events = [
            "<MouseWheel>",
            "<Button-4>",
            "<Button-5>",  # Molette souris
            "<Up>",
            "<Down>",  # Flèches haut/bas
            "<Prior>",
            "<Next>",  # Page Up/Down
            "<Control-Home>",
            "<Control-End>",  # Ctrl+Home/End
            "<Shift-MouseWheel>",  # Shift+molette
            "<Control-MouseWheel>",  # Ctrl+molette
        ]

        for event in scroll_events:
            text_widget.bind(event, block_scroll)

        # Transférer le scroll vers le conteneur principal
        def forward_to_main_scroll(event):
            try:
                if hasattr(self, "chat_frame"):
                    canvas = self._get_parent_canvas()
                    if canvas:
                        if hasattr(event, "delta") and event.delta:
                            scroll_delta = -1 * (event.delta // 120)
                        else:
                            scroll_delta = -1 if event.num == 4 else 1
                        canvas.yview_scroll(scroll_delta, "units")
                    else:
                        parent = self.chat_frame.master
                        while parent and not hasattr(parent, "yview_scroll"):
                            parent = parent.master
                        if parent:
                            if hasattr(event, "delta") and event.delta:
                                scroll_delta = -1 * (event.delta // 120)
                            else:
                                scroll_delta = -1 if event.num == 4 else 1
                            parent.yview_scroll(scroll_delta, "units")
            except Exception:
                pass
            return "break"

        # Appliquer le transfert de scroll uniquement pour la molette
        text_widget.bind("<MouseWheel>", forward_to_main_scroll)
        text_widget.bind("<Button-4>", forward_to_main_scroll)
        text_widget.bind("<Button-5>", forward_to_main_scroll)

    def _reactivate_text_scroll(self, text_widget):
        """Réactive le scroll après l'animation"""
        try:
            # Supprimer tous les bindings de blocage
            scroll_events = [
                "<MouseWheel>",
                "<Button-4>",
                "<Button-5>",
                "<Up>",
                "<Down>",
                "<Prior>",
                "<Next>",
                "<Control-Home>",
                "<Control-End>",
                "<Shift-MouseWheel>",
            ]

            for event in scroll_events:
                try:
                    text_widget.unbind(event)
                except Exception:
                    pass

            # Réactiver le scroll normal via le système de forwarding
            self.setup_improved_scroll_forwarding(text_widget)

        except Exception as e:
            print(f"[DEBUG] Erreur réactivation scroll: {e}")

    def _cleanup_old_messages(self):
        """⚡ OPTIMISATION MÉMOIRE: Supprime les vieux messages pour limiter l'usage mémoire"""
        try:
            if len(self._message_widgets) > self.max_displayed_messages:
                # Calculer combien supprimer (garder les max_displayed_messages derniers)
                num_to_remove = len(self._message_widgets) - self.max_displayed_messages

                # Supprimer les vieux widgets
                for i in range(num_to_remove):
                    widget = self._message_widgets[i]
                    if widget and widget.winfo_exists():
                        widget.destroy()

                # Mettre à jour la liste
                self._message_widgets = self._message_widgets[num_to_remove:]

                # Aussi nettoyer l'historique de conversation dans l'UI
                if len(self.conversation_history) > self.max_displayed_messages:
                    self.conversation_history = self.conversation_history[-self.max_displayed_messages:]

                print(f"🧹 [MEMORY] Nettoyé {num_to_remove} vieux messages pour optimiser la mémoire")

        except Exception as e:
            print(f"⚠️ [MEMORY] Erreur nettoyage messages: {e}")

    def _show_timestamp_for_current_message(self):
        """Affiche le timestamp sous la bulle du dernier message IA (comme pour l'utilisateur)."""
        if (
            hasattr(self, "current_message_container")
            and self.current_message_container is not None
        ):
            # Vérifier qu'il n'y a pas déjà un timestamp (évite doublons)
            for child in self.current_message_container.winfo_children():
                if isinstance(child, (tk.Label,)):
                    if getattr(child, "is_timestamp", False):
                        return  # Déjà affiché
            timestamp = datetime.now().strftime("%H:%M")
            time_label = self.create_label(
                self.current_message_container,
                text=timestamp,
                font=("Segoe UI", 10),
                fg_color=self.colors["bg_chat"],
                text_color="#b3b3b3",
            )
            time_label.grid(row=1, column=0, sticky="w", padx=8, pady=(0, 6))
            time_label.is_timestamp = True
        # Sinon, rien à faire (pas de container)

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
                except Exception:
                    pass
                if enabled:
                    self.root.after(100, self._safe_focus_input)
                else:
                    # Sauvegarder le contenu avant de désactiver
                    try:
                        self._saved_input_content = self.input_text.get("1.0", "end-1c")
                    except Exception:
                        self._saved_input_content = ""
            # Boutons PDF, DOCX, Code
            for btn_name in ["pdf_btn", "docx_btn", "code_btn"]:
                if hasattr(self, btn_name):
                    btn = getattr(self, btn_name)
                    try:
                        btn.configure(state="normal" if enabled else "disabled")
                    except Exception:
                        pass
            # Boutons Clear Chat et Aide
            for btn_name in ["clear_btn", "help_btn"]:
                if hasattr(self, btn_name):
                    btn = getattr(self, btn_name)
                    try:
                        btn.configure(state="normal" if enabled else "disabled")
                    except Exception:
                        pass
            # Bouton d'envoi :
            if hasattr(self, "send_button"):
                if enabled:
                    self._set_send_button_normal()
                else:
                    self._set_send_button_stop()
        except Exception:
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
        except Exception:
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
        except Exception:
            pass

    def interrupt_ai(self):
        """Interrompt l'IA : stop écriture, recherche, réflexion, etc."""
        try:
            print(
                "🛑 [GUI] STOP cliqué - Interruption de toutes les opérations en cours"
            )
            self.is_interrupted = True
            if hasattr(self, "current_request_id"):
                self.current_request_id += 1  # Invalide toutes les requêtes en cours
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
        except Exception:
            pass

    def _safe_focus_input(self):
        """Met le focus sur l'input de manière sécurisée"""
        try:
            if hasattr(self, "input_text"):
                current_state = self.input_text.cget("state")
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
        except Exception:
            pass

    def __init__(self):
        """Initialise l'interface moderne avec système 1M tokens"""
        self.is_interrupted = False  # Pour interruption robuste
        self.logger = setup_logger("modern_ai_gui")
        # AIEngine principal pour toute l'interface
        self.config = Config()
        self.ai_engine = AIEngine(self.config)

        # Initialisation avec CustomAI unifié (avec support 1M tokens)
        if ULTRA_1M_AVAILABLE:
            print("🚀 Interface moderne avec modèle CustomAI unifié !")
            try:
                # Utiliser CustomAIModel avec support 1M tokens intégré
                self.custom_ai = CustomAIModel()

                # 🔗 IMPORTANT: Partager la même ConversationMemory ET le même LocalLLM
                if hasattr(self.ai_engine, "local_ai"):
                    print(
                        "🔗 Synchronisation des mémoires de conversation et LocalLLM..."
                    )

                    # Partager la ConversationMemory
                    if hasattr(self.ai_engine.local_ai, "conversation_memory"):
                        self.ai_engine.local_ai.conversation_memory = (
                            self.custom_ai.conversation_memory
                        )

                    # ⚡ CRUCIAL: Partager le MÊME LocalLLM pour avoir le MÊME historique
                    if hasattr(self.ai_engine.local_ai, "local_llm"):
                        print(
                            "🔗 Partage du même LocalLLM entre AIEngine et CustomAI..."
                        )
                        self.custom_ai.local_llm = self.ai_engine.local_ai.local_llm
                        print(
                            f"✅ LocalLLM partagé - Historique: {len(self.custom_ai.local_llm.conversation_history)} messages"
                        )

                    print("✅ Mémoires et LocalLLM synchronisés")

                # Afficher les stats initiales
                stats = self.custom_ai.get_context_stats()
                print(
                    f"📊 Contexte initial: {stats.get('context_size', 0):,} / {stats.get('max_context_length', 1000000):,} tokens"
                )
                print(
                    f"📚 Documents: {len(self.custom_ai.conversation_memory.stored_documents)}"
                )
                print(
                    f"🧠 Mode: {'Ultra 1M' if self.custom_ai.ultra_mode else 'Classique'}"
                )
            except Exception as e:
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
        self._streaming_complete = False  # Flag indiquant si le streaming est terminé
        self._streaming_mode = False  # Mode streaming actif
        self._streaming_widget = None  # Widget texte du streaming
        self._streaming_container = None  # Container du message streaming
        self._streaming_bubble_created = False  # Bulle déjà créée

        # Buttons for file actions
        self.pdf_btn = None
        self.docx_btn = None
        self.code_btn = None

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

        # Configuration de l'interface
        self.setup_modern_gui()
        self.create_modern_layout()
        self.setup_keyboard_shortcuts()
        self.show_welcome_message()

        # Initialisation IA en arrière-plan
        self.initialize_ai_async()
        self.ensure_input_is_ready()

    def _configure_formatting_tags(self, text_widget):
        """Configure tous les tags de formatage pour l'animation avec coloration Python COMPLÈTE"""
        base_font = ("Segoe UI", 12)

        # 🔧 CONFIGURATION IDENTIQUE à insert_formatted_text_tkinter
        text_widget.tag_configure(
            "bold",
            font=("Segoe UI", 12, "bold"),
            foreground=self.colors["text_primary"],
        )

        # 🔧 TITRES MARKDOWN avec tailles progressives
        text_widget.tag_configure(
            "title1",
            font=("Segoe UI", 16, "bold"),
            foreground=self.colors["text_primary"],
        )
        text_widget.tag_configure(
            "title2",
            font=("Segoe UI", 14, "bold"),
            foreground=self.colors["text_primary"],
        )
        text_widget.tag_configure(
            "title3",
            font=("Segoe UI", 13, "bold"),
            foreground=self.colors["text_primary"],
        )
        text_widget.tag_configure(
            "title4",
            font=("Segoe UI", 12, "bold"),
            foreground=self.colors["text_primary"],
        )
        text_widget.tag_configure(
            "title5",
            font=("Segoe UI", 12, "bold"),
            foreground=self.colors["text_primary"],
        )

        text_widget.tag_configure(
            "italic",
            font=("Segoe UI", 12, "italic"),
            foreground=self.colors["text_primary"],
        )
        text_widget.tag_configure("mono", font=("Consolas", 11), foreground="#f8f8f2")

        # 🔧 DOCSTRING - ESSENTIEL pour le code Python
        text_widget.tag_configure(
            "docstring", font=("Consolas", 11, "italic"), foreground="#ff8c00"
        )

        text_widget.tag_configure(
            "normal", font=base_font, foreground=self.colors["text_primary"]
        )
        text_widget.tag_configure(
            "link", foreground="#3b82f6", underline=1, font=base_font
        )

        # Tag pour placeholder de code
        text_widget.tag_configure(
            "code_placeholder", font=base_font, foreground=self.colors["text_primary"]
        )

        # 🔧 PYTHON COMPLET - Couleurs VS Code EXACTES

        # Keywords - BLEU VS Code
        python_keyword_tags = [
            "Token.Keyword",
            "Token.Keyword.Constant",
            "Token.Keyword.Declaration",
            "Token.Keyword.Namespace",
            "Token.Keyword.Pseudo",
            "Token.Keyword.Reserved",
        ]
        for tag in python_keyword_tags:
            text_widget.tag_configure(
                tag, foreground="#569cd6", font=("Consolas", 11, "bold")
            )

        text_widget.tag_configure(
            "Token.Keyword.Type", foreground="#4ec9b0", font=("Consolas", 11, "bold")
        )

        # Strings - ORANGE-BRUN VS Code
        string_tags = [
            "Token.Literal.String",
            "Token.Literal.String.Double",
            "Token.Literal.String.Single",
            "Token.String",
            "Token.String.Double",
            "Token.String.Single",
        ]
        for tag in string_tags:
            text_widget.tag_configure(tag, foreground="#ce9178", font=("Consolas", 11))

        # Commentaires - VERT VS Code
        comment_tags = [
            "Token.Comment",
            "Token.Comment.Single",
            "Token.Comment.Multiline",
        ]
        for tag in comment_tags:
            text_widget.tag_configure(
                tag, foreground="#6a9955", font=("Consolas", 11, "italic")
            )

        # Fonctions et classes - JAUNE VS Code
        text_widget.tag_configure(
            "Token.Name.Function", foreground="#dcdcaa", font=("Consolas", 11)
        )
        text_widget.tag_configure(
            "Token.Name.Function.Magic", foreground="#dcdcaa", font=("Consolas", 11)
        )
        text_widget.tag_configure(
            "Token.Name.Class", foreground="#4ec9b0", font=("Consolas", 11, "bold")
        )

        # Builtins - JAUNE VS Code
        text_widget.tag_configure(
            "Token.Name.Builtin", foreground="#dcdcaa", font=("Consolas", 11)
        )
        text_widget.tag_configure(
            "Token.Name.Builtin.Pseudo", foreground="#dcdcaa", font=("Consolas", 11)
        )

        # Nombres - VERT CLAIR VS Code
        number_tags = [
            "Token.Literal.Number",
            "Token.Literal.Number.Integer",
            "Token.Literal.Number.Float",
            "Token.Number",
            "Token.Number.Integer",
            "Token.Number.Float",
        ]
        for tag in number_tags:
            text_widget.tag_configure(tag, foreground="#b5cea8", font=("Consolas", 11))

        # Opérateurs - BLANC VS Code
        text_widget.tag_configure(
            "Token.Operator", foreground="#d4d4d4", font=("Consolas", 11)
        )
        text_widget.tag_configure(
            "Token.Punctuation", foreground="#d4d4d4", font=("Consolas", 11)
        )

        # Variables et noms - BLEU CLAIR VS Code
        name_tags = ["Token.Name", "Token.Name.Variable", "Token.Name.Attribute"]
        for tag in name_tags:
            text_widget.tag_configure(tag, foreground="#9cdcfe", font=("Consolas", 11))

        # Constantes spéciales - BLEU VS Code
        text_widget.tag_configure(
            "Token.Name.Constant", foreground="#569cd6", font=("Consolas", 11, "bold")
        )

        # AJOUT : Tags pour les blocs de code
        text_widget.tag_configure(
            "code_block",
            font=("Consolas", 11),
            foreground="#d4d4d4",
        )

        # === JAVASCRIPT - Couleurs VS Code ===
        text_widget.tag_configure(
            "js_keyword", foreground="#569cd6", font=("Consolas", 11, "bold")
        )
        text_widget.tag_configure(
            "js_string", foreground="#ce9178", font=("Consolas", 11)
        )
        text_widget.tag_configure(
            "js_comment", foreground="#6a9955", font=("Consolas", 11, "italic")
        )
        text_widget.tag_configure(
            "js_number", foreground="#b5cea8", font=("Consolas", 11)
        )
        text_widget.tag_configure(
            "js_function", foreground="#dcdcaa", font=("Consolas", 11)
        )
        text_widget.tag_configure(
            "js_variable", foreground="#9cdcfe", font=("Consolas", 11)
        )
        text_widget.tag_configure(
            "js_operator", foreground="#d4d4d4", font=("Consolas", 11)
        )

        # === CSS - Couleurs VS Code ===
        text_widget.tag_configure(
            "css_selector", foreground="#d7ba7d", font=("Consolas", 11)
        )
        text_widget.tag_configure(
            "css_property", foreground="#9cdcfe", font=("Consolas", 11)
        )
        text_widget.tag_configure(
            "css_value", foreground="#ce9178", font=("Consolas", 11)
        )
        text_widget.tag_configure(
            "css_comment", foreground="#6a9955", font=("Consolas", 11, "italic")
        )
        text_widget.tag_configure(
            "css_unit", foreground="#b5cea8", font=("Consolas", 11)
        )

        # === HTML - Couleurs VS Code ===
        text_widget.tag_configure(
            "html_tag", foreground="#569cd6", font=("Consolas", 11)
        )
        text_widget.tag_configure(
            "html_attribute", foreground="#9cdcfe", font=("Consolas", 11)
        )
        text_widget.tag_configure(
            "html_value", foreground="#ce9178", font=("Consolas", 11)
        )
        text_widget.tag_configure(
            "html_comment", foreground="#6a9955", font=("Consolas", 11, "italic")
        )

        # === BASH - Couleurs VS Code ===
        text_widget.tag_configure(
            "bash_command", foreground="#dcdcaa", font=("Consolas", 11)
        )
        text_widget.tag_configure(
            "bash_keyword", foreground="#569cd6", font=("Consolas", 11, "bold")
        )
        text_widget.tag_configure(
            "bash_string", foreground="#ce9178", font=("Consolas", 11)
        )
        text_widget.tag_configure(
            "bash_comment", foreground="#6a9955", font=("Consolas", 11, "italic")
        )
        text_widget.tag_configure(
            "bash_variable", foreground="#9cdcfe", font=("Consolas", 11)
        )

        # === SQL - Couleurs VS Code ===
        text_widget.tag_configure(
            "sql_keyword", foreground="#569cd6", font=("Consolas", 11, "bold")
        )
        text_widget.tag_configure(
            "sql_function", foreground="#dcdcaa", font=("Consolas", 11)
        )
        text_widget.tag_configure(
            "sql_string", foreground="#ce9178", font=("Consolas", 11)
        )
        text_widget.tag_configure(
            "sql_comment", foreground="#6a9955", font=("Consolas", 11, "italic")
        )
        text_widget.tag_configure(
            "sql_number", foreground="#b5cea8", font=("Consolas", 11)
        )

        # === JAVA - Couleurs VS Code ===
        text_widget.tag_configure(
            "java_keyword", foreground="#569cd6", font=("Consolas", 11, "bold")
        )
        text_widget.tag_configure(
            "java_string", foreground="#ce9178", font=("Consolas", 11)
        )
        text_widget.tag_configure(
            "java_comment", foreground="#6a9955", font=("Consolas", 11, "italic")
        )
        text_widget.tag_configure(
            "java_number", foreground="#b5cea8", font=("Consolas", 11)
        )
        text_widget.tag_configure(
            "java_class", foreground="#4ec9b0", font=("Consolas", 11)
        )
        text_widget.tag_configure(
            "java_method", foreground="#dcdcaa", font=("Consolas", 11)
        )
        text_widget.tag_configure(
            "java_annotation", foreground="#dcdcaa", font=("Consolas", 11)
        )

        # === C/C++ - Couleurs VS Code ===
        text_widget.tag_configure(
            "cpp_keyword", foreground="#569cd6", font=("Consolas", 11, "bold")
        )
        text_widget.tag_configure(
            "cpp_string", foreground="#ce9178", font=("Consolas", 11)
        )
        text_widget.tag_configure(
            "cpp_comment", foreground="#6a9955", font=("Consolas", 11, "italic")
        )
        text_widget.tag_configure(
            "cpp_number", foreground="#b5cea8", font=("Consolas", 11)
        )
        text_widget.tag_configure(
            "cpp_preprocessor", foreground="#c586c0", font=("Consolas", 11)
        )
        text_widget.tag_configure(
            "cpp_type", foreground="#4ec9b0", font=("Consolas", 11)
        )
        text_widget.tag_configure(
            "cpp_function", foreground="#dcdcaa", font=("Consolas", 11)
        )

        # === C - Couleurs VS Code (mêmes couleurs que C++) ===
        text_widget.tag_configure(
            "c_keyword", foreground="#569cd6", font=("Consolas", 11, "bold")
        )
        text_widget.tag_configure(
            "c_string", foreground="#ce9178", font=("Consolas", 11)
        )
        text_widget.tag_configure(
            "c_comment", foreground="#6a9955", font=("Consolas", 11, "italic")
        )
        text_widget.tag_configure(
            "c_number", foreground="#b5cea8", font=("Consolas", 11)
        )
        text_widget.tag_configure(
            "c_preprocessor", foreground="#c586c0", font=("Consolas", 11)
        )
        text_widget.tag_configure("c_type", foreground="#4ec9b0", font=("Consolas", 11))
        text_widget.tag_configure(
            "c_function", foreground="#dcdcaa", font=("Consolas", 11)
        )

        # === C# - Couleurs VS Code ===
        text_widget.tag_configure(
            "csharp_keyword", foreground="#569cd6", font=("Consolas", 11, "bold")
        )
        text_widget.tag_configure(
            "csharp_string", foreground="#ce9178", font=("Consolas", 11)
        )
        text_widget.tag_configure(
            "csharp_comment", foreground="#6a9955", font=("Consolas", 11, "italic")
        )
        text_widget.tag_configure(
            "csharp_number", foreground="#b5cea8", font=("Consolas", 11)
        )
        text_widget.tag_configure(
            "csharp_class", foreground="#4ec9b0", font=("Consolas", 11)
        )
        text_widget.tag_configure(
            "csharp_method", foreground="#dcdcaa", font=("Consolas", 11)
        )

        # === Go - Couleurs VS Code ===
        text_widget.tag_configure(
            "go_keyword", foreground="#569cd6", font=("Consolas", 11, "bold")
        )
        text_widget.tag_configure(
            "go_string", foreground="#ce9178", font=("Consolas", 11)
        )
        text_widget.tag_configure(
            "go_comment", foreground="#6a9955", font=("Consolas", 11, "italic")
        )
        text_widget.tag_configure(
            "go_number", foreground="#b5cea8", font=("Consolas", 11)
        )
        text_widget.tag_configure(
            "go_type", foreground="#4ec9b0", font=("Consolas", 11)
        )
        text_widget.tag_configure(
            "go_function", foreground="#dcdcaa", font=("Consolas", 11)
        )
        text_widget.tag_configure(
            "go_package", foreground="#c586c0", font=("Consolas", 11)
        )

        # === Ruby - Couleurs VS Code ===
        text_widget.tag_configure(
            "ruby_keyword", foreground="#569cd6", font=("Consolas", 11, "bold")
        )
        text_widget.tag_configure(
            "ruby_string", foreground="#ce9178", font=("Consolas", 11)
        )
        text_widget.tag_configure(
            "ruby_comment", foreground="#6a9955", font=("Consolas", 11, "italic")
        )
        text_widget.tag_configure(
            "ruby_number", foreground="#b5cea8", font=("Consolas", 11)
        )
        text_widget.tag_configure(
            "ruby_symbol", foreground="#d7ba7d", font=("Consolas", 11)
        )
        text_widget.tag_configure(
            "ruby_method", foreground="#dcdcaa", font=("Consolas", 11)
        )
        text_widget.tag_configure(
            "ruby_class", foreground="#4ec9b0", font=("Consolas", 11)
        )
        text_widget.tag_configure(
            "ruby_variable", foreground="#9cdcfe", font=("Consolas", 11)
        )

        # === Swift - Couleurs VS Code ===
        text_widget.tag_configure(
            "swift_keyword", foreground="#569cd6", font=("Consolas", 11, "bold")
        )
        text_widget.tag_configure(
            "swift_string", foreground="#ce9178", font=("Consolas", 11)
        )
        text_widget.tag_configure(
            "swift_comment", foreground="#6a9955", font=("Consolas", 11, "italic")
        )
        text_widget.tag_configure(
            "swift_number", foreground="#b5cea8", font=("Consolas", 11)
        )
        text_widget.tag_configure(
            "swift_type", foreground="#4ec9b0", font=("Consolas", 11)
        )
        text_widget.tag_configure(
            "swift_function", foreground="#dcdcaa", font=("Consolas", 11)
        )
        text_widget.tag_configure(
            "swift_attribute", foreground="#c586c0", font=("Consolas", 11)
        )

        # === PHP - Couleurs VS Code ===
        text_widget.tag_configure(
            "php_keyword", foreground="#569cd6", font=("Consolas", 11, "bold")
        )
        text_widget.tag_configure(
            "php_string", foreground="#ce9178", font=("Consolas", 11)
        )
        text_widget.tag_configure(
            "php_comment", foreground="#6a9955", font=("Consolas", 11, "italic")
        )
        text_widget.tag_configure(
            "php_number", foreground="#b5cea8", font=("Consolas", 11)
        )
        text_widget.tag_configure(
            "php_variable", foreground="#9cdcfe", font=("Consolas", 11)
        )
        text_widget.tag_configure(
            "php_function", foreground="#dcdcaa", font=("Consolas", 11)
        )
        text_widget.tag_configure(
            "php_tag", foreground="#569cd6", font=("Consolas", 11)
        )

        # === Perl - Couleurs VS Code ===
        text_widget.tag_configure(
            "perl_keyword", foreground="#569cd6", font=("Consolas", 11, "bold")
        )
        text_widget.tag_configure(
            "perl_string", foreground="#ce9178", font=("Consolas", 11)
        )
        text_widget.tag_configure(
            "perl_comment", foreground="#6a9955", font=("Consolas", 11, "italic")
        )
        text_widget.tag_configure(
            "perl_number", foreground="#b5cea8", font=("Consolas", 11)
        )
        text_widget.tag_configure(
            "perl_variable", foreground="#9cdcfe", font=("Consolas", 11)
        )
        text_widget.tag_configure(
            "perl_regex", foreground="#d16969", font=("Consolas", 11)
        )

        # === Rust - Couleurs VS Code ===
        text_widget.tag_configure(
            "rust_keyword", foreground="#569cd6", font=("Consolas", 11, "bold")
        )
        text_widget.tag_configure(
            "rust_string", foreground="#ce9178", font=("Consolas", 11)
        )
        text_widget.tag_configure(
            "rust_comment", foreground="#6a9955", font=("Consolas", 11, "italic")
        )
        text_widget.tag_configure(
            "rust_number", foreground="#b5cea8", font=("Consolas", 11)
        )
        text_widget.tag_configure(
            "rust_type", foreground="#4ec9b0", font=("Consolas", 11)
        )
        text_widget.tag_configure(
            "rust_function", foreground="#dcdcaa", font=("Consolas", 11)
        )
        text_widget.tag_configure(
            "rust_macro", foreground="#c586c0", font=("Consolas", 11)
        )
        text_widget.tag_configure(
            "rust_lifetime", foreground="#569cd6", font=("Consolas", 11, "italic")
        )

        # === Dockerfile - Couleurs VS Code ===
        text_widget.tag_configure(
            "dockerfile_instruction", foreground="#569cd6", font=("Consolas", 11, "bold")
        )
        text_widget.tag_configure(
            "dockerfile_string", foreground="#ce9178", font=("Consolas", 11)
        )
        text_widget.tag_configure(
            "dockerfile_comment", foreground="#6a9955", font=("Consolas", 11, "italic")
        )

        # Tag caché pour les marqueurs ```
        text_widget.tag_configure("hidden", elide=True, font=("Consolas", 1))

        print(
            "✅ Tags de coloration Python/JS/TS/CSS/HTML/Bash/SQL/Java/C++/C/C#/Go/Ruby/Swift/PHP/Perl/Rust/Dockerfile configurés pour l'animation"
        )

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

    def setup_drag_drop(self):
        """Configure le drag & drop pour les fichiers"""
        if DND_AVAILABLE:
            self.root.drop_target_register(DND_FILES)
            self.root.dnd_bind("<<Drop>>", self.on_file_drop)

    def on_file_drop(self, event):
        """Gère le drop de fichiers"""
        files = self.root.tk.splitlist(event.data)
        for file_path in files:
            if os.path.isfile(file_path):
                self.process_dropped_file(file_path)
            else:
                self.show_notification(f"❌ Chemin invalide : {file_path}", "error")

    def process_dropped_file(self, file_path):
        """Traite un fichier glissé-déposé"""
        filename = os.path.basename(file_path)
        ext = os.path.splitext(filename)[1].lower()

        # Déterminer le type de fichier
        if ext == ".pdf":
            file_type = "PDF"
        elif ext in [".docx", ".doc"]:
            file_type = "DOCX"
        elif ext in [".py", ".js", ".html", ".css", ".json", ".xml", ".md", ".txt"]:
            file_type = "Code"
        else:
            self.show_notification(f"❌ **Format non supporté** : {ext}", "error")
            return

        # Ajouter message utilisateur
        self.add_message_bubble(f"📎 **Fichier glissé** : {filename}", is_user=True)

        # Traiter le fichier
        self.process_file(file_path, file_type)

    def show_notification(self, message, type_notif="info", duration=2000):
        """
        Affiche une notification temporaire améliorée

        Args:
            message: Message à afficher
            type_notif: Type de notification (info, success, error, warning)
            duration: Durée d'affichage en millisecondes
        """
        # Couleurs selon le type
        colors_map = {
            "error": "#ef4444",
            "success": "#10b981",
            "warning": "#f59e0b",
            "info": "#3b82f6",
        }

        bg_color = colors_map.get(type_notif, "#3b82f6")

        # Créer une notification en overlay
        if self.use_ctk:
            notif_frame = ctk.CTkFrame(
                self.main_container, fg_color=bg_color, corner_radius=8, border_width=0
            )

            notif_label = ctk.CTkLabel(
                notif_frame,
                text=message,
                text_color="#ffffff",
                font=("Segoe UI", self.get_current_font_size("message"), "bold"),
                fg_color="transparent",
            )
        else:
            notif_frame = tk.Frame(
                self.main_container, bg=bg_color, relief="flat", bd=0
            )

            notif_label = tk.Label(
                notif_frame,
                text=message,
                fg="#ffffff",
                bg=bg_color,
                font=("Segoe UI", self.get_current_font_size("message"), "bold"),
            )

        # Positionner en haut à droite
        notif_frame.place(relx=0.98, rely=0.02, anchor="ne")
        notif_label.pack(padx=15, pady=8)

        # Animation d'apparition (optionnelle)
        notif_frame.lift()  # Mettre au premier plan

        # Supprimer automatiquement après la durée spécifiée
        self.root.after(duration, notif_frame.destroy)

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

    def create_conversation_area(self):
        """Crée la zone de conversation principale"""
        # Container pour la conversation
        conv_container = self.create_frame(
            self.main_container, fg_color=self.colors["bg_chat"]
        )
        conv_container.grid(row=0, column=0, sticky="nsew", padx=20, pady=(10, 20))
        conv_container.grid_columnconfigure(0, weight=1)
        conv_container.grid_rowconfigure(0, weight=1)

        # Zone de scroll pour les messages
        if self.use_ctk:
            self.chat_frame = ctk.CTkScrollableFrame(
                conv_container,
                fg_color=self.colors["bg_chat"],
                scrollbar_fg_color=self.colors["bg_secondary"],
            )
        else:
            # Fallback avec Canvas et Scrollbar
            canvas = tk.Canvas(
                conv_container, fg_color=self.colors["bg_chat"], highlightthickness=0
            )
            scrollbar = ttk.Scrollbar(
                conv_container, orient="vertical", command=canvas.yview
            )
            self.chat_frame = tk.Frame(canvas, fg_color=self.colors["bg_chat"])

            canvas.configure(yscrollcommand=scrollbar.set)
            canvas.create_window((0, 0), window=self.chat_frame, anchor="nw")

            canvas.grid(row=0, column=0, sticky="nsew")
            scrollbar.grid(row=0, column=1, sticky="ns")

            # Mise à jour du scroll
            def configure_scroll(_event):
                canvas.configure(scrollregion=canvas.bbox("all"))

            self.chat_frame.bind("<Configure>", configure_scroll)

        self.chat_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        self.chat_frame.grid_columnconfigure(0, weight=1)

        # Zone d'animation de réflexion
        self.thinking_frame = self.create_frame(
            conv_container, fg_color=self.colors["bg_chat"]
        )
        self.thinking_frame.grid(row=1, column=0, sticky="ew", padx=20, pady=(0, 10))
        self.thinking_frame.grid_remove()  # Caché par défaut

        self.thinking_label = self.create_label(
            self.thinking_frame,
            text="",
            font=(
                "Segoe UI",
                self.get_current_font_size("message"),
            ),  # UNIFIÉ AVEC LES MESSAGES
            text_color=self.colors["text_secondary"],  # text_color au lieu de fg
            fg_color=self.colors["bg_chat"],
        )
        self.thinking_label.grid(row=0, column=0)

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

    def create_frame(self, parent, **kwargs):
        """Crée un frame avec le bon style"""
        if self.use_ctk:
            # Convertir les paramètres tkinter vers CustomTkinter
            ctk_kwargs = {}
            for key, value in kwargs.items():
                if key == "bg" or key == "fg_color":
                    ctk_kwargs["fg_color"] = value
                elif key == "fg":
                    ctk_kwargs["text_color"] = value
                elif key == "relief":
                    # CustomTkinter ne supporte pas relief, on l'ignore
                    continue
                elif key == "bd" or key == "borderwidth":
                    ctk_kwargs["border_width"] = value
                else:
                    ctk_kwargs[key] = value
            return ctk.CTkFrame(parent, **ctk_kwargs)
        else:
            return tk.Frame(parent, **kwargs)

    def create_label(self, parent, **kwargs):
        """Crée un label avec le bon style"""
        if self.use_ctk:
            # Convertir les paramètres tkinter vers CustomTkinter
            ctk_kwargs = {}
            for key, value in kwargs.items():
                if key == "bg":
                    ctk_kwargs["fg_color"] = value
                elif key == "fg":
                    ctk_kwargs["text_color"] = value
                elif key == "font":
                    ctk_kwargs["font"] = value
                elif key == "text":
                    ctk_kwargs["text"] = value
                elif key in ["relief", "bd", "borderwidth"]:
                    # CustomTkinter ne supporte pas ces paramètres
                    continue
                else:
                    ctk_kwargs[key] = value
            return ctk.CTkLabel(parent, **ctk_kwargs)
        else:
            return tk.Label(parent, **kwargs)

    def create_button(self, parent, text, command, style="primary", **_kwargs):
        """Crée un bouton (alias vers create_modern_button pour compatibilité)"""
        return self.create_modern_button(parent, text, command, style)

    def create_text(self, parent, **kwargs):
        """Crée un widget Text avec le bon style"""
        if self.use_ctk:
            # Convertir les paramètres tkinter vers CustomTkinter
            ctk_kwargs = {}
            for key, value in kwargs.items():
                if key == "bg":
                    ctk_kwargs["fg_color"] = value
                elif key == "fg":
                    ctk_kwargs["text_color"] = value
                elif key == "font":
                    ctk_kwargs["font"] = value
                elif key == "wrap":
                    ctk_kwargs["wrap"] = value
                elif key in ["relief", "bd", "borderwidth"]:
                    # CustomTkinter ne supporte pas ces paramètres
                    continue
                else:
                    ctk_kwargs[key] = value
            return ctk.CTkTextbox(parent, **ctk_kwargs)
        else:
            return tk.Text(parent, **kwargs)

    def create_modern_button(self, parent, text, command, style="primary"):
        """Crée un bouton moderne avec différents styles"""
        # Initialisation des valeurs par défaut
        bg_color = self.colors["accent"]
        hover_color = "#ff5730"
        text_color = "#ffffff"

        if style == "primary":
            bg_color = self.colors["accent"]
            hover_color = "#ff5730"
            text_color = "#ffffff"
        elif style == "secondary":
            bg_color = self.colors["bg_secondary"]
            hover_color = self.colors["button_hover"]
            text_color = self.colors["text_primary"]
        elif style == "file":
            bg_color = self.colors["bg_secondary"]
            hover_color = self.colors["button_hover"]
            text_color = self.colors["text_secondary"]

        if self.use_ctk:
            return ctk.CTkButton(
                parent,
                text=text,
                command=command,
                fg_color=bg_color,
                hover_color=hover_color,
                text_color=text_color,
                font=(
                    "Segoe UI",
                    self.get_current_font_size("message"),
                ),  # UNIFIÉ AVEC LES MESSAGES
                corner_radius=6,
                height=32,
            )
        else:
            btn = tk.Button(
                parent,
                text=text,
                command=command,
                bg=bg_color,
                fg=text_color,
                font=(
                    "Segoe UI",
                    self.get_current_font_size("message"),
                ),  # UNIFIÉ AVEC LES MESSAGES
                border=0,
                relief="flat",
            )

            # Effet hover pour tkinter standard
            def on_enter(_e):
                btn.configure(bg=hover_color)

            def on_leave(_e):
                btn.configure(bg=bg_color)

            btn.bind("<Enter>", on_enter)
            btn.bind("<Leave>", on_leave)

            return btn

    def add_message_bubble(self, text, is_user=True, message_type="text"):
        """Version FINALE avec animation de frappe pour les messages IA"""
        # Vérifier que le texte est une chaîne
        if not isinstance(text, str):
            if isinstance(text, dict):
                text = (
                    text.get("response")
                    or text.get("text")
                    or text.get("content")
                    or text.get("message")
                    or str(text)
                )
            else:
                text = str(text)

        # Ajouter à l'historique
        self.conversation_history.append(
            {
                "text": text,
                "is_user": is_user,
                "timestamp": datetime.now(),
                "type": message_type,
            }
        )

        # Container principal avec espacement OPTIMAL
        msg_container = self.create_frame(
            self.chat_frame, fg_color=self.colors["bg_chat"]
        )
        msg_container.grid(
            row=len(self.conversation_history) - 1, column=0, sticky="ew", pady=(0, 12)
        )
        msg_container.grid_columnconfigure(0, weight=1)

        # ⚡ OPTIMISATION: Tracker ce widget pour nettoyage ultérieur
        self._message_widgets.append(msg_container)

        # ⚡ OPTIMISATION MÉMOIRE: Nettoyer les vieux messages si trop nombreux
        self._cleanup_old_messages()

        if is_user:
            self.create_user_message_bubble(msg_container, text)
            # Scroll utilisateur : scroller uniquement si le bas n'est pas visible
            self.root.after(50, self._scroll_if_needed_user())
        else:
            # Crée la bulle IA mais insère le texte vide, puis lance l'animation de frappe
            # Frame de centrage
            center_frame = self.create_frame(
                msg_container, fg_color=self.colors["bg_chat"]
            )
            center_frame.grid(
                row=0, column=0, padx=(250, 250), pady=(0, 0), sticky="ew"
            )
            center_frame.grid_columnconfigure(0, weight=0)
            center_frame.grid_columnconfigure(1, weight=1)

            # Icône IA
            icon_label = self.create_label(
                center_frame,
                text="🤖",
                font=("Segoe UI", 16),
                fg_color=self.colors["bg_chat"],
                text_color=self.colors["accent"],
            )
            icon_label.grid(row=0, column=0, sticky="nw", padx=(0, 10), pady=(1, 0))

            # Container pour le message IA
            message_container = self.create_frame(
                center_frame, fg_color=self.colors["bg_chat"]
            )
            message_container.grid(row=0, column=1, sticky="ew", padx=0, pady=(2, 2))
            message_container.grid_columnconfigure(0, weight=1)

            # ⚡ SOLUTION FINALE: Appliquer le scroll forwarding SUR LE CONTAINER !
            def setup_container_scroll_forwarding(container):
                """Configure le scroll forwarding sur le container IA pour égaler la vitesse utilisateur"""

                def forward_from_container(event):
                    try:
                        if hasattr(self, "chat_frame") and self.use_ctk:
                            canvas = self._get_parent_canvas()
                            if not canvas:
                                return
                            if hasattr(event, "delta") and event.delta:
                                # AMPLIFICATION 60x pour égaler la vitesse utilisateur
                                scroll_delta = -1 * (event.delta // 6) * 60
                            else:
                                scroll_delta = -20 * 60
                            canvas.yview_scroll(scroll_delta, "units")
                        return "break"
                    except Exception:
                        return "break"

                container.bind("<MouseWheel>", forward_from_container)
                container.bind("<Button-4>", forward_from_container)
                container.bind("<Button-5>", forward_from_container)

            setup_container_scroll_forwarding(message_container)

            # Stocker le container pour l'affichage du timestamp
            self.current_message_container = message_container

            # Zone de texte pour le message IA
            text_widget = tk.Text(
                message_container,
                width=120,
                height=1,
                bg=self.colors["bg_chat"],
                fg=self.colors["text_primary"],
                font=("Segoe UI", 12),
                wrap=tk.WORD,
                relief="flat",
                bd=0,
                highlightthickness=0,
                state="normal",
                cursor="xterm",
                padx=8,
                pady=6,
                selectbackground="#4a90e2",
                selectforeground="#ffffff",
                exportselection=True,
                takefocus=False,
                insertwidth=0,
                # DÉSACTIVER COMPLÈTEMENT LE SCROLL INTERNE
                yscrollcommand=None,
                xscrollcommand=None,
            )
            text_widget.grid(row=0, column=0, padx=0, pady=(0, 0), sticky="nsew")
            # Ajustement avec hauteur généreuse pour éviter les scrollbars
            self.adjust_text_widget_height(text_widget)

            # Bind SEULEMENT pour les touches, pas pour la souris
            def prevent_editing_only(event):
                editing_keys = [
                    "BackSpace",
                    "Delete",
                    "Return",
                    "KP_Enter",
                    "Tab",
                    "space",
                    "Insert",
                ]
                if event.state & 0x4:
                    if event.keysym.lower() in ["a", "c"]:
                        return None
                if event.keysym in editing_keys:
                    return "break"
                if len(event.keysym) == 1 and event.keysym.isprintable():
                    return "break"
                return None

            text_widget.bind("<KeyPress>", prevent_editing_only)

            # UTILISER LA MÊME FONCTION QUE LES BULLES USER !
            # MAIS ON VA FORCER LA VITESSE A ÊTRE IDENTIQUE AUX USER !
            def setup_identical_scroll_to_user(text_widget_ia):
                """SCROLL IDENTIQUE AUX BULLES USER - Version finale"""

                def forward_user_style(event):
                    try:
                        if hasattr(self, "chat_frame") and self.use_ctk:
                            canvas = self._get_parent_canvas()
                            if not canvas:
                                return
                            if hasattr(event, "delta") and event.delta:
                                scroll_delta = -1 * (
                                    event.delta // 6
                                )  # EXACTEMENT comme USER
                            elif hasattr(event, "num"):
                                scroll_delta = (
                                    -20 if event.num == 4 else 20
                                )  # EXACTEMENT comme USER
                            else:
                                scroll_delta = -20
                            canvas.yview_scroll(scroll_delta, "units")
                    except Exception:
                        pass
                    return "break"

                # Bindings IDENTIQUES aux USER
                text_widget_ia.bind("<MouseWheel>", forward_user_style)
                text_widget_ia.bind("<Button-4>", forward_user_style)
                text_widget_ia.bind("<Button-5>", forward_user_style)
                text_widget_ia.bind("<Up>", lambda e: "break")
                text_widget_ia.bind("<Down>", lambda e: "break")
                text_widget_ia.bind("<Prior>", lambda e: "break")
                text_widget_ia.bind("<Next>", lambda e: "break")
                text_widget_ia.bind("<Home>", lambda e: "break")
                text_widget_ia.bind("<End>", lambda e: "break")

            setup_identical_scroll_to_user(text_widget)

            # SOLUTION DÉFINITIVE : Copier EXACTEMENT le système des bulles USER
            def apply_exact_user_scroll_system():
                """Applique EXACTEMENT le même système que les bulles USER"""

                def forward_scroll_to_page_ia(event):
                    try:
                        # Transférer le scroll à la zone de conversation principale
                        if hasattr(self, "chat_frame"):
                            # Pour CustomTkinter ScrollableFrame - SCROLL ULTRA RAPIDE
                            canvas = self._get_parent_canvas()
                            if canvas:
                                # Amplifier le delta pour scroll ultra rapide (x20 plus rapide)
                                if hasattr(event, "delta") and event.delta:
                                    scroll_delta = -1 * (
                                        event.delta // 6
                                    )  # 6 au lieu de 120 = 20x plus rapide
                                elif hasattr(event, "num"):
                                    scroll_delta = (
                                        -20 if event.num == 4 else 20
                                    )  # 20x plus rapide
                                else:
                                    scroll_delta = -20
                                canvas.yview_scroll(scroll_delta, "units")
                    except Exception:
                        pass
                    return "break"  # Empêcher le scroll local

                # Appliquer le transfert de scroll EXACTEMENT comme USER
                text_widget.bind("<MouseWheel>", forward_scroll_to_page_ia)
                text_widget.bind(
                    "<Button-4>", forward_scroll_to_page_ia
                )  # Linux scroll up
                text_widget.bind(
                    "<Button-5>", forward_scroll_to_page_ia
                )  # Linux scroll down

                # Désactiver toutes les autres formes de scroll EXACTEMENT comme USER
                text_widget.bind("<Up>", lambda e: "break")
                text_widget.bind("<Down>", lambda e: "break")
                text_widget.bind("<Prior>", lambda e: "break")  # Page Up
                text_widget.bind("<Next>", lambda e: "break")  # Page Down
                text_widget.bind("<Home>", lambda e: "break")
                text_widget.bind("<End>", lambda e: "break")

            apply_exact_user_scroll_system()

            # FORCER L'APPLICATION APRÈS TOUS LES AUTRES SETUPS !
            def force_final_bindings():
                """Force finale après que tout soit terminé"""

                def final_scroll_handler(event):
                    try:
                        if hasattr(self, "chat_frame") and self.use_ctk:
                            canvas = self._get_parent_canvas()
                            if not canvas:
                                return
                            if hasattr(event, "delta") and event.delta:
                                scroll_delta = -1 * (event.delta // 6)
                            else:
                                scroll_delta = -20
                            canvas.yview_scroll(scroll_delta, "units")
                    except Exception:
                        pass
                    return "break"

                # Override avec force absolue
                text_widget.bind("<MouseWheel>", final_scroll_handler, add=False)
                text_widget.bind("<Button-4>", final_scroll_handler, add=False)
                text_widget.bind("<Button-5>", final_scroll_handler, add=False)

            # Appliquer après TOUS les autres setups (délais multiples)
            text_widget.after(200, force_final_bindings)
            text_widget.after(500, force_final_bindings)
            text_widget.after(1000, force_final_bindings)

            def copy_on_double_click(_event):
                try:
                    self.root.clipboard_clear()
                    self.root.clipboard_append(text)
                    self.show_copy_notification("✅ Message copié !")
                except Exception:
                    self.show_copy_notification("❌ Erreur de copie")
                return "break"

            text_widget.bind("<Double-Button-1>", copy_on_double_click)
            self.create_copy_menu_with_notification(text_widget, text)

            # Démarrer l'animation de frappe avec hauteur dynamique
            self.start_typing_animation_dynamic(text_widget, text)

    def _scroll_if_needed_user(self):
        """Scroll pour le message utilisateur uniquement si le bas n'est pas visible"""
        try:
            canvas = self._get_parent_canvas()
            if canvas:
                canvas.update_idletasks()
                yview = canvas.yview()

                if yview and yview[1] < 1.0:
                    canvas.yview_moveto(1.0)
            else:
                parent = self.chat_frame.master
                parent.update_idletasks()
                yview = parent.yview() if hasattr(parent, "yview") else None
                if yview and yview[1] < 1.0:
                    parent.yview_moveto(1.0)
        except Exception:
            pass

    def setup_scroll_forwarding(self, text_widget):
        """Configure le transfert du scroll - Version ultra rapide pour bulles USER"""

        def forward_scroll_to_page(event):
            try:
                # Transférer le scroll à la zone de conversation principale
                if hasattr(self, "chat_frame"):
                    # Pour CustomTkinter ScrollableFrame - SCROLL ULTRA RAPIDE
                    canvas = self._get_parent_canvas()
                    if canvas:
                        # Amplifier le delta pour scroll ultra rapide (x20 plus rapide)
                        if hasattr(event, "delta") and event.delta:
                            scroll_delta = -1 * (
                                event.delta // 6
                            )  # 6 au lieu de 120 = 20x plus rapide
                        elif hasattr(event, "num"):
                            scroll_delta = (
                                -20 if event.num == 4 else 20
                            )  # 20x plus rapide
                        else:
                            scroll_delta = -20
                        canvas.yview_scroll(scroll_delta, "units")
                    else:
                        # Pour tkinter standard - SCROLL ULTRA RAPIDE
                        parent = self.chat_frame.master
                        while parent and not hasattr(parent, "yview_scroll"):
                            parent = parent.master
                        if parent:
                            # Amplifier le delta pour scroll MEGA ULTRA rapide (x60 plus rapide !)
                            if hasattr(event, "delta") and event.delta:
                                scroll_delta = -1 * (
                                    event.delta // 2
                                )  # 2 au lieu de 120 = 60x plus rapide !
                            elif hasattr(event, "num"):
                                scroll_delta = (
                                    -60 if event.num == 4 else 60
                                )  # 60x plus rapide
                            else:
                                scroll_delta = -60
                            parent.yview_scroll(scroll_delta, "units")
            except Exception:
                pass
            return "break"  # Empêcher le scroll local

        # Appliquer le transfert de scroll
        text_widget.bind("<MouseWheel>", forward_scroll_to_page)
        text_widget.bind("<Button-4>", forward_scroll_to_page)  # Linux scroll up
        text_widget.bind("<Button-5>", forward_scroll_to_page)  # Linux scroll down

        # Désactiver toutes les autres formes de scroll
        text_widget.bind("<Up>", lambda e: "break")
        text_widget.bind("<Down>", lambda e: "break")
        text_widget.bind("<Prior>", lambda e: "break")  # Page Up
        text_widget.bind("<Next>", lambda e: "break")  # Page Down
        text_widget.bind("<Home>", lambda e: "break")
        text_widget.bind("<End>", lambda e: "break")

    def create_user_message_bubble(self, parent, text):
        """Version avec hauteur précise et sélection activée pour les messages utilisateur"""
        if not isinstance(text, str):
            text = str(text)

        # Frame principale
        main_frame = self.create_frame(parent, fg_color=self.colors["bg_chat"])
        main_frame.grid(row=0, column=0, padx=(250, 250), pady=(0, 0), sticky="ew")
        main_frame.grid_columnconfigure(0, weight=0)
        main_frame.grid_columnconfigure(1, weight=1)

        # Icône utilisateur
        icon_label = self.create_label(
            main_frame,
            text="👤",
            font=("Segoe UI", 16),
            fg_color=self.colors["bg_chat"],
            text_color=self.colors["text_primary"],
        )
        icon_label.grid(row=0, column=0, sticky="nw", padx=(0, 10), pady=(1, 0))

        # Bulle utilisateur
        if self.use_ctk:
            bubble = ctk.CTkFrame(
                main_frame,
                fg_color=self.colors["bg_user"],
                corner_radius=12,
                border_width=0,
            )
        else:
            bubble = tk.Frame(
                main_frame,
                bg=self.colors["bg_user"],
                relief="flat",
                bd=0,
                highlightthickness=0,
            )

        bubble.grid(row=0, column=1, sticky="w", padx=0, pady=(2, 2))
        bubble.grid_columnconfigure(0, weight=0)

        # Calcul de hauteur PRÉCISE pour utilisateur
        word_count = len(text.split())

        # Largeur adaptée
        if word_count > 25:
            text_width = 120
        elif word_count > 10:
            text_width = 90
        elif word_count > 3:
            text_width = 70
        else:
            text_width = max(30, len(text) + 10)

        text_widget = tk.Text(
            bubble,
            width=text_width,
            height=2,  # Valeur initiale minimale
            bg=self.colors["bg_user"],
            fg="#ffffff",
            font=("Segoe UI", 12),
            wrap=tk.WORD,
            relief="flat",
            bd=0,
            highlightthickness=0,
            state="normal",
            cursor="xterm",
            padx=10,
            pady=8,
            selectbackground="#2563eb",
            selectforeground="#ffffff",
            exportselection=True,
            takefocus=False,
            insertwidth=0,
        )

        self.insert_formatted_text_tkinter(text_widget, text)

        # Ajustement parfait de la hauteur après rendu
        def adjust_height_later():
            text_widget.update_idletasks()
            line_count = int(text_widget.index("end-1c").split(".", maxsplit=1)[0])
            text_widget.configure(height=max(2, line_count))
            text_widget.update_idletasks()
            # Scroll automatique après ajustement
            if hasattr(self, "_force_scroll_to_bottom"):
                self._force_scroll_to_bottom()

        text_widget.after(30, adjust_height_later)

        # Empêcher l'édition mais permettre la sélection
        def on_key_press(event):
            """Permet les raccourcis de sélection et copie, bloque l'édition"""
            # Autoriser Ctrl+A (tout sélectionner)
            if event.state & 0x4 and event.keysym.lower() == "a":
                text_widget.tag_add("sel", "1.0", "end")
                return "break"

            # Autoriser Ctrl+C (copier)
            elif event.state & 0x4 and event.keysym.lower() == "c":
                try:
                    selected_text = text_widget.selection_get()
                    if selected_text:
                        self.root.clipboard_clear()
                        self.root.clipboard_append(selected_text)
                        if hasattr(self, "show_copy_notification"):
                            self.show_copy_notification("📋 Sélection copiée !")
                except tk.TclError:
                    pass
                return "break"

            # Autoriser les touches de sélection (Shift + flèches, etc.)
            elif event.keysym in ["Left", "Right", "Up", "Down", "Home", "End"] and (
                event.state & 0x1
            ):
                return None  # Laisser le widget gérer la sélection

            # Bloquer toutes les autres touches (édition)
            else:
                return "break"

        text_widget.bind("<Key>", on_key_press)
        text_widget.bind("<KeyPress>", on_key_press)

        # Configuration du scroll amélioré
        self.setup_scroll_forwarding(text_widget)

        # COPIE avec double-clic
        def copy_on_double_click(_event):
            try:
                # Essayer de copier la sélection d'abord
                try:
                    selected_text = text_widget.selection_get()
                    if selected_text.strip():
                        self.root.clipboard_clear()
                        self.root.clipboard_append(selected_text)
                        self.show_copy_notification("📋 Sélection copiée !")
                        return "break"
                except tk.TclError:
                    pass

                # Si pas de sélection, copier tout le message
                self.root.clipboard_clear()
                self.root.clipboard_append(text)
                self.show_copy_notification("📋 Message copié !")
            except Exception:
                self.show_copy_notification("❌ Erreur de copie")
            return "break"

        text_widget.bind("<Double-Button-1>", copy_on_double_click)
        text_widget.grid(row=0, column=0, padx=8, pady=(6, 0), sticky="nw")

        # Timestamp
        timestamp = datetime.now().strftime("%H:%M")
        time_label = self.create_label(
            bubble,
            text=timestamp,
            font=("Segoe UI", 10),
            fg_color=self.colors["bg_user"],
            text_color="#b3b3b3",
        )
        time_label.grid(row=1, column=0, sticky="w", padx=8, pady=(0, 6))

        # Menu contextuel amélioré
        def show_context_menu(event):
            try:
                context_menu = tk.Menu(
                    self.root,
                    tearoff=0,
                    bg="#3b82f6",
                    fg="white",
                    activebackground="#2563eb",
                    activeforeground="white",
                )

                # Vérifier s'il y a une sélection
                has_selection = False
                try:
                    selected = text_widget.selection_get()
                    has_selection = bool(selected.strip())
                except tk.TclError:
                    pass

                if has_selection:
                    context_menu.add_command(
                        label="📋 Copier la sélection",
                        command=lambda: copy_on_double_click(None),
                    )
                    context_menu.add_separator()

                context_menu.add_command(
                    label="📄 Copier tout le message",
                    command=lambda: (
                        self.root.clipboard_clear(),
                        self.root.clipboard_append(text),
                        self.show_copy_notification("📋 Message copié !"),
                    ),
                )

                context_menu.add_command(
                    label="🔍 Tout sélectionner",
                    command=lambda: text_widget.tag_add("sel", "1.0", "end"),
                )

                context_menu.tk_popup(event.x_root, event.y_root)

            except Exception:
                pass
            finally:
                try:
                    context_menu.grab_release()
                except Exception:
                    pass

        text_widget.bind("<Button-3>", show_context_menu)  # Clic droit

    def create_ai_message_simple(self, parent, text):
        """Version CORRIGÉE pour les résumés - Hauteur automatique sans scroll interne"""
        try:
            # Vérifier que le texte est une chaîne
            if not isinstance(text, str):
                if isinstance(text, dict):
                    text = (
                        text.get("response")
                        or text.get("text")
                        or text.get("content")
                        or text.get("message")
                        or str(text)
                    )
                else:
                    text = str(text)

            # Frame de centrage
            center_frame = self.create_frame(parent, fg_color=self.colors["bg_chat"])
            center_frame.grid(
                row=0, column=0, padx=(250, 250), pady=(0, 0), sticky="ew"
            )
            center_frame.grid_columnconfigure(0, weight=0)
            center_frame.grid_columnconfigure(1, weight=1)

            # Icône IA
            icon_label = self.create_label(
                center_frame,
                text="🤖",
                font=("Segoe UI", 16),
                fg_color=self.colors["bg_chat"],
                text_color=self.colors["accent"],
            )
            icon_label.grid(row=0, column=0, sticky="nw", padx=(0, 10), pady=(1, 0))

            # Container pour le message IA
            message_container = self.create_frame(
                center_frame, fg_color=self.colors["bg_chat"]
            )
            message_container.grid(row=0, column=1, sticky="ew", padx=0, pady=(2, 2))
            message_container.grid_columnconfigure(0, weight=1)

            # ⚡ SOLUTION: Appliquer le scroll forwarding SUR LE CONTAINER aussi ici !
            def setup_container_scroll_forwarding_simple(container):
                """Configure le scroll forwarding sur le container IA (version simple)"""

                def forward_from_container(event):
                    try:
                        if hasattr(self, "chat_frame") and self.use_ctk:
                            canvas = self._get_parent_canvas()
                            if not canvas:
                                return
                            if hasattr(event, "delta") and event.delta:
                                # AMPLIFICATION 60x pour égaler la vitesse utilisateur
                                scroll_delta = -1 * (event.delta // 6) * 60
                            else:
                                scroll_delta = -20 * 60
                            canvas.yview_scroll(scroll_delta, "units")
                        return "break"
                    except Exception:
                        return "break"

                container.bind("<MouseWheel>", forward_from_container)
                container.bind("<Button-4>", forward_from_container)
                container.bind("<Button-5>", forward_from_container)

            setup_container_scroll_forwarding_simple(message_container)

            # Stocker le container pour l'affichage du timestamp
            self.current_message_container = message_container

            # 🔧 CALCUL INTELLIGENT DE LA HAUTEUR BASÉ SUR LE CONTENU
            estimated_height = self._calculate_text_height_for_widget(text)

            # Widget Text avec hauteur calculée
            text_widget = tk.Text(
                message_container,
                width=120,
                height=estimated_height,  # Hauteur calculée intelligemment
                bg=self.colors["bg_chat"],
                fg=self.colors["text_primary"],
                font=("Segoe UI", 12),
                wrap=tk.WORD,
                relief="flat",
                bd=0,
                highlightthickness=0,
                state="normal",
                cursor="xterm",
                padx=8,
                pady=6,
                selectbackground="#4a90e2",
                selectforeground="#ffffff",
                exportselection=True,
                takefocus=False,
                insertwidth=0,
            )

            # 🔧 DÉSACTIVER LE SCROLL INTERNE DÈS LA CRÉATION
            self._disable_text_scroll(text_widget)

            text_widget.grid(row=0, column=0, padx=0, pady=(0, 0), sticky="nsew")

            # Bind minimal pour permettre la sélection
            def prevent_editing_only(event):
                editing_keys = [
                    "BackSpace",
                    "Delete",
                    "Return",
                    "KP_Enter",
                    "Tab",
                    "space",
                    "Insert",
                ]
                if event.state & 0x4:
                    if event.keysym.lower() in ["a", "c"]:
                        return None
                if event.keysym in editing_keys:
                    return "break"
                if len(event.keysym) == 1 and event.keysym.isprintable():
                    return "break"
                return None

            text_widget.bind("<KeyPress>", prevent_editing_only)

            def copy_on_double_click(_event):
                try:
                    self.root.clipboard_clear()
                    self.root.clipboard_append(text)
                    self.show_copy_notification("✅ Message copié !")
                except Exception:
                    self.show_copy_notification("❌ Erreur de copie")
                return "break"

            text_widget.bind("<Double-Button-1>", copy_on_double_click)
            self.create_copy_menu_with_notification(text_widget, text)

            # Démarrer l'animation de frappe avec hauteur pré-calculée
            self.start_typing_animation_dynamic(text_widget, text)

        except Exception as e:
            err_msg = f"[ERREUR affichage IA] {e}\n{traceback.format_exc()}"
            if hasattr(self, "logger"):
                self.logger.error(err_msg)
            fallback_text = f"❌ Erreur d'affichage du message IA :\n{e}"
            try:
                self.add_message_bubble(fallback_text, is_user=False)
            except Exception:
                pass

    def debug_text_widget_scroll(self, text_widget, widget_name="Widget"):
        """Debug pour vérifier l'état du scroll d'un widget Text"""
        try:
            text_widget.update_idletasks()

            # Obtenir les informations de scroll
            yview = text_widget.yview()
            height = text_widget.cget("height")

            # Compter les lignes réelles
            line_count = int(text_widget.index("end-1c").split(".")[0])

            print(f"🔍 DEBUG {widget_name}:")
            print(f"   Hauteur configurée: {height} lignes")
            print(f"   Lignes réelles: {line_count}")
            print(f"   YView (scroll): {yview}")
            print(
                f"   Scroll nécessaire: {'OUI' if yview and yview[1] < 1.0 else 'NON'}"
            )
            print(
                f"   État: {'✅ OK' if not yview or yview[1] >= 1.0 else '❌ SCROLL INTERNE'}"
            )
            print()

        except Exception as e:
            print(f"❌ Erreur debug {widget_name}: {e}")

    def _calculate_text_height_for_widget(self, text):
        """Calcule la hauteur optimale pour un texte donné"""
        if not text:
            return 5

        # Compter les lignes de base
        lines = text.split("\n")
        base_lines = len(lines)

        # Estimer les lignes wrappées
        estimated_width_chars = 100  # Estimation conservative
        wrapped_lines = 0

        for line in lines:
            if len(line) > estimated_width_chars:
                # Cette ligne va être wrappée
                additional_lines = (len(line) - 1) // estimated_width_chars
                wrapped_lines += additional_lines

        # Calcul final avec marge de sécurité
        total_estimated_lines = base_lines + wrapped_lines

        # Ajouter une marge généreuse pour éviter tout scroll
        margin = max(
            3, int(total_estimated_lines * 0.2)
        )  # 20% de marge minimum 3 lignes
        final_height = total_estimated_lines + margin

        # ⚡ CORRECTION: Pas de limite maximale pour afficher tout le contenu
        # La hauteur s'adapte automatiquement au contenu, même pour des messages très longs
        final_height = max(5, final_height)  # Minimum 5 lignes, pas de maximum

        return final_height

    def setup_improved_scroll_forwarding(self, text_widget):
        """Transfert ultra rapide du scroll pour les bulles IA"""
        # SOLUTION FINALE: Désactiver COMPLÈTEMENT le scroll interne du Text widget
        text_widget.configure(state="disabled")  # Désactiver temporairement

        # Supprimer TOUTES les fonctions de scroll par défaut
        text_widget.bind("<MouseWheel>", lambda e: "break")
        text_widget.bind("<Button-4>", lambda e: "break")
        text_widget.bind("<Button-5>", lambda e: "break")
        text_widget.bind("<Control-MouseWheel>", lambda e: "break")
        text_widget.bind("<Shift-MouseWheel>", lambda e: "break")

        # Remettre en mode normal mais sans scroll interne
        text_widget.configure(state="normal")

        # SOLUTION FINALE: Utiliser EXACTEMENT la même logique que les bulles USER
        def forward_scroll_to_page(event):
            try:
                # Transférer le scroll à la zone de conversation principale
                if hasattr(self, "chat_frame"):
                    # Pour CustomTkinter ScrollableFrame - MÊME LOGIQUE QUE USER
                    canvas = self._get_parent_canvas()
                    if canvas:
                        # EXACTEMENT la même amplification que les bulles USER
                        if hasattr(event, "delta") and event.delta:
                            scroll_delta = -1 * (event.delta // 6)  # MÊME que USER
                        elif hasattr(event, "num"):
                            scroll_delta = (
                                -20 if event.num == 4 else 20
                            )  # MÊME que USER
                        else:
                            scroll_delta = -20
                        canvas.yview_scroll(scroll_delta, "units")
                    else:
                        # Pour tkinter standard - MÊME LOGIQUE QUE USER
                        parent = self.chat_frame.master
                        while parent and not hasattr(parent, "yview_scroll"):
                            parent = parent.master
                        if parent:
                            # EXACTEMENT la même amplification que les bulles USER
                            if hasattr(event, "delta") and event.delta:
                                scroll_delta = -1 * (event.delta // 6)  # MÊME que USER
                            elif hasattr(event, "num"):
                                scroll_delta = (
                                    -20 if event.num == 4 else 20
                                )  # MÊME que USER
                            else:
                                scroll_delta = -20
                            parent.yview_scroll(scroll_delta, "units")
            except Exception:
                pass
            return "break"  # Empêcher le scroll local - MÊME que USER

        # SOLUTION: Désactiver les bindings par défaut de Tkinter qui interceptent le scroll
        text_widget.unbind("<MouseWheel>")
        text_widget.unbind("<Button-4>")
        text_widget.unbind("<Button-5>")

        # Appliquer le transfert de scroll ultra rapide
        text_widget.bind("<MouseWheel>", forward_scroll_to_page)
        text_widget.bind("<Button-4>", forward_scroll_to_page)
        text_widget.bind("<Button-5>", forward_scroll_to_page)

        # Vérifier l'état du widget

        # Tester les événements au niveau du PARENT aussi
        parent_frame = text_widget.master

        def parent_test_event(event):
            # Transférer vers notre fonction
            return forward_scroll_to_page(event)

        # Ajouter les bindings au parent ET au text widget
        parent_frame.bind("<MouseWheel>", parent_test_event)
        parent_frame.bind("<Button-4>", parent_test_event)
        parent_frame.bind("<Button-5>", parent_test_event)

    def start_typing_animation_dynamic(self, text_widget, full_text):
        """Animation caractère par caractère avec formatage progressif intelligent"""
        # DÉSACTIVER la saisie pendant l'animation
        self.set_input_state(False)

        # Réinitialiser le widget
        text_widget.configure(state="normal")
        text_widget.delete("1.0", "end")

        # DÉSACTIVER le scroll pendant l'animation pour éviter les saccades
        self._disable_text_scroll(text_widget)

        # Pré-traiter le texte pour remplacer les liens par leurs titres
        processed_text, link_mapping = self._preprocess_links_for_animation(full_text)

        # Pré-analyser les blocs de code pour la coloration en temps réel
        self._code_blocks_map = self._preanalyze_code_blocks(processed_text)

        # Debug: afficher quelques positions du map
        if self._code_blocks_map:
            sample_keys = list(self._code_blocks_map.keys())[:10]
            print(
                f"[DEBUG] start_typing: _code_blocks_map contient {len(self._code_blocks_map)} entrées"
            )
            print(
                f"[DEBUG] Exemples: {[(k, self._code_blocks_map[k]) for k in sample_keys]}"
            )
        else:
            print(
                "[DEBUG] start_typing: _code_blocks_map est VIDE - pas de blocs de code détectés"
            )
            print(f"[DEBUG] Texte reçu (premiers 500 chars): {processed_text[:500]}")

        # Variables pour l'animation CARACTÈRE PAR CARACTÈRE
        self.typing_index = 0
        self.typing_text = processed_text  # Utiliser le texte pré-traité
        self.typing_widget = text_widget
        self.typing_speed = 1

        # Stocker le mapping des liens pour plus tard
        if link_mapping:
            self._pending_links = link_mapping

        # Réinitialiser les positions formatées et le tracking du bold
        self._formatted_positions = set()
        self._formatted_bold_contents = (
            set()
        )  # NOUVEAU: tracking par contenu pour le bold

        # Pré-analyser les tableaux Markdown pour l'animation progressive
        self._table_blocks = self._preanalyze_markdown_tables(processed_text)
        self._formatted_tables = set()  # Tableaux déjà formatés (par index)

        # Configurer tous les tags de formatage
        self._configure_all_formatting_tags(text_widget)

        # Configuration spéciale du tag 'normal' pour l'animation SANS formatage
        text_widget.tag_configure(
            "normal", font=("Segoe UI", 12), foreground=self.colors["text_primary"]
        )

        # Flag d'interruption
        self._typing_interrupted = False

        # Démarrer l'animation caractère par caractère
        self.continue_typing_animation_dynamic()

    def _preprocess_links_for_animation(self, text):
        """Pré-traite le texte pour remplacer les liens [titre](url) par juste le titre pendant l'animation"""
        # Pattern pour détecter [titre](url)
        link_pattern = r"\[([^\]]+)\]\(([^)]+)\)"

        # Initialiser la liste des liens pour la conversion finale
        if not hasattr(self, "_pending_links"):
            self._pending_links = []

        def replace_link(match):
            title = match.group(1)
            url = match.group(2)

            # Stocker dans _pending_links comme liste
            self._pending_links.append(
                {
                    "title": title,
                    "url": url,
                }
            )

            # Retourner juste le titre (sans marqueur)
            return title

        # Remplacer tous les liens par leurs titres
        processed_text = re.sub(link_pattern, replace_link, text)

        print(f"[DEBUG] Liens prétraités: {len(self._pending_links)} liens trouvés")
        for link_data in self._pending_links:
            print(f"  '{link_data['title']}' -> {link_data['url']}")

        return processed_text, self._pending_links

    def _preanalyze_code_blocks(self, text):
        """Pré-analyse les blocs de code pour la coloration en temps réel"""
        code_blocks_map = {}  # Position -> (language, token_type)

        # Pattern pour détecter les blocs de code avec langage
        # CORRECTION: Capturer aussi les + pour c++, et # pour c#
        code_block_pattern = r"```([\w+#-]+)?\n?(.*?)```"

        matches_found = list(re.finditer(code_block_pattern, text, re.DOTALL))
        print(
            f"[DEBUG] _preanalyze_code_blocks: {len(matches_found)} blocs de code trouvés dans le texte"
        )

        for match in matches_found:
            language = (match.group(1) or "text").lower()
            code_content = match.group(2).strip() if match.group(2) else ""

            print(
                f"[DEBUG] Bloc de code détecté: langage='{language}', longueur={len(code_content)}, position={match.start()}-{match.end()}"
            )

            if not code_content:
                print("[DEBUG] Bloc ignoré car contenu vide")
                continue

            # Marquer la zone des backticks d'ouverture + newline comme "hidden"
            opening_start = match.start()
            # Calculer la fin de l'ouverture (```language\n)
            opening_text = f"```{match.group(1) or ''}"
            opening_end = match.start() + len(opening_text)

            # Chercher le \n après ```language
            newline_pos = text.find("\n", opening_end)
            if newline_pos != -1 and newline_pos < match.end() - 3:
                # Inclure le \n dans le hidden
                opening_end = newline_pos + 1

            # Marquer tout de opening_start à opening_end comme hidden
            for pos in range(opening_start, opening_end):
                if pos < len(text):
                    code_blocks_map[pos] = (language, "code_block_marker")

            # Le code commence après le \n
            code_start = opening_end

            # Calculer la vraie position de fin du code (avant le ``` de fermeture)
            code_end = match.end() - 3

            # Chercher le \n avant les ``` de fermeture pour le masquer aussi
            if code_end > 0 and text[code_end - 1] == "\n":
                code_end -= 1

            # Obtenir le vrai contenu du code SANS strip pour garder les positions correctes
            raw_code_content = text[code_start:code_end]

            # Masquer le \n avant les ``` de fermeture s'il existe
            if code_end < match.end() - 3:
                for pos in range(code_end, match.end() - 3):
                    code_blocks_map[pos] = (language, "code_block_marker")

            if language == "python":
                self._analyze_python_tokens(
                    raw_code_content, code_start, code_blocks_map
                )
            elif language in ["javascript", "js"]:
                self._analyze_javascript_tokens(
                    raw_code_content, code_start, code_blocks_map
                )
            elif language == "css":
                self._analyze_css_tokens(raw_code_content, code_start, code_blocks_map)
            elif language in ["html", "xml"]:
                self._analyze_html_tokens(raw_code_content, code_start, code_blocks_map)
            elif language in ["bash", "shell", "sh"]:
                self._analyze_bash_tokens(raw_code_content, code_start, code_blocks_map)
            elif language in ["sql", "mysql", "postgresql", "sqlite"]:
                self._analyze_sql_tokens(raw_code_content, code_start, code_blocks_map)
            elif language == "java":
                self._analyze_java_tokens(raw_code_content, code_start, code_blocks_map)
            elif language in ["c", "cpp", "c++", "cxx"]:
                self._analyze_cpp_tokens(
                    raw_code_content, code_start, code_blocks_map, language
                )
            elif language in ["csharp", "cs", "c#"]:
                self._analyze_csharp_tokens(
                    raw_code_content, code_start, code_blocks_map
                )
            elif language in ["go", "golang"]:
                self._analyze_go_tokens(raw_code_content, code_start, code_blocks_map)
            elif language in ["ruby", "rb"]:
                self._analyze_ruby_tokens(raw_code_content, code_start, code_blocks_map)
            elif language == "swift":
                self._analyze_swift_tokens(
                    raw_code_content, code_start, code_blocks_map
                )
            elif language == "php":
                self._analyze_php_tokens(raw_code_content, code_start, code_blocks_map)
            elif language in ["perl", "pl"]:
                self._analyze_perl_tokens(raw_code_content, code_start, code_blocks_map)
            elif language in ["rust", "rs"]:
                self._analyze_rust_tokens(raw_code_content, code_start, code_blocks_map)
            else:
                # Code générique
                for i in range(len(raw_code_content)):
                    pos = code_start + i
                    code_blocks_map[pos] = (language, "code_block")

            # Marquer la zone des backticks de fermeture comme "hidden"
            closing_start = match.end() - 3
            for pos in range(closing_start, match.end()):
                if pos < len(text):
                    code_blocks_map[pos] = (language, "code_block_marker")

        print(
            f"[DEBUG] _preanalyze_code_blocks: {len(code_blocks_map)} positions mappées au total"
        )

        # Debug: afficher les types de tokens trouvés par langage
        token_types_by_lang = {}
        for pos, (lang, token_type) in code_blocks_map.items():
            if lang not in token_types_by_lang:
                token_types_by_lang[lang] = set()
            token_types_by_lang[lang].add(token_type)
        print(
            f"[DEBUG] Types de tokens par langage: {dict((k, list(v)) for k, v in token_types_by_lang.items())}"
        )

        return code_blocks_map

    def _preanalyze_markdown_tables(self, text):
        """Pré-analyse les tableaux Markdown pour l'animation progressive"""
        tables = []  # Liste de dictionnaires avec infos sur chaque tableau

        lines = text.split("\n")
        i = 0
        char_pos = 0  # Position en caractères dans le texte

        while i < len(lines):
            line = lines[i]

            # Vérifier si c'est le début d'un tableau
            if "|" in line and i + 1 < len(lines):
                next_line = lines[i + 1]
                separator_pattern = r"^\|?[\s\-:|\s]+\|?$"
                if re.match(separator_pattern, next_line.strip()) and "-" in next_line:
                    # C'est un tableau!
                    table_start_pos = char_pos
                    table_start_line = i
                    table_lines_info = []

                    # Collecter toutes les lignes du tableau
                    j = i
                    table_char_pos = char_pos
                    while j < len(lines) and "|" in lines[j]:
                        line_info = {
                            "line_num": j,
                            "start_pos": table_char_pos,
                            "end_pos": table_char_pos + len(lines[j]),
                            "content": lines[j],
                            "is_separator": j == i + 1,
                        }
                        table_lines_info.append(line_info)
                        table_char_pos += len(lines[j]) + 1  # +1 pour le \n
                        j += 1

                        # Vérifier si c'est un nouveau séparateur (nouveau tableau)
                        if (
                            j < len(lines)
                            and re.match(separator_pattern, lines[j].strip())
                            and "-" in lines[j]
                        ):
                            if j > i + 1:  # Pas le séparateur du tableau actuel
                                break

                    tables.append(
                        {
                            "start_line": table_start_line,
                            "end_line": j - 1,
                            "start_pos": table_start_pos,
                            "end_pos": table_char_pos - 1,
                            "lines": table_lines_info,
                        }
                    )

                    # Avancer après le tableau
                    char_pos = table_char_pos
                    i = j
                    continue

            char_pos += len(line) + 1  # +1 pour le \n
            i += 1

        return tables

    def _analyze_python_tokens(self, code, start_offset, code_map):
        """Analyse les tokens Python pour la coloration en temps réel avec couleurs VS Code"""
        try:
            lexer = PythonLexer()
            current_pos = start_offset
            tokens_added = 0

            for token_type, value in lex(code, lexer):
                # Convertir le type de token Pygments en tag configuré
                tag = self._pygments_token_to_tag(token_type)

                for i in range(len(value)):
                    pos = current_pos + i
                    code_map[pos] = ("python", tag)
                    tokens_added += 1
                current_pos += len(value)

            print(
                f"[DEBUG] _analyze_python_tokens: {tokens_added} tokens ajoutés (offset {start_offset})"
            )

        except Exception as e:
            print(f"[DEBUG] Erreur Pygments: {e}, utilisation du fallback")
            # Fallback sans Pygments
            self._analyze_python_simple(code, start_offset, code_map)

    def _pygments_token_to_tag(self, token_type):
        """Convertit un token Pygments en tag tkinter configuré avec couleurs VS Code"""
        token_str = str(token_type)

        # Mapping des tokens Pygments vers les tags configurés
        # Keywords (bleu #569cd6)
        if "Keyword" in token_str:
            return "Token.Keyword"

        # Strings (orange-brun #ce9178)
        if "String" in token_str or "Literal.String" in token_str:
            return "Token.Literal.String"

        # Comments (vert #6a9955)
        if "Comment" in token_str:
            return "Token.Comment.Single"

        # Numbers (vert clair #b5cea8)
        if "Number" in token_str or "Literal.Number" in token_str:
            return "Token.Literal.Number"

        # Functions (jaune #dcdcaa)
        if "Name.Function" in token_str:
            return "Token.Name.Function"

        # Classes (cyan #4ec9b0)
        if "Name.Class" in token_str:
            return "Token.Name.Class"

        # Builtins (jaune #dcdcaa)
        if "Name.Builtin" in token_str:
            return "Token.Name.Builtin"

        # Decorators (jaune #dcdcaa)
        if "Name.Decorator" in token_str or "Decorator" in token_str:
            return "Token.Name.Function"

        # Operators (blanc #d4d4d4)
        if "Operator" in token_str:
            return "Token.Operator"

        # Punctuation (blanc #d4d4d4)
        if "Punctuation" in token_str:
            return "Token.Punctuation"

        # Variables/Names (bleu clair #9cdcfe)
        if "Name" in token_str:
            return "Token.Name"

        # Text/Whitespace - utiliser le style code_block par défaut
        if "Text" in token_str or "Whitespace" in token_str:
            return "code_block"

        # Par défaut, utiliser code_block
        return "code_block"

    def _analyze_python_simple(self, code, start_offset, code_map):
        """Analyse Python simple sans Pygments"""
        keywords = set(keyword.kwlist)
        tokens_added = 0

        # Pattern pour identifier différents éléments
        token_pattern = r'''
            (#.*$)|                      # Commentaires
            (""".*?""")|                 # Docstrings triple quotes
            ("(?:[^"\\]|\\.)*")|         # Chaînes double quotes
            ('(?:[^'\\]|\\.)*')|         # Chaînes simple quotes
            (\b\d+\.?\d*\b)|             # Nombres
            (\b[a-zA-Z_]\w*\b)|          # Identifiants
            ([+\-*/%=<>!&|^~]|//|\*\*|<<|>>|\+=|-=|\*=|/=|%=|&=|\|=|\^=|<<=|>>=|==|!=|<=|>=|and|or|not|\+=|-=)  # Opérateurs
        '''

        lines = code.split("\n")
        current_pos = start_offset

        for line in lines:
            for match in re.finditer(token_pattern, line, re.VERBOSE):
                value = match.group(0)
                match_start = current_pos + match.start()

                if match.group(1):  # Commentaire
                    tag = "Token.Comment.Single"
                elif match.group(2) or match.group(3) or match.group(4):  # Chaînes
                    tag = "Token.Literal.String"
                elif match.group(5):  # Nombres
                    tag = "Token.Literal.Number"
                elif match.group(6):  # Identifiants
                    if value in keywords:
                        tag = "Token.Keyword"
                    else:
                        tag = "Token.Name"
                else:  # Opérateurs
                    tag = "Token.Operator"

                for i in range(len(value)):
                    pos = match_start + i
                    code_map[pos] = ("python", tag)
                    tokens_added += 1

            current_pos += len(line) + 1  # +1 pour le \n

        print(f"[DEBUG] _analyze_python_simple: {tokens_added} tokens ajoutés")

    def _analyze_javascript_tokens(self, code, start_offset, code_map):
        """Analyse les tokens JavaScript pour la coloration en temps réel"""
        js_keywords = {
            "var",
            "let",
            "const",
            "function",
            "return",
            "if",
            "else",
            "for",
            "while",
            "do",
            "switch",
            "case",
            "default",
            "break",
            "continue",
            "try",
            "catch",
            "finally",
            "throw",
            "new",
            "this",
            "super",
            "class",
            "extends",
            "import",
            "export",
            "from",
            "async",
            "await",
            "yield",
            "typeof",
            "instanceof",
            "in",
            "of",
            "true",
            "false",
            "null",
            "undefined",
        }

        # Pattern pour identifier différents éléments JS - sans mode VERBOSE
        token_pattern = r'(//.*$)|(/\*.*?\*/)|("(?:[^"\\]|\\.)*")|(\x27(?:[^\x27\\]|\\.)*\x27)|(`(?:[^`\\]|\\.)*`)|(\b\d+\.?\d*\b)|(\b[a-zA-Z_$]\w*\b)|([+\-*/%=<>!&|^~]+)'

        lines = code.split("\n")
        current_pos = start_offset

        for line in lines:
            for match in re.finditer(token_pattern, line):
                value = match.group(0)
                match_start = current_pos + match.start()

                if match.group(1) or match.group(2):  # Commentaires
                    tag = "js_comment"
                elif match.group(3) or match.group(4) or match.group(5):  # Chaînes
                    tag = "js_string"
                elif match.group(6):  # Nombres
                    tag = "js_number"
                elif match.group(7):  # Identifiants
                    if value in js_keywords:
                        tag = "js_keyword"
                    else:
                        tag = "js_variable"
                else:  # Opérateurs
                    tag = "js_operator"

                for i in range(len(value)):
                    pos = match_start + i
                    code_map[pos] = ("javascript", tag)

            current_pos += len(line) + 1

        print(
            f"[DEBUG] _analyze_javascript_tokens: {len([k for k in code_map if code_map.get(k, ('', ''))[0] == 'javascript'])} tokens ajoutés (offset {start_offset})"
        )

    def _analyze_css_tokens(self, code, start_offset, code_map):
        """Analyse les tokens CSS pour la coloration en temps réel"""
        # Pattern pour CSS - sans mode VERBOSE pour éviter les problèmes avec #
        token_pattern = r"(/\*.*?\*/)|(\#[a-fA-F0-9]{3,8}\b)|(\d+\.?\d*(px|em|rem|%|vh|vw|pt)?)|([a-zA-Z-]+)\s*:|([\.#]?[a-zA-Z_-][\w-]*)|([{}:;,])"

        lines = code.split("\n")
        current_pos = start_offset

        for line in lines:
            for match in re.finditer(token_pattern, line):
                value = match.group(0)
                match_start = current_pos + match.start()

                if match.group(1):  # Commentaire
                    tag = "css_comment"
                elif match.group(2):  # Couleur hex
                    tag = "css_value"
                elif match.group(3):  # Nombre
                    tag = "css_unit"
                elif match.group(5):  # Propriété
                    tag = "css_property"
                elif match.group(6):  # Sélecteur
                    tag = "css_selector"
                else:
                    tag = "code_block"

                for i in range(len(value)):
                    pos = match_start + i
                    code_map[pos] = ("css", tag)

            current_pos += len(line) + 1

        print(
            f"[DEBUG] _analyze_css_tokens: tokens CSS ajoutés (offset {start_offset})"
        )

    def _analyze_html_tokens(self, code, start_offset, code_map):
        """Analyse les tokens HTML pour la coloration en temps réel"""
        # Pattern amélioré pour HTML - capture séparément les différents éléments
        # Groupe 1: Commentaires <!-- ... -->
        # Groupe 2: Tags fermants </tag> ou tags ouvrants <tag
        # Groupe 3: Attributs name= (sans le =)
        # Groupe 4: Valeurs entre guillemets "..." ou '...'
        # Groupe 5: Fermeture de tag > ou />
        token_pattern = r'(<!--[\s\S]*?-->)|(</?[a-zA-Z][a-zA-Z0-9:-]*)|([a-zA-Z_:][a-zA-Z0-9_:.-]*)(?==)|("(?:[^"\\]|\\.)*"|\'(?:[^\'\\]|\\.)*\')|(/?>)'

        lines = code.split("\n")
        current_pos = start_offset

        for line in lines:
            for match in re.finditer(token_pattern, line, re.DOTALL):
                value = match.group(0)
                match_start = current_pos + match.start()

                if match.group(1):  # Commentaire
                    tag = "html_comment"
                elif match.group(2):  # Tag
                    tag = "html_tag"
                elif match.group(3):  # Attribut (nom avant le =)
                    tag = "html_attribute"
                elif match.group(4):  # Valeur entre guillemets
                    tag = "html_value"
                elif match.group(5):  # Fermeture de tag
                    tag = "html_tag"
                else:
                    tag = "code_block"

                for i in range(len(value)):
                    pos = match_start + i
                    code_map[pos] = ("html", tag)

            current_pos += len(line) + 1

        print(
            f"[DEBUG] _analyze_html_tokens: tokens HTML ajoutés (offset {start_offset})"
        )

    def _analyze_bash_tokens(self, code, start_offset, code_map):
        """Analyse les tokens Bash pour la coloration en temps réel"""
        bash_keywords = {
            "if",
            "then",
            "else",
            "elif",
            "fi",
            "for",
            "while",
            "do",
            "done",
            "case",
            "esac",
            "function",
            "return",
            "exit",
            "export",
            "local",
            "in",
            "until",
            "select",
            "break",
            "continue",
        }
        bash_commands = {
            "echo",
            "cd",
            "ls",
            "cat",
            "grep",
            "sed",
            "awk",
            "find",
            "chmod",
            "chown",
            "mkdir",
            "rm",
            "cp",
            "mv",
            "touch",
            "pwd",
            "source",
            "sudo",
            "apt",
            "pip",
            "npm",
            "git",
            "docker",
            "python",
            "node",
        }

        # Pattern sans mode VERBOSE pour éviter les problèmes avec #
        token_pattern = r'(\#.*$)|("(?:[^"\\]|\\.)*"|\'[^\']*\')|(\$\{?[a-zA-Z_]\w*\}?)|(\b[a-zA-Z_]\w*\b)|([|&;<>])'

        lines = code.split("\n")
        current_pos = start_offset

        for line in lines:
            for match in re.finditer(token_pattern, line):
                value = match.group(0)
                match_start = current_pos + match.start()

                if match.group(1):  # Commentaire
                    tag = "bash_comment"
                elif match.group(2):  # Chaîne
                    tag = "bash_string"
                elif match.group(3):  # Variable
                    tag = "bash_variable"
                elif match.group(4):  # Mot
                    if value in bash_keywords:
                        tag = "bash_keyword"
                    elif value in bash_commands:
                        tag = "bash_command"
                    else:
                        tag = "code_block"
                else:
                    tag = "code_block"

                for i in range(len(value)):
                    pos = match_start + i
                    code_map[pos] = ("bash", tag)

            current_pos += len(line) + 1

    def _analyze_sql_tokens(self, code, start_offset, code_map):
        """Analyse les tokens SQL pour la coloration en temps réel"""
        sql_keywords = {
            "SELECT",
            "FROM",
            "WHERE",
            "AND",
            "OR",
            "NOT",
            "IN",
            "LIKE",
            "ORDER",
            "BY",
            "GROUP",
            "HAVING",
            "JOIN",
            "LEFT",
            "RIGHT",
            "INNER",
            "OUTER",
            "ON",
            "AS",
            "INSERT",
            "INTO",
            "VALUES",
            "UPDATE",
            "SET",
            "DELETE",
            "CREATE",
            "TABLE",
            "DROP",
            "ALTER",
            "INDEX",
            "VIEW",
            "DISTINCT",
            "LIMIT",
            "OFFSET",
            "UNION",
            "ALL",
            "NULL",
            "IS",
            "ASC",
            "DESC",
            "PRIMARY",
            "KEY",
            "FOREIGN",
            "REFERENCES",
            "CONSTRAINT",
        }
        sql_functions = {
            "COUNT",
            "SUM",
            "AVG",
            "MIN",
            "MAX",
            "CONCAT",
            "SUBSTRING",
            "UPPER",
            "LOWER",
            "TRIM",
            "COALESCE",
            "IFNULL",
            "CAST",
            "CONVERT",
        }

        # Pattern SQL - sans mode VERBOSE
        token_pattern = r"(--.*$|/\*.*?\*/)|(\x27(?:[^\x27\\]|\\.)*\x27)|(\b\d+\.?\d*\b)|(\b[a-zA-Z_]\w*\b)"

        lines = code.split("\n")
        current_pos = start_offset

        for line in lines:
            for match in re.finditer(token_pattern, line, re.IGNORECASE):
                value = match.group(0)
                match_start = current_pos + match.start()

                if match.group(1):  # Commentaire
                    tag = "sql_comment"
                elif match.group(2):  # Chaîne
                    tag = "sql_string"
                elif match.group(3):  # Nombre
                    tag = "sql_number"
                elif match.group(4):  # Mot
                    upper_val = value.upper()
                    if upper_val in sql_keywords:
                        tag = "sql_keyword"
                    elif upper_val in sql_functions:
                        tag = "sql_function"
                    else:
                        tag = "code_block"
                else:
                    tag = "code_block"

                for i in range(len(value)):
                    pos = match_start + i
                    code_map[pos] = ("sql", tag)

            current_pos += len(line) + 1

    def _analyze_java_tokens(self, code, start_offset, code_map):
        """Analyse les tokens Java pour la coloration en temps réel"""
        java_keywords = {
            "abstract",
            "assert",
            "boolean",
            "break",
            "byte",
            "case",
            "catch",
            "char",
            "class",
            "const",
            "continue",
            "default",
            "do",
            "double",
            "else",
            "enum",
            "extends",
            "final",
            "finally",
            "float",
            "for",
            "goto",
            "if",
            "implements",
            "import",
            "instanceof",
            "int",
            "interface",
            "long",
            "native",
            "new",
            "package",
            "private",
            "protected",
            "public",
            "return",
            "short",
            "static",
            "strictfp",
            "super",
            "switch",
            "synchronized",
            "this",
            "throw",
            "throws",
            "transient",
            "try",
            "void",
            "volatile",
            "while",
            "true",
            "false",
            "null",
        }
        java_types = {
            "String",
            "Integer",
            "Boolean",
            "Double",
            "Float",
            "Long",
            "Short",
            "Byte",
            "Character",
            "Object",
            "List",
            "ArrayList",
            "HashMap",
            "Map",
            "Set",
            "HashSet",
            "Exception",
            "System",
            "Math",
            "Arrays",
        }

        token_pattern = r'(//.*$|/\*.*?\*/)|("(?:[^"\\]|\\.)*")|(\b\d+\.?\d*[fFdDlL]?\b)|(@\w+)|(\b[a-zA-Z_]\w*\b)'

        lines = code.split("\n")
        current_pos = start_offset

        for line in lines:
            for match in re.finditer(token_pattern, line):
                value = match.group(0)
                match_start = current_pos + match.start()

                if match.group(1):  # Commentaire
                    tag = "java_comment"
                elif match.group(2):  # Chaîne
                    tag = "java_string"
                elif match.group(3):  # Nombre
                    tag = "java_number"
                elif match.group(4):  # Annotation
                    tag = "java_annotation"
                elif match.group(5):  # Mot
                    if value in java_keywords:
                        tag = "java_keyword"
                    elif value in java_types or value[0].isupper():
                        tag = "java_class"
                    else:
                        tag = "code_block"
                else:
                    tag = "code_block"

                for i in range(len(value)):
                    pos = match_start + i
                    code_map[pos] = ("java", tag)

            current_pos += len(line) + 1

    def _analyze_cpp_tokens(self, code, start_offset, code_map, language="cpp"):
        """Analyse les tokens C/C++ pour la coloration en temps réel"""
        cpp_keywords = {
            "auto",
            "break",
            "case",
            "catch",
            "class",
            "const",
            "continue",
            "default",
            "delete",
            "do",
            "else",
            "enum",
            "explicit",
            "export",
            "extern",
            "false",
            "for",
            "friend",
            "goto",
            "if",
            "inline",
            "mutable",
            "namespace",
            "new",
            "operator",
            "private",
            "protected",
            "public",
            "register",
            "return",
            "sizeof",
            "static",
            "struct",
            "switch",
            "template",
            "this",
            "throw",
            "true",
            "try",
            "typedef",
            "typeid",
            "typename",
            "union",
            "unsigned",
            "using",
            "virtual",
            "void",
            "volatile",
            "while",
            "nullptr",
            "constexpr",
            "noexcept",
            "override",
            "final",
        }
        cpp_types = {
            "int",
            "char",
            "float",
            "double",
            "bool",
            "long",
            "short",
            "unsigned",
            "signed",
            "size_t",
            "string",
            "vector",
            "map",
            "set",
            "list",
            "pair",
            "unique_ptr",
            "shared_ptr",
            "weak_ptr",
            "array",
            "deque",
            "stack",
            "queue",
        }

        token_pattern = r'(//.*$|/\*.*?\*/)|("(?:[^"\\]|\\.)*"|\'(?:[^\'\\]|\\.)*\')|(\b\d+\.?\d*[fFlLuU]*\b)|(\#\w+)|(\b[a-zA-Z_]\w*\b)'

        # Normaliser le nom de langue pour les tags (c ou cpp)
        tag_lang = "c" if language == "c" else "cpp"

        lines = code.split("\n")
        current_pos = start_offset

        for line in lines:
            for match in re.finditer(token_pattern, line):
                value = match.group(0)
                match_start = current_pos + match.start()

                if match.group(1):  # Commentaire
                    tag = f"{tag_lang}_comment"
                elif match.group(2):  # Chaîne/Char
                    tag = f"{tag_lang}_string"
                elif match.group(3):  # Nombre
                    tag = f"{tag_lang}_number"
                elif match.group(4):  # Préprocesseur
                    tag = f"{tag_lang}_preprocessor"
                elif match.group(5):  # Mot
                    if value in cpp_keywords:
                        tag = f"{tag_lang}_keyword"
                    elif value in cpp_types:
                        tag = f"{tag_lang}_type"
                    else:
                        tag = "code_block"
                else:
                    tag = "code_block"

                for i in range(len(value)):
                    pos = match_start + i
                    code_map[pos] = (language, tag)

            current_pos += len(line) + 1

    def _analyze_csharp_tokens(self, code, start_offset, code_map):
        """Analyse les tokens C# pour la coloration en temps réel"""
        csharp_keywords = {
            "abstract",
            "as",
            "base",
            "bool",
            "break",
            "byte",
            "case",
            "catch",
            "char",
            "checked",
            "class",
            "const",
            "continue",
            "decimal",
            "default",
            "delegate",
            "do",
            "double",
            "else",
            "enum",
            "event",
            "explicit",
            "extern",
            "false",
            "finally",
            "fixed",
            "float",
            "for",
            "foreach",
            "goto",
            "if",
            "implicit",
            "in",
            "int",
            "interface",
            "internal",
            "is",
            "lock",
            "long",
            "namespace",
            "new",
            "null",
            "object",
            "operator",
            "out",
            "override",
            "params",
            "private",
            "protected",
            "public",
            "readonly",
            "ref",
            "return",
            "sbyte",
            "sealed",
            "short",
            "sizeof",
            "stackalloc",
            "static",
            "string",
            "struct",
            "switch",
            "this",
            "throw",
            "true",
            "try",
            "typeof",
            "uint",
            "ulong",
            "unchecked",
            "unsafe",
            "ushort",
            "using",
            "virtual",
            "void",
            "volatile",
            "while",
            "var",
            "async",
            "await",
            "dynamic",
            "nameof",
        }
        csharp_types = {
            "String",
            "Int32",
            "Int64",
            "Boolean",
            "Double",
            "Float",
            "Object",
            "List",
            "Dictionary",
            "Console",
            "Exception",
            "Task",
            "Action",
            "Func",
        }

        token_pattern = r'(//.*$|/\*.*?\*/)|("(?:[^"\\]|\\.)*"|@"[^"]*")|(\b\d+\.?\d*[fFdDmM]?\b)|(\b[a-zA-Z_]\w*\b)'

        lines = code.split("\n")
        current_pos = start_offset

        for line in lines:
            for match in re.finditer(token_pattern, line):
                value = match.group(0)
                match_start = current_pos + match.start()

                if match.group(1):  # Commentaire
                    tag = "csharp_comment"
                elif match.group(2):  # Chaîne
                    tag = "csharp_string"
                elif match.group(3):  # Nombre
                    tag = "csharp_number"
                elif match.group(4):  # Mot
                    if value in csharp_keywords:
                        tag = "csharp_keyword"
                    elif value in csharp_types or value[0].isupper():
                        tag = "csharp_class"
                    else:
                        tag = "code_block"
                else:
                    tag = "code_block"

                for i in range(len(value)):
                    pos = match_start + i
                    code_map[pos] = ("csharp", tag)

            current_pos += len(line) + 1

    def _analyze_go_tokens(self, code, start_offset, code_map):
        """Analyse les tokens Go pour la coloration en temps réel"""
        go_keywords = {
            "break",
            "case",
            "chan",
            "const",
            "continue",
            "default",
            "defer",
            "else",
            "fallthrough",
            "for",
            "func",
            "go",
            "goto",
            "if",
            "import",
            "interface",
            "map",
            "package",
            "range",
            "return",
            "select",
            "struct",
            "switch",
            "type",
            "var",
            "true",
            "false",
            "nil",
            "iota",
        }
        go_types = {
            "bool",
            "byte",
            "complex64",
            "complex128",
            "error",
            "float32",
            "float64",
            "int",
            "int8",
            "int16",
            "int32",
            "int64",
            "rune",
            "string",
            "uint",
            "uint8",
            "uint16",
            "uint32",
            "uint64",
            "uintptr",
        }
        go_builtins = {
            "append",
            "cap",
            "close",
            "complex",
            "copy",
            "delete",
            "imag",
            "len",
            "make",
            "new",
            "panic",
            "print",
            "println",
            "real",
            "recover",
        }

        token_pattern = r'(//.*$|/\*.*?\*/)|("(?:[^"\\]|\\.)*"|`[^`]*`)|(\b\d+\.?\d*\b)|(\b[a-zA-Z_]\w*\b)'

        lines = code.split("\n")
        current_pos = start_offset

        for line in lines:
            for match in re.finditer(token_pattern, line):
                value = match.group(0)
                match_start = current_pos + match.start()

                if match.group(1):  # Commentaire
                    tag = "go_comment"
                elif match.group(2):  # Chaîne
                    tag = "go_string"
                elif match.group(3):  # Nombre
                    tag = "go_number"
                elif match.group(4):  # Mot
                    if value in go_keywords:
                        tag = "go_keyword"
                    elif value in go_types:
                        tag = "go_type"
                    elif value in go_builtins:
                        tag = "go_function"
                    elif value in {"package", "import"}:
                        tag = "go_package"
                    else:
                        tag = "code_block"
                else:
                    tag = "code_block"

                for i in range(len(value)):
                    pos = match_start + i
                    code_map[pos] = ("go", tag)

            current_pos += len(line) + 1

    def _analyze_ruby_tokens(self, code, start_offset, code_map):
        """Analyse les tokens Ruby pour la coloration en temps réel"""
        ruby_keywords = {
            "alias",
            "and",
            "begin",
            "break",
            "case",
            "class",
            "def",
            "defined",
            "do",
            "else",
            "elsif",
            "end",
            "ensure",
            "false",
            "for",
            "if",
            "in",
            "module",
            "next",
            "nil",
            "not",
            "or",
            "redo",
            "rescue",
            "retry",
            "return",
            "self",
            "super",
            "then",
            "true",
            "undef",
            "unless",
            "until",
            "when",
            "while",
            "yield",
            "require",
            "include",
            "extend",
            "attr_accessor",
            "attr_reader",
            "attr_writer",
            "private",
            "protected",
            "public",
        }
        ruby_builtins = {
            "puts",
            "print",
            "gets",
            "chomp",
            "to_s",
            "to_i",
            "to_f",
            "to_a",
            "each",
            "map",
            "select",
            "reject",
            "reduce",
            "inject",
            "sort",
            "reverse",
        }

        token_pattern = r'(\#.*$)|("(?:[^"\\]|\\.)*"|\'(?:[^\'\\]|\\.)*\')|(\b\d+\.?\d*\b)|(:\w+)|(@{1,2}\w+)|(\b[a-zA-Z_]\w*[!?]?\b)'

        lines = code.split("\n")
        current_pos = start_offset

        for line in lines:
            for match in re.finditer(token_pattern, line):
                value = match.group(0)
                match_start = current_pos + match.start()

                if match.group(1):  # Commentaire
                    tag = "ruby_comment"
                elif match.group(2):  # Chaîne
                    tag = "ruby_string"
                elif match.group(3):  # Nombre
                    tag = "ruby_number"
                elif match.group(4):  # Symbol
                    tag = "ruby_symbol"
                elif match.group(5):  # Variable instance/classe
                    tag = "ruby_variable"
                elif match.group(6):  # Mot
                    if value in ruby_keywords:
                        tag = "ruby_keyword"
                    elif value in ruby_builtins:
                        tag = "ruby_method"
                    elif value[0].isupper():
                        tag = "ruby_class"
                    else:
                        tag = "code_block"
                else:
                    tag = "code_block"

                for i in range(len(value)):
                    pos = match_start + i
                    code_map[pos] = ("ruby", tag)

            current_pos += len(line) + 1

    def _analyze_swift_tokens(self, code, start_offset, code_map):
        """Analyse les tokens Swift pour la coloration en temps réel"""
        swift_keywords = {
            "associatedtype",
            "class",
            "deinit",
            "enum",
            "extension",
            "fileprivate",
            "func",
            "import",
            "init",
            "inout",
            "internal",
            "let",
            "open",
            "operator",
            "private",
            "protocol",
            "public",
            "rethrows",
            "static",
            "struct",
            "subscript",
            "typealias",
            "var",
            "break",
            "case",
            "continue",
            "default",
            "defer",
            "do",
            "else",
            "fallthrough",
            "for",
            "guard",
            "if",
            "in",
            "repeat",
            "return",
            "switch",
            "where",
            "while",
            "as",
            "catch",
            "is",
            "nil",
            "super",
            "self",
            "Self",
            "throw",
            "throws",
            "try",
            "true",
            "false",
            "async",
            "await",
        }
        swift_types = {
            "Any",
            "AnyObject",
            "Bool",
            "Character",
            "Double",
            "Float",
            "Int",
            "Int8",
            "Int16",
            "Int32",
            "Int64",
            "Never",
            "Optional",
            "String",
            "UInt",
            "UInt8",
            "UInt16",
            "UInt32",
            "UInt64",
            "Void",
            "Array",
            "Dictionary",
            "Set",
        }

        token_pattern = r'(//.*$|/\*.*?\*/)|("(?:[^"\\]|\\.)*")|(\b\d+\.?\d*\b)|(@\w+)|(\b[a-zA-Z_]\w*\b)'

        lines = code.split("\n")
        current_pos = start_offset

        for line in lines:
            for match in re.finditer(token_pattern, line):
                value = match.group(0)
                match_start = current_pos + match.start()

                if match.group(1):  # Commentaire
                    tag = "swift_comment"
                elif match.group(2):  # Chaîne
                    tag = "swift_string"
                elif match.group(3):  # Nombre
                    tag = "swift_number"
                elif match.group(4):  # Attribut
                    tag = "swift_attribute"
                elif match.group(5):  # Mot
                    if value in swift_keywords:
                        tag = "swift_keyword"
                    elif value in swift_types or value[0].isupper():
                        tag = "swift_type"
                    else:
                        tag = "code_block"
                else:
                    tag = "code_block"

                for i in range(len(value)):
                    pos = match_start + i
                    code_map[pos] = ("swift", tag)

            current_pos += len(line) + 1

    def _analyze_php_tokens(self, code, start_offset, code_map):
        """Analyse les tokens PHP pour la coloration en temps réel"""
        php_keywords = {
            "abstract",
            "and",
            "as",
            "break",
            "callable",
            "case",
            "catch",
            "class",
            "clone",
            "const",
            "continue",
            "declare",
            "default",
            "do",
            "else",
            "elseif",
            "enddeclare",
            "endfor",
            "endforeach",
            "endif",
            "endswitch",
            "endwhile",
            "extends",
            "final",
            "finally",
            "for",
            "foreach",
            "function",
            "global",
            "goto",
            "if",
            "implements",
            "include",
            "include_once",
            "instanceof",
            "insteadof",
            "interface",
            "namespace",
            "new",
            "or",
            "private",
            "protected",
            "public",
            "require",
            "require_once",
            "return",
            "static",
            "switch",
            "throw",
            "trait",
            "try",
            "use",
            "var",
            "while",
            "xor",
            "yield",
            "yield from",
            "true",
            "false",
            "null",
            "echo",
            "print",
        }
        php_builtins = {
            "array",
            "empty",
            "isset",
            "unset",
            "list",
            "die",
            "exit",
            "eval",
            "count",
            "strlen",
            "substr",
            "strpos",
            "str_replace",
            "explode",
            "implode",
        }

        token_pattern = r'(//.*$|\#.*$|/\*.*?\*/)|("(?:[^"\\]|\\.)*"|\'(?:[^\'\\]|\\.)*\')|(\b\d+\.?\d*\b)|(<\?php|\?>)|(\$[a-zA-Z_]\w*)|(\b[a-zA-Z_]\w*\b)'

        lines = code.split("\n")
        current_pos = start_offset

        for line in lines:
            for match in re.finditer(token_pattern, line):
                value = match.group(0)
                match_start = current_pos + match.start()

                if match.group(1):  # Commentaire
                    tag = "php_comment"
                elif match.group(2):  # Chaîne
                    tag = "php_string"
                elif match.group(3):  # Nombre
                    tag = "php_number"
                elif match.group(4):  # Tag PHP
                    tag = "php_tag"
                elif match.group(5):  # Variable
                    tag = "php_variable"
                elif match.group(6):  # Mot
                    if value.lower() in php_keywords:
                        tag = "php_keyword"
                    elif value.lower() in php_builtins:
                        tag = "php_function"
                    else:
                        tag = "code_block"
                else:
                    tag = "code_block"

                for i in range(len(value)):
                    pos = match_start + i
                    code_map[pos] = ("php", tag)

            current_pos += len(line) + 1

    def _analyze_perl_tokens(self, code, start_offset, code_map):
        """Analyse les tokens Perl pour la coloration en temps réel"""
        perl_keywords = {
            "my",
            "our",
            "local",
            "sub",
            "package",
            "use",
            "require",
            "no",
            "if",
            "elsif",
            "else",
            "unless",
            "while",
            "until",
            "for",
            "foreach",
            "do",
            "last",
            "next",
            "redo",
            "return",
            "goto",
            "die",
            "warn",
            "print",
            "say",
            "open",
            "close",
            "read",
            "write",
            "seek",
            "tell",
            "eof",
            "defined",
            "undef",
            "exists",
            "delete",
            "push",
            "pop",
            "shift",
            "unshift",
            "splice",
            "sort",
            "reverse",
            "keys",
            "values",
            "each",
            "length",
            "substr",
            "index",
            "rindex",
            "split",
            "join",
            "chomp",
            "chop",
            "lc",
            "uc",
            "scalar",
            "wantarray",
            "caller",
            "eval",
            "exec",
            "system",
            "fork",
            "wait",
            "exit",
        }

        token_pattern = r'(\#.*$)|("(?:[^"\\]|\\.)*"|\'(?:[^\'\\]|\\.)*\')|(\b\d+\.?\d*\b)|([\$@%]\w+)|(/(?:[^/\\]|\\.)+/[gimsx]*)|(\b[a-zA-Z_]\w*\b)'

        lines = code.split("\n")
        current_pos = start_offset

        for line in lines:
            for match in re.finditer(token_pattern, line):
                value = match.group(0)
                match_start = current_pos + match.start()

                if match.group(1):  # Commentaire
                    tag = "perl_comment"
                elif match.group(2):  # Chaîne
                    tag = "perl_string"
                elif match.group(3):  # Nombre
                    tag = "perl_number"
                elif match.group(4):  # Variable
                    tag = "perl_variable"
                elif match.group(5):  # Regex
                    tag = "perl_regex"
                elif match.group(6):  # Mot
                    if value in perl_keywords:
                        tag = "perl_keyword"
                    else:
                        tag = "code_block"
                else:
                    tag = "code_block"

                for i in range(len(value)):
                    pos = match_start + i
                    code_map[pos] = ("perl", tag)

            current_pos += len(line) + 1

    def _analyze_rust_tokens(self, code, start_offset, code_map):
        """Analyse les tokens Rust pour la coloration en temps réel"""
        rust_keywords = {
            "as",
            "async",
            "await",
            "break",
            "const",
            "continue",
            "crate",
            "dyn",
            "else",
            "enum",
            "extern",
            "false",
            "fn",
            "for",
            "if",
            "impl",
            "in",
            "let",
            "loop",
            "match",
            "mod",
            "move",
            "mut",
            "pub",
            "ref",
            "return",
            "self",
            "Self",
            "static",
            "struct",
            "super",
            "trait",
            "true",
            "type",
            "unsafe",
            "use",
            "where",
            "while",
            "abstract",
            "become",
            "box",
            "do",
            "final",
            "macro",
            "override",
            "priv",
            "typeof",
            "unsized",
            "virtual",
            "yield",
        }
        rust_types = {
            "bool",
            "char",
            "str",
            "i8",
            "i16",
            "i32",
            "i64",
            "i128",
            "isize",
            "u8",
            "u16",
            "u32",
            "u64",
            "u128",
            "usize",
            "f32",
            "f64",
            "String",
            "Vec",
            "Option",
            "Result",
            "Box",
            "Rc",
            "Arc",
            "Cell",
            "RefCell",
            "HashMap",
            "HashSet",
            "BTreeMap",
            "BTreeSet",
            "VecDeque",
            "LinkedList",
        }

        token_pattern = r'(//.*$|/\*.*?\*/)|("(?:[^"\\]|\\.)*"|r#*"[^"]*"#*)|(\b\d+\.?\d*(?:_\d+)*(?:i8|i16|i32|i64|i128|isize|u8|u16|u32|u64|u128|usize|f32|f64)?\b)|(\'[a-zA-Z_]\w*)|(\b[a-zA-Z_]\w*!)|(\b[a-zA-Z_]\w*\b)'

        lines = code.split("\n")
        current_pos = start_offset

        for line in lines:
            for match in re.finditer(token_pattern, line):
                value = match.group(0)
                match_start = current_pos + match.start()

                if match.group(1):  # Commentaire
                    tag = "rust_comment"
                elif match.group(2):  # Chaîne
                    tag = "rust_string"
                elif match.group(3):  # Nombre
                    tag = "rust_number"
                elif match.group(4):  # Lifetime 'a
                    tag = "rust_lifetime"
                elif match.group(5):  # Macro println!
                    tag = "rust_macro"
                elif match.group(6):  # Mot
                    if value in rust_keywords:
                        tag = "rust_keyword"
                    elif value in rust_types or (
                        value[0].isupper() and not value.isupper()
                    ):
                        tag = "rust_type"
                    else:
                        tag = "code_block"
                else:
                    tag = "code_block"

                for i in range(len(value)):
                    pos = match_start + i
                    code_map[pos] = ("rust", tag)

            current_pos += len(line) + 1

    def _split_text_for_progressive_formatting(self, text):
        """Divise le texte en segments plus larges pour une animation fluide"""
        segments = []

        # Diviser par phrases ou groupes de mots (5-10 caractères par segment)
        words = re.findall(r"\S+\s*", text)

        current_segment = ""
        target_length = 8  # Caractères par segment pour une animation fluide

        for word in words:
            # Si ajouter ce mot dépasse la longueur cible, finir le segment actuel
            if len(current_segment) + len(word) > target_length and current_segment:
                segments.append(current_segment)
                current_segment = word
            else:
                current_segment += word

        # Ajouter le dernier segment s'il existe
        if current_segment:
            segments.append(current_segment)

        # Nettoyer les segments vides
        segments = [s for s in segments if s.strip()]

        return segments

    def continue_typing_animation_dynamic(self):
        """Animation caractère par caractère avec formatage progressif UNIFIÉ"""
        if not hasattr(self, "typing_widget") or not hasattr(self, "typing_text"):
            return

        if getattr(self, "_typing_interrupted", False):
            self.finish_typing_animation_dynamic(interrupted=True)
            return

        # Vérifier si on a terminé
        if self.typing_index >= len(self.typing_text):
            self.finish_typing_animation_dynamic()
            return

        try:
            # Ajouter le caractère suivant
            char = self.typing_text[self.typing_index]

            self.typing_widget.configure(state="normal")

            # NOUVEAU : Déterminer le tag à utiliser selon la position
            tag_to_use = "normal"  # Tag par défaut

            # Vérifier si ce caractère est dans un bloc de code
            if (
                hasattr(self, "_code_blocks_map")
                and self.typing_index in self._code_blocks_map
            ):
                _language, token_type = self._code_blocks_map[self.typing_index]

                # Masquer les marqueurs de blocs de code (```)
                if token_type == "code_block_marker":
                    tag_to_use = "hidden"  # Les ``` seront cachés
                else:
                    tag_to_use = token_type  # Utiliser le tag de coloration syntaxique

            # Insérer le caractère avec le bon tag
            self.typing_widget.insert("end", char, tag_to_use)

            # La coloration est déjà appliquée via _code_blocks_map, pas besoin de _apply_realtime_syntax_coloring

            # Incrémenter l'index
            self.typing_index += 1

            # FORMATAGE PROGRESSIF INTELLIGENT
            should_format = False

            # Détecter completion d'éléments markdown UNIQUEMENT pour les vrais patterns
            if char == "*":
                current_content = self.typing_widget.get("1.0", "end-1c")
                # Ne formater QUE si on a un vrai pattern **texte**
                if current_content.endswith("**") and len(current_content) >= 4:
                    # Vérifier qu'il y a vraiment un pattern **texte** complet
                    # Chercher le dernier pattern **texte** complet dans le contenu
                    bold_pattern = r"\*\*([^*\n]{1,200}?)\*\*$"
                    if re.search(bold_pattern, current_content):
                        should_format = True
                    else:
                        pass
            elif char == "`":
                # Fin possible de `code` - vérifier que c'est un vrai pattern
                current_content = self.typing_widget.get("1.0", "end-1c")
                code_pattern = r"`([^`\n]+)`$"
                if re.search(code_pattern, current_content):
                    should_format = True
                else:
                    pass
            elif char == "'":
                # Fin possible de '''docstring''' - vérifier qu'on a 3 quotes
                current_content = self.typing_widget.get("1.0", "end-1c")
                if current_content.endswith("'''"):
                    docstring_pattern = r"'''([^']*?)'''$"
                    if re.search(docstring_pattern, current_content, re.DOTALL):
                        should_format = True
                    else:
                        pass
            elif char == " ":
                # NE PAS formater pendant l'écriture d'un titre - attendre la fin de ligne
                # Ancien code qui causait le formatage partiel des titres
                pass  # On attend le \n pour formater les titres complets
            elif char == "\n":
                # Nouvelle ligne - MAINTENANT on peut formater les titres complets
                should_format = True

                # Vérifier si on vient de terminer une ligne de tableau
                self._check_and_format_table_line(self.typing_widget, self.typing_index)

            elif self.typing_index % 100 == 0:  # ⚡ OPTIMISÉ: Formatage tous les 100 caractères (au lieu de 50)
                should_format = True

            # Appliquer le formatage unifié si nécessaire
            if should_format:
                self._apply_unified_progressive_formatting(self.typing_widget)

            # Ajuster la hauteur aux retours à la ligne
            if char == "\n":
                self.adjust_text_widget_height(self.typing_widget)
                self.root.after(5, self._smart_scroll_follow_animation)

            self.typing_widget.configure(state="disabled")

            # Planifier le prochain caractère (animation fluide)
            delay = 10
            self.root.after(delay, self.continue_typing_animation_dynamic)

        except tk.TclError:
            self.finish_typing_animation_dynamic(interrupted=True)

    def _apply_realtime_syntax_coloring(self, text_widget, current_index):
        """Applique la coloration syntaxique en temps réel pendant l'animation"""
        try:
            # Obtenir le contenu actuel
            current_text = text_widget.get("1.0", "end-1c")

            # Détecter si on est dans un bloc de code
            in_code_block, language, _block_start = self._detect_current_code_block(
                current_text, current_index
            )

            if in_code_block and language:
                # Récupérer juste le bout de code qui nous intéresse (derniers mots/tokens)
                analysis_start = max(
                    0, current_index - 50
                )  # Analyser les 50 derniers caractères
                text_to_analyze = current_text[analysis_start : current_index + 1]

                # Appliquer la coloration selon le langage
                if language == "python":
                    self._apply_python_realtime_coloring(
                        text_widget, text_to_analyze, analysis_start
                    )
                elif language in ["javascript", "js"]:
                    self._apply_javascript_realtime_coloring(
                        text_widget, text_to_analyze, analysis_start
                    )
                elif language == "css":
                    self._apply_css_realtime_coloring(
                        text_widget, text_to_analyze, analysis_start
                    )
                elif language in ["html", "xml"]:
                    self._apply_html_realtime_coloring(
                        text_widget, text_to_analyze, analysis_start
                    )
                elif language in ["bash", "shell", "sh"]:
                    self._apply_bash_realtime_coloring(
                        text_widget, text_to_analyze, analysis_start
                    )
                elif language in ["sql", "mysql", "postgresql", "sqlite"]:
                    self._apply_sql_realtime_coloring(
                        text_widget, text_to_analyze, analysis_start
                    )

        except Exception:
            # Ignorer les erreurs de coloration pour ne pas casser l'animation
            pass

    def _check_and_format_table_line(self, text_widget, current_pos):
        """Vérifie si on vient de terminer un tableau complet et le formate"""
        if not hasattr(self, "_table_blocks") or not self._table_blocks:
            return

        if not hasattr(self, "_formatted_tables"):
            self._formatted_tables = set()

        # Vérifier si on vient de terminer un tableau
        for table_idx, table in enumerate(self._table_blocks):
            if table_idx in self._formatted_tables:
                continue  # Déjà formaté

            # Vérifier si le tableau a ARRÊTÉ de grandir
            # On regarde si end_line a changé depuis le dernier appel
            prev_end_line = self._table_blocks_history.get(table_idx, -1)
            current_end_line = table["end_line"]

            # Mettre à jour l'historique
            self._table_blocks_history[table_idx] = current_end_line

            # Si c'est la première fois qu'on voit ce tableau, ne pas formater encore
            if prev_end_line == -1:
                continue

            # Si le tableau a grandi depuis le dernier appel, ne pas formater encore
            if current_end_line > prev_end_line:
                print(
                    f"[DEBUG] Tableau {table_idx} grandit encore : ligne {prev_end_line} -> {current_end_line}"
                )
                continue

            # Si on est ici, le tableau n'a PAS grandi depuis le dernier appel
            # Vérifier qu'on a dépassé la fin du tableau ET qu'il y a une ligne non-tableau après
            if current_pos >= table["end_pos"]:
                buffer_text = self._streaming_buffer[:current_pos]
                lines = buffer_text.split("\n")

                # Vérifier qu'on a au moins 1 ligne après le tableau
                lines_after_table = len(lines) - table["end_line"] - 1

                if lines_after_table >= 1:
                    # Vérifier que cette ligne ne contient pas de |
                    if table["end_line"] + 1 < len(lines):
                        first_line_after = lines[table["end_line"] + 1]
                        if "|" not in first_line_after:
                            # Le tableau est stable et terminé
                            self._formatted_tables.add(table_idx)
                            self._format_completed_table(text_widget, table)
                            break  # Un seul tableau à la fois

    def _format_completed_table(self, text_widget, table_info):
        """Formate un tableau complet dans le widget"""
        try:
            text_widget.configure(state="normal")

            # Récupérer le contenu actuel du widget
            content = text_widget.get("1.0", "end-1c")
            widget_lines = content.split("\n")

            # Extraire les lignes brutes du tableau depuis le texte original
            raw_table_lines = [
                line_info["content"] for line_info in table_info["lines"]
            ]

            if len(raw_table_lines) < 2:
                text_widget.configure(state="disabled")
                return

            # Trouver où se trouve ce tableau dans le widget actuel
            # Chercher la première ligne du tableau (header)
            header_content = raw_table_lines[0].strip()
            table_start_widget_line = None

            for idx, wline in enumerate(widget_lines):
                # Chercher une ligne qui contient | et correspond au header
                if "|" in wline and not any(c in wline for c in "┌┬┐│├┼┤└┴┘─"):
                    # Vérifier si c'est bien notre tableau en comparant le contenu
                    if self._lines_match(wline.strip(), header_content):
                        table_start_widget_line = idx
                        break

            if table_start_widget_line is None:
                text_widget.configure(state="disabled")
                return

            # Compter combien de lignes brutes consécutives avec | on a
            table_end_widget_line = table_start_widget_line
            for idx in range(table_start_widget_line, len(widget_lines)):
                if "|" in widget_lines[idx] and not any(
                    c in widget_lines[idx] for c in "┌┬┐│├┼┤└┴┘─"
                ):
                    table_end_widget_line = idx
                else:
                    break

            # Supprimer les lignes brutes du tableau
            start_line_tk = f"{table_start_widget_line + 1}.0"
            end_line_tk = f"{table_end_widget_line + 2}.0"
            text_widget.delete(start_line_tk, end_line_tk)

            # Positionner le curseur pour l'insertion
            text_widget.mark_set("insert", start_line_tk)

            # Insérer le tableau formaté
            self._insert_formatted_table(text_widget, raw_table_lines)

            text_widget.configure(state="disabled")

        except Exception as e:
            print(f"[DEBUG] Erreur formatage tableau: {e}")
            try:
                text_widget.configure(state="disabled")
            except Exception:
                pass

    def _lines_match(self, line1, line2):
        """Vérifie si deux lignes de tableau correspondent (même contenu de cellules)"""
        cells1 = self._parse_table_row(line1)
        cells2 = self._parse_table_row(line2)
        return cells1 == cells2

    def _insert_table_cell_content(self, text_widget, cell_content, is_header):
        """Insère le contenu d'une cellule avec support complet des formattages markdown"""
        if not cell_content:
            return

        # Appliquer les formattages markdown dans l'ordre de priorité
        # 1. Gras **texte**
        # 2. Code `texte`
        # 3. Texte normal

        parts = []
        current_pos = 0

        # Pattern pour détecter les formattages
        # On cherche soit **texte** soit `code`
        format_pattern = r"(\*\*[^*\n]+\*\*|`[^`\n]+`)"

        for match in re.finditer(format_pattern, cell_content):
            # Texte avant le format
            if match.start() > current_pos:
                parts.append(("normal", cell_content[current_pos : match.start()]))

            # Contenu formaté
            matched_text = match.group(0)
            if matched_text.startswith("**") and matched_text.endswith("**"):
                # Gras
                parts.append(("bold", matched_text[2:-2]))
            elif matched_text.startswith("`") and matched_text.endswith("`"):
                # Code
                parts.append(("code", matched_text[1:-1]))
            else:
                parts.append(("normal", matched_text))

            current_pos = match.end()

        # Texte restant
        if current_pos < len(cell_content):
            parts.append(("normal", cell_content[current_pos:]))

        # Insérer les parties avec leurs tags
        for part_type, part_text in parts:
            if part_type == "bold":
                if is_header:
                    text_widget.insert("insert", part_text, "table_header")
                else:
                    text_widget.insert("insert", part_text, "table_cell_bold")
            elif part_type == "code":
                text_widget.insert("insert", part_text, "code")
            else:
                if is_header:
                    text_widget.insert("insert", part_text, "table_header")
                else:
                    text_widget.insert("insert", part_text, "table_cell")

    def _insert_formatted_table(self, text_widget, raw_lines):
        """Insère un tableau complètement formaté avec support des formattages markdown"""
        separator_pattern = r"^\|?[\s\-:|\s]+\|?$"

        # Calculer les largeurs de colonnes (en comptant le texte sans les marqueurs markdown)
        all_cells = []
        for line_content in raw_lines:
            if re.match(separator_pattern, line_content.strip()):
                continue
            cells = self._parse_table_row(line_content)
            all_cells.append(cells)

        if not all_cells:
            return

        max_cols = max(len(row) for row in all_cells)
        widths = []
        for col in range(max_cols):
            max_width = 0
            for row in all_cells:
                if col < len(row):
                    # Enlever tous les marqueurs markdown pour calculer la largeur
                    cell_text = re.sub(r"\*\*([^*]+)\*\*", r"\1", row[col])
                    cell_text = re.sub(r"`([^`]+)`", r"\1", cell_text)
                    max_width = max(max_width, len(cell_text))
            widths.append(max(max_width, 3))

        # Bordure supérieure
        border_top = "┌" + "┬".join("─" * (w + 2) for w in widths) + "┐\n"
        text_widget.insert("insert", border_top, "table_border")

        for line_idx, line_content in enumerate(raw_lines):
            if line_idx == 1:  # Séparateur
                sep_line = "├" + "┼".join("─" * (w + 2) for w in widths) + "┤\n"
                text_widget.insert("insert", sep_line, "table_border")
                continue

            cells = self._parse_table_row(line_content)
            is_header = line_idx == 0

            text_widget.insert("insert", "│", "table_border")

            for col_idx, width in enumerate(widths):
                cell_content = cells[col_idx] if col_idx < len(cells) else ""

                # Calculer la longueur d'affichage (sans les marqueurs)
                display_length = len(re.sub(r"\*\*([^*]+)\*\*", r"\1", cell_content))
                display_length = len(
                    re.sub(
                        r"`([^`]+)`",
                        r"\1",
                        re.sub(r"\*\*([^*]+)\*\*", r"\1", cell_content),
                    )
                )

                padding = width - display_length
                left_pad = padding // 2
                right_pad = padding - left_pad

                text_widget.insert("insert", " " + " " * left_pad, "table_border")

                # Insérer le contenu avec formatage
                self._insert_table_cell_content(text_widget, cell_content, is_header)

                text_widget.insert("insert", " " * right_pad + " ", "table_border")
                text_widget.insert("insert", "│", "table_border")

            text_widget.insert("insert", "\n")

        # Bordure inférieure
        border_bottom = "└" + "┴".join("─" * (w + 2) for w in widths) + "┘\n"
        text_widget.insert("insert", border_bottom, "table_border")

    def _detect_current_code_block(self, text, current_index):
        """Détecte si on est actuellement dans un bloc de code et retourne le langage"""
        # Chercher tous les blocs de code jusqu'à la position actuelle
        text_up_to_current = text[: current_index + 1]

        # Pattern pour détecter les blocs de code
        # CORRECTION: Capturer aussi les + pour c++, et # pour c#
        code_block_pattern = r"```([\w+#-]+)?\n?(.*?)(?:```|$)"

        # Trouver tous les blocs de code
        blocks = list(re.finditer(code_block_pattern, text_up_to_current, re.DOTALL))

        for block in reversed(blocks):  # Commencer par le dernier bloc
            language = (block.group(1) or "text").lower()

            # Vérifier si on est dans ce bloc
            content_start = block.start() + len(f"```{block.group(1) or ''}")
            # Trouver le newline après ```language
            newline_pos = text_up_to_current.find("\n", content_start)
            if newline_pos != -1:
                content_start = newline_pos + 1

            # Si la position actuelle est dans ce bloc et qu'il n'est pas fermé
            if (
                content_start <= current_index
                and not text_up_to_current[block.start() :].count("```") >= 2
            ):
                return True, language, content_start

        return False, None, None

    def _apply_python_realtime_coloring(self, text_widget, text_segment, start_offset):
        """Applique la coloration Python en temps réel sur un segment de texte"""
        # Mots-clés Python
        python_keywords = set(keyword.kwlist)
        python_builtins = {
            "print",
            "len",
            "str",
            "int",
            "float",
            "list",
            "dict",
            "set",
            "tuple",
            "range",
            "enumerate",
            "zip",
            "open",
            "input",
            "type",
            "isinstance",
            "hasattr",
            "getattr",
            "setattr",
        }

        # Patterns pour différents éléments
        patterns = [
            (r"#.*$", "Token.Comment"),  # Commentaires
            (r'""".*?"""', "docstring"),  # Docstrings
            (r'"(?:[^"\\]|\\.)*"', "Token.Literal.String"),  # Chaînes double quotes
            (r"'(?:[^'\\]|\\.)*'", "Token.Literal.String"),  # Chaînes simple quotes
            (r"\b\d+\.?\d*\b", "Token.Literal.Number"),  # Nombres
            (r"\b[a-zA-Z_]\w*\b", "identifier"),  # Identifiants
        ]

        # Analyser chaque pattern
        for pattern, token_type in patterns:
            for match in re.finditer(pattern, text_segment, re.MULTILINE):
                match_start = start_offset + match.start()
                match_end = start_offset + match.end()

                # Convertir en positions Tkinter
                start_line, start_col = self._index_to_line_col(
                    text_widget, match_start
                )
                end_line, end_col = self._index_to_line_col(text_widget, match_end)

                start_pos = f"{start_line}.{start_col}"
                end_pos = f"{end_line}.{end_col}"

                # Déterminer le tag final
                final_tag = token_type
                if token_type == "identifier":
                    word = match.group()
                    if word in python_keywords:
                        final_tag = "Token.Keyword"
                    elif word in python_builtins:
                        final_tag = "Token.Name.Builtin"
                    else:
                        final_tag = "Token.Name"

                # Appliquer le tag
                try:
                    text_widget.tag_add(final_tag, start_pos, end_pos)
                except Exception:
                    pass

    def _apply_javascript_realtime_coloring(
        self, text_widget, text_segment, start_offset
    ):
        """Applique la coloration JavaScript en temps réel"""
        js_keywords = {
            "var",
            "let",
            "const",
            "function",
            "return",
            "if",
            "else",
            "for",
            "while",
            "do",
            "switch",
            "case",
            "default",
            "break",
            "continue",
            "try",
            "catch",
            "finally",
            "throw",
            "new",
            "this",
            "super",
            "class",
            "extends",
            "import",
            "export",
            "from",
            "async",
            "await",
            "yield",
            "typeof",
            "instanceof",
            "in",
            "of",
            "true",
            "false",
            "null",
            "undefined",
        }

        patterns = [
            (r"//.*$", "Token.Comment"),
            (r"/\*.*?\*/", "Token.Comment"),
            (r'"(?:[^"\\]|\\.)*"', "Token.Literal.String"),
            (r"'(?:[^'\\]|\\.)*'", "Token.Literal.String"),
            (r"`(?:[^`\\]|\\.)*`", "Token.Literal.String"),
            (r"\b\d+\.?\d*\b", "Token.Literal.Number"),
            (r"\b[a-zA-Z_$]\w*\b", "identifier"),
        ]

        for pattern, token_type in patterns:
            for match in re.finditer(pattern, text_segment, re.MULTILINE):
                match_start = start_offset + match.start()
                match_end = start_offset + match.end()

                start_line, start_col = self._index_to_line_col(
                    text_widget, match_start
                )
                end_line, end_col = self._index_to_line_col(text_widget, match_end)

                start_pos = f"{start_line}.{start_col}"
                end_pos = f"{end_line}.{end_col}"

                final_tag = token_type
                if token_type == "identifier":
                    word = match.group()
                    if word in js_keywords:
                        final_tag = "Token.Keyword"
                    else:
                        final_tag = "Token.Name"

                try:
                    text_widget.tag_add(final_tag, start_pos, end_pos)
                except Exception:
                    pass

    def _apply_css_realtime_coloring(self, text_widget, text_segment, start_offset):
        """Applique la coloration CSS en temps réel"""
        css_properties = {
            "color",
            "background",
            "font-size",
            "margin",
            "padding",
            "border",
            "width",
            "height",
            "display",
            "position",
            "top",
            "left",
            "right",
            "bottom",
            "z-index",
            "opacity",
            "transform",
            "transition",
            "animation",
            "flex",
            "grid",
        }
        css_values = {
            "auto",
            "none",
            "inherit",
            "initial",
            "unset",
            "block",
            "inline",
            "flex",
            "grid",
            "absolute",
            "relative",
            "fixed",
            "sticky",
            "hidden",
            "visible",
        }
        _css_pseudos = {
            "hover",
            "active",
            "focus",
            "visited",
            "first-child",
            "last-child",
            "nth-child",
            "before",
            "after",
        }

        patterns = [
            (r"/\*.*?\*/", "Token.Comment"),  # Commentaires /* */
            (r'"(?:[^"\\]|\\.)*"', "Token.Literal.String"),  # Chaînes double quotes
            (r"'(?:[^'\\]|\\.)*'", "Token.Literal.String"),  # Chaînes simple quotes
            (r"#[0-9a-fA-F]{3,6}\b", "Token.Literal.Number"),  # Couleurs hexadécimales
            (r"\b\d+(?:px|em|rem|%|vh|vw|pt)?\b", "Token.Literal.Number"),  # Dimensions
            (r"\.[a-zA-Z_][\w-]*", "Token.Name.Class"),  # Sélecteurs de classe .class
            (r"#[a-zA-Z_][\w-]*", "Token.Name.Variable"),  # Sélecteurs d'ID #id
            (r":[a-zA-Z-]+", "Token.Name.Function"),  # Pseudo-sélecteurs :hover
            (r"[a-zA-Z-]+(?=\s*:)", "Token.Name.Attribute"),  # Propriétés CSS
            (r"\b[a-zA-Z_][\w-]*\b", "identifier"),  # Identifiants
        ]

        for pattern, token_type in patterns:
            for match in re.finditer(pattern, text_segment, re.MULTILINE):
                match_start = start_offset + match.start()
                match_end = start_offset + match.end()

                start_line, start_col = self._index_to_line_col(
                    text_widget, match_start
                )
                end_line, end_col = self._index_to_line_col(text_widget, match_end)

                start_pos = f"{start_line}.{start_col}"
                end_pos = f"{end_line}.{end_col}"

                final_tag = token_type
                if token_type == "identifier":
                    word = match.group()
                    if word in css_properties:
                        final_tag = (
                            "Token.Name.Attribute"  # Propriétés en couleur attribut
                        )
                    elif word in css_values:
                        final_tag = "Token.Keyword"  # Valeurs en couleur keyword
                    else:
                        final_tag = "Token.Name"

                try:
                    text_widget.tag_add(final_tag, start_pos, end_pos)
                except Exception:
                    pass

    def _apply_html_realtime_coloring(self, text_widget, text_segment, start_offset):
        """Applique la coloration HTML en temps réel"""
        _html_tags = {
            "html",
            "head",
            "body",
            "title",
            "meta",
            "link",
            "script",
            "style",
            "div",
            "span",
            "p",
            "h1",
            "h2",
            "h3",
            "h4",
            "h5",
            "h6",
            "a",
            "img",
            "ul",
            "ol",
            "li",
            "table",
            "tr",
            "td",
            "th",
            "form",
            "input",
            "button",
            "textarea",
            "select",
            "option",
            "nav",
            "header",
            "footer",
            "section",
            "article",
            "aside",
            "main",
        }
        _html_attributes = {
            "id",
            "class",
            "src",
            "href",
            "alt",
            "title",
            "style",
            "type",
            "name",
            "value",
            "placeholder",
            "required",
            "disabled",
            "readonly",
            "checked",
            "selected",
        }

        patterns = [
            (r"<!--.*?-->", "Token.Comment"),  # Commentaires HTML
            (
                r'"(?:[^"\\]|\\.)*"',
                "Token.Literal.String",
            ),  # Chaînes double quotes (valeurs d'attributs)
            (r"'(?:[^'\\]|\\.)*'", "Token.Literal.String"),  # Chaînes simple quotes
            (r"<!\s*DOCTYPE[^>]*>", "Token.Keyword"),  # DOCTYPE
            (r"</?[a-zA-Z][a-zA-Z0-9]*", "Token.Name.Tag"),  # Balises <div>, </div>
            (r"\b[a-zA-Z-]+(?=\s*=)", "Token.Name.Attribute"),  # Attributs HTML
            (r"[&][a-zA-Z]+[;]", "Token.Name.Entity"),  # Entités HTML &nbsp;
            (r"[<>=/]", "Token.Operator"),  # Opérateurs HTML
        ]

        for pattern, token_type in patterns:
            for match in re.finditer(pattern, text_segment, re.MULTILINE | re.DOTALL):
                match_start = start_offset + match.start()
                match_end = start_offset + match.end()

                start_line, start_col = self._index_to_line_col(
                    text_widget, match_start
                )
                end_line, end_col = self._index_to_line_col(text_widget, match_end)

                start_pos = f"{start_line}.{start_col}"
                end_pos = f"{end_line}.{end_col}"

                final_tag = token_type

                try:
                    text_widget.tag_add(final_tag, start_pos, end_pos)
                except Exception:
                    pass

    def _apply_bash_realtime_coloring(self, text_widget, text_segment, start_offset):
        """Applique la coloration Bash en temps réel"""
        bash_keywords = {
            "if",
            "then",
            "else",
            "elif",
            "fi",
            "for",
            "while",
            "do",
            "done",
            "case",
            "esac",
            "function",
            "return",
            "exit",
            "break",
            "continue",
            "local",
            "export",
            "declare",
            "readonly",
            "unset",
            "source",
            "alias",
            "history",
            "jobs",
            "bg",
            "fg",
            "nohup",
            "disown",
        }
        bash_commands = {
            "ls",
            "cd",
            "pwd",
            "mkdir",
            "rmdir",
            "rm",
            "cp",
            "mv",
            "touch",
            "find",
            "grep",
            "sed",
            "awk",
            "sort",
            "uniq",
            "head",
            "tail",
            "cat",
            "less",
            "more",
            "chmod",
            "chown",
            "ps",
            "top",
            "kill",
            "jobs",
            "wget",
            "curl",
            "ssh",
            "scp",
            "rsync",
            "tar",
            "gzip",
            "gunzip",
            "zip",
            "unzip",
            "git",
            "npm",
            "pip",
            "docker",
            "sudo",
            "su",
            "which",
            "whereis",
            "man",
            "info",
            "help",
            "echo",
            "printf",
            "read",
            "test",
        }

        patterns = [
            (r"#.*$", "Token.Comment"),  # Commentaires
            (r'"(?:[^"\\]|\\.)*"', "Token.Literal.String"),  # Chaînes double quotes
            (r"'(?:[^'\\]|\\.)*'", "Token.Literal.String"),  # Chaînes simple quotes
            (r"`(?:[^`\\]|\\.)*`", "Token.Literal.String"),  # Commandes entre backticks
            (r"\$\{[^}]+\}", "Token.Name.Variable"),  # Variables ${var}
            (r"\$[a-zA-Z_][a-zA-Z0-9_]*", "Token.Name.Variable"),  # Variables $var
            (r"\$[0-9]+", "Token.Name.Variable"),  # Arguments $1, $2, etc.
            (r"\$[@*#?$!0]", "Token.Name.Variable"),  # Variables spéciales $@, $*, etc.
            (r"\b\d+\b", "Token.Literal.Number"),  # Nombres
            (r"[|&;()<>]|\|\||\&\&", "Token.Operator"),  # Opérateurs
            (r"--?[a-zA-Z-]+", "Token.Name.Attribute"),  # Options --option, -o
            (r"\b[a-zA-Z_][a-zA-Z0-9_]*\b", "identifier"),  # Identifiants
        ]

        for pattern, token_type in patterns:
            for match in re.finditer(pattern, text_segment, re.MULTILINE):
                match_start = start_offset + match.start()
                match_end = start_offset + match.end()

                start_line, start_col = self._index_to_line_col(
                    text_widget, match_start
                )
                end_line, end_col = self._index_to_line_col(text_widget, match_end)

                start_pos = f"{start_line}.{start_col}"
                end_pos = f"{end_line}.{end_col}"

                final_tag = token_type
                if token_type == "identifier":
                    word = match.group()
                    if word in bash_keywords:
                        final_tag = "Token.Keyword"
                    elif word in bash_commands:
                        final_tag = "Token.Name.Builtin"  # Commandes en couleur builtin
                    else:
                        final_tag = "Token.Name"

                try:
                    text_widget.tag_add(final_tag, start_pos, end_pos)
                except Exception:
                    pass

    def _apply_sql_realtime_coloring(self, text_widget, text_segment, start_offset):
        """Applique la coloration SQL en temps réel"""
        sql_keywords = {
            "SELECT",
            "FROM",
            "WHERE",
            "INSERT",
            "UPDATE",
            "DELETE",
            "CREATE",
            "DROP",
            "ALTER",
            "TABLE",
            "DATABASE",
            "INDEX",
            "VIEW",
            "PROCEDURE",
            "FUNCTION",
            "TRIGGER",
            "JOIN",
            "INNER",
            "LEFT",
            "RIGHT",
            "FULL",
            "OUTER",
            "ON",
            "AS",
            "AND",
            "OR",
            "NOT",
            "IN",
            "BETWEEN",
            "LIKE",
            "IS",
            "NULL",
            "GROUP",
            "BY",
            "ORDER",
            "HAVING",
            "LIMIT",
            "OFFSET",
            "UNION",
            "DISTINCT",
            "COUNT",
            "SUM",
            "AVG",
            "MIN",
            "MAX",
            "CASE",
            "WHEN",
            "THEN",
            "ELSE",
            "END",
            "IF",
            "EXISTS",
        }
        sql_types = {
            "INT",
            "INTEGER",
            "VARCHAR",
            "CHAR",
            "TEXT",
            "BOOLEAN",
            "BOOL",
            "DATE",
            "DATETIME",
            "TIMESTAMP",
            "TIME",
            "FLOAT",
            "DOUBLE",
            "DECIMAL",
            "NUMERIC",
            "BLOB",
            "JSON",
            "XML",
        }

        patterns = [
            (r"--.*$", "Token.Comment"),  # Commentaires --
            (r"/\*.*?\*/", "Token.Comment"),  # Commentaires /* */
            (r"'(?:[^'\\]|\\.)*'", "Token.Literal.String"),  # Chaînes simple quotes
            (r'"(?:[^"\\]|\\.)*"', "Token.Literal.String"),  # Chaînes double quotes
            (r"\b\d+\.?\d*\b", "Token.Literal.Number"),  # Nombres
            (r"[=<>!]+|<=|>=|<>|!=", "Token.Operator"),  # Opérateurs de comparaison
            (r"[+\-*/%]", "Token.Operator"),  # Opérateurs arithmétiques
            (r"[(),;]", "Token.Punctuation"),  # Ponctuation
            (r"\b[a-zA-Z_][a-zA-Z0-9_]*\b", "identifier"),  # Identifiants
        ]

        for pattern, token_type in patterns:
            for match in re.finditer(pattern, text_segment, re.MULTILINE | re.DOTALL):
                match_start = start_offset + match.start()
                match_end = start_offset + match.end()

                start_line, start_col = self._index_to_line_col(
                    text_widget, match_start
                )
                end_line, end_col = self._index_to_line_col(text_widget, match_end)

                start_pos = f"{start_line}.{start_col}"
                end_pos = f"{end_line}.{end_col}"

                final_tag = token_type
                if token_type == "identifier":
                    word = match.group().upper()  # SQL est case-insensitive
                    if word in sql_keywords:
                        final_tag = "Token.Keyword"
                    elif word in sql_types:
                        final_tag = "Token.Keyword.Type"
                    else:
                        final_tag = "Token.Name"

                try:
                    text_widget.tag_add(final_tag, start_pos, end_pos)
                except Exception:
                    pass

    def _index_to_line_col(self, text_widget, char_index):
        """Convertit un index de caractère en position ligne.colonne pour Tkinter"""
        try:
            # Obtenir le contenu jusqu'à cet index
            content = text_widget.get("1.0", "end-1c")
            if char_index >= len(content):
                char_index = len(content) - 1

            # Compter les lignes et colonnes
            content_up_to_index = content[:char_index]
            lines = content_up_to_index.split("\n")
            line_num = len(lines)
            col_num = len(lines[-1]) if lines else 0

            return line_num, col_num
        except Exception:
            return 1, 0

    def _is_position_in_code_block(self, text_widget, position):
        """Vérifie si une position est dans un bloc de code en regardant les tags appliqués"""
        try:
            tags = text_widget.tag_names(position)
            # Liste des tags qui indiquent qu'on est dans un bloc de code
            code_tags = {
                "code_block",
                "code_block_marker",
                "hidden",
                # Python tokens
                "Token.Keyword",
                "Token.Literal.String",
                "Token.Comment.Single",
                "Token.Literal.Number",
                "Token.Name.Function",
                "Token.Name.Class",
                "Token.Name.Builtin",
                "Token.Operator",
                "Token.Punctuation",
                "Token.Name",
                "Token.Name.Variable",
                "Token.Name.Attribute",
                "Token.Comment",
                "Token.Comment.Multiline",
                "Token.String",
                # JavaScript
                "js_keyword",
                "js_string",
                "js_comment",
                "js_number",
                "js_variable",
                "js_operator",
                "js_function",
                # CSS
                "css_selector",
                "css_property",
                "css_value",
                "css_comment",
                "css_unit",
                # HTML
                "html_tag",
                "html_attribute",
                "html_value",
                "html_comment",
                # Bash
                "bash_keyword",
                "bash_command",
                "bash_string",
                "bash_comment",
                "bash_variable",
                # SQL
                "sql_keyword",
                "sql_function",
                "sql_string",
                "sql_comment",
                "sql_number",
                # Java
                "java_keyword",
                "java_string",
                "java_comment",
                "java_number",
                "java_class",
                "java_method",
                "java_annotation",
                # C/C++
                "cpp_keyword",
                "cpp_string",
                "cpp_comment",
                "cpp_number",
                "cpp_preprocessor",
                "cpp_type",
                "cpp_function",
                # C
                "c_keyword",
                "c_string",
                "c_comment",
                "c_number",
                "c_preprocessor",
                "c_type",
                "c_function",
                # C#
                "csharp_keyword",
                "csharp_string",
                "csharp_comment",
                "csharp_number",
                "csharp_class",
                "csharp_method",
                # Go
                "go_keyword",
                "go_string",
                "go_comment",
                "go_number",
                "go_type",
                "go_function",
                "go_package",
                # Ruby
                "ruby_keyword",
                "ruby_string",
                "ruby_comment",
                "ruby_number",
                "ruby_symbol",
                "ruby_method",
                "ruby_class",
                "ruby_variable",
                # Swift
                "swift_keyword",
                "swift_string",
                "swift_comment",
                "swift_number",
                "swift_type",
                "swift_function",
                "swift_attribute",
                # PHP
                "php_keyword",
                "php_string",
                "php_comment",
                "php_number",
                "php_variable",
                "php_function",
                "php_tag",
                # Perl
                "perl_keyword",
                "perl_string",
                "perl_comment",
                "perl_number",
                "perl_variable",
                "perl_regex",
                # Rust
                "rust_keyword",
                "rust_string",
                "rust_comment",
                "rust_number",
                "rust_type",
                "rust_function",
                "rust_macro",
                "rust_lifetime",
            }
            for tag in tags:
                if tag in code_tags:
                    return True
            return False
        except Exception:
            return False

    def _apply_unified_progressive_formatting(self, text_widget):
        """⚡ OPTIMISÉ : Formatage progressif sécurisé avec limitation de zone"""
        try:
            text_widget.configure(state="normal")

            # ⚡ OPTIMISATION: Limiter la zone de recherche aux 800 derniers caractères
            # Cela réduit drastiquement le nombre de regex et de recherches
            widget_end = text_widget.index("end-1c")
            total_chars = int(float(widget_end.split('.')[0]))  # Ligne actuelle

            # Si moins de 80 lignes, traiter tout; sinon traiter les 80 dernières lignes
            if total_chars > 80:
                search_start = f"{total_chars - 80}.0"
            else:
                search_start = "1.0"

            # Obtenir le texte actuellement affiché
            _current_displayed_text = text_widget.get("1.0", "end-1c")

            # === FORMATAGE GRAS **texte** - Toujours actif mais vérifie le texte complet ===
            start_pos = search_start  # ⚡ OPTIMISÉ: Commence à la zone récente
            while True:
                # Chercher le prochain **
                pos_start = text_widget.search("**", start_pos, "end")
                if not pos_start:
                    break

                # Vérifier si on est dans un bloc de code - si oui, ignorer
                if self._is_position_in_code_block(text_widget, pos_start):
                    start_pos = text_widget.index(f"{pos_start}+2c")
                    continue

                # Chercher le ** de fermeture
                search_start = text_widget.index(f"{pos_start}+2c")
                pos_end = text_widget.search("**", search_start, "end")

                if pos_end:
                    # Vérifier que le contenu entre les ** est valide
                    content_start = text_widget.index(f"{pos_start}+2c")
                    content = text_widget.get(content_start, pos_end)

                    # Valider le contenu
                    if (
                        content
                        and len(content) <= 200
                        and "*" not in content
                        and "\n" not in content
                    ):
                        # Vérifier que ce bold complet existe dans le texte source
                        full_bold = f"**{content}**"
                        if hasattr(self, "typing_text") and self.typing_text:
                            if full_bold not in self.typing_text:
                                # Pas encore complet dans le texte source
                                start_pos = text_widget.index(f"{pos_start}+1c")
                                continue

                        # Utiliser le contenu comme clé de déduplication
                        content_key = content.strip()
                        if content_key not in self._formatted_bold_contents:
                            # Supprimer **texte** et insérer texte en gras
                            end_pos_full = text_widget.index(f"{pos_end}+2c")
                            text_widget.delete(pos_start, end_pos_full)
                            text_widget.insert(pos_start, content, "bold")
                            self._formatted_bold_contents.add(content_key)
                            # Continuer après le texte inséré
                            start_pos = text_widget.index(
                                f"{pos_start}+{len(content)}c"
                            )
                        else:
                            start_pos = text_widget.index(f"{pos_end}+2c")
                    else:
                        start_pos = text_widget.index(f"{pos_start}+1c")
                else:
                    start_pos = text_widget.index(f"{pos_start}+1c")

            # === FORMATAGE LIENS PRÉTRAITÉS (DÉTECTION DES TITRES) ===
            # Les liens ont été remplacés par leurs titres, on doit les détecter et les marquer
            if hasattr(self, "_pending_links") and self._pending_links:
                # Créer un set de titres uniques pour éviter les recherches dupliquées
                unique_titles = set(
                    link_data["title"] for link_data in self._pending_links
                )

                for title in unique_titles:
                    # Chercher toutes les occurrences de ce titre
                    start_pos = search_start  # ⚡ OPTIMISÉ
                    occurrences_found = 0
                    while True:
                        pos_start = text_widget.search(
                            title, start_pos, "end", nocase=False
                        )
                        if not pos_start:
                            break

                        pos_end = text_widget.index(f"{pos_start}+{len(title)}c")
                        pos_str = str(pos_start)

                        # Vérifier que ce n'est pas déjà formaté et que c'est exactement le titre
                        current_text = text_widget.get(pos_start, pos_end)
                        if (
                            current_text == title
                            and pos_str not in self._formatted_positions
                        ):
                            # Marquer comme lien temporaire
                            text_widget.tag_add("link_temp", pos_start, pos_end)
                            self._formatted_positions.add(pos_str)
                            occurrences_found += 1
                            # ⚡ Debug supprimé pour performance

                        start_pos = text_widget.index(f"{pos_start}+1c")

                    # ⚡ Debug supprimé pour performance

            # === FORMATAGE LIENS [titre](url) AVEC PRIORITÉ SUR TITRES (ANCIEN SYSTÈME POUR COMPATIBILITÉ) ===
            start_pos = search_start  # ⚡ OPTIMISÉ
            links_found = 0
            while True:
                # Chercher le prochain [
                pos_start = text_widget.search("[", start_pos, "end")
                if not pos_start:
                    break

                # NOUVEAU: Vérifier si on est dans un bloc de code - si oui, ignorer
                if self._is_position_in_code_block(text_widget, pos_start):
                    start_pos = text_widget.index(f"{pos_start}+1c")
                    continue

                # Obtenir la ligne complète pour analyser le pattern
                line_start = text_widget.index(f"{pos_start} linestart")
                line_end = text_widget.index(f"{pos_start} lineend")
                line_content = text_widget.get(line_start, line_end)

                # Pattern pour détecter [titre](url)
                link_pattern = r"\[([^\]]+)\]\(([^)]+)\)"
                match = re.search(link_pattern, line_content)

                if match:
                    links_found += 1
                    # ⚡ Debug supprimé pour performance
                    title = match.group(1)
                    url = match.group(2)

                    # Calculer les positions dans le widget
                    char_offset = line_content.find(match.group(0))
                    link_start = text_widget.index(f"{line_start}+{char_offset}c")
                    link_end = text_widget.index(f"{link_start}+{len(match.group(0))}c")

                    pos_str = str(link_start)

                    if pos_str not in self._formatted_positions:
                        # Remplacer [titre](url) par juste "titre" pendant l'animation
                        text_widget.delete(link_start, link_end)
                        text_widget.insert(link_start, title, "link_temp")

                        # Stocker l'URL pour plus tard dans une liste (pas dictionnaire)
                        if not hasattr(self, "_pending_links"):
                            self._pending_links = []

                        # Ajouter ce lien à la liste
                        self._pending_links.append(
                            {
                                "title": title,
                                "url": url,
                            }
                        )
                        # ⚡ Debug supprimé pour performance

                        self._formatted_positions.add(pos_str)

                        start_pos = link_start
                    else:
                        start_pos = text_widget.index(f"{pos_start}+1c")
                else:
                    start_pos = text_widget.index(f"{pos_start}+1c")

            # ⚡ Debug supprimé pour performance

            # === FORMATAGE CODE `code` ===
            start_pos = search_start  # ⚡ OPTIMISÉ
            while True:
                # Chercher le prochain `
                pos_start = text_widget.search("`", start_pos, "end")
                if not pos_start:
                    break

                # Vérifier si on est dans un bloc de code - si oui, ignorer
                if self._is_position_in_code_block(text_widget, pos_start):
                    start_pos = text_widget.index(f"{pos_start}+1c")
                    continue

                # Chercher le ` de fermeture
                search_start = text_widget.index(f"{pos_start}+1c")
                pos_end = text_widget.search("`", search_start, "end")

                if pos_end:
                    # Vérifier le contenu
                    content_start = text_widget.index(f"{pos_start}+1c")
                    content = text_widget.get(content_start, pos_end)

                    if (
                        content
                        and len(content) <= 100
                        and "`" not in content
                        and "\n" not in content
                    ):
                        pos_str = str(pos_start)

                        if pos_str not in self._formatted_positions:
                            # Supprimer `code`
                            end_pos_full = text_widget.index(f"{pos_end}+1c")
                            text_widget.delete(pos_start, end_pos_full)

                            # Insérer code formaté
                            text_widget.insert(pos_start, content, "code")

                            self._formatted_positions.add(pos_str)

                            start_pos = pos_start
                        else:
                            start_pos = text_widget.index(f"{pos_end}+1c")
                    else:
                        start_pos = text_widget.index(f"{pos_start}+1c")
                else:
                    start_pos = text_widget.index(f"{pos_start}+1c")

            # === FORMATAGE TITRES # ## ### #### ===
            # Ne pas formater les # qui sont dans des blocs de code (commentaires Python)
            # Formater les titres Markdown avec 1 à 6 #
            start_pos = search_start  # ⚡ OPTIMISÉ
            while True:
                # Chercher le prochain # en début de ligne
                pos_start = text_widget.search("#", start_pos, "end")
                if not pos_start:
                    break

                # Vérifier que c'est bien en début de ligne
                line_start = text_widget.index(f"{pos_start} linestart")
                if pos_start != line_start:
                    start_pos = text_widget.index(f"{pos_start}+1c")
                    continue

                # VÉRIFICATION CRITIQUE: Si ce # a déjà un tag de code (commentaire), ne pas formater comme titre
                if self._is_position_in_code_block(text_widget, pos_start):
                    # C'est un commentaire Python, pas un titre Markdown
                    start_pos = text_widget.index(f"{pos_start}+1c")
                    continue

                # Obtenir la ligne complète
                line_end = text_widget.index(f"{pos_start} lineend")
                line_content = text_widget.get(pos_start, line_end)

                # Analyser la ligne pour détecter le niveau de titre (1 à 6 #)
                title_match = re.match(r"^(#{1,6})\s+(.+)$", line_content)
                if title_match:
                    hash_count = len(title_match.group(1))
                    # Mapper vers title_1, title_2, title_3 (max 3 niveaux de style)
                    level = min(hash_count, 3)
                    title_without_hashes = title_match.group(2)

                    # IMPORTANT: Ne formater que si la ligne est COMPLÈTE
                    # On vérifie si après cette ligne il y a du contenu (donc \n a été affiché)
                    # ou si c'est la fin de l'animation
                    line_is_complete = False

                    # Vérifier s'il y a une ligne après (donc \n a été affiché)
                    next_line_start = text_widget.index(f"{line_end}+1c")
                    widget_end = text_widget.index("end-1c")

                    # Si next_line_start < widget_end, il y a du contenu après cette ligne
                    if text_widget.compare(next_line_start, "<=", widget_end):
                        # Vérifier qu'il y a vraiment du contenu après (pas juste la fin)
                        content_after = text_widget.get(line_end, next_line_start)
                        if content_after == "\n":
                            line_is_complete = True

                    # Si l'animation est terminée (pas de typing_text actif), formater
                    if not hasattr(self, "typing_text") or not self.typing_text:
                        line_is_complete = True
                    # Si typing_index a atteint la fin du texte
                    elif hasattr(self, "typing_index") and hasattr(self, "typing_text"):
                        if self.typing_index >= len(self.typing_text):
                            line_is_complete = True

                    # Utiliser le contenu comme clé pour éviter les doublons
                    content_key = f"title:{title_without_hashes.strip()}"
                    if (
                        line_is_complete
                        and content_key not in self._formatted_bold_contents
                    ):
                        # Remplacer "## titre" par "titre" formaté (sans les ##)
                        text_widget.delete(pos_start, line_end)
                        text_widget.insert(
                            pos_start, title_without_hashes, f"title_{level}"
                        )
                        self._formatted_bold_contents.add(content_key)
                        start_pos = text_widget.index(
                            f"{pos_start}+{len(title_without_hashes)}c"
                        )
                    else:
                        start_pos = text_widget.index(f"{line_end}+1c")
                else:
                    start_pos = text_widget.index(
                        f"{pos_start}+1c"
                    )  # === FORMATAGE DOCSTRINGS '''docstring''' ===
            start_pos = search_start  # ⚡ OPTIMISÉ
            while True:
                # Chercher le prochain '''
                pos_start = text_widget.search("'''", start_pos, "end")
                if not pos_start:
                    break

                # Chercher le ''' de fermeture
                search_start = text_widget.index(f"{pos_start}+3c")
                pos_end = text_widget.search("'''", search_start, "end")

                if pos_end:
                    # Obtenir le contenu COMPLET avec les '''
                    end_pos_full = text_widget.index(f"{pos_end}+3c")
                    full_docstring = text_widget.get(
                        pos_start, end_pos_full
                    )  # '''contenu'''

                    # Obtenir juste le contenu pour validation
                    content_start = text_widget.index(f"{pos_start}+3c")
                    content = text_widget.get(content_start, pos_end)

                    # Valider que c'est une vraie docstring (pas trop courte)
                    if content and len(content.strip()) > 0:
                        pos_str = str(pos_start)

                        if pos_str not in self._formatted_positions:
                            # CORRECTION : Garder les ''' et formater le tout
                            text_widget.delete(pos_start, end_pos_full)

                            # Insérer docstring formatée AVEC les '''
                            text_widget.insert(pos_start, full_docstring, "docstring")

                            self._formatted_positions.add(pos_str)

                            start_pos = pos_start
                        else:
                            start_pos = text_widget.index(f"{pos_end}+1c")
                    else:
                        start_pos = text_widget.index(f"{pos_start}+1c")
                else:
                    start_pos = text_widget.index(f"{pos_start}+1c")

            text_widget.configure(state="disabled")

        except Exception as e:
            print(f"[ERREUR] Formatage unifié: {e}")
            if hasattr(text_widget, "configure"):
                text_widget.configure(state="disabled")

    def _apply_immediate_progressive_formatting(self, text_widget):
        """Formatage progressif IMMÉDIAT et DIRECT"""
        try:
            # Obtenir le contenu actuel
            current_content = text_widget.get("1.0", "end-1c")

            # Pattern pour **texte** complet seulement
            bold_pattern = r"\*\*([^*\n]{1,50}?)\*\*"

            # Chercher et formater tous les **texte** complets
            for match in re.finditer(bold_pattern, current_content):
                try:
                    # Positions des balises et du contenu
                    full_start = match.start()
                    content_start = match.start(1)
                    content_end = match.end(1)
                    full_end = match.end()

                    # Convertir en positions tkinter
                    tk_full_start = self._char_to_tkinter_position(
                        current_content, full_start
                    )
                    tk_content_start = self._char_to_tkinter_position(
                        current_content, content_start
                    )
                    tk_content_end = self._char_to_tkinter_position(
                        current_content, content_end
                    )
                    tk_full_end = self._char_to_tkinter_position(
                        current_content, full_end
                    )

                    if all(
                        [tk_full_start, tk_content_start, tk_content_end, tk_full_end]
                    ):
                        # Supprimer les anciens tags sur cette zone
                        text_widget.tag_remove("bold", tk_full_start, tk_full_end)
                        text_widget.tag_remove("hidden", tk_full_start, tk_full_end)
                        text_widget.tag_remove("normal", tk_full_start, tk_full_end)

                        # Configurer les tags s'ils n'existent pas
                        text_widget.tag_configure(
                            "bold",
                            font=("Segoe UI", 12, "bold"),
                            foreground=self.colors["text_primary"],
                        )
                        text_widget.tag_configure("hidden", elide=True)

                        # Appliquer le formatage : cacher ** et mettre en gras le contenu
                        text_widget.tag_add(
                            "hidden", tk_full_start, tk_content_start
                        )  # Cacher **
                        text_widget.tag_add(
                            "bold", tk_content_start, tk_content_end
                        )  # Gras
                        text_widget.tag_add(
                            "hidden", tk_content_end, tk_full_end
                        )  # Cacher **

                        print(f"[DEBUG] Formaté en gras: {match.group(1)}")

                except Exception as e:
                    print(f"[DEBUG] Erreur formatage match: {e}")
                    continue

            # Pattern pour *texte* italique (pas **texte**)
            italic_pattern = r"(?<!\*)\*([^*\n]{1,50}?)\*(?!\*)"

            for match in re.finditer(italic_pattern, current_content):
                try:
                    full_start = match.start()
                    content_start = match.start(1)
                    content_end = match.end(1)
                    full_end = match.end()

                    tk_full_start = self._char_to_tkinter_position(
                        current_content, full_start
                    )
                    tk_content_start = self._char_to_tkinter_position(
                        current_content, content_start
                    )
                    tk_content_end = self._char_to_tkinter_position(
                        current_content, content_end
                    )
                    tk_full_end = self._char_to_tkinter_position(
                        current_content, full_end
                    )

                    if all(
                        [tk_full_start, tk_content_start, tk_content_end, tk_full_end]
                    ):
                        # Nettoyer la zone
                        text_widget.tag_remove("italic", tk_full_start, tk_full_end)
                        text_widget.tag_remove("hidden", tk_full_start, tk_full_end)

                        # Configurer tag italique
                        text_widget.tag_configure(
                            "italic",
                            font=("Segoe UI", 12, "italic"),
                            foreground=self.colors["text_primary"],
                        )

                        # Appliquer : cacher * et mettre en italique
                        text_widget.tag_add("hidden", tk_full_start, tk_content_start)
                        text_widget.tag_add("italic", tk_content_start, tk_content_end)
                        text_widget.tag_add("hidden", tk_content_end, tk_full_end)

                        print(f"[DEBUG] Formaté en italique: {match.group(1)}")

                except Exception:
                    continue

        except Exception as e:
            print(f"[DEBUG] Erreur formatage immédiat: {e}")

    def _smart_scroll_follow_animation(self):
        """Scroll optimisé qui évite le clignotement"""
        try:
            if self.use_ctk:
                canvas = self._get_parent_canvas()
                if canvas:

                    # 🔧 OPTIMISATION : Ne scroll que si nécessaire
                    canvas.update_idletasks()

                    # Vérifier la position actuelle pour éviter les scrolls inutiles
                    current_scroll = canvas.canvasy(canvas.winfo_height())
                    total_height = canvas.bbox("all")[3] if canvas.bbox("all") else 0

                    # Ne scroll que si on n'est pas déjà proche du bas (tolérance de 50px)
                    if total_height - current_scroll > 50:
                        canvas.yview_moveto(1.0)

                    # Mise à jour immédiate
                    canvas.update()

            else:
                # Version tkinter standard
                parent = self.chat_frame.master
                if hasattr(parent, "yview_moveto"):
                    parent.update_idletasks()
                    parent.yview_moveto(1.0)
                    parent.update()

        except Exception as e:
            print(f"[DEBUG] Erreur scroll animation: {e}")

    def _force_scroll_to_bottom(self):
        """Force un scroll vers le bas quand un gros contenu est ajouté"""
        try:
            if self.use_ctk:
                canvas = self._get_parent_canvas()
                if canvas:
                    canvas.update_idletasks()
                    # Scroll directement vers le bas avec une petite marge
                    canvas.yview_moveto(
                        0.9
                    )  # Pas tout à fait au bas pour laisser de l'espace
                    canvas.update()
            else:
                parent = self.chat_frame.master
                if hasattr(parent, "yview_moveto"):
                    parent.update_idletasks()
                    parent.yview_moveto(0.9)
                    parent.update()
        except Exception as e:
            print(f"[DEBUG] Erreur force scroll: {e}")

    def _is_internet_search_message(self):
        """Détecte si le message en cours de frappe contient des sources de recherche internet"""
        if not hasattr(self, "typing_text") or not self.typing_text:
            return False

        text = self.typing_text

        # 🔧 AMÉLIORATION : Indicateurs plus précis pour les sources de recherche internet
        _search_indicators = [
            # Patterns spécifiques aux sources
            "Sources :",
            "Sources:",
            "Source :",
            "Source:",
            # Patterns de liens numérotés (typiques des sources)
            "1. [",
            "2. [",
            "3. [",
            "4. [",
            "5. [",
            # Patterns d'URLs avec contexte de source
            "] (http",
            "] (https",
            "](http",
            "](https",
            # Autres indicateurs de recherche web
            "Visitez",
            "consultez",
            "source officielle",
            "selon",
            "D'après",
        ]

        # Vérifier la présence de patterns spécifiques
        strong_indicators = ["Sources :", "Sources:", "Source :", "Source:"]
        weak_indicators = ["http://", "https://"]

        # Vérification forte : présence d'indicateurs de sources
        has_strong_indicator = any(indicator in text for indicator in strong_indicators)

        # Vérification faible : présence de liens
        link_count = sum(text.count(indicator) for indicator in weak_indicators)

        # Vérification des liens numérotés (pattern typique des sources)
        numbered_links = sum(1 for i in range(1, 6) if f"{i}. [" in text)

        # C'est une source de recherche si :
        # - Il y a un indicateur fort (Sources:) OU
        # - Il y a au moins 2 liens ET au moins 1 lien numéroté OU
        # - Il y a au moins 3 liens (probable liste de sources)
        is_search_result = (
            has_strong_indicator
            or (link_count >= 2 and numbered_links >= 1)
            or link_count >= 3
        )

        return is_search_result

    def _is_in_incomplete_code_block(self, text):
        """Détecte si le texte contient un bloc de code incomplet (tous langages)"""
        # Langages supportés
        supported_languages = [
            "python",
            "javascript",
            "js",
            "html",
            "xml",
            "css",
            "bash",
            "shell",
            "sh",
            "sql",
            "mysql",
            "postgresql",
            "sqlite",
            "dockerfile",
            "docker",
            "json",
        ]

        for lang in supported_languages:
            # Compter les balises d'ouverture et de fermeture pour ce langage
            opening_pattern = rf"```{lang}\b"
            opening_tags = len(re.findall(opening_pattern, text, re.IGNORECASE))

            if opening_tags > 0:
                # Compter les fermetures après chaque ouverture
                closing_tags = len(
                    re.findall(r"```(?!\w)", text)
                )  # ``` non suivi d'une lettre

                # Si on a plus d'ouvertures que de fermetures, on est dans un bloc incomplet
                if opening_tags > closing_tags:
                    # Vérifier si le dernier bloc ouvert est complet
                    last_opening = text.rfind(f"```{lang}")
                    if last_opening == -1:
                        # Essayer avec case insensitive
                        for match in re.finditer(opening_pattern, text, re.IGNORECASE):
                            last_opening = match.start()

                    if last_opening != -1:
                        # Vérifier s'il y a une balise de fermeture après
                        text_after_opening = text[last_opening + len(f"```{lang}") :]
                        has_closing = "```" in text_after_opening

                        # Si pas de fermeture OU si le texte finit par une fermeture partielle
                        if not has_closing or text_after_opening.rstrip().endswith(
                            "``"
                        ):
                            return True

        return False

    def _insert_text_with_safe_formatting(self, text_widget, text):
        """Formatage sécurisé qui ne traite que les blocs de code complets (tous langages)"""
        # 🔧 STRATÉGIE : Séparer le texte en deux parties
        # 1. La partie avec blocs complets qu'on peut formatter
        # 2. La partie avec bloc incomplet qu'on affiche en texte brut
        # Pattern pour tous les langages supportés
        supported_languages = [
            "python",
            "javascript",
            "js",
            "html",
            "xml",
            "css",
            "bash",
            "shell",
            "sh",
            "sql",
            "mysql",
            "postgresql",
            "sqlite",
            "dockerfile",
            "docker",
            "json",
        ]
        languages_pattern = "|".join(supported_languages)

        # Trouver tous les blocs de code complets (tous langages)
        complete_blocks_pattern = rf"```({languages_pattern})\n?(.*?)```"
        matches = list(
            re.finditer(complete_blocks_pattern, text, re.DOTALL | re.IGNORECASE)
        )

        if not matches:
            # Pas de blocs complets, vérifier s'il y a un bloc en cours
            incomplete_pattern = rf"```({languages_pattern})\b"
            if re.search(incomplete_pattern, text, re.IGNORECASE):
                # Il y a un bloc en cours mais incomplet
                # Trouver où commence le bloc incomplet
                incomplete_match = None
                for match in re.finditer(incomplete_pattern, text, re.IGNORECASE):
                    incomplete_match = match

                if incomplete_match:
                    incomplete_start = incomplete_match.start()
                    # Formatter la partie avant le bloc incomplet
                    text_before_incomplete = text[:incomplete_start]
                    incomplete_part = text[incomplete_start:]

                    if text_before_incomplete:
                        self._insert_markdown_segments(
                            text_widget, text_before_incomplete
                        )

                    # Afficher la partie incomplète en texte brut (sans formatage)
                    text_widget.insert("end", incomplete_part, "normal")
                    return

            # Pas de blocs de code du tout, formatage normal
            self._insert_markdown_segments(text_widget, text)
            return

        # Il y a des blocs complets, les traiter normalement
        last_end = 0

        for match in matches:
            # Formatter le texte avant ce bloc
            if match.start() > last_end:
                text_before = text[last_end : match.start()]
                self._insert_markdown_segments(text_widget, text_before)

            # Afficher le bloc complet avec formatage
            block_text = match.group(0)  # Le bloc complet avec ```language```
            self._insert_markdown_segments(text_widget, block_text)

            last_end = match.end()

        # Traiter le reste du texte après le dernier bloc complet
        if last_end < len(text):
            remaining_text = text[last_end:]

            # Vérifier si le reste contient un bloc incomplet
            incomplete_pattern = rf"```({languages_pattern})\b"
            incomplete_match = re.search(
                incomplete_pattern, remaining_text, re.IGNORECASE
            )

            if incomplete_match:
                incomplete_start = incomplete_match.start()
                text_before_incomplete = remaining_text[:incomplete_start]
                incomplete_part = remaining_text[incomplete_start:]

                if text_before_incomplete:
                    self._insert_markdown_segments(text_widget, text_before_incomplete)

                # Afficher la partie incomplète sans formatage
                text_widget.insert("end", incomplete_part, "normal")
            else:
                # Pas de bloc incomplet, formatage normal
                self._insert_markdown_segments(text_widget, remaining_text)

    def _adjust_height_final_no_scroll(self, text_widget):
        """Ajuste la hauteur du widget Text pour qu'il n'y ait aucun scroll interne ni espace vide, basé sur le nombre de lignes réelles tkinter. Désactive aussi le scroll interne."""
        try:
            text_widget.update_idletasks()
            current_state = text_widget.cget("state")
            text_widget.configure(state="normal")

            # ⚡ CORRECTION : Compter les lignes VISUELLES (avec wrapping)
            display_lines = text_widget.count("1.0", "end", "displaylines")
            if display_lines and len(display_lines) > 0:
                line_count = display_lines[0]
            else:
                line_count = int(text_widget.index("end-1c").split(".")[0])

            text_widget.configure(height=max(2, line_count))
            text_widget.update_idletasks()
            text_widget.configure(state=current_state)
            self._disable_text_scroll(text_widget)
        except Exception:
            text_widget.configure(height=10)
            self._disable_text_scroll(text_widget)

    def _adjust_height_smoothly_during_animation(self, text_widget, current_text):
        """Ajustement de hauteur SMOOTH pendant l'animation pour éviter le scroll dans la bulle"""
        try:
            # Calculer le nombre de lignes nécessaires
            lines_needed = current_text.count("\n") + 1

            # ⚡ CORRECTION: Pas de limite maximale pour l'animation
            min_height = 2

            # Calculer la hauteur idéale
            ideal_height = max(min_height, lines_needed)
            current_height = int(text_widget.cget("height"))

            # Ajuster SEULEMENT si nécessaire (éviter les changements constants)
            if abs(ideal_height - current_height) > 1:
                text_widget.configure(height=ideal_height)

                # IMPORTANT: Réinitialiser la vue SANS scroll
                text_widget.yview_moveto(0.0)  # Toujours commencer du haut

        except Exception as e:
            print(f"[DEBUG] Erreur ajustement hauteur smooth: {e}")

    def _adjust_height_during_animation(self, text_widget):
        """Ajuste la hauteur du widget Text pendant l'animation pour qu'il n'y ait aucun scroll interne, basé sur le nombre de lignes réelles tkinter."""
        try:
            text_widget.update_idletasks()

            # ⚡ CORRECTION: Compter les lignes VISUELLES (avec wrapping)
            display_lines = text_widget.count("1.0", "end", "displaylines")
            if display_lines and len(display_lines) > 0:
                line_count = display_lines[0]
            else:
                line_count = int(text_widget.index("end-1c").split(".")[0])

            text_widget.configure(height=max(2, line_count))
            text_widget.update_idletasks()
            self._disable_text_scroll(text_widget)
        except Exception:
            text_widget.configure(height=10)
            self._disable_text_scroll(text_widget)

    def finish_typing_animation_dynamic(self, interrupted=False):
        """Version CORRIGÉE - Ne réapplique PAS la coloration syntaxique à la fin"""
        if hasattr(self, "typing_widget") and hasattr(self, "typing_text"):

            # Sauvegarder le texte original avant tout traitement
            original_text = self.typing_text if hasattr(self, "typing_text") else ""

            if interrupted:
                # Réinitialiser les positions pour forcer un formatage complet
                if hasattr(self, "_formatted_positions"):
                    self._formatted_positions.clear()

                # Formatage final même en cas d'interruption
                self.typing_widget.configure(state="normal")

                # Formater les tableaux Markdown EN PREMIER (reconstruit le widget)
                self._format_markdown_tables_in_widget(
                    self.typing_widget, original_text
                )

                self._apply_unified_progressive_formatting(self.typing_widget)

                # Convertir les liens temporaires en liens clickables
                self._convert_temp_links_to_clickable(self.typing_widget)

                # Appliquer un nettoyage final pour les formatages manqués
                self.typing_widget.configure(state="disabled")
            else:
                # Animation complète : formatage FINAL COMPLET

                # NOUVEAU : Réinitialiser les positions pour forcer un formatage complet
                if hasattr(self, "_formatted_positions"):
                    self._formatted_positions.clear()

                # Formatage final unifié
                self.typing_widget.configure(state="normal")

                # NOUVEAU : Formater les tableaux Markdown EN PREMIER (reconstruit le widget)
                self._format_markdown_tables_in_widget(
                    self.typing_widget, original_text
                )

                self._apply_unified_progressive_formatting(self.typing_widget)

                # Convertir les liens temporaires en liens clickables
                self._convert_temp_links_to_clickable(self.typing_widget)

                # Appliquer un nettoyage final pour les formatages manqués
                self.typing_widget.configure(state="disabled")

            # Ajustement final de la hauteur
            self._adjust_height_final_no_scroll(self.typing_widget)

            # RÉACTIVER le scroll maintenant que l'animation est finie
            self._reactivate_text_scroll(self.typing_widget)

            self.typing_widget.configure(state="disabled")

            # Afficher le timestamp sous le message IA
            self._show_timestamp_for_current_message()

            # Réactiver la saisie utilisateur
            self.set_input_state(True)

            # Scroll final contrôlé
            self.root.after(200, self._final_smooth_scroll_to_bottom)

            # Nettoyage des variables d'animation
            if hasattr(self, "_typing_animation_after_id"):
                try:
                    self.root.after_cancel(self._typing_animation_after_id)
                except Exception:
                    pass
                del self._typing_animation_after_id

            delattr(self, "typing_widget")
            delattr(self, "typing_text")
            delattr(self, "typing_index")
            self._typing_interrupted = False

            # Nettoyer le cache de formatage
            if hasattr(self, "_formatted_positions"):
                delattr(self, "_formatted_positions")

    def _convert_temp_links_to_clickable(self, text_widget):
        """Convertit les liens temporaires en liens bleus clicables à la fin de l'animation"""
        try:
            if not hasattr(self, "_pending_links"):
                print("[DEBUG] Aucun _pending_links trouvé")
                return

            if not self._pending_links:
                print("[DEBUG] _pending_links est vide")
                return

            print(
                f"[DEBUG] Conversion de {len(self._pending_links)} liens en clickables"
            )
            text_widget.configure(state="normal")

            # Récupérer TOUTES les zones avec le tag link_temp
            ranges = text_widget.tag_ranges("link_temp")

            if not ranges:
                print("[DEBUG] ERREUR: Aucune zone link_temp trouvée")
            else:
                print(f"[DEBUG] {len(ranges)//2} zones link_temp trouvées")
                print(
                    f"[DEBUG] Liens disponibles dans _pending_links: {[(l['title'], l['url'][:50]) for l in self._pending_links]}"
                )

                # Créer un index des liens par titre pour recherche rapide
                # Pour gérer les liens avec le même titre, on utilise une liste
                links_by_title = {}
                for link_data in self._pending_links:
                    title = link_data["title"]
                    if title not in links_by_title:
                        links_by_title[title] = []
                    links_by_title[title].append(link_data["url"])

                # Compteur pour chaque titre (pour gérer les doublons)
                title_usage_count = {}
                link_counter = 0

                # Pour chaque zone link_temp, trouver le lien correspondant
                for i in range(0, len(ranges), 2):
                    start_range = ranges[i]
                    end_range = ranges[i + 1]
                    range_text = text_widget.get(start_range, end_range)

                    # Chercher l'URL correspondante
                    url = None
                    if range_text in links_by_title:
                        # Obtenir l'index d'utilisation pour ce titre
                        usage_idx = title_usage_count.get(range_text, 0)

                        # Si on a plusieurs URLs pour ce titre, utiliser l'index
                        urls_list = links_by_title[range_text]
                        if usage_idx < len(urls_list):
                            url = urls_list[usage_idx]
                            title_usage_count[range_text] = usage_idx + 1
                        else:
                            # Réutiliser la dernière URL si on dépasse
                            url = urls_list[-1]

                    if url:
                        # Créer un tag unique pour ce lien
                        unique_tag = f"clickable_link_{link_counter}"
                        link_counter += 1

                        # Remplacer le tag link_temp par le tag unique
                        text_widget.tag_remove("link_temp", start_range, end_range)
                        text_widget.tag_add(unique_tag, start_range, end_range)

                        # Configurer le style du tag unique
                        text_widget.tag_configure(
                            unique_tag,
                            foreground="#3b82f6",
                            underline=1,
                            font=("Segoe UI", 12),
                        )

                        # CORRECTION CLOSURE : Créer une fonction avec l'URL capturée
                        def create_click_handler(url_to_open):
                            def click_handler(_event):
                                print(f"[DEBUG] Clic sur lien: {url_to_open}")
                                webbrowser.open(url_to_open)
                                return "break"

                            return click_handler

                        # Lier l'événement avec l'URL correcte
                        text_widget.tag_bind(
                            unique_tag, "<Button-1>", create_click_handler(url)
                        )
                        print(
                            f"[DEBUG] Lien configuré: '{range_text}' -> {url} (tag: {unique_tag})"
                        )
                    else:
                        print(
                            f"[DEBUG] WARNING: Aucune URL trouvée pour '{range_text}'"
                        )

            print(
                f"[DEBUG] ✅ Conversion terminée: {link_counter} liens clickables créés"
            )

            # NE PAS nettoyer _pending_links ici - laissé pour la fin de l'animation complète
            # delattr(self, "_pending_links")

            text_widget.configure(state="disabled")

        except Exception as e:
            print(f"[DEBUG] Erreur conversion liens: {e}")

    def _final_smooth_scroll_to_bottom(self):
        """Scroll final en douceur sans saut brutal"""
        try:
            # Une seule mise à jour, puis scroll progressif
            self.root.update_idletasks()

            if self.use_ctk:
                canvas = self._get_parent_canvas()
                if canvas:

                    # Scroll progressif vers le bas
                    for i in range(5):  # 5 étapes progressives
                        current_yview = canvas.yview()
                        if current_yview and current_yview[1] < 1.0:
                            # Calculer la position intermédiaire
                            current_top = current_yview[0]
                            step = (1.0 - current_top) / (5 - i)
                            new_position = min(1.0, current_top + step)
                            canvas.yview_moveto(new_position)
                            canvas.update_idletasks()
                        else:
                            break
            else:
                parent = self.chat_frame.master
                if hasattr(parent, "yview_moveto"):
                    for i in range(5):
                        current_yview = parent.yview()
                        if current_yview and current_yview[1] < 1.0:
                            current_top = current_yview[0]
                            step = (1.0 - current_top) / (5 - i)
                            new_position = min(1.0, current_top + step)
                            parent.yview_moveto(new_position)
                            parent.update_idletasks()
                        else:
                            break

        except Exception:
            # Fallback : scroll simple
            try:
                canvas = self._get_parent_canvas()
                if canvas:
                    canvas.yview_moveto(1.0)
                else:
                    parent = self.chat_frame.master
                    if hasattr(parent, "yview_moveto"):
                        parent.yview_moveto(1.0)
            except Exception:
                pass

    def stop_typing_animation(self):
        """Stoppe proprement l'animation de frappe IA (interruption utilisateur)"""
        self._typing_interrupted = True
        if hasattr(self, "_typing_animation_after_id"):
            try:
                self.root.after_cancel(self._typing_animation_after_id)
            except Exception:
                pass
            del self._typing_animation_after_id

    def scroll_to_bottom_smooth(self):
        """Scroll vers le bas en douceur, sans clignotement"""

        try:
            # Une seule mise à jour, puis scroll
            self.root.update_idletasks()

            if self.use_ctk:
                if hasattr(self, "chat_frame"):
                    parent = self.chat_frame.master
                    while parent and not hasattr(parent, "yview_moveto"):
                        parent = parent.master

                    if parent and hasattr(parent, "yview_moveto"):
                        parent.yview_moveto(1.0)
            else:
                parent = self.chat_frame.master
                if hasattr(parent, "yview_moveto"):
                    parent.yview_moveto(1.0)

        except Exception as e:
            print(f"Erreur scroll doux: {e}")

    def setup_text_copy_functionality(self, text_widget, original_text):
        """Configure la fonctionnalité de copie pour un widget Text"""

        def copy_selected_text():
            """Copie le texte sélectionné ou tout le texte si rien n'est sélectionné"""
            try:
                # Essayer de récupérer la sélection
                selected_text = text_widget.selection_get()
                if selected_text:
                    self.root.clipboard_clear()
                    self.root.clipboard_append(selected_text)
                    self.show_copy_notification("📋 Sélection copiée !")
                else:
                    # Si rien n'est sélectionné, copier tout le texte
                    self.root.clipboard_clear()
                    self.root.clipboard_append(original_text)
                    self.show_copy_notification("📋 Message entier copié !")
            except tk.TclError:
                # Aucune sélection, copier tout le texte
                self.root.clipboard_clear()
                self.root.clipboard_append(original_text)
                self.show_copy_notification("📋 Message copié !")
            except Exception:
                self.show_copy_notification("❌ Erreur de copie")

        # Menu contextuel amélioré
        def show_context_menu(event):
            context_menu = tk.Menu(self.root, tearoff=0)

            # Vérifier s'il y a une sélection
            try:
                selected = text_widget.selection_get()
                if selected:
                    context_menu.add_command(
                        label="📋 Copier la sélection", command=copy_selected_text
                    )
                    context_menu.add_separator()
            except Exception:
                pass

            context_menu.add_command(
                label="📄 Copier tout le message", command=copy_selected_text
            )
            context_menu.add_command(
                label="🔍 Tout sélectionner",
                command=lambda: text_widget.tag_add("sel", "1.0", "end"),
            )

            try:
                context_menu.tk_popup(event.x_root, event.y_root)
            except Exception:
                pass
            finally:
                context_menu.grab_release()

        # Binds pour la copie
        text_widget.bind("<Button-3>", show_context_menu)  # Clic droit
        text_widget.bind("<Control-c>", lambda e: copy_selected_text())  # Ctrl+C
        text_widget.bind(
            "<Control-a>", lambda e: text_widget.tag_add("sel", "1.0", "end")
        )  # Ctrl+A

    def is_animation_running(self):
        """Vérifie si une animation d'écriture est en cours"""
        return (
            hasattr(self, "typing_widget")
            and hasattr(self, "typing_text")
            and hasattr(self, "typing_index")
        )

    def _adjust_text_height_exact(self, text_widget):
        """Ajuste la hauteur du widget Text pour qu'il n'y ait aucun scroll interne ni espace vide, basé sur le nombre de lignes réelles tkinter. Désactive aussi le scroll interne."""
        try:
            text_widget.update_idletasks()
            current_state = text_widget.cget("state")
            text_widget.configure(state="normal")
            # ⚡ CORRECTION: Compter les lignes VISUELLES (avec wrapping)
            display_lines = text_widget.count("1.0", "end", "displaylines")
            if display_lines and len(display_lines) > 0:
                line_count = display_lines[0]
            else:
                line_count = int(text_widget.index("end-1c").split(".")[0])

            # Pas de limite maximale, juste un minimum de 2 lignes
            height = max(2, line_count)
            text_widget.configure(height=height)
            text_widget.configure(state=current_state)
            self._disable_text_scroll(text_widget)
        except Exception:
            try:
                text_widget.configure(height=7)
            except Exception:
                pass

    def _process_text_with_links_only(self, text_widget, text, start_link_count=0):
        """Traite le texte avec liens et markdown, sans blocs de code"""
        # Pattern pour liens Markdown : [texte](url)
        markdown_link_pattern = r"\[([^\]]+)\]\(([^)]+)\)"
        # Pattern pour liens HTTP directs
        http_link_pattern = r"(https?://[^\s\)]+)"
        # Combinaison des patterns
        combined_pattern = (
            f"(?P<markdown>{markdown_link_pattern})|(?P<direct>{http_link_pattern})"
        )

        last_end = 0
        link_count = start_link_count

        # Traiter chaque lien
        for match in re.finditer(combined_pattern, text):
            # Insérer le texte avant le lien avec formatage markdown
            if match.start() > last_end:
                text_before = text[last_end : match.start()]
                self._insert_simple_markdown(text_widget, text_before)

            # Traiter le lien
            if match.group("markdown"):  # Lien Markdown [texte](url)
                markdown_match = re.match(
                    markdown_link_pattern, match.group("markdown")
                )
                if markdown_match:
                    link_text = markdown_match.group(1)
                    url = markdown_match.group(2)
                else:
                    last_end = match.end()
                    continue
            else:  # Lien HTTP direct
                url = match.group("direct")
                # Raccourcissement intelligent selon le type de message
                if len(url) > 60:
                    link_text = url[:30] + "..." + url[-20:]
                else:
                    link_text = url if len(url) <= 80 else url[:77] + "..."

            # Insérer le lien avec formatage
            if url and url.strip() and url != "None":
                self._insert_link_with_callback(text_widget, link_text, url, link_count)
                link_count += 1

            last_end = match.end()

        # Insérer le reste du texte
        if last_end < len(text):
            remaining_text = text[last_end:]
            self._insert_simple_markdown(text_widget, remaining_text)

        return link_count - start_link_count

    def _insert_link_with_callback(self, text_widget, link_text, url, link_count):
        """Insère un lien avec callback et formatage"""
        start_index = text_widget.index("end-1c")
        text_widget.insert("end", link_text, ("link",))
        end_index = text_widget.index("end-1c")

        # Créer un tag unique pour ce lien
        tag_name = f"link_{link_count}"
        text_widget.tag_add(tag_name, start_index, end_index)

        # Configuration du tag
        text_widget.tag_configure(
            tag_name, foreground="#3b82f6", underline=True, font=("Segoe UI", 12)
        )

        # Callback pour ouvrir le lien
        def create_callback(target_url):
            def on_click(_event):
                try:
                    clean_url = str(target_url).strip()
                    if clean_url.startswith(("http://", "https://")):
                        webbrowser.open(clean_url)
                    return "break"
                except Exception as e:
                    print(f"[DEBUG] Erreur ouverture lien: {e}")
                    return "break"

            return on_click

        # Bind des événements
        callback = create_callback(url)
        text_widget.tag_bind(tag_name, "<Button-1>", callback)
        text_widget.tag_bind(
            tag_name, "<Enter>", lambda e: text_widget.configure(cursor="hand2")
        )
        text_widget.tag_bind(
            tag_name, "<Leave>", lambda e: text_widget.configure(cursor="xterm")
        )

        # Assurer la priorité du tag
        text_widget.tag_raise(tag_name)

    def _char_to_tkinter_position(self, text, char_index):
        """Convertit un index de caractère en position Tkinter (ligne.colonne)"""
        try:
            if char_index < 0 or char_index > len(text):
                return None

            lines_before = text[:char_index].split("\n")
            line_num = len(lines_before)
            char_num = len(lines_before[-1]) if lines_before else 0

            return f"{line_num}.{char_num}"
        except Exception:
            return None

    def _insert_markdown_segments(self, text_widget, text, _code_blocks=None):
        """Insère du texte avec formatage markdown amélioré - Support optimal des blocs ```python```"""
        # Debug pour voir si le formatage est appliqué
        if "```python" in text:
            print("[DEBUG] Bloc Python détecté dans le texte")

        # Pattern amélioré pour détecter les blocs de code avec langage
        # CORRECTION: Capturer aussi les + pour c++, et # pour c#
        code_block_pattern = r"```([\w+#-]+)?\n?(.*?)```"

        current_pos = 0

        # Traiter chaque bloc de code trouvé
        for match in re.finditer(code_block_pattern, text, re.DOTALL):
            # Insérer le texte avant le bloc de code
            if match.start() > current_pos:
                pre_text = text[current_pos : match.start()]
                self._insert_simple_markdown(text_widget, pre_text)

            # Extraire les informations du bloc de code
            language = match.group(1) or "text"
            code_content = match.group(2).strip()

            print(
                f"[DEBUG] Bloc de code détecté - Langage: {language}, Contenu: {len(code_content)} caractères"
            )

            # Traitement spécialisé selon le langage
            if language.lower() == "python":
                text_widget.insert("end", "\n")
                self._insert_python_code_block_with_syntax_highlighting(
                    text_widget, code_content
                )
                text_widget.insert("end", "\n")
            elif language.lower() in ["javascript", "js"]:
                self._insert_javascript_code_block(text_widget, code_content)
            elif language.lower() in ["html", "xml"]:
                self._insert_html_code_block(text_widget, code_content)
            elif language.lower() == "css":
                self._insert_css_code_block(text_widget, code_content)
            elif language.lower() in ["bash", "shell", "sh"]:
                self._insert_bash_code_block(text_widget, code_content)
            elif language.lower() in ["sql", "mysql", "postgresql", "sqlite"]:
                self._insert_sql_code_block(text_widget, code_content)
            elif language.lower() in ["dockerfile", "docker"]:
                self._insert_dockerfile_code_block(text_widget, code_content)
            elif language.lower() in ["json"]:
                self._insert_json_code_block(text_widget, code_content)
            else:
                # Bloc de code générique
                text_widget.insert("end", "\n")
                text_widget.insert("end", code_content, "code_block")
                text_widget.insert("end", "\n")

            current_pos = match.end()

        # Insérer le texte restant après le dernier bloc
        if current_pos < len(text):
            remaining_text = text[current_pos:]
            self._insert_simple_markdown(text_widget, remaining_text)

    def _insert_python_code_block_with_syntax_highlighting(self, text_widget, code):
        """Version optimisée pour la coloration syntaxique Python avec support VS Code"""
        try:
            code = code.strip()
            if not code:
                return

            lexer = PythonLexer()

            print(f"[DEBUG] Traitement Pygments du code Python: {len(code)} caractères")

            # Appliquer la coloration avec Pygments
            for token_type, value in lex(code, lexer):
                if not value.strip() and value != "\n":
                    text_widget.insert("end", value, "mono")
                else:
                    tag_name = str(token_type)
                    text_widget.insert("end", value, tag_name)

            print("[DEBUG] Coloration Pygments appliquée avec succès")

        except ImportError:
            print("[DEBUG] Pygments non disponible, utilisation du fallback")
            self._insert_python_code_fallback_enhanced(text_widget, code)
        except Exception as e:
            print(f"[DEBUG] Erreur Pygments: {e}, utilisation du fallback")
            self._insert_python_code_fallback_enhanced(text_widget, code)

    def _insert_python_code_fallback_enhanced(self, text_widget, code):
        """Fallback amélioré avec reconnaissance étendue des patterns Python"""
        code = code.strip()
        if not code:
            return

        # Builtins Python étendus
        python_builtins = {
            "print",
            "len",
            "str",
            "int",
            "float",
            "list",
            "dict",
            "set",
            "tuple",
            "range",
            "enumerate",
            "zip",
            "map",
            "filter",
            "sorted",
            "reversed",
            "sum",
            "min",
            "max",
            "abs",
            "round",
            "pow",
            "divmod",
            "isinstance",
            "issubclass",
            "hasattr",
            "getattr",
            "setattr",
            "delattr",
            "vars",
            "dir",
            "type",
            "id",
            "callable",
            "iter",
            "next",
            "open",
            "input",
        }

        lines = code.split("\n")

        for i, line in enumerate(lines):
            if i > 0:
                text_widget.insert("end", "\n", "mono")

            # Tokenisation améliorée avec regex plus précise
            token_pattern = r'''
                (""".*?"""|\'\'\'.*?\'\'\')|  # Triple quotes (docstrings)
                ("#.*$)|                      # Comments
                ("(?:[^"\\]|\\.)*")|         # Double quoted strings
                ('(?:[^'\\]|\\.)*')|         # Single quoted strings
                (\b\d+\.?\d*\b)|             # Numbers
                (\b[a-zA-Z_]\w*\b)|          # Identifiers
                ([+\-*/%=<>!&|^~]|//|\*\*|==|!=|<=|>=|<<|>>|\+=|-=|\*=|/=|%=|&=|\|=|\^=|<<=|>>=)|  # Operators
                ([\(\)\[\]{},;:.])           # Punctuation
            '''

            tokens = re.findall(token_pattern, line, re.VERBOSE | re.DOTALL)

            pos = 0
            for token_groups in tokens:
                # Trouver quel groupe a matché
                token = next(t for t in token_groups if t)

                # Insérer les espaces avant le token si nécessaire
                token_start = line.find(token, pos)
                if token_start > pos:
                    text_widget.insert("end", line[pos:token_start], "mono")

                # Appliquer la coloration selon le type de token
                if token.startswith('"""') or token.startswith("'''"):
                    text_widget.insert("end", token, "Token.Literal.String.Doc")
                elif token.startswith("#"):
                    text_widget.insert("end", token, "Token.Comment")
                elif token.startswith(('"', "'")):
                    text_widget.insert("end", token, "Token.Literal.String")
                elif token in keyword.kwlist:
                    text_widget.insert("end", token, "Token.Keyword")
                elif token in ["True", "False", "None"]:
                    text_widget.insert("end", token, "Token.Keyword.Constant")
                elif token in python_builtins:
                    text_widget.insert("end", token, "Token.Name.Builtin")
                elif re.match(r"^\d+\.?\d*$", token):
                    text_widget.insert("end", token, "Token.Literal.Number")
                elif re.match(
                    r"^[+\-*/%=<>!&|^~]|//|\*\*|==|!=|<=|>=|<<|>>|\+=|-=|\*=|/=|%=|&=|\|=|\^=|<<=|>>=",
                    token,
                ):
                    text_widget.insert("end", token, "Token.Operator")
                elif re.match(r"^[\(\)\[\]{},;:.]$", token):
                    text_widget.insert("end", token, "Token.Punctuation")
                elif re.match(r"^[a-zA-Z_]\w*$", token):
                    # Détection des fonctions (suivies de '(')
                    remaining = line[token_start + len(token) :].lstrip()
                    if remaining.startswith("("):
                        text_widget.insert("end", token, "Token.Name.Function")
                    else:
                        text_widget.insert("end", token, "Token.Name")
                else:
                    text_widget.insert("end", token, "mono")

                pos = token_start + len(token)

            # Insérer le reste de la ligne
            if pos < len(line):
                text_widget.insert("end", line[pos:], "mono")

    def _insert_simple_markdown(self, text_widget, text):
        """Traite le markdown simple (gras, italique, titres, tableaux) sans les blocs de code"""

        # D'abord, détecter et traiter les tableaux Markdown
        lines = text.split("\n")
        i = 0
        segments = []  # Liste de (type, contenu)
        current_text = []

        while i < len(lines):
            line = lines[i]

            # Vérifier si c'est le début d'un tableau
            if "|" in line and i + 1 < len(lines):
                # Vérifier si la ligne suivante est un séparateur de tableau
                next_line = lines[i + 1]
                separator_pattern = r"^\|?[\s\-:|\s]+\|?$"
                if re.match(separator_pattern, next_line.strip()) and "-" in next_line:
                    # C'est un tableau! D'abord sauvegarder le texte précédent
                    if current_text:
                        segments.append(("text", "\n".join(current_text)))
                        current_text = []

                    # Collecter toutes les lignes du tableau
                    table_lines = [line, next_line]
                    i += 2
                    while i < len(lines) and "|" in lines[i]:
                        # Vérifier que ce n'est pas un autre séparateur (nouveau tableau)
                        if (
                            re.match(separator_pattern, lines[i].strip())
                            and "-" in lines[i]
                        ):
                            break
                        table_lines.append(lines[i])
                        i += 1

                    segments.append(("table", table_lines))
                    continue

            current_text.append(line)
            i += 1

        # Ajouter le reste du texte
        if current_text:
            segments.append(("text", "\n".join(current_text)))

        # Traiter chaque segment
        for seg_type, content in segments:
            if seg_type == "table":
                self._insert_markdown_table(text_widget, content)
            else:
                self._apply_simple_markdown_formatting(text_widget, content)

    def _apply_simple_markdown_formatting(self, text_widget, text):
        """Applique le formatage markdown simple (gras, italique, titres)"""
        # Patterns pour le markdown de base
        patterns = [
            (r"^(#{1,6})\s+(.+)$", "title_markdown"),  # Titres
            (r"\*\*([^*\n]+?)\*\*", "bold"),  # Gras
            (r"\*([^*\n]+?)\*", "italic"),  # Italique
            (r"`([^`]+)`", "mono"),  # Code inline
        ]

        def apply_formatting(text, patterns):
            if not patterns:
                text_widget.insert("end", text, "normal")
                return

            pattern, style = patterns[0]
            remaining_patterns = patterns[1:]

            last_pos = 0
            for match in re.finditer(pattern, text, re.MULTILINE):
                # Texte avant le match
                if match.start() > last_pos:
                    pre_text = text[last_pos : match.start()]
                    apply_formatting(pre_text, remaining_patterns)

                # Appliquer le style
                if style == "title_markdown":
                    level = len(match.group(1))
                    title_text = match.group(2)
                    text_widget.insert(
                        "end", title_text + "\n", f"title{min(level, 5)}"
                    )
                else:
                    content = match.group(1)
                    text_widget.insert("end", content, style)

                last_pos = match.end()

            # Texte après le dernier match
            if last_pos < len(text):
                remaining_text = text[last_pos:]
                apply_formatting(remaining_text, remaining_patterns)

        apply_formatting(text, patterns)

    def _parse_table_row(self, line):
        """Parse une ligne de tableau Markdown et retourne les cellules"""
        # Supprimer les | au début et à la fin
        line = line.strip()
        if line.startswith("|"):
            line = line[1:]
        if line.endswith("|"):
            line = line[:-1]

        # Séparer par | et nettoyer chaque cellule
        cells = [cell.strip() for cell in line.split("|")]
        return cells

    def _calculate_column_widths(self, table_lines):
        """Calcule la largeur optimale de chaque colonne"""
        if not table_lines:
            return []

        # Parser toutes les lignes (sauf le séparateur)
        all_rows = []
        for i, line in enumerate(table_lines):
            if i == 1:  # Ignorer le séparateur
                continue
            cells = self._parse_table_row(line)
            all_rows.append(cells)

        if not all_rows:
            return []

        # Trouver le nombre max de colonnes
        max_cols = max(len(row) for row in all_rows)

        # Calculer la largeur max de chaque colonne
        widths = []
        for col in range(max_cols):
            max_width = 0
            for row in all_rows:
                if col < len(row):
                    # Compter la longueur sans les marqueurs markdown
                    cell_text = re.sub(r"\*\*([^*]+)\*\*", r"\1", row[col])
                    max_width = max(max_width, len(cell_text))
            widths.append(max(max_width, 3))  # Minimum 3 caractères

        return widths

    def _insert_markdown_table(self, text_widget, table_lines):
        """Affiche un tableau Markdown formaté dans le widget avec support complet des formattages"""
        if not table_lines or len(table_lines) < 2:
            return

        column_widths = self._calculate_column_widths(table_lines)
        if not column_widths:
            return

        # Bordure supérieure
        border_line = "┌" + "┬".join("─" * (w + 2) for w in column_widths) + "┐\n"
        text_widget.insert("end", border_line, "table_border")

        for line_idx, line in enumerate(table_lines):
            if line_idx == 1:  # Séparateur - dessiner une ligne de séparation
                sep_line = "├" + "┼".join("─" * (w + 2) for w in column_widths) + "┤\n"
                text_widget.insert("end", sep_line, "table_border")
                continue

            cells = self._parse_table_row(line)
            is_header = line_idx == 0

            # Début de ligne
            text_widget.insert("end", "│", "table_border")

            for col_idx, width in enumerate(column_widths):
                cell_content = cells[col_idx] if col_idx < len(cells) else ""

                # Calculer la longueur d'affichage (sans les marqueurs markdown)
                display_length = len(re.sub(r"\*\*([^*]+)\*\*", r"\1", cell_content))
                display_length = len(
                    re.sub(
                        r"`([^`]+)`",
                        r"\1",
                        re.sub(r"\*\*([^*]+)\*\*", r"\1", cell_content),
                    )
                )

                # Centrer le contenu
                padding = width - display_length
                left_pad = padding // 2
                right_pad = padding - left_pad

                text_widget.insert("end", " " + " " * left_pad, "table_border")

                # Sauvegarder la position actuelle pour insertion avec formatage
                current_mark = "table_cell_insert"
                text_widget.mark_set(current_mark, "end")

                # Insérer le contenu avec formatage via la fonction helper
                # Temporairement changer "end" en utilisant la marque
                old_insert = text_widget.index("insert")
                text_widget.mark_set("insert", current_mark)
                self._insert_table_cell_content(text_widget, cell_content, is_header)
                text_widget.mark_set("insert", old_insert)
                text_widget.mark_unset(current_mark)

                text_widget.insert("end", " " * right_pad + " ", "table_border")
                text_widget.insert("end", "│", "table_border")

            text_widget.insert("end", "\n")

        # Bordure inférieure
        border_line = "└" + "┴".join("─" * (w + 2) for w in column_widths) + "┘\n"
        text_widget.insert("end", border_line, "table_border")

    def _format_markdown_tables_in_widget(self, text_widget, original_text=None):
        """Détecte et reformate les tableaux Markdown - VERSION CORRIGÉE avec texte original"""
        try:
            text_widget.configure(state="normal")

            # Utiliser le texte original s'il est fourni, sinon lire le widget
            if original_text:
                content = original_text
            else:
                content = text_widget.get("1.0", "end-1c")

            # Vérifier s'il y a potentiellement des tableaux (lignes avec |)
            if "|" not in content:
                return

            # Pattern pour identifier une ligne de séparateur de tableau
            separator_pattern = r"^\|?[\s\-:]+\|[\s\-:|]+\|?$"

            lines = content.split("\n")

            # Vérifier si au moins un tableau existe
            has_table = False
            for i, line in enumerate(lines):
                if "|" in line and i + 1 < len(lines):
                    next_line = lines[i + 1]
                    if (
                        re.match(separator_pattern, next_line.strip())
                        and "-" in next_line
                    ):
                        has_table = True
                        break

            if not has_table:
                return

            print("[DEBUG] Tableaux Markdown détectés, reconstruction du widget...")

            # Effacer le widget et reconstruire avec le texte original formaté
            text_widget.delete("1.0", "end")

            # Reconstruire le contenu en utilisant _insert_markdown_segments qui gère les blocs de code
            # et _insert_simple_markdown qui gère maintenant les tableaux
            self._insert_markdown_segments(text_widget, content)

        except Exception as e:
            print(f"[DEBUG] Erreur formatage tableaux: {e}")
            traceback.print_exc()

    def _insert_javascript_code_block(self, text_widget, code):
        """Coloration syntaxique pour JavaScript avec couleurs VS Code"""
        text_widget.insert("end", "\n")
        code = code.strip()
        if not code:
            text_widget.insert("end", "\n")
            return

        # Mots-clés JavaScript
        js_keywords = {
            "var",
            "let",
            "const",
            "function",
            "return",
            "if",
            "else",
            "for",
            "while",
            "do",
            "switch",
            "case",
            "default",
            "break",
            "continue",
            "try",
            "catch",
            "finally",
            "throw",
            "new",
            "this",
            "super",
            "class",
            "extends",
            "import",
            "export",
            "from",
            "async",
            "await",
            "yield",
            "typeof",
            "instanceof",
            "in",
            "of",
            "true",
            "false",
            "null",
            "undefined",
        }

        lines = code.split("\n")
        for i, line in enumerate(lines):
            if i > 0:
                text_widget.insert("end", "\n", "code_block")

            # Tokenisation JavaScript
            # Pattern pour capturer différents éléments
            token_pattern = r"""
                (//.*$)|                     # Commentaires //
                (/\*.*?\*/)|                 # Commentaires /* */
                ("(?:[^"\\]|\\.)*")|         # Chaînes double quotes
                ('(?:[^'\\]|\\.)*')|         # Chaînes simple quotes
                (`(?:[^`\\]|\\.)*`)|         # Template literals
                (\b\d+\.?\d*\b)|             # Nombres
                (\b[a-zA-Z_$]\w*\b)|         # Identifiants
                ([+\-*/%=<>!&|^~]|===|!==|==|!=|<=|>=|&&|\|\||<<|>>|\+=|-=|\*=|/=|%=|&=|\|=|\^=|<<=|>>=|\+\+|--)|  # Opérateurs
                ([\(\)\[\]{},;:.])|          # Ponctuation
                (\s+)                        # Espaces
            """

            pos = 0
            for match in re.finditer(token_pattern, line, re.VERBOSE | re.DOTALL):
                # Ajouter le texte avant le match si nécessaire
                if match.start() > pos:
                    text_widget.insert("end", line[pos : match.start()], "code_block")

                token = match.group(0)

                if match.group(1):  # Commentaire //
                    text_widget.insert("end", token, "js_comment")
                elif match.group(2):  # Commentaire /* */
                    text_widget.insert("end", token, "js_comment")
                elif match.group(3) or match.group(4) or match.group(5):  # Chaînes
                    text_widget.insert("end", token, "js_string")
                elif match.group(6):  # Nombres
                    text_widget.insert("end", token, "js_number")
                elif match.group(7):  # Identifiants
                    if token in js_keywords:
                        text_widget.insert("end", token, "js_keyword")
                    else:
                        # Vérifier si c'est une fonction (suivi de '(')
                        remaining = line[match.end() :].lstrip()
                        if remaining.startswith("("):
                            text_widget.insert("end", token, "js_function")
                        else:
                            text_widget.insert("end", token, "js_variable")
                elif match.group(8):  # Opérateurs
                    text_widget.insert("end", token, "js_operator")
                elif match.group(9):  # Ponctuation
                    text_widget.insert("end", token, "js_punctuation")
                else:
                    text_widget.insert("end", token, "code_block")

                pos = match.end()

            # Ajouter le reste de la ligne
            if pos < len(line):
                text_widget.insert("end", line[pos:], "code_block")

        text_widget.insert("end", "\n")

    def _insert_html_code_block(self, text_widget, code):
        """Coloration syntaxique pour HTML avec couleurs VS Code"""
        text_widget.insert("end", "\n")
        code = code.strip()
        if not code:
            text_widget.insert("end", "\n")
            return

        # Pattern pour les balises HTML
        html_pattern = r"""
            (<!--.*?-->)|                    # Commentaires HTML
            (</?[a-zA-Z][\w-]*(?:\s+[^>]*)?>) | # Balises ouvrantes/fermantes
            ([^<]+)                          # Contenu texte
        """

        for match in re.finditer(html_pattern, code, re.VERBOSE | re.DOTALL):
            content = match.group(0)

            if match.group(1):  # Commentaire
                text_widget.insert("end", content, "html_comment")
            elif match.group(2):  # Balise
                self._parse_html_tag(text_widget, content)
            else:  # Texte
                text_widget.insert("end", content, "html_text")

        text_widget.insert("end", "\n")

    def _parse_html_tag(self, text_widget, tag_content):
        """Parse une balise HTML pour colorer ses composants"""
        # Pattern pour décomposer une balise
        tag_pattern = r"(</?)([\w-]+)(\s+[^>]*)?(>)"
        match = re.match(tag_pattern, tag_content)

        if match:
            text_widget.insert("end", match.group(1), "html_punctuation")  # < ou </
            text_widget.insert("end", match.group(2), "html_tag")  # nom de balise

            # Attributs s'il y en a
            if match.group(3):
                self._parse_html_attributes(text_widget, match.group(3))

            text_widget.insert("end", match.group(4), "html_punctuation")  # >
        else:
            text_widget.insert("end", tag_content, "html_tag")

    def _parse_html_attributes(self, text_widget, attr_content):
        """Parse les attributs HTML"""
        # Pattern pour les attributs
        attr_pattern = r'(\s*)([\w-]+)(=)("(?:[^"\\]|\\.)*"|\'(?:[^\'\\]|\\.)*\'|\S+)?'

        pos = 0
        for match in re.finditer(attr_pattern, attr_content):
            # Espaces avant l'attribut
            if match.start() > pos:
                text_widget.insert(
                    "end", attr_content[pos : match.start()], "html_text"
                )

            text_widget.insert("end", match.group(1), "html_text")  # espaces
            text_widget.insert("end", match.group(2), "html_attribute")  # nom attribut
            text_widget.insert("end", match.group(3), "html_punctuation")  # =

            if match.group(4):  # valeur
                text_widget.insert("end", match.group(4), "html_value")

            pos = match.end()

        # Reste du texte
        if pos < len(attr_content):
            text_widget.insert("end", attr_content[pos:], "html_text")

    def _insert_css_code_block(self, text_widget, code):
        """Coloration syntaxique pour CSS avec couleurs VS Code"""
        text_widget.insert("end", "\n")
        code = code.strip()
        if not code:
            text_widget.insert("end", "\n")
            return

        # Pattern CSS global
        css_pattern = r"""
            (/\*.*?\*/)|                     # Commentaires
            ([\w\-#\.:\[\](),\s>+~*]+)(\s*\{)|  # Sélecteurs + {
            ([\w-]+)(\s*:\s*)([^;}]+)(;?)|   # Propriété: valeur;
            (\})|                            # }
            ([^{}]+)                         # Autres contenus
        """

        for match in re.finditer(css_pattern, code, re.VERBOSE | re.DOTALL):
            if match.group(1):  # Commentaire
                text_widget.insert("end", match.group(1), "css_comment")
            elif match.group(2) and match.group(3):  # Sélecteur + {
                text_widget.insert("end", match.group(2), "css_selector")
                text_widget.insert("end", match.group(3), "css_punctuation")
            elif match.group(4):  # Propriété CSS
                text_widget.insert("end", match.group(4), "css_property")
                text_widget.insert("end", match.group(5), "css_punctuation")  # :
                self._parse_css_value(text_widget, match.group(6))  # valeur
                if match.group(7):  # ;
                    text_widget.insert("end", match.group(7), "css_punctuation")
            elif match.group(8):  # }
                text_widget.insert("end", match.group(8), "css_punctuation")
            else:
                text_widget.insert("end", match.group(0), "code_block")

        text_widget.insert("end", "\n")

    def _parse_css_value(self, text_widget, value):
        """Parse une valeur CSS pour la colorer"""
        # Pattern pour les valeurs CSS
        value_pattern = r"""
            ("(?:[^"\\]|\\.)*")|            # Chaînes double quotes
            ('(?:[^'\\]|\\.)*')|            # Chaînes simple quotes
            (\b\d+(?:\.\d+)?(?:px|em|rem|%|vh|vw|pt|pc|in|cm|mm|ex|ch|vmin|vmax|deg|rad|turn|s|ms)?\b)| # Nombres avec unités
            (#[0-9a-fA-F]{3,8})|            # Couleurs hexadécimales
            (\b(?:rgb|rgba|hsl|hsla|var|calc|url)\([^)]*\))| # Fonctions CSS
            ([^;}\s]+)                      # Autres valeurs
        """

        for match in re.finditer(value_pattern, value, re.VERBOSE):
            token = match.group(0)

            if match.group(1) or match.group(2):  # Chaînes
                text_widget.insert("end", token, "css_string")
            elif match.group(3):  # Nombres avec unités
                text_widget.insert("end", token, "css_number")
            elif match.group(4):  # Couleurs hex
                text_widget.insert("end", token, "css_number")
            elif match.group(5):  # Fonctions CSS
                text_widget.insert("end", token, "css_value")
            else:  # Autres valeurs
                text_widget.insert("end", token, "css_value")

    def _insert_bash_code_block(self, text_widget, code):
        """Coloration syntaxique pour Bash/Shell avec couleurs VS Code"""
        text_widget.insert("end", "\n")
        code = code.strip()
        if not code:
            text_widget.insert("end", "\n")
            return

        # Mots-clés Bash
        bash_keywords = {
            "if",
            "then",
            "else",
            "elif",
            "fi",
            "for",
            "while",
            "until",
            "do",
            "done",
            "case",
            "esac",
            "in",
            "function",
            "return",
            "exit",
            "break",
            "continue",
            "local",
            "export",
            "readonly",
            "declare",
            "set",
            "unset",
            "source",
            "alias",
            "unalias",
            "type",
            "which",
            "whereis",
            "echo",
            "printf",
            "test",
            "true",
            "false",
        }

        lines = code.split("\n")
        for i, line in enumerate(lines):
            if i > 0:
                text_widget.insert("end", "\n", "code_block")

            # Skip shebang
            if line.startswith("#!"):
                text_widget.insert("end", line, "bash_comment")
                continue

            # Tokenisation Bash
            token_pattern = r"""
                (\#.*$)|                     # Commentaires
                ("(?:[^"\\]|\\.)*")|         # Chaînes double quotes
                ('(?:[^'\\]|\\.)*')|         # Chaînes simple quotes
                (\$\{[^}]*\}|\$\w+|\$\d+)|   # Variables
                (\b\d+\.?\d*\b)|             # Nombres
                (\b[a-zA-Z_]\w*\b)|          # Identifiants
                ([<>=!&|;()\[\]{}]|<<|>>|\|\||&&|==|!=|<=|>=|\+=|-=|\*=|/=|%=)| # Opérateurs
                (\s+)                        # Espaces
            """

            pos = 0
            for match in re.finditer(token_pattern, line, re.VERBOSE):
                # Ajouter le texte avant le match
                if match.start() > pos:
                    text_widget.insert("end", line[pos : match.start()], "code_block")

                token = match.group(0)

                if match.group(1):  # Commentaire
                    text_widget.insert("end", token, "bash_comment")
                elif match.group(2) or match.group(3):  # Chaînes
                    text_widget.insert("end", token, "bash_string")
                elif match.group(4):  # Variables
                    text_widget.insert("end", token, "bash_variable")
                elif match.group(5):  # Nombres
                    text_widget.insert("end", token, "bash_number")
                elif match.group(6):  # Identifiants
                    if token in bash_keywords:
                        text_widget.insert("end", token, "bash_keyword")
                    else:
                        text_widget.insert("end", token, "bash_command")
                elif match.group(7):  # Opérateurs
                    text_widget.insert("end", token, "bash_operator")
                else:
                    text_widget.insert("end", token, "code_block")

                pos = match.end()

            # Reste de la ligne
            if pos < len(line):
                text_widget.insert("end", line[pos:], "code_block")

        text_widget.insert("end", "\n")

    def _insert_sql_code_block(self, text_widget, code):
        """Coloration syntaxique pour SQL avec couleurs VS Code"""
        text_widget.insert("end", "\n")
        code = code.strip()
        if not code:
            text_widget.insert("end", "\n")
            return

        # Mots-clés SQL
        sql_keywords = {
            "SELECT",
            "FROM",
            "WHERE",
            "JOIN",
            "INNER",
            "LEFT",
            "RIGHT",
            "FULL",
            "OUTER",
            "ON",
            "AND",
            "OR",
            "NOT",
            "IN",
            "EXISTS",
            "BETWEEN",
            "LIKE",
            "IS",
            "NULL",
            "INSERT",
            "INTO",
            "VALUES",
            "UPDATE",
            "SET",
            "DELETE",
            "CREATE",
            "TABLE",
            "ALTER",
            "DROP",
            "INDEX",
            "VIEW",
            "DATABASE",
            "SCHEMA",
            "PRIMARY",
            "KEY",
            "FOREIGN",
            "REFERENCES",
            "UNIQUE",
            "CHECK",
            "DEFAULT",
            "AUTO_INCREMENT",
            "ORDER",
            "BY",
            "GROUP",
            "HAVING",
            "DISTINCT",
            "LIMIT",
            "OFFSET",
            "UNION",
            "CASE",
            "WHEN",
            "THEN",
            "ELSE",
            "END",
            "AS",
            "ASC",
            "DESC",
        }

        # Fonctions SQL communes
        sql_functions = {
            "COUNT",
            "SUM",
            "AVG",
            "MIN",
            "MAX",
            "ROUND",
            "ABS",
            "UPPER",
            "LOWER",
            "LENGTH",
            "SUBSTRING",
            "CONCAT",
            "NOW",
            "DATE",
            "YEAR",
            "MONTH",
            "DAY",
        }

        lines = code.split("\n")
        for i, line in enumerate(lines):
            if i > 0:
                text_widget.insert("end", "\n", "code_block")

            # Tokenisation SQL
            token_pattern = r"""
                (--.*$)|                     # Commentaires --
                (/\*.*?\*/)|                 # Commentaires /* */
                ('(?:[^'\\]|\\.)*')|         # Chaînes simple quotes
                (\b\d+\.?\d*\b)|             # Nombres
                (\b[a-zA-Z_]\w*\b)|          # Identifiants
                ([=<>!]+|<=|>=|<>|\|\|)|     # Opérateurs
                ([(),;.])|                   # Ponctuation
                (\s+)                        # Espaces
            """

            pos = 0
            for match in re.finditer(token_pattern, line, re.VERBOSE | re.DOTALL):
                # Ajouter le texte avant le match
                if match.start() > pos:
                    text_widget.insert("end", line[pos : match.start()], "code_block")

                token = match.group(0)

                if match.group(1) or match.group(2):  # Commentaires
                    text_widget.insert("end", token, "sql_comment")
                elif match.group(3):  # Chaînes
                    text_widget.insert("end", token, "sql_string")
                elif match.group(4):  # Nombres
                    text_widget.insert("end", token, "sql_number")
                elif match.group(5):  # Identifiants
                    token_upper = token.upper()
                    if token_upper in sql_keywords:
                        text_widget.insert("end", token, "sql_keyword")
                    elif token_upper in sql_functions:
                        text_widget.insert("end", token, "sql_function")
                    else:
                        text_widget.insert("end", token, "sql_identifier")
                elif match.group(6):  # Opérateurs
                    text_widget.insert("end", token, "sql_operator")
                elif match.group(7):  # Ponctuation
                    text_widget.insert("end", token, "sql_punctuation")
                else:
                    text_widget.insert("end", token, "code_block")

                pos = match.end()

            # Reste de la ligne
            if pos < len(line):
                text_widget.insert("end", line[pos:], "code_block")

        text_widget.insert("end", "\n")

    def _insert_dockerfile_code_block(self, text_widget, code):
        """Coloration syntaxique pour Dockerfile avec couleurs VS Code"""
        text_widget.insert("end", "\n")
        code = code.strip()
        if not code:
            text_widget.insert("end", "\n")
            return

        # Instructions Dockerfile
        dockerfile_instructions = {
            "FROM",
            "RUN",
            "COPY",
            "ADD",
            "CMD",
            "ENTRYPOINT",
            "WORKDIR",
            "EXPOSE",
            "ENV",
            "ARG",
            "VOLUME",
            "USER",
            "LABEL",
            "MAINTAINER",
            "ONBUILD",
            "STOPSIGNAL",
            "HEALTHCHECK",
            "SHELL",
        }

        lines = code.split("\n")
        for i, line in enumerate(lines):
            if i > 0:
                text_widget.insert("end", "\n", "code_block")

            line_stripped = line.strip()

            # Commentaires
            if line_stripped.startswith("#"):
                text_widget.insert("end", line, "dockerfile_comment")
                continue

            # Instructions Dockerfile
            instruction_match = re.match(r"^(\s*)(\w+)(\s+)(.*)", line)
            if instruction_match:
                indent, instruction, space, rest = instruction_match.groups()

                text_widget.insert("end", indent, "code_block")

                if instruction.upper() in dockerfile_instructions:
                    text_widget.insert("end", instruction, "dockerfile_instruction")
                else:
                    text_widget.insert("end", instruction, "code_block")

                text_widget.insert("end", space, "code_block")

                # Parser le reste selon l'instruction
                self._parse_dockerfile_rest(text_widget, instruction.upper(), rest)
            else:
                text_widget.insert("end", line, "code_block")

        text_widget.insert("end", "\n")

    def _parse_dockerfile_rest(self, text_widget, instruction, rest):
        """Parse le reste d'une ligne Dockerfile selon l'instruction"""
        # Variables ${VAR} ou $VAR
        _var_pattern = r"(\$\{[^}]*\}|\$\w+)"
        # Chaînes entre guillemets
        _string_pattern = r'("(?:[^"\\]|\\.)*"|\'(?:[^\'\\]|\\.)*\')'
        # Flags comme --from=
        flag_pattern = r"(--[\w-]+(?:=\S+)?)"

        pos = 0

        # Traiter les flags d'abord (pour certaines instructions)
        if instruction in ["COPY", "ADD", "RUN"]:
            for match in re.finditer(flag_pattern, rest):
                if match.start() > pos:
                    self._parse_simple_dockerfile_content(
                        text_widget, rest[pos : match.start()]
                    )
                text_widget.insert("end", match.group(1), "dockerfile_flag")
                pos = match.end()

        # Traiter le reste
        remaining = rest[pos:]
        self._parse_simple_dockerfile_content(text_widget, remaining)

    def _parse_simple_dockerfile_content(self, text_widget, content):
        """Parse le contenu simple d'une ligne Dockerfile"""
        # Pattern pour variables et chaînes
        pattern = r'(\$\{[^}]*\}|\$\w+)|("(?:[^"\\]|\\.)*"|\'(?:[^\'\\]|\\.)*\')'

        pos = 0
        for match in re.finditer(pattern, content):
            if match.start() > pos:
                text_widget.insert("end", content[pos : match.start()], "code_block")

            if match.group(1):  # Variable
                text_widget.insert("end", match.group(1), "dockerfile_variable")
            elif match.group(2):  # Chaîne
                text_widget.insert("end", match.group(2), "dockerfile_string")

            pos = match.end()

        if pos < len(content):
            # Vérifier si le reste ressemble à un chemin
            remaining = content[pos:]
            if re.match(r"^[/.\w-]+$", remaining.strip()):
                text_widget.insert("end", remaining, "dockerfile_path")
            else:
                text_widget.insert("end", remaining, "code_block")

    def _insert_json_code_block(self, text_widget, code):
        """Coloration syntaxique pour JSON avec couleurs VS Code"""
        text_widget.insert("end", "\n")
        code = code.strip()
        if not code:
            text_widget.insert("end", "\n")
            return

        # Essayer de parser le JSON pour une coloration plus précise
        try:
            # Vérifier si c'est du JSON valide
            json.loads(code)

            # Pattern JSON
            json_pattern = r"""
                ("(?:[^"\\]|\\.)*")(\s*:\s*)|  # Clés JSON
                ("(?:[^"\\]|\\.)*")|           # Chaînes
                (\b(?:true|false|null)\b)|     # Mots-clés JSON
                (\b-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?\b)| # Nombres
                ([\[\]{},:])|                  # Structures JSON
                (\s+)                          # Espaces
            """

            for match in re.finditer(json_pattern, code, re.VERBOSE):
                if match.group(1) and match.group(2):  # Clé + :
                    text_widget.insert(
                        "end", match.group(1), "js_property"
                    )  # Clé en couleur propriété
                    text_widget.insert("end", match.group(2), "js_punctuation")  # :
                elif match.group(3):  # Chaîne valeur
                    text_widget.insert("end", match.group(3), "js_string")
                elif match.group(4):  # true/false/null
                    text_widget.insert("end", match.group(4), "js_keyword")
                elif match.group(5):  # Nombres
                    text_widget.insert("end", match.group(5), "js_number")
                elif match.group(6):  # Structures
                    text_widget.insert("end", match.group(6), "js_punctuation")
                else:
                    text_widget.insert("end", match.group(0), "code_block")

        except json.JSONDecodeError:
            # JSON invalide, coloration basique
            text_widget.insert("end", code, "code_block")

        text_widget.insert("end", "\n")

    # === NOUVELLES FONCTIONS SANS NEWLINES AUTOMATIQUES ===

    def _insert_javascript_code_block_without_newlines(self, text_widget, code):
        """Version sans newlines automatiques pour JavaScript"""
        code = code.strip()
        if not code:
            return

        # Mots-clés JavaScript
        js_keywords = {
            "var",
            "let",
            "const",
            "function",
            "return",
            "if",
            "else",
            "for",
            "while",
            "do",
            "switch",
            "case",
            "default",
            "break",
            "continue",
            "try",
            "catch",
            "finally",
            "throw",
            "new",
            "this",
            "super",
            "class",
            "extends",
            "import",
            "export",
            "from",
            "async",
            "await",
            "yield",
            "typeof",
            "instanceof",
            "in",
            "of",
            "true",
            "false",
            "null",
            "undefined",
        }

        lines = code.split("\n")
        for i, line in enumerate(lines):
            if i > 0:
                text_widget.insert("end", "\n", "code_block")

            # Tokenisation JavaScript
            token_pattern = r"""
                (//.*$)|                     # Commentaires //
                (/\*.*?\*/)|                 # Commentaires /* */
                ("(?:[^"\\]|\\.)*")|         # Chaînes double quotes
                ('(?:[^'\\]|\\.)*')|         # Chaînes simple quotes
                (`(?:[^`\\]|\\.)*`)|         # Template literals
                (\b\d+\.?\d*\b)|             # Nombres
                (\b[a-zA-Z_$]\w*\b)|         # Identifiants
                ([+\-*/%=<>!&|^~]|===|!==|==|!=|<=|>=|&&|\|\||<<|>>|\+=|-=|\*=|/=|%=|&=|\|=|\^=|<<=|>>=|\+\+|--)|  # Opérateurs
                ([\(\)\[\]{},;:.])|          # Ponctuation
                (\s+)                        # Espaces
            """

            pos = 0
            for match in re.finditer(token_pattern, line, re.VERBOSE | re.DOTALL):
                # Ajouter le texte avant le match si nécessaire
                if match.start() > pos:
                    text_widget.insert("end", line[pos : match.start()], "code_block")

                token = match.group(0)

                if match.group(1):  # Commentaire //
                    text_widget.insert("end", token, "js_comment")
                elif match.group(2):  # Commentaire /* */
                    text_widget.insert("end", token, "js_comment")
                elif match.group(3) or match.group(4) or match.group(5):  # Chaînes
                    text_widget.insert("end", token, "js_string")
                elif match.group(6):  # Nombres
                    text_widget.insert("end", token, "js_number")
                elif match.group(7):  # Identifiants
                    if token in js_keywords:
                        text_widget.insert("end", token, "js_keyword")
                    else:
                        # Vérifier si c'est une fonction (suivi de '(')
                        remaining = line[match.end() :].lstrip()
                        if remaining.startswith("("):
                            text_widget.insert("end", token, "js_function")
                        else:
                            text_widget.insert("end", token, "js_variable")
                elif match.group(8):  # Opérateurs
                    text_widget.insert("end", token, "js_operator")
                elif match.group(9):  # Ponctuation
                    text_widget.insert("end", token, "js_punctuation")
                else:
                    text_widget.insert("end", token, "code_block")

                pos = match.end()

            # Ajouter le reste de la ligne
            if pos < len(line):
                text_widget.insert("end", line[pos:], "code_block")

    def _insert_html_code_block_without_newlines(self, text_widget, code):
        """Version sans newlines automatiques pour HTML"""
        code = code.strip()
        if not code:
            return

        # Pattern pour les balises HTML
        html_pattern = r"""
            (<!--.*?-->)|                    # Commentaires HTML
            (</?[a-zA-Z][\w-]*(?:\s+[^>]*)?>) | # Balises ouvrantes/fermantes
            ([^<]+)                          # Contenu texte
        """

        for match in re.finditer(html_pattern, code, re.VERBOSE | re.DOTALL):
            content = match.group(0)

            if match.group(1):  # Commentaire
                text_widget.insert("end", content, "html_comment")
            elif match.group(2):  # Balise
                self._parse_html_tag(text_widget, content)
            else:  # Texte
                text_widget.insert("end", content, "html_text")

    def _insert_css_code_block_without_newlines(self, text_widget, code):
        """Version sans newlines automatiques pour CSS"""
        code = code.strip()
        if not code:
            return

        # Pattern CSS global (version simplifiée)
        lines = code.split("\n")
        for i, line in enumerate(lines):
            if i > 0:
                text_widget.insert("end", "\n", "code_block")

            line_stripped = line.strip()

            # Commentaires CSS
            if "/*" in line and "*/" in line:
                text_widget.insert("end", line, "css_comment")
            # Sélecteurs (lignes se terminant par {)
            elif line_stripped.endswith("{"):
                selector = line_stripped[:-1].strip()
                text_widget.insert("end", selector, "css_selector")
                text_widget.insert("end", " {", "css_punctuation")
            # Propriétés CSS (contenant :)
            elif ":" in line and not line_stripped.startswith("/*"):
                parts = line.split(":", 1)
                if len(parts) == 2:
                    prop = parts[0].strip()
                    value = parts[1].strip()

                    text_widget.insert(
                        "end", " " * (len(line) - len(line.lstrip())), "code_block"
                    )  # Indentation
                    text_widget.insert("end", prop, "css_property")
                    text_widget.insert("end", ": ", "css_punctuation")

                    # Enlever le ; final si présent
                    if value.endswith(";"):
                        value_content = value[:-1]
                        text_widget.insert("end", value_content, "css_value")
                        text_widget.insert("end", ";", "css_punctuation")
                    else:
                        text_widget.insert("end", value, "css_value")
                else:
                    text_widget.insert("end", line, "code_block")
            # Fermeture de bloc
            elif line_stripped == "}":
                text_widget.insert("end", line, "css_punctuation")
            else:
                text_widget.insert("end", line, "code_block")

    def _insert_bash_code_block_without_newlines(self, text_widget, code):
        """Version sans newlines automatiques pour Bash"""
        code = code.strip()
        if not code:
            return

        # Mots-clés Bash essentiels
        bash_keywords = {
            "if",
            "then",
            "else",
            "elif",
            "fi",
            "for",
            "while",
            "do",
            "done",
            "case",
            "esac",
            "function",
            "return",
            "exit",
            "break",
            "continue",
            "export",
            "local",
            "echo",
            "printf",
        }

        lines = code.split("\n")
        for i, line in enumerate(lines):
            if i > 0:
                text_widget.insert("end", "\n", "code_block")

            # Shebang
            if line.startswith("#!"):
                text_widget.insert("end", line, "bash_comment")
                continue

            # Commentaires
            if line.strip().startswith("#"):
                text_widget.insert("end", line, "bash_comment")
                continue

            # Tokenisation simple
            words = line.split()
            current_pos = 0

            for word in words:
                # Trouver la position du mot dans la ligne
                word_start = line.find(word, current_pos)

                # Ajouter les espaces avant le mot
                if word_start > current_pos:
                    text_widget.insert(
                        "end", line[current_pos:word_start], "code_block"
                    )

                # Colorer le mot
                if word.startswith("$"):
                    text_widget.insert("end", word, "bash_variable")
                elif word.startswith('"') or word.startswith("'"):
                    text_widget.insert("end", word, "bash_string")
                elif word.isdigit():
                    text_widget.insert("end", word, "bash_number")
                elif word in bash_keywords:
                    text_widget.insert("end", word, "bash_keyword")
                else:
                    text_widget.insert("end", word, "bash_command")

                current_pos = word_start + len(word)

            # Ajouter le reste de la ligne (espaces finaux, etc.)
            if current_pos < len(line):
                text_widget.insert("end", line[current_pos:], "code_block")

    def _insert_sql_code_block_without_newlines(self, text_widget, code):
        """Version sans newlines automatiques pour SQL"""
        code = code.strip()
        if not code:
            return

        # Mots-clés SQL essentiels
        sql_keywords = {
            "SELECT",
            "FROM",
            "WHERE",
            "JOIN",
            "INNER",
            "LEFT",
            "RIGHT",
            "ON",
            "AND",
            "OR",
            "INSERT",
            "INTO",
            "VALUES",
            "UPDATE",
            "SET",
            "DELETE",
            "CREATE",
            "TABLE",
            "ALTER",
            "DROP",
            "ORDER",
            "BY",
            "GROUP",
            "HAVING",
        }

        lines = code.split("\n")
        for i, line in enumerate(lines):
            if i > 0:
                text_widget.insert("end", "\n", "code_block")

            # Commentaires
            if line.strip().startswith("--"):
                text_widget.insert("end", line, "sql_comment")
                continue

            # Tokenisation simple par mots
            words = re.findall(r"\S+|\s+", line)

            for word in words:
                if word.isspace():
                    text_widget.insert("end", word, "code_block")
                elif word.startswith("'") and word.endswith("'"):
                    text_widget.insert("end", word, "sql_string")
                elif word.replace(".", "").isdigit():
                    text_widget.insert("end", word, "sql_number")
                elif word.upper() in sql_keywords:
                    text_widget.insert("end", word, "sql_keyword")
                elif word in [",", ";", "(", ")", "=", "<", ">", "<=", ">="]:
                    text_widget.insert("end", word, "sql_punctuation")
                else:
                    text_widget.insert("end", word, "sql_identifier")

    def _insert_dockerfile_code_block_without_newlines(self, text_widget, code):
        """Version sans newlines automatiques pour Dockerfile"""
        code = code.strip()
        if not code:
            return

        # Instructions Dockerfile
        dockerfile_instructions = {
            "FROM",
            "RUN",
            "COPY",
            "ADD",
            "CMD",
            "ENTRYPOINT",
            "WORKDIR",
            "EXPOSE",
            "ENV",
            "ARG",
            "VOLUME",
            "USER",
            "LABEL",
        }

        lines = code.split("\n")
        for i, line in enumerate(lines):
            if i > 0:
                text_widget.insert("end", "\n", "code_block")

            line_stripped = line.strip()

            # Commentaires
            if line_stripped.startswith("#"):
                text_widget.insert("end", line, "dockerfile_comment")
                continue

            # Instructions
            words = line.split()
            if words and words[0].upper() in dockerfile_instructions:
                # Indentation
                indent = len(line) - len(line.lstrip())
                if indent > 0:
                    text_widget.insert("end", line[:indent], "code_block")

                # Instruction
                text_widget.insert("end", words[0], "dockerfile_instruction")

                # Reste de la ligne
                rest = line[indent + len(words[0]) :]
                if rest:
                    # Variables simples
                    if "$" in rest:
                        parts = re.split(r"(\$\w+|\$\{[^}]*\})", rest)
                        for part in parts:
                            if part.startswith("$"):
                                text_widget.insert("end", part, "dockerfile_variable")
                            else:
                                text_widget.insert("end", part, "dockerfile_string")
                    else:
                        text_widget.insert("end", rest, "dockerfile_string")
            else:
                text_widget.insert("end", line, "code_block")

    def _insert_json_code_block_without_newlines(self, text_widget, code):
        """Version sans newlines automatiques pour JSON"""
        code = code.strip()
        if not code:
            return

        # Tokenisation JSON simple
        json_pattern = r"""
            ("(?:[^"\\]|\\.)*")(\s*:\s*)|  # Clés JSON + :
            ("(?:[^"\\]|\\.)*")|           # Chaînes
            (\b(?:true|false|null)\b)|     # Mots-clés JSON
            (\b-?\d+(?:\.\d+)?\b)|         # Nombres
            ([\[\]{},:])|                  # Structures JSON
            (\s+)                          # Espaces
        """

        for match in re.finditer(json_pattern, code, re.VERBOSE):
            if match.group(1) and match.group(2):  # Clé + :
                text_widget.insert("end", match.group(1), "js_property")
                text_widget.insert("end", match.group(2), "js_punctuation")
            elif match.group(3):  # Chaîne
                text_widget.insert("end", match.group(3), "js_string")
            elif match.group(4):  # true/false/null
                text_widget.insert("end", match.group(4), "js_keyword")
            elif match.group(5):  # Nombres
                text_widget.insert("end", match.group(5), "js_number")
            elif match.group(6):  # Structures
                text_widget.insert("end", match.group(6), "js_punctuation")
            else:
                text_widget.insert("end", match.group(0), "code_block")

    def download_file_to_downloads(self, source_path, filename):
        """Télécharge un fichier vers le dossier Téléchargements de l'utilisateur"""
        try:
            # Obtenir le dossier Téléchargements
            downloads_folder = Path.home() / "Downloads"
            if not downloads_folder.exists():
                downloads_folder = Path.home() / "Téléchargements"  # Pour Windows FR

            # Créer le chemin de destination
            dest_path = downloads_folder / filename

            # Copier le fichier
            shutil.copy2(source_path, dest_path)

            # Afficher la notification
            self.show_copy_notification(
                f"✅ Votre fichier {filename} a été téléchargé dans : {dest_path}"
            )
            return True

        except Exception as e:
            self.show_copy_notification(f"❌ Erreur de téléchargement : {str(e)}")
            return False

    def show_copy_notification(self, message):
        """Affiche une notification GUI élégante pour la copie"""
        try:
            # Créer une notification temporaire
            if self.use_ctk:
                notification = ctk.CTkFrame(
                    self.main_container,
                    fg_color="#10b981",  # Vert succès
                    corner_radius=8,
                    border_width=0,
                )

                notif_label = ctk.CTkLabel(
                    notification,
                    text=message,
                    text_color="#ffffff",
                    font=("Segoe UI", 12, "bold"),
                )
            else:
                notification = tk.Frame(
                    self.main_container, bg="#10b981", relief="flat"
                )

                notif_label = tk.Label(
                    notification,
                    text=message,
                    fg="#ffffff",
                    bg="#10b981",
                    font=("Segoe UI", 12, "bold"),
                )

            notif_label.pack(padx=15, pady=8)

            # Positionner en haut à droite
            notification.place(relx=0.95, rely=0.1, anchor="ne")

            # Supprimer automatiquement après 4 secondes
            self.root.after(4000, notification.destroy)

        except Exception:
            pass

    def create_copy_menu_with_notification(self, widget, original_text):
        """Menu contextuel avec notification GUI"""

        def copy_text():
            try:
                self.root.clipboard_clear()
                self.root.clipboard_append(original_text)
                self.show_copy_notification("Texte copié !")
            except Exception:
                self.show_copy_notification("❌ Erreur de copie")

        def select_all_and_copy():
            """Sélectionne tout le texte et le copie"""
            copy_text()  # Pour l'instant, même action

        # Créer le menu contextuel
        context_menu = tk.Menu(self.root, tearoff=0)
        context_menu.add_command(label="📋 Copier le texte", command=copy_text)
        context_menu.add_separator()
        context_menu.add_command(
            label="🔍 Tout sélectionner et copier", command=select_all_and_copy
        )

        def show_context_menu(event):
            try:
                context_menu.tk_popup(event.x_root, event.y_root)
            except Exception:
                pass
            finally:
                context_menu.grab_release()

        # Bind du clic droit
        widget.bind("<Button-3>", show_context_menu)  # Windows/Linux
        widget.bind("<Button-2>", show_context_menu)  # macOS (parfois)
        widget.bind("<Control-Button-1>", show_context_menu)  # Ctrl+clic

        return context_menu

    def insert_formatted_text_tkinter(self, text_widget, text):
        """Version AMÉLIORÉE qui gère les liens ET le formatage Python"""
        text_widget.delete("1.0", "end")

        # Configuration complète des tags
        self._configure_all_formatting_tags(text_widget)

        # 🔧 CORRECTION DU TEXTE avant parsing
        text = re.sub(r"^(\s*)Args:\s*$", r"\1**Args:**", text, flags=re.MULTILINE)
        text = re.sub(
            r"^(\s*)Returns:\s*$", r"\1**Returns:**", text, flags=re.MULTILINE
        )
        text = re.sub(r"(?<!\n)(^##\d+\.\s+.*$)", r"\n\1", text, flags=re.MULTILINE)

        # Correction du nom de fichier temporaire
        temp_file_match = re.search(
            r'Explication détaillée du fichier [`"]?(tmp\w+\.py)[`"]?', text
        )
        if temp_file_match and hasattr(self, "conversation_history"):
            for hist in reversed(self.conversation_history):
                if "text" in hist and isinstance(hist["text"], str):
                    real_file = re.search(r"document: '([\w\-.]+\.py)'", hist["text"])
                    if real_file:
                        text = text.replace(
                            temp_file_match.group(1), real_file.group(1)
                        )
                        break
            else:
                py_files = [f for f in os.listdir(".") if f.endswith(".py")]
                if py_files:
                    text = text.replace(temp_file_match.group(1), py_files[0])

        # 🔧 NOUVEAU : Traitement des liens AVANT le parsing général
        text_with_links_processed = self._process_links_preserve_formatting(
            text, text_widget
        )

        # 🔧 UTILISATION DU NOUVEAU SYSTÈME DE FORMATAGE AMÉLIORÉ
        self._insert_markdown_segments(text_widget, text_with_links_processed)

        text_widget.update_idletasks()

    def _configure_all_formatting_tags(self, text_widget):
        """Configure TOUS les tags de formatage - Version unifiée et optimisée"""
        base_font = ("Segoe UI", 12)

        # === TAGS DE FORMATAGE UNIFIÉ ===
        text_widget.tag_configure(
            "normal", font=base_font, foreground=self.colors["text_primary"]
        )
        text_widget.tag_configure(
            "bold",
            font=("Segoe UI", 12, "bold"),
            foreground=self.colors["text_primary"],
        )
        text_widget.tag_configure(
            "italic",
            font=("Segoe UI", 12, "italic"),
            foreground=self.colors["text_primary"],
        )
        text_widget.tag_configure("code", font=("Consolas", 11), foreground="#f8f8f2")

        # === TAGS DE TITRES ===
        text_widget.tag_configure(
            "title_1",
            font=("Segoe UI", 15, "bold"),
            foreground=self.colors["text_primary"],
        )  # Réduit de 18 à 16
        text_widget.tag_configure(
            "title_2",
            font=("Segoe UI", 13, "bold"),
            foreground=self.colors["text_primary"],
        )  # Réduit de 16 à 14
        text_widget.tag_configure(
            "title_3",
            font=("Segoe UI", 13, "bold"),
            foreground=self.colors["text_primary"],
        )

        # === TAGS SPÉCIAUX ===
        text_widget.tag_configure(
            "link", foreground="#3b82f6", underline=1, font=base_font
        )
        text_widget.tag_configure(
            "link_temp", foreground="#3b82f6", underline=1, font=base_font
        )  # Lien pendant animation - même style que link
        text_widget.tag_configure(
            "docstring", font=("Consolas", 11, "italic"), foreground="#ff8c00"
        )
        text_widget.tag_configure("hidden", elide=True)  # Pour masquer les balises

        # === TAG CODE_BLOCK (pour le code générique et whitespace) ===
        text_widget.tag_configure(
            "code_block", font=("Consolas", 11), foreground="#d4d4d4"
        )
        text_widget.tag_configure("code_block_marker", elide=True)  # Masquer les ```

        # === TAGS PYTHON (compatibilité) ===
        python_tags = {
            "Token.Keyword": ("#569cd6", "bold"),
            "Token.Keyword.Constant": ("#569cd6", "bold"),
            "Token.Keyword.Declaration": ("#569cd6", "bold"),
            "Token.Keyword.Namespace": ("#569cd6", "bold"),
            "Token.Keyword.Pseudo": ("#569cd6", "bold"),
            "Token.Keyword.Reserved": ("#569cd6", "bold"),
            "Token.Keyword.Type": ("#4ec9b0", "bold"),
            "Token.Literal.String": ("#ce9178", "normal"),
            "Token.Literal.String.Double": ("#ce9178", "normal"),
            "Token.Literal.String.Single": ("#ce9178", "normal"),
            "Token.String": ("#ce9178", "normal"),
            "Token.String.Double": ("#ce9178", "normal"),
            "Token.String.Single": ("#ce9178", "normal"),
            "Token.Comment": ("#6a9955", "italic"),
            "Token.Comment.Single": ("#6a9955", "italic"),
            "Token.Comment.Multiline": ("#6a9955", "italic"),
            "Token.Name.Function": ("#dcdcaa", "normal"),
            "Token.Name.Function.Magic": ("#dcdcaa", "normal"),
            "Token.Name.Class": ("#4ec9b0", "bold"),
            "Token.Name.Builtin": ("#dcdcaa", "normal"),
            "Token.Name.Builtin.Pseudo": ("#dcdcaa", "normal"),
            "Token.Literal.Number": ("#b5cea8", "normal"),
            "Token.Literal.Number.Integer": ("#b5cea8", "normal"),
            "Token.Literal.Number.Float": ("#b5cea8", "normal"),
            "Token.Number": ("#b5cea8", "normal"),
            "Token.Number.Integer": ("#b5cea8", "normal"),
            "Token.Number.Float": ("#b5cea8", "normal"),
            "Token.Operator": ("#d4d4d4", "normal"),
            "Token.Punctuation": ("#d4d4d4", "normal"),
            "Token.Name": ("#9cdcfe", "normal"),
            "Token.Name.Variable": ("#9cdcfe", "normal"),
            "Token.Name.Attribute": ("#9cdcfe", "normal"),
            "Token.Name.Constant": ("#569cd6", "bold"),
        }

        for tag, (color, weight) in python_tags.items():
            if weight == "bold":
                text_widget.tag_configure(
                    tag, foreground=color, font=("Consolas", 11, "bold")
                )
            elif weight == "italic":
                text_widget.tag_configure(
                    tag, foreground=color, font=("Consolas", 11, "italic")
                )
            else:
                text_widget.tag_configure(tag, foreground=color, font=("Consolas", 11))

        # === TAGS POUR AUTRES LANGAGES VS CODE ===

        # JavaScript tags
        js_tags = {
            "js_keyword": (
                "#569cd6",
                "bold",
            ),  # var, let, const, function, if, else, etc.
            "js_string": ("#ce9178", "normal"),  # Chaînes de caractères
            "js_comment": ("#6a9955", "italic"),  # Commentaires
            "js_number": ("#b5cea8", "normal"),  # Nombres
            "js_function": ("#dcdcaa", "normal"),  # Noms de fonctions
            "js_operator": ("#d4d4d4", "normal"),  # Opérateurs
            "js_punctuation": ("#d4d4d4", "normal"),  # Ponctuation
            "js_variable": ("#9cdcfe", "normal"),  # Variables
            "js_property": ("#9cdcfe", "normal"),  # Propriétés d'objets
        }

        # CSS tags
        css_tags = {
            "css_selector": ("#d7ba7d", "normal"),  # Sélecteurs CSS
            "css_property": ("#9cdcfe", "normal"),  # Propriétés CSS
            "css_value": ("#ce9178", "normal"),  # Valeurs
            "css_comment": ("#6a9955", "italic"),  # Commentaires
            "css_number": ("#b5cea8", "normal"),  # Nombres/unités
            "css_string": ("#ce9178", "normal"),  # Chaînes
            "css_punctuation": ("#d4d4d4", "normal"),  # Ponctuation
            "css_pseudo": ("#dcdcaa", "normal"),  # Pseudo-classes/éléments
            "css_unit": ("#b5cea8", "normal"),  # Unités (px, em, etc.)
        }

        # HTML tags
        html_tags = {
            "html_tag": ("#569cd6", "bold"),  # Balises HTML
            "html_attribute": ("#9cdcfe", "normal"),  # Attributs
            "html_value": ("#ce9178", "normal"),  # Valeurs d'attributs
            "html_comment": ("#6a9955", "italic"),  # Commentaires
            "html_text": ("#d4d4d4", "normal"),  # Texte contenu
            "html_punctuation": ("#d4d4d4", "normal"),  # < > = " /
            "Token.Name.Tag": ("#569cd6", "bold"),  # Balises HTML
            "Token.Name.Entity": ("#dcdcaa", "normal"),  # Entités HTML
        }

        # Bash/Shell tags
        bash_tags = {
            "bash_keyword": ("#569cd6", "bold"),  # if, then, else, fi, for, while, etc.
            "bash_command": ("#dcdcaa", "normal"),  # Commandes
            "bash_string": ("#ce9178", "normal"),  # Chaînes
            "bash_comment": ("#6a9955", "italic"),  # Commentaires
            "bash_variable": ("#9cdcfe", "normal"),  # Variables $VAR
            "bash_operator": ("#d4d4d4", "normal"),  # Opérateurs
            "bash_number": ("#b5cea8", "normal"),  # Nombres
            "bash_punctuation": ("#d4d4d4", "normal"),  # Ponctuation
            "Token.Name.Variable": ("#9cdcfe", "normal"),  # Variables
        }

        # SQL tags
        sql_tags = {
            "sql_keyword": ("#569cd6", "bold"),  # SELECT, FROM, WHERE, etc.
            "sql_function": ("#dcdcaa", "normal"),  # COUNT, SUM, etc.
            "sql_string": ("#ce9178", "normal"),  # Chaînes
            "sql_comment": ("#6a9955", "italic"),  # Commentaires
            "sql_number": ("#b5cea8", "normal"),  # Nombres
            "sql_operator": ("#d4d4d4", "normal"),  # =, >, <, etc.
            "sql_punctuation": ("#d4d4d4", "normal"),  # Ponctuation
            "sql_identifier": ("#9cdcfe", "normal"),  # Noms de tables/colonnes
        }

        # Dockerfile tags
        dockerfile_tags = {
            "dockerfile_instruction": ("#569cd6", "bold"),  # FROM, RUN, COPY, etc.
            "dockerfile_string": ("#ce9178", "normal"),  # Chaînes
            "dockerfile_comment": ("#6a9955", "italic"),  # Commentaires
            "dockerfile_variable": ("#9cdcfe", "normal"),  # Variables ${}
            "dockerfile_path": ("#ce9178", "normal"),  # Chemins de fichiers
            "dockerfile_flag": ("#dcdcaa", "normal"),  # Flags --from, etc.
        }

        # Java tags
        java_tags = {
            "java_keyword": ("#569cd6", "bold"),
            "java_string": ("#ce9178", "normal"),
            "java_comment": ("#6a9955", "italic"),
            "java_number": ("#b5cea8", "normal"),
            "java_class": ("#4ec9b0", "normal"),
            "java_method": ("#dcdcaa", "normal"),
            "java_annotation": ("#dcdcaa", "normal"),
        }

        # C++ tags
        cpp_tags = {
            "cpp_keyword": ("#569cd6", "bold"),
            "cpp_string": ("#ce9178", "normal"),
            "cpp_comment": ("#6a9955", "italic"),
            "cpp_number": ("#b5cea8", "normal"),
            "cpp_preprocessor": ("#c586c0", "normal"),
            "cpp_type": ("#4ec9b0", "normal"),
            "cpp_function": ("#dcdcaa", "normal"),
        }

        # C tags (mêmes couleurs que C++)
        c_tags = {
            "c_keyword": ("#569cd6", "bold"),
            "c_string": ("#ce9178", "normal"),
            "c_comment": ("#6a9955", "italic"),
            "c_number": ("#b5cea8", "normal"),
            "c_preprocessor": ("#c586c0", "normal"),
            "c_type": ("#4ec9b0", "normal"),
            "c_function": ("#dcdcaa", "normal"),
        }

        # C# tags
        csharp_tags = {
            "csharp_keyword": ("#569cd6", "bold"),
            "csharp_string": ("#ce9178", "normal"),
            "csharp_comment": ("#6a9955", "italic"),
            "csharp_number": ("#b5cea8", "normal"),
            "csharp_class": ("#4ec9b0", "normal"),
            "csharp_method": ("#dcdcaa", "normal"),
        }

        # Go tags
        go_tags = {
            "go_keyword": ("#569cd6", "bold"),
            "go_string": ("#ce9178", "normal"),
            "go_comment": ("#6a9955", "italic"),
            "go_number": ("#b5cea8", "normal"),
            "go_type": ("#4ec9b0", "normal"),
            "go_function": ("#dcdcaa", "normal"),
            "go_package": ("#c586c0", "normal"),
        }

        # Ruby tags
        ruby_tags = {
            "ruby_keyword": ("#569cd6", "bold"),
            "ruby_string": ("#ce9178", "normal"),
            "ruby_comment": ("#6a9955", "italic"),
            "ruby_number": ("#b5cea8", "normal"),
            "ruby_symbol": ("#d7ba7d", "normal"),
            "ruby_method": ("#dcdcaa", "normal"),
            "ruby_class": ("#4ec9b0", "normal"),
            "ruby_variable": ("#9cdcfe", "normal"),
        }

        # Swift tags
        swift_tags = {
            "swift_keyword": ("#569cd6", "bold"),
            "swift_string": ("#ce9178", "normal"),
            "swift_comment": ("#6a9955", "italic"),
            "swift_number": ("#b5cea8", "normal"),
            "swift_type": ("#4ec9b0", "normal"),
            "swift_function": ("#dcdcaa", "normal"),
            "swift_attribute": ("#dcdcaa", "normal"),
        }

        # PHP tags
        php_tags = {
            "php_keyword": ("#569cd6", "bold"),
            "php_string": ("#ce9178", "normal"),
            "php_comment": ("#6a9955", "italic"),
            "php_number": ("#b5cea8", "normal"),
            "php_variable": ("#9cdcfe", "normal"),
            "php_function": ("#dcdcaa", "normal"),
            "php_tag": ("#569cd6", "bold"),
        }

        # Perl tags
        perl_tags = {
            "perl_keyword": ("#569cd6", "bold"),
            "perl_string": ("#ce9178", "normal"),
            "perl_comment": ("#6a9955", "italic"),
            "perl_number": ("#b5cea8", "normal"),
            "perl_variable": ("#9cdcfe", "normal"),
            "perl_regex": ("#d16969", "normal"),
        }

        # Rust tags
        rust_tags = {
            "rust_keyword": ("#569cd6", "bold"),
            "rust_string": ("#ce9178", "normal"),
            "rust_comment": ("#6a9955", "italic"),
            "rust_number": ("#b5cea8", "normal"),
            "rust_type": ("#4ec9b0", "normal"),
            "rust_function": ("#dcdcaa", "normal"),
            "rust_macro": ("#c586c0", "normal"),
            "rust_lifetime": ("#569cd6", "italic"),
        }

        # Configuration de tous les tags
        all_language_tags = {
            **js_tags,
            **css_tags,
            **html_tags,
            **bash_tags,
            **sql_tags,
            **dockerfile_tags,
            **java_tags,
            **cpp_tags,
            **c_tags,
            **csharp_tags,
            **go_tags,
            **ruby_tags,
            **swift_tags,
            **php_tags,
            **perl_tags,
            **rust_tags,
        }

        for tag, (color, weight) in all_language_tags.items():
            if weight == "bold":
                text_widget.tag_configure(
                    tag, foreground=color, font=("Consolas", 11, "bold")
                )
            elif weight == "italic":
                text_widget.tag_configure(
                    tag, foreground=color, font=("Consolas", 11, "italic")
                )
            else:
                text_widget.tag_configure(tag, foreground=color, font=("Consolas", 11))

        text_widget.tag_configure(
            "code_block",
            font=("Consolas", 11),
            foreground="#d4d4d4",
        )

        # Tags pour les tableaux Markdown
        text_widget.tag_configure(
            "table_header",
            font=("Segoe UI", 11, "bold"),
            foreground="#58a6ff",
            background="#1a1a2e",
        )
        text_widget.tag_configure(
            "table_cell",
            font=("Segoe UI", 11),
            foreground="#e6e6e6",
            background="#16213e",
        )
        text_widget.tag_configure(
            "table_border",
            font=("Consolas", 11),
            foreground="#444466",
        )
        text_widget.tag_configure(
            "table_cell_bold",
            font=("Segoe UI", 11, "bold"),
            foreground="#ffd700",
            background="#16213e",
        )

    def _process_links_preserve_formatting(self, text, text_widget):
        """Traite les liens tout en préservant le formatage du reste du texte"""
        # Configuration des liens
        text_widget.tag_configure(
            "link", foreground="#3b82f6", underline=True, font=("Segoe UI", 12)
        )

        # Pattern pour liens Markdown : [texte](url)
        markdown_link_pattern = r"\[([^\]]+)\]\(([^)]+)\)"
        # Pattern pour liens HTTP directs
        http_link_pattern = r"(https?://[^\s\)]+)"

        # Combinaison des patterns
        combined_pattern = (
            f"(?P<markdown>{markdown_link_pattern})|(?P<direct>{http_link_pattern})"
        )

        processed_text = text
        link_count = 0

        # Remplacer les liens par des marqueurs temporaires pour éviter les conflits
        link_replacements = {}

        for match in re.finditer(combined_pattern, text):
            if match.group("markdown"):
                # Lien Markdown [texte](url)
                markdown_match = re.match(
                    markdown_link_pattern, match.group("markdown")
                )
                if markdown_match:
                    link_text = markdown_match.group(1)
                    url = markdown_match.group(2)

                    if url and url.strip() and url != "None":
                        # Créer un marqueur unique
                        marker = f"__LINK_MARKER_{link_count}__"
                        link_replacements[marker] = {
                            "text": link_text,
                            "url": url,
                            "original": match.group(0),
                        }

                        # Remplacer dans le texte
                        processed_text = processed_text.replace(
                            match.group(0), marker, 1
                        )
                        link_count += 1

            elif match.group("direct"):
                # Lien direct HTTP
                url = match.group("direct")
                link_text = url if len(url) <= 50 else url[:47] + "..."

                if url and url.strip():
                    marker = f"__LINK_MARKER_{link_count}__"
                    link_replacements[marker] = {
                        "text": link_text,
                        "url": url,
                        "original": match.group(0),
                    }

                    processed_text = processed_text.replace(match.group(0), marker, 1)
                    link_count += 1

        # Programmer l'insertion des liens après que le texte soit inséré
        def insert_links_after():
            try:
                current_content = text_widget.get("1.0", "end-1c")

                for marker, link_info in link_replacements.items():
                    if marker in current_content:
                        # Trouver la position du marqueur
                        start_pos = current_content.find(marker)
                        if start_pos != -1:
                            # Calculer les positions tkinter
                            lines_before = current_content[:start_pos].count("\n")
                            chars_in_line = len(
                                current_content[:start_pos].split("\n")[-1]
                            )

                            start_index = f"{lines_before + 1}.{chars_in_line}"
                            end_index = (
                                f"{lines_before + 1}.{chars_in_line + len(marker)}"
                            )

                            # Remplacer le marqueur par le texte du lien
                            text_widget.delete(start_index, end_index)
                            text_widget.insert(start_index, link_info["text"])

                            # Calculer la nouvelle position de fin
                            end_index = f"{lines_before + 1}.{chars_in_line + len(link_info['text'])}"

                            # Créer un tag unique pour ce lien
                            tag_name = f"link_{link_count}_{start_pos}"
                            text_widget.tag_add(tag_name, start_index, end_index)

                            # Callback pour ouvrir le lien
                            def create_callback(target_url):
                                def on_click(_event):
                                    try:
                                        webbrowser.open(str(target_url).strip())
                                        print(f"[DEBUG] ✅ Lien ouvert: {target_url}")
                                    except Exception as e:
                                        print(f"[DEBUG] ❌ Erreur ouverture lien: {e}")
                                    return "break"

                                return on_click

                            # Bind des événements
                            callback = create_callback(link_info["url"])
                            text_widget.tag_bind(tag_name, "<Button-1>", callback)
                            text_widget.tag_bind(
                                tag_name,
                                "<Enter>",
                                lambda e: text_widget.configure(cursor="hand2"),
                            )
                            text_widget.tag_bind(
                                tag_name,
                                "<Leave>",
                                lambda e: text_widget.configure(cursor="xterm"),
                            )

                            # Assurer la priorité du tag
                            text_widget.tag_raise(tag_name)

                            # Mettre à jour le contenu pour les prochaines recherches
                            current_content = text_widget.get("1.0", "end-1c")

            except Exception as e:
                print(f"[DEBUG] Erreur insertion liens: {e}")

        # Programmer l'insertion des liens après un délai
        text_widget.after(50, insert_links_after)

        return processed_text

    def _insert_python_code_block_corrected(self, text_widget, code):
        """Version CORRIGÉE de l'insertion de code Python avec Pygments"""
        try:
            code = code.strip("\n")
            lexer = PythonLexer()

            for token_type, value in lex(code, lexer):
                # Utiliser le nom complet du token pour un mapping précis
                tag_name = str(token_type)
                text_widget.insert("end", value, (tag_name,))

            text_widget.insert("end", "\n", ("mono",))

        except Exception as e:
            print(f"Erreur Pygments : {e}")
            # Fallback avec regex amélioré
            self._insert_python_code_fallback(text_widget, code)

    def _insert_python_code_fallback(self, text_widget, code):
        """Fallback amélioré pour la coloration syntaxique"""
        code = code.strip("\n")
        lines = code.split("\n")

        for line in lines:
            # Pattern plus précis pour tokeniser
            pattern = r'(#.*$|"""[\s\S]*?"""|\'\'\'[\s\S]*?\'\'\'|"[^"]*"|\'[^\']*\'|\b\d+\.?\d*\b|\b\w+\b|[^\w\s]|\s+)'
            tokens = re.findall(pattern, line)

            for token in tokens:
                if not token:
                    continue
                elif token.startswith("#"):
                    text_widget.insert("end", token, ("Token.Comment",))
                elif token.startswith(('"""', "'''")):
                    text_widget.insert("end", token, ("Token.String",))
                elif token.startswith(('"', "'")):
                    text_widget.insert("end", token, ("Token.String",))
                elif token in keyword.kwlist:
                    text_widget.insert("end", token, ("Token.Keyword",))
                elif token in ["True", "False", "None"]:
                    text_widget.insert("end", token, ("Token.Keyword.Constant",))
                elif token in [
                    "print",
                    "len",
                    "str",
                    "int",
                    "float",
                    "list",
                    "dict",
                    "set",
                    "tuple",
                    "range",
                    "enumerate",
                    "zip",
                    "append",
                    "insert",
                    "remove",
                ]:
                    text_widget.insert("end", token, ("Token.Name.Builtin",))
                elif re.match(r"^\d+\.?\d*$", token):
                    text_widget.insert("end", token, ("Token.Number",))
                elif token in [
                    "=",
                    "+",
                    "-",
                    "*",
                    "/",
                    "//",
                    "%",
                    "**",
                    "==",
                    "!=",
                    "<",
                    ">",
                    "<=",
                    ">=",
                ]:
                    text_widget.insert("end", token, ("Token.Operator",))
                elif token.isspace():
                    text_widget.insert("end", token, ("mono",))
                else:
                    text_widget.insert("end", token, ("Token.Name",))

            text_widget.insert("end", "\n", ("mono",))

    def _insert_python_code_block(self, text_widget, code):
        """Insère un bloc de code python avec coloration syntaxique simple"""
        # Utilise Pygments pour une coloration réaliste
        try:
            code = code.strip("\n")
            for token, value in lex(code, PythonLexer()):
                tag = str(token)
                text_widget.insert("end", value, (tag,))
            text_widget.insert("end", "\n", ("mono",))
        except Exception:
            # Fallback simple
            code = code.strip("\n")
            lines = code.split("\n")
            for line in enumerate(lines):
                tokens = re.split(r'(\s+|#.*|"[^"]*"|\'[^"]*\'|\b\w+\b)', line)
                for token in tokens:
                    if not token:
                        continue
                    if token.startswith("#"):
                        text_widget.insert("end", token, ("py_comment",))
                    elif token.startswith('"') or token.startswith("'"):
                        text_widget.insert("end", token, ("py_string",))
                    elif token in keyword.kwlist:
                        text_widget.insert("end", token, ("py_keyword",))
                    elif token in dir(__builtins__):
                        text_widget.insert("end", token, ("py_builtin",))
                    else:
                        text_widget.insert("end", token, ("mono",))
                text_widget.insert("end", "\n", ("mono",))

    def adjust_text_height_no_scroll(self, text_widget, text):
        """Ajuste la hauteur EXACTE pour afficher tout le contenu sans scroll"""
        try:
            # Attendre que le widget soit rendu
            text_widget.update_idletasks()

            if self.use_ctk:
                # Pour CustomTkinter CTkTextbox - CALCUL TRÈS PRÉCIS
                lines = text.split("\n")
                total_lines = 0

                # Obtenir la largeur réelle du widget
                try:
                    widget_width = text_widget.winfo_width()
                    if widget_width <= 50:
                        widget_width = 400  # Largeur par défaut

                    # Estimation caractères par ligne TRÈS précise
                    font_size = self.get_current_font_size("message")
                    char_width = font_size * 0.6  # Approximation largeur caractère
                    chars_per_line = max(30, int((widget_width - 30) / char_width))

                    for line in lines:
                        if len(line) == 0:
                            total_lines += 1
                        else:
                            # Calculer lignes wrapped précisément
                            line_wrapped = max(
                                1, (len(line) + chars_per_line - 1) // chars_per_line
                            )
                            total_lines += line_wrapped

                except Exception:
                    # Fallback conservateur
                    total_lines = len(lines) + 3  # Plus conservateur

                # Calculer hauteur COMPACTE en pixels
                line_height = 18  # Hauteur d'une ligne (plus compact)
                padding = 8  # Padding minimal (plus compact)
                min_height = 30  # Minimum absolu (plus compact)
                max_height = 600  # Maximum raisonnable (plus grand)

                exact_height = max(
                    min_height, min(total_lines * line_height + padding, max_height)
                )

                # MARGE DE SÉCURITÉ pour éviter tout scroll
                exact_height = int(exact_height * 1.1)  # 10% de marge (réduit)
                text_widget.configure(height=exact_height)

            else:
                # Pour tkinter standard Text - CALCUL EN LIGNES
                current_state = text_widget.cget("state")
                text_widget.configure(state="normal")

                # Forcer le rendu puis mesurer SANS déplacer la vue
                text_widget.update_idletasks()

                # Compter lignes réelles affichées
                line_count = int(text_widget.index("end-1c").split(".")[0])

                # Restaurer l'état
                text_widget.configure(state=current_state)

                # Hauteur GÉNÉREUSE - plus de marge pour éviter scroll
                exact_height = max(
                    2, min(line_count + 3, 30)
                )  # +3 de marge au lieu de 0
                text_widget.configure(height=exact_height)

            # Forcer la mise à jour
            text_widget.update_idletasks()

        except Exception as e:
            self.logger.error("Erreur ajustement hauteur: %s", e)
            # Hauteur par défaut GÉNÉREUSE si erreur
            if self.use_ctk:
                text_widget.configure(height=80)  # Plus généreux
            else:
                text_widget.configure(height=5)  # Plus généreux

    def get_current_font_size(self, font_type="message"):
        """NOUVELLE VERSION - Taille de police unifiée pour tous les messages"""
        # Cette fonction retourne la taille de police pour chaque type
        # UNIFICATION TOTALE : tous les contenus de messages utilisent la même taille
        message_types = ["message", "body", "chat", "bold", "small", "content"]
        if font_type in message_types:
            return 12  # TAILLE UNIFIÉE POUR TOUS LES MESSAGES (réduite de 1)

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

        # Ne réactive l'input que si aucune animation IA n'est en cours
        if hasattr(self, "is_animation_running") and self.is_animation_running():
            return
        self.set_input_state(True)

        if hasattr(self, "thinking_frame"):
            self.thinking_frame.grid_remove()

        # Cache aussi le texte en bas
        if hasattr(self, "status_label"):
            self.status_label.configure(text="")

    def show_thinking_animation(self):
        """Affiche l'animation de réflexion et désactive la saisie"""
        self.is_thinking = True
        # NOUVEAU : Désactiver la zone de saisie
        self.set_input_state(False)

        if hasattr(self, "thinking_frame"):
            self.thinking_frame.grid(
                row=1, column=0, sticky="ew", padx=20, pady=(0, 10)
            )
            self.animate_thinking()

    def show_search_animation(self):
        """Affiche l'animation de recherche et désactive la saisie"""
        self.is_searching = True
        # NOUVEAU : Désactiver la zone de saisie
        self.set_input_state(False)

        if hasattr(self, "thinking_frame"):
            self.thinking_frame.grid(
                row=1, column=0, sticky="ew", padx=20, pady=(0, 10)
            )
            self.animate_search()

    def adjust_text_height(self, text_widget, text):
        """Ajuste la hauteur du widget de texte selon le contenu"""
        try:
            if self.use_ctk:
                # Pour CustomTkinter CTkTextbox, mesure plus précise
                text_widget.update_idletasks()  # Forcer la mise à jour

                # Pour CustomTkinter, on ne peut pas changer l'état facilement
                # On va calculer la hauteur autrement
                lines = text.split("\n")
                total_lines = len(lines)

                # Estimer les lignes avec retour automatique
                widget_width = 600  # Largeur approximative
                chars_per_line = widget_width // 8  # Approximation

                for line in lines:
                    if len(line) > chars_per_line:
                        additional_lines = (len(line) - 1) // chars_per_line
                        total_lines += additional_lines

                # Calculer la hauteur nécessaire (ligne_height * nb_lignes + padding)
                line_height = 18  # Hauteur d'une ligne en pixels
                padding = 15  # Padding total
                min_height = 40  # Hauteur minimale
                # ⚡ CORRECTION: Pas de limite maximale pour afficher tout le contenu

                calculated_height = max(min_height, total_lines * line_height + padding)
                text_widget.configure(height=calculated_height)

            else:
                # Pour tkinter standard Text
                text_widget.update_idletasks()

                # Mesurer le contenu réel
                current_state = text_widget.cget("state")
                text_widget.configure(state="normal")
                text_widget.delete("1.0", "end")
                text_widget.insert("1.0", text)
                text_widget.update_idletasks()

                # Obtenir le nombre de lignes
                line_count = int(text_widget.index("end-1c").split(".")[0])

                # Restaurer l'état
                text_widget.configure(state=current_state)

                # Ajuster en nombre de lignes (plus précis pour tkinter)
                height = max(
                    2, min(line_count + 1, 25)
                )  # +1 pour la marge, max 25 lignes
                text_widget.configure(height=height)

        except Exception as e:
            self.logger.error("Erreur lors de l'ajustement de la hauteur: %s", e)
            # Hauteur par défaut en cas d'erreur
            if self.use_ctk:
                text_widget.configure(height=100)
            else:
                text_widget.configure(height=5)

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
                except Exception as e:
                    print(f"❌ Erreur lors de l'envoi du message: {e}")
                    return "break"
        except Exception as e:
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
        except Exception as e:
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

        if self.use_ctk:
            # CustomTkinter avec placeholder natif si disponible
            try:
                # Essayer d'utiliser le placeholder natif de CustomTkinter
                if (
                    hasattr(self.input_text, "configure")
                    and "placeholder_text" in self.input_text.configure()
                ):
                    self.input_text.configure(placeholder_text=self.placeholder_text)
                    self.placeholder_active = False
                    return
            except Exception:
                pass

            # Fallback pour CustomTkinter
            self._show_placeholder()

            def on_focus_in(_event):
                self._hide_placeholder()

            def on_focus_out(_event):
                if not self.input_text.get("1.0", "end-1c").strip():
                    self._show_placeholder()

            def on_key_press(_event):
                if self.placeholder_active:
                    self._hide_placeholder()

            self.input_text.bind("<FocusIn>", on_focus_in)
            self.input_text.bind("<FocusOut>", on_focus_out)
            self.input_text.bind("<KeyPress>", on_key_press)
        else:
            # Pour tkinter standard
            self._show_placeholder()

            def on_focus_in(_event):
                self._hide_placeholder()

            def on_focus_out(_event):
                if not self.input_text.get("1.0", "end-1c").strip():
                    self._show_placeholder()

            def on_key_press(_event):
                if self.placeholder_active:
                    self._hide_placeholder()

            self.input_text.bind("<FocusIn>", on_focus_in)
            self.input_text.bind("<FocusOut>", on_focus_out)
            self.input_text.bind("<KeyPress>", on_key_press)

    def _show_placeholder(self):
        """Affiche le placeholder de manière non éditable"""
        if not self.placeholder_active:
            self.input_text.delete("1.0", "end")
            self.input_text.insert("1.0", self.placeholder_text)

            if self.use_ctk:
                self.input_text.configure(text_color=self.colors["placeholder"])
            else:
                self.input_text.configure(fg=self.colors["placeholder"])

            # Rendre le texte non sélectionnable et transparent visuellement
            self.input_text.configure(state="disabled")
            self.input_text.configure(state="normal")
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

    def start_animations(self):
        """Démarre les animations de l'interface"""
        self.animate_thinking()
        self.animate_search()

    def animate_thinking(self):
        """Animation de réflexion de l'IA"""
        if hasattr(self, "thinking_label") and self.is_thinking:
            # Animations avancées qui montrent l'intelligence de l'IA
            advanced_animations = [
                "⚡ Traitement neural en cours.",
                "💡 Génération de réponse intelligente.",
                "🎯 Optimisation de la réponse.",
                "⚙️ Moteur de raisonnement actif.",
                "📊 Analyse des patterns.",
                "💻 Processing linguistique avancé.",
                "🎪 Préparation d'une réponse.",
            ]

            # Choisir une animation aléatoire pour plus de variété
            if (
                not hasattr(self, "current_thinking_text")
                or self.thinking_dots % 4 == 0
            ):
                self.current_thinking_text = random.choice(advanced_animations)

            # Animation de points progressifs
            dots = ["", ".", "..", "..."][self.thinking_dots % 4]
            display_text = self.current_thinking_text + dots

            self.thinking_dots = (self.thinking_dots + 1) % 4
            self.thinking_label.configure(text=display_text)

            # Animation plus rapide pour donner l'impression de vitesse
            self.root.after(400, self.animate_thinking)
        elif hasattr(self, "thinking_label"):
            self.thinking_label.configure(text="")

    def animate_search(self):
        """Animation de recherche internet"""
        if hasattr(self, "thinking_label") and self.is_searching:
            # Animations de recherche variées
            animations = [
                "🔍 Recherche sur internet",
                "🌐 Recherche sur internet",
                "📡 Recherche sur internet",
                "🔎 Recherche sur internet",
                "💫 Recherche sur internet",
                "⚡ Recherche sur internet",
            ]

            self.search_frame = (self.search_frame + 1) % len(animations)
            self.thinking_label.configure(text=animations[self.search_frame])

            # Continuer l'animation toutes les 800ms
            self.root.after(800, self.animate_search)
        elif hasattr(self, "thinking_label"):
            self.thinking_label.configure(text="")

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
            except Exception as e:
                print(f"❌ Erreur lecture input: {e}")
                return

            # Vérifier que ce n'est pas le texte du placeholder
            if message == getattr(self, "placeholder_text", "") or not message:
                return

            # S'assurer que la saisie est activée pour pouvoir lire et effacer
            was_disabled = False
            try:
                current_state = self.input_text.cget("state")
                if current_state == "disabled":
                    was_disabled = True
                    self.input_text.configure(state="normal")
            except Exception:
                pass

            # Cacher les indicateurs
            self.hide_status_indicators()

            # Ajouter le message utilisateur
            self.add_message_bubble(message, is_user=True)

            # Effacer la zone de saisie et remettre le placeholder
            try:
                self.input_text.delete("1.0", "end")
                # Remettre le placeholder après effacement
                self._show_placeholder()
            except Exception as e:
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

            # Lancer le traitement avec l'ID
            threading.Thread(
                target=self.quel_handle_message_with_id,
                args=(message, request_id),
                daemon=True,
            ).start()

        except Exception as e:

            # En cas d'erreur, s'assurer que la saisie est réactivée
            try:
                self.set_input_state(True)
            except Exception:
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

                    # Icône IA
                    icon_label = self.create_label(
                        center_frame,
                        text="🤖",
                        font=("Segoe UI", 16),
                        fg_color=self.colors["bg_chat"],
                        text_color=self.colors["accent"],
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

                except Exception as e:
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
                        except Exception as e:
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
                        except Exception as e:
                            print(f"Erreur animation: {e}")

                    # CONTINUER L'ANIMATION EN BOUCLE (sauf si interrompu)
                    if self._file_generation_active and not self.is_interrupted:
                        self.root.after(500, animate_loading_dots)
                except Exception as e:
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
                        interrupted = self.is_interrupted
                        if interrupted:
                            print(
                                f"🛑 [GUI Callback] Interruption détectée! is_interrupted={interrupted}"
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
                                                except Exception as e:
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

                                        except Exception as e:
                                            print(f"Erreur ajout tag: {e}")
                                            traceback.print_exc()

                                    # Démarrer l'animation de frappe
                                    animate_typing(0)

                            except Exception as e:
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

                except Exception as e:
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
        except Exception:
            intent = "unknown"
            confidence = 0.0

        self.last_detected_intent = {"name": intent, "confidence": confidence}

        print(
            f"[DEBUG] (ModernAIGUI) Question transmise - Mode {'CustomAI+Streaming' if self.custom_ai else 'Standard'} : {repr(user_text)}"
        )

        try:
            if self.custom_ai and hasattr(self.custom_ai, "generate_response_stream"):
                # ⚡ MODE STREAMING avec animation de frappe
                print("⚡ [GUI] Activation du mode STREAMING avec animation...")

                # Réinitialiser le buffer de streaming
                self._streaming_buffer = ""
                self._streaming_complete = False
                self._streaming_mode = True
                self._streaming_bubble_created = False

                def on_token_received(token):
                    """Callback appelé pour chaque token reçu d'Ollama"""
                    if self.current_request_id != request_id or self.is_interrupted:
                        return False

                    # Ajouter au buffer
                    self._streaming_buffer += token

                    # Premier token : créer la bulle et démarrer l'animation
                    if not self._streaming_bubble_created:
                        self._streaming_bubble_created = True
                        self.root.after(0, self._create_streaming_bubble_with_animation)

                    return True

                # Lancer la génération streaming (bloquant dans ce thread)
                response = self.custom_ai.generate_response_stream(
                    user_text, on_token=on_token_received
                )

                # Marquer le streaming comme terminé
                self._streaming_complete = True
                print(
                    f"✅ [STREAM] Streaming terminé: {len(self._streaming_buffer)} caractères"
                )

            else:
                # Mode classique (fallback)
                print("🔄 [GUI] Mode classique (sans streaming)...")
                if self.custom_ai:
                    response = self.custom_ai.generate_response(user_text)
                else:
                    response = self.ai_engine.process_text(user_text)

                if self.current_request_id == request_id and not self.is_interrupted:
                    self.root.after(0, lambda: self.add_ai_response(response))

        except Exception as e:
            print(f"❌ [GUI] Erreur: {e}")
            response = f"❌ Erreur IA : {e}"
            if self.current_request_id == request_id:
                self.root.after(0, lambda: self.add_ai_response(response))

        self.root.after(0, self.hide_status_indicators)

    def _create_streaming_bubble_with_animation(self):
        """
        Crée la bulle IA et démarre l'animation de frappe en mode streaming.
        L'animation lit depuis le buffer qui se remplit en temps réel.
        """
        try:
            # Cacher l'animation de réflexion immédiatement
            self.is_thinking = False
            if hasattr(self, "thinking_frame"):
                self.thinking_frame.grid_remove()

            # Créer le container principal
            msg_container = self.create_frame(
                self.chat_frame, fg_color=self.colors["bg_chat"]
            )

            # Ajouter un placeholder dans l'historique
            self.conversation_history.append(
                {
                    "text": "",  # Sera mis à jour à la fin
                    "is_user": False,
                    "timestamp": datetime.now(),
                    "type": "streaming",
                }
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

            # Icône IA
            icon_label = self.create_label(
                center_frame,
                text="🤖",
                font=("Segoe UI", 16),
                fg_color=self.colors["bg_chat"],
                text_color=self.colors["accent"],
            )
            icon_label.grid(row=0, column=0, sticky="nw", padx=(0, 10), pady=(1, 0))

            # Container pour le message
            message_container = self.create_frame(
                center_frame, fg_color=self.colors["bg_chat"]
            )
            message_container.grid(row=0, column=1, sticky="ew", padx=0, pady=(2, 2))
            message_container.grid_columnconfigure(0, weight=1)

            self._streaming_container = message_container
            self.current_message_container = message_container

            # Widget texte pour le streaming
            text_widget = tk.Text(
                message_container,
                width=120,
                height=1,
                bg=self.colors["bg_chat"],
                fg=self.colors["text_primary"],
                font=("Segoe UI", 12),
                wrap=tk.WORD,
                relief="flat",
                bd=0,
                highlightthickness=0,
                state="normal",
                cursor="xterm",
                padx=8,
                pady=6,
                selectbackground="#4a90e2",
                selectforeground="#ffffff",
            )
            text_widget.grid(row=0, column=0, sticky="ew")

            self._streaming_widget = text_widget

            # Configurer le scroll forwarding
            self.setup_improved_scroll_forwarding(text_widget)

            # Démarrer l'animation de frappe en mode streaming
            self._start_streaming_typing_animation(text_widget)

            # Scroll vers le bas
            self.scroll_to_bottom()

        except Exception as e:
            print(f"❌ [STREAM] Erreur création bulle: {e}")
            traceback.print_exc()

    def _start_streaming_typing_animation(self, text_widget):
        """
        Démarre l'animation de frappe en MODE STREAMING.
        Similaire à start_typing_animation_dynamic mais lit depuis le buffer en temps réel.
        """
        # DÉSACTIVER la saisie pendant l'animation
        self.set_input_state(False)

        # Réinitialiser le widget
        text_widget.configure(state="normal")
        text_widget.delete("1.0", "end")

        # DÉSACTIVER le scroll pendant l'animation
        self._disable_text_scroll(text_widget)

        # Variables pour l'animation streaming
        self.typing_index = 0
        self.typing_widget = text_widget
        self.typing_speed = 1
        self._typing_interrupted = False

        # IMPORTANT: typing_text est utilisé par _apply_unified_progressive_formatting
        # On le synchronise avec le buffer de streaming
        self.typing_text = self._streaming_buffer

        # Initialiser le code_blocks_map vide (sera mis à jour périodiquement)
        self._code_blocks_map = {}

        # Tracker pour éviter de recoloriser le même bloc plusieurs fois
        self._last_colored_block_end = -1

        # Réinitialiser les positions formatées
        self._formatted_positions = set()
        self._formatted_bold_contents = set()
        self._formatted_tables = set()
        self._pending_links = []
        self._table_blocks = []
        # pylint: disable=attribute-defined-outside-init
        self._table_blocks_history = (
            {}
        )  # Pour tracker l'évolution des tableaux (attribut temporaire de streaming)

        # Configurer tous les tags de formatage
        self._configure_all_formatting_tags(text_widget)

        # Configuration du tag 'normal'
        text_widget.tag_configure(
            "normal", font=("Segoe UI", 12), foreground=self.colors["text_primary"]
        )

        # Démarrer l'animation en mode streaming
        self._continue_streaming_typing_animation()

    def _continue_streaming_typing_animation(self):
        """
        Continue l'animation de frappe en mode streaming.
        Attend si l'animation rattrape le buffer, continue quand de nouveaux tokens arrivent.
        AMÉLIORATION: Détecte la fermeture des blocs de code et applique la coloration immédiatement.
        """
        if not hasattr(self, "typing_widget") or self.typing_widget is None:
            return

        if getattr(self, "_typing_interrupted", False):
            self._finish_streaming_animation(_interrupted=True)
            return

        try:
            buffer_length = len(self._streaming_buffer)

            # IMPORTANT: Synchroniser typing_text avec le buffer pour le formatage
            self.typing_text = self._streaming_buffer

            # Vérifier si on a des caractères à afficher
            if self.typing_index < buffer_length:
                # Il y a du contenu à afficher
                char = self._streaming_buffer[self.typing_index]

                self.typing_widget.configure(state="normal")

                # Déterminer le tag à utiliser (coloration syntaxique)
                tag_to_use = "normal"
                if (
                    hasattr(self, "_code_blocks_map")
                    and self.typing_index in self._code_blocks_map
                ):
                    _language, token_type = self._code_blocks_map[self.typing_index]
                    if token_type == "code_block_marker":
                        tag_to_use = "hidden"
                    else:
                        tag_to_use = token_type

                # Insérer le caractère
                self.typing_widget.insert("end", char, tag_to_use)
                self.typing_index += 1

                # ============================================================
                # 🎨 DÉTECTION FERMETURE BLOC DE CODE - Coloration immédiate
                # ============================================================
                # Détecter quand un bloc de code vient de se fermer (``` suivi de \n ou fin)
                code_block_just_closed = False
                if char == "`":
                    # Vérifier si on vient de fermer un bloc de code (les 3 derniers chars sont ```)
                    current_buffer = self._streaming_buffer[: self.typing_index]
                    if current_buffer.endswith("```"):
                        # Compter les occurrences de ``` pour voir si c'est une fermeture
                        triple_backticks = current_buffer.count("```")
                        if triple_backticks >= 2 and triple_backticks % 2 == 0:
                            # Vérifier qu'on n'a pas déjà traité ce bloc
                            last_block_end = getattr(
                                self, "_last_colored_block_end", -1
                            )
                            if self.typing_index > last_block_end:
                                code_block_just_closed = True
                                self._last_colored_block_end = self.typing_index
                                print(
                                    f"🎨 [STREAM] Bloc de code fermé détecté à position {self.typing_index}"
                                )

                # Si un bloc de code vient de se fermer, appliquer la coloration sur CE bloc uniquement
                if code_block_just_closed:
                    self._apply_streaming_syntax_coloring()

                # Formatage progressif (gras, italique, code inline)
                should_format = False
                if char == "*":
                    current_content = self.typing_widget.get("1.0", "end-1c")
                    if current_content.endswith("**") and len(current_content) >= 4:
                        bold_pattern = r"\*\*([^*\n]{1,200}?)\*\*$"
                        if re.search(bold_pattern, current_content):
                            should_format = True
                elif char == "`":
                    current_content = self.typing_widget.get("1.0", "end-1c")
                    code_pattern = r"`([^`\n]+)`$"
                    if re.search(code_pattern, current_content):
                        should_format = True
                elif char == "\n":
                    should_format = True
                    # Mettre à jour la pré-analyse des tableaux avec le contenu actuel
                    self._table_blocks = self._preanalyze_markdown_tables(
                        self._streaming_buffer[: self.typing_index]
                    )
                    self._check_and_format_table_line(
                        self.typing_widget, self.typing_index
                    )
                elif self.typing_index % 50 == 0:
                    should_format = True

                if should_format:
                    self._apply_unified_progressive_formatting(self.typing_widget)

                # Ajuster la hauteur aux retours à la ligne
                if char == "\n":
                    self.adjust_text_widget_height(self.typing_widget)
                    self.root.after(5, self._smart_scroll_follow_animation)

                self.typing_widget.configure(state="disabled")

                # Continuer rapidement (10ms)
                self.root.after(10, self._continue_streaming_typing_animation)

            elif not self._streaming_complete:
                # Buffer rattrapé mais streaming pas terminé - attendre
                self.root.after(20, self._continue_streaming_typing_animation)

            else:
                # Streaming terminé et tout affiché
                self._finish_streaming_animation()

        except tk.TclError:
            self._finish_streaming_animation(_interrupted=True)
        except Exception as e:
            print(f"⚠️ [STREAM ANIM] Erreur: {e}")
            self._finish_streaming_animation(_interrupted=True)

    def _apply_streaming_syntax_coloring(self):
        """
        Applique la coloration syntaxique sur le PREMIER bloc de code non encore traité.
        MÉTHODE: Chercher directement dans le widget (pas dans le buffer).
        """
        try:
            self.typing_widget.configure(state="normal")
            widget_text = self.typing_widget.get("1.0", "end-1c")

            # Chercher le PREMIER bloc de code avec balises encore présentes dans le widget
            # Pattern: ```langage\n...code...```
            # CORRECTION: Capturer aussi les + pour c++, et # pour c#
            code_block_pattern = r"```([\w+#-]+)\n(.*?)```"
            widget_match = re.search(code_block_pattern, widget_text, re.DOTALL)

            if not widget_match:
                self.typing_widget.configure(state="disabled")
                return

            # Extraire les informations du bloc
            language = widget_match.group(1).lower()
            code_content = widget_match.group(2)
            w_block_start = widget_match.start()
            w_block_end = widget_match.end()

            print(
                f"🎨 [STREAM] Coloration bloc '{language}' positions {w_block_start}-{w_block_end}"
            )

            # Calculer les positions des balises
            opening_marker = "```" + language + "\n"
            opening_len = len(opening_marker)

            # Analyser le code pour obtenir les tokens
            code_tokens = self._get_code_tokens(language, code_content)

            # ============================================================
            # ÉTAPE 1: Supprimer les balises de fermeture ``` (en premier car ça ne décale pas le début)
            # ============================================================
            closing_start = w_block_start + opening_len + len(code_content)
            tk_close_start = f"1.0 + {closing_start} chars"
            tk_close_end = f"1.0 + {closing_start + 3} chars"
            self.typing_widget.delete(tk_close_start, tk_close_end)

            # ============================================================
            # ÉTAPE 2: Appliquer la coloration sur le code (avant de supprimer l'ouverture)
            # ============================================================
            code_start_in_widget = w_block_start + opening_len

            for rel_pos, token_type in code_tokens.items():
                abs_pos = code_start_in_widget + rel_pos
                if rel_pos < len(code_content):
                    tk_start = f"1.0 + {abs_pos} chars"
                    tk_end = f"1.0 + {abs_pos + 1} chars"
                    self.typing_widget.tag_add(token_type, tk_start, tk_end)

            # ============================================================
            # ÉTAPE 3: Supprimer les balises d'ouverture ```langage\n
            # ============================================================
            tk_open_start = f"1.0 + {w_block_start} chars"
            tk_open_end = f"1.0 + {w_block_start + opening_len} chars"
            self.typing_widget.delete(tk_open_start, tk_open_end)

            self.typing_widget.configure(state="disabled")

            # Mettre à jour l'index d'écriture pour compenser les suppressions
            chars_removed = opening_len + 3  # ```langage\n + ```
            self.typing_index -= chars_removed

            # Mettre à jour le buffer en supprimant les balises de CE bloc
            # Chercher le même bloc dans le buffer
            buffer_match = re.search(
                r"```" + re.escape(language) + r"\n(.*?)```",
                self._streaming_buffer,
                re.DOTALL,
            )
            if buffer_match:
                new_buffer = (
                    self._streaming_buffer[: buffer_match.start()]
                    + buffer_match.group(1)  # Garder juste le code
                    + self._streaming_buffer[buffer_match.end() :]
                )
                self._streaming_buffer = new_buffer
                self.typing_text = self._streaming_buffer

            # ============================================================
            # IMPORTANT: Vider le cache de formatage car les positions ont changé
            # ============================================================
            if hasattr(self, "_formatted_positions"):
                self._formatted_positions.clear()
            if hasattr(self, "_formatted_bold_contents"):
                self._formatted_bold_contents.clear()

        except Exception as e:
            print(f"⚠️ [STREAM] Erreur coloration bloc: {e}")
            traceback.print_exc()

    def _get_code_tokens(self, language: str, code: str) -> dict:
        """
        Analyse le code et retourne un dictionnaire position_relative -> token_type.
        """
        tokens = {}

        # Marquer tout comme code_block par défaut
        for i in range(len(code)):
            tokens[i] = "code_block"

        try:
            if language == "python":
                try:
                    lexer = PythonLexer()
                    pos = 0
                    for token_type, token_value in lex(code, lexer):
                        token_name = str(token_type)
                        for _ in token_value:
                            tokens[pos] = token_name
                            pos += 1
                except Exception:
                    pass
            else:
                # Patterns pour chaque langage
                patterns = self._get_language_patterns(language)
                for pattern, token_type in patterns:
                    for match in re.finditer(
                        pattern, code, re.MULTILINE | re.IGNORECASE
                    ):
                        for i in range(match.start(), match.end()):
                            tokens[i] = token_type
        except Exception:
            pass

        return tokens

    def _get_language_patterns(self, language: str) -> list:
        """Retourne les patterns regex pour un langage donné."""
        patterns_map = {
            "javascript": [
                (r"//.*$", "js_comment"),
                (r"/\*.*?\*/", "js_comment"),
                (r'"[^"]*"', "js_string"),
                (r"'[^']*'", "js_string"),
                (r"`[^`]*`", "js_string"),
                (
                    r"\b(const|let|var|function|return|if|else|for|while|class|import|export|from|async|await)\b",
                    "js_keyword",
                ),
                (r"\b(console|document|window)\b", "js_variable"),
            ],
            "java": [
                (r"//.*$", "java_comment"),
                (r"/\*.*?\*/", "java_comment"),
                (r'"[^"]*"', "java_string"),
                (
                    r"\b(public|private|protected|static|void|class|interface|extends|implements|new|return|if|else|for|while|int|String|boolean|package|import)\b",
                    "java_keyword",
                ),
                (r"\b[A-Z][a-zA-Z0-9]*\b", "java_class"),
            ],
            "c": [
                (r"//.*$", "c_comment"),
                (r"/\*.*?\*/", "c_comment"),
                (r'"[^"]*"', "c_string"),
                (r"#\w+.*$", "c_preprocessor"),
                (
                    r"\b(int|void|char|float|double|return|if|else|for|while|include|using|namespace|std)\b",
                    "c_keyword",
                ),
                (r"\b\d+\b", "c_number"),
            ],
            "cpp": [
                (r"//.*$", "c_comment"),
                (r"/\*.*?\*/", "c_comment"),
                (r'"[^"]*"', "c_string"),
                (r"#\w+.*$", "c_preprocessor"),
                (
                    r"\b(int|void|char|float|double|return|if|else|for|while|include|using|namespace|std|class|public|private)\b",
                    "c_keyword",
                ),
                (r"\b\d+\b", "c_number"),
            ],
            "csharp": [
                (r"//.*$", "csharp_comment"),
                (r"/\*.*?\*/", "csharp_comment"),
                (r'"[^"]*"', "csharp_string"),
                (
                    r"\b(public|private|protected|static|void|class|interface|namespace|using|new|return|if|else|for|while|int|string|bool|var)\b",
                    "csharp_keyword",
                ),
                (r"\b[A-Z][a-zA-Z0-9]*\b", "csharp_class"),
            ],
            "html": [
                (r"<!--.*?-->", "html_comment"),
                (r"<[^>]+>", "html_tag"),
                (r'"[^"]*"', "html_value"),
            ],
            "css": [
                (r"/\*.*?\*/", "css_comment"),
                (r"[.#]?[a-zA-Z_][a-zA-Z0-9_-]*(?=\s*\{)", "css_selector"),
                (r"[a-zA-Z-]+(?=\s*:)", "css_property"),
                (r"\d+(\.\d+)?(px|em|rem|%|vh|vw)", "css_unit"),
                (r"#[a-fA-F0-9]{3,8}", "css_value"),
            ],
            "sql": [
                (r"--.*$", "sql_comment"),
                (r"'[^']*'", "sql_string"),
                (
                    r"\b(SELECT|FROM|WHERE|INSERT|UPDATE|DELETE|CREATE|TABLE|INTO|VALUES|AND|OR|JOIN|ON|AS|ORDER|BY|GROUP|HAVING|LIMIT)\b",
                    "sql_keyword",
                ),
            ],
            "bash": [
                (r"#.*$", "bash_comment"),
                (r'"[^"]*"', "bash_string"),
                (r"'[^']*'", "bash_string"),
                (
                    r"\b(echo|cd|ls|mkdir|rm|cp|mv|cat|grep|sed|awk|if|then|else|fi|for|do|done|while)\b",
                    "bash_command",
                ),
            ],
            "php": [
                (r"//.*$", "php_comment"),
                (r"/\*.*?\*/", "php_comment"),
                (r'"[^"]*"', "php_string"),
                (r"'[^']*'", "php_string"),
                (r"<\?php|\?>", "php_tag"),
                (
                    r"\b(echo|print|function|return|if|else|for|while|class|public|private)\b",
                    "php_keyword",
                ),
            ],
            "ruby": [
                (r"#.*$", "ruby_comment"),
                (r'"[^"]*"', "ruby_string"),
                (r"'[^']*'", "ruby_string"),
                (
                    r"\b(def|end|class|module|if|else|elsif|unless|while|do|puts|print|require)\b",
                    "ruby_keyword",
                ),
                (r"\b(puts|print|gets)\b", "ruby_method"),
            ],
            "swift": [
                (r"//.*$", "swift_comment"),
                (r"/\*.*?\*/", "swift_comment"),
                (r'"[^"]*"', "swift_string"),
                (
                    r"\b(func|var|let|class|struct|import|return|if|else|for|while|print)\b",
                    "swift_keyword",
                ),
            ],
            "go": [
                (r"//.*$", "go_comment"),
                (r"/\*.*?\*/", "go_comment"),
                (r'"[^"]*"', "go_string"),
                (r"`[^`]*`", "go_string"),
                (
                    r"\b(package|import|func|var|const|type|struct|interface|return|if|else|for|range|switch|case|break|continue|defer|go|chan|map|make|new)\b",
                    "go_keyword",
                ),
                (r"\b(fmt|Println|Printf)\b", "go_function"),
                (r"\b[A-Z][a-zA-Z0-9]*\b", "go_type"),
            ],
            "rust": [
                (r"//.*$", "rust_comment"),
                (r"/\*.*?\*/", "rust_comment"),
                (r'"[^"]*"', "rust_string"),
                (
                    r"\b(fn|let|mut|const|use|pub|mod|struct|enum|impl|trait|return|if|else|match|for|while|loop|break|continue)\b",
                    "rust_keyword",
                ),
                (r"\b(println!|print!|vec!|format!)\b", "rust_macro"),
                (r"\b[A-Z][a-zA-Z0-9]*\b", "rust_type"),
                (r"&'[a-z]+\b", "rust_lifetime"),
            ],
            "perl": [
                (r"#.*$", "perl_comment"),
                (r'"[^"]*"', "perl_string"),
                (r"'[^']*'", "perl_string"),
                (
                    r"\b(sub|my|local|our|use|require|if|else|elsif|unless|while|for|foreach|do|return|package)\b",
                    "perl_keyword",
                ),
                (r"[$@%]\w+", "perl_variable"),
                (r"/(\\.|[^\\/])+/[gimsx]*", "perl_regex"),
            ],
            "dockerfile": [
                (r"#.*$", "dockerfile_comment"),
                (
                    r"\b(FROM|RUN|CMD|COPY|ADD|EXPOSE|ENV|WORKDIR|ENTRYPOINT|VOLUME|USER|ARG)\b",
                    "dockerfile_instruction",
                ),
                (r'"[^"]*"', "dockerfile_string"),
            ],
        }

        # Alias
        patterns_map["js"] = patterns_map["javascript"]
        patterns_map["ts"] = patterns_map["javascript"]
        patterns_map["typescript"] = patterns_map["javascript"]
        patterns_map["c++"] = patterns_map["cpp"]
        patterns_map["cs"] = patterns_map["csharp"]
        patterns_map["sh"] = patterns_map["bash"]
        patterns_map["shell"] = patterns_map["bash"]
        patterns_map["rb"] = patterns_map["ruby"]
        patterns_map["docker"] = patterns_map["dockerfile"]
        patterns_map["golang"] = patterns_map["go"]
        patterns_map["rs"] = patterns_map["rust"]
        patterns_map["pl"] = patterns_map["perl"]

        return patterns_map.get(language, [])

    def _analyze_single_code_block(
        self, language: str, code_content: str, block_start: int
    ) -> dict:
        """
        Analyse un seul bloc de code et retourne un dictionnaire position -> (language, token_type).
        """
        tokens_map = {}

        try:
            # Offset pour le contenu du code (après ```langage\n)
            marker_length = 3 + len(language) + 1  # ``` + language + \n
            code_offset = block_start + marker_length

            # Marquer les ``` d'ouverture comme hidden
            for i in range(3):
                tokens_map[block_start + i] = (language, "code_block_marker")
            # Marquer le nom du langage comme hidden aussi
            for i in range(len(language)):
                tokens_map[block_start + 3 + i] = (language, "code_block_marker")
            # Marquer le \n après le langage
            tokens_map[block_start + 3 + len(language)] = (
                language,
                "code_block_marker",
            )

            # Marquer les ``` de fermeture comme hidden
            closing_start = block_start + marker_length + len(code_content)
            for i in range(3):
                tokens_map[closing_start + i] = (language, "code_block_marker")

            # Analyser le code selon le langage
            if language == "python":
                self._analyze_python_tokens_for_block(
                    code_content, code_offset, tokens_map, language
                )
            elif language in ("javascript", "js", "typescript", "ts"):
                self._analyze_js_tokens_for_block(
                    code_content, code_offset, tokens_map, language
                )
            elif language in ("java",):
                self._analyze_java_tokens_for_block(
                    code_content, code_offset, tokens_map, language
                )
            elif language in ("c", "cpp", "c++", "csharp", "cs"):
                self._analyze_c_tokens_for_block(
                    code_content, code_offset, tokens_map, language
                )
            elif language in ("html", "xml"):
                self._analyze_html_tokens_for_block(
                    code_content, code_offset, tokens_map, language
                )
            elif language in ("sql",):
                self._analyze_sql_tokens_for_block(
                    code_content, code_offset, tokens_map, language
                )
            elif language in ("bash", "sh", "shell"):
                self._analyze_bash_tokens_for_block(
                    code_content, code_offset, tokens_map, language
                )
            elif language in ("php",):
                self._analyze_php_tokens_for_block(
                    code_content, code_offset, tokens_map, language
                )
            elif language in ("ruby", "rb"):
                self._analyze_ruby_tokens_for_block(
                    code_content, code_offset, tokens_map, language
                )
            elif language in ("css", "scss", "sass"):
                self._analyze_css_tokens_for_block(
                    code_content, code_offset, tokens_map, language
                )
            elif language in ("dockerfile", "docker"):
                self._analyze_dockerfile_tokens_for_block(
                    code_content, code_offset, tokens_map, language
                )
            else:
                # Langage non reconnu - marquer tout comme code_block
                for i, _ in enumerate(code_content):
                    tokens_map[code_offset + i] = (language, "code_block")

        except Exception as e:
            print(f"⚠️ Erreur analyse bloc {language}: {e}")

        return tokens_map

    def _analyze_python_tokens_for_block(
        self, code: str, offset: int, tokens_map: dict, language: str
    ):
        """Analyse les tokens Python avec Pygments."""
        try:
            lexer = PythonLexer()
            pos = 0
            for token_type, token_value in lex(code, lexer):
                token_name = str(token_type)
                for _ in token_value:
                    tokens_map[offset + pos] = (language, token_name)
                    pos += 1
        except Exception:
            for i, _ in enumerate(code):
                tokens_map[offset + i] = (language, "code_block")

    def _analyze_js_tokens_for_block(
        self, code: str, offset: int, tokens_map: dict, language: str
    ):
        """Analyse les tokens JavaScript."""
        patterns = [
            (r"//.*$", "js_comment"),
            (r"/\*.*?\*/", "js_comment"),
            (r'"[^"]*"', "js_string"),
            (r"'[^']*'", "js_string"),
            (r"`[^`]*`", "js_string"),
            (
                r"\b(const|let|var|function|return|if|else|for|while|class|import|export|from|async|await)\b",
                "js_keyword",
            ),
            (r"\b(console|document|window)\b", "js_variable"),
        ]
        self._apply_patterns_to_block(
            code, offset, tokens_map, language, patterns, "code_block"
        )

    def _analyze_java_tokens_for_block(
        self, code: str, offset: int, tokens_map: dict, language: str
    ):
        """Analyse les tokens Java."""
        patterns = [
            (r"//.*$", "java_comment"),
            (r"/\*.*?\*/", "java_comment"),
            (r'"[^"]*"', "java_string"),
            (
                r"\b(public|private|protected|static|void|class|interface|extends|implements|new|return|if|else|for|while|int|String|boolean)\b",
                "java_keyword",
            ),
            (r"\b[A-Z][a-zA-Z0-9]*\b", "java_class"),
        ]
        self._apply_patterns_to_block(
            code, offset, tokens_map, language, patterns, "code_block"
        )

    def _analyze_c_tokens_for_block(
        self, code: str, offset: int, tokens_map: dict, language: str
    ):
        """Analyse les tokens C/C++/C#."""
        prefix = "csharp" if language in ("csharp", "cs") else "c"
        patterns = [
            (r"//.*$", f"{prefix}_comment"),
            (r"/\*.*?\*/", f"{prefix}_comment"),
            (r'"[^"]*"', f"{prefix}_string"),
            (r"#\w+.*$", f"{prefix}_preprocessor"),
            (
                r"\b(int|void|char|float|double|return|if|else|for|while|class|public|private|static|using|namespace|Console|WriteLine)\b",
                f"{prefix}_keyword",
            ),
            (r"\b[A-Z][a-zA-Z0-9]*\b", f"{prefix}_class"),
            (r"\b\d+\b", f"{prefix}_number"),
        ]
        self._apply_patterns_to_block(
            code, offset, tokens_map, language, patterns, "code_block"
        )

    def _analyze_html_tokens_for_block(
        self, code: str, offset: int, tokens_map: dict, language: str
    ):
        """Analyse les tokens HTML."""
        patterns = [
            (r"<!--.*?-->", "html_comment"),
            (r"<[^>]+>", "html_tag"),
            (r'"[^"]*"', "html_string"),
        ]
        self._apply_patterns_to_block(
            code, offset, tokens_map, language, patterns, "code_block"
        )

    def _analyze_sql_tokens_for_block(
        self, code: str, offset: int, tokens_map: dict, language: str
    ):
        """Analyse les tokens SQL."""
        patterns = [
            (r"--.*$", "sql_comment"),
            (r"'[^']*'", "sql_string"),
            (
                r"\b(SELECT|FROM|WHERE|INSERT|UPDATE|DELETE|CREATE|TABLE|INTO|VALUES|AND|OR|JOIN|ON|AS|ORDER|BY|GROUP|HAVING|LIMIT)\b",
                "sql_keyword",
            ),
        ]
        self._apply_patterns_to_block(
            code, offset, tokens_map, language, patterns, "code_block"
        )

    def _analyze_bash_tokens_for_block(
        self, code: str, offset: int, tokens_map: dict, language: str
    ):
        """Analyse les tokens Bash."""
        patterns = [
            (r"#.*$", "bash_comment"),
            (r'"[^"]*"', "bash_string"),
            (r"'[^']*'", "bash_string"),
            (
                r"\b(echo|cd|ls|mkdir|rm|cp|mv|cat|grep|sed|awk|if|then|else|fi|for|do|done|while)\b",
                "bash_command",
            ),
        ]
        self._apply_patterns_to_block(
            code, offset, tokens_map, language, patterns, "code_block"
        )

    def _analyze_php_tokens_for_block(
        self, code: str, offset: int, tokens_map: dict, language: str
    ):
        """Analyse les tokens PHP."""
        patterns = [
            (r"//.*$", "php_comment"),
            (r"/\*.*?\*/", "php_comment"),
            (r'"[^"]*"', "php_string"),
            (r"'[^']*'", "php_string"),
            (r"<\?php|\?>", "php_tag"),
            (
                r"\b(echo|print|function|return|if|else|for|while|class|public|private)\b",
                "php_keyword",
            ),
        ]
        self._apply_patterns_to_block(
            code, offset, tokens_map, language, patterns, "code_block"
        )

    def _analyze_ruby_tokens_for_block(
        self, code: str, offset: int, tokens_map: dict, language: str
    ):
        """Analyse les tokens Ruby."""
        patterns = [
            (r"#.*$", "ruby_comment"),
            (r'"[^"]*"', "ruby_string"),
            (r"'[^']*'", "ruby_string"),
            (
                r"\b(def|end|class|module|if|else|elsif|unless|while|do|puts|print|require)\b",
                "ruby_keyword",
            ),
            (r"\b(puts|print|gets)\b", "ruby_method"),
        ]
        self._apply_patterns_to_block(
            code, offset, tokens_map, language, patterns, "code_block"
        )

    def _analyze_css_tokens_for_block(
        self, code: str, offset: int, tokens_map: dict, language: str
    ):
        """Analyse les tokens CSS."""
        patterns = [
            (r"/\*.*?\*/", "css_comment"),
            (r"[.#]?[a-zA-Z_][a-zA-Z0-9_-]*(?=\s*\{)", "css_selector"),  # Sélecteurs
            (r"[a-zA-Z-]+(?=\s*:)", "css_property"),  # Propriétés
            (r":\s*([^;{}]+)", "css_value"),  # Valeurs
            (r"\d+(\.\d+)?(px|em|rem|%|vh|vw|pt|cm|mm|in)", "css_unit"),  # Unités
            (r'"[^"]*"', "css_string"),
            (r"'[^']*'", "css_string"),
            (r"#[a-fA-F0-9]{3,8}", "css_value"),  # Couleurs hex
        ]
        self._apply_patterns_to_block(
            code, offset, tokens_map, language, patterns, "code_block"
        )

    def _analyze_dockerfile_tokens_for_block(
        self, code: str, offset: int, tokens_map: dict, language: str
    ):
        """Analyse les tokens Dockerfile."""
        patterns = [
            (r"#.*$", "dockerfile_comment"),
            (
                r"\b(FROM|RUN|CMD|LABEL|MAINTAINER|EXPOSE|ENV|ADD|COPY|ENTRYPOINT|VOLUME|USER|WORKDIR|ARG|ONBUILD|STOPSIGNAL|HEALTHCHECK|SHELL)\b",
                "dockerfile_instruction",
            ),
            (r'"[^"]*"', "dockerfile_string"),
            (r"'[^']*'", "dockerfile_string"),
            (r"\$\{?[a-zA-Z_][a-zA-Z0-9_]*\}?", "dockerfile_variable"),
            (r"--[a-zA-Z-]+=?", "dockerfile_flag"),
        ]
        self._apply_patterns_to_block(
            code, offset, tokens_map, language, patterns, "code_block"
        )

    def _apply_patterns_to_block(
        self,
        code: str,
        offset: int,
        tokens_map: dict,
        language: str,
        patterns: list,
        default_token: str,
    ):
        """Applique une liste de patterns regex à un bloc de code."""
        # D'abord, marquer tout comme default_token
        for i, _ in enumerate(code):
            if (offset + i) not in tokens_map:
                tokens_map[offset + i] = (language, default_token)

        # Ensuite, appliquer les patterns spécifiques
        for pattern, token_type in patterns:
            for match in re.finditer(pattern, code, re.MULTILINE | re.IGNORECASE):
                for i in range(match.start(), match.end()):
                    tokens_map[offset + i] = (language, token_type)

    def _finish_streaming_animation(self, _interrupted=False):
        """
        Finalise l'animation de streaming avec le formatage complet.
        IMPORTANT: La coloration syntaxique a déjà été appliquée pendant l'animation,
        donc on ne refait PAS le reformatage des blocs de code.
        """
        try:
            if not hasattr(self, "typing_widget") or self.typing_widget is None:
                self.set_input_state(True)
                return

            # Récupérer le texte ACTUEL du widget (déjà coloré pendant l'animation)
            self.typing_widget.configure(state="normal")
            current_widget_text = self.typing_widget.get("1.0", "end-1c")

            # Mettre à jour l'historique avec le texte actuel du widget
            if self.conversation_history:
                self.conversation_history[-1]["text"] = current_widget_text

            # IMPORTANT: S'assurer que typing_text est défini pour le formatage
            self.typing_text = current_widget_text

            # Réinitialiser les positions pour forcer un formatage complet
            if hasattr(self, "_formatted_positions"):
                self._formatted_positions.clear()
            if hasattr(self, "_formatted_bold_contents"):
                self._formatted_bold_contents.clear()

            # ============================================================
            # 🎨 PAS DE RÉ-ANALYSE DES BLOCS DE CODE
            # La coloration a déjà été faite pendant l'animation
            # On applique juste le formatage Markdown (gras, italique, etc.)
            # ============================================================

            print(
                f"[DEBUG] _finish_streaming: Formatage final sur {len(current_widget_text)} caractères (coloration déjà faite)"
            )

            # Vérifier si les tableaux sont déjà formatés (présence de bordures)
            tables_already_formatted = any(
                c in current_widget_text for c in "┌┬┐│├┼┤└┴┘─"
            )

            if tables_already_formatted:
                print(
                    "[DEBUG] _finish_streaming: Tableaux déjà formatés, pas de reconstruction"
                )
                # Les tableaux sont déjà formatés pendant l'animation
                # On applique juste le formatage Markdown sans détruire le widget
                self._apply_unified_progressive_formatting(self.typing_widget)
            else:
                print(
                    "[DEBUG] _finish_streaming: Tableaux non formatés, formatage nécessaire"
                )
                # Pré-analyser les tableaux
                self._table_blocks = self._preanalyze_markdown_tables(
                    current_widget_text
                )

                # Formater les tableaux Markdown (reconstruit le widget)
                self._format_markdown_tables_in_widget(
                    self.typing_widget, current_widget_text
                )

                # Formatage unifié (gras, italique, code inline, etc.)
                self._apply_unified_progressive_formatting(self.typing_widget)

            # Les liens ont déjà été collectés pendant l'animation dans _pending_links
            # Ne PAS les rescanner ni les effacer
            print(
                f"[DEBUG] _finish_streaming: {len(self._pending_links) if hasattr(self, '_pending_links') else 0} liens dans _pending_links"
            )

            # Convertir les liens en cliquables
            self._convert_temp_links_to_clickable(self.typing_widget)

            # ============================================================
            # 📥 GESTION SPÉCIALE DU LIEN DE TÉLÉCHARGEMENT DE FICHIER
            # ============================================================
            if hasattr(self, "_pending_file_download") and self._pending_file_download:
                try:
                    filename = self._pending_file_download.get("filename", "fichier")
                    file_path = self._pending_file_download.get("file_path")

                    # Capturer le widget dans une variable locale
                    current_widget = self.typing_widget

                    # Ajouter le nom du fichier avec lien cliquable
                    current_widget.configure(state="normal")
                    current_widget.insert("end", filename)

                    # Trouver la position du nom de fichier
                    text_content = current_widget.get("1.0", "end-1c")
                    filename_pos = text_content.rfind(filename)
                    if filename_pos != -1:
                        # Calculer la ligne et colonne
                        lines_before = text_content[:filename_pos].count("\n")
                        col_before = (
                            filename_pos - text_content[:filename_pos].rfind("\n") - 1
                            if "\n" in text_content[:filename_pos]
                            else filename_pos
                        )

                        start_idx = f"{lines_before + 1}.{col_before}"
                        end_idx = f"{lines_before + 1}.{col_before + len(filename)}"

                        # Créer un tag unique pour ce lien
                        tag_name = f"file_download_{filename}"

                        # Configurer le tag avec style de lien
                        current_widget.tag_add(tag_name, start_idx, end_idx)
                        current_widget.tag_config(
                            tag_name,
                            foreground="#3b82f6",
                            underline=True,
                            font=("Segoe UI", 10, "bold"),
                        )

                        # Capturer les données dans la closure
                        def make_click_handler(path, name):
                            def on_click(_event):
                                self.download_file_to_downloads(path, name)

                            return on_click

                        def make_enter_handler(widget):
                            def on_enter(_event):
                                widget.config(cursor="hand2")

                            return on_enter

                        def make_leave_handler(widget):
                            def on_leave(_event):
                                widget.config(cursor="")

                            return on_leave

                        # Bind du clic sur le nom du fichier avec closures
                        current_widget.tag_bind(
                            tag_name,
                            "<Button-1>",
                            make_click_handler(file_path, filename),
                        )
                        current_widget.tag_bind(
                            tag_name, "<Enter>", make_enter_handler(current_widget)
                        )
                        current_widget.tag_bind(
                            tag_name, "<Leave>", make_leave_handler(current_widget)
                        )

                    current_widget.configure(state="disabled")

                    # Nettoyer le pending_file_download
                    self._pending_file_download = None

                except Exception as e:
                    print(f"Erreur ajout lien fichier: {e}")

            # Ajustement final de la hauteur
            self._adjust_height_final_no_scroll(self.typing_widget)

            # Réactiver le scroll
            self._reactivate_text_scroll(self.typing_widget)

            self.typing_widget.configure(state="disabled")

            # Afficher le timestamp
            self._show_timestamp_for_current_message()

            # Réactiver la saisie
            self.set_input_state(True)

            # Scroll final
            self.root.after(200, self._final_smooth_scroll_to_bottom)

            # Nettoyage des variables streaming
            self._streaming_mode = False
            self._streaming_buffer = ""
            self._streaming_complete = False

            # Nettoyage des variables d'animation (comme finish_typing_animation_dynamic)
            if hasattr(self, "typing_widget"):
                delattr(self, "typing_widget")
            if hasattr(self, "typing_text"):
                delattr(self, "typing_text")
            if hasattr(self, "typing_index"):
                delattr(self, "typing_index")

            self._typing_interrupted = False

            # Nettoyer le cache de formatage
            if hasattr(self, "_formatted_positions"):
                delattr(self, "_formatted_positions")

            print(
                f"✅ [STREAM] Animation terminée: {len(current_widget_text)} caractères"
            )

        except Exception as e:
            print(f"❌ [STREAM] Erreur finalisation: {e}")
            traceback.print_exc()
            self.set_input_state(True)

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

    def scroll_to_bottom(self):
        """Version CORRIGÉE - Scroll contrôlé avec délai"""
        # CORRECTION : Ajouter un délai pour laisser le temps au contenu de se rendre
        self.root.after(200, self._perform_scroll_to_bottom)

    def _perform_scroll_to_bottom(self):
        """Scroll synchronisé pour éviter le décalage entre icônes et texte"""
        try:
            # Forcer la mise à jour de TOUT l'interface avant le scroll
            self.root.update_idletasks()
            self.main_container.update_idletasks()

            if hasattr(self, "chat_frame"):
                self.chat_frame.update_idletasks()

            if self.use_ctk:
                # CustomTkinter
                if hasattr(self, "chat_frame"):
                    parent = self.chat_frame.master
                    while parent and not hasattr(parent, "yview_moveto"):
                        parent = parent.master

                    if parent and hasattr(parent, "yview_moveto"):
                        # Double mise à jour pour synchronisation parfaite
                        parent.update_idletasks()
                        parent.yview_moveto(1.0)
                        # Petite pause pour éviter le décalage
                        self.root.after(1, lambda: parent.yview_moveto(1.0))
            else:
                # Tkinter standard
                parent = self.chat_frame.master
                if hasattr(parent, "yview_moveto"):
                    parent.update_idletasks()
                    parent.yview_moveto(1.0)
                    self.root.after(1, lambda: parent.yview_moveto(1.0))

        except Exception as e:
            print(f"Erreur scroll synchronisé: {e}")

    def _force_scroll_bottom(self):
        """Force le scroll vers le bas - tentative secondaire"""
        try:
            if self.use_ctk:
                parent = self.chat_frame.master
                if hasattr(parent, "yview_moveto"):
                    parent.yview_moveto(1.0)
            else:
                parent = self.chat_frame.master
                if hasattr(parent, "yview_moveto"):
                    parent.yview_moveto(1.0)
        except Exception:
            pass  # Silencieux pour éviter spam logs

    def scroll_to_top(self):
        """Fait défiler vers le HAUT de la conversation (pour clear chat)"""
        try:
            self.root.update_idletasks()

            if self.use_ctk:
                # CustomTkinter - Chercher le scrollable frame
                if hasattr(self, "chat_frame"):
                    try:
                        # Méthode 1: Via le parent canvas (plus fiable)
                        parent = self.chat_frame.master
                        while parent and not hasattr(parent, "yview_moveto"):
                            parent = parent.master

                        if parent and hasattr(parent, "yview_moveto"):
                            parent.update_idletasks()
                            parent.yview_moveto(0.0)  # 0.0 pour le HAUT
                            self.logger.debug(
                                "Scroll vers le haut CTk via parent canvas"
                            )
                        else:
                            # Méthode 2: Canvas direct
                            canvas = self._get_parent_canvas()
                            if canvas:
                                canvas.update_idletasks()
                                canvas.yview_moveto(0.0)  # 0.0 pour le HAUT
                                self.logger.debug(
                                    "Scroll vers le haut CTk via canvas parent"
                                )
                            else:
                                self.logger.warning("Canvas parent non disponible")
                    except Exception as e:
                        self.logger.error("Erreur scroll vers le haut CTk: %s", e)
            else:
                # Tkinter standard - Chercher le canvas scrollable
                try:
                    parent = self.chat_frame.master
                    if hasattr(parent, "yview_moveto"):
                        parent.update_idletasks()
                        parent.yview_moveto(0.0)  # 0.0 pour le HAUT
                        self.logger.debug(
                            "Scroll vers le haut tkinter via parent direct"
                        )
                    else:
                        # Chercher dans la hiérarchie
                        current = parent
                        while current:
                            if hasattr(current, "yview_moveto"):
                                current.update_idletasks()
                                current.yview_moveto(0.0)  # 0.0 pour le HAUT
                                self.logger.debug(
                                    "Scroll vers le haut tkinter via hiérarchie"
                                )
                                break
                            current = current.master
                except Exception as e:
                    self.logger.error("Erreur scroll vers le haut tkinter: %s", e)

            # Forcer une seconde tentative après délai court
            self.root.after(100, self._force_scroll_top)

        except Exception as e:
            self.logger.error("Erreur critique lors du scroll vers le haut: %s", e)

    def _force_scroll_top(self):
        """Force le scroll vers le haut - tentative secondaire"""
        try:
            if self.use_ctk:
                parent = self.chat_frame.master
                if hasattr(parent, "yview_moveto"):
                    parent.yview_moveto(0.0)  # 0.0 pour le HAUT
            else:
                parent = self.chat_frame.master
                if hasattr(parent, "yview_moveto"):
                    parent.yview_moveto(0.0)  # 0.0 pour le HAUT
        except Exception:
            pass  # Silencieux pour éviter spam logs

    # ...existing code...

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

        except Exception as e:
            self.logger.error("Erreur lors de l'effacement: %s", e)
            messagebox.showerror("Erreur", f"Impossible d'effacer la conversation: {e}")

    def show_welcome_message(self):
        """Affiche le message de bienvenue initial"""
        # Détection des capacités CustomAI
        ultra_status = ""
        if hasattr(self, "custom_ai") and self.custom_ai:
            if self.custom_ai.ultra_mode:
                ultra_status = """ (Mode **Ultra**)"""
            else:
                ultra_status = """ (Mode **Classique**)"""

        welcome_text = f"""Bonjour ! Je suis votre **Assistant IA Local** 🤖{ultra_status}

    Je peux vous aider avec :
    • **Conversations naturelles** : Discutez avec moi, posez-moi toutes vos questions et obtenez des réponses claires.
    • **Analyse de documents PDF et DOCX** : Importez-les, et je pourrai les résumer ou répondre à vos questions sur leur contenu.
    • **Génération et analyse de code** : Demandez-moi de générer, corriger ou expliquer du code.
    • **Recherche internet avec résumés intelligents** : Je peux effectuer des recherches sur internet pour vous !

    **Commencez** par me dire bonjour ou posez-moi directement une question !"""

        # Utiliser la même fonction que pour les autres messages IA
        self.add_message_bubble(welcome_text, is_user=False, message_type="text")

    def show_help(self):
        """Affiche l'aide"""
        help_text = """**🆘 Aide - My Personal AI**

**📝 Comment utiliser :**
• Tapez votre message et appuyez sur Entrée
• Utilisez Shift+Entrée pour un saut de ligne
• Utilisez les boutons PDF/DOCX/Code

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

    def load_pdf_file(self):
        """Charge un fichier PDF"""
        file_path = filedialog.askopenfilename(
            title="Sélectionner un fichier PDF", filetypes=[("Fichiers PDF", "*.pdf")]
        )

        if file_path:
            self.process_file(file_path, "PDF")

    def load_docx_file(self):
        """Charge un fichier DOCX"""
        file_path = filedialog.askopenfilename(
            title="Sélectionner un fichier DOCX",
            filetypes=[("Fichiers Word", "*.docx")],
        )

        if file_path:
            self.process_file(file_path, "DOCX")

    def load_code_file(self):
        """Charge un fichier de code"""
        file_path = filedialog.askopenfilename(
            title="Sélectionner un fichier de code",
            filetypes=[
                ("Fichiers Python", "*.py"),
                ("Fichiers JavaScript", "*.js"),
                ("Fichiers HTML", "*.html"),
                ("Tous les fichiers", "*.*"),
            ],
        )

        if file_path:
            self.process_file(file_path, "Code")

    def process_file(self, file_path, file_type):
        """Traite un fichier"""
        try:
            filename = os.path.basename(file_path)

            # Animation de traitement
            self.is_thinking = True
            self.add_message_bubble(f"📎 Fichier chargé : **{filename}**", is_user=True)

            # Traitement en arrière-plan
            threading.Thread(
                target=self.process_file_background,
                args=(file_path, file_type, filename),
                daemon=True,
            ).start()

        except Exception as e:
            self.logger.error("Erreur lors du chargement du fichier: %s", e)
            messagebox.showerror("Erreur", f"Impossible de charger le fichier: {e}")

    def process_file_background(self, file_path, file_type, filename):
        """Traite le fichier en arrière-plan avec système 1M tokens"""
        try:
            self.logger.info(
                "Traitement du fichier: %s (type: %s)", filename, file_type
            )

            # Utiliser le processeur unifié
            result = self.file_processor.process_file(file_path)

            if result.get("error"):
                raise ValueError(result["error"])

            content = result.get("content", "")
            self.logger.info("Fichier traité: %s caractères", len(content))

            # Vérifier que le contenu n'est pas vide
            if not content or not content.strip():
                raise ValueError(f"Le fichier {filename} semble vide ou illisible")

            # 🚀 NOUVEAU: Stocker dans CustomAI unifié avec processeurs avancés
            chunks_created = 0
            if self.custom_ai:
                try:
                    self.logger.info(
                        "🚀 Ajout au CustomAI avec processeurs avancés: %s", filename
                    )

                    # Utiliser la nouvelle méthode qui exploite les processeurs PDF/DOCX/Code
                    if hasattr(self.custom_ai, "add_file_to_context"):
                        # Méthode avancée qui utilise les processeurs spécialisés
                        result = self.custom_ai.add_file_to_context(file_path)
                        chunk_ids = result.get("chunk_ids", [])
                        chunks_created = result.get(
                            "chunks_created", len(chunk_ids) if chunk_ids else 0
                        )

                        if result.get("success"):
                            processor_used = result.get("processor_used", "advanced")
                            analysis_info = result.get(
                                "analysis_info", f"{len(content)} caractères"
                            )
                            self.logger.info(
                                "📄 Processeur %s utilisé: %s",
                                processor_used,
                                analysis_info,
                            )
                            print(
                                f"🔧 Traitement avancé: {processor_used} - {analysis_info}"
                            )
                        else:
                            self.logger.warning(
                                "Échec traitement avancé: %s",
                                result.get("message", "Erreur inconnue"),
                            )
                    else:
                        # Méthode de fallback - utiliser add_document_to_context
                        result = self.custom_ai.add_document_to_context(
                            content, filename
                        )
                        chunks_created = result.get("chunks_created", 0)

                    # Statistiques après ajout
                    stats = self.custom_ai.get_context_stats()
                    self.logger.info(
                        "📊 Nouveau contexte: %s tokens (%s)",
                        stats.get("context_size", 0),
                        stats.get("utilization_percent", 0),
                    )

                    print(
                        f"🚀 Document ajouté au CustomAI: {chunks_created} chunks créés"
                    )

                except Exception as e:
                    self.logger.warning("Erreur ajout CustomAI: %s", e)
                    chunks_created = 0

            # Stocker aussi dans la mémoire classique pour compatibilité
            if hasattr(self.ai_engine, "local_ai") and hasattr(
                self.ai_engine.local_ai, "conversation_memory"
            ):
                self.ai_engine.local_ai.conversation_memory.store_document_content(
                    filename, content
                )
                self.logger.info(
                    "Contenu stocké dans la mémoire classique pour %s", filename
                )
            else:
                self.logger.warning("Mémoire de conversation classique non disponible")

            # Arrêter l'animation
            self.is_thinking = False

            # Confirmer le traitement avec informations système 1M tokens
            preview = content[:200] + "..." if len(content) > 200 else content

            if chunks_created > 0:
                # Message avec informations CustomAI
                stats = self.custom_ai.get_context_stats()
                success_msg = f"""✅ **{filename}** traité avec succès !

🚀 **Ajouté au CustomAI {'Ultra' if self.custom_ai.ultra_mode else 'Classique'}:**
• {chunks_created} chunks créés
• Contexte total: {stats.get('context_size', 0):,} / {stats.get('max_context_length', 1000000):,} tokens
• Utilisation: {stats.get('utilization_percent', 0):.1f}%

Vous pouvez maintenant me poser des questions sur ce document."""
            else:
                # Message standard
                success_msg = f"✅ **{filename}** traité avec succès !\n\n**Aperçu du contenu:**\n{preview}\n\nVous pouvez maintenant me poser des questions dessus."

            self.root.after(0, lambda: self.add_ai_response(success_msg))

        except Exception as e:
            self.logger.error("Erreur lors du traitement de %s: %s", filename, str(e))
            self.is_thinking = False
            error_msg = f"❌ Erreur lors du traitement de **{filename}** : {str(e)}"
            self.root.after(0, lambda: self.add_ai_response(error_msg))

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
                    except Exception as e:
                        print(f"⚠️ DEBUG: Erreur test réponse: {e}")
                else:
                    print("❌ DEBUG: Échec de l'initialisation")

            except Exception as e:
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
        except Exception as e:
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


def main():
    """Point d'entrée principal"""
    try:
        app = ModernAIGUI()
        app.run()
    except Exception as e:
        print(f"❌ Erreur lors du démarrage: {e}")
        traceback.print_exc()


if __name__ == "__main__":
    main()
