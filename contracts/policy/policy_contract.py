from abc import abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List

from contracts.common import ApprovalStatus, ExecutionResult, RequestContext, RiskLevel
from contracts.component import ComponentContract


class PolicyAction(str, Enum):
    ALLOW = "ALLOW"
    DENY = "DENY"
    REQUIRE_APPROVAL = "REQUIRE_APPROVAL"
    MASK_DATA = "MASK_DATA"
    ESCALATE = "ESCALATE"
    CONTINUE_WITH_WARNING = "CONTINUE_WITH_WARNING"


@dataclass
class PolicyRequest:
    context: RequestContext
    action: str
    component_name: str
    input: Dict[str, Any] = field(default_factory=dict)
    output: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PolicyDecision:
    action: PolicyAction
    allowed: bool
    risk_level: RiskLevel
    approval_status: ApprovalStatus
    reasons: List[str] = field(default_factory=list)
    modified_output: Dict[str, Any] = field(default_factory=dict)


class PolicyContract(ComponentContract):

    @abstractmethod
    def evaluate(self, request: PolicyRequest) -> ExecutionResult[PolicyDecision]:
        raise NotImplementedError

    @abstractmethod
    def is_action_allowed(self, action: str) -> bool:
        raise NotImplementedError
