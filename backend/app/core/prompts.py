"""Build extraction prompts from a ``DocSchema``.

The prompt is deliberately strict about the output contract (a single JSON
object with per-field value/confidence/source_text) because the whole pipeline
depends on that shape. Confidence and source_text drive the downstream
confidence scoring and the provenance shown in the review UI.
"""
from __future__ import annotations

import json

from app.schemas.base import DocSchema, FieldSpec

_SYSTEM = (
    "You are a meticulous document information extraction engine. "
    "You read the provided document text and extract only the requested fields. "
    "You never invent values: if a field is not present in the text, return null. "
    "You always respond with a single valid JSON object and nothing else."
)


def _field_line(f: FieldSpec) -> str:
    parts = [f"- {f.name} ({'list of ' if f.many else ''}{f.type})"]
    if f.required:
        parts.append("[required]")
    if f.description:
        parts.append(f": {f.description}")
    if f.enum:
        parts.append(f" One of: {', '.join(f.enum)}.")
    if f.example:
        parts.append(f" Example: {f.example}.")
    return "".join(parts)


def build_system_prompt() -> str:
    return _SYSTEM


def build_user_prompt(schema: DocSchema, chunk_text: str) -> str:
    field_lines = "\n".join(_field_line(f) for f in schema.fields)
    shape = {
        "fields": {
            schema.fields[0].name if schema.fields else "example": {
                "value": "<extracted value or null>",
                "confidence": "<float 0.0-1.0 how certain you are>",
                "source_text": "<the exact snippet from the document you used>",
            }
        }
    }
    return (
        f"Document type: {schema.name} - {schema.description}\n\n"
        f"Extract the following fields:\n{field_lines}\n\n"
        "Rules:\n"
        "- Return every field listed above, using null for value when absent.\n"
        "- confidence must reflect how sure you are (1.0 = explicitly stated, "
        "lower when inferred).\n"
        "- source_text must be the verbatim snippet supporting the value, or null.\n"
        "- For list fields, value must be a JSON array.\n\n"
        f"Respond with JSON in exactly this shape:\n{json.dumps(shape, indent=2)}\n\n"
        "----- DOCUMENT TEXT START -----\n"
        f"{chunk_text}\n"
        "----- DOCUMENT TEXT END -----"
    )
