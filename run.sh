#!/bin/bash
# ====================================
# One-Click Launcher - My Personal AI
# ====================================

echo "[INFO] My Personal AI - Lancement rapide..."

# Déterminer la commande Python
if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
    PIP_CMD="pip3"
else
    PYTHON_CMD="python"
    PIP_CMD="pip"
fi

# Installation rapide des dépendances si nécessaire
$PYTHON_CMD -c "import click" 2>/dev/null || $PIP_CMD install --user click
$PYTHON_CMD -c "import yaml" 2>/dev/null || $PIP_CMD install --user pyyaml
$PYTHON_CMD -c "import rich" 2>/dev/null || $PIP_CMD install --user rich

# Lancement
$PYTHON_CMD launcher.py gui

# En cas d'erreur, essayer la CLI
if [ $? -ne 0 ]; then
    echo "[INFO] Tentative avec l'interface CLI..."
    $PYTHON_CMD launcher.py cli
fi

# Si ça marche toujours pas, diagnostic
if [ $? -ne 0 ]; then
    echo "[ERROR] Problème détecté. Lancement du diagnostic..."
    $PYTHON_CMD diagnostic.py
    read -p "Appuyez sur Entrée pour continuer..."
fi
