# 🧠 Mémoire — voir, éditer et supprimer ce que l'IA sait

My_AI mémorise des informations sur vous pour des réponses plus pertinentes. Comme **tout est local**, vous devez pouvoir **inspecter et reprendre le contrôle** de cette mémoire. Le panneau **Mémoire** (bouton en bas de la barre latérale) offre des opérations CRUD **réelles** sur les deux stores de mémoire — aucune donnée ne quitte votre machine, aucune suppression simulée.

---

## 📍 Où la trouver

Cliquez sur **Mémoire** en bas de la barre latérale (ou cherchez « Mémoire » dans la palette Ctrl+K) : le panneau s'ouvre dans la fenêtre.

> Le panneau Mémoire **remplace** l'ancienne mini-section « Connaissances » de la barre latérale : un seul endroit, plus complet (faits **et** mémoire vectorielle).

---

## 🗂️ Les deux stores de mémoire

| Store | Backend | Contenu | Onglet |
|---|---|---|---|
| **Faits structurés** | SQLite (`data/knowledge_base/facts.db`) | Faits catégorisés extraits/ajoutés (préférence, décision, personne, procédure, technique, général) | **Faits** |
| **Mémoire vectorielle — documents** | ChromaDB (`memory/vector_store/`) | Chunks des documents que vous avez fournis | **Documents** |
| **Mémoire vectorielle — conversations** | ChromaDB | Index de recherche reconstruit depuis vos conversations | **Conversations** |

---

## 🌍 Recherche multilingue

La mémoire vectorielle (onglets **Documents** et **Conversations**, outil `search_memory`, recherche globale, dossiers attachés) cherche par le **sens**, avec un modèle d'embeddings local : **Granite Embedding 107M multilingue** (IBM, Apache 2.0, 228 Mo), celui qui choisit déjà les passages des longs documents. Une question en français retrouve un passage anglais, arabe ou chinois.

| Modèle | 3 bons passages retrouvés | Vitesse |
|---|---|---|
| all-MiniLM-L6-v2 (avant, entraîné pour l'anglais) | 28 % | référence |
| **Granite 107M multilingue** (par défaut) | **76 %** | identique |

*29 questions en 9 langues sur la documentation française et anglaise de My_AI (10/11/2026). EmbeddingGemma 2 via Ollama faisait 76 à 79 %, dix fois plus lentement et 0,5 Go sur le GPU : non retenu.*

- **Réglage** : `optimization.rag.embedding_model` dans `config.yaml` (un modèle sentence-transformers du Hub Hugging Face, ou un dossier local).
- **Une collection par modèle** : les vecteurs de deux modèles ne se comparent pas, même à dimension égale. Chaque modèle a donc ses collections ChromaDB (`documents__granite-embedding-107m-multiling-8e8c41d0__384`…) ; MiniLM garde les noms historiques (`documents`, `conversations`, `codebase`).
- **Réindexation en arrière-plan** : au premier lancement avec un autre modèle, les entrées existantes sont recalculées depuis leur texte stocké (déchiffré pour le calcul, toujours chiffré dans la base), avec les mêmes identifiants et la même provenance. Pendant ce temps, la recherche ne voit que ce qui est déjà recalculé ; ce que vous supprimez ou modifiez l'est aussi dans l'ancienne collection, et rien ne revient. L'ancienne collection n'est supprimée qu'à la fin : appli fermée avant, la copie reprend au lancement suivant. Comptez quelques minutes pour plusieurs milliers d'entrées.
- **Repli** : tant que Granite n'est pas téléchargé (il l'est en arrière-plan au lancement), MiniLM sert la session avec l'index MiniLM ; Granite prend le relais au lancement suivant.
- **Morceaux** : 256 tokens, 32 de chevauchement (`optimization.rag.chunk_size` / `chunk_overlap`). Granite lit jusqu'à 512 tokens, mais retrouve mieux à 256 (76 % contre 62 % à 512).
- **Reranking multilingue** : avec Granite, `mmarco-mMiniLMv2` (14 langues, 470 Mo, téléchargé une fois en arrière-plan) remet les passages candidats dans l'ordre : 86 % de bons passages parmi les 3 retenus, contre 77 % avec Granite seul et 60 % avec l'ancien reranker anglais. Réglage : `optimization.rag.reranker_model` (`"auto"`, `"none"` ou un modèle).
- **Recherche des conversations** : un message est gardé s'il est assez proche de la question pour Granite (distance ≤ 0,32) ou s'il en contient tous les mots ; 17 questions sur 18 trouvent leur message, souvent écrit dans une autre langue, et une question hors sujet ne ramène rien.

---

## 💬 Mémoriser depuis le chat

Dites-le simplement dans la conversation :

> Retiens que mon chat s'appelle Félix.

Le fait est enregistré aussitôt dans l'onglet **Faits** (source : `conversation`), un indicateur « 🧠 Mémorisé : … » s'affiche, et My_AI le confirme dans sa réponse. Il reste disponible dans les conversations suivantes.

- **Formulations reconnues**, en début de message ou de phrase : « retiens que… », « retiens ceci : … », « souviens-toi que… », « n'oublie pas que… », « mémorise… », « garde en tête que… », « prends note que… », « tu peux retenir que… ? », et en anglais « remember that… », « keep in mind that… ».
- **Une question ou une autre demande qui suit n'est pas mémorisée** : « Retiens que mon chat s'appelle Félix. Quel temps fait-il ? » enregistre seulement « mon chat s'appelle Félix », puis répond à la question. Un bloc « Retiens ceci : … » est gardé en entier, consignes comprises (une procédure, par exemple).
- **Ne déclenchent rien** : « je retiens que… », « tu te souviens de… ? », une question (« Rappelle-toi : où j'habite ? » demande de s'en souvenir, pas de la retenir), ou une consigne glissée dans une tâche (« écris la fonction, et n'oublie pas que la liste peut être vide »).
- **Autres formulations** : le modèle dispose de l'outil `remember_fact`, qui fait le même enregistrement. Il ne doit s'en servir que si vous lui demandez de retenir quelque chose.
- **Avec des pièces jointes** : ça marche aussi quand le message joint des fichiers (pdf, docx…) ou une image. Un message qui ne fait que demander de retenir suit le chemin habituel, sans faire lire l'image au modèle ; tout autre message part avec l'image et reçoit les faits pour sa réponse.
- **Pas de doublon** : une information déjà connue (casse, accents et ponctuation finale ignorés) est rafraîchie au lieu d'être recopiée.
- **Vos mots, pas les siens** : un fait noté à la première personne (« je m'appelle Nicolas ») est présenté au modèle à la troisième personne (« L'utilisateur s'appelle Nicolas »). Il vous répond donc « Tu t'appelles Nicolas », et non « Je m'appelle Nicolas ». L'onglet Faits garde vos mots.
- **Consignes pour l'IA** : ce qui parle d'elle (« retiens que tu t'appelles Jarvis », « retiens que tu dois toujours me répondre en anglais ») est rangé à part, comme une consigne à appliquer dans chaque réponse. Elle prime sur ses réglages par défaut (nom, langue, ton, format), et l'IA en parle à la première personne (« C'est noté : je m'appelle Jarvis »). En anglais aussi : « Remember that your name is Jarvis » → « Noted: my name is Jarvis ». Une question posée en anglais reçoit sa réponse en anglais, même si les faits ont été dictés en français (« What's your name? » → « My name is Jarvis »).
- **Désactiver** : `knowledge_base.auto_extract: false` dans `config.yaml` ; seul l'ajout manuel (➕ Ajouter) reste possible.

---

## 📨 Ce que le modèle reçoit

| Onglet | Envoyé au modèle |
|---|---|
| **Faits** | Automatiquement, dans le prompt système de chaque réponse, y compris avec un fichier ou une image joints : d'abord les faits qui partagent des mots avec votre message (casse, accents et pluriels ignorés), puis les plus récents, jusqu'à 12 faits ou 2 500 caractères. Ils restent dans la réponse rédigée après un appel d'outil. |
| **Documents** | Quand le modèle appelle l'outil `search_memory`, qui cherche aussi dans les faits. |
| **Conversations** | Jamais : c'est l'index de la recherche globale de la barre latérale. |

**Fichiers et documents générés** (« génère un fichier… », Word, PDF, PowerPoint, Excel) : leur contenu est rédigé à part, et il reçoit les faits **sur vous** seulement quand la demande parle de vous. C'est le cas avec « mon prénom », « mon entreprise », « mon équipe », « mon chat »…, ou pour un CV, une lettre ou une carte de visite. « Génère un fichier qui affiche mon prénom » écrit donc votre prénom, alors qu'un script de tri ou un rapport sur les baleines restent neutres : avec les faits sous les yeux, le modèle les glissait partout. Les consignes pour l'IA (« termine tes réponses par… ») ne s'appliquent qu'au chat.

---

## ✨ Ce que vous pouvez faire

### 👁️ Voir
- **3 onglets** : Faits · Documents · Conversations.
- **Recherche** dans l'onglet courant + **filtre par catégorie** (onglet Faits).
- **Pagination** (20 entrées/page).
- **Provenance** affichée sous chaque entrée :
  - Faits → `source` (manuel / conversation / …), `confiance`, date de mise à jour.
  - Conversations → **session** (son nom actuel : renommer une conversation change aussi celui-ci) · rôle (vous / assistant) · horodatage.
  - Documents → **nom du document** · n° de chunk · date.

### ✏️ Éditer
- Bouton **✏️** : édition **inline** du contenu, puis **💾 Enregistrer** / **✖ Annuler**.
- Pour un **document/conversation**, le texte est **ré-encodé** (nouvel embedding) afin que la recherche reste cohérente.

### 🗑️ Supprimer
- Bouton **🗑️** → **dialogue de confirmation** (cohérent avec la confirmation MCP existante).
- La suppression d'une **entrée vectorielle** est une **vraie suppression dans ChromaDB** (`collection.delete`).

#### Cas particulier : les conversations (« supprimer à la source »)
L'onglet **Conversations** affiche un **index** reconstruit depuis vos workspaces. Une suppression directe dans l'index **réapparaîtrait** au prochain réindex. C'est pourquoi le dialogue propose une case :

> ☑ **Supprimer aussi le message d'origine** *(sinon réapparaît au prochain réindex)*

- **Cochée (défaut)** → le **message d'origine** est retiré du workspace, puis l'index est **reconstruit** : la suppression est **durable**.
- **Décochée** → suppression **transitoire** de l'index uniquement (réapparaît au prochain réindex forcé).

L'édition d'une entrée de conversation propage de même la modification au **message d'origine**.

---

## 🏗️ Sous le capot

```
frontend/src/features/panels/memory/   # Panneau « Mémoire » de la fenêtre
interfaces/desktop/memory.py          # Service du panneau (routes : api_memory.py) ;
        │  appelle                     # message d'origine modifié via le ChatService
        ▼
core/memory_store.py  ── MemoryStore  # Façade CRUD unifiée (testable sans interface)
        │                  exposé par AIEngine.get_memory_store()
        ├─ core/knowledge_base_manager.py   # Faits (SQLite) — CRUD
        └─ memory/vector_memory.py          # Vecteurs (ChromaDB) — CRUD par entrée
             ├─ list_entries / get_entry / count_entries
             ├─ update_entry  (ré-embarque)
             ├─ delete_entry  (vraie suppression ChromaDB)
             └─ memory/embedding_reindex.py  # Changement de modèle : copie en arrière-plan

core/embedding_engine.py           # Modèle d'embeddings (Granite, repli MiniLM) :
                                   # encode / encode_query / encode_document,
                                   # nom de collection par modèle

core/ai_engine.py                  # Côté chat
   ├─ _remember_from_message()     # « retiens que… » → KnowledgeBaseManager.remember()
   ├─ outils remember_fact / search_memory
   └─ _knowledge_base_context()    # select_facts() → prompt système (et synthèse après outils)
```

### `MemoryStore` (API principale, pour développeurs)

```python
store = ai_engine.get_memory_store()

# Faits
items, total = store.list_facts(query="", category=None, limit=25, offset=0)
store.add_fact(category, key, value, source="manual")
store.update_fact(fact_id, value)
store.delete_fact(fact_id)

# Vecteurs (collection_type = "document" | "conversation")
items, total = store.list_vectors("document", query="", limit=25, offset=0)
store.update_vector(entry_id, new_text, "document", at_source=True, metadata=None)
store.delete_vector(entry_id, "conversation", at_source=True, metadata=None)

# Vue d'ensemble & provenance
store.stats()                       # {"facts": n, "documents": n, "conversations": n}
MemoryStore.describe_provenance(item)
```

Pour les conversations, `at_source=True` modifie le message d'origine du workspace puis déclenche un réindex incrémental (suppression/édition **durable**). `at_source=False` n'agit que sur l'index ChromaDB.

---

## ❓ FAQ

**Si je dis « retiens ceci » dans le chat, est-ce vraiment retenu ?**
Oui : le fait apparaît dans l'onglet **Faits** et sert dans les conversations suivantes (voir [Mémoriser depuis le chat](#-mémoriser-depuis-le-chat)). Vous pouvez le modifier ou le supprimer comme n'importe quel fait.

**La suppression efface-t-elle vraiment les données ?**
Oui. Les faits sont supprimés de la base SQLite ; les entrées vectorielles via `ChromaDB.delete`. Pour les conversations, l'option « à la source » retire aussi le message du workspace.

**Le chiffrement est-il géré ?**
Oui. Si le chiffrement AES-256 de la mémoire vectorielle est actif, les entrées sont **déchiffrées** pour l'affichage et **re-chiffrées** à l'édition. La réindexation après un changement de modèle déchiffre le texte pour le calcul seulement : il reste chiffré dans la base.

**Après la mise à jour, la recherche ne trouve pas tout ?**
La mémoire est recalculée avec le nouveau modèle, en arrière-plan, juste après le lancement (« 🔄 Réindexation de la mémoire » dans la console, puis « ✅ Réindexation terminée »). Les entrées apparaissent au fur et à mesure ; rien n'est perdu (voir [Recherche multilingue](#-recherche-multilingue)).

**Est-ce que ça reste local ?**
Entièrement. Toutes les opérations s'effectuent sur les fichiers locaux (`data/knowledge_base/`, `memory/vector_store/`).

---

> Voir aussi : [CONVERSATION_SEARCH.md](CONVERSATION_SEARCH.md) (recherche globale), [ULTRA_10M_TOKENS.md](ULTRA_10M_TOKENS.md) (mémoire vectorielle), [CHANGELOG.md](CHANGELOG.md).
