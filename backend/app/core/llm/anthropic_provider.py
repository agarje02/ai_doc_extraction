"""Anthropic Claude provider (lazy-imported)."""
from __future__ import annotations

from typing import Any

from .base import LLMError, LLMProvider, LLMRequest, normalize_fields, parse_json_object


class AnthropicProvider(LLMProvider):
    name = "anthropic"

    def __init__(self, api_key: str | None) -> None:
        if not api_key:
            raise LLMError("ANTHROPIC_API_KEY is required for the anthropic provider")
        try:
            import anthropic
        except ImportError as exc:  # pragma: no cover - optional dep
            raise LLMError(
                "anthropic package not installed. `pip install anthropic`"
            ) from exc
        self._client = anthropic.Anthropic(api_key=api_key)

    def generate_structured(self, request: LLMRequest) -> dict[str, Any]:
        # Claude reliably emits JSON when the assistant turn is pre-filled with
        # an opening brace; we re-add it before parsing.
        resp = self._client.messages.create(
            model=request.model,
            temperature=request.temperature,
            max_tokens=request.max_output_tokens,
            system=request.system,
            messages=[
                {"role": "user", "content": request.user},
                {"role": "assistant", "content": "{"},
            ],
        )
        text = "".join(block.text for block in resp.content if block.type == "text")
        return normalize_fields(parse_json_object("{" + text))
