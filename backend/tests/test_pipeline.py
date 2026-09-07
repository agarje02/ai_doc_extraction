from app.config import Settings
from app.core.llm.mock_provider import MockProvider
from app.core.text_extraction import ExtractedText, PageText
from app.schemas.registry import get_schema
from app.workflows.pipeline import run_pipeline

SETTINGS = Settings(llm_provider="mock", confidence_review_threshold=0.6)


def _invoice_text() -> ExtractedText:
    body = (
        "Invoice Number: INV-2024-0091\n"
        "Invoice Date: 2024-03-15\n"
        "Total Amount: $189.00\n"
        "Currency: USD\n"
    )
    return ExtractedText(pages=[PageText(1, body, "text")])


def test_invoice_extraction_produces_structured_data():
    schema = get_schema("invoice")
    result = run_pipeline(_invoice_text(), schema, MockProvider(), SETTINGS)

    data = result["data"]
    assert data["invoice_number"] == "INV-2024-0091"
    assert data["invoice_date"] == "2024-03-15"  # normalized ISO
    assert data["total_amount"] == 189  # normalized to number
    assert data["currency"] == "USD"

    assert result["doc_type"] == "invoice"
    assert result["meta"]["provider"] == "mock"
    assert 0.0 < result["review"]["overall_confidence"] <= 1.0


def test_every_schema_field_is_present_in_output():
    schema = get_schema("invoice")
    result = run_pipeline(_invoice_text(), schema, MockProvider(), SETTINGS)
    for spec in schema.fields:
        assert spec.name in result["fields"]
        assert spec.name in result["data"]


def test_missing_required_field_flags_review():
    schema = get_schema("invoice")
    empty = ExtractedText(pages=[PageText(1, "Nothing useful here.", "text")])
    result = run_pipeline(empty, schema, MockProvider(), SETTINGS)
    # invoice_number and total_amount are required -> should be flagged.
    assert "invoice_number" in result["review"]["needs_review_fields"]
