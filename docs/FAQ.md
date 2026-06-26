# ❓ FAQ - My Personal AI

## 🤖 Questions Générales

### Mon IA est-elle vraiment 100% locale ?
Oui ! Absolument aucune donnée n'est envoyée à l'extérieur. Votre IA fonctionne entièrement sur votre machine sans connexion internet après installation. Vos conversations, documents et code restent complètement privés.

### Comment voir et supprimer ce que l'IA sait de moi ?
Ouvrez la sidebar (**☰**) → **🧠 Mémoire**. Vous y trouvez **tout** ce que l'IA a mémorisé, réparti en 3 onglets : **Faits** (base SQLite), **Documents** et **Conversations** (mémoire vectorielle ChromaDB). Vous pouvez **chercher, filtrer, éditer en ligne et supprimer** chaque entrée — ce sont de **vraies** suppressions locales (rien n'est simulé). Pour une entrée de conversation, cochez « supprimer aussi le message d'origine » pour que la suppression soit **définitive**. Détails : [MEMORY.md](MEMORY.md).

### Comment retrouver un ancien échange dans toutes mes conversations ?
Sidebar (**☰**) → section **🔎 Recherche globale**. La recherche est **sémantique** et porte sur **toutes** vos sessions à la fois (pas seulement la conversation ouverte). Un clic sur un résultat **ouvre la conversation source et surligne le passage**. Détails : [CONVERSATION_SEARCH.md](CONVERSATION_SEARCH.md).

### Comment utiliser des prompts réutilisables (slash commands) ?
Tapez **`/`** en début de saisie : un menu propose des commandes (`/code`, `/résume`, `/traduis`…). Vous tapez une **commande courte** (ex. `/code un jeu de morpion`) et l'IA reçoit un **prompt détaillé** — la bulle garde la commande courte. Gérez votre bibliothèque via le bouton **📚 Prompts** de la sidebar. Ça marche aussi sur mobile et dans VS Code. Détails : [PROMPT_LIBRARY.md](PROMPT_LIBRARY.md).

### Comment donner tout un dossier de code (ou de docs) à l'IA ?
Sidebar (**☰**) → section **📁 Dossiers du projet** → **Attacher un dossier** (ou menu **« + » → 📁 Dossier (codebase)**). L'IA garde ce dossier en contexte pour **toutes** les questions du workspace (RAG persistant). L'indexation est **incrémentale et 100% locale**, respecte votre `.gitignore` et ignore `node_modules`/`.git`/`.venv`… Dans **VS Code**, tapez **`@`** pour attacher fichiers/dossiers. Détails : [CODEBASE.md](CODEBASE.md).

### Ai-je besoin d'Ollama, OpenAI ou autres services ?
**Ollama est optionnel mais recommandé !**

| Configuration | Qualité des réponses | Installation |
|---------------|---------------------|--------------|
| **Avec Ollama** | LLM complet - conversations naturelles | Télécharger depuis ollama.com |
| **Sans Ollama** | Mode patterns/règles - fonctionnel mais basique | Rien à installer |

L'IA fonctionne dans les deux cas, mais Ollama offre des réponses beaucoup plus intelligentes et naturelles. **Aucun compte OpenAI ou service cloud n'est requis.**

### Comment changer de modèle Ollama ?

**Le plus simple : le panneau ⚙️ Réglages** (sidebar) → section *Modèles Ollama* → choisir ou télécharger un modèle → **Appliquer** : le modèle custom `my_ai` est régénéré automatiquement (system prompt préservé), sans toucher au moindre fichier.

Manuellement, trois étapes, dans l'ordre :

**Étape 1 — `config.yaml`** (pilote tout le code Python) :
```yaml
llm:
  local:
    default_model: "qwen3.5:2b"  # ← nouvelle valeur
```

**Étape 2 — `Modelfile`** (doit correspondre à `config.yaml`) :
```
FROM qwen3.5:2b   # ← même valeur
```

**Étape 3 — Terminal** :
```bash
ollama pull qwen3.5:2b
.\create_custom_model.bat
```

> ⚠️ `config.yaml` et `Modelfile` doivent toujours avoir la **même valeur**. `config.yaml` contrôle le code Python, `Modelfile` contrôle la construction du modèle custom `my_ai` dans Ollama.

### Comment installer Ollama ?
1. Téléchargez depuis **https://ollama.com/download**
2. Installez le modèle : `ollama pull qwen3.5:4b`
3. Créez le modèle personnalisé : `.\create_custom_model.bat`

L'application détecte automatiquement Ollama au démarrage.

### Quel modèle Ollama choisir selon mon matériel ?

L'**assistant de configuration** (premier lancement) et le panneau ⚙️ Réglages recommandent automatiquement, en **privilégiant la fluidité** :

**Avec un GPU dédié** (le modèle tourne en VRAM → rapide) :

| VRAM | Modèle |
|------|--------|
| 4–6 Go | qwen3.5:2b |
| 6–10 Go | qwen3.5:4b |
| ≥ 10 Go | qwen3.5:9b |

**Sans GPU dédié** (inférence CPU — la **vitesse du CPU** est le facteur limitant, pas la RAM) :

| CPU | Modèle |
|-----|--------|
| PC bureautique (< 8 cœurs) | qwen3.5:2b |
| Desktop costaud (≥ 8 cœurs **et** ≥ 16 Go RAM) | qwen3.5:4b |

> ⚠️ En CPU, on évite les gros modèles (9b/27b) : ils « rentrent » en RAM mais génèrent **trop lentement** pour un usage agréable. Un gros modèle n'a d'intérêt qu'avec un GPU disposant d'assez de VRAM.

### Mes données restent-elles confidentielles avec Ollama ?
**Oui, 100% !** Ollama exécute le modèle **localement sur votre PC**. Aucune donnée n'est envoyée sur internet. C'est l'avantage principal par rapport à ChatGPT ou Claude.

### Quelle est la différence avec ChatGPT ou Claude ?

- **Confidentialité** : Vos données restent sur votre machine
- **Pas d'abonnement** : Gratuit une fois installé
- **Spécialisé** : Optimisé pour l'aide au développement et l'analyse de documents
- **Mémoire locale** : Se souvient de vos documents et conversations, mais stocke tout localement
- **Open source** : Le code est entièrement accessible, modifiable et vérifiable par tous

## 🔧 Installation et Configuration

### Quels sont les prérequis pour installer l'IA ?
 
- Python 3.8+ (3.10+ recommandé)
- 4 GB RAM minimum (8 GB recommandé)
- ~100 MB d'espace disque
- Windows, macOS ou Linux

### L'installation est-elle compliquée ?
Non ! Installation en 3 commandes :
```bash
cd My_AI
pip install -r requirements.txt
.\launch.bat
```

**Pour Ollama (optionnel mais recommandé) :**
```bash
# Télécharger depuis https://ollama.com/download
ollama pull qwen3.5:4b
.\create_custom_model.bat
```

### Que faire si l'installation échoue ?
Vérifiez :
1. Version de Python : `python --version` (doit être 3.8+)
2. Dépendances : `pip install -r requirements.txt`
3. Permissions : Exécutez en administrateur si nécessaire
4. Consultez les logs dans le dossier `logs/`

## 💬 Utilisation et Fonctionnalités

### Comment l'IA reconnaît-elle mes intentions ?
L'IA analyse vos messages et détecte automatiquement :
- **Salutations** : "slt", "bonjour", "bjr", "hello"
- **Questions techniques** : Code, programmation, debug
- **Questions sur documents** : Après traitement d'un PDF/DOCX
- **Conversation générale** : Discussion libre

### Comment traiter des documents PDF ou DOCX ?

1. **Interface graphique** : Glissez le fichier dans la zone de conversation
2. **Ligne de commande** : `python main.py process votre_document.pdf`
3. **Questions** : Ensuite, tapez "résume ce document" ou posez des questions spécifiques

### L'IA se souvient-elle de ce que je lui dis ?
Oui ! L'IA garde en mémoire :
- Les documents que vous avez traités
- Le code que vous avez analysé
- Le contexte pour des réponses cohérentes

### Comment effacer l'historique et repartir à zéro ?
Utilisez le bouton "Clear Chat" dans l'interface graphique, ou redémarrez l'application. Cela efface complètement la conversation et la mémoire.

## 🐛 Dépannage

### L'IA ne démarre pas, que faire ?

1. Vérifiez Python : `python --version`
2. Réinstallez les dépendances : `pip install -r requirements.txt`
3. Vérifiez les logs : dossier `logs/`
4. Essayez en mode debug : `python main.py --debug`

### Les fichiers PDF/DOCX ne se chargent pas

- Vérifiez que le fichier n'est pas corrompu
- Essayez en ayant votre fichier fermé
- Essayez avec un autre fichier
- Vérifiez l'espace disque disponible
- Redémarrez l'application

### L'IA donne des réponses étranges ou incohérentes

- Utilisez "Clear Chat" pour remettre à zéro
- Vérifiez que votre question est claire
- Essayez de reformuler différemment
- **Si Ollama est installé** : Vérifiez qu'il tourne (`ollama list`)
- **Si mode fallback** : Les réponses sont basées sur des patterns, moins naturelles
- Consultez les logs pour diagnostic

### Ollama ne fonctionne pas, que faire ?

1. Vérifiez qu'Ollama est lancé : `ollama list`
2. Testez manuellement : `ollama run qwen3.5:4b "Bonjour"`
3. Vérifiez le port : `curl http://localhost:11434`
4. Redémarrez Ollama si nécessaire
5. L'application fonctionnera en mode fallback si Ollama est indisponible

### L'interface graphique ne s'affiche pas

- Vérifiez que Tkinter est installé : `python -m tkinter`
- Utilisez l'interface CLI : `python launcher.py gui`
- Sur Linux, installez : `sudo apt-get install python3-tk`

## 📚 Fonctionnalités Avancées

### L'IA peut-elle générer du code ?
Oui ! L'IA peut :
- Générer des fonctions Python
- Expliquer du code existant
- Suggérer des améliorations
- Détecter des problèmes
- Proposer des alternatives

### L'IA peut-elle générer des images ?
Oui, 100% en local (texte → image). Demandez simplement « génère une image de… », « dessine-moi… » ou « crée un logo… » : l'image apparaît dans le chat et est sauvegardée dans `outputs/`.

- **Zéro config :** au premier usage, si aucun backend n'est détecté, My_AI installe automatiquement **ComfyUI portable** (Windows/NVIDIA) + un modèle par défaut.
- **Autres options :** AUTOMATIC1111/Forge, ou `diffusers` (tous GPU + CPU). Voir [IMAGE_GENERATION.md](IMAGE_GENERATION.md).
- **Sans GPU :** ça fonctionne aussi sur CPU, mais comptez plusieurs minutes par image (préférez un modèle « Turbo »).
- À ne pas confondre avec l'**analyse** d'image (« décris cette image »), gérée par la vision Ollama.

### Puis-je utiliser l'IA en ligne de commande ?
Absolument ! 
```bash
# Mode interactif CLI
python main.py --cli

# Commande directe
python main.py chat "votre question"

# Traitement de fichier
python main.py process document.pdf
```

## 🔒 Sécurité et Confidentialité

### Mes données sont-elles vraiment sécurisées ?
Oui ! Garanties :
- **Pas de réseau** : Aucun envoi de données externes
- **Stockage local** : Tout reste sur votre machine
- **Code ouvert** : Architecture vérifiable
- **Pas de télémétrie** : Aucun tracking

### Puis-je utiliser l'IA pour des documents confidentiels ?
Absolument ! C'est même recommandé. Vos documents restent 100% sur votre machine, idéal pour :
- Documents d'entreprise confidentiels
- Code source propriétaire
- Données personnelles sensibles
- Informations légales ou médicales

### L'IA conserve-t-elle mes données après fermeture ?
Avec les **Workspaces v7.0.0**, oui ! Vos conversations sont sauvegardées automatiquement dans des espaces de travail isolés (`data/workspaces/`). Vous pouvez les charger à tout moment. Sans workspace, la mémoire de session est effacée à la fermeture.

## 🆕 Questions v7.0.0

### Comment utiliser l'API REST ?
Activez `api.enabled: true` dans `config.yaml`, puis accédez à `http://localhost:8000/api/health` pour vérifier que le serveur tourne. Tous les endpoints sont documentés dans [USAGE.md](USAGE.md#-api-rest-locale).

### Comment exporter une conversation ?
L'export se fait via le module `ConversationExporter`. Les formats disponibles sont Markdown (.md), HTML (.html, avec thème sombre) et PDF (.pdf). Les fichiers sont sauvegardés dans `outputs/exports/`.

### Comment fonctionne la base de connaissances ?
L'IA extrait automatiquement des faits depuis vos conversations (préférences, décisions, personnes, procédures, informations techniques). Ces faits sont stockés dans SQLite (`data/knowledge_base/facts.db`) avec un score de confiance. Les faits pertinents sont injectés dans le contexte des futures conversations.

### L'IA peut-elle répondre dans une autre langue ?
Oui ! Le `LanguageDetector` détecte automatiquement la langue de votre message parmi 12 langues (français, anglais, espagnol, allemand, italien, portugais, néerlandais, russe, chinois, japonais, coréen, arabe) et génère un suffix de prompt système pour que l'IA réponde dans la même langue.

### Comment attacher des fichiers aux agents ?
Cliquez sur le bouton **"+"** dans la zone de saisie de l'onglet Agents, sélectionnez vos fichiers, et ils seront automatiquement lus et injectés dans le prompt de l'agent. Dans un workflow multi-agents, tous les agents reçoivent les fichiers joints.

### L'IA demande-t-elle confirmation avant de supprimer un fichier ?
Oui ! Depuis la v7.0.0, quand l'IA utilise l'outil MCP `delete_local_file`, une fenêtre de confirmation s'affiche avec le chemin du fichier. Vous devez explicitement cliquer "Oui, supprimer" pour autoriser la suppression.

### Les nouveaux modules v7.0.0 sont-ils obligatoires ?
Non ! Tous les modules v7.0.0 sont **optionnels** avec dégradation gracieuse. Si une dépendance est manquante (ex: `fastapi` pour l'API REST, `langdetect` pour la détection de langue), un warning est loggé et le module est désactivé. Le reste de l'application fonctionne normalement.

### Comment fonctionne le nouveau système de feedback par étoiles ?
Depuis la v7.0.0, les boutons 👍/👎 ont été remplacés par une **notation 1-5 étoiles** (☆☆☆☆☆). Après chaque réponse de l'IA, survole les étoiles pour un aperçu visuel, puis clique pour valider ta note. Le feedback est enregistré automatiquement dans `data/rlhf_feedback.db`. Pour en savoir plus : [GUI_RLHF_FEEDBACK.md](GUI_RLHF_FEEDBACK.md).

### Puis-je sauvegarder et réutiliser un workflow d'agents ?
Oui ! Dans l'onglet Agents, le canvas visuel dispose de boutons **💾 Sauvegarder** (export JSON) et **📂 Charger** (import JSON). Tu peux construire un workflow complexe, le sauvegarder dans un fichier `.json`, et le recharger à n'importe quelle session pour le relancer immédiatement. Un bouton **📤 Export** permet aussi d'exporter les résultats d'exécution en Markdown.

## 🎙️ Saisie Vocale (Voice Mode)

### Comment dicter mes prompts au lieu de les taper ?
Depuis la **v7.4.0**, un bouton micro (🎙) est présent en haut-droite de chaque zone de saisie (chat accueil, chat conversation, onglet Agents). Toggle : clic = démarrer l'enregistrement (icône rouge avec pulsation), reclic = arrêter et lancer la transcription. Le texte transcrit s'insère au curseur de la zone active. La langue est auto-détectée (99+ langues), donc tu peux passer du français à l'anglais sans rien configurer.

### Ma voix est-elle envoyée quelque part ?
**Non**, tout est 100% local. La transcription utilise **faster-whisper** (une implémentation optimisée de Whisper d'OpenAI) qui tourne entièrement sur ton CPU. Aucune connexion réseau n'est faite pendant la dictée. Le seul cas où il y a une connexion : le **premier téléchargement** du modèle Whisper `small` (~150 Mo) depuis HuggingFace, qui se fait automatiquement au premier clic sur le micro. Ensuite, tout est en cache local.

### Pourquoi le premier usage est-il plus lent ?
La première dictée déclenche le chargement du modèle Whisper en mémoire (~5 secondes). Les transcriptions suivantes sont quasi-instantanées tant que l'application reste ouverte. Le modèle reste partagé entre tous les onglets (chat + agents) — pas de double chargement.

### Quel modèle Whisper est utilisé et puis-je le changer ?
Par défaut : `small` (~150 Mo, INT8 quantizé pour CPU). Bon compromis qualité/vitesse pour la majorité des cas. Si tu veux changer (par ex. `base` plus rapide ou `medium`/`large-v3` plus précis), édite la constante `MODEL_SIZE` dans `interfaces/gui/voice_input.py`. Les modèles disponibles : `tiny`, `base`, `small`, `medium`, `large-v3`.

### Le bouton micro ne fait rien quand je clique
Trois causes possibles :
1. **Dépendances manquantes** : installe `pip install faster-whisper sounddevice` (déjà inclus dans `requirements.txt`). Une notification d'erreur apparaît dans le GUI si c'est le cas.
2. **Pas de micro détecté** : vérifie que ton OS reconnaît un micro par défaut (Paramètres → Son → Entrée).
3. **Durée trop courte** : les enregistrements de moins de 0,3 seconde sont ignorés (anti-clic accidentel).

### Le micro fonctionne sur Linux/macOS ?
Oui, mais `sounddevice` requiert la librairie système `portaudio` :
- **Debian/Ubuntu** : `sudo apt install libportaudio2`
- **macOS** : `brew install portaudio`
- **Windows** : rien à installer (embarqué dans le wheel)

### Puis-je désactiver la saisie vocale ?
Le bouton micro est toujours présent mais purement opt-in : si tu ne cliques jamais dessus, aucune ressource n'est consommée (le modèle Whisper est chargé en lazy). Si tu veux le masquer complètement, retire les appels à `attach_mic_button` dans `interfaces/gui/layout.py`, `interfaces/gui/base.py` et `interfaces/agents/task_input.py`.

### Puis-je faire lire les réponses à voix haute ?
Oui. Un bouton **🔊** apparaît sous chaque réponse de l'IA (clic = lecture, reclic = stop), et un toggle **« Lecture auto »** dans la sidebar lit automatiquement chaque nouvelle réponse. C'est **100% local** via **pyttsx3** (moteur de synthèse de l'OS, aucun téléchargement). La voix est choisie selon la **langue détectée** de la réponse (pas d'accent anglais sur du français). Sous Linux, installe `espeak-ng` (`sudo apt install espeak-ng`) ; Windows et macOS fonctionnent d'origine.

## 🚀 Évolutions et Support

### L'IA va-t-elle s'améliorer avec le temps ?
Oui ! Évolutions prévues :
- Application web
- Intégrations API tierces
- Enrichissement de l'extension VS Code (intégration aux diagnostics VS Code, application de diffs visuels avant/après pour les éditions, terminaux dédiés pour `run_command`)

### Existe-t-il une extension VS Code ?
Oui, et elle est **agentique façon Claude Code**. L'extension officielle **My_AI Relay** est publiée sur le **Marketplace VS Code** sous l'identifiant `gonicolas12.my-ai`. Elle se connecte à votre instance Relay via le même tunnel chiffré que l'interface mobile, mais avec un comportement très différent : à la connexion, elle s'identifie comme client `vscode` et active une **boucle de raisonnement** qui permet au LLM local de **lire, modifier, créer des fichiers, lancer des commandes shell et chercher dans le workspace VS Code**. Chaque appel d'outil s'affiche comme une carte pliable dans le chat, et les opérations destructives (écriture, édition, commande shell) demandent l'approbation de l'utilisateur. Le LLM est sandboxé au workspace par défaut — il ne voit pas le reste du PC hôte (à l'inverse du GUI desktop ou du mobile, qui ont accès aux MCP locaux complets). Le chat classique avec attachements/auto-attache reste également disponible. Voir [`vscode_extension/README.fr.md`](../vscode_extension/README.fr.md) pour la doc complète.

### Le mode agentique de l'extension peut-il casser mon workspace ?
En théorie non : tous les chemins sont résolus par rapport à la racine du workspace VS Code ouvert ; toute tentative de sortie (lecture/écriture en dehors) déclenche un modal d'approbation par chemin. Les outils `write_file`, `edit_file` et `run_command` demandent toujours confirmation avant exécution la première fois. En pratique : utilisez git, c'est ce qu'on fait avec n'importe quel assistant de codage. Vous pouvez voir précisément ce que le LLM a fait via les cartes d'outils dans le chat (input + output capturés).

### Le mobile et le GUI desktop sont-ils impactés par le mode agentique ?
Non. Le routage côté Relay distingue les clients par leur message `client_hello` : seul un client qui s'annonce comme `client_kind: "vscode"` passe par la boucle agentique. Le mobile et la GUI desktop continuent d'utiliser le pipeline historique avec les MCP locaux complets (accès PC entier).

### Puis-je utiliser les agents IA depuis mon téléphone ?
Oui. L'interface mobile My_AI Relay propose une barre d'onglets **💬 Chat / 🤖 Agents** en haut. L'onglet Agents reprend toute la page Agents du PC en version tactile : grille des 9 agents spécialisés + vos agents personnalisés, **création/édition/suppression d'agents**, **workflow visuel n8n** (déplacer les nœuds au doigt, relier les ports), **Mode Débat** et exécution streamée. Les agents s'exécutent **côté PC** (orchestrateur + Ollama local) et le résultat est streamé au mobile dans le tunnel chiffré — rien ne part vers un cloud. Vous pouvez aussi joindre des fichiers/images à une tâche d'agent via le bouton **+**, comme sur le chat. Les agents personnalisés sont partagés avec le GUI desktop (même `data/custom_agents.json`).

### Sur mobile, comment arrêter une réponse en cours de génération ?
Pendant la génération, le **bouton d'envoi du chat se transforme en bouton Stop** (carré noir sur fond blanc). Le toucher interrompt la génération : la demande remonte au PC qui arrête le streaming et renvoie la réponse partielle. Sur la page Agents, le bouton **▶ Exécuter** devient **■ Stop** pendant un workflow ou un débat.

### Puis-je contribuer au développement ?
Bien sûr ! Le projet est ouvert aux contributions :
- Rapporter des bugs
- Proposer des fonctionnalités
- Améliorer la documentation
- Ajouter des exemples d'usage

### Où trouver de l'aide supplémentaire ?

- **Documentation** : Dossier `docs/`
- **Exemples** : Dossier `examples/`
- **Logs** : Dossier `logs/` pour diagnostic
- **Code source** : Architecture complètement ouverte

---

💡 **Question non listée ?** Envoyez-moi un message sur mon **LinkedIn : [Nicolas Gouy](https://www.linkedin.com/in/nicolas-gouy/)**

🤖 **My Personal AI** - Votre assistant local intelligent et sécurisé
