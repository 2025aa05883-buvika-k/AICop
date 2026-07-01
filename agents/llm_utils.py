from __future__ import annotations

import json
from typing import Any

from backend.config import settings


class FallbackLLM:
    def __call__(self, prompt: Any) -> Any:
        class Response:
            def __init__(self, content: str) -> None:
                self.content = content

        return Response("{}")


def get_llm(model_name: str | None = None) -> Any:
    try:
        from langchain_ollama import ChatOllama

        return ChatOllama(model=model_name or settings.ollama_model, base_url=settings.ollama_base_url)
    except Exception:
        return FallbackLLM()


def parse_json_payload(text: str, fallback: dict[str, Any]) -> dict[str, Any]:
    try:
        payload = json.loads(text)
    except (TypeError, json.JSONDecodeError):
        return fallback
    if isinstance(payload, dict):
        return payload
    return fallback
