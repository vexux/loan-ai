from abc import ABC, abstractmethod

from core_agent.models.decision import Decision


class DecisionEngine(ABC):

    @abstractmethod
    async def select_capability(
        self,
        decision: Decision,
    ) -> Decision:
        raise NotImplementedError