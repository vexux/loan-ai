from abc import ABC, abstractmethod
from typing import Any

from core_agent.models.decision import Decision


class ExecutionController(ABC):
    """
    Executes a selected capability.

    The Agent Core does not know how the capability is implemented.
    """

    @abstractmethod
    async def execute(
        self,
        decision: Decision,
    ) -> Any:
        raise NotImplementedError