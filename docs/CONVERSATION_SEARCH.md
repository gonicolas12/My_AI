# 🔎 Recherche globale cross-conversations

*My Personal AI v7.9.0*

Retrouvez **n'importe quel échange passé** par recherche **sémantique** — sur **toutes** vos conversations/sessions à la fois, pas seulement la conversation courante. 100% local, en réutilisant l'index et les modèles déjà chargés.

---

## 📍 Où la trouver

Barre latérale (**☰**) → section **🔎 Recherche globale** : un champ de recherche, un bouton **🔄** (réindexer), et la liste des résultats.

- Tapez votre requête, **Entrée** (ou **🔍**).
- Chaque résultat affiche l'**icône du rôle** (🧑 vous / 🤖 assistant), le **nom de la session** et un **extrait**.
- **Un clic sur un résultat** ouvre la conversation source **et surligne le passage** trouvé (défilement automatique). Le surlignage **disparaît au clic**, comme une vraie sélection.

---

## ⚙️ Comment ça marche

### Réutilisation de l'existant (aucun doublon)
La recherche s'appuie sur l'**index ChromaDB** déjà présent (collection `conversations`) et l'**embedding partagé** (`core/shared.py`, `all-MiniLM-L6-v2`). **Aucun second pipeline d'embedding** n'est créé.

### Indexation incrémentale
Un manifeste `memory/vector_store/conversation_index.json` mémorise le `last_modified` de chaque workspace indexé :

- au réindex, **seuls les workspaces nouveaux ou modifiés** sont retraités ;
- les workspaces **supprimés** sont **purgés** de l'index ;
- un **numéro de schéma** force une réindexation complète quand la logique d'indexation évolue.

L'index est **rafraîchi automatiquement** avant chaque recherche (incrémental, donc rapide). Le bouton **🔄** force une réindexation complète.

### Couverture
**Chaque message non vide** est indexé — **utilisateur ET assistant**, **sans aucune limite de longueur**. Seuls les types purement techniques (placeholders de génération de fichier, images) sont ignorés.

### Recherche hybride (précision + rappel)
1. **Voisins sémantiques** : recherche vectorielle (sur-échantillonnée).
2. **Filet lexical mot-exact sur tout le corpus** : garantit qu'un message contenant **littéralement** les mots de la requête n'est **jamais manqué**, même hors des plus proches voisins (insensible à la casse → toutes langues).
3. **Reranking CrossEncoder** (si disponible) pour ordonner finement, avec **seuil de pertinence** qui élimine le bruit hors-sujet. En l'absence de reranker, repli sur un **seuil de distance cosinus**.

### Filtres optionnels
- **rôle** : `user` / `assistant`
- **mot-clé** : sous-chaîne devant apparaître littéralement dans l'extrait
- **date** : `since` (timestamp ISO minimal)

---

## 🏗️ Sous le capot

```
interfaces/gui/sidebar.py            # Section « 🔎 Recherche globale » (UI, thread)
        │  via AIEngine.get_conversation_search()
        ▼
core/conversation_search.py  ── ConversationSearch
        ├─ session_manager (SessionManager)     # liste/charge les workspaces
        └─ vector_memory (VectorMemory)         # collection ChromaDB « conversations »
                                                # + embedding partagé + reranker
```

### API (pour développeurs)

```python
cs = ai_engine.get_conversation_search()   # None si dépendances absentes
cs.is_available()                          # embedding + collection + session_manager prêts ?

cs.reindex(force=False)  # incrémental ; force=True = tout réindexer
# → {"indexed": n_workspaces, "messages": n_messages, "removed": n_supprimes}

cs.search(
    query,
    n_results=10,
    role=None,        # "user" | "assistant"
    keyword=None,     # sous-chaîne exacte
    since=None,       # date ISO minimale
    auto_reindex=True,
)
# → [{workspace_id, workspace_name, message_index, role, timestamp, excerpt, score, distance}, ...]
```

### Configuration (`config.yaml`, section `search`)

| Clé | Défaut | Rôle |
|---|---|---|
| `search.min_rerank_score` | `-7.0` | Score CrossEncoder minimal pour conserver un résultat (élimine le hors-sujet ~ -11) |
| `search.max_distance` | `0.55` | Distance cosinus maximale, utilisée **uniquement** en repli si aucun reranker n'est disponible |

---

## 📝 Notes & limites

- La **première** recherche après un long ajout de conversations peut déclencher une réindexation un peu plus longue (réembeddings) ; les suivantes sont incrémentales.
- La qualité du reranking dépend du CrossEncoder (`ms-marco-MiniLM-L-6-v2`) ; le **filet lexical** compense pour les correspondances exactes quel que soit la langue.
- L'index de conversations est aussi visible et **gérable** depuis la fenêtre **🧠 Mémoire** (onglet *Conversations*) — voir [MEMORY.md](MEMORY.md).

---

> Voir aussi : [MEMORY.md](MEMORY.md), [ULTRA_10M_TOKENS.md](ULTRA_10M_TOKENS.md), [CHANGELOG.md](CHANGELOG.md).
