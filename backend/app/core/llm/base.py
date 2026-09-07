"""Provider-agnostic LLM interface used by the extraction pipeline.

Every provider takes the same request (a system prompt, a user prompt, the
target JSON schema, and the raw context text) and returns a normalized dict of
the shape::

    {"fields": {"<field>": {"value": ..., "confidence": 0.0-1.0, "source_text": "..."}}}

Keeping the contract identical across OpenAI / Anthropic / Ollama / mock means
the rest of the pipeline never needs to know which model produced the answer.
"""
from __future__ import annotations

import json
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class LLMRequest:
    system: str
    user: str
    json_schema: dict[str, Any]
    context_text: str
    model: str
    temperature: float = 0.0
    max_output_tokens: int = 2048
    extra: dict[str, Any] = field(default_factory=dict)


class LLMProvider(ABC):
    """Base class for all LLM providers."""

    name: str = "base"

    @abstractmethod
    def generate_structured(self, request: LLMRequest) -> dict[str, Any]:
        """Return a dict shaped like ``{"fields": {...}}``."""
        raise NotImplementedError


class LLMError(RuntimeError):
    """Raised when a provider fails to return a usable structured response."""


_JSON_BLOCK = re.compile(r"\{.*\}", re.DOTALL)


def parse_json_object(text: str) -> dict[str, Any]:
    """Best-effort parse of a JSON object out of a model response.

    Models occasionally wrap JSON in prose or markdown fences; we strip those
    and fall back to the first balanced ``{...}`` block.
    """
    text = text.strip()
    if text.startswith("```"):
        # Remove a leading ```json / ``` fence and the trailing fence.
        text = re.sub(r"^```[a-zA-Z0-9]*\n?", "", text)
        text = re.sub(r"\n?```$", "", text).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = _JSON_BLOCK.search(text)
        if not match:
            raise LLMError(f"No JSON object found in model response: {text[:200]!r}")
        return json.loads(match.group(0))


def normalize_fields(payload: dict[str, Any]) -> dict[str, Any]:
    """Coerce a parsed payload into the canonical ``{"fields": {...}}`` shape.

    Accepts either the canonical shape or a flat ``{field: value}`` mapping
    (which some models return despite instructions) and upgrades the latter.
    """
    fields = payload.get("fields")
    if isinstance(fields, dict):
        out: dict[str, Any] = {}
        for name, spec in fields.items():
            if isinstance(spec, dict) and "value" in spec:
                out[name] = {
                    "value": spec.get("value"),
                    "confidence": spec.get("confidence"),
                    "source_text": spec.get("source_text"),
                }
            else:
                out[name] = {"value": spec, "confidence": None, "source_text": None}
        return {"fields": out}

    # Flat mapping fallback: treat every top-level key as a field value.
    return {
        "fields": {
            name: {"value": value, "confidence": None, "source_text": None}
            for name, value in payload.items()
        }
    }
