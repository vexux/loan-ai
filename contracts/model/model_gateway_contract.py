from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict


class ModelGatewayContract(ABC):
    """Contract for a model gateway implementation."""

    @abstractmethod
    async def generate(
        self,
        request: ModelRequest,
    ) -> ModelResponse:
        """
        Generate a model response.
        """
        raise NotImplementedError

    @abstractmethod
    async def health_check(self) -> bool:
        """
        Check whether the configured model is available.
        """
        raise NotImplementedError
