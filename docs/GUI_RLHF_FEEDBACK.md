# 👍👎 Boutons de Feedback RLHF dans l'Interface

## Présentation

L'interface GUI moderne intègre maintenant des **boutons de feedback** sous chaque réponse de l'IA.

## Utilisation

### Interface visuelle

Après chaque réponse de l'IA, vous verrez :

```
[Réponse de l'IA ici...]

👍  👎  14:32
```

- **👍 Pouce en haut** : Indique que la réponse était bonne/utile
- **👎 Pouce en bas** : Indique que la réponse n'était pas satisfaisante
- **14:32** : Timestamp de la réponse

### Position des boutons

Les boutons sont placés **à gauche du timestamp**, exactement comme dans l'interface web de Claude.

## Fonctionnement automatique

### Collecte en arrière-plan

Chaque fois que vous cliquez sur un bouton :

1. ✅ Le feedback est **automatiquement enregistré** dans la base SQLite
2. 📊 Les **statistiques** sont mises à jour
3. 🧠 Les **patterns** sont analysés et appris
4. 💾 Tout est sauvegardé dans `data/rlhf_feedback.db`

### Intégration RLHF Manager

```python
# Ce qui se passe en arrière-plan lors d'un 👍 :
rlhf.record_interaction(
    user_query="Votre question...",
    ai_response="La réponse de l'IA...",
    feedback_type="positive",    # 👍
    feedback_score=5,             # Score maximum
    intent="conversation",
    confidence=1.0,
    model_version="ollama"
)

# Ce qui se passe lors d'un 👎 :
rlhf.record_interaction(
    user_query="Votre question...",
    ai_response="La réponse de l'IA...",
    feedback_type="negative",    # 👎
    feedback_score=1,             # Score minimum
    intent="conversation",
    confidence=1.0,
    model_version="ollama"
)
```

## Lancement

```bash
# Lancer l'interface GUI avec les boutons de feedback
python launch_unified.py

# Ou
.\launch.bat
```

## Consulter les feedbacks collectés

### Via Python

```python
from core.rlhf_manager import get_rlhf_manager

rlhf = get_rlhf_manager()

# Statistiques globales
stats = rlhf.get_statistics("all")
print(f"Interactions totales : {stats['total_interactions']}")
print(f"Feedbacks positifs : {stats['positive_count']}")
print(f"Feedbacks négatifs : {stats['negative_count']}")
print(f"Satisfaction : {stats['satisfaction_score']:.2%}")

# Patterns appris
patterns = rlhf.get_learned_patterns(min_confidence=0.7)
for p in patterns:
    print(f"{p['pattern_type']} - Confiance : {p['confidence']:.2f}")
```

### Via la console

Pendant que vous utilisez l'interface, les feedbacks s'affichent dans la console :

```
✅ Feedback positif enregistré
❌ Feedback négatif enregistré
```

## Workflow recommandé

### Phase 1 : Utilisation quotidienne (1-2 semaines)
- ✅ Utilisez l'IA normalement
- ✅ Cliquez sur 👍 quand la réponse est bonne
- ✅ Cliquez sur 👎 quand la réponse n'est pas satisfaisante
- ✅ Tout est collecté automatiquement

### Phase 2 : Analyse (après 100+ interactions)
```python
from core.rlhf_manager import get_rlhf_manager

rlhf = get_rlhf_manager()
stats = rlhf.get_statistics("all")

# Vérifier si vous avez assez de données
if stats['positive_count'] >= 50:
    print("✅ Assez de données pour un fine-tuning")
    
    # Exporter pour entraînement
    count = rlhf.export_training_data(
        "data/rlhf_training.jsonl",
        min_score=3
    )
    print(f"{count} exemples exportés")
```

### Phase 3 : Fine-tuning (optionnel)
Voir [ADVANCED_FEATURES.md](ADVANCED_FEATURES.md) pour créer un modèle amélioré.

## Avantages

✅ **Interface intuitive** : Feedback en un clic
✅ **Collecte automatique** : Rien à configurer
✅ **Base de données persistante** : Vos feedbacks sont sauvegardés
✅ **Amélioration continue** : L'IA apprend de vos préférences
✅ **Statistiques en temps réel** : Consultez l'évolution
✅ **Style professionnel** : Design inspiré de Claude

## Architecture technique

### Fichiers modifiés

- [`interfaces/gui/message_bubbles.py`](../interfaces/gui/message_bubbles.py)
  - Ajout de `_show_timestamp_for_current_message()` avec boutons
  - Callbacks `_on_thumbs_up()` et `_on_thumbs_down()`
  - Stockage de `_last_user_query` et `_last_ai_response`

### Intégration

```
Interface GUI (message_bubbles.py)
        ↓
    Boutons 👍 👎
        ↓
   RLHF Manager (rlhf_manager.py)
        ↓
  SQLite Database (data/rlhf_feedback.db)
        ↓
   Pattern Learning & Statistics
```

## Données collectées

Pour chaque feedback :

| Champ | Description | Exemple |
|-------|-------------|---------|
| `user_query` | Votre question | "Comment installer Python ?" |
| `ai_response` | Réponse de l'IA | "Pour installer Python..." |
| `feedback_type` | Type de feedback | "positive" ou "negative" |
| `feedback_score` | Score numérique | 5 (👍) ou 1 (👎) |
| `timestamp` | Date et heure | "2026-02-11 14:32:15" |
| `model_version` | Modèle utilisé | "ollama" |
| `intent` | Type d'interaction | "conversation" |
| `confidence` | Confiance IA | 1.0 |

## Confidentialité

- ✅ Toutes les données restent **100% locales**
- ✅ Base SQLite stockée dans `data/rlhf_feedback.db`
- ✅ Aucune transmission externe
- ✅ Vous contrôlez vos données

## Prochaines étapes

Après avoir collecté ~100-200 feedbacks :

1. **Analysez les patterns** : Voyez ce que l'IA a appris
2. **Exportez les données** : Créez un jeu d'entraînement
3. **Fine-tunez Ollama** : (Optionnel) Créez un modèle personnalisé
4. **Continuez la collecte** : Plus de données = meilleure IA

---

**Prêt à commencer ?**

```bash
python launch_unified.py
```

Puis cliquez simplement sur 👍 ou 👎 après chaque réponse ! 🚀
