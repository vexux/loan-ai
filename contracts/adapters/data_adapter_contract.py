from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from contracts.common.execution_result import ExecutionResult   # ← fixed path


@dataclass
class DataQuery:
    resource: str
    filters: dict[str, Any] = field(default_factory=dict)
    fields: list[str] = field(default_factory=list)
    limit: int = 100
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class DataResult:
    records: list[dict[str, Any]] = field(default_factory=list)
    total: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


class DataAdapterContract(ABC):

    @abstractmethod
    async def query(self, request: DataQuery) -> ExecutionResult[DataResult]:
        raise NotImplementedError

    @abstractmethod
    async def get_by_id(self, resource: str, resource_id: str) -> ExecutionResult[DataResult]:
        raise NotImplementedError
