# 🏗️ Architecture - My Personal AI v9.0.0

## 📋 Vue d'Ensemble de l'Architecture

My Personal AI v9.0.0 est une **IA locale 100%** avec un système de **Mémoire Vectorielle**, **Météo en temps réel**, une **boucle agentique avancée (ChatOrchestrator)** et des **modules intelligents**, basée sur les principes suivants:

- **Mémoire Vectorielle Intelligente** : ChromaDB + embeddings sémantiques (10M tokens réel)
- **Tokenization Précise** : tiktoken cl100k_base (compatible Llama 3, précision maximale vs 70% approximation)
- **Recherche Sémantique** : Sentence-transformers (384 dimensions, similarité cosinus)
- **Météo Temps Réel** : Open-Meteo intégré (gratuit, sans clé, prévisions sur 7 jours)
- **ChatOrchestrator** : Boucle agentique ReAct + Plan & Execute + Scratchpad persistant pour le tool-calling
- **Architecture 100% Locale** : Aucune dépendance cloud obligatoire, persistance locale
- **API REST Locale** : Serveur FastAPI pour intégrations externes (chat, modèles, stats)
- **Base de Connaissances Structurée** : Faits retenus depuis le chat (« retiens que… ») ou ajoutés à la main, injectés dans le prompt
- **Multi-Workspaces** : Sessions isolées avec sauvegarde automatique et persistance JSON
- **Export Multi-Format** : Conversations exportables en Markdown, HTML et PDF
- **Détection de Langue** : 12 langues détectées automatiquement, réponse adaptée
- **Cache Web Persistant** : Cache disque avec TTL pour les recherches internet
- **Historique des Commandes** : Suivi complet avec favoris, recherche et statistiques
- **Reconnaissance d'intentions avancée** : Analyse linguistique multi-niveaux
- **Intégration MCP (Model Context Protocol)** : Connexion standardisée aux outils locaux et serveurs externes
- **Multi-sources d'information** : Code (StackOverflow, GitHub), web (DuckDuckGo, puis Yahoo et Wikipédia en secours)
- **RLHF intégré** : Pipeline complet d'amélioration continue
- **Scheduler proactif** : Exécution récurrente d'agents/workflows (type cron) via `core/scheduler.py` — tourne tant que l'appli ou le Relay est lancé, ou **même appli fermée** via le Planificateur de tâches Windows (`core/scheduler_runner.py`). Réutilise `AgentRelayService` (aucune réimplémentation de l'exécution), persistance JSON, verrou inter-processus.
- **Interface desktop web** : React + TypeScript (`frontend/`) dans une fenêtre native pywebview (WebView2 sous Windows), reliée au moteur par un serveur FastAPI local (`interfaces/desktop/`, 127.0.0.1, jeton par lancement : REST + WebSocket). Le chat passe par `core/chat_service.py`, sans interface, partagé avec le mobile ; la fenêtre reste fluide pendant que le moteur calcule.
- **Aperçu Artifacts** : Rendu live du HTML/CSS/SVG généré par l'IA et des documents produits — `<iframe sandbox>` sans `allow-same-origin` dans la fenêtre comme sur le mobile, lecteur PDF de WebView2, visionneuses natives Word/PowerPoint/Excel posées dans le volet d'aperçu (fenêtre enfant DPI par écran). Ouverture automatique en fin de réponse. Détection partagée dans `interfaces/artifacts.py`.
- **Génération de documents** : outils MCP `generate_document` / `edit_document` — le LLM rédige en Markdown, `generators/markdown_document.py` le découpe en blocs, un backend par format produit le docx, pdf, pptx ou xlsx dans `outputs/documents/`. Les pièces jointes sont modifiées sur une copie, jamais en place.
- **Extension VS Code agentique** : Client TypeScript publié sur le Marketplace VS Code. Branchée sur le Relay via le même tunnel chiffré E2EE (AES-256-GCM) que le mobile, mais avec un **mode agentique** : à la connexion, l'extension s'identifie comme `client_kind: "vscode"` et le Relay aiguille la conversation vers une boucle de raisonnement (`core/agentic_executor.py`) qui appelle Ollama directement. Le LLM peut émettre des appels d'outils (lecture/écriture/édition de fichiers, ripgrep, commandes shell, etc.) qui sont **exécutés côté extension**, sandboxés au workspace VS Code par défaut, avec approbation utilisateur pour les opérations destructives. Le pipeline GUI/mobile reste intact pour les autres clients. UI bilingue FR/EN.
- **Modularité complète** : Composants indépendants avec fallbacks robustes

## 🚀 Architecture Système Complète

```
┌────────────────────────────────────────────────────────────────────────┐
│                         INTERFACES UTILISATEUR                         │
├────────────────────────────────────────────────────────────────────────┤
│  Fenêtre desktop (web)      │  CLI Enhanced    │  VSCode Extension     │
│  • React + TypeScript       │  • Commandes     │  • Mode agentique     │
│  • Fenêtre pywebview        │  • Historique    │  • 9 outils workspace │
│  • Serveur local FastAPI    │  • Stats         │  • Sandbox + approval │
├─────────────────────────────┴──────────────────┴───────────────────────┤
│  Page Agents (même fenêtre)                                            │
│  • Canvas de workflow (React Flow), liens animés pendant l'exécution   │
│  • Fils d'exécution rouvrables, diff du code modifié                   │
│  • Monitoring ressources temps réel (ResourceMonitor)                  │
│  • Exécution DAG / parallèle / séquentielle (AgentRelayService)        │
├────────────────────────────────────────────────────────────────────────┤
│  My_AI Relay (relay/)                                                  │
│  • Interface mobile PWA (iOS/Android) via WebSocket — onglets          │
│    Chat / Agents (comme la fenêtre du PC)                              │
│  • Tunnels HTTPS (cloudflared, localhost.run), vérifiés depuis le PC   │
│  • Authentification token/mot de passe + QR code                       │
│  • RelayBridge (singleton) : chat mobile → ChatService, fenêtre        │
│    ouverte ou non                                                      │
│  • AgentRelayService : exécuteur partagé (fenêtre, mobile, scheduler)  │
│    — workflow/débat/CRUD streamés                                      │
│  • Routage par client_kind : "mobile" → ChatService, "vscode" →        │
│    AgenticExecutor (boucle LLM ↔ outils, exécution côté extension)     │
└────────────────────────────────────────────────────────────────────────┘
                                   │
┌────────────────────────────────────────────────────────────────────────┐
│                          MOTEUR IA CENTRAL                             │
├────────────────────────────────────────────────────────────────────────┤
│ AIEngine (core/ai_engine.py)                                           │
│  • Orchestration de tous les modules                                   │
│  • Routage intelligent selon intentions                                │
│  • Gestion de session et contexte                                      │
│  • Intégration processeurs, générateurs, outils                        │
│  • Client MCP (Model Context Protocol) pour outils externes            │
├────────────────────────────────────────────────────────────────────────┤
│ ChatOrchestrator (core/chat_orchestrator.py)                           │
│  • Boucle agentique ReAct (Reasoning + Acting)                         │
│  • Plan & Execute avec scratchpad XML persistant                       │
│  • Limite de tours (MAX_TOURS=15), LoopDetector, élagage contexte      │
│  • Utilisé par AIEngine pour tout tool-calling de la page Chat         │
├────────────────────────────────────────────────────────────────────────┤
│ ChatService (core/chat_service.py)                                     │
│  • Pipeline du chat sans interface, pour la fenêtre et le mobile       │
│  • File d'attente commune, sessions, branches d'édition                │
│  • Mêmes appels au moteur que l'ancienne interface (reprise du prompt) │
├────────────────────────────────────────────────────────────────────────┤
│ Modules (initialisés par AIEngine._init_v7_modules())                  │
│  • APIServer         — Serveur REST FastAPI (localhost:8000)           │
│  • CommandHistory     — Historique commandes SQLite + favoris          │
│  • ConversationExporter — Export MD / HTML / PDF                       │
│  • KnowledgeBaseManager — Faits structurés + extraction automatique    │
│  • LanguageDetector   — Détection de 12 langues + suffix prompt        │
│  • SessionManager     — Multi-workspaces avec persistance JSON         │
│  • WebCache           — Cache disque (diskcache) avec TTL              │
└────────────────────────────────────────────────────────────────────────┘
                                   │
┌────────────────────────────────────────────────────────────────────────┐
│                       MODÈLES IA ET INTELLIGENCE                       │
├────────────────────────────────────────────────────────────────────────┤
│  Ollama (Prioritaire)       │  CustomAIModel (Fallback)                │
│  • LLM local (qwen3.5:4b)   │  • Détection intentions                  │
│  • Réponses naturelles      │  • Réponses contextuelles                │
│  • 100% confidentiel        │  • Patterns et règles                    │
├─────────────────────────────┴──────────────────────────────────────────┤
│  VectorMemory (10M tokens)  │  LocalLLM (Gestionnaire Ollama)          │
│  • Mémoire vectorielle      │  • Vérification disponibilité            │
│  • Ultra-large context      │  • Fallback automatique                  │
│  • Processeurs avancés      │  • Modèle personnalisable (Modelfile)    │
└────────────────────────────────────────────────────────────────────────┘
                                   │
┌────────────────────────────────────────────────────────────────────────┐
│                    GESTION DU CONTEXTE ET MÉMOIRE                      │
├─────────────────────────┬──────────────────────────────────────────────┤
│ VectorMemory            │ ConversationMemory                           │
│ • ChromaDB vectoriel    │ • Conversations persistantes                 │
│ • tiktoken cl100k_base  │ • Documents stockés                          │
│ • Sentence-transformers │ • Préférences utilisateur                    │
│ • 10M tokens contexte   │ • Cache contexte récent                      │
│ • Recherche sémantique  │ • Format JSON enrichi                        │
│ • AES-256 chiffrement   │                                              │
│ • Similarité cosinus    │                                              │
└─────────────────────────┴──────────────────────────────────────────────┘
                                   │
┌────────────────────────────────────────────────────────────────────────┐
│                 RECONNAISSANCE ET ANALYSE LINGUISTIQUE                 │
├────────────────────────────────────────────────────────────────────────┤
│ LinguisticPatterns                                                     │
│ • Détection salutations                                                │
│ • Mots-clés code                                                       │
│ • Questions types                                                      │
│ • Tolérance typos                                                      │
├────────────────────────────────────────────────────────────────────────┤
│ KnowledgeBase                                                          │
│ • Programmation (Python, web, data)                                    │
│ • Web dev (frontend, backend)                                          │
│ • Mathématiques / Sciences                                             │
│ • Connaissances générales                                              │
└────────────────────────────────────────────────────────────────────────┘
                                   │
┌────────────────────────────────────────────────────────────────────────┐
│                       PROCESSEURS DE DOCUMENTS                         │
├─────────────────────────┬──────────────────────────────────────────────┤
│ PDFProcessor            │ DOCXProcessor                                │
│ • PyMuPDF (primaire)    │ • python-docx                                │
│ • PyPDF2 (fallback)     │ • Extraction paragraphes                     │
│ • Extraction metadata   │ • Tables                                     │
│ • Images                │ • Chunking intelligent                       │
│ • Chunking pages        │                                              │
├─────────────────────────┼──────────────────────────────────────────────┤
│ ExcelProcessor          │ CodeProcessor                                │
│ • openpyxl (.xlsx)      │ • Détection langage                          │
│ • xlrd (.xls legacy)    │ • Analyse structure (classes, fonctions)     │
│ • stdlib csv (.csv)     │ • Extraction commentaires                    │
│ • Multi-feuilles        │ • Analyse sémantique                         │
│ • Formatage tableau     │                                              │
│ • Encodage automatique  │                                              │
├─────────────────────────┼──────────────────────────────────────────────┤
│ PPTXProcessor           │ path_resolution                              │
│ • python-pptx           │ • Chemins OneDrive, partagé DOCX / PPTX      │
│ • Titres, puces, niveaux│                                              │
│ • Tableaux, notes       │                                              │
│ • Modèles .potx         │                                              │
└─────────────────────────┴──────────────────────────────────────────────┘
                                   │
┌────────────────────────────────────────────────────────────────────────┐
│                        GÉNÉRATEURS DE CONTENU                          │
├─────────────────────────┬──────────────────────────────────────────────┤
│ AdvancedCodeGenerator   │ DocumentGenerator                            │
│ • StackOverflow API     │ • docx / pdf / pptx / xlsx (+ md, csv…)      │
│ • GitHub search         │ • Rédaction Markdown par le LLM              │
│ • Web scraping          │ • markdown_document : Markdown → blocs       │
│ • Templates fallback    │ • DocumentEditor : modification sur copie    │
│ • Semantic ranking      │ • Outils MCP generate_ / edit_document       │
└────────────────────────────────────────────────────────────────────────┘
                                   │
┌────────────────────────────────────────────────────────────────────────┐
│                        OUTILS ET RECHERCHE WEB                         │
├─────────────────────────┬──────────────────────────────────────────────┤
│ InternetSearchEngine    │ SmartWebSearcher                             │
│ • DuckDuckGo (HTML)     │ • Code search                                │
│ • Yahoo, Wikipédia      │ • GitHub integration                         │
│   en secours            │ • Real-time patterns                         │
│ • Lecture des pages     │                                              │
│   (4 en parallèle)      │                                              │
│ • Météo Open-Meteo      │                                              │
│   (7 jours, sans clé)   │                                              │
│ • Sources numérotées    │                                              │
│   et cliquables         │                                              │
│ • HTTPS vérifié         │                                              │
│   (truststore)          │                                              │
│ • Pause si anti-robot   │                                              │
│ • Cache 30 min          │                                              │
├─────────────────────────┴──────────────────────────────────────────────┤
│ Local Tools: local_math, local_search, extract_emails, extract_dates   │
└────────────────────────────────────────────────────────────────────────┘
                                   │
┌────────────────────────────────────────────────────────────────────────┐
│                     RLHF ET AMÉLIORATION CONTINUE                      │
├─────────────────────────┬──────────────────────────────────────────────┤
│ RLHF Pipeline           │ Feedback Integration                         │
│ • Dataset loading       │ • Merge feedback to training data            │
│ • Human feedback (0-5)  │ • Rating incorporation                       │
│ • Training loop         │ • Iterative retraining                       │
│ • Model export          │ • Quality metrics                            │
└────────────────────────────────────────────────────────────────────────┘
                                   │
┌────────────────────────────────────────────────────────────────────────┐
│                       OPTIMISATION ET ÉVALUATION                       │
├─────────────────────────┬──────────────────────────────────────────────┤
│ Optimization Module     │ Evaluation & Error Analysis                  │
│ • Quantization          │ • Metrics (P/R/F1/EM)                        │
│ • Pruning               │ • Error tracking                             │
│ • Model export          │ • Performance analysis                       │
└────────────────────────────────────────────────────────────────────────┘
                                   │
┌────────────────────────────────────────────────────────────────────────┐
│                              UTILITAIRES                               │
├────────────────────────────────────────────────────────────────────────┤
│  FileManager │ Logger │ Validators │ Config │ FileProcessor            │
└────────────────────────────────────────────────────────────────────────┘
```

## 📦 Structure Détaillée des Modules

### 🧠 Core - Cœur du Système

**`core/ai_engine.py`** - Orchestrateur central
```python
Responsabilités:
├─ Initialisation de tous les modules
├─ Routage des requêtes selon intentions
├─ Gestion de session (documents, code, historique)
├─ Texte des documents chargés dans le prompt : budget = 25 % de num_ctx
│  (≈ 24 500 caractères pour 32 768 tokens), partagé entre documents ;
│  au-delà, début du document + passages liés à la question par les mots et
│  le sens (core/document_passages.py), sélection signalée au modèle
├─ Garde-fou des réponses sur pièces jointes (_stream_document_answer) : le
│  modèle demande parfois le fichier qu'il a déjà (≈ 1 réponse sur 30) ; un
│  début en forme de refus est retenu jusqu'à la fin de sa première phrase ;
│  un refus est coupé sans être affiché et la réponse redemandée une fois par
│  un message de rappel, qui prolonge la conversation : Ollama reprend le
│  prompt déjà calculé (quelques secondes au lieu de ≈ 2 min sur CPU)
├─ Coordination processeurs/générateurs
├─ Délégation tool-calling → ChatOrchestrator
└─ Point d'entrée unique pour toutes les opérations
```

**`core/chat_orchestrator.py`** - Boucle agentique Chat
```python
Architecture:
├─ LoopDetector     : détecte boucles immédiates et élargies
├─ Scratchpad       : état cognitif persistant entre les tours
│   ├─ OBJECTIF     : début et fin de la demande (300 caractères, en entier
│   │                 plus haut)
│   ├─ PLAN         : étapes numérotées, ✓ faite, ✗ outil sans résultat ;
│   │                 relancer cet outil retente l'étape, sans cocher la suivante
│   ├─ FAITS        : résultats d'outils (tronqués 400 chars)
│   ├─ TOURS REST.  : urgence < 3 tours
│   └─ Placement    : état complet après la question ou le 1er outil, puis
│                     objectif et avancement après chaque outil ; rien n'est
│                     retiré ni modifié en amont (chaque tour prolonge le précédent)
└─ ChatOrchestrator : boucle agentique principale
    ├─ run()         : interface publique unique
    ├─ MAX_TOURS=15  : limite absolue de tours
    ├─ MAX_TOOL_USES=5 : synthèse forcée après N outils ; seul l'outil de
    │                  document reste offert tant que le document demandé
    │                  n'existe pas
    ├─ PLAN_MIN_QUERY_LEN=55 : seuil déclenchement planification
    ├─ Synthèse      : dans la foulée de la boucle (même prompt, mêmes outils,
    │                  consignes en dernier message) ; repli sur une synthèse à
    │                  part si son début est rejeté ou cite la boucle
    └─ Patterns : ReAct + Plan & Execute

Sécurités:
├─ Limite de tours avec message forcé avant coupure
├─ Détection de boucle (immédiate + élargie)
├─ Élagage sélectif contexte (MAX_HISTORY_MESSAGES=40)
├─ Validation légère des arguments avant exécution
├─ Document demandé mais pas créé : une relance avant de conclure, avec ou
│  sans outils déjà utilisés
├─ Recherches web vides (MAX_EMPTY_SEARCHES=2) et document demandé : le
│  créer avec les connaissances du modèle, au lieu de reformuler encore
├─ Document demandé créé, sans autre action demandée (« puis déplace-le »…) :
│  synthèse aussitôt, sans tour de plus
├─ Appel à Ollama en échec, document demandé pas encore créé : refait une
│  fois ; le corps des erreurs HTTP est journalisé
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

**`core/api_server.py`** - Serveur API REST
```python
Architecture:
├─ FastAPI + Uvicorn en thread daemon
├─ Endpoints : health, chat, models, conversations, stats
├─ CORS configurable pour intégrations externes
└─ Arrêt gracieux via stop()
```

**`core/agentic_executor.py`** - Boucle agentique pour clients VS Code
```python
Activé exclusivement quand un client Relay s'identifie comme
client_kind: "vscode" (cf. relay/relay_server.py). Le mobile et la fenêtre
desktop n'utilisent jamais ce module.

Architecture:
├─ AGENT_TOOLS              # Schéma déclaratif des 9 outils workspace
│                           #   (read_file, write_file, edit_file,
│                           #    list_dir, glob, grep, run_command,
│                           #    get_active_editor, open_file)
├─ build_system_prompt(...)  # Prompt système avec doc des outils
│                           #   et format <tool_use>{...}</tool_use>
├─ parse_tool_calls(...)    # Extrait les blocs <tool_use> du texte LLM
│                           #   (tolérant : code-fence ```json, JSON
│                           #    malformés silencieusement ignorés)
├─ RemoteToolExecutor       # Pont WS : envoie tool_use, await tool_result
│                           #   via asyncio.Future indexées par call_id
└─ AgenticExecutor.run()    # Boucle :
                            #   1. appel Ollama /api/chat en streaming
                            #   2. callback on_chunk pour broadcast WS
                            #   3. parse les tool_use éventuels
                            #   4. dispatche en parallèle (asyncio.gather)
                            #   5. réinjecte les résultats au LLM
                            #   6. répète jusqu'à plus de tool_use
                            #      (max 25 itérations) ou réponse finale
                            # Garde-fou anti-boucle : la même action (même
                            #   outil, même chemin) est recadrée à 3, coupée à 5
                            # STOP : la tâche est annulée et le thread de
                            #   streaming coupe la connexion Ollama (la
                            #   génération est abandonnée, le slot libéré)

L'historique de conversation est passé par référence (mutation in-place)
pour permettre la continuité entre messages d'une même session WS.

Format LLM-agnostique : les outils sont transmis via des balises texte
(non via l'API tools native d'Ollama) → marche avec n'importe quel modèle.
```

**`core/command_history.py`** - Historique des commandes
```python
Fonctionnalités:
├─ SQLite WAL thread-safe
├─ Recherche plein texte (COLLATE NOCASE)
├─ Système de favoris avec toggle
├─ Auto-purge des entrées anciennes (préserve favoris)
└─ Statistiques : total, favoris, répartition agents, plage dates
```

**`core/conversation_exporter.py`** - Export conversations
```python
Formats:
├─ Markdown (.md) avec métadonnées header
├─ HTML (.html) avec thème sombre CSS embarqué
├─ PDF (.pdf) via ReportLab avec styles par rôle
└─ Blocs de code préservés dans tous les formats
```

**`core/knowledge_base_manager.py`** - Base de connaissances
```python
Architecture:
├─ SQLite avec 6 catégories de faits
├─ Score de confiance (0.0-1.0)
├─ Extraction automatique (patrons linguistiques FR)
│   ├─ Préférences, Décisions, Personnes
│   ├─ Procédures, Techniques
│   └─ Confiance auto : 0.7
├─ Mémorisation depuis le chat : extract_remember_request (« retiens que… »)
│   + remember() sans doublon (aussi l'outil remember_fact du modèle)
├─ select_facts : mots communs avec la requête, puis les plus récents
├─ Injection contexte dans le prompt IA (et dans la synthèse après outils)
└─ CRUD complet avec recherche plein texte
```

**`core/memory_store.py`** - Accès CRUD unifié à la mémoire
```python
Rôle:
├─ Façade homogène sur les 2 stores (faits SQLite + vecteurs ChromaDB)
├─ Lister / paginer / filtrer / éditer / supprimer faits ET entrées vectorielles
├─ Conversations : suppression/édition « à la source » (workspace + réindex) → durable
└─ Exposé via AIEngine.get_memory_store() (paresseux) ; testable sans GUI
```

**`core/language_detector.py`** - Détection de langue
```python
Capacités:
├─ 12 langues : fr, en, es, de, it, pt, nl, ru, zh, ja, ko, ar
├─ Bibliothèque langdetect (avec fallback)
├─ Cache LRU (128 entrées)
└─ Génération automatique suffix prompt système
```

**`core/session_manager.py`** - Workspaces
```python
Fonctionnalités:
├─ Multi-workspaces isolés avec identifiants slug
├─ Persistance JSON atomique (temp file + rename)
├─ État complet : historique, documents, agents, paramètres
├─ Auto-save configurable (défaut 300s)
└─ Limite 50 workspaces (configurable)
```

**`core/conversation_search.py`** - Recherche globale cross-conversations
```python
Rôle:
├─ Recherche sémantique sur TOUS les workspaces à la fois
├─ Réutilise l'index ChromaDB « conversations » + embedding partagé (aucun 2e pipeline)
├─ Indexation incrémentale (manifeste last_modified + schéma de version)
├─ Hybride : voisins sémantiques + reranking CrossEncoder + filet lexical mot-exact + seuil
└─ Filtres rôle / mot-clé / date ; exposé via AIEngine.get_conversation_search()
```

**`core/document_passages.py`** - Passages d'un long document selon la question
```python
Rôle:
├─ select_passages(text, query, limit, similarity) : appelé par AIEngine quand
│  un document chargé dépasse sa part du prompt
├─ Passages d'≈ 1 000 caractères coupés sur les fins de ligne
├─ Score des mots : BM25 sans accents, racine des mots (5 lettres), mots vides
│  FR/EN, bonus pour deux mots de la question qui se suivent (« section 15 »),
│  « rubrique » / « chapitre » = « section » (FDS françaises)
├─ Score de sens (core/passage_embeddings.py) : relie une question et un
│  passage de langues différentes (« gants » → « gloves ») ; les deux scores,
│  ramenés entre 0 et 1, comptent à poids égal (mots seuls tant que le modèle
│  n'est pas téléchargé)
├─ Début du document + 3 meilleurs passages + leurs voisins + autres passages
│  contenant des mots de la question, dans l'ordre du texte ; budget restant
│  laissé vide (prompt plus court)
├─ Aucun mot trouvé (« résume ce document ») → extraits répartis sur tout le texte
└─ Mesuré sur 27 questions (FDS anglaise + FAQ française, petit budget) :
   réponse dans les extraits 20/27 avec les mots seuls, 25/27 avec le sens
```

**`core/passage_embeddings.py`** - Modèle multilingue de la sélection des passages
```python
Modèle:
├─ ibm-granite/granite-embedding-107m-multilingual (IBM, Apache 2.0), version
│  figée (REVISION) ; 9 fichiers, 228 Mo (le dépôt contient aussi ONNX/PyTorch)
├─ Choisi face à multilingual-e5-small (493 Mo) : même précision sur nos
│  questions, 2 fois plus léger, 1,6 fois plus rapide sur CPU ;
│  paraphrase-multilingual-MiniLM écarté (coupe à 128 tokens)
Téléchargement:
├─ prefetch_in_background() : thread démon lancé par launch_unified.py et
│  main.py (modes interactifs) s'il manque un fichier dans le cache Hugging Face
├─ hf_hub_download fichier par fichier, sans pool de threads : fermer l'app ne
│  fige pas le terminal (reprise au lancement suivant), pas de WinError 1314
│  (Windows sans droit de lien symbolique)
├─ Échec réseau → message + aide proxy (core.network), nouvel essai au lancement suivant
└─ Désactivation : optimization.rag.multilingual_passages: false (config.yaml)
Utilisation:
├─ similarities(query, passages) → cosinus ou None (absent, désactivé, inutilisable)
├─ Chargement au premier long document (≈ 1 s, ≈ 430 Mo de RAM)
└─ Vecteurs des passages en cache (4 096) : les questions suivantes sur le même
   document n'encodent que la question
```

**`core/folder_indexer.py`** - Contexte projet « @codebase »
```python
Rôle:
├─ Attache et indexe un DOSSIER entier rattaché à un workspace (RAG persistant)
├─ Collection ChromaDB dédiée « codebase » ; chunks étiquetés workspace_id/folder/file
├─ Réutilise FileProcessor + VectorMemory.split_into_chunks (aucun 2e pipeline)
├─ Incrémental : manifeste mtime+taille+hash par fichier ; purge des supprimés
├─ Respecte .gitignore (pathspec ou matcher intégré) + exclusions (node_modules…)
└─ search(workspace_id, query) : filtre par workspace + rerank CrossEncoder
   exposé via AIEngine.get_folder_indexer() ; outil MCP « search_codebase »
```

**`core/prompt_library.py`** - Bibliothèque de prompts / slash commands
```python
Rôle:
├─ Templates persistés en JSON (data/prompt_templates.json, atomique, gitignored)
├─ 6 commandes par défaut seedées au 1er lancement (/code, /résume, /traduis…)
├─ expand("/cmd args") : slash command → prompt détaillé (placeholder {arguments})
├─ render(tpl, args) : substitution {arguments} (ou ajout en suffixe)
└─ _sync_builtins() : migration de format des builtins, sans toucher au custom
   exposé via AIEngine.prompt_library ; endpoint Relay GET /api/prompts (E2EE)
```

**`core/web_cache.py`** - Cache web
```python
Architecture:
├─ diskcache pour stockage thread-safe
├─ TTL configurable (défaut 3600s)
├─ Clé SHA256 stable par URL
├─ Éviction automatique (max_entries)
└─ Statistiques hits/misses
```

**`core/shared.py`** - Module partagé
```python
Contenu:
├─ Modèle embeddings partagé (all-MiniLM-L6-v2)
├─ Offline-first : chargé depuis le dossier du cache, sans aucune requête au
│  Hub ; téléchargé seulement s'il n'y est pas (premier lancement)
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
├─ Limites tokens (32768 standard, 10M ultra)
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

### 📡 Relay — Accès Mobile

**`relay/relay_server.py`** - Serveur FastAPI + WebSocket
```python
Architecture:
├─ FastAPI app en thread daemon (non-bloquant)
├─ WebSocket /ws : chat temps réel (auth → messages → réponse)
│   ├─ Protocole : {"e": "<base64url>"} encapsulant {type, ...}
│   ├─ chat (mobile) : armé via bridge, attente DÉTACHÉE en tâche pour
│   │   garder la boucle libre de lire stop_generation pendant la génération
│   ├─ stop_generation : mobile → bridge.request_interrupt() → interrupt_ai()
│   │   côté GUI ; vscode → annule la tâche agentique (flux Ollama coupé), et
│   │   renvoie toujours la réponse « interrompue » qui libère le bouton
│   └─ Messages page Agents (agents_list, agent_create/edit/delete,
│       agent_execute, agent_debate, agent_stop) → AgentRelayService,
│       streamés via une file unique drainée par une seule coroutine
│       (évite l'entrelacement des envois pendant les étapes parallèles)
├─ REST :
│   ├─ GET /, POST /auth, GET /api/health (clair)
│   ├─ GET /api/history, GET /api/pending (réponse E2EE)
│   └─ POST /api/upload : multipart binaire chiffré → fichier temp + file_id
│       ├─ Wire body : nonce(12) || aes_gcm_ct(N+16)
│       ├─ Clair : "MYAI" || u16_be(filename_len) || filename || content
│       ├─ Allowlist extensions (images + PDF/DOCX/XLSX/CSV/code)
│       ├─ Plafond 25 Mo de clair (413 + cleanup si dépassement)
│       └─ Registre Dict[file_id, meta] sous threading.Lock
├─ Authentification : token SHA-256 (password) ou secrets.token_urlsafe
├─ Chiffrement E2EE : AES-256-GCM, clé éphémère 32 octets régénérée à
│   chaque démarrage. Diffusion de la clé : exclusivement via le
│   fragment du QR code (jamais émis sur le réseau).
├─ Multi-tunnel parallèle : cloudflared + localhost.run (serveo en option,
│   son nom de tunnel contient l'IP publique du réseau)
│   ├─ Tunnels → 127.0.0.1 (le Relay n'écoute qu'en IPv4 ; « localhost »
│   │   donnait ::1, que l'OpenSSH de Windows ne sait pas abandonner)
│   ├─ Vérification depuis le PC (_watch_tunnels, même test que la page de
│   │   routage : GET /api/health) : seuls les joignables entrent dans le
│   │   QR code ; si aucun ne répond en 30 s, ils y entrent tous
│   ├─ cloudflared testé via les serveurs DNS faisant autorité de
│   │   trycloudflare.com (pas de « nom inexistant » gardé en cache)
│   ├─ Liste des tunnels jamais servie sans token
│   └─ Téléchargement auto cloudflared si absent (GitHub releases)
├─ QR Code SVG via qrcode.image.svg, encode {urls, token, key}
│   en base64url dans le fragment d'une URL GitHub Pages
└─ Interface login HTML embarquée (servie si token absent)
```

**`relay/relay_bridge.py`** - Pont appli ↔ mobile (Singleton)
```python
Architecture:
├─ Singleton thread-safe (threading.Lock sur __new__)
├─ deque(maxlen=500) côté GUI et côté WebSocket
├─ Callbacks : on_gui_message() / on_ws_message() (enregistrables)
├─ Réponse asynchrone :
│   ├─ wait_for_ai_response(timeout=relay.response_timeout) — asyncio + run_in_executor
│   └─ submit_ai_response(text)          — appelé par le ChatService
├─ Interruption (bouton Stop du chat mobile) :
│   ├─ request_interrupt()               — posé par le handler WS
│   └─ consume_interrupt_request()       — sondé par le ChatService (core/chat_service.py)
├─ Historique session : List[RelayMessage] avec to_dict()
└─ Propriétés : active, connected_clients, history

RelayMessage (dataclass):
├─ text, is_user, timestamp, source ("relay"/"local"), message_id
├─ image_path: Optional[str]     — image consommée par le modèle vision
├─ file_paths: List[str]         — documents ajoutés au contexte vectoriel
└─ message_id auto : "{source}_{timestamp_ms}"
```

**`relay/static/`** - Interface Mobile PWA
```
├─ index.html  — Shell PWA (injecte %%RELAY_TOKEN%% côté serveur)
│                ├─ Barre d'onglets Chat / Agents (largeur égale → séparation
│                │   centrée), vues #viewChat / #viewAgents
│                ├─ bouton + et chip container (Chat ET page Agents)
│                └─ Page Agents : grille, canvas workflow (#wfCanvas/#wfWorld
│                    + SVG liens), zone résultats, modales Créer/Débat
├─ style.css   — Thème sombre, layout mobile-first, scrollbar custom
│                styles onglets, cartes agents, nœuds/ports/liens du canvas,
│                sections de sortie, modales, bouton Stop (.stopmode), liens
├─ app.js      — WebSocket client + couche E2EE :
│                ├─ Import clé AES-GCM depuis location.hash (#k=<b64u>)
│                ├─ encryptObject() / decryptEnvelope() (Web Crypto)
│                ├─ wsSendEncrypted() pour tous les envois WS
│                ├─ uploadEncryptedFile() partagé (Chat + Agents via RelayCore)
│                ├─ renderMarkdown() : code, tableaux, listes + LIENS
│                │    ([titre](url) et URLs nues → <a> bleu cliquable)
│                ├─ Bouton d'envoi ⇄ Stop pendant la génération
│                │    (stop_generation), routage des messages agent_*
│                ├─ /api/history et /api/pending : déchiffrement enveloppe
│                ├─ Indicateur de frappe, reconnexion auto, resume
│                └─ window.RelayCore : pont exposé à agents.js
└─ agents.js   — Page Agents (window.AgentsUI) :
                 ├─ Grille d'agents (built-in + custom), tap → ajout au workflow
                 ├─ Canvas n8n tactile : drag (pointer events), connexion par
                 │    tap sur les ports, courbes de Bézier SVG, statuts de nœud
                 ├─ Modales Créer/Modifier agent + Mode Débat
                 ├─ Exécution : sections dépliables remplies en streaming
                 ├─ Pièces jointes (via RelayCore.uploadEncryptedFile)
                 └─ Save/Load (localStorage) + Export (téléchargement JSON)
```

**`relay/agent_relay.py`** - Service Agents serveur (AgentRelayService)
```python
Architecture:
├─ Exécuteur partagé de la page Agents (fenêtre, mobile, scheduler), sans
│   interface, comme le mode VS Code : orchestrateur d'agents + Ollama local,
│   jamais le bridge
├─ list_agents()            — 9 built-in + custom (rechargés depuis
│                             data/custom_agents.json, partagé avec la fenêtre)
├─ create/edit/delete_agent — CRUD ; génération du system prompt via le LLM
│                             local (prompt repris de l'ancienne page Agents)
├─ compute_execution_plan() — port de WorkflowCanvas.get_execution_plan
│                             (tri topologique → single/sequential/parallel/dag)
├─ run_workflow()           — exécute le plan, streame chaque section via un
│                             callback emit ; injecte les pièces jointes
│                             (_augment_task_with_files : PDF/DOCX/Excel + vision)
├─ run_debate()             — execute_debate de l'orchestrateur, streamé
├─ Gate d'exécution unique + drapeaux d'interruption par exec_id
└─ Émission : callback thread-safe → file asyncio → drainer → WS chiffré
```

**Pipeline du chat mobile** — `core/chat_service.py`
```python
Message du mobile (RelayBridge.on_gui_message → ChatService), fenêtre ouverte ou non :
├─ Entre dans la file d'attente commune au PC et au mobile (un message à la fois)
├─ Requête par défaut si pas de texte + fichier présent
│   (« Décris cette image en détail. » / « Analyse ce fichier et résume-le. »)
├─ Chaque document est lu comme une pièce jointe du PC
│   (custom_ai.add_file_to_context), puis jamais oublié
├─ Image : encodée pour le modèle vision
└─ Même pipeline que le PC → jetons et réponse renvoyés par submit_ai_* ;
   la fenêtre, si elle est ouverte, montre l'échange en direct (badge « Mobile »)
```

### 🤖 Models - Intelligence Artificielle

**`models/custom_ai_model.py`** - Modèle IA principal
```python
Architecture:
├─ LinguisticPatterns (détection intentions)
├─ KnowledgeBase (domaines expertise)
├─ AdvancedCodeGenerator (multi-sources)
├─ ConversationMemory (persistance)
├─ InternetSearchEngine (DuckDuckGo/Yahoo/Wikipédia + Météo)
├─ Processors (PDF, DOCX, Code)
└─ VectorMemory (ChromaDB + embeddings)

Capacités clés:
├─ Détection intentions avec confiance
├─ Tracking contexte session
├─ Mémoire vectorielle sémantique
├─ Météo temps réel (Open-Meteo)
├─ Mode ultra 10M tokens
└─ Intégration processeurs avancés
```

**`memory/vector_memory.py`** - Mémoire Vectorielle
```python
Architecture ML:
├─ tiktoken (cl100k_base, compatible Llama 3)
│   └─ Comptage précis (vocabulaire aligné avec le LLM)
├─ Sentence-Transformers (all-MiniLM-L6-v2)
│   └─ Embeddings 384 dimensions
├─ CrossEncoder ms-marco-MiniLM-L-6-v2 (reranking)
│   └─ Chargé une fois depuis le cache, sans requête au Hub, et partagé
│      par toutes les instances (predict sérialisé entre threads)
├─ ChromaDB PersistentClient
│   ├─ Collections: documents, conversations
│   ├─ Backend: SQLite + Parquet
│   └─ Index: HNSW (similarité cosinus)
└─ Chiffrement AES-256 (optionnel)

Capacités:
├─ Max 10M tokens stockage
├─ Chunks 256 tokens (overlap 32, aligné all-MiniLM-L6-v2)
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
├─ clear_all() → void
├─ list_entries / get_entry / count_entries(type) → inspection par entrée
├─ update_entry(id, text, type) → bool — ré-embarque le texte modifié
└─ delete_entry(id, type) → bool — vraie suppression ChromaDB

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
├─ Connexion Ollama (http://127.0.0.1:11434 ; « localhost » perdait ≈ 2 s
│  par requête sous Windows, qui essaie d'abord l'IPv6)
├─ Vérification disponibilité serveur
├─ Détection modèle (my_ai → llama3 fallback)
├─ Génération de réponses via API
└─ Fallback automatique si Ollama indisponible

Configuration Modelfile:
├─ Modèle de base: qwen3.5:4b (ou autre selon choix)
├─ Temperature: 0.7
├─ Context window: 32768 tokens
└─ System prompt personnalisé français
```

**`models/image_generation.py`** - Génération d'images (texte → image)
```python
ImageGenerator (sortie multimodale, miroir de la vision en entrée) :
├─ Backend configurable (config.yaml → image_generation:)
│   ├─ automatic1111 : API A1111/Forge (/sdapi/v1/txt2img)
│   ├─ comfyui       : API ComfyUI (/prompt + /history)
│   ├─ diffusers     : pipeline en process (tous GPU + CPU)
│   └─ auto          : essaie a1111 → comfyui → diffusers
├─ resolve_backend() : détection HTTP + cache (calque LocalLLM)
├─ Dégradation propre si aucun backend (message clair, pas de crash)
├─ Progression (/sdapi/v1/progress, polling /history) + interruption
│   (/interrupt, ImageGenResult.interrupted, _GenerationInterrupted)
└─ Sauvegarde outputs/img_AAAAMMJJ_HHMMSS_<slug>.png

Routage : core/ai_engine.is_image_generation_request() / extract_image_prompt()
          → court-circuit prioritaire sur MCP, callbacks on_image / on_image_progress
          → « tableau » seul = tableau de données : il ne déclenche l'image
            qu'avec un style pictural (impressionniste, à l'huile…)
```

**`models/comfyui_manager.py`** - Auto-installation ComfyUI portable
```python
ComfyUIManager (zéro config, déclenché au 1er usage si auto_setup) :
├─ Détecte le GPU (Win32_VideoController) et télécharge le build ComfyUI
│   portable qui va avec : nvidia, amd ou intel (Arc) ; sans GPU reconnu,
│   nvidia sur le CPU. Python+torch embarqués dans tools/ — n'altère pas
│   l'environnement Python de My_AI. Un build qui ne correspond pas au GPU
│   est remplacé, modèles gardés
├─ Extraction .7z via 7-Zip (7zr.exe auto-téléchargé, gère le filtre BCJ2)
├─ Télécharge un modèle par défaut (SD-Turbo) si aucun checkpoint
├─ Lance ComfyUI en sous-processus + health-check (localhost:8188) ; arrêt
│   au démarrage sur le GPU → relance sur le CPU ; sortie dans logs/comfyui.log
├─ Arrêté avec l'appli (ChatService.close)
└─ Progression + interruption propagées à l'UI (même esprit que cloudflared)
```

**`models/internet_search.py`** - Moteur recherche
```python
EnhancedInternetSearchEngine :          # aucun appel au modèle
├─ search_and_summarize(query)          # résultat de l'outil web_search
│   ├─ URL dans la requête → lecture directe de la page
│   ├─ Météo → Open-Meteo (géocodage + 7 jours, sans clé)
│   └─ Sinon moteurs, puis lecture des pages
├─ Moteurs (le premier qui répond) :
│   1. DuckDuckGo (html.duckduckgo.com, sans JavaScript)
│   2. Yahoo (secours)
│   3. Wikipédia (dernier recours, articles pertinents seulement)
├─ Lecture des 4 premières pages en parallèle :
│   ├─ Texte principal sans menus, bandeaux ni publicités
│   └─ Début de page + passage le plus proche de la requête
├─ Sources numérotées [n] + bloc 📚 Sources cliquable
├─ clean_query() : requête du modèle sans les années qu'il ajoute
├─ HTTPS vérifié (truststore / network.ca_bundle), User-Agent du projet
├─ Moteur bloqué (page anti-robot) : pause de 15 min
└─ Cache des recherches : 30 min
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
├─ PyMuPDF (pymupdf) - Primaire (recommandé)
└─ PyPDF2 - Fallback

Processing:
├─ Extraction texte page par page
├─ OCR des pages sans couche texte (processors/ocr.py)
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

**`processors/pptx_processor.py`**
```python
Librairie: python-pptx (.pptx et modèles .potx ; .ppt binaire non lisible)

Processing:
├─ Une entrée par diapositive : titre, puces avec leur niveau, tableaux, notes
├─ Représentation texte pour le contexte (« --- Diapositive N --- »)
├─ .potx : type de contenu remplacé en mémoire (python-pptx le refuse)
└─ Chemins OneDrive via processors/path_resolution.py (partagé avec DOCX)

Output:
{
  "success": True,
  "content": {"text": str, "slides": [...], "properties": {...}},
  "file_info": {"original_path": str, "resolved_path": str, "size": int}
}
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

**`processors/attachments.py`**
```python
Pièces jointes des agents (page Agents de la fenêtre + Relay mobile):
├─ read_attachment_text(file_path, file_type="") → texte
├─ PDF → PDFProcessor, DOCX → DOCXProcessor, PPTX/POTX → PPTXProcessor
├─ XLSX/XLS/CSV → ExcelProcessor
├─ Autres fichiers (code, texte, markdown) → lecture directe (200 000 caractères max)
└─ Document illisible ou PDF sans texte reconnu → ValueError (jamais d'octets bruts dans le prompt)
```

**`processors/ocr.py`**
```python
OCR des pages PDF scannées (PDF d'images, sans couche texte):
├─ RapidOCR : modèles ONNX inclus dans le paquet, hors ligne, accents français
├─ ocr_page(page) : page PyMuPDF rendue à 200 dpi puis reconnue
├─ Appelé par PDFProcessor pour chaque page sans texte (chat, agents, indexation RAG)
├─ Cache par fichier + date de modification + page (le chat lit chaque PDF deux fois)
├─ interruptible(cancel) : dans ce bloc et ce thread, OcrInterrupted avant la page
│  suivante dès que cancel est levé (pièce jointe retirée pendant sa lecture) ;
│  PDFProcessor la laisse remonter, sans repli sur PyPDF2 ni pdfplumber
└─ rapidocr absent → MISSING_OCR_HINT au lieu de « vide ou illisible »
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

**`generators/document_generator.py`** - Documents bureautiques
```python
generate_document(brief, fmt, title, content, filename, research)
├─ Rédaction du corps en Markdown par le LLM (sauf content fourni),
│  enrichie des résultats de recherche du tour (research)
├─ markdown_document.parse_markdown() → blocs (Heading, ListBlock, Table…)
├─ Un backend par format :
│   ├─ docx : python-docx (listes imbriquées, tableaux, sommaire TOC)
│   ├─ pdf  : reportlab platypus (styles, tableaux, numérotation)
│   ├─ pptx : python-pptx (une diapo par section, découpe > 9 puces)
│   ├─ xlsx : openpyxl (un onglet par tableau, filtre, vrais nombres)
│   └─ md / txt / csv / html
└─ outputs/documents/ → {success, file_path, format, title, size, outline}

Exposé au chat par l'outil MCP generate_document (AIEngine._setup_local_tools)
```

**`generators/document_editor.py`** - Modification de documents
```python
DocumentEditor.edit(path, operations, output_name) — toujours sur une copie
├─ replace_text · append_markdown · replace_section · delete_paragraph
├─ set_cell · append_row (xlsx) · append_slide (pptx)
├─ Remplacement run par run : la mise en forme de l'occurrence est conservée
├─ PDF : texte extrait, puis nouveau PDF régénéré
└─ outputs/documents/<nom>_modifie.<ext> (compteur si la copie existe)

Exposé au chat par l'outil MCP edit_document
```

**`generators/markdown_document.py`** - Parseur Markdown → blocs, socle commun
des backends de rendu et de l'aperçu HTML des documents. Détails :
[DOCUMENT_GENERATION.md](DOCUMENT_GENERATION.md).

### 🖥️ Interfaces - UI

**Fenêtre desktop** — interface web (`frontend/`) servie par un serveur local (`interfaces/desktop/`)
```
Architecture:
├─ frontend/ : React 19 + TypeScript strict (Vite), Tailwind CSS v4 branché sur
│  les jetons de src/styles/tokens.css, état Zustand ; build versionné dans
│  frontend/dist/ (les utilisateurs n'ont pas besoin de Node)
├─ window.py : fenêtre pywebview (WebView2, le Chromium d'Edge, sous Windows ;
│  GTK ou Qt ailleurs) ; sans pywebview, l'interface s'ouvre dans le navigateur
├─ server.py : FastAPI sur 127.0.0.1 seulement, port libre, REST + un WebSocket ;
│  jeton tiré à chaque lancement (passé dans le fragment de l'URL), Origin et
│  Host vérifiés ; distinct du serveur Relay, jamais exposé par les tunnels
├─ lifecycle.py : la fenêtre s'ouvre tout de suite sur l'écran de chargement ;
│  un fil enchaîne les étapes du lanceur (modèle des longs documents, Ollama,
│  assistant de premier lancement, my_ai, placement), puis moteur, chat,
│  Relay et scheduler. Rien n'appelle Ollama avant la fin du placement
└─ shell_api.py : seul pont entre la page et la fenêtre (dialogues de fichiers,
   ouvrir un fichier ou un lien, visionneuses Office) ; lib/shell.ts côté page

Sécurité:
├─ Liens externes ouverts dans le navigateur du système : la fenêtre ne quitte
│  jamais l'appli (navigation annulée, nouvelles fenêtres refusées)
├─ Markdown des réponses rendu sans HTML brut ; URL non web neutralisées
├─ Artifacts HTML/SVG dans une <iframe sandbox> sans allow-same-origin : ni
│  l'API ni la page de l'appli ne leur sont accessibles
└─ Fichiers locaux servis par liens signés (HMAC), seulement pour les chemins
   que le serveur connaît ; un chemin cité dans une réponse se montre dans
   l'Explorateur, jamais exécuté (utils/path_links.py)
```

**Protocole** — `interfaces/desktop/events.py` (Pydantic) ↔ `frontend/src/lib/events.ts`
```
Chaque événement : type, conversation_id, message_id, seq (croissant), payload
├─ Chat : message.user (source desktop ou mobile), assistant.start / token /
│  thinking / thinking_done / done / error / interrupted
├─ Outils et fichiers : tool.call, tool.result, confirm.request,
│  document.created, image.progress, image.created
├─ Appli : engine.status, relay.status, scheduler.result, resources.sample,
│  voice.*, notification
├─ Agents : agents.* (événements d'AgentRelayService, texte des sections en suite)
└─ Client → serveur (WebSocket) : chat.send, chat.stop, chat.cancel,
   confirm.response ; agents, voix et panneaux passent par l'API REST
Reconnexion : la page relit l'état complet (REST), puis reprend le flux (seq).
```

**`core/chat_service.py`** - Service de chat sans interface
```python
Rôle: Pipeline du chat, pour la fenêtre et pour le mobile (fenêtre ouverte ou non)
├─ Mêmes appels au moteur que l'ancienne interface, dans le même ordre : slash
│  commands, documents visibles, génération de fichier ou d'image, puis
│  process_query_stream. Ollama reprend ainsi le prompt déjà lu (OPTIMIZATION.md)
├─ File d'attente commune desktop / mobile : un message à la fois, Stop arrête
│  le message en cours
├─ Pièces jointes lues en arrière-plan ; envoi refusé tant qu'une lecture dure
├─ Sessions au format data/workspaces/ (conversation_history, turn_branches),
│  sauvegardées après chaque tour, rouvertes au lancement
└─ Branches d'édition ‹ k/n › : modifier et régénérer gardent les variantes
```

**Rendu du chat** (`frontend/src/features/chat/`)
```
├─ Liste virtualisée (react-virtuoso) ; défilement collé en bas, sauf si
│  l'utilisateur est remonté (bouton « ↓ ») ; un message envoyé ramène en bas
├─ Jetons regroupés à chaque image affichée ; seul le dernier bloc Markdown
│  est re-rendu (react-markdown + remark-gfm, blocs terminés mémoïsés)
├─ Coloration du code par Shiki dans un Web Worker ; formules KaTeX chargées à
│  la demande
└─ Réflexion repliable, appels d'outils en lignes compactes, citations [n] et
   chemins de fichiers cliquables
```

**Panneaux** — dialogues internes à la fenêtre
```
├─ Réglages (settings.py, model_setup.py) : modèles Ollama (téléchargement,
│  application qui recrée my_ai), température, num_ctx, timeout, langue,
│  lecture automatique, Relay au lancement ; config.yaml garde ses commentaires
├─ Mémoire (memory.py, via core/memory_store.py) : Faits (SQLite), Documents et
│  Conversations (ChromaDB), recherche, filtre, pagination, provenance,
│  édition et suppression confirmée (« supprimer aussi le message d'origine »)
├─ Prompts (prompts.py, via core/prompt_library.py) : templates et commandes /xxx
├─ Relay : démarrage (Ctrl+R), état de chaque tunnel, QR code (qr.py), URL et
│  chaîne de connexion VS Code
├─ Aide (F1) et palette de commandes (Ctrl+K, cmdk)
└─ Assistant de premier lancement (model_setup.py, fonctions de
   interfaces/onboarding.py), affiché à son étape du lancement
```

**Volet d'aperçu** — `previews.py`, `native_viewer.py`, `preview_handler.py`, `dpi_host.py`
```
├─ Artifacts HTML/SVG : page /preview/<id> dans l'iframe sandbox, onglets
│  Aperçu et Code, ouverture dans le navigateur, ouverture automatique
├─ PDF : lecteur natif de WebView2, dans la page
├─ Word, Excel, PowerPoint : visionneuses de Windows (IPreviewHandler, COM,
│  thread STA dédié) dans une fenêtre enfant posée au-dessus de WebView2 sur la
│  place que la page réserve (position et taille en pixels physiques) ; masquée
│  sous les menus, dialogues et notifications ; hôte « popup » DPI par écran
│  (dpi_host.py) en repli si la fenêtre n'est pas DPI par écran
└─ Ailleurs, ou sans visionneuse : aperçu HTML (interfaces/document_preview.py)
```

**Page Agents** — `agents.py`, `schedule.py`, `resources.py` ; `frontend/src/features/agents/`
```
├─ Un seul exécuteur partagé (relay/agent_relay.py, AgentRelayService) : page
│  Agents, mobile et scheduler (ces deux derniers à travers SharedExecutor)
├─ Chaque exécution (agent, workflow, débat) devient un fil, gardé dans
│  data/agent_runs.json (les 50 derniers), statut en direct, Arrêter ;
│  une sortie qui modifie un code joint s'ouvre en diff
├─ Canvas de workflow React Flow (@xyflow/react) : glisser un agent, relier les
│  ports, zoom, grille, minimap, liens animés pendant l'exécution ; fichiers au
│  format JSON de l'ancien canvas ({"nodes": {...}, "connections": [...]})
├─ Débat entre deux agents, statistiques, moniteur de ressources
│  (interfaces/resource_monitor.py, une mesure toutes les 3 s)
└─ Tâches planifiées (core/scheduler.py) et notification de fin d'un fil long
```

**Voix** — `voice.py`, `voice_input.py`, `voice_output.py`
```
├─ Saisie : faster-whisper (modèle small, int8, CPU) et sounddevice, capture et
│  transcription côté Python ; la page ne fait que démarrer, arrêter, afficher
└─ Lecture : pyttsx3 (SAPI5, NSSpeechSynthesizer, espeak), voix par langue,
   lecture automatique (ui.tts_autoread)
```

**`interfaces/desktop/_whisper_worker.py`** - Transcription isolée (process séparé)
```python
Rôle: Exécuter faster-whisper hors du process applicatif sur macOS
├─ Problème : ctranslate2, torch et scikit-learn embarquent chacun un runtime
│  OpenMP ; leur cohabitation segfaulte le pool de threads de ctranslate2
│  (EXC_BAD_ACCESS dans __kmp_fork_barrier, sans « OMP: Error #15 » car
│  sklearn/threadpoolctl posent KMP_DUPLICATE_LIB_OK=True)
├─ torch est inévitable : ctranslate2 l'importe lui-même. Le worker exclut
│  scikit-learn, qui apporte le troisième runtime (libomp, LLVM)
├─ Process persistant : modèle chargé une fois, protocole JSON + float32 brut
│  sur stdin/stdout
└─ ⚠️ Lancé PAR CHEMIN, jamais par « -m » : le __init__.py d'un package
   pourrait importer toute la pile applicative dans le worker

Déclenchement (voice_input.py) :
├─ _openmp_runtimes() : inventaire via _dyld_image_count (macOS seulement)
├─ > 1 runtime -> process isolé ; sinon en interne (Windows/Linux inchangés)
├─ Forçage manuel : MY_AI_WHISPER_WORKER=1 / =0
└─ Repli si le worker échoue : en interne avec cpu_threads=1 (~1.8x plus lent)
```

**Développement**
```
├─ launch_unified.py --dev : fenêtre sur le serveur Vite (rechargement à chaud,
│  devserver.py) ; « npm run dev » dans frontend/
├─ launch_unified.py --headless : serveur et moteur sans fenêtre (tests)
├─ tools/interface_web/demo_server.py : serveur de démonstration sans Ollama
└─ frontend/scripts/ : vérifications Playwright (captures, mesures, vraie fenêtre)
```

**`interfaces/document_preview.py`** - Rendu HTML des documents
```python
build_document_preview(path) -> str : docx, xlsx, pptx, md, csv, txt, pdf (texte)
├─ Rendu de repli du volet (sans visionneuse native) et contenu de la modale mobile
└─ Réutilise les processeurs de lecture (DOCX, Excel, PPTX, PDF)
```

Détails de l'aperçu : [ARTIFACTS_PREVIEW.md](ARTIFACTS_PREVIEW.md).

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

**`vscode_extension/`** - Extension VS Code (client Relay distant + agent codant)
```
vscode_extension/
├─ package.json             # Manifest, commandes, vues, settings
├─ src/
│  ├─ extension.ts          # Entrée : commandes, status bar, activation
│  ├─ connectionManager.ts  # SecretStorage, état, health-check, hello vscode,
│  │                        #   forward des tool_use → ToolDispatcher
│  ├─ relayClient.ts        # WebSocket E2EE, multi-tunnel failover, upload,
│  │                        #   client_hello, sendToolResult
│  ├─ chatViewProvider.ts   # WebviewView (sidebar) + bridge postMessage
│  ├─ workspaceBridge.ts    # Auto-attach, send selection, insert at cursor
│  ├─ agentTools.ts         # 9 outils workspace (read/write/edit/list/glob/
│  │                        #   grep/run_command/get_active_editor/open_file)
│  │                        #   avec sandbox path-resolution
│  ├─ toolDispatcher.ts     # Politique d'approbation (auto pour read-only,
│  │                        #   modal pour les opérations destructives,
│  │                        #   options "session"/"par fichier")
│  ├─ connectionString.ts   # Parse router.html#d=<base64(json)>
│  ├─ crypto.ts             # AES-256-GCM (Node webcrypto)
│  └─ types.ts
├─ media/                   # Webview UI (HTML/CSS/JS, no bundling)
│  ├─ chat.html
│  ├─ chat.css              # Adapté de relay/static/style.css
│  ├─ chat.js               # Rendu des messages + cartes d'outils inline
│  └─ icon-activitybar.svg
└─ README.md                # Doc Marketplace

Architecture : l'extension est un *client Relay* (au même titre que la PWA mobile),
mais à la connexion elle envoie un message chiffré
`client_hello { client_kind: "vscode" }` qui fait basculer le Relay côté hôte
vers la boucle agentique (`core/agentic_executor.py`). Cette boucle appelle
Ollama directement, parse les balises `<tool_use>{...}</tool_use>` du modèle,
et envoie chaque outil au client via WebSocket (`tool_use` chiffré). Le
client exécute l'outil dans son `ToolDispatcher` (avec sandbox + approbation)
puis renvoie le résultat via `tool_result`. Le LLM continue ses itérations
jusqu'à produire une réponse finale. Le mobile n'envoie pas de
`client_hello` → il reste sur le pipeline historique (bridge → service de chat
de l'appli, avec MCP locaux complets).
```

**`interfaces/resource_monitor.py`** - Monitoring ressources système
```python
Architecture: thread daemon avec collecte périodique (3s)

Sources:
├─ psutil: CPU% et RAM d'Ollama et des processus qu'il lance (llama-server)
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
tools/local_tools.py — outils locaux (fonctions, exposées via le client MCP):
├─ local_math(expr)           : évaluation d'expressions / calculatrice
├─ local_search(pattern,      : recherche récursive de fichiers par motif
│    folder=".")
├─ extract_emails(text)       : extraction d'adresses e-mail
└─ extract_dates(text)        : extraction de dates
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

utils/requirements_sync.py:
├─ sync_requirements() : appelé tout en haut de launch_unified.py et main.py,
│  avant les imports qui ont besoin des paquets (bibliothèque standard + packaging)
├─ Installe avec pip les lignes de requirements.txt non satisfaites (paquet
│  absent ou version hors bornes, marqueurs de plateforme évalués) : les
│  dépendances ajoutées par un git pull arrivent au lancement suivant
├─ Vérification refaite seulement si requirements.txt a changé (empreinte
│  SHA-256 par interpréteur dans data/.requirements_sync.json) : 0,4 ms sinon
├─ Une ligne qui échoue n'empêche pas les autres (nouvel essai ligne par ligne)
│  et n'est retentée qu'au prochain changement du fichier
├─ .dist-info vidés par une installation interrompue ignorés
└─ Désactivation : MY_AI_SKIP_DEPS_SYNC=1 ; ignoré dans un exécutable figé

utils/path_links.py:
├─ find_existing_paths(text) : plus long préfixe qui existe sur le disque
│  (les chemins Windows contiennent des espaces)
├─ Lecteurs locaux seulement : un lecteur réseau déconnecté figerait l'UI
└─ reveal_in_file_manager(path) : explorateur, fichier sélectionné

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
    ├─ .pptx/.potx  → PPTXProcessor
    ├─ .xlsx/.xls   → ExcelProcessor (openpyxl / xlrd)
    ├─ .csv         → ExcelProcessor (stdlib csv)
    └─ .py/.js/...  → CodeProcessor
    ↓
Content Extraction
    ↓
Chunking (256 tokens)
    ↓
Store in ConversationMemory
    ↓
Add to VectorMemory
    ↓
User can query: "résume ce document"
```

### 3. Flux Génération de Document

```
"génère un pdf sur les dauphins"
    ↓
ChatOrchestrator.run() (boucle d'outils MCP)
    ├─ Réponse texte qui annonce le document sans outil ? → une relance
    ├─ Recherche éventuelle → résultats mémorisés (_remember_research)
    ↓
Outil generate_document → DocumentGenerator.generate_document()
    ├─ Rédaction Markdown (LLM) → parse_markdown() → backend du format
    └─ outputs/documents/<titre>.pdf
    ↓
on_document(path) → bouton « 🔍 Aperçu » + ouverture automatique du volet
    │               (Relay : événement ai_document chiffré)
    ↓
Synthèse streamée : présentation du document d'après son plan
```

### 4. Flux Génération Code

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

### 5. Flux RLHF Training

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

### 6. Flux Recherche Internet

```
Le modèle appelle web_search(query)
    ↓
clean_query : sa requête, sans les années qu'il a ajoutées
    ↓
DuckDuckGo → Yahoo → Wikipédia (le premier qui répond)
    ↓
8 sources max, 2 par site ; 4 pages lues en parallèle
    ↓
Passages pertinents de chaque page
    ↓
Sources numérotées + bloc 📚 Sources → le modèle
    ↓
Synthèse streamée, liens des sources cliquables
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
├── knowledge_base/         # Base de faits (SQLite)
├── web_cache/              # Cache des recherches web
├── workspaces/             # Espaces de travail sauvegardés
├── outputs/                # Documents/code générés
└── logs/                   # Logs application

memory/
├── vector_store/           # Mémoire vectorielle
│   ├── chroma_db/         # ChromaDB persistant (ignoré Git)
│   │   ├── chroma.sqlite3 # Metadata
│   │   └── *.parquet      # Vecteurs
│   └── README.md          # Documentation système
└── vector_memory.py        # Gestionnaire mémoire
```

## 🚀 Points d'Entrée

### `launch_unified.py` - Launcher recommandé
```python
# Entry: main()
# Ouvre la fenêtre (pywebview) tout de suite, sur l'écran de chargement
# Étapes (interfaces/desktop/lifecycle.py) : modèle des longs documents,
#   redémarrage d'Ollama, assistant, my_ai, placement, puis moteur et services
# --dev : interface servie par Vite ; --headless : serveur et moteur sans fenêtre
# Sans pywebview : interface ouverte dans le navigateur
```

### `main.py` - Launcher complet CLI
```python
# Modes supportés:
python main.py                        # CLI interactif
python main.py --mode gui             # Fenêtre seule (Ollama tel qu'il tourne)
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

### `launch.sh` - Script macOS / Linux
```bash
# Équivalent POSIX de launch.bat (même menu)
# Sous Linux, signale l'absence de GTK ou de Qt (fenêtre) : repli sur le navigateur
# Bloque Python 3.13+ sur Mac Intel (torch x86_64 plafonne à 2.2.2)
```

## ⚡ Performances et Caractéristiques

### Temps Réponse Typiques
```
Greeting response:        < 100ms
Simple conversation:      500ms - 2s
Météo Open-Meteo:         ~0,5s (API externe)
Code generation:          2-5s (web search inclus)
Document processing:      Variable (50MB PDF ≈ 10-20s)
Internet search:          2-5s (moteur + 4 pages)
Vector search (10M tokens): <20ms (ChromaDB HNSW)
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
Context window standard:  32768 tokens
Context ultra mode:       10,485,760 tokens (10M)
Chunk size VectorMemory:  256 tokens (aligné all-MiniLM-L6-v2)
Chunk overlap:            32 tokens (~12%, contexte préservé)
Embedding dimensions:     384 (all-MiniLM-L6-v2)
Search speed:             <20ms pour 10M tokens
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
- `ULTRA_10M_TOKENS.md` - Détails contexte 10M
- `MEMORY.md` - Contrôle de la mémoire (voir/éditer/supprimer faits + vecteurs)
- `CONVERSATION_SEARCH.md` - Recherche sémantique globale cross-conversations
- `INTERNET_SEARCH.md` - Fonctionnalités recherche
- `ARTIFACTS_PREVIEW.md` - Panneau « Artifacts » (aperçu live HTML/CSS/SVG + documents)
- `DOCUMENT_GENERATION.md` - Génération et modification de documents bureautiques
- `FAQ.md` - Questions fréquentes
- `CHANGELOG.md` - Historique versions

---

**Version**: 9.0.0
**Architecture**: Modulaire, extensible, 100% locale
**Capacité contexte**: 10,485,760 tokens avec recherche sémantique
**Interfaces**: fenêtre desktop (React + TypeScript, pywebview), CLI, Mobile PWA (Relay), Extension VS Code (TypeScript, Marketplace)
