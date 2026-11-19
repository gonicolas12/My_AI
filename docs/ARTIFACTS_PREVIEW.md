# Panneau « Artifacts » — Aperçu live HTML/CSS/SVG et documents

Affiche un rendu en direct du HTML/CSS/SVG généré par l'IA — ainsi que des
**documents produits** (docx, pdf, pptx, xlsx…) — à côté du chat. Disponible dans la **fenêtre desktop** (volet d'aperçu à
droite du chat, et de la page **Code**) et sur l'**interface mobile Relay**.

> 100% local — aucun appel réseau de l'appli. Cohérent avec la promesse de
> confidentialité du projet.

## Vue d'ensemble

| Élément | Rôle |
|---|---|
| [`interfaces/artifacts.py`](../interfaces/artifacts.py) | Détection + préparation du document, **partagé** fenêtre/serveur Relay |
| [`interfaces/document_preview.py`](../interfaces/document_preview.py) | Rendu HTML des documents bureautiques, **partagé** fenêtre/serveur Relay |
| [`interfaces/desktop/previews.py`](../interfaces/desktop/previews.py) | Pages d'aperçu de la fenêtre : artifacts HTML/SVG et documents |
| [`interfaces/desktop/native_viewer.py`](../interfaces/desktop/native_viewer.py) | Visionneuses Office posées dans le volet d'aperçu |
| [`interfaces/desktop/preview_handler.py`](../interfaces/desktop/preview_handler.py) | Visionneuses natives Word/PowerPoint/Excel (`IPreviewHandler`) |
| [`frontend/src/features/preview/`](../frontend/src/features/preview/) | Volet d'aperçu (onglets Aperçu et Code, place réservée aux visionneuses, ouverture automatique) |
| [`frontend/src/lib/artifacts.ts`](../frontend/src/lib/artifacts.ts) | Détection côté fenêtre (bouton « Aperçu » sous les réponses) |
| [`relay/code_links.py`](../relay/code_links.py) | Fichiers qu'une réponse de la page Code cite ou nomme, chemins relatifs au workspace de VS Code compris |
| [`relay/static/app.js`](../relay/static/app.js) | Détection + modale `<iframe sandbox>` côté mobile |
| [`relay/static/style.css`](../relay/static/style.css) | Styles du bouton et de la modale mobile |

## Détection des artifacts

La détection réutilise la convention de blocs de code Markdown du projet
(fences ` ``` ` avec langage optionnel). Un bloc est considéré « rendable » si :

- son langage est `html` / `htm` / `xhtml`, **ou** `svg` ;
- ou bien (langage absent / `xml`) son contenu **ressemble** à du HTML/SVG
  (`<!doctype html>`, `<html>`, `<body>`, `<div>`, `<table>`, `<svg>`…).

Cela évite de proposer un aperçu pour du JSON, du Python, etc. Les fragments
sont enveloppés dans un document complet au thème sombre (cohérent avec la
fenêtre) ; un document déjà complet (`<!doctype>` / `<html>`) est rendu tel quel.

La logique de `frontend/src/lib/artifacts.ts` et de `app.js` est un miroir du
module Python (mêmes règles, mêmes titres déduits via `<title>` puis `<h1>`).

## Artifacts « document »

Un document produit par `generate_document` / `edit_document` (cf.
[DOCUMENT_GENERATION.md](DOCUMENT_GENERATION.md)) devient un artifact de type
document, porteur d'un chemin de fichier au lieu d'un code. Il rejoint la même
file que les blocs HTML : même bouton « Aperçu », même volet, même compteur
quand il y en a plusieurs.

Le chemin remonte du moteur jusqu'à la réponse par le callback `on_document`
de `AIEngine.process_query_stream()` — décalque exact de `on_image`, déjà en
place pour les images générées :

```
outil MCP → AIEngine._register_document()
          → tool_executor observe la liste → on_document(path)
          → ChatService (core/chat_service.py) : événement document.created,
            puis clé « documents » du message enregistré
          → fenêtre : bouton « Aperçu » + ouverture automatique
```

Chaque document est affiché **dans son propre format** :

| Format | Rendu dans le volet |
|---|---|
| **docx, pptx, xlsx** (et doc, ppt, xls, xlsm) | **Visionneuse native de Windows** : Word, PowerPoint ou Excel affichent le document eux-mêmes. Sans elle (pas d'Office, ou elle a échoué), le PDF qu'en tire Office ou LibreOffice, dans le lecteur PDF de WebView2 (voir ci-dessous) |
| **csv** | **Visionneuse d'Excel**, par une copie .xlsx du fichier (voir ci-dessous) ; son texte dans l'onglet Code |
| **pdf** | Lecteur PDF de WebView2 (`needs_native_viewer()` : le fichier est servi tel quel, dans la page) |
| md, txt | Page HTML produite par `interfaces/document_preview.py` |

**Sans visionneuse native : le document tel qu'il s'imprime.** Les visionneuses
de la fenêtre sont celles qu'Office installe sous Windows. Sans elles (pas d'Office,
macOS, Linux), et sur le téléphone ou dans VS Code, un document Word, Excel ou
PowerPoint passe par un PDF : Word, Excel ou PowerPoint l'exportent (Windows, par
COM, sans fenêtre), sinon LibreOffice s'il est installé, toutes plateformes
([`office_pdf.py`](../interfaces/office_pdf.py) ; une copie par version du fichier,
[`utils/preview_cache.py`](../utils/preview_cache.py)). La fenêtre sous Windows
l'ouvre dans son lecteur PDF, sous le nom du document ; la page HTML (téléphone,
VS Code, fenêtre sous macOS et Linux) en montre les pages en images : 12 pages,
30 diapositives, chaque page d'Excel réduite à son tableau (une page à l'italienne
en entier serait illisible sur un téléphone). Toucher une page l'agrandit 2,5 fois
(elle défile alors en largeur), toucher encore la rend à la largeur : une case à
cocher, la page n'ayant pas de script. Sans Office ni LibreOffice, le rendu HTML
reste : texte et tableaux pour Word, tableaux pour Excel, une carte par diapositive.

Office ouvre le fichier sans macros (`AutomationSecurity` désactivée) ni dialogue,
avec un mot de passe factice (un fichier protégé échoue au lieu d'attendre une saisie
invisible ; il n'est pas réessayé pendant le lancement), au plus 90 s. Word et Excel
ont une instance à eux pour l'export, quittée ensuite (Word ne part pas seul : sans
`Quit`, il restait en mémoire) ; Excel imprime chaque feuille sur une page de large,
à l'italienne, grille et en-têtes de lignes et de colonnes compris, ses 1000
premières lignes. PowerPoint n'a qu'une instance, que la visionneuse de la fenêtre
occupe peut-être déjà : une présentation ouverte par l'utilisateur sert à l'export
sans être fermée, et PowerPoint n'est jamais quitté (lancé pour l'export, il part
seul quand plus rien ne le retient).

**CSV.** Windows n'a pas de visionneuse pour le CSV. Il est lu comme l'ouvrirait
un tableur ([`utils/csv_table.py`](../utils/csv_table.py)) : encodage (BOM, UTF-8,
sinon Windows-1252 comme les exports d'Excel en France), séparateur (« ; », « , »,
tabulation ou « | », celui qui donne des colonnes régulières), cellules entre
guillemets (séparateur, guillemets doublés, retours à la ligne). La fenêtre le
montre dans la visionneuse d'Excel par une copie .xlsx
([`csv_workbook.py`](../interfaces/desktop/csv_workbook.py) : en-tête en gras et
figé, colonnes à la largeur de leur texte, nombres en nombres, une copie par version
du fichier dans le dossier temporaire, effacée après une semaine). La page HTML (repli,
téléphone, VS Code) en fait un tableau ; ses cellules vont à la ligne après « / »,
et la feuille s'élargit avec un tableau plus large que l'écran.

Les visionneuses sont celles du **volet d'aperçu de l'Explorateur Windows**
(interface COM `IPreviewHandler`), qu'Office enregistre pour ses formats :
un .docx s'affiche comme dans Word, un .pptx avec ses diapositives, un .xlsx
avec sa grille et ses onglets. Voir
[`preview_handler.py`](../interfaces/desktop/preview_handler.py).

- **Non bloquant** : démarrer Office à froid prend quelques secondes (Excel et
  Word ~2 à 5 s mesurées, PowerPoint ~2,5 s). Le pilotage passe par un thread
  COM dédié (`AsyncNativePreview`) : le volet affiche « Ouverture de l'aperçu
  Word… » et le chat reste utilisable. Au-delà de 45 s, le volet passe au repli
  ci-dessous.
- **Repli** : si aucune visionneuse n'est enregistrée (Office absent) ou
  qu'elle échoue, le volet montre le PDF qu'en tire Office ou LibreOffice
  (voir plus haut) ; sans l'un ni l'autre, le document est rendu en HTML — une
  **feuille de papier** posée sur le fond sombre du volet, comme dans la modale
  du mobile Relay.
- **Sens d'écriture** : la page prend le sens de l'interface (de droite à
  gauche en arabe), et chaque titre, paragraphe, liste ou tableau celui de son
  propre texte (`dir="auto"`) : un document arabe se lit de droite à gauche
  sous une interface française, un document français de gauche à droite sous
  une interface arabe. Le code reste de gauche à droite.
- **Word caché** : après le premier aperçu d'un .docx, le serveur de
  visionneuse de Word (`WINWORD.EXE -Embedding`, ~100 Mo de RAM privée
  mesurés) reste en mémoire pour être réutilisé (aperçus suivants en ~1 s).
  Il se ferme avec l'appli. Seul l'Office lancé par l'appli pour ses aperçus
  est fermé, jamais un Office ouvert par l'utilisateur ni un Office déjà
  lancé avant l'appli.

Le volet porte, pour les documents, les boutons **Ouvrir dans son
application** et **Afficher dans l'Explorateur**.

## Fichiers cliqués : où s'ouvre leur aperçu

Un fichier que l'on clique a le même aperçu, quel que soit son format (image,
code, Markdown, PDF, Word, Excel, CSV…). Il s'ouvre selon l'endroit du clic :

| Où | Ce que l'on clique | Où il s'ouvre |
|---|---|---|
| Chat et page Code de la fenêtre | pièce jointe d'un message envoyé, fichier cité ou nommé dans une réponse, carte d'un document produit et image générée (chat) | **volet de droite** de la page (‹ k/n › entre les pièces jointes d'un message) |
| Zones de saisie du chat et de la page Code, zone de tâche des agents | pièce jointe pas encore envoyée | **fenêtre d'aperçu au premier plan** |
| Page Agents | pièce jointe d'un fil, fichier cité ou nommé dans un résultat, bloc HTML ou SVG | **fenêtre d'aperçu au premier plan**, jamais de volet de droite |
| Mémoire, onglet Documents | un document | volet à droite du panneau |
| Téléphone et VS Code | pièce jointe, fichier cité ou nommé, bloc HTML ou SVG | fenêtre par-dessus la vue ([`preview.js`](../relay/static/preview.js)) |

Un chemin cité n'est un lien que s'il existe sur le PC. Un dossier s'ouvre dans
l'Explorateur ; sur le téléphone et dans VS Code, seuls les fichiers sont des
liens.

## Ouverture automatique

À la fin de la génération d'un message, le volet s'ouvre **tout seul** sur le
premier artifact — HTML comme document —. Le bouton
« Aperçu » sous la réponse (« Aperçu (n) » s'il y en a plusieurs) rouvre le
volet après fermeture. Logique : [`useAutoOpen.ts`](../frontend/src/features/preview/useAutoOpen.ts).

Trois garde-fous :

- **une seule ouverture par message** ;
- **jamais à la réouverture d'une conversation**, ni pour une réponse
  interrompue ou en erreur ; changer de conversation ferme le volet ;
- **délai de 120 ms** avant l'ouverture, pour laisser la réponse finir sa mise
  en page.

Côté mobile, `attachArtifactButton()` prend un paramètre `autoOpen`, vrai
uniquement pour une réponse fraîche et faux au rechargement de l'historique.

### Page Code de la fenêtre

La page Code (conversation de l'extension VS Code) a **son propre volet**, le
même que celui du chat : un volet ouvert dans l'une ne paraît pas dans
l'autre, et la retrouve en revenant (`page` du store `preview.ts`). Il n'y en
a qu'un à la fois : en ouvrir un sur une page ferme celui de l'autre.
Effacer la conversation Code, d'où que ce soit, le ferme.

S'y ouvrent les pièces jointes des messages envoyés (d'ici, de VS Code ou du
téléphone), les fichiers que les réponses citent ou nomment et leurs blocs
HTML ou SVG (bouton « Aperçu »). Les liens sont calculés par le serveur
([`relay/code_links.py`](../relay/code_links.py)), à la fin de la réponse et à
chaque lecture de la conversation :

- chemins absolus existants, comme dans le chat ;
- chemins relatifs au workspace de VS Code (« src/app.ts », « README.md »),
  cherchés dans les dossiers ouverts au moment du message, gardés avec la
  réponse : ils restent des liens après un redémarrage, VS Code fermé ;
- noms seuls (« shell.ts ») des fichiers que les outils de la réponse ont lus,
  écrits ou ouverts, et des pièces jointes de la conversation.

Un fichier n'est un lien que s'il existe sur ce PC ; un VS Code sur une autre
machine n'a donc pas de liens. Un dossier s'ouvre dans l'Explorateur.

Le volet ne s'y ouvre **jamais tout seul** : les réponses de VS Code montrent
souvent du JSX ou des gabarits, que la détection (`<div>` dans le bloc) prend
pour une page HTML.

## Rendu dans la fenêtre desktop

### Artifacts HTML/SVG : une iframe isolée

La fenêtre étant un Chromium (WebView2 sous Windows), l'artifact s'affiche
**exactement** comme dans un navigateur, sans moteur de rendu à part :

- page `/preview/<id>` du serveur local, avec sa propre politique de sécurité
  (CSP), chargée dans une **`<iframe sandbox>`** (`allow-scripts allow-forms
  allow-modals allow-popups`) **sans** `allow-same-origin` : origine opaque, ni
  l'API du serveur local ni la page de l'appli ne sont accessibles à l'artifact ;
- `localStorage` et `sessionStorage`, refusés à une origine opaque, sont
  remplacés dans l'aperçu par un stockage en mémoire qui vit le temps de
  l'aperçu (les artifacts produits par le modèle s'en servent souvent) ;
- onglets **Aperçu** et **Code** ; **Ouvrir dans le navigateur** écrit la page
  dans `outputs/artifacts/` et l'ouvre dans le navigateur du système ;
- volet à largeur réglable (320 à 1200 px), retenue d'un lancement à l'autre.

Comme dans un navigateur, un artifact qui référence une ressource externe
(CDN, police) la **charge** : c'est le prix du rendu exact. L'IA, elle, reste
100% locale.

### Visionneuses Office : une fenêtre enfant posée sur le volet

Aucun élément HTML ne peut accueillir une fenêtre native : la page **réserve
la place** de la visionneuse (un élément vide du volet) et envoie à Python, par
le pont de la fenêtre (`shell_api.py`), sa position et sa taille en pixels
physiques (`getBoundingClientRect` × `devicePixelRatio`), à chaque changement.
[`native_viewer.py`](../interfaces/desktop/native_viewer.py) pose la
visionneuse exactement dessus, dans une **fenêtre enfant** (`WS_CHILD`) de la
fenêtre de l'appli, placée au-dessus du contrôle WebView2 : elle suit la
fenêtre quand on la déplace, la réduit ou l'agrandit, sans barre de titre, ni
entrée dans la barre des tâches ou Alt+Tab.

- **Superpositions** : rien de HTML ne peut s'afficher par-dessus une fenêtre
  native. La visionneuse est masquée (le volet montre alors son fond) sous la
  palette Ctrl+K, les dialogues, les menus, les infobulles et les notifications
  qui touchent sa place, et pendant que le volet s'ouvre ou se ferme ; elle
  revient une fois tout immobile.
- **Redimensionnement** : quand on tire la poignée du volet, la visionneuse
  reste affichée et suit sa place en direct. Les places partent une à une
  (pywebview répond à chaque appel dans son propre thread, sans ordre garanti :
  `shell.ts` n'en envoie une qu'une fois la précédente posée, la plus récente
  seulement) et le thread COM fond en une seule les demandes de
  redimensionnement qui attendent (`AsyncNativePreview.resize`) : la visionneuse
  ne rattrape pas chaque position en retard.
- **DPI** : le processus de l'appli passe en « DPI par écran » (v2) avant que
  pywebview crée sa fenêtre, et la visionneuse garde ainsi un rendu net à 125 %
  ou 150 %.

#### Le piège du DPI : l'hôte « popup » de repli

Une fenêtre étrangère (visionneuse Office, d'un autre processus) ré-parentée
dans une fenêtre qui **ne** gère **pas** le DPI par écran est mal rendue sur un
écran mis à l'échelle : Windows aligne l'enfant sur le régime de son parent,
mais le processus propriétaire continue de dessiner en pixels physiques. Le
contenu est alors mis à l'échelle deux fois : décalé, rogné, parfois une zone
blanche. Sur un écran à 100 %, les deux repères coïncident et rien
n'apparaît. Diagnostic mené par mesures, pas par hypothèses (à l'époque de
l'interface Tk, qui ne gérait pas le DPI) :

| Piste | Résultat |
|---|---|
| Hébergement DPI « mixte » (`SetThreadDpiHostingBehavior`) | Sans effet : ne vaut pas entre processus |
| **Fenêtre hôte DPI par écran** | **Rendu exact et net** |

Si la fenêtre de l'appli n'a pas pu passer en DPI par écran, la visionneuse est
donc posée dans [`dpi_host.py`](../interfaces/desktop/dpi_host.py) : une fenêtre
Win32 sans bordure, **elle-même DPI par écran**, possédée par la fenêtre de
l'appli (elle la suit à la réduction et reste au-dessus d'elle, sans barre des
tâches ni Alt+Tab), posée au pixel près sur la place réservée et recalée quand
la fenêtre se déplace (`is_dpi_virtualized` décide).

Couvert par [`tests/test_native_preview.py`](../tests/test_native_preview.py)
(vrais Word et Excel) et
[`tests/test_desktop_native_viewer.py`](../tests/test_desktop_native_viewer.py).

### Hors Windows

Les documents Office sont rendus en HTML par `interfaces/document_preview.py`,
comme sans visionneuse installée ; les PDF et les artifacts HTML/SVG
s'affichent comme sous Windows, dans le Chromium (ou WebKit) de la fenêtre.

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

- **Visionneuses natives** : fenêtre desktop sous Windows avec Office installé ;
  ailleurs, et sur le mobile Relay, le PDF qu'en tire Office ou LibreOffice, sinon
  le rendu HTML. macOS (Quick Look) et Linux ne sont pas vérifiés sur une vraie
  machine ; le chemin LibreOffice n'est vérifié que par des tests simulés.
- **Superpositions** : une visionneuse native est masquée tant qu'un élément
  HTML (menu, dialogue, notification) touche sa place.
- **Hôte popup** (repli DPI) : comme il flotte au-dessus du volet, un glisser
  rapide de la fenêtre peut le montrer brièvement en retard d'une image.
- **Échelles 125 % et 150 %, deux écrans** : vérifiés sur la vraie fenêtre à
  100 % seulement à ce jour.
- Côté **desktop** comme côté **mobile**, un artifact charge les ressources
  externes qu'il référence explicitement (CDN, polices).
