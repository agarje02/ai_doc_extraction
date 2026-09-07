"""Document endpoints: upload, list, fetch metadata, download raw file."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.ingestion import SUPPORTED_EXTENSIONS, detect_kind
from app.models.db import Document, get_session
from app.workflows.service import create_document

router = APIRouter(prefix="/documents", tags=["documents"])


def _serialize(doc: Document) -> dict[str, Any]:
    return {
        "id": doc.id,
        "filename": doc.filename,
        "kind": doc.kind,
        "size_bytes": doc.size_bytes,
        "created_at": doc.created_at.isoformat() if doc.created_at else None,
        "run_count": len(doc.runs),
    }


@router.post("", status_code=201)
async def upload_document(
    file: UploadFile = File(...), db: Session = Depends(get_session)
) -> dict[str, Any]:
    try:
        detect_kind(file.filename or "")
    except ValueError as exc:
        raise HTTPException(status_code=415, detail=str(exc))
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")
    doc = create_document(db, file.filename or "upload", data)
    return _serialize(doc)


@router.get("")
def list_documents(db: Session = Depends(get_session)) -> list[dict[str, Any]]:
    docs = db.query(Document).order_by(Document.created_at.desc()).all()
    return [_serialize(d) for d in docs]


@router.get("/supported-types")
def supported_types() -> dict[str, list[str]]:
    return {"extensions": SUPPORTED_EXTENSIONS}


@router.get("/{doc_id}")
def get_document(doc_id: str, db: Session = Depends(get_session)) -> dict[str, Any]:
    doc = db.get(Document, doc_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")
    payload = _serialize(doc)
    payload["runs"] = [
        {
            "id": r.id,
            "doc_type": r.doc_type,
            "overall_confidence": r.overall_confidence,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in sorted(doc.runs, key=lambda r: r.created_at or 0, reverse=True)
    ]
    return payload


@router.get("/{doc_id}/file")
def download_document(doc_id: str, db: Session = Depends(get_session)) -> FileResponse:
    doc = db.get(Document, doc_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")
    path = Path(doc.stored_path)
    if not path.exists():
        raise HTTPException(status_code=410, detail="Stored file is missing")
    return FileResponse(str(path), filename=doc.filename)
