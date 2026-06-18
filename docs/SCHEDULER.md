# 📅 Scheduler proactif — Tâches planifiées

Le scheduler transforme My_AI d'un assistant **réactif** (vous lancez une tâche)
en assistant **proactif** : il exécute des agents, des workflows visuels ou des
débats de façon **récurrente** (type cron), puis vous notifie du résultat.

Exemples :
- « Chaque matin à 8h, lance le **WebAgent** sur l'actualité IA et résume. »
- « Tous les lundis à 9h, **audit de sécurité** du dossier X. »
- « Toutes les heures, surveille … »

100% local. Aucune dépendance à un service système : la boucle tourne **tant que
le GUI ou le Relay est lancé**.

---

## Comment ça marche

- **Exécution réutilisée, pas réimplémentée.** Le scheduler délègue à
  `relay/agent_relay.py` (`AgentRelayService.run_workflow` / `run_debate`), le
  même exécuteur *headless* que la page Agents mobile. Il gère single /
  séquentiel / parallèle / DAG et le streaming.
- **Boucle de thread maison** (`core/scheduler.py`) : se réveille toutes les
  `check_interval` secondes, exécute les tâches échues, recalcule la prochaine
  échéance.
- **Persistance JSON** : `data/scheduled_tasks.json` (cohérent avec
  `data/custom_agents.json`), écriture atomique.
- **Rapports** : chaque exécution écrit un `.md` dans `outputs/scheduled/`.

### Tâches manquées (app fermée à l'heure prévue)

Au démarrage, si `run_missed_on_startup` est actif, toute tâche dont l'échéance
est passée **et** dans la fenêtre `catch_up_window_hours` **et** dont
`run_if_missed` est coché est exécutée **une fois**, puis resynchronisée. Au-delà
de la fenêtre, elle est simplement reprogrammée sans s'exécuter.

### Défer-on-busy

Si l'exécuteur d'agents est déjà occupé (vous lancez un workflow depuis le GUI ou
le mobile), l'exécution planifiée est **différée** au prochain tick — on évite de
lancer deux charges LLM concurrentes sur Ollama. La tâche apparaît alors en statut
`deferred` et réessaie automatiquement.

> Le partage du gate d'exécution unique est garanti **entre les exécutions
> planifiées et le mobile** (quand le Relay tourne, il partage son
> `AgentRelayService` avec le scheduler). Une exécution lancée depuis la page
> Agents du **GUI desktop** utilise un orchestrateur distinct et n'est pas prise
> en compte par le défer.

---

## Utilisation (GUI)

Page **🤖 Agents** → section **📅 Tâches planifiées** (en bas) :

- **➕ Nouvelle tâche** : nom, **source** (agent seul / workflow du canvas / débat),
  prompt (ou sujet pour un débat), **planning**, et option *rattraper si manquée*.
- Chaque tâche affiche son planning, sa prochaine et sa dernière exécution + le
  statut. Boutons : **activer/désactiver**, **▶ exécuter maintenant**,
  **📝 éditer**, **✕ supprimer**.
- À la fin d'une tâche : **notification** (toast OS si disponible, sinon toast
  in-app) + entrée dans la page. Cliquer le toast ouvre le rapport `.md`.

> Pour un **workflow**, composez-le d'abord sur le canvas n8n de la page Agents,
> puis créez la tâche avec la source « Workflow (canvas) » : les nœuds et
> connexions sont figés dans la définition de la tâche.
>
> À l'**édition**, la source reste figée (on ne modifie que nom / tâche / planning
> / rattrapage). Pour changer de source, supprimez et recréez la tâche.

### Types de planning

| Type        | Paramètres                  | Exemple                       |
|-------------|-----------------------------|-------------------------------|
| Quotidien   | heure `HH:MM`               | tous les jours à 08:00        |
| Hebdo       | jours (Lun…Dim) + `HH:MM`   | chaque Lun, Jeu à 09:00       |
| Intervalle  | nombre + minutes/heures     | toutes les 2 h                |
| Cron        | expression cron (5 champs)  | `0 8 * * *`                   |

> Les expressions **cron** nécessitent le paquet `croniter`
> (`pip install croniter`). Quotidien / hebdo / intervalle fonctionnent sans.
> Jours de la semaine : **0 = Lundi … 6 = Dimanche**.

---

## Configuration — `config.yaml`

```yaml
scheduler:
  enabled: true                 # démarre la boucle avec le GUI / Relay
  check_interval: 30            # secondes entre deux vérifications (min 5)
  run_missed_on_startup: true   # rattraper les tâches manquées au démarrage
  catch_up_window_hours: 24     # fenêtre de rattrapage
  max_history: 200              # entrées de résultats conservées
  tasks_file: "data/scheduled_tasks.json"
  output_directory: "outputs/scheduled"
  notify_desktop: true          # toast OS (winotify/plyer) sinon toast in-app
  notify_mobile: true           # message WebSocket aux mobiles connectés
```

### Notifications desktop natives (optionnel)

Le fallback est un toast **in-app**. Pour de vraies notifications Windows hors
application, installez l'un de :

```bash
pip install winotify   # Windows (recommandé)
pip install plyer      # cross-plateforme
```

---

## Côté mobile (Relay)

Quand le Relay tourne, la fin d'une tâche planifiée est diffusée à tous les
mobiles connectés via un message WebSocket chiffré `scheduled_task_result`
(`{name, status, status_text, summary, finished_at}`). Le chemin du rapport local
n'est pas transmis.

---

## Format d'une tâche (`data/scheduled_tasks.json`)

```json
{
  "id": "sched_ab12cd34",
  "name": "Veille IA matinale",
  "enabled": true,
  "kind": "workflow",                 // "workflow" | "debate"
  "task": "Résume l'actualité IA du jour",
  "nodes": [{"id": "n1", "agent_type": "web", "name": "WebAgent",
             "color": "#10b981", "icon": "🔍"}],
  "connections": [],
  "debate": null,                     // {"agent_a","agent_b","rounds"} si débat
  "schedule": {"type": "daily", "at": "08:00"},
  "run_if_missed": true,
  "next_run": "2026-06-19T08:00:00",
  "last_run": null,
  "last_status": null,                // success | partial | interrupted | deferred | error
  "last_output_file": null
}
```

## Fichiers

| Fichier                                | Rôle                                            |
|----------------------------------------|-------------------------------------------------|
| `core/scheduler.py`                    | `SchedulerService` + `get_scheduler()`          |
| `interfaces/agents/scheduler_ui.py`    | UI de gestion (mixin de `AgentsInterface`)      |
| `data/scheduled_tasks.json`            | Définitions + historique des tâches             |
| `outputs/scheduled/*.md`               | Rapports de résultats                           |
| `tests/test_scheduler.py`              | Tests (exécuteur factice, sans LLM)             |
