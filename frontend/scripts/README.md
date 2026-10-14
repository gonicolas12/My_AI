# Outils de vérification de l'interface web

Scripts Playwright (dans ce dossier) et outils Python (`tools/interface_web/`) qui ont servi à
vérifier les phases 2 et 3 de la migration (`docs/MIGRATION_INTERFACE_WEB_SUIVI.md`). Ils ne font pas partie
de l'appli. Les scripts se lancent depuis `frontend/`, après `npm ci` et
`npx playwright install chromium`. Les captures vont par défaut dans `frontend/captures/`, ignoré
par git.

## Sans Ollama : serveur de démonstration

Le vrai serveur local et le vrai `ChatService`, avec un moteur scénarisé (« long », « outils »,
« réflexion », « artefact », « document », « dessine »… : voir son en-tête). Il travaille sur une
copie de `data/workspaces` dans `temp/demo_server/PORT/` (ignoré par git, vidé à chaque lancement),
et n'écrit ni dans `data/` ni dans le `outputs/` du dépôt : notes en mémoire, copie de l'historique
des requêtes, voix simulée (sauf `--vraie-voix`). Les sessions « Projet API REST » et « Conversation
longue » de `capture.mjs` et `perf.mjs` viennent des données de test du suivi (section 4) : sans
elles, ces étapes sont sautées.

```powershell
python tools/interface_web/demo_server.py 8765   # depuis la racine du dépôt
# affiche DEMO http://127.0.0.1:8765/#token=…, l'URL à passer aux scripts
```

| Script                                                   | Rôle                                                                                                                                       |
| -------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------ |
| `node scripts/capture.mjs URL [DOSSIER] [L H]`           | captures des états clés : chargement, accueil, sessions, streaming, réflexion, outils, file, erreur…                                       |
| `node scripts/perf.mjs URL [scroll,stream,stress,gil]`   | images, tâches longues, latence des saisies, rendus React, cadence des jetons                                                              |
| `node scripts/tooltips.mjs URL`                          | infobulles : survol, départ, clics, Ctrl+B, sortie de la page                                                                              |
| `node scripts/follow_bottom.mjs URL`                     | le fil suit une longue réponse (distance au bas)                                                                                           |
| `node scripts/capture_chat.mjs URL [DOSSIER] [ÉTAPES]`   | parité du Chat (phase 3a) : artefacts, documents, chemins, citations, image, pièces jointes, `/`, édition, notes, voix, barre latérale     |
| `node scripts/capture_panels.mjs URL [DOSSIER] [ÉTAPES]` | panneaux (phase 3b) : assistant (serveur lancé avec `--premier-lancement`), Réglages, Mémoire, Prompts, Relay simulé, Aide, palette Ctrl+K |

Rendus React : servir un build de profilage, sans toucher à `dist/` :

```powershell
$env:VITE_REACT_PROFILE = 1; npx vite build --outDir ../temp/dist_profil; Remove-Item Env:VITE_REACT_PROFILE
python tools/interface_web/demo_server.py 8765 --dist temp/dist_profil   # depuis la racine du dépôt
```

## Vraie fenêtre (WebView2)

Lancer l'appli avec le port de débogage, puis piloter la page par CDP. Sans Ollama, la même fenêtre
s'ouvre sur le serveur de démonstration (`--window`) :

```powershell
$env:MY_AI_WEBVIEW_CDP_PORT = 9333; python launch_unified.py   # depuis la racine du dépôt
$env:MY_AI_WEBVIEW_CDP_PORT = 9333; python tools/interface_web/demo_server.py 8765 --window
```

Les scripts lisent la même variable (9333 par défaut).

| Script                                                | Rôle                                                                                                                                                            | Touches ou curseur du système    |
| ----------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------- |
| `node scripts/window_look.mjs [DOSSIER]`              | adresse, pont pywebview, captures du chargement et de l'accueil                                                                                                 | non                              |
| `node scripts/window_chat.mjs "QUESTION"`             | vraie réponse d'Ollama : images par seconde, premier texte, captures                                                                                            | non                              |
| `node scripts/window_preview.mjs [DOSSIER] [JOURNAL]` | sur le serveur de démonstration : artefact isolé du pont pywebview, lecteur PDF de WebView2                                                                     | non                              |
| `node scripts/window_native.mjs [DOSSIER]`            | sur le serveur de démonstration : visionneuse Word posée sur la place du volet, masquée sous la palette et les toasts qui la touchent, déchargée à la fermeture | non                              |
| `node scripts/tooltips.mjs --window`                  | infobulles, souris de Playwright                                                                                                                                | non                              |
| `node scripts/window_keys.mjs`                        | F5, Ctrl+R, Ctrl+P… ne rechargent, n'impriment ni ne cherchent rien                                                                                             | oui, touches                     |
| `node scripts/window_tooltips.mjs`                    | infobulle fermée quand le vrai curseur quitte la fenêtre                                                                                                        | oui, curseur                     |
| `node scripts/window_system.mjs [DOSSIER] [ÉTAPES]`   | sur le serveur de démonstration (`--window --vraie-voix`) : dialogues de Windows, glisser-déposer depuis l'Explorateur, voix, ouverture des fichiers            | oui, souris ; ouvre des fenêtres |

Les touches et le curseur du système vont à la fenêtre au premier plan, quelle qu'elle soit.
`tools/interface_web/win.py` attend donc que le clavier et la souris n'aient pas servi depuis
20 secondes (une minute au plus, puis il refuse), et n'envoie une touche que si My_AI est au premier
plan. Après avoir lancé l'un de ces trois scripts, ne plus toucher au clavier ni à la souris jusqu'à
la fin. `win.py` sert aussi seul : bornes, déplacement, fermeture,
capture avec la barre de titre (`python tools/interface_web/win.py` pour l'aide). `win.py capture`
prend la fenêtre sans la mettre au premier plan (PrintWindow) : seule capture où paraît le lecteur
PDF de WebView2, qui dessine hors de la page (gris dans les captures CDP).

`win.py dialog` remplit et valide un dialogue de fichiers ou de dossier ouvert par My_AI, par des
messages adressés au dialogue (ni focus ni saisie du système) ; `win.py drag` fait un vrai
glisser-déposer, après la même attente ; `win.py element` trouve un élément d'une fenêtre (UI
Automation), par exemple un fichier dans l'Explorateur ; `win.py windows` liste les fenêtres
visibles, `win.py close HWND` en ferme une.

Seul `window_system.mjs` clique « Ouvrir … » sur une carte de fichier, « Afficher dans
l'Explorateur », « Ouvrir dans le navigateur » et « Télécharger », PC laissé libre : ces boutons
lancent un programme du système (application par défaut, Explorateur, navigateur), qui prend le
premier plan, ou écrivent dans Téléchargements. Le script referme chaque fenêtre qu'il a vue
apparaître et supprime sa copie dans Téléchargements. Les autres scripts ne les cliquent jamais.

Le micro du PC à RTX 3060 (réseau Intel Smart Sound) annule l'écho : il n'entend pas ce que dit la
synthèse vocale du PC. `window_system.mjs` vérifie donc l'enregistrement et la transcription, pas
le texte : une vraie dictée se vérifie à la voix.

## Divers

- `python tools/interface_web/make_icon.py interfaces/desktop/assets/my_ai.ico [APERCU.png]` :
  icône de la fenêtre, le robot de l'extension VS Code dans la couleur `--accent`.
- Le banc de rendu Markdown de la phase 2 (react-markdown par blocs, Streamdown, react-markdown
  seul) n'est pas versé : il dépend de Streamdown, retiré des dépendances. Ses résultats sont dans le
  suivi (journal de la phase 2).
