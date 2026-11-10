from enum import Enum


class ExecutionStatus(str, Enum):
    SUCCESS = "success"
    FAILURE = "failure"
    PARTIAL = "partial"
    SKIPPED = "skipped"


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ApprovalStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    NOT_REQUIRED = "not_required"


class ComponentType(str, Enum):
    AGENT = "agent"
    MODEL_GATEWAY = "model_gateway"
    TOOL_REGISTRY = "tool_registry"
    POLICY_ENGINE = "policy_engine"
    MEMORY = "memory"
    RAG_ENGINE = "rag_engine"
    WORKFLOW_ENGINE = "workflow_engine"
    DATA_ADAPTER = "data_adapter"
    TOOL = "tool"


class HealthStatus(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
