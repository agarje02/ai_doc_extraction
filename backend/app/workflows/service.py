"""Service layer bridging the pipeline and persistence.

Shared by the REST API and the CLI so both create documents, run extractions,
and record corrections through the exact same code path.
"""
from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.core.ingestion import save_upload
from app.models.db import Correction, Document, ExtractionRun, FieldResult
from app.schemas.base import DocSchema
from app.schemas.generic import schema_from_fields, schema_from_json_schema
from app.schemas.registry import get_schema

from .pipeline import run_on_path


def create_document(db: Session, filename: str, data: bytes) -> Document:
    stored = save_upload(filename, data)
    doc = Document(
        id=stored.id,
        filename=stored.filename,
        kind=stored.kind,
        size_bytes=stored.size_bytes,
        stored_path=str(stored.stored_path),
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc


def resolve_schema(
    doc_type: str,
    custom_fields: list[dict[str, Any]] | None = None,
    json_schema: dict[str, Any] | None = None,
) -> DocSchema:
    """Pick a registered schema or build an ad-hoc one for generic extraction."""
    if custom_fields:
        return schema_from_fields(
            key=doc_type or "custom", name=doc_type or "Custom", fields=custom_fields
        )
    if json_schema:
        return schema_from_json_schema(
            key=doc_type or "custom", name=doc_type or "Custom", json_schema=json_schema
        )
    return get_schema(doc_type)


def run_extraction(
    db: Session,
    document: Document,
    schema: DocSchema,
) -> ExtractionRun:
    result = run_on_path(document.stored_path, document.kind, schema)
    run = ExtractionRun(
        document_id=document.id,
        doc_type=schema.key,
        provider=result["meta"]["provider"],
        model=result["meta"]["model"],
        status="completed",
        overall_confidence=result["review"]["overall_confidence"],
        result=result,
    )
    db.add(run)
    db.flush()  # assign run.id before adding children

    for name, field in result["fields"].items():
        db.add(
            FieldResult(
                run_id=run.id,
                name=name,
                value={"value": field["value"]},
                confidence=field["confidence"],
                needs_review=field["needs_review"],
                page=field["page"],
                source_text=field["source_text"],
                issues=field["issues"],
            )
        )
    db.commit()
    db.refresh(run)
    return run


def apply_correction(
    db: Session, run: ExtractionRun, field_name: str, value: Any
) -> ExtractionRun:
    """Persist a human correction and reflect it in the stored result."""
    db.add(
        Correction(run_id=run.id, field_name=field_name, corrected_value={"value": value})
    )

    fr = (
        db.query(FieldResult)
        .filter(FieldResult.run_id == run.id, FieldResult.name == field_name)
        .one_or_none()
    )
    if fr is not None:
        fr.value = {"value": value}
        fr.confidence = 1.0
        fr.needs_review = False
        fr.issues = []

    # Update the denormalized result blob too.
    result = dict(run.result or {})
    fields = dict(result.get("fields", {}))
    if field_name in fields:
        field = dict(fields[field_name])
        field.update(
            {"value": value, "confidence": 1.0, "needs_review": False,
             "issues": [], "corrected": True}
        )
        fields[field_name] = field
    result["fields"] = fields
    data = dict(result.get("data", {}))
    data[field_name] = value
    result["data"] = data
    review = dict(result.get("review", {}))
    review["needs_review_fields"] = [
        f for f in review.get("needs_review_fields", []) if f != field_name
    ]
    result["review"] = review
    run.result = result

    db.commit()
    db.refresh(run)
    return run
