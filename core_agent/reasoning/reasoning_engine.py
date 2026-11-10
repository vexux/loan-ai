from abc import ABC, abstractmethod

from core_agent.models.decision import Decision
from core_agent.models.execution_state import ExecutionState


class ReasoningEngine(ABC):
    """
    Evaluates the current execution state and produces a decision.
    """

    @abstractmethod
    async def reason(
        self,
        state: ExecutionState,
    ) -> Decision:
        raise NotImplementedError