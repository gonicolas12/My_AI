# Migration de l'interface desktop vers le web — fichier de suivi

Ce fichier permet de reprendre la migration d'une session ou d'un PC à l'autre. Pour reprendre :
relire le prompt de mission (`MIGRATION_INTERFACE_WEB_PROMPT*.md`, jamais commité), puis ce
fichier, en commençant par « État actuel ».

Les décisions de la section 8 sont des réponses de Nicolas : elles complètent le prompt et priment
en cas d'écart (par exemple D13 pour le push sur le PC à RTX 3060, D15 et D17 pour l'orchestrateur).
Écart technique à connaître : `.gitattributes` porte `frontend/** text=auto eol=lf`, et non la
règle `text eol=lf` du prompt (§11), qui abîmait les polices de `frontend/dist/` (journal de la
phase 2).

- Branche : `feat/interface-web` (créée le 2026-10-12 depuis `main` à `543f083`).
- `main` garde l'interface Tk jusqu'à la fusion.

## État actuel

- **Phase 0 (préparation) terminée le 2026-10-12.** Décisions D1 à D13 (section 8).
- **Phase 1 (backend sans interface) terminée le 2026-10-12.** Décisions D14 et D15 (section 8).
- **Phase 2 (squelette de l'interface et cœur du Chat) terminée le 2026-10-13.** `frontend/` (Vite,
  React 19, TypeScript strict), fenêtre pywebview, `launch_unified.py --ui web|tk` (web par défaut
  sur la branche) et `--dev`. Vérifiée dans Chromium (Playwright, serveur de démonstration), puis
  dans la vraie fenêtre WebView2 avec le vrai Ollama. Détails, mesures et bogues corrigés dans le
  journal (section 12).
- Questions de la phase 2 tranchées le 2026-10-13 (décisions D16 à D20, section 8) et appliquées :
  libellé « Réflexion », tokens/s des réponses sans outils, fichiers étrangers retirés, outils de
  vérification versés dans le dépôt, boutons de la phase 3 gardés.
- **Phase 3 : feu vert le 2026-10-13**, découpée en 3a (Chat et barre latérale) puis 3b
  (panneaux, onboarding, visionneuses Office), avec un arrêt et un compte rendu à la fin de 3a.
  Installations permises : paquets de la stack du §6 (cmdk, primitives Radix…) ; demander pour
  tout autre paquet.
- **Phase 3a (Chat et barre latérale) terminée le 2026-10-13** : pièces jointes (menu « + »,
  glisser-déposer, collage), slash commands, modifier et régénérer, notes, lecture et saisie
  vocales, citations et chemins cliquables, cartes de fichiers, image générée, volet d'aperçu
  (artefacts HTML et SVG, PDF, documents), recherche globale, dossiers projet, historique, export,
  lecture automatique, toast des tâches planifiées. Vérifiée dans Chromium (serveur de
  démonstration), et dans la vraie fenêtre WebView2 pour le volet d'aperçu (artefact isolé du pont
  pywebview, lecteur PDF). Détails, mesures et bogues corrigés dans le journal (section 12).
- Questions de la phase 3a tranchées le 2026-10-13 (décisions D21 à D25, section 8) et
  appliquées : essais au vrai matériel faits (PC laissé libre par Nicolas), KaTeX 0.19.0 partout,
  règle de Tk pour Whisper, dossier glissé dans la saisie = ses fichiers joints, vrai tour avec
  Ollama. Ces essais ont trouvé quatre défauts, corrigés (journal, après la phase 3a). Reste à
  essayer à la voix : une vraie dictée.
- Question 26 tranchée le 2026-10-13 : on garde aussi « Dossiers du projet » (D26).
- **Phase 3b (panneaux, onboarding, visionneuses Office) terminée le 2026-10-14** : Réglages,
  assistant de premier lancement, Mémoire, Prompts, Relay (QR code), Aide F1, palette Ctrl+K et
  raccourcis Ctrl+R, Ctrl+virgule et F1, boutons de la barre latérale, Word, Excel et PowerPoint
  dans le volet d'aperçu avec les visionneuses de Windows. Vérifiée dans Chromium (serveur de
  démonstration) et, pour les visionneuses, dans la vraie fenêtre WebView2. Détails, mesures et
  bogues corrigés dans le journal (section 12). Plan de la phase 4 proposé (section 17), en
  attente du feu vert.
- Questions de la phase 3b tranchées le 2026-10-14 (décisions D27 à D31, section 8) et
  appliquées : téléphone (Relay, QR code, badge « Mobile »), vraie dictée et raccourcis au vrai
  clavier essayés avec Nicolas dans la vraie appli ; le Word caché des aperçus se ferme avec
  l'appli (D30) ; adresse locale avec la clé gardée (D31). Détails dans le journal.
- **Phase 4 (page Agents)** : plan en section 17, découpage en 4a puis 4b proposé ; feu vert
  attendu au début de la prochaine conversation.
- Outils de vérification : `frontend/scripts/` (scripts Playwright ; mode d'emploi dans son README)
  et `tools/interface_web/` (serveur de démonstration, pilotage Win32 de la fenêtre, icône).

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

### Installé en phase 3a (2026-10-13)

- @radix-ui/react-dropdown-menu 2.2.1 (menus « + » et Export). @radix-ui/react-dialog passe à
  1.3.1 et @radix-ui/react-tooltip à 1.4.1 : mêmes briques communes que le menu, sinon le build en
  embarquait deux copies. Rien côté Python. `frontend/dist/` : 4,8 Mo, 90 fichiers.
- `npm audit` (dépendances de l'appli) : un avis de faible gravité, antérieur à la phase 3a, sur
  KaTeX 0.16.47, la copie que `rehype-katex` installait pour lui. Réglé le 2026-10-13 (D22) :
  `overrides` impose KaTeX 0.19.0 partout, `npm audit` ne trouve plus rien.

### Installé en phase 3b (2026-10-13 et 2026-10-14)

- cmdk 1.1.1 (palette Ctrl+K), @radix-ui/react-tabs 1.2.1 (onglets de la Mémoire) et
  @radix-ui/react-switch 1.4.1 (Réglages) : paquets du §6. @radix-ui/react-dismissable-layer
  1.2.1 devient une dépendance directe (même version, déjà installée par Dialog) pour les zones
  des toasts. Rien côté Python (`qrcode` était déjà dans `requirements.txt`). `npm audit` ne
  trouve rien. `frontend/dist/` : 4,9 Mo, 99 fichiers.

## 2. Ce que ce PC ne permet pas de vérifier

À faire sur le PC de travail, ou par Nicolas dans la vraie fenêtre :

- Échelles 125 % et 150 %, et deux écrans d'échelles différentes (un seul écran à 100 % ici ; je ne
  modifie pas les réglages d'affichage).
- Python 3.14 + pythonnet ≥ 3.1 + pywebview (PC Arc).
- Placement sur GPU intégré et contexte en 8 bits sur le PC Arc.
- macOS et Linux (`launch.sh`) : aucun des deux PC.
- Recette visuelle finale dans la fenêtre pywebview : je ne vois la fenêtre que par des captures
  (Playwright, ou `win.py capture` pour ce que CDP ne montre pas, comme le lecteur PDF).

Vérifiable ici : Windows, WebView2, visionneuses Office natives, micro, carte NVIDIA, ComfyUI.

Essais au vrai système de la phase 3a : faits le 2026-10-13, PC laissé libre par Nicolas (D21 ;
`frontend/scripts/window_system.mjs`, journal). Restent :

- une vraie dictée à la voix : faite par Nicolas le 2026-10-14 (D28) ;
- la fin d'une vraie tâche planifiée (notification du système ou toast) : sans page Agents
  (phase 4), aucune tâche ne se lance depuis l'interface web ;
- un message du téléphone (badge « Mobile ») et le QR code scanné par un vrai téléphone : faits
  avec Nicolas le 2026-10-14 (D27) ;
- les raccourcis de la phase 3b au vrai clavier (Ctrl+K, Ctrl+virgule, F1, Ctrl+R) : `win.py keys`
  avait été refusé par le verrou de premier plan de Windows ; essayés par Nicolas le 2026-10-14
  (D29) ;
- les visionneuses Office à 125 et 150 % et sur deux écrans (vérifiées à 100 %).

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
- [x] **Assistant de premier lancement** — `interfaces/onboarding.py` (`OnboardingWizard`, `should_run`,
  `detect_ram_gb`, `detect_vram_gb`, `detect_cpu_cores`, `recommend_model`, `pull_model`,
  `apply_model_choice`, `create_custom_model`, `mark_done`), appelé par `launch_unified.py` (étape 3).
  Tk : « 🤖 Bienvenue dans My_AI », statut Ollama, matériel et recommandation, choix qwen3.5:2b/4b/9b,
  progression, journal, « 🚀 Installer » / « Passer » (marque l'assistant comme fait), « 🔄 Réessayer »,
  « ✅ Démarrer My_AI », « Continuer quand même ».
- [x] **Aide F1** — `base.py` (`show_help`). Tk : sections Chat, Éditer & regénérer, Pièces jointes &
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
- [x] **Markdown complet** — `markdown_formatting.py`, `syntax_highlighting.py`,
  `streaming.py` (`_finish_streaming_animation`), `utils/citations.py`, `utils/path_links.py`.
  Écart : Tk n'a **pas de bouton Copier sur les blocs de code** (nouveau dans la cible). Citations : bloc
  « 📚 **Sources** » et marqueurs `[n]` ouverts dans le navigateur ; chemins existants →
  `reveal_in_file_manager`.
- [x] **Pièces jointes** — `interfaces/gui/file_handling.py` (`process_dropped_file`, `process_file`,
  `process_file_background`, `_attachment_loading_started/finished`, `_attachment_removed`,
  `_forget_if_unused`, `_refuse_send_while_loading`, `_process_image_file`, `_on_paste`),
  `layout.py` (`add_file_preview`, `_hide_attachment_spinner`, `clear_file_previews`).
  Tk : menu ＋ (PDF, DOCX, Excel / CSV, PowerPoint, Code, Image, Dossier (codebase)) ; une seule image en
  attente (JPEG 1024 px) ; collage Ctrl+V vers un fichier temporaire au nom fixe ; retirer une pièce
  jointe arrête sa lecture et l'oublie si elle ne sert plus. Écart : le **glisser-déposer refuse les
  dossiers** (« ❌ Chemin invalide ») ; un dossier passe par « Dossiers du projet ».
- [x] **Slash commands** — `slash_commands.py` (`_attach_slash_autocomplete`, `_slash_*`,
  `_expand_slash_command`), `core/prompt_library.py` (`expand`, `search`). La bulle garde la commande
  courte, le modèle reçoit le texte étendu.
- [x] **Édition et régénération avec branches ‹ k/n ›** — `message_editing.py` (`_begin_edit`,
  `_apply_edit`, `_navigate`, `_persist_version`, `_rerender_all`, `_rewind_engine_history`,
  `_regenerate`). Tk : dialogue « Modifier le message », « Regénérer ↻ », refus pendant une génération ou
  sans réponse, texte inchangé = rien, avertissement si des messages suivent. Écart : **pas de
  « régénérer » sans modification** (§8 en demande un au survol).
- [x] **Copie d'un message** — `message_bubbles.py` (`copy_on_double_click`,
  `create_copy_menu_with_notification`), `message_editing.py` (`_copy_message`, bouton 📋 sous les
  messages de l'utilisateur).
- [x] **Note de 1 à 5 étoiles** — `message_bubbles.py` (`_show_timestamp_for_current_message`,
  `_on_star_rating`), `core/rlhf_manager.py`. Tk : `record_interaction(user_query = texte de la bulle
  utilisateur, ai_response = texte affiché, feedback_type positive ≥ 4 / negative ≤ 2 / neutral,
  feedback_score, intent "conversation", confidence 1.0, model_version "ollama")` ; note figée ensuite.
- [x] **Lecture vocale** — `voice_output.py` (`VoiceOutput`), `message_bubbles.py`
  (`_add_speak_button` : 🔊, ⏹ pendant la lecture, 🔇 en erreur), `sidebar.py` (`_make_tts_button`),
  réglage `ui.tts_autoread`.
- [x] **Saisie vocale** — `voice_input.py` (`VoiceInput`, `_WhisperWorker`, `attach_mic_button`),
  `_whisper_worker.py`. Tk : modèle `small` int8 sur CPU ; processus séparé seulement si plusieurs
  runtimes OpenMP sont chargés (macOS) ou `MY_AI_WHISPER_WORKER=1`, avec repli mono-thread ; états
  idle / recording / transcribing / error ; insertion au curseur ; micro désactivé pendant une génération.
- [x] **Génération d'image** — `base.py` (`_handle_image_generation_ui`, `_auto_setup_image_backend`,
  `_attach_generated_image`, `_remember_image_generation`), `models/comfyui_manager.py`,
  `core/ai_engine.py` (`is_image_generation_request`, `extract_image_prompt`, `image_generator`).
  Écart : la session enregistre le texte provisoire « Génération de l'image en cours… » ; **l'image est
  perdue au rechargement**.
- [x] **Génération de fichiers et de documents** — `base.py` (branche « génération de fichier » :
  mots-clés, `process_query`, message tiré au hasard parmi 8, nom cliquable), `file_handling.py`
  (`download_file_to_downloads` : copie dans Téléchargements), `on_document` → `_pending_document_paths`.
- [x] **Volet Artefacts** — `artifacts_panel.py`, `interfaces/artifacts.py`, `message_bubbles.py`
  (`_collect_artifacts`, `_add_artifact_button` « 🔍 Aperçu (n) », `_maybe_auto_open_artifact` : une fois
  par message, jamais à la restauration d'une session). Tk : volet 560 px réglable de 320 à 1200, boutons
  📂 (document), 🌐 (navigateur), ✕. Écart : **pas d'onglets Aperçu / Code** dans Tk (nouveau). Edge
  charge les ressources externes d'un artefact (CDN, polices).
- [x] **Aperçu des documents** — `_preview_handler.py` (`NativePreview`, `AsyncNativePreview`,
  `supports_native_preview`, `NATIVE_EXTENSIONS`), `_dpi_host.py`, `artifacts_panel.py` (`_render_native`,
  « ⏳ Ouverture de l'aperçu Word… »), `interfaces/document_preview.py`. PDF : lecteur d'Edge.
- [x] **Messages du mobile en direct, badge « Mobile »** — `base.py` (`_poll_relay_messages`,
  `_display_relay_message` avec le préfixe 📡, `_process_relay_attachments_then_ai`).
- [x] **Fin de tâche planifiée : toast et notification système** — `base.py` (`_on_scheduled_task_done`,
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

- [x] **Recherche globale** — `sidebar.py` (`_make_section_search`, `_global_search_run`,
  `_global_search_render`, `_global_search_open`, `_global_search_reindex`, `_highlight_in_chat`),
  `core/conversation_search.py`. Tk : 15 résultats « 🧑/🤖 session · extrait », surlignage des mots de la
  requête (sinon du message entier), effacé au clic.
- [x] **Sessions et workspaces** — `sidebar.py` (`_session_new`, `_session_save_current`,
  `_session_load`, `_session_delete`, `_refresh_sessions`), `core/session_manager.py`. Voir les écarts
  (section 7) : pas de sauvegarde automatique, Ctrl+N ne bascule pas sur la nouvelle session.
- [x] **Dossiers projet** — `sidebar.py` (`_folder_attach`, `_folder_reindex`, `_folder_detach`,
  `_ensure_workspace_for_folder`, `_index_folder_async`), `core/folder_indexer.py`. Progression par
  notifications toutes les 10 fichiers ; un workspace est créé si aucun n'est actif.
- [x] **Historique des requêtes** — `sidebar.py` (`_refresh_history`, `_history_toggle_fav`,
  `_history_delete`, `_history_reuse`), `core/command_history.py`. 20 entrées, recherche, « ⭐ Favoris
  uniquement », clic = texte remis dans la saisie.
- [x] **Export Markdown, HTML ou PDF** — `sidebar.py` (`_export_conversation`),
  `core/conversation_exporter.py`.
- [x] **Accès au Relay, à la lecture automatique, aux Réglages, à la Mémoire et aux Prompts** —
  `sidebar.py` (`_make_relay_button`, `_make_tts_button`, `_make_settings_button`,
  `_make_memory_button`, `_make_prompts_button`).

### Fenêtres et panneaux

- [x] **Réglages** — `settings_panel.py` + utilitaires de `interfaces/onboarding.py`
  (`ollama_reachable`, `list_installed_models`, `pull_model`, `apply_model_choice`, `create_custom_model`,
  `apply_generation_params`, `set_config_flag`, `marker_path`). Modèles (liste sans `my_ai`, pull avec
  progression et journal, « ✅ Appliquer » avec confirmation) ; température 0–1 par pas de 0,05,
  num_ctx (2048 à 65536), timeout 30–7200 s, appliqués aussi à l'instance `LocalLLM` en cours ; langue
  par défaut, lecture automatique, `relay.auto_start`, relance de l'onboarding (supprime le marqueur).
- [x] **Mémoire** — `memory_panel.py`, `core/memory_store.py` (`MemoryStore`). Onglets Faits / Documents /
  Conversations, recherche, filtre par catégorie, 20 par page, provenance, édition en ligne, « ➕ Ajouter »,
  suppression confirmée avec « Supprimer aussi le message d'origine ».
- [x] **Prompts** — `prompts_panel.py`, `core/prompt_library.py` (`add`, `update`, `delete`).
- [x] **Relay** — `base.py` (`_toggle_relay`, `_show_relay_info_popup`, `start_relay`, `stop_relay`,
  `_init_relay`). QR code (correction L, marge 4, redessiné quand la liste des tunnels est stable),
  statut des tunnels, URL copiable, « 🧩 Copier pour l'extension VS Code », jeton, appareils connectés,
  « Arrêter le Relay ».
- [x] **Palette Ctrl+K et raccourcis** — `command_palette.py` (`_build_command_list`,
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

### Où en est la checklist après la phase 3b

Cochés ci-dessus : terminés dans l'interface web (phases 2, 3a et 3b). Le téléphone (Relay, QR
code, badge « Mobile »), la dictée et les raccourcis au vrai clavier ont été essayés avec Nicolas
dans la vraie appli le 2026-10-14 (D27 à D29). Restent :

- **Visionneuses Office** : vérifiées à 100 % sur un écran ; 125 %, 150 % et deux écrans restent
  à voir (section 2).
- **Agents** : phase 4 (section 17).

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

### Prises le 2026-10-13 (réponses de Nicolas aux questions de la phase 2)

- **D16. Libellé « Réflexion »**, comme le prompt (§7, §8), suivi de la durée : « Réflexion · 12 s ».
- **D17. Tokens/s des réponses sans outils** : le relevé en lecture seule de D15 est ajouté à
  `models/local_llm.py`, à la fin de `generate_stream` (qui sert aussi aux réponses à une image) et
  de la synthèse de `generate_with_tools_stream`. Le `ChatService` retient le relevé le plus récent
  pris pendant la réponse, de l'orchestrateur ou de `LocalLLM`. Requêtes à Ollama inchangées.
  - Le moment du relevé vient de `time.perf_counter`, dans les deux fichiers. Sous Windows,
    `time.time` n'avance que par pas de 15,6 ms : deux relevés du même tour portaient la même heure,
    et le mauvais l'emportait (test qui échouait). C'est le seul changement apporté au relevé de D15
    dans l'orchestrateur.
- **D18. Fichiers étrangers retirés** : `.env` (vide, du même espace de travail HyperFrames),
  `.env.example`, `AGENTS.md`, `THIRD_PARTY_NOTICES.md`, `package.json`, `package-lock.json` et
  `node_modules/` de la racine, `patterns/`, `templates/`, les six dossiers et le README ajoutés à
  `examples/` (`examples/advanced_features_demo.py` gardé) ; `.gitignore` rendu à sa version commitée.
- **D19. Outils de vérification versés dans le dépôt** : scripts Playwright dans `frontend/scripts/`
  (mode d'emploi dans son README), outils Python dans `tools/interface_web/`. Le banc de rendu
  Markdown ne l'est pas (il dépend de Streamdown, retiré des dépendances) ; les données de test
  (section 4) restent hors dépôt.
- **D20. Boutons de la phase 3 gardés** : affichés et désactivés, avec leur infobulle, puis activés
  au fil de la phase 3.

### Prises le 2026-10-13 (réponses de Nicolas aux questions de la phase 3a)

- **D21. Essais au vrai matériel** : faits par moi, PC laissé libre par Nicolas
  (`frontend/scripts/window_system.mjs`, journal).
- **D22. KaTeX 0.19.0 partout** : `overrides` dans `frontend/package.json` (même paquet, rien de
  nouveau) ; formules revérifiées.
- **D23. Whisper suit la règle de Tk** : dans le processus ; isolé si plusieurs runtimes OpenMP
  sont chargés (macOS) ou avec `MY_AI_WHISPER_WORKER=1`. Accord donné « si ça ne pose pas de
  problème pour la suite », Tk devant disparaître : le code de la voix vit dans
  `interfaces/desktop/` et n'importe rien de Tk. Au retrait de Tk (phase 5) partent seulement les
  relais de `interfaces/gui/` et le paramètre facultatif `ui` de `VoiceInput` et `VoiceOutput`
  (rappels par la boucle Tk).
- **D24. Dossier glissé dans la saisie** : ses fichiers deviennent des pièces jointes, comme sur
  claude.ai. Sous-dossiers compris, sauf les cachés et ceux que l'indexation ignore (`.git`,
  `node_modules`, `__pycache__`…) ; images laissées de côté (le modèle n'en reçoit qu'une par
  message) ; au-delà de 20 fichiers lisibles, refus avec un renvoi à « Dossiers du projet ». Le
  menu « + » garde « Dossier (codebase) » pour les dossiers du projet, comme Tk. Garder aussi
  « Dossiers du projet » : question 26.
- **D25. Vrai tour avec Ollama** : fait (un artefact HTML, un document Word), session supprimée
  ensuite, sans note ; `data/` et `outputs/` remis comme avant (journal).
- **D26. On garde les deux** : le dossier glissé dans la saisie (ses fichiers joints au message,
  D24) et « Dossiers du projet » (dossier indexé, attaché à la conversation).

Note sur D23 : le prompt (§7, §11) demande de garder l'isolation du worker Whisper et son repli
quand il quitte `interfaces/gui/`. C'est fait à l'identique : worker lancé par son chemin, utilisé
quand plusieurs runtimes OpenMP cohabitent (le plantage qu'il évite est propre à macOS) ou avec
`MY_AI_WHISPER_WORKER=1`, repli sur une transcription mono-thread dans le processus.

### Prises le 2026-10-14 (réponses de Nicolas aux questions de la phase 3b)

- **D27. Essai avec le téléphone** : fait ensemble dans la vraie appli, tunnels publics compris
  (journal, après la phase 3b). Le QR code garde les couleurs de Tk : le téléphone l'a lu, et la
  réponse s'y est affichée (confirmé par Nicolas).
- **D28. Vraie dictée** : faite par Nicolas, dans la vraie appli ; transcription exacte
  (« Bonjour, ça va ? », confirmé par Nicolas).
- **D29. Raccourcis au vrai clavier** : essayés par Nicolas, dans la vraie appli.
- **D30. Word caché des aperçus** : il reste lancé tant que l'appli est ouverte (l'aperçu suivant
  s'ouvre plus vite) et se ferme avec l'appli. Seul l'Office lancé par l'appli pour ses aperçus
  est fermé : Word, Excel ou PowerPoint qui a porté une visionneuse de l'appli, lancé par COM
  (« -Embedding ») après elle, sans fenêtre visible ; jamais un Office ouvert par Nicolas ni un
  Office déjà là avant l'appli.
- **D31. Adresse copiée sans tunnel** : l'adresse locale du Relay avec la clé de chiffrement est
  gardée.

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

### Choix techniques de la phase 3a (dans le cadre fixé, pour mémoire)

- **Fichiers locaux** : la page ne lit jamais un chemin de son choix. Images, PDF et aperçus
  passent par des liens signés (`/files/<signature>/<chemin>/<nom>`, HMAC-SHA256 avec une clé
  tirée à chaque lancement, servis hors de `/api`, sans jeton dans l'adresse). Le serveur ne les
  signe que pour un chemin qu'il connaît : pièce jointe, image ou document de la conversation,
  fichier produit par l'appli (`outputs/`, dossier de `generation.output_directory`, rapports de
  `scheduler.output_directory`), image collée (dossier des envois, un sous-dossier par envoi).
  Sauf les PDF, ces fichiers partent avec la CSP `sandbox` ; tous avec `nosniff`.
- **Ouvrir, montrer, télécharger** (`utils/path_links.py`, comme Tk) : un chemin cité dans une
  réponse n'est cliquable que s'il existe, et il se montre dans l'Explorateur, jamais exécuté ;
  seuls les documents produits par l'appli s'ouvrent dans leur application ou se copient dans
  Téléchargements.
- **Artefacts** : page `/preview/<id>` avec sa propre CSP, `sandbox allow-scripts allow-forms
  allow-modals allow-popups`, sans `allow-same-origin` : origine opaque, ni l'API ni la page de
  l'appli ne lui sont accessibles ; ressources externes permises (D8). Documents (Word, Excel,
  PowerPoint, Markdown…) en page HTML sans script ni ressource externe (`sandbox; default-src
  'none'`). « Ouvrir dans le navigateur » écrit la page dans `outputs/artifacts/`.
- **PDF hors bac à sable** : le lecteur PDF de Chromium ne s'affiche pas dans une iframe
  `sandbox`. Le PDF est servi seul, en `application/pdf`, et seulement s'il est connu du serveur.
- **Pont pywebview et iframes** : WebView2 donne `chrome.webview` à chaque cadre, artefacts
  compris, mais pywebview n'écoute que les messages du document principal
  (`CoreWebView2.WebMessageReceived`) et ne déclare aucun objet hôte : un message envoyé au pont
  depuis un artefact n'arrive pas en Python (vérifié dans la vraie fenêtre). À revérifier à chaque
  mise à jour de pywebview (`frontend/scripts/window_preview.mjs`, section 10).
- **Glisser-déposer** : le navigateur ne donne pas le chemin d'un fichier déposé ; WebView2 le
  passe à pywebview (`pywebviewFullPath`), qui le renvoie à la page par l'événement
  `files.dropped`, et la page le remet à la zone où le dépôt a eu lieu. Hors de la fenêtre
  pywebview (navigateur, `--dev`), les fichiers sont envoyés au serveur. Un dossier joint ses
  fichiers (D24 ; Tk le refusait : « ❌ Chemin invalide ») ; dans un navigateur, sans chemin, il est
  écarté avec un message.
- **Notes** : même appel à `record_interaction` que Tk ; la note est gardée dans la session (clé
  facultative, D7), figée aussi à la réouverture.
- **Variantes d'édition** : une variante garde toute sa réponse (réflexion, outils, documents,
  image, durée, note : clé `ai_extra`, D7) ; dans Tk, revenir à une variante n'en rendait que le
  texte. Une variante enregistrée par Tk se rouvre comme avant.
- **Voix** : `voice_input.py`, `voice_output.py` et `_whisper_worker.py` passent dans
  `interfaces/desktop/` (sans Tk) ; `interfaces/gui/` garde le bouton micro et des relais, Tk
  inchangé. Le `VoiceService` publie l'état du micro, la dictée et l'état de la lecture
  (`voice.input`, `voice.transcript`, `voice.output`), importe la voix au premier usage et
  enregistre la lecture automatique dans `config.yaml` (`ui.tts_autoread`, commentaires gardés).
  Whisper suit la règle de Tk : dans le processus, isolé seulement si plusieurs runtimes OpenMP
  sont chargés (macOS) ou avec `MY_AI_WHISPER_WORKER=1` (question 23). Le micro reste actif
  pendant une réponse, comme la zone de saisie (file d'attente, D1) ; Tk le désactivait avec toute
  la saisie.
- **Recherche globale** : surlignage par l'API CSS Custom Highlight, sans toucher au DOM de React ;
  message entier surligné quand aucun mot de la requête n'y figure, comme Tk ; effacé au clic.
- **Dossiers projet** : liste des dossiers dans l'état de la session, mise à jour sous le verrou
  du `ChatService` : une sauvegarde de la conversation ne l'écrase pas.
- **Export** : dialogue « Enregistrer sous » dans la fenêtre ; ailleurs (navigateur, `--dev`),
  `outputs/exports/` avec un nom daté.
- **Toast des tâches planifiées** : comme Tk (6 s, liseré selon le statut, clic = rapport), et
  seulement si la notification du système n'a pas été montrée.
- **Serveur de démonstration** : n'écrit plus rien dans `data/` ni dans le `outputs/` du dépôt
  (incident du journal, phase 3a).
- **Après la phase 3a** (essais au vrai système et vrai tour, journal) :
  - une seule image par message : une nouvelle image remplace celle qui attendait (Tk gardait les
    deux aperçus, mais n'envoyait au modèle que la dernière) ;
  - « Télécharger » n'écrase jamais un fichier du même nom dans Téléchargements : la copie prend
    le premier nom libre, « nom (1).ext », comme dans un navigateur (Tk écrasait) ;
  - modules du micro chargés en arrière-plan à la fin du lancement, comme Tk qui les importait en
    créant l'interface : le premier clic enregistre sans attendre ;
  - artefacts : localStorage et sessionStorage, refusés à une origine opaque, sont remplacés dans
    l'aperçu par un stockage en mémoire qui vit le temps de l'aperçu (ouverte dans un navigateur,
    la page garde le vrai). Les artefacts produits par le modèle s'en servent souvent (état d'un
    compteur, d'une liste) ; cookies et IndexedDB restent refusés.

### Choix techniques de la phase 3b (dans le cadre fixé, pour mémoire)

- **Panneaux** : dialogues internes à la fenêtre (Radix), un seul à la fois, chargés à leur
  première ouverture (morceaux séparés du build). Échap les ferme ; dans la Mémoire, Échap annule
  d'abord une modification en cours.
- **Réglages et assistant** (`model_setup.py`, `settings.py`) : mêmes fonctions de
  `interfaces/onboarding.py` que Tk ; un téléchargement ou une régénération à la fois, progression
  et journal en événements (`models.*`) ; paramètres de génération appliqués aussi au `LocalLLM` en
  cours ; écritures de `config.yaml` qui gardent ses commentaires. L'assistant passe à son étape du
  lancement, avant `my_ai` et le placement ; sans fenêtre (`--headless`), l'étape est sautée.
- **Mémoire** (`memory.py`) : un message de conversation modifié, ou supprimé avec son origine,
  passe par `ChatService.change_saved_message` : retrouvé par son texte près de son index (refus si
  la conversation a changé depuis l'indexation), il change aussi dans la conversation ouverte, et
  la sauvegarde suivante ne le fait pas revenir ; la recherche globale réindexe ensuite la session.
  Le contexte déjà envoyé au modèle n'est pas réécrit, comme dans Tk. Couleurs des catégories en
  jetons (`--memory-*`, reprises des jetons existants).
- **Prompts** (`prompts.py`) : contrôles du formulaire de Tk, erreurs dans le formulaire ; une
  commande créée apparaît aussitôt dans l'autocomplétion.
- **Relay** : Ctrl+R (et le bouton) ouvre le panneau et démarre le Relay s'il ne tourne pas ; il
  ne l'arrête jamais (Tk) ; le panneau se referme sans l'arrêter. Démarrage sous verrou (un seul
  `RelayServer`). QR code calculé en Python (`qrcode`, correction L, marge de 4 modules, comme Tk),
  dessiné en SVG aux couleurs de Tk (modules orange sur fond sombre), une fois la liste des
  tunnels stable 2 s. Sans tunnel, « Copier » copie l'adresse locale avec la clé de chiffrement
  (question 31). Le jeton passe dans `relay.status`.
- **Palette Ctrl+K** (cmdk) : les 14 commandes de Tk, dans son ordre, filtre par sous-chaîne
  (libellé et raccourci), ordre gardé ; palette ouverte, les autres raccourcis attendent sa
  fermeture (fenêtre à part dans Tk). « Afficher / masquer la barre latérale » depuis l'onglet
  Agents revient au Chat, barre ouverte.
- **Toasts** : au-dessus des dialogues et des panneaux ; leurs zones sont des « branches » Radix :
  fermer un toast ne ferme plus le dialogue ouvert. Un dialogue ouvert depuis un panneau voile
  aussi le panneau.
- **Visionneuses Office** (`native_viewer.py`, `preview_handler.py`, `dpi_host.py`) : la page
  demande un aperçu « native » (`/api/previews/document`, champ `native`) ; le serveur ne produit
  la page HTML qu'au repli. La visionneuse se charge masquée dans un `Panel` WinForms posé
  au-dessus de WebView2 (fenêtre DPI par écran) ; si la fenêtre ne l'était pas, repli sur l'hôte
  « popup » de `dpi_host.py` possédé par la fenêtre, comme Tk. Le pont ne connaît que les aperçus
  acceptés par le serveur. La page la masque sous les dialogues, la palette et l'image en grand,
  et sous les menus, infobulles, listes et toasts qui touchent sa place ; elle la recale sur sa
  place (taille, échelle, contrôle toutes les 500 ms) et la masque pendant le redimensionnement du
  volet à la souris. Infobulles de l'en-tête du volet à gauche. Délai d'ouverture : 45 s, puis
  aperçu HTML. Le navigateur du système reçoit la page HTML.
- **Liste « / »** : la souris ne choisit une commande que si elle bouge (une liste ouverte sous un
  curseur immobile garde sa première commande).
- **Serveur de démonstration** : Ollama, mémoire et Relay simulés (ni modèle téléchargé, ni base
  touchée, ni port ni tunnel ouverts) ; vraie `PromptLibrary` sur une copie temporaire.

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

Réponses de Nicolas le 2026-10-13 : « Réflexion » pour la 16, oui à la 17 et à la 19, fichiers
retirés pour la 18, boutons gardés pour la 20 (décisions D16 à D20, section 8).

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

### Questions de la phase 3a (posées le 2026-10-13)

Réponses de Nicolas le 2026-10-13 : essais laissés à ma charge pour la 21, oui à la 22, à la 23
(si rien ne gêne le retrait de Tk) et à la 25 ; pour la 24, un dossier glissé doit joindre ses
fichiers, comme sur claude.ai (décisions D21 à D25, section 8), et question 26.

21. **Essais au vrai clavier et à la vraie souris** (section 2) : dialogues de fichiers,
    glisser-déposer depuis l'Explorateur, Export, micro, lecture vocale, ouverture des fichiers.
    Peux-tu les faire, ou me laisser le PC libre un moment pour que je les fasse ?
22. **KaTeX** : les formules sont rendues par KaTeX 0.16.47, la copie que `rehype-katex` installe
    pour lui, avec la feuille de style et les polices de KaTeX 0.19.0 (dépendance directe).
    `npm audit` signale sur 0.16.47 un avis de faible gravité (GHSA-238p-pmpm-9mq7 : une pollution
    de prototype déjà présente peut contourner l'option `trust`). Je propose d'imposer 0.19.0
    partout (`overrides` dans `package.json` : même paquet, rien de nouveau), puis de revérifier
    les formules. D'accord ?
23. **Whisper** : le plan de la phase 3 (section 15) annonçait le worker toujours isolé ; j'ai
    gardé la règle de Tk (dans le processus sous Windows ; isolé si plusieurs runtimes OpenMP sont
    chargés, ou avec `MY_AI_WHISPER_WORKER=1`). Isoler toujours protégerait l'appli d'un plantage de
    la transcription, au prix d'un processus de plus avec son propre modèle en mémoire et d'une
    première dictée plus lente. Je recommande la règle de Tk. D'accord ?
24. **Dossier déposé dans la saisie** : refusé avec « 📁 Pour un dossier, utilisez « Dossiers du
    projet ». » au lieu de « ❌ Chemin invalide » (Tk). Le garder ainsi, ou l'attacher directement
    comme dossier projet ?
25. **Vrai tour avec Ollama** dans la vraie appli (un artefact HTML, un document) : je ne l'ai pas
    fait, pour ne laisser ni session de test dans `data/workspaces/` ni note dans le RLHF. Le faire
    (session supprimée ensuite, sans note), ou le laisser à tes essais ?

### Question après la phase 3a (posée le 2026-10-13)

26. **Garder « Dossiers du projet » à côté du dossier glissé ?** Nicolas demande mon avis.
    **Réponse le 2026-10-13 : oui, on garde les deux (D26).**
    Recommandation : garder les deux, qui ne font pas la même chose. Un dossier glissé met ses
    fichiers dans le message, une fois : idéal pour quelques fichiers, mais tout passe dans le
    contexte du modèle (32 768 jetons), d'où la limite de 20 fichiers. Un dossier du projet est
    indexé une fois et reste attaché à la conversation : à chaque question, seuls les passages
    utiles sont retrouvés, sans limite de taille, et il se réindexe quand le code change. Pour un
    vrai projet (des centaines de fichiers), seul le second tient. D'accord ?

### Questions de la phase 3b (posées le 2026-10-14)

Réponses de Nicolas le 2026-10-14 : oui à la 27, faite ensemble le jour même, comme la 28 et la
29 (un seul essai, dans la vraie appli) ; pour la 30, fermer le Word caché avec l'appli, le
laisser tant qu'elle est ouverte ; oui à la 31 (décisions D27 à D31, section 8). Après l'essai,
Nicolas confirme que la dictée est exacte et que la réponse s'est affichée sur le téléphone ; il
garde les deux messages de l'essai dans sa conversation et les supprimera lui-même.

27. **Essai avec ton téléphone** (Relay, badge « Mobile ») : il faut la vraie appli, avec ses
    tunnels publics, et ton téléphone. Quand tu es devant le PC : lance My_AI, Ctrl+R, scanne le
    QR code, envoie un message depuis le téléphone ; je vérifie de mon côté (journal, badge, état
    du panneau). Le QR code reprend les couleurs de Tk (modules orange sur fond sombre, code
    « inversé ») : si ton lecteur ne le lit pas, je propose des modules sombres sur fond clair.
    D'accord pour le faire ensemble ?
28. **Vraie dictée** : il faut ta voix (le micro de ce PC n'entend pas la synthèse vocale du PC).
    Peux-tu dicter une phrase dans la vraie appli (bouton micro) et me dire ce qui est inséré ?
29. **Raccourcis au vrai clavier** : dans la vraie appli, Ctrl+K (palette), Ctrl+virgule
    (Réglages) et F1 (Aide) ouvrent-ils bien leur panneau ? Ctrl+R démarre le vrai Relay : à
    garder pour l'essai 27.
30. **Word reste lancé après un aperçu** : la visionneuse de Word tourne dans un `WINWORD.EXE
    -Embedding` qui reste ouvert après l'aperçu, et même après la fermeture de l'appli (Excel et
    PowerPoint se ferment). C'est le comportement d'Office, le même avec Tk et avec le volet
    d'aperçu de l'Explorateur ; le Word suivant s'ouvre alors en 0,2 s au lieu de 1,3 s. Je propose
    de le laisser ainsi. Sinon, l'appli pourrait arrêter, à sa fermeture, le Word qu'elle a lancé.
    D'accord ?
31. **Adresse copiée sans tunnel** : avant l'arrivée des tunnels, « Copier » donne l'adresse
    locale du Relay avec la clé de chiffrement (`http://127.0.0.1:8765/?token=…#k=…`), qui ouvre
    l'interface mobile dans un navigateur du PC. Tk copiait `http://localhost:8765?token=…`, sans
    la clé, qui ne suffit plus depuis le chiffrement. Je garde la nouvelle. D'accord ?

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
- **Visionneuses Office et DPI** : la fenêtre enfant au-dessus de WebView2 fonctionne dans la vraie
  fenêtre à 100 % (2026-10-14 : place au pixel près, masquée sous la palette, suit le volet).
  Restent 125 %, 150 % et deux écrans (la fenêtre WinForms ne se redimensionne pas d'elle-même en
  changeant d'écran, voir plus bas) ; repli « popup » si la fenêtre n'est pas DPI par écran.
- **pythonnet sur Python 3.14** (PC Arc) : version ≥ 3.1 obligatoire ; 3.2.x très récente.
- **Mémoire et sessions** : réglé en phase 3b. Les messages d'origine modifiés ou supprimés par le
  panneau Mémoire passent par le `ChatService`, qui tient la conversation ouverte à jour : une
  sauvegarde ne les écrase plus (section 8).
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
- **Pont pywebview et artefacts** (phase 3a) : un artefact a `chrome.webview` dans son iframe, sans
  effet aujourd'hui (pywebview n'écoute que le document principal). Si une version de pywebview
  écoutait aussi les cadres (`CoreWebView2Frame.WebMessageReceived`), un artefact pourrait appeler
  `shell_api.py` (dialogues, liens externes) : revérifier avec `window_preview.mjs` à chaque mise à
  jour de pywebview.
- **Avertissement du build** (phase 3a) : l'optimiseur CSS de Vite (Lightning CSS) ne connaît pas
  `::highlight()` et le signale ; la règle reste telle quelle dans le CSS construit et fonctionne
  dans WebView2 (surlignage de la recherche vérifié).
- **Mémoire du PC** (phase 3a) : il est arrivé de n'avoir qu'1 Go libre sur 15,7 (PC en usage) ;
  deux tests qui lancent un interpréteur neuf ont alors échoué sur `MemoryError`, puis réussi une
  fois la mémoire revenue.
- **Whisper sur un silence** (constat, comme dans Tk) : sur un enregistrement presque muet, il
  invente parfois un texte (« Thank you. ») et devine la mauvaise langue. Une dictée réelle le dira ;
  le filtre de silence de faster-whisper (`vad_filter`) ou la langue de `config.yaml` pourraient
  l'éviter, sans requête au modèle de chat.
- **Word lancé après un aperçu** (phase 3b) : réglé (D30). Le Word caché reste ouvert tant que
  l'appli tourne et se ferme avec elle ; `test_native_preview.py` ferme aussi celui de ses tests.
  Une fin brutale de l'appli (processus tué) le laisse lancé, comme avant.
- **Mesures sur PC chargé** (phase 3b) : avec 2 Go de mémoire libre, les mesures du défilement et
  du streaming varient du simple au décuple d'un passage à l'autre, pour le build de la phase 3a
  comme pour celui de la phase 3b ; comparer deux builds par passages alternés, dans les mêmes
  conditions.
- **Fichier `nul` du Relay** (constaté le 2026-10-14) : les tunnels serveo et localhost.run lancent
  `ssh` avec `UserKnownHostsFile=nul` (`os.devnull`). Le `ssh` de Git, premier dans le PATH de Git
  Bash, prend `nul` pour un fichier ordinaire et l'écrit dans le dossier de lancement (clé
  publique du serveur, rien de secret). Lancement normal (`launch.bat`, raccourci) : `ssh` de
  Windows, rien d'écrit. Correction possible dans `relay/relay_server.py` (proposée à Nicolas,
  pas faite) ; en attendant, supprimer le fichier après un essai du Relay lancé depuis Git Bash.
- **Chromium sans fenêtre** (captures, phase 3b) : la première seconde après le lancement, les
  animations y avancent au ralenti, sans tâche longue de la page ; `capture_panels.mjs` attend
  1,5 s. À revoir dans la vraie fenêtre si une animation d'ouverture y semblait lente.

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

### Après la phase 2 — 2026-10-13 (réponses aux questions, PC à RTX 3060)

- **Fichiers étrangers** retirés (D18). L'appli ne lit aucun `.env` (pas de `dotenv`).
- **« Réflexion »** (D16) : libellé et test Vitest du bloc. Ce test voyait deux blocs : sans les
  globales de Vitest, Testing Library ne démontait pas le rendu d'un test avant le suivant ; le
  démontage est ajouté à `src/test/setup.ts`.
- **Tokens/s des réponses sans outils** (D17) : relevé dans `LocalLLM`, lecture des deux relevés par
  le `ChatService` ; `tests/test_stream_stats.py` (relevé de `LocalLLM`, flux coupé sans relevé,
  relevés de l'orchestrateur) et deux tests du `ChatService`. Le test « le relevé le plus récent
  l'emporte » a révélé l'égalité des heures (`time.time` par pas de 15,6 ms sous Windows) :
  `time.perf_counter` dans les deux relevés.
- **Outils versés** (D19), revus au passage :
  - plus de chemin propre à ce PC (racine du dépôt déduite du script, fichier de la confirmation de
    suppression pris dans le dossier personnel) ; aides communes dans `frontend/scripts/lib.mjs` ;
    `real_checks.mjs` retiré, doublon de `window_keys.mjs` et `window_tooltips.mjs` ;
  - `win.py` n'envoie touches, curseur ni premier plan qu'après 20 secondes sans clavier ni souris
    (ses propres saisies mises à part ; une minute d'attente au plus, puis refus), et vérifie avant
    chaque touche que My_AI est au premier plan (incident de la phase 2) ; la barre latérale s'ouvre
    par CDP, sans touche système ;
  - serveur de démonstration : sessions copiées dans `temp/demo_server/PORT/`, vidé à chaque
    lancement, et non plus dans un dossier temporaire du système, où chaque arrêt brutal laissait une
    copie (12 copies retirées de `%TEMP%`) ; option `--window` : la vraie fenêtre WebView2 sur le
    serveur de démonstration, sans Ollama ;
  - `make_icon.py` produit toujours exactement `interfaces/desktop/assets/my_ai.ico`.
- **Vérifié avec les outils versés** (Chromium, serveur de démonstration) : 23 captures sans erreur
  de console, bloc « Réflexion · 2 s » ; 10 cas d'infobulle sur 10 refermés ; le fil suit la réponse
  (au plus 38 px du bas) ; défilement des 200 messages dans les fourchettes de la phase 2.
- **Infobulle au vrai curseur, dans la vraie fenêtre** (WebView2 sur le serveur de démonstration,
  `--window`, PC laissé libre par Nicolas) : elle s'affiche au survol et disparaît dès que le vrai
  curseur quitte la fenêtre. Fenêtre restaurée : vers le bas, la barre de titre et la gauche ;
  fenêtre agrandie : vers la barre des tâches et la barre de titre (rien à gauche sur un seul
  écran). Les 10 cas de `tooltips.mjs` (souris de Playwright) passent aussi dans WebView2.
  - Bogue trouvé en route : pywebview vérifie que le fil principal s'appelle `MainThread`, et le
    serveur de démonstration le renommait : `--window` échouait. Corrigé.
  - `win.py` gagne `front` (premier plan, même attente) et `screen` (bornes du bureau) ;
    `window_tooltips.mjs` met la fenêtre devant avant le survol et saute un point de sortie hors de
    l'écran.
- **Tests** : `python -m pytest tests/` : **1034 réussis** (1029 + 5), aucun échec ; front : 47 tests
  Vitest, TypeScript, ESLint et Prettier propres ; `frontend/dist` reconstruit.

### Phase 3a — 2026-10-13 (PC à RTX 3060)

- `main` n'a pas bougé (`543f083`). Paquets : section 1.
- **Front** :
  - pièces jointes : menu « + » (PDF, Word, Excel / CSV, PowerPoint, code, image, dossier projet),
    dialogues du système dans la fenêtre, glisser-déposer sur toute la fenêtre, collage d'image,
    puces (lecture en cours, prête, retrait), envoi refusé pendant une lecture, miniature des
    images ;
  - slash commands : liste sous la saisie (recherche par préfixe dans `PromptLibrary`), Entrée ou
    Tab insère la commande ; la bulle garde la commande courte, le modèle reçoit le texte étendu ;
  - modifier un message (dialogue, avertissement si des messages suivent), « Régénérer » au survol
    d'une réponse (D5), variantes ‹ k/n › ; note de 1 à 5 étoiles, figée ensuite ; lecture d'une
    réponse et lecture automatique ; micro (dictée insérée au curseur) ;
  - réponses : citations `[n]` et chemins existants cliquables, cartes des fichiers et documents
    produits (ouvrir, aperçu, télécharger, Explorateur), image générée avec sa progression, en
    grand au clic ;
  - volet d'aperçu à droite : artefacts HTML et SVG (onglets Aperçu et Code ; ouvert seul une fois
    par réponse, jamais à la réouverture d'une session, comme Tk), PDF, documents en page HTML ;
    largeur réglable de 320 à 1200 px, retenue ; navigateur et Explorateur ;
  - barre latérale : recherche globale (15 résultats ; la conversation s'ouvre au message,
    surligné), dossiers projet (indexation avec sa progression, réindexation, détachement),
    historique des requêtes (20, recherche, favoris, clic = remis dans la saisie), Export
    (Markdown, HTML, PDF), lecture automatique ; Relay, Réglages, Mémoire et Prompts restent
    désactivés (D20) ;
  - toast de fin de tâche planifiée.
- **Backend** :
  - `interfaces/desktop/files.py` (liens signés, fichiers produits par l'appli, ouverture,
    Explorateur, Téléchargements), `previews.py` (pages d'aperçu), `api_files.py` ;
  - `voice.py` et `api_voice.py` ; `voice_input.py`, `voice_output.py` et `_whisper_worker.py`
    déplacés depuis `interfaces/gui/`, qui garde des relais ;
  - `folders.py` (dossiers projet), `api_sidebar.py` (recherche, dossiers, historique, export),
    `routing.py` (aides communes des routes) ;
  - `core/chat_service.py` : note (RLHF), chemins existants des réponses, session d'un dossier
    projet, export, variantes qui gardent toute leur réponse ; aucune requête au modèle en plus ;
    `core/chat_orchestrator.py` inchangé ;
  - `shell_api.py` (dialogues de fichiers), `window.py` (chemins des fichiers déposés),
    `events.py` (événements des fichiers, de la voix, des dossiers et des notes).
- **Tests** : `python -m pytest tests/` : **1080 réussis** (1034 + 46), aucun échec sur le code
  final (2 min 30 à 6 min selon la charge du PC). Lors d'un passage précédent, deux tests qui
  lancent un interpréteur neuf avaient échoué sur `MemoryError` (1 Go de mémoire libre), puis
  réussi (section 10). Front : **80 tests Vitest** (47 + 33), TypeScript, ESLint et Prettier
  propres. Tk importe toujours ses modules (`tests/test_imports.py` : 13 sur 13).
- **Contrôles et captures** (`frontend/scripts/capture_chat.mjs`, Chromium, serveur de
  démonstration) : 26 contrôles sur 26, aucune erreur de console, 32 captures relues. Artefact :
  son script tourne, sa requête vers l'API est bloquée, iframe sans `allow-same-origin` ; volet
  élargi de 200 px par la poignée ; trois cartes de documents, Markdown et Word en pages HTML ;
  seuls les deux chemins existants cliquables ; six citations ; image générée, en grand ; carte
  d'un fichier généré ; PDF choisi, image collée et CSV déposé, avec miniature ; « /code »
  inséré ; variantes 2/2, 3/3 puis retour à 2/3 ; note figée à 4 ; lecture et dictée (voix
  simulée) ; 15 résultats de recherche, deux passages surlignés ; historique ; dossier indexé ;
  export Markdown.
- **Mesures** (protocole de la phase 2 : build de profilage, Chromium sans GPU, serveur de
  démonstration à 80 jetons/s ; PC en usage, environ 3 Go de mémoire libre) :
  - défilement des 200 messages : aucune image au-delà de 33 ms, à la molette (576 images) comme
    très vite (300 images) ; rendus React à 0,3–0,5 ms en médiane, 4,1–5,9 ms au 95ᵉ centile ;
  - réponse de 5 000 jetons avec saisie (une touche toutes les 120 ms) et défilement : une image
    sur 4 419 au-delà de 33 ms (33,4 ms) ; rendus React à 0,2 ms en médiane et 1,3 ms au 95ᵉ
    centile ; saisie au pire à 40 ms (72–80 ms en phase 2) ;
  - calcul Python qui tient le GIL pendant une réponse : affichage intact, jetons à 54 par seconde
    (écart maximal 217 ms), comme en phase 2.
- **Vraie fenêtre WebView2** (serveur de démonstration, `--window`, pilotée par CDP, inactivité du
  PC vérifiée avant l'ouverture ; `frontend/scripts/window_preview.mjs`, 11 contrôles sur 11) :
  - artefact : son script tourne, origine opaque, ni `window.pywebview` ni accès à la page de
    l'appli, requête vers l'API bloquée. `chrome.webview` existe pourtant dans l'iframe (WebView2
    le donne à chaque cadre) ; un message envoyé au pont depuis l'iframe n'arrive pas en Python,
    alors que celui de la page arrive (appel « console » de pywebview, lu dans le journal du
    serveur) : pywebview n'écoute que le document principal (section 8) ;
  - PDF : le lecteur de WebView2 affiche la page (barre d'outils, zoom, « 1 sur 1 »). Les
    captures par CDP le montrent gris, car il dessine hors de la page : `win.py capture` prend la
    fenêtre par `PrintWindow`, sans premier plan ni saisie ;
  - Word en page HTML ; `CSS.highlights` disponible (surlignage de la recherche).
- **Bogues trouvés et corrigés en route** : `--dist` relatif servi en 404 (chemin résolu) ;
  onglet Code sans style ; chemin cliquable coupé en fin de ligne ; cadre de l'image trop large ;
  nom du fichier généré répété à la fin du texte, au-dessus de sa carte ; emoji doublé dans les
  notifications ; deux copies de briques Radix dans le build (versions alignées) ; surlignage
  absent après l'ouverture d'une autre conversation (la liste se place d'abord en bas : défilement
  redemandé) ; une variante d'édition perdait sa réflexion, ses outils, ses documents et sa note ;
  `--window` du serveur de démonstration cassé par son changement de dossier (pywebview situe
  l'appli par `sys.argv[0]`) ; le CSS d'un build dépendait du build précédent, Tailwind cherchant
  aussi des classes dans `frontend/dist/` (commité) : `@source not` sur `dist/` et `scripts/`,
  16 classes inutilisées en moins (45 Ko au lieu de 48), deux builds de suite identiques.
- **Incident, données** : avant d'être corrigé, le serveur de démonstration enregistrait les notes
  dans le vrai `data/rlhf_feedback.db` (une note de test). Retirée : ligne 3 de `feedback` et de
  `learned_patterns`, ligne du 2026-10-13 de `daily_metrics`, compteur remis à 2. Depuis, la
  démonstration garde les notes en mémoire, copie l'historique des requêtes, travaille dans
  `temp/demo_server/PORT/` (aperçus et exports compris). Seule écriture dans `data/` pendant les
  vérifications suivantes : `data/web_cache/cache.db`, que `tests/test_ai_engine.py` (antérieur à
  la migration) ouvre avec un vrai `AIEngine` (purge des entrées expirées).
- **Incident, fenêtre** : en vérifiant le PDF, un clic par CDP visé par un sélecteur trop large a
  touché « Ouvrir rapport_trimestriel.pdf » au lieu de l'aperçu : le PDF de démonstration s'est
  ouvert dans un onglet du Chrome de Nicolas (application des PDF), laissé ouvert. Les scripts
  visent désormais leurs boutons par nom exact et ne cliquent jamais « Ouvrir », « Explorateur »,
  « navigateur » ni « Télécharger » (`frontend/scripts/README.md`).

### Après la phase 3a — 2026-10-13 (réponses aux questions, PC à RTX 3060)

- **Essais au vrai système** (D21), PC laissé libre par Nicolas, sur le serveur de démonstration
  avec la vraie voix (`--window --vraie-voix`), par `frontend/scripts/window_system.mjs` :
  - menu « + » : les six dialogues de Windows, avec les filtres de Tk (PDF, Word, Excel et CSV,
    PowerPoint, code, images), fichier choisi puis joint ; « Dossiers du projet » : dialogue
    « Sélectionner un dossier », dossier indexé puis détaché ; Export : trois « Enregistrer sous »
    (Markdown, HTML, PDF), fichiers écrits là où le dialogue l'a dit ;
  - glisser-déposer à la vraie souris depuis l'Explorateur : un PDF, joint avec son vrai chemin ;
    le dossier des fichiers de test, qui joint ses six fichiers lisibles (D24 ; l'image laissée de
    côté) ;
  - lecture d'une réponse à voix haute (pyttsx3) et lecture automatique, puis remise à `false`
    (`config.yaml` identique ensuite) ; micro : enregistrement, Whisper chargé puis transcription
    en 5 s, texte inséré. Le micro (réseau Intel Smart Sound) annule l'écho : il n'a pas entendu la
    phrase dite par la synthèse du PC, et Whisper a rendu un texte vide, puis « Thank you. » ;
  - chemin cité : Explorateur ; « Ouvrir » d'un document produit : Word ; « Ouvrir dans le
    navigateur » : nouvelle fenêtre de Chrome ; « Télécharger » : copie dans Téléchargements.
    Chaque fenêtre ouverte refermée, la copie supprimée ;
  - outils : `win.py` remplit et valide les dialogues par des messages adressés au dialogue
    (`dialog`), fait un vrai glisser-déposer après l'attente d'inactivité (`drag`), trouve un
    fichier dans l'Explorateur par UI Automation (`element`), liste et ferme des fenêtres
    précises (`windows`, `close HWND`). « Enregistrer sous » ignore un nom posé par `WM_SETTEXT` :
    le nom est saisi caractère par caractère dans la zone (`WM_CHAR`) ; le choix d'un dossier
    demande un second clic, une fois arrivé dans le dossier.
- **Défauts trouvés par ces essais, corrigés** :
  - deux images restaient en attente alors qu'une seule part au modèle : une nouvelle image
    remplace la précédente ;
  - premier clic sur le micro sans effet visible pendant l'import de faster-whisper (plus de 20 s
    dans la démo, qui n'a pas encore chargé torch ; quelques secondes dans l'appli) : modules
    chargés en arrière-plan à la fin du lancement ;
  - « Télécharger » écrasait un fichier du même nom dans Téléchargements, comme Tk : copie en
    « nom (1).ext » ;
  - au vrai tour, l'artefact du modèle gardait son compteur dans `localStorage`, refusé à une
    origine opaque : stockage en mémoire dans l'aperçu (section 8), vérifié dans Chromium et dans
    WebView2 (contrôle ajouté à `capture_chat.mjs` et `window_preview.mjs`, 12 sur 12 dans la
    vraie fenêtre).
- **Vrai tour avec Ollama** (D25 ; vraie appli, `launch_unified.py`, pilotée par CDP) :
  - « Crée une page HTML autonome… avec un bouton qui compte les clics » : réponse en 28 s
    (71,7 tokens/s), volet d'aperçu ouvert seul, iframe sans `allow-same-origin`, le bouton fait
    monter le compteur ;
  - « Rédige un court document Word… » : document produit en 25 s (70,3 tokens/s), carte, aperçu
    en page HTML ;
  - ensuite : session supprimée, les deux requêtes retirées de l'historique, document supprimé de
    `outputs/documents/`, conversation à rouvrir remise dans `data/.desktop_state.json`, journaux
    SQLite repliés : `data/` et `outputs/` ont de nouveau les mêmes fichiers, aux mêmes tailles.
- **KaTeX 0.19.0 partout** (D22) : `npm audit` sans avis ; réponse longue de la démonstration :
  36 formules rendues, aucune erreur, montants en dollars laissés en texte.
- **Dossier glissé** (D24) : `ChatService.add_folder`, `folder_indexer.is_excluded_dir` (mêmes
  dossiers ignorés que l'indexation), dossier écarté avec un message dans un navigateur.
- **Incident, données de test** : pendant la mise au point de `win.py dialog`, trois exports sont
  partis dans `temp/migration_test_data/fichiers/` (nom proposé par le dialogue) ; supprimés.
- **Tests** : `python -m pytest tests/` : **1086 réussis** (1080 + 6) ; front : 80 tests Vitest,
  TypeScript, ESLint et Prettier propres ; `capture_chat.mjs` : 27 contrôles sur 27 ;
  `window_system.mjs` : tous les contrôles passent ; `frontend/dist` reconstruit.

### Phase 3b — 2026-10-13 et 2026-10-14 (PC à RTX 3060)

- `main` n'a pas bougé (`543f083`). Paquets : section 1.
- **Front** :
  - Réglages (Ctrl+virgule) : modèles Ollama (liste sans `my_ai`, téléchargement avec progression
    et journal, « Appliquer » avec confirmation), température, num_ctx, délai, langue, lecture
    automatique, Relay au lancement, relance de l'assistant ;
  - assistant de premier lancement à la place de l'écran de chargement : Ollama, matériel, modèle
    recommandé, installation avec progression et journal, « Passer », « Réessayer », « Démarrer
    My_AI », « Continuer quand même » ;
  - Mémoire : onglets Faits, Documents, Conversations, recherche, catégorie, pages de 20,
    provenance, ajout d'un fait, modification sur place, suppression confirmée (avec le message
    d'origine pour une conversation) ;
  - Prompts : liste, création, modification, suppression ; erreurs dans le formulaire ;
  - Relay (Ctrl+R) : démarrage à l'ouverture, état des tunnels, QR code, « Copier », « Copier pour
    l'extension VS Code », jeton, appareils connectés, « Arrêter le Relay » ;
  - Aide (F1, bouton de l'en-tête) ; palette Ctrl+K avec les 14 commandes de Tk ;
  - boutons Relay, Réglages, Mémoire et Prompts de la barre latérale activés ;
  - volet d'aperçu : Word, Excel et PowerPoint dans la visionneuse de Windows, aperçu HTML en
    repli et dans un navigateur.
- **Backend** :
  - `model_setup.py` et `settings.py` (Réglages, assistant), `memory.py`, `prompts.py`, `qr.py` ;
    routes `api_settings.py`, `api_memory.py`, `api_prompts.py`, `/api/relay/qr` ;
  - `core/chat_service.py` : `change_saved_message` (Mémoire) ; aucune requête au modèle en plus ;
  - lancement : étape de l'assistant ; Relay démarré sous verrou, jeton dans `relay.status` ;
  - visionneuses : `preview_handler.py` et `dpi_host.py` déplacés depuis `interfaces/gui/` (relais
    gardés pour Tk ; `dpi_host.py` prend un handle et un rectangle), `native_viewer.py`, quatre
    fonctions du pont (`native_preview_*`), aperçu « native » de `previews.py`.
- **Tests** : `python -m pytest tests/` : **1120 réussis** (1086 + 34), aucun échec (2 min 24). Front : **94 tests
  Vitest** (80 + 14), TypeScript, ESLint et Prettier propres, `npm audit` sans avis.
  `test_native_preview.py` (vrais Word, Excel et PowerPoint) passe par les modules déplacés ; Tk
  importe toujours ses modules.
- **Contrôles et captures** (Chromium, serveur de démonstration) : `capture_panels.mjs`,
  **45 contrôles sur 45**, 20 captures relues (assistant, Réglages, Mémoire, Prompts, Relay
  simulé, Aide, palette), aucune erreur de console ; `capture_chat.mjs` (phase 3a) : 27 sur 27.
- **Vraie fenêtre WebView2** (serveur de démonstration, `--window`, pilotée par CDP, inactivité
  du PC vérifiée avant chaque ouverture ; `frontend/scripts/window_native.mjs`, 11 contrôles sur
  11, encore après le déplacement de l'hôte DPI) : Word affiche `note_projet.docx` dans le volet
  (processus `WINWORD.EXE`) ; hôte posé au pixel près sur la place réservée par la page ; masqué
  sous la palette, puis revenu ; visible sous un toast qui ne le touche pas ; recalé quand le volet
  change de largeur ; masqué et déchargé à la fermeture du volet ; fermeture de l'appli propre.
  Prête en 1,3 s avec Word fermé, 0,2 s Word déjà lancé.
- **Mesures** (même protocole que la phase 3a, build normal, PC chargé : 2 Go de mémoire libre ;
  deux passages alternés du build de la phase 3a et de celui de la phase 3b, un seul serveur de
  démonstration à la fois) :
  - défilement rapide des 200 messages : 4 et 38 images au-delà de 33 ms (3a), 15 et 46 (3b) ; à
    la molette : 14 et 2 (3a), 3 et 9 (3b) ;
  - réponse de 5 000 jetons avec saisie : 74 et 88 images au-delà de 33 ms sur environ 4 300
    (3a), 105 et 60 (3b) ; saisie au pire à 56 et 48 ms (3a), 56 et 56 ms (3b) ;
  - pas d'écart propre à la phase 3b ; ces chiffres sont moins bons que ceux du journal de la
    phase 3a pour les deux builds, à cause de la charge du PC (section 10).
- **Bogues trouvés et corrigés en route** : fermer un toast fermait le dialogue ouvert (Radix
  traite le clic extérieur au `click`, une fois le toast retiré du DOM) et un toast passait sous
  un panneau ; un dialogue ouvert depuis un panneau ne le voilait pas ; rouge au survol des boutons
  « Supprimer » et « Détacher » perdu (`cn` ne fusionne pas les classes Tailwind) ; liste « / »
  choisie par un curseur immobile (Entrée insérait « /reformule ») ; test de la palette non
  conforme à ESLint (commité sans ESLint, corrigé) ; directives pylint des routes suivies d'un
  texte lu comme des noms de messages (W0012).
- **Outils** : `capture_panels.mjs` (assistant, Réglages, Mémoire, Prompts, Relay, Aide,
  palette), `window_native.mjs` ; `win.py children` (enfants directs de la fenêtre et programmes
  des fenêtres d'autres processus qu'ils contiennent) ; `win.py origin` par la zone client ;
  `window_keys.mjs` n'envoie plus Ctrl+R (vrai Relay dans l'appli) et contrôle Ctrl+K,
  Ctrl+virgule et F1. Serveur de démonstration : Ollama, mémoire et Relay simulés,
  `--premier-lancement`.
- **Incidents** : aucun sur les données. Les tests de visionneuse et les passages dans la vraie
  fenêtre ont laissé des `WINWORD.EXE -Embedding` (lancés par eux, sans document de Nicolas) :
  arrêtés à chaque fois (question 30).

### Après la phase 3b — 2026-10-14 (réponses aux questions, PC à RTX 3060)

- **Essai avec Nicolas** (D27 à D29) dans la vraie appli (`launch_unified.py`, port de débogage),
  suivie en lecture par CDP (`frontend/scripts/window_watch.mjs`) et par le journal de l'appli,
  sans saisie de ma part :
  - raccourcis au vrai clavier : Ctrl+K a ouvert la palette, Ctrl+virgule les Réglages, F1
    l'Aide ; Échap les a refermés ;
  - dictée : micro, enregistrement, transcription par Whisper (« small », chargé au premier
    appel) en 5,1 s, « Bonjour, ça va ? » inséré dans la zone de saisie ;
  - Relay par Ctrl+R : tunnels localhost.run et cloudflared actifs en 4 et 8 s (serveo n'a pas
    répondu) ; le téléphone s'est connecté par le QR code 23 s après l'ouverture du panneau ;
    son message est arrivé avec le badge « Mobile », réponse en 3 s (premier jeton en 1,65 s),
    envoyée au téléphone ; « Arrêter le Relay » a fermé les tunnels et le client. Comme dans
    Tk, le message du téléphone s'ajoute à la conversation ouverte ;
  - Nicolas confirme : la dictée est exacte, la réponse s'est affichée sur le téléphone. Les deux
    messages de l'essai restent dans sa conversation « Explique en détail, avec un exemple de
    code… » : il les supprimera lui-même, ne pas y toucher.
- **D30 appliquée** (`native_viewer.py`) : les processus qui portent une visionneuse sont notés
  quand elle se charge et quand elle se ferme ; à la fermeture de l'appli, après le déchargement de
  la visionneuse, Word, Excel ou PowerPoint caché lancé pour les aperçus reçoit `WM_CLOSE`, puis
  est arrêté s'il reste. Vérifié dans la vraie fenêtre : aperçu fermé, Word encore lancé ; appli
  fermée, plus aucun Word (« Office caché des aperçus fermé avec l'appli »). Tests : sélection sur
  des processus simulés, vrai Word lancé puis fermé (`test_native_preview.py`, 19 sur 19 ; plus
  aucun Office derrière le module).
- **Outil** : `frontend/scripts/window_watch.mjs`, journal d'un essai fait à la main (panneaux,
  raccourcis reçus par la page, micro, saisie, Relay, messages, toasts), en lecture seule. Au
  premier passage, il cherchait le jeton dans l'adresse : la page l'en retire et le garde dans
  `sessionStorage` ; corrigé.
- **Mémoire du PC** : avec l'appli de l'essai encore ouverte (environ 1 Go) et le modèle chargé, il
  ne restait que 0,9 Go libre ; un passage de `test_native_preview.py` s'est arrêté sur une erreur
  interne de pytest (`MemoryError`) et a laissé un Word et un Excel lancés, arrêtés ensuite. Appli
  fermée, le passage suivant est complet.
- **Tests** : `tests/test_desktop_*.py` et `tests/test_chat_service.py` : 183 réussis ;
  `test_native_preview.py` : 19 réussis.

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

## 15. Plan de la phase 3 (approuvé le 2026-10-13 ; 3a réalisée le 2026-10-13, 3b en section 16)

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

## 16. Plan de la phase 3b (feu vert le 2026-10-13, réalisé le 2026-10-14)

But (prompt, §9) : le reste des sections « Structure générale » et « Fenêtres et panneaux » du §7
et les visionneuses Office natives (§5, D8) : Réglages, Mémoire, Prompts, Relay, Aide F1, palette
Ctrl+K et raccourcis, assistant de premier lancement, aperçu natif de Word, Excel et PowerPoint
dans le volet d'aperçu ; puis la vérification avec un vrai téléphone.

Fichiers créés ou complétés :

- Front : panneaux Réglages, Mémoire, Prompts, Relay (QR code) et Aide ; palette Ctrl+K (cmdk,
  paquet du §6) avec les commandes de Tk ; raccourcis Ctrl+R (Relay), Ctrl+virgule (Réglages),
  F1 (Aide) ; assistant de premier lancement, avant l'écran de chargement ; volet d'aperçu : place
  réservée à la visionneuse native (position, taille et échelle envoyées au backend), visionneuse
  masquée sous les menus, dialogues et notifications ; boutons de la barre latérale activés.
- Backend : routes et événements, en réutilisant le moteur. Réglages : fonctions de
  `interfaces/onboarding.py` (modèles installés, téléchargement avec progression, application du
  modèle, paramètres de génération, drapeaux de `config.yaml` en gardant ses commentaires, comme
  Tk). Mémoire : `MemoryStore` (faits, documents, conversations, édition, suppression avec le
  message d'origine, synchronisée avec l'état du chat). Prompts : `PromptLibrary` (ajout, édition,
  suppression). Relay : état, démarrer et arrêter, tunnels, jeton, appareils, QR code produit en
  Python (`qrcode`, déjà dans `requirements.txt`). Assistant : détection du matériel,
  recommandation, téléchargement, création du modèle `my_ai`, marqueur, à son étape du lanceur.
  Visionneuses : `_preview_handler.py` et `_dpi_host.py` déplacés dans `interfaces/desktop/`
  (relais côté Tk), visionneuse en fenêtre enfant au-dessus de WebView2, pilotée par
  `shell_api.py`.
- Tests : pytest pour chaque route et service, `tests/test_native_preview.py` sur les modules
  déplacés ; Vitest pour les panneaux et la palette ; captures Playwright ; vraie fenêtre pour les
  visionneuses (Office est installé sur ce PC).

Étapes : (1) Réglages et assistant de premier lancement (mêmes fonctions) ; (2) Mémoire ;
(3) Prompts ; (4) Relay et QR code, puis vérification avec un vrai téléphone (badge « Mobile »)
et une vraie dictée à la voix ;
(5) Aide F1, palette Ctrl+K et raccourcis ; (6) visionneuses Office natives ; (7) captures,
mesures, recette et compte rendu.

Risques :

- Visionneuses Office en fenêtre enfant au-dessus de WebView2 : la page ne peut rien dessiner
  par-dessus (menus, dialogues, notifications), il faut la masquer à temps et suivre le DPI de
  l'écran ; tests à 125 et 150 % impossibles ici.
- Assistant de premier lancement : il passe avant le placement et le chargement du moteur ; rien
  ne doit appeler Ollama avant la fin du placement (section 10), panneau Réglages compris.
- `config.yaml` : garder ses commentaires à chaque écriture (Réglages, assistant).
- Mémoire : supprimer un fait « avec le message d'origine » modifie une session ; si c'est la
  conversation ouverte, l'état du chat doit suivre sans écraser la modification (section 10).
- Relay : le QR code doit se redessiner quand la liste des tunnels change, comme Tk ; vérification
  avec le téléphone de Nicolas, à faire ensemble.

Écarts au plan, à la fin de la phase 3b :

- Vérification avec un vrai téléphone et vraie dictée : à faire avec Nicolas (questions 27 et 28).
- Raccourcis au vrai clavier : pas encore vérifiés (question 29).
- Visionneuses : l'hôte « popup » de `dpi_host.py` reste en repli de la fenêtre enfant (§5 du
  prompt), pour une fenêtre qui ne serait pas DPI par écran ; Vitest pour les couches et le
  placement, `window_native.mjs` pour la vraie fenêtre.

---

## 17. Plan de la phase 4 (proposé le 2026-10-14, en attente du feu vert)

But (prompt, §9) : tous les éléments de la section « Agents » du §7, avec le design de la page
Agents du §8 (inspirée de Codex). Le backend existe (`relay/agent_relay.py`, `core/scheduler.py`,
`interfaces/resource_monitor.py`) : l'exposer, ne pas le réécrire.

Fichiers créés ou complétés :

- Backend : `interfaces/desktop/agents.py` et `api_agents.py` (liste des agents, agents
  personnalisés, plan d'exécution, exécution d'un agent ou d'un workflow, débat, arrêt), en
  appelant `AgentRelayService` ; événements `agents.*` (début et fin de chaque agent, jetons
  streamés par agent, statut des nœuds, fin du workflow) dans `events.py` et `lib/events.ts` ;
  tâches planifiées (liste, création, édition, suppression, activation, « exécuter maintenant »,
  historique) en routes et événements ; moniteur de ressources échantillonné côté serveur (CPU,
  RAM, GPU, VRAM, inférence, tokens/s) en événements ; notification du système en fin de tâche
  longue (`utils/desktop_notify.py`, comme Tk). Pièces jointes de la zone de tâche par le même
  chemin que le chat (`processors/attachments.py`).
- Front (`features/agents/`) : grille des 9 agents (icônes lucide teintées de leur couleur) et
  des agents personnalisés ; dialogue de création et d'édition (prompt système généré) ; zone de
  tâche (pièces jointes, collage d'image, micro) ; fils d'exécution avec statut en direct,
  rouvrables, sorties streamées par agent, Stop, diff pour un code modifié ; canvas de workflow
  avec `@xyflow/react` (paquet du §6) : glisser depuis la grille, ports, zoom, déplacement, grille
  et aimantation, minimap, sélection multiple, suppression, liens animés pendant l'exécution,
  statut des nœuds, Save / Load / Export au format JSON de `WorkflowCanvas.to_dict` ; mode Débat ;
  statistiques et moniteur (barres par seuil, mini-graphiques de 60 mesures) ; vue des tâches
  planifiées (prochaine exécution, dernier résultat).
- Tests : pytest pour les routes et services ; Vitest pour le canvas (lecture et écriture du JSON
  de Tk), les fils et les composants ; captures Playwright ; vraie exécution avec Ollama.

Étapes : (1) routes et événements des agents, grille, agents personnalisés ; (2) zone de tâche,
exécution d'un agent seul, fils, Stop ; (3) canvas, workflows séquentiel, parallèle et DAG,
Save / Load / Export ; (4) Débat ; (5) statistiques et moniteur ; (6) tâches planifiées et
notification de fin ; (7) captures, mesures, recette et compte rendu.

Découpage proposé, comme la phase 3 : **4a** = étapes 1 à 3 (grille et agents personnalisés,
zone de tâche, exécution d'un agent seul et des workflows avec leurs fils et Stop, canvas), avec
captures, tests et un arrêt pour compte rendu ; **4b** = étapes 4 à 6 (Débat, statistiques et
moniteur, tâches planifiées et notification de fin), puis l'étape 7 pour toute la phase. À
confirmer par Nicolas avec le feu vert.

Risques :

- Une seule file vers Ollama (`n_slots = 1`) : un workflow en parallèle et une réponse du chat se
  partagent le modèle ; garder l'ordre et l'arrêt de Tk, sans requête en plus (section 10).
- Compatibilité du JSON des workflows existants (`WorkflowCanvas.to_dict`) : relire ceux de
  `data/` avant d'en écrire.
- Tokens/s du moniteur à 0 dans Tk (écart, section 5) : à calculer depuis les statistiques
  d'Ollama, comme le chat (D10).
- GPU et VRAM sur le PC Arc (pas de NVML) : affichage dégradé à prévoir.
- « Exécuter même l'appli fermée » (Planificateur de tâches de Windows) : vérifier les droits et
  ne rien laisser derrière les essais.
- Canvas avec beaucoup de nœuds ; liens animés sans coût continu.
