from abc import ABC, abstractmethod

from contracts.model.model_request import ModelRequest
from contracts.model.model_response import ModelResponse


class ModelProvider(ABC):
    """
    Internal abstraction for a concrete model provider.

    Examples:
        LocalTransformersProvider
        Future APIProvider
        Future VLLMProvider
    """

    @abstractmethod
    async def generate(
        self,
        request: ModelRequest,
    ) -> ModelResponse:
        raise NotImplementedError

    @abstractmethod
    async def health_check(self) -> bool:
        raise NotImplementedError