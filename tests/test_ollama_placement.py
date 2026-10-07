"""
Tests du placement automatique du modèle sur le GPU ou le processeur
(utils/ollama_placement.py).

Ollama écarte par défaut le GPU intégré au processeur, alors que sur un Core
Ultra 7 255H celui-ci lit le prompt 4 fois plus vite que le processeur. Aucun
vrai Ollama n'est appelé ici : le serveur, ses redémarrages et ses vitesses
sont simulés.
"""

import os

import pytest

from utils import ollama_placement as placement

EXTRA = placement.EXTRA_GPU_ENV
ARC_140T = "Intel(R) Arc(TM) 140T GPU (15GB) 32.0.101.8826"
# Vitesses mesurées sur un Core Ultra 7 255H (lecture, écriture, en tokens/s)
CPU_SPEEDS = (70.0, 11.4)
IGPU_SPEEDS = (285.0, 12.6)


class FakeOllama:
    """Serveur Ollama simulé, qui place le modèle selon ses variables d'environnement."""

    def __init__(self):
        self.version = "0.35.1"
        self.installed = ["my_ai:latest", "qwen3.5:4b"]
        # Part du modèle sur un GPU : choix par défaut, puis GPU intégré autorisé
        self.default_share = 0.0
        self.integrated_share = 100.0
        self.speeds = {"cpu": CPU_SPEEDS, "gpu": IGPU_SPEEDS}
        self.integrated_error = None  # le runner échoue sur le GPU intégré
        self.empty_stats = False  # réponses sans durées de calcul
        self.up = True
        self.env = {}  # variables de placement du serveur en cours
        self.loaded = None  # (modèle, part sur GPU) du modèle chargé
        self.restarts = []
        self.measured = []  # placements mesurés, dans l'ordre

    def restart(self, placement_env):
        """Redémarrage du serveur par le lanceur (cf. launch_unified._restart_ollama)."""
        self.restarts.append(dict(placement_env))
        self.env, self.loaded = dict(placement_env), None
        return True

    def _share(self):
        if placement.server_env(os.environ, self.env).get("OLLAMA_IGPU_ENABLE") == "1":
            return self.integrated_share
        return self.default_share

    def request(self, _base_url, path, payload=None):
        """Réponse d'Ollama à un appel de son API (cf. placement._request)."""
        if not self.up:
            raise placement.PlacementError("Ollama injoignable (ConnectionError)")
        static = {
            "/api/version": {"version": self.version},
            "/api/tags": {"models": [{"name": name} for name in self.installed]},
            "/api/show": {"details": {
                "family": "qwen35", "parameter_size": "4.7B", "quantization_level": "Q4_K_M",
            }},
        }
        if path in static:
            return static[path]
        if path == "/api/ps":
            loaded = [] if self.loaded is None else [self.loaded]
            return {"models": [
                {"name": model, "size": 1000, "size_vram": round(10 * share)}
                for model, share in loaded
            ]}
        assert path == "/api/generate", path
        return self._generate(payload)

    def _generate(self, payload):
        if payload.get("keep_alive") == 0:
            self.loaded = None
            return {}
        share = self._share()
        if share > self.default_share and self.integrated_error:
            raise placement.PlacementError(self.integrated_error)
        self.loaded = (payload["model"], share)
        if "prompt" not in payload or self.empty_stats:
            return {}  # chargement seul
        kind = "gpu" if share > 0 else "cpu"
        prompt_tps, gen_tps = self.speeds[kind]
        tokens = payload["options"]["num_predict"]
        if tokens > 2:  # pas la chauffe
            self.measured.append(kind)
        return {
            "prompt_eval_count": 500, "prompt_eval_duration": 500 / prompt_tps * 1e9,
            "eval_count": tokens, "eval_duration": tokens / gen_tps * 1e9,
        }


@pytest.fixture(name="ollama")
def _ollama(monkeypatch):
    """Ollama local sur un portable à GPU intégré, sans variable de placement posée."""
    fake = FakeOllama()
    for key in EXTRA:
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setattr(placement, "_request", fake.request)
    monkeypatch.setattr(placement, "_local_ollama_url", lambda: "http://127.0.0.1:11434")
    monkeypatch.setattr(placement, "_graphics_adapters", lambda: [ARC_140T])
    monkeypatch.setattr(placement, "_dedicated_gpu_vram", lambda: None)
    monkeypatch.setattr(placement, "_default_model", lambda: "qwen3.5:4b")
    return fake


@pytest.fixture(name="state")
def _state(tmp_path):
    return tmp_path / "data" / ".ollama_placement.json"


def place(ollama, state):
    return placement.ensure_best_placement(ollama.restart, state_file=state)


def test_faster_integrated_gpu_is_kept(ollama, state, capsys):
    assert place(ollama, state) == "gpu-integre"
    # Processeur (choix d'Ollama) mesuré, puis GPU intégré, où le serveur reste
    assert ollama.measured == ["cpu", "gpu"]
    assert ollama.restarts == [EXTRA]
    assert placement.saved_env(state) == EXTRA
    assert placement.placement_label(state) == "modèle sur le GPU intégré"
    out = capsys.readouterr().out
    assert "• Processeur : lecture 70 tok/s, écriture 11,4 tok/s" in out
    assert "• GPU intégré : lecture 285 tok/s, écriture 12,6 tok/s" in out
    assert "réponse type 1,8× plus rapide qu'avec le processeur" in out


@pytest.mark.parametrize("share, label", [
    (100.0, "modèle sur le GPU"),
    (61.3, "modèle à 61 % sur le GPU"),
])
def test_graphics_card_is_left_to_ollama(ollama, state, share, label):
    """Carte graphique dédiée, même trop petite pour tout le modèle : Ollama le
    répartit déjà tout seul, rien à mesurer ni à redémarrer."""
    ollama.default_share = share
    assert place(ollama, state) == "gpu"
    assert ollama.restarts == [] and ollama.measured == []
    assert placement.saved_env(state) == {}
    assert placement.placement_label(state) == label


def test_busy_graphics_card_keeps_integrated_gpu_out(ollama, state, monkeypatch):
    """Carte dédiée pleine au lancement (génération d'images…) : une fois
    autorisé, le GPU intégré pourrait garder le modèle, même la carte libérée."""
    monkeypatch.setattr(placement, "_dedicated_gpu_vram", lambda: 8.0)
    assert place(ollama, state) == "gpu"
    assert ollama.restarts == [] and ollama.measured == []
    assert placement.saved_env(state) == {}


def test_slower_integrated_gpu_is_dropped(ollama, state, capsys):
    """GPU intégré trop petit pour tout le modèle : moitié GPU, moitié
    processeur, c'est plus lent que le processeur seul (mesuré sur un Core
    Ultra 7 255H)."""
    ollama.integrated_share = 45.7
    ollama.speeds["gpu"] = (127.0, 6.6)
    assert place(ollama, state) == "cpu"
    assert ollama.restarts == [EXTRA, {}]
    assert placement.saved_env(state) == {}
    out = capsys.readouterr().out
    assert "• GPU intégré (46 % du modèle) : lecture 127 tok/s" in out
    assert "le GPU intégré ne fait pas mieux ici" in out


def test_without_any_gpu_the_model_stays_on_cpu(ollama, state, capsys):
    ollama.integrated_share = 0.0
    assert place(ollama, state) == "cpu"
    assert ollama.measured == ["cpu"]
    assert ollama.restarts == [EXTRA, {}]
    assert placement.placement_label(state) == "modèle sur le processeur"
    assert "aucun GPU utilisable par Ollama" in capsys.readouterr().out


def test_integrated_gpu_failure_falls_back_to_cpu(ollama, state, capsys):
    ollama.integrated_error = "llama runner process has terminated: exit status 2"
    assert place(ollama, state) == "cpu"
    assert ollama.restarts == [EXTRA, {}]
    out = capsys.readouterr().out
    assert "• GPU intégré : échec (llama runner process has terminated" in out
    assert "le GPU intégré n'a pas pu le faire tourner" in out


def test_placement_is_measured_once(ollama, state):
    place(ollama, state)
    ollama.restarts.clear()
    ollama.measured.clear()
    assert place(ollama, state) == "gpu-integre"
    assert ollama.restarts == [] and ollama.measured == []


@pytest.mark.parametrize("change", ["Ollama", "modèle", "pilote"])
def test_measured_again_after_a_change(ollama, state, monkeypatch, change):
    """Mise à jour d'Ollama, autre modèle, autre carte graphique ou autre pilote."""
    place(ollama, state)
    ollama.restarts.clear()
    if change == "Ollama":
        ollama.version = "0.36.0"
    elif change == "modèle":
        ollama.installed = ["qwen3.5:4b"]  # my_ai supprimé : modèle de config.yaml
    else:
        monkeypatch.setattr(placement, "_graphics_adapters", lambda: [ARC_140T[:-4] + "9000"])
    assert place(ollama, state) == "gpu-integre"
    # Choix par défaut d'Ollama remesuré sans l'ancien placement, puis GPU intégré
    assert ollama.restarts == [{}, EXTRA]


def test_user_setting_is_never_overridden(ollama, state, monkeypatch):
    """OLLAMA_IGPU_ENABLE=0 posé par l'utilisateur : seule la variable qu'il
    n'a pas fixée est essayée, et la sienne garde sa valeur."""
    monkeypatch.setenv("OLLAMA_IGPU_ENABLE", "0")
    assert place(ollama, state) == "cpu"
    assert ollama.restarts == [{"OLLAMA_VULKAN": "1"}, {}]
    assert placement.server_env({"OLLAMA_IGPU_ENABLE": "0"}, EXTRA) == {
        "OLLAMA_IGPU_ENABLE": "0", "OLLAMA_VULKAN": "1",
    }


def test_user_setting_change_triggers_a_new_measure(ollama, state, monkeypatch):
    place(ollama, state)
    ollama.restarts.clear()
    # GPU intégré autorisé par l'utilisateur lui-même : Ollama l'utilise d'office
    monkeypatch.setenv("OLLAMA_IGPU_ENABLE", "1")
    assert place(ollama, state) == "gpu"
    assert ollama.restarts == [{}]


def test_nothing_happens_without_ollama_or_model(ollama, state):
    """Ollama arrêté, ou assistant de premier lancement passé : rien n'est
    mesuré ni retenu, nouvel essai au lancement suivant."""
    ollama.up = False
    assert place(ollama, state) is None
    ollama.up, ollama.installed = True, []
    assert place(ollama, state) is None
    assert ollama.restarts == [] and not state.exists()

    ollama.installed = ["my_ai:latest"]
    assert place(ollama, state) == "gpu-integre"


def test_failed_measure_restores_ollama_and_is_retried(ollama, state, capsys):
    ollama.empty_stats = True
    assert place(ollama, state) is None
    assert ollama.restarts == [{}]  # serveur relancé tel que le lanceur l'avait démarré
    assert not state.exists()
    out = capsys.readouterr().out
    assert "⚠️ Placement du modèle non mesuré : mesure de vitesse vide" in out
    assert "Nouvel essai au prochain lancement" in out

    ollama.empty_stats = False
    assert place(ollama, state) == "gpu-integre"


@pytest.mark.parametrize("url, local", [
    ("http://127.0.0.1:11434", True),
    ("http://localhost:11434", True),
    ("http://192.168.1.20:11434", False),
    ("http://127.0.0.1:8080", False),
])
def test_only_the_local_ollama_is_calibrated(url, local):
    """Ollama sur une autre machine ou un autre port : ce n'est pas le serveur
    que le lanceur redémarre."""
    assert placement._is_local_ollama(url) is local  # pylint: disable=protected-access
