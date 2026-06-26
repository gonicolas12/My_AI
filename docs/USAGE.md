# 📚 Guide d'Utilisation - My Personal AI v8.0.0

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
- **Mic Button (🎙)** : Saisie vocale toggle — clic pour démarrer, reclic pour transcrire au curseur
- **Speaker Button (🔊)** : Sous chaque réponse de l'IA — lecture vocale (clic = lire, reclic = stop)
- **Image Button (🖼️)** : Charger une image pour analyse
- **Clear Chat Button** : Réinitialiser conversation
- **Drag & Drop Zone** : Glisser-déposer fichiers (PDF/DOCX/Excel/CSV/Images/Code)

**Fonctionnalités:**
- 🎨 **Thème sombre** moderne style Claude
- 💬 **Bulles messages** utilisateur (droite) et IA (gauche)
- 🕒 **Timestamps** sur chaque message
- 🎨 **Syntax highlighting** pour code (via Pygments)
- 📁 **Drag-and-drop** fichiers PDF/DOCX/Excel/CSV/Images/Code
- 🖼️ **Analyse d'images** avec modèles vision (minicpm-v, llava, llama3.2-vision)
- 📋 **Copier-coller** images depuis presse-papiers (Ctrl+V)
- 🎙️ **Saisie vocale locale** (faster-whisper) — voir section *Voice Mode* plus bas
- 🔊 **Sortie vocale locale** (pyttsx3) — lecture des réponses, voix par langue, lecture auto
- ⚙️ **Panneau Réglages** — gestion des modèles Ollama et paramètres, sans éditer de fichiers
- 🔎 **Recherche globale** — recherche sémantique sur *toutes* vos conversations (sidebar → 🔎) ; un clic ouvre la conversation et surligne le passage — voir [CONVERSATION_SEARCH.md](CONVERSATION_SEARCH.md)
- 🧠 **Mémoire** — voir / éditer / supprimer ce que l'IA sait de vous : faits + entrées vectorielles (sidebar → 🧠) — voir [MEMORY.md](MEMORY.md)

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

### 🎨 Génération d'Images (texte → image)

Symétrie de l'analyse d'images : l'IA peut aussi **créer** des images à partir d'une description, 100% en local.

```
Vous: "génère moi une image de dragon rouge"
Vous: "dessine-moi un chat astronaute, style aquarelle"
Vous: "crée un logo minimaliste pour une startup tech"
Vous: "génère une illustration d'une forêt enchantée la nuit"
```

Ce qu'il se passe :
1. Une bulle **« 🎨 Génération de l'image en cours… »** s'affiche (avec % de progression). Le bouton **STOP** reste actif — un clic annule à la fois le message et la génération.
2. L'image générée s'affiche **dans la même bulle** (clic = ouverture en taille réelle) et est sauvegardée dans `outputs/`.
3. La génération entre dans le **contexte** : « de quoi on a parlé ? » → l'IA se souvient de l'image créée.

> **Premier lancement :** si aucun backend Stable Diffusion n'est détecté, My_AI **installe automatiquement ComfyUI portable** (Windows/NVIDIA) + un modèle par défaut — rien à configurer. Sur les autres systèmes, ou pour choisir un autre backend (AUTOMATIC1111/Forge), voir [IMAGE_GENERATION.md](IMAGE_GENERATION.md). Désactivable via `config.yaml` → `image_generation.auto_setup: false`.
>
> L'**analyse** d'image (« décris cette image ») reste gérée par la vision Ollama et n'est pas confondue avec la génération.

### 🎙️ Saisie Vocale (Voice Mode)

Un bouton micro (🎙) est présent en haut-droite de chaque zone de saisie :
- **Écran d'accueil** du chat (avant le premier message)
- **Mode conversation** du chat (pendant une discussion)
- **Onglet Agents** (zone "Décrivez la tâche...")

**Utilisation :**

```
1. Clic sur l'icône micro (🎙)
   → L'icône passe en rouge avec une pulsation = enregistrement en cours.

2. Parlez (sans limite de durée raisonnable).

3. Clic sur l'icône (●) à nouveau pour arrêter
   → L'icône devient ⏳ pendant la transcription (~1-3 s selon la durée).

4. Le texte transcrit s'insère automatiquement au curseur de la zone active.
```

**Caractéristiques :**

| Caractéristique | Valeur |
|---|---|
| **Moteur** | [faster-whisper](https://github.com/SYSTRAN/faster-whisper) — 100% local |
| **Modèle** | `small` (~150 Mo, INT8 quantizé pour CPU) |
| **Langues** | 99+ langues, **auto-détection** (français, anglais, espagnol, etc.) |
| **Capture audio** | `sounddevice` — 16 kHz mono |
| **VAD** | Voice Activity Detection intégré (ignore les silences) |
| **Latence 1er usage** | ~5 s (chargement modèle Whisper depuis le cache HuggingFace ou téléchargement initial) |
| **Latence suivantes** | Instantanée (modèle gardé en mémoire) |
| **Insertion** | Au curseur de la zone de saisie, avec espace auto si nécessaire |

**Astuces :**

- **Dictée de prompts longs** : alternez voix et clavier librement — la transcription respecte la position du curseur.
- **Multi-langues dans une même session** : Whisper détecte la langue à chaque prise. Vous pouvez dicter en français puis en anglais sans rien changer.
- **Confidentialité** : la voix n'est jamais transmise sur internet, tout se passe en local sur votre machine.
- **Si le bouton n'écrit rien** : vérifiez que vous avez bien parlé (durée min. 0,3 s) et que `faster-whisper` + `sounddevice` sont installés (`pip install -r requirements.txt`).

**Dépendances supplémentaires :**

```bash
pip install faster-whisper sounddevice
```

> Sur **Linux/macOS**, `sounddevice` requiert la librairie système `portaudio` (généralement déjà présente — sinon `apt install libportaudio2` ou `brew install portaudio`).

### 🔊 Sortie Vocale (lecture des réponses)

L'IA peut **lire ses réponses à voix haute** :

- **Bouton 🔊** sous chaque réponse (clic = lecture, reclic = stop ; icône ⏹ pendant la lecture)
- **Toggle « Lecture auto »** dans la sidebar : lit automatiquement chaque nouvelle réponse de l'IA

| Caractéristique | Valeur |
|---|---|
| **Moteur** | [pyttsx3](https://pyttsx3.readthedocs.io/) — moteur de synthèse de l'OS, 100% local |
| **Windows / macOS** | SAPI5 / NSSpeechSynthesizer — aucune installation supplémentaire |
| **Linux** | nécessite `espeak-ng` (`sudo apt install espeak-ng`) |
| **Voix** | choisie automatiquement selon la **langue détectée** de la réponse (langdetect) |
| **Nettoyage** | code, markdown, URLs et emojis retirés avant lecture (prose naturelle) |

> La voix ne quitte jamais la machine, et **aucun modèle n'est téléchargé** (contrairement au Whisper de la saisie vocale).

### ⚡ Slash commands & Bibliothèque de prompts

Des **prompts réutilisables façon Claude Code**. Tapez **`/`** en début de saisie pour ouvrir l'autocomplétion :

```
Vous> /code un jeu de morpion en Python
```

- Naviguez au clavier (↑/↓), validez (Entrée/Tab) ou cliquez ; la saisie devient `/commande `, puis vous tapez votre texte.
- À l'**envoi**, la commande courte est **expansée** en un prompt détaillé pour le modèle — la bulle de chat garde la commande courte.
- **Commandes par défaut** : `/code`, `/résume`, `/traduis`, `/explique`, `/corrige`, `/reformule`.
- **Gérez votre bibliothèque** : sidebar → **📚 Prompts** (créer/éditer/supprimer des templates, avec placeholder `{arguments}`).

> Disponible aussi sur **mobile** (Relay) et dans l'**extension VS Code**. Détails : [PROMPT_LIBRARY.md](PROMPT_LIBRARY.md).

### 📁 Contexte projet « @codebase »

Attachez un **dossier entier** à votre workspace pour que l'IA le garde en contexte sur **toutes** vos questions :

- **Sidebar → 📁 Dossiers du projet → Attacher un dossier** (ou menu **« + » → 📁 Dossier (codebase)**).
- L'indexation est **incrémentale** et **100% locale** (respecte `.gitignore`, exclut `node_modules`, `.git`, `.venv`…).
- Posez ensuite vos questions normalement : les passages pertinents sont injectés automatiquement (RAG), et les questions *sur* le dossier (chemin, liste de fichiers) reçoivent une réponse directe.
- **Réindexer** après modification (seuls les fichiers changés sont retraités) ou **Détacher** pour retirer le contexte.

> Dans VS Code, tapez **`@`** pour attacher fichiers/dossiers. Détails : [CODEBASE.md](CODEBASE.md).

### 🎹 Command palette (Ctrl+K) & raccourcis clavier

- **`Ctrl+K`** ouvre une palette de commandes avec recherche filtrante (nouveau chat, export, Relay, Réglages, Mémoire, Prompts, Aide…).
- **Raccourcis globaux** : `Ctrl+N` (nouveau chat), `Ctrl+L` (effacer), `Ctrl+S` (sauver), `Ctrl+B` (sidebar), `Ctrl+R` (Relay), `Ctrl+,` (Réglages), `F1` (Aide).

### ✏️ Éditer & regénérer un message

- Sous chaque **message envoyé**, le bouton **« Modifier »** permet de réécrire votre demande puis de **regénérer** la réponse.
- L'ancienne version est **conservée** : naviguez entre les variantes d'un même tour avec **‹ k/n ›**.
- Éditer un message en milieu de conversation **remplace l'aval** (branchement façon ChatGPT) — vous êtes prévenu avant.

### 🔗 Citations web cliquables

Après une **recherche internet**, les sources sont **numérotées** et l'IA place des marqueurs **`[n]`** dans sa réponse. Cliquez sur un `[n]` (dans le corps ou la liste des sources) pour **ouvrir l'URL d'origine** — sur desktop **et** mobile.

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

État My Personal AI v8.0.0:
- Modèle: CustomAI avec 10M tokens
- Mémoire: 1,234,567 tokens utilisés / 10,485,760 max
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
IA> [Réponse générée par qwen3.5:4b - qualité LLM complète]
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

### 6. Génération d'Images

**Triggers:** génère/dessine/crée une image, une illustration, un dessin, un logo, un visuel…

```bash
Vous> dessine-moi un dragon rouge
IA> 🎨 Génération de l'image en cours… 60%
    [image affichée dans la bulle + sauvegardée dans outputs/]
```

> Distincte de l'**analyse** d'image (« décris cette image ») et de la génération de **code**.

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

### VectorMemory (10M Tokens)

**Capacité:** 10,485,760 tokens maximum

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
  MY PERSONAL AI - System Status v8.0.0
═══════════════════════════════════════════════

🤖 AI Model: CustomAIModel
📊 Version: 8.0.0
💾 Context Manager: VectorMemory

📈 Context Statistics:
   - Total Tokens: 456,789 / 10,485,760 (4.4%)
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

My Personal AI v8.0.0
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
  max_tokens: 10485760  # 10M
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

## 🆕 Fonctionnalités v7.0.0

### 🌐 API REST Locale

My_AI expose une API HTTP sur `localhost:8000` pour piloter l'IA depuis n'importe quel outil.

```bash
# Activer l'API dans config.yaml
api:
  enabled: true
  host: "127.0.0.1"
  port: 8000
```

**Exemples d'utilisation :**
```bash
# Vérifier l'état du serveur
curl http://localhost:8000/api/health

# Envoyer un message
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Bonjour, quelle heure est-il ?"}'

# Lister les modèles disponibles
curl http://localhost:8000/api/models

# Changer de modèle
curl -X POST http://localhost:8000/api/models/switch \
  -H "Content-Type: application/json" \
  -d '{"model_name": "qwen3.5:9b"}'

# Récupérer l'historique
curl http://localhost:8000/api/conversations

# Voir les statistiques
curl http://localhost:8000/api/stats
```

### 📤 Export de Conversations

Exportez vos conversations en 3 formats :

```python
# Markdown
exporter.export(messages, output_format="markdown", filename="ma_conversation")

# HTML (thème sombre embarqué)
exporter.export(messages, output_format="html", filename="rapport")

# PDF (via ReportLab)
exporter.export(messages, output_format="pdf", filename="archive")
```

Les fichiers sont sauvegardés dans `outputs/exports/` avec horodatage automatique.

### 🧠 Base de Connaissances Structurée

L'IA extrait automatiquement des faits depuis vos conversations :

```
Vous : "Je préfère Python pour les scripts d'automatisation"
→ Fait extrait : [preference] préférence: Python pour les scripts d'automatisation (confiance: 70%)

Vous : "Mon manager s'appelle Thomas Dupont"
→ Fait extrait : [person] personne: Thomas Dupont (confiance: 70%)

Vous : "On a décidé de migrer vers PostgreSQL"
→ Fait extrait : [decision] décision: migrer vers PostgreSQL (confiance: 70%)
```

Les faits pertinents sont automatiquement injectés dans le contexte des futures conversations.

### 💼 Workspaces / Sessions

Organisez vos conversations en espaces de travail isolés :

- **Créer** un workspace : chaque workspace a son historique, documents et agents
- **Sauvegarder** automatiquement toutes les 5 minutes (configurable)
- **Charger** un workspace précédent pour reprendre le travail
- **Supprimer** les workspaces obsolètes

Les workspaces sont sauvegardés dans `data/workspaces/`.

### 📜 Historique des Commandes

Toutes vos requêtes sont enregistrées avec :
- **Recherche plein texte** dans les requêtes et réponses
- **Système de favoris** pour marquer les requêtes importantes
- **Statistiques** : total, répartition par agent, plage de dates
- **Nettoyage automatique** des anciennes entrées (les favoris sont préservés)

### 🌍 Détection Automatique de Langue

L'IA détecte automatiquement la langue de votre message et répond dans la même langue :
- 12 langues supportées : français, anglais, espagnol, allemand, italien, portugais, néerlandais, russe, chinois, japonais, coréen, arabe
- Cache LRU pour cohérence dans une conversation

### 📎 Pièces Jointes aux Agents

Dans l'onglet Agents, vous pouvez attacher des fichiers à vos tâches :
1. Cliquez sur le bouton **"+"** à côté de la zone de saisie
2. Sélectionnez un ou plusieurs fichiers (PDF, DOCX, TXT, code, CSV...)
3. Les fichiers apparaissent en preview dans la zone de saisie
4. Le contenu des fichiers est automatiquement injecté dans le prompt de l'agent
5. En workflow multi-agents, **tous les agents** reçoivent les fichiers joints

### 📡 My_AI Relay — Accès depuis le Mobile

My_AI Relay vous permet de discuter avec votre IA depuis votre smartphone (iOS ou Android), partout dans le monde, tant que l'application tourne sur votre PC.

#### Démarrage

1. Cliquez sur le bouton **📡 Relay** dans la **barre latérale gauche** de l'interface (visible en permanence, y compris sur l'écran d'accueil)
2. My_AI Relay démarre un serveur WebSocket local et ouvre **plusieurs tunnels en parallèle** (cloudflared, serveo, localhost.run) pour garantir que le téléphone puisse en atteindre au moins un — utile quand un opérateur mobile filtre certains domaines de tunnels publics
3. Un **QR code** s'affiche dans le panneau Relay — scannez-le avec votre téléphone. Le QR pointe vers une **page de routage statique** (hébergée sur GitHub Pages) qui ping tous les tunnels et redirige automatiquement vers le premier joignable
4. Si un **mot de passe** est configuré (section `relay.password` dans `config.yaml`), entrez-le sur la page de login mobile ; sinon l'accès est direct via le QR code
5. L'interface mobile s'ouvre sur deux onglets en haut — **💬 Chat** et **🤖 Agents** — qui reprennent la navigation du GUI PC. Le Chat est affiché par défaut ; touchez **Agents** pour accéder au système d'agents.

#### Onglet 💬 Chat

```
Téléphone                         PC (GUI desktop)
   │                                     │
   │─── Message via WebSocket ──────────>│
   │                                     │── Affiché dans le chat GUI
   │                                     │── L'IA répond (streaming)
   │<── Streaming + réponse finale ──────│
```

- Le GUI traite le message **exactement comme un message local** (avec streaming, thinking, agents, etc.)
- La réponse est streamée en direct au mobile (token par token), puis finalisée
- **Bouton Stop** : pendant la génération, le bouton d'envoi se transforme en bouton Stop (carré noir sur fond blanc). Le toucher interrompt la génération en cours — la demande remonte au GUI desktop qui appelle `interrupt_ai()` et renvoie la réponse partielle marquée « interrompue »
- **Liens cliquables** : la syntaxe Markdown `[titre](url)` ainsi que les URLs nues s'affichent en **bleu souligné cliquable** (ouverture dans un nouvel onglet), comme sur le GUI PC

#### Onglet 🤖 Agents

L'onglet Agents reprend **toutes les fonctionnalités de la page Agents du GUI desktop**, en version tactile. Tout s'exécute **côté PC** (orchestrateur d'agents + modèle Ollama local) et est streamé au mobile via le même tunnel chiffré — le contenu ne quitte jamais l'enveloppe E2EE.

- **Grille d'agents** — les 9 agents spécialisés (CodeAgent, WebAgent, AnalystAgent, CreativeAgent, DebugAgent, PlannerAgent, SecurityAgent, OptimizerAgent, DataScienceAgent) plus vos agents personnalisés. Touchez une carte pour l'ajouter au workflow.
- **Agents personnalisés** — bouton **➕ Créer Agent** : saisissez un nom + un rôle, le LLM local génère le *system prompt* (et la température). Modification ✏️ et suppression ✕ depuis la carte. Les agents sont stockés dans le **même `data/custom_agents.json` que le PC** → synchronisés dans les deux sens.
- **Workflow visuel (style n8n)** — canvas tactile : déplacez les nœuds au doigt, reliez le **port de sortie** (droite) d'un nœud au **port d'entrée** (gauche) d'un autre. La topologie détermine l'exécution : agent seul, **séquentiel** (chaîne), **parallèle** (nœuds indépendants) ou **DAG** (graphe). Sauvegarde 💾 / chargement 📂 / export 📤 du workflow.
- **Exécution** — décrivez la tâche, touchez **▶ Exécuter** : chaque agent apparaît comme une section dépliable qui se remplit en streaming, avec le statut du nœud (En attente / En cours / Terminé / Erreur). Le bouton **▶ Exécuter** devient **■ Stop** pendant l'exécution.
- **Mode Débat** — bouton **🎭 Mode Débat** : choisissez deux agents, un sujet et un nombre de tours ; les deux agents s'opposent tour par tour, en streaming.
- **Clear Workflow** — vide le canvas.
- **Pièces jointes** — bouton **+** de la barre d'action (voir ci-dessous) : le contenu des fichiers (ou la description de l'image) est injecté dans la tâche des agents.

> Les workflows/débats s'exécutent **un à la fois** (comme sur le PC). Le mode débat ne prend pas de pièces jointes, conformément au GUI desktop.

#### 📎 Pièces jointes depuis le mobile

Le bouton **+** permet de joindre une ou plusieurs pièces jointes — **à la fois sur l'onglet Chat** (à gauche du champ de saisie) **et sur l'onglet Agents** (au-dessus des boutons d'action). Les fichiers sont traités **exactement comme sur le PC** :

- **Images** (PNG, JPG, JPEG, GIF, BMP, WebP, TIFF) → envoyées au **modèle vision** (encodage base64, même pipeline que le drag & drop PC)
- **Documents** (PDF, DOCX, DOC, XLSX, XLS, CSV) → extrait de contenu ajouté au **contexte vectoriel** via les processeurs spécialisés
- **Code & texte** (PY, JS, HTML, CSS, JSON, XML, MD, TXT) → chargés dans le contexte de la session

Détails techniques :

- L'upload est **streamé** vers un répertoire temporaire (`{tempdir}/my_ai_relay_uploads/`) avec validation d'extension et plafond de **25 Mo** par fichier — l'upload chiffré (`POST /api/upload`) est partagé par le Chat et la page Agents
- **Sur l'onglet Agents**, le contenu des documents (et la description vision des images) est injecté en fin de tâche sous forme de sections `--- Fichier joint : … ---` avant le lancement du workflow (même logique que `execute_agent_task` du GUI desktop)
- Un fichier envoyé sans message (Chat) déclenche une requête par défaut (`"Décris cette image en détail."` ou `"Analyse ce fichier et résume-le."`)
- Image + documents peuvent être combinés dans un même message ; le premier fichier image est envoyé au modèle vision, les autres rejoignent le contexte
- Le contexte est garanti **prêt avant** le démarrage de l'inférence (le pipeline document est exécuté de façon synchrone avant l'appel au modèle)
- Endpoint côté serveur : `POST /api/upload?token=...` (multipart, retourne un `file_id`) ; le client WebSocket passe ensuite les `file_ids` dans le message de chat

#### Configuration (`config.yaml`)

```yaml
relay:
  auto_start: false       # true = Relay démarre automatiquement au lancement du GUI
  port: 8765              # Port du serveur local
  response_timeout: 500   # Délai max de réponse IA (secondes)
  password: ""            # Mot de passe (vide = token aléatoire, change à chaque redémarrage)
  tunnel: true            # false = réseau local uniquement (sans accès externe)
  tunnel_providers:       # Providers de tunnel à démarrer en parallèle
    - "cloudflared"       #   *.trycloudflare.com (auto-téléchargé)
    - "serveo"            #   *.serveo.net (via SSH, anonyme)
    - "localhost.run"     #   *.lhr.life (via SSH, anonyme)
  host: "0.0.0.0"         # Écoute sur toutes les interfaces réseau
```

> **Pourquoi plusieurs providers ?** Certains opérateurs mobiles (notamment en 5G) filtrent au niveau DNS les domaines des tunnels publics éphémères (`*.trycloudflare.com` est le plus filtré). En lançant 3 tunnels en parallèle sur 3 domaines différents, le téléphone peut toujours en joindre au moins un. Si vous savez que votre opérateur ne filtre rien, vous pouvez ne garder qu'un provider pour économiser un peu de bande passante : `tunnel_providers: ["cloudflared"]`.

#### Page de routage GitHub Pages (forkers du projet)

Le QR code encode une URL de la forme `https://gonicolas12.github.io/My_AI/router.html#d=<base64>` — la page de routage est servie depuis le **GitHub Pages du repo officiel**. Si vous **forkez** le projet et changez l'URL dans `relay/relay_server.py` (constante `_ROUTER_PAGE_URL`), pensez à activer GitHub Pages sur **votre fork** : Settings → Pages → Source = `Deploy from a branch` → Branch = `main` / `/docs` → Save. Les utilisateurs en aval n'ont rien à configurer : ils clonent et ça marche.

#### Accès réseau local (sans tunnel)

Si tous les providers sont indisponibles ou si `tunnel: false`, le Relay reste accessible sur votre réseau local :

```
http://<IP_de_votre_PC>:8765?token=<votre_token>
```

L'URL et le token sont affichés dans le panneau Relay de l'interface.

#### Sécurité

| Mécanisme | Détail |
|---|---|
| **Token de session** | Généré aléatoirement à chaque démarrage (si pas de mot de passe) |
| **Token permanent** | Dérivé du mot de passe via SHA-256 (reproductible entre sessions) |
| **Tunnel HTTPS** | Tous les providers (cloudflared/serveo/localhost.run) chiffrent en TLS sur le réseau, **mais terminent le TLS sur leur infrastructure** : sans la couche E2EE ci-dessous, le contenu serait lisible par eux |
| **Chiffrement bout-en-bout (E2EE)** | **AES-256-GCM applicatif** au-dessus du WebSocket et des uploads. La clé symétrique (32 octets) est générée localement à chaque démarrage du Relay et transmise au mobile **uniquement via le QR code** (canal optique). Ni le serveur de tunnel public (Cloudflare, serveo, localhost.run) ni GitHub Pages ne peuvent déchiffrer le contenu : ils ne voient que des octets opaques. |
| **Token + clé hors-serveur** | Le token et la clé E2EE voyagent dans le **fragment** de l'URL de routage (`#d=<base64>`) — le fragment n'est jamais émis sur le réseau, seul le navigateur le lit |
| **Strict, pas de downgrade** | Le serveur **rejette** toute connexion WS dont les messages ne sont pas chiffrés (close 4002). Pas de mode dégradé : on ne peut pas forcer du clair via une attaque MITM applicative. |
| **Aucune donnée cloud** | Les tunnels ne sont que des relais chiffrés — vos données restent sur votre PC, et le contenu transitant par les tunnels publics est illisible pour leurs opérateurs |

### 🧩 Extension VS Code — Mode agentique façon Claude Code

L'extension officielle **My_AI Relay** est publiée sur le **Marketplace VS Code**. Depuis sa **v1.1.0**, elle expose un **mode agentique** : l'extension s'identifie auprès du Relay comme client `vscode`, et le Relay aiguille la conversation vers une boucle de raisonnement dédiée qui appelle Ollama directement avec un prompt système outillé. Le LLM reste sur le PC hôte ; l'**exécution des outils est déléguée à l'extension**, qui les exécute dans le workspace VS Code de l'utilisateur, sandboxé par défaut. Le mobile et le GUI desktop continuent à utiliser le pipeline classique (avec MCP locaux complets) — strictement inchangés.

#### Démarrage en 3 étapes

1. **Sur le PC hôte** : démarrez le Relay (bouton 📡 dans la sidebar) → attendez qu'au moins un tunnel soit vert → cliquez sur **🧩 Copier pour l'extension VS Code** dans la popup.
2. **Dans VS Code** : installez l'extension `gonicolas12.my-ai` depuis le Marketplace (Extensions → recherche "My_AI Relay" → Install).
3. **Connexion** : ouvrez la vue *My_AI Relay* dans la sidebar → cliquez sur **Coller la chaîne de connexion…** → collez la chaîne de l'étape 1.

À la première connexion l'extension envoie un `client_hello { client_kind: "vscode" }` chiffré au Relay : la session bascule automatiquement en mode agentique.

#### Outils exposés au LLM

| Outil | Description | Approbation |
|---|---|---|
| `read_file` | Lecture d'un fichier du workspace (avec `offset` / `limit`) | Auto |
| `list_dir` / `glob` | Listing de dossier / recherche par pattern | Auto |
| `grep` | Recherche regex dans le contenu (ripgrep, fallback JS) | Auto |
| `get_active_editor` / `open_file` | Lire le fichier ouvert / ouvrir un fichier dans l'éditeur | Auto |
| `write_file` | Création / écrasement d'un fichier (crée les dossiers parents) | **Modal** |
| `edit_file` | Remplacement par correspondance exacte (`replace_all` optionnel) | **Modal** |
| `run_command` | Commande shell exécutée dans le workspace, sortie capturée | **Modal** |

Pour chaque opération destructive, le modal propose : *Autoriser une fois* / *Autoriser pour ce fichier (mémorisé pour la session)* / *Tout autoriser pour cet outil dans la session* / *Refuser*.

#### Cartes d'outils dans le chat

Chaque appel d'outil s'affiche comme une **carte pliable façon Claude Code**, avec une bordure gauche colorée selon l'état (orange = en cours · indigo = en attente d'approbation · vert = OK · rouge = erreur · gris = refusé). Cliquer déplie les arguments JSON et la sortie capturée (stdout/stderr pour les commandes shell, lignes modifiées pour les éditions).

#### Sandbox & isolation

- **Limité au workspace par défaut.** Tous les chemins sont résolus relativement au premier dossier workspace ouvert. Toute tentative de sortie déclenche un modal d'approbation par chemin (jamais auto-approuvable).
- **Aucun accès aux MCP du PC hôte** depuis l'extension. Le mode agentique est **isolé** du pipeline GUI/mobile : l'utilisateur côté VS Code ne voit que son workspace.
- **Mémoire de session.** Le contexte agentique est conservé pour toute la session WebSocket — *« édite le fichier que tu viens de lire »* fonctionne. Une reconnexion redémarre une session vierge.

#### Exemples typiques

> *« Liste tous les fichiers `.ts` du workspace et trouve celui qui a le plus de lignes »* → `glob('**/*.ts')` puis `read_file` sur les candidats, puis réponse synthétique.
>
> *« Crée un fichier `src/utils/dateFormat.ts` avec une fonction qui formate les dates ISO en français »* → modal `write_file` puis carte verte ✓.
>
> *« Initialise un projet Vite + React + TypeScript dans le dossier courant »* → modal `run_command("npm create vite@latest . -- --template react-ts")` puis modal `npm install` puis cartes ✓.

#### Fonctionnalités également dispo

| Fonctionnalité | Détail |
|---|---|
| 🧷 **Auto-attache du fichier actif** | Toggle dans le header — chaque message envoyé uploadera silencieusement le fichier ouvert dans l'éditeur |
| 📤 **Envoyer la sélection à My_AI** | Palette ou clic droit dans l'éditeur — la sélection est encadrée avec le langage courant pour un rendu propre |
| 📎 **Envoyer le fichier actif à My_AI** | Upload du fichier entier comme pièce jointe (PDF, DOCX, code, image…) |
| 🔧 **Insérer au curseur / Copier** | Boutons sur chaque bloc de code des réponses, au survol |
| 🔁 **Nouvelle connexion** | Bouton toujours visible dans le header — recoller une nouvelle chaîne si vous avez redémarré le Relay sur le PC hôte |
| 💾 **SecretStorage** | Identifiants chiffrés par le keychain de l'OS — auto-restauration au prochain lancement de VS Code |
| 🔄 **Auto-reconnexion** | Détection arrêt du Relay hôte (~30 s), reconnexion automatique au redémarrage |
| 🌍 **Bilingue FR/EN** | UI, modaux d'approbation et doc Marketplace adaptés à la langue de VS Code (NLS) |

#### Sécurité

- La chaîne de connexion contient la clé AES — **traitez-la comme un mot de passe**.
- Tout transite via le **même tunnel E2EE AES-256-GCM** que le mobile : Cloudflare/serveo/localhost.run ne voient que du ciphertext.
- Les outils côté extension sont sandboxés au workspace par construction. Le LLM ne peut **pas** atteindre les MCP locaux du PC hôte (auxquels la GUI desktop et le mobile ont accès).
- L'extension est **open source** — code dans [`vscode_extension/`](../vscode_extension/), aucune télémétrie.

> Doc complète : [`vscode_extension/README.fr.md`](../vscode_extension/README.fr.md) (français) ou [`vscode_extension/README.md`](../vscode_extension/README.md) (anglais). Détails techniques de la boucle agentique côté hôte : [`core/agentic_executor.py`](../core/agentic_executor.py).

### ⚠️ Confirmation de Suppression MCP

Quand l'IA utilise l'outil MCP `delete_local_file` pour supprimer un fichier :
- Une **fenêtre de confirmation** s'affiche avec le chemin complet du fichier
- Boutons **"Oui, supprimer"** et **"Non, annuler"** avec thème cohérent
- La suppression est **bloquée** tant que l'utilisateur n'a pas confirmé

### ⭐ Feedback RLHF — Notation 1-5 Étoiles

Après chaque réponse de l'IA dans le chat, une rangée d'étoiles apparaît (☆☆☆☆☆) :
- **Survolez** les étoiles pour un aperçu interactif (remplissage progressif)
- **Cliquez** sur une étoile pour valider votre note (1 à 5)
- La note est **automatiquement enregistrée** dans `data/rlhf_feedback.db`
- 4-5 ⭐ → feedback positif · 3 ⭐ → neutre · 1-2 ⭐ → négatif

### 💾 Sauvegarde / Chargement de Workflows

Dans l'onglet Agents, le canvas visuel propose trois boutons de gestion :

```
💾 Sauvegarder → exporte le workflow (nœuds + connexions) dans un fichier .json
📂 Charger     → importe un workflow depuis un fichier .json
📤 Export      → exporte les résultats d'exécution en Markdown ou .txt
```

**Exemple d'utilisation :**
```
1. Construire un workflow PlannerAgent → CodeAgent → SecurityAgent
2. Cliquer 💾 Sauvegarder → choisir "mon_workflow.json"
3. Prochaine session : 📂 Charger → sélectionner "mon_workflow.json"
   Le workflow est restauré identiquement, prêt à être exécuté
```

### 🎭 Mode Débat entre deux agents

Dans l'onglet Agents, le bouton **🎭 Mode Débat** (violet) permet de lancer une **confrontation argumentée** entre deux agents au choix :

```
1. Cliquer 🎭 Mode Débat
2. Choisir l'Agent A (proposant) et l'Agent B (opposant) — doivent être différents
3. Saisir le sujet du débat (ex. "Microservices vs monolithe pour une startup")
4. Régler le nombre de tours (1 à 10)
5. Cliquer ▶ Démarrer le débat
```

Chaque tour s'affiche dans une section colorée distincte de la zone de résultats (`Tour N — NomAgent (rôle)`), avec streaming token par token. Le bouton **■ Stop** interrompt le débat entre deux prises de parole.

> Détails complets et API Python : [AGENTS.md → Mode Débat](AGENTS.md#-mode-débat-deux-agents-saffrontent) et [AGENTS_GUI.md → Mode Débat](AGENTS_GUI.md#-mode-débat).

---

**Version:** 8.0.0
**Interfaces:** GUI (CustomTkinter), CLI, API REST, Mobile PWA (Relay), Extension VS Code (TypeScript, Marketplace)
**Capacité Contexte:** 10,485,760 tokens (10M)
**Architecture:** 100% Locale


