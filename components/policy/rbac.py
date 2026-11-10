"""
Domain-Agnostic Role-Based Access Control (RBAC) Policy.
Enforces permissions for CUSTOMER and ADMIN roles with resource ownership.
"""
from enum import Enum
from typing import Any, Dict, Set

from contracts.common.enums import ApprovalStatus, RiskLevel
from contracts.common.request_context import RequestContext
from contracts.policy.policy_contract import PolicyAction, PolicyDecision


class UserRole(str, Enum):
    CUSTOMER = "customer"   # End-user: can search, query eligibility, and view/apply for themselves
    ADMIN = "admin"         # Administrator: unrestricted access across all actions and resources


class RBACPolicyEngine:
    """
    Evaluates role permissions against requested actions and target resources.
    """

    # Role Permissions Matrix
    ROLE_PERMISSIONS: Dict[UserRole, Set[str]] = {
        UserRole.CUSTOMER: {
            "search_documents",
            "query_policy_graph",
            "retrieve_entity",            # Restricted to self (cannot view other customers' data)
            "create_entity",
            "execute_transaction",        # Restricted to self
            "generate_response",
            "query_records",              # Read-only filtered queries (e.g. view own applications)
            "submit_loan_application",    # Industry standard: customers apply for their own loans
        },

        UserRole.ADMIN: {
            "*",  # All permissions
        },
    }

    def evaluate_access(
        self,
        context: RequestContext,
        action: str,
        target_resource_owner_id: str | None = None,
    ) -> PolicyDecision:
        """
        Determines whether the caller has permission to execute the action.
        """
        # Default role is CUSTOMER if not explicitly specified
        raw_role = context.metadata.get("role", UserRole.CUSTOMER.value)
        try:
            role = UserRole(raw_role.lower())
        except ValueError:
            role = UserRole.CUSTOMER

        # 1. ADMIN has full unrestricted access
        if role == UserRole.ADMIN:
            return PolicyDecision(
                action=PolicyAction.ALLOW,
                allowed=True,
                risk_level=RiskLevel.LOW,
                approval_status=ApprovalStatus.APPROVED,
                reasons=["Admin role authorized for all actions."],
                modified_output={},
            )

        # 2. Check CUSTOMER permissions
        allowed_actions = self.ROLE_PERMISSIONS.get(role, set())
        if action in allowed_actions:
            # Resource Ownership Check: A customer can only access/modify their own records
            if target_resource_owner_id and context.user_id:
                if context.user_id != target_resource_owner_id:
                    return PolicyDecision(
                        action=PolicyAction.DENY,
                        allowed=False,
                        risk_level=RiskLevel.HIGH,
                        approval_status=ApprovalStatus.REJECTED,
                        reasons=[f"Access Denied: Customer '{context.user_id}' cannot access records belonging to '{target_resource_owner_id}'."],
                        modified_output={},
                    )

            return PolicyDecision(
                action=PolicyAction.ALLOW,
                allowed=True,
                risk_level=RiskLevel.LOW,
                approval_status=ApprovalStatus.APPROVED,
                reasons=[f"Customer role authorized for action '{action}'."],
                modified_output={},
            )

        # 3. Action not allowed for customer
        return PolicyDecision(
            action=PolicyAction.DENY,
            allowed=False,
            risk_level=RiskLevel.MEDIUM,
            approval_status=ApprovalStatus.REJECTED,
            reasons=[f"Customer role does not have permission for action '{action}'."],
            modified_output={},
        )
