import pytest

from core_agent.decision.llm_decision_engine import (
    LLMDecisionEngine,
)
from core_agent.models.decision import Decision


@pytest.mark.asyncio
async def test_decision_engine_selects_capability():

    engine = LLMDecisionEngine()

    decision = Decision(
        action="query_policy_coverage",
        inputs={
            "topic": "accidental damage"
        },
        rationale=(
            "Retrieve policy information "
            "for accidental damage."
        ),
        confidence=0.95,
    )

    result = await engine.select_capability(
        decision
    )

    print("\n========== CAPABILITY ==========")
    print(result.model_dump_json(indent=2))
    print("================================")

    assert result.capability == (
        "policy_document_search"
    )


@pytest.mark.asyncio
async def test_decision_engine_rejects_unknown_action():

    engine = LLMDecisionEngine()

    decision = Decision(
        action="something_that_does_not_exist"
    )

    with pytest.raises(
        ValueError,
        match="No executable capability found",
    ):
        await engine.select_capability(
            decision
        )