# 🚀 Guide d'Utilisation - Fonctionnalités Avancées

Ce guide explique comment utiliser les fonctionnalités avancées :

## 📚 Table des Matières

1. [RLHF Manager](#-rlhf-manager)
2. [Training Manager](#-training-manager)
3. [Compression Monitor](#-compression-monitor)
4. [Intégration MCP (Model Context Protocol)](#-intégration-mcp)
5. [ChatOrchestrator — Boucle Agentique Avancée](#-chatorchestrator--boucle-agentique-avancée-v670)
6. [Modules v7.0.0](#-modules-v700)

---

## 🤖 RLHF Manager

Le **RLHF Manager** collecte automatiquement le feedback utilisateur et améliore le modèle de manière continue.

### ✨ Fonctionnalités

- ✅ Collecte automatique du feedback
- ✅ Détection des patterns de succès/échec
- ✅ Apprentissage progressif
- ✅ Statistiques détaillées
- ✅ Export des données d'entraînement

### 💻 Utilisation

```python
from core.rlhf_manager import get_rlhf_manager

# Obtenir l'instance singleton
rlhf = get_rlhf_manager()

# Enregistrer une interaction avec feedback
interaction_id = rlhf.record_interaction(
    user_query="Comment installer Python ?",
    ai_response="Pour installer Python...",
    feedback_type="positive",  # 'positive', 'negative', 'neutral'
    feedback_score=5,  # 0-5
    intent="technical_question",
    confidence=0.9,
    model_version="qwen3.5:4b"
)

# Obtenir les statistiques
stats = rlhf.get_statistics("session")  # 'session', 'today', 'all'
print(f"Satisfaction: {stats['satisfaction_score']:.2%}")

# Voir les patterns appris
patterns = rlhf.get_learned_patterns(min_confidence=0.7)
for pattern in patterns:
    print(f"{pattern['pattern_type']}: {pattern['confidence']:.2f}")

# Exporter pour entraînement
count = rlhf.export_training_data(
    "data/rlhf_training.jsonl",
    min_score=3
)
print(f"{count} exemples exportés")
```

### 📊 Métriques Disponibles

- **Taux de satisfaction** : (positifs - négatifs) / total
- **Taux de feedback positif** : positifs / total
- **Score moyen** : moyenne des scores 0-5
- **Patterns appris** : nombre de patterns détectés
- **Confiance** : niveau de confiance des patterns

### 🎯 Intégration dans votre code

```python
# Dans votre fonction de génération de réponse
response = ai_engine.generate(user_query)

# Enregistrer automatiquement
rlhf.record_interaction(
    user_query=user_query,
    ai_response=response,
    feedback_type="neutral",  # Par défaut
    intent=detected_intent,
    confidence=confidence_score
)

# L'utilisateur peut donner un feedback explicite plus tard
# qui sera lié à cette interaction
```

---

## 🎓 Training Manager

Le **Training Manager** gère l'entraînement et le fine-tuning des modèles locaux avec monitoring en temps réel.

### ✨ Fonctionnalités

- ✅ Entraînement de modèles personnalisés
- ✅ Fine-tuning pour Ollama
- ✅ Checkpointing automatique
- ✅ Validation et métriques
- ✅ Callbacks pour monitoring
- ✅ Export des résultats

### 💻 Utilisation - Entraînement Standard

```python
from core.training_manager import get_training_manager

# Obtenir l'instance
trainer = get_training_manager()

# Préparer les données
train_data = [
    {"input": "Question ?", "target": "Réponse..."},
    # ... plus de données
]

val_data = [
    {"input": "Question validation ?", "target": "Réponse..."},
    # ...
]

# Créer un run d'entraînement
run_id = trainer.create_run(
    run_name="my_model",
    config={"description": "Mon modèle personnalisé"}
)

# Callback pour suivre la progression
def on_epoch_end(epoch, metrics):
    print(f"Époque {epoch + 1} - Loss: {metrics['train_loss']:.4f}")

# Entraîner
results = trainer.train_model(
    train_data=train_data,
    val_data=val_data,
    epochs=5,
    batch_size=8,
    learning_rate=1e-4,
    model_name="custom_assistant",
    save_every=1,
    validate_every=1,
    on_epoch_end=on_epoch_end
)

print(f"Loss finale: {results['final_loss']:.4f}")
```

### 💻 Utilisation - Fine-tuning Ollama

```python
from core.training_manager import get_training_manager

trainer = get_training_manager()

# Créer un run
trainer.create_run(run_name="ollama_custom")

# Données de fine-tuning
train_data = [
    {"input": "Qui es-tu ?", "target": "Je suis My AI..."},
    {"input": "Que peux-tu faire ?", "target": "Je peux..."},
    # ... plus d'exemples
]

# Préparer le fine-tuning pour Ollama
result = trainer.fine_tune_ollama_model(
    base_model="qwen3.5:4b",
    train_data=train_data,
    new_model_name="my_ai_custom",
    epochs=5
)

print(f"Modelfile créé: {result['modelfile_path']}")
print(f"Voir instructions: {result['instructions_path']}")

# Ensuite, dans le terminal:
# ollama create my_ai_custom -f chemin/vers/Modelfile
```

### 📊 Métriques Suivies

- **Loss d'entraînement** : par époque et par batch
- **Loss de validation** : si données de validation fournies
- **Accuracy** : précision sur le jeu de validation
- **Durée** : temps par époque
- **Checkpoints** : sauvegardés automatiquement

### 🎯 Structure des Outputs

```
models/training_runs/
└── my_model_20260211_143052/
    ├── config.json           # Configuration de l'entraînement
    ├── summary.json          # Résumé des résultats
    ├── metrics.jsonl         # Métriques par époque
    ├── checkpoints/
    │   ├── checkpoint_epoch_1/
    │   ├── checkpoint_epoch_2/
    │   └── ...
    └── INSTRUCTIONS.txt      # (pour Ollama)
```

---

## 📊 Compression Monitor

Le **Compression Monitor** analyse et expose les métriques de compression intelligente du système.

### ✨ Fonctionnalités

- ✅ Calcul des ratios de compression réels
- ✅ Analyse par type de contenu
- ✅ Métriques d'efficacité
- ✅ Score de qualité
- ✅ Rapports détaillés
- ✅ Historique des compressions

### 💻 Utilisation Directe

```python
from core.compression_monitor import get_compression_monitor

# Obtenir l'instance
monitor = get_compression_monitor()

# Analyser une compression
original_text = "Mon texte original très long..."
chunks = ["chunk 1...", "chunk 2...", "chunk 3..."]

analysis = monitor.analyze_compression(
    original_text=original_text,
    chunks=chunks,
    document_name="mon_document.txt",
    content_type="text",
    metadata={"category": "tutorial"}
)

print(f"Ratio: {analysis['compression_ratio_formatted']}")
print(f"Efficacité: {analysis['efficiency']:.1f}%")
print(f"Score qualité: {analysis['quality_score']:.1f}/100")

# Statistiques globales
stats = monitor.get_stats()
print(f"Ratio moyen: {stats['average_ratio_formatted']}")
print(f"Meilleur ratio: {stats['best_ratio_formatted']}")

# Rapport détaillé
print(monitor.get_compression_report())
```

### 💻 Utilisation avec VectorMemory

Le Compression Monitor est **automatiquement intégré** dans VectorMemory :

```python
from memory.vector_memory import VectorMemory

memory = VectorMemory(max_tokens=1_000_000)

# Les métriques de compression sont calculées automatiquement
result = memory.add_document(
    content="Mon texte...",
    document_name="document.txt",
    metadata={"type": "text"}
)

# Les métriques sont incluses dans le résultat
if 'compression' in result:
    comp = result['compression']
    print(f"Ratio: {comp['ratio_formatted']}")
    print(f"Efficacité: {comp['efficiency']:.1f}%")

# Statistiques complètes avec compression
stats = memory.get_stats()
if 'compression' in stats:
    print(f"Ratio moyen: {stats['compression']['average_ratio_formatted']}")

# Rapport de compression
print(memory.get_compression_report())
```

### 📊 Métriques Calculées

#### Ratios de Compression

- **Compression Ratio** : taille_originale / taille_compressée
  - `2.4:1` = compression modeste (2.4x plus efficace)
  - `10:1` = bonne compression
  - `52:1` = excellente compression

#### Efficacité

- **Overhead** : redondance due au chevauchement des chunks
- **Efficacité** : 100 - overhead_percent
- **Espace économisé** :Bytes et pourcentage

#### Qualité

- **Score de qualité** : métrique composite 0-100
  - Basé sur le ratio, l'efficacité, le nombre de chunks
  - Plus élevé = meilleure compression

### 📈 Analyse par Type de Contenu

Le moniteur suit séparément chaque type :

```python
stats = monitor.get_stats()

# Stats par type
for content_type, type_stats in stats['by_content_type'].items():
    print(f"{content_type}:")
    print(f"  Documents: {type_stats['count']}")
    print(f"  Ratio: {type_stats['average_ratio']:.1f}:1")
```

Types reconnus : `text`, `code`, `pdf`, `docx`, `data`, `html`, etc.

---

## 🎯 Exemples Complets

Un fichier d'exemples complets est disponible : [examples/advanced_features_demo.py](../examples/advanced_features_demo.py)

Pour l'exécuter :

```bash
python examples/advanced_features_demo.py
```

---

## 🦙 Intégration avec Ollama

### À quoi servent ces fonctionnalités ?

#### 1. RLHF Manager - Apprendre de vos feedbacks
**Problème résolu :** L'IA ne "se souvient" pas de ce qui a fonctionné ou échoué.

**Solution :** 
- ✅ Collecte automatique chaque fois que vous donnez un 👍 ou 👎
- ✅ Détecte les patterns : "Quand je réponds comme ça → feedback positif"
- ✅ Mémorise ce qui fonctionne bien dans votre contexte
- ✅ Permet d'améliorer l'IA avec VOS propres données

**Valeur pratique :**
```
Avant : L'IA répond toujours pareil, peu importe vos préférences
Après  : L'IA apprend votre style, votre vocabulaire, votre domaine
```

#### 2. Training Manager - Entraîner sur VOS données
**Problème résolu :** Les modèles génériques ne connaissent pas votre domaine.

**Solution :**
- ✅ Créez un modèle spécialisé sur VOS documents
- ✅ Entraînez sur le vocabulaire de votre entreprise
- ✅ Fine-tunez sur vos processus internes
- ✅ Générez un modèle Ollama personnalisé

**Valeur pratique :**
```
Avant  : qwen3.5 générique → connaissances générales
Après  : qwen3.5-votre-entreprise → connaît vos process, votre jargon
```

#### 3. Compression Monitor - Optimiser la mémoire
**Problème résolu :** Vous ne savez pas si votre limite de 1M tokens est bien utilisée.

**Solution :**
- ✅ Mesure en temps réel l'efficacité de la compression
- ✅ Ratios de 2.4:1 à 52:1 selon le type de contenu
- ✅ Identifie les documents mal compressés
- ✅ Permet d'optimiser l'utilisation des 1M tokens

**Valeur pratique :**
```
Avant : "J'ai stocké 50 documents, mais combien d'espace reste-t-il ?"
Après  : "Ratio 15.3:1, efficacité 87%, il me reste 750k tokens disponibles"
```

### Qu'est-ce qui est automatique avec Ollama ?

| Fonctionnalité | Automatique ? | Détails |
|----------------|---------------|---------|
| **Compression Monitor** | ✅ 100% | Intégré dans VectorMemory, métriques en temps réel |
| **RLHF - Collecte feedback** | ✅ Automatique | Chaque interaction enregistrée automatiquement |
| **RLHF - Détection patterns** | ✅ Automatique | Analyse automatique, patterns appris en continu |
| **RLHF - Export données** | ⚠️ Manuel | Vous décidez quand exporter : `rlhf.export_training_data()` |
| **Training - Préparation données** | ✅ Automatique | Formatage JSONL, Modelfile généré automatiquement |
| **Training - Fine-tuning Ollama** | ❌ Manuel | Vous devez lancer : `ollama create nom_modele -f Modelfile` |
| **Training - Utilisation nouveau modèle** | ❌ Manuel | Vous choisissez quand passer au nouveau modèle |

### Pourquoi le fine-tuning n'est-il pas automatique ?

**C'est volontaire et c'est une BONNE chose :**

1. **Sécurité** 🔒
   - Vous contrôlez quand un nouveau modèle est créé
   - Pas de modification surprise de votre modèle en production
   - Vous pouvez tester avant de déployer

2. **Contrôle** 🎮
   - Vous décidez quand vous avez assez de données (100 ? 1000 ? 10000 exemples ?)
   - Vous choisissez le bon moment (pas pendant une démo importante)
   - Vous validez la qualité avant utilisation

3. **Transparence** 👁️
   - Le Modelfile est généré et visible
   - Les INSTRUCTIONS.txt expliquent exactement quoi faire
   - Vous comprenez ce qui se passe

### Workflow recommandé

```
┌──────────────────────────────────────────────────────────────┐
│ Phase 1 : COLLECTE (1-2 semaines) - AUTOMATIQUE              │
├──────────────────────────────────────────────────────────────┤
│  • Utilisez l'IA normalement avec Ollama                     │
│  • Donnez des feedbacks                                      │
│  • RLHF collecte automatiquement toutes les interactions     │
│  • Compression Monitor suit l'efficacité en temps réel       │
└──────────────────────────────────────────────────────────────┘
                            ▼
┌──────────────────────────────────────────────────────────────┐
│ Phase 2 : ANALYSE - AUTOMATIQUE                              │
├──────────────────────────────────────────────────────────────┤
│  • Consultez les statistiques RLHF                           │
│  • Vérifiez les patterns appris (confiance > 0.7)            │
│  • Regardez les métriques de compression                     │
└──────────────────────────────────────────────────────────────┘
                            ▼
┌──────────────────────────────────────────────────────────────┐
│ Phase 3 : DÉCISION - VOUS DÉCIDEZ                            │
├──────────────────────────────────────────────────────────────┤
│  • "J'ai 500 exemples positifs, c'est suffisant ?"           │
│  • "Les patterns détectés sont-ils corrects ?"               │
│  • "C'est le bon moment pour améliorer le modèle ?"          │
└──────────────────────────────────────────────────────────────┘
                            ▼
┌──────────────────────────────────────────────────────────────┐
│ Phase 4 : FINE-TUNING - SEMI-AUTOMATIQUE (10 minutes)        │
├──────────────────────────────────────────────────────────────┤
│  1. Exporter : rlhf.export_training_data()    [automatique]  │
│  2. Préparer : trainer.fine_tune_ollama_model() [automatique]│
│  3. Créer modèle : ollama create ...          [VOUS]         │
│  4. Tester le nouveau modèle                  [VOUS]         │
│  5. Basculer en production si OK              [VOUS]         │
└──────────────────────────────────────────────────────────────┘
                            ▼
┌──────────────────────────────────────────────────────────────┐
│ Phase 5 : AMÉLIORATION CONTINUE                              │
├──────────────────────────────────────────────────────────────┤
│  • Recommencer le cycle avec le nouveau modèle               │
│  • Chaque itération améliore davantage l'IA                  │
└──────────────────────────────────────────────────────────────┘
```

### Deux façons d'utiliser ces fonctionnalités

#### Option A : Amélioration périodique (RECOMMANDÉ)
```python
# 1. Collecte automatique pendant 2 semaines
# (juste utiliser l'IA normalement)

# 2. Tous les 15 jours : fine-tuning manuel
rlhf = get_rlhf_manager()
trainer = get_training_manager()

# Exporter les bons exemples
count = rlhf.export_training_data("data/train.jsonl", min_score=3)
print(f"{count} exemples exportés")

# Préparer le fine-tuning
result = trainer.fine_tune_ollama_model(
    base_model="qwen3.5",
    train_data_path="data/train.jsonl",
    new_model_name="qwen3.5-improved-v2"
)

# Créer le nouveau modèle (dans le terminal)
# ollama create qwen3.5-improved-v2 -f chemin/vers/Modelfile

# Tester et basculer si satisfait
```

#### Option B : Collecte seule (insights manuels)
```python
# Collectez les données, mais ne faites JAMAIS de fine-tuning
# Utilisez juste les statistiques pour comprendre :

rlhf = get_rlhf_manager()

# Insights manuels
stats = rlhf.get_statistics("all")
print(f"Satisfaction globale : {stats['satisfaction_score']:.2%}")

patterns = rlhf.get_learned_patterns(min_confidence=0.8)
for p in patterns:
    print(f"Pattern type {p['pattern_type']} : confiance {p['confidence']:.2f}")
    # Vous appliquez manuellement ces insights dans votre code

# Métriques de compression
monitor = get_compression_monitor()
stats = monitor.get_stats()
print(f"Efficacité moyenne : {stats['average_efficiency']:.1f}%")
# Vous optimisez manuellement selon ces informations
```

---

## 🔗 Intégration avec l'IA Principale

Ces modules sont conçus pour s'intégrer seamlessly avec le reste du système :

### Dans AIEngine

```python
# Dans ai_engine.py
from core.rlhf_manager import get_rlhf_manager
from core.training_manager import get_training_manager

class AIEngine:
    def __init__(self):
        # ...
        self.rlhf_manager = get_rlhf_manager()
        self.training_manager = get_training_manager()
    
    def process_query(self, query):
        response = self.model.generate(query)
        
        # Enregistrer automatiquement
        self.rlhf_manager.record_interaction(
            user_query=query,
            ai_response=response,
            # ...
        )
        
        return response
```

### Dans l'Interface GUI

```python
# Ajouter un bouton "Bon ✓" / "Mauvais ✗"
def on_good_feedback():
    rlhf.record_interaction(
        user_query=last_query,
        ai_response=last_response,
        feedback_type="positive",
        feedback_score=5
    )

def on_bad_feedback():
    rlhf.record_interaction(
        user_query=last_query,
        ai_response=last_response,
        feedback_type="negative",
        feedback_score=1
    )
```

---

## 📝 Notes Importantes

1. **RLHF Manager**
   - Les patterns sont appris automatiquement
   - Base SQLite créée dans `data/rlhf_feedback.db`
   - Exporter régulièrement les données pour entraînement

2. **Training Manager**
   - Les runs sont sauvegardés dans `models/training_runs/`
   - Checkpoints dans `models/checkpoints/`
   - Pour Ollama, suivre les instructions dans `INSTRUCTIONS.txt`

3. **Compression Monitor**
   - Intégré automatiquement dans VectorMemory
   - Les métriques sont calculées en temps réel
   - Pas de stockage persistant (stats en mémoire)

---

## 🔌 Intégration MCP

Le **Model Context Protocol (MCP)** permet à l'IA d'interagir avec des outils locaux et des serveurs externes de manière standardisée.

### ✨ Fonctionnalités

- ✅ Outils locaux (LocalTools) orchestrant l'accès root : création/déplacement de dossiers et fichiers directement sur le PC, recherche et lecture locale de l'ordinateur de manière sécurisée.
- ✅ Connexion aux serveurs MCP externes via `stdio`
- ✅ Découverte automatique des outils
- ✅ Dégradation gracieuse si le SDK n'est pas installé

### 💻 Utilisation

L'intégration MCP est gérée par `core/mcp_client.py`. L'IA décide de manière autonome quand utiliser les outils mis à sa disposition.

Pour plus de détails, consultez le guide dédié : [🔌 Intégration MCP](MCP_INTEGRATION.md).

---

## 🧠 ChatOrchestrator — Boucle Agentique Avancée

Le **ChatOrchestrator** (`core/chat_orchestrator.py`) est la boucle agentique de la page Chat. Il remplace l'appel direct à `LocalLLM.generate_with_tools_stream()` dans `AIEngine.process_query_stream()` et implémente trois design patterns modernes.

### ✨ Fonctionnalités

- ✅ **Pattern ReAct** (Reasoning + Acting) : boucle `Réfléchis → Agis → Observe` à chaque tour
- ✅ **Plan & Execute** : génération automatique d'un plan structuré pour les requêtes > 55 caractères
- ✅ **Scratchpad persistant** : état interne (objectif, plan, faits, tours restants) injecté dans le system prompt
- ✅ **Limite de tours** : `MAX_TOURS = 15` avec message forcé avant coupure
- ✅ **Détection de boucle** : `LoopDetector` stoppe les appels identiques consécutifs ou répétitifs
- ✅ **Élagage sélectif** du contexte (`MAX_HISTORY_MESSAGES = 40`)
- ✅ **Synthèse streamée** après exécution d'outils

### 💼 Architecture Interne

```
ChatOrchestrator.run(query, history, tools, tool_executor, stream_callback)
  │
  ├── 1. Planification (si len(query) > 55)
  │     └── Scratchpad.set_plan([steps])
  │
  ├── 2. Boucle ReAct (max MAX_TOURS tours)
  │     ├── Injection scratchpad dans system prompt
  │     ├── LLM génère : raisonnement + tool call
  │     ├── LoopDetector.check(tool_name, args)
  │     ├── Validation arguments (Pydantic)
  │     ├── Exécution outil → Observation
  │     └── Scratchpad.update_from_tool_result()
  │
  └── 3. Synthèse finale streamée
        └── Détection hallucinations (HALLUCINATION_MARKERS)
```

### ⚖️ Constantes configurables

| Constante | Valeur | Rôle |
|---|---|---|
| `MAX_TOURS` | 15 | Limite absolue de tours dans la boucle |
| `MAX_HISTORY_MESSAGES` | 40 | Élagage sélectif du contexte |
| `LOOP_THRESHOLD` | 2 | Appels identiques avant détecter boucle élargie |
| `COMPACT_THRESHOLD` | 28 | Messages avant compaction |
| `PLAN_MIN_QUERY_LEN` | 55 | Longueur minimale pour déclencher la planification |
| `MAX_TOOL_USES` | 5 | Appels outils avant synthèse forcée |

### 🖥️ Intégration dans AIEngine

Le `ChatOrchestrator` est instancié une fois dans `AIEngine` et appelé via `process_query_stream()` pour toute requête déclenchant du tool-calling. Il est **distinct** de `AgentOrchestrator` (page Agents, non affecté).

```python
# Dans AIEngine (simplifié)
from core.chat_orchestrator import ChatOrchestrator

class AIEngine:
    def __init__(self):
        self.chat_orchestrator = ChatOrchestrator()

    def process_query_stream(self, query, history, ...):
        # Si tool-calling détecté :
        yield from self.chat_orchestrator.run(
            query=query,
            history=history,
            tools=available_tools,
            tool_executor=self._execute_tool,
            stream_callback=stream_cb
        )
```

### 🛡️ Sécurités intégrées

```python
# Exemple : détection de boucle
detector = LoopDetector()
is_loop, msg = detector.check("web_search", {"query": "bitcoin price"})
if is_loop:
    # Le LLM est informé et invité à synthétiser
    stream_callback(msg)
    break

# Exemple : scratchpad
pad = Scratchpad(goal="Trouve le prix du Bitcoin et compare à 2024")
pad.set_plan(["Rechercher prix actuel", "Rechercher prix 2024", "Comparer"])
pad.update_from_tool_result("web_search", "Bitcoin: 94,500 USD (2026)")
pad.mark_step_done()
print(pad.to_context_block())  # Injecté dans le system prompt
```

---

## 🆕 Modules v7.0.0

La version 7.0.0 introduit 7 nouveaux modules avancés, tous optionnels et avec dégradation gracieuse si les dépendances sont manquantes.

### 🌐 API REST Locale (`core/api_server.py`)

Serveur HTTP intégré pour piloter My_AI depuis des outils externes :

```python
# Démarrage automatique si api.enabled = true dans config.yaml
# Le serveur tourne en thread daemon et n'interfère pas avec la GUI

# Endpoints disponibles :
# GET  /api/health        → État du serveur
# POST /api/chat          → Envoyer un message
# GET  /api/models        → Lister les modèles Ollama
# POST /api/models/switch → Changer de modèle
# GET  /api/conversations → Historique complet
# DELETE /api/conversations → Effacer l'historique
# GET  /api/stats         → Statistiques système
```

**Cas d'usage :** intégration avec des scripts Python, des notebooks Jupyter, ou des outils d'automatisation.

### 📜 Historique des Commandes (`core/command_history.py`)

Enregistrement persistant de toutes les requêtes utilisateur :

```python
# Ajouter une entrée (fait automatiquement par AIEngine)
history.add(query="Explique les closures en Python",
            response_preview="Les closures sont...",
            agent_type="code")

# Rechercher dans l'historique
results = history.search("closures", limit=5)

# Favoris
history.toggle_favorite(entry_id=42)
favorites = history.get_favorites()

# Statistiques
stats = history.get_stats()
# → {"total": 1234, "favorites": 15, "by_agent": {"code": 456, ...}}

# Nettoyage (conserve les favoris)
history.clear_old(days=30)
```

### 📤 Export de Conversations (`core/conversation_exporter.py`)

Export en 3 formats avec métadonnées :

```python
from core.conversation_exporter import ConversationExporter

exporter = ConversationExporter(output_dir="outputs/exports")

# Markdown (avec header métadonnées)
exporter.export_markdown(messages, metadata={"model": "qwen3.5:4b"})

# HTML (thème sombre CSS embarqué, style Claude)
exporter.export_html(messages, filename="rapport_analyse")

# PDF (via ReportLab, styles par rôle)
exporter.export_pdf(messages, metadata={"session": "debug_api"})
```

### 🧠 Base de Connaissances (`core/knowledge_base_manager.py`)

Stockage structuré de faits avec extraction automatique :

```python
from core.knowledge_base_manager import KnowledgeBaseManager

kb = KnowledgeBaseManager(db_path="data/knowledge_base/facts.db")

# Ajout manuel
kb.add_fact(category="technical", key="serveur prod", value="api.example.com:443")

# Extraction automatique depuis du texte
facts = kb.extract_facts_from_text("Je préfère VS Code pour le Python")
# → [{"category": "preference", "key": "préférence: VS Code pour le Python", ...}]

# Recherche
results = kb.search_facts("Python", category="preference")

# Contexte pour le prompt IA
context = kb.get_context_for_prompt("Quel éditeur utiliser ?")
# → "[Base de connaissances]\n- [preference] préférence: VS Code pour le Python (confiance: 70%)"
```

### 🌍 Détection de Langue (`core/language_detector.py`)

Détection automatique et génération de suffixes prompt :

```python
from core.language_detector import LanguageDetector

detector = LanguageDetector(default_language="fr")

# Détecter la langue
lang = detector.detect("What is the capital of France?")  # → "en"

# Nom de la langue dans sa propre langue
name = detector.get_language_name("en")  # → "English"

# Suffix pour le system prompt
suffix = detector.get_system_prompt_suffix("en")
# → "Respond in English."
```

### 💼 Workspaces (`core/session_manager.py`)

Gestion de sessions isolées :

```python
from core.session_manager import SessionManager

sm = SessionManager(workspaces_dir="data/workspaces")

# Créer un workspace
ws_id = sm.create_workspace("Projet API", description="Refactoring de l'API REST")

# Sauvegarder l'état
sm.save_workspace(ws_id, {
    "conversation_history": [...],
    "attached_documents": [...],
    "active_agents": ["code", "debug"],
    "settings": {"model": "qwen3.5:9b"}
})

# Charger un workspace
state = sm.load_workspace(ws_id)

# Lister tous les workspaces
workspaces = sm.list_workspaces()

# Auto-save (appelé périodiquement)
sm.auto_save(ws_id, current_state)
```

### 🗄️ Cache Web (`core/web_cache.py`)

Cache persistant pour les recherches internet :

```python
from core.web_cache import WebCache

cache = WebCache(cache_dir="data/web_cache", ttl_seconds=3600, max_entries=1000)

# Vérifier le cache
cached = cache.get("https://example.com/api/data")
if cached is None:
    # Faire la requête et stocker le résultat
    result = fetch_url("https://example.com/api/data")
    cache.put("https://example.com/api/data", result)

# Statistiques
stats = cache.stats()  # → {"hits": 42, "misses": 8, "size": 156}

# Invalidation sélective
cache.invalidate("https://example.com/api/data")
```

### Initialisation dans AIEngine

Tous ces modules sont initialisés dans `AIEngine._init_v7_modules()` avec dégradation gracieuse :

```python
# Si un module n'est pas disponible (dépendance manquante),
# un warning est loggé et le module est mis à None.
# Le reste de l'application fonctionne normalement.
```

---

## 🚀 Prochaines Étapes

1. Tester les exemples fournis
2. Intégrer dans votre workflow
3. Ajuster les paramètres selon vos besoins
4. Consulter les logs pour le debugging
5. Explorer les modules v7.0.0 (API REST, exports, base de connaissances)

Pour toute question, consultez la documentation complète dans `docs/`.
