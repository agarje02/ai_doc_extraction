"""Extraction orchestration: chunk -> LLM -> merged fields with provenance.

Each chunk is sent to the configured provider independently, then per-field
candidates are merged: scalar fields keep the highest-confidence non-null
answer; list fields are unioned across chunks. Page numbers and source snippets
are carried through so the UI can show where every value came from.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.config import Settings, get_settings
from app.schemas.base import DocSchema

from .chunking import Chunk
from .llm.base import LLMProvider, LLMRequest
from .prompts import build_system_prompt, build_user_prompt


@dataclass
class FieldExtraction:
    name: str
    value: Any = None
    model_confidence: float | None = None
    source_text: str | None = None
    page: int | None = None
    chunk_index: int | None = None


@dataclass
class RawExtraction:
    doc_type: str
    fields: dict[str, FieldExtraction] = field(default_factory=dict)
    chunk_count: int = 0
    errors: list[str] = field(default_factory=list)


def _as_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def extract_document(
    schema: DocSchema,
    chunks: list[Chunk],
    provider: LLMProvider,
    settings: Settings | None = None,
) -> RawExtraction:
    settings = settings or get_settings()
    system = build_system_prompt()
    prompt_schema = schema.prompt_json_schema()
    field_map = schema.field_map()

    result = RawExtraction(doc_type=schema.key, chunk_count=len(chunks))
    # Accumulate values for list ("many") fields across chunks.
    list_acc: dict[str, list[Any]] = {}

    for chunk in chunks:
        request = LLMRequest(
            system=system,
            user=build_user_prompt(schema, chunk.text),
            json_schema=prompt_schema,
            context_text=chunk.text,
            model=settings.llm_model,
            temperature=settings.llm_temperature,
            max_output_tokens=settings.llm_max_output_tokens,
        )
        try:
            payload = provider.generate_structured(request)
        except Exception as exc:  # keep going; a bad chunk shouldn't kill the run
            result.errors.append(f"chunk {chunk.index}: {exc}")
            continue

        chunk_fields = payload.get("fields", {})
        for name, spec in chunk_fields.items():
            if name not in field_map:
                continue
            value = spec.get("value") if isinstance(spec, dict) else spec
            if value is None or value == "" or value == []:
                continue
            conf = _as_float(spec.get("confidence")) if isinstance(spec, dict) else 0.0
            source = spec.get("source_text") if isinstance(spec, dict) else None
            page = chunk.page_start

            if field_map[name].many:
                items = value if isinstance(value, list) else [value]
                acc = list_acc.setdefault(name, [])
                for item in items:
                    if item not in acc:
                        acc.append(item)
                # Track provenance/confidence on the aggregate entry too.
                existing = result.fields.get(name)
                best_conf = max(conf, existing.model_confidence or 0.0) if existing else conf
                result.fields[name] = FieldExtraction(
                    name=name,
                    value=list(acc),
                    model_confidence=best_conf,
                    source_text=source or (existing.source_text if existing else None),
                    page=page if existing is None else existing.page,
                    chunk_index=chunk.index if existing is None else existing.chunk_index,
                )
            else:
                existing = result.fields.get(name)
                if existing is None or conf > (existing.model_confidence or -1.0):
                    result.fields[name] = FieldExtraction(
                        name=name,
                        value=value,
                        model_confidence=conf,
                        source_text=source,
                        page=page,
                        chunk_index=chunk.index,
                    )

    # Ensure every schema field is represented, even if never found.
    for name in field_map:
        result.fields.setdefault(name, FieldExtraction(name=name))
    return result
