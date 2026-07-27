import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
import config
import utils
from schemas import InvoiceSchema, LineItem
from main import app
from backend.exceptions import SchemaValidationError, ProviderUnavailableError
import db

client = TestClient(app)
db.init_db()

DUMMY_INVOICE = InvoiceSchema(
    vendor='Test Vendor',
    vendor_confidence=0.9,
    invoice_number='INV-101',
    invoice_number_confidence=0.9,
    date='2026-07-22',
    date_confidence=0.9,
    currency='USD',
    currency_confidence=0.9,
    subtotal=100.0,
    subtotal_confidence=0.9,
    tax=10.0,
    tax_confidence=0.9,
    total=110.0,
    total_confidence=0.9,
    line_items=[
        LineItem(
            description='Item 1',
            quantity=1.0,
            unit_price=100.0,
            amount=100.0,
            confidence=0.9
        )
    ],
    overall_confidence=0.9
)
DUMMY_USAGE = {'prompt_tokens': 10, 'completion_tokens': 10, 'total_tokens': 20}


def create_dummy_png(width=100, height=100):
    import io
    from PIL import Image
    buf = io.BytesIO()
    img = Image.new('RGB', (width, height), color='white')
    img.save(buf, format='PNG')
    return buf.getvalue()


def test_missing_openai_key_returns_503():
    with patch.object(config, 'AI_PROVIDER', 'openai'), \
         patch.object(config, 'ENABLE_PROVIDER_FALLBACK', False), \
         patch.object(config, 'OPENAI_API_KEY', ''), \
         patch('moderation.check_moderation', return_value=(True, None)):
        files = {'file': ('test.png', create_dummy_png(), 'image/png')}
        response = client.post('/ingest', files=files)
        assert response.status_code == 503
        assert 'OPENAI_API_KEY is required' in response.json()['detail']


def test_missing_gemini_key_returns_503():
    with patch.object(config, 'AI_PROVIDER', 'gemini'), \
         patch.object(config, 'ENABLE_PROVIDER_FALLBACK', False), \
         patch.object(config, 'GEMINI_API_KEY', ''), \
         patch('moderation.check_moderation', return_value=(True, None)):
        files = {'file': ('test.png', create_dummy_png(), 'image/png')}
        response = client.post('/ingest', files=files)
        assert response.status_code == 503
        assert 'GEMINI_API_KEY is required' in response.json()['detail']


def test_missing_groq_key_returns_503():
    with patch.object(config, 'AI_PROVIDER', 'groq'), \
         patch.object(config, 'ENABLE_PROVIDER_FALLBACK', False), \
         patch.object(config, 'GROQ_API_KEY', ''), \
         patch('moderation.check_moderation', return_value=(True, None)):
        files = {'file': ('test.png', create_dummy_png(), 'image/png')}
        response = client.post('/ingest', files=files)
        assert response.status_code == 503
        assert 'GROQ_API_KEY is required' in response.json()['detail']


def test_invalid_provider_returns_503():
    with patch.object(config, 'AI_PROVIDER', 'invalid_provider'), \
         patch.object(config, 'ENABLE_PROVIDER_FALLBACK', False), \
         patch('moderation.check_moderation', return_value=(True, None)):
        files = {'file': ('test.png', create_dummy_png(), 'image/png')}
        response = client.post('/ingest', files=files)
        assert response.status_code == 503
        assert 'Unsupported AI provider' in response.json()['detail']


def test_blocked_image_never_reaches_extraction():
    with patch('moderation.check_moderation', return_value=(False, 'explicit_content')), \
         patch('extraction.extract_invoice') as mock_extract:
        files = {'file': ('test.png', create_dummy_png(), 'image/png')}
        response = client.post('/ingest', files=files)
        assert response.status_code == 422
        assert 'blocked by moderation gate' in response.json()['detail']
        mock_extract.assert_not_called()


def test_groq_invalid_schema_handling():
    from backend.ai.groq_provider import extract_groq
    mock_completion = MagicMock()
    mock_completion.choices = [MagicMock()]
    mock_completion.choices[0].message.content = '{"invalid_field": "no vendor here"}'
    mock_completion.usage = MagicMock(prompt_tokens=5, completion_tokens=5, total_tokens=10)

    with patch.object(config, 'GROQ_API_KEY', 'valid_key'), \
         patch('utils.retry_on_transient', return_value=mock_completion):
        with pytest.raises((ValueError, SchemaValidationError)) as exc_info:
            extract_groq(utils.image_to_base64(create_dummy_png()))
        assert 'failed schema validation' in str(exc_info.value) or 'did not conform' in str(exc_info.value)


def test_corrupted_image_validation():
    with patch.object(config, 'AI_PROVIDER', 'gemini'):
        files = {'file': ('test.png', b'not_a_valid_image_bytes', 'image/png')}
        response = client.post('/ingest', files=files)
        assert response.status_code == 422
        assert 'corrupted_or_invalid_image' in response.json()['detail']


def test_transient_retry_logic():
    attempts = 0
    def flaky_func():
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise Exception('RateLimitError: 429 Too Many Requests')
        return 'success'

    res = utils.retry_on_transient(flaky_func, max_retries=2, base_delay=0.01)
    assert res == 'success'
    assert attempts == 2


def test_upload_size_limit_exceeded():
    large_bytes = b"0" * (10 * 1024 * 1024 + 1)  # 10 MB + 1 byte
    files = {'file': ('large.png', large_bytes, 'image/png')}
    response = client.post('/ingest', files=files)
    assert response.status_code == 413
    assert 'File too large. Maximum upload size is 10 MB.' in response.json()['detail']


def test_approve_document_with_edited_line_items():
    import json
    doc_id = utils.generate_id()
    initial_json = json.dumps({
        "vendor": "Test Vendor",
        "vendor_confidence": 0.4,
        "line_items": [
            {"description": "Item 1", "quantity": 1.0, "unit_price": 10.0, "amount": 10.0, "confidence": 0.4}
        ]
    })
    db.insert_document(doc_id, "test.png", "pending_review", extracted_json=initial_json, created_at=utils.now_iso())

    edited_data = {
        "vendor": "Test Vendor",
        "vendor_confidence": 0.4,
        "line_items": [
            {"description": "Corrected Item 1", "quantity": 5.0, "unit_price": 10.0, "amount": 50.0, "confidence": 0.4}
        ]
    }

    response = client.post("/approve", json={"document_id": doc_id, "reviewed_data": edited_data})
    assert response.status_code == 200
    assert response.json()["status"] == "approved"

    updated_doc = db.get_document(doc_id)
    assert updated_doc["status"] == "approved"
    reviewed = json.loads(updated_doc["reviewed_json"])
    assert reviewed["line_items"][0]["description"] == "Corrected Item 1"
    assert reviewed["line_items"][0]["quantity"] == 5.0
    assert reviewed["line_items"][0]["amount"] == 50.0


def test_groq_normalization_layer():
    from backend.ai.normalizer import normalize_invoice_json, CONFIDENCE_TIERS
    raw_groq_output = {
        "vendor": "Seaside Sushi",
        "date": "2026-07-22",
        "subtotal": 70.85,
        "tax": 5.0,
        "total": 75.85,
        "line_items": [
            {
                "description": "Rainbow Roll",
                "quantity": 1,
                "price": 15.95
            },
            {
                "description": "Spider Roll",
                "quantity": 2,
                "price": 14.95
            }
        ]
    }

    normalized = normalize_invoice_json(raw_groq_output)
    parsed = InvoiceSchema.model_validate(normalized)

    assert parsed.vendor == "Seaside Sushi"
    assert parsed.vendor_confidence == CONFIDENCE_TIERS["EXPLICIT_EXTRACTED"]
    assert parsed.invoice_number_confidence == CONFIDENCE_TIERS["MISSING"]
    assert parsed.invoice_number == ""

    assert len(parsed.line_items) == 2
    assert parsed.line_items[0].description == "Rainbow Roll"
    assert parsed.line_items[0].unit_price == 15.95
    assert parsed.line_items[0].amount == 15.95
    assert parsed.line_items[0].confidence == CONFIDENCE_TIERS["NORMALIZED"]

    assert parsed.line_items[1].description == "Spider Roll"
    assert parsed.line_items[1].quantity == 2.0
    assert parsed.line_items[1].unit_price == 14.95
    assert parsed.line_items[1].amount == 29.90
    assert parsed.line_items[1].confidence == CONFIDENCE_TIERS["NORMALIZED"]
