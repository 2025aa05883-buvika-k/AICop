from __future__ import annotations

from agents.state import InvestigationState


class ReportAgent:
    def run(self, state: InvestigationState) -> InvestigationState:
        security_score = float(state.security_result.get("score", 0))
        reliability_score = float(state.reliability_result.get("score", 0))
        security_evidence = state.security_result.get("evidence", [])
        reliability_evidence = state.reliability_result.get("evidence", [])

        report_lines = [
            f"Case ID: {state.case_id}",
            "Executive Summary",
            f"The AI system received a trust score of {state.overall_score:.2f} with overall risk {state.overall_risk}.",
            "",
            "Security Analysis",
            f"Security Score: {security_score}",
            f"Evidence: {', '.join(security_evidence) if security_evidence else 'None'}",
            "",
            "Reliability Analysis",
            f"Reliability Score: {reliability_score}",
            f"Evidence: {', '.join(reliability_evidence) if reliability_evidence else 'None'}",
            "",
            "Recommendations",
            *[f"- {item}" for item in state.recommendations],
        ]
        state.report = "\n".join(report_lines)
        return state
