import io
import base64
import logging
from PIL import Image
import config
from backend.exceptions import ModerationUnavailableError
from backend.moderation.openai_moderation import check_openai_moderation
from backend.moderation.gemini_moderation import check_gemini_moderation

logger = logging.getLogger("cevondocs")


class ModerationResult(tuple):
    """
    2-element tuple (is_safe, blocked_reason) with moderation_status property.
    Supports unpacking as (is_safe, reason) while exposing .moderation_status.
    """
    def __new__(cls, is_safe: bool, blocked_reason: str | None, moderation_status: str = "PASSED"):
        obj = super().__new__(cls, (is_safe, blocked_reason))
        obj.is_safe = is_safe
        obj.blocked_reason = blocked_reason
        obj.moderation_status = moderation_status
        return obj


def _check_basic_image_validation(b64_image: str) -> tuple[bool, str | None]:
    """
    Validates base64 string, image format, integrity, and file size.
    Returns (is_valid, blocked_reason).
    """
    if not b64_image:
        return False, "empty_image_data"

    try:
        image_bytes = base64.b64decode(b64_image)
    except Exception:
        return False, "invalid_base64_encoding"

    if not image_bytes:
        return False, "empty_file"

    # Max file size limit: 20 MB
    max_bytes = 20 * 1024 * 1024
    if len(image_bytes) > max_bytes:
        return False, "file_size_exceeded"

    try:
        img = Image.open(io.BytesIO(image_bytes))
        img.verify()
        # Re-open after verify() since verify() alters PIL internal state
        img = Image.open(io.BytesIO(image_bytes))
        fmt = (img.format or "").upper()
        if fmt not in ["PNG", "JPEG", "JPG"]:
            return False, f"unsupported_image_format_{fmt}"
    except Exception as e:
        logger.warning(f"Image validation failed: {e}")
        return False, "corrupted_or_invalid_image"

    return True, None


def _is_configured_key(key: str | None) -> bool:
    if not key:
        return False
    k = key.strip().lower()
    return bool(k) and not k.startswith("your-") and not k.startswith("your_")


def check_moderation(b64_image: str) -> ModerationResult:
    """
    Modular, provider-agnostic moderation gate.
    1. Performs local basic image validation (format, integrity, size).
    2. Routes to selected or best available moderation provider.
    Fails closed: raises ModerationUnavailableError if configured provider fails.
    If no moderation provider is configured (local mode or auto without keys), runs local validation only and marks moderation_status="LOCAL_ONLY".
    Returns ModerationResult(is_safe, blocked_reason, moderation_status).
    """
    # 1. Local basic image validation
    is_valid, invalid_reason = _check_basic_image_validation(b64_image)
    if not is_valid:
        return ModerationResult(False, invalid_reason, "BLOCKED")

    provider = (config.MODERATION_PROVIDER or "auto").lower()

    if provider == "auto":
        if _is_configured_key(config.OPENAI_API_KEY):
            logger.info("Auto-selected moderation provider: openai")
            try:
                is_safe, reason = check_openai_moderation(b64_image)
                return ModerationResult(is_safe, reason, "PASSED" if is_safe else "BLOCKED")
            except ModerationUnavailableError as e:
                if _is_configured_key(config.GEMINI_API_KEY):
                    logger.warning(f"OpenAI moderation failed in auto mode ({e.message}), attempting Gemini fallback")
                    try:
                        is_safe, reason = check_gemini_moderation(b64_image)
                        return ModerationResult(is_safe, reason, "PASSED" if is_safe else "BLOCKED")
                    except ModerationUnavailableError as g_err:
                        logger.error(f"Gemini moderation fallback also failed ({g_err.message})")
                        raise g_err
                else:
                    logger.error(f"OpenAI moderation failed in auto mode and no Gemini key available: {e.message}")
                    raise e

        if _is_configured_key(config.GEMINI_API_KEY):
            logger.info("Auto-selected moderation provider: gemini")
            try:
                is_safe, reason = check_gemini_moderation(b64_image)
                return ModerationResult(is_safe, reason, "PASSED" if is_safe else "BLOCKED")
            except ModerationUnavailableError as e:
                logger.error(f"Gemini moderation failed in auto mode: {e.message}")
                raise e

        # Neither OpenAI nor Gemini API keys configured
        logger.info("Auto-selected moderation provider: local (no API keys provided)")
        return ModerationResult(True, None, "LOCAL_ONLY")

    elif provider == "openai":
        is_safe, reason = check_openai_moderation(b64_image)
        return ModerationResult(is_safe, reason, "PASSED" if is_safe else "BLOCKED")

    elif provider == "gemini":
        is_safe, reason = check_gemini_moderation(b64_image)
        return ModerationResult(is_safe, reason, "PASSED" if is_safe else "BLOCKED")

    elif provider in ["local", "none", ""]:
        logger.info("Moderation provider set to local (local validation only)")
        return ModerationResult(True, None, "LOCAL_ONLY")

    else:
        raise ValueError(f"Unsupported moderation provider: '{provider}'")

