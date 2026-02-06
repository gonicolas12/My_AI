"""
ProgrammingHelpMixin — Méthodes d'aide à la programmation pour CustomAIModel.

Regroupe : _answer_programming_question, _answer_general_question,
_extract_question_subject, _detect_user_style, _explain_python_*,
_generate_general_programming_help, _get_random_response.
"""

import random
from typing import Any, Dict, List


class ProgrammingHelpMixin:
    """Mixin regroupant toutes les méthodes d'aide à la programmation."""

    def _answer_programming_question(
        self, user_input: str, context: Dict[str, Any]
    ) -> str:
        """Répond aux questions de programmation avec des exemples pratiques et intelligence avancée"""
        user_lower = user_input.lower()

        # 🚀 ANALYSE INTELLIGENTE DE LA QUESTION
        complexity_level = self._analyze_user_intelligence_level(user_input, context)

        # Réponse de base adaptée au niveau
        base_response = ""

        # Détection du type de question et réponse avec exemples
        if any(word in user_lower for word in ["liste", "list"]):
            if "différence" in user_lower and (
                "dictionnaire" in user_lower or "dict" in user_lower
            ):
                base_response = self._explain_list_vs_dict_difference()
            else:
                base_response = self._explain_python_lists()
        elif any(word in user_lower for word in ["dictionnaire", "dict"]):
            base_response = self._explain_python_dictionaries()
        elif any(word in user_lower for word in ["fonction", "def"]):
            base_response = self._explain_python_functions()
        elif any(word in user_lower for word in ["variable"]):
            base_response = self._explain_python_variables()
        elif any(word in user_lower for word in ["boucle", "for", "while"]):
            base_response = self._explain_python_loops()
        elif any(word in user_lower for word in ["condition", "if", "else"]):
            base_response = self._explain_python_conditions()
        elif any(word in user_lower for word in ["classe", "class", "objet"]):
            base_response = self._explain_python_classes()
        elif any(
            word in user_lower
            for word in ["déboguer", "debug", "débogage", "debugger", "erreur"]
        ):
            base_response = self._explain_python_debugging()
        else:
            base_response = self._generate_general_programming_help()

        # 🧠 AJOUT D'INTELLIGENCE CONTEXTUELLE
        if complexity_level == "expert":
            base_response += "\n\n💡 **Conseil d'expert** : Consultez PEP 8 pour les conventions de style Python"
            base_response += "\n🔧 **Optimisation** : Considérez l'utilisation de type hints pour une meilleure maintenabilité"
        elif complexity_level == "intermediate":
            base_response += (
                "\n\n⚡ **Conseil pro** : Testez votre code avec des cas limites"
            )
            base_response += "\n📚 **Prochaine étape** : Explorez les décorateurs et les context managers"

        # 🎯 PRÉDICTIONS INTELLIGENTES
        predictions = self._predict_user_needs(user_input, context)
        if predictions:
            base_response += f"\n\n{predictions[0]}"

        return base_response

    def _answer_general_question(self, user_input: str, context: Dict[str, Any]) -> str:
        """Répond aux questions générales avec adaptation intelligente"""
        user_lower = user_input.lower().strip()

        # Extraction du sujet de la question
        subject = self._extract_question_subject(user_input)

        # Base de connaissances pour réponses rapides
        quick_answers = {
            "pomodoro": """🍅 **La technique Pomodoro**

C'est une méthode de gestion du temps créée par Francesco Cirillo :

⏰ **Le principe :**
• Travaillez 25 minutes concentré (= 1 pomodoro)  
• Prenez une pause de 5 minutes
• Répétez 4 fois
• Puis une grande pause de 15-30 minutes

🎯 **Pourquoi c'est efficace :**
• Améliore la concentration
• Évite l'épuisement mental  
• Aide à estimer le temps nécessaire
• Réduit les distractions

📱 **Comment faire :**
• Utilisez un timer (physique ou app)
• Choisissez une tâche
• Démarrez le timer 25 min
• Travaillez sans interruption
• Stop quand ça sonne !

C'est super pour la productivité ! 🚀""",
            "intelligence artificielle": """🤖 **L'Intelligence Artificielle (IA)**

L'IA, c'est la capacité des machines à simuler l'intelligence humaine.

🧠 **Types principaux :**
• **IA faible** : Spécialisée (comme moi !)
• **IA forte** : Général (pas encore créée)
• **Machine Learning** : Apprend des données
• **Deep Learning** : Réseaux de neurones

💡 **Applications courantes :**
• Assistants vocaux (Siri, Alexa)
• Recommandations (Netflix, YouTube)
• Traduction automatique
• Reconnaissance d'images
• Voitures autonomes

🎯 **Moi par exemple :** Je suis une IA locale qui peut vous aider avec vos documents, générer du code, et discuter naturellement !""",
        }

        # Recherche de réponse rapide
        for keyword, answer in quick_answers.items():
            if keyword in user_lower:
                return answer

        # Réponse générale adaptative
        style = self._detect_user_style(context)

        if style == "casual":
            return f"🤔 Excellente question sur **{subject}** !\n\nJe peux chercher des infos là-dessus si tu veux ! Dis-moi 'cherche sur internet {subject}' et je te trouve les dernières infos ! 🔍\n\nOu alors pose-moi une question plus spécifique et je ferai de mon mieux pour t'aider ! 😊"
        else:
            return f"📚 Très bonne question concernant **{subject}** !\n\nJe peux effectuer une recherche internet pour vous fournir des informations actualisées. Dites-moi 'cherche sur internet {subject}' et je vous donnerai un résumé détaillé.\n\nVous pouvez aussi me poser une question plus spécifique et je ferai de mon mieux pour vous renseigner ! 🎯"

    def _extract_question_subject(self, user_input: str) -> str:
        """Extrait le sujet principal d'une question"""
        cleaned = user_input.lower()
        question_words = [
            "c'est quoi",
            "qu'est-ce que",
            "que signifie",
            "explique moi",
            "dis moi",
        ]

        for word in question_words:
            cleaned = cleaned.replace(word, "").strip()

        cleaned = cleaned.strip("?!.,;:")
        return cleaned if cleaned else "ce sujet"

    def _detect_user_style(self, context: Dict[str, Any]) -> str:
        """Détecte le style de communication de l'utilisateur"""
        recent_messages = context.get("recent_user_messages", [])

        casual_indicators = [
            "salut", "sa va", "wesh", "lol", "mdr", "cool", "sympa", "ok", "ouais", "wsh",
        ]
        formal_indicators = [
            "bonjour", "bonsoir", "merci beaucoup", "s'il vous plaît", "pouvez-vous",
        ]

        if any(
            any(indicator in msg.lower() for indicator in casual_indicators)
            for msg in recent_messages
        ):
            return "casual"
        elif any(
            any(indicator in msg.lower() for indicator in formal_indicators)
            for msg in recent_messages
        ):
            return "formal"
        else:
            return "neutral"

    def _explain_python_lists(self) -> str:
        """Explique comment créer et utiliser les listes en Python"""
        return """🐍 **Comment créer une liste en Python**

Une liste est une collection ordonnée d'éléments modifiables. Voici comment s'y prendre :

📝 **Création d'une liste :**
```python
# Liste vide
ma_liste = []

# Liste avec des éléments
fruits = ["pomme", "banane", "orange"]
nombres = [1, 2, 3, 4, 5]
mixte = ["texte", 42, True, 3.14]
```

🔧 **Opérations courantes :**
```python
# Ajouter un élément
fruits.append("kiwi")          # ["pomme", "banane", "orange", "kiwi"]

# Insérer à une position
fruits.insert(1, "fraise")     # ["pomme", "fraise", "banane", "orange", "kiwi"]

# Accéder à un élément
premier_fruit = fruits[0]       # "pomme"
dernier_fruit = fruits[-1]      # "kiwi"

# Modifier un élément
fruits[0] = "poire"            # ["poire", "fraise", "banane", "orange", "kiwi"]

# Supprimer un élément
fruits.remove("fraise")        # ["poire", "banane", "orange", "kiwi"]
del fruits[0]                  # ["banane", "orange", "kiwi"]

# Longueur de la liste
taille = len(fruits)           # 3
```

💡 **Conseils pratiques :**
• Les listes sont indexées à partir de 0
• Utilisez des indices négatifs pour partir de la fin
• Les listes peuvent contenir différents types de données"""

    def _explain_python_dictionaries(self) -> str:
        """Explique comment créer et utiliser les dictionnaires en Python"""
        return """🐍 **Comment créer un dictionnaire en Python**

Un dictionnaire stocke des paires clé-valeur. Parfait pour associer des données !

📝 **Création d'un dictionnaire :**
```python
# Dictionnaire vide
mon_dict = {}

# Dictionnaire avec des données
personne = {
    "nom": "Dupont",
    "age": 30,
    "ville": "Paris"
}

# Autre méthode
coords = dict(x=10, y=20, z=5)
```

🔧 **Opérations courantes :**
```python
# Accéder à une valeur
nom = personne["nom"]           # "Dupont"
age = personne.get("age", 0)    # 30 (ou 0 si pas trouvé)

# Ajouter/modifier une valeur
personne["email"] = "dupont@example.com"
personne["age"] = 31

# Vérifier si une clé existe
if "nom" in personne:
    print("Nom trouvé !")

# Supprimer un élément
del personne["ville"]
email = personne.pop("email", "")  # Récupère et supprime

# Récupérer toutes les clés/valeurs
cles = list(personne.keys())       # ["nom", "age"]
valeurs = list(personne.values())  # ["Dupont", 31]
```

💡 **Conseils pratiques :**
• Les clés doivent être uniques et immuables
• Utilisez `get()` pour éviter les erreurs
• Parfait pour structurer des données complexes"""

    def _explain_python_functions(self) -> str:
        """Explique comment créer des fonctions en Python"""
        return """🐍 **Comment créer une fonction en Python**

Les fonctions permettent de réutiliser du code et d'organiser votre programme.

📝 **Syntaxe de base :**
```python
def nom_fonction(paramètres):
    \\"\\"\\"Description de la fonction\\"\\"\\"
    # Code de la fonction
    return résultat  # optionnel
```

🔧 **Exemples pratiques :**
```python
# Fonction simple
def dire_bonjour():
    print("Bonjour !")

# Fonction avec paramètres
def saluer(nom, age=25):
    return f"Salut {nom}, tu as {age} ans !"

# Fonction avec calcul
def calculer_aire_rectangle(longueur, largeur):
    \\"\\"\\"Calcule l'aire d'un rectangle\\"\\"\\"
    aire = longueur * largeur
    return aire

# Fonction avec plusieurs retours
def diviser(a, b):
    if b == 0:
        return None, "Division par zéro impossible"
    return a / b, "OK"

# Utilisation
dire_bonjour()                          # Affiche: Bonjour !
message = saluer("Alice")               # "Salut Alice, tu as 25 ans !"
message2 = saluer("Bob", 30)            # "Salut Bob, tu as 30 ans !"
aire = calculer_aire_rectangle(5, 3)    # 15
resultat, statut = diviser(10, 2)       # 5.0, "OK"
```

💡 **Bonnes pratiques :**
• Utilisez des noms descriptifs
• Ajoutez une docstring pour documenter
• Une fonction = une responsabilité
• Utilisez des paramètres par défaut quand c'est utile"""

    def _explain_python_variables(self) -> str:
        """Explique comment créer et utiliser les variables en Python"""
        return """🐍 **Comment créer des variables en Python**

Les variables stockent des données que vous pouvez utiliser dans votre programme.

📝 **Création de variables :**
```python
# Texte (string)
nom = "Alice"
prenom = 'Bob'

# Nombres
age = 25                    # Entier (int)
taille = 1.75              # Décimal (float)

# Booléens
est_majeur = True
est_mineur = False

# Collections
fruits = ["pomme", "banane"]        # Liste
personne = {"nom": "Dupont"}        # Dictionnaire
coordonnees = (10, 20)              # Tuple (immuable)
```

🔧 **Opérations avec variables :**
```python
# Assignation multiple
x, y, z = 1, 2, 3

# Échange de valeurs
a, b = 5, 10
a, b = b, a                # a=10, b=5

# Concaténation de texte
nom_complet = prenom + " " + nom
presentation = f"Je suis {nom}, {age} ans"  # f-string

# Vérification du type
type(age)                  # <class 'int'>
isinstance(taille, float)  # True
```

💡 **Règles importantes :**
• Noms en minuscules avec _ pour séparer
• Pas d'espaces, pas de chiffres au début
• Évitez les mots-clés Python (if, for, class...)
• Soyez descriptifs : `age_utilisateur` plutôt que `a`"""

    def _explain_python_loops(self) -> str:
        """Explique les boucles en Python"""
        return """🐍 **Comment utiliser les boucles en Python**

Les boucles permettent de répéter du code automatiquement.

📝 **Boucle for (pour itérer) :**
```python
# Boucle sur une liste
fruits = ["pomme", "banane", "orange"]
for fruit in fruits:
    print(f"J'aime les {fruit}s")

# Boucle avec un range
for i in range(5):          # 0, 1, 2, 3, 4
    print(f"Compteur: {i}")

# Boucle avec index et valeur
for index, fruit in enumerate(fruits):
    print(f"{index}: {fruit}")
```

🔄 **Boucle while (tant que) :**
```python
compteur = 0
while compteur < 5:
    print(f"Compteur: {compteur}")
    compteur += 1

# Boucle infinie contrôlée
while True:
    reponse = input("Continuez ? (o/n): ")
    if reponse.lower() == 'n':
        break
```

🛑 **Contrôle des boucles :**
```python
# break : sort de la boucle
for i in range(10):
    if i == 5:
        break

# continue : passe à l'itération suivante
for i in range(5):
    if i == 2:
        continue
    print(i)
```

💡 **Conseils pratiques :**
• `for` pour un nombre connu d'itérations
• `while` pour des conditions variables
• Attention aux boucles infinies avec `while`
• Utilisez `enumerate()` si vous avez besoin de l'index"""

    def _explain_python_conditions(self) -> str:
        """Explique les conditions en Python"""
        return """🐍 **Comment utiliser les conditions en Python**

Les conditions permettent d'exécuter du code selon certains critères.

📝 **Structure if/elif/else :**
```python
age = 18

if age >= 18:
    print("Vous êtes majeur")
elif age >= 16:
    print("Vous pouvez conduire")
else:
    print("Vous êtes enfant")
```

🔍 **Opérateurs de comparaison :**
```python
x == y          # Égal à
x != y          # Différent de
x > y           # Supérieur à
x >= y          # Supérieur ou égal
```

🔗 **Opérateurs logiques :**
```python
if age >= 18 and nom == "Alice":
    print("Alice est majeure")

if age < 18 or nom == "Bob":
    print("Mineur ou Bob")

if not (age < 18):
    print("Pas mineur = majeur")
```

🎯 **Conditions avancées :**
```python
# Opérateur ternaire
statut = "majeur" if age >= 18 else "mineur"

# Vérification d'existence
if fruits:                 # True si la liste n'est pas vide
    print("Il y a des fruits")
```

💡 **Bonnes pratiques :**
• Utilisez des parenthèses pour clarifier les conditions complexes
• Préférez `is` et `is not` pour comparer avec `None`
• Évitez les conditions trop imbriquées"""

    def _explain_python_classes(self) -> str:
        """Explique les classes en Python"""
        return """🐍 **Comment créer des classes en Python**

Les classes permettent de créer vos propres types d'objets avec propriétés et méthodes.

📝 **Syntaxe de base :**
```python
class Personne:
    def __init__(self, nom, age):
        self.nom = nom
        self.age = age
    
    def se_presenter(self):
        return f"Je suis {self.nom}, j'ai {self.age} ans"
```

🏗️ **Utilisation de la classe :**
```python
alice = Personne("Alice", 25)
bob = Personne("Bob", 30)

print(alice.se_presenter())     # "Je suis Alice, j'ai 25 ans"
```

• `self` : référence à l'instance courante
• Attributs : variables de l'objet
• Méthodes : fonctions de l'objet
• Encapsulation : regrouper données et comportements"""

    def _explain_list_vs_dict_difference(self) -> str:
        """Explique la différence entre les listes et les dictionnaires"""
        return """📋 **Différence entre Liste et Dictionnaire en Python**

📋 **LISTES (list)**
```python
fruits = ["pomme", "banane", "orange"]
```
• **Ordonnées** : Les éléments ont une position fixe
• **Indexées par position** : fruits[0] = "pomme"
• **Permettent les doublons**

🗂️ **DICTIONNAIRES (dict)**
```python
personne = {"nom": "Alice", "age": 30}
```
• **Associatifs** : Chaque valeur a une clé unique
• **Indexés par clé** : personne["nom"] = "Alice"
• **Clés uniques**

🎯 **Quand utiliser quoi ?**
• **Liste** : collection ordonnée, doublons possibles
• **Dictionnaire** : association clé-valeur, accès rapide par nom"""

    def _explain_python_debugging(self) -> str:
        """Explique comment déboguer du code Python"""
        return """🐍 **Comment déboguer du code Python**

🔍 **Types d'erreurs courantes :**
• Erreur de syntaxe : parenthèse manquante
• Erreur de type : str + int
• Erreur d'index : liste[999]

🛠️ **Techniques de débogage :**
```python
# Print pour tracer
print(f"DEBUG: x={x}, y={y}")

# Try/except pour gérer les erreurs
try:
    resultat = a / b
except ZeroDivisionError:
    print("Division par zéro!")

# Assertions
assert nombre >= 0, "Le nombre doit être positif"
```

🎯 **Méthode systématique :**
1. **Reproduire** l'erreur
2. **Localiser** où ça plante
3. **Comprendre** pourquoi
4. **Corriger** le problème
5. **Tester** la correction"""

    def _generate_general_programming_help(self) -> str:
        """Génère une aide générale sur la programmation"""
        return """🐍 **Aide générale Python**

Je peux vous aider avec de nombreux concepts Python ! Voici quelques exemples :

📚 **Sujets disponibles :**
• **Listes** : "Comment créer une liste en Python ?"
• **Dictionnaires** : "Comment utiliser un dictionnaire ?"
• **Fonctions** : "Comment créer une fonction ?"
• **Variables** : "Comment déclarer une variable ?"
• **Boucles** : "Comment faire une boucle for ?"
• **Conditions** : "Comment utiliser if/else ?"
• **Classes** : "Comment créer une classe ?"

🎯 **Soyez spécifique :** Plus votre question est précise, plus ma réponse sera adaptée à vos besoins !

Que voulez-vous apprendre exactement ?"""

    def _get_random_response(self, responses: List[str]) -> str:
        """Sélectionne une réponse aléatoire"""
        return random.choice(responses)
