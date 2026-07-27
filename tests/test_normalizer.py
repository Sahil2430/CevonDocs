import pytest
from unittest.mock import patch, MagicMock
from schemas import InvoiceSchema
from backend.ai.normalizer import (
    normalize_invoice_json,
    normalize_line_items,
    normalize_confidence_fields,
    compute_overall_confidence,
    CONFIDENCE_TIERS,
)
from backend.exceptions import (
    InvalidProviderResponseError,
    SchemaValidationError,
    ProviderUnavailableError,
    RateLimitError,
    ConfigurationError,
    ModerationFailure,
)
import config
import extraction
import utils


def test_groq_returns_price_mapped_to_unit_price():
    raw_json = {
        "vendor": "Acme Corp",
        "line_items": [
            {"description": "Gadget", "quantity": 2, "price": 25.0}
        ]
    }
    normalized = normalize_invoice_json(raw_json)
    assert normalized["line_items"][0]["unit_price"] == 25.0
    assert normalized["line_items"][0]["amount"] == 50.0
    assert normalized["line_items"][0]["confidence"] == CONFIDENCE_TIERS["NORMALIZED"]


def test_openai_returns_unit_price():
    raw_json = {
        "vendor": "Acme Corp",
        "line_items": [
            {"description": "Widget", "quantity": 1, "unit_price": 49.99, "amount": 49.99, "confidence": 0.95}
        ]
    }
    normalized = normalize_invoice_json(raw_json)
    assert normalized["line_items"][0]["unit_price"] == 49.99
    assert normalized["line_items"][0]["amount"] == 49.99
    assert normalized["line_items"][0]["confidence"] == 0.95


def test_missing_confidence_fields_tier_defaults():
    raw_json = {
        "vendor": "Tech Store",
        "total": 100.0
    }
    normalized = normalize_invoice_json(raw_json)
    assert normalized["vendor_confidence"] == CONFIDENCE_TIERS["EXPLICIT_EXTRACTED"]
    assert normalized["tax_confidence"] == CONFIDENCE_TIERS["MISSING"]
    assert normalized["invoice_number_confidence"] == CONFIDENCE_TIERS["MISSING"]


def test_missing_line_item_amount_computed():
    raw_json = {
        "vendor": "Bakery",
        "line_items": [
            {"description": "Croissant", "quantity": 3, "unit_price": 3.50}
        ]
    }
    normalized = normalize_invoice_json(raw_json)
    assert normalized["line_items"][0]["amount"] == 10.50
    assert normalized["line_items"][0]["confidence"] == CONFIDENCE_TIERS["COMPUTED"]


def test_no_fabricated_currency_or_vendor_placeholders():
    raw_json = {
        "vendor": "Coffee Shop",
        "subtotal": 5.0,
        "total": 5.0
    }
    normalized = normalize_invoice_json(raw_json)
    assert normalized["currency"] == ""
    assert normalized["currency_confidence"] == CONFIDENCE_TIERS["MISSING"]
    assert normalized["invoice_number"] == ""
    assert normalized["invoice_number_confidence"] == CONFIDENCE_TIERS["MISSING"]


def test_overall_confidence_calculation():
    raw_json = {
        "vendor": "Hardware Store",
        "vendor_confidence": 0.90,
        "tax_confidence": 0.80,
        "line_items": [
            {"description": "Hammer", "quantity": 1, "unit_price": 15.0, "amount": 15.0, "confidence": 0.70}
        ]
    }
    normalized = normalize_invoice_json(raw_json)
    assert "overall_confidence" in normalized
    assert 0.0 <= normalized["overall_confidence"] <= 1.0


def test_retry_after_http_429():
    attempts = 0
    def flaky_api():
        nonlocal attempts
        attempts += 1
        if attempts < 2:
            raise Exception("HTTP 429 Rate limit exceeded")
        return "success"

    res = utils.retry_on_transient(flaky_api, max_retries=3, base_delay=0.01, provider="test")
    assert res == "success"
    assert attempts == 2


def test_provider_fallback_execution():
    dummy_invoice = InvoiceSchema(
        vendor="Fallback Vendor", vendor_confidence=0.9,
        invoice_number="INV-1", invoice_number_confidence=0.9,
        date="2026-07-22", date_confidence=0.9,
        currency="USD", currency_confidence=0.9,
        subtotal=10.0, subtotal_confidence=0.9,
        tax=1.0, tax_confidence=0.9,
        total=11.0, total_confidence=0.9,
        line_items=[], overall_confidence=0.9
    )

    with patch.object(config, "AI_PROVIDER", "groq"), \
         patch.object(config, "ENABLE_PROVIDER_FALLBACK", True), \
         patch("extraction.extract_groq", side_effect=ProviderUnavailableError("Groq 503 Service Unavailable")), \
         patch("extraction.extract_openai", side_effect=ProviderUnavailableError("OpenAI 503 Service Unavailable")), \
         patch("extraction.extract_gemini", return_value=(dummy_invoice, {"total_tokens": 10})) as mock_gemini:

        parsed, usage = extraction.extract_invoice("dHVtbXk=")
        assert parsed.vendor == "Fallback Vendor"
        mock_gemini.assert_called_once()


def test_invalid_json_raises_invalid_provider_response_error():
    from backend.ai.groq_provider import extract_groq
    mock_completion = MagicMock()
    mock_completion.choices = [MagicMock()]
    mock_completion.choices[0].message.content = "NOT_VALID_JSON_STRING"

    with patch.object(config, "GROQ_API_KEY", "valid_key"), \
         patch("utils.retry_on_transient", return_value=mock_completion):
        with pytest.raises(InvalidProviderResponseError) as exc_info:
            extract_groq("dummy_b64")
        assert exc_info.value.status_code == 422


def test_schema_validation_failure_raises_schema_validation_error():
    from backend.ai.groq_provider import extract_groq
    mock_completion = MagicMock()
    mock_completion.choices = [MagicMock()]
    mock_completion.choices[0].message.content = '{"unrecognized_key_only": 123}'

    with patch.object(config, "GROQ_API_KEY", "valid_key"), \
         patch("utils.retry_on_transient", return_value=mock_completion):
        with pytest.raises(SchemaValidationError) as exc_info:
            extract_groq("dummy_b64")
        assert exc_info.value.status_code == 422


def test_data_provenance_tracking():
    raw_json = {
        "vendor": "Target Store",
        "line_items": [
            {"description": "Paper Towels", "quantity": 2, "price": 4.50}
        ]
    }
    normalized = normalize_invoice_json(raw_json)
    assert "_provenance" in normalized
    prov = normalized["_provenance"]
    assert prov["vendor"] == "EXTRACTED"
    assert prov["invoice_number"] == "DEFAULTED"
    assert prov["line_items"][0]["description"] == "EXTRACTED"
    assert prov["line_items"][0]["unit_price"] == "NORMALIZED"
    assert prov["line_items"][0]["amount"] == "COMPUTED"
