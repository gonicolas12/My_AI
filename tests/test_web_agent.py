"""
Tests du WebAgent de la page Agents (models/ai_agents.py, WebSearchAgent).

Il cherche avec models/internet_search.py, comme le chat, mais garde son
propre déroulé : une requête optimisée par le modèle, la recherche, puis
une synthèse. Essai réel du 8 octobre 2026 : la requête embarquait les
consignes de forme (« … 2026 tableau sources fiables »), l'échange
d'optimisation et les ~10 000 caractères de résultats bruts restaient dans
l'historique de l'agent, relu à chaque tâche suivante, et la réponse
ignorait le tableau demandé. Aucun Ollama ici.
"""

from types import SimpleNamespace

from models import ai_agents
from models import internet_search as ws
from models.ai_agents import WebSearchAgent
from utils.citations import SOURCES_STOP, sources_block


class _LLM:
    """Ce que l'agent lit de LocalLLM."""

    is_ollama_available = True

    def __init__(self, reply="marques voitures fiables", stream=()):
        self.conversation_history = []
        self.calls = []
        self.reply = reply
        self.stream = list(stream)

    def generate(self, prompt, system_prompt=None, save_history=True, use_history=True):
        self.calls.append({
            "prompt": prompt, "system_prompt": system_prompt,
            "save_history": save_history, "use_history": use_history,
        })
        return self.reply

    def generate_stream(self, prompt, system_prompt=None, on_token=None, stop=None):
        """Comme Ollama : la réponse s'arrête avant la première séquence d'arrêt."""
        self.calls.append({"prompt": prompt, "system_prompt": system_prompt, "stop": stop})
        answer = "".join(self.stream)
        cuts = [answer.find(sequence) for sequence in stop or () if sequence in answer]
        answer = answer[:min(cuts)] if cuts else answer
        for start in range(0, len(answer), 16):
            on_token(answer[start:start + 16])
        self.conversation_history += [
            {"role": "user", "content": prompt},
            {"role": "assistant", "content": answer},
        ]
        return answer


def test_requete_optimisee_hors_historique_et_sans_consignes_de_forme():
    agent = SimpleNamespace(llm=_LLM())
    query = WebSearchAgent._optimize_search_query(  # pylint: disable=protected-access
        agent, "Quelles sont les meilleures marques de voiture ? Fais un tableau."
    )
    assert query == "marques voitures fiables"
    call = agent.llm.calls[0]
    assert call["use_history"] is False and call["save_history"] is False
    assert "pas les consignes de présentation (tableau, liste, résumé, sources)" in call["prompt"]


def test_historique_garde_la_question_et_pas_les_resultats_bruts():
    task = "Quelles sont les meilleures marques de voiture ?"
    prompt = WebSearchAgent._synthesis_prompt(task, "Résultats " + "x" * 9000)  # pylint: disable=protected-access
    llm = _LLM()
    llm.conversation_history = [
        {"role": "user", "content": "tâche précédente"},
        {"role": "assistant", "content": "réponse précédente"},
        {"role": "user", "content": prompt},
        {"role": "assistant", "content": "Toyota arrive en tête [1]."},
    ]
    WebSearchAgent._keep_task_in_history(SimpleNamespace(llm=llm), task, prompt)  # pylint: disable=protected-access
    assert llm.conversation_history == [
        {"role": "user", "content": "tâche précédente"},
        {"role": "assistant", "content": "réponse précédente"},
        {"role": "user", "content": task},
        {"role": "assistant", "content": "Toyota arrive en tête [1]."},
    ]


def test_historique_inchange_si_la_demande_n_y_est_pas():
    # Résumé glissant de LocalLLM passé entre-temps : rien à remplacer
    llm = _LLM()
    llm.conversation_history = [{"role": "user", "content": "résumé"}]
    WebSearchAgent._keep_task_in_history(SimpleNamespace(llm=llm), "tâche", "autre demande")  # pylint: disable=protected-access
    assert llm.conversation_history == [{"role": "user", "content": "résumé"}]


def test_synthese_respecte_la_forme_demandee():
    prompt = WebSearchAgent._synthesis_prompt("Fais un tableau des marques", "[1] Source")  # pylint: disable=protected-access
    assert "QUESTION ORIGINALE: Fais un tableau des marques" in prompt
    assert "[1] Source" in prompt
    assert "Respecte la forme demandée dans la question (tableau, liste" in prompt
    assert "termine par le bloc 📚 Sources" in prompt


def test_sortie_sans_etat_de_recherche_et_sources_citees_seulement(monkeypatch):
    """
    Essai réel du 22 octobre 2026 : « 🔍 Recherche terminée - Synthèse en
    cours... » restait en tête de la sortie, et le modèle recopiait tout le
    bloc 📚 Sources, sources non citées comprises. Ollama l'arrête désormais
    au début du bloc, que l'agent écrit lui-même : sources citées, numéros
    gardés. (« N'écris pas de liste » ne suffisait pas : qwen3.5:4b en
    écrivait une quand même, sans les adresses.)
    """
    response = ws.SearchResponse(query="population mondiale", engine="DuckDuckGo", results=[
        ws.SearchResult(title=f"Source {n}", url=f"https://example.org/{n}", snippet="Extrait.")
        for n in range(1, 5)
    ])
    # Le modèle cite [1] et [3], puis recopie tout le bloc, comme on le lui demande
    block = sources_block(ws.format_results(response))
    llm = _LLM(reply="population mondiale", stream=[
        "La population mondiale atteint 8,3 milliards [1]", ", et croît de 0,8 % [3].",
        "\n\n" + block,
    ])
    monkeypatch.setattr(ai_agents, "LocalLLM", lambda model: llm)
    monkeypatch.setattr(ai_agents, "EnhancedInternetSearchEngine", lambda: SimpleNamespace(
        search_best_source_context=lambda _query: ws.format_results(response)))
    agent = WebSearchAgent(name="WebAgent")

    streamed = []
    task = "cherche le nombre d'habitants sur terre"
    result = agent.execute_task_stream(task, on_token=streamed.append)

    answer = (
        "La population mondiale atteint 8,3 milliards [1], et croît de 0,8 % [3].\n\n"
        "📚 **Sources**\n"
        "[1] [Source 1](https://example.org/1)\n"
        "[3] [Source 3](https://example.org/3)"
    )
    # La page montre ce qui a été streamé : la réponse, puis ses sources citées
    assert "".join(streamed) == answer and result["result"] == answer
    # Le modèle est toujours invité à finir par le bloc : c'est là qu'il s'arrête
    assert ws.SOURCES_NOTE in llm.calls[-1]["prompt"]
    assert llm.calls[-1]["stop"] == SOURCES_STOP
    # Son historique garde la question et la réponse, sources comprises
    assert llm.conversation_history == [
        {"role": "user", "content": task},
        {"role": "assistant", "content": answer},
    ]
