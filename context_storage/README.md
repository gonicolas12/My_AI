# Dossier context_storage

Ce dossier contient les fichiers de base de données utilisés par l'IA du projet :

- `ultra_context.db` : stocke le contexte, les chunks, et la mémoire de l'IA.
- `code_solutions_cache.db` : stocke le cache des solutions de code générées ou analysées.
- `code_cache.json` : autre stock des solutions de code générées.

Ces fichiers sont créés et utilisés automatiquement par le projet pour la persistance des données et l'optimisation des performances.

Ce dossier peut être vidé lors d'un nettoyage du projet (script de clean), ce qui réinitialise la mémoire et le cache.