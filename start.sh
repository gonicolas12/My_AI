#!/bin/bash
# ====================================
# Lanceur My Personal AI avec activation automatique
# ====================================

echo ""
echo "🤖 My Personal AI - Lanceur"
echo ""

# Vérifier si l'environnement virtuel existe
if [ -f "venv/bin/activate" ]; then
    echo "🔄 Activation de l'environnement virtuel..."
    source venv/bin/activate
    echo "✅ Environnement virtuel activé"
elif [ -f "ai_env/bin/activate" ]; then
    echo "🔄 Activation de l'environnement virtuel..."
    source ai_env/bin/activate
    echo "✅ Environnement virtuel activé"
else
    echo "⚠️ Aucun environnement virtuel trouvé"
    echo "💡 Utilisation de l'installation Python globale"
    echo ""
    echo "Si vous rencontrez des problèmes:"
    echo "1. Exécutez: bash install.sh"
    echo "2. Ou créez un environnement virtuel manuellement:"
    echo "   python -m venv ai_env"
    echo "   source ai_env/bin/activate"
    echo "   pip install -r requirements.txt"
    echo ""
fi

echo ""
echo "🚀 Lancement de l'interface graphique..."
python launcher.py gui

if [ $? -ne 0 ]; then
    echo ""
    echo "❌ Erreur lors du lancement"
    echo "💡 Essayez:"
    echo "  python launcher.py status    (pour vérifier le statut)"
    echo "  python launcher.py demo      (pour tester)"
    echo "  python launcher.py cli       (interface ligne de commande)"
    echo ""
    read -p "Appuyez sur Entrée pour continuer..."
fi
