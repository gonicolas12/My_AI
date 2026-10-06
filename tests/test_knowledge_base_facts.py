"""
Tests des faits de la base de connaissances (core/knowledge_base_manager.py) :
choix des faits envoyés au modèle, enregistrement depuis le chat et
reconnaissance des demandes « retiens que… ».

Régressions observées en usage réel :
  - la recherche des faits pertinents cherchait la question ENTIÈRE dans les
    faits (« LIKE '%Comment s'appelle mon chat ?%' ») et ne trouvait jamais
    rien ; le repli prenait les 6 premiers faits triés par catégorie
    alphabétique. Au-delà de 6 faits, celui que la question visait, ou le
    plus récent, pouvait ne jamais être envoyé ;
  - « retiens que… » n'enregistrait rien : aucun code n'écrivait dans la base.
"""

import pytest

from core.knowledge_base_manager import (
    MAX_REMEMBERED_CHARS,
    KnowledgeBaseManager,
    extract_remember_request,
    fact_for_prompt,
    is_assistant_fact,
    is_only_remember_request,
    memorization_confirmation,
    reply_language,
    spoken_to_user,
    user_fact_for_prompt,
)


@pytest.fixture(name="kb")
def _kb(tmp_path):
    kb = KnowledgeBaseManager(db_path=str(tmp_path / "facts.db"))
    yield kb
    kb.close()


def _add(kb, category, value, day, key=None, confidence=1.0):
    """Ajoute un fait daté du jour donné (ordre chronologique déterministe)."""
    fact_id = kb.add_fact(category, key=key or value[:80], value=value, confidence=confidence)
    conn = kb._get_connection()
    conn.execute(
        "UPDATE facts SET updated_at = ? WHERE id = ?",
        (f"2026-09-{day:02d}T10:00:00", fact_id),
    )
    conn.commit()
    return fact_id


def _values(facts):
    return [fact["value"] for fact in facts]


# ── Choix des faits envoyés au modèle ───────────────────────────────────────


def test_question_reaches_its_fact_among_many(kb):
    """Le fait visé passe en tête, même noyé parmi des faits plus récents."""
    _add(kb, "general", "Mon chat s'appelle Félix", day=1)
    for day in range(2, 22):
        _add(kb, "general", f"Note numéro {day}", day=day)

    facts = kb.select_facts("Comment s'appelle mon chat ?")

    assert facts[0]["value"] == "Mon chat s'appelle Félix"


def test_more_shared_words_rank_first(kb):
    _add(kb, "general", "Mon chien s'appelle Rex", day=2)
    _add(kb, "general", "Mon chat s'appelle Félix", day=1)

    facts = kb.select_facts("Comment s'appelle mon chat ?")

    assert _values(facts)[:2] == ["Mon chat s'appelle Félix", "Mon chien s'appelle Rex"]


def test_recent_facts_follow_by_date_not_by_category(kb):
    """Le plus récent passe d'abord, quelle que soit sa catégorie."""
    for day in range(1, 7):
        _add(kb, "decision", f"Décision numéro {day}", day=day)
    _add(kb, "technical", "Le serveur de prod est 10.0.0.5", day=7)

    facts = kb.select_facts("bonjour")

    assert facts[0]["value"] == "Le serveur de prod est 10.0.0.5"
    assert len(facts) == 7


def test_matching_ignores_case_accents_and_plural(kb):
    _add(kb, "general", "Mes CHATS s'appellent Félix et Tom", day=1)
    for day in range(2, 20):
        _add(kb, "general", f"Note numéro {day}", day=day)

    facts = kb.select_facts("le chat felix", max_facts=1)

    assert _values(facts) == ["Mes CHATS s'appellent Félix et Tom"]


def test_selection_respects_the_character_budget(kb):
    for day in range(1, 11):
        _add(kb, "procedure", f"Procédure {day} : " + "étape " * 80, day=day)

    facts = kb.select_facts("bonjour", max_chars=1500)
    lines = kb.format_facts(facts)

    assert 1 <= len(facts) < 10
    assert sum(len(line) for line in lines) <= 1500


def test_relevant_only_without_recent_facts(kb):
    _add(kb, "general", "Mon chat s'appelle Félix", day=1)

    assert kb.select_facts("quelle heure est-il", include_recent=False) == []
    assert kb.get_context_for_prompt("quelle heure est-il") == ""
    assert "Félix" in kb.get_context_for_prompt("le nom de mon chat")


# ── Mise en forme ───────────────────────────────────────────────────────────


def test_key_repeating_the_value_is_not_shown_twice(kb):
    """Clé tirée de la valeur (fenêtre Mémoire, chat) : « clé: valeur » la
    répétait mot pour mot dans le prompt."""
    _add(kb, "general", "Le chat de l'utilisateur s'appelle Félix", day=1)

    assert kb.format_facts(kb.get_all_facts()) == [
        "- [general] Le chat de l'utilisateur s'appelle Félix"
    ]


def test_first_person_fact_is_shown_in_the_third_person(kb):
    """Nu dans le prompt système, « je suis nicolas gouy » faisait répondre
    « Je suis Nicolas Gouy. » à « qui je suis ? » ; même cité comme ses mots,
    « je m'appelle Nicolas » donnait encore « Je m'appelle Nicolas. » à « qui
    suis-je ? » : le modèle recopiait la phrase."""
    _add(kb, "general", "je m'appelle Nicolas", day=1)

    assert kb.format_facts(kb.get_all_facts()) == ["- [general] L'utilisateur s'appelle Nicolas"]


@pytest.mark.parametrize(
    ("value", "shown"),
    [
        ("je suis nicolas gouy", "L'utilisateur est nicolas gouy"),
        ("J'habite à Toulouse", "L'utilisateur habite à Toulouse"),
        ("Mon chat s'appelle Félix", "L'utilisateur : son chat s'appelle Félix"),
        ("je ne suis pas allergique", "L'utilisateur n'est pas allergique"),
        ("je me suis inscrit au club", "L'utilisateur s'est inscrit au club"),
        ("j'ai deux enfants et ma fille s'appelle Léa",
         "L'utilisateur a deux enfants et sa fille s'appelle Léa"),
        ("je ne m'appelle pas Paul", "L'utilisateur ne s'appelle pas Paul"),
        ("je peux venir lundi", "L'utilisateur peut venir lundi"),
        ("je prends le train", "L'utilisateur prend le train"),
        ("je fais du vélo", "L'utilisateur fait du vélo"),
        ("j'y vais demain", "L'utilisateur y va demain"),
        ("je serai à Paris lundi", "L'utilisateur sera à Paris lundi"),
        ("je l'adore", "L'utilisateur l'adore"),
        ("Moi, je préfère le thé", "L'utilisateur préfère le thé"),
        ("pour moi le thé est meilleur", "Pour l'utilisateur le thé est meilleur"),
        ("I'm a developer", "The user is a developer"),
        ("my car is red", "The user's car is red"),
        # Forme non reconnue : cité comme ses mots plutôt que mal converti
        ("il m'a dit bonjour", "L'utilisateur t'a dit : « il m'a dit bonjour »"),
        ("I like tea", "L'utilisateur t'a dit : « I like tea »"),
        # Déjà à la troisième personne : inchangé
        ("Le chat de l'utilisateur s'appelle Félix",
         "Le chat de l'utilisateur s'appelle Félix"),
    ],
)
def test_user_fact_for_prompt(value, shown):
    assert user_fact_for_prompt(value) == shown


@pytest.mark.parametrize(
    ("value", "for_assistant"),
    [
        ("tu t'appelles Jarvis", True),
        ("tu dois toujours me répondre en anglais", True),
        ("ton nom est Jarvis", True),
        ("you must always answer in English", True),
        # « je » vient d'abord : un fait (ou un souhait) de l'utilisateur
        ("je veux que tu me tutoies", False),
        ("je t'ai dit que je préfère le thé", False),
        ("je m'appelle Nicolas", False),
        ("Mon chat s'appelle Félix", False),
        ("Le chat de l'utilisateur s'appelle Félix", False),
    ],
)
def test_facts_about_the_assistant_are_recognized(value, for_assistant):
    assert is_assistant_fact(value) is for_assistant


@pytest.mark.parametrize(
    ("value", "shown"),
    [
        # Consigne pour l'IA : à la deuxième personne, comme le reste du prompt
        ("tu t'appelles Jarvis", "Tu t'appelles Jarvis"),
        ("ton nom est Jarvis", "Ton nom est Jarvis"),
        # Elle parle aussi de l'utilisateur (« me ») : citée comme sa demande
        ("tu dois toujours me répondre en anglais",
         "L'utilisateur t'a demandé : « tu dois toujours me répondre en anglais »"),
        # Fait sur l'utilisateur : à la troisième personne
        ("je m'appelle Nicolas", "L'utilisateur s'appelle Nicolas"),
    ],
)
def test_fact_for_prompt(value, shown):
    """« Retiens que tu t'appelles Jarvis » était confirmé par « C'est noté :
    tu t'appelles Jarvis », présenté comme un fait sur l'utilisateur."""
    assert fact_for_prompt(value) == shown


@pytest.mark.parametrize(
    ("value", "language"),
    [
        ("tu dois toujours me répondre en anglais", "en"),
        ("you must always answer in English", "en"),
        ("je préfère qu'on parle en espagnol", "es"),
        ("réponds-moi en allemand", "de"),
        # L'utilisateur parle de lui, pas à l'IA
        ("je parle en anglais au travail", None),
        ("j'habite en France", None),
        ("tu dois me répondre en détail", None),
        ("tu t'appelles Jarvis", None),
    ],
)
def test_reply_language_instructions_are_recognized(value, language):
    assert reply_language(value) == language


@pytest.mark.parametrize(
    ("value", "spoken"),
    [
        ("tu t'appelles Jarvis", "je m'appelle Jarvis"),
        ("tu dois toujours me répondre en anglais", "je dois toujours te répondre en anglais"),
        ("tu dois toujours terminer tes réponses par « Bonne journée ! »",
         "je dois toujours terminer mes réponses par « Bonne journée ! »"),
        ("ton nom est Jarvis", "mon nom est Jarvis"),
        ("tu es mon assistant de cuisine", "je suis ton assistant de cuisine"),
        ("tu as le droit de me tutoyer", "j'ai le droit de te tutoyer"),
        ("tu ne m'as pas répondu", "je ne t'ai pas répondu"),
        ("tu t'es trompé hier", "je me suis trompé hier"),
        ("tu seras mon coach", "je serai ton coach"),
        # Les citations restent telles quelles
        ("tu dois me dire « tu as raison » quand c'est vrai",
         "je dois te dire « tu as raison » quand c'est vrai"),
        # Fait sur l'utilisateur : « je » devient « tu »
        ("je m'appelle Sophie", "tu t'appelles Sophie"),
        ("je ne suis pas allergique", "tu n'es pas allergique"),
        ("je me suis inscrit au club", "tu t'es inscrit au club"),
        ("j'ai deux enfants et ma fille s'appelle Léa",
         "tu as deux enfants et ta fille s'appelle Léa"),
        ("je veux que tu me tutoies", "tu veux que je te tutoie"),
        ("je serai à Paris lundi", "tu seras à Paris lundi"),
        # « je » sans verbe reconnu : aucune phrase plutôt qu'une phrase fausse
        ("je, Sophie, suis développeuse", None),
        # Ni l'un ni l'autre : rien à inverser
        ("La réunion d'équipe est le mardi", None),
        # Anglais : you ↔ I, your ↔ my, me → you ; seul « be » change de forme
        ("you must always answer in English", "I must always answer in English"),
        ("your name is Jarvis", "my name is Jarvis"),
        ("You are my cooking assistant", "I am your cooking assistant"),
        ("you're not allowed to use emojis", "I'm not allowed to use emojis"),
        ("You aren't my friend", "I'm not your friend"),
        ("you should always call me Nico", "I should always call you Nico"),
        ("you must tell me when I am wrong", "I must tell you when you are wrong"),
        ("you'll help me every Monday", "I'll help you every Monday"),
        ('you must always end your answers with "Have a nice day"',
         'I must always end my answers with "Have a nice day"'),
        ("you must always say thank you", "I must always say thank you"),
        ("I'm a developer", "you're a developer"),
    ],
)
def test_spoken_to_user(value, spoken):
    """La confirmation recopiait l'exemple à trous de la consigne : « Noté :
    je ferai X pour toutes mes futures réponses. »"""
    assert spoken_to_user(value) == spoken


@pytest.mark.parametrize(
    ("value", "confirmation"),
    [
        ("tu t'appelles Friday", "C'est noté : je m'appelle Friday."),
        ("Je suis Sophie Martin", "C'est noté : tu es Sophie Martin."),
        ("your name is Friday", "Noted: my name is Friday."),
        # « me » existe dans les deux langues : c'est bien de l'anglais
        ("you must always call me Nico", "Noted: I must always call you Nico."),
        ("La réunion d'équipe est le mardi", None),
    ],
)
def test_memorization_confirmation_in_the_language_of_the_fact(value, confirmation):
    assert memorization_confirmation(value) == confirmation


def test_memorization_confirmation_only_in_the_language_of_the_answer():
    """« C'est noté : je dois toujours te répondre en anglais. », recopié, répondait
    en français à la consigne même de répondre en anglais."""
    consigne = "tu dois toujours me répondre en anglais"

    assert memorization_confirmation(consigne, "en") is None
    assert memorization_confirmation(consigne, "fr") == (
        "C'est noté : je dois toujours te répondre en anglais."
    )
    assert memorization_confirmation("your name is Friday", "en") == "Noted: my name is Friday."
    assert memorization_confirmation("your name is Friday", "fr") is None


def test_informative_key_and_low_confidence_are_kept(kb):
    _add(kb, "person", "Paul Martin", day=1, key="manager")
    _add(kb, "preference", "VS Code", day=2, key="préférence: VS Code", confidence=0.7)

    lines = kb.format_facts(kb.select_facts("bonjour"))

    assert "- [preference] VS Code (confiance: 70%)" in lines
    assert "- [person] manager: Paul Martin" in lines


# ── Enregistrement depuis le chat ───────────────────────────────────────────


def test_remember_creates_a_conversation_fact(kb):
    fact_id, created = kb.remember("mon chat s'appelle Félix")

    fact = kb.get_all_facts()[0]
    assert created is True
    assert fact["id"] == fact_id
    assert fact["value"] == "mon chat s'appelle Félix"
    assert fact["source"] == "conversation"
    assert fact["category"] == "general"


def test_remember_twice_refreshes_instead_of_duplicating(kb):
    fact_id = _add(kb, "general", "Mon chat s'appelle Félix", day=1)

    same_id, created = kb.remember("mon chat s'appelle felix.")

    facts = kb.get_all_facts()
    assert (same_id, created) == (fact_id, False)
    assert len(facts) == 1
    assert facts[0]["updated_at"] > "2026-09-01T10:00:00"


def test_remember_unknown_category_falls_back_to_general(kb):
    kb.remember("Je travaille le mardi", category="personnel")

    assert kb.get_all_facts()[0]["category"] == "general"


def test_remember_refuses_an_empty_value(kb):
    with pytest.raises(ValueError):
        kb.remember("   ")


# ── Reconnaissance des demandes « retiens que… » ────────────────────────────


@pytest.mark.parametrize(
    ("message", "fact"),
    [
        ("Retiens que mon chat s'appelle Félix", "mon chat s'appelle Félix"),
        ("Retiens que mon chat s'appelle Félix. Quel temps fait-il ?", "mon chat s'appelle Félix"),
        ("Retiens que je débute en Python. Explique-moi les closures.", "je débute en Python"),
        # Un bloc « ceci : » garde ses consignes : il décrit souvent une procédure
        ("Retiens ceci : lance build.bat. Vérifie ensuite les logs.",
         "lance build.bat. Vérifie ensuite les logs"),
        ("Salut ! Retiens que je m'appelle Nicolas.", "je m'appelle Nicolas"),
        ("Salut, retiens que je m'appelle Nicolas", "je m'appelle Nicolas"),
        ("Merci, retiens que je préfère les réponses courtes !",
         "je préfère les réponses courtes"),
        ("Au fait, souviens-toi que je suis allergique aux arachides",
         "je suis allergique aux arachides"),
        ("N'oublie pas que ma fille s'appelle Léa, stp", "ma fille s'appelle Léa"),
        ("n’oublie pas qu'on se voit lundi à 14h", "on se voit lundi à 14h"),
        ("Mémorise ceci : le serveur de prod est srv-prod-01",
         "le serveur de prod est srv-prod-01"),
        ("Retiens ceci :\n- le port est 8080\n- l'utilisateur est admin",
         "- le port est 8080\n- l'utilisateur est admin"),
        ("Retiens : la réunion d'équipe est le mardi", "la réunion d'équipe est le mardi"),
        ("Retiens mon prénom : Nicolas", "mon prénom : Nicolas"),
        ("Tu peux retenir que je travaille chez Gaches Chimie ?",
         "je travaille chez Gaches Chimie"),
        ("Est-ce que tu peux retenir que je préfère le thé ?", "je préfère le thé"),
        ("Garde bien en tête que je code en Python", "je code en Python"),
        ("Prends note que mon manager s'appelle Paul", "mon manager s'appelle Paul"),
        ("Souviens-toi de ceci : mon numéro client est 4567", "mon numéro client est 4567"),
        ("Retiens que je préfère le thé, ok ?", "je préfère le thé"),
        # Une citation finale garde ses guillemets (le fait était tronqué
        # en « … par « Bonne journée »)
        ("Retiens que tu dois toujours terminer tes réponses par « Bonne journée ! »",
         "tu dois toujours terminer tes réponses par « Bonne journée ! »"),
        ("Retiens : « je suis Nicolas »", "je suis Nicolas"),
        ("Remember that my favourite colour is blue", "my favourite colour is blue"),
        ("Please keep in mind that I work remotely on Fridays", "I work remotely on Fridays"),
        # Un mot interrogatif sans « ? » : une procédure, un proverbe
        ("Retiens ceci : comment faire un café : moudre, filtrer, servir",
         "comment faire un café : moudre, filtrer, servir"),
        ("Retiens que qui dort dîne", "qui dort dîne"),
    ],
)
def test_explicit_requests_are_recognized(message, fact):
    assert extract_remember_request(message) == fact


@pytest.mark.parametrize(
    "message",
    [
        "Je retiens que le projet est en retard",
        "Tu te souviens comment s'appelle mon chat ?",
        "Tu retiens tout ce que je dis ?",
        "Rappelle-moi ce qu'on a dit hier",
        "Retiens-le",
        "Retiens ça",
        "Retiens ce que je t'ai dit hier",
        # Consigne pour la tâche en cours, pas une information à garder
        "Écris une fonction de tri, et n'oublie pas que la liste peut être vide.",
        "Mémorise le contenu du fichier joint",
        "Do you remember that day?",
        "N'oublie pas de me rappeler demain",
        "Ne retiens pas ça",
        # Questions : se souvenir, pas retenir (« où j'habite » devenait un fait)
        "Souviens-toi : comment s'appelle mon chat ?",
        "Rappelle-toi : où j'habite ?",
        "Retiens ceci : quel est le code du portail ?",
        "",
    ],
)
def test_other_messages_are_not_requests(message):
    assert extract_remember_request(message) is None


def test_pasted_text_is_not_a_fact():
    assert extract_remember_request("Retiens ceci : " + "mot " * MAX_REMEMBERED_CHARS) is None


@pytest.mark.parametrize(
    ("message", "alone"),
    [
        ("Retiens que mon chat s'appelle Félix", True),
        ("Salut ! Retiens que je m'appelle Nicolas.", True),
        ("Tu peux retenir que je travaille chez Gaches Chimie ?", True),
        ("Retiens que je préfère le thé, ok ?", True),
        ("Retiens que mon chat s'appelle Félix. Merci !", True),
        ("Retiens ceci :\n- le port est 8080\n- l'utilisateur est admin", True),
        ("Retiens que mon chat s'appelle Félix. Quel temps fait-il ?", False),
        ("Retiens que je débute en Python. Explique-moi les closures.", False),
        ("Peux-tu m'expliquer les closures ? Retiens que je débute.", False),
        ("Explique-moi les closures. Retiens que je débute en Python.", False),
    ],
)
def test_message_that_only_asks_to_remember(message, alone):
    """Seule la demande de mémorisation : elle se confirme sans outils."""
    assert is_only_remember_request(message, extract_remember_request(message)) is alone
