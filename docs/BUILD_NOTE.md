# 🧾 CevonDocs — Capstone Build Note

**Project:** CevonDocs  
**Version:** 1.2.0 (Production-Hardened Release)  
**Date:** July 27, 2026  

---

## What Shipped

CevonDocs shipped a full-stack, multi-provider AI document intelligence platform that ingests receipt and invoice images (PNG, JPEG ≤ 10MB), screens content via a fail-closed moderation gate, extracts structured fields using vision models (**OpenAI**, **Google Gemini**, **Groq**), validates financial rules, redacts PII before logging, stamps provenance watermarks, and routes low-confidence extractions to an interactive human review dashboard.

---

## Key Technical Decisions

- **Multi-Provider Abstraction**: Decoupled vision providers (`openai`, `gemini`, `groq`) behind a unified router interface (`extraction.py`) featuring exponential backoff retries and hot-swap fallback during outages.
- **Shared Normalization (`normalizer.py`)**: Provider-agnostic normalization that maps model field aliases (e.g. `price` → `unit_price`), computes line item amounts, and enforces a zero-fabrication policy.
- **Rule-Based Validation Engine (`validation.py`)**: Runs 10+ deterministic checks (arithmetic verification, required fields, ISO currencies, historical dates) to recalibrate raw AI confidence scores.
- **Confidence Routing (`confidence.py`)**: Enforces an auto-approval cutoff (≥ 0.75). Any extraction below threshold or failing validation fails closed to manual review.
- **Human Review Workflow (`streamlit_app.py`)**: Streamlit tab providing side-by-side watermarked document previews, warning alerts, and an editable line item grid (`st.data_editor`) to commit verified records via `POST /approve`.

---

## Stretch Goals

### Implemented
- Fail-closed moderation architecture (`ModerationUnavailableError`).
- Dynamic Pydantic schema prompting embedding JSON schemas into prompts.
- Internal data provenance tracking (`_provenance`) per field.
- Full Prometheus instrumentation (`/metrics`) and Grafana provisioning.

### Partially Implemented
- Multi-provider fallback (executes failover sequentially; parallel multi-provider voting planned for v2).

---

## Known Limitations

- **Handwritten Invoices**: Unstructured cursive or poor handwriting reduces extraction accuracy.
- **Low-Resolution Images**: Low DPI images below 200×200px trigger validation warnings and require manual review.
- **SQLite Single-Node Storage**: Default SQLite backend (`cevondocs.db`) is intended for single-node deployments.
- **No Batch Uploads**: Ingestion handles single image files per API request.
- **AI Moderation Credentials**: Automated AI moderation requires active OpenAI or Gemini API keys; otherwise, system operates in `LOCAL_ONLY` basic validation mode.
