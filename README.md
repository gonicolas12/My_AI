# 🤖 Une IA personnelle **hybride locale/internet**, capable de :

- 💬 Conversations intelligentes avec reconnaissance d'intentions avancée
- 🧠 Mémoire conversationnelle persistante et contextuelle
- 📄 Traitement complet des documents PDF et DOCX
- 💻 Analyse, génération et débogage de code
- 🌐 Recherche internet intelligente avec résumés automatiques
- 🔍 Distinction automatique entre questions techniques, documents et conversations générales
- 🖥️ Interface graphique moderne et intuitive
- 🔧 Fonctionnement local avec recherche internet - IA 100% Locale

## 🏗️ Architecture Modulaire

```
my_ai/
├── core/                    # Cœur de l'IA
│   ├── __init__.py
│   ├── ai_engine.py        # Moteur principal IA
│   ├── conversation.py     # Gestion des conversations
│   └── config.py          # Configuration globale
├── models/                 # Modèles d'IA locaux avancés
│   ├── __init__.py
│   ├── custom_ai_model.py # Modèle IA principal avec intentions
│   ├── conversation_memory.py # Mémoire conversationnelle avancée
│   ├── base_ai.py         # Interface de base
│   ├── linguistic_patterns.py # Reconnaissance d'intentions et patterns
│   ├── knowledge_base.py  # Base de connaissances locale
│   ├── reasoning_engine.py # Moteur de raisonnement logique
│   └── internet_search.py # Moteur de recherche internet
├── processors/            # Processeurs de fichiers
│   ├── __init__.py
│   ├── pdf_processor.py   # Traitement PDF
│   ├── docx_processor.py  # Traitement DOCX
│   └── code_processor.py  # Traitement de code
├── generators/            # Générateurs de contenu
│   ├── __init__.py
│   ├── document_generator.py # Génération docs
│   ├── code_generator.py    # Génération code
│   └── report_generator.py  # Génération rapports
├── interfaces/            # Interfaces utilisateur
│   ├── __init__.py
│   ├── cli.py            # Interface ligne de commande
│   ├── gui.py            # Interface graphique
│   └── vscode_extension.py # Extension VS Code
├── utils/                 # Utilitaires
│   ├── __init__.py
│   ├── file_manager.py   # Gestion fichiers
│   ├── logger.py         # Logging
│   └── validators.py     # Validation
├── tests/                # Tests unitaires
├── docs/                 # Documentation
├── examples/             # Exemples d'utilisation
├── main.py              # Point d'entrée principal
├── requirements.txt     # Dépendances
└── config.yaml         # Configuration
```

## 🚀 Fonctionnalités Principales

### 🧠 IA Locale Avancée
- **Reconnaissance d'intentions** : Différencie automatiquement salutations, questions techniques, demandes sur documents
- **Mémoire contextuelle** : Se souvient des documents traités et du code analysé
- **Réponses adaptatives** : Format et contenu adaptés au type de question
- **Apprentissage local** : Amélioration continue sans données externes

### 🌐 Recherche Internet Intelligente (v2.3.0)
- **Recherche web** : Accès aux informations en temps réel via DuckDuckGo
- **Résumés automatiques** : Synthèse intelligente des résultats de recherche
- **Extraction de contenu** : Analyse des pages web avec BeautifulSoup
- **Traitement parallèle** : Analyse simultanée de plusieurs sources
- **Réponses contextuelles** : Adaptation du format selon le type de recherche

### 💬 Interaction Intelligente
- **Salutations naturelles** : Reconnaît "slt", "salut", "bonjour", "bjr", etc.
- **Questions techniques** : Spécialisé dans l'aide au code et développement
- **Analyse de documents** : Traitement et résumé de PDF/DOCX avec mémoire
- **Conversations contextuelles** : Référence aux éléments précédemment traités
- **Recherche internet** : "Cherche sur internet les actualités Python"

### 🖥️ Interface Utilisateur
- **GUI moderne** : Interface graphique intuitive avec gestion de l'historique
- **CLI avancée** : Ligne de commande pour utilisateurs experts
- **Gestion d'erreurs** : Messages clairs et récupération gracieuse
- **Bouton Clear Chat** : Remise à zéro complète de la conversation

## 🛠️ Technologies Locales

### Moteur IA 100% Local
- **Modèle customisé** : Aucune dépendance à OpenAI, Claude ou autres APIs
- **Patterns linguistiques** : Reconnaissance avancée des intentions utilisateur
- **Base de connaissances** : Stockage local des informations et contextes

### Traitement de Documents
- **PyPDF2/PyMuPDF** : Extraction complète de texte PDF
- **python-docx** : Traitement avancé DOCX avec conservation de la structure
- **Mémoire documentaire** : Stockage et référencement des contenus traités

### Interface Utilisateur
- **Tkinter** : GUI native Python multiplateforme
- **Click** : CLI avancée avec commandes contextuelles
- **Logging intégré** : Suivi des opérations et débogage

## 🏃‍♂️ Démarrage Rapide

### Installation
```bash
# Installation des dépendances
pip install -r requirements.txt
```

### Lancement
```bash
# Lancement avec script batch (recommandé)
.\launch.bat
# Puis sélectionnez l'option 1 (Interface Graphique)
```

### Premiers Pas
1. **Saluer l'IA** : "Salut", "Bonjour", "slt" - L'IA reconnaîtra votre salutation
2. **Poser une question technique** : "Comment créer une liste en Python ?"
3. **Analyser un document** : Glissez un fichier PDF/DOCX, puis "résume ce document"
4. **Vider le chat** : Utilisez le bouton "Clear Chat" pour recommencer

### Exemples d'Usage
```
🤖 Vous : slt
🤖 IA : Salut ! Comment puis-je t'aider aujourd'hui ?

🤖 Vous : Comment déboguer du code Python ?
🤖 IA : [Réponse technique détaillée sur le débogage Python]

🤖 Vous : résume le pdf
🤖 IA : [Résumé du document PDF précédemment chargé]

🤖 Vous : cherche sur internet les actualités Python
🤖 IA : [Recherche et résumé des dernières actualités Python]

🤖 Vous : trouve-moi des informations sur l'IA en 2025
🤖 IA : [Recherche et synthèse d'informations récentes sur l'IA]
```

## 📖 Documentation Complète

- **[Architecture](docs/ARCHITECTURE.md)** : Structure technique détaillée
- **[Installation](docs/INSTALLATION.md)** : Guide d'installation complet
- **[Usage](docs/USAGE.md)** : Exemples d'utilisation et workflows
- **[Exemples](examples/)** : Scripts d'exemple et cas d'usage

## 🔧 Caractéristiques Techniques

- **Hybride Local/Internet** : IA locale avec recherche internet optionnelle
- **Multiplateforme** : Windows, macOS, Linux
- **Léger** : Fonctionnement optimal sur machines modestes
- **Extensible** : Architecture modulaire pour ajouts futurs
- **Sécurisé** : Données locales protégées, recherche internet anonyme
- **Smart Search** : Moteur de recherche DuckDuckGo avec résumés intelligents

## 🚀 Évolutions Futures

- 🌐 Application Web
- 📊 Amélioration interface
- 🤖 Support de modèles LLM externes optionnels
