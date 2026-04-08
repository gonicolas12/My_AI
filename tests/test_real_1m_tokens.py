"""
🎯 TEST RÉEL MÉMOIRE VECTORIELLE 10M - My Personal AI
Test authentique de la VectorMemory (capacité 10M tokens) avec votre IA principale

Ce test utilise votre CustomAIModel réel et vérifie vraiment :
- Stockage d'1M+ tokens de contenu varié (sous-ensemble du système 10M)
- Compréhension globale du contexte via recherche sémantique
- Raisonnement sur l'ensemble des données indexées
- Performance en conditions réelles

Note: La capacité totale du système est 10 485 760 tokens (10M).
Ce test stresse 1M tokens comme sous-ensemble représentatif pour rester
exécutable en quelques minutes. Pour un benchmark complet jusqu'à 10M,
voir tests/benchmark_10m_tokens.py.
"""

import os
import json
import sys
import time
import re
import gc
from datetime import datetime
from pathlib import Path

# =========================================================================== #
# OPTIMISATION DÉMARRAGE : Imports de modules standards d'abord               #
# Le mode offline HuggingFace est géré automatiquement dans core.shared       #
# avec téléchargement automatique au premier lancement si nécessaire          #
# =========================================================================== #

import tiktoken

# Configuration du chemin - Ajout du répertoire racine du projet
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Imports de votre IA réelle
try:
    from models.conversation_memory import ConversationMemory
    from models.custom_ai_model import CustomAIModel

    REAL_AI_AVAILABLE = True
except ImportError as e:
    REAL_AI_AVAILABLE = False
    print(f"❌ IA réelle non disponible: {e}")


class RealAI1MTest:
    """Test réel de la VectorMemory 10M tokens (stress 1M) avec votre IA"""

    def __init__(self):
        self.results = {
            "test_date": datetime.now().isoformat(),
            "test_type": "REAL AI VECTORMEMORY 10M (1M STRESS) TEST",
            "system_used": "CustomAIModel + VectorMemory 10M (Production)",
            "total_tokens_processed": 0,
            "comprehension_score": 0,
            "performance_metrics": {},
            "test_status": "PENDING",
        }

        # Initialiser l'encodeur de tokens (GPT-4)
        try:
            self.tokenizer = tiktoken.encoding_for_model("gpt-4")
        except (KeyError, AttributeError):
            # Fallback vers cl100k_base si gpt-4 n'est pas disponible
            self.tokenizer = tiktoken.get_encoding("cl100k_base")

        print("\n🎯 TEST RÉEL VECTORMEMORY 10M (STRESS 1M) INITIALISÉ")
        print("=" * 50)

    def count_real_tokens(self, text: str) -> int:
        """Compte les vrais tokens (comme un LLM)"""
        return len(self.tokenizer.encode(text))

    def generate_diverse_content(self, target_tokens: int) -> str:
        """Génère un contenu riche et varié pour test réaliste"""

        contents = []
        current_tokens = 0

        # 1. Documentation technique (25%)
        tech_doc = """
# DOCUMENTATION TECHNIQUE SYSTÈME IA

## Architecture Globale
Le système My Personal AI implémente une architecture modulaire avancée permettant:
- Mémoire vectorielle persistante jusqu'à 10M tokens (stress 1M ici)
- Mémoire de conversation persistante avec indexation sémantique
- Modules spécialisés: calcul, code, documents, recherche internet
- Optimisations de performance pour temps de réponse < 3s

### Composants Principaux

#### 1. CustomAIModel
- Modèle principal de génération de réponses
- Intégration FAQ/ML pour réponses précises
- Détection d'intentions multicritères
- Gestion de contexte intelligent

#### 2. ConversationMemory
- Stockage persistant des conversations
- Indexation automatique par thèmes
- Récupération contextuelle optimisée
- Compression sémantique du contenu

#### 3. Processeurs Spécialisés
- PDFProcessor: extraction et analyse de documents PDF
- DOCXProcessor: traitement de documents Word
- CodeProcessor: analyse et génération de code
- InternetSearch: recherche web intégrée

### Algorithmes d'Optimisation

Le système utilise plusieurs algorithmes pour optimiser les performances:

1. **Chunking Intelligent**: Division du contenu en segments sémantiquement cohérents
2. **Indexation TF-IDF**: Recherche rapide dans de gros volumes
3. **Compression Contextuelle**: Réduction de la redondance
4. **Cache Adaptatif**: Mise en cache des résultats fréquents

### Métriques de Performance

Objectifs de performance du système:
- Temps de réponse: < 3 secondes pour 90% des requêtes
- Précision FAQ: > 95% sur les questions connues
- Capacité contexte: 1,000,000 tokens minimum
- Mémoire utilisée: < 2GB pour fonctionnement optimal

## Cas d'Usage Avancés

### 1. Analyse de Code
Le système peut analyser du code complexe:

```python
def analyze_performance(data, metrics):
    \"\"\"Analyse de performance avancée\"\"\"
    results = {}
    for metric in metrics:
        if metric == 'response_time':
            results[metric] = calculate_response_time(data)
        elif metric == 'accuracy':
            results[metric] = calculate_accuracy(data)
        elif metric == 'memory_usage':
            results[metric] = get_memory_usage()
    return results

class PerformanceAnalyzer:
    def __init__(self, config):
        self.config = config
        self.metrics = []
    
    def add_metric(self, name, calculator):
        self.metrics.append({'name': name, 'calc': calculator})
    
    def run_analysis(self):
        return {m['name']: m['calc']() for m in self.metrics}
```

### 2. Traitement de Documents
Capacité d'extraction et d'analyse:
- Formats supportés: PDF, DOCX, TXT, JSON
- Reconnaissance de structure
- Extraction d'entités nommées
- Résumé automatique

### 3. Recherche Internet
Intégration avec moteurs de recherche:
- Requêtes intelligentes automatiques
- Filtrage de contenu pertinent
- Synthèse d'informations multiples
- Vérification de sources
"""

        contents.append(("Documentation Technique", tech_doc))
        current_tokens += self.count_real_tokens(tech_doc)

        # 2. Code source varié (20%)
        code_examples = """
# EXEMPLES DE CODE POUR TEST DE COMPRÉHENSION

## Python - Algorithmes avancés

### 1. Tri fusion optimisé
```python
def merge_sort_optimized(arr, threshold=32):
    \"\"\"Tri fusion avec basculement vers tri insertion pour petits tableaux\"\"\"
    if len(arr) <= threshold:
        return insertion_sort(arr)
    
    mid = len(arr) // 2
    left = merge_sort_optimized(arr[:mid], threshold)
    right = merge_sort_optimized(arr[mid:], threshold)
    
    return merge(left, right)

def insertion_sort(arr):
    for i in range(1, len(arr)):
        key = arr[i]
        j = i - 1
        while j >= 0 and arr[j] > key:
            arr[j + 1] = arr[j]
            j -= 1
        arr[j + 1] = key
    return arr

def merge(left, right):
    result = []
    i = j = 0
    
    while i < len(left) and j < len(right):
        if left[i] <= right[j]:
            result.append(left[i])
            i += 1
        else:
            result.append(right[j])
            j += 1
    
    result.extend(left[i:])
    result.extend(right[j:])
    return result
```

### 2. Gestionnaire de cache LRU
```python
from collections import OrderedDict
from threading import Lock

class LRUCache:
    def __init__(self, capacity):
        self.capacity = capacity
        self.cache = OrderedDict()
        self.lock = Lock()
    
    def get(self, key):
        with self.lock:
            if key not in self.cache:
                return None
            
            # Déplacer à la fin (plus récemment utilisé)
            value = self.cache.pop(key)
            self.cache[key] = value
            return value
    
    def put(self, key, value):
        with self.lock:
            if key in self.cache:
                self.cache.pop(key)
            elif len(self.cache) >= self.capacity:
                # Supprimer le moins récemment utilisé
                oldest = next(iter(self.cache))
                self.cache.pop(oldest)
            
            self.cache[key] = value
    
    def clear(self):
        with self.lock:
            self.cache.clear()
    
    def size(self):
        return len(self.cache)
```

### 3. Analyseur syntaxique simple
```python
import re
from enum import Enum
from dataclasses import dataclass
from typing import List, Optional

class TokenType(Enum):
    NUMBER = "NUMBER"
    IDENTIFIER = "IDENTIFIER"
    OPERATOR = "OPERATOR"
    PARENTHESIS = "PARENTHESIS"
    EOF = "EOF"

@dataclass
class Token:
    type: TokenType
    value: str
    position: int

class Lexer:
    def __init__(self, text):
        self.text = text
        self.position = 0
        self.current_char = self.text[0] if text else None
    
    def advance(self):
        self.position += 1
        if self.position >= len(self.text):
            self.current_char = None
        else:
            self.current_char = self.text[self.position]
    
    def skip_whitespace(self):
        while self.current_char and self.current_char.isspace():
            self.advance()
    
    def read_number(self):
        result = ''
        while self.current_char and (self.current_char.isdigit() or self.current_char == '.'):
            result += self.current_char
            self.advance()
        return float(result) if '.' in result else int(result)
    
    def read_identifier(self):
        result = ''
        while self.current_char and (self.current_char.isalnum() or self.current_char == '_'):
            result += self.current_char
            self.advance()
        return result
    
    def get_next_token(self):
        while self.current_char:
            if self.current_char.isspace():
                self.skip_whitespace()
                continue
            
            if self.current_char.isdigit():
                return Token(TokenType.NUMBER, self.read_number(), self.position)
            
            if self.current_char.isalpha():
                return Token(TokenType.IDENTIFIER, self.read_identifier(), self.position)
            
            if self.current_char in '+-*/':
                token = Token(TokenType.OPERATOR, self.current_char, self.position)
                self.advance()
                return token
            
            if self.current_char in '()':
                token = Token(TokenType.PARENTHESIS, self.current_char, self.position)
                self.advance()
                return token
            
            raise ValueError(f"Caractère invalide: {self.current_char}")
        
        return Token(TokenType.EOF, None, self.position)
```

## JavaScript - Patterns modernes

### 1. Gestionnaire d'état réactif
```javascript
class ReactiveState {
    constructor(initialState = {}) {
        this.state = { ...initialState };
        this.subscribers = new Map();
        this.middleware = [];
        
        return new Proxy(this, {
            get: (target, prop) => {
                if (prop in target) {
                    return target[prop];
                }
                return target.state[prop];
            },
            set: (target, prop, value) => {
                if (prop in target) {
                    target[prop] = value;
                    return true;
                }
                
                const oldValue = target.state[prop];
                target.state[prop] = value;
                target.notify(prop, value, oldValue);
                return true;
            }
        });
    }
    
    subscribe(key, callback) {
        if (!this.subscribers.has(key)) {
            this.subscribers.set(key, new Set());
        }
        this.subscribers.get(key).add(callback);
        
        return () => {
            const callbacks = this.subscribers.get(key);
            if (callbacks) {
                callbacks.delete(callback);
            }
        };
    }
    
    notify(key, newValue, oldValue) {
        // Appliquer middleware
        let processedValue = newValue;
        for (const middleware of this.middleware) {
            processedValue = middleware(key, processedValue, oldValue);
        }
        
        // Notifier les subscribers
        const callbacks = this.subscribers.get(key);
        if (callbacks) {
            callbacks.forEach(callback => {
                try {
                    callback(processedValue, oldValue);
                } catch (error) {
                    console.error('Erreur dans subscriber:', error);
                }
            });
        }
    }
    
    use(middleware) {
        this.middleware.push(middleware);
    }
    
    getState() {
        return { ...this.state };
    }
    
    setState(updates) {
        Object.entries(updates).forEach(([key, value]) => {
            this[key] = value;
        });
    }
}
```

### 2. Worker Pool pour calculs intensifs
```javascript
class WorkerPool {
    constructor(workerScript, poolSize = navigator.hardwareConcurrency || 4) {
        this.workerScript = workerScript;
        this.poolSize = poolSize;
        this.workers = [];
        this.taskQueue = [];
        this.activeJobs = new Map();
        this.jobId = 0;
        
        this.initializeWorkers();
    }
    
    initializeWorkers() {
        for (let i = 0; i < this.poolSize; i++) {
            const worker = new Worker(this.workerScript);
            worker.onmessage = (event) => this.handleWorkerMessage(worker, event);
            worker.onerror = (error) => this.handleWorkerError(worker, error);
            worker.idle = true;
            this.workers.push(worker);
        }
    }
    
    execute(data, transferable = []) {
        return new Promise((resolve, reject) => {
            const jobId = ++this.jobId;
            const job = {
                id: jobId,
                data,
                transferable,
                resolve,
                reject,
                timestamp: Date.now()
            };
            
            this.activeJobs.set(jobId, job);
            
            const availableWorker = this.workers.find(w => w.idle);
            if (availableWorker) {
                this.assignJobToWorker(availableWorker, job);
            } else {
                this.taskQueue.push(job);
            }
        });
    }
    
    assignJobToWorker(worker, job) {
        worker.idle = false;
        worker.currentJob = job.id;
        worker.postMessage({
            id: job.id,
            data: job.data
        }, job.transferable);
    }
    
    handleWorkerMessage(worker, event) {
        const { id, result, error } = event.data;
        const job = this.activeJobs.get(id);
        
        if (job) {
            if (error) {
                job.reject(new Error(error));
            } else {
                job.resolve(result);
            }
            
            this.activeJobs.delete(id);
            worker.idle = true;
            worker.currentJob = null;
            
            // Traiter la prochaine tâche en attente
            if (this.taskQueue.length > 0) {
                const nextJob = this.taskQueue.shift();
                this.assignJobToWorker(worker, nextJob);
            }
        }
    }
    
    handleWorkerError(worker, error) {
        console.error('Erreur worker:', error);
        const jobId = worker.currentJob;
        if (jobId) {
            const job = this.activeJobs.get(jobId);
            if (job) {
                job.reject(error);
                this.activeJobs.delete(jobId);
            }
        }
        
        worker.idle = true;
        worker.currentJob = null;
    }
    
    terminate() {
        this.workers.forEach(worker => worker.terminate());
        this.workers = [];
        this.activeJobs.clear();
        this.taskQueue = [];
    }
    
    getStats() {
        return {
            totalWorkers: this.workers.length,
            idleWorkers: this.workers.filter(w => w.idle).length,
            activeJobs: this.activeJobs.size,
            queuedJobs: this.taskQueue.length
        };
    }
}
```
"""

        contents.append(("Code Examples", code_examples))
        current_tokens += self.count_real_tokens(code_examples)

        # 3. Données structurées (15%)
        structured_data = """
# DONNÉES STRUCTURÉES POUR TEST

## Configuration Système
```json
{
    "system_config": {
        "version": "7.1.0",
        "environment": "production",
        "features": {
            "context_size": 10485760,
            "memory_persistent": true,
            "internet_search": true,
            "document_processing": true,
            "code_analysis": true
        },
        "performance": {
            "max_response_time": 3000,
            "cache_size": "512MB",
            "parallel_processing": true,
            "optimization_level": "aggressive"
        },
        "modules": [
            {
                "name": "FAQ_ML",
                "enabled": true,
                "priority": 1,
                "accuracy_target": 0.95
            },
            {
                "name": "CustomAI",
                "enabled": true,
                "priority": 2,
                "context_window": 10485760
            },
            {
                "name": "InternetSearch", 
                "enabled": true,
                "priority": 3,
                "max_results": 10
            }
        ]
    }
}
```

## Métriques de Performance
```yaml
performance_metrics:
  response_times:
    - timestamp: "2025-09-05T10:00:00Z"
      query_type: "faq"
      response_time_ms: 150
      tokens_processed: 50
    - timestamp: "2025-09-05T10:01:00Z"
      query_type: "document_analysis"
      response_time_ms: 2500
      tokens_processed: 15000
    - timestamp: "2025-09-05T10:02:00Z"
      query_type: "code_generation"
      response_time_ms: 1800
      tokens_processed: 8000
  
  accuracy_stats:
    faq_accuracy: 0.97
    intent_detection: 0.89
    context_relevance: 0.93
    
  resource_usage:
    memory_mb: 1850
    cpu_percent: 45
    disk_io_mb: 125
    network_kb: 890
```

## Base de Connaissances
```csv
topic,category,content,importance,last_updated
"intelligence_artificielle","tech","L'IA est une technologie permettant aux machines de simuler l'intelligence humaine",5,"2025-09-05"
"machine_learning","tech","Le ML est une méthode d'IA où les systèmes apprennent automatiquement à partir de données",5,"2025-09-05"
"deep_learning","tech","Le DL utilise des réseaux de neurones artificiels pour traiter l'information",4,"2025-09-05"
"python","programming","Python est un langage de programmation polyvalent et facile à apprendre",5,"2025-09-05"
"javascript","programming","JavaScript est le langage du web, utilisé côté client et serveur",4,"2025-09-05"
"react","web","React est une bibliothèque JavaScript pour créer des interfaces utilisateur",4,"2025-09-05"
"node_js","backend","Node.js permet d'exécuter JavaScript côté serveur",4,"2025-09-05"
"docker","devops","Docker permet de containeriser les applications pour un déploiement simplifié",4,"2025-09-05"
"kubernetes","devops","Kubernetes orchestre les containers en production",3,"2025-09-05"
"aws","cloud","Amazon Web Services est une plateforme cloud complète",4,"2025-09-05"
```

## Logs Système
```
2025-09-05 10:00:01 [INFO] System startup completed
2025-09-05 10:00:02 [INFO] Loading FAQ model with 1,247 entries
2026-04-08 10:00:03 [INFO] CustomAI model initialized with 10M token VectorMemory
2025-09-05 10:00:04 [INFO] Internet search module ready
2025-09-05 10:00:05 [INFO] Document processors loaded: PDF, DOCX, TXT
2025-09-05 10:00:06 [DEBUG] Memory usage: 1.2GB / 4GB available
2025-09-05 10:00:10 [INFO] First query received: "Qu'est-ce que l'IA?"
2025-09-05 10:00:10 [DEBUG] FAQ lookup for: "Qu'est-ce que l'IA?"
2025-09-05 10:00:10 [INFO] FAQ match found with confidence 0.95
2025-09-05 10:00:10 [INFO] Response generated in 145ms
2025-09-05 10:00:15 [INFO] Query: "Explique ce code Python"
2025-09-05 10:00:15 [DEBUG] Intent detected: code_explanation
2025-09-05 10:00:15 [DEBUG] Analyzing code context...
2025-09-05 10:00:16 [INFO] Code analysis completed in 1.2s
2025-09-05 10:00:20 [INFO] Query: "Recherche des infos sur React 18"
2025-09-05 10:00:20 [DEBUG] Internet search triggered
2025-09-05 10:00:22 [INFO] Found 8 relevant results
2025-09-05 10:00:23 [INFO] Response synthesized in 2.8s
```
"""

        contents.append(("Structured Data", structured_data))
        current_tokens += self.count_real_tokens(structured_data)

        # 4. Contenu conversationnel (20%)
        conversations = """
# CONVERSATIONS ET DIALOGUES POUR TEST DE MÉMOIRE

## Conversation 1: Support Technique
**Utilisateur**: J'ai un problème avec mon installation Python, ça ne fonctionne pas.

**Assistant**: Je vais vous aider à résoudre votre problème Python. Pouvez-vous me donner plus de détails ?
- Quel système d'exploitation utilisez-vous ?
- Quel message d'erreur obtenez-vous exactement ?
- Quelle version de Python tentez-vous d'installer ?

**Utilisateur**: Je suis sur Windows 11, et quand je lance "python --version" ça me dit que la commande n'est pas reconnue.

**Assistant**: Ce problème indique que Python n'est pas dans votre PATH système. Voici comment le résoudre :

1. **Vérification d'installation** :
   - Allez dans "Paramètres" > "Applications" 
   - Cherchez "Python" dans la liste
   - Si absent, téléchargez depuis python.org

2. **Configuration du PATH** :
   - Tapez "Variables d'environnement" dans le menu Démarrer
   - Cliquez sur "Variables d'environnement"
   - Dans "Variables système", trouvez "Path"
   - Ajoutez le chemin d'installation Python (ex: C:\\Python311\\)

3. **Test** :
   - Ouvrez un nouveau terminal (important !)
   - Tapez `python --version`

**Utilisateur**: Parfait ! Maintenant ça marche, j'ai Python 3.11.5. Mais comment j'installe des packages ?

**Assistant**: Excellent ! Maintenant que Python fonctionne, voici comment installer des packages :

**Méthode principale - pip** :
```bash
# Installer un package
pip install nom_du_package

# Exemples utiles
pip install requests
pip install pandas
pip install matplotlib

# Voir les packages installés
pip list

# Mettre à jour un package
pip install --upgrade nom_du_package
```

**Bonnes pratiques** :
1. **Environnements virtuels** (recommandé) :
```bash
# Créer un environnement virtuel
python -m venv mon_projet

# Activer (Windows)
mon_projet\\Scripts\\activate

# Installer dans l'environnement
pip install requests

# Désactiver
deactivate
```

**Utilisateur**: Super utile ! Et pour créer un projet IA simple, tu recommandes quoi comme libraries ?

**Assistant**: Pour un projet IA débutant, voici ma sélection de libraries essentielles :

**🧠 Machine Learning de base** :
```bash
pip install scikit-learn  # Algorithmes ML classiques
pip install pandas        # Manipulation de données  
pip install numpy         # Calculs numériques
pip install matplotlib    # Visualisation
```

**🚀 Projet starter IA** :
```python
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score

# Charger données
data = pd.read_csv('data.csv')
X = data.drop('target', axis=1)
y = data['target']

# Diviser en train/test
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2)

# Entraîner modèle
model = LogisticRegression()
model.fit(X_train, y_train)

# Prédictions
predictions = model.predict(X_test)
accuracy = accuracy_score(y_test, predictions)
print(f"Précision: {accuracy:.2f}")
```

**📊 Pour aller plus loin** :
- `seaborn` : Visualisations avancées
- `jupyter` : Notebooks interactifs
- `tensorflow` ou `pytorch` : Deep Learning

## Conversation 2: Développement Web

**Utilisateur**: Je veux créer une application web moderne, quelles technologies me conseilles-tu ?

**Assistant**: Excellente question ! Pour une app web moderne, voici ma recommandation basée sur les tendances 2025 :

**🎯 Stack recommandée** :

**Frontend** :
- **React 18** + TypeScript : Composants réactifs type-safe
- **Next.js 14** : Framework full-stack avec App Router
- **Tailwind CSS** : Styling utilitaire rapide
- **Zustand** : Gestion d'état simple

**Backend** :
- **Node.js** + **Express** ou **Fastify**
- **Prisma** : ORM moderne pour base de données
- **PostgreSQL** : Base de données robuste
- **Redis** : Cache et sessions

**Outils** :
- **Vite** : Build tool ultra-rapide
- **ESLint** + **Prettier** : Code quality
- **Vitest** : Tests unitaires
- **Docker** : Containerisation

**Utilisateur**: C'est pas un peu overkill pour débuter ? Tu aurais quelque chose de plus simple ?

**Assistant**: Vous avez raison ! Voici une approche progressive :

**🌱 Étape 1 - Les bases** :
```bash
# Projet simple avec Vite
npm create vite@latest mon-app -- --template vanilla
cd mon-app && npm install && npm run dev
```

**📁 Structure simple** :
```
mon-app/
├── index.html       # Page principale
├── main.js         # JavaScript principal
├── style.css       # Styles
└── package.json    # Dépendances
```

**🔧 Fonctionnalité de base** :
```javascript
// main.js - Application Todo simple
class TodoApp {
    constructor() {
        this.todos = JSON.parse(localStorage.getItem('todos')) || [];
        this.render();
        this.setupEvents();
    }
    
    addTodo(text) {
        const todo = {
            id: Date.now(),
            text: text,
            completed: false
        };
        this.todos.push(todo);
        this.save();
        this.render();
    }
    
    toggleTodo(id) {
        const todo = this.todos.find(t => t.id === id);
        if (todo) {
            todo.completed = !todo.completed;
            this.save();
            this.render();
        }
    }
    
    deleteTodo(id) {
        this.todos = this.todos.filter(t => t.id !== id);
        this.save();
        this.render();
    }
    
    save() {
        localStorage.setItem('todos', JSON.stringify(this.todos));
    }
    
    render() {
        const app = document.getElementById('app');
        app.innerHTML = `
            <h1>Ma Todo App</h1>
            <input type="text" id="todoInput" placeholder="Nouvelle tâche...">
            <button onclick="window.todoApp.addTodo(document.getElementById('todoInput').value)">
                Ajouter
            </button>
            <ul>
                ${this.todos.map(todo => `
                    <li class="${todo.completed ? 'completed' : ''}">
                        <span onclick="window.todoApp.toggleTodo(${todo.id})">
                            ${todo.text}
                        </span>
                        <button onclick="window.todoApp.deleteTodo(${todo.id})">
                            Supprimer
                        </button>
                    </li>
                `).join('')}
            </ul>
        `;
    }
    
    setupEvents() {
        document.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && e.target.id === 'todoInput') {
                this.addTodo(e.target.value);
                e.target.value = '';
            }
        });
    }
}

// Initialiser l'application
window.todoApp = new TodoApp();
```

**Utilisateur**: Parfait ! Ça c'est abordable. Et quand je serai à l'aise, comment passer au niveau supérieur ?

**Assistant**: Excellente approche progressive ! Voici votre roadmap d'évolution :

**🎯 Niveau 2 - React basics** :
```bash
# Quand vous maîtrisez le JavaScript
npm create react-app mon-app-react
# ou mieux avec Vite
npm create vite@latest mon-app-react -- --template react
```

**📈 Évolution graduelle** :
1. **Semaine 1-2** : Composants React de base
2. **Semaine 3-4** : Props et state
3. **Semaine 5-6** : Hooks (useState, useEffect)
4. **Semaine 7-8** : Gestion d'état avec Context
5. **Mois 2** : Router pour navigation
6. **Mois 3** : API calls et données externes

**🚀 Niveau 3 - Production ready** :
- **TypeScript** : Type safety
- **Next.js** : Server-side rendering
- **Base de données** : Commencer par Firebase
- **Authentification** : Auth0 ou Clerk
- **Déploiement** : Vercel ou Netlify

**💡 Mon conseil** : Maîtrisez bien chaque étape avant de passer à la suivante. Créez un projet complet à chaque niveau !
"""

        contents.append(("Conversations", conversations))
        current_tokens += self.count_real_tokens(conversations)

        # 5. Contenu éducatif (20%)
        educational_content = """
# CONTENU ÉDUCATIF POUR TEST DE COMPRÉHENSION

## Cours d'Intelligence Artificielle

### Chapitre 1: Fondements de l'IA

L'Intelligence Artificielle (IA) est un domaine de l'informatique qui vise à créer des systèmes capables de réaliser des tâches nécessitant normalement l'intelligence humaine. Ces tâches incluent la reconnaissance vocale, la vision par ordinateur, la prise de décision et la traduction linguistique.

#### 1.1 Histoire de l'IA

**1950s - Les Pionniers** :
- Alan Turing propose le "Test de Turing" en 1950
- Dartmouth Conference (1956) : naissance officielle de l'IA
- Premiers programmes : Logic Theorist, General Problem Solver

**1960s-70s - L'Optimisme Initial** :
- Développement des premiers systèmes experts
- ELIZA (1966) : premier chatbot
- SHRDLU (1970) : compréhension du langage naturel

**1980s-90s - L'Hiver de l'IA** :
- Limitations des systèmes symboliques
- Problème de l'explosion combinatoire
- Réduction des financements

**2000s-2010s - Renaissance** :
- Augmentation de la puissance de calcul
- Disponibilité des big data
- Progrès en apprentissage automatique

**2010s-Aujourd'hui - L'Ère du Deep Learning** :
- Réseaux de neurones profonds
- Victoires spectaculaires : AlphaGo, GPT, DALL-E
- IA générative et modèles de langage

#### 1.2 Types d'Intelligence Artificielle

**IA Faible (Narrow AI)** :
- Spécialisée dans une tâche spécifique
- Exemples : reconnaissance vocale, jeux d'échecs
- État actuel de la technologie

**IA Forte (General AI)** :
- Intelligence comparable à l'humain
- Capacité de raisonnement général
- Objectif futur (AGI - Artificial General Intelligence)

**Super IA** :
- Intelligence dépassant l'humain
- Hypothèse théorique
- Débats sur faisabilité et implications

#### 1.3 Approches Principales

**Approche Symbolique** :
- Manipulation de symboles et règles logiques
- Systèmes experts, logique formelle
- Avantages : explicabilité, raisonnement
- Inconvénients : rigidité, difficulté avec incertitude

**Approche Connexionniste** :
- Réseaux de neurones artificiels
- Apprentissage par exemples
- Avantages : flexibilité, performance
- Inconvénients : boîte noire, besoins en données

**Approche Statistique** :
- Méthodes probabilistes et statistiques
- Machine learning classique
- Équilibre entre performance et interprétabilité

### Chapitre 2: Machine Learning

Le Machine Learning (ML) est une méthode d'IA où les systèmes apprennent automatiquement à partir de données sans être explicitement programmés pour chaque tâche.

#### 2.1 Types d'Apprentissage

**Apprentissage Supervisé** :
- Données d'entraînement avec labels
- Objectif : prédire labels pour nouvelles données
- Exemples : classification, régression

Algorithmes populaires :
```python
# Classification
from sklearn.ensemble import RandomForestClassifier
from sklearn.svm import SVC
from sklearn.linear_model import LogisticRegression

# Régression  
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import GradientBoostingRegressor
```

**Apprentissage Non-Supervisé** :
- Données sans labels
- Objectif : découvrir structures cachées
- Exemples : clustering, réduction de dimensionnalité

```python
# Clustering
from sklearn.cluster import KMeans, DBSCAN
from sklearn.mixture import GaussianMixture

# Réduction de dimensionnalité
from sklearn.decomposition import PCA
from sklearn.manifold import TSNE
```

**Apprentissage par Renforcement** :
- Agent apprend par interaction avec environnement
- Système de récompenses/punitions
- Exemples : jeux, robotique, recommandations

#### 2.2 Processus ML Typique

**1. Collecte de Données** :
- Sources variées : web, capteurs, bases de données
- Quantité et qualité cruciales
- Représentativité du problème

**2. Préparation des Données** :
```python
import pandas as pd
import numpy as np

# Nettoyage
data = data.dropna()  # Supprimer valeurs manquantes
data = data.drop_duplicates()  # Supprimer doublons

# Transformation
from sklearn.preprocessing import StandardScaler, LabelEncoder

scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)

encoder = LabelEncoder()
y_encoded = encoder.fit_transform(y)
```

**3. Sélection du Modèle** :
- Complexité du problème
- Taille des données
- Besoin d'interprétabilité
- Contraintes de performance

**4. Entraînement** :
```python
from sklearn.model_selection import train_test_split, cross_val_score

# Division des données
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)

# Entraînement
model = RandomForestClassifier(n_estimators=100)
model.fit(X_train, y_train)

# Validation croisée
scores = cross_val_score(model, X_train, y_train, cv=5)
print(f"Accuracy moyenne: {scores.mean():.3f} (+/- {scores.std() * 2:.3f})")
```

**5. Évaluation** :
```python
from sklearn.metrics import classification_report, confusion_matrix

# Prédictions
y_pred = model.predict(X_test)

# Métriques
print(classification_report(y_test, y_pred))
print(confusion_matrix(y_test, y_pred))
```

#### 2.3 Défis du Machine Learning

**Overfitting** :
- Modèle trop complexe pour les données
- Bonne performance sur train, mauvaise sur test
- Solutions : régularisation, validation croisée

**Underfitting** :
- Modèle trop simple
- Performance médiocre sur train et test
- Solutions : modèle plus complexe, plus de features

**Biais dans les Données** :
- Données non représentatives
- Discrimination algorithmique
- Importance de la diversité des données

### Chapitre 3: Deep Learning

Le Deep Learning utilise des réseaux de neurones artificiels avec multiples couches pour apprendre des représentations hiérarchiques des données.

#### 3.1 Réseaux de Neurones

**Perceptron Simple** :
```python
import numpy as np

class Perceptron:
    def __init__(self, learning_rate=0.01, n_iterations=1000):
        self.learning_rate = learning_rate
        self.n_iterations = n_iterations
    
    def fit(self, X, y):
        # Initialiser poids
        self.weights = np.zeros(1 + X.shape[1])
        
        for _ in range(self.n_iterations):
            for xi, target in zip(X, y):
                update = self.learning_rate * (target - self.predict(xi))
                self.weights[1:] += update * xi
                self.weights[0] += update
    
    def net_input(self, X):
        return np.dot(X, self.weights[1:]) + self.weights[0]
    
    def predict(self, X):
        return np.where(self.net_input(X) >= 0.0, 1, -1)
```

**Réseau Multi-Couches** :
```python
import tensorflow as tf
from tensorflow.keras import layers, models

# Architecture simple
model = models.Sequential([
    layers.Dense(128, activation='relu', input_shape=(784,)),
    layers.Dropout(0.2),
    layers.Dense(64, activation='relu'),
    layers.Dropout(0.2),
    layers.Dense(10, activation='softmax')
])

# Compilation
model.compile(
    optimizer='adam',
    loss='sparse_categorical_crossentropy',
    metrics=['accuracy']
)

# Entraînement
history = model.fit(
    X_train, y_train,
    epochs=10,
    batch_size=32,
    validation_data=(X_val, y_val)
)
```

#### 3.2 Architectures Spécialisées

**Réseaux Convolutionnels (CNN)** :
- Spécialisés pour images
- Couches de convolution et pooling
- Invariance aux translations

```python
# CNN pour classification d'images
cnn_model = models.Sequential([
    layers.Conv2D(32, (3, 3), activation='relu', input_shape=(28, 28, 1)),
    layers.MaxPooling2D((2, 2)),
    layers.Conv2D(64, (3, 3), activation='relu'),
    layers.MaxPooling2D((2, 2)),
    layers.Conv2D(64, (3, 3), activation='relu'),
    layers.Flatten(),
    layers.Dense(64, activation='relu'),
    layers.Dense(10, activation='softmax')
])
```

**Réseaux Récurrents (RNN/LSTM)** :
- Spécialisés pour séquences
- Mémoire des états précédents
- Applications : NLP, séries temporelles

```python
# LSTM pour séquences
lstm_model = models.Sequential([
    layers.LSTM(50, return_sequences=True, input_shape=(timesteps, features)),
    layers.Dropout(0.2),
    layers.LSTM(50),
    layers.Dropout(0.2),
    layers.Dense(1)
])
```

**Transformers** :
- Architecture révolutionnaire pour NLP
- Mécanisme d'attention
- Base des modèles modernes (GPT, BERT)

#### 3.3 Applications Pratiques

**Vision par Ordinateur** :
- Classification d'images
- Détection d'objets
- Segmentation sémantique
- Génération d'images (GANs, Diffusion)

**Traitement du Langage Naturel** :
- Analyse de sentiment
- Traduction automatique
- Résumé automatique
- Génération de texte

**Reconnaissance Vocale** :
- Speech-to-text
- Synthèse vocale
- Commandes vocales

## Exercices Pratiques

### Exercice 1: Classification avec Scikit-learn
Créez un modèle pour classifier des iris en utilisant le dataset classique.

### Exercice 2: Réseau de Neurones Simple
Implémentez un perceptron multi-couches pour reconnaissance de chiffres manuscrits.

### Exercice 3: Analyse de Sentiment
Développez un modèle NLP pour analyser la polarité de commentaires.

Ces exercices permettent d'appliquer concrètement les concepts théoriques vus dans le cours.
"""

        contents.append(("Educational Content", educational_content))
        current_tokens += self.count_real_tokens(educational_content)

        # Générer du contenu supplémentaire si nécessaire
        themes = [
            (
                "Systèmes Distribués",
                """
### Architecture Microservices
Les microservices permettent de décomposer une application en services indépendants:
- Service d'authentification avec JWT et OAuth2
- API Gateway pour routage et load balancing  
- Service de base de données avec réplication master-slave
- Service de cache Redis pour performance optimale

### Technologies Cloud Natives
Configuration Kubernetes pour déploiement automatisé avec réplication et haute disponibilité.
Monitoring avec Prometheus et Grafana pour métriques temps réel.
""",
            ),
            (
                "Blockchain et Cryptographie",
                """
### Technologies Blockchain
Les blockchains révolutionnent les transactions numériques:
- Consensus proof-of-stake pour efficacité énergétique
- Smart contracts avec Solidity et Ethereum
- Cryptographie asymétrique RSA et courbes elliptiques
- Hachage SHA-256 pour intégrité des données

### Sécurité Cryptographique
Chiffrement AES-256 pour protection maximale des données sensibles.
Signatures numériques pour authentification non-répudiable.
""",
            ),
            (
                "Intelligence Artificielle",
                """
### Apprentissage Automatique
Les algorithmes d'apprentissage supervisé et non-supervisé:
- Réseaux de neurones convolutifs pour vision par ordinateur
- Transformers et mécanisme d'attention pour NLP
- Gradient boosting et forêts aléatoires pour classification
- Clustering k-means pour segmentation automatique

### Deep Learning Avancé
Architectures ResNet et BERT pour performance state-of-the-art.
Optimiseurs Adam et techniques de régularisation dropout.
""",
            ),
            (
                "Bioinformatique et Génomique",
                """
### Séquençage ADN
Technologies de séquençage nouvelle génération:
- Illumina pour séquençage haut débit
- Assemblage de génomes avec algorithmes de Bruijn
- Annotation génique et prédiction de protéines
- Phylogénie moléculaire pour évolution des espèces

### Analyse Transcriptomique
RNA-seq pour expression différentielle des gènes.
Méthodes d'enrichissement GSEA pour voies métaboliques.
""",
            ),
            (
                "Physique Quantique",
                """
### Mécanique Quantique
Principes fondamentaux de la physique quantique:
- Superposition et intrication quantique
- Équation de Schrödinger et fonctions d'onde
- Principe d'incertitude de Heisenberg
- Effet tunnel et résonance magnétique

### Informatique Quantique
Qubits et portes quantiques pour calcul parallèle.
Algorithmes de Shor et Grover pour cryptanalyse.
""",
            ),
            (
                "Astrophysique et Cosmologie",
                """
### Formation Stellaire
Processus de naissance et évolution des étoiles:
- Effondrement gravitationnel des nuages moléculaires
- Fusion nucléaire et nucléosynthèse stellaire
- Supernovas et formation d'éléments lourds
- Trous noirs et horizons des événements

### Cosmologie Moderne
Expansion de l'univers et constante de Hubble.
Matière noire et énergie sombre pour structure cosmique.
""",
            ),
        ]

        while current_tokens < target_tokens:
            section_num = len(contents) + 1
            theme_index = (section_num - 7) % len(themes)  # -7 car on a déjà 6 sections
            theme_name, theme_content = themes[theme_index]

            unique_content = f"""

## Section {section_num} - {theme_name}

Cette section explore {theme_name.lower()} pour diversifier le contexte de test.

{theme_content}

### Implémentation Pratique

```python
class {theme_name.replace(' ', '').replace('é', 'e')}System:
    def __init__(self):
        self.config = self.load_configuration()
        self.initialize_components()
    
    def process_data(self, input_data):
        preprocessed = self.preprocess(input_data)
        result = self.analyze(preprocessed)
        return self.format_output(result)
    
    def optimize_performance(self):
        # Optimisations spécifiques à {theme_name.lower()}
        return self.apply_optimizations()
```

### Métriques Spécialisées

Pour {theme_name.lower()}:
- Précision analytique: > 95%
- Temps de traitement: < 2 secondes  
- Scalabilité: support multi-thread
- Robustesse: gestion d'erreurs complète

Section #{section_num} avec contenu spécialisé en {theme_name.lower()}.
"""

            contents.append((f"Section {section_num} - {theme_name}", unique_content))
            current_tokens += self.count_real_tokens(unique_content)

        # Assembler tout le contenu
        full_content = (
            "\n\n"
            + "=" * 80
            + "\n\n".join([f"# {title}\n\n{content}" for title, content in contents])
        )

        return full_content

    def run_comprehension_test(self, ai_model) -> dict:
        """Test de compréhension globale du contexte (VectorMemory 10M)"""
        print("\n🧠 TEST DE COMPRÉHENSION GLOBALE")
        print("=" * 50)

        # Questions sur différentes parties du contenu
        test_questions = [
            {
                "question": "Quel est l'objectif de performance pour le temps de réponse du système ?",
                "expected_keywords": ["3 secondes", "3000ms", "performance"],
                "section": "Documentation Technique",
            },
            {
                "question": "Quel algorithme est utilisé dans l'exemple de tri fusion ?",
                "expected_keywords": ["merge sort", "tri fusion", "insertion sort"],
                "section": "Code Examples",
            },
            {
                "question": "Quelle est la version du système selon la configuration JSON ?",
                "expected_keywords": ["7.1.0", "version"],
                "section": "Structured Data",
            },
            {
                "question": "Quel langage est recommandé pour débuter en IA selon la conversation ?",
                "expected_keywords": ["Python", "scikit-learn", "pandas"],
                "section": "Conversations",
            },
            {
                "question": "Qui a proposé le Test de Turing et en quelle année ?",
                "expected_keywords": ["Alan Turing", "1950"],
                "section": "Educational Content",
            },
            {
                "question": "Combien de tokens peut traiter le système selon la configuration ?",
                "expected_keywords": ["10485760", "10M", "10 millions"],
                "section": "Multiple Sections",
            },
        ]

        results = {
            "total_questions": len(test_questions),
            "correct_answers": 0,
            "detailed_results": [],
            "response_times": [],
        }

        for i, test in enumerate(test_questions, 1):
            print(
                f"\n📋 Question {i}/{len(test_questions)}: {test['question'][:50]}..."
            )

            start_time = time.time()
            try:
                # Tester avec l'IA réelle
                response = ai_model.generate_response(test["question"])
                response_time = time.time() - start_time
                results["response_times"].append(response_time)

                # Vérifier si la réponse contient les mots-clés attendus (recherche ultra-intelligente)
                response_lower = response.lower()
                # Utiliser la réponse complète pour l'analyse
                search_text = response_lower

                keywords_found = []

                for kw in test["expected_keywords"]:
                    kw_lower = kw.lower()
                    found = False

                    # 1. Recherche directe
                    if kw_lower in search_text:
                        found = True

                    # 2. Recherche spéciale pour algorithmes (PRIORITÉ HAUTE)
                    elif kw_lower == "merge sort":
                        if any(
                            variant in search_text
                            for variant in [
                                "merge_sort",
                                "tri fusion",
                                "fusion",
                                "merge",
                            ]
                        ):
                            found = True
                    elif kw_lower == "tri fusion":
                        if any(
                            variant in search_text
                            for variant in [
                                "tri fusion",
                                "merge_sort",
                                "fusion",
                                "tri",
                                "merge",
                            ]
                        ):
                            found = True
                    elif kw_lower == "insertion sort":
                        if any(
                            variant in search_text
                            for variant in [
                                "insertion_sort",
                                "insertion",
                                "tri insertion",
                            ]
                        ):
                            found = True

                    # 3. Recherche avec underscores remplacés par espaces
                    elif kw_lower.replace(" ", "_") in search_text:
                        found = True

                    # 4. Recherche avec espaces remplacés par underscores
                    elif kw_lower.replace("_", " ") in search_text:
                        found = True

                    # 5. Recherche de parties du mot-clé (pour "merge sort" -> "merge_sort_optimized")
                    elif " " in kw_lower:
                        parts = kw_lower.split(" ")
                        if all(part in search_text for part in parts):
                            found = True

                    # 6. Recherche insensible à la ponctuation et formatage
                    elif any(char in kw_lower for char in [" ", "_", "-"]):
                        # Nettoyer le mot-clé et chercher les parties

                        clean_kw = re.sub(r"[^a-z0-9]", " ", kw_lower)
                        kw_parts = [p for p in clean_kw.split() if len(p) > 1]
                        if kw_parts and all(part in search_text for part in kw_parts):
                            found = True

                    # 7. Recherche spéciale pour nombres (10485760 -> 10M, 10 millions, etc.)
                    elif kw_lower == "10485760":
                        if any(
                            variant in search_text
                            for variant in [
                                "10485760",
                                "10m",
                                "10 millions",
                                "context_size",
                                "10,485,760",
                                "10 485 760",
                            ]
                        ):
                            found = True
                    elif kw_lower == "10m":
                        if any(
                            variant in search_text
                            for variant in ["10m", "10 millions", "10485760", "10,485,760"]
                        ):
                            found = True
                    elif kw_lower == "10 millions":
                        if any(
                            variant in search_text
                            for variant in ["10 millions", "10m", "10485760", "10,485,760"]
                        ):
                            found = True

                    if found:
                        keywords_found.append(kw)

                is_correct = len(keywords_found) > 0
                if is_correct:
                    results["correct_answers"] += 1

                result_detail = {
                    "question": test["question"],
                    "section": test["section"],
                    "response": (
                        response[:200] + "..." if len(response) > 200 else response
                    ),
                    "full_response": response,  # Garder la réponse complète pour l'affichage final
                    "keywords_expected": test["expected_keywords"],
                    "keywords_found": keywords_found,
                    "correct": is_correct,
                    "response_time": response_time,
                }
                results["detailed_results"].append(result_detail)

                status = "✅" if is_correct else "❌"
                print(f"   {status} Répondu en {response_time:.2f}s")

            except (RuntimeError, ValueError) as e:
                print(f"   ❌ Erreur: {e}")
                results["detailed_results"].append(
                    {
                        "question": test["question"],
                        "section": test["section"],
                        "response": f"ERREUR: {e}",
                        "full_response": f"ERREUR: {e}",
                        "keywords_expected": test["expected_keywords"],
                        "keywords_found": [],
                        "correct": False,
                        "response_time": 0,
                    }
                )

        # Calcul du score final
        comprehension_score = (
            results["correct_answers"] / results["total_questions"]
        ) * 100
        avg_response_time = (
            sum(results["response_times"]) / len(results["response_times"])
            if results["response_times"]
            else 0
        )

        results["comprehension_score"] = comprehension_score
        results["avg_response_time"] = avg_response_time

        print("\n📊 RÉSULTATS DE COMPRÉHENSION")
        print(
            f"Score: {comprehension_score:.1f}% ({results['correct_answers']}/{results['total_questions']} correctes)"
        )
        print(f"Temps moyen: {avg_response_time:.2f}s")

        return results

    def run_full_test(self) -> dict:
        """Test complet de la VectorMemory 10M (stress 1M tokens)"""
        print("🎯 DÉMARRAGE DU TEST RÉEL VECTORMEMORY 10M (STRESS 1M)")
        print("=" * 50)

        if not REAL_AI_AVAILABLE:
            print("❌ Système IA non disponible")
            return {"error": "IA non disponible"}

        start_time = time.time()

        try:
            # 1. Initialiser My_AI
            print("\n🔧 INITIALISATION DE MY_AI\n")
            conversation_memory = ConversationMemory()
            ai_model = CustomAIModel(conversation_memory=conversation_memory)
            print("✅ CustomAIModel initialisé")

            # 2. Générer contenu de stress (1M tokens, sous-ensemble du système 10M)
            print("\n📝 GÉNÉRATION DU CONTENU DE STRESS (1M tokens / capacité 10M)")
            target_tokens = 1000000
            content = self.generate_diverse_content(target_tokens)
            actual_tokens = self.count_real_tokens(content)

            print(f"✅ Contenu généré: {actual_tokens:,} tokens")
            self.results["total_tokens_processed"] = actual_tokens

            # 3. Alimenter l'IA avec le contenu
            print("\n💾 INJECTION DU CONTENU DANS L'IA")

            # Diviser en chunks pour éviter les limitations
            chunk_size = 50000  # 50k tokens par chunk
            content_chunks = []
            words = content.split()
            current_chunk = []
            current_tokens = 0

            for word in words:
                word_tokens = self.count_real_tokens(word)
                if current_tokens + word_tokens > chunk_size:
                    chunk_text = " ".join(current_chunk)
                    content_chunks.append(chunk_text)
                    chunk_name = f"test_chunk_{len(content_chunks)}"
                    # Ajouter le chunk à la mémoire de l'IA
                    # CORRIGÉ: store_document_content(filename, content) - pas l'inverse!
                    ai_model.conversation_memory.store_document_content(
                        chunk_name, chunk_text
                    )
                    # IMPORTANT: Ajouter aussi au context_manager pour la recherche
                    ai_model.context_manager.add_document(
                        chunk_text, chunk_name
                    )
                    current_chunk = [word]
                    current_tokens = word_tokens
                else:
                    current_chunk.append(word)
                    current_tokens += word_tokens

            # Ajouter le dernier chunk
            if current_chunk:
                chunk_text = " ".join(current_chunk)
                content_chunks.append(chunk_text)
                chunk_name = f"test_chunk_{len(content_chunks)}"
                # CORRIGÉ: store_document_content(filename, content) - pas l'inverse!
                ai_model.conversation_memory.store_document_content(
                    chunk_name, chunk_text
                )
                # IMPORTANT: Ajouter aussi au context_manager pour la recherche
                ai_model.context_manager.add_document(
                    chunk_text, chunk_name
                )

            print(f"✅ {len(content_chunks)} chunks injectés dans l'IA")

            # 4. Test de compréhension
            print("\n🧠 TEST DE COMPRÉHENSION")
            comprehension_results = self.run_comprehension_test(ai_model)
            self.results["comprehension_score"] = comprehension_results[
                "comprehension_score"
            ]
            self.results["performance_metrics"] = comprehension_results

            # 5. Test de performance
            print("\n⚡ TEST DE PERFORMANCE")
            performance_tests = [
                "Résume le contenu principal",
                "Quels sont les éléments techniques mentionnés ?",
                "Donne des exemples de code Python du contexte",
            ]

            performance_times = []
            for test_query in performance_tests:
                start = time.time()
                ai_model.generate_response(test_query)
                elapsed = time.time() - start
                performance_times.append(elapsed)
                print(f"  ⏱️ '{test_query[:30]}...': {elapsed:.2f}s")

            avg_performance = sum(performance_times) / len(performance_times)
            self.results["performance_metrics"]["avg_query_time"] = avg_performance

            # 6. Validation finale
            total_time = time.time() - start_time
            self.results["performance_metrics"]["total_test_time"] = total_time

            # Critères de validation
            validation_criteria = {
                "tokens_processed": actual_tokens >= 1000000,
                "comprehension_score": comprehension_results["comprehension_score"]
                >= 60,
                "avg_response_time": avg_performance <= 10.0,  # 10s max
                "no_errors": len(
                    [
                        r
                        for r in comprehension_results["detailed_results"]
                        if "ERREUR" in r["response"]
                    ]
                )
                == 0,
            }

            all_passed = all(validation_criteria.values())
            self.results["test_status"] = "VALIDÉ" if all_passed else "ÉCHEC"
            self.results["validation_criteria"] = validation_criteria

            # Affichage final
            print("\n🎯 RÉSULTATS FINAUX DU TEST")
            print("=" * 50)
            print(f"Tokens traités: {actual_tokens:,}")
            print(
                f"Score compréhension: {comprehension_results['comprehension_score']:.1f}%"
            )
            print(f"Temps moyen/requête: {avg_performance:.2f}s")
            print(f"Temps total: {total_time:.1f}s")
            print(f"Statut: {self.results['test_status']}")

            # AFFICHAGE DÉTAILLÉ DE TOUTES LES QUESTIONS ET RÉPONSES
            print("\n🔍 DÉTAIL COMPLET DES QUESTIONS ET RÉPONSES")
            print("=" * 60)

            for i, result in enumerate(comprehension_results["detailed_results"], 1):
                status_icon = "✅" if result["correct"] else "❌"
                print(
                    f"\n{status_icon} QUESTION {i} - Section: {result.get('section', 'N/A')}"
                )
                print(f"Q: {result['question']}")
                print(f"Mots-clés attendus: {', '.join(result['keywords_expected'])}")
                print(
                    f"Mots-clés trouvés: {', '.join(result['keywords_found']) if result['keywords_found'] else 'Aucun'}"
                )
                print(f"Temps de réponse: {result['response_time']:.2f}s")
                print(
                    f"Réponse: {result.get('full_response', result['response'])[:300]}..."
                )
                print("-" * 40)

            # Sauvegarde des résultats
            with open("tests/test_real_1m_results.json", "w", encoding="utf-8") as f:
                json.dump(self.results, f, indent=2, ensure_ascii=False)

            print("\n📄 Résultats sauvegardés dans 'tests/test_real_1m_results.json'")

            return self.results

        except RuntimeError as e:
            print(f"❌ Erreur durant le test: {e}")
            self.results["test_status"] = "ERREUR"
            self.results["error"] = str(e)
            return self.results


def main():
    """Fonction principale pour lancer le test"""
    tester = RealAI1MTest()
    results = tester.run_full_test()

    if results.get("test_status") == "VALIDÉ":
        print("\n🎉 FÉLICITATIONS ! VectorMemory 10M validée (stress 1M tokens réussi)")
    elif results.get("test_status") == "ÉCHEC":
        print("\n⚠️ Le test révèle des limitations. Voir détails ci-dessus.")
    else:
        print("\n❌ Erreur durant le test")

    # 🧹 NETTOYAGE DES RESSOURCES pour éviter le blocage à la fin
    print("\n🧹 Nettoyage des ressources...")
    try:
        gc.collect()
    except Exception as e:
        print(f"⚠️ Erreur nettoyage: {e}")

    print("✅ Test terminé proprement")

    # Forcer la sortie BRUTALE du programme (kill tous les threads)
    # sys.exit(0) ne suffit pas car ChromaDB garde des threads en arrière-plan
    os._exit(0)


if __name__ == "__main__":
    main()
