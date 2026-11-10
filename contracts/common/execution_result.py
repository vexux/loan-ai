from datetime import datetime
from typing import Generic, TypeVar

from pydantic import BaseModel, Field, ConfigDict

from contracts.common.enums import ExecutionStatus
from contracts.common.errors import ContractError

T = TypeVar("T")


class ExecutionResult(BaseModel, Generic[T]):

    model_config = ConfigDict(arbitrary_types_allowed=True)

    success: bool

    status: ExecutionStatus

    data: T | None = None

    error: ContractError | None = None

    metadata: dict = Field(default_factory=dict)

    timestamp: datetime = Field(default_factory=datetime.utcnow)