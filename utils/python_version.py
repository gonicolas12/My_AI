"""
Versions de Python prises en charge par My_AI

- 3.11 au moins : Python 3.10 est en fin de vie depuis le 1er octobre 2026,
  et Pillow 13, websockets 17, PyMuPDF 2 et torch 2.15 ne s'y installent plus.
- 3.14 au plus : onnxruntime, dont dépendent chromadb et faster-whisper, ne
  publie encore aucune roue pour Python 3.15 ; « pip install -r
  requirements.txt » y échoue.
- Mac Intel (x86_64) : 3.12 au plus. torch 2.2.2 et numpy 1.26.4, les
  dernières versions publiées pour cette architecture, s'arrêtent là.

launch.bat et launch.sh font le même contrôle. Les lanceurs Python
(launch_unified.py, main.py) appellent check_python_version() avant
d'installer quoi que ce soit : ce module n'utilise que la bibliothèque
standard, et une syntaxe que les anciens Python lisent encore.
"""

import platform
import sys
from typing import Optional, Sequence, Tuple

MINIMUM = (3, 11)
MAXIMUM = (3, 14)
MAXIMUM_INTEL_MAC = (3, 12)


def supported_range(
    system: Optional[str] = None, machine: Optional[str] = None
) -> Tuple[Tuple[int, int], Tuple[int, int]]:
    """Plus ancienne et plus récente version de Python prises en charge sur cette machine."""
    system = platform.system() if system is None else system
    machine = platform.machine() if machine is None else machine
    if system == "Darwin" and machine == "x86_64":
        return MINIMUM, MAXIMUM_INTEL_MAC
    return MINIMUM, MAXIMUM


def unsupported_message(
    version: Optional[Sequence[int]] = None,
    system: Optional[str] = None,
    machine: Optional[str] = None,
) -> Optional[str]:
    """
    Message à afficher si cette version de Python ne convient pas

    Args:
        version: (majeure, mineure), celle de l'interpréteur courant par défaut
        system: platform.system() par défaut
        machine: platform.machine() par défaut

    Returns:
        None si la version est prise en charge, sinon deux lignes dans la langue
        de l'appli : le problème, puis quoi installer
    """
    current = tuple(sys.version_info[:2]) if version is None else tuple(version[:2])
    low, high = supported_range(system, machine)
    if low <= current <= high:
        return None
    params = {
        "version": "%d.%d" % current,
        "minimum": "%d.%d" % low,
        "maximum": "%d.%d" % high,
    }
    try:
        # core.i18n n'importe que la bibliothèque standard (config.yaml lu si possible)
        from core.i18n import tr  # pylint: disable=import-outside-toplevel

        return "%s\n%s" % (
            tr("launch.pythonUnsupported", **params), tr("launch.pythonInstall", **params)
        )
    except Exception:  # pylint: disable=broad-except
        return (
            "Python {version} is not supported: My_AI needs Python {minimum} to {maximum}.\n"
            "Install Python {maximum} (python.org), then start My_AI again."
        ).format(**params)


def check_python_version() -> None:
    """Arrête le lanceur, avec un message clair, sur une version de Python non prise en charge."""
    message = unsupported_message()
    if not message:
        return
    try:
        print(message, flush=True)
    except UnicodeEncodeError:  # console qui ne connaît pas l'alphabet de la langue
        encoding = getattr(sys.stdout, "encoding", None) or "ascii"
        print(message.encode(encoding, "replace").decode(encoding), flush=True)
    sys.exit(1)
