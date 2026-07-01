from __future__ import annotations

from typing import Any

from agents.evaluator import EvaluatorAgent
from agents.planner import PlannerAgent
from agents.reporter import ReportAgent
from agents.reliability_agent import ReliabilityAgent
from agents.security_agent import SecurityAgent
from agents.state import InvestigationState

try:
    from langgraph.graph import END, StateGraph
except Exception:  # pragma: no cover - optional dependency
    StateGraph = None
    END = "__end__"


class InvestigationOrchestrator:
    def __init__(self) -> None:
        self.planner = PlannerAgent()
        self.security = SecurityAgent()
        self.reliability = ReliabilityAgent()
        self.evaluator = EvaluatorAgent()
        self.reporter = ReportAgent()

    def run(self, state: InvestigationState) -> InvestigationState:
        if StateGraph is not None:
            workflow = StateGraph(InvestigationState)
            workflow.add_node("planner", self._planner_node)
            workflow.add_node("security", self._security_node)
            workflow.add_node("reliability", self._reliability_node)
            workflow.add_node("evaluator", self._evaluator_node)
            workflow.add_node("reporter", self._reporter_node)
            workflow.set_entry_point("planner")
            workflow.add_edge("planner", "security")
            workflow.add_edge("security", "reliability")
            workflow.add_edge("reliability", "evaluator")
            workflow.add_edge("evaluator", "reporter")
            workflow.add_edge("reporter", END)
            app = workflow.compile()
            result = app.invoke(state.model_dump())
            if isinstance(result, dict):
                return InvestigationState(**result)
            return result
        return self._sequential_run(state)

    def _sequential_run(self, state: InvestigationState) -> InvestigationState:
        state = self.planner.run(state)
        state = self.security.run(state)
        state = self.reliability.run(state)
        state = self.evaluator.run(state)
        state = self.reporter.run(state)
        return state

    def _planner_node(self, state: InvestigationState) -> InvestigationState:
        return self.planner.run(state)

    def _security_node(self, state: InvestigationState) -> InvestigationState:
        return self.security.run(state)

    def _reliability_node(self, state: InvestigationState) -> InvestigationState:
        return self.reliability.run(state)

    def _evaluator_node(self, state: InvestigationState) -> InvestigationState:
        return self.evaluator.run(state)

    def _reporter_node(self, state: InvestigationState) -> InvestigationState:
        return self.reporter.run(state)
