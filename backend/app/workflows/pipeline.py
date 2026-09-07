"""End-to-end extraction pipeline producing application-ready structured JSON.

    text extraction -> chunking -> LLM extraction -> normalization ->
    validation -> confidence scoring -> final JSON

The output separates a clean ``data`` mapping (just values, ready to consume)
from a rich ``fields`` mapping (value + confidence + provenance + issues) used
by the review UI.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from app.config import Settings, get_settings
from app.core.chunking import chunk_document
from app.core.confidence import score_field
from app.core.extract import extract_document
from app.core.llm.base import LLMProvider
from app.core.llm.factory import build_provider
from app.core.postprocess import normalize_value
from app.core.text_extraction import ExtractedText, extract_text
from app.core.validation import validate_field
from app.schemas.base import DocSchema


def run_pipeline(
    extracted: ExtractedText,
    schema: DocSchema,
    provider: LLMProvider | None = None,
    settings: Settings | None = None,
) -> dict[str, Any]:
    settings = settings or get_settings()
    provider = provider or build_provider(settings)

    chunks = chunk_document(extracted, settings)
    raw = extract_document(schema, chunks, provider, settings)
    document_text = extracted.full_text
    field_map = schema.field_map()

    fields: dict[str, Any] = {}
    data: dict[str, Any] = {}
    needs_review_fields: list[str] = []
    confidences: list[float] = []

    for name, spec in field_map.items():
        fx = raw.fields.get(name)
        raw_value = fx.value if fx else None
        value = normalize_value(spec, raw_value)
        issues = validate_field(spec, value)
        confidence, needs_review = score_field(
            value=value,
            model_confidence=fx.model_confidence if fx else None,
            source_text=fx.source_text if fx else None,
            document_text=document_text,
            issues=issues,
            review_threshold=settings.confidence_review_threshold,
        )
        fields[name] = {
            "value": value,
            "type": spec.type,
            "many": spec.many,
            "confidence": confidence,
            "needs_review": needs_review,
            "page": fx.page if fx else None,
            "source_text": fx.source_text if fx else None,
            "issues": [
                {"severity": i.severity, "message": i.message} for i in issues
            ],
        }
        data[name] = value
        if value not in (None, "", []):
            confidences.append(confidence)
        if needs_review:
            needs_review_fields.append(name)

    overall = round(sum(confidences) / len(confidences), 3) if confidences else 0.0

    return {
        "doc_type": schema.key,
        "schema_name": schema.name,
        "schema_version": schema.version,
        "meta": {
            "pages": len(extracted.pages),
            "chunks": raw.chunk_count,
            "used_ocr": extracted.used_ocr,
            "provider": provider.name,
            "model": settings.llm_model,
            "errors": raw.errors,
        },
        "fields": fields,
        "data": data,
        "review": {
            "overall_confidence": overall,
            "needs_review_fields": needs_review_fields,
            "review_threshold": settings.confidence_review_threshold,
        },
    }


def run_on_path(
    path: str | Path,
    kind: str,
    schema: DocSchema,
    provider: LLMProvider | None = None,
    settings: Settings | None = None,
) -> dict[str, Any]:
    settings = settings or get_settings()
    extracted = extract_text(path, kind, settings)
    return run_pipeline(extracted, schema, provider, settings)
