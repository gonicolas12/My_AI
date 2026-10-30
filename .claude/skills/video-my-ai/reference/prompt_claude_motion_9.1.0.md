Tu es motion designer. Réalise avec Claude Motion la vidéo d'annonce de My_AI 9.1.0, à partir des 18 captures jointes (01 à 18) et de la fiche technique jointe (00_fiche_technique.md, qui donne les coordonnées exactes).

## Le produit

My_AI est mon assistant IA personnel, confidentiel et local, open source (licence MIT) : le modèle tourne sur le PC avec Ollama. La 9.1.0 apporte **Code** : la conversation de l'extension VS Code de My_AI est partagée par trois écrans, VS Code, la fenêtre de My_AI sur le PC (nouveau bouton Code dans la barre latérale, nouvelle page Code) et le téléphone (vue Code du Relay, bouton </>). Un message tapé sur l'un des trois fait agir My_AI dans le projet ouvert dans VS Code, et la réponse s'affiche en direct sur les trois. Avant d'écrire un fichier ou de lancer une commande, My_AI demande l'accord : le premier bouton touché compte, sur le PC, dans VS Code ou sur le téléphone.

## La vidéo

- Pour LinkedIn, public de développeurs et d'étudiants francophones.
- 46 secondes, 1920 × 1080, 30 images/s, export MP4.
- Pas de voix off. Textes à l'écran en français, courts, un seul par plan.
- Ton : annonce de produit sobre et haut de gamme, dans l'esprit des vidéos de lancement d'OpenAI et d'Anthropic.

## Règles sur les captures (important)

- Ce sont de vraies captures de l'application. Recadrer, zoomer, fondre, découper, mettre dans un cadre : oui. Redessiner l'interface, modifier un texte des captures ou inventer un écran : non.
- PC et VS Code : 2880 × 1800 (échelle 2). Téléphone : 1170 × 2532 (échelle 3). Toutes les coordonnées sont en pixels de l'image, origine en haut à gauche.
- Jamais au-delà de 100 % : 1 pixel d'image au plus par pixel de vidéo. On peut donc zoomer jusqu'à une zone de 1920 px de large dans les captures PC et VS Code.

## Direction artistique

- **Fond** : blanc cassé chaud `#F4F1EA`, avec un halo orange `#ff6b47` très léger (6 % d'opacité) derrière les fenêtres.
- **Textes** : titres en serif élégante, Source Serif 4 (Google Fonts), 64 à 96 px, `#141413`, interlettrage serré. Textes secondaires en Inter, 28 à 34 px, `#5f5b53`. Une seule couleur d'accent : l'orange de My_AI `#ff6b47`.
- **Fenêtres** : les captures flottent dans des fenêtres aux coins arrondis 14 px, bordure 1 px `#00000014`, grande ombre douce (`0 30px 80px #0000002e`).
  - PC : barre de titre sombre `#1a1a1a` de 34 px, avec le logo robot orange, « My_AI » en blanc 13 px et les trois boutons de fenêtre Windows (–, □, ×) gris à droite.
  - VS Code : pas de barre ajoutée, la capture a déjà la sienne.
  - Téléphone : maquette d'iPhone noire, coins 56 px, Dynamic Island, barre d'état blanche (9:41, réseau, Wi-Fi, batterie) sur fond `#1a1a1a` au-dessus de la capture.
- **Mouvement** : lent et fluide, courbe `cubic-bezier(0.2, 0, 0, 1)` (celle de l'application), entrées en fondu avec 24 px de montée, poussée de caméra de 3 à 6 % pendant les plans fixes, transitions de 300 à 500 ms. Aucun effet tape-à-l'œil, pas d'émojis, pas d'images de stock.
- **Curseur** : flèche blanche à contour noir (style Windows), trajectoires courbes et naturelles. Un clic = léger enfoncement (échelle 0,92) et petite onde. Sur le téléphone, un toucher = disque gris translucide de 44 px qui s'efface.
- **Plan de fond** : quand une fenêtre passe en retrait, elle recule (échelle 0,96), s'assombrit (opacité 0,35) et se floute légèrement (2 px). Elle ne doit jamais rester au premier plan avec un état périmé.
- **Logo** (robot My_AI) :

```svg
<svg viewBox="0 0 24 24" fill="#ff6b47" xmlns="http://www.w3.org/2000/svg"><circle cx="7" cy="1.5" r="1"/><rect x="6.6" y="2.4" width="0.8" height="2.8" rx="0.4"/><circle cx="17" cy="1.5" r="1"/><rect x="16.6" y="2.4" width="0.8" height="2.8" rx="0.4"/><path fill-rule="evenodd" d="M5 4.5H19A4 4 0 0 1 23 8.5V18A4 4 0 0 1 19 22H5A4 4 0 0 1 1 18V8.5A4 4 0 0 1 5 4.5ZM6.25 9.25H8.75A1.25 1.25 0 0 1 10 10.5V12A1.25 1.25 0 0 1 8.75 13.25H6.25A1.25 1.25 0 0 1 5 12V10.5A1.25 1.25 0 0 1 6.25 9.25ZM15.25 9.25H17.75A1.25 1.25 0 0 1 19 10.5V12A1.25 1.25 0 0 1 17.75 13.25H15.25A1.25 1.25 0 0 1 14 12V10.5A1.25 1.25 0 0 1 15.25 9.25ZM9 15.75H15A1 1 0 0 1 15 17.75H9A1 1 0 0 1 9 15.75Z"/></svg>
```

## Le moment clé : le « pop » du bouton Code (6,4 s → 9,6 s)

Base : image 01 (sans le bouton Code), caméra déjà rapprochée au maximum permis (100 %) sur le haut de la barre latérale, qui occupe alors environ 28 % de la largeur de l'écran.

1. **6,60 s** : la bande de la barre latérale sous « Nouvelle conversation » (x 0 → 528, y 204 → 1538) descend de 82 px en 420 ms, avec un léger rebond de 4 px. Elle passe sous la partie basse (y ≥ 1538 : « Dossiers du projet », « Historique », barre d'icônes), qui ne bouge pas. Le reste de l'écran ne bouge pas.
2. **6,75 s** : la ligne Code, découpée dans l'image 02 (x 16, y 204, 496 × 72), apparaît dans l'espace libéré avec un pop : échelle 0,6 → 1,08 → 1,0 et opacité 0 → 1, en 450 ms, ressort amorti, centré sur l'icône `</>` (52, 238).
3. **6,75 s**, en même temps : une gerbe de 14 gouttes orange part de l'icône `</>`.
   - Forme : cercle étiré en pointe, de 8 à 18 px de l'image.
   - Couleur : `#ff6b47`, quelques-unes en `#ff8a6b`.
   - Trajectoire : projetées en éventail vers le haut et la droite (angles −160° à −20°), vitesses variées, gravité, légère rotation dans le sens du mouvement. Trois ou quatre gouttes rebondissent une fois sur la ligne.
   - Disparition : toutes s'estompent en 600 à 800 ms.
   - Avec elles, un anneau orange s'élargit : rayon 0 → 70 px, épaisseur 3 px, opacité 0,6 → 0, en 450 ms.
   - Les gouttes restent dans la fenêtre du PC.
4. **7,10 s** : la pastille verte (centre 486, 238 ; 12 px) apparaît avec un petit pop (0 → 1,2 → 1, 200 ms).
5. **7,40 s** : fondu de 120 ms vers l'image 02 entière, pour retomber pile sur le vrai écran.

## Timeline (à respecter à 0,1 s près : une bande-son d'effets est calée dessus)

1. **0,0 → 3,2 s, titre.** Logo robot à 0,3 s, « My_AI 9.1.0 » à 0,8 s, puis « Une IA personnelle, confidentielle et locale. » à 1,6 s. Fondu sortant à 2,8 s.
2. **3,2 → 6,4 s, la fenêtre.** Image 01 : la fenêtre du PC monte et apparaît (600 ms), puis la caméra se rapproche lentement de la barre latérale. Texte à 4,4 s : « Nouveau dans la barre latérale. »
3. **6,4 → 9,6 s, le pop.** Images 01 → 02, animation ci-dessus. Texte à 7,6 s : « Code » en grand, puis « La conversation de VS Code, sur le PC et sur votre téléphone. »
4. **9,6 → 12,0 s, ouvrir Code.** Le curseur va sur la ligne Code (9,6 → 10,3 s), clic à 10,4 s, fondu vers l'image 03 à 10,5 s (300 ms), léger zoom sur le centre de la page Code. Pas de texte.
5. **12,0 → 18,6 s, du PC vers VS Code.**
   - 12,0 → 12,6 s : écran partagé, le PC à gauche (03), VS Code à droite (04), un peu en retrait.
   - 12,8 → 14,0 s : le message apparaît dans la zone de saisie du PC comme s'il était tapé : révélation de gauche à droite du texte de l'image 05, dans sa zone de saisie (x 984, y 924, 1440 × 288).
   - 14,2 s : envoi, le PC passe à l'image 06.
   - 14,5 s : VS Code passe à l'image 07, le même message y arrive. Un halo orange discret pulse sur les deux demandes d'accord (06 : x 1078, y 574, 1298 × 240 ; 07 : x 2176, y 662, 622 × 378). Texte : « Demandez depuis le PC. VS Code agit. »
   - 15,6 → 16,3 s : le curseur va sur « Autoriser une fois » du PC (06 : x 1104, y 652, 268 × 64), clic à 16,4 s.
   - 16,6 s : VS Code passe à l'image 08 et vient au premier plan, le PC passe en retrait. La caméra zoome sur les lignes ajoutées dans l'éditeur (x 624, y 1014, 1362 × 190), entourées d'un trait orange arrondi qui se dessine.
6. **18,6 → 24,6 s, de VS Code vers le PC.**
   - 18,6 s : le PC sort par la gauche, VS Code se centre en grand (09).
   - 18,8 → 19,8 s : le message apparaît dans le champ du chat My_AI comme s'il était tapé (révélation du texte de 09, x 2120, y 1642, 628 × 68).
   - 20,0 s : envoi, VS Code passe à l'image 10 (fenêtre d'accord de VS Code). Texte à 20,2 s : « Écrivez dans VS Code. Le PC suit. »
   - 21,2 → 21,7 s : le curseur va sur le bouton bleu « Autoriser une fois » de la fenêtre d'accord (fenêtre : x 718, y 768, 1446 × 264 ; bouton tout à droite), clic à 21,8 s.
   - 22,2 s : VS Code passe en retrait, le PC revient par la gauche au premier plan avec l'image 11. Zoom doux sur le message venu de VS Code (petit badge « VS Code ») et sa réponse.
7. **24,6 → 29,2 s, le téléphone.**
   - 24,6 s : les fenêtres sortent, la maquette du téléphone entre par la droite avec l'image 12. Texte à 24,9 s : « Et sur votre téléphone. »
   - 25,6 s : zoom sur la barre d'onglets (x 0, y 180, 1170 × 153). Trois étiquettes apparaissent l'une après l'autre (26,0 / 26,5 / 27,0 s), petites pastilles blanches en Inter 26 px reliées par un trait fin :
     - « </> : la conversation Code », sur le bouton de gauche (x 12, y 180, 132 × 150) ;
     - « Chat et Agents, avec les icônes du PC » ;
     - « Corbeille : vide la page ouverte », sur la corbeille (x 1026, y 180, 132 × 150).
   - 27,9 s : toucher sur `</>`.
   - 28,1 s : fondu vers l'image 13 (vue Code avec le message du PC).
8. **29,2 → 37,6 s, du téléphone vers VS Code.**
   - 29,2 s : le téléphone au centre-gauche, VS Code entre à droite, un peu en retrait.
   - 30,6 s : envoi, le téléphone passe à l'image 14.
   - 30,9 s : VS Code passe à l'image 15 (« Depuis le téléphone »). Halo orange qui pulse sur les deux demandes d'accord (14 : x 303, y 1623, 741 × 597 ; 15 : x 2176, y 1214, 622 × 338). Texte : « Validez depuis votre téléphone. »
   - 31,8 s : étiquette sur la corbeille grisée (x 1026, y 180, 132 × 150) : « Grisée tant que la réponse s'écrit ».
   - 33,4 s : toucher sur « Autoriser une fois » du téléphone (x 339, y 1797, 411 × 99).
   - 33,7 s : le téléphone passe à l'image 16, VS Code passe en retrait puis sort. Texte à 33,9 s : « La commande tourne dans VS Code. »
   - 35,4 s : le téléphone passe à l'image 17 (« Les 4 tests passent ») ; petite pulsation orange sur la corbeille redevenue active.
9. **37,6 → 41,4 s, de VS Code vers le téléphone.** Le téléphone passe à l'image 18 : le message parti de VS Code et sa réponse. Texte à 38,2 s : « Une conversation. Trois écrans. »
10. **41,4 → 46,0 s, fin.**
    - 41,4 → 43,0 s : les trois écrans réunis (PC avec 11, VS Code avec 08, téléphone devant avec 18), en léger flottement.
    - 43,0 s : ils s'effacent, carte de fin : logo, « My_AI 9.1.0 », « Une IA personnelle, confidentielle et locale. », puis en petit « Extension VS Code 1.6.1 · 12 langues · Open source (MIT) » et « github.com/gonicolas12/My_AI » en orange.
    - 45,6 → 46,0 s : fondu vers le fond.

## Son

N'ajoute pas de son. Je pose moi-même au montage une bande-son d'effets calée sur cette timeline :
- pop et gouttes à 6,75 s ;
- clics à 10,4 / 16,4 / 21,8 / 27,9 / 33,4 s ;
- frappe au clavier de 12,8 à 14,0 s et de 18,8 à 19,8 s ;
- envois à 14,2 / 20,0 / 30,6 / 37,8 s ;
- succès à 35,4 s ;
- carte de fin à 43,0 s.

Garde donc exactement ces temps.

## Ce que j'attends

1. La vidéo complète, puis l'export MP4 1920 × 1080.
2. La liste des temps réels de début de chaque plan, pour que je vérifie la synchro du son.
3. Si un point de la timeline est impossible, dis-le et propose l'alternative la plus proche plutôt que de l'ignorer.

Si Claude Motion n'est pas disponible sur mon compte : fais la même vidéo en artifact HTML autonome. Scène fixe de 1920 × 1080 mise à l'échelle de la fenêtre, lecture automatique, bouton Rejouer, même timeline, captures jointes chargées depuis les fichiers envoyés.
