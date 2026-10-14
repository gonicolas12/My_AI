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
  --vraie-voix    micro et synthèse du PC ; sinon voix simulée : la dictée renvoie
                  « texte dicté (démo) », la lecture dure deux secondes, en silence
  --premier-lancement
                  l'assistant de premier lancement s'affiche au lancement

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
  « artefact »   page HTML (avec script) et logo SVG : volet d'aperçu
  « document »   documents produits (PDF, Word, Markdown) : cartes et aperçus
  « chemin »     réponse qui cite des chemins existants (Explorateur au clic)
  « dessine »    génération d'image, avec progression
  « génère un fichier X.py »  génération de fichier (carte, Téléchargements)
  autre          courte réponse avec code et formule

Les fichiers produits vont dans temp/demo_server/PORT/outputs/, dossier des
fichiers « produits par l'appli » pour ce serveur. Rien n'est écrit dans data/ :
les notes restent en mémoire, l'historique des requêtes est une copie de
data/command_history.db, la recherche globale lit les sessions copiées (mots
exacts, sans embeddings) et l'indexation des dossiers projet est simulée. Les
Réglages et l'assistant travaillent sur un Ollama simulé (modèles, téléchargement,
création de my_ai) et des réglages en mémoire : ni config.yaml ni Modelfile ne
changent. La Mémoire montre des faits et des documents fictifs, en mémoire, et les
messages des sessions copiées (modifiés ou supprimés à la source dans ces copies).
Les Prompts sont ceux par défaut de la vraie bibliothèque, dans
temp/demo_server/PORT/prompt_templates.json.
"""

import argparse
import os
import secrets
import shutil
import sys
import threading
import time
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

# pylint: disable=wrong-import-position,wrong-import-order,import-error
from core.chat_service import ChatService  # noqa: E402
from core.memory_store import MemoryStore  # noqa: E402
from core.prompt_library import PromptLibrary  # noqa: E402
from interfaces.desktop.lifecycle import DesktopApp, DesktopState  # noqa: E402
from interfaces.desktop.previews import PreviewStore  # noqa: E402
from interfaces.desktop.model_setup import OllamaSetup  # noqa: E402
from interfaces.desktop.voice import VoiceService  # noqa: E402
from core.command_history import CommandHistory  # noqa: E402
from test_chat_service import FakeEngine, FakeFileProcessor, FakeRLHF  # noqa: E402

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


ARTIFACT = """Voici une petite page interactive, et un logo :

```html
<!doctype html>
<html lang="fr">
<head><meta charset="utf-8"><title>Compteur</title>
<style>
  body { font-family: system-ui, sans-serif; background: #1a1a1a; color: #fff;
         display: grid; place-items: center; height: 100vh; margin: 0; }
  button { background: #ff6b47; color: #fff; border: 0; border-radius: 8px;
           padding: 10px 18px; font-size: 16px; cursor: pointer; }
</style></head>
<body>
  <div>
    <h1>Compteur</h1>
    <p>Clics : <strong id="n">0</strong></p>
    <button onclick="document.getElementById('n').textContent++">Cliquer</button>
    <p id="api"></p>
    <p id="memo"></p>
  </div>
  <script>
    // L'artefact ne peut pas joindre l'API de l'appli (iframe isolée)
    fetch('/api/status').then(r => r.status).catch(() => 'bloqué')
      .then(s => { document.getElementById('api').textContent = 'API : ' + s; });
    // Mais il garde son état : stockage en mémoire de l'aperçu (origine opaque)
    localStorage.setItem('visites', String(Number(localStorage.getItem('visites') || 0) + 1));
    document.getElementById('memo').textContent = 'Stockage : ' + localStorage.getItem('visites');
  </script>
</body>
</html>
```

```svg
<svg xmlns="http://www.w3.org/2000/svg" width="160" height="160" viewBox="0 0 160 160">
  <circle cx="80" cy="80" r="70" fill="#ff6b47"/>
  <text x="80" y="92" font-size="36" text-anchor="middle" fill="#fff">AI</text>
</svg>
```
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


class DemoImageGenerator:
    """Générateur d'image simulé : progression, puis un PNG dans outputs/."""

    def __init__(self, outputs: Path):
        self.outputs = outputs

    @staticmethod
    def is_available():
        """Toujours disponible."""
        return True

    def generate(self, prompt, on_progress, is_interrupted):
        """Dix étapes de diffusion, puis un dégradé à l'orange de l'appli."""
        from PIL import Image  # pylint: disable=import-outside-toplevel

        for step in range(1, 11):
            if is_interrupted():
                return SimpleNamespace(interrupted=True, success=False, image_path=None,
                                       message="⏹️ Génération de l'image interrompue.")
            on_progress(step / 10, f"Diffusion {step * 10} %")
            time.sleep(0.25)
        image = Image.new("RGB", (768, 512))
        pixels = image.load()
        for x in range(768):
            for y in range(512):
                pixels[x, y] = (255, max(0, 107 - x // 12), min(255, 71 + y // 4))
        target = self.outputs / f"image_{int(time.time())}.png"
        image.save(target)
        return SimpleNamespace(interrupted=False, success=True, image_path=str(target),
                               message=f"🎨 Image générée : « {prompt} »")


class DemoSearch:
    """Recherche globale par mots exacts dans les sessions copiées (sans embeddings)."""

    def __init__(self, sessions):
        self.sessions = sessions

    @staticmethod
    def is_available():
        """Toujours disponible."""
        return True

    def _messages(self):
        for workspace in self.sessions.list_workspaces():
            state = self.sessions.load_workspace(workspace["id"]) or {}
            for index, message in enumerate(state.get("conversation_history", [])):
                text = (message.get("text") or "").strip()
                if text:
                    yield workspace, index, message, text

    def search(self, query, n_results=10):
        """Messages qui contiennent tous les mots de la requête."""
        words = [word.lower() for word in query.split() if len(word) >= 2]
        results = []
        for workspace, index, message, text in self._messages():
            if words and all(word in text.lower() for word in words):
                results.append({
                    "workspace_id": workspace["id"], "workspace_name": workspace.get("name"),
                    "message_index": index,
                    "role": "user" if message.get("is_user") else "assistant",
                    "timestamp": str(message.get("timestamp", "")), "excerpt": text,
                })
        return results[:n_results]

    def reindex(self, force=False):
        """Compte les messages, comme une réindexation."""
        del force
        return {"indexed": 0, "messages": sum(1 for _ in self._messages()), "removed": 0}


class DemoIndexer:
    """Indexation des dossiers projet simulée : compte les fichiers, 20 ms chacun."""

    def __init__(self):
        self.manifest = {}

    @staticmethod
    def is_available():
        """Toujours disponible."""
        return True

    def index_folder(self, workspace_id, folder_path, force=False, progress_cb=None):
        """Parcourt le dossier (300 fichiers au plus) en publiant la progression."""
        del force
        files = []
        for root, _dirs, names in os.walk(folder_path):
            files.extend(os.path.join(root, name) for name in names)
            if len(files) >= 300:
                break
        files = files[:300]
        for done, path in enumerate(files, 1):
            time.sleep(0.02)
            if progress_cb:
                progress_cb(done, len(files), os.path.relpath(path, folder_path))
        self.manifest.setdefault(workspace_id, {})[folder_path] = len(files)
        return {"status": "success", "folder": folder_path, "total_files": len(files),
                "chunks": len(files) * 3}

    def get_status(self, workspace_id):
        """Dossiers indexés de la session."""
        return {"folders": [{"path": path, "file_count": count, "chunks": count * 3,
                             "indexed_at": time.strftime("%Y-%m-%d")}
                            for path, count in self.manifest.get(workspace_id, {}).items()]}

    def remove_folder(self, workspace_id, folder_path):
        """Détache un dossier."""
        return self.manifest.get(workspace_id, {}).pop(folder_path, None) is not None


DEMO_FACTS = [
    ("preference", "Préfère des réponses concises, en français"),
    ("preference", "Aime les exemples de code commentés, en Python de préférence"),
    ("preference", "Thème sombre partout, police de code Cascadia Code"),
    ("decision", "Interface de bureau : React et FastAPI dans une fenêtre WebView2"),
    ("decision", "Les prompts ne sont jamais commités dans le dépôt"),
    ("decision", "Revue de code obligatoire avant toute fusion sur main"),
    ("person", "Camille : responsable produit, relit les comptes rendus du vendredi"),
    ("person", "Hugo : développeur backend, référent pour la base SQLite"),
    ("person", "Léa : designer, prépare les maquettes du tableau de bord"),
    ("procedure", "Pour publier : tests, build du frontend, puis commit de dist/"),
    ("procedure", "Sauvegarde hebdomadaire du dossier data/ sur le disque externe"),
    ("procedure", "Nouveau modèle : ollama pull, puis Réglages > Appliquer"),
    ("technical", "Carte graphique : RTX 3060, 12 Go de mémoire vidéo"),
    ("technical", "Python 3.11, Node 22, Windows 11"),
    ("technical", "Le serveur local écoute sur 127.0.0.1, port choisi au lancement"),
    ("technical", "ChromaDB stocke les embeddings dans data/vector_store"),
    ("general", "Le projet My_AI tourne en local avec Ollama"),
    ("general", "Réunion d'équipe le lundi à 10 h"),
    ("general", "Le rapport trimestriel est attendu pour le 15 du mois"),
    ("general", "Objectif du trimestre : une version web de l'interface"),
    ("general", "Le dossier temp/ ne contient que des fichiers jetables"),
    ("preference", "Notifications discrètes, sans son"),
    ("technical", "Les tests se lancent avec pytest depuis la racine du dépôt\n"
                  "Les tests du frontend avec npm run test"),
]

DEMO_DOCUMENTS = [
    ("rapport_trimestriel.pdf", "Rapport trimestriel. Le chiffre d'affaires progresse de 12 % "
                                "sur le trimestre, porté par les abonnements."),
    ("rapport_trimestriel.pdf", "La marge brute atteint 31 %, contre 28 % au trimestre "
                                "précédent. Les coûts d'hébergement baissent de 8 %."),
    ("rapport_trimestriel.pdf", "Perspectives : lancement de la version web au prochain "
                                "trimestre, recrutement de deux développeurs."),
    ("note_projet.docx", "Note de projet. L'interface Tk est remplacée par une interface "
                         "web servie localement, dans une fenêtre native."),
    ("note_projet.docx", "Calendrier : maquettes en juin, chat et barre latérale en "
                         "juillet, panneaux en septembre."),
]


class DemoVectors:  # pylint: disable=too-few-public-methods
    """VectorMemory de la démonstration : entrées lues par leur identifiant."""

    def __init__(self, store):
        self.store = store

    def get_entry(self, entry_id, collection_type="document"):
        """Entrée d'une collection, ou None."""
        return next((entry for entry in self.store.entries(collection_type)
                     if entry["id"] == entry_id), None)


class DemoMemoryStore:  # pylint: disable=too-many-instance-attributes
    """MemoryStore en mémoire : faits et documents fictifs, messages des sessions copiées."""

    describe_provenance = staticmethod(MemoryStore.describe_provenance)

    def __init__(self, sessions, search):
        self.sessions = sessions
        self.conversation_search = search
        self.vector_memory = DemoVectors(self)
        self.lock = threading.Lock()
        self.facts = []
        self.next_id = 1
        for minutes, (category, value) in enumerate(DEMO_FACTS):
            self._add({"category": category, "key": value.split("\n", 1)[0][:80],
                       "value": value, "source": "conversation" if minutes % 3 else "manual",
                       "updated_at": f"2026-10-{10 + minutes // 8:02d}T09:{minutes:02d}:00"})
        self.documents = [
            {"id": f"doc_{name}_{index}", "content": content,
             "metadata": {"document_name": name, "chunk_index": index % 3,
                          "created": "2026-10-08T14:30:00"}}
            for index, (name, content) in enumerate(DEMO_DOCUMENTS)]
        # Messages retirés de l'index seul (« sinon réapparaît au prochain réindex »)
        self.hidden = set()

    def _add(self, fact):
        fact.update(kind="fact", id=self.next_id, created_at=fact["updated_at"],
                    confidence=1.0 if fact["source"] == "manual" else 0.8)
        self.next_id += 1
        self.facts.insert(0, fact)
        return fact["id"]

    def entries(self, collection_type):
        """Documents, ou messages des sessions (relus à chaque appel, comme un index à jour)."""
        if collection_type == "document":
            return list(self.documents)
        entries = []
        for workspace in self.sessions.list_workspaces():
            state = self.sessions.load_workspace(workspace["id"]) or {}
            for index, message in enumerate(state.get("conversation_history", [])):
                entry_id = f"conv_{workspace['id']}_{index}"
                text = (message.get("text") or "").strip()
                if text and entry_id not in self.hidden:
                    entries.append({"id": entry_id, "content": text, "metadata": {
                        "workspace_id": workspace["id"],
                        "workspace_name": workspace.get("name") or workspace["id"],
                        "message_index": index,
                        "role": "user" if message.get("is_user") else "assistant",
                        "timestamp": str(message.get("timestamp", ""))}})
        return entries

    def list_facts(self, query="", category=None, limit=25, offset=0):
        """Faits filtrés, les plus récents d'abord."""
        query = (query or "").strip().lower()
        with self.lock:
            rows = [dict(fact) for fact in self.facts
                    if (not category or fact["category"] == category)
                    and (not query or query in fact["value"].lower()
                         or query in fact["key"].lower())]
        return rows[offset:offset + limit], len(rows)

    def list_vectors(self, collection_type="document", query="", limit=25, offset=0):
        """Entrées d'une collection, filtrées par sous-chaîne."""
        query = (query or "").strip().lower()
        rows = [{"kind": "vector", "collection": collection_type, **entry}
                for entry in self.entries(collection_type)
                if not query or query in entry["content"].lower()]
        return rows[offset:offset + limit], len(rows)

    def add_fact(self, category, key, value, source="manual"):
        """Fait ajouté à la main."""
        with self.lock:
            return self._add({"category": category, "key": key, "value": value,
                              "source": source,
                              "updated_at": time.strftime("%Y-%m-%dT%H:%M:%S")})

    def update_fact(self, fact_id, value):
        """Nouveau contenu d'un fait."""
        with self.lock:
            for fact in self.facts:
                if fact["id"] == fact_id:
                    fact["value"] = value
                    fact["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
                    return True
        return False

    def delete_fact(self, fact_id):
        """Supprime un fait."""
        with self.lock:
            before = len(self.facts)
            self.facts = [fact for fact in self.facts if fact["id"] != fact_id]
            return len(self.facts) < before

    def update_vector(self, entry_id, new_text, collection_type="document", **_source):
        """Nouveau texte d'un document (index seul)."""
        if collection_type != "document":
            return False
        for entry in self.documents:
            if entry["id"] == entry_id:
                entry["content"] = new_text
                return True
        return False

    def delete_vector(self, entry_id, collection_type="document", **_source):
        """Retire une entrée de l'index."""
        if collection_type == "document":
            before = len(self.documents)
            self.documents = [entry for entry in self.documents if entry["id"] != entry_id]
            return len(self.documents) < before
        self.hidden.add(entry_id)
        return True

    def stats(self):
        """Compteurs, comme MemoryStore.stats."""
        return {"facts": len(self.facts), "documents": len(self.documents),
                "conversations": len(self.entries("conversation"))}


class DemoEngine(FakeEngine):
    """Moteur scénarisé, à vitesse réaliste."""

    def __init__(self, workspaces_dir, rate, outputs: Path):
        super().__init__(workspaces_dir)
        self.rate = rate
        self.outputs = outputs
        self.generator = DemoImageGenerator(outputs)
        # Historique des requêtes : copie de la vraie base, jamais la base elle-même
        history_db = Path(workspaces_dir).parent / "command_history.db"
        if (ROOT / "data" / "command_history.db").is_file():
            shutil.copy2(ROOT / "data" / "command_history.db", history_db)
        self.command_history = CommandHistory(db_path=str(history_db))
        self.search_engine = DemoSearch(self.session_manager)
        self.indexer = DemoIndexer()
        self.memory_store = DemoMemoryStore(self.session_manager, self.search_engine)
        # Prompts par défaut, jamais data/prompt_templates.json
        self.prompt_library = PromptLibrary(
            path=str(Path(workspaces_dir).parent / "prompt_templates.json"))

    def get_memory_store(self):
        """Mémoire de la démonstration."""
        return self.memory_store

    def get_conversation_search(self):
        """Recherche globale de la démonstration."""
        return self.search_engine

    def get_folder_indexer(self):
        """Indexeur de dossiers de la démonstration."""
        return self.indexer

    def is_image_generation_request(self, text):
        """« dessine » : génération d'image."""
        self.calls.append("is_image_generation_request")
        return "dessine" in text.lower()

    async def process_query(self, query, context=None, is_interrupted_callback=None):
        """Génération de fichier : un petit programme écrit dans outputs/."""
        del context, is_interrupted_callback
        last = query.split()[-1] if query.split() else ""
        name = last if last.count(".") == 1 else "calcul.py"
        target = self.outputs / name
        target.write_text("def somme(a, b):\n    return a + b\n\n\nprint(somme(2, 3))\n",
                          encoding="utf-8")
        return {"type": "file_generation", "success": True, "filename": name,
                "file_path": str(target)}

    def demo_documents(self):
        """Documents « produits » : copies des fichiers de test, et une note Markdown."""
        documents = self.outputs / "documents"
        documents.mkdir(parents=True, exist_ok=True)
        produced = []
        fixtures = ROOT / "temp" / "migration_test_data" / "fichiers"
        for name in ("rapport_trimestriel.pdf", "note_projet.docx"):
            if (fixtures / name).is_file():
                shutil.copy2(fixtures / name, documents / name)
                produced.append(documents / name)
        note = documents / "synthese.md"
        note.write_text("# Synthèse\n\n- Chiffre d'affaires : **+12 %**\n- Marge : 31 %\n\n"
                        "| Trimestre | Ventes |\n|---|---|\n| T1 | 120 |\n| T2 | 134 |\n",
                        encoding="utf-8")
        produced.append(note)
        return produced

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
        if "artefact" in text:
            return stream(ARTIFACT, size=12)
        if "document" in text:
            produced = self.demo_documents()
            kwargs["on_tool_call"]("generate_document", {"format": "pdf"})
            time.sleep(0.6)
            for path in produced:
                kwargs["on_document"](str(path))
            kwargs["on_tool_result"]("generate_document", {}, f"Document créé : {produced[0]}")
            kwargs["on_tool_call"]("synthesis", {})
            names = ", ".join(path.name for path in produced)
            return stream(f"J'ai rédigé les documents demandés ({names}). "
                          f"Le rapport est dans {produced[0]}.\n")
        if "chemin" in text:
            readme = ROOT / "README.md"
            return stream(f"Le fichier de présentation est {readme} et la documentation est "
                          f"dans `{ROOT / 'docs'}`. Ce chemin n'existe pas : "
                          "C:\\inexistant\\x.txt.\n")
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


class DemoVoiceInput:
    """Micro simulé : enregistre, puis « transcrit » en une demi-seconde."""

    available = True

    def __init__(self, on_result=None, on_state=None):
        self.on_result = on_result
        self.on_state = on_state
        self.state = "idle"
        self.recording = False

    @staticmethod
    def unavailable_reason():
        """Toujours disponible."""
        return ""

    def toggle(self):
        """Enregistre, ou arrête et transcrit."""
        if self.recording:
            self.stop()
            return
        self.recording = True
        self.state = "recording"
        self.on_state("recording")

    def stop(self):
        """Transcription simulée."""
        if not self.recording:
            return
        self.recording = False
        self.state = "transcribing"
        self.on_state("transcribing")

        def transcribe():
            time.sleep(0.5)
            self.on_result("texte dicté (démo)")
            self.state = "idle"
            self.on_state("idle")

        threading.Thread(target=transcribe, daemon=True).start()


class DemoVoiceOutput:
    """Synthèse simulée : une lecture dure deux secondes, sans son."""

    available = True

    def __init__(self):
        self.is_speaking = False
        self._on_state = None
        self._generation = 0

    def speak(self, _text, on_state=None):
        """Lecture silencieuse."""
        self._on_state = on_state
        self._generation += 1
        generation = self._generation
        self.is_speaking = True
        on_state("speaking")

        def finish():
            time.sleep(2)
            if generation == self._generation and self.is_speaking:
                self.is_speaking = False
                on_state("idle")

        threading.Thread(target=finish, daemon=True).start()

    def stop(self):
        """Coupe la lecture."""
        self._generation += 1
        self.is_speaking = False
        if self._on_state:
            self._on_state("idle")


class DemoVoiceService(VoiceService):
    """Voix de la démonstration : micro et synthèse simulés."""

    def _voice_input(self):
        if self._input is None:
            self._input = DemoVoiceInput(on_result=self._on_transcript,
                                         on_state=self._on_input_state)
        return self._input

    def _voice_output(self):
        if self._output is None:
            self._output = DemoVoiceOutput()
        return self._output


class DemoOllamaSetup(OllamaSetup):
    """Ollama simulé : modèles, téléchargement par couches, création de my_ai ; réglages en mémoire."""

    def __init__(self):
        self.installed = ["qwen3.5:4b", "qwen3.5:2b", "my_ai:latest", "llava:latest"]
        self.base = "qwen3.5:4b"
        self.config = {"temperature": 0.7, "num_ctx": 32768, "timeout": 1200, "language": "fr",
                       "languages": ["fr", "en", "es", "de", "it", "pt"],
                       "relay_auto_start": False}
        self.done = False

    def values(self):
        return dict(self.config)

    def model_choices(self):
        return ["qwen3.5:2b", "qwen3.5:4b", "qwen3.5:9b"]

    def ollama_reachable(self):
        return True

    def installed_models(self):
        return list(self.installed)

    def base_model(self):
        return self.base

    def pull(self, name, on_progress, on_log):
        on_log("pulling manifest")
        for layer in ("2f5d1c", "9a8b7e", "c41d03"):
            for step in range(1, 11):
                time.sleep(0.12)
                on_progress(step / 10, f"pulling {layer}")
        for line in ("verifying sha256 digest", "writing manifest", "success"):
            time.sleep(0.2)
            on_log(line)
        if name not in self.installed:
            self.installed.append(name)

    def apply_base(self, base):
        self.base = base

    def create_custom_model(self, on_log):
        for line in ("gathering model components", "using existing layer sha256:2f5d1c",
                     "writing manifest", "success"):
            time.sleep(0.3)
            on_log(line)

    def save_generation(self, temperature, num_ctx, timeout):
        self.config.update(temperature=temperature, num_ctx=num_ctx, timeout=timeout)

    def set_flag(self, name, value):
        key = {"language.default": "language", "relay.auto_start": "relay_auto_start"}.get(name)
        if key:
            self.config[key] = value

    def mark_done(self):
        self.done = True

    def forget_done(self):
        self.done = False


class DemoApp(DesktopApp):  # pylint: disable=too-few-public-methods
    """DesktopApp sans Ollama : étapes du lancement simulées, moteur scénarisé."""

    def __init__(self, workspaces, rate, fast, real_voice=False, first_launch=False, **kwargs):
        super().__init__(launcher=None, **kwargs)
        self._workspaces = workspaces
        self._rate = rate
        self._fast = fast
        self._first_launch_demo = first_launch
        # Réglages et assistant : Ollama simulé, jamais config.yaml ni le Modelfile
        self.ollama_setup = DemoOllamaSetup()
        if not real_voice:
            # Lecture automatique gardée en mémoire : rien n'est écrit dans config.yaml
            self._voice = DemoVoiceService(self.bus.publish)

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
            if step == "onboarding" and self._first_launch_demo:
                self._set_status(state="onboarding", label="Configuration initiale")
                if not self.first_launch.wait(lambda: self._closing):
                    return
                self._set_status(state="starting")
        if not self._fast:
            for line in ("Essai : choix d'Ollama — 61 tok/s", "Essai : contexte en 8 bits — 78 tok/s"):
                self._set_status(detail=line)
                time.sleep(pause)
        self._set_status(placement="modèle sur le GPU (100 %)")
        self._step("engine", "Chargement du moteur…")
        outputs = self._workspaces.parent / "outputs"
        outputs.mkdir(parents=True, exist_ok=True)
        # Dossier des fichiers « produits par l'appli » (files.generated_roots)
        self.config = SimpleNamespace(
            get=lambda key, default=None: str(outputs)
            if key == "generation.output_directory" else default)
        engine = DemoEngine(self._workspaces, self._rate, outputs)
        self.engine = engine
        # Notes gardées en mémoire : jamais dans data/rlhf_feedback.db
        self.chat = ChatService(engine, self.bus.publish, file_processor=FakeFileProcessor(),
                                ui_connected=lambda: self.bus.subscriber_count > 0,
                                on_session_change=lambda sid: self.state.set("current_session", sid),
                                rlhf=FakeRLHF())
        self.chat.start()
        time.sleep(pause)
        self._step("services", "Démarrage des services…")
        time.sleep(pause)
        self._restore_session()
        self.preload_voice()
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
    parser.add_argument("--premier-lancement", dest="first_launch", action="store_true",
                        help="assistant de premier lancement au lancement")
    parser.add_argument("--vraie-voix", dest="real_voice", action="store_true",
                        help="micro et synthèse du PC (sinon voix simulée)")
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
        desktop_server.DIST_DIR = Path(args.dist).resolve()
    # Chemins relatifs (export sans dialogue : outputs/exports/) dans le dossier
    # temporaire, jamais dans le outputs/ du dépôt. pywebview situe l'appli par
    # le dossier du script (sys.argv[0]) : chemin absolu avant de changer de dossier
    sys.argv[0] = os.path.abspath(sys.argv[0])
    os.chdir(tmp)

    token = args.token or secrets.token_urlsafe(16)
    app = DemoApp(workspaces, args.rate, args.fast_launch, real_voice=args.real_voice,
                  first_launch=args.first_launch,
                  port=args.port,
                  state=DesktopState(tmp / ".desktop_state.json"))
    app.token = token  # pylint: disable=attribute-defined-outside-init
    app.server.previews = PreviewStore(directory=tmp / "outputs" / "artifacts")
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
        os.chdir(ROOT)
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    # Fil principal laissé tel quel : pywebview vérifie qu'il s'appelle MainThread
    main()
