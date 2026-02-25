# 📚 Guide d'Utilisation - My Personal AI v6.6.0

## 🚀 Démarrage Rapide

### Lancement de l'Application

**Interface Graphique (Recommandée):**
```bash
# Lancement direct GUI
python launch_unified.py

# OU via main.py
python main.py --mode gui
```

**Interface CLI:**
```bash
# Mode interactif
python main.py

# OU explicitement
python main.py --mode cli
```

**Requêtes Directes:**
```bash
# Chat direct
python main.py chat "Votre question ici"

# Analyser fichier
python main.py file analyze document.pdf

# Générer code
python main.py generate code "description"

# Statut système
python main.py status
```

---

## 💬 Utilisation Interface Graphique

### Vue d'Ensemble GUI Modern

L'interface graphique moderne (inspirée de Claude.ai) offre:

**Éléments Interface:**
- **Chat Area** : Zone de conversation avec scroll
- **Input Box** : Zone de saisie (supporte multilignes avec Shift+Enter)
- **Send Button** : Bouton d'envoi (ou Enter)
- **Image Button (🖼️)** : Charger une image pour analyse
- **Clear Chat Button** : Réinitialiser conversation
- **Drag & Drop Zone** : Glisser-déposer fichiers (PDF/DOCX/Excel/CSV/Images/Code)

**Fonctionnalités:**
- 🎨 **Thème sombre** moderne style Claude
- 💬 **Bulles messages** utilisateur (droite) et IA (gauche)
- 🕒 **Timestamps** sur chaque message
- 🎨 **Syntax highlighting** pour code (via Pygments)
- 📁 **Drag-and-drop** fichiers PDF/DOCX/Excel/CSV/Images/Code
- 🖼️ **Analyse d'images** avec modèles vision (llava, llama3.2-vision)
- 📋 **Copier-coller** images depuis presse-papiers (Ctrl+V)

### Utilisation Typique GUI

```bash
# 1. Lancer GUI
python launch_unified.py

# 2. Interface s'ouvre
#    - Zone chat en haut
#    - Zone saisie en bas
#    - Bouton Send et Clear

# 3. Interactions
# Type de message et Enter OU clic Send
Vous: "Bonjour, comment ça va?"
IA: "Salut ! Je vais bien, merci. Comment puis-je t'aider ?"

# 4. Glisser-déposer fichier
# Drag PDF/DOCX/Excel/CSV dans fenêtre
IA: "Fichier 'rapport.pdf' chargé avec succès. 15 pages traitées."

# 5. Questions sur document
Vous: "Résume ce document"
IA: [Résumé basé sur rapport.pdf]

# 6. Effacer conversation
# Clic button "Clear Chat"
# Conversation réinitialisée
```

### 🖼️ Analyse d'Images

L'IA peut analyser des images avec les modèles vision Ollama:

**Méthodes de chargement:**
```bash
# 1. Bouton Image (🖼️)
# Clic sur bouton → Sélectionner PNG/JPG/JPEG/GIF/BMP
# Image encodée et prête pour analyse

# 2. Copier-Coller (Ctrl+V)
# Prendre une capture d'écran (Win+Shift+S)
# Dans le chat : Ctrl+V
# Image collée depuis presse-papiers

# 3. Glisser-Déposer
# Drag une image dans la fenêtre
# Image chargée automatiquement
```

**Questions exemple:**
```
Vous: [Charge image.png]
Vous: "Décris cette image en détail"
IA: "Je vois une capture d'écran montant..."

Vous: "Que vois-tu sur cette image ?"
Vous: "Explique-moi ce diagramme"
Vous: "Quel texte est visible ?"
```

> **Note:** Nécessite un modèle vision installé (`ollama pull llava`). L'image est automatiquement redimensionnée à 1024px max.

### Commandes Spéciales GUI

Dans la zone de saisie, vous pouvez taper:

```
aide       # Afficher commandes disponibles
help       # (English version)

statut     # Afficher état système
status     # (English version)

quitter    # Fermer application
exit       # (Alternative)
```

---

### 🧠 Mode Thinking — Raisonnement en Deux Passes

Pour les requêtes complexes, l'IA active automatiquement un **mode de raisonnement préalable** avant de générer la réponse finale.

#### Déclenchement automatique

Le mode thinking s'active si la requête remplit l'un de ces critères :
- **Longueur > 150 caractères**
- **Mots-clés analytiques** : `explique`, `analyse`, `compare`, `pourquoi`, `comment fonctionne`, `démontre`, `résous`, `débogage`, `optimise`, `implémente`, `architecture`, `step by step`, etc.
- **Requête > 60 caractères** avec au moins un mot-clé analytique
- **Plusieurs points d'interrogation** (≥ 2)
- **Blocs de code** dans la requête

> Le mode thinking ne s'active **pas** pour les questions conversationnelles simples (`bonjour`, `merci`, etc.) ni pour les requêtes avec image jointe.

#### Widget de raisonnement

Quand le thinking est actif, un widget apparaît dans le chat **au-dessus de la réponse** :

```
┌─────────────────────────────────────────────────┐
│ ▼  Raisonnement..                               │
│                                                 │
│  Voyons cette question sous différents angles.  │
│  D'abord, le concept principal est...           │
│  Ensuite, il faut considérer...                 │
│  Les points clés à retenir sont...              │
└─────────────────────────────────────────────────┘
```

- **Titre animé** : `Raisonnement.` → `Raisonnement..` → `Raisonnement...` (cycle toutes les 400 ms)
- **Streaming temps réel** : les tokens de raisonnement s'affichent au fur et à mesure
- **Bouton ▼/▶** : cliquer pour replier/déplier le contenu du raisonnement
- **État final** : `Raisonnement ✓` quand la réflexion est terminée, puis la réponse arrive

#### Exemple d'utilisation

```
Vous: "Explique-moi comment fonctionne le machine learning étape par étape"

→ Widget "Raisonnement." apparaît (animé)
→ L'IA réfléchit : concepts clés, angles d'approche, exemples pertinents...
→ Widget passe à "Raisonnement ✓"
→ Réponse finale complète et structurée s'affiche
```

#### Interruption

Cliquer sur le bouton **STOP** pendant la passe de raisonnement arrête immédiatement le thinking et le streaming.

---

## 🖥️ Utilisation Interface CLI

### Lancement CLI

```bash
python main.py
# OU
python main.py --mode cli
```

### Commandes CLI Disponibles

#### Requêtes Normales
```bash
# Questions générales
Vous> Bonjour
IA> Salut ! Comment puis-je t'aider ?

Vous> Comment créer une liste en Python?
IA> Pour créer une liste en Python, utilisez des crochets: my_list = []

Vous> Explique les boucles for
IA> [Explication détaillée avec exemples]
```

#### Commandes Spéciales

**aide / help** - Afficher toutes les commandes
```bash
Vous> aide

Commandes disponibles:
- aide / help : Afficher cette aide
- quitter / exit : Quitter l'application
- statut / status : Afficher l'état du système
- historique / history : Voir l'historique des conversations
- fichier <path> : Traiter un fichier
- generer <type> <description> : Générer du contenu
```

**statut / status** - État système
```bash
Vous> statut

État My Personal AI v6.6.0:
- Modèle: CustomAI avec 1M tokens
- Mémoire: 1,234,567 tokens utilisés / 1,048,576 max
- Documents: 3 fichiers en mémoire
- Conversations: 45 échanges dans l'historique
- Cache: Actif (75% hit rate)
- Système: OK
```

**historique / history** - Voir conversations
```bash
Vous> historique

Historique (10 derniers échanges):
1. Vous: "Bonjour"
   IA: "Salut ! Comment puis-je t'aider ?"
2. Vous: "Résume le PDF"
   IA: "Voici le résumé: ..."
...
```

**fichier** - Traiter fichier
```bash
Vous> fichier rapport.pdf
IA> Traitement de rapport.pdf en cours...
IA> Fichier traité avec succès. 25 pages analysées, 12,345 tokens ajoutés.
IA> Vous pouvez maintenant me poser des questions sur ce document.

Vous> Que dit ce rapport sur les performances?
IA> [Extraction des informations pertinentes du PDF]
```

**generer** - Générer contenu
```bash
Vous> generer code fonction fibonacci récursive Python
IA> Voici une fonction Fibonacci récursive en Python:

def fibonacci(n):
    """Calcule le n-ième nombre de Fibonacci récursivement"""
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)

# Exemple d'utilisation:
print(fibonacci(10))  # Output: 55
```

**quitter / exit** - Fermer application
```bash
Vous> quitter
IA> Au revoir ! À bientôt.
# Application se ferme
```

---

## 🦙 Modes de Fonctionnement

L'application fonctionne selon deux modes, détectés automatiquement au démarrage :

### Mode Ollama (Prioritaire)

Si Ollama est installé et lancé, toutes vos questions sont traitées par le LLM local :

```
✅ [LocalLLM] Ollama détecté et actif sur http://localhost:11434 (Modèle: my_ai)

Vous> Comment fonctionne une boucle for en Python ?
IA> [Réponse générée par llama3.1:8b - qualité LLM complète]
```

**Avantages :**
- Réponses naturelles et contextuelles
- Compréhension sémantique avancée
- Conversations fluides
- 100% confidentiel (rien ne quitte votre PC)

### Mode Fallback (Sans Ollama)

Si Ollama n'est pas disponible, l'IA utilise le système de patterns :

```
⚠️ [LocalLLM] Ollama non détecté. Le mode génératif avancé sera désactivé.

Vous> Bonjour
IA> Salut ! Comment puis-je t'aider ? [Pattern de salutation]
```

**Fonctionnalités toujours disponibles :**
- Reconnaissance d'intentions (salutations, code, documents)
- FAQ thématique
- Traitement de documents
- Recherche internet
- Génération de code (via templates)

---

## 🎯 Reconnaissance d'Intentions

L'IA détecte automatiquement le type de requête et adapte sa réponse:

### 1. Salutations

**Patterns détectés:** bonjour, salut, bjr, slt, hello, hi, coucou, hey

```bash
Vous> slt
IA> Salut ! Comment puis-je t'aider aujourd'hui ?

Vous> bonjour
IA> Bonjour ! Que puis-je faire pour vous ?
```

### 2. Questions de Programmation

**Keywords:** fonction, classe, code, python, javascript, html, css, algorithme

```bash
Vous> Comment créer une fonction Python?
IA> Pour créer une fonction en Python:

def ma_fonction(param1, param2):
    # Code de la fonction
    return resultat

Exemple concret:
def additionner(a, b):
    return a + b
```

### 3. Analyse de Documents

**Patterns:** résume, analyse, que dit, extrait, explique le document/PDF/fichier

```bash
# Après avoir chargé un PDF
Vous> résume ce document
IA> Résumé du document "technical_spec.pdf":
Le document présente...
[Résumé détaillé basé sur contenu réel]

Vous> Que dit le PDF sur la sécurité?
IA> Concernant la sécurité, le document mentionne:
- Point 1: [extraction]
- Point 2: [extraction]
```

### 4. Génération de Code

**Triggers:** génère, crée, écris du code, fais-moi

```bash
Vous> Génère une classe Python pour gérer une base de données
IA> Voici une classe pour gérer une base de données SQLite:

import sqlite3

class DatabaseManager:
    def __init__(self, db_name):
        self.conn = sqlite3.connect(db_name)
        self.cursor = self.conn.cursor()

    def execute(self, query, params=()):
        self.cursor.execute(query, params)
        self.conn.commit()

    def fetch(self, query, params=()):
        self.cursor.execute(query, params)
        return self.cursor.fetchall()

    def close(self):
        self.conn.close()

# Utilisation:
db = DatabaseManager('my_database.db')
```

### 5. Recherche Internet

**Triggers:** cherche sur internet, recherche web, google, trouve sur le web

```bash
Vous> cherche sur internet population de Paris
IA> 🌐 Recherche sur internet...

Résultat de la recherche:
La population de Paris est d'environ 2,2 millions d'habitants
(agglomération: 10,9 millions).

Sources:
- [URL1]
- [URL2]
```

---

## 📁 Traitement de Fichiers

### Types de Fichiers Supportés

| Extension | Processeur | Capacités |
|-----------|------------|-----------|
| .pdf | PDFProcessor | Texte, metadata, images, chunking |
| .docx | DOCXProcessor | Paragraphes, tables, formatage |
| .xlsx | ExcelProcessor | Feuilles multiples, cellules, formatage tableau |
| .xls | ExcelProcessor | Ancien format Excel (via xlrd) |
| .csv | ExcelProcessor | Données tabulaires, encodage automatique |
| .txt | FileManager | Texte brut |
| .py, .js, .html, .css | CodeProcessor | Code avec analyse syntaxique |
| .md | FileManager | Markdown |
| .json | FileManager | JSON structuré |

### Méthodes de Chargement

#### 1. Drag-and-Drop (GUI)
```bash
# Dans interface GUI:
# 1. Ouvrir explorateur fichiers
# 2. Sélectionner fichier (PDF, DOCX, Excel, CSV, code...)
# 3. Glisser dans fenêtre GUI
# 4. Attendre confirmation: "Fichier chargé"
```

#### 1b. Via le Menu Fichier (GUI)
```bash
# Page d'accueil ou page de conversation :
# Menu déroulant → choisir le type de fichier :
#   📄  PDF        → sélection .pdf
#   📝  DOCX       → sélection .docx
#   📊  Excel/CSV  → sélection .xlsx / .xls / .csv
#   💻  Code       → sélection fichier source
#   🖼️   Image      → sélection .png / .jpg
```

#### 2. Commande CLI
```bash
# Mode interactif
Vous> fichier path/to/document.pdf

# Mode direct
python main.py file analyze path/to/document.pdf
```

#### 3. Via Code Python
```python
from core.ai_engine import AIEngine

ai = AIEngine()

# Traiter fichier
result = ai.process_file("rapport.pdf")
print(result)  # {"success": True, "message": "...", "content": "..."}

# Poser question sur fichier
response = ai.process_query("Résume ce document")
print(response["message"])
```

### Workflow Traitement Document

```
1. Chargement fichier
   ↓
2. Détection type (extension)
   ↓
3. Processeur approprié
   ├─ .pdf         → PDFProcessor
   ├─ .docx        → DOCXProcessor
   ├─ .xlsx/.xls   → ExcelProcessor (openpyxl / xlrd)
   ├─ .csv         → ExcelProcessor (stdlib csv)
   └─ .py/.js/...  → CodeProcessor
   ↓
4. Extraction contenu
   ↓
5. Chunking (2048 tokens)
   ↓
6. Stockage ConversationMemory
   ↓
7. Ajout MillionTokenContextManager
   ↓
8. Confirmation utilisateur
   ↓
9. Questions possibles sur document
```

### Exemples Traitement

#### PDF Technique
```bash
Vous> fichier technical_documentation.pdf
IA> Traitement PDF en cours...
IA> ✅ Fichier traité: 50 pages, 45,678 tokens
IA> Vous pouvez maintenant poser des questions sur ce document.

Vous> Quelles sont les spécifications techniques?
IA> Selon le document, les spécifications techniques sont:
1. [Point 1 extrait]
2. [Point 2 extrait]
...

Vous> Comment implémenter la section 3.2?
IA> La section 3.2 décrit... [explication avec code si pertinent]
```

#### Excel / CSV
```bash
Vous> fichier rapport_ventes.xlsx
IA> Traitement Excel en cours...
IA> ✅ Fichier traité: 3 feuilles, 450 lignes

Vous> Quelles sont les ventes du mois de mars?
IA> Selon la feuille "Mars" du fichier rapport_ventes.xlsx:
- Total ventes: 128 450 €
- Meilleur produit: Produit A (34 200 €)
- Régions: Sud (42%), Nord (31%), Est (27%)

Vous> fichier export_clients.csv
IA> ✅ Fichier traité: 1 200 lignes, 8 colonnes

Vous> Compare les données de rapport_ventes.xlsx et export_clients.csv
IA> En croisant les deux fichiers:
[Analyse comparative basée sur les données réelles des deux fichiers]
```

#### Code Source
```bash
Vous> fichier src/main.py
IA> Analyse du code Python...
IA> ✅ Fichier analysé: 250 lignes, 3 classes, 15 fonctions

Vous> Explique la fonction process_data
IA> La fonction process_data (ligne 45) fait ceci:
[Explication détaillée avec extrait de code]

Vous> Comment optimiser cette fonction?
IA> Voici des suggestions d'optimisation:
1. Utiliser list comprehension au lieu de boucle for
2. [Autres suggestions avec code]
```

---

## 💾 Gestion Mémoire et Contexte

### ConversationMemory

**Stockage automatique:**
- Conversations (user + AI messages)
- Documents traités (nom + contenu)
- Code analysé
- Préférences utilisateur
- Cache contexte récent

**Persistance:**
- Format JSON
- Sauvegarde automatique
- Rechargement au démarrage

### MillionTokenContextManager (1M Tokens)

**Capacité:** 1,048,576 tokens maximum

**Workflow:**
```python
# Ajout document
context_mgr.add_document(
    content=large_text,
    document_name="spec.pdf"
)
# → Chunking automatique
# → Indexation
# → Stockage persistant

# Recherche
results = context_mgr.search_context(
    query="security requirements",
    top_k=5
)
# → Chunks pertinents retournés

# Statistiques
stats = context_mgr.get_statistics()
# {
#   "total_tokens": 456789,
#   "total_documents": 3,
#   "total_chunks": 223
# }
```

**Utilisation pratique:**
```bash
# Charger plusieurs documents
Vous> fichier doc1.pdf
IA> ✅ Document 1 chargé (50K tokens)

Vous> fichier doc2.pdf
IA> ✅ Document 2 chargé (75K tokens)

Vous> fichier doc3.docx
IA> ✅ Document 3 chargé (30K tokens)

# Total contexte: 155K tokens / 1M disponible

# Questions multi-documents
Vous> Compare les approches dans doc1 et doc2
IA> [Analyse comparative en utilisant les deux documents]

Vous> Synthèse des 3 documents
IA> [Synthèse complète avec références croisées]
```

---

## 🔍 Recherche Internet

### Activation

**Trigger:** "cherche sur internet", "recherche web", "google"

```bash
Vous> cherche sur internet capitale du Japon
IA> 🌐 Recherche sur internet...

Résultat:
La capitale du Japon est Tokyo.

Informations complémentaires:
- Population: ~14 millions (agglomération: ~37 millions)
- Fondation: 1603
- Anciennement: Edo

Sources:
- [URL1]
- [URL2]
```

### Fonctionnalités Recherche

**Moteur:** DuckDuckGo API + Web Scraping

**Capacités:**
- Recherche top 8 résultats
- Extraction patterns:
  - Faits (taille, poids, population, dates)
  - Définitions
  - Prix et spécifications techniques
- BeautifulSoup scraping
- Cache 1h (évite requêtes répétées)

**Patterns reconnus:**
```python
# Taille/Poids
"Quelle est la taille de la Tour Eiffel?"
→ "324 mètres"

# Population
"Population de New York?"
→ "8,3 millions"

# Dates
"Quand a été construit le Taj Mahal?"
→ "1632-1653"

# Définitions
"Qu'est-ce que le machine learning?"
→ [Définition extraite]
```

---

## 💻 Génération de Code

### Sources Multi-Intégrées

**1. StackOverflow** (priorité 1)
- Solutions les plus votées
- Code vérifié par communauté
- Exemples pratiques

**2. GitHub** (priorité 2)
- Recherche par langage
- Code production
- Patterns réels

**3. Web Scraping** (priorité 3)
- Tutoriels en ligne
- Documentation

**4. Templates** (fallback)
- Templates intégrés si pas de résultats web

### Workflow Génération

```bash
Vous> Génère une fonction pour parser JSON en Python
IA> 🔍 Recherche de code...
IA> ✅ Solution trouvée (StackOverflow, 1,234 votes)

import json

def parse_json(json_string):
    """Parse une chaîne JSON et retourne un objet Python"""
    try:
        data = json.loads(json_string)
        return {"success": True, "data": data}
    except json.JSONDecodeError as e:
        return {"success": False, "error": str(e)}

# Utilisation:
json_str = '{"name": "John", "age": 30}'
result = parse_json(json_str)
print(result["data"])  # {'name': 'John', 'age': 30}

Source: StackOverflow #12345678
```

### Langages Supportés

```yaml
langages_supportes:
  - Python
  - JavaScript / TypeScript
  - HTML / CSS
  - Java
  - C / C++
  - Go
  - Rust
  - SQL
  - Bash / Shell
  - Et plus...
```

### Types de Génération

**Fonctions:**
```bash
Vous> Fonction pour calculer factorielle Python
IA> [Génère fonction avec docstring et exemples]
```

**Classes:**
```bash
Vous> Classe pour gérer utilisateurs
IA> [Génère classe complète avec méthodes]
```

**Scripts complets:**
```bash
Vous> Script pour scraper un site web
IA> [Génère script avec imports et gestion erreurs]
```

**Composants UI:**
```bash
Vous> Composant React pour formulaire de connexion
IA> [Génère composant JSX avec gestion état]
```

---

## 📊 Commandes Système

### Statut Système

```bash
python main.py status

# Output:
═══════════════════════════════════════════════
  MY PERSONAL AI - System Status v6.6.0
═══════════════════════════════════════════════

🤖 AI Model: CustomAIModel
📊 Version: 6.6.0
💾 Context Manager: MillionTokenContextManager

📈 Context Statistics:
   - Total Tokens: 456,789 / 1,048,576 (43.6%)
   - Documents: 3
   - Chunks: 223
   - Storage: 145 MB

💬 Conversation Memory:
   - Exchanges: 45
   - Stored Documents: 3
   - Cache Keywords: 127

🔧 Features Status:
   ✅ Internet Search: Active
   ✅ Code Generation: Active
   ✅ RLHF: Configured
   ✅ FAQ Model: Loaded (4 enrichment files)

⚙️  Performance:
   - Cache Hit Rate: 75%
   - Average Response Time: 850ms
   - Memory Usage: 1,245 MB

✅ System: Operational
═══════════════════════════════════════════════
```

### Informations Version

```bash
python main.py --version

My Personal AI v6.6.0
- Architecture: 100% Local
- Context: 1,048,576 tokens (1M)
- Interfaces: GUI (CustomTkinter), CLI
- Python: 3.10+
```

---

## 🎓 Exemples d'Utilisation Avancée

### Session Complète: Analyse Projet

```bash
# 1. Lancer IA
python launch_unified.py

# 2. Charger architecture
Vous> fichier docs/ARCHITECTURE.md
IA> ✅ Document chargé (12,345 tokens)

# 3. Charger code principal
Vous> fichier src/main.py
IA> ✅ Code analysé (5,678 tokens)

# 4. Charger tests
Vous> fichier tests/test_main.py
IA> ✅ Tests analysés (3,456 tokens)

# 5. Questions multi-fichiers
Vous> L'architecture documentée correspond-elle au code réel?
IA> En comparant ARCHITECTURE.md et main.py:
✅ Correspondances:
   - Structure modules conforme
   - Patterns documentés appliqués

⚠️  Différences détectées:
   - Section 3.2 de ARCHITECTURE.md non implémentée dans main.py
   - Fonction process_data() pas documentée

📝 Recommandations:
   1. Mettre à jour ARCHITECTURE.md section 3.2
   2. Ajouter documentation process_data()

Vous> Génère les tests manquants pour main.py
IA> Voici les tests unitaires manquants:
[Tests générés basés sur analyse du code]
```

### Session: Recherche et Documentation

```bash
# 1. Recherche concept
Vous> cherche sur internet design patterns python
IA> 🌐 Recherche...
[Résultats avec sources]

# 2. Génération code basé sur recherche
Vous> Implémente le pattern Singleton en Python
IA> Voici une implémentation Singleton:
[Code généré]

# 3. Questions approfondies
Vous> Quand utiliser ce pattern?
IA> Le pattern Singleton est recommandé quand:
1. [Cas d'usage 1]
2. [Cas d'usage 2]

Vous> Alternatives au Singleton?
IA> Alternatives au pattern Singleton:
- Dependency Injection
- Factory Pattern
[Explications et exemples]
```

### Session: RLHF Interactif

```bash
# 1. Poser question
Vous> Comment optimiser une requête SQL?
IA> [Réponse générée]

# 2. Noter réponse (si RLHF configuré)
Rating: 4/5

# 3. Feedback enregistré
IA> Merci pour votre feedback! (4/5)

# 4. Après plusieurs feedbacks, modèle s'améliore
# Réponses futures sur SQL seront plus précises
```

---

## ⚙️ Configuration Utilisateur

### Fichier config.yaml

```yaml
# config.yaml - Personnalisation utilisateur

ai:
  name: "Mon IA Personnelle"
  max_tokens: 4096
  temperature: 0.7
  conversation_history_limit: 10

ui:
  cli:
    prompt: "💬 Vous> "
    ai_prompt: "🤖 IA> "
  gui:
    theme: "dark"  # dark, light
    font_size: 11
    code_highlighting: true

features:
  enable_internet_search: true
  enable_code_generation: true
  enable_rlhf: false

context_manager:
  max_tokens: 1048576  # 1M
  chunk_size: 2048
  auto_cleanup: true

logging:
  level: "INFO"  # DEBUG, INFO, WARNING, ERROR
  log_file: "data/logs/app.log"
```

### Variables Environnement (.env)

```bash
# .env
GITHUB_TOKEN=your_github_token_here  # Pour code generation
DEBUG=false
LOG_LEVEL=INFO
```

---

## 🔧 Troubleshooting Utilisation

### Problème: IA ne répond pas

**Diagnostic:**
1. Vérifier statut: `python main.py status`
2. Vérifier logs: `data/logs/`
3. Tester requête simple: `python main.py chat "test"`

**Solutions:**
- Redémarrer application
- Vérifier mémoire disponible
- Réduire `max_tokens` dans config

### Problème: Fichier non traité

**Erreur:** "Impossible de traiter le fichier"

**Solutions:**
1. Vérifier extension supportée (.pdf, .docx, .txt, etc.)
2. Vérifier taille fichier (< 100MB par défaut)
3. Vérifier permissions lecture fichier
4. Essayer chemin absolu au lieu de relatif

### Problème: Recherche internet ne fonctionne pas

**Diagnostic:**
- Vérifier connexion internet
- Tester: `python main.py chat "cherche sur internet test"`

**Solutions:**
1. Vérifier config: `enable_internet_search: true`
2. Vérifier firewall/proxy
3. DuckDuckGo peut avoir rate limits (attendre quelques minutes)

### Problème: Mémoire pleine

**Erreur:** "Context manager at capacity"

**Solutions:**
```bash
# Via CLI
Vous> statut
# Voir utilisation contexte

# Clear chat (GUI) OU redémarrer
python launch_unified.py
```

**Configuration:**
```yaml
# Dans config.yaml, réduire:
context_manager:
  max_tokens: 524288  # 512K au lieu de 1M
  auto_cleanup: true  # Active cleanup automatique
```

---

## 📚 Ressources Supplémentaires

**Documentation:**
- `INSTALLATION.md` - Installation et setup
- `ARCHITECTURE.md` - Détails techniques
- `OPTIMIZATION.md` - Performance tuning
- `FAQ.md` - Questions fréquentes

**Exemples:**
- `examples/basic_usage.py` - Usage basique
- `examples/file_processing.py` - Traitement fichiers
- `examples/code_generation.py` - Génération code
- `examples/workflow_examples.py` - Workflows complets

**Tests:**
- `tests/test_imports.py` - Vérification modules
- `tests/test_real_1m_tokens.py` - Test contexte 1M
- `tests/demo_1m_tokens.py` - Démonstration interactive

---

## 🎯 Best Practices

### Pour Questions Efficaces

**✅ Faire:**
- Questions claires et spécifiques
- Fournir contexte si nécessaire
- Charger documents pertinents avant questions
- Utiliser commandes système (statut, aide)

**❌ Éviter:**
- Questions trop vagues sans contexte
- Demandes multiples dans une requête
- Oublier de charger fichiers avant d'y référer

### Pour Documents

**✅ Faire:**
- Charger documents au début de session
- Donner noms descriptifs aux fichiers
- Organiser documents par projet

**❌ Éviter:**
- Charger trop de documents inutiles
- Fichiers > 100MB sans nécessité
- Recharger même fichier plusieurs fois

### Pour Performance

**✅ Faire:**
- Clear chat régulièrement si mémoire limitée
- Utiliser CLI pour machines peu puissantes
- Activer cache pour requêtes répétées

**❌ Éviter:**
- Laisser tourner avec contexte plein 24/7
- Charger des centaines de fichiers
- Requêtes internet trop fréquentes (rate limits)

---

**Version:** 6.6.0
**Interfaces:** GUI (CustomTkinter), CLI
**Capacité Contexte:** 1,048,576 tokens (1M)
**Architecture:** 100% Locale
