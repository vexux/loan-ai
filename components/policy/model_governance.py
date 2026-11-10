"""
Domain-Agnostic Model Governance & Compliance Engine.
Tracks risk tiering, escalates high-risk transactions for human review, and logs governance records.
"""
import os
import json
from datetime import datetime
from typing import Any, Dict

from contracts.common.enums import ApprovalStatus, RiskLevel
from contracts.common.request_context import RequestContext
from contracts.policy.policy_contract import PolicyAction, PolicyDecision

LOGS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "logs", "governance")


class ModelGovernance:
    def __init__(self, escalation_threshold: float = 5000000.0) -> None:
        self.escalation_threshold = escalation_threshold
        os.makedirs(LOGS_DIR, exist_ok=True)

    def evaluate_risk(self, action: str, payload: Dict[str, Any]) -> PolicyDecision:
        """
        Classifies risk and requires escalation if transaction amount exceeds limit.
        """
        # Extract numerical amount if transaction
        amount = payload.get("amount") or payload.get("total") or payload.get("value") or payload.get("loan_amount") or 0.0

        if action in ("execute_transaction", "submit_application_transaction"):
            if float(amount) >= self.escalation_threshold:
                return PolicyDecision(
                    action=PolicyAction.REQUIRE_APPROVAL,
                    allowed=True,
                    risk_level=RiskLevel.HIGH,
                    approval_status=ApprovalStatus.PENDING,
                    reasons=[f"Transaction amount ({amount}) exceeds threshold ({self.escalation_threshold}). Requires Manager Approval."],
                    modified_output={"requires_manual_approval": True},
                )
            return PolicyDecision(
                action=PolicyAction.ALLOW,
                allowed=True,
                risk_level=RiskLevel.MEDIUM,
                approval_status=ApprovalStatus.APPROVED,
                reasons=["Standard transaction within threshold."],
                modified_output={},
            )

        return PolicyDecision(
            action=PolicyAction.ALLOW,
            allowed=True,
            risk_level=RiskLevel.LOW,
            approval_status=ApprovalStatus.APPROVED,
            reasons=["Low risk query action."],
            modified_output={},
        )

    def log_governance_event(
        self,
        context: RequestContext,
        action: str,
        risk_level: RiskLevel,
        model_name: str,
        audit_metadata: Dict[str, Any],
    ) -> str:
        """
        Writes an immutable governance audit record for compliance.
        """
        event = {
            "timestamp": datetime.utcnow().isoformat(),
            "request_id": context.request_id,
            "user_id": context.user_id,
            "action": action,
            "risk_level": risk_level.value,
            "model_name": model_name,
            "metadata": audit_metadata,
        }

        filename = f"GOV-{context.request_id}.json"
        path = os.path.join(LOGS_DIR, filename)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(event, f, indent=2)

        return path
