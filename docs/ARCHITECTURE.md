# 🏗️ Architecture - My Personal AI v5.6.0

## 📋 Vue d'Ensemble de l'Architecture

My Personal AI v5.6.0 est une **IA locale 100%** avec un système de contexte de **1 Million de tokens RÉEL**, basée sur les principes suivants:

- **Contexte Ultra-Étendu** : 1,048,576 tokens de contexte réel (vs 4K-8K standards)
- **Architecture 100% Locale** : Aucune dépendance cloud obligatoire, persistance locale
- **Compression Intelligente** : Multi-niveaux avec ratios de 2.4:1 à 52:1
- **Reconnaissance d'intentions avancée** : Analyse linguistique multi-niveaux
- **Mémoire conversationnelle persistante** : Stockage documents + contexte ML
- **Multi-sources d'information** : Code (StackOverflow, GitHub), web (DuckDuckGo)
- **RLHF intégré** : Pipeline complet d'amélioration continue
- **Modularité complète** : Composants indépendants avec fallbacks robustes

## 🚀 Architecture Système Complète

```
┌──────────────────────────────────────────────────────────────────────┐
│                    INTERFACES UTILISATEUR                            │
├──────────────────────────────────────────────────────────────────────┤
│  GUI Modern (CustomTkinter) │  CLI Enhanced    │  VSCode Extension   │
│  • Dark theme Claude-style  │  • Commandes     │  • (Prototype)      │
│  • Code highlighting        │  • Historique    │  • Command palette  │
│  • Drag-and-drop files      │  • Stats         │                     │
└──────────────────────────────────────────────────────────────────────┘
                                   │
┌──────────────────────────────────────────────────────────────────────┐
│                        MOTEUR IA CENTRAL                             │
├──────────────────────────────────────────────────────────────────────┤
│                          AIEngine (core/ai_engine.py)                │
│  • Orchestration de tous les modules                                 │
│  • Routage intelligent selon intentions                              │
│  • Gestion de session et contexte                                    │
│  • Intégration processeurs, générateurs, outils                      │
└──────────────────────────────────────────────────────────────────────┘
                                   │
┌──────────────────────────────────────────────────────────────────────┐
│                      MODÈLES IA ET INTELLIGENCE                      │
├──────────────────────────────────────────────────────────────────────┤
│  CustomAIModel (v5.6.0)     │  UltraCustomAI (1M tokens)             │
│  • Détection intentions     │  • Extend CustomAI                     │
│  • Réponses contextuelles   │  • Ultra-large context                 │
│  • Mémoire intégrée         │  • Advanced processors                 │
└──────────────────────────────────────────────────────────────────────┘
                                   │
┌──────────────────────────────────────────────────────────────────────┐
│                   GESTION DU CONTEXTE ET MÉMOIRE                     │
├─────────────────────────┬────────────────────────────────────────────┤
│ MillionTokenContextMgr  │ ConversationMemory                         │
│ • 1,048,576 tokens max  │ • Conversations persistantes               │
│ • Chunks 2048 tokens    │ • Documents stockés                        │
│ • Index sémantique      │ • Préférences utilisateur                  │
│ • Cleanup automatique   │ • Cache contexte récent                    │
│ • Persistance disque    │ • Format JSON enrichi                      │
└─────────────────────────┴────────────────────────────────────────────┘
                                   │
┌──────────────────────────────────────────────────────────────────────┐
│              RECONNAISSANCE ET ANALYSE LINGUISTIQUE                  │
├─────────────────────────┬────────────────────────────────────────────┤
│ LinguisticPatterns      │ ML FAQ Model                               │
│ • Détection salutations │ • TF-IDF matching                          │
│ • Mots-clés code        │ • Fuzzy matching (RapidFuzz)               │
│ • Questions types       │ • Enrichissement thématique:               │
│ • Tolérance typos       │   - Culture                                │
│                         │   - Informatique                           │
│                         │   - Général                                │
│                         │   - Exemples                               │
├─────────────────────────┴────────────────────────────────────────────┤
│ ReasoningEngine         │ KnowledgeBase                              │
│ • Opérateurs logiques   │ • Programmation (Python, web, data)        │
│ • Chaînes raisonnement  │ • Web dev (frontend, backend)              │
│ • Stratégies résolution │ • Mathématiques                            │
│                         │ • Sciences                                 │
│                         │ • Connaissances générales                  │
└──────────────────────────────────────────────────────────────────────┘
                                   │
┌──────────────────────────────────────────────────────────────────────┐
│                    PROCESSEURS DE DOCUMENTS                          │
├─────────────────────────┬────────────────────────────────────────────┤
│ PDFProcessor            │ DOCXProcessor                              │
│ • PyMuPDF (primaire)    │ • python-docx                              │
│ • PyPDF2 (fallback)     │ • Extraction paragraphes                   │
│ • Extraction metadata   │ • Tables                                   │
│ • Images                │ • Chunking intelligent                     │
│ • Chunking pages        │                                            │
├─────────────────────────┴────────────────────────────────────────────┤
│ CodeProcessor                                                        │
│ • Détection langage                                                  │
│ • Analyse structure (classes, fonctions)                             │
│ • Extraction commentaires                                            │
│ • Analyse sémantique                                                 │
└──────────────────────────────────────────────────────────────────────┘
                                   │
┌──────────────────────────────────────────────────────────────────────┐
│                    GÉNÉRATEURS DE CONTENU                            │
├─────────────────────────┬────────────────────────────────────────────┤
│ AdvancedCodeGenerator   │ DocumentGenerator                          │
│ • StackOverflow API     │ • Markdown                                 │
│ • GitHub search         │ • PDF (reportlab)                          │
│ • Web scraping          │ • Structured output                        │
│ • Templates fallback    │ • Context-aware                            │
│ • Semantic ranking      │                                            │
└──────────────────────────────────────────────────────────────────────┘
                                   │
┌──────────────────────────────────────────────────────────────────────┐
│                    OUTILS ET RECHERCHE WEB                           │
├─────────────────────────┬────────────────────────────────────────────┤
│ InternetSearchEngine    │ SmartWebSearcher                           │
│ • DuckDuckGo API        │ • Code search                              │
│ • Multi-thread (8)      │ • GitHub integration                       │
│ • Pattern extraction:   │ • Real-time patterns                       │
│   - Facts (taille,      │                                            │
│     population, dates)  │                                            │
│   - Définitions         │                                            │
│   - Prix                │                                            │
│ • Caching (3600s)       │                                            │
│ • BeautifulSoup scraping│                                            │
├─────────────────────────┴────────────────────────────────────────────┤
│ Local Tools: SearchTool, MathTool, InfoExtractionTool                │
└──────────────────────────────────────────────────────────────────────┘
                                   │
┌──────────────────────────────────────────────────────────────────────┐
│                RLHF ET AMÉLIORATION CONTINUE                         │
├─────────────────────────┬────────────────────────────────────────────┤
│ RLHF Pipeline           │ Feedback Integration                       │
│ • Dataset loading       │ • Merge feedback to training data          │
│ • Human feedback (0-5)  │ • Rating incorporation                     │
│ • Training loop         │ • Iterative retraining                     │
│ • Model export          │ • Quality metrics                          │
└──────────────────────────────────────────────────────────────────────┘
                                   │
┌──────────────────────────────────────────────────────────────────────┐
│              OPTIMISATION ET ÉVALUATION                              │
├─────────────────────────┬────────────────────────────────────────────┤
│ Optimization Module     │ Evaluation & Error Analysis                │
│ • Quantization          │ • Metrics (P/R/F1/EM)                      │
│ • Pruning               │ • Error tracking                           │
│ • Model export          │ • Performance analysis                     │
└──────────────────────────────────────────────────────────────────────┘
                                   │
┌──────────────────────────────────────────────────────────────────────┐
│                          UTILITAIRES                                 │
├──────────────────────────────────────────────────────────────────────┤
│  FileManager │ Logger │ Validators │ Config │ FileProcessor          │
└──────────────────────────────────────────────────────────────────────┘
```

## 📦 Structure Détaillée des Modules

### 🧠 Core - Cœur du Système

**`core/ai_engine.py`** - Orchestrateur central
```python
Responsabilités:
├─ Initialisation de tous les modules
├─ Routage des requêtes selon intentions
├─ Gestion de session (documents, code, historique)
├─ Coordination processeurs/générateurs
└─ Point d'entrée unique pour toutes les opérations
```

**`core/config.py`** - Configuration globale
```python
AI_CONFIG:
├─ Modèles par défaut
├─ Limites tokens (4096 standard, 1M ultra)
├─ Types de fichiers supportés
└─ Répertoires de travail

FILE_CONFIG:
├─ Taille maximale fichiers
├─ Répertoires temporaires/backups
└─ Extensions autorisées

UI_CONFIG:
├─ Thèmes CLI/GUI
└─ Prompts et messages
```

**`core/conversation.py`** - Gestion conversations
```python
ConversationManager:
├─ Historique dialogues (max 10 échanges)
├─ Sessions avec timestamps
├─ Synchronisation ConversationMemory
└─ Format échanges (input + response)
```

**`core/context_manager.py`** - Contexte basique
```python
Features:
├─ Fenêtre glissante (2048 tokens)
├─ Résumé automatique
├─ Persistance JSONL
└─ Base pour MillionTokenContextManager
```

**RLHF et Training**
```python
core/rlhf.py:
├─ Chargement datasets (JSONL/CSV)
├─ Collecte feedback humain (0-5)
├─ Boucle d'entraînement RLHF
└─ Export modèles optimisés

core/rlhf_feedback_integration.py:
├─ Fusion feedback dans training data
├─ Intégration ratings
└─ Préparation réentraînement itératif

core/training_pipeline.py:
├─ Chargement données diverses
├─ Préprocessing
└─ Pipeline d'entraînement

core/optimization.py:
├─ Quantization support
├─ Pruning
└─ Export optimisé

core/evaluation.py + error_analysis.py:
├─ Métriques (P/R/F1/exact match)
├─ Tracking erreurs
└─ Analyse qualité
```

### 🤖 Models - Intelligence Artificielle

**`models/custom_ai_model.py`** - Modèle IA principal (v5.6.0)
```python
Architecture:
├─ LinguisticPatterns (détection intentions)
├─ KnowledgeBase (domaines expertise)
├─ AdvancedCodeGenerator (multi-sources)
├─ ReasoningEngine (logique)
├─ ConversationMemory (persistance)
├─ InternetSearchEngine (DuckDuckGo)
├─ ML FAQ Model (TF-IDF)
├─ Processors (PDF, DOCX, Code)
└─ MillionTokenContextManager (1M tokens)

Capacités clés:
├─ Détection intentions avec confiance
├─ Tracking contexte session
├─ Mémoire conversationnelle
├─ Mode ultra 1M tokens
└─ Intégration processeurs avancés
```

**`models/ultra_custom_ai.py`** - Extension 1M tokens
```python
Features:
├─ Hérite de CustomAIModel
├─ Contexte ultra-large (1,048,576 tokens)
├─ Stockage et retrieval documents
├─ Processing par chunks
└─ Initialisation processeurs avancés
```

**`models/million_token_context_manager.py`** - Gestionnaire contexte
```python
Capacités:
├─ Max 1M tokens stockage
├─ Chunks 2048 tokens (configurable)
├─ Chunking intelligent avec overlap
├─ Index sémantique
├─ Cleanup automatique (capacité atteinte)
├─ Statistiques détaillées
└─ Persistance (context_storage/)

Méthodes principales:
├─ add_document(content, name) → deduplication
├─ search_context(query) → retrieval sémantique
├─ get_context_summary() → compression
└─ cleanup_old_chunks() → gestion mémoire
```

**`models/conversation_memory.py`** - Mémoire avancée
```python
Structure données:
{
  "conversations": [
    {
      "timestamp": float,
      "user_message": str,
      "ai_response": str,
      "intent": str,
      "confidence": float,
      "context": Dict
    }
  ],
  "stored_documents": {filename: content},
  "document_order": [chronological],
  "user_preferences": Dict,
  "context_cache": {topics, keywords}
}

Features:
├─ Tracking conversations persistant
├─ Mémoire documents avec ordre
├─ Cache contexte pour optimisation
├─ Apprentissage préférences utilisateur
└─ Extraction keywords
```

**`models/ml_faq_model.py`** - FAQ ML
```python
Implémentation TF-IDF:
├─ Chargement enrichissements:
│   ├─ enrichissement_culture.jsonl
│   ├─ enrichissement_informatique.jsonl
│   ├─ enrichissement_général.jsonl
│   └─ enrichissement_exemples.jsonl
├─ Normalisation questions
├─ Matching 3 niveaux:
│   1. Exact match (priorité max)
│   2. TF-IDF cosine (seuil 0.9)
│   3. RapidFuzz fuzzy (seuil 92%)
└─ Return None si pas de match
```

**`models/linguistic_patterns.py`** - Reconnaissance patterns
```python
Détection:
├─ Variations salutations (bonjour, bjr, salut, slt)
├─ Keywords programmation
├─ Marqueurs politesse
├─ Triggers génération code
├─ Types questions
└─ Dictionnaire tolérance typos
```

**`models/knowledge_base.py`** - Base connaissances
```python
Organisation:
├─ Programmation
│   ├─ Python (basics, avancé, librairies)
│   ├─ Web dev (frontend, backend)
│   └─ Data science
├─ Mathématiques (constantes, formules)
├─ Sciences (physique, chimie, bio)
└─ Connaissances générales
```

**`models/reasoning_engine.py`** - Raisonnement logique
```python
Composants:
├─ Opérateurs logiques (and, or, not, if-then)
├─ Types questions (what, how, why, when, where, who)
├─ Chaînes raisonnement (cause-effet, comparaison)
└─ Stratégies résolution problèmes
```

**`models/internet_search.py`** - Moteur recherche
```python
EnhancedInternetSearchEngine:
├─ DuckDuckGo API
├─ Multi-thread (max 8 résultats)
├─ Extraction patterns réponses:
│   ├─ Taille/poids
│   ├─ Population
│   ├─ Dates
│   ├─ Prix
│   └─ Définitions
├─ BeautifulSoup scraping
├─ Système caching (3600s)
└─ Rotation user agents
```

**`models/advanced_code_generator.py`** - Génération code avancée
```python
Sources intégrées:
├─ StackOverflow code extractor
├─ GitHub code searcher
├─ RealWebCodeGenerator
└─ Templates fallback

Processing:
├─ Semantic embedding matching (SentenceTransformer)
├─ Détection langage/complexité
├─ Filtrage par requirements
└─ Extraction direct answers
```

**Autres modules models/**
```python
web_code_searcher.py, smart_code_searcher.py, real_web_code_generator.py:
├─ Agrégation multi-sources
├─ Web scraping exemples code
├─ GitHub API (token requis)
└─ Pattern matching temps réel

base_ai.py:
├─ Interface abstraite modèles
├─ Format réponse standard
└─ Hooks extensibilité
```

### ⚙️ Processors - Traitement Documents

**`processors/pdf_processor.py`**
```python
Librairies:
├─ PyMuPDF (fitz) - Primaire (recommandé)
└─ PyPDF2 - Fallback

Processing:
├─ Extraction texte page par page
├─ Extraction metadata
├─ Extraction images
├─ Chunking documents larges
└─ Error handling + fallback

Output:
{
  "text": complete_document_text,
  "pages": [page_contents],
  "metadata": pdf_metadata,
  "page_count": int,
  "chunks": [smart_chunks]
}
```

**`processors/docx_processor.py`**
```python
Features:
├─ python-docx integration
├─ Extraction paragraphes et tables
├─ Préservation formatage
└─ Chunking pour optimisation contexte
```

**`processors/code_processor.py`**
```python
Capacités:
├─ Syntax highlighting compatible
├─ Détection langage
├─ Analyse structure (classes, fonctions)
├─ Analyse sémantique
└─ Extraction commentaires
```

### 🏭 Generators - Génération Contenu

**`generators/code_generator.py`**
```python
Templates disponibles:
├─ Python: class, function, script
├─ HTML: page, component
├─ JavaScript: function, component
└─ CSS: stylesheet

Features:
├─ Templates paramétrés
├─ Formatage spécifique langage
├─ Génération documentation
└─ Injection exemples
```

**`generators/document_generator.py`**
```python
Formats:
├─ Markdown
├─ PDF (reportlab)
├─ Structured output
└─ Context-aware content
```

### 🖥️ Interfaces - UI

**`interfaces/gui_modern.py`** - Interface graphique moderne
```python
Framework: CustomTkinter (fallback tkinter)
Design: Dark theme inspiré Claude.ai

Features:
├─ Chat interface responsive
├─ Bulles messages utilisateur (droite)
├─ Réponses IA (gauche, sans bulle)
├─ Code highlighting (Pygments)
├─ Drag-and-drop fichiers (tkinterdnd2)
├─ Timestamps
├─ Bouton clear chat
└─ Commandes help/status

Architecture:
├─ Gestion async messages
├─ Threading opérations longues
├─ Updates UI temps réel
└─ Affichage messages memory-efficient
```

**`interfaces/cli.py`** - CLI améliorée
```python
Commandes:
├─ Requêtes normales → AI
├─ Commandes spéciales:
│   ├─ aide/help: afficher commandes
│   ├─ quitter/exit: fermer
│   ├─ statut/status: état système
│   ├─ historique/history: conversations
│   ├─ fichier: traiter fichiers
│   └─ generer: générer contenu

Features:
├─ Boucle interactive
├─ Processing async
├─ Récupération erreurs
└─ Système aide détaillé
```

**`interfaces/modern_styles.py`**
```python
├─ Palette couleurs (dark theme)
├─ Configurations fonts
├─ Breakpoints responsive
└─ Adaptations plateforme
```

**`interfaces/vscode_extension.py`**
```python
├─ Placeholder extension VSCode
└─ Potentiel intégration command palette
```

### 🛠️ Tools - Outils Spécialisés

```python
tools/search_tool.py:
├─ Parcours récursif répertoires
├─ Matching keywords fichiers
└─ Recherche case-insensitive

tools/math_tool.py:
├─ Support calculatrice
└─ Évaluation formules

tools/local_tools.py:
├─ Opérations fichiers
└─ Informations système

tools/info_extraction_tool.py:
├─ Reconnaissance entités nommées
└─ Extraction données texte
```

### 🔧 Utils - Utilitaires

```python
utils/file_manager.py:
├─ Lecture/écriture fichiers
├─ Gestion répertoires
├─ Handling chemins
└─ Validation fichiers

utils/file_processor.py:
├─ Détection format
├─ Routage processing
└─ Error handling

utils/logger.py:
├─ Setup logging configuré
├─ Niveaux multiples
└─ Output fichier + console

utils/validators.py:
├─ Vérification types données
├─ Validation format
└─ Contrôle bornes

utils/intelligent_calculator.py:
├─ Évaluation expressions
├─ Opérations mathématiques
└─ Conversion unités
```

## 🔄 Flux de Traitement Complets

### 1. Flux Requête Utilisateur Standard

```
User Input
    ↓
Intent Detection (LinguisticPatterns)
    ├─ greeting? → greeting_response()
    ├─ code_generation? → code_generator.generate()
    ├─ document_analysis? → pdf/docx_processor.process()
    ├─ internet_search? → internet_search_engine.search()
    ├─ faq_match? → ml_faq_model.predict()
    └─ general? → custom_ai_model.respond()
    ↓
Response Generation + Confidence Scoring
    ↓
ConversationMemory Update
    ↓
Display (GUI/CLI)
```

### 2. Flux Traitement Document

```
File Upload
    ↓
Format Detection
    ├─ .pdf → PDFProcessor
    ├─ .docx → DOCXProcessor
    └─ .py/.js/.etc → CodeProcessor
    ↓
Content Extraction
    ↓
Chunking (2048 tokens)
    ↓
Store in ConversationMemory
    ↓
Add to MillionTokenContextManager
    ↓
User can query: "résume ce document"
```

### 3. Flux Génération Code

```
"Génère du code pour: [description]"
    ↓
Query StackOverflow API
    ├─ Extract top solutions
    └─ Rank by votes/relevance
    ↓
Query GitHub (web scraping)
    ├─ Search by language
    └─ Extract examples
    ↓
Semantic similarity matching
    ├─ Match to description
    └─ Filter by complexity
    ↓
Format best solution
    ├─ With explanation
    ├─ Alternative approaches
    └─ Source attribution
```

### 4. Flux RLHF Training

```
Initial Model State
    ↓
Load Training Dataset (JSONL/CSV)
    ↓
Generate Predictions
    ↓
Collect Human Feedback (0-5 ratings)
    ↓
Merge Feedback into Dataset
    ↓
Train with Feedback Signal
    ├─ Adjust loss based on ratings
    └─ Update model weights
    ↓
Evaluate Improvements
    ↓
Export Improved Model
```

### 5. Flux Recherche Internet

```
"cherche sur internet [query]"
    ↓
DuckDuckGo API search
    ↓
Top 8 results fetched
    ↓
Web scraping (BeautifulSoup)
    ↓
Pattern-based answer extraction
    ├─ Factual data (population, size)
    ├─ Definitions
    ├─ Dates/events
    └─ Technical specs
    ↓
Formatted response with sources
```

## 🎯 Patterns Architecturaux

### 1. Dependency Injection
```python
class AIEngine:
    def __init__(self, custom_ai=None, processors=None):
        self.custom_ai = custom_ai or CustomAIModel()
        self.processors = processors or self._init_processors()
```

### 2. Factory Pattern
```python
def create_processor(file_path: str) -> BaseProcessor:
    ext = Path(file_path).suffix.lower()
    processors = {
        '.pdf': PDFProcessor,
        '.docx': DOCXProcessor,
        '.py': CodeProcessor
    }
    return processors.get(ext, BaseProcessor)()
```

### 3. Strategy Pattern (Multi-backend)
```python
class CustomAIModel:
    def __init__(self):
        self.response_strategies = {
            'greeting': self._handle_greeting,
            'code_generation': self._handle_code_gen,
            'document': self._handle_document
        }
```

### 4. Observer Pattern (Logging/Analytics)
```python
class ConversationManager:
    def add_exchange(self, user, ai):
        for observer in self.observers:
            observer.on_exchange_added(user, ai)
```

## 📊 Données et Stockage

### Structure Data Directory
```
data/
├── enrichissement/
│   ├── enrichissement_culture.jsonl       # Priorité 1
│   ├── enrichissement_informatique.jsonl  # Priorité 2
│   ├── enrichissement_général.jsonl       # Priorité 3
│   └── enrichissement_exemples.jsonl      # Priorité 4
├── context_storage/        # Chunks contexte 1M tokens
├── outputs/                # Documents/code générés
├── temp/                   # Fichiers temporaires
├── backups/                # Sauvegardes
└── logs/                   # Logs application
```

### Format Enrichissement (JSONL)
```json
{"input": "Quelle est la capitale de la France?", "target": "Paris"}
{"input": "Comment faire une boucle en Python?", "target": "for i in range(10): ..."}
```

## 🚀 Points d'Entrée

### `launch_unified.py` - Launcher recommandé
```python
# Entry: main()
# Lance directement ModernAIGUI
# Initialisation minimale
# Fallback vers main.py si erreurs
```

### `main.py` - Launcher complet CLI
```python
# Modes supportés:
python main.py                        # CLI interactif
python main.py --mode gui             # GUI mode
python main.py chat "query"           # Requête directe
python main.py status                 # État système
python main.py file analyze path      # Analyse fichier
python main.py generate code "desc"   # Génération code
```

### `launch.bat` - Script Windows
```batch
# Options interface
# Setup environnement
# Récupération erreurs
```

## ⚡ Performances et Caractéristiques

### Temps Réponse Typiques
```
Greeting response:        < 100ms
FAQ match:                ~200ms
Simple conversation:      500ms - 2s
Code generation:          2-5s (web search inclus)
Document processing:      Variable (50MB PDF ≈ 10-20s)
Internet search:          3-8s (API + scraping)
1M token context query:   5-15s (dépend taille)
```

### Utilisation Mémoire
```
Base AI engine:           ~500MB RAM
Per document (chunked):   ~10MB par 1M tokens
Conversation memory:      ~50KB par 1000 messages
Total typique:            800MB - 2GB
```

### Token Efficiency
```
Compression ratio:        2.4:1 à 52:1 (selon contenu)
Context window standard:  4096 tokens
Context ultra mode:       1,048,576 tokens (1M)
Chunk size:               2048 tokens (configurable)
```

## 🔒 Sécurité

### Points Forts
```
✅ 100% local (pas de cloud sauf recherche web optionnelle)
✅ Validation fichiers (extension, taille)
✅ Sandboxing génération code (pas d'exécution)
✅ Error handling robuste
```

### Considérations
```
⚠️ Web scraping peut violer certains TOS
⚠️ GitHub token en variable environnement
⚠️ Parsing PDF sources non fiables
⚠️ Pas de sanitization HTML/code input
```

## 📈 Extensibilité

### Ajouter Nouveau Processeur
```python
# Créer dans processors/
class NewProcessor(BaseProcessor):
    def process(self, file_path: str) -> Dict:
        return {"content": ..., "metadata": ...}

# Enregistrer dans AIEngine.__init__()
self.new_processor = NewProcessor()
```

### Ajouter Nouvel Outil
```python
# Créer dans tools/
def new_tool(input: str) -> str:
    return processed_result

# Enregistrer dans AIEngine
```

### Custom Intent Detection
```python
# Ajouter à LinguisticPatterns._load_patterns()
self.patterns["new_intent"] = [variations_list]

# Handler dans CustomAIModel.respond()
elif intent == "new_intent":
    return self.new_intent_handler()
```

## 📚 Documentation Complémentaire

**Dans `docs/`:**
- `INSTALLATION.md` - Guide installation
- `USAGE.md` - Guide utilisation
- `OPTIMIZATION.md` - Optimisations performance
- `ULTRA_1M_TOKENS.md` - Détails contexte 1M
- `INTERNET_SEARCH.md` - Fonctionnalités recherche
- `FAQ.md` - Questions fréquentes
- `CHANGELOG.md` - Historique versions

## 🎯 État Architecture Actuel

### ✅ Production-Ready
- Système mémoire conversationnel
- Pipelines traitement documents
- Classification intentions
- Matching FAQ
- Gestion configuration

### 🟢 Fonctionnel (Bon État)
- Gestion contexte 1M tokens
- Framework génération code
- Intégration recherche internet
- Setup pipeline RLHF

### 🟡 Prototype
- Détection intentions neurale
- Recherche contexte sémantique
- Modules optimisation
- Extension VSCode

---

**Version**: 5.6.0
**Architecture**: Modulaire, extensible, 100% locale
**Capacité contexte**: 1,048,576 tokens (1M)
**Interfaces**: GUI (CustomTkinter), CLI, VSCode (prototype)
