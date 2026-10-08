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

from models.ai_agents import WebSearchAgent


class _LLM:
    """Ce que l'agent lit de LocalLLM."""

    is_ollama_available = True

    def __init__(self, reply="marques voitures fiables"):
        self.conversation_history = []
        self.calls = []
        self.reply = reply

    def generate(self, prompt, system_prompt=None, save_history=True, use_history=True):
        self.calls.append({
            "prompt": prompt, "system_prompt": system_prompt,
            "save_history": save_history, "use_history": use_history,
        })
        return self.reply


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
