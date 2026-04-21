"""Package interfaces.agents — architecture modulaire de la page Agents.

La classe `AgentsInterface` est assemblée dans `interfaces.agents_interface`
à partir des mixins de ce package. Importer depuis ce module reste possible
pour un accès direct aux mixins.
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
from interfaces.agents.syntax_helper import (
    SyntaxColorHelper,
    SYNTAX_ANALYZER,
    SYNTAX_AVAILABLE,
)

__all__ = [
    "BaseMixin",
    "AgentSelectionMixin",
    "DragDropMixin",
    "WorkflowMixin",
    "FileHandlingMixin",
    "TaskInputMixin",
    "OutputAreaMixin",
    "StatsSectionMixin",
    "ExecutionMixin",
    "OutputRenderingMixin",
    "CustomAgentsMixin",
    "DebateMixin",
    "SyntaxColorHelper",
    "SYNTAX_ANALYZER",
    "SYNTAX_AVAILABLE",
]
