# 🔎 Recherche globale cross-conversations

Retrouvez **n'importe quel échange passé** par recherche **sémantique** — sur **toutes** vos conversations/sessions à la fois, pas seulement la conversation courante. 100% local, en réutilisant l'index et les modèles déjà chargés.

---

## 📍 Où la trouver

Barre latérale (**Ctrl+B**) → **Recherche globale** : un champ de recherche, un bouton **Réindexer les conversations**, et la liste des résultats.

- Tapez votre requête, puis **Entrée**.
- Chaque résultat affiche le **rôle** (vous / assistant), le **nom de la session** (son nom actuel, même juste après un renommage) et un **extrait**.
- **Un clic sur un résultat** ouvre la conversation source **et surligne le passage** trouvé (défilement automatique). Le surlignage **disparaît au clic**, comme une vraie sélection.

---

## ⚙️ Comment ça marche

### Réutilisation de l'existant (aucun doublon)
La recherche s'appuie sur l'**index ChromaDB** déjà présent (collection `conversations` du modèle d'embeddings actif) et l'**embedding partagé** (`core/shared.py`, Granite 107M multilingue : une question en français retrouve un message écrit en anglais). **Aucun second pipeline d'embedding** n'est créé.

### Indexation incrémentale
Un manifeste `memory/vector_store/conversation_index.json` mémorise le `last_modified` et le nom de chaque workspace indexé :

- au réindex, **seuls les workspaces nouveaux ou modifiés** sont retraités ;
- les workspaces **supprimés** sont **purgés** de l'index ;
- un workspace **renommé** (crayon de la barre latérale) garde son `last_modified` : seul le nom porté par ses messages dans l'index est réécrit, **sans réembedding**. Cela se fait au renommage même, ou au réindex suivant si l'index était injoignable à ce moment-là. Un manifeste écrit avant cette version relit une fois les noms dans l'index ;
- un **numéro de schéma** force une réindexation complète quand la logique d'indexation évolue.

L'index est **rafraîchi automatiquement** avant chaque recherche (incrémental, donc rapide). Le bouton **🔄** force une réindexation complète ; le nombre de messages indexés s'affiche alors quelques secondes sous le champ de recherche.

### Couverture
**Chaque message non vide** est indexé — **utilisateur ET assistant**, **sans aucune limite de longueur**. Seuls les types purement techniques (placeholders de génération de fichier, images) sont ignorés.

### Recherche hybride (précision + rappel)
1. **Voisins sémantiques** : recherche vectorielle (sur-échantillonnée).
2. **Filet lexical mot-exact sur tout le corpus** : garantit qu'un message contenant **littéralement** les mots de la requête n'est **jamais manqué**, même hors des plus proches voisins (insensible à la casse → toutes langues).
3. **Filtre de pertinence** qui élimine le bruit hors sujet. Avec Granite (modèle par défaut), c'est la **distance cosinus** (`search.max_distance`, 0,32), et le reranker multilingue `mmarco-mMiniLMv2` ne fait qu'**ordonner** les résultats gardés : son score change d'échelle d'une question à l'autre. Avec MiniLM, le **seuil de score** du CrossEncoder anglais `ms-marco-MiniLM-L-6-v2` (`search.min_rerank_score`), ou la distance (0,55) sans reranker. Mesuré sur 18 questions en 9 langues et 10 hors sujet : 17 trouvées et aucun bruit, contre 12 et 2 avec l'ancien filtre (voir [OPTIMIZATION.md](OPTIMIZATION.md#reranking-et-filtre-de-pertinence-mesures-du-lot-5-bis)).

### Filtres optionnels
- **rôle** : `user` / `assistant`
- **mot-clé** : sous-chaîne devant apparaître littéralement dans l'extrait
- **date** : `since` (timestamp ISO minimal)

---

## 🏗️ Sous le capot

```
frontend/src/features/shell/sidebar/SearchPanel.tsx   # « Recherche globale » de la barre latérale
interfaces/desktop/api_sidebar.py                      # routes de la recherche et de la réindexation
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
# → {"indexed": n_workspaces, "messages": n_messages, "removed": n_supprimes,
#    "renamed": n_renommes}

# Après SessionManager.rename_workspace : nouveau nom dans les métadonnées,
# sans réembedding (ChatService.rename_session l'appelle)
cs.rename_workspace(workspace_id, "Nouveau nom")   # → True si l'index le porte

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
| `search.min_rerank_score` | `-7.0` | Score minimal du CrossEncoder anglais (ms-marco, avec MiniLM) pour conserver un résultat (élimine le hors-sujet ~ -11) |
| `search.max_distance` | `0.32` avec Granite, `0.55` avec MiniLM | Distance cosinus maximale d'un résultat gardé, quand le score du reranker ne sert pas de filtre (Granite, ou pas de reranker) |

---

## 📝 Notes & limites

- La **première** recherche après un long ajout de conversations peut déclencher une réindexation un peu plus longue (réembeddings) ; les suivantes sont incrémentales.
- Le seuil de 0,32 a été mesuré sur des messages courts ; s'il écarte trop de résultats chez vous, montez `search.max_distance` (0,34 gardait les 18 questions, avec un résultat parasite sur 10 questions hors sujet). Le **filet lexical** garde toujours les correspondances exactes, quelle que soit la langue.
- L'index de conversations est aussi visible et **gérable** depuis le panneau **Mémoire** (onglet *Conversations*) — voir [MEMORY.md](MEMORY.md).

---

> Voir aussi : [MEMORY.md](MEMORY.md), [ULTRA_10M_TOKENS.md](ULTRA_10M_TOKENS.md), [CHANGELOG.md](CHANGELOG.md).
