"""
Appels d'outils mal écrits par le modèle dans la conversation Code
(core/agentic_executor.py, parse_tool_blocks et la boucle de AgenticExecutor).

Vu le 2026-11-19 avec my_ai : un write_file dont le JSON oubliait l'accolade
fermante de « input » après le long contenu du fichier. Le bloc était jeté,
la passe n'avait plus aucun appel, et la boucle concluait sur l'annonce du
modèle (« Voici le code complet avec la fonction `bonjour` ajoutée : »),
sans code ni fichier écrit. La docstring promettait qu'il réessaierait.

L'appel LLM est simulé (pas d'Ollama) en remplaçant ``_call_llm_streaming``.
"""

import asyncio

from core.agentic_executor import AgenticExecutor, parse_tool_blocks, parse_tool_calls

# Le bloc de my_ai tel qu'il l'a écrit : il manque la « } » de « input »
REAL_BLOCK = (
    "Voici le code complet avec la fonction `bonjour` ajoutée :\n\n<tool_use>\n"
    '{"name": "write_file", "input": {"path": "utils.py", "content": "def moyenne(valeurs: '
    'list[float]) -> float:\\n    \\"\\"\\"Moyenne des valeurs, arrondie à 2 décimales (0.0 '
    'pour une liste vide).\\"\\"\\"\\n    if not valeurs:\\n        return 0.0\\n    return '
    'round(sum(valeurs) / len(valeurs), 2)\\n\\ndef bonjour(nom: str) -> str:\\n    '
    '\\"\\"\\"Salut quelqu\'un.\\"\\"\\"\\n    return f\\"Bonjour {nom} !\\""\n}</tool_use>'
)
# Le dernier bloc d'un edit_file : my_ai s'est arrêté avant la « } » finale et
# </tool_use> (2 tours sur 9 sur origin/main, réponse vide)
REAL_CUT_BLOCK = (
    '<tool_use>\n{"name": "edit_file", "input": {"path": "utils.py", "old_string": "de'
    'f moyenne(valeurs: list[float]) -> float:\\n    \\"\\"\\"Moyenne des valeurs, arrond'
    'ie à 2 décimales (0.0 pour une liste vide).\\"\\"\\"\\n    if not valeurs:\\n        '
    'return 0.0\\n    return round(sum(valeurs) / len(valeurs), 2)", "new_string": "de'
    'f moyenne(valeurs: list[float]) -> float:\\n    \\"\\"\\"Moyenne des valeurs, arrond'
    'ie à 2 décimales (0.0 pour une liste vide).\\"\\"\\"\\n    if not valeurs:\\n        '
    'return 0.0\\n    return round(sum(valeurs) / len(valeurs), 2)\\n\\ndef chemin_windo'
    'ws(dossier: str, nom: str) -> str:\\n    \\"\\"\\"Crée un chemin Windows complet.\\n\\'
    "n    Exemples:\\n        >>> chemin_windows('donnees', 'fichier.txt')\\n        'C"
    ":\\\\donnees\\\\fichier.txt'\\n        \\n        >>> chemin_windows('logs', 'report_2"
    '026-11-20.csv\')\\n        \'C:\\\\logs\\\\report_2026-11-20.csv\'\\n    \\"\\"\\"\\n    retu'
    'rn f\'C:\\\\{dossier}\\\\{nom}\'"}'
)
# Guillemet du contenu pas échappé : rien à réparer sûrement
UNREADABLE = ('Voici le fichier :\n<tool_use>{"name": "write_file", "input": {"path": "a.py", '
              '"content": "print("bonjour")"}}</tool_use>')
VALID_WRITE = ('<tool_use>{"name": "write_file", "input": {"path": "a.py", '
               '"content": "print(\\"bonjour\\")"}}</tool_use>')


def test_the_block_of_my_ai_missing_its_brace_is_repaired():
    calls, broken = parse_tool_blocks(REAL_BLOCK)

    assert broken == []
    assert [(call["name"], call["input"]["path"]) for call in calls] == [("write_file", "utils.py")]
    content = calls[0]["input"]["content"]
    assert content.startswith("def moyenne(valeurs: list[float]) -> float:\n")
    assert content.endswith('    return f"Bonjour {nom} !"')


def test_real_newlines_and_windows_paths_in_a_string_are_read():
    # « \U » n'est pas un échappement JSON, « \n » de « \notes » en est un
    block = ('<tool_use>{"name": "write_file", "input": {"path": "C:\\Users\\data\\notes.txt", '
             '"content": "ligne 1\nligne 2\tfin"}}</tool_use>')
    calls, broken = parse_tool_blocks(block)
    assert broken == []
    assert calls[0]["input"] == {"path": "C:\\Users\\data\\notes.txt",
                                 "content": "ligne 1\nligne 2\tfin"}
    # JSON valide, mais « \t » de « tests\test_utils.py » n'était pas une tabulation
    valid = '<tool_use>{"name": "read_file", "input": {"path": "tests\\test_utils.py"}}</tool_use>'
    assert parse_tool_calls(valid)[0]["input"]["path"] == "tests\\test_utils.py"


def test_several_objects_in_one_block_are_several_calls():
    block = ('<tool_use>{"name": "read_file", "input": {"path": "a.py"}}\n'
             '{"name": "read_file", "input": {"path": "b.py"}}</tool_use>')
    calls, broken = parse_tool_blocks(block)
    assert [call["input"]["path"] for call in calls] == ["a.py", "b.py"]
    assert broken == []


def test_an_unreadable_block_is_reported_not_dropped():
    calls, broken = parse_tool_blocks(UNREADABLE)
    assert calls == []
    assert [(item["name"], item["reason"]) for item in broken] == [("write_file", "json")]
    assert broken[0]["detail"]


def test_a_last_block_missing_its_end_but_complete_is_read():
    calls, broken = parse_tool_blocks(REAL_CUT_BLOCK)

    assert broken == []
    assert [(call["name"], call["input"]["path"]) for call in calls] == [("edit_file", "utils.py")]
    assert calls[0]["input"]["new_string"].rstrip().endswith("return f'C:\\{dossier}\\{nom}'")


def test_a_cut_block_is_never_run():
    """Génération coupée (pas de </tool_use>) : son contenu est incomplet, même
    si des fermetures le rendraient lisible."""
    text = ('Je crée le fichier.\n<tool_use>{"name": "write_file", "input": {"path": "a.py", '
            '"content": "def f():\\n    return 1')
    calls, broken = parse_tool_blocks(text)
    assert calls == []
    assert [(item["name"], item["reason"]) for item in broken] == [("write_file", "truncated")]


def test_valid_blocks_are_read_as_before():
    text = ('Je lis.\n<tool_use>\n```json\n{"name": "read_file", "input": {"path": "a.py"}}\n'
            '```\n</tool_use>\n<tool_use>{"name": "list_dir", "input": {}}</tool_use>')
    calls, broken = parse_tool_blocks(text)
    assert [call["name"] for call in calls] == ["read_file", "list_dir"]
    assert broken == []
    assert [call["name"] for call in parse_tool_calls(text)] == ["read_file", "list_dir"]
    # Sans « name » ou pas un objet : rien à exécuter, et le modèle le saura
    assert parse_tool_blocks('<tool_use>{"input": {}}</tool_use>')[1][0]["name"] == "?"
    assert parse_tool_blocks("<tool_use>[1, 2]</tool_use>")[0] == []


# ── La boucle relance le modèle au lieu de conclure ─────────────────────────


class RecordingTools:
    """Exécuteur d'outils factice : garde les appels reçus."""

    def __init__(self):
        self.calls = []

    async def call(self, call_id, name, input_data):
        self.calls.append((name, input_data))
        return {"content": "Fichier écrit.", "is_error": False}


def _run(script):
    executor = AgenticExecutor(ollama_chat_url="http://localhost:0/api/chat", model="test")
    replies = iter(script)
    seen = []

    async def fake_llm(messages, segment_index, on_chunk):
        seen.append([dict(message) for message in messages])
        return next(replies)

    executor._call_llm_streaming = fake_llm  # pylint: disable=protected-access
    tools = RecordingTools()
    announced = []
    history = []
    result = asyncio.run(executor.run(
        user_message="Écris a.py",
        history=history,
        tool_executor=tools,
        on_chunk=lambda *a, **k: None,
        on_tool_call_announced=announced.append,
        on_tool_result=lambda *a, **k: None,
        workspace_info="",
    ))
    return result, tools.calls, announced, seen


def test_an_unreadable_call_is_rewritten_instead_of_ending_the_reply():
    result, calls, announced, seen = _run([UNREADABLE, VALID_WRITE, "C'est fait."])

    assert calls == [("write_file", {"path": "a.py", "content": 'print("bonjour")'})]
    # Pas de carte pour le bloc illisible : seulement pour l'appel réécrit
    assert [call["name"] for call in announced] == ["write_file"]
    note = seen[1][-1]
    assert note["role"] == "user"
    assert note["content"].startswith('<tool_error name="write_file">\nTon bloc <tool_use> '
                                      "n'est pas du JSON valide")
    assert result == "Voici le fichier :\n\nC'est fait."


def test_a_model_that_never_manages_stops_after_the_retries():
    executor_limit = AgenticExecutor.BROKEN_RETRY_LIMIT
    result, calls, _announced, seen = _run([UNREADABLE] * (executor_limit + 5))

    assert calls == []
    assert len(seen) == executor_limit + 1
    assert result.startswith("Voici le fichier :")
    assert "n'a pas réussi à écrire son appel d'outil" in result


def test_a_cut_call_asks_for_the_file_in_several_writes():
    cut = 'Je crée le fichier.\n<tool_use>{"name": "write_file", "input": {"path": "a.py", "content": "x'
    result, calls, _announced, seen = _run([cut, VALID_WRITE, "Fini."])

    assert calls == [("write_file", {"path": "a.py", "content": 'print("bonjour")'})]
    assert "est coupé (pas de </tool_use>)" in seen[1][-1]["content"]
    assert result.endswith("Fini.")


def test_readable_calls_run_and_the_unreadable_one_is_reported_with_their_results():
    mixed = ('<tool_use>{"name": "read_file", "input": {"path": "b.py"}}</tool_use>\n'
             + UNREADABLE.split("\n", 1)[1])
    _result, calls, _announced, seen = _run([mixed, "Terminé."])

    assert calls == [("read_file", {"path": "b.py"})]
    results = seen[1][-1]["content"]
    assert '<tool_result call_id="' in results and 'name="read_file"' in results
    assert '<tool_error name="write_file">' in results
