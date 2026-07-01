from typing import Any, Optional
from pydantic import BaseModel, Field


class InvestigationState(BaseModel):
    case_id: str = Field(default="")
    prompt: str = Field(default="")
    response: str = Field(default="")
    conversation_history: str = Field(default="")
    security_result: dict[str, Any] = Field(default_factory=dict)
    reliability_result: dict[str, Any] = Field(default_factory=dict)
    overall_score: float = Field(default=0.0)
    overall_risk: str = Field(default="low")
    recommendations: list[str] = Field(default_factory=list)
    report: str = Field(default="")
