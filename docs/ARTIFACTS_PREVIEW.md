# Panneau « Artifacts » — Aperçu live HTML/CSS/SVG et documents

Affiche un rendu en direct du HTML/CSS/SVG généré par l'IA — ainsi que des
**documents produits** (docx, pdf, pptx, xlsx…) — à côté du chat, façon
*Claude Artifacts*. Disponible sur le **GUI desktop** (CustomTkinter) et sur
l'**interface mobile Relay**.

> 100% local — aucun appel réseau. Cohérent avec la promesse de confidentialité
> du projet.

## Vue d'ensemble

| Élément | Rôle |
|---|---|
| [`interfaces/artifacts.py`](../interfaces/artifacts.py) | Détection + préparation du document, **partagé** desktop/serveur |
| [`interfaces/document_preview.py`](../interfaces/document_preview.py) | Rendu HTML des documents bureautiques, **partagé** desktop/serveur |
| [`interfaces/gui/artifacts_panel.py`](../interfaces/gui/artifacts_panel.py) | Volet de preview desktop (`ArtifactsPanelMixin`) |
| [`interfaces/gui/message_bubbles.py`](../interfaces/gui/message_bubbles.py) | Bouton « 🔍 Aperçu » + ouverture automatique sous les réponses IA |
| [`relay/static/app.js`](../relay/static/app.js) | Détection + modale `<iframe sandbox>` côté mobile |
| [`relay/static/style.css`](../relay/static/style.css) | Styles du bouton et de la modale mobile |

## Détection des artifacts

La détection réutilise la convention de blocs de code Markdown du projet
(fences ` ``` ` avec langage optionnel), comme
`syntax_highlighting._preanalyze_code_blocks`. Un bloc est considéré
« rendable » si :

- son langage est `html` / `htm` / `xhtml`, **ou** `svg` ;
- ou bien (langage absent / `xml`) son contenu **ressemble** à du HTML/SVG
  (`<!doctype html>`, `<html>`, `<body>`, `<div>`, `<table>`, `<svg>`…).

Cela évite de proposer un aperçu pour du JSON, du Python, etc. Les fragments
sont enveloppés dans un document complet au thème sombre (cohérent avec le
GUI) ; un document déjà complet (`<!doctype>` / `<html>`) est rendu tel quel.

La logique JS de `app.js` est un miroir exact du module Python (mêmes règles,
mêmes titres déduits via `<title>` puis `<h1>`).

## Artifacts « document »

Un document produit par `generate_document` / `edit_document` (cf.
[DOCUMENT_GENERATION.md](DOCUMENT_GENERATION.md)) devient un `Artifact` de
`kind="document"`, porteur d'un `file_path` au lieu d'un `code`. Il rejoint la
même file que les blocs HTML : même bouton « 🔍 Aperçu », même volet, même
compteur quand il y en a plusieurs.

Le chemin remonte du moteur jusqu'à la bulle par le callback `on_document`
de `AIEngine.process_query_stream()` — décalque exact de `on_image`, déjà en
place pour les images générées :

```
outil MCP → AIEngine._register_document()
          → tool_executor observe la liste → on_document(path)
          → GUI : _pending_document_paths
          → fin de streaming : container.document_paths
          → _collect_artifacts() → bouton + ouverture automatique
```

Chaque document est affiché **dans son propre format** :

| Format | Rendu dans le volet |
|---|---|
| **docx, pptx, xlsx** (et doc, ppt, xls, xlsm) | **Visionneuse native de Windows** : Word, PowerPoint ou Excel affichent le document eux-mêmes |
| **pdf** | Lecteur PDF d'Edge (`needs_native_viewer()` : le fichier est servi tel quel) |
| md, txt, csv, potx (modèle PowerPoint) | Page HTML produite par `interfaces/document_preview.py` |

Les visionneuses sont celles du **volet d'aperçu de l'Explorateur Windows**
(interface COM `IPreviewHandler`), qu'Office enregistre pour ses formats :
un .docx s'affiche comme dans Word, un .pptx avec ses diapositives, un .xlsx
avec sa grille et ses onglets. Voir
[`_preview_handler.py`](../interfaces/gui/_preview_handler.py).

- **Non bloquant** : démarrer Office à froid prend quelques secondes (Excel et
  Word ~2 à 5 s mesurées, PowerPoint ~2,5 s). Le pilotage passe par un thread
  COM dédié (`AsyncNativePreview`) : le volet affiche « ⏳ Ouverture de
  l'aperçu Word… » et le chat reste utilisable.
- **Repli** : si aucune visionneuse n'est enregistrée (Office absent) ou
  qu'elle échoue, le document est rendu en HTML — une **feuille de papier**
  posée sur le fond sombre du volet. C'est aussi ce rendu HTML que reçoit le
  mobile Relay.
- **Word reste chargé** : après le premier aperçu d'un .docx, le serveur de
  visionneuse de Word (`WINWORD.EXE -Embedding`, ~100 Mo de RAM privée
  mesurés) reste en mémoire pour être réutilisé (aperçus suivants en ~1 s).
  C'est le comportement de Word, identique avec le volet d'aperçu de
  l'Explorateur ; il n'est pas tué à la fermeture, car Word peut réutiliser ce
  processus pour des documents ouverts par l'utilisateur. Excel et PowerPoint
  se ferment d'eux-mêmes.

Le volet gagne un bouton **📂** (visible pour les seuls artifacts document) qui
ouvre le vrai fichier dans son application système.

## Ouverture automatique

À la fin de la génération d'un message, le volet s'ouvre **tout seul** sur le
premier artifact — HTML comme document —, comme sur Claude web. Le bouton
« 🔍 Aperçu » reste en place pour rouvrir le volet après fermeture.

Le point d'étranglement est unique :
`_show_timestamp_for_current_message()`, appelé par les quatre chemins de fin
de message (streaming, animation, mode instantané, génération de fichier).

Trois garde-fous :

- **une seule ouverture par message** (`container.artifact_autoopened`) ;
- **jamais pendant la restauration d'une session** : le mode `instant=True`
  pose `container.autoopen_allowed = False`, sinon recharger une conversation
  ferait surgir le volet pour chaque ancien message ;
- **délai de 120 ms** avant l'ouverture, pour laisser la bulle finir son
  layout — le volet provoque un reflow de la colonne chat, qui recalculerait
  sinon la hauteur d'une bulle à mi-course.

Côté mobile, `attachArtifactButton()` prend un paramètre `autoOpen`, vrai
uniquement pour une réponse fraîche et faux au rechargement de l'historique.

## Rendu desktop — choix du moteur

**Décision : Edge `--app` embarqué (rendu Chromium EXACT), avec repli
tkinterweb puis code source.**

Le moteur est sélectionné dans cet ordre par
[`artifacts_panel.py`](../interfaces/gui/artifacts_panel.py) :

| Priorité | Moteur | Rendu | Notes |
|---|---|---|---|
| 0 | **Visionneuse native** (documents Office) | **Exact** (Word, PowerPoint, Excel) | Windows + Office ; `comtypes` (installé avec `pyttsx3`) |
| 1 | **Edge `--app` embarqué** | **Exact** (Chromium) | Windows ; **aucune dépendance Python** (réutilise Edge + WebView2 déjà présents) |
| 2 | tkinterweb | Approximatif | Pur Python, CSS limité (pas de flexbox/grid/JS) — bandeau d'avertissement affiché |
| 3 | Code source + bouton 🌐 | — | Dernier recours |

### Comment fonctionne l'embarquement Edge

[`_edge_embed.py`](../interfaces/gui/_edge_embed.py) lance
`msedge.exe --app=file://…/outputs/artifacts/artifact_*.html` avec un profil
temporaire dédié, repère la **nouvelle** fenêtre Chromium (classe
`Chrome_WidgetWin_1`) par diff avant/après lancement, puis la **ré-parente**
dans le widget du volet via l'API Win32 `SetParent` (en retirant bordure et
barre de titre). La fenêtre est redimensionnée avec le volet (`<Configure>`)
et recalée quelques instants après l'attachement, Chromium pouvant réappliquer
ses propres dimensions (fin de chargement, changement de DPI en multi-écran).

#### Le piège du lanceur

Le `msedge.exe` lancé n'est **qu'un lanceur** : il démarre le vrai processus
navigateur puis se termine en moins d'une seconde. Deux conséquences, qui
étaient deux bugs :

| Symptôme | Cause | Parade |
|---|---|---|
| Fenêtres empilées dans le volet ; ~15 processus Edge qui survivaient à chaque fermeture | `close()` terminait le lanceur, déjà mort | L'instance est retrouvée par son **profil temporaire** (`--user-data-dir`, présent dans la ligne de commande de tous ses processus) et terminée en entier via `psutil` |
| Une fenêtre étrangère (VS Code, Teams, navigateur) avalée dans le volet ; la nôtre flottante, barre de titre visible | Toute nouvelle fenêtre `Chrome_WidgetWin_1` était éligible — c'est la classe de **toutes** les applis Chromium/Electron | Seules les fenêtres dont le processus porte **notre** profil sont retenues |
| Rectangle blanc dans le volet | Le profil était supprimé sous un Edge encore vivant | Le profil n'est supprimé qu'une fois les processus morts ; les profils abandonnés de plus d'une heure sont balayés au démarrage |

Rouvrir l'aperçu déjà affiché (clic sur « 🔍 Aperçu » juste après
l'ouverture automatique) ne relance plus Edge : le volet est simplement
ré-affiché. Un jeton de rendu neutralise les sondes d'attachement d'un rendu
remplacé entre-temps.

Ces comportements sont couverts par
[`tests/test_edge_embed.py`](../tests/test_edge_embed.py), qui lance un vrai
Edge (Windows uniquement).

#### Le piège du DPI : la fenêtre hôte

L'appli **ne gère pas le DPI** : sa racine est un `TkinterDnD.Tk` (pour le
glisser-déposer), or CustomTkinter n'active la prise en charge du DPI qu'à la
création d'une fenêtre `ctk.CTk`. Sur un écran à 125 %, Windows agrandit donc
toute la fenêtre en bitmap.

Ré-parenter Edge (qui gère le DPI par écran) dans un widget de cette fenêtre
ne fonctionne pas : Windows aligne la fenêtre enfant sur le régime de son
parent, **mais Chromium continue de se croire en pixels physiques**. Son
contenu est alors mis à l'échelle deux fois : décalé vers la droite, rogné,
barre de titre visible, et une zone blanche à gauche quand Edge tourne en
rendu logiciel. Sur un écran à 100 %, les deux repères coïncident et rien
n'apparaît. Diagnostic mené par mesures, pas par hypothèses :

| Piste | Résultat |
|---|---|
| Hébergement DPI « mixte » (`SetThreadDpiHostingBehavior`) | Sans effet : ne vaut pas entre processus |
| Forcer Edge sans DPI (`__COMPAT_LAYER`, `--high-dpi-support=0`) | Ignoré par Chromium |
| `--disable-direct-composition` | Corrige la position, pas l'échelle |
| `--force-device-scale-factor` | Ignoré par Edge |
| **Fenêtre hôte DPI par écran** | **Rendu exact et net** |

[`_dpi_host.py`](../interfaces/gui/_dpi_host.py) crée une fenêtre Win32 sans
bordure, **elle-même DPI par écran**, possédée par la fenêtre principale (elle
la suit à la réduction et reste au-dessus d'elle), et posée au pixel près sur
le volet. Edge — et les visionneuses Office — y sont ré-parentés : même
régime DPI, plus de double mise à l'échelle. Le volet la recale à chaque
déplacement ou redimensionnement (`_sync_embedded_geometry`). Si la fenêtre
principale devient un jour DPI-aware, l'hôte n'est plus utilisé et Edge
retourne directement dans le volet (`is_dpi_virtualized`).

Couvert par [`tests/test_native_preview.py`](../tests/test_native_preview.py).

### Compromis assumé

- **Windows uniquement** : le ré-parentage `SetParent` est spécifique à Win32.
  Sur les autres OS, on retombe automatiquement sur tkinterweb puis le code
  source + bouton navigateur.
- **Hack natif** : juggling de `HWND` entre processus — robuste mais peut
  présenter de légers artefacts (z-order/redimensionnement) dans des cas
  limites ; tout échec est silencieux et déclenche le repli.
- **Ressources externes** : comme c'est un vrai Chromium, un artifact qui
  référence un CDN (police Google, etc.) **chargera** cette ressource — c'est
  le prix du « rendu exact ». L'IA, elle, reste 100% locale.

### Pourquoi pas pywebview / PySide6 (QtWebEngine) ?

Tous deux donnent un rendu Chromium exact, mais :
- **pywebview** ouvre une fenêtre séparée (boucle d'événements bloquante sur le
  thread principal, difficile à embarquer dans Tk) ;
- **PySide6 + QtWebEngine** embarquerait, mais ajoute une dépendance lourde
  (plusieurs centaines de Mo), en tension avec la promesse « léger ».

Edge `--app` embarqué donne le **rendu exact sans aucune dépendance Python
supplémentaire**.

### Repli léger optionnel

```bash
pip install tkinterweb   # moteur de repli si Edge indisponible (rendu approximatif)
```

## Rendu mobile

Le mobile étant déjà du web, le preview utilise une **`<iframe sandbox>`** :

- contenu injecté via `srcdoc` (aucune requête réseau) ;
- `sandbox="allow-scripts"` **sans** `allow-same-origin` → isolation forte
  (l'artifact ne peut pas accéder au DOM de l'app ni aux cookies) ;
- bouton **« 🌐 »** : ouvre le document dans un nouvel onglet via un
  `Blob` local (`URL.createObjectURL`), toujours sans réseau.

Aucune route serveur n'est nécessaire pour les blocs HTML/SVG : tout est rendu
côté client à partir du texte déjà reçu, ce qui évite tout état côté serveur et
reste 100% local.

### Documents sur mobile

Un document ne peut pas être détecté depuis le texte de la réponse : il faut le
fichier. Il est donc poussé par un événement WebSocket `ai_document`, décalqué
de `ai_image` et **chiffré de la même façon** (`encrypt_json()` →
AES-256-GCM) — le document ne transite jamais en clair par le tunnel public.
Aucune route non chiffrée n'a été ajoutée.

L'événement transporte deux charges : le HTML d'aperçu rendu par l'hôte (pour
l'iframe `srcdoc`) et le fichier réel en base64 (pour le bouton **💾** de
téléchargement, qui reconstruit un `Blob` local).

L'outil s'exécutant avant que le modèle ne rédige sa synthèse, l'événement
arrive **avant** la réponse finale : `app.js` l'empile dans `pendingDocuments`
et le rattache à la bulle au moment où elle est rendue.

## Limitations connues

- **Edge embarqué** : Windows uniquement ; ré-parentage natif (`SetParent`)
  pouvant présenter de légers artefacts dans des cas limites.
- **Fenêtre hôte** : comme elle flotte au-dessus du volet, un glisser rapide
  de la fenêtre principale peut la montrer brièvement en retard d'une image ;
  cliquer dans l'aperçu active l'hôte (la barre de titre de My_AI passe alors
  en inactif, comme avec toute fenêtre).
- **Visionneuses natives** : desktop Windows avec Office installé ; ailleurs,
  et sur le mobile Relay, le document est rendu en HTML.
- **tkinterweb** (repli) : pas de flexbox/grid/JS → utiliser le bouton 🌐.
- Côté **desktop**, le rendu exact (Edge) charge les ressources externes
  référencées par l'artifact (CDN, polices). Côté **mobile**, l'iframe
  `srcdoc` ne charge rien d'extérieur par défaut au-delà de ce que le HTML
  demande explicitement.
