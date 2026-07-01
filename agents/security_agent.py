from typing import Any

from agents.llm_utils import get_llm, parse_json_payload
from agents.prompts import SECURITY_PROMPT
from agents.state import InvestigationState


class SecurityAgent:
    def __init__(self, model_name: str | None = None) -> None:
        self.llm = get_llm(model_name)

    def run(self, state: InvestigationState) -> InvestigationState:
        text = str(self.llm({"prompt": state.prompt, "response": state.response}))
        payload = parse_json_payload(text, {
            "score": 65,
            "risk": "medium",
            "evidence": ["Fallback analysis applied"],
            "recommendations": ["Strengthen input validation and response filtering"],
        })
        state.security_result = payload
        return state
