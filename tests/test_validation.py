import pytest
from datetime import date, timedelta
from backend.validation import evaluate_validation, parse_invoice_date, ValidationResult


def test_valid_invoice_validation():
    data = {
        "vendor": "Acme Corp",
        "invoice_number": "INV-1001",
        "date": "2026-07-20",
        "currency": "USD",
        "subtotal": 100.0,
        "tax": 10.0,
        "total": 110.0,
        "line_items": [
            {"description": "Widget A", "quantity": 2.0, "unit_price": 50.0, "amount": 100.0, "confidence": 0.95}
        ],
        "overall_confidence": 0.95,
    }
    result = evaluate_validation(data)
    assert isinstance(result, ValidationResult)
    assert result.final_confidence >= 0.95
    assert len(result.failed_checks) == 0
    assert any("Financial totals verified" in c for c in result.passed_checks)
    assert any("Line item amounts sum matches subtotal" in c for c in result.passed_checks)


def test_incorrect_totals_validation():
    data = {
        "vendor": "Acme Corp",
        "invoice_number": "INV-1002",
        "date": "2026-07-20",
        "currency": "USD",
        "subtotal": 100.0,
        "tax": 10.0,
        "total": 150.0,  # Incorrect total (100 + 10 != 150)
        "overall_confidence": 0.90,
    }
    result = evaluate_validation(data)
    assert any("Subtotal + Tax" in c for c in result.failed_checks)
    assert result.confidence_adjustment < 0.0
    assert result.final_confidence < 0.90


def test_missing_vendor_validation():
    data = {
        "vendor": "",  # Missing vendor
        "invoice_number": "INV-1003",
        "date": "2026-07-20",
        "currency": "USD",
        "subtotal": 50.0,
        "tax": 5.0,
        "total": 55.0,
        "overall_confidence": 0.90,
    }
    result = evaluate_validation(data)
    assert any("Missing required field: Vendor Name" in c for c in result.failed_checks)


def test_missing_subtotal_validation():
    data = {
        "vendor": "Acme Corp",
        "invoice_number": "INV-1004",
        "date": "2026-07-20",
        "currency": "USD",
        "subtotal": 0.0,  # Missing subtotal
        "tax": 0.0,
        "total": 50.0,
        "overall_confidence": 0.85,
    }
    result = evaluate_validation(data)
    assert any("Missing required field: Subtotal Amount" in c for c in result.failed_checks)


def test_missing_currency_validation():
    data = {
        "vendor": "Acme Corp",
        "invoice_number": "INV-1005",
        "date": "2026-07-20",
        "currency": "",  # Missing currency
        "subtotal": 50.0,
        "tax": 5.0,
        "total": 55.0,
        "overall_confidence": 0.85,
    }
    result = evaluate_validation(data)
    assert any("Missing required field: Currency" in c for c in result.failed_checks)


def test_negative_values_validation():
    data = {
        "vendor": "Acme Corp",
        "invoice_number": "INV-1006",
        "date": "2026-07-20",
        "currency": "USD",
        "subtotal": -50.0,  # Negative subtotal
        "tax": 5.0,
        "total": -45.0,  # Negative total
        "line_items": [
            {"description": "Item", "quantity": -1.0, "unit_price": 50.0, "amount": -50.0, "confidence": 0.8}
        ],
        "overall_confidence": 0.85,
    }
    result = evaluate_validation(data)
    failed_text = " ".join(result.failed_checks)
    assert "Negative numeric value rejected" in failed_text or "Negative line item value rejected" in failed_text


def test_future_date_validation():
    future_dt = date.today() + timedelta(days=30)
    future_date_str = future_dt.strftime("%Y-%m-%d")
    data = {
        "vendor": "Acme Corp",
        "invoice_number": "INV-1007",
        "date": future_date_str,  # Future date
        "currency": "USD",
        "subtotal": 50.0,
        "tax": 5.0,
        "total": 55.0,
        "overall_confidence": 0.90,
    }
    result = evaluate_validation(data)
    assert any("Future invoice date detected" in c for c in result.failed_checks)


def test_low_resolution_image_validation():
    data = {
        "vendor": "Acme Corp",
        "invoice_number": "INV-1008",
        "date": "2026-07-20",
        "currency": "USD",
        "subtotal": 50.0,
        "tax": 5.0,
        "total": 55.0,
        "overall_confidence": 0.90,
    }
    img_meta = {"width": 300, "height": 400}  # Low resolution (< 500px)
    result = evaluate_validation(data, image_metadata=img_meta)
    assert any("Low resolution image" in w for w in result.warnings)
