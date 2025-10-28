#!/usr/bin/env python3
"""
🚀 MY PERSONAL AI - LAUNCHER UNIFIÉ v5.6.0
Lance l'interface avec CustomAI unifié (support 1M tokens intégré)
"""

import sys
from pathlib import Path

from interfaces.gui_modern import ModernAIGUI

# Ajouter le répertoire parent au chemin
sys.path.insert(0, str(Path(__file__).parent))

def main():
    """Point d'entrée principal"""
    print("\n🚀 MY PERSONAL AI LAUNCHER UNIFIÉ v5.6.0")
    print("=" * 50)
    print("   🧠 CustomAI avec support 1M tokens intégré")
    print("   🔧 Processeurs PDF, DOCX, Code avancés")
    print("   🎨 Interface moderne CustomTkinter")
    print("   📊 Mémoire conversationnelle intelligente")
    print("   🌐 Recherche internet intégrée")
    print("   ⚡ Architecture 100% locale")
    print()

    try:
        print("✅ Modules chargés avec succès")
        print("🚀 Lancement de l'interface...")
        print()

        # Lancer l'interface
        app = ModernAIGUI()
        app.run()

    except ImportError as e:
        print(f"❌ Erreur d'import: {e}")
        print()
        print("🔧 Solutions possibles:")
        print("   1. Installez les dépendances: pip install -r requirements.txt")
        print("   2. Vérifiez que tous les modules sont présents")
        print("   3. Utilisez: python main.py en fallback")
        sys.exit(1)

    except (RuntimeError, OSError, AttributeError) as e:
        print(f"❌ Erreur lors du lancement: {e}")
        print()
        print("🔧 Essayez le mode debug:")
        print(
            '   python -c "from interfaces.gui_modern import ModernAIGUI; ModernAIGUI().run()"'
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
