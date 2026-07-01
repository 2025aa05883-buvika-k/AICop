from __future__ import annotations

from agents.state import InvestigationState


class EvaluatorAgent:
    def run(self, state: InvestigationState) -> InvestigationState:
        security_score = float(state.security_result.get("score", 0))
        reliability_score = float(state.reliability_result.get("score", 0))
        state.overall_score = round((security_score * 0.55 + reliability_score * 0.45), 2)

        if state.overall_score >= 80:
            state.overall_risk = "low"
        elif state.overall_score >= 60:
            state.overall_risk = "medium"
        else:
            state.overall_risk = "high"

        state.recommendations = []
        state.recommendations.extend(state.security_result.get("recommendations", []))
        state.recommendations.extend(state.reliability_result.get("recommendations", []))
        state.recommendations = list(dict.fromkeys(state.recommendations))
        return state
