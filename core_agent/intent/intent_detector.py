from abc import ABC, abstractmethod

from core_agent.models.task_understanding import TaskUnderstanding


class IntentDetector(ABC):
    """
    Determines what the user is trying to accomplish.
    """

    @abstractmethod
    async def detect(
        self,
        message: str,
        history: str = "",
    ) -> TaskUnderstanding:
        raise NotImplementedError