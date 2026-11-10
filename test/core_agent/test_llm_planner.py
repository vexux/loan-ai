import pytest

from components.model_gateway import (
    create_local_model_gateway,
)

from core_agent.models.execution_state import (
    ExecutionState,
)

from core_agent.models.task_understanding import (
    TaskUnderstanding,
)

from core_agent.planning.llm_planner import (
    LLMPlanner,
)


@pytest.mark.asyncio
@pytest.mark.integration
async def test_llm_planner():

    gateway = create_local_model_gateway(
        "Qwen/Qwen3-0.6B"
    )

    planner = LLMPlanner(
        model_gateway=gateway,
        model_name="Qwen/Qwen3-0.6B",
    )

    understanding = TaskUnderstanding(
        intent="policy_coverage_query",
        entities={
            "topic": "accidental damage"
        },
        constraints={},
        requested_output=(
            "Determine whether accidental damage "
            "is covered."
        ),
        confidence=0.9,
    )

    state = ExecutionState(
        request_id="planner-test",
        max_iterations=10,
    )

    state.understanding = understanding

    plan = await planner.plan(state)

    print("\n========== LLM PLAN ==========")
    print(plan.model_dump_json(indent=2))
    print("==============================")

    assert plan.goal
    assert len(plan.steps) > 0

    for step in plan.steps:
        assert step.step_id
        assert step.objective
        assert step.action