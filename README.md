# 🤖 Une IA personnelle, capable de :

- 💬 **Conversations intelligentes** avec reconnaissance d'intentions avancée
- 🧠 **Mémoire conversationnelle** persistante et contextuelle
- 📄 **Traitement complet** des documents **PDF** et **DOCX**
- 💻 **Analyse**, **génération** et **débogage** de **code**
- 🌐 **Recherche internet intelligente** avec résumés automatiques
- 🔍 **Distinction automatique** entre questions techniques, documents et conversations générales
- 🎨 **Interface graphique moderne style Claude** avec bulles de chat optimisées
- ✨ **Formatage de texte avancé** avec support **gras** Unicode
- 🔧 **Fonctionnement 100% Locale**

## 🏗️ Architecture Modulaire & FAQ Thématique

```
my_ai/
├── core/                      # Cœur de l'IA
│   ├── __init__.py
│   ├── ai_engine.py           # Moteur principal IA
│   ├── conversation.py        # Gestion des conversations
│   └── config.py              # Configuration globale
├── models/                    # Modèles d'IA locaux avancés
│   ├── __init__.py
│   ├── custom_ai_model.py     # Modèle IA principal avec intentions
│   ├── conversation_memory.py # Mémoire conversationnelle avancée
│   ├── base_ai.py             # Interface de base
│   ├── linguistic_patterns.py # Reconnaissance d'intentions et patterns
│   ├── knowledge_base.py      # Base de connaissances locale
│   ├── reasoning_engine.py    # Moteur de raisonnement logique
│   └── internet_search.py     # Moteur de recherche internet
├── processors/                # Processeurs de fichiers
│   ├── __init__.py
│   ├── pdf_processor.py       # Traitement PDF
│   ├── docx_processor.py      # Traitement DOCX
│   └── code_processor.py      # Traitement de code
├── generators/                # Générateurs de contenu
│   ├── __init__.py
│   ├── document_generator.py  # Génération docs
│   ├── code_generator.py      # Génération code
│   └── report_generator.py    # Génération rapports
├── interfaces/                # Interfaces utilisateur
│   ├── __init__.py
│   ├── cli.py                 # Interface ligne de commande
│   ├── gui.py                 # Interface graphique basique
│   ├── gui_modern.py          # Interface graphique moderne style Claude
│   ├── gui_simple.py          # Interface graphique simplifiée
│   ├── modern_styles.py       # Styles et thèmes modernes
│   └── vscode_extension.py    # Extension VS Code
├── utils/                     # Utilitaires
│   ├── __init__.py
│   ├── file_manager.py        # Gestion fichiers
│   ├── logger.py              # Logging
│   └── validators.py          # Validation
├── data/                      # Données d'enrichissement FAQ
│   └── enrichissement/        # Exemples thématiques
├── tests/                     # Tests unitaires
├── docs/                      # Documentation
├── examples/                  # Exemples d'utilisation
├── main.py                    # Point d'entrée principal
├── requirements.txt           # Dépendances
├── launch.bat                 # Script pour lancer le programme
├── clean_project.bat          # Script pour supprimer les fichiers temporaires
└── config.yaml                # Configuration
```

## 🚀 Fonctionnalités Principales

### 📚 FAQ Thématique Prioritaire
- **Organisation par thèmes** : Placez vos fichiers d’enrichissement dans `data/` (ex : `enrichissement_culture.jsonl`, `enrichissement_informatique.jsonl`, etc.)
- **Chargement automatique** : Toutes les questions/réponses sont fusionnées et accessibles instantanément
- **Matching prioritaire** : La FAQ répond avant tout autre modèle
- **Personnalisation** : Ajoutez, modifiez ou supprimez des fichiers à la volée

### 🧠 IA Locale Avancée
- **Reconnaissance d'intentions** : Différencie automatiquement salutations, questions techniques, demandes sur documents
- **Mémoire contextuelle** : Se souvient des documents traités et du code analysé
- **Réponses adaptatives** : Format et contenu adaptés au type de question
- **Apprentissage local** : Amélioration continue sans données externes

### 🌐 Recherche Internet Intelligente
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

### 🖥️ Interface Utilisateur Moderne (v3.0.0)

#### 🎨 Interface Graphique Style Claude
- **Design moderne** : Interface sombre élégante avec bulles de chat optimisées
- **Messages adaptatifs** : Bulles utilisateur à droite, réponses IA sans bulle
- **Drag & Drop** : Glisser-déposer direct de fichiers PDF, DOCX et code
- **Formatage avancé** : Support complet du **texte en gras** avec Unicode
- **Animations fluides** : Indicateurs de réflexion et recherche internet
- **Responsive design** : Adaptation automatique à tous types d'écrans

#### 🖱️ Fonctionnalités Interactives
- **Raccourcis clavier** : Entrée (envoyer), Shift+Entrée (nouvelle ligne), Ctrl+L (clear)
- **Boutons d'action** : Clear Chat, Aide, chargement de fichiers spécialisés
- **Messages non-scrollables** : Labels optimisés pour de meilleures performances
- **Timestamp automatique** : Horodatage discret pour chaque message

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
- **Tkinter + CustomTkinter** : GUI native moderne avec thèmes sombres
- **Drag & Drop** : Support natif avec tkinterdnd2
- **Click** : CLI avancée avec commandes contextuelles
- **Styles adaptatifs** : Polices et couleurs optimisées par OS
- **Logging intégré** : Suivi des opérations et débogage

## 🏃‍♂️ Démarrage Rapide

### Clonez ce dépôt
```bash
git clone https://github.com/gonicolas12/My_AI
cd My_AI
```

### Installation
##### Installation des dépendances
```bash
pip install -r requirements.txt
```

### Lancement
##### Lancement avec script batch (recommandé)
```bash
.\launch.bat
```
Sélectionnez **l'option 1 (Interface Graphique)**, puis patientez...

### Premiers Pas
1. **Saluer l'IA** : "Salut", "Bonjour", "slt" - L'IA reconnaîtra votre salutation
2. **Poser une question technique** : "Comment créer une liste en Python ?"
3. **Analyser un document** : Importez un fichier PDF/DOCX, puis "résume ce document"
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
- **[Changelog](CHANGELOG.md)** : Historique des mises à jour

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
