"""
Serveur de démonstration de l'interface web : le vrai serveur local et le vrai
ChatService, avec un moteur scénarisé, pour les captures et les mesures
Playwright (frontend/scripts/), sans Ollama.

Usage, depuis la racine du dépôt :
  python tools/interface_web/demo_server.py PORT [JETON] [--rate N] [--fast-launch]
                                            [--dist DOSSIER] [--window]
  --rate N        jetons par seconde du streaming (défaut 80, ~ la carte RTX 3060)
  --fast-launch   écran de chargement écourté
  --dist DOSSIER  autre build à servir (build de profilage, par exemple)
  --window        vraie fenêtre WebView2 (pywebview) sur ce serveur, fermée = arrêt ;
                  avec MY_AI_WEBVIEW_CDP_PORT, les scripts window_*.mjs s'y branchent

Les sessions sont une copie de data/workspaces (les données de test du
suivi, section 4) dans temp/demo_server/PORT/, effacée à l'arrêt (Ctrl+C) ou
au lancement suivant sur le même port : rien n'est écrit dans data/.

Scénarios (mot dans le message) :
  « long »       réponse Markdown d'environ 5 000 jetons (titres, listes, code, tableaux, formules)
  « outils »     préambule, recherche web, calcul, synthèse
  « réflexion »  bloc Réflexion puis réponse
  « supprime »   confirmation de suppression d'un fichier (rien n'est supprimé)
  « erreur »     réponse en échec
  « attends »    réponse lente (10 s), pour le Stop et la file d'attente
  « indexe »     réponse pendant un calcul Python qui tient le GIL 12 s
  autre          courte réponse avec code et formule
"""

import argparse
import secrets
import shutil
import sys
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

# pylint: disable=wrong-import-position,wrong-import-order,import-error
from core.chat_service import ChatService  # noqa: E402
from interfaces.desktop.lifecycle import DesktopApp, DesktopState  # noqa: E402
from test_chat_service import FakeEngine, FakeFileProcessor  # noqa: E402

LONG_SECTION = """## Section {n} : architecture du service

Le service **{n}** reçoit les requêtes, les valide puis les range dans une file. Chaque
requête porte un identifiant, une priorité et une *échéance*. Voici les étapes :

1. lecture de la requête et contrôle du jeton ;
2. validation du schéma (`pydantic`) ;
3. mise en file, avec un délai maximal de `{n}` secondes ;
4. traitement, puis réponse au client.

```python
from dataclasses import dataclass, field
from datetime import datetime, timedelta


@dataclass(order=True)
class Requete:
    priorite: int
    echeance: datetime = field(compare=False)
    contenu: dict = field(default_factory=dict, compare=False)

    def en_retard(self, maintenant: datetime) -> bool:
        \"\"\"Vrai si l'échéance est dépassée.\"\"\"
        return maintenant > self.echeance + timedelta(seconds={n})
```

| Étape | Durée moyenne | Écart type |
|---|---|---|
| Lecture | 0,{n} ms | 0,02 ms |
| Validation | 1,{n} ms | 0,10 ms |
| Traitement | {n}2 ms | 4 ms |

La charge suit une loi de Poisson : la probabilité de $k$ arrivées vaut
$P(k) = \\frac{{\\lambda^k e^{{-\\lambda}}}}{{k!}}$, et le coût total coûte entre 5 $ et 10 $ par mois.

> Remarque : un service saturé doit refuser tôt plutôt que d'accumuler du retard.

"""


def long_answer() -> str:
    """Réponse d'environ 21 000 caractères (5 000 jetons)."""
    text = "# Rapport détaillé\n\nVoici une analyse complète, section par section.\n\n"
    n = 1
    while len(text) < 21_000:
        text += LONG_SECTION.format(n=n)
        n += 1
    return text + "## Conclusion\n\nLe service tient la charge prévue. 🚀\n"


SHORT = """Voici un exemple **simple** :

```js
const somme = (a, b) => a + b;
console.log(somme(2, 3)); // 5
```

La formule $E = mc^2$ relie masse et énergie. Plus d'informations sur [MDN](https://developer.mozilla.org/).
"""


def chunks(text: str, size: int = 4):
    """Découpe en « jetons » d'environ 4 caractères."""
    return [text[i:i + size] for i in range(0, len(text), size)]


def burn(seconds: float = 12.0) -> None:
    """Calcul en Python pur qui tient le GIL (indexation lourde simulée)."""
    end = time.time() + seconds
    x = 0
    while time.time() < end:
        for i in range(20000):
            x = (x * 31 + i) % 1000003


class DemoEngine(FakeEngine):
    """Moteur scénarisé, à vitesse réaliste."""

    def __init__(self, workspaces_dir, rate):
        super().__init__(workspaces_dir)
        self.rate = rate

    def is_complex_query(self, text):
        """Bloc Réflexion affiché d'emblée, comme pour une requête complexe."""
        self.calls.append("is_complex_query")
        return "réflexion" in text.lower() or "outils" in text.lower()

    def process_query_stream(self, user_input, **kwargs):  # noqa: C901
        """Joue le scénario choisi par un mot du message."""
        # pylint: disable=too-many-return-statements
        text = user_input.lower()
        on_token = kwargs["on_token"]
        stop = kwargs["is_interrupted_callback"]
        delay = 1.0 / self.rate

        def stream(content, size=4):
            sent = ""
            for chunk in chunks(content, size):
                if stop() or on_token(chunk) is False:
                    return sent
                sent += chunk
                time.sleep(delay)
            return sent

        def think(content):
            if kwargs.get("on_thinking_token") is None:
                return
            for chunk in chunks(content, 5):
                if stop():
                    return
                kwargs["on_thinking_token"](chunk)
                time.sleep(0.06)  # réflexion lisible (~3 s)
            kwargs["on_thinking_complete"]()

        time.sleep(0.6)  # lecture du prompt
        if "erreur" in text:
            raise ConnectionError("Ollama ne répond pas (simulation)")
        if "supprime" in text:
            accepted = kwargs["on_delete_confirm"](str(Path.home() / "Documents" / "brouillon.txt"))
            return stream("Fichier supprimé." if accepted else "D'accord, je ne supprime rien.")
        if "réflexion" in text:
            think("🧠 Analyse :\nL'utilisateur veut comparer deux approches. Je liste les "
                  "critères : performance, lisibilité, maintenance. Ensuite je pèse chaque "
                  "critère et je conclus.\n")
            return stream("Après réflexion, la **seconde approche** est préférable :\n\n"
                          "- plus lisible ;\n- plus facile à tester ;\n- aussi rapide.\n")
        if "outils" in text:
            think("🧠 Analyse :\nIl faut chercher des sources récentes.\n")
            sent = stream("Je cherche des sources récentes.\n")
            if stop():
                return sent
            kwargs["on_tool_call"]("web_search", {"query": "python 3.14 nouveautés"})
            time.sleep(1.5)
            kwargs["on_tool_result"]("web_search", {}, "[1] https://docs.python.org/3.14/whatsnew\n"
                                     "[2] https://peps.python.org/pep-0745/\n[3] https://realpython.com/")
            kwargs["on_tool_call"]("calculate", {"expression": "2026 - 1991"})
            time.sleep(0.5)
            kwargs["on_tool_result"]("calculate", {}, "35")
            kwargs["on_tool_call"]("synthesis", {})
            time.sleep(1.2)
            return sent + stream("Python 3.14 apporte l'**interpréteur sans GIL** en option [1], "
                                 "les *template strings* [2] et un meilleur message d'erreur [3]. "
                                 "Le langage a 35 ans.\n\n📚 **Sources**\n"
                                 "[1] https://docs.python.org/3.14/whatsnew\n"
                                 "[2] https://peps.python.org/pep-0745/\n[3] https://realpython.com/")
        if "indexe" in text:
            threading.Thread(target=burn, name="indexation-simulee", daemon=True).start()
            return stream(long_answer()[:6000])
        if "attends" in text:
            for _ in range(100):
                if stop():
                    return ""
                time.sleep(0.1)
            return stream("Merci d'avoir attendu.")
        if "long" in text:
            return stream(long_answer())
        return stream(SHORT)


class DemoApp(DesktopApp):  # pylint: disable=too-few-public-methods
    """DesktopApp sans Ollama : étapes du lancement simulées, moteur scénarisé."""

    def __init__(self, workspaces, rate, fast, **kwargs):
        super().__init__(launcher=None, **kwargs)
        self._workspaces = workspaces
        self._rate = rate
        self._fast = fast

    def _launch(self):
        # engine et chat : posés au lancement, comme DesktopApp._launch
        # pylint: disable=attribute-defined-outside-init
        pause = 0.05 if self._fast else 0.7
        steps = [
            ("prefetch", "Préparation du modèle des longs documents…"),
            ("ollama", "Démarrage d'Ollama…"),
            ("onboarding", "Vérification de la configuration…"),
            ("model", "Vérification du modèle my_ai…"),
            ("placement", "Placement du modèle…"),
        ]
        for step, label in steps:
            self._step(step, label)
            time.sleep(pause)
        if not self._fast:
            for line in ("Essai : choix d'Ollama — 61 tok/s", "Essai : contexte en 8 bits — 78 tok/s"):
                self._set_status(detail=line)
                time.sleep(pause)
        self._set_status(placement="modèle sur le GPU (100 %)")
        self._step("engine", "Chargement du moteur…")
        engine = DemoEngine(self._workspaces, self._rate)
        self.engine = engine
        self.chat = ChatService(engine, self.bus.publish, file_processor=FakeFileProcessor(),
                                ui_connected=lambda: self.bus.subscriber_count > 0,
                                on_session_change=lambda sid: self.state.set("current_session", sid))
        self.chat.start()
        time.sleep(pause)
        self._step("services", "Démarrage des services…")
        time.sleep(pause)
        self._restore_session()
        self._set_status(state="ready", step="ready", label="Prêt", detail="")


def main():
    """Lance le serveur jusqu'à Ctrl+C (ou la fermeture de la fenêtre)."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", maxsplit=1)[0])
    parser.add_argument("port", type=int)
    parser.add_argument("token", nargs="?", default=None, help="jeton (tiré au hasard sinon)")
    parser.add_argument("--rate", type=float, default=80.0)
    parser.add_argument("--fast-launch", action="store_true")
    parser.add_argument("--dist", default=None, help="dossier dist à servir")
    parser.add_argument("--window", action="store_true", help="vraie fenêtre WebView2")
    args = parser.parse_args()

    # Dossier ignoré par git ; un arrêt brutal le laisse, le lancement suivant le vide
    tmp = ROOT / "temp" / "demo_server" / str(args.port)
    shutil.rmtree(tmp, ignore_errors=True)
    tmp.mkdir(parents=True)
    workspaces = tmp / "workspaces"
    if (ROOT / "data" / "workspaces").is_dir():
        shutil.copytree(ROOT / "data" / "workspaces", workspaces)
    else:
        workspaces.mkdir()
    if args.dist:
        from interfaces.desktop import server as desktop_server  # pylint: disable=import-outside-toplevel
        desktop_server.DIST_DIR = Path(args.dist)

    token = args.token or secrets.token_urlsafe(16)
    app = DemoApp(workspaces, args.rate, args.fast_launch, port=args.port,
                  state=DesktopState(tmp / ".desktop_state.json"))
    app.token = token  # pylint: disable=attribute-defined-outside-init
    url = app.start()
    print(f"DEMO {url}", flush=True)
    try:
        if args.window:
            from interfaces.desktop.window import open_window  # pylint: disable=import-outside-toplevel
            if open_window(app, url):
                return  # fenêtre fermée
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        app.shutdown()
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    # Fil principal laissé tel quel : pywebview vérifie qu'il s'appelle MainThread
    main()
