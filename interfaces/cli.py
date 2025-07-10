"""
Interface en ligne de commande pour l'IA personnelle
"""

import asyncio
import sys
from pathlib import Path
from typing import Dict, Any, Optional

# Ajout du dossier parent au path pour les imports
sys.path.append(str(Path(__file__).parent.parent))

from core.ai_engine import AIEngine
from core.config import UI_CONFIG
from utils.logger import setup_logger

class CLIInterface:
    """
    Interface en ligne de commande
    """
    
    def __init__(self):
        """
        Initialise l'interface CLI
        """
        self.logger = setup_logger("CLI")
        self.ai_engine = None
        self.running = False
        self.prompt = UI_CONFIG.get("cli_prompt", "🤖 MyAI> ")
    
    async def initialize(self):
        """
        Initialise l'IA
        """
        try:
            print("🔄 Initialisation de l'IA personnelle...")
            self.ai_engine = AIEngine()
            print("✅ IA initialisée avec succès!")
            self.logger.info("Interface CLI démarrée")
        except Exception as e:
            print(f"❌ Erreur lors de l'initialisation: {e}")
            self.logger.error(f"Erreur d'initialisation: {e}")
            sys.exit(1)
    
    async def run(self):
        """
        Lance l'interface CLI principale
        """
        await self.initialize()
        self.running = True
        
        print("\n" + "="*60)
        print("🤖 IA PERSONNELLE - INTERFACE CLI")
        print("="*60)
        print("Tapez 'aide' pour voir les commandes disponibles")
        print("Tapez 'quitter' pour fermer l'application")
        print("="*60 + "\n")
        
        while self.running:
            try:
                # Lecture de l'entrée utilisateur
                user_input = input(self.prompt).strip()
                
                if not user_input:
                    continue
                
                # Traitement des commandes spéciales
                if user_input.lower() in ['quitter', 'exit', 'quit']:
                    await self.handle_quit()
                elif user_input.lower() in ['aide', 'help']:
                    self.show_help()
                elif user_input.lower() in ['statut', 'status']:
                    await self.show_status()
                elif user_input.lower() in ['historique', 'history']:
                    self.show_history()
                elif user_input.lower().startswith('fichier '):
                    await self.handle_file_command(user_input)
                elif user_input.lower().startswith('generer '):
                    await self.handle_generate_command(user_input)
                else:
                    # Requête normale à l'IA
                    await self.handle_query(user_input)
                    
            except KeyboardInterrupt:
                print("\n\n🛑 Interruption détectée. Tapez 'quitter' pour fermer proprement.")
            except EOFError:
                print("\n👋 Au revoir!")
                break
            except Exception as e:
                print(f"❌ Erreur: {e}")
                self.logger.error(f"Erreur CLI: {e}")
    
    async def handle_query(self, query: str):
        """
        Traite une requête utilisateur
        
        Args:
            query: Requête de l'utilisateur
        """
        try:
            print("🤔 Réflexion en cours...")
            
            # Envoi de la requête à l'IA
            response = await self.ai_engine.process_query(query)
            
            if response.get("success"):
                print("\n💡 Réponse:")
                print("-" * 40)
                
                # Affichage selon le type de réponse
                response_type = response.get("type", "unknown")
                
                if response_type == "conversation":
                    print(response.get("message", "Pas de réponse"))
                
                elif response_type == "code_generation":
                    print("📝 Code généré:")
                    print("```")
                    print(response.get("code", "Pas de code"))
                    print("```")
                
                elif response_type == "document_generation":
                    doc_info = response.get("document", {})
                    if doc_info.get("success"):
                        print(f"📄 Document généré: {doc_info.get('file_name')}")
                        print(f"📁 Chemin: {doc_info.get('file_path')}")
                    else:
                        print(f"❌ Erreur de génération: {doc_info.get('error')}")
                
                elif response_type == "file_processing":
                    print("📁 Traitement de fichier terminé")
                    print(response.get("message", "Traitement effectué"))
                
                else:
                    print(response.get("message", "Réponse reçue"))
                
            else:
                print(f"❌ Erreur: {response.get('message', 'Erreur inconnue')}")
                
        except Exception as e:
            print(f"❌ Erreur lors du traitement: {e}")
            self.logger.error(f"Erreur traitement requête: {e}")
        
        print()  # Ligne vide pour la lisibilité
    
    async def handle_file_command(self, command: str):
        """
        Traite les commandes de fichier
        
        Args:
            command: Commande fichier
        """
        try:
            parts = command.split(" ", 2)
            if len(parts) < 3:
                print("❌ Usage: fichier <action> <chemin>")
                print("Actions disponibles: lire, analyser, info")
                return
            
            action = parts[1].lower()
            file_path = parts[2]
            
            if action == "lire":
                query = f"Lis le fichier {file_path} et résume son contenu"
                await self.handle_query(query)
            
            elif action == "analyser":
                query = f"Analyse le fichier {file_path} en détail"
                await self.handle_query(query)
            
            elif action == "info":
                from utils.file_manager import FileManager
                fm = FileManager()
                info = fm.get_file_info(file_path)
                
                if info.get("exists"):
                    print("📋 Informations du fichier:")
                    print(f"   Nom: {info['name']}")
                    print(f"   Taille: {info['size_human']}")
                    print(f"   Type: {info['file_type']}")
                    print(f"   Modifié: {info['modified']}")
                else:
                    print("❌ Fichier non trouvé")
            
            else:
                print(f"❌ Action inconnue: {action}")
                
        except Exception as e:
            print(f"❌ Erreur commande fichier: {e}")
    
    async def handle_generate_command(self, command: str):
        """
        Traite les commandes de génération
        
        Args:
            command: Commande de génération
        """
        try:
            # Extraction du type et de la description
            parts = command.split(" ", 2)
            if len(parts) < 3:
                print("❌ Usage: generer <type> <description>")
                print("Types disponibles: code, document, rapport")
                return
            
            gen_type = parts[1].lower()
            description = parts[2]
            
            if gen_type == "code":
                query = f"Génère du code pour: {description}"
            elif gen_type == "document":
                query = f"Crée un document sur: {description}"
            elif gen_type == "rapport":
                query = f"Génère un rapport concernant: {description}"
            else:
                print(f"❌ Type de génération inconnu: {gen_type}")
                return
            
            await self.handle_query(query)
            
        except Exception as e:
            print(f"❌ Erreur commande génération: {e}")
    
    def show_help(self):
        """
        Affiche l'aide
        """
        help_text = """
📚 AIDE - Commandes disponibles:

🗣️  CONVERSATION:
    • Tapez votre question directement
    • Exemple: "Explique-moi les listes en Python"

📁 FICHIERS:
    • fichier lire <chemin>     - Lit et résume un fichier
    • fichier analyser <chemin> - Analyse un fichier en détail
    • fichier info <chemin>     - Affiche les infos du fichier

🛠️  GÉNÉRATION:
    • generer code <description>     - Génère du code
    • generer document <description> - Crée un document
    • generer rapport <description>  - Génère un rapport

⚙️  SYSTÈME:
    • statut     - Affiche le statut de l'IA
    • historique - Affiche l'historique des conversations
    • aide       - Affiche cette aide
    • quitter    - Ferme l'application

💡 CONSEILS:
    • Soyez précis dans vos demandes
    • Les fichiers générés sont sauvés dans le dossier 'outputs'
    • L'historique est conservé pendant la session
        """
        print(help_text)
    
    async def show_status(self):
        """
        Affiche le statut de l'IA
        """
        try:
            if not self.ai_engine:
                print("❌ IA non initialisée")
                return
            
            status = self.ai_engine.get_status()
            
            print("\n📊 STATUT DE L'IA:")
            print("-" * 30)
            print(f"🚀 Moteur: {status.get('engine', 'Inconnu')}")
            
            llm_status = status.get('llm_status', {})
            print(f"🧠 Backend actif: {llm_status.get('active_backend', 'Aucun')}")
            print(f"🔌 Backends disponibles: {', '.join(llm_status.get('available_backends', []))}")
            
            print(f"💬 Conversations: {status.get('conversation_count', 0)}")
            
            # Informations sur les backends
            backend_info = llm_status.get('backend_info', {})
            for name, info in backend_info.items():
                available = "✅" if info.get('available') else "❌"
                print(f"   {available} {name}: {info.get('model', 'N/A')}")
            
        except Exception as e:
            print(f"❌ Erreur récupération statut: {e}")
    
    def show_history(self):
        """
        Affiche l'historique des conversations
        """
        try:
            if not self.ai_engine:
                print("❌ IA non initialisée")
                return
            
            history = self.ai_engine.conversation_manager.get_recent_history(5)
            
            if not history:
                print("📝 Aucun historique disponible")
                return
            
            print("\n📜 HISTORIQUE DES CONVERSATIONS:")
            print("-" * 40)
            
            for i, exchange in enumerate(history, 1):
                timestamp = exchange.get('timestamp', 'Inconnu')
                user_input = exchange.get('user_input', '')[:50] + "..." if len(exchange.get('user_input', '')) > 50 else exchange.get('user_input', '')
                response_type = exchange.get('ai_response', {}).get('type', 'inconnu')
                
                print(f"{i}. [{timestamp[:19]}] {response_type}")
                print(f"   👤 {user_input}")
                print()
            
        except Exception as e:
            print(f"❌ Erreur récupération historique: {e}")
    
    async def handle_quit(self):
        """
        Gère la fermeture de l'application
        """
        print("\n👋 Fermeture de l'IA personnelle...")
        
        # Sauvegarde de la session si nécessaire
        if self.ai_engine and self.ai_engine.conversation_manager:
            try:
                session_file = f"session_{self.ai_engine.conversation_manager.current_session['id'][:8]}.json"
                self.ai_engine.conversation_manager.save_session(f"logs/{session_file}")
                print(f"💾 Session sauvegardée: {session_file}")
            except Exception as e:
                print(f"⚠️  Erreur sauvegarde session: {e}")
        
        self.running = False
        print("✅ Au revoir!")

async def main():
    """
    Fonction principale CLI
    """
    cli = CLIInterface()
    await cli.run()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n👋 Arrêt forcé. Au revoir!")
    except Exception as e:
        print(f"\n❌ Erreur critique: {e}")
        sys.exit(1)
