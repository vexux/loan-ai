from typing import Any
from abc import ABC, abstractmethod
from contracts.common.request_context import RequestContext
from contracts.common.execution_result import ExecutionResult

class ContextManagerContract(ABC):

    @abstractmethod
    async def create(
        self,
        context: RequestContext
    ) -> ExecutionResult[RequestContext]:
        raise NotImplementedError

    @abstractmethod
    async def get(
        self,
        request_id: str
    ) -> ExecutionResult[RequestContext]:
        raise NotImplementedError

    @abstractmethod
    async def update(
        self,
        request_id: str,
        updates: dict[str, Any]
    ) -> ExecutionResult[RequestContext]:
        raise NotImplementedError

    @abstractmethod
    async def delete(
        self,
        request_id: str
    ) -> ExecutionResult[None]:
        raise NotImplementedError