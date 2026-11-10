from dataclasses import dataclass, field
from datetime import datetime, timezone   # ← Add timezone here
from typing import Any, Optional
from abc import ABC, abstractmethod

from contracts.common.execution_result import ExecutionResult


@dataclass
class MemoryRequest:
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    query: Optional[str] = None
    memory_type: Optional[str] = "conversation"
    limit: int = 10
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class MemoryRecord:
    memory_id: str
    content: str
    memory_type: str = "conversation"
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class MemoryContract(ABC):

    @abstractmethod
    async def save(self, record: MemoryRecord) -> ExecutionResult[MemoryRecord]:
        raise NotImplementedError

    @abstractmethod
    async def retrieve(self, request: MemoryRequest) -> ExecutionResult[list[MemoryRecord]]:
        raise NotImplementedError

    @abstractmethod
    async def delete(self, memory_id: str) -> ExecutionResult[None]:
        raise NotImplementedError
