# 🎨 Utilisation des Agents dans l'Interface Graphique

## Accès à l'onglet Agents

1. Lancez l'interface graphique : `python launch_unified.py` ou `python main.py`
2. Cliquez sur l'onglet **🤖 Agents** en haut de l'interface

## 📋 Interface Agents

### Vue d'ensemble

L'interface agents est divisée en plusieurs sections :

#### 1️⃣ **Sélection d'Agents (Grille 3x3)**
9 cartes représentant chaque agent spécialisé :
- **💻 CodeAgent** - Génération et debug de code
- **🔍 ResearchAgent** - Recherche et documentation
- **📊 AnalystAgent** - Analyse de données
- **✨ CreativeAgent** - Contenu créatif
- **🐛 DebugAgent** - Debug et correction
- **📋 PlannerAgent** - Planification
- **🛡️ SecurityAgent** - Cybersécurité et audit
- **⚡ OptimizerAgent** - Optimisation et performance
- **🧬 DataScienceAgent** - Data science et ML

**Comment utiliser :**
- **Drag & Drop** : Glissez un agent depuis sa carte et déposez-le dans la zone de workflow
- Vous pouvez ajouter **plusieurs agents** pour créer un workflow personnalisé
- Les agents sont exécutés **dans l'ordre** où vous les avez ajoutés
- Chaque carte affiche une description détaillée de l'expertise de l'agent

#### 2️⃣ **Zone de Tâche et Workflow**

**Zone de texte** — Décrivez votre tâche :
```
"Crée une API REST sécurisée pour gérer des utilisateurs"
"Analyse ce dataset et donne-moi les tendances"
"Audite ce code pour les vulnérabilités de sécurité"
```

**Pipeline visuel** — Après avoir glissé-déposé des agents :
- Un pipeline coloré s'affiche avec les noms des agents et des flèches (→) entre eux
- Chaque agent apparaît dans un badge de sa couleur distinctive
- Cliquez sur un badge pour retirer un agent du workflow

**Boutons :**
- **► Exécuter** (orange) : Lance la tâche. Se transforme en **■ Stop** (blanc) pendant la génération
- **➕ Créer Agent** (bleu) : Ouvre l'interface de création d'agents personnalisés
- **❌ Clear Selection** (rouge) : Vide le workflow et la sélection en cours

#### 3️⃣ **Zone de Résultats**
Grande zone avec scrollbar affichant :
- Les résultats de chaque agent en temps réel (streaming token par token)
- Le code généré
- Les analyses et explications
- Les transitions entre étapes du workflow

**Fonctionnalités :**
- Lecture seule (copier-coller possible)
- Scroll automatique vers le bas
- Historique de toutes les exécutions

#### 4️⃣ **Statistiques**
En bas de l'écran, 3 indicateurs :
- **Tâches Exécutées** : Nombre total de tâches
- **Agents Actifs** : Nombre d'agents utilisés
- **Taux de Succès** : Pourcentage de réussite

## ⏹️ Bouton Stop

Pendant la génération, le bouton **▶ Exécuter** se transforme en bouton **■ Stop** :
- Apparence : Carré noir (■) sur fond blanc
- Cliquez dessus pour **interrompre immédiatement** la génération
- Dans un workflow multi-agents, **toutes les étapes restantes sont annulées**
- Le bouton revient automatiquement à son apparence normale après l'arrêt
- Le message "⛔ Génération interrompue" s'affiche dans les résultats

## 🎯 Scénarios d'Usage

### Scénario 1 : Agent unique
1. **Glisser** CodeAgent 💻 vers la zone de workflow
2. Écrire : "Crée une calculatrice simple en Python"
3. Cliquer **▶ Exécuter**
4. Résultat : Code complet avec commentaires

### Scénario 2 : Workflow personnalisé (Développement)
1. **Glisser** PlannerAgent 📋, puis CodeAgent 💻, puis DebugAgent 🐛
2. Le pipeline affiche : `PlannerAgent → CodeAgent → DebugAgent`
3. Écrire : "Une API REST pour gérer une bibliothèque de livres"
4. Cliquer **▶ Exécuter**
5. Voir les 3 agents travailler en séquence, chacun enrichissant le résultat du précédent

### Scénario 3 : Audit de sécurité
1. **Glisser** SecurityAgent 🛡️, puis CodeAgent 💻
2. Pipeline : `SecurityAgent → CodeAgent`
3. Coller votre code et écrire : "Audite et corrige les failles"
4. SecurityAgent identifie les vulnérabilités, CodeAgent les corrige

### Scénario 4 : Data Science
1. **Glisser** DataScienceAgent 🧬, puis AnalystAgent 📊
2. Pipeline : `DataScienceAgent → AnalystAgent`
3. Écrire : "Analyse ce dataset et propose un modèle prédictif"

### Scénario 5 : Optimisation de code
1. **Glisser** OptimizerAgent ⚡
2. Coller votre code et écrire : "Optimise les performances"
3. Résultat : Code refactorisé avec explications

### Scénario 6 : Interruption d'un workflow
1. Lancer un workflow multi-agents
2. Pendant l'exécution, cliquer sur **■ Stop**
3. La génération s'arrête immédiatement
4. Le bouton revient à **▶ Exécuter**

## 💡 Conseils & Astuces

### Pour de meilleurs résultats :
- **Soyez spécifique** : Plus votre description est précise, meilleur sera le résultat
- **Incluez le contexte** : Mentionnez le langage, le framework, les contraintes
- **Créez des workflows** : Pour des tâches complexes, combinez plusieurs agents par drag & drop
- **Lisez les résultats** : Les agents fournissent souvent des explications utiles

### Drag & Drop :
- Glissez depuis n'importe quelle partie de la carte agent
- Un indicateur flottant suit votre curseur pendant le drag
- Déposez dans la zone de workflow OU directement dans la zone de texte
- Ajoutez le même agent plusieurs fois si nécessaire
- Cliquez sur un badge dans le pipeline pour le retirer

### Optimisation :
- Les agents gardent une mémoire des tâches précédentes
- Vous pouvez enchaîner plusieurs tâches avec le même agent
- Les stats vous permettent de suivre votre utilisation
- Utilisez **✕ Clear Selection** pour recommencer un workflow depuis zéro

### Dépannage :
- **Aucun résultat** : Vérifiez qu'Ollama est lancé (`ollama serve`)
- **Erreur d'agent** : Au moins un agent doit être dans le workflow
- **Timeout** : Tâches très complexes peuvent prendre du temps
- **Workflow bloqué** : Utilisez le bouton Stop (■) pour interrompre

## 🎨 Création d'Agents Personnalisés

### Bouton "➕ Créer Agent"

Le bouton bleu **"➕ Créer Agent"** (entre Exécuter et Clear Selection) permet de créer vos propres agents spécialisés.

### Interface de Création

1. **Cliquez sur "➕ Créer Agent"**
2. Une **fenêtre modale** s'ouvre au centre avec :
   - **Champ Nom** : Nom court de l'agent (ex: "TranslatorAgent")
   - **Champ Rôle/Description** : Description détaillée de l'expertise
   - **Bouton "Créer"** (vert) : Lance la génération
   - **Bouton "Annuler"** (gris) : Ferme la fenêtre

3. **Remplissez les champs** :
   ```
   Nom : TranslatorAgent
   Rôle : Expert en traduction multilingue avec adaptation culturelle et nuances linguistiques
   ```

4. **Cliquez sur "Créer"** :
   - Un **spinner animé** apparaît (⠋⠙⠹⠸...)
   - **Ollama (llama3.2)** génère automatiquement :
     - Le **system prompt** optimisé
     - La **température** idéale (0.2-0.8)
     - Une **description courte** (3-4 mots)
   - **Notification verte** "✅ Agent créé !" en haut à droite
   - **Votre agent apparaît** dans la grille après les 9 agents par défaut

### Génération Automatique

L'IA analyse votre description et génère :

**Exemple** :
```
Description : "Expert en cybersécurité spécialisé dans les audits et la détection de vulnérabilités"

→ System Prompt généré :
"Tu es un expert en cybersécurité spécialisé dans les audits de code..."

→ Température : 0.2 (précision maximale)

→ Description courte : "Audit & Sécurité"
```

### Affichage des Agents Personnalisés

Les agents personnalisés apparaissent dans la grille **après les 9 agents par défaut** :

- **Icône** : 🤖 (pour tous les agents personnalisés)
- **Nom** : Votre nom d'agent
- **Description courte** : 3-4 mots générés automatiquement
- **Couleur** : Couleur vibrante aléatoire (#3b82f6, #10b981, #f59e0b, etc.)
- **Boutons d'action** (visibles au hover) :
  - **📝 Éditer** : Modifier le nom et la description
  - **✖ Supprimer** : Supprimer l'agent (avec confirmation)

### Édition d'un Agent Personnalisé

1. **Survolez la carte** de votre agent
2. **Cliquez sur 📝** (icône crayon en bas de la carte)
3. La **même fenêtre modale** s'ouvre avec les champs pré-remplis
4. **Modifiez** le nom et/ou la description
5. **Cliquez sur "Sauvegarder"** :
   - Si vous changez la **description** : Le system prompt est **régénéré** par Ollama
   - Si vous changez seulement le **nom** : Modification **instantanée**

### Suppression d'un Agent Personnalisé

1. **Cliquez sur ✖** (croix rouge en haut à droite de la carte)
2. Une **boîte de dialogue** demande confirmation
3. **Confirmez** : 
   - **Notification rouge** "❌ Agent supprimé" en haut à droite
   - L'agent disparaît de la grille
   - Suppression permanente du fichier `data/custom_agents.json`

### Utilisation dans les Workflows

Les agents personnalisés fonctionnent **exactement comme les agents par défaut** :

**Drag & Drop** :
- Glissez depuis la carte de l'agent personnalisé
- Déposez dans la zone de workflow
- Combinez avec d'autres agents (par défaut ou personnalisés)

**Exemple de workflow** :
```
1. Glisser TranslatorAgent 🤖
2. Glisser CreativeAgent ✨
3. Glisser CodeAgent 💻

Pipeline : TranslatorAgent → CreativeAgent → CodeAgent
```

### Conseils pour la Création

#### Description Détaillée
- **Soyez spécifique** : Plus la description est précise, meilleur sera le résultat
- **Mentionnez l'expertise** : Domaines, technologies, compétences
- **Indiquez le style** : Technique, créatif, analytique, etc.

#### Exemples de Bonnes Descriptions
✅ "Expert en traduction multilingue avec adaptation culturelle et nuances linguistiques"
✅ "Spécialiste en référencement naturel, optimisation de contenu et stratégie SEO"
✅ "Expert en CI/CD, containerisation Docker/Kubernetes et automatisation"
✅ "Designer UI/UX spécialisé dans les interfaces modernes et l'accessibilité"
✅ "Conseiller juridique en droit numérique, RGPD et propriété intellectuelle"

❌ "Traduction" (trop vague)
❌ "Un agent qui traduit" (pas assez professionnel)
❌ "Agent cool" (pas d'information utile)

#### Nommage
- **CamelCase** : TranslatorAgent, SEOAgent, DevOpsAgent
- **Suffixe "Agent"** : Pour cohérence
- **Court** : 2-3 mots maximum

### Persistance

Tous vos agents personnalisés sont **sauvegardés automatiquement** dans :
```
data/custom_agents.json
```

Ils sont **rechargés au démarrage** de l'application.

### Exemples d'Agents Personnalisés

#### 🌐 TranslatorAgent
```
Nom : TranslatorAgent
Rôle : Expert en traduction multilingue avec adaptation culturelle
Couleur : Bleu #3b82f6
Description courte : Traduction multilingue
```

#### 📈 SEOAgent
```
Nom : SEOAgent
Rôle : Spécialiste en référencement naturel et optimisation de contenu
Couleur : Vert #10b981
Description courte : SEO & référencement
```

#### 🔧 DevOpsAgent
```
Nom : DevOpsAgent
Rôle : Expert en CI/CD, containerisation et automatisation d'infrastructure
Couleur : Orange #f59e0b
Description courte : DevOps & CI/CD
```

### Limitations

- **Ollama requis** : La génération nécessite Ollama avec llama3.2
- **Nom unique** : Chaque agent doit avoir un nom différent
- **Pas de modification directe du prompt** : Pour garantir la cohérence
- **Suppression définitive** : Pas de récupération possible après suppression

## 🔄 Comparaison Chat vs Agents

| Aspect | Onglet Chat 💬 | Onglet Agents 🤖 |
|--------|----------------|------------------|
| **Usage** | Conversation générale | Tâches spécifiques |
| **Mémoire** | Conversation continue | Par agent |
| **Spécialisation** | Généraliste | 9 agents experts |
| **Workflows** | Non | Oui (drag & drop) |
| **Stop** | ■ pendant la génération | ■ pendant la génération |
| **Idéal pour** | Questions, discussions | Projets, analyses |

## 🚀 Exemples Rapides par Agent

### CodeAgent 💻
```
"Génère une classe Python pour gérer une file d'attente"
"Convertis cette boucle for en list comprehension"
"Crée des tests unitaires pour cette fonction"
```

### ResearchAgent 🔍
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

### SecurityAgent 🛡️
```
"Audite ce code pour les injections SQL"
"Quelles sont les bonnes pratiques de sécurité pour une API REST ?"
"Analyse les vulnérabilités potentielles de cette authentification"
```

### OptimizerAgent ⚡
```
"Optimise cette requête SQL pour de meilleures performances"
"Refactorise ce code pour réduire la complexité cyclomatique"
"Comment réduire la consommation mémoire de ce programme ?"
```

### DataScienceAgent 🧬
```
"Crée un modèle de classification pour prédire le churn"
"Propose une pipeline de preprocessing pour ce dataset"
"Quels algorithmes de ML sont adaptés pour ce type de données ?"
```

## 🎨 Personnalisation

L'interface suit automatiquement le thème de votre interface principale :
- **Couleurs** : Adaptées au mode sombre
- **Polices** : Consistantes avec le reste de l'app
- **Layout** : Responsive et moderne

---

**Prêt à utiliser les agents ?** Lancez l'interface et cliquez sur l'onglet 🤖 Agents ! 🚀
