# 🎨 Utilisation des Agents dans l'Interface Graphique

## Accès à l'onglet Agents

1. Lancez l'interface graphique : `python launch_unified.py` ou `python main.py`
2. Cliquez sur l'onglet **🤖 Agents** en haut de l'interface

## 📋 Interface Agents

### Vue d'ensemble

L'interface agents est divisée en plusieurs sections :

#### 1️⃣ **Sélection d'Agents**
6 cartes représentant chaque agent spécialisé :
- **🐍 CodeAgent** - Génération et debug de code
- **📚 ResearchAgent** - Recherche et documentation
- **📊 AnalystAgent** - Analyse de données
- **✨ CreativeAgent** - Contenu créatif
- **🐛 DebugAgent** - Debug et correction
- **📋 PlannerAgent** - Planification

**Comment utiliser :**
- Cliquez sur "Sélectionner" sur la carte de l'agent désiré
- La carte se mettra en surbrillance avec sa couleur distinctive
- Le statut indiquera "✅ Agent sélectionné"

#### 2️⃣ **Zone de Tâche**
Grande zone de texte pour décrire votre tâche

**Exemple de tâches :**
```
Pour CodeAgent:
"Crée une fonction Python qui trie une liste de nombres par ordre décroissant"

Pour ResearchAgent:
"Recherche les nouveautés de Python 3.13"

Pour AnalystAgent:
"Analyse ce dataset et donne-moi les statistiques principales: [1, 5, 3, 9, 2, 7]"

Pour CreativeAgent:
"Rédige une introduction engageante pour un article sur l'IA"

Pour DebugAgent:
"Mon code plante avec IndexError: list index out of range sur la ligne my_list[5]"

Pour PlannerAgent:
"Planifie le développement d'un bot Discord qui répond aux commandes"
```

**Actions :**
- Écrivez votre tâche dans la zone
- Cliquez sur **▶ Exécuter** (grand bouton orange)
- Le statut passera à "⏳ Traitement en cours..."

#### 3️⃣ **Workflows Multi-Agents**
3 workflows pré-configurés pour des tâches complexes

**💻 Développement Complet**
- Agents : Planner → Code → Debug
- Utilisation : Cliquez sur "Lancer", décrivez votre projet
- Exemple : "Un système d'authentification JWT avec Python"

**📚 Recherche & Doc**
- Agents : Research → Analyst → Creative
- Utilisation : Pour créer de la documentation complète
- Exemple : "Les microservices avec FastAPI"

**🔧 Debug Assisté**
- Agents : Debug → Code
- Utilisation : Pour corriger des erreurs
- Exemple : "Mon API Flask renvoie 500 Internal Server Error"

#### 4️⃣ **Zone de Résultats**
Grande zone avec scrollbar affichant :
- Les résultats de chaque agent
- Le code généré (avec coloration syntaxique)
- Les analyses et explications
- Les timestamps d'exécution

**Fonctionnalités :**
- Lecture seule (copier-coller possible)
- Scroll automatique vers le bas
- Historique de toutes les exécutions

#### 5️⃣ **Statistiques**
En bas de l'écran, 3 indicateurs :
- **Tâches Exécutées** : Nombre total de tâches
- **Agents Actifs** : Nombre d'agents utilisés
- **Taux de Succès** : Pourcentage de réussite

## 🎯 Scénarios d'Usage

### Scénario 1 : Génération de Code Simple
1. Sélectionner **CodeAgent** 🐍
2. Écrire : "Crée une calculatrice simple en Python"
3. Cliquer **▶ Exécuter**
4. Résultat : Code complet avec commentaires

### Scénario 2 : Développement d'une Feature Complète
1. Cliquer sur **💻 Développement Complet** (workflows)
2. Entrer : "Une API REST pour gérer une bibliothèque de livres"
3. Voir les 3 agents travailler en séquence :
   - PlannerAgent décompose le projet
   - CodeAgent génère le code
   - DebugAgent vérifie et optimise

### Scénario 3 : Recherche Approfondie
1. Sélectionner **ResearchAgent** 📚
2. Écrire : "Quelles sont les meilleures pratiques de sécurité en 2026 pour les APIs web ?"
3. Résultat : Synthèse structurée avec points clés

### Scénario 4 : Analyse de Données
1. Sélectionner **AnalystAgent** 📊
2. Coller vos données ou décrire le dataset
3. Résultat : Statistiques, tendances, insights

### Scénario 5 : Correction d'Erreur
1. Sélectionner **DebugAgent** 🐛
2. Décrire l'erreur et le contexte
3. Résultat : Explication de la cause + solution

## 💡 Conseils & Astuces

### Pour de meilleurs résultats :
- **Soyez spécifique** : Plus votre description est précise, meilleur sera le résultat
- **Incluez le contexte** : Mentionnez le langage, le framework, les contraintes
- **Utilisez les workflows** : Pour des tâches complexes, les workflows sont plus efficaces
- **Lisez les résultats** : Les agents fournissent souvent des explications utiles

### Optimisation :
- Les agents gardent une mémoire des tâches précédentes
- Vous pouvez enchaîner plusieurs tâches avec le même agent
- Les stats vous permettent de suivre votre utilisation

### Dépannage :
- **Aucun résultat** : Vérifiez qu'Ollama est lancé (`ollama serve`)
- **Erreur d'agent** : L'agent doit être sélectionné avant l'exécution
- **Timeout** : Tâches très complexes peuvent prendre du temps

## 🔄 Comparaison Chat vs Agents

| Aspect | Onglet Chat 💬 | Onglet Agents 🤖 |
|--------|----------------|------------------|
| **Usage** | Conversation générale | Tâches spécifiques |
| **Mémoire** | Conversation continue | Par agent |
| **Spécialisation** | Généraliste | Expertise ciblée |
| **Workflows** | Non | Oui (multi-agents) |
| **Idéal pour** | Questions, discussions | Projets, analyses |

## 🚀 Exemples Rapides par Agent

### CodeAgent 🐍
```
"Génère une classe Python pour gérer une file d'attente"
"Convertis cette boucle for en list comprehension"
"Crée des tests unitaires pour cette fonction"
```

### ResearchAgent 📚
```
"Recherche les différences entre FastAPI et Flask"
"Quels sont les frameworks JavaScript les plus populaires en 2026"
"Explique le concept de containerisation avec Docker"
```

### AnalystAgent 📊
```
"Analyse ces ventes : Janvier: 1000€, Février: 1200€, Mars: 950€"
"Compare les performances de ces algorithmes: [données]"
"Quels sont les KPIs importants pour une API REST"
```

### CreativeAgent ✨
```
"Rédige une description pour mon package Python"
"Crée un message d'accueil engageant pour mon bot"
"Génère 5 titres accrocheurs pour un article sur l'IA"
```

### DebugAgent 🐛
```
"Pourquoi j'ai une KeyError avec ce dictionnaire ?"
"Mon code Python a une indentation incorrecte, peux-tu le corriger ?"
"Analyse ce traceback: [stacktrace]"
```

### PlannerAgent 📋
```
"Planifie la migration de mon app Flask vers FastAPI"
"Décompose le développement d'un scraper web"
"Organise les étapes pour créer une API GraphQL"
```

## 🎨 Personnalisation

L'interface suit automatiquement le thème de votre interface principale :
- **Couleurs** : Adaptées au mode sombre
- **Polices** : Consistantes avec le reste de l'app
- **Layout** : Responsive et moderne

---

**Prêt à utiliser les agents ?** Lancez l'interface et cliquez sur l'onglet 🤖 Agents ! 🚀
