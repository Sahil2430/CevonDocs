import json
import base64
import logging
import config
import utils
from backend.exceptions import ModerationUnavailableError

logger = logging.getLogger("cevondocs")


def check_gemini_moderation(b64_image: str) -> tuple[bool, str | None]:
    """
    Calls Gemini vision model for safety and content screening.
    Fails closed: raises ModerationUnavailableError on missing key, API failure, timeout, malformed JSON, or missing is_safe field.
    Returns (is_safe, blocked_reason).
    """
    if not config.GEMINI_API_KEY or config.GEMINI_API_KEY.strip().startswith("your-") or config.GEMINI_API_KEY.strip().startswith("your_"):
        logger.warning("GEMINI_API_KEY is required for Gemini moderation provider.")
        raise ModerationUnavailableError("GEMINI_API_KEY is required for Gemini moderation provider.", provider="gemini")

    mime_type = utils.detect_mime_type(b64_image)
    image_bytes = base64.b64decode(b64_image)

    from google import genai
    from google.genai import types

    try:
        client = genai.Client(api_key=config.GEMINI_API_KEY)

        safety_prompt = (
            "Analyze this image carefully for illegal, unsafe, inappropriate, or sensitive content "
            "(e.g., violence, adult content, hate speech, harassment, weapons, explicit material).\n"
            "Return a JSON object with keys:\n"
            '- "is_safe": boolean (true if safe, false if unsafe)\n'
            '- "blocked_reason": string or null (category if unsafe, e.g. "hate_speech", "violence", "adult", "content_flagged")'
        )

        image_part = types.Part.from_bytes(
            data=image_bytes,
            mime_type=mime_type,
        )

        def _call_moderation():
            return client.models.generate_content(
                model=config.GEMINI_MODEL,
                contents=[image_part, safety_prompt],
                config=types.GenerateContentConfig(
                    response_mime_type="application/json"
                ),
            )

        response = utils.retry_on_transient(_call_moderation)
        if not response or not getattr(response, "text", None):
            logger.error("Gemini Moderation API returned an empty response.")
            raise ModerationUnavailableError("Gemini Moderation API returned an empty response.", provider="gemini")

        try:
            parsed = json.loads(response.text)
        except Exception as e:
            logger.error(f"Gemini Moderation API returned malformed JSON: {e}")
            raise ModerationUnavailableError(f"Gemini Moderation API returned malformed JSON: {e}", provider="gemini")

        if not isinstance(parsed, dict) or "is_safe" not in parsed:
            logger.error("Gemini Moderation API response missing required 'is_safe' field.")
            raise ModerationUnavailableError("Gemini Moderation API response missing required 'is_safe' field.", provider="gemini")

        is_safe = parsed.get("is_safe")
        if not isinstance(is_safe, bool):
            logger.error("Gemini Moderation API response 'is_safe' is not a boolean.")
            raise ModerationUnavailableError("Gemini Moderation API response 'is_safe' is not a boolean.", provider="gemini")

        blocked_reason = parsed.get("blocked_reason")

        if not is_safe:
            reason = blocked_reason or "content_flagged"
            logger.warning(f"Image blocked by Gemini moderation gate. Reason: {reason}")
            return False, reason

        return True, None

    except ModerationUnavailableError:
        raise
    except Exception as e:
        logger.error(f"Error calling Gemini Moderation API: {e}")
        raise ModerationUnavailableError(f"Gemini Moderation API request failed: {e}", provider="gemini")

