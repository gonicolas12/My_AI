"""
Générateur de Code Avancé - Version Corrigée
Résout les problèmes de génération de code non pertinent
"""

import re
import json
import asyncio
import aiohttp
import sqlite3
import hashlib
import time
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
from urllib.parse import quote

# Intégration avec l'ancien système
try:
    from .advanced_code_generator import AdvancedCodeGenerator, CodeRequest, CodeSolution
    LEGACY_AVAILABLE = True
except ImportError:
    LEGACY_AVAILABLE = False

@dataclass
class EnhancedCodeRequest:
    """Requête de code enrichie avec analyse d'intention"""
    description: str
    language: str
    intent: str
    keywords: List[str]
    algorithm_type: str
    complexity: str
    expected_inputs: List[str]
    expected_outputs: List[str]

class EnhancedCodeGenerator:
    """
    Générateur de code avancé avec validation de pertinence
    """

    def __init__(self):
        self.cache_db = self._init_cache_db()
        self.algorithm_templates = self._load_algorithm_templates()
        self.intent_analyzer = IntentAnalyzer()
        self.relevance_validator = RelevanceValidator()

        # Intégration avec l'ancien système
        if LEGACY_AVAILABLE:
            self.legacy_generator = AdvancedCodeGenerator()
        else:
            self.legacy_generator = None

    def _init_cache_db(self) -> sqlite3.Connection:
        """Initialise le cache SQLite pour les solutions"""
        db_path = Path(__file__).parent.parent / "code_solutions_cache.db"
        conn = sqlite3.connect(str(db_path))

        conn.execute("""
            CREATE TABLE IF NOT EXISTS code_solutions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                request_hash TEXT UNIQUE,
                description TEXT,
                language TEXT,
                intent TEXT,
                code TEXT,
                explanation TEXT,
                rating REAL,
                source TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        return conn

    def _load_algorithm_templates(self) -> Dict[str, Dict[str, str]]:
        """Charge les templates d'algorithmes spécialisés"""
        return {
            "sorting": {
                "alphabetical_sort": {
                    "python": '''def sort_alphabetically(items):
    """
    Trie une liste par ordre alphabétique

    Args:
        items (list): Liste d'éléments à trier

    Returns:
        list: Liste triée par ordre alphabétique
    """
    if not items:
        return []

    # Conversion en chaînes et tri alphabétique
    str_items = [str(item) for item in items]
    return sorted(str_items)

def sort_alphabetically_advanced(items, reverse=False, key_func=None):
    """
    Trie une liste par ordre alphabétique avec options avancées

    Args:
        items (list): Liste d'éléments à trier
        reverse (bool): Tri inverse si True
        key_func (function): Fonction pour extraire la clé de tri

    Returns:
        list: Liste triée
    """
    if not items:
        return []

    if key_func:
        return sorted(items, key=key_func, reverse=reverse)
    else:
        return sorted(items, reverse=reverse)

# Exemples d'utilisation
if __name__ == "__main__":
    # Test avec des chaînes
    names = ["Charlie", "Alice", "Bob", "David"]
    sorted_names = sort_alphabetically(names)
    print(f"Noms triés: {sorted_names}")

    # Test avec tri inverse
    sorted_reverse = sort_alphabetically_advanced(names, reverse=True)
    print(f"Tri inverse: {sorted_reverse}")

    # Test avec des objets complexes
    people = [
        {"name": "Charlie", "age": 30},
        {"name": "Alice", "age": 25},
        {"name": "Bob", "age": 35}
    ]
    sorted_people = sort_alphabetically_advanced(people, key_func=lambda x: x["name"])
    print(f"Personnes triées par nom: {sorted_people}")

    # Test avec tri insensible à la casse
    mixed_case = ["apple", "Banana", "cherry", "Date"]
    sorted_case_insensitive = sorted(mixed_case, key=str.lower)
    print(f"Tri insensible à la casse: {sorted_case_insensitive}")''',

                    "javascript": '''function sortAlphabetically(items) {
    /**
     * Trie un tableau par ordre alphabétique
     * @param {Array} items - Tableau d'éléments à trier
     * @returns {Array} Tableau trié par ordre alphabétique
     */
    if (!Array.isArray(items) || items.length === 0) {
        return [];
    }

    // Conversion en chaînes et tri alphabétique
    return items.map(item => String(item)).sort();
}

function sortAlphabeticallyAdvanced(items, options = {}) {
    /**
     * Trie un tableau par ordre alphabétique avec options avancées
     * @param {Array} items - Tableau d'éléments à trier
     * @param {Object} options - Options de tri
     * @param {boolean} options.reverse - Tri inverse si true
     * @param {Function} options.keyFunc - Fonction pour extraire la clé
     * @param {boolean} options.caseInsensitive - Ignore la casse si true
     * @returns {Array} Tableau trié
     */
    if (!Array.isArray(items) || items.length === 0) {
        return [];
    }

    const { reverse = false, keyFunc, caseInsensitive = false } = options;

    let sortedItems = [...items];

    if (keyFunc) {
        sortedItems.sort((a, b) => {
            const keyA = keyFunc(a);
            const keyB = keyFunc(b);
            return caseInsensitive ?
                String(keyA).toLowerCase().localeCompare(String(keyB).toLowerCase()) :
                String(keyA).localeCompare(String(keyB));
        });
    } else {
        sortedItems.sort((a, b) => {
            return caseInsensitive ?
                String(a).toLowerCase().localeCompare(String(b).toLowerCase()) :
                String(a).localeCompare(String(b));
        });
    }

    return reverse ? sortedItems.reverse() : sortedItems;
}

// Exemples d'utilisation
if (typeof module !== 'undefined') {
    // Test avec des chaînes
    const names = ["Charlie", "Alice", "Bob", "David"];
    const sortedNames = sortAlphabetically(names);
    console.log("Noms triés:", sortedNames);

    // Test avec tri inverse
    const sortedReverse = sortAlphabeticallyAdvanced(names, { reverse: true });
    console.log("Tri inverse:", sortedReverse);

    // Test avec des objets complexes
    const people = [
        { name: "Charlie", age: 30 },
        { name: "Alice", age: 25 },
        { name: "Bob", age: 35 }
    ];
    const sortedPeople = sortAlphabeticallyAdvanced(people, {
        keyFunc: person => person.name
    });
    console.log("Personnes triées par nom:", sortedPeople);

    // Test avec tri insensible à la casse
    const mixedCase = ["apple", "Banana", "cherry", "Date"];
    const sortedCaseInsensitive = sortAlphabeticallyAdvanced(mixedCase, {
        caseInsensitive: true
    });
    console.log("Tri insensible à la casse:", sortedCaseInsensitive);
}'''
                },

                "numeric_sort": {
                    "python": '''def sort_numerically(numbers):
    """
    Trie une liste de nombres par ordre croissant

    Args:
        numbers (list): Liste de nombres à trier

    Returns:
        list: Liste triée numériquement
    """
    if not numbers:
        return []

    # Conversion en nombres et tri
    numeric_values = []
    for item in numbers:
        try:
            numeric_values.append(float(item))
        except (ValueError, TypeError):
            numeric_values.append(0)  # Valeur par défaut pour les non-nombres

    return sorted(numeric_values)

# Exemple d'utilisation
if __name__ == "__main__":
    numbers = [3, 1, 4, 1, 5, 9, 2, 6]
    sorted_numbers = sort_numerically(numbers)
    print(f"Nombres triés: {sorted_numbers}")'''
                }
            },

            "string_manipulation": {
                "case_conversion": {
                    "python": '''def convert_case(text, case_type="lower"):
    """
    Convertit la casse d'un texte

    Args:
        text (str): Texte à convertir
        case_type (str): Type de conversion ('lower', 'upper', 'title', 'capitalize')

    Returns:
        str: Texte avec la casse convertie
    """
    if not isinstance(text, str):
        text = str(text)

    case_type = case_type.lower()

    if case_type == "lower":
        return text.lower()
    elif case_type == "upper":
        return text.upper()
    elif case_type == "title":
        return text.title()
    elif case_type == "capitalize":
        return text.capitalize()
    else:
        return text

# Exemple d'utilisation
if __name__ == "__main__":
    text = "Hello World!"
    print(f"Minuscules: {convert_case(text, 'lower')}")
    print(f"Majuscules: {convert_case(text, 'upper')}")
    print(f"Titre: {convert_case(text, 'title')}")'''
                }
            },

            "data_structures": {
                "list_operations": {
                    "python": '''def filter_and_sort_list(items, filter_func=None, sort_key=None, reverse=False):
    """
    Filtre et trie une liste selon des critères

    Args:
        items (list): Liste d'éléments
        filter_func (function): Fonction de filtrage (optionnel)
        sort_key (function): Fonction de tri (optionnel)
        reverse (bool): Tri inverse si True

    Returns:
        list: Liste filtrée et triée
    """
    if not items:
        return []

    # Filtrage
    if filter_func:
        filtered_items = [item for item in items if filter_func(item)]
    else:
        filtered_items = list(items)

    # Tri
    if sort_key:
        return sorted(filtered_items, key=sort_key, reverse=reverse)
    else:
        return sorted(filtered_items, reverse=reverse)

# Exemple d'utilisation
if __name__ == "__main__":
    numbers = [3, 1, 4, 1, 5, 9, 2, 6, 5, 3, 5]

    # Filtrer les nombres > 3 et trier
    result = filter_and_sort_list(
        numbers,
        filter_func=lambda x: x > 3,
        reverse=False
    )
    print(f"Nombres > 3 triés: {result}")'''
                }
            }
        }

    async def generate_code(self, description: str, language: str = "python") -> Dict[str, Any]:
        """
        Génère du code basé sur une description avec validation de pertinence
        """
        try:
            # 1. Analyser l'intention de la requête
            enhanced_request = await self.intent_analyzer.analyze_request(description, language)

            # 2. Vérifier le cache
            cached_solution = self._get_cached_solution(enhanced_request)
            if cached_solution:
                return {
                    "success": True,
                    "code": cached_solution["code"],
                    "explanation": cached_solution["explanation"],
                    "source": f"Cache ({cached_solution['source']})",
                    "rating": cached_solution["rating"]
                }

            # 3. Chercher une solution spécialisée
            specialized_solution = await self._generate_specialized_solution(enhanced_request)
            if specialized_solution:
                # Valider la pertinence
                is_relevant = self.relevance_validator.validate_solution(
                    enhanced_request, specialized_solution
                )

                if is_relevant:
                    self._cache_solution(enhanced_request, specialized_solution)
                    return {
                        "success": True,
                        "code": specialized_solution["code"],
                        "explanation": specialized_solution["explanation"],
                        "source": "Template spécialisé",
                        "rating": specialized_solution["rating"]
                    }

            # 4. Fallback sur l'ancien système si disponible
            if self.legacy_generator:
                try:
                    legacy_request = CodeRequest(
                        description=description,
                        language=language,
                        complexity="Intermédiaire",
                        requirements=[],
                        context={}
                    )
                    legacy_result = await self.legacy_generator.generate_code(
                        description, language
                    )

                    if legacy_result.get("success"):
                        return legacy_result

                except Exception as e:
                    print(f"[WARNING] Erreur générateur legacy: {e}")

            # 5. Génération de base si tout échoue
            return self._generate_basic_fallback(enhanced_request)

        except Exception as e:
            return {
                "success": False,
                "error": f"Erreur génération code: {str(e)}",
                "code": "# Erreur lors de la génération",
                "source": "Erreur"
            }

    async def _generate_specialized_solution(self, request: EnhancedCodeRequest) -> Optional[Dict[str, Any]]:
        """Génère une solution spécialisée basée sur l'intention"""

        # Recherche dans les templates d'algorithmes
        algorithm_type = request.algorithm_type
        intent = request.intent
        language = request.language.lower()

        # Mapping intention -> template
        template_mapping = {
            "sort_alphabetical": ("sorting", "alphabetical_sort"),
            "sort_numeric": ("sorting", "numeric_sort"),
            "convert_case": ("string_manipulation", "case_conversion"),
            "filter_sort": ("data_structures", "list_operations")
        }

        if intent in template_mapping:
            category, template_name = template_mapping[intent]

            if (category in self.algorithm_templates and
                template_name in self.algorithm_templates[category] and
                language in self.algorithm_templates[category][template_name]):

                code = self.algorithm_templates[category][template_name][language]

                return {
                    "code": code,
                    "explanation": f"Solution spécialisée pour {request.description}",
                    "rating": 4.5,
                    "source": "Template spécialisé"
                }

        return None

    def _generate_basic_fallback(self, request: EnhancedCodeRequest) -> Dict[str, Any]:
        """Génère une solution de base"""

        if request.language.lower() == "python":
            if "tri" in request.description.lower() or "sort" in request.description.lower():
                code = '''def sort_items(items):
    """
    Trie une liste d'éléments

    Args:
        items (list): Liste à trier

    Returns:
        list: Liste triée
    """
    if not items:
        return []

    return sorted(items)

# Exemple d'utilisation
if __name__ == "__main__":
    test_list = ["banana", "apple", "cherry"]
    sorted_list = sort_items(test_list)
    print(f"Liste triée: {sorted_list}")'''
            else:
                code = f'''def process_data(data):
    """
    {request.description}

    Args:
        data: Données à traiter

    Returns:
        Résultat du traitement
    """
    # Implémentation basée sur: {request.description}
    result = data
    return result

# Exemple d'utilisation
if __name__ == "__main__":
    example_data = "exemple"
    result = process_data(example_data)
    print(f"Résultat: {{result}}")'''
        else:
            code = f"// Code pour: {request.description}\n// TODO: Implémentation"

        return {
            "success": True,
            "code": code,
            "explanation": f"Solution de base pour: {request.description}",
            "source": "Fallback basique",
            "rating": 3.0
        }

    def _get_cached_solution(self, request: EnhancedCodeRequest) -> Optional[Dict[str, Any]]:
        """Récupère une solution du cache"""
        request_hash = self._hash_request(request)

        cursor = self.cache_db.execute(
            "SELECT code, explanation, rating, source FROM code_solutions WHERE request_hash = ?",
            (request_hash,)
        )
        result = cursor.fetchone()

        if result:
            return {
                "code": result[0],
                "explanation": result[1],
                "rating": result[2],
                "source": result[3]
            }
        return None

    def _cache_solution(self, request: EnhancedCodeRequest, solution: Dict[str, Any]):
        """Met en cache une solution"""
        request_hash = self._hash_request(request)

        self.cache_db.execute("""
            INSERT OR REPLACE INTO code_solutions
            (request_hash, description, language, intent, code, explanation, rating, source)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            request_hash,
            request.description,
            request.language,
            request.intent,
            solution["code"],
            solution["explanation"],
            solution["rating"],
            solution["source"]
        ))
        self.cache_db.commit()

    def _hash_request(self, request: EnhancedCodeRequest) -> str:
        """Génère un hash pour identifier une requête"""
        content = f"{request.description}|{request.language}|{request.intent}"
        return hashlib.md5(content.encode()).hexdigest()


class IntentAnalyzer:
    """Analyse l'intention d'une requête de code"""

    def __init__(self):
        self.intent_patterns = {
            "sort_alphabetical": [
                r"tri\w*\s+(?:par\s+)?ordre\s+alphabétique",
                r"sort\w*\s+alphabetical",
                r"tri\w*\s+(?:des?\s+)?(?:mots?|chaînes?|strings?)\s+(?:par\s+)?alphabet",
                r"classer\s+(?:par\s+)?ordre\s+alphabétique"
            ],
            "sort_numeric": [
                r"tri\w*\s+(?:par\s+)?ordre\s+(?:numérique|croissant|décroissant)",
                r"sort\w*\s+(?:numeric|ascending|descending)",
                r"tri\w*\s+(?:des?\s+)?nombres?"
            ],
            "convert_case": [
                r"convertir?\s+en\s+(?:majuscules?|minuscules?)",
                r"(?:upper|lower)case",
                r"changer\s+la\s+casse"
            ],
            "filter_sort": [
                r"filtr\w*\s+et\s+tri\w*",
                r"filter\s+and\s+sort"
            ]
        }

    async def analyze_request(self, description: str, language: str) -> EnhancedCodeRequest:
        """Analyse une requête et détermine l'intention"""
        description_lower = description.lower()

        # Détecter l'intention
        intent = "general"
        algorithm_type = "general"

        for intent_name, patterns in self.intent_patterns.items():
            for pattern in patterns:
                if re.search(pattern, description_lower):
                    intent = intent_name
                    if "sort" in intent_name:
                        algorithm_type = "sorting"
                    elif "convert" in intent_name:
                        algorithm_type = "string_manipulation"
                    elif "filter" in intent_name:
                        algorithm_type = "data_structures"
                    break
            if intent != "general":
                break

        # Extraire les mots-clés
        keywords = re.findall(r'\b\w+\b', description_lower)

        # Déterminer les entrées/sorties attendues
        expected_inputs = self._extract_expected_inputs(description)
        expected_outputs = self._extract_expected_outputs(description)

        return EnhancedCodeRequest(
            description=description,
            language=language,
            intent=intent,
            keywords=keywords,
            algorithm_type=algorithm_type,
            complexity="Intermédiaire",
            expected_inputs=expected_inputs,
            expected_outputs=expected_outputs
        )

    def _extract_expected_inputs(self, description: str) -> List[str]:
        """Extrait les types d'entrées attendues"""
        inputs = []
        description_lower = description.lower()

        if any(word in description_lower for word in ["liste", "list", "array", "tableau"]):
            inputs.append("list")
        if any(word in description_lower for word in ["chaîne", "string", "texte", "text"]):
            inputs.append("string")
        if any(word in description_lower for word in ["nombre", "number", "numérique", "numeric"]):
            inputs.append("number")

        return inputs if inputs else ["any"]

    def _extract_expected_outputs(self, description: str) -> List[str]:
        """Extrait les types de sorties attendues"""
        outputs = []
        description_lower = description.lower()

        if any(word in description_lower for word in ["tri", "sort", "classer"]):
            outputs.append("sorted_list")
        if any(word in description_lower for word in ["convertir", "convert", "transformer"]):
            outputs.append("converted_data")
        if any(word in description_lower for word in ["filtrer", "filter"]):
            outputs.append("filtered_data")

        return outputs if outputs else ["processed_data"]


class RelevanceValidator:
    """Valide la pertinence d'une solution de code"""

    def validate_solution(self, request: EnhancedCodeRequest, solution: Dict[str, Any]) -> bool:
        """Valide qu'une solution correspond à la requête"""
        code = solution["code"].lower()
        description = request.description.lower()

        # Validation spécifique par intention
        if request.intent == "sort_alphabetical":
            return self._validate_sort_alphabetical(code, description)
        elif request.intent == "sort_numeric":
            return self._validate_sort_numeric(code, description)
        elif request.intent == "convert_case":
            return self._validate_convert_case(code, description)
        else:
            return self._validate_general(code, description, request.keywords)

    def _validate_sort_alphabetical(self, code: str, description: str) -> bool:
        """Valide une solution de tri alphabétique"""
        required_indicators = ["sort", "alphabét", "ordre"]
        code_indicators = ["sorted(", ".sort(", "alphabetical", "ordre"]

        # Vérifier que la description concerne bien le tri alphabétique
        description_match = any(indicator in description for indicator in required_indicators)

        # Vérifier que le code contient des éléments de tri
        code_match = any(indicator in code for indicator in code_indicators)

        return description_match and code_match

    def _validate_sort_numeric(self, code: str, description: str) -> bool:
        """Valide une solution de tri numérique"""
        required_indicators = ["tri", "nombre", "numérique", "croissant", "décroissant"]
        code_indicators = ["sorted(", ".sort(", "numeric", "float", "int"]

        description_match = any(indicator in description for indicator in required_indicators)
        code_match = any(indicator in code for indicator in code_indicators)

        return description_match and code_match

    def _validate_convert_case(self, code: str, description: str) -> bool:
        """Valide une solution de conversion de casse"""
        required_indicators = ["convertir", "majuscule", "minuscule", "casse"]
        code_indicators = [".lower(", ".upper(", ".title(", ".capitalize(", "case"]

        description_match = any(indicator in description for indicator in required_indicators)
        code_match = any(indicator in code for indicator in code_indicators)

        return description_match and code_match

    def _validate_general(self, code: str, description: str, keywords: List[str]) -> bool:
        """Validation générale basée sur les mots-clés"""
        keyword_matches = 0

        for keyword in keywords[:5]:  # Vérifier les 5 premiers mots-clés
            if len(keyword) > 3 and keyword in code:
                keyword_matches += 1

        # Au moins 30% des mots-clés doivent être présents dans le code
        threshold = max(1, len(keywords[:5]) * 0.3)
        return keyword_matches >= threshold


# Instance globale pour compatibilité
enhanced_generator = EnhancedCodeGenerator()

async def generate_enhanced_code(description: str, language: str = "python") -> Dict[str, Any]:
    """Point d'entrée principal pour la génération de code améliorée"""
    return await enhanced_generator.generate_code(description, language)