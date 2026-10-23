# 📚 Guide d'Utilisation - My Personal AI v9.0.0

## 🚀 Démarrage Rapide

### Lancement de l'Application

**Interface Graphique (Recommandée):**
```bash
# Lancement direct de la fenêtre
python launch_unified.py

# OU via main.py (fenêtre seule, avec l'Ollama déjà lancé)
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

### Vue d'Ensemble de la fenêtre

L'interface s'affiche dans une fenêtre native ; elle reste fluide
pendant que le moteur calcule.

**Éléments Interface:**
- **Onglets Chat et Agents** en haut de la fenêtre
- **Barre latérale** (Ctrl+B) : nouvelle conversation, recherche globale, conversations, dossiers
  du projet, historique ; en bas, Relay, lecture automatique, Réglages, Mémoire, Prompts et export
- **Fil de messages** : colonne de lecture centrée ; vos messages en bulle, les réponses de l'IA
  directement sur le fond
- **Zone de saisie** en forme de carte : pièces jointes en puces au-dessus du texte, menu
  **« + »**, micro, bouton d'envoi rond qui devient un carré **Stop** pendant la génération
  (Entrée envoie, Maj+Entrée va à la ligne, Échap arrête la réponse)
- **Actions au survol** sous chaque message : copier, lire à voix haute, régénérer, modifier,
  noter (toujours visibles sous le dernier)
- **Volet Aperçu** : à droite du chat — pages HTML générées et documents produits, ouvert
  automatiquement en fin de réponse, à largeur réglable

**Fonctionnalités:**
- 🎨 **Thème sombre** moderne
- 🕒 **Heure** de chaque message, durée et vitesse (tokens/s) de chaque réponse
- 🎨 **Coloration du code** (Shiki) avec bouton **Copier** sur chaque bloc ; formules LaTeX (KaTeX)
- 📁 **Glisser-déposer** de fichiers PDF/DOCX/PowerPoint/Excel/CSV/Images/Code ; un **dossier**
  déposé joint ses fichiers (20 au plus)
- ⏳ **Lecture des pièces jointes** — un indicateur tourne dans la puce tant que le fichier est lu (OCR d'un PDF scanné : 4 à 20 s par page selon la densité du texte) ; l'envoi attend la fin de la lecture, le message reste dans la zone de saisie
- ⏭️ **File d'attente** : un message envoyé pendant une réponse attend son tour, visible au-dessus de la saisie (retirable)
- ✕ **Retirer une pièce jointe** avant l'envoi l'oublie : mémoire de session, mémoire vectorielle (base ChromaDB comprise) et analyse. Si sa lecture est en cours, elle s'arrête à la fin de la page en cours d'OCR. Le document reste en mémoire s'il sert encore : joint à un message de la conversation (ou d'une de ses variantes), à une autre pièce jointe, ou déjà chargé avant cette pièce jointe
- 📝 **Génération de documents** Word/PDF/PowerPoint/Excel, avec aperçu au format natif — voir *Génération de Documents* plus bas
- 🔗 **Chemins cliquables** — un chemin de fichier ou de dossier dans une réponse ouvre son emplacement dans l'explorateur
- 🖼️ **Analyse d'images** avec modèles vision (minicpm-v, llava, llama3.2-vision)
- 📋 **Copier-coller** images depuis presse-papiers (Ctrl+V)
- 🎙️ **Saisie vocale locale** (faster-whisper) — voir section *Voice Mode* plus bas
- 🔊 **Sortie vocale locale** (pyttsx3) — lecture des réponses, voix par langue, lecture auto
- ⚙️ **Panneau Réglages** — gestion des modèles Ollama et paramètres, sans éditer de fichiers
- 🔎 **Recherche globale** — recherche sémantique sur *toutes* vos conversations (barre latérale) ; un clic ouvre la conversation et surligne le passage — voir [CONVERSATION_SEARCH.md](CONVERSATION_SEARCH.md)
- 🧠 **Mémoire** — voir / éditer / supprimer ce que l'IA sait de vous : faits + entrées vectorielles (bouton **Mémoire** en bas de la barre latérale) — voir [MEMORY.md](MEMORY.md)
- 💾 **Sessions** — chaque conversation est enregistrée après chaque réponse et se rouvre au lancement suivant

### Utilisation Typique

```bash
# 1. Lancer l'appli
python launch_unified.py

# 2. La fenêtre s'ouvre sur l'écran de chargement, puis sur l'accueil :
#    logo, titre « My_AI », zone de saisie centrée

# 3. Interactions
# Tapez votre message et Entrée (ou le bouton d'envoi)
Vous: "Bonjour, comment ça va?"
IA: "Salut ! Je vais bien, merci. Comment puis-je t'aider ?"

# 4. Glisser-déposer un fichier dans la saisie (ou menu « + »)
# Le fichier devient une puce ; l'envoi attend la fin de sa lecture

# 5. Questions sur document
Vous: "Résume ce document"
IA: [Résumé basé sur rapport.pdf]

# 6. Nouvelle conversation
# Ctrl+N (ou Ctrl+L) : l'ancienne reste enregistrée dans la barre latérale
```

### 🖼️ Analyse d'Images

L'IA peut analyser des images avec les modèles vision Ollama:

**Méthodes de chargement:**
```bash
# 1. Menu « + » de la saisie → Image
# Sélectionner PNG/JPG/JPEG/GIF/BMP
# Image encodée et prête pour analyse

# 2. Copier-Coller (Ctrl+V)
# Prendre une capture d'écran (Win+Shift+S)
# Dans la zone de saisie : Ctrl+V
# Image collée depuis presse-papiers

# 3. Glisser-Déposer
# Glisser une image sur la zone de saisie
# Image chargée automatiquement
```

Le modèle ne reçoit **qu'une image par message** : une nouvelle image remplace celle qui
attendait (une notification le dit).

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
1. La réponse affiche **« 🎨 Génération de l'image en cours… »** (avec % de progression). Le bouton **Stop** reste actif — un clic annule à la fois le message et la génération.
2. L'image générée s'affiche **dans la même réponse** (clic = ouverture en grand) et est sauvegardée dans `outputs/` ; elle se réaffiche quand la conversation se rouvre.
3. La génération entre dans le **contexte** : « de quoi on a parlé ? » → l'IA se souvient de l'image créée.

> **Premier lancement :** si aucun backend Stable Diffusion n'est détecté, My_AI **installe automatiquement ComfyUI portable** (Windows/NVIDIA) + un modèle par défaut — rien à configurer. Sur les autres systèmes, ou pour choisir un autre backend (AUTOMATIC1111/Forge), voir [IMAGE_GENERATION.md](IMAGE_GENERATION.md). Désactivable via `config.yaml` → `image_generation.auto_setup: false`.
>
> L'**analyse** d'image (« décris cette image ») reste gérée par la vision Ollama et n'est pas confondue avec la génération.

### 🎙️ Saisie Vocale (Voice Mode)

Un bouton micro est présent dans chaque zone de saisie :
- **Écran d'accueil** du chat (avant le premier message)
- **Mode conversation** du chat (pendant une discussion)
- **Onglet Agents** (zone de tâche)

**Utilisation :**

```
1. Clic sur le micro
   → Un point rouge pulse = enregistrement en cours.

2. Parlez (sans limite de durée raisonnable).

3. Clic à nouveau pour arrêter
   → Un indicateur tourne pendant la transcription (~1-3 s selon la durée).

4. Le texte transcrit s'insère automatiquement au curseur de la zone de saisie.
```

La capture du micro et la transcription restent côté Python : la fenêtre ne fait que
démarrer, arrêter et afficher l'état.

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

- **Bouton « Lire à voix haute »** sous chaque réponse (clic = lecture, reclic = stop ; carré ■ pendant la lecture)
- **Bouton « Lecture automatique »** en bas de la barre latérale : lit automatiquement chaque nouvelle réponse de l'IA

| Caractéristique | Valeur |
|---|---|
| **Moteur** | [pyttsx3](https://pyttsx3.readthedocs.io/) — moteur de synthèse de l'OS, 100% local |
| **Windows / macOS** | SAPI5 / NSSpeechSynthesizer — aucune installation supplémentaire |
| **Linux** | nécessite `espeak-ng` (`sudo apt install espeak-ng`) |
| **Voix** | choisie automatiquement selon la **langue détectée** de la réponse (langdetect) |
| **Nettoyage** | code, markdown, URLs et emojis retirés avant lecture (prose naturelle) |

> La voix ne quitte jamais la machine, et **aucun modèle n'est téléchargé** (contrairement au Whisper de la saisie vocale).

### ⚡ Slash commands & Bibliothèque de prompts

Des **prompts réutilisables**. Tapez **`/`** en début de saisie pour ouvrir l'autocomplétion :

```
Vous> /code un jeu de morpion en Python
```

- Naviguez au clavier (↑/↓), validez (Entrée/Tab) ou cliquez ; la saisie devient `/commande `, puis vous tapez votre texte.
- À l'**envoi**, la commande courte est **expansée** en un prompt détaillé pour le modèle — la bulle de chat garde la commande courte.
- **Commandes par défaut** : `/code`, `/résume`, `/traduis`, `/explique`, `/corrige`, `/reformule`.
- **Gérez votre bibliothèque** : bouton **Prompts** en bas de la barre latérale (créer/éditer/supprimer des templates, avec placeholder `{arguments}`).

> Disponible aussi sur **mobile** (Relay) et dans l'**extension VS Code**. Détails : [PROMPT_LIBRARY.md](PROMPT_LIBRARY.md).

### 📁 Contexte projet « @codebase »

Attachez un **dossier entier** à votre workspace pour que l'IA le garde en contexte sur **toutes** vos questions :

- **Barre latérale → Dossiers du projet → Attacher un dossier** (ou menu **« + » → Dossier (codebase)**).
- L'indexation est **incrémentale** et **100% locale** (respecte `.gitignore`, exclut `node_modules`, `.git`, `.venv`…).
- Posez ensuite vos questions normalement : les passages pertinents sont injectés automatiquement (RAG), et les questions *sur* le dossier (chemin, liste de fichiers) reçoivent une réponse directe.
- **Réindexer** après modification (seuls les fichiers changés sont retraités) ou **Détacher** pour retirer le contexte.

> Dans VS Code, tapez **`@`** pour attacher fichiers/dossiers. Détails : [CODEBASE.md](CODEBASE.md).

### 🎹 Command palette (Ctrl+K) & raccourcis clavier

- **`Ctrl+K`** ouvre une palette de commandes avec recherche filtrante (nouveau chat, export, Relay, Réglages, Mémoire, Prompts, Aide…).
- **Raccourcis globaux** : `Ctrl+N` (nouvelle conversation), `Ctrl+L` (nouvelle conversation ; l'ancienne reste enregistrée), `Ctrl+S` (enregistrer la session), `Ctrl+B` (barre latérale), `Ctrl+R` (Relay), `Ctrl+,` (Réglages), `F1` (Aide), `Échap` (arrêter la réponse, ou fermer un dialogue ou un menu).
- Les raccourcis du navigateur (Ctrl+R qui recharge la page, Ctrl+P, F5…) sont neutralisés dans la fenêtre.

### ✏️ Éditer & regénérer un message

- Au survol d'un **message envoyé**, le bouton **« Modifier »** permet de réécrire votre demande puis de **regénérer** la réponse ; au survol d'une **réponse**, **« Régénérer »** en produit une nouvelle variante sans rien modifier.
- L'ancienne version est **conservée** (réponse, réflexion et documents compris) : naviguez entre les variantes d'un même tour avec **‹ k/n ›**.
- Éditer un message en milieu de conversation **remplace l'aval** (branchement façon ChatGPT) — vous êtes prévenu avant ; l'aval reste attaché à l'ancienne variante.

### 🔗 Citations web cliquables

Après une **recherche internet**, les sources sont **numérotées** et l'IA place des marqueurs **`[n]`** dans sa réponse. Cliquez sur un `[n]` (dans le corps ou la liste des sources) pour **ouvrir l'URL d'origine** — sur desktop **et** mobile.

> Les commandes `aide`, `statut` et `quitter` n'existent que dans la **CLI** (voir plus bas).
> Dans la fenêtre : **F1** pour l'aide, l'écran de chargement et les Réglages pour l'état
> d'Ollama et du modèle.

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

État My Personal AI v9.0.0:
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
> « Génère un **tableau**… » n'en fait pas partie : seul, le mot désigne un tableau de données.

### 7. Génération de Documents

**Triggers:** génère/crée/rédige/fais + un format ou un type de document (docx, Word, PDF, PowerPoint, présentation, Excel, tableur, rapport…)

```bash
Vous> génère un pdf sur les dauphins
IA> [📄 Rédaction du document pdf]
    J'ai créé le PDF « Les dauphins » : il présente leurs espèces, leur habitat…
    [aperçu ouvert automatiquement dans le volet de droite]
    [fichier dans outputs/documents/]

# Modifier un document joint (📎 ou glisser-déposer) — l'original n'est jamais touché
Vous> dans ce docx, remplace "rorqual commun" par "petit rorqual"
IA> La version modifiée est enregistrée dans outputs/documents/rapport_modifie.docx
```

> Le bouton **🔍 Aperçu** sous la réponse rouvre le volet, le bouton **📂** ouvre le
> fichier dans son application. Détails : [DOCUMENT_GENERATION.md](DOCUMENT_GENERATION.md)
> et [ARTIFACTS_PREVIEW.md](ARTIFACTS_PREVIEW.md).

---

## 📁 Traitement de Fichiers

### Types de Fichiers Supportés

| Extension | Processeur | Capacités |
|-----------|------------|-----------|
| .pdf | PDFProcessor | Texte, metadata, images, chunking |
| .docx | DOCXProcessor | Paragraphes, tables, formatage |
| .pptx, .potx | PPTXProcessor | Titres, puces avec niveaux, tableaux, notes du présentateur |
| .xlsx | ExcelProcessor | Feuilles multiples, cellules, formatage tableau |
| .xls | ExcelProcessor | Ancien format Excel (via xlrd) |
| .csv | ExcelProcessor | Données tabulaires, encodage automatique |
| .txt | FileManager | Texte brut |
| .py, .js, .html, .css | CodeProcessor | Code avec analyse syntaxique |
| .md | FileManager | Markdown |
| .json | FileManager | JSON structuré |

### Méthodes de Chargement

#### 1. Glisser-déposer (fenêtre)
```bash
# Dans la fenêtre :
# 1. Ouvrir l'explorateur de fichiers
# 2. Sélectionner un fichier (PDF, DOCX, PowerPoint, Excel, CSV, code...) ou un dossier
# 3. Le glisser sur la zone de saisie
# 4. La puce du fichier tourne pendant sa lecture, puis la notification « ✅ … prêt »
```

#### 1b. Via le menu « + » (fenêtre)
```bash
# Écran d'accueil ou conversation : menu « + » de la saisie → type de fichier :
#   PDF               → sélection .pdf
#   DOCX              → sélection .docx
#   Excel / CSV       → sélection .xlsx / .xls / .csv
#   PowerPoint        → sélection .pptx / .potx
#   Code              → sélection fichier source
#   Image             → sélection .png / .jpg
#   Dossier (codebase) → dossier du projet, indexé (voir « Contexte projet »)
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
   ├─ .pptx/.potx  → PPTXProcessor (python-pptx)
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

Le modèle lance la recherche de lui-même quand une question demande des informations récentes (actualités, prix, classements, documentation à jour). « Cherche sur internet… » la demande explicitement.

```bash
Vous> Cherche sur internet les meilleures marques de voiture, fais un tableau
IA> | Rang | Marque | Points forts | …
    | 1 | Toyota | Robustesse, fiabilité durable | …
    …
    📚 Sources
    [Quelle est la meilleure marque de voiture 2026 - autohero.com](https://www.autohero.com/…)
    …
```

### Fonctionnalités Recherche

**Moteurs :** DuckDuckGo, puis Yahoo en secours, puis Wikipédia (articles pertinents seulement)

**Capacités :**
- 8 sources au plus (2 par site), les 4 premières pages lues en parallèle
- Passages de chaque page qui répondent à la requête, sans menus ni bandeaux
- Sources numérotées et liens cliquables en fin de réponse
- Météo : Open-Meteo, conditions actuelles et prévisions sur 7 jours (« météo Toulouse »)
- URL dans la question : la page est lue directement (« résume https://… »)
- Cache 30 min des recherches déjà faites

Détails, réseau et dépannage : [INTERNET_SEARCH.md](INTERNET_SEARCH.md).

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
  MY PERSONAL AI - System Status v9.0.0
═══════════════════════════════════════════════

🤖 AI Model: CustomAIModel
📊 Version: 9.0.0
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

My Personal AI v9.0.0
- Architecture: 100% Local
- Context: 1,048,576 tokens (1M)
- Interfaces: fenêtre (React + pywebview), CLI
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
1. Lire le message « Aucun résultat trouvé pour … » : il indique l'état de chaque moteur (bloqué, injoignable, sans résultat)
2. Vérifier firewall/proxy (section `network` de `config.yaml`)
3. DuckDuckGo bloqué : il est mis en pause 15 min, Yahoo prend le relais

### Problème: Mémoire pleine

**Erreur:** "Context manager at capacity"

**Solutions:**
```bash
# Via CLI
Vous> statut
# Voir utilisation contexte

# Nouvelle conversation dans la fenêtre (Ctrl+N) OU redémarrer
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
- Ouvrir une nouvelle conversation (Ctrl+N) régulièrement si mémoire limitée
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

Demandez à l'IA de retenir une information : elle l'enregistre comme fait (panneau Mémoire, onglet Faits) et s'en sert dans les conversations suivantes :

```
Vous : "Retiens que je préfère Python pour les scripts d'automatisation"
→ Fait enregistré : [general] je préfère Python pour les scripts d'automatisation

Vous : "N'oublie pas que mon manager s'appelle Thomas Dupont"
→ Fait enregistré : [general] mon manager s'appelle Thomas Dupont
```

Vous pouvez aussi ajouter, modifier ou supprimer des faits dans le panneau Mémoire. À chaque réponse, les faits utiles à votre message (mots en commun, puis les plus récents) sont injectés dans le prompt du modèle. Détails : [MEMORY.md](MEMORY.md).

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
2. Sélectionnez un ou plusieurs fichiers (PDF, DOCX, PowerPoint, TXT, code, CSV...)
3. Les fichiers apparaissent en preview dans la zone de saisie
4. Le contenu des fichiers est automatiquement injecté dans le prompt de l'agent
5. En workflow multi-agents, **tous les agents** reçoivent les fichiers joints

### 📡 My_AI Relay — Accès depuis le Mobile

My_AI Relay vous permet de discuter avec votre IA depuis votre smartphone (iOS ou Android), partout dans le monde, tant que l'application tourne sur votre PC.

#### Démarrage

1. Cliquez sur **Relay** en bas de la **barre latérale** (ou **Ctrl+R**, ou la palette Ctrl+K) : le panneau Relay s'ouvre et démarre le Relay s'il ne tourne pas
2. My_AI Relay démarre un serveur WebSocket local et ouvre **plusieurs tunnels en parallèle** (cloudflared et localhost.run ; serveo en option) pour garantir que le téléphone puisse en atteindre au moins un — utile quand un opérateur mobile filtre certains domaines de tunnels publics. Le PC vérifie chaque tunnel annoncé : le panneau montre l'état de chacun (« Vérification des tunnels… », « ne répond pas »). Si aucun ne répond au PC dans les 30 s, le panneau affiche « Aucun tunnel ne répond depuis ce PC » et le QR code les reprend tous, sans garantie : le PC peut être sur un réseau qui filtre ces domaines, pas le téléphone
3. Un **QR code** s'affiche dans le panneau Relay dès qu'un tunnel répond (en quelques secondes avec localhost.run ; cloudflared le rejoint 15 à 20 s après le démarrage, et le QR code se met alors à jour) — scannez-le avec votre téléphone. Le QR ne contient que les tunnels joignables et pointe vers une **page de routage statique** (hébergée sur GitHub Pages) qui les ping et redirige automatiquement vers le premier qui répond, en général le plus rapide
4. Le téléphone demande le **code d'accès** affiché sous le QR code dans le panneau Relay (6 chiffres, nouveau à chaque démarrage du Relay). Un rechargement de la page ne le redemande pas ; le lien rouvert dans un autre onglet, si. Après 5 codes erronés, le Relay n'en accepte plus aucun jusqu'à son redémarrage (nouveau QR code, nouveau code), et la fenêtre du PC signale chaque code erroné
5. L'interface mobile s'ouvre sur deux onglets en haut — **💬 Chat** et **🤖 Agents** — qui reprennent la navigation de la fenêtre du PC. Le Chat est affiché par défaut ; touchez **Agents** pour accéder au système d'agents.

#### Onglet 💬 Chat

```
Téléphone                         PC (service de chat de l'appli)
   │                                     │
   │─── Message via WebSocket ──────────>│
   │                                     │── Affiché dans la fenêtre (badge « Mobile »), si elle est ouverte
   │                                     │── L'IA répond (streaming)
   │<── Streaming + réponse finale ──────│
```

- L'appli traite le message **exactement comme un message local** (avec streaming, thinking, outils, etc.), **fenêtre ouverte ou non** ; il prend sa place dans la même file d'attente que les messages du PC
- La réponse est streamée en direct au mobile (token par token), puis finalisée
- **Bouton Stop** : pendant la génération, le bouton d'envoi se transforme en bouton Stop (carré noir sur fond blanc). Le toucher interrompt la réponse du téléphone (ou retire son message de la file d'attente) et renvoie la réponse partielle marquée « interrompue »
- **Liens cliquables** : la syntaxe Markdown `[titre](url)` ainsi que les URLs nues s'affichent en **bleu souligné cliquable** (ouverture dans un nouvel onglet), comme sur le PC

#### Onglet 🤖 Agents

L'onglet Agents reprend **toutes les fonctionnalités de la page Agents du PC**, en version tactile. Une exécution lancée du téléphone devient aussi un fil de la page Agents du PC (« Lancé du téléphone »). Tout s'exécute **côté PC** (orchestrateur d'agents + modèle Ollama local) et est streamé au mobile via le même tunnel chiffré — le contenu ne quitte jamais l'enveloppe E2EE.

- **Grille d'agents** — les 9 agents spécialisés (CodeAgent, WebAgent, AnalystAgent, CreativeAgent, DebugAgent, PlannerAgent, SecurityAgent, OptimizerAgent, DataScienceAgent) plus vos agents personnalisés. Touchez une carte pour l'ajouter au workflow.
- **Agents personnalisés** — bouton **➕ Créer Agent** : saisissez un nom + un rôle, le LLM local génère le *system prompt* (et la température). Modification ✏️ et suppression ✕ depuis la carte. Les agents sont stockés dans le **même `data/custom_agents.json` que le PC** → synchronisés dans les deux sens.
- **Workflow visuel (style n8n)** — canvas tactile : déplacez les nœuds au doigt, reliez le **port de sortie** (droite) d'un nœud au **port d'entrée** (gauche) d'un autre. La topologie détermine l'exécution : agent seul, **séquentiel** (chaîne), **parallèle** (nœuds indépendants) ou **DAG** (graphe). Sauvegarde 💾 / chargement 📂 / export 📤 du workflow.
- **Exécution** — décrivez la tâche, touchez **▶ Exécuter** : chaque agent apparaît comme une section dépliable qui se remplit en streaming, avec le statut du nœud (En attente / En cours / Terminé / Erreur). Le bouton **▶ Exécuter** devient **■ Stop** pendant l'exécution.
- **Mode Débat** — bouton **🎭 Mode Débat** : choisissez deux agents, un sujet et un nombre de tours ; les deux agents s'opposent tour par tour, en streaming.
- **Clear Workflow** — vide le canvas.
- **Pièces jointes** — bouton **+** de la barre d'action (voir ci-dessous) : le contenu des fichiers (ou la description de l'image) est injecté dans la tâche des agents.

> Les workflows/débats s'exécutent **un à la fois** (comme sur le PC). Le mode débat ne prend pas de pièces jointes, comme sur le PC.

#### 📎 Pièces jointes depuis le mobile

Le bouton **+** permet de joindre une ou plusieurs pièces jointes — **à la fois sur l'onglet Chat** (à gauche du champ de saisie) **et sur l'onglet Agents** (au-dessus des boutons d'action). Les fichiers sont traités **exactement comme sur le PC** :

- **Images** (PNG, JPG, JPEG, GIF, BMP, WebP, TIFF) → envoyées au **modèle vision** (encodage base64, même pipeline que le drag & drop PC)
- **Documents** (PDF, DOCX, DOC, PPTX, POTX, XLSX, XLS, CSV) → extrait de contenu ajouté au **contexte vectoriel** via les processeurs spécialisés
- **Code & texte** (PY, JS, HTML, CSS, JSON, XML, MD, TXT) → chargés dans le contexte de la session

Un document **généré** depuis le mobile (« *génère un pdf sur…* ») arrive avec son aperçu, ouvert automatiquement dans la modale, et un bouton **💾** pour télécharger le fichier. Aperçu et fichier transitent chiffrés, comme les images générées.

Détails techniques :

- L'upload est **streamé** vers un répertoire temporaire (`{tempdir}/my_ai_relay_uploads/`) avec validation d'extension et plafond de **25 Mo** par fichier — l'upload chiffré (`POST /api/upload`) est partagé par le Chat et la page Agents
- **Sur l'onglet Agents**, le contenu des documents (et la description vision des images) est injecté en fin de tâche sous forme de sections `--- Fichier joint : … ---` avant le lancement du workflow (même logique que la page Agents du PC, `processors/attachments.py`)
- Un fichier envoyé sans message (Chat) déclenche une requête par défaut (`"Décris cette image en détail."` ou `"Analyse ce fichier et résume-le."`)
- Image + documents peuvent être combinés dans un même message ; le premier fichier image est envoyé au modèle vision, les autres rejoignent le contexte
- Le contexte est garanti **prêt avant** le démarrage de l'inférence (le pipeline document est exécuté de façon synchrone avant l'appel au modèle)
- Endpoint côté serveur : `POST /api/upload?token=...` (multipart, retourne un `file_id`) ; le client WebSocket passe ensuite les `file_ids` dans le message de chat

#### Configuration (`config.yaml`)

```yaml
relay:
  auto_start: false       # true = Relay démarre automatiquement au lancement de l'appli
  port: 8765              # Port du serveur local
  response_timeout: 500   # Délai max de réponse IA (secondes)
  tunnel: true            # false = réseau local uniquement (sans accès externe)
  tunnel_providers:       # Providers de tunnel à démarrer en parallèle
    - "cloudflared"       #   *.trycloudflare.com (auto-téléchargé)
    - "localhost.run"     #   *.lhr.life (via SSH, anonyme)
    # - "serveo"          #   *.serveousercontent.com (via SSH) : expose votre IP, voir ci-dessous
  host: "0.0.0.0"         # Écoute sur toutes les interfaces réseau
```

> **Pourquoi plusieurs providers ?** Certains opérateurs mobiles (notamment en 5G) filtrent au niveau DNS les domaines des tunnels publics éphémères (`*.trycloudflare.com` est le plus filtré). En lançant plusieurs tunnels en parallèle sur des domaines différents, le téléphone peut toujours en joindre au moins un. Si vous savez que votre opérateur ne filtre rien, vous pouvez ne garder qu'un provider pour économiser un peu de bande passante : `tunnel_providers: ["cloudflared"]`.

Les providers comparés (mesures du 2026-10-19, depuis un PC en France) :

| Provider | Serveurs | Prêt après | Aller-retour | À savoir |
|---|---|---|---|---|
| `cloudflared` | Cloudflare (Paris) | 15 à 20 s | ~70 ms | Le plus rapide ; son nom n'existe que quelques secondes après l'annonce, d'où le délai |
| `localhost.run` | Amazon (Virginie, USA) | ~2 s | ~190 ms | Le plus lent (serveurs aux États-Unis), mais disponible tout de suite |
| `serveo` (en option) | Hetzner (Helsinki) | ~1 s | ~120 ms | Le nom du tunnel **contient l'adresse IP publique de votre réseau** (`…-203-0-113-7.serveousercontent.com`), visible de qui a le QR code et du réseau du téléphone (DNS, début de la connexion HTTPS). Sa page d'avertissement est sautée par la page de routage |

Pour la fluidité du chat, la différence ne se voit pas : la réponse arrive en flux continu et le tunnel ne fait que décaler son début (le rythme dépend du modèle). Le provider le plus rapide rend surtout plus vives les actions (chargement, envoi d'un message).

#### Page de routage GitHub Pages (forkers du projet)

Le QR code encode une URL de la forme `https://gonicolas12.github.io/My_AI/router.html#d=<base64>` — la page de routage est servie depuis le **GitHub Pages du repo officiel**. Si vous **forkez** le projet et changez l'URL dans `relay/relay_server.py` (constante `_ROUTER_PAGE_URL`), pensez à activer GitHub Pages sur **votre fork** : Settings → Pages → Source = `Deploy from a branch` → Branch = `main` / `/docs` → Save. Les utilisateurs en aval n'ont rien à configurer : ils clonent et ça marche.

#### Accès réseau local (sans tunnel)

Si tous les providers sont indisponibles ou si `tunnel: false`, le Relay reste accessible sur votre réseau local :

```
http://<IP_de_votre_PC>:8765/?token=<votre_token>#k=<clé_E2EE>
```

Copiez l'adresse locale affichée dans le panneau Relay (elle contient le token et la clé de chiffrement, sans laquelle l'interface mobile refuse de s'ouvrir) et remplacez `127.0.0.1` par l'adresse IP du PC sur votre réseau. Le code d'accès est demandé comme avec le QR code.

#### Sécurité

| Mécanisme | Détail |
|---|---|
| **Jeton (token)** | 12 octets aléatoires (`secrets.token_urlsafe`), tirés à chaque démarrage du Relay et inclus dans le lien du QR code : personne ne le tape. Sans lui, le Relay refuse tout, avant même de regarder un code. Après un redémarrage, l'ancien lien ne sert plus : il faut rescanner |
| **Code d'accès** | 6 chiffres tirés à chaque démarrage du Relay, affichés sous le QR code mais **absents du lien** : le téléphone et l'extension VS Code le demandent avant tout accès (API et WebSocket refusés sans la session qu'il ouvre). Un lien qui fuite sans que l'écran soit vu (historique du navigateur synchronisé, presse-papiers, appli de lecture de QR code, chaîne de connexion recopiée) ne suffit donc pas. Le code voyage chiffré par la clé E2EE : sans le lien complet, impossible d'en essayer un. Après 5 codes erronés, le Relay n'en accepte plus aucun jusqu'à son redémarrage ; la fenêtre du PC signale chaque code erroné. Ne protège pas d'une personne qui voit votre écran (QR code et code côte à côte) |
| **Tunnel HTTPS** | Tous les providers (cloudflared/localhost.run/serveo) chiffrent en TLS sur le réseau, **mais terminent le TLS sur leur infrastructure** : sans la couche E2EE ci-dessous, le contenu serait lisible par eux |
| **Adresse IP du PC** | Le PC n'ouvre aucun port vers Internet : il ne fait que des connexions sortantes vers les tunnels. Les noms des tunnels cloudflared et localhost.run ne révèlent pas votre adresse IP ; celui de serveo la contient, d'où son absence par défaut. La liste des tunnels n'est jamais servie sans token |
| **Chiffrement bout-en-bout (E2EE)** | **AES-256-GCM applicatif** au-dessus du WebSocket et des uploads. La clé symétrique (32 octets) est générée localement à chaque démarrage du Relay et transmise au mobile **uniquement via le QR code** (canal optique). Ni le serveur de tunnel public (Cloudflare, serveo, localhost.run) ni GitHub Pages ne peuvent déchiffrer le contenu : ils ne voient que des octets opaques. |
| **Token + clé hors-serveur** | Le token et la clé E2EE voyagent dans le **fragment** de l'URL de routage (`#d=<base64>`) — le fragment n'est jamais émis sur le réseau, seul le navigateur le lit : GitHub Pages ne voit ni l'un ni l'autre. Le token part ensuite vers le Relay avec chaque requête (le service de tunnel le voit passer) ; la clé, jamais |
| **Strict, pas de downgrade** | Le serveur **rejette** toute connexion WS dont les messages ne sont pas chiffrés (close 4002). Pas de mode dégradé : on ne peut pas forcer du clair via une attaque MITM applicative. |
| **Aucune donnée cloud** | Les tunnels ne sont que des relais chiffrés — vos données restent sur votre PC, et le contenu transitant par les tunnels publics est illisible pour leurs opérateurs |

### 🧩 Extension VS Code — Mode agentique

L'extension officielle **My_AI Relay** est publiée sur le **Marketplace VS Code**. Depuis sa **v1.1.0**, elle expose un **mode agentique** : l'extension s'identifie auprès du Relay comme client `vscode`, et le Relay aiguille la conversation vers une boucle de raisonnement dédiée qui appelle Ollama directement avec un prompt système outillé. Le LLM reste sur le PC hôte ; l'**exécution des outils est déléguée à l'extension**, qui les exécute dans le workspace VS Code de l'utilisateur, sandboxé par défaut. Le mobile et la fenêtre desktop continuent à utiliser le pipeline classique (avec MCP locaux complets) — strictement inchangés.

#### Démarrage en 3 étapes

1. **Sur le PC hôte** : démarrez le Relay (**Relay** en bas de la barre latérale, ou Ctrl+R) → attendez qu'au moins un tunnel réponde → cliquez sur **Copier pour l'extension VS Code** dans le panneau.
2. **Dans VS Code** : installez l'extension `gonicolas12.my-ai` depuis le Marketplace (Extensions → recherche "My_AI Relay" → Install).
3. **Connexion** : ouvrez la vue *My_AI Relay* dans la sidebar → cliquez sur **Coller la chaîne de connexion…** → collez la chaîne de l'étape 1 → saisissez le **code d'accès** affiché sous le QR code (extension 1.5.0 ou plus récente).

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

Chaque appel d'outil s'affiche comme une **carte pliable**, avec une bordure gauche colorée selon l'état (orange = en cours · indigo = en attente d'approbation · vert = OK · rouge = erreur · gris = refusé). Cliquer déplie les arguments JSON et la sortie capturée (stdout/stderr pour les commandes shell, lignes modifiées pour les éditions).

#### Sandbox & isolation

- **Limité au workspace par défaut.** Tous les chemins sont résolus relativement au premier dossier workspace ouvert. Toute tentative de sortie déclenche un modal d'approbation par chemin (jamais auto-approuvable).
- **Aucun accès aux MCP du PC hôte** depuis l'extension. Le mode agentique est **isolé** du pipeline de la fenêtre et du mobile : l'utilisateur côté VS Code ne voit que son workspace.
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
| 📎 **Envoyer le fichier actif à My_AI** | Upload du fichier entier comme pièce jointe (PDF, DOCX, PowerPoint, code, image…) |
| 🔧 **Insérer au curseur / Copier** | Boutons sur chaque bloc de code des réponses, au survol |
| ⏹️ **Stop** | Le bouton d'envoi devient Stop pendant la génération : il arrête le modèle et les appels d'outils en attente ; le texte se fige aussitôt |
| 🧹 **Clear** (« Effacer » en français) | Vide la vue (le contexte de la session reste côté hôte) ; pendant une génération, il l'arrête aussi |
| 🔁 **Nouvelle connexion** | Bouton toujours visible dans le header — recoller une nouvelle chaîne si vous avez redémarré le Relay sur le PC hôte |
| 💾 **SecretStorage** | Identifiants chiffrés par le keychain de l'OS — auto-restauration au prochain lancement de VS Code |
| 🔄 **Auto-reconnexion** | Détection arrêt du Relay hôte (~30 s), reconnexion automatique au redémarrage |
| 🌍 **Bilingue FR/EN** | UI, modaux d'approbation et doc Marketplace adaptés à la langue de VS Code (NLS) |

#### Sécurité

- La chaîne de connexion contient la clé AES — **traitez-la comme un mot de passe**.
- Elle ne suffit pas seule : l'extension demande aussi le **code d'accès** affiché sous le QR code, que la chaîne ne contient pas. La session ouverte par ce code est gardée avec les identifiants (pas de nouvelle saisie au relancement de VS Code tant que le Relay tourne).
- Tout transite via le **même tunnel E2EE AES-256-GCM** que le mobile : Cloudflare/serveo/localhost.run ne voient que du ciphertext.
- Les outils côté extension sont sandboxés au workspace par construction. Le LLM ne peut **pas** atteindre les MCP locaux du PC hôte (auxquels la fenêtre desktop et le mobile ont accès).
- L'extension est **open source** — code dans [`vscode_extension/`](../vscode_extension/), aucune télémétrie.

> Doc complète : [`vscode_extension/README.fr.md`](../vscode_extension/README.fr.md) (français) ou [`vscode_extension/README.md`](../vscode_extension/README.md) (anglais). Détails techniques de la boucle agentique côté hôte : [`core/agentic_executor.py`](../core/agentic_executor.py).

### ⚠️ Confirmation de Suppression MCP

Quand l'IA utilise l'outil MCP `delete_local_file` pour supprimer un fichier :
- Un **dialogue de confirmation** s'affiche dans la fenêtre avec le chemin complet du fichier
- Boutons **"Oui, supprimer"** et **"Non, annuler"** ; Échap ou fermer le dialogue vaut refus
- La suppression est **bloquée** tant que l'utilisateur n'a pas confirmé ; sans fenêtre ouverte (message du téléphone), elle est refusée

### ⭐ Feedback RLHF — Notation 1-5 Étoiles

Sous chaque réponse de l'IA, une rangée d'étoiles (☆☆☆☆☆) apparaît avec les autres actions, au survol (toujours visible sous la dernière réponse) :
- **Survolez** les étoiles pour un aperçu interactif (remplissage progressif)
- **Cliquez** sur une étoile pour valider votre note (1 à 5)
- La note est **automatiquement enregistrée** dans `data/rlhf_feedback.db`
- 4-5 ⭐ → feedback positif · 3 ⭐ → neutre · 1-2 ⭐ → négatif

### 💾 Sauvegarde / Chargement de Workflows

Dans l'onglet Agents, le canvas visuel propose trois boutons de gestion :

```
Enregistrer → enregistre le workflow (nœuds + liens) dans un fichier .json
Charger     → restaure un workflow depuis un fichier .json
Exporter    → fichier Markdown : la tâche, les agents (nom, type, statut), puis la
              réponse de chacun à la dernière exécution
```

**Exemple d'utilisation :**
```
1. Construire un workflow PlannerAgent → CodeAgent → SecurityAgent
2. Cliquer Enregistrer → choisir "mon_workflow.json"
3. Prochaine session : Charger → sélectionner "mon_workflow.json"
   Le workflow est restauré identiquement, prêt à être exécuté
```

Les workflows enregistrés avec l'ancienne interface se rechargent tels quels (même format).

### 🎭 Mode Débat entre deux agents

Dans l'onglet Agents, le bouton **Débat** permet de lancer une **confrontation argumentée** entre deux agents au choix :

```
1. Cliquer Débat
2. Choisir l'Agent A (proposant) et l'Agent B (opposant) — doivent être différents
3. Saisir le sujet du débat (ex. "Microservices vs monolithe pour une startup")
4. Régler le nombre de tours (1 à 10)
5. Cliquer Démarrer le débat : le débat devient un fil, un tour par section
```

Chaque tour s'affiche dans une section colorée distincte de la zone de résultats (`Tour N — NomAgent (rôle)`), avec streaming token par token. Le bouton **■ Stop** interrompt le débat entre deux prises de parole.

> Détails complets et API Python : [AGENTS.md → Mode Débat](AGENTS.md#-mode-débat-deux-agents-saffrontent) et [AGENTS_GUI.md → Mode Débat](AGENTS_GUI.md#-mode-débat).

---

**Version:** 9.0.0
**Interfaces:** fenêtre desktop (React + TypeScript, pywebview), CLI, API REST, Mobile PWA (Relay), Extension VS Code (TypeScript, Marketplace)
**Capacité Contexte:** 10,485,760 tokens (10M)
**Architecture:** 100% Locale


