"""Mesure de l'empreinte énergétique et carbone d'une session My_AI.

Instrumente le vrai chemin d'inférence du projet (models.local_llm.LocalLLM ->
Ollama) avec codecarbon, en deux phases :

  1. Phase IDLE   : poste allumé, aucune inférence. Donne le plancher de
                    consommation qui existerait de toute façon.
  2. Phase CHARGE : boucle de requêtes representatives d'un usage normal.

Le coût réel imputable a My_AI est le *delta* entre les deux phases, pas la
consommation absolue de la phase de charge : le poste de travail est allumé
que l'utilisateur interroge l'IA ou non.

Usage :
    python tools/measure_energy.py                       # 3 min idle + 10 min charge
    python tools/measure_energy.py --idle 2 --load 5     # durees personnalisees

Sorties : claudedocs/energy_measurement_<horodatage>.{json,md}
"""

from __future__ import annotations

import argparse
import json
import platform
import subprocess
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

import models.local_llm as llm_mod
from models.local_llm import LocalLLM

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import psutil  # noqa: E402  (dependance codecarbon)
from codecarbon import OfflineEmissionsTracker  # noqa: E402

# Requetes representatives d'un usage normal de My_AI : question courte,
# explication technique, redaction, analyse de code, synthese.
PROMPTS = [
    "Bonjour, peux-tu me rappeler en deux phrases ce que tu sais faire ?",
    "Explique-moi la difference entre une base vectorielle et une base relationnelle.",
    "Redige un court paragraphe professionnel annoncant la mise en production d'un outil interne.",
    "Que fait ce code Python : [x**2 for x in range(10) if x % 2 == 0] ?",
    "Resume en trois points les avantages d'un LLM execute en local par rapport a une API cloud.",
    "Quelles sont les bonnes pratiques pour nommer les variables en Python ?",
    "Traduis en anglais : « la conformite RGPD impose la minimisation des donnees ».",
    "Donne-moi un plan en quatre parties pour une note de cadrage technique.",
]


# --------------------------------------------------------------------------
# Echantillonnage materiel
# --------------------------------------------------------------------------
class HardwareSampler:
    """Echantillonne CPU/RAM, et la puissance batterie si le poste est debranche.

    La decharge batterie (root\\WMI BatteryStatus.DischargeRate, en mW) est la
    seule *mesure* materielle directe disponible sur ce poste : elle donne la
    puissance instantanee reellement tiree par la machine entiere. Elle n'est
    exploitable que sur batterie ; sur secteur, Windows renvoie 0.
    """

    def __init__(self, interval: float = 5.0):
        self.interval = interval
        self.cpu_samples: list[float] = []
        self.ram_samples: list[float] = []
        self.power_samples_mw: list[float] = []
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._ps: subprocess.Popen | None = None

    def _battery_reader(self) -> None:
        """Un seul process PowerShell en boucle : evite de payer un spawn par mesure."""
        script = (
            "while($true){"
            "$b = Get-CimInstance -Namespace root\\WMI -ClassName BatteryStatus "
            "-ErrorAction SilentlyContinue | Select-Object -First 1;"
            "if($b){ Write-Output \"$($b.DischargeRate)\" } else { Write-Output 'NA' };"
            f"Start-Sleep -Seconds {int(self.interval)} }}"
        )
        try:
            self._ps = subprocess.Popen(
                ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            for line in self._ps.stdout:  # type: ignore[union-attr]
                if self._stop.is_set():
                    break
                line = line.strip()
                if line and line != "NA":
                    try:
                        self.power_samples_mw.append(float(line))
                    except ValueError:
                        pass
        except Exception:
            pass

    def _cpu_reader(self) -> None:
        while not self._stop.wait(self.interval):
            self.cpu_samples.append(psutil.cpu_percent(interval=None))
            self.ram_samples.append(psutil.virtual_memory().percent)

    def start(self) -> None:
        """Lance les threads de lecture CPU/RAM et batterie (si Windows)."""
        psutil.cpu_percent(interval=None)  # amorce le compteur differentiel
        self._stop.clear()
        self._thread = threading.Thread(target=self._cpu_reader, daemon=True)
        self._thread.start()
        if platform.system() == "Windows":
            threading.Thread(target=self._battery_reader, daemon=True).start()

    def stop(self) -> None:
        """Arrete les threads et le process PowerShell de lecture batterie."""
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=self.interval + 2)
        if self._ps and self._ps.poll() is None:
            self._ps.terminate()

    def summary(self) -> dict:
        """Resume les echantillons CPU/RAM et batterie en quelques statistiques simples."""
        def avg(xs: list[float]) -> float | None:
            return round(sum(xs) / len(xs), 2) if xs else None

        # Les valeurs nulles = poste sur secteur : on ne les compte pas comme
        # une puissance mesuree de 0 W.
        discharging = [p for p in self.power_samples_mw if p > 0]
        return {
            "cpu_percent_avg": avg(self.cpu_samples),
            "cpu_percent_max": round(max(self.cpu_samples), 2) if self.cpu_samples else None,
            "ram_percent_avg": avg(self.ram_samples),
            "battery_power_w_avg": round(avg(discharging) / 1000, 2) if discharging else None,
            "battery_samples": len(discharging),
            "on_battery": bool(discharging),
        }


# --------------------------------------------------------------------------
# Instrumentation du chemin d'inference reel
# --------------------------------------------------------------------------
def instrument_llm():
    """Capture les compteurs de tokens natifs d'Ollama sans devier du code My_AI.

    LocalLLM.generate() jette la reponse HTTP brute apres extraction du texte ;
    on enveloppe _resilient_post pour relever eval_count / prompt_eval_count,
    qui sont les compteurs du tokenizer du modele (et non une estimation).
    """
    stats: list[dict] = []
    original = llm_mod._resilient_post

    def wrapped(url, **kwargs):
        response = original(url, **kwargs)
        try:
            payload = response.json()
            stats.append(
                {
                    "prompt_tokens": payload.get("prompt_eval_count", 0),
                    "output_tokens": payload.get("eval_count", 0),
                    "total_duration_s": round(payload.get("total_duration", 0) / 1e9, 3),
                    "eval_duration_s": round(payload.get("eval_duration", 0) / 1e9, 3),
                }
            )
        except Exception:
            pass
        return response

    llm_mod._resilient_post = wrapped
    return stats


# --------------------------------------------------------------------------
# Phases de mesure
# --------------------------------------------------------------------------
def make_tracker(name: str) -> OfflineEmissionsTracker:
    """Construit un tracker codecarbon pour la phase de mesure."""
    # Mode offline : aucun appel reseau de geolocalisation (coherent avec la
    # philosophie 100 % local du projet et compatible proxy d'entreprise).
    return OfflineEmissionsTracker(
        country_iso_code="FRA",
        project_name=f"My_AI-{name}",
        measure_power_secs=5,
        save_to_file=False,
        log_level="error",
    )


def run_phase(name: str, duration_s: float, work=None) -> dict:
    """Execute une phase de mesure codecarbon + echantillonnage materiel."""
    print(f"\n=== Phase {name.upper()} : {duration_s / 60:.1f} min ===")
    sampler = HardwareSampler()
    tracker = make_tracker(name)

    sampler.start()
    tracker.start()
    started = time.time()
    try:
        if work is None:
            while time.time() - started < duration_s:
                time.sleep(1)
        else:
            work(started, duration_s)
    finally:
        emissions_kg = tracker.stop()
        sampler.stop()
    elapsed = time.time() - started

    energy_kwh = float(tracker.final_emissions_data.energy_consumed)
    return {
        "phase": name,
        "duration_s": round(elapsed, 1),
        "energy_kwh": energy_kwh,
        "emissions_kgco2eq": float(emissions_kg or 0.0),
        "avg_power_w": round(energy_kwh * 1000 * 3600 / elapsed, 2) if elapsed else None,
        "cpu_energy_kwh": float(tracker.final_emissions_data.cpu_energy),
        "gpu_energy_kwh": float(tracker.final_emissions_data.gpu_energy),
        "ram_energy_kwh": float(tracker.final_emissions_data.ram_energy),
        "cpu_power_w_codecarbon": float(tracker.final_emissions_data.cpu_power),
        "hardware": sampler.summary(),
    }


def build_load(llm, stats: list[dict]) -> callable:
    """Construit la fonction de travail pour la phase de charge, qui boucle sur"""
    def work(started: float, duration_s: float) -> None:
        i = 0
        while time.time() - started < duration_s:
            prompt = PROMPTS[i % len(PROMPTS)]
            i += 1
            t0 = time.time()
            answer = llm.generate(prompt, use_history=False, save_history=False)
            print(
                f"  [{i:>2}] {time.time() - t0:6.1f}s  "
                f"{len(answer) if answer else 0:>5} car.  {prompt[:52]}..."
            )
    return work


# --------------------------------------------------------------------------
# Agregation
# --------------------------------------------------------------------------
def summarize(env: dict, idle: dict, load: dict, stats: list[dict],
              timestamp: str | None = None) -> dict:
    """Ramene les deux phases a des metriques par unite d'usage.

    Le cout impute a My_AI est le *delta* charge - repos : le poste consomme
    deja la puissance de repos, que l'utilisateur interroge l'IA ou non.
    """
    n_req = len(stats)
    out_tokens = sum(s["output_tokens"] for s in stats)
    in_tokens = sum(s["prompt_tokens"] for s in stats)

    intensity = (
        load["emissions_kgco2eq"] / load["energy_kwh"] if load["energy_kwh"] else 0.0
    )  # kgCO2eq/kWh, telle qu'appliquee par codecarbon pour la France

    def derive(marginal_kwh: float, source: str) -> dict:
        """Metriques ramenees a l'unite d'usage, pour une source d'energie donnee."""
        return {
            "source": source,
            "marginal_energy_kwh": marginal_kwh,
            "marginal_wh_per_request": round(marginal_kwh * 1e3 / n_req, 4) if n_req else None,
            "marginal_wh_per_1k_output_tokens": round(
                marginal_kwh * 1e6 / out_tokens, 4
            ) if out_tokens else None,
            # intensity est en kgCO2eq/kWh -> x1e3 pour des grammes.
            "marginal_gco2eq_per_request": round(
                marginal_kwh * intensity * 1e3 / n_req, 5
            ) if n_req else None,
            "marginal_gco2eq_per_1k_output_tokens": round(
                marginal_kwh * intensity * 1e6 / out_tokens, 5
            ) if out_tokens else None,
        }

    # Source 1 : codecarbon. Sur un CPU AMD sous Windows, ni RAPL ni NVML ne sont
    # disponibles : codecarbon *modelise* la puissance CPU a partir du TDP et de la
    # charge. C'est une estimation, pas une mesure.
    cc_marginal_kwh = max(
        load["energy_kwh"] - idle["avg_power_w"] * load["duration_s"] / 3.6e6, 0.0
    )

    # Source 2 : decharge batterie. Puissance reellement tiree par la machine
    # entiere, lue sur le controleur de batterie. Mesure materielle directe.
    bat_idle = idle["hardware"]["battery_power_w_avg"]
    bat_load = load["hardware"]["battery_power_w_avg"]
    bat_marginal_kwh = (
        max(bat_load - bat_idle, 0.0) * load["duration_s"] / 3.6e6
        if bat_idle and bat_load
        else None
    )

    return {
        "timestamp": timestamp or datetime.now().isoformat(timespec="seconds"),
        "environment": env,
        "idle": idle,
        "load": load,
        "requests": {
            "count": n_req,
            "input_tokens": in_tokens,
            "output_tokens": out_tokens,
            "avg_latency_s": round(
                sum(s["total_duration_s"] for s in stats) / n_req, 2
            ) if n_req else None,
            "tokens_per_s": round(
                out_tokens / sum(s["eval_duration_s"] for s in stats), 1
            ) if n_req and sum(s["eval_duration_s"] for s in stats) else None,
            "detail": stats,
        },
        "grid_intensity_gco2eq_per_kwh": round(intensity * 1000, 1),
        "derived_codecarbon": derive(cc_marginal_kwh, "codecarbon (modele TDP, estimation)"),
        "derived_battery": (
            derive(bat_marginal_kwh, "decharge batterie (mesure materielle)")
            if bat_marginal_kwh is not None
            else {"source": "decharge batterie", "unavailable": "poste sur secteur"}
        ),
    }

def report(result: dict) -> None:
    """Restitution console : les deux sources cote a cote, jamais l'une sans l'autre."""
    idle, load = result["idle"], result["load"]
    n_req = result["requests"]["count"]
    out_tokens = result["requests"]["output_tokens"]

    print("\n" + "=" * 68)
    print(f"Modele                : {result['environment']['model']}")
    print(f"Requetes / tokens     : {n_req} requetes, {out_tokens} tokens generes "
          f"({out_tokens // n_req if n_req else 0}/requete)")
    print(f"Debit                 : {result['requests']['tokens_per_s']} tokens/s")
    print(f"Intensite reseau (FR) : {result['grid_intensity_gco2eq_per_kwh']} gCO2eq/kWh")
    for key, label, p_idle, p_load in (
        ("derived_codecarbon", "CODECARBON (estimation TDP)",
         idle["avg_power_w"], load["avg_power_w"]),
        ("derived_battery", "BATTERIE (mesure materielle)",
         idle["hardware"]["battery_power_w_avg"], load["hardware"]["battery_power_w_avg"]),
    ):
        d = result[key]
        print("-" * 68)
        print(f"  {label}")
        if d.get("unavailable"):
            print(f"    indisponible : {d['unavailable']}")
            continue
        print(f"    Puissance         : {p_idle} W a vide -> {p_load} W en charge "
              f"(delta {round(p_load - p_idle, 2)} W)")
        print(f"    Energie marginale : {d['marginal_energy_kwh'] * 1000:.3f} Wh "
              f"sur {load['duration_s'] / 60:.1f} min")
        print(f"    Par requete       : {d['marginal_wh_per_request']} Wh / "
              f"{d['marginal_gco2eq_per_request']} gCO2eq")
        print(f"    Par 1000 tokens   : {d['marginal_wh_per_1k_output_tokens']} Wh / "
              f"{d['marginal_gco2eq_per_1k_output_tokens']} gCO2eq")
    print("=" * 68)


# --------------------------------------------------------------------------
def main() -> int:
    """Mesure l'empreinte energetique et carbone d'une session My_AI."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--idle", type=float, default=3.0, help="minutes de reference a vide")
    parser.add_argument("--load", type=float, default=10.0, help="minutes de charge d'inference")
    parser.add_argument("--model", default=None, help="modele Ollama (defaut : celui de My_AI)")
    parser.add_argument(
        "--recompute",
        metavar="FICHIER.json",
        default=None,
        help="recalcule les metriques derivees d'une mesure existante, sans remesurer",
    )
    args = parser.parse_args()

    outdir = PROJECT_ROOT / "claudedocs"
    outdir.mkdir(exist_ok=True)

    if args.recompute:
        path = Path(args.recompute)
        raw = json.loads(path.read_text(encoding="utf-8"))
        result = summarize(
            raw["environment"], raw["idle"], raw["load"],
            raw["requests"]["detail"], timestamp=raw.get("timestamp"),
        )
        path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
        report(result)
        print(f"\nMetriques recalculees : {path}")
        return 0

    stats = instrument_llm()
    llm = LocalLLM(model=args.model) if args.model else LocalLLM()
    if not llm.is_ollama_available:
        print("ERREUR : Ollama injoignable — demarrer Ollama avant la mesure.")
        return 1

    print("Prechauffage du modele (exclu de la mesure)...")
    llm.generate("Bonjour", use_history=False, save_history=False)
    stats.clear()
    time.sleep(5)

    env = {
        "host": platform.node(),
        "os": f"{platform.system()} {platform.release()}",
        "cpu": platform.processor(),
        "physical_cores": psutil.cpu_count(logical=False),
        "python": platform.python_version(),
        "model": llm.model,
        "num_ctx": llm.gen_num_ctx,
        "temperature": llm.gen_temperature,
    }

    idle = run_phase("idle", args.idle * 60)
    load = run_phase("charge", args.load * 60, work=build_load(llm, stats))

    result = summarize(env, idle, load, stats)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_path = outdir / f"energy_measurement_{stamp}.json"
    json_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")

    report(result)
    print(f"\nResultats bruts : {json_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
