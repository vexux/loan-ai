from dataclasses import dataclass, field
from typing import Any, Callable, Coroutine, Optional

# A handler is any async function: async def handler(inputs: dict) -> dict
HandlerType = Callable[[dict[str, Any]], Coroutine[Any, Any, dict[str, Any]]]


@dataclass
class CapabilityDefinition:
    """
    Describes a single domain-agnostic capability.
    """
    action: str
    name: str
    description: str
    domain: str = "generic"
    enabled: bool = True
    handler: Optional[HandlerType] = None  # The real Python function to execute
    metadata: dict = field(default_factory=dict)
