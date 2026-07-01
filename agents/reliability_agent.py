from typing import Any

from agents.llm_utils import get_llm, parse_json_payload
from agents.prompts import RELIABILITY_PROMPT
from agents.state import InvestigationState


class ReliabilityAgent:
    def __init__(self, model_name: str | None = None) -> None:
        self.llm = get_llm(model_name)

    def run(self, state: InvestigationState) -> InvestigationState:
        text = str(self.llm({"prompt": state.prompt, "response": state.response}))
        payload = parse_json_payload(text, {
            "score": 70,
            "evidence": ["Fallback analysis applied"],
            "recommendations": ["Add confidence calibration and reasoning audits"],
        })
        state.reliability_result = payload
        return state
