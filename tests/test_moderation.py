import pytest
from unittest.mock import patch, MagicMock
import config
import utils
from backend.exceptions import ModerationUnavailableError
from backend.moderation.router import check_moderation
from backend.moderation.openai_moderation import check_openai_moderation
from backend.moderation.gemini_moderation import check_gemini_moderation


def create_dummy_png_b64():
    import io
    from PIL import Image
    buf = io.BytesIO()
    img = Image.new('RGB', (100, 100), color='white')
    img.save(buf, format='PNG')
    return utils.image_to_base64(buf.getvalue())


def test_auto_moderation_selects_openai_when_key_present():
    b64 = create_dummy_png_b64()
    with patch.object(config, 'MODERATION_PROVIDER', 'auto'), \
         patch.object(config, 'OPENAI_API_KEY', 'valid_openai_key'), \
         patch('backend.moderation.router.check_openai_moderation', return_value=(True, None)) as mock_openai:
        res = check_moderation(b64)
        assert res[0] is True
        assert res[1] is None
        assert res.moderation_status == "PASSED"
        mock_openai.assert_called_once_with(b64)


def test_auto_moderation_selects_gemini_when_openai_key_missing():
    b64 = create_dummy_png_b64()
    with patch.object(config, 'MODERATION_PROVIDER', 'auto'), \
         patch.object(config, 'OPENAI_API_KEY', ''), \
         patch.object(config, 'GEMINI_API_KEY', 'valid_gemini_key'), \
         patch('backend.moderation.router.check_gemini_moderation', return_value=(True, None)) as mock_gemini:
        res = check_moderation(b64)
        assert res[0] is True
        assert res[1] is None
        assert res.moderation_status == "PASSED"
        mock_gemini.assert_called_once_with(b64)


def test_auto_moderation_falls_back_to_local_when_no_keys_present():
    b64 = create_dummy_png_b64()
    with patch.object(config, 'MODERATION_PROVIDER', 'auto'), \
         patch.object(config, 'OPENAI_API_KEY', ''), \
         patch.object(config, 'GEMINI_API_KEY', ''):
        res = check_moderation(b64)
        assert res[0] is True
        assert res[1] is None
        assert res.moderation_status == "LOCAL_ONLY"


def test_explicit_openai_moderation_fails_when_key_missing():
    b64 = create_dummy_png_b64()
    with patch.object(config, 'MODERATION_PROVIDER', 'openai'), \
         patch.object(config, 'OPENAI_API_KEY', ''):
        with pytest.raises(ModerationUnavailableError) as exc_info:
            check_moderation(b64)
        assert "OPENAI_API_KEY is required" in str(exc_info.value)


def test_explicit_gemini_moderation_fails_when_key_missing():
    b64 = create_dummy_png_b64()
    with patch.object(config, 'MODERATION_PROVIDER', 'gemini'), \
         patch.object(config, 'GEMINI_API_KEY', ''):
        with pytest.raises(ModerationUnavailableError) as exc_info:
            check_moderation(b64)
        assert "GEMINI_API_KEY is required" in str(exc_info.value)


def test_explicit_local_moderation():
    b64 = create_dummy_png_b64()
    with patch.object(config, 'MODERATION_PROVIDER', 'local'):
        res = check_moderation(b64)
        assert res[0] is True
        assert res[1] is None
        assert res.moderation_status == "LOCAL_ONLY"


def test_gemini_moderation_blocks_unsafe_image():
    b64 = create_dummy_png_b64()
    mock_response = MagicMock()
    mock_response.text = '{"is_safe": false, "blocked_reason": "violence"}'

    with patch.object(config, 'GEMINI_API_KEY', 'valid_key'), \
         patch('utils.retry_on_transient', return_value=mock_response):
        is_safe, reason = check_gemini_moderation(b64)
        assert is_safe is False
        assert reason == 'violence'


def test_gemini_moderation_api_timeout_raises_moderation_unavailable_error():
    b64 = create_dummy_png_b64()
    with patch.object(config, 'GEMINI_API_KEY', 'valid_key'), \
         patch('utils.retry_on_transient', side_effect=TimeoutError("Request timed out")):
        with pytest.raises(ModerationUnavailableError) as exc_info:
            check_gemini_moderation(b64)
        assert "Gemini Moderation API request failed" in str(exc_info.value)


def test_gemini_moderation_malformed_json_raises_moderation_unavailable_error():
    b64 = create_dummy_png_b64()
    mock_response = MagicMock()
    mock_response.text = "NOT_JSON_DATA"

    with patch.object(config, 'GEMINI_API_KEY', 'valid_key'), \
         patch('utils.retry_on_transient', return_value=mock_response):
        with pytest.raises(ModerationUnavailableError) as exc_info:
            check_gemini_moderation(b64)
        assert "malformed JSON" in str(exc_info.value)


def test_gemini_moderation_missing_is_safe_field_raises_moderation_unavailable_error():
    b64 = create_dummy_png_b64()
    mock_response = MagicMock()
    mock_response.text = '{"status": "ok"}'  # missing "is_safe"

    with patch.object(config, 'GEMINI_API_KEY', 'valid_key'), \
         patch('utils.retry_on_transient', return_value=mock_response):
        with pytest.raises(ModerationUnavailableError) as exc_info:
            check_gemini_moderation(b64)
        assert "missing required 'is_safe' field" in str(exc_info.value)


def test_gemini_moderation_empty_response_raises_moderation_unavailable_error():
    b64 = create_dummy_png_b64()
    mock_response = MagicMock()
    mock_response.text = ""  # empty text

    with patch.object(config, 'GEMINI_API_KEY', 'valid_key'), \
         patch('utils.retry_on_transient', return_value=mock_response):
        with pytest.raises(ModerationUnavailableError) as exc_info:
            check_gemini_moderation(b64)
        assert "empty response" in str(exc_info.value)


def test_openai_moderation_api_timeout_raises_moderation_unavailable_error():
    b64 = create_dummy_png_b64()
    with patch.object(config, 'OPENAI_API_KEY', 'valid_key'), \
         patch('utils.retry_on_transient', side_effect=TimeoutError("Connection timeout")):
        with pytest.raises(ModerationUnavailableError) as exc_info:
            check_openai_moderation(b64)
        assert "OpenAI Moderation API request failed" in str(exc_info.value)


def test_openai_moderation_provider_exception_raises_moderation_unavailable_error():
    b64 = create_dummy_png_b64()
    with patch.object(config, 'OPENAI_API_KEY', 'valid_key'), \
         patch('utils.retry_on_transient', side_effect=RuntimeError("API Exception")):
        with pytest.raises(ModerationUnavailableError) as exc_info:
            check_openai_moderation(b64)
        assert "OpenAI Moderation API request failed" in str(exc_info.value)

