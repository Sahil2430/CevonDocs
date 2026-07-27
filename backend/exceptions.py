"""
Typed Exceptions for CevonDocs Multi-Provider Extraction & Moderation Architecture.
Provides distinct error classes mapped to appropriate HTTP status codes.
"""

class CevonDocsError(Exception):
    """Base exception for all CevonDocs application errors."""
    def __init__(self, message: str, status_code: int = 500, details: dict | None = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.details = details or {}


# Backward compatibility alias
LedgerLensError = CevonDocsError


class ProviderUnavailableError(CevonDocsError):
    """Raised when an AI provider is unreachable or returns 503 Service Unavailable."""
    def __init__(self, message: str, provider: str = "unknown", details: dict | None = None):
        super().__init__(message, status_code=503, details={"provider": provider, **(details or {})})


class RateLimitError(CevonDocsError):
    """Raised when an AI provider rate limit / quota (HTTP 429) is exceeded."""
    def __init__(self, message: str, provider: str = "unknown", retry_after: float | None = None, details: dict | None = None):
        super().__init__(
            message,
            status_code=429,
            details={"provider": provider, "retry_after": retry_after, **(details or {})}
        )


class InvalidProviderResponseError(CevonDocsError):
    """Raised when an AI provider returns malformed, non-JSON, or empty responses (HTTP 422)."""
    def __init__(self, message: str, provider: str = "unknown", raw_response: str | None = None, details: dict | None = None):
        super().__init__(
            message,
            status_code=422,
            details={"provider": provider, "raw_response": raw_response, **(details or {})}
        )


class SchemaValidationError(CevonDocsError):
    """Raised when provider output fails Pydantic InvoiceSchema validation (HTTP 422)."""
    def __init__(self, message: str, provider: str = "unknown", validation_errors: list | None = None, details: dict | None = None):
        super().__init__(
            message,
            status_code=422,
            details={"provider": provider, "validation_errors": validation_errors or [], **(details or {})}
        )


class ModerationFailure(CevonDocsError):
    """Raised when an uploaded document fails moderation screening (HTTP 422)."""
    def __init__(self, reason: str, provider: str = "unknown", details: dict | None = None):
        super().__init__(
            f"Image blocked by moderation gate: {reason}",
            status_code=422,
            details={"reason": reason, "provider": provider, **(details or {})}
        )


class ModerationUnavailableError(CevonDocsError):
    """Raised when a moderation provider fails, times out, is unavailable, or returns malformed response (HTTP 503)."""
    def __init__(self, message: str, provider: str = "unknown", details: dict | None = None):
        super().__init__(
            message,
            status_code=503,
            details={"provider": provider, **(details or {})}
        )


class ConfigurationError(CevonDocsError):
    """Raised when application configuration or API keys are missing/invalid (HTTP 503)."""
    def __init__(self, message: str, details: dict | None = None):
        super().__init__(message, status_code=503, details=details)


class ProviderTimeoutError(CevonDocsError):
    """Raised when an AI provider request times out (HTTP 504)."""
    def __init__(self, message: str, provider: str = "unknown", timeout_seconds: float | None = None, details: dict | None = None):
        super().__init__(
            message,
            status_code=504,
            details={"provider": provider, "timeout_seconds": timeout_seconds, **(details or {})}
        )
