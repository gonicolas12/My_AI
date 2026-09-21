#!/usr/bin/env python3
"""Détecte (et supprime, sur demande) les dossiers .dist-info corrompus.

Pourquoi
--------
Quand un ``pip install`` est interrompu, pip peut laisser des dossiers
``<paquet>-<version>.dist-info`` vidés de leur fichier ``METADATA``, parfois à
côté du dossier neuf de la version suivante. L'ancien reste alors visible pour
``importlib.metadata`` mais ne déclare plus aucune version.

Le symptôme est illisible. Exemple réel, où deux dossiers ``regex`` coexistaient
et où le plus ancien n'avait plus de METADATA ::

    ValueError: Unable to compare versions for regex!=2019.12.17:
                need=2019.12.17 found=None

Rien dans ce message ne désigne l'installation interrompue.

Usage
-----
    python tools/clean_broken_dist_info.py            # inventaire seul
    python tools/clean_broken_dist_info.py --delete   # supprime après confirmation
    python tools/clean_broken_dist_info.py --delete --yes

Le mode par défaut ne touche à rien : il liste ce qui serait supprimé.
"""

from __future__ import annotations

import argparse
import shutil
import site
import sys
import sysconfig
from pathlib import Path


def site_packages_dirs() -> list:
    """Répertoires site-packages de l'interpréteur courant, dédoublonnés."""
    candidates = []
    for key in ("purelib", "platlib"):
        path = sysconfig.get_paths().get(key)
        if path:
            candidates.append(path)
    try:
        candidates.extend(site.getsitepackages())
    except AttributeError:  # pragma: no cover - environnements exotiques
        pass
    user = site.getusersitepackages() if hasattr(site, "getusersitepackages") else None
    if isinstance(user, str):
        candidates.append(user)

    seen, out = set(), []
    for c in candidates:
        p = Path(c)
        if p.is_dir() and p not in seen:
            seen.add(p)
            out.append(p)
    return out


def broken_dist_infos(dirs) -> list:
    """Dossiers .dist-info dont le METADATA est absent ou vide."""
    broken = []
    for d in dirs:
        for info in sorted(d.glob("*.dist-info")):
            meta = info / "METADATA"
            try:
                if not meta.is_file() or meta.stat().st_size == 0:
                    broken.append(info)
            except OSError:
                broken.append(info)
    return broken


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Détecte les .dist-info sans METADATA laissés par un pip interrompu."
    )
    parser.add_argument(
        "--delete", action="store_true", help="supprimer (sinon : inventaire seul)"
    )
    parser.add_argument(
        "--yes", action="store_true", help="ne pas demander de confirmation"
    )
    args = parser.parse_args()

    dirs = site_packages_dirs()
    print(f"Interpréteur : {sys.executable}")
    for d in dirs:
        print(f"  site-packages : {d}")

    broken = broken_dist_infos(dirs)
    if not broken:
        print("\n✅ Aucun .dist-info corrompu détecté.")
        return 0

    print(f"\n⚠️  {len(broken)} dossier(s) .dist-info sans METADATA :")
    for b in broken:
        print(f"   - {b}")

    if not args.delete:
        print("\nInventaire seul — rien n'a été supprimé.")
        print("Relancez avec --delete pour nettoyer, puis réinstallez :")
        print("   pip install -r requirements.txt")
        return 0

    if not args.yes:
        try:
            answer = input(f"\nSupprimer ces {len(broken)} dossiers ? [o/N] ")
        except EOFError:
            answer = ""
        if answer.strip().lower() not in ("o", "oui", "y", "yes"):
            print("Annulé — rien n'a été supprimé.")
            return 1

    removed = 0
    for b in broken:
        try:
            shutil.rmtree(b)
            removed += 1
        except OSError as exc:
            print(f"   ⚠️ {b} : {exc}")
    print(f"\n✅ {removed}/{len(broken)} dossier(s) supprimé(s).")
    print("Réinstallez maintenant :  pip install -r requirements.txt")
    return 0


if __name__ == "__main__":
    sys.exit(main())
