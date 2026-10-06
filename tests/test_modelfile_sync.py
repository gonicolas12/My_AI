"""
Tests de la recréation au lancement du modèle my_ai (interfaces/onboarding.py).

Après une modification du Modelfile (à la main, par un « git pull » ou par
⚙️ Réglages), my_ai gardait l'ancien contenu tant que l'utilisateur ne
relançait pas create_custom_model.bat. Aucun vrai Ollama n'est appelé ici :
les modèles installés, « ollama create » et le téléchargement sont simulés.
"""

import subprocess

import pytest

from interfaces import onboarding

MODELFILE = 'FROM qwen3.5:4b\nPARAMETER temperature 0.7\nSYSTEM """\nTu es My_AI.\n"""\n'
CREATE = ["ollama", "create", "my_ai", "-f", "Modelfile"]
# stderr d'un « ollama create » en échec : progression (ANSI), puis l'erreur
FAILED_CREATE = (
    "\x1b[?25l\x1b[1Ggathering model components \x1b[K\n"
    'Error: (line 3): command must be one of "from", "license", "template"\n'
)


@pytest.fixture(name="env")
def _env(monkeypatch, tmp_path):
    """Projet simulé : my_ai et son modèle de base dans Ollama, « ollama create » qui réussit."""
    env = {
        "modelfile": tmp_path / "Modelfile", "exists": True,
        "installed": ["qwen3.5:4b", "my_ai:latest"], "returncode": 0, "stderr": "",
        "calls": [], "captured": [], "pulls": [], "pull_error": None,
    }

    def fake_run(command, **kwargs):
        env["calls"].append(command)
        env["captured"].append(kwargs.get("capture_output"))
        return subprocess.CompletedProcess(
            command, env["returncode"], stdout="", stderr=env["stderr"]
        )

    def fake_pull(model, on_progress, _on_log):
        env["pulls"].append(model)
        if env["pull_error"]:
            raise env["pull_error"]
        on_progress(0.98, "pulling")  # comme Ollama, pas toujours de 100 % final
        env["installed"].append(model)

    env["modelfile"].write_text(MODELFILE, encoding="utf-8")
    monkeypatch.setattr(onboarding, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(onboarding, "_MODELFILE_SYNC", tmp_path / "data" / ".modelfile_sync")
    monkeypatch.setattr(onboarding, "custom_model_exists", lambda: env["exists"])
    monkeypatch.setattr(onboarding, "list_installed_models", lambda: list(env["installed"]))
    monkeypatch.setattr(onboarding, "pull_model", fake_pull)
    monkeypatch.setattr(subprocess, "run", fake_run)
    return env


def test_modified_modelfile_recreates_my_ai_once(env):
    assert onboarding.sync_custom_model() is True
    assert env["calls"] == [CREATE]
    # Lancement suivant, Modelfile inchangé : rien à refaire
    assert onboarding.sync_custom_model() is False
    assert len(env["calls"]) == 1

    # Modification locale ou git pull : my_ai est recréé
    env["modelfile"].write_text(MODELFILE.replace("0.7", "0.5"), encoding="utf-8")
    assert onboarding.sync_custom_model() is True
    assert env["calls"] == [CREATE, CREATE]


def test_console_shows_only_the_start_and_the_outcome(env, capsys):
    """La progression d'« ollama create » (gathering model components, using
    existing layer…, writing manifest, success) n'apparaît pas au lancement."""
    onboarding.sync_custom_model()
    assert env["captured"] == [True]
    assert capsys.readouterr().out == (
        "🔄 Mise à jour du modèle 'my_ai' depuis le Modelfile…\n"
        "✅ Modèle 'my_ai' à jour\n"
    )


def test_unchanged_modelfile_does_not_query_ollama(env, monkeypatch):
    onboarding.sync_custom_model()

    def no_query():
        raise AssertionError("Ollama interrogé alors que le Modelfile n'a pas changé")

    monkeypatch.setattr(onboarding, "custom_model_exists", no_query)
    assert onboarding.sync_custom_model() is False


def test_failed_creation_shows_ollama_error_and_is_retried(env, capsys):
    env["returncode"], env["stderr"] = 1, FAILED_CREATE
    assert onboarding.sync_custom_model() is False
    out = capsys.readouterr().out
    assert "non mis à jour : (line 3): command must be one of" in out
    assert "Nouvel essai au prochain lancement" in out
    assert "\x1b" not in out and "gathering" not in out

    env["returncode"], env["stderr"] = 0, ""
    assert onboarding.sync_custom_model() is True
    assert env["calls"] == [CREATE, CREATE]


def test_nothing_is_created_without_my_ai(env):
    """Ollama arrêté ou assistant passé : ni création ni téléchargement de la
    ligne FROM, et la mise à jour attend un lancement où my_ai est joignable."""
    env["exists"] = False
    assert onboarding.sync_custom_model() is False
    assert env["calls"] == []

    env["exists"] = True
    assert onboarding.sync_custom_model() is True


def test_line_endings_alone_do_not_recreate_my_ai(env):
    onboarding.sync_custom_model()
    env["modelfile"].write_bytes(MODELFILE.replace("\n", "\r\n").encode("utf-8"))
    assert onboarding.sync_custom_model() is False
    assert len(env["calls"]) == 1


def test_model_created_from_the_gui_is_not_recreated_at_launch(env):
    """Assistant de premier lancement ou ⚙️ Réglages → Appliquer."""
    onboarding.create_custom_model(lambda _message: None)
    assert onboarding.sync_custom_model() is False
    assert env["calls"] == [CREATE]


def test_new_base_model_is_pulled_with_progress_first(env, capsys):
    """Sans ce téléchargement, « ollama create » s'en chargerait, sortie masquée :
    la console resterait muette pendant plusieurs Go."""
    env["modelfile"].write_text(MODELFILE.replace("qwen3.5:4b", "qwen3.6:4b"), encoding="utf-8")
    assert onboarding.sync_custom_model() is True
    assert env["pulls"] == ["qwen3.6:4b"]
    assert env["calls"] == [CREATE]
    assert capsys.readouterr().out.endswith(
        "\r📥 Téléchargement de qwen3.6:4b : 100%\n✅ Modèle 'my_ai' à jour\n"
    )


def test_failed_pull_creates_nothing_and_is_retried(env, capsys):
    env["modelfile"].write_text(MODELFILE.replace("qwen3.5:4b", "qwen3.6:4b"), encoding="utf-8")
    env["pull_error"] = RuntimeError("pull model manifest: file does not exist")
    assert onboarding.sync_custom_model() is False
    assert env["calls"] == []
    assert "non mis à jour : pull model manifest: file does not exist" in capsys.readouterr().out

    env["pull_error"] = None
    assert onboarding.sync_custom_model() is True
    assert env["pulls"] == ["qwen3.6:4b", "qwen3.6:4b"]


@pytest.mark.parametrize("base", ["qwen3.5:4b", "minicpm-v", "./modele.gguf"])
def test_installed_or_local_base_model_is_not_pulled(env, base):
    env["installed"].append("minicpm-v:latest")
    (env["modelfile"].parent / "modele.gguf").write_bytes(b"GGUF")
    env["modelfile"].write_text(MODELFILE.replace("qwen3.5:4b", base), encoding="utf-8")
    assert onboarding.sync_custom_model() is True
    assert env["pulls"] == []
    assert env["calls"] == [CREATE]
