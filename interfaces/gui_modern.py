"""
Interface Graphique Moderne - My AI Personal Assistant
Inspirée de l'interface Claude avec animations et design moderne
🚀 MAINTENANT AVEC SYSTÈME 1M TOKENS !
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

# 🚀 NOUVEAU: Import du modèle CustomAI unifié avec support 1M tokens
try:
    from models.custom_ai_model import CustomAIModel
    ULTRA_1M_AVAILABLE = True
    print("🚀 Modèle CustomAI unifié avec système 1M tokens intégré !")
except ImportError:
    ULTRA_1M_AVAILABLE = False
    print("📝 Interface moderne en mode standard")

# Imports pour asyncio
import asyncio
import concurrent.futures

try:
    import customtkinter as ctk
    CTK_AVAILABLE = True
except ImportError:
    CTK_AVAILABLE = False
    # CustomTkinter non disponible, utilisation de tkinter standard
    import tkinter as ctk  # Fallback vers tkinter standard

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
    import tkinter as ctk  # Fallback vers tkinter standard

try:
    from core.ai_engine import AIEngine
    from core.config import Config
    from utils.file_processor import FileProcessor
    from utils.logger import setup_logger
except ImportError as e:
    # Fallback for direct execution
    import sys
    from pathlib import Path
    
    # Add parent directory to path
    parent_dir = Path(__file__).parent.parent
    sys.path.insert(0, str(parent_dir))
    
    from core.ai_engine import AIEngine
    from core.config import Config
    from utils.file_processor import FileProcessor
    from utils.logger import setup_logger


class ModernAIGUI:
    def adjust_text_widget_height(self, text_widget):
        """NOUVELLE VERSION : Hauteur illimitée pour éviter les scrollbars internes"""
        try:
            text_widget.update_idletasks()
            current_state = text_widget.cget("state")
            text_widget.configure(state="normal")
            
            # ⚡ CORRECTION MAJEURE : Obtenir la hauteur RÉELLE nécessaire
            line_count = int(text_widget.index("end-1c").split('.')[0])
            
            # ⚡ HAUTEUR GÉNÉREUSE : Toujours assez pour tout afficher
            generous_height = max(line_count + 5, 10)  # Au moins 10 lignes, +5 de marge
            
            text_widget.configure(height=generous_height)
            text_widget.update_idletasks()
            
            text_widget.configure(state=current_state)
            
            # ⚡ DÉSACTIVER COMPLÈTEMENT LES SCROLLBARS INTERNES
            # COMMENTÉ CAR CELA ÉCRASE NOS BINDINGS DE FORWARDING !
            # self._disable_text_scroll(text_widget)
            # self._disable_text_scroll(text_widget)
            
        except Exception:
            # Fallback sécurisé : laisser la hauteur par défaut
            try:
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

    def _reactivate_text_scroll(self, text_widget):
        """Réactive le scroll après l'animation"""
        try:
            # Supprimer tous les bindings de blocage
            scroll_events = [
                '<MouseWheel>', '<Button-4>', '<Button-5>',
                '<Up>', '<Down>', '<Prior>', '<Next>',
                '<Control-Home>', '<Control-End>', '<Shift-MouseWheel>'
            ]
            
            for event in scroll_events:
                try:
                    text_widget.unbind(event)
                except:
                    pass
            
            # Réactiver le scroll normal via le système de forwarding
            self.setup_improved_scroll_forwarding(text_widget)
            print("✅ Scroll réactivé après animation")
            
        except Exception as e:
            print(f"[DEBUG] Erreur réactivation scroll: {e}")

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
        """Initialise l'interface moderne avec système 1M tokens"""
        self.is_interrupted = False  # Pour interruption robuste
        self.logger = setup_logger("modern_ai_gui")
        # AIEngine principal pour toute l'interface
        self.config = Config()
        self.ai_engine = AIEngine(self.config)
        
        # 🚀 NOUVEAU: Initialisation avec CustomAI unifié (avec support 1M tokens)
        if ULTRA_1M_AVAILABLE:
            print("🚀 Interface moderne avec modèle CustomAI unifié !")
            try:
                # Utiliser CustomAIModel avec support 1M tokens intégré
                self.custom_ai = CustomAIModel()
                
                # 🔗 IMPORTANT: Partager la même ConversationMemory entre AIEngine et CustomAI
                if hasattr(self.ai_engine, 'local_ai') and hasattr(self.ai_engine.local_ai, 'conversation_memory'):
                    print("🔗 Synchronisation des mémoires de conversation...")
                    # Utiliser la mémoire de CustomAI comme référence
                    self.ai_engine.local_ai.conversation_memory = self.custom_ai.conversation_memory
                    print("✅ Mémoires synchronisées")
                
                # Afficher les stats initiales
                stats = self.custom_ai.get_context_stats()
                print(f"📊 Contexte initial: {stats.get('context_size', 0):,} / {stats.get('max_context_length', 1000000):,} tokens")
                print(f"📚 Documents: {len(self.custom_ai.conversation_memory.stored_documents)}")
                print(f"🧠 Mode: {'Ultra 1M' if self.custom_ai.ultra_mode else 'Classique'}")
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
        
        # 🔧 NOUVEAU : Tag pour placeholder de code
        text_widget.tag_configure("code_placeholder", font=BASE_FONT, foreground=self.colors['text_primary'])
        
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

            # ⚡ SOLUTION FINALE: Appliquer le scroll forwarding SUR LE CONTAINER !
            def setup_container_scroll_forwarding(container):
                """Configure le scroll forwarding sur le container IA pour égaler la vitesse utilisateur"""
                def forward_from_container(event):
                    try:
                        if hasattr(self, 'chat_frame') and self.use_ctk and hasattr(self.chat_frame, '_parent_canvas'):
                            canvas = self.chat_frame._parent_canvas
                            if hasattr(event, 'delta') and event.delta:
                                # AMPLIFICATION 60x pour égaler la vitesse utilisateur
                                scroll_delta = -1 * (event.delta // 6) * 60
                            else:
                                scroll_delta = -20 * 60
                            canvas.yview_scroll(scroll_delta, "units")
                        return "break"
                    except Exception as e:
                        return "break"
                
                container.bind("<MouseWheel>", forward_from_container)
                container.bind("<Button-4>", forward_from_container)
                container.bind("<Button-5>", forward_from_container)
            
            setup_container_scroll_forwarding(message_container)

            # Stocker le container pour l'affichage du timestamp
            self.current_message_container = message_container

            # Widget Text avec hauteur ILLIMITÉE pour éviter les scrollbars internes
            estimated_lines = max(1, len(text.split('\n')))  # Estimation basique
            import tkinter as tk
            text_widget = tk.Text(
                message_container,
                width=120,
                height=1,
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
                insertwidth=0,
                # DÉSACTIVER COMPLÈTEMENT LE SCROLL INTERNE
                yscrollcommand=None,
                xscrollcommand=None
            )
            text_widget.grid(row=0, column=0, padx=0, pady=(0, 0), sticky="nsew")
            # ⚡ NOUVEAU : Ajustement avec hauteur généreuse pour éviter les scrollbars
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
            
            # UTILISER LA MÊME FONCTION QUE LES BULLES USER !
            # MAIS ON VA FORCER LA VITESSE A ÊTRE IDENTIQUE AUX USER !
            def setup_identical_scroll_to_user(text_widget_ia):
                """SCROLL IDENTIQUE AUX BULLES USER - Version finale"""
                def forward_user_style(event):
                    try:
                        if hasattr(self, 'chat_frame') and self.use_ctk and hasattr(self.chat_frame, '_parent_canvas'):
                            canvas = self.chat_frame._parent_canvas
                            if hasattr(event, 'delta') and event.delta:
                                scroll_delta = -1 * (event.delta // 6)  # EXACTEMENT comme USER
                            elif hasattr(event, 'num'):
                                scroll_delta = -20 if event.num == 4 else 20  # EXACTEMENT comme USER
                            else:
                                scroll_delta = -20
                            canvas.yview_scroll(scroll_delta, "units")
                    except Exception as e:
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
                
                def forward_scroll_to_page_IA(event):
                    try:
                        # Transférer le scroll à la zone de conversation principale
                        if hasattr(self, 'chat_frame'):
                            if self.use_ctk and hasattr(self.chat_frame, '_parent_canvas'):
                                # Pour CustomTkinter ScrollableFrame - SCROLL ULTRA RAPIDE
                                canvas = self.chat_frame._parent_canvas
                                # Amplifier le delta pour scroll ultra rapide (x20 plus rapide)
                                if hasattr(event, 'delta') and event.delta:
                                    scroll_delta = -1 * (event.delta // 6)  # 6 au lieu de 120 = 20x plus rapide
                                elif hasattr(event, 'num'):
                                    scroll_delta = -20 if event.num == 4 else 20  # 20x plus rapide
                                else:
                                    scroll_delta = -20
                                canvas.yview_scroll(scroll_delta, "units")
                    except Exception as e:
                        pass
                    return "break"  # Empêcher le scroll local
                
                # Appliquer le transfert de scroll EXACTEMENT comme USER
                text_widget.bind("<MouseWheel>", forward_scroll_to_page_IA)
                text_widget.bind("<Button-4>", forward_scroll_to_page_IA)  # Linux scroll up
                text_widget.bind("<Button-5>", forward_scroll_to_page_IA)  # Linux scroll down
                
                # Désactiver toutes les autres formes de scroll EXACTEMENT comme USER
                text_widget.bind("<Up>", lambda e: "break")
                text_widget.bind("<Down>", lambda e: "break")
                text_widget.bind("<Prior>", lambda e: "break")  # Page Up
                text_widget.bind("<Next>", lambda e: "break")   # Page Down
                text_widget.bind("<Home>", lambda e: "break")
                text_widget.bind("<End>", lambda e: "break")
            
            apply_exact_user_scroll_system()
            
            # FORCER L'APPLICATION APRÈS TOUS LES AUTRES SETUPS !
            def force_final_bindings():
                """Force finale après que tout soit terminé"""
                def final_scroll_handler(event):
                    try:
                        if hasattr(self, 'chat_frame') and self.use_ctk and hasattr(self.chat_frame, '_parent_canvas'):
                            canvas = self.chat_frame._parent_canvas
                            if hasattr(event, 'delta') and event.delta:
                                scroll_delta = -1 * (event.delta // 6)
                            else:
                                scroll_delta = -20
                            canvas.yview_scroll(scroll_delta, "units")
                    except Exception as e:
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
        """Configure le transfert du scroll - Version ultra rapide pour bulles USER"""
        
        def forward_scroll_to_page(event):
            try:
                # Transférer le scroll à la zone de conversation principale
                if hasattr(self, 'chat_frame'):
                    if self.use_ctk and hasattr(self.chat_frame, '_parent_canvas'):
                        # Pour CustomTkinter ScrollableFrame - SCROLL ULTRA RAPIDE
                        canvas = self.chat_frame._parent_canvas
                        # Amplifier le delta pour scroll ultra rapide (x20 plus rapide)
                        if hasattr(event, 'delta') and event.delta:
                            scroll_delta = -1 * (event.delta // 6)  # 6 au lieu de 120 = 20x plus rapide
                        elif hasattr(event, 'num'):
                            scroll_delta = -20 if event.num == 4 else 20  # 20x plus rapide
                        else:
                            scroll_delta = -20
                        canvas.yview_scroll(scroll_delta, "units")
                    else:
                        # Pour tkinter standard - SCROLL ULTRA RAPIDE
                        parent = self.chat_frame.master
                        while parent and not hasattr(parent, 'yview_scroll'):
                            parent = parent.master
                        if parent:
                            # Amplifier le delta pour scroll MEGA ULTRA rapide (x60 plus rapide !)
                            if hasattr(event, 'delta') and event.delta:
                                scroll_delta = -1 * (event.delta // 2)  # 2 au lieu de 120 = 60x plus rapide !
                            elif hasattr(event, 'num'):
                                scroll_delta = -60 if event.num == 4 else 60  # 60x plus rapide
                            else:
                                scroll_delta = -60
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


        text_widget = tk.Text(
            bubble,
            width=text_width,
            height=2,  # Valeur initiale minimale
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

        print(f"[DEBUG] Bulle USER: hauteur={text_widget.cget('height')}, parent={text_widget.master}")

        self.insert_formatted_text_tkinter(text_widget, text)
        # Ajustement parfait de la hauteur après rendu
        def adjust_height_later():
            text_widget.update_idletasks()
            line_count = int(text_widget.index("end-1c").split(".")[0])
            text_widget.configure(height=max(2, line_count))
            text_widget.update_idletasks()
            # Scroll automatique après ajustement
            if hasattr(self, '_force_scroll_to_bottom'):
                self._force_scroll_to_bottom()
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
        self.setup_scroll_forwarding(text_widget)
        
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

            # ⚡ SOLUTION: Appliquer le scroll forwarding SUR LE CONTAINER aussi ici !
            def setup_container_scroll_forwarding_simple(container):
                """Configure le scroll forwarding sur le container IA (version simple)"""
                def forward_from_container(event):
                    try:
                        if hasattr(self, 'chat_frame') and self.use_ctk and hasattr(self.chat_frame, '_parent_canvas'):
                            canvas = self.chat_frame._parent_canvas
                            if hasattr(event, 'delta') and event.delta:
                                # AMPLIFICATION 60x pour égaler la vitesse utilisateur
                                scroll_delta = -1 * (event.delta // 6) * 60
                            else:
                                scroll_delta = -20 * 60
                            canvas.yview_scroll(scroll_delta, "units")
                        return "break"
                    except Exception as e:
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
                if hasattr(self, 'chat_frame'):
                    if self.use_ctk and hasattr(self.chat_frame, '_parent_canvas'):
                        # Pour CustomTkinter ScrollableFrame - MÊME LOGIQUE QUE USER
                        canvas = self.chat_frame._parent_canvas
                        # EXACTEMENT la même amplification que les bulles USER
                        if hasattr(event, 'delta') and event.delta:
                            scroll_delta = -1 * (event.delta // 6)  # MÊME que USER
                        elif hasattr(event, 'num'):
                            scroll_delta = -20 if event.num == 4 else 20  # MÊME que USER
                        else:
                            scroll_delta = -20
                        canvas.yview_scroll(scroll_delta, "units")
                    else:
                        # Pour tkinter standard - MÊME LOGIQUE QUE USER
                        parent = self.chat_frame.master
                        while parent and not hasattr(parent, 'yview_scroll'):
                            parent = parent.master
                        if parent:
                            # EXACTEMENT la même amplification que les bulles USER
                            if hasattr(event, 'delta') and event.delta:
                                scroll_delta = -1 * (event.delta // 6)  # MÊME que USER
                            elif hasattr(event, 'num'):
                                scroll_delta = -20 if event.num == 4 else 20  # MÊME que USER
                            else:
                                scroll_delta = -20
                            parent.yview_scroll(scroll_delta, "units")
            except Exception as e:
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
            print(f"[DEBUG IA SCROLL PARENT] Event capturé par parent: {event}")
            # Transférer vers notre fonction
            return forward_scroll_to_page(event)
        
        # Ajouter les bindings au parent ET au text widget
        parent_frame.bind("<MouseWheel>", parent_test_event)
        parent_frame.bind("<Button-4>", parent_test_event)
        parent_frame.bind("<Button-5>", parent_test_event)
        
        print(f"✅ Scroll ultra rapide configuré pour widget Text IA ET son parent")

    def start_typing_animation_dynamic(self, text_widget, full_text):
        """Animation caractère par caractère avec formatage progressif intelligent"""
        # DÉSACTIVER la saisie pendant l'animation
        self.set_input_state(False)
        
        # Réinitialiser le widget
        text_widget.configure(state="normal")
        text_widget.delete("1.0", "end")
        
        # DÉSACTIVER le scroll pendant l'animation pour éviter les saccades
        self._disable_text_scroll(text_widget)
        
        # NOUVEAU : Pré-traiter le texte pour remplacer les liens par leurs titres
        processed_text, link_mapping = self._preprocess_links_for_animation(full_text)
        
        # NOUVEAU : Pré-analyser les blocs de code pour la coloration en temps réel
        self._code_blocks_map = self._preanalyze_code_blocks(processed_text)
        
        # Variables pour l'animation CARACTÈRE PAR CARACTÈRE
        self.typing_index = 0
        self.typing_text = processed_text  # Utiliser le texte pré-traité
        self.typing_widget = text_widget
        self.typing_speed = 1
        
        # Stocker le mapping des liens pour plus tard
        if link_mapping:
            self._pending_links = link_mapping
        
        # NOUVEAU : Réinitialiser les positions formatées
        self._formatted_positions = set()
        
        print(f"[DEBUG] Animation caractère par caractère - {len(processed_text)} caractères total")
        
        # Configurer tous les tags de formatage
        self._configure_all_formatting_tags(text_widget)
        
        # Configuration spéciale du tag 'normal' pour l'animation SANS formatage
        text_widget.tag_configure("normal", font=('Segoe UI', 12), foreground=self.colors['text_primary'])

        # Flag d'interruption
        self._typing_interrupted = False
        
        # Démarrer l'animation caractère par caractère
        self.continue_typing_animation_dynamic()

    def _preprocess_links_for_animation(self, text):
        """Pré-traite le texte pour remplacer les liens [titre](url) par juste le titre pendant l'animation"""
        import re
        
        # Pattern pour détecter [titre](url)
        link_pattern = r'\[([^\]]+)\]\(([^)]+)\)'
        
        # Initialiser le mapping des liens pour la conversion finale
        if not hasattr(self, '_pending_links'):
            self._pending_links = {}
        
        def replace_link(match):
            title = match.group(1)
            url = match.group(2)
            
            # Stocker dans _pending_links avec le titre comme clé
            self._pending_links[title] = {
                'title': title,
                'url': url,
                'original': match.group(0)
            }
            
            # Retourner juste le titre (sans marqueur)
            return title
        
        # Remplacer tous les liens par leurs titres
        processed_text = re.sub(link_pattern, replace_link, text)
        
        print(f"[DEBUG] Liens prétraités: {len(self._pending_links)} liens trouvés")
        for title, data in self._pending_links.items():
            print(f"  '{data['title']}' -> {data['url']}")
        
        return processed_text, self._pending_links

    def _preanalyze_code_blocks(self, text):
        """Pré-analyse les blocs de code pour la coloration en temps réel"""
        import re
        
        code_blocks_map = {}  # Position -> (language, token_type)
        
        # Pattern pour détecter les blocs de code avec langage
        code_block_pattern = r'```(\w+)?\n?(.*?)```'
        
        print(f"[DEBUG] Pré-analyse des blocs de code dans {len(text)} caractères")
        
        for match in re.finditer(code_block_pattern, text, re.DOTALL):
            language = (match.group(1) or "text").lower()
            code_content = match.group(2).strip() if match.group(2) else ""
            
            if not code_content:
                continue
                
            print(f"[DEBUG] Bloc trouvé: {language}, position {match.start()}-{match.end()}")
            
            # Marquer la zone des backticks d'ouverture comme "hidden"
            opening_start = match.start()
            opening_end = match.start() + len(f"```{match.group(1) or ''}")
            for pos in range(opening_start, opening_end + 1):
                if pos < len(text):
                    code_blocks_map[pos] = (language, "code_block_marker")
            
            # Analyser le contenu du code selon le langage
            code_start = match.start() + len(f"```{match.group(1) or ''}")
            # Chercher le \n après ```language
            newline_pos = text.find('\n', code_start)
            if newline_pos != -1:
                code_start = newline_pos + 1
            else:
                code_start += 1  # Pas de \n trouvé, continuer quand même
            
            if language == 'python':
                self._analyze_python_tokens(code_content, code_start, code_blocks_map)
            elif language in ['javascript', 'js']:
                self._analyze_javascript_tokens(code_content, code_start, code_blocks_map)
            elif language == 'css':
                self._analyze_css_tokens(code_content, code_start, code_blocks_map)
            elif language in ['html', 'xml']:
                self._analyze_html_tokens(code_content, code_start, code_blocks_map)
            elif language in ['bash', 'shell', 'sh']:
                self._analyze_bash_tokens(code_content, code_start, code_blocks_map)
            elif language in ['sql', 'mysql', 'postgresql', 'sqlite']:
                self._analyze_sql_tokens(code_content, code_start, code_blocks_map)
            else:
                # Code générique
                for i, char in enumerate(code_content):
                    pos = code_start + i
                    # Pas besoin de vérifier self.typing_text ici car on travaille sur le texte passé en paramètre
                    code_blocks_map[pos] = (language, "code_block")
            
            # Marquer la zone des backticks de fermeture comme "hidden"
            closing_start = match.end() - 3
            for pos in range(closing_start, match.end()):
                if pos < len(text):
                    code_blocks_map[pos] = (language, "code_block_marker")
        
        print(f"[DEBUG] Pré-analyse terminée: {len(code_blocks_map)} positions mappées")
        return code_blocks_map

    def _analyze_python_tokens(self, code, start_offset, code_map):
        """Analyse les tokens Python pour la coloration en temps réel"""
        try:
            from pygments import lex
            from pygments.lexers import PythonLexer
            
            lexer = PythonLexer()
            current_pos = start_offset
            
            for token_type, value in lex(code, lexer):
                for i in range(len(value)):
                    # Utiliser la longueur totale du texte passé en paramètre
                    pos = current_pos + i
                    if hasattr(self, 'typing_text') and pos < len(self.typing_text):
                        tag = str(token_type)
                        code_map[pos] = ("python", tag)
                current_pos += len(value)
                
        except ImportError:
            # Fallback sans Pygments
            self._analyze_python_simple(code, start_offset, code_map)
    
    def _analyze_python_simple(self, code, start_offset, code_map):
        """Analyse Python simple sans Pygments"""
        import keyword
        import re
        
        keywords = set(keyword.kwlist)
        
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
        
        lines = code.split('\n')
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
                    if hasattr(self, 'typing_text') and pos < len(self.typing_text):
                        code_map[pos] = ("python", tag)
            
            current_pos += len(line) + 1  # +1 pour le \n
    
    def _analyze_javascript_tokens(self, code, start_offset, code_map):
        """Analyse les tokens JavaScript pour la coloration en temps réel"""
        import re
        
        js_keywords = {
            'var', 'let', 'const', 'function', 'return', 'if', 'else', 'for', 'while', 'do',
            'switch', 'case', 'default', 'break', 'continue', 'try', 'catch', 'finally',
            'throw', 'new', 'this', 'super', 'class', 'extends', 'import', 'export',
            'from', 'async', 'await', 'yield', 'typeof', 'instanceof', 'in', 'of',
            'true', 'false', 'null', 'undefined'
        }
        
        # Pattern pour identifier différents éléments JS
        token_pattern = r'''
            (//.*$)|                     # Commentaires //
            (/\*.*?\*/)|                 # Commentaires /* */
            ("(?:[^"\\]|\\.)*")|         # Chaînes double quotes
            ('(?:[^'\\]|\\.)*')|         # Chaînes simple quotes
            (`(?:[^`\\]|\\.)*`)|         # Template literals
            (\b\d+\.?\d*\b)|             # Nombres
            (\b[a-zA-Z_$]\w*\b)|         # Identifiants
            ([+\-*/%=<>!&|^~]|===|!==|==|!=|<=|>=|&&|\|\||<<|>>|\+=|-=|\*=|/=|%=|&=|\|=|\^=|<<=|>>=|\+\+|--) # Opérateurs
        '''
        
        lines = code.split('\n')
        current_pos = start_offset
        
        for line in lines:
            for match in re.finditer(token_pattern, line, re.VERBOSE):
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
                    if hasattr(self, 'typing_text') and pos < len(self.typing_text):
                        code_map[pos] = ("javascript", tag)
            
            current_pos += len(line) + 1
    
    def _analyze_css_tokens(self, code, start_offset, code_map):
        """Analyse les tokens CSS pour la coloration en temps réel"""
        # Implémentation simplifiée pour CSS
        for i, char in enumerate(code):
            pos = start_offset + i
            if hasattr(self, 'typing_text') and pos < len(self.typing_text):
                code_map[pos] = ("css", "css_selector")  # Tag générique pour l'instant
    
    def _analyze_html_tokens(self, code, start_offset, code_map):
        """Analyse les tokens HTML pour la coloration en temps réel"""
        # Implémentation simplifiée pour HTML
        for i, char in enumerate(code):
            pos = start_offset + i
            if hasattr(self, 'typing_text') and pos < len(self.typing_text):
                code_map[pos] = ("html", "html_tag")  # Tag générique pour l'instant
    
    def _analyze_bash_tokens(self, code, start_offset, code_map):
        """Analyse les tokens Bash pour la coloration en temps réel"""
        # Implémentation simplifiée pour Bash
        for i, char in enumerate(code):
            pos = start_offset + i
            if hasattr(self, 'typing_text') and pos < len(self.typing_text):
                code_map[pos] = ("bash", "bash_command")  # Tag générique pour l'instant
    
    def _analyze_sql_tokens(self, code, start_offset, code_map):
        """Analyse les tokens SQL pour la coloration en temps réel"""
        # Implémentation simplifiée pour SQL
        for i, char in enumerate(code):
            pos = start_offset + i
            if hasattr(self, 'typing_text') and pos < len(self.typing_text):
                code_map[pos] = ("sql", "sql_keyword")  # Tag générique pour l'instant

    def _split_text_for_progressive_formatting(self, text):
        """Divise le texte en segments plus larges pour une animation fluide"""
        import re
        segments = []
        
        # Diviser par phrases ou groupes de mots (5-10 caractères par segment)
        words = re.findall(r'\S+\s*', text)
        
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
        if not hasattr(self, 'typing_widget') or not hasattr(self, 'typing_text'):
            return
        
        if getattr(self, '_typing_interrupted', False):
            self.finish_typing_animation_dynamic(interrupted=True)
            return
        
        # Vérifier si on a terminé
        if self.typing_index >= len(self.typing_text):
            self.finish_typing_animation_dynamic()
            return
        
        try:
            # Ajouter le caractère suivant
            char = self.typing_text[self.typing_index]
            
            self.typing_widget.configure(state='normal')
            
            # NOUVEAU : Déterminer le tag à utiliser selon la position
            tag_to_use = "normal"  # Tag par défaut
            
            # Vérifier si ce caractère est dans un bloc de code
            if hasattr(self, '_code_blocks_map') and self.typing_index in self._code_blocks_map:
                language, token_type = self._code_blocks_map[self.typing_index]
                
                # Masquer les marqueurs de blocs de code (```)
                if token_type == "code_block_marker":
                    tag_to_use = "hidden"  # Les ``` seront cachés
                else:
                    tag_to_use = token_type  # Utiliser le tag de coloration syntaxique
                    
                print(f"[DEBUG] Position {self.typing_index}: char='{char}' -> tag='{tag_to_use}' (langue={language})")
            
            # Insérer le caractère avec le bon tag
            self.typing_widget.insert('end', char, tag_to_use)
            
            # NOUVEAU : Appliquer la coloration syntaxique en temps réel pour les blocs de code
            self._apply_realtime_syntax_coloring(self.typing_widget, self.typing_index, char)
            
            # Incrémenter l'index
            self.typing_index += 1
            
            # === FORMATAGE PROGRESSIF INTELLIGENT ===
            should_format = False
            
            # Détecter completion d'éléments markdown UNIQUEMENT pour les vrais patterns
            if char == '*':
                current_content = self.typing_widget.get("1.0", "end-1c")
                # NOUVELLE LOGIQUE : Ne formater QUE si on a un vrai pattern **texte**
                if current_content.endswith('**') and len(current_content) >= 4:
                    # Vérifier qu'il y a vraiment un pattern **texte** complet
                    import re
                    # Chercher le dernier pattern **texte** complet dans le contenu
                    bold_pattern = r'\*\*([^*\n]{1,200}?)\*\*$'
                    if re.search(bold_pattern, current_content):
                        should_format = True
                    else:
                        pass
            elif char == '`':
                # Fin possible de `code` - vérifier que c'est un vrai pattern
                current_content = self.typing_widget.get("1.0", "end-1c")
                import re
                code_pattern = r'`([^`\n]+)`$'
                if re.search(code_pattern, current_content):
                    should_format = True
                else:
                    pass
            elif char == "'":
                # Fin possible de '''docstring''' - vérifier qu'on a 3 quotes
                current_content = self.typing_widget.get("1.0", "end-1c")
                if current_content.endswith("'''"):
                    import re
                    docstring_pattern = r"'''([^']*?)'''$"
                    if re.search(docstring_pattern, current_content, re.DOTALL):
                        should_format = True
                    else:
                        pass
            elif char == ' ':
                # NE PAS formater pendant l'écriture d'un titre - attendre la fin de ligne
                # Ancien code qui causait le formatage partiel des titres
                pass  # On attend le \n pour formater les titres complets
            elif char == '\n':
                # Nouvelle ligne - MAINTENANT on peut formater les titres complets
                should_format = True
            elif self.typing_index % 50 == 0:  # Formatage périodique moins fréquent
                should_format = True
            
            # Appliquer le formatage unifié si nécessaire
            if should_format:
                self._apply_unified_progressive_formatting(self.typing_widget)
            
            # Ajuster la hauteur aux retours à la ligne
            if char == '\n':
                self.adjust_text_widget_height(self.typing_widget)
                self.root.after(5, self._smart_scroll_follow_animation)
                        
            self.typing_widget.configure(state='disabled')
            
            # Planifier le prochain caractère (animation fluide)
            delay = 10
            self.root.after(delay, self.continue_typing_animation_dynamic)
            
        except tk.TclError:
            self.finish_typing_animation_dynamic(interrupted=True)

    def _apply_realtime_syntax_coloring(self, text_widget, current_index, current_char):
        """Applique la coloration syntaxique en temps réel pendant l'animation"""
        try:
            # Obtenir le contenu actuel
            current_text = text_widget.get("1.0", "end-1c")
            
            # Détecter si on est dans un bloc de code
            in_code_block, language, code_start = self._detect_current_code_block(current_text, current_index)
            
            if in_code_block and language:
                # Récupérer juste le bout de code qui nous intéresse (derniers mots/tokens)
                analysis_start = max(0, current_index - 50)  # Analyser les 50 derniers caractères
                text_to_analyze = current_text[analysis_start:current_index + 1]
                
                # Appliquer la coloration selon le langage
                if language == 'python':
                    self._apply_python_realtime_coloring(text_widget, text_to_analyze, analysis_start)
                elif language in ['javascript', 'js']:
                    self._apply_javascript_realtime_coloring(text_widget, text_to_analyze, analysis_start)
                elif language == 'css':
                    self._apply_css_realtime_coloring(text_widget, text_to_analyze, analysis_start)
                elif language in ['html', 'xml']:
                    self._apply_html_realtime_coloring(text_widget, text_to_analyze, analysis_start)
                elif language in ['bash', 'shell', 'sh']:
                    self._apply_bash_realtime_coloring(text_widget, text_to_analyze, analysis_start)
                elif language in ['sql', 'mysql', 'postgresql', 'sqlite']:
                    self._apply_sql_realtime_coloring(text_widget, text_to_analyze, analysis_start)
                    
        except Exception as e:
            # Ignorer les erreurs de coloration pour ne pas casser l'animation
            pass

    def _detect_current_code_block(self, text, current_index):
        """Détecte si on est actuellement dans un bloc de code et retourne le langage"""
        import re
        
        # Chercher tous les blocs de code jusqu'à la position actuelle
        text_up_to_current = text[:current_index + 1]
        
        # Pattern pour détecter les blocs de code
        code_block_pattern = r'```(\w+)?\n?(.*?)(?:```|$)'
        
        # Trouver tous les blocs de code
        blocks = list(re.finditer(code_block_pattern, text_up_to_current, re.DOTALL))
        
        for block in reversed(blocks):  # Commencer par le dernier bloc
            block_start = block.start()
            language = (block.group(1) or "text").lower()
            
            # Vérifier si on est dans ce bloc
            content_start = block.start() + len(f"```{block.group(1) or ''}")
            # Trouver le newline après ```language
            newline_pos = text_up_to_current.find('\n', content_start)
            if newline_pos != -1:
                content_start = newline_pos + 1
            
            # Si la position actuelle est dans ce bloc et qu'il n'est pas fermé
            if content_start <= current_index and not text_up_to_current[block.start():].count('```') >= 2:
                return True, language, content_start
        
        return False, None, None

    def _apply_python_realtime_coloring(self, text_widget, text_segment, start_offset):
        """Applique la coloration Python en temps réel sur un segment de texte"""
        import re
        import keyword
        
        # Mots-clés Python
        python_keywords = set(keyword.kwlist)
        python_builtins = {'print', 'len', 'str', 'int', 'float', 'list', 'dict', 'set', 'tuple', 'range', 'enumerate', 'zip', 'open', 'input', 'type', 'isinstance', 'hasattr', 'getattr', 'setattr'}
        
        # Patterns pour différents éléments
        patterns = [
            (r'#.*$', 'Token.Comment'),                    # Commentaires
            (r'""".*?"""', 'docstring'),                   # Docstrings
            (r'"(?:[^"\\]|\\.)*"', 'Token.Literal.String'),# Chaînes double quotes
            (r"'(?:[^'\\]|\\.)*'", 'Token.Literal.String'),# Chaînes simple quotes
            (r'\b\d+\.?\d*\b', 'Token.Literal.Number'),   # Nombres
            (r'\b[a-zA-Z_]\w*\b', 'identifier'),          # Identifiants
        ]
        
        # Analyser chaque pattern
        for pattern, token_type in patterns:
            for match in re.finditer(pattern, text_segment, re.MULTILINE):
                match_start = start_offset + match.start()
                match_end = start_offset + match.end()
                
                # Convertir en positions Tkinter
                start_line, start_col = self._index_to_line_col(text_widget, match_start)
                end_line, end_col = self._index_to_line_col(text_widget, match_end)
                
                start_pos = f"{start_line}.{start_col}"
                end_pos = f"{end_line}.{end_col}"
                
                # Déterminer le tag final
                final_tag = token_type
                if token_type == 'identifier':
                    word = match.group()
                    if word in python_keywords:
                        final_tag = 'Token.Keyword'
                    elif word in python_builtins:
                        final_tag = 'Token.Name.Builtin'
                    else:
                        final_tag = 'Token.Name'
                
                # Appliquer le tag
                try:
                    text_widget.tag_add(final_tag, start_pos, end_pos)
                except:
                    pass

    def _apply_javascript_realtime_coloring(self, text_widget, text_segment, start_offset):
        """Applique la coloration JavaScript en temps réel"""
        import re
        
        js_keywords = {'var', 'let', 'const', 'function', 'return', 'if', 'else', 'for', 'while', 'do', 'switch', 'case', 'default', 'break', 'continue', 'try', 'catch', 'finally', 'throw', 'new', 'this', 'super', 'class', 'extends', 'import', 'export', 'from', 'async', 'await', 'yield', 'typeof', 'instanceof', 'in', 'of', 'true', 'false', 'null', 'undefined'}
        
        patterns = [
            (r'//.*$', 'Token.Comment'),
            (r'/\*.*?\*/', 'Token.Comment'),
            (r'"(?:[^"\\]|\\.)*"', 'Token.Literal.String'),
            (r"'(?:[^'\\]|\\.)*'", 'Token.Literal.String'),
            (r'`(?:[^`\\]|\\.)*`', 'Token.Literal.String'),
            (r'\b\d+\.?\d*\b', 'Token.Literal.Number'),
            (r'\b[a-zA-Z_$]\w*\b', 'identifier'),
        ]
        
        for pattern, token_type in patterns:
            for match in re.finditer(pattern, text_segment, re.MULTILINE):
                match_start = start_offset + match.start()
                match_end = start_offset + match.end()
                
                start_line, start_col = self._index_to_line_col(text_widget, match_start)
                end_line, end_col = self._index_to_line_col(text_widget, match_end)
                
                start_pos = f"{start_line}.{start_col}"
                end_pos = f"{end_line}.{end_col}"
                
                final_tag = token_type
                if token_type == 'identifier':
                    word = match.group()
                    if word in js_keywords:
                        final_tag = 'Token.Keyword'
                    else:
                        final_tag = 'Token.Name'
                
                try:
                    text_widget.tag_add(final_tag, start_pos, end_pos)
                except:
                    pass

    def _apply_css_realtime_coloring(self, text_widget, text_segment, start_offset):
        """Applique la coloration CSS en temps réel"""
        import re
        
        css_properties = {'color', 'background', 'font-size', 'margin', 'padding', 'border', 'width', 'height', 'display', 'position', 'top', 'left', 'right', 'bottom', 'z-index', 'opacity', 'transform', 'transition', 'animation', 'flex', 'grid'}
        css_values = {'auto', 'none', 'inherit', 'initial', 'unset', 'block', 'inline', 'flex', 'grid', 'absolute', 'relative', 'fixed', 'sticky', 'hidden', 'visible'}
        css_pseudos = {'hover', 'active', 'focus', 'visited', 'first-child', 'last-child', 'nth-child', 'before', 'after'}
        
        patterns = [
            (r'/\*.*?\*/', 'Token.Comment'),                      # Commentaires /* */
            (r'"(?:[^"\\]|\\.)*"', 'Token.Literal.String'),       # Chaînes double quotes
            (r"'(?:[^'\\]|\\.)*'", 'Token.Literal.String'),       # Chaînes simple quotes
            (r'#[0-9a-fA-F]{3,6}\b', 'Token.Literal.Number'),     # Couleurs hexadécimales
            (r'\b\d+(?:px|em|rem|%|vh|vw|pt)?\b', 'Token.Literal.Number'), # Dimensions
            (r'\.[a-zA-Z_][\w-]*', 'Token.Name.Class'),           # Sélecteurs de classe .class
            (r'#[a-zA-Z_][\w-]*', 'Token.Name.Variable'),         # Sélecteurs d'ID #id
            (r':[a-zA-Z-]+', 'Token.Name.Function'),              # Pseudo-sélecteurs :hover
            (r'[a-zA-Z-]+(?=\s*:)', 'Token.Name.Attribute'),      # Propriétés CSS
            (r'\b[a-zA-Z_][\w-]*\b', 'identifier'),               # Identifiants
        ]
        
        for pattern, token_type in patterns:
            for match in re.finditer(pattern, text_segment, re.MULTILINE):
                match_start = start_offset + match.start()
                match_end = start_offset + match.end()
                
                start_line, start_col = self._index_to_line_col(text_widget, match_start)
                end_line, end_col = self._index_to_line_col(text_widget, match_end)
                
                start_pos = f"{start_line}.{start_col}"
                end_pos = f"{end_line}.{end_col}"
                
                final_tag = token_type
                if token_type == 'identifier':
                    word = match.group()
                    if word in css_properties:
                        final_tag = 'Token.Name.Attribute'  # Propriétés en couleur attribut
                    elif word in css_values:
                        final_tag = 'Token.Keyword'  # Valeurs en couleur keyword
                    else:
                        final_tag = 'Token.Name'
                
                try:
                    text_widget.tag_add(final_tag, start_pos, end_pos)
                except:
                    pass

    def _apply_html_realtime_coloring(self, text_widget, text_segment, start_offset):
        """Applique la coloration HTML en temps réel"""
        import re
        
        html_tags = {'html', 'head', 'body', 'title', 'meta', 'link', 'script', 'style', 'div', 'span', 'p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'a', 'img', 'ul', 'ol', 'li', 'table', 'tr', 'td', 'th', 'form', 'input', 'button', 'textarea', 'select', 'option', 'nav', 'header', 'footer', 'section', 'article', 'aside', 'main'}
        html_attributes = {'id', 'class', 'src', 'href', 'alt', 'title', 'style', 'type', 'name', 'value', 'placeholder', 'required', 'disabled', 'readonly', 'checked', 'selected'}
        
        patterns = [
            (r'<!--.*?-->', 'Token.Comment'),                     # Commentaires HTML
            (r'"(?:[^"\\]|\\.)*"', 'Token.Literal.String'),       # Chaînes double quotes (valeurs d'attributs)
            (r"'(?:[^'\\]|\\.)*'", 'Token.Literal.String'),       # Chaînes simple quotes
            (r'<!\s*DOCTYPE[^>]*>', 'Token.Keyword'),             # DOCTYPE
            (r'</?[a-zA-Z][a-zA-Z0-9]*', 'Token.Name.Tag'),       # Balises <div>, </div>
            (r'\b[a-zA-Z-]+(?=\s*=)', 'Token.Name.Attribute'),    # Attributs HTML
            (r'[&][a-zA-Z]+[;]', 'Token.Name.Entity'),            # Entités HTML &nbsp;
            (r'[<>=/]', 'Token.Operator'),                        # Opérateurs HTML
        ]
        
        for pattern, token_type in patterns:
            for match in re.finditer(pattern, text_segment, re.MULTILINE | re.DOTALL):
                match_start = start_offset + match.start()
                match_end = start_offset + match.end()
                
                start_line, start_col = self._index_to_line_col(text_widget, match_start)
                end_line, end_col = self._index_to_line_col(text_widget, match_end)
                
                start_pos = f"{start_line}.{start_col}"
                end_pos = f"{end_line}.{end_col}"
                
                final_tag = token_type
                
                try:
                    text_widget.tag_add(final_tag, start_pos, end_pos)
                except:
                    pass

    def _apply_bash_realtime_coloring(self, text_widget, text_segment, start_offset):
        """Applique la coloration Bash en temps réel"""
        import re
        
        bash_keywords = {'if', 'then', 'else', 'elif', 'fi', 'for', 'while', 'do', 'done', 'case', 'esac', 'function', 'return', 'exit', 'break', 'continue', 'local', 'export', 'declare', 'readonly', 'unset', 'source', 'alias', 'history', 'jobs', 'bg', 'fg', 'nohup', 'disown'}
        bash_commands = {'ls', 'cd', 'pwd', 'mkdir', 'rmdir', 'rm', 'cp', 'mv', 'touch', 'find', 'grep', 'sed', 'awk', 'sort', 'uniq', 'head', 'tail', 'cat', 'less', 'more', 'chmod', 'chown', 'ps', 'top', 'kill', 'jobs', 'wget', 'curl', 'ssh', 'scp', 'rsync', 'tar', 'gzip', 'gunzip', 'zip', 'unzip', 'git', 'npm', 'pip', 'docker', 'sudo', 'su', 'which', 'whereis', 'man', 'info', 'help', 'echo', 'printf', 'read', 'test'}
        
        patterns = [
            (r'#.*$', 'Token.Comment'),                           # Commentaires
            (r'"(?:[^"\\]|\\.)*"', 'Token.Literal.String'),       # Chaînes double quotes
            (r"'(?:[^'\\]|\\.)*'", 'Token.Literal.String'),       # Chaînes simple quotes
            (r'`(?:[^`\\]|\\.)*`', 'Token.Literal.String'),       # Commandes entre backticks
            (r'\$\{[^}]+\}', 'Token.Name.Variable'),              # Variables ${var}
            (r'\$[a-zA-Z_][a-zA-Z0-9_]*', 'Token.Name.Variable'), # Variables $var
            (r'\$[0-9]+', 'Token.Name.Variable'),                 # Arguments $1, $2, etc.
            (r'\$[@*#?$!0]', 'Token.Name.Variable'),              # Variables spéciales $@, $*, etc.
            (r'\b\d+\b', 'Token.Literal.Number'),                 # Nombres
            (r'[|&;()<>]|\|\||\&\&', 'Token.Operator'),           # Opérateurs
            (r'--?[a-zA-Z-]+', 'Token.Name.Attribute'),           # Options --option, -o
            (r'\b[a-zA-Z_][a-zA-Z0-9_]*\b', 'identifier'),        # Identifiants
        ]
        
        for pattern, token_type in patterns:
            for match in re.finditer(pattern, text_segment, re.MULTILINE):
                match_start = start_offset + match.start()
                match_end = start_offset + match.end()
                
                start_line, start_col = self._index_to_line_col(text_widget, match_start)
                end_line, end_col = self._index_to_line_col(text_widget, match_end)
                
                start_pos = f"{start_line}.{start_col}"
                end_pos = f"{end_line}.{end_col}"
                
                final_tag = token_type
                if token_type == 'identifier':
                    word = match.group()
                    if word in bash_keywords:
                        final_tag = 'Token.Keyword'
                    elif word in bash_commands:
                        final_tag = 'Token.Name.Builtin'  # Commandes en couleur builtin
                    else:
                        final_tag = 'Token.Name'
                
                try:
                    text_widget.tag_add(final_tag, start_pos, end_pos)
                except:
                    pass

    def _apply_sql_realtime_coloring(self, text_widget, text_segment, start_offset):
        """Applique la coloration SQL en temps réel"""
        import re
        
        sql_keywords = {'SELECT', 'FROM', 'WHERE', 'INSERT', 'UPDATE', 'DELETE', 'CREATE', 'DROP', 'ALTER', 'TABLE', 'DATABASE', 'INDEX', 'VIEW', 'PROCEDURE', 'FUNCTION', 'TRIGGER', 'JOIN', 'INNER', 'LEFT', 'RIGHT', 'FULL', 'OUTER', 'ON', 'AS', 'AND', 'OR', 'NOT', 'IN', 'BETWEEN', 'LIKE', 'IS', 'NULL', 'GROUP', 'BY', 'ORDER', 'HAVING', 'LIMIT', 'OFFSET', 'UNION', 'DISTINCT', 'COUNT', 'SUM', 'AVG', 'MIN', 'MAX', 'CASE', 'WHEN', 'THEN', 'ELSE', 'END', 'IF', 'EXISTS'}
        sql_types = {'INT', 'INTEGER', 'VARCHAR', 'CHAR', 'TEXT', 'BOOLEAN', 'BOOL', 'DATE', 'DATETIME', 'TIMESTAMP', 'TIME', 'FLOAT', 'DOUBLE', 'DECIMAL', 'NUMERIC', 'BLOB', 'JSON', 'XML'}
        
        patterns = [
            (r'--.*$', 'Token.Comment'),                          # Commentaires --
            (r'/\*.*?\*/', 'Token.Comment'),                      # Commentaires /* */
            (r"'(?:[^'\\]|\\.)*'", 'Token.Literal.String'),       # Chaînes simple quotes
            (r'"(?:[^"\\]|\\.)*"', 'Token.Literal.String'),       # Chaînes double quotes
            (r'\b\d+\.?\d*\b', 'Token.Literal.Number'),           # Nombres
            (r'[=<>!]+|<=|>=|<>|!=', 'Token.Operator'),           # Opérateurs de comparaison
            (r'[+\-*/%]', 'Token.Operator'),                      # Opérateurs arithmétiques
            (r'[(),;]', 'Token.Punctuation'),                     # Ponctuation
            (r'\b[a-zA-Z_][a-zA-Z0-9_]*\b', 'identifier'),        # Identifiants
        ]
        
        for pattern, token_type in patterns:
            for match in re.finditer(pattern, text_segment, re.MULTILINE | re.DOTALL):
                match_start = start_offset + match.start()
                match_end = start_offset + match.end()
                
                start_line, start_col = self._index_to_line_col(text_widget, match_start)
                end_line, end_col = self._index_to_line_col(text_widget, match_end)
                
                start_pos = f"{start_line}.{start_col}"
                end_pos = f"{end_line}.{end_col}"
                
                final_tag = token_type
                if token_type == 'identifier':
                    word = match.group().upper()  # SQL est case-insensitive
                    if word in sql_keywords:
                        final_tag = 'Token.Keyword'
                    elif word in sql_types:
                        final_tag = 'Token.Keyword.Type'
                    else:
                        final_tag = 'Token.Name'
                
                try:
                    text_widget.tag_add(final_tag, start_pos, end_pos)
                except:
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
            lines = content_up_to_index.split('\n')
            line_num = len(lines)
            col_num = len(lines[-1]) if lines else 0
            
            return line_num, col_num
        except:
            return 1, 0

    def _apply_unified_progressive_formatting(self, text_widget):
        """MÉTHODE UNIFIÉE SIMPLIFIÉE : Formatage progressif sécurisé"""
        import re
        
        try:
            # Initialiser le tracking si nécessaire
            if not hasattr(self, '_formatted_positions'):
                self._formatted_positions = set()
            
            text_widget.configure(state='normal')
            
            # === FORMATAGE GRAS **texte** AVEC SEARCH TKINTER ===
            start_pos = "1.0"
            while True:
                # Chercher le prochain **
                pos_start = text_widget.search("**", start_pos, "end")
                if not pos_start:
                    break
                
                # Chercher le ** de fermeture
                search_start = text_widget.index(f"{pos_start}+2c")
                pos_end = text_widget.search("**", search_start, "end")
                
                if pos_end:
                    # Vérifier que le contenu entre les ** est valide (pas de *, pas trop long)
                    content_start = text_widget.index(f"{pos_start}+2c")
                    content = text_widget.get(content_start, pos_end)
                    
                    # Valider le contenu
                    if content and len(content) <= 200 and '*' not in content and '\n' not in content:
                        # Position string pour tracking
                        pos_str = str(pos_start)
                        
                        if pos_str not in self._formatted_positions:
                            # Supprimer **texte**
                            end_pos_full = text_widget.index(f"{pos_end}+2c")
                            text_widget.delete(pos_start, end_pos_full)
                            
                            # Insérer juste texte en gras
                            text_widget.insert(pos_start, content, 'bold')
                            
                            self._formatted_positions.add(pos_str)
                            
                            # Continuer à partir de la position actuelle
                            start_pos = pos_start
                        else:
                            start_pos = text_widget.index(f"{pos_end}+1c")
                    else:
                        start_pos = text_widget.index(f"{pos_start}+1c")
                else:
                    start_pos = text_widget.index(f"{pos_start}+1c")
            
            # === FORMATAGE LIENS PRÉTRAITÉS (DÉTECTION DES TITRES) ===
            # Les liens ont été remplacés par leurs titres, on doit les détecter et les marquer
            if hasattr(self, '_pending_links'):
                for title, link_data in self._pending_links.items():
                    # Chercher toutes les occurrences de ce titre
                    start_pos = "1.0"
                    while True:
                        pos_start = text_widget.search(title, start_pos, "end")
                        if not pos_start:
                            break
                        
                        pos_end = text_widget.index(f"{pos_start}+{len(title)}c")
                        pos_str = str(pos_start)
                        
                        # Vérifier que ce n'est pas déjà formaté et que c'est exactement le titre
                        current_text = text_widget.get(pos_start, pos_end)
                        if current_text == title and pos_str not in self._formatted_positions:
                            # Marquer comme lien temporaire
                            text_widget.tag_add('link_temp', pos_start, pos_end)
                            self._formatted_positions.add(pos_str)
                        
                        start_pos = text_widget.index(f"{pos_start}+1c")

            # === FORMATAGE LIENS [titre](url) AVEC PRIORITÉ SUR TITRES (ANCIEN SYSTÈME POUR COMPATIBILITÉ) ===
            import re
            start_pos = "1.0"
            while True:
                # Chercher le prochain [
                pos_start = text_widget.search("[", start_pos, "end")
                if not pos_start:
                    break
                
                # Obtenir la ligne complète pour analyser le pattern
                line_start = text_widget.index(f"{pos_start} linestart")
                line_end = text_widget.index(f"{pos_start} lineend")
                line_content = text_widget.get(line_start, line_end)
                
                # Pattern pour détecter [titre](url)
                link_pattern = r'\[([^\]]+)\]\(([^)]+)\)'
                match = re.search(link_pattern, line_content)
                
                if match:
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
                        text_widget.insert(link_start, title, 'link_temp')
                        
                        # Stocker l'URL pour plus tard
                        if not hasattr(self, '_pending_links'):
                            self._pending_links = {}
                        self._pending_links[pos_str] = {'title': title, 'url': url, 'position': link_start}
                        
                        self._formatted_positions.add(pos_str)
                        
                        start_pos = link_start
                    else:
                        start_pos = text_widget.index(f"{pos_start}+1c")
                else:
                    start_pos = text_widget.index(f"{pos_start}+1c")
            
            # === FORMATAGE CODE `code` ===
            start_pos = "1.0"
            while True:
                # Chercher le prochain `
                pos_start = text_widget.search("`", start_pos, "end")
                if not pos_start:
                    break
                
                # Chercher le ` de fermeture
                search_start = text_widget.index(f"{pos_start}+1c")
                pos_end = text_widget.search("`", search_start, "end")
                
                if pos_end:
                    # Vérifier le contenu
                    content_start = text_widget.index(f"{pos_start}+1c")
                    content = text_widget.get(content_start, pos_end)
                    
                    if content and len(content) <= 100 and '`' not in content and '\n' not in content:
                        pos_str = str(pos_start)
                        
                        if pos_str not in self._formatted_positions:
                            # Supprimer `code`
                            end_pos_full = text_widget.index(f"{pos_end}+1c")
                            text_widget.delete(pos_start, end_pos_full)
                            
                            # Insérer code formaté
                            text_widget.insert(pos_start, content, 'code')
                            
                            self._formatted_positions.add(pos_str)
                            
                            start_pos = pos_start
                        else:
                            start_pos = text_widget.index(f"{pos_end}+1c")
                    else:
                        start_pos = text_widget.index(f"{pos_start}+1c")
                else:
                    start_pos = text_widget.index(f"{pos_start}+1c")
            
            # === FORMATAGE TITRES # ## ### ===
            start_pos = "1.0"
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
                
                # Obtenir la ligne complète
                line_end = text_widget.index(f"{pos_start} lineend")
                line_content = text_widget.get(pos_start, line_end)
                
                # Analyser la ligne pour détecter le niveau de titre
                import re
                title_match = re.match(r'^(#{1,3})\s+(.+)$', line_content)
                if title_match:
                    level = len(title_match.group(1))
                    # CORRECTION : Enlever les # mais garder tout le titre
                    title_without_hashes = title_match.group(2)  # "1. Objectif général"
                    
                    pos_str = str(pos_start)
                    if pos_str not in self._formatted_positions:
                        # Remplacer "## titre" par "titre" formaté (sans les ##)
                        text_widget.delete(pos_start, line_end)
                        text_widget.insert(pos_start, title_without_hashes, f'title_{level}')
                        
                        self._formatted_positions.add(pos_str)
                        
                        start_pos = text_widget.index(f"{pos_start}+1l")
                    else:
                        start_pos = text_widget.index(f"{pos_start}+1l")
                else:
                    start_pos = text_widget.index(f"{pos_start}+1c")
            
            # === FORMATAGE FINAL TITRES SANS # (pour re-formatage complet) ===
            # NOUVEAU : Détecter les titres qui n'ont plus de # (après le premier formatage)
            import re
            lines = text_widget.get("1.0", "end-1c").split('\n')
            
            for i, line in enumerate(lines):
                # Debug de toutes les lignes qui pourraient être des titres
                if line.strip() and (line.strip().startswith('1.') or line.strip().startswith('2.') or line.strip().startswith('3.') or line.strip().startswith('4.') or line.strip().startswith('5.')):
                    
                    line_start = f"{i+1}.0"
                    line_end = f"{i+1}.end"
                    line_content = text_widget.get(line_start, line_end)
                    
                    # Vérifier si ce n'est pas déjà formaté avec un tag de titre
                    existing_tags = text_widget.tag_names(line_start)
                    has_title_tag = any(tag.startswith('title_') for tag in existing_tags)
                    
                    # CORRECTION : Re-formater même si il y a déjà un tag, pour s'assurer que TOUTE la ligne est formatée
                    if line_content.strip():
                        # D'abord enlever tous les tags de titre existants
                        for tag in ['title_1', 'title_2', 'title_3']:
                            text_widget.tag_remove(tag, line_start, line_end)
                        
                        # Puis appliquer le formatage sur TOUTE la ligne
                        text_widget.tag_add('title_2', line_start, line_end)
                    else:
                        pass
            
            # === FORMATAGE DOCSTRINGS '''docstring''' ===
            start_pos = "1.0"
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
                    full_docstring = text_widget.get(pos_start, end_pos_full)  # '''contenu'''
                    
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
                            text_widget.insert(pos_start, full_docstring, 'docstring')
                            
                            self._formatted_positions.add(pos_str)
                            
                            start_pos = pos_start
                        else:
                            start_pos = text_widget.index(f"{pos_end}+1c")
                    else:
                        start_pos = text_widget.index(f"{pos_start}+1c")
                else:
                    start_pos = text_widget.index(f"{pos_start}+1c")
            
            text_widget.configure(state='disabled')
            
        except Exception as e:
            print(f"[ERREUR] Formatage unifié: {e}")
            if hasattr(text_widget, 'configure'):
                text_widget.configure(state='disabled')

    def _apply_immediate_progressive_formatting(self, text_widget):
        """Formatage progressif IMMÉDIAT et DIRECT"""
        import re
        
        try:
            # Obtenir le contenu actuel
            current_content = text_widget.get("1.0", "end-1c")
            
            # Pattern pour **texte** complet seulement
            bold_pattern = r'\*\*([^*\n]{1,50}?)\*\*'
            
            # Chercher et formater tous les **texte** complets
            for match in re.finditer(bold_pattern, current_content):
                try:
                    # Positions des balises et du contenu
                    full_start = match.start()
                    content_start = match.start(1)
                    content_end = match.end(1)
                    full_end = match.end()
                    
                    # Convertir en positions tkinter
                    tk_full_start = self._char_to_tkinter_position(current_content, full_start)
                    tk_content_start = self._char_to_tkinter_position(current_content, content_start)
                    tk_content_end = self._char_to_tkinter_position(current_content, content_end)
                    tk_full_end = self._char_to_tkinter_position(current_content, full_end)
                    
                    if all([tk_full_start, tk_content_start, tk_content_end, tk_full_end]):
                        # Supprimer les anciens tags sur cette zone
                        text_widget.tag_remove('bold', tk_full_start, tk_full_end)
                        text_widget.tag_remove('hidden', tk_full_start, tk_full_end)
                        text_widget.tag_remove('normal', tk_full_start, tk_full_end)
                        
                        # Configurer les tags s'ils n'existent pas
                        text_widget.tag_configure("bold", font=('Segoe UI', 12, 'bold'), foreground=self.colors['text_primary'])
                        text_widget.tag_configure("hidden", elide=True)
                        
                        # Appliquer le formatage : cacher ** et mettre en gras le contenu
                        text_widget.tag_add('hidden', tk_full_start, tk_content_start)  # Cacher **
                        text_widget.tag_add('bold', tk_content_start, tk_content_end)   # Gras
                        text_widget.tag_add('hidden', tk_content_end, tk_full_end)      # Cacher **
                        
                        print(f"[DEBUG] Formaté en gras: {match.group(1)}")
                
                except Exception as e:
                    print(f"[DEBUG] Erreur formatage match: {e}")
                    continue
            
            # Pattern pour *texte* italique (pas **texte**)
            italic_pattern = r'(?<!\*)\*([^*\n]{1,50}?)\*(?!\*)'
            
            for match in re.finditer(italic_pattern, current_content):
                try:
                    full_start = match.start()
                    content_start = match.start(1)
                    content_end = match.end(1)
                    full_end = match.end()
                    
                    tk_full_start = self._char_to_tkinter_position(current_content, full_start)
                    tk_content_start = self._char_to_tkinter_position(current_content, content_start)
                    tk_content_end = self._char_to_tkinter_position(current_content, content_end)
                    tk_full_end = self._char_to_tkinter_position(current_content, full_end)
                    
                    if all([tk_full_start, tk_content_start, tk_content_end, tk_full_end]):
                        # Nettoyer la zone
                        text_widget.tag_remove('italic', tk_full_start, tk_full_end)
                        text_widget.tag_remove('hidden', tk_full_start, tk_full_end)
                        
                        # Configurer tag italique
                        text_widget.tag_configure("italic", font=('Segoe UI', 12, 'italic'), foreground=self.colors['text_primary'])
                        
                        # Appliquer : cacher * et mettre en italique
                        text_widget.tag_add('hidden', tk_full_start, tk_content_start)
                        text_widget.tag_add('italic', tk_content_start, tk_content_end)
                        text_widget.tag_add('hidden', tk_content_end, tk_full_end)
                        
                        print(f"[DEBUG] Formaté en italique: {match.group(1)}")
                
                except Exception as e:
                    continue
            
        except Exception as e:
            print(f"[DEBUG] Erreur formatage immédiat: {e}")


    def _smart_scroll_follow_animation(self):
        """Scroll optimisé qui évite le clignotement"""
        try:
            if self.use_ctk:
                if hasattr(self, 'chat_frame') and hasattr(self.chat_frame, '_parent_canvas'):
                    canvas = self.chat_frame._parent_canvas
                    
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
                if hasattr(parent, 'yview_moveto'):
                    parent.update_idletasks()
                    parent.yview_moveto(1.0)
                    parent.update()
                    
        except Exception as e:
            print(f"[DEBUG] Erreur scroll animation: {e}")

    def _force_scroll_to_bottom(self):
        """Force un scroll vers le bas quand un gros contenu est ajouté"""
        try:
            if self.use_ctk:
                if hasattr(self, 'chat_frame') and hasattr(self.chat_frame, '_parent_canvas'):
                    canvas = self.chat_frame._parent_canvas
                    canvas.update_idletasks()
                    # Scroll directement vers le bas avec une petite marge
                    canvas.yview_moveto(0.9)  # Pas tout à fait au bas pour laisser de l'espace
                    canvas.update()
            else:
                parent = self.chat_frame.master
                if hasattr(parent, 'yview_moveto'):
                    parent.update_idletasks()
                    parent.yview_moveto(0.9)
                    parent.update()
        except Exception as e:
            print(f"[DEBUG] Erreur force scroll: {e}")

    def _is_internet_search_message(self):
        """Détecte si le message en cours de frappe contient des sources de recherche internet"""
        if not hasattr(self, 'typing_text') or not self.typing_text:
            return False
        
        text = self.typing_text
        
        # 🔧 AMÉLIORATION : Indicateurs plus précis pour les sources de recherche internet
        search_indicators = [
            # Patterns spécifiques aux sources
            'Sources :',
            'Sources:',
            'Source :',
            'Source:',
            
            # Patterns de liens numérotés (typiques des sources)
            '1. [',
            '2. [',
            '3. [',
            '4. [',
            '5. [',
            
            # Patterns d'URLs avec contexte de source
            '] (http',
            '] (https',
            '](http',
            '](https',
            
            # Autres indicateurs de recherche web
            'Visitez',
            'consultez',
            'source officielle',
            'selon',
            'D\'après'
        ]
        
        # Vérifier la présence de patterns spécifiques
        strong_indicators = ['Sources :', 'Sources:', 'Source :', 'Source:']
        weak_indicators = ['http://', 'https://']
        
        # Vérification forte : présence d'indicateurs de sources
        has_strong_indicator = any(indicator in text for indicator in strong_indicators)
        
        # Vérification faible : présence de liens
        link_count = sum(text.count(indicator) for indicator in weak_indicators)
        
        # Vérification des liens numérotés (pattern typique des sources)
        numbered_links = sum(1 for i in range(1, 6) if f'{i}. [' in text)
        
        # 🔧 LOGIQUE DE DÉCISION AMÉLIORÉE
        # C'est une source de recherche si :
        # - Il y a un indicateur fort (Sources:) OU
        # - Il y a au moins 2 liens ET au moins 1 lien numéroté OU
        # - Il y a au moins 3 liens (probable liste de sources)
        is_search_result = (
            has_strong_indicator or
            (link_count >= 2 and numbered_links >= 1) or
            link_count >= 3
        )
        
        return is_search_result

    def _is_in_incomplete_code_block(self, text):
        """Détecte si le texte contient un bloc de code incomplet (tous langages)"""
        import re
        
        # Langages supportés
        supported_languages = ['python', 'javascript', 'js', 'html', 'xml', 'css', 'bash', 'shell', 'sh', 'sql', 'mysql', 'postgresql', 'sqlite', 'dockerfile', 'docker', 'json']
        
        for lang in supported_languages:
            # Compter les balises d'ouverture et de fermeture pour ce langage
            opening_pattern = rf'```{lang}\b'
            opening_tags = len(re.findall(opening_pattern, text, re.IGNORECASE))
            
            if opening_tags > 0:
                # Compter les fermetures après chaque ouverture
                closing_tags = len(re.findall(r'```(?!\w)', text))  # ``` non suivi d'une lettre
                
                # Si on a plus d'ouvertures que de fermetures, on est dans un bloc incomplet
                if opening_tags > closing_tags:
                    # Vérifier si le dernier bloc ouvert est complet
                    last_opening = text.rfind(f'```{lang}')
                    if last_opening == -1:
                        # Essayer avec case insensitive
                        for match in re.finditer(opening_pattern, text, re.IGNORECASE):
                            last_opening = match.start()
                    
                    if last_opening != -1:
                        # Vérifier s'il y a une balise de fermeture après
                        text_after_opening = text[last_opening + len(f'```{lang}'):]
                        has_closing = '```' in text_after_opening
                        
                        # Si pas de fermeture OU si le texte finit par une fermeture partielle
                        if not has_closing or text_after_opening.rstrip().endswith('``'):
                            return True
        
        return False

    def _insert_text_with_safe_formatting(self, text_widget, text):
        """Formatage sécurisé qui ne traite que les blocs de code complets (tous langages)"""
        import re
        
        # 🔧 STRATÉGIE : Séparer le texte en deux parties
        # 1. La partie avec blocs complets qu'on peut formatter
        # 2. La partie avec bloc incomplet qu'on affiche en texte brut
        
        # Pattern pour tous les langages supportés
        supported_languages = ['python', 'javascript', 'js', 'html', 'xml', 'css', 'bash', 'shell', 'sh', 'sql', 'mysql', 'postgresql', 'sqlite', 'dockerfile', 'docker', 'json']
        languages_pattern = '|'.join(supported_languages)
        
        # Trouver tous les blocs de code complets (tous langages)
        complete_blocks_pattern = rf'```({languages_pattern})\n?(.*?)```'
        matches = list(re.finditer(complete_blocks_pattern, text, re.DOTALL | re.IGNORECASE))
        
        if not matches:
            # Pas de blocs complets, vérifier s'il y a un bloc en cours
            incomplete_pattern = rf'```({languages_pattern})\b'
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
                        self._insert_markdown_segments(text_widget, text_before_incomplete)
                    
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
                text_before = text[last_end:match.start()]
                self._insert_markdown_segments(text_widget, text_before)
            
            # Afficher le bloc complet avec formatage
            block_text = match.group(0)  # Le bloc complet avec ```language```
            self._insert_markdown_segments(text_widget, block_text)
            
            last_end = match.end()
        
        # Traiter le reste du texte après le dernier bloc complet
        if last_end < len(text):
            remaining_text = text[last_end:]
            
            # Vérifier si le reste contient un bloc incomplet
            incomplete_pattern = rf'```({languages_pattern})\b'
            incomplete_match = re.search(incomplete_pattern, remaining_text, re.IGNORECASE)
            
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

    def _insert_text_simple_during_animation(self, text_widget, text):
        """Insertion ULTRA-SIMPLE pendant l'animation - AUCUN formatage"""
        # 🔧 SOLUTION RADICALE : Zéro formatage pendant l'animation
        # Tout le formatage se fait à la fin seulement
        
        # Configuration du tag normal seulement
        text_widget.tag_configure("normal", font=('Segoe UI', 12), foreground=self.colors['text_primary'])
        
        # Insertion brute sans aucun formatage
        text_widget.insert("end", text, "normal")

    def _normal_scroll_follow_animation(self):
        """Scroll normal pour les messages non-recherche internet"""
        try:
            if self.use_ctk:
                if hasattr(self, 'chat_frame') and hasattr(self.chat_frame, '_parent_canvas'):
                    canvas = self.chat_frame._parent_canvas
                    canvas.update_idletasks()
                    
                    # Obtenir la position actuelle et la hauteur totale
                    yview = canvas.yview()
                    if yview:
                        current_top, current_bottom = yview
                        
                        # Scroll normal - plus agressif pour le suivi standard
                        if current_bottom < 0.95:  # Pas complètement en bas
                            # Scroll progressif normal
                            scroll_amount = 0.02  # Increment standard
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
        """Ajuste la hauteur du widget Text pour qu'il n'y ait aucun scroll interne ni espace vide, basé sur le nombre de lignes réelles tkinter. Désactive aussi le scroll interne."""
        try:
            text_widget.update_idletasks()
            current_state = text_widget.cget("state")
            text_widget.configure(state="normal")
            line_count = int(text_widget.index("end-1c").split(".")[0])
            text_widget.configure(height=max(2, line_count))
            text_widget.update_idletasks()
            text_widget.configure(state=current_state)
            self._disable_text_scroll(text_widget)
        except Exception as e:
            text_widget.configure(height=10)
            self._disable_text_scroll(text_widget)

    def _adjust_height_smoothly_during_animation(self, text_widget, current_text):
        """Ajustement de hauteur SMOOTH pendant l'animation pour éviter le scroll dans la bulle"""
        try:
            # Calculer le nombre de lignes nécessaires
            lines_needed = current_text.count('\n') + 1
            
            # Hauteur minimum et maximum
            min_height = 2
            max_height = 15  # Limiter pour éviter des bulles trop grandes
            
            # Calculer la hauteur idéale
            ideal_height = min(max(min_height, lines_needed), max_height)
            current_height = int(text_widget.cget('height'))
            
            # Ajuster SEULEMENT si nécessaire (éviter les changements constants)
            if abs(ideal_height - current_height) > 1:
                text_widget.configure(height=ideal_height)
                
                # IMPORTANT: Réinitialiser la vue SANS scroll
                text_widget.yview_moveto(0.0)  # Toujours commencer du haut
                
        except Exception as e:
            print(f"[DEBUG] Erreur ajustement hauteur smooth: {e}")

    def _adjust_height_during_animation(self, text_widget, current_text):
        """Ajuste la hauteur du widget Text pendant l'animation pour qu'il n'y ait aucun scroll interne, basé sur le nombre de lignes réelles tkinter."""
        try:
            text_widget.update_idletasks()
            line_count = int(text_widget.index("end-1c").split(".")[0])
            text_widget.configure(height=max(2, line_count))
            text_widget.update_idletasks()
            self._disable_text_scroll(text_widget)
        except Exception as e:
            text_widget.configure(height=10)
            self._disable_text_scroll(text_widget)

    def _insert_formatted_text_animated(self, text_widget, text):
        """Version améliorée du formatage pour l'animation avec support des blocs Python"""
        import re
        
        # Configuration complète des tags pour l'animation
        self._configure_formatting_tags(text_widget)
        
        # Utiliser le nouveau système de formatage amélioré même pour l'animation
        self._insert_markdown_segments(text_widget, text)

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
        """Version CORRIGÉE avec formatage unifié final"""
        if hasattr(self, 'typing_widget') and hasattr(self, 'typing_text'):
            
            if interrupted:
                # Pour l'interruption, appliquer quand même le formatage final
                current_content = self.typing_widget.get("1.0", "end-1c")
                
                # NOUVEAU : Réinitialiser les positions pour forcer un formatage complet
                if hasattr(self, '_formatted_positions'):
                    self._formatted_positions.clear()
                
                # Formatage final même en cas d'interruption
                self.typing_widget.configure(state="normal")
                self._apply_unified_progressive_formatting(self.typing_widget)
                
                # NOUVEAU : Convertir les liens temporaires en liens clickables
                self._convert_temp_links_to_clickable(self.typing_widget)
                
                # SOLUTION FINALE : Appliquer la coloration syntaxique directement
                self._apply_final_syntax_highlighting(self.typing_widget)
                
                self.typing_widget.configure(state="disabled")
            else:
                # Animation complète : formatage FINAL COMPLET
                
                # NOUVEAU : Réinitialiser les positions pour forcer un formatage complet
                if hasattr(self, '_formatted_positions'):
                    self._formatted_positions.clear()
                
                # Formatage final unifié
                self.typing_widget.configure(state="normal")
                self._apply_unified_progressive_formatting(self.typing_widget)
                
                # NOUVEAU : Convertir les liens temporaires en liens clickables
                self._convert_temp_links_to_clickable(self.typing_widget)
                
                # SOLUTION FINALE : Appliquer la coloration syntaxique directement
                self._apply_final_syntax_highlighting(self.typing_widget)
                
                self.typing_widget.configure(state="disabled")
            
            # Ajustement final de la hauteur
            self._adjust_height_final_no_scroll(self.typing_widget, self.typing_text)
            
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
            
            # Nettoyer le cache de formatage
            if hasattr(self, '_formatted_positions'):
                delattr(self, '_formatted_positions')
            
            print(f"[DEBUG] Animation terminée et formatage progressif définitivement préservé")

    def _convert_temp_links_to_clickable(self, text_widget):
        """Convertit les liens temporaires en liens bleus clicables à la fin de l'animation"""
        try:
            if not hasattr(self, '_pending_links'):
                return
            
            text_widget.configure(state='normal')
            
            # Parcourir tous les liens en attente (organisés par titre maintenant)
            link_counter = 0
            for title, link_data in self._pending_links.items():
                url = link_data['url']
                
                # Chercher toutes les zones avec le tag link_temp qui correspondent à ce titre
                ranges = text_widget.tag_ranges('link_temp')
                
                for i in range(0, len(ranges), 2):
                    start_range = ranges[i]
                    end_range = ranges[i + 1]
                    range_text = text_widget.get(start_range, end_range)
                    
                    if range_text == title:
                        # Créer un tag unique pour ce lien
                        unique_tag = f'clickable_link_{link_counter}'
                        link_counter += 1
                        
                        # Remplacer le tag link_temp par le tag unique
                        text_widget.tag_remove('link_temp', start_range, end_range)
                        text_widget.tag_add(unique_tag, start_range, end_range)
                        
                        # Configurer le style du tag unique
                        text_widget.tag_configure(unique_tag, foreground="#3b82f6", underline=1, font=('Segoe UI', 12))
                        
                        # CORRECTION CLOSURE : Créer une fonction avec l'URL capturée
                        def create_click_handler(url_to_open):
                            def click_handler(event):
                                print(f"[DEBUG] Clic sur lien: {url_to_open}")
                                import webbrowser
                                webbrowser.open(url_to_open)
                                return "break"
                            return click_handler
                        
                        # Lier l'événement avec l'URL correcte
                        text_widget.tag_bind(unique_tag, '<Button-1>', create_click_handler(url))
                        print(f"[DEBUG] Lien configuré: '{title}' -> {url} (tag: {unique_tag})")
            
            # Nettoyer les liens en attente
            delattr(self, '_pending_links')
            
            text_widget.configure(state='disabled')
            
        except Exception as e:
            print(f"[DEBUG] Erreur conversion liens: {e}")

    def _apply_final_cleanup_formatting(self, text_widget):
        """Applique les derniers formatages manqués sans effacer le contenu"""
        try:
            current_content = text_widget.get("1.0", "end-1c")
            
            # Vérifier s'il reste des ** non formatés
            import re
            remaining_bold = re.findall(r'\*\*([^*\n]{1,50}?)\*\*', current_content)
            
            if remaining_bold:
                print(f"[DEBUG] Formatage final de {len(remaining_bold)} éléments manqués")
                # Utiliser la même méthode que pendant l'animation
                self._apply_smart_formatting_once(text_widget)
            else:
                print(f"[DEBUG] Aucun formatage manqué, tout est déjà correct")
                
        except Exception as e:
            print(f"[DEBUG] Erreur formatage final: {e}")

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

    def _preserve_link_tags(self, text_widget):
        """Force la préservation des tags de liens même en mode disabled"""
        try:
            # Reconfigurer les tags de liens pour être plus persistants
            text_widget.tag_configure("link", 
                                    foreground="#3b82f6", 
                                    underline=True,
                                    font=('Segoe UI', 12),
                                    selectforeground="#3b82f6",
                                    selectbackground="#e1f5fe")
            
            # Forcer la mise à jour des tags existants
            link_ranges = text_widget.tag_ranges("link")
            if link_ranges:
                print(f"[DEBUG] {len(link_ranges)//2} liens préservés avec style forcé")
            
        except Exception as e:
            print(f"[DEBUG] Erreur préservation liens: {e}")

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
        """Version CORRIGÉE avec regex fixé pour les liens Markdown - AMÉLIORATION scroll"""
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
                # 🔧 CORRECTION CLÉE : Raccourcir intelligemment SEULEMENT pour sources de recherche
                if self._is_internet_search_message() and len(url) > 60:
                    # Garder le début et la fin pour rester informatif
                    link_text = url[:30] + "..." + url[-20:]
                else:
                    # Pour les autres messages, laisser le lien tel quel ou raccourcir légèrement
                    link_text = url if len(url) <= 80 else url[:77] + "..."
                print(f"[DEBUG] Lien direct: url='{url}', display='{link_text}'")
            
            # Vérification de l'URL
            if not url or not url.strip() or url == 'None':
                print(f"[DEBUG] URL invalide: {repr(url)}, insertion comme texte normal")
                text_widget.insert("end", link_text if 'link_text' in locals() else match.group(0))
                last_end = match.end()
                continue
            
            # 🔧 NOUVELLE AMÉLIORATION : Insérer le lien sans forcer le wrap
            start_index = text_widget.index("end-1c")
            text_widget.insert("end", link_text, ("link",))
            end_index = text_widget.index("end-1c")
            
            # Créer un tag unique pour ce lien
            tag_name = f"link_{link_count}"
            text_widget.tag_add(tag_name, start_index, end_index)
            
            # 🔧 OPTIMISATION : Configuration du tag pour éviter le wrap agressif
            text_widget.tag_configure(tag_name, 
                                    foreground="#3b82f6", 
                                    underline=True,
                                    font=('Segoe UI', 12),
                                    wrap="none")  # Empêcher le wrap automatique
            
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

    def _insert_complete_markdown_with_code(self, text_widget, text):
        """Formatage complet : liens + blocs de code (tous langages) + markdown + docstrings orange"""
        import re
        import webbrowser
        prev_state = text_widget.cget("state")
        text_widget.configure(state="normal")
        self._configure_all_formatting_tags(text_widget)
        # D'abord, découper le texte sur les docstrings ('''...''' ou """...""")
        docstring_pattern = r"('''[\s\S]*?'''|\"\"\"[\s\S]*?\"\"\")"
        last_end = 0
        for m in re.finditer(docstring_pattern, text):
            # Texte avant la docstring
            if m.start() > last_end:
                self._insert_complete_markdown_with_code_no_docstring(text_widget, text[last_end:m.start()])
            # Docstring
            docstring = m.group(0)
            import re as _re
            docstring_clean = _re.sub(r"^([\"']{3})docstring", r"\1", docstring, flags=_re.IGNORECASE)
            text_widget.insert("end", docstring_clean, "docstring")
            last_end = m.end()
        # Reste du texte
        if last_end < len(text):
            self._insert_complete_markdown_with_code_no_docstring(text_widget, text[last_end:])
        text_widget.configure(state=prev_state)

    def _insert_complete_markdown_with_code_no_docstring(self, text_widget, text):
        """Ancienne logique de _insert_complete_markdown_with_code, sans gestion docstring (pour découpage) - TOUS LANGAGES."""
        import re
        import webbrowser
        
        # Pattern pour tous les langages supportés
        supported_languages = ['python', 'javascript', 'js', 'html', 'xml', 'css', 'bash', 'shell', 'sh', 'sql', 'mysql', 'postgresql', 'sqlite', 'dockerfile', 'docker', 'json']
        languages_pattern = '|'.join(supported_languages)
        code_pattern = rf'```({languages_pattern})\n?(.*?)```'
        
        code_matches = list(re.finditer(code_pattern, text, flags=re.DOTALL | re.IGNORECASE))
        if not code_matches:
            self._process_text_with_links_only(text_widget, text)
            return
        last_end = 0
        link_count = 0
        for code_match in code_matches:
            if code_match.start() > last_end:
                text_before = text[last_end:code_match.start()]
                link_count += self._process_text_with_links_only(text_widget, text_before, link_count)
            
            language = code_match.group(1).lower()
            code_content = code_match.group(2)
            
            text_widget.insert("end", "\n")
            
            # Utiliser la fonction appropriée selon le langage
            if language == 'python':
                self._insert_python_code_block_corrected(text_widget, code_content)
            elif language in ['javascript', 'js']:
                # Utiliser la version sans newlines automatiques (le \n est géré par la fonction appelante)
                self._insert_javascript_code_block_without_newlines(text_widget, code_content)
            elif language in ['html', 'xml']:
                self._insert_html_code_block_without_newlines(text_widget, code_content)
            elif language == 'css':
                self._insert_css_code_block_without_newlines(text_widget, code_content)
            elif language in ['bash', 'shell', 'sh']:
                self._insert_bash_code_block_without_newlines(text_widget, code_content)
            elif language in ['sql', 'mysql', 'postgresql', 'sqlite']:
                self._insert_sql_code_block_without_newlines(text_widget, code_content)
            elif language in ['dockerfile', 'docker']:
                self._insert_dockerfile_code_block_without_newlines(text_widget, code_content)
            elif language == 'json':
                self._insert_json_code_block_without_newlines(text_widget, code_content)
            else:
                text_widget.insert("end", code_content, "code_block")
                
            text_widget.insert("end", "\n")
            last_end = code_match.end()
            
        if last_end < len(text):
            remaining_text = text[last_end:]
            self._process_text_with_links_only(text_widget, remaining_text, link_count)

    def _process_text_with_links_only(self, text_widget, text, start_link_count=0):
        """Traite le texte avec liens et markdown, sans blocs de code"""
        import re
        import webbrowser
        
        # Pattern pour liens Markdown : [texte](url)
        markdown_link_pattern = r'\[([^\]]+)\]\(([^)]+)\)'
        # Pattern pour liens HTTP directs
        http_link_pattern = r'(https?://[^\s\)]+)'
        # Combinaison des patterns
        combined_pattern = f'(?P<markdown>{markdown_link_pattern})|(?P<direct>{http_link_pattern})'
        
        last_end = 0
        link_count = start_link_count
        
        # Traiter chaque lien
        for match in re.finditer(combined_pattern, text):
            # Insérer le texte avant le lien avec formatage markdown
            if match.start() > last_end:
                text_before = text[last_end:match.start()]
                self._insert_simple_markdown(text_widget, text_before)
            
            # Traiter le lien
            if match.group('markdown'):  # Lien Markdown [texte](url)
                markdown_match = re.match(markdown_link_pattern, match.group('markdown'))
                if markdown_match:
                    link_text = markdown_match.group(1)
                    url = markdown_match.group(2)
                else:
                    last_end = match.end()
                    continue
            else:  # Lien HTTP direct
                url = match.group('direct')
                # Raccourcissement intelligent selon le type de message
                if len(url) > 60:
                    link_text = url[:30] + "..." + url[-20:]
                else:
                    link_text = url if len(url) <= 80 else url[:77] + "..."
            
            # Insérer le lien avec formatage
            if url and url.strip() and url != 'None':
                self._insert_link_with_callback(text_widget, link_text, url, link_count)
                link_count += 1
            
            last_end = match.end()
        
        # Insérer le reste du texte
        if last_end < len(text):
            remaining_text = text[last_end:]
            self._insert_simple_markdown(text_widget, remaining_text)
        
        return link_count - start_link_count
        
    def _insert_simple_markdown(self, text_widget, text):
        """Insère du texte avec formatage markdown simple (bold, italic, mono, titles)"""
        import re
        patterns = [
            (r'^(#{1,6})\s+(.+)$', 'title_markdown'),
            (r'`([^`]+)`', 'mono'),
            (r'\*\*([^*\n]+?)\*\*', 'bold'),
            (r'\*([^*\n]+?)\*', 'italic'),
        ]
        
        def parse_segments(text, patterns):
            if not patterns:
                return [(text, 'normal')]
            pattern, style = patterns[0]
            segments = []
            last = 0
            for m in re.finditer(pattern, text, flags=re.MULTILINE):
                if m.start() > last:
                    segments.extend(parse_segments(text[last:m.start()], patterns[1:]))
                if style == 'title_markdown':
                    level = len(m.group(1))
                    title_text = m.group(2)
                    segments.append((title_text, f'title{min(level, 5)}'))
                else:
                    segments.append((m.group(1), style))
                last = m.end()
            if last < len(text):
                segments.extend(parse_segments(text[last:], patterns[1:]))
            return segments
        
        segments = parse_segments(text, patterns)
        for segment, style in segments:
            if not segment:
                continue
            if style.startswith('title'):
                text_widget.insert("end", segment + "\n", style)
            else:
                text_widget.insert("end", segment, style)

    def _insert_link_with_callback(self, text_widget, link_text, url, link_count):
        """Insère un lien avec callback et formatage"""
        import webbrowser
        
        start_index = text_widget.index("end-1c")
        text_widget.insert("end", link_text, ("link",))
        end_index = text_widget.index("end-1c")
        
        # Créer un tag unique pour ce lien
        tag_name = f"link_{link_count}"
        text_widget.tag_add(tag_name, start_index, end_index)
        
        # Configuration du tag
        text_widget.tag_configure(tag_name, 
                                foreground="#3b82f6", 
                                underline=True,
                                font=('Segoe UI', 12))
        
        # Callback pour ouvrir le lien
        def create_callback(target_url):
            def on_click(event):
                try:
                    clean_url = str(target_url).strip()
                    if clean_url.startswith(('http://', 'https://')):
                        webbrowser.open(clean_url)
                    return "break"
                except Exception as e:
                    print(f"[DEBUG] Erreur ouverture lien: {e}")
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

    def _apply_smart_progressive_formatting(self, text_widget, current_text):
        """Applique le formatage progressif INTELLIGENT qui cache les balises"""
        import re
        
        try:
            # Obtenir le contenu RÉEL du widget pour éviter les décalages
            text_widget.configure(state='normal')
            actual_content = text_widget.get("1.0", "end-1c")
            
            # NOUVEAU : Appliquer un formatage progressif SIMPLE et EFFICACE
            self._apply_simple_progressive_formatting(text_widget, actual_content)
            
            text_widget.configure(state='disabled')
            
        except Exception as e:
            print(f"[DEBUG] Erreur formatage smart: {e}")
            text_widget.configure(state='disabled')
    
    def _apply_simple_progressive_formatting(self, text_widget, content):
        """MÉTHODE DÉSACTIVÉE - Remplacée par _apply_unified_progressive_formatting"""
        # Cette méthode a été remplacée par le système unifié pour éviter les conflits
        print("[INFO] Méthode de formatage legacy désactivée - utilisation du système unifié")
        return
    
    def _char_to_tkinter_position(self, text, char_index):
        """Convertit un index de caractère en position Tkinter (ligne.colonne)"""
        try:
            if char_index < 0 or char_index > len(text):
                return None
            
            lines_before = text[:char_index].split('\n')
            line_num = len(lines_before)
            char_num = len(lines_before[-1]) if lines_before else 0
            
            return f"{line_num}.{char_num}"
        except Exception:
            return None
    
    def _format_complete_elements_hide_markers_safe(self, text_widget, actual_content):
        """Version SÉCURISÉE qui travaille directement avec le contenu du widget"""
        import re
        
        # Patterns pour éléments COMPLETS uniquement
        patterns = [
            # Gras complet **texte** -> formater "texte" et cacher ** **
            (r'\*\*([^*\n]+?)\*\*', 'bold'),
            # Italique complet *texte* -> formater "texte" et cacher * *
            (r'(?<!\*)\*([^*\n]+?)\*(?!\*)', 'italic'),
            # Code inline complet `texte` -> formater "texte" et cacher ` `
            (r'`([^`\n]+?)`', 'mono'),
            # Titres complets ## Titre -> formater "Titre" et cacher ##
            (r'^(#{1,6})\s+(.+)$', 'title'),
        ]
        
        # Traiter chaque pattern de manière sécurisée
        for pattern, style_base in patterns:
            flags = re.MULTILINE if style_base == 'title' else 0
            
            # Chercher tous les matches dans le contenu actuel
            for match in re.finditer(pattern, actual_content, flags=flags):
                try:
                    # Calculer les positions de manière sécurisée
                    if style_base == 'title':
                        content_text = match.group(2)
                        level = min(len(match.group(1)), 5)
                        tag_name = f'title{level}'
                        
                        # Pour les titres: cacher # et formater le texte
                        hash_start = self._safe_char_to_tk(actual_content, match.start())
                        content_start = self._safe_char_to_tk(actual_content, match.start(2))
                        content_end = self._safe_char_to_tk(actual_content, match.end(2))
                        
                        # Vérifier que les positions sont valides ET pas déjà formatées
                        if hash_start and content_start and content_end:
                            # Vérifier si cette zone n'est pas déjà formatée
                            existing_tags = text_widget.tag_names(content_start)
                            if not any(tag.startswith('title') or tag == 'hidden' for tag in existing_tags):
                                # Masquer les # et l'espace
                                text_widget.tag_add('hidden', hash_start, content_start)
                                # Formater le titre
                                text_widget.tag_add(tag_name, content_start, content_end)
                    else:
                        content_text = match.group(1)
                        tag_name = style_base
                        
                        # Calculer positions ouverture, contenu, fermeture
                        opening_start = self._safe_char_to_tk(actual_content, match.start())
                        content_start = self._safe_char_to_tk(actual_content, match.start(1))
                        content_end = self._safe_char_to_tk(actual_content, match.end(1))
                        closing_end = self._safe_char_to_tk(actual_content, match.end())
                        
                        # Vérifier que toutes les positions sont valides ET pas déjà formatées
                        if all([opening_start, content_start, content_end, closing_end]):
                            # Vérifier si cette zone n'est pas déjà formatée
                            existing_tags = text_widget.tag_names(content_start)
                            if not any(tag in ['bold', 'italic', 'mono', 'hidden'] for tag in existing_tags):
                                # Masquer la balise d'ouverture
                                text_widget.tag_add('hidden', opening_start, content_start)
                                # Formater le contenu
                                text_widget.tag_add(tag_name, content_start, content_end)
                                # Masquer la balise de fermeture  
                                text_widget.tag_add('hidden', content_end, closing_end)
                    
                    print(f"[DEBUG] Formaté et caché balises: {content_text[:20]}...")
                    
                except Exception as e:
                    print(f"[DEBUG] Erreur formatage élément: {e}")
                    continue

    def _safe_char_to_tk(self, text, char_index):
        """Conversion SÉCURISÉE d'index caractère vers position Tkinter"""
        try:
            if char_index < 0 or char_index > len(text):
                return None
                
            lines_before = text[:char_index].split('\n')
            line_num = len(lines_before)
            char_num = len(lines_before[-1]) if lines_before else 0
            
            # Position Tkinter (1-indexé pour les lignes)
            return f"{line_num}.{char_num}"
        except Exception:
            return None
    
    def _is_already_formatted(self, text_widget, start_tk, end_tk):
        """Vérifie si une zone est déjà formatée"""
        try:
            # Vérifier s'il y a déjà des tags de formatage ou hidden dans cette zone
            tags_in_range = text_widget.tag_names(start_tk)
            return any(tag in ['bold', 'italic', 'mono', 'hidden'] or tag.startswith('title') 
                      for tag in tags_in_range)
        except:
            return False
    
    def _char_index_to_tk_position(self, text, char_index):
        """Convertit un index de caractère en position Tkinter (ligne.colonne)"""
        try:
            lines_before = text[:char_index].split('\n')
            line_num = len(lines_before)
            char_num = len(lines_before[-1]) if lines_before else 0
            return f"{line_num}.{char_num}"
        except:
            return None

    def _apply_markdown_formatting(self, text_widget, text):
        """Applique le formatage Markdown progressif sans effacer le contenu"""
        import re
        
        # Sauvegarder l'état actuel
        current_state = text_widget.cget('state')
        
        # Activer l'édition temporairement
        text_widget.configure(state='normal')
        
        try:
            # Appliquer les styles markdown par regex sur le texte existant
            self._apply_progressive_markdown_styles(text_widget, text)
            
        except Exception as e:
            print(f"[DEBUG] Erreur formatage markdown: {e}")
        finally:
            # Restaurer l'état
            text_widget.configure(state=current_state)
    
    def _apply_progressive_markdown_styles(self, text_widget, text):
        """Applique les styles markdown sans effacer le contenu"""
        import re
        
        # CORRECTION : Utiliser le contenu RÉEL du widget au lieu du paramètre text
        actual_content = text_widget.get("1.0", "end-1c")
        
        # Patterns markdown dans l'ordre de priorité
        patterns = [
            # Titres markdown
            (r'^(#{1,6})\s+(.+)$', 'title_markdown', lambda m: (m.group(2), f'title{min(len(m.group(1)), 5)}')),
            # Gras
            (r'\*\*([^*\n]+?)\*\*', 'bold', lambda m: (m.group(1), 'bold')),
            # Italique  
            (r'\*([^*\n]+?)\*', 'italic', lambda m: (m.group(1), 'italic')),
            # Code inline
            (r'`([^`]+)`', 'mono', lambda m: (m.group(1), 'mono')),
        ]
        
        # Appliquer chaque pattern
        for pattern, style_name, extract_func in patterns:
            flags = re.MULTILINE if style_name == 'title_markdown' else 0
            for match in re.finditer(pattern, actual_content, flags=flags):
                start_pos = self._find_text_position_widget_based(text_widget, match.start())
                end_pos = self._find_text_position_widget_based(text_widget, match.end())
                
                if start_pos and end_pos:
                    # Extraire le texte et le style
                    display_text, tag_style = extract_func(match)
                    
                    # Appliquer le tag au texte correspondant
                    text_widget.tag_add(tag_style, start_pos, end_pos)
    
    def _find_text_position_widget_based(self, text_widget, char_index):
        """Trouve la position dans le widget basée directement sur le contenu du widget"""
        try:
            # Obtenir le contenu actuel du widget
            widget_content = text_widget.get("1.0", "end-1c")
            
            # Vérifier que l'index est valide
            if char_index < 0 or char_index > len(widget_content):
                return None
            
            # Convertir l'index de caractère en position Tkinter
            lines = widget_content[:char_index].split('\n')
            line_num = len(lines)
            char_num = len(lines[-1]) if lines else 0
            return f"{line_num}.{char_num}"
        except:
            return None

    def _find_text_position(self, text_widget, full_text, char_index):
        """Trouve la position dans le widget correspondant à l'index dans le texte"""
        try:
            # Convertir l'index de caractère en position Tkinter
            lines = full_text[:char_index].split('\n')
            line_num = len(lines)
            char_num = len(lines[-1]) if lines else 0
            return f"{line_num}.{char_num}"
        except:
            return None

    def _insert_markdown_segments(self, text_widget, text, code_blocks=None):
        """Insère du texte avec formatage markdown amélioré - Support optimal des blocs ```python```"""
        import re
        
        # Debug pour voir si le formatage est appliqué
        if "```python" in text:
            print(f"[DEBUG] Bloc Python détecté dans le texte")
        
        # Pattern amélioré pour détecter les blocs de code avec langage
        code_block_pattern = r'```(\w+)?\n?(.*?)```'
        
        current_pos = 0
        
        # Traiter chaque bloc de code trouvé
        for match in re.finditer(code_block_pattern, text, re.DOTALL):
            # Insérer le texte avant le bloc de code
            if match.start() > current_pos:
                pre_text = text[current_pos:match.start()]
                self._insert_simple_markdown(text_widget, pre_text)
            
            # Extraire les informations du bloc de code
            language = match.group(1) or "text"
            code_content = match.group(2).strip()
            
            print(f"[DEBUG] Bloc de code détecté - Langage: {language}, Contenu: {len(code_content)} caractères")
            
            # Traitement spécialisé selon le langage
            if language.lower() == 'python':
                text_widget.insert("end", "\n")
                self._insert_python_code_block_with_syntax_highlighting(text_widget, code_content)
                text_widget.insert("end", "\n")
            elif language.lower() in ['javascript', 'js']:
                self._insert_javascript_code_block(text_widget, code_content)
            elif language.lower() in ['html', 'xml']:
                self._insert_html_code_block(text_widget, code_content)
            elif language.lower() == 'css':
                self._insert_css_code_block(text_widget, code_content)
            elif language.lower() in ['bash', 'shell', 'sh']:
                self._insert_bash_code_block(text_widget, code_content)
            elif language.lower() in ['sql', 'mysql', 'postgresql', 'sqlite']:
                self._insert_sql_code_block(text_widget, code_content)
            elif language.lower() in ['dockerfile', 'docker']:
                self._insert_dockerfile_code_block(text_widget, code_content)
            elif language.lower() in ['json']:
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
            from pygments import lex
            from pygments.lexers import PythonLexer
            from pygments.token import Token
            
            code = code.strip()
            if not code:
                return
            
            lexer = PythonLexer()
            
            print(f"[DEBUG] Traitement Pygments du code Python: {len(code)} caractères")
            
            # Appliquer la coloration avec Pygments
            for token_type, value in lex(code, lexer):
                if not value.strip() and value != '\n':
                    text_widget.insert("end", value, "mono")
                else:
                    tag_name = str(token_type)
                    text_widget.insert("end", value, tag_name)
            
            print(f"[DEBUG] Coloration Pygments appliquée avec succès")
            
        except ImportError:
            print("[DEBUG] Pygments non disponible, utilisation du fallback")
            self._insert_python_code_fallback_enhanced(text_widget, code)
        except Exception as e:
            print(f"[DEBUG] Erreur Pygments: {e}, utilisation du fallback")
            self._insert_python_code_fallback_enhanced(text_widget, code)

    def _insert_python_code_fallback_enhanced(self, text_widget, code):
        """Fallback amélioré avec reconnaissance étendue des patterns Python"""
        import keyword
        import re
        
        code = code.strip()
        if not code:
            return
        
        # Builtins Python étendus
        python_builtins = {
            'print', 'len', 'str', 'int', 'float', 'list', 'dict', 'set', 'tuple', 
            'range', 'enumerate', 'zip', 'map', 'filter', 'sorted', 'reversed',
            'sum', 'min', 'max', 'abs', 'round', 'pow', 'divmod', 'isinstance',
            'issubclass', 'hasattr', 'getattr', 'setattr', 'delattr', 'vars',
            'dir', 'type', 'id', 'callable', 'iter', 'next', 'open', 'input'
        }
        
        lines = code.split('\n')
        
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
                elif token.startswith('#'):
                    text_widget.insert("end", token, "Token.Comment")
                elif token.startswith(('"', "'")):
                    text_widget.insert("end", token, "Token.Literal.String")
                elif token in keyword.kwlist:
                    text_widget.insert("end", token, "Token.Keyword")
                elif token in ['True', 'False', 'None']:
                    text_widget.insert("end", token, "Token.Keyword.Constant")
                elif token in python_builtins:
                    text_widget.insert("end", token, "Token.Name.Builtin")
                elif re.match(r'^\d+\.?\d*$', token):
                    text_widget.insert("end", token, "Token.Literal.Number")
                elif re.match(r'^[+\-*/%=<>!&|^~]|//|\*\*|==|!=|<=|>=|<<|>>|\+=|-=|\*=|/=|%=|&=|\|=|\^=|<<=|>>=', token):
                    text_widget.insert("end", token, "Token.Operator")
                elif re.match(r'^[\(\)\[\]{},;:.]$', token):
                    text_widget.insert("end", token, "Token.Punctuation")
                elif re.match(r'^[a-zA-Z_]\w*$', token):
                    # Détection des fonctions (suivies de '(')
                    remaining = line[token_start + len(token):].lstrip()
                    if remaining.startswith('('):
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
        """Traite le markdown simple (gras, italique, titres) sans les blocs de code"""
        import re
        
        # Patterns pour le markdown de base
        patterns = [
            (r'^(#{1,6})\s+(.+)$', 'title_markdown'),  # Titres
            (r'\*\*([^*\n]+?)\*\*', 'bold'),           # Gras
            (r'\*([^*\n]+?)\*', 'italic'),             # Italique  
            (r'`([^`]+)`', 'mono'),                    # Code inline
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
                    pre_text = text[last_pos:match.start()]
                    apply_formatting(pre_text, remaining_patterns)
                
                # Appliquer le style
                if style == 'title_markdown':
                    level = len(match.group(1))
                    title_text = match.group(2)
                    text_widget.insert("end", title_text + "\n", f'title{min(level, 5)}')
                else:
                    content = match.group(1)
                    text_widget.insert("end", content, style)
                
                last_pos = match.end()
            
            # Texte après le dernier match
            if last_pos < len(text):
                remaining_text = text[last_pos:]
                apply_formatting(remaining_text, remaining_patterns)
        
        apply_formatting(text, patterns)

    def _insert_javascript_code_block(self, text_widget, code):
        """Coloration syntaxique pour JavaScript avec couleurs VS Code"""
        import re
        
        text_widget.insert("end", "\n")
        code = code.strip()
        if not code:
            text_widget.insert("end", "\n")
            return
        
        # Mots-clés JavaScript
        js_keywords = {
            'var', 'let', 'const', 'function', 'return', 'if', 'else', 'for', 'while', 'do', 
            'switch', 'case', 'default', 'break', 'continue', 'try', 'catch', 'finally',
            'throw', 'new', 'this', 'super', 'class', 'extends', 'import', 'export',
            'from', 'async', 'await', 'yield', 'typeof', 'instanceof', 'in', 'of',
            'true', 'false', 'null', 'undefined'
        }
        
        lines = code.split('\n')
        for i, line in enumerate(lines):
            if i > 0:
                text_widget.insert("end", "\n", "code_block")
            
            # Tokenisation JavaScript
            # Pattern pour capturer différents éléments
            token_pattern = r'''
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
            '''
            
            pos = 0
            for match in re.finditer(token_pattern, line, re.VERBOSE | re.DOTALL):
                # Ajouter le texte avant le match si nécessaire
                if match.start() > pos:
                    text_widget.insert("end", line[pos:match.start()], "code_block")
                
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
                        remaining = line[match.end():].lstrip()
                        if remaining.startswith('('):
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
        import re
        
        text_widget.insert("end", "\n")
        code = code.strip()
        if not code:
            text_widget.insert("end", "\n")
            return
        
        # Pattern pour les balises HTML
        html_pattern = r'''
            (<!--.*?-->)|                    # Commentaires HTML
            (</?[a-zA-Z][\w-]*(?:\s+[^>]*)?>) | # Balises ouvrantes/fermantes
            ([^<]+)                          # Contenu texte
        '''
        
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
        import re
        
        # Pattern pour décomposer une balise
        tag_pattern = r'(</?)([\w-]+)(\s+[^>]*)?(>)'
        match = re.match(tag_pattern, tag_content)
        
        if match:
            text_widget.insert("end", match.group(1), "html_punctuation")  # < ou </
            text_widget.insert("end", match.group(2), "html_tag")          # nom de balise
            
            # Attributs s'il y en a
            if match.group(3):
                self._parse_html_attributes(text_widget, match.group(3))
            
            text_widget.insert("end", match.group(4), "html_punctuation")  # >
        else:
            text_widget.insert("end", tag_content, "html_tag")
    
    def _parse_html_attributes(self, text_widget, attr_content):
        """Parse les attributs HTML"""
        import re
        
        # Pattern pour les attributs
        attr_pattern = r'(\s*)([\w-]+)(=)("(?:[^"\\]|\\.)*"|\'(?:[^\'\\]|\\.)*\'|\S+)?'
        
        pos = 0
        for match in re.finditer(attr_pattern, attr_content):
            # Espaces avant l'attribut
            if match.start() > pos:
                text_widget.insert("end", attr_content[pos:match.start()], "html_text")
            
            text_widget.insert("end", match.group(1), "html_text")        # espaces
            text_widget.insert("end", match.group(2), "html_attribute")   # nom attribut
            text_widget.insert("end", match.group(3), "html_punctuation") # =
            
            if match.group(4):  # valeur
                text_widget.insert("end", match.group(4), "html_value")
            
            pos = match.end()
        
        # Reste du texte
        if pos < len(attr_content):
            text_widget.insert("end", attr_content[pos:], "html_text")

    def _insert_css_code_block(self, text_widget, code):
        """Coloration syntaxique pour CSS avec couleurs VS Code"""
        import re
        
        text_widget.insert("end", "\n")
        code = code.strip()
        if not code:
            text_widget.insert("end", "\n")
            return
        
        # Pattern CSS global
        css_pattern = r'''
            (/\*.*?\*/)|                     # Commentaires
            ([\w\-#\.:\[\](),\s>+~*]+)(\s*\{)|  # Sélecteurs + {
            ([\w-]+)(\s*:\s*)([^;}]+)(;?)|   # Propriété: valeur;
            (\})|                            # }
            ([^{}]+)                         # Autres contenus
        '''
        
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
        import re
        
        # Pattern pour les valeurs CSS
        value_pattern = r'''
            ("(?:[^"\\]|\\.)*")|            # Chaînes double quotes
            ('(?:[^'\\]|\\.)*')|            # Chaînes simple quotes
            (\b\d+(?:\.\d+)?(?:px|em|rem|%|vh|vw|pt|pc|in|cm|mm|ex|ch|vmin|vmax|deg|rad|turn|s|ms)?\b)| # Nombres avec unités
            (#[0-9a-fA-F]{3,8})|            # Couleurs hexadécimales
            (\b(?:rgb|rgba|hsl|hsla|var|calc|url)\([^)]*\))| # Fonctions CSS
            ([^;}\s]+)                      # Autres valeurs
        '''
        
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
        import re
        
        text_widget.insert("end", "\n")
        code = code.strip()
        if not code:
            text_widget.insert("end", "\n")
            return
        
        # Mots-clés Bash
        bash_keywords = {
            'if', 'then', 'else', 'elif', 'fi', 'for', 'while', 'until', 'do', 'done',
            'case', 'esac', 'in', 'function', 'return', 'exit', 'break', 'continue',
            'local', 'export', 'readonly', 'declare', 'set', 'unset', 'source',
            'alias', 'unalias', 'type', 'which', 'whereis', 'echo', 'printf',
            'test', 'true', 'false'
        }
        
        lines = code.split('\n')
        for i, line in enumerate(lines):
            if i > 0:
                text_widget.insert("end", "\n", "code_block")
            
            # Skip shebang
            if line.startswith('#!'):
                text_widget.insert("end", line, "bash_comment")
                continue
            
            # Tokenisation Bash
            token_pattern = r'''
                (\#.*$)|                     # Commentaires
                ("(?:[^"\\]|\\.)*")|         # Chaînes double quotes
                ('(?:[^'\\]|\\.)*')|         # Chaînes simple quotes
                (\$\{[^}]*\}|\$\w+|\$\d+)|   # Variables
                (\b\d+\.?\d*\b)|             # Nombres
                (\b[a-zA-Z_]\w*\b)|          # Identifiants
                ([<>=!&|;()\[\]{}]|<<|>>|\|\||&&|==|!=|<=|>=|\+=|-=|\*=|/=|%=)| # Opérateurs
                (\s+)                        # Espaces
            '''
            
            pos = 0
            for match in re.finditer(token_pattern, line, re.VERBOSE):
                # Ajouter le texte avant le match
                if match.start() > pos:
                    text_widget.insert("end", line[pos:match.start()], "code_block")
                
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
        import re
        
        text_widget.insert("end", "\n")
        code = code.strip()
        if not code:
            text_widget.insert("end", "\n")
            return
        
        # Mots-clés SQL
        sql_keywords = {
            'SELECT', 'FROM', 'WHERE', 'JOIN', 'INNER', 'LEFT', 'RIGHT', 'FULL', 'OUTER',
            'ON', 'AND', 'OR', 'NOT', 'IN', 'EXISTS', 'BETWEEN', 'LIKE', 'IS', 'NULL',
            'INSERT', 'INTO', 'VALUES', 'UPDATE', 'SET', 'DELETE', 'CREATE', 'TABLE',
            'ALTER', 'DROP', 'INDEX', 'VIEW', 'DATABASE', 'SCHEMA', 'PRIMARY', 'KEY',
            'FOREIGN', 'REFERENCES', 'UNIQUE', 'CHECK', 'DEFAULT', 'AUTO_INCREMENT',
            'ORDER', 'BY', 'GROUP', 'HAVING', 'DISTINCT', 'LIMIT', 'OFFSET', 'UNION',
            'CASE', 'WHEN', 'THEN', 'ELSE', 'END', 'AS', 'ASC', 'DESC'
        }
        
        # Fonctions SQL communes
        sql_functions = {
            'COUNT', 'SUM', 'AVG', 'MIN', 'MAX', 'ROUND', 'ABS', 'UPPER', 'LOWER',
            'LENGTH', 'SUBSTRING', 'CONCAT', 'NOW', 'DATE', 'YEAR', 'MONTH', 'DAY'
        }
        
        lines = code.split('\n')
        for i, line in enumerate(lines):
            if i > 0:
                text_widget.insert("end", "\n", "code_block")
            
            # Tokenisation SQL
            token_pattern = r'''
                (--.*$)|                     # Commentaires --
                (/\*.*?\*/)|                 # Commentaires /* */
                ('(?:[^'\\]|\\.)*')|         # Chaînes simple quotes
                (\b\d+\.?\d*\b)|             # Nombres
                (\b[a-zA-Z_]\w*\b)|          # Identifiants
                ([=<>!]+|<=|>=|<>|\|\|)|     # Opérateurs
                ([(),;.])|                   # Ponctuation
                (\s+)                        # Espaces
            '''
            
            pos = 0
            for match in re.finditer(token_pattern, line, re.VERBOSE | re.DOTALL):
                # Ajouter le texte avant le match
                if match.start() > pos:
                    text_widget.insert("end", line[pos:match.start()], "code_block")
                
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
        import re
        
        text_widget.insert("end", "\n")
        code = code.strip()
        if not code:
            text_widget.insert("end", "\n")
            return
        
        # Instructions Dockerfile
        dockerfile_instructions = {
            'FROM', 'RUN', 'COPY', 'ADD', 'CMD', 'ENTRYPOINT', 'WORKDIR', 'EXPOSE',
            'ENV', 'ARG', 'VOLUME', 'USER', 'LABEL', 'MAINTAINER', 'ONBUILD',
            'STOPSIGNAL', 'HEALTHCHECK', 'SHELL'
        }
        
        lines = code.split('\n')
        for i, line in enumerate(lines):
            if i > 0:
                text_widget.insert("end", "\n", "code_block")
            
            line_stripped = line.strip()
            
            # Commentaires
            if line_stripped.startswith('#'):
                text_widget.insert("end", line, "dockerfile_comment")
                continue
            
            # Instructions Dockerfile
            instruction_match = re.match(r'^(\s*)(\w+)(\s+)(.*)', line)
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
        import re
        
        # Variables ${VAR} ou $VAR
        var_pattern = r'(\$\{[^}]*\}|\$\w+)'
        # Chaînes entre guillemets
        string_pattern = r'("(?:[^"\\]|\\.)*"|\'(?:[^\'\\]|\\.)*\')'
        # Flags comme --from=
        flag_pattern = r'(--[\w-]+(?:=\S+)?)'
        
        pos = 0
        
        # Traiter les flags d'abord (pour certaines instructions)
        if instruction in ['COPY', 'ADD', 'RUN']:
            for match in re.finditer(flag_pattern, rest):
                if match.start() > pos:
                    self._parse_simple_dockerfile_content(text_widget, rest[pos:match.start()])
                text_widget.insert("end", match.group(1), "dockerfile_flag")
                pos = match.end()
        
        # Traiter le reste
        remaining = rest[pos:]
        self._parse_simple_dockerfile_content(text_widget, remaining)
    
    def _parse_simple_dockerfile_content(self, text_widget, content):
        """Parse le contenu simple d'une ligne Dockerfile"""
        import re
        
        # Pattern pour variables et chaînes
        pattern = r'(\$\{[^}]*\}|\$\w+)|("(?:[^"\\]|\\.)*"|\'(?:[^\'\\]|\\.)*\')'
        
        pos = 0
        for match in re.finditer(pattern, content):
            if match.start() > pos:
                text_widget.insert("end", content[pos:match.start()], "code_block")
            
            if match.group(1):  # Variable
                text_widget.insert("end", match.group(1), "dockerfile_variable")
            elif match.group(2):  # Chaîne
                text_widget.insert("end", match.group(2), "dockerfile_string")
            
            pos = match.end()
        
        if pos < len(content):
            # Vérifier si le reste ressemble à un chemin
            remaining = content[pos:]
            if re.match(r'^[/.\w-]+$', remaining.strip()):
                text_widget.insert("end", remaining, "dockerfile_path")
            else:
                text_widget.insert("end", remaining, "code_block")

    def _insert_json_code_block(self, text_widget, code):
        """Coloration syntaxique pour JSON avec couleurs VS Code"""
        import re
        import json
        
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
            json_pattern = r'''
                ("(?:[^"\\]|\\.)*")(\s*:\s*)|  # Clés JSON
                ("(?:[^"\\]|\\.)*")|           # Chaînes
                (\b(?:true|false|null)\b)|     # Mots-clés JSON
                (\b-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?\b)| # Nombres
                ([\[\]{},:])|                  # Structures JSON
                (\s+)                          # Espaces
            '''
            
            for match in re.finditer(json_pattern, code, re.VERBOSE):
                if match.group(1) and match.group(2):  # Clé + :
                    text_widget.insert("end", match.group(1), "js_property")  # Clé en couleur propriété
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
        import re
        
        code = code.strip()
        if not code:
            return
        
        # Mots-clés JavaScript
        js_keywords = {
            'var', 'let', 'const', 'function', 'return', 'if', 'else', 'for', 'while', 'do', 
            'switch', 'case', 'default', 'break', 'continue', 'try', 'catch', 'finally',
            'throw', 'new', 'this', 'super', 'class', 'extends', 'import', 'export',
            'from', 'async', 'await', 'yield', 'typeof', 'instanceof', 'in', 'of',
            'true', 'false', 'null', 'undefined'
        }
        
        lines = code.split('\n')
        for i, line in enumerate(lines):
            if i > 0:
                text_widget.insert("end", "\n", "code_block")
            
            # Tokenisation JavaScript
            token_pattern = r'''
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
            '''
            
            pos = 0
            for match in re.finditer(token_pattern, line, re.VERBOSE | re.DOTALL):
                # Ajouter le texte avant le match si nécessaire
                if match.start() > pos:
                    text_widget.insert("end", line[pos:match.start()], "code_block")
                
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
                        remaining = line[match.end():].lstrip()
                        if remaining.startswith('('):
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
        import re
        
        code = code.strip()
        if not code:
            return
        
        # Pattern pour les balises HTML
        html_pattern = r'''
            (<!--.*?-->)|                    # Commentaires HTML
            (</?[a-zA-Z][\w-]*(?:\s+[^>]*)?>) | # Balises ouvrantes/fermantes
            ([^<]+)                          # Contenu texte
        '''
        
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
        import re
        
        code = code.strip()
        if not code:
            return
        
        # Pattern CSS global (version simplifiée)
        lines = code.split('\n')
        for i, line in enumerate(lines):
            if i > 0:
                text_widget.insert("end", "\n", "code_block")
            
            line_stripped = line.strip()
            
            # Commentaires CSS
            if '/*' in line and '*/' in line:
                text_widget.insert("end", line, "css_comment")
            # Sélecteurs (lignes se terminant par {)
            elif line_stripped.endswith('{'):
                selector = line_stripped[:-1].strip()
                text_widget.insert("end", selector, "css_selector")
                text_widget.insert("end", " {", "css_punctuation")
            # Propriétés CSS (contenant :)
            elif ':' in line and not line_stripped.startswith('/*'):
                parts = line.split(':', 1)
                if len(parts) == 2:
                    prop = parts[0].strip()
                    value = parts[1].strip()
                    
                    text_widget.insert("end", " " * (len(line) - len(line.lstrip())), "code_block")  # Indentation
                    text_widget.insert("end", prop, "css_property")
                    text_widget.insert("end", ": ", "css_punctuation")
                    
                    # Enlever le ; final si présent
                    if value.endswith(';'):
                        value_content = value[:-1]
                        text_widget.insert("end", value_content, "css_value")
                        text_widget.insert("end", ";", "css_punctuation")
                    else:
                        text_widget.insert("end", value, "css_value")
                else:
                    text_widget.insert("end", line, "code_block")
            # Fermeture de bloc
            elif line_stripped == '}':
                text_widget.insert("end", line, "css_punctuation")
            else:
                text_widget.insert("end", line, "code_block")

    def _insert_bash_code_block_without_newlines(self, text_widget, code):
        """Version sans newlines automatiques pour Bash"""
        import re
        
        code = code.strip()
        if not code:
            return
        
        # Mots-clés Bash essentiels
        bash_keywords = {
            'if', 'then', 'else', 'elif', 'fi', 'for', 'while', 'do', 'done',
            'case', 'esac', 'function', 'return', 'exit', 'break', 'continue',
            'export', 'local', 'echo', 'printf'
        }
        
        lines = code.split('\n')
        for i, line in enumerate(lines):
            if i > 0:
                text_widget.insert("end", "\n", "code_block")
            
            # Shebang
            if line.startswith('#!'):
                text_widget.insert("end", line, "bash_comment")
                continue
            
            # Commentaires
            if line.strip().startswith('#'):
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
                    text_widget.insert("end", line[current_pos:word_start], "code_block")
                
                # Colorer le mot
                if word.startswith('$'):
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
        import re
        
        code = code.strip()
        if not code:
            return
        
        # Mots-clés SQL essentiels
        sql_keywords = {
            'SELECT', 'FROM', 'WHERE', 'JOIN', 'INNER', 'LEFT', 'RIGHT', 'ON', 
            'AND', 'OR', 'INSERT', 'INTO', 'VALUES', 'UPDATE', 'SET', 'DELETE',
            'CREATE', 'TABLE', 'ALTER', 'DROP', 'ORDER', 'BY', 'GROUP', 'HAVING'
        }
        
        lines = code.split('\n')
        for i, line in enumerate(lines):
            if i > 0:
                text_widget.insert("end", "\n", "code_block")
            
            # Commentaires
            if line.strip().startswith('--'):
                text_widget.insert("end", line, "sql_comment")
                continue
            
            # Tokenisation simple par mots
            words = re.findall(r'\S+|\s+', line)
            
            for word in words:
                if word.isspace():
                    text_widget.insert("end", word, "code_block")
                elif word.startswith("'") and word.endswith("'"):
                    text_widget.insert("end", word, "sql_string")
                elif word.replace('.', '').isdigit():
                    text_widget.insert("end", word, "sql_number")
                elif word.upper() in sql_keywords:
                    text_widget.insert("end", word, "sql_keyword")
                elif word in [',', ';', '(', ')', '=', '<', '>', '<=', '>=']:
                    text_widget.insert("end", word, "sql_punctuation")
                else:
                    text_widget.insert("end", word, "sql_identifier")

    def _insert_dockerfile_code_block_without_newlines(self, text_widget, code):
        """Version sans newlines automatiques pour Dockerfile"""
        import re
        
        code = code.strip()
        if not code:
            return
        
        # Instructions Dockerfile
        dockerfile_instructions = {
            'FROM', 'RUN', 'COPY', 'ADD', 'CMD', 'ENTRYPOINT', 'WORKDIR', 'EXPOSE',
            'ENV', 'ARG', 'VOLUME', 'USER', 'LABEL'
        }
        
        lines = code.split('\n')
        for i, line in enumerate(lines):
            if i > 0:
                text_widget.insert("end", "\n", "code_block")
            
            line_stripped = line.strip()
            
            # Commentaires
            if line_stripped.startswith('#'):
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
                rest = line[indent + len(words[0]):]
                if rest:
                    # Variables simples
                    if '$' in rest:
                        parts = re.split(r'(\$\w+|\$\{[^}]*\})', rest)
                        for part in parts:
                            if part.startswith('$'):
                                text_widget.insert("end", part, "dockerfile_variable")
                            else:
                                text_widget.insert("end", part, "dockerfile_string")
                    else:
                        text_widget.insert("end", rest, "dockerfile_string")
            else:
                text_widget.insert("end", line, "code_block")

    def _insert_json_code_block_without_newlines(self, text_widget, code):
        """Version sans newlines automatiques pour JSON"""
        import re
        
        code = code.strip()
        if not code:
            return
        
        # Tokenisation JSON simple
        json_pattern = r'''
            ("(?:[^"\\]|\\.)*")(\s*:\s*)|  # Clés JSON + :
            ("(?:[^"\\]|\\.)*")|           # Chaînes
            (\b(?:true|false|null)\b)|     # Mots-clés JSON
            (\b-?\d+(?:\.\d+)?\b)|         # Nombres
            ([\[\]{},:])|                  # Structures JSON
            (\s+)                          # Espaces
        '''
        
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

    def _insert_javascript_code_block_content(self, text_widget, code):
        """Version content pour JavaScript (sans newlines automatiques)"""
        import re
        
        code = code.strip()
        if not code:
            return
        
        # Mots-clés JavaScript
        js_keywords = {
            'var', 'let', 'const', 'function', 'return', 'if', 'else', 'for', 'while', 'do', 
            'switch', 'case', 'default', 'break', 'continue', 'try', 'catch', 'finally',
            'throw', 'new', 'this', 'super', 'class', 'extends', 'import', 'export',
            'from', 'async', 'await', 'yield', 'typeof', 'instanceof', 'in', 'of',
            'true', 'false', 'null', 'undefined'
        }
        
        lines = code.split('\n')
        for i, line in enumerate(lines):
            if i > 0:
                text_widget.insert("end", "\n", "code_block")
            
            # Tokenisation JavaScript (version simplifiée)
            token_pattern = r'''
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
            '''
            
            pos = 0
            for match in re.finditer(token_pattern, line, re.VERBOSE | re.DOTALL):
                if match.start() > pos:
                    text_widget.insert("end", line[pos:match.start()], "code_block")
                
                token = match.group(0)
                
                if match.group(1) or match.group(2):  # Commentaires
                    text_widget.insert("end", token, "js_comment")
                elif match.group(3) or match.group(4) or match.group(5):  # Chaînes
                    text_widget.insert("end", token, "js_string")
                elif match.group(6):  # Nombres
                    text_widget.insert("end", token, "js_number")
                elif match.group(7):  # Identifiants
                    if token in js_keywords:
                        text_widget.insert("end", token, "js_keyword")
                    else:
                        remaining = line[match.end():].lstrip()
                        if remaining.startswith('('):
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
            
            if pos < len(line):
                text_widget.insert("end", line[pos:], "code_block")

    def _insert_html_code_block_content(self, text_widget, code):
        """Version content pour HTML (sans newlines automatiques)"""
        import re
        
        code = code.strip()
        if not code:
            return
        
        # Pattern pour les balises HTML
        html_pattern = r'''
            (<!--.*?-->)|                    # Commentaires HTML
            (</?[a-zA-Z][\w-]*(?:\s+[^>]*)?>) | # Balises ouvrantes/fermantes
            ([^<]+)                          # Contenu texte
        '''
        
        for match in re.finditer(html_pattern, code, re.VERBOSE | re.DOTALL):
            content = match.group(0)
            
            if match.group(1):  # Commentaire
                text_widget.insert("end", content, "html_comment")
            elif match.group(2):  # Balise
                self._parse_html_tag(text_widget, content)
            else:  # Texte
                text_widget.insert("end", content, "html_text")

    def _insert_css_code_block_content(self, text_widget, code):
        """Version content pour CSS (sans newlines automatiques)"""
        import re
        
        code = code.strip()
        if not code:
            return
        
        # Pattern CSS global
        css_pattern = r'''
            (/\*.*?\*/)|                     # Commentaires
            ([\w\-#\.:\[\](),\s>+~*]+)(\s*\{)|  # Sélecteurs + {
            ([\w-]+)(\s*:\s*)([^;}]+)(;?)|   # Propriété: valeur;
            (\})|                            # }
            ([^{}]+)                         # Autres contenus
        '''
        
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

    def _insert_bash_code_block_content(self, text_widget, code):
        """Version content pour Bash (sans newlines automatiques)"""
        import re
        
        code = code.strip()
        if not code:
            return
        
        # Mots-clés Bash
        bash_keywords = {
            'if', 'then', 'else', 'elif', 'fi', 'for', 'while', 'until', 'do', 'done',
            'case', 'esac', 'in', 'function', 'return', 'exit', 'break', 'continue',
            'local', 'export', 'readonly', 'declare', 'set', 'unset', 'source',
            'alias', 'unalias', 'type', 'which', 'whereis', 'echo', 'printf',
            'test', 'true', 'false'
        }
        
        lines = code.split('\n')
        for i, line in enumerate(lines):
            if i > 0:
                text_widget.insert("end", "\n", "code_block")
            
            # Skip shebang
            if line.startswith('#!'):
                text_widget.insert("end", line, "bash_comment")
                continue
            
            # Tokenisation Bash
            token_pattern = r'''
                (\#.*$)|                     # Commentaires
                ("(?:[^"\\]|\\.)*")|         # Chaînes double quotes
                ('(?:[^'\\]|\\.)*')|         # Chaînes simple quotes
                (\$\{[^}]*\}|\$\w+|\$\d+)|   # Variables
                (\b\d+\.?\d*\b)|             # Nombres
                (\b[a-zA-Z_]\w*\b)|          # Identifiants
                ([<>=!&|;()\[\]{}]|<<|>>|\|\||&&|==|!=|<=|>=|\+=|-=|\*=|/=|%=)| # Opérateurs
                (\s+)                        # Espaces
            '''
            
            pos = 0
            for match in re.finditer(token_pattern, line, re.VERBOSE):
                if match.start() > pos:
                    text_widget.insert("end", line[pos:match.start()], "code_block")
                
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
            
            if pos < len(line):
                text_widget.insert("end", line[pos:], "code_block")

    def _insert_sql_code_block_content(self, text_widget, code):
        """Version content pour SQL (sans newlines automatiques)"""
        import re
        
        code = code.strip()
        if not code:
            return
        
        # Mots-clés SQL
        sql_keywords = {
            'SELECT', 'FROM', 'WHERE', 'JOIN', 'INNER', 'LEFT', 'RIGHT', 'FULL', 'OUTER',
            'ON', 'AND', 'OR', 'NOT', 'IN', 'EXISTS', 'BETWEEN', 'LIKE', 'IS', 'NULL',
            'INSERT', 'INTO', 'VALUES', 'UPDATE', 'SET', 'DELETE', 'CREATE', 'TABLE',
            'ALTER', 'DROP', 'INDEX', 'VIEW', 'DATABASE', 'SCHEMA', 'PRIMARY', 'KEY',
            'FOREIGN', 'REFERENCES', 'UNIQUE', 'CHECK', 'DEFAULT', 'AUTO_INCREMENT',
            'ORDER', 'BY', 'GROUP', 'HAVING', 'DISTINCT', 'LIMIT', 'OFFSET', 'UNION',
            'CASE', 'WHEN', 'THEN', 'ELSE', 'END', 'AS', 'ASC', 'DESC'
        }
        
        sql_functions = {
            'COUNT', 'SUM', 'AVG', 'MIN', 'MAX', 'ROUND', 'ABS', 'UPPER', 'LOWER',
            'LENGTH', 'SUBSTRING', 'CONCAT', 'NOW', 'DATE', 'YEAR', 'MONTH', 'DAY'
        }
        
        lines = code.split('\n')
        for i, line in enumerate(lines):
            if i > 0:
                text_widget.insert("end", "\n", "code_block")
            
            # Tokenisation SQL
            token_pattern = r'''
                (--.*$)|                     # Commentaires --
                (/\*.*?\*/)|                 # Commentaires /* */
                ('(?:[^'\\]|\\.)*')|         # Chaînes simple quotes
                (\b\d+\.?\d*\b)|             # Nombres
                (\b[a-zA-Z_]\w*\b)|          # Identifiants
                ([=<>!]+|<=|>=|<>|\|\|)|     # Opérateurs
                ([(),;.])|                   # Ponctuation
                (\s+)                        # Espaces
            '''
            
            pos = 0
            for match in re.finditer(token_pattern, line, re.VERBOSE | re.DOTALL):
                if match.start() > pos:
                    text_widget.insert("end", line[pos:match.start()], "code_block")
                
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
            
            if pos < len(line):
                text_widget.insert("end", line[pos:], "code_block")

    def _insert_dockerfile_code_block_content(self, text_widget, code):
        """Version content pour Dockerfile (sans newlines automatiques)"""
        import re
        
        code = code.strip()
        if not code:
            return
        
        # Instructions Dockerfile
        dockerfile_instructions = {
            'FROM', 'RUN', 'COPY', 'ADD', 'CMD', 'ENTRYPOINT', 'WORKDIR', 'EXPOSE',
            'ENV', 'ARG', 'VOLUME', 'USER', 'LABEL', 'MAINTAINER', 'ONBUILD',
            'STOPSIGNAL', 'HEALTHCHECK', 'SHELL'
        }
        
        lines = code.split('\n')
        for i, line in enumerate(lines):
            if i > 0:
                text_widget.insert("end", "\n", "code_block")
            
            line_stripped = line.strip()
            
            # Commentaires
            if line_stripped.startswith('#'):
                text_widget.insert("end", line, "dockerfile_comment")
                continue
            
            # Instructions Dockerfile
            instruction_match = re.match(r'^(\s*)(\w+)(\s+)(.*)', line)
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

    def _insert_json_code_block_content(self, text_widget, code):
        """Version content pour JSON (sans newlines automatiques)"""
        import re
        import json
        
        code = code.strip()
        if not code:
            return
        
        # Essayer de parser le JSON pour une coloration plus précise
        try:
            # Vérifier si c'est du JSON valide
            json.loads(code)
            
            # Pattern JSON
            json_pattern = r'''
                ("(?:[^"\\]|\\.)*")(\s*:\s*)|  # Clés JSON
                ("(?:[^"\\]|\\.)*")|           # Chaînes
                (\b(?:true|false|null)\b)|     # Mots-clés JSON
                (\b-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?\b)| # Nombres
                ([\[\]{},:])|                  # Structures JSON
                (\s+)                          # Espaces
            '''
            
            for match in re.finditer(json_pattern, code, re.VERBOSE):
                if match.group(1) and match.group(2):  # Clé + :
                    text_widget.insert("end", match.group(1), "js_property")  # Clé en couleur propriété
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

    def _parse_markdown_styles(self, text):
        """Parse markdown styles (bold, italic, titles, inline code) for non-python segments."""
        import re
        patterns = [
            (r'^(#{1,6})\s+(.+)$', 'title_markdown'),
            (r'`([^`]+)`', 'mono'),
            (r'\*\*([^*\n]+?)\*\*', 'bold'),
            (r'\*([^*\n]+?)\*', 'italic'),
        ]
        segments = []
        last = 0
        for pattern, style in patterns:
            for m in re.finditer(pattern, text, flags=re.MULTILINE):
                if m.start() > last:
                    segments.append((text[last:m.start()], 'normal'))
                if style == 'title_markdown':
                    level = len(m.group(1))
                    title_text = m.group(2)
                    segments.append((title_text, f'title{min(level, 5)}'))
                else:
                    segments.append((m.group(1), style))
                last = m.end()
            text = text[last:]
            last = 0
        if text:
            segments.append((text, 'normal'))
        return segments

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
        
        # 🔧 UTILISATION DU NOUVEAU SYSTÈME DE FORMATAGE AMÉLIORÉ
        self._insert_markdown_segments(text_widget, text_with_links_processed)

        text_widget.update_idletasks()

    def _configure_all_formatting_tags(self, text_widget):
        """Configure TOUS les tags de formatage - Version unifiée et optimisée"""
        BASE_FONT = ('Segoe UI', 12)
        
        # === TAGS DE FORMATAGE UNIFIÉ ===
        text_widget.tag_configure("normal", font=BASE_FONT, foreground=self.colors['text_primary'])
        text_widget.tag_configure("bold", font=('Segoe UI', 12, 'bold'), foreground=self.colors['text_primary'])
        text_widget.tag_configure("italic", font=('Segoe UI', 12, 'italic'), foreground=self.colors['text_primary'])
        text_widget.tag_configure("code", font=('Consolas', 11), foreground="#f8f8f2", background="#2b2b2b")
        
        # === TAGS DE TITRES ===
        text_widget.tag_configure("title_1", font=('Segoe UI', 15, 'bold'), foreground=self.colors['text_primary'])  # Réduit de 18 à 16
        text_widget.tag_configure("title_2", font=('Segoe UI', 13, 'bold'), foreground=self.colors['text_primary'])  # Réduit de 16 à 14
        text_widget.tag_configure("title_3", font=('Segoe UI', 13, 'bold'), foreground=self.colors['text_primary'])
        
        # === TAGS SPÉCIAUX ===
        text_widget.tag_configure("link", foreground="#3b82f6", underline=1, font=BASE_FONT)
        text_widget.tag_configure("link_temp", font=BASE_FONT, foreground=self.colors['text_primary'])  # Lien pendant animation
        text_widget.tag_configure("docstring", font=('Consolas', 11, 'italic'), foreground="#ff8c00")
        text_widget.tag_configure("hidden", elide=True)  # Pour masquer les balises
        
        # === TAGS PYTHON (compatibilité) ===
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
        
        # === TAGS POUR AUTRES LANGAGES VS CODE ===
        
        # JavaScript tags
        js_tags = {
            "js_keyword": ("#569cd6", 'bold'),      # var, let, const, function, if, else, etc.
            "js_string": ("#ce9178", 'normal'),     # Chaînes de caractères
            "js_comment": ("#6a9955", 'italic'),    # Commentaires
            "js_number": ("#b5cea8", 'normal'),     # Nombres
            "js_function": ("#dcdcaa", 'normal'),   # Noms de fonctions
            "js_operator": ("#d4d4d4", 'normal'),   # Opérateurs
            "js_punctuation": ("#d4d4d4", 'normal'),# Ponctuation
            "js_variable": ("#9cdcfe", 'normal'),   # Variables
            "js_property": ("#9cdcfe", 'normal'),   # Propriétés d'objets
        }
        
        # CSS tags
        css_tags = {
            "css_selector": ("#d7ba7d", 'normal'),   # Sélecteurs CSS
            "css_property": ("#9cdcfe", 'normal'),   # Propriétés CSS
            "css_value": ("#ce9178", 'normal'),      # Valeurs
            "css_comment": ("#6a9955", 'italic'),    # Commentaires
            "css_number": ("#b5cea8", 'normal'),     # Nombres/unités
            "css_string": ("#ce9178", 'normal'),     # Chaînes
            "css_punctuation": ("#d4d4d4", 'normal'),# Ponctuation
            "css_pseudo": ("#dcdcaa", 'normal'),     # Pseudo-classes/éléments
        }
        
        # HTML tags
        html_tags = {
            "html_tag": ("#569cd6", 'bold'),         # Balises HTML
            "html_attribute": ("#9cdcfe", 'normal'), # Attributs
            "html_value": ("#ce9178", 'normal'),     # Valeurs d'attributs
            "html_comment": ("#6a9955", 'italic'),   # Commentaires
            "html_text": ("#d4d4d4", 'normal'),      # Texte contenu
            "html_punctuation": ("#d4d4d4", 'normal'),# < > = " /
            "Token.Name.Tag": ("#569cd6", 'bold'),   # NOUVEAU: Balises HTML
            "Token.Name.Entity": ("#dcdcaa", 'normal'), # NOUVEAU: Entités HTML
        }
        
        # Bash/Shell tags
        bash_tags = {
            "bash_keyword": ("#569cd6", 'bold'),     # if, then, else, fi, for, while, etc.
            "bash_command": ("#dcdcaa", 'normal'),   # Commandes
            "bash_string": ("#ce9178", 'normal'),    # Chaînes
            "bash_comment": ("#6a9955", 'italic'),   # Commentaires
            "bash_variable": ("#9cdcfe", 'normal'),  # Variables $VAR
            "bash_operator": ("#d4d4d4", 'normal'),  # Opérateurs
            "bash_number": ("#b5cea8", 'normal'),    # Nombres
            "bash_punctuation": ("#d4d4d4", 'normal'),# Ponctuation
            "Token.Name.Variable": ("#9cdcfe", 'normal'), # NOUVEAU: Variables
        }
        
        # SQL tags
        sql_tags = {
            "sql_keyword": ("#569cd6", 'bold'),      # SELECT, FROM, WHERE, etc.
            "sql_function": ("#dcdcaa", 'normal'),   # COUNT, SUM, etc.
            "sql_string": ("#ce9178", 'normal'),     # Chaînes
            "sql_comment": ("#6a9955", 'italic'),    # Commentaires
            "sql_number": ("#b5cea8", 'normal'),     # Nombres
            "sql_operator": ("#d4d4d4", 'normal'),   # =, >, <, etc.
            "sql_punctuation": ("#d4d4d4", 'normal'),# Ponctuation
            "sql_identifier": ("#9cdcfe", 'normal'), # Noms de tables/colonnes
        }
        
        # HTML tags
        html_tags = {
            "html_tag": ("#569cd6", 'bold'),         # Balises HTML
            "html_attribute": ("#9cdcfe", 'normal'), # Attributs
            "html_value": ("#ce9178", 'normal'),     # Valeurs d'attributs
            "html_comment": ("#6a9955", 'italic'),   # Commentaires
            "html_text": ("#d4d4d4", 'normal'),      # Texte contenu
            "html_punctuation": ("#d4d4d4", 'normal'),# < > = " /
        }
        
        # Bash/Shell tags
        bash_tags = {
            "bash_keyword": ("#569cd6", 'bold'),     # if, then, else, fi, for, while, etc.
            "bash_command": ("#dcdcaa", 'normal'),   # Commandes
            "bash_string": ("#ce9178", 'normal'),    # Chaînes
            "bash_comment": ("#6a9955", 'italic'),   # Commentaires
            "bash_variable": ("#9cdcfe", 'normal'),  # Variables $VAR
            "bash_operator": ("#d4d4d4", 'normal'),  # Opérateurs
            "bash_number": ("#b5cea8", 'normal'),    # Nombres
            "bash_punctuation": ("#d4d4d4", 'normal'),# Ponctuation
        }
        
        # SQL tags
        sql_tags = {
            "sql_keyword": ("#569cd6", 'bold'),      # SELECT, FROM, WHERE, etc.
            "sql_function": ("#dcdcaa", 'normal'),   # COUNT, SUM, etc.
            "sql_string": ("#ce9178", 'normal'),     # Chaînes
            "sql_comment": ("#6a9955", 'italic'),    # Commentaires
            "sql_number": ("#b5cea8", 'normal'),     # Nombres
            "sql_operator": ("#d4d4d4", 'normal'),   # =, >, <, etc.
            "sql_punctuation": ("#d4d4d4", 'normal'),# Ponctuation
            "sql_identifier": ("#9cdcfe", 'normal'), # Noms de tables/colonnes
        }
        
        # Dockerfile tags
        dockerfile_tags = {
            "dockerfile_instruction": ("#569cd6", 'bold'), # FROM, RUN, COPY, etc.
            "dockerfile_string": ("#ce9178", 'normal'),    # Chaînes
            "dockerfile_comment": ("#6a9955", 'italic'),   # Commentaires
            "dockerfile_variable": ("#9cdcfe", 'normal'),  # Variables ${}
            "dockerfile_path": ("#ce9178", 'normal'),      # Chemins de fichiers
            "dockerfile_flag": ("#dcdcaa", 'normal'),      # Flags --from, etc.
        }
        
        # Configuration de tous les tags
        all_language_tags = {**js_tags, **css_tags, **html_tags, **bash_tags, **sql_tags, **dockerfile_tags}
        
        for tag, (color, weight) in all_language_tags.items():
            if weight == 'bold':
                text_widget.tag_configure(tag, foreground=color, font=('Consolas', 11, 'bold'))
            elif weight == 'italic':
                text_widget.tag_configure(tag, foreground=color, font=('Consolas', 11, 'italic'))
            else:
                text_widget.tag_configure(tag, foreground=color, font=('Consolas', 11))
        
        text_widget.tag_configure("code_block", font=('Consolas', 11), background="#1e1e1e", foreground="#d4d4d4")

    def _apply_final_syntax_highlighting(self, text_widget):
        """Applique la coloration syntaxique finale à tous les blocs de code détectés"""
        try:
            text_widget.configure(state="normal")
            
            # Récupérer tout le contenu du widget
            content = text_widget.get("1.0", "end-1c")
            
            print(f"[DEBUG] Application de la coloration finale sur {len(content)} caractères")
            
            # Pattern pour détecter les blocs de code avec langage
            code_block_pattern = r'```(\w+)?\n?(.*?)```'
            
            # Parcourir tous les blocs de code trouvés
            for match in re.finditer(code_block_pattern, content, re.DOTALL):
                language = match.group(1) or "text"
                code_content = match.group(2).strip() if match.group(2) else ""
                
                if not code_content:
                    continue
                    
                print(f"[DEBUG] Bloc de code trouvé - Langage: {language}, Contenu: {len(code_content)} caractères")
                
                # Trouver la position du bloc dans le widget
                start_pos = f"1.0+{match.start()}c"
                end_pos = f"1.0+{match.end()}c"
                
                # Supprimer le bloc existant
                text_widget.delete(start_pos, end_pos)
                
                # Réinsérer avec la coloration syntaxique appropriée
                text_widget.mark_set("insert", start_pos)
                
                # Appliquer la coloration selon le langage
                if language.lower() == 'python':
                    self._insert_python_code_block_with_syntax_highlighting(text_widget, code_content)
                elif language.lower() in ['javascript', 'js']:
                    self._insert_javascript_code_block(text_widget, code_content)
                elif language.lower() in ['html', 'xml']:
                    self._insert_html_code_block(text_widget, code_content)
                elif language.lower() == 'css':
                    self._insert_css_code_block(text_widget, code_content)
                elif language.lower() in ['bash', 'shell', 'sh']:
                    self._insert_bash_code_block(text_widget, code_content)
                elif language.lower() in ['sql', 'mysql', 'postgresql', 'sqlite']:
                    self._insert_sql_code_block(text_widget, code_content)
                elif language.lower() in ['dockerfile', 'docker']:
                    self._insert_dockerfile_code_block(text_widget, code_content)
                elif language.lower() in ['json']:
                    self._insert_json_code_block(text_widget, code_content)
                else:
                    # Bloc de code générique
                    text_widget.insert("insert", "\n")
                    text_widget.insert("insert", code_content, "code_block")
                    text_widget.insert("insert", "\n")
                
                # Mettre à jour le contenu pour les prochaines itérations
                content = text_widget.get("1.0", "end-1c")
            
            print(f"[DEBUG] Coloration syntaxique finale appliquée")
            
        except Exception as e:
            print(f"[ERROR] Erreur lors de l'application de la coloration finale: {e}")
            import traceback
            traceback.print_exc()

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
                
                # Forcer le rendu puis mesurer SANS déplacer la vue
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
        """Définit le texte de placeholder correctement (non éditable)"""
        self.placeholder_text = "Tapez votre message ici... (Entrée pour envoyer, Shift+Entrée pour nouvelle ligne)"
        self.placeholder_active = True
        
        if self.use_ctk:
            # CustomTkinter avec placeholder natif si disponible
            try:
                # Essayer d'utiliser le placeholder natif de CustomTkinter
                if hasattr(self.input_text, 'configure') and 'placeholder_text' in self.input_text.configure():
                    self.input_text.configure(placeholder_text=self.placeholder_text)
                    self.placeholder_active = False
                    return
            except:
                pass
            
            # Fallback pour CustomTkinter
            self._show_placeholder()
            
            def on_focus_in(event):
                self._hide_placeholder()
            
            def on_focus_out(event):
                if not self.input_text.get("1.0", "end-1c").strip():
                    self._show_placeholder()
            
            def on_key_press(event):
                if self.placeholder_active:
                    self._hide_placeholder()
            
            self.input_text.bind("<FocusIn>", on_focus_in)
            self.input_text.bind("<FocusOut>", on_focus_out)
            self.input_text.bind("<KeyPress>", on_key_press)
        else:
            # Pour tkinter standard
            self._show_placeholder()
            
            def on_focus_in(event):
                self._hide_placeholder()
            
            def on_focus_out(event):
                if not self.input_text.get("1.0", "end-1c").strip():
                    self._show_placeholder()
            
            def on_key_press(event):
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
                self.input_text.configure(text_color=self.colors['placeholder'])
            else:
                self.input_text.configure(fg=self.colors['placeholder'])
            
            # Rendre le texte non sélectionnable et transparent visuellement
            self.input_text.configure(state='disabled')
            self.input_text.configure(state='normal')
            self.placeholder_active = True
    
    def _hide_placeholder(self):
        """Cache le placeholder et permet la saisie normale"""
        if self.placeholder_active:
            self.input_text.delete("1.0", "end")
            
            if self.use_ctk:
                self.input_text.configure(text_color=self.colors['text_primary'])
            else:
                self.input_text.configure(fg=self.colors['text_primary'])
            
            self.placeholder_active = False
    
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
        """Envoie le message - VERSION CORRIGÉE avec gestion placeholder"""
        try:
            # Permettre l'envoi même si animation interrompue
            if self.is_animation_running():
                if getattr(self, '_typing_interrupted', False):
                    self.finish_typing_animation_dynamic(interrupted=True)
                else:
                    return
            
            # Vérifier si le placeholder est actif
            if getattr(self, 'placeholder_active', False):
                return  # Ne pas envoyer si seul le placeholder est présent
            
            # Récupérer le texte AVANT de vérifier l'état
            message = ""
            try:
                message = self.input_text.get("1.0", "end-1c").strip()
            except Exception as e:
                print(f"❌ Erreur lecture input: {e}")
                return
            
            # Vérifier que ce n'est pas le texte du placeholder
            if message == getattr(self, 'placeholder_text', '') or not message:
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

        # 🚀 NOUVEAU: Utiliser CustomAI unifié si disponible
        print(f"[DEBUG] (ModernAIGUI) Question transmise - Mode {'CustomAI' if self.custom_ai else 'Standard'} : {repr(user_text)}")
        try:
            if self.custom_ai:
                # 🚀 Utiliser CustomAI unifié (avec support 1M tokens intégré)
                print("🚀 Traitement avec CustomAI unifié...")
                response = self.custom_ai.generate_response(user_text)
                
                # Afficher les stats après traitement (optionnel)
                try:
                    stats = self.custom_ai.get_context_stats()
                    if stats.get('context_size', 0) > 100000:  # Plus de 100K tokens
                        print(f"📊 Contexte après traitement: {stats.get('context_size', 0):,} tokens")
                except:
                    pass
            else:
                # Mode standard avec AIEngine classique
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
        # Détection des capacités CustomAI
        ultra_status = ""
        if hasattr(self, 'custom_ai') and self.custom_ai:
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
        """Traite le fichier en arrière-plan avec système 1M tokens"""
        try:
            self.logger.info(f"Traitement du fichier: {filename} (type: {file_type})")
            
            # Utiliser le processeur unifié
            result = self.file_processor.process_file(file_path)
            
            if result.get('error'):
                raise ValueError(result['error'])
            
            content = result.get('content', '')
            self.logger.info(f"Fichier traité: {len(content)} caractères")
            
            # Vérifier que le contenu n'est pas vide
            if not content or not content.strip():
                raise ValueError(f"Le fichier {filename} semble vide ou illisible")
            
            # 🚀 NOUVEAU: Stocker dans CustomAI unifié avec processeurs avancés
            chunks_created = 0
            if self.custom_ai:
                try:
                    self.logger.info(f"🚀 Ajout au CustomAI avec processeurs avancés: {filename}")
                    
                    # Utiliser la nouvelle méthode qui exploite les processeurs PDF/DOCX/Code
                    if hasattr(self.custom_ai, 'add_file_to_context'):
                        # Méthode avancée qui utilise les processeurs spécialisés
                        result = self.custom_ai.add_file_to_context(file_path)
                        chunk_ids = result.get('chunk_ids', [])
                        chunks_created = result.get('chunks_created', len(chunk_ids) if chunk_ids else 0)
                        
                        if result.get('success'):
                            processor_used = result.get('processor_used', 'advanced')
                            analysis_info = result.get('analysis_info', f'{len(content)} caractères')
                            self.logger.info(f"📄 Processeur {processor_used} utilisé: {analysis_info}")
                            print(f"🔧 Traitement avancé: {processor_used} - {analysis_info}")
                        else:
                            self.logger.warning(f"Échec traitement avancé: {result.get('message', 'Erreur inconnue')}")
                    else:
                        # Méthode de fallback - utiliser add_document_to_context
                        result = self.custom_ai.add_document_to_context(content, filename)
                        chunks_created = result.get('chunks_created', 0)
                    
                    # Statistiques après ajout
                    stats = self.custom_ai.get_context_stats()
                    self.logger.info(f"📊 Nouveau contexte: {stats.get('context_size', 0):,} tokens ({stats.get('utilization_percent', 0):.1f}%)")
                    
                    print(f"🚀 Document ajouté au CustomAI: {chunks_created} chunks créés")
                    
                except Exception as e:
                    self.logger.warning(f"Erreur ajout CustomAI: {e}")
                    chunks_created = 0
            
            # Stocker aussi dans la mémoire classique pour compatibilité
            if hasattr(self.ai_engine, 'local_ai') and hasattr(self.ai_engine.local_ai, 'conversation_memory'):
                self.ai_engine.local_ai.conversation_memory.store_document_content(filename, content)
                self.logger.info(f"Contenu stocké dans la mémoire classique pour {filename}")
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