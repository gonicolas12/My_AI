# 🧠 Vector Store - Mémoire Vectorielle de l'IA

## 📂 Qu'est-ce que c'est ?

Ce dossier contient la **base de données vectorielle** de votre assistant IA. C'est sa "mémoire à long terme" qui lui permet de :

- 💬 **Se souvenir de vos conversations** même après redémarrage
- 📚 **Indexer vos documents** (PDF, Word, code, etc.)
- 🔍 **Rechercher sémantiquement** (comprendre le sens, pas juste les mots)
- ⚡ **Accéder instantanément** à 1M+ tokens de contexte

## 🗄️ Structure

```
vector_store/
├── chroma_db/              # Base de données ChromaDB (SQLite + vecteurs)
│   ├── chroma.sqlite3      # Métadonnées et index
│   ├── *.bin               # Vecteurs d'embeddings (384 dimensions)
│   └── *.parquet           # Collections (conversations, documents)
└── README.md               # Ce fichier
```

## 🔐 Données Personnelles

⚠️ **IMPORTANT : Ce dossier contient VOS données personnelles**

- Toutes vos conversations avec l'IA
- Vos documents uploadés et analysés
- Vos snippets de code
- Vos notes et contexte

🚫 **NE JAMAIS commiter ce dossier sur GitHub** (déjà dans `.gitignore`)

## 🛠️ Fonctionnement Technique

### 1. Tokenization (tiktoken — cl100k_base)
```python
Texte: "L'IA est fascinante !"
Tokens: ['L', "'", 'IA', ' est', ' fasc', 'inante', ' !']  # 7 tokens (encodage cl100k_base)
```

### 2. Embeddings (Sentence-Transformers)
```python
Texte → Vecteur de 384 nombres
"Comment créer une API ?" → [0.23, -0.45, 0.67, ..., 0.12]
```

### 3. Recherche Sémantique (ChromaDB)
```python
Query: "Développer un service web"
✅ Trouve: "Créer une API REST" (95% similarité)
✅ Trouve: "Endpoints HTTP" (88% similarité)
❌ Ignore: "Recette de cuisine" (5% similarité)
```

## 📊 Capacités

| Métrique | Valeur |
|----------|--------|
| **Capacité maximale** | 1,000,000 tokens |
| **Taille des chunks** | 512 tokens |
| **Overlap chunks** | 50 tokens |
| **Dimensions vecteur** | 384 |
| **Modèle embeddings** | all-MiniLM-L6-v2 |
| **Recherche** | Cosine similarity |
| **Stockage** | SQLite + Parquet |

## 🔄 Cycle de Vie

### Au Démarrage
```python
# Si le dossier existe
→ Charge toutes vos données (0.5s)
→ Restaure conversations et documents
→ Prêt à chercher dans 10M tokens

# Si le dossier n'existe pas
→ Crée automatiquement la structure
→ Initialise les collections
→ Prêt à stocker de nouvelles données
```

### Pendant l'Utilisation
```python
# À chaque conversation
→ Tokenize (tiktoken cl100k_base)
→ Créer embeddings (sentence-transformers)
→ Stocker dans ChromaDB
→ Indexer pour recherche rapide

# À chaque question
→ Embedder la question
→ Chercher les chunks similaires (0.02s)
→ Retourner les 5 plus pertinents
```

## 🧹 Maintenance

### Voir les Statistiques
```python
from memory.vector_memory import VectorMemory

vm = VectorMemory()
print(vm.stats)
# {
#   'documents_added': 42,
#   'chunks_created': 318,
#   'total_tokens': 163840,
#   'last_updated': '2025-11-17 14:30:22'
# }
```

### Nettoyer la Mémoire
```python
# ATTENTION : Supprime TOUTES les données
vm.clear_memory()
```

### Sauvegarder Manuellement
```python
# Automatique, mais vous pouvez forcer
vm.save_state()
```

## 🔒 Chiffrement (Optionnel)

Activez le chiffrement AES-256 pour protéger vos données :

```python
vm = VectorMemory(
    enable_encryption=True,
    encryption_key="votre-clé-32-caractères"
)
```

⚠️ **Ne perdez JAMAIS votre clé** : données irrécupérables sans elle !

## 🐛 Dépannage

### "ChromaDB non disponible"
```bash
pip install chromadb sentence-transformers tiktoken
```

### "Mémoire pleine"
```python
# Augmenter la limite (défaut : 10M tokens)
vm = VectorMemory(max_tokens=50_000_000)  # 50M tokens
```

### Réinitialiser Complètement
```bash
# Windows
rd /s /q memory\vector_store\chroma_db

# Linux/Mac
rm -rf memory/vector_store/chroma_db
```

## 📈 Performance

| Opération | Temps |
|-----------|-------|
| Charger au démarrage | 0.5s |
| Ajouter 1 document | 0.1s |
| Chercher dans 10M tokens | <0.02s |
| Créer embeddings | 0.05s / chunk |

## 🔗 Liens Utiles

- [ChromaDB Documentation](https://docs.trychroma.com/)
- [Sentence-Transformers](https://www.sbert.net/)
- [tiktoken](https://github.com/openai/tiktoken)

---

**Version** : 1.0.0  
**Dernière mise à jour** : 17 novembre 2025  
**Compatibilité** : Python 3.8+
