import json
import time
import logging
from openai import OpenAI
import config
import utils
from schemas import InvoiceSchema
from backend.prompts import OPENAI_SYSTEM_PROMPT, OPENAI_USER_PROMPT_TEMPLATE, OPENAI_PROMPT_VERSION
from backend.ai.normalizer import normalize_invoice_json
from backend.exceptions import ConfigurationError, InvalidProviderResponseError, SchemaValidationError
import metrics

logger = logging.getLogger("cevondocs")


def extract_openai(b64_image: str, resized_b64: str | None = None) -> tuple[InvoiceSchema, dict]:
    """
    Calls OpenAI vision API with response_format=InvoiceSchema and shared normalization pipeline.
    Returns (parsed_schema, usage_stats).
    """
    if not config.OPENAI_API_KEY:
        logger.warning("OPENAI_API_KEY is required for OpenAI vision extraction.")
        raise ConfigurationError("OPENAI_API_KEY is required for OpenAI vision extraction.")

    if not resized_b64:
        resized_b64 = utils.resize_image_b64(b64_image, config.MAX_IMAGE_DIMENSION)

    mime_type = utils.detect_mime_type(resized_b64)
    client = OpenAI(api_key=config.OPENAI_API_KEY)
    model_name = config.OPENAI_MODEL

    start_time = time.time()
    metrics.provider_requests_total.labels(provider="openai", model=model_name).inc()

    def _call_extraction():
        return client.beta.chat.completions.parse(
            model=model_name,
            messages=[
                {"role": "system", "content": OPENAI_SYSTEM_PROMPT},
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
                            "text": OPENAI_USER_PROMPT_TEMPLATE
                        }
                    ]
                }
            ],
            response_format=InvoiceSchema,
        )

    completion = utils.retry_on_transient(_call_extraction, provider="openai")
    latency = time.time() - start_time
    metrics.provider_latency_seconds.labels(provider="openai").observe(latency)

    raw_message = completion.choices[0].message
    if hasattr(raw_message, "parsed") and raw_message.parsed:
        raw_dict = raw_message.parsed.model_dump()
    elif hasattr(raw_message, "content") and raw_message.content:
        try:
            raw_dict = json.loads(raw_message.content)
        except Exception as e:
            metrics.provider_failures_total.labels(provider="openai", error_type="InvalidProviderResponseError").inc()
            raise InvalidProviderResponseError(f"OpenAI response was not valid JSON: {e}", provider="openai", raw_response=raw_message.content)
    else:
        metrics.provider_failures_total.labels(provider="openai", error_type="InvalidProviderResponseError").inc()
        raise InvalidProviderResponseError("OpenAI returned empty response object.", provider="openai")

    raw_json_size = len(json.dumps(raw_dict))

    try:
        normalized_dict = normalize_invoice_json(raw_dict)
        parsed_schema = InvoiceSchema.model_validate(normalized_dict)
    except Exception as e:
        metrics.schema_validation_failures_total.labels(provider="openai").inc()
        metrics.provider_failures_total.labels(provider="openai", error_type="SchemaValidationError").inc()
        logger.error(f"OpenAI output failed InvoiceSchema validation. Raw JSON size: {raw_json_size} bytes. Missing/invalid fields: {e}")
        raise SchemaValidationError(f"OpenAI response failed schema validation: {e}", provider="openai")

    usage = {
        "prompt_tokens": completion.usage.prompt_tokens if completion.usage else 0,
        "completion_tokens": completion.usage.completion_tokens if completion.usage else 0,
        "total_tokens": completion.usage.total_tokens if completion.usage else 0,
        "latency_seconds": round(latency, 3),
        "raw_json_bytes": raw_json_size,
        "prompt_version": OPENAI_PROMPT_VERSION,
    }

    logger.info(
        f"OpenAI vision extraction successful. Provider: openai, Model: {model_name}, "
        f"Latency: {usage['latency_seconds']}s, Size: {raw_json_size}B, Prompt Tokens: {usage['prompt_tokens']}, "
        f"Completion Tokens: {usage['completion_tokens']}, Total Tokens: {usage['total_tokens']}"
    )
    return parsed_schema, usage
