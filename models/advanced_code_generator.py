"""
Générateur de code avancé
"""

import base64
import hashlib
import json
import os
import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import quote, urljoin

import aiohttp
import yaml
from bs4 import BeautifulSoup
from sentence_transformers import SentenceTransformer

from models.real_web_code_generator import RealWebCodeGenerator


@dataclass
class CodeSolution:
    """Structure pour une solution de code"""

    code: str
    language: str
    explanation: str
    source: str
    rating: float
    complexity: str
    tags: List[str]
    examples: List[str]


@dataclass
class CodeRequest:
    """Structure pour une demande de code"""

    description: str
    language: str
    complexity: str
    requirements: List[str]
    context: Dict[str, Any]


# Classe unique AdvancedCodeGenerator
class AdvancedCodeGenerator:
    """
    Générateur de code avancé avec intégration multi-sources
    """

    def __init__(self):
        self.stackoverflow_searcher = StackOverflowCodeExtractor()
        self.github_searcher = GitHubCodeSearcher()
        self.fallback_templates = self._load_fallback_templates()
        self.intent_patterns = self._load_intent_patterns()
        try:
            self.embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
        except Exception:
            self.embedding_model = None
        # Import et initialisation du générateur web
        try:
            self.web_generator = RealWebCodeGenerator()
        except Exception:
            self.web_generator = None

    async def generate_code(
        self,
        description: str,
        language: str = "python",
        complexity: str = "Intermédiaire",
        requirements: List[str] = None,
        context: Dict[str, Any] = None,
    ) -> Dict[str, Any]:
        """
        MÉTHODE PRINCIPALE - Génère du code basé sur une description
        """
        if requirements is None:
            requirements = []
        if context is None:
            context = {}

        # CORRECTION: S'assurer que tous les paramètres sont des chaînes
        description = (
            str(description) if not isinstance(description, str) else description
        )
        language = str(language) if not isinstance(language, str) else language
        complexity = str(complexity) if not isinstance(complexity, str) else complexity

        # Créer la requête
        request = CodeRequest(
            description=description,
            language=language,
            complexity=complexity,
            requirements=requirements,
            context=context,
        )

        debug_info = []
        all_solutions = []

        try:
            # 1. Chercher sur Stack Overflow
            debug_info.append("[INFO] Recherche sur Stack Overflow...")
            so_solutions = (
                await self.stackoverflow_searcher.search_stackoverflow_solutions(
                    request, debug_info
                )
            )
            all_solutions.extend(so_solutions)

            # 2. Chercher sur GitHub
            debug_info.append("[INFO] Recherche sur GitHub...")
            gh_solutions = await self.github_searcher.search_github_repositories(
                request, debug_info
            )
            all_solutions.extend(gh_solutions)

            # 3. Si pas assez de solutions, générer une solution de fallback
            if len(all_solutions) == 0:
                debug_info.append(
                    "[INFO] Aucune solution trouvée, génération d'une solution de base..."
                )
                fallback_solution = self.generate_fallback_solution(request)
                all_solutions.append(fallback_solution)

            # 4. Trier et sélectionner la meilleure solution
            best_solutions = self._rank_solutions(all_solutions, request)
            best_solution = best_solutions[0] if best_solutions else None

            if best_solution:
                return {
                    "success": True,
                    "code": best_solution.code,
                    "language": best_solution.language,
                    "explanation": best_solution.explanation,
                    "source": best_solution.source,
                    "rating": best_solution.rating,
                    "complexity": best_solution.complexity,
                    "tags": best_solution.tags,
                    "alternatives": (
                        best_solutions[1:3] if len(best_solutions) > 1 else []
                    ),
                    "debug_info": debug_info,
                }
            else:
                return {
                    "success": False,
                    "error": "Impossible de générer une solution",
                    "debug_info": debug_info,
                }

        except Exception as e:
            debug_info.append(f"[ERROR] Erreur lors de la génération: {e}")
            return {"success": False, "error": str(e), "debug_info": debug_info}

    def _rank_solutions(
        self, solutions: List[CodeSolution], request: CodeRequest
    ) -> List[CodeSolution]:
        """Classe les solutions par ordre de pertinence"""
        if not solutions:
            return []

        # Calculer un score pour chaque solution
        scored_solutions = []

        for solution in solutions:
            score = solution.rating * 2  # Score de base

            # Bonus pour correspondance de langage
            if solution.language.lower() == request.language.lower():
                score += 2

            # Bonus pour correspondance de complexité
            if solution.complexity.lower() == request.complexity.lower():
                score += 1

            # Bonus pour longueur de code appropriée
            code_length = len(solution.code)
            if 20 <= code_length <= 200:  # Code court et lisible
                score += 3
            elif 200 <= code_length <= 500:  # Code moyen
                score += 2
            elif code_length <= 20:  # Trop court
                score += 0.5
            else:  # Trop long
                score -= 1

            # Bonus pour mots-clés dans la description
            description_words = set(request.description.lower().split())
            explanation_words = set(solution.explanation.lower().split())
            matching_words = description_words & explanation_words
            score += len(matching_words) * 0.3

            scored_solutions.append((score, solution))

        # Trier par score décroissant
        scored_solutions.sort(key=lambda x: x[0], reverse=True)

        return [solution for score, solution in scored_solutions]

    def _extract_intent_concepts(self, description: str) -> dict:
        """Analyse NLP pour extraire action, objet, critère, etc. de la demande utilisateur."""
        desc = description.lower()
        actions = [
            ("trier", ["trier", "tri", "sort", "ordre"]),
            ("additionner", ["addition", "add", "somme", "sum", "plus", "total"]),
            ("retourner", ["retourner", "renvoyer", "return", "donner", "afficher"]),
            ("extraire", ["extraire", "extract", "trouver", "chercher", "get"]),
            (
                "max",
                ["plus grand", "maximum", "max", "le plus long", "longueur", "long"],
            ),
            ("min", ["plus petit", "minimum", "min", "court", "le plus court"]),
            ("filtrer", ["filtrer", "filter", "sélectionner", "select"]),
            ("compter", ["compter", "count", "nombre", "quantité"]),
        ]
        objets = [
            (
                "mot",
                ["mot", "string", "texte", "mot le plus long", "mot le plus court"],
            ),
            ("nombre", ["nombre", "chiffre", "int", "float", "entier"]),
            ("liste", ["liste", "array", "tableau", "list"]),
            ("élément", ["élément", "item", "valeur"]),
        ]
        criteres = [
            ("longueur", ["longueur", "len", "taille", "length"]),
            ("valeur", ["valeur", "value", "contenu"]),
        ]
        result = {"action": None, "objet": None, "critere": None}
        for act, keys in actions:
            if any(k in desc for k in keys):
                result["action"] = act
                break
        for obj, keys in objets:
            if any(k in desc for k in keys):
                result["objet"] = obj
                break
        for crit, keys in criteres:
            if any(k in desc for k in keys):
                result["critere"] = crit
                break
        if re.search(r"mot\s+le\s+plus\s+long", desc):
            result["action"] = "max"
            result["objet"] = "mot"
            result["critere"] = "longueur"
        return result

    def _load_fallback_templates(self) -> Dict[str, Dict[str, str]]:
        """Charge les templates de code de base par langage et par type de problème"""
        return {
            "python": {
                "basic_function": """def {function_name}({parameters}):
    '''
    {description}
    '''
    # Votre code ici
    return result""",
                "list_processing": """def process_list(items):
    '''
    Traite une liste d'éléments
    '''
    result = []
    for item in items:
        # Traitement de l'item
        result.append(item)
    return result""",
                "string_manipulation": """def manipulate_string(text):
    '''
    Manipule une chaîne de caractères
    '''
    # Exemple: inverser une chaîne
    return text[::-1]""",
                "file_operations": """def read_file(filename):
    '''
    Lit un fichier
    '''
    try:
        with open(filename, 'r', encoding='utf-8') as file:
            content = file.read()
        return content
    except FileNotFoundError:
        return "Fichier non trouvé\"""",
                "api_request": """import requests

def make_api_request(url, params=None):
    '''
    Effectue une requête API
    '''
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        return {"error": str(e)}""",
            },
            "javascript": {
                "basic_function": """function {function_name}({parameters}) {
    /*
     * {description}
     */
    // Votre code ici
    return result;
}""",
                "array_processing": """function processArray(items) {
    /*
     * Traite un tableau d'éléments
     */
    return items.map(item => {
        // Traitement de l'item
        return item;
    });
}""",
                "dom_manipulation": """function manipulateDOM(elementId) {
    /*
     * Manipule un élément DOM
     */
    const element = document.getElementById(elementId);
    if (element) {
        // Manipulation de l'élément
        element.textContent = "Nouveau contenu";
    }
}""",
            },
            "java": {
                "basic_class": """public class {class_name} {
    /*
     * {description}
     */
    public static void main(String[] args) {
        // Votre code ici
    }
}""",
                "method_template": """public {return_type} {method_name}({parameters}) {
    /*
     * {description}
     */
    // Votre code ici
    return result;
}""",
            },
        }

    def _load_intent_patterns(self) -> Dict[str, List[str]]:
        """Charge les patterns d'intention pour analyser les demandes utilisateur"""
        return {
            "sorting": [
                r"trier",
                r"tri",
                r"sort",
                r"ordre",
                r"ordonner",
                r"classer",
                r"organiser",
                r"ranger",
                r"alphabétique",
                r"croissant",
                r"décroissant",
            ],
            "searching": [
                r"chercher",
                r"rechercher",
                r"trouver",
                r"localiser",
                r"identifier",
                r"search",
                r"find",
                r"locate",
                r"get",
                r"extract",
                r"récupérer",
            ],
            "filtering": [
                r"filtrer",
                r"filter",
                r"sélectionner",
                r"select",
                r"garder",
                r"éliminer",
                r"exclure",
                r"include",
                r"exclude",
                r"où",
                r"qui",
            ],
            "calculating": [
                r"calculer",
                r"calculate",
                r"compter",
                r"count",
                r"somme",
                r"sum",
                r"moyenne",
                r"average",
                r"total",
                r"addition",
                r"multiplication",
                r"division",
                r"soustraction",
                r"mathématique",
            ],
            "transforming": [
                r"transformer",
                r"transform",
                r"convertir",
                r"convert",
                r"modifier",
                r"changer",
                r"adapter",
                r"ajuster",
                r"formater",
                r"format",
            ],
            "string_operations": [
                r"chaîne",
                r"string",
                r"texte",
                r"text",
                r"caractère",
                r"char",
                r"mot",
                r"word",
                r"phrase",
                r"sentence",
                r"inverser",
                r"reverse",
                r"remplacer",
                r"replace",
                r"diviser",
                r"split",
                r"joindre",
                r"join",
            ],
            "file_operations": [
                r"fichier",
                r"file",
                r"lire",
                r"read",
                r"écrire",
                r"write",
                r"sauvegarder",
                r"save",
                r"charger",
                r"load",
                r"ouvrir",
                r"open",
                r"csv",
                r"json",
                r"txt",
                r"xml",
                r"yaml",
            ],
            "web_operations": [
                r"api",
                r"http",
                r"request",
                r"response",
                r"url",
                r"web",
                r"site",
                r"page",
                r"scraping",
                r"crawling",
                r"télécharger",
                r"download",
                r"upload",
                r"post",
                r"get",
                r"put",
                r"delete",
            ],
            "data_structures": [
                r"liste",
                r"list",
                r"array",
                r"tableau",
                r"dictionnaire",
                r"dict",
                r"hash",
                r"map",
                r"set",
                r"tuple",
                r"stack",
                r"queue",
                r"pile",
                r"file",
                r"arbre",
                r"tree",
                r"graphe",
                r"graph",
            ],
        }

    def generate_fallback_solution(self, request: CodeRequest) -> CodeSolution:
        """Génère une solution de base quand aucune n'est trouvée en ligne"""

        # Analyser l'intention de la requête
        intent = self._analyze_request_intent(request.description)

        # Sélectionner le template approprié
        templates = self.fallback_templates.get(request.language.lower(), {})

        if intent == "string_operations" and "string_manipulation" in templates:
            template = templates["string_manipulation"]
        elif intent == "file_operations" and "file_operations" in templates:
            template = templates["file_operations"]
        elif intent == "web_operations" and "api_request" in templates:
            template = templates["api_request"]
        elif (
            intent in ["sorting", "filtering", "transforming"]
            and "list_processing" in templates
        ):
            template = templates["list_processing"]
        else:
            # Template de base
            template = templates.get(
                "basic_function", "# Code de base\nprint('Hello World')"
            )

        # Personnaliser le template si possible
        personalized_code = self._personalize_template(template, request)

        return CodeSolution(
            code=personalized_code,
            language=request.language,
            explanation=f"Solution de base générée pour: {request.description}",
            source="Template interne",
            rating=3.0,
            complexity=request.complexity,
            tags=[request.language, "template", "basic"],
            examples=[personalized_code],
        )

    def _analyze_request_intent(self, description: str) -> str:
        """Analyse l'intention de la requête utilisateur"""
        description_lower = description.lower()

        # Scorer chaque catégorie d'intention
        intent_scores = {}

        for intent, patterns in self.intent_patterns.items():
            score = 0
            for pattern in patterns:
                if re.search(pattern, description_lower):
                    score += 1
            intent_scores[intent] = score

        # Retourner l'intention avec le score le plus élevé
        if intent_scores:
            best_intent = max(intent_scores, key=intent_scores.get)
            if intent_scores[best_intent] > 0:
                return best_intent

        return "general"

    def _personalize_template(self, template: str, request: CodeRequest) -> str:
        """Personnalise un template avec les détails de la requête"""
        personalized = template

        # Remplacer les placeholders génériques
        replacements = {
            "{function_name}": self._generate_function_name(request.description),
            "{parameters}": self._generate_parameters(request.description),
            "{description}": request.description,
            "{class_name}": self._generate_class_name(request.description),
            "{return_type}": self._guess_return_type(
                request.description, request.language
            ),
            "{method_name}": self._generate_function_name(request.description),
        }

        for placeholder, value in replacements.items():
            if placeholder in personalized:
                personalized = personalized.replace(placeholder, value)

        return personalized

    def _generate_function_name(self, description: str) -> str:
        """Génère un nom de fonction basé sur la description"""
        # Extraire les mots-clés principaux
        words = re.findall(r"\b[a-zA-Z]+\b", description.lower())

        # Filtrer les mots utiles
        useful_words = []
        stop_words = {
            "le",
            "la",
            "les",
            "un",
            "une",
            "des",
            "et",
            "ou",
            "de",
            "du",
            "pour",
            "avec",
            "sur",
            "dans",
        }

        for word in words[:3]:  # Prendre les 3 premiers mots utiles
            if word not in stop_words and len(word) > 2:
                useful_words.append(word)

        if not useful_words:
            return "ma_fonction"

        # Créer le nom de fonction
        function_name = "_".join(useful_words)
        return function_name if function_name else "ma_fonction"

    def _generate_parameters(self, description: str) -> str:
        """Génère des paramètres basés sur la description"""
        description_lower = description.lower()

        params = []

        # Détecter les types de paramètres courants
        if any(
            word in description_lower for word in ["liste", "array", "tableau", "list"]
        ):
            params.append("items")

        if any(
            word in description_lower
            for word in ["chaîne", "string", "texte", "text", "mot"]
        ):
            params.append("text")

        if any(
            word in description_lower
            for word in ["nombre", "number", "int", "float", "valeur"]
        ):
            params.append("number")

        if any(word in description_lower for word in ["fichier", "file"]):
            params.append("filename")

        return ", ".join(params) if params else "data"

    def _generate_class_name(self, description: str) -> str:
        """Génère un nom de classe basé sur la description"""
        words = re.findall(r"\b[a-zA-Z]+\b", description)
        if words:
            # Utiliser le premier mot significatif et le mettre en PascalCase
            first_word = words[0].capitalize()
            return f"{first_word}Processor"
        return "MyClass"

    def _guess_return_type(self, description: str, language: str) -> str:
        """Devine le type de retour basé sur la description et le langage"""
        description_lower = description.lower()

        if language.lower() == "java":
            if any(word in description_lower for word in ["liste", "array", "list"]):
                return "List<String>"
            elif any(word in description_lower for word in ["nombre", "int", "count"]):
                return "int"
            elif any(
                word in description_lower for word in ["texte", "string", "chaîne"]
            ):
                return "String"
            elif any(
                word in description_lower
                for word in ["boolean", "vrai", "faux", "true", "false"]
            ):
                return "boolean"
            else:
                return "Object"

        return "auto"  # Pour les autres langages

    def generate_simple_function(self, text: str) -> str:
        """Génère une fonction simple basée sur la demande"""
        if "factorielle" in text.lower():
            return """🔧 Fonction générée :

```python
def factorielle(n):
    \"\"\"
    Calcule la factorielle d'un nombre

    Args:
        n (int): Nombre dont on veut la factorielle

    Returns:
        int: Factorielle de n
    \"\"\"
    if n < 0:
        raise ValueError("La factorielle n'est pas définie pour les nombres négatifs")
    elif n == 0 or n == 1:
        return 1
    else:
        return n * factorielle(n - 1)

# Exemple d'utilisation
print(factorielle(5))  # Output: 120
```"""
        elif "fibonacci" in text.lower():
            return """🔧 Fonction générée :

```python
def fibonacci(n):
    \"\"\"
    Calcule le n-ième nombre de Fibonacci

    Args:
        n (int): Position dans la séquence

    Returns:
        int: n-ième nombre de Fibonacci
    \"\"\"
    if n <= 0:
        return 0
    elif n == 1:
        return 1
    else:
        return fibonacci(n-1) + fibonacci(n-2)

# Exemple d'utilisation
for i in range(10):
    print(f"F({i}) = {fibonacci(i)}")
```"""
        else:
            return f"""🔧 Fonction générée basée sur votre demande :

```python
def ma_fonction():
    \"\"\"
    Fonction générée automatiquement
    Basée sur : {text}
    \"\"\"
    # TODO: Implétez votre logique ici
    print("Fonction créée avec succès !")
    return True

# Exemple d'utilisation
ma_fonction()
```
💡 Pour une génération plus précise, décrivez exactement ce que doit faire la fonction."""

    def generate_simple_class(self, text: str) -> str:
        """Génère une classe simple basée sur la demande"""
        if "personne" in text.lower() or "person" in text.lower():
            return """🏗️ Classe générée :

```python
class Personne:
    \"\"\"
    Classe représentant une personne
    \"\"\"

    def __init__(self, nom, age):
        \"\"\"
        Initialise une nouvelle personne

        Args:
            nom (str): Nom de la personne
            age (int): Âge de la personne
        \"\"\"
        self.nom = nom
        self.age = age

    def se_presenter(self):
        \"\"\"Présente la personne\"\"\"
        return f"Bonjour, je suis {self.nom} et j'ai {self.age} ans."

    def avoir_anniversaire(self):
        \"\"\"Incrémente l'âge d'un an\"\"\"
        self.age += 1
        return f"Joyeux anniversaire ! {self.nom} a maintenant {self.age} ans."

# Exemple d'utilisation
personne = Personne("Alice", 25)
print(personne.se_presenter())
print(personne.avoir_anniversaire())
```"""
        else:
            return f"""🏗️ Classe générée basée sur votre demande :

```python
class MaClasse:
    \"\"\"
    Classe générée automatiquement
    Basée sur : {text}
    \"\"\"

    def __init__(self):
        \"\"\"Initialise la classe\"\"\"
        self.nom = "MaClasse"
        self.active = True

    def action(self):
        \"\"\"Méthode d'action principale\"\"\"
        if self.active:
            return "Action exécutée avec succès !"
        return "Classe inactive"

    def __str__(self):
        \"\"\"Représentation string de la classe\"\"\"
        return f"{self.nom} - Active: {self.active}"

# Exemple d'utilisation
objet = MaClasse()
print(objet)
print(objet.action())
```

💡 Pour une génération plus précise, décrivez les attributs et méthodes souhaités."""

    def generate_code_from_text(self, text: str) -> str:
        """Génère du code basé sur une description textuelle"""
        return f"""💻 Code généré basé sur votre demande :

```python
# Code basé sur : {text}

def solution():
    \"\"\"
    Solution générée automatiquement
    \"\"\"
    # TODO: Implétez votre solution ici
    print("Code généré avec succès !")

    # Exemple de logique de base
    resultat = "Mission accomplie"
    return resultat

# Exécution
if __name__ == "__main__":
    print(solution())
```

💡 Pour une génération plus complète, fournissez plus de détails sur les fonctionnalités souhaitées."""

    async def generate_code_from_web(
        self, query: str, language: str = "python"
    ) -> Dict[str, Any]:
        """
        Génère du code UNIQUEMENT à partir de recherches web réelles
        Délègue à RealWebCodeGenerator pour la recherche web
        """
        if self.web_generator:
            return await self.web_generator.generate_code_from_web(query, language)
        else:
            # Fallback si RealWebCodeGenerator n'est pas disponible
            return {"success": False, "error": "Générateur web non disponible"}


class StackOverflowCodeExtractor:
    """Extracteur de code depuis Stack Overflow"""

    def __init__(self):
        self.base_url = "https://api.stackexchange.com/2.3"
        self.site = "stackoverflow"
        self.cache_db = Path("context_storage/code_solutions_cache.db")
        self._init_cache()

        # Headers pour imiter un navigateur réel
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json, text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
        }

    def _init_cache(self):
        """Initialise la base de données de cache"""
        with sqlite3.connect(self.cache_db) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS code_solutions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    query_hash TEXT UNIQUE,
                    query TEXT,
                    language TEXT,
                    solution_json TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    rating REAL,
                    source TEXT
                )
            """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_query_hash ON code_solutions(query_hash)
            """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_language ON code_solutions(language)
            """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_rating ON code_solutions(rating DESC)
            """
            )

    def _get_query_hash(self, query: str, language: str) -> str:
        """Génère un hash pour la requête"""
        content = f"{query.lower().strip()}:{language.lower()}"
        return hashlib.md5(content.encode()).hexdigest()

    async def search_stackoverflow_solutions(
        self, request: CodeRequest, debug_info: list = None
    ) -> List[CodeSolution]:
        """Recherche des solutions sur Stack Overflow"""
        if debug_info is None:
            debug_info = []
        query_hash = self._get_query_hash(request.description, request.language)
        debug_info.append(f"[DEBUG][SO] Query hash: {query_hash}")
        cached_solution = self._get_cached_solution(query_hash)
        if cached_solution:
            debug_info.append("[DEBUG][SO] Solution trouvée dans le cache.")
            return [cached_solution]

        try:
            search_terms = self._build_search_terms(request)
            debug_info.append(f"[DEBUG][SO] Search terms: {search_terms}")
            api_solutions, api_debug = await self._search_via_api(
                search_terms, request.language
            )
            debug_info.append(f"[DEBUG][SO] Solutions API: {len(api_solutions)}")
            debug_info.extend(api_debug)
            if len(api_solutions) < 3:
                web_solutions, web_debug = await self._search_via_web_scraping(
                    search_terms, request.language
                )
                debug_info.append(
                    f"[DEBUG][SO] Solutions scraping: {len(web_solutions)}"
                )
                debug_info.extend(web_debug)
                api_solutions.extend(web_solutions)
            best_solutions = self._filter_and_rank_solutions(api_solutions, request)
            debug_info.append(f"[DEBUG][SO] Solutions filtrées: {len(best_solutions)}")
            for solution in best_solutions[:3]:
                self._cache_solution(
                    query_hash, request.description, request.language, solution
                )
            return best_solutions
        except Exception as e:
            debug_info.append(f"[DEBUG][SO] Erreur recherche Stack Overflow: {e}")
            return []

    def _build_search_terms(self, request: CodeRequest) -> str:
        """Construit des termes de recherche optimisés pour APIs internationales"""
        description = request.description.lower()

        # Traduction directe français -> anglais
        translations = {
            "tic tac toe": "tic tac toe",
            "morpion": "tic tac toe",
            "jeu": "game",
            "jouer": "game",
            "génère": "create",
            "programme": "program",
            "fonction": "function",
            "calculer": "calculate",
            "trier": "sort",
            "chercher": "search",
            "inverser": "reverse",
        }

        # Construire la requête en anglais
        english_terms = []

        # Détecter les concepts spécifiques
        if "tic tac toe" in description or "morpion" in description:
            english_terms = ["tic", "tac", "toe", "python", "game"]
        elif "jeu" in description:
            english_terms = ["game", "python"]
        else:
            # Traduire terme par terme
            for fr_word, en_word in translations.items():
                if fr_word in description:
                    english_terms.append(en_word)

        # Ajouter le langage si pas déjà présent
        if request.language.lower() not in english_terms:
            english_terms.append(request.language.lower())

        # Limiter à 4-5 termes pour éviter les requêtes trop complexes
        final_query = " ".join(english_terms[:5])

        return final_query

    def _extract_technical_keywords(self, description: str) -> List[str]:
        """Extrait les mots-clés techniques de la description"""
        # Dictionnaire de mots-clés techniques par domaine
        tech_patterns = {
            "web": [
                "api",
                "http",
                "request",
                "response",
                "json",
                "xml",
                "rest",
                "ajax",
                "fetch",
            ],
            "data": [
                "database",
                "sql",
                "query",
                "insert",
                "select",
                "update",
                "delete",
                "orm",
            ],
            "algorithms": [
                "sort",
                "search",
                "tree",
                "graph",
                "hash",
                "algorithm",
                "recursive",
            ],
            "ui": [
                "button",
                "form",
                "input",
                "display",
                "show",
                "hide",
                "click",
                "event",
            ],
            "file": [
                "file",
                "read",
                "write",
                "save",
                "load",
                "import",
                "export",
                "csv",
                "txt",
            ],
            "math": [
                "calculate",
                "sum",
                "average",
                "count",
                "math",
                "number",
                "integer",
            ],
            "string": ["string", "text", "format", "replace", "split", "join", "regex"],
            "date": ["date", "time", "datetime", "timestamp", "format", "parse"],
            "error": ["error", "exception", "try", "catch", "handle", "debug"],
            "async": ["async", "await", "promise", "callback", "thread", "concurrent"],
        }

        description_lower = description.lower()
        keywords = []

        for terms in tech_patterns.items():
            for term in terms:
                if term in description_lower:
                    keywords.append(term)

        # Extraire aussi les mots importants (noms, verbes techniques)
        words = re.findall(r"\b[a-zA-Z]+\b", description)
        important_words = [
            w
            for w in words
            if len(w) > 3
            and w.lower() not in ["the", "and", "for", "with", "that", "this"]
        ]

        return list(set(keywords + important_words[:5]))

    async def _search_via_api(
        self, search_terms: str, language: str
    ) -> Tuple[List[CodeSolution], List[str]]:
        """Recherche via l'API Stack Exchange avec debug"""
        solutions = []
        debug = []
        try:
            async with aiohttp.ClientSession() as session:
                # Construire une requête conforme à l'API Stack Overflow
                params = {
                    "order": "desc",
                    "sort": "relevance",
                    "intitle": search_terms,  # OBLIGATOIRE: utiliser intitle au lieu de q
                    "tagged": language,  # OBLIGATOIRE: spécifier le tag langage
                    "site": self.site,
                    "pagesize": 10,
                }
                async with session.get(
                    f"{self.base_url}/search", params=params
                ) as response:
                    debug.append(f"[DEBUG][SO][API] Status: {response.status}")
                    if response.status == 200:
                        data = await response.json()
                        questions = data.get("items", [])
                        debug.append(
                            f"[DEBUG][SO][API] Questions trouvées: {len(questions)}"
                        )
                        for question in questions:
                            debug.append(
                                f"[DEBUG][SO][API] Question: {question.get('title', '')}"
                            )
                            question_id = question["question_id"]
                            answer_solutions = await self._get_answers_for_question(
                                session, question_id, language, debug
                            )
                            debug.append(
                                f"[DEBUG][SO][API] Réponses pour question {question_id}: {len(answer_solutions)}"
                            )
                            solutions.extend(answer_solutions)
                            if len(solutions) >= 10:
                                break
        except Exception as e:
            debug.append(f"[DEBUG][SO][API] Erreur: {e}")
        return solutions, debug

    async def _get_answers_for_question(
        self,
        session: aiohttp.ClientSession,
        question_id: int,
        language: str,
        debug_info: list = None,
    ) -> List[CodeSolution]:
        """Récupère les réponses pour une question donnée"""
        solutions = []
        if debug_info is None:
            debug_info = []

        try:
            params = {
                "order": "desc",
                "sort": "votes",
                "site": self.site,
                "filter": "withbody",  # IMPORTANT: inclure le body des réponses
            }

            async with session.get(
                f"{self.base_url}/questions/{question_id}/answers", params=params
            ) as response:
                debug_info.append(
                    f"[DEBUG][SO][ANSWERS] Status pour question {question_id}: {response.status}"
                )
                if response.status == 200:
                    data = await response.json()
                    answers = data.get("items", [])
                    debug_info.append(
                        f"[DEBUG][SO][ANSWERS] Réponses trouvées: {len(answers)}"
                    )

                    for answer in answers:
                        score = answer.get("score", 0)
                        is_accepted = answer.get("is_accepted", False)
                        debug_info.append(
                            f"[DEBUG][SO][ANSWERS] Réponse score: {score}, acceptée: {is_accepted}"
                        )

                        if is_accepted or score > 0:
                            solution = self._parse_answer_to_solution(answer, language)
                            if solution:
                                debug_info.append(
                                    "[DEBUG][SO][ANSWERS] Solution extraite avec succès"
                                )
                                solutions.append(solution)
                            else:
                                debug_info.append(
                                    "[DEBUG][SO][ANSWERS] Échec extraction solution"
                                )
                else:
                    debug_info.append(
                        f"[DEBUG][SO][ANSWERS] Erreur API: {response.status}"
                    )

        except Exception as e:
            debug_info.append(f"[DEBUG][SO][ANSWERS] Erreur: {e}")

        return solutions

    def _parse_answer_to_solution(
        self, answer: Dict, language: str
    ) -> Optional[CodeSolution]:
        """Parse une réponse Stack Overflow en solution"""
        try:
            body = answer.get("body", "")
            if not body:
                return None

            # Extraire le code de la réponse
            code_blocks = self._extract_code_blocks(body, language)
            if not code_blocks:
                return None

            # Prendre le bloc de code le plus long
            main_code = max(code_blocks, key=len)

            # Extraire l'explication (texte hors code)
            explanation = self._extract_explanation(body)

            # Calculer la note basée sur le score et l'acceptation
            rating = self._calculate_rating(answer)

            # Déterminer la complexité
            complexity = self._determine_complexity(main_code)

            # Extraire les tags/mots-clés
            tags = self._extract_tags_from_code(main_code, language)

            return CodeSolution(
                code=main_code,
                language=language,
                explanation=explanation,
                source=f"Stack Overflow (Score: {answer.get('score', 0)})",
                rating=rating,
                complexity=complexity,
                tags=tags,
                examples=[main_code],  # Le code lui-même comme exemple
            )

        except Exception as e:
            print(f"Erreur parsing réponse: {e}")
            return None

    def _extract_code_blocks(self, html_body: str, language: str) -> List[str]:
        """Extrait les blocs de code du HTML"""
        soup = BeautifulSoup(html_body, "html.parser")
        code_blocks = []

        # Rechercher les balises <code> et <pre>
        for code_tag in soup.find_all(["code", "pre"]):
            code_text = code_tag.get_text().strip()

            # Filtrer le code pertinent pour le langage
            if self._is_relevant_code(code_text, language):
                code_blocks.append(code_text)

        return code_blocks

    def _is_relevant_code(self, code: str, language: str) -> bool:
        """Vérifie si le code est pertinent pour le langage"""
        if len(code) < 10:  # Trop court
            return False

        language_patterns = {
            "python": [
                r"def\s+\w+",
                r"import\s+\w+",
                r"class\s+\w+",
                r"if\s+__name__",
                r"\.py",
            ],
            "javascript": [
                r"function\s+\w+",
                r"var\s+\w+",
                r"let\s+\w+",
                r"const\s+\w+",
                r"=>",
                r"\.js",
            ],
            "java": [
                r"public\s+class",
                r"public\s+static",
                r"import\s+java",
                r"\.java",
            ],
            "c++": [r"#include", r"int\s+main", r"std::", r"namespace", r"\.cpp"],
            "html": [r"<html>", r"<div>", r"<script>", r"<!DOCTYPE"],
            "css": [r"\.\w+\s*{", r"#\w+\s*{", r":\s*\w+;"],
        }

        patterns = language_patterns.get(language.lower(), [])
        return any(re.search(pattern, code, re.IGNORECASE) for pattern in patterns)

    def _extract_explanation(self, html_body: str) -> str:
        """Extrait l'explication textuelle"""
        soup = BeautifulSoup(html_body, "html.parser")

        # Supprimer les blocs de code
        for code_tag in soup.find_all(["code", "pre"]):
            code_tag.decompose()

        # Récupérer le texte restant
        text = soup.get_text().strip()

        # Nettoyer et limiter
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        explanation = " ".join(lines[:5])  # Limiter à 5 lignes

        return (
            explanation[:500] if explanation else "Solution trouvée sur Stack Overflow"
        )

    def _calculate_rating(self, answer: Dict) -> float:
        """Calcule une note pour la solution"""
        score = answer.get("score", 0)
        is_accepted = answer.get("is_accepted", False)

        # Note de base sur le score
        rating = min(5.0, max(1.0, (score + 5) / 10 * 5))

        # Bonus si acceptée
        if is_accepted:
            rating = min(5.0, rating + 1.0)

        return round(rating, 1)

    def _determine_complexity(self, code: str) -> str:
        """Détermine la complexité du code"""
        lines = len(code.split("\n"))

        # Facteurs de complexité
        complexity_indicators = [
            ("class ", 2),
            ("def ", 1),
            ("function ", 1),
            ("for ", 1),
            ("while ", 1),
            ("if ", 0.5),
            ("try:", 1),
            ("except:", 1),
            ("async ", 2),
            ("import ", 0.5),
            ("from ", 0.5),
        ]

        complexity_score = 0
        for indicator, weight in complexity_indicators:
            complexity_score += code.count(indicator) * weight

        # Classification basée sur les lignes et la complexité
        if lines <= 10 and complexity_score <= 3:
            return "Débutant"
        elif lines <= 30 and complexity_score <= 8:
            return "Intermédiaire"
        else:
            return "Avancé"

    def _extract_tags_from_code(self, code: str, language: str) -> List[str]:
        """Extrait les tags/concepts du code"""
        tags = [language.lower()]

        # Patterns pour différents concepts
        concept_patterns = {
            "api": [r"requests\.", r"fetch\(", r"axios\.", r"urllib"],
            "database": [
                r"SELECT",
                r"INSERT",
                r"UPDATE",
                r"DELETE",
                r"sqlite3",
                r"mysql",
            ],
            "web": [r"<html>", r"<div>", r"@app\.route", r"app\.get"],
            "async": [r"async\s+def", r"await\s+", r"Promise"],
            "file-io": [r"open\(", r"read\(", r"write\(", r"with\s+open"],
            "algorithm": [r"sort\(", r"sorted\(", r"\.sort", r"binary_search"],
            "class": [r"class\s+\w+", r"def\s+__init__"],
            "function": [r"def\s+\w+", r"function\s+\w+"],
        }

        for tag, patterns in concept_patterns.items():
            if any(re.search(pattern, code, re.IGNORECASE) for pattern in patterns):
                tags.append(tag)

        return tags[:5]  # Limiter à 5 tags

    async def _search_via_web_scraping(
        self, search_terms: str, language: str
    ) -> Tuple[List[CodeSolution], List[str]]:
        """Recherche par scraping web de Stack Overflow avec debug"""
        solutions = []
        debug = []
        try:
            async with aiohttp.ClientSession(headers=self.headers) as session:
                search_url = f"https://stackoverflow.com/search?q={quote(search_terms + ' ' + language)}"
                async with session.get(search_url) as response:
                    debug.append(f"[DEBUG][SO][SCRAPE] Status: {response.status}")
                    if response.status == 200:
                        html = await response.text()
                        soup = BeautifulSoup(html, "html.parser")
                        question_links = []
                        for link in soup.find_all("a", {"class": "s-link"}):
                            href = link.get("href")
                            if href and "/questions/" in href:
                                full_url = urljoin("https://stackoverflow.com", href)
                                question_links.append(full_url)
                        debug.append(
                            f"[DEBUG][SO][SCRAPE] Questions URLs: {question_links[:5]}"
                        )
                        for url in question_links[:5]:
                            debug.append(f"[DEBUG][SO][SCRAPE] Scraping URL: {url}")
                            question_solutions = await self._scrape_question_page(
                                session, url, language
                            )
                            solutions.extend(question_solutions)
                            if len(solutions) >= 5:
                                break
        except Exception as e:
            debug.append(f"[DEBUG][SO][SCRAPE] Erreur: {e}")
        return solutions, debug

    async def _scrape_question_page(
        self, session: aiohttp.ClientSession, url: str, language: str
    ) -> List[CodeSolution]:
        """Scrape une page de question Stack Overflow"""
        solutions = []

        try:
            async with session.get(url) as response:
                if response.status == 200:
                    html = await response.text()
                    soup = BeautifulSoup(html, "html.parser")

                    # Trouver les réponses
                    answers = soup.find_all("div", {"class": "answer"})

                    for answer in answers[:3]:  # Limiter à 3 réponses par question
                        # Extraire le score
                        score_elem = answer.find("span", {"class": "vote-count-post"})
                        score = int(score_elem.text) if score_elem else 0

                        # Vérifier si acceptée
                        is_accepted = bool(
                            answer.find("div", {"class": "accepted-answer"})
                        )

                        # Extraire le contenu
                        content = answer.find("div", {"class": "s-prose"})
                        if content:
                            code_blocks = self._extract_code_blocks(
                                str(content), language
                            )
                            if code_blocks:
                                main_code = max(code_blocks, key=len)
                                explanation = self._extract_explanation(str(content))

                                rating = min(5.0, max(1.0, (score + 5) / 10 * 5))
                                if is_accepted:
                                    rating = min(5.0, rating + 1.0)

                                solution = CodeSolution(
                                    code=main_code,
                                    language=language,
                                    explanation=explanation,
                                    source=f"Stack Overflow (Score: {score})",
                                    rating=round(rating, 1),
                                    complexity=self._determine_complexity(main_code),
                                    tags=self._extract_tags_from_code(
                                        main_code, language
                                    ),
                                    examples=[main_code],
                                )
                                solutions.append(solution)

        except Exception as e:
            print(f"Erreur scraping question: {e}")

        return solutions

    def _filter_and_rank_solutions(
        self, solutions: List[CodeSolution], request: CodeRequest
    ) -> List[CodeSolution]:
        """Filtre et classe les solutions par pertinence"""
        if not solutions:
            return []

        # Scoring basé sur plusieurs critères
        scored_solutions = []

        for solution in solutions:
            score = 0

            # Score de base (rating existant)
            score += solution.rating * 2

            # Bonus pour longueur appropriée du code
            code_length = len(solution.code)
            if 50 <= code_length <= 500:  # Longueur idéale
                score += 3
            elif code_length <= 50:  # Trop court
                score += 1
            else:  # Peut être trop long
                score += 2

            # Bonus pour correspondance de complexité
            if request.complexity.lower() == solution.complexity.lower():
                score += 2

            # Bonus pour tags correspondants
            matching_tags = set(solution.tags) & set(request.requirements)
            score += len(matching_tags) * 1.5

            # Bonus pour présence de mots-clés de la demande
            request_words = set(request.description.lower().split())
            code_words = set(solution.code.lower().split())
            matching_words = request_words & code_words
            score += len(matching_words) * 0.5

            scored_solutions.append((score, solution))

        # Trier par score décroissant
        scored_solutions.sort(key=lambda x: x[0], reverse=True)

        # Retourner les meilleures solutions (max 5)
        return [solution for score, solution in scored_solutions[:5]]

    def _get_cached_solution(self, query_hash: str) -> Optional[CodeSolution]:
        """Récupère une solution du cache"""
        try:
            with sqlite3.connect(self.cache_db) as conn:
                cursor = conn.execute(
                    "SELECT solution_json FROM code_solutions WHERE query_hash = ? AND created_at > datetime('now', '-7 days')",
                    (query_hash,),
                )
                row = cursor.fetchone()

                if row:
                    solution_data = json.loads(row[0])
                    return CodeSolution(**solution_data)

        except Exception as e:
            print(f"Erreur lecture cache: {e}")

        return None

    def _cache_solution(
        self, query_hash: str, query: str, language: str, solution: CodeSolution
    ):
        """Met en cache une solution"""
        try:
            solution_json = json.dumps(
                {
                    "code": solution.code,
                    "language": solution.language,
                    "explanation": solution.explanation,
                    "source": solution.source,
                    "rating": solution.rating,
                    "complexity": solution.complexity,
                    "tags": solution.tags,
                    "examples": solution.examples,
                }
            )

            with sqlite3.connect(self.cache_db) as conn:
                conn.execute(
                    """INSERT OR REPLACE INTO code_solutions 
                       (query_hash, query, language, solution_json, rating, source) 
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (
                        query_hash,
                        query,
                        language,
                        solution_json,
                        solution.rating,
                        solution.source,
                    ),
                )

        except Exception as e:
            print(f"Erreur mise en cache: {e}")


class GitHubCodeSearcher:
    """Recherche de code sur GitHub"""

    def __init__(self):
        self.base_url = "https://api.github.com"
        self.headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "AI-Code-Generator/1.0",
        }
        # Charger le token GitHub depuis config.yaml
        config_path = Path(__file__).parent.parent / "config.yaml"
        if config_path.exists():
            with open(config_path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)
            token = None
            # Cherche la clé dans github: token
            if "github" in config and "token" in config["github"]:
                token = config["github"]["token"]
                # Si le token est une variable d'environnement, charge la vraie valeur
                if isinstance(token, str) and token.strip() == "${GITHUB_TOKEN}":
                    env_token = os.environ.get("GITHUB_TOKEN")
                    if env_token:
                        token = env_token
            if token:
                self.headers["Authorization"] = f"token {token}"

    def _build_search_terms(self, request):
        """Construit des termes de recherche optimisés pour GitHub"""
        description = request.description.lower()

        # Traduction français -> anglais
        translations = {
            "tic tac toe": "tic tac toe",
            "morpion": "tic tac toe",
            "jeu": "game",
            "jouer": "game",
            "génère": "create",
            "programme": "program",
            "fonction": "function",
            "calculer": "calculate",
            "trier": "sort",
            "chercher": "search",
            "inverser": "reverse",
        }

        # Construire la requête en anglais
        english_terms = []

        # Détecter les concepts spécifiques
        if "tic tac toe" in description or "morpion" in description:
            english_terms = ["tic", "tac", "toe", "python", "game"]
        elif "jeu" in description:
            english_terms = ["game", "python"]
        else:
            # Traduire terme par terme
            for fr_word, en_word in translations.items():
                if fr_word in description:
                    english_terms.append(en_word)

        # Ajouter le langage si pas déjà présent
        if request.language.lower() not in english_terms:
            english_terms.append(request.language.lower())

        # Limiter à 4-5 termes pour éviter les requêtes trop complexes
        final_query = " ".join(english_terms[:5])

        return final_query

    def _determine_github_complexity(self, code: str) -> str:
        """Détermine la complexité d'un code GitHub"""
        lines = len(code.split("\n"))
        if lines <= 20:
            return "Débutant"
        if lines <= 100:
            return "Intermédiaire"
        return "Avancé"

    async def search_github_repositories(
        self, request: CodeRequest, debug_info: list = None
    ) -> List[CodeSolution]:
        """Recherche dans les repositories GitHub"""
        solutions = []
        if debug_info is None:
            debug_info = []
        try:
            async with aiohttp.ClientSession(headers=self.headers) as session:
                # Utiliser les termes optimisés au lieu de la description brute
                search_terms = self._build_search_terms(request)
                search_query = f"{search_terms} language:{request.language}"
                params = {
                    "q": search_query,
                    "sort": "stars",
                    "order": "desc",
                    "per_page": 15,  # Augmenter pour plus de choix
                }
                debug_info.append(f"[DEBUG][GH] Search query: {search_query}")
                async with session.get(
                    f"{self.base_url}/search/code", params=params
                ) as response:
                    debug_info.append(f"[DEBUG][GH] Status: {response.status}")
                    if response.status == 401:
                        debug_info.append(
                            "[DEBUG][GH] Token d'autorisation manquant ou invalide"
                        )
                        # Essayer sans token (recherche publique limitée)
                        self.headers.pop("Authorization", None)
                        async with session.get(
                            f"{self.base_url}/search/repositories",
                            params={
                                "q": search_query,
                                "sort": "stars",
                                "order": "desc",
                                "per_page": 5,
                            },
                        ) as fallback_response:
                            debug_info.append(
                                f"[DEBUG][GH] Fallback status: {fallback_response.status}"
                            )
                            if fallback_response.status == 200:
                                data = await fallback_response.json()
                                debug_info.append(
                                    f"[DEBUG][GH] Repositories trouvés: {len(data.get('items', []))}"
                                )
                                # Pour chaque repo, essayer de trouver des fichiers pertinents
                                for repo in data.get("items", [])[
                                    :3
                                ]:  # Limiter à 3 repos
                                    repo_name = repo.get("full_name", "")
                                    debug_info.append(f"[DEBUG][GH] Repo: {repo_name}")
                                    # Simuler une solution basée sur le repo (sans contenu de fichier)
                                    if any(
                                        term in repo_name.lower()
                                        for term in ["tic", "tac", "toe", "game"]
                                    ):
                                        solution = CodeSolution(
                                            code=f"# Code inspiré du repository: {repo_name}\n# Implémenter tic tac toe game",
                                            language=request.language,
                                            explanation=f"Code basé sur le repository GitHub: {repo_name}",
                                            source=f"GitHub Repository - {repo_name}",
                                            rating=3.5,
                                            complexity="Intermédiaire",
                                            tags=[
                                                request.language,
                                                "github",
                                                "repository",
                                            ],
                                            examples=[],
                                        )
                                        solutions.append(solution)
                        return solutions
                    elif response.status == 200:
                        data = await response.json()
                        debug_info.append(
                            f"[DEBUG][GH] Items trouvés: {len(data.get('items', []))}"
                        )
                        for item in data.get("items", []):
                            debug_info.append(
                                f"[DEBUG][GH] Processing item: {item.get('name', 'Unknown')}"
                            )
                            content_url = item.get("url", "")
                            debug_info.append(f"[DEBUG][GH] Content URL: {content_url}")
                            file_content = await self._get_file_content(
                                session, content_url, request, debug_info
                            )
                            debug_info.append(
                                f"[DEBUG][GH] File content length: {len(file_content) if file_content else 0}"
                            )
                            if file_content:
                                debug_info.append(
                                    f"[DEBUG][GH] File content preview: {file_content[:100]}..."
                                )

                                # Analyser la pertinence du code
                                relevance_score = self._calculate_code_relevance(
                                    file_content, request
                                )
                                debug_info.append(
                                    f"[DEBUG][GH] Relevance score: {relevance_score}"
                                )

                                # Ne garder que les codes très pertinents ou courts
                                if relevance_score >= 3 or len(file_content) <= 500:
                                    solution = CodeSolution(
                                        code=file_content,
                                        language=request.language,
                                        explanation=f"Code extrait du repository: {item.get('repository', {}).get('full_name', 'GitHub')}",
                                        source=f"GitHub - {item.get('repository', {}).get('full_name', 'Unknown')}",
                                        rating=min(5.0, relevance_score),
                                        complexity=self._determine_github_complexity(
                                            file_content
                                        ),
                                        tags=[request.language, "github"],
                                        examples=[file_content[:200] + "..."],
                                    )
                                    solutions.append(solution)
                                    debug_info.append(
                                        f"[DEBUG][GH] Solution added, total: {len(solutions)}"
                                    )
                                    if len(solutions) >= 5:
                                        break
                                else:
                                    debug_info.append(
                                        f"[DEBUG][GH] Code rejected (low relevance: {relevance_score})"
                                    )
        except Exception as e:
            debug_info.append(f"[DEBUG][GH] Erreur recherche GitHub: {e}")
        return solutions

    async def _get_file_content(
        self,
        session: aiohttp.ClientSession,
        content_url: str,
        request: CodeRequest = None,
        debug_info: list = None,
    ) -> str:
        """Récupère le contenu d'un fichier depuis l'API GitHub"""
        if debug_info is None:
            debug_info = []
        try:
            if content_url:
                async with session.get(content_url) as response:
                    debug_info.append(
                        f"[DEBUG][GH] Content API status: {response.status} for {content_url}"
                    )
                    if response.status == 200:
                        data = await response.json()
                        # GitHub API returns content as base64 encoded
                        content = data.get("content", "").replace("\n", "")
                        if content:
                            decoded_content = base64.b64decode(content).decode(
                                "utf-8", errors="ignore"
                            )
                            # Extraire le code pertinent
                            return self._extract_relevant_code(
                                decoded_content, request, debug_info
                            )
                        return ""
            return ""
        except Exception as e:
            debug_info.append(f"[ERROR][GH] Exception: {e}")
            return ""

    def _extract_relevant_code(
        self, full_content: str, request: CodeRequest = None, debug_info: list = None
    ) -> str:
        """Extrait le code pertinent du fichier complet"""
        if debug_info is None:
            debug_info = []

        lines = full_content.split("\n")
        debug_info.append(f"[DEBUG][GH] Total lines in file: {len(lines)}")

        # Patterns pour identifier les blocs de code importants
        function_pattern = re.compile(r"^(def\s+\w+\s*\([^)]*\)\s*:)", re.MULTILINE)
        class_pattern = re.compile(r"^(class\s+\w+.*?:)", re.MULTILINE)
        import_pattern = re.compile(r"^(import\s+.*|from\s+.*import.*)$", re.MULTILINE)

        # Extraire les imports (généralement au début)
        imports = []
        for line in lines[:20]:  # Regarder les 20 premières lignes pour les imports
            if import_pattern.match(line.strip()):
                imports.append(line.strip())

        # Chercher les fonctions et classes
        functions = []
        classes = []

        # Analyser la requête pour les mots-clés
        request_keywords = []
        if request:
            # Mots-clés liés à l'inversion/reverse et aux chaînes
            reverse_keywords = [
                "reverse",
                "inverse",
                "invert",
                "renvers",
                "sens inverse",
                "retourne",
                "chaine",
                "string",
                "caractere",
                "character",
                "str",
                "[::-1]",
                "reversed(",
                ".reverse(",
                "slice",
                "retourner",
                "inverser",
                "renverser",
                "backwards",
            ]
            # Ajouter aussi les mots de la requête elle-même
            request_words = request.description.lower().split()
            request_keywords = reverse_keywords + request_words

        i = 0
        while i < len(lines):
            line = lines[i].strip()

            # Détecter le début d'une fonction
            if function_pattern.match(line):
                debug_info.append(f"[DEBUG][GH] Found function: {line}")
                func_lines = [line]
                i += 1
                indent_level = (
                    len(lines[i - 1]) - len(lines[i - 1].lstrip())
                    if i < len(lines)
                    else 0
                )

                # Collecter le corps de la fonction
                while i < len(lines):
                    current_line = lines[i]
                    current_indent = len(current_line) - len(current_line.lstrip())

                    # Si on revient au niveau d'indentation précédent ou moins, fin de la fonction
                    if (
                        current_line.strip()
                        and current_indent <= indent_level
                        and not current_line.startswith(" ")
                    ):
                        break

                    func_lines.append(current_line)
                    i += 1

                    # Limiter la taille d'une fonction
                    if len(func_lines) > 50:  # Max 50 lignes par fonction
                        break

                func_code = "\n".join(func_lines)

                # Prioriser les fonctions courtes et pertinentes
                func_lower = func_code.lower()
                priority_score = 0

                # Bonus pour les fonctions qui contiennent des mots-clés de la requête
                if request_keywords:
                    for keyword in request_keywords:
                        if keyword in func_lower:
                            priority_score += 3  # Augmenté pour mieux prioriser

                # Bonus pour les fonctions avec "return"
                if "return" in func_lower:
                    priority_score += 2

                # Bonus pour les fonctions courtes
                if len(func_lines) <= 15:
                    priority_score += 3
                elif len(func_lines) <= 30:
                    priority_score += 1

                functions.append((priority_score, func_code))
                continue

            # Détecter le début d'une classe
            elif class_pattern.match(line):
                debug_info.append(f"[DEBUG][GH] Found class: {line}")
                class_lines = [line]
                i += 1
                indent_level = (
                    len(lines[i - 1]) - len(lines[i - 1].lstrip())
                    if i < len(lines)
                    else 0
                )

                # Collecter le corps de la classe
                while i < len(lines):
                    current_line = lines[i]
                    current_indent = len(current_line) - len(current_line.lstrip())

                    # Si on revient au niveau d'indentation précédent ou moins, fin de la classe
                    if (
                        current_line.strip()
                        and current_indent <= indent_level
                        and not current_line.startswith(" ")
                    ):
                        break

                    class_lines.append(current_line)
                    i += 1

                    # Limiter la taille d'une classe
                    if len(class_lines) > 100:  # Max 100 lignes par classe
                        break

                classes.append("\n".join(class_lines))
                continue

            i += 1

        debug_info.append(
            f"[DEBUG][GH] Found {len(functions)} functions and {len(classes)} classes"
        )

        # Construire le code final
        final_code = []

        # Ajouter les imports si pertinents
        if imports and len(imports) <= 10:  # Max 10 imports
            final_code.extend(imports)
            final_code.append("")  # Ligne vide

        # Trier les fonctions par score de priorité et prendre les meilleures
        if functions:
            functions.sort(
                key=lambda x: x[0], reverse=True
            )  # Trier par priorité décroissante
            selected_functions = [
                func for score, func in functions[:3]
            ]  # Prendre les 3 meilleures
            final_code.extend(selected_functions)

        # Ajouter les classes si pas de fonctions
        elif classes:
            # Prendre la classe la plus courte
            classes.sort(key=len)
            final_code.append(classes[0])

        # Si rien trouvé, prendre un extrait du fichier original
        if not final_code:
            debug_info.append(
                "[DEBUG][GH] No specific functions/classes found, using file excerpt"
            )
            # Prendre les premières lignes non vides
            non_empty_lines = [line for line in lines if line.strip()]
            excerpt = "\n".join(non_empty_lines[:30])  # Max 30 lignes
            final_code.append(excerpt)

        result = "\n".join(final_code)
        debug_info.append(f"[DEBUG][GH] Final extracted code length: {len(result)}")

        return result

    def _calculate_code_relevance(self, code: str, request: CodeRequest) -> float:
        """Calcule la pertinence du code par rapport à la requête"""
        score = 0.0

        # Convertir en minuscules pour la recherche
        code_lower = code.lower()
        description_lower = request.description.lower()

        # Mots-clés de la requête présents dans le code
        request_words = set(description_lower.split())
        code_words = set(code_lower.split())
        matching_words = request_words & code_words

        # Bonus pour les mots exacts
        score += len(matching_words) * 2.0

        # Recherche de patterns spécifiques selon le langage
        if request.language.lower() == "python":
            # Pour Python, chercher des patterns spécifiques
            patterns = {
                "function": [r"def\s+\w+\s*\(", r"return\s+"],
                "class": [r"class\s+\w+", r"def\s+__init__"],
                "string": [
                    r"\'[^\']*\'",
                    r'"[^"]*"',
                    r"\.split\(",
                    r"\.join\(",
                    r"\.replace\(",
                ],
                "list": [r"\[.*\]", r"\.append\(", r"\.extend\(", r"for\s+\w+\s+in"],
                "dict": [r"\{.*\}", r"\.keys\(\)", r"\.values\(\)", r"\.items\(\)"],
                "file": [r"open\(", r"with\s+open", r"\.read\(", r"\.write\("],
                "math": [r"\+", r"-", r"\*", r"/", r"sum\(", r"len\("],
                "reverse": [r"\[::?-1\]", r"reversed\(", r"\.reverse\("],
            }

            # Chercher les patterns correspondant à la requête
            for category, category_patterns in patterns.items():
                if category in description_lower:
                    for pattern in category_patterns:
                        if re.search(pattern, code, re.IGNORECASE):
                            score += 1.5
                            break

            # Bonus pour les fonctions courtes (préférées)
            lines = len(code.split("\n"))
            if lines <= 20:
                score += 2.0
            elif lines <= 50:
                score += 1.0

            # Pénalité pour les codes trop longs
            if lines > 100:
                score -= 1.0

        # Bonus pour la présence d'exemples/docstrings
        if '"""' in code or "'''" in code:
            score += 0.5

        # Pénalité pour les codes avec trop d'imports complexes
        complex_imports = [
            "django",
            "flask",
            "tensorflow",
            "pytorch",
            "numpy",
            "pandas",
        ]
        for imp in complex_imports:
            if f"import {imp}" in code_lower or f"from {imp}" in code_lower:
                score -= 0.5

        return max(0.0, min(5.0, score))
