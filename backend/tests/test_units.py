from app.config import Settings
from app.core.chunking import chunk_document, count_tokens
from app.core.confidence import score_field
from app.core.postprocess import (
    normalize_date,
    normalize_email,
    normalize_number,
    normalize_phone,
)
from app.core.text_extraction import ExtractedText, PageText
from app.schemas.generic import schema_from_json_schema
from app.schemas.registry import get_schema, list_schemas


def test_registry_has_builtin_types():
    keys = {s.key for s in list_schemas()}
    assert {"invoice", "resume", "contract", "generic"} <= keys


def test_normalizers():
    assert normalize_date("03/15/2024") == "2024-03-15"
    assert normalize_date("March 15, 2024") == "2024-03-15"
    assert normalize_number("$1,234.50") == 1234.5
    assert normalize_number("42") == 42
    assert normalize_phone("+49 (151) 234-5678") == "+491512345678"
    assert normalize_email("  Jane@Example.COM ") == "jane@example.com"


def test_chunking_tracks_pages():
    pages = [
        PageText(1, "\n".join(f"line {i}" for i in range(50)), "text"),
        PageText(2, "\n".join(f"more {i}" for i in range(50)), "text"),
    ]
    settings = Settings(chunk_max_tokens=64, chunk_overlap_tokens=8)
    chunks = chunk_document(ExtractedText(pages=pages), settings)
    assert len(chunks) >= 2
    assert chunks[0].page_start == 1
    assert any(c.page_end == 2 for c in chunks)
    assert all(c.token_count <= 64 for c in chunks)


def test_count_tokens_nonzero():
    assert count_tokens("hello world") >= 1


def test_generic_schema_from_json_schema():
    js = {
        "properties": {
            "policy_number": {"type": "string", "description": "id"},
            "premium": {"type": "number"},
            "beneficiaries": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["policy_number"],
    }
    schema = schema_from_json_schema("policy", "Policy", js)
    fmap = schema.field_map()
    assert fmap["policy_number"].required is True
    assert fmap["premium"].type == "number"
    assert fmap["beneficiaries"].many is True


def test_confidence_source_boost_and_error_penalty():
    high, review = score_field(
        value="INV-1",
        model_confidence=0.7,
        source_text="INV-1",
        document_text="the id is INV-1 here",
        issues=[],
        review_threshold=0.6,
    )
    assert high > 0.7
    assert review is False

    low, review2 = score_field(
        value=None,
        model_confidence=None,
        source_text=None,
        document_text="",
        issues=[],
        review_threshold=0.6,
    )
    assert low == 0.0


def test_invoice_schema_prompt_json_schema_shape():
    schema = get_schema("invoice")
    js = schema.prompt_json_schema()
    assert js["type"] == "object"
    assert "fields" in js["properties"]
