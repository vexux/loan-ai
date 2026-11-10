"""
Domain-Agnostic Output Guardrails.
Checks factual grounding, hallucination detection, and response sanitization.
"""
import re
from typing import Any, Tuple

from contracts.common.enums import ApprovalStatus, RiskLevel
from contracts.policy.policy_contract import PolicyAction, PolicyDecision


class OutputGuardrails:
    # Leaked internal prompt / pipeline tokens to strip
    LEAKAGE_PATTERNS = [
        r"(?i)\[Fetch\s+Rules\]:?",
        r"(?i)\[Fetch\s+Customer\]:?",
        r"(?i)\[Fetch\s+Strict\s+Policy\]:?",
        r"(?i)\[Decide\s+Eligibility\]:?",
        r"(?i)System\s+Prompt:?",
        r"(?i)Retrieved\s+Context\s+&\s+Data:?",
        r"(?i)CRITICAL\s+PRIORITY\s+RULES:?",
    ]

    def evaluate_output(
        self,
        output_text: str,
        context_text: str = "",
        claimed_numbers: list[float] | None = None,
    ) -> Tuple[PolicyDecision, str]:
        """
        Validates factual grounding and sanitizes model output.
        """
        if not output_text or not output_text.strip():
            return PolicyDecision(
                action=PolicyAction.DENY,
                allowed=False,
                risk_level=RiskLevel.HIGH,
                approval_status=ApprovalStatus.REJECTED,
                reasons=["Model produced empty or invalid response."],
                modified_output={},
            ), "I am unable to formulate a verified response to your request."

        # 1. Sanitize System Prompt / Internal Pipeline Leakage
        sanitized_output = output_text
        for pattern in self.LEAKAGE_PATTERNS:
            sanitized_output = re.sub(pattern, "", sanitized_output).strip()

        # 2. Numerical Grounding Check
        # Extracts numbers cited in output and checks if they exist in retrieved context
        if context_text:
            output_numbers = re.findall(r"\b\d+(?:,\d+)*(?:\.\d+)?\b", sanitized_output)
            context_numbers = set(re.findall(r"\b\d+(?:,\d+)*(?:\.\d+)?\b", context_text))

            unsupported_numbers = []
            for num_str in output_numbers:
                clean_num = num_str.replace(",", "")
                # Ignore trivial small numbers (0-10) like rule indices
                if float(clean_num) > 10:
                    matched = any(
                        clean_num == c.replace(",", "") or clean_num in c
                        for c in context_numbers
                    )
                    if not matched:
                        unsupported_numbers.append(num_str)

            # If model generated arbitrary large figures not in context, flag warning
            if len(unsupported_numbers) > 3:
                return PolicyDecision(
                    action=PolicyAction.CONTINUE_WITH_WARNING,
                    allowed=True,
                    risk_level=RiskLevel.MEDIUM,
                    approval_status=ApprovalStatus.APPROVED,
                    reasons=[f"Potential hallucination: numbers not in context: {unsupported_numbers[:3]}"],
                    modified_output={"sanitized_text": sanitized_output},
                ), sanitized_output

        return PolicyDecision(
            action=PolicyAction.ALLOW,
            allowed=True,
            risk_level=RiskLevel.LOW,
            approval_status=ApprovalStatus.APPROVED,
            reasons=["Output passed grounding and sanitization."],
            modified_output={"sanitized_text": sanitized_output},
        ), sanitized_output
