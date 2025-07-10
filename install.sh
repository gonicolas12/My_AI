#!/bin/bash

# ====================================
# Script d'installation My Personal AI
# ====================================

# Couleurs pour les messages
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Fonction pour afficher les messages
print_status() {
    echo -e "${BLUE}🔍 $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️ $1${NC}"
}

# Bannière
echo -e "${BLUE}"
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║                 🤖 MY PERSONAL AI - INSTALLATION 🤖          ║"
echo "║                                                              ║"
echo "║                 Script d'installation automatique           ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Vérification de Python
print_status "Vérification de Python..."
if ! command -v python3 &> /dev/null; then
    if ! command -v python &> /dev/null; then
        print_error "Python n'est pas installé"
        echo "💡 Installez Python depuis: https://python.org"
        echo "   ou utilisez votre gestionnaire de paquets:"
        echo "   - Ubuntu/Debian: sudo apt install python3 python3-pip python3-venv"
        echo "   - macOS: brew install python"
        echo "   - CentOS/RHEL: sudo yum install python3 python3-pip"
        exit 1
    else
        PYTHON_CMD="python"
    fi
else
    PYTHON_CMD="python3"
fi

$PYTHON_CMD --version
print_success "Python détecté"

# Vérification de pip
print_status "Vérification de pip..."
if ! $PYTHON_CMD -m pip --version &> /dev/null; then
    print_error "pip n'est pas disponible"
    echo "💡 Installez pip:"
    echo "   - Ubuntu/Debian: sudo apt install python3-pip"
    echo "   - macOS: pip est inclus avec Python"
    echo "   - CentOS/RHEL: sudo yum install python3-pip"
    exit 1
fi

print_success "pip disponible"

# Création de l'environnement virtuel
print_status "Création de l'environnement virtuel..."
if [ -d "venv" ]; then
    print_warning "Environnement virtuel existant détecté"
    read -p "Voulez-vous le recréer? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        rm -rf venv
        $PYTHON_CMD -m venv venv
    fi
else
    $PYTHON_CMD -m venv venv
fi

if [ $? -ne 0 ]; then
    print_error "Erreur lors de la création de l'environnement virtuel"
    exit 1
fi

print_success "Environnement virtuel créé"

# Activation de l'environnement virtuel
print_status "Activation de l'environnement virtuel..."
source venv/bin/activate

# Mise à jour de pip
print_status "Mise à jour de pip..."
pip install --upgrade pip

# Installation des dépendances
print_status "Installation des dépendances..."
echo "⏳ Cela peut prendre plusieurs minutes..."

pip install -r requirements.txt

if [ $? -ne 0 ]; then
    print_error "Erreur lors de l'installation des dépendances"
    echo "💡 Vérifiez votre connexion internet et requirements.txt"
    exit 1
fi

print_success "Dépendances installées avec succès"

# Création des répertoires
print_status "Création des répertoires nécessaires..."
mkdir -p outputs logs temp backups docs
print_success "Répertoires créés"

# Test de l'installation
print_status "Test de l'installation..."
if $PYTHON_CMD main.py status > /dev/null 2>&1; then
    print_success "Test initial réussi"
else
    print_warning "Le test initial a échoué, mais l'installation semble complète"
    echo "💡 Vous devrez peut-être installer un modèle LLM (voir documentation)"
fi

# Information sur Ollama
echo
echo -e "${YELLOW}🧠 CONFIGURATION DES MODÈLES LLM:${NC}"
echo
echo "Pour une utilisation optimale, installez Ollama:"
echo "1. Téléchargez depuis: https://ollama.ai/"
echo "2. Installez Ollama selon votre OS"
echo "3. Exécutez: ollama pull llama3.2"
echo
echo "Alternative: Les modèles Transformers seront téléchargés automatiquement"
echo

# Création du script de lancement
print_status "Création du script de lancement..."
cat > start_ai.sh << 'EOF'
#!/bin/bash
cd "$(dirname "$0")"
source venv/bin/activate
python main.py "$@"
EOF

chmod +x start_ai.sh
print_success "Script de lancement créé: start_ai.sh"

# Installation terminée
echo
echo -e "${GREEN}"
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║                    🎉 INSTALLATION TERMINÉE! 🎉             ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

echo "🚀 Pour lancer votre IA:"
echo "   • Exécutez: ./start_ai.sh"
echo "   • Ou tapez: source venv/bin/activate && python main.py"
echo
echo "📚 Documentation:"
echo "   • Guide d'installation: docs/INSTALLATION.md"
echo "   • Guide d'utilisation: docs/USAGE.md"
echo
echo "💡 Première utilisation:"
echo "   1. Lancez l'IA"
echo "   2. Tapez 'aide' pour voir les commandes"
echo "   3. Commencez à poser des questions!"
echo

# Proposition de lancement
read -p "Voulez-vous lancer l'IA maintenant? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo
    echo "🤖 Lancement de l'IA..."
    $PYTHON_CMD main.py
fi

echo
echo "👋 Installation terminée. Bon codage!"
