"""Assistant de premier lancement (onboarding) : fonctions sans interface.

Au tout premier démarrage, l'assistant de la fenêtre (FirstLaunch de
interfaces/desktop/model_setup.py) guide l'utilisateur avec ces fonctions :
  1. Vérifie qu'Ollama est joignable
  2. Détecte la RAM → recommande un modèle de base (qwen3.5:2b/4b/9b)
  3. Pull le modèle choisi (progression streamée depuis /api/pull)
  4. Met à jour Modelfile (FROM) + config.yaml (llm.local.default_model)
  5. Crée le modèle personnalisé 'my_ai' (ollama create -f Modelfile)

Les Réglages de la fenêtre s'en servent aussi (modèles, paramètres de
génération, réglages simples de config.yaml, commentaires préservés).

100% local. Tout passe par Ollama sur la machine. Si Ollama est absent,
l'assistant se dégrade proprement et l'app démarre quand même.

Le wizard ne s'affiche qu'une fois : un marqueur `data/.onboarding_done` est
écrit après installation ou si l'utilisateur passe l'étape. Il est aussi
considéré comme fait si le modèle 'my_ai' existe déjà (utilisateurs existants).

Ensuite, à chaque lancement, sync_custom_model() recrée 'my_ai' si le Modelfile
a changé depuis sa création (modifié à la main, par un git pull ou par
⚙️ Réglages) : plus besoin de relancer create_custom_model.bat.
"""

from __future__ import annotations

import hashlib
import json
import platform
import re
import subprocess
from pathlib import Path
from typing import Callable, Optional

import requests

from core.i18n import tr

# CREATE_NO_WINDOW seulement sur Windows (évite une console qui flashe)
_NO_WINDOW = 0x08000000 if platform.system() == "Windows" else 0

PROJECT_ROOT = Path(__file__).resolve().parent.parent
_MARKER = PROJECT_ROOT / "data" / ".onboarding_done"
# Empreinte du Modelfile dont 'my_ai' a été créé (cf. sync_custom_model)
_MODELFILE_SYNC = PROJECT_ROOT / "data" / ".modelfile_sync"
CUSTOM_MODEL = "my_ai"

# Choix proposés (modèles texte) + RAM minimale indicative
MODEL_CHOICES = ["qwen3.5:2b", "qwen3.5:4b", "qwen3.5:9b"]


# ── Helpers sans interface (testables) ───────────────────────────────────
def _base_url() -> str:
    """URL Ollama depuis config.yaml (fallback 127.0.0.1)."""
    try:
        from core.config import get_config, normalize_ollama_url
        url = get_config().get("llm.local.base_url", "http://127.0.0.1:11434")
        return normalize_ollama_url(str(url).rstrip("/"))
    except Exception:
        return "http://127.0.0.1:11434"


def marker_path() -> Path:
    return _MARKER


def mark_done() -> None:
    try:
        _MARKER.parent.mkdir(parents=True, exist_ok=True)
        _MARKER.write_text("done\n", encoding="utf-8")
    except Exception:
        pass


def ollama_reachable(timeout: float = 2.0) -> bool:
    try:
        r = requests.get(_base_url() + "/api/tags", timeout=timeout)
        return r.status_code == 200
    except Exception:
        return False


def custom_model_exists() -> bool:
    """True si le modèle personnalisé 'my_ai' est déjà présent dans Ollama."""
    try:
        r = requests.get(_base_url() + "/api/tags", timeout=2)
        if r.status_code != 200:
            return False
        names = [m.get("name", "") for m in r.json().get("models", [])]
        return any(CUSTOM_MODEL in n for n in names)
    except Exception:
        return False


def should_run() -> bool:
    """Décide si l'assistant doit s'afficher au lancement."""
    if _MARKER.exists():
        return False
    # Utilisateur déjà configuré : ne pas déranger, marquer comme fait.
    if custom_model_exists():
        mark_done()
        return False
    return True


def detect_ram_gb() -> Optional[float]:
    try:
        import psutil
        return round(psutil.virtual_memory().total / (1024 ** 3), 1)
    except Exception:
        return None


def detect_vram_gb() -> Optional[float]:
    """Détecte la VRAM du GPU dédié (Go), ou None si aucun GPU exploitable.

    Sondes par ordre de fiabilité, sans imposer de dépendance :
      1. nvidia-smi (CLI livrée avec les drivers NVIDIA — aucun paquet Python)
      2. pynvml, 3. GPUtil (NVIDIA), 4. pyamdgpuinfo (AMD)
    Le fallback WMI Windows est volontairement ignoré : son AdapterRAM est
    plafonné à ~4 Go et faux pour les GPU intégrés → mieux vaut None (→ reco RAM).
    """
    # 1. nvidia-smi
    try:
        out = subprocess.run(
            ["nvidia-smi", "--query-gpu=memory.total", "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=4, creationflags=_NO_WINDOW,
        )
        if out.returncode == 0 and out.stdout.strip():
            mb = [int(t) for t in out.stdout.split() if t.strip().isdigit()]
            if mb:
                return round(max(mb) / 1024, 1)
    except Exception:
        pass
    # 2. pynvml
    try:
        import pynvml
        pynvml.nvmlInit()
        h = pynvml.nvmlDeviceGetHandleByIndex(0)
        total = pynvml.nvmlDeviceGetMemoryInfo(h).total
        pynvml.nvmlShutdown()
        return round(total / (1024 ** 3), 1)
    except Exception:
        pass
    # 3. GPUtil (memoryTotal en Mo)
    try:
        import GPUtil
        gpus = GPUtil.getGPUs()
        if gpus:
            return round(float(gpus[0].memoryTotal) / 1024, 1)
    except Exception:
        pass
    # 4. AMD pyamdgpuinfo
    try:
        import pyamdgpuinfo
        if pyamdgpuinfo.detect_gpus() > 0:
            size = pyamdgpuinfo.get_gpu(0).memory_info["vram_size"]
            return round(size / (1024 ** 3), 1)
    except Exception:
        pass
    return None


def detect_cpu_cores() -> Optional[int]:
    """Nombre de cœurs physiques (proxy de vitesse CPU), ou None."""
    try:
        import psutil
        n = psutil.cpu_count(logical=False)
        if n:
            return int(n)
    except Exception:
        pass
    try:
        import os
        return os.cpu_count()
    except Exception:
        return None


def recommend_model(
    ram_gb: Optional[float],
    vram_gb: Optional[float] = None,
    cpu_cores: Optional[int] = None,
) -> str:
    """Recommande un modèle de base en privilégiant une expérience FLUIDE.

    - GPU dédié (VRAM ≥ 4 Go) : le modèle tourne en VRAM et le GPU est rapide,
      donc on dimensionne sur la VRAM (2b/4b/9b ≈ 4/6/10 Go).
    - Sinon (inférence CPU) : le facteur limitant est la VITESSE du CPU, pas la
      RAM — un gros modèle « rentre » en RAM mais génère trop lentement sur un
      PC bureautique. On reste donc conservateur : 2b par défaut, 4b seulement
      si le CPU est costaud (≥ 8 cœurs physiques) ET la RAM confortable
      (≥ 16 Go). Jamais 9b en CPU (trop lent pour un usage agréable).
    """
    # GPU dédié exploitable → on dimensionne sur la VRAM
    if vram_gb is not None and vram_gb >= 4:
        if vram_gb < 6:
            return "qwen3.5:2b"
        if vram_gb < 10:
            return "qwen3.5:4b"
        return "qwen3.5:9b"
    # Inférence CPU → priorité à la fluidité
    if ram_gb is not None and ram_gb >= 16 and cpu_cores is not None and cpu_cores >= 8:
        return "qwen3.5:4b"
    return "qwen3.5:2b"


def apply_model_choice(base_model: str) -> None:
    """Met à jour Modelfile (FROM) et config.yaml (1re clé default_model).

    Édition par remplacement de ligne pour PRÉSERVER les commentaires des
    fichiers (un yaml.dump détruirait toute la mise en forme de config.yaml).
    """
    # Modelfile : ligne FROM
    mf = PROJECT_ROOT / "Modelfile"
    if mf.exists():
        text = mf.read_text(encoding="utf-8")
        new_text, n = re.subn(r"(?m)^FROM[ \t]+.*$", f"FROM {base_model}", text, count=1)
        if n == 0:  # pas de FROM trouvé : préfixer
            new_text = f"FROM {base_model}\n" + text
        mf.write_text(new_text, encoding="utf-8")

    # config.yaml : 1re occurrence de default_model (= llm.local, avant transformers)
    cfg = PROJECT_ROOT / "config.yaml"
    if cfg.exists():
        ctext = cfg.read_text(encoding="utf-8")
        ctext = re.sub(
            r'(?m)^([ \t]*default_model:[ \t]*).*$',
            lambda m: f'{m.group(1)}"{base_model}"',
            ctext,
            count=1,
        )
        cfg.write_text(ctext, encoding="utf-8")


def _reload_config() -> None:
    """Recharge le singleton de configuration après une écriture fichier."""
    try:
        from core.config import get_config
        get_config().reload()
    except Exception:
        pass


def list_installed_models() -> list:
    """Liste les modèles installés dans Ollama (GET /api/tags).

    Retourne la liste des noms (ex: ['qwen3.5:4b', 'my_ai:latest', ...]) ou
    une liste vide si Ollama est injoignable.
    """
    try:
        r = requests.get(_base_url() + "/api/tags", timeout=3)
        if r.status_code != 200:
            return []
        return [m.get("name", "") for m in r.json().get("models", []) if m.get("name")]
    except Exception:
        return []


def current_base_model() -> str:
    """Modèle de base courant = ligne FROM du Modelfile.

    Fallback sur config.yaml (llm.local.default_model) puis 'qwen3.5:4b'.
    """
    mf = PROJECT_ROOT / "Modelfile"
    if mf.exists():
        try:
            m = re.search(r"(?m)^FROM[ \t]+(.+?)[ \t]*$", mf.read_text(encoding="utf-8"))
            if m:
                return m.group(1).strip()
        except Exception:
            pass
    try:
        from core.config import get_config
        return str(get_config().get("llm.local.default_model", "qwen3.5:4b"))
    except Exception:
        return "qwen3.5:4b"


def apply_generation_params(temperature=None, num_ctx=None, timeout=None) -> None:
    """Met à jour les paramètres de génération sans détruire les commentaires.

    Écrit dans le Modelfile (lignes PARAMETER) et dans config.yaml (clés sous
    llm.local:, ancrées sur 4 espaces d'indentation pour ne pas confondre avec
    ai.temperature / ai.timeout qui sont indentés de 2 espaces). Les arguments
    laissés à None ne sont pas modifiés.
    """
    # ── Modelfile : PARAMETER temperature / num_ctx ──
    mf = PROJECT_ROOT / "Modelfile"
    if mf.exists():
        text = mf.read_text(encoding="utf-8")
        if temperature is not None:
            text, n = re.subn(
                r"(?m)^PARAMETER[ \t]+temperature[ \t]+.*$",
                f"PARAMETER temperature {temperature}", text, count=1,
            )
            if n == 0:
                text = text.rstrip() + f"\nPARAMETER temperature {temperature}\n"
        if num_ctx is not None:
            text, n = re.subn(
                r"(?m)^PARAMETER[ \t]+num_ctx[ \t]+.*$",
                f"PARAMETER num_ctx {int(num_ctx)}", text, count=1,
            )
            if n == 0:
                text = text.rstrip() + f"\nPARAMETER num_ctx {int(num_ctx)}\n"
        mf.write_text(text, encoding="utf-8")

    # ── config.yaml : llm.local.temperature / num_ctx / timeout ──
    cfg = PROJECT_ROOT / "config.yaml"
    if cfg.exists():
        ctext = cfg.read_text(encoding="utf-8")
        if temperature is not None:
            ctext = re.sub(r'(?m)^(    temperature:[ \t]*).*$',
                           lambda m: f'{m.group(1)}{temperature}', ctext, count=1)
        if num_ctx is not None:
            ctext = re.sub(r'(?m)^(    num_ctx:[ \t]*).*$',
                           lambda m: f'{m.group(1)}{int(num_ctx)}', ctext, count=1)
        if timeout is not None:
            ctext = re.sub(r'(?m)^(    timeout:[ \t]*).*$',
                           lambda m: f'{m.group(1)}{int(timeout)}', ctext, count=1)
        cfg.write_text(ctext, encoding="utf-8")

    _reload_config()


# Réglages simples → regex de ligne ancré (préserve les commentaires).
_CONFIG_FLAG_PATTERNS = {
    "language.default": r'(?m)^(  default:[ \t]*).*$',
    "ui.tts_autoread": r'(?m)^(  tts_autoread:[ \t]*).*$',
    "relay.auto_start": r'(?m)^(  auto_start:[ \t]*).*$',
}


def _yaml_scalar(value) -> str:
    """Formate une valeur Python en scalaire YAML."""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, str):
        return f'"{value}"'
    return str(value)


def set_config_flag(name: str, value) -> None:
    """Met à jour un réglage simple dans config.yaml (commentaires préservés).

    `name` ∈ {'language.default', 'ui.tts_autoread', 'relay.auto_start'}.
    """
    pattern = _CONFIG_FLAG_PATTERNS.get(name)
    if pattern is None:
        raise ValueError(f"Clé de configuration non supportée : {name}")
    cfg = PROJECT_ROOT / "config.yaml"
    if not cfg.exists():
        return
    ctext = cfg.read_text(encoding="utf-8")
    scalar = _yaml_scalar(value)
    ctext = re.sub(pattern, lambda m: f'{m.group(1)}{scalar}', ctext, count=1)
    cfg.write_text(ctext, encoding="utf-8")
    _reload_config()


def pull_model(
    model: str,
    on_progress: Callable[[float, str], None],
    on_log: Callable[[str], None],
) -> None:
    """Télécharge un modèle via /api/pull en streamant la progression."""
    url = _base_url() + "/api/pull"
    seen = set()
    with requests.post(url, json={"name": model, "stream": True}, stream=True, timeout=None) as r:
        r.raise_for_status()
        for line in r.iter_lines():
            if not line:
                continue
            try:
                data = json.loads(line.decode("utf-8"))
            except Exception:
                continue
            if data.get("error"):
                raise RuntimeError(data["error"])
            status = data.get("status", "")
            total = data.get("total")
            completed = data.get("completed")
            if total and completed:
                on_progress(completed / total, status)
            elif status and status not in seen:
                seen.add(status)
                on_log(status)


def create_custom_model(on_log: Callable[[str], None]) -> None:
    """Crée le modèle 'my_ai' depuis le Modelfile (équiv. create_custom_model.bat)."""
    digest = _modelfile_digest()
    try:
        proc = subprocess.run(
            ["ollama", "create", CUSTOM_MODEL, "-f", "Modelfile"],
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            # Spinner d'Ollama en UTF-8 : l'encodage par défaut de Windows échoue dessus
            encoding="utf-8",
            errors="replace",
            creationflags=_NO_WINDOW,
        )
    except FileNotFoundError as exc:
        raise RuntimeError(tr("models.ollamaNotFound")) from exc
    if proc.stdout:
        on_log(proc.stdout.strip())
    if proc.returncode != 0:
        raise RuntimeError(_ollama_error(proc.stderr) or tr("models.createFailed"))
    _remember_modelfile(digest)


def sync_custom_model() -> bool:
    """Recrée 'my_ai' au lancement si le Modelfile a changé depuis sa création.

    Modelfile inchangé : aucun appel à Ollama. Ollama injoignable : nouvel essai
    au prochain lancement. 'my_ai' absent (assistant passé) : rien n'est créé ni
    téléchargé, la création reste le rôle de l'assistant et de ⚙️ Réglages.
    La sortie d'Ollama est masquée : la console n'affiche que le début et
    l'issue de la mise à jour.

    Returns:
        True si le modèle a été recréé
    """
    digest = _modelfile_digest()
    try:
        synced = _MODELFILE_SYNC.read_text(encoding="utf-8").strip()
    except OSError:
        synced = ""
    if digest is None or digest == synced or not custom_model_exists():
        return False
    print(f"🔄 Mise à jour du modèle '{CUSTOM_MODEL}' depuis le Modelfile…", flush=True)
    try:
        _pull_base_model()
        create_custom_model(lambda _message: None)
    except (RuntimeError, OSError) as exc:  # OSError couvre aussi les erreurs de requests
        print(f"⚠️ Modèle '{CUSTOM_MODEL}' non mis à jour : {exc}")
        print("   Nouvel essai au prochain lancement")
        return False
    print(f"✅ Modèle '{CUSTOM_MODEL}' à jour")
    return True


def _pull_base_model() -> None:
    """Télécharge le modèle de la ligne FROM s'il n'est pas encore dans Ollama.

    « ollama create » le téléchargerait sinon lui-même, sortie masquée : la
    console resterait muette pendant tout le téléchargement (plusieurs Go).
    """
    base = current_base_model()
    installed = list_installed_models()
    if base in installed or f"{base}:latest" in installed or (PROJECT_ROOT / base).exists():
        return  # déjà dans Ollama, ou fichier local (GGUF)

    def show(frac: float, _status: str = "") -> None:
        print(f"\r📥 Téléchargement de {base} : {frac:>4.0%}", end="", flush=True)

    show(0.0)
    try:
        pull_model(base, show, lambda _status: None)
        show(1.0)  # Ollama ne renvoie pas toujours la dernière progression
    finally:
        print()  # termine la ligne de progression


# Séquences ANSI de la progression qu'Ollama écrit sur stderr
_ANSI_ESCAPE = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")


def _ollama_error(stderr: str) -> str:
    """Message d'erreur d'Ollama, sans la progression qui le précède sur stderr."""
    lines = [line.strip() for line in _ANSI_ESCAPE.sub("", stderr or "").splitlines()]
    lines = [line for line in lines if line]
    for line in reversed(lines):
        if line.startswith("Error:"):
            return line[len("Error:"):].strip()
    return lines[-1] if lines else ""


def _modelfile_digest() -> Optional[str]:
    """Empreinte SHA-256 du Modelfile, ou None s'il est illisible.

    Calculée sur le texte lu : le même Modelfile en CRLF (Windows) ou en LF
    donne la même empreinte.
    """
    try:
        text = (PROJECT_ROOT / "Modelfile").read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _remember_modelfile(digest: Optional[str]) -> None:
    """Retient l'empreinte du Modelfile dont 'my_ai' vient d'être créé."""
    if digest is None:
        return
    try:
        _MODELFILE_SYNC.parent.mkdir(parents=True, exist_ok=True)
        _MODELFILE_SYNC.write_text(digest + "\n", encoding="utf-8")
    except OSError:
        pass
