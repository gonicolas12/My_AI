"""Interface du système d'agents spécialisés — façade assemblant les mixins.

`interfaces.agents`. Cette façade conserve l'import public
`from interfaces.agents_interface import AgentsInterface` pour compatibilité.
"""

from interfaces.agents.base import BaseMixin
from interfaces.agents.agent_selection import AgentSelectionMixin
from interfaces.agents.drag_drop import DragDropMixin
from interfaces.agents.workflow import WorkflowMixin
from interfaces.agents.file_handling import FileHandlingMixin
from interfaces.agents.task_input import TaskInputMixin
from interfaces.agents.output_area import OutputAreaMixin
from interfaces.agents.stats_section import StatsSectionMixin
from interfaces.agents.execution import ExecutionMixin
from interfaces.agents.output_rendering import OutputRenderingMixin
from interfaces.agents.custom_agents import CustomAgentsMixin
from interfaces.agents.debate import DebateMixin
# Ré-exports publics pour la compatibilité ascendante.
from interfaces.agents.syntax_helper import SyntaxColorHelper, SYNTAX_ANALYZER, SYNTAX_AVAILABLE  # noqa: F401  pylint: disable=unused-import

__all__ = [
    "AgentsInterface",
    "SyntaxColorHelper",
    "SYNTAX_ANALYZER",
    "SYNTAX_AVAILABLE",
]


class AgentsInterface(
    BaseMixin,
    AgentSelectionMixin,
    DragDropMixin,
    WorkflowMixin,
    FileHandlingMixin,
    TaskInputMixin,
    OutputAreaMixin,
    StatsSectionMixin,
    ExecutionMixin,
    OutputRenderingMixin,
    CustomAgentsMixin,
    DebateMixin,
):
    """Interface pour le système d'agents IA spécialisés."""
