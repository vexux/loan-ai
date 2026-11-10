from datetime import datetime

from pydantic import BaseModel, Field

from contracts.common.enums import HealthStatus


class ComponentHealth(BaseModel):
    status: HealthStatus

    message: str = "OK"

    timestamp: datetime = Field(default_factory=datetime.utcnow)