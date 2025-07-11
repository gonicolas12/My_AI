"""
Interface graphique simplifiée pour l'assistant IA local
Mode entreprise : minimal et sécurisé
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import threading
import sys
import os
from pathlib import Path

# Ajouter le projet au path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


class SimpleAIGUI:
    """Interface graphique simplifiée pour l'assistant IA local"""
    
    def __init__(self):
        """Initialise l'interface"""
        self.setup_gui()
        self.init_ai_engine()
        
    def setup_gui(self):
        """Configure l'interface graphique"""
        self.root = tk.Tk()
        self.root.title("🤖 Assistant IA Local - Mode Entreprise")
        self.root.geometry("900x700")
        self.root.minsize(600, 500)
        
        # Configuration de style
        self.setup_styles()
        
        # Création des widgets
        self.create_widgets()
        
    def setup_styles(self):
        """Configure les styles"""
        self.style = ttk.Style()
        self.style.theme_use('clam')
        
    def create_widgets(self):
        """Crée les widgets de l'interface"""
        # Frame principal
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configuration du grid
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(1, weight=1)
        
        # Titre
        title_label = ttk.Label(
            main_frame, 
            text="🤖 Assistant IA Local - Mode Entreprise", 
            font=('Arial', 16, 'bold')
        )
        title_label.grid(row=0, column=0, pady=(0, 10), sticky='w')
        
        # Indicateur de statut
        status_frame = ttk.Frame(main_frame)
        status_frame.grid(row=0, column=1, sticky='e')
        
        self.status_label = ttk.Label(
            status_frame, 
            text="🟢 100% Local", 
            foreground="green",
            font=('Arial', 10, 'bold')
        )
        self.status_label.grid(row=0, column=0)
        
        # Zone de conversation
        conversation_frame = ttk.LabelFrame(main_frame, text="💬 Conversation", padding="5")
        conversation_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        conversation_frame.columnconfigure(0, weight=1)
        conversation_frame.rowconfigure(0, weight=1)
        
        # Zone d'affichage des messages
        self.conversation_display = scrolledtext.ScrolledText(
            conversation_frame,
            height=20,
            font=('Consolas', 10),
            wrap=tk.WORD,
            state='disabled'
        )
        self.conversation_display.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Zone de saisie
        input_frame = ttk.Frame(main_frame)
        input_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        input_frame.columnconfigure(0, weight=1)
        
        self.user_input = tk.Text(input_frame, height=3, font=('Arial', 10))
        self.user_input.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 5))
        
        # Bouton d'envoi
        self.send_button = ttk.Button(
            input_frame, 
            text="Envoyer", 
            command=self.send_message
        )
        self.send_button.grid(row=0, column=1)
        
        # Bind Enter pour envoyer
        self.user_input.bind('<Control-Return>', lambda e: self.send_message())
        
        # Boutons utiles
        buttons_frame = ttk.Frame(main_frame)
        buttons_frame.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E))
        
        ttk.Button(buttons_frame, text="Aide", command=self.show_help).grid(row=0, column=0, padx=(0, 5))
        ttk.Button(buttons_frame, text="Effacer", command=self.clear_conversation).grid(row=0, column=1, padx=(0, 5))
        ttk.Button(buttons_frame, text="Statut", command=self.show_status).grid(row=0, column=2, padx=(0, 5))
        
        # Message d'accueil
        self.add_message("Assistant", "🤖 Bonjour ! Je suis votre assistant IA local.\n✅ Toutes vos données restent sur votre machine.\n✅ Aucune connexion externe requise.\n\nQue puis-je faire pour vous ?")
        
    def init_ai_engine(self):
        """Initialise le moteur IA"""
        try:
            from core.ai_engine import AIEngine
            self.ai_engine = AIEngine()
            self.add_message("Système", "✅ Moteur IA local initialisé avec succès")
        except Exception as e:
            self.ai_engine = None
            self.add_message("Système", f"❌ Erreur d'initialisation : {e}")
            
    def send_message(self):
        """Envoie un message à l'IA"""
        message = self.user_input.get("1.0", tk.END).strip()
        
        if not message:
            return
            
        # Effacer la zone de saisie
        self.user_input.delete("1.0", tk.END)
        
        # Afficher le message utilisateur
        self.add_message("Vous", message)
        
        # Désactiver le bouton d'envoi
        self.send_button.config(state='disabled')
        
        # Traiter en arrière-plan
        threading.Thread(target=self.process_message, args=(message,), daemon=True).start()
        
    def process_message(self, message):
        """Traite le message avec l'IA"""
        try:
            if self.ai_engine:
                response = self.ai_engine.process_text(message)
            else:
                response = "❌ Moteur IA non disponible. Vérifiez l'initialisation."
                
            # Afficher la réponse
            self.root.after(0, lambda: self.add_message("Assistant", response))
            
        except Exception as e:
            error_msg = f"❌ Erreur lors du traitement : {e}"
            self.root.after(0, lambda: self.add_message("Système", error_msg))
            
        finally:
            # Réactiver le bouton
            self.root.after(0, lambda: self.send_button.config(state='normal'))
            
    def add_message(self, sender, message):
        """Ajoute un message à la conversation"""
        self.conversation_display.config(state='normal')
        
        # Formatage selon l'expéditeur
        if sender == "Vous":
            prefix = "👤 Vous : "
        elif sender == "Assistant":
            prefix = "🤖 Assistant : "
        else:
            prefix = f"ℹ️  {sender} : "
            
        self.conversation_display.insert(tk.END, f"{prefix}{message}\n\n")
        self.conversation_display.see(tk.END)
        self.conversation_display.config(state='disabled')
        
    def clear_conversation(self):
        """Efface la conversation"""
        if messagebox.askyesno("Confirmation", "Effacer toute la conversation ?"):
            self.conversation_display.config(state='normal')
            self.conversation_display.delete(1.0, tk.END)
            self.conversation_display.config(state='disabled')
            
            # Réinitialiser l'historique
            if self.ai_engine:
                self.ai_engine.clear_conversation()
                
            # Message d'accueil
            self.add_message("Assistant", "Conversation effacée. Comment puis-je vous aider ?")
            
    def show_help(self):
        """Affiche l'aide"""
        if self.ai_engine:
            response = self.ai_engine.process_text("aide")
            self.add_message("Assistant", response)
        else:
            help_text = """🤖 Aide 🤖

📝 **Commandes possibles :**
• "génère une fonction pour..."
• "crée une classe..."
• "explique-moi..."
• "aide"

✅ **Fonctionnement :**
• 100% local - aucune donnée envoyée
• Modèle IA personnalisé
• Génération de code intelligente"""
            self.add_message("Assistant", help_text)
            
    def show_status(self):
        """Affiche le statut du système"""
        if self.ai_engine:
            try:
                status = self.ai_engine.get_status()
                status_text = f"""📊 **Statut du Système**

🔧 **Moteur :** {status.get('engine', 'inconnu')}
🔒 **Mode :** {status.get('mode', 'local')}
🤖 **IA :** {status.get('llm_status', 'local_model')}
💬 **Conversations :** {status.get('conversation_count', 0)}

✅ **Sécurité :** 100% local, aucune donnée externe"""
                self.add_message("Système", status_text)
            except Exception as e:
                self.add_message("Système", f"❌ Erreur de statut : {e}")
        else:
            self.add_message("Système", "❌ Moteur IA non initialisé")
            
    def run(self):
        """Lance l'interface"""
        print("✅ Interface graphique lancée")
        print("💡 Utilisez Ctrl+Enter pour envoyer rapidement")
        self.root.mainloop()


if __name__ == "__main__":
    try:
        app = SimpleAIGUI()
        app.run()
    except Exception as e:
        print(f"❌ Erreur de lancement : {e}")
        print("💡 Essayez : python launch_local.py --console")
