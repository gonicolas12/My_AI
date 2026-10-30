# Tournage des captures (vidéo 9.1.0)

Ces scripts sont ceux de la 9.1.0, tels qu'ils ont tourné : un exemple à adapter (scénario, messages, choix des images), pas un outil fini.

Ils travaillent dans un dossier `S`, le scratchpad de la session, organisé ainsi :

```
S/scripts/                       ce dossier : les .cjs prennent S = dossier parent
S/workspace/bibliotheque-api/    projet_demo/, dans un dépôt git
S/kit/raw/                       sortie de capture.cjs (PNG et meta.json)
S/kit/pour_claude_web/           sortie de build_kit.py
```

## Ce qui tourne pour de vrai

- **La fenêtre du PC :** `harness.py` lance, sans Ollama :
  - le serveur de démonstration (`tools/interface_web/demo_server.py`) ;
  - le vrai Relay sur 127.0.0.1, sans tunnel ;
  - la conversation Code (CodeHub), avec une boucle agentique scénarisée. Les réponses sont écrites d'avance, mais les outils (lecture, modification, commande) s'exécutent pour de vrai dans l'extension VS Code.
- **VS Code :** le serveur officiel « VS Code Server for web » (paquet `server-linux-x64-web`), avec la vraie extension empaquetée depuis `vscode_extension/`.
- **Le téléphone :** la page du Relay ouverte dans Chromium, en 390 × 844 à l'échelle 3.
- **Les échelles :** PC et VS Code en 1440 × 900 à l'échelle 2, soit des captures de 2880 × 1800.

## Étapes

1. **Dépendances.**
   - Paquets Python :
     ```bash
     pip install fastapi "uvicorn[standard]" websockets python-multipart "qrcode[pil]" croniter aiohttp aiofiles rich psutil markdown markdown2 tenacity validators regex colorama python-dateutil beautifulsoup4 requests pytest httpx
     ```
   - `langdetect` ne s'installe pas, mais n'est pas nécessaire ici.
   - Playwright et Chromium sont déjà installés dans les sessions cloud.
2. **Projet de démo.**
   - Copier `projet_demo/` dans `S/workspace/bibliotheque-api`.
   - Faire `git init` et un premier commit, avec « Nicolas » comme auteur.
   - Ajouter `.vscode` dans `.git/info/exclude`.
3. **VS Code Server for web.** L'URL du paquet est donnée par `https://update.code.visualstudio.com/api/update/server-linux-x64-web/stable/latest`. L'extraire dans `S/vscode/`.
4. **Extension.**
   - Depuis `vscode_extension/`, empaqueter l'extension :
     ```bash
     npx @vscode/vsce package --no-dependencies --skip-license -o S/my-ai.vsix
     ```
   - L'installer :
     ```bash
     code-server --install-extension S/my-ai.vsix --extensions-dir S/vscode-ext --server-data-dir S/vscode-data
     ```
5. **Lancement**, chaque commande en tâche de fond.
   - Depuis la racine du repo :
     ```bash
     LANG=fr_FR.UTF-8 PYTHONDONTWRITEBYTECODE=1 VIDEO_RATE=26 python3 S/scripts/harness.py 8770 S/demo_tmp S/relay_info.json
     ```
   - Démarrer le Relay, ce qui écrit `relay_info.json` :
     ```bash
     curl -X POST -H "Authorization: Bearer videotoken" -H "Content-Type: application/json" -H "Origin: http://127.0.0.1:8770" -d '{"tunnel": false}' http://127.0.0.1:8770/api/relay/start
     ```
   - Depuis le projet de démo, lancer VS Code :
     ```bash
     S/vscode/vscode-server-linux-x64-web/bin/code-server --host 127.0.0.1 --port 8000 --without-connection-token --accept-server-license-terms --server-data-dir S/vscode-data --extensions-dir S/vscode-ext --telemetry-level off
     ```
6. **Préparation de VS Code**, une seule fois, dans le profil Chromium persistant `S/chrome-vscode` :
   1. `node vscode_setup.cjs` : dossier de confiance et réglages ;
   2. `node vscode_connect.cjs` : connexion de l'extension au Relay ;
   3. `node vscode_layout3.cjs` : le chat My_AI seul dans la barre latérale droite, d'environ 460 px.
7. **Tournage.**
   - `node capture.cjs` fait tout le tournage, dans cet ordre :
     1. la barre latérale avant et après ;
     2. PC → VS Code ;
     3. VS Code → PC ;
     4. téléphone → VS Code ;
     5. VS Code → téléphone.
   - `node measure_pop.cjs` donne les mesures au pixel pour le pop.
8. **Kit.** `python3 build_kit.py S` sélectionne les images, les renomme dans l'ordre du récit et écrit la fiche technique.

## Pièges rencontrés

- **Réglages ignorés :** VS Code ignore les réglages « Machine » pour la confiance et la page d'accueil. Il faut passer par l'interface, dans un profil persistant (`vscode_setup.cjs`).
- **Vues déplacées :** « View: Move View » a déplacé Problèmes et Sortie par erreur. Correction :
  1. « View: Reset View Locations » ;
  2. clic droit sur l'icône My_AI → Move To → Secondary Side Bar.
- **Panneau du bas qui reste ouvert :** « View: Hide Panel », sinon Ctrl+J.
- **Défilement de l'éditeur :** il revient à l'ancienne position. Faire Ctrl+Home, puis deux fois flèche bas.
- **Réponse en cours d'écriture :** une capture peut tomber en plein streaming. Attendre que le texte dépasse 200 caractères.
- **Recherche de lignes dans l'éditeur :** remplacer d'abord les espaces insécables (` `).
- **Images « avant » et « après » d'un bouton :** pour l'image « avant », masquer l'élément dans le DOM ; tout le reste garde le même état.
- **Sortie de pytest :** garder `addopts = "-p no:asyncio -p no:cacheprovider"` pour qu'elle soit propre à l'écran.
- **Sélecteurs, à revérifier à chaque version :**
  - accord sur le téléphone : `.tool-approval-btn.primary` ;
  - chat de l'extension : `iframe.webview.ready` → `iframe#active-frame`.
