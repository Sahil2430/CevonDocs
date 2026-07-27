from prometheus_client import Counter, Histogram

# Latency Histograms
moderation_latency = Histogram(
    "moderation_latency_seconds", "Moderation API latency in seconds"
)
extraction_latency = Histogram(
    "extraction_latency_seconds", "GPT-4o extraction latency in seconds"
)

# Usage & Cost Counters
token_cost_total = Counter(
    "token_cost_usd_total", "Cumulative token cost in USD"
)
auto_approvals_total = Counter(
    "auto_approvals_total", "Total documents auto-approved"
)
reviews_total = Counter(
    "reviews_total", "Total documents routed to human review queue"
)
documents_processed_total = Counter(
    "documents_processed_total", "Total documents processed", ["status"]
)

# Multi-Provider Production Observability Metrics
provider_requests_total = Counter(
    "provider_requests_total", "Total AI provider extraction requests", ["provider", "model"]
)
provider_failures_total = Counter(
    "provider_failures_total", "Total AI provider extraction failures", ["provider", "error_type"]
)
provider_latency_seconds = Histogram(
    "provider_latency_seconds", "AI provider extraction latency in seconds", ["provider"]
)
provider_retries_total = Counter(
    "provider_retries_total", "Total AI provider retry attempts", ["provider"]
)
provider_fallback_total = Counter(
    "provider_fallback_total", "Total provider fallback executions", ["from_provider", "to_provider"]
)
schema_validation_failures_total = Counter(
    "schema_validation_failures_total", "Total schema validation failures", ["provider"]
)
