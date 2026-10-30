#!/usr/bin/env python3
"""Kit de la vidéo My_AI 9.1.0 : images choisies (renommées dans l'ordre du récit),
fiche technique avec les coordonnées utiles aux zooms et à l'animation « pop »."""

import json
import shutil
import sys
from pathlib import Path

from PIL import Image

S = Path(sys.argv[1])
RAW = S / "kit" / "raw"
UP = S / "kit" / "pour_claude_web"
shutil.rmtree(UP, ignore_errors=True)
UP.mkdir(parents=True)
meta = json.loads((RAW / "meta.json").read_text(encoding="utf-8"))
BOXES = meta["boxes"]

# (nom dans le kit, capture, écran, échelle, ce qu'on voit)
IMAGES = [
    ("01_pc_avant_sans_bouton_code", "D01_pc_barre_sans_code", "PC", 2,
     "Fenêtre My_AI, barre latérale SANS le bouton Code (état « avant »)."),
    ("02_pc_apres_avec_bouton_code", "D02_pc_barre_avec_code", "PC", 2,
     "Même écran AVEC le bouton Code sous « Nouvelle conversation » (pastille verte : VS Code connecté). État « après » du pop."),
    ("03_pc_page_code", "D03_pc_page_code_vide", "PC", 2,
     "Clic sur Code : la page Code s'ouvre (grande icône </>, titre « Code », champ « Demandez à My_AI d'agir dans VS Code… », dossier bibliotheque-api)."),
    ("04_vscode_pret", "V00_vscode_pret", "VS Code", 2,
     "VS Code avec le projet bibliotheque-api, src/app.py ouvert, le chat My_AI à droite, connecté et vide (avant le premier message)."),
    ("05_pc_message_tape", "D04_pc_message_tape", "PC", 2,
     "Message tapé sur le PC : « Ajoute une route GET /livres/{id} qui renvoie une 404 si le livre n'existe pas »."),
    ("06_pc_accord_demande", "D05_pc_approbation", "PC", 2,
     "Message envoyé : My_AI a lu src/app.py et demande l'accord avant de le modifier (bouton orange « Autoriser une fois »)."),
    ("07_vscode_meme_accord", "V01_vscode_message_du_pc", "VS Code", 2,
     "AU MÊME INSTANT dans VS Code : le message marqué « Depuis My_AI sur le PC », la même demande d'accord dans le chat My_AI (à droite)."),
    ("08_vscode_route_ajoutee", "V03_vscode_fichier_modifie_final", "VS Code", 2,
     "Après « Autoriser une fois » cliqué sur le PC : VS Code a écrit la route dans src/app.py (lignes 33 à 37, marge verte), réponse finale dans le chat."),
    ("09_vscode_message_tape", "V04_vscode_message_tape", "VS Code", 2,
     "Message tapé dans VS Code : « Ajoute un test pour cette 404 »."),
    ("10_vscode_fenetre_accord", "V05_vscode_dialogue_approbation", "VS Code", 2,
     "Message parti de VS Code : c'est VS Code qui demande l'accord, dans sa propre fenêtre (« Autoriser une fois » en bleu)."),
    ("11_pc_message_de_vscode", "D10_pc_reponse_vscode_finale", "PC", 2,
     "Sur le PC : le message venu de VS Code (petit badge « VS Code » au-dessus) et sa réponse : test ajouté."),
    ("12_tel_barre_onglets", "M01_tel_chat_barre_onglets", "Téléphone", 3,
     "Téléphone (Relay) : nouvelle barre d'onglets : </> orange tout à gauche, Chat et Agents centrés avec les icônes du PC, corbeille orange tout à droite."),
    ("13_tel_vue_code", "M02b_tel_vue_code_haut", "Téléphone", 3,
     "Toucher </> : la vue Code s'ouvre (</> souligné), avec toute la conversation : ici le message envoyé du PC (badge « PC ») et sa réponse."),
    ("14_tel_accord", "M04_tel_approbation", "Téléphone", 3,
     "« Lance les tests » envoyé du téléphone : My_AI demande l'accord pour lancer python -m pytest -q, sur le téléphone. Corbeille grisée pendant l'écriture."),
    ("15_vscode_message_du_tel", "V07_vscode_message_du_tel", "VS Code", 2,
     "AU MÊME INSTANT dans VS Code : « Depuis le téléphone », même demande d'accord pour la commande."),
    ("16_tel_reponse_en_cours", "M05_tel_reponse_en_cours", "Téléphone", 3,
     "Accord donné sur le téléphone : la commande tourne dans VS Code, la réponse s'écrit sur le téléphone (curseur orange), corbeille toujours grisée."),
    ("17_tel_reponse_finale", "M06_tel_reponse_finale", "Téléphone", 3,
     "« Les 4 tests passent… » : réponse finie, la corbeille redevient orange."),
    ("18_tel_message_de_vscode", "M08_tel_message_de_vscode_final", "Téléphone", 3,
     "Sur le téléphone : le message tapé dans VS Code (badge « VS Code »), « Écris le message de commit », et sa réponse."),
]

LABELS = {
    "barre_laterale": "barre latérale", "bouton_code": "bouton Code", "zone_de_saisie": "zone de saisie",
    "carte_accord": "carte d'accord", "bouton_autoriser": "bouton « Autoriser une fois »",
    "message_utilisateur": "bulle du message", "chat_my_ai": "panneau du chat My_AI",
    "editeur": "éditeur", "explorateur": "explorateur", "accord_dans_vscode": "demande d'accord",
    "message_du_pc": "message du PC", "nouvelle_route": "lignes ajoutées (nouvelle route)",
    "saisie_vscode": "champ de saisie", "dialogue": "fenêtre d'accord de VS Code",
    "message_de_vscode": "message venu de VS Code", "attente_vscode": "« Approbation demandée dans VS Code »",
    "nouveau_test": "lignes ajoutées (nouveau test)", "barre_onglets": "barre d'onglets",
    "onglet_chat": "onglet Chat", "onglet_agents": "onglet Agents", "corbeille": "corbeille",
    "accord": "carte d'accord",
}


def px(box, scale):
    return f"x {box['x'] * scale}, y {box['y'] * scale}, l {box['w'] * scale}, h {box['h'] * scale}"


rows = []
for name, raw, screen, scale, what in IMAGES:
    src = RAW / f"{raw}.png"
    dst = UP / f"{name}.png"
    shutil.copy2(src, dst)
    w, h = Image.open(dst).size
    regions = BOXES.get(raw) or {}
    zones = "; ".join(f"{LABELS.get(k, k)} : {px(v, scale)}" for k, v in regions.items() if v)
    rows.append((name, screen, f"{w} × {h}", what, zones))

spec = []
spec.append("# Fiche technique — vidéo My_AI 9.1.0 (page Code)\n")
spec.append("Captures réelles de My_AI 9.1.0 : fenêtre du PC, extension VS Code 1.6.1 dans un vrai "
            "VS Code, page du téléphone servie par le vrai Relay. Une seule conversation, partagée "
            "par les trois écrans ; les fichiers ont vraiment été modifiés et les tests vraiment lancés.\n")
spec.append("Coordonnées en pixels DE L'IMAGE (origine en haut à gauche). PC et VS Code : captures "
            "à l'échelle 2 (2880 × 1800 pour une fenêtre de 1440 × 900). Téléphone : échelle 3 "
            "(1170 × 2532 pour un écran de 390 × 844, sans barre d'état iOS).\n")
spec.append("## Identité visuelle\n")
spec.append("- Fond principal `#0f0f0f`, panneaux `#1a1a1a`, surfaces `#2d2d2d`, bordures `#374151`.")
spec.append("- **Orange My_AI `#ff6b47`** (survol `#ff5730`, clair `#ff8a6b`) : c'est la couleur des gouttes.")
spec.append("- Vert « connecté » `#10b981`, bulles de l'utilisateur bleu `#2d5aa0`.")
spec.append("- Texte `#ffffff`, secondaire `#9ca3af`, discret `#6b7280`.")
spec.append("- Polices : **Inter** (interface), **JetBrains Mono** (code). Logo : le robot orange.\n")
spec.append("## Images (dans l'ordre du récit)\n")
spec.append("| Fichier | Écran | Taille | Ce qu'on voit | Zones utiles (px de l'image) |")
spec.append("|---|---|---|---|---|")
for name, screen, size, what, zones in rows:
    spec.append(f"| `{name}.png` | {screen} | {size} | {what} | {zones or '—'} |")
spec.append("")
spec.append("Paires « même instant » (à montrer côte à côte, synchronisées) : **05 puis 06 ↔ 04 puis 07** (PC → VS Code), "
            "**09 puis 10 ↔ 11** (VS Code → PC), **14 ↔ 15** (téléphone → VS Code), **18** (VS Code → téléphone).\n")
spec.append("## Animation « pop » du bouton Code (images 01 → 02)\n")
spec.append("Les deux images sont identiques, au bouton Code près. Dans 02, la ligne Code occupe "
            "**x 16 → 512, y 204 → 276** (496 × 72 px, coins arrondis 20 px, fond identique à la barre "
            "`#1a1a1a`). Icône `</>` orange centrée en **(52, 238)**, texte « Code » blanc, pastille verte "
            "de 12 px centrée en **(486, 238)**.\n")
spec.append("- Dans 01, tout ce qui est sous « Nouvelle conversation » (champ de recherche, libellé "
            "CONVERSATIONS, liste) occupe la bande **x 0 → 528, y 204 → 1538**. Pour l'animation, "
            "cette bande **descend de 82 px** (y 204 → 286), et la ligne Code apparaît à sa place.")
spec.append("- Ce qui est sous y = 1538 (« Dossiers du projet », « Historique », barre d'icônes du bas) "
            "**ne bouge pas** : la bande qui descend passe dessous (rogner la bande à y = 1538).")
spec.append("- Le reste de l'écran (zone de droite, à partir de x = 528) ne change pas.")
spec.append("- Fin de l'animation : fondu de 120 ms vers l'image 02 pour retomber pile sur le vrai écran.")
spec.append("- La ligne Code peut être découpée dans l'image 02 (x 16, y 204, 496 × 72).\n")
spec.append("## Nouveautés du téléphone à mettre en avant\n")
spec.append("- `</>` orange tout à gauche de la barre d'onglets : ouvre la vue Code (souligné quand elle est ouverte).")
spec.append("- Chat et Agents centrés, avec les icônes de la fenêtre du PC (plus d'émojis).")
spec.append("- Corbeille orange tout à droite (remplace le bouton « Effacer ») ; **grisée tant qu'une réponse "
            "s'écrit** (images 14 et 16), de nouveau orange à la fin (17).")
spec.append("- Une réponse = une bulle : le texte, puis les actions de My_AI dedans (Lecture, Modification, "
            "Commande…), l'accord en dessous ; blocs de code avec bouton Copier. Même rendu dans VS Code.\n")
spec.append("## Sons fournis à part (dossier `sons/`)\n")
spec.append("- `pop.wav` (0,22 s) : le pop du bouton Code.")
spec.append("- `pop_gouttes.wav` (0,62 s) : pop + gouttelettes aiguës, pour le pop avec les gouttes orange.")
spec.append("- `clic.wav` : clics et touchers (« Autoriser une fois », `</>`).")
spec.append("- `envoi.wav` : message envoyé.")
(UP / "00_fiche_technique.md").write_text("\n".join(spec) + "\n", encoding="utf-8")
print("images :", len(rows), "→", UP)
