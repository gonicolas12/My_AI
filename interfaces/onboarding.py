"""Assistant de premier lancement (onboarding wizard).

Au tout premier démarrage, guide l'utilisateur en 1 fenêtre :
  1. Vérifie qu'Ollama est joignable
  2. Détecte la RAM → recommande un modèle de base (qwen3.5:2b/4b/9b)
  3. Pull le modèle choisi (progression streamée depuis /api/pull)
  4. Met à jour Modelfile (FROM) + config.yaml (llm.local.default_model)
  5. Crée le modèle personnalisé 'my_ai' (ollama create -f Modelfile)

100% local. Tout passe par Ollama sur la machine. Si pyttsx3/CTk indisponible
ou Ollama absent, l'assistant se dégrade proprement et l'app démarre quand même.

Le wizard ne s'affiche qu'une fois : un marqueur `data/.onboarding_done` est
écrit après installation ou si l'utilisateur passe l'étape. Il est aussi
considéré comme fait si le modèle 'my_ai' existe déjà (utilisateurs existants).
"""

from __future__ import annotations

import json
import platform
import re
import subprocess
import threading
from pathlib import Path
from typing import Callable, Optional

import requests

# CREATE_NO_WINDOW seulement sur Windows (évite une console qui flashe)
_NO_WINDOW = 0x08000000 if platform.system() == "Windows" else 0

PROJECT_ROOT = Path(__file__).resolve().parent.parent
_MARKER = PROJECT_ROOT / "data" / ".onboarding_done"
CUSTOM_MODEL = "my_ai"

# Choix proposés (modèles texte) + RAM minimale indicative
MODEL_CHOICES = ["qwen3.5:2b", "qwen3.5:4b", "qwen3.5:9b"]


# ── Helpers sans interface (testables) ───────────────────────────────────
def _base_url() -> str:
    """URL Ollama depuis config.yaml (fallback localhost)."""
    try:
        from core.config import get_config
        url = get_config().get("llm.local.base_url", "http://localhost:11434")
        return str(url).rstrip("/")
    except Exception:
        return "http://localhost:11434"


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
    try:
        proc = subprocess.run(
            ["ollama", "create", CUSTOM_MODEL, "-f", "Modelfile"],
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            creationflags=_NO_WINDOW,
        )
    except FileNotFoundError as exc:
        raise RuntimeError("Commande 'ollama' introuvable dans le PATH.") from exc
    if proc.stdout:
        on_log(proc.stdout.strip())
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or "ollama create a échoué.")


# ── Interface graphique du wizard ────────────────────────────────────────
class OnboardingWizard:
    """Fenêtre CustomTkinter d'onboarding (mainloop propre, autonome)."""

    def __init__(self):
        import customtkinter as ctk  # import différé : pas requis si jamais affiché
        self.ctk = ctk
        self._busy = False
        ctk.set_appearance_mode("dark")
        self.win = ctk.CTk()
        self.win.title("My_AI — Configuration initiale")
        self.win.geometry("660x600")
        self.win.resizable(False, False)
        self._build_ui()

    # --- Construction de l'UI ---
    def _build_ui(self):
        ctk = self.ctk
        accent = "#ff6b47"

        ctk.CTkLabel(
            self.win, text="🤖 Bienvenue dans My_AI",
            font=("Segoe UI", 22, "bold"),
        ).pack(pady=(22, 4))
        ctk.CTkLabel(
            self.win,
            text="Configurons votre modèle IA local en quelques clics.",
            font=("Segoe UI", 13), text_color="#b3b3b3",
        ).pack(pady=(0, 14))

        # Statut Ollama
        self.ollama_lbl = ctk.CTkLabel(self.win, text="Vérification d'Ollama…",
                                       font=("Segoe UI", 12))
        self.ollama_lbl.pack(pady=(0, 2))

        # Matériel (RAM + GPU/VRAM + cœurs CPU) + recommandation
        ram = detect_ram_gb()
        vram = detect_vram_gb()
        cores = detect_cpu_cores()
        rec = recommend_model(ram, vram, cores)
        ram_txt = f"{ram} Go" if ram is not None else "inconnue"
        if vram is not None:
            hw_txt = f"💾 RAM : {ram_txt}   ·   🎮 VRAM GPU : {vram} Go   →   recommandé : {rec}"
        else:
            cores_txt = f"{cores} cœurs" if cores else "CPU"
            hw_txt = f"💾 RAM : {ram_txt}   ·   🖥️ {cores_txt}, pas de GPU dédié (inférence CPU)   →   recommandé : {rec}"
        ctk.CTkLabel(
            self.win, text=hw_txt,
            font=("Segoe UI", 12), text_color="#b3b3b3",
        ).pack(pady=(2, 10))

        # Choix du modèle
        row = ctk.CTkFrame(self.win, fg_color="transparent")
        row.pack(pady=(0, 8))
        ctk.CTkLabel(row, text="Modèle de base :", font=("Segoe UI", 12)).pack(side="left", padx=(0, 8))
        self.model_var = ctk.StringVar(value=rec)
        self.model_menu = ctk.CTkOptionMenu(
            row, values=MODEL_CHOICES, variable=self.model_var,
            fg_color="#2f2f2f", button_color=accent, button_hover_color="#e85a3a",
            width=160,
        )
        self.model_menu.pack(side="left")

        # Barre de progression
        self.progress = ctk.CTkProgressBar(self.win, width=560, progress_color=accent)
        self.progress.set(0)
        self.progress.pack(pady=(14, 4))
        self.progress_lbl = ctk.CTkLabel(self.win, text="", font=("Segoe UI", 11),
                                         text_color="#b3b3b3")
        self.progress_lbl.pack(pady=(0, 6))

        # Zone de log
        self.log = ctk.CTkTextbox(self.win, width=580, height=210, font=("Consolas", 11))
        self.log.pack(pady=(0, 10))
        self.log.configure(state="disabled")

        # Boutons
        btns = ctk.CTkFrame(self.win, fg_color="transparent")
        btns.pack(pady=(0, 14))
        self.install_btn = ctk.CTkButton(
            btns, text="🚀 Installer", command=self._on_install,
            fg_color=accent, hover_color="#e85a3a", width=180, height=38,
            font=("Segoe UI", 13, "bold"),
        )
        self.install_btn.pack(side="left", padx=8)
        self.skip_btn = ctk.CTkButton(
            btns, text="Passer", command=self._on_skip,
            fg_color="#3a3a3a", hover_color="#4a4a4a", width=120, height=38,
        )
        self.skip_btn.pack(side="left", padx=8)

        self.win.after(200, self._refresh_ollama_status)

    # --- Logique UI ---
    def _refresh_ollama_status(self):
        if ollama_reachable():
            self.ollama_lbl.configure(text="✅ Ollama détecté et actif", text_color="#10b981")
        else:
            self.ollama_lbl.configure(
                text="⚠️ Ollama non détecté — installez-le depuis ollama.com puis Réessayez",
                text_color="#f59e0b",
            )
            self.install_btn.configure(text="🔄 Réessayer", command=self._retry)

    def _retry(self):
        self.install_btn.configure(text="🚀 Installer", command=self._on_install)
        self._refresh_ollama_status()

    def _log(self, msg: str):
        def _append():
            self.log.configure(state="normal")
            self.log.insert("end", msg.rstrip() + "\n")
            self.log.see("end")
            self.log.configure(state="disabled")
        try:
            self.win.after(0, _append)
        except Exception:
            pass

    def _set_progress(self, frac: float, status: str):
        def _upd():
            self.progress.set(max(0.0, min(1.0, frac)))
            self.progress_lbl.configure(text=f"{status} — {int(frac * 100)}%")
        try:
            self.win.after(0, _upd)
        except Exception:
            pass

    def _on_install(self):
        if self._busy:
            return
        if not ollama_reachable():
            self._refresh_ollama_status()
            return
        self._busy = True
        self.install_btn.configure(state="disabled")
        self.skip_btn.configure(state="disabled")
        self.model_menu.configure(state="disabled")
        model = self.model_var.get()
        threading.Thread(target=self._worker, args=(model,), daemon=True).start()

    def _worker(self, model: str):
        try:
            self._log(f"📥 Téléchargement de {model}…")
            pull_model(model, self._set_progress, self._log)
            self._log(f"✅ {model} téléchargé.")

            self._log("🔧 Mise à jour de Modelfile et config.yaml…")
            apply_model_choice(model)

            self._log("🏗️  Création du modèle personnalisé 'my_ai'…")
            create_custom_model(self._log)
            self._log("✅ Modèle 'my_ai' créé.")

            mark_done()
            self._log("🎉 Configuration terminée ! Vous pouvez lancer My_AI.")
            self.win.after(0, self._finish_success)
        except Exception as exc:
            self._log(f"❌ Erreur : {exc}")
            self.win.after(0, self._finish_error)

    def _finish_success(self):
        self.progress.set(1.0)
        self.progress_lbl.configure(text="Terminé — 100%")
        self.install_btn.configure(text="✅ Démarrer My_AI", state="normal",
                                   command=self._close)
        self.skip_btn.configure(state="disabled")
        self._busy = False

    def _finish_error(self):
        self.install_btn.configure(text="🔄 Réessayer", state="normal",
                                   command=self._reset_after_error)
        self.skip_btn.configure(state="normal", text="Continuer quand même")
        self.model_menu.configure(state="normal")
        self._busy = False

    def _reset_after_error(self):
        self.progress.set(0)
        self.progress_lbl.configure(text="")
        self.install_btn.configure(text="🚀 Installer", command=self._on_install)

    def _on_skip(self):
        # L'utilisateur passe : on marque fait pour ne plus afficher au démarrage
        mark_done()
        self._close()

    def _close(self):
        try:
            self.win.destroy()
        except Exception:
            pass

    def run(self):
        """Affiche le wizard (bloquant jusqu'à fermeture)."""
        self.win.protocol("WM_DELETE_WINDOW", self._on_skip)
        self.win.mainloop()
