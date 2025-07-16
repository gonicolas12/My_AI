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
            # Fallback amélioré avec des tailles plus grandes
            sizes = {
                'title': 28,
                'subtitle': 16,
                'body': 14,
                'small': 12,
                'chat': 15,
                'code': 13,
                'message': 15,
                'bold': 15
            }
            # Créer style_config même en fallback
            self.style_config = {
                'large_screen': {
                    'title': 32, 'subtitle': 18, 'body': 14, 'small': 12,
                    'chat': 15, 'code': 13, 'message': 15, 'bold': 15
                },
                'medium_screen': {
                    'title': 28, 'subtitle': 16, 'body': 13, 'small': 11,
                    'chat': 14, 'code': 12, 'message': 14, 'bold': 14
                },
                'small_screen': {
                    'title': 24, 'subtitle': 14, 'body': 12, 'small': 10,
                    'chat': 13, 'code': 11, 'message': 13, 'bold': 13
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
                font=('Segoe UI', 12, 'bold'),
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
                font=('Segoe UI', 12, 'bold')
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
        
        # Logo/Icône
        logo_label = self.create_label(
            header_frame, 
            text="🤖", 
            font=('Segoe UI', 28),
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
        
        # Indicateur de statut
        self.status_label = self.create_label(
            buttons_frame,
            text="●",
            font=('Segoe UI', 16),
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
            font=self.fonts['body'],
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
                font=self.fonts['chat']
            )
        else:
            self.input_text = tk.Text(
                input_wrapper,
                height=3,
                fg_color=self.colors['input_bg'],
                fg=self.colors['text_primary'],
                font=self.fonts['chat'],
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
                font=self.fonts['body'],
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
                font=self.fonts['body'],
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
        msg_container.grid(row=len(self.conversation_history)-1, column=0, sticky="ew", pady=(0, 15))  # REDUCED spacing
        msg_container.grid_columnconfigure(0, weight=1)
        
        if is_user:
            # MESSAGE UTILISATEUR - AVEC BULLE (sans scroll)
            self.create_user_message_bubble(msg_container, text)
        else:
            # RÉPONSE IA - SANS BULLE (sans scroll) 
            self.create_ai_message_simple(msg_container, text)
        
        # Scroll automatique vers le bas
        self.root.after(100, self.scroll_to_bottom)
    
    def create_user_message_bubble(self, parent, text):
        """Crée une bulle de message utilisateur - CENTRÉ avec alignement parfait"""
        # Frame principale DÉCALÉE comme avant (400px de la gauche)
        main_frame = self.create_frame(parent, fg_color=self.colors['bg_chat'])
        main_frame.grid(row=0, column=0, padx=(400, 0), pady=0, sticky="w")  # RETOUR au décalage original
        main_frame.grid_columnconfigure(0, weight=0)  # Icône fixe
        main_frame.grid_columnconfigure(1, weight=0)  # Bulle fixe
        
        # Icône utilisateur à GAUCHE (comme avant)
        icon_label = self.create_label(
            main_frame,
            text="👤",
            font=('Segoe UI', 16),
            fg_color=self.colors['bg_chat'],
            text_color=self.colors['text_primary']
        )
        icon_label.grid(row=0, column=0, sticky="nw", padx=(0, 15), pady=(5, 0))
        
        # Calculer la largeur de bulle adaptative
        lines = text.split('\n')
        max_line_length = max(len(line) for line in lines) if lines else len(text)
        
        if max_line_length <= 5:
            bubble_width = 80
        elif max_line_length <= 15:
            bubble_width = max(100, max_line_length * 7)
        elif max_line_length <= 30:
            bubble_width = max(140, max_line_length * 6)
        elif max_line_length <= 50:
            bubble_width = max(200, max_line_length * 5)
        else:
            bubble_width = min(400, max_line_length * 4)
        
        if len(lines) > 1:
            bubble_width = max(bubble_width, 150)
        
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
        
        bubble.grid(row=0, column=1, sticky="w", padx=0, pady=(5, 5))  # ALIGNÉ avec l'icône
        bubble.grid_columnconfigure(0, weight=1)
        
        # TEXTE SÉLECTIONNABLE avec TextBox SANS SCROLL interne
        current_font_size = self.get_current_font_size('message')
        
        if self.use_ctk:
            # CTkTextbox SÉLECTIONNABLE sans scroll
            text_widget = ctk.CTkTextbox(
                bubble,
                width=bubble_width - 16,
                height=1,  # Sera ajusté automatiquement
                fg_color="transparent",
                text_color='#ffffff',
                font=('Segoe UI', current_font_size),
                wrap="word",
                state="normal"
            )
            
            # Insérer le texte avec formatage gras
            text_widget.delete("1.0", "end")
            self.insert_formatted_text_ctk(text_widget, text)
            text_widget.configure(state="disabled")  # Lecture seule mais sélectionnable
            
            # DÉSACTIVER COMPLÈTEMENT LE SCROLL INTERNE
            text_widget.bind("<MouseWheel>", lambda e: "break")
            text_widget.bind("<Button-4>", lambda e: "break")  # Linux
            text_widget.bind("<Button-5>", lambda e: "break")  # Linux
            text_widget.bind("<Key-Up>", lambda e: "break")
            text_widget.bind("<Key-Down>", lambda e: "break")
            text_widget.bind("<Key-Prior>", lambda e: "break")  # Page Up
            text_widget.bind("<Key-Next>", lambda e: "break")   # Page Down
            
            # PERMETTRE LA SÉLECTION en cliquant
            def enable_selection(event):
                text_widget.configure(state="normal")
                # Repositionner le curseur où l'utilisateur a cliqué
                text_widget.mark_set("insert", text_widget.index(f"@{event.x},{event.y}"))
                return "break"
            
            text_widget.bind("<Button-1>", enable_selection)
            
        else:
            # Text widget tkinter SÉLECTIONNABLE sans scroll
            text_widget = tk.Text(
                bubble,
                width=(bubble_width - 16) // 8,
                height=1,
                bg=self.colors['bg_user'],
                fg='#ffffff',
                font=('Segoe UI', current_font_size),
                wrap="word",
                relief="flat",
                bd=0,
                highlightthickness=0,
                state="normal"
            )
            
            # Insérer le texte avec formatage gras
            text_widget.delete("1.0", "end")
            self.insert_formatted_text_tkinter(text_widget, text)
            text_widget.configure(state="disabled")
            
            # DÉSACTIVER LE SCROLL INTERNE
            text_widget.bind("<MouseWheel>", lambda e: "break")
            text_widget.bind("<Button-4>", lambda e: "break")
            text_widget.bind("<Button-5>", lambda e: "break")
            text_widget.bind("<Key-Up>", lambda e: "break")
            text_widget.bind("<Key-Down>", lambda e: "break")
            text_widget.bind("<Key-Prior>", lambda e: "break")
            text_widget.bind("<Key-Next>", lambda e: "break")
            
            # PERMETTRE LA SÉLECTION
            def enable_selection(event):
                text_widget.configure(state="normal")
                return "break"
            
            text_widget.bind("<Button-1>", enable_selection)
        
        text_widget.grid(row=0, column=0, padx=8, pady=(6, 2), sticky="nw")  # REDUCED bottom padding
        
        # Ajuster la hauteur selon le contenu APRÈS insertion
        self.root.after(50, lambda: self.adjust_text_height_no_scroll(text_widget, text))
        
        # Menu contextuel pour copier
        self.create_copy_menu(text_widget, text)
        
        # Timestamp PROCHE de la bulle - RÉDUIT L'ESPACEMENT
        timestamp = datetime.now().strftime("%H:%M")
        time_label = self.create_label(
            main_frame,
            text=timestamp,
            font=('Segoe UI', 8),
            fg_color=self.colors['bg_chat'],
            text_color=self.colors['text_secondary']
        )
        time_label.grid(row=1, column=1, sticky="w", padx=(8, 0), pady=(0, 0))  # REDUCED padding
    
    def create_ai_message_simple(self, parent, text):
        """Crée un message IA simple sans bulle - CENTRÉ avec même alignement"""
        # Frame de centrage IDENTIQUE au décalage utilisateur (400px)
        center_frame = self.create_frame(parent, fg_color=self.colors['bg_chat'])
        center_frame.grid(row=0, column=0, padx=(400, 0), pady=0, sticky="w")  # MÊME décalage que l'utilisateur
        center_frame.grid_columnconfigure(0, weight=0)  # Icône fixe
        center_frame.grid_columnconfigure(1, weight=1)  # Zone de texte extensible
        
        # Icône IA à position IDENTIQUE à l'utilisateur
        icon_label = self.create_label(
            center_frame,
            text="🤖",
            font=('Segoe UI', 16),
            fg_color=self.colors['bg_chat'],
            text_color=self.colors['accent']
        )
        icon_label.grid(row=0, column=0, sticky="nw", padx=(0, 15), pady=(5, 0))  # MÊME position que l'utilisateur
        
        # Zone de texte IA SÉLECTIONNABLE sans scroll
        current_font_size = self.get_current_font_size('message')
        max_width = min(600, self.root.winfo_width() - 300) if self.root.winfo_width() > 300 else 500
        
        if self.use_ctk:
            # CTkTextbox SÉLECTIONNABLE sans scroll
            text_widget = ctk.CTkTextbox(
                center_frame,
                width=max_width,
                height=1,  # Sera ajusté automatiquement
                fg_color=self.colors['bg_chat'],
                text_color=self.colors['text_primary'],
                font=('Segoe UI', current_font_size),
                wrap="word",
                state="normal"
            )
            
            # Insérer le texte avec formatage gras
            text_widget.delete("1.0", "end")
            self.insert_formatted_text_ctk(text_widget, text)
            text_widget.configure(state="disabled")  # Lecture seule mais sélectionnable
            
            # DÉSACTIVER COMPLÈTEMENT LE SCROLL INTERNE
            text_widget.bind("<MouseWheel>", lambda e: "break")
            text_widget.bind("<Button-4>", lambda e: "break")
            text_widget.bind("<Button-5>", lambda e: "break")
            text_widget.bind("<Key-Up>", lambda e: "break")
            text_widget.bind("<Key-Down>", lambda e: "break")
            text_widget.bind("<Key-Prior>", lambda e: "break")
            text_widget.bind("<Key-Next>", lambda e: "break")
            
            # PERMETTRE LA SÉLECTION
            def enable_selection(event):
                text_widget.configure(state="normal")
                text_widget.mark_set("insert", text_widget.index(f"@{event.x},{event.y}"))
                return "break"
            
            text_widget.bind("<Button-1>", enable_selection)
            
        else:
            # Text widget tkinter SÉLECTIONNABLE sans scroll
            text_widget = tk.Text(
                center_frame,
                width=(max_width - 20) // 8,
                height=1,
                bg=self.colors['bg_chat'],
                fg=self.colors['text_primary'],
                font=('Segoe UI', current_font_size),
                wrap="word",
                relief="flat",
                bd=0,
                highlightthickness=0,
                state="normal"
            )
            
            # Insérer le texte avec formatage gras
            text_widget.delete("1.0", "end")
            self.insert_formatted_text_tkinter(text_widget, text)
            text_widget.configure(state="disabled")
            
            # DÉSACTIVER LE SCROLL INTERNE
            text_widget.bind("<MouseWheel>", lambda e: "break")
            text_widget.bind("<Button-4>", lambda e: "break")
            text_widget.bind("<Button-5>", lambda e: "break")
            text_widget.bind("<Key-Up>", lambda e: "break")
            text_widget.bind("<Key-Down>", lambda e: "break")
            text_widget.bind("<Key-Prior>", lambda e: "break")
            text_widget.bind("<Key-Next>", lambda e: "break")
            
            # PERMETTRE LA SÉLECTION
            def enable_selection(event):
                text_widget.configure(state="normal")
                return "break"
            
            text_widget.bind("<Button-1>", enable_selection)
        
        text_widget.grid(row=0, column=1, sticky="w", padx=(0, 0), pady=(5, 2))  # REDUCED bottom padding
        
        # Ajuster la hauteur selon le contenu
        self.root.after(50, lambda: self.adjust_text_height_no_scroll(text_widget, text))
        
        # Menu contextuel pour copier
        self.create_copy_menu(text_widget, text)
        
        # Timestamp PROCHE du texte - RÉDUIT L'ESPACEMENT
        timestamp = datetime.now().strftime("%H:%M")
        time_label = self.create_label(
            center_frame,
            text=timestamp,
            font=('Segoe UI', 8),
            fg_color=self.colors['bg_chat'],
            text_color=self.colors['text_secondary']
        )
        time_label.grid(row=1, column=1, sticky="w", padx=(0, 0), pady=(0, 0))  # REMOVED padding

    def start_text_selection(self, widget, text, event):
        """Démarre la sélection de texte sur un label"""
        # Stocker les informations de sélection
        self.selection_widget = widget
        self.selection_text = text
        self.selection_start = event.x, event.y
        
    def continue_text_selection(self, event):
        """Continue la sélection de texte"""
        # Mise à jour visuelle de la sélection (optionnel)
        pass
        
    def end_text_selection(self, text):
        """Termine la sélection et copie automatiquement le texte sélectionné"""
        try:
            # Copier automatiquement le texte complet dans le presse-papiers
            self.root.clipboard_clear()
            self.root.clipboard_append(text)
            # Notification discrète
            print(f"✅ Texte copié: {text[:50]}...")
        except Exception as e:
            print(f"❌ Erreur copie: {e}")

    def adjust_text_height_selectable(self, text_widget, text):
        """NOUVELLE VERSION : Ajuste la hauteur pour texte sélectionnable SANS SCROLL"""
        try:
            if self.use_ctk:
                # Pour CustomTkinter CTkTextbox - CALCUL TRÈS PRÉCIS
                text_widget.update_idletasks()
                
                # Compter les lignes avec wrapping précis
                lines = text.split('\n')
                total_display_lines = 0
                
                # Largeur de widget disponible
                try:
                    widget_width = text_widget.winfo_width()
                    if widget_width <= 50:
                        widget_width = 350  # Largeur par défaut pour bulle
                    
                    # Caractères par ligne (estimation précise)
                    chars_per_line = max(30, (widget_width - 25) // 8)  # -25 pour padding bulle
                    
                    for line in lines:
                        if len(line) == 0:
                            total_display_lines += 1
                        else:
                            # Calcul précis du nombre de lignes après wrap
                            wrapped_lines = max(1, (len(line) + chars_per_line - 1) // chars_per_line)
                            total_display_lines += wrapped_lines
                            
                except Exception:
                    # Fallback conservateur
                    total_display_lines = len(lines) * 2
                
                # Calcul hauteur GÉNÉREUSE pour bulles utilisateur
                line_height = 18  # Lignes plus compactes pour bulles
                padding = 20      # Padding pour bulle
                min_height = 30   # Hauteur minimale bulle
                max_height = 600  # Maximum pour une bulle
                
                calculated_height = max(min_height, min(total_display_lines * line_height + padding, max_height))
                
                # MARGE DE SÉCURITÉ 25% pour éviter tout scroll
                calculated_height = int(calculated_height * 1.25)
                
                text_widget.configure(height=calculated_height)
                
            else:
                # Pour tkinter standard Text
                text_widget.update_idletasks()
                
                current_state = text_widget.cget("state")
                text_widget.configure(state="normal")
                
                # Compter lignes après wrap
                line_count = int(text_widget.index("end-1c").split('.')[0])
                
                text_widget.configure(state=current_state)
                
                # Hauteur généreuse pour éviter scroll
                height = max(2, min(line_count + 2, 25))  # +2 de marge
                text_widget.configure(height=height)
                
        except Exception as e:
            # Hauteur par défaut généreuse
            if self.use_ctk:
                text_widget.configure(height=60)
            else:
                text_widget.configure(height=3)
    
    def insert_formatted_text_tkinter(self, text_widget, text):
        """Insère du texte formaté avec VRAI gras dans tkinter Text"""
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

    def adjust_text_height_no_scroll(self, text_widget, text):
        """NOUVELLE VERSION : Ajuste la hauteur pour afficher TOUT le contenu sans JAMAIS avoir besoin de scroll"""
        try:
            if self.use_ctk:
                # Pour CustomTkinter CTkTextbox - CALCUL PRÉCIS
                text_widget.update_idletasks()
                
                # Compter les lignes réelles avec calcul précis du wrapping
                lines = text.split('\n')
                total_display_lines = 0
                
                # Calculer largeur disponible
                try:
                    widget_width = text_widget.winfo_width()
                    if widget_width <= 50:  # Si pas encore affiché, utiliser largeur par défaut
                        widget_width = 400  # Largeur par défaut
                    
                    # Estimation plus précise : caractères par ligne
                    chars_per_line = max(35, (widget_width - 30) // 8)  # -30 pour padding
                    
                    for line in lines:
                        if len(line) == 0:
                            total_display_lines += 1  # Ligne vide compte pour 1
                        else:
                            # Calculer combien de lignes cette ligne va occuper avec le wrap
                            wrapped_lines = max(1, (len(line) + chars_per_line - 1) // chars_per_line)
                            total_display_lines += wrapped_lines
                except Exception as e:
                    # Fallback simple si erreur de calcul
                    total_display_lines = len(lines) * 2  # Estimation conservatrice
                
                # Calculer hauteur en pixels - GÉNÉREUSE pour éviter tout scroll
                line_height = 20  # Hauteur d'une ligne de texte
                padding = 25      # Padding généreaux
                min_height = 35   # Hauteur minimale
                max_height = 800  # Hauteur maximale raisonnable
                
                calculated_height = max(min_height, min(total_display_lines * line_height + padding, max_height))
                
                # AJOUTER 20% de marge de sécurité pour éviter tout scroll
                calculated_height = int(calculated_height * 1.2)
                
                text_widget.configure(height=calculated_height)
                self.logger.debug(f"CTk hauteur ajustée: {calculated_height}px pour {total_display_lines} lignes")
                
            else:
                # Pour tkinter standard Text - CALCUL EN LIGNES
                text_widget.update_idletasks()
                
                # Compter les lignes réelles après insertion
                current_state = text_widget.cget("state")
                text_widget.configure(state="normal")
                
                # Mesurer le contenu affiché
                line_count = int(text_widget.index("end-1c").split('.')[0])
                
                # Ajouter marge de sécurité
                safe_height = max(2, line_count + 2)  # +2 lignes de marge
                max_height = 35  # Pas plus de 35 lignes
                
                final_height = min(safe_height, max_height)
                text_widget.configure(height=final_height)
                
                # Restaurer l'état
                text_widget.configure(state=current_state)
                
                self.logger.debug(f"Tkinter hauteur ajustée: {final_height} lignes")
                
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
        """Obtient la taille de police adaptée à l'écran"""
        screen_width = self.root.winfo_screenwidth()
        
        # Vérifier si style_config existe
        if hasattr(self, 'style_config') and self.style_config:
            if screen_width >= 1600:
                return self.style_config['large_screen'].get(font_type, 15)
            elif screen_width >= 1200:
                return self.style_config['medium_screen'].get(font_type, 14)
            else:
                return self.style_config['small_screen'].get(font_type, 13)
        else:
            # Fallback si style_config n'existe pas
            if screen_width >= 1600:
                return {'title': 32, 'subtitle': 18, 'body': 14, 'small': 12, 'message': 15, 'bold': 15}.get(font_type, 15)
            elif screen_width >= 1200:
                return {'title': 28, 'subtitle': 16, 'body': 13, 'small': 11, 'message': 14, 'bold': 14}.get(font_type, 14)
            else:
                return {'title': 24, 'subtitle': 14, 'body': 12, 'small': 10, 'message': 13, 'bold': 13}.get(font_type, 13)
    
    def insert_formatted_text_ctk(self, text_widget, text):
        """Insère du texte formaté avec gras dans CustomTkinter TextBox"""
        import re
        
        text_widget.delete("1.0", "end")
        
        # Configurer les tags pour le formatage
        current_font_size = self.get_current_font_size('message')
        
        # Pattern pour détecter **texte en gras**
        pattern = r'\*\*([^*]+)\*\*'
        
        # Diviser le texte en parties normales et en gras
        parts = re.split(pattern, text)
        
        for i, part in enumerate(parts):
            if i % 2 == 0:  # Texte normal
                if part:
                    text_widget.insert("end", part)
            else:  # Texte en gras (simulé avec majuscules pour CTk)
                if part:
                    # CustomTkinter ne supporte pas le gras dans TextBox, utiliser MAJUSCULES
                    text_widget.insert("end", part.upper())
    
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
        """Animation de réflexion de l'IA"""
        if hasattr(self, 'thinking_label') and self.is_thinking:
            # Animations de points qui bougent
            animations = [
                "🤖 L'IA réfléchit",
                "🤖 L'IA réfléchit.",
                "🤖 L'IA réfléchit..",
                "🤖 L'IA réfléchit..."
            ]
            
            self.thinking_dots = (self.thinking_dots + 1) % len(animations)
            self.thinking_label.configure(text=animations[self.thinking_dots])
            
            # Continuer l'animation toutes les 500ms
            self.root.after(500, self.animate_thinking)
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
    
    def clean_text_for_label(self, text):
        """
        AMÉLIORATION : Convertit le texte avec **gras** en utilisant des caractères Unicode 
        ET gère les longs textes pour éviter les débordements
        """
        import re
        
        def to_bold_unicode(match):
            bold_text = match.group(1)
            bold_chars = ""
            for char in bold_text:
                if 'A' <= char <= 'Z':
                    bold_chars += chr(ord(char) - ord('A') + ord('𝐀'))
                elif 'a' <= char <= 'z':
                    bold_chars += chr(ord(char) - ord('a') + ord('𝐚'))
                elif '0' <= char <= '9':
                    bold_chars += chr(ord(char) - ord('0') + ord('𝟎'))
                else:
                    bold_chars += char
            return bold_chars
        
        # Remplacer **texte** par du texte en gras Unicode
        pattern = r'\*\*([^*]+)\*\*'
        formatted_text = re.sub(pattern, to_bold_unicode, text)
        
        # NOUVEAU : Gestion des très longs textes
        lines = formatted_text.split('\n')
        processed_lines = []
        
        for line in lines:
            # Si une ligne est très longue, essayer de la découper intelligemment
            if len(line) > 100:
                # Découper aux espaces les plus proches
                words = line.split(' ')
                current_line = ""
                
                for word in words:
                    if len(current_line + " " + word) <= 100:
                        current_line += " " + word if current_line else word
                    else:
                        if current_line:
                            processed_lines.append(current_line)
                            current_line = word
                        else:
                            # Mot trop long, le garder tel quel
                            processed_lines.append(word)
                            current_line = ""
                
                if current_line:
                    processed_lines.append(current_line)
            else:
                processed_lines.append(line)
        
        return '\n'.join(processed_lines)

    def create_context_menu_for_label(self, label_widget, text_content):
        """Crée un menu contextuel pour copier le texte d'un label"""
        def copy_text():
            try:
                self.root.clipboard_clear()
                self.root.clipboard_append(text_content)
                # Notification temporaire
                self.show_notification("📋 Texte copié dans le presse-papiers", "success")
            except Exception as e:
                self.show_notification(f"❌ Erreur lors de la copie: {e}", "error")
        
        def copy_selection():
            # Pour une future implémentation de sélection
            copy_text()
        
        # Créer le menu contextuel
        context_menu = tk.Menu(self.root, tearoff=0)
        context_menu.add_command(label="📋 Copier tout le texte", command=copy_text)
        context_menu.add_separator()
        context_menu.add_command(label="🔍 Sélectionner tout", command=copy_selection)
        
        def show_context_menu(event):
            try:
                context_menu.tk_popup(event.x_root, event.y_root)
            except Exception:
                pass
        
        # Bind du clic droit
        label_widget.bind("<Button-3>", show_context_menu)  # Windows/Linux
        label_widget.bind("<Button-2>", show_context_menu)  # macOS
        
        return context_menu
   
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
        """Fait défiler vers le bas de la conversation"""
        try:
            if self.use_ctk:
                # Pour CustomTkinter avec CTkScrollableFrame
                if hasattr(self, 'chat_frame') and hasattr(self.chat_frame, '_parent_canvas'):
                    # Forcer la mise à jour de la géométrie
                    self.chat_frame.update_idletasks()
                    self.root.update_idletasks()
                    
                    # Scroller vers le bas en utilisant la méthode interne de CTkScrollableFrame
                    canvas = self.chat_frame._parent_canvas
                    canvas.update_idletasks()
                    canvas.yview_moveto(1.0)
                    
                elif hasattr(self, 'chat_frame'):
                    # Méthode alternative si _parent_canvas n'est pas accessible
                    self.chat_frame.update_idletasks()
                    self.root.update_idletasks()
            else:
                # Pour tkinter standard avec Canvas
                if hasattr(self, 'canvas'):
                    self.canvas.update_idletasks()
                    self.canvas.yview_moveto(1.0)
                    
        except Exception as e:
            self.logger.error(f"Erreur lors du scroll: {e}")
            # Fallback silencieux - ne pas bloquer l'interface

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
            
            self.logger.info("Conversation effacée")
            
        except Exception as e:
            self.logger.error(f"Erreur lors de l'effacement: {e}")
            messagebox.showerror("Erreur", f"Impossible d'effacer la conversation: {e}")
    
    def show_welcome_message(self):
        """Affiche le message de bienvenue"""
        welcome_text = """Bonjour ! Je suis votre **Assistant IA Local** 🤖

Je peux vous aider avec :
• **Conversations naturelles** et réponses à vos questions
• **Analyse de documents** PDF et DOCX
• **Génération et analyse de code**
• **Recherche internet** avec résumés intelligents

**Commencez** par me dire bonjour ou posez-moi directement une question !"""
        
        self.add_message_bubble(welcome_text, is_user=False)
    
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
• **Texte en gras** : Entourez avec **deux astérisques**
• **Effacer** : Bouton "Clear Chat" pour recommencer
• **Fichiers** : Drag & drop ou boutons de chargement

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
