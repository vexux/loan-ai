from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from contracts.common.enums import RiskLevel


class RequestContext(BaseModel):
    request_id: str
    correlation_id: str
    session_id: str

    user_id: str
    tenant_id: str

    conversation_id: str | None = None
    domain: str | None = None
    intent: str | None = None

    risk_level: RiskLevel = RiskLevel.LOW

    metadata: dict[str, Any] = Field(default_factory=dict)

    created_at: datetime = Field(default_factory=datetime.utcnow)