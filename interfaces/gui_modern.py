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
    print("⚠️  CustomTkinter non disponible, utilisation de tkinter standard")

try:
    from tkinterdnd2 import TkinterDnD
    DND_AVAILABLE = True
except ImportError:
    DND_AVAILABLE = False
    print("⚠️  TkinterDnD2 non disponible, drag & drop désactivé")

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
    print("⚠️  CustomTkinter non disponible, utilisation de tkinter standard")

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
    """Interface Graphique Moderne pour l'Assistant IA - Style Claude"""
    
    def __init__(self):
        """Initialise l'interface moderne"""
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
        clear_btn = self.create_modern_button(
            buttons_frame,
            text="🗑️ Clear Chat",
            command=self.clear_chat,
            style="secondary"
        )
        clear_btn.grid(row=0, column=0, padx=(0, 10))
        
        # Bouton Help
        help_btn = self.create_modern_button(
            buttons_frame,
            text="❓ Aide",
            command=self.show_help,
            style="secondary"
        )
        help_btn.grid(row=0, column=1, padx=(0, 10))
        
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
        
        pdf_btn = self.create_modern_button(
            file_buttons,
            text="📄 PDF",
            command=self.load_pdf_file,
            style="file"
        )
        pdf_btn.grid(row=0, column=0, padx=(0, 5))
        
        docx_btn = self.create_modern_button(
            file_buttons,
            text="📝 DOCX",
            command=self.load_docx_file,
            style="file"
        )
        docx_btn.grid(row=0, column=1, padx=(0, 5))
        
        code_btn = self.create_modern_button(
            file_buttons,
            text="💻 Code",
            command=self.load_code_file,
            style="file"
        )
        code_btn.grid(row=0, column=2, padx=(0, 10))
        
        # Bouton d'envoi principal
        self.send_button = self.create_modern_button(
            button_frame,
            text="Envoyer ↗",
            command=self.send_message,
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
        """Version améliorée sans scroll interne"""
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
        
        # Ajouter à l'historique
        self.conversation_history.append({
            'text': text,
            'is_user': is_user,
            'timestamp': datetime.now(),
            'type': message_type
        })
        
        # Container principal pour le message
        msg_container = self.create_frame(self.chat_frame, fg_color=self.colors['bg_chat'])
        # Espacement vertical RÉDUIT entre les messages pour plus de compacité
        msg_container.grid(row=len(self.conversation_history)-1, column=0, sticky="ew", pady=(0, 8))  # Réduit de 15 à 8
        msg_container.grid_columnconfigure(0, weight=1)

        if is_user:
            self.create_user_message_bubble(msg_container, text)
        else:
            self.create_ai_message_simple(msg_container, text)

        # Scroll automatique vers le bas (plus rapide pour éviter le "vide")
        self.root.after(10, self.scroll_to_bottom)
    
    def create_user_message_bubble(self, parent, text):
        """Crée une bulle de message utilisateur - CENTRÉ avec alignement parfait"""
        # Frame principale DÉCALÉE comme avant (400px de la gauche)
        main_frame = self.create_frame(parent, fg_color=self.colors['bg_chat'])
        main_frame.grid(row=0, column=0, padx=(400, 0), pady=(0, 0), sticky="w")  # PAS DE PADDING VERTICAL
        main_frame.grid_columnconfigure(0, weight=0)
        main_frame.grid_columnconfigure(1, weight=0)
        
        # Icône utilisateur à GAUCHE (comme avant)
        icon_label = self.create_label(
            main_frame,
            text="👤",
            font=('Segoe UI', self.get_current_font_size('icon')),  # Dynamique
            fg_color=self.colors['bg_chat'],
            text_color=self.colors['text_primary']
        )
        icon_label.grid(row=0, column=0, sticky="nw", padx=(0, 10), pady=(1, 0))  # padding minimal
        
        # Calculer la largeur de bulle OPTIMALE selon le contenu RÉEL
        lines = text.split('\n')
        max_line_length = max(len(line) for line in lines) if lines else len(text)
        
        # Estimation plus précise de la largeur en pixels (basée sur la police)
        current_font_size = self.get_current_font_size('message')
        char_width = current_font_size * 0.6  # Approximation largeur caractère
        
        # Calcul de largeur INTELLIGENT basé sur le contenu réel
        if max_line_length <= 5:
            bubble_width = max(80, int(max_line_length * char_width * 2))   # Très petit
        elif max_line_length <= 15:
            bubble_width = max(120, int(max_line_length * char_width * 1.5))  # Petit optimal
        elif max_line_length <= 30:
            bubble_width = max(180, int(max_line_length * char_width * 1.3))  # Moyen optimal
        elif max_line_length <= 50:
            bubble_width = max(250, int(max_line_length * char_width * 1.2))  # Grand optimal
        elif max_line_length <= 80:
            bubble_width = max(350, int(max_line_length * char_width * 1.1))  # Très grand
        else:
            bubble_width = min(500, int(max_line_length * char_width))  # Maximum adaptatif
        
        # Ajustement selon le nombre de lignes (plus conservateur)
        if len(lines) > 1:
            bubble_width = max(bubble_width, 200)  # Minimum raisonnable pour multi-lignes
        if len(lines) > 4:
            bubble_width = max(bubble_width, 300)  # Plus large seulement si vraiment nécessaire
        
        # Bulle utilisateur ALIGNÉE avec l'icône (même ligne verticale)
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
        
        bubble.grid(row=0, column=1, sticky="w", padx=0, pady=(2, 2))  # RÉDUIT l'espacement vertical
        bubble.grid_columnconfigure(0, weight=1)
        
        # TEXTE SÉLECTIONNABLE - CHOIX TRÈS INTELLIGENT entre Label et TextBox
        current_font_size = self.get_current_font_size('message')
        
        # Analyser le texte pour décider du widget de manière PLUS RESTRICTIVE
        lines = text.split('\n')
        total_chars = len(text)
        has_formatting = '**' in text or '*' in text or '`' in text or '```' in text
        max_line_length = max(len(line) for line in lines) if lines else 0
        
        # Critères ULTRA-STRICTS pour utiliser TextBox (éviter absolument le scroll sur messages courts)
        needs_textbox = (
            has_formatting and total_chars > 250 or  # Formatage ET très long (augmenté de 100 à 250)
            len(lines) > 10 or  # Plus de 10 lignes (augmenté de 7 à 10)
            total_chars > 600 or  # Très très long (augmenté de 400 à 600)
            max_line_length > 110 or  # Ligne vraiment très longue (augmenté de 90 à 110)
            ('\n\n' in text and total_chars > 300)  # Paragraphes multiples ET très long (augmenté de 150 à 300)
        )
        
        # Pour tous les autres cas : TOUJOURS utiliser CTkLabel (jamais de scroll)
        print(f"🔍 DEBUG USER - Message: '{text[:50]}...' | Chars: {total_chars} | Lines: {len(lines)} | Max line: {max_line_length} | Needs TextBox: {needs_textbox}")
        
        if self.use_ctk:
            if needs_textbox:
                # Pour textes longs/formatés : CTkTextbox avec hauteur EXACTE calculée
                lines_count = len(lines)
                max_line_length = max(len(line) for line in lines) if lines else 0
                
                # Calcul précis des lignes wrapped
                chars_per_line = max(30, (bubble_width - 20) // 8)
                wrapped_lines = sum(max(1, (len(line) + chars_per_line - 1) // chars_per_line) for line in lines)
                
                # Hauteur OPTIMISÉE pour éviter les espaces vides
                exact_height = max(30, min(wrapped_lines * 18 + 15, 350))  # Réduit pour compacité
                
                text_widget = ctk.CTkTextbox(
                    bubble,
                    width=bubble_width - 16,
                    height=exact_height,
                    fg_color="transparent",
                    text_color='#ffffff',
                    font=('Segoe UI', current_font_size),
                    wrap="word",
                    state="normal"
                )
                
                # Insérer le texte avec formatage - TOUJOURS UTILISER TKINTER TEXT pour uniformité
                text_widget.delete("1.0", "end")
                # FORCER tkinter Text pour TOUS les messages (uniformité totale)
                text_widget.destroy()
                
                text_widget = tk.Text(
                    bubble,
                    width=int((bubble_width - 16) / 8),  # Approximation caractères
                    height=max(2, min(int(wrapped_lines + 1), 25)),
                    bg='#2b2b2b',
                    fg='#ffffff',
                    font=('Segoe UI', current_font_size),
                    wrap="word",
                    relief="flat",
                    bd=0,
                    highlightthickness=0,
                    state="normal"
                )
                self.insert_formatted_text_tkinter(text_widget, text)
                text_widget.configure(state="disabled")
                
                # DÉSACTIVER LE SCROLL INTERNE mais PERMETTRE le scroll global
                def redirect_scroll_to_parent(event):
                    # Rediriger le scroll vers le CTkScrollableFrame parent
                    if hasattr(self, 'chat_frame') and self.use_ctk:
                        # Pour CTkScrollableFrame, utiliser la méthode native
                        self.chat_frame._parent_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
                    return "break"
                
                text_widget.bind("<MouseWheel>", redirect_scroll_to_parent)
                text_widget.bind("<Button-4>", redirect_scroll_to_parent)
                text_widget.bind("<Button-5>", redirect_scroll_to_parent)
                
                # Bloquer seulement les touches de navigation clavier
                def block_keyboard_scroll(event):
                    return "break"
                    
                text_widget.bind("<Key-Up>", block_keyboard_scroll)
                text_widget.bind("<Key-Down>", block_keyboard_scroll)
                text_widget.bind("<Key-Prior>", block_keyboard_scroll)
                text_widget.bind("<Key-Next>", block_keyboard_scroll)
                text_widget.bind("<Control-a>", lambda e: text_widget.tag_add("sel", "1.0", "end"))
                
                # Permettre sélection par clic
                def enable_selection(event):
                    text_widget.configure(state="normal")
                    text_widget.mark_set("insert", text_widget.index(f"@{event.x},{event.y}"))
                    return "break"
                
                text_widget.bind("<Button-1>", enable_selection)
                
                # Ajouter la fonctionnalité de copie par double-clic
                def copy_text_on_double_click(event):
                    try:
                        self.root.clipboard_clear()
                        self.root.clipboard_append(text)
                        self.show_notification("✅ Texte copié", "success")
                    except:
                        pass
                    return "break"
                
                text_widget.bind("<Double-Button-1>", copy_text_on_double_click)
                text_widget.bind("<Button-3>", copy_text_on_double_click)  # Clic droit aussi
                
            else:
                # Pour textes courts : CTkLabel simple SÉLECTIONNABLE
                text_widget = ctk.CTkLabel(
                    bubble,
                    text=text,
                    width=bubble_width - 16,
                    fg_color="transparent", 
                    text_color='#ffffff',
                    font=('Segoe UI', current_font_size),
                    wraplength=bubble_width - 20,
                    justify="left",
                    anchor="w"
                )
                
                # Rendre le label sélectionnable via menu contextuel
                def copy_text(event):
                    try:
                        self.root.clipboard_clear()
                        self.root.clipboard_append(text)
                        self.show_notification("✅ Texte copié", "success")
                    except:
                        pass
                
                text_widget.bind("<Button-3>", copy_text)  # Clic droit pour copier
                text_widget.bind("<Double-Button-1>", copy_text)  # Double-clic pour copier
            
        else:
            # Text widget tkinter - choix intelligent aussi
            if needs_textbox:
                text_widget = tk.Text(
                    bubble,
                    width=(bubble_width - 16) // 8,
                    height=2,  # Sera ajustée
                    bg=self.colors['bg_user'],
                    fg='#ffffff',
                    font=('Segoe UI', current_font_size),
                    wrap="word",
                    relief="flat",
                    bd=0,
                    highlightthickness=0,
                    state="normal"
                )
                
                # Insérer le texte avec formatage
                text_widget.delete("1.0", "end")
                self.insert_formatted_text_tkinter(text_widget, text)
                text_widget.configure(state="disabled")
                
                # DÉSACTIVER LE SCROLL INTERNE mais permettre scroll global pour tkinter aussi
                def redirect_scroll_to_parent_tk(event):
                    # Pour tkinter, rediriger vers le canvas parent s'il existe
                    parent_canvas = None
                    widget = text_widget
                    while widget:
                        widget = widget.master
                        if hasattr(widget, 'yview_scroll'):
                            parent_canvas = widget
                            break
                    
                    if parent_canvas:
                        parent_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
                    return "break"
                
                text_widget.bind("<MouseWheel>", redirect_scroll_to_parent_tk)
                text_widget.bind("<Button-4>", redirect_scroll_to_parent_tk)
                text_widget.bind("<Button-5>", redirect_scroll_to_parent_tk)
                
                # Bloquer seulement navigation clavier
                def block_keyboard_scroll(event):
                    return "break"
                    
                text_widget.bind("<Key-Up>", block_keyboard_scroll)
                text_widget.bind("<Key-Down>", block_keyboard_scroll)
                text_widget.bind("<Key-Prior>", block_keyboard_scroll)
                text_widget.bind("<Key-Next>", block_keyboard_scroll)
                
                # PERMETTRE LA SÉLECTION
                def enable_selection(event):
                    text_widget.configure(state="normal")
                    return "break"
                
                text_widget.bind("<Button-1>", enable_selection)
                
            else:
                # Label simple pour textes courts
                text_widget = tk.Label(
                    bubble,
                    text=text,
                    bg=self.colors['bg_user'],
                    fg='#ffffff',
                    font=('Segoe UI', current_font_size),
                    wraplength=bubble_width - 20,
                    justify="left",
                    anchor="w"
                )
                
                # Menu contextuel pour copier
                def copy_text(event):
                    try:
                        self.root.clipboard_clear()
                        self.root.clipboard_append(text)
                        self.show_notification("✅ Texte copié", "success")
                    except:
                        pass
                
                text_widget.bind("<Button-3>", copy_text)
                text_widget.bind("<Double-Button-1>", copy_text)
        
        text_widget.grid(row=0, column=0, padx=8, pady=(1, 0), sticky="nw")

        # Menu contextuel pour copier (tous les widgets)
        self.create_copy_menu(text_widget, text)
        
        # Timestamp DANS LA MÊME BULLE, juste en dessous du texte
        timestamp = datetime.now().strftime("%H:%M")
        time_label = self.create_label(
            bubble,  # Dans la bulle, pas dans main_frame
            text=timestamp,
            font=('Segoe UI', self.get_current_font_size('timestamp')),  # Dynamique
            fg_color=self.colors['bg_user'],  # Même couleur que la bulle
            text_color=self.colors['text_secondary']
        )
        # Placement DANS la bulle, row=1 pour être sous le texte
        time_label.grid(row=1, column=0, sticky="w", padx=8, pady=(0, 1))
    
    def create_ai_message_simple(self, parent, text):
        """Crée un message IA simple sans bulle - CENTRÉ avec même alignement"""
        # Frame de centrage IDENTIQUE au décalage utilisateur (400px)
        center_frame = self.create_frame(parent, fg_color=self.colors['bg_chat'])
        center_frame.grid(row=0, column=0, padx=(400, 0), pady=(0, 0), sticky="w")
        center_frame.grid_columnconfigure(0, weight=0)
        center_frame.grid_columnconfigure(1, weight=0)  # Changé de weight=1 à weight=0
        
        # Icône IA à position IDENTIQUE à l'utilisateur
        icon_label = self.create_label(
            center_frame,
            text="🤖",
            font=('Segoe UI', self.get_current_font_size('icon')),  # Dynamique
            fg_color=self.colors['bg_chat'],
            text_color=self.colors['accent']
        )
        icon_label.grid(row=0, column=0, sticky="nw", padx=(0, 10), pady=(1, 0))
        
        # Zone de texte IA SÉLECTIONNABLE - CHOIX TRÈS INTELLIGENT entre Label et TextBox
        current_font_size = self.get_current_font_size('message')
        
        # Analyser le texte pour décider du widget de manière PLUS RESTRICTIVE
        lines = text.split('\n')
        total_chars = len(text)
        has_formatting = '**' in text or '*' in text or '`' in text or '```' in text
        max_line_length = max(len(line) for line in lines) if lines else 0
        
        # Calcul de largeur OPTIMALE pour IA (largeurs TRÈS réduites pour éviter les bulles trop larges)
        char_width = current_font_size * 0.6  # Approximation largeur caractère
        
        if max_line_length <= 10:
            optimal_width = max(100, int(max_line_length * char_width * 1.2))  # Encore plus réduit
        elif max_line_length <= 25:
            optimal_width = max(130, int(max_line_length * char_width * 1.1))  # Encore plus réduit
        elif max_line_length <= 50:
            optimal_width = max(180, int(max_line_length * char_width * 1.0))  # Très réduit
        elif max_line_length <= 80:
            optimal_width = max(220, int(max_line_length * char_width * 0.9))  # Très réduit
        else:
            optimal_width = min(300, int(max_line_length * char_width * 0.8))  # Maximum très réduit
        
        # Ajustement selon nombre de lignes - beaucoup plus conservateur
        if len(lines) > 4:
            optimal_width = max(optimal_width, 200)  # Réduit de 250 à 200
        
        # Limitation par la taille de l'écran - TRÈS restrictive pour éviter les bulles trop larges
        screen_available = self.root.winfo_width() - 500 if self.root.winfo_width() > 600 else 300
        max_width = min(optimal_width, min(screen_available, 450))  # Maximum absolu de 450px
        
        # Critères ULTRA-STRICTS pour utiliser TextBox (éviter absolument le scroll sur messages courts)
        needs_textbox_ai = (
            has_formatting and total_chars > 300 or  # Formatage ET très long (augmenté de 100 à 300)
            len(lines) > 12 or  # Plus de 12 lignes (augmenté de 8 à 12)
            total_chars > 800 or  # Très très long (augmenté de 500 à 800)
            max_line_length > 120 or  # Ligne vraiment très longue (augmenté de 100 à 120)
            ('\n\n' in text and total_chars > 400)  # Paragraphes multiples ET très long (augmenté de 200 à 400)
        )
        
        # Pour tous les autres cas : TOUJOURS utiliser CTkLabel (jamais de scroll)
        print(f"🔍 DEBUG IA - Message: '{text[:50]}...' | Chars: {total_chars} | Lines: {len(lines)} | Max line: {max_line_length} | Needs TextBox: {needs_textbox_ai}")
        
        if self.use_ctk:
            if needs_textbox_ai:
                # CTkTextbox pour textes longs avec hauteur optimisée
                lines_count = len(lines)
                chars_per_line = max(40, (max_width - 20) // 8)
                wrapped_lines = sum(max(1, (len(line) + chars_per_line - 1) // chars_per_line) for line in lines)
                exact_height = max(35, min(wrapped_lines * 18 + 15, 400))  # Réduit pour éviter espaces vides
                
                text_widget = ctk.CTkTextbox(
                    center_frame,
                    width=min(max_width, 400),  # Limiter davantage la largeur
                    height=exact_height,
                    fg_color=self.colors['bg_chat'],
                    text_color=self.colors['text_primary'],
                    font=('Segoe UI', current_font_size),
                    wrap="word",
                    state="normal"
                )
                
                # Insérer le texte avec formatage - UTILISER TKINTER TEXT pour vrai formatage
                text_widget.delete("1.0", "end")
                # Si on a du formatage, utiliser tkinter Text pour un vrai rendu
                if '**' in text or '*' in text or '`' in text:
                    # Créer un widget tkinter Text avec vrai formatage
                    text_widget.destroy()
                    
                    text_widget = tk.Text(
                        center_frame,
                        width=min(int(max_width / 8), 50),  # Limiter la largeur en caractères
                        height=max(2, min(int(wrapped_lines + 1), 30)),
                        bg=self.colors['bg_chat'],
                        fg=self.colors['text_primary'],
                        font=('Segoe UI', current_font_size),
                        wrap="word",
                        relief="flat",
                        bd=0,
                        highlightthickness=0,
                        state="normal"
                    )
                    self.insert_formatted_text_tkinter(text_widget, text)
                    text_widget.configure(state="disabled")
                else:
                    # Texte simple sans formatage
                    self.insert_formatted_text_ctk(text_widget, text)
                    text_widget.configure(state="disabled")
                
                # DÉSACTIVER LE SCROLL INTERNE mais PERMETTRE le scroll global
                def redirect_scroll_to_parent(event):
                    # Rediriger le scroll vers le CTkScrollableFrame parent
                    if hasattr(self, 'chat_frame') and self.use_ctk:
                        # Pour CTkScrollableFrame, utiliser la méthode native
                        self.chat_frame._parent_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
                    return "break"
                
                text_widget.bind("<MouseWheel>", redirect_scroll_to_parent)
                text_widget.bind("<Button-4>", redirect_scroll_to_parent)
                text_widget.bind("<Button-5>", redirect_scroll_to_parent)
                
                # Bloquer seulement les touches de navigation clavier
                def block_keyboard_scroll(event):
                    return "break"
                    
                text_widget.bind("<Key-Up>", block_keyboard_scroll)
                text_widget.bind("<Key-Down>", block_keyboard_scroll)
                text_widget.bind("<Key-Prior>", block_keyboard_scroll)
                text_widget.bind("<Key-Next>", block_keyboard_scroll)
                
                # PERMETTRE LA SÉLECTION
                def enable_selection(event):
                    text_widget.configure(state="normal")
                    text_widget.mark_set("insert", text_widget.index(f"@{event.x},{event.y}"))
                    return "break"
                
                text_widget.bind("<Button-1>", enable_selection)
                
                # Ajouter la fonctionnalité de copie par double-clic
                def copy_text_on_double_click(event):
                    try:
                        self.root.clipboard_clear()
                        self.root.clipboard_append(text)
                        self.show_notification("✅ Texte copié", "success")
                    except:
                        pass
                    return "break"
                
                text_widget.bind("<Double-Button-1>", copy_text_on_double_click)
                text_widget.bind("<Button-3>", copy_text_on_double_click)  # Clic droit aussi
                
            else:
                # CTkLabel pour textes courts - largeur adaptée au contenu
                text_widget = ctk.CTkLabel(
                    center_frame,
                    text=text,
                    width=min(max_width, 350),  # Limiter la largeur maximum
                    fg_color=self.colors['bg_chat'],
                    text_color=self.colors['text_primary'],
                    font=('Segoe UI', current_font_size),
                    wraplength=min(max_width - 20, 330),  # Wraplength également limitée
                    justify="left",
                    anchor="w"
                )
                
                # Copie par clic droit
                def copy_text(event):
                    try:
                        self.root.clipboard_clear()
                        self.root.clipboard_append(text)
                        self.show_notification("✅ Texte copié", "success")
                    except:
                        pass
                
                text_widget.bind("<Button-3>", copy_text)
                text_widget.bind("<Double-Button-1>", copy_text)
            
        else:
            if needs_textbox_ai:
                # Text widget tkinter pour textes longs
                text_widget = tk.Text(
                    center_frame,
                    width=(max_width - 20) // 8,
                    height=3,  # Sera ajustée
                    bg=self.colors['bg_chat'],
                    fg=self.colors['text_primary'],
                    font=('Segoe UI', current_font_size),
                    wrap="word",
                    relief="flat",
                    bd=0,
                    highlightthickness=0,
                    state="normal"
                )
                
                # Insérer le texte avec formatage
                text_widget.delete("1.0", "end")
                self.insert_formatted_text_tkinter(text_widget, text)
                text_widget.configure(state="disabled")
                
                # DÉSACTIVER LE SCROLL INTERNE mais permettre scroll global pour tkinter IA
                def redirect_scroll_to_parent_tk_ai(event):
                    # Pour tkinter, rediriger vers le canvas parent s'il existe
                    parent_canvas = None
                    widget = text_widget
                    while widget:
                        widget = widget.master
                        if hasattr(widget, 'yview_scroll'):
                            parent_canvas = widget
                            break
                    
                    if parent_canvas:
                        parent_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
                    return "break"
                
                text_widget.bind("<MouseWheel>", redirect_scroll_to_parent_tk_ai)
                text_widget.bind("<Button-4>", redirect_scroll_to_parent_tk_ai)
                text_widget.bind("<Button-5>", redirect_scroll_to_parent_tk_ai)
                
                # Bloquer seulement navigation clavier
                def block_keyboard_scroll_ai(event):
                    return "break"
                    
                text_widget.bind("<Key-Up>", block_keyboard_scroll_ai)
                text_widget.bind("<Key-Down>", block_keyboard_scroll_ai)
                text_widget.bind("<Key-Prior>", block_keyboard_scroll_ai)
                text_widget.bind("<Key-Next>", block_keyboard_scroll_ai)
                
                # PERMETTRE LA SÉLECTION
                def enable_selection(event):
                    text_widget.configure(state="normal")
                    return "break"
                
                text_widget.bind("<Button-1>", enable_selection)
                
            else:
                # Label pour textes courts
                text_widget = tk.Label(
                    center_frame,
                    text=text,
                    bg=self.colors['bg_chat'],
                    fg=self.colors['text_primary'],
                    font=('Segoe UI', current_font_size),
                    wraplength=max_width - 20,
                    justify="left",
                    anchor="w"
                )
                
                # Menu contextuel pour copier
                def copy_text(event):
                    try:
                        self.root.clipboard_clear()
                        self.root.clipboard_append(text)
                        self.show_notification("✅ Texte copié", "success")
                    except:
                        pass
                
                text_widget.bind("<Button-3>", copy_text)
                text_widget.bind("<Double-Button-1>", copy_text)
        
        text_widget.grid(row=0, column=1, sticky="w", padx=(0, 0), pady=(1, 0))

        # Menu contextuel pour copier (tous les widgets)
        self.create_copy_menu(text_widget, text)
        
        # Timestamp DIRECTEMENT sous le texte IA, dans le même container
        timestamp = datetime.now().strftime("%H:%M")
        time_label = self.create_label(
            center_frame,
            text=timestamp,
            font=('Segoe UI', self.get_current_font_size('timestamp')),  # Dynamique
            fg_color=self.colors['bg_chat'],
            text_color=self.colors['text_secondary']
        )
        # Placement SOUS le texte dans la même colonne, row=1 avec padding minimal
        time_label.grid(row=1, column=1, sticky="w", padx=(0, 0), pady=(0, 1))

    def insert_formatted_text_tkinter(self, text_widget, text):
        """Insère du texte formaté avec VRAI gras/italique/monospace dans tkinter Text"""
        import re
        text_widget.delete("1.0", "end")
        current_font_size = self.get_current_font_size('message')
        
        # Configurer les tags AVANT insertion
        text_widget.tag_configure("bold", font=('Segoe UI', current_font_size, 'bold'))
        text_widget.tag_configure("italic", font=('Segoe UI', current_font_size, 'italic'))
        text_widget.tag_configure("mono", font=('Consolas', current_font_size))
        text_widget.tag_configure("normal", font=('Segoe UI', current_font_size))
        
        # Patterns pour détecter **gras**, *italique*, `monospace`
        patterns = [
            (r'\*\*([^*]+)\*\*', 'bold'),     # **texte** -> gras
            (r'\*([^*]+)\*', 'italic'),       # *texte* -> italique  
            (r'`([^`]+)`', 'mono')            # `texte` -> monospace
        ]
        
        # Traitement séquentiel pour gérer les imbrications
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
        
        # Insérer les segments avec le bon tag
        for segment_text, style in segments:
            if segment_text:  # Éviter les segments vides
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
        
        Args:
            widget: Widget auquel attacher le menu
            original_text: Texte original à copier (sans formatage Unicode)
        """
        def copy_text():
            try:
                self.root.clipboard_clear()
                self.root.clipboard_append(original_text)
                self.show_notification("📋 Texte copié dans le presse-papiers", "success")
            except Exception as e:
                self.show_notification(f"❌ Erreur lors de la copie: {e}", "error")
        
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
    
    def get_current_font_size(self, font_type='message'):
        """Obtient la taille de police adaptée à l'écran - UNIFIÉ À 11px pour tout le contenu"""
        screen_width = self.root.winfo_screenwidth()
        
        # FORCE L'UNIFICATION : tous les contenus textuels utilisent 11px
        content_types = ['message', 'body', 'chat', 'bold', 'small']
        if font_type in content_types:
            return 11  # TAILLE UNIFIÉE POUR TOUT LE CONTENU
        
        # Seuls les éléments d'interface gardent leurs tailles spécifiques
        interface_font_sizes = {
            'timestamp': 9,     # Timestamps plus petits
            'icon': 16,         # Icônes (🤖, 👤)
            'header': 20,       # Éléments d'en-tête
            'status': 12,       # Indicateurs de statut
            'title': 32,        # Titres principaux
            'subtitle': 18,     # Sous-titres
        }
        
        return interface_font_sizes.get(font_type, 11)  # 11 par défaut
    
    def insert_formatted_text_ctk(self, text_widget, text):
        """Insère du texte formaté avec rendu visuel subtil dans CustomTkinter TextBox"""
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
        """Cache tous les indicateurs de statut"""
        # Arrêter les animations
        self.is_thinking = False
        self.is_searching = False
        
        if hasattr(self, 'thinking_frame'):
            self.thinking_frame.grid_remove()
        
        # Cache aussi le texte en bas
        if hasattr(self, 'status_label'):
            self.status_label.configure(text="")
    
    def show_thinking_animation(self):
        """Affiche l'animation de réflexion seulement quand nécessaire"""
        self.is_thinking = True
        if hasattr(self, 'thinking_frame'):
            self.thinking_frame.grid(row=1, column=0, sticky="ew", padx=20, pady=(0, 10))
            self.animate_thinking()
    
    def show_search_animation(self):
        """Affiche l'animation de recherche seulement quand nécessaire"""
        self.is_searching = True
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
        """Gère la touche Entrée"""
        # Envoyer le message si c'est juste Entrée (sans Shift)
        if not event.state & 0x1:  # Pas de Shift pressé
            self.send_message()
            return "break"  # Empêche l'insertion d'une nouvelle ligne
        return None  # Permet l'insertion d'une nouvelle ligne avec Shift+Entrée
    
    def on_shift_enter(self, event):
        """Gère Shift+Entrée pour nouvelle ligne"""
        # Déjà géré dans on_enter_key
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
                "� Analyse contextuelle...",
                "⚡ Traitement neural en cours...",
                "🔍 Détection d'intentions...",
                "💡 Génération de réponse intelligente...",
                "🎯 Optimisation de la réponse...",
                "⚙️ Moteur de raisonnement actif...",
                "📊 Analyse des patterns...",
                "🚀 Finalisation de la réponse...",
                "🔮 Prédiction des besoins...",
                "💻 Processing linguistique avancé...",
                "� Calculs d'inférence...",
                "🎪 Préparation d'une réponse époustouflante..."
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
        """Envoie le message de l'utilisateur - AMÉLIORÉ"""
        message = self.input_text.get("1.0", "end-1c").strip()
        
        if not message:
            return
        
        # Cacher les indicateurs de statut
        self.hide_status_indicators()
        
        # Ajouter le message utilisateur
        self.add_message_bubble(message, is_user=True)
        
        # Effacer la zone de saisie
        self.input_text.delete("1.0", "end")
        
        # Scroll vers le bas
        self.scroll_to_bottom()
        
        # Afficher l'animation de réflexion
        self.show_thinking_animation()
        
        # Traitement en arrière-plan
        threading.Thread(
            target=self.process_user_message,
            args=(message,),
            daemon=True
        ).start()
    
    def process_user_message(self, message):
        """Traite le message utilisateur en arrière-plan"""
        
        def run_async_task():
            """Exécute la tâche asynchrone dans un thread séparé"""
            try:
                # Créer une nouvelle boucle d'événements pour ce thread
                import asyncio
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                # Exécuter la tâche asynchrone
                response = loop.run_until_complete(self.ai_engine.process_query(message))
                
                # Fermer la boucle
                loop.close()
                
                # Mettre à jour l'interface dans le thread principal
                self.root.after(0, self.hide_status_indicators)
                self.root.after(0, lambda r=response: self.add_ai_response(r))
                
            except Exception as e:
                self.logger.error(f"Erreur lors du traitement du message: {e}")
                self.root.after(0, self.hide_status_indicators)
                error_msg = f"❌ Erreur: {str(e)}"
                self.root.after(0, lambda msg=error_msg: self.add_ai_response(msg))
        
        # Lancer dans un thread séparé
        import threading
        threading.Thread(target=run_async_task, daemon=True).start()
    
    def add_ai_response(self, response):
        """Ajoute une réponse de l'IA"""
        # Extraire le texte de la réponse si c'est un dictionnaire
        if isinstance(response, dict):
            # Chercher différentes clés possibles pour le texte
            text_response = (response.get('response') or 
                           response.get('text') or 
                           response.get('content') or 
                           response.get('message') or 
                           str(response))
        else:
            text_response = str(response)
        
        self.add_message_bubble(text_response, is_user=False)
        self.scroll_to_bottom()
    
    def scroll_to_bottom(self):
        """Fait défiler vers le bas de la conversation (ROBUSTE et GARANTI)"""
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
                            parent.yview_moveto(1.0)
                            self.logger.debug("Scroll CTk via parent canvas")
                        elif hasattr(self.chat_frame, '_parent_canvas'):
                            # Méthode 2: Canvas direct
                            canvas = self.chat_frame._parent_canvas
                            canvas.update_idletasks()
                            canvas.yview_moveto(1.0)
                            self.logger.debug("Scroll CTk via _parent_canvas")
                        else:
                            self.logger.warning("Impossible de trouver canvas pour scroll CTk")
                    except Exception as e:
                        self.logger.error(f"Erreur scroll CTk: {e}")
            else:
                # Tkinter standard - Chercher le canvas scrollable
                try:
                    parent = self.chat_frame.master
                    if hasattr(parent, 'yview_moveto'):
                        parent.update_idletasks()
                        parent.yview_moveto(1.0)
                        self.logger.debug("Scroll tkinter via parent direct")
                    else:
                        # Chercher dans la hiérarchie
                        current = parent
                        while current:
                            if hasattr(current, 'yview_moveto'):
                                current.update_idletasks()
                                current.yview_moveto(1.0)
                                self.logger.debug("Scroll tkinter via hiérarchie")
                                break
                            current = current.master
                except Exception as e:
                    self.logger.error(f"Erreur scroll tkinter: {e}")
                    
            # Forcer une seconde tentative après délai court
            self.root.after(100, self._force_scroll_bottom)
            
        except Exception as e:
            self.logger.error(f"Erreur critique lors du scroll: {e}")
    
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
• **Conversations naturelles** et réponses à vos questions
• **Analyse de documents** PDF et DOCX
• **Génération et analyse de code**
• **Recherche internet** avec résumés intelligents

**Commencez** par me dire bonjour ou posez-moi directement une question !"""
        
        # Utiliser la même fonction que pour les autres messages IA
        self.add_message_bubble(welcome_text, is_user=False, message_type="text")
    
    def show_help(self):
        """Affiche l'aide"""
        help_text = """**🆘 Aide - My Personal AI**

**📝 Comment utiliser :**
• Tapez votre message et appuyez sur Entrée
• Utilisez Shift+Entrée pour un saut de ligne
• Glissez des fichiers ou utilisez les boutons PDF/DOCX/Code

**💬 Exemples de messages :**
• "Bonjour" - Salutation
• "Résume ce document" - Analyse de fichier
• "Génère une fonction Python" - Création de code
• "Cherche sur internet les actualités IA" - Recherche web

**🎯 Fonctionnalités :**
• **Effacer** : Bouton "Clear Chat" pour recommencer
• **Fichiers** : Boutons de chargement

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
        """Initialise l'IA en arrière-plan"""
        def init_ai():
            try:
                # Initialiser les composants IA
                self.logger.info("Initialisation de l'IA en cours...")
                
                # Mettre à jour le statut
                self.root.after(0, lambda: self.status_label.configure(text_color='#ffff00'))  # Jaune = initialisation
                
                # Attendre l'initialisation
                time.sleep(2)
                
                # Statut connecté
                self.root.after(0, lambda: self.status_label.configure(text_color='#00ff00'))  # Vert = connecté
                
                self.logger.info("IA initialisée avec succès")
                
            except Exception as e:
                self.logger.error(f"Erreur d'initialisation IA: {e}")
                self.root.after(0, lambda: self.status_label.configure(text_color='#ff0000'))  # Rouge = erreur
        
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
