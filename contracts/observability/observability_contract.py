from abc import ABC, abstractmethod
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, AsyncIterator, Optional


@dataclass
class Span:
    span_id: str
    trace_id: str
    component: str
    operation: str
    parent_span_id: Optional[str] = None
    status: str = "RUNNING"  # SUCCESS, FAILED, SKIPPED, BLOCKED_BY_POLICY
    duration_ms: Optional[float] = None
    decision: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    error_code: str = ""
    error_message: str = ""
    start_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class Trace:
    trace_id: str
    request_id: str
    spans: list[Span] = field(default_factory=list)
    status: str = "SUCCESS"
    total_duration_ms: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class ObservabilityContract(ABC):

    @abstractmethod
    async def record_span(self, span: Span) -> None:
        raise NotImplementedError

    @abstractmethod
    async def save_trace(self, trace: Trace) -> str:
        raise NotImplementedError

    @abstractmethod
    def get_trace(self, trace_id: str) -> Optional[Trace]:
        raise NotImplementedError

    @abstractmethod
    @asynccontextmanager
    async def span(
        self,
        trace_id: str,
        component: str,
        operation: str,
        decision: Optional[dict[str, Any]] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> AsyncIterator[Span]:
        raise NotImplementedError
