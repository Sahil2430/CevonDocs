import re
import logging

logger = logging.getLogger("cevondocs")

# PII Regular Expression Patterns
SSN_PATTERN = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
EMAIL_PATTERN = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
PHONE_PATTERN = re.compile(r"\b(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b")
AADHAAR_PATTERN = re.compile(r"\b[2-9]\d{3}\s?\d{4}\s?\d{4}\b")


def redact_pii(text: str) -> str:
    """
    Replaces SSN, email, phone numbers, and Aadhaar patterns with [REDACTED].
    Prevents PII from leaking into application log files.
    """
    if not text:
        return ""

    redacted = SSN_PATTERN.sub("[REDACTED]", text)
    redacted = EMAIL_PATTERN.sub("[REDACTED]", redacted)
    redacted = PHONE_PATTERN.sub("[REDACTED]", redacted)
    redacted = AADHAAR_PATTERN.sub("[REDACTED]", redacted)

    return redacted
