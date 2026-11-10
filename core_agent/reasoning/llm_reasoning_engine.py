import json
import re

from components.model_gateway.gateway import ModelGateway
from components.tool_registry.tool_registry import ToolRegistry
from contracts.common.request_context import RequestContext
from contracts.model.model_request import ModelRequest

from core_agent.models.decision import Decision
from core_agent.models.execution_state import ExecutionState
from core_agent.reasoning.reasoning_engine import ReasoningEngine


class LLMReasoningEngine(ReasoningEngine):
    """
    LLM-backed reasoning engine.

    Determines what should happen next based on the
    current execution state and current plan step.

    BEFORE (tight coupling):
        The system prompt contained a hardcoded list of
        insurance-specific action names.

    AFTER (loose coupling):
        Available actions are fetched from the ToolRegistry
        at runtime and injected into the prompt dynamically.
    """

    def __init__(
        self,
        model_gateway: ModelGateway,
        tool_registry: ToolRegistry,
        model_name: str = "Qwen/Qwen3-0.6B",
    ):
        self.model_gateway = model_gateway
        self.tool_registry = tool_registry
        self.model_name = model_name

    async def reason(
        self,
        state: ExecutionState,
    ) -> Decision:

        if state.current_step is None:
            return Decision(
                action="complete",
                rationale="There is no remaining step.",
                confidence=1.0,
            )

        # ------------------------------------------------------------------
        # GUARDRAIL: If the current step has never been executed, force
        # the action to match the plan step's action. Do NOT ask the LLM.
        # Small SLMs hallucinate that steps are complete when they are not.
        # ------------------------------------------------------------------
        step_id = state.current_step.step_id
        if step_id not in state.step_results:
            return Decision(
                action=state.current_step.action,
                rationale=(
                    f"Step '{step_id}' has not been executed yet. "
                    f"Executing as planned."
                ),
                confidence=1.0,
            )

        # ------------------------------------------------------------------
        # The step HAS been executed. Now ask the LLM what to do next
        # (e.g. did it succeed? Should we replan or proceed?)
        # ------------------------------------------------------------------
        action_descriptions = self.tool_registry.get_action_descriptions()
        system_prompt = self._build_system_prompt(action_descriptions)
        user_prompt = self._build_user_prompt(state)

        request = ModelRequest(
            request_context=self._create_context(state),
            system_prompt=system_prompt,
            prompt=user_prompt,
            model=self.model_name,
            temperature=0.0,
            max_tokens=400,
        )

        response = await self.model_gateway.generate(request)
        return self._parse_response(response.content)


    @staticmethod
    def _build_system_prompt(
        action_descriptions: list[str],
    ) -> str:

        # The action list comes from the registry — not hardcoded.
        actions_block = "\n".join(action_descriptions)

        return f"""
You are the reasoning component of an AI agent.

Your job is to decide what should happen next based on
the current execution state and plan.

Return ONLY valid JSON.

Do not use markdown.
Do not include explanations outside the JSON.
Do not include ```json fences.
Do not include <think> blocks in the final answer.

The JSON must have exactly these fields:

{{
    "action": "string",
    "capability": null,
    "inputs": {{}},
    "rationale": "string",
    "confidence": 0.0,
    "requires_replanning": false
}}

Rules:

- action describes what should happen next.
- capability should always be null (capability selection is handled
  by the DecisionEngine, not the ReasoningEngine).
- inputs contains information required for the action.
- rationale briefly explains the decision.
- confidence must be between 0.0 and 1.0.
- requires_replanning should be true only when the current plan
  cannot continue and a new plan is needed.
- If a current step exists and has not been completed, do NOT
  return "complete".
- Only return "complete" when all required plan steps have
  successfully completed.
- Do not assume that a step has executed unless it appears in
  the execution results.
- If the task cannot continue safely, use action "fail".
- Your action MUST match the action field of the current plan step.
- Do not invent a different action.

REGISTERED ACTIONS (your action must be one of these,
or "complete" / "fail"):
{actions_block}

The current plan step is authoritative.
Your action MUST correspond to the action field of the current step.
""".strip()

    @staticmethod
    def _build_user_prompt(
        state: ExecutionState,
    ) -> str:

        current_step = state.current_step

        step_results = {}
        for step_id, result in state.step_results.items():
            step_results[step_id] = {
                "success": result.success,
                "output": str(result.output),
            }

        return f"""
Determine the next action for the agent.

TASK UNDERSTANDING:
{
    state.understanding.model_dump_json(indent=2)
    if state.understanding
    else "None"
}

CURRENT PLAN:
{
    state.plan.model_dump_json(indent=2)
    if state.plan
    else "None"
}

CURRENT STEP:
{
    current_step.model_dump_json(indent=2)
    if current_step
    else "None"
}

COMPLETED STEPS:
{json.dumps(state.completed_steps, indent=2)}

FAILED STEPS:
{json.dumps(state.failed_steps, indent=2)}

STEP RESULTS:
{json.dumps(step_results, indent=2)}

CURRENT ITERATION:
{state.iteration}

Determine exactly what the Agent should do next.
""".strip()

    @staticmethod
    def _parse_response(content: str) -> Decision:

        cleaned = content.strip()

        cleaned = re.sub(
            r"<think>.*?</think>",
            "",
            cleaned,
            flags=re.DOTALL | re.IGNORECASE,
        )

        cleaned = cleaned.strip()

        cleaned = re.sub(
            r"^```(?:json)?\s*",
            "",
            cleaned,
            flags=re.IGNORECASE,
        )

        cleaned = re.sub(r"\s*```$", "", cleaned)

        cleaned = cleaned.strip()

        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError as exc:
            raise ValueError(
                "LLM returned invalid JSON for Decision."
            ) from exc

        try:
            return Decision.model_validate(data)
        except Exception as exc:
            raise ValueError(
                "LLM returned JSON that does not match "
                "the Decision model."
            ) from exc

    @staticmethod
    def _create_context(state: ExecutionState) -> RequestContext:

        request_id = state.request_id

        return RequestContext(
            request_id=request_id,
            correlation_id=request_id,
            session_id=request_id,
            user_id="system",
            tenant_id="system",
        )
