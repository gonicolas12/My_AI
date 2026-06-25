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

**La suppression efface-t-elle vraiment les données ?**
Oui. Les faits sont supprimés de la base SQLite ; les entrées vectorielles via `ChromaDB.delete`. Pour les conversations, l'option « à la source » retire aussi le message du workspace.

**Le chiffrement est-il géré ?**
Oui. Si le chiffrement AES-256 de la mémoire vectorielle est actif, les entrées sont **déchiffrées** pour l'affichage et **re-chiffrées** à l'édition.

**Est-ce que ça reste local ?**
Entièrement. Toutes les opérations s'effectuent sur les fichiers locaux (`data/knowledge_base/`, `memory/vector_store/`).

---

> Voir aussi : [CONVERSATION_SEARCH.md](CONVERSATION_SEARCH.md) (recherche globale), [ULTRA_10M_TOKENS.md](ULTRA_10M_TOKENS.md) (mémoire vectorielle), [CHANGELOG.md](CHANGELOG.md).
