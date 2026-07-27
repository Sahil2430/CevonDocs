from pii import redact_pii


def test_redact_ssn():
    raw = "Customer SSN: 123-45-6789 for tax identification"
    cleaned = redact_pii(raw)
    assert "123-45-6789" not in cleaned
    assert "[REDACTED]" in cleaned


def test_redact_email():
    raw = "Send receipt copy to billing.dept@enterprise-corp.com"
    cleaned = redact_pii(raw)
    assert "billing.dept@enterprise-corp.com" not in cleaned
    assert "[REDACTED]" in cleaned


def test_redact_phone():
    raw = "Support line: 800-555-0199 or +1-555-123-4567"
    cleaned = redact_pii(raw)
    assert "800-555-0199" not in cleaned
    assert "+1-555-123-4567" not in cleaned
    assert "[REDACTED]" in cleaned


def test_redact_aadhaar():
    raw = "Tax ID Aadhaar: 2345 5678 9012"
    cleaned = redact_pii(raw)
    assert "2345 5678 9012" not in cleaned
    assert "[REDACTED]" in cleaned


def test_clean_text_unmodified():
    raw = "Vendor: Acme Hardware Store, Invoice: INV-1001, Total: $149.99"
    cleaned = redact_pii(raw)
    assert cleaned == raw
