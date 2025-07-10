"""
Base de connaissances étendue pour l'IA locale
"""

from typing import Dict, Any, List
import json
from pathlib import Path


class KnowledgeBase:
    """Gestionnaire de la base de connaissances"""
    
    def __init__(self, knowledge_base_path: str = "advanced_knowledge.json"):
        self.knowledge_base_path = knowledge_base_path
        self.knowledge = self._load_knowledge()
    
    def _load_knowledge(self) -> Dict[str, Any]:
        """Charge une base de connaissances ultra-étendue"""
        knowledge = {
            "programming": {
                "python": {
                    "basics": {
                        "variables": "Les variables stockent des données. En Python: nom = valeur",
                        "types": "str (texte), int (entier), float (décimal), bool (True/False), list, dict",
                        "control": "if/elif/else pour conditions, for/while pour boucles",
                        "functions": "def nom(paramètres): pour créer des fonctions réutilisables",
                        "classes": "class Nom: pour créer des objets avec attributs et méthodes",
                        "lists": "Collections ordonnées: [1, 2, 3], accès par index, modifiables",
                        "dictionaries": "Collections clé-valeur: {'nom': 'Jean'}, très efficaces",
                        "strings": "Texte entre quotes: 'Hello' ou \"World\", nombreuses méthodes",
                        "loops": "for pour itérer, while pour conditions, break/continue pour contrôle"
                    },
                    "advanced": {
                        "decorators": "Modifient le comportement des fonctions: @property, @staticmethod",
                        "generators": "yield pour créer des itérateurs économes en mémoire",
                        "context_managers": "with statement pour gérer les ressources",
                        "metaclasses": "Classes qui créent d'autres classes",
                        "async": "async/await pour la programmation asynchrone",
                        "lambdas": "Fonctions anonymes: lambda x: x*2, utiles avec map/filter",
                        "comprehensions": "Syntaxe concise: [x*2 for x in range(10) if x > 5]",
                        "exceptions": "try/except/finally pour gérer les erreurs proprement"
                    },
                    "libraries": {
                        "standard": ["os", "sys", "json", "re", "datetime", "pathlib", "collections"],
                        "data": ["pandas", "numpy", "matplotlib", "seaborn", "plotly"],
                        "web": ["requests", "flask", "django", "fastapi", "beautifulsoup"],
                        "gui": ["tkinter", "pygame", "kivy", "wxpython"]
                    }
                },
                "web_development": {
                    "frontend": {
                        "html": "Structure des pages web avec des éléments (tags)",
                        "css": "Style et mise en forme des pages web",
                        "javascript": "Interactivité côté client, manipulation du DOM",
                        "frameworks": ["React", "Vue.js", "Angular", "Svelte"],
                        "responsive": "Design adaptatif pour tous types d'écrans"
                    },
                    "backend": {
                        "servers": "Traitement des requêtes côté serveur",
                        "apis": "Interfaces pour communication entre services",
                        "databases": "Stockage persistant des données",
                        "authentication": "Sécurité et gestion des utilisateurs"
                    }
                }
            },
            "mathematics": {
                "arithmetic": {
                    "addition": "Opération qui combine deux nombres",
                    "multiplication": "Addition répétée d'un nombre",
                    "division": "Partage d'un nombre en parts égales",
                    "fractions": "Parties d'un tout: numérateur/dénominateur",
                    "percentages": "Parties sur 100: 50% = 50/100 = 0.5"
                },
                "algebra": {
                    "variables": "Lettres représentant des nombres inconnus",
                    "equations": "Égalités avec des inconnues à résoudre",
                    "functions": "Relations mathématiques: f(x) = 2x + 1",
                    "polynomials": "Expressions avec puissances: x² + 3x + 2"
                },
                "statistics": {
                    "mean": "Moyenne arithmétique: somme / nombre",
                    "median": "Valeur centrale d'une série ordonnée",
                    "mode": "Valeur la plus fréquente",
                    "std_dev": "Écart-type: mesure de dispersion"
                }
            },
            "computer_science": {
                "algorithms": {
                    "sorting": {
                        "bubble": "O(n²) - Compare et échange éléments adjacents",
                        "merge": "O(n log n) - Divise et conquiert",
                        "quick": "O(n log n) moyenne - Pivot et partitionnement"
                    },
                    "search": {
                        "linear": "O(n) - Vérifie chaque élément",
                        "binary": "O(log n) - Divise par 2 à chaque étape"
                    }
                },
                "data_structures": {
                    "array": "Collection d'éléments de même type, accès par index",
                    "linked_list": "Éléments chaînés par pointeurs",
                    "stack": "LIFO - Last In First Out",
                    "queue": "FIFO - First In First Out",
                    "tree": "Structure hiérarchique",
                    "graph": "Nœuds connectés par arêtes"
                }
            },
            "daily_life": {
                "productivity": {
                    "pomodoro": "25 min travail + 5 min pause",
                    "time_management": "Planification et priorisation",
                    "goal_setting": "Objectifs SMART: Spécifiques, Mesurables, Atteignables"
                },
                "communication": {
                    "active_listening": "Écouter avec attention et empathie",
                    "clear_expression": "Communiquer de manière claire et directe",
                    "feedback": "Donner et recevoir des retours constructifs"
                }
            }
        }
        
        # Essayer de charger depuis fichier si existant
        try:
            if Path(self.knowledge_base_path).exists():
                with open(self.knowledge_base_path, 'r', encoding='utf-8') as f:
                    loaded_kb = json.load(f)
                    knowledge.update(loaded_kb)
        except Exception:
            pass  # Utiliser la base par défaut
        
        return knowledge
    
    def search_knowledge(self, query: str, category: str = None) -> List[Dict[str, Any]]:
        """Recherche dans la base de connaissances"""
        results = []
        query_lower = query.lower()
        
        def search_recursive(data, path=""):
            if isinstance(data, dict):
                for key, value in data.items():
                    current_path = f"{path}.{key}" if path else key
                    
                    if isinstance(value, str):
                        if query_lower in key.lower() or query_lower in value.lower():
                            results.append({
                                "path": current_path,
                                "key": key,
                                "content": value,
                                "relevance": self._calculate_relevance(query_lower, key, value)
                            })
                    else:
                        search_recursive(value, current_path)
        
        search_data = self.knowledge[category] if category and category in self.knowledge else self.knowledge
        search_recursive(search_data)
        
        # Trier par pertinence
        results.sort(key=lambda x: x["relevance"], reverse=True)
        return results[:10]  # Retourner les 10 meilleurs résultats
    
    def _calculate_relevance(self, query: str, key: str, content: str) -> float:
        """Calcule la pertinence d'un résultat"""
        relevance = 0.0
        
        # Correspondance exacte dans la clé
        if query in key.lower():
            relevance += 2.0
        
        # Correspondance exacte dans le contenu
        if query in content.lower():
            relevance += 1.5
        
        # Correspondance partielle
        query_words = query.split()
        for word in query_words:
            if word in key.lower():
                relevance += 1.0
            if word in content.lower():
                relevance += 0.5
        
        return relevance
    
    def get_category_info(self, category: str) -> Dict[str, Any]:
        """Récupère les informations d'une catégorie"""
        return self.knowledge.get(category, {})
    
    def get_all_categories(self) -> List[str]:
        """Retourne toutes les catégories disponibles"""
        return list(self.knowledge.keys())
    
    def add_knowledge(self, category: str, key: str, value: str):
        """Ajoute une nouvelle connaissance"""
        if category not in self.knowledge:
            self.knowledge[category] = {}
        
        self.knowledge[category][key] = value
        self._save_knowledge()
    
    def _save_knowledge(self):
        """Sauvegarde la base de connaissances"""
        try:
            with open(self.knowledge_base_path, 'w', encoding='utf-8') as f:
                json.dump(self.knowledge, f, ensure_ascii=False, indent=2)
        except Exception:
            pass  # Échec silencieux
