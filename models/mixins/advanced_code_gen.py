"""
AdvancedCodeGenMixin — Génération de code avancée avec recherche web.

Regroupe : _handle_advanced_code_generation, _search_web_solutions,
_detect_programming_language, _analyze_complexity, etc.
"""

import traceback

try:
    from models.smart_code_searcher import smart_code_searcher

    SMART_CODE_SEARCHER_AVAILABLE = True
except ImportError:
    SMART_CODE_SEARCHER_AVAILABLE = False
    smart_code_searcher = None


class AdvancedCodeGenMixin:
    """Mixin regroupant la génération de code avancée."""

    async def _handle_advanced_code_generation(self, user_input: str) -> str:
        """
        🚀 NOUVELLE VERSION - Génération de code avancée avec SmartCodeSearcher
        - Recherche web intelligente (DuckDuckGo)
        - Analyse sémantique avec embeddings
        - Ranking intelligent des solutions
        - Cache avec similarité
        """
        try:
            # 1. Analyse de la demande
            language = self._detect_programming_language(user_input)
            complexity = self._analyze_complexity(user_input)
            requirements = self._extract_requirements(user_input)

            print(f"🚀 Génération de code SMART: {language}, complexité: {complexity}")

            # 2. 🆕 Utiliser SmartCodeSearcher (nouveau système intelligent)
            try:
                print("🔍 Recherche avec SmartCodeSearcher...")
                smart_snippets = await smart_code_searcher.search_code(
                    user_input, language
                )

                if smart_snippets and len(smart_snippets) > 0:
                    best_snippet = smart_snippets[0]

                    print(
                        f"✅ Meilleure solution trouvée: Score={best_snippet.final_score:.2f}, Source={best_snippet.source_name}"
                    )

                    code = best_snippet.code.strip()

                    response = f"""Voici le code complet :

```{language}
{code}
```

_(Source: {best_snippet.source_name})_"""

                    self._add_to_conversation_history(
                        user_input,
                        response,
                        "code_generation",
                        1.0,
                        {
                            "language": language,
                            "complexity": complexity,
                            "source": best_snippet.source_name,
                            "score": best_snippet.final_score,
                        },
                    )

                    return response
                else:
                    print("⚠️ SmartCodeSearcher n'a pas trouvé de solutions")

            except (ConnectionError, TimeoutError, ImportError, ValueError) as e:
                print(f"⚠️ Erreur SmartCodeSearcher: {e}")
                traceback.print_exc()

            # 3. Fallback sur l'ancien système
            print("📦 Fallback sur l'ancien système de recherche...")
            web_solutions = []
            try:
                web_solutions = await self._search_web_solutions(user_input, language)
            except (ConnectionError, TimeoutError, ImportError) as e:
                print(f"⚠️ Recherche web (fallback) échouée: {e}")

            # 4. Génération hybride ou locale
            if web_solutions:
                best_solution = web_solutions[0]
                enhanced_code = self._create_enhanced_solution(
                    best_solution, user_input, language, requirements
                )
                response = f"💻 Code généré avec recherche web:\n```{language}\n{enhanced_code}\n```\n"
            else:
                local_code = await self._generate_local_advanced_code(
                    user_input, language, requirements
                )
                response = (
                    f"📝 Code généré localement:\n```{language}\n{local_code}\n```\n"
                )

            self._add_to_conversation_history(
                user_input,
                response,
                "code_generation",
                0.8,
                {"language": language, "complexity": complexity, "method": "fallback"},
            )

            return response

        except Exception as e:
            error_msg = f"❌ Erreur lors de la génération de code: {str(e)}"
            print(error_msg)
            traceback.print_exc()
            return error_msg

    def _enhance_smart_snippet(self, snippet, query: str, requirements: list) -> str:
        """Améliore un snippet du SmartCodeSearcher avec commentaires et adaptations"""
        code = snippet.code.strip()

        header = f'''"""
{snippet.title}

Solution pour: {query}
Source: {snippet.source_name}
Qualité: {snippet.quality_score:.1f}/10 | Pertinence: {snippet.relevance_score:.1f}/10
"""

'''

        enhanced_code = header + code

        if "error_handling" in requirements and snippet.language == "python":
            enhanced_code += (
                "\n\n# 💡 Conseil: Ajoutez une gestion d'erreurs avec try/except"
            )

        if "examples" in requirements:
            enhanced_code += "\n\n# 💡 Exemple d'utilisation ci-dessus"

        if "documentation" in requirements:
            enhanced_code += (
                "\n\n# 📝 Ajoutez des docstrings pour documenter vos fonctions"
            )

        return enhanced_code

    async def _search_web_solutions(self, query: str, language: str):
        """Recherche asynchrone de solutions web"""
        return await self.web_code_searcher.search_all_sources(
            query, language, max_results=3
        )

    def _detect_programming_language(self, user_input: str) -> str:
        """Détecte le langage de programmation demandé"""
        user_lower = user_input.lower()

        language_keywords = {
            "python": ["python", "py", "django", "flask", "pandas", "numpy"],
            "javascript": ["javascript", "js", "node", "react", "vue", "angular"],
            "html": ["html", "page web", "site web", "webpage"],
            "css": ["css", "style", "stylesheet", "bootstrap"],
            "java": ["java", "spring", "maven"],
            "cpp": ["c++", "cpp", "c plus plus"],
            "c": ["langage c", "programmation c"],
            "sql": ["sql", "mysql", "database", "base de données"],
            "php": ["php", "laravel", "wordpress"],
            "go": ["golang", "go lang"],
            "rust": ["rust", "cargo"],
            "swift": ["swift", "ios"],
            "kotlin": ["kotlin", "android"],
        }

        for lang, keywords in language_keywords.items():
            if any(keyword in user_lower for keyword in keywords):
                return lang

        return "python"

    def _analyze_complexity(self, user_input: str) -> str:
        """Analyse la complexité de la demande"""
        user_lower = user_input.lower()

        complex_keywords = [
            "api",
            "base de données",
            "algorithme",
            "optimisé",
            "performant",
            "architecture",
            "design pattern",
            "async",
            "threading",
        ]
        intermediate_keywords = [
            "classe",
            "fonction",
            "boucle",
            "condition",
            "fichier",
            "json",
            "csv",
        ]

        if any(keyword in user_lower for keyword in complex_keywords):
            return "avancé"
        elif any(keyword in user_lower for keyword in intermediate_keywords):
            return "intermédiaire"
        else:
            return "débutant"

    def _extract_requirements(self, user_input: str) -> list:
        """Extrait les exigences spécifiques de la demande"""
        requirements = []
        user_lower = user_input.lower()

        if "gestion erreur" in user_lower or "try except" in user_lower:
            requirements.append("error_handling")
        if "commentaire" in user_lower or "documentation" in user_lower:
            requirements.append("documentation")
        if "test" in user_lower or "exemple" in user_lower:
            requirements.append("examples")
        if "optimisé" in user_lower or "performance" in user_lower:
            requirements.append("optimization")
        if "sécurisé" in user_lower or "sécurité" in user_lower:
            requirements.append("security")

        return requirements

    def _create_enhanced_solution(
        self, web_solution, query: str, language: str, requirements: list
    ) -> str:
        """Crée une solution améliorée basée sur une solution web"""
        base_code = web_solution.code

        enhanced_code = f'"""\n{web_solution.title}\nSolution adaptée pour: {query}\nSource: {web_solution.source_name}\n"""\n\n{base_code}'

        if "error_handling" in requirements and language == "python":
            enhanced_code += '\n\n# Gestion d\'erreurs recommandée:\n# try:\n#     result = votre_fonction()\n# except Exception as e:\n#     print(f"Erreur: {e}")'

        if "examples" in requirements:
            enhanced_code += '\n\n# Exemple d\'utilisation:\nif __name__ == "__main__":\n    # Testez votre code ici\n    pass'

        return enhanced_code

    async def _generate_local_advanced_code(
        self, query: str, language: str, requirements: list
    ) -> str:
        """Génère du code avancé localement avec notre AdvancedCodeGenerator"""
        try:
            result = await self.code_generator.generate_code(
                query, language=language, requirements=requirements
            )

            if result.get("success"):
                return result.get("code", "# Aucun code généré")
            else:
                return f"# Erreur lors de la génération: {result.get('error', 'Erreur inconnue')}"

        except (AttributeError, TypeError, ValueError) as e:
            return f"# Erreur lors de la génération: {str(e)}"
