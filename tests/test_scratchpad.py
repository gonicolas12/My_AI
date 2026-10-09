"""
Tests du scratchpad de la boucle d'outils (core/chat_orchestrator.py).

Le scratchpad était réécrit dans le message système à chaque tour, et sa
ligne OBJECTIF recopiait toute la demande (le XML d'un ticket, par exemple).
Le début du prompt changeait donc à chaque appel : Ollama relisait toute la
conversation, et la demande deux fois. Avec un modèle hybride comme qwen3.5,
il ne reprend la lecture que depuis un point de sauvegarde tout près de la fin
du prompt précédent : chaque tour doit prolonger le précédent, sans rien
retirer ni modifier en amont. Aucun vrai Ollama n'est appelé ici : les tours de
la boucle sont écrits à l'avance.
"""

from core.chat_orchestrator import ChatOrchestrator, Scratchpad, _tool_failed

SYSTEM = "Système de My_AI"
QUESTION = "Lis le ticket LOGM-80 et retrouve son dossier"
RESULTS = {
    "list_directory": "C:\\Projets\\LOGM-80\\notes.txt\nC:\\Projets\\LOGM-80\\bases.xlsx",
    "read_local_file": "Notes : reprendre les bases articles de référence.",
}


class _LLM:
    """Ce que l'orchestrateur lit de LocalLLM, sans Ollama."""

    is_ollama_available = True
    model = "fake"
    chat_url = "http://127.0.0.1:9/api/chat"
    timeout = 1
    gen_temperature = 0.0
    gen_num_ctx = 32768

    def __init__(self):
        self.conversation_history = []

    def add_to_history(self, role, content):
        self.conversation_history.append({"role": role, "content": content})

    @staticmethod
    def parse_text_tool_call(_text, _names):
        return None


def _blocks(messages):
    """Positions des messages de la boucle qui portent le scratchpad (et non
    des relances qui y renvoient, « Vérifie ton <scratchpad>… »)."""
    return [
        i for i, message in enumerate(messages)
        if message["role"] == "user"
        and message["content"].startswith("[ORCHESTRATEUR] État de la tâche")
    ]


# pylint: disable=protected-access
def _three_turns():
    """Dossier listé, notes lues, puis réponse : messages envoyés à chaque tour."""
    sent = []
    turns = [
        {"name": "list_directory", "arguments": {"path": "C:\\Projets\\LOGM-80"}},
        {"name": "read_local_file", "arguments": {"path": "C:\\Projets\\LOGM-80\\notes.txt"}},
        "Le dossier contient les notes et les bases articles.",
    ]

    def fake_turn(**kwargs):
        sent.append([dict(message) for message in kwargs["messages"]])
        turn = turns.pop(0)
        if isinstance(turn, dict):
            return {"content": "", "tool_calls": [{"function": turn}], "streamed": False}
        return {"content": turn, "tool_calls": [], "streamed": True}

    orchestrator = ChatOrchestrator()
    orchestrator._call_ollama_smart_stream = fake_turn
    orchestrator._stream_synthesis = lambda **_kwargs: "Synthèse."
    orchestrator.run(
        user_input=QUESTION,
        tools=[{"type": "function", "function": {"name": name}} for name in RESULTS],
        tool_executor=lambda name, _arguments: RESULTS[name],
        llm=_LLM(),
        system_prompt=SYSTEM,
        on_token=lambda _token: None,
    )
    assert len(sent) == 3
    return sent


def test_system_message_no_longer_changes_between_turns():
    sent = _three_turns()
    assert [messages[0] for messages in sent] == [{"role": "system", "content": SYSTEM}] * 3


def test_each_turn_starts_with_the_whole_previous_prompt():
    """Ni retrait ni modification en amont : Ollama reprend la lecture juste
    avant la fin du prompt précédent."""
    sent = _three_turns()
    for previous, current in zip(sent, sent[1:]):
        assert current[:len(previous)] == previous


def test_full_state_then_progress_after_each_tool_result():
    """Les relances de la boucle (« Vérifie ton <scratchpad>… ») restent après
    chaque bloc : elles sont la dernière consigne lue par le modèle. Le bloc
    d'avancement rappelle l'objectif, sans les consignes."""
    last = _three_turns()[-1]
    blocks = _blocks(last)
    assert len(blocks) == 2
    full, progress = (last[i]["content"] for i in blocks)
    assert "OBJECTIF" in full and "INSTRUCTION CRUCIALE" in full
    assert "OBJECTIF : " + QUESTION in progress
    assert "INSTRUCTION CRUCIALE" not in progress and "CONSIGNE STRICTE" not in progress
    assert all(last[i - 1]["role"] == "tool" for i in blocks)
    assert all(message["role"] == "user" for message in last[blocks[-1] + 1:])


def test_with_a_plan_the_block_follows_the_question():
    """Requête complexe : le plan existe dès le 1er tour. Placé devant la
    question, le bloc aurait fait relire toute la question au tour suivant."""
    scratchpad = Scratchpad(goal=QUESTION)
    scratchpad.set_plan(["Lister le dossier du ticket", "Lire les notes"])
    messages = [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": "Bonjour"},
        {"role": "assistant", "content": "Bonjour !"},
        {"role": "user", "content": QUESTION},
    ]
    placed = ChatOrchestrator()._inject_scratchpad(
        messages, scratchpad, loop_start=len(messages)
    )
    assert placed[:4] == messages
    assert len(placed) == 5 and _blocks(placed) == [4]


def test_objective_is_the_start_and_end_of_the_request():
    """OBJECTIF recopiait toute la demande : le XML du ticket LOGM-80 était lu
    deux fois à chaque tour (13 224 tokens au lieu de ≈ 7 800). Le début seul
    n'en gardait que le XML : la question, qui le suit, reste aussi."""
    from core.chat_orchestrator import SCRATCHPAD_GOAL_CHARS  # pylint: disable=import-outside-toplevel

    xml = "<item><title>LOGM-80</title><description>Bases articles</description></item>\n"
    goal = f"Voici le xml de la mission :\n{xml * 110}Puis résume-moi la mission."
    scratchpad = Scratchpad(goal=goal)
    for block in (scratchpad.to_context_block(), scratchpad.to_progress_block()):
        objective = next(line for line in block.splitlines() if line.startswith("OBJECTIF"))
        assert objective.startswith("OBJECTIF : Voici le xml de la mission : <item>")
        assert objective.endswith("Puis résume-moi la mission. (demande complète plus haut)")
        assert len(objective) < SCRATCHPAD_GOAL_CHARS + 50
    assert "OBJECTIF : " + QUESTION in Scratchpad(goal=QUESTION).to_context_block()


def test_synthesis_never_sees_the_blocks():
    last = _three_turns()[-1]
    synthesis = ChatOrchestrator._synthesis_messages(last, 2, "Synthèse", QUESTION)
    assert all("<scratchpad>" not in message["content"] for message in synthesis)


# ── Plan : une recherche vide ne coche pas l'étape suivante ────────────────
#
# Chaque résultat d'outil avançait d'une étape : deux recherches vides
# cochaient « créer le document », et le modèle (qwen3.5:4b, 6 outils)
# concluait sans l'avoir créé.

STORAGE = "Crée un document Word sur le stockage des produits chimiques"
STORAGE_PLAN = ["Rechercher les règles sur internet", "Créer le document Word"]


def _storage_scratchpad():
    scratchpad = Scratchpad(goal=STORAGE)
    scratchpad.set_plan(STORAGE_PLAN)
    return scratchpad


def test_retried_search_does_not_tick_the_next_step():
    scratchpad = _storage_scratchpad()
    scratchpad.record_result("web_search", failed=True)
    scratchpad.record_result("web_search", failed=True)
    block = scratchpad.to_progress_block()
    assert "1. [✗] Rechercher les règles sur internet (sans résultat)" in block
    assert "2. [ ] Créer le document Word" in block
    assert "ÉTAPE ACTUELLE : 2" in block


def test_successful_retry_ticks_the_failed_step():
    scratchpad = _storage_scratchpad()
    scratchpad.record_result("web_search", failed=True)
    scratchpad.record_result("web_search", failed=False)
    block = scratchpad.to_progress_block()
    assert "1. [✓] Rechercher les règles sur internet" in block
    assert "2. [ ] Créer le document Word" in block


def test_another_tool_after_a_failure_does_the_next_step():
    """Le modèle renonce à la recherche et crée le document."""
    scratchpad = _storage_scratchpad()
    scratchpad.record_result("web_search", failed=True)
    scratchpad.record_result("generate_document", failed=False)
    block = scratchpad.to_progress_block()
    assert "1. [✗] Rechercher les règles sur internet (sans résultat)" in block
    assert "2. [✓] Créer le document Word" in block


def test_each_useful_result_still_ticks_a_step():
    scratchpad = Scratchpad(goal=QUESTION)
    scratchpad.set_plan(["Lister le dossier", "Lire les notes"])
    scratchpad.record_result("list_directory", failed=False)
    scratchpad.record_result("read_local_file", failed=False)
    block = scratchpad.to_progress_block()
    assert "1. [✓] Lister le dossier" in block and "2. [✓] Lire les notes" in block


def test_loop_marks_the_empty_search_and_keeps_the_document_step():
    """Dans la boucle : deux recherches vides, l'étape du document reste à faire."""
    from models.internet_search import SearchResponse, _no_result_message  # pylint: disable=import-outside-toplevel

    sent = []
    turns = [
        {"name": "web_search", "arguments": {"query": "stockage produits chimiques"}},
        {"name": "web_search", "arguments": {"query": "règles stockage chimique entrepôt"}},
        "Je n'ai rien trouvé.",
    ]

    def fake_turn(**kwargs):
        sent.append([dict(message) for message in kwargs["messages"]])
        turn = turns.pop(0)
        if isinstance(turn, dict):
            return {"content": "", "tool_calls": [{"function": turn}], "streamed": False}
        return {"content": turn, "tool_calls": [], "streamed": False}

    orchestrator = ChatOrchestrator()
    orchestrator._call_ollama_smart_stream = fake_turn
    orchestrator._stream_synthesis = lambda **_kwargs: "Synthèse."
    orchestrator._should_plan = lambda *_args: True
    orchestrator._generate_plan_stream = lambda *_args, **_kwargs: list(STORAGE_PLAN)
    empty = _no_result_message(SearchResponse(query="stockage", notes=["moteurs injoignables"]))
    orchestrator.run(
        user_input=STORAGE,
        tools=[{"type": "function", "function": {"name": "web_search"}}],
        tool_executor=lambda _name, _arguments: empty,
        llm=_LLM(),
        system_prompt=SYSTEM,
        on_token=lambda _token: None,
        on_thinking_token=lambda _token: None,
    )
    assert len(sent) == 3
    last = sent[-1]
    block = last[_blocks(last)[-1]]["content"]
    assert "1. [✗] Rechercher les règles sur internet (sans résultat)" in block
    assert "2. [ ] Créer le document Word" in block


def test_empty_or_failed_tool_results():
    from models.internet_search import SearchResponse, _no_result_message  # pylint: disable=import-outside-toplevel

    failures = [
        ("web_search", _no_result_message(SearchResponse(query="stockage"))),
        ("web_search", "Recherche impossible (Timeout). Aucun résultat pour « stockage »."),
        ("search_local_files", "Aucun fichier contenant 'rapport' trouvé dans C:\\Users\\x."),
        ("search_memory", "Aucun résultat dans la mémoire (faits mémorisés et documents indexés)."),
        ("read_local_file", "Fichier introuvable : C:\\Missions\\LOGM-80\\notes.txt"),
        ("generate_document", "Erreur génération document : délai dépassé"),
        ("move_local_file", "[Erreur lors de l'exécution de 'move_local_file']: accès refusé"),
    ]
    assert [result for tool, result in failures if not _tool_failed(tool, result)] == []


def test_useful_tool_results():
    from core.ai_engine import _document_success_message  # pylint: disable=import-outside-toplevel

    document = _document_success_message({
        "format": "docx", "title": "Stockage", "file_path": "C:\\x\\stockage.docx",
        "size": 10, "outline": ["Règles de compatibilité"],
    })
    useful = [
        ("web_search", "[1] Que Choisir — fiabilité\nLien : https://www.quechoisir.org"),
        ("search_local_files", "Fichiers trouvés (1 max) :\nC:\\Users\\x\\rapport.docx"),
        ("generate_document", document),
        # Fichier lu qui commence par « Erreur » : la lecture, elle, a réussi
        ("read_local_file", "Erreur 404 relevée dans le journal du serveur le 3 mars."),
    ]
    assert [result for tool, result in useful if _tool_failed(tool, result)] == []
