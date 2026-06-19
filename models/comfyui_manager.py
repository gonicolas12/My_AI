"""
Gestionnaire ComfyUI portable auto-géré (backend de génération d'image).

Au premier besoin de génération d'image, si aucun backend n'est détecté et que
`image_generation.auto_setup` est actif, ce module :
  1. télécharge **ComfyUI portable** (build NVIDIA, Python+CUDA EMBARQUÉS — il
     n'altère PAS l'environnement Python de My_AI) dans `tools/`,
  2. l'extrait (archive .7z),
  3. télécharge un checkpoint Stable Diffusion par défaut (si aucun présent),
  4. lance ComfyUI en sous-processus et attend qu'il réponde sur localhost:8188.

Tout est piloté par des callbacks de progression pour alimenter l'animation
« Génération en cours » du GUI, et interruptible (bouton STOP). Même esprit que
le téléchargement automatique de cloudflared pour le tunnel Relay.

⚠️ Le build portable est **Windows / NVIDIA**. Sur les autres plateformes, on
laisse l'utilisateur installer ComfyUI/Forge lui-même (message clair).
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Callable, Optional

import requests

ProgressCallback = Callable[[float, str], None]
InterruptCallback = Callable[[], bool]


class ComfyUISetupError(Exception):
    """Erreur durant l'installation/lancement automatique de ComfyUI."""


class ComfyUIManager:
    """Installe, lance et surveille une instance ComfyUI portable locale."""

    def __init__(self, host: str = "127.0.0.1", port: int = 8188):
        self.host = host
        self.port = port
        self.base_url = f"http://{host}:{port}"

        self._tools_dir = Path(__file__).resolve().parent.parent / "tools"
        self._portable_dir = self._tools_dir / "ComfyUI_windows_portable"
        self._process: Optional[subprocess.Popen] = None

        # Sources (surchargées par config.yaml → image_generation.*)
        self._portable_url = (
            "https://github.com/comfyanonymous/ComfyUI/releases/latest/download/"
            "ComfyUI_windows_portable_nvidia.7z"
        )
        # Checkpoint par défaut : SD-Turbo (rapide, ~2.5 Go, OK pour 6 Go VRAM)
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
        """Le build portable auto-géré n'existe que pour Windows/NVIDIA."""
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

    # ------------------------------------------------------------------
    # Pipeline complet
    # ------------------------------------------------------------------

    def ensure_running(
        self,
        on_progress: Optional[ProgressCallback] = None,
        is_interrupted: Optional[InterruptCallback] = None,
    ) -> bool:
        """Garantit qu'une instance ComfyUI répond, en installant/lançant au besoin.

        Retourne True si ComfyUI répond à la fin, False sinon. Lève
        ComfyUISetupError sur erreur fatale (avec message utilisateur clair).
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
                "L'auto-installation de ComfyUI portable est réservée à Windows/NVIDIA. "
                "Installe ComfyUI ou AUTOMATIC1111/Forge manuellement "
                "(voir docs/IMAGE_GENERATION.md)."
            )

        # 1. Installation du portable
        if not self.is_installed():
            _prog(0.02, "Préparation de l'installation de ComfyUI…")
            self._ensure_installed(_prog, _check_interrupt)

        # 2. Modèle par défaut
        if not self.has_model():
            self._download_model(_prog, _check_interrupt)

        # 3. Lancement + attente
        _check_interrupt()
        if not self.is_running():
            _prog(0.9, "Démarrage de ComfyUI…")
            self.start()
        ok = self.wait_until_ready(timeout=180, on_progress=_prog, check=_check_interrupt)
        if not ok:
            raise ComfyUISetupError(
                "ComfyUI a été installé mais ne répond pas. Réessaie, ou lance-le "
                "manuellement via tools/ComfyUI_windows_portable."
            )
        _prog(1.0, "ComfyUI prêt")
        return True

    # ------------------------------------------------------------------
    # 1. Installation (téléchargement + extraction du .7z)
    # ------------------------------------------------------------------

    def _ensure_installed(self, prog, check) -> None:
        self._tools_dir.mkdir(exist_ok=True)
        archive = self._tools_dir / "ComfyUI_windows_portable_nvidia.7z"

        # Télécharger l'archive (~2-2.5 Go) si pas déjà là
        if not archive.exists():
            self._download_file(
                self._portable_url,
                archive,
                prog,
                check,
                label="Téléchargement de ComfyUI",
                frac_start=0.03,
                frac_end=0.6,
            )

        # Extraire (.7z → py7zr)
        prog(0.62, "Extraction de ComfyUI…")
        self._extract_7z(archive, self._tools_dir, prog, check)

        if not self.is_installed():
            raise ComfyUISetupError(
                "Extraction terminée mais ComfyUI introuvable "
                f"(attendu : {self._portable_dir})."
            )

        # Nettoyage de l'archive pour libérer l'espace disque
        try:
            archive.unlink()
        except Exception:
            pass

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
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
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
        import shutil

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

    def start(self) -> None:
        """Lance ComfyUI en sous-processus (sans ouvrir de navigateur)."""
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
        creationflags = 0
        if sys.platform == "win32":
            # Pas de fenêtre console
            creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)

        self._process = subprocess.Popen(
            cmd,
            cwd=str(self._portable_dir),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=creationflags,
        )
        print(f"🚀 [ComfyUI] Lancé (PID {self._process.pid}) sur {self.base_url}")

    def wait_until_ready(
        self,
        timeout: int = 180,
        on_progress: Optional[ProgressCallback] = None,
        check: Optional[Callable[[], None]] = None,
    ) -> bool:
        deadline = time.time() + timeout
        while time.time() < deadline:
            if check:
                check()
            # Le process est mort prématurément ?
            if self._process is not None and self._process.poll() is not None:
                return False
            if self.is_responding():
                return True
            if on_progress:
                elapsed = timeout - (deadline - time.time())
                on_progress(0.93, f"Démarrage de ComfyUI… ({int(elapsed)}s)")
            time.sleep(1.5)
        return False

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
