"""
Génération d'images locale (texte → image), 100% offline.

Ferme la symétrie multimodale du projet : l'ENTRÉE vision existe déjà
(models/local_llm.py → describe_image via Ollama minicpm-v/llava), ce module
ajoute la SORTIE image.

Architecture calquée sur LocalLLM : on parle à un backend Stable Diffusion
local en HTTP (localhost), avec détection de disponibilité et *dégradation
propre* (message clair si aucun backend, comme le fallback Ollama). Le backend
est configurable via config.yaml → section "image_generation:".

Backends supportés :
  - "automatic1111" : API AUTOMATIC1111 / Forge WebUI (/sdapi/v1/txt2img)
                      → backend par défaut, calque exact du pattern Ollama.
  - "comfyui"       : API ComfyUI (/prompt + /history) — workflow par graphe.
  - "diffusers"     : pipeline diffusers en process (optionnel, deps lourdes).
  - "auto"          : essaie automatic1111 puis comfyui (puis diffusers si dispo).

Aucune dépendance n'est ajoutée au requirements de base : les backends HTTP
n'utilisent que `requests` (déjà présent) ; diffusers reste optionnel.
"""

from __future__ import annotations

import base64
import importlib.util
import io
import os
import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, Optional

import requests

from core.config import get_config

# NB : torch / diffusers / torch_directml sont des dépendances OPTIONNELLES
# (backend "diffusers" uniquement). Elles sont importées PARESSEUSEMENT dans les
# méthodes concernées pour ne pas casser l'import du module quand elles sont
# absentes (cas par défaut : backends HTTP A1111/ComfyUI).

# [OPTIM] Retry résilient (réutilise tenacity si présent, comme local_llm.py)
try:
    from tenacity import (retry, retry_if_exception_type, stop_after_attempt,
                          wait_exponential)

    TENACITY_AVAILABLE = True
except ImportError:
    TENACITY_AVAILABLE = False


# Callback de progression : reçoit (fraction_0_1, message) pour l'indicateur UI.
ProgressCallback = Callable[[float, str], None]


class _GenerationInterrupted(Exception):
    """Signal interne : l'utilisateur a annulé la génération (bouton STOP)."""


@dataclass
class ImageGenConfig:
    """Configuration de la génération d'images (lue depuis config.yaml)."""

    enabled: bool = True
    backend: str = "automatic1111"  # auto | automatic1111 | comfyui | diffusers
    # Endpoints HTTP des backends locaux
    automatic1111_url: str = "http://127.0.0.1:7860"
    comfyui_url: str = "http://127.0.0.1:8188"
    # Paramètres de génération par défaut
    width: int = 512
    height: int = 512
    steps: int = 25
    cfg_scale: float = 7.0
    sampler: str = "DPM++ 2M Karras"
    negative_prompt: str = (
        "lowres, bad anatomy, bad hands, text, error, missing fingers, "
        "extra digit, fewer digits, cropped, worst quality, low quality, "
        "jpeg artifacts, signature, watermark, blurry"
    )
    # Modèle diffusers (utilisé seulement si backend diffusers)
    diffusers_model: str = "stabilityai/sd-turbo"
    # Répertoire de sortie (cohérent avec generation.output_directory)
    output_directory: str = "outputs"
    # Timeout d'une génération (s) — une image peut être lente sur petite VRAM
    timeout: int = 300

    @classmethod
    def from_config(cls) -> "ImageGenConfig":
        """Construit la config depuis config.yaml (section image_generation)."""
        cfg = cls()
        try:
            c = get_config()
            cfg.enabled = bool(c.get("image_generation.enabled", cfg.enabled))
            cfg.backend = str(c.get("image_generation.backend", cfg.backend))
            cfg.automatic1111_url = str(
                c.get("image_generation.automatic1111_url", cfg.automatic1111_url)
            ).rstrip("/")
            cfg.comfyui_url = str(
                c.get("image_generation.comfyui_url", cfg.comfyui_url)
            ).rstrip("/")
            cfg.width = int(c.get("image_generation.width", cfg.width))
            cfg.height = int(c.get("image_generation.height", cfg.height))
            cfg.steps = int(c.get("image_generation.steps", cfg.steps))
            cfg.cfg_scale = float(c.get("image_generation.cfg_scale", cfg.cfg_scale))
            cfg.sampler = str(c.get("image_generation.sampler", cfg.sampler))
            cfg.negative_prompt = str(
                c.get("image_generation.negative_prompt", cfg.negative_prompt)
            )
            cfg.diffusers_model = str(
                c.get("image_generation.diffusers_model", cfg.diffusers_model)
            )
            cfg.output_directory = str(
                c.get("generation.output_directory", cfg.output_directory)
            )
            cfg.timeout = int(c.get("image_generation.timeout", cfg.timeout))
        except Exception as exc:  # pragma: no cover - config best-effort
            print(f"⚠️ [ImageGen] Lecture config échouée, valeurs par défaut : {exc}")
        return cfg


@dataclass
class ImageGenResult:
    """Résultat d'une génération d'image."""

    success: bool
    image_path: Optional[str] = None  # chemin absolu du PNG sauvegardé
    message: str = ""  # message destiné à l'utilisateur (markdown)
    backend: str = ""
    error: Optional[str] = None
    interrupted: bool = False  # True si annulé par l'utilisateur (bouton STOP)
    info: Dict[str, Any] = field(default_factory=dict)


class ImageGenerator:
    """
    Générateur d'images local avec backend configurable et fallback gracieux.

    Usage :
        gen = ImageGenerator()
        if gen.is_available():
            result = gen.generate("un chat astronaute, style aquarelle",
                                   on_progress=lambda f, m: print(f, m))
            if result.success:
                print(result.image_path)
        else:
            print(gen.unavailable_message())
    """

    def __init__(self, config: Optional[ImageGenConfig] = None):
        self.config = config or ImageGenConfig.from_config()
        # Backend effectivement utilisable (résolu paresseusement)
        self._resolved_backend: Optional[str] = None
        self._last_probe: float = 0.0
        self._probe_ttl: float = 30.0  # re-sonder au plus toutes les 30 s
        # Pipeline diffusers chargé paresseusement (backend "diffusers")
        self._diffusers_pipe: Any = None
        self._diffusers_device: Any = None

    # ------------------------------------------------------------------
    # Disponibilité / détection de backend
    # ------------------------------------------------------------------

    def is_available(self) -> bool:
        """True si au moins un backend de génération d'image répond."""
        return self.resolve_backend() is not None

    def resolve_backend(self, force: bool = False) -> Optional[str]:
        """
        Détermine le backend disponible selon la config.
        Met en cache le résultat pendant `_probe_ttl` secondes pour éviter de
        sonder le réseau à chaque message.
        """
        if not self.config.enabled:
            return None

        now = time.time()
        if (
            not force
            and self._resolved_backend is not None
            and (now - self._last_probe) < self._probe_ttl
        ):
            return self._resolved_backend

        self._last_probe = now
        backend = self.config.backend.lower().strip()

        if backend == "auto":
            order = ["automatic1111", "comfyui", "diffusers"]
        else:
            order = [backend]

        for b in order:
            if self._probe_backend(b):
                self._resolved_backend = b
                return b

        self._resolved_backend = None
        return None

    def _probe_backend(self, backend: str) -> bool:
        """Teste rapidement si un backend donné est joignable."""
        try:
            if backend == "automatic1111":
                r = requests.get(
                    f"{self.config.automatic1111_url}/sdapi/v1/sd-models", timeout=3
                )
                return r.status_code == 200
            if backend == "comfyui":
                r = requests.get(
                    f"{self.config.comfyui_url}/system_stats", timeout=3
                )
                return r.status_code == 200
            if backend == "diffusers":

                return (
                    importlib.util.find_spec("diffusers") is not None
                    and importlib.util.find_spec("torch") is not None
                )
        except Exception:
            return False
        return False

    def unavailable_message(self) -> str:
        """Message clair de dégradation propre (style fallback Ollama)."""
        return (
            "🎨 **Génération d'image indisponible**\n\n"
            "Aucun backend de génération d'image local n'a été détecté. "
            "Pour activer cette fonctionnalité 100 % hors-ligne, lance l'un de ces "
            "services en local :\n\n"
            "- **Stable Diffusion WebUI (AUTOMATIC1111 / Forge)** — recommandé — "
            "démarré avec l'option `--api` (écoute sur "
            f"`{self.config.automatic1111_url}`). Forge est conseillé sur une petite "
            "VRAM (ajoute `--medvram`).\n"
            "- **ComfyUI** sur "
            f"`{self.config.comfyui_url}`.\n\n"
            "Le backend est configurable dans `config.yaml` → section "
            "`image_generation:`."
        )

    # ------------------------------------------------------------------
    # Génération
    # ------------------------------------------------------------------

    def generate(
        self,
        prompt: str,
        negative_prompt: Optional[str] = None,
        width: Optional[int] = None,
        height: Optional[int] = None,
        steps: Optional[int] = None,
        on_progress: Optional[ProgressCallback] = None,
        is_interrupted: Optional[Callable[[], bool]] = None,
    ) -> ImageGenResult:
        """
        Génère une image depuis un prompt texte.

        Args:
            prompt:        Description de l'image souhaitée.
            negative_prompt: Prompt négatif (sinon défaut config).
            width/height/steps: Surchargent la config si fournis.
            on_progress:   Callback(fraction_0_1, message) pour l'indicateur UI.
            is_interrupted: Callback() -> bool pour annuler la génération.

        Returns:
            ImageGenResult (success, image_path, message, ...).
        """
        backend = self.resolve_backend()
        if backend is None:
            return ImageGenResult(
                success=False,
                message=self.unavailable_message(),
                error="no_backend",
            )

        prompt = (prompt or "").strip()
        if not prompt:
            return ImageGenResult(
                success=False,
                message="🎨 Précise ce que tu veux que je dessine.",
                error="empty_prompt",
            )

        if on_progress:
            try:
                on_progress(0.02, f"Initialisation ({backend})…")
            except Exception:
                pass

        params = {
            "prompt": prompt,
            "negative_prompt": negative_prompt or self.config.negative_prompt,
            "width": width or self.config.width,
            "height": height or self.config.height,
            "steps": steps or self.config.steps,
        }

        try:
            if backend == "automatic1111":
                png_bytes = self._generate_automatic1111(
                    params, on_progress, is_interrupted
                )
            elif backend == "comfyui":
                png_bytes = self._generate_comfyui(params, on_progress, is_interrupted)
            elif backend == "diffusers":
                png_bytes = self._generate_diffusers(params, on_progress, is_interrupted)
            else:
                return ImageGenResult(
                    success=False,
                    message=self.unavailable_message(),
                    error="unknown_backend",
                )
        except _GenerationInterrupted:
            return ImageGenResult(
                success=False,
                backend=backend,
                interrupted=True,
                error="interrupted",
                message="⏹️ Génération de l'image interrompue.",
            )
        except requests.exceptions.Timeout:
            return ImageGenResult(
                success=False,
                backend=backend,
                error="timeout",
                message=(
                    f"⚠️ La génération a dépassé le délai de {self.config.timeout}s. "
                    "Réduis la taille/le nombre d'étapes, ou vérifie le backend."
                ),
            )
        except Exception as exc:
            return ImageGenResult(
                success=False,
                backend=backend,
                error=str(exc),
                message=f"⚠️ Échec de la génération d'image : {exc}",
            )

        # L'utilisateur a pu annuler pendant que le backend finissait sa requête.
        if is_interrupted and is_interrupted():
            return ImageGenResult(
                success=False,
                backend=backend,
                interrupted=True,
                error="interrupted",
                message="⏹️ Génération de l'image interrompue.",
            )

        if not png_bytes:
            return ImageGenResult(
                success=False,
                backend=backend,
                error="empty_result",
                message="⚠️ Le backend n'a renvoyé aucune image.",
            )

        path = self._save_png(png_bytes, prompt)
        if on_progress:
            try:
                on_progress(1.0, "Terminé")
            except Exception:
                pass

        return ImageGenResult(
            success=True,
            image_path=path,
            backend=backend,
            message=f"Voici l'image générée pour : **{prompt}**",
            info={"prompt": prompt, **params},
        )

    # ------------------------------------------------------------------
    # Backend : AUTOMATIC1111 / Forge WebUI
    # ------------------------------------------------------------------

    def _generate_automatic1111(
        self,
        params: Dict[str, Any],
        on_progress: Optional[ProgressCallback],
        is_interrupted: Optional[Callable[[], bool]],
    ) -> Optional[bytes]:
        """Appelle /sdapi/v1/txt2img et sonde /sdapi/v1/progress en parallèle."""
        url = f"{self.config.automatic1111_url}/sdapi/v1/txt2img"
        payload = {
            "prompt": params["prompt"],
            "negative_prompt": params["negative_prompt"],
            "width": params["width"],
            "height": params["height"],
            "steps": params["steps"],
            "cfg_scale": self.config.cfg_scale,
            "sampler_name": self.config.sampler,
            "batch_size": 1,
            "n_iter": 1,
        }

        # Thread de polling de progression (A1111 expose une jauge globale) qui
        # sert aussi à détecter l'annulation utilisateur et à interrompre le
        # backend via /sdapi/v1/interrupt (sinon le POST txt2img reste bloquant).
        stop_poll = {"stop": False, "interrupted": False}
        def _poll():
            while not stop_poll["stop"]:
                if is_interrupted and is_interrupted():
                    stop_poll["interrupted"] = True
                    try:
                        requests.post(
                            f"{self.config.automatic1111_url}/sdapi/v1/interrupt",
                            timeout=5,
                        )
                    except Exception:
                        pass
                    break
                try:
                    pr = requests.get(
                        f"{self.config.automatic1111_url}/sdapi/v1/progress",
                        params={"skip_current_image": "true"},
                        timeout=5,
                    )
                    if pr.status_code == 200 and on_progress:
                        data = pr.json()
                        frac = float(data.get("progress", 0.0) or 0.0)
                        eta = data.get("eta_relative", 0.0) or 0.0
                        # Mapper 0..1 → 0.05..0.95 (réserver le début/fin)
                        mapped = 0.05 + min(max(frac, 0.0), 1.0) * 0.9
                        msg = (
                            f"Génération… {int(frac * 100)}%"
                            + (f" (≈{eta:.0f}s)" if eta else "")
                        )
                        try:
                            on_progress(mapped, msg)
                        except Exception:
                            pass
                except Exception:
                    pass
                time.sleep(0.5)

        t = threading.Thread(target=_poll, daemon=True)
        t.start()

        try:
            resp = self._post(url, json=payload, timeout=self.config.timeout)
        finally:
            stop_poll["stop"] = True

        if stop_poll["interrupted"] or (is_interrupted and is_interrupted()):
            raise _GenerationInterrupted()

        if resp.status_code != 200:
            raise RuntimeError(f"HTTP {resp.status_code} : {resp.text[:200]}")

        data = resp.json()
        images = data.get("images") or []
        if not images:
            return None
        # A1111 renvoie du base64 (parfois préfixé "data:image/png;base64,")
        b64 = images[0].split(",", 1)[-1]
        return base64.b64decode(b64)

    # ------------------------------------------------------------------
    # Backend : ComfyUI
    # ------------------------------------------------------------------

    def _generate_comfyui(
        self,
        params: Dict[str, Any],
        on_progress: Optional[ProgressCallback],
        is_interrupted: Optional[Callable[[], bool]],
    ) -> Optional[bytes]:
        """
        Soumet un workflow txt2img minimal à ComfyUI puis récupère l'image.
        Utilise le checkpoint par défaut chargé côté ComfyUI.
        """
        base = self.config.comfyui_url
        client_id = uuid.uuid4().hex

        # Récupérer un checkpoint disponible
        ckpt = self._comfyui_default_checkpoint(base)
        if not ckpt:
            raise RuntimeError("Aucun checkpoint trouvé côté ComfyUI.")

        seed = int.from_bytes(os.urandom(4), "big")
        workflow = {
            "3": {
                "class_type": "KSampler",
                "inputs": {
                    "seed": seed,
                    "steps": params["steps"],
                    "cfg": self.config.cfg_scale,
                    "sampler_name": "dpmpp_2m",
                    "scheduler": "karras",
                    "denoise": 1.0,
                    "model": ["4", 0],
                    "positive": ["6", 0],
                    "negative": ["7", 0],
                    "latent_image": ["5", 0],
                },
            },
            "4": {
                "class_type": "CheckpointLoaderSimple",
                "inputs": {"ckpt_name": ckpt},
            },
            "5": {
                "class_type": "EmptyLatentImage",
                "inputs": {
                    "width": params["width"],
                    "height": params["height"],
                    "batch_size": 1,
                },
            },
            "6": {
                "class_type": "CLIPTextEncode",
                "inputs": {"text": params["prompt"], "clip": ["4", 1]},
            },
            "7": {
                "class_type": "CLIPTextEncode",
                "inputs": {"text": params["negative_prompt"], "clip": ["4", 1]},
            },
            "8": {
                "class_type": "VAEDecode",
                "inputs": {"samples": ["3", 0], "vae": ["4", 2]},
            },
            "9": {
                "class_type": "SaveImage",
                "inputs": {"filename_prefix": "MyAI", "images": ["8", 0]},
            },
        }

        if on_progress:
            on_progress(0.1, "Soumission du workflow ComfyUI…")

        resp = self._post(
            f"{base}/prompt",
            json={"prompt": workflow, "client_id": client_id},
            timeout=30,
        )
        if resp.status_code != 200:
            raise RuntimeError(f"HTTP {resp.status_code} : {resp.text[:200]}")
        prompt_id = resp.json().get("prompt_id")
        if not prompt_id:
            raise RuntimeError("Pas de prompt_id renvoyé par ComfyUI.")

        # Polling de l'historique jusqu'à complétion
        deadline = time.time() + self.config.timeout
        while time.time() < deadline:
            if is_interrupted and is_interrupted():
                try:
                    requests.post(f"{base}/interrupt", timeout=5)
                except Exception:
                    pass
                raise _GenerationInterrupted()
            try:
                h = requests.get(f"{base}/history/{prompt_id}", timeout=5)
                if h.status_code == 200:
                    hist = h.json().get(prompt_id)
                    if hist and hist.get("outputs"):
                        img_info = self._comfyui_first_image(hist["outputs"])
                        if img_info:
                            if on_progress:
                                on_progress(0.95, "Récupération de l'image…")
                            img = requests.get(
                                f"{base}/view", params=img_info, timeout=30
                            )
                            if img.status_code == 200:
                                return img.content
            except Exception:
                pass
            if on_progress:
                on_progress(0.5, "Génération ComfyUI en cours…")
            time.sleep(1.0)
        raise requests.exceptions.Timeout()

    @staticmethod
    def _comfyui_first_image(outputs: Dict[str, Any]) -> Optional[Dict[str, str]]:
        for node in outputs.values():
            for img in node.get("images", []) or []:
                return {
                    "filename": img.get("filename", ""),
                    "subfolder": img.get("subfolder", ""),
                    "type": img.get("type", "output"),
                }
        return None

    def _comfyui_default_checkpoint(self, base: str) -> Optional[str]:
        try:
            r = requests.get(f"{base}/object_info/CheckpointLoaderSimple", timeout=5)
            if r.status_code == 200:
                info = r.json()
                ckpts = (
                    info.get("CheckpointLoaderSimple", {})
                    .get("input", {})
                    .get("required", {})
                    .get("ckpt_name", [[]])
                )
                if ckpts and ckpts[0]:
                    return ckpts[0][0]
        except Exception:
            pass
        return None

    # ------------------------------------------------------------------
    # Backend : diffusers (optionnel, en process)
    # ------------------------------------------------------------------

    def _generate_diffusers(
        self,
        params: Dict[str, Any],
        on_progress: Optional[ProgressCallback],
        is_interrupted: Optional[Callable[[], bool]] = None,
    ) -> Optional[bytes]:
        """
        Pipeline diffusers local. Déconseillé sur petite VRAM partagée avec
        Ollama, mais fourni pour le mode 100% pip. Charge le pipeline une fois.
        """
        # Imports paresseux (dépendances optionnelles du backend diffusers).
        # pylint: disable=import-error,import-outside-toplevel
        import torch  # type: ignore
        from diffusers import AutoPipelineForText2Image  # type: ignore
        # pylint: enable=import-error,import-outside-toplevel

        if self._diffusers_pipe is None:
            if on_progress:
                on_progress(0.05, "Chargement du modèle diffusers…")

            device, dtype, label = self._detect_diffusers_device(torch)
            print(f"🎨 [ImageGen] Backend diffusers sur {label} (dtype={dtype})")

            pipe = AutoPipelineForText2Image.from_pretrained(
                self.config.diffusers_model, torch_dtype=dtype
            )

            # DirectML (Windows AMD/Intel) expose un device objet, pas une chaîne.
            try:
                pipe = pipe.to(device)
            except Exception as exc:
                print(f"⚠️ [ImageGen] .to({label}) a échoué ({exc}) → repli CPU")
                device, dtype, label = "cpu", torch.float32, "CPU"
                pipe = AutoPipelineForText2Image.from_pretrained(
                    self.config.diffusers_model, torch_dtype=dtype
                ).to("cpu")

            # Économies mémoire (utile sur toute VRAM, ex. 6 Go partagés avec Ollama).
            if label != "CPU":
                try:
                    pipe.enable_attention_slicing()
                    pipe.enable_vae_slicing()
                except Exception:
                    pass

            self._diffusers_pipe = pipe
            self._diffusers_device = device

        pipe = self._diffusers_pipe

        def _cb(pipe_ref, step: int, _t, _kw):
            # diffusers appelle callback_on_step_end(pipe, step, timestep, kwargs).
            if is_interrupted and is_interrupted():
                try:
                    # arrêt natif diffusers si supporté
                    pipe_ref._interrupt = True  # pylint: disable=protected-access
                except Exception:
                    pass
                raise _GenerationInterrupted()
            if on_progress:
                frac = 0.1 + (step / max(params["steps"], 1)) * 0.85
                on_progress(min(frac, 0.95), f"Diffusion… étape {step}")
            return _kw

        kwargs: Dict[str, Any] = {
            "prompt": params["prompt"],
            "negative_prompt": params["negative_prompt"],
            "width": params["width"],
            "height": params["height"],
            "num_inference_steps": params["steps"],
            "guidance_scale": self.config.cfg_scale,
        }
        try:
            kwargs["callback_on_step_end"] = _cb
        except Exception:
            pass

        image = pipe(**kwargs).images[0]
        buf = io.BytesIO()
        image.save(buf, format="PNG")
        return buf.getvalue()

    @staticmethod
    def _detect_diffusers_device(torch):
        """Détecte le meilleur device disponible pour diffusers, tous GPU confondus.

        Ordre de préférence : CUDA (NVIDIA + AMD ROCm) → Apple MPS (Metal) →
        Intel XPU → DirectML (Windows AMD/Intel) → CPU. Renvoie un triplet
        (device, dtype, label_humain). float16 sur GPU, float32 sur CPU.
        """
        # CUDA couvre NVIDIA ET AMD ROCm (les builds torch-ROCm exposent l'API cuda).
        try:
            if torch.cuda.is_available():
                # torch.version.hip != None → build ROCm (AMD)
                is_amd = getattr(torch.version, "hip", None) is not None
                name = "AMD ROCm" if is_amd else "NVIDIA CUDA"
                try:
                    name = f"{name} ({torch.cuda.get_device_name(0)})"
                except Exception:
                    pass
                return "cuda", torch.float16, name
        except Exception:
            pass

        # Apple Silicon (Metal Performance Shaders)
        try:
            if getattr(torch.backends, "mps", None) is not None and torch.backends.mps.is_available():
                return "mps", torch.float16, "Apple MPS (Metal)"
        except Exception:
            pass

        # Intel Arc / GPU Intel (oneAPI / IPEX)
        try:
            if hasattr(torch, "xpu") and torch.xpu.is_available():
                return "xpu", torch.float16, "Intel XPU"
        except Exception:
            pass

        # DirectML (Windows : AMD / Intel / NVIDIA via DirectX 12)
        try:
            import torch_directml  # type: ignore  # pylint: disable=import-error,import-outside-toplevel

            return torch_directml.device(), torch.float16, "DirectML (Windows)"
        except Exception:
            pass

        # Repli CPU (lent mais universel)
        return "cpu", torch.float32, "CPU"

    # ------------------------------------------------------------------
    # Utilitaires
    # ------------------------------------------------------------------

    def _save_png(self, png_bytes: bytes, prompt: str) -> str:
        """Sauvegarde l'image dans outputs/ et renvoie le chemin absolu."""
        out_dir = os.path.abspath(self.config.output_directory)
        os.makedirs(out_dir, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        slug = "".join(c for c in prompt[:30] if c.isalnum() or c in " -_").strip()
        slug = slug.replace(" ", "_") or "image"
        filename = f"img_{ts}_{slug}.png"
        path = os.path.join(out_dir, filename)
        with open(path, "wb") as f:
            f.write(png_bytes)
        print(f"🎨 [ImageGen] Image sauvegardée : {path}")
        return path

    def _post(self, url: str, **kwargs) -> requests.Response:
        """POST avec retry tenacity si disponible (calque local_llm._resilient_post)."""
        return _resilient_post(url, **kwargs)


def _resilient_post(url: str, **kwargs) -> requests.Response:
    timeout = kwargs.pop("timeout", 300)
    return requests.post(url, timeout=timeout, **kwargs)


if TENACITY_AVAILABLE:
    _resilient_post = retry(  # type: ignore
        wait=wait_exponential(multiplier=1, max=10),
        stop=stop_after_attempt(2),
        retry=retry_if_exception_type(
            (requests.exceptions.ConnectionError,)
        ),
        reraise=True,
    )(_resilient_post)


# Singleton pratique (évite de re-sonder/charger à chaque requête).
_GLOBAL_GENERATOR: Optional[ImageGenerator] = None


def get_image_generator() -> ImageGenerator:
    """Retourne l'instance globale du générateur d'images."""
    global _GLOBAL_GENERATOR
    if _GLOBAL_GENERATOR is None:
        _GLOBAL_GENERATOR = ImageGenerator()
    return _GLOBAL_GENERATOR
