"""Post-processing normalization rules.

Turns noisy model output into consistent, application-ready values: ISO dates,
numeric currency, digit-normalized phones, lowercased emails, tidy whitespace.
Normalization is type-driven and can be disabled per field via ``normalize``.
"""
from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from app.schemas.base import FieldSpec

_DATE_FORMATS = [
    "%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y", "%m-%d-%Y",
    "%d.%m.%Y", "%B %d, %Y", "%b %d, %Y", "%d %B %Y", "%d %b %Y",
    "%Y/%m/%d", "%d/%m/%y", "%m/%d/%y",
]


def normalize_date(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    raw = value.strip()
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(raw, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return raw  # leave as-is if unrecognized; validation will flag it


def normalize_number(value: Any) -> Any:
    if isinstance(value, (int, float)):
        return value
    if not isinstance(value, str):
        return value
    cleaned = re.sub(r"[^\d.\-]", "", value.replace(",", ""))
    if cleaned in {"", "-", ".", "-."}:
        return value
    try:
        num = float(cleaned)
        return int(num) if num.is_integer() else num
    except ValueError:
        return value


def normalize_phone(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    digits = re.sub(r"[^\d+]", "", value)
    return digits or value


def normalize_email(value: Any) -> Any:
    if isinstance(value, str):
        return value.strip().lower()
    return value


def normalize_string(value: Any) -> Any:
    if isinstance(value, str):
        return re.sub(r"\s+", " ", value).strip()
    return value


def normalize_value(spec: FieldSpec, value: Any) -> Any:
    if value is None or not spec.normalize:
        return value
    if spec.many and isinstance(value, list):
        return [normalize_value(_scalar_spec(spec), v) for v in value]

    if spec.type == "date":
        return normalize_date(value)
    if spec.type in {"number", "integer", "currency"}:
        return normalize_number(value)
    if spec.type == "phone":
        return normalize_phone(value)
    if spec.type == "email":
        return normalize_email(value)
    if spec.type in {"string", "text"}:
        return normalize_string(value)
    return value


def _scalar_spec(spec: FieldSpec) -> FieldSpec:
    return FieldSpec(
        name=spec.name, type=spec.type, description=spec.description,
        pattern=spec.pattern, enum=spec.enum, normalize=spec.normalize,
    )
