from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from contracts.common.enums import ApprovalStatus, RiskLevel
from contracts.policy import PolicyAction


@dataclass
class PolicyRule:
    """
    Domain-agnostic policy rule.
    """
    rule_id: str
    description: str
    target_action: str  # Action name (e.g. "search_documents", "transfer_funds", "*")
    policy_action: PolicyAction = PolicyAction.ALLOW
    risk_level: RiskLevel = RiskLevel.LOW
    approval_status: ApprovalStatus = ApprovalStatus.NOT_REQUIRED
    # Custom condition callable: condition(inputs: dict) -> bool
    condition: Optional[Callable[[dict[str, Any]], bool]] = None
    reasons: list[str] = field(default_factory=list)
