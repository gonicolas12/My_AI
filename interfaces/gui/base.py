"""Base GUI class and shared utilities for ModernAIGUI."""

import asyncio
import os
import platform
import random
import re
import threading
import traceback
import tkinter as tk
from datetime import datetime
from tkinter import messagebox

from core.ai_engine import AIEngine
from core.config import Config
from utils.file_processor import FileProcessor
from utils.logger import setup_logger

# Import des styles (uniquement ce qui est utilisé)
try:
    from interfaces.modern_styles import (
        FONT_CONFIG,
        FONT_SIZES,
        RESPONSIVE_BREAKPOINTS,
    )
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
    from models.custom_ai_model import CustomAIModel  # noqa: F401  # pylint: disable=unused-import

    ULTRA_1M_AVAILABLE = True
    print("🚀 Modèle CustomAI unifié avec système 1M tokens intégré !")
except ImportError:
    ULTRA_1M_AVAILABLE = False
    print("📝 Interface moderne en mode standard")


class BaseGUI:
    """Base class providing shared state and core logic."""

    def __init__(self):
        """Initialise l'interface moderne avec système 1M tokens"""
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
                    f"📊 Contexte initial: {stats.get('context_size', 0):,} / {stats.get('max_context_length', 1000000):,} tokens"
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
                    # Sauvegarder le contenu avant de désactiver
                    try:
                        self._saved_input_content = self.input_text.get("1.0", "end-1c")
                    except (tk.TclError, AttributeError):
                        self._saved_input_content = ""
            # Boutons PDF, DOCX, Code
            for btn_name in ["pdf_btn", "docx_btn", "code_btn"]:
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

            # Ajouter le message utilisateur
            self.add_message_bubble(message, is_user=True)

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

        except (ConnectionError, TimeoutError, AttributeError) as e:
            print(f"❌ [GUI] Erreur: {e}")
            response = f"❌ Erreur IA : {e}"
            if self.current_request_id == request_id:
                self.root.after(0, lambda: self.add_ai_response(response))

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
