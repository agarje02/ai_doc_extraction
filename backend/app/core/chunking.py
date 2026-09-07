"""Token-aware, page-aware chunking.

Splits extracted text into overlapping chunks that stay under a token budget
while remembering which page(s) each chunk came from. Uses ``tiktoken`` when
available and falls back to a word-count approximation otherwise.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

from app.config import Settings, get_settings

from .text_extraction import ExtractedText


@dataclass
class Chunk:
    index: int
    text: str
    page_start: int
    page_end: int
    token_count: int


@lru_cache
def _encoder():
    try:
        import tiktoken

        return tiktoken.get_encoding("cl100k_base")
    except Exception:  # pragma: no cover - tiktoken optional/offline
        return None


def count_tokens(text: str) -> int:
    enc = _encoder()
    if enc is None:
        return max(1, len(text.split()))
    return len(enc.encode(text))


@dataclass
class _Unit:
    page: int
    text: str
    tokens: int


def _units(extracted: ExtractedText) -> list[_Unit]:
    """Split each page into line-level units for packing into chunks."""
    units: list[_Unit] = []
    for page in extracted.pages:
        for line in page.text.splitlines():
            line = line.strip()
            if not line:
                continue
            units.append(_Unit(page.page_number, line, count_tokens(line)))
    return units


def chunk_document(
    extracted: ExtractedText, settings: Settings | None = None
) -> list[Chunk]:
    settings = settings or get_settings()
    max_tokens = max(64, settings.chunk_max_tokens)
    overlap = max(0, min(settings.chunk_overlap_tokens, max_tokens // 2))

    units = _units(extracted)
    chunks: list[Chunk] = []
    buf: list[_Unit] = []
    buf_tokens = 0

    def flush() -> None:
        nonlocal buf, buf_tokens
        if not buf:
            return
        text = "\n".join(u.text for u in buf)
        chunks.append(
            Chunk(
                index=len(chunks),
                text=text,
                page_start=buf[0].page,
                page_end=buf[-1].page,
                token_count=buf_tokens,
            )
        )
        # Seed the next buffer with a token-bounded overlap tail for context.
        if overlap and buf:
            tail: list[_Unit] = []
            t = 0
            for u in reversed(buf):
                if t + u.tokens > overlap:
                    break
                tail.insert(0, u)
                t += u.tokens
            buf = tail
            buf_tokens = t
        else:
            buf = []
            buf_tokens = 0

    for unit in units:
        # A single oversized line becomes its own chunk.
        if unit.tokens > max_tokens:
            flush()
            chunks.append(
                Chunk(len(chunks), unit.text, unit.page, unit.page, unit.tokens)
            )
            continue
        if buf_tokens + unit.tokens > max_tokens:
            flush()
        buf.append(unit)
        buf_tokens += unit.tokens

    flush()

    if not chunks and extracted.full_text.strip():
        chunks.append(Chunk(0, extracted.full_text.strip(), 1, 1, count_tokens(extracted.full_text)))
    return chunks
