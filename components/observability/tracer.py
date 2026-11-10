import asyncio
import json
import os
import time
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any, AsyncIterator, Optional
from uuid import uuid4

from contracts.observability.observability_contract import ObservabilityContract, Span, Trace


class StructuredTracer(ObservabilityContract):
    """
    Domain-agnostic tracer implementing ObservabilityContract.
    Supports parent/child spans, decision recording, and file-based JSON persistence.
    """

    def __init__(self, log_dir: str = "logs/traces") -> None:
        self.log_dir = os.path.abspath(log_dir)
        os.makedirs(self.log_dir, exist_ok=True)
        self._traces: dict[str, Trace] = {}
        self._active_spans: dict[str, list[str]] = {}  # trace_id -> stack of span_ids

    async def record_span(self, span: Span) -> None:
        if span.trace_id not in self._traces:
            self._traces[span.trace_id] = Trace(trace_id=span.trace_id, request_id=span.trace_id)
        self._traces[span.trace_id].spans.append(span)

    @asynccontextmanager
    async def span(
        self,
        trace_id: str,
        component: str,
        operation: str,
        decision: Optional[dict[str, Any]] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> AsyncIterator[Span]:
        span_id = f"SPN-{uuid4().hex[:6]}"
        
        stack = self._active_spans.setdefault(trace_id, [])
        parent_span_id = stack[-1] if stack else None
        stack.append(span_id)

        start_time = time.perf_counter()
        span_obj = Span(
            span_id=span_id,
            trace_id=trace_id,
            component=component,
            operation=operation,
            parent_span_id=parent_span_id,
            decision=decision or {},
            metadata=metadata or {},
        )

        try:
            yield span_obj
            span_obj.status = "SUCCESS"
        except Exception as exc:
            span_obj.status = "FAILED"
            span_obj.error_code = type(exc).__name__
            span_obj.error_message = str(exc)
            raise
        finally:
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            span_obj.duration_ms = round(elapsed_ms, 2)
            await self.record_span(span_obj)
            if stack and stack[-1] == span_id:
                stack.pop()

    async def save_trace(self, trace: Trace) -> str:
        total_duration = sum(s.duration_ms or 0 for s in trace.spans)
        trace.total_duration_ms = round(total_duration, 2)
        
        # Preserve caller's FAILED status or mark failed if any span failed
        has_errors = any(s.status == "FAILED" for s in trace.spans)
        if has_errors or trace.status == "FAILED":
            trace.status = "FAILED"
        else:
            trace.status = "SUCCESS"

        trace_data = {
            "trace_id": trace.trace_id,
            "request_id": trace.request_id,
            "status": trace.status,
            "total_duration_ms": trace.total_duration_ms,
            "timestamp": trace.created_at.isoformat(),
            "total_spans": len(trace.spans),
            "spans": [
                {
                    "span_id": s.span_id,
                    "parent_span_id": s.parent_span_id,
                    "component": s.component,
                    "operation": s.operation,
                    "status": s.status,
                    "duration_ms": s.duration_ms,
                    "decision": s.decision,
                    "metadata": s.metadata,
                    "error_code": s.error_code,
                    "error_message": s.error_message,
                }
                for s in trace.spans
            ],
        }

        file_path = os.path.join(self.log_dir, f"{trace.trace_id}.json")
        
        def _write_file():
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(trace_data, f, indent=2)

        await asyncio.to_thread(_write_file)
        return file_path

    def get_trace(self, trace_id: str) -> Optional[Trace]:
        return self._traces.get(trace_id)
