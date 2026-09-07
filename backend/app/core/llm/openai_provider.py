"""OpenAI chat-completions provider (lazy-imported)."""
from __future__ import annotations

from typing import Any

from .base import LLMError, LLMProvider, LLMRequest, normalize_fields, parse_json_object


class OpenAIProvider(LLMProvider):
    name = "openai"

    def __init__(self, api_key: str | None) -> None:
        if not api_key:
            raise LLMError("OPENAI_API_KEY is required for the openai provider")
        try:
            from openai import OpenAI
        except ImportError as exc:  # pragma: no cover - optional dep
            raise LLMError("openai package not installed. `pip install openai`") from exc
        self._client = OpenAI(api_key=api_key)

    def generate_structured(self, request: LLMRequest) -> dict[str, Any]:
        resp = self._client.chat.completions.create(
            model=request.model,
            temperature=request.temperature,
            max_tokens=request.max_output_tokens,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": request.system},
                {"role": "user", "content": request.user},
            ],
        )
        content = resp.choices[0].message.content or ""
        return normalize_fields(parse_json_object(content))
