from abc import ABC, abstractmethod

from core_agent.models.execution_state import ExecutionState
from core_agent.models.plan import Plan

class Planner(ABC):
    """
    Converts task understanding into an executable plan.
    """

    @abstractmethod
    async def plan(
        self,
        state: ExecutionState,
    ) -> Plan:
        raise NotImplementedError