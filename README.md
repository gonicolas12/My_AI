# 🤖 Une IA personnelle, confidentielle et locale

- 🧠 **Contexte Ultra-Étendu** : **1,048,576 tokens RÉELS** pour des conversations et analyses approfondies
- 🗜️ **Compression Intelligente** : Ratio de compression 2.4:1 à 52:1 selon le contenu
- 💬 **Conversations intelligentes** avec reconnaissance d'intentions avancée et mémoire persistante
- 📄 **Traitement complet** des documents **PDF** et **DOCX** avec analyse contextuelle ultra-étendue
- 💻 **Analyse**, **génération (via [clé API GitHub](#-utilisation-de-la-clé-api-github))** et **débogage** de **code** avec contexte massif
- 🌐 **Recherche internet intelligente** avec résumés automatiques et intégration contextuelle
- 🔍 **Distinction automatique** entre questions techniques, documents et conversations générales
- 🎨 **Interface graphique moderne style Claude** avec bulles de chat optimisées
- ✨ **Formatage de texte avancé** avec support **gras** Unicode et blocs de code Python colorisés
- 🏗️ **Architecture 100% Locale** avec persistance SQLite optimisée
- ⚡ **Gestion automatique de la mémoire** et optimisations en temps réel

## 🏗️ Architecture Ultra 1M Tokens & FAQ Thématique

### 💥 Capacités Révolutionnaires

- **1,048,576 tokens de contexte réel** (contre 4K-8K traditionnels)
- **Compression intelligente multi-niveaux** : texte, code, documents
- **Recherche sémantique ultra-rapide** avec TF-IDF et similarité cosinus
- **Chunking intelligent** avec détection automatique de blocs logiques
- **Auto-optimisation** de la mémoire selon l'usage

```
my_ai/
├── core/                                # Cœur de l'IA
│   ├── __init__.py
│   ├── ai_engine.py                     # Moteur principal IA
│   ├── conversation.py                  # Gestion des conversations
│   ├── context_manager.py               # Gestionnaire de contexte standard
│   └── config.py                        # Configuration globale
├── models/                              # Modèles d'IA Ultra avec 1M tokens
│   ├── __init__.py
│   ├── ultra_custom_ai.py               # Modèle ULTRA
│   ├── intelligent_context_manager.py   # Gestionnaire contexte intelligent
│   ├── million_token_context_manager.py # Persistance 1M tokens
│   ├── custom_ai_model.py               # Modèle IA principal avec intentions
│   ├── conversation_memory.py           # Mémoire conversationnelle avancée
│   ├── base_ai.py                       # Interface de base
│   ├── linguistic_patterns.py           # Reconnaissance d'intentions et patterns
│   ├── knowledge_base.py                # Base de connaissances locale
│   ├── reasoning_engine.py              # Moteur de raisonnement logique
│   ├── ml_faq_model.py                  # FAQ avec ML et fuzzy matching
│   └── internet_search.py               # Moteur de recherche internet
├── processors/                          # Processeurs de fichiers Ultra
│   ├── __init__.py
│   ├── pdf_processor.py                 # Traitement PDF avec chunking intelligent
│   ├── docx_processor.py                # Traitement DOCX avec compression
│   ├── code_processor.py                # Traitement de code avec analyse sémantique
│   └── file_processor.py                # Processeur unifié
├── generators/                          # Générateurs de contenu
│   ├── __init__.py
│   ├── document_generator.py            # Génération docs avec contexte étendu
│   ├── code_generator.py                # Génération code avec analyse ultra
│   └── report_generator.py              # Génération rapports détaillés
├── interfaces/                          # Interfaces utilisateur Ultra
│   ├── __init__.py
│   ├── cli.py                           # Interface ligne de commande
│   ├── gui.py                           # Interface graphique basique
│   ├── gui_modern.py                    # Interface moderne
│   ├── gui_simple.py                    # Interface graphique simplifiée
│   ├── modern_styles.py                 # Styles et thèmes modernes
│   └── vscode_extension.py              # Extension VS Code
├── utils/                               # Utilitaires Ultra
│   ├── __init__.py
│   ├── file_manager.py                  # Gestion fichiers
│   ├── logger.py                        # Logging
│   └── validators.py                    # Validation
├── data/                                # Données d'enrichissement FAQ
│   └── enrichissement/                  # Exemples thématiques
├── tests/                               # Tests unitaires
├── docs/                                # Documentation
├── examples/                            # Exemples d'utilisation
├── main.py                              # Point d'entrée principal
├── requirements.txt                     # Dépendances
├── launch.bat                           # Script pour lancer le programme
├── clean_project.bat                    # Script pour supprimer les fichiers temporaires
└── config.yaml                          # Configuration
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

### 🖥️ Interface Utilisateur Moderne
#### 🎨 Interface Graphique Style [Claude](https://claude.ai/new)
- **Design moderne** : Interface sombre élégante avec bulles de chat optimisées
- **Messages adaptatifs** : Bulles utilisateur à droite, réponses IA sans bulle
- **Formatage avancé** : Support complet du **texte en gras** avec Unicode
- **Animations fluides** : Indicateurs de réflexion et recherche internet
- **Responsive design** : Adaptation automatique à tous types d'écrans

#### 🖱️ Fonctionnalités Interactives
- **Raccourcis clavier** : Entrée (envoyer), Shift+Entrée (nouvelle ligne), Ctrl+L (clear)
- **Boutons d'action** : Clear Chat, Aide, chargement de fichiers spécialisés
- **Messages non-scrollables** : Labels optimisés pour de meilleures performances
- **Timestamp automatique** : Horodatage discret pour chaque message

#### 🖥️ Différentes Interfaces
- **GUI moderne** : Interface graphique intuitive avec gestion de l'historique
- **CLI avancée** : Ligne de commande pour utilisateurs experts
- **Gestion d'erreurs** : Messages clairs et récupération gracieuse

## 🔑 Utilisation de la clé API GitHub

Certaines **fonctionnalités** (**génération** de code, accès à **GitHub**, etc.) nécessitent une clé **API GitHub**. Pour que **votre IA** ai accès à **Github**, c'est simple :

### 1. Générer une clé API GitHub
1. **Rendez-vous** sur [github.com/settings/tokens](https://github.com/settings/tokens)
2. Cliquez sur **"Generate new token"** (classic ou fine-grained)
3. Donnez les **permissions nécessaires** (repo, user, etc.)
4. Copiez la **clé générée**

### 2. Configurer la clé API sur votre machine
Dans votre **terminal**, entrez :
```powershell
$env:GITHUB_TOKEN="votre_token_github"
```
Et voilà ! Votre **IA personnelle** aura accès à l'**API Github**.

### 3. Utilisation sans clé API
Si **aucune clé** n'est configurée, l'**IA** utilisera automatiquement le **backend local**. Les fonctionnalités dépendantes de **GitHub** seront **désactivées**.

---
N'hésitez pas à consulter le fichier `config.yaml` pour personnaliser les backends et modèles utilisés.

## 🛠️ Technologies Locales

### Moteur IA 100% Local
- **Modèle customisé** : Aucune dépendance à OpenAI, Claude, etc...
- **Patterns linguistiques** : Reconnaissance avancée des intentions utilisateur
- **Base de connaissances** : Stockage local des informations et contextes

### Traitement de Documents
- **PyPDF2/PyMuPDF** : Extraction complète de texte PDF
- **python-docx** : Traitement avancé DOCX avec conservation de la structure
- **Mémoire documentaire** : Stockage et référencement des contenus traités

### Interface Utilisateur
- **Tkinter + CustomTkinter** : GUI native moderne avec thèmes sombres
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

##### Nettoyage des fichiers temporaires
```bash
.\clean_project.bat
```
Si après avoir lancé plusieurs fois l'**IA** vous avez des **problèmes inexpliqués**, des **erreurs** ou des **comportements inattendus**, lancez ce **script** pour supprimer les **fichiers temporaires** générés par l'application (logs, caches, historiques, etc.). Cela permet de repartir sur une base **propre** avant de relancer l'**IA**.

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
- **[Recherche Internet](docs/INTERNET_SEARCH.md)** : Guide complet sur la recherche web
- **[Optimisation](docs/OPTIMIZATION.md)** : Conseils et techniques d'optimisation locale
- **[Ultra 1M Tokens](docs/ULTRA_1M_TOKENS.md)** : Détails sur la gestion du contexte étendu
- **[Usage](docs/USAGE.md)** : Exemples d'utilisation et workflows
- **[Changelog](CHANGELOG.md)** : Historique des mises à jour
- **[FAQ](docs/FAQ.md)** : Questions fréquentes et réponses détaillées
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
