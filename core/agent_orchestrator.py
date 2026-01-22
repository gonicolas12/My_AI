"""
Agent Orchestrator - Coordonne les agents IA pour des tâches complexes
Permet la collaboration entre plusieurs agents
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
import json

from models.ai_agents import AIAgent, create_agent, AVAILABLE_AGENTS


class AgentOrchestrator:
    """
    Orchestrateur qui coordonne plusieurs agents IA
    pour résoudre des tâches complexes
    """

    def __init__(self, model: str = "llama3.2"):
        """
        Initialise l'orchestrateur

        Args:
            model: Modèle Ollama à utiliser pour tous les agents
        """
        self.model = model
        self.agents: Dict[str, AIAgent] = {}
        self.task_history: List[Dict[str, Any]] = []

        print("🎯 Agent Orchestrator initialisé")

    def get_or_create_agent(self, agent_type: str) -> Optional[AIAgent]:
        """
        Récupère un agent existant ou en crée un nouveau

        Args:
            agent_type: Type d'agent

        Returns:
            Instance de AIAgent ou None
        """
        if agent_type not in self.agents:
            agent = create_agent(agent_type, self.model)
            if agent:
                self.agents[agent_type] = agent
                return agent
            return None
        return self.agents[agent_type]

    def execute_single_task(
        self, agent_type: str, task: str, context: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Exécute une tâche avec un seul agent

        Args:
            agent_type: Type d'agent à utiliser
            task: Description de la tâche
            context: Contexte additionnel

        Returns:
            Résultat de l'agent
        """
        print(f"\n🎯 Tâche simple: {agent_type}")
        print(f"📋 {task[:100]}...")

        agent = self.get_or_create_agent(agent_type)
        if not agent:
            return {
                "success": False,
                "error": f"Agent type '{agent_type}' invalide",
                "available_agents": list(AVAILABLE_AGENTS.keys()),
            }

        # Exécuter la tâche
        result = agent.execute_task(task, context)

        # Enregistrer dans l'historique
        self._record_task(agent_type, task, result)

        return result

    def execute_single_task_stream(
        self, agent_type: str, task: str, context: Optional[Dict] = None, on_token=None
    ) -> Dict[str, Any]:
        """
        Exécute une tâche avec un seul agent en mode streaming

        Args:
            agent_type: Type d'agent à utiliser
            task: Description de la tâche
            context: Contexte additionnel
            on_token: Callback pour affichage progressif

        Returns:
            Résultat de l'agent
        """
        print(f"\n🎯 Tâche simple: {agent_type}")
        print(f"📋 {task[:100]}...")

        agent = self.get_or_create_agent(agent_type)
        if not agent:
            return {
                "success": False,
                "error": f"Agent type '{agent_type}' invalide",
                "available_agents": list(AVAILABLE_AGENTS.keys()),
            }

        # Exécuter la tâche avec streaming
        result = agent.execute_task_stream(task, context, on_token)

        # Enregistrer dans l'historique
        self._record_task(agent_type, task, result)

        return result

    def execute_multi_agent_task(
        self, task_description: str, workflow: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Exécute une tâche complexe avec plusieurs agents en séquence

        Args:
            task_description: Description générale de la tâche
            workflow: Liste de steps [{"agent": "type", "task": "description", "pass_result": bool}]

        Returns:
            Résultats agrégés de tous les agents

        Example:
            workflow = [
                {"agent": "planner", "task": "Planifie le développement d'une API REST", "pass_result": True},
                {"agent": "code", "task": "Génère le code selon le plan", "pass_result": True},
                {"agent": "debug", "task": "Vérifie et corrige le code", "pass_result": False}
            ]
        """
        print(f"\n🎯 Tâche Multi-Agent: {task_description}")
        print(f"👥 Agents impliqués: {len(workflow)}")

        results = []
        context = {"original_task": task_description}

        for step_idx, step in enumerate(workflow, 1):
            agent_type = step["agent"]
            task = step["task"]
            pass_result = step.get("pass_result", False)

            print(f"\n--- Étape {step_idx}/{len(workflow)}: {agent_type.upper()} ---")

            # Si pass_result=True, inclure le résultat précédent dans le contexte
            if pass_result and results:
                previous_result = results[-1]
                context["previous_step"] = {
                    "agent": previous_result["agent"],
                    "result": previous_result.get("result", ""),
                }

            # Exécuter la tâche
            result = self.execute_single_task(agent_type, task, context)
            results.append(result)

            # Si une étape échoue, on peut choisir de continuer ou arrêter
            if not result.get("success"):
                print(f"⚠️ Étape {step_idx} échouée, poursuite du workflow...")

        # Enregistrer dans l'historique
        self._record_multi_agent_task(task_description, workflow, results)

        return {
            "success": True,
            "task_description": task_description,
            "workflow": workflow,
            "results": results,
            "summary": self._generate_summary(results),
            "timestamp": datetime.now().isoformat(),
        }

    def execute_multi_agent_task_stream(
        self,
        task_description: str,
        workflow: List[Dict[str, Any]],
        on_step_start=None,
        on_token=None,
        on_step_complete=None,
    ) -> Dict[str, Any]:
        """
        Exécute une tâche complexe avec plusieurs agents en séquence avec streaming

        Args:
            task_description: Description générale de la tâche
            workflow: Liste de steps [{"agent": "type", "task": "description", "pass_result": bool}]
            on_step_start: Callback appelé au début de chaque étape (step_idx, agent_type, task)
            on_token: Callback pour chaque token généré
            on_step_complete: Callback appelé à la fin de chaque étape (step_idx, result)

        Returns:
            Résultats agrégés de tous les agents
        """
        print(f"\n🎯 Tâche Multi-Agent: {task_description}")
        print(f"👥 Agents impliqués: {len(workflow)}")

        results = []
        context = {"original_task": task_description}

        for step_idx, step in enumerate(workflow, 1):
            agent_type = step["agent"]
            task = step["task"]
            pass_result = step.get("pass_result", False)

            print(f"\n--- Étape {step_idx}/{len(workflow)}: {agent_type.upper()} ---")

            # Callback de début d'étape
            if on_step_start:
                on_step_start(step_idx, agent_type, task)

            # Si pass_result=True, inclure le résultat précédent dans le contexte
            if pass_result and results:
                previous_result = results[-1]
                context["previous_step"] = {
                    "agent": previous_result["agent"],
                    "result": previous_result.get("result", ""),
                }

            # Exécuter la tâche avec streaming
            result = self.execute_single_task_stream(agent_type, task, context, on_token)
            results.append(result)

            # Callback de fin d'étape
            if on_step_complete:
                on_step_complete(step_idx, result)

            # Si une étape échoue, on peut choisir de continuer ou arrêter
            if not result.get("success"):
                print(f"⚠️ Étape {step_idx} échouée, poursuite du workflow...")

        # Enregistrer dans l'historique
        self._record_multi_agent_task(task_description, workflow, results)

        return {
            "success": True,
            "task_description": task_description,
            "workflow": workflow,
            "results": results,
            "summary": self._generate_summary(results),
            "timestamp": datetime.now().isoformat(),
        }

    def execute_parallel_tasks(
        self, tasks: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Exécute plusieurs tâches en parallèle avec différents agents

        Args:
            tasks: Liste de tâches [{"agent": "type", "task": "description", "context": {...}}]

        Returns:
            Résultats de toutes les tâches
        """
        print(f"\n🎯 Tâches Parallèles: {len(tasks)} agents")

        results = []
        for task_spec in tasks:
            agent_type = task_spec["agent"]
            task = task_spec["task"]
            context = task_spec.get("context")

            result = self.execute_single_task(agent_type, task, context)
            results.append(result)

        return {
            "success": True,
            "parallel_execution": True,
            "tasks_count": len(tasks),
            "results": results,
            "summary": self._generate_summary(results),
            "timestamp": datetime.now().isoformat(),
        }

    def ask_agent(
        self, agent_type: str, question: str, context: Optional[Dict] = None
    ) -> str:
        """
        Interface simple pour poser une question à un agent

        Args:
            agent_type: Type d'agent
            question: Question à poser
            context: Contexte additionnel

        Returns:
            Réponse de l'agent (texte)
        """
        result = self.execute_single_task(agent_type, question, context)

        if result.get("success"):
            return result.get("result", "")
        else:
            return f"❌ Erreur: {result.get('error', 'Inconnue')}"

    def get_agent_stats(self, agent_type: Optional[str] = None) -> Dict[str, Any]:
        """
        Récupère les statistiques des agents

        Args:
            agent_type: Type d'agent spécifique, ou None pour tous

        Returns:
            Statistiques des agents
        """
        if agent_type:
            agent = self.agents.get(agent_type)
            if agent:
                return agent.get_stats()
            return {"error": f"Agent '{agent_type}' non trouvé"}
        else:
            return {
                agent_type: agent.get_stats()
                for agent_type, agent in self.agents.items()
            }

    def list_available_agents(self) -> List[str]:
        """Liste tous les types d'agents disponibles"""
        return list(AVAILABLE_AGENTS.keys())

    def list_active_agents(self) -> List[str]:
        """Liste les agents actuellement instanciés"""
        return list(self.agents.keys())

    def reset_agent(self, agent_type: str):
        """Réinitialise un agent spécifique"""
        if agent_type in self.agents:
            self.agents[agent_type].reset_history()
            print(f"✅ Agent {agent_type} réinitialisé")
        else:
            print(f"⚠️ Agent {agent_type} non trouvé")

    def reset_all_agents(self):
        """Réinitialise tous les agents"""
        for agent in self.agents.values():
            agent.reset_history()
        print("✅ Tous les agents réinitialisés")

    def _record_task(self, agent_type: str, task: str, result: Dict[str, Any]):
        """Enregistre une tâche dans l'historique"""
        self.task_history.append(
            {
                "type": "single",
                "agent": agent_type,
                "task": task,
                "result": result,
                "timestamp": datetime.now().isoformat(),
            }
        )

    def _record_multi_agent_task(
        self, task_description: str, workflow: List[Dict], results: List[Dict]
    ):
        """Enregistre une tâche multi-agent dans l'historique"""
        self.task_history.append(
            {
                "type": "multi_agent",
                "task_description": task_description,
                "workflow": workflow,
                "results": results,
                "timestamp": datetime.now().isoformat(),
            }
        )

    def _generate_summary(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Génère un résumé des résultats"""
        successful = sum(1 for r in results if r.get("success"))
        failed = len(results) - successful

        return {
            "total_tasks": len(results),
            "successful": successful,
            "failed": failed,
            "success_rate": successful / len(results) if results else 0,
        }

    def get_orchestrator_stats(self) -> Dict[str, Any]:
        """Statistiques de l'orchestrateur"""
        return {
            "total_tasks": len(self.task_history),
            "active_agents": len(self.agents),
            "available_agent_types": len(AVAILABLE_AGENTS),
            "agents": list(self.agents.keys()),
        }

    def export_session(self, filepath: str):
        """Exporte la session (historique + stats) vers un fichier JSON"""
        session_data = {
            "orchestrator_stats": self.get_orchestrator_stats(),
            "agent_stats": self.get_agent_stats(),
            "task_history": self.task_history,
            "exported_at": datetime.now().isoformat(),
        }

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(session_data, f, indent=2, ensure_ascii=False)

        print(f"✅ Session exportée: {filepath}")


# Workflows pré-configurés pour tâches courantes
class WorkflowTemplates:
    """Templates de workflows multi-agents courants"""

    @staticmethod
    def code_development(project_description: str) -> tuple[str, List[Dict]]:
        """Workflow complet de développement logiciel"""
        return (
            project_description,
            [
                {
                    "agent": "planner",
                    "task": f"Planifie le développement: {project_description}",
                    "pass_result": True,
                },
                {
                    "agent": "code",
                    "task": "Génère le code selon le plan",
                    "pass_result": True,
                },
                {
                    "agent": "debug",
                    "task": "Vérifie et corrige le code généré",
                    "pass_result": True,
                },
            ],
        )

    @staticmethod
    def research_and_document(topic: str) -> tuple[str, List[Dict]]:
        """Workflow de recherche et documentation"""
        return (
            f"Recherche et documentation sur: {topic}",
            [
                {
                    "agent": "research",
                    "task": f"Recherche approfondie sur: {topic}",
                    "pass_result": True,
                },
                {
                    "agent": "analyst",
                    "task": "Analyse les informations recueillies",
                    "pass_result": True,
                },
                {
                    "agent": "creative",
                    "task": "Rédige un document structuré et clair",
                    "pass_result": False,
                },
            ],
        )

    @staticmethod
    def debug_and_fix(code: str, error: str) -> tuple[str, List[Dict]]:
        """Workflow de debug et correction"""
        return (
            "Debug et correction de code",
            [
                {
                    "agent": "debug",
                    "task": f"Analyse l'erreur: {error}\nCode: {code[:500]}",
                    "pass_result": True,
                },
                {
                    "agent": "code",
                    "task": "Génère le code corrigé",
                    "pass_result": False,
                },
            ],
        )
