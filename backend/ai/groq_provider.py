import json
import time
import logging
import config
import utils
from schemas import InvoiceSchema
from backend.prompts import GROQ_SYSTEM_PROMPT, GROQ_USER_PROMPT_TEMPLATE, GROQ_PROMPT_VERSION
from backend.ai.normalizer import normalize_invoice_json
from backend.exceptions import ConfigurationError, InvalidProviderResponseError, SchemaValidationError
import metrics

logger = logging.getLogger("cevondocs")

# Alias for backwards compatibility
_normalize_groq_json = normalize_invoice_json


def extract_groq(b64_image: str, resized_b64: str | None = None) -> tuple[InvoiceSchema, dict]:
    """
    Calls Groq vision API with JSON output format and shared normalization pipeline.
    Returns (parsed_schema, usage_stats).
    """
    if not config.GROQ_API_KEY:
        logger.warning("GROQ_API_KEY is required for Groq vision extraction.")
        raise ConfigurationError("GROQ_API_KEY is required for Groq vision extraction.")

    if not resized_b64:
        resized_b64 = utils.resize_image_b64(b64_image, config.MAX_IMAGE_DIMENSION)

    mime_type = utils.detect_mime_type(resized_b64)
    from groq import Groq

    client = Groq(api_key=config.GROQ_API_KEY)
    model_name = config.GROQ_MODEL

    start_time = time.time()
    metrics.provider_requests_total.labels(provider="groq", model=model_name).inc()

    def _call_extraction():
        return client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": GROQ_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{mime_type};base64,{resized_b64}"
                            }
                        },
                        {
                            "type": "text",
                            "text": GROQ_USER_PROMPT_TEMPLATE
                        }
                    ]
                }
            ],
            response_format={"type": "json_object"},
        )

    try:
        completion = utils.retry_on_transient(_call_extraction, provider="groq")
    except Exception as e:
        from backend.exceptions import CevonDocsError
        if isinstance(e, CevonDocsError):
            raise
        logger.error(f"Groq vision API execution failed: {e}")
        raise InvalidProviderResponseError(f"Groq vision API execution failed: {e}", provider="groq")
    latency = time.time() - start_time
    metrics.provider_latency_seconds.labels(provider="groq").observe(latency)

    content = completion.choices[0].message.content
    if not content:
        metrics.provider_failures_total.labels(provider="groq", error_type="InvalidProviderResponseError").inc()
        raise InvalidProviderResponseError("Groq extraction returned empty response.", provider="groq")

    raw_json_size = len(content)
    try:
        raw_json = json.loads(content)
    except Exception as e:
        metrics.provider_failures_total.labels(provider="groq", error_type="InvalidProviderResponseError").inc()
        raise InvalidProviderResponseError(f"Groq output was not valid JSON: {e}", provider="groq", raw_response=content)

    try:
        normalized_dict = normalize_invoice_json(raw_json)
        parsed_schema = InvoiceSchema.model_validate(normalized_dict)
    except Exception as e:
        metrics.schema_validation_failures_total.labels(provider="groq").inc()
        metrics.provider_failures_total.labels(provider="groq", error_type="SchemaValidationError").inc()
        logger.error(f"Groq response failed InvoiceSchema validation. Raw JSON size: {raw_json_size} bytes. Missing/invalid fields: {e}")
        raise SchemaValidationError(f"Groq extraction output did not conform to InvoiceSchema: {e}", provider="groq")

    usage = {
        "prompt_tokens": completion.usage.prompt_tokens if completion.usage else 0,
        "completion_tokens": completion.usage.completion_tokens if completion.usage else 0,
        "total_tokens": completion.usage.total_tokens if completion.usage else 0,
        "latency_seconds": round(latency, 3),
        "raw_json_bytes": raw_json_size,
        "prompt_version": GROQ_PROMPT_VERSION,
    }

    logger.info(
        f"Groq vision extraction successful. Provider: groq, Model: {model_name}, "
        f"Latency: {usage['latency_seconds']}s, Size: {raw_json_size}B, Prompt Tokens: {usage['prompt_tokens']}, "
        f"Completion Tokens: {usage['completion_tokens']}, Total Tokens: {usage['total_tokens']}"
    )
    return parsed_schema, usage


