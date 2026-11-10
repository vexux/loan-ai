from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class AuditMetadata(BaseModel):
    """Audit information."""

    created_by: str | None = None
    updated_by: str | None = None

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime | None = None


class VersionMetadata(BaseModel):
    """Version information."""

    version: str = "1.0.0"

    tags: list[str] = Field(default_factory=list)

    labels: dict[str, str] = Field(default_factory=dict)


class ExtendedMetadata(BaseModel):
    """
    Extensible metadata object.
    Safe place for future attributes.
    """

    attributes: dict[str, Any] = Field(default_factory=dict)