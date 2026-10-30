# Retour de Claude Motion sur la vidéo 9.1.0

La vidéo livrée fait 1920 × 1080, à 30 images/s, et dure 46,0 s.
- **Export :** le MP4 se récupère avec le bouton Export de la page de l'animation, sur claude.ai.
- **Polices :** chargées depuis Google Fonts ; si le chargement échoue, Fraunces et Instrument Sans s'affichent à la place.

## Débuts des plans

| Plan | Début |
|---|---|
| 1. Titre | 0,0 s |
| 2. La fenêtre | 3,2 s |
| 3. Le pop Code | 6,4 s |
| 4. Ouvrir Code | 9,6 s |
| 5. Depuis le PC | 12,0 s |
| 6. Depuis VS Code | 18,6 s |
| 7. Le téléphone | 24,6 s |
| 8. Depuis le téléphone | 29,2 s |
| 9. Vers le téléphone | 37,6 s |
| 10. Fin | 41,4 s (fin à 46,0 s) |

Tous les sons tombaient aux temps demandés.

## Ce que Claude Motion a dû adapter

Ces points sont à anticiper dans le prochain prompt et dans les captures.

- **Poussée de caméra pendant le pop :** impossible, car la caméra était déjà à 100 %. À la place, la caméra recule de 4 % entre 7,6 et 9,6 s.
  - Ne pas demander de zoom au-delà de 100 %.
- **Descente de la bande (01 → 02) :** certaines lignes descendent de 84 px et non de 82, à cause des arrondis. Chaque ligne descend donc de son vrai décalage.
  - Donner les décalages mesurés, et garder le fondu final vers la vraie capture.
- **Frappe sur le PC :** en écran partagé, le texte ne faisait qu'environ 12 px de haut. Claude Motion a ajouté une poussée vers le champ de saisie (12,6 → 13,2 s), puis un retour à l'écran partagé à 14,2 s.
  - Prévoir un gros plan pour chaque frappe.
- **Après le clic dans VS Code (21,8 s) :** aucune capture ne montrait VS Code une fois sa fenêtre d'accord fermée. VS Code passe donc en retrait dès 22,0 s.
  - Capturer aussi l'état qui suit chaque fenêtre d'accord.
- **VS Code entre 29,2 et 30,9 s :** aucune capture ne le montrait entre le 2ᵉ et le 3ᵉ message. Son chat reste hors cadre jusqu'à 30,9 s.
  - Capturer chaque appareil entre deux messages.
- **Envoi depuis le téléphone (30,6 s) :** aucune capture ne montrait le message tapé sur le téléphone. L'envoi est donc un simple fondu de l'image 13 vers la 14.
  - Capturer le message tapé sur chaque appareil qui envoie.

## Retouches notées à la relecture

Ces retouches ont été proposées à l'auteur, comme facultatives.

1. **De 20,2 à 22,6 s :** la phrase « Écrivez dans VS Code. Le PC suit. » touche presque le haut de la fenêtre VS Code (environ 3 px).
   - Règle : au moins 32 px entre un titre et une fenêtre.
2. **De 33,7 à 34,4 s :** VS Code s'efface sur place et ressemble un instant à un rectangle gris vide.
   - Règle : une fenêtre qui sort glisse pendant son fondu.
