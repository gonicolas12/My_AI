"""
Demandes de mémoire dans les dix langues de My_AI autres que le français et
l'anglais (core/memory_languages.py), lues par les fonctions de
core/knowledge_base_manager.py comme le français et l'anglais.

Avant, seuls ces deux-là étaient reconnus : « Olvida que vivo en Madrid » passait
par la lecture sans demande, qui ne retire jamais rien, et la réponse pouvait
prétendre l'avoir oublié. En russe, chinois, japonais, coréen et arabe, rien
ne pouvait même être retenu : aucun mot n'y comptait (content_words).
"""

import pytest

from core.chat_memory import _SECRET_RE
from core.code_memory import _ALL_PROJECTS_RE, _THIS_PROJECT_RE, _forgets_a_fact, remember_request
from core.knowledge_base_manager import (
    SCOPE_CODE,
    SCOPE_PROJECT,
    asks_to_forget,
    asks_to_remember,
    content_words,
    extract_remember_request,
    is_only_remember_request,
    is_rememberable,
    only_asks_to_forget,
    only_asks_to_remember,
    remember_block,
)
from core.memory_languages import is_request, message_parts, request_languages, word_count

# ── Retenir ──────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("message", "fact"),
    [
        ("Recuerda que vivo en Madrid", "vivo en Madrid"),
        ("Hola, recuerda que mi gato se llama Félix. ¡Gracias!", "mi gato se llama Félix"),
        ("No olvides que soy vegetariano", "soy vegetariano"),
        ("¿Puedes recordar que trabajo de noche?", "trabajo de noche"),
        ("Acuérdate de que mi hermana vive en Sevilla", "mi hermana vive en Sevilla"),
        ("No, recuerda mejor que vivo en Valencia", "vivo en Valencia"),
        ("Merk dir, dass ich in Berlin wohne", "ich in Berlin wohne"),
        ("Bitte merk dir, dass meine Katze Mimi heißt. Danke!", "meine Katze Mimi heißt"),
        ("Vergiss nicht, dass ich Vegetarier bin", "ich Vegetarier bin"),
        ("Nein, merk dir lieber, dass ich in München wohne", "ich in München wohne"),
        ("Ricorda che abito a Roma", "abito a Roma"),
        ("Ricordati che sono vegetariano", "sono vegetariano"),
        ("Non dimenticare che lavoro di notte", "lavoro di notte"),
        ("Lembra que moro em Lisboa", "moro em Lisboa"),
        ("Lembre-se de que sou vegetariano", "sou vegetariano"),
        ("Não esqueça que trabalho à noite", "trabalho à noite"),
        ("Não esquece que tenho dois filhos", "tenho dois filhos"),
        ("Onthoud dat ik in Utrecht woon", "ik in Utrecht woon"),
        ("Vergeet niet dat ik vegetariër ben", "ik vegetariër ben"),
        ("Запомни, что я живу в Москве", "я живу в Москве"),
        ("Пожалуйста, запомни, что моего кота зовут Барсик", "моего кота зовут Барсик"),
        ("Не забудь, что я вегетарианец", "я вегетарианец"),
        ("记住我住在北京", "我住在北京"),
        ("请记住，我的猫叫咪咪。谢谢！", "我的猫叫咪咪"),
        ("别忘了我是素食者", "我是素食者"),
        ("私はベジタリアンだと覚えておいて", "私はベジタリアンだ"),
        ("私の猫の名前はミケだということを覚えておいてください。", "私の猫の名前はミケだ"),
        ("ねえ、私が夜勤だってこと、忘れないでね", "私が夜勤だ"),
        ("내가 채식주의자라는 걸 기억해 줘", "내가 채식주의자다"),
        ("아니, 내가 대구에 산다는 걸 기억해 줘", "내가 대구에 산다"),
        ("تذكر أنني أعيش في القاهرة", "أنني أعيش في القاهرة"),
        ("من فضلك، تذكر أن قطتي اسمها مشمش", "قطتي اسمها مشمش"),
        ("لا تنس أنني نباتي", "أنني نباتي"),
    ],
)
def test_remember_requests_in_ten_more_languages(message, fact):
    assert asks_to_remember(message)
    assert not asks_to_forget(message)
    assert extract_remember_request(message) == fact
    # Rien d'autre n'est demandé : la réponse se limite à confirmer
    assert is_only_remember_request(message, fact)


@pytest.mark.parametrize(
    "message",
    [
        # Se souvenir n'est pas retenir
        "¿Recuerdas dónde vivo?",
        "Recuerda: ¿dónde vivo?",
        "Erinnerst du dich, wo ich wohne?",
        "Ti ricordi dove abito?",
        "Você lembra onde eu moro?",
        "Lembra?",
        "Weet je nog waar ik woon?",
        "Ты помнишь, где я живу?",
        "你还记得我住在哪里吗？",
        "你记住了吗？",
        "私がどこに住んでいるか覚えてる？",
        "내가 어디 사는지 기억해?",
        "هل تتذكر أين أعيش؟",
        # « Rappelle-moi de… » n'est pas une demande de mémoire
        "Recuérdame que compre leche",
        "Lembre-me de comprar leite",
        # Ni une phrase sur soi, ni une consigne glissée dans une tâche
        "Recuerdo que vivía en Madrid",
        "Escribe la función y ten en cuenta que el puerto es 8000",
        "Ich habe mir gemerkt, wo du wohnst",
        "Я запомнил твой адрес",
        "我记住了你的地址",
        "昨日習ったことを覚えて、テストに合格した",
        # Le français et l'anglais restent lus par knowledge_base_manager seul
        "Note que le port est 8000",
    ],
)
def test_not_a_remember_request(message):
    assert not asks_to_remember(message)
    assert extract_remember_request(message) is None


@pytest.mark.parametrize(
    "message",
    ["Recuérdalo", "Recuerda esto, por favor", "Merk dir das", "Ricordatelo, grazie",
     "Lembra disso", "Onthoud dit", "Запомни это", "记住这个", "これを覚えておいて",
     "覚えておいて", "이거 기억해 줘", "تذكر هذا"],
)
def test_remember_what_came_before(message):
    """Un renvoi (« retiens ça ») : le modèle lit quoi dans les échanges précédents."""
    assert asks_to_remember(message)
    assert only_asks_to_remember(message)
    assert extract_remember_request(message) is None


@pytest.mark.parametrize(
    "message",
    ["Recuerda que vivo en Madrid", "Recuerda esto y dime la hora", "记住我住在北京",
     "私はベジタリアンだと覚えておいて"],
)
def test_not_only_what_came_before(message):
    assert not only_asks_to_remember(message)


def test_remember_this_block_keeps_every_sentence():
    """« Recuerda esto: … » : le bloc en entier, une procédure par exemple."""
    message = "Recuerda esto: lanza build.bat. Después revisa los logs. ¡Gracias!"
    assert remember_block(message) == "lanza build.bat. Después revisa los logs"
    assert remember_block("Merk dir: der Port ist 8000") == "der Port ist 8000"
    assert remember_block("Recuerda que vivo en Madrid") is None


@pytest.mark.parametrize(
    ("message", "fact"),
    [
        ("Recuerda que soy vegetariano y dame una idea de cena rápida", "soy vegetariano"),
        ("Merk dir, dass ich Vegetarier bin, und gib mir eine Idee für ein schnelles Abendessen",
         "ich Vegetarier bin"),
        ("Ricorda che sono vegetariano e dammi un'idea per cena", "sono vegetariano"),
        ("Lembra que sou vegetariano e me dá uma ideia de jantar", "sou vegetariano"),
        ("Onthoud dat ik vegetariër ben en geef me een idee voor het avondeten", "ik vegetariër ben"),
        ("Запомни, что я вегетарианец, и предложи мне быстрый ужин", "я вегетарианец"),
        ("记住我是素食者，然后推荐一个简单的晚餐", "我是素食者"),
        ("تذكر أنني نباتي وأعطني فكرة لعشاء سريع", "أنني نباتي"),
        ("私はベジタリアンだと覚えておいて、それから簡単な夕食のアイデアを教えて", "私はベジタリアンだ"),
    ],
)
def test_the_fact_stops_before_another_request(message, fact):
    """Ce que les règles lisent (sans modèle, ou quand il traduit le fait) s'arrête avant
    l'autre demande : sinon, « …y dame una idea de cena rápida » était retenu avec."""
    assert asks_to_remember(message)
    assert extract_remember_request(message) == fact
    assert not is_only_remember_request(message, fact)


def test_a_comma_inside_the_fact_stays():
    assert extract_remember_request("Recuerda que mi gato, que es negro, se llama Félix") == (
        "mi gato, que es negro, se llama Félix")
    assert extract_remember_request("تذكر أنني أعيش في القاهرة وأعمل في بنك") == (
        "أنني أعيش في القاهرة وأعمل في بنك")


def test_another_request_after_the_fact():
    assert not is_only_remember_request("Recuerda que vivo en Madrid y dime qué tiempo hace",
                                        "vivo en Madrid")
    assert not is_only_remember_request("Запомни, что я живу в Москве. Какая там погода?",
                                        "я живу в Москве")


# ── Oublier ──────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("message", "alone"),
    [
        ("Olvida que tengo un perro", True),
        ("Olvida que tengo un perro y que fumo", True),
        ("Borra de tu memoria que vivo en Madrid", True),
        ("Olvídalo", True),
        ("Olvida que tengo un perro y dame una receta", False),
        ("Olvida que tengo un perro y quedamos mañana", False),
        ("Olvida que tengo un perro. ¿Qué tiempo hace?", False),
        ("Vergiss, dass ich rauche", True),
        ("Vergiss, dass ich rauche, und schreib mir ein Gedicht", False),
        ("Lösch aus deinem Gedächtnis, dass ich in Berlin wohne", True),
        ("Dimentica che fumo", True),
        ("Esquece que eu fumo", True),
        ("Não, esquece isso", True),
        ("Vergeet dat ik rook", True),
        ("Забудь, что я курю", True),
        ("Забудь, что я курю, и напиши стихотворение", False),
        ("Удали из памяти, что я живу в Москве", True),
        ("忘掉我住在北京", True),
        ("把我抽烟这件事忘掉吧", True),
        ("忘掉我住在北京，然后告诉我天气", False),
        ("犬を飼っていることは忘れて", True),
        ("犬のことは忘れて、レシピを教えて", False),
        ("내가 담배 피운다는 거 잊어 줘", True),
        ("انس أنني أدخن", True),
        ("انسَ أنني أدخن وأعطني وصفة", False),
    ],
)
def test_forget_requests_in_ten_more_languages(message, alone):
    assert asks_to_forget(message)
    assert only_asks_to_forget(message) is alone


@pytest.mark.parametrize(
    "message",
    [
        # « N'oublie pas » demande de retenir ; un oubli constaté n'est pas une demande
        "No olvides que soy vegetariano", "Olvidé que tenía cita", "Vergiss nicht, dass ich koche",
        "Vergiss es nicht", "Ich habe vergessen, das Fenster zu schließen", "Ho dimenticato le chiavi",
        "Non dimenticare di comprare il latte", "Não esquece que tenho dois filhos", "Esqueci a chave",
        "Vergeet niet dat ik vegetariër ben", "Ik vergeet altijd mijn sleutels", "Не забудь, что я врач",
        "Я забыл ключи", "我忘了带钥匙", "忘记了带伞", "别忘记我是素食者", "你忘记了我的生日",
        "鍵を忘れてた", "忘れないで", "열쇠를 잊어버렸어", "잊지 마", "نسيت المفتاح", "لا تنس أنني نباتي",
        # « Supprime… » sans la mémoire, c'est une tâche
        "Borra el archivo temporal", "Lösche die Datei",
    ],
)
def test_not_a_forget_request(message):
    assert not asks_to_forget(message)


@pytest.mark.parametrize(
    ("message", "fact"),
    [
        ("Olvida que tengo un perro", True),
        ("Borra de tu memoria lo de mi perro", True),
        ("Vergiss, dass ich einen Hund habe", True),
        ("Забудь, что у меня есть собака", True),
        ("忘掉我有一只狗", True),
        ("把我有狗这件事忘掉吧", True),
        ("私が犬を飼っていることは忘れて", True),
        ("내가 개를 키운다는 걸 잊어 줘", True),
        ("انس أنني أملك كلبا", True),
        # « Laisse tomber » : rien de tel retenu n'est à signaler
        ("Olvídalo", False),
        ("Vergiss es", False),
        ("忘了吧", False),
        ("それは忘れて", False),
        ("그거 잊어 줘", False),
    ],
)
def test_a_forget_request_names_a_fact(message, fact):
    """Rien de tel retenu : seule une demande qui vise un fait (ou la mémoire) le dit
    (MemoryUpdate.missing)."""
    assert _forgets_a_fact(message) is fact


# ── Langue de la demande ─────────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("message", "codes"),
    [
        ("Recuerda que vivo en Madrid", ["es"]),
        ("Vergiss, dass ich rauche", ["de"]),
        ("Ricorda che abito a Roma", ["it"]),
        ("Esquece que eu fumo", ["pt"]),
        ("Onthoud dat ik in Utrecht woon", ["nl"]),
        ("Забудь, что я курю", ["ru"]),
        ("记住我住在北京", ["zh"]),
        ("犬を飼っていることは忘れて", ["ja"]),
        ("내가 채식주의자라는 걸 기억해 줘", ["ko"]),
        ("انس أنني أدخن", ["ar"]),
        # Un verbe de deux langues : le détecteur de l'appli tranche (AIEngine)
        ("Memoriza que moro em Lisboa", ["es", "pt"]),
        ("Retiens que j'habite à Lyon", []),
        ("Remember that I live in Paris", []),
        ("Bonjour", []),
    ],
)
def test_language_of_the_request(message, codes):
    """La réponse fixe « rien à oublier » et la confirmation prennent cette langue,
    même si l'appli est en français."""
    assert request_languages(message) == codes


# ── Mots qui comptent, dans toutes les écritures ─────────────────────────────


def test_content_words_in_every_script():
    """Seules les lettres latines comptaient : un fait en russe, chinois, japonais,
    coréen ou arabe ne venait « pas de l'utilisateur », et n'était pas retenu."""
    assert content_words("я живу в Москве") == ["живу", "москве"]
    assert content_words("我住在北京") == ["我住", "住在", "在北", "北京"]
    assert content_words("내가 서울에 산다") == ["내가", "서울", "울에", "산다"]
    assert content_words("أنني أعيش في القاهرة") == ["اعيش", "القاهرة"]
    # Le latin ne change pas
    assert content_words("j'ai une sœur") == ["soeur"]
    assert content_words("Recuerda que vivo en Madrid") == ["recuerda", "vivo", "madrid"]


def test_words_of_languages_written_without_spaces():
    """« 我住在北京 » n'avait qu'un mot, coupé aux espaces : trop peu pour être retenu."""
    assert word_count("我住在北京") == 3
    assert word_count("北京") == 1
    assert word_count("je m'appelle Camille") == 3
    assert is_rememberable("我住在北京")
    assert is_rememberable("私はベジタリアンです")
    assert not is_rememberable("北京")


@pytest.mark.parametrize(
    ("said", "asks"),
    [
        ("Dame una receta", True), ("Por favor, dame una receta", True), ("¿Qué hora es?", True),
        ("Gib mir ein Rezept", True), ("Расскажи анекдот", True), ("告诉我天气", True),
        ("レシピを教えて", True), ("레시피 알려 줘", True), ("اقترح وصفة", True),
        ("Mi hermana se llama Lucía y vive en Sevilla.", False),
        ("Meine Schwester heißt Anna.", False), ("Мою сестру зовут Маша.", False),
        ("我妹妹叫小美，她住在杭州。", False), ("妹の名前はミホで、福岡に住んでいます。", False),
        ("내 여동생 이름은 미나이고 부산에 살아.", False), ("اسم أختي سارة وهي تعيش في عمّان.", False),
    ],
)
def test_what_asks_for_something_rather_than_tells(said, asks):
    """Un renvoi (« 记住这个 ») dont le modèle n'a rien tiré reprend la dernière information
    de l'utilisateur : pas une question ni une autre demande."""
    assert is_request(said) is asks


@pytest.mark.parametrize(
    ("message", "parts"),
    [
        # Ce qu'il dit, puis sa question ou une autre demande
        ("Я работаю медсестрой по ночам, посоветуй, как лучше спать днём?",
         [("Я работаю медсестрой по ночам", True), ("посоветуй", False),
          ("как лучше спать днём", False)]),
        ("我上夜班，有什么白天睡好觉的建议吗？",
         [("我上夜班", True), ("有什么白天睡好觉的建议吗", False)]),
        ("أعمل ممرضًا في الليل، هل لديك نصائح للنوم أثناء النهار؟",
         [("أعمل ممرضًا في الليل", True), ("هل لديك نصائح للنوم أثناء النهار", False)]),
        ("Trabajo de noche como enfermero, ¿tienes consejos para dormir de día?",
         [("Trabajo de noche como enfermero", True),
          ("¿tienes consejos para dormir de día", False)]),
        ("Напиши мне рецепт, я вегетарианец.",
         [("Напиши мне рецепт", False), ("я вегетарианец", True)]),
        # Plusieurs phrases ; une question qui s'ouvre sur un mot interrogatif
        ("Моего сына зовут Артём, ему семь лет. Что подарить ему на день рождения?",
         [("Моего сына зовут Артём", True), ("ему семь лет", True),
          ("Что подарить ему на день рождения", False)]),
        ("Как мне лучше спать днём, если я работаю по ночам?",
         [("Как мне лучше спать днём", False), ("если я работаю по ночам", False)]),
        # Ce qu'il cherche, ce qu'il demande de faire, un salut
        ("Я ищу роман на испанском для сестры.", [("Я ищу роман на испанском для сестры", False)]),
        ("我在找一本西班牙语小说送给妹妹。", [("我在找一本西班牙语小说送给妹妹", False)]),
        ("妹のためにスペイン語の小説を探しています。",
         [("妹のためにスペイン語の小説を探しています", False)]),
        ("Procuro um romance em espanhol para a minha irmã.",
         [("Procuro um romance em espanhol para a minha irmã", False)]),
        ("Schrijf een kort gedicht over de zee.", [("Schrijf een kort gedicht over de zee", False)]),
        ("海についての短い詩を書いて。", [("海についての短い詩を書いて", False)]),
        ("바다에 관한 짧은 시를 써 줘.", [("바다에 관한 짧은 시를 써 줘", False)]),
        ("Привет! Я врач.", [("Привет", False), ("Я врач", True)]),
        # Ce qui ne vaut que pour la journée ; « de nos jours », « maintenant » durent
        ("Сегодня я опоздал на работу, представляешь?",
         [("Сегодня я опоздал на работу", False), ("представляешь", False)]),
        ("Hoje cheguei atrasado ao trabalho.", [("Hoje cheguei atrasado ao trabalho", False)]),
        ("我今天很累。", [("我今天很累", False)]),
        ("오늘 회사에 지각했어요.", [("오늘 회사에 지각했어요", False)]),
        ("Hoy en día trabajo desde casa.", [("Hoy en día trabajo desde casa", True)]),
        ("오늘날 저는 재택근무를 해요.", [("오늘날 저는 재택근무를 해요", True)]),
        ("Ya no soy profesor, ahora trabajo en un banco.",
         [("Ya no soy profesor", True), ("ahora trabajo en un banco", True)]),
        ("我已经不当老师了，现在在银行工作。",
         [("我已经不当老师了", True), ("现在在银行工作", True)]),
        # Qui ne demande rien : « …ですよ », « …운동해요 » ; un nombre reste entier
        ("私は医者ですよ。", [("私は医者ですよ", True)]),
        ("저는 매일 운동해요.", [("저는 매일 운동해요", True)]),
        ("Мне 35, я встаю в 6:30.", [("Мне 35", True), ("я встаю в 6:30", True)]),
    ],
)
def test_what_a_message_says_and_what_it_asks(message, parts):
    """Sans demande, dans les dix autres langues, ce qui est retenu est repris des parties
    du message qui disent quelque chose (core/chat_memory.py, _in_his_words) : ni sa
    question, ni une autre demande, ni ce qu'il cherche."""
    assert [(part.text, part.says) for part in message_parts(message)] == parts


@pytest.mark.parametrize(
    ("said", "secret"),
    [
        ("mi contraseña del wifi es 1234", True),
        ("mein Passwort ist geheim123", True),
        ("мой пароль от почты 1234", True),
        ("我的wifi密码是1234", True),
        ("パスワードはabcdです", True),
        ("내 비밀번호는 1234야", True),
        ("كلمة المرور الخاصة بي هي 1234", True),
        ("Escribo código en Python", False),
        ("我住在北京", False),
    ],
)
def test_passwords_are_kept_only_on_request(said, secret):
    """Sans demande, ni mot de passe ni code n'est retenu (chat_memory._SECRET_RE) : avec des
    mots qui comptent dans toutes les écritures, la lecture sans demande pouvait désormais
    en retenir un en russe, chinois, japonais, coréen ou arabe."""
    assert bool(_SECRET_RE.search(said)) is secret


# ── Conversation Code : pour quels projets ───────────────────────────────────


@pytest.mark.parametrize(
    "message",
    ["Recuerda para todos mis proyectos que uso tabuladores",
     "Merk dir für alle meine Projekte, dass ich Tabs nutze",
     "Ricorda per tutti i miei progetti che uso i tab",
     "Lembra para todos os meus projetos que uso tabs",
     "Onthoud voor al mijn projecten dat ik tabs gebruik",
     "Запомни для всех моих проектов, что я использую табы",
     "在所有项目中记住我用制表符",
     "すべてのプロジェクトで、タブを使うと覚えておいて",
     "모든 프로젝트에서 탭을 쓴다는 걸 기억해 줘",
     "تذكر في كل مشاريعي أنني أستخدم المسافات"],
)
def test_all_projects_in_ten_more_languages(message):
    assert _ALL_PROJECTS_RE.search(message)


@pytest.mark.parametrize(
    "message",
    ["Recuerda para este proyecto que uso tabuladores",
     "Merk dir für dieses Projekt, dass ich Tabs nutze",
     "Запомни для этого проекта, что я использую табы",
     "记住在这个项目中我用制表符",
     "このプロジェクトでは、タブを使うと覚えておいて"],
)
def test_this_project_in_ten_more_languages(message):
    assert _THIS_PROJECT_RE.search(message)


def test_remember_for_all_projects_reads_the_scope():
    fact, scope, _text = remember_request("Recuerda para todos mis proyectos que uso tabuladores")
    assert (fact, scope) == ("uso tabuladores", SCOPE_CODE)
    fact, scope, _text = remember_request("Recuerda que uso tabuladores")
    assert (fact, scope) == ("uso tabuladores", SCOPE_PROJECT)
