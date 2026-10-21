"""
Tests de l'installation automatique de ComfyUI (models/comfyui_manager.py).

Le build NVIDIA de ComfyUI portable, seul installé jusqu'ici, s'arrête au
démarrage sur un PC sans carte NVIDIA (« Windows fatal exception: access
violation » dans torch.cuda). Sur un Core Ultra 7 255H, le GPU intégré Intel
Arc 140T fait tourner le build Intel (~2 s par image) et le CPU le build NVIDIA
en mode --cpu (~30 s). Rien n'est téléchargé ni lancé ici : PowerShell, le
téléchargement, 7-Zip et le process de ComfyUI sont simulés.
"""

import stat
import subprocess
import sys
from types import SimpleNamespace

import pytest

from models import comfyui_manager as cm

# Cartes vues par Win32_VideoController : PNPDeviceID|Name (instances fictives)
ARC_140T = r"PCI\VEN_8086&DEV_7D51&SUBSYS_00000000&REV_03\3&0&0&10|Intel(R) Arc(TM) 140T GPU (15GB)"
UHD_620 = r"PCI\VEN_8086&DEV_5917&SUBSYS_00000000&REV_07\3&0&0&10|Intel(R) UHD Graphics 620"
RTX_3060 = r"PCI\VEN_10DE&DEV_2560&SUBSYS_00000000&REV_A1\4&0&0&0008|NVIDIA GeForce RTX 3060 Laptop GPU"
RX_7800 = r"PCI\VEN_1002&DEV_747E&SUBSYS_00000000&REV_C8\6&0&0&0019|AMD Radeon RX 7800 XT"
VIRTUAL = r"ROOT\DISPLAY\0000|Mirage Driver"

# Journal du build NVIDIA lancé sans carte NVIDIA (extraits)
CUDA_CRASH_LOG = (
    "\x1b[32m[INFO]\x1b[0m Found comfy_kitchen backend triton: {'available': False, "
    "'unavailable_reason': \"ImportError: No module named 'triton'\"}\n"
    "C:\\ComfyUI\\python_embeded\\Lib\\site-packages\\torch\\cuda\\__init__.py:228: "
    "UserWarning: cudaGetDeviceCount() returned cudaErrorNotSupported\n"
    "Windows fatal exception: access violation\n"
    "\n"
    "Stack (most recent call first):\n"
    '  File "C:\\ComfyUI\\comfy\\model_management.py", line 213 in get_torch_device\n'
)
READY_LOG = "\x1b[32m[INFO]\x1b[0m To see the GUI go to: http://127.0.0.1:8188\n"


def gpus_seen(monkeypatch, *adapters):
    """detect_gpu_builds sur une machine Windows aux cartes données."""
    monkeypatch.setattr(sys, "platform", "win32")
    output = "\n".join(adapters) + "\n"
    monkeypatch.setattr(subprocess, "run", lambda *_a, **_k: SimpleNamespace(stdout=output))
    return cm.detect_gpu_builds()


def test_arc_integrated_gpu_takes_the_intel_build(monkeypatch):
    assert gpus_seen(monkeypatch, VIRTUAL, VIRTUAL, ARC_140T) == {"intel"}


def test_older_intel_integrated_gpu_has_no_build(monkeypatch):
    # Pas de torch.xpu pour les Intel UHD / Iris Xe : ComfyUI tournera sur le CPU
    assert gpus_seen(monkeypatch, UHD_620) == set()


def test_every_gpu_of_the_machine_is_seen(monkeypatch):
    assert gpus_seen(monkeypatch, ARC_140T, RTX_3060, RX_7800) == {"intel", "nvidia", "amd"}


def test_failed_detection_is_unknown(monkeypatch):
    def timeout(*_a, **_k):
        raise subprocess.TimeoutExpired("powershell", 30)

    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setattr(subprocess, "run", timeout)
    assert cm.detect_gpu_builds() is None


# ── Installation et lancement ───────────────────────────────────────────────


def make_portable(root, build, files=()):
    """Arborescence d'un ComfyUI portable : python, main.py, lanceur du build,
    et un pack de son dépôt git, en lecture seule comme sous Windows."""
    (root / "python_embeded").mkdir(parents=True)
    (root / "python_embeded" / "python.exe").write_bytes(b"")
    (root / "ComfyUI" / "models" / "checkpoints").mkdir(parents=True)
    (root / "ComfyUI" / "main.py").write_text("", encoding="utf-8")
    (root / f"run_{build}_gpu.bat").write_text("", encoding="utf-8")
    pack = root / "ComfyUI" / ".git" / "objects" / "pack" / "pack-0123abcd.pack"
    pack.parent.mkdir(parents=True)
    pack.write_bytes(b"git")
    pack.chmod(stat.S_IREAD)
    for relative, content in files:
        path = root / "ComfyUI" / "models" / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)


class FakeComfyUI:
    """Process ComfyUI simulé : répond, ou s'arrête au démarrage selon le mode."""

    def __init__(self):
        self.launches = []  # commandes, dans l'ordre
        self.crashes_on = set()  # "gpu" et/ou "cpu"
        self.up = False
        self.downloads = []  # URL téléchargées
        self.extracted_build = None  # build livré par la prochaine extraction

    def popen(self, cmd, stdout, **_kwargs):
        self.launches.append(cmd)
        mode = "cpu" if "--cpu" in cmd else "gpu"
        crashed = mode in self.crashes_on
        stdout.write((CUDA_CRASH_LOG if crashed else READY_LOG).encode("utf-8"))
        self.up = not crashed
        return SimpleNamespace(pid=4242, poll=lambda: 1 if crashed else None,
                               terminate=lambda: None)

    def download(self, url, dest, _prog, _check, **_kwargs):
        self.downloads.append(url)
        dest.write_bytes(b"7z")

    def extract(self, _archive, dest, _prog, _check):
        make_portable(dest / "ComfyUI_windows_portable", self.extracted_build)

    def modes(self):
        return ["cpu" if "--cpu" in cmd else "gpu" for cmd in self.launches]


@pytest.fixture(name="comfy")
def _comfy(tmp_path, monkeypatch):
    """Gestionnaire dans un dossier temporaire, sans réseau, process ni PowerShell."""
    fake = FakeComfyUI()
    manager = cm.ComfyUIManager(root=tmp_path)
    manager._portable_url = "https://example.test/ComfyUI_windows_portable_{build}.7z"
    monkeypatch.setattr(cm.ComfyUIManager, "is_supported", staticmethod(lambda: True))
    monkeypatch.setattr(manager, "is_responding", lambda: fake.up)
    monkeypatch.setattr(manager, "_download_file", fake.download)
    monkeypatch.setattr(manager, "_extract_7z", fake.extract)
    monkeypatch.setattr(subprocess, "Popen", fake.popen)
    return SimpleNamespace(manager=manager, fake=fake, tmp_path=tmp_path)


def gpus(comfy, builds):
    """Résultat de la détection des GPU (None : détection échouée)."""
    comfy.manager._gpus, comfy.manager._gpus_known = builds, True


def test_nvidia_build_runs_on_cpu_without_any_usable_gpu(comfy):
    make_portable(comfy.manager._portable_dir, "nvidia", [("checkpoints/sd_turbo.safetensors", b"w")])
    gpus(comfy, set())  # Intel UHD seul

    assert comfy.manager.ensure_running() is True
    assert comfy.fake.modes() == ["cpu"]  # pas d'essai voué à l'échec sur le GPU
    assert comfy.fake.downloads == []


def test_gpu_crash_at_startup_relaunches_on_cpu(comfy, capsys):
    make_portable(comfy.manager._portable_dir, "nvidia", [("checkpoints/sd_turbo.safetensors", b"w")])
    gpus(comfy, None)
    comfy.fake.crashes_on = {"gpu"}

    assert comfy.manager.ensure_running() is True
    assert comfy.fake.modes() == ["gpu", "cpu"]
    assert "Windows fatal exception: access violation" in capsys.readouterr().out


def test_crash_on_cpu_too_cites_the_error_and_the_log(comfy):
    make_portable(comfy.manager._portable_dir, "nvidia", [("checkpoints/sd_turbo.safetensors", b"w")])
    gpus(comfy, None)
    comfy.fake.crashes_on = {"gpu", "cpu"}

    with pytest.raises(cm.ComfyUISetupError) as error:
        comfy.manager.ensure_running()
    message = str(error.value)
    assert "s'est arrêté au démarrage (Windows fatal exception: access violation)" in message
    assert str(comfy.manager.log_path) in message


def test_build_that_cannot_use_the_gpu_is_replaced_with_its_models(comfy):
    # Build NVIDIA installé avant la détection du GPU, sur un PC Intel Arc
    make_portable(comfy.manager._portable_dir, "nvidia", [
        ("checkpoints/sd_turbo.safetensors", b"turbo"),
        ("loras/style.safetensors", b"lora"),
    ])
    gpus(comfy, {"intel"})
    comfy.fake.extracted_build = "intel"

    assert comfy.manager.ensure_running() is True
    assert comfy.fake.downloads == ["https://example.test/ComfyUI_windows_portable_intel.7z"]
    assert comfy.manager.installed_build() == "intel"
    models = comfy.manager._portable_dir / "ComfyUI" / "models"
    assert (models / "checkpoints" / "sd_turbo.safetensors").read_bytes() == b"turbo"
    assert (models / "loras" / "style.safetensors").read_bytes() == b"lora"
    assert comfy.fake.modes() == ["gpu"]
    # Ni archive, ni extraction, ni ancien build (effacé pendant le démarrage)
    comfy.manager._cleaner.join(timeout=10)
    assert sorted(p.name for p in comfy.manager._tools_dir.iterdir()) == ["ComfyUI_windows_portable"]


def test_failed_build_switch_keeps_the_old_build_on_cpu(comfy, monkeypatch):
    make_portable(comfy.manager._portable_dir, "nvidia", [("checkpoints/sd_turbo.safetensors", b"w")])
    gpus(comfy, {"intel"})

    def offline(*_args, **_kwargs):
        raise cm.ComfyUISetupError("Téléchargement de ComfyUI (intel) échoué : hors ligne")

    monkeypatch.setattr(comfy.manager, "_download_file", offline)

    assert comfy.manager.ensure_running() is True
    assert comfy.manager.installed_build() == "nvidia"
    assert comfy.fake.modes() == ["cpu"]


def test_first_install_takes_the_build_of_the_gpu(comfy, monkeypatch):
    gpus(comfy, {"amd", "intel"})
    comfy.fake.extracted_build = "amd"

    def download_model(_prog, _check):
        comfy.fake.downloads.append("modèle")
        (comfy.manager._checkpoints_dir / "sd_turbo.safetensors").write_bytes(b"w")

    monkeypatch.setattr(comfy.manager, "_download_model", download_model)

    assert comfy.manager.ensure_running() is True
    assert comfy.fake.downloads == ["https://example.test/ComfyUI_windows_portable_amd.7z", "modèle"]
    assert comfy.fake.modes() == ["gpu"]


def test_stop_during_the_build_switch_stops_everything(comfy, monkeypatch):
    make_portable(comfy.manager._portable_dir, "nvidia", [("checkpoints/sd_turbo.safetensors", b"w")])
    gpus(comfy, {"intel"})

    def interrupted(*_args, **_kwargs):
        raise cm.ComfyUISetupError("__interrupted__")

    monkeypatch.setattr(comfy.manager, "_download_file", interrupted)

    with pytest.raises(cm.ComfyUISetupError, match="__interrupted__"):
        comfy.manager.ensure_running()
    assert comfy.fake.launches == []


def test_log_excerpt_is_the_last_python_error(comfy):
    comfy.manager.log_path.parent.mkdir(parents=True)
    comfy.manager.log_path.write_text(
        "Traceback (most recent call last):\n"
        '  File "C:\\ComfyUI\\main.py", line 259, in <module>\n'
        "PermissionError: [WinError 5] Accès refusé. Error loading c10_xpu.dll\n",
        encoding="utf-8",
    )
    assert comfy.manager._log_excerpt() == (
        "PermissionError: [WinError 5] Accès refusé. Error loading c10_xpu.dll"
    )
    comfy.manager.log_path.write_text("", encoding="utf-8")
    assert comfy.manager._log_excerpt() == "aucune sortie"
