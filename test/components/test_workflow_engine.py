import pytest
from components.tool_registry.capability import CapabilityDefinition
from components.tool_registry.tool_registry import ToolRegistry
from components.workflow.workflow_definition import EnhancedWorkflowStep, WorkflowDefinition
from components.workflow.workflow_engine import WorkflowEngine
from contracts.common.request_context import RequestContext
from contracts.workflow.workflow_contract import WorkflowRequest


@pytest.mark.asyncio
async def test_workflow_batching_and_execution():
    registry = ToolRegistry()

    async def mock_step_a(inputs):
        return {"status": "success", "content": "Step A output", "data": {"val_a": 10}}

    async def mock_step_b(inputs):
        return {"status": "success", "content": "Step B output", "data": {"val_b": 20}}

    async def mock_step_c(inputs):
        val_a = inputs.get("val_a", 0)
        val_b = inputs.get("val_b", 0)
        return {"status": "success", "content": f"Sum is {val_a + val_b}"}

    registry.register(CapabilityDefinition(action="step_a", name="StepA", description="A", handler=mock_step_a))
    registry.register(CapabilityDefinition(action="step_b", name="StepB", description="B", handler=mock_step_b))
    registry.register(CapabilityDefinition(action="step_c", name="StepC", description="C", handler=mock_step_c))

    wf = WorkflowDefinition(
        workflow_id="test_wf",
        name="Test Workflow",
        description="Tests parallel and dependency resolution",
        steps=[
            EnhancedWorkflowStep(step_id="a", action="step_a", parallel_group="group_1", dependencies=[]),
            EnhancedWorkflowStep(step_id="b", action="step_b", parallel_group="group_1", dependencies=[]),
            EnhancedWorkflowStep(step_id="c", action="step_c", dependencies=["a", "b"]),
        ],
    )

    engine = WorkflowEngine(tool_registry=registry)
    engine.register(wf)

    req = WorkflowRequest(
        context=RequestContext(request_id="1", session_id="1", correlation_id="1", user_id="u1", tenant_id="t1"),
        workflow_name="test_wf",
        intent="test_wf",
    )
    res = await engine.execute(req)

    assert res.success is True
    assert res.data.successful is True
    assert len(res.data.executed_steps) == 3
    assert "Sum is 30" in res.data.message
