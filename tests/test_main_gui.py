"""
Tests de « python main.py --mode gui » (main.py)

Le mode graphique ouvre la fenêtre de l'interface web, comme launch_unified.py,
mais sans redémarrer Ollama ni placer le modèle (« GUI seule »). Ni fenêtre ni
moteur ici : main.py est chargé sans ses imports lourds, la fenêtre est simulée.
"""

# pylint: disable=protected-access

import asyncio
import importlib.util
import sys
import types
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(name="main_module")
def _main_module(monkeypatch):
    """main.py chargé sans le moteur, avec ses étapes de lancement notées."""
    calls = []
    stubs = {
        "interfaces.cli": {"CLIInterface": None},
        "core.ai_engine": {"AIEngine": None},
        "core.passage_embeddings": {"prefetch_in_background": lambda: calls.append("prefetch")},
        "interfaces.onboarding": {"sync_custom_model": lambda: calls.append("model")},
        "core.network": {"configure_network_environment": lambda: None},
    }
    for name, attributes in stubs.items():
        module = types.ModuleType(name)
        vars(module).update(attributes)
        monkeypatch.setitem(sys.modules, name, module)
    monkeypatch.setattr(sys, "path", list(sys.path))  # main.py y ajoute sa racine
    spec = importlib.util.spec_from_file_location("main_under_test", ROOT / "main.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.calls = calls
    return module


@pytest.fixture(name="window")
def _window(main_module, monkeypatch):
    """Fenêtre simulée : run_desktop note le lanceur reçu ; os._exit arrête le test."""
    opened = []
    launcher = types.ModuleType("launch_unified")
    lifecycle = types.ModuleType("interfaces.desktop.lifecycle")
    lifecycle.without_ollama_setup = lambda module: ("sans configuration d'Ollama", module)
    lifecycle.run_desktop = opened.append
    monkeypatch.setitem(sys.modules, "launch_unified", launcher)
    monkeypatch.setitem(sys.modules, "interfaces.desktop.lifecycle", lifecycle)
    monkeypatch.setattr(main_module.os, "_exit",
                        lambda code: (_ for _ in ()).throw(SystemExit(code)))
    return types.SimpleNamespace(opened=opened, launcher=launcher)


def test_gui_mode_opens_the_web_window_without_ollama_setup(main_module, window, monkeypatch):
    monkeypatch.setattr(sys, "argv", ["main.py", "--mode", "gui"])
    with pytest.raises(SystemExit) as stopped:
        asyncio.run(main_module.main())
    assert stopped.value.code == 0
    assert window.opened == [("sans configuration d'Ollama", window.launcher)]
    # Modèle des longs documents et my_ai : sur l'écran de chargement de la fenêtre
    assert main_module.calls == []


def test_cli_mode_keeps_its_launch_steps(main_module, monkeypatch):
    ran = []

    class CLI:
        async def run(self):
            ran.append("cli")

    monkeypatch.setattr(main_module, "CLIInterface", CLI)
    monkeypatch.setattr(sys, "argv", ["main.py"])
    asyncio.run(main_module.main())
    assert main_module.calls == ["prefetch", "model"] and ran == ["cli"]
