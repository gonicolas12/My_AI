# 🤖 Une IA personnelle, confidentielle et locale

- 🧠 **Contexte Ultra-Étendu** pour des conversations et analyses approfondies
- 🗜️ **Compression Intelligente** : Ratio de compression 2.4:1 à 52:1 selon le contenu
- 💬 **Conversations intelligentes** avec reconnaissance d'intentions avancée et mémoire persistante
- 🤖 **Système d'Agents IA Spécialisés** : 9 agents experts pour des tâches complexes
- 📄 **Traitement complet** des documents **PDF** et **DOCX** avec analyse contextuelle ultra-étendue
- 🖼️ **Analyse d'images** avec modèles vision Ollama (llava, llama3.2-vision, etc.)
- 💻 **Analyse** et **génération** de **code** avec contexte massif
- 🌐 **Recherche internet intelligente** avec résumés automatiques et intégration contextuelle
- 🔍 **Distinction automatique** entre questions techniques, documents et conversations générales
- 🎨 **Interface graphique moderne style Claude** avec bulles de chat optimisées et onglets
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
│   ├── agent_orchestrator.py            # Orchestrateur d'agents
│   ├── ai_engine.py                     # Moteur principal IA
│   ├── config.py                        # Configuration de l'IA
│   ├── context_manager.py               # Gestion de contexte long
│   ├── conversation.py                  # Gestion des conversations
│   ├── data_preprocessing.py            # Prétraitement des données
│   ├── rlhf.py                          # Reinforcement Learning from Human Feedback
│   └── training_pipeline.py             # Pipeline d'entraînement local
├── data/                                # Données d'enrichissement FAQ
│   ├── enrichissement/                  # Exemples thématiques
│   └── data_collection.py               # Script de structuration des données
├── generators/                          # Générateurs de contenu
│   ├── __init__.py
│   ├── document_generator.py            # Génération docs avec contexte étendu
│   └── code_generator.py                # Génération code avec analyse ultra
├── interfaces/                          # Interfaces utilisateur Ultra
│   ├── __init__.py
│   ├── agents_interface.py              # Interface graphique Agents IA
│   ├── cli.py                           # Interface ligne de commande
│   ├── gui_modern.py                    # Interface moderne
│   ├── modern_styles.py                 # Styles et thèmes modernes
│   └── vscode_extension.py              # Extension VS Code
├── memory/                              # Mémoire vectorielle
│   ├── vector_store/chroma_db/          # Base de données ChromaDB
│   ├── __init__.py
│   └── vector_memory.py                 # Mémoire vectorielle avec ChromaDB
├── models/                              # Modèles d'IA Ultra avec 1M tokens
│   ├── mixins/                          # Mixins pour custom_ai_model
│   ├── weights/                         # Poids de modèles entraînés localement
│   ├── __init__.py
│   ├── advanced_code_generator.py       # Générateur de code avancé
│   ├── ai_agents.py                     # Agents IA spécialisés
│   ├── base_ai.py                       # Interface de base
│   ├── conversation_memory.py           # Mémoire conversationnelle avancée
│   ├── custom_ai_model.py               # Modèle IA principal avec intentions
│   ├── intelligent_code_orchestrator.py # Orchestrateur pour la génération de code
│   ├── intelligent_document_analyzer.py # Analyseur de documents intelligent
│   ├── internet_search.py               # Moteur de recherche internet
│   ├── knowledge_base.py                # Base de connaissances locale
│   ├── linguistic_patterns.py           # Reconnaissance d'intentions et patterns
│   ├── local_llm.py                     # Gestionnaire Ollama (détection + fallback)
│   ├── ml_faq_model.py                  # FAQ avec ML et fuzzy matching
│   ├── real_web_code_generator.py       # Générateur de Code Basé sur Recherche Web Pure
│   ├── reasoning_engine.py              # Moteur de raisonnement logique
│   ├── smart_code_searcher.py           # Recherche de code intelligente
│   ├── smart_web_searcher.py            # Système de Recherche Web Intelligent pour Code
│   └── ultra_custom_ai.py               # Modèle ULTRA
├── outputs/                             # Fichiers générées par l'IA
├── processors/                          # Processeurs de fichiers Ultra
│   ├── __init__.py
│   ├── pdf_processor.py                 # Traitement PDF avec chunking intelligent
│   ├── docx_processor.py                # Traitement DOCX avec compression
│   └── code_processor.py                # Traitement de code avec analyse sémantique
├── utils/                               # Utilitaires Ultra
│   ├── __init__.py
│   ├── file_manager.py                  # Gestion fichiers
│   ├── file_processor.py                # Gestion traitement fichiers
│   ├── intelligent_calculator.py        # Calculateur intelligent
│   ├── logger.py                        # Logging
│   └── validators.py                    # Validation
├── tests/                               # Tests unitaires
├── docs/                                # Documentation
├── main.py                              # Point d'entrée principal
├── Modelfile                            # Configuration modèle Ollama
├── requirements.txt                     # Dépendances
├── launch.bat                           # Script pour lancer le programme
├── clean_project.bat                    # Script pour supprimer les fichiers temporaires
├── create_custom_model.bat              # Script pour créer un modèle personnalisé Ollama
└── config.yaml                          # Configuration
```

## 🖥️ Interface Utilisateur Moderne

### 🎨 Interface Graphique Style [Claude](https://claude.ai/new)
- **Design moderne** : Interface sombre élégante avec bulles de chat optimisées
- **Messages adaptatifs** : Bulles utilisateur à droite, réponses IA sans bulle
- **Formatage avancé** : Support complet du **texte en gras** avec Unicode
- **Animations fluides** : Indicateurs de réflexion et recherche internet
- **Responsive design** : Adaptation automatique à tous types d'écrans

### 🖱️ Fonctionnalités Interactives
- **Raccourcis clavier** : Entrée (envoyer), Shift+Entrée (nouvelle ligne), Ctrl+L (clear)
- **Boutons d'action** : Clear Chat, Aide, chargement de fichiers spécialisés
- **Messages non-scrollables** : Labels optimisés pour de meilleures performances
- **Timestamp automatique** : Horodatage discret pour chaque message

### 🖥️ Différentes Interfaces
- **GUI moderne** : Interface graphique intuitive avec gestion de l'historique
- **CLI avancée** : Ligne de commande pour utilisateurs experts
- **Gestion d'erreurs** : Messages clairs et récupération gracieuse

![Interface Chat](docs/images/chatScreen.png)

## 🚀 Fonctionnalités Principales

### 🤖 Système d'Agents IA Spécialisés
| Agent | Description |
|-------|-------------|
| 🐍 **CodeAgent** | Génération et debug de code multi-langages |
| 📚 **ResearchAgent** | Recherche et documentation technique |
| 📊 **AnalystAgent** | Analyse de données et insights |
| ✨ **CreativeAgent** | Rédaction et contenu créatif |
| 🐛 **DebugAgent** | Détection et correction d'erreurs |
| 📋 **PlannerAgent** | Planification de projets complexes |
| 🛡️ **SecurityAgent** | Audit de sécurité & vulnérabilités |
| ⚡ **OptimizerAgent** | Optimisation & Performance |
| 🧬 **DataScienceAgent** | Data Science & Machine Learning |

- **Workflows multi-agents** : Collaboration entre agents pour tâches complexes
- **Interface graphique dédiée** : Onglet "Agents" dans la GUI moderne
- **CLI enrichi** : Commandes `agent` et `workflow` disponibles

![Interface Agents](docs/images/agentsScreen.png)

### 🦙 Intégration Ollama (LLM Local)
- **LLM 100% local** : Réponses générées par llama3.2 directement sur votre machine
- **Confidentialité totale** : Aucune donnée n'est envoyée sur internet
- **Fallback intelligent** : Si Ollama n'est pas installé, l'IA utilise le mode patterns
- **Modèle personnalisable** : Configuration via `Modelfile` (température, contexte, system prompt)
- **Installation optionnelle** : L'application fonctionne avec ou sans Ollama

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

### Installation Ollama (Optionnel mais Recommandé)

Pour des réponses de qualité LLM, installez Ollama :

```bash
# 1. Télécharger depuis https://ollama.com/download
# 2. Installer le modèle texte (choisir selon votre RAM)
ollama pull llama3.2         # Modèle plus léger pour des réponses plus rapides (8 GB RAM)
# OU
ollama pull llama3.1:8b      # Modèle plus lourd pour des réponses plus détaillées (16 GB RAM)

# 3. [OPTIONNEL] Installer un modèle vision pour l'analyse d'images
ollama pull llava            # Modèle vision recommandé
# OU
ollama pull llama3.2-vision  # Alternative plus récente

# 4. Créer le modèle personnalisé
.\create_custom_model.bat

# Note : Adaptez la 3ème ligne du 'Modelfile' selon le modèle choisi (llama3.2 ou llama3.1:8b)
```

> **Sans Ollama**, l'IA fonctionne en mode fallback avec des patterns/règles.

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

## 🔑 Utilisation de la clé API GitHub

Si vous n'avez pas **[Ollama](#installation-ollama-optionnel-mais-recommandé)** d'installé, la **génération de code** nécessite une clé **API GitHub**. Pour que **votre IA** ai accès à **Github**, c'est simple :

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

N'hésitez pas à consulter le fichier `config.yaml` pour personnaliser les backends et modèles utilisés.

## 📖 Documentation Complète

- **[Architecture](docs/ARCHITECTURE.md)** : Structure technique détaillée
- **[Installation](docs/INSTALLATION.md)** : Guide d'installation complet
- **[Recherche Internet](docs/INTERNET_SEARCH.md)** : Guide complet sur la recherche web
- **[Optimisation](docs/OPTIMIZATION.md)** : Conseils et techniques d'optimisation locale
- **[Ultra 1M Tokens](docs/ULTRA_1M_TOKENS.md)** : Détails sur la gestion du contexte étendu
- **[Usage](docs/USAGE.md)** : Exemples d'utilisation et workflows
- **[Changelog](docs/CHANGELOG.md)** : Historique des mises à jour
- **[FAQ](docs/FAQ.md)** : Questions fréquentes et réponses détaillées
- **[Génération de Fichiers](docs/FILE_GENERATION.md)** : Guide sur la génération de fichiers via l'IA
- **[Agents IA](docs/AGENTS.md)** : Documentation complète sur les agents IA spécialisés

## 🔧 Caractéristiques Techniques

- **Hybride Local/Internet** : IA locale avec recherche internet optionnelle
- **Multiplateforme** : Windows, macOS, Linux
- **Léger** : Fonctionnement optimal sur machines modestes
- **Extensible** : Architecture modulaire pour ajouts futurs
- **Sécurisé** : Données locales protégées, recherche internet anonyme
- **Smart Search** : Moteur de recherche DuckDuckGo avec résumés intelligents

## 🚀 Évolutions Futures

- 📊 **Amélioration interface**
- 🌐 **Application Web**
- 💻 **Extension VS Code**
- 🧩 **Nouveaux agents spécialisés**
- 🔄 **Intégration avec d'autres LLM locaux**