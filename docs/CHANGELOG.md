# 📋 CHANGELOG - My Personal AI

# 🎨 Version 7.8.0 — Génération d'images locale (19 Juin 2026)

### La symétrie multimodale est complète : l'IA *voit* ET *dessine*

My_AI gérait déjà l'**entrée vision** (décrire une image via Ollama `minicpm-v`/`llava`). Cette version ajoute la **sortie image** : demandez « *génère une image de…* » et l'IA produit l'image, l'affiche dans le chat (desktop **et** mobile) et la sauvegarde dans `outputs/`. Le tout **100% local**.

## 🖼️ Backend Stable Diffusion local — `models/image_generation.py` (nouveau)

- **Backend configurable** (`config.yaml` → `image_generation:`) calqué sur le pattern Ollama de `LocalLLM` : on parle à un service Stable Diffusion **local en HTTP**.
  - **`automatic1111`** (défaut, recommandé) : API AUTOMATIC1111 / **Forge** WebUI (`/sdapi/v1/txt2img`), démarrée avec `--api`. Forge + `--medvram` conseillé sur **6 Go VRAM** ; coexiste avec Ollama via services séparés.
  - **`comfyui`** : API ComfyUI (workflow txt2img par graphe, `/prompt` + `/history`).
  - **`diffusers`** : pipeline Python en process (optionnel) — détection automatique de device **tous GPU** : NVIDIA/AMD (CUDA/ROCm), **Apple Silicon** (MPS), **Intel Arc** (XPU), **DirectML** (Windows), repli **CPU** universel.
  - **`auto`** : essaie `automatic1111` puis `comfyui` puis `diffusers`.
- **Dégradation propre** : si aucun backend n'est joignable, message clair expliquant comment en lancer un (exactement comme le fallback Ollama existant) — **aucun crash**.
- **Indicateur de progression** : poll `/sdapi/v1/progress` (A1111) / `/history` (ComfyUI) → barre d'avancement dans l'UI (génération = opération lourde).
- **Aucune dépendance ajoutée** au socle : les backends HTTP n'utilisent que `requests` (déjà présent) ; `diffusers` reste optionnel.

## 🎯 Détection d'intention & routage

- Nouvelle intention **`image_generation`** dans `models/linguistic_patterns.py` (« génère/dessine/crée une image/illustration/logo… »), **distincte** de la génération de code et de l'**analyse** d'image (vision) qui reste intacte.
- Routage dans `core/ai_engine.py` (`process_query_stream` et `process_query`) : court-circuit prioritaire sur MCP, extraction du prompt pictural, callbacks `on_image` / `on_image_progress`.

## 🖥️ Affichage desktop & 📱 mobile (E2EE)

- **Desktop** — l'image générée s'affiche **dans la même bulle** que le texte « Voici l'image générée… » (une seule icône 🎨), avec aperçu **cliquable** (ouverture en taille réelle). Le rendu **`**gras**`** du message est interprété dans la bulle.
- **Contexte LLM** — la génération est inscrite dans l'historique du modèle local : si on demande ensuite « de quoi on a parlé ? », l'IA **sait** qu'elle a généré une image.
- **Mobile (Relay)** — l'image transite **chiffrée AES-256-GCM** : `relay/relay_server.py` `_broadcast_image()` l'envoie dans un événement WS `ai_image` via `encrypt_json()` (même enveloppe E2EE que les pièces jointes) ; `relay/static/app.js` l'affiche en `data:` URI (**jamais en clair sur le réseau**).

## ⚙️ Installation automatique (zéro config) — `models/comfyui_manager.py` (nouveau)

Par défaut (`image_generation.auto_setup: true`), **rien à installer manuellement** : à la **première** demande d'image sans backend détecté, My_AI télécharge et lance automatiquement **ComfyUI portable** (Windows/NVIDIA, **Python + CUDA embarqués** — n'altère pas l'environnement de My_AI), récupère un **modèle par défaut** (SD-Turbo) et bascule dessus. Même esprit que le téléchargement auto de cloudflared pour le tunnel.

## ✨ Expérience de génération (animation, STOP, annulation)

- **Animation « 🎨 Génération de l'image en cours… »** dans une bulle dédiée (points + **% de progression**, et **% de téléchargement** pendant l'auto-installation).
- Le **bouton STOP reste actif** pendant toute la génération (comme un message en cours d'écriture) ; le message **se finalise** seulement à la fin, puis l'**image s'affiche** directement dans le chat.
- **Annulation conjointe** : un clic sur STOP arrête le **message ET la génération** (interruption propagée au backend : `/sdapi/v1/interrupt` A1111, `/interrupt` ComfyUI, `_interrupt` diffusers) — y compris pendant le téléchargement de l'auto-installation.

> Détails, installation des backends et compromis VRAM : [docs/IMAGE_GENERATION.md](IMAGE_GENERATION.md).

---

# 🎨 Version 7.7.0 — Artifacts live & Scheduler proactif (18 Juin 2026)

### Voir le rendu en direct, et laisser l'IA travailler toute seule

Deux grandes nouveautés : un **panneau Artifacts** qui affiche le rendu **live** du HTML/CSS/SVG généré par l'IA (façon *Claude Artifacts*), et un **scheduler proactif** qui exécute vos agents et workflows **automatiquement, de façon récurrente** (type cron). Le tout **100% local**.

## 🎨 Aperçu Artifacts (HTML / CSS / SVG)

Quand l'IA produit du HTML/CSS/SVG, un volet de **prévisualisation live** s'ouvre à côté du chat — sur le **GUI desktop** et sur le **mobile Relay**.

#### Desktop — `interfaces/gui/artifacts_panel.py`, `interfaces/gui/_edge_embed.py` (nouveaux)

- Bouton **« 🔍 Aperçu »** sous chaque réponse IA contenant un artifact rendable.
- **Rendu Chromium EXACT via Edge `--app` embarqué** : la fenêtre Edge est ré-parentée dans un volet redimensionnable (Win32 `SetParent`, barre de titre masquée) — **sans aucune dépendance Python supplémentaire** (réutilise Edge/WebView2 déjà installés).
- **Replis automatiques** : `tkinterweb` (pur Python, rendu approximatif) puis code source + bouton 🌐. L'embarquement exact est Windows-only.
- Bulles IA **responsives** : hauteur recalculée au redimensionnement du volet.

#### Mobile (Relay) — `relay/static/app.js`

- Aperçu via **`<iframe sandbox>`** (`srcdoc`, sans `allow-same-origin`) : isolation forte, **aucune requête réseau** ; bouton **« 🌐 »** pour ouvrir dans un onglet via un `Blob` local.

#### Détection partagée — `interfaces/artifacts.py` (nouveau)

- Réutilise les blocs de code Markdown : rend `html` / `svg` (ou contenu ressemblant à du HTML/SVG), ignore JSON/Python/etc. La logique JS du mobile est un miroir exact.

> Détails et compromis du moteur : [docs/ARTIFACTS_PREVIEW.md](ARTIFACTS_PREVIEW.md).

## 📅 Scheduler proactif (tâches planifiées)

Jusqu'ici l'assistant était **réactif** : vous lanciez chaque agent, workflow ou débat à la main. Cette version ajoute un **planificateur** (type cron) qui exécute vos agents **automatiquement et de façon récurrente**, puis vous notifie du résultat — sans réimplémenter l'exécution (elle est déléguée à l'`AgentRelayService` existant).

> Exemples : « chaque matin à 8h, WebAgent sur l'actu IA et résume », « tous les lundis, audit sécurité du dossier X », « toutes les heures, surveille … ».

#### 🧠 SchedulerService — `core/scheduler.py` (nouveau)

- **Boucle de thread maison** (daemon) qui vit tant que le **GUI** ou le **Relay** est lancé — 100% local, **aucun service système**.
- **Délègue l'exécution** à `relay/agent_relay.py` (`run_workflow` / `run_debate`) : single / séquentiel / parallèle / DAG / débat, via un *emit-collector* qui reconstruit le rapport final.
- **Persistance JSON** `data/scheduled_tasks.json` (écriture atomique, cohérent avec `data/custom_agents.json`) ; rapports `.md` dans `outputs/scheduled/`.
- **Plannings** : quotidien (`HH:MM`), hebdomadaire (jours + `HH:MM`), intervalle, **cron** (via `croniter`, optionnel — les presets fonctionnent sans).
- **Tâches manquées** (app fermée à l'heure prévue) : exécutées une fois au prochain démarrage si dans la fenêtre `catch_up_window_hours` et si `run_if_missed`.
- **Défer-on-busy** : si l'exécuteur est occupé (workflow lancé par l'utilisateur ou le mobile), l'exécution planifiée est différée au tick suivant → pas de double charge LLM concurrente sur Ollama.
- Singleton `get_scheduler()` (modèle `get_config()`), partage de l'exécuteur du Relay via `set_executor`.

#### 🖥️ Exécution en arrière-plan (appli fermée) — `core/scheduler_runner.py` (nouveau)

- Intégration optionnelle au **Planificateur de tâches Windows** : un **runner headless** s'exécute toutes les N minutes (`SchedulerService.run_once()`) et lance les tâches dues **même l'application fermée**, tant que la session Windows est ouverte — **sans droits admin ni mot de passe stocké**.
- Activable d'un clic depuis la page Agents (**« 🖥️ Exécuter même l'appli fermée »**) ou en CLI (`python core/scheduler_runner.py --register [N]`).
- **Verrou inter-processus** `data/scheduler.lock` (avec heartbeat) : le scheduler in-process (GUI/Relay) et le runner Windows ne lancent **jamais** la même tâche deux fois.
- Limite physique : ne couvre pas un PC **éteint / en veille** (les tâches manquées sont alors rattrapées au retour).

#### 🔌 Démarrage & notifications

- **GUI** (`interfaces/gui/base.py`) : démarrage au lancement + **toast in-app** non-bloquant (auto-effacé, clic = ouvre le rapport) — affiché seulement si l'OS n'a pas déjà montré de notification native.
- **Relay** (`relay/relay_server.py`) : démarrage dans `start()` en **partageant** son `AgentRelayService` (même gate `_busy` que le mobile) + **broadcast WebSocket** chiffré `scheduled_task_result` aux mobiles connectés. Le scheduler tourne donc aussi en **Relay standalone**.
- **Notification OS** native optionnelle via `winotify` / `plyer` (import optionnel, fallback in-app).

#### 🖥️ UI de gestion — `interfaces/agents/scheduler_ui.py` (nouveau)

- Section **📅 Tâches planifiées** en bas de la page **Agents** : liste (planning lisible, prochaine/dernière exécution, statut coloré), **activer/désactiver**, **▶ exécuter maintenant**, **📝 éditer**, **✕ supprimer**.
- **Dialogue créer/éditer** : source = *agent seul* / *workflow du canvas* (`WorkflowCanvas.to_dict()`) / *débat* ; prompt ; planning à paramètres dynamiques ; option *rattraper si manquée*.

#### Autres changements

- `config.yaml` : nouvelle section **`scheduler:`**.
- `requirements.txt` : `croniter>=2.0.0` (cron) et `winotify` (toast Windows, notifications appli fermée) ; `tkinterweb` (repli artifacts) et `plyer` en option.
- `tests/test_scheduler.py` : 24 tests (exécuteur factice, sans LLM ; incl. verrou + runner).
- `.gitignore` : `data/scheduled_tasks.json` + `data/scheduler.lock` (données locales).
- Documentation : `docs/ARTIFACTS_PREVIEW.md`, `docs/SCHEDULER.md`.
- Version du projet → **7.7.0**.

---

# 🎙️ Version 7.6.0 — Sortie vocale, Assistant de configuration & Panneau Réglages (16 Juin 2026)

### Trois nouveautés pour une expérience plus fluide

Cette version **complète la boucle vocale** (l'IA peut désormais **parler**, pas seulement écouter), ajoute un **assistant de premier lancement** qui configure le modèle automatiquement, et un **panneau Réglages** complet qui remplace l'édition manuelle de `config.yaml` / `Modelfile` / `.bat`.

#### 🔊 Sortie vocale (Text-to-Speech) — `interfaces/gui/voice_output.py` (nouveau)

- **`VoiceOutput`** : lecture vocale des réponses, **100% locale** via **pyttsx3** (moteur de l'OS — SAPI5 sur Windows, NSSpeechSynthesizer sur macOS, espeak-ng sur Linux) → aucun téléchargement de modèle.
- **Bouton 🔊 par message** (sous chaque réponse IA, à côté des étoiles RLHF) : 1ᵉʳ clic = lecture, 2ᵉ clic = stop (icône ⏹ pendant la lecture).
- **Toggle « 🔊 Lecture auto »** dans la sidebar : lit automatiquement chaque nouvelle réponse de l'IA.
- **Sélection de voix automatique selon la langue détectée** (`langdetect`) — évite de lire du français avec une voix anglaise ; bascule FR↔EN↔… selon le contenu.
- **`clean_for_speech()`** : retire blocs de code, markdown, URLs, emojis et pipes de tableaux avant lecture (prose naturelle).
- **Worker thread + file d'attente**, callbacks marshalés vers Tk via `after()` (même architecture que la saisie vocale 7.4.0). Dégradation propre si `pyttsx3` absent.
- **Correctif important** : `pyttsx3.init()` met le moteur en cache (WeakValueDictionary) et un moteur SAPI5 réutilisé **ne lit qu'une seule fois** ; on construit donc un `Engine` neuf à chaque lecture (`_new_engine`) → corrige l'impossibilité de réécouter un message.

#### 🧭 Assistant de premier lancement — `interfaces/onboarding.py` (nouveau)

- Au **tout premier démarrage** : vérifie qu'Ollama est joignable → détecte le **matériel** → recommande un modèle → le **télécharge** (progression streamée via `/api/pull`) → met à jour `Modelfile` (FROM) + `config.yaml` (`llm.local.default_model`) → crée le modèle personnalisé **`my_ai`**.
- **Recommandation matérielle (priorité à la fluidité)** :
  - **GPU dédié** (VRAM ≥ 4 Go, détecté via `nvidia-smi` → `pynvml` → `GPUtil` → `pyamdgpuinfo`) → dimensionné sur la **VRAM** (2b / 4b / 9b ≈ 4 / 6 / 10 Go).
  - **CPU seul** → `qwen3.5:2b` par défaut ; `4b` uniquement si CPU ≥ 8 cœurs physiques **et** RAM ≥ 16 Go ; **jamais `9b` en CPU** (génération trop lente pour un usage agréable sur PC bureautique).
- S'affiche **une seule fois** (marqueur `data/.onboarding_done`), et **jamais** si le modèle `my_ai` existe déjà (utilisateurs existants non dérangés). Échec **non bloquant** : l'app démarre quand même.
- Branché dans `launch_unified.py` après le démarrage d'Ollama. Helpers réutilisables (pull, création modèle, édition config en **préservant les commentaires**) partagés avec le panneau Réglages.

#### ⚙️ Panneau Réglages + gestionnaire de modèles — `interfaces/gui/settings_panel.py` (nouveau)

- Bouton **⚙️ Réglages** dans la sidebar → fenêtre complète :
  - **Modèles Ollama** : liste des modèles installés, choix du modèle de base, **pull** d'un nouveau modèle (barre de progression), **Appliquer** = régénère proprement `my_ai` (**system prompt du Modelfile préservé** → résout le problème de la 7.4.0 qui avait forcé le retrait du sélecteur de modèle inline).
  - **Paramètres** : température, `num_ctx`, timeout — écrits dans `config.yaml` + `Modelfile` (**commentaires préservés**) et **appliqués en live** à l'instance `LocalLLM` en cours, sans redémarrage.
  - **Autres réglages** : langue par défaut, lecture vocale auto, Relay auto-start, et **relance de l'assistant de configuration**.
- Toute écriture dans `config.yaml` passe par un **remplacement de ligne ancré** (jamais `yaml.dump`, qui détruirait commentaires et mise en forme).

#### Autres changements

- `config.yaml` : nouvelles clés `llm.local.temperature` / `num_ctx` / `timeout` (réglables via ⚙️ Réglages).
- `requirements.txt` : ajout de `pyttsx3>=2.90`.
- `.gitignore` : `data/.onboarding_done` ignoré (marqueur d'état local).
- Version du projet → **7.6.0**.

---

# 📱 Version 7.5.0 — Page Agents sur My_AI Relay (Mobile) (10 Juin 2026)

### 🤖 L'interface mobile gagne une page Agents complète

My_AI Relay (l'interface mobile, **pas** l'extension VS Code) affiche désormais une barre d'onglets **💬 Chat / 🤖 Agents** en haut, à la manière du GUI desktop. L'onglet Agents reprend **toutes les fonctionnalités de la page Agents du PC** en version tactile : grille des 9 agents spécialisés + agents personnalisés, création/édition/suppression d'agents, **workflow visuel n8n** (canvas tactile, nœuds reliables par les ports), **Mode Débat**, et exécution streamée avec sections dépliables et statuts de nœud.

Tout s'exécute **côté serveur Relay** (orchestrateur d'agents + modèle Ollama local) — comme le mode agentique VS Code, et **sans** passer par le `RelayBridge`/GUI. Le contenu ne quitte jamais l'enveloppe E2EE AES-256-GCM.

#### `relay/agent_relay.py` — Nouveau service `AgentRelayService`

- `list_agents()` — 9 built-in + agents personnalisés, rechargés depuis **`data/custom_agents.json` (fichier partagé avec le GUI desktop)** → synchro bidirectionnelle
- `create_agent()` / `edit_agent()` / `delete_agent()` — CRUD ; génération du *system prompt* + température via le LLM local (même prompt que `interfaces/agents/custom_agents.py`)
- `compute_execution_plan()` — port de `WorkflowCanvas.get_execution_plan` (tri topologique de Kahn → `single` / `sequential` / `parallel` / `dag`)
- `run_workflow()` — exécute le plan, streame chaque section via un callback `emit` ; étapes parallèles en threads ; respect de l'interruption (`on_token → False`)
- `run_debate()` — `execute_debate` de l'orchestrateur, streamé tour par tour
- `_augment_task_with_files()` — injecte le contenu des pièces jointes (PDF/DOCX/Excel/code via processeurs, images via modèle vision `describe_image`) dans la tâche
- Gate d'exécution unique + drapeaux d'interruption par `exec_id`

#### `relay/relay_server.py` — Dispatch Agents + corrections chat

- Nouveaux messages WS : `agents_list`, `agent_create`, `agent_edit`, `agent_delete`, `agent_execute`, `agent_debate`, `agent_stop` → `_handle_agent_message`
- **File d'émission unique drainée par une seule coroutine** : évite l'entrelacement de `send_text` concurrents pendant les étapes parallèles d'un workflow
- **Correction bouton Stop du chat** : l'attente de la réponse mobile (`wait_for_ai_response`) est désormais **détachée dans une tâche** — auparavant elle bloquait la boucle `receive_text()`, si bien qu'un `stop_generation` envoyé pendant la génération n'était jamais lu (le bouton Stop ne faisait rien)
- Nouveau message `stop_generation` → `bridge.request_interrupt()`
- `agent_execute` résout les `file_ids` via `consume_upload_ids` (même mécanisme d'upload chiffré que le chat)

#### `relay/relay_bridge.py` — Canal d'interruption

- `request_interrupt()` / `consume_interrupt_request()` (one-shot, thread-safe) : posé par le handler WS, consommé par la boucle de polling du GUI (`interrupt_ai()` renvoie la réponse partielle marquée « interrompue »)

#### `relay/static/` — Front-end mobile

- **`index.html`** — barre d'onglets (largeur égale → séparation centrée), vue Agents (grille, canvas `#wfCanvas`/`#wfWorld` + SVG liens, zone résultats, barre d'action, bouton + pièces jointes), modales Créer agent / Mode Débat
- **`agents.js`** (nouveau, `window.AgentsUI`) — grille, **canvas n8n tactile** (drag via *pointer events*, connexion par tap sur les ports, courbes de Bézier SVG, statuts de nœud), modales, exécution streamée, pièces jointes, Save/Load (localStorage) + Export (JSON)
- **`app.js`** — refactor de l'upload chiffré en `uploadEncryptedFile()` partagé ; pont `window.RelayCore` exposé à `agents.js` ; **rendu des liens** dans `renderMarkdown` (`[titre](url)` et URLs nues → `<a>` bleu cliquable) ; **bouton d'envoi ⇄ Stop** pendant la génération
- **`style.css`** — onglets, cartes (hauteur/largeur uniformes), canvas, sections, modales, bouton Stop (`.stopmode`), liens bleus soulignés ; barre d'action Agents compactée

#### `interfaces/gui/base.py`

- La boucle `_poll_relay_messages` consomme la demande d'interruption mobile et appelle `interrupt_ai()` (sur le thread Tk)

---

# 🎙️ Version 7.4.0 — Saisie vocale (Voice Mode) (13 Mai 2026)

### 🎤 Nouvelle fonctionnalité : dictée vocale dans toutes les zones de saisie

Un **bouton micro** remplace l'ancien sélecteur de modèle inline dans la zone de saisie du chat (écran d'accueil + mode conversation) et est également ajouté à la zone de saisie de l'onglet **Agents**. En toggle : un clic démarre l'enregistrement, un second clic l'arrête et lance la transcription locale. Le texte transcrit est inséré au curseur de la zone de saisie active. Tout fonctionne **100% localement** via **faster-whisper** — la voix ne quitte jamais la machine.

#### `interfaces/gui/voice_input.py` — Nouveau module

- **`VoiceInput`** : classe encapsulant capture audio + transcription
  - **Capture micro** via `sounddevice` (cross-platform, 16 kHz mono, float32)
  - **Transcription** via `faster-whisper` (modèle `small` ~150 Mo, `compute_type="int8"` CPU)
  - **Langue auto-détectée** (`language=None` passé au modèle) — supporte 99+ langues
  - **VAD intégré** (Voice Activity Detection de Whisper) pour ignorer les silences
  - **Lazy-loading** du modèle Whisper : pas chargé au démarrage, première transcription = ~5 s (téléchargement HuggingFace si pas en cache), suivantes instantanées
  - **Singleton de classe** `VoiceInput.get_shared(tk_root)` : une seule instance Whisper dans toute l'app, partagée entre chat & agents
  - **Thread-safe** : enregistrement dans un thread audio, transcription dans un thread séparé, callbacks marshalés vers le thread Tk via `root.after(0, ...)`
  - **Dégradation propre** : si `sounddevice` ou `faster-whisper` ne sont pas installés, `VoiceInput.available == False` et le bouton affiche une notification d'erreur sans crash
- **`attach_mic_button(parent, tk_root, target_getter, colors, show_notification)`** : factory du bouton micro overlay
  - Position : haut-droite du parent via `.place(relx=1.0, rely=0.0, anchor="ne")`
  - 3 états visuels : 🎙 gris (idle) / ● rouge avec pulsation 500 ms (recording) / ⏳ orange (transcribing)
  - **Insertion robuste au curseur** : détection automatique du placeholder par couleur (`cget("text_color")` ou `cget("fg")`), nettoyage manuel si présent, puis insertion différée de 50 ms via `tk_root.after()` pour laisser le binding `<FocusIn>` natif s'exécuter sans wiper le texte fraîchement inséré
  - **Préfixe espace automatique** si le caractère précédent le curseur n'est pas un blanc
  - **`target_getter` lazy** : résout le widget cible au moment du clic, ce qui permet à un bouton de cibler différents widgets selon l'écran/onglet actif

#### Suppression du sélecteur de modèle inline

L'ancien sélecteur (dropdown discret en haut-droite affichant `my_ai:latest`) est entièrement retiré :

- **`_create_inline_model_selector`** (~125 lignes), `_populate_model_selector`, `_update_model_selector`, `_on_model_selected` supprimés dans [`interfaces/gui/layout.py`](../interfaces/gui/layout.py)
- Variables `_model_selector_var`, `_model_list`, `_inline_model_selector`, `_home_inline_model_selector` retirées
- **Motivation** : non utilisé en pratique, et le changement de modèle à chaud bypassait le `system_prompt` du `Modelfile` → comportement incohérent. La procédure officielle reste documentée (modifier `config.yaml` + `Modelfile` + `create_custom_model.bat`)

#### Intégrations dans les deux interfaces

- **[`interfaces/gui/layout.py`](../interfaces/gui/layout.py)** (mode conversation chat) : `attach_mic_button(target_getter=lambda: self.input_text, ...)` dans `create_modern_input_area`
- **[`interfaces/gui/base.py`](../interfaces/gui/base.py)** (écran d'accueil chat) : `attach_mic_button(target_getter=lambda: self._home_input, ...)` dans le `home_screen`
- **[`interfaces/agents/task_input.py`](../interfaces/agents/task_input.py)** (onglet Agents) : `attach_mic_button(target_getter=lambda: self.task_entry, ...)` après création de `task_wrapper`. Récupération du `tk_root` via `self.parent.winfo_toplevel()` car `AgentsInterface` n'est pas un mixin du GUI principal

#### Nouvelles dépendances (`requirements.txt`)

```
faster-whisper>=1.0.0   # transcription locale, multi-langue
sounddevice>=0.4.6      # capture micro cross-platform
```

> Sur Linux/macOS, `sounddevice` requiert `portaudio` (souvent déjà présent — sinon `apt install libportaudio2` ou `brew install portaudio`).

#### Comportement détaillé

- **Toggle** : 1er clic = start, 2ème clic = stop + transcription async
- **Durée minimale** : enregistrements < 300 ms ignorés (évite les clics fantômes)
- **Modèle Whisper `small`** : ~150 Mo, compromis qualité/poids ; téléchargé au premier usage dans le cache HuggingFace (`~/.cache/huggingface/hub/`)
- **`int8` quantization** : ~3× plus rapide que `float32` sur CPU, perte de qualité négligeable
- **Logs console** : `🎙️ [VOICE] fr (98%) en 1.2s : 'Salut ça va'` après chaque transcription

---

# 🧩 Version 7.3.0 — Extension VS Code (7 Mai 2026)

### 🤖 Mise à jour : Mode Agentique (Extension VS Code v1.1.0)

L'extension VS Code passe d'un simple client de chat à un **assistant agentique façon Claude Code**, tournant sur le LLM local du PC hôte. À la connexion, l'extension s'identifie comme `client_kind: "vscode"` et le Relay aiguille la conversation vers une boucle de raisonnement dédiée qui appelle Ollama directement avec un prompt système outillé. Le LLM peut désormais lire, modifier et créer des fichiers, lancer des commandes shell et chercher dans le workspace VS Code — chaque appel d'outil est exécuté **côté extension**, sandboxé au workspace par défaut, et affiché dans le chat sous forme de carte pliable. **Le mobile et le GUI desktop ne sont absolument pas impactés** : sans `client_hello` un client reste en mode legacy et passe par le pipeline GUI/MCP local complet.

#### `core/agentic_executor.py` — Boucle agentique (nouveau module)

- **9 outils workspace** déclarés dans `AGENT_TOOLS` :
  - Lecture (auto-approuvée) : `read_file`, `list_dir`, `glob`, `grep`, `get_active_editor`, `open_file`
  - Modification (approbation utilisateur requise côté client) : `write_file`, `edit_file`, `run_command`
- **Format LLM-agnostique** : les outils sont décrits en texte brut dans le prompt système, et invoqués via des balises `<tool_use>{"name":...,"input":{...}}</tool_use>` parsées côté hôte. Aucune dépendance à l'API tools native d'Ollama → fonctionne avec n'importe quel modèle (qwen3.5:2b/4b/7b, llama, mistral...)
- **Streaming** : chaque token de la réponse Ollama est broadcast au client via `chunk` (avec retrait à la volée des blocs `<tool_use>` pour ne pas exposer le JSON brut à l'utilisateur)
- **Boucle multi-itérations** : LLM → parse `<tool_use>` → dispatch en parallèle (`asyncio.gather`) → réinjection des résultats → répétition jusqu'à plus de tool_use ou max 25 itérations
- **`RemoteToolExecutor`** : pont WS → extension via `asyncio.Future` indexées par `call_id`, avec timeout de 120 s par appel
- **Mémoire de session** : l'historique de conversation est passé par référence au `run()` et muté en place pour conserver le contexte d'un message au suivant

#### `relay/relay_server.py` — Routage par client_kind (modif chirurgicale)

- **Per-WS state** : `client_kind` (défaut `"mobile"` → 100% backward compat), `pending_tool_calls`, `vscode_history`, `workspace_info`
- **3 nouveaux types WS** dispatchés AVANT le handler `chat` legacy :
  - `client_hello { client_kind, workspace_info }` → bascule la session en mode VS Code, répond `hello_ack`
  - `tool_use` (sortant) → envoyé par la boucle agentique pour demander l'exécution d'un outil au client
  - `tool_result { call_id, content, is_error }` (entrant) → résout la `Future` correspondante
- **Branche `chat` agentique** : si `client_kind == "vscode"` → délègue à `_handle_vscode_chat` (qui crée un `AgenticExecutor` + `RemoteToolExecutor` et orchestre la boucle). **Le branche `chat` mobile est strictement intacte** (toujours `bridge.send_to_gui` → GUI desktop avec MCP locaux complets → `submit_ai_response`)
- Le seul changement structurel dans le branche `chat` mobile est la lecture de `msg_data.get("type")` une fois dans une variable locale `msg_type` — aucun changement de comportement

#### `vscode_extension/src/` — Modules ajoutés

- **`agentTools.ts`** : implémentation des 9 outils avec sandbox par construction
  - `resolveWorkspacePath` : résolution case-insensitive sur Windows, rejet par défaut hors workspace
  - `read_file` / `write_file` / `edit_file` : I/O via `vscode.workspace.fs`, création auto des dossiers parents, plafond 500 Ko par lecture
  - `glob` : `vscode.workspace.findFiles` avec cap 500 résultats
  - `grep` : appel `rg` (ripgrep) externe avec fallback JS quand absent du PATH
  - `run_command` : `cp.spawn` dans le workspace, `cmd.exe /d /s /c` sur Windows / `/bin/sh -c` ailleurs, output capé à 200 Ko, timeout configurable (1-600 s)
  - `get_active_editor` / `open_file` : intégration `vscode.window.activeTextEditor` / `showTextDocument`
- **`toolDispatcher.ts`** : politique d'approbation
  - Auto-approuve les outils en lecture seule
  - Modal pour les opérations destructives, avec 3 niveaux d'autorisation : *Une fois* / *Pour ce fichier (mémorisé pour la session)* / *Tout autoriser pour cet outil dans la session*
  - Modal séparé et **non-mémorisable** pour les chemins hors workspace
  - Émet des événements (`requested`, `awaiting-approval`, `running`, `completed`, `failed`, `denied`) consommés par le webview pour piloter les cartes
  - Réinitialisé à chaque reconnexion
- **Modifications de `relayClient.ts` et `connectionManager.ts`** :
  - Envoi du `client_hello` à l'ouverture du WebSocket
  - Construction de `workspace_info` à partir de `vscode.workspace.workspaceFolders`
  - Interception des `tool_use` (jamais affichés comme texte) → dispatch local → renvoi du `tool_result`
  - Forward des événements dispatcher au `ChatViewProvider` qui les transmet au webview

#### `vscode_extension/media/` — UI cartes d'outils

- **`chat.js`** : nouveau handler `applyToolEvent` qui crée/met à jour des cartes par `call_id`. La carte est insérée AVANT la bulle de streaming en cours pour respecter l'ordre d'arrivée
- **`chat.css`** : style des cartes pliables (header cliquable, bordure gauche colorée selon l'état, sections input/output en `<pre>` scrollables)

#### Bilingue (FR/EN)

- Nouvelles strings localisées pour les modaux d'approbation : `Allow once`, `Allow for this file`, `Allow all {0} this session`, `Default: deny`, et 5 messages de prompt (`My_AI wants to WRITE/EDIT/run shell command/access outside workspace/use tool`)

#### Garanties d'isolation

- **Sandbox** par défaut : tous les chemins résolus contre le workspace root, sortie hors workspace = modal explicite par chemin (jamais auto-approuvable)
- **Aucun accès aux MCP locaux** depuis le mode agentique VS Code : le LLM ne voit que ce que les 9 outils workspace lui donnent
- **Mode mobile/GUI** : strictement intact (le routage `client_kind` est défensif, défaut `mobile`)

#### Distribution

- **Extension v1.1.0** : bump dans `vscode_extension/package.json`, descriptions Marketplace mises à jour (FR + EN) pour refléter le mode agentique

---

### 💻 Nouveau Module : Extension VS Code (`vscode_extension/`)

L'extension VS Code **My_AI Relay** est un client distant officiel publié sur le Marketplace VS Code. Elle se connecte à une instance Relay déjà active sur un PC hôte (votre PC perso, votre serveur, etc.) via le même tunnel chiffré et le même protocole WebSocket que l'interface mobile. Toute l'inférence, les processeurs de fichiers et l'historique restent côté hôte — VS Code ne transporte que des prompts/réponses chiffrés. Bénéfice principal : faire tourner le LLM sur une grosse machine fixe et s'y connecter depuis n'importe quel laptop.

#### Architecture

- **Réutilise intégralement** l'infrastructure Relay existante (WebSocket `/ws`, endpoints REST `/api/health`, `/api/history`, `/api/pending`, `/api/upload`) — aucun nouveau composant côté serveur
- **Chiffrement AES-256-GCM** identique à l'interface mobile (Node `webcrypto`)
- **Failover multi-tunnel** côté client : ping de chaque URL, sélection du premier joignable, reconnexion automatique
- **Identifiants persistants** dans le `SecretStorage` de VS Code (chiffré par le keychain de l'OS)
- **Auto-déconnexion** quand le Relay hôte s'arrête, **auto-reconnexion** au redémarrage

#### Fichiers et structure

```
vscode_extension/
├─ package.json                # Manifest + 8 commandes + setting "openInSecondarySidebar"
├─ src/
│  ├─ extension.ts             # activate, status bar, prompts, déplacement secondary sidebar
│  ├─ connectionManager.ts     # SecretStorage + état + health-check polling (3 échecs → déco)
│  ├─ relayClient.ts           # WebSocket + AES-GCM + multi-tunnel failover + upload + history
│  ├─ chatViewProvider.ts      # WebviewView (sidebar) + bridge postMessage + bundle l10n webview
│  ├─ workspaceBridge.ts       # auto-attach, send selection, send active file, insert at cursor
│  ├─ connectionString.ts      # Parse `router.html#d=<base64(json)>` (mêmes données que le QR)
│  ├─ crypto.ts                # AES-256-GCM via Node `webcrypto`
│  └─ types.ts
├─ media/                      # Webview UI (HTML/CSS/JS, adaptée de relay/static/)
│  ├─ chat.html chat.css chat.js
│  ├─ extension_logo.png       # Icône Marketplace
│  └─ icon-activitybar.svg
├─ l10n/                       # Bundles runtime FR/EN pour `vscode.l10n.t()`
│  ├─ bundle.l10n.json         # Source EN (fallback)
│  └─ bundle.l10n.fr.json      # Traductions FR
├─ package.nls.json            # Strings du manifest (EN, défaut Marketplace)
├─ package.nls.fr.json         # Strings du manifest (FR)
├─ README.md  README.fr.md     # Doc Marketplace bilingue (sélecteur en tête)
├─ CHANGELOG.md  LICENSE
├─ tsconfig.json esbuild.js    # Build TypeScript → bundle CommonJS
└─ .vscodeignore .gitignore
```

#### Bouton GUI hôte (`interfaces/gui/base.py`)

- Nouveau bouton **🧩 Copier pour l'extension VS Code** dans la popup Relay (`_show_relay_info_popup`), copie l'URL `router.html#d=<base64>` (même payload que le QR mobile)
- Désactivé tant qu'aucun tunnel n'est actif, message contextuel "Tunnel non prêt"

#### Commandes VS Code (palette + menus contextuels)

| Commande | Description |
|---|---|
| `My_AI Relay : Se connecter` | Coller la chaîne de connexion |
| `My_AI Relay : Se déconnecter` | Fermer la session (garde les credentials) |
| `My_AI Relay : Oublier la connexion enregistrée` | Supprime du SecretStorage |
| `My_AI Relay : Envoyer la sélection à My_AI` | Envoie la sélection avec fence langage (clic droit éditeur) |
| `My_AI Relay : Envoyer le fichier actif à My_AI` | Upload + envoi du fichier courant |
| `My_AI Relay : Activer / désactiver l'attache automatique du fichier actif` | Toggle |
| `My_AI Relay : Ouvrir le chat` | Affiche le panneau |
| `My_AI Relay : Déplacer le chat vers la barre latérale secondaire (droite)` | Déclenche le picker "Move View" |

#### UI webview (`media/`)

- **Adaptation desktop** de `relay/static/` (HTML/CSS/JS) avec densité plus compacte
- **Header enrichi** : bouton toggle "Auto-attach", bouton "Nouvelle connexion" (toujours visible — récupération sans se retrouver bloqué si le token a changé), bouton "Effacer"
- **Boutons par bloc de code** (au survol) : **Insérer** (au curseur de l'éditeur actif) et **Copier** (presse-papiers)
- **Reprise de stream** identique à l'interface mobile (chunks cumulatifs, déduplication par `message_id`)
- **Strings localisées injectées** depuis l'extension via `postMessage init-strings` au démarrage — la webview rend tout dans la langue active de VS Code

#### Bilingue intégral (FR / EN)

- **Manifest** : strings dans `package.nls.json` (EN, affiché par défaut sur le Marketplace) et `package.nls.fr.json` (FR, affiché aux utilisateurs FR)
- **Runtime extension** : tous les `vscode.window.show*Message`, prompts, status bar, openDialog passent par `vscode.l10n.t('English source string')` avec bundle FR dans `l10n/bundle.l10n.fr.json`
- **Webview** : bundle de strings localisées envoyé par l'extension à la webview au démarrage
- **README bilingue** (`README.md` + `README.fr.md`) avec sélecteur de langue en tête

#### Sécurité

- La chaîne de connexion (URL + token + clé AES) ne quitte **jamais** le PC hôte sauf saisie manuelle de l'utilisateur
- Stockée chiffrée dans le `SecretStorage` de VS Code (keychain OS)
- Aucun token / credential n'est embarqué dans le code source publié sur GitHub ou le Marketplace

#### Distribution

- **Marketplace VS Code** : publiée sous l'identifiant `gonicolas12.my-ai`
- **VSIX local** : `npm run package` génère un `.vsix` installable hors-ligne (`code --install-extension`)
- **Open source** : tout le code de l'extension est dans le dossier `vscode_extension/` du dépôt principal

### 📂 Documentation

- `vscode_extension/README.md` (EN) et `vscode_extension/README.fr.md` (FR) — doc Marketplace complète
- `vscode_extension/CHANGELOG.md` — historique des versions de l'extension (0.1.0 → 0.1.5)
- Mise à jour `docs/ARCHITECTURE.md` (section dédiée à l'extension)
- Mise à jour `README.md` racine (mention dans les Points Forts, lien dans la documentation)

### 🗑️ Suppressions

- `interfaces/vscode_extension.py` (ancien stub Python stdin/stdout, jamais finalisé) — remplacé par la vraie extension TypeScript dans `vscode_extension/`

---

# 📡 Version 7.2.0 — My_AI Relay : Accès Mobile (16 Avril 2026)

### 📱 Nouveau Module : My_AI Relay

My_AI Relay permet d'accéder à votre IA locale depuis un smartphone, partout dans le monde, tant que l'application tourne sur votre PC. Les échanges sont synchronisés en temps réel entre le mobile et le GUI desktop, pièces jointes comprises (images et documents).

#### `relay/relay_server.py` — Serveur FastAPI + WebSocket

- **Serveur FastAPI** exposé sur le port 8765 (configurable dans `config.yaml`)
- **WebSocket temps réel** `/ws` pour le chat bidirectionnel
  - Protocole : `{type:'chat', message, file_ids:[...]}` — les `file_ids` sont résolus côté serveur ; le premier fichier image devient `image_path`, les autres rejoignent `file_paths`
- **Authentification sécurisée** :
  - Token aléatoire unique par session (si aucun mot de passe configuré)
  - Token dérivé du mot de passe via SHA-256 (reproductible entre sessions)
  - Vérification via query param (`?token=...`) ou endpoint `POST /auth`
- **Tunnel cloudflared** automatique pour l'accès HTTPS depuis l'extérieur :
  - Détection de cloudflared dans `$PATH` ou `tools/`
  - **Téléchargement automatique** au premier lancement (Windows, macOS, Linux)
  - Fallback réseau local (`http://localhost:8765`) si cloudflared indisponible
- **QR Code SVG** généré automatiquement pour scanner depuis le téléphone
- **Page de login HTML** embarquée (servie quand le token est absent)
- **Endpoints REST** :
  - `GET /` — Interface mobile (PWA) ou page de login
  - `POST /auth` — Authentification par mot de passe → retourne le token
  - `POST /api/upload` — Réception multipart des pièces jointes mobiles :
    - Allowlist d'extensions (images + PDF, DOCX, XLSX, CSV, code, txt/md)
    - Streaming 64 Ko vers `{tempdir}/my_ai_relay_uploads/` avec plafond **25 Mo** (réponse `413` + nettoyage du fichier partiel si dépassement)
    - Registre en mémoire `Dict[file_id, metadata]` protégé par `threading.Lock`, consommé une seule fois lors de l'envoi du message de chat
  - `GET /api/health` — Santé du serveur, uptime, nombre de clients connectés
  - `GET /api/history` — Historique de la session relay
  - `WebSocket /ws` — Chat temps réel (messages, pings, accusés de réception)

#### `relay/relay_bridge.py` — Pont GUI ↔ Mobile

- **Singleton thread-safe** : partage d'état entre le serveur asyncio et le GUI Tkinter
- **Files de messages bidirectionnelles** (`deque` maxlen 500) :
  - `send_to_gui()` — achemine les messages du mobile vers le GUI desktop
  - `send_to_ws()` — achemine les réponses du GUI vers le téléphone
- **Callbacks** enregistrables pour notification temps réel des deux côtés (`on_gui_message`, `on_ws_message`)
- **Mécanisme de réponse asynchrone** :
  - `wait_for_ai_response(timeout=relay.response_timeout)` — attend la réponse du GUI (async-safe via `run_in_executor`)
  - `submit_ai_response(text)` — le GUI soumet la réponse finale après streaming
- **Historique de session** : liste complète des `RelayMessage` (texte, source, timestamp, id, `image_path`, `file_paths`)
- **Cycle de vie** : `clear_history()`, `reset()`, propriétés `active` et `connected_clients`

#### `relay/static/` — Interface Mobile PWA

- **`index.html`** — Interface de chat mobile-first, Progressive Web App installable, bouton **+** d'attachement et conteneur de chips d'aperçu
- **`style.css`** — Thème sombre élégant, typographie et layout adaptés aux petits écrans, styles `.attach-btn` / `.attachments` / `.attachment-chip` (avec états `uploading` / `error`)
- **`app.js`** — Logique WebSocket : connexion, envoi/réception, indicateur de frappe, reconnexion automatique ; upload asynchrone via `XMLHttpRequest` vers `POST /api/upload?token=...`, bouton d'envoi désactivé tant qu'un upload est en cours, injection des `file_ids` dans le message de chat

#### 📎 Pièces jointes depuis le mobile

Le bouton **+** de l'interface mobile permet de joindre des fichiers qui sont traités **exactement comme sur le PC** :

- **Images** (PNG, JPG, JPEG, GIF, BMP, WebP, TIFF) → envoyées au **modèle vision** (encodage base64, même pipeline que le drag & drop PC)
- **Documents** (PDF, DOCX, DOC, XLSX, XLS, CSV) → extraits ajoutés au **contexte vectoriel** via les processeurs spécialisés (`custom_ai.add_file_to_context`)
- **Code & texte** (PY, JS, HTML, CSS, JSON, XML, MD, TXT) → chargés dans le contexte de la session
- **Image + documents combinés** : la première image part vers la vision, les autres fichiers rejoignent le contexte
- Si aucun texte n'accompagne le fichier, une requête par défaut est injectée (`"Décris cette image en détail."` ou `"Analyse ce fichier et résume-le."`)

#### GUI (`interfaces/gui/base.py`) — Pipeline de réception

- **`_display_relay_message`** construit une bulle enrichie avec préfixes 🖼️ / 📎 pour chaque pièce jointe
- **`_process_relay_attachments_then_ai`** (nouveau) : exécute `process_file_background` (documents) et `_process_image_file` (image) **de façon synchrone** dans un seul thread de travail avant d'appeler `quel_handle_message_with_id`, garantissant que le contexte est chargé avant l'inférence
- **Relance de l'animation « thinking »** sur le thread Tk entre la fin du traitement fichier et le démarrage de l'inférence (compense le `is_thinking = False` positionné par `process_file_background` qui arrêtait la boucle `animate_thinking`)

### 🎨 GUI desktop — Bouton Relay dans la barre latérale

- Le bouton **📡 Relay** est intégré à la **sidebar** (fichier `interfaces/gui/sidebar.py`) et **visible en permanence**, y compris sur l'écran d'accueil
- Bouton accent `#ff6b47`, placé entre le titre de la sidebar et la section Sessions

### ⚙️ Configuration (`config.yaml`)

Nouvelle section `relay` :

```yaml
relay:
  auto_start: false      # Démarrage automatique au lancement du GUI
  port: 8765             # Port du serveur WebSocket
  response_timeout: 500  # Délai max de réponse IA (secondes)
  password: ""           # Mot de passe (vide = token aléatoire par session)
  tunnel: true           # Activer le tunnel cloudflared
  host: "0.0.0.0"        # Adresse d'écoute (0.0.0.0 = toutes les interfaces)
```

### 📦 Dépendances (`requirements.txt`)

- Ajout de **`python-multipart>=0.0.9`** (requis par FastAPI pour le parsing `UploadFile` du nouvel endpoint `/api/upload`)

---

# 💾 Version 7.1.0 - Mémoire Vectorielle 10M Tokens (8 Avril 2026)

### 🧠 Capacité mémoire x10

- **`ai.max_tokens`** passé de **1 048 576** (1M) à **10 485 760** (**10M tokens**)
  dans `config.yaml`. Le `VectorMemory` peut désormais stocker ~40 000 chunks
  de 256 tokens avant éviction FIFO, contre ~4 000 auparavant.
- Empreinte réelle : ~15 Mo d'embeddings + ~30 Mo d'index HNSW au plafond —
  aucun impact perceptible sur la RAM ni la latence de recherche (<20 ms).
- Marge confortable (~10×) sur l'usage personnel réel tout en conservant
  le cleanup FIFO comme garde-fou fonctionnel.

### 🔧 Correction qualité des embeddings

- **Chunks réduits de 512 → 256 tokens** (`config.yaml` RAG + défauts
  `VectorMemory`) pour s'aligner sur la limite d'input réelle du modèle
  `sentence-transformers/all-MiniLM-L6-v2` (256 tokens).
- **Avant :** la seconde moitié de chaque chunk était silencieusement tronquée
  au moment du calcul de l'embedding — dégradation invisible de la qualité
  de recherche sémantique.
- **Après :** chaque chunk est intégralement vectorisé, la précision du
  RAG et du reranking CrossEncoder s'en trouve améliorée.
- `chunk_overlap` ajusté de 50 → 32 (~12%) pour garder une continuité
  sémantique cohérente avec la nouvelle taille de chunk.

### 📝 Fichiers modifiés

- `config.yaml` — `ai.max_tokens: 10485760`, `optimization.rag.chunk_size: 256`,
  `optimization.rag.chunk_overlap: 32`, bump version → `7.1.0`
- `memory/vector_memory.py` — défauts `chunk_size=256`, `chunk_overlap=32`
- `models/custom_ai_model.py` — alignement sur les nouveaux défauts
- `tests/test_vector_memory.py` — assertions mises à jour
- Documentation (`docs/`, `README.md` mémoire) — toutes les références
  à « 1M tokens » actualisées en « 10M tokens »

---

# 🚀 Version 7.0.0 - Modules Intelligents & API REST (24 Mars 2026)

### ✨ Nouveaux Modules (7 modules)

#### 🌐 Serveur API REST Local (`core/api_server.py`)
- **API HTTP complète** exposée sur `localhost:8000` via FastAPI + Uvicorn
- **Endpoints disponibles** :
  - `GET /api/health` — État du serveur (version, uptime, statut moteur)
  - `POST /api/chat` — Envoyer un message à l'IA avec system prompt optionnel
  - `GET /api/models` — Lister les modèles Ollama disponibles
  - `POST /api/models/switch` — Changer de modèle actif
  - `GET /api/conversations` — Récupérer l'historique complet
  - `DELETE /api/conversations` — Effacer l'historique
  - `GET /api/stats` — Statistiques système (contexte, mémoire, modèle, uptime)
- **CORS configurable** pour intégrations externes
- **Thread daemon** pour exécution non-bloquante

#### 📜 Historique des Commandes (`core/command_history.py`)
- **Base SQLite persistante** avec mode WAL pour accès concurrent
- **Recherche plein texte** dans les requêtes et réponses (COLLATE NOCASE)
- **Système de favoris** pour conserver les requêtes importantes
- **Statistiques** : total, favoris, répartition par agent, plage de dates
- **Nettoyage automatique** des entrées anciennes (préserve les favoris)
- **Limite configurable** (défaut : 5 000 entrées)

#### 📤 Export de Conversations (`core/conversation_exporter.py`)
- **3 formats d'export** : Markdown (.md), HTML (.html), PDF (.pdf)
- **Métadonnées** incluses : date, modèle, nom de session, nombre de messages
- **Thème sombre CSS** embarqué pour l'export HTML (inspiré Claude)
- **Blocs de code** préservés avec formatage dans tous les formats
- **PDF** via ReportLab avec styles par rôle (Utilisateur/Assistant/Système)
- **Noms de fichiers horodatés** automatiques ou personnalisés

#### 🧠 Base de Connaissances Structurée (`core/knowledge_base_manager.py`)
- **Stockage de faits éditables** dans SQLite avec catégorisation
- **6 catégories** : preference, decision, person, procedure, technical, general
- **Score de confiance** (0.0 à 1.0) pour chaque fait
- **Extraction automatique** depuis le texte libre (patrons linguistiques français) :
  - Préférences : "je préfère...", "j'aime mieux..."
  - Décisions : "on a décidé de...", "nous avons décidé..."
  - Personnes : "mon collègue s'appelle...", "mon manager est..."
  - Procédures : "la procédure est de...", "les étapes sont..."
  - Techniques : "le serveur est...", "l'url est...", "on utilise..."
- **Injection dans le prompt** : les faits pertinents sont automatiquement contextualisés
- **CRUD complet** : ajout, recherche, mise à jour, suppression

#### 🌍 Détection Automatique de Langue (`core/language_detector.py`)
- **12 langues supportées** : fr, en, es, de, it, pt, nl, ru, zh, ja, ko, ar
- **Détection automatique** via la bibliothèque `langdetect` (avec fallback)
- **Cache LRU** (128 entrées) pour cohérence et performance
- **Suffix de prompt système** généré automatiquement pour forcer la réponse dans la langue détectée
- **Seuil de longueur minimale** configurable (défaut : 10 caractères)

#### 💼 Gestionnaire de Sessions / Workspaces (`core/session_manager.py`)
- **Multi-workspaces** : créer, sauvegarder, charger, supprimer des espaces de travail isolés
- **Persistance JSON** sur disque avec écriture atomique (fichier temporaire + rename)
- **État complet** sauvegardé : historique, documents attachés, agents actifs, paramètres
- **Auto-save** configurable (défaut : toutes les 5 minutes)
- **Identifiants slug** URL-safe avec normalisation des accents
- **Limite configurable** (défaut : 50 workspaces)

#### 🗄️ Cache Web Persistant (`core/web_cache.py`)
- **Cache disque** via `diskcache` pour les réponses HTTP
- **TTL configurable** (défaut : 3 600 secondes = 1 heure)
- **Éviction automatique** des entrées expirées et limite d'entrées
- **Statistiques** : hits, misses, taille du cache
- **Clé SHA256** stable pour chaque URL
- **Context manager** pour nettoyage propre

### 🖥️ Améliorations Interface Graphique

#### 🏠 Écran d'Accueil (Home Screen)
- **Page d'accueil style Claude** affichée quand la conversation est vide
- **Logo My_AI central** avec message de bienvenue
- **Zone de saisie intégrée** avec preview de fichiers joints
- **Transition fluide** vers la conversation au premier message
- **Sauvegarde des fichiers joints** lors de la transition home → chat

#### 📎 Pièces Jointes aux Agents
- **Bouton "+" sur la page Agents** pour attacher des fichiers (PDF, DOCX, TXT, code, CSV...)
- **Preview visuelle** des fichiers joints dans la zone de saisie des agents
- **Contenu injecté dans le prompt** : les fichiers sont lus et leur contenu est ajouté au prompt de l'agent
- **Support multi-formats** : PDF (via PDFProcessor), DOCX (via DOCXProcessor), texte/code (lecture directe)
- **Propagation en multi-agents** : dans un workflow séquentiel, tous les agents reçoivent les fichiers joints + le contexte des agents précédents

#### ⭐ Système de Feedback 1-5 Étoiles (remplace 👍👎)
- **Notation par étoiles** : 5 étoiles cliquables (☆☆☆☆☆) remplacent les anciens boutons pouce haut/bas
- **Hover interactif** : Les étoiles se remplissent progressivement au survol pour un aperçu visuel
- **Désactivation après notation** : Impossible de noter deux fois la même réponse
- **Mapping automatique** : 4-5 ⭐ → feedback positif · 3 ⭐ → neutre · 1-2 ⭐ → négatif
- **Rétro-compatibilité** : L'ancienne API `on_thumbs_up/down` redirige vers le nouveau système

#### 💾 Sauvegarde / Chargement de Workflows en JSON
- **Bouton 💾 Sauvegarder** : Exporte le workflow actuel (nœuds + connexions) dans un fichier `.json` via boîte de dialogue
- **Bouton 📂 Charger** : Importe et restaure un workflow sauvegardé depuis un fichier `.json`
- **Bouton 📤 Export** : Exporte les résultats d'exécution en Markdown ou texte
- **Format JSON structuré** : `version`, liste des nœuds (id, agent, position, statut), liste des connexions
- **Notification toast** : Confirmation visuelle après sauvegarde/chargement réussi

#### ⚠️ Dialogue de Confirmation de Suppression MCP
- **Fenêtre modale stylisée** quand l'IA demande à supprimer un fichier via MCP (`delete_local_file`)
- **Affichage du chemin complet** du fichier à supprimer
- **Boutons Oui/Non** avec thème orange/noir cohérent
- **Synchronisation thread** via `threading.Event` entre le thread IA et le thread GUI

### ⚙️ Configuration

Nouvelles sections dans `config.yaml` :
- `api` — Serveur REST (host, port, CORS)
- `workspaces` — Sessions et workspaces (répertoire, auto-save, limite)
- `knowledge_base` — Base de connaissances (répertoire, auto-extract)
- `command_history` — Historique des commandes (max_entries, db_path)
- `export` — Export conversations (répertoire, format par défaut)
- `language` — Détection de langue (auto-detect, langues supportées)
- `web_cache` — Cache web (TTL, max_entries, répertoire)

### 📦 Nouvelles Dépendances
- `fastapi>=0.100.0` — Framework API REST
- `uvicorn>=0.23.0` — Serveur ASGI
- `langdetect>=1.0.9` — Détection de langue

---

# 🌟 Version 6.9.0 - Optimisations MCP & Stabilité Interface (19 Mars 2026)

### 🚀 Nouveautés et Optimisations

#### ⚙️ Optimisations des requêtes Ollama (ChatOrchestrator)
- **Pré-chargement du modèle (Keep Alloc)** : Ajout systématique du paramètre `keep_alive="1h"` pour conserver le modèle en VRAM vidéo tout au long des longues boucles de réflexion et de chaînage d'outils, éliminant les latences froides.
- **Allocation dynamique de contexte (`num_ctx`)** : Ajustement sur-mesure de la fenêtre de contexte (`16384` pour l'action pure, `8192` pour la synthèse) permettant d'éviter radicalement les erreurs Out-Of-Memory (OOM) et de contourner le "swapping" lourd de la RAM système sous Windows.
- **Ancrage du Prompt Système (`num_keep=-1`)** : Verrouillage du prompt système et du Scratchpad de réflexion dans le cache K/V (Key/Value) d'Ollama. Garantit une stricte adhésion aux règles sans recalcul de ce prompt lors du "Rolling Window Eviction".

#### 📂 Fiabilisation & Accès Locaux (Accès ROOT via MCP Local)
- **Accès à tout le PC (Root System)** : L'IA a désormais un accès complet et encadré à l'ensemble de vos disques durs. Elle peut écrire, rechercher des fichiers, lire leur contenu et organiser les espaces de travail par des créations de dossiers.
- **Chemins absolus stricts** : Renforcement drastique des directives orchestrant les outils pour forcer la réutilisation "à l'octet près" des chemins complets retournés. L'IA ne raccourcira plus jamais les longs chemins réseau ou de sauvegarde.
- **Correction des boucles `search_memory`** : Amende l'ordonnanceur de l'IA pour stopper la recherche vectorielle entêtée sur les événements locaux immédiats ou pour prévenir les boucles indéfinies en cas de recherche vide.

---

# 🖼️ Version 6.8.0 - Canvas Visuel Workflow & Monitoring Ressources (9 Mars 2026)

### 🚀 Nouveautés Principales

#### 🎨 Canvas Visuel de Workflow (style n8n)

Nouveau module `interfaces/workflow_canvas.py` — éditeur visuel interactif pour orchestrer des workflows d'agents :

- **Nœuds visuels** : Rectangles arrondis avec bandeau couleur, nom d'agent, indicateur de statut (idle/running/done/error), ports d'entrée/sortie
- **Connexions Bézier** : Courbes cubiques horizontales avec flèches, créées par drag du port de sortie vers le port d'entrée
- **Zoom & Pan** : Molette (0.3x à 3x), clic milieu/droit pour naviguer, toolbar avec boutons ⊕/⊖/⊙
- **Grille & Minimap** : Points de repère avec snap automatique, vue miniature du graphe complet
- **Sélection avancée** : Clic, Shift+clic, rectangle de sélection, touche Suppr pour suppression
- **Exécution DAG** : Tri topologique automatique — les nœuds sans dépendances mutuelles sont exécutés en parallèle (threads)
- **Passage de contexte** : Le résultat d'un nœud parent est injecté dans le contexte du nœud enfant
- **Statuts temps réel** : Chaque nœud change de couleur pendant l'exécution (gris → jaune → vert/rouge)

#### 📊 Monitoring Ressources Système

Nouveau module `interfaces/resource_monitor.py` — collecte et affichage des métriques système :

- **CPU & RAM** : Utilisation spécifique aux processus Ollama (via psutil)
- **GPU & VRAM** : Monitoring NVIDIA (via pynvml/GPUtil, optionnel)
- **Inférence** : Temps d'exécution en ms et vitesse de génération en tokens/s
- **Barres de progression colorées** : Vert (0-60%) → Jaune (60-85%) → Rouge (85-100%)
- **Sparklines** : Mini-graphiques des 60 dernières mesures (~3 min d'historique)
- **Thread daemon** : Collecte toutes les 3 secondes sans bloquer l'UI

---

# 🏗️ Version 6.7.0 - ChatOrchestrator & Migration Qwen3.5 (4 Mars 2026)

### 🚀 Nouveautés Principales

#### 🧠 ChatOrchestrator — Boucle Agentique Avancée

Nouveau module `core/chat_orchestrator.py` (1 161 lignes) qui remplace l'appel direct à `LocalLLM.generate_with_tools_stream()` dans `AIEngine.process_query_stream()`. Il implémente trois design patterns issus de l'architecture moderne des agents IA :

- **Pattern ReAct** (Reasoning + Acting) : boucle `Réfléchis → Agis → Observe` à chaque tour — le modèle raisonne avant d'appeler un outil et met à jour son état après chaque résultat
- **Pattern Plan & Execute** : pour les requêtes longues (> 55 caractères), le modèle génère un plan structuré en étapes avant d'agir, puis coche chaque étape à mesure qu'elle est complétée
- **Scratchpad persistant** : état interne maintenu entre les tours, injecté dans le system prompt sous forme de bloc XML structuré :
  - `OBJECTIF` : la demande originale de l'utilisateur
  - `PLAN` : étapes numérotées avec marqueur ✓ sur les complétées
  - `ÉTAPE ACTUELLE` : numéro de l'étape en cours
  - `FAITS COLLECTÉS` : résultats d'outils résumés (tronqués à 400 chars)
  - `TOURS RESTANTS` : indicateur d'urgence quand < 3 tours disponibles
  - `PROCHAINE ACTION` : intention du prochain tour

### 🦙 Migration vers Qwen3.5 — Modèles Légers et Rapides

#### 🔄 Remplacement de llama3.2 par Qwen3.5

- **Modèle principal** : `qwen3.5:4b` (ou `qwen3.5:2b` selon la config) remplace `llama3.2`
- **`Modelfile`** mis à jour : `FROM qwen3.5:4b` — modèle léger, rapide, avec thinking natif
- **`config.yaml`** : `llm.local.default_model` est désormais la **source unique** pour le nom du modèle

#### 🧠 Mode thinking natif utilisé

- **Qwen3.5** ayant une capacité de **raisonnement intégrée**, le mode **thinking** est désormais **natif** et plus fluide
- La logique de déclenchement du mode **thinking** est conservée (longueur, complexité, mots-clés), mais la réflexion est plus rapide et mieux intégrée
- Le prompt de **system prompt** a été ajusté pour tirer parti des capacités de **reasoning** de **Qwen3.5**

#### 👁️ Modèle de Vision

- **`minicpm-v`** ajouté en priorité #1 dans `_get_vision_model()` — meilleur ratio qualité/vitesse (3 Go)
- `llava` reste en fallback
- `qwen3.5` n'ayant pas de capacité vision, le routage vers un modèle dédié est obligatoire

### 📄 Procédure de Changement de Modèle

Pour changer de modèle LLM à l'avenir, modifier **3 fichiers uniquement** :

- `Étape 1:` `config.yaml` → champ `llm.local.default_model`
- `Étape 2:` `Modelfile` → directive `FROM`
- `Étape 3:` Terminal → `ollama pull <nouveau-modele>` puis `.\create_custom_model.bat`

---

# 🧠 Version 6.6.0 - Mode Thinking & Refonte Interface (24 Février 2026)

### 🚀 Nouveautés Principales

#### 🧠 Mode Thinking — Raisonnement en Deux Passes

- **Détection automatique de complexité** : Le moteur IA analyse chaque requête et déclenche le mode thinking pour les questions complexes (longueur > 150 caractères, mots-clés analytiques, requêtes multi-questions, blocs de code, etc.)
- **Première passe de raisonnement** : Avant de répondre, l'IA effectue une réflexion interne étape par étape via `generate_thinking_stream()` — sans ajouter ce raisonnement à l'historique de conversation
- **Streaming temps réel** : Chaque token de raisonnement s'affiche instantanément dans un widget dépliable animé dans le chat
- **Widget "Raisonnement" animé** :
  - Titre cycling animé : `Raisonnement.` → `Raisonnement..` → `Raisonnement...` (toutes les 400 ms)
  - Bouton ▼/▶ pour déplier/replier le contenu
  - État final : `Raisonnement ✓` quand la réflexion est terminée
- **Réponse enrichie** : La réponse finale intègre le contexte du raisonnement préalable pour une qualité accrue
- **Interruption propre** : La passe thinking respecte le bouton STOP et s'arrête immédiatement

#### 🎯 Écran d'Accueil (Home Screen)

- **Nouvelle page d'accueil** : Au lancement, l'interface affiche un écran d'accueil centré avec emoji robot, titre "My_AI" et zone de saisie intégrée
- **Saisie directe depuis l'accueil** : Taper un message dans l'écran d'accueil et appuyer sur Entrée lance directement la conversation
- **Transition fluide** : L'écran d'accueil disparaît proprement et le message est transmis au chat

#### 🎨 Refonte du Header

- **Header épuré** : Suppression du logo robot, du titre "My Personal AI" et du sous-titre "Assistant IA Local" en haut à gauche — interface plus minimaliste
- **Boutons d'onglets parfaitement centrés** : `💬 Chat` et `🤖 Agents` sont maintenant positionnés via `place(relx=0.5)` pour un centrage absolu garanti, indépendant des autres éléments

---

# 🔌 Version 6.5.0 - Intégration MCP (Model Context Protocol) (20 Février 2026)

### 🚀 Nouveautés Principales

#### 🔌 Support du Model Context Protocol (MCP)
- **Client MCP Intégré** : Nouveau module `core/mcp_client.py` permettant à Ollama d'interagir avec des outils locaux et des serveurs MCP externes.
- **Outils Locaux (LocalTools)** : Encapsulation des capacités existantes (recherche web, analyse de fichiers) au format standardisé MCP.
- **Serveurs MCP Externes** : Possibilité de se connecter à des serveurs MCP externes via le transport `stdio` pour étendre les capacités de l'IA (fichiers, git, bases de données, etc.).
- **Dégradation Gracieuse** : Le système continue de fonctionner parfaitement même si le SDK `mcp` n'est pas installé.
- **Autonomie de l'IA** : Ollama décide désormais intelligemment quand et comment utiliser les outils mis à sa disposition.

#### 🌐 Amélioration de la Recherche Web
- **Correction du Scraper Brave Search** : Résolution d'un problème de décodage HTML (Brotli) qui empêchait la récupération des résultats.
- **Extraction de Données en Temps Réel** : Optimisation du prompt Ollama pour prioriser les "Extraits de recherche" (snippets) plutôt que le contenu complet de la page, garantissant des informations à jour (ex: prix du Bitcoin).
- **Détection d'Intentions Étendue** : Ajout de mots-clés liés aux lieux (café, restaurant, proche, adresse, etc.) pour forcer la recherche web sur les requêtes locales.

# 🤖 Version 6.4.0 - Création d'Agents Personnalisés (11 Février 2026)

### 🚀 Nouveautés Principales

#### 🎨 Création d'Agents Personnalisés avec IA
- **Bouton "➕ Créer Agent"** : Interface modale pour créer vos propres agents
- **Génération automatique de system prompts** : Ollama génère le system prompt optimisé selon votre description
- **Température intelligente** : L'IA choisit automatiquement la température idéale (0.2-0.8) selon le rôle
- **Description courte automatique** : Génération d'un résumé de 3-4 mots pour l'affichage sur la carte
- **Couleurs aléatoires vibrantes** : Chaque agent personnalisé a une couleur unique et attrayante
- **Gestion complète** : Édition (📝) et suppression (✖) des agents personnalisés
- **Persistance JSON** : Sauvegarde automatique dans `data/custom_agents.json`

#### 🎯 Fonctionnalités d'Édition
- **Édition du nom et de la description** : Modifiez vos agents personnalisés à tout moment
- **Régénération intelligente du prompt** : Si vous changez la description, le system prompt est automatiquement régénéré
- **Édition rapide du nom** : Changement de nom instantané sans régénération
- **Interface modale réutilisable** : Même interface élégante pour création et édition

#### 🔧 Intégration Workflow
- **Drag & Drop** : Les agents personnalisés sont draggables comme les agents par défaut
- **Workflows mixtes** : Combinez agents par défaut et agents personnalisés dans vos workflows
- **Affichage en grille** : Les agents personnalisés apparaissent après les 9 agents par défaut
- **Icône unique** : Chaque agent personnalisé utilise l'emoji 🤖

### 📊 Format des Agents Personnalisés

Structure JSON d'un agent personnalisé :
```json
{
  "custom_AgentName_1234567890": {
    "name": "AgentName",
    "desc": "Description complète du rôle et des capacités de l'agent",
    "short_desc": "Résumé 3-4 mots",
    "color": "#3b82f6",
    "system_prompt": "System prompt généré par Ollama...",
    "temperature": 0.5
  }
}
```

### 💡 Exemples d'Agents Personnalisés

#### Agent Traducteur
- **Nom** : TranslatorAgent
- **Rôle** : Expert en traduction multilingue avec adaptation culturelle
- **Temperature** : 0.4 (précis mais naturel)

#### Agent SEO
- **Nom** : SEOAgent
- **Rôle** : Spécialiste en référencement naturel, optimisation de contenu et stratégie SEO
- **Temperature** : 0.6 (créatif mais structuré)

#### Agent DevOps
- **Nom** : DevOpsAgent
- **Rôle** : Expert en CI/CD, containerisation, Kubernetes et automatisation d'infrastructure
- **Temperature** : 0.3 (technique et précis)

---

# 🤖 Version 6.3.0 - Drag & Drop Agents, Workflows Personnalisés et Nouveaux Agents (9 Février 2026)

### 🚀 Nouveautés Principales

#### 🆕 3 Nouveaux Agents Spécialisés
- **SecurityAgent** 🛡️ : Cybersécurité, audit de sécurité, détection de vulnérabilités (temp: 0.2)
- **OptimizerAgent** ⚡ : Optimisation de performance, refactoring, profiling (temp: 0.3)
- **DataScienceAgent** 🧬 : Data science, machine learning, analyse prédictive (temp: 0.4)

#### 🎯 Drag & Drop pour création de Workflows
- **Glisser-déposer** les agents depuis leur carte vers la zone de workflow
- **Pipeline visuel** avec noms d'agents colorés et flèches (→) entre les étapes
- **Workflows personnalisés** : Construisez votre propre chaîne d'agents sans limite
- **Exécution séquentielle** : Chaque agent reçoit le résultat du précédent

#### ⏹️ Bouton Stop pendant la génération
- **Bouton Exécuter se transforme en bouton Stop** (■ blanc sur fond blanc) pendant la génération
- **Interruption immédiate** : Arrête le streaming et toutes les étapes du workflow
- **Restauration automatique** du bouton à son état original après l'arrêt
- Comportement identique au bouton Stop de l'onglet Chat

#### 🗑️ Suppression des Workflows pré-configurés
- Section "Workflows Multi-Agents" supprimée (redondante avec le drag & drop)
- Les workflows Développement Complet, Recherche & Doc, Debug Assisté sont remplacés par le système de drag & drop plus flexible

### 🎨 Améliorations UI

#### Refonte de la zone de saisie
- **Bouton Exécuter** : Plus grand (160px), s'adapte automatiquement à la hauteur de la zone de texte
- **Bouton Clear Workflow** : Rouge (#dc2626), permet de vider le workflow en un clic
- **Alignement parfait** : Les boutons s'étirent pour s'aligner avec le bas de la zone de texte
- **Cartes agents** : Description agrandie (police 13 bold), indication de drag & drop

#### Drag & Drop
- **Indicateur flottant** lors du glissement d'un agent
- **Zone de drop visuelle** avec bordure et feedback
- **Badges colorés** dans le pipeline avec la couleur de chaque agent
- **Suppression individuelle** d'agents du workflow (clic sur le badge)

### 🔧 Architecture Technique

#### Modifications
- **`models/ai_agents.py`** : 3 nouvelles factories (SecurityAgent, OptimizerAgent, DataScienceAgent), 9 agents au total
- **`interfaces/agents_interface.py`** : Réécriture complète — drag & drop, pipeline display, bouton stop, suppression workflows pré-configurés
- **`core/agent_orchestrator.py`** : Ajout du paramètre `on_should_stop` pour interruption inter-étapes

---

# 🤖 Version 6.2.0 - Système Multi-Agents IA (22 Janvier 2026)

### 🚀 Nouveautés Principales

#### 🤖 Système d'Agents IA Spécialisés
- **6 agents spécialisés** basés sur Ollama pour des tâches ciblées :
  - **CodeAgent** 💻 : Génération et débogage de code
  - **ResearchAgent** 🔍 : Recherche et documentation
  - **AnalystAgent** 📊 : Analyse de données et insights
  - **CreativeAgent** ✨ : Contenu créatif et rédaction
  - **DebugAgent** 🐛 : Débogage et correction d'erreurs
  - **PlannerAgent** 📋 : Planification et architecture de projets

#### 🎭 Interface Graphique Agents
- **Nouvelle interface avec onglets** : Chat et Agents séparés
- **Sélection visuelle d'agents** : Cartes cliquables avec descriptions
- **Workflows pré-configurés** :
  - 🔧 **Dev** : Planification → Génération de code → Débogage
  - 📚 **Research** : Recherche → Analyse → Documentation
  - 🐛 **Debug** : Analyse d'erreur → Correction
- **Affichage en streaming** : Résultats affichés progressivement token par token
- **Statistiques en temps réel** : Tâches exécutées, agents actifs, taux de succès

#### ⚡ Orchestration Multi-Agents
- **Tâches simples** : Un agent pour une tâche spécifique
- **Workflows séquentiels** : Plusieurs agents travaillent en chaîne
- **Exécution parallèle** : Plusieurs agents sur différents aspects en simultané
- **Transmission de contexte** : Les résultats d'un agent alimentent le suivant
- **Mémoire d'agent** : Chaque agent garde l'historique de ses tâches

#### 🎨 Interface Moderne
- **Boutons Chat/Agents centrés** dans la barre supérieure
- **Zone de résultats en lecture seule** : Protection contre les modifications accidentelles
- **Design cohérent** : Style Claude maintenu sur tous les onglets
- **Navigation fluide** : Basculement instantané entre Chat et Agents

#### 🛠️ Intégration CLI
Nouvelles commandes dans l'interface en ligne de commande :
```bash
agent <type> <tâche>          # Exécuter un agent spécifique
workflow <type> <description>  # Lancer un workflow multi-agents
agents                        # Lister tous les agents disponibles
```

### 📚 Documentation

#### Nouveaux Guides
- **`docs/AGENTS.md`** : Documentation complète du système d'agents
- **`docs/AGENTS_GUI.md`** : Guide d'utilisation de l'interface graphique

### 🎯 Exemples d'Usage

#### Interface Graphique
1. **Cliquer sur l'onglet "Agents"** en haut au centre
2. **Sélectionner un agent** (ex: CodeAgent)
3. **Décrire la tâche** : "Crée une fonction de tri rapide en Python"
4. **Cliquer sur "Exécuter"**
5. **Voir le résultat** apparaître progressivement en streaming

#### Workflows Multi-Agents
```bash
# Workflow de développement complet
1. PlannerAgent → Architecture du projet
2. CodeAgent → Génération du code
3. DebugAgent → Vérification et correction
   
# Résultat : Projet complet et testé
```

#### Ligne de Commande
```bash
# Agent simple
agent code "Crée une classe Python pour gérer une liste de tâches"

# Workflow
workflow research "Intelligence artificielle dans la santé"

# Lister les agents
agents
```

### 🔧 Architecture Technique

#### Nouveaux Modules
- **`models/ai_agents.py`** (521 lignes)
  - Classe `AIAgent` : Base pour tous les agents
  - `AgentFactory` : Création d'agents pré-configurés
  - Système de prompts spécialisés par agent
  - Historique des tâches par agent

- **`core/agent_orchestrator.py`** (406 lignes)
  - `AgentOrchestrator` : Coordination des agents
  - `WorkflowTemplates` : Templates de workflows pré-configurés
  - Exécution simple, multi-agents, et parallèle
  - Streaming des résultats avec callbacks

- **`interfaces/agents_interface.py`** (916 lignes)
  - Interface graphique complète pour les agents
  - Gestion du threading pour exécution non-bloquante
  - Affichage en streaming des résultats
  - Suivi des statistiques en temps réel

#### Améliorations du Code
- **Streaming complet** : `execute_task_stream()` et `execute_multi_agent_task_stream()`
- **Callbacks** : `on_step_start`, `on_token`, `on_step_complete`
- **Zone de sortie protégée** : Mode readonly avec déblocage temporaire pour l'écriture
- **Interface à onglets** : Navigation centralisée entre Chat et Agents

### 🚦 Performances

- **Streaming temps réel** : Latence minimale, affichage progressif
- **Threading** : Exécution non-bloquante, interface toujours réactive
- **Mémoire optimisée** : Chaque agent a sa propre mémoire isolée
- **Réutilisation** : Les agents créés sont mis en cache et réutilisés

### 💡 Cas d'Usage

#### Développement
- Architecture de projet → Génération de code → Tests et débogage
- Code review automatisé avec DebugAgent
- Documentation automatique du code

#### Recherche
- Recherche de documentation → Analyse → Synthèse structurée
- Veille technologique multi-sources
- Création de rapports détaillés

#### Création de Contenu
- Brainstorming → Rédaction → Analyse qualité
- Articles de blog structurés
- Documentation technique accessible

---

# 🎨 Version 6.1.0 - Génération de Fichiers avec Ollama (14 Janvier 2026)

### 🚀 Nouveautés Principales

#### 📝 Génération de Fichiers Dynamique
- **Génération intelligente de code** : Ollama génère des fichiers complets et fonctionnels
- **Détection automatique** : Reconnaissance des commandes "génère moi un fichier..."
- **Support multi-langages** : Python, JavaScript, HTML, CSS, et plus encore
- **Code prêt à l'emploi** : Fichiers directement utilisables sans modification

#### 🧠 Intégration Contexte Ollama
- **Mémoire conversationnelle** : Ollama se souvient de toutes les générations de fichiers
- **Historique unifié** : LocalLLM partagé entre AIEngine et CustomAI
- **Contexte persistant** : Les générations de fichiers font partie de la conversation
- **Références croisées** : L'IA peut faire référence aux fichiers générés précédemment

### 🎯 Exemples d'Usage

#### Génération de Fichiers
```bash
🤖 "génère moi un fichier main.py qui me permet de jouer au morpion"
   → Génération d'un jeu de morpion complet avec interface console
   → Fichier téléchargeable directement via le nom cliquable

🤖 "crée moi un fichier index.html pour une page web moderne"
   → Génération HTML5 avec CSS moderne et responsive design
   → Prêt à ouvrir dans un navigateur

🤖 "génère un fichier calculator.py avec une calculatrice"
   → Calculatrice complète avec toutes les opérations de base
   → Code Python propre et commenté
```

#### Mémoire Contextuelle
```bash
# Jour 1
🤖 "génère moi un fichier main.py qui me permet de jouer au morpion"
   → ✅ Fichier généré

# Plus tard dans la conversation
🤖 "on a parlé de quoi aujourd'hui ?"
   → "Nous avons parlé de la génération d'un fichier main.py pour jouer au morpion..."

🤖 "peux-tu améliorer le fichier que tu m'as fait ?"
   → Ollama se souvient du fichier et peut le modifier
```

### 🔐 Sécurité et Stockage

#### Gestion des Fichiers
- **Sauvegarde automatique** : Copie dans `outputs/` pour historique
- **Téléchargement sécurisé** : Copie vers Downloads avec `shutil.copy2()`
- **Permissions préservées** : Métadonnées de fichier conservées
- **Nettoyage automatique** : Variables temporaires effacées après usage

---

# 🦙 Version 6.0.0 - Intégration Ollama & LLM Local (28 Novembre 2025)

### 🚀 Nouveautés Principales

#### 🦙 Intégration Ollama - LLM 100% Local
- **Support complet d'Ollama** : Exécution de modèles LLM directement sur votre machine
- **Architecture hybride intelligente** :
  - Si Ollama est disponible → Réponses générées par le LLM
  - Si Ollama est absent → Fallback automatique sur CustomAIModel (patterns)
- **Détection automatique** : Vérification au démarrage de la disponibilité d'Ollama
- **Modèle personnalisable** : Configuration via `Modelfile` à la racine du projet
- **100% confidentiel** : Aucune donnée n'est envoyée sur internet

#### 🔧 Nouveau Module LocalLLM
- **Fichier** : `models/local_llm.py`
- **Fonctionnalités** :
  - Connexion au serveur Ollama (`http://localhost:11434`)
  - Vérification de disponibilité du serveur
  - Détection des modèles installés (my_ai → llama3 fallback)
  - Génération de réponses via l'API Ollama
  - Injection de system prompt personnalisé
  - Gestion des timeouts et erreurs

#### 📄 Configuration Modelfile
```dockerfile
FROM llama3.1:8b
PARAMETER temperature 0.7
PARAMETER num_ctx 8192

SYSTEM """
Tu es My_AI, un assistant IA personnel expert et bienveillant.
Réponds toujours en français par défaut.
"""
```

### 🎯 Modes de Fonctionnement

| Mode | Condition | Qualité Réponses |
|------|-----------|------------------|
| **Ollama** | Ollama installé et lancé | LLM complet, conversations naturelles |
| **Fallback** | Ollama non disponible | Patterns, règles |

### 📊 Modèles Recommandés par RAM

| RAM | Modèle | num_ctx | Performance |
|-----|--------|---------|-------------|
| 8 GB | `llama3.2` (3B) | 4096 | Rapide |
| 16 GB | `llama3.1:8b` | 8192 | Équilibré ✅ |
| 32 GB | `llama3.1:70b` | 16384 | Maximum |

### 🛠️ Installation Ollama

```bash
# 1. Télécharger depuis https://ollama.com/download
# 2. Installer le modèle
ollama pull llama3.1:8b

# 3. Créer modèle personnalisé
.\create_custom_model.bat
```

### 📝 Messages au Démarrage

**Avec Ollama :**
```
✅ [LocalLLM] Ollama détecté et actif sur http://localhost:11434 (Modèle: my_ai)
```

**Sans Ollama :**
```
⚠️ [LocalLLM] Ollama non détecté. Le mode génératif avancé sera désactivé.
```

### 🔐 Sécurité & Confidentialité
- **100% local** : Tout reste sur votre machine
- **Aucune API cloud** : Pas de dépendance à OpenAI, Anthropic, etc.
- **Fonctionne hors-ligne** : Une fois Ollama et le modèle téléchargés
- **Données privées** : Vos conversations ne quittent jamais votre PC

### 📚 Documentation Mise à Jour
- **README.md** : Section Ollama ajoutée
- **ARCHITECTURE.md** : Flux avec Ollama en priorité
- **INSTALLATION.md** : Guide installation Ollama
- **OPTIMIZATION.md** : Configuration modèles par RAM
- **USAGE.md** : Modes de fonctionnement expliqués

---

# 🌤️ Version 5.7.0 - Météo Temps Réel & Mémoire Vectorielle (19 Novembre 2025)

### 🚀 Nouveautés Principales

#### 🌤️ Météo Temps Réel Intégrée
- **Service météo gratuit wttr.in** : Récupération des données météo sans clé API
- **Détection automatique** : L'IA reconnaît les questions météo et répond instantanément
- **Données en temps réel** :
  - Conditions météorologiques actuelles
  - Température et ressenti
  - Humidité et précipitations
  - Vitesse et direction du vent
  - Prévisions sur 3 jours
- **Support multi-villes** : Plus de 40 villes françaises reconnues automatiquement
- **Gestion d'erreurs intelligente** : Fallback vers liens Météo-France si service indisponible
- **Format convivial** : Réponses structurées avec emojis et liens cliquables

#### 🧠 Système de Mémoire Vectorielle (Vector Memory)
- **Architecture ML avancée** : Remplacement complet de l'ancien `million_token_context_manager`
- **Tokenization précise** : Utilisation de tiktoken cl100k_base (compatible Llama 3, vs 70% avant)
- **Recherche sémantique** : Embeddings sentence-transformers (384 dimensions)
  - Comprend le **sens** des questions, pas juste les mots
  - Trouve les synonymes et concepts similaires automatiquement
  - Similarité cosinus pour résultats ultra-pertinents
- **Base vectorielle ChromaDB** :
  - Stockage persistant sur disque (SQLite + Parquet)
  - Collections séparées (conversations, documents)
  - Recherche ultra-rapide (0.02s dans 1M tokens)
- **Capacités étendues** :
  - 1,000,000 tokens de contexte réel
  - Chunks de 512 tokens avec overlap de 50 tokens
  - Chiffrement AES-256 optionnel pour données sensibles
- **Persistance totale** : Toutes vos conversations et documents sauvegardés automatiquement

#### 🔍 Recherche Internet Optimisée
- **Réorganisation des moteurs** : DuckDuckGo API Instant en priorité #1
- **Performance améliorée** : 
  - Plus de timeouts Wikipedia grâce au nouvel ordre
  - Cloudscraper en fallback pour contourner les CAPTCHA
  - Gestion intelligente des erreurs réseau
- **Support étendu** : Détection automatique questions météo vs recherche classique

### 🛠️ Améliorations Techniques

#### 🗄️ Structure Memory/
```
memory/
├── vector_memory.py          # Gestionnaire mémoire vectorielle
├── vector_store/             # Stockage persistant (ignoré par Git)
│   ├── chroma_db/           # Base ChromaDB (SQLite + vecteurs)
│   └── README.md            # Documentation complète du système
└── __init__.py
```

#### 📊 Comparaison Performances

| Métrique | Ancien (v5.6) | Nouveau (v5.7) | Amélioration |
|----------|---------------|----------------|--------------|
| **Comptage tokens** | Mots (~70% précis) | tiktoken cl100k_base | Précision maximale |
| **Recherche** | Mots-clés exact | Sémantique | Comprend synonymes |
| **Vitesse recherche** | O(n) linéaire | O(log n) vectorielle | 100x plus rapide |
| **Persistance** | Perdu au redémarrage | ChromaDB permanent | ♾️ |
| **Capacité stable** | ~300K tokens | 1M+ tokens | +233% |
| **Météo** | ❌ Non disponible | ✅ Temps réel | Nouveau |

#### 🔐 Sécurité & Confidentialité
- **Données locales** : dossier `memory/vector_store/` exclu de Git (.gitignore)
- **Chiffrement optionnel** : AES-256 pour protéger conversations sensibles
- **Aucune API externe** : wttr.in gratuit, pas de clé requise
- **100% privé** : Tous vos documents restent sur votre machine

### 🎯 Exemples d'Usage Nouveaux

#### Météo
```bash
🤖 "Quelle est la météo à Toulouse ?"
   → Conditions actuelles + température + humidité + vent + prévisions 3 jours

🤖 "Quel temps fait-il à Paris aujourd'hui ?"
   → Données temps réel mises à jour automatiquement

🤖 "Température à Lyon ?"
   → Réponse instantanée avec toutes les infos météo
```

#### Mémoire Vectorielle
```bash
# Jour 1
🤖 "Crée une fonction Python pour parser du JSON"
   → Assistant crée le code et le sauvegarde dans vector_memory

# Jour 15 (2 semaines après)
🤖 "Comment je parse du JSON déjà ?"
   → Assistant retrouve la conversation du Jour 1 grâce à la recherche sémantique
   → "Voici le code que je t'ai donné il y a 2 semaines : ..."
```

### 🐛 Corrections Majeures

#### Recherche Internet
- ✅ **Ordre des moteurs corrigé** : API Instant prioritaire (était en 3ème)
- ✅ **Timeouts Wikipedia résolus** : Contournement proxy entreprise
- ✅ **DuckDuckGo Lite abandonnée** : Status 202 + CAPTCHA trop fréquents
- ✅ **Gestion erreurs améliorée** : Messages clairs au lieu de crash

#### Million Token Manager
- ✅ **Comptage tokens cassé** : Remplacé par tiktoken (cl100k_base)
- ✅ **Recherche inefficace** : Remplacée par recherche vectorielle
- ✅ **Perte de données** : ChromaDB sauvegarde tout automatiquement
- ✅ **Chunks mal coupés** : Overlap intelligent de 50 tokens

### 🔧 Configuration

#### Activer le Chiffrement
```python
from memory.vector_memory import VectorMemory

vm = VectorMemory(
    enable_encryption=True,
    encryption_key="votre-clé-32-caractères-ici"
)
```

#### Augmenter la Capacité Mémoire
```python
vm = VectorMemory(
    max_tokens=2_000_000,  # 2M tokens au lieu de 1M
    chunk_size=1024,       # Chunks plus grands
    chunk_overlap=100      # Plus de contexte
)
```

### 📚 Documentation Mise à Jour
- **memory/vector_store/README.md** : Guide complet du système vectoriel
- **.gitignore** : Exclusion données personnelles (chroma_db, *.sqlite3, etc.)

---

# ✨ Version 5.6.0 - Refonte PEP 8 & Résumé d'URL (28 Octobre 2025)

### 🚀 Nouveautés principales

#### 🔗 Résumé automatique d'URL
- **Fonctionnalité de résumé de pages web** : L'IA peut désormais visiter et résumer automatiquement le contenu de n'importe quelle URL
- **Détection intelligente d'URL** : Reconnaissance automatique des demandes de résumé avec patterns variés
  - "Résume cette page : [lien]"
  - "Résume ce lien : [lien]"
  - "Que contient cette page : [lien]"
  - "Résume ceci : [lien]"
- **Extraction de contenu avancée** :
  - Parsing HTML intelligent avec BeautifulSoup
  - Extraction du contenu principal (article, main, .content)
  - Nettoyage automatique des scripts, styles, nav, footer
  - Support multi-stratégies pour différents formats de sites
- **Résumés structurés** :
  - Titre de la page
  - URL source
  - Top 5 des phrases clés
  - Statistiques (nombre de mots, phrases)
  - Mots-clés principaux automatiquement extraits
- **Cache intelligent** : Mise en cache des résumés pour éviter les requêtes répétées (TTL: 1h)
- **Gestion d'erreurs complète** : Timeout, 404, 403, erreurs de connexion avec messages explicites

#### 🧹 Refonte PEP 8 & Qualité du code
- **Normalisation complète du code Python** selon les standards PEP 8
- **Organisation améliorée** : Tous les fichiers Python refactorisés pour une meilleure lisibilité
- **Cohérence des conventions** :
  - Noms de variables et fonctions en snake_case
  - Noms de classes en PascalCase
  - Constantes en MAJUSCULES
  - Documentation docstrings standardisée
- **Imports optimisés** : Ordre et organisation des imports selon PEP 8
- **Espacement et formatage** : Respect strict des règles de formatage Python

### 🎯 Exemples d'usage nouveaux
```bash
🤖 "Résume cette page : https://fr.wikipedia.org/wiki/Tour_Eiffel"
🤖 "Résume ce lien : https://www.python.org"
🤖 "Que contient cette page : https://github.com/anthropics"
🤖 "Résume ceci : https://www.example.com/article"
```

---

# 🟢 Version 5.5.0 - Génération de code par API & Simplification Architecture (29 Septembre 2025)

### 🚀 Nouveautés principales

#### 🌐 Génération de code par API
- Ajout de la génération de code automatisée via des APIs externes : GitHub, Stack Overflow, etc.
- Recherche et intégration de solutions de code en temps réel depuis des sources web spécialisées.

#### 🏗️ Simplification de l'architecture
- Refactoring et simplification des modules principaux pour une meilleure maintenabilité.
- Réduction de la complexité des imports et des dépendances internes.
- Documentation technique mise à jour pour refléter la nouvelle structure.

#### 🐞 Corrections et améliorations
- Optimisation des performances lors de la génération et de l'intégration de code externe.
- Correction de bugs mineurs liés à la gestion des API et à la modularité.

---

# 🚀 Version 5.0.0 - SYSTÈME 1 MILLION DE TOKENS RÉEL (3 Septembre 2025)

### 🎯 RÉVOLUTION ULTRA : 1,048,576 TOKENS DE CONTEXTE RÉEL

#### 💥 Capacités Ultra-Étendues
- **1,048,576 tokens de contexte RÉEL** (1M tokens, vs 4K-8K standards)
- **Architecture 100% locale** avec persistance SQLite optimisée
- **Compression intelligente multi-niveaux** : 2.4:1 à 52:1 selon le contenu
- **Gestion automatique de la mémoire** et auto-optimisation
- **Recherche sémantique ultra-rapide** avec TF-IDF et similarité cosinus

#### 🧠 Nouveaux Composants Ultra
- **UltraCustomAI** : Modèle principal avec contexte étendu
- **IntelligentContextManager** : Gestionnaire de contexte intelligent avec ML
- **MillionTokenContextManager** : Persistance et compression avancée
- **FileProcessor** : Processeur unifié pour tous types de fichiers
- **GUI Ultra Modern** : Interface optimisée pour le système 1M tokens

#### 🔧 Améliorations Techniques Majeures
- **Chunking intelligent** avec détection automatique de blocs logiques
- **Compression adaptative** : texte, code, documents selon leur nature
- **Base de données SQLite** avec indexation pour performances optimales
- **Système de fallback** pour toutes les dépendances optionnelles (sklearn, etc.)
- **Architecture modulaire** avec imports robustes et gestion d'erreurs

#### 🎨 Interface Utilisateur Ultra
- **Support des blocs de code Python** avec coloration syntaxique Pygments
- **Formatage Markdown avancé** avec gras, italique, liens cliquables
- **Animation de frappe** optimisée pour les réponses longues (1M tokens)
- **Hauteur adaptative** automatique selon le contenu des réponses
- **Nettoyage des messages de debug** pour une expérience utilisateur fluide

#### 🐛 Corrections et Stabilité
- **Résolution des erreurs d'import** : chemins corrigés, dépendances installées
- **Compatibility multiplateforme** avec fallbacks pour toutes les librairies
- **Gestion d'erreurs robuste** dans tous les composants critiques
- **Optimisation mémoire** pour éviter les débordements avec 1M tokens

#### 📊 Statistiques et Monitoring
- **Métriques en temps réel** : tokens utilisés, documents traités, chunks créés
- **Vérification système** automatique des composants Ultra
- **Logs optimisés** pour le débogage sans spam utilisateur

---

# 🧠 Version 4.0.0 - FAQ Thématique & Robustesse (25 Juillet 2025)

### ✨ Nouveautés Majeures

#### 📚 FAQ locale multi-fichiers thématiques
- Chargement automatique de tous les fichiers `enrichissement*.jsonl` du dossier `data/`
- Organisation possible par thèmes (culture, informatique, langues, sciences, synonymes, etc.)
- Ajout, modification ou suppression de fichiers sans redémarrage du code

#### 🧠 Matching FAQ prioritaire et ajustable
- La FAQ est toujours consultée en premier, même en mode asynchrone (GUI moderne)
- Seuils de tolérance aux fautes d’orthographe ajustables (TF-IDF et fuzzy)
- Matching exact, TF-IDF, puis fuzzy (rapide et robuste)

#### 🔧 Debug et logs simplifiés
- Suppression des logs verbeux (diffs, fuzzy, etc.)
- Logs clairs sur la normalisation et le matching

#### 🏗️ Robustesse et modularité
- Correction du routage asynchrone (FAQ prioritaire partout)
- Code plus modulaire pour l’enrichissement et la FAQ
- Support de l’enrichissement par thèmes pour une personnalisation maximale

### 📚 Documentation et guides mis à jour
- Tous les guides (README, QUICKSTART, etc.) expliquent le fonctionnement de la FAQ thématique
- Exemples d’organisation par thèmes et d’ajustement des seuils

---

## 🎨 Version 3.0.0 - INTERFACE GRAPHIQUE MODERNE (18 Juillet 2025)

### ✨ Révolution de l'Interface Utilisateur

#### 🎨 Interface Graphique Moderne Style Claude
- **Design moderne** : Interface sombre élégante inspirée de Claude
- **Bulles de chat optimisées** : 
  - Messages utilisateur avec bulles positionnées à droite
  - Messages IA sans bulle, texte simple et lisible
  - Hauteur adaptative automatique selon le contenu
  - Positionnement optimisé pour tous types d'écrans

#### 💬 Système de Messages Révolutionné
- **Formatage de texte avancé** : Support complet du texte en **gras** avec Unicode
- **Messages non-scrollables** : Remplacement des zones de texte par des labels simples
- **Animation de réponse** : Indicateurs visuels de réflexion et recherche internet
- **Timestamp automatique** : Horodatage discret pour chaque message

#### 🖱️ Fonctionnalités Interactives
- **Drag & Drop** : Glisser-déposer de fichiers PDF, DOCX et code directement
- **Raccourcis clavier** : 
  - Entrée : Envoyer message
  - Shift+Entrée : Nouvelle ligne
  - Ctrl+L : Effacer conversation
- **Boutons d'action** : Clear Chat, Aide, chargement de fichiers

#### 🎯 Design Responsive
- **Adaptation écran** : Optimisation automatique selon la taille d'écran
- **Polices adaptatives** : Tailles de police intelligentes par OS et résolution
- **Plein écran automatique** : Lancement en mode maximisé avec focus

### 🛠️ Architecture Technique Avancée

#### 📦 Nouvelles Dépendances UI
- `customtkinter>=5.2.0` : Framework UI moderne avec thèmes sombres
- `tkinterdnd2>=0.3.0` : Support drag & drop natif
- `pillow>=10.0.0` : Traitement d'images pour l'interface

#### 🎨 Système de Style Moderne
- **Couleurs modernes** : Palette sombre professionnelle avec accents colorés
- **Typographie adaptative** : Polices système optimisées (Segoe UI, SF Pro, Ubuntu)
- **Animations fluides** : Indicateurs de statut avec animations personnalisées

#### 🔧 Optimisations Performance
- **Rendu optimisé** : Labels au lieu de zones de texte pour de meilleures performances
- **Scroll intelligent** : Défilement automatique vers les nouveaux messages
- **Mémoire efficace** : Gestion optimisée de l'historique des conversations

### 📝 Fonctionnalités Texte Avancées
- **Unicode Bold** : Conversion automatique `**texte**` vers 𝐭𝐞𝐱𝐭𝐞 en gras Unicode
- **Formatage intelligent** : Préservation de la mise en forme dans les labels
- **Wrapping automatique** : Adaptation du texte à la largeur des bulles

### 🚀 Expérience Utilisateur
- **Interface intuitive** : Design inspiré des meilleures pratiques de Claude
- **Feedback visuel** : Animations de réflexion et recherche internet
- **Gestion d'erreurs** : Messages d'erreur élégants avec notifications temporaires
- **Message de bienvenue** : Introduction claire des fonctionnalités disponibles

---

## 🌐 Version 2.3.0 - RECHERCHE INTERNET (11 Juillet 2025)

### ✨ Nouvelles Fonctionnalités Majeures

#### 🌐 Recherche Internet Intelligente
- **Moteur de recherche intégré** : Accès en temps réel aux informations web
  - API DuckDuckGo pour recherches anonymes et rapides
  - Extraction automatique du contenu des pages web
  - Résumés intelligents des résultats de recherche
  - Support multilingue avec priorité au français

#### 🧠 IA Contextuelle Avancée
- **Reconnaissance d'intentions étendues** :
  - Nouveau pattern `internet_search` avec 15+ variations
  - Détection automatique du type de recherche (actualités, tutoriels, définitions)
  - Extraction intelligente des requêtes depuis le langage naturel
  - Adaptation des réponses selon le contexte de recherche

#### 🛠️ Architecture Technique
- **Nouveau module** : `models/internet_search.py`
  - Classe `InternetSearchEngine` complète et robuste
  - Gestion d'erreurs avancée avec retry automatique
  - Timeout adaptatif et headers anti-détection
  - Traitement parallèle de multiples sources web

### 🎯 Exemples d'Usage Nouveaux
```bash
🤖 "Cherche sur internet les actualités Python"
🤖 "Recherche des informations sur l'IA en 2025"  
🤖 "Trouve-moi comment faire du pain"
🤖 "Peux-tu chercher les dernières news sur Tesla ?"
🤖 "Informations sur le réchauffement climatique"
```

### 📦 Nouvelles Dépendances
- `requests>=2.31.0` : Requêtes HTTP robustes
- `beautifulsoup4>=4.12.0` : Extraction de contenu web
- `lxml>=4.9.0` : Parsing HTML haute performance

### 🔧 Améliorations Système
- **Interface utilisateur** : Aide mise à jour avec exemples de recherche
- **Documentation** : README et guides enrichis avec la recherche internet
- **Configuration** : Support des proxies et paramètres réseau
- **Logs** : Traçabilité complète des recherches internet

---

## 🚀 Version 2.2.0 - IA Locale Avancée (10 Juillet 2025)

### 🎯 Fonctionnalités Majeures

#### 🧠 Reconnaissance d'Intentions Avancée
- **Nouvelles intentions détectées** :
  - Salutations étendues : "slt", "bjr", "salut", "bonjour", "hello", etc.
  - Questions sur le code : Distinction automatique des questions techniques
  - Questions sur documents : Référencement intelligent aux documents traités
  - Conversations générales : Gestion adaptative des échanges libres

#### 💾 Mémoire Conversationnelle Intelligente
- **Stockage contextuel** : Documents et code traités restent en mémoire
- **Référencement croisé** : L'IA fait référence aux éléments précédents
- **Persistance de session** : Continuité des conversations
- **Clear intelligent** : Remise à zéro complète avec gestion d'état

#### 📄 Traitement de Documents Amélioré
- **Analyse universelle** : Support PDF et DOCX avec structure préservée
- **Mémorisation automatique** : Contenu immédiatement disponible pour questions
- **Résumés contextuels** : Format adaptatif selon le type de document
- **Extraction intelligente** : Points clés et thèmes automatiquement identifiés

### 🔧 Améliorations Techniques

#### Architecture 100% Locale
- **Suppression des dépendances externes** : Plus besoin d'Ollama, OpenAI, etc.
- **Moteur IA custom** : Logique de raisonnement développée spécialement
- **Patterns linguistiques locaux** : Reconnaissance d'intentions sans API
- **Base de connaissances intégrée** : Informations stockées localement

#### Interface Utilisateur
- **GUI moderne** : Interface Tkinter optimisée et intuitive
- **Bouton Clear Chat** : Remise à zéro complète avec confirmation
- **Gestion d'erreurs robuste** : Messages clairs et récupération gracieuse
- **Glisser-déposer** : Chargement direct de fichiers PDF/DOCX

#### Gestion des Réponses
- **Formatage adaptatif** : Réponses formatées selon le type de question
- **Extraction intelligente** : Gestion des réponses complexes et imbriquées
- **Cohérence contextuelle** : Références aux éléments précédemment traités
- **Prévention des doublons** : Évite les réponses répétitives

### 🐛 Corrections de Bugs

#### Détection d'Intentions
- **Faux positifs corrigés** : Questions d'identité/capacités vs questions sur documents
- **Patterns améliorés** : Structure des patterns linguistiques corrigée
- **Fallback intelligent** : Gestion améliorée des intentions non reconnues
- **Debug intégré** : Logs de débogage pour diagnostic facile

#### Mémoire et Stockage
- **Synchronisation** : Session context synchronisé avec la mémoire
- **Stockage de code** : Méthode `store_code_content` ajoutée
- **Gestion d'erreurs** : Récupération gracieuse en cas de problème de mémoire
- **Clear complet** : Effacement de toutes les données de session

#### Interface et UX
- **Message de bienvenue** : Réaffiché après clear chat
- **Formatage des réponses** : Gestion des dictionnaires et types complexes
- **Gestion des erreurs** : Messages d'erreur clairs et utiles
- **Navigation fluide** : Workflow utilisateur optimisé

### 📚 Documentation Mise à Jour

#### Documentation Complète
- **README.md** : Vue d'ensemble actualisée avec fonctionnalités 100% locales
- **ARCHITECTURE.md** : Structure technique mise à jour
- **USAGE.md** : Guide d'utilisation avec exemples d'intentions
- **INSTALLATION.md** : Installation simplifiée sans dépendances externes

#### Guides et Exemples
- **QUICKSTART_NEW.md** : Guide de démarrage rapide moderne
- **examples/intention_detection.py** : Démonstration des intentions
- **examples/workflow_examples.py** : Scénarios d'usage complets
- **README exemples mis à jour** : Nouveaux cas d'usage documentés

### 🔒 Sécurité et Confidentialité

#### Protection des Données
- **100% Local** : Aucune donnée n'est envoyée à l'extérieur
- **Stockage sécurisé** : Tous les fichiers restent sur votre machine
- **Mémoire privée** : Conversations et documents confidentiels
- **Pas de télémétrie** : Aucun tracking ou envoi de statistiques

#### Isolation Complète
- **Pas d'internet requis** : Fonctionnement hors ligne après installation
- **Pas d'API externes** : Indépendance totale des services cloud
- **Contrôle total** : Utilisateur maître de ses données
- **Audit transparent** : Code source ouvert et vérifiable

### 🚀 Performances

#### Optimisations
- **Démarrage rapide** : Initialisation optimisée de tous les composants
- **Mémoire efficace** : Gestion intelligente de la mémoire conversationnelle
- **Réponses rapides** : Traitement local sans latence réseau
- **Ressources minimales** : Fonctionnement optimal sur machines modestes

#### Stabilité
- **Gestion d'erreurs** : Récupération gracieuse en cas de problème
- **Tests robustes** : Validation de tous les workflows utilisateur
- **Logging intégré** : Suivi des opérations pour diagnostic
- **Fallbacks intelligents** : Alternatives en cas d'échec

### 🔮 Évolutions Futures Planifiées

#### Fonctionnalités à Venir
- **Extension VS Code** : Intégration directe dans l'éditeur
- **API REST locale** : Interface pour intégrations tierces
- **Support de langages** : Extension à d'autres langages de programmation
- **Interface web** : Version navigateur pour usage distant

#### Améliorations Techniques
- **Modèles LLM optionnels** : Support optionnel de modèles externes
- **Cache intelligent** : Mise en cache des résultats fréquents
- **Plugins système** : Architecture de plugins pour extensions
- **Synchronisation** : Sync optionnelle entre instances

---

## 📋 Versions Précédentes

### Version 2.1.0 - Interface Graphique
- Ajout de l'interface GUI Tkinter
- Traitement de fichiers PDF/DOCX
- Gestion de base des conversations

### Version 2.0.0 - Architecture Modulaire
- Refactorisation complète de l'architecture
- Séparation des responsabilités
- Modules spécialisés (processors, generators, etc.)

### Version 1.0.0 - Version Initiale
- IA de base avec Ollama
- Interface CLI simple
- Fonctionnalités basiques de conversation

---

🤖 **My Personal AI** - Votre IA locale évolutive et sécurisée !
