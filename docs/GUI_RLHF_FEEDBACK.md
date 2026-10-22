# ⭐ Feedback RLHF — Notation par étoiles

## Présentation

La fenêtre de l'appli intègre un **système de notation 1-5 étoiles** sous chaque réponse de l'IA.
Ce système remplace les anciens boutons 👍/👎 et permet un feedback plus précis.

## Utilisation

### Interface visuelle

Sous chaque réponse de l'IA, les actions apparaissent au survol (et restent visibles sous la
dernière réponse) : copier, lire à voix haute, régénérer, puis les étoiles, suivies de l'heure,
de la durée et de la vitesse de la réponse :

```
[Réponse de l'IA ici...]

⧉  🔊  ↻  ☆ ☆ ☆ ☆ ☆   14:32 · 6 s · 58 tokens/s   ◉◉◉ Sources
```

Le bouton **Sources** ne suit que les réponses appuyées sur une recherche web : les icônes des
trois premières sources, puis, au clic, la liste de toutes, en liens.

Survolez les étoiles pour un aperçu interactif, puis cliquez pour valider votre note :

| Note | Signification |
|------|---------------|
| ⭐ (1/5) | Réponse très mauvaise |
| ⭐⭐ (2/5) | Réponse insuffisante |
| ⭐⭐⭐ (3/5) | Réponse correcte |
| ⭐⭐⭐⭐ (4/5) | Bonne réponse |
| ⭐⭐⭐⭐⭐ (5/5) | Réponse excellente |

### Comportement après notation

- Les étoiles se remplissent et se **désactivent** (plus possible de noter deux fois)
- La note est gardée avec la conversation : elle reste affichée, et figée, quand la session se rouvre
- Un feedback 4-5 ⭐ est enregistré comme **positif**
- Un feedback 1-2 ⭐ est enregistré comme **négatif**
- Un feedback 3 ⭐ est enregistré comme **neutre**

## Fonctionnement automatique

### Collecte en arrière-plan

Chaque fois que vous cliquez sur une étoile :

1. ✅ Le feedback est **automatiquement enregistré** dans la base SQLite
2. 📊 Les **statistiques** sont mises à jour (session + métriques quotidiennes)
3. 🧠 Les **patterns** sont analysés et appris (mots-clés → score de confiance)
4. 💾 Tout est sauvegardé dans `data/rlhf_feedback.db`

### Intégration RLHF Manager

```python
# Ce qui se passe en arrière-plan lors d'un clic 5 étoiles :
rlhf.record_interaction(
    user_query="Votre question...",
    ai_response="La réponse de l'IA...",
    feedback_type="positive",    # déduit du score >= 4
    feedback_score=5,             # score sélectionné
    intent="conversation",
    confidence=1.0,
    model_version="ollama"
)

# Lors d'un clic 2 étoiles :
rlhf.record_interaction(
    user_query="Votre question...",
    ai_response="La réponse de l'IA...",
    feedback_type="negative",    # déduit du score <= 2
    feedback_score=2,
    intent="conversation",
    confidence=1.0,
    model_version="ollama"
)
```

## Lancement

```bash
.\launch.bat        # Windows
./launch.sh         # macOS / Linux
```

Sélectionnez l'interface graphique, puis notez chaque réponse en cliquant sur les étoiles.

## Consulter les feedbacks collectés

### Via Python

```python
from core.rlhf_manager import get_rlhf_manager

rlhf = get_rlhf_manager()

# Statistiques globales
stats = rlhf.get_statistics("all")
print(f"Interactions totales : {stats['total_interactions']}")
print(f"Score moyen         : {stats['average_score']:.1f}/5")
print(f"Taux de satisfaction : {stats['positive_rate']:.0%}")

# Patterns appris
patterns = rlhf.get_learned_patterns(min_confidence=0.7)
for p in patterns:
    print(f"{p['pattern_type']} – Confiance : {p['confidence']:.2f}")
```

## Workflow recommandé

### Phase 1 : Utilisation quotidienne (1-2 semaines)
- ✅ Utilisez l'IA normalement
- ✅ Notez chaque réponse honnêtement (1-5 ⭐)
- ✅ Tout est collecté automatiquement

### Phase 2 : Analyse (après 100+ interactions)
```python
from core.rlhf_manager import get_rlhf_manager

rlhf = get_rlhf_manager()
stats = rlhf.get_statistics("all")

if stats['total_interactions'] >= 100:
    print(f"Score moyen : {stats['average_score']:.1f}/5")

    # Exporter pour entraînement (uniquement les bonnes réponses ≥ 3/5)
    count = rlhf.export_training_data(
        "data/rlhf_training.jsonl",
        min_score=3
    )
    print(f"{count} exemples exportés")
```

### Phase 3 : Fine-tuning (optionnel)
Voir [ADVANCED_FEATURES.md](ADVANCED_FEATURES.md) pour créer un modèle amélioré.

## Architecture technique

### Fichiers concernés

- [`frontend/src/features/chat/MessageControls.tsx`](../frontend/src/features/chat/MessageControls.tsx)
  - `StarRating` : ligne d'étoiles, remplissage progressif au survol, figée une fois notée
- [`core/chat_service.py`](../core/chat_service.py)
  - `rate()` : appelle le RLHF Manager (question du tour, texte de la réponse, score)
    et garde la note dans la session (clé facultative `rating` du message)
- [`interfaces/desktop/server.py`](../interfaces/desktop/server.py)
  - `POST /api/conversation/messages/{mid}/rating` : route appelée par la fenêtre

### Flux de données

```
Fenêtre (StarRating, MessageControls.tsx)
        ↓
  Étoiles ☆☆☆☆☆ (clic) → POST /api/conversation/messages/{mid}/rating
        ↓
   ChatService.rate (core/chat_service.py)
        ↓
   RLHF Manager (rlhf_manager.py)
        ↓  ↓
  SQLite (feedback)  →  Patterns appris
  Métriques quotidiennes
```

## Données collectées

Pour chaque feedback :

| Champ | Description | Exemple |
|-------|-------------|---------|
| `user_query` | Votre question | "Comment installer Python ?" |
| `ai_response` | Réponse de l'IA | "Pour installer Python..." |
| `feedback_type` | Type déduit du score | "positive", "negative", "neutral" |
| `feedback_score` | Score 1-5 | 4 |
| `timestamp` | Date et heure | "2026-03-24 14:32:15" |
| `model_version` | Modèle utilisé | "ollama" |
| `intent` | Type d'interaction | "conversation" |
| `confidence` | Confiance IA | 1.0 |

## Confidentialité

- ✅ Toutes les données restent **100% locales**
- ✅ Base SQLite stockée dans `data/rlhf_feedback.db`
- ✅ Aucune transmission externe
- ✅ Vous contrôlez vos données (supprimable via `clean_project.bat` → niveau complet)

## Limites du système

> ⚠️ Le système RLHF **collecte** les feedbacks et **apprend des patterns de mots-clés**, mais il ne modifie **pas** les poids du modèle Ollama en temps réel.
>
> Pour une vraie amélioration du modèle, il faut activer le fine-tuning avec les données collectées (voir `ADVANCED_FEATURES.md`). Le paramètre `fine_tuning.enabled` dans `config.yaml` est désactivé par défaut.
