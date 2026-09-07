"""Local Ollama provider (offline, no API key) via its HTTP API."""
from __future__ import annotations

from typing import Any

from .base import LLMError, LLMProvider, LLMRequest, normalize_fields, parse_json_object


class OllamaProvider(LLMProvider):
    name = "ollama"

    def __init__(self, base_url: str) -> None:
        self._base_url = base_url.rstrip("/")
        try:
            import httpx  # noqa: F401
        except ImportError as exc:  # pragma: no cover - optional dep
            raise LLMError("httpx not installed. `pip install httpx`") from exc

    def generate_structured(self, request: LLMRequest) -> dict[str, Any]:
        import httpx

        payload = {
            "model": request.model,
            "stream": False,
            "format": "json",
            "options": {
                "temperature": request.temperature,
                "num_predict": request.max_output_tokens,
            },
            "messages": [
                {"role": "system", "content": request.system},
                {"role": "user", "content": request.user},
            ],
        }
        try:
            resp = httpx.post(
                f"{self._base_url}/api/chat", json=payload, timeout=120.0
            )
            resp.raise_for_status()
        except httpx.HTTPError as exc:
            raise LLMError(f"Ollama request failed: {exc}") from exc
        content = resp.json().get("message", {}).get("content", "")
        return normalize_fields(parse_json_object(content))
