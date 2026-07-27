import json
import time
import base64
import logging
import config
import utils
from schemas import InvoiceSchema
from backend.prompts import GEMINI_SYSTEM_PROMPT, GEMINI_USER_PROMPT_TEMPLATE, GEMINI_PROMPT_VERSION
from backend.ai.normalizer import normalize_invoice_json
from backend.exceptions import ConfigurationError, InvalidProviderResponseError, SchemaValidationError
import metrics

logger = logging.getLogger("cevondocs")


def extract_gemini(b64_image: str, resized_b64: str | None = None) -> tuple[InvoiceSchema, dict]:
    """
    Calls Gemini vision API with response_schema=InvoiceSchema and shared normalization pipeline.
    Returns (parsed_schema, usage_stats).
    """
    if not config.GEMINI_API_KEY:
        logger.warning("GEMINI_API_KEY is required for Gemini vision extraction.")
        raise ConfigurationError("GEMINI_API_KEY is required for Gemini vision extraction.")

    if not resized_b64:
        resized_b64 = utils.resize_image_b64(b64_image, config.MAX_IMAGE_DIMENSION)

    mime_type = utils.detect_mime_type(resized_b64)
    image_bytes = base64.b64decode(resized_b64)

    from google import genai
    from google.genai import types

    client = genai.Client(api_key=config.GEMINI_API_KEY)
    model_name = config.GEMINI_MODEL

    start_time = time.time()
    metrics.provider_requests_total.labels(provider="gemini", model=model_name).inc()

    image_part = types.Part.from_bytes(
        data=image_bytes,
        mime_type=mime_type,
    )

    def _call_extraction():
        return client.models.generate_content(
            model=model_name,
            contents=[
                image_part,
                f"{GEMINI_SYSTEM_PROMPT}\n{GEMINI_USER_PROMPT_TEMPLATE}"
            ],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
            ),
        )

    try:
        response = utils.retry_on_transient(_call_extraction, provider="gemini")
    except Exception as e:
        from backend.exceptions import CevonDocsError
        if isinstance(e, CevonDocsError):
            raise
        logger.error(f"Gemini vision API execution failed: {e}")
        raise InvalidProviderResponseError(f"Gemini vision API execution failed: {e}", provider="gemini")
    latency = time.time() - start_time
    metrics.provider_latency_seconds.labels(provider="gemini").observe(latency)

    if not response.text:
        metrics.provider_failures_total.labels(provider="gemini", error_type="InvalidProviderResponseError").inc()
        raise InvalidProviderResponseError("Gemini extraction returned empty response.", provider="gemini")

    raw_json_size = len(response.text)
    try:
        raw_dict = json.loads(response.text)
    except Exception as e:
        metrics.provider_failures_total.labels(provider="gemini", error_type="InvalidProviderResponseError").inc()
        raise InvalidProviderResponseError(f"Gemini output was not valid JSON: {e}", provider="gemini", raw_response=response.text)

    try:
        normalized_dict = normalize_invoice_json(raw_dict)
        parsed_schema = InvoiceSchema.model_validate(normalized_dict)
    except Exception as e:
        metrics.schema_validation_failures_total.labels(provider="gemini").inc()
        metrics.provider_failures_total.labels(provider="gemini", error_type="SchemaValidationError").inc()
        logger.error(f"Gemini output failed InvoiceSchema validation. Raw JSON size: {raw_json_size} bytes. Missing/invalid fields: {e}")
        raise SchemaValidationError(f"Gemini response failed schema validation: {e}", provider="gemini")

    usage_meta = getattr(response, "usage_metadata", None)
    prompt_tokens = getattr(usage_meta, "prompt_token_count", 0) if usage_meta else 0
    completion_tokens = getattr(usage_meta, "candidates_token_count", 0) if usage_meta else 0
    total_tokens = getattr(usage_meta, "total_token_count", 0) if usage_meta else (prompt_tokens + completion_tokens)

    usage = {
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": total_tokens,
        "latency_seconds": round(latency, 3),
        "raw_json_bytes": raw_json_size,
        "prompt_version": GEMINI_PROMPT_VERSION,
    }

    logger.info(
        f"Gemini vision extraction successful. Provider: gemini, Model: {model_name}, "
        f"Latency: {usage['latency_seconds']}s, Size: {raw_json_size}B, Prompt Tokens: {usage['prompt_tokens']}, "
        f"Completion Tokens: {usage['completion_tokens']}, Total Tokens: {usage['total_tokens']}"
    )
    return parsed_schema, usage
