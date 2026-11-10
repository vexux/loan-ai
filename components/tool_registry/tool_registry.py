from components.tool_registry.capability import CapabilityDefinition


class ToolRegistry:
    """
    Central registry of all capabilities available to the Agent.

    The Agent Core never holds a hardcoded list of action names.
    Instead, it queries this registry at runtime to discover
    what it can do.

    This is what breaks the tight coupling:
    - Planner asks:          "What actions are available?"
    - Reasoning Engine asks: "What actions are available?"
    - Decision Engine asks:  "Which capability maps to this action?"

    All three get their answers from here, not from hardcoded strings.

    To switch domains (e.g., Insurance → Retail), you simply register
    different capabilities. Zero changes to the Agent Core.
    """

    def __init__(self) -> None:
        # Internal store: action_name → CapabilityDefinition
        self._capabilities: dict[str, CapabilityDefinition] = {}

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register(self, capability: CapabilityDefinition) -> None:
        """
        Register a capability in the registry.

        If a capability with the same action already exists,
        it is overwritten. This allows bootstrap to reconfigure
        capabilities at startup without errors.
        """
        self._capabilities[capability.action] = capability

    # ------------------------------------------------------------------
    # Discovery (used by Planner and Reasoning Engine)
    # ------------------------------------------------------------------

    def get_available_actions(self) -> list[str]:
        """
        Return all currently enabled action names.

        This list is injected into LLM prompts so the model
        can only pick from registered actions — not invent them.
        """
        return [
            cap.action
            for cap in self._capabilities.values()
            if cap.enabled
        ]

    def get_action_descriptions(self) -> list[str]:
        """
        Return formatted lines describing each enabled capability.

        Injected directly into system prompts so the LLM understands
        what each action does.

        Example output line:
            "- search_documents: Search documents to retrieve information"
        """
        return [
            f"- {cap.action}: {cap.description}"
            for cap in self._capabilities.values()
            if cap.enabled
        ]

    # ------------------------------------------------------------------
    # Lookup (used by Decision Engine)
    # ------------------------------------------------------------------

    def find_by_action(
        self,
        action: str,
    ) -> CapabilityDefinition | None:
        """
        Find the concrete capability registered for a given action name.

        Returns None if no matching capability is registered.
        The Decision Engine uses this to resolve action → implementation.
        """
        return self._capabilities.get(action)

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------

    def all_capabilities(self) -> list[CapabilityDefinition]:
        """Return all registered capabilities (enabled or not)."""
        return list(self._capabilities.values())

    def is_registered(self, action: str) -> bool:
        """Check whether an action is registered and enabled."""
        cap = self._capabilities.get(action)
        return cap is not None and cap.enabled
