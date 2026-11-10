import json
import re

from components.model_gateway.gateway import ModelGateway
from contracts.common.request_context import RequestContext
from contracts.model.model_request import ModelRequest

from core_agent.intent.intent_detector import IntentDetector
from core_agent.models.task_understanding import TaskUnderstanding


class LLMIntentDetector(IntentDetector):
    """
    100% Pure Neural SLM Intent Detector (Zero regex fast-paths).
    Optimized via Micro-Prompting to run in ~2-3 seconds on CPU.
    """

    def __init__(
        self,
        model_gateway: ModelGateway,
        model_name: str = "Llama-3.2-3B-Instruct",
        allowed_intents: list[str] | dict[str, str] | None = None,
    ):
        self.model_gateway = model_gateway
        self.model_name = model_name
        self.intents_dict = {}
        if isinstance(allowed_intents, dict):
            self.intents_dict = allowed_intents
            self.intents_list = list(allowed_intents.keys())
        elif isinstance(allowed_intents, list):
            self.intents_list = allowed_intents
        else:
            self.intents_list = ["general_inquiry"]


    async def detect(
        self,
        message: str,
        history: str = "",
    ) -> TaskUnderstanding:
        #Build system prompt from descriptions if provided (injected by domain layer via bootstrap)
        if self.intents_dict:
            intent_lines = [f"- {k}: {v}" for k, v in self.intents_dict.items()]
            intents_str = "\n".join(intent_lines)
            system_prompt = (
                "You are a fast intent classifier for an AI agent platform.\n"
                f"Classify the user message into EXACTLY ONE intent from this list:\n{intents_str}\n- general_inquiry: fallback for anything else\n\n"
                "Respond ONLY with a JSON object: {\"intent\": \"<intent_name>\"}."
            )
        else:
            intents_str = ", ".join(self.intents_list)
            system_prompt = (
                "You are a fast intent classifier for an AI agent platform. "
                f"Classify the user message into EXACTLY ONE intent from this list: [{intents_str}, general_inquiry]. "
                "Respond ONLY with a JSON object: {\"intent\": \"<intent_name>\"}."
            )


        user_content = message
        if history.strip():
            user_content = f"Recent Context:\n{history.strip()}\n\nUser: {message}"

        # max_tokens=25 is plenty for {"intent": "..."}
        request = ModelRequest(
            request_context=self._create_context(),
            system_prompt=system_prompt,
            prompt=user_content,
            model=self.model_name,
            temperature=0.0,
            max_tokens=25,
        )

        # 100% Pure SLM generation
        response = await self.model_gateway.generate(request)
        return self._parse_response(response.content)

    @staticmethod
    def _parse_response(content: str) -> TaskUnderstanding:
        cleaned = content.strip()
        cleaned = re.sub(r"<think>.*?</think>", "", cleaned, flags=re.DOTALL | re.IGNORECASE).strip()

        match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
        json_str = match.group(0) if match else cleaned

        try:
            data = json.loads(json_str)
            intent = data.get("intent", "general_inquiry")
            return TaskUnderstanding(intent=intent, confidence=0.90, entities={})
        except Exception:
            intent_match = re.search(r'"intent"\s*:\s*"([^"]+)"', cleaned)
            intent = intent_match.group(1) if intent_match else "general_inquiry"
            return TaskUnderstanding(intent=intent, confidence=0.80, entities={})

    @staticmethod
    def _create_context() -> RequestContext:
        return RequestContext(
            request_id="intent-slm",
            correlation_id="intent-slm",
            session_id="intent-slm",
            user_id="system",
            tenant_id="default",
        )
