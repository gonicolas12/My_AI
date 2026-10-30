---
name: video-my-ai
description: Direction artistique validée des vidéos d'annonce de My_AI (la vidéo de la 9.1.0, que l'auteur a beaucoup aimée) et méthode pour en refaire une dans le même style. Couvre les captures réelles, le prompt pour Claude Motion, la musique originale, les effets sonores, le mixage et la miniature. À utiliser dès qu'on demande une vidéo, un teaser, une annonce animée, un prompt pour Claude Motion, une musique ou des effets sonores pour My_AI.
---

# Vidéos d'annonce de My_AI

La vidéo d'annonce de la 9.1.0 (la page Code, 46 s) est la référence : l'auteur l'a beaucoup aimée. Il veut **la même direction artistique** pour toutes les prochaines vidéos de My_AI :
- même fond, mêmes polices, mêmes cadres ;
- mêmes mouvements et transitions ;
- même style de musique et mêmes effets sonores.

On change le contenu (captures, textes, timeline), jamais le style, sauf s'il le demande.

Avant d'écrire quoi que ce soit :
- regarder `reference/planche_video_9.1.0.jpg` (16 images de la vidéo validée) ;
- lire `reference/prompt_claude_motion_9.1.0.md` (le prompt exact qui l'a produite).

## Contenu du dossier

| Fichier | Rôle |
|---|---|
| `reference/prompt_claude_motion_9.1.0.md` | Prompt exact donné à Claude Motion, modèle de tout nouveau prompt. |
| `reference/retour_claude_motion_9.1.0.md` | Ce que Claude Motion a livré et adapté, et les retouches notées à la relecture. |
| `reference/planche_video_9.1.0.jpg` | 16 images de la vidéo finale, de 1,6 s à 44,4 s. |
| `audio/music.py` | Musique originale (FluidSynth et synthèse), calée sur la timeline. |
| `audio/soundtrack.py` | Effets sonores calés sur la timeline. |
| `audio/mix.py` | Mixage final sur le MP4 exporté. |
| `captures_9.1.0/` | Tournage des vraies captures (PC, VS Code, téléphone) et kit pour claude.ai. |

## Déroulé

1. **Le sujet.**
   - Lire `docs/CHANGELOG.md` et les commits depuis la dernière version.
   - Choisir la nouveauté qui « apparaît » (le pop), puis 3 à 5 démonstrations courtes.
2. **Les captures.** Toujours de vraies captures de l'app, jamais de maquettes. Méthode : `captures_9.1.0/README.md`.
3. **Le kit pour claude.ai** (`build_kit.py`) :
   - les images, numérotées dans l'ordre du récit ;
   - `00_fiche_technique.md`, avec les zones utiles en pixels de l'image.
4. **Le prompt.** Repartir du prompt 9.1.0.
   - Garder mot pour mot « Règles sur les captures », « Direction artistique » et « Son », en ajoutant les leçons ci-dessous.
   - Réécrire « Le produit », « Le moment clé » et « Timeline ».
   - L'auteur colle le prompt et le kit dans Claude Motion sur claude.ai, puis exporte le MP4.
5. **Le son.** Claude Motion ne fait pas de son. Quand le MP4 revient :
   - vérifier les temps, en extrayant des images aux moments clés ;
   - recaler les repères si besoin ;
   - générer la musique et les effets, puis mixer (`audio/`).
6. **La miniature et le post.** Voir la dernière section.

## Direction visuelle

- **Fond** blanc cassé chaud `#F4F1EA`, avec un halo orange `#ff6b47` très léger (6 %) derrière les fenêtres.
- **Titres** en Source Serif 4, 64 à 96 px, `#141413`, interlettrage serré.
  - Souvent sur deux lignes.
  - Posés à côté de la fenêtre : texte à gauche et écran à droite, ou l'inverse.
- **Textes secondaires** en Inter, 28 à 34 px, `#5f5b53`.
- **Une seule couleur d'accent :** l'orange de My_AI `#ff6b47` (clair : `#ff8a6b`).
- **Textes à l'écran :** en français, courts, un seul par plan, en phrase complète avec un point (« Une conversation. Trois écrans. »). Pas de voix off.
- **Fenêtres :** les captures flottent dans des cadres aux coins arrondis de 14 px, avec une bordure de 1 px `#00000014` et une ombre `0 30px 80px #0000002e`.
  - PC : barre de titre `#1a1a1a` de 34 px, logo robot orange, « My_AI » en blanc 13 px, boutons Windows gris.
  - VS Code : sa propre barre.
  - Téléphone : iPhone noir, coins de 56 px, Dynamic Island, barre d'état 9:41.
- **Cadrage :** gros plans francs, quitte à couper la fenêtre au bord de l'écran.
  - Jamais au-delà de 100 % (1 px de capture par px de vidéo).
  - D'où les captures à l'échelle 2 pour le PC et VS Code, et à l'échelle 3 pour le téléphone.
- **Repères visuels :**
  - étiquettes en pastilles blanches (Inter 26 px), reliées par un trait fin ;
  - halo orange qui pulse sur ce qu'il faut regarder ;
  - trait orange arrondi qui se dessine autour des lignes de code ajoutées.
- **Ouverture :** le logo robot, « My_AI X.Y.Z » en serif, puis le slogan « Une IA personnelle, confidentielle et locale. ».
- **Carte de fin :**
  - le logo, « My_AI X.Y.Z » et le slogan en Inter gris ;
  - une ligne de détails (« Extension VS Code 1.6.1 · 12 langues · Open source (MIT) ») ;
  - « github.com/gonicolas12/My_AI » en orange.
- **Logo :** le SVG du robot est dans le prompt 9.1.0.
- **Couleurs de l'app**, visibles dans les captures :
  - fond `#0f0f0f`, panneaux `#1a1a1a` ;
  - vert « connecté » `#10b981` ;
  - bulles de l'utilisateur `#2d5aa0`.

## Mouvement et transitions

- **Courbe :** `cubic-bezier(0.2, 0, 0, 1)`, celle de l'app.
- **Rythme :**
  - entrées en fondu avec 24 px de montée ;
  - poussée de caméra de 3 à 6 % sur les plans fixes ;
  - transitions de 300 à 500 ms.
- **Sobriété :** rien de tape-à-l'œil, pas d'émojis, pas d'images de stock.
- **Changements d'écran :**
  - un écran change d'état par un fondu entre deux vraies captures ;
  - une frappe est une révélation, de gauche à droite, du texte de la capture « message tapé ».
- **Plan de fond :** un écran en retrait passe à l'échelle 0,96, à l'opacité 0,35 et à un flou de 2 px. Jamais d'état périmé au premier plan.
- **Curseur :**
  - flèche blanche à contour noir, trajectoires courbes ;
  - un clic = échelle 0,92 et petite onde ;
  - un toucher sur le téléphone = disque gris translucide de 44 px.
- **Plusieurs écrans :**
  - écrans côte à côte pour montrer deux appareils au même instant ;
  - à la fin, les trois écrans réunis qui flottent légèrement.
- **Leçons de la 9.1.0, à écrire dans le prochain prompt :**
  - au moins 32 px entre un titre et une fenêtre ;
  - une fenêtre qui sort glisse pendant son fondu, elle ne s'efface jamais sur place ;
  - prévoir un gros plan pour toute frappe, sinon le texte est illisible en écran partagé.
- **Signature, le « pop »** d'un nouvel élément d'interface (6,4 → 9,6 s dans la 9.1.0) :
  1. la zone du dessous glisse vers le bas, en 420 ms, avec un rebond de 4 px ;
  2. l'élément apparaît en fondu, à l'échelle 0,6 → 1,08 → 1, en 450 ms, avec un ressort amorti ;
  3. en même temps, une gerbe de 14 gouttes orange (`#ff6b47`, quelques-unes en `#ff8a6b`) part de son icône, avec un anneau orange (rayon 0 → 70 px, 450 ms) ;
  4. une éventuelle pastille fait un petit pop (0 → 1,2 → 1, 200 ms) ;
  5. un fondu de 120 ms ramène sur la vraie capture « après ».

  Mesurer les coordonnées au pixel près avec `captures_9.1.0/measure_pop.cjs` : les lignes ne bougent pas toutes du même nombre de pixels.

## Structure et rythme

- **Format :** 40 à 50 s, 1920 × 1080, 30 images/s.
- **Enchaînement :**
  1. le titre (environ 3 s) ;
  2. l'app « avant » (environ 3 s) ;
  3. le pop, vers 6 à 7 s ;
  4. des démonstrations d'une idée chacune, dans les deux sens entre les appareils ;
  5. le plan d'ensemble ;
  6. la carte de fin (environ 3 s).
- **Timeline :** le prompt la donne au dixième de seconde, avec les temps des sons.
- **Retour demandé :** on demande à Claude Motion la liste des débuts de plans et ce qu'il a dû adapter.

## Musique (style validé)

`python3 audio/music.py SORTIE/` → `musique.wav` (46 s, 48 kHz). C'est une musique originale composée ici, sans droits à gérer.

- **Style :** pop électronique douce et lumineuse, comme une keynote de produit. Do majeur, 105,9 BPM.
- **Calage :** le tempo est choisi pour que les moments clés tombent sur le premier temps d'une mesure.
  - Dans la 9.1.0, une mesure dure 2,265625 s.
  - La mesure 3 tombe sur le pop (6,75 s), la mesure 19 sur la carte de fin (43,0 s).
  - Pour une autre timeline : ajuster `BAR`, `OFFSET`, `CHORDS` et les mesures des sections.
- **Forme :**
  - intro planante (Am9 → Fmaj9 → Gsus4 qui se résout en G) : la nappe s'ouvre, le piano égrène les accords, une montée de bruit filtré mène au pop ;
  - impact sur le pop, puis le groove C – G – Am – F :
    - piano électrique en croches et basse ronde ;
    - grosse caisse sur 1 et 3, claps sur 2 et 4, charleston en croches ;
    - mélodie au vibraphone ;
  - respiration sans grosse caisse quand un nouvel appareil entre (le téléphone dans la 9.1.0) ;
  - les cordes montent, puis F – G sans batterie, avec une montée ;
  - Cadd9 final sur la carte de fin, qui s'éteint.
- **Instruments :**
  - sons General MIDI de FluidR3_GM : piano électrique (programme 4), nappe chaude (89), cordes (48), vibraphone (11) ;
  - batterie, basse, montées et impacts synthétisés.
- **Niveaux RMS visés :**

  | Piste | Niveau |
  |---|---|
  | Nappe | −27 dB |
  | Piano (passe-bas à 4,2 kHz) | −30 dB |
  | Cordes, vibraphone | −29 dB |
  | Basse | −25 dB |
  | Batterie | −23 dB |
  | Charleston | −34 dB |
  | Effets (montées, impacts) | −30 dB |

  Avec une réverbe à convolution et un léger pompage sur la grosse caisse.
- **Retours de l'auteur, à respecter :**
  - il veut de la musique, pas seulement des effets ;
  - le piano reste doux et en retrait, sans attaque brusque : vélocités de 36 à 52, et un piano électrique plutôt qu'un piano à queue ;
  - **aucune « fausse note » :** jamais deux notes à un demi-ton (ou à une neuvième mineure) en même temps.
    - Le script le vérifie (`check_clashes`) et s'arrête s'il en trouve.
    - Attention aux accords suspendus : la résolution (do → si) se joue une note après l'autre, jamais ensemble.
- **Dépendances :** `apt-get install fluidsynth fluid-soundfont-gm`, puis `pip install mido numpy scipy`.

## Effets sonores (style validé)

`python3 audio/soundtrack.py SORTIE/` → `bande_son_sfx.wav` et `reperes_sons.txt`. Ce sont des sons synthétisés, courts et discrets :

- **pop :** un « bloop » qui glisse de 1150 à 300 Hz (0,16 s), suivi de 6 gouttelettes aiguës (2,3 à 3,6 kHz) ;
- **clic :** sec (1,9 kHz et un peu de bruit, 45 ms), pour les clics et les touchers ;
- **frappe au clavier :** petits bruits secs avec un léger choc grave, toutes les 65 à 130 ms ;
- **envoi :** un souffle doux (bruit lissé, 0,28 s) ;
- **succès :** deux notes, la5 puis mi6 ;
- **fin :** accord do-mi-sol-do égrené, 60 ms entre les notes.

Les temps (`CUES`) reprennent la timeline du prompt.

## Mixage final

`python3 audio/mix.py VIDEO.mp4 musique.wav bande_son_sfx.wav SORTIE.mp4`

- Musique à −3 dB, effets à −4 dB.
- Gain jusqu'à −15 LUFS intégrés, puis limiteur (0,82).
- Audio en AAC 192 kb/s, image copiée sans réencodage.
- Le script affiche la sonie et la crête finales : environ −15 LUFS, crête vraie vers −1,5 dB.

## Miniature et publication

- **Miniature :** la première image est presque vide (fond crème). En prévoir une : le plan des trois écrans réunis, vers 42,2 s dans la 9.1.0.
- **Lecture sans le son :** LinkedIn démarre la vidéo muette, donc le texte à l'écran doit porter seul le message.
- **Post LinkedIn :** skill `li-post` du plugin `linkedin-agent` (`/plugin marketplace add Jakeschincariol/linkedin-agent-skill`).
- **Quand publier :** du mardi au jeudi, vers 8 h 30 (heure de Paris).
- **Premier commentaire :** le poster soi-même dès la publication, avec les liens ; LinkedIn ne permet pas de le programmer.
