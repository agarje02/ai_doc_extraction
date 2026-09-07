"""Field validation: types, formats, regex patterns, enums and requiredness.

Produces a list of ``ValidationIssue``s per field (error | warning) that feed
both the confidence score and the review UI. Validation runs on already
normalized values.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from app.schemas.base import DocSchema, FieldSpec

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_PHONE_RE = re.compile(r"^\+?\d[\d]{6,}$")


@dataclass
class ValidationIssue:
    field: str
    severity: str  # "error" | "warning"
    message: str


def _check_scalar(spec: FieldSpec, value: Any) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    if spec.type in {"number", "integer", "currency"}:
        if not isinstance(value, (int, float)):
            issues.append(ValidationIssue(spec.name, "warning",
                          f"Expected a number, got {value!r}"))
    elif spec.type == "email":
        if isinstance(value, str) and not _EMAIL_RE.match(value):
            issues.append(ValidationIssue(spec.name, "warning",
                          f"Value does not look like an email: {value!r}"))
    elif spec.type == "date":
        if isinstance(value, str) and not _ISO_DATE_RE.match(value):
            issues.append(ValidationIssue(spec.name, "warning",
                          f"Date is not normalized to YYYY-MM-DD: {value!r}"))
    elif spec.type == "phone":
        if isinstance(value, str) and not _PHONE_RE.match(value):
            issues.append(ValidationIssue(spec.name, "warning",
                          f"Phone number looks malformed: {value!r}"))

    if spec.enum and value not in spec.enum:
        issues.append(ValidationIssue(spec.name, "error",
                      f"Value {value!r} not in allowed set {spec.enum}"))
    if spec.pattern and isinstance(value, str) and not re.search(spec.pattern, value):
        issues.append(ValidationIssue(spec.name, "warning",
                      f"Value {value!r} does not match pattern {spec.pattern}"))
    return issues


def validate_field(spec: FieldSpec, value: Any) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    if value is None or value == "" or value == []:
        if spec.required:
            issues.append(ValidationIssue(spec.name, "error",
                          "Required field is missing"))
        return issues

    if spec.many:
        if not isinstance(value, list):
            issues.append(ValidationIssue(spec.name, "warning",
                          "Expected a list of values"))
            return issues
        for item in value:
            issues.extend(_check_scalar(spec, item))
    else:
        issues.extend(_check_scalar(spec, value))
    return issues


def validate_extraction(
    schema: DocSchema, values: dict[str, Any]
) -> dict[str, list[ValidationIssue]]:
    out: dict[str, list[ValidationIssue]] = {}
    for spec in schema.fields:
        issues = validate_field(spec, values.get(spec.name))
        if issues:
            out[spec.name] = issues
    return out
