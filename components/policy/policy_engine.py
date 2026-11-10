from typing import Any, Optional
from contracts.common.enums import ApprovalStatus, ComponentType, ExecutionStatus, RiskLevel
from contracts.common.execution_result import ExecutionResult
from contracts.component.component_metadata import ComponentMetadata
from contracts.policy import (
    PolicyAction,
    PolicyContract,
    PolicyDecision,
    PolicyRequest,
)
from components.policy.rule import PolicyRule


class RuleBasedPolicyEngine(PolicyContract):
    """
    Domain-Agnostic, Enterprise Rule-Based Policy Engine.
    Follows True Governance Architecture:
    - Does not rely on fragile hardcoded 3-item action lists.
    - Evaluates registered compliance, risk, and approval rules against actions.
    - An action is only blocked if an explicit PolicyRule denies it or triggers a violation.
    - Supports optional strict allowlists for regulated environments without breaking dynamic tools.
    """

    def __init__(self, allowed_actions: Optional[list[str]] = None) -> None:
        # None means open to all registered capabilities unless restricted by a rule
        self._strict_allowlist = set(allowed_actions) if allowed_actions is not None else None
        self._rules: list[PolicyRule] = []

    def add_rule(self, rule: PolicyRule) -> None:
        self._rules.append(rule)

    def is_action_allowed(self, action: str) -> bool:
        """
        Implementation of PolicyContract abstract method.
        If an explicit environment allowlist was supplied, enforces it.
        Otherwise permits all registered actions by default (rules govern execution).
        """
        if self._strict_allowlist is not None:
            return action in self._strict_allowlist
        return True

    def evaluate(self, request: PolicyRequest) -> ExecutionResult[PolicyDecision]:
        action = request.action
        inputs = request.input or {}

        # 1. Environment-level strict allowlist (optional compliance enforcement)
        if self._strict_allowlist is not None and action not in self._strict_allowlist:
            decision = PolicyDecision(
                action=PolicyAction.DENY,
                allowed=False,
                risk_level=RiskLevel.HIGH,
                approval_status=ApprovalStatus.REJECTED,
                reasons=[f"Action '{action}' is not permitted by environment policy."],
            )
            return ExecutionResult(
                success=True,
                status=ExecutionStatus.SUCCESS,
                data=decision,
            )

        # 2. Evaluate registered safety and compliance rules defensively
        for rule in self._rules:
            if rule.target_action == action or rule.target_action == "*":
                triggered = False
                if rule.condition:
                    try:
                        triggered = bool(rule.condition(inputs))
                    except Exception:
                        triggered = False

                if triggered:
                    decision = PolicyDecision(
                        action=rule.policy_action,
                        allowed=(rule.policy_action == PolicyAction.ALLOW),
                        risk_level=rule.risk_level,
                        approval_status=rule.approval_status,
                        reasons=rule.reasons or [f"Triggered rule: {rule.rule_id}"],
                    )
                    return ExecutionResult(
                        success=True,
                        status=ExecutionStatus.SUCCESS,
                        data=decision,
                    )

        # 3. Default: Action complies with all policies
        decision = PolicyDecision(
            action=PolicyAction.ALLOW,
            allowed=True,
            risk_level=RiskLevel.LOW,
            approval_status=ApprovalStatus.NOT_REQUIRED,
            reasons=["Action complies with all registered policies."],
        )
        return ExecutionResult(
            success=True,
            status=ExecutionStatus.SUCCESS,
            data=decision,
        )

    async def get_metadata(self) -> ComponentMetadata:
        return ComponentMetadata(
            component_id="policy_engine",
            name="RuleBasedPolicyEngine",
            description="Evaluates guardrails and security policies for agent actions",
            version="2.0.0",
            component_type=ComponentType.POLICY_ENGINE,
        )

    async def health_check(self) -> bool:
        return True
