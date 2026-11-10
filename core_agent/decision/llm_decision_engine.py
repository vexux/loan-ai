from components.tool_registry.tool_registry import ToolRegistry
from core_agent.decision.decision_engine import DecisionEngine
from core_agent.models.decision import Decision


class LLMDecisionEngine(DecisionEngine):
    """
    Resolves an abstract action into a concrete, executable capability.
    Normalizes string artifacts and validates capability existence in the ToolRegistry.
    """

    def __init__(self, tool_registry: ToolRegistry) -> None:
        self.tool_registry = tool_registry

    @staticmethod
    def _normalize_action(action: str) -> str:
        """Clean up whitespace or accidental LLM return prefixes."""
        action = action.strip()
        if action.lower().startswith("return "):
            action = action[7:].strip().strip("\"'")
        return action

    async def select_capability(self, decision: Decision) -> Decision:
        action = self._normalize_action(decision.action)
        capability = self.tool_registry.find_by_action(action)

        if capability is None:
            available = self.tool_registry.get_available_actions()
            raise ValueError(
                f"No executable capability found for action: '{action}'. "
                f"Registered actions: {available}"
            )

        decision.action = action
        decision.capability = capability.name

        return decision
