#!/usr/bin/env python3
"""
My Personal AI - IA Locale Complète
Point d'entrée principal de l'application
"""

import asyncio
import argparse
import sys
from pathlib import Path

# Ajout du répertoire courant au path Python
sys.path.insert(0, str(Path(__file__).parent))

from interfaces.cli import CLIInterface
from core.ai_engine import AIEngine
from utils.logger import setup_logger

def parse_arguments():
    """
    Parse les arguments de ligne de commande
    
    Returns:
        Arguments parsés
    """
    parser = argparse.ArgumentParser(
        description="My Personal AI - IA locale complète",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemples d'utilisation:
  python main.py                           # Lance l'interface CLI interactive
  python main.py --mode cli                # Lance l'interface CLI
  python main.py chat "Bonjour l'IA"       # Requête directe
  python main.py status                     # Affiche le statut
  python main.py --help                     # Affiche cette aide

Mode interactif:
  Une fois lancé, tapez 'aide' pour voir toutes les commandes disponibles.
        """
    )
    
    parser.add_argument(
        "--mode",
        choices=["cli", "gui"],
        default="cli",
        help="Mode d'interface (défaut: cli)"
    )
    
    parser.add_argument(
        "--config",
        type=str,
        help="Fichier de configuration personnalisé"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Mode verbeux (plus de logs)"
    )
    
    parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="Mode silencieux (moins de logs)"
    )
    
    # Sous-commandes
    subparsers = parser.add_subparsers(dest="command", help="Commandes disponibles")
    
    # Commande chat
    chat_parser = subparsers.add_parser("chat", help="Envoi d'une requête directe")
    chat_parser.add_argument("query", help="Requête à envoyer à l'IA")
    
    # Commande status
    status_parser = subparsers.add_parser("status", help="Affiche le statut de l'IA")
    
    # Commande file
    file_parser = subparsers.add_parser("file", help="Traite un fichier")
    file_parser.add_argument("action", choices=["read", "analyze"], help="Action à effectuer")
    file_parser.add_argument("path", help="Chemin vers le fichier")
    
    # Commande generate
    gen_parser = subparsers.add_parser("generate", help="Génère du contenu")
    gen_parser.add_argument("type", choices=["code", "document"], help="Type de contenu")
    gen_parser.add_argument("description", help="Description du contenu à générer")
    gen_parser.add_argument("--output", "-o", help="Fichier de sortie")
    
    return parser.parse_args()

async def handle_chat_command(query: str):
    """
    Traite une commande chat directe
    
    Args:
        query: Requête utilisateur
    """
    try:
        print("🔄 Initialisation de l'IA...")
        ai_engine = AIEngine()
        
        print(f"🤔 Traitement de: {query}")
        response = await ai_engine.process_query(query)
        
        print("\\n💡 Réponse:")
        print("-" * 40)
        
        if response.get("success"):
            response_type = response.get("type", "unknown")
            
            if response_type == "conversation":
                print(response.get("message", "Pas de réponse"))
            elif response_type == "code_generation":
                print("📝 Code généré:")
                print("```")
                print(response.get("code", "Pas de code"))
                print("```")
            else:
                print(response.get("message", "Réponse reçue"))
        else:
            print(f"❌ Erreur: {response.get('message', 'Erreur inconnue')}")
            
    except Exception as e:
        print(f"❌ Erreur: {e}")
        sys.exit(1)

async def handle_status_command():
    """
    Affiche le statut de l'IA
    """
    try:
        print("🔄 Vérification du statut...")
        ai_engine = AIEngine()
        status = ai_engine.get_status()
        
        print("\\n📊 STATUT DE L'IA:")
        print("-" * 30)
        print(f"🚀 Moteur: {status.get('engine', 'Inconnu')}")
        
        llm_status = status.get('llm_status', {})
        if isinstance(llm_status, dict):
            print(f"🧠 Backend actif: {llm_status.get('active_backend', 'Aucun')}")
            print(f"🔌 Backends disponibles: {', '.join(llm_status.get('available_backends', []))}")
            
            backend_info = llm_status.get('backend_info', {})
            for name, info in backend_info.items():
                available = "✅" if info.get('available') else "❌"
                print(f"   {available} {name}: {info.get('model', 'N/A')}")
        else:
            print(f"🧠 Statut LLM: {llm_status}")
            
    except Exception as e:
        print(f"❌ Erreur: {e}")
        sys.exit(1)

async def handle_file_command(action: str, file_path: str):
    """
    Traite une commande de fichier
    
    Args:
        action: Action à effectuer
        file_path: Chemin du fichier
    """
    try:
        ai_engine = AIEngine()
        
        if action == "read":
            query = f"Lis le fichier {file_path} et résume son contenu"
        elif action == "analyze":
            query = f"Analyse le fichier {file_path} en détail"
        else:
            print(f"❌ Action inconnue: {action}")
            return
        
        print(f"🔄 {action.capitalize()} du fichier: {file_path}")
        response = await ai_engine.process_query(query)
        
        if response.get("success"):
            print(f"\\n📁 Résultat:")
            print("-" * 40)
            print(response.get("message", "Traitement effectué"))
        else:
            print(f"❌ Erreur: {response.get('message', 'Erreur inconnue')}")
            
    except Exception as e:
        print(f"❌ Erreur: {e}")
        sys.exit(1)

async def handle_generate_command(gen_type: str, description: str, output_file: str = None):
    """
    Traite une commande de génération
    
    Args:
        gen_type: Type de génération
        description: Description du contenu
        output_file: Fichier de sortie optionnel
    """
    try:
        ai_engine = AIEngine()
        
        if gen_type == "code":
            query = f"Génère du code pour: {description}"
        elif gen_type == "document":
            query = f"Crée un document sur: {description}"
        else:
            print(f"❌ Type de génération inconnu: {gen_type}")
            return
        
        print(f"🔄 Génération de {gen_type}: {description}")
        response = await ai_engine.process_query(query)
        
        if response.get("success"):
            print(f"\\n🎉 {gen_type.capitalize()} généré!")
            print("-" * 40)
            
            if gen_type == "code":
                code = response.get("code", "")
                if output_file:
                    with open(output_file, 'w', encoding='utf-8') as f:
                        f.write(code)
                    print(f"💾 Code sauvé dans: {output_file}")
                else:
                    print("📝 Code généré:")
                    print("```")
                    print(code)
                    print("```")
            else:
                print(response.get("message", "Génération effectuée"))
        else:
            print(f"❌ Erreur: {response.get('message', 'Erreur inconnue')}")
            
    except Exception as e:
        print(f"❌ Erreur: {e}")
        sys.exit(1)

def setup_logging(verbose: bool = False, quiet: bool = False):
    """
    Configure le logging selon les options
    
    Args:
        verbose: Mode verbeux
        quiet: Mode silencieux
    """
    import logging
    
    if quiet:
        level = logging.ERROR
    elif verbose:
        level = logging.DEBUG
    else:
        level = logging.INFO
    
    setup_logger("MyAI", level)

def print_banner():
    """
    Affiche la bannière de l'application
    """
    banner = """
╔══════════════════════════════════════════════════════════════╗
║                    🤖 MY PERSONAL AI 🤖                      ║
║                                                              ║
║            IA Locale Complète - Version 1.0                 ║
║        Répondre, Lire, Générer, Analyser - Tout Local!     ║
╚══════════════════════════════════════════════════════════════╝
    """
    print(banner)

async def main():
    """
    Fonction principale de l'application
    """
    try:
        args = parse_arguments()
        
        # Configuration du logging
        setup_logging(args.verbose, args.quiet)
        
        # Affichage de la bannière si mode interactif
        if not args.command:
            print_banner()
        
        # Traitement des commandes
        if args.command == "chat":
            await handle_chat_command(args.query)
        
        elif args.command == "status":
            await handle_status_command()
        
        elif args.command == "file":
            await handle_file_command(args.action, args.path)
        
        elif args.command == "generate":
            await handle_generate_command(args.type, args.description, args.output)
        
        else:
            # Mode interactif
            if args.mode == "cli":
                cli = CLIInterface()
                await cli.run()
            elif args.mode == "gui":
                print("🚧 Interface GUI en cours de développement...")
                print("💡 Utilisez le mode CLI pour le moment: python main.py --mode cli")
            else:
                print(f"❌ Mode inconnu: {args.mode}")
                sys.exit(1)
    
    except KeyboardInterrupt:
        print("\\n\\n👋 Interruption utilisateur. Au revoir!")
    except Exception as e:
        print(f"\\n❌ Erreur critique: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

# CORRECTION : Fonction pour compatibilité avec le launcher
def main_sync():
    """
    Fonction main synchrone pour compatibilité avec le launcher
    """
    return asyncio.run(main())

# Fonction d'entrée alternative pour l'import direct
def cli_main():
    """Point d'entrée pour le CLI depuis le launcher"""
    return main_sync()

if __name__ == "__main__":
    main_sync()