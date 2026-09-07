"""Extraction endpoints: run extraction, fetch results, correct, export."""
from __future__ import annotations

import csv
import io
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.models.db import Document, ExtractionRun, get_session
from app.workflows.service import apply_correction, resolve_schema, run_extraction

router = APIRouter(prefix="/extractions", tags=["extractions"])


class RunRequest(BaseModel):
    document_id: str
    doc_type: str = "generic"
    custom_fields: list[dict[str, Any]] | None = None
    json_schema: dict[str, Any] | None = None


class CorrectionRequest(BaseModel):
    field_name: str
    value: Any


def _serialize(run: ExtractionRun) -> dict[str, Any]:
    return {
        "id": run.id,
        "document_id": run.document_id,
        "doc_type": run.doc_type,
        "provider": run.provider,
        "model": run.model,
        "status": run.status,
        "overall_confidence": run.overall_confidence,
        "created_at": run.created_at.isoformat() if run.created_at else None,
        "result": run.result,
    }


@router.post("", status_code=201)
def create_extraction(
    req: RunRequest, db: Session = Depends(get_session)
) -> dict[str, Any]:
    doc = db.get(Document, req.document_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")
    try:
        schema = resolve_schema(req.doc_type, req.custom_fields, req.json_schema)
    except KeyError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    run = run_extraction(db, doc, schema)
    return _serialize(run)


@router.get("")
def list_extractions(
    document_id: str | None = Query(default=None),
    db: Session = Depends(get_session),
) -> list[dict[str, Any]]:
    q = db.query(ExtractionRun)
    if document_id:
        q = q.filter(ExtractionRun.document_id == document_id)
    runs = q.order_by(ExtractionRun.created_at.desc()).all()
    return [_serialize(r) for r in runs]


@router.get("/{run_id}")
def get_extraction(run_id: str, db: Session = Depends(get_session)) -> dict[str, Any]:
    run = db.get(ExtractionRun, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Extraction run not found")
    return _serialize(run)


@router.post("/{run_id}/corrections")
def correct_field(
    run_id: str, req: CorrectionRequest, db: Session = Depends(get_session)
) -> dict[str, Any]:
    run = db.get(ExtractionRun, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Extraction run not found")
    run = apply_correction(db, run, req.field_name, req.value)
    return _serialize(run)


@router.get("/{run_id}/export")
def export_extraction(
    run_id: str,
    format: str = Query(default="json", pattern="^(json|csv)$"),
    db: Session = Depends(get_session),
) -> StreamingResponse:
    run = db.get(ExtractionRun, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Extraction run not found")

    if format == "json":
        import json

        buf = io.BytesIO(json.dumps(run.result, indent=2).encode("utf-8"))
        return StreamingResponse(
            buf,
            media_type="application/json",
            headers={"Content-Disposition": f'attachment; filename="{run_id}.json"'},
        )

    # CSV: one row per field.
    sio = io.StringIO()
    writer = csv.writer(sio)
    writer.writerow(["field", "value", "confidence", "needs_review", "page"])
    for name, field in (run.result or {}).get("fields", {}).items():
        value = field.get("value")
        if isinstance(value, list):
            value = "; ".join(str(v) for v in value)
        writer.writerow(
            [name, value, field.get("confidence"), field.get("needs_review"),
             field.get("page")]
        )
    out = io.BytesIO(sio.getvalue().encode("utf-8"))
    return StreamingResponse(
        out,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{run_id}.csv"'},
    )
