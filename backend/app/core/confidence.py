"""Confidence scoring combining the model's self-report with heuristics.

Final score blends:
  - the model-reported confidence (or a neutral prior when absent),
  - a provenance boost when the source snippet is actually found in the
    document text (guards against hallucination),
  - a penalty for validation errors/warnings.

Fields scoring below the configured threshold (or with hard errors) are flagged
``needs_review`` for the human-in-the-loop UI.
"""
from __future__ import annotations

from typing import Any

from .validation import ValidationIssue


def _source_supported(source_text: str | None, document_text: str) -> bool:
    if not source_text:
        return False
    needle = source_text.strip().lower()
    if len(needle) < 3:
        return False
    return needle in document_text.lower()


def score_field(
    *,
    value: Any,
    model_confidence: float | None,
    source_text: str | None,
    document_text: str,
    issues: list[ValidationIssue],
    review_threshold: float,
) -> tuple[float, bool]:
    """Return ``(final_confidence, needs_review)``."""
    if value is None or value == "" or value == []:
        # Nothing extracted: zero confidence; needs review only if required
        # (that shows up as an error issue).
        has_error = any(i.severity == "error" for i in issues)
        return 0.0, has_error

    base = model_confidence if model_confidence is not None else 0.5
    score = base

    if _source_supported(source_text, document_text):
        score = min(1.0, score + 0.15)
    elif source_text:
        # Model cited a snippet we can't find verbatim - mild distrust.
        score = max(0.0, score - 0.1)

    errors = sum(1 for i in issues if i.severity == "error")
    warnings = sum(1 for i in issues if i.severity == "warning")
    score -= 0.4 * errors + 0.1 * warnings
    score = max(0.0, min(1.0, score))

    needs_review = score < review_threshold or errors > 0
    return round(score, 3), needs_review
