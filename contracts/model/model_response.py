from typing import Any

from pydantic import BaseModel, Field


class ModelResponse(BaseModel):
    """
    Provider-independent response returned by the Model Gateway.
    """

    response_id: str

    content: str

    model_name: str

    tokens_input: int = 0

    tokens_output: int = 0

    latency_ms: int = 0

    metadata: dict[str, Any] = Field(
        default_factory=dict
    )