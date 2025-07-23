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
        """Version avec espacement OPTIMAL et structure améliorée"""
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
        
        print(f"🔍 DEBUG add_message_bubble: is_user={is_user}, text_length={len(text)}, preview='{text[:50]}...'")
        
        # Ajouter à l'historique
        self.conversation_history.append({
            'text': text,
            'is_user': is_user,
            'timestamp': datetime.now(),
            'type': message_type
        })
        
        # Container principal avec espacement OPTIMAL
        msg_container = self.create_frame(self.chat_frame, fg_color=self.colors['bg_chat'])
        # 🎯 ESPACEMENT OPTIMAL - PAS TROP, PAS TROP PEU : 20px → 12px
        msg_container.grid(row=len(self.conversation_history)-1, column=0, sticky="ew", pady=(0, 12))
        msg_container.grid_columnconfigure(0, weight=1)

        if is_user:
            self.create_user_message_bubble(msg_container, text)
        else:
            self.create_ai_message_simple(msg_container, text)

        # Scroll automatique vers le bas
        self.root.after(10, self.scroll_to_bottom)
    
    def setup_scroll_forwarding(self, text_widget):
        """Configure le transfert du scroll pour les widgets de texte - VITESSE NATIVE"""
        def forward_scroll_to_page(event):
            try:
                # Méthode améliorée : transfert direct d'événement pour vitesse native
                if hasattr(self, 'chat_frame') and hasattr(self.chat_frame, '_parent_canvas'):
                    # Pour CustomTkinter ScrollableFrame - transfert direct
                    canvas = self.chat_frame._parent_canvas
                    canvas.event_generate("<MouseWheel>", delta=event.delta, x=event.x, y=event.y)
                elif hasattr(self, 'chat_frame'):
                    # Pour tkinter standard - chercher le parent scrollable et transférer directement
                    parent = self.chat_frame.master
                    while parent and not hasattr(parent, 'yview'):
                        parent = parent.master
                    if parent and hasattr(parent, 'yview'):
                        # Transfert avec vitesse multipliée pour compenser
                        scroll_delta = int(-1 * (event.delta / 40))  # Plus sensible (120 -> 40)
                        parent.yview_scroll(scroll_delta, "units")
            except Exception as e:
                print(f"⚠️ Erreur transfert scroll: {e}")
                pass
            return "break"
        
        # Appliquer le transfert de scroll
        text_widget.bind("<MouseWheel>", forward_scroll_to_page)
        text_widget.bind("<Button-4>", forward_scroll_to_page)  # Linux
        text_widget.bind("<Button-5>", forward_scroll_to_page)  # Linux
        
        # Désactiver seulement les touches de navigation
        def disable_keyboard_scroll(event):
            return "break"
        
        text_widget.bind("<Up>", disable_keyboard_scroll)
        text_widget.bind("<Down>", disable_keyboard_scroll)
        text_widget.bind("<Prior>", disable_keyboard_scroll)
        text_widget.bind("<Next>", disable_keyboard_scroll)

    def create_user_message_bubble(self, parent, text):
        """Version PARFAITE - Affichage complet garanti + notification GUI"""
        from datetime import datetime
        
        # Frame principale - RETOUR au centrage original
        main_frame = self.create_frame(parent, fg_color=self.colors['bg_chat'])
        main_frame.grid(row=0, column=0, padx=(400, 400), pady=(0, 0), sticky="ew")
        main_frame.grid_columnconfigure(0, weight=0)
        main_frame.grid_columnconfigure(1, weight=1)  # Permettre expansion du contenu
        
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
        
        # Largeur fixe plus large pour les longs messages, pour forcer le retour à la ligne et permettre plus de hauteur
        max_width = 120
        min_width = 60
        lines = text.split('\n')
        longest_line = max(lines, key=len) if lines else text
        words = text.split()
        word_count = len(words)
        # Pour les très longs messages, largeur maximale
        if word_count > 40 or len(longest_line) > 100:
            text_width = max_width
        else:
            text_width = min(max_width, max(min_width, len(longest_line) + 10))

        # Créer le widget texte avec un scroll vertical si besoin
        text_widget = tk.Text(
            bubble,
            width=text_width,
            height=10,  # Valeur initiale, ajustée après
            bg=self.colors['bg_user'],
            fg='#ffffff',
            font=('Segoe UI', 12),
            wrap=tk.WORD,
            relief="flat",
            bd=0,
            highlightthickness=0,
            state="normal",
            cursor="arrow",
            yscrollcommand=None,
            xscrollcommand=None
        )

        # Insérer le texte
        self.insert_formatted_text_tkinter(text_widget, text)

        # Calculer le nombre de lignes affichées après wrapping
        text_widget.update_idletasks()
        text_widget.update()
        try:
            total_pixels = text_widget.dlineinfo('end-1c')[1] if text_widget.dlineinfo('end-1c') else 0
            line_height = text_widget.dlineinfo('1.0')[3] if text_widget.dlineinfo('1.0') else 20
            widget_height = text_widget.winfo_height()
            # Nombre de lignes visibles (approx)
            num_lines = int(text_widget.index('end-1c').split('.')[0])
            # Pour les très longs textes, forcer une hauteur max et ajouter un scroll vertical
            max_height = 25
            final_height = min(max_height, num_lines + 2)
            text_widget.configure(height=final_height)
            text_widget.update_idletasks()
            text_widget.update()
            text_widget.see('1.0')
            text_widget.mark_set('insert', '1.0')
            print(f"📏 USER: final_height={final_height}, num_lines={num_lines}")
        except Exception as e:
            print(f"⚠️ Erreur ajustement user: {e}")
            safe_height = min(25, max(3, len(text.split('\n')) + 2))
            text_widget.configure(height=safe_height)
            text_widget.update()
        text_widget.configure(state="disabled")
        self.setup_scroll_forwarding(text_widget)
        
        # COPIE avec notification GUI
        def copy_on_double_click(event):
            try:
                self.root.clipboard_clear()
                self.root.clipboard_append(text)
                # NOTIFICATION GUI au lieu de juste terminal
                self.show_copy_notification("✅ Message copié !")
            except Exception as e:
                self.show_copy_notification("❌ Erreur de copie")
            return "break"
        
        text_widget.bind("<Double-Button-1>", copy_on_double_click)
        
        # Positionner le widget
        text_widget.grid(row=0, column=0, padx=8, pady=(6, 0), sticky="nw")
        
        # TIMESTAMP (plus proche du message)
        timestamp = datetime.now().strftime("%H:%M")
        time_label = self.create_label(
            bubble,
            text=timestamp,
            font=('Segoe UI', 10),
            fg_color=self.colors['bg_user'],
            text_color='#b3b3b3'
        )
        time_label.grid(row=1, column=0, sticky="w", padx=8, pady=(0, 6))
        
        # Menu contextuel avec notification GUI
        self.create_copy_menu_with_notification(text_widget, text)


    def create_ai_message_simple(self, parent, text):
        """Version PARFAITE - Messages IA affichage complet + notification GUI"""
        from datetime import datetime
        
        # Frame de centrage - RETOUR au centrage original  
        center_frame = self.create_frame(parent, fg_color=self.colors['bg_chat'])
        center_frame.grid(row=0, column=0, padx=(400, 400), pady=(0, 0), sticky="ew")
        center_frame.grid_columnconfigure(0, weight=0)
        center_frame.grid_columnconfigure(1, weight=1)  # Permettre expansion du contenu
        
        # Icône IA
        icon_label = self.create_label(
            center_frame,
            text="🤖",
            font=('Segoe UI', 16),
            fg_color=self.colors['bg_chat'],
            text_color=self.colors['accent']
        )
        icon_label.grid(row=0, column=0, sticky="nw", padx=(0, 10), pady=(1, 0))
        
        # Container pour le message IA avec expansion
        message_container = self.create_frame(center_frame, fg_color=self.colors['bg_chat'])
        message_container.grid(row=0, column=1, sticky="ew", padx=0, pady=(2, 2))
        message_container.grid_columnconfigure(0, weight=1)  # Permettre expansion
        
        # Largeur fixe plus large pour les longs messages, pour forcer le retour à la ligne et permettre plus de hauteur
        max_width = 125
        min_width = 60
        lines = text.split('\n')
        longest_line = max(lines, key=len) if lines else text
        words = text.split()
        word_count = len(words)
        if word_count > 60 or len(longest_line) > 120:
            text_width = max_width
        else:
            text_width = min(max_width, max(min_width, len(longest_line) + 10))

        text_widget = tk.Text(
            message_container,
            width=text_width,
            height=10,  # Valeur initiale, ajustée après
            bg=self.colors['bg_chat'],
            fg=self.colors['text_primary'],
            font=('Segoe UI', 12),
            wrap=tk.WORD,
            relief="flat",
            bd=0,
            highlightthickness=0,
            state="normal",
            cursor="arrow",
            yscrollcommand=None,
            xscrollcommand=None
        )

        self.insert_formatted_text_tkinter(text_widget, text)

        text_widget.update_idletasks()
        text_widget.update()
        try:
            total_pixels = text_widget.dlineinfo('end-1c')[1] if text_widget.dlineinfo('end-1c') else 0
            line_height = text_widget.dlineinfo('1.0')[3] if text_widget.dlineinfo('1.0') else 20
            widget_height = text_widget.winfo_height()
            num_lines = int(text_widget.index('end-1c').split('.')[0])
            max_height = 30
            final_height = min(max_height, num_lines + 2)
            text_widget.configure(height=final_height)
            text_widget.update_idletasks()
            text_widget.update()
            text_widget.see('1.0')
            text_widget.mark_set('insert', '1.0')
            print(f"📏 IA: final_height={final_height}, num_lines={num_lines}")
        except Exception as e:
            print(f"⚠️ Erreur ajustement IA: {e}")
            safe_height = min(30, max(3, len(text.split('\n')) + 2))
            text_widget.configure(height=safe_height)
            text_widget.update()
        text_widget.configure(state="disabled")
        self.setup_scroll_forwarding(text_widget)
        
        # COPIE avec notification GUI
        def copy_on_double_click(event):
            try:
                self.root.clipboard_clear()
                self.root.clipboard_append(text)
                # NOTIFICATION GUI au lieu de juste terminal
                self.show_copy_notification("✅ Message copié !")
            except Exception as e:
                self.show_copy_notification("❌ Erreur de copie")
            return "break"
        
        text_widget.bind("<Double-Button-1>", copy_on_double_click)
        
        # Positionner le widget
        text_widget.grid(row=0, column=0, padx=0, pady=(0, 0), sticky="nw")
        
        # TIMESTAMP (plus proche du message)
        timestamp = datetime.now().strftime("%H:%M")
        time_label = self.create_label(
            message_container,
            text=timestamp,
            font=('Segoe UI', 10),
            fg_color=self.colors['bg_chat'],
            text_color=self.colors['text_secondary']
        )
        time_label.grid(row=1, column=0, sticky="w", padx=0, pady=(0, 6))
        
        # Menu contextuel avec notification GUI
        self.create_copy_menu_with_notification(text_widget, text)

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
            print(f"⚠️ Erreur notification GUI: {e}")


    def create_copy_menu_with_notification(self, widget, original_text):
        """Menu contextuel avec notification GUI"""
        def copy_text():
            try:
                self.root.clipboard_clear()
                self.root.clipboard_append(original_text)
                self.show_copy_notification("📋 Texte copié !")
            except Exception as e:
                self.show_copy_notification("❌ Erreur de copie")
        
        # Menu contextuel
        context_menu = tk.Menu(self.root, tearoff=0)
        context_menu.add_command(label="📋 Copier", command=copy_text)
        
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
        """Version OPTIMISÉE pour formatage unifié avec hauteur précise"""
        import re
        text_widget.delete("1.0", "end")
        
        # POLICE UNIFIÉE ABSOLUE - même pour tous les styles
        BASE_FONT = ('Segoe UI', 12)
        
        # Configurer TOUS les tags avec la même taille de police de base
        text_widget.tag_configure("bold", font=('Segoe UI', 12, 'bold'))
        text_widget.tag_configure("italic", font=('Segoe UI', 12, 'italic'))
        text_widget.tag_configure("mono", font=('Consolas', 12))  # Même taille pour monospace
        text_widget.tag_configure("normal", font=BASE_FONT)
        
        # Traitement du formatage (même logique qu'avant)
        patterns = [
            (r'\*\*([^*]+)\*\*', 'bold'),
            (r'\*([^*]+)\*', 'italic'),
            (r'`([^`]+)`', 'mono')
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
        
        # Insérer les segments avec les tags appropriés
        for segment_text, style in segments:
            if segment_text:
                text_widget.insert("end", segment_text, style)
        
        # AJUSTEMENT HAUTEUR SIMPLE ET FINAL
        text_widget.update_idletasks()
        text_widget.update()
        
        try:
            # Calculer hauteur basée sur le contenu réel
            total_lines = int(text_widget.index("end-1c").split('.')[0])
            
            # Hauteur réelle + très petite marge
            required_height = max(1, total_lines)
            text_widget.configure(height=required_height)
            text_widget.update_idletasks()
            text_widget.update()
            
            # Retour au début pour un affichage propre
            text_widget.see("1.0")
            text_widget.mark_set("insert", "1.0")
            
            print(f"📏 Format: final_height={required_height}, total_lines={total_lines}")
            
        except Exception as e:
            print(f"⚠️ Erreur ajustement format: {e}")
            # Fallback simple
            fallback_height = max(2, len(text.split('\n')))
            text_widget.configure(height=fallback_height)

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
        """NOUVELLE VERSION - Taille de police unifiée pour tous les messages"""
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
        """Gère la touche Entrée - VERSION CORRIGÉE"""
        # Vérifier l'état de la touche Shift
        shift_pressed = bool(event.state & 0x1)
        
        if shift_pressed:
            # Shift+Entrée : insérer une nouvelle ligne (comportement par défaut)
            return None  # Laisser tkinter gérer l'insertion de nouvelle ligne
        else:
            # Entrée seule : envoyer le message
            try:
                self.send_message()
                return "break"  # Empêcher l'insertion d'une nouvelle ligne
            except Exception as e:
                print(f"❌ Erreur lors de l'envoi du message: {e}")
                return "break"
    
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
        """Envoie le message de l'utilisateur - VERSION AVEC DEBUG"""
        try:
            print("🔍 DEBUG: send_message appelé")
            
            # Récupérer le texte de l'input
            message = self.input_text.get("1.0", "end-1c").strip()
            print(f"🔍 DEBUG: Message récupéré: '{message}'")
            
            if not message:
                print("⚠️ DEBUG: Message vide, abandon")
                return
            
            # Cacher les indicateurs de statut
            self.hide_status_indicators()
            
            # Ajouter le message utilisateur
            print("🔍 DEBUG: Ajout du message utilisateur")
            self.add_message_bubble(message, is_user=True)
            
            # Effacer la zone de saisie
            self.input_text.delete("1.0", "end")
            print("🔍 DEBUG: Zone de saisie effacée")
            
            # Scroll vers le bas
            self.scroll_to_bottom()
            
            # Afficher l'animation de réflexion
            self.show_thinking_animation()
            print("🔍 DEBUG: Animation de réflexion lancée")
            
            # Traitement en arrière-plan
            print("🔍 DEBUG: Lancement du thread de traitement")
            threading.Thread(
                target=self.process_user_message,
                args=(message,),
                daemon=True
            ).start()
            
            print("✅ DEBUG: send_message terminé avec succès")
            
        except Exception as e:
            print(f"❌ ERROR: Erreur dans send_message: {e}")
            import traceback
            traceback.print_exc()
    
    def process_user_message(self, message):
        """Traite le message utilisateur en arrière-plan - VERSION AVEC DEBUG"""
        print(f"🔍 DEBUG: process_user_message démarré avec '{message}'")
        
        def run_async_task():
            """Exécute la tâche asynchrone dans un thread séparé"""
            try:
                print("🔍 DEBUG: run_async_task démarré")
                
                # Créer une nouvelle boucle d'événements pour ce thread
                import asyncio
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                print("🔍 DEBUG: Boucle asyncio créée")
                
                # Exécuter la tâche asynchrone
                print("🔍 DEBUG: Appel de ai_engine.process_query")
                response = loop.run_until_complete(self.ai_engine.process_query(message))
                print(f"🔍 DEBUG: Réponse reçue: {type(response)} - {str(response)[:100]}...")
                
                # Fermer la boucle
                loop.close()
                print("🔍 DEBUG: Boucle asyncio fermée")
                
                # Mettre à jour l'interface dans le thread principal
                self.root.after(0, self.hide_status_indicators)
                self.root.after(0, lambda r=response: self.add_ai_response(r))
                print("🔍 DEBUG: Réponse envoyée à l'interface")
                
            except Exception as e:
                print(f"❌ ERROR: Erreur dans run_async_task: {e}")
                import traceback
                traceback.print_exc()
                
                self.root.after(0, self.hide_status_indicators)
                error_msg = f"❌ Erreur: {str(e)}"
                self.root.after(0, lambda msg=error_msg: self.add_ai_response(msg))
        
        # Lancer dans un thread séparé
        import threading
        print("🔍 DEBUG: Création du thread pour run_async_task")
        threading.Thread(target=run_async_task, daemon=True).start()
    
    def add_ai_response(self, response):
        """Ajoute une réponse de l'IA - VERSION CORRIGÉE pour réponses complètes"""
        print(f"🔍 DEBUG add_ai_response: type={type(response)}, contenu={str(response)[:200]}...")
        
        # CORRECTION : Extraire correctement le texte de la réponse
        if isinstance(response, dict):
            # Chercher le message dans l'ordre de priorité
            if 'message' in response:
                text_response = response['message']
            elif 'text' in response:
                text_response = response['text']
            elif 'content' in response:
                text_response = response['content']
            elif 'response' in response:
                text_response = response['response']
            else:
                text_response = str(response)
        else:
            text_response = str(response)
        
        print(f"🔍 DEBUG: Texte extrait pour affichage: '{text_response[:100]}...'")
        
        # Ajouter le message avec le texte complet
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
