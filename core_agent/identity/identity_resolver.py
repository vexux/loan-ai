import re
from typing import Any, Optional
from contracts.common.request_context import RequestContext


class IdentityResolver:
    """
    Domain-agnostic identity and target resolution component.
    Determines the target subject of a query (self vs. explicit entity ID vs. named entity),
    sanitizes generic role nouns, and enriches request inputs accordingly.
    """

    GENERIC_ROLE_NOUNS = {
        "applicant", "customer", "user", "client", "borrower", "account",
        "person", "individual", "unknown", "none", "null", "n/a", "na", "undefined"
    }

    SELF_PRONOUNS = {"my", "me", "mine", "i"}

    @classmethod
    def resolve_target(
        cls,
        query: str,
        context: RequestContext,
        entities: dict[str, Any],
        is_self_operation: bool = False,
        is_write_operation: bool = False,
    ) -> tuple[Optional[str], dict[str, Any]]:
        """
        Returns (target_id, resolved_inputs).
        """
        query_words = set(re.findall(r"\b\w+\b", query.lower()))
        is_self_query = bool(query_words.intersection(cls.SELF_PRONOUNS))

        # Check explicit ID in extracted entities using universal platform keys
        explicit_target = (
            entities.get("id")
            or entities.get("entity_id")
            or entities.get("target_id")
        )

        # Domain-agnostic fallback: discover any entity ID ending with '_id'
        if not explicit_target:
            id_keys = [
                k for k in entities.keys()
                if k.endswith("_id") and k not in {"session_id", "request_id", "trace_id", "span_id"}
            ]
            for k in id_keys:
                if entities.get(k):
                    explicit_target = entities[k]
                    break

        if explicit_target:
            explicit_target = str(explicit_target).strip()
            if explicit_target.lower() in cls.GENERIC_ROLE_NOUNS:
                explicit_target = None
            else:
                # Verbatim Grounding Guard: Reject hallucinated IDs not present in query or history
                query_lower = query.lower()
                history_lower = (context.metadata.get("history") or "").lower() if context and context.metadata else ""
                target_lower = explicit_target.lower()
                if target_lower not in query_lower and target_lower not in history_lower:
                    explicit_target = None


        # Determine target_id:
        # Rule 1: An explicit target entity ID (e.g. "C002") ALWAYS takes precedence over conversational "me"
        if explicit_target:
            target_id = explicit_target
        # Rule 2: If no explicit entity was named, check if the query is asking about the caller ("my", "me")
        elif is_self_query:
            target_id = context.user_id
        # Rule 3: Self-scoped or write operations default to the authenticated caller
        elif is_self_operation or is_write_operation:
            target_id = context.user_id
        else:
            target_id = None


        # Build clean workflow inputs preserving extracted entities
        resolved_inputs = dict(entities)
        if target_id:
            resolved_inputs["id"] = target_id
            resolved_inputs["target_id"] = target_id
        else:
            # If target_id could not be resolved from self/explicit ID,
            # remove empty id/entity_id placeholders so name-based search is not blocked
            if resolved_inputs.get("id") is None:
                resolved_inputs.pop("id", None)
            if resolved_inputs.get("entity_id") is None:
                resolved_inputs.pop("entity_id", None)

        return target_id, resolved_inputs
