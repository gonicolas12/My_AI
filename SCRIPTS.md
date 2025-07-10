# 🚀 Fichiers de lancement - My AI Assistant

## 📋 Fichiers essentiels (seulement 2 !)

### `setup.bat` - Installation initiale
**Utilisation :** Double-cliquez pour installer
- Vérifie Python
- Propose environnement virtuel ou installation globale
- Installe toutes les dépendances
- Teste l'installation

### `launch.bat` - Lanceur principal  
**Utilisation :** Double-cliquez pour utiliser l'IA
- Menu interactif
- Lance GUI, CLI, demo, ou diagnostic
- Gère automatiquement les dépendances
- Fonctionne avec ou sans environnement virtuel

## 🎯 Workflow recommandé

```
1. Première fois : Double-cliquez setup.bat
2. Usage quotidien : Double-cliquez launch.bat
```

## 📁 Autres fichiers (optionnels)

- `test_quick.bat` - Tests rapides de développement
- `diagnostic.py` - Diagnostic Python détaillé  
- `launcher.py` - Script Python principal
- `*.sh` - Versions Linux/macOS des scripts

## 🔄 Migration depuis les anciens scripts

Anciens fichiers → Nouveau fichier :
- `install.bat` → `setup.bat`
- `install_simple.bat` → `setup.bat` 
- `start.bat` → `launch.bat`
- `run.bat` → `launch.bat`

## 💡 Utilisation directe (sans .bat)

```bash
# Installation
python -m pip install --user -r requirements.txt

# Lancement
python launcher.py gui      # Interface graphique
python launcher.py cli      # Interface ligne de commande  
python launcher.py demo     # Démonstration
python launcher.py status   # Statut système
```

---

**🎯 Objectif : 2 fichiers maximum pour une utilisation simple !**
