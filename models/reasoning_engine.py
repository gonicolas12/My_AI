"""
Moteur de raisonnement pour l'IA locale
"""

from typing import Dict, List, Any, Optional
import re


class ReasoningEngine:
    """Moteur de raisonnement logique"""

    def __init__(self):
        self.reasoning_patterns = self._load_reasoning_patterns()
        self.problem_solving_strategies = self._load_problem_solving_strategies()

    def _load_reasoning_patterns(self) -> Dict[str, Any]:
        """Charge les patterns de raisonnement"""
        return {
            "logical_operators": {
                "and": ["et", "and", "aussi", "également", "en plus"],
                "or": ["ou", "or", "soit", "alternativement"],
                "not": ["pas", "non", "jamais", "aucun", "sans"],
                "if_then": ["si", "alors", "if", "then", "quand", "lorsque"],
                "because": ["parce que", "car", "because", "puisque", "étant donné"],
            },
            "question_types": {
                "what": ["quoi", "que", "qu'est-ce", "what"],
                "how": ["comment", "how", "de quelle manière"],
                "why": ["pourquoi", "why", "pour quelle raison"],
                "when": ["quand", "when", "à quel moment"],
                "where": ["où", "where", "à quel endroit"],
                "who": ["qui", "who", "quelle personne"],
            },
            "reasoning_chains": {
                "cause_effect": [
                    "cause",
                    "effet",
                    "conséquence",
                    "résultat",
                    "provoque",
                ],
                "comparison": [
                    "plus",
                    "moins",
                    "mieux",
                    "pire",
                    "similaire",
                    "différent",
                ],
                "sequence": ["d'abord", "ensuite", "puis", "enfin", "avant", "après"],
                "condition": ["si", "seulement si", "à condition que", "pourvu que"],
            },
        }

    def _load_problem_solving_strategies(self) -> Dict[str, Any]:
        """Charge les stratégies de résolution de problèmes"""
        return {
            "decomposition": {
                "description": "Diviser le problème en sous-problèmes",
                "steps": [
                    "Identifier le problème principal",
                    "Diviser en sous-problèmes",
                    "Résoudre chaque sous-problème",
                    "Combiner les solutions",
                ],
            },
            "analogy": {
                "description": "Utiliser des analogies pour comprendre",
                "steps": [
                    "Identifier un problème similaire connu",
                    "Comparer les structures",
                    "Adapter la solution connue",
                    "Vérifier la validité",
                ],
            },
            "trial_and_error": {
                "description": "Essayer différentes approches",
                "steps": [
                    "Générer des hypothèses",
                    "Tester chaque hypothèse",
                    "Évaluer les résultats",
                    "Raffiner l'approche",
                ],
            },
            "pattern_recognition": {
                "description": "Reconnaître des patterns",
                "steps": [
                    "Analyser les données",
                    "Identifier les répétitions",
                    "Extraire le pattern",
                    "Appliquer le pattern",
                ],
            },
        }

    def analyze_reasoning(self, text: str) -> Dict[str, Any]:
        """Analyse le raisonnement dans le texte"""
        text_lower = text.lower()

        reasoning_analysis = {
            "logical_structure": self._analyze_logical_structure(text_lower),
            "question_type": self._identify_question_type(text_lower),
            "reasoning_chain": self._identify_reasoning_chain(text_lower),
            "complexity_level": self._assess_complexity(text_lower),
            "required_strategy": self._suggest_strategy(text_lower),
        }

        return reasoning_analysis

    def _analyze_logical_structure(self, text: str) -> Dict[str, Any]:
        """Analyse la structure logique du texte"""
        structure = {
            "operators": [],
            "conditions": [],
            "conclusions": [],
            "premises": [],
        }

        # Recherche des opérateurs logiques
        for operator, keywords in self.reasoning_patterns["logical_operators"].items():
            for keyword in keywords:
                if keyword in text:
                    structure["operators"].append(operator)

        # Recherche des structures conditionnelles
        if_then_patterns = [
            r"si\s+(.+?)\s+alors\s+(.+)",
            r"if\s+(.+?)\s+then\s+(.+)",
            r"quand\s+(.+?),\s*(.+)",
        ]

        for pattern in if_then_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                structure["conditions"].append(
                    {"condition": match[0].strip(), "consequence": match[1].strip()}
                )

        return structure

    def _identify_question_type(self, text: str) -> Optional[str]:
        """Identifie le type de question"""
        for question_type, keywords in self.reasoning_patterns[
            "question_types"
        ].items():
            for keyword in keywords:
                if keyword in text:
                    return question_type
        return None

    def _identify_reasoning_chain(self, text: str) -> List[str]:
        """Identifie les chaînes de raisonnement"""
        chains = []

        for chain_type, keywords in self.reasoning_patterns["reasoning_chains"].items():
            for keyword in keywords:
                if keyword in text:
                    chains.append(chain_type)

        return list(set(chains))

    def _assess_complexity(self, text: str) -> str:
        """Évalue la complexité du raisonnement"""
        complexity_indicators = {
            "simple": ["simple", "facile", "basique", "direct"],
            "moderate": ["moyen", "modéré", "normal", "standard"],
            "complex": ["complexe", "difficile", "avancé", "sophistiqué", "compliqué"],
        }

        for level, indicators in complexity_indicators.items():
            for indicator in indicators:
                if indicator in text:
                    return level

        # Évaluation basée sur la longueur et la structure
        if len(text.split()) < 10:
            return "simple"
        elif len(text.split()) < 30:
            return "moderate"
        else:
            return "complex"

    def _suggest_strategy(self, text: str) -> str:
        """Suggère une stratégie de résolution"""
        # Analyse du contexte pour suggérer la meilleure stratégie
        if "problème" in text or "résoudre" in text:
            if "étapes" in text or "comment" in text:
                return "decomposition"
            elif "similaire" in text or "comme" in text:
                return "analogy"
            elif "essayer" in text or "tester" in text:
                return "trial_and_error"
            else:
                return "pattern_recognition"

        return "decomposition"  # Stratégie par défaut

    def solve_problem(self, problem: str) -> str:
        """Résout un problème en utilisant le raisonnement"""
        analysis = self.analyze_reasoning(problem)
        strategy = analysis["required_strategy"]

        solution_steps = self.problem_solving_strategies[strategy]["steps"]

        # Génération de la solution
        solution_text = f"🧠 **Analyse du problème :**\n{problem}\n\n"
        solution_text += f"📋 **Stratégie recommandée :** {self.problem_solving_strategies[strategy]['description']}\n\n"
        solution_text += "🔍 **Étapes de résolution :**\n"

        for i, step in enumerate(solution_steps, 1):
            solution_text += f"{i}. {step}\n"

        # Analyse spécifique du problème
        if analysis["question_type"]:
            solution_text += (
                f"\n❓ **Type de question :** {analysis['question_type']}\n"
            )

        if analysis["reasoning_chain"]:
            solution_text += f"🔗 **Chaînes de raisonnement :** {', '.join(analysis['reasoning_chain'])}\n"

        solution_text += f"\n⚡ **Complexité :** {analysis['complexity_level']}\n"

        # Suggestion d'approche concrète
        concrete_approach = self._generate_concrete_approach(problem)
        solution_text += f"\n💡 **Approche concrète :**\n{concrete_approach}"

        return solution_text

    def _generate_concrete_approach(self, problem: str) -> str:
        """Génère une approche concrète pour le problème"""
        problem_lower = problem.lower()

        # Approches spécifiques selon le type de problème
        if "code" in problem_lower or "programmer" in problem_lower:
            return "1. Définir les spécifications\n2. Choisir l'algorithme\n3. Implémenter étape par étape\n4. Tester et déboguer"

        elif "mathématique" in problem_lower or "calcul" in problem_lower:
            return "1. Identifier les variables\n2. Écrire l'équation\n3. Résoudre étape par étape\n4. Vérifier le résultat"

        elif "analyse" in problem_lower or "comprendre" in problem_lower:
            return "1. Collecter les informations\n2. Organiser les données\n3. Identifier les patterns\n4. Tirer des conclusions"

        else:
            return "1. Clarifier le problème\n2. Rassembler les ressources\n3. Développer un plan\n4. Exécuter et évaluer"

    def generate_explanation(self, topic: str) -> str:
        """Génère une explication détaillée"""
        explanation_structure = {
            "introduction": f"📚 **Introduction à {topic}**",
            "main_points": self._generate_main_points(topic),
            "examples": self._generate_examples(topic),
            "conclusion": "🎯 **Points clés à retenir**",
        }

        explanation_text = f"{explanation_structure['introduction']}\n\n"

        # Points principaux
        explanation_text += "🔍 **Points principaux :**\n"
        for i, point in enumerate(explanation_structure["main_points"], 1):
            explanation_text += f"{i}. {point}\n"

        # Exemples
        explanation_text += "\n💡 **Exemples :**\n"
        for example in explanation_structure["examples"]:
            explanation_text += f"• {example}\n"

        # Conclusion
        explanation_text += f"\n{explanation_structure['conclusion']}\n"
        explanation_text += "• Concept bien défini\n• Applications pratiques\n• Compréhension progressive"

        return explanation_text

    def _generate_main_points(self, topic: str) -> List[str]:
        """Génère les points principaux pour un sujet"""
        generic_points = [
            f"Définition et concepts de base de {topic}",
            f"Importance et applications de {topic}",
            f"Méthodes et techniques liées à {topic}",
            f"Avantages et limitations de {topic}",
        ]

        return generic_points

    def _generate_examples(self, topic: str) -> List[str]:
        """Génère des exemples pour un sujet"""
        generic_examples = [
            f"Exemple pratique d'utilisation de {topic}",
            f"Cas d'usage courant de {topic}",
            f"Application concrète de {topic}",
        ]

        return generic_examples

    def process_query(self, query: str) -> str:
        """Traite une requête générale avec raisonnement"""
        try:
            # Détermination du type de traitement
            if any(
                word in query.lower()
                for word in ["problème", "résoudre", "comment", "pourquoi", "solution"]
            ):
                return self.solve_problem(query)
            elif any(
                word in query.lower()
                for word in ["expliquer", "qu'est-ce que", "définir", "concept"]
            ):
                return self.generate_explanation(query)
            else:
                # Analyse de raisonnement générale
                analysis = self.analyze_reasoning(query)

                if analysis["complexity"] == "low":
                    return "Je peux vous aider avec cette question simple. Pouvez-vous être plus spécifique ?"
                else:
                    return f"C'est une question intéressante qui nécessite réflexion. {analysis['suggested_strategy']}"
        except Exception:
            return "Je ne suis pas sûr de comprendre votre question."
