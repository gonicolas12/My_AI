# 🚀 Installation Ultra-Rapide - My AI Personal Assistant

## Installation en 1 commande

### Windows
```bash
# Téléchargez le projet et exécutez :
install_simple.bat
```

### Linux/macOS
```bash
# Téléchargez le projet et exécutez :
chmod +x install_simple.sh
./install_simple.sh
```

## Ou installation manuelle (30 secondes)

### 1. Clonez le dépôt
```bash
git clone [votre-repo-url]
cd My_AI
```

### 2. Installez les dépendances
```bash
# Windows
pip install --user -r requirements.txt

# Linux/macOS
pip3 install --user -r requirements.txt
```

### 3. Lancez l'assistant
```bash
# Interface graphique
python launcher.py gui

# Interface ligne de commande
python launcher.py cli

# Démonstration
python launcher.py demo
```

## ✨ Fonctionnalités principales

- **💬 Chat IA** : Conversation naturelle avec l'IA
- **📄 Traitement PDF** : Extraction et résumé de documents
- **📝 Traitement DOCX** : Analyse de documents Word
- **💻 Code** : Génération et analyse de code
- **🖥️ Interface** : CLI et GUI disponibles

## 🔧 Configuration (optionnelle)

### Pour une meilleure IA (recommandé)
```bash
# Installez Ollama depuis: https://ollama.ai/
# Puis :
ollama pull llama3.2
```

### Configuration personnalisée
Éditez `config.yaml` pour personnaliser :
- Modèle IA à utiliser
- Paramètres d'interface
- Limites de traitement

## 📋 Commandes utiles

```bash
# Vérifier le statut
python launcher.py status

# Tests
python launcher.py test

# Diagnostic complet
python diagnostic.py

# Aide
python launcher.py --help
```

## 🆘 Problèmes courants

### "Module not found"
```bash
pip install --user click pyyaml rich transformers torch
```

### "Defaulting to user installation..."
C'est normal ! Les packages sont installés dans votre dossier utilisateur.

### Interface graphique ne fonctionne pas
```bash
# Utilisez la CLI à la place
python launcher.py cli
```

### Problèmes de modèles IA
1. Installez Ollama : https://ollama.ai/
2. Ou les modèles se téléchargeront automatiquement

## 📚 Documentation complète

- `QUICKSTART.md` - Guide de démarrage rapide
- `docs/` - Documentation technique complète
- `examples/` - Exemples d'utilisation

## 🎯 Utilisation typique

```bash
# Démarrage rapide
python launcher.py gui

# Traiter un document
python launcher.py cli process-file document.pdf

# Générer du code
python launcher.py cli generate-function "calculer fibonacci"

# Chat simple
python launcher.py cli chat "Bonjour IA !"
```

---

**🚀 Prêt en moins d'une minute !** L'installation se fait entièrement sans environnement virtuel pour une simplicité maximale.
