#!/usr/bin/env python3
"""
My Personal AI - IA Locale Complète avec 1M TOKENS
Point d'entrée principal avec capacités ultra-avancées
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

# 🚀 NOUVEAU : Import du système 1M tokens
try:
    from models.ultra_custom_ai import UltraCustomAIModel
    from core.ai_engine import AIEngine
    ULTRA_MODE_AVAILABLE = True
    print("🚀 Mode Ultra 1M Tokens disponible !")
except ImportError:
    from core.ai_engine import AIEngine
    ULTRA_MODE_AVAILABLE = False
    print("📝 Mode Standard disponible")

def parse_arguments():
    """
    Parse les arguments de ligne de commande
    
    Returns:
        Arguments parsés
    """
    parser = argparse.ArgumentParser(
        description="My Personal AI - IA locale complète avec capacités 1M tokens",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
🚀 Nouvelles fonctionnalités 1M Tokens:
  --ultra                 Active le mode Ultra avec 1M tokens
  --stats                 Affiche les statistiques du contexte
  --optimize              Lance l'optimisation du contexte
  
Exemples d'utilisation:
  python main.py --ultra              # Lance en mode 1M tokens
  python main.py --stats              # Voir les stats du contexte
  python main.py --cli --ultra        # CLI avec 1M tokens
  python main.py --gui --ultra        # Interface graphique avec 1M tokens
"""
    )
    
    # Arguments existants
    parser.add_argument('--cli', action='store_true', help='Lance l\'interface CLI')
    parser.add_argument('--gui', action='store_true', help='Lance l\'interface graphique')
    parser.add_argument('--debug', action='store_true', help='Active le mode debug')
    parser.add_argument('--verbose', '-v', action='count', default=0, help='Niveau de verbosité')
    
    # 🚀 NOUVEAUX arguments pour 1M tokens
    parser.add_argument('--ultra', action='store_true', help='Active le mode Ultra 1M tokens')
    parser.add_argument('--stats', action='store_true', help='Affiche les statistiques du contexte')
    parser.add_argument('--optimize', action='store_true', help='Lance l\'optimisation du contexte')
    parser.add_argument('--test-1m', action='store_true', help='Lance les tests de validation 1M tokens')
    
    return parser.parse_args()

def create_ai_instance(ultra_mode=False):
    """
    Crée l'instance IA appropriée selon le mode
    """
    
    if ultra_mode and ULTRA_MODE_AVAILABLE:
        print("🚀 Initialisation du mode Ultra 1M Tokens...")
        base_ai = AIEngine()
        ai = UltraCustomAIModel(base_ai)
        
        # Afficher les stats initiales
        try:
            stats = ai.get_context_stats()
            print(f"📊 Contexte actuel: {stats.get('current_tokens', 0):,} / {stats.get('max_context_length', 1000000):,} tokens")
            print(f"� Documents: {stats.get('documents_processed', 0)}")
            print(f"🧩 Chunks: {stats.get('chunks_created', 0)}")
        except Exception as e:
            print(f"⚠️ Impossible d'afficher les stats: {e}")
        
        return ai
    else:
        if ultra_mode:
            print("⚠️  Mode Ultra non disponible, utilisation du mode standard")
        else:
            print("📝 Initialisation du mode standard...")
        
        return AIEngine()

def show_ultra_stats():
    """Affiche les statistiques du système 1M tokens"""
    
    if not ULTRA_MODE_AVAILABLE:
        print("❌ Mode Ultra non disponible")
        return
    
    print("📊 STATISTIQUES DU SYSTÈME 1M TOKENS")
    print("=" * 50)
    
    try:
        base_ai = AIEngine()
        ai = UltraCustomAIModel(base_ai)
        stats = ai.get_context_stats()
        
        print(f"🎯 Tokens actifs: {stats.get('current_tokens', 0):,}")
        print(f"📄 Documents traités: {stats.get('documents_processed', 0)}")
        print(f"🧩 Chunks créés: {stats.get('chunks_created', 0)}")
        print(f"📊 Capacité max: {stats.get('max_context_length', 1000000):,} tokens")
        print(f"📈 Utilisation: {(stats.get('current_tokens', 0) / stats.get('max_context_length', 1000000)) * 100:.1f}%")
        
    except Exception as e:
        print(f"❌ Erreur lors de l'affichage des stats: {e}")

def optimize_ultra_context():
    """Lance l'optimisation du contexte 1M tokens"""
    
    if not ULTRA_MODE_AVAILABLE:
        print("❌ Mode Ultra non disponible")
        return
    
    print("🚀 OPTIMISATION DU CONTEXTE 1M TOKENS")
    print("=" * 50)
    
    try:
        base_ai = AIEngine()
        ai = UltraCustomAIModel(base_ai)
        
        # Simple optimisation basique
        ai.clear_context()
        print("✅ Contexte réinitialisé")
        
        # Nouvelles stats
        stats = ai.get_context_stats()
        print(f"📊 Nouvel état: {stats.get('current_tokens', 0):,} tokens actifs")
        
    except Exception as e:
        print(f"❌ Erreur lors de l'optimisation: {e}")

def run_1m_tests():
    """Lance les tests de validation 1M tokens"""
    
    if not ULTRA_MODE_AVAILABLE:
        print("❌ Mode Ultra non disponible")
        return
    
    print("🧪 TESTS DE VALIDATION 1M TOKENS")
    print("=" * 50)
    
    try:
        # Test simple du système Ultra
        base_ai = AIEngine()
        ai = UltraCustomAIModel(base_ai)
        
        # Test d'ajout de document
        test_content = "Ceci est un document de test pour valider le système 1M tokens. " * 100
        result = ai.add_document_to_context(test_content, "Document Test")
        
        if result.get('success', False):
            print("✅ Tests réussis !")
            print(f"🎯 Document ajouté: {result.get('chunks_created', 0)} chunks créés")
            print(f"📊 Tokens ajoutés: {result.get('tokens_added', 0)}")
        else:
            print("⚠️ Tests partiels, vérifiez la configuration")
            print(f"❌ Erreur: {result.get('error', 'Inconnue')}")
            
    except Exception as e:
        print(f"❌ Erreur lors des tests: {e}")

async def main():
    """Fonction principale avec support 1M tokens"""
    
    args = parse_arguments()
    
    # Configuration du logging
    log_level = "DEBUG" if args.debug else "INFO"
    if args.verbose >= 2:
        log_level = "DEBUG"
    elif args.verbose == 1:
        log_level = "INFO"
    
    logger = setup_logger(level=log_level)
    logger.info(f"Démarrage de My Personal AI")
    
    # 🚀 Gestion des nouvelles commandes Ultra
    if args.stats:
        show_ultra_stats()
        return
    
    if args.optimize:
        optimize_ultra_context()
        return
    
    if args.test_1m:
        run_1m_tests()
        return
    
    # Création de l'instance IA
    ai_instance = create_ai_instance(ultra_mode=args.ultra)
    
    # Interface utilisateur
    if args.gui:
        print("🖥️  Lancement de l'interface graphique...")
        
        # Import de l'interface graphique appropriée
        try:
            # Version moderne avec support Ultra
            from interfaces.gui_modern import ModernAIGUI
            gui = ModernAIGUI()
            
            gui.run()
            
        except ImportError as e:
            print(f"⚠️ Interface graphique non disponible: {e}")
            print("Basculement vers CLI")
            args.cli = True
    
    if args.cli or not args.gui:
        print("💻 Lancement de l'interface CLI...")
        
        # Version CLI adaptée
        if args.ultra and ULTRA_MODE_AVAILABLE:
            print("🚀 CLI Mode Ultra 1M Tokens activé")
            
        cli = CLIInterface(ai_instance)
        await cli.run()
    
    logger.info("Arrêt de My Personal AI")

def interactive_mode():
    """Mode interactif pour choisir les options"""
    
    print("🤖 MY PERSONAL AI - ASSISTANT IA LOCAL")
    print("=" * 50)
    
    if ULTRA_MODE_AVAILABLE:
        print("🚀 Mode Ultra 1M Tokens disponible !")
        print("📝 Mode Standard disponible")
        print()
        print("Choisissez votre mode :")
        print("1. Mode Ultra (1M tokens)")
        print("2. Mode Standard") 
        print("3. Voir les statistiques")
        print("4. Optimiser le contexte")
        print("5. Tests de validation")
        
        choice = input("\nVotre choix (1-5): ").strip()
        
        if choice == "1":
            return ["--ultra", "--gui"]
        elif choice == "2":
            return ["--gui"]
        elif choice == "3":
            return ["--stats"]
        elif choice == "4":
            return ["--optimize"]
        elif choice == "5":
            return ["--test-1m"]
        else:
            return ["--gui"]
    else:
        print("📝 Mode Standard uniquement")
        return ["--gui"]

if __name__ == "__main__":
    
    # Si aucun argument, mode interactif
    if len(sys.argv) == 1:
        fake_args = interactive_mode()
        sys.argv.extend(fake_args)
    
    # Lancement
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Arrêt de l'application")
    except Exception as e:
        print(f"❌ Erreur fatale: {e}")
        sys.exit(1)
