"""Document ingestion: persist an uploaded file and detect its type."""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from pathlib import Path

from app.config import get_settings

# Extension -> logical kind used to pick a text-extraction strategy.
_EXT_KIND = {
    ".pdf": "pdf",
    ".docx": "docx",
    ".doc": "docx",
    ".txt": "text",
    ".md": "text",
    ".png": "image",
    ".jpg": "image",
    ".jpeg": "image",
    ".tif": "image",
    ".tiff": "image",
    ".bmp": "image",
    ".webp": "image",
}

SUPPORTED_EXTENSIONS = sorted(_EXT_KIND.keys())


@dataclass
class StoredDocument:
    id: str
    filename: str
    stored_path: Path
    kind: str
    size_bytes: int


def detect_kind(filename: str) -> str:
    ext = Path(filename).suffix.lower()
    kind = _EXT_KIND.get(ext)
    if kind is None:
        raise ValueError(
            f"Unsupported file type {ext!r}. Supported: {', '.join(SUPPORTED_EXTENSIONS)}"
        )
    return kind


def save_upload(filename: str, data: bytes) -> StoredDocument:
    """Persist raw bytes under a unique id and return its metadata."""
    kind = detect_kind(filename)
    doc_id = uuid.uuid4().hex
    safe_name = Path(filename).name
    dest_dir = get_settings().storage_path / doc_id
    dest_dir.mkdir(parents=True, exist_ok=True)
    stored_path = dest_dir / safe_name
    stored_path.write_bytes(data)
    return StoredDocument(
        id=doc_id,
        filename=safe_name,
        stored_path=stored_path,
        kind=kind,
        size_bytes=len(data),
    )
