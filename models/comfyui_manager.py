"""
Gestionnaire ComfyUI portable auto-géré (backend de génération d'image).

Au premier besoin de génération d'image, si aucun backend n'est détecté et que
`image_generation.auto_setup` est actif, ce module :
  1. télécharge dans `tools/` le build **ComfyUI portable** du GPU de la machine
     (NVIDIA, AMD ou Intel Arc ; sans GPU reconnu, le build NVIDIA, sur le CPU).
     Python et torch y sont EMBARQUÉS : il n'altère PAS l'environnement Python
     de My_AI,
  2. l'extrait (archive .7z),
  3. télécharge un checkpoint Stable Diffusion par défaut (si aucun présent),
  4. lance ComfyUI en sous-processus et attend qu'il réponde sur localhost:8188.
     S'il s'arrête au démarrage sur le GPU (pilote, carte non prise en charge),
     il est relancé sur le CPU.

Un build qui ne sait pas utiliser le GPU de la machine (le build NVIDIA, seul
installé avant la détection du GPU, sur un PC Intel ou AMD) est remplacé par le
bon, modèles gardés. La sortie de ComfyUI va dans logs/comfyui.log.

Tout est piloté par des callbacks de progression pour alimenter l'animation
« Génération en cours » du GUI, et interruptible (bouton STOP). Même esprit que
le téléchargement automatique de cloudflared pour le tunnel Relay.

⚠️ Les builds portables sont **Windows**. Sur les autres plateformes, on laisse
l'utilisateur installer ComfyUI/Forge lui-même (message clair).
"""

from __future__ import annotations

import os
import re
import shutil
import stat
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Callable, Optional, Set

import requests

ProgressCallback = Callable[[float, str], None]
InterruptCallback = Callable[[], bool]

# Builds portables publiés par ComfyUI, par ordre de préférence quand la machine
# a plusieurs GPU. Le build nvidia sert aussi au mode CPU.
BUILDS = ("nvidia", "amd", "intel")

# Identifiant PCI du fabricant → build
_PCI_VENDORS = {"10DE": "nvidia", "1002": "amd", "8086": "intel"}

# Le 1er lancement après l'installation peut prendre plusieurs minutes :
# l'antivirus analyse chaque DLL de torch à son premier chargement. Un arrêt au
# démarrage, lui, est vu tout de suite.
_STARTUP_TIMEOUT = 600

_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)

_ANSI = re.compile(r"\x1b\[[0-9;]*m")
# Ligne d'erreur d'une trace Python (« RuntimeError: … ») ou de faulthandler
_ERROR_LINE = re.compile(r"^[\w.]*(Error|Exception)\b|fatal exception")


def detect_gpu_builds() -> Optional[Set[str]]:
    """Builds ComfyUI que les GPU de la machine savent faire tourner (Windows).

    Lit les cartes présentes (Win32_VideoController) par l'identifiant PCI de
    leur fabricant. Côté Intel, seuls les GPU Arc ont torch.xpu : les Intel UHD
    et Iris Xe passent par le CPU. None si la détection échoue.
    """
    if sys.platform != "win32":
        return None
    try:
        out = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-NonInteractive",
                "-Command",
                "Get-CimInstance Win32_VideoController | "
                "ForEach-Object { $_.PNPDeviceID + '|' + $_.Name }",
            ],
            capture_output=True,
            text=True,
            errors="replace",
            timeout=30,
            creationflags=_NO_WINDOW,
            check=True,
        ).stdout
    except (OSError, subprocess.SubprocessError):
        return None
    builds = set()
    for line in out.splitlines():
        device, _, name = line.partition("|")
        vendor = re.search(r"VEN_([0-9A-F]{4})", device, re.IGNORECASE)
        build = _PCI_VENDORS.get(vendor.group(1).upper()) if vendor else None
        if build == "intel" and not re.search(r"\bArc\b", name, re.IGNORECASE):
            continue
        if build:
            builds.add(build)
    return builds


def _rmtree(path: Path) -> None:
    """Efface un dossier sans lever d'erreur, fichiers en lecture seule compris :
    sous Windows, shutil.rmtree laisse les packs de ComfyUI/.git."""

    def make_writable(func, target, _exc):
        try:
            os.chmod(target, stat.S_IWRITE)
            func(target)
        except OSError:
            pass

    if sys.version_info >= (3, 12):
        shutil.rmtree(path, onexc=make_writable)  # pylint: disable=unexpected-keyword-arg
    else:
        shutil.rmtree(path, onerror=make_writable)  # pylint: disable=deprecated-argument


class ComfyUISetupError(Exception):
    """Erreur durant l'installation/lancement automatique de ComfyUI."""


class ComfyUIManager:
    """Installe, lance et surveille une instance ComfyUI portable locale."""

    def __init__(self, host: str = "127.0.0.1", port: int = 8188, root: Optional[Path] = None):
        self.host = host
        self.port = port
        self.base_url = f"http://{host}:{port}"

        # Dossier de My_AI : tools/ et logs/ (un dossier temporaire dans les tests)
        root = root or Path(__file__).resolve().parent.parent
        self._tools_dir = root / "tools"
        self._portable_dir = self._tools_dir / "ComfyUI_windows_portable"
        # Build remplacé par celui du GPU, effacé en arrière-plan
        self._old_dir = self._tools_dir / "ComfyUI_windows_portable.old"
        self._cleaner: Optional[threading.Thread] = None
        # Sortie de ComfyUI : dit pourquoi il s'arrête au démarrage
        self.log_path = root / "logs" / "comfyui.log"
        self._process: Optional[subprocess.Popen] = None
        self._on_cpu = False  # le process lancé tourne sur le CPU
        self._force_cpu = False  # le GPU s'est arrêté au démarrage dans cette session
        self._gpus: Optional[Set[str]] = None
        self._gpus_known = False

        # Sources (surchargées par config.yaml → image_generation.*) ;
        # {build} : nvidia, amd ou intel selon le GPU
        self._portable_url = (
            "https://github.com/comfyanonymous/ComfyUI/releases/latest/download/"
            "ComfyUI_windows_portable_{build}.7z"
        )
        # Checkpoint par défaut : SD-Turbo (rapide, ~5 Go, OK pour 6 Go VRAM)
        self._model_url = (
            "https://huggingface.co/stabilityai/sd-turbo/resolve/main/"
            "sd_turbo.safetensors"
        )
        self._model_filename = "sd_turbo.safetensors"
        self._load_config()

    def _load_config(self) -> None:
        try:
            from core.config import get_config

            c = get_config()
            self._portable_url = str(
                c.get("image_generation.comfyui_portable_url", self._portable_url)
            )
            self._model_url = str(
                c.get("image_generation.comfyui_model_url", self._model_url)
            )
            self._model_filename = str(
                c.get("image_generation.comfyui_model_filename", self._model_filename)
            )
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Chemins internes du portable
    # ------------------------------------------------------------------

    @property
    def _python_exe(self) -> Path:
        return self._portable_dir / "python_embeded" / "python.exe"

    @property
    def _comfyui_main(self) -> Path:
        return self._portable_dir / "ComfyUI" / "main.py"

    @property
    def _checkpoints_dir(self) -> Path:
        return self._portable_dir / "ComfyUI" / "models" / "checkpoints"

    # ------------------------------------------------------------------
    # État
    # ------------------------------------------------------------------

    @staticmethod
    def is_supported() -> bool:
        """Les builds portables auto-gérés n'existent que pour Windows."""
        return sys.platform == "win32"

    def is_installed(self) -> bool:
        return self._python_exe.exists() and self._comfyui_main.exists()

    def has_model(self) -> bool:
        d = self._checkpoints_dir
        if not d.exists():
            return False
        return any(
            p.suffix.lower() in (".safetensors", ".ckpt") for p in d.iterdir()
        )

    def is_responding(self) -> bool:
        try:
            r = requests.get(f"{self.base_url}/system_stats", timeout=3)
            return r.status_code == 200
        except Exception:
            return False

    def is_running(self) -> bool:
        return self._process is not None and self._process.poll() is None

    def installed_build(self) -> Optional[str]:
        """Build installé (nvidia, amd, intel), d'après le lanceur livré à sa racine."""
        for build in BUILDS:
            if (self._portable_dir / f"run_{build}_gpu.bat").exists():
                return build
        return None

    def gpu_builds(self) -> Optional[Set[str]]:
        """detect_gpu_builds, gardé pour la session (PowerShell : ~1 s)."""
        if not self._gpus_known:
            self._gpus = detect_gpu_builds()
            self._gpus_known = True
        return self._gpus

    def wanted_build(self) -> str:
        """Build à installer : celui du GPU, sinon nvidia (sur le CPU)."""
        gpus = self.gpu_builds() or set()
        return next((build for build in BUILDS if build in gpus), "nvidia")

    def _needs_other_build(self) -> bool:
        """Le build installé ne sait pas utiliser le GPU de la machine, qui en a un."""
        installed, gpus = self.installed_build(), self.gpu_builds()
        return bool(installed and gpus) and installed not in gpus

    def _gpu_usable(self) -> bool:
        """Lancer sur le GPU ? Oui dans le doute : un arrêt au démarrage relance sur le CPU."""
        installed, gpus = self.installed_build(), self.gpu_builds()
        return installed is None or gpus is None or installed in gpus

    def _exited(self) -> bool:
        """Le process lancé s'est arrêté."""
        return self._process is not None and self._process.poll() is not None

    # ------------------------------------------------------------------
    # Pipeline complet
    # ------------------------------------------------------------------

    def ensure_running(
        self,
        on_progress: Optional[ProgressCallback] = None,
        is_interrupted: Optional[InterruptCallback] = None,
    ) -> bool:
        """Garantit qu'une instance ComfyUI répond, en installant/lançant au besoin.

        Retourne True quand ComfyUI répond. Lève ComfyUISetupError sur erreur
        fatale (avec message utilisateur clair).
        """

        def _prog(f, m):
            if on_progress:
                try:
                    on_progress(f, m)
                except Exception:
                    pass

        def _check_interrupt():
            if is_interrupted and is_interrupted():
                raise ComfyUISetupError("__interrupted__")

        # Déjà en route ?
        if self.is_responding():
            return True

        if not self.is_supported():
            raise ComfyUISetupError(
                "L'auto-installation de ComfyUI portable est réservée à Windows. "
                "Installe ComfyUI ou AUTOMATIC1111/Forge manuellement "
                "(voir docs/IMAGE_GENERATION.md)."
            )

        # 1. Installation du portable, ou du build qui sait utiliser le GPU
        if not self.is_installed():
            _prog(0.02, "Préparation de l'installation de ComfyUI…")
            self._install(_prog, _check_interrupt)
        elif not self.is_running() and self._needs_other_build():
            self._switch_build(_prog, _check_interrupt)
        self._clean_old_build()

        # 2. Modèle par défaut
        if not self.has_model():
            self._download_model(_prog, _check_interrupt)

        # 3. Lancement + attente
        _check_interrupt()
        if not self.is_running():
            _prog(0.9, "Démarrage de ComfyUI…")
            self.start(cpu=self._force_cpu or not self._gpu_usable())
        ok = self.wait_until_ready(on_progress=_prog, check=_check_interrupt)
        if not ok and self._exited() and not self._on_cpu:
            # Le GPU n'a pas pu servir (pilote, carte non prise en charge) : CPU
            print(
                f"⚠️ [ComfyUI] Arrêt au démarrage sur le GPU ({self._log_excerpt()}) "
                "→ relance sur le CPU"
            )
            self._force_cpu = True
            self.start(cpu=True)
            ok = self.wait_until_ready(on_progress=_prog, check=_check_interrupt)
        if not ok:
            raise ComfyUISetupError(self._startup_failure())
        _prog(1.0, "ComfyUI prêt")
        return True

    # ------------------------------------------------------------------
    # 1. Installation (téléchargement + extraction du .7z)
    # ------------------------------------------------------------------

    def _switch_build(self, prog, check) -> None:
        """Passe au build du GPU ; à défaut, le build installé tourne sur le CPU."""
        old, new = self.installed_build(), self.wanted_build()
        print(f"🔄 [ComfyUI] Build {old} installé, GPU {new} : passage au build {new}")
        try:
            self._install(prog, check)
        except ComfyUISetupError as exc:
            if str(exc) == "__interrupted__":
                raise
            print(
                f"⚠️ [ComfyUI] Passage au build {new} échoué ({exc}) : "
                f"le build {old} tourne sur le CPU"
            )

    def _install(self, prog, check) -> None:
        """Télécharge et extrait le build du GPU, à la place de l'installation actuelle."""
        build = self.wanted_build()
        self._tools_dir.mkdir(exist_ok=True)
        archive = self._tools_dir / f"ComfyUI_windows_portable_{build}.7z"

        # Télécharger l'archive (~1,5-2 Go) si pas déjà là
        if not archive.exists():
            self._download_file(
                self._portable_url.replace("{build}", build),
                archive,
                prog,
                check,
                label=f"Téléchargement de ComfyUI ({build})",
                frac_start=0.03,
                frac_end=0.6,
            )

        # Extraire (.7z) à côté, puis mettre en place d'un seul renommage
        staging = self._tools_dir / "ComfyUI_extract"
        _rmtree(staging)
        prog(0.62, "Extraction de ComfyUI…")
        self._extract_7z(archive, staging, prog, check)
        extracted = staging / self._portable_dir.name
        if not (extracted / "python_embeded" / "python.exe").exists():
            raise ComfyUISetupError(
                f"Extraction terminée mais ComfyUI introuvable (attendu : {extracted})."
            )
        prog(0.66, "Mise en place de ComfyUI…")
        self._replace_install(extracted)
        _rmtree(staging)

        # Nettoyage de l'archive pour libérer l'espace disque
        try:
            archive.unlink()
        except Exception:
            pass

    def _replace_install(self, extracted: Path) -> None:
        """Met `extracted` à la place de l'installation actuelle, avec ses modèles."""
        old = self._old_dir
        if self._portable_dir.exists():
            _rmtree(old)  # reste d'un effacement interrompu (appli fermée)
            try:
                self._portable_dir.rename(old)
            except OSError as exc:
                raise ComfyUISetupError(
                    f"Impossible de remplacer {self._portable_dir} : {exc}"
                ) from exc
            # Modèles téléchargés ou ajoutés par l'utilisateur, repris tels quels
            # (même disque : un renommage, même pour un checkpoint de 5 Go)
            new_models = extracted / "ComfyUI" / "models"
            new_models.mkdir(parents=True, exist_ok=True)
            for entry in (old / "ComfyUI" / "models").glob("*"):
                target = new_models / entry.name
                if target.is_dir():
                    shutil.rmtree(target)
                elif target.exists():
                    target.unlink()
                entry.rename(target)
        extracted.rename(self._portable_dir)

    def _clean_old_build(self) -> None:
        """Efface l'ancien build pendant que ComfyUI démarre : des dizaines de
        milliers de fichiers, 4 min avec l'antivirus."""
        if self._old_dir.exists() and not (self._cleaner and self._cleaner.is_alive()):
            self._cleaner = threading.Thread(
                target=_rmtree, args=(self._old_dir,), name="comfyui-old-build", daemon=True
            )
            self._cleaner.start()

    def _extract_7z(self, archive: Path, dest: Path, prog, check) -> None:
        """Extrait l'archive .7z.

        L'archive ComfyUI portable utilise le filtre **BCJ2**, NON supporté par
        py7zr. On utilise donc le vrai 7-Zip : binaire système (`7z`/`7za`/`7zr`)
        s'il existe, sinon téléchargement de `7zr.exe` (standalone, ~600 Ko, gère
        BCJ2). py7zr ne sert que de dernier recours (autres archives).
        """
        check()
        exe = self._ensure_7zip(prog, check)
        if exe is not None:
            prog(0.62, "Extraction de ComfyUI…")
            # 7-Zip : x = extract avec arborescence, -o<dir> = sortie, -y = oui à tout
            proc = subprocess.run(
                [exe, "x", str(archive), f"-o{dest}", "-y"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                creationflags=_NO_WINDOW,
            )
            if proc.returncode != 0:
                err = (proc.stderr or b"").decode("utf-8", "ignore")[:300]
                raise ComfyUISetupError(f"Extraction 7-Zip échouée : {err}")
            return

        # Dernier recours : py7zr (échouera sur BCJ2, mais utile pour d'autres .7z)
        try:
            import py7zr  # type: ignore
        except ImportError:
            prog(0.62, "Installation de l'extracteur (py7zr)…")
            self._pip_install("py7zr")
            import py7zr  # type: ignore
        check()
        with py7zr.SevenZipFile(str(archive), mode="r") as z:
            z.extractall(path=str(dest))

    def _ensure_7zip(self, prog, check) -> Optional[str]:
        """Retourne le chemin d'un exécutable 7-Zip, en téléchargeant 7zr.exe au besoin."""
        # 1. 7-Zip déjà présent (système ou installé précédemment dans tools/)
        for name in ("7z", "7za", "7zr"):
            found = shutil.which(name)
            if found:
                return found
        for cand in (
            self._tools_dir / "7zr.exe",
            Path(r"C:\Program Files\7-Zip\7z.exe"),
            Path(r"C:\Program Files (x86)\7-Zip\7z.exe"),
        ):
            if cand.exists():
                return str(cand)

        # 2. Télécharger le 7-Zip standalone (Windows uniquement)
        if sys.platform != "win32":
            return None
        self._tools_dir.mkdir(exist_ok=True)
        dest = self._tools_dir / "7zr.exe"
        prog(0.61, "Préparation de l'extracteur 7-Zip…")
        try:
            url = "https://www.7-zip.org/a/7zr.exe"
            with requests.get(url, stream=True, timeout=60) as r:
                r.raise_for_status()
                with open(dest, "wb") as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        check()
                        f.write(chunk)
            return str(dest)
        except ComfyUISetupError:
            if dest.exists():
                dest.unlink()
            raise
        except Exception as exc:
            if dest.exists():
                dest.unlink()
            print(f"⚠️ [ComfyUI] Téléchargement de 7zr.exe échoué : {exc}")
            return None

    # ------------------------------------------------------------------
    # 2. Modèle par défaut
    # ------------------------------------------------------------------

    def _download_model(self, prog, check) -> None:
        self._checkpoints_dir.mkdir(parents=True, exist_ok=True)
        dest = self._checkpoints_dir / self._model_filename
        self._download_file(
            self._model_url,
            dest,
            prog,
            check,
            label="Téléchargement du modèle",
            frac_start=0.6,
            frac_end=0.88,
        )

    # ------------------------------------------------------------------
    # 3. Lancement / surveillance
    # ------------------------------------------------------------------

    def start(self, cpu: bool = False) -> None:
        """Lance ComfyUI en sous-processus (sans ouvrir de navigateur), sur le CPU si `cpu`."""
        if self.is_running():
            return
        if not self.is_installed():
            raise ComfyUISetupError("ComfyUI n'est pas installé.")

        cmd = [
            str(self._python_exe),
            "-s",
            str(self._comfyui_main),
            "--port",
            str(self.port),
            "--disable-auto-launch",
        ]
        if cpu:
            cmd.append("--cpu")
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.log_path, "wb") as log:
            self._process = subprocess.Popen(
                cmd,
                cwd=str(self._portable_dir),
                stdout=log,
                stderr=subprocess.STDOUT,
                env=dict(os.environ, PYTHONIOENCODING="utf-8"),
                creationflags=_NO_WINDOW,  # pas de fenêtre console
            )
        self._on_cpu = cpu
        device = "CPU" if cpu else f"GPU, build {self.installed_build()}"
        print(f"🚀 [ComfyUI] Lancé (PID {self._process.pid}) sur {self.base_url} ({device})")

    def wait_until_ready(
        self,
        timeout: int = _STARTUP_TIMEOUT,
        on_progress: Optional[ProgressCallback] = None,
        check: Optional[Callable[[], None]] = None,
    ) -> bool:
        start = time.time()
        deadline = start + timeout
        while time.time() < deadline:
            if check:
                check()
            # Le process est mort prématurément ?
            if self._exited():
                return False
            if self.is_responding():
                return True
            if on_progress:
                mode = " sur le CPU" if self._on_cpu else ""
                on_progress(0.93, f"Démarrage de ComfyUI{mode}… ({int(time.time() - start)}s)")
            time.sleep(1.5)
        return False

    def _startup_failure(self) -> str:
        """Message d'échec du démarrage : la dernière erreur de ComfyUI et son journal."""
        if self._exited():
            return (
                f"ComfyUI s'est arrêté au démarrage ({self._log_excerpt()}). "
                f"Journal : {self.log_path}"
            )
        return (
            f"ComfyUI ne répond pas après {_STARTUP_TIMEOUT // 60} min. Réessaie, ou "
            "lance-le manuellement via tools/ComfyUI_windows_portable. "
            f"Journal : {self.log_path}"
        )

    def _log_excerpt(self) -> str:
        """Dernière ligne d'erreur du journal de ComfyUI, sinon sa dernière ligne."""
        try:
            text = self.log_path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return "journal illisible"
        lines = [_ANSI.sub("", line).strip() for line in text.splitlines()]
        lines = [line for line in lines if line]
        errors = [line for line in lines if _ERROR_LINE.search(line)]
        return (errors or lines or ["aucune sortie"])[-1][:200]

    def stop(self) -> None:
        if self._process is not None:
            try:
                self._process.terminate()
            except Exception:
                pass
            self._process = None

    # ------------------------------------------------------------------
    # Utilitaires
    # ------------------------------------------------------------------

    def _download_file(
        self,
        url: str,
        dest: Path,
        prog,
        check,
        label: str,
        frac_start: float,
        frac_end: float,
    ) -> None:
        """Télécharge un fichier en streaming avec progression et reprise propre."""
        tmp = dest.with_suffix(dest.suffix + ".part")
        try:
            with requests.get(url, stream=True, timeout=60) as r:
                r.raise_for_status()
                total = int(r.headers.get("content-length", 0) or 0)
                done = 0
                last_emit = 0.0
                with open(tmp, "wb") as f:
                    for chunk in r.iter_content(chunk_size=1024 * 256):
                        check()
                        if not chunk:
                            continue
                        f.write(chunk)
                        done += len(chunk)
                        now = time.time()
                        if total and (now - last_emit) > 0.4:
                            last_emit = now
                            ratio = done / total
                            frac = frac_start + ratio * (frac_end - frac_start)
                            mb = done / (1024 * 1024)
                            tot_mb = total / (1024 * 1024)
                            prog(frac, f"{label}… {int(ratio * 100)}% ({mb:.0f}/{tot_mb:.0f} Mo)")
            tmp.replace(dest)
        except ComfyUISetupError:
            # Interruption : nettoyer le partiel
            if tmp.exists():
                tmp.unlink()
            raise
        except Exception as exc:
            if tmp.exists():
                tmp.unlink()
            raise ComfyUISetupError(f"{label} échoué : {exc}")

    @staticmethod
    def _pip_install(package: str) -> None:
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "--quiet", package]
        )


_GLOBAL_MANAGER: Optional[ComfyUIManager] = None


def get_comfyui_manager() -> ComfyUIManager:
    """Retourne l'instance globale du gestionnaire ComfyUI portable."""
    global _GLOBAL_MANAGER
    if _GLOBAL_MANAGER is None:
        # Aligner le port sur la config image_generation.comfyui_url si présente.
        host, port = "127.0.0.1", 8188
        try:
            from core.config import get_config
            from urllib.parse import urlparse

            url = get_config().get("image_generation.comfyui_url", "")
            if url:
                p = urlparse(url)
                host = p.hostname or host
                port = p.port or port
        except Exception:
            pass
        _GLOBAL_MANAGER = ComfyUIManager(host=host, port=port)
    return _GLOBAL_MANAGER
