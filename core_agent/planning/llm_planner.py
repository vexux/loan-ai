import json
import re

from components.model_gateway.gateway import ModelGateway
from contracts.common.request_context import RequestContext
from contracts.model.model_request import ModelRequest

from core_agent.models.plan import Plan, PlanStep
from core_agent.models.task_understanding import TaskUnderstanding
from core_agent.planning.planner import Planner


class LLMPlanner(Planner):
    def __init__(
        self,
        model_gateway: ModelGateway,
        available_actions: list[str] | None = None,
        action_descriptions: list[str] | None = None,
        model_name: str = "Qwen/Qwen3-0.6B",
    ):
        self.model_gateway = model_gateway
        self.available_actions = available_actions or [
            "search_documents",
            "retrieve_entity",
            "generate_response",
        ]
        self.action_descriptions = action_descriptions or [
            "- search_documents: Search knowledge base documents for relevant information",
            "- retrieve_entity: Retrieve a structured record or entity by identifier",
            "- generate_response: Synthesize a final answer from retrieved context",
        ]
        self.model_name = model_name

    async def plan(self, understanding: TaskUnderstanding) -> Plan:
        request_context = self._create_context()
        system_prompt = self._build_system_prompt()
        user_prompt = self._build_user_prompt(understanding)

        request = ModelRequest(
            request_context=request_context,
            system_prompt=system_prompt,
            prompt=user_prompt,
            model=self.model_name,
            temperature=0.0,
            max_tokens=800,
        )

        response = await self.model_gateway.generate(request)
        return self._parse_response(response.content, understanding)

    def plan_from_workflow(self, workflow, request_inputs: dict) -> Plan:
        """
        Converts a deterministic WorkflowDefinition into a unified Plan.
        Eliminates the workflow bypass by allowing workflows to run through
        the standard agent lifecycle.
        """
        plan_steps = []
        for s in workflow.steps:
            # Merge workflow step defaults with request-level inputs
            step_inputs = dict(s.inputs)
            step_inputs.update({
                k: v for k, v in request_inputs.items() 
                if k not in {"context", "history"}
            })
            
            plan_steps.append(
                PlanStep(
                    step_id=s.step_id,
                    action=s.action,
                    objective=s.name or s.step_id,
                    dependencies=list(s.dependencies),
                    inputs=step_inputs,
                    condition=s.condition,
                )
            )

        return Plan(
            goal=workflow.description or f"Execute workflow: {workflow.name}",
            steps=plan_steps,
        )

    def _build_system_prompt(self) -> str:
        actions_list = ', '.join([f"'{a}'" for a in self.available_actions])
        descriptions = "\n".join(self.action_descriptions)

        return f"""
You are a planning component inside an AI agent.
Your job is to generate a step-by-step execution plan to accomplish the user's goal.

AVAILABLE ACTIONS:
{descriptions}

You MUST ONLY use actions from this list: [{actions_list}].
ALWAYS include a 'generate_response' step at the end to synthesize the final answer.

Return ONLY valid JSON. No markdown, no explanations, no ```json fences.

JSON SCHEMA:
{{
    "goal": "string",
    "steps": [
        {{
            "step_id": "step_1",
            "action": "one of the available actions",
            "objective": "what this step accomplishes",
            "dependencies": [],
            "inputs": {{}}
        }}
    ]
}}

EXAMPLES:
Example 1: Document/Policy Inquiry
{{
    "goal": "Answer policy question",
    "steps": [
        {{
            "step_id": "step_1",
            "action": "search_documents",
            "objective": "search knowledge base for relevant policy rules",
            "dependencies": [],
            "inputs": {{"query": "policy rules"}}
        }},
        {{
            "step_id": "step_2",
            "action": "generate_response",
            "objective": "synthesize a final answer from retrieved context",
            "dependencies": ["step_1"],
            "inputs": {{}}
        }}
    ]
}}

Example 2: Database Record Lookup
{{
    "goal": "Retrieve a specific record from the database",
    "steps": [
        {{
            "step_id": "step_1",
            "action": "retrieve_entity",
            "objective": "fetch the record by identifier",
            "dependencies": [],
            "inputs": {{}}
        }},
        {{
            "step_id": "step_2",
            "action": "generate_response",
            "objective": "synthesize a final answer from retrieved data",
            "dependencies": ["step_1"],
            "inputs": {{}}
        }}
    ]
}}
""".strip()

    def _build_user_prompt(self, understanding: TaskUnderstanding) -> str:
        return f"Intent: {understanding.intent}\nEntities: {understanding.entities}\nGoal: Generate a plan to satisfy this request."

    def _parse_response(self, content: str, understanding: TaskUnderstanding) -> Plan:
        cleaned = content.strip()
        cleaned = re.sub(r"<think>.*?</think>", "", cleaned, flags=re.DOTALL | re.IGNORECASE).strip()

        match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
        json_str = match.group(0) if match else cleaned

        try:
            data = json.loads(json_str)
        except json.JSONDecodeError as exc:
            raise ValueError(f"LLM returned invalid JSON for Plan: {content}") from exc

        try:
            return Plan.model_validate(data)
        except Exception as exc:
            raise ValueError(f"LLM returned JSON that does not match Plan schema: {data}") from exc

    @staticmethod
    def _create_context() -> RequestContext:
        return RequestContext(
            request_id="planning",
            correlation_id="planning",
            session_id="planning",
            user_id="system",
            tenant_id="system",
        )