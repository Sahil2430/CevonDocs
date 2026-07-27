# Changelog

All notable changes to **CevonDocs** will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [v1.0.0] - 2026-07-27

### Added
- **Multi-Provider AI Vision Extraction**: Integrated support for **OpenAI** (`gpt-4o-mini`), **Google Gemini** (`gemini-3.6-flash`), and **Groq** (`llama-3.2-11b-vision-preview` / `qwen3.6-27b`) vision models.
- **Dynamic Pydantic Schema Prompting**: Automatically injects `InvoiceSchema.model_json_schema()` into versioned system prompts (`backend/prompts/`) to guarantee structured JSON output.
- **Shared Output Normalization (`backend/ai/normalizer.py`)**: Provider-agnostic normalization mapping model field aliases (`price` → `unit_price`), calculating line item amounts, and enforcing a non-fabrication policy.
- **Rule-Based Validation & Recalibration Engine (`backend/validation.py`)**: Runs 10+ deterministic checks (financial totals verification, line item sums, required fields, ISO currencies, historical dates) to calibrate raw AI confidence scores.
- **Independent Validation Metrics UI**: Streamlit dashboard presenting four independent metrics: **Validation Score**, **AI Base Confidence**, **Validation Adjustment**, and **Final Confidence**.
- **Fail-Closed Content Moderation Gate**: Provider-agnostic moderation gate (`auto`, `openai`, `gemini`, `local`). API failures, timeouts, or unconfigured credentials raise `ModerationUnavailableError` and force human review.
- **Human-in-the-Loop Review Workflow**: Interactive Streamlit tab allowing users to inspect watermarked previews, review warnings, edit fields/line items (`st.data_editor`), and submit approvals (`POST /approve`).
- **PII Redaction & Provenance Watermarking**: Automatic regex masking (`pii.py`) for SSNs, email, phone numbers, and Aadhaar IDs prior to log output, plus PIL watermarking (`watermark.py`).
- **Prometheus & Grafana Instrumentation**: Granular metric tracking at `/metrics` (request counts, latency histograms, token costs, validation scores) paired with pre-configured Grafana dashboards.
- **Docker & GitHub Actions CI/CD**: Multi-stage production [Dockerfile](Dockerfile), [docker-compose.yml](docker-compose.yml) stack, and automated GitHub Actions CI workflow ([ci.yml](.github/workflows/ci.yml)).
- **Automated Test Suite**: 57 comprehensive unit and integration tests covering schemas, normalization, confidence routing, fail-closed moderation, and API endpoints.

### Changed
- Standardized product branding to **CevonDocs** across all backend loggers (`logging.getLogger("cevondocs")`), database defaults (`cevondocs.db`), exception handlers, and documentation.
- Grouped passed validation checks in the Streamlit UI into clean summary items (`✓ Required fields verified`, `✓ Financial totals verified`, `✓ Image validation passed`) to eliminate debug noise.
- Formatted all confidence scores across the application to consistent decimal representations (e.g. `0.97`, `0.85`, `< 0.75`).

### Improved
- Structured exponential backoff retries (**2s → 4s → 8s**, max 3 attempts) for transient provider errors (`429`, `500`, `502`, `503`, `504`).
- Hot-swap provider failover sequence (`groq` → `gemini` → `openai`) when primary provider quotas are exceeded.
- Image preprocessing & thumbnail resizing to reduce vision API token consumption by up to 65%.

### Known Limitations
- **Handwritten Invoices**: Complex cursive or poor handwriting reduces extraction accuracy.
- **Low-Resolution Documents**: Images below $200 \times 200\text{px}$ trigger validation warnings and require manual review.
- **SQLite Storage**: Default database backend (`cevondocs.db`) is designed for single-node deployments.
- **Single-Document Ingestion**: Ingestion handles one receipt/invoice image file per API request (no batch uploads).
- **AI Moderation Credentials**: Automated AI moderation requires active OpenAI or Gemini API keys; otherwise operates in `LOCAL_ONLY` basic image validation mode.
