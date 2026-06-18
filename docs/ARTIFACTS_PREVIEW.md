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

**Décision : `tkinterweb` embarqué + fallback navigateur systématique.**

| Option | Avantages | Inconvénients |
|---|---|---|
| **tkinterweb** *(retenu)* | Volet réellement **embarqué** dans le GUI, léger, pur Python, pas de fenêtre séparée | **CSS limité** (pas de flexbox/grid complet, JS quasi inexistant) |
| pywebview (WebView2/Edge) | Fidélité CSS/JS **totale** | Ouvre une **fenêtre séparée** (pas un vrai volet « à côté du chat »), dépendance plus lourde |
| Navigateur uniquement | Le plus simple, 100% fiable, fidélité totale | Pas de panneau intégré |

### Compromis assumé

`tkinterweb` rend le HTML/CSS **simple** correctement (titres, paragraphes,
tableaux, couleurs, images, SVG basique) mais ne gère pas la mise en page
moderne (flexbox/grid) ni le JavaScript. Pour ces cas, le bouton
**« 🌐 Ouvrir dans le navigateur »** ouvre le fichier généré
(`outputs/artifacts/artifact_*.html`) dans le navigateur par défaut, avec une
**fidélité totale**.

### Dégradation propre

`tkinterweb` est une **dépendance optionnelle**. S'il est absent, le volet
affiche un message d'aide (`pip install tkinterweb`) + le **code source** de
l'artifact, et le bouton « Ouvrir dans le navigateur » reste pleinement
fonctionnel. Le rendu embarqué n'est donc jamais bloquant.

```bash
pip install tkinterweb   # active le rendu embarqué (sinon : fallback navigateur)
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

- `tkinterweb` : pas de flexbox/grid/JS → utiliser le fallback navigateur.
- Les ressources externes (CDN, polices distantes) ne sont volontairement pas
  chargées (confidentialité) ; un artifact qui en dépend s'affichera dégradé.
