from abc import abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List

from contracts.common import ExecutionResult, RequestContext
from contracts.component import ComponentContract


@dataclass
class WorkflowStep:
    step_id: str
    name: str
    component_name: str
    action: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    requires_approval: bool = False


@dataclass
class WorkflowRequest:
    context: RequestContext
    workflow_name: str
    intent: str
    input: Dict[str, Any] = field(default_factory=dict)


@dataclass
class WorkflowResponse:
    workflow_name: str
    successful: bool
    executed_steps: List[WorkflowStep] = field(default_factory=list)
    output: Dict[str, Any] = field(default_factory=dict)
    message: str = ""


class WorkflowContract(ComponentContract):

    @abstractmethod
    async def execute(self, request: WorkflowRequest) -> ExecutionResult[WorkflowResponse]:
        raise NotImplementedError

    @abstractmethod
    def get_steps(self, workflow_name: str) -> List[WorkflowStep]:
        raise NotImplementedError

    @abstractmethod
    def can_execute(self, request: WorkflowRequest) -> bool:
        raise NotImplementedError
