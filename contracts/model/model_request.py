from typing import Any

from pydantic import BaseModel, Field

from contracts.common.request_context import RequestContext


class ModelRequest(BaseModel):
    """
    Provider-independent request sent to the Model Gateway.
    """

    request_context: RequestContext

    prompt: str

    system_prompt: str | None = None

    model: str = "Qwen/Qwen3-0.6B"

    temperature: float = 0.7

    max_tokens: int = 1024

    top_p: float = 0.95

    top_k: int = 20

    metadata: dict[str, Any] = Field(
        default_factory=dict
    )