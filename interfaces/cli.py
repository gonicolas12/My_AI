"""
Interface en ligne de commande pour l'IA personnelle
"""

import asyncio
import sys
import traceback
from pathlib import Path
from core.ai_engine import AIEngine
from core.config import get_config
from core.agent_orchestrator import AgentOrchestrator, WorkflowTemplates
from utils.logger import setup_logger
from utils.file_manager import FileManager

# Ajout du dossier parent au path pour les imports
sys.path.append(str(Path(__file__).parent.parent))

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
        self.agent_orchestrator = None
        self.running = False
        self.prompt = get_config().get("ui.cli.prompt", "🤖 MyAI> ")

    async def initialize(self):
        """
        Initialise l'IA
        """
        try:
            print("🔄 Initialisation de l'IA personnelle...")
            self.ai_engine = AIEngine()
            print("✅ IA initialisée avec succès!")

            # Initialiser l'orchestrateur d'agents
            print("🤖 Initialisation du système d'agents...")
            self.agent_orchestrator = AgentOrchestrator()
            print("✅ Système d'agents prêt!")

            self.logger.info("Interface CLI démarrée")
        except Exception as e:
            print(f"❌ Erreur lors de l'initialisation: {e}")
            self.logger.error("Erreur d'initialisation: %s", e)
            sys.exit(1)

    async def run(self):
        """
        Lance l'interface CLI principale
        """
        await self.initialize()
        self.running = True

        print("\n" + "=" * 60)
        print("🤖 IA PERSONNELLE - INTERFACE CLI")
        print("=" * 60)
        print("Tapez 'aide' pour voir les commandes disponibles")
        print("Tapez 'quitter' pour fermer l'application")
        print("=" * 60 + "\n")

        while self.running:
            try:
                # Lecture de l'entrée utilisateur
                user_input = input(self.prompt).strip()

                if not user_input:
                    continue

                # Traitement des commandes spéciales
                if user_input.lower() in ["quitter", "exit", "quit"]:
                    await self.handle_quit()
                elif user_input.lower() in ["aide", "help"]:
                    self.show_help()
                elif user_input.lower() in ["statut", "status"]:
                    await self.show_status()
                elif user_input.lower().startswith("agent "):
                    await self.handle_agent_command(user_input)
                elif user_input.lower() in ["agents", "list-agents"]:
                    self.show_agents()
                elif user_input.lower().startswith("workflow "):
                    await self.handle_workflow_command(user_input)
                elif user_input.lower() in ["historique", "history"]:
                    self.show_history()
                elif user_input.lower().startswith("fichier "):
                    await self.handle_file_command(user_input)
                elif user_input.lower().startswith("generer "):
                    await self.handle_generate_command(user_input)
                else:
                    # Requête normale à l'IA
                    await self.handle_query(user_input)

            except KeyboardInterrupt:
                print(
                    "\n\n🛑 Interruption détectée. Tapez 'quitter' pour fermer proprement."
                )
            except EOFError:
                print("\n👋 Au revoir!")
                break
            except Exception as e:
                print(f"❌ Erreur: {e}")
                self.logger.error("Erreur CLI: %s", e)

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

        except (AttributeError, TypeError, ValueError, ConnectionError) as e:
            print(f"❌ Erreur lors du traitement: {e}")
            self.logger.error("Erreur traitement requête: %s", e)

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

        except (FileNotFoundError, OSError, ValueError) as e:
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

        except (ValueError, TypeError, AttributeError) as e:
            print(f"❌ Erreur commande génération: {e}")

    async def handle_agent_command(self, command: str):
        """
        Traite les commandes d'agents IA

        Args:
            command: Commande agent (format: agent <type> <tâche>)
        """
        try:
            parts = command.split(" ", 2)
            if len(parts) < 3:
                print("❌ Usage: agent <type> <tâche>")
                print("Exemples:")
                print("  agent code Crée une fonction qui trie une liste")
                print("  agent web Cherche les groupes de la Coupe du monde 2026")
                print("  agent analyst Analyse ces données: [1,2,3,4,5]")
                print("\nTapez 'agents' pour voir la liste des agents disponibles")
                return

            agent_type = parts[1].lower()
            task = parts[2]

            print(f"\n🎯 Exécution de l'agent: {agent_type.upper()}")
            print(f"📋 Tâche: {task}")
            print("=" * 60)

            # Exécuter la tâche avec l'agent
            result = self.agent_orchestrator.execute_single_task(agent_type, task)

            # Afficher le résultat
            if result.get("success"):
                print("\n✅ Résultat:")
                print("-" * 60)
                print(result.get("result", "Pas de résultat"))
                print("-" * 60)
                print(f"⏱️  {result.get('timestamp', 'N/A')}")
            else:
                print(f"\n❌ Erreur: {result.get('error')}")
                if "available_agents" in result:
                    print(f"Agents disponibles: {', '.join(result['available_agents'])}")

        except (ValueError, TypeError, AttributeError, KeyError) as e:
            print(f"❌ Erreur commande agent: {e}")

    async def handle_workflow_command(self, command: str):
        """
        Traite les commandes de workflow multi-agents

        Args:
            command: Commande workflow
        """
        try:
            parts = command.split(" ", 2)
            if len(parts) < 3:
                print("❌ Usage: workflow <template> <description>")
                print("\nTemplates disponibles:")
                print("  • dev <description>       - Développement (planner → code → debug)")
                print("  • web <sujet>            - Recherche Internet (web → analyst → creative)")
                print("  • debug <code> <erreur>   - Debug (debug → code)")
                print("\nExemple:")
                print("  workflow dev Une API REST pour gérer des utilisateurs")
                return

            template = parts[1].lower()
            description = parts[2]

            print(f"\n🎯 Workflow multi-agents: {template.upper()}")
            print(f"📋 {description}")
            print("=" * 60)

            # Sélectionner le template
            if template == "dev":
                task_desc, workflow = WorkflowTemplates.code_development(description)
            elif template == "web":
                task_desc, workflow = WorkflowTemplates.research_and_document(description)
            elif template == "debug":
                # Pour debug, on s'attend à ce que description soit au format "code | erreur"
                if "|" in description:
                    code, error = description.split("|", 1)
                    task_desc, workflow = WorkflowTemplates.debug_and_fix(code.strip(), error.strip())
                else:
                    print("❌ Pour le template debug, utilisez: workflow debug <code> | <erreur>")
                    return
            else:
                print(f"❌ Template inconnu: {template}")
                print("Templates disponibles: dev, web, debug")
                return

            # Exécuter le workflow
            result = self.agent_orchestrator.execute_multi_agent_task(task_desc, workflow)

            # Afficher les résultats
            print("\n📊 Résumé du workflow:")
            print(f"  Tâches: {result['summary']['total_tasks']}")
            print(f"  Réussies: {result['summary']['successful']}")
            print(f"  Taux de succès: {result['summary']['success_rate']:.1%}")

            # Afficher chaque étape
            for idx, agent_result in enumerate(result["results"], 1):
                print(f"\n{'='*60}")
                print(f"Étape {idx}: {agent_result['agent'].upper()}")
                print(f"{'='*60}")
                if agent_result["success"]:
                    # Limiter l'affichage à 500 caractères pour la lisibilité
                    result_text = agent_result["result"]
                    if len(result_text) > 500:
                        print(result_text[:500] + "\n... (tronqué)")
                    else:
                        print(result_text)
                else:
                    print(f"❌ Erreur: {agent_result.get('error')}")

            print(f"\n{'='*60}")
            print(f"✅ Workflow terminé: {result.get('timestamp', 'N/A')}")

        except (ValueError, TypeError, AttributeError, KeyError) as e:
            print(f"❌ Erreur commande workflow: {e}")
            traceback.print_exc()

    def show_agents(self):
        """
        Affiche la liste des agents disponibles
        """
        if not self.agent_orchestrator:
            print("❌ Système d'agents non initialisé")
            return

        print("\n🤖 AGENTS IA DISPONIBLES:")
        print("=" * 60)

        agents_info = {
            "code": ("🐍 CodeAgent", "Génération et debug de code", "Prec: 0.3"),
            "web": ("🌐 WebAgent", "Recherche Internet & Fact-Checking", "Bal: 0.5"),
            "analyst": ("📊 AnalystAgent", "Analyse de données", "Anal: 0.4"),
            "creative": ("✨ CreativeAgent", "Contenu créatif", "Créa: 0.8"),
            "debug": ("🐛 DebugAgent", "Debug et correction", "Prec: 0.2"),
            "planner": ("📋 PlannerAgent", "Planification", "Méth: 0.5"),
        }

        for _agent_type, (icon_name, desc, temp) in agents_info.items():
            print(f"{icon_name:<25} - {desc:<30} ({temp})")

        # Afficher les agents actifs
        active = self.agent_orchestrator.list_active_agents()
        if active:
            print(f"\n✅ Agents actifs: {', '.join(active)}")

        # Statistiques si des agents ont été utilisés
        stats = self.agent_orchestrator.get_orchestrator_stats()
        if stats["total_tasks"] > 0:
            print("\n📊 Statistiques:")
            print(f"  Tâches totales: {stats['total_tasks']}")

        print("\n💡 Usage: agent <type> <tâche>")
        print("💡 Workflow: workflow <template> <description>")

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

🤖 AGENTS IA:
    • agents                         - Liste tous les agents disponibles
    • agent <type> <tâche>           - Exécute une tâche avec un agent
      Exemple: agent code Crée une fonction qui trie une liste
      Types: code, web, analyst, creative, debug, planner
    
    • workflow <template> <description> - Exécute un workflow multi-agents
      Templates:
        - dev <projet>       : Planner → Code → Debug
        - web <sujet>        : Web → Analyst → Creative
        - debug <code|err>   : Debug → Code
      Exemple: workflow dev Une API REST pour gérer des utilisateurs

⚙️  SYSTÈME:
    • statut     - Affiche le statut de l'IA
    • historique - Affiche l'historique des conversations
    • aide       - Affiche cette aide
    • quitter    - Ferme l'application

💡 CONSEILS:
    • Soyez précis dans vos demandes
    • Les fichiers générés sont sauvés dans le dossier 'outputs'
    • L'historique est conservé pendant la session
    • Les agents sont spécialisés: utilisez le bon agent pour la bonne tâche!
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

            llm_status = status.get("llm_status", {})
            print(f"🧠 Backend actif: {llm_status.get('active_backend', 'Aucun')}")
            print(
                f"🔌 Backends disponibles: {', '.join(llm_status.get('available_backends', []))}"
            )

            print(f"💬 Conversations: {status.get('conversation_count', 0)}")

            # Informations sur les backends
            backend_info = llm_status.get("backend_info", {})
            for name, info in backend_info.items():
                available = "✅" if info.get("available") else "❌"
                print(f"   {available} {name}: {info.get('model', 'N/A')}")

        except (AttributeError, KeyError, TypeError) as e:
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
                timestamp = exchange.get("timestamp", "Inconnu")
                user_input = (
                    exchange.get("user_input", "")[:50] + "..."
                    if len(exchange.get("user_input", "")) > 50
                    else exchange.get("user_input", "")
                )
                response_type = exchange.get("ai_response", {}).get("type", "inconnu")

                print(f"{i}. [{timestamp[:19]}] {response_type}")
                print(f"   👤 {user_input}")
                print()

        except (AttributeError, KeyError, TypeError, IndexError) as e:
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
            except (OSError, PermissionError, TypeError) as e:
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
