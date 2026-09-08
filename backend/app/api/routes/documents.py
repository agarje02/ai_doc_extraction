"""Document endpoints: upload, list, fetch metadata, download raw file."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.ingestion import SUPPORTED_EXTENSIONS, detect_kind
from app.models.db import Document, get_session
from app.workflows.service import create_document

router = APIRouter(prefix="/documents", tags=["documents"])

# Owner/workspace ids must be short, url-safe tokens so they can be reused as
# stable keys on both the client (localStorage) and server (DB filter).
_OWNER_ID_RE = re.compile(r"^[A-Za-z0-9_-]{3,128}$")


def _validate_owner_id(owner_id: str) -> str:
    owner_id = (owner_id or "").strip()
    if not _OWNER_ID_RE.fullmatch(owner_id):
        raise HTTPException(
            status_code=422,
            detail=(
                "Invalid id. Use 3-128 characters: letters, numbers, hyphen or "
                "underscore."
            ),
        )
    return owner_id


def _serialize(doc: Document) -> dict[str, Any]:
    return {
        "id": doc.id,
        "owner_id": doc.owner_id,
        "filename": doc.filename,
        "kind": doc.kind,
        "size_bytes": doc.size_bytes,
        "created_at": doc.created_at.isoformat() if doc.created_at else None,
        "run_count": len(doc.runs),
    }


@router.post("", status_code=201)
async def upload_document(
    file: UploadFile = File(...),
    owner_id: str = Form(...),
    db: Session = Depends(get_session),
) -> dict[str, Any]:
    owner_id = _validate_owner_id(owner_id)
    try:
        detect_kind(file.filename or "")
    except ValueError as exc:
        raise HTTPException(status_code=415, detail=str(exc))
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")
    doc = create_document(db, file.filename or "upload", data, owner_id=owner_id)
    return _serialize(doc)


@router.get("")
def list_documents(
    owner_id: str, db: Session = Depends(get_session)
) -> list[dict[str, Any]]:
    owner_id = _validate_owner_id(owner_id)
    docs = (
        db.query(Document)
        .filter(Document.owner_id == owner_id)
        .order_by(Document.created_at.desc())
        .all()
    )
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
