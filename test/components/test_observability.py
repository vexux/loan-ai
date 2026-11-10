import os
import pytest
from components.observability.tracer import StructuredTracer


@pytest.mark.asyncio
async def test_tracer_parent_child_spans_and_persistence():
    tracer = StructuredTracer(log_dir="logs/test_traces")
    trace_id = "TRC-TEST-001"

    async with tracer.span(trace_id, "ParentComponent", "parent_op", decision={"choice": "A"}):
        async with tracer.span(trace_id, "ChildComponent", "child_op", metadata={"param": 123}):
            pass

    trace = tracer.get_trace(trace_id)
    assert trace is not None
    assert len(trace.spans) == 2

    # Verify parent-child relationship
    child_span = [s for s in trace.spans if s.operation == "child_op"][0]
    parent_span = [s for s in trace.spans if s.operation == "parent_op"][0]

    assert child_span.parent_span_id == parent_span.span_id
    assert child_span.status == "SUCCESS"
    assert parent_span.decision["choice"] == "A"

    # Verify JSON persistence
    saved_path = await tracer.save_trace(trace)
    assert os.path.exists(saved_path)

    # Cleanup
    if os.path.exists(saved_path):
        os.remove(saved_path)
