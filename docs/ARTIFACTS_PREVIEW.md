# Panneau « Artifacts » — Aperçu live HTML/CSS/SVG

Affiche un rendu en direct du HTML/CSS/SVG généré par l'IA, à côté du chat,
façon *Claude Artifacts*. Disponible sur le **GUI desktop** (CustomTkinter) et
sur l'**interface mobile Relay**.

> 100% local — aucun appel réseau. Cohérent avec la promesse de confidentialité
> du projet.

## Vue d'ensemble

| Élément | Rôle |
|---|---|
| [`interfaces/artifacts.py`](../interfaces/artifacts.py) | Détection + préparation du document, **partagé** desktop/serveur |
| [`interfaces/gui/artifacts_panel.py`](../interfaces/gui/artifacts_panel.py) | Volet de preview desktop (`ArtifactsPanelMixin`) |
| [`interfaces/gui/message_bubbles.py`](../interfaces/gui/message_bubbles.py) | Bouton « 🔍 Aperçu » sous les réponses IA |
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

## Rendu desktop — choix du moteur

**Décision : Edge `--app` embarqué (rendu Chromium EXACT), avec repli
tkinterweb puis code source.**

Le moteur est sélectionné dans cet ordre par
[`artifacts_panel.py`](../interfaces/gui/artifacts_panel.py) :

| Priorité | Moteur | Rendu | Notes |
|---|---|---|---|
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
et le processus Edge est fermé à la fermeture du volet ou de l'application.

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

Aucune route serveur n'est nécessaire : tout est rendu côté client à partir du
texte déjà reçu, ce qui évite tout état côté serveur et reste 100% local.

## Limitations connues

- **Edge embarqué** : Windows uniquement ; ré-parentage natif (`SetParent`)
  pouvant présenter de légers artefacts dans des cas limites.
- **tkinterweb** (repli) : pas de flexbox/grid/JS → utiliser le bouton 🌐.
- Côté **desktop**, le rendu exact (Edge) charge les ressources externes
  référencées par l'artifact (CDN, polices). Côté **mobile**, l'iframe
  `srcdoc` ne charge rien d'extérieur par défaut au-delà de ce que le HTML
  demande explicitement.
