"""Declarative schema model shared by all document types.

A ``DocSchema`` is a list of ``FieldSpec``s plus metadata. From it we derive:
  - a JSON schema string embedded in the extraction prompt, and
  - validation + normalization behaviour (see core/validation.py, postprocess.py).

Using a declarative spec (instead of hand-written Pydantic models per type)
means the built-in types and the "generic / bring-your-own" mode share one code
path, and new document types are a few lines of data.
"""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

FieldType = Literal[
    "string",
    "text",
    "integer",
    "number",
    "boolean",
    "date",
    "email",
    "phone",
    "currency",
    "array",
]


class FieldSpec(BaseModel):
    name: str
    type: FieldType = "string"
    description: str = ""
    required: bool = False
    many: bool = False  # value is a list of `type`
    pattern: str | None = None  # regex the raw value must match
    enum: list[str] | None = None
    example: str | None = None
    normalize: bool = True  # apply post-processing normalization for this type

    def json_type(self) -> str:
        mapping = {
            "string": "string",
            "text": "string",
            "email": "string",
            "phone": "string",
            "date": "string",
            "currency": "number",
            "integer": "integer",
            "number": "number",
            "boolean": "boolean",
            "array": "array",
        }
        return "array" if self.many else mapping.get(self.type, "string")


class DocSchema(BaseModel):
    key: str = Field(..., description="Stable identifier, e.g. 'invoice'")
    name: str
    description: str = ""
    version: str = "1"
    fields: list[FieldSpec]

    def field_map(self) -> dict[str, FieldSpec]:
        return {f.name: f for f in self.fields}

    def prompt_json_schema(self) -> dict[str, Any]:
        """JSON schema describing the ``{"fields": {...}}`` object we want back."""
        props: dict[str, Any] = {}
        for f in self.fields:
            value_schema: dict[str, Any] = {"type": [f.json_type(), "null"]}
            if f.many:
                value_schema = {
                    "type": ["array", "null"],
                    "items": {"type": f.json_type()},
                }
            props[f.name] = {
                "type": "object",
                "properties": {
                    "value": value_schema,
                    "confidence": {"type": ["number", "null"]},
                    "source_text": {"type": ["string", "null"]},
                },
                "description": f.description,
            }
        return {
            "type": "object",
            "properties": {
                "fields": {"type": "object", "properties": props},
            },
        }
