"""
Placement du modèle d'Ollama sur le matériel le plus rapide de la machine

Ollama place déjà le modèle tout seul sur une carte graphique dédiée (en partie
seulement si sa mémoire ne suffit pas, le reste allant au processeur) et, sans
carte graphique, sur le processeur. Il écarte en revanche le GPU intégré au
processeur (Intel Arc, AMD Radeon 780M…) : selon la machine, celui-ci va bien
plus vite que le processeur (prompt lu 4 fois plus vite sur un Core Ultra 7
255H) ou plus lentement.

Au lancement, ce module regarde donc où Ollama place le modèle de l'appli. S'il
reste sur le processeur, il mesure sa vitesse, relance Ollama avec le GPU
intégré autorisé, mesure à nouveau et garde le plus rapide des deux. Le choix
est retenu dans data/.ollama_placement.json : la mesure n'est refaite qu'après
une mise à jour d'Ollama, un changement de modèle, de carte graphique ou de
pilote. Pour la refaire à la main, supprimer ce fichier.
"""

# Imports différés (core.config, interfaces.onboarding, winreg) : inutiles
# quand le placement est déjà mesuré, soit la plupart des lancements
# pylint: disable=import-outside-toplevel

import json
import os
import platform
import re
import sys
import time
from datetime import date
from pathlib import Path
from typing import Callable, Dict, List, Mapping, Optional
from urllib.parse import urlsplit

import requests

PROJECT_ROOT = Path(__file__).resolve().parent.parent
# Dernier calibrage : empreinte de la machine, placement retenu et mesures
STATE_FILE = PROJECT_ROOT / "data" / ".ollama_placement.json"
CUSTOM_MODEL = "my_ai"

# Variables qui autorisent ce qu'Ollama écarte par défaut : le GPU intégré, et
# Vulkan (par lequel passent les GPU Intel) sur les versions d'Ollama où il
# n'est pas encore actif d'office
EXTRA_GPU_ENV = {"OLLAMA_VULKAN": "1", "OLLAMA_IGPU_ENABLE": "1"}

# Le lanceur ne pilote que le serveur local, sur le port par défaut
_DEFAULT_URL = "http://127.0.0.1:11434"
_LOCAL_HOSTS = ("127.0.0.1", "localhost", "::1")
_DEFAULT_PORT = 11434

# Requête type de My_AI pour comparer deux placements : prompt système, outils
# et contexte (≈ 2 000 tokens), puis la réponse (≈ 300 tokens)
_TYPICAL_PROMPT_TOKENS = 2000
_TYPICAL_ANSWER_TOKENS = 300
# Gain minimal pour préférer le GPU intégré au choix par défaut d'Ollama
_MIN_SPEEDUP = 1.15

# Phrase répétée du texte de mesure (une vingtaine de tokens)
_PHRASE = "Ce texte sert seulement à mesurer la vitesse de lecture et d'écriture de la machine. "

# Cartes graphiques dans le registre Windows (classe de périphériques « Display »)
_DISPLAY_CLASS_KEY = (
    r"SYSTEM\CurrentControlSet\Control\Class\{4d36e968-e325-11ce-bfc1-08002be10318}"
)

_PLACEMENTS = ("gpu", "gpu-integre", "cpu")


class PlacementError(Exception):
    """Ollama injoignable, ou en échec pendant le calibrage."""


def server_env(base: Mapping[str, str], placement_env: Mapping[str, str]) -> Dict[str, str]:
    """
    Environnement du serveur Ollama

    Args:
        base: Environnement de l'utilisateur
        placement_env: Variables du placement retenu

    Returns:
        L'environnement de l'utilisateur complété par le placement : une
        variable qu'il a définie lui-même garde sa valeur
    """
    env = dict(base)
    for key, value in placement_env.items():
        env.setdefault(key, value)
    return env


def saved_env(state_file: Path = STATE_FILE) -> Dict[str, str]:
    """Variables du placement retenu au dernier calibrage (vide sans calibrage)."""
    env = _read_state(state_file).get("env")
    if not isinstance(env, dict):
        return {}
    return {str(key): str(value) for key, value in env.items()}


def placement_label(state_file: Path = STATE_FILE) -> Optional[str]:
    """Où tourne le modèle d'après le dernier calibrage, en clair (None sans calibrage)."""
    state = _read_state(state_file)
    placement = state.get("placement")
    if placement == "cpu":
        return "modèle sur le processeur"
    if placement not in ("gpu", "gpu-integre"):
        return None
    where = "le GPU intégré" if placement == "gpu-integre" else "le GPU"
    share = state.get("gpu_share")
    if isinstance(share, (int, float)) and 0 < share < 99.5:
        return f"modèle à {share:.0f} % sur {where}"
    return f"modèle sur {where}"


def ensure_best_placement(
    restart: Callable[[Dict[str, str]], bool], state_file: Path = STATE_FILE
) -> Optional[str]:
    """
    Place le modèle de l'appli sur le matériel le plus rapide, si ce n'est déjà fait

    Args:
        restart: Relance le serveur Ollama avec ces variables de placement, en
            plus de l'environnement de l'utilisateur ; True s'il répond
        state_file: Mémoire du dernier calibrage

    Returns:
        Placement retenu : "gpu" (choix d'Ollama), "gpu-integre" ou "cpu" ;
        None si Ollama ou le modèle manquent (nouvel essai au prochain lancement)
    """
    base_url = _local_ollama_url()
    if base_url is None:
        return None  # Ollama sur une autre machine : le lanceur ne le pilote pas
    try:
        model = _model_to_place(base_url)
        if model is None:
            return None  # assistant de premier lancement passé : rien à placer
        signature = _signature(base_url, model)
    except PlacementError:
        return None  # Ollama arrêté : nouvel essai au prochain lancement
    state = _read_state(state_file)
    if state.get("signature") == signature and state.get("placement") in _PLACEMENTS:
        return state["placement"]

    print(
        f"🔍 Recherche du meilleur emplacement pour le modèle '{model}' "
        "(une seule fois, jusqu'à une minute)…",
        flush=True,
    )
    previous_env = saved_env(state_file)
    try:
        result = _calibrate(base_url, model, restart, previous_env)
    except Exception as exc:  # jamais bloquant : l'appli démarre quand même
        print(f"⚠️ Placement du modèle non mesuré : {exc}")
        print("   Nouvel essai au prochain lancement")
        try:
            restart(previous_env)  # serveur laissé tel que le lanceur l'avait démarré
        except Exception:
            pass
        return None
    finally:
        _unload(base_url, model)

    print(_conclusion(result))
    _write_state(
        state_file, {"signature": signature, "date": date.today().isoformat(), **result}
    )
    return result["placement"]


def _calibrate(
    base_url: str,
    model: str,
    restart: Callable[[Dict[str, str]], bool],
    previous_env: Dict[str, str],
) -> dict:
    """Compare les placements possibles du modèle et laisse Ollama sur le meilleur."""
    # 1. Choix par défaut d'Ollama, avec l'environnement de l'utilisateur seul
    if previous_env:
        _restart(restart, {})
    share = _load(base_url, model)
    if share > 0:
        return {"placement": "gpu", "env": {}, "gpu_share": round(share, 1)}
    if _dedicated_gpu_vram():
        # Carte dédiée pleine à cet instant : y ajouter le GPU intégré risquerait
        # qu'Ollama lui donne le modèle même une fois la carte libérée
        return {"placement": "gpu", "env": {}, "reason": "dedicated"}
    print("   • Choix par défaut d'Ollama : processeur", flush=True)
    cpu = _measure(base_url, model)
    print(f"   • Processeur : {_speeds(cpu)}", flush=True)

    # 2. GPU intégré autorisé, sauf variable que l'utilisateur a fixée lui-même
    extra = {key: value for key, value in EXTRA_GPU_ENV.items() if key not in os.environ}
    result = {"placement": "cpu", "env": {}, "gpu_share": 0.0, "measures": {"cpu": cpu}}
    if not extra:
        return {**result, "reason": "no-gpu"}
    result.update(_try_integrated_gpu(base_url, model, restart, extra, cpu))
    if result["placement"] == "cpu":
        _restart(restart, {})  # serveur rendu au choix par défaut d'Ollama
    return result


def _try_integrated_gpu(
    base_url: str,
    model: str,
    restart: Callable[[Dict[str, str]], bool],
    extra: Dict[str, str],
    cpu: Dict[str, float],
) -> dict:
    """Relance Ollama avec le GPU intégré autorisé et le compare au processeur."""
    try:
        _restart(restart, extra)
        share = _load(base_url, model)
        gpu = _measure(base_url, model) if share > 0 else None
    except PlacementError as exc:
        # Pilote ou GPU sur lequel le modèle échoue : le processeur reste le bon choix
        print(f"   • GPU intégré : échec ({exc})", flush=True)
        return {"reason": "failed"}
    if gpu is None:
        return {"reason": "no-gpu"}

    where = "GPU intégré" if share >= 99.5 else f"GPU intégré ({share:.0f} % du modèle)"
    print(f"   • {where} : {_speeds(gpu)}", flush=True)
    speedup = _typical_time(cpu) / _typical_time(gpu)
    measured = {"measures": {"cpu": cpu, "gpu": gpu}, "speedup": round(speedup, 2)}
    if speedup < _MIN_SPEEDUP:
        return {**measured, "reason": "slower"}
    return {**measured, "placement": "gpu-integre", "env": extra, "gpu_share": round(share, 1)}


# Conclusion quand le modèle reste sur le processeur, selon la raison
_CPU_CONCLUSIONS = {
    "slower": "✅ Modèle laissé sur le processeur : le GPU intégré ne fait pas mieux ici",
    "failed": "✅ Modèle laissé sur le processeur : le GPU intégré n'a pas pu le faire tourner",
    "no-gpu": "✅ Modèle sur le processeur : aucun GPU utilisable par Ollama",
}


def _conclusion(result: dict) -> str:
    """Ligne de console qui annonce le placement retenu."""
    placement, reason = result["placement"], result.get("reason")
    if placement == "cpu":
        return _CPU_CONCLUSIONS.get(reason, _CPU_CONCLUSIONS["no-gpu"])
    if placement == "gpu-integre":
        return (
            "✅ Modèle placé sur le GPU intégré : réponse type "
            f"{_decimal(result['speedup'])}× plus rapide qu'avec le processeur"
        )
    if reason == "dedicated":
        return (
            "✅ Modèle confié à la carte graphique dédiée : Ollama l'y place "
            "dès qu'elle a assez de mémoire libre"
        )
    share = result.get("gpu_share", 100.0)
    if share >= 99.5:
        return "✅ Modèle sur le GPU : Ollama l'y place déjà tout seul"
    return (
        f"✅ Modèle à {share:.0f} % sur le GPU, le reste sur le processeur : "
        "la mémoire de la carte graphique ne suffit pas pour tout"
    )


def _restart(restart: Callable[[Dict[str, str]], bool], placement_env: Dict[str, str]) -> None:
    if not restart(placement_env):
        raise PlacementError("Ollama ne répond plus après son redémarrage")


def _load(base_url: str, model: str) -> float:
    """Charge le modèle ; renvoie la part (en %) qu'Ollama en a mise sur un GPU."""
    # Sans prompt, /api/generate charge seulement le modèle
    _request(base_url, "/api/generate", {"model": model, "keep_alive": "5m"})
    for entry in _request(base_url, "/api/ps").get("models", []):
        if _tagged(str(entry.get("name", ""))) == _tagged(model):
            size = entry.get("size") or 0
            return 100.0 * (entry.get("size_vram") or 0) / size if size else 0.0
    raise PlacementError(f"modèle '{model}' absent des modèles chargés")


def _measure(base_url: str, model: str) -> Dict[str, float]:
    """Vitesses de lecture du prompt et d'écriture (tokens/s), modèle chargé."""
    # Chauffe : sur GPU, les premiers calculs après un chargement préparent les shaders
    _generate(base_url, model, sentences=4, tokens=2)
    stats = _generate(base_url, model, sentences=25, tokens=32)
    speeds = {"prompt_tps": _rate(stats, "prompt_eval"), "gen_tps": _rate(stats, "eval")}
    if not all(speeds.values()):
        raise PlacementError("mesure de vitesse vide")
    return {key: round(value, 1) for key, value in speeds.items()}


def _generate(base_url: str, model: str, sentences: int, tokens: int) -> dict:
    # Préfixe unique : Ollama ne peut pas reprendre le calcul du texte précédent
    prompt = f"[{time.time_ns()}]\n" + "".join(
        f"{number}. {_PHRASE}" for number in range(1, sentences + 1)
    )
    return _request(base_url, "/api/generate", {
        "model": model,
        "prompt": prompt,
        "raw": True,  # texte brut : ni gabarit de conversation, ni réflexion
        "stream": False,
        "keep_alive": "5m",
        "options": {"num_predict": tokens, "temperature": 0, "seed": 1},
    })


def _rate(stats: dict, prefix: str) -> float:
    count = stats.get(f"{prefix}_count") or 0
    seconds = (stats.get(f"{prefix}_duration") or 0) / 1e9
    return count / seconds if count and seconds else 0.0


def _typical_time(speeds: Dict[str, float]) -> float:
    """Durée estimée d'une requête type de My_AI, en secondes."""
    return (
        _TYPICAL_PROMPT_TOKENS / speeds["prompt_tps"]
        + _TYPICAL_ANSWER_TOKENS / speeds["gen_tps"]
    )


def _speeds(speeds: Dict[str, float]) -> str:
    return (
        f"lecture {speeds['prompt_tps']:.0f} tok/s, "
        f"écriture {_decimal(speeds['gen_tps'])} tok/s"
    )


def _decimal(value: float) -> str:
    return f"{value:.1f}".replace(".", ",")


def _unload(base_url: str, model: str) -> None:
    """Libère la mémoire : l'appli rechargera le modèle avec ses propres réglages."""
    try:
        _request(base_url, "/api/generate", {"model": model, "keep_alive": 0})
    except PlacementError:
        pass


def _model_to_place(base_url: str) -> Optional[str]:
    """Modèle principal de l'appli : 'my_ai', à défaut celui de config.yaml (cf. LocalLLM)."""
    installed = {
        _tagged(str(entry.get("name", "")))
        for entry in _request(base_url, "/api/tags").get("models", [])
    }
    for model in (CUSTOM_MODEL, _default_model()):
        if _tagged(model) in installed:
            return model
    return None


def _signature(base_url: str, model: str) -> dict:
    """Ce qui, en changeant, peut changer le meilleur placement."""
    details = _request(base_url, "/api/show", {"model": model}).get("details") or {}
    return {
        "ollama": _request(base_url, "/api/version").get("version", ""),
        "model": model,
        "weights": " ".join(
            str(details.get(key, "")) for key in ("family", "parameter_size", "quantization_level")
        ),
        # Une variable de placement posée ou retirée par l'utilisateur change la donne
        "user_env": {key: os.environ.get(key) for key in EXTRA_GPU_ENV},
        "cpu": platform.processor() or platform.machine(),
        "gpus": _graphics_adapters(),
    }


def _graphics_adapters() -> List[str]:
    """Cartes graphiques de la machine (avec la version du pilote sous Windows)."""
    adapters: List[str] = []
    if sys.platform.startswith("win"):
        try:
            import winreg

            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, _DISPLAY_CLASS_KEY) as root:
                for index in range(winreg.QueryInfoKey(root)[0]):
                    name = winreg.EnumKey(root, index)
                    if not name.isdigit():
                        continue  # « Configuration », « Properties »
                    try:
                        with winreg.OpenKey(root, name) as key:
                            adapters.append(" ".join(
                                str(winreg.QueryValueEx(key, value)[0])
                                for value in ("DriverDesc", "DriverVersion")
                            ))
                    except OSError:
                        continue
        except OSError:
            pass
    else:
        # Linux : identifiants PCI des cartes vues par le noyau (rien sous macOS,
        # où Ollama utilise toujours le GPU d'Apple)
        for card in sorted(Path("/sys/class/drm").glob("card*")):
            if not re.fullmatch(r"card\d+", card.name):
                continue  # connecteurs : card0-HDMI-A-1…
            try:
                adapters.append(":".join(
                    (card / "device" / field).read_text(encoding="utf-8").strip()
                    for field in ("vendor", "device")
                ))
            except OSError:
                continue
    return sorted(adapters)


def _dedicated_gpu_vram() -> Optional[float]:
    """VRAM de la carte graphique dédiée (Go), None sans carte détectée (cf. onboarding)."""
    try:
        from interfaces.onboarding import detect_vram_gb

        return detect_vram_gb()
    except Exception:
        return None


def _local_ollama_url() -> Optional[str]:
    """Adresse d'Ollama d'après config.yaml, si c'est le serveur local du lanceur."""
    try:
        from core.config import get_config, normalize_ollama_url

        url = str(get_config().get("llm.local.base_url", _DEFAULT_URL)).rstrip("/")
        url = normalize_ollama_url(url)
    except Exception:
        url = _DEFAULT_URL
    return url if _is_local_ollama(url) else None


def _is_local_ollama(url: str) -> bool:
    try:
        parts = urlsplit(url)
        port = parts.port or _DEFAULT_PORT
    except ValueError:  # port illisible
        return False
    return (parts.hostname or "").lower() in _LOCAL_HOSTS and port == _DEFAULT_PORT


def _default_model() -> str:
    try:
        from core.config import get_default_model

        return str(get_default_model())
    except Exception:
        return "qwen3.5:4b"


def _tagged(name: str) -> str:
    """Nom complet d'un modèle : « my_ai » et « my_ai:latest » se rejoignent."""
    return name if ":" in name.rsplit("/", 1)[-1] else f"{name}:latest"


def _request(base_url: str, path: str, payload: Optional[dict] = None) -> dict:
    """Appel à l'API d'Ollama : GET sans payload, POST sinon."""
    try:
        if payload is None:
            response = requests.get(base_url + path, timeout=10)
        else:
            # Chargement ou mesure : plusieurs minutes possibles sur une machine lente
            response = requests.post(base_url + path, json=payload, timeout=600)
    except requests.RequestException as exc:
        raise PlacementError(f"Ollama injoignable ({type(exc).__name__})") from exc
    try:
        data = response.json()
    except ValueError:
        data = {}
    if not isinstance(data, dict):
        data = {}
    if response.status_code != 200:
        raise PlacementError(str(data.get("error") or f"erreur HTTP {response.status_code}"))
    return data


def _read_state(state_file: Path) -> dict:
    try:
        state = json.loads(state_file.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return state if isinstance(state, dict) else {}


def _write_state(state_file: Path, state: dict) -> None:
    try:
        state_file.parent.mkdir(parents=True, exist_ok=True)
        state_file.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")
    except OSError:
        pass
