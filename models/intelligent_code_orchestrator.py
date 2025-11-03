"""
Orchestrateur intelligent pour la génération de code dynamique
Coordonne tous les modules existants pour créer des solutions adaptées
Version 1.0 - Conçu pour rivaliser avec les IA modernes
"""

import logging
import re
import traceback
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List

from generators.code_generator import CodeGenerator

# Imports des modules existants
from .advanced_code_generator import AdvancedCodeGenerator
from .internet_search import EnhancedInternetSearchEngine
from .web_code_searcher import MultiSourceCodeSearcher


@dataclass
class IntelligentRequest:
    """Requête enrichie avec analyse contextuelle"""

    original_query: str
    intent: str
    complexity: str
    language: str
    domain: str
    requirements: List[str]
    constraints: List[str]
    examples_needed: bool
    explanation_level: str


@dataclass
class GeneratedSolution:
    """Solution générée avec métadonnées enrichies"""

    code: str
    explanation: str
    language: str
    confidence: float
    sources: List[str]
    adaptations_made: List[str]
    similar_solutions: List[str]
    learning_points: List[str]


class IntelligentCodeOrchestrator:
    """
    Orchestrateur intelligent qui coordonne tous les outils de génération de code
    pour créer des solutions dynamiques et adaptées
    """

    def __init__(self):
        # Initialisation des modules existants
        self.advanced_generator = AdvancedCodeGenerator()
        self.web_searcher = MultiSourceCodeSearcher()
        self.internet_search = EnhancedInternetSearchEngine()
        self.basic_generator = CodeGenerator()

        # Configuration de l'orchestrateur
        self.confidence_threshold = 0.7
        self.max_iterations = 3

        # Base de connaissances pour l'analyse contextuelle
        self.domain_patterns = self._init_domain_patterns()
        self.complexity_indicators = self._init_complexity_indicators()
        self.intent_patterns = self._init_intent_patterns()

        # Logger pour le débogage
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)

    def _init_domain_patterns(self) -> Dict[str, List[str]]:
        """Patterns pour identifier le domaine de programmation"""
        return {
            "web_development": [
                "site web",
                "page html",
                "api rest",
                "serveur",
                "client",
                "frontend",
                "backend",
                "react",
                "vue",
                "angular",
                "django",
                "flask",
            ],
            "data_science": [
                "analyse données",
                "machine learning",
                "pandas",
                "numpy",
                "statistiques",
                "graphique",
                "visualisation",
                "dataset",
            ],
            "automation": [
                "automatiser",
                "script",
                "tâche répétitive",
                "cron",
                "selenium",
                "scraping",
                "téléchargement",
                "backup",
            ],
            "algorithms": [
                "algorithme",
                "tri",
                "recherche",
                "optimisation",
                "complexité",
                "récursion",
                "dynamique",
                "graphe",
            ],
            "system_programming": [
                "système",
                "fichier",
                "processus",
                "thread",
                "réseau",
                "socket",
                "performance",
                "mémoire",
            ],
            "gui_development": [
                "interface graphique",
                "fenêtre",
                "bouton",
                "tkinter",
                "pyqt",
                "gui",
                "desktop",
                "application",
            ],
        }

    def _init_complexity_indicators(self) -> Dict[str, List[str]]:
        """Indicateurs pour évaluer la complexité"""
        return {
            "beginner": [
                "simple",
                "basique",
                "débutant",
                "facile",
                "hello world",
                "premier",
                "introduction",
                "exemple",
            ],
            "intermediate": [
                "moyen",
                "intermédiaire",
                "avec",
                "utilisant",
                "gestion",
                "plusieurs",
                "options",
                "paramètres",
            ],
            "advanced": [
                "avancé",
                "complexe",
                "optimisé",
                "performant",
                "robuste",
                "production",
                "enterprise",
                "scalable",
                "async",
            ],
        }

    def _init_intent_patterns(self) -> Dict[str, List[str]]:
        """Patterns pour identifier l'intention"""
        return {
            "create_new": [
                "créer",
                "faire",
                "générer",
                "construire",
                "développer",
                "écrire",
                "programmer",
                "coder",
            ],
            "modify_existing": [
                "modifier",
                "changer",
                "améliorer",
                "adapter",
                "optimiser",
                "corriger",
                "mettre à jour",
            ],
            "understand": [
                "expliquer",
                "comprendre",
                "comment",
                "pourquoi",
                "documentation",
                "exemple",
                "tutorial",
            ],
            "debug": [
                "déboguer",
                "corriger",
                "erreur",
                "bug",
                "problème",
                "ne fonctionne pas",
                "plantage",
            ],
            "integrate": [
                "intégrer",
                "combiner",
                "connecter",
                "importer",
                "utiliser avec",
                "faire communiquer",
            ],
        }

    def debug_types(self, **kwargs):
        """Fonction de débogage pour vérifier les types"""
        for key, value in kwargs.items():
            print(f"[DEBUG] {key}: {type(value)} = {repr(value)[:100]}")

    async def generate_intelligent_code(
        self, query: str, context: Dict[str, Any] = None
    ) -> GeneratedSolution:
        """
        Génère du code de manière intelligente en utilisant tous les outils disponibles
        """
        # DEBUG: Vérifier les types d'entrée
        self.debug_types(query=query, context=context)

        # CORRECTION: S'assurer que query est une chaîne
        if isinstance(query, dict):
            # Si query est un dictionnaire, extraire la vraie requête
            if "description" in query:
                query = str(query["description"])
            elif "query" in query:
                query = str(query["query"])
            else:
                query = str(query.get("original_query", str(query)))
        elif not isinstance(query, str):
            query = str(query)

        self.logger.info("Génération intelligente pour: %s", query)

        try:
            # 1. Analyse approfondie de la requête
            intelligent_request = await self._analyze_request(query, context or {})
            self.logger.info(
                "Analyse: %s - %s - %s", intelligent_request.intent, intelligent_request.domain, intelligent_request.complexity
            )

            # 2. Recherche de solutions existantes
            existing_solutions = await self._search_existing_solutions(
                intelligent_request
            )
            self.logger.info("%s solutions trouvées", len(existing_solutions))

            # 3. Génération adaptée basée sur l'analyse
            generated_code = await self._generate_adapted_code(
                intelligent_request, existing_solutions
            )

            # 4. Post-traitement et amélioration
            final_solution = await self._enhance_solution(
                generated_code, intelligent_request, existing_solutions
            )

            self.logger.info(
                "Solution générée avec confiance: %s", final_solution.confidence
            )
            return final_solution

        except Exception as e:
            self.logger.error("Erreur génération: %s", e)
            self.logger.error("Traceback: %s", traceback.format_exc())
            # Solution de fallback
            return await self._generate_fallback_solution(query, context)

    async def _analyze_request(
        self, query: str, context: Dict[str, Any]
    ) -> IntelligentRequest:
        """Analyse intelligente et approfondie de la requête"""

        # Détection de l'intention
        intent = self._detect_intent(query)

        # Détection du domaine
        domain = self._detect_domain(query)

        # Évaluation de la complexité
        complexity = self._evaluate_complexity(query)

        # Détection du langage
        language = self._detect_language(query, context)

        # Extraction des exigences
        requirements = self._extract_requirements(query)

        # Détection des contraintes
        constraints = self._extract_constraints(query)

        # Autres paramètres
        examples_needed = any(
            word in query.lower()
            for word in ["exemple", "example", "comment", "how to"]
        )
        explanation_level = "detailed" if examples_needed else "basic"

        return IntelligentRequest(
            original_query=query,
            intent=intent,
            complexity=complexity,
            language=language,
            domain=domain,
            requirements=requirements,
            constraints=constraints,
            examples_needed=examples_needed,
            explanation_level=explanation_level,
        )

    def _detect_intent(self, query: str) -> str:
        """Détecte l'intention principale de la requête"""
        # CORRECTION: S'assurer que query est une chaîne
        if isinstance(query, dict):
            query = str(query.get("description", str(query)))
        elif not isinstance(query, str):
            query = str(query)

        query_lower = query.lower()

        for intent, patterns in self.intent_patterns.items():
            if any(pattern in query_lower for pattern in patterns):
                return intent

        return "create_new"

    def _detect_domain(self, query: str) -> str:
        """Détecte le domaine de programmation"""
        # CORRECTION: S'assurer que query est une chaîne
        if isinstance(query, dict):
            query = str(query.get("description", str(query)))
        elif not isinstance(query, str):
            query = str(query)

        query_lower = query.lower()

        domain_scores = {}
        for domain, patterns in self.domain_patterns.items():
            score = sum(1 for pattern in patterns if pattern in query_lower)
            if score > 0:
                domain_scores[domain] = score

        if domain_scores:
            return max(domain_scores, key=domain_scores.get)

        return "general"

    def _evaluate_complexity(self, query: str) -> str:
        """Évalue la complexité requise"""
        # CORRECTION: S'assurer que query est une chaîne
        if isinstance(query, dict):
            query = str(query.get("description", str(query)))
        elif not isinstance(query, str):
            query = str(query)

        query_lower = query.lower()

        # Vérifier les indicateurs explicites
        for complexity, indicators in self.complexity_indicators.items():
            if any(indicator in query_lower for indicator in indicators):
                return complexity

        # Analyse contextuelle
        complexity_score = 0

        # Facteurs augmentant la complexité
        if any(
            word in query_lower
            for word in ["async", "thread", "performance", "production"]
        ):
            complexity_score += 3
        if any(word in query_lower for word in ["base de données", "api", "réseau"]):
            complexity_score += 2
        if any(word in query_lower for word in ["avec", "utilisant", "plusieurs"]):
            complexity_score += 1

        # Classification
        if complexity_score >= 4:
            return "advanced"
        elif complexity_score >= 2:
            return "intermediate"
        else:
            return "beginner"

    def _detect_language(self, query: str, context: Dict[str, Any]) -> str:
        """Détecte le langage de programmation souhaité"""
        # CORRECTION: S'assurer que query est une chaîne
        if isinstance(query, dict):
            query = str(query.get("description", str(query)))
        elif not isinstance(query, str):
            query = str(query)

        query_lower = query.lower()

        # Détection explicite
        language_patterns = {
            "python": ["python", "py", "django", "flask", "pandas"],
            "javascript": ["javascript", "js", "node", "react", "vue"],
            "html": ["html", "page web", "site web"],
            "css": ["css", "style", "design"],
            "java": ["java", "spring"],
            "cpp": ["c++", "cpp"],
            "sql": ["sql", "database", "base de données"],
        }

        for lang, patterns in language_patterns.items():
            if any(pattern in query_lower for pattern in patterns):
                return lang

        # Contexte ou défaut
        return context.get("preferred_language", "python")

    def _extract_requirements(self, query: str) -> List[str]:
        """Extrait les exigences spécifiques"""
        # CORRECTION: S'assurer que query est une chaîne
        if isinstance(query, dict):
            query = str(query.get("description", str(query)))
        elif not isinstance(query, str):
            query = str(query)

        requirements = []

        # Patterns pour les exigences
        requirement_patterns = [
            r"qui (?:peut|doit|fait) ([^.!?]+)",
            r"avec (.+?) (?:et|,|$)",
            r"utilisant (.+?)(?:\s|$)",
            r"pour (.+?)(?:\s|$)",
        ]

        try:
            for pattern in requirement_patterns:
                matches = re.findall(pattern, query.lower())
                requirements.extend(
                    [match.strip() for match in matches if len(match.strip()) > 3]
                )
        except Exception as e:
            print(f"[ERROR] Erreur extraction requirements: {e}")

        return list(set(requirements))  # Supprimer les doublons

    def _extract_constraints(self, query: str) -> List[str]:
        """Extrait les contraintes"""
        # CORRECTION: S'assurer que query est une chaîne
        if isinstance(query, dict):
            query = str(query.get("description", str(query)))
        elif not isinstance(query, str):
            query = str(query)

        constraints = []

        constraint_patterns = [
            r"sans (.+?)(?:\s|$)",
            r"pas de (.+?)(?:\s|$)",
            r"éviter (.+?)(?:\s|$)",
            r"seulement (.+?)(?:\s|$)",
        ]

        try:
            for pattern in constraint_patterns:
                matches = re.findall(pattern, query.lower())
                constraints.extend(
                    [match.strip() for match in matches if len(match.strip()) > 3]
                )
        except Exception as e:
            print(f"[ERROR] Erreur extraction constraints: {e}")

        return list(set(constraints))

    async def _search_existing_solutions(
        self, request: IntelligentRequest
    ) -> List[Dict[str, Any]]:
        """Recherche des solutions existantes via tous les canaux"""
        all_solutions = []

        # 1. Recherche via l'Advanced Generator (CORRECTION COMPLÈTE)
        try:
            # DEBUG: Vérifier le type de request.original_query
            print(
                f"[DEBUG] request.original_query type: {type(request.original_query)}"
            )
            print(
                f"[DEBUG] request.original_query value: {repr(request.original_query)}"
            )

            # S'assurer que tous les paramètres sont des chaînes
            description = (
                str(request.original_query)
                if not isinstance(request.original_query, str)
                else request.original_query
            )
            language = (
                str(request.language)
                if not isinstance(request.language, str)
                else request.language
            )
            complexity = (
                str(request.complexity)
                if not isinstance(request.complexity, str)
                else request.complexity
            )

            advanced_result = await self.advanced_generator.generate_code(
                description=description,
                language=language,
                complexity=complexity,
                requirements=(
                    request.requirements
                    if isinstance(request.requirements, list)
                    else []
                ),
                context={},
            )

            # Adapter le format de réponse
            if advanced_result.get("success"):
                all_solutions.append(
                    {
                        "code": advanced_result.get("code", ""),
                        "source": advanced_result.get("source", "Advanced Generator"),
                        "rating": advanced_result.get("rating", 3.0),
                        "explanation": advanced_result.get("explanation", ""),
                        "type": "advanced_search",
                    }
                )

        except Exception as e:
            self.logger.warning("Advanced search failed: %s", e)
            self.logger.warning("Advanced search traceback: %s", traceback.format_exc())

        # 2. Recherche multi-sources web
        try:
            web_solutions = await self.web_searcher.search_all_sources(
                str(request.original_query),  # S'assurer que c'est une chaîne
                str(request.language),  # S'assurer que c'est une chaîne
                max_results=3,
            )
            for sol in web_solutions:
                all_solutions.append(
                    {
                        "code": sol.code,
                        "source": sol.source_name,
                        "rating": sol.rating,
                        "explanation": sol.description,
                        "type": "web_search",
                    }
                )
        except Exception as e:
            self.logger.warning("Web search failed: %s", e)

        # 3. Recherche internet générale pour contexte
        try:
            context_info = self.internet_search.search_and_summarize(
                f"{str(request.original_query)} programming tutorial"
            )
            if context_info and len(str(context_info)) > 50:
                all_solutions.append(
                    {
                        "code": "",
                        "source": "Internet Research",
                        "rating": 3.0,
                        "explanation": str(context_info),
                        "type": "context_info",
                    }
                )
        except Exception as e:
            self.logger.warning("Internet search failed: %s", e)

        return all_solutions

    async def _generate_adapted_code(
        self, request: IntelligentRequest, existing_solutions: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Génère du code adapté basé sur l'analyse et les solutions existantes"""

        # Stratégie basée sur l'intention
        if request.intent == "create_new":
            return await self._create_new_solution(request, existing_solutions)
        elif request.intent == "modify_existing":
            return await self._modify_existing_solution(request, existing_solutions)
        elif request.intent == "understand":
            return await self._create_educational_solution(request, existing_solutions)
        else:
            return await self._create_hybrid_solution(request, existing_solutions)

    async def _create_new_solution(
        self, request: IntelligentRequest, existing_solutions: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Crée une nouvelle solution en s'inspirant des solutions existantes"""

        # Sélectionner les meilleures solutions comme inspiration
        code_solutions = [
            sol
            for sol in existing_solutions
            if sol.get("code") and len(sol["code"]) > 20
        ]

        if code_solutions:
            # Prendre la meilleure solution comme base
            best_solution = max(code_solutions, key=lambda x: x.get("rating", 0))

            # Adapter le code selon les spécifications
            adapted_code = await self._adapt_code_to_requirements(
                best_solution["code"], request
            )

            return {
                "code": adapted_code,
                "source": f"Adapted from {best_solution['source']}",
                "base_rating": best_solution.get("rating", 3.0),
                "adaptations": self._document_adaptations(
                    best_solution["code"], adapted_code
                ),
            }
        else:
            # Fallback sur génération basique
            try:
                basic_result = await self.basic_generator.generate_code(request.original_query)

                return {
                    "code": basic_result.get("code", "# Code généré de base"),
                    "source": "Basic Template Generation",
                    "base_rating": 2.5,
                    "adaptations": ["Generated from template"],
                }
            except Exception :
                # Fallback ultime
                return {
                    "code": f"# Solution pour: {request.original_query}\n# TODO: Implémenter",
                    "source": "Fallback Template",
                    "base_rating": 1.0,
                    "adaptations": ["Fallback generation"],
                }

    async def _adapt_code_to_requirements(
        self, base_code: str, request: IntelligentRequest
    ) -> str:
        """Adapte le code de base selon les exigences spécifiques"""
        adapted_code = base_code

        # Adaptations basées sur la complexité
        if request.complexity == "beginner":
            adapted_code = self._simplify_code(adapted_code)
        elif request.complexity == "advanced":
            adapted_code = self._enhance_code(adapted_code)

        # Adaptations basées sur le domaine
        if request.domain == "web_development":
            adapted_code = self._add_web_features(adapted_code)
        elif request.domain == "data_science":
            adapted_code = self._add_data_features(adapted_code)

        # Adaptations basées sur les exigences
        for _requirement in request.requirements:
            adapted_code = self._apply_requirement(adapted_code)

        # Application des contraintes
        for _constraint in request.constraints:
            adapted_code = self._apply_constraint(adapted_code)

        return adapted_code

    def _simplify_code(self, code: str) -> str:
        """Simplifie le code pour les débutants"""
        # Ajouter plus de commentaires
        lines = code.split("\n")
        simplified_lines = []

        for line in lines:
            simplified_lines.append(line)

            # Ajouter des commentaires explicatifs
            if "def " in line:
                simplified_lines.append("    # Cette fonction fait...")
            elif "for " in line:
                simplified_lines.append("    # Boucle pour parcourir...")
            elif "if " in line:
                simplified_lines.append("    # Vérification si...")

        return "\n".join(simplified_lines)

    def _enhance_code(self, code: str) -> str:
        """Améliore le code pour un niveau avancé"""
        enhanced = code

        # Ajouter la gestion d'erreurs
        if "try:" not in enhanced:
            enhanced = f"""try:
{self._indent_code(enhanced, 1)}
except Exception as e:
    print(f"Erreur: {{e}}")
    raise"""

        # Ajouter des docstrings si manquants
        if '"""' not in enhanced and "def " in enhanced:
            enhanced = self._add_docstrings(enhanced)

        return enhanced

    def _add_web_features(self, code: str) -> str:
        """Ajoute des fonctionnalités spécifiques au web"""
        # Exemple d'adaptation pour le web
        if "import" not in code:
            code = "from flask import Flask, request, jsonify\n\n" + code

        return code

    def _add_data_features(self, code: str) -> str:
        """Ajoute des fonctionnalités spécifiques à la data science"""
        if "import" not in code:
            code = "import pandas as pd\nimport numpy as np\n\n" + code

        return code

    def _apply_requirement(self, code: str) -> str:
        """Applique une exigence spécifique au code"""
        # Logique pour appliquer les exigences
        # (à développer selon les besoins)
        return code

    def _apply_constraint(self, code: str) -> str:
        """Applique une contrainte au code"""
        # Logique pour respecter les contraintes
        # (à développer selon les besoins)
        return code

    def _indent_code(self, code: str, levels: int) -> str:
        """Indente le code du nombre de niveaux spécifié"""
        indent = "    " * levels
        return "\n".join(indent + line for line in code.split("\n"))

    def _add_docstrings(self, code: str) -> str:
        """Ajoute des docstrings aux fonctions"""
        # Simple ajout de docstring
        return code.replace("def ", "def ").replace(
            "):", '):\n    """Description de la fonction"""'
        )

    def _document_adaptations(self, original: str, adapted: str) -> List[str]:
        """Documente les adaptations effectuées"""
        adaptations = []

        if len(adapted) > len(original) * 1.2:
            adaptations.append("Code étendu avec des améliorations")

        if '"""' in adapted and '"""' not in original:
            adaptations.append("Ajout de documentation")

        if "try:" in adapted and "try:" not in original:
            adaptations.append("Ajout de gestion d'erreurs")

        return adaptations

    async def _create_educational_solution(
        self, request: IntelligentRequest, existing_solutions: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Crée une solution éducative avec explications détaillées"""
        base_solution = await self._create_new_solution(request, existing_solutions)

        # Ajouter des explications détaillées
        educational_code = self._add_educational_comments(base_solution["code"])

        return {**base_solution, "code": educational_code, "educational_mode": True}

    def _add_educational_comments(self, code: str) -> str:
        """Ajoute des commentaires éducatifs détaillés"""
        lines = code.split("\n")
        educational_lines = []

        for line in enumerate(lines):
            # Ajouter un commentaire explicatif avant les lignes importantes
            if any(
                keyword in line
                for keyword in ["def ", "class ", "for ", "if ", "while "]
            ):
                educational_lines.append(
                    f"# Étape {len([l for l in educational_lines if l.strip().startswith('# Étape')]) + 1}: Explication de cette partie"
                )

            educational_lines.append(line)

            # Ajouter des explications après certaines constructions
            if "def " in line:
                educational_lines.append(
                    "    # Cette fonction va accomplir une tâche spécifique"
                )

        return "\n".join(educational_lines)

    async def _create_hybrid_solution(
        self, request: IntelligentRequest, existing_solutions: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Crée une solution hybride combinant plusieurs approches"""
        # Pour l'instant, utiliser la création nouvelle comme base
        return await self._create_new_solution(request, existing_solutions)

    async def _modify_existing_solution(
        self, request: IntelligentRequest, existing_solutions: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Modifie une solution existante"""
        # Pour l'instant, traiter comme une création nouvelle
        return await self._create_new_solution(request, existing_solutions)

    async def _enhance_solution(
        self,
        generated_code: Dict[str, Any],
        request: IntelligentRequest,
        existing_solutions: List[Dict[str, Any]],
    ) -> GeneratedSolution:
        """Post-traitement et amélioration de la solution"""

        # Calculer la confiance
        confidence = self._calculate_confidence(generated_code, existing_solutions)

        # Générer l'explication
        explanation = self._generate_explanation(generated_code, request)

        # Identifier les sources
        sources = [generated_code.get("source", "Generated")]

        # Documenter les adaptations
        adaptations = generated_code.get("adaptations", [])

        # Solutions similaires
        similar_solutions = [
            sol.get("code", "")[:100] + "..."
            for sol in existing_solutions[:2]
            if sol.get("code") and sol.get("code") != generated_code.get("code")
        ]

        # Points d'apprentissage
        learning_points = self._extract_learning_points(generated_code["code"], request)

        return GeneratedSolution(
            code=generated_code.get("code", ""),
            explanation=explanation,
            language=request.language,
            confidence=confidence,
            sources=sources,
            adaptations_made=adaptations,
            similar_solutions=similar_solutions,
            learning_points=learning_points,
        )

    def _calculate_confidence(
        self, generated_code: Dict[str, Any], existing_solutions: List[Dict[str, Any]]
    ) -> float:
        """Calcule la confiance dans la solution générée"""
        base_confidence = 0.5

        # Bonus si basé sur une bonne solution
        base_rating = generated_code.get("base_rating", 0)
        if base_rating > 0:
            base_confidence += min(0.4, base_rating / 5.0 * 0.4)

        # Bonus pour le nombre de sources
        if len(existing_solutions) > 2:
            base_confidence += 0.1

        # Bonus pour les adaptations
        adaptations = generated_code.get("adaptations", [])
        if adaptations:
            base_confidence += min(0.2, len(adaptations) * 0.05)

        return min(1.0, base_confidence)

    def _generate_explanation(
        self, generated_code: Dict[str, Any], request: IntelligentRequest
    ) -> str:
        """Génère une explication de la solution"""
        explanation = f"Cette solution a été générée pour répondre à votre demande : '{request.original_query}'\n\n"

        if generated_code.get("source"):
            explanation += f"**Source d'inspiration :** {generated_code['source']}\n\n"

        explanation += f"**Langage :** {request.language.title()}\n"
        explanation += f"**Complexité :** {request.complexity}\n"
        explanation += f"**Domaine :** {request.domain.replace('_', ' ').title()}\n\n"

        adaptations = generated_code.get("adaptations", [])
        if adaptations:
            explanation += "**Adaptations effectuées :**\n"
            for adaptation in adaptations:
                explanation += f"• {adaptation}\n"
            explanation += "\n"

        if request.requirements:
            explanation += "**Exigences prises en compte :**\n"
            for req in request.requirements[:3]:  # Limiter à 3
                explanation += f"• {req}\n"

        return explanation

    def _extract_learning_points(
        self, code: str, request: IntelligentRequest
    ) -> List[str]:
        """Extrait les points d'apprentissage du code"""
        learning_points = []

        # Analyser les concepts présents
        if "def " in code:
            learning_points.append("Définition et utilisation de fonctions")

        if "class " in code:
            learning_points.append("Programmation orientée objet")

        if "for " in code or "while " in code:
            learning_points.append("Structures de boucle")

        if "if " in code:
            learning_points.append("Structures conditionnelles")

        if "try:" in code:
            learning_points.append("Gestion des erreurs")

        if "import " in code:
            learning_points.append("Utilisation de bibliothèques externes")

        # Points spécifiques au domaine
        if request.domain == "web_development":
            learning_points.append("Développement web")
        elif request.domain == "data_science":
            learning_points.append("Science des données")

        return learning_points[:5]  # Limiter à 5 points

    async def _generate_fallback_solution(
        self, query: str, context: Dict[str, Any]
    ) -> GeneratedSolution:
        """Génère une solution de fallback en cas d'échec"""
        try:
            basic_result = await self.basic_generator.generate_code(
                query or {}
            )

            return GeneratedSolution(
                code=basic_result.get(
                    "code", f"# Solution pour: {query}\n# TODO: Implémenter"
                ),
                explanation=f"Solution de base générée pour: {query}",
                language=context.get("language", "python"),
                confidence=0.3,
                sources=["Template de base"],
                adaptations_made=["Génération par template"],
                similar_solutions=[],
                learning_points=["Programmation de base"],
            )
        except Exception as e:
            return GeneratedSolution(
                code=f"# Erreur lors de la génération pour: {query}\n# TODO: Implémenter manuellement",
                explanation=f"Une erreur s'est produite: {str(e)}",
                language="python",
                confidence=0.1,
                sources=["Erreur système"],
                adaptations_made=[],
                similar_solutions=[],
                learning_points=[],
            )


# Instance globale pour utilisation facile
intelligent_orchestrator = IntelligentCodeOrchestrator()


# Fonction utilitaire principale avec nom unique
async def create_intelligent_code(query: str, **kwargs) -> Dict[str, Any]:
    """
    Point d'entrée principal pour la génération intelligente de code

    Args:
        query: Demande de génération de code
        **kwargs: Paramètres optionnels (language, complexity, etc.)

    Returns:
        Dictionnaire avec le code généré et les métadonnées
    """
    # CORRECTION: S'assurer que query est une chaîne
    if not isinstance(query, str):
        query = str(query)

    try:
        solution = await intelligent_orchestrator.generate_intelligent_code(
            query, kwargs
        )

        return {
            "success": True,
            "code": solution.code,
            "explanation": solution.explanation,
            "language": solution.language,
            "confidence": solution.confidence,
            "sources": solution.sources,
            "adaptations": solution.adaptations_made,
            "similar_solutions": solution.similar_solutions,
            "learning_points": solution.learning_points,
            "generated_at": datetime.now().isoformat(),
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "code": f"# Erreur lors de la génération: {e}\n# TODO: Implémenter manuellement",
            "explanation": f"Une erreur s'est produite: {str(e)}",
            "language": kwargs.get("language", "python"),
            "confidence": 0.1,
            "sources": ["Erreur système"],
            "adaptations": [],
            "similar_solutions": [],
            "learning_points": [],
            "debug_info": [f"Traceback: {traceback.format_exc()}"],
        }


if __name__ == "__main__":
    # Test de l'orchestrateur
    async def test_orchestrator():
        """Test l'orchestrateur"""
        test_queries = [
            "Créer une fonction Python pour inverser une chaîne de caractères",
            "Faire un script avancé pour analyser des données CSV avec pandas",
            "Comment créer une API REST simple avec Flask",
            "Algorithme de tri rapide optimisé pour de gros datasets",
        ]

        orchestrator = IntelligentCodeOrchestrator()

        for query in test_queries:
            print(f"\n Test: {query}")
            print("-" * 80)

            solution = await orchestrator.generate_intelligent_code(query)

            print(f" Confiance: {solution.confidence:.2f}")
            print(f" Sources: {', '.join(solution.sources)}")
            print(f" Adaptations: {len(solution.adaptations_made)}")
            print("\n Code généré:")
            print(
                solution.code[:300] + "..."
                if len(solution.code) > 300
                else solution.code
            )
            print("\n" + "=" * 80)

    # Décommenter pour tester
    # asyncio.run(test_orchestrator())
