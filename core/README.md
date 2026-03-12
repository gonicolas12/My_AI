## Dossier core/

Ce dossier contient les composants centraux (backend) de l'assistant IA local. Les modules sont conçus pour fonctionner en mode local (sans dépendance obligatoire à des services externes) et exposent souvent une interface CLI via une fonction `main()`.

Contenu principal
-----------------

### Orchestration & Moteur IA

- `ai_engine.py` — Moteur principal. Orchestration de tous les composants (mémoire de conversation, processeurs de fichiers, générateurs, gestion des requêtes, routage vers recherche web ou génération de code). Expose `process_text`, `process_message`, `process_query_stream` et plusieurs helpers privés. Délègue le tool-calling à `ChatOrchestrator`.
- `chat_orchestrator.py` — `ChatOrchestrator` : boucle agentique avancée pour la page Chat. Remplace l'appel direct à `LocalLLM.generate_with_tools_stream()` dans `AIEngine.process_query_stream()`. Implémente trois design patterns :
  - **ReAct** (Reasoning + Acting) : boucle `Réfléchis → Agis → Observe` à chaque tour.
  - **Plan & Execute** : génération d'un plan structuré en étapes pour les requêtes > 55 caractères.
  - **Scratchpad persistant** : état interne (objectif, plan, étape, faits collectés, tours restants) injecté dans le system prompt sous forme de bloc XML.
  - Sécurités intégrées : limite de tours (`MAX_TOURS = 15`), `LoopDetector` (boucle immédiate + boucle élargie), élagage sélectif du contexte (`MAX_HISTORY_MESSAGES = 40`), validation des arguments outils, synthèse forcée après `MAX_TOOL_USES = 5`.
- `agent_orchestrator.py` — `AgentOrchestrator` : coordonne les agents IA spécialisés (page Agents). Gère la création à la demande des agents (`get_or_create_agent`), l'historique des tâches et l'exécution de workflows multi-agents. **Distinct** de `ChatOrchestrator` (usage exclusif page Agents).
- `mcp_client.py` — Client MCP (Model Context Protocol). Expose les outils locaux au format MCP standardisé et permet la connexion à des serveurs MCP externes via le transport `stdio`. Utilisé par `AIEngine` pour étendre les capacités d'Ollama.

### Configuration & Données

- `config.py` — Configuration par défaut (dictionnaires `AI_CONFIG`, `FILE_CONFIG`, `UI_CONFIG`) et la classe `Config` pour charger/sauvegarder `config.yaml`. La clé `llm.local.default_model` est la **source unique** du nom de modèle.
- `shared.py` — Module anti-import-circulaire. Contient le **modèle d'embeddings partagé** (`all-MiniLM-L6-v2` via `sentence_transformers`) chargé une seule fois au démarrage (stratégie offline-first puis online) pour éviter de l'instancier plusieurs fois dans les différents modules.
- `validation.py` — Validation Pydantic de toutes les entrées utilisateur. `UserQueryInput` vérifie longueur, caractères dangereux (injections `eval`, `exec`, `os.system`, etc.) et contexte additionnel. `ToolArgumentsInput` valide les arguments des appels d'outils.

### Gestion du Contexte & Conversation

- `context_manager.py` — Outils pour gérer le contexte long (fenêtre glissante, résumé simple), sauvegarde/chargement de mémoire locale (JSONL) et utilitaires CLI.
- `conversation.py` — `ConversationManager` : historique des échanges, sessions, sérialisation, et formatage du contexte pour les LLM.

### Apprentissage & RLHF

- `rlhf_manager.py` — `RLHFManager` : collecte automatique du feedback utilisateur (scores 0-5), détection de patterns succès/échec, statistiques de satisfaction, export des données d'entraînement JSONL. Singleton partagé via `get_rlhf_manager()`.
- `training_manager.py` — `TrainingManager` : gestion de l'entraînement et du fine-tuning de modèles locaux avec monitoring en temps réel (checkpoints, métriques, export).
- `training_pipeline.py` — Pipeline d'entraînement/fine-tuning local (chargement dataset, boucles d'entraînement, checkpoints, sauvegarde).
- `data_preprocessing.py` — Fonctions de nettoyage et pipeline de prétraitement pour datasets (`clean_text`, `load_dataset`, `preprocess_dataset`) pour JSONL et CSV.

### Monitoring & Évaluation

- `compression_monitor.py` — `CompressionMonitor` : analyse l'efficacité du chunking et de la compression en temps réel. Calcule les ratios de compression par type de contenu, maintient un historique et génère des rapports.
- `evaluation.py` — Outils et CLI pour évaluer un modèle local sur un jeu de tests (exact match, precision, recall, F1).
- `error_analysis.py` — Scripts utilitaires pour analyser erreurs, générer rapports d'évaluation et produire un JSON de rapport.
- `optimization.py` — Outils CLI pour optimiser des modèles locaux (quantization, pruning, etc.) et loader générique de modèles.

### Infrastructure

- `__init__.py` — Initialisation du package `core`.

Exécution / exemples rapides
---------------------------

La plupart des fichiers exposent une interface CLI via `if __name__ == '__main__': main()`.
Exemples (depuis la racine du projet) :

```powershell
# Prétraitement
python .\core\data_preprocessing.py --input data/train.jsonl --output data/train_clean.jsonl

# Entraînement
python .\core\training_pipeline.py --model models/my_model.py --trainset data/train_clean.jsonl --epochs 3

# Évaluation
python .\core\evaluation.py --model models/my_model.py --testset data/test.jsonl --save_metrics outputs/metrics.json
```

Dépendances
-----------

Certains modules utilisent des bibliothèques externes (ex: `yaml` dans `config.py`, `pydantic` dans `validation.py`). Installez les dépendances du projet :

```powershell
pip install -r requirements.txt
```

Notes et bonnes pratiques
------------------------

- **Point d'entrée principal** : `AIEngine` orchestre tous les modules. Tout tool-calling passe par `ChatOrchestrator` (page Chat) ou `AgentOrchestrator` (page Agents) — ces deux orchestrateurs sont **indépendants** et ne se partagent pas.
- **Modèle partagé** : `shared.py` expose le modèle d'embeddings `all-MiniLM-L6-v2` via `get_shared_embedding_model()` pour éviter de le charger plusieurs fois (important pour les performances de démarrage).
- **Source unique du modèle LLM** : Seul `config.yaml` (clé `llm.local.default_model`) définit le modèle Ollama. Ne pas le dupliquer dans d'autres fichiers.
- **Sécurité des entrées** : utiliser `validation.py` (Pydantic) pour valider toutes les entrées utilisateur et les arguments d'outils avant de les transmettre au LLM.
- Les dossiers `outputs/`, `temp/`, `backups/` sont utilisés par défaut pour sauvegarder résultats et fichiers temporaires (voir `config.py` pour les chemins configurables).
- Le code privilégie le fonctionnement 100% local (mode `local_mode` dans `config.py`).

Besoin d'une mise à jour ?
-------------------------
Si vous ajoutez ou modifiez des modules dans `core/`, mettez à jour ce README pour garder la documentation synchronisée.
