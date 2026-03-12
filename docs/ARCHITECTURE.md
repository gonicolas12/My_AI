# 🏗️ Architecture - My Personal AI v6.8.0

## 📋 Vue d'Ensemble de l'Architecture

My Personal AI v6.8.0 est une **IA locale 100%** avec un système de **Mémoire Vectorielle**, **Météo en temps réel** et une **boucle agentique avancée (ChatOrchestrator)**, basée sur les principes suivants:

- **Mémoire Vectorielle Intelligente** : ChromaDB + embeddings sémantiques (1M tokens réel)
- **Tokenization Précise** : tiktoken cl100k_base (compatible Llama 3, précision maximale vs 70% approximation)
- **Recherche Sémantique** : Sentence-transformers (384 dimensions, similarité cosinus)
- **Météo Temps Réel** : Service wttr.in intégré (gratuit, toutes les villes du monde)
- **ChatOrchestrator** : Boucle agentique ReAct + Plan & Execute + Scratchpad persistant pour le tool-calling
- **Architecture 100% Locale** : Aucune dépendance cloud obligatoire, persistance locale
- **Reconnaissance d'intentions avancée** : Analyse linguistique multi-niveaux
- **Intégration MCP (Model Context Protocol)** : Connexion standardisée aux outils locaux et serveurs externes
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
├─────────────────────────────┴──────────────────┴─────────────────────┤
│  Agents Interface                                                    │
│  • Canvas visuel workflow n8n (WorkflowCanvas)                       │
│  • Monitoring ressources temps réel (ResourceMonitor)                │
│  • Exécution DAG / parallèle / séquentielle                         │
│  • Drag-and-drop agents + connexions Bézier                         │
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
│  • Client MCP (Model Context Protocol) pour outils externes          │
├──────────────────────────────────────────────────────────────────────┤
│ ChatOrchestrator (core/chat_orchestrator.py)                         │
│  • Boucle agentique ReAct (Reasoning + Acting)                       │
│  • Plan & Execute avec scratchpad XML persistant                     │
│  • Limite de tours (MAX_TOURS=15), LoopDetector, élagage contexte    │
│  • Utilisé par AIEngine pour tout tool-calling de la page Chat       │
└──────────────────────────────────────────────────────────────────────┘
                                   │
┌──────────────────────────────────────────────────────────────────────┐
│                      MODÈLES IA ET INTELLIGENCE                      │
├──────────────────────────────────────────────────────────────────────┤
│  Ollama (Prioritaire)       │  CustomAIModel (Fallback)              │
│  • LLM local (qwen3.5:4 b)  │  • Détection intentions                │
│  • Réponses naturelles      │  • Réponses contextuelles              │
│  • 100% confidentiel        │  • Patterns et règles                  │
├─────────────────────────────┴────────────────────────────────────────┤
│  UltraCustomAI (1M tokens)  │  LocalLLM (Gestionnaire Ollama)        │
│  • Extend CustomAI          │  • Vérification disponibilité          │
│  • Ultra-large context      │  • Fallback automatique                │
│  • Advanced processors      │  • Modèle personnalisable (Modelfile)  │
└──────────────────────────────────────────────────────────────────────┘
                                   │
┌──────────────────────────────────────────────────────────────────────┐
│                   GESTION DU CONTEXTE ET MÉMOIRE                     │
├─────────────────────────┬────────────────────────────────────────────┤
│ VectorMemory            │ ConversationMemory                         │
│ • ChromaDB vectoriel    │ • Conversations persistantes               │
│ • tiktoken cl100k_base  │ • Documents stockés                        │
│ • Sentence-transformers │ • Préférences utilisateur                  │
│ • 1M tokens contexte    │ • Cache contexte récent                    │
│ • Recherche sémantique  │ • Format JSON enrichi                      │
│ • AES-256 chiffrement   │                                            │
│ • Similarité cosinus    │                                            │
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
├─────────────────────────┼────────────────────────────────────────────┤
│ ExcelProcessor          │ CodeProcessor                              │
│ • openpyxl (.xlsx)      │ • Détection langage                        │
│ • xlrd (.xls legacy)    │ • Analyse structure (classes, fonctions)   │
│ • stdlib csv (.csv)     │ • Extraction commentaires                  │
│ • Multi-feuilles        │ • Analyse sémantique                       │
│ • Formatage tableau     │                                            │
│ • Encodage automatique  │                                            │
└─────────────────────────┴────────────────────────────────────────────┘
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
│ • DuckDuckGo API Instant│ • Code search                              │
│ • Météo temps réel      │ • GitHub integration                       │
│   (wttr.in gratuit)     │ • Real-time patterns                       │
│ • Toutes les villes     |                                            |
|   du monde              │                                            │
│ • Multi-thread (8)      │                                            │
│ • Pattern extraction:   │                                            │
│   - Facts (taille,      │                                            │
│     population, dates)  │                                            │
│   - Définitions         │                                            │
│   - Prix                │                                            │
│   - Conditions météo    │                                            │
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
├─ Délégation tool-calling → ChatOrchestrator
└─ Point d'entrée unique pour toutes les opérations
```

**`core/chat_orchestrator.py`** - Boucle agentique Chat
```python
Architecture:
├─ LoopDetector     : détecte boucles immédiates et élargies
├─ Scratchpad       : état cognitif persistant entre les tours
│   ├─ OBJECTIF     : demande originale
│   ├─ PLAN         : étapes numérotées avec ✓
│   ├─ FAITS        : résultats d'outils (tronqués 400 chars)
│   └─ TOURS REST.  : urgence < 3 tours
└─ ChatOrchestrator : boucle agentique principale
    ├─ run()         : interface publique unique
    ├─ MAX_TOURS=15  : limite absolue de tours
    ├─ MAX_TOOL_USES=5 : synthèse forcée après N outils
    ├─ PLAN_MIN_QUERY_LEN=55 : seuil déclenchement planification
    └─ Patterns : ReAct + Plan & Execute

Sécurités:
├─ Limite de tours avec message forcé avant coupure
├─ Détection de boucle (immédiate + élargie)
├─ Élagage sélectif contexte (MAX_HISTORY_MESSAGES=40)
├─ Validation légère des arguments avant exécution
└─ Détection d'hallucinations dans la réponse finale
```

**`core/agent_orchestrator.py`** - Coordonnateur Agents
```python
Responsabilités:
├─ Crée et réutilise les agents IA (page Agents)
├─ Historique des tâches multi-agents
└─ Distinct de ChatOrchestrator (usage exclusif page Agents)
```

**`core/mcp_client.py`** - Client MCP
```python
Capacités:
├─ Exposition outils locaux au format MCP
├─ Connexion serveurs MCP externes (stdio)
└─ Dégradation gracieuse si SDK mcp absent
```

**`core/shared.py`** - Module partagé
```python
Contenu:
├─ Modèle embeddings partagé (all-MiniLM-L6-v2)
├─ Stratégie offline-first (HF_HUB_OFFLINE=1)
└─ Évite de charger sentence_transformers 3× au démarrage
```

**`core/validation.py`** - Validation Pydantic
```python
Modèles:
├─ UserQueryInput  : query (1-10000 chars), context optionnel
├─ ToolArgumentsInput : validation args appels outils
└─ Sanitization : bloque exec/eval/os.system/subprocess
```

**`core/compression_monitor.py`** - Monitoring compression
```python
Fonctionnalités:
├─ Ratios compression en temps réel
├─ Stats par type de contenu
├─ Historique et rapports
└─ Indicateurs qualité chunking
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
core/rlhf_manager.py:
├─ Collecte feedback humain (0-5) via get_rlhf_manager()
├─ Détection patterns succès/échec
├─ Statistiques satisfaction
└─ Export données entraînement JSONL

core/training_manager.py:
├─ Fine-tuning modèles locaux
├─ Monitoring temps réel (métriques, checkpoints)
└─ Export modèles optimisés

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

**`models/custom_ai_model.py`** - Modèle IA principal
```python
Architecture:
├─ LinguisticPatterns (détection intentions)
├─ KnowledgeBase (domaines expertise)
├─ AdvancedCodeGenerator (multi-sources)
├─ ReasoningEngine (logique)
├─ ConversationMemory (persistance)
├─ InternetSearchEngine (DuckDuckGo + Météo)
├─ ML FAQ Model (TF-IDF)
├─ Processors (PDF, DOCX, Code)
└─ VectorMemory (ChromaDB + embeddings)

Capacités clés:
├─ Détection intentions avec confiance
├─ Tracking contexte session
├─ Mémoire vectorielle sémantique
├─ Météo temps réel (wttr.in)
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

**`memory/vector_memory.py`** - Mémoire Vectorielle
```python
Architecture ML:
├─ tiktoken (cl100k_base, compatible Llama 3)
│   └─ Comptage précis (vocabulaire aligné avec le LLM)
├─ Sentence-Transformers (all-MiniLM-L6-v2)
│   └─ Embeddings 384 dimensions
├─ ChromaDB PersistentClient
│   ├─ Collections: documents, conversations
│   ├─ Backend: SQLite + Parquet
│   └─ Index: HNSW (similarité cosinus)
└─ Chiffrement AES-256 (optionnel)

Capacités:
├─ Max 1M tokens stockage
├─ Chunks 512 tokens (overlap 50)
├─ Recherche sémantique ultra-rapide (0.02s)
├─ Déduplication automatique
├─ Cleanup intelligent (capacité atteinte)
├─ Statistiques détaillées
└─ Persistance (memory/vector_store/chroma_db/)

Méthodes principales:
├─ add_document(content, name, metadata) → Dict
├─ search_similar(query, n_results, type) → List[Dict]
├─ count_tokens(text) → int (tiktoken précis)
├─ split_into_chunks(text) → List[str]
├─ get_stats() → Dict
└─ clear_all() → void

Avantages vs ancien système:
✅ Tokenization précise tiktoken (cl100k_base, compatible Llama 3) vs 70% (mots)
✅ Recherche sémantique (comprend synonymes) vs mots-clés
✅ Vitesse 100x (vectoriel) vs linéaire
✅ Persistance totale (ChromaDB) vs perdu au redémarrage
✅ Capacité stable 1M+ tokens vs dégradation
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

**`models/local_llm.py`** - Gestionnaire Ollama
```python
Architecture:
├─ Connexion Ollama (http://localhost:11434)
├─ Vérification disponibilité serveur
├─ Détection modèle (my_ai → llama3 fallback)
├─ Génération de réponses via API
└─ Fallback automatique si Ollama indisponible

Configuration Modelfile:
├─ Modèle de base: qwen3.5:4b (ou autre selon choix)
├─ Temperature: 0.7
├─ Context window: 8192 tokens
└─ System prompt personnalisé français
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
EnhancedInternetSearchEngine :
├─ DuckDuckGo API Instant
├─ Météo temps réel intégrée:
│   ├─ Service wttr.in (gratuit, sans API)
│   ├─ Détection automatique requêtes météo
│   ├─ Toutes les villes du monde reconnues
│   ├─ Données: conditions, température, humidité, vent
│   ├─ Prévisions 3 jours
│   └─ Fallback Météo-France si indisponible
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

Ordre moteurs :
1. DuckDuckGo API Instant (rapide, stable)
2. Météo wttr.in (si détection météo)
3. Wikipedia API (fallback)
4. DuckDuckGo Lite (dernière chance, CAPTCHA)
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

**`processors/excel_processor.py`**
```python
Librairies:
├─ openpyxl  - Fichiers .xlsx (format moderne)
├─ xlrd      - Fichiers .xls (ancien format)
└─ csv       - Fichiers .csv (stdlib Python)

Processing:
├─ Lecture multi-feuilles (.xlsx, .xls)
├─ Détection encodage automatique (.csv)
├─ Formatage tableau texte (max 200 lignes, 30 chars/cellule)
├─ Fallback openpyxl → xlrd pour .xls
└─ Error handling par format

Output:
{
  "success": True,
  "content": formatted_text,          # Tableau(x) textuels
  "sheets": {sheet_name: [rows]},     # Données brutes
  "sheet_names": [str],
  "total_rows": int,
  "processor": "openpyxl|xlrd|csv-stdlib"
}
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

**`interfaces/agents_interface.py`** - Interface Agents IA
```python
Features:
├─ Grille 3x3+ de cartes agents (drag & drop)
├─ Pipeline classique (liste séquentielle)
├─ Canvas visuel n8n (WorkflowCanvas)
│   ├─ Nœuds avec statuts temps réel
│   ├─ Connexions Bézier
│   └─ Exécution DAG/parallèle/séquentielle
├─ Monitoring ressources (ResourceMonitor)
│   ├─ Barres de progression CPU/RAM/GPU/VRAM
│   ├─ Sparklines historiques
│   └─ Temps d'inférence et tokens/s
├─ Création/édition/suppression agents personnalisés
├─ Streaming résultats token par token
└─ Bouton Stop avec interruption immédiate
```

**`interfaces/workflow_canvas.py`** - Canvas visuel style n8n
```python
Architecture: tkinter Canvas pur (pas de dépendance externe)

Features:
├─ Nœuds: rectangle arrondi, bandeau couleur, ports E/S, status dot
├─ Connexions: Bézier cubique, flèches, clic droit suppression
├─ Zoom/Pan: molette (0.3x-3x), clic milieu/droit, zoom vers curseur
├─ Grille: points de repère, snap automatique, toggle
├─ Minimap: vue orthographique, viewport rectangle
├─ Toolbar: zoom ⊕/⊖, reset ⊙, grid ⊞
├─ Sélection: clic, shift+clic, rectangle de sélection
├─ Exécution: get_execution_plan() → tri topologique DAG
│   ├─ Mode empty: rien à exécuter
│   ├─ Mode single: un seul nœud
│   ├─ Mode sequential: chaîne linéaire
│   ├─ Mode parallel: nœuds indépendants simultanés
│   └─ Mode dag: étapes avec parallélisation intra-étape
└─ API: add_node(), remove_node(), add_connection(), set_node_status(), clear()
```

**`interfaces/resource_monitor.py`** - Monitoring ressources système
```python
Architecture: thread daemon avec collecte périodique (3s)

Sources:
├─ psutil: CPU% et RAM des processus Ollama
├─ pynvml (optionnel): GPU% et VRAM NVIDIA
├─ GPUtil (optionnel): fallback GPU
└─ Chronomètre interne: inference_ms et tokens_per_sec

Features:
├─ Historique 60 points par métrique (sparklines)
├─ Thread-safe (lock)
├─ Callbacks pour mise à jour UI
└─ Dégradation gracieuse si GPU packages absents
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
Ollama Check (LocalLLM.is_ollama_available)
    ├─ Ollama disponible?
    │   ├─ OUI → AIEngine.process_query_stream()
    │   │        ├─ Tool-calling détecté?
    │   │        │   ├─ OUI → ChatOrchestrator.run()
    │   │        │   │        ├─ 1. Planification (scratchpad)
    │   │        │   │        ├─ 2. Boucle ReAct (max 15 tours)
    │   │        │   │        │   ├─ Reasoning → Tool call
    │   │        │   │        │   ├─ LoopDetector (anti-boucle)
    │   │        │   │        │   └─ Observation → mise à jour scratchpad
    │   │        │   │        └─ 3. Synthèse streamée
    │   │        │   └─ NON  → Génération directe Ollama
    │   └─ NON → Fallback CustomAIModel
    │            ↓
    │        Intent Detection (LinguisticPatterns)
    │            ├─ greeting? → greeting_response()
    │            ├─ code_generation? → code_generator.generate()
    │            ├─ document_analysis? → pdf/docx_processor.process()
    │            ├─ internet_search? → internet_search_engine.search()
    │            ├─ faq_match? → ml_faq_model.predict()
    │            └─ general? → custom_ai_model.respond()
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
    ├─ .pdf         → PDFProcessor
    ├─ .docx        → DOCXProcessor
    ├─ .xlsx/.xls   → ExcelProcessor (openpyxl / xlrd)
    ├─ .csv         → ExcelProcessor (stdlib csv)
    └─ .py/.js/...  → CodeProcessor
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
├── context_storage/        # (Legacy - remplacé par vector_store)
├── outputs/                # Documents/code générés
├── temp/                   # Fichiers temporaires
├── backups/                # Sauvegardes
└── logs/                   # Logs application

memory/
├── vector_store/           # Mémoire vectorielle
│   ├── chroma_db/         # ChromaDB persistant (ignoré Git)
│   │   ├── chroma.sqlite3 # Metadata
│   │   └── *.parquet      # Vecteurs
│   └── README.md          # Documentation système
└── vector_memory.py        # Gestionnaire mémoire
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
Météo wttr.in:            1-3s (API externe)
Code generation:          2-5s (web search inclus)
Document processing:      Variable (50MB PDF ≈ 10-20s)
Internet search:          3-8s (API + scraping)
Vector search (1M tokens): 20-50ms (ChromaDB indexé)
```

### Utilisation Mémoire
```
Base AI engine:           ~500MB RAM
VectorMemory + models:    ~800MB (sentence-transformers)
Per document (chunked):   ~10MB par 1M tokens
ChromaDB persistent:      ~200MB disque (+ usage)
Conversation memory:      ~50KB par 1000 messages
Total typique:            1.3GB - 2.5GB RAM
```

### Token Efficiency
```
Tokenization précision:   tiktoken cl100k_base (compatible Llama 3) vs 70% (approximation mots)
Context window standard:  4096 tokens
Context ultra mode:       1,048,576 tokens (1M)
Chunk size VectorMemory:  512 tokens (configurable)
Chunk overlap:            50 tokens (contexte préservé)
Embedding dimensions:     384 (all-MiniLM-L6-v2)
Search speed:             0.02s pour 1M tokens
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

---

**Version**: 6.8.0
**Architecture**: Modulaire, extensible, 100% locale
**Capacité contexte**: 1,048,576 tokens (1M) avec recherche sémantique
**Interfaces**: GUI (CustomTkinter), CLI, VSCode (prototype)
