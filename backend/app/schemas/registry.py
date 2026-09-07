"""Registry mapping doc-type keys to ``DocSchema`` definitions."""
from __future__ import annotations

from .base import DocSchema
from .contract import CONTRACT_SCHEMA
from .generic import GENERIC_SCHEMA
from .invoice import INVOICE_SCHEMA
from .resume import RESUME_SCHEMA

_REGISTRY: dict[str, DocSchema] = {
    INVOICE_SCHEMA.key: INVOICE_SCHEMA,
    RESUME_SCHEMA.key: RESUME_SCHEMA,
    CONTRACT_SCHEMA.key: CONTRACT_SCHEMA,
    GENERIC_SCHEMA.key: GENERIC_SCHEMA,
}


def list_schemas() -> list[DocSchema]:
    return list(_REGISTRY.values())


def get_schema(key: str) -> DocSchema:
    try:
        return _REGISTRY[key]
    except KeyError:
        raise KeyError(
            f"Unknown doc_type {key!r}. Known: {', '.join(sorted(_REGISTRY))}"
        )


def register_schema(schema: DocSchema, *, overwrite: bool = False) -> DocSchema:
    """Register (or replace) a reusable doc-type schema."""
    if schema.key in _REGISTRY and not overwrite:
        raise ValueError(f"Schema {schema.key!r} already exists")
    _REGISTRY[schema.key] = schema
    return schema


def has_schema(key: str) -> bool:
    return key in _REGISTRY
