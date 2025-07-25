"""
Graphical User Interface for My AI Personal Assistant.
A modern, user-friendly GUI built with tkinter and customtkinter.
"""
import tkinter as tk
from tkinter import ttk, scrolledtext, filedialog, messagebox
import threading
import sys
import os
from typing import Optional, Any
from datetime import datetime

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import customtkinter as ctk
    CTK_AVAILABLE = True
except ImportError:
    CTK_AVAILABLE = False

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


class AIAssistantGUI:
    """Main GUI application for the AI Assistant."""
    
    def __init__(self):
        """Initialize the GUI application."""
        self.logger = Logger.get_logger("ai_assistant_gui")
        self.config = Config()
        self.ai_engine = AIEngine(self.config)
        self.file_manager = FileManager()
        
        # Processors
        self.pdf_processor = PDFProcessor()
        self.docx_processor = DOCXProcessor()
        self.code_processor = CodeProcessor()
        
        # GUI setup
        self.setup_gui()
        self.setup_styles()
        self.create_widgets()
        self.show_welcome_message()
        
        # Initialize AI in background
        self.initialize_ai_async()
    
    def setup_gui(self):
        """Setup the main GUI window."""
        if CTK_AVAILABLE:
            # Use CustomTkinter for modern look
            ctk.set_appearance_mode("dark")
            ctk.set_default_color_theme("blue")
            self.root = ctk.CTk()
        else:
            # Fallback to standard tkinter
            self.root = tk.Tk()

        self.root.title("🤖 My AI Personal Assistant")
        self.root.geometry("1200x800")
        self.root.minsize(800, 600)

        # Maximiser la fenêtre au lancement (Windows/Linux)
        # Cela garde la barre de titre et les boutons classiques
        self.root.after(100, lambda: self.root.state("zoomed"))

        # Si vous souhaitez un mode fenêtré par défaut, commentez la ligne ci-dessus

        self.root.update_idletasks()
        
        # Configure grid
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_rowconfigure(0, weight=1)
    
    def setup_styles(self):
        """Setup GUI styles."""
        if not CTK_AVAILABLE:
            # Configure ttk styles for standard tkinter
            self.style = ttk.Style()
            self.style.theme_use('clam')
    
    def create_widgets(self):
        """Create and layout GUI widgets."""
        # Main container
        if CTK_AVAILABLE:
            main_frame = ctk.CTkFrame(self.root)
        else:
            main_frame = ttk.Frame(self.root, padding="10")
        
        main_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        main_frame.grid_columnconfigure(1, weight=1)
        main_frame.grid_rowconfigure(1, weight=1)
        
        # Title
        if CTK_AVAILABLE:
            title_label = ctk.CTkLabel(
                main_frame, 
                text="🤖 My AI Personal Assistant",
                font=ctk.CTkFont(size=24, weight="bold")
            )
        else:
            title_label = ttk.Label(
                main_frame, 
                text="🤖 My AI Personal Assistant",
                font=("Arial", 18, "bold")
            )
        
        title_label.grid(row=0, column=0, columnspan=2, pady=(0, 20), sticky="ew")
        
        # Left panel - Controls
        self.create_control_panel(main_frame)
        
        # Right panel - Chat
        self.create_chat_panel(main_frame)
        
        # Status bar
        self.create_status_bar(main_frame)
    
    def create_control_panel(self, parent):
        """Create the control panel with buttons and options."""
        if CTK_AVAILABLE:
            control_frame = ctk.CTkFrame(parent)
        else:
            control_frame = ttk.LabelFrame(parent, text="Controls", padding="10")
        
        control_frame.grid(row=1, column=0, sticky="nsew", padx=(0, 10))
        control_frame.grid_columnconfigure(0, weight=1)
        
        # AI Status
        if CTK_AVAILABLE:
            ai_status_label = ctk.CTkLabel(control_frame, text="AI Status:")
        else:
            ai_status_label = ttk.Label(control_frame, text="AI Status:")
        
        ai_status_label.grid(row=0, column=0, sticky="w", pady=(0, 5))
        
        self.ai_status_var = tk.StringVar(value="Initializing...")
        if CTK_AVAILABLE:
            self.ai_status_display = ctk.CTkLabel(
                control_frame, 
                textvariable=self.ai_status_var,
                text_color="orange"
            )
        else:
            self.ai_status_display = ttk.Label(
                control_frame, 
                textvariable=self.ai_status_var
            )
        
        self.ai_status_display.grid(row=1, column=0, sticky="w", pady=(0, 15))
        
        # File processing section
        if CTK_AVAILABLE:
            file_label = ctk.CTkLabel(control_frame, text="File Processing:")
        else:
            file_label = ttk.Label(control_frame, text="File Processing:")
        
        file_label.grid(row=2, column=0, sticky="w", pady=(0, 5))
        
        if CTK_AVAILABLE:
            self.process_pdf_btn = ctk.CTkButton(
                control_frame, 
                text="📄 Process PDF",
                command=self.process_pdf_file
            )
        else:
            self.process_pdf_btn = ttk.Button(
                control_frame, 
                text="📄 Process PDF",
                command=self.process_pdf_file
            )
        
        self.process_pdf_btn.grid(row=3, column=0, sticky="ew", pady=2)
        
        if CTK_AVAILABLE:
            self.process_docx_btn = ctk.CTkButton(
                control_frame, 
                text="📝 Process DOCX",
                command=self.process_docx_file
            )
        else:
            self.process_docx_btn = ttk.Button(
                control_frame, 
                text="📝 Process DOCX",
                command=self.process_docx_file
            )
        
        self.process_docx_btn.grid(row=4, column=0, sticky="ew", pady=2)
        
        if CTK_AVAILABLE:
            self.process_code_btn = ctk.CTkButton(
                control_frame, 
                text="💻 Process Code",
                command=self.process_code_file
            )
        else:
            self.process_code_btn = ttk.Button(
                control_frame, 
                text="💻 Process Code",
                command=self.process_code_file
            )
        
        self.process_code_btn.grid(row=5, column=0, sticky="ew", pady=2)
        
        # Separator
        if CTK_AVAILABLE:
            separator = ctk.CTkFrame(control_frame, height=2)
        else:
            separator = ttk.Separator(control_frame)
        
        separator.grid(row=6, column=0, sticky="ew", pady=15)
        
        # Generation section
        if CTK_AVAILABLE:
            gen_label = ctk.CTkLabel(control_frame, text="Quick Actions:")
        else:
            gen_label = ttk.Label(control_frame, text="Quick Actions:")
        
        gen_label.grid(row=7, column=0, sticky="w", pady=(0, 5))
        
        if CTK_AVAILABLE:
            self.help_btn = ctk.CTkButton(
                control_frame, 
                text="❓ Help",
                command=self.show_help
            )
        else:
            self.help_btn = ttk.Button(
                control_frame, 
                text="❓ Help",
                command=self.show_help
            )
        
        self.help_btn.grid(row=8, column=0, sticky="ew", pady=2)
        
        # Clear conversation
        if CTK_AVAILABLE:
            self.clear_btn = ctk.CTkButton(
                control_frame, 
                text="🗑️ Clear Chat",
                command=self.clear_conversation,
                fg_color="red",
                hover_color="darkred"
            )
        else:
            self.clear_btn = ttk.Button(
                control_frame, 
                text="🗑️ Clear Chat",
                command=self.clear_conversation
            )
        
        self.clear_btn.grid(row=9, column=0, sticky="ew", pady=(15, 0))

        # Add memory status display after the buttons
        self.add_memory_status_display(control_frame)
    
    def create_chat_panel(self, parent):
        """Create the chat panel for conversation."""
        if CTK_AVAILABLE:
            chat_frame = ctk.CTkFrame(parent)
        else:
            chat_frame = ttk.LabelFrame(parent, text="Conversation", padding="10")
        
        chat_frame.grid(row=1, column=1, sticky="nsew")
        chat_frame.grid_columnconfigure(0, weight=1)
        chat_frame.grid_rowconfigure(0, weight=1)
        
        # Chat history
        if CTK_AVAILABLE:
            self.chat_display = ctk.CTkTextbox(
                chat_frame, 
                state="disabled",
                wrap="word",  # Empêche la coupure des mots
                font=ctk.CTkFont(family="Segoe UI", size=13)  # Taille optimale pour la lisibilité
            )
        else:
            self.chat_display = scrolledtext.ScrolledText(
                chat_frame, 
                wrap=tk.WORD,  # Empêche la coupure des mots
                height=20,
                state=tk.DISABLED,
                font=("Segoe UI", 13),  # Taille optimale pour la lisibilité
                padx=10,
                pady=10
            )
        
        self.chat_display.grid(row=0, column=0, columnspan=2, sticky="nsew", pady=(0, 10))
        
        # Input area
        if CTK_AVAILABLE:
            self.input_entry = ctk.CTkEntry(
                chat_frame, 
                placeholder_text="Type your message here..."
            )
        else:
            self.input_entry = ttk.Entry(chat_frame)
        
        self.input_entry.grid(row=1, column=0, sticky="ew", padx=(0, 10))
        self.input_entry.bind("<Return>", self.send_message)
        
        if CTK_AVAILABLE:
            self.send_btn = ctk.CTkButton(
                chat_frame, 
                text="Send",
                command=self.send_message,
                width=80
            )
        else:
            self.send_btn = ttk.Button(
                chat_frame, 
                text="Send",
                command=self.send_message,
                width=10
            )
        
        self.send_btn.grid(row=1, column=1)
    
    def create_status_bar(self, parent):
        """Create the status bar."""
        if CTK_AVAILABLE:
            status_frame = ctk.CTkFrame(parent)
        else:
            status_frame = ttk.Frame(parent)
        
        status_frame.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(10, 0))
        status_frame.grid_columnconfigure(0, weight=1)
        
        self.status_var = tk.StringVar(value="Ready")
        if CTK_AVAILABLE:
            self.status_label = ctk.CTkLabel(status_frame, textvariable=self.status_var)
        else:
            self.status_label = ttk.Label(status_frame, textvariable=self.status_var)
        
        self.status_label.grid(row=0, column=0, sticky="w")
    
    def initialize_ai_async(self):
        """Initialize AI engine in background thread."""
        def init_ai():
            try:
                self.update_status("Initializing AI engine...")
                success = self.ai_engine.initialize_llm()
                
                if success:
                    self.ai_status_var.set("✅ Connected")
                    self.update_status("AI engine initialized successfully")
                    if CTK_AVAILABLE:
                        self.ai_status_display.configure(text_color="green")
                    
                    # Afficher le message d'accueil
                    try:
                        welcome_msg = self.ai_engine.model.get_welcome_message()
                        self.root.after(0, lambda: self.add_to_chat("AI", welcome_msg))
                    except Exception as e:
                        self.logger.error(f"Error getting welcome message: {e}")
                        self.root.after(0, lambda: self.add_to_chat("AI", "Bonjour ! Je suis votre assistant IA personnel. Comment puis-je vous aider ?"))
                else:
                    self.ai_status_var.set("❌ Disconnected")
                    self.update_status("Failed to initialize AI engine")
                    if CTK_AVAILABLE:
                        self.ai_status_display.configure(text_color="red")
                
            except Exception as e:
                self.logger.error(f"Error initializing AI: {e}")
                self.ai_status_var.set("❌ Error")
                self.update_status(f"AI initialization error: {e}")
                if CTK_AVAILABLE:
                    self.ai_status_display.configure(text_color="red")
        
        thread = threading.Thread(target=init_ai, daemon=True)
        thread.start()
    
    def update_status(self, message: str):
        """Update the status bar message."""
        self.status_var.set(message)
        self.logger.info(message)
    
    def add_to_chat(self, sender: str, message: str):
        """Add a message to the chat display with auto-scroll and improved formatting."""
        # Formater le message pour une meilleure lisibilité
        formatted_message = self._format_chat_message(message)
        
        if CTK_AVAILABLE:
            self.chat_display.configure(state="normal")
            if sender == "AI":
                self.chat_display.insert("end", f"🤖 AI: {formatted_message}\n\n")
            elif sender == "You":
                self.chat_display.insert("end", f"👤 You: {formatted_message}\n\n")
            else:
                self.chat_display.insert("end", f"ℹ️ {sender}: {formatted_message}\n\n")
            self.chat_display.configure(state="disabled")
            # Auto-scroll to bottom for customtkinter with multiple attempts
            self.chat_display.see("end")
            self.root.after(10, lambda: self.chat_display.see("end"))
            self.root.after(50, lambda: self.chat_display.see("end"))
        else:
            self.chat_display.config(state=tk.NORMAL)
            if sender == "AI":
                self.chat_display.insert(tk.END, f"🤖 AI: {formatted_message}\n\n")
            elif sender == "You":
                self.chat_display.insert(tk.END, f"👤 You: {formatted_message}\n\n")
            else:
                self.chat_display.insert(tk.END, f"ℹ️ {sender}: {formatted_message}\n\n")
            self.chat_display.config(state=tk.DISABLED)
            # Auto-scroll to bottom for tkinter with multiple attempts
            self.chat_display.see(tk.END)
            self.chat_display.update_idletasks()
            self.chat_display.yview_moveto(1.0)
            self.root.after(10, lambda: self.chat_display.yview_moveto(1.0))
            self.root.after(50, lambda: self.chat_display.yview_moveto(1.0))
    
    def _format_chat_message(self, message: str) -> str:
        """
        Formate un message pour un meilleur affichage dans le chat.
        Formatage minimal pour ne pas interférer avec le word wrapping.
        """
        import re
        
        # Remplacer seulement les URLs très longues par une version tronquée
        url_pattern = r'https?://[^\s]+'
        urls = re.findall(url_pattern, message)
        for url in urls:
            if len(url) > 80:  # Seulement les URLs vraiment très longues
                short_url = url[:40] + "..." + url[-25:]
                message = message.replace(url, short_url)
        
        return message
    
    def send_message(self, event=None):
        """Send a message to the AI with auto-scroll."""
        message = self.input_entry.get().strip()
        if not message:
            return
        
        self.input_entry.delete(0, tk.END)
        self.add_to_chat("You", message)
        
        # Force scroll to bottom after user message
        self._ensure_scroll_to_bottom()
        
        # Process in background thread
        def process_message():
            try:
                self.update_status("Processing message...")
                response = self.ai_engine.process_text(message)
                self.root.after(0, lambda: self._handle_ai_response(response))
                self.root.after(0, lambda: self.update_status("Ready"))
            except Exception as e:
                self.logger.error(f"Error processing message: {e}")
                self.root.after(0, lambda: self.add_to_chat("AI", f"Error: {e}"))
                self.root.after(0, lambda: self.update_status("Error occurred"))
        
        thread = threading.Thread(target=process_message, daemon=True)
        thread.start()
    
    def _handle_ai_response(self, response):
        """Handle AI response with guaranteed auto-scroll."""
        # Extraire et formater le texte de réponse
        response_text = self._extract_response_text(response)
        
        self.add_to_chat("AI", response_text)
        # Force scroll to bottom after AI response with delay
        self.root.after(50, self._ensure_scroll_to_bottom)
    
    def _extract_response_text(self, response) -> str:
        """
        Extrait le texte de réponse depuis différents formats de réponse
        CORRECTION: Gestion améliorée des formats imbriqués
        """
        try:
            # Si c'est déjà une chaîne, la retourner directement
            if isinstance(response, str):
                return response
            
            # Si c'est un dictionnaire (réponse structurée)
            elif isinstance(response, dict):
                # Gestion des dictionnaires imbriqués
                
                # Cas spécial: dictionnaire avec une clé 'message' qui contient un autre dictionnaire
                if "message" in response:
                    message_content = response["message"]
                    
                    # Si le message est lui-même un dictionnaire stringifié
                    if isinstance(message_content, str) and message_content.startswith("{'message':"):
                        try:
                            import ast
                            parsed_dict = ast.literal_eval(message_content)
                            if isinstance(parsed_dict, dict) and "message" in parsed_dict:
                                return str(parsed_dict["message"])
                        except:
                            pass
                    
                    # Si le message contient encore un dictionnaire, l'extraire
                    if isinstance(message_content, dict) and "message" in message_content:
                        return str(message_content["message"])
                    return str(message_content)
                
                # Autres champs possibles
                elif "text" in response:
                    return str(response["text"])
                elif "content" in response:
                    return str(response["content"])
                elif "response" in response:
                    return str(response["response"])
                elif "ai_response" in response:
                    ai_resp = response["ai_response"]
                    if isinstance(ai_resp, dict):
                        return str(ai_resp.get("message", ai_resp.get("text", str(ai_resp))))
                    else:
                        return str(ai_resp)
                else:
                    # Si aucun champ reconnu, convertir le dict en string propre
                    # Mais d'abord vérifier s'il y a une seule clé avec le contenu
                    if len(response) == 1:
                        key, value = next(iter(response.items()))
                        if isinstance(value, str):
                            return value
                    # Sinon convertir le dict complet en string
                    return str(response)
            
            # Pour tout autre type, convertir en string
            else:
                return str(response)
                
        except Exception as e:
            self.logger.error(f"Error extracting response text: {e}")
            return f"Erreur lors de l'extraction de la réponse: {str(e)}"

    def _ensure_scroll_to_bottom(self):
        """Ensure the chat scrolls to the very bottom."""
        if CTK_AVAILABLE:
            self.chat_display.see("end")
            # Force scroll to bottom with multiple attempts
            self.root.after(10, lambda: self.chat_display.see("end"))
        else:
            self.chat_display.see(tk.END)
            self.chat_display.update_idletasks()
            # Force scroll to very bottom
            self.chat_display.yview_moveto(1.0)
            # Additional scroll attempt to ensure we're at the bottom
            self.root.after(10, lambda: self.chat_display.yview_moveto(1.0))
    
    def process_pdf_file(self):
        """Process a PDF file with improved memory management and error handling."""
        file_path = filedialog.askopenfilename(
            title="Select PDF file",
            filetypes=[("PDF files", "*.pdf")]
        )
        
        if file_path:
            def process():
                try:
                    self.update_status("Processing PDF...")
                    text = self.pdf_processor.extract_text(file_path)
                    
                    if text:
                        filename = os.path.basename(file_path)
                        self.add_to_chat("System", f"📄 PDF traité avec succès : {filename}")
                        
                        # Vérifier que ai_engine a session_context
                        if self.ai_engine and hasattr(self.ai_engine, 'session_context'):
                            # IMMEDIATELY store in AI memory 
                            if self.ai_engine.conversation_memory:
                                clean_filename = filename.replace('.pdf', '')
                                self.ai_engine.conversation_memory.store_document_content(clean_filename, text)
                                # Update session context
                                self.ai_engine.session_context["documents_processed"].append(clean_filename)
                                self.ai_engine.session_context["last_document_type"] = "PDF"
                                self.ai_engine.session_context["current_document"] = clean_filename
                                # Debug removed
                        
                        # Generate summary through AI
                        if self.ai_engine and len(text.strip()) > 10:
                            self.logger.info(f"Asking AI to summarize PDF: {filename}")
                            summary_prompt = f"Please summarize this PDF content from file '{filename}':\n\n{text[:2000]}"
                            response = self.ai_engine.process_text(summary_prompt)
                            self.root.after(0, lambda: self.add_to_chat("AI", response))
                        else:
                            self.root.after(0, lambda: self.add_to_chat("AI", "PDF traité, mais le contenu semble vide."))
                        
                        self.root.after(0, lambda: self.update_status("PDF processed successfully"))
                    else:
                        self.root.after(0, lambda: self.add_to_chat("System", "❌ Impossible d'extraire le texte du PDF"))
                        self.root.after(0, lambda: self.update_status("PDF processing failed"))
                        
                except Exception as e:
                    self.logger.error(f"Error processing PDF: {e}")
                    self.root.after(0, lambda: self.add_to_chat("System", f"❌ Erreur PDF: {e}"))
                    self.root.after(0, lambda: self.update_status("Error occurred"))
            
            thread = threading.Thread(target=process, daemon=True)
            thread.start()
    
    def process_docx_file(self):
        """Process a DOCX file with improved memory management and error handling."""
        file_path = filedialog.askopenfilename(
            title="Select DOCX file",
            filetypes=[("DOCX files", "*.docx")]
        )
        
        if file_path:
            def process():
                try:
                    self.update_status("Processing DOCX...")
                    result = self.docx_processor.extract_text(file_path)
                    
                    if isinstance(result, dict) and result.get("success"):
                        filename = os.path.basename(file_path)
                        content = result.get("content", "")
                        self.add_to_chat("System", f"📝 DOCX traité avec succès : {filename}")
                        
                        # Vérifier que ai_engine a session_context
                        if self.ai_engine and hasattr(self.ai_engine, 'session_context'):
                            # IMMEDIATELY store in AI memory
                            if self.ai_engine.conversation_memory and content:
                                clean_filename = filename.replace('.docx', '')
                                self.ai_engine.conversation_memory.store_document_content(clean_filename, content)
                                # Update session context
                                self.ai_engine.session_context["documents_processed"].append(clean_filename)
                                self.ai_engine.session_context["last_document_type"] = "DOCX"
                                self.ai_engine.session_context["current_document"] = clean_filename
                                # Debug removed
                        
                        # Generate analysis through AI
                        if self.ai_engine and content:
                            content_to_analyze = content[:2000] if len(content) > 2000 else content
                            analysis_prompt = f"Please analyze this document content from file '{filename}':\n\n{content_to_analyze}"
                            response = self.ai_engine.process_text(analysis_prompt)
                            self.root.after(0, lambda: self.add_to_chat("AI", response))
                        
                        self.root.after(0, lambda: self.update_status("DOCX processed successfully"))
                    else:
                        error_msg = result.get("error", "Erreur inconnue") if isinstance(result, dict) else "Échec de lecture"
                        self.root.after(0, lambda: self.add_to_chat("System", f"❌ {error_msg}"))
                        self.root.after(0, lambda: self.update_status("DOCX processing failed"))
                        
                except Exception as e:
                    self.logger.error(f"Error processing DOCX: {e}")
                    self.root.after(0, lambda: self.add_to_chat("System", f"❌ Erreur DOCX: {e}"))
                    self.root.after(0, lambda: self.update_status("Error occurred"))
            
            thread = threading.Thread(target=process, daemon=True)
            thread.start()
    
    def process_code_file(self):
        """Process a code file with improved memory management and error handling."""
        file_path = filedialog.askopenfilename(
            title="Select code file",
            filetypes=[
                ("Python files", "*.py"),
                ("JavaScript files", "*.js"),
                ("HTML files", "*.html"),
                ("CSS files", "*.css"),
                ("All files", "*.*")
            ]
        )
        
        if file_path:
            def process():
                try:
                    self.update_status("Processing code file...")
                    code = self.code_processor.read_code_file(file_path)
                    
                    if code:
                        filename = os.path.basename(file_path)
                        language = self.code_processor.detect_language(file_path)
                        
                        self.add_to_chat("System", f"💻 Code traité avec succès : {filename}")
                        self.add_to_chat("System", f"Langage: {language}, Lignes: {len(code.splitlines())}")
                        
                        # Validate syntax
                        is_valid = self.code_processor.validate_syntax(file_path)
                        status = "✅ Syntaxe valide" if is_valid.get("success") else "❌ Erreurs de syntaxe"
                        self.add_to_chat("System", f"Validation: {status}")
                        
                        # Vérifier que ai_engine a session_context
                        if self.ai_engine and hasattr(self.ai_engine, 'session_context'):
                            # IMMEDIATELY store in AI memory
                            if self.ai_engine.conversation_memory:
                                code_info = {
                                    "code": code,
                                    "language": language,
                                    "file_path": file_path,
                                    "filename": filename,
                                    "timestamp": datetime.now().isoformat(),
                                    "type": "code"  # Mark as code type
                                }
                                clean_filename = filename.replace('.py', '').replace('.js', '').replace('.html', '').replace('.css', '')
                                self.ai_engine.conversation_memory.store_code_content(clean_filename, code_info)
                                # Update session context
                                self.ai_engine.session_context["code_files_processed"].append(clean_filename)
                                self.ai_engine.session_context["current_document"] = clean_filename
                                # Debug removed
                        
                        # Generate initial analysis message
                        initial_message = (
                            f"📄 Code '{filename}' analysé avec succès !\n\n"
                            f"🔍 **Détails :**\n"
                            f"• Langage : {language}\n"
                            f"• Lignes : {len(code.splitlines())}\n"
                            f"• Validation : {status}\n\n"
                            f"💡 **Vous pouvez maintenant :**\n"
                            f"• Me demander d'expliquer le code\n"
                            f"• Poser des questions sur des fonctions spécifiques\n"
                            f"• Demander des suggestions d'amélioration\n"
                            f"• Demander des modifications\n\n"
                            f"Que souhaitez-vous savoir sur ce code ?"
                        )
                        
                        self.root.after(0, lambda: self.add_to_chat("AI", initial_message))
                        self.root.after(0, lambda: self.update_status("Code file processed successfully"))
                    else:
                        self.root.after(0, lambda: self.add_to_chat("System", "❌ Impossible de lire le fichier de code"))
                        self.root.after(0, lambda: self.update_status("Code processing failed"))
                        
                except Exception as e:
                    self.logger.error(f"Error processing code file: {e}")
                    self.root.after(0, lambda: self.add_to_chat("System", f"❌ Erreur code: {e}"))
                    self.root.after(0, lambda: self.update_status("Error occurred"))
            
            thread = threading.Thread(target=process, daemon=True)
            thread.start()
    
    def show_help(self):
        """Show help information."""
        try:
            response = self.ai_engine.process_text("aide")
            self.add_to_chat("AI Assistant", response)
            self.update_status("Help displayed")
        except Exception as e:
            self.logger.error(f"Error showing help: {e}")
            help_text = """🤖 My AI Personal Assistant - Aide

💬 **Interface Chat :**
Tapez vos demandes directement dans le chat, par exemple :
• "génère une fonction pour calculer la factorielle"
• "crée une classe Personne avec nom et âge"
• "explique-moi comment fonctionne un dictionnaire Python"

📁 **Traitement de fichiers :**
• Cliquez sur "Process PDF" pour analyser un document PDF
• Cliquez sur "Process DOCX" pour analyser un document Word
• Cliquez sur "Process Code" pour analyser un fichier de code

💡 **Conseils :**
• Soyez spécifique dans vos demandes
• Utilisez un langage naturel
• N'hésitez pas à poser des questions de suivi"""
            
            self.add_to_chat("System", help_text)
            self.update_status("Help displayed")
    
    def clear_conversation(self):
        """Clear conversation with improved memory management."""
        if messagebox.askyesno("Clear Chat", "Voulez-vous effacer la conversation ET la mémoire des documents ?"):
            try:
                # Clear chat display
                if CTK_AVAILABLE:
                    self.chat_display.configure(state="normal")
                    self.chat_display.delete("0.0", "end")
                    self.chat_display.configure(state="disabled")
                else:
                    self.chat_display.config(state=tk.NORMAL)
                    self.chat_display.delete("1.0", tk.END)
                    self.chat_display.config(state=tk.DISABLED)
                
                # Clear AI memory and session context
                if self.ai_engine:
                    self.ai_engine.clear_conversation()
                    # Also clear session context
                    self.ai_engine.session_context = {
                        "documents_processed": [],
                        "code_files_processed": [],
                        "last_document_type": None,
                        "current_document": None
                    }
                    # Debug removed
                
                self.show_welcome_message()
                self.update_status("Conversation et mémoire effacées")
            except Exception as e:
                self.logger.error(f"Error clearing conversation: {e}")
                self.update_status(f"Erreur lors de l'effacement: {e}")

    def add_memory_status_display(self, control_frame):
        """Add a status display for documents in memory with proper alignment"""
        # Memory status section
        if CTK_AVAILABLE:
            memory_label = ctk.CTkLabel(control_frame, text="Documents en mémoire:")
        else:
            memory_label = ttk.Label(control_frame, text="Documents en mémoire:")
        
        memory_label.grid(row=10, column=0, sticky="w", pady=(15, 5))
        
        self.memory_status_var = tk.StringVar(value="Aucun document")
        if CTK_AVAILABLE:
            self.memory_status_display = ctk.CTkLabel(
                control_frame, 
                textvariable=self.memory_status_var,
                text_color="gray",
                # Alignement à gauche et ajustement de la largeur
                justify="left",
                anchor="w"  # Ancrage à gauche (west)
            )
        else:
            self.memory_status_display = ttk.Label(
                control_frame, 
                textvariable=self.memory_status_var,
                # Alignement à gauche pour tkinter standard
                justify="left",
                anchor="w"
            )
        
        # sticky="ew" pour occuper toute la largeur mais aligné à gauche
        self.memory_status_display.grid(row=11, column=0, sticky="ew", pady=(0, 10))
        
        # Update memory status periodically
        self.update_memory_status()
    
    def update_memory_status(self):
        """Update the memory status display with proper formatting"""
        try:
            if self.ai_engine and hasattr(self.ai_engine, 'conversation_memory'):
                docs = self.ai_engine.conversation_memory.get_document_content()
                if docs:
                    doc_list = list(docs.keys())
                    if len(doc_list) == 1:
                        self.memory_status_var.set(f"📄 {doc_list[0]}")
                    elif len(doc_list) <= 4:  # Augmenté de 3 à 4 pour plus de documents visibles
                        # Formatage amélioré avec alignement
                        doc_display = "\n".join([f"• {doc}" for doc in doc_list])
                        self.memory_status_var.set(doc_display)
                    else:
                        # Pour plus de 4 documents, afficher les 4 premiers + compteur
                        first_four = doc_list[:4]
                        doc_display = "\n".join([f"• {doc}" for doc in first_four])
                        doc_display += f"\n• ... et {len(doc_list)-4} autres"
                        self.memory_status_var.set(doc_display)
                    
                    if CTK_AVAILABLE and hasattr(self, 'memory_status_display'):
                        self.memory_status_display.configure(text_color="green")
                else:
                    self.memory_status_var.set("Aucun document")
                    if CTK_AVAILABLE and hasattr(self, 'memory_status_display'):
                        self.memory_status_display.configure(text_color="gray")
        except Exception as e:
            self.logger.error(f"Error updating memory status: {e}")
        
        # Schedule next update
        self.root.after(2000, self.update_memory_status)  # Update every 2 seconds

    def show_welcome_message(self):
        """Affiche le message de bienvenue au démarrage"""
        welcome_msg = """🎉 Bienvenue dans votre Assistant IA Local ! 🎉

🔵 VOUS UTILISEZ GUI.PY - PAS CORRIGÉ ! 🔵

🚀 Votre IA personnelle est maintenant 100% locale et modulaire !

✨ Que puis-je faire pour vous ?
• 💬 Conversations naturelles avec mémoire persistante
• 🔍 Réponses aux questions sur mon identité et mes capacités
• 💻 Génération de code dans plusieurs langages (Python, JavaScript, HTML/CSS...)
• 🧠 Raisonnement logique et résolution de problèmes
• 📚 Explications de concepts techniques
• 🎯 Détection intelligente de vos intentions

🔧 Fonctionnalités avancées :
• Architecture modulaire avec 6 modules spécialisés
• Mémoire de conversation pour des réponses contextuelles
• Fonctionnement 100% local (pas besoin d'internet)
• Réponses personnalisées selon votre style de communication

💡 Exemples de commandes :
• "Tu es qui ?" - Pour connaître mon identité
• "Que peux-tu faire ?" - Pour voir mes capacités
• "Génère-moi une fonction Python pour..." - Pour du code
• "Explique-moi le concept de..." - Pour des explications
• "Comment résoudre..." - Pour de l'aide au raisonnement

🎨 Tapez votre message dans la zone de saisie ci-dessous et appuyez sur Entrée !
───────────────────────────────────────────────────────────────────────────────
"""
        self.add_to_chat("Assistant IA", welcome_msg)
    
    def run(self):
        """Run the GUI application."""
        self.logger.info("Starting AI Assistant GUI")
        self.root.mainloop()


def main():
    """Main entry point for the GUI application."""
    try:
        app = AIAssistantGUI()
        app.run()
    except Exception as e:
        from utils.logger import Logger
        logger = Logger.get_logger("gui_main")
        logger.error(f"Error running GUI application: {e}")
        print(f"Error: {e}")


if __name__ == "__main__":
    main()
