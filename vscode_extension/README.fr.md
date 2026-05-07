# My_AI Relay — Extension VS Code

[English](./README.md) · **Français**

> Chat **agentique** avec votre **assistant [My_AI](https://github.com/gonicolas12/My_AI) auto-hébergé**
> depuis VS Code, via un tunnel chiffré bout-en-bout — comme Claude Code,
> mais sur le LLM local qui tourne sur votre propre machine.

L'extension est un client distant. Le LLM, l'historique et le traitement
des fichiers vivent sur le **PC qui héberge My_AI** ; l'extension exécute
les opérations sur le système de fichiers et le shell côté workspace,
limitées au workspace VS Code par défaut. Vous pouvez ainsi faire tourner
un gros LLM sur un desktop à la maison et l'utiliser depuis n'importe quel
laptop, n'importe où — avec une expérience développeur équivalente à
Claude Code, et l'interface mobile existante continue de fonctionner
exactement comme avant.

---

## Points forts

- 🤖 **Mode agentique** (nouveau en 1.1.0) — le modèle peut lire, modifier
  et créer des fichiers, lancer des commandes shell, et chercher dans le
  workspace via neuf outils intégrés. Chaque appel d'outil s'affiche dans
  le chat sous forme de carte pliable façon Claude Code, avec son statut,
  ses arguments et sa sortie.
- 🛡️ **Sandbox du workspace** — tous les chemins sont résolus à partir du
  dossier workspace ouvert. Tout accès en dehors du workspace nécessite
  une approbation modale par chemin, jamais auto-approuvable.
- ✋ **Flux d'approbation** — les outils en lecture seule s'exécutent
  silencieusement ; `write_file`, `edit_file` et `run_command` demandent
  confirmation, avec des options pour autoriser une fois, autoriser le
  même fichier, ou autoriser l'outil pour le reste de la session.
- 🔐 **Chiffrement bout-en-bout** — AES-256-GCM par-dessus le tunnel
  public. Le serveur Cloudflare/serveo/localhost.run ne voit que du
  ciphertext.
- 🌐 **Failover multi-tunnel** — cloudflared, serveo et localhost.run
  tournent en parallèle côté hôte ; l'extension choisit le premier
  joignable et bascule automatiquement si l'un tombe.
- 💾 **Connexion persistante** — les identifiants restent chiffrés dans le
  SecretStorage de VS Code. L'extension se reconnecte automatiquement
  quand le Relay hôte revient en ligne, et se déconnecte quand il
  s'arrête.
- 🧩 **Intégration espace de travail**
  - Attache automatique du fichier actif à chaque message (toggle).
  - « Envoyer la sélection à My_AI » (palette de commandes + menu
    contextuel de l'éditeur).
  - « Envoyer le fichier actif à My_AI ».
  - Boutons **Insérer au curseur** / **Copier** sur chaque bloc de code
    des réponses, en un clic.

## Prérequis

- **VS Code** ≥ 1.85.
- Un **PC hôte My_AI** où le Relay tourne (n'importe quelle machine
  capable de lancer My_AI). Le bouton Relay est en haut à gauche de la
  barre latérale du GUI.
- Une **connexion Internet** des deux côtés (le tunnel chiffré passe par
  Cloudflare / serveo / localhost.run).

## Démarrage rapide

### 1. Lancer le Relay sur le PC hôte

1. Lancez My_AI sur le PC qui fait tourner le modèle.
2. Cliquez sur le bouton **Relay** en haut à gauche de la barre latérale.
3. Attendez qu'au moins un tunnel soit « actif » (statut vert).

### 2. Copier la chaîne de connexion

Dans la même popup Relay, cliquez sur **🧩 Copier pour l'extension VS Code**.
La chaîne copiée ressemble à :

```
https://gonicolas12.github.io/My_AI/router.html#d=…
```

Elle contient la liste des tunnels publics, le token d'authentification
et la clé AES-256-GCM — le tout dans le fragment d'URL, donc rien ne
fuite vers le serveur de tunnel. **Traitez-la comme un mot de passe.**

### 3. Se connecter depuis VS Code

1. Installez l'extension **My_AI Relay**.
2. Ouvrez la vue **My_AI Relay** dans la barre d'activité (la petite icône
   d'assistant, par défaut à gauche). Au premier lancement, l'extension
   vous proposera de déplacer le chat dans la **barre latérale secondaire**
   (à droite, comme GitHub Copilot Chat) — acceptez et VS Code s'en
   souviendra.
3. Cliquez sur **Coller la chaîne de connexion…** (ou lancez la commande
   *My_AI Relay : Se connecter* depuis la palette de commandes) et
   collez la chaîne de l'étape 2.

Le chat est désormais actif. La même conversation est visible sur le GUI
hôte et sur tout mobile ayant scanné le QR code.

> **Astuce — déplacer le chat plus tard.** L'API d'extensions VS Code ne
> permet de contribuer des vues custom qu'à la barre d'activité ou au
> panneau ; la barre latérale secondaire est réservée aux déplacements
> manuels par l'utilisateur. Si vous avez raté la proposition initiale,
> lancez *My_AI Relay : Déplacer le chat vers la barre latérale
> secondaire* depuis la palette, ou faites clic droit sur l'icône My_AI
> Relay → « Déplacer vers » → « Barre latérale secondaire ».

## Mode agentique

À la connexion, l'extension s'identifie auprès du Relay comme client
VS Code. À partir de ce moment, chaque message passe par une boucle
agentique côté hôte : le LLM local peut émettre des appels d'outils,
l'extension les exécute dans votre workspace, et le résultat est renvoyé
au modèle jusqu'à ce qu'il produise une réponse finale.

### Outils disponibles

| Outil | Description |
| --- | --- |
| `read_file` | Lire un fichier du workspace (avec `offset` / `limit` pour les gros fichiers). |
| `write_file` | Créer ou écraser un fichier. Crée les dossiers parents automatiquement. ⚠ |
| `edit_file` | Remplacement par correspondance exacte dans un fichier existant (`replace_all` optionnel). ⚠ |
| `list_dir` | Lister le contenu d'un dossier du workspace. |
| `glob` | Trouver les fichiers correspondant à un glob (`**/*.ts`, `src/**/index.*`, …). |
| `grep` | Rechercher dans le contenu des fichiers via ripgrep, avec fallback JS si `rg` est absent. |
| `run_command` | Exécuter une commande shell dans le workspace. ⚠ |
| `get_active_editor` | Lire le fichier actuellement ouvert et la sélection utilisateur. |
| `open_file` | Ouvrir un fichier du workspace dans l'éditeur (et révéler une ligne optionnelle). |

⚠ = demande l'approbation explicite de l'utilisateur (modal).

### Sandbox & approbations

- **Limité au workspace par défaut.** Tous les chemins sont résolus à
  partir du premier dossier workspace. Un chemin qui sort du workspace
  déclenche un modal demandant une autorisation ponctuelle — il n'y a
  pas d'option « se souvenir » pour les accès hors workspace.
- **Outils en lecture seule** (`read_file`, `list_dir`, `glob`, `grep`,
  `get_active_editor`, `open_file`) : exécution silencieuse.
- **Outils modifiants** (`write_file`, `edit_file`, `run_command`) :
  modal d'approbation. La boîte de dialogue propose trois options en plus
  du refus :
  - *Autoriser une fois* — exception pour cet appel uniquement.
  - *Autoriser pour ce fichier* — auto-approuve les futurs appels du même
    outil sur le même chemin pour le reste de la session (indisponible
    pour `run_command`).
  - *Tout autoriser pour `<outil>` dans cette session* — auto-approuve
    l'outil partout jusqu'à la déconnexion.
- Les approbations sont réinitialisées à chaque reconnexion.

### Cartes d'outils dans le chat

Chaque appel d'outil s'affiche comme une carte pliable avec une bordure
gauche colorée :

- **Orange** — en cours.
- **Indigo** — en attente d'approbation.
- **Vert** — terminé.
- **Rouge** — erreur.
- **Gris** — refusé par l'utilisateur.

Cliquez sur l'en-tête pour déplier les arguments JSON et la sortie
capturée (stdout/stderr pour les commandes shell, diffs de fichiers pour
les éditions, etc.).

### Mémoire de conversation

Le contexte agentique est conservé pour toute la session WebSocket. Vous
pouvez dire *« maintenant édite le fichier que tu viens de lire »* et le
modèle se souviendra des appels d'outils précédents. Une reconnexion
démarre une nouvelle conversation agentique.

## Fonctionnalités espace de travail

- **Attache automatique du fichier actif** — toggle dans le header du
  chat. Chaque message envoyé uploadera silencieusement le fichier
  actuellement actif dans l'éditeur. Pratique quand vous voulez que le
  modèle suive ce sur quoi vous travaillez.
- **Envoyer la sélection** — palette → *My_AI Relay : Envoyer la
  sélection à My_AI*, ou clic droit dans l'éditeur. Encadre la sélection
  avec le langage courant pour un rendu propre.
- **Envoyer le fichier actif** — palette → *My_AI Relay : Envoyer le
  fichier actif à My_AI*. Upload le fichier entier comme pièce jointe
  (PDF, DOCX, code, image, etc.).
- **Insérer au curseur / Copier** — chaque bloc de code d'une réponse IA
  reçoit ces deux boutons au survol.

## Commandes

| Commande | Description |
| --- | --- |
| `My_AI Relay : Se connecter` | Coller une chaîne de connexion et démarrer une session. |
| `My_AI Relay : Se déconnecter` | Fermer la session courante (garde les identifiants). |
| `My_AI Relay : Oublier la connexion enregistrée` | Supprime les identifiants du SecretStorage. |
| `My_AI Relay : Envoyer la sélection à My_AI` | Envoie la sélection comme message. |
| `My_AI Relay : Envoyer le fichier actif à My_AI` | Upload et envoie le fichier courant. |
| `My_AI Relay : Activer / désactiver l'attache automatique du fichier actif` | Bascule la fonctionnalité. |
| `My_AI Relay : Ouvrir le chat` | Affiche le panneau de chat. |
| `My_AI Relay : Déplacer le chat vers la barre latérale secondaire` | Ouvre le sélecteur « Déplacer la vue » de VS Code pré-positionné sur la vue chat. |

## Réglages

| Réglage | Défaut | Description |
| --- | --- | --- |
| `myaiRelay.openInSecondarySidebar` | `true` | Au premier lancement, propose de déplacer le chat dans la barre latérale secondaire. |
| `myaiRelay.healthCheckIntervalSeconds` | `10` | Intervalle de polling de la santé des tunnels (secondes). |
| `myaiRelay.autoReconnect` | `true` | Reconnecter automatiquement quand le Relay hôte redémarre. |
| `myaiRelay.requestTimeoutSeconds` | `15` | Timeout HTTP par requête. |

## Modèle de sécurité

- La chaîne de connexion contient la clé AES. Quiconque y a accès peut
  déchiffrer tous les messages de cette session Relay. **Ne la partagez
  pas.**
- Les identifiants sont persistés dans le
  [`SecretStorage`](https://code.visualstudio.com/api/references/vscode-api#SecretStorage)
  de VS Code — chiffrés par le keychain de l'OS, scopés par machine et
  utilisateur.
- Le serveur de tunnel (Cloudflare / serveo / localhost.run) ne voit que
  du ciphertext. L'IP de votre PC hôte est masquée derrière le tunnel.
- Arrêter le Relay sur le PC hôte invalide la clé de chiffrement et les
  tunnels. L'extension le détecte sous ~30 s et passe en « hors ligne ».
- **Isolation du workspace.** Le mode agentique exécute tous les outils
  côté client à l'intérieur de l'extension VS Code. L'accès complet au PC
  hôte (les MCP locaux utilisés par l'interface desktop GUI et l'UI
  mobile) **n'est pas** atteignable depuis le chat VS Code. Le modèle ne
  peut toucher qu'aux fichiers accessibles via les outils workspace,
  eux-mêmes bornés à la racine du workspace et protégés par le flux
  d'approbation.

## Dépannage

- **« Aucun tunnel joignable »** — le PC hôte est hors ligne, le Relay a
  été arrêté, ou votre réseau local bloque les trois providers. Essayez
  de relancer le Relay.
- **« Échec du déchiffrement E2EE »** — la chaîne de connexion vient
  d'une session Relay précédente (la clé AES est régénérée à chaque
  démarrage du Relay). Copiez une nouvelle chaîne et reconnectez-vous.
- **Health check trop sensible** — augmentez
  `myaiRelay.healthCheckIntervalSeconds` si votre lien est instable.

## Développement

```bash
cd vscode_extension
npm install
npm run watch       # esbuild en mode watch
# Appuyez sur F5 dans VS Code pour lancer un host d'extension
```

Packager un VSIX :

```bash
npm run package
```

## Licence

[MIT](./LICENSE) © gonicolas12
