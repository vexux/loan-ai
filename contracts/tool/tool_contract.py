from abc import abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict

from contracts.common import ExecutionResult, RequestContext
from contracts.component import ComponentContract


@dataclass
class ToolRequest:
    context: RequestContext
    tool_name: str
    intent: str
    input: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ToolResponse:
    tool_name: str
    successful: bool
    output: Dict[str, Any] = field(default_factory=dict)
    message: str = ""
    error_code: str = ""


class ToolContract(ComponentContract):

    @abstractmethod
    def execute(self, request: ToolRequest) -> ExecutionResult[ToolResponse]:
        raise NotImplementedError

    @abstractmethod
    def validate_input(self, request: ToolRequest) -> bool:
        raise NotImplementedError
