# 🤖 My Personal AI v4.0.0 - IA 100% Locale (25 juillet 2025)

## 🚀 Nouveautés 4.0.0
- FAQ locale multi-fichiers thématiques : placez autant de fichiers `enrichissement*.jsonl` que vous voulez dans `data/` (par thème, domaine, etc.)
- Matching FAQ prioritaire et typo-tolérant (ajustable)
- Debug simplifié et logs épurés

> **Assistant IA personnel entièrement local - Prêt en 30 secondes !**

## 🚀 Démarrage Ultra-Rapide

### Windows
```bash
# Double-cliquez sur run.bat
# OU tapez dans un terminal :
run.bat
```

### Linux/macOS
```bash
chmod +x run.sh
./run.sh
```

### Commande universelle
```bash
# Marche partout :
python main.py
```

## ✨ Que fait cette IA Locale ?

- 📚 FAQ thématique prioritaire : toutes vos questions/réponses sont accessibles instantanément, organisées par fichiers thématiques

- **💬 Conversations intelligentes** : Reconnaît vos intentions (salutations, questions techniques, etc.)
- **📄 Analyse de documents** : Résume vos PDF/DOCX avec mémoire contextuelle
- **💻 Assistance au code** : Analyse, génère et explique le code Python
- **🧠 Mémoire persistante** : Se souvient de vos documents et conversations
- **🔒 100% privé** : Aucune donnée n'est envoyée à l'extérieur
- **🖥️ Interface** : CLI et GUI au choix

## 📋 Commandes de base

```bash
python launcher.py gui      # Interface graphique
python launcher.py cli      # Interface ligne de commande
python launcher.py demo     # Démonstration
python launcher.py status   # Vérifier le statut
```

## 🔧 Installation complète (optionnelle)

```bash
# Pour toutes les fonctionnalités :
pip install --user -r requirements.txt

# Ou utilisez le script :
install_simple.bat    # Windows
./install_simple.sh   # Linux/macOS
```

## 🧠 Modèles IA (optionnel)

### Ollama (recommandé)
```bash
# Installez depuis : https://ollama.ai/
ollama pull llama3.2
```

### Transformers (automatique)
Les modèles se téléchargent automatiquement

## 🆘 Problèmes ?

```bash
# Diagnostic automatique
python diagnostic.py

# Installation rapide
pip install --user click pyyaml rich transformers torch
```

## 📚 Documentation

- `INSTALL_SIMPLE.md` - Installation détaillée
- `QUICKSTART.md` - Guide de démarrage
- `docs/` - Documentation complète

---

**🎯 Objectif : Fonctionner immédiatement après clone du dépôt !**

*Si `python launcher.py gui` ne marche pas, le script `run.bat`/`run.sh` installe automatiquement les dépendances manquantes.*
