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

from core_agent.reasoning.llm_reasoning_engine import (
    LLMReasoningEngine,
)


@pytest.mark.asyncio
@pytest.mark.integration
async def test_llm_reasoning_engine():

    gateway = create_local_model_gateway(
        "Qwen/Qwen3-0.6B"
    )

    planner = LLMPlanner(
        model_gateway=gateway,
        model_name="Qwen/Qwen3-0.6B",
    )

    reasoning_engine = LLMReasoningEngine(
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
        request_id="reasoning-test",
        max_iterations=10,
    )

    state.understanding = understanding

    # Create a plan first.
    state.plan = await planner.plan(state)

    # Select the first step.
    state.current_step = state.plan.steps[0]

    decision = await reasoning_engine.reason(
        state
    )

    print("\n========== LLM DECISION ==========")
    print(decision.model_dump_json(indent=2))
    print("==================================")

    assert decision.action != "complete"
    assert 0.0 <= decision.confidence <= 1.0