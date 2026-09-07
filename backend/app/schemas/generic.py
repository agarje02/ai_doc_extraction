"""Generic / bring-your-own-schema support.

Callers can define an ad-hoc document type at request time by passing a list of
field definitions (or a JSON Schema-ish ``properties`` object). This powers the
"works for any document type" capability without code changes.
"""
from __future__ import annotations

from typing import Any

from .base import DocSchema, FieldSpec

# A small default used when the caller asks for "generic" without a custom spec.
GENERIC_SCHEMA = DocSchema(
    key="generic",
    name="Generic Document",
    description="Free-form key information extraction from any document.",
    fields=[
        FieldSpec(name="title", type="string",
                  description="Document title or main subject."),
        FieldSpec(name="summary", type="text",
                  description="One or two sentence summary of the document."),
        FieldSpec(name="date", type="date",
                  description="The primary date mentioned, if any."),
        FieldSpec(name="entities", type="string", many=True,
                  description="Key named entities: people, organizations, places."),
        FieldSpec(name="key_values", type="text", many=True,
                  description="Notable 'label: value' facts found in the document."),
    ],
)


_JSON_TYPE_MAP = {
    "string": "string",
    "integer": "integer",
    "number": "number",
    "boolean": "boolean",
    "array": "array",
}


def schema_from_fields(
    key: str,
    name: str,
    fields: list[dict[str, Any]],
    description: str = "",
) -> DocSchema:
    """Build a ``DocSchema`` from a list of plain field dicts."""
    specs = [FieldSpec(**f) for f in fields]
    return DocSchema(key=key, name=name, description=description, fields=specs)


def schema_from_json_schema(
    key: str,
    name: str,
    json_schema: dict[str, Any],
    description: str = "",
) -> DocSchema:
    """Build a ``DocSchema`` from a JSON-Schema ``properties`` object.

    Accepts either a full JSON Schema (with ``properties``/``required``) or the
    bare properties mapping. Nested objects are flattened to ``text`` fields.
    """
    props = json_schema.get("properties", json_schema)
    required = set(json_schema.get("required", []))
    specs: list[FieldSpec] = []
    for field_name, spec in props.items():
        spec = spec or {}
        jtype = spec.get("type", "string")
        if isinstance(jtype, list):
            jtype = next((t for t in jtype if t != "null"), "string")
        many = jtype == "array"
        base_type = "text" if jtype == "object" else _JSON_TYPE_MAP.get(jtype, "string")
        if many:
            items = spec.get("items", {})
            item_type = items.get("type", "string")
            base_type = _JSON_TYPE_MAP.get(item_type, "string")
        specs.append(
            FieldSpec(
                name=field_name,
                type=base_type,  # type: ignore[arg-type]
                description=spec.get("description", ""),
                required=field_name in required,
                many=many,
                enum=spec.get("enum"),
            )
        )
    return DocSchema(key=key, name=name, description=description, fields=specs)
