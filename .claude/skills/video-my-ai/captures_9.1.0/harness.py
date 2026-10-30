#!/usr/bin/env python3
"""
Démo de la vidéo My_AI 9.1.0, sans Ollama :
  - la fenêtre : serveur de démonstration (tools/interface_web/demo_server.py),
  - le vrai Relay (relay/relay_server.py), sans tunnel, sur 127.0.0.1,
  - la conversation Code (relay/code_hub.py) avec une boucle agentique
    scénarisée, dont les outils s'exécutent dans la VRAIE extension VS Code.

Usage : python3 harness.py PORT_FENETRE DOSSIER_TMP FICHIER_INFO
"""

import asyncio
import base64
import json
import os
import re
import secrets
import shutil
import sys
import threading
import time
from pathlib import Path

ROOT = Path(os.environ.get("MY_AI_ROOT", "/home/user/My_AI"))
sys.path.insert(0, str(ROOT / "tools" / "interface_web"))

import demo_server as ds  # noqa: E402  (insère ROOT et ROOT/tests dans sys.path)
from interfaces.desktop.code import CodeService  # noqa: E402
from interfaces.desktop.lifecycle import DesktopApp, DesktopState  # noqa: E402
from interfaces.desktop.previews import PreviewStore  # noqa: E402
from relay import relay_server as rs  # noqa: E402
from relay.code_hub import CodeHub  # noqa: E402
from relay.relay_bridge import RelayBridge  # noqa: E402

# Le scheduler global du Relay lirait data/ du dépôt : la démo n'en a pas besoin
rs.RelayServer._init_scheduler = lambda self: None

RATE = float(os.environ.get("VIDEO_RATE", "26"))
RELAY_PORT = int(os.environ.get("VIDEO_RELAY_PORT", "8765"))

# ── Scénario (textes de la réponse ; les outils agissent pour de vrai) ──────

APP_OLD = '''    LIVRES[livre.id] = livre
    return livre
'''
APP_NEW = '''    LIVRES[livre.id] = livre
    return livre


@app.get("/livres/{livre_id}")
def lire_livre(livre_id: int) -> Livre:
    if livre_id not in LIVRES:
        raise HTTPException(status_code=404, detail="Livre introuvable")
    return LIVRES[livre_id]
'''
TEST_OLD = '''    assert client.post("/livres", json=livre).status_code == 409
'''
TEST_NEW = '''    assert client.post("/livres", json=livre).status_code == 409


def test_livre_introuvable():
    reponse = client.get("/livres/999")
    assert reponse.status_code == 404
    assert reponse.json()["detail"] == "Livre introuvable"
'''

ROUTE_ANSWER = (
    "C'est fait : `GET /livres/{livre_id}` renvoie le livre demandé, "
    "ou une **404** s'il n'existe pas.\n\n"
    "```python\n"
    "@app.get(\"/livres/{livre_id}\")\n"
    "def lire_livre(livre_id: int) -> Livre:\n"
    "    if livre_id not in LIVRES:\n"
    "        raise HTTPException(status_code=404, detail=\"Livre introuvable\")\n"
    "    return LIVRES[livre_id]\n"
    "```"
)
TEST_ANSWER = ("Test ajouté dans `tests/test_app.py` : `test_livre_introuvable` vérifie "
               "qu'un identifiant inconnu renvoie bien une **404**.")
COMMIT_ANSWER = (
    "Voici un message de commit pour ces changements :\n\n"
    "```text\n"
    "feat(api): route GET /livres/{id}, 404 si le livre n'existe pas\n\n"
    "- lire_livre renvoie le livre demandé\n"
    "- test_livre_introuvable couvre la 404\n"
    "```"
)


def _plural_tests(output: str) -> str:
    """« Les **4 tests** passent, en 0,52 s. » d'après la vraie sortie de pytest."""
    match = re.search(r"(\d+) passed[^\n]*? in ([\d.]+)s", output)
    failed = re.search(r"(\d+) failed", output)
    if failed:
        return f"**{failed.group(1)} test(s)** échouent : je regarde pourquoi."
    if not match:
        return "Les tests sont terminés."
    count, seconds = match.group(1), match.group(2).replace(".", ",")
    return (f"Les **{count} tests** passent, en {seconds} s : "
            "la nouvelle route et sa 404 sont couvertes.")


class VideoCodeExecutor:
    """Boucle agentique scénarisée : le texte est écrit d'avance, les outils
    passent par la vraie extension VS Code (lecture, édition, commande)."""

    def __init__(self, **_config):
        pass

    @staticmethod
    async def _pause(seconds):
        await asyncio.sleep(seconds)

    async def _stream(self, text, segment, on_chunk):
        shown = ""
        for piece in ds.chunks(text, 3):
            shown += piece
            on_chunk(shown, segment)
            await asyncio.sleep(1 / RATE)

    async def _tool(self, run, name, arguments):
        call = {"call_id": secrets.token_hex(8), "name": name, "input": arguments}
        run["on_tool_call_announced"](call)
        result = await run["tool_executor"].call(call_id=call["call_id"], name=name,
                                                 input_data=arguments)
        run["on_tool_result"](call["call_id"], result)
        return result

    async def run(self, **run):
        message = run["user_message"].lower()
        run["history"].append({"role": "user", "content": run["user_message"]})
        await self._pause(0.6)  # le modèle « réfléchit »
        if "commit" in message:
            text = COMMIT_ANSWER
            await self._stream(text, 0, run["on_chunk"])
        elif "test pour" in message or "un test" in message:
            intro = "Je regarde d'abord les tests existants."
            await self._stream(intro, 0, run["on_chunk"])
            await self._tool(run, "read_file", {"path": "tests/test_app.py"})
            await self._tool(run, "edit_file", {"path": "tests/test_app.py",
                                                "old_string": TEST_OLD, "new_string": TEST_NEW})
            await self._tool(run, "open_file", {"path": "tests/test_app.py", "line": 23})
            await self._pause(0.4)
            await self._stream(TEST_ANSWER, 1, run["on_chunk"])
            text = intro + "\n\n" + TEST_ANSWER
        elif "test" in message:
            intro = "Je lance la suite de tests."
            await self._stream(intro, 0, run["on_chunk"])
            result = await self._tool(run, "run_command", {"command": "python -m pytest -q"})
            await self._pause(0.4)
            final = _plural_tests(result.get("content", ""))
            await self._stream(final, 1, run["on_chunk"])
            text = intro + "\n\n" + final
        else:
            intro = "Je regarde d'abord `src/app.py`."
            await self._stream(intro, 0, run["on_chunk"])
            await self._tool(run, "read_file", {"path": "src/app.py"})
            await self._tool(run, "edit_file", {"path": "src/app.py",
                                                "old_string": APP_OLD, "new_string": APP_NEW})
            await self._tool(run, "open_file", {"path": "src/app.py", "line": 33})
            await self._pause(0.4)
            await self._stream(ROUTE_ANSWER, 1, run["on_chunk"])
            text = intro + "\n\n" + ROUTE_ANSWER
        run["history"].append({"role": "assistant", "content": text})
        return text


def _b64u(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


class VideoApp(ds.DemoApp):
    """Serveur de démonstration, mais le vrai Relay (sans tunnel) et la vraie extension."""

    info_file: Path = None

    @property
    def code(self):
        with self._services_lock:
            if self._code is None:
                hub = CodeHub(store=self._workspaces.parent / "code_conversation.json",
                              executor_factory=VideoCodeExecutor)
                self._video_hub = hub  # pylint: disable=attribute-defined-outside-init
                self._code = CodeService(hub, self.bus.publish, lambda: self.bus.last_seq)
            return self._code

    def _demo_llm(self):
        return {"chat_url": "demo", "model": "my_ai", "num_ctx": 32768,
                "describe_image": lambda _image, _question: "Capture d'écran (démo)."}

    def start_relay(self, tunnel=None):
        with self._relay_lock:
            if self.relay is None or not self.relay.is_running():
                _ = self.code
                self.relay = rs.RelayServer(
                    ai_engine=self.engine,
                    config={"host": "127.0.0.1", "port": RELAY_PORT, "response_timeout": 500},
                    agent_service=self.agents.executor_tap(),
                    code_hub=self._video_hub)
                self.relay.start(start_tunnel=False)
                self._video_hub.set_llm_resolver(self._demo_llm)
                self._write_info()
        self._watch_relay_status()
        return self.relay_status()

    def stop_relay(self):
        return DesktopApp.stop_relay(self)

    def _write_info(self):
        relay = self.relay
        key = relay._e2e_key  # pylint: disable=protected-access
        payload = json.dumps({"urls": [f"http://127.0.0.1:{RELAY_PORT}"],
                              "token": relay.auth_token, "key": _b64u(key)})
        info = {"local_url": relay.local_url, "access_code": relay.access_code,
                "connection_string": _b64u(payload.encode("utf-8"))}
        self.info_file.write_text(json.dumps(info, indent=2), encoding="utf-8")
        print("RELAY", json.dumps(info), flush=True)

    def _launch(self):
        super()._launch()
        # Chat du téléphone : traité par le moteur scénarisé, comme dans l'appli
        self.chat.attach_bridge(RelayBridge())


# Conversations de la barre latérale : (nom, jours écoulés, heure)
SESSIONS = (
    ("Révision : protocoles TCP/IP", 0, "11:42"),
    ("Script de sauvegarde en Python", 0, "09:15"),
    ("Résumé du rapport de stage", 1, "18:03"),
    ("Optimiser une requête SQL lente", 1, "14:27"),
    ("Plan de la présentation IA locale", 2, "10:51"),
    ("Traduire la doc en anglais", 3, "16:38"),
    ("Regex pour analyser des logs", 5, "21:10"),
    ("Idées de projets Python", 8, "13:22"),
)


def seed_sessions(workspaces: Path) -> None:
    """Conversations plausibles (noms et dates seulement) dans le dossier de la démo."""
    from datetime import datetime, timedelta  # pylint: disable=import-outside-toplevel
    from core.session_manager import SessionManager  # pylint: disable=import-outside-toplevel
    manager = SessionManager(str(workspaces))
    today = datetime.now()
    for name, days, hour in SESSIONS:
        workspace_id = manager.create_workspace(name)
        hh, mm = (int(x) for x in hour.split(":"))
        stamp = (today - timedelta(days=days)).replace(hour=hh, minute=mm, second=0,
                                                         microsecond=0).isoformat()
        for filename in ("metadata.json", "state.json"):
            path = workspaces / workspace_id / filename
            data = json.loads(path.read_text(encoding="utf-8"))
            meta = data if filename == "metadata.json" else data["metadata"]
            meta["created_at"] = meta["last_modified"] = stamp
            meta["message_count"] = 2
            if filename == "state.json":
                data["conversation_history"] = [
                    {"role": "user", "content": name, "timestamp": stamp},
                    {"role": "assistant", "content": "…", "timestamp": stamp},
                ]
            path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def main():
    port = int(sys.argv[1])
    tmp = Path(sys.argv[2]).resolve()
    info = Path(sys.argv[3]).resolve()
    shutil.rmtree(tmp, ignore_errors=True)
    tmp.mkdir(parents=True)
    workspaces = tmp / "workspaces"
    workspaces.mkdir()
    seed_sessions(workspaces)
    sys.argv[0] = os.path.abspath(sys.argv[0])
    os.chdir(tmp)
    VideoApp.info_file = info
    app = VideoApp(workspaces, 80.0, True, port=port,
                   state=DesktopState(tmp / ".desktop_state.json"))
    app.token = "videotoken"  # pylint: disable=attribute-defined-outside-init
    app.server.previews = PreviewStore(directory=tmp / "outputs" / "artifacts")
    url = app.start()
    print(f"DEMO {url}", flush=True)
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        app.shutdown()


if __name__ == "__main__":
    main()
