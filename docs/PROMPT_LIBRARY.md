# ⚡ Bibliothèque de prompts & Slash commands

My_AI intègre une **bibliothèque de prompts réutilisables**, accessibles via des **slash commands façon [Claude Code](https://claude.com/claude-code)**. Vous tapez une **commande courte** (`/code un jeu de morpion`) et l'IA reçoit un **prompt d'ingénierie complet et détaillé**. La commande reste lisible dans le chat, mais le modèle, lui, travaille sur des instructions soignées. **100% local** — vos templates ne quittent jamais votre machine.

---

## 📍 Où la trouver

- **Autocomplétion** : tapez **`/`** en **tout début** d'une zone de saisie (chat principal, écran d'accueil, mobile, extension VS Code) → un menu déroulant liste les commandes disponibles.
- **Gestion** : barre latérale (**☰**) → bouton **📚 Prompts** → fenêtre de création/édition/suppression de vos templates.

---

## ✨ Le principe : prompt engineering, pas du texte pré-rempli

Une slash command est un **wrapper de prompt engineering**. Elle a un `content` détaillé (le vrai prompt envoyé au modèle) qui contient un placeholder spécial **`{arguments}`** :

```
Vous tapez :   /code un jeu de morpion en Python
                      │
                      ▼  (expansion à l'envoi)
Le modèle reçoit :
   « Tu es un développeur logiciel expert. Écris un programme complet,
     fonctionnel et prêt à l'emploi pour répondre à la demande suivante :

     un jeu de morpion en Python

     Exigences :
     - Choisis le langage le plus adapté si rien n'est précisé…
     - Code clair, idiomatique et commenté.
     - Gère les cas limites et les erreurs éventuelles.
     - Termine par un court mode d'emploi. »
```

La **bulle de chat** continue d'afficher la commande courte (`/code un jeu de morpion en Python`) ; seule la requête envoyée au LLM est étendue. Une commande courte produit donc un prompt bien construit.

> Si le `content` d'un template ne contient **pas** `{arguments}`, le texte saisi après la commande est simplement **ajouté à la suite** du contenu.

---

## 📋 Commandes par défaut

Seedées au **premier lancement** (vous pouvez les éditer ou les supprimer ensuite) :

| Commande | Rôle |
|---|---|
| `/code` | Génère un programme complet, commenté et prêt à l'emploi |
| `/résume` | Résumé fidèle + points clés du texte ou du sujet fourni |
| `/traduis` | Traduit le texte (langue cible déduite, anglais par défaut) |
| `/explique` | Explication simple et pédagogique, avec analogie et exemple |
| `/corrige` | Corrige orthographe/grammaire/ponctuation sans changer le sens |
| `/reformule` | Reformule pour plus de clarté + variante plus concise |

---

## 🖥️ Utilisation (GUI desktop)

1. Dans la zone de saisie, tapez **`/`** : le menu d'autocomplétion s'ouvre.
2. Naviguez au **clavier** (↑/↓), validez avec **Entrée** ou **Tab** (ou cliquez). La saisie devient `/commande `.
3. Tapez votre texte après la commande, puis envoyez normalement.

La gestion des templates (**📚 Prompts**) propose un **CRUD complet** : créer une commande, lui donner un titre/une description, écrire son `content` (avec `{arguments}` où vous voulez injecter le texte de l'utilisateur), et supprimer.

---

## 📱 Mobile (Relay) & 🧩 Extension VS Code

Le même système est disponible partout, via le canal **chiffré de bout en bout** :

- **Mobile** — l'autocomplétion `/` fonctionne dans le chat mobile ; les templates sont récupérés via l'endpoint **`GET /api/prompts`** (E2EE), et l'**expansion** est faite côté hôte à l'envoi.
- **VS Code** — l'extension propose l'autocomplétion `/` et l'expansion à l'envoi (la bulle garde la commande courte). Voir [`vscode_extension/CHANGELOG.md`](../vscode_extension/CHANGELOG.md) (1.3.0 → 1.3.1).

---

## 🏗️ Sous le capot

```
core/prompt_library.py  ── PromptLibrary
   ├─ data/prompt_templates.json     # persistance (écriture atomique, gitignored)
   ├─ _DEFAULT_TEMPLATES             # 6 commandes seedées au 1er lancement
   ├─ expand("/cmd args") → str|None # repère la commande, injecte {arguments}
   ├─ render(tpl, args) → str        # substitution {arguments} (ou ajout en suffixe)
   ├─ find_by_command / search       # lookup + autocomplétion
   └─ _sync_builtins()               # migre le contenu des commandes builtin

interfaces/gui/slash_commands.py  ── SlashCommandsMixin   # autocomplétion « / »
interfaces/gui/prompts_panel.py   ── PromptsPanelMixin    # fenêtre « 📚 Prompts »
relay/relay_server.py             ── GET /api/prompts      # mobile + VS Code (E2EE)
```

- **`expand()`** renvoie `None` si le texte n'est pas une slash command connue → l'appelant envoie le texte tel quel (aucune interférence avec un message normal qui commencerait par `/`).
- **`_sync_builtins()`** met à jour le contenu des commandes **builtin** vers la dernière version du code (migration de format), **sans toucher** à vos templates personnalisés ni aux commandes que vous avez supprimées ou éditées.
- Couvert par `tests/test_prompt_library.py`.

---

## ❓ FAQ

**Mes templates sont-ils synchronisés / envoyés quelque part ?**
Non. Ils vivent dans `data/prompt_templates.json` sur votre machine (fichier **gitignored**). Le mobile et VS Code les lisent via le tunnel **chiffré** du Relay.

**Puis-je créer mes propres commandes ?**
Oui, dans la fenêtre **📚 Prompts**. Donnez une commande `/maCommande`, écrivez le `content` avec `{arguments}`, et elle apparaîtra dans l'autocomplétion partout.

**Une commande supprimée revient-elle après une mise à jour ?**
Non. La migration interne (`_sync_builtins`) ne ré-insère jamais une commande builtin que vous avez supprimée, et ne modifie pas vos templates personnalisés.

---

> Voir aussi : [USAGE.md](USAGE.md), [CODEBASE.md](CODEBASE.md), [CHANGELOG.md](CHANGELOG.md).
