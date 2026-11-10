from pydantic import BaseModel, Field

from contracts.common.enums import (
    ComponentType,
    RiskLevel,
)


class ComponentMetadata(BaseModel):
    """
    Standard metadata exposed by every platform component.
    """

    component_id: str

    name: str

    description: str

    version: str

    component_type: ComponentType

    risk_level: RiskLevel = RiskLevel.LOW

    owner: str | None = None

    tags: list[str] = Field(default_factory=list)

    enabled: bool = True