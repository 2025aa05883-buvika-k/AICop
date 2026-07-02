from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
import logging
from typing import Any

from agents.state import BaseInvestigationState

logger = logging.getLogger("aicop.agents")


class BaseAgent(ABC):
    def __init__(self, name: str) -> None:
        self.name = name

    @abstractmethod
    def run(self, state: BaseInvestigationState) -> BaseInvestigationState:
        raise NotImplementedError

    def log(self, state: BaseInvestigationState, message: str) -> None:
        state.logs.append(f"{datetime.utcnow().isoformat()} {self.name}: {message}")
        logger.info(
            "agent_step",
            extra={"event": "agent_step", "agent": self.name, "case_id": state.case_id, "log_message": message},
        )


class BasePlanner(BaseAgent):
    """Plans the steps for an investigation module."""


class BaseJury(BaseAgent):
    """Aggregates completed specialist findings without re-running analysis."""


class BaseReportGenerator(BaseAgent):
    """Builds a professional report from evidence, findings, and verdict."""


def clamp_score(value: float) -> float:
    return max(0.0, min(100.0, round(value, 1)))


def risk_from_score(score: float, inverse: bool = False) -> str:
    normalized = 100 - score if inverse else score
    if normalized >= 75:
        return "high"
    if normalized >= 45:
        return "medium"
    return "low"


def result_payload(
    agent: str,
    title: str,
    score: float,
    risk: str,
    confidence: float,
    evidence: list[str],
    recommendations: list[str],
    status: str = "completed",
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "agent": agent,
        "title": title,
        "status": status,
        "score": clamp_score(score),
        "risk": risk,
        "confidence": clamp_score(confidence),
        "evidence": evidence,
        "recommendations": recommendations,
        "details": details or {},
    }
