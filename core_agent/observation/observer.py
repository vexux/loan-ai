from abc import ABC, abstractmethod
from typing import Any
from core_agent.models.execution_state import StepExecutionResult


class ObservationResult:
    """
    Describes the outcome of observing an executed plan step.
    """
    def __init__(
        self,
        successful: bool,
        sufficient: bool,
        requires_replanning: bool = False,
        message: str = "",
    ):
        self.successful = successful
        self.sufficient = sufficient
        self.requires_replanning = requires_replanning
        self.message = message


class Observer(ABC):
    @abstractmethod
    async def observe(self, result: StepExecutionResult) -> ObservationResult:
        raise NotImplementedError


class ExecutionObserver(Observer):
    """
    Evaluates execution success and verifies that the step produced 
    substantive data, preventing downstream hallucinations.
    """

    async def observe(self, result: StepExecutionResult) -> ObservationResult:
        # 1. Technical execution failure
        if not result.success:
            return ObservationResult(
                successful=False,
                sufficient=False,
                requires_replanning=False,  # Kept False for now; hook ready for future replanning
                message=f"Step '{result.step_id}' failed: {result.error}",
            )

        output = result.output
        
        if isinstance(output, dict):
            data_block = output.get("data", {})
            if isinstance(data_block, dict) and "records" in data_block:
                if len(data_block["records"]) == 0 and data_block.get("count", 0) == 0:
                    return ObservationResult(
                        successful=True,
                        sufficient=False,
                        requires_replanning=False,
                        message=f"Step '{result.step_id}' executed but found 0 matching records.",
                    )

            content = str(output.get("content", "")).strip().lower()
            if "no records found" in content or "no relevant information found" in content:
                return ObservationResult(
                    successful=True,
                    sufficient=False,
                    requires_replanning=False,
                    message=f"Step '{result.step_id}' returned no usable content.",
                )

        return ObservationResult(
            successful=True,
            sufficient=True,
            requires_replanning=False,
            message=f"Step '{result.step_id}' completed with valid output.",
        )
