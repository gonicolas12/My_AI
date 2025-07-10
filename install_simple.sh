#!/bin/bash
# ====================================
# Installation rapide My Personal AI - Sans environnement virtuel
# ====================================

echo ""
echo "==============================================="
echo " MY PERSONAL AI - INSTALLATION RAPIDE"
echo " Installation directe sans environnement virtuel"
echo "==============================================="
echo ""

# Vérification de Python
echo "[INFO] Vérification de Python..."
if ! command -v python3 &> /dev/null && ! command -v python &> /dev/null; then
    echo "[ERROR] Python n'est pas installé"
    echo "[ASTUCE] Installez Python depuis votre gestionnaire de paquets"
    exit 1
fi

# Utiliser python3 si disponible, sinon python
if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
    PIP_CMD="pip3"
else
    PYTHON_CMD="python"
    PIP_CMD="pip"
fi

$PYTHON_CMD --version
echo "[OK] Python détecté"

# Vérification de pip
echo ""
echo "[INFO] Vérification de pip..."
if ! command -v $PIP_CMD &> /dev/null; then
    echo "[ERROR] pip n'est pas disponible"
    echo "[ASTUCE] Installez pip depuis votre gestionnaire de paquets"
    exit 1
fi

echo "[OK] pip disponible"

# Mise à jour de pip
echo ""
echo "[INFO] Mise à jour de pip..."
$PYTHON_CMD -m pip install --upgrade pip --user

# Installation des dépendances
echo ""
echo "[INFO] Installation des dépendances..."
echo "[INFO] Cela peut prendre plusieurs minutes..."
echo "[INFO] Les packages seront installés dans votre répertoire utilisateur"

$PIP_CMD install --user -r requirements.txt

if [ $? -ne 0 ]; then
    echo "[WARNING] Erreur lors de l'installation complète"
    echo "[INFO] Tentative d'installation des dépendances critiques..."
    $PIP_CMD install --user click pyyaml rich transformers torch PyMuPDF python-docx
    
    if [ $? -ne 0 ]; then
        echo "[ERROR] Impossible d'installer les dépendances critiques"
        echo "[ASTUCE] Vérifiez votre connexion internet"
        exit 1
    fi
    echo "[OK] Dépendances critiques installées"
else
    echo "[OK] Toutes les dépendances installées avec succès"
fi

# Création des répertoires
echo ""
echo "[INFO] Création des répertoires nécessaires..."
mkdir -p outputs logs temp backups
echo "[OK] Répertoires créés"

# Test de l'installation
echo ""
echo "[INFO] Test de l'installation..."
$PYTHON_CMD launcher.py status > /dev/null 2>&1
if [ $? -ne 0 ]; then
    echo "[WARNING] Le test initial a échoué"
    echo "[INFO] Tentative de test des modules critiques..."
    $PYTHON_CMD -c "import click, yaml, rich; print('[OK] Modules critiques disponibles')"
    if [ $? -ne 0 ]; then
        echo "[ERROR] Modules critiques non disponibles"
        exit 1
    fi
    echo "[OK] Modules critiques fonctionnels"
else
    echo "[OK] Test initial réussi"
fi

# Information sur Ollama
echo ""
echo "[INFO] CONFIGURATION OPTIONNELLE DES MODÈLES LLM:"
echo ""
echo "Pour une utilisation optimale, installez Ollama:"
echo "1. Téléchargez depuis: https://ollama.ai/"
echo "2. Installez Ollama"
echo "3. Exécutez: ollama pull llama3.2"
echo ""
echo "Alternative: Les modèles Transformers seront téléchargés automatiquement"
echo ""

# Création du script de lancement
echo ""
echo "[INFO] Création du script de lancement..."
cat > start_ai.sh << 'EOF'
#!/bin/bash
echo "[INFO] Lancement de My Personal AI..."
if command -v python3 &> /dev/null; then
    python3 launcher.py gui
else
    python launcher.py gui
fi
if [ $? -ne 0 ]; then
    echo "[ERROR] Erreur de lancement"
    echo "[ASTUCE] Essayez: python launcher.py cli"
    read -p "Appuyez sur Entrée pour continuer..."
fi
EOF

chmod +x start_ai.sh
echo "[OK] Script de lancement créé: start_ai.sh"

echo ""
echo "==============================================="
echo " INSTALLATION TERMINÉE!"
echo "==============================================="
echo ""
echo "[INFO] Pour lancer votre IA:"
echo "   - Exécutez: ./start_ai.sh"
echo "   - Ou tapez: python launcher.py gui"
echo "   - Ou tapez: python launcher.py cli"
echo ""
echo "[INFO] Documentation:"
echo "   - Guide rapide: QUICKSTART.md"
echo "   - Documentation complète: docs/"
echo ""
echo "[INFO] Première utilisation:"
echo "   1. Lancez: python launcher.py gui"
echo "   2. Ou testez: python launcher.py demo"
echo "   3. Commencez à poser des questions!"
echo ""
echo "[INFO] Note: Les packages sont installés dans votre répertoire utilisateur"
echo "[INFO] C'est normal si vous voyez des messages d'installation utilisateur"
echo ""

read -p "Voulez-vous lancer l'IA maintenant? (y/N): " choice
if [[ $choice =~ ^[Yy]$ ]]; then
    echo ""
    echo "[INFO] Lancement de l'IA..."
    $PYTHON_CMD launcher.py gui
fi

echo ""
echo "[INFO] Installation terminée. Bon codage!"
