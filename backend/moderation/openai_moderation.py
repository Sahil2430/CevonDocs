import logging
from openai import OpenAI
import config
import utils
from backend.exceptions import ModerationUnavailableError

logger = logging.getLogger("cevondocs")


def check_openai_moderation(b64_image: str) -> tuple[bool, str | None]:
    """
    Calls OpenAI Moderation API with omni-moderation-latest.
    Fails closed: raises ModerationUnavailableError on missing key, API failure, timeout, or malformed response.
    Returns (is_safe, blocked_reason).
    """
    if not config.OPENAI_API_KEY or config.OPENAI_API_KEY.strip().startswith("your-") or config.OPENAI_API_KEY.strip().startswith("your_"):
        logger.warning("OPENAI_API_KEY is required for OpenAI Moderation API gate.")
        raise ModerationUnavailableError("OPENAI_API_KEY is required for OpenAI Moderation API gate.", provider="openai")

    mime_type = utils.detect_mime_type(b64_image)

    try:
        client = OpenAI(api_key=config.OPENAI_API_KEY)

        def _call_moderation():
            return client.moderations.create(
                model=config.MODERATION_MODEL,
                input=[
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{mime_type};base64,{b64_image}"
                        }
                    }
                ]
            )

        response = utils.retry_on_transient(_call_moderation)
        if not response or not hasattr(response, "results") or not response.results:
            logger.error("OpenAI Moderation API returned an empty or malformed response.")
            raise ModerationUnavailableError("OpenAI Moderation API returned an empty or malformed response.", provider="openai")

        result = response.results[0]
        if not hasattr(result, "flagged") or not hasattr(result, "category_scores"):
            logger.error("OpenAI Moderation API response missing 'flagged' or 'category_scores' fields.")
            raise ModerationUnavailableError("OpenAI Moderation API response missing required fields.", provider="openai")

        # Check if flagged by OpenAI or score exceeds threshold
        flagged_category = None
        max_score = 0.0

        category_scores = result.category_scores
        scores_dict = category_scores.__dict__ if hasattr(category_scores, "__dict__") else dict(category_scores)
        for category, score in scores_dict.items():
            if isinstance(score, (int, float)):
                if score > config.MODERATION_THRESHOLD and score > max_score:
                    max_score = score
                    flagged_category = category

        if getattr(result, "flagged", False) or flagged_category:
            reason = flagged_category or "content_flagged"
            logger.warning(f"Image blocked by OpenAI moderation gate. Reason: {reason}")
            return False, reason

        return True, None

    except ModerationUnavailableError:
        raise
    except Exception as e:
        logger.error(f"Error calling OpenAI Moderation API: {e}")
        raise ModerationUnavailableError(f"OpenAI Moderation API request failed: {e}", provider="openai")

