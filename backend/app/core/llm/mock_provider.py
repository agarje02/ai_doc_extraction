"""Deterministic, offline mock provider.

It performs lightweight regex/heuristic extraction driven by the field names in
the target JSON schema so the full pipeline (and tests) can run without any API
key or network access. It is intentionally simple - real accuracy comes from
the hosted/Ollama providers.
"""
from __future__ import annotations

import re
from typing import Any

from .base import LLMProvider, LLMRequest

_EMAIL = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
_PHONE = re.compile(r"(\+?\d[\d\s().-]{7,}\d)")
_DATE = re.compile(
    r"(\d{4}-\d{2}-\d{2}|\d{1,2}[/-]\d{1,2}[/-]\d{2,4}"
    r"|[A-Z][a-z]+ \d{1,2},? \d{4})"
)
_MONEY = re.compile(r"(?:[$€£₹]\s?\d[\d,]*(?:\.\d{2})?|\d[\d,]*\.\d{2})")


def _search_line(text: str, keyword: str) -> str | None:
    """Return the value following ``keyword:`` on a line, if present."""
    pattern = re.compile(
        rf"{re.escape(keyword)}\s*[:#-]?\s*(.+)", re.IGNORECASE
    )
    for line in text.splitlines():
        m = pattern.search(line)
        if m and m.group(1).strip():
            return m.group(1).strip()
    return None


def _guess_value(field_name: str, field_type: str, text: str) -> tuple[Any, str | None]:
    """Return a heuristic value and the source snippet it came from."""
    name = field_name.lower()

    # Keyword-labelled line ("Invoice Number: 123") is the strongest signal.
    label = field_name.replace("_", " ")
    line_val = _search_line(text, label)
    if line_val:
        return _coerce(line_val, field_type), line_val

    if "email" in name:
        m = _EMAIL.search(text)
        if m:
            return m.group(0), m.group(0)
    if "phone" in name or "mobile" in name or "tel" in name:
        m = _PHONE.search(text)
        if m:
            return m.group(0).strip(), m.group(0).strip()
    if "date" in name:
        m = _DATE.search(text)
        if m:
            return m.group(0), m.group(0)
    if any(k in name for k in ("amount", "total", "price", "cost", "salary")):
        m = _MONEY.search(text)
        if m:
            return _coerce(m.group(0), field_type), m.group(0)

    return None, None


def _coerce(raw: str, field_type: str) -> Any:
    if field_type in {"number", "integer", "float"}:
        cleaned = re.sub(r"[^\d.\-]", "", raw)
        try:
            return float(cleaned) if "." in cleaned else int(cleaned or 0)
        except ValueError:
            return None
    return raw


def _iter_field_specs(json_schema: dict[str, Any]):
    props = json_schema.get("properties", {})
    for name, spec in props.items():
        if name == "fields" and "properties" in spec:
            yield from _iter_field_specs(spec)
            continue
        yield name, spec.get("type", "string")


class MockProvider(LLMProvider):
    name = "mock"

    def generate_structured(self, request: LLMRequest) -> dict[str, Any]:
        text = request.context_text
        fields: dict[str, Any] = {}
        for field_name, field_type in _iter_field_specs(request.json_schema):
            value, source = _guess_value(field_name, field_type, text)
            if value is None:
                fields[field_name] = {
                    "value": None,
                    "confidence": 0.0,
                    "source_text": None,
                }
            else:
                # Higher confidence when we found an explicit labelled line.
                labelled = source is not None and ":" in (
                    _search_line(text, field_name.replace("_", " ")) or ""
                )
                fields[field_name] = {
                    "value": value,
                    "confidence": 0.9 if labelled else 0.7,
                    "source_text": source,
                }
        return {"fields": fields}
