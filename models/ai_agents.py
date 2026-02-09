"""
Système d'Agents IA Spécialisés basés sur Ollama
Chaque agent a une expertise et un comportement spécifique
"""

from typing import Dict, List, Optional, Any
from datetime import datetime

from models.local_llm import LocalLLM


class AIAgent:
    """
    Agent IA de base avec expertise spécialisée
    """

    def __init__(
        self,
        name: str,
        expertise: str,
        system_prompt: str,
        model: str = "llama3.2",
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


class AgentFactory:
    """
    Factory pour créer des agents pré-configurés
    """

    @staticmethod
    def create_code_agent(model: str = "llama3.2") -> AIAgent:
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
    def create_research_agent(model: str = "llama3.2") -> AIAgent:
        """Agent spécialisé en recherche et documentation"""
        system_prompt = """Tu es ResearchAgent, un chercheur et documentaliste expert.

EXPERTISE: Recherche d'information, synthèse, documentation technique, veille technologique

COMPORTEMENT:
- Recherche des informations précises et vérifiables
- Synthétise les sources multiples
- Cite les références quand possible
- Structure l'information de manière claire
- Fait la distinction entre faits et opinions

FORMAT DE RÉPONSE:
- Titre clair
- Points clés en bullet points
- Sources et références
- Conclusion concise"""

        return AIAgent(
            name="ResearchAgent",
            expertise="Recherche & Documentation",
            system_prompt=system_prompt,
            model=model,
            temperature=0.5,
        )

    @staticmethod
    def create_analyst_agent(model: str = "llama3.2") -> AIAgent:
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
    def create_creative_agent(model: str = "llama3.2") -> AIAgent:
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
    def create_debug_agent(model: str = "llama3.2") -> AIAgent:
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
    def create_planner_agent(model: str = "llama3.2") -> AIAgent:
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
    def create_security_agent(model: str = "llama3.2") -> AIAgent:
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
    def create_optimizer_agent(model: str = "llama3.2") -> AIAgent:
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
    def create_datascience_agent(model: str = "llama3.2") -> AIAgent:
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


# Agents pré-configurés disponibles
AVAILABLE_AGENTS = {
    "code": AgentFactory.create_code_agent,
    "research": AgentFactory.create_research_agent,
    "analyst": AgentFactory.create_analyst_agent,
    "creative": AgentFactory.create_creative_agent,
    "debug": AgentFactory.create_debug_agent,
    "planner": AgentFactory.create_planner_agent,
    "security": AgentFactory.create_security_agent,
    "optimizer": AgentFactory.create_optimizer_agent,
    "datascience": AgentFactory.create_datascience_agent,
}


def create_agent(agent_type: str, model: str = "llama3.2") -> Optional[AIAgent]:
    """
    Crée un agent du type spécifié

    Args:
        agent_type: Type d'agent (code, research, analyst, creative, debug, planner)
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
