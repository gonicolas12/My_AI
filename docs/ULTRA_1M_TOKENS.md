# 🚀 Documentation Mémoire Vectorielle Étendue - v5.0.0 (3 Septembre 2025)

## 💾 Vue d'Ensemble : Mémoire Interne de 1M Tokens

Le système Ultra de My Personal AI v5.0.0 implémente une **mémoire vectorielle interne pouvant stocker jusqu'à 1 million de tokens** (via ChromaDB et SQLite). Il est important de distinguer deux notions différentes :

> ⚠️ **À ne pas confondre**
> - **Mémoire interne (1M tokens)** : ce que l'IA stocke et indexe en local (historique, documents, contexte cumulatif)
> - **Fenêtre de contexte LLM (4k–8k tokens)** : ce qui est réellement envoyé à Ollama pour chaque génération de réponse (défini par `num_ctx` dans le `Modelfile`)
>
> Le moteur de recherche sémantique sélectionne les fragments les plus pertinents dans la mémoire interne, puis les injecte dans la fenêtre LLM disponible.

### 🎯 Chiffres Clés
- **1 000 000 tokens** de capacité de stockage en mémoire vectorielle interne
- **Fenêtre LLM effective** : 4 096 tokens (défaut `Modelfile`) jusqu'à 8 192 tokens (`local_llm.py`)
- **Compression intelligente** : 2.4:1 à 52:1 selon le contenu
- **Persistance SQLite** optimisée pour les gros volumes
- **Recherche sémantique** ultra-rapide (TF-IDF + cosinus)
- **Architecture 100% locale** sans cloud

## 🧠 Architecture Technique Ultra

### Composants Clés

#### 1. UltraCustomAI (`models/ultra_custom_ai.py`)
```python
from models.ultra_custom_ai import UltraCustomAIModel
from core.ai_engine import AIEngine

# Initialisation Ultra
base_engine = AIEngine()
ultra_ai = UltraCustomAIModel(base_engine)

# Génération avec contexte étendu
response = ultra_ai.generate_response("Analyse ce projet complet")
print(response['ultra_stats'])  # Statistiques 1M tokens
```

#### 2. IntelligentContextManager (`models/intelligent_context_manager.py`)
```python
from models.intelligent_context_manager import UltraIntelligentContextManager

# Gestionnaire de contexte intelligent
context_mgr = UltraIntelligentContextManager()

# Ajout de contenu avec chunking intelligent
context_mgr.add_content("Document très long...", "document")

# Recherche sémantique ultra-rapide
results = context_mgr.search_relevant_chunks("ma requête", limit=10)
```

#### 3. MillionTokenContextManager (`models/million_token_context_manager.py`)
```python
from models.million_token_context_manager import MillionTokenContextManager

# Persistance et compression
token_mgr = MillionTokenContextManager()

# Ajout de gros volumes avec compression automatique
token_mgr.add_document("gros_document.pdf", auto_compress=True)

# Statistiques en temps réel
stats = token_mgr.get_stats()
print(f"Tokens utilisés: {stats['current_tokens']:,} / 1,048,576")
```

## ⚡ Performances et Optimisations

### Système de Compression Intelligent

| Type de Contenu | Ratio Moyen | Exemple |
|------------------|-------------|---------|
| Texte répétitif | 15:1 à 52:1 | Logs, documentation répétitive |
| Code Python | 3:1 à 8:1 | Fichiers sources avec commentaires |
| Documents PDF | 4:1 à 12:1 | Articles, rapports |
| Conversations | 2:1 à 4:1 | Échanges utilisateur-IA |

### Base de Données SQLite Optimisée
```sql
-- Structure de la table de contexte
CREATE TABLE context_chunks (
    id TEXT PRIMARY KEY,
    content_hash TEXT,
    compressed_content BLOB,
    tokens INTEGER,
    importance REAL,
    chunk_type TEXT,
    created_at TIMESTAMP,
    last_accessed TIMESTAMP
);

-- Index pour recherche ultra-rapide
CREATE INDEX idx_importance ON context_chunks(importance DESC);
CREATE INDEX idx_type_tokens ON context_chunks(chunk_type, tokens);
```

### Recherche Sémantique Ultra-Rapide
- **TF-IDF Vectorization** : Analyse sémantique des requêtes
- **Similarité Cosinus** : Matching précis des chunks pertinents
- **Fallback Intelligent** : Système sans sklearn pour compatibilité totale
- **Cache Adaptatif** : Accélération des requêtes répétées

## 🎨 Interface Ultra Moderne

### Fonctionnalités Avancées
- **Coloration Syntaxique Python** : Pygments intégré
- **Formatage Markdown** : Gras, italique, liens cliquables
- **Blocs de Code** : Support natif ```python```
- **Animation de Frappe** : Optimisée pour réponses 1M tokens
- **Hauteur Adaptative** : Auto-ajustement selon le contenu
- **Stats en Temps Réel** : Monitoring du contexte utilisé

### Interface Graphique Moderne
```python
# Lancement de l'interface Ultra
from interfaces.gui_modern import ModernAIInterface

# Configuration Ultra automatique
interface = ModernAIInterface()
interface.configure_ultra_mode(max_tokens=1048576)
interface.run()
```

## 🔧 Configuration et Personnalisation

### Configuration Ultra (ultra_config.py)
```python
ULTRA_CONFIG = {
    'max_context_length': 1000000,  # Capacité mémoire vectorielle interne
    'compression_ratio': 'auto',    # Automatique selon contenu
    'chunk_size': 512,              # Taille des chunks
    'overlap_size': 50,             # Recouvrement entre chunks
    'database_path': 'data/ultra_context.db',
    'enable_semantic_search': True,
    'search_algorithm': 'tfidf_cosine',
    'auto_optimize': True,
    'max_memory_mb': 1024
}
```

### Variables d'Environnement
```bash
# Activation du mode Ultra
export ENABLE_ULTRA_MODE=true
export MAX_CONTEXT_TOKENS=1048576
export ULTRA_DB_PATH="data/ultra_context.db"

# Optimisations performances
export ULTRA_CHUNK_SIZE=512
export ULTRA_COMPRESSION="auto"
export ULTRA_SEARCH_ALGO="tfidf_cosine"
```

## 📊 Monitoring et Statistiques

### Métriques Temps Réel
```python
from models.ultra_custom_ai import UltraCustomAIModel

ultra_ai = UltraCustomAIModel()
stats = ultra_ai.get_context_stats()

print(f"""
🚀 STATISTIQUES MÉMOIRE VECTORIELLE :
   📊 Tokens en mémoire interne : {stats['current_tokens']:,} / {stats['max_context_length']:,}
   ⚠️  Fenêtre LLM effective (Ollama) : 4 096 – 8 192 tokens
   📄 Documents traités : {stats['documents_processed']}
   🧩 Chunks créés : {stats['chunks_created']}
   🗜️  Ratio compression : {stats.get('compression_ratio', 'N/A')}
   ⚡ Temps recherche moyen : {stats.get('avg_search_time_ms', 'N/A')} ms
   💾 Taille DB : {stats.get('database_size_mb', 'N/A')} MB
""")
```

### Logs et Débogage
```python
import logging

# Configuration logging Ultra
logging.basicConfig(
    level=logging.INFO,
    format='[ULTRA] %(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/ultra_1m_tokens.log'),
        logging.StreamHandler()
    ]
)
```

## 🛠️ Dépannage et FAQ

### Problèmes Courants

#### "Mémoire insuffisante"
```bash
# Solution : Ajuster la taille des chunks
export ULTRA_CHUNK_SIZE=256  # Plus petits chunks
export ULTRA_MAX_MEMORY_MB=2048  # Plus de RAM autorisée
```

#### "Base de données corrompue"
```bash
# Réinitialisation complète
python -c "from models.million_token_context_manager import MillionTokenContextManager; mgr = MillionTokenContextManager(); mgr.reset_database()"
```

#### "Recherche lente"
```bash
# Optimisation des index
python -c "from models.intelligent_context_manager import UltraIntelligentContextManager; mgr = UltraIntelligentContextManager(); mgr.optimize_database()"
```

### Performance Optimale

#### Configuration Recommandée
- **RAM** : 16 GB minimum pour utilisation intensive
- **Stockage** : SSD recommandé (base SQLite)
- **Processeur** : Multi-core pour compression parallèle
- **Python** : 3.10+ pour performances optimales

#### Bonnes Pratiques
1. **Chunking adaptatif** : Laisser l'auto-détection
2. **Compression automatique** : Mode auto selon le contenu
3. **Maintenance régulière** : Nettoyage périodique des chunks anciens
4. **Monitoring continu** : Surveillance de l'usage mémoire

---

*Documentation générée automatiquement le 3 Septembre 2025 pour My Personal AI Ultra v5.0.0*
