import logging
import config
import utils
from schemas import InvoiceSchema
from backend.ai.openai_provider import extract_openai
from backend.ai.gemini_provider import extract_gemini
from backend.ai.groq_provider import extract_groq
from backend.exceptions import ConfigurationError, InvalidProviderResponseError, SchemaValidationError
import metrics

logger = logging.getLogger("cevondocs")

# Alias for backwards compatibility
resize_image_b64 = utils.resize_image_b64


def extract_invoice(b64_image: str) -> tuple[InvoiceSchema, dict]:
    """
    Router that delegates extraction to the configured AI provider.
    Supports multi-provider fallback when ENABLE_PROVIDER_FALLBACK=True.
    Returns (parsed_schema, usage_stats).
    """
    resized_b64 = resize_image_b64(b64_image, config.MAX_IMAGE_DIMENSION)
    primary_provider = config.AI_PROVIDER

    providers_map = {
        "openai": extract_openai,
        "gemini": extract_gemini,
        "groq": extract_groq,
    }

    if primary_provider not in providers_map:
        raise ConfigurationError(f"Unsupported AI provider: '{primary_provider}'")

    fallback_order = [primary_provider]
    if config.ENABLE_PROVIDER_FALLBACK:
        # Build order preferring configured keys
        candidates = ["openai", "gemini", "groq"]
        for p in candidates:
            if p not in fallback_order:
                fallback_order.append(p)

    last_error = None
    for i, current_provider in enumerate(fallback_order):
        if i > 0:
            prev_provider = fallback_order[i - 1]
            logger.warning(f"Fallback triggered: Attempting extraction with '{current_provider}' after '{prev_provider}' failed.")
            metrics.provider_fallback_total.labels(from_provider=prev_provider, to_provider=current_provider).inc()

        try:
            extractor = providers_map[current_provider]
            return extractor(b64_image, resized_b64)
        except (InvalidProviderResponseError, SchemaValidationError) as e:
            last_error = e
            if not config.ENABLE_PROVIDER_FALLBACK:
                raise
        except Exception as e:
            last_error = e
            if not config.ENABLE_PROVIDER_FALLBACK:
                raise

    if last_error:
        raise last_error
    raise ConfigurationError(f"All extraction providers failed: {primary_provider}")
