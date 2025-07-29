"""
Interface Graphique Moderne - My AI Personal Assistant
Inspirée de l'interface Claude avec animations et design moderne
"""
import tkinter as tk
from tkinter import ttk, scrolledtext, filedialog, messagebox
import tkinter.dnd as dnd
from tkinterdnd2 import DND_FILES, TkinterDnD
import threading
import sys
import os
import time
import re
import platform
from typing import Optional, Any, List, Dict
from datetime import datetime
import webbrowser

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Imports pour asyncio
import asyncio
import concurrent.futures

try:
    import customtkinter as ctk
    CTK_AVAILABLE = True
except ImportError:
    CTK_AVAILABLE = False
    # CustomTkinter non disponible, utilisation de tkinter standard

try:
    from tkinterdnd2 import TkinterDnD
    DND_AVAILABLE = True
except ImportError:
    DND_AVAILABLE = False
    # TkinterDnD2 non disponible, drag & drop désactivé

try:
    from interfaces.modern_styles import *
except ImportError:
    # Fallback colors si le fichier de styles n'est pas disponible - STYLE CLAUDE
    MODERN_COLORS = {
        'bg_primary': '#212121',      # Fond principal plus clair 
        'bg_secondary': '#2f2f2f',    # Fond secondaire
        'bg_chat': '#212121',         # Fond de chat 
        'bg_user': '#3b82f6',         # Bleu pour utilisateur
        'bg_ai': '#2f2f2f',           # Gris foncé pour IA
        'text_primary': '#ffffff',     # Texte principal blanc
        'text_secondary': '#9ca3af',   # Texte secondaire gris
        'accent': '#3b82f6',          # Accent bleu
        'accent_hover': '#2563eb',    # Accent hover
        'border': '#404040',          # Bordures
        'input_bg': '#2f2f2f',        # Fond input
        'button_hover': '#404040'     # Bouton hover
    }

try:
    import customtkinter as ctk
    CTK_AVAILABLE = True
except ImportError:
    CTK_AVAILABLE = False
    # CustomTkinter non disponible, utilisation de tkinter standard

try:
    from core.ai_engine import AIEngine
    from core.config import Config
    from processors.pdf_processor import PDFProcessor
    from processors.docx_processor import DOCXProcessor
    from processors.code_processor import CodeProcessor
    from utils.logger import Logger
    from utils.file_manager import FileManager
except ImportError as e:
    # Fallback for direct execution
    import sys
    from pathlib import Path
    
    # Add parent directory to path
    parent_dir = Path(__file__).parent.parent
    sys.path.insert(0, str(parent_dir))
    
    from core.ai_engine import AIEngine
    from core.config import Config
    from processors.pdf_processor import PDFProcessor
    from processors.docx_processor import DOCXProcessor
    from processors.code_processor import CodeProcessor
    from utils.logger import Logger
    from utils.file_manager import FileManager


class ModernAIGUI:
    def add_ai_response(self, response):
        # Ne surtout pas réactiver l'input ici !
        self.add_message_bubble(response, is_user=False)
        # (Aucun set_input_state(True) ici)
    def set_input_state(self, enabled: bool):
        """Active/désactive la zone de saisie et les boutons d'action, mais le bouton Envoyer devient STOP si IA occupe."""
        import traceback
        # if enabled:
        #     traceback.print_stack()
        try:
            # Zone de saisie
            if hasattr(self, 'input_text'):
                state = "normal" if enabled else "disabled"
                try:
                    self.input_text.configure(state=state)
                except Exception:
                    pass
                if enabled:
                    self.root.after(100, lambda: self._safe_focus_input())
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
            if hasattr(self, 'send_button'):
                if enabled:
                    self._set_send_button_normal()
                else:
                    self._set_send_button_stop()
        except Exception:
            pass

    def _set_send_button_normal(self):
        """Affiche le bouton Envoyer normal et réactive l'envoi."""
        try:
            if hasattr(self, 'send_button'):
                # Orange vif, texte blanc, style moderne
                if self.use_ctk:
                    self.send_button.configure(
                        text="Envoyer ↗",
                        command=lambda: self.send_message(),
                        state="normal",
                        fg_color=self.colors['accent'],
                        hover_color="#ff5730",
                        text_color="#ffffff",
                        border_width=0
                    )
                else:
                    self.send_button.configure(
                        text="Envoyer ↗",
                        command=lambda: self.send_message(),
                        state="normal",
                        bg=self.colors['accent'],
                        fg="#ffffff",
                        activebackground="#ff5730",
                        relief="flat",
                        border=0
                    )
        except Exception:
            pass

    def _set_send_button_stop(self):
        """Affiche le bouton STOP (carré noir dans cercle blanc, fond blanc, bord noir) pour interrompre l'IA."""
        try:
            if hasattr(self, 'send_button'):
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
                        border_width=2
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
                        relief="solid"
                    )
        except Exception:
            pass

    def interrupt_ai(self):
        """Interrompt l'IA : stop écriture, recherche, réflexion, etc."""
        try:
            self.is_interrupted = True
            self.current_request_id += 1  # Invalide toutes les requêtes en cours

            # Arrêter l'animation de frappe IA (si en cours)
            if hasattr(self, 'stop_typing_animation'):
                try:
                    self.stop_typing_animation()
                except Exception:
                    pass
            # Arrêter la recherche internet (si en cours)
            if hasattr(self, 'stop_internet_search'):
                try:
                    self.stop_internet_search()
                except Exception:
                    pass
            # Arrêter la réflexion IA (si en cours)
            if hasattr(self, 'stop_thinking'):
                try:
                    self.stop_thinking()
                except Exception:
                    pass
            # Remettre l'UI en état normal
            self.set_input_state(True)
            self.is_thinking = False
            self.is_searching = False
        except Exception:
            pass

    def _safe_focus_input(self):
        """Met le focus sur l'input de manière sécurisée"""
        try:
            if hasattr(self, 'input_text'):
                current_state = self.input_text.cget("state")
                if current_state == "normal":
                    self.input_text.focus_set()
                    # Restaurer le contenu sauvegardé s'il existe
                    if hasattr(self, '_saved_input_content') and self._saved_input_content:
                        current_content = self.input_text.get("1.0", "end-1c").strip()
                        if not current_content:  # Seulement si vide
                            self.input_text.insert("1.0", self._saved_input_content)
                        delattr(self, '_saved_input_content')
        except Exception as e:
            pass

    """Interface Graphique Moderne pour l'Assistant IA - Style Claude"""
    
    def __init__(self):
        """Initialise l'interface moderne"""
        self.is_interrupted = False  # Pour interruption robuste
        self.logger = Logger.get_logger("modern_ai_gui")
        self.config = Config()
        self.ai_engine = AIEngine(self.config)
        self.file_manager = FileManager()

        # Processors
        self.pdf_processor = PDFProcessor()
        self.docx_processor = DOCXProcessor()
        self.code_processor = CodeProcessor()

        # État de l'application
        self.is_thinking = False
        self.is_searching = False
        self.conversation_history = []

        # Variables d'animation
        self.thinking_dots = 0
        self.search_frame = 0

        # Configuration de l'interface
        self.setup_modern_gui()
        self.create_modern_layout()
        self.setup_keyboard_shortcuts()
        self.show_welcome_message()
        
        # Initialisation IA en arrière-plan
        self.initialize_ai_async()
        self.ensure_input_is_ready()
    
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
        
        # Plein écran automatique et premier plan
        self.root.attributes('-topmost', True)  # Premier plan
        self.root.state('zoomed')  # Plein écran sur Windows
        self.root.after(1000, lambda: self.root.attributes('-topmost', False))  # Retirer topmost après 1s
        
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
        if hasattr(self, 'RESPONSIVE_BREAKPOINTS'):
            if self.screen_width < RESPONSIVE_BREAKPOINTS['small']:
                self.layout_size = 'small'
            elif self.screen_width < RESPONSIVE_BREAKPOINTS['medium']:
                self.layout_size = 'medium'
            else:
                self.layout_size = 'large'
        else:
            # Fallback
            if self.screen_width < 800:
                self.layout_size = 'small'
            elif self.screen_width < 1200:
                self.layout_size = 'medium'
            else:
                self.layout_size = 'large'
    
    def setup_fonts(self):
        """Configure les polices selon l'OS et la taille d'écran"""
        os_name = platform.system().lower()
        
        # Sélection des polices selon l'OS
        if 'FONT_CONFIG' in globals() and os_name in FONT_CONFIG:
            font_family = FONT_CONFIG[os_name]['primary']
            mono_family = FONT_CONFIG[os_name]['mono']
        else:
            # Fallback
            if os_name == 'windows':
                font_family = 'Segoe UI'
                mono_family = 'Consolas'
            elif os_name == 'darwin':  # macOS
                font_family = 'SF Pro Display'
                mono_family = 'SF Mono'
            else:  # Linux
                font_family = 'Ubuntu'
                mono_family = 'Ubuntu Mono'
        
        # Tailles selon la résolution
        if 'FONT_SIZES' in globals() and self.layout_size in FONT_SIZES:
            sizes = FONT_SIZES[self.layout_size]
            self.style_config = FONT_SIZES  # Stocker pour utilisation ultérieure
        else:
            # Fallback amélioré avec des tailles plus raisonnables - UNIFIÉ À 11px
            sizes = {
                'title': 20,      # Réduit de 28 à 20
                'subtitle': 12,   # Réduit de 16 à 12
                'body': 11,       # Unifié à 11 pour cohérence
                'small': 10,      # Réduit de 12 à 10
                'chat': 11,       # UNIFIÉ À 11 comme les messages
                'code': 11,       # Réduit de 13 à 11
                'message': 11,    # UNIFIÉ À 11 pour cohérence totale
                'bold': 11        # UNIFIÉ À 11 pour cohérence
            }
            # Créer style_config même en fallback avec des tailles réduites - UNIFIÉ À 11px
            self.style_config = {
                'large_screen': {
                    'title': 22, 'subtitle': 14, 'body': 11, 'small': 10,
                    'chat': 11, 'code': 11, 'message': 11, 'bold': 11
                },
                'medium_screen': {
                    'title': 20, 'subtitle': 12, 'body': 11, 'small': 10,
                    'chat': 11, 'code': 11, 'message': 11, 'bold': 11
                },
                'small_screen': {
                    'title': 18, 'subtitle': 11, 'body': 11, 'small': 9,
                    'chat': 11, 'code': 10, 'message': 11, 'bold': 11
                }
            }
            
            # Fallback sizes selon la taille d'écran
            if self.layout_size == 'small':
                sizes = self.style_config['small_screen']
            elif self.layout_size == 'medium':
                sizes = self.style_config['medium_screen']
            else:
                sizes = self.style_config['large_screen']
        
        self.fonts = {
            'title': (font_family, sizes['title'], 'bold'),
            'subtitle': (font_family, sizes['subtitle']),
            'body': (font_family, sizes['body']),
            'chat': (font_family, sizes['chat']),
            'bold': (font_family, sizes['body'], 'bold'),
            'code': (mono_family, sizes['code'])
        }
    
    def setup_drag_drop(self):
        """Configure le drag & drop pour les fichiers"""
        if DND_AVAILABLE:
            self.root.drop_target_register(DND_FILES)
            self.root.dnd_bind('<<Drop>>', self.on_file_drop)
    
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
        if ext == '.pdf':
            file_type = "PDF"
        elif ext in ['.docx', '.doc']:
            file_type = "DOCX"
        elif ext in ['.py', '.js', '.html', '.css', '.json', '.xml', '.md', '.txt']:
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
            "info": "#3b82f6"
        }
        
        bg_color = colors_map.get(type_notif, "#3b82f6")
        
        # Créer une notification en overlay
        if self.use_ctk:
            notif_frame = ctk.CTkFrame(
                self.main_container,
                fg_color=bg_color,
                corner_radius=8,
                border_width=0
            )
            
            notif_label = ctk.CTkLabel(
                notif_frame,
                text=message,
                text_color='#ffffff',
                font=('Segoe UI', self.get_current_font_size('message'), 'bold'),
                fg_color="transparent"
            )
        else:
            notif_frame = tk.Frame(
                self.main_container,
                bg=bg_color,
                relief="flat",
                bd=0
            )
            
            notif_label = tk.Label(
                notif_frame,
                text=message,
                fg='#ffffff',
                bg=bg_color,
                font=('Segoe UI', self.get_current_font_size('message'), 'bold')
            )
        
        # Positionner en haut à droite
        notif_frame.place(relx=0.98, rely=0.02, anchor="ne")
        notif_label.pack(padx=15, pady=8)
        
        # Animation d'apparition (optionnelle)
        notif_frame.lift()  # Mettre au premier plan
        
        # Supprimer automatiquement après la durée spécifiée
        self.root.after(duration, lambda: notif_frame.destroy())
    
    def setup_fallback_style(self):
        """Style de base pour tkinter standard"""
        self.root.configure(fg_color='#1a1a1a')
        
        # Style TTK pour tkinter standard
        style = ttk.Style()
        style.theme_use('clam')
        
        # Configuration des styles sombres
        style.configure('Dark.TFrame', background='#1a1a1a')
        style.configure('Dark.TLabel', background='#1a1a1a', foreground='#ffffff')
        style.configure('Dark.TButton', background='#2d2d2d', foreground='#ffffff')
    
    def create_modern_layout(self):
        """Crée le layout moderne style Claude"""
        # Container principal
        self.main_container = self.create_frame(self.root, fg_color=self.colors['bg_primary'])
        self.main_container.grid(row=0, column=0, sticky="nsew", padx=0, pady=0)
        self.main_container.grid_columnconfigure(0, weight=1)
        self.main_container.grid_rowconfigure(1, weight=1)
        
        # Header moderne
        self.create_modern_header()
        
        # Zone de conversation principale
        self.create_conversation_area()
        
        # Zone de saisie moderne
        self.create_modern_input_area()
        
        # Animations et effets
        self.start_animations()
    
    def create_modern_header(self):
        """Crée l'en-tête moderne style Claude"""
        header_frame = self.create_frame(self.main_container, fg_color=self.colors['bg_primary'])
        header_frame.grid(row=0, column=0, sticky="ew", padx=20, pady=(20, 10))
        header_frame.grid_columnconfigure(1, weight=1)
        
        # Logo/Icône - taille réduite
        logo_label = self.create_label(
            header_frame, 
            text="🤖", 
            font=('Segoe UI', self.get_current_font_size('header')),  # Dynamique
            text_color=self.colors['accent'],  # text_color au lieu de fg
            fg_color=self.colors['bg_primary']
        )
        logo_label.grid(row=0, column=0, padx=(0, 15))
        
        # Titre principal
        title_frame = self.create_frame(header_frame, fg_color=self.colors['bg_primary'])
        title_frame.grid(row=0, column=1, sticky="w")
        
        title_label = self.create_label(
            title_frame,
            text="My Personal AI",
            font=self.fonts['title'],
            text_color=self.colors['text_primary'],  # text_color au lieu de fg
            fg_color=self.colors['bg_primary']
        )
        title_label.grid(row=0, column=0, sticky="w")
        
        subtitle_label = self.create_label(
            title_frame,
            text="Assistant IA Local - Prêt à vous aider",
            font=self.fonts['subtitle'],
            text_color=self.colors['text_secondary'],  # text_color au lieu de fg
            fg_color=self.colors['bg_primary']
        )
        subtitle_label.grid(row=1, column=0, sticky="w", pady=(2, 0))
        
        # Boutons d'action
        self.create_header_buttons(header_frame)
    
    def create_header_buttons(self, parent):
        """Crée les boutons de l'en-tête"""
        buttons_frame = self.create_frame(parent, fg_color=self.colors['bg_primary'])
        buttons_frame.grid(row=0, column=2, padx=(10, 0))
        
        # Bouton Clear Chat
        self.clear_btn = self.create_modern_button(
            buttons_frame,
            text="🗑️ Clear Chat",
            command=self.clear_chat,
            style="secondary"
        )
        self.clear_btn.grid(row=0, column=0, padx=(0, 10))

        # Bonton Help
        self.help_btn = self.create_modern_button(
            buttons_frame,
            text="❓ Aide",
            command=self.show_help,
            style="secondary"
        )
        self.help_btn.grid(row=0, column=1, padx=(0, 10))
        
        # Indicateur de statut - taille réduite
        self.status_label = self.create_label(
            buttons_frame,
            text="●",
            font=('Segoe UI', self.get_current_font_size('status')),  # Dynamique
            text_color='#00ff00',  # Vert = connecté (text_color au lieu de fg)
            fg_color=self.colors['bg_primary']
        )
        self.status_label.grid(row=0, column=2)
    
    def create_conversation_area(self):
        """Crée la zone de conversation principale"""
        # Container pour la conversation
        conv_container = self.create_frame(self.main_container, fg_color=self.colors['bg_chat'])
        conv_container.grid(row=1, column=0, sticky="nsew", padx=20, pady=(10, 20))
        conv_container.grid_columnconfigure(0, weight=1)
        conv_container.grid_rowconfigure(0, weight=1)
        
        # Zone de scroll pour les messages
        if self.use_ctk:
            self.chat_frame = ctk.CTkScrollableFrame(
                conv_container,
                fg_color=self.colors['bg_chat'],
                scrollbar_fg_color=self.colors['bg_secondary']
            )
        else:
            # Fallback avec Canvas et Scrollbar
            canvas = tk.Canvas(conv_container, fg_color=self.colors['bg_chat'], highlightthickness=0)
            scrollbar = ttk.Scrollbar(conv_container, orient="vertical", command=canvas.yview)
            self.chat_frame = tk.Frame(canvas, fg_color=self.colors['bg_chat'])
            
            canvas.configure(yscrollcommand=scrollbar.set)
            canvas.create_window((0, 0), window=self.chat_frame, anchor="nw")
            
            canvas.grid(row=0, column=0, sticky="nsew")
            scrollbar.grid(row=0, column=1, sticky="ns")
            
            # Mise à jour du scroll
            def configure_scroll(event):
                canvas.configure(scrollregion=canvas.bbox("all"))
            self.chat_frame.bind("<Configure>", configure_scroll)
        
        self.chat_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        self.chat_frame.grid_columnconfigure(0, weight=1)
        
        # Zone d'animation de réflexion
        self.thinking_frame = self.create_frame(conv_container, fg_color=self.colors['bg_chat'])
        self.thinking_frame.grid(row=1, column=0, sticky="ew", padx=20, pady=(0, 10))
        self.thinking_frame.grid_remove()  # Caché par défaut
        
        self.thinking_label = self.create_label(
            self.thinking_frame,
            text="",
            font=('Segoe UI', self.get_current_font_size('message')),  # UNIFIÉ AVEC LES MESSAGES
            text_color=self.colors['text_secondary'],  # text_color au lieu de fg
            fg_color=self.colors['bg_chat']
        )
        self.thinking_label.grid(row=0, column=0)
    
    def create_modern_input_area(self):
        """Crée la zone de saisie moderne style Claude"""
        input_container = self.create_frame(self.main_container, fg_color=self.colors['bg_primary'])
        input_container.grid(row=2, column=0, sticky="ew", padx=20, pady=(0, 20))
        input_container.grid_columnconfigure(0, weight=1)
        
        # Zone de saisie avec bordure moderne
        input_wrapper = self.create_frame(
            input_container, 
            fg_color=self.colors['border']
        )
        input_wrapper.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        input_wrapper.grid_columnconfigure(0, weight=1)
        
        # Champ de saisie
        if self.use_ctk:
            self.input_text = ctk.CTkTextbox(
                input_wrapper,
                height=60,
                fg_color=self.colors['input_bg'],
                text_color=self.colors['text_primary'],
                border_color=self.colors['border'],
                border_width=1,
                corner_radius=8,
                font=('Segoe UI', self.get_current_font_size('message'))  # UNIFIÉ AVEC LES MESSAGES
            )
        else:
            self.input_text = tk.Text(
                input_wrapper,
                height=3,
                fg_color=self.colors['input_bg'],
                fg=self.colors['text_primary'],
                font=('Segoe UI', self.get_current_font_size('message')),  # UNIFIÉ AVEC LES MESSAGES
                border=1,
                relief='solid',
                wrap=tk.WORD
            )
        
        self.input_text.grid(row=0, column=0, sticky="ew", padx=2, pady=2)
        
        # Boutons d'action
        button_frame = self.create_frame(input_container, fg_color=self.colors['bg_primary'])
        button_frame.grid(row=1, column=0, sticky="ew")
        button_frame.grid_columnconfigure(1, weight=1)
        
        # Boutons de fichiers
        file_buttons = self.create_frame(button_frame, fg_color=self.colors['bg_primary'])
        file_buttons.grid(row=0, column=0, sticky="w")
        
        self.pdf_btn = self.create_modern_button(
            file_buttons,
            text="📄 PDF",
            command=self.load_pdf_file,
            style="file"
        )
        self.pdf_btn.grid(row=0, column=0, padx=(0, 5))

        self.docx_btn = self.create_modern_button(
            file_buttons,
            text="📝 DOCX",
            command=self.load_docx_file,
            style="file"
        )
        self.docx_btn.grid(row=0, column=1, padx=(0, 5))

        self.code_btn = self.create_modern_button(
            file_buttons,
            text="💻 Code",
            command=self.load_code_file,
            style="file"
        )
        self.code_btn.grid(row=0, column=2, padx=(0, 10))
        
        # Bouton d'envoi principal
        self.send_button = self.create_modern_button(
            button_frame,
            text="Envoyer ↗",
            command=lambda: self.send_message(),  # Lambda pour s'assurer de la bonne référence
            style="primary"
        )
        self.send_button.grid(row=0, column=2, sticky="e")
        
        # Bind des événements
        self.input_text.bind('<Return>', self.on_enter_key)
        self.input_text.bind('<Shift-Return>', self.on_shift_enter)
        
        # Placeholder text
        self.set_placeholder()
    
    def create_frame(self, parent, **kwargs):
        """Crée un frame avec le bon style"""
        if self.use_ctk:
            # Convertir les paramètres tkinter vers CustomTkinter
            ctk_kwargs = {}
            for key, value in kwargs.items():
                if key == 'bg' or key == 'fg_color':
                    ctk_kwargs['fg_color'] = value
                elif key == 'fg':
                    ctk_kwargs['text_color'] = value
                elif key == 'relief':
                    # CustomTkinter ne supporte pas relief, on l'ignore
                    continue
                elif key == 'bd' or key == 'borderwidth':
                    ctk_kwargs['border_width'] = value
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
                if key == 'bg':
                    ctk_kwargs['fg_color'] = value
                elif key == 'fg':
                    ctk_kwargs['text_color'] = value
                elif key == 'font':
                    ctk_kwargs['font'] = value
                elif key == 'text':
                    ctk_kwargs['text'] = value
                elif key in ['relief', 'bd', 'borderwidth']:
                    # CustomTkinter ne supporte pas ces paramètres
                    continue
                else:
                    ctk_kwargs[key] = value
            return ctk.CTkLabel(parent, **ctk_kwargs)
        else:
            return tk.Label(parent, **kwargs)
    
    def create_modern_button(self, parent, text, command, style="primary"):
        """Crée un bouton moderne avec différents styles"""
        if style == "primary":
            bg_color = self.colors['accent']
            hover_color = '#ff5730'
            text_color = '#ffffff'
        elif style == "secondary":
            bg_color = self.colors['bg_secondary']
            hover_color = self.colors['button_hover']
            text_color = self.colors['text_primary']
        elif style == "file":
            bg_color = self.colors['bg_secondary']
            hover_color = self.colors['button_hover']
            text_color = self.colors['text_secondary']
        
        if self.use_ctk:
            return ctk.CTkButton(
                parent,
                text=text,
                command=command,
                fg_color=bg_color,
                hover_color=hover_color,
                text_color=text_color,
                font=('Segoe UI', self.get_current_font_size('message')),  # UNIFIÉ AVEC LES MESSAGES
                corner_radius=6,
                height=32
            )
        else:
            btn = tk.Button(
                parent,
                text=text,
                command=command,
                bg=bg_color,
                fg=text_color,
                font=('Segoe UI', self.get_current_font_size('message')),  # UNIFIÉ AVEC LES MESSAGES
                border=0,
                relief='flat'
            )
            
            # Effet hover pour tkinter standard
            def on_enter(e):
                btn.configure(bg=hover_color)
            def on_leave(e):
                btn.configure(bg=bg_color)
            
            btn.bind("<Enter>", on_enter)
            btn.bind("<Leave>", on_leave)
            
            return btn
    
    def add_message_bubble(self, text, is_user=True, message_type="text"):
        """Version FINALE avec animation de frappe pour les messages IA"""
        # Debug removed
        from datetime import datetime
        
        # Vérifier que le texte est une chaîne
        if not isinstance(text, str):
            if isinstance(text, dict):
                text = (text.get('response') or 
                    text.get('text') or 
                    text.get('content') or 
                    text.get('message') or 
                    str(text))
            else:
                text = str(text)
        
        # Debug removed
        
        # Ajouter à l'historique
        self.conversation_history.append({
            'text': text,
            'is_user': is_user,
            'timestamp': datetime.now(),
            'type': message_type
        })
        
        # Container principal avec espacement OPTIMAL
        msg_container = self.create_frame(self.chat_frame, fg_color=self.colors['bg_chat'])
        msg_container.grid(row=len(self.conversation_history)-1, column=0, sticky="ew", pady=(0, 12))
        msg_container.grid_columnconfigure(0, weight=1)

        if is_user:
            self.create_user_message_bubble(msg_container, text)
            # Scroll utilisateur : scroller uniquement si le bas n'est pas visible
            self.root.after(50, lambda: self._scroll_if_needed_user())
        else:
            # Crée la bulle IA mais insère le texte vide, puis lance l'animation de frappe
            from datetime import datetime
            # Frame de centrage
            center_frame = self.create_frame(msg_container, fg_color=self.colors['bg_chat'])
            center_frame.grid(row=0, column=0, padx=(250, 250), pady=(0, 0), sticky="ew")
            center_frame.grid_columnconfigure(0, weight=0)
            center_frame.grid_columnconfigure(1, weight=1)

            # Icône IA
            icon_label = self.create_label(
                center_frame,
                text="🤖",
                font=('Segoe UI', 16),
                fg_color=self.colors['bg_chat'],
                text_color=self.colors['accent']
            )
            icon_label.grid(row=0, column=0, sticky="nw", padx=(0, 10), pady=(1, 0))

            # Container pour le message IA
            message_container = self.create_frame(center_frame, fg_color=self.colors['bg_chat'])
            message_container.grid(row=0, column=1, sticky="ew", padx=0, pady=(2, 2))
            message_container.grid_columnconfigure(0, weight=1)

            # Stocker le container pour l'affichage du timestamp
            self.current_message_container = message_container

            # Widget Text vide pour l'animation
            import tkinter as tk
            text_widget = tk.Text(
                message_container,
                width=120,
                bg=self.colors['bg_chat'],
                fg=self.colors['text_primary'],
                font=('Segoe UI', 12),
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
                insertwidth=0
            )
            text_widget.grid(row=0, column=0, padx=0, pady=(0, 0), sticky="nsew")
            self._adjust_widget_height_final(text_widget, "")

            # Bind SEULEMENT pour les touches, pas pour la souris
            def prevent_editing_only(event):
                editing_keys = [
                    'BackSpace', 'Delete', 'Return', 'KP_Enter', 'Tab',
                    'space', 'Insert'
                ]
                if event.state & 0x4:
                    if event.keysym.lower() in ['a', 'c']:
                        return None
                if event.keysym in editing_keys:
                    return "break"
                if len(event.keysym) == 1 and event.keysym.isprintable():
                    return "break"
                return None
            text_widget.bind("<KeyPress>", prevent_editing_only)
            self.setup_improved_scroll_forwarding(text_widget)
            def copy_on_double_click(event):
                try:
                    self.root.clipboard_clear()
                    self.root.clipboard_append(text)
                    self.show_copy_notification("✅ Message copié !")
                except Exception as e:
                    self.show_copy_notification("❌ Erreur de copie")
                return "break"
            text_widget.bind("<Double-Button-1>", copy_on_double_click)
            self.create_copy_menu_with_notification(text_widget, text)

            # Démarrer l'animation de frappe avec hauteur dynamique
            self.start_typing_animation_dynamic(text_widget, text)

    def _scroll_if_needed_user(self):
        """Scroll pour le message utilisateur uniquement si le bas n'est pas visible"""
        try:
            if self.use_ctk and hasattr(self.chat_frame, '_parent_canvas'):
                canvas = self.chat_frame._parent_canvas
                canvas.update_idletasks()
                yview = canvas.yview()
        # Debug removed
                if yview and yview[1] < 1.0:
                    canvas.yview_moveto(1.0)
                    pass
            else:
                parent = self.chat_frame.master
                parent.update_idletasks()
                yview = parent.yview() if hasattr(parent, 'yview') else None
                pass
                if yview and yview[1] < 1.0:
                    parent.yview_moveto(1.0)
                    pass
        except Exception as e:
            pass
    
    def setup_scroll_forwarding(self, text_widget):
        """Configure le transfert du scroll - Version améliorée"""
        def forward_scroll_to_page(event):
            try:
                # Transférer le scroll à la zone de conversation principale
                if hasattr(self, 'chat_frame'):
                    if self.use_ctk and hasattr(self.chat_frame, '_parent_canvas'):
                        # Pour CustomTkinter ScrollableFrame
                        canvas = self.chat_frame._parent_canvas
                        # Transférer l'événement avec la bonne sensibilité
                        scroll_delta = -1 * (event.delta // 120) if event.delta else (-1 if event.num == 4 else 1)
                        canvas.yview_scroll(scroll_delta, "units")
                    else:
                        # Pour tkinter standard
                        parent = self.chat_frame.master
                        while parent and not hasattr(parent, 'yview_scroll'):
                            parent = parent.master
                        if parent:
                            scroll_delta = -1 * (event.delta // 120) if event.delta else (-1 if event.num == 4 else 1)
                            parent.yview_scroll(scroll_delta, "units")
            except Exception as e:
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
        text_widget.bind("<Next>", lambda e: "break")   # Page Down
        text_widget.bind("<Home>", lambda e: "break")
        text_widget.bind("<End>", lambda e: "break")



    def create_user_message_bubble(self, parent, text):
        """Version avec hauteur précise et sélection activée pour les messages utilisateur"""
        from datetime import datetime
        
        if not isinstance(text, str):
            text = str(text)
        
        # Debug removed
        
        # Frame principale
        main_frame = self.create_frame(parent, fg_color=self.colors['bg_chat'])
        main_frame.grid(row=0, column=0, padx=(250, 250), pady=(0, 0), sticky="ew")
        main_frame.grid_columnconfigure(0, weight=0)
        main_frame.grid_columnconfigure(1, weight=1)
        
        # Icône utilisateur
        icon_label = self.create_label(
            main_frame,
            text="👤",
            font=('Segoe UI', 16),
            fg_color=self.colors['bg_chat'],
            text_color=self.colors['text_primary']
        )
        icon_label.grid(row=0, column=0, sticky="nw", padx=(0, 10), pady=(1, 0))
        
        # Bulle utilisateur
        if self.use_ctk:
            bubble = ctk.CTkFrame(main_frame, 
                                fg_color=self.colors['bg_user'], 
                                corner_radius=12,
                                border_width=0)
        else:
            bubble = tk.Frame(main_frame, 
                            bg=self.colors['bg_user'], 
                            relief="flat", 
                            bd=0,
                            highlightthickness=0)
        
        bubble.grid(row=0, column=1, sticky="w", padx=0, pady=(2, 2))
        bubble.grid_columnconfigure(0, weight=0)
        
        # Calcul de hauteur PRÉCISE pour utilisateur
        word_count = len(text.split())
        char_count = len(text)
        line_count = text.count('\n') + 1
        
        # Largeur adaptée
        if word_count > 25:
            text_width = 120
        elif word_count > 10:
            text_width = 90
        elif word_count > 3:
            text_width = 70
        else:
            text_width = max(30, len(text) + 10)

        # Hauteur PRÉCISE : calculée pour éviter tout scroll interne
        chars_per_line = 60
        estimated_lines = max(line_count, (char_count // chars_per_line) + 1)
        precise_height = min(max(estimated_lines, 2), 25)  # min 2, max 25

        text_widget = tk.Text(
            bubble,
            width=text_width,
            height=precise_height,
            bg=self.colors['bg_user'],
            fg='#ffffff',
            font=('Segoe UI', 12),
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
            insertwidth=0
        )

        self.insert_formatted_text_tkinter(text_widget, text)
        # Correction : attendre que le widget soit bien rendu avant d'ajuster la hauteur
        def adjust_height_later():
            self._adjust_widget_height_final(text_widget, text)
        text_widget.after(30, adjust_height_later)

        # Debug removed
        
        # Empêcher l'édition mais permettre la sélection
        def on_key_press(event):
            """Permet les raccourcis de sélection et copie, bloque l'édition"""
            # Autoriser Ctrl+A (tout sélectionner)
            if event.state & 0x4 and event.keysym.lower() == 'a':
                text_widget.tag_add("sel", "1.0", "end")
                return "break"
            
            # Autoriser Ctrl+C (copier)
            elif event.state & 0x4 and event.keysym.lower() == 'c':
                try:
                    selected_text = text_widget.selection_get()
                    if selected_text:
                        self.root.clipboard_clear()
                        self.root.clipboard_append(selected_text)
                        if hasattr(self, 'show_copy_notification'):
                            self.show_copy_notification("📋 Sélection copiée !")
                except tk.TclError:
                    pass
                return "break"
            
            # Autoriser les touches de sélection (Shift + flèches, etc.)
            elif event.keysym in ['Left', 'Right', 'Up', 'Down', 'Home', 'End'] and (event.state & 0x1):
                return None  # Laisser le widget gérer la sélection
            
            # Bloquer toutes les autres touches (édition)
            else:
                return "break"
        
        text_widget.bind("<Key>", on_key_press)
        text_widget.bind("<KeyPress>", on_key_press)
        
        # Configuration du scroll amélioré
        self.setup_improved_scroll_forwarding(text_widget)
        
        # COPIE avec double-clic
        def copy_on_double_click(event):
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
            except Exception as e:
                self.show_copy_notification("❌ Erreur de copie")
            return "break"
        
        text_widget.bind("<Double-Button-1>", copy_on_double_click)
        text_widget.grid(row=0, column=0, padx=8, pady=(6, 0), sticky="nw")
        
        # Timestamp
        timestamp = datetime.now().strftime("%H:%M")
        time_label = self.create_label(
            bubble,
            text=timestamp,
            font=('Segoe UI', 10),
            fg_color=self.colors['bg_user'],
            text_color='#b3b3b3'
        )
        time_label.grid(row=1, column=0, sticky="w", padx=8, pady=(0, 6))
        
        # Menu contextuel amélioré
        def show_context_menu(event):
            try:
                context_menu = tk.Menu(self.root, tearoff=0, bg='#3b82f6', fg='white', 
                                    activebackground='#2563eb', activeforeground='white')
                
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
                        command=lambda: copy_on_double_click(None)
                    )
                    context_menu.add_separator()
                
                context_menu.add_command(
                    label="📄 Copier tout le message", 
                    command=lambda: (
                        self.root.clipboard_clear(),
                        self.root.clipboard_append(text),
                        self.show_copy_notification("📋 Message copié !")
                    )
                )
                
                context_menu.add_command(
                    label="🔍 Tout sélectionner", 
                    command=lambda: text_widget.tag_add("sel", "1.0", "end")
                )
                
                context_menu.tk_popup(event.x_root, event.y_root)
                
            except Exception as e:
                pass
            finally:
                try:
                    context_menu.grab_release()
                except:
                    pass
        
        text_widget.bind("<Button-3>", show_context_menu)  # Clic droit

    def create_ai_message_simple(self, parent, text):
        """Version DÉFINITIVE - Messages IA complets sans AUCUN scroll interne"""
        # Debug removed
        from datetime import datetime
        
        # Vérifier que le texte est une chaîne
        if not isinstance(text, str):
            if isinstance(text, dict):
                text = (text.get('response') or 
                    text.get('text') or 
                    text.get('content') or 
                    text.get('message') or 
                    str(text))
            else:
                text = str(text)
        
        # Frame de centrage
        center_frame = self.create_frame(parent, fg_color=self.colors['bg_chat'])
        center_frame.grid(row=0, column=0, padx=(250, 250), pady=(0, 0), sticky="ew")
        center_frame.grid_columnconfigure(0, weight=0)
        center_frame.grid_columnconfigure(1, weight=1)
        
        # Icône IA
        icon_label = self.create_label(
            center_frame,
            text="🤖",
            font=('Segoe UI', 16),
            fg_color=self.colors['bg_chat'],
            text_color=self.colors['accent']
        )
        icon_label.grid(row=0, column=0, sticky="nw", padx=(0, 10), pady=(1, 0))
        
        # Container pour le message IA
        message_container = self.create_frame(center_frame, fg_color=self.colors['bg_chat'])
        message_container.grid(row=0, column=1, sticky="ew", padx=0, pady=(2, 2))
        message_container.grid_columnconfigure(0, weight=1)
        
        # Stocker le container pour l'affichage du timestamp
        self.current_message_container = message_container
        
        # SOLUTION RADICALE : Widget Text sans hauteur fixe - laisse tkinter décider
        text_widget = tk.Text(
            message_container,
            width=120,
            bg=self.colors['bg_chat'],
            fg=self.colors['text_primary'],
            font=('Segoe UI', 12),
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
            insertwidth=0  # AJOUTÉ
        )

        text_widget.grid(row=0, column=0, padx=0, pady=(0, 0), sticky="nsew")
        # Ajustement final pour garantir aucune barre de scroll interne
        self._adjust_widget_height_final(text_widget, text)
        # Debug removed
        if hasattr(self, 'chat_frame'):
            try:
                parent_widget = self.chat_frame.master
                pass
            except Exception:
                pass
        
        # NOUVELLE APPROCHE : Bind minimal pour permettre la sélection
        def prevent_editing_only(event):
            """Empêche SEULEMENT l'édition, permet tout le reste"""
            # Liste des touches qui modifient le texte
            editing_keys = [
                'BackSpace', 'Delete', 'Return', 'KP_Enter', 'Tab',
                'space', 'Insert'
            ]
            
            # Permettre Ctrl+A et Ctrl+C
            if event.state & 0x4:  # Ctrl est pressé
                if event.keysym.lower() in ['a', 'c']:
                    return None  # Laisser passer
            
            # Bloquer seulement les touches d'édition
            if event.keysym in editing_keys:
                return "break"
            
            # Bloquer la saisie de caractères normaux
            if len(event.keysym) == 1 and event.keysym.isprintable():
                return "break"
            
            # Laisser passer tout le reste (sélection, navigation, etc.)
            return None
        
        # Bind SEULEMENT pour les touches, pas pour la souris
        text_widget.bind("<KeyPress>", prevent_editing_only)
        
        # Configuration du scroll SANS bloquer la sélection
        self.setup_improved_scroll_forwarding(text_widget)
        
        # Fonction de copie
        def copy_on_double_click(event):
            try:
                self.root.clipboard_clear()
                self.root.clipboard_append(text)
                self.show_copy_notification("✅ Message copié !")
            except Exception as e:
                self.show_copy_notification("❌ Erreur de copie")
            return "break"
        
        text_widget.bind("<Double-Button-1>", copy_on_double_click)
        
        # Menu contextuel
        self.create_copy_menu_with_notification(text_widget, text)
        
        # Démarrer l'animation de frappe avec hauteur dynamique
        self.start_typing_animation_dynamic(text_widget, text)

    def setup_improved_scroll_forwarding(self, text_widget):
        """Version CORRIGÉE - Scroll sans conflit avec sélection"""
        
        def smooth_scroll_forward(event):
            """Transfère le scroll vers le container principal"""
            try:
                if hasattr(self, 'chat_frame'):
                    if self.use_ctk and hasattr(self.chat_frame, '_parent_canvas'):
                        canvas = self.chat_frame._parent_canvas
                        if hasattr(event, 'delta') and event.delta:
                            scroll_delta = -1 * (event.delta // 120)
                        elif hasattr(event, 'num'):
                            scroll_delta = -1 if event.num == 4 else 1
                        else:
                            scroll_delta = -1
                        canvas.yview_scroll(scroll_delta, "units")
                    else:
                        parent = self.chat_frame.master
                        while parent and not hasattr(parent, 'yview_scroll'):
                            parent = parent.master
                        if parent and hasattr(parent, 'yview_scroll'):
                            if hasattr(event, 'delta') and event.delta:
                                scroll_delta = -1 * (event.delta // 120)
                            elif hasattr(event, 'num'):
                                scroll_delta = -1 if event.num == 4 else 1
                            else:
                                scroll_delta = -1
                            parent.yview_scroll(scroll_delta, "units")
            except Exception as e:
                print(f"⚠️ Erreur scroll: {e}")
            
            # IMPORTANT : Ne pas retourner "break"
            return None
        
        def handle_focus_events(event):
            """Version CORRIGÉE sans erreur state"""
            try:
                # Transférer le focus vers l'input principal
                if hasattr(self, 'input_text'):
                    try:
                        if self.input_text.winfo_exists():
                            self.input_text.focus_set()
                    except:
                        pass
            except:
                pass
            return None
        
        # Bind des événements de scroll
        text_widget.bind("<MouseWheel>", smooth_scroll_forward)
        text_widget.bind("<Button-4>", smooth_scroll_forward)
        text_widget.bind("<Button-5>", smooth_scroll_forward)
        
        # Bind du focus CORRIGÉ
        text_widget.bind("<FocusIn>", handle_focus_events)
        
        # Configuration du widget SANS insertwidth=0 qui peut causer des problèmes
        text_widget.configure(
            takefocus=False,
            wrap=tk.WORD
        )
        
        print(f"✅ Scroll amélioré configuré pour widget Text")

    def start_typing_animation_dynamic(self, text_widget, full_text):
        """Animation avec désactivation de la saisie"""
        # DÉSACTIVER la saisie pendant l'animation
        # Debug removed
        self.set_input_state(False)
        
        # Réinitialiser le widget
        text_widget.configure(state="normal")
        text_widget.delete("1.0", "end")
        
        # Variables pour l'animation
        self.typing_index = 0
        self.typing_text = full_text
        self.typing_widget = text_widget
        self.typing_speed = 3
        
        # Configurer tous les tags de formatage
        self._configure_formatting_tags(text_widget)

        # Flag d'interruption
        self._typing_interrupted = False
        
        # Debug removed
        # Démarrer l'animation
        self.continue_typing_animation_dynamic()

    def continue_typing_animation_dynamic(self):
        """Animation AVEC scroll automatique qui suit l'écriture"""
        idx = getattr(self, 'typing_index', None)
        if idx == 0:
            pass
        elif idx is not None and idx % 100 == 0:
            pass

        # SÉCURITÉ : aucun set_input_state(True) ne doit être appelé ici !
        # Si jamais cela arrive, on logue une erreur (détection de bug/régression)
        # (AUCUN set_input_state(True) dans cette fonction !)

        if not hasattr(self, 'typing_widget') or not hasattr(self, 'typing_text'):
            return
            return

        if getattr(self, '_typing_interrupted', False):
            # Debug removed
            self.finish_typing_animation_dynamic(interrupted=True)
            return

        if self.typing_index < len(self.typing_text):
            current_text = self.typing_text[:self.typing_index + 1]

            # Insérer le texte avec formatage
            self.typing_widget.configure(state="normal")
            self.typing_widget.delete("1.0", "end")
            self._insert_formatted_text_progressive(self.typing_widget, current_text)

            # Ajustement dynamique de la hauteur à CHAQUE étape
            self._adjust_widget_height_dynamically(self.typing_widget)
            # Scroll pendant l'animation uniquement si le bas n'est pas visible
            if hasattr(self, 'chat_frame') and self.typing_index % 10 == 0:
                try:
                    if self.use_ctk and hasattr(self.chat_frame, '_parent_canvas'):
                        canvas = self.chat_frame._parent_canvas
                        yview = canvas.yview()
                        widget_bottom = self.typing_widget.winfo_rooty() + self.typing_widget.winfo_height()
                        container_bottom = canvas.winfo_rooty() + canvas.winfo_height()
                        if widget_bottom > container_bottom or (yview and yview[1] < 1.0):
                            self.root.after(1, self._gentle_scroll_to_bottom)
                    else:
                        parent = self.chat_frame.master
                        yview = parent.yview() if hasattr(parent, 'yview') else None
                        widget_bottom = self.typing_widget.winfo_rooty() + self.typing_widget.winfo_height()
                        container_bottom = parent.winfo_rooty() + parent.winfo_height()
                        if widget_bottom > container_bottom or (yview and yview[1] < 1.0):
                            self.root.after(1, self._gentle_scroll_to_bottom)
                except Exception as e:
                    pass

            self.typing_index += 1

            # Programmer le caractère suivant
            self._typing_animation_after_id = self.root.after(self.typing_speed, self.continue_typing_animation_dynamic)
        else:
            # Debug removed
            self.finish_typing_animation_dynamic()

    def _gentle_scroll_to_bottom(self):
        """Scroll doux pendant l'animation sans clignotement, avec debug détaillé"""
        try:
            if self.use_ctk:
                if hasattr(self, 'chat_frame') and hasattr(self.chat_frame, '_parent_canvas'):
                    canvas = self.chat_frame._parent_canvas
                    yview = canvas.yview()
                    pass
                    canvas.yview_moveto(1.0)
                    pass
            else:
                parent = self.chat_frame.master
                yview = parent.yview() if hasattr(parent, 'yview') else None
                pass
                if hasattr(parent, 'yview_moveto'):
                    parent.yview_moveto(1.0)
                pass
        except Exception as e:
            pass

    def _adjust_widget_height_dynamically(self, text_widget):
        """Ajustement dynamique PRÉCIS pendant l'animation"""
        try:
            text_widget.update_idletasks()
            # Récupérer le texte actuellement affiché
            current_text = text_widget.get("1.0", "end-1c")
            lines = current_text.split('\n')
            total_lines = 0
            widget_width = text_widget.winfo_width()
            font = text_widget.cget('font')
            char_width = 7.2
            try:
                import tkinter.font as tkfont
                f = tkfont.Font(font=font)
                char_width = f.measure('n')
                if char_width < 5: char_width = 7.2
            except Exception:
                pass
            chars_per_line = max(10, int(widget_width // char_width))
            for l in lines:
                wrapped = max(1, int((len(l) + chars_per_line - 1) // chars_per_line))
                total_lines += wrapped
            new_height = max(2, total_lines + 1)
            # Limiter pour éviter les bulles énormes pendant l'animation
            new_height = min(new_height, 50)
            text_widget.configure(height=new_height)
        except Exception as e:
            print(f"⚠️ Erreur ajustement dynamique: {e}")

    def finish_typing_animation_dynamic(self, interrupted=False):
        """Version FINALE avec scroll qui marche, support interruption"""
        # Debug removed
        if hasattr(self, 'typing_widget') and hasattr(self, 'typing_text'):
            # Debug removed
            self.typing_widget.configure(state="normal")
            self.typing_widget.delete("1.0", "end")
            if interrupted:
                # Affiche le texte à l'endroit où on a stoppé
                partial_text = self.typing_text[:self.typing_index]
                self.insert_formatted_text_tkinter(self.typing_widget, partial_text)
            else:
                self.insert_formatted_text_tkinter(self.typing_widget, self.typing_text)
            # Ajustement final de la hauteur
            self._adjust_widget_height_final(self.typing_widget, self.typing_text)
            # GARDER en state="normal" pour la sélection
            self.typing_widget.configure(state="normal")
            # Afficher le timestamp à l'arrêt de l'animation (même si interrompu)
            self._show_timestamp_for_current_message()
            # RÉACTIVER la saisie utilisateur
            self.set_input_state(True)
            # Scroll final AMÉLIORÉ avec délais progressifs
            self.root.after(100, self.scroll_to_bottom_smooth)
            self.root.after(300, self.scroll_to_bottom_smooth)  # Double scroll pour sécurité
            # Nettoyer les variables
            if hasattr(self, '_typing_animation_after_id'):
                try:
                    self.root.after_cancel(self._typing_animation_after_id)
                except Exception:
                    pass
                del self._typing_animation_after_id
            delattr(self, 'typing_widget')
            delattr(self, 'typing_text')
            delattr(self, 'typing_index')
            self._typing_interrupted = False

    def stop_typing_animation(self):
        """Stoppe proprement l'animation de frappe IA (interruption utilisateur)"""
        self._typing_interrupted = True
        if hasattr(self, '_typing_animation_after_id'):
            try:
                self.root.after_cancel(self._typing_animation_after_id)
            except Exception:
                pass
            del self._typing_animation_after_id

    def scroll_to_bottom_smooth(self):
        """Scroll vers le bas en douceur, sans clignotement"""
        # Debug removed
        try:
            # Une seule mise à jour, puis scroll
            self.root.update_idletasks()
            
            if self.use_ctk:
                if hasattr(self, 'chat_frame'):
                    parent = self.chat_frame.master
                    while parent and not hasattr(parent, 'yview_moveto'):
                        parent = parent.master
                    
                    if parent and hasattr(parent, 'yview_moveto'):
                        parent.yview_moveto(1.0)
            else:
                parent = self.chat_frame.master
                if hasattr(parent, 'yview_moveto'):
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
            except Exception as e:
                self.show_copy_notification("❌ Erreur de copie")
        
        # Menu contextuel amélioré
        def show_context_menu(event):
            context_menu = tk.Menu(self.root, tearoff=0)
            
            # Vérifier s'il y a une sélection
            try:
                selected = text_widget.selection_get()
                if selected:
                    context_menu.add_command(label="📋 Copier la sélection", command=copy_selected_text)
                    context_menu.add_separator()
            except:
                pass
            
            context_menu.add_command(label="📄 Copier tout le message", command=copy_selected_text)
            context_menu.add_command(label="🔍 Tout sélectionner", command=lambda: text_widget.tag_add("sel", "1.0", "end"))
            
            try:
                context_menu.tk_popup(event.x_root, event.y_root)
            except:
                pass
            finally:
                context_menu.grab_release()
        
        # Binds pour la copie
        text_widget.bind("<Button-3>", show_context_menu)  # Clic droit
        text_widget.bind("<Control-c>", lambda e: copy_selected_text())  # Ctrl+C
        text_widget.bind("<Control-a>", lambda e: text_widget.tag_add("sel", "1.0", "end"))  # Ctrl+A

    def is_animation_running(self):
        """Vérifie si une animation d'écriture est en cours"""
        return (hasattr(self, 'typing_widget') and 
                hasattr(self, 'typing_text') and 
                hasattr(self, 'typing_index'))

    def _adjust_widget_height_final(self, text_widget, full_text):
        """Ajustement dynamique parfait : hauteur adaptée au texte et à la largeur réelle du widget (padx inclus), sans scroll interne ni espace vide. Correction spéciale pour les bulles user (largeur à 1px au début)."""
        import math, time
        try:
            # Forcer le rendu complet du widget (pour bulles user)
            for i in range(10):
                text_widget.update_idletasks()
                widget_width = text_widget.winfo_width()
                if widget_width > 50:
                    break
                if hasattr(self, 'root'):
                    self.root.update_idletasks()
                time.sleep(0.01)
            else:
                # Fallback si la largeur reste anormale
                widget_width = 400
            # Largeur moyenne d'un caractère (en pixels)
            font = text_widget.cget('font')
            char_width = 7.2
            try:
                import tkinter.font as tkfont
                f = tkfont.Font(font=font)
                char_width = f.measure('n')
                if char_width < 5: char_width = 7.2
            except Exception:
                pass
            chars_per_line = max(10, int(widget_width // char_width))
            lines = full_text.split('\n')
            total_lines = 0
            for l in lines:
                wrapped = max(1, math.ceil(len(l) / chars_per_line))
                total_lines += wrapped
            height = total_lines + 1
            text_widget.configure(height=height)
            text_widget.update_idletasks()
            for j in range(20):
                yview = text_widget.yview()
                if yview[1] >= 1.0:
                    break
                height += 1
                text_widget.configure(height=height)
                text_widget.update_idletasks()
        except Exception:
            text_widget.configure(height=7)

    def _configure_formatting_tags(self, text_widget):
        """Configure tous les tags de formatage avant l'animation"""
        # Tags pour le formatage markdown
        text_widget.tag_configure("bold", font=('Segoe UI', 12, 'bold'))
        text_widget.tag_configure("italic", font=('Segoe UI', 12, 'italic'))
        text_widget.tag_configure("mono", font=('Consolas', 11), foreground="#f8f8f2")
        text_widget.tag_configure("normal", font=('Segoe UI', 12))
        
        # Tags pour la coloration Python
        text_widget.tag_configure("python_keyword", foreground="#ff79c6", font=('Consolas', 11, 'bold'))
        text_widget.tag_configure("python_string", foreground="#f1fa8c", font=('Consolas', 11))
        text_widget.tag_configure("python_comment", foreground="#6272a4", font=('Consolas', 11, 'italic'))
        text_widget.tag_configure("python_number", foreground="#bd93f9", font=('Consolas', 11))
        text_widget.tag_configure("python_builtin", foreground="#8be9fd", font=('Consolas', 11))


    def _insert_formatted_text_progressive(self, text_widget, text):
        """Insère le texte avec formatage progressif (version simplifiée pour l'animation)"""
        import re
        
        # Traitement simplifié pour l'animation - pas de blocs de code complexes
        # Remplacer les marqueurs markdown basiques
        formatted_text = text
        
        # Traiter le gras **texte**
        def replace_bold(match):
            return match.group(1)  # Retourner juste le texte sans les **
        
        # Traiter l'italique *texte*
        def replace_italic(match):
            return match.group(1)  # Retourner juste le texte sans les *
        
        # Pour l'animation, on affiche le texte sans les marqueurs mais on garde le formatage
        current_pos = 0
        
        # Traitement du gras **texte**
        for match in re.finditer(r'\*\*([^*]+)\*\*', text):
            # Texte avant
            if match.start() > current_pos:
                text_widget.insert("end", text[current_pos:match.start()], "normal")
            
            # Texte en gras
            text_widget.insert("end", match.group(1), "bold")
            current_pos = match.end()
        
        # Reste du texte
        if current_pos < len(text):
            remaining_text = text[current_pos:]
            
            # Traitement de l'italique dans le reste
            italic_pos = 0
            for italic_match in re.finditer(r'\*([^*]+)\*', remaining_text):
                if italic_match.start() > italic_pos:
                    text_widget.insert("end", remaining_text[italic_pos:italic_match.start()], "normal")
                text_widget.insert("end", italic_match.group(1), "italic")
                italic_pos = italic_match.end()
            
            if italic_pos < len(remaining_text):
                text_widget.insert("end", remaining_text[italic_pos:], "normal")


    def _show_timestamp_for_current_message(self):
        """Affiche le timestamp pour le message actuel"""
        from datetime import datetime
        
        # Trouver le dernier message container
        if hasattr(self, 'current_message_container'):
            timestamp = datetime.now().strftime("%H:%M")
            time_label = self.create_label(
                self.current_message_container,
                text=timestamp,
                font=('Segoe UI', 10),
                fg_color=self.colors['bg_chat'],
                text_color=self.colors['text_secondary']
            )
            time_label.grid(row=1, column=0, sticky="w", padx=0, pady=(2, 6))

    def _calculate_text_lines(self, text, chars_per_line=120):
        """Version finale sans limite"""
        return self._calculate_text_lines_unlimited(text)
    
    def _calculate_text_lines_unlimited(self, text):
        """Calcul de hauteur EXACT - Méthode corrigée pour éviter les bulles avec scroll"""
        if not text:
            return 2
        
        # Compter les vraies lignes
        lines = text.split('\n')
        content_lines = len([line for line in lines if line.strip()])
        
        # Estimation du wrapping avec une approche plus conservatrice
        total_chars = len(text.replace('\n', ' '))
        chars_per_line = 120  # Largeur de référence
        wrapped_lines = max(content_lines, (total_chars + chars_per_line - 1) // chars_per_line)
        
        # CORRECTION MAJEURE : Calcul plus généreux pour éviter le scroll dans les bulles
        # Au lieu de 1.05, utiliser 1.25 pour avoir plus de marge
        safety_margin = max(3, int(wrapped_lines * 0.25))  # 25% de marge minimum 3
        final_lines = wrapped_lines + safety_margin
        
        # Pour les longs messages, être encore plus généreux
        if len(text) > 2000:
            final_lines = int(final_lines * 1.3)
        elif len(text) > 1000:
            final_lines = int(final_lines * 1.2)
        
        # Minimum raisonnable
        result = max(5, final_lines)
        
        print(f"📏 CALCUL GÉNÉREUX: {len(text)} chars → {content_lines} lignes → {wrapped_lines} wrapped → {result} final (marge: {safety_margin})")
        
        return result

    def show_copy_notification(self, message):
        """Affiche une notification GUI élégante pour la copie"""
        try:
            # Créer une notification temporaire
            if self.use_ctk:
                notification = ctk.CTkFrame(
                    self.main_container,
                    fg_color="#10b981",  # Vert succès
                    corner_radius=8,
                    border_width=0
                )
                
                notif_label = ctk.CTkLabel(
                    notification,
                    text=message,
                    text_color="#ffffff",
                    font=('Segoe UI', 12, 'bold')
                )
            else:
                notification = tk.Frame(
                    self.main_container,
                    bg="#10b981",
                    relief="flat"
                )
                
                notif_label = tk.Label(
                    notification,
                    text=message,
                    fg="#ffffff",
                    bg="#10b981",
                    font=('Segoe UI', 12, 'bold')
                )
            
            notif_label.pack(padx=15, pady=8)
            
            # Positionner en haut à droite
            notification.place(relx=0.95, rely=0.1, anchor="ne")
            
            # Supprimer automatiquement après 2 secondes
            self.root.after(2000, notification.destroy)
            
        except Exception as e:
            pass


    def create_copy_menu_with_notification(self, widget, original_text):
        """Menu contextuel avec notification GUI"""
        def copy_text():
            try:
                self.root.clipboard_clear()
                self.root.clipboard_append(original_text)
                self.show_copy_notification("Texte copié !")
            except Exception as e:
                self.show_copy_notification("❌ Erreur de copie")
        
        # Menu contextuel
        context_menu = tk.Menu(self.root, tearoff=0)
        context_menu.add_command(label="📋 Copier", command=copy_text)

        def select_all_and_copy():
            """Sélectionne tout le texte et le copie"""
            copy_text()  # Pour l'instant, même action
            
            # Créer le menu contextuel
            if self.use_ctk:
                # Pour CustomTkinter, utiliser un menu tkinter standard
                context_menu = tk.Menu(self.root, tearoff=0)
            else:
                context_menu = tk.Menu(self.root, tearoff=0)
            
                context_menu.add_command(label="📋 Copier le texte", command=copy_text)
                context_menu.add_separator()
                context_menu.add_command(label="🔍 Tout sélectionner et copier", command=select_all_and_copy)
            
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
            
            # Pour CustomTkinter, essayer aussi Control+clic
            widget.bind("<Control-Button-1>", show_context_menu)
        
            return context_menu
        
        def show_context_menu(event):
            try:
                context_menu.tk_popup(event.x_root, event.y_root)
            except:
                pass
            finally:
                context_menu.grab_release()
        
        widget.bind("<Button-3>", show_context_menu)  # Clic droit
        widget.bind("<Control-Button-1>", show_context_menu)  # Ctrl+clic
        
        return context_menu

    def insert_formatted_text_tkinter(self, text_widget, text):
        """Version CORRIGÉE avec les bonnes couleurs Pygments"""
        import re
        import webbrowser
        text_widget.delete("1.0", "end")

        # Configuration des couleurs CORRIGÉES pour thème sombre
        BASE_FONT = ('Segoe UI', 12)
        text_widget.tag_configure("bold", font=('Segoe UI', 12, 'bold'))
        text_widget.tag_configure("italic", font=('Segoe UI', 12, 'italic'))
        text_widget.tag_configure("mono", font=('Consolas', 11), foreground="#f8f8f2")
        text_widget.tag_configure("normal", font=BASE_FONT)
        text_widget.tag_configure("link", foreground="#3b82f6", underline=1, font=BASE_FONT)
        
        # CORRECTION MAJEURE : Configuration précise des couleurs Pygments
        # Mots-clés (def, class, if, for, etc.)
        text_widget.tag_configure("Token.Keyword", foreground="#ff79c6", font=('Consolas', 11, 'bold'))
        text_widget.tag_configure("Token.Keyword.Constant", foreground="#ff79c6", font=('Consolas', 11, 'bold'))
        text_widget.tag_configure("Token.Keyword.Declaration", foreground="#ff79c6", font=('Consolas', 11, 'bold'))
        text_widget.tag_configure("Token.Keyword.Namespace", foreground="#ff79c6", font=('Consolas', 11, 'bold'))
        text_widget.tag_configure("Token.Keyword.Pseudo", foreground="#ff79c6", font=('Consolas', 11, 'bold'))
        text_widget.tag_configure("Token.Keyword.Reserved", foreground="#ff79c6", font=('Consolas', 11, 'bold'))
        text_widget.tag_configure("Token.Keyword.Type", foreground="#8be9fd", font=('Consolas', 11, 'bold'))
        
        # Strings (entre guillemets)
        text_widget.tag_configure("Token.Literal.String", foreground="#f1fa8c", font=('Consolas', 11))
        text_widget.tag_configure("Token.Literal.String.Double", foreground="#f1fa8c", font=('Consolas', 11))
        text_widget.tag_configure("Token.Literal.String.Single", foreground="#f1fa8c", font=('Consolas', 11))
        text_widget.tag_configure("Token.String", foreground="#f1fa8c", font=('Consolas', 11))
        text_widget.tag_configure("Token.String.Double", foreground="#f1fa8c", font=('Consolas', 11))
        text_widget.tag_configure("Token.String.Single", foreground="#f1fa8c", font=('Consolas', 11))
        
        # Commentaires
        text_widget.tag_configure("Token.Comment", foreground="#6272a4", font=('Consolas', 11, 'italic'))
        text_widget.tag_configure("Token.Comment.Single", foreground="#6272a4", font=('Consolas', 11, 'italic'))
        text_widget.tag_configure("Token.Comment.Multiline", foreground="#6272a4", font=('Consolas', 11, 'italic'))
        
        # Fonctions et méthodes
        text_widget.tag_configure("Token.Name.Function", foreground="#50fa7b", font=('Consolas', 11))
        text_widget.tag_configure("Token.Name.Class", foreground="#50fa7b", font=('Consolas', 11, 'bold'))
        
        # Builtins (print, len, etc.)
        text_widget.tag_configure("Token.Name.Builtin", foreground="#8be9fd", font=('Consolas', 11))
        text_widget.tag_configure("Token.Name.Builtin.Pseudo", foreground="#8be9fd", font=('Consolas', 11))
        
        # Nombres
        text_widget.tag_configure("Token.Literal.Number", foreground="#bd93f9", font=('Consolas', 11))
        text_widget.tag_configure("Token.Literal.Number.Integer", foreground="#bd93f9", font=('Consolas', 11))
        text_widget.tag_configure("Token.Literal.Number.Float", foreground="#bd93f9", font=('Consolas', 11))
        text_widget.tag_configure("Token.Number", foreground="#bd93f9", font=('Consolas', 11))
        text_widget.tag_configure("Token.Number.Integer", foreground="#bd93f9", font=('Consolas', 11))
        text_widget.tag_configure("Token.Number.Float", foreground="#bd93f9", font=('Consolas', 11))
        
        # Opérateurs
        text_widget.tag_configure("Token.Operator", foreground="#ff79c6", font=('Consolas', 11))
        text_widget.tag_configure("Token.Punctuation", foreground="#f8f8f2", font=('Consolas', 11))
        
        # Variables et noms
        text_widget.tag_configure("Token.Name", foreground="#f8f8f2", font=('Consolas', 11))
        text_widget.tag_configure("Token.Name.Variable", foreground="#f8f8f2", font=('Consolas', 11))
        
        # Valeurs spéciales (True, False, None)
        text_widget.tag_configure("Token.Name.Constant", foreground="#bd93f9", font=('Consolas', 11, 'bold'))
        text_widget.tag_configure("Token.Keyword.Constant", foreground="#bd93f9", font=('Consolas', 11, 'bold'))

        def open_link(event, url):
            webbrowser.open_new(url)

        # Traitement du texte avec blocs de code
        code_block_pattern = r"```python\s*([\s\S]+?)```"
        pos = 0
        for code_match in re.finditer(code_block_pattern, text, re.IGNORECASE):
            # Texte avant le bloc code
            if code_match.start() > pos:
                self._insert_markdown_and_links(text_widget, text[pos:code_match.start()])
            code_content = code_match.group(1)
            self._insert_python_code_block_corrected(text_widget, code_content)
            pos = code_match.end()
        # Texte après le dernier bloc code
        if pos < len(text):
            self._insert_markdown_and_links(text_widget, text[pos:])

        text_widget.update_idletasks()
        text_widget.see("1.0")

    def _insert_python_code_block_corrected(self, text_widget, code):
        """Version CORRIGÉE de l'insertion de code Python avec Pygments"""
        try:
            from pygments import lex
            from pygments.lexers import PythonLexer
            
            code = code.strip('\n')
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
        import keyword
        import re
        
        code = code.strip('\n')
        lines = code.split('\n')
        
        for line in lines:
            # Pattern plus précis pour tokeniser
            pattern = r'(#.*$|"""[\s\S]*?"""|\'\'\'[\s\S]*?\'\'\'|"[^"]*"|\'[^\']*\'|\b\d+\.?\d*\b|\b\w+\b|[^\w\s]|\s+)'
            tokens = re.findall(pattern, line)
            
            for token in tokens:
                if not token:
                    continue
                elif token.startswith('#'):
                    text_widget.insert("end", token, ("Token.Comment",))
                elif token.startswith(('"""', "'''")):
                    text_widget.insert("end", token, ("Token.String",))
                elif token.startswith(('"', "'")):
                    text_widget.insert("end", token, ("Token.String",))
                elif token in keyword.kwlist:
                    text_widget.insert("end", token, ("Token.Keyword",))
                elif token in ['True', 'False', 'None']:
                    text_widget.insert("end", token, ("Token.Keyword.Constant",))
                elif token in ['print', 'len', 'str', 'int', 'float', 'list', 'dict', 'set', 'tuple', 'range', 'enumerate', 'zip', 'append', 'insert', 'remove']:
                    text_widget.insert("end", token, ("Token.Name.Builtin",))
                elif re.match(r'^\d+\.?\d*$', token):
                    text_widget.insert("end", token, ("Token.Number",))
                elif token in ['=', '+', '-', '*', '/', '//', '%', '**', '==', '!=', '<', '>', '<=', '>=']:
                    text_widget.insert("end", token, ("Token.Operator",))
                elif token.isspace():
                    text_widget.insert("end", token, ("mono",))
                else:
                    text_widget.insert("end", token, ("Token.Name",))
            
            text_widget.insert("end", "\n", ("mono",))

    def _insert_markdown_and_links(self, text_widget, text):
        """Insère du texte avec gestion des liens Markdown et du markdown classique (gras, italique, etc.)"""
        import re
        import webbrowser
        link_pattern = r'\[([^\]]+)\]\(([^)]+)\)'
        last_end = 0
        for match in re.finditer(link_pattern, text):
            if match.start() > last_end:
                self._insert_markdown_segments(text_widget, text[last_end:match.start()])
            link_text = match.group(1)
            url = match.group(2)
            start_index = text_widget.index("end-1c")
            text_widget.insert("end", link_text, ("link",))
            end_index = text_widget.index("end-1c")
            text_widget.tag_add(f"link_{start_index}", start_index, end_index)
            text_widget.tag_bind(f"link_{start_index}", "<Button-1>", lambda e, url=url: webbrowser.open_new(url))
            last_end = match.end()
        if last_end < len(text):
            self._insert_markdown_segments(text_widget, text[last_end:])

    def _insert_python_code_block(self, text_widget, code):
        """Insère un bloc de code python avec coloration syntaxique simple"""
        # Utilise Pygments pour une coloration réaliste
        try:
            from pygments import lex
            from pygments.lexers import PythonLexer
            code = code.strip('\n')
            for token, value in lex(code, PythonLexer()):
                tag = str(token)
                text_widget.insert("end", value, (tag,))
            text_widget.insert("end", "\n", ("mono",))
        except Exception:
            # Fallback simple
            import keyword, re
            code = code.strip('\n')
            lines = code.split('\n')
            for i, line in enumerate(lines):
                tokens = re.split(r'(\s+|#.*|"[^"]*"|\'[^"]*\'|\b\w+\b)', line)
                for token in tokens:
                    if not token:
                        continue
                    if token.startswith('#'):
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

    def _insert_markdown_segments(self, text_widget, text):
        """Insère du texte avec gras, italique, monospace (hors liens)"""
        import re
        patterns = [
            (r'\*\*([^*]+)\*\*', 'bold'),   # **texte** -> gras
            (r'\*([^*]+)\*', 'italic'),     # *texte* -> italique
            (r'`([^`]+)`', 'mono')          # `texte` -> monospace
        ]
        segments = [(text, 'normal')]
        for pattern, style in patterns:
            new_segments = []
            for segment_text, segment_style in segments:
                if segment_style == 'normal':
                    pos = 0
                    for match in re.finditer(pattern, segment_text):
                        if match.start() > pos:
                            new_segments.append((segment_text[pos:match.start()], 'normal'))
                        new_segments.append((match.group(1), style))
                        pos = match.end()
                    if pos < len(segment_text):
                        new_segments.append((segment_text[pos:], 'normal'))
                else:
                    new_segments.append((segment_text, segment_style))
            segments = new_segments
        for segment_text, style in segments:
            if segment_text:
                text_widget.insert("end", segment_text, style)

    def adjust_text_height_no_scroll(self, text_widget, text):
        """Ajuste la hauteur EXACTE pour afficher tout le contenu sans scroll"""
        try:
            # Attendre que le widget soit rendu
            text_widget.update_idletasks()
            
            if self.use_ctk:
                # Pour CustomTkinter CTkTextbox - CALCUL TRÈS PRÉCIS
                lines = text.split('\n')
                total_lines = 0
                
                # Obtenir la largeur réelle du widget
                try:
                    widget_width = text_widget.winfo_width()
                    if widget_width <= 50:
                        widget_width = 400  # Largeur par défaut
                    
                    # Estimation caractères par ligne TRÈS précise
                    font_size = self.get_current_font_size('message')
                    char_width = font_size * 0.6  # Approximation largeur caractère
                    chars_per_line = max(30, int((widget_width - 30) / char_width))
                    
                    for line in lines:
                        if len(line) == 0:
                            total_lines += 1
                        else:
                            # Calculer lignes wrapped précisément
                            line_wrapped = max(1, (len(line) + chars_per_line - 1) // chars_per_line)
                            total_lines += line_wrapped
                            
                except Exception:
                    # Fallback conservateur
                    total_lines = len(lines) + 3  # Plus conservateur
                
                # Calculer hauteur COMPACTE en pixels
                line_height = 18   # Hauteur d'une ligne (plus compact)
                padding = 8        # Padding minimal (plus compact)
                min_height = 30    # Minimum absolu (plus compact)
                max_height = 600   # Maximum raisonnable (plus grand)
                
                exact_height = max(min_height, min(total_lines * line_height + padding, max_height))
                
                # MARGE DE SÉCURITÉ pour éviter tout scroll
                exact_height = int(exact_height * 1.1)  # 10% de marge (réduit)
                text_widget.configure(height=exact_height)
                
            else:
                # Pour tkinter standard Text - CALCUL EN LIGNES
                current_state = text_widget.cget("state")
                text_widget.configure(state="normal")
                
                # Forcer le rendu puis mesurer
                text_widget.see("end")
                text_widget.update_idletasks()
                
                # Compter lignes réelles affichées
                line_count = int(text_widget.index("end-1c").split('.')[0])
                
                # Restaurer l'état
                text_widget.configure(state=current_state)
                
                # Hauteur GÉNÉREUSE - plus de marge pour éviter scroll
                exact_height = max(2, min(line_count + 3, 30))  # +3 de marge au lieu de 0
                text_widget.configure(height=exact_height)
                
            # Forcer la mise à jour
            text_widget.update_idletasks()
            
        except Exception as e:
            self.logger.error(f"Erreur ajustement hauteur: {e}")
            # Hauteur par défaut GÉNÉREUSE si erreur
            if self.use_ctk:
                text_widget.configure(height=80)  # Plus généreux
            else:
                text_widget.configure(height=5)   # Plus généreux
                
        except Exception as e:
            self.logger.error(f"Erreur ajustement hauteur: {e}")
            # Hauteur généreuse par défaut en cas d'erreur
            if self.use_ctk:
                text_widget.configure(height=120)
            else:
                text_widget.configure(height=6)

    def create_copy_menu(self, widget, original_text):
        """
        Crée un menu contextuel pour copier le texte d'un widget
        """
        try:
            # Scroll le chat_frame pour que le bas du dernier message soit visible, sans overshoot
            if hasattr(self, 'chat_frame'):
                self.chat_frame.update_idletasks()
                if hasattr(self.chat_frame, 'yview'):
                    yview = self.chat_frame.yview()
                    # Scroll uniquement si le bas n'est pas visible
                    if yview[1] < 0.99:
                        if hasattr(self.chat_frame, 'yview_moveto'):
                            self.chat_frame.yview_moveto(1.0)
            pass
        except Exception as e:
            print(f"⚠️ Erreur scroll doux: {e}")
    
    def get_current_font_size(self, font_type='message'):
        """NOUVELLE VERSION - Taille de police unifiée pour tous les messages"""
        # Cette fonction retourne la taille de police pour chaque type
        # UNIFICATION TOTALE : tous les contenus de messages utilisent la même taille
        message_types = ['message', 'body', 'chat', 'bold', 'small', 'content']
        if font_type in message_types:
            return 12  # TAILLE UNIFIÉE POUR TOUS LES MESSAGES (réduite de 1)
        
        # Seuls les éléments d'interface gardent leurs tailles spécifiques
        interface_font_sizes = {
            'timestamp': 10,    # Timestamps un peu plus petits
            'icon': 16,         # Icônes (🤖, 👤)
            'header': 20,       # Éléments d'en-tête
            'status': 12,       # Indicateurs de statut
            'title': 32,        # Titres principaux
            'subtitle': 18,     # Sous-titres
        }
        
        return interface_font_sizes.get(font_type, 12)
    
    def insert_formatted_text_ctk(self, text_widget, text):
        """Insère du texte formaté avec rendu visuel subtil dans CustomTkinter TextBox"""
        # Cette fonction insère le texte formaté dans le widget CTk
        import re
        
        # Pour CustomTkinter, on utilise un rendu subtil quand le formatage tkinter n'est pas possible
        
        if not ('**' in text or '*' in text or '`' in text):
            # Pas de formatage : insérer directement
            text_widget.delete("1.0", "end")
            text_widget.insert("end", text)
            return
        
        # Traitement du formatage avec rendu subtil
        text_widget.delete("1.0", "end")
        
        # Patterns pour détecter **gras**, *italique*, `monospace`
        patterns = [
            (r'\*\*([^*]+)\*\*', 'bold'),     # **texte** -> gras
            (r'\*([^*]+)\*', 'italic'),       # *texte* -> italique  
            (r'`([^`]+)`', 'mono')            # `texte` -> monospace
        ]
        
        # Traitement séquentiel du texte
        segments = [(text, 'normal')]
        
        for pattern, style in patterns:
            new_segments = []
            for segment_text, segment_style in segments:
                if segment_style == 'normal':
                    # Diviser ce segment selon le pattern
                    pos = 0
                    for match in re.finditer(pattern, segment_text):
                        # Ajouter le texte avant le match
                        if match.start() > pos:
                            new_segments.append((segment_text[pos:match.start()], 'normal'))
                        # Ajouter le texte formaté
                        new_segments.append((match.group(1), style))
                        pos = match.end()
                    # Ajouter le reste
                    if pos < len(segment_text):
                        new_segments.append((segment_text[pos:], 'normal'))
                else:
                    # Garder les segments déjà formatés
                    new_segments.append((segment_text, segment_style))
            segments = new_segments
        
        # Insérer les segments avec un rendu visuel subtil mais lisible
        for segment_text, style in segments:
            if style == 'bold':
                # Gras : ajouter des espaces pour créer de l'emphase visuelle
                text_widget.insert("end", f" {segment_text} ")
            elif style == 'italic':
                # Italique : utiliser des guillemets pour l'emphase
                text_widget.insert("end", f'"{segment_text}"')
            elif style == 'mono':
                # Code : utiliser backticks pour le style code
                text_widget.insert("end", f"`{segment_text}`")
            else:
                text_widget.insert("end", segment_text)           # Texte normal
    
    def insert_formatted_text(self, text_widget, text):
        """Insère du texte formaté dans un widget tkinter standard avec support du gras"""
        import re
        
        text_widget.delete("1.0", "end")
        
        # Configurer les tags de formatage
        current_font_size = self.get_current_font_size('message')
        text_widget.tag_configure("bold", font=('Segoe UI', current_font_size, 'bold'))
        text_widget.tag_configure("normal", font=('Segoe UI', current_font_size))
        
        # Pattern pour détecter **texte en gras**
        pattern = r'\*\*([^*]+)\*\*'
        parts = re.split(pattern, text)
        
        for i, part in enumerate(parts):
            if i % 2 == 0:  # Texte normal
                if part:
                    text_widget.insert("end", part, "normal")
            else:  # Texte en gras
                if part:
                    text_widget.insert("end", part, "bold")
    
    def hide_status_indicators(self):
        """Cache tous les indicateurs de statut et réactive la saisie"""
        # Arrêter les animations
        self.is_thinking = False
        self.is_searching = False
        
        # NOUVEAU : Réactiver la zone de saisie
        # Correction : ne réactive l'input que si aucune animation IA n'est en cours
        if hasattr(self, 'is_animation_running') and self.is_animation_running():
            # Debug removed
            return
        self.set_input_state(True)
        
        if hasattr(self, 'thinking_frame'):
            self.thinking_frame.grid_remove()
        
        # Cache aussi le texte en bas
        if hasattr(self, 'status_label'):
            self.status_label.configure(text="")
    
    def show_thinking_animation(self):
        """Affiche l'animation de réflexion et désactive la saisie"""
        self.is_thinking = True
        # NOUVEAU : Désactiver la zone de saisie
        self.set_input_state(False)
        
        if hasattr(self, 'thinking_frame'):
            self.thinking_frame.grid(row=1, column=0, sticky="ew", padx=20, pady=(0, 10))
            self.animate_thinking()

    def show_search_animation(self):
        """Affiche l'animation de recherche et désactive la saisie"""
        self.is_searching = True
        # NOUVEAU : Désactiver la zone de saisie
        self.set_input_state(False)
        
        if hasattr(self, 'thinking_frame'):
            self.thinking_frame.grid(row=1, column=0, sticky="ew", padx=20, pady=(0, 10))
            self.animate_search()

    def adjust_text_height(self, text_widget, text):
        """Ajuste la hauteur du widget de texte selon le contenu"""
        try:
            if self.use_ctk:
                # Pour CustomTkinter CTkTextbox, mesure plus précise
                text_widget.update_idletasks()  # Forcer la mise à jour
                
                # Pour CustomTkinter, on ne peut pas changer l'état facilement
                # On va calculer la hauteur autrement
                lines = text.split('\n')
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
                padding = 15      # Padding total
                min_height = 40   # Hauteur minimale
                max_height = 500  # Hauteur maximale pour éviter les messages trop longs
                
                calculated_height = max(min_height, min(total_lines * line_height + padding, max_height))
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
                line_count = int(text_widget.index("end-1c").split('.')[0])
                
                # Restaurer l'état
                text_widget.configure(state=current_state)
                
                # Ajuster en nombre de lignes (plus précis pour tkinter)
                height = max(2, min(line_count + 1, 25))  # +1 pour la marge, max 25 lignes
                text_widget.configure(height=height)
                
        except Exception as e:
            self.logger.error(f"Erreur lors de l'ajustement de la hauteur: {e}")
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
                if getattr(self, '_typing_interrupted', False):
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
            if hasattr(self, 'input_text'):
                # S'assurer que l'input est activé au démarrage
                self.input_text.configure(state="normal")
                # Mettre le focus
                self.root.after(200, lambda: self.input_text.focus_set())
                print("✅ Input ready")
        except Exception as e:
            print(f"⚠️ Erreur ensure_input_ready: {e}")
    
    def on_shift_enter(self, event):
        """Gère Shift+Entrée pour nouvelle ligne - VERSION CORRIGÉE"""
        # Cette fonction peut être vide car on_enter_key gère déjà tout
        return None
    
    def setup_keyboard_shortcuts(self):
        """Configure les raccourcis clavier"""
        # Raccourci Ctrl+L pour effacer
        self.root.bind('<Control-l>', lambda e: self.clear_chat())
        self.root.bind('<Control-L>', lambda e: self.clear_chat())
        
        # Focus sur le champ de saisie au démarrage
        self.root.after(100, lambda: self.input_text.focus())
    
    def set_placeholder(self):
        """Définit le texte de placeholder"""
        placeholder_text = "Tapez votre message ici... (Entrée pour envoyer, Shift+Entrée pour nouvelle ligne)"
        
        if self.use_ctk:
            # CustomTkinter gère le placeholder différemment
            self.input_text.insert("1.0", placeholder_text)
            self.input_text.configure(text_color=self.colors['text_secondary'])
            
            def on_focus_in(event):
                if self.input_text.get("1.0", "end-1c") == placeholder_text:
                    self.input_text.delete("1.0", "end")
                    self.input_text.configure(text_color=self.colors['text_primary'])
            
            def on_focus_out(event):
                if not self.input_text.get("1.0", "end-1c").strip():
                    self.input_text.insert("1.0", placeholder_text)
                    self.input_text.configure(text_color=self.colors['text_secondary'])
            
            self.input_text.bind("<FocusIn>", on_focus_in)
            self.input_text.bind("<FocusOut>", on_focus_out)
        else:
            # Pour tkinter standard
            self.input_text.insert("1.0", placeholder_text)
            self.input_text.configure(fg=self.colors['text_secondary'])
            
            def on_focus_in(event):
                if self.input_text.get("1.0", "end-1c") == placeholder_text:
                    self.input_text.delete("1.0", "end")
                    self.input_text.configure(fg=self.colors['text_primary'])
            
            def on_focus_out(event):
                if not self.input_text.get("1.0", "end-1c").strip():
                    self.input_text.insert("1.0", placeholder_text)
                    self.input_text.configure(fg=self.colors['text_secondary'])
            
            self.input_text.bind("<FocusIn>", on_focus_in)
            self.input_text.bind("<FocusOut>", on_focus_out)
    
    def start_animations(self):
        """Démarre les animations de l'interface"""
        self.animate_thinking()
        self.animate_search()
    
    def animate_thinking(self):
        """Animation de réflexion de l'IA - VERSION WOW FACTOR"""
        if hasattr(self, 'thinking_label') and self.is_thinking:
            # Animations avancées qui montrent l'intelligence de l'IA
            advanced_animations = [
                "⚡ Traitement neural en cours...",
                "🔍 Détection d'intentions...",
                "💡 Génération de réponse intelligente...",
                "🎯 Optimisation de la réponse...",
                "⚙️ Moteur de raisonnement actif...",
                "📊 Analyse des patterns...",
                "🚀 Finalisation de la réponse...",
                "🔮 Prédiction des besoins...",
                "💻 Processing linguistique avancé...",
                "🎪 Préparation d'une réponse..."
            ]
            
            # Choisir une animation aléatoire pour plus de variété
            import random
            if not hasattr(self, 'current_thinking_text') or self.thinking_dots % 4 == 0:
                self.current_thinking_text = random.choice(advanced_animations)
            
            # Animation de points progressifs
            dots = ["", ".", "..", "..."][self.thinking_dots % 4]
            display_text = self.current_thinking_text + dots
            
            self.thinking_dots = (self.thinking_dots + 1) % 4
            self.thinking_label.configure(text=display_text)
            
            # Animation plus rapide pour donner l'impression de vitesse
            self.root.after(400, self.animate_thinking)
        elif hasattr(self, 'thinking_label'):
            self.thinking_label.configure(text="")
    
    def animate_search(self):
        """Animation de recherche internet"""
        if hasattr(self, 'thinking_label') and self.is_searching:
            # Animations de recherche variées
            animations = [
                "🔍 Recherche sur internet",
                "🌐 Recherche sur internet",
                "📡 Recherche sur internet", 
                "🔎 Recherche sur internet",
                "💫 Recherche sur internet",
                "⚡ Recherche sur internet"
            ]
            
            self.search_frame = (self.search_frame + 1) % len(animations)
            self.thinking_label.configure(text=animations[self.search_frame])
            
            # Continuer l'animation toutes les 800ms
            self.root.after(800, self.animate_search)
        elif hasattr(self, 'thinking_label'):
            self.thinking_label.configure(text="")
   
    def send_message(self):
        # Debug removed
        """Envoie le message - VERSION CORRIGÉE"""
        try:
            # Permettre l'envoi même si animation interrompue
            if self.is_animation_running():
                if getattr(self, '_typing_interrupted', False):
                    self.finish_typing_animation_dynamic(interrupted=True)
                else:
                    return
            # Récupérer le texte AVANT de vérifier l'état
            message = ""
            try:
                message = self.input_text.get("1.0", "end-1c").strip()
            except Exception as e:
                print(f"❌ Erreur lecture input: {e}")
                return
                
            # Debug removed
            
            if not message:
                return
                return
            
            # S'assurer que la saisie est activée pour pouvoir lire et effacer
            was_disabled = False
            try:
                current_state = self.input_text.cget("state")
                if current_state == "disabled":
                    was_disabled = True
                    self.input_text.configure(state="normal")
            except:
                pass
            
            # Cacher les indicateurs
            self.hide_status_indicators()
            
            # Ajouter le message utilisateur
            # Debug removed
            self.add_message_bubble(message, is_user=True)
            
            # Effacer la zone de saisie
            try:
                self.input_text.delete("1.0", "end")
                # Debug removed
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
            if not hasattr(self, 'current_request_id'):
                self.current_request_id = 0
            self.current_request_id += 1
            request_id = self.current_request_id

            # Réinitialise l'interruption à chaque nouveau message
            self.is_interrupted = False

            # Lancer le traitement avec l'ID
            threading.Thread(
                target=self.quel_handle_message_with_id,
                args=(message, request_id),
                daemon=True
            ).start()
            
            # Debug removed
            
        except Exception as e:
            # Debug removed
            
            # En cas d'erreur, s'assurer que la saisie est réactivée
            try:
                self.set_input_state(True)
            except:
                pass

    def quel_handle_message_with_id(self, user_text, request_id):
        """
        Traite le message utilisateur avec gestion de l'ID de requête et de l'aiguillage.
        """
        # Détection d'intention (à adapter selon votre logique)
        intent = None
        confidence = 0.0
        try:
            # Si votre AIEngine expose une méthode d'intent, utilisez-la, sinon adaptez ici
            if hasattr(self.ai_engine, 'detect_intent'):
                intent, confidence = self.ai_engine.detect_intent(user_text)
            else:
                # Fallback simple : détection par mot-clé
                if 'internet' in user_text.lower() or 'cherche sur internet' in user_text.lower():
                    intent = 'internet_search'
                    confidence = 1.0
                elif 'qui es-tu' in user_text.lower() or 'tu es qui' in user_text.lower():
                    intent = 'identity_question'
                    confidence = 1.0
                else:
                    intent = 'unknown'
                    confidence = 0.0
        except Exception:
            intent = 'unknown'
            confidence = 0.0

        # Correction : toujours passer la question à AIEngine.process_text pour garantir la priorité FAQ/ML
        print(f"[DEBUG] (ModernAIGUI) Question transmise à AIEngine.process_text : {repr(user_text)}")
        try:
            response = self.ai_engine.process_text(user_text)
        except Exception as e:
            response = f"❌ Erreur IA : {e}"
        if self.current_request_id == request_id and not self.is_interrupted:
            self.root.after(0, lambda: self.add_ai_response(response))
        self.root.after(0, self.hide_status_indicators)
        
    def process_user_message(self, message):
        print(f"[DEBUG] process_user_message called with message: {message}")
        """Traite le message utilisateur en arrière-plan - VERSION AVEC DEBUG"""
        # Debug removed
        
        def run_async_task():
            """Exécute la tâche asynchrone dans un thread séparé"""
            try:
                # Debug removed
                
                # Créer une nouvelle boucle d'événements pour ce thread
                import asyncio
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                # Debug removed
                
                # Exécuter la tâche asynchrone
                # Debug removed
                response = loop.run_until_complete(self.ai_engine.process_query(message))
                # Debug removed
                
                # Fermer la boucle
                loop.close()
                # Debug removed
                
                # Mettre à jour l'interface dans le thread principal
                self.root.after(0, self.hide_status_indicators)
                self.root.after(0, lambda r=response: self.add_ai_response(r))
                # Debug removed
                
            except Exception as e:
                # Debug removed
                
                self.root.after(0, self.hide_status_indicators)
                error_msg = f"❌ Erreur: {str(e)}"
                self.root.after(0, lambda msg=error_msg: self.add_ai_response(msg))
        
        # Lancer dans un thread séparé
        import threading
        print("🔍 DEBUG: Création du thread pour run_async_task")
        threading.Thread(target=run_async_task, daemon=True).start()
    
    def add_ai_response(self, response):
        print(f"[DEBUG] add_ai_response called with response: {str(response)[:60]}")
        """Ajoute une réponse de l'IA - VERSION CORRIGÉE pour affichage complet"""
        # Debug removed
        
        # EXTRACTION ROBUSTE du texte de réponse
        if isinstance(response, dict):
            # Ordre de priorité pour extraire le message
            message_keys = ['message', 'text', 'content', 'response', 'ai_response']
            
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
                if 'message' in text_response:
                    text_response = text_response['message']
                elif 'text' in text_response:
                    text_response = text_response['text']
                else:
                    text_response = str(text_response)
            
            # Convertir en string si nécessaire
            if text_response is None:
                text_response = str(response)
            else:
                text_response = str(text_response)
        
        else:
            text_response = str(response)
        
        # Debug removed
        
        # VÉRIFICATION que le texte n'est pas vide
        if not text_response or text_response.strip() == "" or text_response == "None":
            text_response = "⚠️ Réponse vide reçue"
            pass
        
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
            
            if hasattr(self, 'chat_frame'):
                self.chat_frame.update_idletasks()
            
            if self.use_ctk:
                # CustomTkinter
                if hasattr(self, 'chat_frame'):
                    parent = self.chat_frame.master
                    while parent and not hasattr(parent, 'yview_moveto'):
                        parent = parent.master
                    
                    if parent and hasattr(parent, 'yview_moveto'):
                        # Double mise à jour pour synchronisation parfaite
                        parent.update_idletasks()
                        parent.yview_moveto(1.0)
                        # Petite pause pour éviter le décalage
                        self.root.after(1, lambda: parent.yview_moveto(1.0))
            else:
                # Tkinter standard
                parent = self.chat_frame.master
                if hasattr(parent, 'yview_moveto'):
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
                if hasattr(parent, 'yview_moveto'):
                    parent.yview_moveto(1.0)
            else:
                parent = self.chat_frame.master
                if hasattr(parent, 'yview_moveto'):
                    parent.yview_moveto(1.0)
        except:
            pass  # Silencieux pour éviter spam logs
    
    def scroll_to_top(self):
        """Fait défiler vers le HAUT de la conversation (pour clear chat)"""
        try:
            self.root.update_idletasks()
            
            if self.use_ctk:
                # CustomTkinter - Chercher le scrollable frame
                if hasattr(self, 'chat_frame'):
                    try:
                        # Méthode 1: Via le parent canvas (plus fiable)
                        parent = self.chat_frame.master
                        while parent and not hasattr(parent, 'yview_moveto'):
                            parent = parent.master
                        
                        if parent and hasattr(parent, 'yview_moveto'):
                            parent.update_idletasks()
                            parent.yview_moveto(0.0)  # 0.0 pour le HAUT
                            self.logger.debug("Scroll vers le haut CTk via parent canvas")
                        elif hasattr(self.chat_frame, '_parent_canvas'):
                            # Méthode 2: Canvas direct
                            canvas = self.chat_frame._parent_canvas
                            canvas.update_idletasks()
                            canvas.yview_moveto(0.0)  # 0.0 pour le HAUT
                            self.logger.debug("Scroll vers le haut CTk via _parent_canvas")
                        else:
                            self.logger.warning("Impossible de trouver canvas pour scroll vers le haut CTk")
                    except Exception as e:
                        self.logger.error(f"Erreur scroll vers le haut CTk: {e}")
            else:
                # Tkinter standard - Chercher le canvas scrollable
                try:
                    parent = self.chat_frame.master
                    if hasattr(parent, 'yview_moveto'):
                        parent.update_idletasks()
                        parent.yview_moveto(0.0)  # 0.0 pour le HAUT
                        self.logger.debug("Scroll vers le haut tkinter via parent direct")
                    else:
                        # Chercher dans la hiérarchie
                        current = parent
                        while current:
                            if hasattr(current, 'yview_moveto'):
                                current.update_idletasks()
                                current.yview_moveto(0.0)  # 0.0 pour le HAUT
                                self.logger.debug("Scroll vers le haut tkinter via hiérarchie")
                                break
                            current = current.master
                except Exception as e:
                    self.logger.error(f"Erreur scroll vers le haut tkinter: {e}")
                    
            # Forcer une seconde tentative après délai court
            self.root.after(100, self._force_scroll_top)
            
        except Exception as e:
            self.logger.error(f"Erreur critique lors du scroll vers le haut: {e}")
    
    def _force_scroll_top(self):
        """Force le scroll vers le haut - tentative secondaire"""
        try:
            if self.use_ctk:
                parent = self.chat_frame.master
                if hasattr(parent, 'yview_moveto'):
                    parent.yview_moveto(0.0)  # 0.0 pour le HAUT
            else:
                parent = self.chat_frame.master
                if hasattr(parent, 'yview_moveto'):
                    parent.yview_moveto(0.0)  # 0.0 pour le HAUT
        except:
            pass  # Silencieux pour éviter spam logs

    # ...existing code...
    
    def clear_chat(self):
        """Efface la conversation"""
        try:
            # Vider l'historique
            self.conversation_history.clear()
            
            # Vider l'interface de chat
            for widget in self.chat_frame.winfo_children():
                widget.destroy()
            
            # Effacer la mémoire de l'IA
            if hasattr(self.ai_engine, 'clear_conversation'):
                self.ai_engine.clear_conversation()
            
            # Message de confirmation
            self.show_welcome_message()
            
            # RETOURNER EN HAUT de la page après clear
            self.scroll_to_top()
            
            self.logger.info("Conversation effacée")
            
        except Exception as e:
            self.logger.error(f"Erreur lors de l'effacement: {e}")
            messagebox.showerror("Erreur", f"Impossible d'effacer la conversation: {e}")
    
    def show_welcome_message(self):
        """Affiche le message de bienvenue initial"""
        welcome_text = """Bonjour ! Je suis votre **Assistant IA Local** 🤖

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
            title="Sélectionner un fichier PDF",
            filetypes=[("Fichiers PDF", "*.pdf")]
        )
        
        if file_path:
            self.process_file(file_path, "PDF")
    
    def load_docx_file(self):
        """Charge un fichier DOCX"""
        file_path = filedialog.askopenfilename(
            title="Sélectionner un fichier DOCX",
            filetypes=[("Fichiers Word", "*.docx")]
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
                ("Tous les fichiers", "*.*")
            ]
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
                daemon=True
            ).start()
            
        except Exception as e:
            self.logger.error(f"Erreur lors du chargement du fichier: {e}")
            messagebox.showerror("Erreur", f"Impossible de charger le fichier: {e}")
    
    def process_file_background(self, file_path, file_type, filename):
        """Traite le fichier en arrière-plan"""
        try:
            self.logger.info(f"Traitement du fichier: {filename} (type: {file_type})")
            
            if file_type == "PDF":
                self.logger.info("Extraction PDF en cours...")
                content = self.pdf_processor.extract_text_from_pdf(file_path)
                self.logger.info(f"PDF extrait: {len(content)} caractères")
            elif file_type == "DOCX":
                self.logger.info("Extraction DOCX en cours...")
                content = self.docx_processor.extract_text_from_docx(file_path)
                self.logger.info(f"DOCX extrait: {len(content)} caractères")
            elif file_type == "Code":
                self.logger.info("Extraction code en cours...")
                content = self.code_processor.extract_text_from_file(file_path)
                self.logger.info(f"Code extrait: {len(content)} caractères")
            else:
                raise ValueError(f"Type de fichier non supporté: {file_type}")
            
            # Vérifier que le contenu n'est pas vide
            if not content or not content.strip():
                raise ValueError(f"Le fichier {filename} semble vide ou illisible")
            
            # Stocker dans la mémoire de l'IA
            if hasattr(self.ai_engine, 'local_ai') and hasattr(self.ai_engine.local_ai, 'conversation_memory'):
                self.ai_engine.local_ai.conversation_memory.store_document_content(filename, content)
                self.logger.info(f"Contenu stocké dans la mémoire de l'IA pour {filename}")
            else:
                self.logger.warning("Mémoire de conversation non disponible")
            
            # Arrêter l'animation
            self.is_thinking = False
            
            # Confirmer le traitement avec un aperçu du contenu
            preview = content[:200] + "..." if len(content) > 200 else content
            success_msg = f"✅ **{filename}** traité avec succès !\n\n**Aperçu du contenu:**\n{preview}\n\nVous pouvez maintenant me poser des questions dessus."
            self.root.after(0, lambda: self.add_ai_response(success_msg))
            
        except Exception as e:
            self.logger.error(f"Erreur lors du traitement de {filename}: {str(e)}")
            self.is_thinking = False
            error_msg = f"❌ Erreur lors du traitement de **{filename}** : {str(e)}"
            self.root.after(0, lambda: self.add_ai_response(error_msg))
    
    def initialize_ai_async(self):
        """Version CORRIGÉE sans ai_status_var"""
        def init_ai():
            try:
                print("🔍 DEBUG: Initialisation de l'IA en cours...")
                
                if not hasattr(self, 'ai_engine'):
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
                import traceback
                traceback.print_exc()
        
        print("🔍 DEBUG: Lancement du thread d'initialisation IA")
        threading.Thread(target=init_ai, daemon=True).start()
    
    def run(self):
        """Lance l'interface"""
        try:
            self.logger.info("Démarrage de l'interface graphique moderne")
            self.root.mainloop()
        except KeyboardInterrupt:
            self.logger.info("Arrêt de l'interface par l'utilisateur")
        except Exception as e:
            self.logger.error(f"Erreur dans l'interface: {e}")
            messagebox.showerror("Erreur", f"Erreur dans l'interface: {e}")


def main():
    """Point d'entrée principal"""
    try:
        app = ModernAIGUI()
        app.run()
    except Exception as e:
        print(f"❌ Erreur lors du démarrage: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
