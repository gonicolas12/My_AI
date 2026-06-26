# 📁 Contexte projet « @codebase » — attacher un dossier entier

Attachez un **dossier complet** (codebase ou dossier de documentation) à un workspace : l'IA garde ce contexte **disponible en permanence** pour **toutes** les questions du workspace, sans avoir à re-glisser les fichiers à chaque fois. C'est le principe **`@codebase`**. **100% local** : l'indexation réutilise votre mémoire vectorielle existante, rien ne part sur le réseau.

---

## 📍 Où la trouver

| Surface | Comment |
|---|---|
| **GUI desktop** | Sidebar (**☰**) → section **📁 Dossiers du projet** → **Attacher un dossier**. Ou menu **« + »** → **📁 Dossier (codebase)**. |
| **Extension VS Code** | Tapez **`@`** dans le chat → choisissez un dossier (ou un fichier). Ou *Command Palette* → **Attach Folder as @codebase** / clic droit sur un dossier de l'Explorateur. |
| **Mobile (Relay)** | Le contexte attaché côté PC s'applique aux questions envoyées depuis le mobile pour le même workspace. |

---

## ✨ Ce qu'il fait

- **Contexte projet persistant** : une fois un dossier attaché, chaque question du workspace bénéficie automatiquement des passages pertinents (RAG au moment de la question) — plus besoin de joindre les fichiers un par un.
- **Lié au workspace** : changer de workspace change le contexte projet actif. Vous pouvez attacher **plusieurs** dossiers à un même workspace.
- **Incrémental** : réindexer ne retraite que les fichiers **nouveaux ou modifiés** ; les fichiers supprimés sont retirés de l'index.
- **Propre** : respecte votre `.gitignore` et ignore d'office les dossiers de bruit (`node_modules`, `.git`, `.venv`, `dist`, `build`, caches…).

---

## 🗂️ Ce qui est indexé

- **Formats** : tout ce que gèrent les processeurs de fichiers existants — code, texte, **PDF**, **DOCX**, **Excel/CSV**, Markdown, etc.
- **Exclusions automatiques** : `.git`, `node_modules`, `__pycache__`, `.venv`/`venv`, `dist`, `build`, `out`, `target`, `.idea`, `.vscode`, caches divers… **en plus** des règles de votre `.gitignore`.
- **Limite par fichier** : 2 Mo (au-delà, c'est en général un binaire/asset/dump, pas du contexte utile → sauté).
- **Un fichier ciblé** : vous pouvez attacher **un seul fichier** (ex. via le menu `@` de VS Code) sans indexer tout son dossier.

---

## 🔁 Indexation incrémentale (comment ça reste rapide)

Un **manifeste par workspace** (`data/workspaces/<id>/folder_index.json`) mémorise pour chaque fichier son `mtime`, sa `taille` et son `hash` :

1. **Chemin rapide** — `mtime` + taille inchangés → le fichier est gardé tel quel (aucun retraitement).
2. **Repli sur le hash** — `mtime`/taille différents mais contenu identique (ex. après un `git checkout`) → pas de ré-embedding.
3. **Sinon** — le fichier est ré-indexé (ses anciens chunks sont purgés puis recréés).
4. **Fichiers disparus** → leurs chunks sont supprimés de l'index.

Un numéro de **schéma d'indexation** force une réindexation complète si la logique d'indexation évolue.

---

## 🏗️ Sous le capot

```
core/folder_indexer.py  ── FolderIndexer
   ├─ collection ChromaDB dédiée « codebase » (VectorMemory partagée)
   │     chunks étiquetés : workspace_id / folder_path / file_path
   ├─ réutilise FileProcessor + VectorMemory.split_into_chunks  (zéro nouveau pipeline)
   ├─ respect .gitignore (pathspec, sinon matcher intégré) + exclusions par défaut
   ├─ index_folder / index_single_file / index_path / reindex
   ├─ remove_folder / list_folders / get_status
   └─ search(workspace_id, query)  → filtre par workspace + rerank CrossEncoder

core/ai_engine.py
   ├─ get_folder_indexer()              # accès paresseux
   ├─ outil MCP « search_codebase »     # exposé au LLM
   ├─ _inject_codebase_context()        # RAG injecté dans le system prompt
   └─ _try_codebase_direct_answer()     # court-circuit déterministe (chemin, liste de fichiers…)

interfaces/gui/sidebar.py   ── section « 📁 Dossiers du projet » (attacher/réindexer/détacher)
relay/relay_server.py       ── handle_codebase_message() + _resolve_vscode_workspace()
```

### Deux voies de récupération

- **Injection RAG** (`_inject_codebase_context`) : avant chaque génération, les passages pertinents du dossier attaché sont ajoutés au system prompt.
- **Court-circuit déterministe** (`_try_codebase_direct_answer`) : pour les questions *sur* le dossier lui-même (« quel est le chemin du projet ? », « liste les fichiers »…), une réponse fiable est construite directement, sans dépendre d'un appel d'outil du modèle.

La recherche filtre par `workspace_id` côté ChromaDB et réutilise le **reranking CrossEncoder** de `VectorMemory`.

---

## 🧩 Spécificités VS Code

- Le menu **`@`** liste fichiers **et** dossiers du workspace ; on peut **naviguer dans les dossiers** ou taper un chemin/nom pour filtrer.
- Un **fichier** choisi via `@` est attaché par le **canal d'indexation** (WebSocket chiffré), pas par un upload HTTP — fiable, et cohérent avec le modèle « contexte du workspace » (fini les erreurs `… · fetch failed`). Le bouton **« + »** reste, lui, une pièce jointe ponctuelle.
- **Un seul contexte `@codebase` partagé par projet VS Code** : tous les fichiers/dossiers attachés depuis le même workspace vont dans **un** workspace hôte (clé = racine du projet) → l'assistant voit un projet cohérent, pas un contexte par attache.

---

## ❓ FAQ

**Est-ce que ça reste local ?**
Oui. L'indexation réutilise votre `VectorMemory` (ChromaDB local) et les processeurs de fichiers existants. Aucun appel réseau, aucun nouveau pipeline d'embedding.

**Faut-il réindexer manuellement après avoir modifié des fichiers ?**
Lancez **Réindexer** (sidebar ou commande VS Code) : seuls les fichiers modifiés sont retraités. C'est rapide et sûr.

**Comment retirer un dossier du contexte ?**
**Détacher** depuis la section *📁 Dossiers du projet* (ou la commande VS Code) : les chunks du dossier sont purgés et il est retiré du manifeste.

**`pathspec` est-il obligatoire ?**
Non. S'il est installé, il donne la sémantique `.gitignore` exacte ; sinon, un matcher `.gitignore` intégré couvre les motifs courants.

---

> Voir aussi : [PROMPT_LIBRARY.md](PROMPT_LIBRARY.md), [CONVERSATION_SEARCH.md](CONVERSATION_SEARCH.md), [MCP_INTEGRATION.md](MCP_INTEGRATION.md), [CHANGELOG.md](CHANGELOG.md).
