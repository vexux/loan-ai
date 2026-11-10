"""
Domain-Agnostic Input Guardrails.
Detects prompt injection, jailbreaks, and sanitizes/masks sensitive PII before model execution.
"""
import re
from typing import Any, Tuple

from contracts.common.enums import ApprovalStatus, RiskLevel
from contracts.policy.policy_contract import PolicyAction, PolicyDecision


class InputGuardrails:
    # Common prompt injection and jailbreak patterns
    INJECTION_PATTERNS = [
        r"(?i)\bignore\s+(?:all\s+)?(?:previous|prior|above)\s+instructions\b",
        r"(?i)\bdisregard\s+(?:all\s+)?(?:previous|prior|system)\s+prompts?\b",
        r"(?i)\breveal\s+(?:the\s+)?(?:system\s+prompt|hidden\s+instructions)\b",
        r"(?i)\byou\s+are\s+now\s+(?:an?\s+)?(?:unfiltered|jailbroken|dan|evil)\b",
        r"(?i)\bbypass\s+(?:all\s+)?(?:filters?|rules?|guardrails?|safety)\b",
        r"(?i)\bswitch\s+to\s+(?:developer|maintenance|god)\s+mode\b",
        r"(?i)\boutput\s+only\s+(?:as|in)\s+plaintext\s+system\b",
    ]

    # Sensitive PII Regex Patterns
    PII_PATTERNS = {
        "CREDIT_CARD": (r"\b(?:\d{4}[-\s]?){3}\d{4}\b", "[MASKED_CARD]"),
        "GOVT_ID_PAN": (r"\b[A-Z]{5}[0-9]{4}[A-Z]{1}\b", "[MASKED_GOVT_ID]"),
        "GOVT_ID_AADHAAR": (r"\b\d{4}\s\d{4}\s\d{4}\b", "[MASKED_NATIONAL_ID]"),
        "PHONE_NUMBER": (r"\b(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b", "[MASKED_PHONE]"),
    }

    def evaluate_input(self, text: str) -> Tuple[PolicyDecision, str]:
        """
        Evaluates input text against safety policies.
        Returns a PolicyDecision and the sanitized/masked text.
        """
        # 1. Check Prompt Injection / Jailbreak
        for pattern in self.INJECTION_PATTERNS:
            if re.search(pattern, text):
                return PolicyDecision(
                    action=PolicyAction.DENY,
                    allowed=False,
                    risk_level=RiskLevel.CRITICAL,
                    approval_status=ApprovalStatus.REJECTED,
                    reasons=["Prompt injection or adversarial jailbreak attempt detected."],
                    modified_output={},
                ), text

        # 2. Check and Mask PII
        sanitized_text = text
        pii_found = []
        for pii_type, (regex, mask) in self.PII_PATTERNS.items():
            matches = re.findall(regex, sanitized_text)
            if matches:
                pii_found.append(f"{pii_type} ({len(matches)} matches)")
                sanitized_text = re.sub(regex, mask, sanitized_text)

        if pii_found:
            return PolicyDecision(
                action=PolicyAction.MASK_DATA,
                allowed=True,
                risk_level=RiskLevel.MEDIUM,
                approval_status=ApprovalStatus.APPROVED,
                reasons=[f"PII detected and masked: {', '.join(pii_found)}"],
                modified_output={"masked_input": sanitized_text},
            ), sanitized_text

        # 3. Clean Input
        return PolicyDecision(
            action=PolicyAction.ALLOW,
            allowed=True,
            risk_level=RiskLevel.LOW,
            approval_status=ApprovalStatus.APPROVED,
            reasons=["Input passed all security guardrails."],
            modified_output={},
        ), sanitized_text
