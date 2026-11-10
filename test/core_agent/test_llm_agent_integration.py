import pytest

from core_agent.bootstrap import create_llm_agent
from core_agent.models.agent_request import AgentRequest


@pytest.mark.asyncio
@pytest.mark.integration
async def test_llm_agent_end_to_end():

    agent = create_llm_agent()

    request = AgentRequest(
        message=(
            "Is accidental damage covered "
            "under my policy?"
        )
    )

    response = await agent.run(request)

    print("\n")
    print("==========================================")
    print("       LLM AGENT INTEGRATION TEST")
    print("==========================================")
    print(f"Success: {response.success}")
    print(f"Intent: {response.intent}")
    print(
        f"Completed steps: "
        f"{response.completed_steps}"
    )
    print(f"Message: {response.message}")

    if response.error:
        print(f"Error: {response.error}")

    print("==========================================")
    print()

    assert response.success is True

    assert response.intent is not None

    assert len(response.completed_steps) > 0