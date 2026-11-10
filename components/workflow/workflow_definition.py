from dataclasses import dataclass, field
from typing import Any, Callable, Optional


@dataclass
class EnhancedWorkflowStep:
    """
    A single step in a workflow.
    """
    step_id: str
    action: str                           # Registered tool action name
    name: str = ""
    inputs: dict[str, Any] = field(default_factory=dict)
    dependencies: list[str] = field(default_factory=list)
    parallel_group: Optional[str] = None  # Steps with same group run in parallel
    condition: Optional[Callable[[dict[str, Any]], bool]] = None
    requires_approval: bool = False


@dataclass
class WorkflowDefinition:
    workflow_id: str
    name: str
    description: str
    steps: list[EnhancedWorkflowStep]
    trigger_intents: list[str] = field(default_factory=list)
    primary_intent: str = ""
    is_write_operation: bool = False
    is_self_operation: bool = False
    requires_auth: bool = False     
    input_schema: dict = field(default_factory=dict)