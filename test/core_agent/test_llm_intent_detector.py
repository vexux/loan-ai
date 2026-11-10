import pytest

from components.model_gateway import (
    create_local_model_gateway,
)

from core_agent.intent.llm_intent_detector import (
    LLMIntentDetector,
)


@pytest.mark.asyncio
@pytest.mark.integration
async def test_llm_intent_detector():

    gateway = create_local_model_gateway(
        "Qwen/Qwen3-0.6B"
    )

    detector = LLMIntentDetector(
        model_gateway=gateway,
        model_name="Qwen/Qwen3-0.6B",
    )

    result = await detector.detect(
        "Is accidental damage covered under my policy?"
    )

    print("\n========== INTENT RESULT ==========")
    print(result)
    print("===================================")

    assert result.intent
    assert isinstance(result.entities, dict)
    assert isinstance(result.constraints, dict)
    assert 0.0 <= result.confidence <= 1.0