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
    def adjust_text_widget_height(self, text_widget):
        """Version améliorée pour ajuster la hauteur ET désactiver le scroll"""
        try:
            text_widget.update_idletasks()
            current_state = text_widget.cget("state")
            text_widget.configure(state="normal")
            
            # Obtenir le nombre de lignes
            line_count = int(text_widget.index("end-1c").split('.')[0])
            
            # Calculer une hauteur généreuse
            generous_height = max(2, line_count + 1)
            
            # Vérifier s'il y a du scroll et ajuster
            for _ in range(5):  # Maximum 5 tentatives
                text_widget.configure(height=generous_height)
                text_widget.update_idletasks()
                
                yview = text_widget.yview()
                if yview and yview[1] >= 1.0:
                    break  # Plus de scroll, parfait
                
                generous_height += 1
            
            text_widget.configure(state=current_state)
            
            # 🔧 IMPORTANT : Désactiver le scroll interne
            self._disable_text_scroll(text_widget)
            
        except Exception:
            # Fallback sécurisé
            try:
                text_widget.configure(height=10)
                self._disable_text_scroll(text_widget)
            except:
                pass
        
    def _disable_text_scroll(self, text_widget):
        """Désactive complètement le scroll interne du widget Text"""
        def block_scroll(event):
            return "break"
        
        # Désactiver tous les événements de scroll
        scroll_events = [
            '<MouseWheel>', '<Button-4>', '<Button-5>',  # Molette souris
            '<Up>', '<Down>',                             # Flèches haut/bas
            '<Prior>', '<Next>',                          # Page Up/Down
            '<Control-Home>', '<Control-End>',            # Ctrl+Home/End
            '<Shift-MouseWheel>',                         # Shift+molette
            '<Control-MouseWheel>'                        # Ctrl+molette
        ]
        
        for event in scroll_events:
            text_widget.bind(event, block_scroll)
        
        # Transférer le scroll vers le conteneur principal
        def forward_to_main_scroll(event):
            try:
                if hasattr(self, 'chat_frame'):
                    if self.use_ctk and hasattr(self.chat_frame, '_parent_canvas'):
                        canvas = self.chat_frame._parent_canvas
                        if hasattr(event, 'delta') and event.delta:
                            scroll_delta = -1 * (event.delta // 120)
                        else:
                            scroll_delta = -1 if event.num == 4 else 1
                        canvas.yview_scroll(scroll_delta, "units")
                    else:
                        parent = self.chat_frame.master
                        while parent and not hasattr(parent, 'yview_scroll'):
                            parent = parent.master
                        if parent:
                            if hasattr(event, 'delta') and event.delta:
                                scroll_delta = -1 * (event.delta // 120)
                            else:
                                scroll_delta = -1 if event.num == 4 else 1
                            parent.yview_scroll(scroll_delta, "units")
            except Exception:
                pass
            return "break"
        
        # Appliquer le transfert de scroll uniquement pour la molette
        text_widget.bind('<MouseWheel>', forward_to_main_scroll)
        text_widget.bind('<Button-4>', forward_to_main_scroll)
        text_widget.bind('<Button-5>', forward_to_main_scroll)

    def _show_timestamp_for_current_message(self):
        """Affiche le timestamp sous la bulle du dernier message IA (comme pour l'utilisateur)."""
        from datetime import datetime
        if hasattr(self, 'current_message_container') and self.current_message_container is not None:
            # Vérifier qu'il n'y a pas déjà un timestamp (évite doublons)
            for child in self.current_message_container.winfo_children():
                if isinstance(child, (tk.Label,)):
                    if getattr(child, 'is_timestamp', False):
                        return  # Déjà affiché
            timestamp = datetime.now().strftime("%H:%M")
            time_label = self.create_label(
                self.current_message_container,
                text=timestamp,
                font=('Segoe UI', 10),
                fg_color=self.colors['bg_chat'],
                text_color='#b3b3b3'
            )
            time_label.grid(row=1, column=0, sticky="w", padx=8, pady=(0, 6))
            time_label.is_timestamp = True
        # Sinon, rien à faire (pas de container)
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
            if hasattr(self, 'current_request_id'):
                self.current_request_id += 1  # Invalide toutes les requêtes en cours
            if hasattr(self, 'stop_typing_animation'):
                self.stop_typing_animation()
            if hasattr(self, 'stop_internet_search'):
                self.stop_internet_search()
            if hasattr(self, 'stop_thinking'):
                self.stop_thinking()
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
    
    def _configure_formatting_tags(self, text_widget):
        """Configure tous les tags de formatage pour l'animation avec coloration Python COMPLÈTE"""
        BASE_FONT = ('Segoe UI', 12)
        
        # 🔧 CONFIGURATION IDENTIQUE à insert_formatted_text_tkinter
        text_widget.tag_configure("bold", font=('Segoe UI', 12, 'bold'), foreground=self.colors['text_primary'])
        
        # 🔧 TITRES MARKDOWN avec tailles progressives
        text_widget.tag_configure("title1", font=('Segoe UI', 16, 'bold'), foreground=self.colors['text_primary'])
        text_widget.tag_configure("title2", font=('Segoe UI', 14, 'bold'), foreground=self.colors['text_primary'])
        text_widget.tag_configure("title3", font=('Segoe UI', 13, 'bold'), foreground=self.colors['text_primary'])
        text_widget.tag_configure("title4", font=('Segoe UI', 12, 'bold'), foreground=self.colors['text_primary'])
        text_widget.tag_configure("title5", font=('Segoe UI', 12, 'bold'), foreground=self.colors['text_primary'])
        
        text_widget.tag_configure("italic", font=('Segoe UI', 12, 'italic'), foreground=self.colors['text_primary'])
        text_widget.tag_configure("mono", font=('Consolas', 11), foreground="#f8f8f2")
        
        # 🔧 DOCSTRING - ESSENTIEL pour le code Python
        text_widget.tag_configure("docstring", font=('Consolas', 11, 'italic'), foreground="#ff8c00")
        
        text_widget.tag_configure("normal", font=BASE_FONT, foreground=self.colors['text_primary'])
        text_widget.tag_configure("link", foreground="#3b82f6", underline=1, font=BASE_FONT)
        
        # 🔧 PYTHON COMPLET - Couleurs VS Code EXACTES
        
        # Keywords - BLEU VS Code
        python_keyword_tags = [
            "Token.Keyword", "Token.Keyword.Constant", "Token.Keyword.Declaration",
            "Token.Keyword.Namespace", "Token.Keyword.Pseudo", "Token.Keyword.Reserved"
        ]
        for tag in python_keyword_tags:
            text_widget.tag_configure(tag, foreground="#569cd6", font=('Consolas', 11, 'bold'))
        
        text_widget.tag_configure("Token.Keyword.Type", foreground="#4ec9b0", font=('Consolas', 11, 'bold'))
        
        # Strings - ORANGE-BRUN VS Code
        string_tags = [
            "Token.Literal.String", "Token.Literal.String.Double", "Token.Literal.String.Single",
            "Token.String", "Token.String.Double", "Token.String.Single"
        ]
        for tag in string_tags:
            text_widget.tag_configure(tag, foreground="#ce9178", font=('Consolas', 11))
        
        # Commentaires - VERT VS Code
        comment_tags = [
            "Token.Comment", "Token.Comment.Single", "Token.Comment.Multiline"
        ]
        for tag in comment_tags:
            text_widget.tag_configure(tag, foreground="#6a9955", font=('Consolas', 11, 'italic'))
        
        # Fonctions et classes - JAUNE VS Code
        text_widget.tag_configure("Token.Name.Function", foreground="#dcdcaa", font=('Consolas', 11))
        text_widget.tag_configure("Token.Name.Function.Magic", foreground="#dcdcaa", font=('Consolas', 11))
        text_widget.tag_configure("Token.Name.Class", foreground="#4ec9b0", font=('Consolas', 11, 'bold'))
        
        # Builtins - JAUNE VS Code
        text_widget.tag_configure("Token.Name.Builtin", foreground="#dcdcaa", font=('Consolas', 11))
        text_widget.tag_configure("Token.Name.Builtin.Pseudo", foreground="#dcdcaa", font=('Consolas', 11))
        
        # Nombres - VERT CLAIR VS Code
        number_tags = [
            "Token.Literal.Number", "Token.Literal.Number.Integer", "Token.Literal.Number.Float",
            "Token.Number", "Token.Number.Integer", "Token.Number.Float"
        ]
        for tag in number_tags:
            text_widget.tag_configure(tag, foreground="#b5cea8", font=('Consolas', 11))
        
        # Opérateurs - BLANC VS Code
        text_widget.tag_configure("Token.Operator", foreground="#d4d4d4", font=('Consolas', 11))
        text_widget.tag_configure("Token.Punctuation", foreground="#d4d4d4", font=('Consolas', 11))
        
        # Variables et noms - BLEU CLAIR VS Code
        name_tags = [
            "Token.Name", "Token.Name.Variable", "Token.Name.Attribute"
        ]
        for tag in name_tags:
            text_widget.tag_configure(tag, foreground="#9cdcfe", font=('Consolas', 11))
        
        # Constantes spéciales - BLEU VS Code
        text_widget.tag_configure("Token.Name.Constant", foreground="#569cd6", font=('Consolas', 11, 'bold'))
        
        # AJOUT : Tags pour les blocs de code
        text_widget.tag_configure("code_block", font=('Consolas', 11), background="#1e1e1e", foreground="#d4d4d4")
        
        print("✅ Tags de coloration Python configurés pour l'animation")


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
            self.adjust_text_widget_height(text_widget)

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
            self.adjust_text_widget_height(text_widget)
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
        """Version CORRIGÉE pour les résumés - Hauteur automatique sans scroll interne"""
        import re
        from datetime import datetime
        try:
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

            # 🔧 CALCUL INTELLIGENT DE LA HAUTEUR BASÉ SUR LE CONTENU
            estimated_height = self._calculate_text_height_for_widget(text)

            # Widget Text avec hauteur calculée
            text_widget = tk.Text(
                message_container,
                width=120,
                height=estimated_height,  # Hauteur calculée intelligemment
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
            
            # 🔧 DÉSACTIVER LE SCROLL INTERNE DÈS LA CRÉATION
            self._disable_text_scroll(text_widget)

            text_widget.grid(row=0, column=0, padx=0, pady=(0, 0), sticky="nsew")

            # Bind minimal pour permettre la sélection
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

            # Démarrer l'animation de frappe avec hauteur pré-calculée
            self.start_typing_animation_dynamic(text_widget, text)
            
        except Exception as e:
            import traceback
            err_msg = f"[ERREUR affichage IA] {e}\n{traceback.format_exc()}"
            if hasattr(self, 'logger'):
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
            line_count = int(text_widget.index("end-1c").split('.')[0])
            
            print(f"🔍 DEBUG {widget_name}:")
            print(f"   Hauteur configurée: {height} lignes")
            print(f"   Lignes réelles: {line_count}")
            print(f"   YView (scroll): {yview}")
            print(f"   Scroll nécessaire: {'OUI' if yview and yview[1] < 1.0 else 'NON'}")
            print(f"   État: {'✅ OK' if not yview or yview[1] >= 1.0 else '❌ SCROLL INTERNE'}")
            print()
            
        except Exception as e:
            print(f"❌ Erreur debug {widget_name}: {e}")

    def _calculate_text_height_for_widget(self, text):
        """Calcule la hauteur optimale pour un texte donné"""
        if not text:
            return 5
        
        # Compter les lignes de base
        lines = text.split('\n')
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
        margin = max(3, int(total_estimated_lines * 0.2))  # 20% de marge minimum 3 lignes
        final_height = total_estimated_lines + margin
        
        # Limites raisonnables
        final_height = max(5, min(final_height, 80))  # Entre 5 et 80 lignes
        
        return final_height

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
        """Animation avec désactivation de la saisie - CORRIGÉ pour hauteur dynamique"""
        # DÉSACTIVER la saisie pendant l'animation
        self.set_input_state(False)
        
        # Réinitialiser le widget
        text_widget.configure(state="normal")
        text_widget.delete("1.0", "end")
        
        # Variables pour l'animation
        self.typing_index = 0
        self.typing_text = full_text
        self.typing_widget = text_widget
        self.typing_speed = 2
        
        # Configurer tous les tags de formatage
        self._configure_formatting_tags(text_widget)

        # Flag d'interruption
        self._typing_interrupted = False
        
        # Démarrer l'animation
        self.continue_typing_animation_dynamic()

    def continue_typing_animation_dynamic(self):
        """Animation AVEC formatage en temps réel - CORRIGÉE pour suivi et formatage Python"""
        if not hasattr(self, 'typing_widget') or not hasattr(self, 'typing_text'):
            return
        
        if getattr(self, '_typing_interrupted', False):
            self.finish_typing_animation_dynamic(interrupted=True)
            return
        
        if self.typing_index < len(self.typing_text):
            current_text = self.typing_text[:self.typing_index + 1]
            
            self.typing_widget.configure(state="normal")
            self.typing_widget.delete("1.0", "end")
            
            # 🔧 CORRECTION : Utiliser le formatage complet même pendant l'animation
            self.insert_formatted_text_tkinter(self.typing_widget, current_text)
            
            # Ajuster la hauteur
            self._adjust_height_during_animation(self.typing_widget, current_text)
            
            self.typing_widget.configure(state="disabled")
            self.typing_index += 1
            
            # 🔧 CORRECTION CLÉE : Scroll intelligent qui suit l'animation
            self._smart_scroll_follow_animation()
            
            self._typing_animation_after_id = self.root.after(self.typing_speed, self.continue_typing_animation_dynamic)
        else:
            # À la fin : formatage complet avec liens
            self.typing_widget.configure(state="normal")
            self.typing_widget.delete("1.0", "end")
            
            # 🔧 FORMATAGE FINAL COMPLET
            self._insert_markdown_and_links(self.typing_widget, self.typing_text)
            
            # Ajustement final de hauteur
            self._adjust_height_final_no_scroll(self.typing_widget, self.typing_text)
            
            self.finish_typing_animation_dynamic(interrupted=False)

    def _smart_scroll_follow_animation(self):
        """Scroll intelligent qui suit l'animation sans sauter à la fin"""
        try:
            if self.use_ctk:
                if hasattr(self, 'chat_frame') and hasattr(self.chat_frame, '_parent_canvas'):
                    canvas = self.chat_frame._parent_canvas
                    canvas.update_idletasks()
                    
                    # Obtenir la position actuelle et la hauteur totale
                    yview = canvas.yview()
                    if yview:
                        current_top, current_bottom = yview
                        
                        # Si on n'est pas déjà en bas, scroller progressivement
                        if current_bottom < 0.95:  # Pas complètement en bas
                            # Scroll progressif de quelques pixels seulement
                            scroll_amount = 0.02  # Très petit increment
                            new_position = min(1.0, current_top + scroll_amount)
                            canvas.yview_moveto(new_position)
            else:
                parent = self.chat_frame.master
                if hasattr(parent, 'yview') and hasattr(parent, 'yview_moveto'):
                    parent.update_idletasks()
                    yview = parent.yview()
                    if yview:
                        current_top, current_bottom = yview
                        if current_bottom < 0.95:
                            scroll_amount = 0.02
                            new_position = min(1.0, current_top + scroll_amount)
                            parent.yview_moveto(new_position)
                            
        except Exception as e:
            pass  # Scroll silencieux en cas d'erreur

    def _adjust_height_final_no_scroll(self, text_widget, full_text):
        """Ajustement final de hauteur pour éliminer complètement le scroll interne"""
        try:
            text_widget.update_idletasks()
            
            # Méthode 1 : Compter les lignes réelles dans le widget
            current_state = text_widget.cget("state")
            text_widget.configure(state="normal")
            
            # Obtenir le nombre de lignes réellement affichées
            line_count = int(text_widget.index("end-1c").split('.')[0])
            
            # Méthode 2 : Vérifier s'il y a du scroll interne
            max_attempts = 10
            for attempt in range(max_attempts):
                text_widget.update_idletasks()
                
                # Vérifier si le contenu déborde (yview indique s'il y a du scroll)
                yview = text_widget.yview()
                
                if yview and yview[1] < 1.0:
                    # Il y a du scroll interne, augmenter la hauteur
                    current_height = text_widget.cget("height")
                    new_height = current_height + 2
                    text_widget.configure(height=new_height)
                else:
                    # Plus de scroll interne, on s'arrête
                    break
            
            # Restaurer l'état
            text_widget.configure(state=current_state)
            
            # Méthode 3 : Vérification finale avec calcul manuel si nécessaire
            if yview and yview[1] < 1.0:
                # Calcul manuel en dernier recours
                lines = full_text.split('\n')
                total_lines = 0
                
                widget_width = text_widget.winfo_width()
                if widget_width <= 50:
                    widget_width = 800
                
                char_width = 7.2
                chars_per_line = max(50, int((widget_width - 30) / char_width))
                
                for line in lines:
                    if len(line) == 0:
                        total_lines += 1
                    else:
                        wrapped_lines = max(1, (len(line) + chars_per_line - 1) // chars_per_line)
                        total_lines += wrapped_lines
                
                # Hauteur finale avec marge généreuse
                final_height = total_lines + 3
                text_widget.configure(height=final_height)
            
        except Exception as e:
            # En cas d'erreur, utiliser une hauteur généreuse
            text_widget.configure(height=20)

    def _adjust_height_during_animation(self, text_widget, current_text):
        """Ajuste la hauteur pendant l'animation pour éviter tout scroll interne"""
        try:
            text_widget.update_idletasks()
            
            # Compter les lignes réelles du texte actuel
            lines = current_text.split('\n')
            
            # Calculer la hauteur nécessaire en tenant compte du wrapping
            total_lines = 0
            widget_width = text_widget.winfo_width()
            
            # Si la largeur n'est pas encore calculée, utiliser une valeur par défaut
            if widget_width <= 50:
                widget_width = 800  # Largeur approximative
            
            # Estimation du nombre de caractères par ligne
            char_width = 7.2  # Largeur moyenne d'un caractère
            chars_per_line = max(50, int((widget_width - 30) / char_width))  # -30 pour padding
            
            for line in lines:
                if len(line) == 0:
                    total_lines += 1
                else:
                    # Calculer le nombre de lignes wrapped pour cette ligne
                    wrapped_lines = max(1, (len(line) + chars_per_line - 1) // chars_per_line)
                    total_lines += wrapped_lines
            
            # Ajouter une marge de sécurité
            safe_height = total_lines + 2
            
            # Limiter la hauteur maximale pour éviter des bulles énormes
            final_height = min(safe_height, 50)
            
            text_widget.configure(height=final_height)
            
        except Exception as e:
            # En cas d'erreur, utiliser une hauteur conservative
            text_widget.configure(height=10)   

    def _insert_formatted_text_animated(self, text_widget, text):
        """Version allégée du formatage pour l'animation (sans liens pour éviter les ralentissements)"""
        import re
        
        # Configuration des tags essentiels
        text_widget.tag_configure("bold", font=('Segoe UI', 12, 'bold'), foreground=self.colors['text_primary'])
        text_widget.tag_configure("italic", font=('Segoe UI', 12, 'italic'), foreground=self.colors['text_primary'])
        text_widget.tag_configure("mono", font=('Consolas', 11), foreground="#f8f8f2")
        text_widget.tag_configure("normal", font=('Segoe UI', 12), foreground=self.colors['text_primary'])
        
        # Formatage simplifié pour l'animation
        def parse_simple_segments(txt):
            patterns = [
                (r'\*\*([^*]+)\*\*', 'bold'),     # **texte**
                (r'\*([^*]+)\*', 'italic'),       # *texte*
                (r'`([^`]+)`', 'mono')            # `code`
            ]
            
            def _parse(txt, pat_idx=0):
                if pat_idx >= len(patterns):
                    return [(txt, 'normal')]
                
                pattern, style = patterns[pat_idx]
                segments = []
                last = 0
                
                for m in re.finditer(pattern, txt):
                    start, end = m.start(), m.end()
                    if start > last:
                        segments.extend(_parse(txt[last:start], pat_idx+1))
                    segments.append((m.group(1), style))
                    last = end
                
                if last < len(txt):
                    segments.extend(_parse(txt[last:], pat_idx+1))
                return segments
            
            return _parse(txt)
        
        # Insérer avec formatage
        for segment, style in parse_simple_segments(text):
            if segment:
                text_widget.insert("end", segment, style)

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
        """Version CORRIGÉE qui préserve le formatage Python"""
        if hasattr(self, 'typing_widget') and hasattr(self, 'typing_text'):
            self.typing_widget.configure(state="normal")
            self.typing_widget.delete("1.0", "end")
            
            if interrupted:
                partial_text = self.typing_text[:self.typing_index]
                # 🔧 CORRECTION : Utiliser le formatage Python complet, pas _insert_markdown_and_links
                self.insert_formatted_text_tkinter(self.typing_widget, partial_text)
            else:
                # 🔧 CORRECTION CLÉE : Ne pas écraser avec _insert_markdown_and_links
                # Utiliser directement insert_formatted_text_tkinter qui préserve le formatage Python
                self.insert_formatted_text_tkinter(self.typing_widget, self.typing_text)
            
            # Ajustement final EXACT de la hauteur
            self._adjust_height_final_no_scroll(self.typing_widget, self.typing_text)
            
            # 🔧 CORRECTION : NE PAS remettre en "disabled" pour préserver les liens
            # Les liens ont besoin que le widget reste en état "normal" pour être cliquables
            print(f"[DEBUG] Widget gardé en état 'normal' pour préserver le formatage et les liens")
            
            # Afficher le timestamp sous le message IA
            self._show_timestamp_for_current_message()
            
            # Réactiver la saisie utilisateur
            self.set_input_state(True)
            
            # Scroll final contrôlé
            self.root.after(200, self._final_smooth_scroll_to_bottom)
            
            # Nettoyage des variables d'animation
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
            
            print(f"[DEBUG] Animation terminée et formatage préservé")

    def _final_smooth_scroll_to_bottom(self):
        """Scroll final en douceur sans saut brutal"""
        try:
            # Une seule mise à jour, puis scroll progressif
            self.root.update_idletasks()
            
            if self.use_ctk:
                if hasattr(self, 'chat_frame') and hasattr(self.chat_frame, '_parent_canvas'):
                    canvas = self.chat_frame._parent_canvas
                    
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
                if hasattr(parent, 'yview_moveto'):
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
                            
        except Exception as e:
            # Fallback : scroll simple
            try:
                if self.use_ctk and hasattr(self.chat_frame, '_parent_canvas'):
                    self.chat_frame._parent_canvas.yview_moveto(1.0)
                else:
                    parent = self.chat_frame.master
                    if hasattr(parent, 'yview_moveto'):
                        parent.yview_moveto(1.0)
            except:
                pass

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

    def _adjust_text_height_exact(self, text_widget):
        """Ajuste la hauteur du widget Text pour qu'il n'y ait aucun scroll interne ni espace vide, basé sur le nombre de lignes réelles tkinter. Désactive aussi le scroll interne."""
        try:
            text_widget.update_idletasks()
            current_state = text_widget.cget("state")
            text_widget.configure(state="normal")
            # Compter le nombre de lignes réelles (tkinter)
            line_count = int(text_widget.index("end-1c").split('.')[0])
            # Min 2, max 50 lignes (ajuster si besoin)
            height = max(2, min(line_count, 50))
            text_widget.configure(height=height)
            text_widget.configure(state=current_state)
            self._disable_text_scroll(text_widget)
        except Exception as e:
            try:
                text_widget.configure(height=7)
            except Exception:
                pass

    def _adjust_widget_height_final(self, text_widget, full_text):
        """Ajustement dynamique parfait : hauteur adaptée au texte et à la largeur réelle du widget (padx inclus), sans scroll interne ni espace vide. Correction spéciale pour les bulles user (largeur à 1px au début)."""
        import math, time
        try:
            # Forcer le rendu complet du widget (pour bulles user)
            import math, time
            for i in range(10):
                text_widget.update_idletasks()
                widget_width = text_widget.winfo_width()
                if widget_width > 50:
                    break
                if hasattr(self, 'root'):
                    self.root.update_idletasks()
                time.sleep(0.01)
            else:
                widget_width = 400
            font = text_widget.cget('font')
            char_width = 7.2
            try:
                import tkinter.font as tkfont
                f = tkfont.Font(font=font)
                char_width = f.measure('n')
                if char_width < 5:
                    char_width = 7.2
            except Exception:
                pass
            chars_per_line = max(10, int(widget_width // char_width))
            lines = full_text.split('\n')
            total_lines = 0
            for l in lines:
                l = l.rstrip()
                wrapped = max(1, math.ceil(len(l) / chars_per_line))
                total_lines += wrapped
            # Correction : PAS de +1 systématique, mais min 2 lignes
            height = max(2, total_lines)
            text_widget.configure(height=height)
            text_widget.update_idletasks()
            # Correction : n'augmente la hauteur que si le texte est coupé (scroll interne visible)
            for j in range(10):
                yview = text_widget.yview()
                if yview[1] >= 1.0:
                    break
                height += 1
                text_widget.configure(height=height)
                text_widget.update_idletasks()
        except Exception:
            text_widget.configure(height=7)

    def _insert_markdown_and_links(self, text_widget, text):
        """Version CORRIGÉE avec regex fixé pour les liens Markdown"""
        import re
        import webbrowser
        
        print(f"[DEBUG] _insert_markdown_and_links appelée avec: {repr(text[:100])}")
        
        prev_state = text_widget.cget("state")
        text_widget.configure(state="normal")
        
        # Configuration des tags
        text_widget.tag_configure("link", 
                                foreground="#3b82f6", 
                                underline=True,
                                font=('Segoe UI', 12))
        
        text_widget.tag_configure("bold", 
                                font=('Segoe UI', 12, 'bold'), 
                                foreground=self.colors['text_primary'])
        
        # CORRECTION : Patterns corrigés pour les liens
        # Pattern pour liens Markdown : [texte](url)
        markdown_link_pattern = r'\[([^\]]+)\]\(([^)]+)\)'
        # Pattern pour liens HTTP directs
        http_link_pattern = r'(https?://[^\s\)]+)'
        
        # CORRECTION : Combinaison des patterns avec groupes nommés pour éviter la confusion
        combined_pattern = f'(?P<markdown>{markdown_link_pattern})|(?P<direct>{http_link_pattern})'
        
        print(f"[DEBUG] Pattern utilisé: {combined_pattern}")
        
        last_end = 0
        link_count = 0
        
        # Traiter chaque lien trouvé
        for match in re.finditer(combined_pattern, text):
            print(f"[DEBUG] Match trouvé: {match.groupdict()}")
            
            # Insérer le texte avant le lien avec formatage
            if match.start() > last_end:
                text_before = text[last_end:match.start()]
                self._insert_markdown_segments(text_widget, text_before)
            
            # CORRECTION : Extraction correcte selon le type de lien
            if match.group('markdown'):  # Lien Markdown [texte](url)
                # Pour les liens Markdown, on re-match pour extraire les groupes
                markdown_match = re.match(markdown_link_pattern, match.group('markdown'))
                if markdown_match:
                    link_text = markdown_match.group(1)  # Texte entre []
                    url = markdown_match.group(2)        # URL entre ()
                    print(f"[DEBUG] Lien Markdown corrigé: texte='{link_text}', url='{url}'")
                else:
                    print(f"[DEBUG] Erreur parsing Markdown: {match.group('markdown')}")
                    last_end = match.end()
                    continue
            else:  # Lien HTTP direct
                url = match.group('direct')
                link_text = url if len(url) <= 50 else url[:47] + "..."
                print(f"[DEBUG] Lien direct: url='{url}'")
            
            # Vérification de l'URL
            if not url or not url.strip() or url == 'None':
                print(f"[DEBUG] URL invalide: {repr(url)}, insertion comme texte normal")
                text_widget.insert("end", link_text if 'link_text' in locals() else match.group(0))
                last_end = match.end()
                continue
            
            # Insérer le lien avec formatage
            start_index = text_widget.index("end-1c")
            text_widget.insert("end", link_text, ("link",))
            end_index = text_widget.index("end-1c")
            
            # Créer un tag unique pour ce lien
            tag_name = f"link_{link_count}"
            text_widget.tag_add(tag_name, start_index, end_index)
            
            # Callback pour ouvrir le lien
            def create_callback(target_url):
                def on_click(event):
                    try:
                        clean_url = str(target_url).strip()
                        print(f"[DEBUG] Tentative d'ouverture: {clean_url}")
                        
                        if not clean_url.startswith(('http://', 'https://')):
                            print(f"[DEBUG] URL mal formatée: {clean_url}")
                            return "break"
                        
                        webbrowser.open(clean_url)
                        print(f"[DEBUG] ✅ Lien ouvert: {clean_url}")
                        
                    except Exception as e:
                        print(f"[DEBUG] ❌ Erreur: {e}")
                    
                    return "break"
                return on_click
            
            # Bind des événements
            callback = create_callback(url)
            text_widget.tag_bind(tag_name, "<Button-1>", callback)
            text_widget.tag_bind(tag_name, "<Enter>", 
                            lambda e: text_widget.configure(cursor="hand2"))
            text_widget.tag_bind(tag_name, "<Leave>", 
                            lambda e: text_widget.configure(cursor="xterm"))
            
            # Assurer la priorité du tag
            text_widget.tag_raise(tag_name)
            
            link_count += 1
            last_end = match.end()
        
        # Insérer le reste du texte
        if last_end < len(text):
            remaining_text = text[last_end:]
            self._insert_markdown_segments(text_widget, remaining_text)
        
        print(f"[DEBUG] {link_count} liens traités avec succès")

    def _insert_markdown_segments(self, text_widget, text):
        """Insère du texte avec formatage - ÉVITE les (args: ...) dans les fonctions"""
        import re
        
        def parse_segments(text, patterns):
            if not patterns:
                return [(text, 'normal')]
            
            pattern, style = patterns[0]
            segments = []
            last = 0
            
            for m in re.finditer(pattern, text):
                if m.start() > last:
                    segments.extend(parse_segments(text[last:m.start()], patterns[1:]))
                
                # TRAITEMENT SPÉCIAL pour **Args:** et **Returns:**
                if style == 'args_returns':
                    word = m.group(1)  # "Args" ou "Returns"
                    segments.append((f"{word}:", 'bold'))
                else:
                    segments.append((m.group(1), style))
                last = m.end()
                
            if last < len(text):
                segments.extend(parse_segments(text[last:], patterns[1:]))
            return segments
        
        # PATTERNS dans l'ordre - Args/Returns spécifiques en premier
        patterns = [
            # SEULEMENT les **Args:** et **Returns:** isolés (pas dans les args de fonctions)
            (r'\*\*(Args|Returns):\*\*(?!\s*[a-z])', 'args_returns'),  # Negative lookahead pour éviter "args: self"
            (r'`([^`]+)`', 'mono'),                                    # `code`
            (r'\*\*([^*]+)\*\*', 'bold'),                              # **texte** (autres)
            (r'\*([^*]+)\*', 'italic'),                                # *texte*
        ]
        
        for segment, style in parse_segments(text, patterns):
            if segment:
                text_widget.insert("end", segment, style)

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
        """Version AMÉLIORÉE qui gère les liens ET le formatage Python"""
        import re, webbrowser, os
        text_widget.delete("1.0", "end")

        # Configuration complète des tags
        self._configure_all_formatting_tags(text_widget)

        # 🔧 CORRECTION DU TEXTE avant parsing
        text = re.sub(r'^(\s*)Args:\s*$', r'\1**Args:**', text, flags=re.MULTILINE)
        text = re.sub(r'^(\s*)Returns:\s*$', r'\1**Returns:**', text, flags=re.MULTILINE)
        text = re.sub(r'(?<!\n)(^##\d+\.\s+.*$)', r'\n\1', text, flags=re.MULTILINE)

        # Correction du nom de fichier temporaire
        temp_file_match = re.search(r'Explication détaillée du fichier [`"]?(tmp\w+\.py)[`"]?', text)
        if temp_file_match and hasattr(self, 'conversation_history'):
            for hist in reversed(self.conversation_history):
                if 'text' in hist and isinstance(hist['text'], str):
                    real_file = re.search(r"document: '([\w\-.]+\.py)'", hist['text'])
                    if real_file:
                        text = text.replace(temp_file_match.group(1), real_file.group(1))
                        break
            else:
                py_files = [f for f in os.listdir('.') if f.endswith('.py')]
                if py_files:
                    text = text.replace(temp_file_match.group(1), py_files[0])

        # 🔧 NOUVEAU : Traitement des liens AVANT le parsing général
        text_with_links_processed = self._process_links_preserve_formatting(text, text_widget)
        
        # Parsing avec formatage Python complet
        def parse_segments(txt):
            patterns = [
                # DOCSTRINGS - Priorité maximale
                (r"'''docstring([\s\S]+?)'''|\"\"\"docstring([\s\S]+?)\"\"\"", 'docstring_strip'),
                (r"'''([\s\S]+?)'''|\"\"\"([\s\S]+?)\"\"\"", 'docstring'),
                
                # TITRES MARKDOWN
                (r'^(#+) (.+)$', 'title'),
                
                # FORMATAGE STANDARD
                (r'`([^`]+)`', 'mono'),
                (r'\*\*([^*]+)\*\*', 'bold'),
                (r'\*([^*]+)\*', 'italic'),
            ]
            
            def _parse(txt, pat_idx=0):
                if pat_idx >= len(patterns):
                    return [(txt, 'normal')]
                
                pattern, style = patterns[pat_idx]
                segments = []
                last = 0
                
                for m in re.finditer(pattern, txt, re.MULTILINE):
                    start, end = m.start(), m.end()
                    if start > last:
                        segments.extend(_parse(txt[last:start], pat_idx+1))
                    
                    if style == 'docstring_strip':
                        doc = m.group(1) or m.group(2)
                        if doc is not None:
                            doc = doc.lstrip('\n').rstrip("'\" ")
                        segments.append((doc, 'docstring'))
                    elif style == 'docstring':
                        doc = m.group(1) or m.group(2)
                        segments.append((doc, 'docstring'))
                    elif style == 'title':
                        hashes = m.group(1)
                        title_text = m.group(2)
                        tag = f"title{min(len(hashes),5)}"
                        segments.append((title_text, tag))
                    else:
                        segments.append((m.group(1), style))
                    last = end
                
                if last < len(txt):
                    segments.extend(_parse(txt[last:], pat_idx+1))
                return segments
            
            return _parse(txt)

        # Insertion avec formatage complet
        for segment, style in parse_segments(text_with_links_processed):
            if not segment:
                continue
            text_widget.insert("end", segment, style)

        text_widget.update_idletasks()
        text_widget.see("1.0")

    def _configure_all_formatting_tags(self, text_widget):
        """Configure TOUS les tags de formatage - Version unifiée"""
        BASE_FONT = ('Segoe UI', 12)
        
        # Tags de base
        text_widget.tag_configure("bold", font=('Segoe UI', 12, 'bold'), foreground=self.colors['text_primary'])
        text_widget.tag_configure("title1", font=('Segoe UI', 16, 'bold'), foreground=self.colors['text_primary'])
        text_widget.tag_configure("title2", font=('Segoe UI', 14, 'bold'), foreground=self.colors['text_primary'])
        text_widget.tag_configure("title3", font=('Segoe UI', 13, 'bold'), foreground=self.colors['text_primary'])
        text_widget.tag_configure("title4", font=('Segoe UI', 12, 'bold'), foreground=self.colors['text_primary'])
        text_widget.tag_configure("title5", font=('Segoe UI', 12, 'bold'), foreground=self.colors['text_primary'])
        text_widget.tag_configure("italic", font=('Segoe UI', 12, 'italic'), foreground=self.colors['text_primary'])
        text_widget.tag_configure("mono", font=('Consolas', 11), foreground="#f8f8f2")
        text_widget.tag_configure("docstring", font=('Consolas', 11, 'italic'), foreground="#ff8c00")
        text_widget.tag_configure("normal", font=BASE_FONT, foreground=self.colors['text_primary'])
        text_widget.tag_configure("link", foreground="#3b82f6", underline=1, font=BASE_FONT)
        
        # Tags Python complets
        python_tags = {
            "Token.Keyword": ("#569cd6", 'bold'),
            "Token.Keyword.Constant": ("#569cd6", 'bold'),
            "Token.Keyword.Declaration": ("#569cd6", 'bold'),
            "Token.Keyword.Namespace": ("#569cd6", 'bold'),
            "Token.Keyword.Pseudo": ("#569cd6", 'bold'),
            "Token.Keyword.Reserved": ("#569cd6", 'bold'),
            "Token.Keyword.Type": ("#4ec9b0", 'bold'),
            "Token.Literal.String": ("#ce9178", 'normal'),
            "Token.Literal.String.Double": ("#ce9178", 'normal'),
            "Token.Literal.String.Single": ("#ce9178", 'normal'),
            "Token.String": ("#ce9178", 'normal'),
            "Token.String.Double": ("#ce9178", 'normal'),
            "Token.String.Single": ("#ce9178", 'normal'),
            "Token.Comment": ("#6a9955", 'italic'),
            "Token.Comment.Single": ("#6a9955", 'italic'),
            "Token.Comment.Multiline": ("#6a9955", 'italic'),
            "Token.Name.Function": ("#dcdcaa", 'normal'),
            "Token.Name.Function.Magic": ("#dcdcaa", 'normal'),
            "Token.Name.Class": ("#4ec9b0", 'bold'),
            "Token.Name.Builtin": ("#dcdcaa", 'normal'),
            "Token.Name.Builtin.Pseudo": ("#dcdcaa", 'normal'),
            "Token.Literal.Number": ("#b5cea8", 'normal'),
            "Token.Literal.Number.Integer": ("#b5cea8", 'normal'),
            "Token.Literal.Number.Float": ("#b5cea8", 'normal'),
            "Token.Number": ("#b5cea8", 'normal'),
            "Token.Number.Integer": ("#b5cea8", 'normal'),
            "Token.Number.Float": ("#b5cea8", 'normal'),
            "Token.Operator": ("#d4d4d4", 'normal'),
            "Token.Punctuation": ("#d4d4d4", 'normal'),
            "Token.Name": ("#9cdcfe", 'normal'),
            "Token.Name.Variable": ("#9cdcfe", 'normal'),
            "Token.Name.Attribute": ("#9cdcfe", 'normal'),
            "Token.Name.Constant": ("#569cd6", 'bold'),
        }
        
        for tag, (color, weight) in python_tags.items():
            if weight == 'bold':
                text_widget.tag_configure(tag, foreground=color, font=('Consolas', 11, 'bold'))
            elif weight == 'italic':
                text_widget.tag_configure(tag, foreground=color, font=('Consolas', 11, 'italic'))
            else:
                text_widget.tag_configure(tag, foreground=color, font=('Consolas', 11))
        
        text_widget.tag_configure("code_block", font=('Consolas', 11), background="#1e1e1e", foreground="#d4d4d4")

    def _process_links_preserve_formatting(self, text, text_widget):
        """Traite les liens tout en préservant le formatage du reste du texte"""
        import re, webbrowser
        
        # Configuration des liens
        text_widget.tag_configure("link", 
                                foreground="#3b82f6", 
                                underline=True,
                                font=('Segoe UI', 12))
        
        # Pattern pour liens Markdown : [texte](url)
        markdown_link_pattern = r'\[([^\]]+)\]\(([^)]+)\)'
        # Pattern pour liens HTTP directs
        http_link_pattern = r'(https?://[^\s\)]+)'
        
        # Combinaison des patterns
        combined_pattern = f'(?P<markdown>{markdown_link_pattern})|(?P<direct>{http_link_pattern})'
        
        processed_text = text
        link_count = 0
        
        # Remplacer les liens par des marqueurs temporaires pour éviter les conflits
        link_replacements = {}
        
        for match in re.finditer(combined_pattern, text):
            if match.group('markdown'):
                # Lien Markdown [texte](url)
                markdown_match = re.match(markdown_link_pattern, match.group('markdown'))
                if markdown_match:
                    link_text = markdown_match.group(1)
                    url = markdown_match.group(2)
                    
                    if url and url.strip() and url != 'None':
                        # Créer un marqueur unique
                        marker = f"__LINK_MARKER_{link_count}__"
                        link_replacements[marker] = {
                            'text': link_text,
                            'url': url,
                            'original': match.group(0)
                        }
                        
                        # Remplacer dans le texte
                        processed_text = processed_text.replace(match.group(0), marker, 1)
                        link_count += 1
            
            elif match.group('direct'):
                # Lien direct HTTP
                url = match.group('direct')
                link_text = url if len(url) <= 50 else url[:47] + "..."
                
                if url and url.strip():
                    marker = f"__LINK_MARKER_{link_count}__"
                    link_replacements[marker] = {
                        'text': link_text,
                        'url': url,
                        'original': match.group(0)
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
                            lines_before = current_content[:start_pos].count('\n')
                            chars_in_line = len(current_content[:start_pos].split('\n')[-1])
                            
                            start_index = f"{lines_before + 1}.{chars_in_line}"
                            end_index = f"{lines_before + 1}.{chars_in_line + len(marker)}"
                            
                            # Remplacer le marqueur par le texte du lien
                            text_widget.delete(start_index, end_index)
                            text_widget.insert(start_index, link_info['text'])
                            
                            # Calculer la nouvelle position de fin
                            end_index = f"{lines_before + 1}.{chars_in_line + len(link_info['text'])}"
                            
                            # Créer un tag unique pour ce lien
                            tag_name = f"link_{link_count}_{start_pos}"
                            text_widget.tag_add(tag_name, start_index, end_index)
                            
                            # Callback pour ouvrir le lien
                            def create_callback(target_url):
                                def on_click(event):
                                    try:
                                        webbrowser.open(str(target_url).strip())
                                        print(f"[DEBUG] ✅ Lien ouvert: {target_url}")
                                    except Exception as e:
                                        print(f"[DEBUG] ❌ Erreur ouverture lien: {e}")
                                    return "break"
                                return on_click
                            
                            # Bind des événements
                            callback = create_callback(link_info['url'])
                            text_widget.tag_bind(tag_name, "<Button-1>", callback)
                            text_widget.tag_bind(tag_name, "<Enter>", 
                                            lambda e: text_widget.configure(cursor="hand2"))
                            text_widget.tag_bind(tag_name, "<Leave>", 
                                            lambda e: text_widget.configure(cursor="xterm"))
                            
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
                "⚡ Traitement neural en cours.",
                "💡 Génération de réponse intelligente.",
                "🎯 Optimisation de la réponse.",
                "⚙️ Moteur de raisonnement actif.",
                "📊 Analyse des patterns.",
                "💻 Processing linguistique avancé.",
                "🎪 Préparation d'une réponse."
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