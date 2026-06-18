"""
Runner headless du scheduler — lancé par le Planificateur de tâches Windows.

Permet aux tâches planifiées de s'exécuter **même quand l'application (GUI) est
fermée**, tant que la session Windows est ouverte (PC allumé). Le Planificateur
de tâches Windows lance ce script toutes les N minutes ; il exécute UN passage
du ``SchedulerService`` (tâches dues + rattrapage) puis s'arrête.

Quand le GUI ou le Relay est ouvert, leur scheduler in-process détient le verrou
(``data/scheduler.lock``) : ce runner détecte alors qu'un scheduler est déjà
actif et ne fait rien — aucune double exécution.

Usage :
    pythonw scheduler_runner.py             # exécute les tâches dues, puis quitte
    python  scheduler_runner.py --register [N]   # enregistre la tâche Windows (toutes les N min)
    python  scheduler_runner.py --unregister
    python  scheduler_runner.py --status
"""

import os
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent


def _prepare_runtime() -> None:
    """Prépare l'environnement d'exécution (path, cwd, flux de sortie).

    Sous ``pythonw.exe`` il n'y a pas de console : ``sys.stdout``/``stderr``
    peuvent être ``None`` et les ``print()`` emoji de certains modules
    planteraient. On garantit des flux UTF-8 valides avant tout import lourd.
    """
    sys.path.insert(0, str(_ROOT))
    try:
        os.chdir(_ROOT)
    except OSError:
        pass
    for name in ("stdout", "stderr"):
        stream = getattr(sys, name, None)
        if stream is None:
            try:
                setattr(sys, name, open(os.devnull, "w", encoding="utf-8"))
            except OSError:
                pass
        else:
            try:
                stream.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
            except Exception:
                pass


def run_due_tasks() -> bool:
    """Exécute les tâches planifiées dues (une passe). Retourne True si actif."""
    _prepare_runtime()
    from core.scheduler import SchedulerService
    # Instance dédiée (process séparé) avec son propre exécuteur lazy.
    service = SchedulerService()
    return service.run_once()


# ----------------------------------------------------------------------
# Intégration Planificateur de tâches Windows (schtasks)
# ----------------------------------------------------------------------

def _task_name() -> str:
    _prepare_runtime()
    try:
        from core.config import get_config
        return get_config().get("scheduler.windows_task_name", "My_AI Scheduler")
    except Exception:
        return "My_AI Scheduler"


def _pythonw_path() -> str:
    """Chemin de pythonw.exe (pas de fenêtre console), sinon python.exe."""
    exe = Path(sys.executable)
    candidate = exe.with_name("pythonw.exe")
    return str(candidate if candidate.exists() else exe)


def register_windows_task(interval_minutes: int = 5):
    """Enregistre une tâche Planificateur Windows (par utilisateur, sans admin).

    Tourne quand la session est ouverte (aucun mot de passe stocké). Retourne
    ``(ok: bool, message: str)``.
    """
    if os.name != "nt":
        return False, "Disponible uniquement sous Windows."
    import subprocess
    runner = _ROOT / "core" / "scheduler_runner.py"
    tr = f'"{_pythonw_path()}" "{runner}"'
    cmd = [
        "schtasks", "/Create", "/TN", _task_name(), "/TR", tr,
        "/SC", "MINUTE", "/MO", str(max(1, int(interval_minutes))), "/F",
    ]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode == 0:
            return True, f"Exécution en arrière-plan activée (toutes les {interval_minutes} min)."
        return False, (res.stderr or res.stdout or "Échec schtasks").strip()
    except Exception as exc:  # pragma: no cover - dépend de l'OS
        return False, str(exc)


def unregister_windows_task():
    """Supprime la tâche Planificateur Windows. Retourne (ok, message)."""
    if os.name != "nt":
        return False, "Disponible uniquement sous Windows."
    import subprocess
    cmd = ["schtasks", "/Delete", "/TN", _task_name(), "/F"]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode == 0:
            return True, "Exécution en arrière-plan désactivée."
        return False, (res.stderr or res.stdout or "Échec schtasks").strip()
    except Exception as exc:  # pragma: no cover
        return False, str(exc)


def is_windows_task_registered() -> bool:
    """Indique si la tâche Planificateur Windows existe."""
    if os.name != "nt":
        return False
    import subprocess
    try:
        res = subprocess.run(
            ["schtasks", "/Query", "/TN", _task_name()],
            capture_output=True, text=True,
        )
        return res.returncode == 0
    except Exception:  # pragma: no cover
        return False


def main(argv=None) -> None:
    argv = list(sys.argv[1:] if argv is None else argv)
    if "--register" in argv:
        interval = next((int(a) for a in argv if a.isdigit()), 5)
        ok, msg = register_windows_task(interval)
        print(msg)
        sys.exit(0 if ok else 1)
    if "--unregister" in argv:
        ok, msg = unregister_windows_task()
        print(msg)
        sys.exit(0 if ok else 1)
    if "--status" in argv:
        print("registered" if is_windows_task_registered() else "not-registered")
        sys.exit(0)
    # Défaut : exécuter les tâches dues (mode lancé par le Planificateur).
    run_due_tasks()


if __name__ == "__main__":
    main()
