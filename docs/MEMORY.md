# 🧠 Mémoire — voir, éditer et supprimer ce que l'IA sait

My_AI mémorise des informations sur vous pour des réponses plus pertinentes. Comme **tout est local**, vous devez pouvoir **inspecter et reprendre le contrôle** de cette mémoire. La fenêtre **🧠 Mémoire** (sidebar) offre des opérations CRUD **réelles** sur les deux stores de mémoire — aucune donnée ne quitte votre machine, aucune suppression simulée.

---

## 📍 Où la trouver

Ouvrez la barre latérale (bouton **☰**) → bouton **🧠 Mémoire**.

> La fenêtre Mémoire **remplace** l'ancienne mini-section « Connaissances » de la sidebar : un seul endroit, plus complet (faits **et** mémoire vectorielle).

---

## 🗂️ Les deux stores de mémoire

| Store | Backend | Contenu | Onglet |
|---|---|---|---|
| **Faits structurés** | SQLite (`data/knowledge_base/facts.db`) | Faits catégorisés extraits/ajoutés (préférence, décision, personne, procédure, technique, général) | **Faits** |
| **Mémoire vectorielle — documents** | ChromaDB (`memory/vector_store/`) | Chunks des documents que vous avez fournis | **Documents** |
| **Mémoire vectorielle — conversations** | ChromaDB | Index de recherche reconstruit depuis vos conversations | **Conversations** |

---

## 💬 Mémoriser depuis le chat

Dites-le simplement dans la conversation :

> Retiens que mon chat s'appelle Félix.

Le fait est enregistré aussitôt dans l'onglet **Faits** (source : `conversation`), un indicateur « 🧠 Mémorisé : … » s'affiche, et My_AI le confirme dans sa réponse. Il reste disponible dans les conversations suivantes.

- **Formulations reconnues**, en début de message ou de phrase : « retiens que… », « retiens ceci : … », « souviens-toi que… », « n'oublie pas que… », « mémorise… », « garde en tête que… », « prends note que… », « tu peux retenir que… ? », et en anglais « remember that… », « keep in mind that… ».
- **Une question ou une autre demande qui suit n'est pas mémorisée** : « Retiens que mon chat s'appelle Félix. Quel temps fait-il ? » enregistre seulement « mon chat s'appelle Félix », puis répond à la question. Un bloc « Retiens ceci : … » est gardé en entier, consignes comprises (une procédure, par exemple).
- **Ne déclenchent rien** : « je retiens que… », « tu te souviens de… ? », une question (« Rappelle-toi : où j'habite ? » demande de s'en souvenir, pas de la retenir), ou une consigne glissée dans une tâche (« écris la fonction, et n'oublie pas que la liste peut être vide »).
- **Autres formulations** : le modèle dispose de l'outil `remember_fact`, qui fait le même enregistrement. Il ne doit s'en servir que si vous lui demandez de retenir quelque chose.
- **Avec des pièces jointes** : ça marche aussi quand le message joint des fichiers (pdf, docx…) ou une image. Une question qui ne porte pas sur l'image jointe suit le chemin habituel (faits, outils) ; une question sur l'image reçoit les faits pour sa réponse.
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
| **Conversations** | Jamais : c'est l'index de la recherche globale de la sidebar. |

**Fichiers et documents générés** (« génère un fichier… », Word, PDF, PowerPoint, Excel) : leur contenu est rédigé à part, et il reçoit les faits **sur vous** seulement quand la demande parle de vous. C'est le cas avec « mon prénom », « mon entreprise », « mon équipe », « mon chat »…, ou pour un CV, une lettre ou une carte de visite. « Génère un fichier qui affiche mon prénom » écrit donc votre prénom, alors qu'un script de tri ou un rapport sur les baleines restent neutres : avec les faits sous les yeux, le modèle les glissait partout. Les consignes pour l'IA (« termine tes réponses par… ») ne s'appliquent qu'au chat.

---

## ✨ Ce que vous pouvez faire

### 👁️ Voir
- **3 onglets** : Faits · Documents · Conversations.
- **Recherche** dans l'onglet courant + **filtre par catégorie** (onglet Faits).
- **Pagination** (20 entrées/page).
- **Provenance** affichée sous chaque entrée :
  - Faits → `source` (manuel / conversation / …), `confiance`, date de mise à jour.
  - Conversations → **session** · rôle (vous / assistant) · horodatage.
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
interfaces/gui/memory_panel.py     # Fenêtre « Mémoire » (mixin GUI)
        │  appelle
        ▼
core/memory_store.py  ── MemoryStore  # Façade CRUD unifiée (testable sans GUI)
        │                  exposé par AIEngine.get_memory_store()
        ├─ core/knowledge_base_manager.py   # Faits (SQLite) — CRUD
        └─ memory/vector_memory.py          # Vecteurs (ChromaDB) — CRUD par entrée
             ├─ list_entries / get_entry / count_entries
             ├─ update_entry  (ré-embarque)
             └─ delete_entry  (vraie suppression ChromaDB)

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
Oui. Si le chiffrement AES-256 de la mémoire vectorielle est actif, les entrées sont **déchiffrées** pour l'affichage et **re-chiffrées** à l'édition.

**Est-ce que ça reste local ?**
Entièrement. Toutes les opérations s'effectuent sur les fichiers locaux (`data/knowledge_base/`, `memory/vector_store/`).

---

> Voir aussi : [CONVERSATION_SEARCH.md](CONVERSATION_SEARCH.md) (recherche globale), [ULTRA_10M_TOKENS.md](ULTRA_10M_TOKENS.md) (mémoire vectorielle), [CHANGELOG.md](CHANGELOG.md).
