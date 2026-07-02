from datetime import datetime
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class BaseInvestigationState(BaseModel):
    """Shared saga state persisted as an investigation moves between agents."""

    case_id: str = Field(default_factory=lambda: f"AICOP-{uuid4().hex[:8].upper()}")
    status: str = Field(default="initialized")
    current_step: str = Field(default="initialized")
    prompt: str = Field(default="")
    response: str = Field(default="")
    conversation_history: str = Field(default="")
    evidence: dict[str, Any] = Field(default_factory=dict)
    agent_results: list[dict[str, Any]] = Field(default_factory=list)
    logs: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    jury_result: dict[str, Any] = Field(default_factory=dict)
    report: str = Field(default="")
    started_time: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    completed_time: str | None = Field(default=None)


class SecurityState(BaseInvestigationState):
    module: str = Field(default="security")


class ReliabilityState(BaseInvestigationState):
    module: str = Field(default="reliability")


class DeploymentState(BaseInvestigationState):
    module: str = Field(default="deployment")


class InvestigationState(BaseInvestigationState):
    """Backward-compatible state for the legacy single-workflow orchestrator."""

    module: str = Field(default="legacy")
    security_result: dict[str, Any] = Field(default_factory=dict)
    reliability_result: dict[str, Any] = Field(default_factory=dict)
    evaluation_result: dict[str, Any] = Field(default_factory=dict)
