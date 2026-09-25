"""
Résolution de chemins OneDrive

Partagé par les processeurs de documents : un fichier référencé par son seul
nom, ou par un chemin qui n'existe plus tel quel (dossier OneDrive renommé,
fichier déplacé), est recherché dans les racines OneDrive de l'utilisateur.
"""

import glob
import os
from pathlib import Path
from typing import List


def onedrive_roots() -> List[str]:
    """
    Liste les racines OneDrive présentes dans le dossier personnel.

    OneDrive se monte sous ``~`` sur Windows comme sur macOS ; coder
    ``C:/Users/`` + ``%USERNAME%`` serait inopérant hors Windows (macOS expose
    USER, pas USERNAME).

    Returns:
        Les chemins candidats, dédoublonnés, dans l'ordre de préférence.
    """
    home = Path.home()
    roots = [
        str(home / "OneDrive"),
        str(home / "OneDrive - Personnel"),
        str(home / "OneDrive - Professionnel"),
    ]

    # Racines Business/Enterprise détectées automatiquement
    for pattern in ("OneDrive - *", "OneDrive*"):
        roots.extend(glob.glob(str(home / pattern)))

    return list(dict.fromkeys(roots))


def resolve_onedrive_path(file_path: str) -> str:
    """
    Résout un chemin potentiellement OneDrive pour le rendre accessible.

    Args:
        file_path: Chemin du fichier (peut être OneDrive)

    Returns:
        Le chemin résolu, ou le chemin d'origine si rien n'a été trouvé.
    """
    # Si le fichier existe déjà, le retourner tel quel
    if os.path.exists(file_path):
        return file_path

    file_name = os.path.basename(file_path)

    # Recherche récursive dans toutes les racines OneDrive
    for root_path in onedrive_roots():
        if not os.path.exists(root_path):
            continue
        for root, _dirs, files in os.walk(root_path):
            if file_name in files:
                found = os.path.join(root, file_name)
                print(f"✅ Fichier trouvé dans OneDrive: {found}")
                return found

    # Dernier essai : le Bureau synchronisé
    desktop_onedrive = os.path.expanduser("~/OneDrive/Desktop")
    if os.path.exists(desktop_onedrive):
        desktop_file = os.path.join(desktop_onedrive, file_name)
        if os.path.exists(desktop_file):
            print(f"✅ Fichier trouvé sur Bureau OneDrive: {desktop_file}")
            return desktop_file

    print("⚠️ Fichier non trouvé dans OneDrive, tentative avec le chemin original")
    return file_path
