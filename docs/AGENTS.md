# 🤖 Système d'Agents IA - Documentation

## Vue d'Ensemble

Le système d'agents IA permet d'utiliser des **agents spécialisés** basés sur Ollama pour résoudre des tâches complexes. Chaque agent a une **expertise spécifique** et peut collaborer avec d'autres agents. Vous pouvez créer vos propres workflows par **drag & drop** dans un **canvas visuel interactif style n8n** avec nœuds connectables, exécution parallèle DAG et monitoring de ressources en temps réel.

## 🎯 Concepts Clés

### Agent IA
Un agent est une instance d'Ollama avec :
- **Une expertise** (code, recherche, analyse, sécurité, etc.)
- **Un system prompt** spécialisé
- **Une mémoire contextuelle** de ses tâches
- **Des statistiques** de performance

### Orchestrateur
Coordonne les agents pour :
- Exécuter des tâches simples (1 agent)
- Orchestrer des workflows personnalisés (plusieurs agents en séquence via drag & drop)
- Exécuter des tâches parallèles
- Exécuter des DAG (graphes acycliques dirigés) via le canvas visuel
- Lancer un **Mode Débat** entre deux agents (proposant vs opposant) sur un sujet donné

### Canvas Visuel de Workflow (style n8n)
Le canvas permet de :
- **Créer des nœuds** visuels pour chaque agent (drag & drop depuis la grille)
- **Connecter des nœuds** par des courbes de Bézier (drag depuis un port de sortie vers un port d'entrée)
- **Zoomer/naviguer** (molette + clic milieu/droit pour le pan)
- **Organiser** sur une grille avec snap automatique et minimap
- **Exécuter** le workflow en respectant la topologie du graphe (séquentiel, parallèle, DAG)

## 🤖 Types d'Agents Disponibles (9 agents)

### 1. **CodeAgent** 🐍
**Expertise:** Génération et debug de code

**Utilise pour:**
- Générer du code propre et fonctionnel
- Corriger des bugs
- Optimiser du code existant
- Expliquer du code complexe

**Langages supportés:** Python, JavaScript, Java, C++, HTML/CSS, SQL

**Temperature:** 0.3 (précis et fiable)

```python
orchestrator.ask_agent("code", "Crée une fonction qui trie une liste")
```

### 2. **WebAgent** 🔍
**Expertise:** Recherche Internet & Fact-Checking

**Utilise pour:**
- Rechercher des informations en temps réel sur internet
- Fact-checking avec sources vérifiables
- Trouver des actualités et événements récents (focus 2026)
- Obtenir des données réelles depuis le web

**Temperature:** 0.5 (équilibré)

```python
orchestrator.ask_agent("web", "Cherche les groupes de la Coupe du monde 2026")
```

### 3. **AnalystAgent** 📊
**Expertise:** Analyse de données

**Utilise pour:**
- Analyser des datasets
- Extraire des insights
- Calculer des statistiques
- Analyser des documents

**Temperature:** 0.4 (analytique)

```python
orchestrator.ask_agent("analyst", "Analyse ce CSV et donne-moi les insights clés")
```

### 4. **CreativeAgent** ✨
**Expertise:** Contenu créatif

**Utilise pour:**
- Rédiger du contenu engageant
- Storytelling
- Marketing et communication
- Articles et blogs

**Temperature:** 0.8 (très créatif)

```python
orchestrator.ask_agent("creative", "Rédige un article sur l'IA")
```

### 5. **DebugAgent** 🐛
**Expertise:** Debug et correction d'erreurs

**Utilise pour:**
- Identifier des bugs
- Analyser des stack traces
- Proposer des corrections
- Suggérer des tests

**Temperature:** 0.2 (très précis)

```python
orchestrator.ask_agent("debug", "Pourquoi ce code plante : [code]")
```

### 6. **PlannerAgent** 📋
**Expertise:** Planification de projets

**Utilise pour:**
- Décomposer des tâches complexes
- Planifier un projet
- Identifier les dépendances
- Estimer les efforts

**Temperature:** 0.5 (méthodique)

```python
orchestrator.ask_agent("planner", "Planifie le développement d'une API REST")
```

### 7. **SecurityAgent** 🛡️
**Expertise:** Cybersécurité et audit de sécurité

**Utilise pour:**
- Auditer la sécurité du code
- Détecter les vulnérabilités (injections SQL, XSS, etc.)
- Proposer des mesures de protection
- Analyser les configurations de sécurité

**Temperature:** 0.2 (très précis)

```python
orchestrator.ask_agent("security", "Audite ce code pour les failles de sécurité")
```

### 8. **OptimizerAgent** ⚡
**Expertise:** Optimisation et performance

**Utilise pour:**
- Optimiser les performances du code
- Refactoring et amélioration de la qualité
- Profiling et analyse de complexité
- Réduction de la consommation mémoire

**Temperature:** 0.3 (précis)

```python
orchestrator.ask_agent("optimizer", "Optimise cette fonction pour de meilleures performances")
```

### 9. **DataScienceAgent** 🧬
**Expertise:** Data science et machine learning

**Utilise pour:**
- Analyse de données et statistiques avancées
- Modèles de machine learning
- Visualisation de données
- Analyse prédictive

**Temperature:** 0.4 (analytique)

```python
orchestrator.ask_agent("datascience", "Crée un modèle de classification pour ce dataset")
```

## 🎭 Mode Débat (deux agents s'affrontent)

### Vue d'Ensemble

Le **Mode Débat** confronte **deux agents** sur un sujet donné selon des perspectives opposées. L'un joue le rôle de **proposant** (défend la position), l'autre celui d'**opposant** (contre-argumente). Les agents alternent sur plusieurs tours et chacun répond explicitement aux arguments de l'autre.

Tous les agents sont éligibles : agents par défaut **et** agents personnalisés. Le streaming token-par-token est conservé, l'historique complet est retourné à la fin.

### Lancement depuis le code

```python
from core.agent_orchestrator import AgentOrchestrator

orchestrator = AgentOrchestrator()

result = orchestrator.execute_debate(
    agent_type_a="security",   # Proposant
    agent_type_b="optimizer",  # Opposant
    topic="Faut-il sacrifier la performance pour renforcer la sécurité ?",
    rounds=3,
    on_token=lambda tok: print(tok, end="", flush=True),
    on_round_start=lambda n, agent: print(f"\n--- Tour {n} ({agent}) ---"),
    on_should_stop=lambda: False,
)

for entry in result["debate_history"]:
    print(f"Tour {entry['round']} [{entry['role']}] {entry['agent']} : {entry['argument']}")
```

### Paramètres

| Paramètre | Type | Description |
|---|---|---|
| `agent_type_a` | `str` | Clé de l'agent proposant (`code`, `security`, agent personnalisé…) |
| `agent_type_b` | `str` | Clé de l'agent opposant — doit être différent de `agent_type_a` |
| `topic` | `str` | Sujet du débat injecté dans les prompts des deux agents |
| `rounds` | `int` | Nombre de tours (1 à 10 — chaque tour = 1 prise de parole par agent) |
| `on_token` | `Callable` | Callback streaming token par token |
| `on_round_start` | `Callable[[int, str], None]` | Notifié au début de chaque prise de parole |
| `on_should_stop` | `Callable[[], bool]` | Permet d'interrompre le débat entre deux tours |

### Format de la réponse

```python
{
    "success": True,
    "mode": "debate",
    "topic": "...",
    "agents": {"proposant": "security", "opposant": "optimizer"},
    "rounds_completed": 3,
    "debate_history": [
        {"round": 1, "agent": "security",  "role": "proposant", "argument": "..."},
        {"round": 1, "agent": "optimizer", "role": "opposant",  "argument": "..."},
        # ...
    ],
    "timestamp": "2026-04-20T..."
}
```

### Lancement depuis l'interface

Voir [AGENTS_GUI.md](AGENTS_GUI.md#-mode-débat) — le bouton **🎭 Mode Débat** (violet) ouvre une boîte de dialogue pour choisir les deux agents, le sujet et le nombre de tours, puis affiche chaque tour dans une section dédiée de la zone de résultats.

## 🎨 Création d'Agents Personnalisés

### Vue d'Ensemble

Vous pouvez créer vos **propres agents spécialisés** directement depuis l'interface graphique ! Le système utilise **Ollama** pour générer automatiquement un system prompt optimisé selon votre description.

### Comment Créer un Agent

1. **Cliquez sur le bouton "➕ Créer Agent"** (bleu, entre Exécuter et Clear Workflow)
2. **Remplissez le formulaire** :
   - **Nom** : Nom court de votre agent (ex: "TranslatorAgent")
   - **Rôle/Description** : Description détaillée de l'expertise et des capacités (ex: "Expert en traduction multilingue avec adaptation culturelle et nuances linguistiques")
3. **Cliquez sur "Créer"** : L'IA génère automatiquement :
   - Un **system prompt optimisé** pour guider le comportement de l'agent
   - Une **température idéale** (0.2-0.8) selon le type de tâche
   - Une **description courte** (3-4 mots) pour l'affichage sur la carte
4. **Votre agent apparaît** dans la grille après les 9 agents par défaut

### Génération Automatique par IA

Lorsque vous créez un agent, **Ollama analyse votre description** et génère :

- **System Prompt** : Instructions détaillées qui définissent le comportement de l'agent
- **Température** : Valeur entre 0.2 (très précis) et 0.8 (très créatif) selon la nature de la tâche
- **Description Courte** : Résumé de 3-4 mots pour un affichage compact

**Exemple de génération** :
```
Description : "Expert en cybersécurité spécialisé dans les audits de code et la détection de vulnérabilités"

→ System Prompt : "Tu es un expert en cybersécurité spécialisé dans..."
→ Température : 0.2 (précision maximale)
→ Description courte : "Audit & Sécurité"
```

### Gestion de vos Agents

#### Édition (📝)
- **Survolez la carte** de votre agent personnalisé
- **Cliquez sur l'icône 📝** (crayon) qui apparaît
- **Modifiez le nom et/ou la description**
- Si vous changez la **description**, le system prompt est **automatiquement régénéré** par Ollama
- Si vous changez seulement le **nom**, la modification est instantanée

#### Suppression (✖)
- **Cliquez sur l'icône ✖** (rouge, en haut à droite de la carte)
- **Confirmez la suppression** dans la boîte de dialogue
- L'agent est supprimé et la grille est mise à jour

### Persistance

Tous vos agents personnalisés sont **sauvegardés automatiquement** dans :
```
data/custom_agents.json
```

Structure :
```json
{
  "custom_TranslatorAgent_1707654321": {
    "name": "TranslatorAgent",
    "desc": "Expert en traduction multilingue avec adaptation culturelle",
    "short_desc": "Traduction multilingue",
    "color": "#3b82f6",
    "system_prompt": "Tu es un expert en traduction...",
    "temperature": 0.4
  }
}
```

### Intégration avec les Workflows

Les agents personnalisés fonctionnent **exactement comme les agents par défaut** :

- **Drag & Drop** : Glissez-déposez comme n'importe quel agent
- **Workflows mixtes** : Combinez agents par défaut et personnalisés
- **Exécution identique** : Même système d'orchestration
- **Mémoire** : Historique des tâches conservé

**Exemple de workflow** :
```
TranslatorAgent → CreativeAgent → CodeAgent
1. Traduire les specs en français
2. Rédiger la documentation
3. Générer le code
```

### Exemples d'Agents Personnalisés

#### 🌐 TranslatorAgent
```
Nom : TranslatorAgent
Rôle : Expert en traduction multilingue avec adaptation culturelle et nuances linguistiques

→ Température : 0.4
→ Description : Traduction multilingue
```

#### 📈 SEOAgent
```
Nom : SEOAgent
Rôle : Spécialiste en référencement naturel, optimisation de contenu web et stratégie SEO avancée

→ Température : 0.6
→ Description : SEO & référencement
```

#### 🔧 DevOpsAgent
```
Nom : DevOpsAgent
Rôle : Expert en CI/CD, containerisation Docker/Kubernetes, automatisation d'infrastructure et monitoring

→ Température : 0.3
→ Description : DevOps & CI/CD
```

#### 🎨 UIUXAgent
```
Nom : UIUXAgent
Rôle : Designer UI/UX spécialisé dans les interfaces modernes, accessibilité et expérience utilisateur

→ Température : 0.7
→ Description : Design UI/UX
```

#### ⚖️ LegalAgent
```
Nom : LegalAgent
Rôle : Conseiller juridique spécialisé en droit numérique, RGPD et propriété intellectuelle

→ Température : 0.2
→ Description : Conseil juridique
```

### Conseils pour Créer de Bons Agents

#### Description Détaillée
- **Soyez spécifique** : Plus la description est précise, meilleur sera le system prompt
- **Mentionnez l'expertise** : Domaines, technologies, méthodologies
- **Indiquez le style** : Formel, technique, créatif, etc.

#### Nommage
- **CamelCase recommandé** : TranslatorAgent, SEOAgent, DevOpsAgent
- **Suffixe "Agent"** : Pour cohérence avec les agents par défaut
- **Court et descriptif** : 2-3 mots maximum

#### Exemples de Bonnes Descriptions
✅ "Expert en traduction multilingue avec adaptation culturelle et nuances linguistiques"
✅ "Spécialiste en référencement naturel, optimisation de contenu et stratégie SEO"
✅ "Expert en CI/CD, containerisation, Kubernetes et automatisation d'infrastructure"

❌ "Traduction" (trop vague)
❌ "Un agent qui traduit des trucs" (pas assez professionnel)
❌ "Agent" (pas d'information)

### Limitations

- **Ollama requis** : La génération automatique nécessite Ollama avec qwen3.5
- **Pas de modification directe du system prompt** : Pour garantir la cohérence, le prompt est toujours généré par l'IA
- **Nom unique** : Chaque agent doit avoir un nom différent
- **Suppression définitive** : Pas de corbeille, suppression immédiate

## 🚀 Utilisation

### Installation

Aucune installation supplémentaire nécessaire ! Le système d'agents utilise votre installation Ollama existante.

### Utilisation Simple (1 agent)

```python
from core.agent_orchestrator import AgentOrchestrator

# Créer l'orchestrateur
orchestrator = AgentOrchestrator()

# Demander à un agent
response = orchestrator.ask_agent(
    agent_type="code",
    question="Crée une fonction qui calcule la factorielle"
)

print(response)
```

### Workflow Multi-Agents

Les agents collaborent en séquence, chaque agent bénéficiant du travail du précédent :

```python
# Workflow personnalisé
workflow = [
    {
        "agent": "planner",
        "task": "Planifie le développement d'un bot Discord",
        "pass_result": True  # Passe le résultat à l'agent suivant
    },
    {
        "agent": "code",
        "task": "Génère le code selon le plan",
        "pass_result": True
    },
    {
        "agent": "debug",
        "task": "Vérifie et optimise le code",
        "pass_result": False
    }
]

result = orchestrator.execute_multi_agent_task(
    "Développement d'un bot Discord",
    workflow
)
```

### Workflows Personnalisés (Drag & Drop)

Créez vos propres workflows directement depuis l'interface graphique en glissant-déposant les agents. En code, vous pouvez aussi définir un workflow personnalisé :

```python
# Exemple : workflow Security → Code → Debug
workflow = [
    {"agent": "security", "task": "Audite ce code pour les vulnérabilités", "pass_result": True},
    {"agent": "code", "task": "Corrige les failles identifiées", "pass_result": True},
    {"agent": "debug", "task": "Vérifie que les corrections sont valides", "pass_result": False}
]

result = orchestrator.execute_multi_agent_task("Audit et correction", workflow)
```

### Agents en Parallèle

Plusieurs agents travaillent simultanément sur différents aspects :

```python
tasks = [
    {"agent": "web", "task": "Cherche les frameworks Python web"},
    {"agent": "analyst", "task": "Compare FastAPI vs Flask vs Django"},
    {"agent": "code", "task": "Exemple de code pour chaque framework"}
]

result = orchestrator.execute_parallel_tasks(tasks)
```

## 📊 Statistiques et Suivi

### Statistiques d'un Agent

```python
stats = orchestrator.get_agent_stats("code")
print(f"Tâches complétées: {stats['tasks_completed']}")
print(f"Taux de succès: {stats['success_rate']:.1%}")
```

### Statistiques Globales

```python
stats = orchestrator.get_orchestrator_stats()
print(f"Agents actifs: {stats['active_agents']}")
print(f"Tâches totales: {stats['total_tasks']}")
```

### Export de Session

```python
# Exporter toutes les données vers JSON
orchestrator.export_session("outputs/ma_session_agents.json")
```

## 🎨 Exemples Concrets

### Exemple 1: Développement d'une Feature Complète

```python
orchestrator = AgentOrchestrator()

# Étape 1: Planification
plan = orchestrator.ask_agent(
    "planner",
    "Planifie le développement d'un système de connexion utilisateur"
)

# Étape 2: Génération du code
code = orchestrator.ask_agent(
    "code",
    f"Génère le code pour: {plan}",
    context={"plan": plan}
)

# Étape 3: Debug
verified_code = orchestrator.ask_agent(
    "debug",
    f"Vérifie ce code: {code}"
)
```

### Exemple 2: Recherche et Article

```python
# Recherche
web_search = orchestrator.ask_agent(
    "web",
    "Cherche les meilleures pratiques en cybersécurité 2026"
)

# Analyse
analysis = orchestrator.ask_agent(
    "analyst",
    f"Analyse ces informations et identifie les 5 points clés: {web_search}"
)

# Rédaction
article = orchestrator.ask_agent(
    "creative",
    f"Rédige un article de blog basé sur: {analysis}"
)
```

### Exemple 3: Debug Assisté

```python
error_code = """
def calculate(numbers):
    return sum(numbers) / len(numbers)

result = calculate([])  # Erreur!
"""

# Debug identifie le problème
diagnosis = orchestrator.ask_agent(
    "debug",
    f"Analyse cette erreur: {error_code}"
)

# Code génère la correction
fixed_code = orchestrator.ask_agent(
    "code",
    f"Corrige ce code selon: {diagnosis}"
)
```

## 🖼️ Canvas Visuel de Workflow

### Vue d'Ensemble

Le canvas visuel transforme la création de workflows en une expérience interactive de type n8n. Au lieu de simplement empiler des agents dans un pipeline linéaire, vous pouvez créer des graphes complexes avec des branches parallèles et des dépendances.

### Interactions

| Action | Geste |
|---|---|
| **Ajouter un nœud** | Drag & drop un agent depuis la grille sur le canvas |
| **Connecter deux nœuds** | Drag du port de sortie (●, à droite) vers le port d'entrée (●, à gauche) |
| **Déplacer un nœud** | Clic gauche + drag |
| **Sélectionner** | Clic sur un nœud, Shift+clic pour multi-sélection, rectangle de sélection |
| **Supprimer un nœud** | Touche Suppr ou clic sur ✕ |
| **Supprimer une connexion** | Clic droit sur une connexion |
| **Zoomer** | Molette de la souris |
| **Naviguer (pan)** | Clic milieu ou clic droit + drag |
| **Grille** | Bouton ⊞ Grid pour afficher/masquer |
| **Reset vue** | Bouton ⊙ Reset |

### Topologie d'Exécution

Le canvas analyse automatiquement le graphe et détermine le mode d'exécution optimal :

- **Séquentiel** : Nœuds connectés en chaîne (A → B → C)
- **Parallèle** : Nœuds au même niveau sans dépendances mutuelles (exécutés en threads simultanés)
- **DAG** : Graphe acyclique dirigé avec tri topologique — exécution étape par étape : les nœuds d'une même étape sans dépendances partagées sont exécutés en parallèle

### Statuts des Nœuds

Pendant l'exécution, chaque nœud affiche son statut en temps réel :

| Statut | Couleur | Signification |
|---|---|---|
| ⚪ **Idle** | Gris | En attente |
| 🟡 **Running** | Jaune | En cours d'exécution |
| 🟢 **Done** | Vert | Terminé avec succès |
| 🔴 **Error** | Rouge | Erreur lors de l'exécution |

### Passage de contexte

Quand deux nœuds sont connectés (A → B), le résultat de A est automatiquement injecté dans le contexte de B. Cela permet aux agents de collaborer :

```
PlannerAgent → CodeAgent → DebugAgent
     ↓ plan        ↓ code        ↓ rapport
```

Chaque agent reçoit le résultat du précédent et enrichit la réponse.

## 📊 Monitoring de Ressources

### Métriques Collectées

Le panneau de statistiques affiche en temps réel la consommation des processus Ollama :

| Métrique | Source | Description |
|---|---|---|
| **CPU %** | psutil (processus Ollama) | Utilisation CPU agrégée de tous les processus Ollama |
| **RAM** | psutil (processus Ollama) | Mémoire RSS totale consommée par Ollama |
| **GPU %** | pynvml / GPUtil | Utilisation du GPU (NVIDIA) |
| **VRAM** | pynvml / GPUtil | Mémoire GPU utilisée |
| **Inférence** | Chronomètre interne | Temps de la dernière inférence en ms |
| **Tokens/s** | Calcul interne | Vitesse de génération |

### Affichage

Chaque métrique est accompagnée de :
- **Barre de progression colorée** : vert (0-60%) → jaune (60-85%) → rouge (85-100%)
- **Valeur numérique** en temps réel
- **Sparkline** : mini-graphique des 60 dernières mesures (~3 minutes à 3s d'intervalle)

### Dépendances Optionnelles

Le monitoring CPU/RAM fonctionne avec `psutil` (inclus). Pour le monitoring GPU :
```bash
pip install pynvml GPUtil
```
Sans ces packages, les lignes GPU/VRAM affichent "N/A".

## 🎯 Cas d'Usage Avancés

### 1. Pipeline de Documentation Automatique

```python
workflow = [
    {"agent": "code", "task": "Génère une classe Python ComplexCalculator", "pass_result": True},
    {"agent": "analyst", "task": "Analyse la complexité du code", "pass_result": True},
    {"agent": "creative", "task": "Rédige la documentation utilisateur", "pass_result": False}
]
```

### 2. Analyse de Projet Multi-Perspectives

```python
project_desc = "Une marketplace en ligne pour artisans locaux"

tasks = [
    {"agent": "planner", "task": f"Architecture technique pour: {project_desc}"},
    {"agent": "analyst", "task": f"Analyse de marché et besoins pour: {project_desc}"},
    {"agent": "creative", "task": f"Stratégie marketing pour: {project_desc}"}
]

results = orchestrator.execute_parallel_tasks(tasks)
```

### 3. Refactoring Assisté

```python
old_code = "[votre ancien code]"

workflow = [
    {"agent": "analyst", "task": f"Analyse ce code et identifie les améliorations: {old_code}", "pass_result": True},
    {"agent": "code", "task": "Refactorise le code selon les recommandations", "pass_result": True},
    {"agent": "debug", "task": "Vérifie la qualité du refactoring", "pass_result": False}
]
```

## 🔧 Configuration Avancée

### Changer le Modèle Ollama

```python
# Utiliser un modèle plus puissant
orchestrator = AgentOrchestrator(model="llama3.1:70b")

# Ou créer un agent avec un modèle spécifique
from models.ai_agents import create_agent
agent = create_agent("code", model="codellama")
```

### Créer un Agent Personnalisé

```python
from models.ai_agents import AIAgent

custom_agent = AIAgent(
    name="SecurityAgent",
    expertise="Sécurité informatique",
    system_prompt="""Tu es un expert en cybersécurité.
    Analyse les vulnérabilités et propose des solutions.""",
    model="qwen3.5:4b",
    temperature=0.3
)

result = custom_agent.execute_task(
    "Analyse la sécurité de cette fonction: [code]"
)
```

## 📝 Bonnes Pratiques

### 1. Choix de l'Agent
- **Code simple** → CodeAgent seul
- **Projet complexe** → Workflow Planner → Code → Debug (via drag & drop)
- **Recherche Internet** → WebAgent → AnalystAgent
- **Contenu avec recherche** → WebAgent → CreativeAgent
- **Sécurité** → SecurityAgent → CodeAgent
- **Performance** → OptimizerAgent
- **Data science** → DataScienceAgent → AnalystAgent

### 2. Gestion du Contexte
- Utilisez `pass_result=True` pour que les agents collaborent
- Ajoutez du contexte spécifique avec le paramètre `context`
- Limitez la taille du contexte passé (~500 tokens max)

### 3. Performance
- Un agent consomme des ressources Ollama (CPU/RAM)
- Ne créez pas trop d'agents simultanément
- Réutilisez les agents existants (`get_or_create_agent`)

### 4. Température
- **0.0-0.3** : Précision (code, debug, analyse)
- **0.4-0.6** : Équilibré (recherche, planning)
- **0.7-1.0** : Créativité (rédaction, brainstorming)

## 🚨 Dépannage

### Ollama non disponible
```
❌ Ollama non disponible
```
**Solution:** Lancez Ollama avec `ollama serve`

### Agent échoue
```python
if not result["success"]:
    print(f"Erreur: {result['error']}")
    print(f"Agents disponibles: {orchestrator.list_available_agents()}")
```

### Réinitialiser un Agent
```python
# Un agent garde sa mémoire, parfois il faut la vider
orchestrator.reset_agent("code")

# Ou tous les agents
orchestrator.reset_all_agents()
```

## 📚 Ressources

- **Code source agents:** `models/ai_agents.py`
- **Orchestrateur:** `core/agent_orchestrator.py`
- **Interface agents:** `interfaces/agents_interface.py` (façade) + package `interfaces/agents/` (mixins)
- **Canvas visuel:** `interfaces/workflow_canvas.py`
- **Monitoring ressources:** `interfaces/resource_monitor.py`
- **Documentation Ollama:** https://ollama.com/

---

**Astuce:** Commencez par des tâches simples avec un seul agent, puis explorez les workflows multi-agents une fois à l'aise ! 🚀
