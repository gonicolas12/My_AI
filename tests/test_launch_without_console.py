"""
Tests du lanceur ouvert depuis l'épingle de la barre des tâches (launch_unified.py)

L'épingle lance « pythonw launch_unified.py » sans dossier garanti ni console.
Le lanceur doit se placer dans son dossier (config.yaml, data/ et logs/ y
sont lus et écrits) et, sans console, écrire ses sorties dans logs/. Vrais
lancements ici, arrêtés par --help avant toute étape (ni Ollama ni fenêtre).
"""

import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
LAUNCHER = PROJECT_ROOT / "launch_unified.py"
# Ni installation de dépendances ni Relay : le lanceur s'arrête à --help
ENV = {**os.environ, "MY_AI_SKIP_DEPS_SYNC": "1", "PYTHONIOENCODING": "utf-8"}


def test_the_launcher_works_from_any_folder(tmp_path):
    """Lancé d'ailleurs (épingle, raccourci), rien n'est écrit dans le dossier courant."""
    run = subprocess.run([sys.executable, str(LAUNCHER), "--help"], cwd=tmp_path,
                         capture_output=True, encoding="utf-8", env=ENV, timeout=180,
                         check=False)
    assert run.returncode == 0, run.stderr[-3000:]
    assert "usage: launch_unified.py" in run.stdout
    assert list(tmp_path.iterdir()) == []  # ni logs/ ni data/ ici


# Le lanceur, tel que l'épingle le lance, sans vraie boîte de dialogue ni
# notification en test (un Python sans le correctif de sécurité de sa branche
# est signalé par une notification)
PINNED = (
    "import runpy, sys\n"
    "sys.path.insert(0, sys.argv[1])\n"
    "from utils import desktop_notify, no_console\n"
    "no_console._message_box = lambda message, icon: print('BOÎTE', message) or True\n"
    "desktop_notify.notify_desktop = lambda title, message: print('NOTIFICATION', title) or True\n"
    "sys.argv = [sys.argv[2], '--help']\n"
    "runpy.run_path(sys.argv[0], run_name='__main__')\n"
)


def test_a_pinned_launch_writes_its_outputs_to_the_logs(tmp_path):
    pythonw = Path(sys.executable).with_name("pythonw.exe")
    if not sys.platform.startswith("win") or not pythonw.is_file():
        pytest.skip("pythonw : Windows seulement")
    # Aucune sortie redirigée : comme lancé par l'Explorateur, sys.stdout vaut None
    process = subprocess.Popen([str(pythonw), "-c", PINNED, str(PROJECT_ROOT), str(LAUNCHER)],
                               cwd=tmp_path, env=ENV)
    assert process.wait(timeout=180) == 0
    log = PROJECT_ROOT / "logs" / f"console_{time.strftime('%Y%m%d')}.log"
    text = log.read_text(encoding="utf-8")
    start = text.index(f"pid {process.pid}) =====")
    following = text.find("\n===== ", start)
    block = text[start:] if following == -1 else text[start:following]
    assert "usage: launch_unified.py" in block
    assert "BOÎTE" not in block
    assert list(tmp_path.iterdir()) == []
