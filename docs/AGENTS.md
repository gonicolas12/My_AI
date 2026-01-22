# 🤖 Système d'Agents IA - Documentation

## Vue d'Ensemble

Le système d'agents IA permet d'utiliser des **agents spécialisés** basés sur Ollama pour résoudre des tâches complexes. Chaque agent a une **expertise spécifique** et peut collaborer avec d'autres agents.

## 🎯 Concepts Clés

### Agent IA
Un agent est une instance d'Ollama avec :
- **Une expertise** (code, recherche, analyse, etc.)
- **Un system prompt** spécialisé
- **Une mémoire contextuelle** de ses tâches
- **Des statistiques** de performance

### Orchestrateur
Coordonne les agents pour :
- Exécuter des tâches simples (1 agent)
- Orchestrer des workflows complexes (plusieurs agents en séquence)
- Exécuter des tâches parallèles

## 🤖 Types d'Agents Disponibles

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

### 2. **ResearchAgent** 📚
**Expertise:** Recherche et documentation

**Utilise pour:**
- Rechercher des informations techniques
- Synthétiser plusieurs sources
- Documenter des sujets
- Veille technologique

**Temperature:** 0.5 (équilibré)

```python
orchestrator.ask_agent("research", "Quelles sont les nouveautés Python 3.13 ?")
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

### Workflows Pré-Configurés

Des templates prêts à l'emploi :

```python
from core.agent_orchestrator import WorkflowTemplates

# Développement logiciel complet (planner → code → debug)
task, workflow = WorkflowTemplates.code_development(
    "Une API REST pour gérer des utilisateurs"
)
result = orchestrator.execute_multi_agent_task(task, workflow)

# Recherche et documentation (research → analyst → creative)
task, workflow = WorkflowTemplates.research_and_document(
    "L'intelligence artificielle dans la santé"
)
result = orchestrator.execute_multi_agent_task(task, workflow)

# Debug et correction (debug → code)
task, workflow = WorkflowTemplates.debug_and_fix(
    code="[votre code]",
    error="IndexError: list index out of range"
)
result = orchestrator.execute_multi_agent_task(task, workflow)
```

### Agents en Parallèle

Plusieurs agents travaillent simultanément sur différents aspects :

```python
tasks = [
    {"agent": "research", "task": "Recherche les frameworks Python web"},
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
research = orchestrator.ask_agent(
    "research",
    "Recherche les meilleures pratiques en cybersécurité 2026"
)

# Analyse
analysis = orchestrator.ask_agent(
    "analyst",
    f"Analyse ces informations et identifie les 5 points clés: {research}"
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
    model="llama3.2",
    temperature=0.3
)

result = custom_agent.execute_task(
    "Analyse la sécurité de cette fonction: [code]"
)
```

## 📝 Bonnes Pratiques

### 1. Choix de l'Agent
- **Code simple** → CodeAgent seul
- **Projet complexe** → Workflow Planner → Code → Debug
- **Recherche** → ResearchAgent → AnalystAgent
- **Contenu** → ResearchAgent → CreativeAgent

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

- **Exemples complets:** `examples/agent_examples.py`
- **Code source:** `models/ai_agents.py`
- **Orchestrateur:** `core/agent_orchestrator.py`
- **Documentation Ollama:** https://ollama.com/

## 🎓 Tutoriel Interactif

Lancez les exemples pour apprendre :

```bash
python examples/agent_examples.py
```

Chaque exemple est commenté et montre un cas d'usage différent.

---

**Astuce:** Commencez par des tâches simples avec un seul agent, puis explorez les workflows multi-agents une fois à l'aise ! 🚀
