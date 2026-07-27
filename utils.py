import io
import uuid
import time
import base64
import logging
from datetime import datetime, timezone
from pathlib import Path
from PIL import Image

logger = logging.getLogger("cevondocs")


def generate_id() -> str:
    """Generate a UUID4 string."""
    return str(uuid.uuid4())


def now_iso() -> str:
    """Current UTC timestamp in ISO format."""
    return datetime.now(timezone.utc).isoformat()


def image_to_base64(image_bytes: bytes) -> str:
    """Encode raw image bytes to base64 string."""
    return base64.standard_b64encode(image_bytes).decode("utf-8")


def detect_mime_type(b64_image: str) -> str:
    """
    Detects MIME type (image/png or image/jpeg) from base64 encoded image using PIL.
    Defaults to 'image/png' if detection fails or format is unsupported.
    """
    try:
        image_bytes = base64.b64decode(b64_image)
        img = Image.open(io.BytesIO(image_bytes))
        fmt = (img.format or "").upper()
        if fmt in ("JPEG", "JPG"):
            return "image/jpeg"
        return "image/png"
    except Exception as e:
        logger.warning(f"MIME type detection failed, defaulting to image/png: {e}")
        return "image/png"


def resize_image_b64(b64_image: str, max_dim: int = 2048) -> str:
    """Resizes base64 encoded image to keep max dimension <= max_dim."""
    try:
        image_bytes = base64.b64decode(b64_image)
        img = Image.open(io.BytesIO(image_bytes))
        width, height = img.size

        if width > max_dim or height > max_dim:
            img.thumbnail((max_dim, max_dim), Image.Resampling.LANCZOS)
            buffer = io.BytesIO()
            fmt = img.format if img.format else "PNG"
            img.save(buffer, format=fmt)
            return base64.b64encode(buffer.getvalue()).decode("utf-8")
        return b64_image
    except Exception as e:
        logger.warning(f"Image resize failed, proceeding with original: {e}")
        return b64_image


def save_upload(image_bytes: bytes, upload_dir: Path, doc_id: str, filename: str) -> Path:
    """Save uploaded image to uploads/{doc_id}/original.{ext}. Returns saved path."""
    doc_dir = upload_dir / doc_id
    doc_dir.mkdir(parents=True, exist_ok=True)
    ext = Path(filename).suffix.lower() if filename else ".png"
    if ext not in [".jpg", ".jpeg", ".png"]:
        ext = ".png"
    dest = doc_dir / f"original{ext}"
    dest.write_bytes(image_bytes)
    return dest


def retry_on_transient(fn, max_retries: int = 3, base_delay: float = 2.0, provider: str = "unknown"):
    """
    Call fn(). Retry on transient AI provider errors (HTTP 429, 500, 502, 503, 504, timeout).
    Exponential backoff: 2s -> 4s -> 8s (max 3 attempts).
    Do NOT retry 401 unauthorized, malformed JSON, or schema validation failures.
    Returns fn() result on success, raises on final failure.
    """
    import metrics

    for attempt in range(max_retries):
        try:
            return fn()
        except Exception as e:
            error_name = type(e).__name__.lower()
            error_str = str(e).lower()

            # Non-transient errors: DO NOT RETRY
            non_transient_keywords = [
                "401", "unauthorized", "invalid_api_key", "authentication",
                "schemavalidationerror", "invalidproviderresponseerror", "jsondecodeerror"
            ]
            if any(kw in error_name or kw in error_str for kw in non_transient_keywords):
                raise

            # Transient errors: RETRY
            transient_keywords = [
                "ratelimiterror", "apitimeouterror", "internalservererror",
                "apiconnectionerror", "resourceexhausted", "serviceunavailable",
                "too_many_requests", "rate_limit", "timeout", "503", "429", "500", "502", "504"
            ]
            is_transient = any(kw in error_name or kw in error_str for kw in transient_keywords)

            if not is_transient or attempt == max_retries - 1:
                raise

            delay = base_delay * (2 ** attempt)  # 2s, 4s, 8s
            metrics.provider_retries_total.labels(provider=provider).inc()
            logger.warning(
                f"Transient error ({type(e).__name__}) for provider '{provider}', retrying in {delay}s (attempt {attempt + 1}/{max_retries})"
            )
            time.sleep(delay)
