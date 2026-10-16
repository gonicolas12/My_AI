# 🎨 Utilisation des Agents dans l'Interface Graphique

## Accès à l'onglet Agents

1. Lancez l'appli : `launch.bat` / `launch.sh` (option 1), `python launch_unified.py` ou
   `python main.py --mode gui`
2. Cliquez sur l'onglet **Agents** en haut de la fenêtre

## 📋 Interface Agents

### Vue d'ensemble

La page Agents se lit de haut en bas :

1. la **grille des agents** ;
2. la **zone de tâche** et ses boutons ;
3. le **canvas du workflow** ;
4. les **exécutions** : la liste des fils à gauche, le fil ouvert à droite ;
5. les **statistiques et ressources** ;
6. les **tâches planifiées**.

#### 1️⃣ **Grille des agents**
9 cartes représentant chaque agent spécialisé (+ agents personnalisés), chacune avec
son icône teintée de la couleur de l'agent :
- **CodeAgent** - Génération et debug de code
- **WebAgent** - Recherche Internet & Fact-Checking
- **AnalystAgent** - Analyse de données
- **CreativeAgent** - Contenu créatif
- **DebugAgent** - Debug et correction
- **PlannerAgent** - Planification
- **SecurityAgent** - Cybersécurité et audit
- **OptimizerAgent** - Optimisation et performance
- **DataScienceAgent** - Data science et ML

**Comment utiliser :**
- **Glisser-déposer** : glissez une carte sur le **canvas** ; le nœud apparaît à l'endroit du dépôt
- **Clic** (ou Entrée sur une carte) : ajoute l'agent au canvas, en cascade à côté du précédent
- Ajoutez **plusieurs agents**, ou le même plusieurs fois, pour composer un workflow
- Le survol d'une carte montre la description complète de l'expertise de l'agent

#### 2️⃣ **Zone de tâche**

**Zone de texte** — Décrivez votre tâche :
```
"Crée une API REST sécurisée pour gérer des utilisateurs"
"Analyse ce dataset et donne-moi les tendances"
"Audite ce code pour les vulnérabilités de sécurité"
```

- **Ctrl+Entrée** exécute la tâche
- **« + »** (Joindre) : PDF, DOCX, Excel / CSV, PowerPoint, Code, Image ; **Ctrl+V** colle une
  capture ; on peut aussi **déposer** des fichiers ou un dossier sur la zone (voir
  [Pièces jointes](#-pièces-jointes-aux-agents))
- **Micro** : dictée locale (faster-whisper), insérée dans la tâche

**Boutons :**
- **▶ Exécuter** (le seul bouton orange) : lance la tâche ; devient **■ Arrêter** pendant
  l'exécution (ou **Échap**)
- **Créer un agent** : ouvre le dialogue de création d'agents personnalisés
- **Débat** : ouvre le dialogue d'un débat entre deux agents (voir [section dédiée](#-mode-débat))
- **Vider** : vide le workflow et le canvas

> 🔔 **Notification desktop** : à la fin d'une exécution de plus de 8 s, si la fenêtre n'a
> pas le focus, une notification **système native** (100% locale) vous prévient — débats
> compris.

#### 3️⃣ **Canvas de Workflow Visuel (style n8n)**

Le canvas (React Flow) est un espace interactif de type éditeur de flux :

| Fonctionnalité | Description |
|---|---|
| **Nœuds** | Carte de l'agent (icône, nom, liseré de sa couleur), point de statut, ports d'entrée et de sortie |
| **Liens** | Courbes de Bézier avec flèche, de la couleur du nœud source ; pointillés animés vers un agent en cours |
| **Zoom** | Molette (0.3x à 3x), boutons **Zoom avant** / **Zoom arrière** / **Réinitialiser la vue** |
| **Déplacement** | Clic milieu ou clic droit + glisser |
| **Grille** | Points de repère et aimantation des nœuds (25 px), **Afficher / Masquer la grille** |
| **Minimap** | Vue miniature du graphe entier en bas à droite |
| **Sélection** | Clic, Maj+clic multi-sélection, rectangle de sélection par glisser dans le vide |
| **Suppression** | Touche Suppr (ou Retour arrière) sur la sélection ; clic droit sur un lien |
| **Liens refusés** | Lien d'un nœud vers lui-même, doublon, et tout cycle (A→B→C→A compris) |
| **Exécution DAG** | Tri topologique automatique — nœuds indépendants lancés ensemble |
| **Enregistrer** | Enregistre la structure du workflow (nœuds + liens) dans un `.json` |
| **Charger** | Restaure un workflow enregistré (ou un workflow de l'interface mobile) |
| **Exporter** | Écrit un fichier Markdown : la tâche, la liste des agents (nom, type, statut), puis la réponse de chacun à la dernière exécution |

Les fichiers `.json` gardent le format de l'ancien canvas
(`{"nodes": {...}, "connections": [...], "zoom": …, "pan_x": …, "pan_y": …}`) : les workflows
enregistrés avant la fenêtre web se rechargent tels quels. Enregistrer, Charger et Exporter
ouvrent les dialogues de fichiers du système.

**Statuts des nœuds pendant l'exécution :**
- ⚪ **En attente** (gris) — pas encore exécuté
- 🟡 **En cours** (jaune) — en train de traiter la tâche
- 🟢 **Terminé** (vert) — terminé avec succès
- 🔴 **Erreur** (rouge) — erreur

Le canvas survit au passage par l'onglet Chat, pas au redémarrage de l'appli : enregistrez
vos workflows.

#### 4️⃣ **Exécutions (fils)**

Chaque exécution — agent seul, workflow ou débat — devient un **fil** : la liste à gauche,
le fil ouvert à droite, comme dans l'app Codex.

- **Statut en direct** dans la liste : en attente, en cours, terminé, terminé en partie
  (des agents ont échoué), erreur, interrompu
- **Une section par agent**, remplie au fil de l'écriture (Markdown, code coloré, tableaux,
  formules), avec sa durée et sa vitesse (tokens/s) ; **Copier la sortie**
- **En parallèle**, Ollama ne sert qu'un agent à la fois : celui qui attend affiche
  « Attend son tour » et écrira ensuite
- **Diff** : quand un agent modifie un code fourni (fichier joint ou bloc de la tâche), sa
  sortie s'ouvre en **Diff** (lignes ajoutées et retirées), **Sortie** montrant la réponse entière
- **Rouvrables** : les 50 derniers fils sont gardés d'un lancement à l'autre
  (`data/agent_runs.json`) ; **Effacer l'historique** les supprime
- Les exécutions lancées **du téléphone** (« Lancé du téléphone ») et les **tâches planifiées**
  (« Tâche planifiée », avec leur **Rapport**) deviennent aussi des fils

#### 5️⃣ **Statistiques et ressources**

- **Tâches exécutées**, **Agents actifs**, **Taux de succès** : calculés sur les fils gardés,
  mis à jour à la fin de chaque fil, remis à zéro par « Effacer l'historique »

**Consommation de ressources (Ollama)** — 6 lignes de monitoring en temps réel :

| Métrique | Description | Barre |
|---|---|---|
| **CPU** | Utilisation CPU par Ollama et son `llama-server` | Vert → Orange → Rouge |
| **RAM** | Mémoire utilisée par Ollama (en Mo) | Vert → Orange → Rouge |
| **GPU** | Utilisation GPU (NVIDIA, AMD ou WMI) | Vert → Orange → Rouge |
| **VRAM** | Mémoire GPU utilisée (en Mo) | Vert → Orange → Rouge |
| **Inférence** | Durée de génération du dernier agent | Barre dynamique |
| **Tokens/s** | Vitesse d'écriture du dernier agent (statistiques de fin de flux d'Ollama) | Bleue, sans seuil |

Chaque ligne comporte :
- un **libellé** ;
- une **barre de progression colorée** (vert sous 50 %, orange sous 80 %, rouge au-delà) ;
- la **valeur numérique** ;
- un **mini-graphique** des 60 dernières mesures (une toutes les 3 s, fenêtre ouverte).

> **Note :** Le monitoring GPU est **multi-vendor** et détecte automatiquement votre carte graphique :
>
> | GPU | Package à installer | Commande |
> |---|---|---|
> | **NVIDIA** | `pynvml` + `GPUtil` | `pip install pynvml GPUtil` |
> | **AMD** | `pyamdgpuinfo` | `pip install pyamdgpuinfo` |
> | **AMD (Linux)** | `rocm-smi` (CLI) | Inclus avec les drivers ROCm |
> | **Tout GPU (Windows)** | `wmi` | `pip install wmi` (infos basiques) |
>
> **Ordre de détection :** NVIDIA pynvml → NVIDIA GPUtil → AMD pyamdgpuinfo → AMD rocm-smi → Windows WMI.
> Sans aucun de ces packages, GPU et VRAM ne sont pas mesurés.

#### 6️⃣ **Tâches Planifiées (Scheduler proactif)**

En bas de la page, la vue **Tâches planifiées** transforme l'assistant réactif en assistant
**proactif** : exécuter un agent, un workflow ou un débat **automatiquement et de façon
récurrente** (type cron).

- **Nouvelle tâche** : nom · **source** (*Agent seul* / *Workflow du canvas* courant, figé dans
  la tâche / *Débat*) · tâche ou sujet · **planning** (*Quotidien* `HH:MM` / *Hebdomadaire* /
  *Intervalle* / *Cron*) · option *Rattraper au prochain démarrage si manquée*.
- Chaque tâche affiche son **planning**, sa **prochaine exécution** et son **dernier résultat**
  (réussie, partielle, interrompue, différée, en erreur), avec son fil et son rapport. Boutons :
  **activer/désactiver**, **▶ Exécuter maintenant**, **Modifier**, **Supprimer**.
- **Exécuter même l'appli fermée** (Windows) : enregistre une tâche du Planificateur de tâches
  Windows qui lance les tâches dues même quand l'application est fermée (session ouverte).
- À la fin d'une exécution : **notification** du système (sinon un toast dans la fenêtre), fil à
  son nom dans les exécutions, et rapport `.md` dans `outputs/scheduled/`.

> Détails complets (plannings, rattrapage, exécution en arrière-plan, notifications) :
> [docs/SCHEDULER.md](SCHEDULER.md).

## ⏹️ Bouton Arrêter

Pendant une exécution lancée de la page, le bouton **▶ Exécuter** devient **■ Arrêter** :
- Cliquez dessus, ou appuyez sur **Échap**, pour **interrompre** l'exécution
- Dans un workflow multi-agents, **toutes les étapes restantes sont annulées**
- Le fil se termine sur « ⛔ Génération interrompue »

Pendant une exécution lancée du **téléphone** ou par une **tâche planifiée**, **Exécuter**
attend (son infobulle dit pourquoi) et Échap ne l'arrête pas : le bouton **Arrêter** de son
fil, oui.

## 🎯 Scénarios d'Usage

### Scénario 1 : Agent unique
1. **Cliquer** sur CodeAgent (il rejoint le canvas)
2. Écrire : "Crée une calculatrice simple en Python"
3. Cliquer **▶ Exécuter**
4. Résultat : un fil avec le code complet et ses commentaires

### Scénario 2 : Workflow séquentiel (Développement)
1. **Ajouter** PlannerAgent, CodeAgent et DebugAgent au canvas
2. **Relier** PlannerAgent → CodeAgent → DebugAgent (port de sortie → port d'entrée)
3. Écrire : "Une API REST pour gérer une bibliothèque de livres"
4. Cliquer **▶ Exécuter**
5. Voir les 3 agents travailler en séquence, chacun enrichissant le résultat du précédent

### Scénario 3 : Workflow en DAG
1. **Glisser** PlannerAgent, CodeAgent et SecurityAgent sur le canvas
2. **Relier** PlannerAgent → CodeAgent et PlannerAgent → SecurityAgent
3. CodeAgent et SecurityAgent sont au même niveau → étape **parallèle**
4. Écrire : "Développer une API REST sécurisée"
5. Cliquer **▶ Exécuter**
6. PlannerAgent s'exécute d'abord (nœud jaune → vert), puis CodeAgent et SecurityAgent ; Ollama
   n'en servant qu'un à la fois, le second « attend son tour »

### Scénario 4 : Audit de sécurité
1. Relier SecurityAgent → CodeAgent
2. Joindre votre code (ou le coller) et écrire : "Audite et corrige les failles"
3. SecurityAgent identifie les vulnérabilités, CodeAgent les corrige : sa sortie s'ouvre en **Diff**

### Scénario 5 : Data Science
1. Relier DataScienceAgent → AnalystAgent
2. Écrire : "Analyse ce dataset et propose un modèle prédictif"

### Scénario 6 : Optimisation de code
1. Ajouter OptimizerAgent
2. Joindre votre code et écrire : "Optimise les performances"
3. Résultat : le code revu, en Diff, et les explications dans **Sortie**

### Scénario 7 : Interruption d'un workflow
1. Lancer un workflow multi-agents
2. Pendant l'exécution, cliquer sur **■ Arrêter** (ou Échap)
3. L'exécution s'arrête ; le fil le signale
4. Le bouton redevient **▶ Exécuter**

### Scénario 8 : Mode Débat entre deux agents
1. Cliquer sur **Débat**
2. Choisir l'**Agent A — Proposant** (ex : SecurityAgent)
3. Choisir l'**Agent B — Opposant** (ex : OptimizerAgent)
4. Saisir le **sujet** : *"Faut-il sacrifier la performance pour renforcer la sécurité ?"*
5. Régler le **nombre de tours** (1 à 10)
6. Cliquer **Démarrer le débat**
7. Le débat devient un fil « Débat · SecurityAgent vs OptimizerAgent », un tour par section
8. **■ Arrêter** (ou le bouton de son fil) interrompt le débat

## 🎭 Mode Débat

### Ouverture

Le bouton **Débat** de la zone de tâche ouvre le dialogue « Mode Débat entre deux agents ».

### Champs de configuration

| Champ | Détail |
|---|---|
| **Agent A — Proposant** | Liste de tous les agents disponibles (par défaut + personnalisés). Défend la position |
| **Agent B — Opposant** | Liste de tous les agents disponibles. Doit être différent de l'Agent A — contre-argumente à chaque tour |
| **Sujet du débat** | Texte injecté dans les prompts des deux agents |
| **Nombre de tours** | De 1 à 10 (3 par défaut). Un tour = une prise de parole de chaque agent (donc 2 réponses) |
| **Démarrer le débat** | Lance le débat dans un fil, avec streaming |
| **Annuler** | Ferme le dialogue sans rien lancer |

### Déroulement

1. **Tour 1** — l'Agent A (proposant) présente son argument initial sur le sujet
2. **Tour 1 (suite)** — l'Agent B (opposant) répond et défend la position contraire
3. **Tour 2** — l'Agent A répond aux contre-arguments et renforce sa position
4. *…et ainsi de suite jusqu'au nombre de tours configuré*

Chaque prise de parole est une **section** du fil (liseré de la couleur de l'agent), écrite
en direct.

### Statuts du débat

- **En cours** — pendant l'exécution
- **✅ Débat terminé (N tours)** — succès
- **⛔ Débat interrompu** — arrêté
- **❌ …** (le message d'erreur) — agent invalide ou erreur d'inférence

### Contraintes

- **Agents différents** : si A == B, « ❌ Choisis deux agents différents »
- **Sujet requis** : « ❌ Sujet requis »
- **Pas de cumul** : impossible de lancer un débat pendant une autre exécution
  (« ⏳ Une tâche est déjà en cours »)

### Historique

Chaque débat reste dans la liste des fils (les 50 derniers sont gardés) : on le rouvre pour
relire tous ses tours.

## 💡 Conseils & Astuces

### Pour de meilleurs résultats :
- **Soyez spécifique** : Plus votre description est précise, meilleur sera le résultat
- **Incluez le contexte** : Mentionnez le langage, le framework, les contraintes
- **Créez des workflows** : Pour des tâches complexes, combinez plusieurs agents sur le canvas
- **Lisez les résultats** : Les agents fournissent souvent des explications utiles

### Glisser-déposer :
- Glissez depuis n'importe quelle partie de la carte d'un agent, ou cliquez sur la carte
- Sur le canvas, le nœud apparaît à l'endroit du dépôt
- Ajoutez le même agent plusieurs fois si nécessaire

### Canvas Visuel :
- **Relier** : glisser du port de sortie (droite) vers le port d'entrée (gauche)
- **Zoom** : molette, ou boutons Zoom avant / Zoom arrière
- **Naviguer** : clic milieu ou clic droit + glisser
- **Grille** : bouton Afficher / Masquer la grille
- **Minimap** : vue miniature en bas à droite
- **Multi-sélection** : Maj+clic ou rectangle de sélection dans le vide
- **Supprimer** : touche Suppr sur la sélection, ou clic droit sur un lien

### Optimisation :
- Vous pouvez enchaîner plusieurs tâches avec le même workflow
- Les statistiques vous permettent de suivre votre utilisation
- Utilisez **Vider** pour recommencer un workflow depuis zéro

### Dépannage :
- **Aucun résultat** : vérifiez qu'Ollama est lancé (`ollama serve`)
- **Erreur d'agent** : au moins un agent doit être sur le canvas
- **Timeout** : les tâches très complexes peuvent prendre du temps
- **Workflow bloqué** : utilisez **■ Arrêter** (ou Échap)

## 🎨 Création d'Agents Personnalisés

### Bouton « Créer un agent »

Le bouton **Créer un agent** de la zone de tâche permet de créer vos propres agents spécialisés.

### Dialogue de création

1. **Cliquez sur « Créer un agent »**
2. Le dialogue « Créer un agent personnalisé » s'ouvre avec :
   - **Nom de l'agent** : nom court (ex: "TranslatorAgent")
   - **Rôle / Description** : description détaillée de l'expertise
   - **Créer** : lance la génération
   - **Annuler** : ferme le dialogue

3. **Remplissez les champs** :
   ```
   Nom : TranslatorAgent
   Rôle : Expert en traduction multilingue avec adaptation culturelle et nuances linguistiques
   ```

4. **Cliquez sur « Créer »** :
   - le dialogue attend la réponse du modèle local, qui génère :
     - le **system prompt** optimisé
     - la **température** idéale (0.2-0.8)
     - une **description courte** (3-4 mots)
   - **votre agent apparaît** dans la grille après les 9 agents par défaut
   - une erreur (Ollama injoignable…) s'affiche dans le dialogue, qui reste ouvert

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

- **Icône** : un robot, teinté de la couleur de l'agent
- **Nom** : votre nom d'agent
- **Description courte** : 3-4 mots générés automatiquement
- **Couleur** : couleur vive tirée au hasard
- **Boutons** sur la carte : **Modifier** et **Supprimer**

### Édition d'un Agent Personnalisé

1. Cliquez sur **Modifier** sur la carte de votre agent
2. Le **même dialogue** s'ouvre avec les champs pré-remplis
3. **Modifiez** le nom et/ou la description
4. **Cliquez sur « Sauvegarder »** :
   - si vous changez la **description** : le system prompt est **régénéré** par le modèle
   - si vous changez seulement le **nom** : modification **instantanée**

### Suppression d'un Agent Personnalisé

1. Cliquez sur **Supprimer** sur la carte
2. Un **dialogue** demande confirmation
3. **Confirmez** : l'agent disparaît de la grille, et ses nœuds du canvas avec lui ;
   il est retiré de `data/custom_agents.json`

### Utilisation dans les Workflows

Les agents personnalisés fonctionnent **exactement comme les agents par défaut** : glissez ou
cliquez leur carte, reliez-les à d'autres agents (par défaut ou personnalisés).

**Exemple de workflow** :
```
TranslatorAgent → CreativeAgent → CodeAgent
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

Ils sont **rechargés au démarrage** de l'application, et partagés avec la page Agents du
téléphone (Relay).

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

- **Ollama requis** : la génération demande le modèle local
- **Nom unique** : chaque agent doit avoir un nom différent
- **Pas de modification directe du prompt** : pour garantir la cohérence
- **Suppression définitive** : pas de récupération possible après suppression

## 🔄 Comparaison Chat vs Agents

| Aspect | Onglet Chat | Onglet Agents |
|--------|-------------|---------------|
| **Usage** | Conversation générale | Tâches spécifiques |
| **Mémoire** | Conversation continue | Par exécution (fils rouvrables) |
| **Spécialisation** | Généraliste | 9+ agents experts |
| **Workflows** | Non | Canvas visuel (séquentiel, parallèle, DAG) |
| **Exécution** | Un message à la fois (file d'attente) | Séquentielle, parallèle, DAG ou débat 2 agents |
| **Monitoring** | Non | CPU, RAM, GPU, VRAM, inférence, tokens/s |
| **Stop** | ■ ou Échap pendant la génération | ■ Arrêter ou Échap pendant l'exécution |
| **Idéal pour** | Questions, discussions | Projets, analyses, workflows complexes |

## 🚀 Exemples Rapides par Agent

### CodeAgent 💻
```
"Génère une classe Python pour gérer une file d'attente"
"Convertis cette boucle for en list comprehension"
"Crée des tests unitaires pour cette fonction"
```

### WebAgent 🔍
```
"Cherche les groupes de la Coupe du monde 2026"
"Quels sont les résultats des dernières élections législatives en France"
"Trouve des informations à jour sur l'intelligence artificielle"
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

## 📎 Pièces Jointes aux Agents

Vous pouvez attacher des fichiers aux tâches envoyées aux agents.

### Comment attacher un fichier

1. Cliquez sur **« + »** dans la zone de tâche, puis choisissez le type (PDF, DOCX, Excel / CSV,
   PowerPoint, Code, Image) ; ou **déposez** des fichiers sur la zone ; ou **collez** une image
   (Ctrl+V)
2. Les fichiers apparaissent en **puces** au-dessus du texte
3. Cliquez sur **✕** pour retirer un fichier
4. Un **dossier** déposé joint ses fichiers (sous-dossiers compris, sauf les cachés et
   `.git`, `node_modules`… ; 20 fichiers lisibles au plus)

### Formats supportés

| Format | Méthode de lecture |
|--------|-------------------|
| **PDF** | PDFProcessor (extraction texte + métadonnées, OCR des pages scannées) |
| **DOCX** | DOCXProcessor (paragraphes + tables) |
| **PPTX, POTX** | PPTXProcessor (titres, puces, tableaux, notes) |
| **XLSX, XLS, CSV** | ExcelProcessor (feuilles en tableau texte, 200 lignes max par feuille) |
| **TXT, MD, JSON** | Lecture directe (200 000 caractères max) |
| **Code** (.py, .js, .ts, .java...) | Lecture directe |
| **Images** | Décrites par le modèle de vision, chacune |

La lecture est commune à la page Agents et aux agents lancés depuis le mobile (`processors/attachments.py`).

### Comportement en workflow multi-agents

Dans un workflow séquentiel (A → B → C) avec des fichiers joints :
- **Agent A** reçoit : tâche + contenu des fichiers joints
- **Agent B** reçoit : résultat de A + tâche originale (avec fichiers)
- **Agent C** reçoit : résultat de B + tâche originale (avec fichiers)

**Tous les agents du workflow ont accès aux fichiers joints**, pas uniquement le premier.

### Notes importantes

- Le contenu des fichiers est **injecté dans le prompt** sous forme de blocs textuels formatés
- Les fichiers texte et de code sont tronqués à 200 000 caractères
- Les PDF scannés (pages sans couche texte) sont lus par OCR : environ 4 s par page au premier envoi, puis instantané grâce au cache
- Un document illisible (fichier corrompu, PDF dont aucun texte n'est reconnu) est signalé à l'agent par « [Erreur de lecture : …] », jamais injecté sous forme d'octets bruts
- Un code joint est gardé dans le fil : c'est lui que l'onglet **Diff** compare à la sortie

---

## 🔄 Statut Visuel des Agents sur le Canvas

Chaque nœud sur le canvas de workflow affiche un indicateur de statut en temps réel :

| Statut | Couleur | Signification |
|--------|---------|---------------|
| **En attente** | Gris `#6b7280` | L'agent n'a pas encore été exécuté |
| **En cours** | Jaune `#f59e0b` | L'agent est en train de traiter la tâche (ou attend son tour auprès d'Ollama) |
| **Terminé** | Vert `#10b981` | L'agent a terminé avec succès |
| **Erreur** | Rouge `#ef4444` | L'agent a rencontré une erreur |

Ce statut se met à jour dans **tous les cas** :
- Agent unique sur le canvas
- Workflow séquentiel multi-agents
- Workflow parallèle (DAG)
- Agents isolés (sans lien)

---

## 🎨 Personnalisation

Toutes les couleurs de l'interface viennent des jetons de `frontend/src/styles/tokens.css`
(couleurs des agents comprises) : changer la couleur d'accent ne demande de modifier que ce
fichier.

---

**Prêt à utiliser les agents ?** Lancez l'appli et cliquez sur l'onglet **Agents** ! 🚀
