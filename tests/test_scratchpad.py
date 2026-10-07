"""
Tests de l'emplacement du scratchpad de la boucle d'outils
(core/chat_orchestrator.py).

Le scratchpad était réécrit dans le message système à chaque tour : le début
du prompt changeait, et Ollama relisait toute la conversation (prompt système,
outils, documents, résultats d'outils) avant chaque appel, 73 à 81 s par tour
sur un GPU intégré, contre 12 à 32 s une fois le scratchpad placé après le
dernier échange d'outils. Aucun vrai Ollama n'est appelé ici : les tours de la
boucle sont écrits à l'avance.
"""

from core.chat_orchestrator import ChatOrchestrator, Scratchpad

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
        if message["role"] == "user" and "<scratchpad>\nOBJECTIF" in message["content"]
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


def test_each_turn_extends_what_ollama_already_read():
    """Tout ce qui précède le bloc du tour précédent est renvoyé à l'identique :
    Ollama ne relit que ce que le dernier tour a ajouté."""
    sent = _three_turns()
    for previous, current in zip(sent, sent[1:]):
        block = (_blocks(previous) or [len(previous)])[0]
        assert current[:block] == previous[:block]


def test_one_block_right_after_the_last_tool_result():
    """Les relances de la boucle (« Vérifie ton <scratchpad>… ») restent après
    le bloc : elles sont la dernière consigne lue par le modèle."""
    last = _three_turns()[-1]
    blocks = _blocks(last)
    assert len(blocks) == 1
    assert last[blocks[0] - 1]["role"] == "tool"
    assert all(message["role"] == "user" for message in last[blocks[0] + 1:])


def test_with_a_plan_the_block_follows_the_question():
    """Requête complexe : le plan existe dès le 1er tour. Placé devant la
    question, le bloc aurait fait relire toute la question au tour suivant
    (le XML d'un ticket, par exemple)."""
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


def test_synthesis_never_sees_the_block():
    last = _three_turns()[-1]
    synthesis = ChatOrchestrator._synthesis_messages(last, 2, "Synthèse", QUESTION)
    assert all("<scratchpad>" not in message["content"] for message in synthesis)
