## Dossier core/

Ce dossier contient les composants centraux (backend) de l'assistant IA local. Les modules sont conçus pour fonctionner en mode local (sans dépendance obligatoire à des services externes) et exposent souvent une interface CLI via une fonction `main()`.

Contenu principal
-----------------

- `ai_engine.py` — Moteur principal. Orchestration des composants (mémoire de conversation, processeurs de fichiers, générateurs, gestion des requêtes, routage vers recherche web ou génération de code). Expose des méthodes comme `process_text`, `process_message`, `process_query` et plusieurs helpers privés.
- `config.py` — Configuration par défaut (dictionnaires `AI_CONFIG`, `FILE_CONFIG`, `UI_CONFIG`) et la classe `Config` pour charger/sauvegarder une configuration YAML (`config.yaml`).
- `context_manager.py` — Outils pour gérer le contexte long (fenêtre glissante, résumé simple), sauvegarde/chargement de mémoire locale (JSONL) et utilitaires CLI.
- `conversation.py` — `ConversationManager` : historique des échanges, sessions, sérialisation, et formatage du contexte pour les LLM.
- `data_preprocessing.py` — Fonctions de nettoyage et pipeline de prétraitement pour datasets (`clean_text`, `load_dataset`, `preprocess_dataset`) pour JSONL et CSV.
- `error_analysis.py` — Scripts utilitaires pour analyser erreurs, générer rapports d'évaluation et produire un JSON de rapport.
- `evaluation.py` — Outils et CLI pour évaluer un modèle local sur un jeu de tests (chargement de modèle `.py`, calcul des métriques: exact match, precision, recall, f1).
- `optimization.py` — Outils CLI pour optimiser des modèles locaux (quantization, pruning, etc.) et loader générique de modèles.
- `rlhf.py` — Boucle RLHF (collecte de feedback humain, génération de sorties, réentraînement basique). Fonctions pour interagir en CLI.
- `rlhf_feedback_integration.py` — Scripts pour intégrer automatiquement les feedbacks RLHF dans le dataset d'entraînement.
- `training_pipeline.py` — Pipeline d'entraînement/fine-tuning local (chargement dataset, boucles d'entraînement, checkpoints, sauvegarde).
- `__init__.py` — Initialisation du package `core`.

Exécution / exemples rapides
---------------------------

La plupart des fichiers exposent une interface CLI via `if __name__ == '__main__': main()`.
Exemples (depuis la racine du projet) :

```powershell
python .\core\data_preprocessing.py --input data/train.jsonl --output data/train_clean.jsonl
python .\core\training_pipeline.py --model models/my_model.py --trainset data/train_clean.jsonl --epochs 3
python .\core\evaluation.py --model models/my_model.py --testset data/test.jsonl --save_metrics outputs/metrics.json
python .\core\rlhf.py --model models/my_model.py --dataset data/samples.jsonl
```

Dépendances
-----------

Certains modules utilisent des bibliothèques externes (ex: `yaml` dans `config.py`). Installez les dépendances du projet :

```powershell
pip install -r requirements.txt
```

Notes et bonnes pratiques
------------------------

- Les scripts sont orientés « gabarits » et stubs : ils attendent souvent que le modèle local fourni (`.py`) expose une interface standard (`LocalModel`, `predict`, `train`, `optimize`, etc.).
- `AIEngine` est le point d'entrée pour l'orchestration : il utilise `ConversationManager`, des processeurs (PDF/DOCX/Code), et des générateurs (documents, code).
- Les dossiers `outputs/`, `temp/`, `backups/` sont utilisés par défaut pour sauvegarder résultats et fichiers temporaires (voir `config.py` pour les chemins configurables).
- Le code privilégie le fonctionnement 100% local (mode `local_mode` dans `config.py`).

Besoin d'une mise à jour ?
-------------------------
Si vous ajoutez ou modifiez des modules dans `core/`, mettez à jour ce README pour garder la documentation synchronisée.
