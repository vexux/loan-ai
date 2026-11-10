from typing import Any
import inspect

from components.tool_registry.tool_registry import ToolRegistry
from core_agent.execution.execution_controller import ExecutionController
from core_agent.models.decision import Decision


class RegistryExecutionController(ExecutionController):
    """
    Executes capabilities that have been resolved and validated by the DecisionEngine.
    Handles async/sync dispatch and execution error containment.
    """

    def __init__(self, tool_registry: ToolRegistry) -> None:
        self.tool_registry = tool_registry

    async def execute(self, decision: Decision) -> Any:
        handler = getattr(decision, "handler", None)

        # Fallback lookup if handler was not pre-bound by decision engine
        if handler is None:
            capability = self.tool_registry.find_by_action(decision.action)
            handler = capability.handler if capability else None

        if handler is None:
            return {
                "status": "failure",
                "error": f"No executable handler registered for action '{decision.action}'",
                "content": None,
            }

        try:
            if inspect.iscoroutinefunction(handler):
                result = await handler(decision.inputs)
            else:
                result = handler(decision.inputs)

            return result

        except Exception as exc:
            return {
                "status": "failure",
                "error": f"Execution of '{decision.action}' failed: {str(exc)}",
                "content": None,
            }