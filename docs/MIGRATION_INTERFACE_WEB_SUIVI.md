# Migration de l'interface desktop vers le web — fichier de suivi

Ce fichier permet de reprendre la migration d'une session ou d'un PC à l'autre. Pour reprendre :
relire le prompt de mission (`MIGRATION_INTERFACE_WEB_PROMPT*.md`, jamais commité), puis ce
fichier, en commençant par « État actuel ».

- Branche : `feat/interface-web` (créée le 2026-10-12 depuis `main` à `543f083`).
- `main` garde l'interface Tk jusqu'à la fusion.

## État actuel

- **Phase 0 (préparation) terminée le 2026-10-12.** Décisions D1 à D13 (section 8).
- **Phase 1 (backend sans interface) terminée le 2026-10-12.** Décisions D14 et D15 (section 8).
- **Phase 2 (squelette de l'interface et cœur du Chat) terminée le 2026-10-13**, en attente du feu
  vert pour la phase 3. `frontend/` (Vite, React 19, TypeScript strict), fenêtre pywebview,
  `launch_unified.py --ui web|tk` (web par défaut sur la branche) et `--dev`. Vérifiée dans
  Chromium (Playwright, serveur de démonstration), puis dans la vraie fenêtre WebView2 avec le vrai
  Ollama. Détails, mesures et bogues corrigés dans le journal (section 12).
- Questions de la phase 2 : section 9 (« Questions de la phase 2 »), dont des **fichiers étrangers**
  apparus à la racine du dépôt pendant la session (question 18).
- Prochaine étape : phase 3 (plan proposé en section 15), après le feu vert de Nicolas.
- Outils de vérification, hors dépôt : `temp/migration_tools/` (serveur de démonstration, scripts
  Playwright, pilotage Win32 ; voir son README).

---

## 1. Environnement

### PC à RTX 3060 (vérifié le 2026-10-12)

| Élément | Valeur |
|---|---|
| Système | Windows 11 Home 10.0.26300 |
| Processeur, mémoire | Intel i7-12700H, 15,7 Go |
| Cartes graphiques | NVIDIA RTX 3060 Laptop (6 Go) + Intel Iris Xe |
| Écran | un seul, 1920 × 1080, échelle 100 % (96 DPI) |
| Python | 3.11.9 (Microsoft Store) |
| Node / npm | 22.12.0 (LTS) / 10.9.0 |
| Ollama | 0.40.3 ; modèles `my_ai`, `qwen3.5:4b`, `qwen3.5:2b`, `llava`, `minicpm-v` |
| WebView2 | 154.0.4258.62 |
| Office | Microsoft 365 x64 (16.0.20430) ; visionneuses `IPreviewHandler` enregistrées pour .docx, .xlsx, .pptx (et .pdf) |
| Micro | « Réseau de microphones (Technologie Intel Smart Sound) », 4 canaux ; sounddevice et faster-whisper installés |
| Génération d'image | ComfyUI portable déjà installé dans `tools/` |
| git | `core.autocrlf=true` (copie de travail en CRLF) ; identité locale du dépôt réglée sur `gonicolas12` / `nicolasgouy@yahoo.com` (l'identité globale est celle de Ynov) ; `credential.https://github.com.username` volontairement non réglé |

Où tourne le modèle :

- `data/.ollama_placement.json` : `placement: gpu`, `env: {"OLLAMA_KV_CACHE_TYPE": "q8_0"}`, `gpu_share: 100`,
  écriture 78 tok/s en 8 bits contre 45 en 16 bits, `num_ctx` 32 768 (mesuré le 2026-10-11).
- `ollama ps` avec l'Ollama de l'application bureau (lancé avec Windows, sans les variables du lanceur) :
  `my_ai` à 32 768 de contexte occupe 4,8 Go, **23 %/77 % CPU/GPU**. Avec l'Ollama du lanceur, le
  placement annonce 100 % GPU. Les mesures de la phase 1 et de la phase 2 se font donc avec l'Ollama du
  lanceur (`launch_unified.py`, `--headless`), pas avec celui de l'application bureau.

Paquets Python : fastapi 0.115.8, uvicorn 0.34.0, starlette 0.45.3, websockets 15.0.1, pydantic 2.13.4,
pytest 8.4.2, pytest-asyncio 1.1.0, httpx 0.28.1. pywebview et Playwright ne sont pas installés.

### PC à GPU intégré Intel Arc (à vérifier sur place)

- Python 3.14 : **pythonnet 3.0.5 s'arrête à Python 3.13**. Il faut `pythonnet>=3.1` (3.1.0, mai 2026,
  Python 3.10 à 3.14) ; la dernière, 3.2.1 (8 octobre 2026), couvre 3.11 à 3.15. Sans contrainte, pip prend 3.2.1.
- Node : Vitest 5 exige Node `^22.12.0 || ^24 || >=26`, Vite 8 `^20.19.0 || >=22.12.0`. À vérifier là-bas.
- Placement : le contexte en 8 bits n'a jamais été vérifié sur ce PC (cf. mémoire du projet).

### pywebview et pythonnet

- pywebview 6.2.1 (avril 2026) ; sous Windows il dépend de `pythonnet` (non épinglé), `proxy_tools`, `bottle`.
- `pip install --dry-run pywebview` sur ce PC : installerait `pywebview-6.2.1 pythonnet-3.2.1
  clr_loader-0.3.1 cffi-2.1.1 bottle-0.13.4 proxy_tools-0.1.0`. cffi passerait en 2.1.1 (à surveiller :
  cryptography en dépend). Rien n'a été installé en phase 0.

### Stack front (versions npm du 2026-10-12)

react 19.3.0, vite 8.3.4, @xyflow/react 12.12.0, react-virtuoso 4.18.16, zustand 5.0.15, streamdown 2.7.0,
react-markdown 10.1.0, remark-gfm 4.0.1, shiki 4.5.0, katex 0.19.0, cmdk 1.1.1, lucide-react 1.55.0,
tailwindcss 4.3.3, @fontsource/inter 5.3.0, @fontsource/jetbrains-mono 5.3.0, vitest 5.0.4,
@testing-library/react 16.3.3, @radix-ui/react-dialog 1.3.0, playwright 1.64.0.

- **TypeScript** : la dernière (7.0.2, compilateur natif) n'est pas prise en charge par typescript-eslint
  8.71.1 (`typescript >=4.8.4 <6.1.0`). Prendre la dernière 6.0.x.
- **Streamdown** dépend de `rehype-raw` (avec `rehype-sanitize` et `rehype-harden`) : le HTML brut est
  assaini, mais il faut le désactiver explicitement (contrainte de sécurité du §4). Choix à faire en phase 2
  entre Streamdown (gère le Markdown incomplet pendant le streaming) et react-markdown + remark-gfm.

### Installé en phase 2 (2026-10-13)

- Python 3.11 : pywebview 6.2.1, pythonnet 3.2.1, clr_loader 0.3.1, bottle 0.13.4, proxy_tools
  0.1.0 ; cffi passé de 1.16.0 à 2.1.1 (accord de Nicolas). cryptography 45.0.5 fonctionne avec cffi
  2.1.1 (AES-GCM du Relay vérifié, suite de tests verte). `pip check` ne signale que deux conflits
  antérieurs, sans rapport (tf-keras, opencv et numpy).
- Playwright 1.64 (dépendance de développement de `frontend/`) : Chromium 1248 et son « headless
  shell » dans `%LOCALAPPDATA%\ms-playwright`, **environ 715 Mo sur disque** (les ~150 Mo annoncés
  étaient la taille du téléchargement).
- Node 22.12.0 est trop ancien pour ESLint 10 (Node ≥ 22.13) et jsdom 30 (≥ 22.22) : ESLint 9.39.5
  et jsdom 28.1.0 à la place. Reste un avertissement d'engine sans effet (eslint-visitor-keys 5,
  module de données). Conseillé sur les deux PC : Node ≥ 22.13.
- Versions du front : react 19.3.0, vite 8.3.4, @vitejs/plugin-react 6.1.2, typescript 6.0.3,
  typescript-eslint 8.71.2, tailwindcss 4.3.3, zustand 5.0.15, react-virtuoso 4.18.16,
  react-markdown 10.1.0, remark-gfm 4.0.1, remark-breaks 4.0.0, marked 18.1.1, remend 1.4.0,
  shiki 4.5.0, katex 0.19.0, remark-math 6.0.0, rehype-katex 7.0.1, lucide-react 1.55.0,
  @radix-ui/react-dialog 1.3.0, @radix-ui/react-tooltip 1.4.0, @fontsource-variable/inter et
  jetbrains-mono 5.3.0, vitest 5.0.4, prettier 3.9.10. `frontend/dist/` : 4,7 Mo, 88 fichiers
  (coloration du code et formules en morceaux chargés à la demande).

## 2. Ce que ce PC ne permet pas de vérifier

À faire sur le PC de travail, ou par Nicolas dans la vraie fenêtre :

- Échelles 125 % et 150 %, et deux écrans d'échelles différentes (un seul écran à 100 % ici ; je ne
  modifie pas les réglages d'affichage).
- Python 3.14 + pythonnet ≥ 3.1 + pywebview (PC Arc).
- Placement sur GPU intégré et contexte en 8 bits sur le PC Arc.
- macOS et Linux (`launch.sh`) : aucun des deux PC.
- Recette visuelle finale dans la fenêtre pywebview : je ne vois pas la fenêtre, seulement les captures
  Playwright (Chromium headless).

Vérifiable ici : Windows, WebView2, visionneuses Office natives, micro, carte NVIDIA, ComfyUI.

## 3. Tests de référence (phase 0)

`python -m pytest tests/` (avec `PYTHONIOENCODING=utf-8`, `-p no:cacheprovider`) : **930 réussis, aucun
échec, aucun ignoré, 31 avertissements, 3 min 48 s**. Aucun test ne demande de réponse au vrai Ollama.
Correction du 2026-10-12 (phase 1) : quand Ollama tourne, `test_ai_engine.py` et
`test_attachment_refusal.py` créent un vrai `AIEngine()`. Son préchauffage envoie alors « hi » à
Ollama et charge `my_ai`. La note de la phase 0 (« aucun modèle chargé après la suite ») était fausse.
Conséquence : ne pas lancer la suite pendant une mesure sur le vrai Ollama.

- Plus longs : `test_imports.py::test_agents_package_imports_on_its_own` (15,5 s),
  `test_agent_attachments.py::test_pdf_without_text_raises` (6,5 s),
  `test_edge_embed.py::test_close_terminates_the_real_browser_not_just_the_launcher` (5,3 s, lance le vrai
  Edge), les tests OCR (≈ 1,8 s chacun), `test_native_preview.py` (≈ 1,8 s, ouvre les vraies visionneuses Office).
- Liés à Tk ou à l'interface actuelle : `test_agent_attachments.py`, `test_agent_output_links.py`,
  `test_attachment_loading.py`, `test_chat_scroll.py`, `test_edge_embed.py`, `test_imports.py`,
  `test_native_preview.py`, `test_path_links.py`, et `test_ollama_restart.py` (stubs de
  `interfaces.gui_modern`, `interfaces.onboarding`, `core.passage_embeddings`, `core.network`).
- `tests/test_real_1m_tokens.py`, `benchmark_10m_tokens.py` et `rag_pipeline.py` sont des scripts : pytest
  n'y collecte aucun test.

## 4. Données de test

Ce PC n'avait presque aucune donnée personnelle : aucune session (`data/workspaces/` absent), aucun agent
personnalisé, aucune tâche planifiée (seulement deux entrées d'historique), aucun historique de commandes,
aucun fait mémorisé (`data/knowledge_base/` absent).

Créées le 2026-10-12 par `temp/migration_test_data/seed_test_data.py` (dossier ignoré par git, jamais
commité) :

- 4 sessions au format exact de l'interface Tk : « Projet API REST » (réflexion, code, tableau, règle,
  citations `[n]` et bloc Sources, chemin de fichier existant, PDF joint, artefact HTML, tour édité avec
  deux variantes et une suite), « Analyse d'images et recettes » (image jointe, slash command, formule
  `$E = mc^2$`), « Documents et génération » (génération de fichier, génération d'image, Excel,
  PowerPoint et code joints), « Conversation longue » (200 messages, pour le défilement) ;
- 3 agents personnalisés (TranslatorAgent, SEOAgent, DevOpsAgent) ;
- 3 prompts (`/email`, `/sql`, et un modèle sans commande) ;
- 4 tâches planifiées **désactivées**, sans rattrapage (quotidienne, hebdomadaire, intervalle, cron) ;
- 12 entrées d'historique de commandes, dont 3 favoris ;
- 3 workflows au format `WorkflowCanvas.to_dict` dans `temp/migration_test_data/workflows/`
  (pipeline, DAG, nœuds isolés) ;
- pièces jointes réelles dans `temp/migration_test_data/fichiers/` (PDF, DOCX, XLSX, PPTX, PNG, CSV, .py).

Les fichiers d'origine (`custom_agents.json`, `prompt_templates.json`, `scheduled_tasks.json`) sont
sauvegardés dans `temp/migration_test_data/backup/`. `remove_test_data.py` retire tout ce que liste
`manifest.json`.

Pas encore créés : les **faits mémorisés**. Ils sont injectés dans le prompt système de chaque réponse :
en créer maintenant changerait les réponses de l'assistant sur ce PC et les prompts mesurés en phase 1.
Je les créerai en phase 3, pour tester le panneau Mémoire, puis les retirerai. Les dossiers projet
attachés demandent une indexation ChromaDB : même traitement.

---

## 5. Checklist de parité (§7) avec les fichiers d'origine

Notation : « Tk » décrit le comportement actuel, à reproduire ; « Écart » signale une différence entre le
code, la documentation et §7.

### Structure générale

- [x] **En-tête avec les onglets Chat et Agents** — `interfaces/gui/layout.py` (`create_modern_header`,
  `create_tab_buttons`, `create_header_buttons`, `switch_tab`, `_update_header_buttons_visibility`).
  Tk : ☰ à gauche (onglet Chat, sidebar fermée), onglets « 💬 Chat » et « 🤖 Agents » centrés,
  « 🗑️ Clear Chat », « ❓ Aide » et une pastille ● verte à droite, masqués sur l'accueil et sur
  l'onglet Agents ; quitter l'onglet Chat ferme la sidebar. La pastille ne change jamais de couleur.
- [x] **Sidebar repliable avec Ctrl+B** — `interfaces/gui/sidebar.py` (`create_left_sidebar`,
  `toggle_sidebar`), raccourci dans `command_palette.py`. Tk : fermée au lancement, 260 px ; sections
  repliables Recherche globale, Sessions, Dossiers du projet, Historique, Export (toutes fermées au
  lancement).
- [x] **Écran d'accueil** — `interfaces/gui/base.py` (`_create_home_screen`, `_home_screen_send`,
  `_dismiss_home_screen`). Tk : 🤖 orange, « My_AI » en gras, saisie « Tapez votre message... », micro,
  menu ＋, « Envoyer ↗ », autocomplétion « / » ; les pièces jointes suivent quand on quitte l'accueil.
- [ ] **Assistant de premier lancement** — `interfaces/onboarding.py` (`OnboardingWizard`, `should_run`,
  `detect_ram_gb`, `detect_vram_gb`, `detect_cpu_cores`, `recommend_model`, `pull_model`,
  `apply_model_choice`, `create_custom_model`, `mark_done`), appelé par `launch_unified.py` (étape 3).
  Tk : « 🤖 Bienvenue dans My_AI », statut Ollama, matériel et recommandation, choix qwen3.5:2b/4b/9b,
  progression, journal, « 🚀 Installer » / « Passer » (marque l'assistant comme fait), « 🔄 Réessayer »,
  « ✅ Démarrer My_AI », « Continuer quand même ».
- [ ] **Aide F1** — `base.py` (`show_help`). Tk : sections Chat, Éditer & regénérer, Pièces jointes &
  documents, Recherche web & citations, Agents, Autres fonctions, Raccourcis clavier ; Échap ferme.

### Chat

- [x] **Streaming, bouton Stop et touche Échap** — `base.py` (`send_message`,
  `quel_handle_message_with_id`, `interrupt_ai`, `_set_send_button_stop`), `streaming.py`.
  Écart : dans Tk, **Échap n'arrête pas la génération** (il ferme seulement dialogues, palette et menus).
- [x] **Bloc « Réflexion » repliable** — `streaming.py` (`_create_reasoning_widget`,
  `_stream_thinking_token`, `_finalize_reasoning_widget`, `_toggle_reasoning_widget`). Tk : créé seulement
  pour une requête complexe (`is_complex_query`, non conversationnelle, sans image) ; « Raisonnement. .. ... »,
  déplié au premier jeton, masqué s'il reste vide ; en-têtes émis par l'orchestrateur « 🧠 Analyse : »,
  « 📋 Plan d'action : », « 💡 Synthèse : ». La réflexion **n'est pas enregistrée** dans la session.
- [x] **Indicateur d'outil MCP et confirmation de suppression** — `base.py` (`on_tool_call` et ses
  libellés, `_show_mcp_tool_indicator`, `_hide_mcp_tool_indicator`, `on_delete_confirm`,
  `_show_delete_confirmation_dialog`). Tk : « synthesis » masque l'indicateur et force un saut de
  paragraphe ; dialogue « L'IA souhaite supprimer ce fichier : », « Oui, supprimer » / « Non, annuler »,
  Échap ou fermeture = refus ; le fil du moteur attend la réponse.
- [ ] **Markdown complet** — `markdown_formatting.py`, `syntax_highlighting.py`,
  `streaming.py` (`_finish_streaming_animation`), `utils/citations.py`, `utils/path_links.py`.
  Écart : Tk n'a **pas de bouton Copier sur les blocs de code** (nouveau dans la cible). Citations : bloc
  « 📚 **Sources** » et marqueurs `[n]` ouverts dans le navigateur ; chemins existants →
  `reveal_in_file_manager`.
- [ ] **Pièces jointes** — `interfaces/gui/file_handling.py` (`process_dropped_file`, `process_file`,
  `process_file_background`, `_attachment_loading_started/finished`, `_attachment_removed`,
  `_forget_if_unused`, `_refuse_send_while_loading`, `_process_image_file`, `_on_paste`),
  `layout.py` (`add_file_preview`, `_hide_attachment_spinner`, `clear_file_previews`).
  Tk : menu ＋ (PDF, DOCX, Excel / CSV, PowerPoint, Code, Image, Dossier (codebase)) ; une seule image en
  attente (JPEG 1024 px) ; collage Ctrl+V vers un fichier temporaire au nom fixe ; retirer une pièce
  jointe arrête sa lecture et l'oublie si elle ne sert plus. Écart : le **glisser-déposer refuse les
  dossiers** (« ❌ Chemin invalide ») ; un dossier passe par « Dossiers du projet ».
- [ ] **Slash commands** — `slash_commands.py` (`_attach_slash_autocomplete`, `_slash_*`,
  `_expand_slash_command`), `core/prompt_library.py` (`expand`, `search`). La bulle garde la commande
  courte, le modèle reçoit le texte étendu.
- [ ] **Édition et régénération avec branches ‹ k/n ›** — `message_editing.py` (`_begin_edit`,
  `_apply_edit`, `_navigate`, `_persist_version`, `_rerender_all`, `_rewind_engine_history`,
  `_regenerate`). Tk : dialogue « Modifier le message », « Regénérer ↻ », refus pendant une génération ou
  sans réponse, texte inchangé = rien, avertissement si des messages suivent. Écart : **pas de
  « régénérer » sans modification** (§8 en demande un au survol).
- [x] **Copie d'un message** — `message_bubbles.py` (`copy_on_double_click`,
  `create_copy_menu_with_notification`), `message_editing.py` (`_copy_message`, bouton 📋 sous les
  messages de l'utilisateur).
- [ ] **Note de 1 à 5 étoiles** — `message_bubbles.py` (`_show_timestamp_for_current_message`,
  `_on_star_rating`), `core/rlhf_manager.py`. Tk : `record_interaction(user_query = texte de la bulle
  utilisateur, ai_response = texte affiché, feedback_type positive ≥ 4 / negative ≤ 2 / neutral,
  feedback_score, intent "conversation", confidence 1.0, model_version "ollama")` ; note figée ensuite.
- [ ] **Lecture vocale** — `voice_output.py` (`VoiceOutput`), `message_bubbles.py`
  (`_add_speak_button` : 🔊, ⏹ pendant la lecture, 🔇 en erreur), `sidebar.py` (`_make_tts_button`),
  réglage `ui.tts_autoread`.
- [ ] **Saisie vocale** — `voice_input.py` (`VoiceInput`, `_WhisperWorker`, `attach_mic_button`),
  `_whisper_worker.py`. Tk : modèle `small` int8 sur CPU ; processus séparé seulement si plusieurs
  runtimes OpenMP sont chargés (macOS) ou `MY_AI_WHISPER_WORKER=1`, avec repli mono-thread ; états
  idle / recording / transcribing / error ; insertion au curseur ; micro désactivé pendant une génération.
- [ ] **Génération d'image** — `base.py` (`_handle_image_generation_ui`, `_auto_setup_image_backend`,
  `_attach_generated_image`, `_remember_image_generation`), `models/comfyui_manager.py`,
  `core/ai_engine.py` (`is_image_generation_request`, `extract_image_prompt`, `image_generator`).
  Écart : la session enregistre le texte provisoire « Génération de l'image en cours… » ; **l'image est
  perdue au rechargement**.
- [ ] **Génération de fichiers et de documents** — `base.py` (branche « génération de fichier » :
  mots-clés, `process_query`, message tiré au hasard parmi 8, nom cliquable), `file_handling.py`
  (`download_file_to_downloads` : copie dans Téléchargements), `on_document` → `_pending_document_paths`.
- [ ] **Volet Artefacts** — `artifacts_panel.py`, `interfaces/artifacts.py`, `message_bubbles.py`
  (`_collect_artifacts`, `_add_artifact_button` « 🔍 Aperçu (n) », `_maybe_auto_open_artifact` : une fois
  par message, jamais à la restauration d'une session). Tk : volet 560 px réglable de 320 à 1200, boutons
  📂 (document), 🌐 (navigateur), ✕. Écart : **pas d'onglets Aperçu / Code** dans Tk (nouveau). Edge
  charge les ressources externes d'un artefact (CDN, polices).
- [ ] **Aperçu des documents** — `_preview_handler.py` (`NativePreview`, `AsyncNativePreview`,
  `supports_native_preview`, `NATIVE_EXTENSIONS`), `_dpi_host.py`, `artifacts_panel.py` (`_render_native`,
  « ⏳ Ouverture de l'aperçu Word… »), `interfaces/document_preview.py`. PDF : lecteur d'Edge.
- [ ] **Messages du mobile en direct, badge « Mobile »** — `base.py` (`_poll_relay_messages`,
  `_display_relay_message` avec le préfixe 📡, `_process_relay_attachments_then_ai`).
- [ ] **Fin de tâche planifiée : toast et notification système** — `base.py` (`_on_scheduled_task_done`,
  `_display_scheduled_result`, `_show_scheduled_toast` : 6 s, liseré vert / orange / rouge, clic = ouvre
  le rapport, seulement si `os_toast_shown` est faux), `core/scheduler.py`, `utils/desktop_notify.py`.
- [x] **Horodatage des messages** — `message_bubbles.py` (`_show_timestamp_for_current_message`, hh:mm
  sous la réponse), `message_editing.py` (`_add_edit_controls`, hh:mm sous la bulle utilisateur).
- [x] **Remise à zéro avec Ctrl+L** — `base.py` (`clear_chat`) : vide l'historique, les branches,
  `ai_engine.clear_conversation()`, `local_llm.clear_history()`, la mémoire de conversation (documents
  compris), le stockage Ultra, la liste `documents` du gestionnaire de contexte et `session_context`.
  L'appel à `vector_memory.clear_all()` ne s'exécute jamais (`CustomAIModel` n'a pas d'attribut
  `vector_memory`) : ChromaDB reste intact.

### Sidebar

- [ ] **Recherche globale** — `sidebar.py` (`_make_section_search`, `_global_search_run`,
  `_global_search_render`, `_global_search_open`, `_global_search_reindex`, `_highlight_in_chat`),
  `core/conversation_search.py`. Tk : 15 résultats « 🧑/🤖 session · extrait », surlignage des mots de la
  requête (sinon du message entier), effacé au clic.
- [x] **Sessions et workspaces** — `sidebar.py` (`_session_new`, `_session_save_current`,
  `_session_load`, `_session_delete`, `_refresh_sessions`), `core/session_manager.py`. Voir les écarts
  (section 7) : pas de sauvegarde automatique, Ctrl+N ne bascule pas sur la nouvelle session.
- [ ] **Dossiers projet** — `sidebar.py` (`_folder_attach`, `_folder_reindex`, `_folder_detach`,
  `_ensure_workspace_for_folder`, `_index_folder_async`), `core/folder_indexer.py`. Progression par
  notifications toutes les 10 fichiers ; un workspace est créé si aucun n'est actif.
- [ ] **Historique des requêtes** — `sidebar.py` (`_refresh_history`, `_history_toggle_fav`,
  `_history_delete`, `_history_reuse`), `core/command_history.py`. 20 entrées, recherche, « ⭐ Favoris
  uniquement », clic = texte remis dans la saisie.
- [ ] **Export Markdown, HTML ou PDF** — `sidebar.py` (`_export_conversation`),
  `core/conversation_exporter.py`.
- [ ] **Accès au Relay, à la lecture automatique, aux Réglages, à la Mémoire et aux Prompts** —
  `sidebar.py` (`_make_relay_button`, `_make_tts_button`, `_make_settings_button`,
  `_make_memory_button`, `_make_prompts_button`).

### Fenêtres et panneaux

- [ ] **Réglages** — `settings_panel.py` + utilitaires de `interfaces/onboarding.py`
  (`ollama_reachable`, `list_installed_models`, `pull_model`, `apply_model_choice`, `create_custom_model`,
  `apply_generation_params`, `set_config_flag`, `marker_path`). Modèles (liste sans `my_ai`, pull avec
  progression et journal, « ✅ Appliquer » avec confirmation) ; température 0–1 par pas de 0,05,
  num_ctx (2048 à 65536), timeout 30–7200 s, appliqués aussi à l'instance `LocalLLM` en cours ; langue
  par défaut, lecture automatique, `relay.auto_start`, relance de l'onboarding (supprime le marqueur).
- [ ] **Mémoire** — `memory_panel.py`, `core/memory_store.py` (`MemoryStore`). Onglets Faits / Documents /
  Conversations, recherche, filtre par catégorie, 20 par page, provenance, édition en ligne, « ➕ Ajouter »,
  suppression confirmée avec « Supprimer aussi le message d'origine ».
- [ ] **Prompts** — `prompts_panel.py`, `core/prompt_library.py` (`add`, `update`, `delete`).
- [ ] **Relay** — `base.py` (`_toggle_relay`, `_show_relay_info_popup`, `start_relay`, `stop_relay`,
  `_init_relay`). QR code (correction L, marge 4, redessiné quand la liste des tunnels est stable),
  statut des tunnels, URL copiable, « 🧩 Copier pour l'extension VS Code », jeton, appareils connectés,
  « Arrêter le Relay ».
- [ ] **Palette Ctrl+K et raccourcis** — `command_palette.py` (`_build_command_list`,
  `setup_command_palette_shortcuts`), `base.py` (`setup_keyboard_shortcuts`, `on_enter_key`),
  `layout.py`. Commandes : Nouveau chat, Effacer le chat, Sauvegarder la session, barre latérale, onglet
  Chat, onglet Agents, Relay, Réglages, Mémoire, Bibliothèque de prompts, Export ×3, Aide.

### Agents

- [ ] **Grille des 9 agents et agents personnalisés** — `interfaces/agents/agent_selection.py`,
  `custom_agents.py` (`_render_custom_agents_in_grid`, `_create_custom_agent_card` : icône 🤖, 📝, ✕).
  Le service `relay/agent_relay.py` (`list_agents`) donne aux agents personnalisés l'icône 🧩.
- [ ] **Agents personnalisés : créer, éditer, supprimer** — `custom_agents.py`, `relay/agent_relay.py`
  (`create_agent`, `edit_agent`, `delete_agent`, même prompt de génération), `data/custom_agents.json`.
- [ ] **Zone de tâche avec pièces jointes, collage d'image et micro** — `task_input.py`,
  `interfaces/agents/file_handling.py` (`_agent_load_file`, `_analyze_image_for_agent`,
  `_read_attached_file`), `processors/attachments.py`.
- [ ] **Exécution : agent seul, séquentiel, parallèle, DAG, Stop** — `execution.py`,
  `output_rendering.py`, `output_area.py` ; service : `relay/agent_relay.py` (`run_workflow`,
  `compute_execution_plan`, `interrupt`). Tk utilise son propre `AgentOrchestrator` (voir section 7).
- [ ] **Canvas de workflow** — `interfaces/workflow_canvas.py` (`to_dict`, `from_dict`,
  `get_execution_plan`), `drag_drop.py` (dépôt sur le canvas seulement), `workflow.py` (Save / Load /
  Export). Zoom 0,3 à 3, déplacement au clic milieu ou droit, grille avec aimantation, minimap,
  multi-sélection (Maj+clic, rectangle), Suppr, clic droit sur un lien pour le supprimer, liens de la
  couleur du nœud source. Statuts : gris `#6b7280`, jaune `#f59e0b`, vert `#10b981`, rouge `#ef4444`.
- [ ] **Mode Débat** — `debate.py`, `relay/agent_relay.py` (`run_debate`),
  `core/agent_orchestrator.py` (`execute_debate`). Proposant / Opposant, sujet, 1 à 10 tours.
- [ ] **Statistiques et moniteur de ressources** — `stats_section.py`, `interfaces/resource_monitor.py`.
  Tâches exécutées, agents actifs, taux de succès ; CPU, RAM, GPU, VRAM, inférence, tokens/s, barres
  colorées et mini-graphiques (60 mesures). Écart : **tokens/s toujours à 0** (Tk passe 0 à
  `update_inference`).
- [ ] **Tâches planifiées** — `scheduler_ui.py`, `core/scheduler.py`, `core/scheduler_runner.py`.
  Plannings quotidien, hebdomadaire (0 = lundi), intervalle, cron (croniter) ; « ▶ exécuter
  maintenant » ; source figée à l'édition ; « 🖥️ Exécuter même l'appli fermée » (Planificateur de tâches
  Windows).
- [ ] **Notification système à la fin d'une tâche longue** — `execution.py` (`_notify_task_complete` :
  plus de 8 s et fenêtre sans focus), `utils/desktop_notify.py`.

### Où en est la checklist après la phase 2

Cochés ci-dessus : terminés dans l'interface web (phase 2). En partie faits :

- **Markdown complet** : titres, listes, tableaux, citations, règles, code coloré avec Copier, liens
  ouverts dans le navigateur, formules (D9), sauts de ligne simples comme Tk. Restent pour la phase 3
  les citations web `[n]` cliquables et les chemins de fichiers cliquables.
- **Édition et régénération** : la navigation entre variantes ‹ k/n › fonctionne ; modifier un
  message et régénérer arrivent en phase 3.
- **Génération d'image** et **de fichiers** : progression et carte du fichier affichées ; afficher
  l'image, l'ouvrir en grand et ouvrir le fichier arrivent en phase 3.
- **Messages du mobile** : badge « Mobile » et affichage en direct prêts ; pas encore vérifiés avec
  un vrai téléphone.
- **Raccourcis** : Entrée, Maj+Entrée, Échap, Ctrl+B, Ctrl+N, Ctrl+L, Ctrl+S ; ceux du navigateur
  sont neutralisés (vérifié au vrai clavier). Ctrl+K, Ctrl+R, Ctrl+virgule et F1 en phase 3.
- **Accès au Relay, à la lecture automatique, aux Réglages, à la Mémoire, aux Prompts, à l'Export** :
  boutons en bas de la barre latérale, désactivés jusqu'à la phase 3 (question 20).

## 6. Inventaire complété (absent de §7, présent dans Tk)

- Notifications internes (`show_notification` : coin haut droit, couleurs info / succès / avertissement
  / erreur, 1,5 à 3 s) et notification de copie (`show_copy_notification`).
- Pièce jointe en cours de lecture : cercle orange dans la vignette, arrêt de l'OCR à la page suivante si
  on la retire.
- Clic sur le nom d'un fichier généré : copie dans le dossier Téléchargements.
- Défilement « suivi » : la vue suit la réponse sauf si l'utilisateur est remonté (`chat_area.py`).
- Variantes d'édition conservées avec leur suite (`tail`) et rattachées par `mid`.
- Réglages : journal des opérations (pull, création du modèle) et état d'Ollama.
- Agents : « 🖥️ Exécuter même l'appli fermée » (tâche du Planificateur Windows), « Vider » le workflow et
  le canvas, statut texte sous les boutons (« ⏳ Workflow visuel en cours... », « ⛔ Génération
  interrompue », « ✅ Tâche terminée avec … »), sections de sortie repliables par agent.
- Relay : nombre d'appareils connectés, URL locale en attendant les tunnels.

## 7. Écarts constatés entre le code, la documentation et §7

1. **Mobile pendant une génération desktop** : un nouveau message incrémente `current_request_id` ; la
   génération en cours devient obsolète (ses jetons sont ignorés et `is_interrupted_callback` l'arrête).
   Le dernier arrivé gagne. De plus, `send_message` ne remet pas `_current_message_from_relay` à faux : une
   réponse desktop qui suit un message mobile interrompu part vers le mobile.
2. **Réponse finale au mobile** : envoyée à la fin de l'*animation de frappe* Tk
   (`_finish_streaming_animation`), pas à la fin de la génération.
3. **Sessions** : aucune sauvegarde automatique (`workspaces.auto_save` et `SessionManager.auto_save` ne
   sont jamais utilisés) ; la session courante n'est pas retenue d'un lancement à l'autre ; Ctrl+S ne fait
   rien sans session courante ; Ctrl+N (« Nouveau chat ») demande un nom, crée une session vide et **ne
   bascule pas dessus**.
4. **Rechargement d'une session** : sans variantes d'édition, l'historique du LLM reste vide (le modèle ne
   voit pas la conversation rechargée) ; avec des variantes, `_rerender_all` le reconstruit. Le
   chargement passe par `clear_chat` (mémoire de conversation et documents de session vidés).
5. **Historique tronqué** : au-delà de 100 bulles, `_cleanup_old_messages` tronque `conversation_history`
   aux 100 derniers messages, donc la session enregistrée aussi.
6. **Réflexion et image générée** non enregistrées dans la session (voir section 5).
7. **Commandes « aide », « statut », « quitter »** : la documentation (`docs/USAGE.md`) les annonce dans
   l'interface graphique ; elles n'existent que dans la CLI (`interfaces/cli.py`).
8. **Export d'un workflow** : `docs/AGENTS_GUI.md` parle des résultats ; le code exporte la liste des
   nœuds et leur statut.
9. **Page Agents Tk** : elle utilise son propre `AgentOrchestrator`, distinct de l'exécuteur partagé du
   Relay et du scheduler (`docs/SCHEDULER.md` le signale : pas de report si occupé). Le chemin « workflow
   classique » (`_execute_custom_workflow_thread`) est mort : le dépôt ne se fait que sur le canvas.
10. **LaTeX** : les sorties d'agents remplacent `$\rightarrow$` et consorts par de l'Unicode
    (`_render_latex_symbols`) ; le chat Tk affiche le LaTeX brut. L'IA en produit donc.
11. **Adresse d'écoute** : le Relay écoute sur `0.0.0.0` (`relay.host`) ; l'API desktop écoutera sur
    127.0.0.1 uniquement (rappel, aucun changement au Relay).

## 8. Décisions

### Prises par le prompt (§3), rappel

React + TypeScript strict + Vite dans `frontend/` ; fenêtre pywebview ≥ 6 (repli navigateur) ; FastAPI
local sur 127.0.0.1 (REST + un WebSocket), jeton par lancement, vérification de `Origin` et `Host` ;
`ChatService` sans dépendance d'interface ; `frontend/dist/` versionné ; module `shell` ; visionneuses
Office natives dans le volet ; branche `feat/interface-web`.

### Prises le 2026-10-12 (réponses de Nicolas aux questions de la phase 0)

Numérotées comme les questions de la section 9.

- **D1. File d'attente** : les messages du desktop et du mobile passent par une file commune et sont
  traités un à la fois ; l'interface montre ceux qui attendent ; Stop arrête la requête en cours.
- **D2. Sessions** : Ctrl+N ouvre une conversation vide, nommée d'après le début de son premier message
  (aucun appel au modèle) ; la session courante est sauvegardée après chaque tour et retenue d'un
  lancement à l'autre.
- **D3. Rechargement d'une session** : l'historique du LLM est toujours reconstruit depuis la
  conversation affichée (Tk ne le faisait que s'il y avait des variantes d'édition).
- **D4.** Plus de troncature de l'historique à 100 messages.
- **D5. « Régénérer »** au survol d'une réponse : nouvelle variante ‹ k/n › du même message.
- **D6. Échap** arrête la génération quand aucun dialogue ni menu n'est ouvert.
- **D7. Sessions enrichies** par des clés optionnelles dans chaque message (réflexion, appels d'outils,
  documents, image générée, source mobile) ; l'interface Tk les ignore sans erreur.
- **D8. Artefacts** : comme dans Tk, un artefact HTML peut charger des ressources externes (iframe
  `sandbox` sans `allow-same-origin`, sans CSP qui les bloque) ; les aperçus natifs des documents Office
  sont conservés. Lecture de la réponse confirmée par Nicolas le 2026-10-12.
- **D9. KaTeX** : les formules LaTeX sont rendues dans le chat et dans les sorties d'agents ; KaTeX et
  ses polices sont livrés avec l'appli et chargés seulement quand une réponse contient une formule.
- **D10. Tokens/s** calculés à partir des statistiques de fin de flux d'Ollama (`eval_count`,
  `eval_duration`), sans appel supplémentaire au modèle.
- **D11. Export d'un workflow** (bouton « 📤 Export » du canvas) : un fichier Markdown avec la tâche, la
  liste des agents (nom, type, statut), puis la réponse de chacun à la dernière exécution. « Save »
  continue d'enregistrer la structure en JSON ; `docs/AGENTS_GUI.md` sera aligné en phase 5.
- **D12. Progression du placement** : paramètre facultatif ajouté à `ensure_best_placement`
  (rétrocompatible), pour que l'écran de chargement nomme les sous-étapes du calibrage.
- **D13. Push** : sur le PC à RTX 3060, avec l'identifiant déjà enregistré, sans forcer le compte.
  Toujours ni push ni fusion sur `main` sans accord.

### Prises le 2026-10-12 (réponses de Nicolas aux questions de la phase 1)

- **D14. Écarts à Tk décidés en phase 1, validés.**
  - Ctrl+L ouvre une nouvelle conversation, et l'ancienne reste enregistrée.
  - La génération de fichier répond aussi au mobile.
  - Une session rechargée garde ses horodatages.
- **D15. Tokens/s (complète D10) : option (a).** `core/chat_orchestrator.py` reçoit un relevé en lecture
  seule : `eval_count` et `eval_duration` du dernier flux, gardés dans un attribut que le `ChatService`
  lit pour ses tokens/s.
  - Requêtes à Ollama inchangées, aucun appel en plus.
  - C'est la seule modification autorisée de l'orchestrateur.
  - L'estimation actuelle (un fragment streamé = un jeton) sert de repli si le relevé manque.

### Constats techniques qui orientent la phase 1

- **Brancher le mobile sans toucher au Relay** : `RelayBridge` offre déjà `on_gui_message(callback)` ;
  l'interruption mobile se lit avec `consume_interrupt_request()` (sondage léger). Le `ChatService`
  s'abonne au bridge et soumet ses réponses avec `submit_ai_chunk / image / document / response`, comme
  aujourd'hui. Aucun changement de protocole ni de fichier du Relay n'est nécessaire.
- **Un seul `AgentRelayService`** partagé par la page Agents web, le Relay et le scheduler (le scheduler
  sait déjà le recevoir, `set_executor`) : une seule exécution à la fois partout. Le Relay le crée
  aujourd'hui lui-même (`agent_service`, paresseux) : il faudra pouvoir lui passer l'instance partagée
  (petit ajout, protocole inchangé).
- **Format des sessions** : `save_workspace` ne garde que des clés de premier niveau listées en dur
  (`conversation_history`, `attached_documents`, `attached_folders`, `active_agents`, `settings`,
  `turn_branches`, `metadata`). Un enrichissement rétrocompatible passe par des clés optionnelles *dans*
  chaque message (`thinking`, `tool_calls`, `documents`, `source`…), ou par l'ajout de la clé à cette
  liste.
- **Format des workflows** : celui de `WorkflowCanvas.to_dict` (`nodes` = dictionnaire à clés entières
  en texte, `connections` à identifiants entiers, `zoom`, `pan_x`, `pan_y`) ; la PWA utilise un autre
  format (liste de nœuds) dans son stockage local, sans incidence.

### Constats de la phase 1 : reprise du prompt par Ollama avec `qwen3.5`

- `my_ai` (qwen3.5) mêle couches d'attention et couches récurrentes. Ollama 0.40 (runner llama-server)
  ne peut donc pas revenir à n'importe quelle position du cache. Il garde des points de reprise
  (« context checkpoints », 50 Mo chacun), posés pendant la lecture de chaque prompt, dont un 4 jetons
  avant la fin.
- Le prompt d'un tour se termine par le bloc de réflexion vide du rendu `qwen3.5` (4 jetons). Dans
  l'historique, la réponse est réécrite sans ce bloc. Au tour suivant, Ollama reprend donc au point posé
  4 jetons avant la fin du prompt précédent, puis relit la réponse précédente et le nouveau message. Le
  message système, les outils et les tours plus anciens ne sont pas relus.
- Un prompt qui n'est que le début du précédent (requête intercalée plus courte, édition d'un tour
  ancien) n'a aucun point de reprise utilisable : tout est relu (« forcing full prompt re-processing »).
  Le cache de prompts du serveur (8 Go en mémoire vive) peut ensuite resservir un prompt déjà vu : le
  préchauffage « hi », ou le premier tour d'une conversation qui commence pareil.
- `prompt_eval_count` compte tout le prompt. Le nombre de jetons réellement relus figure dans le journal
  du serveur (« prompt eval time = … ms / N tokens »), à condition de relancer `ollama serve` avec une
  sortie capturée : le lanceur l'envoie dans DEVNULL.

### Choix techniques de la phase 2 (dans le cadre fixé, pour mémoire)

- **Rendu Markdown** : react-markdown + remark-gfm, réponse découpée en blocs (jetons de bloc de
  marked) mémoïsés, Markdown incomplet du dernier bloc refermé par remend. Départagé par une mesure
  (journal, phase 2) : Streamdown, même sans HTML brut, est 4 fois plus lent et produit des tâches
  longues. Le HTML brut s'affiche comme du texte ; les URL non web sont neutralisées.
- **Coloration du code** : Shiki (moteur JavaScript, thème à variables CSS de `tokens.css`, palette
  Dark+ de Tk), dans un **Web Worker** : la première coloration d'un langage compile sa grammaire
  (54 ms pour Python, 112 ms pour JavaScript, plus d'une seconde pour C++), jamais sur le fil de la
  fenêtre. Pendant le streaming, au plus une coloration toutes les 400 ms ; lignes en cours en brut.
- **Sauts de ligne simples** gardés (remark-breaks), comme Tk et la PWA : bloc « Sources », listes
  écrites sans ligne vide.
- **Position des appels d'outils** : chaque appel garde `at`, la longueur du texte au moment de
  l'appel (événement `tool.call` et `tool_calls` des sessions, clé optionnelle, D7). Les outils
  s'affichent à leur place, en direct comme à la réouverture ; sans `at` (sessions anciennes), en tête.
- **Session rouverte sans changement non réenregistrée** (empreinte de l'historique et des
  variantes) : elle garde sa date et sa place dans la liste des conversations. Tk la réenregistrait
  avant d'en ouvrir une autre ; avec la sauvegarde après chaque tour (D2), cela ne servait plus qu'à
  la faire remonter en tête de liste, sous le curseur.
- **Fenêtre** : processus en DPI par écran v2 avant pywebview ; navigation hors de l'appli annulée et
  nouvelles fenêtres refusées (deux gestionnaires de pywebview remplacés : NavigationStarting,
  NewWindowRequested) ; seuls http, https et mailto s'ouvrent dans le navigateur du système ;
  téléchargements et `file://` interdits ; mode privé de WebView2 ; barre de titre sombre, aux
  couleurs de `tokens.css` sous Windows 11 (la page les envoie à la fenêtre) ; taille, position et
  état agrandi retenus (`window` dans `data/.desktop_state.json`) ; premier lancement agrandi, comme Tk.
- **Raccourcis du navigateur** neutralisés deux fois : réglage de WebView2 (hors mode debug) et
  `preventDefault` dans la page.
- **`--dev`** : serveur local sur le port 5180, Vite sur 5173 (lancé par le lanceur, ou réutilisé
  s'il tourne déjà), arrêté à la fermeture.
- **Variables de développement** : `MY_AI_WEBVIEW_CDP_PORT` ouvre le port de débogage de WebView2,
  seulement sur demande, pour piloter la vraie fenêtre depuis Playwright ; `MY_AI_WEBVIEW_DEBUG=1`
  donne les outils de développement sans `--dev`. Build de profilage : `VITE_REACT_PROFILE=1`
  (React Profiler), absent des builds normaux.
- **Infobulles** sans contenu cliquable (`disableHoverableContent`) : elles se ferment dès que la
  souris quitte leur bouton, même vers l'extérieur de la fenêtre (bogue signalé par Nicolas).
- **Polices** Inter et JetBrains Mono variables (toutes les graisses, sous-ensembles chargés à la
  demande) ; pas de ligatures dans le code (« => » reste « => », comme Consolas dans Tk) ; KaTeX
  livré en WOFF2 seulement.

## 9. Questions de la phase 0

Réponses de Nicolas le 2026-10-12 : oui aux questions 1 à 8, 10 et 12, consigne pour la 13 ;
questions 9 et 11 précisées puis tranchées le même jour (décisions D1 à D13, section 8).

1. **Chevauchement desktop / mobile** : reproduire la politique Tk (le dernier message interrompt le
   précédent) ou une **file d'attente** ? Je recommande la file : Ollama traite de toute façon une requête
   à la fois, aucune réponse n'est perdue, et l'interface affiche « en attente ». Stop arrête la requête
   en cours.
2. **Sessions** : je propose, sans appel au modèle, (a) Ctrl+N = nouvelle conversation vide, nommée
   d'après le début du premier message ; (b) sauvegarde automatique de la session courante après chaque
   tour ; (c) session courante retenue d'un lancement à l'autre. Ou garder exactement Tk ?
3. **Rechargement d'une session** : reconstruire toujours l'historique du LLM (comme Tk le fait déjà
   quand il y a des variantes) ou garder l'écart actuel ? Je recommande de toujours reconstruire.
4. **Historique tronqué à 100 messages** : je propose de ne plus tronquer (liste virtualisée).
5. **« Régénérer » au survol (§8)** : l'ajouter comme nouvelle variante ‹ k/n › du même texte ?
6. **Échap** : l'ajouter comme Stop quand aucun dialogue ni menu n'est ouvert ?
7. **Enrichir les sessions** (réflexion, appels d'outils, documents, image générée, source mobile) avec
   des clés optionnelles par message ? Je recommande oui.
8. **Artefacts** : autoriser comme Tk les ressources externes dans l'`<iframe sandbox>`, ou les bloquer
   par une CSP (hors ligne strict, mais un artefact qui charge un CDN s'afficherait mal) ?
9. **KaTeX** : le rendre dans le chat et les sorties d'agents (l'IA produit du LaTeX, cf. section 7) ?
10. **Tokens/s** : alimenter vraiment la métrique (statistiques renvoyées par Ollama en fin de flux,
    sans appel supplémentaire) ?
11. **Export d'un workflow** : nœuds et statut (code Tk) ou résultats de la dernière exécution (doc) ?
12. **Écran de chargement pendant le placement** : pour nommer les sous-étapes du calibrage, j'ajouterais
    un paramètre facultatif de progression à `ensure_best_placement` (`utils/ollama_placement.py`),
    rétrocompatible. D'accord ?
13. **Push de la branche** sur ce PC : voir le journal (section 12).

### Précisées puis tranchées le 2026-10-12

- **Question 9 — KaTeX** (phase 2), expliquée le 2026-10-12. KaTeX affiche comme dans un manuel les
  formules que l'IA écrit en LaTeX (fractions, racines, exposants, lettres grecques), au lieu du texte
  brut avec ses dollars et ses barres obliques que le chat Tk affiche aujourd'hui. Environ 300 Ko de code
  et de polices livrés avec l'appli (rien en ligne), chargés seulement quand une réponse contient une
  formule. Recommandation : oui. **Réponse : oui (D9).**
- **Question 11 — Export d'un workflow** (phase 4), reformulée le 2026-10-12. Le bouton « 📤 Export » du
  canvas écrit un fichier Markdown : (a) la liste des agents du workflow, comme le code Tk ; (b) le texte
  produit par chaque agent à la dernière exécution, comme le dit `docs/AGENTS_GUI.md` ; (c) les deux : la
  tâche, les agents, puis la réponse de chacun. Recommandation : (c), puisque « Save » enregistre déjà la
  structure du workflow en JSON. **Réponse : (c) (D11).**

### Questions de la phase 1 (posées le 2026-10-12)

Réponses de Nicolas le 2026-10-12 : oui à la 14 (D14), option (a) pour la 15 (D15). Voir la section 8.

14. **Écarts à Tk décidés en route** (journal, section 12) : Ctrl+L ouvre une nouvelle conversation et
    l'ancienne reste enregistrée ; la génération de fichier répond aussi au mobile ; une session
    rechargée garde ses horodatages. D'accord ?
15. **Tokens/s (D10)** : les statistiques de fin de flux d'Ollama sont lues uniquement dans
    `core/chat_orchestrator.py`, que le prompt interdit de modifier. Trois options :
    - (a) un relevé en lecture seule dans l'orchestrateur : `eval_count` et `eval_duration` du dernier
      flux gardés dans un attribut, requêtes inchangées, aucun appel en plus ;
    - (b) envelopper `_resilient_post` depuis le `ChatService`, comme le fait `tools/measure_energy.py`.
      Le fichier reste intact, mais c'est plus fragile ;
    - (c) garder l'estimation actuelle (un fragment streamé = un jeton). Comparée à Ollama, elle est 1 %
      trop basse pour une réponse longue, 10 à 17 % trop basse pour une réponse de 120 jetons, et absente
      sous 0,2 s.

    Recommandation : (a).

### Questions de la phase 2 (posées le 2026-10-13)

16. **Libellé du bloc de réflexion** : « Raisonnement » comme dans Tk, suivi de la durée
    (« Raisonnement · 12 s »), ou « Réflexion » comme dans le prompt (§7, §8) ? J'ai gardé le
    libellé de Tk.
17. **Tokens/s des réponses sans outils** : elles passent par `LocalLLM.generate_stream`, que D15 ne
    couvre pas ; l'estimation de repli y est 10 à 17 % trop basse pour une réponse courte. Ajouter le
    même relevé en lecture seule (`eval_count`, `eval_duration`) à `models/local_llm.py` ?
18. **Fichiers étrangers dans le dépôt** : le 2026-10-13 à 08:54:23, pendant la session, sont apparus
    à la racine `package.json`, `package-lock.json`, `AGENTS.md`, `THIRD_PARTY_NOTICES.md`,
    `.env.example`, `examples/` (six dossiers et un README), `patterns/` et `templates/`, ainsi qu'un
    bloc « HyperFrames / motion design » à la fin de `.gitignore`. Ils viennent d'un espace de travail
    « motion-design-claude-code » (HyperFrames). Je ne les ai ni créés, ni modifiés, ni commités (le
    commit de `.gitignore` ne contient que le bloc `frontend/`). Les retirer, les garder ou les déplacer ?
19. **Outils de vérification** (`temp/migration_tools/`, hors dépôt) : les verser dans le dépôt
    (par exemple `frontend/scripts/` et `tools/`) pour les retrouver sur le PC Arc ?
20. **Boutons de la phase 3** (Relay, lecture automatique, Réglages, Mémoire, Prompts, Export, pièces
    jointes, micro, recherche) : affichés désactivés, avec une infobulle « arrive à la phase 3 », pour
    juger la structure. Les garder ainsi, ou les masquer d'ici là ?

## 10. Risques repérés

- **Reprise du prompt par Ollama** : `_rewind_engine_history` (édition, rechargement) réécrit tout
  l'historique du LLM, donc la conversation est relue au tour suivant. C'est déjà le cas dans Tk ; le
  `ChatService` doit faire exactement les mêmes appels, et seulement ceux-là. À mesurer sur le vrai Ollama.
- **Requêtes intercalées** : agents, création d'agent personnalisé (`LocalLLM.generate`), description
  d'image et chat VS Code utilisent `my_ai` avec d'autres prompts ; le tour de chat suivant relit tout.
  Inchangé par la migration, mais une file d'attente commune ne doit pas l'aggraver.
- **Le placement et l'ordre de démarrage** : rien ne doit appeler Ollama avant la fin du placement, y
  compris le panneau Réglages (`ollama_reachable`, `/api/tags`), la vérification `my_ai` du moteur, le
  préchargement, les agents, le Relay, le scheduler (rattrapage) et la recherche globale.
- **Visionneuses Office et DPI** : passer le processus en « DPI par écran v2 » avant pywebview peut
  changer le rendu de WebView2 ; l'hébergement en fenêtre enfant (`WS_CHILD`) au-dessus de WebView2 est à
  prouver ; tests à 125 et 150 % impossibles ici.
- **pythonnet sur Python 3.14** (PC Arc) : version ≥ 3.1 obligatoire ; 3.2.x très récente.
- **Mémoire et sessions** : le panneau Mémoire modifie les messages d'origine des sessions
  (`at_source=True`). Avec l'état de la conversation côté backend, une sauvegarde de la session courante
  pourrait écraser ces modifications : à synchroniser.
- **Glisser-déposer dans WebView2** : le vrai chemin des fichiers (`pywebviewFullPath`) est à vérifier ;
  les dossiers ne sont pas gérés par Tk aujourd'hui.
- **Raccourcis du navigateur dans WebView2** (Ctrl+R, F5, Ctrl+N, Ctrl+S, Ctrl+P, Ctrl+F…) à neutraliser.
- **KaTeX (D9)** : un montant en dollars (« entre 5 $ et 10 $ ») peut être pris pour une formule. À
  régler et tester en phase 2 (par exemple, pas d'espace juste après le `$` ouvrant ni juste avant le `$`
  fermant, comme pandoc).
- **Outillage front** : TypeScript 7 incompatible avec typescript-eslint ; Vite 8 / Vitest 5 exigent
  Node ≥ 22.12 (à vérifier sur le PC Arc) ; Streamdown embarque `rehype-raw` (à désactiver).
- **Autre session Claude active sur ce PC** (projet ML-et-DL, `pip install` dans le même Python) :
  éviter d'installer des paquets en même temps.

- **Échelles 125 % et 150 %, deux écrans** (phase 2) : non vérifiables ici. En DPI par écran v2, la
  fenêtre WinForms (.NET Framework, sans app.config) ne se redimensionne pas d'elle-même en
  changeant d'écran ; WebView2, lui, suit l'échelle. À vérifier sur le PC de travail (et en phase 3
  avec les visionneuses Office).
- **Chargement du moteur à froid** : 3 min au premier lancement du 2026-10-13, 10 s aux suivants
  (imports de torch et du modèle d'embeddings, comme avec Tk). L'écran de chargement l'affiche
  (« Chargement du moteur »).

---

## 11. Carte du pipeline actuel (référence du `ChatService`)

### Lancement (`launch_unified.py`)

1. `sync_requirements()` (avant les imports), puis `prefetch_in_background()`.
2. `_ensure_ollama_parallel()` : `OLLAMA_NUM_PARALLEL=4` persistant, arrêt de tous les Ollama (application
   bureau comprise), attente du port, `ollama serve` avec `server_env(os.environ, saved_env())`.
   Échec : « ⚠️ Ollama n'a pas pu démarrer — lancez l'application Ollama ou « ollama serve » ».
3. `should_run()` → `OnboardingWizard().run()` (bloquant).
4. `sync_custom_model()`.
5. `ensure_best_placement(_restart_ollama)` : compare la signature ; sinon calibre (jusqu'à une minute,
   « 🔍 Recherche du meilleur emplacement pour le modèle '…' (une seule fois, jusqu'à une minute)… »).
6. `ModernAIGUI()` : `AIEngine(Config())` (synchrone), puis `initialize_ai_async` (thread :
   `initialize_llm()`, `is_ollama_active()`), `_init_relay` (si `relay.auto_start`), `_init_scheduler`
   (si `scheduler.enabled`, défaut vrai).

`main.py --mode gui` ne fait ni le redémarrage d'Ollama ni le placement (seulement `sync_custom_model`).

### Message desktop (`send_message` → `quel_handle_message_with_id`)

Avant le fil : refus si une pièce jointe est en lecture ; bulle utilisateur (lignes 📎/🖼️, `attachments`,
`image_path`, `mid`) ; `current_request_id += 1` ; `is_interrupted = False` ;
`engine.command_history.add(query=message)`. Dans le fil, dans cet ordre :

1. `user_text = _expand_slash_command(user_text)` (`prompt_library.expand`).
2. `_sync_visible_documents()` → `engine.set_visible_documents(noms)` puis
   `engine.set_attached_documents(chemins)` (pièces jointes de l'historique affiché).
3. Mots-clés de génération de fichier (« génère moi un fichier », « crée moi un fichier », « génère un
   fichier », « crée un fichier ») → `asyncio` : `ai_engine.process_query(user_text,
   is_interrupted_callback)` ; puis `llm.add_to_history("user", user_text)` et
   `llm.add_to_history("assistant", <message fixe>)`.
4. `ai_engine.is_image_generation_request(user_text)` → `image_generator`, `_auto_setup_image_backend`,
   `extract_image_prompt`, `gen.generate(prompt, on_progress, is_interrupted)`, puis
   `llm.add_to_history` ×2 (`_remember_image_generation`).
5. `detect_intent` : absent d'`AIEngine`, donc repli par mots-clés, sans appel au modèle.
6. `_show_reasoning = not is_conversational(t) and is_ollama_active() and is_complex_query(t) and pas
   d'image en attente` (`is_ollama_active` = GET sur Ollama, 2 s max).
7. `ai_engine.process_query_stream(user_text, on_token, on_tool_call, on_thinking_token (ou None),
   on_thinking_complete (ou None), image_base64, is_interrupted_callback, on_delete_confirm, on_document)`.
   `on_image` et `on_image_progress` ne sont pas passés (l'image est interceptée à l'étape 4).
8. Rien streamé mais une réponse → affichée d'un bloc. Erreur (`ConnectionError`, `TimeoutError`,
   `AttributeError`) → « ❌ Erreur IA : … ».

Les rappels renvoient `False` quand la requête est périmée ou interrompue. `on_token` relaie le texte
cumulé au mobile (`submit_ai_chunk`). `on_document` dédoublonne et relaie (`submit_ai_document`).

### Message mobile

`relay_server` (`chat`) : `RelayMessage(source="relay", image_path, file_paths)` →
`bridge.arm_response(id)` → `bridge.send_to_gui(msg)` → `ack` → tâche détachée
`bridge.wait_for_ai_response(timeout)` → `response`. Côté Tk : sondage toutes les 200 ms
(`consume_interrupt_request` → `interrupt_ai`, `poll_gui_messages`), bulle « 📡 », texte par défaut si vide
(« Décris cette image en détail. » / « Analyse ce fichier et résume-le. »), puis dans un fil
`process_file_background` pour chaque document, `_process_image_file`, et `quel_handle_message_with_id`.
Fin : `submit_ai_response(texte brut)` ; interruption : texte partiel + « ⚠️ *Réponse interrompue.* ».

### Agents (`AgentRelayService`)

Événements : `agents_list_result`, `agent_create_result`, `agent_edit_result`, `agent_delete_result`,
`agent_exec_start` (`mode`), `agent_debate_topic`, `agent_section_start` (`section_id`, `title`,
`color`), `agent_section_chunk` (texte cumulé, 60 ms au plus), `agent_section_end` (`success`),
`agent_node_status` (`idle` / `running` / `done` / `error`), `agent_exec_end` (`success`,
`interrupted`, `status_text`), `agent_exec_error`.

---

## 12. Journal

### Phase 0 — 2026-10-12 (PC à RTX 3060)

- Identité git : l'identité globale est celle de Ynov ; identité locale du dépôt réglée sur
  `gonicolas12` / `nicolasgouy@yahoo.com`. `credential.https://github.com.username` non réglé (voir §10 du
  prompt).
- Branche `feat/interface-web` créée depuis `main` à jour (`543f083`, identique à `origin/main`).
- Environnement, matériel testable et versions relevés (section 1) ; suite de tests de référence lancée
  (section 3) ; données de test créées (section 4).
- Lu : `interfaces/gui/base.py`, `streaming.py` (création et finalisation du streaming, réflexion),
  `file_handling.py`, `message_editing.py`, `sidebar.py`, `layout.py`, `message_bubbles.py` (en partie),
  `command_palette.py`, `slash_commands.py`, `artifacts_panel.py`, `settings_panel.py`, `voice_input.py`,
  `interfaces/onboarding.py`, `interfaces/agents/` (survol), `relay/relay_server.py`, `relay_bridge.py`,
  `agent_relay.py`, `core/ai_engine.py` (`process_query_stream` et méthodes appelées par l'interface),
  `core/chat_orchestrator.py` (survol), `core/session_manager.py`, `core/scheduler.py` (survol),
  `core/api_server.py` (survol), `launch_unified.py`, `main.py`, `utils/ollama_placement.py`,
  `utils/path_links.py`, section 8 de `docs/OPTIMIZATION.md`, la documentation listée en phase 0, les trois
  captures de `docs/images/` et la PWA (`app.js`, `agents.js`, survol).
- Aucun code applicatif modifié en phase 0.
- Push de la branche : `git -c credential.https://github.com.username=gonicolas12 push -u origin
  feat/interface-web` échoue (« could not read Password for 'https://gonicolas12@github.com': terminal
  prompts disabled »), comme prévu sur ce PC. Poussée ensuite avec l'identifiant déjà enregistré, sur
  consigne de Nicolas (D13).
- Réponses de Nicolas aux questions : décisions D1 à D13 (section 8) ; questions 9 et 11 précisées puis
  tranchées (KaTeX : oui ; export d'un workflow : option c).

### Phase 1 — à partir du 2026-10-12 (PC à RTX 3060)

- `interfaces/desktop/events.py` : protocole (modèles Pydantic des événements et des messages de la
  fenêtre) et `EventBus` (numérotation, ordre, reprise après reconnexion).
- `core/chat_service.py` : pipeline de `quel_handle_message_with_id` (mêmes appels au moteur, même
  ordre, vérifié par test), file d'attente commune (D1), pièces jointes, variantes d'édition et
  régénération (D5), sessions créées au premier message, sauvegardées après chaque tour et rouvertes
  au lancement (D2), historique du modèle reconstruit au chargement (D3), pas de troncature (D4),
  clés optionnelles par message (D7), chat mobile par le `RelayBridge`. Stop du mobile : sa réponse
  en cours, sinon ses messages en attente, sinon la réponse en cours (comme Tk).
- Moteur : `process_query_stream` accepte `on_tool_result` (facultatif, observation seule) ;
  `SessionManager.clear_current_workspace`.
- `utils/ollama_placement.py` : `ensure_best_placement(on_progress=…)` (D12).
- `relay/relay_server.py` : `agent_service` partagé (constructeur) et `local_url`.
- `interfaces/desktop/server.py` et `lifecycle.py` ; `launch_unified.py --headless [--port N]`.
- Écarts à Tk décidés en route (à valider) : Ctrl+L (« Effacer la conversation ») vide la mémoire du
  moteur et ouvre une nouvelle conversation, la session précédente reste enregistrée (avec la
  sauvegarde automatique, vider la session en place l'effacerait) ; la génération de fichier répond
  aussi au mobile (Tk le laissait attendre jusqu'au délai maximal) ; une session rechargée garde ses
  horodatages (Tk les remplaçait par l'heure du chargement).
- Message de fin de la génération de fichier : 8 messages fixes tirés au hasard, comme Tk
  (`base.py:2399`) ; les documents (Word, PDF…) gardent leur message rédigé par le modèle. Le faire
  rédiger par le modèle serait un appel de plus : seulement si Nicolas le demande.
- `lifecycle.py` : les messages d'arrêt sont écrits tout de suite (`flush=True`). Le lanceur sort par
  `os._exit`, qui perdait « 🛑 Fermeture… » dans un journal redirigé.
- Vérifications sur le vrai Ollama, celui du lanceur (100 % GPU, contexte en 8 bits), avec des scripts
  hors dépôt :
  - `--headless` : les étapes du chargement s'enchaînent jusqu'à « prêt », avec le placement. Client
    WebSocket : premier jeton en 6,9 s (modèle froid), 73 jetons/s ; Stop garde la réponse partielle,
    marquée interrompue ; la session prend le nom du premier message.
  - Chat mobile sans fenêtre : Relay démarré par l'API, client chiffré comme la PWA. Premier fragment en
    0,8 s. Stop mobile : le texte partiel arrive suivi de « ⚠️ *Réponse interrompue.* ». Côté PC, le
    message est enregistré avec `source=mobile` et marqué interrompu.
  - Arrêt par `/api/shutdown` : Relay, puis scheduler (verrou libéré), puis serveur ; code de sortie 0.
- **Reprise du prompt, Tk contre web** (critère de fin de la phase 1).
  - Méthode : six essais alternés Tk / web, avec un moteur neuf à chaque essai. Tk est piloté par sa
    vraie fenêtre (`send_message`), le web par le `ChatService`. Les jetons relus sont lus dans le
    journal du serveur (section 8).
  - Conversation : « Écris un texte d'environ trois cents mots sur l'histoire du café, en trois
    paragraphes. », puis « Propose un titre court pour ce texte. ».

  | Essai | Jetons repris au 2e tour | Jetons relus | Durée de relecture | Premier jeton |
  |---|---|---|---|---|
  | Tk 1 | 4 825 | 648 | 560 ms | 0,60 s |
  | web 1 | 4 825 | 494 | 272 ms | 0,32 s |
  | Tk 2 | 4 825 | 603 | 464 ms | 0,50 s |
  | web 2 | 4 825 | 628 | 331 ms | 0,37 s |
  | Tk 3 | 4 825 | 454 | 412 ms | 0,46 s |
  | web 3 | 4 825 | 916 | 461 ms | 0,51 s |

  - Premier tour : les deux interfaces envoient les mêmes messages, les mêmes options et les mêmes
    15 outils (empreintes identiques). Le deuxième tour prolonge exactement le premier.
  - Deuxième tour : Ollama reprend les 4 825 jetons du premier prompt (message système, outils, première
    question). Il relit la réponse précédente et la nouvelle question (454 à 916 jetons, selon la
    longueur de la réponse). Aucune relecture complète.
  - Le web n'est pas plus lent : il relit même un peu plus vite par jeton (0,5 ms contre 0,8 ms). Cause
    non vérifiée : peut-être la fenêtre Tk, qui occupe le processeur.
  - Tokens/s estimés par le `ChatService`, comparés aux statistiques d'Ollama : 71,4 à 72,4 contre 72,2
    à 73,1 pour des réponses de 470 à 900 jetons ; 61,7 à 67,4 contre 73,9 à 74,6 pour des réponses de
    120 jetons ; aucune estimation pour une réponse de 11 jetons. Voir la question 15.
  - Contrôle sans l'appli, par des requêtes `/api/chat` directes : un prompt qui prolonge exactement le
    précédent coûte 83 ms, contre 1 230 ms à froid. C'est le comportement du modèle, pas de l'interface.
- Suite complète : **987 réussis** (930 + 57 nouveaux), aucun échec, 33 avertissements. Les 2 nouveaux
  avertissements viennent d'uvicorn 0.34, qui importe l'API `websockets.legacy`, dépréciée.
- Nettoyage : j'ai retiré la session et les 6 entrées d'historique créées par les clients de test, ainsi
  que `data/.desktop_state.json`. Les données de test de la phase 0 sont intactes (4 sessions,
  12 entrées).
- Ollama : le lanceur l'a relancé pendant les vérifications (l'application bureau d'Ollama a alors été
  arrêtée). Je l'ai relancé ensuite avec le même environnement, journal capturé le temps du diagnostic.
  Il tourne maintenant comme le lanceur le laisse.

### Phase 2 — 2026-10-12 et 2026-10-13 (PC à RTX 3060)

- `main` n'avait pas bougé (rien à fusionner). pywebview et Playwright installés (section 1).
- **Front** (`frontend/`) : Vite 8, React 19.3, TypeScript 6 strict, ESLint, Prettier, Vitest ;
  `tokens.css` (couleurs du §8, palette Dark+ du code, typographie, formes, mouvement) branché sur
  Tailwind 4, palettes par défaut retirées ; polices auto-hébergées.
  - Protocole : `lib/events.ts` (miroir de `events.py`), client REST, WebSocket avec reprise
    (`since`, `hello`), relecture de l'état et règle d'ordre par `seq`, actions par WebSocket avec
    repli REST sans double envoi ; module `shell` (liens externes, couleurs de la barre de titre).
  - État : réducteur du chat pur et testé, appliqué par lots à chaque image (minuteur de secours
    quand la fenêtre est réduite).
  - Écrans : chargement (étapes du lanceur, sous-étapes du calibrage, erreur d'Ollama), accueil,
    onglets, barre latérale (conversations : ouvrir, supprimer, nouvelle ; reste en phase 3),
    page Agents provisoire.
  - Fil virtualisé (react-virtuoso), colonne de 720 px, collé en bas pendant une réponse (sans le
    relancer à chaque changement de hauteur, il décroche jusqu'à 104 px), bouton « ↓ ».
  - Réponse : Markdown par blocs, code coloré dans un worker avec Copier, formules (KaTeX à la
    demande, règle des dollars), bloc Raisonnement, appels d'outils à leur place (« · 3 sources »),
    activité (« L'IA réfléchit… », « Analyse du résultat et synthèse en cours… »), interrompue,
    erreur, durée et tokens/s (D15).
  - Saisie : carte, Entrée et Maj+Entrée, bouton rond devenant Stop, file d'attente visible et
    annulable (D1), Échap (D6), confirmation de suppression (dialogue), notifications.
- **Backend** :
  - `tool.call` et `tool_calls` portent `at` ;
  - `core/chat_orchestrator.py` : relevé en lecture seule `last_stream_stats` (D15, 15 lignes),
    lu par le `ChatService` (repli sur l'estimation) ;
  - une session rouverte sans changement n'est plus réenregistrée ;
  - `/api/status` donne `chat` et `seq`, `/api/ui` garde l'état de la barre latérale ;
  - `window.py` (fenêtre), `shell_api.py`, `devserver.py` (`--dev`), `run_desktop` dans
    `lifecycle.py` ;
  - `launch_unified.py --ui web|tk` (web par défaut) et `--dev` ; `requirements.txt` : pywebview,
    pythonnet ≥ 3.1 sous Windows ; icône `interfaces/desktop/assets/my_ai.ico`.
- **Tests** : `python -m pytest tests/` : **1029 réussis** (987 + 42), aucun échec, 33 avertissements,
  86 s. Front : 45 tests Vitest, TypeScript, ESLint et Prettier propres.
- **Captures** (Chromium, serveur de démonstration) : chargement, accueil, barre latérale, sessions,
  conversation de 200 messages, streaming, réflexion, outils, file d'attente, Échap, confirmation,
  erreur, Agents. Comparées à `docs/images/` et au §8 : même structure que Tk (☰, onglets centrés,
  logo, « My_AI », carte de saisie), finition plus sobre ; le bouton « Envoyer ↗ » devient le bouton
  rond du §8.
- **Choix du rendu Markdown** (même réponse de 5 000 jetons, durée de chaque mise à jour, rendu et mise
  en page compris, Chromium) :

  | Rendu | Jetons par mise à jour | Moyenne | 95ᵉ centile | Pire | Tâches longues |
  |---|---|---|---|---|---|
  | Blocs mémoïsés (retenu) | 2 | 4,0 ms | 9,0 ms | 33 ms | 0 |
  | Streamdown sans HTML brut | 2 | 18,6 ms | 61,9 ms | 226 ms | 17,8 s |
  | react-markdown d'un bloc | 2 | 6,3 ms | 11,3 ms | 110 ms | 0,55 s |
  | Blocs mémoïsés (retenu) | 20 | 1,6 ms | 3,0 ms | 23 ms | 0 |
  | Streamdown sans HTML brut | 20 | 38,6 ms | 164 ms | 338 ms | 8,1 s |
  | react-markdown d'un bloc | 20 | 16,4 ms | 94 ms | 204 ms | 2,8 s |

- **Mesures de la phase 2** (build de profilage, React Profiler, Chromium sans GPU, serveur de
  démonstration) :
  - défilement des 200 messages à la molette (~2 400 px/s) : images à 16,7 ms (médiane et 95ᵉ
    centile), 2 à 7 images sur 560 au-delà de 33 ms ; défilement très rapide (~15 000 px/s) : 11 à
    22 images sur ~390 au-delà de 33 ms (Shiki dans le worker : 2 fois moins de tâches longues que
    dans la page, mesuré en alternance) ;
  - réponse de 5 000 jetons à 80 jetons/s avec saisie (une touche toutes les 120 ms) et défilement :
    rendus React à 0,5 ms en médiane et 5,5 ms au 95ᵉ centile, saisie au pire à 72–80 ms, 4 à 5 %
    d'images au-delà de 33 ms (une seule tâche longue de 62 ms dans une trace de 8 s) ;
  - en charge (≈ 280 jetons/s) : rendus à 0,3 ms en médiane, 4,2–4,6 ms au 95ᵉ centile, 1,7 %
    d'images au-delà de 33 ms ;
  - calcul Python lourd (GIL tenu 12 s) pendant une réponse : affichage intact (95ᵉ centile à
    16,8 ms) ; seuls les jetons arrivent plus lentement (53 au lieu de 70 par seconde, écart maximal
    174 ms), le fil qui les lit partageant le GIL.
- **Vraie fenêtre WebView2** (Edge 154), vrai Ollama (celui du lanceur), pilotée par CDP :
  - lancement complet en 18 s (moteur 10 s), écran de chargement puis « prêt » ; premier
    lancement agrandi ; barre de titre sombre aux couleurs de l'appli, avec l'icône du robot ;
  - vraie question (code, tableau, recherche web) : réflexion en direct, « Recherche sur internet …
    · 8 sources », synthèse, « 28 s · 69 tokens/s » (relevé d'Ollama, D15) ; affichage à 144 images/s
    (écran à 144 Hz), 6,9 ms par image en médiane, 3 images sur 4 158 au-delà de 33 ms ;
  - raccourcis du navigateur au vrai clavier (F5, Ctrl+R, Ctrl+Maj+R, Ctrl+F5, Ctrl+P, Ctrl+F, F3,
    F7, Ctrl+U, Ctrl+G, Ctrl+J, Ctrl+H, Alt+←, Ctrl+T, Ctrl+W, Ctrl+O) : aucun rechargement, aucune
    barre de recherche ni dialogue ; Ctrl+B ouvre et ferme la barre latérale ;
  - fermeture : arrêt propre (Relay, scheduler, serveur), état enregistré ; taille et position
    retenues (déplacée en 120, 80, 1400 × 900, relancée exactement là) ;
  - `--dev` : Vite lancé (0,3 s), page servie par Vite, API et WebSocket relayés, Vite arrêté avec
    l'appli ; `--ui tk` se lance toujours.
- **Bogues trouvés et corrigés en route** : gestionnaires de fenêtre jamais appelés (pywebview ne
  passe la fenêtre qu'à un paramètre nommé `window`) ; infobulle restée affichée quand la souris
  quitte la fenêtre (signalé par Nicolas) ; bloc Raisonnement « déplié » avant tout texte ; un pixel
  de bordure de la barre latérale fermée ; liste des conversations réordonnée à l'ouverture d'une
  session ; doublon « ❌ » dans l'encadré d'erreur ; ligatures dans le code.
- **`.gitattributes`** : la règle du prompt `frontend/** text eol=lf` traitait les polices WOFF2 de
  `dist/` comme du texte, et Git y remplaçait des octets CRLF par LF (fichiers altérés dans le
  commit). Remplacée par `frontend/** text=auto eol=lf`, plus `binary` pour les polices et images ;
  les commits locaux concernés ont été refaits avant tout push, et chaque fichier de `dist/` commité
  est identique au disque.
- **Incident** : en vérifiant l'infobulle au vrai curseur, deux Ctrl+B sont partis vers la fenêtre
  au premier plan de Nicolas (Windows refusait de mettre l'appli devant, il utilisait le PC). Plus de
  touches système ensuite ; vérifications par CDP seulement.
- **Fichiers étrangers** apparus à la racine pendant la session : question 18.
- Données : `data/.desktop_state.json` remis en « agrandie » après les essais ; une session réelle
  créée par la vérification (« Explique en détail, avec un exemple de code… ») est restée dans
  `data/workspaces/`.

---

## 13. Plan de la phase 1 (approuvé le 2026-10-12, réalisé)

`--ui web|tk` est reporté à la phase 2, où le prompt le place. `tests/test_ollama_restart.py` n'a pas
eu besoin de changer.

Fichiers créés : `core/chat_service.py`, `interfaces/desktop/__init__.py`, `interfaces/desktop/server.py`,
`interfaces/desktop/events.py`, `interfaces/desktop/lifecycle.py` (étapes de lancement et cycle de vie),
`tests/test_chat_service.py`, `tests/test_desktop_server.py`.
Fichiers modifiés : `launch_unified.py` (options `--headless` et `--ui`, imports de l'interface dans
`main()`), `tests/test_ollama_restart.py` (stubs), éventuellement `relay/relay_server.py` (recevoir
l'`AgentRelayService` partagé, sans changer le protocole) et `utils/ollama_placement.py` (progression
du calibrage, D12). Aucun fichier Tk modifié ; `core/chat_orchestrator.py` intouché.

Étapes :

1. `ChatService` : état de la conversation (format Tk), pipeline de `quel_handle_message_with_id` dans le
   même ordre et avec les mêmes arguments, file d'attente commune au desktop et au mobile (D1),
   interruption, confirmation de suppression par événement, pièces jointes (`process_file_background`,
   image), branches d'édition (`message_editing.py`) et régénération sans modification (D5), sessions
   (D2 : création au premier message, nom tiré de ce message, sauvegarde après chaque tour, session
   courante retenue ; D3 : historique du LLM reconstruit au rechargement ; D4 : pas de troncature ;
   D7 : clés optionnelles par message), `clear_chat`.
2. Événements (`events.py`) : `type`, `conversation_id`, `message_id`, `seq`, `payload` ; émission
   thread-safe vers la boucle asyncio.
3. Branchement du mobile sur le bridge (`on_gui_message`, sondage de l'interruption, soumission des
   réponses) : chat mobile sans fenêtre.
4. Serveur desktop : FastAPI sur 127.0.0.1, port libre, jeton par lancement, contrôle `Origin` / `Host`,
   REST (conversation, sessions, pièces jointes) et WebSocket, fichiers statiques de `frontend/dist`.
5. Cycle de vie : étapes de lancement dans un fil avec état publié (`engine.status`, sous-étapes du
   calibrage grâce à D12), moteur, Relay, scheduler après le placement, arrêt propre (Relay et tunnels,
   verrou du scheduler).
6. Mode `--headless`.
7. Tests : `ChatService` avec moteur factice (streaming, stop, confirmation, pièces jointes, branches),
   API via `TestClient` (refus sans jeton ou avec une mauvaise origine), non-régression du Relay.
8. Vérification sur le vrai Ollama, en alternant Tk et web : `prompt_eval_duration` du deuxième tour et
   délai avant le premier jeton, sur la même conversation ; chat mobile sans fenêtre ; client WebSocket de
   test (streaming et Stop).

Risques propres à la phase 1 : appels au moteur différents de Tk (reprise du prompt perdue) ; course
entre le fil du moteur et la boucle asyncio ; sessions modifiées par le panneau Mémoire ; arrêt propre
des tunnels du Relay.

---

## 14. Plan de la phase 2 (approuvé le 2026-10-12, réalisé le 2026-10-13)

But (prompt, §9) : le squelette de l'interface et le cœur du Chat, dans la vraie fenêtre.

Fichiers créés :

- `frontend/` : Vite 8, React 19.3, TypeScript 6.0.x en mode strict, ESLint (typescript-eslint),
  Prettier, Vitest 5. Avec `src/styles/tokens.css` (couleurs du §8) et les polices Inter et JetBrains
  Mono livrées avec l'appli (@fontsource). `frontend/dist/` est versionné (décision du prompt).
- `interfaces/desktop/window.py` : la fenêtre pywebview (titre, icône, taille minimale, barre de titre
  sombre, liens externes dans le navigateur du système, outils de développement en mode debug).
- Tests : Vitest pour le protocole, l'état et le rendu Markdown ; pytest pour `window.py` et les
  options du lanceur.

Fichiers modifiés :

- `launch_unified.py` : options `--ui web|tk` et `--dev` ; stubs de `tests/test_ollama_restart.py` si
  ses imports changent.
- `interfaces/desktop/lifecycle.py` et `server.py` : la fenêtre s'ouvre tout de suite sur l'écran de
  chargement, et la fermer arrête l'appli proprement.
- `requirements.txt` (pywebview), `.gitignore` (`frontend/node_modules/`, captures), `.gitattributes`
  (`frontend/** text eol=lf`, `frontend/dist/** -diff linguist-generated`).
- Ni Tk, ni l'orchestrateur, ni le Relay.

Étapes :

1. Outillage du front et jetons de couleur. Le build est vérifié hors ligne : aucune ressource externe.
2. Couche protocole : le jeton est lu dans le fragment de l'URL puis retiré de l'adresse ; REST et
   WebSocket authentifiés ; reprise après reconnexion (`seq`) ; état de l'appli dans Zustand.
3. Écran de chargement branché sur `engine.status` (étapes, sous-étapes du calibrage, Ollama arrêté),
   puis bascule sur « prêt ».
4. Coquille : onglets Chat et Agents (Agents reste vide jusqu'à la phase 4), structure de la sidebar
   (conversations, nouvelle conversation), écran d'accueil.
5. Fil de messages :
   - liste virtualisée (react-virtuoso) ;
   - streaming regroupé par image affichée, pas un rendu par jeton ;
   - Markdown sans HTML brut ; Streamdown (HTML brut désactivé) ou react-markdown + remark-gfm,
     départagés par une mesure ;
   - blocs de code colorés par Shiki, chargé à la demande ;
   - réflexion repliable, appels d'outils, Stop, états « interrompu » et « erreur ».
6. Saisie : Entrée envoie, Maj+Entrée va à la ligne, Échap arrête la réponse (D6), les messages en
   attente sont visibles (D1).
7. KaTeX chargé à la demande (D9). Règle des dollars : pas d'espace juste après le `$` ouvrant ni juste
   avant le `$` fermant. Testée sur des montants (« entre 5 $ et 10 $ »).
8. Fenêtre pywebview et `--ui web|tk` (défaut `web` dès que le Chat de base fonctionne). Raccourcis du
   navigateur neutralisés (Ctrl+R, F5, Ctrl+N, Ctrl+P, Ctrl+F, Ctrl+S…).
9. Mesures avec les DevTools et le React Profiler :
   - défilement sur la session de 200 messages ;
   - réponse de 5 000 jetons en streaming, sans bloquer la saisie ni le défilement ;
   - fenêtre réactive pendant une indexation lourde.

   Captures Playwright (Chromium headless) des états clés, comparées à `docs/images/` et au §8.

Risques :

- Streaming : un Markdown re-rendu à chaque jeton saccade. Parade : regrouper par image et figer les
  blocs terminés.
- Sécurité :
  - aucun HTML brut, CSP stricte (`script-src 'self'`) ;
  - Shiki avec son moteur JavaScript, sans WebAssembly, sinon la CSP doit l'autoriser ;
  - en mode `--dev`, l'origine de Vite et le WebSocket du rechargement à chaud.
- Installation :
  - pywebview 6.2.1 dans le Python 3.11 global installerait pythonnet 3.2.1 et ferait passer cffi de
    1.16.0 à 2.1.1. cryptography 45.0.5 en dépend : je le vérifierai après l'installation ;
  - Playwright télécharge Chromium (environ 150 Mo, hors du dépôt).
- WebView2 : raccourcis du navigateur, barre de titre sombre (API Windows), outils de développement.
- `frontend/dist/` versionné : le build est à refaire avant chaque commit qui touche le front.

---

## 15. Plan de la phase 3 (proposé, en attente du feu vert)

But (prompt, §9) : tous les éléments des sections « Chat », « Sidebar » et « Fenêtres et
panneaux » du §7, l'assistant de premier lancement et les visionneuses Office natives (§5).
La phase est grosse : elle peut se découper en 3a (Chat et barre latérale) et 3b (panneaux,
onboarding, visionneuses), avec un arrêt entre les deux.

Fichiers créés ou complétés :

- Front : menu « + », glisser-déposer (`pywebviewFullPath`), collage d'image, puces de pièces
  jointes ; autocomplétion des slash commands ; modifier et régénérer, note de 1 à 5 étoiles,
  lecture vocale, micro ; citations `[n]` et chemins de fichiers cliquables ; image générée (grand
  format au clic), cartes de fichiers et de documents ; volet Artefacts (iframe `sandbox` sans
  `allow-same-origin`, onglets Aperçu et Code, largeur réglable et retenue) ; volet d'aperçu
  (PDF dans la page, visionneuses Office, aperçu HTML de repli) ; recherche globale, dossiers projet,
  historique, export ; panneaux Réglages, Mémoire, Prompts, Relay (QR code), Aide ; palette Ctrl+K
  (cmdk) et raccourcis restants ; assistant de premier lancement ; toast de fin de tâche planifiée.
- Backend : routes REST et événements pour ces fonctions, en réutilisant le moteur (`MemoryStore`,
  `PromptLibrary`, `conversation_search`, `folder_indexer`, `command_history`,
  `conversation_exporter`, `rlhf_manager`, `scheduler`, fonctions de `interfaces/onboarding.py`) ;
  fichiers servis seulement depuis des dossiers autorisés, ouverture selon les règles de
  `utils/path_links.py` ; lecture vocale et Whisper côté Python (worker toujours isolé dans son
  processus) ; `shell_api.py` : dialogues de fichiers, ouvrir, montrer dans l'Explorateur, placer la
  visionneuse Office ; `_preview_handler.py` et `_dpi_host.py` déplacés dans `interfaces/desktop/`,
  avec `tests/test_native_preview.py`.
- Tests : pytest pour chaque route et service ; Vitest pour les composants ; captures Playwright.

Étapes : (1) pièces jointes et dialogues ; (2) liens, cartes et ouverture des fichiers ; (3) édition,
régénération, notes, voix ; (4) Artefacts et aperçus (PDF, Office, HTML) ; (5) barre latérale ;
(6) panneaux, palette et raccourcis ; (7) onboarding ; (8) notifications et vérification avec le
téléphone ; (9) captures, mesures et recette.

Risques :

- Visionneuses Office en fenêtre enfant au-dessus de WebView2, avec le DPI par écran : à prouver ;
  masquer la visionneuse sous les menus, dialogues et notifications ; tests à 125 et 150 % impossibles ici.
- `config.yaml` : garder ses commentaires (Réglages), comme le fait Tk aujourd'hui.
- Service de fichiers locaux : chemins hors des dossiers autorisés refusés (traversée de dossiers).
- Le panneau Mémoire modifie les messages d'origine des sessions : synchroniser avec l'état du chat.
- Glisser-déposer : vrai chemin des fichiers à vérifier dans WebView2 ; dossiers refusés comme dans Tk.
