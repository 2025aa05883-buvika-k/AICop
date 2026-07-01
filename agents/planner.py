from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from agents.llm_utils import get_llm
from agents.state import InvestigationState


class PlannerAgent:
    def __init__(self, model_name: str | None = None) -> None:
        self.llm = get_llm(model_name)

    def run(self, state: InvestigationState) -> InvestigationState:
        if not state.prompt.strip() or not state.response.strip():
            raise ValueError("Prompt and response are required")

        case_id = f"AICOP-{uuid4().hex[:4].upper()}"
        state.case_id = case_id
        state.conversation_history = f"Investigation started at {datetime.utcnow().isoformat()}"
        return state
