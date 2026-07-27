import pytest
from pydantic import ValidationError
from schemas import InvoiceSchema, LineItem


def test_line_item_schema():
    item = LineItem(
        description="Office Desk Chair",
        quantity=2.0,
        unit_price=120.00,
        amount=240.00,
        confidence=0.95
    )
    assert item.description == "Office Desk Chair"
    assert item.quantity == 2.0
    assert item.amount == 240.00
    assert item.confidence == 0.95


def test_invoice_schema_valid_instantiation():
    invoice = InvoiceSchema(
        vendor="Acme Furniture Store",
        vendor_confidence=0.98,
        invoice_number="INV-2026-001",
        invoice_number_confidence=0.92,
        date="2026-07-22",
        date_confidence=0.90,
        currency="USD",
        currency_confidence=1.0,
        subtotal=240.00,
        subtotal_confidence=0.95,
        tax=24.00,
        tax_confidence=0.95,
        total=264.00,
        total_confidence=0.99,
        line_items=[
            LineItem(
                description="Office Desk Chair",
                quantity=2.0,
                unit_price=120.00,
                amount=240.00,
                confidence=0.95
            )
        ],
        overall_confidence=0.95
    )
    assert invoice.vendor == "Acme Furniture Store"
    assert invoice.total == 264.00
    assert len(invoice.line_items) == 1


def test_schema_json_roundtrip():
    original = InvoiceSchema(
        vendor="Tech Supplies Inc",
        vendor_confidence=0.99,
        invoice_number="TS-994",
        invoice_number_confidence=0.95,
        date="2026-07-22",
        date_confidence=0.95,
        currency="USD",
        currency_confidence=1.0,
        subtotal=500.0,
        subtotal_confidence=0.98,
        tax=50.0,
        tax_confidence=0.98,
        total=550.0,
        total_confidence=0.99,
        line_items=[
            LineItem(
                description="Monitor",
                quantity=1.0,
                unit_price=500.0,
                amount=500.0,
                confidence=0.99
            )
        ],
        overall_confidence=0.98
    )

    json_str = original.model_dump_json()

    # Deserialize back from JSON
    restored = InvoiceSchema.model_validate_json(json_str)

    assert restored == original
    assert restored.vendor == original.vendor
    assert restored.total == original.total


def test_schema_validation_error():
    with pytest.raises(ValidationError):
        # Passing invalid data type for total (string that cannot be converted to float)
        InvoiceSchema(
            vendor="Test Store",
            vendor_confidence=0.9,
            invoice_number="123",
            invoice_number_confidence=0.9,
            date="2026-07-22",
            date_confidence=0.9,
            currency="USD",
            currency_confidence=1.0,
            subtotal=10.0,
            subtotal_confidence=0.9,
            tax=1.0,
            tax_confidence=0.9,
            total="invalid-amount-not-a-number",
            total_confidence=0.9,
            line_items=[],
            overall_confidence=0.9
        )
