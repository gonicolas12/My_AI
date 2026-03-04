"""
Système d'Agents IA Spécialisés basés sur Ollama
Chaque agent a une expertise et un comportement spécifique
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
import re

from models.local_llm import LocalLLM
from models.internet_search import EnhancedInternetSearchEngine

# ── Modèle par défaut (lu depuis config.yaml → llm.local.default_model) ────────────
try:
    from core.config import get_default_model as _cfg_default_model
    _DEFAULT_LLM_MODEL: str = str(_cfg_default_model())
except Exception:
    _DEFAULT_LLM_MODEL: str = "qwen3.5:4b"


class AIAgent:
    """
    Agent IA de base avec expertise spécialisée
    """

    def __init__(
        self,
        name: str,
        expertise: str,
        system_prompt: str,
        model: str = _DEFAULT_LLM_MODEL,
        temperature: float = 0.7,
    ):
        """
        Initialise un agent IA

        Args:
            name: Nom de l'agent
            expertise: Domaine d'expertise
            system_prompt: Prompt système qui définit le comportement
            model: Modèle Ollama à utiliser
            temperature: Créativité (0.0-1.0)
        """
        self.name = name
        self.expertise = expertise
        self.system_prompt = system_prompt
        self.model = model
        self.temperature = temperature

        # Créer une instance LLM dédiée pour cet agent
        self.llm = LocalLLM(model=model)

        # Historique des tâches de cet agent
        self.task_history: List[Dict[str, Any]] = []

        # Statistiques
        self.stats = {
            "tasks_completed": 0,
            "total_tokens": 0,
            "success_rate": 1.0,
            "created_at": datetime.now().isoformat(),
        }

        print(f"🤖 Agent '{self.name}' initialisé (expertise: {self.expertise})")

    def execute_task(self, task: str, context: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Exécute une tâche avec le contexte de l'agent

        Args:
            task: Description de la tâche
            context: Contexte additionnel

        Returns:
            Dict avec le résultat et les métadonnées
        """
        if not self.llm.is_ollama_available:
            return {
                "success": False,
                "result": "❌ Ollama non disponible",
                "agent": self.name,
                "error": "ollama_unavailable",
            }

        # Construire le prompt enrichi
        full_prompt = self._build_prompt(task, context)

        try:
            print(f"⚙️ Agent {self.name} exécute la tâche...")

            # Générer la réponse
            response = self.llm.generate(
                prompt=full_prompt, system_prompt=self.system_prompt
            )

            if response:
                # Enregistrer dans l'historique
                task_record = {
                    "task": task,
                    "result": response,
                    "timestamp": datetime.now().isoformat(),
                    "context": context,
                }
                self.task_history.append(task_record)

                # Mettre à jour les stats
                self.stats["tasks_completed"] += 1

                print(f"✅ Agent {self.name} a terminé la tâche")

                return {
                    "success": True,
                    "result": response,
                    "agent": self.name,
                    "expertise": self.expertise,
                    "timestamp": task_record["timestamp"],
                }
            else:
                return {
                    "success": False,
                    "result": "❌ Pas de réponse générée",
                    "agent": self.name,
                    "error": "no_response",
                }

        except Exception as e:
            print(f"❌ Erreur agent {self.name}: {e}")
            return {
                "success": False,
                "result": f"❌ Erreur: {str(e)}",
                "agent": self.name,
                "error": str(e),
            }

    def execute_task_stream(
        self, task: str, context: Optional[Dict] = None, on_token=None
    ) -> Dict[str, Any]:
        """
        Exécute une tâche avec streaming (affichage progressif)

        Args:
            task: Description de la tâche
            context: Contexte additionnel
            on_token: Callback appelé pour chaque token reçu

        Returns:
            Dict avec le résultat et les métadonnées
        """
        if not self.llm.is_ollama_available:
            return {
                "success": False,
                "result": "❌ Ollama non disponible",
                "agent": self.name,
                "error": "ollama_unavailable",
            }

        # Construire le prompt enrichi
        full_prompt = self._build_prompt(task, context)

        try:
            print(f"⚙️ Agent {self.name} exécute la tâche (streaming)...")

            # Générer la réponse avec streaming
            response = self.llm.generate_stream(
                prompt=full_prompt, system_prompt=self.system_prompt, on_token=on_token
            )

            if response:
                # Enregistrer dans l'historique
                task_record = {
                    "task": task,
                    "result": response,
                    "timestamp": datetime.now().isoformat(),
                    "context": context,
                }
                self.task_history.append(task_record)

                # Mettre à jour les stats
                self.stats["tasks_completed"] += 1

                print(f"✅ Agent {self.name} a terminé la tâche")

                return {
                    "success": True,
                    "result": response,
                    "agent": self.name,
                    "expertise": self.expertise,
                    "timestamp": task_record["timestamp"],
                }
            else:
                return {
                    "success": False,
                    "result": "❌ Pas de réponse générée",
                    "agent": self.name,
                    "error": "no_response",
                }

        except Exception as e:
            print(f"❌ Erreur agent {self.name}: {e}")
            return {
                "success": False,
                "result": f"❌ Erreur: {str(e)}",
                "agent": self.name,
                "error": str(e),
            }

    def _build_prompt(self, task: str, context: Optional[Dict]) -> str:
        """Construit le prompt enrichi avec contexte"""
        prompt_parts = [f"TÂCHE: {task}"]

        if context:
            prompt_parts.append("\nCONTEXTE:")
            for key, value in context.items():
                prompt_parts.append(f"- {key}: {value}")

        # Ajouter l'historique récent si pertinent
        if len(self.task_history) > 0:
            recent_tasks = self.task_history[-3:]  # 3 dernières tâches
            prompt_parts.append("\nHISTORIQUE RÉCENT:")
            for i, task_record in enumerate(recent_tasks, 1):
                prompt_parts.append(f"{i}. {task_record['task'][:100]}...")

        return "\n".join(prompt_parts)

    def get_stats(self) -> Dict[str, Any]:
        """Retourne les statistiques de l'agent"""
        return {
            "name": self.name,
            "expertise": self.expertise,
            "model": self.model,
            **self.stats,
            "recent_tasks": len(self.task_history[-10:]),
        }

    def reset_history(self):
        """Efface l'historique des tâches"""
        self.task_history.clear()
        self.llm.clear_history()
        print(f"🗑️ Historique de l'agent {self.name} effacé")


class WebSearchAgent(AIAgent):
    """
    Agent spécialisé en recherche internet RÉELLE
    Utilise EnhancedInternetSearchEngine pour faire de vraies recherches
    puis synthétise les résultats avec Ollama
    """

    def __init__(
        self,
        name: str = "WebSearchAgent",
        expertise: str = "Recherche Internet & Fact-Checking",
        model: str = _DEFAULT_LLM_MODEL,
        temperature: float = 0.5,
        focus_year: int = None,
    ):
        """
        Initialise l'agent de recherche web

        Args:
            name: Nom de l'agent
            expertise: Domaine d'expertise
            model: Modèle Ollama
            temperature: Créativité
            focus_year: Année spécifique à privilégier (optionnel, None = pas de filtre)
        """
        # Construire le comportement selon focus_year
        year_instruction = f"- Privilégier les sources datant de {focus_year} quand pertinent\n" if focus_year else "- Privilégier les sources les plus récentes et pertinentes\n"

        system_prompt = f"""Tu es {name}, un agent de recherche internet expert.

EXPERTISE: Recherche web approfondie, fact-checking, croisement de sources, analyse de sources récentes

COMPORTEMENT:
- Tu reçois des RÉSULTATS DE RECHERCHE RÉELS provenant d'internet
- Tu DOIS te baser UNIQUEMENT sur ces résultats pour répondre
- Ne JAMAIS inventer de données ou d'informations
- Croiser plusieurs sources quand disponibles
{year_instruction}- Citer les sources utilisées
- Si les résultats sont insuffisants, le dire clairement

FORMAT DE RÉPONSE:
- Introduction concise
- Informations factuelles basées sur les sources
- Sources utilisées
- Note sur la fiabilité si pertinent
- Suggestions pour approfondir si nécessaire

IMPORTANT: Si tu ne trouves pas d'information dans les résultats fournis, DIS-LE clairement au lieu d'inventer."""

        super().__init__(
            name=name,
            expertise=expertise,
            system_prompt=system_prompt,
            model=model,
            temperature=temperature,
        )

        # Module de recherche internet RÉEL avec accès au LLM pour analyse intelligente
        self.search_engine = EnhancedInternetSearchEngine(llm=self.llm)
        self.focus_year = focus_year

        if focus_year:
            print(f"🌐 Agent de recherche web initialisé avec Ollama (focus: {focus_year})")
        else:
            print("🌐 Agent de recherche web initialisé avec Ollama (mode: recherche universelle)")

    def _optimize_search_query(self, query: str) -> str:
        """
        Optimise la requête de recherche avec LLM (1er appel Ollama).
        Transforme une question naturelle en requête de recherche concise et efficace.
        Fallback regex si LLM indisponible.

        Exemple: "cherche les résultats des élecions légilatives de 2024 en France"
                 -> "élections législatives France 2024 résultats"
        """
        # Nettoyage de base commun
        query_clean = query.strip()
        query_clean = re.sub(r"\s+", " ", query_clean)

        # Appel LLM si disponible
        if self.llm and self.llm.is_ollama_available:
            try:
                llm_prompt = (
                    f"Transforme cette demande en une requête de recherche Wikipedia courte et efficace "
                    f"(5 à 8 mots maximum, mots-clés essentiels uniquement, sans verbes ni politesse). "
                    f"Réponds UNIQUEMENT avec la requête, rien d'autre.\n\nDemande: {query_clean}"
                )
                optimized = self.llm.generate(
                    prompt=llm_prompt,
                    system_prompt="Tu es un expert en recherche d'information. Réponds uniquement avec la requête optimisée, sans explication ni ponctuation.",
                )
                if optimized:
                    optimized = optimized.strip().strip("\"'.,!?:;\n\r")
                    # Sanity check: résultat raisonnable (entre 3 et 120 chars)
                    if 3 <= len(optimized) <= 120:
                        print(f"🔧 Requête optimisée (LLM): '{query}' → '{optimized}'")
                        return optimized
            except Exception as e:
                print(f"⚠️ LLM query optimization failed, fallback regex: {e}")

        # Fallback regex
        query_clean = re.sub(
            r"^(?:peux[-\s]?tu\s+|pourrais[-\s]?tu\s+|merci\s+de\s+)?",
            "",
            query_clean,
            flags=re.IGNORECASE,
        )
        query_clean = re.sub(
            r"^(?:cherche(?:r)?|trouve(?:r)?|recherche(?:r)?)\s+(?:sur\s+)?(?:internet|web|google)?\s*",
            "",
            query_clean,
            flags=re.IGNORECASE,
        )
        query_clean = query_clean.strip(" .,!?:;\"'\n\r")

        if len(query_clean) >= 3 and len(query_clean) < len(query):
            print(f"🔧 Requête optimisée (regex): '{query}' → '{query_clean}'")
            return query_clean
        return query

    def execute_task(self, task: str, context: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Exécute une recherche internet RÉELLE puis synthétise avec Ollama

        Args:
            task: Question/requête de recherche
            context: Contexte additionnel

        Returns:
            Dict avec résultats réels de la recherche
        """
        if not self.llm.is_ollama_available:
            return {
                "success": False,
                "result": "❌ Ollama non disponible",
                "agent": self.name,
                "error": "ollama_unavailable",
            }

        try:
            # ÉTAPE 0: Optimiser la requête avec Ollama
            optimized_query = self._optimize_search_query(task)
            print(f"🌐 Lancement de la recherche pour: '{optimized_query[:100]}'")

            # ÉTAPE 1: Recherche source unique (sans synthèse intermédiaire)
            search_results = self.search_engine.search_best_source_context(
                optimized_query
            )

            if not search_results or len(str(search_results)) < 50:
                return {
                    "success": False,
                    "result": f"❌ Aucun résultat de recherche trouvé pour: {optimized_query}",
                    "agent": self.name,
                    "error": "no_search_results",
                }

            # ÉTAPE 2: Filtrer/prioriser sources de l'année focus (seulement si focus_year défini)
            if self.focus_year:
                filtered_results = self._filter_by_year(search_results, self.focus_year)
            else:
                filtered_results = search_results

            # ÉTAPE 3: Construire le prompt avec LES VRAIS RÉSULTATS
            synthesis_prompt = f"""QUESTION ORIGINALE: {task}

RÉSULTATS DE RECHERCHE INTERNET (SOURCES RÉELLES):
{filtered_results if filtered_results else search_results}

------------------------------------------

INSTRUCTIONS:
1. Analyse ces résultats de recherche RÉELS
2. Réponds à la question en te basant UNIQUEMENT sur ces informations
3. Cite les sources utilisées
4. Si les informations sont contradictoires, mentionne-le
5. Si les résultats sont insuffisants pour répondre complètement, dis-le clairement
6. NE JAMAIS inventer ou supposer des informations qui ne sont pas dans les résultats

Réponds maintenant:"""

            # ÉTAPE 4: Demander à Ollama de SYNTHÉTISER les vrais résultats
            print(f"🧠 Synthèse des résultats avec {self.model}...")
            synthesis = self.llm.generate(
                prompt=synthesis_prompt, system_prompt=self.system_prompt
            )

            if synthesis:
                # Enregistrer dans l'historique
                task_record = {
                    "task": task,
                    "search_results": search_results,
                    "synthesis": synthesis,
                    "timestamp": datetime.now().isoformat(),
                    "context": context,
                }
                self.task_history.append(task_record)
                self.stats["tasks_completed"] += 1

                print("✅ Recherche et synthèse terminées")

                return {
                    "success": True,
                    "result": synthesis,
                    "agent": self.name,
                    "expertise": self.expertise,
                    "search_results_raw": search_results,
                    "timestamp": task_record["timestamp"],
                }
            else:
                return {
                    "success": False,
                    "result": f"❌ Échec de la synthèse\n\nRésultats bruts:\n{search_results}",
                    "agent": self.name,
                    "error": "synthesis_failed",
                }

        except Exception as e:
            print(f"❌ Erreur recherche web: {e}")
            return {
                "success": False,
                "result": f"❌ Erreur lors de la recherche: {str(e)}",
                "agent": self.name,
                "error": str(e),
            }

    def execute_task_stream(
        self, task: str, context: Optional[Dict] = None, on_token=None
    ) -> Dict[str, Any]:
        """
        Exécute une recherche avec streaming de la synthèse

        Args:
            task: Question/requête
            context: Contexte
            on_token: Callback streaming

        Returns:
            Résultats avec streaming
        """
        if not self.llm.is_ollama_available:
            return {
                "success": False,
                "result": "❌ Ollama non disponible",
                "agent": self.name,
                "error": "ollama_unavailable",
            }

        try:
            # ÉTAPE 0: Optimiser la requête avec Ollama
            optimized_query = self._optimize_search_query(task)
            print(f"🌐 Lancement de la recherche pour: '{optimized_query[:100]}'")

            # ÉTAPE 1: Recherche source unique (pas de synthèse intermédiaire)
            search_results = self.search_engine.search_best_source_context(
                optimized_query
            )

            if not search_results or len(str(search_results)) < 50:
                error_msg = (
                    f"❌ Aucun résultat de recherche trouvé pour: {optimized_query}"
                )
                if on_token:
                    on_token(error_msg)
                return {
                    "success": False,
                    "result": error_msg,
                    "agent": self.name,
                    "error": "no_search_results",
                }

            # Notifier l'utilisateur que la recherche est terminée
            if on_token:
                on_token("\n🔍 **Recherche terminée** - Synthèse en cours...\n\n")

            # ÉTAPE 2: Filtrer par année (seulement si focus_year défini)
            if self.focus_year:
                filtered_results = self._filter_by_year(search_results, self.focus_year)
            else:
                filtered_results = search_results

            # ÉTAPE 3: Construire le prompt
            synthesis_prompt = f"""QUESTION ORIGINALE: {task}

RÉSULTATS DE RECHERCHE INTERNET (SOURCES RÉELLES):
{filtered_results if filtered_results else search_results}

------------------------------------------

INSTRUCTIONS:
1. Analyse ces résultats de recherche RÉELS
2. Réponds à la question en te basant UNIQUEMENT sur ces informations
3. Cite les sources utilisées
4. Si les informations sont contradictoires, mentionne-le
5. Si les résultats sont insuffisants, dis-le clairement
6. NE JAMAIS inventer des informations

Réponds maintenant:"""

            # ÉTAPE 4: Streaming de la synthèse
            print(f"🧠 Synthèse streaming avec {self.model}...")
            synthesis = self.llm.generate_stream(
                prompt=synthesis_prompt,
                system_prompt=self.system_prompt,
                on_token=on_token,
            )

            if synthesis:
                task_record = {
                    "task": task,
                    "search_results": search_results,
                    "synthesis": synthesis,
                    "timestamp": datetime.now().isoformat(),
                    "context": context,
                }
                self.task_history.append(task_record)
                self.stats["tasks_completed"] += 1

                print("✅ Recherche et synthèse streaming terminées")

                return {
                    "success": True,
                    "result": synthesis,
                    "agent": self.name,
                    "expertise": self.expertise,
                    "search_results_raw": search_results,
                    "timestamp": task_record["timestamp"],
                }
            else:
                fallback = (
                    f"❌ Échec de la synthèse\n\nRésultats bruts:\n{search_results}"
                )
                if on_token:
                    on_token(fallback)
                return {
                    "success": False,
                    "result": fallback,
                    "agent": self.name,
                    "error": "synthesis_failed",
                }

        except Exception as e:
            error_msg = f"❌ Erreur lors de la recherche: {str(e)}"
            print(error_msg)
            if on_token:
                on_token(error_msg)
            return {
                "success": False,
                "result": error_msg,
                "agent": self.name,
                "error": str(e),
            }

    def _filter_by_year(self, search_results: str, year: int) -> str:
        """
        Filtre/priorise les résultats contenant l'année spécifiée

        Args:
            search_results: Résultats bruts
            year: Année à prioriser

        Returns:
            Résultats filtrés ou texte indiquant la priorité
        """
        # Chercher des mentions de l'année dans les résultats
        year_pattern = rf"\b{year}\b"
        lines = search_results.split("\n")

        # Lignes contenant l'année
        year_lines = [line for line in lines if re.search(year_pattern, line)]

        if year_lines:
            filtered = "\n".join(year_lines)
            return f"""⚠️ RÉSULTATS FILTRÉS - Focus sur {year}:

{filtered}

--- Tous les résultats ---

{search_results}"""
        else:
            return f"""⚠️ Aucune source spécifique à {year} trouvée. Voici les résultats disponibles:

{search_results}"""


class AgentFactory:
    """
    Factory pour créer des agents pré-configurés
    """

    @staticmethod
    def create_code_agent(model: str = _DEFAULT_LLM_MODEL) -> AIAgent:
        """Agent spécialisé en génération et debug de code"""
        system_prompt = """Tu es CodeAgent, un expert en programmation.
        
EXPERTISE: Développement logiciel, algorithmes, debug, optimisation de code
LANGAGES: Python, JavaScript, Java, C++, HTML/CSS, SQL

COMPORTEMENT:
- Génère du code propre, commenté et fonctionnel
- Explique chaque partie du code
- Propose des alternatives et optimisations
- Détecte et corrige les bugs
- Suit les bonnes pratiques et conventions

FORMAT DE RÉPONSE:
- Code dans des blocs ```langage
- Commentaires clairs
- Exemples d'utilisation
- Tests unitaires si pertinent"""

        return AIAgent(
            name="CodeAgent",
            expertise="Programmation & Debug",
            system_prompt=system_prompt,
            model=model,
            temperature=0.3,  # Moins créatif, plus précis
        )

    @staticmethod
    def create_analyst_agent(model: str = _DEFAULT_LLM_MODEL) -> AIAgent:
        """Agent spécialisé en analyse de données et documents"""
        system_prompt = """Tu es AnalystAgent, un analyste de données expert.

EXPERTISE: Analyse de données, statistiques, visualisation, extraction d'insights, documents

COMPORTEMENT:
- Analyse en profondeur les données fournies
- Identifie les patterns et tendances
- Calcule des statistiques pertinentes
- Propose des visualisations
- Tire des conclusions basées sur les données

FORMAT DE RÉPONSE:
- Résumé exécutif
- Analyses détaillées avec chiffres
- Insights clés
- Recommandations
- Graphiques suggérés (en texte)"""

        return AIAgent(
            name="AnalystAgent",
            expertise="Analyse de Données",
            system_prompt=system_prompt,
            model=model,
            temperature=0.4,
        )

    @staticmethod
    def create_creative_agent(model: str = _DEFAULT_LLM_MODEL) -> AIAgent:
        """Agent spécialisé en contenu créatif"""
        system_prompt = """Tu es CreativeAgent, un créateur de contenu expert.

EXPERTISE: Rédaction créative, storytelling, marketing, communication

COMPORTEMENT:
- Génère du contenu original et engageant
- Adapte le ton et le style à l'audience
- Utilise des techniques narratives efficaces
- Propose plusieurs variantes
- Optimise pour la lisibilité et l'impact

FORMAT DE RÉPONSE:
- Contenu principal
- Variantes proposées
- Explications des choix créatifs
- Suggestions d'amélioration"""

        return AIAgent(
            name="CreativeAgent",
            expertise="Contenu Créatif",
            system_prompt=system_prompt,
            model=model,
            temperature=0.8,  # Plus créatif
        )

    @staticmethod
    def create_debug_agent(model: str = _DEFAULT_LLM_MODEL) -> AIAgent:
        """Agent spécialisé en détection et correction d'erreurs"""
        system_prompt = """Tu es DebugAgent, un expert en debug et correction d'erreurs.

EXPERTISE: Débogage, analyse d'erreurs, tests, qualité du code

COMPORTEMENT:
- Identifie les bugs et erreurs logiques
- Analyse les stack traces
- Propose des corrections précises
- Suggère des tests pour prévenir les régressions
- Explique la cause racine du problème

FORMAT DE RÉPONSE:
- Problème identifié
- Cause racine
- Solution proposée avec code corrigé
- Tests recommandés
- Conseils de prévention"""

        return AIAgent(
            name="DebugAgent",
            expertise="Debug & Correction",
            system_prompt=system_prompt,
            model=model,
            temperature=0.2,  # Très précis
        )

    @staticmethod
    def create_planner_agent(model: str = _DEFAULT_LLM_MODEL) -> AIAgent:
        """Agent spécialisé en planification de tâches complexes"""
        system_prompt = """Tu es PlannerAgent, un expert en planification et organisation.

EXPERTISE: Décomposition de tâches, planification de projets, gestion de workflow

COMPORTEMENT:
- Décompose les tâches complexes en étapes simples
- Identifie les dépendances entre tâches
- Estime les efforts et priorités
- Propose un ordre d'exécution optimal
- Identifie les risques potentiels

FORMAT DE RÉPONSE:
- Vue d'ensemble du projet
- Liste des tâches numérotées
- Dépendances entre tâches
- Estimation de complexité
- Ordre d'exécution recommandé
- Risques et mitigations"""

        return AIAgent(
            name="PlannerAgent",
            expertise="Planification & Organisation",
            system_prompt=system_prompt,
            model=model,
            temperature=0.5,
        )

    @staticmethod
    def create_security_agent(model: str = _DEFAULT_LLM_MODEL) -> AIAgent:
        """Agent spécialisé en sécurité et audit de code"""
        system_prompt = """Tu es SecurityAgent, un expert en cybersécurité et audit de code.

EXPERTISE: Sécurité applicative, détection de vulnérabilités, audit de code, OWASP, bonnes pratiques

COMPORTEMENT:
- Analyse le code pour détecter les failles de sécurité
- Identifie les vulnérabilités (injection SQL, XSS, CSRF, etc.)
- Propose des corrections sécurisées
- Vérifie la gestion des données sensibles
- Applique les recommandations OWASP et CWE
- Audite les dépendances et configurations

FORMAT DE RÉPONSE:
- Niveau de risque (Critique/Élevé/Moyen/Faible)
- Vulnérabilités détectées avec description
- Code corrigé et sécurisé
- Recommandations de prévention
- Checklist de sécurité"""

        return AIAgent(
            name="SecurityAgent",
            expertise="Sécurité & Audit",
            system_prompt=system_prompt,
            model=model,
            temperature=0.2,
        )

    @staticmethod
    def create_optimizer_agent(model: str = _DEFAULT_LLM_MODEL) -> AIAgent:
        """Agent spécialisé en optimisation et performance"""
        system_prompt = """Tu es OptimizerAgent, un expert en optimisation et performance logicielle.

EXPERTISE: Optimisation de code, refactoring, performance, profilage, design patterns

COMPORTEMENT:
- Analyse les performances du code
- Identifie les goulots d'étranglement
- Propose des optimisations algorithmiques
- Refactore le code pour une meilleure maintenabilité
- Applique les design patterns appropriés
- Optimise la consommation mémoire et CPU

FORMAT DE RÉPONSE:
- Analyse de complexité (Big O)
- Points d'optimisation identifiés
- Code optimisé avec comparaison avant/après
- Métriques de performance attendues
- Suggestions d'architecture"""

        return AIAgent(
            name="OptimizerAgent",
            expertise="Optimisation & Performance",
            system_prompt=system_prompt,
            model=model,
            temperature=0.3,
        )

    @staticmethod
    def create_datascience_agent(model: str = _DEFAULT_LLM_MODEL) -> AIAgent:
        """Agent spécialisé en data science et machine learning"""
        system_prompt = """Tu es DataScienceAgent, un expert en data science et machine learning.

EXPERTISE: Data science, machine learning, statistiques, modélisation prédictive, visualisation de données

COMPORTEMENT:
- Analyse et prépare les données (nettoyage, feature engineering)
- Sélectionne les modèles ML appropriés
- Propose des pipelines de traitement de données
- Évalue les performances des modèles
- Crée des visualisations pertinentes
- Interprète les résultats statistiques

FORMAT DE RÉPONSE:
- Analyse exploratoire des données
- Choix de modèle justifié
- Code Python avec pandas, scikit-learn, etc.
- Métriques d'évaluation
- Visualisations suggérées
- Interprétation des résultats"""

        return AIAgent(
            name="DataScienceAgent",
            expertise="Data Science & ML",
            system_prompt=system_prompt,
            model=model,
            temperature=0.4,
        )

    @staticmethod
    def create_web_agent(
        model: str = _DEFAULT_LLM_MODEL, focus_year: int = None
    ) -> WebSearchAgent:
        """Agent spécialisé en recherche internet RÉELLE avec fact-checking"""
        return WebSearchAgent(
            name="WebAgent",
            expertise="Recherche Internet & Fact-Checking",
            model=model,
            temperature=0.5,
            focus_year=focus_year,
        )


# Agents pré-configurés disponibles
AVAILABLE_AGENTS = {
    "code": AgentFactory.create_code_agent,
    "web": AgentFactory.create_web_agent,  # 🌐 Agent de recherche internet RÉELLE (remplace research)
    "analyst": AgentFactory.create_analyst_agent,
    "creative": AgentFactory.create_creative_agent,
    "debug": AgentFactory.create_debug_agent,
    "planner": AgentFactory.create_planner_agent,
    "security": AgentFactory.create_security_agent,
    "optimizer": AgentFactory.create_optimizer_agent,
    "datascience": AgentFactory.create_datascience_agent,
}


def create_agent(agent_type: str, model: str = _DEFAULT_LLM_MODEL) -> Optional[AIAgent]:
    """
    Crée un agent du type spécifié

    Args:
        agent_type: Type d'agent (code, web, analyst, creative, debug, planner, security, optimizer, datascience)
        model: Modèle Ollama à utiliser

    Returns:
        Instance de AIAgent ou None si type invalide
    """
    factory_func = AVAILABLE_AGENTS.get(agent_type.lower())
    if factory_func:
        return factory_func(model)
    else:
        print(f"❌ Type d'agent invalide: {agent_type}")
        print(f"Types disponibles: {', '.join(AVAILABLE_AGENTS.keys())}")
        return None
