"""
Tests de la voix de l'interface web (interfaces/desktop/voice.py, api_voice.py)

Micro, Whisper et synthèse sont simulés : on vérifie ce que la fenêtre voit,
c'est-à-dire les événements (état du micro, texte dicté, lecture en cours) et
les messages de l'interface Tk quand une dépendance manque.
"""

import sys
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from interfaces.desktop.events import EventBus, validate_event
from interfaces.desktop.server import DesktopServer
from interfaces.desktop.voice import INPUT_UNAVAILABLE, OUTPUT_UNAVAILABLE, VoiceService
from test_chat_service import FakeEngine  # pylint: disable=import-error
from test_desktop_server import AUTH, BASE, PORT, FakeApp  # pylint: disable=import-error


class FakeVoiceInput:
    """VoiceInput : enregistre au premier toggle, dicte au second."""

    available = True

    def __init__(self, on_result=None, on_state=None):
        self.on_result = on_result
        self.on_state = on_state
        self.state = "idle"
        self.recording = False

    @staticmethod
    def unavailable_reason():
        return "faster-whisper indisponible : simulé"

    def toggle(self):
        if self.recording:
            self.stop()
        else:
            self.recording = True
            self.state = "recording"
            self.on_state("recording")

    def stop(self):
        self.recording = False
        self.on_state("transcribing")
        self.on_result("Bonjour depuis le micro")
        self.state = "idle"
        self.on_state("idle")


class FakeVoiceOutput:
    """VoiceOutput : lit à la demande ; finish() termine la lecture en cours."""

    available = True

    def __init__(self):
        self.is_speaking = False
        self.spoken = []
        self._on_state = None

    def speak(self, text, on_state=None):
        self._on_state = on_state
        self.spoken.append(text)
        self.is_speaking = True
        on_state("speaking")

    def stop(self):
        self.is_speaking = False
        if self._on_state:
            self._on_state("idle")

    def finish(self):
        self.stop()


@pytest.fixture(name="voice")
def voice_fixture(monkeypatch):
    """Service de la voix sur un micro et une synthèse simulés."""
    output = FakeVoiceOutput()
    monkeypatch.setitem(sys.modules, "interfaces.desktop.voice_input",
                        SimpleNamespace(VoiceInput=FakeVoiceInput,
                                        _WhisperWorker=SimpleNamespace(
                                            get=lambda: SimpleNamespace(stop=lambda: None))))
    monkeypatch.setitem(sys.modules, "interfaces.desktop.voice_output",
                        SimpleNamespace(VoiceOutput=lambda: output))
    bus = EventBus()
    events = []
    bus.subscribe(events.append)
    saved = []
    service = VoiceService(bus.publish, autoread=False, save_autoread=saved.append)
    return SimpleNamespace(service=service, events=events, output=output, saved=saved, bus=bus)


def payloads(events, event_type):
    return [event["payload"] for event in events if event["type"] == event_type]


def test_microphone_modules_can_be_loaded_ahead(voice, monkeypatch):
    voice.service.preload_input()
    assert isinstance(voice.service._voice_input(), FakeVoiceInput)  # pylint: disable=protected-access
    assert payloads(voice.events, "voice.input") == []  # rien ne s'enregistre

    # Modules absents : le préchargement se tait, le clic dira pourquoi
    broken = VoiceService(voice.bus.publish)
    monkeypatch.setitem(sys.modules, "interfaces.desktop.voice_input", None)
    broken.preload_input()


def test_dictation_reaches_the_window_as_events(voice):
    assert voice.service.toggle_input() == "recording"
    assert voice.service.toggle_input() == "idle"
    states = [p["state"] for p in payloads(voice.events, "voice.input")]
    assert states == ["recording", "transcribing", "idle"]
    assert payloads(voice.events, "voice.transcript") == [{"text": "Bonjour depuis le micro"}]
    for event in voice.events:
        validate_event(event)


def test_missing_dictation_dependencies_show_the_tk_message(voice, monkeypatch):
    monkeypatch.setattr(FakeVoiceInput, "available", False)
    assert voice.service.toggle_input() == "error"
    assert payloads(voice.events, "voice.input")[-1] == {"state": "error",
                                                         "message": INPUT_UNAVAILABLE}


def test_reading_an_answer_toggles_and_follows_its_key(voice):
    assert voice.service.toggle_speak("**Bonjour**", "a1") == "speaking"
    assert voice.output.spoken == ["**Bonjour**"]
    # Une autre réponse : la première s'arrête, la seconde est lue
    voice.service.toggle_speak("Autre", "a2")
    outputs = payloads(voice.events, "voice.output")
    assert [(p["state"], p["key"]) for p in outputs] == [
        ("speaking", "a1"), ("idle", "a1"), ("speaking", "a2"),
    ]
    assert voice.service.status()["speaking_key"] == "a2"
    # Même bouton : la lecture s'arrête
    assert voice.service.toggle_speak("Autre", "a2") == "idle"
    assert voice.service.status()["output_state"] == "idle"


def test_missing_speech_engine_shows_the_tk_message(voice):
    voice.output.available = False
    assert voice.service.speak("Bonjour", "a1") == "error"
    assert payloads(voice.events, "voice.output")[-1]["message"] == OUTPUT_UNAVAILABLE


def test_autoread_is_saved_and_switching_it_off_stops_reading(voice):
    assert voice.service.set_autoread(True) is True
    voice.service.speak("Longue réponse", "a1")
    assert voice.service.set_autoread(False) is False
    assert voice.saved == [True, False]
    assert voice.output.is_speaking is False
    assert voice.service.status()["autoread"] is False


def test_voice_routes(voice, tmp_path):
    app = FakeApp(None, voice.bus, engine=FakeEngine(tmp_path / "workspaces"))
    app.voice = voice.service
    server = DesktopServer(app)
    server.port = PORT
    client = TestClient(server.fastapi, base_url=BASE)

    status = client.get("/api/voice", headers=AUTH).json()
    assert set(status) == {"input_available", "output_available", "input_state",
                           "output_state", "speaking_key", "autoread"}
    assert client.post("/api/voice/input", headers=AUTH).json() == {"state": "recording"}
    assert client.post("/api/voice/input/stop", headers=AUTH).json() == {"ok": True}
    assert client.post("/api/voice/speak", headers=AUTH,
                       json={"text": "Salut", "key": "m1"}).json() == {"state": "speaking"}
    assert client.post("/api/voice/stop", headers=AUTH).json() == {"ok": True}
    assert client.put("/api/voice/autoread", headers=AUTH,
                      json={"enabled": True}).json() == {"autoread": True}
    assert client.post("/api/voice/stop").status_code == 401
