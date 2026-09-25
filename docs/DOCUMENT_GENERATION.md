# 📄 Génération et modification de documents

My_AI produit des documents bureautiques réels — **Word, PDF, PowerPoint,
Excel**, Markdown, CSV, HTML, texte — à partir d'une simple demande en langage
naturel, et sait modifier ceux que vous lui joignez.

> 100% local : le contenu est rédigé par votre modèle Ollama, le rendu est fait
> par des bibliothèques Python installées sur la machine. Aucun appel réseau.

## 🚀 Utilisation

```
génère moi un docx sur les baleines
fais-moi un PDF de synthèse sur la conservation marine
crée une présentation PowerPoint sur le cycle de l'eau
un tableur Excel comparant les espèces de cétacés
```

Le document est écrit dans `outputs/documents/` et **l'aperçu s'ouvre
automatiquement** dans le volet latéral (cf.
[ARTIFACTS_PREVIEW.md](ARTIFACTS_PREVIEW.md)).

> « Génère un **tableau** excel… » part bien vers un classeur : seul, le mot
> « tableau » désigne un tableau de données, pas une peinture. La génération
> d'image ne le prend qu'avec un style pictural (« un tableau impressionniste »,
> « à l'huile »…), cf. [IMAGE_GENERATION.md](IMAGE_GENERATION.md).

### Modifier une pièce jointe

Joignez un fichier avec 📎 ou par glisser-déposer, puis demandez la
modification :

```
dans ce docx, remplace "rorqual commun" par "petit rorqual"
ajoute une section Conclusion à ce document
dans ce classeur, mets 33 dans la cellule B2 de la feuille Ventes
ajoute une diapo de remerciements à cette présentation
```

> ⚠️ **Le fichier d'origine n'est jamais écrasé.** La version modifiée est
> écrite à côté, dans `outputs/documents/<nom>_modifie.<ext>`. Si une copie du
> même nom existe déjà, un compteur est ajouté — aucune modification
> précédente n'est perdue.

## 🧱 Architecture

```
Requête utilisateur
    ↓
ChatOrchestrator → outil MCP 'generate_document' ou 'edit_document'
    ↓
DocumentGenerator._write_content()      ← le LLM rédige le corps en Markdown
    ↓
markdown_document.parse_markdown()      ← Markdown → liste de blocs
    ↓
Backend du format (docx / pdf / pptx / xlsx / …)
    ↓
outputs/documents/  +  callback on_document → volet « Aperçu »
    ↓
Synthèse du modèle : présentation du document d'après son plan
```

### Orchestration : quatre pièges évités

Le chemin ci-dessus paraît évident, mais quatre comportements de
[`ChatOrchestrator`](../core/chat_orchestrator.py) et du modèle le brisaient.
Les garde-fous correspondants sont couverts par `tests/test_document_routing.py`.

**1. La synthèse forcée coupait le plan.** Quand un outil de recherche rapporte
plus de 500 caractères, l'orchestrateur retire les outils pour éviter que le
modèle ne boucle. Un plan légitime — « je cherche d'abord, je rédige ensuite » —
était donc tronqué : l'utilisateur recevait un résumé dans le chat à la place de
son fichier. `_wants_document()` détecte qu'un livrable est attendu et, tant
qu'aucun outil producteur n'a tourné, laisse la boucle continuer.

**2. La recherche était jetée.** `generate_document` relance le modèle pour
rédiger ; ce second appel n'avait aucun accès à ce que la recherche venait de
trouver. `AIEngine._remember_research()` conserve les résultats des outils de
collecte du tour et les réinjecte dans le prompt de rédaction (plafond
`_RESEARCH_CONTEXT_MAX`, 8000 caractères).

**3. La synthèse ne savait pas ce que contenait le document.** Le contenu est
rédigé par un appel LLM séparé, à l'intérieur de l'outil : le modèle qui
présente ensuite le résultat à l'utilisateur ne l'a jamais vu. Pour qu'il
puisse en faire un petit résumé sans l'inventer, `generate_document` renvoie
le **plan** du document (titres de niveau 1 et 2) dans son message de succès.

**4. Le modèle annonçait le document sans le créer.** Un petit modèle local
termine parfois son tour par « Je vais créer un document PDF… Commençons
par… », sans appeler l'outil : la réponse s'arrêtait là, sans fichier. Le
prompt système demande désormais d'appeler l'outil sans annonce préalable, et
l'orchestrateur relance le modèle **une fois** quand :

- la requête réclame un document (`_wants_document()`) et l'outil
  `generate_document` est disponible ;
- la réponse est courte (600 caractères au plus) et annonce l'action ou avoue
  une incapacité (« je vais », « commençons », « je ne peux pas »…,
  `_announces_without_acting()`) ;
- elle ne pose pas de question : « Sur quel sujet ? » attend légitimement une
  précision.

L'annonce reste affichée ; l'appel d'outil et la synthèse s'y enchaînent comme
après un préambule. Le tour relancé n'est pas affiché : si le modèle répond
encore en texte, ou si Ollama ne répond plus, la première réponse reste la
réponse du tour, sans doublon.

> **Confirmation de secours.** Si la synthèse ne produit rien (délai dépassé,
> Ollama tombé), `_document_confirmation()` affiche un message construit à
> partir du résultat de l'outil — sinon le moteur retomberait sur une
> génération sans outils qui ignore l'existence du fichier. Ce secours exige
> que le **dernier** outil ait réussi à produire un document avec un chemin
> exploitable : un échec ne doit jamais être masqué par un ✅ automatique.

### Coût en passes de modèle

Une demande de document coûte **quatre appels** au modèle local :

| Appel | Rôle |
|---|---|
| Décision (tour 1) | choisir l'outil |
| Rédaction | écrire le contenu — de loin le plus long |
| Décision (tour 2) | constater que le travail est fait |
| Synthèse | présenter le document à l'utilisateur |

Quand le modèle annonce le document au lieu de le créer (piège 4), la relance
ajoute un cinquième appel.

Deux raccourcis ont été écartés volontairement : un court-circuit par
mots-clés avant le tour 1 (« génère un rapport à partir de ce que tu trouves
sur le web » doit pouvoir déclencher une recherche), et la suppression de la
synthèse (une présentation naturelle du document a été préférée au gain de
temps).

| Module | Rôle |
|---|---|
| [`generators/markdown_document.py`](../generators/markdown_document.py) | Parseur Markdown → blocs (`Heading`, `ListBlock`, `Table`, `CodeBlock`…), **socle commun à tous les backends** |
| [`generators/document_generator.py`](../generators/document_generator.py) | Orchestration + un backend de rendu par format |
| [`generators/document_editor.py`](../generators/document_editor.py) | Modification d'un document existant, toujours sur une copie |
| [`interfaces/document_preview.py`](../interfaces/document_preview.py) | Rendu HTML pour le volet d'aperçu et la modale mobile |
| [`processors/pptx_processor.py`](../processors/pptx_processor.py) | Lecture des présentations jointes |

### Pourquoi un parseur Markdown maison

Les backends ont besoin d'une **structure**, pas de HTML : python-pptx veut des
puces avec un niveau, openpyxl veut des lignes de cellules, python-docx veut
des runs stylés. Passer par `markdown` → HTML → re-parsing perdrait justement
cette structure. Le parseur couvre ce qu'un LLM produit réellement (titres,
listes imbriquées, tableaux, fences, gras/italique/code/liens), pas CommonMark
en entier.

Deux comportements volontaires, hérités de l'usage technique :

- `snake_case_comme_ceci` **n'est pas** de l'italique (pas d'emphase intra-mot
  sur les underscores) ;
- `***texte***` donne bien gras **et** italique, et l'imbrication
  `*ital **gras** fin*` conserve les deux styles.

## 🎨 Ce que rend chaque format

| Format | Bibliothèque | Rendu |
|---|---|---|
| **docx** | python-docx | Titres H1–H4, gras/italique/code, listes à puces et numérotées **imbriquées**, tableaux stylés, blocs de code tramés, pied de page « Page N », sommaire (champ `TOC`) dès 3 titres |
| **pdf** | reportlab | Styles de titres, listes, tableaux à en-tête coloré et lignes alternées, code préformaté, filets, numérotation de page |
| **pptx** | python-pptx | Couverture, une diapo par `##`, puces hiérarchisées, tableaux natifs, **découpe automatique** au-delà de 9 puces (`Section (2)`, `(3)`…) |
| **xlsx** | openpyxl | Un onglet par tableau (nommé d'après la section), en-tête figé + filtre auto, largeurs ajustées, **nombres convertis en nombres**, onglet « Notes » pour la prose |
| **md / txt / html / csv** | — | Markdown canonique, texte à colonnes alignées, page HTML autonome, CSV `;` |

### Sommaire Word

Le champ `TOC` est inséré en XML brut (python-docx n'a pas d'API pour cela).
Word calcule la table à l'ouverture ; si elle reste vide, **F9** la force.

### Markdown dans les tableaux

Les LLM mettent souvent en gras la première colonne d'un tableau
(`| **Taille** | 30 m |`). Le parseur garde les cellules en texte brut ; chaque
backend passe par `_cell_inlines()` pour restituer gras, italique et code —
sans quoi les astérisques apparaissaient tels quels dans le document. Une
cellule Excel n'ayant qu'un style, elle passe en gras quand elle l'est
entièrement ; CSV et texte reçoivent le texte sans marqueurs.

## 🔧 Les deux outils MCP

Enregistrés dans `AIEngine._setup_local_tools()`
([core/ai_engine.py](../core/ai_engine.py)), au même titre que `generate_code`
ou `write_local_file`.

### `generate_document`

| Paramètre | Rôle |
|---|---|
| `brief` *(requis)* | Sujet et consignes de rédaction |
| `format` | `docx` (défaut), `pdf`, `pptx`, `xlsx`, `csv`, `md`, `txt`, `html` |
| `title` | Titre du document ; déduit du contenu s'il est absent |
| `content` | Corps en Markdown **déjà rédigé** ; sinon le LLM s'en charge |
| `filename` | Nom de fichier souhaité, sans dossier |

Le mode par défaut (`content` vide) est le plus fiable avec un petit modèle
local : rédiger un long Markdown **dans un argument JSON d'appel d'outil** est
justement ce que ces modèles ratent le plus souvent. La rédaction se fait donc
dans un second appel dédié, avec un prompt système spécialisé (et adapté au
format : consignes différentes pour une présentation ou un classeur).

### `edit_document`

| Paramètre | Rôle |
|---|---|
| `path` *(requis)* | Chemin du document, ou simple nom de fichier s'il est joint |
| `operations` *(requis)* | Liste ordonnée de modifications |
| `output_name` | Nom de la copie modifiée |

Opérations disponibles :

| Action | Champs | Formats |
|---|---|---|
| `replace_text` | `find`, `replace` | tous |
| `append_markdown` | `content` | docx, md, txt, csv, pdf |
| `replace_section` | `heading`, `content` | docx, md, txt, pdf |
| `delete_paragraph` | `contains` | docx, pptx, md, txt, pdf |
| `set_cell` | `sheet`, `cell`, `value` | xlsx |
| `append_row` | `sheet`, `values` | xlsx |
| `append_slide` | `title`, `content` | pptx |

Les noms d'action et de champs sont **normalisés** (`remplacer`, `old_text`,
`add_slide`, `contenu`… sont acceptés) : les petits modèles locaux nomment ces
champs de façons très variables, et refuser sur un synonyme reviendrait à faire
échouer une demande parfaitement claire.

#### Préservation du formatage

Un remplacement de texte se fait **d'abord run par run** : si l'occurrence tient
dans un seul run, sa mise en forme (gras, couleur, police) est intégralement
conservée. Le repli au niveau du paragraphe n'intervient que si Word ou
PowerPoint a découpé l'occurrence sur plusieurs runs — auquel cas le paragraphe
prend le formatage de son premier run, ce qu'aucune approche ne peut éviter.

#### Le cas du PDF

Un PDF **n'est pas modifiable en place**. Son texte est extrait, les opérations
lui sont appliquées, puis un nouveau PDF est régénéré : la mise en page
d'origine (polices, colonnes, images) est perdue. C'est indiqué explicitement
dans la réponse. Un PDF scanné, sans texte extractible, est refusé avec un
message clair plutôt que de produire un document vide.

## 📽 Lecture des présentations

`PPTXProcessor` calque l'interface de `DOCXProcessor` (`read_pptx`,
`extract_text`, `is_supported`, résolution OneDrive partagée via
[`processors/path_resolution.py`](../processors/path_resolution.py)) et extrait
par diapositive : titre, puces **avec leur niveau**, tableaux, notes du
présentateur.

Le `.pptx` est branché partout où les autres documents le sont : glisser-déposer,
menu 📎, contexte du modèle, page Agents, Relay mobile et extension VS Code.

Les modèles `.potx` sont lus aussi : python-pptx refuse leur type de contenu,
qui est donc remplacé en mémoire par celui d'une présentation (le fichier n'est
pas touché). Ils ne sont en revanche pas modifiables par `edit_document`.

> `.ppt` (format binaire pré-2007) n'est **pas** pris en charge : python-pptx ne
> le lit pas. Convertissez-le en `.pptx` d'abord.

## 🔗 Chemins cliquables dans le chat

Un chemin de fichier ou de dossier affiché dans une réponse (« Le fichier a
été créé dans C:\Users\…\rapport.docx ») est rendu **en gras, en bleu,
souligné et cliquable** ; un clic ouvre son emplacement dans l'explorateur —
le fichier sélectionné, ou le dossier ouvert. Le bouton 📂 du volet d'aperçu
ouvre, lui, le document dans son application.

La difficulté est de savoir où un chemin s'arrête : ceux de Windows
contiennent des espaces (« OneDrive - Pierre Fabre SA ») et se fondent dans la
phrase. [`utils/path_links.py`](../utils/path_links.py) garde, depuis chaque
début de chemin, **le plus long préfixe qui existe réellement sur le disque** :

- un chemin inventé par le modèle n'est jamais rendu cliquable ;
- la ponctuation qui suit (point final, parenthèse, accent grave) est exclue ;
- les chemins d'un bloc de code ne sont pas touchés ;
- tester l'existence d'un chemin sur un lecteur réseau déconnecté peut figer
  l'interface plusieurs secondes : seuls les disques locaux sont sondés sous
  Windows (les partages `\\serveur\…` et lecteurs réseau sont ignorés), et le
  seul dossier personnel sous macOS/Linux.

Desktop uniquement : le mobile Relay ne peut pas ouvrir l'explorateur du PC.

## 📦 Dépendances

Aucune nouvelle : `python-docx`, `reportlab`, `python-pptx` et `openpyxl`
étaient déjà dans [`requirements.txt`](../requirements.txt). L'aperçu natif
des documents Office utilise `comtypes`, déjà installé sous Windows avec
`pyttsx3` (lecture vocale) ; sans lui, l'aperçu retombe sur le rendu HTML.

## 🐛 Dépannage

| Symptôme | Cause probable |
|---|---|
| « Le modèle local n'a produit aucun contenu » | Ollama arrêté → `ollama serve` |
| Le modèle écrit un fichier `.txt` au lieu d'un docx | Il a choisi `write_local_file` ; reformulez en nommant le format (« un document **Word** ») |
| « Je vais créer le document… », puis rien | Le modèle a ignoré la relance automatique (une seule par demande) : renvoyez la demande |
| Document pauvre ou hors sujet | Limite du modèle local, pas du générateur — essayez un modèle plus capable |
| Sommaire Word vide | Normal : ouvrez le document et appuyez sur **F9** |
| « Aucune opération n'a pu être appliquée » | Le texte cherché n'existe pas tel quel dans le document |
| Génération très lente (plusieurs minutes) | Inférence sur CPU. Vérifiez avec `ollama ps` : un `size_vram` à 0 signifie que le modèle tourne en RAM. Quatre appels au modèle sont nécessaires par document (voir *Coût en passes de modèle*). |

## 🧪 Tests

```bash
python -m pytest tests/test_markdown_document.py \
                 tests/test_document_generator.py \
                 tests/test_document_editor.py \
                 tests/test_document_routing.py \
                 tests/test_pptx_processor.py \
                 tests/test_document_preview.py \
                 tests/test_path_links.py \
                 tests/test_native_preview.py \
                 tests/test_edge_embed.py -v
```

Génération et lecture **réelles** (pas de mock) : chaque document est écrit puis
relu avec la bibliothèque de son format pour vérifier la structure. Les tests
d'édition vérifient systématiquement que **le fichier source est resté
intact**.
