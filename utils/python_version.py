"""
Versions de Python prises en charge par My_AI

- 3.11 au moins : Python 3.10 est en fin de vie depuis le 1er octobre 2026,
  et Pillow 13, websockets 17, PyMuPDF 2 et torch 2.15 ne s'y installent plus.
- 3.14 au plus : onnxruntime, dont dépendent chromadb et faster-whisper, ne
  publie encore aucune roue pour Python 3.15 ; « pip install -r
  requirements.txt » y échoue.
- Mac Intel (x86_64) : 3.12 au plus. torch 2.2.2 et numpy 1.26.4, les
  dernières versions publiées pour cette architecture, s'arrêtent là.

Dans cette plage, un Python sans le correctif de sécurité du 25/10/2026 (clés
eMudhra compromises, voir SECURITY_FIXES) se lance quand même, avec un
avertissement (outdated_message).

launch.bat et launch.sh font le même contrôle de plage, puis lancent
launch_unified.py, qui donne l'avertissement. Les lanceurs Python
(launch_unified.py, main.py) appellent check_python_version() avant
d'installer quoi que ce soit : ce module n'utilise que la bibliothèque
standard, et une syntaxe que les anciens Python lisent encore.
"""

import platform
import sys
from typing import Any, Callable, Dict, Optional, Sequence, Tuple

MINIMUM = (3, 11)
MAXIMUM = (3, 14)
MAXIMUM_INTEL_MAC = (3, 12)

# Correctif de sécurité du 25/10/2026 (CVE-2026-115557, gh-160040) : des clés
# d'autorités intermédiaires eMudhra ont été compromises le 20/10/2026, et le
# module ssl refuse depuis toute chaîne de certificats qui en contient une,
# même quand l'appli apporte ses propres autorités (certifi, dont se servent
# requests et pip, garde la racine emSign Root CA - G1). Première version
# corrigée de chaque branche. Seule la 3.14 a des installeurs (Windows,
# macOS) : les autres branches ne reçoivent plus que leurs sources.
SECURITY_FIXES: Dict[Tuple[int, int], Tuple[int, int, int]] = {
    (3, 11): (3, 11, 18),
    (3, 12): (3, 12, 16),
    (3, 13): (3, 13, 18),
    (3, 14): (3, 14, 10),
}
# Conseillée là où python.org publie un installeur (Windows, Mac Apple Silicon)
RECOMMENDED = (3, 14, 10)

# Empreintes SHA-256 des clés refusées par ce correctif (Modules/_ssl/
# distrusted_spki.h de CPython, les mêmes dans les quatre branches), compilées
# telles quelles dans le module _ssl : les y trouver prouve le correctif, même
# rétroporté par une distribution Linux qui garde son numéro de version.
_REFUSED_KEY_DIGESTS = tuple(bytes.fromhex(digest) for digest in (
    "43bffa19d6ef651451f6841e019931e96f6f2eaeff28ab4b6f1ce4576de2717b",
    "49dd353dc2b919a3770645117d0e60c16115e7d1bc259eefe734b00ea434fe5f",
    "5c0660a2b164910d8ff589c18e14552e9e0ec237dcefe2cb736d41a4811f81a0",
    "63ecefee431d49523bc1136c4e72d0206a477086caf606cd5cf025686c109cf8",
    "92c063d67e8f14db71d288e11266ffdaf69cbf115f7bab14f3bc2f68d25e0e30",
    "e0254c7fcdc265e2f0f8a428dabb75ab4ae039b4872d62f5ee57f0877d5a8a41",
    "ebed6475c2c2d80fcb199f3fe8dd6e6b3ce60b77eb15d4e42c3dec0c6f5b5105",
    "ec4ffa1ad0ac88081314b7aaffef6a91f97cd57291bb5ba686c5415f5eb4f6b6",
))

# Repli anglais si core.i18n ne se charge pas (comme pour unsupported_message)
_OUTDATED_EN = (
    "Python {version} predates security fix {fixed}: its HTTPS connections, including pip's "
    "automatic installs, are less protected against interception (compromised eMudhra keys)."
)
_UPDATE_INSTALLER_EN = "Install Python {recommended} or later (python.org), then start My_AI again."
_UPDATE_PACKAGES_EN = (
    "Install the fixed Python from your distribution or package manager ({fixed} or later), "
    "then start My_AI again."
)
_OUTDATED_TITLE_EN = "Python update recommended"


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


def _tr(key: str, fallback: str, **params: Any) -> str:
    """Texte dans la langue de l'appli ; en anglais si core.i18n ne se charge pas."""
    try:
        # core.i18n n'importe que la bibliothèque standard (config.yaml lu si possible)
        from core.i18n import tr  # pylint: disable=import-outside-toplevel

        text = tr(key, **params)
    except Exception:  # pylint: disable=broad-except
        text = key
    return fallback.format(**params) if text == key else text


def ssl_refuses_compromised_keys() -> Optional[bool]:
    """Le module _ssl de cet interpréteur contient-il les clés eMudhra refusées ?

    Returns:
        None si on ne peut pas le savoir : module intégré à l'interpréteur (sans
        fichier), illisible, ou Python sans ssl
    """
    try:
        import _ssl  # pylint: disable=import-outside-toplevel

        path = getattr(_ssl, "__file__", None)
        if not path:
            return None
        with open(path, "rb") as module:
            data = module.read()
    except (ImportError, OSError):
        return None
    return any(digest in data for digest in _REFUSED_KEY_DIGESTS)


def outdated_message(
    version: Optional[Sequence[int]] = None,
    system: Optional[str] = None,
    machine: Optional[str] = None,
) -> Optional[str]:
    """
    Avertissement pour un Python sans le correctif de sécurité de sa branche

    Rien de bloquant : ses connexions HTTPS, dont les installations
    automatiques de pip (utils/requirements_sync.py), sont seulement moins
    protégées contre une interception.

    Args:
        version: (majeure, mineure, micro), celle de l'interpréteur courant par
            défaut ; alors son module _ssl est lu aussi, pour un correctif
            rétroporté sans changement de numéro (distribution Linux)
        system: platform.system() par défaut
        machine: platform.machine() par défaut

    Returns:
        None si le correctif est là (ou branche hors de SECURITY_FIXES), sinon
        deux lignes dans la langue de l'appli : le problème, puis quoi installer
    """
    current = tuple(sys.version_info[:3]) if version is None else tuple(version[:3])
    fixed = SECURITY_FIXES.get(current[:2])
    if fixed is None or current >= fixed:
        return None
    if version is None and ssl_refuses_compromised_keys():
        return None
    system = platform.system() if system is None else system
    machine = platform.machine() if machine is None else machine
    params = {
        "version": "%d.%d.%d" % current,
        "fixed": "%d.%d.%d" % fixed,
        "recommended": "%d.%d.%d" % RECOMMENDED,
    }
    # Installeur de python.org pour la 3.14 seulement, et le Mac Intel s'arrête
    # à 3.12 : ailleurs, le Python de la distribution ou du gestionnaire de paquets
    if system == "Windows" or (system == "Darwin" and machine != "x86_64"):
        advice = _tr("launch.pythonUpdateInstaller", _UPDATE_INSTALLER_EN, **params)
    else:
        advice = _tr("launch.pythonUpdatePackages", _UPDATE_PACKAGES_EN, **params)
    return "%s\n%s" % (_tr("launch.pythonOutdated", _OUTDATED_EN, **params), advice)


def _print(message: str) -> None:
    """Écrit le message dans la console (ou le fichier des sorties, sans console)."""
    try:
        print(message, flush=True)
    except UnicodeEncodeError:  # console qui ne connaît pas l'alphabet de la langue
        encoding = getattr(sys.stdout, "encoding", None) or "ascii"
        print(message.encode(encoding, "replace").decode(encoding), flush=True)


def check_python_version(
    report: Optional[Callable[[str], Any]] = None,
    notify: Optional[Callable[[str, str], Any]] = None,
) -> None:
    """Arrête le lanceur, avec un message clair, sur une version de Python non prise en charge.

    Un Python pris en charge mais sans le correctif de sécurité de sa branche
    est seulement signalé (outdated_message), une fois, et le lancement continue.

    Args:
        report: montre aussi le message d'arrêt hors de la console (boîte de
            dialogue d'un lancement sans console, cf. utils/no_console.py)
        notify: montre aussi l'avertissement hors de la console, sans rien
            bloquer : reçoit un titre et un texte (notification du système)
    """
    message = unsupported_message()
    if message:
        _print(message)
        if report is not None:
            report(message)
        sys.exit(1)
    warning = outdated_message()
    if not warning:
        return
    _print(warning)
    if notify is not None:
        problem, advice = warning.split("\n", 1)
        # Le conseil d'abord : une notification n'en garde que 220 caractères
        notify(_tr("launch.pythonOutdatedTitle", _OUTDATED_TITLE_EN), "%s\n%s" % (advice, problem))
